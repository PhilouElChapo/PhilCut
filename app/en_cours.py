"""Créations en cours, à reprendre (1.2.1 ; demande de Philippe du 22/11 21h13 : « instaurer une sauvegarde sur les créations IA,
musique etc., pour pouvoir reprendre ce qui a été créé… on perd tout le bénéfice des créations et des corrections » ; choix du
25/11 : Fabrique musique, clip de groupe, motion design IA, assistant musique ; enregistrement à chaque changement).

Chaque fenêtre suivie est relue toutes les 2 secondes ; son état, s'il a changé, est écrit aussitôt (fichier entier remplacé
d'un coup) dans donnees/en_cours/<genre>/<id>.json. Un plantage ne perd donc au plus que deux secondes de réglages, jamais
un résultat payé (les fichiers créés restent où ils sont). « Fabrique IA › Reprendre une création en cours… » les liste.
L'assistant vidéo garde déjà ses séquences (sequence_ia.en_cours) : elles sont listées aussi.
"""
import json
import os
import time
import uuid

from PySide6.QtCore import QObject, QTimer

from .langue import _

GENRES = {"fabrique_musique": _("Fabrique musique"), "assistant_musique": _("Assistant musique"), "clip_groupe": _("Clip de groupe"),
          "motion_ia": _("Motion design IA")}
GARDER_JOURS = 60


def dossier(genre=None):
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "en_cours", *([genre] if genre else []))
    os.makedirs(d, exist_ok=True)
    return d


def ecrire(genre, ident, titre, etat):
    p = os.path.join(dossier(genre), ident + ".json")
    tmp = p + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"genre": genre, "id": ident, "titre": (titre or "").strip()[:120], "modifie": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "etat": etat}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    return p


def lire(genre, ident):
    try:
        with open(os.path.join(dossier(genre), ident + ".json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def retirer(genre, ident):
    try:
        os.remove(os.path.join(dossier(genre), ident + ".json"))
        return True
    except OSError:
        return False


def lister():
    """Toutes les créations en cours, la plus récente d'abord ; les plus vieilles que GARDER_JOURS sont oubliées."""
    out, limite = [], time.time() - GARDER_JOURS * 86400
    for g in GENRES:
        d = dossier(g)
        for n in os.listdir(d):
            if not n.endswith(".json"):
                continue
            p = os.path.join(d, n)
            if os.path.getmtime(p) < limite:
                continue
            x = lire(g, n[:-5])
            if x and x.get("etat"):
                out.append(x)
    return sorted(out, key=lambda x: x.get("modifie", ""), reverse=True)


def resume(x):
    return f"{GENRES.get(x['genre'], x['genre'])} · {x.get('titre') or _('sans titre')} · {x.get('modifie', '')[:16]}"


class Suivi(QObject):
    """Relit l'état d'une fenêtre toutes les `ms` et l'écrit s'il a changé. etat() → dict (ou None : rien à garder) ;
    titre() → texte court."""

    def __init__(self, fenetre, genre, etat, titre, ident=None, ms=2000):
        super().__init__(fenetre)
        self.genre, self.etat, self.titre = genre, etat, titre
        self.ident = ident or time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        self._dernier = None
        self.minuteur = QTimer(self)
        self.minuteur.timeout.connect(self.maintenant)
        self.minuteur.start(ms)

    def maintenant(self):
        try:
            e = self.etat()
        except RuntimeError:                         # fenêtre détruite
            self.minuteur.stop()
            return None
        except Exception:      # noqa: BLE001 : un état illisible ne doit jamais gêner le travail
            return None
        if not e:
            return None
        texte = json.dumps(e, ensure_ascii=False, sort_keys=True, default=str)
        if texte == self._dernier:
            return None
        self._dernier = texte
        try:
            return ecrire(self.genre, self.ident, self.titre() or "", json.loads(texte))
        except OSError:
            return None

    def oublier(self):
        """La création est terminée et posée : elle quitte la liste."""
        self.minuteur.stop()
        retirer(self.genre, self.ident)


def suivre(fenetre, genre, etat, titre, ident=None):
    s = Suivi(fenetre, genre, etat, titre, ident)
    fenetre._suivi_en_cours = s
    return s
