"""Le moteur Remotion des animations (0.9.99) : la même fiche que le moteur maison et HyperFrames, dessinée par Remotion (React)
avec le look de l'étalon « Chiffres ».

Licence de Remotion (vérifiée le 20/11/2026) : gratuite pour un particulier, une structure de 3 personnes au plus, une
association, ou pour un essai sans usage commercial ; au-delà, une licence entreprise Remotion est obligatoire. PhilCut ne
distribue pas Remotion : il l'installe depuis npm sur ce poste, après que l'utilisateur a confirmé (une fois) y avoir droit.
Le moteur « motion » (Node portable, Chrome sans fenêtre) est celui d'HyperFrames ; le projet Remotion de PhilCut y est livré
sans ses bibliothèques (dossier remotion/).
"""
import json, os, re, shutil, subprocess, sys, threading

from .langue import _
from . import motion as M

LICENCE_URL = "https://www.remotion.dev/docs/license"


class ErreurRemotion(Exception):
    def __init__(self, texte, journal=""):
        super().__init__(texte)
        self.journal = journal          # 1.1.2 : la fin de la sortie de Remotion (renvoyée à l'IA pour qu'elle corrige)


CODE_LIBRE = "LibreCode.tsx"           # réécrit avant chaque rendu libre : jamais remplacé par la mise à jour des sources
_UN_RENDU_LIBRE = threading.Lock()    # un seul LibreCode.tsx dans le projet : un rendu libre à la fois


def dossier():
    from . import motion_html as MH
    return os.path.join(MH.dossier_moteur(), "remotion")


def cli():
    return os.path.join(dossier(), "node_modules", "@remotion", "cli", "remotion-cli.js")


def pret():
    return os.path.exists(cli())


def npm_cli():
    from . import motion_html as MH
    n = os.path.dirname(MH.node())
    for c in (os.path.join(n, "node_modules", "npm", "bin", "npm-cli.js"),
              os.path.join(os.path.dirname(n), "lib", "node_modules", "npm", "bin", "npm-cli.js")):
        if os.path.exists(c):
            return c
    return ""


def installer(params, progression=None, arret=lambda: False):
    """Installe Remotion (depuis npm, sur ce poste) dans le projet de PhilCut ; demande la licence confirmée et le moteur
    « motion » installé."""
    from . import moteur, motion_html as MH
    if not (params or {}).get("remotion_licence"):
        raise ErreurRemotion(_("Confirmez d'abord votre droit à la licence gratuite de Remotion (ou votre licence entreprise)."))
    if not MH.local_pret():
        raise ErreurRemotion(_("Installez d'abord le moteur « Animations HyperFrames et Remotion » (Préférences › IA locale)."))
    if not os.path.exists(os.path.join(dossier(), "package.json")) or not npm_cli():
        raise ErreurRemotion(_("Le moteur installé est trop ancien pour Remotion : réinstallez-le (Préférences › IA locale)."))
    progression and progression(0.05, _("Installation de Remotion depuis npm (environ 250 Mo)"))
    env = dict(os.environ, npm_config_update_notifier="false", npm_config_fund="false", npm_config_audit="false")
    env["PATH"] = os.path.dirname(MH.node()) + os.pathsep + env.get("PATH", "")
    proc = subprocess.Popen([MH.node(), npm_cli(), "install", "--omit=dev", "--no-audit", "--no-fund", "--loglevel", "http"],
                            cwd=dossier(), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace", **moteur._sans_console())
    n, fin = 0, []
    for ligne in proc.stdout:
        n += 1
        fin = (fin + [ligne.rstrip()])[-30:]
        if arret():
            proc.kill()
            raise InterruptedError()
        if progression and n % 5 == 0:
            progression(min(0.95, 0.05 + n / 600), _("Installation de Remotion depuis npm"))
    if proc.wait() != 0 or not pret():
        from .journal import ecrire
        ecrire("remotion", "\n".join(fin))
        raise ErreurRemotion(_("Installation de Remotion impossible : {e}", e=" / ".join(fin[-3:])[-300:]))
    progression and progression(1.0, _("Remotion installé"))
    return True


def sources_livrees():
    """Le projet Remotion livré avec PhilCut (src/) : il suit la version de PhilCut, pas celle du moteur installé."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "motion", "philcut-remotion", "src")


def mettre_a_jour_sources():
    """1.0.1 : les nouveaux types d'animation sont dans PhilCut.tsx ; le moteur installé avant les reçoit sans réinstallation."""
    src, dst = sources_livrees(), os.path.join(dossier(), "src")
    if not os.path.isdir(src) or not os.path.isdir(os.path.dirname(dst)):
        return 0
    n = 0
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(src):
        a, b = os.path.join(src, f), os.path.join(dst, f)
        if not os.path.isfile(a) or (f == CODE_LIBRE and os.path.exists(b)):
            continue
        with open(a, "rb") as x:
            neuf = x.read()
        try:
            with open(b, "rb") as y:
                if y.read() == neuf:
                    continue
        except OSError:
            pass
        with open(b, "wb") as y:
            y.write(neuf)
        n += 1
    return n


def preparer(anim):
    """La fiche passée à Remotion (--props) ; polices et logo copiés dans public/ ; les sources mises à la version de PhilCut."""
    from . import charte as CH, motion_html as MH
    try:
        mettre_a_jour_sources()
    except OSError:
        pass
    pub = os.path.join(dossier(), "public")
    os.makedirs(pub, exist_ok=True)
    if anim.get("genre") == "defilement" and anim.get("image") and os.path.exists(anim["image"]):
        nom = "capture" + os.path.splitext(anim["image"])[1].lower()
        shutil.copy2(anim["image"], os.path.join(pub, nom))
        anim = dict(anim, _html_image=nom, _html_ratio=MH._ratio(anim["image"]))
    m = MH.mise_en_page(anim)
    m["cadence"] = int(anim.get("cadence") or 30)
    ch = CH.complete(anim.get("charte"))
    polices = []
    for fam in {ch.get("police_titre") or "Poppins", ch.get("police_texte") or "Poppins", "Poppins"}:
        for f, poids in MH.POLICES_LIVREES.get(fam, []):
            src = os.path.join(MH._dossier_polices(), f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(pub, f))
                polices.append([fam, f, poids])
    m["polices"] = polices
    if ch.get("logo") and os.path.exists(ch["logo"]) and anim.get("logo") is not False:
        nom = "logo" + os.path.splitext(ch["logo"])[1].lower()
        shutil.copy2(ch["logo"], os.path.join(pub, nom))
        m["logo"] = nom
    return {"A": m}


def _polices_et_logo(anim, pub):
    from . import charte as CH, motion_html as MH
    ch = CH.complete(anim.get("charte"))
    polices, logo = [], ""
    for fam in {ch.get("police_titre") or "Poppins", ch.get("police_texte") or "Poppins", "Poppins"}:
        for f, poids in MH.POLICES_LIVREES.get(fam, []):
            src = os.path.join(MH._dossier_polices(), f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(pub, f))
                polices.append([fam, f, poids])
    if ch.get("logo") and os.path.exists(ch["logo"]) and anim.get("logo") is not False:
        logo = "logo" + os.path.splitext(ch["logo"])[1].lower()
        shutil.copy2(ch["logo"], os.path.join(pub, logo))
    return ch, polices, logo


def fiche_libre(anim):
    """1.1.2 : la fiche de la composition « Libre » (mêmes noms que pour HyperFrames : W, H, D, u, C, F…)."""
    from . import charte as CH
    from .motion import _langue_ui
    ch = CH.complete(anim.get("charte"))
    L, H = [int(x) // 2 * 2 for x in (anim.get("taille") or (1920, 1080))]
    cad = int(anim.get("cadence") or 30)
    return {"W": L, "H": H, "D": float(anim.get("duree") or 8), "fps": cad, "cadence": cad, "u": min(L, H) / 1080,
            "C": ch["couleurs"], "F": {"titre": ch.get("police_titre") or "Poppins", "texte": ch.get("police_texte") or "Poppins"},
            "TRANSPARENT": bool(anim.get("transparent")), "LANG": _langue_ui()}


def preparer_libre(anim, racine=None):
    """Ecrit le code de l'IA (LibreCode.tsx) dans le projet Remotion et rend la fiche (--props)."""
    racine = racine or dossier()
    lib = anim.get("libre") or {}
    if not lib.get("tsx", "").strip():
        raise ErreurRemotion(_("Cette animation n'a pas encore de code Remotion : faites-la écrire (ou réécrire) par l'IA."))
    if racine == dossier():
        try:
            mettre_a_jour_sources()
        except OSError:
            pass
    os.makedirs(os.path.join(racine, "src"), exist_ok=True)
    with open(os.path.join(racine, "src", CODE_LIBRE), "w", encoding="utf-8") as f:
        f.write(lib["tsx"])
    pub = os.path.join(racine, "public")
    os.makedirs(pub, exist_ok=True)
    m = fiche_libre(anim)
    _ch, m["polices"], logo = _polices_et_logo(anim, pub)
    if logo:
        m["logo"] = logo
    return {"A": m}


def _erreurs_utiles(lignes):
    """Les lignes de la sortie de Remotion qui disent l'erreur (compilation, exception dans le composant)."""
    garde = [x for x in lignes if re.search(r"error|Error|ERROR|✘|TypeError|ReferenceError|SyntaxError|is not|cannot|Cannot|"
                                            r"Expected|Unexpected|\.tsx:\d+", x)]
    return "\n".join((garde or lignes)[-25:])


def commande(props, sortie, anim):
    from . import motion_html as MH
    compo = "Libre" if anim.get("genre") == "libre" else "PhilCut"
    c = [MH.node(), cli(), "render", "src/index.ts", compo, sortie, f"--props={props}", f"--browser-executable={MH.navigateur()}",
         "--log=verbose" if os.environ.get("PHILCUT_DEBUG") else "--log=info"]
    if anim.get("transparent"):
        c += ["--codec=prores", "--prores-profile=4444", "--pixel-format=yuva444p10le"]
    else:
        c += ["--codec=h264", "--crf=16"]
    return c


def lire_progression(ligne):
    m = re.search(r"Rendered\s+(\d+)\s*/\s*(\d+)", ligne) or re.search(r"(\d+)\s*/\s*(\d+)", ligne)
    if m and int(m.group(2)) > 0:
        return min(1.0, int(m.group(1)) / int(m.group(2)))
    m = re.search(r"(\d{1,3})\s?%", ligne)
    return min(1.0, int(m.group(1)) / 100) if m else None


def rendre(params, anim, sortie, progression=None, arret=lambda: False):
    from . import moteur, motion_html as MH
    if not (params or {}).get("remotion_licence"):
        raise ErreurRemotion(_("Remotion : confirmez d'abord votre droit à la licence (une fois, dans la fenêtre Animation)."))
    if not pret():
        installer(params, progression, arret)
    if anim.get("genre") == "libre":
        with _UN_RENDU_LIBRE:
            return _rendre(params, anim, sortie, progression, arret)
    return _rendre(params, anim, sortie, progression, arret)


def _rendre(params, anim, sortie, progression=None, arret=lambda: False):
    from . import moteur, motion_html as MH
    sortie = os.path.splitext(sortie)[0] + (".mov" if anim.get("transparent") else ".mp4")
    props = os.path.join(M.dossier(), os.path.splitext(os.path.basename(sortie))[0] + ".props.json")
    fiche = preparer_libre(anim) if anim.get("genre") == "libre" else preparer(anim)
    json.dump(fiche, open(props, "w", encoding="utf-8"), ensure_ascii=False)
    env = dict(os.environ, REMOTION_DISABLE_TELEMETRY="1")
    env["PATH"] = os.path.dirname(MH.node()) + os.pathsep + os.path.dirname(moteur.ffmpeg()) + os.pathsep + env.get("PATH", "")
    progression and progression(0.02, _("Remotion prépare le rendu"))
    proc = subprocess.Popen(commande(props, sortie, anim), cwd=dossier(), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", **moteur._sans_console())
    fin = []
    try:
        for ligne in proc.stdout:
            fin = (fin + [ligne.rstrip()])[-120:]
            if arret():
                proc.kill()
                raise InterruptedError()
            f = lire_progression(ligne)
            if f is not None and progression and ("Render" in ligne or "%" in ligne):
                progression(0.05 + 0.93 * f, _("Remotion : rendu des images"))
        code = proc.wait()
    except BaseException:
        try:
            proc.kill()
        except OSError:
            pass
        raise
    if code != 0 or not os.path.exists(sortie):
        from .journal import ecrire
        ecrire("remotion", "\n".join(fin))
        raise ErreurRemotion(_("Le rendu Remotion a échoué : {e}", e=" / ".join(x for x in fin[-3:] if x.strip())[-300:]),
                             _erreurs_utiles(fin))
    return sortie


def projet_libre(anim, d):
    """1.1.2 : un projet Remotion complet de l'animation libre (sources, code de l'IA, fiche), à ouvrir dans Remotion Studio ou
    à retoucher dans Claude Code ; « npm install » puis « npx remotion studio »."""
    base = os.path.dirname(sources_livrees())
    os.makedirs(d, exist_ok=True)
    for f in ("package.json", "tsconfig.json"):
        if os.path.exists(os.path.join(base, f)):
            shutil.copy2(os.path.join(base, f), os.path.join(d, f))
    shutil.copytree(sources_livrees(), os.path.join(d, "src"), dirs_exist_ok=True)
    fiche = preparer_libre(anim, d)
    with open(os.path.join(d, "props.json"), "w", encoding="utf-8") as f:
        json.dump(fiche, f, ensure_ascii=False, indent=1)
    with open(os.path.join(d, "LISEZMOI.txt"), "w", encoding="utf-8") as f:
        f.write(_("Animation libre de PhilCut pour Remotion.\n\nLe code de l'animation : src/LibreCode.tsx.\n"
                  "Pour la voir et la retoucher : npm install, puis npx remotion studio --props=props.json (composition « Libre »).\n"
                  "Licence de Remotion : {u}\n", u=LICENCE_URL))
    return d
