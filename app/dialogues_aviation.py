"""Fenêtres du lot Aviation : tableau de bord (profil de vol), trajet (carte animée, mini-carte), manche à air,
sous-titres des échanges radio. Chaque fenêtre montre directement ce qu'elle va poser (courbes, carte, manche)."""
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import aviation as A, goodies as GO, theme
from .langue import _
from .widgets import CaseLongue, boutons_fr
from .taches import texte_erreur


def _sp(mini, maxi, val, suffixe="", pas=1, decimales=0):
    s = QDoubleSpinBox()
    s.setRange(mini, maxi)
    s.setDecimals(decimales)
    s.setSingleStep(pas)
    s.setValue(val)
    if suffixe:
        s.setSuffix(" " + suffixe)
    return s


def _tc(t):
    m, s = divmod(max(0.0, float(t)), 60)
    return f"{int(m)}:{s:04.1f}"


class Courbes(QWidget):
    """Les courbes du profil de vol (altitude, vitesse, cap), redessinées à chaque réglage."""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(150)
        self.courbes, self.duree = {}, 1.0

    def montrer(self, courbes, duree):
        self.courbes, self.duree = courbes, max(1.0, duree)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(36, 8, -8, -20)
        p.fillRect(self.rect(), QColor(theme.COULEURS["surface"]))
        p.setPen(QPen(QColor(theme.COULEURS["bord_leger"]), 1))
        p.drawRect(r)
        for i in range(1, 5):
            x = r.left() + r.width() * i / 5
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            p.drawText(QRectF(x - 30, r.bottom() + 2, 60, 16), Qt.AlignCenter, _tc(self.duree * i / 5))
        for cle, couleur, lib in (("altimetre", "#5ad1ff", _("altitude")), ("anemometre", "#ffd24a", _("vitesse")), ("compas", "#ff7ab3", _("cap"))):
            pts = self.courbes.get(cle) or []
            if not pts:
                continue
            vs = [v for _t, v in pts]
            lo, hi = min(vs), max(vs)
            if hi - lo < 1e-6:
                hi = lo + 1
            g = {"genre": cle, "valeurs": pts, "debut": 0, "fin": self.duree, "options": {"lisse": cle != "altimetre"}}
            p.setPen(QPen(QColor(couleur), 2))
            prec = None
            for k in range(121):
                t = self.duree * k / 120
                v = GO.valeur(g, t)
                q = QPointF(r.left() + r.width() * k / 120, r.bottom() - (v - lo) / (hi - lo) * r.height())
                if prec is not None:
                    p.drawLine(prec, q)
                prec = q
            p.drawText(QRectF(r.left() + 4, r.top() + 2 + 14 * ["altimetre", "anemometre", "compas"].index(cle), 200, 14),
                       Qt.AlignLeft, f"— {lib} ({lo:.0f} → {hi:.0f})")


class DialogueTableau(QDialog):
    """Tableau de bord de vol : instruments à poser et profil de vol qui fabrique leurs courbes."""

    def __init__(self, parent, debut, fin, reglages=None, instruments=None, etapes=None):
        super().__init__(parent)
        self.setWindowTitle(_("Tableau de bord de vol"))
        self.resize(760, 640)
        self.etapes = etapes or []
        r = dict(A.PROFIL_DEFAUT)
        r.update(reglages or {})
        v = QVBoxLayout(self)
        aide = QLabel(_("Pas de lecture de la caméra : vous donnez le profil du vol, PhilCut en tire les courbes de tous les instruments, "
                        "cohérentes entre elles et sans à-coups. Chaque instrument reste ensuite déplaçable, redimensionnable et modifiable "
                        "point par point dans l'Inspecteur."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        h = QHBoxLayout()
        gi = QGroupBox(_("Instruments"))
        vi = QVBoxLayout(gi)
        choisis = set(instruments or ["altimetre", "anemometre", "compas", "variometre"])
        self.cases = {}
        for k, lib in A.INSTRUMENTS:
            c = QCheckBox(lib)
            c.setChecked(k in choisis)
            vi.addWidget(c)
            self.cases[k] = c
        vi.addStretch(1)
        h.addWidget(gi)
        gp = QGroupBox(_("Profil de vol"))
        f = QFormLayout(gp)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.champs = {
            "terrain_ft": _sp(-1000, 15000, r["terrain_ft"], "ft", 10), "croisiere_ft": _sp(0, 25000, r["croisiere_ft"], "ft", 100),
            "arrivee_ft": _sp(-1000, 15000, r["arrivee_ft"], "ft", 10), "vitesse_kt": _sp(20, 400, r["vitesse_kt"], "kt", 5),
            "regime_croisiere": _sp(500, 6000, r["regime_croisiere"], "tr/min", 50),
            "roulage_s": _sp(0, 3600, r["roulage_s"], "s", 5), "montee_s": _sp(0, 7200, r["montee_s"], "s", 10),
            "descente_s": _sp(0, 7200, r["descente_s"], "s", 10), "atterrissage_s": _sp(0, 3600, r["atterrissage_s"], "s", 5),
            "cap_depart": _sp(0, 359, r["cap_depart"], "°", 5), "cap_arrivee": _sp(0, 359, r["cap_arrivee"], "°", 5)}
        libs = {"terrain_ft": _("Altitude du terrain de départ"), "croisiere_ft": _("Altitude de croisière"), "arrivee_ft": _("Altitude du terrain d'arrivée"),
                "vitesse_kt": _("Vitesse de croisière"), "regime_croisiere": _("Régime de croisière"), "roulage_s": _("Roulage avant le décollage"),
                "montee_s": _("Durée de la montée"), "descente_s": _("Durée de la descente"), "atterrissage_s": _("Roulage après l'atterrissage"),
                "cap_depart": _("Cap au départ"), "cap_arrivee": _("Cap à l'arrivée")}
        for k, w in self.champs.items():
            f.addRow(libs[k], w)
            w.valueChanged.connect(self._apercu)
        self.suivre = CaseLongue(_("Le cap suit le trajet de la carte ({n} étapes)", n=len(self.etapes)))
        self.suivre.setChecked(len(self.etapes) > 1)
        self.suivre.setEnabled(len(self.etapes) > 1)
        self.suivre.toggled.connect(self._apercu)
        f.addRow(self.suivre)
        h.addWidget(gp, 1)
        v.addLayout(h)
        hm = QHBoxLayout()
        self.debut = _sp(0, 36000, debut, "s", 1, 1)
        self.fin = _sp(0, 36000, fin, "s", 1, 1)
        for w in (self.debut, self.fin):
            w.valueChanged.connect(self._apercu)
        hm.addWidget(QLabel(_("De")))
        hm.addWidget(self.debut)
        hm.addWidget(QLabel(_("à")))
        hm.addWidget(self.fin)
        hm.addWidget(QLabel(_("Taille")))
        self.taille = _sp(0.08, 0.4, 0.17, "", 0.01, 2)
        hm.addWidget(self.taille)
        hm.addStretch(1)
        v.addLayout(hm)
        self.courbes = Courbes()
        v.addWidget(self.courbes, 1)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.button(QDialogButtonBox.Ok).setText(_("Poser le tableau de bord"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._apercu()

    def reglages(self):
        return {k: w.value() for k, w in self.champs.items()}

    def instruments(self):
        return [k for k, _l in A.INSTRUMENTS if self.cases[k].isChecked()]

    def etapes_suivies(self):
        return self.etapes if self.suivre.isChecked() else None

    def _apercu(self, *_a):
        d = max(10.0, self.fin.value() - self.debut.value())
        self.courbes.montrer(A.profil(d, self.reglages(), self.etapes_suivies()), d)


class DialogueTrajet(QDialog):
    """Etapes du vol, pour la carte animée et la mini-carte ; aperçu de la carte à mi-parcours."""

    def __init__(self, parent, debut, fin, options=None, avec_mini=True):
        super().__init__(parent)
        self.setWindowTitle(_("Trajet : carte animée et mini-carte"))
        self.resize(1180, 720)
        opts = dict(options or {})
        v = QVBoxLayout(self)
        aide = QLabel(_("Ajoutez les étapes dans l'ordre : cherchez un aérodrome (code OACI, nom ou ville), reprenez un de vos points, "
                        "ou double-cliquez sur la carte. Pendant la vidéo, le trait se dessine et l'avion avance au prorata des distances."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        h = QHBoxLayout()
        g = QVBoxLayout()
        from . import aerodromes as AD
        self._AD = AD
        ha = QHBoxLayout()
        self.cherche_ad = QLineEdit()
        self.cherche_ad.setPlaceholderText(_("Chercher un aérodrome : LFPG, Toulouse, Megève…"))
        self.cherche_ad.setClearButtonEnabled(True)
        self.cherche_ad.textChanged.connect(self._chercher_ad)
        self.cherche_ad.returnPressed.connect(self._ajouter_ad)
        ha.addWidget(self.cherche_ad, 1)
        b = QPushButton(_("Ajouter"))
        b.clicked.connect(self._ajouter_ad)
        ha.addWidget(b)
        g.addLayout(ha)
        self.resultats_ad = QListWidget()
        self.resultats_ad.setMaximumHeight(110)
        self.resultats_ad.itemDoubleClicked.connect(lambda _it: self._ajouter_ad())
        self.resultats_ad.hide()
        g.addWidget(self.resultats_ad)
        self.b_monde = QPushButton(_("Télécharger tous les aérodromes du monde (OurAirports, libre, environ 12 Mo)"))
        self.b_monde.setToolTip(_("Plus de 40 000 aérodromes, altisurfaces, hydrobases et héliports ; gardés sur ce poste"))
        self.b_monde.clicked.connect(self._telecharger_monde)
        self.b_monde.setVisible(not AD.installe())
        g.addWidget(self.b_monde)
        hm_ = QHBoxLayout()
        self.mes_points = QComboBox()
        self._remplir_points()
        hm_.addWidget(self.mes_points, 1)
        bmp = QPushButton(_("Ajouter ce point"))
        bmp.clicked.connect(self._ajouter_mon_point)
        hm_.addWidget(bmp)
        g.addLayout(hm_)
        hp = QHBoxLayout()
        self.nom = QLineEdit()
        self.nom.setPlaceholderText(_("Nom du point"))
        self.lat = _sp(-90, 90, 43.5, "°N", 0.01, 4)
        self.lon = _sp(-180, 180, 7.0, "°E", 0.01, 4)
        hp.addWidget(self.nom, 1)
        hp.addWidget(self.lat)
        hp.addWidget(self.lon)
        bp = QPushButton(_("Ajouter ces coordonnées"))
        bp.clicked.connect(self._ajouter_point)
        hp.addWidget(bp)
        g.addLayout(hp)
        self.liste = QListWidget()
        self.liste.setDragDropMode(QAbstractItemView.InternalMove)
        self.liste.model().rowsMoved.connect(lambda *_a: self._apercu())
        g.addWidget(self.liste, 1)
        hb = QHBoxLayout()
        for lib, f in ((_("Retirer"), self._retirer), ("↑", lambda: self._bouger(-1)), ("↓", lambda: self._bouger(1))):
            bb = QPushButton(lib)
            bb.clicked.connect(f)
            hb.addWidget(bb)
        hb.addStretch(1)
        g.addLayout(hb)
        fo = QFormLayout()
        self.fond = QComboBox()
        self.fond.addItem(_("Sombre"), "sombre")
        self.fond.addItem(_("Papier (clair)"), "clair")
        self.fond.setCurrentIndex(1 if opts.get("fond") == "clair" else 0)
        self.fond.currentIndexChanged.connect(self._apercu)
        fo.addRow(_("Fond de carte"), self.fond)
        self.attente = _sp(0, 3600, float(opts.get("attente", 0) or 0), "s", 5)
        fo.addRow(_("Immobile au départ"), self.attente)
        self.c_carte = QCheckBox(_("Carte animée (grande)"))
        self.c_carte.setChecked(True)
        self.c_mini = QCheckBox(_("Mini-carte dans un coin (centrée sur l'avion)"))
        self.c_mini.setChecked(avec_mini)
        fo.addRow(self.c_carte)
        fo.addRow(self.c_mini)
        hm = QHBoxLayout()
        self.debut = _sp(0, 36000, debut, "s", 1, 1)
        self.fin = _sp(0, 36000, fin, "s", 1, 1)
        hm.addWidget(self.debut)
        hm.addWidget(QLabel("→"))
        hm.addWidget(self.fin)
        fo.addRow(_("Moment"), hm)
        g.addLayout(fo)
        h.addLayout(g, 1)
        from PySide6.QtWidgets import QTabWidget
        from .carte_osm import CarteOSM
        self.onglets_carte = QTabWidget()
        self.carte = CarteOSM()
        self.carte.point_demande.connect(self._point_carte)
        self.onglets_carte.addTab(self.carte, _("Carte (double-clic : poser un point)"))
        self.vue = QLabel()
        self.vue.setMinimumSize(300, 300)
        self.vue.setAlignment(Qt.AlignCenter)
        self.onglets_carte.addTab(self.vue, _("Aperçu de l'animation"))
        h.addWidget(self.onglets_carte, 1)
        v.addLayout(h, 1)
        self.resume = QLabel("")
        v.addWidget(self.resume)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        for e in opts.get("etapes") or []:
            self._ajouter(e)
        self._apercu()
        if self.etapes():
            QTimer.singleShot(0, lambda: self.carte.centrer(self.etapes()))

    def _ajouter(self, e):
        it = QListWidgetItem(f"{e.get('nom', '?')}  ({e['lat']:.3f}, {e['lon']:.3f})")
        it.setData(Qt.UserRole, dict(e))
        self.liste.addItem(it)

    def _chercher_ad(self, texte):
        self.resultats_ad.clear()
        res = self._AD.chercher(texte, 40, "FR") if len(texte.strip()) >= 2 else []
        for a in res:
            it = QListWidgetItem(self._AD.libelle(a))
            it.setData(Qt.UserRole, a)
            self.resultats_ad.addItem(it)
        self.resultats_ad.setVisible(bool(res))
        if res:
            self.resultats_ad.setCurrentRow(0)

    def _ajouter_ad(self):
        it = self.resultats_ad.currentItem()
        if it is None:
            return
        self._ajouter(self._AD.etape(it.data(Qt.UserRole)))
        self.cherche_ad.clear()
        self._apercu()
        self.carte.centrer(self.etapes())

    def _telecharger_monde(self):
        from .taches import Tache
        self.b_monde.setEnabled(False)
        self.b_monde.setText(_("Téléchargement des aérodromes…"))
        t = Tache(lambda tache: self._AD.telecharger(progression=lambda f: tache.avancer(f), arret=tache.arret_demande), _("Aérodromes"))
        self._tache_ad = t
        t.progression.connect(lambda f, _x: self.b_monde.setText(_("Téléchargement des aérodromes : {p} %", p=int(f * 100))), Qt.QueuedConnection)

        def fin(n, err):
            try:
                if err:
                    self.b_monde.setEnabled(True)
                    self.b_monde.setText(_("✕ Téléchargement impossible : {e}. Réessayer", e=texte_erreur(err)[:120]))
                    return
                self.b_monde.hide()
                self.resume.setText(_("✓ {n} aérodromes disponibles : cherchez par code, nom ou ville.", n=n))
                self._chercher_ad(self.cherche_ad.text())
            except RuntimeError:
                pass
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _remplir_points(self):
        self.mes_points.clear()
        pts = self._AD.mes_points(getattr(self.parent(), "params", None))
        if not pts:
            self.mes_points.addItem(_("Mes points : aucun (double-cliquez sur la carte pour en créer)"), None)
        for p_ in pts:
            self.mes_points.addItem(f"{p_['nom']}  ({p_['lat']:.4f}, {p_['lon']:.4f})", p_)

    def _ajouter_mon_point(self):
        p_ = self.mes_points.currentData()
        if p_:
            self._ajouter(dict(p_))
            self._apercu()
            self.carte.centrer(self.etapes())

    def _point_carte(self, lat, lon):
        """Double-clic sur la carte : un point à cet endroit, nommé par vous, gardé dans « Mes points » si vous voulez."""
        from PySide6.QtWidgets import QInputDialog
        nom, ok = QInputDialog.getText(self, _("Nouveau point"), _("Nom du point ({a:.4f}, {o:.4f}) :", a=lat, o=lon),
                                       text=_("Point {n}", n=self.liste.count() + 1))
        if not ok:
            return
        nom = nom.strip() or _("Point {n}", n=self.liste.count() + 1)
        self._ajouter({"nom": nom, "lat": round(lat, 5), "lon": round(lon, 5)})
        if QMessageBox.question(self, _("Mes points"), _("Garder « {n} » dans vos points, pour vos prochains trajets (et vos autres "
                                                          "postes) ?", n=nom)) == QMessageBox.Yes:
            self._AD.enregistrer_point(getattr(self.parent(), "params", None), nom, lat, lon)
            self._remplir_points()
        self._apercu()

    def _ajouter_point(self):
        self._ajouter({"nom": self.nom.text().strip() or _("Point {n}", n=self.liste.count() + 1), "lat": self.lat.value(), "lon": self.lon.value()})
        self._apercu()
        self.carte.centrer(self.etapes())

    def _retirer(self):
        r = self.liste.currentRow()
        if r >= 0:
            self.liste.takeItem(r)
            self._apercu()

    def _bouger(self, s):
        r = self.liste.currentRow()
        if 0 <= r + s < self.liste.count() and r >= 0:
            it = self.liste.takeItem(r)
            self.liste.insertItem(r + s, it)
            self.liste.setCurrentRow(r + s)
            self._apercu()

    def etapes(self):
        return [self.liste.item(i).data(Qt.UserRole) for i in range(self.liste.count())]

    def options(self):
        return {"etapes": self.etapes(), "fond": self.fond.currentData(), "attente": self.attente.value()}

    def _apercu(self, *_a):
        if hasattr(self, "carte"):
            self.carte.etapes = self.etapes()
            self.carte.update()
        g = {"genre": "carte_trajet", "debut": 0, "fin": 10, "options": self.options()}
        img = GO.image(g, 6.0, 300)
        self.vue.setPixmap(QPixmap.fromImage(img))
        ls = A.longueurs(self.etapes())
        self.resume.setText(_("{n} étapes · {d:.0f} NM au total", n=self.liste.count(), d=sum(ls)) if ls else _("Ajoutez au moins deux étapes."))


class DialogueManche(QDialog):
    """Manche à air : vent réglé par vous ; aperçu animé."""

    def __init__(self, parent, debut, fin, options=None):
        super().__init__(parent)
        self.setWindowTitle(_("Manche à air"))
        opts = dict(options or {})
        v = QVBoxLayout(self)
        h = QHBoxLayout()
        f = QFormLayout()
        self.dir = _sp(0, 359, float(opts.get("vent_dir", 270)), "°", 10)
        self.force = _sp(0, 60, float(opts.get("vent_kt", 10)), "kt", 1)
        self.rafales = _sp(0, 80, float(opts.get("rafales_kt", 0)), "kt", 1)
        self.sens = QComboBox()
        self.sens.addItem(_("Vers la droite de l'image"), "droite")
        self.sens.addItem(_("Vers la gauche de l'image"), "gauche")
        self.sens.setCurrentIndex(1 if opts.get("sens") == "gauche" else 0)
        self.infos = QCheckBox(_("Afficher « 250° / 12 kt »"))
        self.infos.setChecked(opts.get("infos", True))
        f.addRow(_("Vent du (direction)"), self.dir)
        f.addRow(_("Force"), self.force)
        f.addRow(_("Rafales jusqu'à (0 = sans)"), self.rafales)
        f.addRow(_("La manche flotte"), self.sens)
        f.addRow(self.infos)
        hm = QHBoxLayout()
        self.debut = _sp(0, 36000, debut, "s", 1, 1)
        self.fin = _sp(0, 36000, fin, "s", 1, 1)
        hm.addWidget(self.debut)
        hm.addWidget(QLabel("→"))
        hm.addWidget(self.fin)
        f.addRow(_("Moment"), hm)
        h.addLayout(f, 1)
        self.vue = QLabel()
        self.vue.setFixedSize(200, 200)
        h.addWidget(self.vue)
        v.addLayout(h)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._t = 0.0
        self.minut = QTimer(self)
        self.minut.timeout.connect(self._anim)
        self.minut.start(80)
        self._anim()

    def options(self):
        return {"vent_dir": self.dir.value(), "vent_kt": self.force.value(), "rafales_kt": self.rafales.value(),
                "sens": self.sens.currentData(), "infos": self.infos.isChecked()}

    def _anim(self):
        self._t += 0.08
        g = {"genre": "manche_air", "debut": 0, "fin": 100, "options": self.options()}
        self.vue.setPixmap(QPixmap.fromImage(GO.image(g, self._t, 200)))


class DialogueRadio(QDialog):
    """Echanges radio trouvés dans le son : on coche ceux qui deviennent des sous-titres « radio »."""

    def __init__(self, parent, segments):
        super().__init__(parent)
        self.setWindowTitle(_("Sous-titres des échanges radio"))
        self.resize(820, 520)
        v = QVBoxLayout(self)
        n = len([s for s in segments if s[3] >= 2])
        aide = QLabel(_("{n} phrase(s) ressemblent à des échanges radio (phraséologie, alphabet, immatriculation, fréquences) : elles sont "
                        "cochées. Les autres phrases entendues sont listées décochées. Le texte se corrige en double-cliquant.", n=n))
        aide.setWordWrap(True)
        v.addWidget(aide)
        self.table = QTableWidget(len(segments), 3)
        self.table.setHorizontalHeaderLabels([_("Moment"), _("Indice radio"), _("Texte")])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        for i, (a, b, t, sc) in enumerate(segments):
            it = QTableWidgetItem(f"{_tc(a)} → {_tc(b)}")
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            it.setCheckState(Qt.Checked if sc >= 2 else Qt.Unchecked)
            it.setData(Qt.UserRole, (a, b))
            self.table.setItem(i, 0, it)
            s = QTableWidgetItem("★" * min(5, sc) or "—")
            s.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(i, 1, s)
            self.table.setItem(i, 2, QTableWidgetItem(t))
        v.addWidget(self.table, 1)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.button(QDialogButtonBox.Ok).setText(_("Poser les phrases cochées"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def resultat(self):
        out = []
        for i in range(self.table.rowCount()):
            it = self.table.item(i, 0)
            if it.checkState() == Qt.Checked:
                a, b = it.data(Qt.UserRole)
                out.append((a, b, self.table.item(i, 2).text().strip()))
        return out
