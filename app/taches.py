"""Taches de fond (QThread) : import des medias, proxys, vignettes, export, assistant, IA.

Une Tache execute `fonction(tache)` dans un fil ; la fonction appelle tache.avancer(fraction, texte) et teste
tache.arret. La fenetre affiche la progression dans un encart non bloquant (voir fenetre.Encart)."""
import traceback

from PySide6.QtCore import QThread, Signal


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

    def avancer(self, fraction, texte=""):
        self.progression.emit(max(0.0, min(1.0, float(fraction))), texte)

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
        self.fini.emit(self.resultat, self.erreur)


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
