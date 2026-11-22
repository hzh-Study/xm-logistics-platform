"""后端启动入口：python run.py。"""

import uvicorn

from app.main import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
