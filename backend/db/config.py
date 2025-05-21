# backend/db/config.py
import os

# 데이터베이스 설정
DB_CONFIG = {
    'host': 'localhost',
    'user': 'dael',
    'password': os.environ.get('DB_AM_PASSWORD'),
    'database': 'arielle',
    'port': 3306,
    'charset': 'utf8mb4'
}