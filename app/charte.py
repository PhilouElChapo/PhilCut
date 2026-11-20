"""Ma charte (0.9.99) : couleurs, polices, logo et allure, renseignées une fois et reprises par toutes les animations
(motion design, titres, sous-titres animés, habillage). Une charte se tire d'un logo, d'une image ou de votre site.

Les chartes sont des réglages communs (synchronisés entre vos postes) : params["chartes"] = {id: charte},
params["charte_active"] = id. Une charte :
  {"id", "nom", "couleurs": {"fond", "texte", "doux", "accent", "accent2"}, "police_titre", "police_texte",
   "logo": chemin, "allure": "moderne|sobre|punchy|tech", "mouvement": "doux|vif|rebond", "coins": 0..1,
   "interdits": texte libre ("pas de rouge", "jamais de police à empattements"…), "source": d'où elle vient}
"""
import html, json, os, re, time, urllib.parse, urllib.request, uuid

from .langue import _

ALLURES = {"moderne": _("Moderne : fond sombre, dégradés doux, lueur"), "sobre": _("Sobre : fond uni, aucun effet"),
           "punchy": _("Punchy : couleurs franches, gros chiffres"), "tech": _("Tech : grille, traits fins, chiffres à chasse fixe")}
MOUVEMENTS = {"doux": _("Doux : arrivées glissées, sans rebond"), "vif": _("Vif : arrivées rapides"),
              "rebond": _("Rebond : chaque élément rebondit en arrivant")}

DEFAUT = {"id": "defaut", "nom": _("PhilCut (par défaut)"),
          "couleurs": {"fond": "#0B1020", "texte": "#EEF1FA", "doux": "#8A93B2", "accent": "#8B7CFF", "accent2": "#3EE0F0"},
          "police_titre": "Poppins", "police_texte": "Poppins", "logo": "", "allure": "moderne", "mouvement": "doux",
          "coins": 0.6, "interdits": "", "source": ""}
ROLES = ("fond", "texte", "doux", "accent", "accent2")
NOMS_ROLES = {"fond": _("Fond"), "texte": _("Texte"), "doux": _("Texte discret"), "accent": _("Accent"), "accent2": _("Second accent")}
UA = {"User-Agent": "PhilCut (charte graphique ; https://github.com/PhilouElChapo/PhilCut)"}


# ------------------------------------------------------------------ couleurs
def hex_rvb(c):
    c = (c or "#000000").lstrip("#")
    if len(c) == 3:
        c = "".join(x * 2 for x in c)
    try:
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (0, 0, 0)


def rvb_hex(r, g, b):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(x)))) for x in (r, g, b))


def luminance(c):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = hex_rvb(c)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contraste(a, b):
    """Rapport de contraste (WCAG) : 4,5 au moins pour un texte lisible, 3 pour un gros titre."""
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def saturation(c):
    r, g, b = (x / 255 for x in hex_rvb(c))
    mx, mn = max(r, g, b), min(r, g, b)
    return 0.0 if mx == 0 else (mx - mn) / mx


def melanger(a, b, t):
    ra, rb = hex_rvb(a), hex_rvb(b)
    return rvb_hex(*(x + (y - x) * t for x, y in zip(ra, rb)))


def lisible_sur(fond, voulu=None, mini=4.5):
    """La couleur de texte voulue si elle se lit sur le fond, sinon éclaircie ou foncée jusqu'à se lire."""
    if voulu and contraste(voulu, fond) >= mini:
        return voulu
    cible = "#FFFFFF" if luminance(fond) < 0.4 else "#111111"
    if not voulu:
        return cible
    for k in range(1, 11):
        c = melanger(voulu, cible, k / 10)
        if contraste(c, fond) >= mini:
            return c
    return cible


def avertissements(ch):
    """Ce qui ne se lirait pas bien, dit en clair (la fenêtre l'affiche en orange)."""
    c = ch["couleurs"]
    out = []
    if contraste(c["texte"], c["fond"]) < 4.5:
        out.append(_("Le texte se lit mal sur le fond (contraste {r} ; 4,5 conseillé).", r=f"{contraste(c['texte'], c['fond']):.1f}".replace(".", ",")))
    if contraste(c["accent"], c["fond"]) < 3:
        out.append(_("L'accent ressort peu sur le fond (contraste {r} ; 3 conseillé).", r=f"{contraste(c['accent'], c['fond']):.1f}".replace(".", ",")))
    if contraste(c["doux"], c["fond"]) < 3:
        out.append(_("Le texte discret disparaît presque sur le fond."))
    return out


def corriger(ch):
    """Rend la charte lisible sans changer son esprit : texte et texte discret ajustés au fond."""
    ch = json.loads(json.dumps(ch))
    c = ch["couleurs"]
    c["texte"] = lisible_sur(c["fond"], c["texte"], 4.5)
    c["doux"] = lisible_sur(c["fond"], c["doux"], 3.0)
    c["accent"] = lisible_sur(c["fond"], c["accent"], 3.0)
    return ch


# ------------------------------------------------------------------ tirer une charte d'une image
def couleurs_image(chemin, n=6):
    """Les couleurs principales d'une image (logo, capture) : [(hex, part)], des plus présentes aux moins présentes. Un
    fond transparent est ignoré."""
    import cv2
    import numpy as np
    img = cv2.imread(chemin, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(_("Image illisible : {f}", f=os.path.basename(chemin)))
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    h, w = img.shape[:2]
    k = 160 / max(h, w)
    if k < 1:
        img = cv2.resize(img, (max(1, int(w * k)), max(1, int(h * k))), interpolation=cv2.INTER_AREA)
    if img.shape[2] == 4:
        px = img[img[:, :, 3] > 128][:, :3]
    else:
        px = img.reshape(-1, 3)
    if len(px) < 10:
        raise ValueError(_("L'image est presque vide."))
    px = px.astype(np.float32)
    n = min(n, len(px))
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0)
    _c, etiq, centres = cv2.kmeans(px, n, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    parts = np.bincount(etiq.ravel(), minlength=n) / len(etiq)
    out = [(rvb_hex(c[2], c[1], c[0]), float(p)) for c, p in zip(centres, parts)]
    return sorted(out, key=lambda x: -x[1])


def depuis_couleurs(couleurs, nom="", source="", base=None):
    """Une charte proposée d'après des couleurs [(hex, part)] : la plus vive devient l'accent, la seconde vive le second
    accent ; le fond reste sombre (allure moderne) sauf si l'image est surtout claire."""
    ch = json.loads(json.dumps(base or DEFAUT))
    ch["id"] = time.strftime("%Y%m%d") + "_" + uuid.uuid4().hex[:6]
    ch["nom"], ch["source"] = nom or _("Ma charte"), source
    vives = sorted((c for c, p in couleurs if saturation(c) > 0.35 and 0.03 < luminance(c) < 0.9),
                   key=lambda c: -(saturation(c) * (0.5 + dict(couleurs).get(c, 0))))
    claires = sum(p for c, p in couleurs if luminance(c) > 0.6)
    c = ch["couleurs"]
    if vives:
        c["accent"] = vives[0]
        c["accent2"] = next((v for v in vives[1:] if _ecart_teinte(v, vives[0]) > 30), melanger(vives[0], "#FFFFFF", 0.35))
    if claires > 0.55:          # identité claire (fond blanc dominant)
        c["fond"], c["texte"], c["doux"] = "#F7F7F9", "#14161C", "#5B6170"
        ch["allure"] = "sobre"
    else:
        sombres = [x for x, _p in couleurs if luminance(x) < 0.05]
        c["fond"] = sombres[0] if sombres else melanger(c["accent"], "#05070D", 0.88)
    return corriger(ch)


def _teinte(c):
    r, g, b = (x / 255 for x in hex_rvb(c))
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return 0.0
    if mx == r:
        h = ((g - b) / (mx - mn)) % 6
    elif mx == g:
        h = (b - r) / (mx - mn) + 2
    else:
        h = (r - g) / (mx - mn) + 4
    return h * 60


def _ecart_teinte(a, b):
    d = abs(_teinte(a) - _teinte(b)) % 360
    return min(d, 360 - d)


def depuis_image(chemin, nom=""):
    ch = depuis_couleurs(couleurs_image(chemin), nom or os.path.splitext(os.path.basename(chemin))[0],
                         _("image {f}", f=os.path.basename(chemin)))
    ch["logo"] = chemin
    return ch


# ------------------------------------------------------------------ tirer une charte d'un site
def lire_site(url, delai=15):
    """La page d'accueil (et ses feuilles de style) : texte HTML et CSS, lus comme un navigateur sans s'en faire passer pour
    un (PhilCut se nomme)."""
    if not re.match(r"^https?://", url or ""):
        url = "https://" + (url or "").strip()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=delai) as r:
        page = r.read(2_000_000).decode("utf-8", "replace")
        url = r.geturl()
    css = []
    for lien in re.findall(r"<link[^>]+rel=[\"']?stylesheet[^>]*>", page, re.I)[:6]:
        m = re.search(r"href=[\"']([^\"']+)", lien)
        if m:
            try:
                with urllib.request.urlopen(urllib.request.Request(urllib.parse.urljoin(url, html.unescape(m.group(1))), headers=UA),
                                            timeout=delai) as r:
                    css.append(r.read(1_000_000).decode("utf-8", "replace"))
            except Exception:      # noqa: BLE001 : une feuille absente n'empêche rien
                pass
    return url, page, "\n".join(css)


def analyser_site(url, page, css):
    """Couleurs (les plus employées, la couleur de thème d'abord), polices et logo d'un site."""
    tout = page + "\n" + css
    theme = re.findall(r"<meta[^>]+name=[\"']theme-color[\"'][^>]+content=[\"'](#[0-9a-fA-F]{3,6})", page, re.I)
    vues = {}
    for c in re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", tout):
        h = rvb_hex(*hex_rvb(c))
        vues[h] = vues.get(h, 0) + 1
    for r_, g_, b_ in re.findall(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})", tout):
        h = rvb_hex(int(r_), int(g_), int(b_))
        vues[h] = vues.get(h, 0) + 1
    total = sum(vues.values()) or 1
    couleurs = sorted(((c, n / total) for c, n in vues.items()), key=lambda x: -x[1])[:16]
    if theme:
        couleurs.insert(0, (rvb_hex(*hex_rvb(theme[0])), 0.5))
    polices = []
    for f in re.findall(r"font-family\s*:\s*([^;}{]+)", tout, re.I):
        nom = f.split(",")[0].strip().strip("'\"")
        if nom and not nom.startswith(("var(", "inherit", "-apple", "system-ui", "sans-serif", "serif", "monospace")) and nom not in polices:
            polices.append(nom)
    for f in re.findall(r"fonts\.googleapis\.com/css2?\?family=([^&\"':]+)", page):
        nom = urllib.parse.unquote_plus(f.split(":")[0])
        if nom not in polices:
            polices.insert(0, nom)
    logo = ""
    for motif in (r"<link[^>]+rel=[\"'](?:apple-touch-icon|icon)[\"'][^>]+href=[\"']([^\"']+)",
                  r"<meta[^>]+property=[\"']og:image[\"'][^>]+content=[\"']([^\"']+)",
                  r"<img[^>]+(?:class|id|alt)=[\"'][^\"']*logo[^\"']*[\"'][^>]+src=[\"']([^\"']+)",
                  r"<img[^>]+src=[\"']([^\"']*logo[^\"']*)"):
        m = re.search(motif, page, re.I)
        if m:
            logo = urllib.parse.urljoin(url, html.unescape(m.group(1)))
            break
    return {"couleurs": couleurs, "polices": polices[:6], "logo": logo,
            "nom": (re.search(r"<title>([^<]{1,80})", page, re.I) or [None, ""])[1].strip()}


def depuis_site(url, dossier_logo=None, delai=15):
    url, page, css = lire_site(url, delai)
    a = analyser_site(url, page, css)
    hote = urllib.parse.urlparse(url).hostname or url
    ch = depuis_couleurs(a["couleurs"] or [("#8B7CFF", 1.0)], a["nom"] or hote, _("site {s}", s=hote))
    if a["polices"]:
        ch["police_titre"] = ch["police_texte"] = a["polices"][0]
        ch["polices_site"] = a["polices"]
    if a["logo"] and dossier_logo:
        try:
            os.makedirs(dossier_logo, exist_ok=True)
            ext = os.path.splitext(urllib.parse.urlparse(a["logo"]).path)[1].lower()
            ext = ext if ext in (".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico") else ".png"
            f = os.path.join(dossier_logo, f"logo_{ch['id']}{ext}")
            with urllib.request.urlopen(urllib.request.Request(a["logo"], headers=UA), timeout=delai) as r:
                open(f, "wb").write(r.read(5_000_000))
            ch["logo"] = f
        except Exception:      # noqa: BLE001 : la charte vaut sans le logo
            pass
    return ch


# ------------------------------------------------------------------ rangement (réglages communs)
def toutes(params):
    d = dict((params or {}).get("chartes") or {})
    out = [json.loads(json.dumps(DEFAUT))] + [complete(v) for k, v in d.items() if k != "defaut"]
    return out[:1] + sorted(out[1:], key=lambda c: _alpha(c.get("nom", "")))


def _alpha(t):
    import unicodedata
    return "".join(x for x in unicodedata.normalize("NFD", t or "") if unicodedata.category(x) != "Mn").casefold()


def complete(ch):
    out = json.loads(json.dumps(DEFAUT))
    out.update({k: v for k, v in (ch or {}).items() if k != "couleurs"})
    out["couleurs"].update({k: v for k, v in ((ch or {}).get("couleurs") or {}).items() if k in ROLES and v})
    return out


def active(params):
    ident = (params or {}).get("charte_active") or "defaut"
    return next((c for c in toutes(params) if c["id"] == ident), toutes(params)[0])


def garder(params, ch, rendre_active=True):
    ch = complete(ch)
    if not ch.get("id") or ch["id"] == "defaut":
        ch["id"] = time.strftime("%Y%m%d") + "_" + uuid.uuid4().hex[:6]
    d = dict(params.get("chartes") or {})
    d[ch["id"]] = ch
    params["chartes"] = d
    if rendre_active:
        params["charte_active"] = ch["id"]
    return ch


def retirer(params, ident):
    d = dict(params.get("chartes") or {})
    d.pop(ident, None)
    params["chartes"] = d
    if params.get("charte_active") == ident:
        params["charte_active"] = "defaut"


def dossier_logos():
    from .config import dossier_donnees
    return os.path.join(dossier_donnees(), "chartes")
