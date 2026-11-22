"""应用配置：数据库路径、凭证目录、CORS 与 Cookie 安全参数。"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """从环境变量构造的不可变配置。"""

    db_path: str = "data/logistics.db"
    data_dir: str = "data"
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://localhost:5174",
    )
    cookie_secure: bool = True
    session_ttl_seconds: int = 8 * 3600
    seed_admin_phone: str = "13800138000"
    seed_admin_password: str = ""
    checkin_radius_m: int = 1000

    @classmethod
    def from_env(cls) -> "Settings":
        """读取环境变量，未设置处用默认值。"""
        origins = os.getenv("CORS_ORIGINS")
        return cls(
            db_path=os.getenv("DB_PATH", cls.db_path),
            data_dir=os.getenv("DATA_DIR", cls.data_dir),
            cors_origins=tuple(origins.split(",")) if origins else cls.cors_origins,
            cookie_secure=os.getenv("COOKIE_SECURE", "1") == "1",
            seed_admin_phone=os.getenv("SEED_ADMIN_PHONE", cls.seed_admin_phone),
            seed_admin_password=os.getenv("SEED_ADMIN_PASSWORD", ""),
            checkin_radius_m=int(os.getenv("CHECKIN_RADIUS_M", str(cls.checkin_radius_m))),
        )
