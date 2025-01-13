from flask import Blueprint, request, jsonify
from .database import db, Harvester, NetworkScan
from functools import wraps
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "API key manquante"}), 401
            
        harvester = Harvester.query.filter_by(api_key=api_key).first()
        if not harvester:
            return jsonify({"error": "API key invalide"}), 401
            
        harvester.last_seen = datetime.utcnow()
        db.session.commit()

        return f(*args, **kwargs, harvester=harvester)
    return decorated

@api_bp.route('/harvesters', methods=['POST'])
def register_harvester():
    """Enregistre un nouveau harvester"""
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'client_name' not in data:
            return jsonify({"error": "Données manquantes (name et client_name requis)"}), 400

        harvester = Harvester(
            name=data['name'],
            client_name=data['client_name']
        )
        db.session.add(harvester)
        db.session.commit()

        return jsonify({
            'id': harvester.id,
            'api_key': harvester.api_key
        }), 201

    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du harvester: {str(e)}")
        return jsonify({"error": str(e)}), 400

@api_bp.route('/harvesters', methods=['GET'])
def list_harvesters():
    """List all registered harvesters"""
    try:
        harvesters = Harvester.query.all()
        return jsonify({
            "harvesters": [
                {
                    "id": h.id,
                    "name": h.name,
                    "last_seen": h.last_seen.isoformat() if h.last_seen else None
                } for h in harvesters
            ]
        })
    except Exception as e:
        logger.error(f"Error listing harvesters: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/scan', methods=['POST'])
@require_api_key
def receive_scan(harvester):
    """Reçoit les données de scan d'un harvester"""
    try:
        data = request.get_json()
        scan = NetworkScan(
            harvester_id=harvester.id,
            scan_data=data
        )
        scan.generate_summary()
        db.session.add(scan)
        db.session.commit()
        return jsonify({'status': 'success', 'scan_id': scan.id}), 200
    except Exception as e:
        logger.error(f"Erreur lors de la réception du scan: {str(e)}")
        return jsonify({"error": str(e)}), 400

@api_bp.route('/scans', methods=['GET'])
def list_scans():
    """List recent network scans"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        scans = NetworkScan.query.order_by(
            NetworkScan.timestamp.desc()
        ).paginate(page=page, per_page=per_page)
        
        return jsonify({
            "scans": [
                {
                    "id": scan.id,
                    "harvester_id": scan.harvester_id,
                    "timestamp": scan.timestamp.isoformat(),
                    "device_count": len(scan.scan_data)
                } for scan in scans.items
            ],
            "total": scans.total,
            "pages": scans.pages,
            "current_page": scans.page
        })
    except Exception as e:
        logger.error(f"Error listing scans: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/scan/<int:scan_id>', methods=['GET'])
def get_scan(scan_id):
    """Get details of a specific scan"""
    try:
        scan = NetworkScan.query.get_or_404(scan_id)
        return jsonify({
            "id": scan.id,
            "harvester_id": scan.harvester_id,
            "timestamp": scan.timestamp.isoformat(),
            "data": scan.scan_data
        })
    except Exception as e:
        logger.error(f"Error retrieving scan {scan_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Retourne les statistiques globales"""
    try:
        stats = {
            'harvester_count': Harvester.query.count(),
            'scan_count': NetworkScan.query.count(),
            'recent_scans': [
                {
                    'id': scan.id,
                    'timestamp': scan.timestamp.isoformat(),
                    'harvester': scan.harvester.name,
                    'client': scan.harvester.client_name
                }
                for scan in NetworkScan.query.order_by(NetworkScan.timestamp.desc()).limit(5)
            ]
        }
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des stats: {str(e)}")
        return jsonify({'error': str(e)}), 500
