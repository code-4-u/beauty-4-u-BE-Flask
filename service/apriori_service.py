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
                print(f"Successfully created analysis with ID: {new_analysis.analysis_id}")
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
                    print(f"Successfully deleted analysis ID: {analysis_id}")
                    return True
                print(f"Analysis ID {analysis_id} not found")
                return False
            except Exception as e:
                print(f"An error occurred while deleting analysis: {e}")
                return False

    def get_top_category_by_goods_code(self, goods_code):
        with current_app.app_context():
            goods = Goods.query.filter_by(goods_code=goods_code).first()
            if goods:
                print(f"Found goods: {goods.goods_code} in sub_category: {goods.sub_category_code}")
                sub_category = SubCategory.query.filter_by(sub_category_code=goods.sub_category_code).first()
                if sub_category:
                    print(
                        f"Found sub_category: {sub_category.sub_category_code} in top_category: {sub_category.top_category_code}")
                    top_category = TopCategory.query.filter_by(
                        top_category_code=sub_category.top_category_code).first()
                    return top_category.top_category_code if top_category else None
            return None

    def recommend_all_combinations(self, target_goods_code_a, analysis_kind, analysis_title, analysis_description):
        with current_app.app_context():
            analysis_id = None
            try:
                # 1. 분석 생성
                print("\nStep 1: Creating analysis")
                analysis_id = self.create_analysis(analysis_kind, analysis_title, analysis_description)
                if analysis_id is None:
                    print("Failed to create analysis")
                    return None

                # 2. 타겟 상품의 카테고리 정보 가져오기
                print("\nStep 2: Getting target product category information")
                target_goods = Goods.query.filter_by(goods_code=target_goods_code_a).first()
                if not target_goods:
                    print(f"Target goods {target_goods_code_a} not found")
                    self.delete_analysis(analysis_id)  # 실패 시 analysis 삭제
                    return None

                print(f"Found target goods: {target_goods.goods_code}")
                print(f"Sub category code: {target_goods.sub_category_code}")

                target_sub_category = SubCategory.query.filter_by(
                    sub_category_code=target_goods.sub_category_code).first()
                if not target_sub_category:
                    print("Target sub category not found")
                    self.delete_analysis(analysis_id)  # 실패 시 analysis 삭제
                    return None

                target_top_category = TopCategory.query.filter_by(
                    top_category_code=target_sub_category.top_category_code).first()
                if not target_top_category:
                    print("Target top category not found")
                    self.delete_analysis(analysis_id)  # 실패 시 analysis 삭제
                    return None

                print(f"Target goods hierarchy:")
                print(f"- Top category: {target_top_category.top_category_code}")
                print(f"- Sub category: {target_sub_category.sub_category_code}")
                print(f"- Goods code: {target_goods.goods_code}")

                # 3. 같은 상위 카테고리, 다른 하위 카테고리의 상품 코드들 가져오기
                print("\nStep 3: Getting products in same top category")
                same_category_goods = []
                all_goods = Goods.query.join(SubCategory, Goods.sub_category_code == SubCategory.sub_category_code) \
                    .filter(SubCategory.top_category_code == target_top_category.top_category_code) \
                    .filter(Goods.sub_category_code != target_goods.sub_category_code) \
                    .all()

                for goods in all_goods:
                    if goods.goods_code != target_goods_code_a:
                        same_category_goods.append(goods.goods_code)

                if not same_category_goods:
                    print("No products found in same category")
                    self.delete_analysis(analysis_id)  # 실패 시 analysis 삭제
                    return None

                print(f"Found {len(same_category_goods)} products in same top category")
                print(f"Sample of found products: {same_category_goods[:5]}")

                # 4. 고객별 구매 데이터 가져오기
                print("\nStep 4: Getting purchase data")
                orders = OrderInfo.query.filter(
                    OrderInfo.order_status == 'PURCHASED',
                    OrderInfo.goods_code.in_([target_goods_code_a] + same_category_goods)
                ).all()

                if not orders:
                    print("No purchase data found")
                    self.delete_analysis(analysis_id)  # 실패 시 analysis 삭제
                    return None

                print(f"Total orders retrieved: {len(orders)}")
                print("Sample of first few orders:")
                for order in orders[:5]:
                    print(f"- Customer: {order.customer_code}, Goods: {order.goods_code}, Count: {order.order_count}")

                # 5. 고객별 구매 상품 집합 생성
                print("\nStep 5: Creating customer purchase sets")
                customer_sets = {}
                for order in orders:
                    if order.customer_code not in customer_sets:
                        customer_sets[order.customer_code] = set()
                    customer_sets[order.customer_code].add(order.goods_code)

                total_customers = len(customer_sets)
                print(f"Total unique customers: {total_customers}")
                print("Sample of customer purchase sets:")
                for customer_code, purchases in list(customer_sets.items())[:5]:
                    print(f"- Customer {customer_code}: {purchases}")

                # 6. 타겟 상품의 구매 고객 수 계산
                target_customers = sum(1 for goods_set in customer_sets.values()
                                       if target_goods_code_a in goods_set)

                if target_customers == 0:
                    print("No customers found for target product")
                    self.delete_analysis(analysis_id)  # 실패 시 analysis 삭제
                    return None

                print(f"\nTarget item statistics:")
                print(f"- Total customers in dataset: {total_customers}")
                print(f"- Customers who bought target item: {target_customers}")
                print(f"- Target item purchase rate: {(target_customers / total_customers) * 100:.2f}%")

                # 7. 연관성 분석
                print("\nStep 7: Performing association analysis")
                potential_recommendations = []

                # 완화된 조건들
                min_customer_count = 3  # 최소 3명 이상의 고객이 구매
                min_confidence = 0.05  # 최소 5% 이상의 신뢰도
                min_lift = 1.1  # 최소 1.1 이상의 리프트

                for item in same_category_goods:
                    try:
                        # 두 상품을 모두 구매한 고객 수 계산
                        co_occurrence = sum(1 for goods_set in customer_sets.values()
                                            if target_goods_code_a in goods_set and item in goods_set)

                        # 각 상품의 구매 고객 수 계산
                        item_customers = sum(1 for goods_set in customer_sets.values()
                                             if item in goods_set)

                        if item_customers > 0:  # 0으로 나누기 방지
                            # 지표 계산
                            support = (co_occurrence / total_customers)
                            confidence = (co_occurrence / target_customers)
                            lift = ((co_occurrence * total_customers) / (target_customers * item_customers))

                            print(f"\nAnalysis for item {item}:")
                            print(f"- Co-occurrence: {co_occurrence}")
                            print(f"- Item customers: {item_customers}")
                            print(f"- Support: {support:.4f}")
                            print(f"- Confidence: {confidence:.4f}")
                            print(f"- Lift: {lift:.4f}")

                            # 강화된 조건 적용
                            if (co_occurrence >= min_customer_count and
                                    confidence >= min_confidence and
                                    lift >= min_lift):
                                potential_recommendations.append({
                                    'item': item,
                                    'support': support,
                                    'confidence': confidence,
                                    'lift': lift,
                                    'co_occurrence': co_occurrence
                                })
                                print("-> Added to recommendations!")
                            else:
                                print("-> Skipped: did not meet strengthened criteria")
                        else:
                            print(f"-> Skipped item {item}: no customers")

                    except Exception as e:
                        print(f"Error processing item {item}: {str(e)}")
                        continue

                if not potential_recommendations:
                    print("No recommendations found that meet the criteria")
                    self.delete_analysis(analysis_id)  # 실패 시 analysis 삭제
                    return None

                # 8. 점수화 및 정렬
                print("\nStep 8: Scoring and sorting recommendations")
                recommendations = []
                sorted_recommendations = sorted(
                    potential_recommendations,
                    key=lambda x: (x['lift'], x['confidence'], x['support']),
                    reverse=True
                )

                print("\nFinal recommendations:")
                for idx, rec in enumerate(sorted_recommendations, 1):
                    print(f"\nRecommendation {idx}:")
                    print(f"- Item: {rec['item']}")
                    print(f"- Support: {rec['support']:.4f}")
                    print(f"- Confidence: {rec['confidence']:.4f}")
                    print(f"- Lift: {rec['lift']:.4f}")
                    print(f"- Co-occurrence: {rec['co_occurrence']}")

                    recommendation = AssociationRecommendation(
                        goods_code=target_goods_code_a,
                        associated_goods_code=rec['item'],
                        analysis_id=analysis_id,
                        support=float(rec['support']),
                        confidence=float(rec['confidence']),
                        lift=float(rec['lift'])
                    )
                    recommendations.append(recommendation)

                print(f"\nTotal recommendations generated: {len(recommendations)}")

                try:
                    db.session.add_all(recommendations)
                    db.session.commit()
                    print(f"Successfully saved all recommendations to database")
                    return analysis_id
                except Exception as e:
                    print(f"Error saving recommendations: {str(e)}")
                    db.session.rollback()
                    self.delete_analysis(analysis_id)  # DB 저장 실패 시에도 analysis 삭제
                    raise

            except Exception as e:
                print(f"An error occurred: {str(e)}")
                if analysis_id:
                    self.delete_analysis(analysis_id)  # 전체 예외 발생 시에도 analysis 삭제
                return None