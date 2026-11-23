"""后端启动入口：python run.py。"""

import os
from pathlib import Path

import uvicorn


def load_local_env() -> None:
    """从本地环境文件加载开发配置，避免把口令写进代码。"""
    path = Path(__file__).parent / ".env.development.local"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()

from app.main import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
