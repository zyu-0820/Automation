from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

# Map of table_name -> { column_name: column_type_sql }
EXPECTED_COLUMNS = {
    "servers": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "VARCHAR(100) NOT NULL",
        "host": "VARCHAR(255) NOT NULL",
        "port": "INTEGER NOT NULL DEFAULT 22",
        "username": "VARCHAR(100) NOT NULL",
        "auth_type": "VARCHAR(20) NOT NULL DEFAULT 'password'",
        "encrypted_password": "TEXT",
        "encrypted_private_key": "TEXT",
        "become_method": "VARCHAR(20) NOT NULL DEFAULT ''",
        "become_user": "VARCHAR(100)",
        "encrypted_become_password": "TEXT",
        "service_base_path": "VARCHAR(500) NOT NULL DEFAULT '/home/apps/services'",
        "config_extensions": "VARCHAR(200) NOT NULL DEFAULT 'yml,yaml,xml'",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    },
    "services": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "server_id": "INTEGER NOT NULL",
        "name": "VARCHAR(200) NOT NULL",
        "display_name": "VARCHAR(200)",
        "custom_path": "VARCHAR(500)",
        "control_method": "VARCHAR(20) NOT NULL DEFAULT 'auto'",
        "status": "VARCHAR(20) DEFAULT 'unknown'",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    },
    "operation_logs": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "server_id": "INTEGER",
        "service_id": "INTEGER",
        "operation_type": "VARCHAR(50) NOT NULL",
        "target_file": "VARCHAR(500)",
        "backup_file": "VARCHAR(500)",
        "status": "VARCHAR(20) NOT NULL",
        "message": "TEXT",
        "created_at": "DATETIME",
    },
}

# Map of table_name -> set of UNIQUE constraint names to create if they don't exist
# SQLite doesn't support adding constraints after table creation,
# but we track them for documentation


async def auto_migrate(engine: AsyncEngine):
    """Add any missing columns to existing tables without dropping data."""

    async with engine.connect() as conn:
        for table_name, columns in EXPECTED_COLUMNS.items():
            # check if table exists
            result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=:name"
                ),
                {"name": table_name},
            )
            if not result.fetchone():
                continue  # table doesn't exist yet, Base.metadata.create_all will handle it

            # get existing columns
            existing = await conn.execute(text(f"PRAGMA table_info('{table_name}')"))
            existing_cols = {row[1] for row in existing.fetchall()}

            for col_name, col_type in columns.items():
                if col_name not in existing_cols:
                    try:
                        await conn.execute(
                            text(
                                f"ALTER TABLE '{table_name}' ADD COLUMN '{col_name}' {col_type}"
                            )
                        )
                        await conn.commit()
                        print(f"[migrate] Added {table_name}.{col_name} {col_type}")
                    except Exception as e:
                        print(f"[migrate] Failed to add {table_name}.{col_name}: {e}")

        # update defaults for newly added columns (SQLite can't add DEFAULT to existing rows)
        await conn.commit()
