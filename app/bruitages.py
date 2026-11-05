"""Bruitages (0.4.1) : petits sons fabriqués sur ce poste par le moteur vidéo (aucun téléchargement, libres de droits).

Chaque son est synthétisé une fois (bruit filtré, sinusoïdes, enveloppes) et gardé dans le dossier de PhilCut. On le pose
au curseur sur une piste de son libre ; il devient un plan comme un autre (volume, déplacer, supprimer).
"""
import os

from .langue import _

# id : (nom, description, source lavfi, durée en secondes, filtres)
SONS = {
    "whoosh": (_("Whoosh"), _("Souffle rapide : transition, filé, objet qui passe."),
               "anoisesrc=d={d}:c=pink:a=0.7", 0.8, "highpass=f=250,lowpass=f=5000,afade=t=in:d=0.4:curve=exp,afade=t=out:st=0.42:d=0.38,volume=1.4"),
    "impact": (_("Impact"), _("Coup sourd : choc, atterrissage, titre qui tombe."),
               "aevalsrc='0.9*sin(2*PI*(45+140*exp(-9*t))*t)*exp(-4.5*t)+0.25*(random(0)*2-1)*exp(-30*t)':d={d}", 1.0, "lowpass=f=2500"),
    "declic": (_("Déclic photo"), _("Obturateur d'appareil photo : image figée, polaroïd."),
               "aevalsrc='(random(0)*2-1)*0.8*(lt(t,0.018)+between(t,0.085,0.115)*exp(-(t-0.085)*40))':d={d}", 0.25, "highpass=f=900"),
    "bip": (_("Bip"), _("Bip court : compte à rebours, alerte, interface."), "sine=f=1000:d={d}", 0.15, "afade=t=out:st=0.11:d=0.04,volume=0.6"),
    "ding": (_("Ding"), _("Clochette claire : bonne nouvelle, apparition."),
             "aevalsrc='0.5*(sin(2*PI*1320*t)+0.45*sin(2*PI*2640*t)+0.2*sin(2*PI*3960*t))*exp(-3*t)':d={d}", 1.6, ""),
    "pop": (_("Pop"), _("Petite bulle : autocollant, Goodie ou texte qui apparaît."),
            "aevalsrc='0.9*sin(2*PI*(260+600*exp(-30*t))*t)*exp(-22*t)':d={d}", 0.25, ""),
    "radio": (_("Radio (pschitt)"), _("Souffle de radio à l'alternat : début ou fin d'un message radio."),
              "anoisesrc=d={d}:c=white:a=0.5", 0.3, "highpass=f=400,lowpass=f=3000,afade=t=out:st=0.2:d=0.1"),
    "moteur": (_("Moteur (ronron)"), _("Ronronnement grave d'un moteur à pistons, à mettre en boucle sous une scène."),
               "aevalsrc='0.35*sin(2*PI*42*t)*(0.7+0.3*sin(2*PI*21*t))+0.15*sin(2*PI*84*t)+0.05*(random(0)*2-1)':d={d}", 4.0,
               "lowpass=f=600,afade=t=in:d=0.3,afade=t=out:st=3.6:d=0.4"),
}


def dossier():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "bruitages")
    os.makedirs(d, exist_ok=True)
    return d


def chemin(ident):
    """Fichier WAV du bruitage (fabriqué la première fois)."""
    from . import moteur
    nom, _desc, src, duree, filtres = SONS[ident]
    f = os.path.join(dossier(), f"{ident}.wav")
    if not os.path.exists(f) or os.path.getsize(f) < 1000:
        tmp = f + ".part.wav"
        args = ["-f", "lavfi", "-i", src.format(d=duree)]
        if filtres:
            args += ["-af", filtres]
        moteur.lancer(args + ["-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", tmp])
        os.replace(tmp, f)
    return f


def piste_libre(projet, debut, duree):
    """Première piste de musique / sons sans plan entre debut et debut + duree ; une piste est ajoutée s'il le faut."""
    from .projet import fin_clip
    for p in projet.pistes_audio():
        if not any(c["debut"] < debut + duree and fin_clip(c) > debut for c in projet.clips_piste(p)):
            return p
    if len(projet.pistes_audio()) < 4:
        return projet.ajouter_piste("audio")
    return projet.pistes_audio()[-1]


def poser(projet, ident, debut, volume=1.0):
    """Pose le bruitage au moment `debut` ; renvoie le plan créé."""
    from . import moteur
    f = chemin(ident)
    m = next((x for x in projet.medias if x.get("chemin") == f), None)
    if m is None:
        m = projet.ajouter_media(f, moteur.sonder(f))
        m["nom"] = SONS[ident][0]
    d = float((m.get("fiche") or {}).get("duree") or SONS[ident][3])
    piste = piste_libre(projet, debut, d)
    c = projet.ajouter_clip(m["id"], piste, float(debut))
    c["volume"] = float(volume)
    c["nom"] = _("Bruitage : {n}", n=SONS[ident][0])
    projet.ranger(piste)
    return c
