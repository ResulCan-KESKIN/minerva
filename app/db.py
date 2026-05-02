import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

_conn = None


def get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = _yeni_baglanti()
    else:
        try:
            _conn.cursor().execute("SELECT 1")
        except Exception:
            _conn = _yeni_baglanti()
    return _conn


def _yeni_baglanti():
    return psycopg2.connect(
        host=os.environ["EXT_DB_HOST"],
        port=int(os.environ["EXT_DB_PORT"]),
        database=os.environ["EXT_DB_NAME"],
        user=os.environ["EXT_DB_USER"],
        password=os.environ["EXT_DB_PASSWORD"],
    )
