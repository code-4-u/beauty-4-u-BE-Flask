from flask import Blueprint, jsonify, request
from service.collaboFilter_service import CollaboFilterService
from evaluation.HybridRecommenderEvaluator import HybridRecommenderEvaluator
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split
import numpy as np

review_blueprint = Blueprint('review', __name__)

@review_blueprint.route('/collabo')
def recommendCollabo():
    service = CollaboFilterService()
    data = service.load_review_data()
    recommend = service.runningRecommend()
    results = [tuple(row) for row in data]
    return jsonify(results), 200

@review_blueprint.route('/collaboTest')
def testing():
    try:
        # 추천 서비스 인스턴스 생성
        recommender_service = CollaboFilterService()
        
        print("\n=== 추천 시스템 평가 시작 ===\n")
        
        # 데이터 로드
        reviews = recommender_service.load_review_data()
        statis = recommender_service.load_statis_data()
        processed_data = recommender_service.process_training_data(reviews)
        ratings_df = pd.DataFrame(processed_data)
        
        print("1. 데이터 통계:")
        print(f"총 리뷰 수: {len(ratings_df)}")
        print(f"고유 사용자 수: {ratings_df['customer_code'].nunique()}")
        print(f"고유 상품 수: {ratings_df['goods_code'].nunique()}")
        print(f"평균 평점: {ratings_df['review_score'].mean():.2f}")
        
        # 데이터 분할
        train_data, test_data = train_test_split(ratings_df, test_size=0.2, random_state=42)
        print(f"\n2. 데이터 분할: 학습 데이터 {len(train_data)}개, 테스트 데이터 {len(test_data)}개")
        
        # 모델 학습
        loaded_train_data = recommender_service.load_data(train_data)
        recommender_service.model = recommender_service.train_model(loaded_train_data)
        
        # 기본 예측 평가
        print("\n3. 기본 예측 평가:")
        true_ratings = []
        predicted_ratings = []
        
        for _, row in test_data.iterrows():
            pred = recommender_service.predict(
                row['customer_code'],
                row['goods_code'],
                row['review_score']
            )
            true_ratings.append(row['review_score'])
            predicted_ratings.append(pred.est)
        
        rmse = np.sqrt(mean_squared_error(true_ratings, predicted_ratings))
        mae = mean_absolute_error(true_ratings, predicted_ratings)
        
        print(f"RMSE: {rmse:.4f}")
        print(f"MAE: {mae:.4f}")
        
        # 가중치 평가
        print("\n4. 가중치 적용 평가:")
        recommendations = recommender_service.runningRecommend()
        
        total_recommendations = len(recommendations)
        unique_products = set()
        
        for rec in recommendations:
            for prod_id, _ in rec['recommendations']:
                unique_products.add(prod_id)
        
        coverage = len(unique_products) / ratings_df['goods_code'].nunique()
        print(f"추천 커버리지: {coverage:.2%}")
        print(f"평균 추천 수: {sum(len(rec['recommendations']) for rec in recommendations) / total_recommendations:.1f}")
        
        print("\n=== 평가 완료 ===")
        
        return "평가가 완료되었습니다. 콘솔을 확인해주세요."
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        return f"평가 중 오류가 발생했습니다: {str(e)}"
