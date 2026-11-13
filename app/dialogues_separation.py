"""Fenêtre « Séparer voix, musique et bruits » (0.9.53) : sur un plan du film (clic droit) ou sur un fichier (Fabrique IA ›
Musique). Calcul sur ce poste, avec sa progression ; on écoute chaque piste avant de poser ; tout se défait d'un coup."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout)

from . import separation as S
from .langue import _
from .taches import Tache


NOMS = {"voix": _("Voix"), "musique": _("Musique"), "bruits": _("Bruits (fond continu)")}


class DialogueSeparation(QDialog):
    def __init__(self, ed, clip=None, fichier=None):
        super().__init__(ed)
        self.ed, self.clip, self.fichier = ed, clip, fichier
        self.setModal(False)
        self.setWindowTitle(_("Séparer voix, musique et bruits"))
        self.setMinimumWidth(560)
        self.tache, self.resultat, self.lecteur, self._ecoute = None, None, None, None
        v = QVBoxLayout(self)
        quoi = (clip or {}).get("nom") or os.path.basename(fichier or "")
        t = QLabel(_("<b>{q}</b> : PhilCut sépare le son en trois pistes — la voix, la musique, et les bruits de fond continus "
                     "(vent, rumeur, ventilation). Les trois ensemble redonnent exactement le son d'origine. Calcul sur ce "
                     "poste, gratuit, rien n'est envoyé ; écoutez chaque piste avant de poser.", q=quoi))
        t.setWordWrap(True)
        v.addWidget(t)
        self.manque = QLabel("")
        self.manque.setWordWrap(True)
        self.manque.setStyleSheet("color:#e3b341")
        v.addWidget(self.manque)
        self.b_installer = QPushButton(_("Installer le modèle…"))
        self.b_installer.clicked.connect(self._installer)
        v.addWidget(self.b_installer)
        # ce qu'on veut garder : trois choix tout faits, puis les cases
        hp = QHBoxLayout()
        for lib, garde, tip in ((_("Retirer la voix"), ("musique", "bruits"), _("Garder la musique et l'ambiance, sans la voix")),
                                (_("Garder la voix seule"), ("voix",), _("Une voix nette, sans musique ni bruit de fond")),
                                (_("Les trois pistes"), ("voix", "musique", "bruits"), _("Chaque piste séparée, à doser vous-même"))):
            b = QPushButton(lib)
            b.setToolTip(tip)
            b.clicked.connect(lambda _c=False, g=garde: self._garder(g))
            hp.addWidget(b)
        v.addLayout(hp)
        self.cases = {}
        hc = QHBoxLayout()
        for k in S.PISTES:
            c = QCheckBox(NOMS[k])
            c.setChecked(True)
            self.cases[k] = c
            hc.addWidget(c)
        hc.addStretch(1)
        v.addLayout(hc)
        self.muet = QCheckBox(_("Couper le son d'origine du plan (les pistes séparées le remplacent)"))
        self.muet.setChecked(True)
        self.muet.setVisible(clip is not None)
        v.addWidget(self.muet)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        v.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        self.ecoutes = {}
        he = QHBoxLayout()
        for k in S.PISTES:
            b = QPushButton("▶ " + NOMS[k])
            b.setEnabled(False)
            b.clicked.connect(lambda _c=False, k_=k: self._ecouter(k_))
            self.ecoutes[k] = b
            he.addWidget(b)
        v.addLayout(he)
        hb = QHBoxLayout()
        hb.addStretch(1)
        self.b_separer = QPushButton(_("Séparer"))
        self.b_separer.setStyleSheet("font-weight:600")
        self.b_separer.clicked.connect(self.separer)
        hb.addWidget(self.b_separer)
        self.b_poser = QPushButton(_("Poser dans le film") if clip else _("Ajouter aux médias du projet"))
        self.b_poser.setEnabled(False)
        self.b_poser.clicked.connect(self.poser)
        hb.addWidget(self.b_poser)
        self.b_fermer = QPushButton(_("Fermer"))
        self.b_fermer.clicked.connect(self.close)
        hb.addWidget(self.b_fermer)
        v.addLayout(hb)
        self._etat_modele()

    def _etat_modele(self):
        m = S.manquant(self.ed.params)
        self.manque.setText(m or "")
        self.manque.setVisible(bool(m))
        self.b_installer.setVisible(bool(m))
        self.b_separer.setEnabled(not m and not self._en_calcul())

    def _installer(self):
        from .telechargements import installer_modele
        from . import separation as S
        if installer_modele(self, self.ed, S.CLE, self._etat_modele, self.manque):
            self.b_installer.setEnabled(False)

    def _garder(self, garde):
        for k, c in self.cases.items():
            c.setChecked(k in garde)

    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    # ------------------------------------------------------------------ calcul
    def _source(self):
        """(fichier, début, durée) : la partie du rush utilisée par le plan, ou tout le fichier."""
        if self.clip:
            m = self.ed.projet.media(self.clip["media"]) or {}
            return m.get("chemin", ""), float(self.clip["src_debut"]), float(self.clip["src_fin"]) - float(self.clip["src_debut"])
        return self.fichier, 0.0, None

    def separer(self):
        if self._en_calcul():
            return
        src, debut, duree = self._source()
        params = self.ed.params
        self.b_separer.setEnabled(False)
        self.barre.show()
        self.barre.setValue(0)
        self.tache = Tache(lambda t: S.separer(src, S.dossier_sorties(), debut, duree, params,
                                               progression=lambda f, txt="": t.avancer(f, txt), arret=lambda: t.arret),
                           _("Séparation voix, musique et bruits"))
        self.tache.lier(self)
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), self.etat.setText(txt)), Qt.QueuedConnection)
        self.tache.fini.connect(self._fini, Qt.QueuedConnection)
        self.tache.start()

    def _fini(self, r, err):
        self.barre.hide()
        self.b_separer.setEnabled(True)
        if err or not r:
            from .taches import texte_erreur
            self.etat.setText(_("✕ La séparation n'a pas abouti : {e}", e=texte_erreur(err)))
            return
        self.resultat = r
        for k, b in self.ecoutes.items():
            b.setEnabled(bool(r.get(k)))
        self.b_poser.setEnabled(True)
        self.etat.setText(_("✓ Séparé. Ecoutez chaque piste, puis « {p} ».", p=self.b_poser.text()))

    def _ecouter(self, k):
        from PySide6.QtCore import QUrl
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        if not self.resultat:
            return
        if self.lecteur is None:
            self.lecteur, self._sortie = QMediaPlayer(self), QAudioOutput(self)
            self.lecteur.setAudioOutput(self._sortie)
        if self._ecoute == k and self.lecteur.playbackState() == QMediaPlayer.PlayingState:
            self.lecteur.pause()
            self.ecoutes[k].setText("▶ " + NOMS[k])
            return
        for kk, b in self.ecoutes.items():
            b.setText("▶ " + NOMS[kk])
        self._ecoute = k
        self.lecteur.setSource(QUrl.fromLocalFile(self.resultat[k]))
        self.lecteur.play()
        self.ecoutes[k].setText("⏸ " + NOMS[k])

    # ------------------------------------------------------------------ pose
    def gardees(self):
        return [k for k in S.PISTES if self.cases[k].isChecked() and (self.resultat or {}).get(k)]

    def poser(self):
        if not self.resultat:
            return
        from . import moteur
        p = self.ed.projet
        gardees = self.gardees()
        if not gardees:
            self.etat.setText(_("Cochez au moins une piste à garder."))
            return
        p.marquer()                                            # une seule étape d'annulation
        medias = {}
        for k in gardees:
            ch = self.resultat[k]
            m = p.ajouter_media(ch, moteur.sonder(ch))
            m["nom"] = f"{NOMS[k]} — {(self.clip or {}).get('nom') or os.path.basename(self.fichier or '')}"
            m["separe"] = k
            medias[k] = m
        if self.clip:
            poses = poser_pistes(p, self.clip, medias, couper_origine=self.muet.isChecked())
            self.etat.setText(_("✓ {n} piste(s) posée(s) sous le plan. Edition › Annuler pour revenir.", n=len(poses)))
        else:
            self.etat.setText(_("✓ {n} piste(s) ajoutée(s) aux médias du projet (et rangées dans {d}).", n=len(medias),
                                d=S.dossier_sorties()))
        self.ed.rafraichir()
        self.b_poser.setEnabled(False)

    def closeEvent(self, ev):
        if self.lecteur is not None:
            self.lecteur.stop()
        if self._en_calcul():
            self.tache.stopper()
        super().closeEvent(ev)


def _libre(projet, piste, a, b):
    return all(c["debut"] >= b - 1e-6 or c["debut"] + (c["src_fin"] - c["src_debut"]) / (c.get("vitesse") or 1.0) <= a + 1e-6
               for c in projet.clips_piste(piste))


def poser_pistes(projet, clip, medias, couper_origine=True):
    """Pose les pistes séparées à la place exacte du plan : voix sur la piste Voix, musique et bruits sur des pistes de
    sons libres à cet endroit (une piste est ajoutée s'il le faut). Le plan d'origine peut être rendu muet."""
    v = float(clip.get("vitesse") or 1.0)
    a = float(clip["debut"])
    b = a + (float(clip["src_fin"]) - float(clip["src_debut"])) / v
    poses = []
    for k in ("voix", "musique", "bruits"):
        m = medias.get(k)
        if not m:
            continue
        candidates = ["voix"] + projet.pistes_audio() if k == "voix" else projet.pistes_audio()
        piste = next((x for x in candidates if _libre(projet, x, a, b)), None)
        if piste is None:
            piste = projet.ajouter_piste("audio")
        duree = float((m.get("fiche") or {}).get("duree") or (b - a) * v)
        c = projet.ajouter_clip(m["id"], piste=piste, debut=a, src_debut=0.0, src_fin=min(duree, (b - a) * v), vitesse=v)
        c["separe_de"] = clip["id"]
        poses.append(c)
    if couper_origine:
        clip["muet"] = True
    projet.modifie = True
    return poses
