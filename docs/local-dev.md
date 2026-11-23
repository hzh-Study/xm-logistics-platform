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
# 登录应 200，随后的 /me 应 200；若 /me 401 就是 cookie/Session 配置回归
curl -s -c /tmp/c.txt -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"<种子账号手机号>","password":"<本地环境口令>"}'
curl -s -b /tmp/c.txt http://127.0.0.1:8000/api/auth/me
```

口令从本地环境文件读取，命令里用占位，不要回显明文。登录 200 且 `/me` 200 才算通过。
