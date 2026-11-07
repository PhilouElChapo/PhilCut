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


def _pilote(texte):
    t = (texte or "").lower()
    if "nvidia" in t or "geforce" in t or "rtx" in t:
        return ("pilote_nvidia", _("Mettre à jour le pilote Nvidia"))
    if "radeon" in t or "amd" in t:
        return ("pilote_amd", _("Mettre à jour le pilote AMD"))
    return ("pilote_intel", _("Mettre à jour le pilote graphique"))


def diagnostiquer(texte, genre=None):
    texte = str(texte or "")
    bas = texte.lower()
    code = code_arret(texte)
    gpu = bool(genre and str(genre).endswith("_gpu")) or "cuda" in bas or "vulkan" in bas
    actions = []
    if code in (DLL_MANQUANTE, POINT_ENTREE) or "dll" in bas and ("not found" in bas or "introuvable" in bas):
        titre = _("Il manque un composant de Windows au moteur")
        explication = _("Le moteur ne trouve pas une de ses bibliothèques (DLL) et s'arrête avant même de commencer. C'est presque "
                        "toujours le « Visual C++ » de Microsoft (gratuit, officiel) qui manque ou est trop ancien ; avec la version "
                        "carte graphique du moteur, ce peut aussi être un pilote trop ancien. Installez Visual C++, puis réessayez ; "
                        "si cela ne suffit pas, passez sur le processeur (plus lent, mais sans ces composants).")
        actions = [("vcredist", _("Installer Visual C++ (Microsoft)")), ("processeur", _("Utiliser le processeur à la place")),
                   ("reinstaller", _("Réinstaller le moteur"))]
        if gpu:
            actions.append(_pilote(texte))
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
    return {"titre": titre, "explication": explication, "actions": actions, "code": code}


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
