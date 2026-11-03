from .langue import _
"""Catalogue des outils de PhilCut, par famille : ce que montrent la barre d'outils personnalisable et le volet."""

FAMILLES = [
    ("monter", _('Monter'), "#6d3fc6", "#efe9fb"),
    ("assistant", _('Assistant'), "#4338ca", "#ecebfd"),
    ("habiller", _('Habiller'), "#b0186b", "#fbe8f2"),
    ("son", _('Son'), "#0b7a80", "#e2f4f4"),
    ("fabrique", _('Fabrique'), "#a35c00", "#fdf1e2"),
    ("sortir", _('Sortir'), "#1462c2", "#e6f0fc"),
]

# (id, famille, icone, titre, sous-titre, bulle d'aide, disponible)
OUTILS = [
    ("importer", "monter", "importer", _('Importer'), _('Rushes, musiques, images'),
     _("Ajoute des vidéos, des musiques ou des images au projet. Les rushes restent où ils sont ; PhilCut fabrique en arrière-plan une copie légère (proxy) pour monter sans ralentir."), True),
    ("couper", "monter", "couper", _('Couper'), _('Couper au curseur (C)'),
     _("Coupe le plan sous le curseur de lecture en deux. Raccourci : C."), True),
    ("supprimer", "monter", "supprimer", _('Supprimer'), _('Retirer le plan et refermer (Suppr)'),
     _("Retire le plan sélectionné ; les suivants se recollent. Maj+Suppr laisse un trou."), True),
    ("vitesse", "monter", "vitesse", _('Vitesse'), _('Ralenti, accéléré, speed ramp'),
     _("Change la vitesse du plan sélectionné : ralenti fluide, accéléré, ou speed ramp (lent puis rapide)."), True),
    ("recadrer", "monter", "recadrer", _('Cadrage'), _('Remplir, bandes, fond flou, suivi'),
     _("Comment le plan remplit le format : recadré, avec des bandes, avec un fond flou, ou recadré en suivant une personne."), True),
    ("stabiliser", "monter", "stabiliser", _('Stabiliser'), _('Plan filmé à la main'),
     _("Supprime les tremblements du plan sélectionné et redresse l'horizon si besoin."), True),
    ("assistant", "assistant", "assistant", _('Assistant de montage'), _('Analyse les rushes, propose la recette'),
     _("PhilCut lit vos rushes (coupes, lumière, son, personnes, lieu, date), puis propose un montage complet : logo, musique, plans, textes, effets, Goodies. Vous cochez ce que vous gardez."), True),
    ("fiche", "assistant", "liste_fichiers", _('Fiche vidéo'), _('Ce que PhilCut a compris du rush'),
     _("La fiche locale d'un rush : durée, format, cadence réelle, rotation, HDR, son, luminosité, coupes, moments forts."), True),
    ("texte", "habiller", "texte", _('Texte'), _('Titres animés, étiquettes'),
     _("Ajoute un titre, un sous-titre ou une étiquette : fondu, zoom, néon, feu, machine à écrire, tournoyant, mots au rythme. Une étiquette peut suivre une personne."), True),
    ("effets", "habiller", "effets", _('Effets'), _('Glow, glitch, puzzle, Matrix…'),
     _("Pose un effet ou une transition sur le plan sélectionné. Les effets qui demandent un téléchargement se cochent dans les Préférences."), True),
    ("goodies", "habiller", "goodies", _('Goodies'), _('Instruments, badges, horloge'),
     _("Incrustations à thème : altimètre, vitesse, cap, horloge, immatriculation, boussole, compte à rebours… Valeurs tirées d'une trace GPS ou saisies."), True),
    ("sous_titres", "habiller", "sous_titres", _('Sous-titres'), _('Automatiques (local) ou importés'),
     _("Transcrit la voix sur ce poste (pack Whisper) ou importe un fichier SRT ; style karaoké possible."), True),
    ("musique", "son", "musique", _('Musique'), _('Bibliothèque libre, votre dossier'),
     _("Ajoute une musique sous la vidéo : catalogue libre de droits (téléchargé à la demande) ou votre dossier. La musique baisse automatiquement sous la voix."), True),
    ("voix", "son", "volume", _('Voix et son'), _('Embellir, débruiter, volume'),
     _("Débruitage, voix embellie pour la narration, autotune pour le chant, volume du plan, muet."), True),
    ("fabrique", "fabrique", "fabrique", _('Fabrique'), _('Logos, intros, plans IA'),
     _("Crée un logo animé, une intro ou une fin de vidéo, ou un plan généré par IA (Flow avec votre abonnement, Veo par l'API) dans le style que vous indiquez."), True),
    ("exporter", "sortir", "exporter", _('Exporter'), _('YouTube, Insta, WhatsApp, écran LED'),
     _("Fabrique la vidéo finale au bon format et au bon poids pour sa destination, avec l'encodeur de votre carte graphique si possible."), True),
    ("partager", "sortir", "nuage", _('Déposer sur le Drive'), _('Partager l\'export'),
     _("Dépose la vidéo exportée sur votre Drive ou votre NAS pour la partager."), True),
]

# elements de la barre d'outils (en plus des outils) : cle -> libelle
ELEMENTS_BARRE = [("|", _("Séparateur")), ("annuler", _("Annuler|action")), ("retablir", _("Rétablir")), ("lecture", _("Lecture")),
                  ("zoom", _("Zoom de la timeline")), ("aimant", _("Aimant (coller aux bords)")), ("volet", _("Volet de droite"))]
BARRE_DEFAUT = ["importer", "|", "annuler", "retablir", "|", "couper", "supprimer", "vitesse", "recadrer", "|", "assistant", "|",
                "texte", "effets", "goodies", "musique", "|", "fabrique", "|", "exporter", "zoom", "aimant", "volet"]


def famille(fid):
    for f in FAMILLES:
        if f[0] == fid:
            return f
    return FAMILLES[0]


def outil(oid):
    for o in OUTILS:
        if o[0] == oid:
            return o
    return None
