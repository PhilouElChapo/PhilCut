"""Journal des echanges (Drives, NAS, FTP, IA, autorisations) garde dans un fichier, pour retrouver ce qui
s'est passe apres coup. Mots de passe, codes et jetons masques. Taille limitee : le plus ancien est jete."""
import os, threading, time

TAILLE_MAX = 2 * 1024 * 1024
_verrou = threading.Lock()


def chemin():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "journaux")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "echanges.log")


def ecrire(source, texte):
    """Ajoute une ligne : date, origine (Google Drive, NAS..., IA), texte masque."""
    try:
        from .distant import masquer
        ligne = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  [{source}]  {masquer(str(texte))}\n"
        with _verrou:
            p = chemin()
            if os.path.exists(p) and os.path.getsize(p) > TAILLE_MAX:
                ancien = p + ".1"
                if os.path.exists(ancien):
                    os.remove(ancien)
                os.replace(p, ancien)
            with open(p, "a", encoding="utf-8") as f:
                f.write(ligne)
    except Exception:
        pass                                       # le journal ne doit jamais faire echouer une operation


def noter_version(version):
    """Au demarrage : note la version lancee et, si elle a change depuis la fois precedente, la mise a jour faite."""
    try:
        f = os.path.join(os.path.dirname(chemin()), "derniere_version.txt")
        avant = open(f, encoding="utf-8").read().strip() if os.path.exists(f) else ""
        if avant and avant != version:
            ecrire("mise a jour", f"PhilCut {avant} -> {version} : mise a jour faite, nouvelle version lancee")
        elif not avant:
            ecrire("mise a jour", f"PhilCut {version} lance (premiere fois sur ce poste)")
        with open(f, "w", encoding="utf-8") as g:
            g.write(version)
    except Exception:
        pass


# ------------------------------------------------------------------ plantages et erreurs (0.9.50)
_fichier_plantage = None


def chemin_plantages():
    return os.path.join(os.path.dirname(chemin()), "plantages.log")


def _ecrire_plantage(texte):
    try:
        p = chemin_plantages()
        with _verrou:
            if os.path.exists(p) and os.path.getsize(p) > TAILLE_MAX:
                os.replace(p, p + ".1")
            with open(p, "a", encoding="utf-8") as f:
                f.write(texte)
    except Exception:       # noqa: BLE001
        pass


def surveiller_plantages(version):
    """Note dans journaux/plantages.log : les erreurs Python (avec la pile d'appels, même dans les tâches), les messages
    graves de Qt, et — grâce à faulthandler — la pile au moment d'un plantage brutal (fenêtre qui disparaît, « a cessé de
    fonctionner »). Rien n'est envoyé : c'est un fichier à me transmettre (Outils › Journal des plantages)."""
    global _fichier_plantage
    import faulthandler, platform, sys, traceback
    entete = f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')}  PhilCut {version}  {platform.platform()}  Python {platform.python_version()}\n"
    try:
        _fichier_plantage = open(chemin_plantages(), "a", encoding="utf-8")
        _fichier_plantage.write(entete + "démarrage\n")
        _fichier_plantage.flush()
        faulthandler.enable(file=_fichier_plantage, all_threads=True)
    except Exception:       # noqa: BLE001
        _fichier_plantage = None

    ancien = sys.excepthook

    def crochet(t, v, tb):
        _ecrire_plantage(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  ERREUR\n" + "".join(traceback.format_exception(t, v, tb)))
        try:
            ancien(t, v, tb)
        except Exception:   # noqa: BLE001
            pass
    sys.excepthook = crochet
    import threading

    def crochet_fil(a):
        _ecrire_plantage(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  ERREUR (tâche {getattr(a.thread, 'name', '?')})\n" +
                         "".join(traceback.format_exception(a.exc_type, a.exc_value, a.exc_traceback)))
    threading.excepthook = crochet_fil
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler

        def qt(mode, contexte, message):
            if mode in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
                _ecrire_plantage(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  Qt : {message}\n")
        qInstallMessageHandler(qt)
    except Exception:       # noqa: BLE001
        pass


def fin_normale():
    """Fermeture normale : notée, pour distinguer un plantage d'une sortie voulue en lisant le journal."""
    if _fichier_plantage:
        try:
            _fichier_plantage.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  fermeture normale\n")
            _fichier_plantage.flush()
        except Exception:   # noqa: BLE001
            pass
