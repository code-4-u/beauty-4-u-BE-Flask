import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

db = SQLAlchemy()

def init_app(app):
    """Flask 앱 초기화 및 SQLAlchemy 설정."""
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+pymysql://{os.getenv('MARIADB_USER')}:{os.getenv('MARIADB_PASSWORD')}"
        f"@{os.getenv('MARIADB_HOST')}:{os.getenv('MARIADB_PORT')}/{os.getenv('MARIADB_DATABASE')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)