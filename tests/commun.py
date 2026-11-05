"""Outils communs des tests : application Qt hors ecran, videos de synthese via FFmpeg."""
import os, sys, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PHILCUT_SANS_MULTIMEDIA", "1")
os.environ.setdefault("PHILCUT_APERCU_FIDELE", "0")      # pas de rendu en arrière-plan pendant les tests (sauf demande explicite)
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
# donnees dans un dossier jetable : les tests ne touchent jamais aux vrais reglages
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="philcut-tests-")
os.environ["HOME"] = os.environ["APPDATA"]
os.environ["XDG_CONFIG_HOME"] = os.environ["APPDATA"]

_app = None


def application():
    global _app
    if _app is None:
        from PySide6.QtWidgets import QApplication
        _app = QApplication.instance() or QApplication([])
    return _app


def video_test(dossier, nom="a.mp4", duree=4, taille="640x360", cadence=30, son=True):
    from app import moteur
    p = os.path.join(dossier, nom)
    args = ["-f", "lavfi", "-i", f"testsrc2=s={taille}:r={cadence}:d={duree}"]
    if son:
        args += ["-f", "lavfi", "-i", f"sine=f=440:d={duree}"]
    args += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    if son:
        args += ["-c:a", "aac"]
    moteur.lancer(args + [p])
    return p


def musique_test(dossier, nom="m.mp3", duree=10):
    from app import moteur
    p = os.path.join(dossier, nom)
    moteur.lancer(["-f", "lavfi", "-i", f"sine=f=220:d={duree}", "-c:a", "libmp3lame", p])
    return p
