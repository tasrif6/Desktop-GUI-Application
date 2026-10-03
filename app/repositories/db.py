from sqlalchemy import create_engine
import oracledb
from app.config.settings import TRINO_URL, ORACLE_DSN, ORACLE_CLIENT_LIB

class DatabaseManager:
    def __init__(self):
        self.trino_engine=None
        self.oracle_conn=None

    def connect_trino(self):
        if not TRINO_URL:
            raise RuntimeError("TRINO_URL is not configured in .env")
        # Reuse a single engine/connection-pool for the lifetime of this
        # DatabaseManager instead of creating a brand-new engine (and a
        # brand-new pool of open sockets) on every fetch call. Each
        # `with self.db.connect_trino() as con:` call site already closes
        # the individual connection it checks out; only the engine itself
        # needs to be created once and disposed once, in close().
        if self.trino_engine is None:
            self.trino_engine=create_engine(TRINO_URL, pool_pre_ping=True)
        return self.trino_engine.connect()

    def connect_oracle(self):
        if not ORACLE_DSN:
            raise RuntimeError("ORACLE_DSN is not configured in .env")
        if ORACLE_CLIENT_LIB:
            try: oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB)
            except oracledb.ProgrammingError: pass
        self.oracle_conn=oracledb.connect(ORACLE_DSN)
        return self.oracle_conn

    def close(self):
        try:
            if self.oracle_conn: self.oracle_conn.close()
        finally:
            self.oracle_conn=None
        if self.trino_engine:
            self.trino_engine.dispose()
            self.trino_engine=None
