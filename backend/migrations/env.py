from alembic import context

from app.models.entities import Base

connection = context.config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Use python -m app.db.migrate so migration uses the application configuration")
context.configure(connection=connection, target_metadata=Base.metadata)
with context.begin_transaction():
    context.run_migrations()
