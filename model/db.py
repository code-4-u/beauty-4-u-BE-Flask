# db.py

import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()  # 환경 변수 로드

database = SQLAlchemy()  # SQLAlchemy 객체를 생성

def init_app(app):
    """Flask 앱을 초기화하고 SQLAlchemy를 연결합니다."""
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+pymysql://{os.getenv('MARIADB_USER')}:{os.getenv('MARIADB_PASSWORD')}"
        f"@{os.getenv('MARIADB_HOST')}:{os.getenv('MARIADB_PORT')}/{os.getenv('MARIADB_DATABASE')}"
    )
    database.init_app(app)  # SQLAlchemy 초기화
