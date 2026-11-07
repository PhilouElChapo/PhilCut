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
    # 0.9.15 : la famille s'agrandit (toujours fabriqués ici, libres de droits)
    "whoosh_inverse": (_("Whoosh inversé"), _("Souffle qui monte puis s'arrête net : avant une coupe, une révélation."),
                       "anoisesrc=d={d}:c=pink:a=0.7", 0.9, "highpass=f=300,lowpass=f=6000,afade=t=in:d=0.85:curve=exp,afade=t=out:st=0.85:d=0.05"),
    "montee": (_("Montée (riser)"), _("Tension qui monte pendant 2 secondes : avant le moment fort."),
               "aevalsrc='0.35*sin(2*PI*(200*t+300*t*t)*1)+0.2*(random(0)*2-1)*t/2':d={d}", 2.0, "highpass=f=150,afade=t=in:d=1.8:curve=exp,afade=t=out:st=1.95:d=0.05"),
    "descente": (_("Descente"), _("Son qui tombe : déception, chute, retour au calme."),
                 "aevalsrc='0.5*sin(2*PI*(900*t-350*t*t))*exp(-0.8*t)':d={d}", 1.2, "afade=t=out:st=0.9:d=0.3"),
    "boom": (_("Boum grave"), _("Basse profonde : titre qui claque, moment de cinéma."),
             "aevalsrc='0.95*sin(2*PI*(38+60*exp(-6*t))*t)*exp(-2.2*t)':d={d}", 2.0, "lowpass=f=300"),
    "tic_tac": (_("Tic-tac"), _("Horloge : attente, compte à rebours, suspense."),
                "aevalsrc='(random(0)*2-1)*0.7*(lt(mod(t,1),0.012)+0.6*between(mod(t,1),0.5,0.51))':d={d}", 4.0, "highpass=f=1500,lowpass=f=6000"),
    "buzzer": (_("Buzzer (erreur)"), _("Mauvaise réponse, raté, interdit."),
               "aevalsrc='0.35*(sgn(sin(2*PI*140*t))+0.5*sgn(sin(2*PI*147*t)))':d={d}", 0.6, "lowpass=f=2500,afade=t=out:st=0.5:d=0.1"),
    "validation": (_("Validation"), _("Deux notes qui montent : réussi, étape validée ✓."),
                   "aevalsrc='0.5*sin(2*PI*(if(lt(t,0.12),880,1320))*t)*exp(-6*mod(t,0.12))':d={d}", 0.5, "afade=t=out:st=0.4:d=0.1"),
    "notification": (_("Notification"), _("Petit son de téléphone : message, alerte douce."),
                     "aevalsrc='0.45*sin(2*PI*1568*t)*exp(-12*t)+0.35*between(t,0.13,1)*sin(2*PI*2093*(t-0.13))*exp(-12*(t-0.13))':d={d}", 0.6, ""),
    "laser": (_("Laser"), _("Tir de science-fiction, jeu vidéo."),
              "aevalsrc='0.4*sin(2*PI*(2500*t-9000*t*t))*exp(-9*t)':d={d}", 0.3, ""),
    "tambour": (_("Roulement de tambour"), _("Avant une annonce, un résultat, un « tadaa »."),
                "aevalsrc='(random(0)*2-1)*(0.3+0.4*t/2)*(0.6+0.4*sin(2*PI*28*t))':d={d}", 2.2, "highpass=f=180,lowpass=f=4500,afade=t=out:st=2.05:d=0.15"),
    "cymbale": (_("Cymbale"), _("Coup de cymbale : fin du roulement, grande annonce."),
                "anoisesrc=d={d}:c=white:a=0.8", 2.0, "highpass=f=3000,afade=t=out:st=0.05:d=1.95:curve=exp"),
    "gong": (_("Gong"), _("Grand gong : ouverture, moment solennel."),
             "aevalsrc='0.5*(sin(2*PI*110*t)+0.6*sin(2*PI*167*t)+0.4*sin(2*PI*231*t)+0.2*sin(2*PI*347*t))*exp(-0.9*t)':d={d}", 4.0, "lowpass=f=3000"),
    "sonnette": (_("Sonnette (ding-dong)"), _("Quelqu'un arrive, nouveau chapitre."),
                 "aevalsrc='0.5*(lt(t,0.6)*sin(2*PI*659*t)*exp(-3*t)+gte(t,0.6)*sin(2*PI*523*t)*exp(-2.5*(t-0.6)))':d={d}", 1.8, ""),
    "coeur": (_("Battement de cœur"), _("Stress, suspense, émotion."),
              "aevalsrc='0.9*sin(2*PI*55*t)*(exp(-25*mod(t,0.9))+0.7*exp(-25*abs(mod(t,0.9)-0.22))*gte(mod(t,0.9),0.22))':d={d}", 3.6, "lowpass=f=200"),
    "boing": (_("Boing (ressort)"), _("Rebond de dessin animé : chute comique, saut."),
              "aevalsrc='0.6*sin(2*PI*(180+120*sin(2*PI*14*t))*t)*exp(-3*t)':d={d}", 1.0, ""),
    "machine": (_("Machine à écrire"), _("Frappe de touches : texte qui s'écrit à l'image."),
                "aevalsrc='(random(0)*2-1)*0.8*lt(mod(t,0.13),0.01)':d={d}", 2.0, "highpass=f=1200,lowpass=f=7000"),
    "sifflet": (_("Sifflet"), _("Coup de sifflet : départ, fin, faute."),
                "aevalsrc='0.4*sin(2*PI*(2800+60*sin(2*PI*35*t))*t)':d={d}", 0.7, "afade=t=in:d=0.03,afade=t=out:st=0.6:d=0.1"),
    "vent": (_("Vent"), _("Vent qui souffle : extérieur, altitude, montagne (fond sonore)."),
             "anoisesrc=d={d}:c=brown:a=0.6", 6.0, "lowpass=f=700,tremolo=f=0.3:d=0.5,afade=t=in:d=1,afade=t=out:st=5:d=1"),
    "pluie": (_("Pluie"), _("Pluie régulière (fond sonore)."),
              "anoisesrc=d={d}:c=pink:a=0.5", 6.0, "highpass=f=800,lowpass=f=9000,afade=t=in:d=1,afade=t=out:st=5:d=1"),
    "glitch": (_("Glitch numérique"), _("Bug d'écran, transition « numérique »."),
               "aevalsrc='0.5*sgn(sin(2*PI*(200+1800*random(0)*lt(mod(t,0.05),0.025))*t))*lt(mod(t,0.11),0.07)':d={d}", 0.6, "lowpass=f=6000"),
    "caisse": (_("Caisse enregistreuse"), _("Ka-tching : argent, prix, bonne affaire."),
               "aevalsrc='(random(0)*2-1)*0.7*lt(t,0.03)+0.5*between(t,0.08,1.2)*(sin(2*PI*2093*t)+0.5*sin(2*PI*2637*t))*exp(-4*(t-0.08))':d={d}", 1.2, ""),
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
