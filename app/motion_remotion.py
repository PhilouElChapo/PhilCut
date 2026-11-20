"""Le moteur Remotion des animations (0.9.99) : la même fiche que le moteur maison et HyperFrames, dessinée par Remotion (React)
avec le look de l'étalon « Chiffres ».

Licence de Remotion (vérifiée le 20/11/2026) : gratuite pour un particulier, une structure de 3 personnes au plus, une
association, ou pour un essai sans usage commercial ; au-delà, une licence entreprise Remotion est obligatoire. PhilCut ne
distribue pas Remotion : il l'installe depuis npm sur ce poste, après que l'utilisateur a confirmé (une fois) y avoir droit.
Le moteur « motion » (Node portable, Chrome sans fenêtre) est celui d'HyperFrames ; le projet Remotion de PhilCut y est livré
sans ses bibliothèques (dossier remotion/).
"""
import json, os, re, shutil, subprocess, sys

from .langue import _
from . import motion as M

LICENCE_URL = "https://www.remotion.dev/docs/license"


class ErreurRemotion(Exception):
    pass


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
        if not os.path.isfile(a):
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


def commande(props, sortie, anim):
    from . import motion_html as MH
    c = [MH.node(), cli(), "render", "src/index.ts", "PhilCut", sortie, f"--props={props}", f"--browser-executable={MH.navigateur()}",
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
    sortie = os.path.splitext(sortie)[0] + (".mov" if anim.get("transparent") else ".mp4")
    props = os.path.join(M.dossier(), os.path.splitext(os.path.basename(sortie))[0] + ".props.json")
    json.dump(preparer(anim), open(props, "w", encoding="utf-8"), ensure_ascii=False)
    env = dict(os.environ, REMOTION_DISABLE_TELEMETRY="1")
    env["PATH"] = os.path.dirname(MH.node()) + os.pathsep + os.path.dirname(moteur.ffmpeg()) + os.pathsep + env.get("PATH", "")
    progression and progression(0.02, _("Remotion prépare le rendu"))
    proc = subprocess.Popen(commande(props, sortie, anim), cwd=dossier(), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", **moteur._sans_console())
    fin = []
    try:
        for ligne in proc.stdout:
            fin = (fin + [ligne.rstrip()])[-40:]
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
        raise ErreurRemotion(_("Le rendu Remotion a échoué : {e}", e=" / ".join(x for x in fin[-3:] if x.strip())[-300:]))
    return sortie
