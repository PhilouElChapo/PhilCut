"""IA locale 100 % portable : moteurs et modèles rangés dans le dossier de données de PhilCut, rien d'installé.

- Moteurs : llama.cpp (llama-server, vision) et whisper.cpp (whisper-cli, voix), versions officielles reprises par
  la fabrication GitHub de PhilCut (release « moteurs-ia »). Le détourage passe par onnxruntime, embarqué dans PhilCut.
- Modèles : téléchargés chez leurs auteurs quand on coche la case, avec la taille affichée avant ; vérifiés par
  empreinte quand elle est connue ; reprise d'un téléchargement interrompu.
- Lancement : seulement à la demande, en priorité basse, avec un nombre de cœurs limité en mode « poste léger » ;
  arrêt à la fin du travail. Rien ne démarre avec le système, rien ne va dans le registre.
- Supprimer le dossier de PhilCut (ou décocher) efface tout.
"""
import base64, hashlib, json, os, shutil, socket, subprocess, sys, tarfile, tempfile, threading, time, urllib.error, urllib.request, zipfile

from .config import dossier_donnees
from .langue import _

MANIFESTE_URL = "https://github.com/PhilouElChapo/PhilCut/releases/download/moteurs-ia/moteurs-ia.json"
GENRES = {"vision": _("Vision (idées de montage)"), "whisper": _("Voix (sous-titres automatiques)"), "detourage": _("Détourage de personne"),
          "voix": _("Voix de synthèse (voix off, doublage)")}
DEFAUT = {"vision": "vision_leger", "whisper": "whisper_leger", "detourage": "detourage_leger", "voix": "voix_fr_femme"}
MOTEURS_GENRE = ("vision", "whisper", "voix")          # genres qui ont un programme à télécharger
UA = {"User-Agent": "PhilCut"}


class ErreurIA(Exception):
    pass


# ------------------------------------------------------------------ emplacements
def dossier():
    d = os.path.abspath(os.environ.get("PHILCUT_IA_DOSSIER") or os.path.join(dossier_donnees(), "ia"))
    os.makedirs(d, exist_ok=True)
    return d


def systeme():
    return "windows" if sys.platform == "win32" else "linux"


def _exe(nom):
    return nom + (".exe" if sys.platform == "win32" else "")


def dossier_moteur(genre):
    return os.path.join(dossier(), "moteurs", genre)


def executable(genre):
    return os.path.join(dossier_moteur(genre), _exe({"vision": "llama-server", "vision_gpu": "llama-server", "whisper": "whisper-cli",
                                                     "voix": "piper"}[genre]))


# ------------------------------------------------------------------ carte graphique (Vulkan)
_carte = None


def carte_graphique():
    """Nom de la carte graphique dédiée (Nvidia, AMD, Intel Arc) si ce poste en a une, sinon ""."""
    global _carte
    if _carte is None:
        try:
            from .ia_locale import materiel
            m = materiel()
            nom = m.get("gpu") or ""
            dediee = m.get("nvidia") or any(x in nom.lower() for x in ("nvidia", "geforce", "rtx", "quadro", "radeon rx", "radeon pro", "arc a", "arc b"))
            _carte = nom if dediee else ""
        except Exception:       # noqa: BLE001
            _carte = ""
    return _carte


_peripherique = None


def peripherique_vulkan():
    """(identifiant, nom) de la carte dédiée vue par le moteur Vulkan, par exemple ("Vulkan1", "NVIDIA GeForce RTX 3070
    Laptop GPU"). Sur un portable à deux cartes (Intel intégrée + Nvidia), c'est la Nvidia qui est choisie."""
    global _peripherique
    if _peripherique is not None:
        return _peripherique or None
    _peripherique = ()
    if not moteur_installe("vision_gpu"):
        return None
    try:
        r = subprocess.run([executable("vision_gpu"), "--list-devices"], cwd=dossier_moteur("vision_gpu"), env=_env("vision_gpu"),
                           capture_output=True, text=True, errors="replace", timeout=60, **{k: v for k, v in _options_processus().items() if k != "preexec_fn"})
        vus = []
        for ligne in (r.stdout + "\n" + r.stderr).splitlines():
            ligne = ligne.strip()
            if ligne.startswith("Vulkan") and ":" in ligne:
                ident, nom = ligne.split(":", 1)
                vus.append((ident.strip(), nom.strip()))
        dedies = [v for v in vus if any(x in v[1].lower() for x in ("nvidia", "geforce", "rtx", "quadro", "radeon", "arc"))
                  and "integrated" not in v[1].lower() and "uhd" not in v[1].lower()]
        _peripherique = (dedies or vus or [()])[0]
    except Exception:       # noqa: BLE001
        _peripherique = ()
    return _peripherique or None


def gpu_voulu(params=None):
    """La version carte graphique du moteur de vision est utilisée si le poste a une carte dédiée et si l'utilisateur
    ne l'a pas désactivée (Préférences › IA locale)."""
    if (params or {}).get("ia_gpu", True) is False:
        return False
    return bool(carte_graphique()) and bool(moteur_info("vision_gpu"))


def dossier_modele(cle):
    return os.path.join(dossier(), "modeles", cle)


# ------------------------------------------------------------------ catalogue
_manifeste = None


def manifeste(rafraichir=False, delai=8):
    """Catalogue des moteurs et modèles. Copie locale gardée un jour ; hors ligne, la dernière copie sert."""
    global _manifeste
    if _manifeste is not None and not rafraichir:
        return _manifeste
    local = os.environ.get("PHILCUT_IA_MANIFESTE")
    if local:
        with open(local, encoding="utf-8") as f:
            _manifeste = json.load(f)
        return _manifeste
    copie = os.path.join(dossier(), "moteurs-ia.json")
    vieux = not os.path.exists(copie) or time.time() - os.path.getmtime(copie) > 86400
    if rafraichir or vieux:
        try:
            req = urllib.request.Request(MANIFESTE_URL, headers=UA)
            with urllib.request.urlopen(req, timeout=delai) as r:
                donnees = r.read()
            json.loads(donnees.decode("utf-8"))
            with open(copie + ".tmp", "wb") as f:
                f.write(donnees)
            os.replace(copie + ".tmp", copie)
        except Exception as e:          # noqa: BLE001 : hors ligne, on garde la copie
            if not os.path.exists(copie):
                raise ErreurIA(_("Catalogue de l'IA locale injoignable : {e}", e=e)) from e
    with open(copie, encoding="utf-8") as f:
        _manifeste = json.load(f)
    return _manifeste


def modeles(genre=None, avec_essai=False):
    try:
        m = manifeste().get("modeles", {})
    except ErreurIA:
        return {}
    return {k: v for k, v in m.items() if (genre is None or v.get("genre") == genre) and (avec_essai or not v.get("essai"))}


def moteur_info(genre):
    return (manifeste().get("moteurs", {}).get(genre) or {}).get(systeme())


# ------------------------------------------------------------------ état local
def _etat_chemin():
    return os.path.join(dossier(), "installe.json")


def etat():
    try:
        with open(_etat_chemin(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:       # noqa: BLE001
        return {}


def _noter(cle, valeur):
    e = etat()
    if valeur is None:
        e.pop(cle, None)
    else:
        e[cle] = valeur
    with open(_etat_chemin() + ".tmp", "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=1)
    os.replace(_etat_chemin() + ".tmp", _etat_chemin())


def moteur_installe(genre):
    if genre == "detourage":
        return onnx_present()
    return f"moteur_{genre}" in etat() and os.path.exists(executable(genre))


def installe(cle):
    e = etat().get(cle)
    if not e:
        return False
    return all(os.path.exists(os.path.join(dossier_modele(cle), f)) for f in e.get("fichiers", []))


def installes(genre=None):
    out = []
    for cle, e in etat().items():
        if cle.startswith("moteur_") or not installe(cle):
            continue
        if genre is None or e.get("genre") == genre:
            out.append(cle)
    return out


def modele_actif(genre, params=None):
    """Modèle choisi pour ce genre : celui des préférences s'il est là, sinon le premier installé."""
    choix = ((params or {}).get("ia_locale_modeles") or {}).get(genre)
    if choix and installe(choix):
        return choix
    ins = [c for c in installes(genre) if not c.endswith("_test")] or installes(genre)
    return ins[0] if ins else None


def taille_dossier(chemin=None):
    chemin = chemin or dossier()
    total = 0
    for racine, _d, fichiers in os.walk(chemin):
        for f in fichiers:
            try:
                total += os.path.getsize(os.path.join(racine, f))
            except OSError:
                pass
    return total


def taille_texte(octets):
    if octets >= 1e9:
        return f"{octets / 1e9:.1f} Go".replace(".", ",")
    return f"{max(1, round(octets / 1e6))} Mo"


def a_telecharger(cle):
    """Octets à télécharger pour installer ce modèle (moteur compris s'il manque)."""
    m = modeles(avec_essai=True).get(cle) or {}
    total = 0 if installe(cle) else m.get("taille", 0)
    g = m.get("genre")
    if g in MOTEURS_GENRE and not moteur_installe(g):
        total += (moteur_info(g) or {}).get("taille", 0)
    if g == "vision" and gpu_voulu() and not moteur_installe("vision_gpu"):
        total += (moteur_info("vision_gpu") or {}).get("taille", 0)
    return total


def octets_partiels(cle):
    """Octets déjà téléchargés (fichiers .part) pour ce modèle et son moteur : la reprise repartira de là."""
    g = (modeles(avec_essai=True).get(cle) or {}).get("genre")
    total = 0
    for base, _d, fichiers in os.walk(dossier_modele(cle)):
        total += sum(os.path.getsize(os.path.join(base, f)) for f in fichiers if f.endswith(".part"))
    if g in MOTEURS_GENRE and not moteur_installe(g):
        info = moteur_info(g) or {}
        p = os.path.join(dossier(), "tmp", (info.get("fichier") or "?") + ".part")
        if os.path.exists(p):
            total += os.path.getsize(p)
    return total


# ------------------------------------------------------------------ téléchargement
def _telecharger(url, cible, taille=0, sha256="", progression=None, arret=lambda: False):
    """Téléchargement avec reprise (.part), contrôle de taille et d'empreinte."""
    os.makedirs(os.path.dirname(cible), exist_ok=True)
    part = cible + ".part"
    deja = os.path.getsize(part) if os.path.exists(part) else 0
    if taille and deja > taille:
        os.remove(part)
        deja = 0
    if url.startswith("file://") or os.path.exists(url):
        src = url[7:] if url.startswith("file://") else url
        shutil.copyfile(src, part)
    elif not (taille and deja == taille):
        entetes = dict(UA)
        if deja:
            entetes["Range"] = f"bytes={deja}-"
        req = urllib.request.Request(url, headers=entetes)
        with urllib.request.urlopen(req, timeout=60) as r:
            if deja and r.status != 206:
                deja = 0
            total = taille or (deja + int(r.headers.get("Content-Length") or 0))
            with open(part, "ab" if deja else "wb") as f:
                fait = deja
                while True:
                    if arret():
                        raise InterruptedError()
                    bloc = r.read(1 << 20)
                    if not bloc:
                        break
                    f.write(bloc)
                    fait += len(bloc)
                    if progression and total:
                        progression(fait / total)
    if taille and os.path.getsize(part) != taille:
        raise ErreurIA(_("Téléchargement incomplet ({a} sur {b}) : relancez, il reprendra où il s'est arrêté.",
                         a=taille_texte(os.path.getsize(part)), b=taille_texte(taille)))
    if sha256 and len(sha256) == 64:
        if empreinte(part) != sha256.lower():
            os.remove(part)
            raise ErreurIA(_("Fichier abîmé (empreinte différente) : supprimé, relancez le téléchargement."))
    os.replace(part, cible)
    return cible


def empreinte(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def installer_moteur(genre, progression=None, arret=lambda: False):
    if genre == "detourage" or moteur_installe(genre):
        return True
    info = moteur_info(genre)
    if not info:
        raise ErreurIA(_("Pas de moteur « {g} » pour ce système dans le catalogue.", g=genre))
    tmp = os.path.join(dossier(), "tmp")
    archive = os.path.join(tmp, info["fichier"])
    source = os.environ.get("PHILCUT_IA_ARCHIVES")
    url = os.path.join(source, info["fichier"]) if source else info["url"]
    _telecharger(url, archive, info.get("taille", 0), info.get("sha256", ""), progression, arret)
    cible = dossier_moteur(genre)
    shutil.rmtree(cible, ignore_errors=True)
    os.makedirs(cible, exist_ok=True)
    extraire(archive, cible)
    os.remove(archive)
    if not os.path.exists(executable(genre)):
        raise ErreurIA(_("Archive du moteur « {g} » incomplète.", g=genre))
    if sys.platform != "win32":
        for f in os.listdir(cible):
            p = os.path.join(cible, f)
            if os.path.isfile(p) and not os.path.islink(p):
                os.chmod(p, 0o755)
    _noter(f"moteur_{genre}", {"genre": genre, "version": manifeste().get("moteurs", {}).get(genre, {}).get("version", ""), "date": time.strftime("%Y-%m-%d")})
    return True


def extraire(archive, cible):
    """Extrait à plat (un éventuel dossier racine unique est retiré), sans sortir de la cible."""
    racine_cible = os.path.realpath(cible)

    def sur(nom):
        p = os.path.realpath(os.path.join(cible, nom))
        if not (p == racine_cible or p.startswith(racine_cible + os.sep)):
            raise ErreurIA(_("Archive refusée (chemin suspect) : {n}", n=nom))
        return p
    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            noms = [n for n in z.namelist() if not n.endswith("/")]
            prefixe = _prefixe_commun(noms)
            for n in noms:
                dest = sur(n[len(prefixe):])
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with z.open(n) as s, open(dest, "wb") as d:
                    shutil.copyfileobj(s, d)
    else:
        with tarfile.open(archive) as t:
            membres = [m for m in t.getmembers() if m.isfile() or m.issym()]
            prefixe = _prefixe_commun([m.name for m in membres])
            for m in membres:
                dest = sur(m.name[len(prefixe):])
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                if m.issym():
                    if os.path.isabs(m.linkname) or ".." in m.linkname.split("/"):
                        continue
                    if os.path.lexists(dest):
                        os.remove(dest)
                    os.symlink(m.linkname, dest)
                else:
                    with t.extractfile(m) as s, open(dest, "wb") as d:
                        shutil.copyfileobj(s, d)


def _prefixe_commun(noms):
    tetes = {n.split("/", 1)[0] for n in noms}
    if len(tetes) == 1 and all("/" in n for n in noms):
        return tetes.pop() + "/"
    return ""


def installer(cle, progression=None, arret=lambda: False):
    """Installe un modèle (et son moteur s'il manque). progression(fraction, texte)."""
    m = modeles(avec_essai=True).get(cle)
    if not m:
        raise ErreurIA(_("Modèle inconnu : {c}", c=cle))
    g = m["genre"]
    if g == "detourage" and not onnx_present():
        raise ErreurIA(_("Le détourage demande onnxruntime, présent dans PhilCut à partir de la version 0.2."))
    total = max(1, a_telecharger(cle))
    fait = [0]

    def prog_part(taille, texte):
        def p(f):
            progression and progression(min(0.99, (fait[0] + f * taille) / total), texte)
        return p
    if g in MOTEURS_GENRE and not moteur_installe(g):
        t = (moteur_info(g) or {}).get("taille", 0)
        installer_moteur(g, prog_part(t, _("moteur {g}", g=g)), arret)
        fait[0] += t
    if g == "vision" and gpu_voulu() and not moteur_installe("vision_gpu"):
        t = (moteur_info("vision_gpu") or {}).get("taille", 0)
        try:        # facultatif : sans lui, le processeur prend le relais
            installer_moteur("vision_gpu", prog_part(t, _("moteur carte graphique")), arret)
        except InterruptedError:
            raise
        except Exception as e:      # noqa: BLE001
            from .journal import ecrire
            ecrire("ia locale", f"moteur carte graphique non installé : {e}")
        fait[0] += t
    noms = []
    for f in m["fichiers"]:
        cible = os.path.join(dossier_modele(cle), f["nom"])
        if not os.path.exists(cible):
            _telecharger(f["url"], cible, f.get("taille", 0), f.get("sha256", ""), prog_part(f.get("taille", 0), m["nom"]), arret)
        fait[0] += f.get("taille", 0)
        noms.append(f["nom"])
    _noter(cle, {"genre": g, "nom": m["nom"], "fichiers": noms, "roles": {f["role"]: f["nom"] for f in m["fichiers"]},
                 "taille": m.get("taille", 0), "date": time.strftime("%Y-%m-%d")})
    progression and progression(1.0, m["nom"])
    return True


def supprimer(cle):
    """Retire un modèle ; quand plus aucun modèle d'un genre ne reste, son moteur part aussi."""
    e = etat().get(cle) or {}
    shutil.rmtree(dossier_modele(cle), ignore_errors=True)
    _noter(cle, None)
    g = e.get("genre")
    if g in MOTEURS_GENRE and not installes(g):
        for m in ((g, "vision_gpu") if g == "vision" else (g,)):
            shutil.rmtree(dossier_moteur(m), ignore_errors=True)
            _noter(f"moteur_{m}", None)
    shutil.rmtree(os.path.join(dossier(), "tmp"), ignore_errors=True)


# ------------------------------------------------------------------ ménagement du poste
def coeurs(params=None):
    n = os.cpu_count() or 2
    if (params or {}).get("ia_poste_leger", True):
        return max(1, n // 2)
    return max(1, n - 1)


def _options_processus():
    """Priorité basse, pas de fenêtre de console."""
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {"startupinfo": si, "creationflags": 0x08000000 | 0x00004000}     # CREATE_NO_WINDOW | BELOW_NORMAL
    return {"preexec_fn": lambda: os.nice(10)}


def _env(genre):
    env = dict(os.environ)
    d = dossier_moteur(genre)
    cle = "PATH" if sys.platform == "win32" else "LD_LIBRARY_PATH"
    env[cle] = d + (os.pathsep + env[cle] if env.get(cle) else "")
    return env


def _port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ------------------------------------------------------------------ vision (llama-server)
class ServeurVision:
    """Lance llama-server pour la durée d'un travail, puis l'arrête :

        with ServeurVision("vision_leger", params) as s:
            texte = s.generer("Décris", [png])
    """

    def __init__(self, cle=None, params=None, contexte=8192):
        self.params = params or {}
        self.cle = cle or modele_actif("vision", self.params)
        if not self.cle or not installe(self.cle):
            raise ErreurIA(_("Aucun modèle de vision installé sur ce poste (Préférences › IA locale)."))
        if not moteur_installe("vision"):
            raise ErreurIA(_("Moteur de vision absent : décochez puis recochez le modèle dans Préférences › IA locale."))
        self.contexte = contexte
        self.mode = ""          # "gpu" (carte graphique, Vulkan) ou "cpu"
        self.peripherique = None
        self.proc = None
        self.port = None
        self.journal = os.path.join(dossier(), "journal_vision.txt")

    def __enter__(self):
        self.demarrer()
        return self

    def __exit__(self, *exc):
        self.arreter()

    def demarrer(self, delai=300):
        """Carte graphique d'abord si elle est là ; au moindre souci, le processeur prend le relais."""
        if self.params.get("ia_gpu", True) is not False and moteur_installe("vision_gpu") and carte_graphique():
            try:
                self._demarrer("vision_gpu", delai)
                self.mode = "gpu"
                return
            except ErreurIA as e:
                from .journal import ecrire
                ecrire("ia locale", f"carte graphique indisponible, passage au processeur : {e}")
                self.arreter()
        self._demarrer("vision", delai)
        self.mode = "cpu"

    def _demarrer(self, moteur, delai):
        roles = etat()[self.cle]["roles"]
        d = dossier_modele(self.cle)
        self.port = _port_libre()
        cmd = [executable(moteur), "-m", os.path.join(d, roles["modele"]), "--mmproj", os.path.join(d, roles["mmproj"]),
               "--host", "127.0.0.1", "--port", str(self.port), "-t", str(coeurs(self.params)), "-c", str(self.contexte), "-np", "1",
               "-ngl", "99" if moteur == "vision_gpu" else "0"]
        if moteur == "vision_gpu":
            self.peripherique = peripherique_vulkan()
            if self.peripherique:            # portables à deux cartes : la carte dédiée, jamais la puce Intel intégrée
                cmd += ["--device", self.peripherique[0]]
        self._log = open(self.journal, "w", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(cmd, cwd=dossier_moteur(moteur), env=_env(moteur), stdout=self._log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, **_options_processus())
        debut = time.time()
        while time.time() - debut < delai:
            if self.proc.poll() is not None:
                raise ErreurIA(_("Le moteur de vision s'est arrêté au démarrage : {t}", t=self._fin_journal()))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=3) as r:
                    if r.status == 200:
                        return
            except Exception:       # noqa: BLE001 : modèle en cours de chargement
                pass
            time.sleep(0.5)
        self.arreter()
        raise ErreurIA(_("Le moteur de vision met trop de temps à démarrer."))

    def _fin_journal(self):
        try:
            self._log.flush()
            with open(self.journal, encoding="utf-8", errors="replace") as f:
                return f.read()[-400:]
        except OSError:
            return ""

    def generer(self, consigne, images=(), systeme="", json_attendu=False, delai=900, max_jetons=2000):
        contenu = [{"type": "text", "text": consigne}]
        for img in images:
            mime = "image/png" if img[:4] == b"\x89PNG" else "image/jpeg"
            contenu.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64," + base64.b64encode(img).decode()}})
        messages = ([{"role": "system", "content": systeme}] if systeme else []) + [{"role": "user", "content": contenu}]
        corps = {"messages": messages, "temperature": 0.4, "max_tokens": max_jetons, "stream": False}
        if json_attendu:
            corps["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/chat/completions", data=json.dumps(corps).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=delai) as r:
                d = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise ErreurIA(_("Le moteur de vision a refusé : {e}", e=e.read().decode("utf-8", "replace")[:300])) from e
        return d["choices"][0]["message"]["content"] or ""

    def arreter(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(5)
        self.proc = None
        try:
            self._log.close()
        except Exception:       # noqa: BLE001
            pass


def generer_vision(consigne, images=(), systeme="", json_attendu=False, params=None, cle=None, delai=900):
    """Un travail complet : démarrer, demander, arrêter."""
    with ServeurVision(cle, params) as s:
        return s.generer(consigne, images, systeme, json_attendu, delai)


# ------------------------------------------------------------------ voix (whisper-cli)
def transcrire(wav, cle=None, langue="fr", params=None, progression=None, arret=lambda: False, mots=False):
    """Transcription d'un WAV 16 kHz mono : [(debut_s, fin_s, texte)] ; avec mots=True :
    [(debut_s, fin_s, texte, [(debut_s, fin_s, mot), ...])] (karaoké, doublage)."""
    cle = cle or modele_actif("whisper", params)
    if not cle or not installe(cle):
        raise ErreurIA(_("Aucun modèle de voix installé sur ce poste (Préférences › IA locale)."))
    if not moteur_installe("whisper"):
        raise ErreurIA(_("Moteur de voix absent : décochez puis recochez le modèle dans Préférences › IA locale."))
    modele = os.path.join(dossier_modele(cle), etat()[cle]["roles"]["modele"])
    racine_tmp = os.path.join(dossier(), "tmp")
    os.makedirs(racine_tmp, exist_ok=True)
    tmp = tempfile.mkdtemp(dir=racine_tmp)
    base = os.path.join(tmp, "transcription")
    cmd = [executable("whisper"), "-m", modele, "-f", wav, "-l", langue or "auto", "-t", str(coeurs(params)), "-ojf" if mots else "-oj", "-of", base, "-pp"]
    proc = subprocess.Popen(cmd, cwd=dossier_moteur("whisper"), env=_env("whisper"), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL, text=True, errors="replace", **_options_processus())
    fin = []

    def lire():
        for ligne in proc.stderr:
            fin.append(ligne)
            del fin[:-20]
            if "progress" in ligne and "%" in ligne and progression:
                try:
                    progression(int(ligne.rsplit("=", 1)[-1].strip().rstrip("%")) / 100)
                except ValueError:
                    pass
    t = threading.Thread(target=lire, daemon=True)
    t.start()
    try:
        while proc.poll() is None:
            if arret():
                proc.kill()
                raise InterruptedError()
            time.sleep(0.3)
        t.join(5)
        if proc.returncode != 0 or not os.path.exists(base + ".json"):
            raise ErreurIA(_("La transcription a échoué : {t}", t="".join(fin)[-400:]))
        with open(base + ".json", encoding="utf-8", errors="replace") as f:
            d = json.load(f)
        out = []
        for s in d.get("transcription", []):
            o = s.get("offsets") or {}
            texte = (s.get("text") or "").strip()
            if texte and not (texte.startswith("[") and texte.endswith("]")):
                seg = (o.get("from", 0) / 1000.0, o.get("to", 0) / 1000.0, texte)
                out.append(seg + (mots_segment(s.get("tokens") or [], seg),) if mots else seg)
        return out
    finally:
        try:
            proc.stderr.close()
        except Exception:       # noqa: BLE001
            pass
        shutil.rmtree(tmp, ignore_errors=True)


def mots_segment(jetons, seg):
    """Regroupe les jetons de whisper.cpp (morceaux de mots, l'espace en tête marque un nouveau mot) en mots datés."""
    out = []
    for j in jetons:
        t = j.get("text") or ""
        if not t.strip() or (t.strip().startswith("[_") and t.strip().endswith("]")) or t.strip().startswith("<|"):
            continue
        o = j.get("offsets") or {}
        a, b = o.get("from", 0) / 1000.0, o.get("to", 0) / 1000.0
        if out and not t.startswith(" "):           # suite du mot précédent (ou ponctuation collée)
            out[-1] = (out[-1][0], max(out[-1][1], b), out[-1][2] + t)
        else:
            out.append((a, b, t.strip()))
    if not out:     # pas de jetons : mots répartis à parts égales
        m = seg[2].split()
        pas = (seg[1] - seg[0]) / max(1, len(m))
        out = [(seg[0] + i * pas, seg[0] + (i + 1) * pas, w) for i, w in enumerate(m)]
    return out


# ------------------------------------------------------------------ voix de synthèse (Piper)
def synthese(texte, sortie_wav, cle=None, params=None, vitesse=1.0):
    """Lit le texte avec une voix locale (Piper) ; écrit un WAV. vitesse > 1 : plus rapide."""
    cle = cle or modele_actif("voix", params)
    if not cle or not installe(cle):
        raise ErreurIA(_("Aucune voix de synthèse installée sur ce poste (Préférences › IA locale)."))
    if not moteur_installe("voix"):
        raise ErreurIA(_("Moteur de voix absent : décochez puis recochez la voix dans Préférences › IA locale."))
    roles = etat()[cle]["roles"]
    modele = os.path.join(dossier_modele(cle), roles["modele"])
    cmd = [executable("voix"), "--model", modele, "--output_file", sortie_wav, "--length_scale", f"{1.0 / max(0.5, min(2.0, vitesse)):.3f}"]
    if roles.get("config"):
        cmd += ["--config", os.path.join(dossier_modele(cle), roles["config"])]
    r = subprocess.run(cmd, input=texte.encode("utf-8"), cwd=dossier_moteur("voix"), env=_env("voix"), capture_output=True, timeout=600,
                       **{k: v for k, v in _options_processus().items() if k != "preexec_fn"})
    if r.returncode != 0 or not os.path.exists(sortie_wav):
        raise ErreurIA(_("La voix de synthèse a échoué : {t}", t=r.stderr.decode("utf-8", "replace")[-300:]))
    return sortie_wav


# ------------------------------------------------------------------ détourage (onnxruntime)
_sessions = {}


def onnx_present():
    try:
        import onnxruntime    # noqa: F401
        return True
    except ImportError:
        return False


def masque_personne(img_bgr, cle=None, params=None):
    """Masque 0..255 (H x L) de la personne, avec un modèle U²-Net installé. None si aucun modèle."""
    import numpy as np
    cle = cle or modele_actif("detourage", params)
    if not cle or not installe(cle) or not onnx_present():
        return None
    s = _sessions.get(cle)
    if s is None:
        import onnxruntime as ort
        o = ort.SessionOptions()
        o.intra_op_num_threads = coeurs(params)
        o.inter_op_num_threads = 1
        s = ort.InferenceSession(os.path.join(dossier_modele(cle), etat()[cle]["roles"]["modele"]), o, providers=["CPUExecutionProvider"])
        _sessions[cle] = s
    import cv2
    H, L = img_bgr.shape[:2]
    rgb = cv2.cvtColor(cv2.resize(img_bgr, (320, 320), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB).astype(np.float32)
    rgb /= max(float(rgb.max()), 1e-6)
    rgb = (rgb - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    x = rgb.transpose(2, 0, 1)[None].astype(np.float32)
    sortie = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
    mi, ma = float(sortie.min()), float(sortie.max())
    m = (sortie - mi) / max(ma - mi, 1e-6)
    m = np.clip((m - 0.3) / 0.4, 0.0, 1.0)      # contraste : pas de personne à moitié transparente ni de fond fantôme
    return cv2.resize((m * 255).astype(np.uint8), (L, H), interpolation=cv2.INTER_LINEAR)
