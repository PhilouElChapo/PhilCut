@echo off
REM Lancer PhilCut depuis les sources (Windows). Cree l'environnement la premiere fois.
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv || goto erreur
  .venv\Scripts\pip install -r requirements.txt || goto erreur
)
.venv\Scripts\python philcut.py %*
goto :eof
:erreur
echo Installation impossible : Python 3.10+ est-il installe (python.org, "Add to PATH") ?
pause
