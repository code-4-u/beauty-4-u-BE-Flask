# analysis.py

from sqlalchemy import Enum as SqlAlchemyEnum, ForeignKey
from datetime import datetime  # datetime 모듈 임포트
from model.db import db  # db 객체를 가져옵니다.

from model.enums import AnalysisKind, CustomerGender, CustomerGrade, OrderState


# 분석 entity
class Analysis(db.Model):
    __tablename__ = 'analysis'

    analysis_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    analysis_kind = db.Column(SqlAlchemyEnum(AnalysisKind), nullable=False)
    analysis_title = db.Column(db.String(128))
    analysis_description = db.Column(db.String(256))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)  # 기본값 설정

# 고객 entity
class Customer(db.Model):
    __tablename__ = 'customer'

    customer_code = db.Column(db.String(20), primary_key=True)
    customer_name = db.Column(db.String(20), nullable=False)
    customer_email = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_age = db.Column(db.Integer, nullable=False)
    customer_gender = db.Column(SqlAlchemyEnum(CustomerGender), nullable=False)
    customer_skintype = db.Column(db.String(20), nullable=False)
    customer_grade = db.Column(SqlAlchemyEnum(CustomerGrade), nullable=False)
    created_date = db.Column(db.DateTime, nullable=True)
    updated_date = db.Column(db.DateTime, nullable=True)
    privacy_consent_yn = db.Column(db.String(1), nullable=False)

# 주문 entity
class OrderInfo(db.Model):
    __tablename__ = 'order_info'

    order_id = db.Column(db.Integer, primary_key=True)
    customer_code = db.Column(db.String(20), db.ForeignKey('customer.customer_code'), nullable=False)
    goods_code = db.Column(db.String(20), db.ForeignKey('goods.goods_code'), nullable=False)
    order_count = db.Column(db.Integer, nullable=False)
    order_price = db.Column(db.Integer, nullable=False)
    order_status = db.Column(SqlAlchemyEnum(OrderState), nullable=False)
    created_date = db.Column(db.DateTime, nullable=False)

# 상품 entity
class Goods(db.Model):
    __tablename__ = 'goods'

    goods_code = db.Column(db.String(20), primary_key=True)
    brand_code = db.Column(db.String(20), db.ForeignKey('brand.brand_code'), nullable=False)
    sub_category_code = db.Column(db.String(20), db.ForeignKey('sub_category.sub_category_code'), nullable=False)
    goods_name = db.Column(db.String(50), nullable=False)
    goods_price = db.Column(db.Integer, nullable=False)
    goods_skintype = db.Column(db.String(20), nullable=False)
    created_date = db.Column(db.DateTime, nullable=False)

# association_recommendation 엔티티
class AssociationRecommendation(db.Model):
    __tablename__ = 'association_recommendation'

    association_recommendation_id = db.Column(db.Integer, primary_key=True)
    goods_code = db.Column(db.String(20), db.ForeignKey('goods.goods_code'), nullable=False)
    associated_goods_code = db.Column(db.String(20), db.ForeignKey('goods.goods_code'), nullable=False)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analysis.analysis_id'), nullable=False)
    support = db.Column(db.Integer, nullable=False)
    confidence = db.Column(db.Integer, nullable=False)
    lift = db.Column(db.Integer, nullable=False)
    last_noti_sent_date = db.Column(db.DateTime, nullable=True)

class TopCategory(db.Model):
    __tablename__ = 'top_category'

    top_category_code = db.Column(db.String(20), primary_key=True)
    top_category_name = db.Column(db.String(50), nullable=False)


class SubCategory(db.Model):
    __tablename__ = 'sub_category'

    sub_category_code = db.Column(db.String(20), primary_key=True)
    top_category_code = db.Column(db.String(20), db.ForeignKey('top_category.top_category_code'), nullable=False)
    sub_category_name = db.Column(db.String(50), nullable=False)

class Review(db.Model):
    __tablename__ = 'review'

    review_id = db.Column(db.Integer, primary_key=True)
    customer_code = db.Column(db.String(20), db.ForeignKey('customer.customer_code'), nullable=False)
    goods_code = db.Column(db.String(20), db.ForeignKey('goods.goods_code'), nullable=False)
    review_score = db.Column(db.Integer, nullable=False)
    review_content = db.Column(db.Text, nullable=False)
    created_date = db.Column(db.DateTime, nullable=False)

    # personalized_recommendation 엔티티
class PersonalizedRecommendation(db.Model):
    __tablename__ = 'personalized_recommendation'
    personalized_recommendation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # autoincrement 추가
    customer_code = db.Column(db.String(20), db.ForeignKey('customer.customer_code'), nullable=False)
    goods_code = db.Column(db.String(20), db.ForeignKey('goods.goods_code'),nullable=False)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analysis.analysis_id'), nullable=False)
    recommendation_score = db.Column(db.Float, nullable=False)
    last_noti_sent_date = db.Column(db.DateTime, nullable=True)