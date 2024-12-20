import pandas as pd
from flask import current_app
from mlxtend.frequent_patterns import apriori, association_rules

from model.analysis import Customer  # Customer 모델 가져오기
from model.analysis import OrderInfo, AssociationRecommendation, Analysis, Goods, SubCategory, TopCategory  # 모델 가져오기
from model.db import db  # SQLAlchemy 객체 가져오기


class RecommendationService:
    def __init__(self):
        self.db = db  # SQLAlchemy 객체

    def create_analysis(self, analysis_kind, analysis_title, analysis_description):
        with current_app.app_context():
            try:
                # 1. 새로운 분석 생성
                new_analysis = Analysis(
                    analysis_kind=analysis_kind,  # 분석 종류
                    analysis_title=analysis_title,  # 제목
                    analysis_description=analysis_description  # 설명
                )
                db.session.add(new_analysis)
                db.session.commit()

                return new_analysis.analysis_id  # 생성된 분석 ID 반환

            except Exception as e:
                print(f"An error occurred while creating analysis: {e}")
                return None

    def delete_analysis(self, analysis_id):
        with current_app.app_context():
            try:
                analysis = Analysis.query.get(analysis_id)
                if analysis:
                    db.session.delete(analysis)
                    db.session.commit()
                    return True
                return False
            except Exception as e:
                print(f"An error occurred while deleting analysis: {e}")
                return False

    def get_top_category_by_goods_code(self, goods_code):
        goods = Goods.query.filter_by(goods_code=goods_code).first()
        if goods:
            sub_category = SubCategory.query.filter_by(sub_category_code=goods.sub_category_code).first()
            if sub_category:
                top_category = TopCategory.query.filter_by(top_category_code=sub_category.top_category_code).first()
                return top_category.top_category_code if top_category else None
        return None

    def recommend_all_combinations(self, target_goods_code_a, customer_code, analysis_kind, analysis_title, analysis_description):
        with current_app.app_context():
            analysis_id = None
            try:
                # 1. 분석 생성
                analysis_id = self.create_analysis(analysis_kind, analysis_title, analysis_description)
                if analysis_id is None:
                    return {"message": "Failed to create analysis."}

                # 2. 주문 데이터 가져오기
                orders = OrderInfo.query.filter(OrderInfo.order_status == 'PURCHASED').all()

                if not orders:
                    return {}  # 데이터가 없을 경우 빈 결과 반환

                # 3. 데이터 전처리
                data = []
                for order in orders:
                    if order.order_count > 0:
                        customer = db.session.get(Customer, order.customer_code)  # 고객 정보 가져오기
                        data.append({
                            'customer_code': order.customer_code,
                            'goods_code': order.goods_code,
                            'order_count': order.order_count,
                            'skin_type': customer.customer_skintype  # 고객의 피부 타입 추가
                        })

                df = pd.DataFrame(data)

                # 고객-상품 이진 행렬 생성
                basket = df.pivot_table(index='customer_code', columns='goods_code', values='order_count', fill_value=0)
                basket_binary = (basket > 0).astype(int)

                # Apriori 알고리즘 적용
                frequent_itemsets = apriori(basket_binary, min_support=0.015, use_colnames=True)

                # num_itemsets 계산
                num_itemsets = frequent_itemsets.shape[0]

                # 연관 규칙 생성
                rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.5, num_itemsets=num_itemsets)

                # 타겟 상품의 top_category 가져오기
                target_top_category = self.get_top_category_by_goods_code(target_goods_code_a)

                # 상품 A와 모든 다른 상품 간의 조합 점수 계산
                recommendations = []
                for item in basket.columns:
                    if item != target_goods_code_a:  # 상품 A와 다른 상품만 비교
                        # 현재 상품의 top_category 가져오기
                        item_top_category = self.get_top_category_by_goods_code(item)

                        # 두 상품의 top_category가 같고, sub_category가 다른 경우
                        if item_top_category == target_top_category:
                            combination_rule = rules[
                                (rules['antecedents'].apply(lambda x: target_goods_code_a in x)) &
                                (rules['consequents'].apply(lambda x: item in x))
                            ]

                            if not combination_rule.empty:
                                support = combination_rule['support'].values[0]
                                confidence = combination_rule['confidence'].values[0]

                                # 향상도 계산
                                support_b = rules[rules['consequents'].apply(lambda x: item in x)]['support'].values[0]
                                lift = confidence / support_b if support_b > 0 else 0

                                # DB에 조합 추천 저장
                                recommendation = AssociationRecommendation(
                                    goods_code=target_goods_code_a,
                                    associated_goods_code=item,
                                    customer_code=customer_code,
                                    analysis_id=analysis_id,
                                    support=support,
                                    confidence=confidence,
                                    lift=lift  # 향상도 추가
                                )
                                recommendations.append(recommendation)

                # DB에 모든 추천 저장
                if recommendations:
                    db.session.add_all(recommendations)
                    db.session.commit()

                return {"message": "Recommendations calculated and saved.", "recommendations_count": len(recommendations)}

            except Exception as e:
                print(f"An error occurred: {e}")
                # 분석 삭제
                if analysis_id:
                    self.delete_analysis(analysis_id)
                return {"message": "An error occurred during analysis, and the created analysis has been deleted."}

