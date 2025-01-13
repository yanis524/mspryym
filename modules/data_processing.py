from .database import NetworkScan, Harvester
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    @staticmethod
    def get_dashboard_stats():
        """Récupère les statistiques pour le tableau de bord"""
        try:
            # Statistiques de base
            stats = {
                'harvester_count': Harvester.query.count(),
                'total_scans': NetworkScan.query.count(),
                'active_devices': 0,
                'recent_scans': []
            }

            # Calcul des appareils actifs
            latest_scans = NetworkScan.query.order_by(
                NetworkScan.timestamp.desc()
            ).limit(10).all()

            devices = set()
            for scan in latest_scans:
                for device in scan.scan_data:
                    if device.get('status') == 'up':
                        devices.add(device.get('ip'))
            
            stats['active_devices'] = len(devices)

            # Récupération des scans récents
            stats['recent_scans'] = [
                {
                    'timestamp': scan.timestamp,
                    'harvester_name': scan.harvester.name,
                    'device_count': len(scan.scan_data)
                }
                for scan in latest_scans
            ]

            return stats
        except Exception as e:
            logger.error(f"Erreur lors du traitement des données : {str(e)}")
            return None

    @staticmethod
    def analyze_network_changes(timeframe_hours=24):
        """Analyse les changements dans le réseau sur une période donnée"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=timeframe_hours)
            scans = NetworkScan.query.filter(
                NetworkScan.timestamp >= cutoff_time
            ).order_by(NetworkScan.timestamp).all()

            changes = []
            previous_devices = set()

            for scan in scans:
                current_devices = {device['ip'] for device in scan.scan_data}
                
                # Nouveaux appareils
                new_devices = current_devices - previous_devices
                if new_devices:
                    changes.append({
                        'timestamp': scan.timestamp,
                        'type': 'new_devices',
                        'devices': list(new_devices)
                    })

                # Appareils disparus
                missing_devices = previous_devices - current_devices
                if missing_devices:
                    changes.append({
                        'timestamp': scan.timestamp,
                        'type': 'missing_devices',
                        'devices': list(missing_devices)
                    })

                previous_devices = current_devices

            return changes
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des changements : {str(e)}")
            return None
