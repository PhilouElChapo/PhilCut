"""1.0.5 : remplacer un élément d'une image par un élément de ma bibliothèque (Philippe, 20/11 22h31 : « garder le lieu, la photo
des filles ; l'avion enlevé et le Falcon mis à la place »).

Gemini reçoit, dans cet ordre : l'image d'origine, la même avec la zone à remplacer entourée de rouge, puis la fiche (et une
image) de l'élément de la bibliothèque. Il rend l'image modifiée ; PhilCut la remet aux dimensions de l'origine.
"""
import os
import time

from .langue import _

PRIX = 0.04          # une image Gemini (prix indicatif, noté dans « dépensé ce mois »)
PRIX_RELECTURE = 0.01

# 1.0.9 (Philippe, 21/11 08h51 : « comment être sûr que c'est un bon remplacement… prévoir les deux solutions ») :
# « auto » : Gemini trouve lui-même ce qu'il faut remplacer (rien à tracer) ; « place » : vous tracez où va le nouvel élément
# et choisissez son orientation. Dans les deux cas, une relecture par l'IA compare avant / après et la fiche.
MODES = {"auto": _("Gemini trouve et remplace tout seul (rien à tracer)"),
         "place": _("Je place moi-même : je trace où il va et je choisis son orientation")}
ORIENTATIONS = {"fiche": (_("Comme il vient (au mieux pour la scène)"), ""),
                "gauche": (_("Tourné vers la gauche de l'image"), "Its front/nose points to the LEFT of the frame."),
                "droite": (_("Tourné vers la droite de l'image"), "Its front/nose points to the RIGHT of the frame."),
                "face": (_("De face, vers la caméra"), "It faces the camera."),
                "trois_quarts": (_("De trois quarts"), "Seen in a three-quarter view."),
                "profil": (_("De profil"), "Seen exactly from the side.")}

CONSIGNE_AUTO = (
    "Edit the FIRST image. Find {quoi} in it and replace it with: {nom}. {description} The new element takes the same place, "
    "at a believable size for the scene, and must look exactly like the reference image(s) that follow (same shape, "
    "proportions, colours, markings), with the light, shadows and colours of the FIRST image. Nothing of what was removed may "
    "remain. Keep everything else strictly identical: the people (faces, expressions, hair, clothes), their position, the "
    "background, the framing and the image size. Photorealistic, no text, no added logo.")
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


def consigne(quoi, entree, mode="place", orientation="fiche"):
    d = (entree.get("description") or "").strip()
    q = f"« {quoi.strip()} »" if quoi.strip() else "the object outlined in red"
    base = CONSIGNE_AUTO if mode == "auto" else CONSIGNE
    texte = base.format(quoi=q, nom=f"« {entree.get('nom', '')} »", description=(f"Description: {d}." if d else ""))
    if mode != "auto":
        texte += " The red outline also gives the place and size of the new element."
    o = ORIENTATIONS.get(orientation, ("", ""))[1]
    return texte + (" " + o if o else "")


CONSIGNE_RELIRE = (
    "Tu compares deux images : la PREMIÈRE est l'originale, la DEUXIÈME a été retouchée pour y remplacer {quoi} par « {nom} », "
    "dont la ou les images de référence suivent. Vérifie honnêtement, sans complaisance : 1) remplace : l'ancien élément a "
    "disparu et le nouveau est là, à une taille et une perspective crédibles ; 2) ressemble : le nouvel élément ressemble à la "
    "référence (forme, couleurs, marquages) ; 3) personnes : les personnes sont restées identiques (visages, expressions, "
    "vêtements, position) ; 4) decor : le reste du décor, la lumière et le cadrage n'ont pas changé. Réponds en JSON : "
    "{{\"remplace\": true/false, \"ressemble\": true/false, \"personnes\": true/false, \"decor\": true/false, "
    "\"defauts\": \"ce qui ne va pas, en une ou deux phrases courtes, en français, vide si rien\"}}")

POINTS = (("remplace", _("Ancien élément remplacé")), ("ressemble", _("Ressemble à la fiche de la bibliothèque")),
          ("personnes", _("Personnes inchangées")), ("decor", _("Décor et lumière inchangés")))


def verifier(params, avant, apres, quoi, entree):
    """La relecture par l'IA (Claude ou Gemini selon les clefs) : {remplace, ressemble, personnes, decor, defauts}."""
    from . import ia
    r = ia.demander(params, CONSIGNE_RELIRE.format(quoi=f"« {quoi.strip()} »" if quoi.strip() else "un élément",
                                                    nom=entree.get("nom", "")),
                    _("Voici les images."), images=[avant, apres] + references(entree)[:1], json_attendu=True, max_jetons=600)
    if isinstance(r, str):
        r = ia.lire_json(r)
    r = r if isinstance(r, dict) else {}
    out = {k: bool(r.get(k)) for k, _l in POINTS}
    out["defauts"] = str(r.get("defauts") or "")[:300]
    return out


def remplacer(params, chemin, zone, quoi, entree, progression=None, mode="place", orientation="fiche"):
    """Fait le remplacement ; renvoie le chemin de la nouvelle image (dossier des créations IA). En mode « auto », pas de
    cadre : Gemini trouve lui-même ce qu'il faut remplacer."""
    from PySide6.QtGui import QImage
    from . import creations, ia
    im = QImage(chemin)
    if im.isNull():
        raise ValueError(_("Image illisible : {f}", f=chemin))
    d = creations.dossier()
    base = os.path.splitext(os.path.basename(chemin))[0][:40]
    marque = time.strftime("%Y%m%d-%H%M%S")
    zones = image_zone(chemin, zone, os.path.join(d, f"{base}_zone_{marque}.png")) if zone else ""
    progression and progression(0.15, _("Gemini remplace l'élément…"))
    texte = consigne(quoi, entree, mode if zones else "auto", orientation)
    if mode == "auto" and zones:
        texte += " The SECOND image is the same picture with the element to replace outlined in red (do not draw it)."
    octets = ia.generer_image_refs(params, texte,
                                   [chemin] + ([zones] if zones else []) + references(entree))
    progression and progression(0.9, _("Mise aux dimensions de l'image d'origine…"))
    nom = "".join(c for c in entree.get("nom", "element") if c.isalnum() or c in " -_")[:30].strip().replace(" ", "_")
    sortie = aux_dimensions(octets, im.width(), im.height(), os.path.join(d, f"{base}_avec_{nom}_{marque}.png"))
    if zones:
        try:
            os.remove(zones)
        except OSError:
            pass
    return sortie
