# 本地开发约定

三服务协作：后端 FastAPI + Web 管理端 + 司机 H5。本文只讲启动、环境文件与会话验证；代码规则见 `AGENTS.md` 指向的 conventions。

## 启动

按此顺序，各自在独立终端运行：

```bash
cd backend && pip install -r requirements.txt && python run.py     # 127.0.0.1:8000
cd web && npm install && npm run dev                               # 0.0.0.0:5173
cd driver-h5 && npm install && npm run dev                         # 0.0.0.0:5174
```

- `web` 与 `driver-h5` 把 `/api` 代理到 `http://localhost:8000`；浏览器只需访问前端端口。
- 后端根路径返回 404 属正常，`/docs` 为 200 即健康。
- 三个服务固定占用 **8000 / 5173 / 5174**。启动后必须核对端口，见下方「干净重启」。

### 访问地址与会话隔离

Web 管理端访问 `http://localhost:5173`，司机 H5 访问 `http://127.0.0.1:5174`。两端**可以用同一域名**：请求层按端注入 `X-Client-Id: web|h5`，后端据此分别使用 `session_token` 与 `h5_session_token` 两个 cookie，同域下也不会互相覆盖。

未做分端隔离前，两端同用 `127.0.0.1` 会共享一份会话，登录一个角色覆盖另一个，表现为被弹回登录页且 Network 出现大量 `404 资源不存在`。现已用无头浏览器在两端同域场景下实测：登录互不覆盖、刷新保持登录、H5 退出不影响 Web 会话（见 `docs/browser-smoke-checklist.md` 执行记录）。

## 本地环境文件 `.env.development.local`

口令只放在被 git 忽略的 `.env.*.local`（已在 `.gitignore`），**禁止写进代码或提交**。三份文件各管各的：

| 文件 | 键 | 用途 |
|------|-----|------|
| `backend/.env.development.local` | `SEED_DEV_ACCOUNTS=1`、`SEED_DEV_PASSWORD=<自行设置>`、`COOKIE_SECURE=0` | 开开发种子账号；关 Secure cookie |
| `web/.env.development.local` | `VITE_DEV_PHONE`、`VITE_DEV_PASSWORD` | 管理端登录预填 |
| `driver-h5/.env.development.local` | `VITE_DEV_PHONE`、`VITE_DEV_PASSWORD` | 司机端登录预填 |

- 开发种子账号（幂等创建，手机号固定）：管理员 `13800138000`、物流公司 `13800138001`、司机 `13800138002`，口令统一取 `SEED_DEV_PASSWORD`。前端预填的手机号须与对应种子账号一致。
- 前端预填仅在 `import.meta.env.DEV` 下生效；`npm run build` 产物不含任何预填账号口令。

### 为什么 dev 必须 `COOKIE_SECURE=0`

后端 `Settings.cookie_secure` 默认为 `True`（`COOKIE_SECURE=1`）。但本地走**明文 HTTP**，`Secure` cookie 不会被浏览器/客户端回传：登录接口返回 200，随后路由守卫的 `restore()` → `/api/auth/me` 拿到 401，用户被踢回登录页——表现为"登录失败"。

- 原因：会话靠 cookie 保持，`/me` 是登录态的唯一恢复点。
- 生产环境保持默认 `Secure`，**不要**把 `COOKIE_SECURE=0` 带上线。

## 干净重启

IDE 的任务停止常只结束 shell，`vite` 的 node 子进程会变成孤儿继续占端口；新服务发现 5173/5174 被占会自动跳到 5175/5176，导致你访问标准地址时看到的是旧进程。

处理：停服务后按端口确认没有残留监听，再启动；若发现跳端口，按端口找到 PID 结束进程后重启。

```powershell
# 查看占用（Windows）
Get-NetTCPConnection -State Listen -LocalPort 5173,5174,8000
# 必要时按PID结束
Stop-Process -Id <PID> -Force
```

完成后核对：`curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5173/` 返回 200，且 vite 输出显示监听的是标准端口。

## 会话链路验证（必做）

CI（`.github/workflows/ci.yml`）只跑 `pytest` 与 `npm run build`：backend 测试用 `tests/conftest.py` 里自定义的 `Settings(cookie_secure=False)`，前端只做类型检查/构建。**两者都覆盖不到真实 dev 的 HTTP + cookie 链路**。

因此，改动会话、cookie、鉴权或环境配置后，**必须**在跑起来的 dev 后端上手动验证一次登录态闭环：

```bash
# 两端各验一次：Web 用管理员号、H5 用司机号；login 与 /me 都应 200
# /me 401 就是该端 cookie/Session 配置回归
curl -s -c /tmp/c-web.txt -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' -H 'X-Client-Id: web' \
  -d '{"phone":"13800138000","password":"<本地环境口令>"}' \
  -o /dev/null -w 'web login: %{http_code}\n'
curl -s -b /tmp/c-web.txt -H 'X-Client-Id: web' \
  http://127.0.0.1:8000/api/auth/me -o /dev/null -w 'web me: %{http_code}\n'

curl -s -c /tmp/c-h5.txt -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' -H 'X-Client-Id: h5' \
  -d '{"phone":"13800138002","password":"<本地环境口令>"}' \
  -o /dev/null -w 'h5 login: %{http_code}\n'
curl -s -b /tmp/c-h5.txt -H 'X-Client-Id: h5' \
  http://127.0.0.1:8000/api/auth/me -o /dev/null -w 'h5 me: %{http_code}\n'
```

口令从本地环境文件读取，命令里用占位，不要回显明文。两端 login 与 `/me` 都 200 才算通过。分端 cookie 后 Web 写 `session_token`、H5 写 `h5_session_token`，`/me` 必须带对应 `X-Client-Id` 才能读到自己的会话。

## 浏览器冒烟验证（必做）

`npm run build` 全绿**不代表页面能用**——组件未注册、拼错组件名、路由失效这类问题，构建阶段可能完全无感（曾出现 Vant 只导入 CSS、漏 `app.use(Vant)`，页面只剩文字按钮，CI 与本地构建却全绿）。

因此，改动前端组件、组件注册、路由或布局后，除了 `npm run build`，**必须**在浏览器打开对应页面，确认关键控件可见、可点击、表单能提交。遵守 V1 决定：这里只加人工约定，**不引入 E2E 自动化框架**。

可复用的渲染回路：`python scripts/browser_smoke.py`（仓库根执行），自动登录三角色遍历全部页面，断言无 JS 异常 / console error / 4xx / 「资源不存在」并截图到 `debug-shots/`。它是人工约定的执行辅助，不是 E2E 框架；交互与响应式仍按清单人工检查。

逐页执行项与结果记录模板见 [`docs/browser-smoke-checklist.md`](browser-smoke-checklist.md)。

静态护栏已就位：H5 端 `src/components.d.ts` 声明了 Vant 全局组件类型，`tsconfig.json` 开启 `strictTemplates`，组件名拼错或 props 用错会在 `vue-tsc` 阶段报错。但它抓不到"运行时漏注册"——那一步只能靠浏览器冒烟兜住。
