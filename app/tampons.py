"""Tampons vidéo : petites séquences toutes faites (2 à 4 s, avec leur son) qu'on glisse dans un montage pour ponctuer,
faire rire ou relancer : « Quelques heures plus tard… », rembobinage, télé qui s'éteint, bip de censure, tadaa…

Trois sources, toutes rangées dans la même bibliothèque :
- les tampons maison, fabriqués sur ce poste par PhilCut (dessin + son synthétisé, aucun droit à payer) ;
- vos propres clips (un extrait de vos rushes, une réaction filmée…), importés avec un nom et des mots-clefs ;
- des clips libres trouvés en ligne : Wikimedia Commons (sans clef), Pixabay et Pexels (clef gratuite de l'utilisateur,
  rangée dans le coffre du système). Auteur, licence et lien sont gardés et ajoutés à la description à la publication.

Les extraits de films ou d'émissions connus ne sont pas libres : PhilCut ne les propose pas.

La bibliothèque est rangée dans le dossier de synchronisation quand il y en a un (Drive, NAS) : elle suit l'utilisateur
sur ses autres postes ; sinon dans le dossier de données de PhilCut. Index : tampons.json."""
import json, math, os, re, shutil, tempfile, time, urllib.parse, urllib.request

from .langue import _

API_COMMONS = "https://commons.wikimedia.org/w/api.php"
API_PIXABAY = "https://pixabay.com/api/videos/"
API_PEXELS = "https://api.pexels.com/videos/search"
SOURCES = {"wikimedia": "Wikimedia Commons", "pixabay": "Pixabay", "pexels": "Pexels"}
CLEFS = {"pixabay": "pixabay_cle", "pexels": "pexels_cle"}         # identifiants dans le coffre du système
# extraits de films et de séries (protégés) : recherche ouverte dans le navigateur, téléchargement par l'utilisateur
EXTRAITS = {"clipcafe": ("clip.cafe", "https://clip.cafe/s/{q}/"), "yarn": ("Yarn", "https://yarn.co/yarn-find?text={q}"),
            "playphrase": ("PlayPhrase.me", "https://www.playphrase.me/#/search?q={q}&language=en")}
# répliques et sons de films (audio) : recherche limitée au site, ouverte dans le navigateur
SONS_FILMS = {"voicy": ("Voicy", "voicy.network"), "movie_sounds": ("Movie-sounds.org", "movie-sounds.org"),
              "moviesoundclips": ("MovieSoundClips", "moviesoundclips.net"), "wavsource": ("WavSource", "wavsource.com"),
              "samplefocus": ("Sample Focus", "samplefocus.com"), "quodb": ("QuoDB", "quodb.com")}
PAGES_CLEF = {"pixabay": "https://pixabay.com/api/docs/", "pexels": "https://www.pexels.com/api/new/"}


class ErreurTampon(Exception):
    pass


# ------------------------------------------------------------------ tampons maison
# id : (nom, description, mots-clefs, durée)
MAISON = {
    "plus_tard": (_("Quelques heures plus tard…"), _("Carton de documentaire : le temps a passé."), _("temps, transition, humour"), 3.0),
    "pendant_ce_temps": (_("Pendant ce temps…"), _("Carton pour passer à une autre scène."), _("transition, scène, humour"), 2.6),
    "rembobiner": (_("Rembobinage VHS"), _("Ecran bleu de magnétoscope, compteur qui recule : on revient en arrière."), _("retour, vintage, humour"), 2.2),
    "tv_eteinte": (_("Télé qui s'éteint"), _("Le vieux téléviseur s'éteint en un trait puis un point : fin d'une scène."), _("fin, vintage, coupure"), 1.6),
    "censure": (_("Bip de censure"), _("Bande noire, tampon « CENSURÉ » et long bip."), _("humour, censure, bip"), 1.6),
    "tadaa": (_("Roulement de tambour… tadaa !"), _("Projecteur, roulement de tambour puis révélation avec confettis."), _("révélation, fête, surprise"), 3.2),
    "bravo": (_("Bravo !"), _("Applaudissements et étoiles : une réussite."), _("réussite, applaudissements, fête"), 2.8),
    "rate": (_("Raté !"), _("Grande croix rouge et buzzer : un échec, une chute."), _("échec, humour, buzzer"), 1.6),
    "compte_film": (_("Amorce de film 3, 2, 1"), _("Compte à rebours de vieux film, grain et bips."), _("vintage, cinéma, début"), 3.0),
    "idee": (_("Idée !"), _("Une ampoule s'allume avec un ding."), _("idée, astuce, ding"), 2.0),
    "silence": (_("Silence gêné…"), _("Grillons et points de suspension : un blanc."), _("humour, silence, blanc"), 3.0),
    "fin": (_("Fin|tampon"), _("« FIN » à l'ancienne, l'iris se referme."), _("fin, cinéma, vintage"), 2.6),
}

# id : (source audio lavfi, filtres)
_SONS = {
    "plus_tard": ("anoisesrc=d={d}:c=pink:a=0.5", "highpass=f=200,lowpass=f=3000,afade=t=in:d=0.5,afade=t=out:st=0.6:d=1.2,volume=0.8"),
    "pendant_ce_temps": ("anoisesrc=d={d}:c=pink:a=0.5", "highpass=f=300,lowpass=f=4000,afade=t=in:d=0.3,afade=t=out:st=0.4:d=0.8,volume=0.8"),
    "rembobiner": ("aevalsrc='0.25*sin(2*PI*(300+700*t)*t)*(0.6+0.4*sin(2*PI*14*t))+0.15*(random(0)*2-1)':d={d}", "lowpass=f=3500,afade=t=out:st=1.8:d=0.4"),
    "tv_eteinte": ("aevalsrc='0.35*sin(2*PI*(3200*exp(-3*t))*t)*exp(-2.5*t)+0.1*(random(0)*2-1)*lt(t,0.15)':d={d}", ""),
    "censure": ("sine=f=1000:d={d}", "afade=t=in:d=0.02,afade=t=out:st=1.3:d=0.1,volume=0.5"),
    "tadaa": ("aevalsrc='0.45*(random(0)*2-1)*(0.55+0.45*sin(2*PI*26*t))*lt(t,1.6)*(0.4+0.6*t/1.6)+0.22*(sin(2*PI*523*t)+sin(2*PI*659*t)+"
              "sin(2*PI*784*t)+0.5*sin(2*PI*1046*t))*gte(t,1.6)*exp(-1.4*(t-1.6))':d={d}", "lowpass=f=7000"),
    "bravo": ("aevalsrc='(random(0)*2-1)*(0.35+0.25*abs(sin(2*PI*6.7*t))*abs(sin(2*PI*9.1*t+1)))':d={d}",
              "highpass=f=700,lowpass=f=6500,afade=t=in:d=0.2,afade=t=out:st=2.0:d=0.8"),
    "rate": ("aevalsrc='0.35*(2*mod(98*t,1)-1)*lt(t,1.0)+0.25*(2*mod(73*t,1)-1)*lt(t,1.0)':d={d}", "lowpass=f=1400,afade=t=out:st=0.85:d=0.2"),
    "compte_film": ("aevalsrc='0.45*sin(2*PI*1000*t)*lt(mod(t,1),0.1)+0.04*(random(0)*2-1)':d={d}", "highpass=f=200"),
    "idee": ("aevalsrc='0.5*(sin(2*PI*1320*t)+0.45*sin(2*PI*2640*t))*gte(t,0.3)*exp(-3*(t-0.3))':d={d}", ""),
    "silence": ("aevalsrc='0.18*sin(2*PI*4500*t)*gt(sin(2*PI*32*t),0)*lt(mod(t,0.85),0.22)':d={d}", "highpass=f=2500"),
    "fin": ("aevalsrc='0.3*sin(2*PI*196*t)*exp(-1.1*t)+0.22*sin(2*PI*147*t)*exp(-0.9*t)+0.15*sin(2*PI*294*t)*exp(-1.5*t)':d={d}", ""),
}


def _ease(u):
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 3


def _texte(p, rect, texte, f, couleur, align=None, largeur=None):
    """Texte centré, réduit jusqu'à tenir dans la largeur voulue."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontMetricsF, QColor
    largeur = largeur or rect.width() * 0.92
    while f.pixelSize() > 6 and QFontMetricsF(f).horizontalAdvance(texte) > largeur:
        f.setPixelSize(int(f.pixelSize() * 0.92))
    p.setFont(f)
    p.setPen(QColor(couleur))
    p.drawText(rect, align if align is not None else Qt.AlignCenter, texte)


def image_maison(ident, t, L, H):
    """Image (QImage L × H) du tampon maison à l'instant t."""
    import random
    from PySide6.QtCore import Qt, QRectF, QPointF
    from PySide6.QtGui import (QImage, QPainter, QColor, QPen, QRadialGradient, QLinearGradient, QBrush, QPainterPath,
                               QPolygonF)
    from .intros import police
    d = MAISON[ident][3]
    img = QImage(L, H, QImage.Format_RGB32)
    img.fill(QColor(0, 0, 0))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    U = min(L, H)
    cx, cy = L / 2, H / 2
    plein = QRectF(0, 0, L, H)
    rnd = random.Random(int(t * 30) + 7)

    def vignette(alpha=200):
        g = QRadialGradient(QPointF(cx, cy), max(L, H) * 0.75)
        g.setColorAt(0.55, QColor(0, 0, 0, 0))
        g.setColorAt(1, QColor(0, 0, 0, alpha))
        p.fillRect(plein, QBrush(g))

    if ident in ("plus_tard", "pendant_ce_temps"):
        fond = QLinearGradient(0, 0, 0, H)
        fond.setColorAt(0, QColor("#141a2b") if ident == "plus_tard" else QColor("#24142b"))
        fond.setColorAt(1, QColor("#05060a"))
        p.fillRect(plein, QBrush(fond))
        vignette()
        texte = MAISON[ident][0]
        n = max(1, int(len(texte) * _ease(t / (d * 0.55))))        # les lettres arrivent une à une
        f = police("Poppins", U * 0.09, 600)
        f.setItalic(True)
        p.setOpacity(min(1.0, (d - t) / 0.35))
        _texte(p, QRectF(0, cy - U * 0.12, L, U * 0.24), texte[:n], f, "#ffd54a" if ident == "plus_tard" else "#9fe3ff", largeur=L * 0.86)
        p.setPen(QPen(QColor(255, 255, 255, 90), U * 0.004))
        w = L * 0.3 * _ease(t / 0.8)
        p.drawLine(QPointF(cx - w, cy + U * 0.13), QPointF(cx + w, cy + U * 0.13))
    elif ident == "rembobiner":
        p.fillRect(plein, QColor("#1b33c4"))
        for k in range(0, H, max(2, H // 180)):                       # lignes de balayage
            p.fillRect(QRectF(0, k, L, max(1, H // 360)), QColor(0, 0, 0, 40))
        bande = (t * 1.7 % 1.0) * H
        p.fillRect(QRectF(0, bande, L, H * 0.06), QColor(255, 255, 255, 50))
        for _k in range(120):
            p.fillRect(QRectF(rnd.random() * L, rnd.random() * H, U * 0.01, U * 0.003), QColor(255, 255, 255, 90))
        f = police("DejaVu Sans Mono", U * 0.07, 700)
        _texte(p, QRectF(L * 0.06, H * 0.08, L * 0.6, U * 0.1), "◀◀ " + _("REMBOBINAGE"), f, "#ffffff", Qt.AlignLeft | Qt.AlignVCenter)
        s = max(0, int(3600 * 1.5 - t * 1800))
        _texte(p, QRectF(L * 0.5, H * 0.82, L * 0.44, U * 0.1), f"{s // 3600:01d}:{s // 60 % 60:02d}:{s % 60:02d}", police("DejaVu Sans Mono", U * 0.07, 700),
               "#ffffff", Qt.AlignRight | Qt.AlignVCenter)
    elif ident == "tv_eteinte":
        u = t / d
        if u < 0.12:
            p.fillRect(plein, QColor(235, 240, 255))
        elif u < 0.45:
            h = H * (1 - (u - 0.12) / 0.33) ** 2 + 2
            p.fillRect(QRectF(0, cy - h / 2, L, h), QColor(235, 240, 255))
        elif u < 0.75:
            w = L * (1 - (u - 0.45) / 0.3) ** 2 + U * 0.01
            g = QRadialGradient(QPointF(cx, cy), w / 2)
            g.setColorAt(0, QColor(255, 255, 255))
            g.setColorAt(1, QColor(150, 180, 255, 0))
            p.fillRect(QRectF(cx - w / 2, cy - U * 0.01, w, U * 0.02), QBrush(g))
        else:
            a = int(255 * max(0.0, 1 - (u - 0.75) / 0.25))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, a))
            p.drawEllipse(QPointF(cx, cy), U * 0.012, U * 0.012)
    elif ident == "censure":
        p.fillRect(plein, QColor("#101014"))
        for _k in range(400):                                          # neige
            c = rnd.randint(30, 90)
            p.fillRect(QRectF(rnd.random() * L, rnd.random() * H, U * 0.006, U * 0.006), QColor(c, c, c))
        p.fillRect(QRectF(0, cy - U * 0.11, L, U * 0.22), QColor(0, 0, 0))
        f = police("Anton", U * 0.16)
        _texte(p, QRectF(0, cy - U * 0.11, L, U * 0.22), _("BIIIP"), f, "#ffffff" if int(t * 8) % 2 else "#ffeb3b")
        e = _ease(t / 0.25)
        p.save()
        p.translate(cx + U * 0.32, cy - U * 0.26)
        p.rotate(-14)
        p.scale(2.2 - 1.2 * e, 2.2 - 1.2 * e)
        p.setOpacity(e)
        p.setPen(QPen(QColor("#e53935"), U * 0.012))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(-U * 0.24, -U * 0.07, U * 0.48, U * 0.14), U * 0.02, U * 0.02)
        _texte(p, QRectF(-U * 0.24, -U * 0.07, U * 0.48, U * 0.14), _("CENSURÉ"), police("Anton", U * 0.09), "#e53935")
        p.restore()
    elif ident == "tadaa":
        p.fillRect(plein, QColor("#0b0612"))
        ouvert = _ease((t - 1.6) / 0.25)
        balaye = math.sin(t * 2.4) * L * 0.25 * (1 - ouvert)
        g = QRadialGradient(QPointF(cx + balaye, cy + U * 0.05), U * (0.25 + 0.35 * ouvert))
        g.setColorAt(0, QColor(255, 240, 200, 230))
        g.setColorAt(1, QColor(255, 240, 200, 0))
        p.fillRect(plein, QBrush(g))
        p.fillRect(QRectF(0, H * 0.82, L, H * 0.18), QColor(60, 10, 30))
        if t >= 1.6:
            e = (t - 1.6)
            s = 0.4 + 0.6 * _ease(e / 0.18) + 0.08 * math.sin(e * 18) * math.exp(-e * 4)
            p.save()
            p.translate(cx, cy)
            p.scale(s, s)
            _texte(p, QRectF(-L / 2, -U * 0.14, L, U * 0.28), _("TADAAA !"), police("Anton", U * 0.2), "#ffd54a", largeur=L * 0.8)
            p.restore()
            r2 = random.Random(3)
            couleurs = ["#ff5c8a", "#ffd24a", "#5ad1ff", "#7cff8a", "#c78bff"]
            for k in range(90):
                ang, vit = r2.random() * 6.28, (0.4 + r2.random()) * U
                x = cx + math.cos(ang) * vit * e
                y = cy + math.sin(ang) * vit * e + 0.6 * U * e * e
                p.save()
                p.translate(x, y)
                p.rotate(k * 37 + e * 400)
                p.fillRect(QRectF(-U * 0.008, -U * 0.004, U * 0.016, U * 0.008), QColor(couleurs[k % 5]))
                p.restore()
        else:
            _texte(p, QRectF(0, H * 0.84, L, H * 0.12), "· · ·", police("Poppins", U * 0.06, 700), "#ffffff")
    elif ident == "bravo":
        fond = QRadialGradient(QPointF(cx, cy), max(L, H) * 0.7)
        fond.setColorAt(0, QColor("#ff9a3c"))
        fond.setColorAt(1, QColor("#7a1fa2"))
        p.fillRect(plein, QBrush(fond))
        r2 = random.Random(5)
        for k in range(26):                                            # étoiles qui jaillissent
            ang, dist = r2.random() * 6.28, U * (0.2 + 0.45 * r2.random())
            u = _ease((t - k * 0.04) / 0.9)
            x, y = cx + math.cos(ang) * dist * u, cy + math.sin(ang) * dist * u
            r = U * 0.025 * (1 - 0.5 * u)
            poly = QPolygonF([QPointF(x + math.cos(a * math.pi / 5 - math.pi / 2) * (r if a % 2 == 0 else r * 0.45),
                                      y + math.sin(a * math.pi / 5 - math.pi / 2) * (r if a % 2 == 0 else r * 0.45)) for a in range(10)])
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, int(255 * (1 - u * 0.6))))
            p.drawPolygon(poly)
        s = 0.5 + 0.5 * _ease(t / 0.35) + 0.04 * math.sin(t * 7)
        p.save()
        p.translate(cx, cy)
        p.scale(s, s)
        _texte(p, QRectF(-L / 2, -U * 0.14, L, U * 0.28), _("BRAVO !"), police("Anton", U * 0.2), "#ffffff", largeur=L * 0.8)
        p.restore()
    elif ident == "rate":
        p.fillRect(plein, QColor("#2a0606"))
        vignette(230)
        dx = math.sin(t * 60) * U * 0.012 * max(0.0, 1 - t / 0.6)
        p.translate(dx, 0)
        p.setPen(QPen(QColor("#ff1744"), U * 0.07, Qt.SolidLine, Qt.RoundCap))
        r = U * 0.22
        u1, u2 = _ease(t / 0.18), _ease((t - 0.15) / 0.18)
        p.drawLine(QPointF(cx - r, cy - r - U * 0.06), QPointF(cx - r + 2 * r * u1, cy - r - U * 0.06 + 2 * r * u1))
        if t > 0.15:
            p.drawLine(QPointF(cx + r, cy - r - U * 0.06), QPointF(cx + r - 2 * r * u2, cy - r - U * 0.06 + 2 * r * u2))
        if t > 0.35:
            _texte(p, QRectF(0, cy + r * 0.85, L, U * 0.18), _("RATÉ !"), police("Anton", U * 0.13), "#ffffff")
    elif ident == "compte_film":
        p.fillRect(plein, QColor("#c9b48a"))
        n = max(1, 3 - int(t))
        frac = t % 1.0
        r = U * 0.36
        p.setPen(QPen(QColor(40, 30, 20), U * 0.006))
        p.drawLine(QPointF(0, cy), QPointF(L, cy))
        p.drawLine(QPointF(cx, 0), QPointF(cx, H))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.drawEllipse(QPointF(cx, cy), r * 0.82, r * 0.82)
        path = QPainterPath(QPointF(cx, cy))
        path.arcTo(QRectF(cx - r * 1.5, cy - r * 1.5, r * 3, r * 3), 90, -360 * frac)
        path.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(60, 45, 30, 110))
        p.drawPath(path)
        _texte(p, QRectF(0, cy - r * 0.7, L, r * 1.4), str(n), police("DejaVu Serif", r * 1.1, 700), "#1e160d")
        for _k in range(160):                                          # grain et rayures
            c = rnd.randint(20, 80)
            p.fillRect(QRectF(rnd.random() * L, rnd.random() * H, U * 0.004, U * 0.004), QColor(c, c, c, 160))
        for _k in range(2):
            x = rnd.random() * L
            p.fillRect(QRectF(x, 0, U * 0.002, H), QColor(30, 20, 10, 120))
        vignette(170)
    elif ident == "idee":
        p.fillRect(plein, QColor("#0d1220"))
        allume = _ease((t - 0.3) / 0.2)
        bx, by, br = cx, cy - U * 0.08, U * 0.15
        if allume > 0:
            g = QRadialGradient(QPointF(bx, by), U * 0.5)
            g.setColorAt(0, QColor(255, 230, 120, int(200 * allume * (0.8 + 0.2 * math.sin(t * 9)))))
            g.setColorAt(1, QColor(255, 230, 120, 0))
            p.fillRect(plein, QBrush(g))
            p.setPen(QPen(QColor(255, 220, 90, int(255 * allume)), U * 0.012, Qt.SolidLine, Qt.RoundCap))
            for k in range(8):
                a = math.radians(-180 + k * (180 / 7))
                p.drawLine(QPointF(bx + math.cos(a) * br * 1.35, by + math.sin(a) * br * 1.35),
                           QPointF(bx + math.cos(a) * br * 1.7, by + math.sin(a) * br * 1.7))
        p.setPen(QPen(QColor(230, 230, 235), U * 0.008))
        p.setBrush(QColor(255, 225, 100) if allume > 0.5 else QColor(60, 66, 80))
        p.drawEllipse(QPointF(bx, by), br, br)
        p.setBrush(QColor(170, 175, 185))
        p.drawRoundedRect(QRectF(bx - br * 0.45, by + br * 0.85, br * 0.9, br * 0.55), br * 0.1, br * 0.1)
        if t > 0.45:
            s = 1 + 0.06 * math.sin((t - 0.45) * 10) * math.exp(-(t - 0.45) * 2)
            p.save()
            p.translate(cx, cy + U * 0.28)
            p.scale(s, s)
            _texte(p, QRectF(-L / 2, -U * 0.08, L, U * 0.16), _("IDÉE !"), police("Anton", U * 0.12), "#ffd54a")
            p.restore()
    elif ident == "silence":
        fond = QLinearGradient(0, 0, 0, H)
        fond.setColorAt(0, QColor("#1c2633"))
        fond.setColorAt(1, QColor("#0a0e14"))
        p.fillRect(plein, QBrush(fond))
        r2 = random.Random(11)
        for k in range(60):
            a = 0.3 + 0.7 * abs(math.sin(t * 1.5 + k))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, int(120 * a)))
            p.drawEllipse(QPointF(r2.random() * L, r2.random() * H * 0.7), U * 0.003, U * 0.003)
        n = 1 + int(t * 2.2) % 3
        _texte(p, QRectF(0, cy - U * 0.15, L, U * 0.14), "." * n, police("Poppins", U * 0.12, 700), "#c9d4e3")
        p.setOpacity(_ease((t - 0.6) / 0.6))
        f = police("Poppins", U * 0.065, 500)
        f.setItalic(True)
        _texte(p, QRectF(0, cy + U * 0.02, L, U * 0.12), _("silence gêné"), f, "#8fa1b8")
    elif ident == "fin":
        p.fillRect(plein, QColor("#16120c"))
        for _k in range(200):
            c = rnd.randint(50, 110)
            p.fillRect(QRectF(rnd.random() * L, rnd.random() * H, U * 0.004, U * 0.004), QColor(c, c, c, 120))
        p.setOpacity(_ease(t / 0.6))
        _texte(p, QRectF(0, cy - U * 0.15, L, U * 0.3), _("FIN"), police("DejaVu Serif", U * 0.22, 700), "#f2e6c9")
        p.setOpacity(1.0)
        iris = max(0.0, 1 - _ease((t - (d - 1.0)) / 0.9))             # l'iris se referme
        if iris < 1:
            trou = QPainterPath()
            trou.addRect(plein)
            cercle = QPainterPath()
            cercle.addEllipse(QPointF(cx, cy), max(L, H) * 0.75 * iris, max(L, H) * 0.75 * iris)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0))
            p.drawPath(trou.subtracted(cercle))
        vignette(200)
    p.end()
    return img


def fabriquer_maison(params, ident, L=1920, H=1080, cadence=30, progression=None):
    """Fabrique le tampon maison (MP4 avec son) dans la bibliothèque ; renvoie son entrée."""
    from . import moteur, langue
    nom, desc, mots, d = MAISON[ident]
    dossier = dossier_tampons(params)
    sortie = os.path.join(dossier, f"maison_{ident}_{langue.LANGUE or 'fr'}_{L}x{H}.mp4")
    if not (os.path.exists(sortie) and os.path.getsize(sortie) > 2000):
        tmp = tempfile.mkdtemp(prefix="philcut-tampon-")
        try:
            n = max(2, int(d * cadence))
            for i in range(n):
                image_maison(ident, i / cadence, L, H).save(os.path.join(tmp, f"{i:05d}.jpg"), "JPG", 92)
                progression and progression(0.85 * i / n)
            src, filtres = _SONS[ident]
            args = ["-framerate", str(cadence), "-i", os.path.join(tmp, "%05d.jpg"), "-f", "lavfi", "-i", src.format(d=d)]
            if filtres:
                args += ["-af", filtres]
            moteur.lancer(args + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                                  "-ac", "2", "-ar", "48000", "-shortest", "-movflags", "+faststart", sortie + ".part.mp4"])
            os.replace(sortie + ".part.mp4", sortie)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    progression and progression(1.0)
    liste = charger(params)
    for e in liste:
        if e.get("fichier") == os.path.basename(sortie):
            return e
    e = _entree(sortie, nom, [m.strip() for m in mots.split(",") if m.strip()], "maison", d, maison=ident)
    liste.append(e)
    enregistrer(params, liste)
    return e


# ------------------------------------------------------------------ bibliothèque
def dossier_tampons(params):
    """Dossier de la bibliothèque : sur le lieu de synchronisation s'il existe (suit l'utilisateur), sinon local."""
    d = None
    try:
        from .bibliotheque import dossier_philcut_drive
        racine = dossier_philcut_drive(params)
        if racine:
            d = os.path.join(racine, "tampons")
    except Exception:    # noqa: BLE001
        d = None
    if not d:
        from .config import dossier_donnees
        d = os.path.join(dossier_donnees(), "tampons")
    os.makedirs(d, exist_ok=True)
    return d


def _index(params):
    return os.path.join(dossier_tampons(params), "tampons.json")


def charger(params):
    """Entrées de la bibliothèque dont le fichier est présent."""
    try:
        with open(_index(params), encoding="utf-8") as f:
            liste = json.load(f).get("tampons", [])
    except (OSError, ValueError, AttributeError):
        liste = []
    d = dossier_tampons(params)
    return [e for e in liste if isinstance(e, dict) and os.path.exists(os.path.join(d, e.get("fichier", "")))]


def enregistrer(params, liste):
    f = _index(params)
    with open(f + ".part", "w", encoding="utf-8") as g:
        json.dump({"philcut": 1, "tampons": liste}, g, ensure_ascii=False, indent=1)
    os.replace(f + ".part", f)


def chemin(params, e):
    return os.path.join(dossier_tampons(params), e["fichier"])


def _entree(fichier, nom, mots, source, duree, auteur="", licence="", page="", maison=None):
    e = {"id": f"t{int(time.time() * 1000) % 10 ** 11}{abs(hash(fichier)) % 1000}", "fichier": os.path.basename(fichier), "nom": nom,
         "mots": mots, "source": source, "duree": round(float(duree or 0), 2), "auteur": auteur, "licence": licence, "page": page,
         "ajoute": time.strftime("%Y-%m-%d")}
    if maison:
        e["maison"] = maison
    return e


def _nom_fichier(nom, ext):
    base = re.sub(r"[^\w\- ]+", "_", nom).strip()[:70] or "tampon"
    return f"{base}{ext}"


def ajouter_fichier(params, source, nom="", mots=(), debut=0.0, duree=None):
    """Range une copie de votre clip (ou d'un extrait : debut, duree) dans la bibliothèque ; renvoie l'entrée."""
    from . import moteur
    d = dossier_tampons(params)
    nom = nom or os.path.splitext(os.path.basename(source))[0]
    son = moteur.sonder(source).get("genre") == "audio"             # réplique ou bruit sans image : tampon sonore
    ext = (".m4a" if son else ".mp4") if (debut or duree) else (os.path.splitext(source)[1].lower() or ".mp4")
    cible = os.path.join(d, _nom_fichier(nom, ext))
    k = 2
    while os.path.exists(cible):
        cible = os.path.join(d, _nom_fichier(f"{nom} {k}", ext))
        k += 1
    if debut or duree:
        args = ["-ss", f"{float(debut):.3f}", "-i", source] + (["-t", f"{float(duree):.3f}"] if duree else [])
        video = [] if son else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
        moteur.lancer(args + video + ["-c:a", "aac", "-b:a", "160k", cible])
    else:
        shutil.copy2(source, cible)
    info = moteur.sonder(cible)
    e = _entree(cible, nom, list(mots), "perso", info.get("duree") or duree or 0)
    if info.get("genre") == "audio":
        e["genre"] = "son"
    liste = charger(params)
    liste.append(e)
    enregistrer(params, liste)
    return e


def modifier(params, ident, **champs):
    liste = charger(params)
    for e in liste:
        if e["id"] == ident:
            e.update({k: v for k, v in champs.items() if k in ("nom", "mots")})
    enregistrer(params, liste)


def retirer(params, ident):
    liste = charger(params)
    for e in [x for x in liste if x["id"] == ident]:
        for f in (chemin(params, e), os.path.splitext(chemin(params, e))[0] + ".credit.txt", vignette_chemin(params, e)):
            try:
                os.remove(f)
            except OSError:
                pass
    enregistrer(params, [x for x in liste if x["id"] != ident])


def vignette_chemin(params, e):
    return os.path.join(dossier_tampons(params), ".vignettes", os.path.splitext(e["fichier"])[0] + ".jpg")


def vignette(params, e):
    """Image JPEG du milieu du tampon (fabriquée une fois)."""
    from . import moteur
    v = vignette_chemin(params, e)
    if not os.path.exists(v):
        os.makedirs(os.path.dirname(v), exist_ok=True)
        try:
            t = max(0.0, float(e.get("duree") or 1) * 0.55)
            moteur.lancer(["-ss", f"{t:.2f}", "-i", chemin(params, e), "-frames:v", "1", "-vf", "scale=320:-2", v])
        except Exception:    # noqa: BLE001
            return None
    return v if os.path.exists(v) else None


def chercher_local(liste, texte):
    """Filtre la bibliothèque par nom et mots-clefs (sans accents ni majuscules)."""
    import unicodedata

    def plat(s):
        return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
    mots = plat(texte).split()
    return [e for e in liste if all(m in plat(e.get("nom", "") + " " + " ".join(e.get("mots") or [])) for m in mots)]


# ------------------------------------------------------------------ recherche en ligne
def _agent():
    from .config import VERSION
    return {"User-Agent": f"PhilCut/{VERSION} (+https://github.com/PhilouElChapo/PhilCut)"}


def _json(url, entetes=None, timeout=20):
    req = urllib.request.Request(url, headers={**_agent(), **(entetes or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ErreurTampon(_("Clef refusée par le site (HTTP {c}) : vérifiez-la.", c=e.code)) from e
        if e.code == 429:
            raise ErreurTampon(_("Trop de recherches d'un coup : réessayez dans une minute.")) from e
        raise ErreurTampon(_("Site injoignable (HTTP {c}).", c=e.code)) from e
    except ErreurTampon:
        raise
    except Exception as e:    # noqa: BLE001
        raise ErreurTampon(_("Site injoignable : {e}", e=e)) from e


def _sans_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def chercher_wikimedia(texte, n=24):
    """Vidéos libres de Wikimedia Commons : [{"titre", "auteur", "licence", "page", "url", "vignette", "duree", "source"}]."""
    q = f"filetype:video {texte}".strip()
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": q, "gsrnamespace": 6, "gsrlimit": n,
              "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 320, "origin": "*"}
    d = _json(API_COMMONS + "?" + urllib.parse.urlencode(params))
    out = []
    for pg in sorted((d.get("query") or {}).get("pages", {}).values(), key=lambda x: x.get("index", 0)):
        ii = (pg.get("imageinfo") or [{}])[0]
        if not str(ii.get("mime", "")).startswith("video/") or not ii.get("url"):
            continue
        meta = ii.get("extmetadata") or {}
        lic = _sans_html((meta.get("LicenseShortName") or {}).get("value", ""))
        if not lic or "NC" in lic.upper() or "ND" in lic.upper().replace("AND", ""):
            continue
        duree = 0.0
        try:
            duree = float(ii.get("duration") or 0)
        except (TypeError, ValueError):
            pass
        out.append({"titre": re.sub(r"^File:|\.\w+$", "", pg.get("title", "")).strip(), "auteur": _sans_html((meta.get("Artist") or {}).get("value", "")) or "?",
                    "licence": lic, "page": ii.get("descriptionurl") or "", "url": ii["url"], "vignette": ii.get("thumburl") or "",
                    "duree": duree, "source": "wikimedia", "taille": ii.get("size") or 0})
    return out


def chercher_pixabay(texte, cle, n=24):
    params = {"key": cle, "q": texte[:100], "per_page": max(3, min(n, 200)), "safesearch": "true"}
    d = _json(API_PIXABAY + "?" + urllib.parse.urlencode(params))
    out = []
    for h in d.get("hits") or []:
        v = h.get("videos") or {}
        choix = v.get("medium") or v.get("small") or v.get("large") or {}
        if not choix.get("url"):
            continue
        out.append({"titre": (h.get("tags") or "Pixabay").split(",")[0].strip().capitalize(), "auteur": h.get("user") or "?",
                    "licence": _("Licence Pixabay (libre, sans attribution obligatoire)"), "page": h.get("pageURL") or "", "url": choix["url"],
                    "vignette": choix.get("thumbnail") or "", "duree": float(h.get("duration") or 0), "source": "pixabay",
                    "mots": [m.strip() for m in (h.get("tags") or "").split(",") if m.strip()][:6]})
    return out


def chercher_pexels(texte, cle, n=24):
    params = {"query": texte[:100], "per_page": max(1, min(n, 80))}
    d = _json(API_PEXELS + "?" + urllib.parse.urlencode(params), {"Authorization": cle})
    out = []
    for v in d.get("videos") or []:
        fichiers = sorted([f for f in v.get("video_files") or [] if f.get("link") and (f.get("width") or 0) <= 1920],
                          key=lambda f: -(f.get("width") or 0))
        if not fichiers:
            continue
        page = v.get("url") or ""
        titre = re.sub(r"[-/]+", " ", page.rstrip("/").split("/")[-1]).strip()
        titre = re.sub(r"\s\d+$", "", titre).capitalize() or "Pexels"
        out.append({"titre": titre, "auteur": (v.get("user") or {}).get("name") or "?", "licence": _("Licence Pexels (libre, sans attribution obligatoire)"),
                    "page": page, "url": fichiers[0]["link"], "vignette": v.get("image") or "", "duree": float(v.get("duration") or 0),
                    "source": "pexels"})
    return out


def chercher(source, texte, params=None):
    if source == "wikimedia":
        return chercher_wikimedia(texte)
    from . import coffre
    cle = coffre.lire(CLEFS[source]) or ""
    if not cle:
        raise ErreurTampon(_("Clef {s} absente : « Ma clef {s}… » pour l'entrer (gratuite).", s=SOURCES[source]))
    return chercher_pixabay(texte, cle) if source == "pixabay" else chercher_pexels(texte, cle)


def telecharger(params, r, progression=None, arret=lambda: False, duree_max=None):
    """Télécharge un résultat en ligne dans la bibliothèque (crédit à côté) ; renvoie l'entrée."""
    from . import moteur
    d = dossier_tampons(params)
    ext = os.path.splitext(urllib.parse.urlparse(r["url"]).path)[1].lower() or ".mp4"
    brut = os.path.join(d, _nom_fichier(f"{r['titre']} ({SOURCES.get(r['source'], r['source'])})", ext))
    req = urllib.request.Request(r["url"], headers=_agent())
    with urllib.request.urlopen(req, timeout=120) as rep, open(brut + ".part", "wb") as f:
        total = int(rep.headers.get("Content-Length") or 0)
        fait = 0
        while True:
            if arret():
                raise ErreurTampon(_("Téléchargement arrêté."))
            bloc = rep.read(1 << 16)
            if not bloc:
                break
            f.write(bloc)
            fait += len(bloc)
            if progression and total:
                progression(0.9 * fait / total)
    os.replace(brut + ".part", brut)
    fichier = brut
    if ext not in (".mp4", ".mov", ".m4v"):                           # webm / ogv de Commons : converti pour tous les postes
        fichier = os.path.splitext(brut)[0] + ".mp4"
        try:
            moteur.lancer(["-i", brut, "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                           "-movflags", "+faststart", fichier])
            os.remove(brut)
        except Exception:    # noqa: BLE001
            fichier = brut
    with open(os.path.splitext(fichier)[0] + ".credit.txt", "w", encoding="utf-8") as f:
        f.write(credit(r) + "\n")
    info = moteur.sonder(fichier)
    e = _entree(fichier, r["titre"], list(r.get("mots") or []), r["source"], info.get("duree") or r.get("duree") or 0,
                r.get("auteur", ""), r.get("licence", ""), r.get("page", ""))
    liste = charger(params)
    liste.append(e)
    enregistrer(params, liste)
    progression and progression(1.0)
    return e


def url_extrait(site, texte):
    """Page de recherche du site d'extraits pour ces mots (déjà en anglais)."""
    if site in SONS_FILMS:                  # recherche web limitée au site : marche même si le site change ses adresses
        return "https://duckduckgo.com/?q=" + urllib.parse.quote_plus(f"site:{SONS_FILMS[site][1]} {texte.strip()}")
    q = urllib.parse.quote_plus(texte.strip()) if site == "clipcafe" else urllib.parse.quote(texte.strip())
    return EXTRAITS[site][1].format(q=q)


def credit(r):
    lien = f" — {r['page']}" if r.get("page") else ""
    return _("Vidéo : « {t} », {a} ({l}, {s}){p}", t=r.get("titre", ""), a=r.get("auteur", "?"), l=r.get("licence", ""),
             s=SOURCES.get(r.get("source"), r.get("source", "")), p=lien)


def maison_manquants(params, L, H):
    """Tampons maison pas encore fabriqués pour ce format et cette langue."""
    from . import langue
    d = dossier_tampons(params)
    return [k for k in MAISON if not os.path.exists(os.path.join(d, f"maison_{k}_{langue.LANGUE or 'fr'}_{L}x{H}.mp4"))]
