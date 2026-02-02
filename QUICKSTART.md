# Quick Start Guide

Guide rapide pour démarrer le bot en 5 minutes.

## 1. Prérequis

```bash
# Vérifier Python
python3 --version  # Doit être 3.10+

# Installer git (si nécessaire)
sudo apt install git
```

## 2. Installation rapide

```bash
# Cloner le projet
git clone <url>
cd lolbot

# Copier le fichier d'exemple
cp .env.example .env

# Éditer .env avec vos tokens
nano .env
```

## 3. Lancer le bot

### Option 1 : Script automatique (Linux/Mac)
```bash
./run.sh
```

### Option 2 : Manuel
```bash
# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer
python main.py
```

## 4. Tester

Une fois le bot démarré, dans Discord :

```
/link riot_id:TonNom tag:EUW
/stats
/subscribe champion:Ahri
```

## Problèmes courants

### Erreur "Module not found"
```bash
pip install -r requirements.txt
```

### Erreur "Invalid token"
- Vérifier le token Discord dans .env
- Régénérer le token si nécessaire

### Erreur API Riot "403 Forbidden"
- Vérifier la clé API Riot
- La renouveler sur https://developer.riotgames.com/

### Commandes slash invisibles
Attendre ~1 minute pour la synchronisation ou redémarrer Discord.

## Développement

### Modifier le Danger Score
Éditer `config.py` :
```python
DANGER_SCORE = {
    'OTP_SCORE': 50,  # Changer ici
    ...
}
```

### Ajouter une nouvelle commande
1. Créer la logique dans `modules/`
2. Ajouter la commande dans `cogs/`
3. Redémarrer le bot

### Logs et Debug
Les logs s'affichent dans le terminal. Pour plus de détails, ajouter :
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```
