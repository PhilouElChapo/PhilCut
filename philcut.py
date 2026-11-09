"""Point d'entree de PhilCut : python philcut.py [projet.philcut | video ...]"""
import os, sys

if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def verifier(sortie):
    """Auto-controle sans fenetre (fabrication automatique) : FFmpeg embarque, encodage, titres (libass), langues, icones."""
    import tempfile
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication
    QGuiApplication([])
    from app import moteur, langue, icones, projet, export, titres
    lignes, ok = [], True
    v = moteur.version()
    lignes.append(f"moteur ffmpeg: {v or 'ABSENT'} ({moteur.ffmpeg()})")
    ok = ok and bool(v)
    try:
        enc = moteur.encodeurs()
        lignes.append("moteur encodeurs: " + ", ".join(enc))
    except Exception as e:
        lignes.append(f"moteur encodeurs: ERREUR {e}")
        ok = False
    try:
        d = tempfile.mkdtemp(prefix="philcut-verif-")
        src = os.path.join(d, "a.mp4")
        moteur.lancer(["-f", "lavfi", "-i", "testsrc2=s=320x180:r=25:d=2", "-f", "lavfi", "-i", "sine=f=440:d=2", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", src])
        p = projet.Projet("verif")
        m = p.ajouter_media(src, moteur.sonder(src))
        p.ajouter_clip(m["id"])
        p.ajouter_titre("PhilCut", 0.2, 1.5, animation="neon")
        out, journal = export.exporter(p, os.path.join(d, "out.mp4"), "whatsapp")
        f = moteur.sonder(out)
        lignes.append(f"moteur export: ok ({moteur.resume_fiche(f)})")
        ok = ok and f["duree"] > 1.5
    except Exception as e:
        lignes.append(f"moteur export: ERREUR {e}")
    try:                                         # moteur d'effets GL : embarqué ; la carte graphique peut manquer (machine de fabrication)
        import moderngl  # noqa: F401
        from app import moteur_gl
        n = len(moteur_gl.charger()["effets"])
        lignes.append(f"moteur GL: {n} effets, contexte : {moteur_gl.raison() if moteur_gl.disponible() else 'indisponible ici (' + moteur_gl.raison() + ')'}")
        ok = ok and n > 0
    except Exception as e:
        lignes.append(f"moteur GL: ERREUR {e}")
        ok = False
        ok = False
    lignes.append("langues: " + ", ".join(c for c, _n in langue.disponibles()))
    try:
        icones.icone("clap")
        icones.logo()
        lignes.append("icones: ok")
    except Exception as e:
        lignes.append(f"icones: ERREUR {e}")
        ok = False
    try:
        from PySide6 import QtMultimedia  # noqa: F401
        lignes.append("multimedia: ok")
    except ImportError as e:
        lignes.append(f"multimedia: absent ({e}) : apercu par images")
    try:   # detourage portable : onnxruntime embarque dans PhilCut
        import onnxruntime as ort
        lignes.append(f"ia locale: onnxruntime {ort.__version__} ({', '.join(ort.get_available_providers())})")
    except Exception as e:
        lignes.append(f"ia locale: onnxruntime ERREUR {e}")
        ok = False
    lignes.append("RESULTAT: " + ("OK" if ok else "ECHEC"))
    with open(sortie, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    print("\n".join(lignes))
    return 0 if ok else 1


def main():
    if "--verifier" in sys.argv:
        return verifier(sys.argv[sys.argv.index("--verifier") + 1])
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont, QFontDatabase
    from PySide6.QtWidgets import QApplication
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("PhilCut")
    app.setOrganizationName("PhilouElChapo")
    from app.config import VERSION
    from app.demarrage import EcranDemarrage
    lancement = EcranDemarrage(VERSION)
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    polices = os.path.join(base, "fonts")
    if os.path.isdir(polices):
        for f in os.listdir(polices):
            if f.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(polices, f))
    from app.langue import _
    lancement.etape(_("Lecture de vos réglages…"), 0.08)
    from app import theme, ecran
    from app.config import Parametres, dossier_donnees
    params = Parametres()
    theme.appliquer(params.get("theme", "sombre"))
    lancement.etape(_("Mise en place du thème et des polices…"), 0.18)
    police = QFont("Nunito" if "Nunito" in QFontDatabase.families() else app.font().family(), 10)
    app.setFont(police)
    theme.proteger_bulles()
    app.setStyleSheet(theme.feuille(dossier_donnees(), params.get("theme", "sombre")))
    try:                                    # Oui, Non, Annuler, Copier… de Qt dans la langue de PhilCut
        from app.langue import LANGUE
        from app.widgets import installer_traduction_qt
        installer_traduction_qt(app, LANGUE)
    except Exception:
        pass
    try:
        ecran.installer(app)
    except Exception:
        pass
    import importlib
    for frac, texte, modules in ((0.3, _("Recherche du moteur vidéo (FFmpeg)…"), ("app.moteur",)),
                                 (0.4, _("Chargement des effets et des transitions…"), ("app.effets", "app.catalogue_effets")),
                                 (0.5, _("Chargement des Goodies, titres et intros…"), ("app.goodies", "app.intros")),
                                 (0.6, _("Chargement de la timeline et de l'aperçu…"), ("app.editeur",))):
        lancement.etape(texte, frac)
        for m in modules:
            try:
                importlib.import_module(m)
            except Exception:    # noqa: BLE001 : l'erreur éventuelle réapparaît, lisible, à l'ouverture de la fenêtre
                pass
    from app.fenetre import Fenetre
    lancement.etape(_("Préparation de la fenêtre de montage…"), 0.72)
    f = Fenetre([a for a in sys.argv[1:] if os.path.exists(a)])
    lancement.etape(_("Ouverture…"), 1.0)
    f.afficher()
    lancement.close()
    code = app.exec()
    sortir(code)                        # ici, pas après le retour de main() : sinon Python détruit la fenêtre et ses
    return code                         # tâches de fond encore vivantes (« QThread détruit en cours » : plantage à l'arrêt)


def sortir(code):
    """Tout est enregistré à la fermeture de la fenêtre : on sort sans laisser Python ni Qt détruire les objets dans le
    désordre (plantages à l'arrêt dans pyside6.abi3.dll ou ucrtbase.dll vus sous Windows)."""
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:       # noqa: BLE001 : version sans console (Windows)
        pass
    os._exit(code or 0)


if __name__ == "__main__":
    sortir(main())
