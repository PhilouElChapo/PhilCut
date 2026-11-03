"""IA locale : un modele de vision qui tourne sur ce poste, jamais interdite, mais mesuree.

Le moteur et le modele sont portables (app/packs_ia.py : ranges dans le dossier de PhilCut, lances a la demande,
arretes ensuite). Un Ollama deja installe par l'utilisateur sert seulement de secours.

Au premier usage PhilCut regarde le materiel (carte graphique, memoire, processeur, systeme), lance un petit
test chronometre, puis dit franchement : temps estime par video, qualite attendue, modele conseille.
Le resultat est garde par poste (params["ia_locale"]) et peut etre relance dans les Preferences.
"""
import json, os, platform, shutil, subprocess, sys, time, urllib.request

from .langue import _

OLLAMA = os.environ.get("PHILCUT_OLLAMA", "http://127.0.0.1:11434")


def materiel():
    """Ce que l'on sait du poste, sans rien installer."""
    m = {"systeme": platform.system(), "version": platform.release(), "processeur": platform.processor() or platform.machine(),
         "coeurs": os.cpu_count() or 1, "memoire_go": _memoire_go(), "gpu": "", "vram_go": 0.0, "nvidia": False}
    nv = shutil.which("nvidia-smi")
    if nv:
        try:
            out = subprocess.run([nv, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout
            nom, mem = out.strip().splitlines()[0].split(",")
            m.update(gpu=nom.strip(), vram_go=round(float(mem) / 1024, 1), nvidia=True)
        except Exception:
            pass
    if not m["gpu"]:
        if sys.platform == "win32":
            try:
                out = subprocess.run(["wmic", "path", "win32_VideoController", "get", "name"], capture_output=True, text=True, timeout=10).stdout
                noms = [l.strip() for l in out.splitlines()[1:] if l.strip()]
                m["gpu"] = ", ".join(noms)
            except Exception:
                pass
        else:
            try:
                out = subprocess.run(["lspci"], capture_output=True, text=True, timeout=10).stdout
                m["gpu"] = ", ".join(l.split(":", 2)[-1].strip() for l in out.splitlines() if "VGA" in l or "3D" in l)[:120]
            except Exception:
                pass
    return m


def _memoire_go():
    try:
        if sys.platform == "win32":
            import ctypes
            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            s = MS()
            s.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
            return round(s.ullTotalPhys / 1024 ** 3, 1)
        with open("/proc/meminfo") as f:
            for l in f:
                if l.startswith("MemTotal"):
                    return round(int(l.split()[1]) / 1024 ** 2, 1)
    except Exception:
        pass
    return 0.0


def ollama_present():
    """Ollama déjà installé par l'utilisateur : utilisé en secours, jamais demandé."""
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3) as r:
            d = json.loads(r.read().decode("utf-8"))
        return [m["name"] for m in d.get("models", [])]
    except Exception:
        return None


def modele_conseille(mat):
    """Clef du modèle de vision portable conseillé pour ce poste."""
    vram = mat.get("vram_go") or 0
    ram = mat.get("memoire_go") or 0
    return "vision_standard" if (vram >= 6 or ram >= 16) else "vision_leger"


def modele_actif(params):
    """Modèle à utiliser : le modèle portable installé, sinon un modèle Ollama déjà présent, sinon rien."""
    from . import packs_ia
    m = packs_ia.modele_actif("vision", params)
    if m:
        return m
    etat = (params or {}).get("ia_locale") or {}
    if etat.get("modele") and not str(etat["modele"]).startswith("vision_"):
        return etat["modele"]
    o = ollama_present()
    return o[0] if o else None


def _png_essai():
    import struct, zlib
    L = H = 64
    brut = b"".join(b"\x00" + bytes(((x // 8 + y // 8) % 2) * 255 for x in range(L) for _c in range(3)) for y in range(H))

    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", L, H, 8, 2, 0, 0, 0)) + bloc(b"IDAT", zlib.compress(brut)) + bloc(b"IEND", b"")


def tester(params, texte_progression=None):
    """Test chronométré du modèle installé : démarrage du moteur, une question avec une petite image, arrêt.
    Renvoie le dictionnaire gardé par poste dans params["ia_locale"]."""
    from . import packs_ia
    mat = materiel()
    conseil = modele_conseille(mat)
    res = {"materiel": mat, "date": time.strftime("%Y-%m-%d %H:%M"), "modele": "", "secondes": None, "qualite": 0, "avis": "",
           "conseil": conseil, "poste_leger": bool((params or {}).get("ia_poste_leger", True))}
    cible = modele_actif(params)
    if not cible:
        info = packs_ia.modeles("vision").get(conseil) or {}
        res["avis"] = _("Aucun modèle de vision sur ce poste. Conseillé ici : « {n} » ({t} à télécharger), à cocher dans Préférences › IA locale. "
                        "Tout reste dans le dossier de PhilCut.", n=info.get("nom", conseil), t=packs_ia.taille_texte(packs_ia.a_telecharger(conseil)) if info else "?")
        return res
    res["modele"] = cible
    portable = cible.startswith("vision_")
    res["qualite"] = (packs_ia.modeles("vision", avec_essai=True).get(cible) or {}).get("qualite", 3) if portable else 3
    texte_progression and texte_progression(_("Démarrage du moteur…"))
    debut = time.time()
    try:
        if portable:
            with packs_ia.ServeurVision(cible, params) as serveur:
                res["demarrage_s"] = round(time.time() - debut, 1)
                t1 = time.time()
                r = serveur.generer("Décris cette image en cinq mots.", [_png_essai()], delai=600)
                res["reponse_s"] = round(time.time() - t1, 1)
                res["mode"] = serveur.mode
        else:
            r = generer(cible, "Décris cette image en cinq mots.", [_png_essai()], delai=600, params=params)
        res["secondes"] = round(time.time() - debut, 1)
        res["reponse"] = r[:120]
    except Exception as e:      # noqa: BLE001
        res["avis"] = _("Le modèle {m} n'a pas répondu : {e}", m=cible, e=e)
        return res
    s = res["secondes"]
    # une recette ≈ un démarrage + une longue réponse (fiche et une dizaine de vignettes ≈ 10 fois la petite question)
    estim = res.get("demarrage_s", 0) + res.get("reponse_s", s) * 10 if portable else s * 6
    res["estimation_recette_s"] = round(estim)
    nom = (packs_ia.modeles("vision", avec_essai=True).get(cible) or {}).get("nom", cible) if portable else cible
    carte = packs_ia.carte_graphique()
    if res.get("mode") == "gpu":
        res["materiel_ia"] = _("carte graphique ({c}, Vulkan)", c=carte)
    elif portable:
        res["materiel_ia"] = _("processeur, {n} cœurs sur {t}{l}", n=packs_ia.coeurs(params), t=os.cpu_count() or "?",
                               l=_(" (poste léger)") if (params or {}).get("ia_poste_leger", True) else "")
    if estim < 60:
        res["avis"] = _("Rapide sur ce poste : environ {n} s par vidéo avec « {m} ». Qualité des idées : {q}/5.", n=round(estim), m=nom, q=res["qualite"])
    elif estim < 300:
        res["avis"] = _("Utilisable : environ {n} min par vidéo avec « {m} ». Qualité des idées : {q}/5. L'IA cloud sera plus inspirée.", n=round(estim / 60), m=nom, q=res["qualite"])
    else:
        res["avis"] = _("Lent sur ce poste : environ {n} min par vidéo. Vous pouvez quand même l'utiliser ; sinon les recettes sans IA ou l'IA cloud.", n=round(estim / 60))
    if res.get("materiel_ia"):
        res["avis"] += " " + _("Calcul sur : {m}.", m=res["materiel_ia"])
        if carte and res.get("mode") != "gpu" and (params or {}).get("ia_gpu", True) is not False:
            res["avis"] += " " + _("La carte graphique n'a pas pu servir (pilote Vulkan absent ?) : le processeur a pris le relais.")
    return res


def generer(modele, consigne, images=(), systeme="", json_attendu=False, delai=900, params=None):
    """Modèle portable (clef « vision_… ») : moteur lancé pour ce travail puis arrêté. Sinon : Ollama déjà installé."""
    if not modele or str(modele).startswith("vision_"):
        from . import packs_ia
        return packs_ia.generer_vision(consigne, images, systeme, json_attendu, params=params, cle=modele or None, delai=delai)
    import base64
    corps = {"model": modele, "prompt": consigne, "stream": False, "images": [base64.b64encode(i).decode() for i in images]}
    if systeme:
        corps["system"] = systeme
    if json_attendu:
        corps["format"] = "json"
    req = urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps(corps).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=delai) as r:
        return json.loads(r.read().decode("utf-8")).get("response", "")
