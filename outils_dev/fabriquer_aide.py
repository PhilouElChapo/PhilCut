"""Fiches d'aide de la discussion (1.1.12) → catalogue/aide.json. Elles complètent les menus et les guides : ce qu'il faut savoir
pour choisir (prix, pièges, quel outil pour quel cas). Textes en français ; l'IA répond dans la langue de la question.
Une fiche corrigée ici puis poussée sur main est lue par tous les PhilCut au démarrage, sans nouvelle version."""
import json
import os

FICHES = [
    ("rallonger_photo", "Rallonger un plan ou continuer une scène à partir d'une photo ou d'un rush",
     "rallonger prolonger continuer photo image suite plan court scene animer",
     "Deux chemins, selon le besoin :\n"
     "1) Une seule suite au même endroit (la photo s'anime, la scène continue) : clic droit sur le plan › « Prolonger ce plan "
     "(image tenue, ralenti ou IA)… ». Méthodes : image tenue avec léger zoom (gratuit, instantané), ralenti de la fin (gratuit), "
     "IA de ce poste (gratuit, une à plusieurs minutes, modèle vidéo à installer dans Préférences › IA locale), IA cloud fidèle "
     "Kling O3 Référence (clef fal, environ 0,084 $ la seconde, 3 à 15 s, prix demandé avant). On choisit « A la fin du plan » "
     "ou « Au début du plan », la durée et le son (ambiance prolongée ou silence). Un aperçu est montré avant de poser.\n"
     "2) Une vraie suite en plusieurs gestes ou plusieurs plans avec les mêmes personnes (ex. les personnes marchent vers un avion, "
     "il roule puis décolle) : clic droit sur le plan › « Continuer ce plan avec l'assistant IA… ». L'assistant part de la "
     "dernière image du plan : 1. Votre idée (écrire la suite en clair, chaque événement dans l'ordre), 2. Qui et quoi (cartes des "
     "personnes, objets, lieux ; prendre les fiches de « Ma bibliothèque » pour garder les visages), 3. Les plans (un plan par "
     "action, modifiable, « Moteur vidéo » sous le tableau), 4. Les images (images clefs), 5. La vidéo (fabrication, relecture, "
     "« Poser dans le film »). Un brouillon gratuit de toute la séquence peut être vu avant de payer.\n"
     "Pour changer d'abord un élément de la photo (un avion par un autre) : clic droit › « Remplacer un élément de l'image par un "
     "de ma bibliothèque… » (Gemini, environ 0,04 $), puis prolonger."),
    ("memes_visages", "Garder les mêmes visages, objets et lieux d'un plan à l'autre",
     "visage ressemblance personnage fiche bibliotheque identique pilote coherent",
     "Les moteurs vidéo gardent un visage grâce à sa fiche (face, trois quarts, profil, en pied). Fabrique IA › « Ma bibliothèque "
     "de créations… » › Nouveau… › Personnage (ou Objet, Lieu) ; ajouter des photos (Réel ou Inspiré de photos : cocher l'accord de "
     "la personne, ou que c'est vous) ou décrire (Inventé) ; puis « Faire sa fiche (Gemini)… » (environ 0,04 $). Dans l'assistant, "
     "écrire le nom exact de l'entrée dans le texte (ex. le nom donné au personnage) : il est repris tout seul de la bibliothèque. "
     "Le moteur « Kling O3 Référence » est celui qui garde le mieux les visages (jusqu'à 4 fiches par plan)."),
    ("groupe_clip", "Garder les mêmes musiciens dans tous les clips (groupe entier)",
     "groupe musiciens clip chanson visages memes bibliotheque band",
     "Fabrique IA › Vidéo › « Clip de groupe d'après une chanson… ». Dans « Le groupe » : « Depuis ma bibliothèque… » prend un "
     "musicien gardé ; « ☆ Garder ce groupe… » range le groupe entier (chaque musicien entre dans la bibliothèque avec son image) ; "
     "pour la chanson suivante, « Prendre un groupe de ma bibliothèque… » remet les mêmes musiciens, mêmes visages. Le groupe se "
     "modifie aussi dans « Ma bibliothèque de créations » (genre Groupe : ajouter ou retirer un musicien)."),
    ("moteur_video", "Choisir ou changer le moteur vidéo",
     "moteur video modele kling veo omni seedance changer choisir",
     "Dans l'assistant de création : page « Les plans », liste « Moteur vidéo » sous le tableau des plans (à côté : « Images de "
     "contrôle »). Dans la Séquence IA : onglet Plans, liste du moteur. Les moteurs cloud demandent une clef (fal, Google) : "
     "Assistant › « Connecter une IA (obtenir et tester ma clef)… ». Le prix de chaque plan est montré et demandé avant de payer."),
    ("image_clef", "Image clef d'un plan",
     "image clef fin arrivee raccord plan creer ligne rouge",
     "Dans l'assistant, page « Les images » : pour chaque plan, cocher « Image clef » si le plan doit arriver sur une image précise. "
     "« Créer… » la dessine avec vos fiches (Gemini, environ 0,04 $) ; « Image de la ligne rouge » prend une vraie image du "
     "montage (gratuit). Sans image clef, le plan suivant part de la vraie dernière image du plan d'avant (gestes cohérents)."),
    ("clefs_ia", "Clefs des IA, crédits et prix",
     "clef cle api claude gemini fal credit recharger prix cout payer",
     "Les clefs se mettent dans Edition › Préférences › IA (ou Assistant › « Connecter une IA… »). Elles sont rangées dans le "
     "coffre du système, jamais dans un fichier ni dans une conversation : ne les collez nulle part ailleurs. Fabrique IA › "
     "« Crédits et recharges des IA… » montre chaque service et son bouton « Recharger… ». Ordres de prix : image Gemini environ "
     "0,04 $, relecture d'un plan environ 0,01 $, Kling O3 Référence environ 0,084 $ la seconde ; l'IA de ce poste est gratuite. "
     "PhilCut demande toujours avant de payer."),
    ("brouillon", "Voir toute la séquence avant de payer",
     "brouillon animatique apercu gratuit avant payer sequence",
     "Dans l'assistant, page « Les images » : « Brouillon de toute la séquence… ». L'animatique (images fixes animées, gratuit) "
     "montre le rythme et l'ordre ; le brouillon Omni 360p est payant mais bon marché. « Revoir le brouillon » le rejoue."),
    ("annuler", "Revenir en arrière",
     "annuler defaire erreur revenir sauvegarde",
     "Edition › Annuler (Ctrl+Z) défait chaque action, même un « Dites-le en clair » entier. Fichier › « Revenir à une sauvegarde "
     "automatique… » reprend une copie faite chaque minute. Fermer une fenêtre de travail la range (« Afficher la fenêtre » dans la "
     "barre du bas) : rien n'est perdu."),
]


def main():
    sortie = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogue", "aide.json")
    d = {"format": 1, "fiches": [{"id": i, "titre": {"fr": t}, "mots": m, "texte": {"fr": x}} for i, t, m, x in FICHES]}
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print(len(FICHES), "fiches →", sortie)


if __name__ == "__main__":
    main()
