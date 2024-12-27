from flask import Blueprint, request, jsonify
from service.apriori_service import RecommendationService  # RecommendationService 임포트

apriori_blueprint = Blueprint('apriori', __name__)

# 조합 분석하기
@apriori_blueprint.route('/apriori', methods=['POST'])
def run_apriori():
    data = request.json
    target_goods_code_a = data.get('goodsCode')
    analysis_kind = data.get('analysisKind', 'ASSOCIATION')
    analysis_title = data.get('analysisTitle', 'Product Association Analysis')
    analysis_description = data.get('analysisDescription', 'Analyzing product associations for recommendations.')

    print(f"Received request with goods_code: {target_goods_code_a}")  # 로그 추가

    if not target_goods_code_a:
        return jsonify({"message": "Missing required parameter: goods_code."}), 400

    try:
        service = RecommendationService()
        analysis_id = service.recommend_all_combinations(target_goods_code_a, analysis_kind, analysis_title,
                                                         analysis_description)

        print(f"Returned analysis_id: {analysis_id}")  # 로그 추가

        if analysis_id is None:
            return jsonify({
                "message": "Failed to create analysis. Please check if the goods_code exists and has valid purchase data."
            }), 400

        return jsonify({
            "analysis_id": analysis_id
        }), 200

    except Exception as e:
        print(f"Error in run_apriori: {str(e)}")  # 로그 추가
        return jsonify({
            "message": str(e)
        }), 500