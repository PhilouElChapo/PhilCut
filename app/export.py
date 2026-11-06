"""Export : traduit le projet en une commande FFmpeg (filtres), puis encode avec le meilleur encodeur du poste.

Etapes : bande video (plans, vitesse, cadrage, effets, transitions) -> calques generes (feu d'artifice, puzzle,
Goodies...) -> titres (ASS) -> son (plans, musiques, normalisation YouTube -14 LUFS) -> fichier final.
Tout est ecrit dans un dossier temporaire ; progression et arret possibles.
"""
import os, shutil, tempfile

from . import effets as E, generateurs as G, goodies as GO, moteur, titres as T
from .projet import duree_clip, fin_clip

# effets audio d'un plan (menu Voix et son)
_NARRATION_FIN = ("deesser=i=0.45,equalizer=f=280:t=q:w=1.2:g=-3,equalizer=f=3200:t=q:w=1:g=2.5,treble=g=2:f=9000,"
                  "acompressor=threshold=-24dB:ratio=3.5:attack=5:release=120:makeup=5,speechnorm=e=6:r=0.0001:l=1,alimiter=limit=0.92")
FILTRES_AUDIO = {
    # narration : vraie chaîne de traitement de la voix parlée (coupe-bas, débruitage, porte de bruit entre les phrases,
    # « s » adoucis, moins de boue, présence, air, compression, niveau de parole régulier, limiteur)
    "a_narration": "highpass=f=80,afftdn=nr=14:nf=-38:tn=1,agate=threshold=0.015:ratio=2:range=0.25:attack=5:release=180," + _NARRATION_FIN,
    "a_narration_chaude": "highpass=f=70,afftdn=nr=12:nf=-38:tn=1,agate=threshold=0.015:ratio=2:range=0.3:attack=5:release=200,deesser=i=0.5,"
                          "equalizer=f=140:t=q:w=1:g=3,equalizer=f=400:t=q:w=1.2:g=-2,equalizer=f=2800:t=q:w=1:g=1.5,"
                          "acompressor=threshold=-26dB:ratio=4:attack=8:release=160:makeup=6,speechnorm=e=6:r=0.0001:l=1,alimiter=limit=0.92",
    "a_narration_bruit": "highpass=f=100,afftdn=nr=24:nf=-30:tn=1,anlmdn=s=6,agate=threshold=0.025:ratio=3:range=0.15:attack=5:release=150," + _NARRATION_FIN,
    "a_debruit": "afftdn=nf=-25:tn=1,highpass=f=80",
    "a_voix": "highpass=f=90,lowpass=f=12000,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3000:t=q:w=1:g=2,acompressor=threshold=-18dB:ratio=3:attack=10:release=120:makeup=4,alimiter=limit=0.95",
    "a_autotune": "acompressor=threshold=-16dB:ratio=4,chorus=0.6:0.9:50|60:0.4|0.32:0.25|0.4:2|1.3",      # effet chorus ; la vraie correction de justesse : app/autotune.py
    "a_reverb": "aecho=0.8:0.9:40|60|90:0.35|0.25|0.15",
    "a_echo": "aecho=0.8:0.88:320:0.4",
    # voix « harmonieuse » : coupe des graves sourds, débruitage, sifflements adoucis, moins nasale, chaleur et présence,
    # dynamique tenue, léger espace ; tout en local
    "a_harmonieuse": "highpass=f=80,afftdn=nf=-25:tn=1,deesser=i=0.4,equalizer=f=1000:t=q:w=1.4:g=-3,equalizer=f=200:t=q:w=1:g=2,"
                     "equalizer=f=4500:t=q:w=1:g=1.5,acompressor=threshold=-20dB:ratio=3:attack=8:release=150:makeup=4,"
                     "aecho=0.8:0.6:25:0.10,alimiter=limit=0.95",
    "a_desser": "deesser=i=0.5",
    "a_anti_nasal": "equalizer=f=1000:t=q:w=1.4:g=-4",
    "a_chaude": "equalizer=f=150:t=q:w=1:g=3,equalizer=f=6000:t=q:w=1:g=-2",
    "a_claire": "highpass=f=120,equalizer=f=3500:t=q:w=1:g=3",
    "a_radio": "highpass=f=300,lowpass=f=3400,acompressor=threshold=-22dB:ratio=6:attack=5:release=80:makeup=6,aeval=val(0)*0.9|val(1)*0.9",
    "a_grave": "rubberband=pitch=0.9:formant=preserved",
    "a_aigu": "rubberband=pitch=1.1:formant=preserved",
}
TIMBRE_SECOURS = {"a_grave": "asetrate=48000*0.9,aresample=48000,atempo=1.111", "a_aigu": "asetrate=48000*1.1,aresample=48000,atempo=0.909"}
NARRATION = [("", "Aucune (voix brute)"), ("a_studio", "Voix studio, façon Insta (conseillé)"), ("a_narration", "Narration claire"), ("a_narration_chaude", "Narration chaude (radio)"),
             ("a_narration_bruit", "Pièce bruyante (débruitage fort)")]
VOIX = [("a_studio", "Voix studio, façon Insta (débruitage IA locale)"), ("a_studio_doux", "Voix studio, plus naturelle"),
        ("a_narration", "Narration claire (traitement complet)"), ("a_narration_chaude", "Narration chaude (radio)"),
        ("a_narration_bruit", "Narration, pièce bruyante"),
        ("a_harmonieuse", "Voix harmonieuse (tout en un)"), ("a_voix", "Voix embellie (narration)"), ("a_debruit", "Débruiter (vent, moteur)"),
        ("a_desser", "Adoucir les « s » qui sifflent"), ("a_anti_nasal", "Moins nasale"), ("a_chaude", "Plus chaude"), ("a_claire", "Plus claire"),
        ("a_grave", "Timbre plus grave"), ("a_aigu", "Timbre plus aigu"), ("a_radio", "Effet radio (ATC)"),
        ("a_autotune", "Effet chorus (chant)"), ("a_reverb", "Réverbération"), ("a_echo", "Echo")]


def modele_rnnoise(genre="parole"):
    """Chemin du modèle RNNoise livré avec PhilCut (catalogue/voix), écrit pour un filtre FFmpeg ; None s'il manque."""
    import sys
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(base, "catalogue", "voix", f"{genre}.rnnn")
    if not os.path.exists(p) or not moteur.filtre_disponible("arnndn"):
        return None
    return "'" + p.replace("\\", "/").replace(":", "\\:").replace("'", "") + "'"


def chaine_studio(force=1.0, genre="parole"):
    """Voix « studio », façon amélioration de voix d'Instagram : débruitage par réseau de neurones (RNNoise, sur ce
    poste), sifflements adoucis, moins de boue et de nasalité, chaleur, présence et air, compression en deux temps,
    niveau de parole régulier, limiteur. Sans écho ajouté : la voix est proche et nette."""
    m = modele_rnnoise(genre)
    debruit = f"arnndn=m={m}:mix={min(1.0, 0.75 + 0.25 * force):.2f}" if m else f"afftdn=nr={int(12 + 10 * force)}:nf=-35:tn=1"
    return ("highpass=f=75:p=2," + debruit + ",agate=threshold=0.01:ratio=1.6:range=0.4:attack=4:release=200,"
            f"deesser=i={0.35 + 0.2 * force:.2f}:m=0.5:f=0.5,"
            "equalizer=f=120:t=q:w=0.9:g=2.5,equalizer=f=300:t=q:w=1.1:g=-3.5,equalizer=f=1100:t=q:w=1.6:g=-2,"
            f"equalizer=f=3400:t=q:w=1.0:g={2 + 1.5 * force:.1f},highshelf=f=9500:g={2.5 + 1.5 * force:.1f},"
            "acompressor=threshold=-26dB:ratio=2.5:attack=12:release=180:makeup=3:knee=6,"
            "acompressor=threshold=-14dB:ratio=5:attack=2:release=60:makeup=2,"
            "speechnorm=e=8:r=0.00005:l=1:p=0.9,alimiter=limit=0.93:level=disabled")


def filtre_audio(eid):
    """Filtre d'un préréglage de voix ; le changement de timbre se replie sur asetrate si rubberband manque."""
    if eid == "a_studio":
        return chaine_studio(1.0)
    if eid == "a_studio_doux":
        return chaine_studio(0.5, "voix")
    f = FILTRES_AUDIO.get(eid)
    if eid in TIMBRE_SECOURS and not moteur.filtre_disponible("rubberband"):
        return TIMBRE_SECOURS[eid]
    return f

LUFS = {"youtube": -14, "youtube4k": -14, "insta": -14, "insta_carre": -14, "whatsapp": -16, "ecran_led": -14, "original": -14}


class Exportateur:
    def __init__(self, projet, sortie, destination="youtube", qualite=None, encodeur=None, params=None, dossier_tmp=None):
        from .projet import decouper_effets_partiels
        self.p = decouper_effets_partiels(projet)      # effet sur une partie du plan : le plan est coupé à ses bornes
        self.sortie = sortie
        self.dest = destination
        self.params = params or {}
        d = moteur.destination(destination)
        self.L, self.H = (d[1], d[2]) if d[1] else projet.taille
        if destination == "original":
            self.L, self.H = projet.taille
        if destination == "whatsapp" and projet.taille[1] > projet.taille[0]:     # allégé, mais dans le sens du projet
            self.L, self.H = self.H, self.L
        self.cad = d[3] or projet.cadence
        self.qualite = qualite or d[4]
        self.debit_audio = d[5]
        self.enc = encodeur or (self.params.get("encodeur") or moteur.encodeurs()[0])
        self.tmp = dossier_tmp or tempfile.mkdtemp(prefix="philcut-export-")
        self.entrees = []           # ["-i", chemin] groupes
        self.filtres = []
        self._n = 0
        self.journal = []
        self.sans_son = False       # image seule (aperçu fidèle) : pas de piste audio dans le graphe

    # ---------------------------------------------------------------- utilitaires
    def _entree(self, *args):
        self.entrees.append(list(args))
        return len(self.entrees) - 1

    def _nom(self, prefixe):
        self._n += 1
        return f"{prefixe}{self._n}"

    def _cadrage(self, clip, m):
        """Met le plan au format du projet : remplir (recadre), contenir_noir (bandes), contenir_flou (fond flou)."""
        L, H = self.L, self.H
        mode = clip.get("ajustement", "remplir")
        if mode == "suivi" and (clip.get("suivi_cadre") or {}).get("positions"):
            from . import suivi
            return suivi.filtre_recadrage(clip["suivi_cadre"], clip, L, H)
        if mode == "contenir_noir":
            return f"scale={L}:{H}:force_original_aspect_ratio=decrease,pad={L}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"
        if mode == "contenir_flou":         # étiquettes uniques : plusieurs plans peuvent avoir un fond flou
            a, b, fo, dv = self._nom("cfa"), self._nom("cfb"), self._nom("cff"), self._nom("cfd")
            return (f"split[{a}][{b}];[{b}]scale={L}:{H}:force_original_aspect_ratio=increase,crop={L}:{H},gblur=sigma=30,eq=brightness=-0.08[{fo}];"
                    f"[{a}]scale={L}:{H}:force_original_aspect_ratio=decrease[{dv}];[{fo}][{dv}]overlay=(W-w)/2:(H-h)/2")
        return f"scale={L}:{H}:force_original_aspect_ratio=increase,crop={L}:{H}"

    # ---------------------------------------------------------------- bande video
    def _segments_video(self):
        clips = self.p.clips_piste("video")
        segs = []
        t = 0.0
        self.calques = []           # (debut, fin, entree, x, y)
        longueurs, fusions = [], []        # durée réelle de chaque segment, transition « fusion » avec le précédent
        ext_prec = 0.0
        for i, c in enumerate(clips):
            if c["debut"] > t + 0.02:           # trou : noir
                segs.append(self._noir(c["debut"] - t))
                longueurs.append(c["debut"] - t)
                fusions.append(None)
                ext_prec = 0.0
            suivant = clips[i + 1] if i + 1 < len(clips) else None
            fs = E.fusion(E.transition_active(suivant)) if suivant and abs(suivant["debut"] - fin_clip(c)) < 0.05 else None
            ext = min(fs[1], duree_clip(suivant) * 0.9) if fs else 0.0
            # fusion avec le précédent : il a été prolongé de ext_prec (seulement s'il touche ce plan)
            fe = E.fusion(E.transition_active(c))
            fusions.append((fe[0], ext_prec, c["transition"]["id"]) if fe and ext_prec > 0 else None)
            segs.append(self._clip_video(c, suivant, ext))
            longueurs.append(duree_clip(c) + ext)
            ext_prec = ext
            t = fin_clip(c)
        duree_titres = max([x.get("fin", 0) for x in self.p.titres + self.p.goodies] + [0])
        if duree_titres > t + 0.02:
            segs.append(self._noir(duree_titres - t))
            longueurs.append(duree_titres - t)
            fusions.append(None)
            t = duree_titres
        self.duree = t
        if not segs:
            segs.append(self._noir(1.0))
            self.duree = 1.0
        if len(segs) == 1:
            return segs[0]
        if not any(fusions):
            nom = self._nom("vcat")
            self.filtres.append("".join(f"[{s}]" for s in segs) + f"concat=n={len(segs)}:v=1:a=0[{nom}]")
            return nom
        # avec des fusions : on enchaîne deux à deux ; le segment précédent a été prolongé de la durée de la fusion
        cour, long_cour = segs[0], longueurs[0]
        for s, lg, fu in zip(segs[1:], longueurs[1:], fusions[1:]):
            nom = self._nom("vx")
            if fu:
                genre, d, eid = fu
                flou = ""
                if eid in E.FLOU_FUSION:            # filé : flou de mouvement horizontal pendant le passage
                    part = E.FLOU_FUSION[eid]
                    k = max(2, int((self.L if part > 0 else self.H) * abs(part)))
                    sx, sy = (k, 1) if part > 0 else (1, k)
                    flou = f",avgblur=sizeX={sx}:sizeY={sy}:enable='between(t,{long_cour - d:.3f},{long_cour:.3f})'"
                self.filtres.append(f"[{cour}][{s}]xfade=transition={genre}:duration={d:.3f}:offset={long_cour - d:.3f}{flou}[{nom}]")
                long_cour = long_cour + lg - d
            else:
                self.filtres.append(f"[{cour}][{s}]concat=n=2:v=1:a=0[{nom}]")
                long_cour += lg
            cour = nom
        return cour

    def _noir(self, duree):
        k = self._entree("-f", "lavfi", "-t", f"{duree:.3f}", "-i", f"color=c=black:s={self.L}x{self.H}:r={self.cad}")
        nom = self._nom("noir")
        self.filtres.append(f"[{k}:v]format=yuv420p,setsar=1[{nom}]")
        return nom

    def _clip_video(self, c, suivant, ext=0.0):
        """ext : prolongation (s) de la fin du plan pour une transition « fusion » avec le suivant : images suivantes
        du rush si elles existent, sinon dernière image figée."""
        m = self.p.media(c["media"])
        fiche = m.get("fiche") or {}
        v = fiche.get("video") or {}
        d = duree_clip(c)
        if m["genre"] == "image":
            k = self._entree("-loop", "1", "-framerate", str(self.cad), "-t", f"{d + ext:.3f}", "-i", m["chemin"])
            chaine = [f"[{k}:v]format=yuv420p,setpts=PTS-STARTPTS"]
        else:
            k = self._entree("-ss", f"{c['src_debut']:.3f}", "-t", f"{(c['src_fin'] - c['src_debut']) + ext * c.get('vitesse', 1.0):.3f}", "-i", m["chemin"])
            chaine = [f"[{k}:v]setpts=(PTS-STARTPTS)/{c.get('vitesse', 1.0):.4f}"]
            if v.get("hdr"):
                chaine.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
        chaine.append(f"fps={self.cad}")
        chaine.append(self._cadrage(c, m))
        chaine.append("format=yuv420p")
        ctx = {"cadence": self.cad, "largeur": self.L, "hauteur": self.H, "duree": d, "debut": c["debut"]}
        avance = float(c.get("_avance") or 0.0)     # extrait (aperçu) : les effets gardent l'horloge du plan entier
        if avance > 0:
            chaine.append(f"setpts=PTS+{avance:.3f}/TB")
        for e in E.actifs(c):
            f = E.filtre(e, ctx) or E.filtre_en_ligne(e["id"])
            if f:
                chaine.append(f)
            elif e["id"] in E.GENERES:
                self._calque_effet(e, c, ctx)
            if e["id"] == "detourage":
                chaine = self._detourage(chaine, e, c, d)
            elif e["id"] in ("double_exposition", "chroma_key", "avant_apres"):
                chaine = self._avec_second_media(chaine, e, c, d)
        if avance > 0:
            chaine.append("setpts=PTS-STARTPTS")
        # transition du clip suivant : sortie de celui-ci
        if suivant and E.transition_active(suivant):
            fs = E.filtre_sortie_transition(suivant["transition"])
            if fs:
                chaine.append(fs.replace("{st}", f"{max(0.0, d - float((suivant['transition'].get('params') or {}).get('duree', E.defauts(suivant['transition']['id']).get('duree', 0.5)))):.3f}"))
        if E.transition_active(c) and not E.fusion(c["transition"]):
            f = E.filtre(c["transition"], ctx)
            if f:
                chaine.append(f)
            else:
                self._calque_transition(c["transition"], c, ctx)
        if ext > 0:
            chaine.append(f"tpad=stop_mode=clone:stop_duration={ext:.3f}")
        chaine.append(f"trim=duration={d + ext:.3f},setpts=PTS-STARTPTS,setsar=1")
        nom = self._nom("v")
        self.filtres.append(",".join(chaine) + f"[{nom}]")
        return nom

    def _detourage(self, chaine, e, c, d):
        """Changer le fond : masque de la personne (segmentation.py) ; nouveau fond = média du projet, fond flouté ou couleur."""
        p = dict(E.defauts("detourage"))
        p.update(e.get("params") or {})
        fond = p.get("fond") or "media"
        if fond == "media":
            if not p.get("media") or not self.p.media(p["media"]):
                self.journal.append("changer le fond : aucune image ou vidéo choisie, fond d'origine gardé")
                return chaine
            return self._avec_second_media(chaine, e, c, d)
        masque = self._masque_sequence(c)
        if not masque:
            return chaine
        km = self._entree("-framerate", str(self.cad), "-i", masque)
        a, a1, a2, bg, mk, fg, out = (self._nom(x) for x in ("prim", "pa", "pb", "fond", "msk", "fg", "mix"))
        self.filtres.append(",".join(chaine) + f"[{a}]")
        if fond == "flou":
            self.filtres.append(f"[{a}]split[{a1}][{a2}]")
            self.filtres.append(f"[{a2}]gblur=sigma=40,eq=brightness=-0.08:saturation=0.8[{bg}]")
        else:
            a1 = a
            coul = str(p.get("couleur") or "#1d2b3a").lstrip("#")
            kc = self._entree("-f", "lavfi", "-t", f"{d:.3f}", "-i", f"color=c=0x{coul}:s={self.L}x{self.H}:r={self.cad}")
            self.filtres.append(f"[{kc}:v]format=yuv420p[{bg}]")
        douceur = float(p.get("adoucir", 1.0))
        flou = f",gblur=sigma={douceur * 2:.2f}" if douceur > 0 else ""
        self.filtres.append(f"[{km}:v]format=gray,scale={self.L}:{self.H}{flou}[{mk}]")
        self.filtres.append(f"[{a1}][{mk}]alphamerge[{fg}]")
        self.filtres.append(f"[{bg}][{fg}]overlay=0:0:format=auto,format=yuv420p[{out}]")
        return [f"[{out}]null"]

    def _avec_second_media(self, chaine, e, c, d):
        """Double exposition / fond vert / detourage : second media mis au format et combine."""
        ident = (e.get("params") or {}).get("media")
        m2 = self.p.media(ident) if ident else None
        if not m2:
            return chaine
        avance = float(c.get("_avance") or 0.0)
        if m2["genre"] == "image":
            k = self._entree("-loop", "1", "-framerate", str(self.cad), "-t", f"{d:.3f}", "-i", m2["chemin"])
        else:
            k = self._entree("-stream_loop", "-1", "-ss", f"{avance:.3f}", "-t", f"{d:.3f}", "-i", m2["chemin"])
        a, b = self._nom("prim"), self._nom("sec")
        self.filtres.append(",".join(chaine + (["setpts=PTS-STARTPTS"] if avance > 0 else [])) + f"[{a}]")
        self.filtres.append(f"[{k}:v]fps={self.cad},scale={self.L}:{self.H}:force_original_aspect_ratio=increase,crop={self.L}:{self.H},format=yuv420p,trim=duration={d:.3f},setpts=PTS-STARTPTS[{b}]")
        out = self._nom("mix")
        if e["id"] == "double_exposition":
            op = float((e.get("params") or {}).get("opacite", 0.5))
            self.filtres.append(f"[{a}][{b}]blend=all_mode=screen:all_opacity={op:.2f}[{out}]")
        elif e["id"] == "avant_apres":
            pa = dict(E.defauts("avant_apres"))
            pa.update(e.get("params") or {})
            police = os.path.join(T.dossier_polices(), "Nunito-800.ttf").replace("\\", "/").replace(":", "\\:")
            fs = max(18, int(self.H * 0.045))
            boite = f":box=1:boxcolor=black@0.55:boxborderw={fs // 3}:fontcolor=white:fontsize={fs}:fontfile='{police}'"
            if pa.get("mode") == "moitie":
                g_, mz = self._nom("av"), self._nom("avm")
                self.filtres.append(f"[{b}]crop=iw/2:ih:0:0[{g_}]")
                self.filtres.append(f"[{a}][{g_}]overlay=0:0,drawbox=x=iw/2-2:y=0:w=4:h=ih:color=white@0.9:t=fill[{mz}]")
                lib = (f",drawtext=text='AVANT':x=w*0.04:y=h*0.06{boite},drawtext=text='APRES':x=w*0.96-tw:y=h*0.06{boite}"
                       if pa.get("libelles", True) else "")
                self.filtres.append(f"[{mz}]null{lib}[{out}]")
            else:
                dep = float(pa.get("debut", 0.5)) - avance
                du = float(pa.get("duree", 2.0))
                if dep < 0:                     # extrait commencé pendant le rideau : il finit à la même heure
                    du, dep = max(0.05, du + dep), 0.0
                dep = max(0.0, min(d - 0.1, dep))
                du = max(0.05, min(d - dep - 0.02, du))
                mz = self._nom("avm")
                self.filtres.append(f"[{b}][{a}]xfade=transition=wiperight:duration={du:.3f}:offset={dep:.3f}[{mz}]")
                lib = (f",drawtext=text='AVANT':x=w*0.04:y=h*0.06{boite}:enable='lt(t,{dep + du:.3f})'"
                       f",drawtext=text='APRES':x=w*0.96-tw:y=h*0.06{boite}:enable='gt(t,{dep:.3f})'" if pa.get("libelles", True) else "")
                self.filtres.append(f"[{mz}]null{lib}[{out}]")
        elif e["id"] == "chroma_key":
            coul = (e.get("params") or {}).get("couleur", "#00ff00").lstrip("#")
            tol = float((e.get("params") or {}).get("tolerance", 0.3))
            fg = self._nom("fg")
            self.filtres.append(f"[{a}]format=yuva420p,chromakey=0x{coul}:{tol:.2f}:0.1[{fg}]")
            self.filtres.append(f"[{b}][{fg}]overlay=0:0:format=auto[{out}]")
        else:   # detourage : masque IA (segmentation.py) prepare en PNG
            masque = self._masque_sequence(c)
            if masque:
                km = self._entree("-framerate", str(self.cad), "-i", masque)
                fg = self._nom("fg")
                self.filtres.append(f"[{a}][{km}:v]alphamerge[{fg}]")
                self.filtres.append(f"[{b}][{fg}]overlay=0:0:format=auto[{out}]")
            else:
                return chaine
        return [f"[{out}]null"]

    # ---------------------------------------------------------------- calques generes
    def _calque_effet(self, e, c, ctx):
        if G.cv2 is None:
            self.journal.append(f"{e['id']} : OpenCV absent, effet ignoré")
            return
        d = ctx["duree"]
        dossier = tempfile.mkdtemp(prefix=e["id"] + "-", dir=self.tmp)
        p = dict(E.defauts(e["id"]))
        p.update(e.get("params") or {})
        i, L, H, cad = e["id"], self.L, self.H, self.cad
        x = y = 0
        if i == "feu_artifice" or i == "feu_artifice_derriere":
            motif, n = G.feu_artifice(dossier, L, H, cad, d, int(p.get("quantite", 6)))
        elif i == "eclairs":
            motif, n = G.eclairs(dossier, L, H, cad, d, int(p.get("quantite", 4)))
        elif i == "fuite_lumiere":
            motif, n = G.fuite_lumiere(dossier, L, H, cad, d, float(p.get("force", 0.6)))
        elif i == "pluie_code":
            motif, n = G.pluie_code(dossier, L, H, cad, d, float(p.get("densite", 1.0)), float(p.get("opacite", 0.7)))
        elif i == "halo":
            masques = self._masques(c)
            motif, n = G.halo(dossier, L, H, cad, d, masques, p.get("couleur", "#ffd36b"), float(p.get("force", 1.0)))
        elif i == "code_personne":
            d = min(d, float(p.get("duree", 2.0)) + 0.01) if p.get("duree") else d
            motif, n = G.code_personne(dossier, L, H, cad, d, self._masques(c))
        elif i == "bullet_time":
            return      # traite comme filtre de vitesse dans la chaine (voir effets.filtre) : rien a superposer
        else:
            self.journal.append(f"{i} : pas encore généré dans cette version")
            return
        self.calques.append((c["debut"], c["debut"] + d, motif, x, y, "screen" if i in ("feu_artifice", "eclairs", "halo") else "over"))

    def _calque_transition(self, tr, c, ctx):
        if G.cv2 is None:
            return
        p = dict(E.defauts(tr["id"]))
        p.update(tr.get("params") or {})
        d = min(float(p.get("duree", 1.0)), ctx["duree"])
        dossier = tempfile.mkdtemp(prefix=tr["id"] + "-", dir=self.tmp)
        L, H, cad = self.L, self.H, self.cad
        m = self.p.media(c["media"])
        i = tr["id"]
        if i == "t_puzzle":
            lecteur = G.lecteur_images(m["chemin"], c["src_debut"], L, H, cad)
            motif, n = G.puzzle(dossier, L, H, cad, d, lecteur, int(p.get("pieces", 4)))
            lecteur.fermer()
            mode = "over"
        elif i == "t_explosion":
            prec = [x for x in self.p.clips_piste("video") if fin_clip(x) <= c["debut"] + 0.02]
            if not prec:
                return
            pm = self.p.media(prec[-1]["media"])
            img = G.image_fixe(pm["chemin"], prec[-1]["src_fin"] - 0.05, L, H)
            motif, n = G.explosion(dossier, L, H, cad, d, img, int(p.get("pieces", 16)))
            mode = "over"
        elif i == "t_glitch":
            motif, n = G.glitch_transition(dossier, L, H, cad, d)
            mode = "over"
        elif i == "t_balayage":
            motif, n = G.balayage(dossier, L, H, cad, d)
            mode = "over"
        elif i == "t_code":
            motif, n = G.dissolution_code(dossier, L, H, cad, d)
            mode = "over"
        elif i == "t_zoom":
            return
        else:
            return
        self.calques.append((c["debut"], c["debut"] + d, motif, 0, 0, mode))

    def _masques(self, c):
        try:
            from . import segmentation
        except ImportError:
            return lambda i: None
        m = self.p.media(c["media"])
        return segmentation.masques(m["chemin"], c["src_debut"], self.L, self.H, self.cad, clip=c)

    def _masque_sequence(self, c):
        try:
            from . import segmentation
        except ImportError:
            return None
        m = self.p.media(c["media"])
        d = tempfile.mkdtemp(prefix="masque-", dir=self.tmp)
        return segmentation.sequence(m["chemin"], c["src_debut"], duree_clip(c), self.L, self.H, self.cad, d, clip=c)

    def _goodies(self):
        for g in self.p.goodies:
            if g["fin"] <= g["debut"] or g.get("genre") == "zone":
                continue
            dossier = tempfile.mkdtemp(prefix="goodie-", dir=self.tmp)
            ips = self.cad if g.get("genre") in GO.FLUIDES else min(self.cad, GO.IPS_GOODIES)
            motif, n, x, y = GO.rendre(dossier, g, self.L, self.H, ips, texte_extra=self.p.d.get("chaine"))
            if (g.get("suivi") or {}).get("positions"):          # Goodie accroché à une personne
                from . import suivi
                cote = max(48, int(self.H * float(g.get("taille", 0.22))))
                x, y = suivi.position_pixels(g, self.L, self.H, cote, cote)
            elif g.get("cles"):                                   # images clefs : il se déplace
                from . import cles as K
                cote = max(48, int(self.H * float(g.get("taille", 0.22))))
                x = f"'({K.expr(g, 'x')})*{self.L}-{cote}/2'"
                y = f"'({K.expr(g, 'y')})*{self.H}-{cote}/2'"
            self.calques.append((g["debut"], g["fin"], motif, x, y, "over", ips))

    def _incrustations(self, base):
        """Plans des pistes vidéo 2, 3… posés par-dessus la base : plein cadre (B-roll) ou réduits et placés
        (image dans l'image), avec leur opacité, entre leur début et leur fin."""
        for c in self.p.incrustations():
            m = self.p.media(c["media"])
            if not m or self.p.piste_masquee(c["piste"]):
                continue
            src = self._clip_video(c, None, 0.0)
            inc = c.get("incrust") or {}
            e = max(0.05, min(1.0, float(inc.get("echelle", 1.0))))
            op = max(0.0, min(1.0, float(inc.get("opacite", 1.0))))
            d, f = c["debut"], fin_clip(c)
            ov, out = self._nom("inc"), self._nom("vi")
            chaine = [f"[{src}]setpts=PTS+{d:.3f}/TB"]
            if c.get("cles"):               # images clefs : taille et opacité pilotées par sendcmd, position par expression
                from . import cles as K
                n_s, n_m = self._nom("ks"), self._nom("km")
                lignes = K.commandes_echelle_opacite(c, self.L, self.H, f"scale@{n_s}", f"colorchannelmixer@{n_m}", self.cad)
                fichier = os.path.join(self.tmp, f"cles_{n_s}.txt")
                with open(fichier, "w", encoding="utf-8") as fc:
                    fc.write("\n".join(lignes) + "\n")
                v0 = K.valeurs(c, 0.0)
                w0, h0 = max(2, int(self.L * v0["echelle"]) // 2 * 2), max(2, int(self.H * v0["echelle"]) // 2 * 2)
                chemin = fichier.replace("\\", "/").replace(":", "\\:")
                chaine += ["format=rgba", f"sendcmd=f='{chemin}'", f"scale@{n_s}=w={w0}:h={h0}",
                           f"colorchannelmixer@{n_m}=aa={max(0.0, min(1.0, v0['opacite'])):.3f}"]
                self.filtres.append(",".join(chaine) + f"[{ov}]")
                x = f"'(W-w)*({K.expr(c, 'x')})'"
                y = f"'(H-h)*({K.expr(c, 'y')})'"
                self.filtres.append(f"[{base}][{ov}]overlay=x={x}:y={y}:eval=frame:eof_action=pass:format=auto:enable='between(t,{d:.3f},{f:.3f})'[{out}]")
                base = out
                continue
            if e < 0.999:
                chaine.append(f"scale=trunc(iw*{e:.3f}/2)*2:trunc(ih*{e:.3f}/2)*2")
            if op < 0.999:
                chaine.append(f"format=rgba,colorchannelmixer=aa={op:.3f}")
            self.filtres.append(",".join(chaine) + f"[{ov}]")
            x = f"(W-w)*{float(inc.get('x', 0.5)):.3f}"
            y = f"(H-h)*{float(inc.get('y', 0.5)):.3f}"
            self.filtres.append(f"[{base}][{ov}]overlay={x}:{y}:eof_action=pass:format=auto:enable='between(t,{d:.3f},{f:.3f})'[{out}]")
            base = out
        return base

    def _zones(self, base):
        """Zones tracées (flou, mosaïque, cache…), fixes ou suivies, sous les textes et les Goodies."""
        from . import zones as Z
        for z in self.p.goodies:
            if z.get("genre") != "zone" or z["fin"] <= z["debut"]:
                continue
            lignes, base = Z.filtres(z, base, self.L, self.H, self._nom)
            self.filtres += lignes
        return base

    def _superposer(self, base):
        base = self._incrustations(base)
        base = self._zones(base)
        for calque in sorted(self.calques, key=lambda z: z[0]):
            d, f, motif, x, y, mode = calque[:6]
            ips = calque[6] if len(calque) > 6 else self.cad
            k = self._entree("-framerate", str(ips), "-i", motif)
            ov, out = self._nom("ov"), self._nom("vo")
            self.filtres.append(f"[{k}:v]format=rgba,setpts=PTS-STARTPTS+{d:.3f}/TB[{ov}]")
            if mode == "screen":
                self.filtres.append(f"[{base}][{ov}]overlay={x}:{y}:eof_action=pass:format=auto:enable='between(t,{d:.3f},{f:.3f})'[{out}]")
            else:
                self.filtres.append(f"[{base}][{ov}]overlay={x}:{y}:eof_action=pass:format=auto:enable='between(t,{d:.3f},{f:.3f})'[{out}]")
            base = out
        return base

    def _titres(self, base, sous_titres):
        radio = [tuple(x[:3]) for x in (self.p.d.get("sous_titres_radio") or [])]
        if not self.p.titres and not sous_titres and not radio:
            return base
        chemin = os.path.join(self.tmp, "titres.ass")
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(T.ass(self.p.titres, self.L, self.H, self.cad, sous_titres, radio))
        out = self._nom("vt")
        self.filtres.append(f"[{base}]{T.filtre_ass(chemin)}[{out}]")
        return out

    # ---------------------------------------------------------------- son
    def _son(self):
        def a_du_son(c):
            m = self.p.media(c["media"]) or {}
            return m.get("genre") != "image" and (m.get("fiche") or {}).get("audio") and not c.get("muet") and not self.p.piste_muette(c["piste"])
        if not any(a_du_son(c) for p_ in self.p.pistes_video() for c in self.p.clips_piste(p_)) and \
                not any(self.p.clips_piste(p_) for p_ in self.p.pistes_audio() if not self.p.piste_muette(p_)) and \
                not (self.p.clips_piste("voix") and not self.p.piste_muette("voix")):
            return self._silence(self.duree)     # rien à normaliser : loudnorm sur un silence pur donnerait des NaN
        pistes = []
        # son des plans video, bout a bout
        segs = []
        t = 0.0
        for c in self.p.clips_piste("video"):
            if c["debut"] > t + 0.02:
                segs.append(self._silence(c["debut"] - t))
            segs.append(self._audio_clip(c))
            t = fin_clip(c)
        if t < self.duree - 0.02:
            segs.append(self._silence(self.duree - t))
        if segs:
            if len(segs) == 1:
                pistes.append(segs[0])
            else:
                nom = self._nom("acat")
                self.filtres.append("".join(f"[{s}]" for s in segs) + f"concat=n={len(segs)}:v=0:a=1[{nom}]")
                pistes.append(nom)
        # voix off et doublage (piste « voix ») : mélangées au son des plans, elles font baisser la musique
        voix = []
        for c in [x for x in self.p.clips_piste("voix") if not self.p.piste_muette("voix")] + [x for x in self.p.incrustations() if a_du_son(x)]:
            m = self.p.media(c["media"])
            k = self._entree("-ss", f"{c['src_debut']:.3f}", "-t", f"{(c['src_fin'] - c['src_debut']):.3f}", "-i", m["chemin"])
            nom = self._nom("vo")
            fx = "".join("," + f for f in (filtre_audio(e) for e in (c.get("effets_audio") or [])) if f)
            fv = fondus_audio(c, duree_clip(c), 0.0, 0.0) if c["piste"] == "voix" else ""
            self.filtres.append(f"[{k}:a]asetpts=PTS-STARTPTS{self._atempo(c)}{fx},volume={0.0 if c.get('muet') else c.get('volume', 1.0):.3f}{fv},"
                                f"aresample=48000,aformat=channel_layouts=stereo,adelay={int(c['debut'] * 1000)}|{int(c['debut'] * 1000)}[{nom}]")
            voix.append(nom)
        if voix:
            base = pistes[:1]
            nom = self._nom("voixmix")
            self.filtres.append("".join(f"[{x}]" for x in base + voix) + f"amix=inputs={len(base + voix)}:duration=longest:normalize=0[{nom}]")
            pistes = [nom]
        # musiques : piste audio, decalees a leur position
        for c in [x for p_ in self.p.pistes_audio() if not self.p.piste_muette(p_) for x in self.p.clips_piste(p_)]:
            m = self.p.media(c["media"])
            d = duree_clip(c)
            k = self._entree("-ss", f"{c['src_debut']:.3f}", "-t", f"{(c['src_fin'] - c['src_debut']):.3f}", "-i", m["chemin"])
            nom = self._nom("mus")
            fondu = fondus_audio(c, d)
            self.filtres.append(f"[{k}:a]asetpts=PTS-STARTPTS{self._atempo(c)},volume={0.0 if c.get('muet') else c.get('volume', 1.0):.3f}"
                                f"{fondu},aresample=48000,aformat=channel_layouts=stereo,adelay={int(c['debut'] * 1000)}|{int(c['debut'] * 1000)}[{nom}]")
            pistes.append(nom)
        if not pistes:
            return self._silence(self.duree)
        if len(pistes) == 1:
            mix = pistes[0]
        else:
            mix = self._nom("amix")
            ducking = self.p.d.get("ducking", True) and len(pistes) >= 2
            if ducking:
                # la voix (piste 1 = plans) baisse les musiques : compresseur a chaine laterale
                voix, musiques = pistes[0], pistes[1:]
                if len(musiques) > 1:
                    mm = self._nom("mm")
                    self.filtres.append("".join(f"[{s}]" for s in musiques) + f"amix=inputs={len(musiques)}:duration=longest:normalize=0[{mm}]")
                else:
                    mm = musiques[0]
                v1, v2 = self._nom("vx"), self._nom("vx")
                duck = self._nom("duck")
                self.filtres.append(f"[{voix}]asplit[{v1}][{v2}]")
                self.filtres.append(f"[{mm}][{v2}]sidechaincompress=threshold=0.02:ratio=6:attack=80:release=600[{duck}]")
                self.filtres.append(f"[{v1}][{duck}]amix=inputs=2:duration=longest:normalize=0[{mix}]")
            else:
                self.filtres.append("".join(f"[{s}]" for s in pistes) + f"amix=inputs={len(pistes)}:duration=longest:normalize=0[{mix}]")
        out = self._nom("aout")
        lufs = LUFS.get(self.dest, -14)
        # format de sortie explicite : FFmpeg 4.x ne sait pas toujours le deviner (piste entièrement silencieuse)
        self.filtres.append(f"[{mix}]loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[{out}]")
        return out

    def _atempo(self, c):
        v = float(c.get("vitesse", 1.0))
        if abs(v - 1.0) < 1e-3:
            return ""
        parts = []
        while v > 2.0:
            parts.append("atempo=2.0")
            v /= 2.0
        while v < 0.5:
            parts.append("atempo=0.5")
            v *= 2.0
        parts.append(f"atempo={v:.4f}")
        return "," + ",".join(parts)

    def _audio_clip(self, c):
        m = self.p.media(c["media"])
        d = duree_clip(c)
        fiche = m.get("fiche") or {}
        if m["genre"] == "image" or not fiche.get("audio") or c.get("muet") or self.p.piste_muette(c["piste"]):
            return self._silence(d)
        k = self._entree("-ss", f"{c['src_debut']:.3f}", "-t", f"{(c['src_fin'] - c['src_debut']):.3f}", "-i", m["chemin"])
        nom = self._nom("a")
        fx = "".join("," + f for f in (filtre_audio(e) for e in (c.get("effets_audio") or [])) if f)
        self.filtres.append(f"[{k}:a]asetpts=PTS-STARTPTS{self._atempo(c)}{fx},volume={c.get('volume', 1.0):.3f},"
                            f"aresample=48000,aformat=channel_layouts=stereo,atrim=duration={d:.3f},apad=whole_dur={d:.3f}[{nom}]")
        return nom

    def _silence(self, d):
        k = self._entree("-f", "lavfi", "-t", f"{max(0.02, d):.3f}", "-i", "anullsrc=r=48000:cl=stereo")
        nom = self._nom("sil")
        self.filtres.append(f"[{k}:a]asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[{nom}]")
        return nom

    # ---------------------------------------------------------------- commande complete
    def commande(self, sous_titres=()):
        v = self._segments_video()
        self._goodies()
        v = self._superposer(v)
        v = self._titres(v, sous_titres)
        a = None if self.sans_son else self._son()
        script = os.path.join(self.tmp, "filtres.txt")
        with open(script, "w", encoding="utf-8") as f:
            f.write(";\n".join(self.filtres))
        args = []
        for e in self.entrees:
            args += e
        args += moteur.args_script_filtres(script) + ["-map", f"[{v}]"] + (["-map", f"[{a}]"] if a else ["-an"])
        args += moteur.args_encodeur(self.enc, self.qualite)
        args += ["-r", str(self.cad), "-c:a", "aac", "-b:a", self.debit_audio, "-ar", "48000", "-movflags", "+faststart",
                 "-t", f"{self.duree:.3f}", self.sortie]
        return args

    def lancer(self, progression=None, arret=lambda: False, sous_titres=()):
        args = self.commande(sous_titres)
        try:
            moteur.lancer(args, progression=progression, duree=self.duree, arret=arret)
        except moteur.ErreurMoteur as e:
            if self.enc != "libx264":           # encodeur materiel capricieux : on retombe sur le processeur
                self.journal.append(f"{moteur.nom_encodeur(self.enc)} a échoué, nouvel essai avec x264 : {e}")
                self.enc = "libx264"
                self.entrees, self.filtres, self._n = [], [], 0
                args = self.commande(sous_titres)
                moteur.lancer(args, progression=progression, duree=self.duree, arret=arret)
            else:
                raise
        self.vignette = None
        if self.p.d.get("vignette_t") is not None:
            try:
                self.vignette = poser_vignette(self.sortie, float(self.p.d["vignette_t"]))
            except Exception as e:      # noqa: BLE001 : la vidéo est faite, la vignette est un plus
                self.journal.append(f"Vignette non posée : {e}")
        return self.sortie

    def nettoyer(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def poser_vignette(video, t):
    """Image du film choisie comme vignette du fichier : intégrée au MP4 (explorateur de fichiers, lecteurs) et
    enregistrée à côté en JPG (à envoyer comme miniature sur YouTube). Renvoie le chemin du JPG."""
    base, ext = os.path.splitext(video)
    jpg = base + "_vignette.jpg"
    moteur.lancer(["-y", "-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1", "-q:v", "2", jpg])
    if ext.lower() in (".mp4", ".mov", ".m4v"):
        tmp = base + "_avec_vignette" + ext
        moteur.lancer(["-y", "-i", video, "-i", jpg, "-map", "0", "-map", "1", "-c", "copy", "-c:v:1", "mjpeg",
                       "-disposition:v:1", "attached_pic", "-movflags", "+faststart", tmp])
        os.replace(tmp, video)
    return jpg


def autre_format(projet, destination):
    """Copie du projet prête pour une autre destination (double export 16:9 + 9:16) : un plan qui suit une personne la
    suit aussi dans l'autre format ; un plan « remplir » dont l'orientation ne colle pas passe en fond flou (rien de
    coupé : la personne n'est jamais hors cadre)."""
    import copy
    from . import moteur as M
    p = copy.deepcopy(projet)
    _n, L, H = M.DESTINATIONS.get(destination, ("", 1920, 1080))[:3]
    if not L or not H:
        return p
    cible_vert = H > L
    for c in p.clips_piste("video"):
        if c.get("ajustement", "remplir") != "remplir":
            continue
        v = ((p.media(c["media"]) or {}).get("fiche") or {}).get("video") or {}
        lw, lh = v.get("largeur") or L, v.get("hauteur") or H
        if (lh > lw) != cible_vert:
            c["ajustement"] = "contenir_flou"
    return p


def nom_autre(sortie, destination):
    from . import moteur as M
    _n, L, H = M.DESTINATIONS.get(destination, ("", 1920, 1080))[:3]
    base, ext = os.path.splitext(sortie)
    return f"{base}_{'vertical' if H > L else 'carre' if H == L else 'horizontal'}{ext or '.mp4'}"


def extrait(projet, debut, fin):
    """Copie du projet réduite au passage [debut, fin], ramené à 0 (aperçu rendu, aperçu d'un effet)."""
    import copy
    p = copy.deepcopy(projet)
    for piste in sorted(set(p.toutes_pistes()) | {c["piste"] for c in p.clips}):
        for c in list(p.clips_piste(piste)):
            if fin_clip(c) <= debut or c["debut"] >= fin:
                p.d["clips"].remove(c)
                continue
            if c["debut"] < debut:
                from .projet import decaler_effets
                delta = debut - c["debut"]
                c["_avance"] = float(c.get("_avance") or 0.0) + delta
                c["src_debut"] += delta * c.get("vitesse", 1.0)
                c["debut"] = debut
                c["transition"] = None
                decaler_effets(c, delta, duree_clip(c))
                if c.get("cles"):
                    from . import cles as K
                    K.decaler(c, delta, duree_clip(c))
            if fin_clip(c) > fin:
                c["src_fin"] = c["src_debut"] + (fin - c["debut"]) * c.get("vitesse", 1.0)
            c["debut"] -= debut
    from .projet import decaler_suivi
    for g in p.goodies:                      # Goodies : leurs valeurs et leur déroulé suivent le décalage du temps
        o = (g.get("options") or {}).get("_origine") or (g["debut"], g["fin"])
        g.setdefault("options", {})["_origine"] = (o[0] - debut, o[1] - debut)
        g["valeurs"] = [(round(t - debut, 3), v) for t, v in (g.get("valeurs") or [])]
        if g["options"].get("roulis_valeurs"):
            g["options"]["roulis_valeurs"] = [(round(t - debut, 3), v) for t, v in g["options"]["roulis_valeurs"]]
    for x in p.titres + p.goodies:
        if x.get("cles") and x["debut"] < debut < x["fin"]:
            from . import cles as K
            K.decaler(x, debut - x["debut"], x["fin"] - debut)
        x["debut"], x["fin"] = max(0.0, x["debut"] - debut), max(0.0, min(fin, x["fin"]) - debut)
        decaler_suivi(x, lambda t: t - debut)
    p.d["titres"] = [t for t in p.titres if t["fin"] > 0.05]
    p.d["goodies"] = [g for g in p.goodies if g["fin"] > 0.05]
    p.d["sous_titres"] = []
    p.d["sous_titres_radio"] = [(max(0.0, a - debut), min(fin, b) - debut, t) for a, b, t, *_r in (p.d.get("sous_titres_radio") or [])
                                if b > debut and a < fin]
    return p


def image_rendue(projet, t, sortie_png, params=None, largeur=960, sous_titres=()):
    """L'image du montage à l'instant t, avec tout : cadrage, effets, transitions, textes, Goodies, sous-titres.
    C'est ce que montre l'aperçu à l'arrêt (0.3.0) : on voit ce qu'on crée sans passer par un export."""
    from . import effets as E
    pas = 1.0 / max(1.0, float(projet.cadence or 30))
    # on part un peu avant t : les fondus des textes et la transition en cours ont ainsi vraiment commencé
    marge = 3.0
    c = projet.clip_a(t, "video")
    tr = E.transition_active(c) if c else None
    if tr:
        marge = max(marge, float((tr.get("params") or {}).get("duree", 0.8) or 0.8) + 0.5)
    t0 = max(0.0, t - marge)
    p = extrait(projet, t0, t + 3 * pas)
    st = [(a - t0, b - t0) + tuple(x[2:]) for x in sous_titres for a, b in [(x[0], x[1])] if a <= t + pas and b >= t0]
    ex = Exportateur(p, sortie_png, "whatsapp", qualite="allegee", encodeur="libx264", params=params)     # 720p : deux fois plus vite
    ex.sans_son = True
    try:
        args = ex.commande(st)
        i = args.index("-c:v")
        args = args[:i] + ["-ss", f"{t - t0:.3f}", "-frames:v", "1", "-s", f"{int(largeur)}x{int(round(largeur * ex.H / ex.L / 2) * 2)}",
                           "-f", "image2", "-vcodec", "png", "-update", "1", sortie_png]
        moteur.lancer(args)
        return sortie_png
    finally:
        ex.nettoyer()


def fondus_audio(c, d, entree=0.8, sortie=1.2):
    """Fondus d'entrée et de sortie d'un plan de son (réglables dans l'Inspecteur ; 0 = aucun)."""
    if not c.get("fondus", True) and "fondu_entree" not in c and "fondu_sortie" not in c:
        return ""
    fe = max(0.0, min(d / 2, float(c.get("fondu_entree", entree))))
    fs = max(0.0, min(d / 2, float(c.get("fondu_sortie", sortie))))
    out = ""
    if fe > 0.01:
        out += f",afade=t=in:st=0:d={fe:.3f}"
    if fs > 0.01:
        out += f",afade=t=out:st={max(0.0, d - fs):.3f}:d={fs:.3f}"
    return out


def apercu_effet(projet, clip_id, effets, transition, t, sortie, params=None, arret=lambda: False):
    """Petit film de 2 à 3 s montrant le plan avec ces effets (ou cette transition), pour juger avant de poser."""
    p = extrait(projet, 0, projet.duree())
    c = p.clip(clip_id)
    if not c:
        raise ValueError("plan introuvable")
    c["effets"] = [dict(e) for e in effets]
    c["transition"] = dict(transition) if transition else None
    if transition:
        d = float((transition.get("params") or {}).get("duree", 1.0))
        a, b = max(0.0, c["debut"] - d - 0.5), min(fin_clip(c), c["debut"] + d + 1.0)
    else:
        a = min(max(c["debut"], t - 0.3), max(c["debut"], fin_clip(c) - 2.5))
        b = min(fin_clip(c), a + 2.5)
    p = extrait(p, a, b)
    p.d["musique"] = None
    ex = Exportateur(p, sortie, "whatsapp", qualite="allegee", encodeur="libx264", params=params)
    try:
        return ex.lancer(arret=arret)
    finally:
        ex.nettoyer()


def exporter(projet, sortie, destination="youtube", params=None, progression=None, arret=lambda: False, sous_titres=(), garder_tmp=False):
    ex = Exportateur(projet, sortie, destination, params=params)
    try:
        return ex.lancer(progression, arret, sous_titres), ex.journal
    finally:
        if not garder_tmp:
            ex.nettoyer()
