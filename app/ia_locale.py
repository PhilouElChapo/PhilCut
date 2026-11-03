"""IA locale : un modele de vision qui tourne sur ce poste (via Ollama), jamais interdite, mais mesuree.

Au premier usage PhilCut regarde le materiel (carte graphique, memoire, processeur, systeme), lance un petit
test chronometre, puis dit franchement : temps estime par video, qualite attendue, modele conseille.
Le resultat est garde par poste (params["ia_locale"]) et peut etre relance dans les Preferences.
"""
import json, os, platform, shutil, subprocess, sys, time, urllib.request

from .langue import _

OLLAMA = os.environ.get("PHILCUT_OLLAMA", "http://127.0.0.1:11434")
MODELES = [                     # (nom Ollama, taille, qualite 1-5, memoire video conseillee Go)
    ("qwen2.5vl:7b", "≈ 6 Go", 4, 8),
    ("llama3.2-vision:11b", "≈ 8 Go", 4, 10),
    ("moondream", "≈ 1,7 Go", 2, 2),
    ("llava:7b", "≈ 4,7 Go", 3, 6),
]


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
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3) as r:
            d = json.loads(r.read().decode("utf-8"))
        return [m["name"] for m in d.get("models", [])]
    except Exception:
        return None


def modele_conseille(mat):
    vram = mat.get("vram_go") or 0
    ram = mat.get("memoire_go") or 0
    if vram >= 8 or (mat["systeme"] == "Linux" and ram >= 16):
        return MODELES[0]
    if vram >= 6 or ram >= 16:
        return MODELES[3]
    return MODELES[2]


def tester(params, texte_progression=None):
    """Petit test chronometre : une question courte avec une image minuscule au modele installe (ou conseille s'il est la).
    Renvoie le dictionnaire garde dans params["ia_locale"]."""
    mat = materiel()
    res = {"materiel": mat, "date": time.strftime("%Y-%m-%d %H:%M"), "ollama": False, "modeles": [], "modele": "", "secondes": None,
           "qualite": 0, "avis": ""}
    modeles = ollama_present()
    if modeles is None:
        res["avis"] = _("Ollama n'est pas lancé sur ce poste. Installez-le (ollama.com), lancez-le, puis « ollama pull {m} » ; PhilCut le détectera.",
                        m=modele_conseille(mat)[0])
        return res
    res["ollama"] = True
    res["modeles"] = modeles
    conseil = modele_conseille(mat)
    cible = next((m for m in modeles if m.split(":")[0] == conseil[0].split(":")[0]), None) or (modeles[0] if modeles else "")
    if not cible:
        res["avis"] = _("Ollama tourne mais aucun modèle de vision n'est installé. Conseillé pour ce poste : « ollama pull {m} » ({t}).", m=conseil[0], t=conseil[1])
        return res
    res["modele"] = cible
    res["qualite"] = next((q for n, _t, q, _v in MODELES if n.split(":")[0] == cible.split(":")[0]), 3)
    # image test : un petit damier PNG genere a la main (pas de dependance)
    import base64, struct, zlib
    L = H = 64
    brut = b"".join(b"\x00" + bytes(((x // 8 + y // 8) % 2) * 255 for x in range(L) for _c in range(3)) for y in range(H))
    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", L, H, 8, 2, 0, 0, 0)) + bloc(b"IDAT", zlib.compress(brut)) + bloc(b"IEND", b"")
    debut = time.time()
    try:
        r = generer(cible, "Décris cette image en cinq mots.", [png], delai=240)
        res["secondes"] = round(time.time() - debut, 1)
        res["reponse"] = r[:120]
    except Exception as e:      # noqa: BLE001
        res["avis"] = _("Le modèle {m} n'a pas répondu : {e}", m=cible, e=e)
        return res
    s = res["secondes"]
    estim = s * 12                      # une recette = ~12 fois ce petit echange (fiche + 10 vignettes)
    res["estimation_recette_s"] = round(estim)
    if estim < 60:
        res["avis"] = _("Rapide sur ce poste : environ {n} s par vidéo avec {m}. Qualité des idées : {q}/5.", n=round(estim), m=cible, q=res["qualite"])
    elif estim < 300:
        res["avis"] = _("Utilisable : environ {n} min par vidéo avec {m}. Qualité des idées : {q}/5. L'IA cloud sera plus inspirée.", n=round(estim / 60), m=cible, q=res["qualite"])
    else:
        res["avis"] = _("Lent sur ce poste : environ {n} min par vidéo. Vous pouvez quand même l'utiliser ; sinon les recettes sans IA ou l'IA cloud.", n=round(estim / 60))
    return res


def generer(modele, consigne, images=(), systeme="", json_attendu=False, delai=600):
    import base64
    corps = {"model": modele, "prompt": consigne, "stream": False, "images": [base64.b64encode(i).decode() for i in images]}
    if systeme:
        corps["system"] = systeme
    if json_attendu:
        corps["format"] = "json"
    req = urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps(corps).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=delai) as r:
        return json.loads(r.read().decode("utf-8")).get("response", "")
