# app.py

from dotenv import load_dotenv
from flask import Flask

import controller.apriori_controller
import controller.collaboFilter_controller
from model.db import init_app

from dotenv import load_dotenv
import os

# .env 파일 절대 경로로 지정
from pathlib import Path
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Flask 애플리케이션 초기화
app = Flask(__name__)

# 초기화
init_app(app)

# 블루프린트 등록
app.register_blueprint(controller.apriori_controller.apriori_blueprint)
app.register_blueprint(controller.collaboFilter_controller.review_blueprint)

if __name__ == '__main__':
    app.run(port=8000, debug=True)
