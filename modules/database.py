from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json

db = SQLAlchemy()

class Harvester(db.Model):
    """Modèle pour les sondes"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    client_name = db.Column(db.String(100), nullable=False)
    api_key = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='disconnected')
    ip_address = db.Column(db.String(15), nullable=True)
    last_seen = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relation avec les scans
    scans = db.relationship('NetworkScan', backref='harvester', lazy=True)

    def update_status(self):
        """Met à jour le statut de la sonde en fonction de sa dernière activité"""
        if not self.last_seen:
            self.status = 'disconnected'
        else:
            # Si pas de nouvelle depuis plus de 5 minutes, on considère la sonde déconnectée
            if datetime.utcnow() - self.last_seen > timedelta(minutes=5):
                self.status = 'disconnected'
            else:
                self.status = 'connected'

class NetworkScan(db.Model):
    """Modèle pour les résultats de scan"""
    id = db.Column(db.Integer, primary_key=True)
    harvester_id = db.Column(db.Integer, db.ForeignKey('harvester.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    network = db.Column(db.String(50), nullable=False)
    total_devices = db.Column(db.Integer, default=0)
    total_ports = db.Column(db.Integer, default=0)
    scan_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='completed')
    scan_scan_count = db.Column(db.Integer, default=0)
    scan_status = db.Column(db.String(20), default='completed')
    scan_scan_data = db.Column(db.Text, nullable=True)
    
    # Stockage des données brutes du scan
    _scan_data = db.Column('scan_data', db.Text, nullable=True)
    
    @property
    def scan_data(self):
        """Récupère les données du scan"""
        if self._scan_data:
            return json.loads(self._scan_data)
        return []
    
    @scan_data.setter
    def scan_data(self, value):
        """Stocke les données du scan"""
        self._scan_data = json.dumps(value)

    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'harvester_id': self.harvester_id,
            'timestamp': self.timestamp.isoformat(),
            'network': self.network,
            'total_devices': self.total_devices,
            'total_ports': self.total_ports,
            'scan_count': self.scan_count,
            'status': self.status,
            'scan_data': self.scan_data
        }
