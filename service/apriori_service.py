# service/recommendation_service.py

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from model.analysis import OrderInfo  # OrderInfo 모델 가져오기
from model.db import database  # db 객체 가져오기


class RecommendationService:
    def __init__(self):
        self.db = database  # SQLAlchemy 객체

    def recommend(self):
        try:
            # 앱 컨텍스트를 메서드 내에서 활성화
            with self.db.app.app_context():
                # 1. 주문 데이터 가져오기
                orders = OrderInfo.query.all()

                print(orders)

                if not orders:
                    return {}  # 데이터가 없을 경우 빈 결과 반환

                # 2. 데이터 전처리
                data = []
                for order in orders:
                    data.append({
                        'customer_code': order.customer_code,  # 고객 코드 추가
                        'goods_code': order.goods_code,
                        'order_count': order.order_count
                    })

                # DataFrame 생성
                df = pd.DataFrame(data)

                # 고객별로 구매한 상품을 거래 형식으로 변환
                basket = df.groupby(['customer_code', 'goods_code'])['order_count'].sum().unstack().reset_index().fillna(0)
                basket = basket.set_index('customer_code')

                # 0을 1로 변환 (상품 존재 여부)
                basket = basket.applymap(lambda x: 1 if x > 0 else 0)

                # 3. Apriori 알고리즘 적용
                frequent_itemsets = apriori(basket, min_support=0.01, use_colnames=True)
                rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.5)

                # 4. 추천 로직 구현
                recommendations = {}
                for index, row in rules.iterrows():
                    if row['antecedents']:  # 선행 조건이 있을 경우
                        for item in row['antecedents']:
                            if item not in recommendations:
                                recommendations[item] = set()  # 중복 방지를 위해 set 사용
                            recommendations[item].update(row['consequents'])  # set에 추가

                # set을 list로 변환하여 반환
                recommendations = {k: list(v) for k, v in recommendations.items()}

                return recommendations

        except Exception as e:
            print(f"An error occurred: {e}")
            return {}
