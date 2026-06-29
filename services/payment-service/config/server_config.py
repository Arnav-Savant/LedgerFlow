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
    payment_session_max_attempts: int = 3      # override via APP_PAYMENT_SESSION_MAX_ATTEMPTS
    psp_simulate_success: bool | None = None   # None=random, True=always succeed, False=always fail; APP_PSP_SIMULATE_SUCCESS
    payment_frontend_base_url: str = "http://localhost:5173/payments/session"  # Env: APP_PAYMENT_FRONTEND_BASE_URL

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        case_sensitive=False,
        extra="ignore",
    )


server_config = ServerConfig()
