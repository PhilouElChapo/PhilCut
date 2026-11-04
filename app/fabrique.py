"""La Fabrique : logos animes, intros et fins de video, plans generes par IA.

- Logos et intros : modeles animes faits maison (trace du contour, particules, code Matrix, eclat, lucioles,
  carnet), rendus par QPainter en images puis encodes en clip ; texte, couleurs et style au choix, ou proposes
  par l'assistant a partir du film.
- Plans IA : Flow avec l'abonnement (PhilCut prepare la consigne, ouvre Flow, surveille un dossier et ramene le
  clip) ; Veo par l'API Gemini (payant a la seconde, prix affiche, confirmation) ; d'autres generateurs peuvent
  s'ajouter (Kling...) sur le meme modele.
"""
import json, math, os, random, tempfile, time, urllib.request, webbrowser

from . import moteur
from .langue import _

MODELES_LOGO = {
    "trace": _("Tracé du contour"), "particules": _("Particules qui se rassemblent"), "code": _("Code Matrix qui forme le texte"),
    "eclat": _("Eclat de lumière"), "lucioles": _("Lucioles"), "carnet": _("Carnet qui s'ouvre"), "glitch": _("Glitch"), "rotation": _("Rotation 3D"),
}
STYLES = [_("sobre"), _("cinéma"), _("néon"), _("aviation"), _("chaleureux"), _("numérique"), _("festif"), _("enfantin")]


# ------------------------------------------------------------------ logos et intros
def rendre_logo(dossier, texte, modele="trace", L=1920, H=1080, cadence=30, duree=2.5, couleur="#ffffff", fond="#0b0b12",
                accent="#9b7bff", sous_texte="", image_logo=None, progression=None):
    """Images PNG de l'animation ; renvoie (motif, nb). image_logo : chemin d'un PNG/SVG a animer au lieu du texte."""
    from PySide6.QtCore import Qt, QRectF, QPointF
    from PySide6.QtGui import QImage, QPainter, QColor, QPen, QFont, QPainterPath, QBrush, QRadialGradient, QPixmap, QFontMetricsF
    n = max(2, int(duree * cadence))
    rng = random.Random(42)
    police = QFont("Nunito")
    police.setBold(True)
    police.setPixelSize(int(H * (0.16 if len(texte) < 12 else 0.11)))
    chemin = QPainterPath()
    fm = QFontMetricsF(police)
    larg = fm.horizontalAdvance(texte)
    chemin.addText((L - larg) / 2, H / 2 + fm.capHeight() / 2, police, texte)
    logo_px = QPixmap(image_logo) if image_logo and os.path.exists(image_logo) else None
    if logo_px is not None and not logo_px.isNull():
        logo_px = logo_px.scaledToHeight(int(H * 0.35), Qt.SmoothTransformation)
    # points le long du contour (pour particules, lucioles, code)
    pts = []
    for i in range(400):
        pts.append(chemin.pointAtPercent(i / 400))
    rempl = []
    br = chemin.boundingRect()
    for _k in range(900):
        p = QPointF(rng.uniform(br.left(), br.right()), rng.uniform(br.top(), br.bottom()))
        if chemin.contains(p):
            rempl.append(p)
    depart = [(QPointF(rng.uniform(0, L), rng.uniform(0, H))) for _ in range(len(rempl))]
    glyphes = "01ABCXZ<>#$%"
    for i in range(n):
        t = i / (n - 1)
        img = QImage(L, H, QImage.Format_ARGB32_Premultiplied)
        img.fill(QColor(fond))
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        e = _ease(min(1.0, t / 0.7))
        fin = max(0.0, (t - 0.85) / 0.15)          # fondu de sortie
        if modele == "trace":
            tr = QPen(QColor(accent), max(2, H // 240), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(tr)
            p.setBrush(Qt.NoBrush)
            partiel = QPainterPath()
            total = int(400 * e)
            for k in range(max(0, total)):
                pt = pts[k]
                if k == 0 or k % 40 == 0:
                    partiel.moveTo(pt)
                else:
                    partiel.lineTo(pt)
            p.drawPath(partiel)
            if t > 0.55:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(couleur))
                p.setOpacity(min(1.0, (t - 0.55) / 0.25))
                p.drawPath(chemin)
        elif modele in ("particules", "lucioles"):
            p.setPen(Qt.NoPen)
            for k, (a, b) in enumerate(zip(depart, rempl)):
                x = a.x() + (b.x() - a.x()) * e
                y = a.y() + (b.y() - a.y()) * e
                r = (2.5 if modele == "particules" else 4) * H / 1080
                if modele == "lucioles":
                    r *= 0.6 + 0.6 * abs(math.sin(i / 6 + k))
                    g = QRadialGradient(x, y, r * 4)
                    g.setColorAt(0, QColor(255, 230, 140, 220))
                    g.setColorAt(1, QColor(255, 200, 80, 0))
                    p.setBrush(QBrush(g))
                    p.drawEllipse(QPointF(x, y), r * 4, r * 4)
                p.setBrush(QColor(couleur if modele == "particules" else "#fff2c0"))
                p.drawEllipse(QPointF(x, y), r, r)
            if t > 0.75:
                p.setBrush(QColor(couleur))
                p.setOpacity(min(1.0, (t - 0.75) / 0.2))
                p.drawPath(chemin)
        elif modele == "code":
            f2 = QFont("Consolas" if os.name == "nt" else "DejaVu Sans Mono")
            f2.setPixelSize(int(H * 0.028))
            p.setFont(f2)
            pas = int(H * 0.03)
            for col in range(0, L, pas):
                tete = int((t * 2.2 * H + (col * 37) % H))
                for row in range(0, H, pas):
                    if row > tete:
                        continue
                    age = (tete - row) / pas
                    if age > 18:
                        continue
                    dans = chemin.contains(QPointF(col + pas / 2, row + pas / 2))
                    a = max(0.1, 1 - age / 18) * (1.0 if dans or t < 0.6 else max(0.0, 1 - (t - 0.6) / 0.25))
                    p.setPen(QColor(120, 255, 150, int(255 * a)) if age > 0.5 else QColor(230, 255, 230))
                    p.drawText(col, row + pas, glyphes[(col // pas + row // pas + i // 2) % len(glyphes)])
            if t > 0.65:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#c8ffd8"))
                p.setOpacity(min(1.0, (t - 0.65) / 0.25))
                p.drawPath(chemin)
        elif modele == "eclat":
            g = QRadialGradient(L / 2, H / 2, H * (0.1 + 1.2 * e))
            g.setColorAt(0, QColor(255, 255, 255, int(230 * (1 - e))))
            g.setColorAt(0.4, QColor(accent))
            g.setColorAt(1, QColor(fond))
            p.fillRect(0, 0, L, H, QBrush(g))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(couleur))
            p.setOpacity(min(1.0, e * 1.4))
            s = 0.6 + 0.4 * e
            p.translate(L / 2, H / 2)
            p.scale(s, s)
            p.translate(-L / 2, -H / 2)
            p.drawPath(chemin)
            p.resetTransform()
        elif modele == "carnet":
            # page de carnet qui pivote, texte manuscrit qui apparait lettre par lettre
            p.fillRect(0, 0, L, H, QColor("#3a2a1a"))
            ouverture = e
            pw, ph = L * 0.6, H * 0.72
            p.translate(L / 2, H / 2)
            p.save()
            p.scale(max(0.02, ouverture), 1)
            p.fillRect(QRectF(-pw / 2, -ph / 2, pw, ph), QColor("#f6efdf"))
            p.setPen(QPen(QColor(120, 160, 220, 120), 1))
            for y in range(int(-ph / 2 + 40), int(ph / 2), int(H * 0.055)):
                p.drawLine(QPointF(-pw / 2 + 30, y), QPointF(pw / 2 - 30, y))
            p.restore()
            if ouverture > 0.9:
                f3 = QFont("Nunito")
                f3.setItalic(True)
                f3.setPixelSize(int(H * 0.08))
                p.setFont(f3)
                p.setPen(QColor("#2a3f7a"))
                k = int(len(texte) * min(1.0, (t - 0.63) / 0.3))
                p.drawText(QRectF(-pw / 2 + 50, -ph / 2 + 40, pw - 100, ph - 80), Qt.AlignLeft | Qt.AlignTop, texte[:k])
            p.resetTransform()
        elif modele == "glitch":
            p.setPen(Qt.NoPen)
            for dx, c in ((-14 * (1 - e), QColor(255, 60, 60, 200)), (14 * (1 - e), QColor(60, 120, 255, 200)), (0, QColor(couleur))):
                p.save()
                p.translate(dx + (rng.uniform(-18, 18) if rng.random() < 0.2 * (1 - e) else 0), 0)
                p.setBrush(c)
                p.drawPath(chemin)
                p.restore()
            if rng.random() < 0.25 * (1 - e):
                y = rng.randint(0, H)
                p.fillRect(QRectF(0, y, L, rng.randint(3, 30)), QColor(255, 255, 255, 60))
        else:   # rotation
            p.translate(L / 2, H / 2)
            sx = math.cos((1 - e) * math.pi * 2)
            p.scale(max(0.05, abs(sx)), 1)
            p.translate(-L / 2, -H / 2)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(couleur) if sx > 0 else QColor(accent))
            p.drawPath(chemin)
            p.resetTransform()
        if logo_px is not None and not logo_px.isNull() and t > 0.3:
            p.setOpacity(min(1.0, (t - 0.3) / 0.3))
            p.drawPixmap(int(L / 2 - logo_px.width() / 2), int(H * 0.08), logo_px)
            p.setOpacity(1.0)
        if sous_texte and t > 0.7:
            f4 = QFont("Nunito")
            f4.setPixelSize(int(H * 0.045))
            p.setFont(f4)
            p.setPen(QColor(couleur))
            p.setOpacity(min(1.0, (t - 0.7) / 0.2))
            p.drawText(QRectF(0, H * 0.66, L, H * 0.1), Qt.AlignCenter, sous_texte)
            p.setOpacity(1.0)
        if fin > 0:
            p.fillRect(0, 0, L, H, QColor(0, 0, 0, int(255 * fin)))
        p.end()
        img.save(os.path.join(dossier, f"{i:05d}.png"))
        if progression:
            progression(i / n)
    return os.path.join(dossier, "%05d.png"), n


def fabriquer_logo(sortie, texte, modele="trace", L=1920, H=1080, cadence=30, duree=2.5, progression=None, **opts):
    """Clip MP4 du logo anime (sans son), pret a poser au debut du montage."""
    d = tempfile.mkdtemp(prefix="philcut-logo-")
    motif, n = rendre_logo(d, texte, modele, L, H, cadence, duree, progression=lambda f: progression and progression(f * 0.8), **opts)
    moteur.lancer(["-framerate", str(cadence), "-i", motif, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                   "-movflags", "+faststart", sortie])
    import shutil
    shutil.rmtree(d, ignore_errors=True)
    progression and progression(1.0)
    return sortie


def _ease(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


# ------------------------------------------------------------------ plans IA : Flow (abonnement) et Veo (API)
URL_FLOW = "https://labs.google/fx/fr/tools/flow"
# Google a arrêté Veo 3.1 le 22 octobre 2026 : la génération passe par Gemini Omni Flash (Interactions API, même clef).
# Prix relevés le 4 novembre 2026 (indicatifs) : environ 0,10 $/s en 720p, un tiers en 360p ; 1080p et 4K sont agrandis.
MODELE_VIDEO = "gemini-omni-1.1-flash"
MODELES_VEO = {           # choix : (nom, prix $/s indicatif, note)
    "gemini-omni-1.1-flash@360p": ("Omni Flash 360p (brouillon)", 0.035, _("pour essayer une idée")),
    "gemini-omni-1.1-flash@720p": ("Omni Flash 720p", 0.10, _("bon compromis")),
    "gemini-omni-1.1-flash@1080p": ("Omni Flash 1080p", 0.10, _("720p agrandi par Google, prix à vérifier")),
}


def consigne_plan(usage, sujet, style="", duree=8, format_="16:9", details=""):
    """Consigne prete a coller dans Flow (ou envoyee a Veo), en anglais car les generateurs y repondent mieux."""
    f = "vertical 9:16" if format_ == "9:16" else "widescreen 16:9"
    u = {"intro": "opening shot", "fin": "closing shot", "transition": "short transitional shot", "illustration": "illustrative shot"}.get(usage, "shot")
    s = f", {style} style" if style else ""
    return (f"Cinematic {u}, {f}, {int(duree)} seconds: {sujet}{s}. Smooth camera movement, natural light, high detail, "
            f"no text, no watermark, no logo.{(' ' + details) if details else ''}")


def preparer_flow(consigne, dossier_surveille):
    """Copie la consigne dans le presse-papiers, ouvre Flow, et renvoie la liste des fichiers deja presents dans le dossier."""
    try:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(consigne)
    except Exception:
        pass
    webbrowser.open(URL_FLOW)
    os.makedirs(dossier_surveille, exist_ok=True)
    return set(os.listdir(dossier_surveille))


def nouveaux_clips(dossier_surveille, avant):
    """Fichiers video arrives dans le dossier depuis preparer_flow()."""
    try:
        maintenant = set(os.listdir(dossier_surveille))
    except OSError:
        return []
    out = []
    for f in sorted(maintenant - avant):
        p = os.path.join(dossier_surveille, f)
        if f.lower().endswith((".mp4", ".mov", ".webm")) and not f.endswith(".crdownload") and os.path.getsize(p) > 0:
            out.append(p)
    return out


def prix_veo(modele, duree):
    """Prix estimé ; Omni Flash choisit lui-même la durée (3 à 10 s) : on compte le maximum entre la demande et 10 s."""
    d = 10 if "omni" in modele else duree
    return round(MODELES_VEO.get(modele, ("", 0.4, ""))[1] * max(duree, d), 2)


def _trouver_video(d):
    """Cherche dans la réponse de l'Interactions API un contenu vidéo : (données base64, uri)."""
    if isinstance(d, dict):
        if d.get("type") == "video" and (d.get("data") or d.get("uri")):
            return d.get("data"), d.get("uri")
        for v in d.values():
            r = _trouver_video(v)
            if r:
                return r
    elif isinstance(d, list):
        for v in d:
            r = _trouver_video(v)
            if r:
                return r
    return None


def generer_omni(clef, consigne, sortie, modele=MODELE_VIDEO, duree=8, format_="16:9", image=None, resolution="720p",
                 progression=None, arret=lambda: False):
    """Plan vidéo par Gemini Omni Flash (Interactions API) : demande en tâche de fond, interrogée jusqu'à la fin."""
    import base64
    base = "https://generativelanguage.googleapis.com/v1beta"
    entete = {"Content-Type": "application/json", "x-goog-api-key": clef}
    texte = consigne.strip() + f"\n\n(Durée souhaitée : environ {int(duree)} secondes.)"
    if image:
        with open(image, "rb") as f:
            img = {"type": "image", "mime_type": "image/png" if image.lower().endswith(".png") else "image/jpeg",
                   "data": base64.b64encode(f.read()).decode()}
        entree = [{"type": "text", "text": texte}, img]
    else:
        entree = texte
    corps = {"model": modele, "input": entree, "background": True,
             "response_format": {"type": "video", "aspect_ratio": "9:16" if format_ == "9:16" else "16:9", "resolution": resolution}}
    req = urllib.request.Request(f"{base}/interactions", data=json.dumps(corps).encode("utf-8"), headers=entete)
    with urllib.request.urlopen(req, timeout=180) as r:
        it = json.loads(r.read().decode("utf-8"))
    debut = time.time()
    while it.get("status") not in ("completed", "failed", "cancelled") and not _trouver_video(it):
        if arret():
            raise InterruptedError()
        if not it.get("id"):
            raise RuntimeError(_("Réponse inattendue de Google : {r}", r=str(it)[:200]))
        time.sleep(6)
        progression and progression(min(0.9, (time.time() - debut) / 240))
        req = urllib.request.Request(f"{base}/interactions/{it['id']}", headers=entete)
        with urllib.request.urlopen(req, timeout=60) as r:
            it = json.loads(r.read().decode("utf-8"))
        if time.time() - debut > 900:
            raise RuntimeError(_("La génération met trop de temps ; réessayez plus tard."))
    if it.get("status") in ("failed", "cancelled"):
        raise RuntimeError(_("Google a refusé ou interrompu la génération : {e}", e=str(it.get("error") or it.get("status"))[:300]))
    trouve = _trouver_video(it)
    if not trouve:
        raise RuntimeError(_("Google n'a renvoyé aucune vidéo (contenu refusé ?)."))
    data, uri = trouve
    if data:
        with open(sortie, "wb") as f:
            f.write(base64.b64decode(data))
    else:
        if uri.startswith("files/"):
            uri = f"{base}/{uri}:download?alt=media"
        req = urllib.request.Request(uri, headers={"x-goog-api-key": clef})
        with urllib.request.urlopen(req, timeout=300) as r, open(sortie, "wb") as f:
            f.write(r.read())
    progression and progression(1.0)
    return sortie


def generer_veo(params, consigne, sortie, modele="gemini-omni-1.1-flash@720p", duree=8, format_="16:9", image=None, progression=None, arret=lambda: False):
    """Generation par l'API Gemini (clef Gemini des Preferences). Longue (1 a 6 min) : on interroge l'operation jusqu'a la fin."""
    from . import ia
    clef = ia.nettoyer_clef(params.get("clef_gemini", ""))
    if not clef:
        raise RuntimeError(_("Clef Gemini absente (Préférences › IA)."))
    if not modele.startswith("veo"):         # Gemini Omni Flash (modèle@résolution)
        nom, _a, resolution = modele.partition("@")
        return generer_omni(clef, consigne, sortie, nom, duree, format_, image, resolution or "720p", progression, arret)
    base = "https://generativelanguage.googleapis.com/v1beta"
    inst = {"prompt": consigne}
    if image:
        import base64
        with open(image, "rb") as f:
            inst["image"] = {"bytesBase64Encoded": base64.b64encode(f.read()).decode(), "mimeType": "image/png" if image.lower().endswith(".png") else "image/jpeg"}
    corps = {"instances": [inst], "parameters": {"aspectRatio": "9:16" if format_ == "9:16" else "16:9", "durationSeconds": int(duree), "personGeneration": "allow_adult"}}
    req = urllib.request.Request(f"{base}/models/{modele}:predictLongRunning", data=json.dumps(corps).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": clef})
    with urllib.request.urlopen(req, timeout=120) as r:
        op = json.loads(r.read().decode("utf-8"))
    nom = op.get("name")
    if not nom:
        raise RuntimeError(_("Veo n'a pas accepté la demande : {r}", r=str(op)[:200]))
    debut = time.time()
    while True:
        if arret():
            raise InterruptedError()
        time.sleep(8)
        progression and progression(min(0.9, (time.time() - debut) / 300))
        req = urllib.request.Request(f"{base}/{nom}", headers={"x-goog-api-key": clef})
        with urllib.request.urlopen(req, timeout=60) as r:
            op = json.loads(r.read().decode("utf-8"))
        if op.get("done"):
            break
        if time.time() - debut > 900:
            raise RuntimeError(_("Veo met trop de temps ; réessayez plus tard."))
    if op.get("error"):
        raise RuntimeError(str(op["error"])[:300])
    videos = (((op.get("response") or {}).get("generateVideoResponse") or {}).get("generatedSamples")) or []
    if not videos:
        raise RuntimeError(_("Veo n'a renvoyé aucune vidéo (contenu refusé ?)."))
    uri = videos[0]["video"]["uri"]
    req = urllib.request.Request(uri, headers={"x-goog-api-key": clef})
    with urllib.request.urlopen(req, timeout=300) as r, open(sortie, "wb") as f:
        f.write(r.read())
    progression and progression(1.0)
    return sortie
