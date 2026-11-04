"""Parametres de PhilCut.

Mode portable : si un fichier 'portable.txt' est a cote de l'executable, tout
(parametres, session, bibliotheque, proxys) est range dans le dossier 'donnees' a cote,
et rien n'est ecrit ailleurs sur le PC ni dans le registre.
"""
import json, os, platform, sys

APP = "PhilCut"
VERSION = "0.2.2"


def dossier_programme():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def est_portable():
    return os.path.exists(os.path.join(dossier_programme(), "portable.txt"))


def dossier_donnees():
    if est_portable():
        d = os.path.join(dossier_programme(), "donnees")
    elif sys.platform == "win32":
        d = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP)
    else:
        d = os.path.join(os.path.expanduser("~/.config"), APP.lower())
    os.makedirs(d, exist_ok=True)
    return d


DEFAUTS = {
    "machine": platform.node() or "Ce PC",
    "recents": [],
    "outils_epingles": ["importer", "assistant", "couper", "texte", "musique", "effets", "exporter"],
    "zoom": 1.0,
    "theme": "sombre",            # video : fond sombre par defaut, clair dans les Preferences
    "drive": "",                    # racine du Drive sur ce PC (ex. G:\\Mon Drive) : sauvegarde + session
    "drive_restaure": False,
    "ia_moteur": "claude",
    "clef_claude": "",
    "clef_gemini": "",
    "clef_fal": "",                 # fal.ai : générateurs vidéo (Kling, Seedance…), paiement à l'usage
    "modeles_video_perso": [],      # modèles fal ajoutés par l'utilisateur : {"modele", "modele_image", "nom", "prix_s"}
    "association_video": False,
    "proxys": True,                 # copies legeres des rushes a l'import
    "export_destination": "youtube",
    "ia_locale": {},                # resultat du test materiel, par poste
    "ia_poste_leger": True,         # IA locale : moitie des coeurs, priorite basse
    "ia_gpu": True,                 # IA locale : carte graphique (Vulkan) si presente
    "ia_locale_modeles": {},        # modele choisi par genre (vision, whisper, detourage), par poste
    "assistant_niveau": "recettes",  # recettes | locale | cloud
    "dossier_flow": "",             # dossier surveille pour les clips Flow
    "veo_actif": False,
    "barre_rapide": True,
    "maj_source": "github",         # "github" ou "dossier" (dossier synchronise)
    "maj_auto": True,               # verifier au demarrage (une fois par jour)
    "maj_derniere": "",
    "racines": [],                  # emplacements supplementaires a fouiller (mode avance)
    "nas": "",                      # dossier du NAS sur ce poste
    "synchro": True,                # synchroniser les fichiers ouverts entre postes
    "dernier_dossier": "",
    "bienvenue_vue": False,         # assistant de premiere installation deja montre
    "drive_compte": "",             # Drive « en direct » (compte Google...) au lieu du dossier de l'appli de bureau
}


class Parametres(dict):
    def __init__(self):
        super().__init__(DEFAUTS)
        self.chemin = os.path.join(dossier_donnees(), "parametres.json")
        self.nouveau = not os.path.exists(self.chemin)      # premiere installation sur ce poste
        try:
            with open(self.chemin, encoding="utf-8") as f:
                self.update(json.load(f))
        except (OSError, ValueError):
            pass
        if self.get("dossier_synchro") and not self.get("drive"):   # ancienne 0.1
            self["drive"] = self.pop("dossier_synchro")
        self._clefs_coffre = {}
        self._charger_clefs()
        self._communs_vus = self._empreinte_communs()

    # ---- clefs IA : dans le coffre du systeme, jamais dans parametres.json
    CLEFS_COFFRE = ("clef_claude", "clef_gemini", "clef_fal")

    def _charger_clefs(self):
        """Lit les clefs dans le coffre ; une clef trouvee en clair (version 0.1) y est deplacee puis effacee du fichier."""
        try:
            from . import coffre
        except Exception:
            return
        a_migrer = False
        for k in self.CLEFS_COFFRE:
            en_clair = super().get(k) or ""
            try:
                v = coffre.lire("ia:" + k) or ""
            except Exception:
                v = ""
            if en_clair and en_clair != v:
                a_migrer = True
                v = en_clair
            self[k] = v
            self._clefs_coffre[k] = None if a_migrer else v
        if a_migrer:
            self.enregistrer()

    def _ranger_clefs(self):
        try:
            from . import coffre
        except Exception:
            return False
        for k in self.CLEFS_COFFRE:
            v = super().get(k) or ""
            if self._clefs_coffre.get(k) == v:
                continue
            try:
                if v:
                    coffre.enregistrer("ia:" + k, v)
                else:
                    coffre.supprimer("ia:" + k)
                self._clefs_coffre[k] = v
            except Exception:
                return False
        return True

    def _empreinte_communs(self):
        try:
            from .reglages import COMMUNS
        except ImportError:
            return ""
        return json.dumps({k: self.get(k) for k in COMMUNS}, sort_keys=True, ensure_ascii=False, default=str)

    def enregistrer(self):
        e = self._empreinte_communs() if hasattr(self, "_communs_vus") else ""
        if e and e != self._communs_vus:          # un reglage commun a vraiment change sur ce poste : il est date
            import datetime
            self["communs_maj"] = datetime.datetime.now().isoformat(timespec="seconds")
            self._communs_vus = e
        ok = self._ranger_clefs() if hasattr(self, "_clefs_coffre") else False
        donnees = dict(self)
        if ok:
            for k in self.CLEFS_COFFRE:
                donnees[k] = ""
        try:
            with open(self.chemin + ".tmp", "w", encoding="utf-8") as f:
                json.dump(donnees, f, ensure_ascii=False, indent=2)
            os.replace(self.chemin + ".tmp", self.chemin)
        except OSError:
            pass

    def ajouter_recent(self, chemin):
        import datetime
        r = [p for p in self["recents"] if os.path.normcase(p) != os.path.normcase(chemin)]
        self["recents"] = [chemin] + r[:49]
        dates = dict(self.get("recents_dates") or {})
        dates[chemin] = datetime.datetime.now().isoformat(timespec="minutes")
        self["recents_dates"] = {p: dates[p] for p in self["recents"] if p in dates}
        self.enregistrer()

    # ---- session partagee : voir app/session.py
    def chemin_session(self):
        """La session (emplacements des fichiers ouverts, pas les fichiers) vit sur le Drive."""
        try:
            from .bibliotheque import dossier_philcut_drive
            d = dossier_philcut_drive(self)          # copie locale du compte de synchronisation, jamais un ancien chemin
        except Exception:
            d = None
        if d:
            os.makedirs(d, exist_ok=True)
            return os.path.join(d, "session.json")
        return os.path.join(dossier_donnees(), "session.json")


EXTENSIONS_VIDEO = (".mp4", ".mov", ".mkv", ".m4v", ".webm", ".avi", ".mts", ".m2ts", ".3gp")
EXTENSIONS_AUDIO = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus")
EXTENSIONS_IMAGE = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp", ".gif")
EXTENSION_PROJET = ".philcut"


def est_video(chemin):
    return chemin.lower().endswith(EXTENSIONS_VIDEO)


def est_audio(chemin):
    return chemin.lower().endswith(EXTENSIONS_AUDIO)


def est_image(chemin):
    return chemin.lower().endswith(EXTENSIONS_IMAGE)


def associer_projets(activer):
    """Association .philcut -> PhilCut pour l'utilisateur courant (Windows), reversible.
    Les videos elles-memes ne sont jamais associees : PhilCut ne gene pas les autres lecteurs."""
    if sys.platform != "win32":
        return False
    import winreg
    exe = sys.executable if getattr(sys, "frozen", False) else f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
    cle = r"Software\Classes\PhilCut.Projet"
    if activer:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cle + r"\shell\open\command") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, f'{exe} "%1"')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\" + EXTENSION_PROJET) as k:
            winreg.SetValue(k, "", winreg.REG_SZ, "PhilCut.Projet")
    else:
        for c in (cle + r"\shell\open\command", cle + r"\shell\open", cle + r"\shell", cle, "Software\\Classes\\" + EXTENSION_PROJET):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, c)
            except OSError:
                pass
    return True
