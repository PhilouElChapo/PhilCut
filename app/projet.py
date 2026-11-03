"""Le projet PhilCut : medias importes, bande video, bande son, titres, Goodies, recette.

Un projet est un fichier .philcut (JSON lisible) qui ne contient que des EMPLACEMENTS : les rushes restent la ou
ils sont (local, NAS, Drive). Il se synchronise entre postes comme la session de PhilPDF ; les chemins y sont
notes avec l'empreinte du fichier pour le retrouver s'il a bouge.

Temps : tout est en secondes (float). Un clip pose sur la timeline a une position `debut` et joue la portion
[src_debut, src_fin] de son media a la vitesse `vitesse` ; sa duree affichee vaut (src_fin - src_debut) / vitesse.
"""
import copy, json, os, time, uuid

from .config import EXTENSION_PROJET, est_video, est_audio, est_image

VERSION_FORMAT = 1
FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}


def _id():
    return uuid.uuid4().hex[:10]


class Projet:
    def __init__(self, nom="Sans titre", format_="16:9"):
        self.chemin = None
        self.d = {"version": VERSION_FORMAT, "nom": nom, "format": format_, "cadence": 30, "cree": time.strftime("%Y-%m-%dT%H:%M:%S"),
                  "medias": [], "clips": [], "titres": [], "goodies": [], "recette": None, "notes": "", "chaine": ""}
        self._pile = []           # annuler
        self._refaire = []
        self.modifie = False

    # ---------------------------------------------------------------- acces
    @property
    def nom(self):
        return self.d["nom"]

    @nom.setter
    def nom(self, v):
        self.d["nom"] = v

    @property
    def format(self):
        return self.d["format"]

    @property
    def taille(self):
        return FORMATS.get(self.d["format"], FORMATS["16:9"])

    @property
    def cadence(self):
        return self.d.get("cadence") or 30

    @property
    def medias(self):
        return self.d["medias"]

    @property
    def clips(self):
        return self.d["clips"]

    @property
    def titres(self):
        return self.d["titres"]

    @property
    def goodies(self):
        return self.d["goodies"]

    def media(self, ident):
        for m in self.medias:
            if m["id"] == ident:
                return m
        return None

    def clip(self, ident):
        for c in self.clips:
            if c["id"] == ident:
                return c
        return None

    def clips_piste(self, piste):
        return sorted((c for c in self.clips if c["piste"] == piste), key=lambda c: c["debut"])

    def duree(self):
        fins = [fin_clip(c) for c in self.clips] + [t.get("fin", 0) for t in self.titres] + [g.get("fin", 0) for g in self.goodies]
        return max(fins) if fins else 0.0

    # ---------------------------------------------------------------- annuler / refaire
    def marquer(self):
        """A appeler AVANT une modification : garde l'etat pour Annuler (50 niveaux)."""
        self._pile.append(copy.deepcopy(self.d))
        del self._pile[:-50]
        self._refaire.clear()
        self.modifie = True

    def annuler(self):
        if not self._pile:
            return False
        self._refaire.append(copy.deepcopy(self.d))
        self.d = self._pile.pop()
        self.modifie = True
        return True

    def refaire(self):
        if not self._refaire:
            return False
        self._pile.append(copy.deepcopy(self.d))
        self.d = self._refaire.pop()
        self.modifie = True
        return True

    # ---------------------------------------------------------------- medias
    def ajouter_media(self, chemin, fiche=None):
        for m in self.medias:
            if os.path.normcase(os.path.abspath(m["chemin"])) == os.path.normcase(os.path.abspath(chemin)):
                return m
        genre = "video" if est_video(chemin) else "audio" if est_audio(chemin) else "image" if est_image(chemin) else "autre"
        m = {"id": _id(), "chemin": chemin, "nom": os.path.basename(chemin), "genre": genre, "fiche": fiche or {},
             "empreinte": _empreinte(chemin), "proxy": "", "etiquettes": []}
        self.medias.append(m)
        return m

    def retirer_media(self, ident):
        self.d["medias"] = [m for m in self.medias if m["id"] != ident]
        self.d["clips"] = [c for c in self.clips if c["media"] != ident]

    # ---------------------------------------------------------------- clips
    def ajouter_clip(self, media_id, piste=None, debut=None, src_debut=0.0, src_fin=None, vitesse=1.0):
        m = self.media(media_id)
        if not m:
            raise KeyError(media_id)
        piste = piste or ("audio" if m["genre"] == "audio" else "video")
        duree_media = float((m.get("fiche") or {}).get("duree") or 0) or (5.0 if m["genre"] == "image" else 0.0)
        if src_fin is None:
            src_fin = duree_media
        if debut is None:
            debut = self.fin_piste(piste)
        c = {"id": _id(), "media": media_id, "piste": piste, "debut": float(debut), "src_debut": float(src_debut),
             "src_fin": float(src_fin), "vitesse": float(vitesse), "volume": 1.0, "muet": False, "effets": [],
             "transition": None, "ajustement": "remplir", "nom": m["nom"]}
        self.clips.append(c)
        return c

    def fin_piste(self, piste):
        cs = self.clips_piste(piste)
        return fin_clip(cs[-1]) if cs else 0.0

    def retirer_clip(self, ident, refermer=True):
        c = self.clip(ident)
        if not c:
            return
        self.d["clips"] = [x for x in self.clips if x["id"] != ident]
        if refermer:
            d = duree_clip(c)
            for x in self.clips:
                if x["piste"] == c["piste"] and x["debut"] > c["debut"]:
                    x["debut"] = max(0.0, x["debut"] - d)

    def couper(self, ident, t):
        """Coupe le clip a l'instant t de la timeline : deux clips, le second commence a t."""
        c = self.clip(ident)
        if not c or not (c["debut"] + 0.04 < t < fin_clip(c) - 0.04):
            return None
        dans_src = c["src_debut"] + (t - c["debut"]) * c["vitesse"]
        droite = copy.deepcopy(c)
        droite["id"] = _id()
        droite["debut"] = t
        droite["src_debut"] = dans_src
        droite["transition"] = None
        c["src_fin"] = dans_src
        i = self.clips.index(c)
        self.clips.insert(i + 1, droite)
        return droite

    def couper_a(self, t, piste="video"):
        """Coupe le clip de la piste qui contient t."""
        for c in self.clips_piste(piste):
            if c["debut"] < t < fin_clip(c):
                return self.couper(c["id"], t)
        return None

    def deplacer(self, ident, debut):
        c = self.clip(ident)
        if c:
            c["debut"] = max(0.0, float(debut))
            self.ranger(c["piste"])

    def ranger(self, piste):
        """Interdit les chevauchements sur une piste : les clips se poussent dans l'ordre de leur debut."""
        t = 0.0
        for c in self.clips_piste(piste):
            if c["debut"] < t:
                c["debut"] = t
            t = fin_clip(c)

    def resserrer(self, piste):
        """Supprime les trous : chaque clip colle au precedent."""
        t = 0.0
        for c in self.clips_piste(piste):
            c["debut"] = t
            t = fin_clip(c)

    def rogner(self, ident, src_debut=None, src_fin=None):
        c = self.clip(ident)
        if not c:
            return
        if src_debut is not None:
            c["src_debut"] = max(0.0, min(float(src_debut), c["src_fin"] - 0.04))
        if src_fin is not None:
            c["src_fin"] = max(c["src_debut"] + 0.04, float(src_fin))

    def vitesse(self, ident, v):
        c = self.clip(ident)
        if c:
            c["vitesse"] = max(0.1, min(16.0, float(v)))
            self.ranger(c["piste"])

    def clip_a(self, t, piste="video"):
        for c in self.clips_piste(piste):
            if c["debut"] <= t < fin_clip(c):
                return c
        return None

    # ---------------------------------------------------------------- titres et goodies
    def ajouter_titre(self, texte, debut, fin, style="simple", **extra):
        t = {"id": _id(), "texte": texte, "debut": float(debut), "fin": float(fin), "style": style, "x": 0.5, "y": 0.85,
             "taille": 1.0, "couleur": "#ffffff", "police": "", "animation": "fondu", "suivi": None}
        t.update(extra)
        self.titres.append(t)
        return t

    def ajouter_goodie(self, genre, debut, fin, **extra):
        g = {"id": _id(), "genre": genre, "debut": float(debut), "fin": float(fin), "x": 0.88, "y": 0.85, "taille": 0.22,
             "style": "cadran", "valeurs": [], "options": {}}
        g.update(extra)
        self.goodies.append(g)
        return g

    def retirer_element(self, ident):
        self.d["titres"] = [t for t in self.titres if t["id"] != ident]
        self.d["goodies"] = [g for g in self.goodies if g["id"] != ident]

    # ---------------------------------------------------------------- fichier
    def enregistrer(self, chemin=None):
        chemin = chemin or self.chemin
        if not chemin:
            raise ValueError("chemin")
        if not chemin.lower().endswith(EXTENSION_PROJET):
            chemin += EXTENSION_PROJET
        self.d["modifie"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        base = os.path.dirname(os.path.abspath(chemin))
        d = copy.deepcopy(self.d)
        for m in d["medias"]:                      # chemin relatif en plus, pour un dossier deplace d'un bloc
            try:
                m["relatif"] = os.path.relpath(m["chemin"], base)
            except ValueError:
                m["relatif"] = ""
            m.pop("proxy", None)
        tmp = chemin + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, chemin)
        self.chemin = chemin
        self.modifie = False
        return chemin

    @classmethod
    def ouvrir(cls, chemin):
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("version", 0) > VERSION_FORMAT:
            raise ValueError("Ce projet vient d'une version plus récente de PhilCut.")
        p = cls()
        p.d.update(d)
        p.chemin = chemin
        base = os.path.dirname(os.path.abspath(chemin))
        for m in p.medias:                         # retrouver les rushes qui ont bouge
            m.setdefault("proxy", "")
            if not os.path.exists(m["chemin"]):
                for cand in (os.path.join(base, m.get("relatif") or ""), os.path.join(base, m["nom"])):
                    if cand and os.path.isfile(cand) and (not m.get("empreinte") or _empreinte(cand) == m["empreinte"]):
                        m["chemin"] = cand
                        break
        return p

    def manquants(self):
        return [m for m in self.medias if not os.path.exists(m["chemin"])]


# ------------------------------------------------------------------ fonctions sur les clips
def duree_clip(c):
    return max(0.0, (c["src_fin"] - c["src_debut"]) / (c.get("vitesse") or 1.0))


def fin_clip(c):
    return c["debut"] + duree_clip(c)


def _empreinte(chemin):
    """Taille + debut + fin du fichier : reconnait un rush renomme sans le lire en entier."""
    import hashlib
    try:
        t = os.path.getsize(chemin)
        h = hashlib.sha1(str(t).encode())
        with open(chemin, "rb") as f:
            h.update(f.read(65536))
            if t > 131072:
                f.seek(-65536, 2)
                h.update(f.read(65536))
        return h.hexdigest()[:24]
    except OSError:
        return ""
