import os
import logging
from logging.config import fileConfig

from flask import current_app
from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
instance_folder = os.path.join(project_dir, 'instance')
os.makedirs(instance_folder, exist_ok=True)
local_db_path = os.path.join(instance_folder, 'app.db')
local_db_uri = 'sqlite:///' + local_db_path


db_url_to_use = os.environ.get('DATABASE_URL', local_db_uri)
if "postgres://" in db_url_to_use:
    db_url_to_use = db_url_to_use.replace("postgres://", "postgresql://", 1)

config.set_main_option('sqlalchemy.url', db_url_to_use)

target_db = current_app.extensions['migrate'].db

def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # this change fixed the db error
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
