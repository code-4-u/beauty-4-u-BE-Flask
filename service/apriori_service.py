import pandas as pd
from flask import current_app
from mlxtend.frequent_patterns import apriori, association_rules

from model.analysis import OrderInfo, AssociationRecommendation, Analysis, Goods, SubCategory, TopCategory
from model.db import db


class RecommendationService:
    def __init__(self):
        self.db = db

    def create_analysis(self, analysis_kind, analysis_title, analysis_description):
        with current_app.app_context():
            try:
                new_analysis = Analysis(
                    analysis_kind=analysis_kind,
                    analysis_title=analysis_title,
                    analysis_description=analysis_description
                )
                db.session.add(new_analysis)
                db.session.commit()

                return new_analysis.analysis_id

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

    def get_top_category_by_goods_code(self, goods_code):
        with current_app.app_context():
            goods = Goods.query.filter_by(goods_code=goods_code).first()
            if goods:
                sub_category = SubCategory.query.filter_by(sub_category_code=goods.sub_category_code).first()
                if sub_category:
                    top_category = TopCategory.query.filter_by(top_category_code=sub_category.top_category_code).first()
                    return top_category.top_category_code if top_category else None
            return None

    def recommend_all_combinations(self, target_goods_code_a, analysis_kind, analysis_title, analysis_description):
        with current_app.app_context():
            analysis_id = None
            try:
                # 1. 분석 생성
                analysis_id = self.create_analysis(analysis_kind, analysis_title, analysis_description)
                if analysis_id is None:
                    return {"message": "Failed to create analysis."}

                # 2. 타겟 상품의 카테고리 정보 가져오기
                target_goods = Goods.query.filter_by(goods_code=target_goods_code_a).first()
                if not target_goods:
                    return {"message": "Target goods not found"}

                target_sub_category = SubCategory.query.filter_by(
                    sub_category_code=target_goods.sub_category_code).first()
                if not target_sub_category:
                    return {"message": "Target subcategory not found"}

                target_top_category = TopCategory.query.filter_by(
                    top_category_code=target_sub_category.top_category_code).first()
                if not target_top_category:
                    return {"message": "Target top category not found"}

                print(f"Target goods top category: {target_top_category.top_category_code}")
                print(f"Target goods sub category: {target_sub_category.sub_category_code}")

                # 3. 같은 상위 카테고리, 다른 하위 카테고리의 상품 코드들 가져오기
                same_category_goods = []
                all_goods = Goods.query.join(SubCategory, Goods.sub_category_code == SubCategory.sub_category_code) \
                    .filter(SubCategory.top_category_code == target_top_category.top_category_code) \
                    .filter(Goods.sub_category_code != target_goods.sub_category_code) \
                    .all()

                for goods in all_goods:
                    if goods.goods_code != target_goods_code_a:
                        same_category_goods.append(goods.goods_code)

                if not same_category_goods:
                    return {"message": "No other products found in the same top category with different subcategories"}

                print(f"Found {len(same_category_goods)} products in same top category but different subcategories")

                # 4. 고객별 구매 데이터 가져오기
                orders = OrderInfo.query.filter(
                    OrderInfo.order_status == 'PURCHASED',
                    OrderInfo.goods_code.in_([target_goods_code_a] + same_category_goods)
                ).all()

                if not orders:
                    return {"message": "No orders found for the relevant products"}

                # 5. 고객별 구매 상품 집합 생성
                customer_sets = {}
                for order in orders:
                    if order.order_count > 0:
                        if order.customer_code not in customer_sets:
                            customer_sets[order.customer_code] = set()
                        customer_sets[order.customer_code].add(order.goods_code)

                total_customers = len(customer_sets)
                print(f"Processed {total_customers} customers who purchased relevant products")

                # 6. 타겟 상품의 구매 고객 수 계산
                target_customers = sum(1 for goods_set in customer_sets.values()
                                       if target_goods_code_a in goods_set)

                if target_customers == 0:
                    return {"message": "Target item has no customers"}

                print(f"Target item purchased by {target_customers} customers")

                # 7. 연관성 분석
                potential_recommendations = []
                min_customer_count = 1  # 최소 1명 이상의 고객이 구매

                for item in same_category_goods:
                    try:
                        # 두 상품을 모두 구매한 고객 수 계산
                        co_occurrence = sum(1 for goods_set in customer_sets.values()
                                            if target_goods_code_a in goods_set and item in goods_set)

                        if co_occurrence >= min_customer_count:
                            # 각 상품의 구매 고객 수 계산
                            item_customers = sum(1 for goods_set in customer_sets.values()
                                                 if item in goods_set)

                            if item_customers > 0:
                                # 지표 계산
                                support = co_occurrence / total_customers
                                confidence = co_occurrence / target_customers
                                lift = (co_occurrence * total_customers) / (target_customers * item_customers)

                                # 연관성이 있는 경우만 포함
                                if lift > 0.2:  # lift가 1보다 크면 양의 연관성이 있음
                                    potential_recommendations.append({
                                        'item': item,
                                        'support': support,
                                        'confidence': confidence,
                                        'lift': lift,
                                        'co_occurrence': co_occurrence
                                    })
                                    print(f"Found potential association with item {item}: "
                                          f"support={support:.4f}, confidence={confidence:.4f}, "
                                          f"lift={lift:.4f}, co_purchase_customers={co_occurrence}")

                    except Exception as e:
                        print(f"Error processing item {item}: {str(e)}")
                        continue

                if not potential_recommendations:
                    return {
                        "message": f"No associations found for target item (purchased by {target_customers} customers)"}

                # 8. 점수화 및 정렬
                recommendations = []
                sorted_recommendations = sorted(
                    potential_recommendations,
                    key=lambda x: (x['lift'], x['confidence'], x['support']),
                    reverse=True
                )

                # 모든 유효한 추천 저장
                for rec in sorted_recommendations:
                    recommendation = AssociationRecommendation(
                        goods_code=target_goods_code_a,
                        associated_goods_code=rec['item'],
                        analysis_id=analysis_id,
                        support=float(rec['support']),
                        confidence=float(rec['confidence']),
                        lift=float(rec['lift'])
                    )
                    recommendations.append(recommendation)

                print(f"Generated {len(recommendations)} recommendations")

                try:
                    db.session.add_all(recommendations)
                    db.session.commit()
                    return {
                        "message": "Recommendations calculated and saved.",
                        "recommendations_count": len(recommendations),
                        "analysis_id": analysis_id
                    }
                except Exception as e:
                    print(f"Error saving recommendations: {str(e)}")
                    db.session.rollback()
                    raise

            except Exception as e:
                print(f"An error occurred: {str(e)}")
                if analysis_id:
                    self.delete_analysis(analysis_id)
                return {"message": f"An error occurred during analysis: {str(e)}"}