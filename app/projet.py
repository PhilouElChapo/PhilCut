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

    def __deepcopy__(self, memo):
        """Une copie pour un export ou un rendu n'emporte pas la pile d'Annuler (jusqu'à 50 états du projet)."""
        q = Projet.__new__(Projet)
        q.chemin = self.chemin
        q.d = copy.deepcopy(self.d, memo)
        q._pile, q._refaire = [], []
        q.modifie = self.modifie
        return q

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

    # ---------------------------------------------------------------- pistes
    # « video » est la piste de base ; « video2 », « video3 » s'incrustent par-dessus (B-roll, image dans l'image).
    # « audio » = Musique ; « audio2 »… d'autres musiques ou sons ; « voix » = voix off et doublage.
    def pistes_video(self):
        n = max(1, int(self.d.get("nb_video") or 1))
        return ["video"] + [f"video{i}" for i in range(2, n + 1)]

    def pistes_audio(self):
        n = max(1, int(self.d.get("nb_audio") or 1))
        return ["audio"] + [f"audio{i}" for i in range(2, n + 1)]

    def toutes_pistes(self):
        return self.pistes_video() + self.pistes_audio() + ["voix"]

    def incrustations(self):
        """Plans des pistes vidéo au-dessus de la base, dans l'ordre d'empilement (video2 sous video3)."""
        return [c for p in self.pistes_video()[1:] for c in self.clips_piste(p)]

    def ajouter_piste(self, genre):
        cle = "nb_video" if genre == "video" else "nb_audio"
        self.d[cle] = min(4, max(1, int(self.d.get(cle) or 1)) + 1)
        self.modifie = True
        return (self.pistes_video() if genre == "video" else self.pistes_audio())[-1]

    def retirer_piste(self, piste):
        """Retire la dernière piste vidéo ou audio ajoutée, si elle est vide. Renvoie True si fait."""
        for genre, cle in (("video", "nb_video"), ("audio", "nb_audio")):
            pistes = self.pistes_video() if genre == "video" else self.pistes_audio()
            if piste == pistes[-1] and len(pistes) > 1 and not self.clips_piste(piste):
                self.d[cle] = len(pistes) - 1
                self.modifie = True
                return True
        return False

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

    def historique(self):
        """(à annuler, à rétablir) : libellés des actions, la plus récente d'abord."""
        etats = self._pile + [self.d]
        annul = [decrire(etats[i], etats[i + 1]) for i in range(len(etats) - 1)][::-1]
        suite = [self.d] + self._refaire[::-1]
        retab = [decrire(suite[i], suite[i + 1]) for i in range(len(suite) - 1)]
        return annul, retab

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

    def partie(self, a, b, garder):
        """Sélection [a, b] de la timeline. garder=True : on ne garde qu'elle (elle passe au début) ;
        garder=False : on la supprime et la suite se recolle. Toutes les pistes, textes et Goodies compris."""
        a, b = sorted((max(0.0, a), max(0.0, b)))
        if b - a < 0.04:
            return False
        for piste in self.toutes_pistes():
            for t in (a, b):
                for c in list(self.clips_piste(piste)):
                    if c["debut"] + 0.04 < t < fin_clip(c) - 0.04:
                        self.couper(c["id"], t)
        largeur = b - a

        def dedans(d, f):
            return d >= a - 0.02 and f <= b + 0.02
        clips = []
        for c in self.clips:
            d, f = c["debut"], fin_clip(c)
            if garder:
                if dedans(d, f):
                    c["debut"] = d - a
                    clips.append(c)
            else:
                if dedans(d, f):
                    continue
                if d >= b - 0.02:
                    c["debut"] = d - largeur
                clips.append(c)
        self.d["clips"] = clips
        for cle in ("titres", "goodies"):
            out = []
            for e in self.d.get(cle) or []:
                d, f = e["debut"], e["fin"]
                if garder:
                    d, f = max(d, a) - a, min(f, b) - a
                else:
                    if d >= a and f <= b:
                        continue
                    d = d if d < a else (a if d < b else d - largeur)
                    f = f if f <= a else (a if f <= b else f - largeur)
                if f - d > 0.05:
                    e["debut"], e["fin"] = d, f
                    out.append(e)
            self.d[cle] = out
        st = []
        for x in self.d.get("sous_titres") or []:
            d, f = x[0], x[1]
            if garder and d >= a and f <= b + 0.02:
                st.append([d - a, f - a] + list(x[2:]))
            elif not garder and (f <= a or d >= b):
                st.append([d - (largeur if d >= b else 0), f - (largeur if d >= b else 0)] + list(x[2:]))
        self.d["sous_titres"] = st
        self.modifie = True
        return True

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


def _nom(x):
    return x.get("nom") or x.get("texte", "")[:30] or x.get("genre") or "?"


def decrire(avant, apres):
    """Ce qui a changé entre deux états du projet, en quelques mots (liste d'Annuler / Rétablir)."""
    from .langue import _
    for cle, quoi in (("clips", _("plan")), ("titres", _("texte")), ("goodies", _("Goodie"))):
        a = {x["id"]: x for x in avant.get(cle) or []}
        b = {x["id"]: x for x in apres.get(cle) or []}
        ajoutes = [b[i] for i in b if i not in a]
        retires = [a[i] for i in a if i not in b]
        if cle == "clips" and len(ajoutes) == 1 and not retires and any(
                a[i].get("media") == ajoutes[0].get("media") and abs(a[i].get("src_fin", 0) - b[i].get("src_fin", 0)) > 1e-3 for i in a if i in b):
            return _("Coupe de « {n} »", n=_nom(ajoutes[0]))
        if ajoutes and not retires:
            return _("Ajout ({q}) « {n} »", q=quoi, n=_nom(ajoutes[0])) if len(ajoutes) == 1 else _("Ajout de {k} éléments", k=len(ajoutes))
        if retires and not ajoutes:
            return _("Suppression de « {n} »", n=_nom(retires[0])) if len(retires) == 1 else _("Suppression de {k} éléments", k=len(retires))
        if ajoutes or retires:
            return _("Montage refait ({k} éléments)", k=len(ajoutes) + len(retires))
        for i in a:
            if a[i] != b[i]:
                diff = {k for k in set(a[i]) | set(b[i]) if a[i].get(k) != b[i].get(k)}
                n = _nom(b[i])
                for cles, lib in ((("effets", "transition"), _("Effets de « {n} »")), (("effets_audio",), _("Retouche de la voix de « {n} »")),
                                  (("vitesse",), _("Vitesse de « {n} »")), (("volume", "muet"), _("Son de « {n} »")),
                                  (("ajustement", "cadrage", "suivi"), _("Cadrage de « {n} »")), (("src_debut", "src_fin"), _("Longueur de « {n} »")),
                                  (("debut", "fin", "piste"), _("Déplacement de « {n} »")), (("texte", "animation", "couleur", "taille", "police", "effet_texte"), _("Texte « {n} »"))):
                    if diff & set(cles):
                        return lib.format(n=n) if "{n}" in lib else lib
                return _("Réglage de « {n} »", n=n)
    if (avant.get("sous_titres") or []) != (apres.get("sous_titres") or []):
        return _("Sous-titres")
    am = {m["id"] for m in avant.get("medias") or []}
    nouveaux = [m for m in apres.get("medias") or [] if m["id"] not in am]
    if nouveaux:
        return _("Import de « {n} »", n=nouveaux[0].get("nom", ""))
    if len(apres.get("medias") or []) < len(avant.get("medias") or []):
        return _("Retrait d'un média")
    return _("Modification du projet")
