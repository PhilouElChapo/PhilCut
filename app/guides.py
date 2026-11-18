"""Guides pas à pas (0.9.52) : « Comment faire… » pour des cas concrets de montage.

Chaque guide a des étapes ; une étape peut avoir :
- « montrer » : ce que fait le bouton « Montrez-moi » — ouvrir un menu de la barre en surlignant la bonne ligne
  ({"menu": [...]}), ouvrir le menu du clic droit sur le plan sous la ligne rouge ({"clic_droit": [...]}), ou ouvrir
  un onglet du volet de droite et y chercher un mot ({"volet": "effets", "chercher": "..."}) ;
- « fait » : comment PhilCut voit que l'étape est faite (« plan_choisi », « partie_jaune », « fenetre:NomDeClasse »,
  « effet:id », « suivi ») ; sans cela, l'utilisateur coche lui-même « C'est fait ».
Un guide dit honnêtement ce qui manque encore (« etat » : ok, partiel, a_venir) et propose le détour le plus proche.
Les textes des menus sont ceux de PhilCut (traduits par _()) : le guide suit la langue choisie.
"""
import unicodedata

from .langue import _


def _norm(t):
    t = (t or "").replace("&", "").replace("…", "").replace("...", "").strip()
    return unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower()


def _version(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)


def guides_catalogue():
    """Guides livrés par le catalogue en ligne (0.9.55), comme les Goodies : ajoutés ou corrigés sans nouvelle version.
    Textes par langue ; chemins de menus en français, traduits ici ; un guide qui demande une version plus récente de
    PhilCut est laissé de côté."""
    from . import catalogue_ligne as CL
    from .config import VERSION
    out = []
    for g in (CL.charger("guides.json").get("guides") or []):
        try:
            if _version(g.get("philcut_min", "0")) > _version(VERSION):
                continue
            etapes = []
            for e in g.get("etapes") or []:
                n = {"texte": CL.localise(e.get("texte"))}
                mo = e.get("montrer") or {}
                if mo.get("menu"):
                    n["montrer"] = {"menu": [_(x) for x in mo["menu"]]}
                elif mo.get("clic_droit"):
                    n["montrer"] = {"clic_droit": [_(x) for x in mo["clic_droit"]]}
                elif mo.get("volet"):
                    n["montrer"] = {"volet": mo["volet"], "chercher": CL.localise(mo.get("chercher", ""))}
                if e.get("fait"):
                    n["fait"] = e["fait"]
                etapes.append(n)
            if not g.get("id") or not etapes:
                continue
            out.append({"id": g["id"], "etat": g.get("etat", "ok") if g.get("etat") in ETATS else "ok",
                        "titre": CL.localise(g.get("titre")), "intro": CL.localise(g.get("intro")), "mots": g.get("mots", ""),
                        "etapes": etapes, "catalogue": True})
        except (TypeError, AttributeError, KeyError):
            continue                                       # un guide mal formé ne gêne pas les autres
    return out


def guides():
    """Les guides intégrés et ceux du catalogue (qui remplacent un guide de même id), par ordre alphabétique."""
    tous = {g["id"]: g for g in _guides_integres()}
    for g in guides_catalogue():
        tous[g["id"]] = g
    return sorted(tous.values(), key=lambda g: _norm(g["titre"]))


def _guides_integres():
    G = [
        {"id": "fond", "etat": "ok",
         "titre": _("Changer le fond (décor, paysage) d'un rush"),
         "mots": "fond decor paysage arriere-plan detourer remplacer chroma vert objet animal avion cloud bria sujet",
         "intro": _("Un rush tourné devant un fond uni (vert, bleu) se détoure par la couleur. Un rush filmé n'importe où : l'effet "
                    "« Changer le fond (détourage) » sépare le sujet du fond et le pose sur une image, une vidéo, une couleur ou le "
                    "fond flouté. Méthode « IA de ce poste » : une personne, gratuit (modèle « Détourage de personne »). Méthode "
                    "« IA cloud, tout sujet » : personne, animal, objet, avion…, environ 0,05 $ la seconde, payé une seule fois par "
                    "passage."),
         "etapes": [
             {"texte": _("Rush tourné devant un fond uni : cliquez le plan dans la timeline."), "fait": "plan_choisi"},
             {"texte": _("Dans le volet Effets, cherchez « Fond vert » et glissez « Fond vert (chroma key) » sur le plan."),
              "montrer": {"volet": "effets", "chercher": _("Fond vert")}, "fait": "effet:chroma_key"},
             {"texte": _("Dans l'Inspecteur, « Nouveau décor » : choisissez l'image ou la vidéo du paysage ; réglez la couleur du "
                         "fond et la tolérance jusqu'à ce que le sujet soit net.")},
             {"texte": _("Rush filmé n'importe où : volet Effets, cherchez « Changer le fond », glissez « Changer le fond (détourage) » "
                         "sur le plan ; dans l'Inspecteur, « Nouveau fond » : image ou vidéo du projet, couleur, ou fond flouté."),
              "montrer": {"volet": "effets", "chercher": _("Changer le fond")}, "fait": "effet:detourage"},
             {"texte": _("Un sujet qui n'est pas une personne (avion, animal, objet), ou un détourage plus fin : dans l'Inspecteur, "
                         "« Préparer par l'IA cloud (environ … $)… » : le prix est demandé, la barre du bas suit, puis la méthode passe "
                         "seule à « IA cloud, tout sujet ».")},
             {"texte": _("Ou seulement flouter le fond : ligne rouge sur le plan, puis Fabrique IA › Vidéo › Effet IA sur le film… › "
                         "« Flou d'arrière-plan (effet portrait) » › Créer."),
              "montrer": {"menu": [_("Fabrique IA"), _("Vidéo"), _("Effet IA sur le film (dessin animé, ralenti, agrandir, photo 3D…)…")]},
              "fait": "fenetre:DialogueAtelierIA"},
         ]},
        {"id": "suite_voix", "etat": "ok",
         "titre": _("Continuer un commentaire avec la même voix"),
         "mots": "voix commentaire continuer suite clone ma voix narration phrase dire",
         "intro": _("PhilCut fait dire une nouvelle phrase avec la voix d'un extrait de 5 à 15 secondes du film : votre voix, ou "
                    "celle d'une personne qui vous a donné son accord (case à cocher), jamais une personne connue. Tout se fait sur "
                    "ce poste, gratuitement (modèle d'environ 1,6 Go à installer une fois)."),
         "etapes": [
             {"texte": _("Placez la ligne rouge là où le commentaire doit reprendre (juste après la voix à continuer).")},
             {"texte": _("Clic droit sur le plan qui porte la voix › « Continuer avec cette voix… » (ou Montage › Son › « Continuer "
                         "avec ma voix… »)."),
              "montrer": {"clic_droit": [_("Continuer avec cette voix…")]}, "fait": "fenetre:DialogueVoixSuite"},
             {"texte": _("Ecoutez l'extrait proposé (les dernières secondes de voix avant la ligne rouge) ; déplacez-le si besoin. "
                         "Musique derrière ? Cochez « Isoler d'abord la voix ».")},
             {"texte": _("Cochez l'accord, écrivez la phrase (ex. : « Et maintenant, passons à autre chose. »), puis « Fabriquer la "
                         "voix ». Ecoutez ; refabriquez en changeant la ponctuation ou l'expressivité si besoin.")},
             {"texte": _("« Poser dans le film » : la phrase va sur la piste Voix à la ligne rouge. Après un plan de liaison, le bouton "
                         "« Une phrase avec ma voix sur ce plan… » la pose au début du plan de liaison."), "fait": "voix_ia"},
         ]},
        {"id": "couper", "etat": "ok",
         "titre": _("Couper des images dans un rush"),
         "mots": "couper coupe retirer supprimer passage morceau partie jaune enlever",
         "intro": _("Couper un plan en deux, ou retirer un passage : la suite se recolle toute seule."),
         "etapes": [
             {"texte": _("Placez la ligne rouge au début du passage à retirer (clic sur la règle des temps).")},
             {"texte": _("Clic droit sur le plan › « Couper ici » coupe le plan en deux à la ligne rouge."),
              "montrer": {"clic_droit": [_("Couper ici")]}},
             {"texte": _("Pour retirer tout un passage : posez la partie jaune (fanions [ et ] sur la règle, ou Montage › Pistes et "
                         "passage choisi › « Partie jaune : la faire commencer à la ligne rouge », puis « … finir à la ligne "
                         "rouge »)."),
              "montrer": {"menu": [_("Montage"), _("Pistes et passage choisi (partie jaune)"),
                                   _("Partie jaune : la faire commencer à la ligne rouge")]},
              "fait": "partie_jaune"},
             {"texte": _("Montage › Pistes et passage choisi › « Partie jaune : supprimer ce passage »."),
              "montrer": {"menu": [_("Montage"), _("Pistes et passage choisi (partie jaune)"), _("Partie jaune : supprimer ce passage")]}},
             {"texte": _("Un vide est resté entre deux plans ? Clic droit dans le vide › « Refermer ce vide : recoller les plans ».")},
         ]},
        {"id": "assistant_creation", "etat": "ok",
         "titre": _("Etre guidé pour continuer un rush ou créer une scène par IA (mode assisté)"),
         "mots": "assistant assiste guide aide pas a pas continuer rallonger rush suite scene histoire personnages plans budget "
                 "facile automatique idee carte fiche cadre ameliorer reformuler continuite",
         "intro": _("Vous dites en quelques mots ce que vous voulez ; l'assistant (Claude, Gemini ou l'IA de ce poste) regarde la "
                    "dernière image, en déduit une carte par personne et par objet (cadre proposé sur l'image), et les plans d'une "
                    "action. Vous validez ou corrigez carte par carte : dans l'image, une photo à vous, ou inventé d'après la "
                    "description. Tout texte a son « ✨ Améliorer » (l'IA reformule, vous choisissez). Puis images avant la vidéo, "
                    "fabrication relue, budget prévu et dépensé (rouge s'il est dépassé)."),
         "etapes": [
             {"texte": _("Cliquez le plan à continuer dans la timeline."), "fait": "plan_choisi"},
             {"texte": _("Clic droit sur le plan › « Continuer ce plan avec l'assistant IA… » (ou Fabrique IA › Vidéo › Assistant de création)."),
              "montrer": {"clic_droit": [_("Continuer ce plan avec l'assistant IA…")]}, "fait": "fenetre:DialogueAssistant"},
             {"texte": _("« Que voulez-vous faire ? » : écrivez la suite d'un trait (« ✨ Améliorer » si vous voulez), vérifiez ce que "
                         "l'assistant comprend, puis « Voir ce qu'il faut ».")},
             {"texte": _("Une carte par personne et par objet : pas la bonne personne ? Cliquez la carte puis la personne sur l'image (ou "
                         "tracez son cadre). Choisissez d'où vient chacun ; « Compléter la description » aide pour les inventés.")},
             {"texte": _("Les plans : « Qui » dit qui on voit (vide = personne ; survolez pour savoir où sont les autres), « Cadrage » "
                         "dit plan large, serré, ce que fait la caméra. « ✨ Vérifier la continuité » les remplit d'après l'histoire "
                         "(quelqu'un monté en voiture ne réapparaît pas). Corrigez dans le tableau ou en clair en bas.")},
             {"texte": _("« Images de contrôle » : Gemini (visages fidèles, payant), l'IA de ce poste (gratuite, visages "
                         "approximatifs) ou aucune. Puis confirmez le budget : l'assistant prépare fiches et images.")},
             {"texte": _("Regardez chaque image, « Corriger… » celles qui ne vont pas (dites aussi le cadrage : « plan large, on voit "
                         "toute la voiture ») : l'image refaite est entourée en orange, et l'assistant propose de refaire l'image "
                         "suivante qui en part. Puis lancez la vidéo.")},
             {"texte": _("Revenir en arrière : « ‹ Précédent » ou un clic sur une étape du fil en haut ; en avançant à nouveau, seul ce "
                         "qui a changé est refait. « Régler moi-même… » ouvre la Séquence IA, et « ‹ Retour à l'assistant » y "
                         "ramène.")},
             {"texte": _("Chaque plan est relu : ✓ ou ⚠ avec la raison. « Refaire ce plan… » si besoin, puis « Poser dans le film ».")},
         ]},
        {"id": "atelier_bibliotheque", "etat": "ok",
         "titre": _("Créer ses personnages, lieux et tenues dans la bibliothèque (réels, inspirés ou inventés)"),
         "mots": "creer personnage lieu tenue vetement habit costume bibliotheque atelier invente inspire photo reel directrice "
                 "secretaire bureau planche fiche rush",
         "intro": _("Ce que vous créez une fois se réutilise partout. Un personnage ou un lieu est réel (vos photos, plusieurs "
                    "angles), inspiré de photos (ressemblance gardée, adapté par la description) ou inventé (description). Les "
                    "photos peuvent venir de vos fichiers ou de n'importe quel rush (ligne rouge). Les tenues se rangent à part et "
                    "se mettent à n'importe quel personnage."),
         "etapes": [
             {"texte": _("Fabrique IA › « Ma bibliothèque de créations… » › « Nouveau… » › Personnage (ou Lieu, Objet, Tenue)."),
              "fait": "fenetre:DialogueBibliothequeCreations"},
             {"texte": _("Nom, description (« ✨ Améliorer »), « Création » : réel, inspiré de photos ou inventé.")},
             {"texte": _("« Ajouter des photos… » ou « Image d'un rush… » (ligne rouge sur un rush, puis encadrez) : plusieurs "
                         "angles donnent un meilleur résultat. Pour une personne réelle ou inspirée, cochez l'accord.")},
             {"texte": _("Tenue : « Toute faite… », « Composer… » pièce par pièce, ou une tenue à vous ; choisissez-la sur le "
                         "personnage.")},
             {"texte": _("« Faire sa fiche » (personnage, objet) ou « Faire sa planche » (lieu) : quatre vues, environ 0,04 $, "
                         "puis « Enregistrer ».")},
             {"texte": _("Dans l'assistant, sur chaque carte : « Dans ma bibliothèque », et « Tenue dans cette scène ».")},
         ]},
        {"id": "bibliotheque_toute_faite", "etat": "ok",
         "titre": _("Prendre une description toute faite (tenue, lieu, véhicule, avion, personnage type) ou composer une tenue"),
         "mots": "toute faite pret catalogue prompt description tenue vetement chaussures chapeau matiere lieu piscine plage "
                 "monument vehicule limousine berline suv avion helicoptere personnage composer",
         "intro": _("PhilCut contient une bibliothèque toute faite : tenues complètes, pièces (hauts, bas, robes, vestes, "
                    "chaussures, chapeaux, accessoires, matières), lieux, véhicules, avions et autres transports, personnages "
                    "types inventés. Chaque description a ses mots anglais pour les IA. Prenez-en une : elle devient la vôtre, "
                    "modifiable ; vos propres créations s'ajoutent à côté."),
         "etapes": [
             {"texte": _("Fabrique IA › « Ma bibliothèque de créations… » › « Toute faite… »."),
              "fait": "fenetre:DialogueBibliothequeCreations"},
             {"texte": _("Choisissez la rubrique, Femme ou Homme, ou cherchez un mot (piscine, cuir, berline…) ; l'image "
                         "d'exemple montre le résultat.")},
             {"texte": _("« Ajouter à ma bibliothèque » : modifiez la description si vous voulez, ajoutez vos photos, faites sa "
                         "fiche ou sa planche.")},
             {"texte": _("Pour une tenue sur mesure : sur une tenue, « Composer… » ; choisissez pièce par pièce et la matière.")},
             {"texte": _("Dans l'assistant, sur chaque carte : « Dans ma bibliothèque » › « Toute faite… ».")},
         ]},
        {"id": "brouillon_sequence", "etat": "ok",
         "titre": _("Voir un brouillon de toute la séquence avant de payer la vraie fabrication"),
         "mots": "brouillon animatique apercu essai sequence entiere avant payer gratuit omni 360p ia locale",
         "intro": _("Le brouillon montre la séquence entière, plan après plan, à la bonne durée. Rien n'est posé dans le film : "
                    "on corrige ce qui ne va pas, puis on lance la vraie fabrication."),
         "etapes": [
             {"texte": _("Dans l'assistant, à l'étape « 4. Les images » : « Brouillon de toute la séquence… ».")},
             {"texte": _("« Images et textes, plan par plan » : gratuit et immédiat ; chaque plan montre son image connue, son "
                         "action et sa durée, en fondu vers son image clef.")},
             {"texte": _("« IA vidéo de ce poste » (gratuit, lent) ou « Gemini Omni 360p » (prix demandé) : une vraie vidéo, en "
                         "petite qualité.")},
             {"texte": _("« Revoir le brouillon » le rouvre ; si tout va bien, « Tout me convient : fabriquer la vidéo ».")},
         ]},
        {"id": "sequence_continue", "etat": "ok",
         "titre": _("Fabriquer d'un seul tenant les plans d'un même moment (gestes enchaînés)"),
         "mots": "continu seul tenant enchaine gestes moment plusieurs plans un calcul kling multi sequence continue",
         "intro": _("Avec Kling O3 Référence, les plans qui se suivent jusqu'à la prochaine image clef (15 s et six plans au "
                    "plus) sont fabriqués en un seul calcul : les gestes continuent d'un plan à l'autre, sans arrêt ni saut, "
                    "puis la vidéo est coupée en ses plans. Le prix est le même (à la seconde)."),
         "etapes": [
             {"texte": _("Dans l'assistant, à l'étape des images, cochez « Image clef » là où la scène doit être respectée : "
                         "chaque image clef ferme un moment.")},
             {"texte": _("Lancez la vidéo : « Fabrication des plans 2 à 4 d'un seul tenant » ; dans la liste, ⛓ relie les plans "
                         "faits ensemble.")},
             {"texte": _("« Refaire ce plan… » refait aussi les plans suivants du même calcul (ils partent de sa fin).")},
             {"texte": _("Pour revenir au plan par plan : Edition › Préférences › IA locale, décochez « Faire d'un seul "
                         "calcul les plans d'un même moment ».")},
         ]},
        {"id": "relier_rushes", "etat": "ok",
         "titre": _("Recréer ce qui n'a pas été filmé entre deux rushes (relier deux plans)"),
         "mots": "relier raccord trou manquant pas filme entre deux rushes jonction reconstituer scene image clef keyframe sortie "
                 "attendre",
         "intro": _("La vidéo part de la dernière image du premier rush et arrive exactement sur la première image du suivant : "
                    "deux images réelles. Entre les deux, l'assistant prévoit les images clefs (quelqu'un qui attend, un "
                    "nouveau lieu), créées avec les fiches de vos personnes, objets et véhicules et les photos réelles des lieux, ou "
                    "prises dans un autre rush. Entre deux images clefs, les gestes s'enchaînent sur la vraie vidéo."),
         "etapes": [
             {"texte": _("Clic droit sur le premier des deux plans › « Continuer ce plan avec l'assistant IA… »."),
              "montrer": {"clic_droit": [_("Continuer ce plan avec l'assistant IA…")]}, "fait": "fenetre:DialogueAssistant"},
             {"texte": _("Racontez ce qui s'est passé entre les deux et choisissez « Ce qui n'a pas été filmé entre ce plan et le "
                         "suivant ».")},
             {"texte": _("Qui et quoi : l'image montre avant | après ; vérifiez le cadre de chaque personne, objet ou véhicule.")},
             {"texte": _("Les images : cochez « Image clef » là où la scène doit être respectée ; « Créer… » (dites ce qu'on voit et "
                         "le cadrage) ou « Image de la ligne rouge » pour une vraie image d'un rush.")},
             {"texte": _("Fabriquez, regardez, puis « Poser dans le film » : la reconstitution s'insère entre les deux rushes.")},
         ]},
        {"id": "images_une_a_une", "etat": "ok",
         "titre": _("Avancer image par image et supprimer quelques images d'un rush"),
         "mots": "image par image frame trame avancer reculer supprimer images couper precis une image rush debut fin partie jaune",
         "intro": _("Au-dessus de la timeline, ◀| et |▶ avancent d'une image exactement ; [ et ] choisissent les images à retirer "
                    "(la partie jaune, l'image affichée comprise) ; « Supprimer N image(s) » les retire et recolle la suite."),
         "etapes": [
             {"texte": _("Agrandissez la timeline (+ ou molette) pour bien voir les images.")},
             {"texte": _("◀| ou |▶ (ou les flèches du clavier) jusqu'à la première image à retirer, puis [ .")},
             {"texte": _("|▶ jusqu'à la dernière image à retirer, puis ] (Maj + flèche : une image de plus ou de moins).")},
             {"texte": _("« Supprimer N image(s) » : la suite se recolle. Ctrl+Z revient.")},
         ]},
        {"id": "assistant_musique", "etat": "ok",
         "titre": _("Créer une musique ou une chanson guidé pas à pas (style d'un groupe, voix, paroles, passage lent)"),
         "mots": "assistant musique chanson ballade rock style groupe a la maniere voix feminine chaude paroles tempo lent rapide "
                 "partie deroule reorchestrer morceau guide",
         "intro": _("Dites en quelques mots la musique voulue (« une chanson pop de 2 minutes, joyeuse, avec un passage calme au "
                    "milieu, dans le style d'un de mes morceaux, voix de femme »). L'assistant en déduit trois cartes (style, voix, "
                    "paroles) et le déroulé ; pour chaque carte vous choisissez d'où elle vient, chaque possibilité expliquée. La "
                    "musique est créée partie par partie à son tempo, sur ce poste, puis enchaînée."),
         "etapes": [
             {"texte": _("Fabrique IA › Musique › « Assistant de création : une musique ou une chanson… »."),
              "montrer": {"menu": [_("Fabrique IA"), _("Musique"), _("Assistant de création : une musique ou une chanson, guidé pas à pas…")]},
              "fait": "fenetre:DialogueAssistant"},
             {"texte": _("Ecrivez votre idée (« ✨ Améliorer » si vous voulez), puis « Voir ce qu'il faut ».")},
             {"texte": _("Carte Style : un morceau à vous ou trouvé en ligne, puis « S'en inspirer » (style mesuré) ou « Repartir du "
                         "morceau » (seulement à vous ou libre, déclaré) ; ou le décrire, ou la liste.")},
             {"texte": _("Carte Voix : la voix d'un morceau, « Décrire sa manière de chanter » ou « Garder son timbre » (accord de la "
                         "personne) ; « A changer dans cette voix » : plus féminine, plus chaude… ; ou la décrire, la liste, aucune.")},
             {"texte": _("Le déroulé : une ligne par partie (durée, tempo, énergie, chantée) ; « Recaler les parties » sur la durée totale.")},
             {"texte": _("Les paroles : écrivez-les ou « Ecrire avec l'IA », une balise par partie chantée ; « ✨ Améliorer » propose une "
                         "version, vous choisissez.")},
             {"texte": _("« Créer la musique » : chaque partie à son tempo, puis l'enchaînement. Ecoutez les raccords, « Refaire la "
                         "partie choisie » si besoin, puis « Poser sous la vidéo ».")},
         ]},
        {"id": "assistant_intro", "etat": "ok",
         "titre": _("Créer une intro ou un logo animé guidé pas à pas (logo, style, fond, son)"),
         "mots": "assistant intro logo anime generique ouverture fin titre jingle whoosh impact bruitage fond style cinema guide",
         "intro": _("Dites en quelques mots l'intro voulue (« 3 s style cinéma avec mon logo et un impact »). L'assistant en déduit "
                    "quatre cartes : le logo (un des vôtres, une image, dessiné par l'IA, de la bibliothèque, aucun), le style (un "
                    "modèle animé, sa couleur), le fond (dégradé, uni, images du film, posé sur le film, une image) et le son (bruitage, "
                    "jingle créé sur ce poste, un son à vous). Puis le titre, l'aperçu animé, la fabrication avec le son, et la pose."),
         "etapes": [
             {"texte": _("Fabrique IA › Logo, intro et vignette › « Assistant de création : une intro ou un logo animé… »."),
              "montrer": {"menu": [_("Fabrique IA"), _("Logo, intro et vignette"),
                                   _("Assistant de création : une intro ou un logo animé, guidé pas à pas…")]},
              "fait": "fenetre:DialogueAssistant"},
             {"texte": _("Ecrivez votre idée, puis « Voir ce qu'il faut ».")},
             {"texte": _("Vérifiez les cartes Logo, Style, Fond et Son ; choisissez d'où vient chacun.")},
             {"texte": _("Le titre et le sous-titre (« ✨ Améliorer »), la durée, où la poser : l'aperçu animé suit.")},
             {"texte": _("« Fabriquer l'intro » : regardez-la avec son son, puis « Poser l'intro ». « ☆ Garder ce style d'intro » "
                         "pour refaire la même allure plus tard.")},
         ]},
        {"id": "bibliotheque_creations", "etat": "ok",
         "titre": _("Garder un personnage, un lieu, une voix ou un style pour le réutiliser (ma bibliothèque de créations)"),
         "mots": "bibliotheque garder reutiliser personnage musicien lieu endroit decor objet voix chanteur chanteuse narration style "
                 "nommer musique image fiche creer",
         "intro": _("Ce que vous gardez se réutilise tel quel : la fiche d'un personnage (sans la repayer), un lieu, une voix décrite ou "
                    "son timbre (avec accord), un style nommé, une musique. La bibliothèque est rangée avec vos réglages : elle vous "
                    "suit sur vos autres postes, et servira aussi aux autres logiciels PhilFactory. On n'y range que sur clic."),
         "etapes": [
             {"texte": _("Dans l'assistant de création, « ☆ Garder » sur une carte (ou sur une fiche, à l'étape des images ; ou "
                         "sur la musique créée) : donnez-lui un nom.")},
             {"texte": _("Pour la reprendre : sur une carte, « Dans ma bibliothèque », puis choisissez-la dans la liste.")},
             {"texte": _("Fabrique IA › « Ma bibliothèque de créations… » : voir, chercher, renommer, retirer ; « Nouveau… » pour "
                         "créer un personnage, un musicien, un lieu, une voix, un style ; « Faire sa fiche », « Décrire d'après un "
                         "morceau », « Ecouter un morceau ».")},
         ]},
        {"id": "maj_ia", "etat": "ok",
         "titre": _("Mettre à jour les IA (moteurs et modèles locaux, services cloud)"),
         "mots": "mise a jour maj ia modele moteur version nouvelle ancienne revenir retour arriere essai cloud prix fal retire "
                 "remplace catalogue",
         "intro": _("Les IA changent souvent. Chaque semaine, PhilCut regarde s'il y a du nouveau et le dit dans la barre du bas "
                    "(« ✦ IA : … mise(s) à jour ») ; rien ne s'installe sans vous. Chaque mise à jour est essayée : si l'essai "
                    "rate, l'ancienne version revient toute seule. Les IA cloud, elles, se mettent à jour chez leur fournisseur : "
                    "PhilCut relit leur adresse et leur prix, et remplace un service retiré en vous le disant."),
         "etapes": [
             {"texte": _("Aide › « Mises à jour des IA (locales et cloud)… » (ou le bouton dans la barre du bas)."),
              "montrer": {"menu": [_("Aide"), _("Mises à jour des IA (locales et cloud)…")]},
              "fait": "fenetre:DialogueMajIA"},
             {"texte": _("Onglet « Sur ce poste » : cochez ce que vous voulez, « Mettre à jour la sélection ». Le téléchargement "
                         "continue si vous fermez ou réduisez la fenêtre.")},
             {"texte": _("Si une IA marche moins bien : « Revenir » dans « Anciennes versions gardées ». « Libérer la place » "
                         "efface ces anciennes versions.")},
             {"texte": _("Onglet « Dans le cloud » : chaque service, à quoi il sert, son prix indicatif et son état. Le prix est "
                         "toujours redemandé avant de payer.")},
             {"texte": _("Pour ne plus chercher chaque semaine : Préférences › IA locale, décochez « Chercher les mises à jour "
                         "des IA ».")},
         ]},
        {"id": "personnages", "etat": "ok",
         "titre": _("Garder le même personnage d'un plan à l'autre (Séquence IA)"),
         "mots": "personnage personne jouer parler replique dialogue visage acteur histoire sequence ressemblant fidele identique "
                 "fiche planche reference kling enchainer raccord table traverse",
         "intro": _("Une seule image de départ ne suffit pas : le moteur invente le reste et le visage dérive. Quatre verrous : la "
                    "fiche du personnage (face, profil, en pied), l'image de départ, l'image d'arrivée, et le moteur « Kling O3 "
                    "Référence » qui garde le visage ; chaque plan démarre sur la dernière image du précédent. Seulement des "
                    "personnes d'accord, jamais une célébrité."),
         "etapes": [
             {"texte": _("Fabrique IA › Vidéo › « Histoire en plusieurs plans (Séquence IA)… » : écrivez la scène, une action "
                         "simple par plan."),
              "montrer": {"menu": [_("Fabrique IA"), _("Vidéo"), _("Histoire en plusieurs plans (Séquence IA)…")]},
              "fait": "fenetre:DialogueSequence"},
             {"texte": _("Onglet des personnages : cliquez la ligne › « Images du personnage… » (une image nette de face, bien "
                         "éclairée), puis « Fiche personnage… » : regardez la planche avant de la garder.")},
             {"texte": _("Moteur « Kling O3 Référence : personnage fidèle (fal) » ; laissez cochées « Image de départ » et « Image "
                         "d'arrivée et fiche personnage » : le plan doit rejoindre la pose finale, il ne traverse plus la table.")},
             {"texte": _("Dans chaque plan, « Enchaîner » (coché d'office) : le plan démarre sur la dernière image du précédent. "
                         "Jusqu'à 15 s par plan ; le prix total est demandé avant l'envoi.")},
             {"texte": _("Un plan raté ? Refaites seulement celui-là ; les suivants repartent de sa nouvelle dernière image.")},
         ]},
        {"id": "rallonger", "etat": "ok",
         "titre": _("Rallonger un rush ou créer sa suite (même personnage)"),
         "mots": "rallonger prolonger allonger suite continuer fin rush plan plus long 6 secondes duree extend",
         "intro": _("La suite démarre sur la dernière image exacte du plan : le raccord est parfait. Sur ce poste (gratuit, moins "
                    "fidèle) ou par le cloud (Kling O3 Référence : les personnes et objets du plan sont gardés, jusqu'à 15 s, prix "
                    "demandé avant). Plus long encore : prolongez le morceau posé, il repart de sa propre fin."),
         "etapes": [
             {"texte": _("Cliquez le plan dans la timeline."), "fait": "plan_choisi"},
             {"texte": _("Clic droit sur le plan › « Prolonger ce plan (image tenue, ralenti ou IA)… »."),
              "montrer": {"clic_droit": [_("Prolonger ce plan (image tenue, ralenti ou IA)…")]}, "fait": "fenetre:DialogueProlonger"},
             {"texte": _("« Comment » : « Prolongé par l'IA cloud, fidèle » ; la durée (jusqu'à 15 s) ; « Suite » : ce qui se passe "
                         "ensuite, dans votre langue (l'anglais envoyé reste visible et modifiable).")},
             {"texte": _("« Fabriquer », regardez, puis « Poser dans le film » : la suite du montage est décalée, Ctrl+Z l'enlève.")},
         ]},
        {"id": "credit_ia", "etat": "ok",
         "titre": _("Voir le crédit restant chez l'IA et le recharger"),
         "mots": "credit solde reste argent recharger payer compte fal gemini prix cout budget",
         "intro": _("Les fenêtres qui paient un calcul (Séquence IA, Prolonger, Faire parler) montrent le crédit fal.ai restant et "
                    "un bouton « Recharger… » qui ouvre votre compte. Google ne donne pas le solde d'une clef Gemini : le bouton "
                    "ouvre le suivi des dépenses."),
         "etapes": [
             {"texte": _("Ouvrez par exemple la Séquence IA, choisissez un moteur fal.ai : la ligne « Crédit fal.ai restant » "
                         "apparaît sous le prix.")},
             {"texte": _("« Recharger… » ouvre la page de facturation de fal.ai dans le navigateur ; le solde se relit à la "
                         "prochaine ouverture de la fenêtre.")},
         ]},
        {"id": "liaison", "etat": "ok",
         "titre": _("Lier deux rushes par un plan de passage"),
         "mots": "liaison lier raccord passage transition entre deux rushes plans enchainer vide trou",
         "intro": _("Un plan de liaison part de la dernière image du premier rush et arrive à la première image du suivant. "
                    "PhilCut mesure les deux images et propose des passages ; une IA peut aussi les regarder pour proposer mieux. "
                    "Trois façons de fabriquer : transition 3D (gratuite), IA de ce poste (gratuite), Gemini Omni (prix annoncé)."),
         "etapes": [
             {"texte": _("Cliquez le premier des deux plans dans la timeline (ou faites un clic droit dans le vide entre eux : "
                         "« Remplir ce vide par un plan de liaison… »)."), "fait": "plan_choisi"},
             {"texte": _("Clic droit sur ce plan › « Plan de liaison avec le plan suivant… ». La fenêtre montre les deux images "
                         "du raccord et des propositions."),
              "montrer": {"clic_droit": [_("Plan de liaison avec le plan suivant…")]}, "fait": "fenetre:DialogueLiaison"},
             {"texte": _("Ou par le menu : Montage › Pistes et passage choisi › « Plan de liaison entre deux plans… » (la ligne "
                         "rouge sur le premier plan)."),
              "montrer": {"menu": [_("Montage"), _("Pistes et passage choisi (partie jaune)"), _("Plan de liaison entre deux plans…")]},
              "fait": "fenetre:DialogueLiaison"},
             {"texte": _("Choisissez une proposition, ou « Analyser avec l'IA de ce poste » pour des idées qui tiennent compte de ce "
                         "que montrent les images. La consigne reste modifiable.")},
             {"texte": _("Choisissez comment fabriquer, cochez l'accord des personnes visibles si c'est une IA, puis « Fabriquer le "
                         "plan ». Regardez le résultat ; refabriquez si besoin.")},
             {"texte": _("« Poser entre les deux plans » : la suite du film se décale d'autant. Edition › Annuler revient en arrière."),
              "fait": "liaison"},
         ]},
        {"id": "narration", "etat": "ok",
         "titre": _("Illustrer ce qui est dit : vidéo de narration"),
         "mots": "narration illustrer voix off explication images plans b-roll presentateur commentaire explicative tuto",
         "intro": _("La voix d'abord : PhilCut la transcrit sur ce poste, la découpe en idées et propose une image animée pour "
                    "chacune, posée exactement sous les mots. Un présentateur inventé peut apparaître et dire la voix. "
                    "Fabrication par le cloud, prix total demandé avant."),
         "etapes": [
             {"texte": _("Posez la voix (piste Voix : enregistrement, voix IA…), puis clic droit dessus › « Illustrer ce qui est dit "
                         "(vidéo de narration)… », ou Fabrique IA › Vidéo › « Vidéo de narration d'après ce qui est dit… »."),
              "montrer": {"menu": [_("Fabrique IA"), _("Vidéo"), _("Vidéo de narration d'après ce qui est dit…")]},
              "fait": "fenetre:DialogueNarration"},
             {"texte": _("« Ecouter et découper » : la voix est transcrite et coupée en idées de 2 à 8 secondes.")},
             {"texte": _("Choisissez le rendu ; cochez « Un présentateur… » si vous voulez le voir parler par moments (une image, ou "
                         "« Le créer avec Gemini »).")},
             {"texte": _("Relisez les images proposées (modifiables), ou « Idées d'images avec l'IA ».")},
             {"texte": _("Choisissez le moteur, « Fabriquer les plans » (prix demandé), regardez chaque ligne, puis « Poser sous les "
                         "mots ». Edition › Annuler pour revenir.")},
         ]},
        {"id": "clip_groupe", "etat": "ok",
         "titre": _("Créer le clip d'un groupe d'après une chanson"),
         "mots": "clip groupe concert scene chanson musique musiciens chanteur batteur guitariste video clip dessin anime refrain",
         "intro": _("PhilCut écoute la chanson (tempo, mesures, intro, couplets, refrains, voix), invente le groupe et propose les "
                    "plans calés sur les mesures. Vous corrigez tout ; la fabrication passe par le cloud, prix total demandé avant. "
                    "Des musiciens inventés, jamais un vrai groupe."),
         "etapes": [
             {"texte": _("Clic droit sur la chanson dans la timeline › « Créer le clip du groupe d'après ce morceau… » (ou Fabrique "
                         "IA › Vidéo › « Clip de groupe d'après une chanson… »). Depuis la Fabrique musique : ligne « Clip vidéo » "
                         "avant de créer, la fenêtre s'ouvre quand le morceau est posé."),
              "montrer": {"menu": [_("Fabrique IA"), _("Vidéo"), _("Clip de groupe d'après une chanson…")]},
              "fait": "fenetre:DialogueClipGroupe"},
             {"texte": _("« Ecouter le morceau » : la bande de couleurs montre les parties ; gardez « Séparer la voix » pour que le "
                         "chanteur chante au bon moment.")},
             {"texte": _("Lieu (concert ou ailleurs), dessin animé ou non ; décrivez les musiciens comme vous les voulez.")},
             {"texte": _("Relisez les plans (modifiables), ou « Idées avec l'IA » ; gardez « Un refrain qui revient reprend les "
                         "plans du premier » pour payer moins.")},
             {"texte": _("Choisissez le moteur, cochez « Musiciens inventés », « Fabriquer les plans » (prix demandé). Vous pouvez "
                         "fermer : la barre du bas suit.")},
             {"texte": _("Cliquez chaque ligne pour regarder le plan, puis « Poser le clip sous la chanson ». Edition › Annuler "
                         "pour revenir.")},
         ]},
        {"id": "levres", "etat": "ok",
         "titre": _("Faire parler un personnage sur ma voix (lèvres synchronisées)"),
         "mots": "levres bouche parler synchroniser lipsync personnage presentateur avatar chanter chanteur voix doublage",
         "intro": _("Le son d'abord : posez la voix (ou la chanson) sur la timeline, puis le moteur fabrique les lèvres dessus. "
                    "Un plan déjà fait garde tout sauf la bouche ; une image du personnage devient une vidéo complète. Calcul par "
                    "fal.ai (clef à connecter une fois), prix annoncé avant. Jamais une personnalité."),
         "etapes": [
             {"texte": _("Posez la voix sous le plan (piste Voix : enregistrement, voix IA, « Continuer avec ma voix »…).")},
             {"texte": _("Un plan déjà fait : clic droit sur le plan › « Faire parler ce plan sur le son dessous… ». Une image : "
                         "Fabrique IA › Vidéo › « Personnage qui parle (une image et votre son)… »."),
              "montrer": {"clic_droit": [_("Faire parler ce plan sur le son dessous…")]}, "fait": "fenetre:DialogueLevres"},
             {"texte": _("Vérifiez la ligne bleue « Son : ce qui passe de … à … ». Musique derrière ou chanson : cochez « Isoler "
                         "d'abord la voix ».")},
             {"texte": _("Choisissez le moteur (le prix s'affiche), cochez la case du visage, puis « Faire parler ». Vous pouvez "
                         "fermer la fenêtre : la barre du bas suit le calcul.")},
             {"texte": _("Regardez le résultat, puis « Poser à la place du plan » (ou « au-dessus du film ») : le son reste celui "
                         "de la timeline. Edition › Annuler pour revenir.")},
             {"texte": _("Gratuit sur ce poste (Windows, carte NVIDIA de 8 Go) : installez une fois « Lèvres synchronisées sur ce "
                         "poste » dans Edition › Préférences › IA locale (environ 9 Go), puis choisissez le moteur « LatentSync 1.5 "
                         "sur ce poste ».")},
         ]},
        {"id": "musique_maniere", "etat": "ok",
         "titre": _("Créer une musique à la manière de… (style, voix, passage d'un morceau)"),
         "mots": "musique maniere style comme metal compositeur groupe chanteur voix chanter inspirer passage refrain morceau decrire",
         "intro": _("La Fabrique musique crée sur ce poste, gratuitement. « À la manière de » décrit un style ou une manière de "
                    "chanter, jamais un nom ni une voix copiée ; la liste s'enrichit en ligne. On peut aussi s'inspirer d'un passage "
                    "d'un morceau, ou décrire la voix d'une chanson."),
         "etapes": [
             {"texte": _("Fabrique IA › Musique › « Créer une musique par IA (Fabrique musique)… »."),
              "montrer": {"menu": [_("Fabrique IA"), _("Musique"), _("Créer une musique par IA (Fabrique musique)…")]},
              "fait": "fenetre:DialogueFabriqueMusique"},
             {"texte": _("Ligne Phrase › « Style « à la manière de »… » : choisissez une famille ou tapez (« metal », « Einaudi »…), "
                         "double-cliquez un nom. Absent de la liste ? « Utiliser », puis « Améliorer avec l'IA ».")},
             {"texte": _("Ligne Voix › « À la manière de… » : une manière de chanter connue, ou « Décrire la voix d'un morceau » : "
                         "choisissez le passage où la voix chante, PhilCut l'isole de la musique et la décrit (registre, vibrato, "
                         "timbre).")},
             {"texte": _("« S'inspirer d'un morceau » › Choisir un morceau : un fichier, ou en ligne (« S'inspirer de ce morceau » "
                         "télécharge tout seul ; « Plus de résultats » si besoin). Gardez tout le morceau ou seulement un passage.")},
             {"texte": _("Relisez la consigne anglaise en bas, puis « Créer la musique ».")},
         ]},
        {"id": "voix_retouches", "etat": "ok",
         "titre": _("Retoucher une voix (studio, narration, plus grave ou plus aiguë) et l'entendre"),
         "mots": "voix retouche studio narration diction grave aigu timbre feminine masculine changer transformer ecouter "
                 "ameliorer radio echo appliquer rush plans",
         "intro": _("Les retouches se posent sur le plan et se rendent à l'export ; « Ecouter » fait entendre 15 s avec elles, à "
                    "partir de la ligne rouge. Un seul traitement complet à la fois (studio, narration…) : en cocher un remplace "
                    "l'autre ; les petites retouches (plus grave, plus chaude, « s » qui sifflent…) s'ajoutent. Pour changer "
                    "vraiment la voix (masculine, féminine, enfant), « Transformer la voix… »."),
         "etapes": [
             {"texte": _("Cliquez le plan de la voix dans la timeline (piste Voix, ou un rush avec du son)."), "fait": "plan_choisi"},
             {"texte": _("Inspecteur (volet de droite), groupe « Voix et son » : cochez les retouches voulues.")},
             {"texte": _("« ▶ Ecouter avec ces retouches » : 15 s jouées depuis la ligne rouge ; second clic pour arrêter. Depuis le "
                         "bouton « Voix et son » de la barre, choisir une retouche la fait entendre aussitôt.")},
             {"texte": _("« Appliquer à… » : les mêmes retouches sur les plans sélectionnés, toute la piste, ou tous les plans du "
                         "même rush (Ctrl+Z pour revenir).")},
         ]},
        {"id": "voix_transformer", "etat": "ok",
         "titre": _("Transformer une voix : plus grave, plus aiguë, masculine, féminine, enfant"),
         "mots": "voix transformer changer grave aigue masculine feminine homme femme enfant timbre hauteur narrateur diction",
         "intro": _("Sur ce poste : hauteur et timbre réglés, gratuit, s'entend aussitôt (un peu artificiel si on force). IA cloud : "
                    "la voix est redite par une voix toute faite avec vos intonations, plus naturel (0,30 $ la minute, prix "
                    "demandé). Seulement votre voix ou celle d'une personne d'accord."),
         "etapes": [
             {"texte": _("Cliquez le plan de la voix dans la timeline."), "fait": "plan_choisi"},
             {"texte": _("Inspecteur › « Voix et son » › « Transformer la voix… » (ou bouton Voix et son de la barre)."),
              "fait": "fenetre:DialogueVoixTransfo"},
             {"texte": _("Sur ce poste : choisissez « Plus masculine », « Plus féminine »… ou réglez hauteur et timbre, « ▶ Ecouter », "
                         "puis « Appliquer au plan ».")},
             {"texte": _("Par l'IA cloud : choisissez la nouvelle voix, cochez l'accord, « Transformer », écoutez, puis « Poser sur "
                         "la piste Voix » (le son d'origine du plan est coupé ; Ctrl+Z pour revenir).")},
         ]},
        {"id": "suivre_element", "etat": "ok",
         "titre": _("Une flèche, un texte ou un goodie qui suit une personne ou un objet"),
         "mots": "fleche suivre suit accrocher goodie texte etiquette personne objet avion voiture narration montrer designer",
         "intro": _("Un élément posé (flèche, étiquette, goodie, image) peut suivre une personne ou un objet du plan : il se déplace "
                    "avec lui, à l'export comme à l'aperçu."),
         "etapes": [
             {"texte": _("Posez la flèche (bouton Goodies) ou le texte au-dessus du plan, au moment voulu.")},
             {"texte": _("Clic droit sur l'élément dans la timeline › « Accrocher à une personne (suit ses mouvements)… ».")},
             {"texte": _("La personne est trouvée seule ; pour un objet (avion, voiture), tracez un cadre autour à la souris, puis OK : "
                         "la barre du bas suit le calcul.")},
             {"texte": _("Pour un suivi précis (le sujet se tourne, se cache un instant, change de taille) : cochez « Suivi précis par "
                         "l'IA cloud » avant OK ; le prix (quelques centimes) est demandé. Pour une zone floutée : Inspecteur › « Suivre "
                         "précisément (IA cloud) ».")},
             {"texte": _("Il décroche à un moment ? Clic droit sur l'élément › « Décrocher (position fixe) », puis accrochez-le à nouveau.")},
         ]},
        {"id": "tampons_son", "etat": "ok",
         "titre": _("Créer un tampon IA avec un vrai son (voix, tambour, cymbales…)"),
         "mots": "tampon ia son bruitage bruit tambour cymbale voix commentateur gemini cloud victoire animation",
         "intro": _("La phrase d'image ne fait aucun son : le son se décrit à part. « Son : IA cloud » fabrique les bruitages "
                    "d'après la vidéo du tampon (fal.ai, environ 0,001 $ la seconde) et fait dire la phrase par la voix Gemini, "
                    "dans le style choisi. Sur ce poste, gratuit, les sons sont plus simples."),
         "etapes": [
             {"texte": _("Menu Montage › « Tampons vidéo… », onglet « Tampons IA » ; choisissez un modèle.")},
             {"texte": _("« Phrase dite » : les mots dits à voix haute (« Victoire ! »). « Son décrit » : les bruitages (« roulement "
                         "de tambour, quelques cymbales »). Ecrit dans la phrase d'image, le son y est retiré et passé à « Son décrit ».")},
             {"texte": _("« Son » : « IA cloud : voix Gemini, bruitages d'après la vidéo » ; le prix est demandé, le crédit fal.ai "
                         "restant s'affiche.")},
             {"texte": _("« Créer ce tampon » : il rejoint « Ma bibliothèque » ; « ▶ Écouter » pour l'entendre.")},
         ]},
        {"id": "voix_musique", "etat": "ok",
         "titre": _("Retirer la voix d'une musique (garder la musique)"),
         "mots": "retirer enlever voix chant musique instrumental karaoke separer bruit vent ambiance isoler",
         "intro": _("PhilCut sépare le son en voix, musique et bruits de fond, sur ce poste. Les trois pistes ensemble redonnent le "
                    "son d'origine : on garde ce qu'on veut. Il faut une fois le modèle « Séparer voix, musique et bruits » "
                    "(Préférences › IA locale, environ 170 Mo)."),
         "etapes": [
             {"texte": _("Cliquez le plan (ou la musique) dans la timeline."), "fait": "plan_choisi"},
             {"texte": _("Clic droit sur le plan › « Séparer voix, musique et bruits… »."),
              "montrer": {"clic_droit": [_("Séparer voix, musique et bruits…")]}, "fait": "fenetre:DialogueSeparation"},
             {"texte": _("« Retirer la voix » (ou « Garder la voix seule », ou « Les trois pistes »), puis « Séparer » : la progression "
                         "s'affiche. Ecoutez chaque piste.")},
             {"texte": _("« Poser dans le film » : les pistes se posent sous le plan, le son d'origine est coupé. Edition › Annuler "
                         "pour revenir."), "fait": "separe"},
             {"texte": _("Pour un fichier qui n'est pas dans le film : Fabrique IA › Musique › « Séparer voix, musique et bruits… »."),
              "montrer": {"menu": [_("Fabrique IA"), _("Musique"), _("Séparer voix, musique et bruits…")]}},
         ]},
        {"id": "suivi", "etat": "ok",
         "titre": _("Suivre une personne et recadrer"),
         "mots": "suivre suivi personne recadrer recadrage cadrage vertical short reel 9:16",
         "intro": _("Le cadre suit la personne tout seul ; utile surtout pour un film vertical (Shorts, Reels)."),
         "etapes": [
             {"texte": _("Cliquez le plan dans la timeline."), "fait": "plan_choisi"},
             {"texte": _("Clic droit sur le plan › Cadrage › « Suivre la personne (recadrage automatique)… »."),
              "montrer": {"clic_droit": [_("Cadrage"), _("Suivre la personne (recadrage automatique)…")]}, "fait": "suivi"},
             {"texte": _("Le suivi se trompe à un moment ? Ligne rouge à cet instant, clic droit sur le plan › Cadrage › « Corriger "
                         "le suivi à la ligne rouge… », retracez la zone : la suite est refaite."),
              "montrer": {"clic_droit": [_("Cadrage"), _("Corriger le suivi à la ligne rouge…")]}},
         ]},
        {"id": "projets_cloud", "etat": "ok",
         "titre": _("Retrouver mes projets et mes rushes sur un autre PC (cloud)"),
         "mots": "cloud pcloud drive nas projet autre pc poste ordinateur ouvrir enregistrer retrouver rushes original copie",
         "intro": _("Chaque compte a son rôle : un pour les réglages, un pour déposer et retrouver les projets, un pour les rushes "
                    "(gros fichiers). Un projet ouvert depuis un compte y retourne à chaque Enregistrer ; sur un autre PC, chaque rush "
                    "absent se télécharge au choix en copie légère ou en original."),
         "etapes": [
             {"texte": _("Edition › Préférences › Comptes et synchro : ajoutez vos comptes (pCloud, Google Drive, NAS…), puis, dans "
                         "« Rôle de chaque compte », choisissez le compte des projets et celui des rushes."),
              "montrer": {"menu": [_("&Edition"), _("Préférences…")]}},
             {"texte": _("Projet ouvert : Fichier › « Enregistrer le projet vers un emplacement (cloud, NAS)… ». Ensuite, chaque "
                         "Enregistrer le renvoie là-bas (☁ devant son nom)."),
              "montrer": {"menu": [_("&Fichier"), _("Enregistrer le projet vers un emplacement (cloud, NAS)…")]}},
             {"texte": _("Pour l'autre PC : après l'enregistrement, cochez « Les originaux » (ou la copie légère) des rushes à "
                         "déposer.")},
             {"texte": _("Sur l'autre PC : Fichier › « Ouvrir un projet depuis un emplacement (cloud, NAS)… », ou double-clic sur le "
                         "projet dans l'Accueil (☁)."),
              "montrer": {"menu": [_("&Fichier"), _("Ouvrir un projet depuis un emplacement (cloud, NAS)…")]}},
             {"texte": _("Rushes absents : Fichier › « Médias introuvables sur ce poste… » : « Télécharger la copie légère » ou "
                         "« Télécharger l'original », rush par rush."),
              "montrer": {"menu": [_("&Fichier"), _("Médias introuvables sur ce poste…")]}},
         ]},
        {"id": "derniere_image", "etat": "ok",
         "titre": _("Passer d'un rush à l'autre par la dernière image ou une animation"),
         "mots": "derniere image figer arret sur image animer animation photo 3d transition fin",
         "intro": _("Arrêt sur la dernière image, image qui s'anime, ou transition classique entre les deux plans."),
         "etapes": [
             {"texte": _("Placez la ligne rouge sur la dernière image du premier rush.")},
             {"texte": _("Arrêt sur image : clic droit sur le plan › « Figer l'image à cet endroit (cadre photo, légende)… »."),
              "montrer": {"clic_droit": [_("Figer l'image à cet endroit (cadre photo, légende)…")]}},
             {"texte": _("Ou l'animer : Fabrique IA › Vidéo › Effet IA sur le film… › « Animer l'image » ou « Photo 3D à partir de "
                         "l'image (3 s) » › Créer, regarder, Poser."),
              "montrer": {"menu": [_("Fabrique IA"), _("Vidéo"), _("Effet IA sur le film (dessin animé, ralenti, agrandir, photo 3D…)…")]},
              "fait": "fenetre:DialogueAtelierIA"},
             {"texte": _("Ou une transition : volet Effets, cherchez « transition », glissez-la sur le début du plan qui arrive. "
                         "Montage › Montage automatique › « Transitions automatiques… » en pose une à chaque coupe."),
              "montrer": {"volet": "effets", "chercher": _("transition")}},
         ]},
    ]
    return G


ETATS = {"ok": ("✓", "#3fb950"), "partiel": ("◐", "#e3b341"), "a_venir": ("…", "#8a94a6")}


def libelle_etat(etat):
    return {"ok": _("Faisable aujourd'hui"), "partiel": _("En partie (avec un détour)"), "a_venir": _("Pas encore : prévu")}.get(etat, "")


def chercher(phrase):
    """Les guides qui répondent à une question (« comment retirer la voix »), du plus proche au moins proche."""
    mots = [m for m in _norm(phrase).replace("'", " ").split() if len(m) > 3 and m not in
            ("comment", "faire", "pour", "dans", "avec", "veux", "voudrais", "faut", "est-ce", "quoi", "rush", "rushes")]
    res = []
    for g in guides():
        cible = _norm(g["titre"] + " " + g.get("mots", ""))
        score = sum(1 for m in mots if m in cible or (len(m) > 5 and m[:5] in cible))
        if score:
            res.append((score, g))
    return [g for _s, g in sorted(res, key=lambda x: -x[0])]


# ---------------------------------------------------------------- « Montrez-moi »
def _trouver(actions, texte):
    n = _norm(texte)
    for a in actions:
        if a.isSeparator():
            continue
        t = _norm(a.text())
        if t == n or (n and t.startswith(n)) or (t and n.startswith(t) and len(t) > 6):
            return a
    return None


def surligner(menu, chemin, delai=180):
    """Dans un menu ouvert : surligne la ligne voulue, en ouvrant les sous-menus du chemin un par un."""
    from PySide6.QtCore import QTimer
    if not chemin or menu is None:
        return
    a = _trouver(menu.actions(), chemin[0])
    if a is None:
        return
    menu.setActiveAction(a)
    if a.menu() is not None and len(chemin) > 1:
        sous = a.menu()
        r = menu.actionGeometry(a)
        sous.popup(menu.mapToGlobal(r.topRight()))
        QTimer.singleShot(delai, lambda: surligner(sous, chemin[1:], delai))


def montrer_menu(fenetre, chemin):
    """Ouvre le menu de la barre (Montage, Fabrique IA…) et surligne la ligne du chemin. Renvoie False si introuvable."""
    from PySide6.QtCore import QTimer
    mb = fenetre.menuBar()
    top = _trouver(mb.actions(), chemin[0]) if chemin else None
    if top is None or top.menu() is None:
        return False
    mb.setActiveAction(top)
    QTimer.singleShot(200, lambda: surligner(top.menu(), chemin[1:]))
    return True


def clip_a_montrer(ed):
    """Le plan vidéo sous la ligne rouge (sinon celui choisi, sinon le premier)."""
    p = ed.projet
    c = p.clip_a(ed.timeline.position, "video") or ed._clip_selectionne()
    if not c:
        vs = sorted(p.clips_piste("video"), key=lambda x: x["debut"])
        c = vs[0] if vs else None
    return c


def montrer_clic_droit(ed, chemin):
    """Ouvre le menu du clic droit sur le plan sous la ligne rouge, ligne du chemin surlignée."""
    c = clip_a_montrer(ed)
    if not c:
        return False
    tl = ed.timeline
    tl.selectionner(c["id"])
    it = tl.items_clips.get(c["id"])
    if it is None:
        return False
    from PySide6.QtCore import QPointF
    r = it.sceneBoundingRect()
    x = min(max(r.left() + 20, tl.mapToScene(0, 0).x() + 20), r.right() - 10)
    pos = tl.viewport().mapToGlobal(tl.mapFromScene(QPointF(x, r.center().y())))
    tl.surligner_menu = list(chemin)
    t = tl.position if c["debut"] <= tl.position <= c["debut"] + 1e9 else c["debut"]
    tl.menu_clip(c, pos, t)
    return True


def montrer_volet(ed, onglet, chercher=""):
    noms = {"effets": ed.catalogue, "inspecteur": ed.inspecteur}
    w = noms.get(onglet)
    if w is None:
        return False
    i = ed.volet.indexOf(w)
    if i < 0:
        return False
    ed._ouvrir_volet(i)
    if chercher and hasattr(w, "recherche"):
        w.recherche.setText(chercher)
        w.recherche.setFocus()
    return True


def montrer(fenetre, ed, m):
    if not m:
        return False
    if "menu" in m:
        return montrer_menu(fenetre, m["menu"])
    if "clic_droit" in m and ed is not None:
        return montrer_clic_droit(ed, m["clic_droit"])
    if "volet" in m and ed is not None:
        return montrer_volet(ed, m["volet"], m.get("chercher", ""))
    return False


# ---------------------------------------------------------------- étapes faites
def est_fait(cond, ed):
    """PhilCut voit-il que l'étape est faite ?"""
    if not cond or ed is None:
        return False
    try:
        if cond == "plan_choisi":
            return ed._clip_selectionne() is not None
        if cond == "partie_jaune":
            return bool(ed.timeline.zone_valide())
        if cond == "separe":
            return any(c.get("separe_de") for c in ed.projet.clips)
        if cond == "voix_ia":
            return any(c.get("voix_ia") for c in ed.projet.clips)
        if cond == "liaison":
            return any(c.get("liaison") for c in ed.projet.clips)
        if cond == "suivi":
            return any(c.get("ajustement") == "suivi" for c in ed.projet.clips_piste("video"))
        if cond.startswith("effet:"):
            eid = cond.split(":", 1)[1]
            return any(any(e.get("id") == eid for e in (c.get("effets") or [])) for c in ed.projet.clips)
        if cond.startswith("fenetre:"):
            from PySide6.QtWidgets import QApplication
            nom = cond.split(":", 1)[1]
            return any(w.isVisible() and type(w).__name__ == nom for w in QApplication.topLevelWidgets())
    except (RuntimeError, AttributeError, TypeError):
        return False
    return False
