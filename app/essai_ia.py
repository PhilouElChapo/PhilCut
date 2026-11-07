"""Vérifier que les modèles d'IA locale installés marchent vraiment sur ce poste (0.9.3).

Pour chaque genre installé : un petit travail réel, chronométré (une image 256 px, 5 s de musique, une image passée en
dessin animé…). Le résultat (marche ou non, durée, carte graphique ou processeur) est gardé par poste dans
params["essais_ia"] et affiché dans Préférences › IA locale ; la durée sert d'ordre de grandeur pour les vrais travaux.
"""
import os
import tempfile
import time

from . import packs_ia as P
from .langue import _

# genres testables, dans l'ordre du plus rapide au plus long, avec ce que le test fait
ESSAIS = {
    "detourage": _("détourage d'une petite image"),
    "anime": _("une image passée en dessin animé"),
    "profondeur": _("carte de profondeur d'une petite image"),
    "vision": _("démarrage du modèle et une question sur une petite image"),
    "upscale": _("agrandissement d'une petite image"),
    "interpolation": _("une image intermédiaire entre deux images"),
    "image": _("une image de 256 px à partir d'une phrase"),
    "whisper": _("transcription de 3 secondes de son"),
    "voix": _("une phrase lue à voix haute"),
    "musique": _("5 secondes de musique"),
    "video": _("une très courte vidéo (long : plusieurs minutes)"),
}


def genres_installes(params=None):
    """Genres qui ont un modèle installé sur ce poste, dans l'ordre des essais."""
    out = []
    for g in ESSAIS:
        try:
            if P.modele_actif(g, params):
                out.append(g)
        except Exception:      # noqa: BLE001
            pass
    return out


def _image_essai(L=128, H=96):
    import numpy as np
    img = np.zeros((H, L, 3), dtype=np.uint8)
    img[:, :] = (180, 140, 90)
    import cv2
    cv2.circle(img, (L // 2, H // 2), H // 3, (60, 90, 220), -1)
    cv2.rectangle(img, (8, H - 30), (L // 3, H - 8), (40, 200, 80), -1)
    return img


def _peripherique(params):
    if (params or {}).get("ia_gpu", True) is not False and P.carte_graphique():
        return _("carte graphique ({c})", c=P.carte_graphique())
    return _("processeur (sans carte graphique : plus lent, résultat plus faible pour les images)")


def tester(genre, params=None, progression=None, arret=lambda: False):
    """Teste le modèle actif du genre. Renvoie {"ok", "secondes", "modele", "peripherique", "message", "date"}."""
    cle = P.modele_actif(genre, params)
    res = {"genre": genre, "modele": cle or "", "ok": False, "secondes": None, "message": "", "date": time.strftime("%Y-%m-%d %H:%M"),
           "peripherique": _peripherique(params)}
    if not cle:
        res["message"] = _("Aucun modèle installé.")
        return res
    nom = (P.modeles(avec_essai=True).get(cle) or {}).get("nom", cle)
    res["nom"] = nom
    dossier = tempfile.mkdtemp(prefix="philcut-essai-")
    debut = time.time()

    def avance(f, t=""):
        if progression:
            try:
                progression(f, t)
            except TypeError:
                progression(f)
    try:
        from . import creatif as C
        avance(0.0, _("{n} : {q}…", n=nom, q=ESSAIS[genre]))
        if genre == "detourage":
            m = P.masque_personne(_image_essai(), params=params)
            if m is None:
                raise RuntimeError(_("le moteur de détourage n'est pas utilisable (onnxruntime)"))
        elif genre == "anime":
            C.anime_image(_image_essai(), params=params)
        elif genre == "profondeur":
            C.profondeur(_image_essai(), params=params)
        elif genre == "vision":
            from . import ia_locale
            r = ia_locale.tester(params)
            if not r.get("secondes"):
                raise RuntimeError(r.get("avis") or _("pas de réponse"))
        elif genre in ("upscale", "interpolation"):
            v = os.path.join(dossier, "essai.mp4")
            from . import moteur
            moteur.lancer(["-y", "-f", "lavfi", "-i", "testsrc=s=128x96:r=10:d=0.4", "-pix_fmt", "yuv420p", v])
            sortie = os.path.join(dossier, "sortie.mp4")
            if genre == "upscale":
                C.agrandir(v, sortie, facteur=2, ips=10, params=params, progression=avance, arret=arret)
            else:
                C.ralentir(v, sortie, facteur=2, ips=10, params=params, progression=avance, arret=arret)
            if not os.path.exists(sortie):
                raise RuntimeError(_("aucun fichier produit"))
        elif genre == "image":
            C.image("a red apple on a wooden table, photo", os.path.join(dossier, "essai.png"), params=params, largeur=256, hauteur=256,
                    progression=avance, arret=arret)
        elif genre == "whisper":
            from . import moteur, sous_titres
            w = os.path.join(dossier, "essai.wav")
            moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=440:d=3", "-ar", "16000", "-ac", "1", w])
            sous_titres.transcrire_fichier(w, langue="fr", params=params)
        elif genre == "voix":
            from . import voix
            voix.lire(_("Bonjour, ceci est un essai."), os.path.join(dossier, "essai.wav"), params)
        elif genre == "musique":
            C.musique("calm piano", os.path.join(dossier, "essai.wav"), duree=5.0, params=params, progression=avance, arret=arret)
        elif genre == "video":
            C.video("a calm lake at sunset", os.path.join(dossier, "essai.mp4"), params=params, secondes=0.5, largeur=256, hauteur=160,
                    progression=avance, arret=arret)
        res["ok"] = True
        res["secondes"] = round(time.time() - debut, 1)
        res["message"] = _("Fonctionne : {q} en {s} s.", q=ESSAIS[genre], s=res["secondes"])
    except InterruptedError:
        res["message"] = _("Test arrêté.")
    except Exception as e:       # noqa: BLE001 : le message dit pourquoi
        from . import diagnostic_ia as D
        res["secondes"] = round(time.time() - debut, 1)
        res["detail"] = str(e)[:4000]
        res["journal"] = getattr(e, "journal", None) or ""
        res["moteur"] = getattr(e, "genre", None) or ""
        res["cause"] = D.diagnostiquer(res["detail"], res["moteur"] or genre)["titre"]
        res["message"] = _("Ne fonctionne pas : {c}.", c=res["cause"])
    finally:
        import shutil
        shutil.rmtree(dossier, ignore_errors=True)
    avance(1.0, res["message"])
    return res


def tester_tout(params=None, genres=None, progression=None, arret=lambda: False):
    """Teste chaque genre installé l'un après l'autre ; renvoie {genre: résultat} et l'enregistre dans params."""
    genres = genres or genres_installes(params)
    out = {}
    n = max(1, len(genres))
    for i, g in enumerate(genres):
        if arret():
            break
        sous = (lambda f, t="", i=i: progression((i + f) / n, _("Test {i}/{n} : {t}", i=i + 1, n=n, t=t))) if progression else None
        out[g] = tester(g, params, sous, arret)
    if params is not None:
        essais = dict(params.get("essais_ia") or {})
        essais.update(out)
        params["essais_ia"] = essais
    return out


def resume(r):
    """Une ligne courte pour les Préférences (le détail technique est à part, replié)."""
    if not r:
        return _("Pas encore testé.")
    signe = "✓" if r.get("ok") else "✕"
    msg = r.get("message", "") or (_("Ne fonctionne pas : {c}.", c=r["cause"]) if r.get("cause") else "")
    if not r.get("ok") and not r.get("cause"):             # ancien résultat : on raccourcit le message brut du moteur
        from . import diagnostic_ia as D
        msg = _("Ne fonctionne pas : {c}.", c=D.diagnostiquer(msg, r.get("genre"))["titre"])
    return f"{signe} {msg}"


def sous_titre(r):
    """Sur quoi et quand : « carte graphique (…) · 2026-11-07 21:10 »."""
    if not r:
        return ""
    return " · ".join(x for x in (r.get("peripherique", ""), r.get("date", "")) if x)
