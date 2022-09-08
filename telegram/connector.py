from sqlalchemy import create_engine, engine

from .common import config


def connect_with_tcp(db_config: dict = {}) -> engine.base.Engine:
    pool = create_engine(
        engine.URL.create(
            drivername="postgresql",
            username=config["db_user"],
            password=config["db_pass"],
            database=config["db_name"],
            host=config.get("db_host") or "localhost",
            port=config.get("db_port") or 5432,
        ),
        **db_config
    )

    return pool


def init_connection_engine(method: str = "tcp", **kwargs) -> engine.base.Engine:
    pool_size = kwargs.get("pool_size")
    pool_timeout = kwargs.get("pool_timeout")

    db_config = {
        # Pool size is the maximum number of permanent connections to keep.
        "pool_size": pool_size or 5,
        # Temporarily exceeds the set pool_size if no connections are available.
        "max_overflow": 2,
        # The total number of concurrent connections for your application will be
        # a total of pool_size and max_overflow.
        # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
        # new connection from the pool. After the specified amount of time, an
        # exception will be thrown.
        "pool_timeout": pool_timeout or 30,  # 30 seconds
        # 'pool_recycle' is the maximum number of seconds a connection can persist.
        # Connections that live longer than the specified amount of time will be
        # reestablished
        "pool_recycle": 1800,  # 30 minutes
    }

    match method:
        case "tcp":
            return connect_with_tcp(db_config)
        case _:
            raise ValueError('Use "tcp" for method as currently supported method')
