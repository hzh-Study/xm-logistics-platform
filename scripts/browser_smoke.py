"""浏览器冒烟：无头 Edge + CDP 遍历三角色页面，捕获错误并截图。"""

import argparse
import base64
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import websocket

EDGE_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/microsoft-edge",
    "/usr/bin/chromium",
)

WEB_PAGES = (
    "/admin", "/admin/orders", "/admin/tasks", "/admin/accounts",
    "/admin/announcements", "/admin/platform-exceptions", "/admin/vehicle-transfers",
    "/admin/carriers", "/admin/certifications", "/admin/shipper-certifications",
)
CARRIER_PAGES = (
    "/carrier", "/carrier/certification", "/carrier/order-pool", "/carrier/dispatch",
    "/carrier/exceptions", "/carrier/cancel-applications", "/carrier/drivers",
    "/carrier/vehicles", "/carrier/expenses",
)
H5_PAGES = ("/home", "/tasks", "/expenses")


def free_port() -> int:
    """取一个空闲端口供 CDP 使用。"""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def edge_path() -> str:
    """返回本机可用的 Edge 或 Chromium 路径。"""
    for path in EDGE_CANDIDATES:
        if Path(path).is_file():
            return path
    raise RuntimeError("未找到 Edge/Chromium，请安装后重试")


def wait_cdp(port: int, timeout: float = 15.0) -> str:
    """轮询 CDP 版本接口，返回浏览器 WebSocket 地址。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as resp:
                return json.load(resp)["webSocketDebuggerUrl"]
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("CDP 未就绪")


class Cdp:
    """极简 CDP 客户端：命令同步等待，事件留作断言。"""

    def __init__(self, url: str):
        self.ws = websocket.create_connection(url, timeout=15)
        self.seq = 0
        self.events: list[dict] = []

    def cmd(self, method: str, params: dict | None = None, session_id: str | None = None) -> dict:
        """发一条 CDP 命令并返回结果。"""
        self.seq += 1
        message = {"id": self.seq, "method": method, "params": params or {}}
        if session_id:
            message["sessionId"] = session_id
        self.ws.send(json.dumps(message))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.seq:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self.events.append(msg)

    def drain(self, seconds: float) -> None:
        """再收一段时间事件，确保网络与日志事件到齐。"""
        deadline = time.time() + seconds
        self.ws.settimeout(0.2)
        while time.time() < deadline:
            try:
                self.events.append(json.loads(self.ws.recv()))
            except websocket.WebSocketTimeoutException:
                pass
        self.ws.settimeout(15)

    def close(self) -> None:
        """关闭 WebSocket 连接。"""
        self.ws.close()


def evaluate(cdp: Cdp, session: str, expression: str):
    """在页面上下文执行表达式并取值。"""
    result = cdp.cmd(
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True, "awaitPromise": True},
        session,
    )
    return result.get("result", {}).get("value")


def navigate(cdp: Cdp, session: str, url: str, wait: float = 2.2) -> None:
    """导航到 URL 并收齐事件。"""
    cdp.events.clear()
    cdp.cmd("Page.navigate", {"url": url}, session)
    time.sleep(wait)
    cdp.drain(0.4)


def problems(events: list[dict]) -> list[str]:
    """从事件里挑出 JS 异常、console error 与 4xx/5xx。"""
    found = []
    for event in events:
        method = event.get("method")
        if method == "Runtime.exceptionThrown":
            detail = event["params"]["exceptionDetails"]
            found.append(f"JS: {detail.get('text', '')}")
        elif method == "Log.entryAdded" and event["params"]["entry"].get("level") == "error":
            found.append(f"LOG: {event['params']['entry'].get('text', '')}")
        elif method == "Network.responseReceived":
            resp = event["params"]["response"]
            if resp["status"] >= 400:
                path = urllib.parse.urlparse(resp["url"]).path
                found.append(f"HTTP {resp['status']}: {path}")
    return found


def statuses(events: list[dict]) -> list[str]:
    """列出 /api 请求的状态码与路径，脱敏且不含请求体。"""
    lines = []
    for event in events:
        if event.get("method") != "Network.responseReceived":
            continue
        resp = event["params"]["response"]
        path = urllib.parse.urlparse(resp["url"]).path
        if path.startswith("/api/"):
            lines.append(f"{resp['status']} {path}")
    return lines


def screenshot(cdp: Cdp, session: str, out_dir: Path, name: str) -> None:
    """把当前页面存成 PNG。"""
    result = cdp.cmd("Page.captureScreenshot", {"format": "png"}, session)
    (out_dir / f"{name}.png").write_bytes(base64.b64decode(result["data"]))


def login(cdp: Cdp, session: str, base_url: str) -> bool:
    """点真实登录按钮，依赖 dev 预填手机号与口令。"""
    navigate(cdp, session, f"{base_url}/login", wait=1.8)
    cdp.events.clear()
    evaluate(cdp, session, "document.querySelector('button[type=submit]')?.click(); true")
    time.sleep(2.5)
    cdp.drain(0.4)
    ok = any(
        "200" in line and "/api/auth/login" in line
        for line in statuses(cdp.events)
    )
    path = evaluate(cdp, session, "location.pathname")
    return ok and path != "/login"


def visit(cdp: Cdp, session: str, base_url: str, path: str, tag: str, out_dir: Path, shots: bool) -> bool:
    """打开一个页面并断言无错误，返回是否通过。"""
    navigate(cdp, session, f"{base_url}{path}")
    text = evaluate(cdp, session, "document.body.innerText") or ""
    found = problems(cdp.events)
    bad_text = "资源不存在" in text
    ok = not found and not bad_text
    flag = "PASS" if ok else "FAIL"
    print(f"  [{flag}] {tag} {path} | 资源不存在={bad_text} 错误={len(found)}")
    for item in found[:5]:
        print(f"         {item}")
    if shots:
        screenshot(cdp, session, out_dir, f"{tag}_{path.strip('/').replace('/', '_') or 'home'}")
    return ok


def run(args: argparse.Namespace) -> int:
    """执行完整冒烟，返回进程退出码。"""
    port = free_port()
    profile = tempfile.mkdtemp(prefix="browser-smoke-")
    out_dir = Path(args.screenshot_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    edge = subprocess.Popen(
        [
            edge_path(), "--headless=new", f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
            "--disable-gpu", "--window-size=1440,900", "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    cdp = None
    passed = True
    try:
        cdp = Cdp(wait_cdp(port))
        target = cdp.cmd("Target.createTarget", {"url": "about:blank"})["targetId"]
        session = cdp.cmd("Target.attachToTarget", {"targetId": target, "flatten": True})["sessionId"]
        for domain in ("Page", "Network", "Runtime", "Log"):
            cdp.cmd(f"{domain}.enable", {}, session)

        plans = (
            ("管理员", args.web_url, WEB_PAGES),
            ("物流公司", args.web_url, CARRIER_PAGES),
            ("司机", args.h5_url, H5_PAGES),
        )
        for index, (role, base_url, pages) in enumerate(plans):
            print(f"[{role}] 登录 {base_url}")
            if not login(cdp, session, base_url):
                print(f"  [FAIL] 登录失败：请确认 dev 预填账号与口令已配置")
                passed = False
                continue
            for path in pages:
                if not visit(cdp, session, base_url, path, role, out_dir, not args.no_screenshot):
                    passed = False
            print("  API:", " | ".join(statuses(cdp.events)[:6]))
    finally:
        if cdp:
            cdp.close()
        edge.terminate()
        try:
            edge.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(edge.pid)], capture_output=True)
            else:
                edge.kill()
        shutil.rmtree(profile, ignore_errors=True)

    print(f"截图目录: {out_dir}")
    return 0 if passed else 1


def main() -> int:
    """解析参数并运行冒烟。"""
    parser = argparse.ArgumentParser(description="三角色页面浏览器冒烟")
    parser.add_argument("--web-url", default="http://127.0.0.1:5173", help="Web 管理端地址")
    parser.add_argument("--h5-url", default="http://127.0.0.1:5174", help="司机 H5 地址")
    parser.add_argument("--screenshot-dir", default="debug-shots", help="截图输出目录")
    parser.add_argument("--no-screenshot", action="store_true", help="不保存截图")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
