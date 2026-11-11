import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

load_dotenv()


def connect_with_connector(*, admin=False):
    mode = os.getenv("DATABASE_MODE", "cloud").strip().lower()

    if mode == "local":
        user = (
            os.environ["LOCAL_DB_ADMIN_USER"]
            if admin
            else os.environ["LOCAL_DB_USER"]
        )
        password = (
            os.environ["LOCAL_DB_ADMIN_PASSWORD"]
            if admin
            else os.environ["LOCAL_DB_PASSWORD"]
        )

        url = URL.create(
            drivername="postgresql+pg8000",
            username=user,
            password=password,
            host=os.getenv("LOCAL_DB_HOST", "127.0.0.1"),
            port=int(os.getenv("LOCAL_DB_PORT", "5433")),
            database=os.environ["LOCAL_DB_NAME"],
        )

        return create_engine(
            url,
            pool_size=5,
            max_overflow=2,
            pool_timeout=30,
            pool_pre_ping=True,
        )

    if mode == "cloud":
        if admin:
            from cloud_admin_connection import (
                connect_with_connector as connect_cloud,
            )
        else:
            from cloud_sql_connection import (
                connect_with_connector as connect_cloud,
            )

        return connect_cloud()

    raise ValueError("DATABASE_MODE must be local or cloud")


def close_connector(*, admin=False):
    if os.getenv("DATABASE_MODE", "cloud").strip().lower() != "cloud":
        return

    if admin:
        from cloud_admin_connection import close_connector as close_cloud
    else:
        from cloud_sql_connection import close_connector as close_cloud

    close_cloud()