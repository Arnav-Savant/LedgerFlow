from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresConfig(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    db: str = "ledgerflow"
    user: str = "postgres"
    password: str = "postgres"
    pool_size: int = 5
    max_overflow: int = 10

    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="POSTGRES_",
        case_sensitive=False,
        extra="ignore",
    )


postgres_config = PostgresConfig()
