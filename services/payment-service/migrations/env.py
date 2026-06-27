import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure the service root is on the path so config/models are importable
# when running `alembic` from the CLI inside services/payment-service/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.postgres_config import postgres_config
from models.base import Base
import models  # noqa: F401 — side-effect import: registers all models with Base.metadata

config = context.config
config.set_main_option("sqlalchemy.url", postgres_config.sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

VERSION_TABLE = "payment_alembic_version"

def include_object(obj, name, type_, reflected, compare_to):
    """Restrict autogenerate to tables owned by the payment service only.

    Derives the owned table set from Base.metadata, which is populated by
    `import models` above. Any model added to models/ is automatically
    included; any removed model is automatically excluded — no manual list.
    """
    if type_ == "table" and name not in target_metadata.tables:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=VERSION_TABLE,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
