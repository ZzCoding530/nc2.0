"""应用配置：只从 .env / 环境变量读取，代码中不出现任何真实密钥。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/app.db"

    jwt_secret_student: str = "dev-student-secret"
    jwt_secret_staff: str = "dev-staff-secret"
    jwt_expire_days: int = 14

    # 邮件后端：console（打印终端）/ mailpit（本地 SMTP 调试）/ smtp（生产）
    email_backend: str = "console"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_ssl: bool = False
    mail_from_name: str = "NiceOffer 班主任"

    app_base_url: str = "http://localhost:5173"

    admin_bootstrap_email: str = "admin@example.com"
    admin_bootstrap_password: str = "ChangeMe123!"

    tz: str = "Asia/Shanghai"

    testing: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
