#!/bin/bash
# Script de lancement du bot LoL

echo "🤖 Démarrage du bot LoL..."

# Vérifier que .env existe
if [ ! -f .env ]; then
    echo "❌ Fichier .env introuvable!"
    echo "Créez un fichier .env basé sur .env.example"
    exit 1
fi

# Vérifier que Python 3.10+ est installé
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Installer les dépendances si nécessaire
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

echo "📦 Activation de l'environnement virtuel..."
source venv/bin/activate

echo "📦 Installation des dépendances..."
pip install -r requirements.txt --quiet

echo "🚀 Lancement du bot..."
python main.py
