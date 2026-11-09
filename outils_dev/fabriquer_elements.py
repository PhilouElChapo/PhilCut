"""Fabrique catalogue/elements.json : les éléments animés de PhilCut (autocollants, réactions, flèches, météo, fête…),
au format Lottie (dessins vectoriels animés). Le même fichier est lu par le PC (rlottie) et par Android (lottie-android) :
nets à toute taille, couleurs modifiables, aucune vidéo à transparence.

Tous les dessins sont originaux (formes simples, couleurs vives, contour blanc) : aucun personnage, logo ou marque.
Lancer : python3 outils_dev/fabriquer_elements.py   (puis tests/test_0936.py qui vérifie et rend chaque élément)
"""
import json, math, os, time

FR, W = 30, 512
C = W / 2
BLANC = "#ffffff"


# ------------------------------------------------------------------ briques Lottie
def P(v):
    return {"a": 0, "k": v}


def _liste(v):
    return list(v) if isinstance(v, (list, tuple)) else [v]


def A(kfs, ease=(0.33, 0.67)):
    """Valeur animée : kfs = [(image, valeur), ...]."""
    k = []
    for i, (t, v) in enumerate(kfs):
        e = {"t": t, "s": _liste(v)}
        if i < len(kfs) - 1:
            e["o"] = {"x": [ease[0]], "y": [0]}
            e["i"] = {"x": [ease[1]], "y": [1]}
        k.append(e)
    return {"a": 1, "k": k}


def V(x):
    return x if isinstance(x, dict) else P(x)


def couleur(h, a=1):
    h = h.lstrip("#")
    return [round(int(h[i:i + 2], 16) / 255, 4) for i in (0, 2, 4)] + [a]


def tr(p=(0, 0), a=(0, 0), s=(100, 100), r=0, o=100):
    return {"ty": "tr", "p": V(list(p) if not isinstance(p, dict) else p), "a": V(list(a)), "s": V(list(s) if not isinstance(s, dict) else s),
            "r": V(r), "o": V(o), "sk": P(0), "sa": P(0)}


def el(x, y, w, h=None):
    return {"ty": "el", "p": P([x, y]), "s": V([w, w if h is None else h]) if not isinstance(w, dict) else w, "d": 1}


def rc(x, y, w, h, r=0):
    return {"ty": "rc", "p": P([x, y]), "s": P([w, h]), "r": P(r), "d": 1}


def sr(x, y, pointes, ext, inte=None, rot=0):
    """Etoile (inte donné) ou polygone régulier."""
    d = {"ty": "sr", "sy": 1 if inte else 2, "p": P([x, y]), "r": V(rot), "pt": P(pointes), "or": V(ext), "os": P(0), "d": 1}
    if inte:
        d.update({"ir": V(inte), "is": P(0)})
    return d


def sh(v, ferme=True, i=None, o=None):
    i = i or [[0, 0]] * len(v)
    o = o or [[0, 0]] * len(v)
    return {"ty": "sh", "ks": P({"i": [list(x) for x in i], "o": [list(x) for x in o], "v": [list(x) for x in v], "c": ferme}), "d": 1}


def fl(h, o=100):
    return {"ty": "fl", "c": P(couleur(h)), "o": V(o), "r": 1}


def st(h, w, o=100):
    return {"ty": "st", "c": P(couleur(h)), "o": V(o), "w": V(w), "lc": 2, "lj": 2}


def tm(e=100, s=0):
    return {"ty": "tm", "s": V(s), "e": V(e), "o": P(0), "m": 1}


def gr(items, t=None):
    return {"ty": "gr", "it": list(items) + [t or tr()]}


def plein(formes, h, contour=10, t=None, o=100):
    """Formes pleines à contour blanc : le contour est dessiné dessous, il ne coupe jamais l'intérieur."""
    return gr([gr(formes + [fl(h, o)]), gr(formes + [st(BLANC, contour * 2)])] if contour else [gr(formes + [fl(h, o)])], t)


def trait(formes, h, w, t=None, trim=None, contour=8):
    """Formes tracées (contour seul) avec un liseré blanc ; trim = (début, fin) animés pour les tracer."""
    haut = formes + ([trim] if trim else []) + [st(h, w)]
    bas = formes + ([json.loads(json.dumps(trim))] if trim else []) + [st(BLANC, w + contour * 2)]
    return gr([gr(haut), gr(bas)] if contour else [gr(haut)], t)


def calque(formes, n, ks=None, ind=1):
    k = {"o": P(100), "r": P(0), "p": P([C, C, 0]), "a": P([C, C, 0]), "s": P([100, 100, 100])}
    k.update(ks or {})
    return {"ddd": 0, "ind": ind, "ty": 4, "nm": f"c{ind}", "sr": 1, "ks": k, "ao": 0, "shapes": list(formes), "ip": 0, "op": n, "st": 0, "bm": 0}


def anim(ident, n, calques):
    for i, c in enumerate(calques):
        c["ind"] = i + 1
    return {"v": "5.7.4", "fr": FR, "ip": 0, "op": n, "w": W, "h": W, "nm": ident, "ddd": 0, "assets": [], "layers": calques}


def cycle(n, pas):
    """Images clefs d'une boucle : [(0, a), (n/2, b), (n, a)] avec pas = [a, b, ...]."""
    m = len(pas)
    return [(round(n * i / m), pas[i]) for i in range(m)] + [(n, pas[0])]


def apparition(n, d=10, fin=100):
    """Echelle 0 → dépassement → 100 en d images (le « pop » des Goodies)."""
    return A([(0, [0, 0]), (d, [fin * 1.15, fin * 1.15]), (d + 5, [fin, fin])], (0.3, 0.7))


# ------------------------------------------------------------------ dessins de base
def coeur(x=0, y=0, k=1.0):
    v = [[x, y - 40 * k], [x, y + 100 * k]]
    o = [[70 * k, -100 * k], [-160 * k, -120 * k]]
    i = [[-70 * k, -100 * k], [160 * k, -120 * k]]
    return sh(v, True, i, o)


def arc(r, a0=180, a1=360, cx=0, cy=0, segs=4):
    """Arc de cercle (degrés, 0 = droite, sens horaire à l'écran)."""
    v, i, o = [], [], []
    pas = (a1 - a0) / segs
    k = 4 / 3 * math.tan(math.radians(pas) / 4) * r
    for s in range(segs + 1):
        a = math.radians(a0 + s * pas)
        px, py = cx + r * math.cos(a), cy + r * math.sin(a)
        tx, ty = -math.sin(a), math.cos(a)
        v.append([px, py])
        i.append([-tx * k, -ty * k])
        o.append([tx * k, ty * k])
    return sh(v, False, i, o)


def visage(couleur_peau="#ffcc33"):
    return plein([el(0, 0, 330)], couleur_peau, 9)


# ------------------------------------------------------------------ les éléments
E = {}


def element(ident, pack, noms, n, fin, calques, couleurs, desc=None):
    E[ident] = {"pack": pack, "nom": dict(zip(("fr", "en", "de", "es", "it"), noms)), "fin": fin, "couleurs": couleurs,
                "description": dict(zip(("fr", "en", "de", "es", "it"), desc)) if desc else None,
                "lottie": anim(ident, n, calques), "ajoute": "2026-11-09"}


def centre(formes, n, ks=None):
    return calque([gr(formes, tr(p=(C, C)))], n, ks)


ROUGE, ROSE, JAUNE, ORANGE, VERT, BLEU, VIOLET, CIEL, NOIR = "#ff3b5c", "#ff4fa3", "#ffd21f", "#ff8c1a", "#2ecc40", "#1e90ff", "#9b5de5", "#5ec8ff", "#222222"

# --- Réactions
n = 30
element("coeur_bat", "reactions", ["Cœur qui bat", "Beating heart", "Schlagendes Herz", "Corazón que late", "Cuore che batte"], n, "boucle",
        [centre([plein([coeur(0, -20, 1.25)], ROUGE, 10)], n, {"s": A(cycle(n, [[100, 100, 100], [118, 118, 100], [100, 100, 100], [110, 110, 100]]))})],
        [ROUGE])

n = 60
coeurs = []
for j, (dx, k, d) in enumerate([(-90, 0.45, 0), (40, 0.6, 12), (110, 0.4, 24), (-20, 0.5, 36), (-130, 0.35, 48)]):
    def kf(v0, v1, d=d):
        return [(0, v0), (d, v0), (d + 1, v0), (min(n, d + 40), v1), (n, v1)] if d + 40 <= n else [(0, v0), (d, v0), (n, v1)]
    pos = A([(0, [dx, 150]), ((d) % n, [dx, 150]), (min(n, d + 40), [dx + 25, -170]), (n, [dx + 25, -170])])
    coeurs.append(plein([coeur(0, 0, k)], ROUGE if j % 2 == 0 else ROSE, 7,
                        tr(p=pos, o=A([(0, 0), (d, 0), (d + 4, 100), (min(n, d + 30), 100), (min(n, d + 40), 0), (n, 0)]))))
element("coeurs_envol", "reactions", ["Cœurs qui s'envolent", "Floating hearts", "Aufsteigende Herzen", "Corazones que vuelan", "Cuori che volano"], n,
        "boucle", [calque([gr(coeurs, tr(p=(C, C)))], n)], [ROUGE, ROSE])

n = 40
eclats = []
for j, (x, y, t0, k) in enumerate([(-80, -60, 0, 1.0), (90, -20, 13, 0.7), (-10, 90, 26, 0.55)]):
    eclats.append(plein([sr(0, 0, 4, 90 * k, 22 * k)], JAUNE, 6,
                        tr(p=(x, y), s=A([(0, [20, 20]), ((t0) % n, [20, 20]), ((t0 + 10) % n or n, [100, 100]), ((t0 + 20) % n or n, [20, 20])] if t0 + 20 <= n else
                                         [(0, [70, 70]), (t0 + 20 - n, [20, 20]), (t0, [20, 20]), (t0 + 10, [100, 100]), (n, [70, 70])]),
                           r=A([(0, 0), (n, 90)]))))
element("etincelles", "reactions", ["Etincelles", "Sparkles", "Funkeln", "Destellos", "Scintille"], n, "boucle",
        [calque([gr(eclats, tr(p=(C, C)))], n)], [JAUNE])


def visage_el(ident, noms, yeux, bouche, n=40, ks=None, extra=()):
    element(ident, "reactions", noms, n, "boucle", [centre([*extra, *bouche, *yeux, visage()], n, ks)], ["#ffcc33"])


visage_el("emoji_rire", ["Visage qui rit", "Laughing face", "Lachendes Gesicht", "Cara que ríe", "Faccina che ride"],
          [trait([arc(28, 200, 340, -62, -20)], NOIR, 14, contour=0), trait([arc(28, 200, 340, 62, -20)], NOIR, 14, contour=0)],
          [plein([sh([[-95, 30], [95, 30], [0, 120]], True, [[0, 0], [0, 0], [70, 0]], [[0, 0], [0, 75], [-70, 0]])], "#7a1f1f", 0)],
          ks={"r": A(cycle(40, [-6, 6])), "p": A(cycle(40, [[C, C + 6, 0], [C, C - 10, 0]]))})
visage_el("emoji_wahou", ["Visage étonné", "Amazed face", "Staunendes Gesicht", "Cara asombrada", "Faccina stupita"],
          [plein([el(-60, -30, 50, 64)], NOIR, 0), plein([el(60, -30, 50, 64)], NOIR, 0)],
          [plein([el(0, 75, 70, 90)], "#7a1f1f", 0)], ks={"s": A(cycle(40, [[100, 100, 100], [112, 112, 100]]))})
visage_el("emoji_coeur", ["Yeux en cœur", "Heart eyes", "Herzaugen", "Ojos de corazón", "Occhi a cuore"],
          [plein([coeur(-62, -45, 0.42)], ROUGE, 0, tr(s=A(cycle(40, [[100, 100], [125, 125]])), a=(-62, -30), p=(-62, -30))),
           plein([coeur(62, -45, 0.42)], ROUGE, 0, tr(s=A(cycle(40, [[100, 100], [125, 125]])), a=(62, -30), p=(62, -30)))],
          [trait([arc(70, 20, 160, 0, 15)], NOIR, 14, contour=0)])
visage_el("emoji_clin", ["Clin d'œil", "Wink", "Zwinkern", "Guiño", "Occhiolino"],
          [plein([el(-60, -30, 44, 58)], NOIR, 0),
           gr([gr([el(60, -30, 44, 58), fl(NOIR)], tr(p=(60, -30), a=(60, -30), s=A([(0, [100, 100]), (14, [100, 100]), (18, [100, 8]), (26, [100, 8]), (30, [100, 100]), (40, [100, 100])])))])],
          [trait([arc(75, 25, 155, 0, 10)], NOIR, 14, contour=0)])

n = 24
flamme_ext = sh([[0, -170], [105, 40], [0, 150], [-105, 40]], True, [[0, 0], [10, -120], [80, 0], [0, 80]], [[60, 80], [0, 80], [-80, 0], [-10, -120]])
flamme_int = sh([[0, -60], [55, 60], [0, 130], [-55, 60]], True, [[0, 0], [5, -60], [40, 0], [0, 40]], [[30, 40], [0, 40], [-40, 0], [-5, -60]])
element("flamme", "reactions", ["Flamme", "Flame", "Flamme", "Llama", "Fiamma"], n, "boucle",
        [calque([gr([gr([flamme_int, fl(JAUNE)]), plein([flamme_ext], ORANGE, 9)], tr(p=(C, C + 165), a=(0, 150), s=A(cycle(n, [[100, 100], [94, 108], [104, 96]]))))], n)],
        [ORANGE, JAUNE])

n = 36
element("pouce", "reactions", ["Pouce levé", "Thumbs up", "Daumen hoch", "Pulgar arriba", "Pollice in su"], n, "boucle",
        [centre([plein([rc(-150, 40, 60, 170, 14)], BLEU, 9),
                 plein([rc(15, 45, 220, 170, 50), rc(-40, -70, 70, 160, 35)], JAUNE, 9),
                 trait([sh([[40, -5], [120, -5]], False), sh([[40, 45], [125, 45]], False), sh([[40, 95], [115, 95]], False)], "#c79a00", 10, contour=0)],
                n, {"s": apparition(n, 8), "r": A([(0, -25), (10, 5), (18, -8), (26, 0), (n, 0)])})],
        [JAUNE, BLEU])

# --- Flèches et repères
n = 45


def fleche_tracee(ident, noms, chemin, tete_p, tete_r, h=ROUGE):
    tete = plein([sh([[0, -38], [55, 0], [0, 38]])], h, 8, tr(p=tete_p, r=tete_r, s=A([(0, [0, 0]), (17, [0, 0]), (22, [120, 120]), (26, [100, 100])])))
    element(ident, "reperes", noms, n, "tenir", [calque([gr([tete, trait([chemin], h, 22, trim=tm(A([(0, 0), (20, 100)])))], tr(p=(C, C)))], n)], [h])


fleche_tracee("fleche_courbe", ["Flèche courbe qui se trace", "Curved arrow drawing itself", "Gebogener Pfeil, der sich zeichnet",
                                "Flecha curva que se dibuja", "Freccia curva che si disegna"],
              sh([[-180, 120], [150, -60]], False, [[0, 0], [-60, 140]], [[60, -220], [0, 0]]), (150, -60), 15)
fleche_tracee("fleche_droite", ["Flèche droite qui se trace", "Straight arrow drawing itself", "Gerader Pfeil, der sich zeichnet",
                                "Flecha recta que se dibuja", "Freccia dritta che si disegna"],
              sh([[-190, 0], [150, 0]], False), (150, 0), 0, ORANGE)
fleche_tracee("fleche_boucle", ["Flèche avec boucle", "Looping arrow", "Pfeil mit Schleife", "Flecha con bucle", "Freccia con anello"],
              sh([[-200, 60], [-20, -40], [40, 60], [170, -30]], False, [[0, 0], [-60, -10], [90, 0], [-70, 40]], [[80, 0], [70, 15], [-80, 10], [0, 0]]),
              (170, -30), -30, ROSE)

n = 40
cercle_main = sh([[0, -150], [190, -10], [10, 140], [-185, 0], [30, -165]], False,
                 [[-80, 0], [0, -90], [100, 0], [0, 90], [-90, 0]], [[110, 0], [0, 90], [-110, 0], [0, -100], [0, 0]])
element("cercle_trace", "reperes", ["Cercle tracé à la main", "Hand-drawn circle", "Handgezeichneter Kreis", "Círculo a mano", "Cerchio a mano"],
        n, "tenir", [calque([trait([cercle_main], ROUGE, 18, tr(p=(C, C)), tm(A([(0, 0), (22, 100)])))], n)], [ROUGE])
element("souligne", "reperes", ["Soulignement", "Underline", "Unterstreichung", "Subrayado", "Sottolineatura"], n, "tenir",
        [calque([trait([sh([[-210, 10], [-70, -10], [70, 15], [210, -5]], False, [[0, 0], [-50, 25], [-50, -25], [-40, 15]],
                           [[50, -25], [50, 25], [40, -15], [0, 0]])], JAUNE, 26, tr(p=(C, C)), tm(A([(0, 0), (16, 100)])))], n)], [JAUNE])
element("coche", "reperes", ["Coche (validé)", "Check mark", "Häkchen", "Marca de verificación", "Spunta"], n, "tenir",
        [calque([gr([trait([sh([[-80, 5], [-20, 65], [90, -60]], False)], BLANC, 34, trim=tm(A([(0, 0), (12, 0), (26, 100)])), contour=0),
                     plein([el(0, 0, 330)], VERT, 10)], tr(p=(C, C), s=apparition(n, 9)))], n)], [VERT])
element("croix_non", "reperes", ["Croix (refusé)", "Cross", "Kreuz", "Cruz", "Croce"], n, "tenir",
        [calque([gr([trait([sh([[-70, -70], [70, 70]], False)], BLANC, 34, trim=tm(A([(0, 0), (11, 0), (19, 100)])), contour=0),
                     trait([sh([[70, -70], [-70, 70]], False)], BLANC, 34, trim=tm(A([(0, 0), (18, 0), (26, 100)])), contour=0),
                     plein([el(0, 0, 330)], ROUGE, 10)], tr(p=(C, C), s=apparition(n, 9)))], n)], [ROUGE])
n = 36
element("exclamation", "reperes", ["Point d'exclamation", "Exclamation mark", "Ausrufezeichen", "Signo de exclamación", "Punto esclamativo"],
        n, "boucle", [calque([plein([rc(0, -50, 70, 220, 35), el(0, 130, 76)], ORANGE, 10, tr(p=(C, C), r=A(cycle(n, [0, -10, 0, 10]))))], n)],
        [ORANGE])
element("interrogation", "reperes", ["Point d'interrogation", "Question mark", "Fragezeichen", "Signo de interrogación", "Punto interrogativo"],
        n, "boucle", [calque([gr([plein([el(0, 140, 70)], VIOLET, 9),
                                  trait([sh([[-80, -80], [0, -160], [80, -80], [0, 10], [0, 60]], False,
                                            [[0, 0], [-60, 0], [0, -60], [20, -30], [0, 0]], [[0, -60], [60, 0], [0, 50], [0, 0], [0, 0]])], VIOLET, 48)],
                                 tr(p=A(cycle(n, [[C, C + 8], [C, C - 12]]))))], n)], [VIOLET])
n = 40
anneaux = [plein([el(0, 0, 50)], BLANC, 0), plein([el(0, 0, 130)], ROUGE, 0), plein([el(0, 0, 210)], BLANC, 0), plein([el(0, 0, 300)], ROUGE, 8)]
element("cible", "reperes", ["Cible", "Target", "Zielscheibe", "Diana", "Bersaglio"], n, "boucle",
        [calque([gr([trait([sh([[-200, 0], [-120, 0]], False), sh([[120, 0], [200, 0]], False), sh([[0, -200], [0, -120]], False),
                            sh([[0, 120], [0, 200]], False)], ROUGE, 12), *anneaux],
                    tr(p=(C, C), s=A(cycle(n, [[100, 100], [90, 90]])), r=A([(0, 0), (n, 90)])))], n)], [ROUGE])
n = 40
curseur = plein([sh([[0, 0], [0, 150], [38, 116], [66, 172], [92, 160], [64, 106], [112, 106]])], NOIR, 9)
ondes_clic = [trait([el(0, 0, A([(0, 20), (12, 20), (30, 200), (n, 200)]))], BLEU, 10, tr(o=A([(0, 0), (12, 0), (14, 100), (30, 0), (n, 0)])), contour=0)]
element("clic", "reperes", ["Curseur qui clique", "Clicking cursor", "Klickender Mauszeiger", "Cursor que hace clic", "Cursore che clicca"], n,
        "boucle", [calque([gr(ondes_clic, tr(p=(C - 10, C - 10))),
                           gr([curseur], tr(p=A([(0, [C + 120, C + 120]), (10, [C - 10, C - 10]), (n, [C - 10, C - 10])]),
                                            s=A([(0, [100, 100]), (10, [100, 100]), (12, [85, 85]), (16, [100, 100]), (n, [100, 100])])))], n)],
        [BLEU])
n = 30
chevrons = [trait([sh([[-60, -40], [0, 20], [60, -40]], False)], BLANC, 28, tr(p=(0, 90 - 70 * j), o=A(cycle(n, [30 if k != j else 100 for k in range(3)]))),
                  contour=0) for j in range(3)]
element("chevrons", "reperes", ["Chevrons (glisser vers le haut)", "Swipe-up chevrons", "Nach-oben-Pfeile", "Chevrones (deslizar)", "Frecce in su"], n,
        "boucle", [calque([gr([*chevrons, plein([rc(0, 20, 190, 300, 95)], BLEU, 8)], tr(p=(C, C)))], n)], [BLEU])

# --- Vlog et réseaux
n = 30
element("point_rec", "vlog", ["Point d'enregistrement", "Recording dot", "Aufnahmepunkt", "Punto de grabación", "Punto di registrazione"], n, "boucle",
        [calque([gr([plein([el(0, 0, 150)], ROUGE, 0, tr(o=A(cycle(n, [100, 100, 15, 15])))),
                     trait([el(0, 0, 230)], ROUGE, 16, contour=0), plein([el(0, 0, 290)], NOIR, 0, o=45)], tr(p=(C, C)))], n)], [ROUGE])
n = 40
cloche = sh([[0, -150], [95, -40], [140, 90], [-140, 90], [-95, -40]], True,
            [[-55, 0], [0, -70], [-20, -50], [0, 0], [0, 50]], [[55, 0], [0, 50], [0, 0], [20, -50], [0, -70]])
element("cloche", "vlog", ["Cloche de notification", "Notification bell", "Benachrichtigungsglocke", "Campana de notificaciones", "Campanella notifiche"],
        n, "boucle", [calque([gr([plein([el(0, 120, 70)], ORANGE, 8, tr(p=A(cycle(n, [[0, 0], [14, 0], [0, 0], [-14, 0]])))),
                                  plein([cloche, rc(0, 90, 300, 40, 20)], JAUNE, 10)],
                                 tr(p=(C, C - 150), a=(0, -150), r=A([(0, 0), (5, 18), (10, -16), (15, 12), (20, -8), (25, 0), (n, 0)])))], n)],
        [JAUNE])
n = 45
points = [plein([el(-70 + 70 * j, 0, 44)], BLANC, 0, tr(p=A([(0, [0, 0]), (6 * j, [0, 0]), (6 * j + 6, [0, -24]), (6 * j + 12, [0, 0]), (n, [0, 0])]))) for j in range(3)]
element("bulle_dialogue", "vlog", ["Bulle qui écrit", "Typing bubble", "Tippende Sprechblase", "Burbuja escribiendo", "Fumetto che scrive"], n, "boucle",
        [calque([gr([*points, plein([rc(0, -20, 340, 220, 90), sh([[-90, 60], [-130, 150], [-20, 80]])], BLEU, 10)],
                    tr(p=(C, C), s=apparition(n, 8)))], n)], [BLEU])
element("bulle_coeur", "vlog", ["Bulle cœur (j'aime)", "Like bubble", "Herz-Blase", "Burbuja de me gusta", "Fumetto mi piace"], n, "boucle",
        [calque([gr([plein([coeur(0, -30, 0.6)], BLANC, 0, tr(p=(0, -10), a=(0, -10), s=A(cycle(n, [[100, 100], [120, 120]])))),
                     plein([rc(0, -20, 280, 220, 70), sh([[-20, 80], [0, 150], [30, 80]])], ROUGE, 10)], tr(p=(C, C), s=apparition(n, 8)))], n)], [ROUGE])
n = 30
element("chargement", "vlog", ["Chargement", "Loading spinner", "Ladekreis", "Cargando", "Caricamento"], n, "boucle",
        [calque([gr([trait([el(0, 0, 260)], BLEU, 34, trim=tm(A(cycle(n, [70, 95])), A(cycle(n, [0, 40]))), contour=0),
                     trait([el(0, 0, 260)], "#d0d8e8", 34, contour=6)], tr(p=(C, C), r=A([(0, 0), (n, 360)], (0, 1))))], n)], [BLEU])
n = 50
epingle = sh([[0, 150], [-110, -40], [0, -160], [110, -40]], True, [[0, 0], [0, 60], [-60, 0], [0, -60]], [[-60, -70], [0, -60], [60, 0], [60, -70]])
element("epingle", "vlog", ["Epingle de lieu", "Location pin", "Ortsnadel", "Chincheta de lugar", "Segnaposto"], n, "tenir",
        [calque([gr([plein([el(0, 200, A([(0, 20), (14, 160), (18, 200), (24, 170), (n, 170)]), 34)], NOIR, 0, o=35)], tr(p=(C, C))),
                 gr([plein([el(0, -50, 90)], BLANC, 0), plein([epingle], ROUGE, 10)],
                    tr(p=A([(0, [C, C - 300]), (14, [C, C]), (20, [C, C - 40]), (26, [C, C]), (n, [C, C])], (0.4, 0.9))))], n)], [ROUGE])
n = 60
silhouette = [rc(0, 0, 300, 52, 26), sh([[-10, -20], [-60, -170], [-20, -170], [70, -20]]), sh([[-10, 20], [-60, 170], [-20, 170], [70, 20]]),
              sh([[-120, -10], [-150, -70], [-125, -70], [-95, -10]]), sh([[-120, 10], [-150, 70], [-125, 70], [-95, 10]])]
trainee = [trait([sh([[-330, 0], [-180, 0]], False)], BLANC, 8, tr(p=(0, dy), o=55), contour=0) for dy in (-60, 60)]
element("avion", "vlog", ["Avion qui passe", "Passing plane", "Vorbeifliegendes Flugzeug", "Avión que pasa", "Aereo che passa"], n, "boucle",
        [calque([gr([plein(silhouette, BLEU, 8), *trainee], tr(p=A([(0, [-200, C + 40]), (n, [W + 200, C - 40])], (0, 1)), r=-8, s=(55, 55)))], n)], [BLEU])
n = 60
graduations = [trait([sh([[0, -120], [0, -100]], False)], NOIR, 10, tr(r=30 * j), contour=0) for j in range(12)]
element("horloge", "vlog", ["Horloge (le temps passe)", "Clock (time passing)", "Uhr (die Zeit vergeht)", "Reloj (pasa el tiempo)", "Orologio (il tempo passa)"],
        n, "boucle", [calque([gr([plein([el(0, 0, 26)], NOIR, 0),
                                  trait([sh([[0, 0], [0, -105]], False)], ROUGE, 10, tr(r=A([(0, 0), (n, 720)], (0, 1))), contour=0),
                                  trait([sh([[0, 0], [0, -70]], False)], NOIR, 16, tr(r=A([(0, 0), (n, 60)], (0, 1))), contour=0),
                                  *graduations, plein([el(0, 0, 290)], BLANC, 0), plein([el(0, 0, 330)], BLEU, 8)], tr(p=(C, C)))], n)], [BLEU])
n = 50
element("loupe", "vlog", ["Loupe", "Magnifier", "Lupe", "Lupa", "Lente"], n, "boucle",
        [calque([gr([plein([el(-35, -45, 60, 40)], BLANC, 0, o=70), trait([el(0, 0, 220)], VIOLET, 34),
                     plein([el(0, 0, 220)], CIEL, 0, o=45), plein([rc(0, 0, 160, 50, 25)], VIOLET, 9, tr(p=(130, 130), r=45))],
                    tr(p=A(cycle(n, [[C - 20, C - 10], [C + 20, C + 10], [C + 10, C - 20]])), r=A(cycle(n, [-6, 6]))))], n)], [VIOLET])

# --- Météo et nature
n = 60
rayons = [plein([rc(0, -175, 34, 80, 17)], ORANGE, 0, tr(r=30 * j)) for j in range(12)]
element("soleil", "meteo", ["Soleil", "Sun", "Sonne", "Sol", "Sole"], n, "boucle",
        [calque([gr([plein([el(0, 0, 210)], JAUNE, 10, tr(s=A(cycle(n, [[100, 100], [108, 108]])))), gr(rayons, tr(r=A([(0, 0), (n, 30)], (0, 1))))],
                    tr(p=(C, C)))], n)], [JAUNE, ORANGE])
nuage_formes = [el(-80, 30, 160), el(10, -20, 200), el(100, 35, 150), rc(10, 70, 300, 90, 45)]
element("nuage", "meteo", ["Nuage", "Cloud", "Wolke", "Nube", "Nuvola"], n, "boucle",
        [calque([plein(nuage_formes, "#e9f2ff", 10, tr(p=A(cycle(n, [[C - 15, C], [C + 15, C - 8]]))))], n)], ["#e9f2ff"])
n = 30
gouttes = [plein([sh([[0, -25], [16, 10], [0, 26], [-16, 10]], True, [[0, 0], [0, -14], [10, 0], [0, 10]], [[6, 12], [0, 10], [-10, 0], [-6, -14]])],
                 BLEU, 0, tr(p=A([(0, [x, 90 + o]), (n, [x - 20, 240 + o])], (0, 1)), o=A([(0, 100), (int(n * 0.8), 100), (n, 0)])))
           for x, o in ((-90, 0), (-20, 40), (50, -10), (120, 30))]
element("pluie", "meteo", ["Pluie", "Rain", "Regen", "Lluvia", "Pioggia"], n, "boucle",
        [calque([gr([plein([el(-80, -50, 150), el(10, -95, 190), el(100, -45, 140), rc(10, -5, 290, 80, 40)], "#c8d6ea", 9), *gouttes], tr(p=(C, C - 20)))], n)],
        ["#c8d6ea", BLEU])
n = 30
element("eclair", "meteo", ["Eclair", "Lightning bolt", "Blitz", "Rayo", "Fulmine"], n, "boucle",
        [calque([plein([sh([[40, -190], [-90, 20], [0, 20], [-50, 190], [100, -40], [10, -40], [70, -190]])], JAUNE, 10,
                       tr(p=(C, C), o=A([(0, 100), (3, 30), (5, 100), (8, 40), (10, 100), (n, 100)]), s=A(cycle(n, [[100, 100], [106, 106]]))))], n)], [JAUNE])
n = 90
branche = [sh([[0, 0], [0, -170]], False), sh([[0, -110], [-40, -150]], False), sh([[0, -110], [40, -150]], False),
           sh([[0, -60], [-30, -90]], False), sh([[0, -60], [30, -90]], False)]
element("flocon", "meteo", ["Flocon", "Snowflake", "Schneeflocke", "Copo de nieve", "Fiocco di neve"], n, "boucle",
        [calque([gr([trait(branche, CIEL, 18, tr(r=60 * j)) for j in range(6)], tr(p=(C, C), r=A([(0, 0), (n, 120)], (0, 1)),
                                                                                    s=A(cycle(n, [[100, 100], [92, 92]]))))], n)], [CIEL])
n = 45
couleurs_arc = ["#ff3b30", "#ff8c1a", "#ffd21f", "#2ecc40", "#1e90ff", "#9b5de5"]
element("arc_en_ciel", "meteo", ["Arc-en-ciel", "Rainbow", "Regenbogen", "Arcoíris", "Arcobaleno"], n, "tenir",
        [calque([gr([trait([arc(200 - 26 * j)], c, 26, trim=tm(A([(0, 0), (3 * j, 0), (3 * j + 22, 100)])), contour=0) for j, c in enumerate(couleurs_arc)]
                    + [trait([arc(200 - 26 * j) for j in range(6)], BLANC, 44, trim=tm(A([(0, 0), (22, 100)])), contour=0)], tr(p=(C, C + 90)))], n)],
        couleurs_arc)

# --- Fête animée
n = 50


def gerbe(cx, cy, t0, h, rayon=170):
    traits_ = []
    for j in range(12):
        traits_.append(trait([sh([[0, -30], [0, -rayon]], False)], h, 12,
                             tr(r=30 * j), tm(A([(0, 0), (t0, 0), (t0 + 14, 100), (n, 100)]), A([(0, 0), (t0 + 6, 0), (t0 + 24, 100), (n, 100)])), contour=0))
    return gr(traits_, tr(p=(cx, cy)))


element("feu_artifice", "fete", ["Feu d'artifice", "Fireworks", "Feuerwerk", "Fuegos artificiales", "Fuochi d'artificio"], n, "boucle",
        [calque([gr([gerbe(-70, -40, 0, JAUNE), gerbe(90, 50, 14, ROSE, 130), gerbe(-40, 110, 24, CIEL, 100)], tr(p=(C, C)))], n)], [JAUNE, ROSE, CIEL])
n = 90
ballons = []
for j, (x, h, d) in enumerate([(-110, ROUGE, 0), (0, JAUNE, 25), (110, BLEU, 50)]):
    corps = [plein([el(0, 0, 130, 160), sh([[0, 78], [14, 98], [-14, 98]])], h, 8),
             plein([el(-28, -35, 26, 40)], BLANC, 0, o=60)]
    fil = trait([sh([[0, 98], [0, 230]], False, [[0, 0], [20, -40]], [[-20, 40], [0, 0]])], "#666666", 4, contour=0)
    ballons.append(gr([*corps, fil], tr(p=A([(0, [x, 260]), (d, [x, 260]), (d + 1, [x, 260]), (min(n, d + 80), [x + 20, -330]), (n, [x + 20, -330])]
                                              if d + 80 <= n else [(0, [x + 10, -60]), (d + 80 - n, [x + 20, -330]), (d, [x, 260]), (n, [x + 10, -60])], (0.2, 0.8)),
                                        r=A(cycle(n, [-8, 8])))))
element("ballons", "fete", ["Ballons qui montent", "Rising balloons", "Aufsteigende Ballons", "Globos que suben", "Palloncini che salgono"], n, "boucle",
        [calque([gr(ballons, tr(p=(C, C)))], n)], [ROUGE, JAUNE, BLEU])
n = 45
element("etoile_filante", "fete", ["Etoile filante", "Shooting star", "Sternschnuppe", "Estrella fugaz", "Stella cadente"], n, "boucle",
        [calque([gr([plein([sr(0, 0, 5, 60, 26)], JAUNE, 8, tr(r=A([(0, 0), (n, 180)]))),
                     trait([sh([[-40, 0], [-260, 0]], False)], JAUNE, 26, tr(o=60), contour=0),
                     trait([sh([[-40, -20], [-200, -40]], False), sh([[-40, 20], [-200, 40]], False)], BLANC, 10, tr(o=60), contour=0)],
                    tr(p=A([(0, [-150, C - 160]), (n, [W + 150, C + 140])], (0, 1)), r=33))], n)], [JAUNE])
n = 50
element("cadeau", "fete", ["Cadeau qui s'ouvre", "Opening gift", "Sich öffnendes Geschenk", "Regalo que se abre", "Regalo che si apre"], n, "tenir",
        [calque([gr([*[plein([sr(x, y, 4, 40, 10)], JAUNE, 5, tr(s=A([(0, [0, 0]), (20, [0, 0]), (28, [130, 130]), (36, [90, 90])]), a=(x, y), p=(x, y)))
                        for x, y in ((-120, -170), (0, -230), (120, -170))],
                     gr([plein([rc(0, -90, 290, 60, 10)], ROUGE, 9), plein([rc(0, -90, 50, 60, 0)], JAUNE, 0)],
                        tr(p=A([(0, [0, 0]), (14, [0, 0]), (22, [40, -120]), (n, [40, -120])], (0.3, 0.9)), r=A([(0, 0), (14, 0), (22, 25), (n, 25)]))),
                     plein([rc(0, 50, 60, 220, 0)], JAUNE, 0), plein([rc(0, 50, 260, 220, 10)], ROUGE, 9)],
                    tr(p=(C, C + 40), s=A([(0, [100, 100]), (6, [110, 90]), (12, [95, 105]), (14, [100, 100]), (n, [100, 100])])))], n)], [ROUGE, JAUNE])
n = 36
element("explosion_bd", "fete", ["Explosion de BD", "Comic burst", "Comic-Explosion", "Explosión de cómic", "Esplosione fumetto"], n, "tenir",
        [calque([gr([plein([sr(0, 0, 12, 120, 70)], ROUGE, 0, tr(r=15)), plein([sr(0, 0, 12, 200, 120)], JAUNE, 10)],
                    tr(p=(C, C), s=apparition(n, 8), r=A([(0, -30), (8, 4), (16, -3), (24, 0), (n, 0)])))], n)], [JAUNE, ROUGE])

# --- Formes animées
n = 60
ondes = [trait([el(0, 0, 360)], CIEL, 14, tr(s=A([(0, [10, 10]), ((20 * j) % n, [10, 10]), ((20 * j) % n + 40, [100, 100]), (n, [100, 100])]
                                                 if 20 * j + 40 <= n else [(0, [70, 70]), (20 * j + 40 - n, [100, 100]), (20 * j + 40 - n + 1, [10, 10]), (20 * j, [10, 10]), (n, [70, 70])]),
                                           o=A([(0, 100), ((20 * j) % n, 100), ((20 * j) % n + 40, 0), (n, 0)] if 20 * j + 40 <= n else
                                               [(0, 30), (20 * j + 40 - n, 0), (20 * j + 40 - n + 1, 100), (20 * j, 100), (n, 30)])), contour=0) for j in range(3)]
element("onde", "formes", ["Ondes", "Ripples", "Wellen", "Ondas", "Onde"], n, "boucle", [calque([gr(ondes, tr(p=(C, C)))], n)], [CIEL])
n = 90
bulles = [gr([plein([el(-14, -14, 14 * k, 14 * k)], BLANC, 0, o=80), trait([el(0, 0, 60 * k)], CIEL, 6, contour=0), plein([el(0, 0, 60 * k)], CIEL, 0, o=25)],
             tr(p=A([(0, [x, 200]), (n, [x + 30 * math.sin(j), -190])], (0, 1)) if j % 2 == 0 else
                A([(0, [x, 5]), (n // 2, [x + 20, -190]), (n // 2 + 1, [x, 200]), (n, [x, 5])], (0, 1)),
                o=A([(0, 0), (8, 100), (n - 10, 100), (n, 0)]) if j % 2 == 0 else A([(0, 100), (n // 2 - 8, 100), (n // 2, 0), (n // 2 + 1, 0), (n // 2 + 8, 100), (n, 100)])))
          for j, (x, k) in enumerate([(-120, 1.2), (-40, 0.8), (40, 1.5), (120, 1.0), (0, 0.6), (-90, 0.7)])]
element("bulles", "formes", ["Bulles", "Bubbles", "Blasen", "Burbujas", "Bolle"], n, "boucle", [calque([gr(bulles, tr(p=(C, C)))], n)], [CIEL])
n = 40
element("pastille_pulse", "formes", ["Pastille qui pulse", "Pulsing badge", "Pulsierendes Abzeichen", "Insignia que late", "Bollino pulsante"], n, "boucle",
        [calque([gr([trait([el(0, 0, 300)], ROSE, 12, tr(s=A([(0, [100, 100]), (n, [135, 135])]), o=A([(0, 100), (n, 0)])), contour=0),
                     plein([el(0, 0, 300)], ROSE, 10, tr(s=A(cycle(n, [[100, 100], [106, 106]]))))], tr(p=(C, C)))], n)], [ROSE])

PACKS = {
    "reactions": ["Réactions et emoji", "Reactions and emoji", "Reaktionen und Emoji", "Reacciones y emoji", "Reazioni ed emoji"],
    "reperes": ["Flèches et repères animés", "Animated arrows and markers", "Animierte Pfeile und Markierungen", "Flechas y marcas animadas",
                "Frecce e segni animati"],
    "vlog": ["Vlog et réseaux", "Vlog and social", "Vlog und soziale Netzwerke", "Vlog y redes", "Vlog e social"],
    "meteo": ["Météo et nature", "Weather and nature", "Wetter und Natur", "Tiempo y naturaleza", "Meteo e natura"],
    "fete": ["Fête animée", "Party", "Party", "Fiesta", "Festa"],
    "formes": ["Formes animées", "Animated shapes", "Animierte Formen", "Formas animadas", "Forme animate"],
}
DESC_PACK = ["Eléments animés vectoriels : nets à toute taille, couleurs modifiables, identiques sur PC et téléphone.",
             "Animated vector elements: sharp at any size, colours you can change, identical on PC and phone.",
             "Animierte Vektorelemente: scharf in jeder Größe, Farben änderbar, auf PC und Handy identisch.",
             "Elementos vectoriales animados: nítidos a cualquier tamaño, colores modificables, idénticos en PC y teléfono.",
             "Elementi vettoriali animati: nitidi a ogni dimensione, colori modificabili, identici su PC e telefono."]

if __name__ == "__main__":
    langues = ("fr", "en", "de", "es", "it")
    sortie = {"_commentaire": "Eléments animés de PhilCut (Lottie, 512×512, 30 i/s). Produit par outils_dev/fabriquer_elements.py ; "
                              "« couleurs » : couleurs principales, remplaçables ; « fin » : boucle (recommence) ou tenir (reste sur la dernière "
                              "image). « source » : philcut (dessins originaux) ou le nom de la banque gratuite et sa licence.",
              "maj": time.strftime("%Y-%m-%d"),
              "packs": {k: {"nom": dict(zip(langues, v)), "description": dict(zip(langues, DESC_PACK))} for k, v in PACKS.items()},
              "elements": {k: dict(v, source="philcut") for k, v in E.items()}}
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogue", "elements.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(sortie, f, ensure_ascii=False, separators=(",", ":"))
    print(len(E), "éléments,", os.path.getsize(p) // 1024, "Ko")
