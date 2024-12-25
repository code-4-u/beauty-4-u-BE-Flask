from flask import Blueprint, request, jsonify
from service.apriori_service import RecommendationService  # RecommendationService 임포트

apriori_blueprint = Blueprint('apriori', __name__)

# 조합 분석하기
@apriori_blueprint.route('/apriori', methods=['POST'])
def run_apriori():
    data = request.json  # JSON 형식의 요청 본문 받기
    target_goods_code_a = data.get('goods_code')  # 요청 본문에서 상품 코드 가져오기
    analysis_kind = data.get('analysis_kind', 'ASSOCIATION')  # 기본값 설정
    analysis_title = data.get('analysis_title', 'Product Association Analysis')  # 기본값 설정
    analysis_description = data.get('analysis_description', 'Analyzing product associations for recommendations.')  # 기본값 설정

    if not target_goods_code_a:  # customer_code 관련 조건 제거
        return jsonify({"message": "Missing required parameter: goods_code."}), 400

    service = RecommendationService()  # RecommendationService 클래스의 인스턴스 생성
    # customer_code 인자 제거
    result = service.recommend_all_combinations(target_goods_code_a, analysis_kind, analysis_title, analysis_description)

    return jsonify(result), 200