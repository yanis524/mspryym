from flask import Flask, request, jsonify, render_template, flash, redirect, url_for
from modules.database import db, Harvester, NetworkScan
from sqlalchemy.sql import func
import logging
import os
from datetime import datetime, timedelta
import requests
from sqlalchemy import func
import uuid
import time

def create_app():
    app = Flask(__name__)
    
    # Configuration de la base de données
    base_dir = os.path.abspath(os.path.dirname(__file__))
    instance_dir = os.path.join(base_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_dir, "seahawks.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev-key-123'  # Clé secrète pour les sessions et messages flash
    app.config['DEBUG'] = True  # Active le mode debug
    
    # Configuration du logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('app')
    
    # Initialisation de la base de données
    db.init_app(app)
    with app.app_context():
        db.create_all()
        logger.info("Base de données initialisée")
    
    # Configuration des dossiers
    app.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    app.static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    
    logger.info(f"Dossier des templates: {app.template_folder}")
    logger.info(f"Dossier static: {app.static_folder}")
    logger.info(f"Dossier instance: {app.instance_path}")
    
    return app

app = create_app()

# Ajouter le filtre format_datetime
@app.template_filter('format_datetime')
def format_datetime(value):
    if value is None:
        return ""
    return value.strftime('%Y-%m-%d %H:%M:%S')

def get_harvester_from_request():
    """Récupère la sonde à partir de l'API key"""
    api_key = request.headers.get('X-API-Key')
    app.logger.info(f"Tentative de récupération de la sonde avec la clé : {api_key}")
    
    if not api_key:
        app.logger.error("Pas de clé API fournie dans les headers")
        return None
        
    harvester = Harvester.query.filter_by(api_key=api_key).first()
    if not harvester:
        app.logger.error(f"Aucune sonde trouvée avec la clé API : {api_key}")
    else:
        app.logger.info(f"Sonde trouvée : {harvester.name}")
    
    return harvester

@app.route('/')
def index():
    """Page d'accueil avec statistiques"""
    # Compter les sondes actives
    active_harvesters = Harvester.query.filter_by(status='connected').count()
    
    # Compter les réseaux uniques
    networks_count = db.session.query(db.func.count(db.distinct(NetworkScan.network))).scalar()
    
    # Compter le total des appareils détectés
    devices_count = db.session.query(db.func.sum(NetworkScan.total_devices)).scalar() or 0
    
    return render_template('index.html', 
                         active_harvesters=active_harvesters,
                         networks_count=networks_count,
                         devices_count=devices_count)

@app.route('/harvesters')
def harvesters():
    """Liste des sondes organisées par client"""
    all_harvesters = Harvester.query.all()
    
    # Mettre à jour le statut de toutes les sondes
    for harvester in all_harvesters:
        harvester.update_status()
    db.session.commit()
    
    # Organiser les sondes par client
    harvesters_by_client = {}
    for harvester in all_harvesters:
        if harvester.client_name not in harvesters_by_client:
            harvesters_by_client[harvester.client_name] = []
        harvesters_by_client[harvester.client_name].append(harvester)
    
    return render_template('harvesters.html', 
                         clients=sorted(harvesters_by_client.keys()),
                         harvesters=harvesters_by_client)

@app.route('/harvester/<int:harvester_id>')
def harvester_dashboard(harvester_id):
    """Afficher le dashboard d'une sonde"""
    try:
        harvester = Harvester.query.get_or_404(harvester_id)
        
        # Récupérer les scans de la sonde
        scans = NetworkScan.query.filter_by(harvester_id=harvester_id)\
            .order_by(NetworkScan.timestamp.desc())\
            .all()
        
        # Calculer les statistiques
        total_networks = db.session.query(func.count(func.distinct(NetworkScan.network)))\
            .filter_by(harvester_id=harvester_id).scalar() or 0
            
        total_devices = db.session.query(func.sum(NetworkScan.total_devices))\
            .filter_by(harvester_id=harvester_id).scalar() or 0
            
        total_ports = db.session.query(func.sum(NetworkScan.total_ports))\
            .filter_by(harvester_id=harvester_id).scalar() or 0

        return render_template('harvester.html',
                            harvester=harvester,
                            scans=scans,
                            networks=total_networks,
                            total_devices=total_devices,
                            total_ports=total_ports)
    except Exception as e:
        app.logger.error(f"Erreur lors de l'affichage du dashboard: {str(e)}")
        flash('Une erreur est survenue lors de l\'affichage du dashboard', 'error')
        return redirect(url_for('harvesters'))

@app.route('/api/harvesters', methods=['POST'])
def add_harvester():
    """Ajout d'une nouvelle sonde via l'interface web"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON manquantes'}), 400
            
        client_name = data.get('client_name')
        if not client_name:
            return jsonify({'error': 'Le nom du client est requis'}), 400
            
        # Générer un nom d'hôte unique basé sur le nom du client
        hostname = f"harvester_{client_name.lower().replace(' ', '_')}_{str(uuid.uuid4())[:8]}"
        
        # Générer une clé API unique
        api_key = str(uuid.uuid4())
        
        # Créer la nouvelle sonde
        harvester = Harvester(
            name=hostname,
            client_name=client_name,
            api_key=api_key,
            status='disconnected'
        )
        
        db.session.add(harvester)
        db.session.commit()
        
        app.logger.info(f"Nouvelle sonde ajoutée: {hostname} pour le client {client_name}")
        
        return jsonify({
            'success': True, 
            'message': 'Sonde ajoutée avec succès',
            'api_key': api_key
        }), 200
        
    except Exception as e:
        app.logger.error(f"Erreur lors de l'ajout d'une sonde: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ping', methods=['POST'])
def ping():
    """Endpoint pour mettre à jour le statut d'une sonde"""
    harvester = get_harvester_from_request()
    if not harvester:
        return jsonify({'error': 'Invalid API key'}), 401
        
    try:
        harvester.status = 'connected'
        harvester.last_seen = datetime.utcnow()
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        app.logger.error(f"Erreur lors du ping : {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/harvester/info', methods=['GET'])
def get_harvester_info():
    """Endpoint pour récupérer les informations d'une sonde"""
    harvester = get_harvester_from_request()
    if not harvester:
        return jsonify({'error': 'Invalid API key'}), 401
        
    return jsonify({
        'status': harvester.status,
        'force_scan': getattr(harvester, 'force_scan', False)
    })

@app.route('/api/harvester/<int:harvester_id>/force-scan', methods=['POST'])
def force_scan(harvester_id):
    """Force un scan immédiat sur une sonde spécifique"""
    try:
        harvester = Harvester.query.get(harvester_id)
        if not harvester:
            return jsonify({'error': 'Sonde non trouvée'}), 404
            
        harvester.force_scan = True
        db.session.commit()
        
        # Attendre que le scan soit effectué (max 30 secondes)
        start_time = time.time()
        while time.time() - start_time < 30:
            # Vérifier si un nouveau scan a été reçu
            latest_scan = NetworkScan.query.filter_by(harvester_id=harvester_id).order_by(NetworkScan.timestamp.desc()).first()
            if latest_scan and latest_scan.timestamp > datetime.utcnow() - timedelta(seconds=30):
                harvester.force_scan = False
                db.session.commit()
                return jsonify({
                    'status': 'success',
                    'message': 'Scan effectué avec succès',
                    'scan_id': latest_scan.id
                })
            time.sleep(1)
            
        # Si aucun scan n'a été reçu après 30 secondes
        harvester.force_scan = False
        db.session.commit()
        return jsonify({'error': 'Timeout - Aucun scan reçu'}), 408
        
    except Exception as e:
        app.logger.error(f"Erreur lors du scan forcé : {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test', methods=['GET'])
def test_api():
    """Endpoint de test pour vérifier la clé API"""
    app.logger.info("Test API appelé")
    app.logger.info(f"Headers reçus : {dict(request.headers)}")
    
    harvester = get_harvester_from_request()
    if not harvester:
        return jsonify({
            'status': 'error',
            'message': 'Clé API non valide',
            'headers_received': dict(request.headers)
        }), 401
    
    return jsonify({
        'status': 'success',
        'message': 'Clé API valide',
        'harvester': {
            'name': harvester.name,
            'client': harvester.client_name,
            'status': harvester.status
        }
    })

@app.route('/register', methods=['POST'])
def register_harvester():
    """Endpoint pour l'auto-enregistrement des sondes"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données manquantes'}), 400
            
        hostname = data.get('hostname')
        client_name = data.get('client_name')
        ip_address = data.get('ip_address')
        
        if not hostname or not client_name:
            return jsonify({'error': 'Hostname et client_name requis'}), 400
            
        # Générer un nom d'hôte unique basé sur le hostname
        name = f"harvester_{hostname.lower().replace(' ', '_')}_{str(uuid.uuid4())[:8]}"
        
        # Générer une clé API unique
        api_key = str(uuid.uuid4())
        
        # Créer la nouvelle sonde
        harvester = Harvester(
            name=name,
            client_name=client_name,
            api_key=api_key,
            ip_address=ip_address,
            status='connected',
            last_seen=datetime.utcnow()
        )
        
        db.session.add(harvester)
        db.session.commit()
        
        app.logger.info(f"Nouvelle sonde enregistrée : {name} avec IP {ip_address}")
        return jsonify({
            'status': 'success',
            'api_key': api_key,
            'name': name
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Erreur lors de l'enregistrement : {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/harvester/<harvester_id>/force-scan', methods=['POST'])
def force_scan(harvester_id):
    """Force un scan immédiat sur une sonde spécifique"""
    try:
        harvester = Harvester.query.get(harvester_id)
        if not harvester:
            return jsonify({'error': 'Sonde non trouvée'}), 404

        # Envoyer la commande de scan à la sonde
        response = requests.post(
            f"http://{harvester.ip_address}:5001/scan",
            headers={'Authorization': f'Bearer {harvester.api_key}'},
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify({'status': 'success', 'message': 'Scan lancé'})
        else:
            return jsonify({'error': 'Erreur lors du lancement du scan'}), 500
            
    except Exception as e:
        app.logger.error(f"Erreur lors du lancement du scan : {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan/<scan_id>/details', methods=['GET'])
def get_scan_details(scan_id):
    """Récupère les détails d'un scan"""
    try:
        scan = NetworkScan.query.get(scan_id)
        if not scan:
            return jsonify({'error': 'Scan non trouvé'}), 404
            
        # Formater les détails du scan
        details = {
            'id': scan.id,
            'timestamp': scan.timestamp.isoformat(),
            'network': scan.network,
            'total_devices': scan.total_devices,
            'total_ports': scan.total_ports,
            'devices': []
        }
        
        # Si des données de scan sont disponibles
        if scan.scan_data and isinstance(scan.scan_data, dict):
            details['devices'] = scan.scan_data.get('devices', [])
            
        return jsonify(details)
        
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération des détails : {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/harvester/<int:harvester_id>/delete', methods=['POST'])
def delete_harvester(harvester_id):
    """Supprimer une sonde"""
    try:
        harvester = Harvester.query.get_or_404(harvester_id)
        db.session.delete(harvester)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sonde supprimée avec succès'}), 200
    except Exception as e:
        app.logger.error(f"Erreur lors de la suppression de la sonde: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit_scan', methods=['POST'])
def submit_scan():
    """Soumettre les résultats d'un scan"""
    harvester = get_harvester_from_request()
    if not harvester:
        return jsonify({'error': 'Invalid API key'}), 401

    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        scan = NetworkScan(
            harvester_id=harvester.id,
            timestamp=datetime.fromisoformat(data['timestamp']),
            network=data['network'],
            total_devices=data['total_devices'],
            total_ports=data['total_ports'],
            scan_data=data['scan_data']
        )
        db.session.add(scan)
        
        # Mettre à jour les statistiques du harvester
        harvester.last_seen = datetime.utcnow()
        harvester.force_scan = False
        db.session.commit()

        app.logger.info(f"Scan reçu de {harvester.name} pour le réseau {data['network']}")
        return jsonify({'success': True, 'scan_id': scan.id}), 200
    except Exception as e:
        app.logger.error(f"Erreur lors de la soumission du scan: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/harvester/<int:harvester_id>/scan', methods=['POST'])
def request_scan(harvester_id):
    """Demande à une sonde de lancer un scan"""
    try:
        # Récupérer la sonde
        harvester = Harvester.query.get_or_404(harvester_id)
        
        # Créer un nouveau scan avec le statut "pending"
        scan = NetworkScan(
            harvester_id=harvester_id,
            timestamp=datetime.utcnow(),
            network="En attente",
            total_devices=0,
            total_ports=0,
            status='pending'
        )
        
        db.session.add(scan)
        db.session.commit()
        
        app.logger.info(f"Scan demandé pour la sonde {harvester.name}")
        return jsonify({'status': 'success', 'message': 'Scan demandé'})
        
    except Exception as e:
        app.logger.error(f"Erreur lors de la demande de scan : {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
