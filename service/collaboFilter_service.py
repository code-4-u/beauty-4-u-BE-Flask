import pandas as pd
from flask import current_app, jsonify
from surprise import Dataset, Reader, SVD
from surprise.model_selection import train_test_split
from model.analysis import Customer  # Customer 모델 가져오기
from model.analysis import OrderInfo, Analysis, Goods, SubCategory, TopCategory, Review  # 모델 가져오기
from model.analysis import PersonalizedRecommendation
from model.db import db  # SQLAlchemy 객체 가져오기
from collections import defaultdict  
from sqlalchemy import cast, String, func, case  # 추가

class CollaboFilterService:
    def __init__(self):
        self.db = db
        self.model = None

    def predict(self, user_id, product_id, review_score):
        prediction = self.model.predict(user_id, product_id, review_score)
        return prediction

    #데이터 로드 함수
    def load_data(self, ratings_df):
        reader = Reader(rating_scale=(1, 5))

        # DataFrame를 Surprise 라이브러리가 사용할 수 있는 형태로 전환
        data = Dataset.load_from_df(ratings_df[['customer_code', 'goods_code', 'review_score']], reader)
        return data

    # 모델 학습 함수
    def train_model(self, data):
        trainset = data.build_full_trainset() # 전체 데이터 셋을 학습용으로 변환
        model = SVD(n_factors=50, lr_all=0.005, reg_all=0.02) # SVD 알고리즘 사용, 100개의 잠재 요인
        model.fit(trainset) # 모델 학습
        return model

    # 추천 생성 함수
    def get_recommendations(model, customer_code, customer_age, customer_skintype, goods_ids, review_scores, buyandreviewData, n_recommendations=3):
        product_predictions = defaultdict(list)
        # 각 제품에 대해 예상 평점 계산
        # 평점 총 0 ~ 5점, 그외 가중치 총합 1점 총 6점으로 평가 (해당하지 않을 경우 가산점 부여를 안함.)
        # 1점의 가산점 구성 
        # 0.5점 : 고객의 피부 타입과 제품의 피부타입에 따른 점수 
        # (피부 타입 100% 일치 0.5점 가산점 부여, 불일치 20% 0.1점 부여)
        # 0.3점 : 제품의 리뷰를 작성한 고객의 등급에 따른 제품에 대한 가산점 부여
        # (GOLD, BLACK등급의 고객이 많이 작성한 제품일 경우 0.2 점 가산점 부여) 아닌 경우 그린,핑크, 베이비 일때 0.1 점 부여)
        # 0.2 점 : 연령에 따른 점수 (제품의 리뷰를 보았을때 40대 미만의 고객이 리뷰를 많이 남긴 제품일 경우 0.2점 부여)
        # 도합 만점 6점.
        # goods_code 기준으로 딕셔너리 변환
        result_dict = {item['goods_code']: item for item in buyandreviewData}

        for product_id, review_score in zip(goods_ids, review_scores):
            # 기본 예측
            predicted_rating = model.predict(customer_code, product_id, review_score).est

            # 후 가중치 계산
            final_score = predicted_rating

            # 상품코드 기준으로 딕셔너리 생성
            reviewdata_info = result_dict.get(product_id, {})

            # 고객 피부 타입에 따른 가산점 부여
            if customer_skintype == reviewdata_info.get('goods_skintype', 0):
                final_score += 0.5
            else:
                final_score += 0.1

            # 고등급 고객의 리뷰 비율 25% 이상일 경우 가산점 부여
            high_grade_count = reviewdata_info.get('high_grade_count', 0)
            total_reviews = reviewdata_info.get('total', 0)

            if (high_grade_count / total_reviews) > 0.25:
                final_score += 0.3
            else:
                final_score += 0.1

            # 제품의 리뷰 남긴 고객의 나이대가 고객이 속한 나이대의 비율 60% 이상 (40세 미만, 40세 이상 구별)
            young_count = reviewdata_info.get('young_count', 0)
            old_count = reviewdata_info.get('old_count', 0)

            if customer_age < 40 :
                if (young_count / total_reviews) > 0.6 :
                    final_score += 0.2

            # 계산 후 배열에 추가
            product_predictions[product_id].append(round(final_score, 3))

        average_predictions = [
            (product_id, sum(ratings)/len(ratings))
            for product_id, ratings in product_predictions.items()
        ]
        # 예상 평점이 높은 순으로 정렬
        recommendations = sorted(average_predictions, key=lambda x: x[1], reverse=True)[:n_recommendations]
        return recommendations
    
    #고객별이므로 요청된 고객의 id 값으로 고객의 나이, 스킨 타입, 고객 등급을 조회한다.
    def load_customer_data(self):
        try:
            customer_data = self.db.session.query(
                Customer.customer_code,
                Customer.customer_age,
                Customer.customer_skintype,
                cast(Customer.customer_grade, String)
            )
            
            process = pd.DataFrame(list(customer_data), columns=['customer_code',
                                                                 'customer_age',
                                                                 'customer_skintype',
                                                                 'customer_grade'])
            result = process.to_dict('records')
            return result
        except Exception as e:
            f'DB 정보를 불러오는데 실패했습니다. 에러코드 : {e}'


    def load_statis_data(self):
        try:
            j1_subquery = self.db.session.query(
                Customer.customer_code,
                Customer.customer_age,
                Customer.customer_grade,
                Review.goods_code,
                Goods.goods_name,
                Goods.goods_skintype,
                Review.review_score
            ).join(
                Goods,
                (Goods.goods_code == Review.goods_code) 
            ).join(
                Customer,
                (Customer.customer_code == Review.customer_code)
            ).subquery('j1')

            data = self.db.session.query(
                j1_subquery.c.goods_code,
                Goods.goods_skintype,
                func.count(
                    case(
                        (Customer.customer_grade.in_(['GOLD', 'BLACK']), 1),
                        else_=None
                    )
                ).label('high_grade_count'),
                func.count(
                    case(
                        (Customer.customer_grade.in_(['GREEN', 'PINK', 'BABY']), 1),
                        else_=None
                    )
                ).label('other_grade_count'),
                func.count(
                    case(
                    (Customer.customer_age.between(10, 19), 1),
                    else_=None
                    )
                ).label('age_10s_count'),
                func.count(
                    case(
                    (Customer.customer_age.between(20, 29), 1),
                    else_=None
                    )
                ).label('age_20s_count'),
                func.count(
                    case(
                    (Customer.customer_age.between(30, 39), 1),
                    else_=None
                    )
                ).label('age_30s_count'),
                func.count(
                    case(
                    (Customer.customer_age.between(40, 49), 1),
                    else_=None
                    )
                ).label('age_40s_count'),
                func.count(
                    case(
                    (Customer.customer_age.between(50, 59), 1),
                    else_=None
                    )
                ).label('age_50s_count'),
                func.count(
                    case(
                    (Customer.customer_age >= 60, 1),
                    else_=None
                    )
                ).label('age_60s_plus_count'),
                func.count(
                    case(
                        (Customer.customer_age < 40, 1),
                        else_=None
                    )
                ).label('young_count'),
                func.count(
                    case(
                        (Customer.customer_age >= 40, 1),
                        else_=None
                    )
                ).label('old_count'),
                func.count(j1_subquery.c.review_score).label('total')
            ).join(
                Customer, 
                j1_subquery.c.customer_code == Customer.customer_code
            ).join(
                Goods,
                j1_subquery.c.goods_code == Goods.goods_code
            ).group_by(j1_subquery.c.goods_code, Goods.goods_name)

            process = pd.DataFrame(list(data), columns=['goods_code',
                                                        'goods_skintype',
                                                        'high_grade_count',
                                                        'other_grade_count',
                                                        'age_10s_count',
                                                        'age_20s_count',
                                                        'age_30s_count',
                                                        'age_40s_count',
                                                        'age_50s_count',
                                                        'age_60s_plus_count',
                                                        'young_count', 
                                                        'old_count', 
                                                        'total'])
            result = process.to_dict('records')
            return result
        except Exception as e:
            return f'load_statis_data DB 정보를 불러오는데 실패했습니다. 에러코드 : {e}'

    # DB - 리뷰데이터 조회
    def load_review_data(self):
        try:
            # Review 테이블에서 최신순으로 1만개만 조회하는 서브쿼리 생성
            latest_reviews = self.db.session.query(Review).order_by(Review.created_date.desc()).limit(2000).subquery()

            data = self.db.session.query(
                Customer.customer_code,
                Customer.customer_age,
                Customer.customer_grade,
                latest_reviews.c.goods_code,
                Goods.goods_name,
                Goods.goods_skintype,
                latest_reviews.c.review_score
            ).join(
                latest_reviews,
                Goods.goods_code == latest_reviews.c.goods_code
            ).join(
                Customer,
                latest_reviews.c.customer_code == Customer.customer_code
            )

            process = pd.DataFrame(list(data), columns=['customer_code',
                                                        'customer_age',
                                                        'customer_grade',
                                                        'goods_code', 
                                                        'goods_name', 
                                                        'goods_skintype',
                                                        'review_score'])
            
            # 데이터 확인 로그
            print("\n=== 데이터 로딩 결과 ===")
            print(f"총 로드된 리뷰 수: {len(process)}")

            result = process.to_dict('records')
            return result
        except Exception as e:
            return f'DB 정보를 불러오는데 실패했습니다. 에러코드 : {e}'
        
    # SVD에 넣기 위해 데이터 가공    
    def process_training_data(self, result):

        process = pd.DataFrame(result, columns=['customer_code',
                                                'goods_code', 
                                                'goods_name', 
                                                'goods_skintype', 
                                                'review_score'])
        # load_data 에 넘겨줄 딕셔너리 생성
        input_training = {
            'customer_code' : process['customer_code'].tolist(),
            'goods_code' : process['goods_code'].tolist(),
            'goods_name' : process['goods_name'].tolist(),
            'goods_skintype' : process['goods_skintype'].tolist(),
            'review_score' : process['review_score'].tolist()
        }

        return input_training
    
    # 추천 실행
    def runningRecommend(self):
        # 리뷰 데이터 조회
        reviews = self.load_review_data()

        # 고객 데이터 조회
        customers = self.load_customer_data()

        # 리뷰 통계 데이터 조회
        statis = self.load_statis_data()

        # 데이터 가공 
        processData = self.process_training_data(reviews)

        # DataFrame 으로 전환
        recommend_df = pd.DataFrame(processData)

        goods_ids = recommend_df['goods_code'].tolist()
        review_scores = recommend_df['review_score'].tolist()

        loaded_data = self.load_data(recommend_df)

        self.model = self.train_model(loaded_data)

        all_recommends = []

        for customer in customers :
            customer_code = customer['customer_code']
            customer_age = customer['customer_age']
            customer_skintype = customer['customer_skintype']

            recommendations = self.get_recommendations(customer_code, customer_age, customer_skintype, goods_ids, review_scores, statis)

            all_recommends.append({
                'customer_code' : customer_code,
                'recommendations' : recommendations
            })

        # 고객 개인별 Id, 나이, 피부타입, 등급, 상품 목록, 리뷰 점수, 리뷰데이터에 대한 통계 데이터
        return all_recommends
    
    def create_analysis(self, analysis_kind, analysis_title, analysis_description):
        try:
            new_analysis = Analysis(
                analysis_kind = analysis_kind,
                analysis_title = analysis_title,
                analysis_description = analysis_description,
                created_date = func.now()
            )

            db.session.add(new_analysis)
            db.session.commit()

            return new_analysis.analysis_id  # 생성된 분석 ID 반환
        except Exception as e:
            print(f"An error occurred while creating analysis: {e}")
        return None
    
    def delete_analysis(self, analysis_id):
        try:
            analysis = Analysis.query.get(analysis_id)
            if analysis:
                db.session.delete(analysis)
                db.session.commit()
                return True
            return False
        except Exception as e:
            print(f"An error occurred while creating analysis: {e}")
            return False
        
    def save_recommendation(self, all_recommends, analysis_id): 
        personalized_recommendations = []
        # 리스트의 각 요소(딕셔너리)에 접근
        for recommendation in all_recommends:
            customer_code = recommendation['customer_code']
            goods_code, score = recommendation['recommendations'][0]
            personalized = PersonalizedRecommendation(
                customer_code = customer_code,
                goods_code = goods_code,
                analysis_id = analysis_id,
                recommendation_score = score
            )
            personalized_recommendations.append(personalized)
        
        db.session.bulk_save_objects(personalized_recommendations)
        db.session.commit()
