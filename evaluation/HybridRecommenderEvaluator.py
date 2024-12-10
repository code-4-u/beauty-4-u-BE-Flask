from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
import numpy as np
from collections import defaultdict
from surprise.model_selection import cross_validate
import pandas as pd

class HybridRecommenderEvaluator:
    def __init__(self, collabo_filter_service):
        self.service = collabo_filter_service

    # 데이터를 학습용과 평가용으로 분할
    def split_evaluation_data(self, ratings_df, test_size=0.2):
        return train_test_split(
            ratings_df,
            test_size=test_size,
            stratify=ratings_df['customer_code'],
            radom_state=42
        )
    
    # 기본 협업 필터링 예측의 정확도 평가
    def evaluate_base_predictions(self, test_data):
        true_ratings = []
        predicted_ratings = []

        for _, row in test_data.iterrows():
            pred = self.service.predict(
                row['customer_code'],
                row['goods_code'],
                row['review_score']
            )
            true_ratings.append(row['review_score'])
            predicted_ratings.append(pred.est)
        
        rmse = np.sqrt(mean_squared_error(true_ratings, predicted_ratings))
        mae = mean_absolute_error(true_ratings, predicted_ratings)
        
        return {
            'Base_RMSE': rmse,
            'Base_MAE': mae
        }
    
    # 가중치가 적용된 예측의 정확도 평가
    def evaluate_weighted_predictions(self, test_data, statis_data):
        weighted_errors = []
        skin_match_count = 0
        age_match_count = 0
        grade_match_count = 0

        for _, row in test_data.iterrows():
            # 기본 예측
            base_pred = self.service.predict(
                row['customer_code'],
                row['goods_code'],
                row['review_score']
            ).est
            
            # 가중치 적용된 예측 계산
            product_info = next(
                (item for item in statis_data if item['goods_code'] == row['goods_code']),
                None
            )
            
            if product_info:
                weighted_pred = base_pred
                
                # 피부타입 매칭 평가
                if row['customer_skintype'] == product_info['goods_skintype']:
                    weighted_pred += 0.5
                    skin_match_count += 1
                else:
                    weighted_pred += 0.1
                
                # 고객 등급 평가
                total_reviews = product_info['total']
                if total_reviews > 0:
                    high_grade_ratio = product_info['high_grade_count'] / total_reviews
                    if high_grade_ratio > 0.25:
                        weighted_pred += 0.3
                        grade_match_count += 1
                    else:
                        weighted_pred += 0.1
                
                # 연령대 매칭 평가
                if row['customer_age'] < 40:
                    young_ratio = product_info['young_count'] / total_reviews
                    if young_ratio > 0.6:
                        weighted_pred += 0.2
                        age_match_count += 1
                
                # 오차 계산
                weighted_errors.append(abs(weighted_pred - row['review_score']))
        
        total_predictions = len(test_data)
        
        return {
            'Weighted_MAE': np.mean(weighted_errors),
            'Skin_Type_Match_Rate': skin_match_count / total_predictions,
            'Age_Group_Match_Rate': age_match_count / total_predictions,
            'Grade_Match_Rate': grade_match_count / total_predictions
        }
    
    #추천의 다양성 평가
    def evaluate_recommendation_diversity(self, recommendations):
        unique_products = set()
        product_frequencies = defaultdict(int)
        
        for rec in recommendations:
            for prod_id, _ in rec['recommendations']:
                unique_products.add(prod_id)
                product_frequencies[prod_id] += 1
        
        total_recommendations = sum(len(rec['recommendations']) for rec in recommendations)
        
        # 카탈로그 커버리지
        coverage = len(unique_products) / len(self.service.goods_ids)
        
        # 추천 다양성 (지니 계수 사용)
        frequencies = np.array(list(product_frequencies.values()))
        gini = self._calculate_gini(frequencies)
        
        return {
            'Coverage': coverage,
            'Gini_Diversity': gini
        }
    
    def _calculate_gini(self, frequencies):
        frequencies = np.sort(frequencies)
        n = len(frequencies)
        index = np.arange(1, n + 1)
        return np.sum((2 * index - n - 1) * frequencies) / (n * np.sum(frequencies))
    
    def evaluate_system(self):
        # 데이터 로드
        reviews = self.service.load_review_data()
        statis = self.service.load_statis_data()
        processed_data = self.service.process_training_data(reviews)
        ratings_df = pd.DataFrame(processed_data)
        
        # 데이터 분할
        train_data, test_data = self.split_evaluation_data(ratings_df)
        
        # 모델 학습
        loaded_train_data = self.service.load_data(train_data)
        self.service.model = self.service.train_model(loaded_train_data)
        
        # 기본 예측 평가
        base_metrics = self.evaluate_base_predictions(test_data)
        
        # 가중치 적용된 예측 평가
        weighted_metrics = self.evaluate_weighted_predictions(test_data, statis)
        
        # 전체 추천 생성 및 평가
        recommendations = self.service.runningRecommend()
        diversity_metrics = self.evaluate_recommendation_diversity(recommendations)
        
        return {
            'base_metrics': base_metrics,
            'weighted_metrics': weighted_metrics,
            'diversity_metrics': diversity_metrics
        }
    
    def visualize_evaluation_results(evaluation_results):
        import matplotlib.pyplot as plt
        
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))

        # 기본 메트릭스 시각화
        metrics = [
            evaluation_results['base_metrics']['Base_RMSE'],
            evaluation_results['base_metrics']['Base_MAE'],
            evaluation_results['weighted_metrics']['Weighted_MAE']
        ]
        ax1.bar(['RMSE', 'Base MAE', 'Weighted MAE'], metrics)
        ax1.set_title('Error Metrics')

        # 매칭 비율 시각화
        matching_rates = [
            evaluation_results['weighted_metrics']['Skin_Type_Match_Rate'],
            evaluation_results['weighted_metrics']['Age_Group_Match_Rate'],
            evaluation_results['weighted_metrics']['Grade_Match_Rate']
        ]
        ax2.bar(['Skin Type', 'Age Group', 'Grade'], matching_rates)
        ax2.set_title('Matching Rates')

        # 다양성 메트릭스 시각화
        diversity = [
            evaluation_results['diversity_metrics']['Coverage'],
            evaluation_results['diversity_metrics']['Gini_Diversity']
        ]
        ax3.bar(['Coverage', 'Gini Diversity'], diversity)
        ax3.set_title('Diversity Metrics')
    
        plt.tight_layout()
        return fig