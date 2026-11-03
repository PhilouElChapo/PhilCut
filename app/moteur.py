"""Moteur video de PhilCut : FFmpeg et FFprobe embarques.

Tout le travail lourd passe par ici : fiche technique d'un media, vignettes, forme d'onde, proxys (copies legeres
pour monter sans ralentir), detection des coupes et des silences, encodeurs materiels disponibles, export.

FFmpeg est cherche d'abord dans le dossier « bin » a cote du programme (paquet tout-en-un), puis dans le PATH.
Aucune fenetre noire sous Windows : chaque appel est lance sans console.
"""
import json, os, re, shutil, subprocess, sys, tempfile, threading

from .config import dossier_programme, dossier_donnees

HAUTEUR_PROXY = 540
_verrou = threading.Lock()
_encodeurs = None


class ErreurMoteur(Exception):
    pass


# ------------------------------------------------------------------ outils
def _sans_console():
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {"startupinfo": si, "creationflags": 0x08000000}
    return {}


def _bin(nom):
    exe = nom + (".exe" if sys.platform == "win32" else "")
    for d in (os.path.join(dossier_programme(), "bin"), os.path.join(dossier_programme(), "_internal", "bin"),
              os.path.join(getattr(sys, "_MEIPASS", ""), "bin")):
        p = os.path.join(d, exe)
        if d and os.path.exists(p):
            return p
    return shutil.which(nom) or nom


def ffmpeg():
    return _bin("ffmpeg")


def ffprobe():
    return _bin("ffprobe")


def disponible():
    try:
        subprocess.run([ffmpeg(), "-version"], capture_output=True, timeout=20, **_sans_console())
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def version():
    try:
        out = subprocess.run([ffmpeg(), "-version"], capture_output=True, text=True, timeout=20, **_sans_console()).stdout
        m = re.search(r"ffmpeg version (\S+)", out)
        return m.group(1) if m else "?"
    except (OSError, subprocess.SubprocessError):
        return ""


def version_majeure():
    """7 pour « 7.1 », 8 pour une build « N-128293-g… » (master BtbN = la plus recente), 0 si inconnue."""
    v = version()
    mm = re.match(r"(\d+)\.", v)
    if mm:
        return int(mm.group(1))
    return 99 if v.startswith("N-") else 0


def args_script_filtres(chemin):
    """Le graphe de filtres est long : on le passe par un fichier. FFmpeg 7+ lit « -/filter_complex fichier »,
    les versions anterieures « -filter_complex_script fichier » (retire dans FFmpeg 8)."""
    return ["-/filter_complex", chemin] if version_majeure() >= 7 else ["-filter_complex_script", chemin]


def lancer(args, entree=None, delai=None, progression=None, duree=None, arret=lambda: False):
    """Lance ffmpeg ; progression(fraction) si la duree de sortie est connue. Leve ErreurMoteur si echec."""
    cmd = [ffmpeg(), "-hide_banner", "-nostdin", "-y"] + list(args)
    if progression and duree:
        cmd[1:1] = ["-progress", "pipe:1", "-loglevel", "error"]
    try:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE if entree is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, **_sans_console())
    except OSError as e:
        raise ErreurMoteur(f"FFmpeg introuvable : {e}")
    if entree is not None:
        try:
            p.stdin.write(entree)
        except OSError:
            pass
        p.stdin.close()
    err = []

    def lire_err():
        for ligne in p.stderr:
            err.append(ligne.decode("utf-8", "replace"))
    t = threading.Thread(target=lire_err, daemon=True)
    t.start()
    if progression and duree:
        for ligne in p.stdout:
            ligne = ligne.decode("utf-8", "replace").strip()
            if ligne.startswith("out_time_us=") or ligne.startswith("out_time_ms="):
                try:
                    us = int(ligne.split("=")[1])
                    progression(min(1.0, us / 1e6 / duree))
                except ValueError:
                    pass
            if arret():
                p.kill()
                raise InterruptedError()
    else:
        p.stdout.read()
    p.wait(timeout=delai)
    t.join(timeout=5)
    if p.returncode != 0:
        texte = "".join(err[-12:]).strip()
        raise ErreurMoteur(texte or f"FFmpeg a échoué (code {p.returncode})")
    return "".join(err)


def sortie(args, delai=120):
    """Lance ffmpeg et renvoie ce qu'il ecrit sur la sortie standard (octets)."""
    cmd = [ffmpeg(), "-hide_banner", "-nostdin", "-loglevel", "error"] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=delai, **_sans_console())
    except OSError as e:
        raise ErreurMoteur(f"FFmpeg introuvable : {e}")
    if r.returncode != 0:
        raise ErreurMoteur(r.stderr.decode("utf-8", "replace")[-800:])
    return r.stdout


# ------------------------------------------------------------------ fiche technique
def sonder(chemin):
    """Fiche technique d'un media : ce que PhilCut doit savoir avant de monter.
    Rotation (telephones), cadence reelle et variable, HDR, pistes son, date, GPS."""
    cmd = [ffprobe(), "-v", "error", "-print_format", "json", "-show_format", "-show_streams", chemin]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace", **_sans_console())
    except OSError as e:
        raise ErreurMoteur(f"FFprobe introuvable : {e}")
    if r.returncode != 0:
        raise ErreurMoteur(r.stderr.strip()[-400:] or "fichier illisible")
    d = json.loads(r.stdout or "{}")
    fmt = d.get("format", {})
    tags = {k.lower(): v for k, v in (fmt.get("tags") or {}).items()}
    f = {"chemin": chemin, "nom": os.path.basename(chemin), "duree": float(fmt.get("duration") or 0),
         "debit": int(fmt.get("bit_rate") or 0), "taille": int(fmt.get("size") or 0), "video": None, "audio": [],
         "date": tags.get("creation_time", ""), "gps": _gps(tags.get("location") or tags.get("com.apple.quicktime.location.iso6709", "")),
         "appareil": " ".join(x for x in (tags.get("com.android.manufacturer", ""), tags.get("com.android.model", ""),
                                            tags.get("com.apple.quicktime.model", "")) if x).strip(),
         "cadence_capture": float(tags.get("com.android.capture.fps") or 0)}
    for s in d.get("streams", []):
        if s.get("codec_type") == "video" and f["video"] is None and s.get("disposition", {}).get("attached_pic") != 1:
            rot = 0
            for sd in s.get("side_data_list") or []:
                if "rotation" in sd:
                    rot = int(round(float(sd["rotation"])))
            st = {k.lower(): v for k, v in (s.get("tags") or {}).items()}
            if not rot and st.get("rotate"):
                rot = int(st["rotate"])
            rot %= 360
            l, h = int(s.get("width") or 0), int(s.get("height") or 0)
            if rot in (90, 270):
                l, h = h, l
            cad = _fraction(s.get("avg_frame_rate")) or _fraction(s.get("r_frame_rate"))
            nominale = _fraction(s.get("r_frame_rate"))
            f["video"] = {"codec": s.get("codec_name"), "largeur": l, "hauteur": h, "rotation": rot,
                          "cadence": round(cad, 3), "cadence_nominale": round(nominale, 3),
                          "cadence_variable": bool(nominale and cad and abs(nominale - cad) / nominale > 0.02),
                          "pixel": s.get("pix_fmt"), "bits": 10 if "10" in (s.get("pix_fmt") or "") else 8,
                          "hdr": (s.get("color_transfer") in ("smpte2084", "arib-std-b67")),
                          "transfert": s.get("color_transfer"), "duree": float(s.get("duration") or f["duree"] or 0),
                          "images": int(s.get("nb_frames") or 0)}
        elif s.get("codec_type") == "audio":
            f["audio"].append({"codec": s.get("codec_name"), "canaux": int(s.get("channels") or 0),
                               "frequence": int(s.get("sample_rate") or 0), "langue": (s.get("tags") or {}).get("language", "")})
    f["vertical"] = bool(f["video"] and f["video"]["hauteur"] > f["video"]["largeur"])
    f["genre"] = "video" if f["video"] and f["duree"] > 0.05 else ("image" if f["video"] else ("audio" if f["audio"] else "inconnu"))
    return f


def _fraction(t):
    try:
        a, b = t.split("/")
        return float(a) / float(b) if float(b) else 0.0
    except (ValueError, AttributeError, ZeroDivisionError):
        return 0.0


def _gps(t):
    m = re.match(r"([+-]\d+\.?\d*)([+-]\d+\.?\d*)", t or "")
    if not m:
        return None
    try:
        return {"lat": float(m.group(1)), "lon": float(m.group(2))}
    except ValueError:
        return None


def resume_fiche(f):
    """Phrase courte pour l'Accueil et la bibliotheque : « 1 min 16 · 1080×1920 · 30 i/s · vertical »."""
    if not f:
        return ""
    v = f.get("video") or {}
    parts = [duree_texte(f.get("duree", 0))]
    if v:
        parts.append(f"{v['largeur']}×{v['hauteur']}")
        parts.append(f"{v['cadence']:g} i/s")
        if f.get("vertical"):
            parts.append("vertical")
        if v.get("hdr"):
            parts.append("HDR")
    if not f.get("audio"):
        parts.append("sans son")
    return " · ".join(parts)


def duree_texte(s):
    s = max(0, float(s or 0))
    if s < 60:
        return f"{s:.1f} s" if s < 10 else f"{int(round(s))} s"
    m, sec = divmod(int(round(s)), 60)
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min {sec:02d}"


# ------------------------------------------------------------------ images, vignettes, son
def image(chemin, t, largeur=640, fiche=None):
    """Une image du media a l'instant t, en PNG (octets), rotation du telephone appliquee."""
    args = ["-ss", f"{max(0.0, t):.3f}", "-i", chemin, "-frames:v", "1", "-an",
            "-vf", f"scale={int(largeur)}:-2:flags=bicubic", "-f", "image2", "-vcodec", "png", "pipe:1"]
    return sortie(args, delai=60)


def vignettes(chemin, n=12, hauteur=72, duree=None):
    """n vignettes reparties sur la duree, en une seule bande (PNG) : pour la timeline et l'assistant."""
    duree = duree or (sonder(chemin)["duree"] or 1)
    n = max(1, int(n))
    pas = max(duree / n, 0.04)
    args = ["-i", chemin, "-an", "-vf", f"fps=1/{pas:.4f},scale=-2:{int(hauteur)},tile={n}x1", "-frames:v", "1",
            "-f", "image2", "-vcodec", "png", "pipe:1"]
    return sortie(args, delai=240)


def images_clefs(chemin, instants, largeur=320):
    """Plusieurs images a des instants donnes (liste de PNG)."""
    return [image(chemin, t, largeur) for t in instants]


def forme_onde(chemin, points=400):
    """Niveaux sonores (0..1) en `points` colonnes : dessine la bande son dans la timeline."""
    try:
        brut = sortie(["-i", chemin, "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1"], delai=300)
    except ErreurMoteur:
        return [0.0] * points
    import array
    a = array.array("h")
    a.frombytes(brut[: len(brut) - len(brut) % 2])
    if not a:
        return [0.0] * points
    taille = max(1, len(a) // points)
    out = []
    for i in range(points):
        bloc = a[i * taille:(i + 1) * taille]
        out.append(min(1.0, (max(abs(x) for x in bloc) if bloc else 0) / 32768.0))
    return out


def niveaux(chemin):
    """Volume moyen et maximal (dB) ; piste muette si le maximal est sous -80 dB."""
    try:
        txt = lancer(["-i", chemin, "-vn", "-af", "volumedetect", "-f", "null", "-"], delai=600)
    except ErreurMoteur as e:
        txt = str(e)
    moy = re.search(r"mean_volume:\s*(-?[\d.]+)", txt)
    mx = re.search(r"max_volume:\s*(-?[\d.]+)", txt)
    m, x = (float(moy.group(1)) if moy else -91.0), (float(mx.group(1)) if mx else -91.0)
    return {"moyen": m, "max": x, "muet": x < -80}


def silences(chemin, seuil=-40, mini=1.0):
    """[(debut, fin)] des passages silencieux : pour couper les blancs."""
    try:
        txt = lancer(["-i", chemin, "-vn", "-af", f"silencedetect=n={seuil}dB:d={mini}", "-f", "null", "-"], delai=600)
    except ErreurMoteur as e:
        txt = str(e)
    debuts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", txt)]
    fins = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", txt)]
    return list(zip(debuts, fins))


def coupes(chemin, seuil=0.3):
    """Instants des changements de plan (detection de scene) : rythme d'un montage existant, moments forts."""
    try:
        txt = lancer(["-i", chemin, "-an", "-vf", f"select='gt(scene,{seuil})',showinfo", "-f", "null", "-"], delai=900)
    except ErreurMoteur as e:
        txt = str(e)
    return [float(x) for x in re.findall(r"pts_time:\s*([\d.]+)", txt)]


def luminosite(chemin, pas=1.0):
    """Luminosite moyenne (0..255) echantillonnee toutes les `pas` secondes : reperer la nuit, les passages noirs."""
    try:
        txt = lancer(["-i", chemin, "-an", "-vf", f"fps=1/{pas},signalstats,metadata=print:key=lavfi.signalstats.YAVG",
                      "-f", "null", "-"], delai=900)
    except ErreurMoteur as e:
        txt = str(e)
    return [float(x) for x in re.findall(r"YAVG=([\d.]+)", txt)]


def rythme(chemin):
    """Tempo approximatif (BPM) et instants des temps forts d'une musique, par l'energie du signal.
    Suffit a caler des coupes sur la musique ; une detection plus fine viendra avec une bibliotheque dediee."""
    try:
        brut = sortie(["-i", chemin, "-vn", "-ac", "1", "-ar", "11025", "-f", "s16le", "pipe:1"], delai=300)
    except ErreurMoteur:
        return {"bpm": 0, "temps": []}
    import array
    a = array.array("h")
    a.frombytes(brut[: len(brut) - len(brut) % 2])
    if len(a) < 11025:
        return {"bpm": 0, "temps": []}
    fen = 512                                              # ~46 ms
    energie = []
    for i in range(0, len(a) - fen, fen):
        bloc = a[i:i + fen]
        energie.append(sum(x * x for x in bloc) / fen)
    if not energie:
        return {"bpm": 0, "temps": []}
    moy = sum(energie) / len(energie)
    temps = []
    for i in range(1, len(energie) - 1):
        if energie[i] > 1.6 * moy and energie[i] > energie[i - 1] and energie[i] >= energie[i + 1]:
            t = i * fen / 11025
            if not temps or t - temps[-1] > 0.25:
                temps.append(round(t, 3))
    bpm = 0
    if len(temps) > 4:
        ecarts = sorted(b - a_ for a_, b in zip(temps, temps[1:]))
        med = ecarts[len(ecarts) // 2]
        if med > 0:
            bpm = 60 / med
            while bpm > 180:
                bpm /= 2
            while bpm and bpm < 60:
                bpm *= 2
    return {"bpm": round(bpm), "temps": temps}


# ------------------------------------------------------------------ proxys
def dossier_proxys(params=None):
    d = (params or {}).get("dossier_proxys") if params else ""
    d = d or os.path.join(dossier_donnees(), "proxys")
    os.makedirs(d, exist_ok=True)
    return d


def chemin_proxy(chemin, params=None):
    import hashlib
    try:
        st = os.stat(chemin)
        cle = f"{os.path.abspath(chemin)}|{st.st_size}|{int(st.st_mtime)}"
    except OSError:
        cle = chemin
    return os.path.join(dossier_proxys(params), hashlib.sha1(cle.encode("utf-8")).hexdigest()[:20] + ".mp4")


def proxy(chemin, params=None, fiche=None, progression=None, arret=lambda: False, hauteur=HAUTEUR_PROXY):
    """Copie legere H.264 (cadence fixe, rotation appliquee, HDR ramene en SDR) ; renvoie son chemin.
    C'est sur elle que l'on monte ; l'export repart de l'original."""
    cible = chemin_proxy(chemin, params)
    if os.path.exists(cible) and os.path.getsize(cible) > 0:
        return cible
    fiche = fiche or sonder(chemin)
    v = fiche.get("video") or {}
    cad = v.get("cadence") or 30
    cad = 30 if cad > 31 else (25 if 24.5 < cad < 25.5 else (24 if cad < 24.5 else 30))
    vf = [f"scale=-2:{hauteur}" if not fiche.get("vertical") else f"scale={int(hauteur * 9 / 16) // 2 * 2}:-2", f"fps={cad}"]
    if v.get("hdr"):
        vf.insert(0, "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
    else:
        vf.append("format=yuv420p")
    tmp = cible + ".part.mp4"
    args = ["-i", chemin, "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-g", str(int(cad)),
            "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-movflags", "+faststart", "-fps_mode", "cfr", tmp]
    try:
        lancer(args, progression=progression, duree=fiche.get("duree"), arret=arret, delai=None)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    os.replace(tmp, cible)
    return cible


# ------------------------------------------------------------------ encodeurs
def encodeurs():
    """Encodeurs H.264 reellement utilisables sur ce poste, du plus rapide au plus lent : NVENC (Nvidia),
    QuickSync (Intel), AMF (AMD), VA-API (Linux), puis libx264. Teste une fois par session."""
    global _encodeurs
    with _verrou:
        if _encodeurs is not None:
            return _encodeurs
        out = []
        for enc, extra in (("h264_nvenc", []), ("h264_qsv", []), ("h264_amf", []), ("h264_vaapi", ["-vaapi_device", "/dev/dri/renderD128"])):
            try:
                args = extra + ["-f", "lavfi", "-i", "color=c=black:s=256x144:d=0.2", "-frames:v", "3"]
                if enc == "h264_vaapi":
                    args += ["-vf", "format=nv12,hwupload"]
                args += ["-c:v", enc, "-f", "null", "-"]
                lancer(args, delai=30)
                out.append(enc)
            except Exception:
                pass
        out.append("libx264")
        _encodeurs = out
        return out


def nom_encodeur(e):
    return {"h264_nvenc": "Nvidia NVENC", "h264_qsv": "Intel QuickSync", "h264_amf": "AMD AMF", "h264_vaapi": "VA-API (Linux)",
            "libx264": "Processeur (x264)"}.get(e, e)


def args_encodeur(enc, qualite="normale"):
    """Options d'encodage H.264 selon l'encodeur et la qualite (allegee | normale | haute)."""
    q = {"allegee": 2, "normale": 1, "haute": 0}.get(qualite, 1)
    if enc == "h264_nvenc":
        return ["-c:v", enc, "-preset", "p5", "-rc", "vbr", "-cq", str([19, 23, 28][q]), "-b:v", "0", "-pix_fmt", "yuv420p"]
    if enc == "h264_qsv":
        return ["-c:v", enc, "-global_quality", str([20, 24, 29][q]), "-look_ahead", "0", "-pix_fmt", "nv12"]
    if enc == "h264_amf":
        return ["-c:v", enc, "-quality", "balanced", "-rc", "cqp", "-qp_i", str([19, 23, 28][q]), "-qp_p", str([19, 23, 28][q])]
    if enc == "h264_vaapi":
        return ["-vf", "format=nv12,hwupload", "-c:v", enc, "-qp", str([20, 24, 29][q])]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", str([18, 22, 27][q]), "-pix_fmt", "yuv420p"]


# ------------------------------------------------------------------ destinations d'export
DESTINATIONS = {
    # id : (libelle, largeur, hauteur, cadence, qualite, debit audio)
    "youtube": ("YouTube (16:9, 1080p)", 1920, 1080, 30, "haute", "192k"),
    "youtube4k": ("YouTube 4K (16:9)", 3840, 2160, 30, "haute", "192k"),
    "insta": ("Instagram / Reels (9:16)", 1080, 1920, 30, "normale", "128k"),
    "insta_carre": ("Instagram carré (1:1)", 1080, 1080, 30, "normale", "128k"),
    "whatsapp": ("WhatsApp (allégé)", 1280, 720, 30, "allegee", "96k"),
    "ecran_led": ("Écran LED vertical (9:16, 720p)", 720, 1280, 30, "normale", "96k"),
    "original": ("Comme la source", 0, 0, 0, "haute", "192k"),
}


def destination(ident):
    return DESTINATIONS.get(ident) or DESTINATIONS["youtube"]
