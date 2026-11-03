#!/bin/sh
# Lancer PhilCut depuis les sources (Linux). Cree l'environnement la premiere fois.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt || { echo "Installation impossible (python3-venv ?)"; exit 1; }
fi
exec .venv/bin/python philcut.py "$@"
