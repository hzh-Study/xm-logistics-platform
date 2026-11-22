# 项目上下文（交给 Agent 的说明文件）

> 使用方式：把本文件提供给任意 Agent，它即可了解本项目的环境、技术栈和约定，无需再口头补充说明。
> 本文中的项目指 `c:\Users\20992\Desktop\xm\logistics platform` 下的应用。

## 一、本地环境

- **操作系统**：Windows 11 Home
- **终端**：Windows cmd（不是 PowerShell，也不是 bash/sh）
- **已安装工具**：
  - Node.js `v26.13.1`，npm `11.20.0`
  - Git `2.56.1.windows.1`
  - Python `3.12.10`（通过 winget 安装，位置 `C:\Users\20992\AppData\Local\Programs\Python\Python312\`）
    - pip `25.0.1`、`venv` 均可用
    - 用户级 PATH 已写入；**新开终端**可直接用 `python`，旧终端需重开才生效
- **未安装**：MySQL、PostgreSQL、Redis、Docker 等任何数据库或容器服务

## 二、技术栈

| 层次 | 技术 | 说明 |
| --- | --- | --- |
| 前端 | Vue 3 | Vite 构建，npm 管理依赖 |
| 后端 | FastAPI | Python Web 框架 |
| 数据库 | SQLite | Python 标准库 `sqlite3`，无需安装服务，数据为本地 `.db` 文件 |
| 版本控制 | Git | — |

选择理由：本地只有 Node / Python3 / Git 三个环境，SQLite 为 Python 内置、免安装，因此该技术栈正好覆盖且无需额外软件。

## 三、约定与偏好（重要）

1. **脚本统一用 Python**：所有自动化、启动、构建、建表、数据初始化等脚本一律写为 `.py` 文件，**不写** `.bat` / `.cmd` 批处理，也不依赖 bash/sh 脚本。运行方式：`python xxx.py`。
2. **前端命令例外**：`npm run dev` / `npm run build` 等属于 npm 自带命令，不是手写脚本，可正常使用。
3. **后端启动入口**：提供一个 `run.py` 作为启动脚本（内部调用 uvicorn），运行 `python run.py`。若需并行启动前后端，也用 Python 脚本编排，不写批处理。
4. **不引入额外服务**：优先选择零额外依赖的库；若方案需要 MySQL / Redis / Docker / PostgreSQL 等，先明确告知用户需要先安装，再动手。
5. **依赖声明**：Python 依赖写入 `requirements.txt`（或 `pyproject.toml`），前端依赖写入 `package.json`，便于复现环境。
6. **可读性优先**：脚本尽量只依赖标准库或已声明依赖，保持跨平台与清晰。
