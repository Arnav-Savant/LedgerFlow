from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseSettings):
    name: str = "commerce-service"
    environment: str = "development"
    host: str = "localhost"
    port: int = 8001
    debug: bool = False
    reload: bool = True
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    payment_service_host: str = "localhost"
    payment_service_port: int = 8002

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        case_sensitive=False,
        extra="ignore",
    )


server_config = ServerConfig()
