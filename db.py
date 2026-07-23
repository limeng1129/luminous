"""
数据库层。

- 没设 DATABASE_URL           → 用本地 SQLite（本地开发，什么都不用装）
- 设了 DATABASE_URL 且是 postgres → 自动切到 Postgres（线上，数据永久保存）

两边的 SQL 写法差异（占位符、自增主键、加锁方式）都在这个文件里抹平了，
业务代码不用关心当前连的是哪种数据库。
"""
import os
from contextlib import contextmanager

BASE = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.environ.get("LUMINOUS_DB", os.path.join(BASE, "luminous.db"))


def database_url():
    return (os.environ.get("DATABASE_URL") or "").strip()


def is_postgres():
    return database_url().startswith(("postgres://", "postgresql://"))


def describe():
    """给自检页用的一句话描述。"""
    if is_postgres():
        url = database_url()
        host = url.split("@")[-1].split("/")[0] if "@" in url else "（未知主机）"
        return f"Postgres @ {host}"
    return f"SQLite @ {SQLITE_PATH}"


def _connect_pg():
    import psycopg2
    import psycopg2.extras
    url = database_url()
    kw = {"connect_timeout": 10, "cursor_factory": psycopg2.extras.RealDictCursor}
    if "sslmode=" not in url:
        kw["sslmode"] = "require"      # Neon / Supabase 都要求 SSL
    return psycopg2.connect(url, **kw)


def _connect_sqlite():
    import sqlite3
    conn = sqlite3.connect(SQLITE_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


class _Conn:
    """把两种驱动的差异包起来，对外只暴露 execute()。"""

    def __init__(self, raw, pg):
        self._raw = raw
        self.is_postgres = pg

    def execute(self, q, params=()):
        cur = self._raw.cursor()
        cur.execute(q.replace("?", "%s") if self.is_postgres else q, params)
        return cur

    def insert_returning_id(self, q, params=()):
        """插入一行并拿回新 id（两种数据库拿法不同）。"""
        if self.is_postgres:
            return self.execute(q + " RETURNING id", params).fetchone()["id"]
        return self.execute(q, params).lastrowid

    def lock_for_seeding(self):
        """播种示例数据时加锁，避免多进程同时启动重复写入。"""
        if self.is_postgres:
            self.execute("SELECT pg_advisory_xact_lock(%s)", (874112,))
        else:
            self.execute("BEGIN IMMEDIATE")


@contextmanager
def get_db():
    """用法：with get_db() as c: c.execute(...)   —— 正常结束自动提交，出错回滚，最后关闭。"""
    pg = is_postgres()
    raw = _connect_pg() if pg else _connect_sqlite()
    conn = _Conn(raw, pg)
    try:
        yield conn
        raw.commit()
    except Exception:
        try:
            raw.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            raw.close()
        except Exception:
            pass


def init_db():
    """建表。两种数据库的自增主键写法不同。"""
    pk = "SERIAL PRIMARY KEY" if is_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    with get_db() as c:
        c.execute(f"""CREATE TABLE IF NOT EXISTS photos(
            id         {pk},
            category   TEXT    NOT NULL,
            filename   TEXT,
            url        TEXT,
            title      TEXT    NOT NULL,
            subtitle   TEXT,
            width      INTEGER DEFAULT 800,
            height     INTEGER DEFAULT 1000,
            likes      INTEGER DEFAULT 0,
            created_at TEXT
        )""")
