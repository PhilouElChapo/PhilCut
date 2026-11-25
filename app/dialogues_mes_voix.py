"""« Mes voix… » (1.2.0) : un seul bouton sur la ligne Voix (Fabrique musique, assistant musique, clip de groupe, bibliothèque).

Arbre (ordre alphabétique) : mes voix gardées, chacune avec « Normale » (le modèle principal) et ses variantes ; dessous, la
branche repliée « À la manière de (catalogue) ». Recherche en haut. Un clic pré-écoute l'extrait gardé (rien n'est recalculé
ni payé) ; un double-clic pose la voix. Les 7 réglages sont visibles sous l'arbre : « Revenir au modèle », « Garder comme
variante… » ; une voix changée sans être gardée ne vaut que pour ce morceau. « Nouvelle voix » : d'après un morceau
(décrite) ou réelle (timeline, micro, fichier, en ligne ; voix séparée de la musique ; case d'accord).
"""
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (QCheckBox, QDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox,
                               QPushButton, QSlider, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import voix_familles as VF
from .langue import _
from .taches import Tache, texte_erreur

ROLE = Qt.UserRole


class DialogueMesVoix(QDialog):
    """choisi : dict de voix_familles.choix / choix_catalogue (ou None si fermé sans choisir)."""

    def __init__(self, parent, params, paroles="", langue="fr", son_timeline=None, poser=None):
        super().__init__(parent)
        self.setWindowTitle(_("Mes voix"))
        self.params, self.paroles, self.langue = params, paroles, langue
        self.son_timeline, self.poser_cb = son_timeline, poser
        self.choisi, self._taches, self._lecteur, self._modifie = None, [], None, False
        self.resize(900, 700)
        v = QVBoxLayout(self)
        intro = QLabel(_("Choisissez une voix : un clic l'écoute, un double-clic la prend. Les réglages dessous changent la voix pour ce "
                         "morceau ; « Garder comme variante… » la range sous son modèle."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText(_("Chercher une voix, une variante, un style (ex. : chaude, rock, crooner)"))
        self.recherche.textChanged.connect(self.remplir)
        v.addWidget(self.recherche)
        self.arbre = QTreeWidget()
        self.arbre.setHeaderHidden(True)
        self.arbre.setWordWrap(True)
        self.arbre.currentItemChanged.connect(lambda *_a: self._selection())
        self.arbre.itemClicked.connect(lambda it, _c: self._ecouter(automatique=True))
        self.arbre.itemDoubleClicked.connect(lambda it, _c: self.utiliser())
        v.addWidget(self.arbre, 3)
        self.titre = QLabel("")
        self.titre.setWordWrap(True)
        self.titre.setStyleSheet("font-weight:600")
        v.addWidget(self.titre)
        self.desc = QLabel("")
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("color:#9ad0ff")
        v.addWidget(self.desc)
        f = QFormLayout()
        self.curseurs = {}
        for k, lib in VF.REGLAGES:
            s = QSlider(Qt.Horizontal)
            s.setRange(0, 100)
            s.valueChanged.connect(self._reglage_change)
            self.curseurs[k] = s
            f.addRow(lib, s)
        self.boite_reglages = QWidget()
        self.boite_reglages.setLayout(f)
        v.addWidget(self.boite_reglages)
        h = QHBoxLayout()
        self.b_ecouter = QPushButton(_("▶ Pré-écouter"))
        self.b_ecouter.clicked.connect(lambda: self._ecouter())
        self.b_modele = QPushButton(_("Revenir au modèle"))
        self.b_modele.clicked.connect(self._revenir)
        self.b_variante = QPushButton(_("Garder comme variante…"))
        self.b_variante.clicked.connect(self.garder_variante)
        for b in (self.b_ecouter, self.b_modele, self.b_variante):
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        h = QHBoxLayout()
        self.b_nouvelle = QPushButton(_("Nouvelle voix"))
        m = QMenu(self.b_nouvelle)
        m.addAction(_("D'après un morceau de ce poste (manière décrite)…"), lambda: self.nouvelle("fichier", reel=False))
        m.addAction(_("D'après un morceau en ligne (manière décrite)…"), lambda: self.nouvelle("en_ligne", reel=False))
        m.addSeparator()
        m.addAction(_("Voix réelle : un fichier…"), lambda: self.nouvelle("fichier", reel=True))
        m.addAction(_("Voix réelle : le son de la timeline…"), lambda: self.nouvelle("timeline", reel=True))
        m.addAction(_("Voix réelle : enregistrer au micro…"), lambda: self.nouvelle("micro", reel=True))
        m.addAction(_("Voix réelle : un morceau en ligne…"), lambda: self.nouvelle("en_ligne", reel=True))
        self.b_nouvelle.setMenu(m)
        self.b_ajout = QPushButton(_("+ Ajouter une variante"))
        ma = QMenu(self.b_ajout)
        for cle in sorted(VF.TYPES, key=lambda c: VF._net(VF.TYPES[c][0])):
            ma.addAction(VF.TYPES[cle][0], lambda c=cle: self.ajouter_type(c))
        ma.addSeparator()
        ma.addAction(_("Autre (nommée, d'après les réglages)…"), self.garder_variante)
        self.b_ajout.setMenu(ma)
        self.b_retirer = QPushButton(_("Retirer…"))
        self.b_retirer.clicked.connect(self.retirer)
        self.b_ok = QPushButton(_("Prendre cette voix"))
        self.b_ok.setDefault(True)
        self.b_ok.clicked.connect(self.utiliser)
        b_fermer = QPushButton(_("Fermer"))
        b_fermer.clicked.connect(self.reject)
        for b in (self.b_nouvelle, self.b_ajout, self.b_retirer):
            h.addWidget(b)
        h.addStretch(1)
        h.addWidget(self.b_ok)
        h.addWidget(b_fermer)
        v.addLayout(h)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        v.addWidget(self.info)
        self.remplir()

    # ------------------------------------------------------------------ arbre
    def remplir(self, *_a):
        q = self.recherche.text().strip()
        from .styles_ia import correspond
        courant = self._cle(self.arbre.currentItem())
        self.arbre.clear()
        a_choisir = None
        for e in VF.mes_voix(self.params):
            vs = VF.variantes(e)
            textes = [VF.nom_affiche(e), (e.get("donnees") or {}).get("role", ""), e.get("description", "")]
            if q and not correspond(q, " ".join(textes + [v["nom"] for v in vs])):
                continue
            it = QTreeWidgetItem([VF.nom_affiche(e)])
            it.setData(0, ROLE, ("mienne", e, None))
            it.setToolTip(0, e.get("description", ""))
            n = QTreeWidgetItem([_("Normale (modèle principal)")])
            n.setData(0, ROLE, ("mienne", e, None))
            it.addChild(n)
            for va in vs:
                c = QTreeWidgetItem([va["nom"]])
                c.setData(0, ROLE, ("mienne", e, va))
                it.addChild(c)
            self.arbre.addTopLevelItem(it)
            it.setExpanded(True)
            for k in range(it.childCount()):
                if self._cle(it.child(k)) == courant:
                    a_choisir = it.child(k)
        cat = QTreeWidgetItem([_("À la manière de (catalogue)")])
        cat.setData(0, ROLE, ("branche", None, None))
        for x in VF.catalogue(self.params):
            if q and not correspond(q, " ".join([x["nom"], x["genre"]] + [v["nom"] for v in x["variantes"]])):
                continue
            it = QTreeWidgetItem([x["nom"]])
            it.setData(0, ROLE, ("catalogue", x, None))
            n = QTreeWidgetItem([_("Normale")])
            n.setData(0, ROLE, ("catalogue", x, None))
            it.addChild(n)
            for va in sorted(x["variantes"], key=lambda v: VF._net(v["nom"])):
                c = QTreeWidgetItem([va["nom"]])
                c.setData(0, ROLE, ("catalogue", x, va))
                it.addChild(c)
            cat.addChild(it)
        self.arbre.addTopLevelItem(cat)
        cat.setExpanded(bool(q))
        if a_choisir is not None:
            self.arbre.setCurrentItem(a_choisir)
        self._selection()

    @staticmethod
    def _cle(it):
        if it is None:
            return None
        quoi, e, va = it.data(0, ROLE) or (None, None, None)
        return (quoi, (e or {}).get("id") or (e or {}).get("nom"), (va or {}).get("id"))

    def _courant(self):
        it = self.arbre.currentItem()
        return it.data(0, ROLE) if it is not None else (None, None, None)

    def _selection(self):
        quoi, e, va = self._courant()
        mienne, cat = quoi == "mienne", quoi == "catalogue"
        self.b_ok.setEnabled(mienne or cat)
        self.b_ecouter.setEnabled(mienne or cat)
        self.boite_reglages.setVisible(mienne)
        self.b_modele.setVisible(mienne)
        self.b_variante.setEnabled(mienne)
        self.b_ajout.setEnabled(mienne)
        self.b_retirer.setEnabled(mienne)
        if mienne:
            reg = (va or {}).get("reglages") or VF.reglages_de(e)
            self._poser_curseurs(reg)
            self.titre.setText(VF.nom_affiche(e) + (" › " + va["nom"] if va else ""))
            vd = (va or {}).get("voix_decrite") or (e.get("donnees") or {}).get("voix_decrite") or {}
            self.desc.setText(vd.get("fr") or VF.decrire(reg)[1])
        elif cat:
            self.titre.setText(e["nom"] + " " + _("(à la manière de)") + (" › " + va["nom"] if va else ""))
            self.desc.setText(_("Décrite au moteur, jamais copiée : {d}", d=(va or {}).get("en") or e["en"]))
        else:
            self.titre.setText("")
            self.desc.setText("")
        self._modifie = False

    def _poser_curseurs(self, reg):
        for k, s in self.curseurs.items():
            s.blockSignals(True)
            s.setValue(int(reg.get(k, 50)))
            s.blockSignals(False)

    def reglages(self):
        return {k: s.value() for k, s in self.curseurs.items()}

    def _reglage_change(self, *_a):
        self._modifie = True
        self.desc.setText(VF.decrire(self.reglages())[1] + "  " + _("(changée pour ce morceau)"))

    def _revenir(self):
        self._selection()

    # ------------------------------------------------------------------ prendre
    def utiliser(self):
        quoi, e, va = self._courant()
        if quoi == "mienne":
            c = VF.choix(e, va)
            if self._modifie:                         # pour ce morceau seulement : le modèle ne change pas
                reg = self.reglages()
                en, fr = VF.decrire(reg)
                c.update(reglages=reg, voix_decrite={"en": en, "fr": fr, "fichier": c["nom"] + " " + _("(changée)")}, modifiee=True)
        elif quoi == "catalogue":
            c = VF.choix_catalogue(e, va)
        else:
            return
        self.choisi = c
        if self.poser_cb:
            self.poser_cb(c)
        self.accept()

    # ------------------------------------------------------------------ pré-écoute
    def _extrait_catalogue(self, e, va):
        nom = VF._net(e["nom"] + "_" + ((va or {}).get("id") or "normale"))
        return os.path.join(VF.dossier_extraits(), "".join(ch if ch.isalnum() else "_" for ch in nom)[:80] + ".wav")

    def _ecouter(self, automatique=False):
        quoi, e, va = self._courant()
        if quoi not in ("mienne", "catalogue"):
            return
        if quoi == "mienne" and not self._modifie:
            ch = VF.extrait_de(e, va)
        elif quoi == "catalogue":
            ch = self._extrait_catalogue(e, va)
        else:
            ch = ""
        if ch and os.path.exists(ch):
            return self._jouer(ch)
        if automatique:                                     # un simple clic ne lance jamais de calcul
            self.info.setText(_("Pas encore d'extrait pour cette voix : « ▶ Pré-écouter » le fabrique (sur ce poste ou par le cloud)."))
            return
        ou = self._ou_calculer()
        if not ou:
            return
        if quoi == "mienne":
            c = VF.choix(e, va)
            en = VF.decrire(self.reglages())[0] if self._modifie else c["voix_decrite"]["en"]
            ref = c.get("reference")
        else:
            en, ref = (va or {}).get("en") or e["en"], None
        sortie = os.path.join(VF.dossier_extraits(), f"pre_{os.getpid()}_{id(self)}_{len(self._taches)}.wav") \
            if not (quoi == "catalogue") else self._extrait_catalogue(e, va)
        params, paroles, langue, modifie = self.params, self.paroles, self.langue, self._modifie

        def travail(t):
            return VF.preecoute(en, paroles, sortie, params, langue, ou, ref, 10, lambda f, x="": t.avancer(f, x), lambda: t.arret)

        def fin(r, err):
            if err:
                if not isinstance(err, InterruptedError):
                    self.info.setText(_("✕ Pré-écoute non faite : {e}", e=texte_erreur(err)[:300]))
                return
            ch2 = r if isinstance(r, str) else sortie
            if quoi == "mienne" and not modifie:            # gardé avec la voix : la prochaine fois, rien n'est refait
                try:
                    VF.garder_extrait(self.params, e, ch2, va)
                except Exception:      # noqa: BLE001
                    pass
            self.info.setText(_("✓ Extrait prêt."))
            self._jouer(ch2)
        self.info.setText(_("Fabrication de l'extrait…"))
        t = Tache(travail, _("Pré-écoute d'une voix"))
        t.fini.connect(lambda r, err: fin(r, err), Qt.QueuedConnection)
        t.progression.connect(lambda f, x: self.info.setText(f"{int(f * 100)} % — {x}"), Qt.QueuedConnection)
        self._taches.append(t)
        t.start()

    def _ou_calculer(self):
        if getattr(self, "_test_ou", None):
            return self._test_ou
        m = QMessageBox(self)
        m.setWindowTitle(_("Pré-écoute"))
        m.setText(_("Cette voix n'a pas encore d'extrait. Le fabriquer (environ 10 s chantées) :"))
        b_local = m.addButton(_("Sur ce poste (gratuit, environ 1 min)"), QMessageBox.AcceptRole)
        b_cloud = m.addButton(_("Par le cloud (fal.ai, environ {p} $)", p=f"{VF.prix_cloud(10):.3f}".replace(".", ",")), QMessageBox.AcceptRole)
        m.addButton(_("Annuler"), QMessageBox.RejectRole)
        m.exec()
        return "local" if m.clickedButton() is b_local else "cloud" if m.clickedButton() is b_cloud else None

    def _jouer(self, ch):
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        if self._lecteur is None:
            self._lecteur = QMediaPlayer(self)
            self._sortie_son = QAudioOutput(self)
            self._lecteur.setAudioOutput(self._sortie_son)
        self._lecteur.stop()
        self._lecteur.setSource(QUrl.fromLocalFile(ch))
        self._lecteur.play()
        self.info.setText(_("▶ Lecture de l'extrait."))

    def done(self, r):
        if self._lecteur is not None:
            self._lecteur.stop()
        super().done(r)

    # ------------------------------------------------------------------ variantes
    def _nom_demande(self, titre, texte, defaut=""):
        if getattr(self, "_test_nom", None) is not None:
            return self._test_nom
        nom, ok = QInputDialog.getText(self, titre, texte, text=defaut)
        return nom.strip() if ok else ""

    def garder_variante(self):
        quoi, e, va = self._courant()
        if quoi != "mienne":
            return
        nom = self._nom_demande(_("Garder comme variante"), _("Nom de la variante (ex. : chaude, aiguë, rapide, solo) :"))
        if not nom:
            return
        e2 = VF.ajouter_variante(self.params, e, nom, self.reglages())
        self.info.setText(_("✓ Variante « {n} » gardée sous « {m} ».", n=nom, m=VF.nom_affiche(e2)))
        self._recharger(e2["id"], VF._net(nom))

    def ajouter_type(self, cle):
        quoi, e, _va = self._courant()
        if quoi != "mienne":
            return
        v = VF.variante_type(cle, VF.reglages_de(e))
        e2 = VF.ajouter_variante(self.params, e, v["nom"], v["reglages"], v["mots"])
        self.info.setText(_("✓ Variante « {n} » ajoutée : réglez-la si besoin, puis « Garder comme variante… ».", n=v["nom"]))
        self._recharger(e2["id"], VF._net(v["nom"]))

    def _recharger(self, ident, nom_variante=None):
        self.remplir()
        for i in range(self.arbre.topLevelItemCount()):
            it = self.arbre.topLevelItem(i)
            q, e, _v = it.data(0, ROLE) or (None, None, None)
            if q == "mienne" and e["id"] == ident:
                cible = it.child(0)
                for k in range(it.childCount()):
                    va = it.child(k).data(0, ROLE)[2]
                    if va and nom_variante and VF._net(va["nom"]) == nom_variante:
                        cible = it.child(k)
                self.arbre.setCurrentItem(cible)
                return

    def retirer(self):
        quoi, e, va = self._courant()
        if quoi != "mienne":
            return
        quoi_txt = _("la variante « {v} »", v=va["nom"]) if va else _("la voix « {n} » et ses variantes", n=VF.nom_affiche(e))
        if not getattr(self, "_test_oui", False) and QMessageBox.question(
                self, _("Retirer"), _("Retirer {q} ? (elle va dans la corbeille de la bibliothèque si c'est la voix entière)", q=quoi_txt)) \
                != QMessageBox.Yes:
            return
        if va:
            VF.retirer_variante(self.params, e, va["id"])
        else:
            from . import bibliotheque_creations as B
            B.retirer(self.params, e)
        self.remplir()

    # ------------------------------------------------------------------ nouvelle voix
    def nouvelle(self, source, reel):
        """Voix décrite d'après un morceau, ou voix réelle (timeline, micro, fichier, en ligne) : voix séparée de la musique,
        mesurée, puis gardée comme modèle principal (case d'accord pour une voix réelle)."""
        if source == "en_ligne":
            from .dialogues_musique_ia import DialogueMusiqueEnLigne
            DialogueMusiqueEnLigne(self, self.params, utiliser=lambda ch: self._analyser(ch, reel, True),
                                   libelle_utiliser=_("Prendre sa voix") if reel else _("Décrire sa voix")).exec()
            return
        if source == "timeline":
            if not self.son_timeline:
                QMessageBox.information(self, _("Voix réelle"), _("Pas de timeline ici : choisissez un fichier ou le micro."))
                return
            try:
                ch = self.son_timeline()
            except Exception as e:      # noqa: BLE001
                QMessageBox.information(self, _("Voix réelle"), texte_erreur(e))
                return
            return self._analyser(ch, reel, True, passage_deja=True) if ch else None
        if source == "micro":
            from .dialogues_voix import DialogueEnregistrement
            d = DialogueEnregistrement(self, self.params)
            if d.exec() != QDialog.Accepted or not d.chemin:
                return
            return self._analyser(d.chemin, reel, False, passage_deja=True)
        from .widgets import ouvrir_fichier
        ch = ouvrir_fichier(self, _("Morceau ou voix"), _("Sons") + " (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.opus *.mp4 *.mkv *.webm)",
                            "musique", self.params)
        if ch:
            self._analyser(ch, reel, True)

    def _accord(self, nom):
        if getattr(self, "_test_accord", None) is not None:
            return self._test_accord
        d = QDialog(self)
        d.setWindowTitle(_("Voix réelle"))
        v = QVBoxLayout(d)
        lb = QLabel(_("« {n} » sera gardée comme voix réelle : son timbre servira au moteur de musique.", n=nom))
        lb.setWordWrap(True)
        v.addWidget(lb)
        c = QCheckBox(_("C'est ma voix, ou celle d'une personne qui m'a donné son accord pour cet usage."))
        v.addWidget(c)
        h = QHBoxLayout()
        ok, ann = QPushButton(_("Garder")), QPushButton(_("Annuler"))
        ok.setEnabled(False)
        c.toggled.connect(ok.setEnabled)
        ok.clicked.connect(d.accept)
        ann.clicked.connect(d.reject)
        h.addStretch(1)
        h.addWidget(ok)
        h.addWidget(ann)
        v.addLayout(h)
        return d.exec() == QDialog.Accepted and c.isChecked()

    def _analyser(self, ch, reel, separer, passage_deja=False):
        from .dialogues_musique_ia import choisir_passage
        passage = None
        if not passage_deja:
            passage = choisir_passage(self, ch, _("Passage où la voix chante"),
                                      _("Choisissez 15 à 40 secondes où l'on entend bien la voix."))
            if not passage:
                return
        if separer and not getattr(self, "_test_sans_separation", False):
            r = QMessageBox.question(self, _("Voix seule ?"), _("Faut-il séparer la voix de la musique ? (Non si le fichier ne contient "
                                                                 "que la voix)"), QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            separer = r == QMessageBox.Yes
        elif getattr(self, "_test_sans_separation", False):
            separer = False
        from . import creatif, musique_ia as MI
        if separer:
            manque = creatif.separation_manquante(self.params)
            if manque:
                QMessageBox.information(self, _("Voix"), manque)
                return
        defaut = os.path.splitext(os.path.basename(ch))[0][:40]
        nom = self._nom_demande(_("Nouvelle voix"), _("Nom de la voix (ex. : Archangel, ma voix) :"), defaut)
        if not nom:
            return
        if reel and not self._accord(nom):
            return
        params = self.params

        def travail(t):
            src = MI.extraire_passage(ch, *passage) if passage else ch
            voix = src
            if separer:
                voix = creatif.extraire_voix(src, os.path.join(VF.dossier_extraits(), f"voix_{os.getpid()}_{len(self._taches)}.wav"),
                                             params, lambda f, x="": t.avancer(0.05 + 0.75 * f, x), lambda: t.arret)
            r = MI.decrire_voix(voix, lambda f, x="": t.avancer(0.8 + 0.2 * f, x), lambda: t.arret)
            r["voix_seule"] = voix
            return r

        def fin(r, err):
            if err:
                if not isinstance(err, InterruptedError):
                    self.info.setText(_("✕ Voix non analysée : {e}", e=texte_erreur(err)[:300]))
                return
            reg = VF.reglages_depuis_mesures(r.get("mesures"))
            if reel:                                  # la déclaration suit le fichier (musique_ia.creer la vérifie)
                MI.declarer(r["voix_seule"], voix_accord=True, voix_de=nom)
            e = VF.garder_principal(self.params, nom, reg, {"en": r.get("en", ""), "fr": r.get("fr", ""), "mesures": r.get("mesures")},
                                    extrait=r["voix_seule"] if reel else None, reel=reel, voix_seule=r["voix_seule"] if reel else None,
                                    accord=reel, source=os.path.basename(ch))
            self.info.setText(_("✓ « {n} » gardée comme modèle principal : ajoutez ses variantes (chaude, aiguë…).", n=VF.nom_affiche(e)))
            self._recharger(e["id"])
        self.info.setText(_("Analyse de la voix…"))
        t = Tache(travail, _("Nouvelle voix"))
        t.fini.connect(lambda r, err: fin(r, err), Qt.QueuedConnection)
        t.progression.connect(lambda f, x: self.info.setText(f"{int(f * 100)} % — {x}"), Qt.QueuedConnection)
        self._taches.append(t)
        t.start()


def choisir_voix(parent, params, paroles="", langue="fr", son_timeline=None):
    """Ouvre « Mes voix… » ; renvoie le choix (voix_familles.choix…) ou None."""
    d = DialogueMesVoix(parent, params, paroles, langue, son_timeline)
    if getattr(parent, "_test_mes_voix", None):
        return parent._test_mes_voix(d)
    d.exec()
    return d.choisi
