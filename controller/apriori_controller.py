from flask import Blueprint, jsonify

from service.apriori_service import RecommendationService

apriori_blueprint = Blueprint('apriori', __name__)


# 조합 분석하기
@apriori_blueprint.route('/apriori', methods=['GET'])
def run_apriori():
    service = RecommendationService()
    recommend = service.recommend()
    return jsonify(recommend)
