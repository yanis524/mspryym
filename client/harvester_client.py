#!/usr/bin/env python3

import requests
import json
import time
import logging
import os
import sys
from datetime import datetime
import random

class HarvesterClient:
    def __init__(self, server_url, api_key=None):
        """Initialise le client avec l'URL du serveur et optionnellement une clé API"""
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.config_file = 'harvester_config.json'
        self.headers = {'X-API-Key': self.api_key} if api_key else {}
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('harvester_client')
    
    def _setup_logging(self):
        """Configure le logging"""
        logger = logging.getLogger('harvester_client')
        logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Log vers la console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Log vers un fichier
        file_handler = logging.FileHandler('harvester.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger

    def register(self, client_name):
        """Enregistre la sonde auprès du serveur"""
        try:
            response = requests.post(
                f"{self.server_url}/api/harvesters",
                json={"client_name": client_name}
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('api_key'):
                self.api_key = data['api_key']
                self.headers = {'X-API-Key': self.api_key}
                self.save_config()
                self.logger.info(f"Sonde enregistrée avec succès. API Key: {self.api_key}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Erreur lors de l'enregistrement: {str(e)}")
            return False

    def save_config(self):
        """Sauvegarde la configuration dans un fichier"""
        config = {
            "server_url": self.server_url,
            "api_key": self.api_key
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            self.logger.info("Configuration sauvegardée")
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")

    def load_config(self):
        """Charge la configuration depuis un fichier"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.server_url = config.get('server_url', self.server_url)
                self.api_key = config.get('api_key')
                self.headers = {'X-API-Key': self.api_key}
                self.logger.info("Configuration chargée")
                return True
        except FileNotFoundError:
            self.logger.warning("Fichier de configuration non trouvé")
            return False
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
            return False

    def ping(self):
        """Envoie un ping au serveur pour maintenir la connexion"""
        if not self.api_key:
            self.logger.error("Pas de clé API configurée")
            return False

        try:
            response = requests.post(
                f"{self.server_url}/api/ping",
                headers=self.headers
            )
            response.raise_for_status()
            self.logger.debug("Ping envoyé avec succès")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors du ping: {str(e)}")
            return False

    def submit_scan(self, scan_data):
        """Envoie les résultats d'un scan au serveur"""
        if not self.api_key:
            self.logger.error("Pas de clé API configurée")
            return False

        try:
            response = requests.post(
                f"{self.server_url}/api/submit_scan",
                headers=self.headers,
                json=scan_data
            )
            response.raise_for_status()
            self.logger.info("Résultats du scan envoyés avec succès")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi des résultats: {str(e)}")
            return False

    def check_pending_scans(self):
        """Vérifie s'il y a des scans en attente"""
        try:
            response = requests.get(f"{self.server_url}/api/harvester/info", headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                scans = data.get('pending_scans', [])
                if scans:
                    self.logger.info(f"Scan en attente détecté, lancement du scan...")
                    return self.perform_scan()
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification des scans : {str(e)}")
            return False

    def perform_scan(self):
        """Simule un scan réseau"""
        # Simulation d'un scan
        scan_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'network': f"192.168.1.0/24",
            'total_devices': random.randint(5, 20),
            'total_ports': random.randint(10, 50),
            'status': 'completed'
        }
        
        try:
            response = requests.post(
                f"{self.server_url}/api/submit_scan",
                headers=self.headers,
                json={'scan_data': scan_data}
            )
            
            if response.status_code == 200:
                self.logger.info("Scan envoyé avec succès")
                return True
            else:
                self.logger.error("Erreur lors de l'envoi du scan")
                return False
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi du scan : {str(e)}")
            return False

def main():
    # Configuration du client
    server_url = "http://localhost:5001"  # À modifier selon votre configuration
    client = HarvesterClient(server_url)

    # Essayer de charger la configuration existante
    if not client.load_config():
        # Si pas de configuration, demander l'enregistrement
        print("Pas de configuration trouvée. Enregistrement nécessaire.")
        client_name = input("Nom du client: ")
        if not client.register(client_name):
            print("Erreur lors de l'enregistrement")
            sys.exit(1)

    # Boucle principale
    try:
        while True:
            # Envoyer un ping
            client.ping()
            
            # Vérifier les scans en attente
            client.check_pending_scans()
            
            # Simuler un scan (à remplacer par votre logique de scan)
            scan_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "network": "192.168.1.0/24",
                "total_devices": 10,
                "total_ports": 100,
                "scan_data": {
                    "devices": [
                        {"ip": "192.168.1.1", "ports": [80, 443]},
                        {"ip": "192.168.1.2", "ports": [22, 80]}
                    ]
                }
            }
            
            # Envoyer les résultats
            client.submit_scan(scan_data)
            
            # Attendre avant le prochain scan
            time.sleep(300)  # 5 minutes
    except KeyboardInterrupt:
        print("\nArrêt du client...")
        sys.exit(0)

if __name__ == "__main__":
    main()
