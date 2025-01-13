# Client Harvester

Ce client Python permet de communiquer avec le serveur Seahawks Monitoring.

## Installation

1. Créer un environnement virtuel (recommandé) :
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

## Utilisation

1. Lancer le client :
```bash
python harvester_client.py
```

Lors du premier lancement, le client vous demandera de vous enregistrer avec un nom de client.
Une fois enregistré, il sauvegardera la configuration (y compris la clé API) dans un fichier `harvester_config.json`.

Le client va ensuite :
- Envoyer des pings réguliers au serveur pour maintenir la connexion
- Simuler des scans de réseau et envoyer les résultats

## Configuration

La configuration est stockée dans `harvester_config.json` et contient :
- L'URL du serveur
- La clé API

## Fonctionnalités

- Enregistrement automatique auprès du serveur
- Sauvegarde de la configuration
- Envoi de pings réguliers
- Simulation de scans réseau
- Logging des activités
