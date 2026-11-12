"""Taches de fond (QThread) : import des medias, proxys, vignettes, export, assistant, IA.

Une Tache execute `fonction(tache)` dans un fil ; la fonction appelle tache.avancer(fraction, texte) et teste
tache.arret. La fenetre affiche la progression dans un encart non bloquant (voir fenetre.Encart)."""
import traceback

from PySide6.QtCore import QThread, Signal


_EN_COURS = set()          # 0.9.51 : toute tâche lancée est gardée ici jusqu'à sa vraie fin


class Tache(QThread):
    progression = Signal(float, str)       # 0..1, texte
    fini = Signal(object, object)          # resultat, erreur (None si tout va bien)

    def __init__(self, fonction, titre=""):
        super().__init__()
        self.fonction = fonction
        self.titre = titre
        self.arret = False
        self.resultat = None
        self.erreur = None
        self.dernier = (0.0, "")              # dernière progression : pour dire ce qui est en cours (fermeture…)

    def avancer(self, fraction, texte=""):
        f = max(0.0, min(1.0, float(fraction)))
        self.dernier = (f, texte or self.dernier[1])
        self.progression.emit(f, texte)

    def start(self, *a):
        """Une tâche n'est jamais détruite en plein travail : sinon Qt arrête tout PhilCut (« QThread: Destroyed while
        thread is still running », code 0xc0000409 dans Qt6Core.dll), par exemple quand une fenêtre relance une tâche
        alors que la précédente tourne encore."""
        if self not in _EN_COURS:
            _EN_COURS.add(self)
            self.finished.connect(self._liberer)
        super().start(*a)

    def _liberer(self):
        # jamais détruite pendant l'appel de son propre signal « finished » (plantage) : relâchée au tour suivant
        self.wait(5000)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda t=self: _EN_COURS.discard(t))

    def lier(self, objet):
        """La tâche appartient à cet objet (fenêtre, volet, barre du bas) : s'il disparaît, elle est arrêtée et ne prévient
        plus personne (sinon sa fin appellerait un objet détruit)."""
        try:
            objet.destroyed.connect(self._orpheline)
        except (AttributeError, RuntimeError):
            pass
        return self

    def _orpheline(self, *_a):
        self.arret = True
        for sig in (self.fini, self.progression):
            try:
                sig.disconnect()
            except (RuntimeError, TypeError):
                pass

    def stopper(self):
        self.arret = True

    def arret_demande(self):
        return self.arret

    def run(self):
        try:
            self.resultat = self.fonction(self)
        except Exception as e:          # noqa: BLE001 : l'erreur remonte a l'interface
            self.erreur = e
            self.trace = traceback.format_exc()
            if not isinstance(e, InterruptedError):        # 0.9.51 : le détail va au journal des plantages et erreurs
                try:
                    from .journal import _ecrire_plantage
                    import time as _t
                    _ecrire_plantage(f"{_t.strftime('%Y-%m-%d %H:%M:%S')}  ERREUR dans « {self.titre} »\n{self.trace}")
                except Exception:   # noqa: BLE001
                    pass
        self.fini.emit(self.resultat, self.erreur)


class ListeTaches(list):
    """Liste des tâches d'une fenêtre : chaque tâche ajoutée lui est liée (fenêtre détruite → tâche arrêtée, débranchée)."""

    def __init__(self, proprietaire):
        super().__init__()
        self._proprio = proprietaire

    def append(self, t):
        if hasattr(t, "lier"):
            t.lier(self._proprio)
        super().append(t)


def texte_erreur(e):
    """Le message d'une erreur, jamais vide (certaines erreurs n'ont pas de texte : on dit au moins leur nature)."""
    from .langue import _
    t = str(e or "").strip()
    return t or _("erreur {n} sans message (détail : Outils › Journal des plantages et erreurs)", n=type(e).__name__)


def importer_media(tache, chemin, params, avec_proxy=True):
    """Fiche technique + proxy + bande de vignettes + forme d'onde + niveaux ; renvoie le dictionnaire du media."""
    import os
    from . import moteur
    from .config import dossier_donnees
    tache.avancer(0.02, os.path.basename(chemin))
    fiche = moteur.sonder(chemin)
    out = {"fiche": fiche, "proxy": "", "vignettes": "", "onde": [], "niveaux": None}
    genre = fiche.get("genre")
    if genre in ("video", "audio"):
        try:
            out["niveaux"] = moteur.niveaux(chemin)
        except moteur.ErreurMoteur:
            pass
    d = os.path.join(dossier_donnees(), "vignettes")
    os.makedirs(d, exist_ok=True)
    cle = os.path.basename(moteur.chemin_proxy(chemin, params))[:-4]
    if genre == "video":
        try:
            png = moteur.vignettes(chemin, n=24, hauteur=60, duree=fiche.get("duree") or 1)
            vp = os.path.join(d, cle + ".png")
            with open(vp, "wb") as f:
                f.write(png)
            out["vignettes"] = vp
        except moteur.ErreurMoteur:
            pass
        tache.avancer(0.15, os.path.basename(chemin))
        if fiche.get("audio"):
            out["onde"] = moteur.forme_onde(chemin, 300)
        if avec_proxy and params.get("proxys", True):
            def prog(f):
                tache.avancer(0.2 + 0.8 * f, os.path.basename(chemin))
            out["proxy"] = moteur.proxy(chemin, params, fiche, progression=prog, arret=lambda: tache.arret)
    elif genre == "audio":
        out["onde"] = moteur.forme_onde(chemin, 300)
    elif genre == "image":
        try:
            png = moteur.image(chemin, 0, 240)
            vp = os.path.join(d, cle + ".png")
            with open(vp, "wb") as f:
                f.write(png)
            out["vignettes"] = vp
        except moteur.ErreurMoteur:
            pass
    tache.avancer(1.0, os.path.basename(chemin))
    return out
