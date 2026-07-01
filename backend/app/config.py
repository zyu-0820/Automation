from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./automation.db"
    encryption_key: str = ""
    secret_key: str = "change-me-in-production"
    cors_origins: list[str] = ["http://localhost:5173"]
    ssh_connect_timeout: int = 10
    ssh_operation_timeout: int = 30
    max_concurrent_ssh: int = 5
    temp_dir: str = "./temp"

    model_config = {"env_file": ".env"}


settings = Settings()
