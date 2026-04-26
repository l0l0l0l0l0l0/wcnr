import os
from pymysql.cursors import DictCursor

DB2_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root_password"),
    "database": os.getenv("DB_NAME", "smart_platform"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
}
