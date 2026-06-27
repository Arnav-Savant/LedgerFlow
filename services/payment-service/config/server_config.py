from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseSettings):
    name: str = "payment-service"
    environment: str = "development"
    host: str = "localhost"
    port: int = 8002
    debug: bool = False
    reload: bool = True
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    payment_session_expiry_seconds: int = 900  # 15 minutes; override via APP_PAYMENT_SESSION_EXPIRY_SECONDS

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        case_sensitive=False,
        extra="ignore",
    )


server_config = ServerConfig()
