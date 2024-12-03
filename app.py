# app.py

from flask import Flask
from model.db import database, init_app  # db 객체와 init_app을 가져옵니다.
import controller.apriori_controller

# Flask 애플리케이션 초기화
app = Flask(__name__)

# 데이터베이스 초기화
init_app(app)  # init_app 호출

# 블루프린트 등록
app.register_blueprint(controller.apriori_controller.apriori_blueprint)

if __name__ == '__main__':
    with app.app_context():
        database.create_all()  # 데이터베이스 테이블 생성
    app.run(debug=True)
