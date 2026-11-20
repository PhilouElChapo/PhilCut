"""1.0.5 : remplacer un élément d'une image par un élément de ma bibliothèque (Philippe, 20/11 22h31 : « garder le lieu, la photo
des filles ; l'avion enlevé et le Falcon mis à la place »).

Gemini reçoit, dans cet ordre : l'image d'origine, la même avec la zone à remplacer entourée de rouge, puis la fiche (et une
image) de l'élément de la bibliothèque. Il rend l'image modifiée ; PhilCut la remet aux dimensions de l'origine.
"""
import os
import time

from .langue import _

PRIX = 0.04          # une image Gemini (prix indicatif, noté dans « dépensé ce mois »)
GENRES = ("objet", "personnage", "musicien", "lieu", "image")

CONSIGNE = (
    "Edit the FIRST image. The SECOND image is the same picture with the area to change outlined in red. In that area, "
    "remove {quoi} and put in its place: {nom}. {description} It must look exactly like the reference image(s) that follow "
    "(same shape, proportions, colours, markings), seen from the angle, distance and perspective of the scene, at a believable "
    "scale, with the light, shadows and colours of the FIRST image. Nothing of what was removed may remain. Keep everything else "
    "strictly identical: the people (faces, expressions, hair, clothes), their position, the background, the framing and the "
    "image size. Photorealistic, no text, no added logo. Do not draw the red outline.")


def entrees(params):
    """Ce qu'on peut mettre à la place : les éléments de la bibliothèque qui ont une image (alphabétique)."""
    from . import bibliotheque_creations as B
    return [e for e in B.lister(params, GENRES) if B.apercu(e)]


def references(entree):
    """La fiche d'abord (planche), puis une autre image de l'élément ; deux au plus."""
    from . import bibliotheque_creations as B
    f = entree.get("fichiers") or {}
    refs = [B.apercu(entree)]
    refs += [p for r, p in sorted(f.items()) if p not in refs and p.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
             and os.path.exists(p)]
    return [p for p in refs if p and os.path.exists(p)][:2]


def image_zone(chemin, zone, sortie):
    """La même image avec la zone (fractions x0, y0, x1, y1) entourée de rouge."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QImage, QPainter, QPen
    im = QImage(chemin).convertToFormat(QImage.Format_RGB32)
    if im.isNull():
        raise ValueError(_("Image illisible : {f}", f=chemin))
    p = QPainter(im)
    ep = max(4, int(min(im.width(), im.height()) * 0.008))
    p.setPen(QPen(QColor(255, 0, 0), ep))
    x0, y0, x1, y1 = zone
    p.drawRect(QRectF(x0 * im.width(), y0 * im.height(), (x1 - x0) * im.width(), (y1 - y0) * im.height()))
    p.end()
    im.save(sortie, "PNG")
    return sortie


def aux_dimensions(octets, largeur, hauteur, sortie):
    """L'image rendue, remise exactement aux dimensions de l'origine (recadrée au centre si le format diffère)."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage
    im = QImage.fromData(octets)
    if im.isNull():
        raise ValueError(_("Gemini a rendu une image illisible."))
    if (im.width(), im.height()) != (largeur, hauteur):
        im = im.scaled(largeur, hauteur, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        im = im.copy((im.width() - largeur) // 2, (im.height() - hauteur) // 2, largeur, hauteur)
    im.save(sortie, "PNG")
    return sortie


def consigne(quoi, entree):
    d = (entree.get("description") or "").strip()
    return CONSIGNE.format(quoi=f"« {quoi.strip()} »" if quoi.strip() else "the object outlined in red",
                           nom=f"« {entree.get('nom', '')} »", description=(f"Description: {d}." if d else ""))


def remplacer(params, chemin, zone, quoi, entree, progression=None):
    """Fait le remplacement ; renvoie le chemin de la nouvelle image (dossier des créations IA)."""
    from PySide6.QtGui import QImage
    from . import creations, ia
    im = QImage(chemin)
    if im.isNull():
        raise ValueError(_("Image illisible : {f}", f=chemin))
    d = creations.dossier()
    base = os.path.splitext(os.path.basename(chemin))[0][:40]
    marque = time.strftime("%Y%m%d-%H%M%S")
    zones = image_zone(chemin, zone, os.path.join(d, f"{base}_zone_{marque}.png"))
    progression and progression(0.15, _("Gemini remplace l'élément…"))
    octets = ia.generer_image_refs(params, consigne(quoi, entree), [chemin, zones] + references(entree))
    progression and progression(0.9, _("Mise aux dimensions de l'image d'origine…"))
    nom = "".join(c for c in entree.get("nom", "element") if c.isalnum() or c in " -_")[:30].strip().replace(" ", "_")
    sortie = aux_dimensions(octets, im.width(), im.height(), os.path.join(d, f"{base}_avec_{nom}_{marque}.png"))
    try:
        os.remove(zones)
    except OSError:
        pass
    return sortie
