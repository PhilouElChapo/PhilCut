"""Quand un moteur d'IA locale échoue : trouver pourquoi et proposer la solution (0.9.9).

Les moteurs (musique, images, agrandissement…) sont des programmes à part ; quand ils s'arrêtent, Windows ne donne qu'un
code (3221225781…). On le traduit en clair, avec ce qu'on peut faire, sous forme de boutons : installer le composant
Microsoft qui manque, passer sur le processeur, réinstaller le moteur, mettre à jour le pilote, voir le journal.

diagnostiquer(texte, genre) → {"titre", "explication", "actions": [(id, libellé)], "code"}
"""
import re

from .langue import _

# codes d'arrêt Windows (NTSTATUS), tels que le programme les renvoie (non signés)
DLL_MANQUANTE = 0xC0000135          # 3221225781 : une bibliothèque (DLL) est introuvable
POINT_ENTREE = 0xC0000139           # 3221225785 : DLL présente mais trop ancienne
ARRET_BRUTAL = 0xC0000409           # 3221226505 : arrêt d'urgence du programme (souvent pilote graphique, ou mémoire)
ACCES = 0xC0000005                  # 3221225477 : accès mémoire interdit (pilote, carte graphique, fichier abîmé)
INSTRUCTION = 0xC000001D            # 3221225501 : processeur trop ancien pour ce moteur (AVX2)
PILE = 0xC00000FD                   # 3221225725 : débordement de pile
MEMOIRE = 0xC0000017                # 3221225495 : plus assez de mémoire

LIEN_VCREDIST = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
LIEN_NVIDIA = "https://www.nvidia.com/fr-fr/drivers/"
LIEN_AMD = "https://www.amd.com/fr/support/download/drivers.html"
LIEN_INTEL = "https://www.intel.fr/content/www/fr/fr/support/detect.html"


def code_arret(texte):
    """Code d'arrêt du moteur lu dans le message (« code 3221225781 » ou « code -1073741515 »), non signé ; None sinon."""
    m = re.search(r"code\s*\(?\s*(-?\d+)", str(texte or ""))
    if not m:
        return None
    return int(m.group(1)) & 0xFFFFFFFF


def cartes_vulkan(lignes):
    """Cartes vues par un moteur ncnn/Vulkan (« [0 Intel(R) UHD Graphics]  queueC=… ») : [(indice, nom)]."""
    vues = {}
    for l in lignes if isinstance(lignes, (list, tuple)) else str(lignes or "").splitlines():
        m = re.match(r"\s*\[(\d+)\s+([^\]]+)\]", l)
        if m:
            vues.setdefault(int(m.group(1)), m.group(2).strip())
    return sorted(vues.items())


def est_dediee(nom):
    n = (nom or "").lower()
    return any(x in n for x in ("nvidia", "geforce", "rtx", "quadro", "radeon rx", "radeon pro", "arc a", "arc b")) and "uhd" not in n


def carte_dediee(lignes):
    """Indice de la carte dédiée (Nvidia, AMD) parmi celles vues par le moteur Vulkan, ou None."""
    for i, nom in cartes_vulkan(lignes):
        if est_dediee(nom):
            return i
    return None


# ------------------------------------------------------------------ quelle DLL manque (0.9.10)
def imports_pe(chemin):
    """Bibliothèques (DLL) qu'un programme Windows (.exe, .dll) demande : table des imports, et imports différés."""
    import struct
    with open(chemin, "rb") as f:
        b = f.read()
    if len(b) < 64 or b[:2] != b"MZ":
        return []
    u16 = lambda o: struct.unpack_from("<H", b, o)[0]
    u32 = lambda o: struct.unpack_from("<I", b, o)[0]
    pe = u32(0x3C)
    nsec, taille_opt = u16(pe + 6), u16(pe + 20)
    opt = pe + 24
    dd = opt + (112 if u16(opt) == 0x20B else 96)
    secs = opt + taille_opt

    def decalage(rva):
        for i in range(nsec):
            s_ = secs + 40 * i
            va, taille = u32(s_ + 12), max(u32(s_ + 8), u32(s_ + 16))
            if va <= rva < va + taille:
                return rva - va + u32(s_ + 20)
        return -1
    noms = set()
    for entree, pas, champ in ((1, 20, 12), (13, 32, 4)):
        rva = u32(dd + 8 * entree)
        o = decalage(rva) if rva else -1
        while 0 < o and o + pas <= len(b):
            n = u32(o + champ)
            if not n:
                break
            p_ = decalage(n)
            if p_ < 0:
                break
            noms.add(b[p_:b.index(b"\0", p_)].decode("ascii", "replace"))
            o += pas
    return sorted(noms)


def dll_manquantes(dossier, chemins=None):
    """{dll: [programmes qui la demandent]} pour les DLL demandées par les .exe et .dll du dossier et introuvables
    (ni dans le dossier, ni dans Windows › System32, ni dans le PATH). Windows seulement ; {} ailleurs."""
    import os
    import sys
    if not dossier or not os.path.isdir(dossier) or (chemins is None and sys.platform != "win32"):
        return {}
    fichiers = []
    for base, _s, noms in os.walk(dossier):
        fichiers += [os.path.join(base, n) for n in noms if n.lower().endswith((".exe", ".dll"))]
    locaux = {os.path.basename(f).lower() for f in fichiers}
    if chemins is None:
        chemins = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32")] + [c for c in os.environ.get("PATH", "").split(os.pathsep) if c]
    presents = {}
    manque = {}
    for f in fichiers:
        try:
            demandes = imports_pe(f)
        except (OSError, ValueError, IndexError, Exception):      # noqa: BLE001 : fichier illisible, on passe
            continue
        for d in demandes:
            dl = d.lower()
            if dl.startswith(("api-ms-", "ext-ms-")) or dl in locaux:
                continue
            if dl not in presents:
                presents[dl] = any(os.path.exists(os.path.join(c, d)) for c in chemins)
            if not presents[dl]:
                manque.setdefault(d, set()).add(os.path.basename(f))
    return {k: sorted(v) for k, v in manque.items()}


def famille_dll(nom):
    """D'où vient une DLL : « vcredist », « pilote_nvidia », « pilote », « moteur »."""
    n = nom.lower()
    if n.startswith(("vcruntime140", "msvcp140", "concrt140", "vcomp140", "vccorlib140", "msvcp_win")):
        return "vcredist"
    if n.startswith(("nvcuda", "nvml", "nvapi")):
        return "pilote_nvidia"
    if n.startswith(("vulkan-1", "opencl")):
        return "pilote"
    return "moteur"


def _pilote(texte):
    t = (texte or "").lower()
    if "nvidia" in t or "geforce" in t or "rtx" in t:
        return ("pilote_nvidia", _("Mettre à jour le pilote Nvidia"))
    if "radeon" in t or "amd" in t:
        return ("pilote_amd", _("Mettre à jour le pilote AMD"))
    return ("pilote_intel", _("Mettre à jour le pilote graphique"))


def diagnostiquer(texte, genre=None, manquantes=None):
    """manquantes : {dll: [programmes]} déjà cherchées ; sinon cherchées dans le dossier du moteur (genre) si c'est une DLL."""
    texte = str(texte or "")
    bas = texte.lower()
    code = code_arret(texte)
    actions = []
    if manquantes is None and code in (DLL_MANQUANTE, POINT_ENTREE) and genre:
        try:
            from . import packs_ia as P
            manquantes = dll_manquantes(P.dossier_moteur(genre))
        except Exception:      # noqa: BLE001
            manquantes = {}
    manquantes = manquantes or {}
    if code in (DLL_MANQUANTE, POINT_ENTREE) and manquantes:
        familles = {famille_dll(d) for d in manquantes}
        liste = ", ".join(sorted(manquantes))
        if "vcredist" in familles:
            titre = _("Il manque {d} : Visual C++ de Microsoft", d=liste)
            explication = _("Le moteur a besoin de « Visual C++ 2015-2022 » de Microsoft (gratuit, officiel), absent ou trop ancien "
                            "sur ce poste. L'installer ne change rien aux logiciels qui marchent déjà : les anciennes versions restent "
                            "à côté. Ensuite, « Réessayer ».")
            actions = [("vcredist", _("Installer Visual C++ (Microsoft)"))]
        elif familles == {"pilote_nvidia"}:
            titre = _("Il manque {d} : pilote Nvidia", d=liste)
            explication = _("Ce fichier est fourni par le pilote de la carte Nvidia : il est absent ou abîmé. Réinstallez le pilote, "
                            "ou passez sur le processeur.")
            actions = [("pilote_nvidia", _("Mettre à jour le pilote Nvidia")), ("processeur", _("Utiliser le processeur à la place"))]
        elif "pilote" in familles:
            titre = _("Il manque {d} : pilote graphique", d=liste)
            explication = _("Ce fichier vient du pilote de la carte graphique. Mettez-le à jour, ou passez sur le processeur.")
            actions = [_pilote(texte), ("processeur", _("Utiliser le processeur à la place"))]
        else:
            titre = _("Il manque {d} dans le moteur", d=liste)
            explication = _("Ce fichier fait partie du moteur, rangé dans le dossier de PhilCut : téléchargement incomplet ou fichier "
                            "mis de côté par l'antivirus. Réinstallez le moteur (le modèle est gardé).")
            actions = [("reinstaller", _("Réinstaller le moteur")), ("processeur", _("Utiliser le processeur à la place"))]
    elif code in (DLL_MANQUANTE, POINT_ENTREE) or "dll" in bas and ("not found" in bas or "introuvable" in bas):
        titre = _("Il manque un composant de Windows au moteur")
        explication = _("Le moteur ne trouve pas une de ses bibliothèques (DLL) et s'arrête avant même de commencer. C'est presque "
                        "toujours le « Visual C++ » de Microsoft (gratuit, officiel) qui manque ou est trop ancien. Installez-le, puis "
                        "réessayez ; sinon réinstallez le moteur, ou passez sur le processeur.")
        actions = [("vcredist", _("Installer Visual C++ (Microsoft)")), ("reinstaller", _("Réinstaller le moteur")),
                   ("processeur", _("Utiliser le processeur à la place"))]
    elif re.search(r"(_wfopen|fopen|load_param|load_model)[^\n]*(\.param|\.bin)[^\n]*failed", texte) or "dossier « models »" in bas:
        titre = _("Les modèles du moteur manquent")
        explication = _("Le moteur démarre mais ne trouve pas ses modèles (dossier « models ») : l'archive installée était "
                        "incomplète. La carte graphique et le pilote ne sont pas en cause. Réinstallez le moteur : la version "
                        "corrigée, avec ses modèles, est téléchargée.")
        actions = [("reinstaller", _("Réinstaller le moteur"))]
    elif code == ARRET_BRUTAL:
        titre = _("Le moteur s'est arrêté d'un coup")
        cartes = cartes_vulkan(texte)
        if len(cartes) > 1 and carte_dediee(texte) not in (None, 0):
            explication = _("Ce poste a deux cartes graphiques ({c}) et le moteur a pris la première, la carte intégrée, trop "
                            "faible : il a planté. PhilCut réessaie tout seul avec la carte dédiée ; si cela se reproduit, mettez à "
                            "jour son pilote.", c=", ".join(n for _i, n in cartes))
            actions = [("carte_dediee", _("Réessayer avec la carte dédiée")), _pilote(texte)]
        else:
            explication = _("Le moteur a été stoppé par Windows en plein travail : le plus souvent un pilote graphique trop ancien, "
                            "ou plus assez de mémoire sur la carte graphique. Mettez à jour le pilote, fermez les autres logiciels "
                            "lourds, ou passez sur le processeur.")
            actions = [_pilote(texte), ("processeur", _("Utiliser le processeur à la place")), ("reinstaller", _("Réinstaller le moteur"))]
    elif code == ACCES:
        titre = _("Le moteur a planté (accès mémoire)")
        explication = _("Le moteur a voulu lire une mémoire interdite : pilote graphique, fichier du modèle abîmé (téléchargement "
                        "incomplet) ou moteur trop ancien. Réinstallez le moteur ; si cela continue, mettez à jour le pilote ou "
                        "passez sur le processeur.")
        actions = [("reinstaller", _("Réinstaller le moteur")), _pilote(texte), ("processeur", _("Utiliser le processeur à la place"))]
    elif code == INSTRUCTION:
        titre = _("Processeur trop ancien pour ce moteur")
        explication = _("Ce moteur utilise des instructions (AVX2) que ce processeur n'a pas. La version carte graphique, si le poste "
                        "en a une, peut marcher ; sinon ce modèle n'est pas utilisable sur ce poste.")
        actions = [("carte", _("Utiliser la carte graphique"))]
    elif code in (MEMOIRE, PILE) or any(x in bas for x in ("out of memory", "outofmemory", "out_of_memory", "bad_alloc", "mémoire insuffisante",
                                                          "erroroutofdevicememory", "cudaerrormemoryallocation")):
        titre = _("Plus assez de mémoire")
        explication = _("Le travail demande plus de mémoire que le poste (ou sa carte graphique) n'en a de libre. Fermez les autres "
                        "logiciels lourds (navigateur, jeux), demandez plus court ou plus petit, ou passez sur le processeur.")
        actions = [("processeur", _("Utiliser le processeur à la place")), ("reessayer", _("Réessayer"))]
    elif "vulkan" in bas and any(x in bas for x in ("failed", "error", "not supported")):
        titre = _("La carte graphique n'a pas répondu (Vulkan)")
        explication = _("Le moteur n'a pas pu utiliser la carte graphique : pilote trop ancien ou carte non prise en charge. "
                        "Mettez à jour le pilote, ou passez sur le processeur.")
        actions = [_pilote(texte), ("processeur", _("Utiliser le processeur à la place"))]
    elif "n'est pas installé" in bas or "no such file" in bas or "introuvable" in bas or "manquant" in bas:
        titre = _("Moteur ou modèle incomplet")
        explication = _("Un fichier du moteur ou du modèle manque (téléchargement interrompu, antivirus). Réinstallez-le.")
        actions = [("reinstaller", _("Réinstaller le moteur"))]
    elif "trop long" in bas:
        titre = _("Calcul trop long")
        explication = _("Le moteur n'a pas fini dans le temps prévu. Sans carte graphique, demandez plus court ou plus petit.")
        actions = [("reessayer", _("Réessayer"))]
    else:
        titre = _("Le moteur n'a pas pu finir")
        explication = _("La cause n'est pas reconnue. Le journal du moteur dit ce qu'il faisait au moment de l'arrêt ; réessayer, "
                        "ou réinstaller le moteur, règle la plupart des cas.")
        actions = [("reessayer", _("Réessayer")), ("reinstaller", _("Réinstaller le moteur"))]
    return {"titre": titre, "explication": explication, "actions": actions, "code": code, "manquantes": manquantes}


def court(texte):
    """Le message brut sans les longues listes du moteur : première ligne utile, 160 caractères au plus."""
    t = str(texte or "").strip()
    t = t.split("\n")[0]
    return (t[:157] + "…") if len(t) > 160 else t


def ouvrir_lien(action):
    import webbrowser
    lien = {"vcredist": LIEN_VCREDIST, "pilote_nvidia": LIEN_NVIDIA, "pilote_amd": LIEN_AMD, "pilote_intel": LIEN_INTEL}.get(action)
    if lien:
        webbrowser.open(lien)
        return True
    return False


def appliquer(action, genre, params):
    """Réglage à changer pour l'action (sans interface). Renvoie True si quelque chose a été changé et qu'on peut réessayer."""
    if action == "processeur":
        evites = set((params.get("moteurs_evites") or []))
        evites.add(f"{genre}_gpu" if genre and not str(genre).endswith("_gpu") else str(genre))
        params["moteurs_evites"] = sorted(evites)
        return True
    if action == "carte":
        params["ia_gpu"] = True
        params["moteurs_evites"] = [m for m in (params.get("moteurs_evites") or []) if not m.endswith("_gpu")]
        return True
    if action == "carte_dediee":
        params.pop("vulkan_carte", None)
        return True
    return False
