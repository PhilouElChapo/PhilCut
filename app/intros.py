"""Intros et logos animés « modernes » (0.5.0) : le savoir-faire du motion design, programmé.

Ce qui fait moderne, et que les anciens modèles n'avaient pas :
- des courbes de mouvement (départ rapide, arrivée en douceur, léger rebond) au lieu de mouvements linéaires ;
- des polices actuelles livrées avec PhilCut (Poppins, Bebas Neue, Anton) et l'espacement des lettres travaillé ;
- des apparitions par masque, lettre par lettre, un flou de mouvement, des fonds vivants (dégradés qui respirent,
  ou les premières images de votre film floutées), du verre dépoli, des balayages de lumière ;
- trois familles : Punchy (réseaux), Clean minimal, Cinéma.
Chaque image est dessinée par QPainter (identique à l'aperçu), puis encodée en clip par FFmpeg.
"""
import math, os, random, tempfile

from .langue import _

FAMILLES = {"punchy": _("Punchy (réseaux)"), "clean": _("Clean minimal"), "cinema": _("Cinéma")}

MODELES = {
    "slam": ("punchy", _("Mots qui claquent"), _("Chaque mot arrive en force, petite secousse et flash ; idéal sur un temps fort.")),
    "decoupe": ("punchy", _("Titre découpé"), _("Le titre arrive en deux moitiés qui glissent et se rejoignent, barre de couleur.")),
    "contour": ("punchy", _("Contour puis couleur"), _("Le contour se trace, la couleur remplit les lettres, ombre décalée.")),
    "glitch_net": ("punchy", _("Glitch net"), _("Tranches décalées et couleurs séparées, puis l'image se stabilise ; sous-titre tapé.")),
    "masque": ("clean", _("Lettres qui montent"), _("Les lettres sortent d'un masque une à une, un trait fin se dessine.")),
    "verre": ("clean", _("Carte en verre dépoli"), _("Une carte translucide glisse sur un fond qui respire, le texte apparaît dedans.")),
    "espacement": ("clean", _("Espacement qui se resserre"), _("Lettres espacées et floues qui se resserrent et deviennent nettes.")),
    "cinema": ("cinema", _("Générique de cinéma"), _("Bandes noires, lettres très espacées, poussée lente, balayage de lumière.")),
    "horizon": ("cinema", _("Ligne d'horizon"), _("Un trait doré s'ouvre ; le titre monte au-dessus, le sous-titre descend dessous.")),
    "lumiere": ("cinema", _("Fuites de lumière"), _("Lumières chaudes qui passent, le titre sort du flou.")),
}

FONDS = {"degrade": _("Dégradé vivant"), "film": _("Premières images du film, floutées"), "uni": _("Couleur unie")}
# « transparent » : posé directement sur le film (Goodie « Titre d'ouverture animé »), avec un léger voile pour la lisibilité

PALETTES = {
    "punchy": {"texte": "#ffffff", "accent": "#ff3b30", "accent2": "#ffd21f", "fond": "#0d0d12", "taches": ["#ff3b30", "#7b2ff7", "#ff8c1a"]},
    "clean": {"texte": "#ffffff", "accent": "#7cc4ff", "accent2": "#ffffff", "fond": "#0f1115", "taches": ["#3a7bd5", "#8e9bff", "#00d2ff"]},
    "cinema": {"texte": "#f4efe6", "accent": "#e8c27a", "accent2": "#9fc7ff", "fond": "#050507", "taches": ["#ff9a3c", "#ff4f6d", "#ffd36b"]},
}


# ------------------------------------------------------------------ courbes de mouvement
def borne(t):
    return 0.0 if t <= 0 else (1.0 if t >= 1 else t)


def expo(t):
    t = borne(t)
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def rebond(t, s=1.7):
    t = borne(t) - 1
    return 1 + (s + 1) * t ** 3 + s * t ** 2


def doux(t):
    t = borne(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ressort(t):
    t = borne(t)
    return 1 - math.exp(-6 * t) * math.cos(11 * t)


def phase(sec, debut, duree):
    return borne((sec - debut) / max(1e-6, duree))


# ------------------------------------------------------------------ outils de dessin
def police(famille, px, poids=None):
    from PySide6.QtGui import QFont
    f = QFont(famille)
    f.setPixelSize(max(4, int(px)))
    if poids is not None:
        f.setWeight(QFont.Weight(poids))
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


def lettres(texte, f, espacement=0.0):
    """[(chemin de la lettre, x, largeur)], largeur totale ; lettre par lettre, avec l'espacement voulu (en em)."""
    from PySide6.QtGui import QFontMetricsF, QPainterPath
    fm = QFontMetricsF(f)
    out, x = [], 0.0
    ex = espacement * f.pixelSize()
    for ch in texte:
        ch_ = QPainterPath()
        ch_.addText(0, 0, f, ch)
        w = fm.horizontalAdvance(ch)
        out.append((ch_, x, w))
        x += w + ex
    return out, max(0.0, x - ex), fm


def chemin_texte(texte, f, espacement=0.0):
    """Chemin du texte centré horizontalement sur 0, ligne de base à 0."""
    from PySide6.QtGui import QPainterPath
    ls, total, fm = lettres(texte, f, espacement)
    ch = QPainterPath()
    for c, x, _w in ls:
        ch.addPath(c.translated(x - total / 2, 0))
    return ch, total, fm


def ajuster(texte, famille, px, poids, largeur_max, espacement=0.0):
    """Police réduite si le texte dépasse la largeur."""
    f = police(famille, px, poids)
    _c, w, _fm = chemin_texte(texte, f, espacement)
    if w > largeur_max:
        f = police(famille, px * largeur_max / w, poids)
    return f


def flouter(img, force):
    """Flou rapide : réduction puis agrandissement lissé (deux passes)."""
    from PySide6.QtCore import Qt
    if force <= 0.5:
        return img
    w, h = img.width(), img.height()
    k = max(1.0, force)
    petit = img.scaled(max(2, int(w / k)), max(2, int(h / k)), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    petit = petit.scaled(max(2, int(w / k * 2)), max(2, int(h / k * 2)), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return petit.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


class Contexte:
    def __init__(self, modele, texte, sous_texte, L, H, duree, fond, couleurs, image_film, logo):
        from PySide6.QtGui import QColor, QImage
        self.modele, self.L, self.H, self.duree = modele, L, H, duree
        self.famille = MODELES.get(modele, MODELES["masque"])[0]
        pal = dict(PALETTES[self.famille])
        pal.update({k: v for k, v in (couleurs or {}).items() if v})
        self.pal = pal
        self.c = {k: QColor(v) for k, v in pal.items() if isinstance(v, str)}
        self.texte = (texte or _("Votre titre")).strip()
        self.sous = (sous_texte or "").strip()
        self.fond = fond if fond in FONDS or fond == "transparent" else "degrade"
        self.film = None
        if image_film and self.fond == "film":
            im = QImage(image_film) if isinstance(image_film, str) else image_film
            if im is not None and not im.isNull():
                from PySide6.QtCore import Qt
                im = im.scaled(L, H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                im = im.copy((im.width() - L) // 2, (im.height() - H) // 2, L, H)
                self.film = flouter(im, 18)
        self.logo = None
        if logo and os.path.exists(logo):
            from PySide6.QtGui import QImage as QI
            lg = QI(logo)
            if not lg.isNull():
                from PySide6.QtCore import Qt
                self.logo = lg.scaledToHeight(int(H * 0.26), Qt.SmoothTransformation)
        rng = random.Random(7)
        self.grain = QImage(256, 256, QImage.Format_ARGB32_Premultiplied)
        for y in range(256):
            for x in range(256):
                v = rng.randint(0, 255)
                self.grain.setPixelColor(x, y, QColor(v, v, v, 10))
        self.y_texte = H * (0.6 if self.logo is not None else 0.5)


# ------------------------------------------------------------------ fonds
def dessiner_fond(p, ctx, sec):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QPainter, QRadialGradient
    L, H = ctx.L, ctx.H
    if ctx.fond == "transparent":
        voile = QRadialGradient(QPointF(L / 2, ctx.y_texte), L * 0.55)
        a = int(110 * min(1.0, sec / 0.4, max(0.0, (ctx.duree - sec) / 0.45)))
        voile.setColorAt(0, QColor(0, 0, 0, a))
        voile.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(QRectF(0, 0, L, H), QBrush(voile))
        return
    p.fillRect(QRectF(0, 0, L, H), ctx.c["fond"])
    if ctx.fond == "film" and ctx.film is not None:
        s = 1.0 + 0.06 * sec / max(1.0, ctx.duree)
        p.save()
        p.translate(L / 2, H / 2)
        p.scale(s, s)
        p.translate(-L / 2, -H / 2)
        p.drawImage(QRectF(0, 0, L, H), ctx.film)
        p.restore()
        p.fillRect(QRectF(0, 0, L, H), QColor(0, 0, 0, 120))
    elif ctx.fond == "degrade":
        p.setCompositionMode(QPainter.CompositionMode_Screen)
        for k, coul in enumerate(ctx.pal.get("taches") or []):
            a = sec * 0.35 + k * 2.1
            cx = L * (0.5 + 0.32 * math.cos(a * 0.9 + k))
            cy = H * (0.5 + 0.28 * math.sin(a * 0.7 + k * 1.7))
            r = H * (0.75 + 0.15 * math.sin(a))
            g = QRadialGradient(QPointF(cx, cy), r)
            c0 = QColor(coul)
            c0.setAlpha(150)
            c1 = QColor(coul)
            c1.setAlpha(0)
            g.setColorAt(0, c0)
            g.setColorAt(1, c1)
            p.setBrush(QBrush(g))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx, cy), r, r)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.fillRect(QRectF(0, 0, L, H), QColor(0, 0, 0, 70))
    # vignettage et grain léger : l'image respire, rien n'est « plat »
    v = QRadialGradient(QPointF(L / 2, H / 2), max(L, H) * 0.75)
    v.setColorAt(0.55, QColor(0, 0, 0, 0))
    v.setColorAt(1, QColor(0, 0, 0, 150))
    p.fillRect(QRectF(0, 0, L, H), QBrush(v))
    p.save()
    p.translate((int(sec * 37) % 7) * 13, (int(sec * 53) % 5) * 11)
    p.fillRect(QRectF(-100, -100, L + 200, H + 200), QBrush(ctx.grain))
    p.restore()


def dessiner_logo(p, ctx, sec):
    if ctx.logo is None:
        return
    from PySide6.QtCore import QRectF
    e = rebond(phase(sec, 0.05, 0.5))
    a = phase(sec, 0.05, 0.25)
    w, h = ctx.logo.width() * e, ctx.logo.height() * e
    p.save()
    p.setOpacity(a)
    p.drawImage(QRectF(ctx.L / 2 - w / 2, ctx.H * 0.33 - h / 2, w, h), ctx.logo)
    p.restore()


def sous_titre(p, ctx, sec, debut, couleur=None, poids=400, espacement=0.18, monte=True, famille="Poppins", taille=0.042, y=None):
    if not ctx.sous:
        return
    from PySide6.QtCore import Qt
    f = ajuster(ctx.sous, famille, ctx.H * taille, poids, ctx.L * 0.8, espacement)
    ch, w, fm = chemin_texte(ctx.sous, f, espacement)
    e = expo(phase(sec, debut, 0.7))
    p.save()
    p.setOpacity(phase(sec, debut, 0.35))
    base = ctx.y_texte + ctx.H * 0.12 if y is None else y + fm.ascent()
    p.translate(ctx.L / 2, base + (1 - e) * ctx.H * 0.03 * (1 if monte else -1))
    p.setPen(Qt.NoPen)
    p.setBrush(couleur or ctx.c["texte"])
    p.drawPath(ch)
    p.restore()


# ------------------------------------------------------------------ les modèles
def _slam(p, ctx, sec):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor
    L, H = ctx.L, ctx.H
    mots = ctx.texte.upper().split() or [ctx.texte.upper()]
    f = ajuster(" ".join(mots), "Anton", H * 0.2, None, L * 0.86, 0.02)
    fm_w = [chemin_texte(m, f, 0.02)[1] for m in mots]
    esp = f.pixelSize() * 0.28
    total = sum(fm_w) + esp * (len(mots) - 1)
    x = -total / 2
    secousse = 0.0
    flash = 0.0
    for i, (m, w) in enumerate(zip(mots, fm_w)):
        t0 = 0.12 + i * 0.22
        ph = phase(sec, t0, 0.28)
        if ph <= 0:
            x += w + esp
            continue
        s = 2.4 - 1.4 * rebond(ph, 1.2)
        imp = sec - (t0 + 0.2)
        if 0 <= imp < 0.25:
            secousse = max(secousse, (1 - imp / 0.25))
            flash = max(flash, 1 - imp / 0.15) if imp < 0.15 else flash
        ch, _w, _fm = chemin_texte(m, f, 0.02)
        p.save()
        p.translate(L / 2 + x + w / 2, ctx.y_texte + f.pixelSize() * 0.36)
        p.scale(s, s)
        p.setOpacity(phase(sec, t0, 0.08))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawPath(ch.translated(H * 0.006, H * 0.008))
        p.setBrush(ctx.c["accent2"] if i % 2 else ctx.c["texte"])
        p.drawPath(ch)
        p.restore()
        x += w + esp
    if flash > 0:
        p.fillRect(QRectF(0, 0, L, H), QColor(255, 255, 255, int(90 * flash)))
    # barre de couleur sous le titre
    fin_mots = 0.12 + len(mots) * 0.22
    e = expo(phase(sec, fin_mots, 0.45))
    if e > 0:
        p.fillRect(QRectF(L / 2 - total / 2, ctx.y_texte + f.pixelSize() * 0.5, total * e, H * 0.012), ctx.c["accent"])
    sous_titre(p, ctx, sec, fin_mots + 0.1, poids=600, espacement=0.12, y=ctx.y_texte + f.pixelSize() * 0.5 + H * 0.04)
    return secousse


def _decoupe(p, ctx, sec):
    from PySide6.QtCore import QRectF, Qt
    L, H = ctx.L, ctx.H
    f = ajuster(ctx.texte.upper(), "Bebas Neue", H * 0.26, None, L * 0.88, 0.04)
    ch, w, fm = chemin_texte(ctx.texte.upper(), f, 0.04)
    br = ch.boundingRect()
    y = ctx.y_texte + br.height() / 2
    e = expo(phase(sec, 0.1, 0.8))
    barre = expo(phase(sec, 0.0, 0.6))
    p.fillRect(QRectF(L / 2 - w * 0.55, y - br.height() * 0.3, w * 1.1 * barre, br.height() * 0.42), ctx.c["accent"])
    for haut, sens in ((True, -1), (False, 1)):
        p.save()
        clip = QRectF(-L, -H, 3 * L, H + br.center().y()) if haut else QRectF(-L, br.center().y(), 3 * L, 2 * H)
        p.translate(L / 2 + sens * (1 - e) * L * 0.7, y)
        p.setClipRect(clip)
        p.setPen(Qt.NoPen)
        p.setBrush(ctx.c["texte"])
        p.drawPath(ch)
        p.restore()
    sous_titre(p, ctx, sec, 0.75, poids=300, espacement=0.4, famille="Poppins", y=y + H * 0.04)


def _contour(p, ctx, sec):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QPen
    L, H = ctx.L, ctx.H
    f = ajuster(ctx.texte.upper(), "Poppins", H * 0.17, 900, L * 0.86, 0.01)
    ch, w, fm = chemin_texte(ctx.texte.upper(), f, 0.01)
    br = ch.boundingRect()
    y = ctx.y_texte + br.height() / 2
    trace = doux(phase(sec, 0.05, 0.7))
    rempli = expo(phase(sec, 0.55, 0.6))
    ombre = expo(phase(sec, 0.9, 0.5)) * H * 0.014
    p.save()
    p.translate(L / 2, y)
    if ombre > 0:
        p.setPen(Qt.NoPen)
        p.setBrush(ctx.c["accent"])
        p.drawPath(ch.translated(ombre, ombre))
    p.save()
    p.setClipRect(QRectF(br.left() - 10, br.top() - 10, (br.width() + 20) * trace, br.height() + 20))
    p.setPen(QPen(ctx.c["texte"], max(2.0, H * 0.004)))
    p.setBrush(Qt.NoBrush)
    p.drawPath(ch)
    p.restore()
    if rempli > 0:
        p.setClipRect(QRectF(br.left() - 10, br.top() - 10, (br.width() + 20) * rempli, br.height() + 20))
        p.setPen(Qt.NoPen)
        p.setBrush(ctx.c["texte"])
        p.drawPath(ch)
    p.restore()
    sous_titre(p, ctx, sec, 1.0, couleur=ctx.c["accent2"], poids=600, espacement=0.1, y=y + H * 0.04)


def _glitch_net(p, ctx, sec):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QPainter
    L, H = ctx.L, ctx.H
    f = ajuster(ctx.texte.upper(), "Poppins", H * 0.15, 900, L * 0.86, 0.0)
    ch, w, fm = chemin_texte(ctx.texte.upper(), f, 0.0)
    br = ch.boundingRect()
    y = ctx.y_texte + br.height() / 2
    force = max(0.0, 1 - sec / 0.7) + (0.6 if 1.6 < sec % 2.2 < 1.68 else 0)
    rng = random.Random(int(sec * 30))
    p.save()
    p.translate(L / 2, y)
    p.setPen(Qt.NoPen)
    if force > 0.02:
        p.setCompositionMode(QPainter.CompositionMode_Screen)
        for dx, coul in ((-1, QColor(255, 40, 80)), (1, QColor(40, 220, 255))):
            p.setBrush(coul)
            p.drawPath(ch.translated(dx * H * 0.012 * force, 0))
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        tranches = 9
        for k in range(tranches):
            h = br.height() / tranches
            p.save()
            p.setClipRect(QRectF(br.left() - L, br.top() + k * h, br.width() + 2 * L, h + 1))
            p.translate(rng.uniform(-1, 1) * H * 0.05 * force if rng.random() < 0.5 else 0, 0)
            p.setBrush(ctx.c["texte"])
            p.drawPath(ch)
            p.restore()
    else:
        p.setBrush(ctx.c["texte"])
        p.drawPath(ch)
    p.restore()
    p.setOpacity(phase(sec, 0.1, 0.15))
    if ctx.sous:                                   # sous-titre tapé, avec curseur
        n = int(len(ctx.sous) * phase(sec, 0.8, 0.04 * len(ctx.sous)))
        f2 = police("Poppins", H * 0.04, 500)
        vis = ctx.sous[:n] + ("▍" if int(sec * 3) % 2 == 0 else " ")
        ch2, w2, _fm = chemin_texte(ctx.sous, f2, 0.06)
        ch3, _w3, _fm3 = chemin_texte(vis, f2, 0.06)
        p.save()
        p.translate(L / 2 - w2 / 2 + _w3 / 2, ctx.y_texte + H * 0.13)
        p.setPen(Qt.NoPen)
        p.setBrush(ctx.c["accent2"])
        p.drawPath(ch3)
        p.restore()
    p.setOpacity(1)


def _masque(p, ctx, sec):
    from PySide6.QtCore import QRectF, Qt
    L, H = ctx.L, ctx.H
    f = ajuster(ctx.texte, "Poppins", H * 0.13, 600, L * 0.84, 0.0)
    ls, total, fm = lettres(ctx.texte, f, 0.0)
    y = ctx.y_texte + fm.capHeight() / 2
    p.save()
    p.setClipRect(QRectF(0, y - fm.ascent() * 1.05, L, fm.ascent() * 1.05 + fm.descent() + 2))
    p.setPen(Qt.NoPen)
    p.setBrush(ctx.c["texte"])
    sortie = phase(sec, ctx.duree - 0.55, 0.45)
    for i, (c, x, _w) in enumerate(ls):
        e = expo(phase(sec, 0.1 + i * 0.035, 0.75))
        dy = (1 - e) * fm.ascent() * 1.1 - expo(phase(sortie, i * 0.02, 0.6)) * fm.ascent() * 1.2
        p.drawPath(c.translated(L / 2 - total / 2 + x, y + dy))
    p.restore()
    e = expo(phase(sec, 0.55, 0.9))
    lw = total * 0.6 * e
    p.fillRect(QRectF(L / 2 - lw / 2, y + fm.descent() + H * 0.025, lw, max(1.5, H * 0.0025)), ctx.c["accent"])
    sous_titre(p, ctx, sec, 0.85, poids=300, espacement=0.3)


def _verre(p, ctx, sec, fond_img):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QPainterPath, QPen
    L, H = ctx.L, ctx.H
    f = ajuster(ctx.texte, "Poppins", H * 0.09, 600, L * 0.6, 0.0)
    ch, w, fm = chemin_texte(ctx.texte, f, 0.0)
    cw = max(w + H * 0.16, L * 0.38)
    chh = H * (0.25 if ctx.sous else 0.19)
    e = expo(phase(sec, 0.05, 0.9))
    s = 0.92 + 0.08 * e
    r = QRectF(L / 2 - cw / 2, ctx.y_texte - chh / 2 + (1 - e) * H * 0.08, cw, chh)
    p.save()
    p.setOpacity(phase(sec, 0.05, 0.4))
    p.translate(r.center())
    p.scale(s, s)
    p.translate(-r.center())
    rayon = H * 0.03
    forme = QPainterPath()
    forme.addRoundedRect(r, rayon, rayon)
    # ombre douce
    for k in range(6):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 14))
        p.drawRoundedRect(r.adjusted(-k * 3, -k * 3 + H * 0.02, k * 3, k * 3 + H * 0.02), rayon + k * 3, rayon + k * 3)
    p.setClipPath(forme)
    if fond_img is not None:
        flou = flouter(fond_img.copy(r.toRect()), 14)
        p.drawImage(r, flou)
    p.fillRect(r, QColor(255, 255, 255, 38))
    p.setClipping(False)
    p.setPen(QPen(QColor(255, 255, 255, 90), max(1.0, H * 0.0015)))
    p.setBrush(Qt.NoBrush)
    p.drawPath(forme)
    p.setPen(Qt.NoPen)
    p.setBrush(ctx.c["texte"])
    te = expo(phase(sec, 0.35, 0.7))
    p.setOpacity(phase(sec, 0.35, 0.4))
    p.drawPath(ch.translated(L / 2, r.center().y() + (fm.capHeight() / 2 if not ctx.sous else -H * 0.012) + (1 - te) * H * 0.02))
    if ctx.sous:
        f2 = ajuster(ctx.sous, "Poppins", H * 0.034, 300, cw * 0.9, 0.12)
        ch2, _w2, _fm2 = chemin_texte(ctx.sous, f2, 0.12)
        p.setOpacity(phase(sec, 0.6, 0.4))
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawPath(ch2.translated(L / 2, r.center().y() + H * 0.07))
    p.restore()


def _espacement(p, ctx, sec):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    L, H = ctx.L, ctx.H
    e = doux(phase(sec, 0.0, 1.5))
    esp = 0.9 - 0.62 * e
    f = ajuster(ctx.texte.upper(), "Poppins", H * 0.085, 300, L * 0.9, esp)
    ch, w, fm = chemin_texte(ctx.texte.upper(), f, esp)
    flou = (1 - expo(phase(sec, 0.0, 1.2))) * 22
    img = QImage(L, int(H * 0.3), QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    q = QPainter(img)
    q.setRenderHint(QPainter.Antialiasing)
    q.setPen(Qt.NoPen)
    q.setBrush(ctx.c["texte"])
    q.drawPath(ch.translated(L / 2, img.height() / 2 + fm.capHeight() / 2))
    q.end()
    p.save()
    p.setOpacity(phase(sec, 0.0, 0.8))
    p.drawImage(0, int(ctx.y_texte - img.height() / 2), flouter(img, flou))
    p.restore()
    sous_titre(p, ctx, sec, 1.1, couleur=ctx.c["accent"], poids=400, espacement=0.35, taille=0.032)


def _cinema(p, ctx, sec):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QRadialGradient
    L, H = ctx.L, ctx.H
    bande = H * 0.12 * expo(phase(sec, 0.0, 0.8))
    f = ajuster(ctx.texte.upper(), "Poppins", H * 0.075, 300, L * 0.86, 0.45)
    ch, w, fm = chemin_texte(ctx.texte.upper(), f, 0.45)
    s = 1.0 + 0.05 * sec / max(1.0, ctx.duree)
    p.save()
    p.translate(L / 2, ctx.y_texte + fm.capHeight() / 2)
    p.scale(s, s)
    p.setOpacity(doux(phase(sec, 0.2, 1.0)))
    p.setPen(Qt.NoPen)
    p.setBrush(ctx.c["texte"])
    p.drawPath(ch)
    # balayage de lumière dans les lettres
    sw = phase(sec, 0.9, 1.1)
    if 0 < sw < 1:
        x = -w / 2 - w * 0.2 + (w * 1.4) * sw
        g = QLinearGradient(QPointF(x - w * 0.12, 0), QPointF(x + w * 0.12, 0))
        g.setColorAt(0, QColor(255, 255, 255, 0))
        g.setColorAt(0.5, QColor(255, 255, 255, 230))
        g.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(g))
        p.drawPath(ch)
        # reflet horizontal façon objectif anamorphique
        p.setCompositionMode(QPainter.CompositionMode_Screen)
        fl = QRadialGradient(QPointF(0, 0), w * 0.6)
        c = QColor(ctx.c["accent2"])
        c.setAlpha(int(140 * math.sin(sw * math.pi)))
        fl.setColorAt(0, c)
        fl.setColorAt(1, QColor(0, 0, 0, 0))
        p.save()
        p.translate(x, -fm.capHeight() / 2)
        p.scale(1, 0.035)
        p.setBrush(QBrush(fl))
        p.drawEllipse(QPointF(0, 0), w * 0.6, w * 0.6)
        p.restore()
    p.restore()
    sous_titre(p, ctx, sec, 1.2, couleur=ctx.c["accent"], poids=400, espacement=0.5, taille=0.028)
    p.fillRect(QRectF(0, 0, L, bande), QColor(0, 0, 0))
    p.fillRect(QRectF(0, H - bande, L, bande), QColor(0, 0, 0))


def _horizon(p, ctx, sec):
    from PySide6.QtCore import QRectF, Qt
    L, H = ctx.L, ctx.H
    y = ctx.y_texte
    e = expo(phase(sec, 0.0, 1.0))
    lw = L * 0.5 * e
    p.fillRect(QRectF(L / 2 - lw / 2, y - max(1.0, H * 0.0012), lw, max(2.0, H * 0.0024)), ctx.c["accent"])
    f = ajuster(ctx.texte.upper(), "Poppins", H * 0.085, 600, L * 0.8, 0.22)
    ch, w, fm = chemin_texte(ctx.texte.upper(), f, 0.22)
    t1 = expo(phase(sec, 0.45, 1.0))
    p.save()
    p.setClipRect(QRectF(0, 0, L, y - H * 0.006))
    p.setPen(Qt.NoPen)
    p.setBrush(ctx.c["texte"])
    p.drawPath(ch.translated(L / 2, y - H * 0.03 + (1 - t1) * fm.ascent() * 1.3))
    p.restore()
    if ctx.sous:
        f2 = ajuster(ctx.sous.upper(), "Poppins", H * 0.032, 300, L * 0.7, 0.5)
        ch2, _w2, fm2 = chemin_texte(ctx.sous.upper(), f2, 0.5)
        t2 = expo(phase(sec, 0.75, 1.0))
        p.save()
        p.setClipRect(QRectF(0, y + H * 0.006, L, H))
        p.setPen(Qt.NoPen)
        p.setBrush(ctx.c["accent"])
        p.drawPath(ch2.translated(L / 2, y + H * 0.06 - (1 - t2) * fm2.ascent() * 1.6))
        p.restore()


def _lumiere(p, ctx, sec):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QRadialGradient
    L, H = ctx.L, ctx.H
    p.setCompositionMode(QPainter.CompositionMode_Screen)
    for k, coul in enumerate(ctx.pal.get("taches") or []):
        x = L * (-0.3 + 1.6 * ((sec * 0.28 + k * 0.37) % 1.0))
        yy = H * (0.3 + 0.4 * math.sin(k * 2 + sec * 0.6))
        g = QRadialGradient(QPointF(x, yy), H * 0.8)
        c = QColor(coul)
        c.setAlpha(110)
        g.setColorAt(0, c)
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(g))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(x, yy), H * 0.8, H * 0.8)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    f = ajuster(ctx.texte, "Poppins", H * 0.11, 400, L * 0.84, 0.04)
    ch, w, fm = chemin_texte(ctx.texte, f, 0.04)
    img = QImage(L, int(H * 0.3), QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    q = QPainter(img)
    q.setRenderHint(QPainter.Antialiasing)
    q.setPen(Qt.NoPen)
    q.setBrush(ctx.c["texte"])
    q.drawPath(ch.translated(L / 2, img.height() / 2 + fm.capHeight() / 2))
    q.end()
    p.save()
    p.setOpacity(doux(phase(sec, 0.2, 1.0)))
    p.drawImage(0, int(ctx.y_texte - img.height() / 2), flouter(img, (1 - expo(phase(sec, 0.2, 1.3))) * 26))
    p.restore()
    sous_titre(p, ctx, sec, 1.1, couleur=ctx.c["accent2"], poids=300, espacement=0.3, taille=0.034)


DESSINS = {"slam": _slam, "decoupe": _decoupe, "contour": _contour, "glitch_net": _glitch_net, "masque": _masque,
           "espacement": _espacement, "cinema": _cinema, "horizon": _horizon, "lumiere": _lumiere}


def image(ctx, sec):
    """Une image de l'intro à l'instant sec (secondes)."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QImage, QPainter
    L, H = ctx.L, ctx.H
    img = QImage(L, H, QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    dessiner_fond(p, ctx, sec)
    p.end()
    fond_img = img.copy() if ctx.modele == "verre" else None
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    # sortie : l'ensemble grossit légèrement et s'efface (ou passe au noir) sur la dernière demi-seconde
    fin = phase(sec, ctx.duree - 0.45, 0.45)
    calque = QImage(L, H, QImage.Format_ARGB32_Premultiplied)
    calque.fill(0)
    q = QPainter(calque)
    q.setRenderHint(QPainter.Antialiasing)
    q.setRenderHint(QPainter.SmoothPixmapTransform)
    dessiner_logo(q, ctx, sec)
    secousse = 0.0
    if ctx.modele == "verre":
        _verre(q, ctx, sec, fond_img)
    else:
        secousse = DESSINS.get(ctx.modele, _masque)(q, ctx, sec) or 0.0
    q.end()
    p.save()
    s = 1.0 + 0.06 * doux(fin)
    p.translate(L / 2, H / 2)
    p.scale(s, s)
    p.translate(-L / 2, -H / 2)
    if secousse:
        r = random.Random(int(sec * 60))
        p.translate(r.uniform(-1, 1) * H * 0.012 * secousse, r.uniform(-1, 1) * H * 0.012 * secousse)
    p.setOpacity(1 - doux(fin))
    p.drawImage(0, 0, calque)
    p.restore()
    if fin > 0 and ctx.fond != "transparent":
        p.fillRect(QRectF(0, 0, L, H), QColor(0, 0, 0, int(200 * doux(fin))))
    p.end()
    return img


def contexte(modele, texte, sous_texte="", L=1920, H=1080, duree=3.0, fond="degrade", couleurs=None, image_film=None, logo=None):
    return Contexte(modele, texte, sous_texte, L, H, duree, fond, couleurs, image_film, logo)


def fabriquer(sortie, modele, texte, sous_texte="", L=1920, H=1080, cadence=30, duree=3.0, fond="degrade", couleurs=None,
              image_film=None, logo=None, progression=None):
    """Clip MP4 de l'intro (sans son), prêt à poser au début du montage."""
    import shutil
    from . import moteur
    ctx = contexte(modele, texte, sous_texte, L, H, duree, fond, couleurs, image_film, logo)
    d = tempfile.mkdtemp(prefix="philcut-intro-")
    n = max(2, int(duree * cadence))
    try:
        for i in range(n):
            image(ctx, i / cadence).save(os.path.join(d, f"{i:05d}.png"), "PNG", 20)
            progression and progression(0.85 * i / n)
        moteur.lancer(["-y", "-framerate", str(cadence), "-i", os.path.join(d, "%05d.png"), "-c:v", "libx264", "-preset", "veryfast",
                       "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", sortie])
    finally:
        shutil.rmtree(d, ignore_errors=True)
    progression and progression(1.0)
    return sortie
