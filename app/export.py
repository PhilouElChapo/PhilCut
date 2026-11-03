"""Export : traduit le projet en une commande FFmpeg (filtres), puis encode avec le meilleur encodeur du poste.

Etapes : bande video (plans, vitesse, cadrage, effets, transitions) -> calques generes (feu d'artifice, puzzle,
Goodies...) -> titres (ASS) -> son (plans, musiques, normalisation YouTube -14 LUFS) -> fichier final.
Tout est ecrit dans un dossier temporaire ; progression et arret possibles.
"""
import os, shutil, tempfile

from . import effets as E, generateurs as G, goodies as GO, moteur, titres as T
from .projet import duree_clip, fin_clip

# effets audio d'un plan (menu Voix et son)
FILTRES_AUDIO = {
    "a_debruit": "afftdn=nf=-25:tn=1,highpass=f=80",
    "a_voix": "highpass=f=90,lowpass=f=12000,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3000:t=q:w=1:g=2,acompressor=threshold=-18dB:ratio=3:attack=10:release=120:makeup=4,alimiter=limit=0.95",
    "a_autotune": "acompressor=threshold=-16dB:ratio=4,chorus=0.6:0.9:50|60:0.4|0.32:0.25|0.4:2|1.3",      # approximation en attendant un vrai correcteur de justesse
    "a_reverb": "aecho=0.8:0.9:40|60|90:0.35|0.25|0.15",
    "a_echo": "aecho=0.8:0.88:320:0.4",
}

LUFS = {"youtube": -14, "youtube4k": -14, "insta": -14, "insta_carre": -14, "whatsapp": -16, "ecran_led": -14, "original": -14}


class Exportateur:
    def __init__(self, projet, sortie, destination="youtube", qualite=None, encodeur=None, params=None, dossier_tmp=None):
        self.p = projet
        self.sortie = sortie
        self.dest = destination
        self.params = params or {}
        d = moteur.destination(destination)
        self.L, self.H = (d[1], d[2]) if d[1] else projet.taille
        if destination == "original":
            self.L, self.H = projet.taille
        self.cad = d[3] or projet.cadence
        self.qualite = qualite or d[4]
        self.debit_audio = d[5]
        self.enc = encodeur or (self.params.get("encodeur") or moteur.encodeurs()[0])
        self.tmp = dossier_tmp or tempfile.mkdtemp(prefix="philcut-export-")
        self.entrees = []           # ["-i", chemin] groupes
        self.filtres = []
        self._n = 0
        self.journal = []

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
        if mode == "contenir_flou":
            return (f"split[cf_a][cf_b];[cf_b]scale={L}:{H}:force_original_aspect_ratio=increase,crop={L}:{H},gblur=sigma=30,eq=brightness=-0.08[cf_fond];"
                    f"[cf_a]scale={L}:{H}:force_original_aspect_ratio=decrease[cf_dev];[cf_fond][cf_dev]overlay=(W-w)/2:(H-h)/2")
        return f"scale={L}:{H}:force_original_aspect_ratio=increase,crop={L}:{H}"

    # ---------------------------------------------------------------- bande video
    def _segments_video(self):
        clips = self.p.clips_piste("video")
        segs = []
        t = 0.0
        self.calques = []           # (debut, fin, entree, x, y)
        for i, c in enumerate(clips):
            if c["debut"] > t + 0.02:           # trou : noir
                segs.append(self._noir(c["debut"] - t))
            segs.append(self._clip_video(c, clips[i + 1] if i + 1 < len(clips) else None))
            t = fin_clip(c)
        duree_titres = max([x.get("fin", 0) for x in self.p.titres + self.p.goodies] + [0])
        if duree_titres > t + 0.02:
            segs.append(self._noir(duree_titres - t))
            t = duree_titres
        self.duree = t
        if not segs:
            segs.append(self._noir(1.0))
            self.duree = 1.0
        if len(segs) == 1:
            return segs[0]
        nom = self._nom("vcat")
        self.filtres.append("".join(f"[{s}]" for s in segs) + f"concat=n={len(segs)}:v=1:a=0[{nom}]")
        return nom

    def _noir(self, duree):
        k = self._entree("-f", "lavfi", "-t", f"{duree:.3f}", "-i", f"color=c=black:s={self.L}x{self.H}:r={self.cad}")
        nom = self._nom("noir")
        self.filtres.append(f"[{k}:v]format=yuv420p[{nom}]")
        return nom

    def _clip_video(self, c, suivant):
        m = self.p.media(c["media"])
        fiche = m.get("fiche") or {}
        v = fiche.get("video") or {}
        d = duree_clip(c)
        if m["genre"] == "image":
            k = self._entree("-loop", "1", "-framerate", str(self.cad), "-t", f"{d:.3f}", "-i", m["chemin"])
            chaine = [f"[{k}:v]format=yuv420p,setpts=PTS-STARTPTS"]
        else:
            k = self._entree("-ss", f"{c['src_debut']:.3f}", "-t", f"{(c['src_fin'] - c['src_debut']):.3f}", "-i", m["chemin"])
            chaine = [f"[{k}:v]setpts=(PTS-STARTPTS)/{c.get('vitesse', 1.0):.4f}"]
            if v.get("hdr"):
                chaine.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
        chaine.append(f"fps={self.cad}")
        chaine.append(self._cadrage(c, m))
        chaine.append("format=yuv420p")
        ctx = {"cadence": self.cad, "largeur": self.L, "hauteur": self.H, "duree": d, "debut": c["debut"]}
        for e in c.get("effets") or []:
            f = E.filtre(e, ctx) or E.filtre_en_ligne(e["id"])
            if f:
                chaine.append(f)
            elif e["id"] in E.GENERES:
                self._calque_effet(e, c, ctx)
            if e["id"] in ("double_exposition", "chroma_key", "detourage"):
                chaine = self._avec_second_media(chaine, e, c, d)
        # transition du clip suivant : sortie de celui-ci
        if suivant and suivant.get("transition"):
            fs = E.filtre_sortie_transition(suivant["transition"])
            if fs:
                chaine.append(fs.replace("{fin}", f"{d:.3f}"))
        if c.get("transition"):
            f = E.filtre(c["transition"], ctx)
            if f:
                chaine.append(f)
            else:
                self._calque_transition(c["transition"], c, ctx)
        chaine.append(f"trim=duration={d:.3f},setpts=PTS-STARTPTS")
        nom = self._nom("v")
        self.filtres.append(",".join(chaine) + f"[{nom}]")
        return nom

    def _avec_second_media(self, chaine, e, c, d):
        """Double exposition / fond vert / detourage : second media mis au format et combine."""
        ident = (e.get("params") or {}).get("media")
        m2 = self.p.media(ident) if ident else None
        if not m2:
            return chaine
        if m2["genre"] == "image":
            k = self._entree("-loop", "1", "-framerate", str(self.cad), "-t", f"{d:.3f}", "-i", m2["chemin"])
        else:
            k = self._entree("-stream_loop", "-1", "-t", f"{d:.3f}", "-i", m2["chemin"])
        a, b = self._nom("prim"), self._nom("sec")
        self.filtres.append(",".join(chaine) + f"[{a}]")
        self.filtres.append(f"[{k}:v]fps={self.cad},scale={self.L}:{self.H}:force_original_aspect_ratio=increase,crop={self.L}:{self.H},format=yuv420p,trim=duration={d:.3f},setpts=PTS-STARTPTS[{b}]")
        out = self._nom("mix")
        if e["id"] == "double_exposition":
            op = float((e.get("params") or {}).get("opacite", 0.5))
            self.filtres.append(f"[{a}][{b}]blend=all_mode=screen:all_opacity={op:.2f}[{out}]")
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
        return segmentation.masques(m["chemin"], c["src_debut"], self.L, self.H, self.cad)

    def _masque_sequence(self, c):
        try:
            from . import segmentation
        except ImportError:
            return None
        m = self.p.media(c["media"])
        d = tempfile.mkdtemp(prefix="masque-", dir=self.tmp)
        return segmentation.sequence(m["chemin"], c["src_debut"], duree_clip(c), self.L, self.H, self.cad, d)

    def _goodies(self):
        for g in self.p.goodies:
            if g["fin"] <= g["debut"]:
                continue
            dossier = tempfile.mkdtemp(prefix="goodie-", dir=self.tmp)
            motif, n, x, y = GO.rendre(dossier, g, self.L, self.H, self.cad, texte_extra=self.p.d.get("chaine"))
            if (g.get("suivi") or {}).get("positions"):          # Goodie accroché à une personne
                from . import suivi
                cote = max(48, int(self.H * float(g.get("taille", 0.22))))
                x, y = suivi.position_pixels(g, self.L, self.H, cote, cote)
            self.calques.append((g["debut"], g["fin"], motif, x, y, "over"))

    def _superposer(self, base):
        for (d, f, motif, x, y, mode) in sorted(self.calques, key=lambda z: z[0]):
            k = self._entree("-framerate", str(self.cad), "-i", motif)
            ov, out = self._nom("ov"), self._nom("vo")
            self.filtres.append(f"[{k}:v]format=rgba,setpts=PTS-STARTPTS+{d:.3f}/TB[{ov}]")
            if mode == "screen":
                self.filtres.append(f"[{base}][{ov}]overlay={x}:{y}:eof_action=pass:format=auto:enable='between(t,{d:.3f},{f:.3f})'[{out}]")
            else:
                self.filtres.append(f"[{base}][{ov}]overlay={x}:{y}:eof_action=pass:format=auto:enable='between(t,{d:.3f},{f:.3f})'[{out}]")
            base = out
        return base

    def _titres(self, base, sous_titres):
        if not self.p.titres and not sous_titres:
            return base
        chemin = os.path.join(self.tmp, "titres.ass")
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(T.ass(self.p.titres, self.L, self.H, self.cad, sous_titres))
        out = self._nom("vt")
        self.filtres.append(f"[{base}]{T.filtre_ass(chemin)}[{out}]")
        return out

    # ---------------------------------------------------------------- son
    def _son(self):
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
        # musiques et voix off : piste audio, decalees a leur position
        for c in self.p.clips_piste("audio"):
            m = self.p.media(c["media"])
            d = duree_clip(c)
            k = self._entree("-ss", f"{c['src_debut']:.3f}", "-t", f"{(c['src_fin'] - c['src_debut']):.3f}", "-i", m["chemin"])
            nom = self._nom("mus")
            fondu = f",afade=t=in:st=0:d=0.8,afade=t=out:st={max(0, d - 1.2):.3f}:d=1.2" if c.get("fondus", True) else ""
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
        self.filtres.append(f"[{mix}]loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[{out}]")
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
        if m["genre"] == "image" or not fiche.get("audio") or c.get("muet"):
            return self._silence(d)
        k = self._entree("-ss", f"{c['src_debut']:.3f}", "-t", f"{(c['src_fin'] - c['src_debut']):.3f}", "-i", m["chemin"])
        nom = self._nom("a")
        fx = "".join("," + f for f in (FILTRES_AUDIO.get(e) for e in (c.get("effets_audio") or [])) if f)
        self.filtres.append(f"[{k}:a]asetpts=PTS-STARTPTS{self._atempo(c)}{fx},volume={c.get('volume', 1.0):.3f},"
                            f"aresample=48000,aformat=channel_layouts=stereo,atrim=duration={d:.3f},apad=whole_dur={d:.3f}[{nom}]")
        return nom

    def _silence(self, d):
        k = self._entree("-f", "lavfi", "-t", f"{max(0.02, d):.3f}", "-i", "anullsrc=r=48000:cl=stereo")
        nom = self._nom("sil")
        self.filtres.append(f"[{k}:a]asetpts=PTS-STARTPTS[{nom}]")
        return nom

    # ---------------------------------------------------------------- commande complete
    def commande(self, sous_titres=()):
        v = self._segments_video()
        self._goodies()
        v = self._superposer(v)
        v = self._titres(v, sous_titres)
        a = self._son()
        script = os.path.join(self.tmp, "filtres.txt")
        with open(script, "w", encoding="utf-8") as f:
            f.write(";\n".join(self.filtres))
        args = []
        for e in self.entrees:
            args += e
        args += moteur.args_script_filtres(script) + ["-map", f"[{v}]", "-map", f"[{a}]"]
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
        return self.sortie

    def nettoyer(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def exporter(projet, sortie, destination="youtube", params=None, progression=None, arret=lambda: False, sous_titres=(), garder_tmp=False):
    ex = Exportateur(projet, sortie, destination, params=params)
    try:
        return ex.lancer(progression, arret, sous_titres), ex.journal
    finally:
        if not garder_tmp:
            ex.nettoyer()
