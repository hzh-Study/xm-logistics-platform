"""FastAPI 应用入口：装配路由、异常处理器、CORS 与启动初始化。"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.db.connection import initialize
from app.db.seed import seed_admin
from app.errors import register_error_handlers
from app.routers import (
    admin,
    auth,
    carrier,
    carrier_pool,
    cert_review,
    dispatch,
    driver,
    shipper,
    vehicle,
    warehouse,
    workbench,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """创建并返回应用实例，settings 缺省时从环境变量读取。"""
    if settings is None:
        settings = Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
        initialize(settings.db_path)
        from app.db.connection import connect

        conn = connect(settings.db_path)
        try:
            seed_admin(conn, settings.seed_admin_phone, settings.seed_admin_password)
        finally:
            conn.close()
        yield

    app = FastAPI(title="物流运输管理平台", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )
    register_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(shipper.router)
    app.include_router(carrier.router)
    app.include_router(carrier_pool.router)
    app.include_router(dispatch.carrier_router)
    app.include_router(dispatch.driver_router)
    app.include_router(driver.carrier_router)
    app.include_router(driver.driver_router)
    app.include_router(vehicle.router)
    app.include_router(cert_review.router)
    app.include_router(admin.router)
    app.include_router(warehouse.router)
    app.include_router(workbench.router)
    return app
