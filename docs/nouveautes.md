PhilCut pour Windows, tout en un (Python, Qt, OpenCV et FFmpeg embarques).
- PhilCut_portable.zip : a decompresser, aucune trace sur le PC (c'est la version de test).
- PhilCut_Setup.exe : installation sans droits administrateur.
Linux : PhilCut_linux_x86_64.tar.gz (FFmpeg du systeme : paquet ffmpeg). Flatpak a venir.
Guide de test : docs/guideline-tests.md

## Nouveautes de 1.1.14 (comprend tout ce qui est sorti depuis la 0.4.4)

### 1.1.14 (animation libre)
- Animation libre : quand l'IA donnait les styles d'un element sous forme d'objet, ils etaient tous perdus (couleurs, positions, transparence) : mots sans couleur, canons mal places, flammes visibles en etoiles des le debut. PhilCut accepte maintenant les deux ecritures ; les animations deja construites sont corrigees en relancant l'apercu.

### 1.1.13 (fabrication du tarmac)
- Kling O3 Reference : l'erreur HTTP 422 « End Image Url is not supported with Multi Prompt » est corrigee. Un plan avec image clef est maintenant toujours fabrique seul : il part de la vraie derniere image du plan d'avant et arrive sur son image clef ; les plans entre deux images clefs restent faits d'un seul calcul.
- Assistant, page « Votre idee » : « Reprendre une creation en cours… » reprend une video preparee sur ce poste (fiches, images clefs, plans deja faits), sans rien refaire ni payer deux fois.

### 1.1.12 (aide par discussion, groupe entier)
- Aide › « Demander a l'aide (discussion avec l'IA)… » : posez votre question en clair. L'aide recoit le manuel de PhilCut tire des vrais menus (barre et clic droit), des guides et de fiches d'aide mises a jour en ligne, l'etat du montage et, sur clic, une capture de l'ecran.
- Chaque reponse donne les etapes, « Montrez-moi » (le menu s'ouvre, la ligne est surlignee), « Le faire pour moi » (l'outil s'ouvre) ou une phrase pour « Dites-le en clair ». Un chemin invente par l'IA n'est jamais montre.
- Au choix : Claude ou Gemini avec votre clef (quelques centimes la question, le manuel est garde en cache), ou l'IA de ce poste (gratuit). Aussi dans « Dites-le en clair » et dans les guides (« Pas trouve ? »), et dans les Preferences.
- Clip de groupe : « ☆ Garder ce groupe… » range le groupe entier dans la bibliotheque, « Prendre un groupe de ma bibliotheque… » remet les memes musiciens, memes visages, dans le clip suivant. Le groupe se modifie aussi dans la bibliotheque (genre Groupe).

### 1.1.11 (atelier de creation : plans, image clef, video)
- Fabrication : une image de reference trop allongee (rapport largeur/hauteur hors de 0,4 a 2,5) est encadree de gris avant l'envoi : fini l'erreur HTTP 422 de fal.
- Relecture du remplacement : l'erreur « string argument without an encoding » est corrigee (toutes les images envoyees a l'IA sont converties).
- Les plans suivent le texte jusqu'au dernier evenement (roulage, decollage…), jusqu'a 14 plans.
- Cocher « Image clef » ne fait plus planter PhilCut, et un message dit comment la creer (« Creer… », environ 0,04 $) ou la prendre a la ligne rouge (gratuit).
- Un personnage nomme dans le texte (ex. « Pilote Maxime ») est repris directement de la bibliotheque.

### 1.1.10 (bibliotheque)
- Les boutons des photos (« Ajouter des photos… », « Decrire d'apres les photos… », « Image d'un rush… ») sont sur leur propre rangee : ils ne sortent plus de la fenetre.
- La fiche faite par Gemini reste en grand en haut de l'entree, meme si une photo est choisie comme vignette ; une ligne dit si la fiche est faite.
- Quand Gemini ne dessine pas une fiche d'apres des photos, le message conseille « Decrire d'apres les photos » puis « Invente ».

### 1.1.9 (apercu de l'animation libre)
- L'apercu leger etait faux : rendu en demi-taille, il decalait tout ce que l'IA place en pixels (cadeau en bas a droite, textes qui se chevauchent). Il garde maintenant la vraie mise en page, seule l'image est reduite (HyperFrames et Remotion).
- « Nouvelle animation » et « Construire » effacent l'apercu precedent : plus jamais l'ancienne animation a l'ecran.
- Les etapes signalees absentes par la verification n'empechent plus de fabriquer et de poser.

### 1.1.8 (double-clic, bruitages, verification des etapes)
- Double-clic sur un plan : une animation rouvre sa fenetre avec tout ce qui l'a faite, une creation IA son atelier, tout autre plan (rush, son, bruitage) ses reglages dans l'Inspecteur. Les effets et transitions restent au clic droit.
- Bruitages : poses sans fondus, a plein volume ; si l'IA n'a pas ecrit de sons, PhilCut les deduit de son plan (apparition, feu d'artifice, confettis, machine a ecrire, ouragan, explosion…).
- Animation libre : le plan se lit en entier (zone qui defile) ; « Verifier les etapes sur l'apercu » : l'IA regarde une image par etape et dit ce qui ne se voit pas, puis « Faire corriger ces erreurs ».

### 1.1.7 (bibliotheque : photos)
- Un clic sur une photo en fait la vignette de l'entree.
- « Decrire d'apres les photos… » : l'IA ecrit la description de ce qu'on voit (allure, cheveux, age apparent, tenue), sans jamais dire qui c'est ; avec « Invente », on cree quelqu'un de nouveau dans le meme esprit.
- Quand Gemini ne rend pas d'image, PhilCut dit pourquoi (ressemblance avec une personne reelle, contenu bloque…) et ce que Gemini a repondu.
- Une coupure de connexion avant l'envoi est reessayee une fois toute seule.

### 1.1.6 (animation libre : bruitages et musique)
- « Bruitages places par l'IA » : l'IA ecrit aussi la liste des sons de son plan (pop, boum, machine a ecrire, souffle, cymbale…), choisis parmi les bruitages de PhilCut. L'apercu les fait entendre ; ils sont poses avec l'animation sur des pistes de son, chacun modifiable.
- « Calee sur la musique du film » : les temps forts de la musique du montage, a partir de la ligne rouge, sont donnes a l'IA ; les moments forts tombent dessus et l'animation est posee au meme endroit.
- Les deux reglages sont aussi dans les Preferences (Assistant et IA).

### 1.1.4 (mes modeles)
- Fabrique musique : « Garder cette fiche comme modele… » et « Reprendre un modele… » (style, paroles, voix, inspiration, duree), sans avoir a creer la musique. Les morceaux deja gardes avec leur fiche se reprennent aussi.
- Animation libre : « Garder comme modele… » et « Reprendre un modele… » (description, moteur et code : rien a repayer).
- Les modeles sont dans « Ma bibliotheque de creations », sur tous vos postes.
- 1.1.5 : voix de reference comme avant (la question « C'est ma voix » ou « Une personne d'accord » : votre reponse fait foi).

### 1.1.3 (fenetres de travail)
- Toutes les fenetres de travail (Fabrique musique, Sequence IA, Atelier IA, plan de liaison, faire parler, continuer avec ma voix, separer les sons, narration, clip de groupe, assistant…) ont « Reduire », toujours visible. Fermer une fenetre qui contient un travail la range : le meme menu ou « Afficher la fenetre » dans la barre du bas la rouvre telle quelle. « Repartir de zero » ouvre une fenetre neuve.

### 1.1.2 (animation libre pour Remotion, recherche YouTube Music)
- Animation libre : au choix, ecrite pour HyperFrames ou pour Remotion (fenetre et Preferences). Changer de moteur fait reecrire l'animation par l'IA, meme allure et meme minutage.
- L'IA ecrit d'abord le plan, une ligne par etape avec ses secondes ; il s'affiche, chaque etape de votre texte doit y figurer, et PhilCut refuse un plan qui depasse la duree.
- « Reduire » toujours present ; fermer range la fenetre sans rien perdre ; « Nouvelle animation » repart de zero.
- YouTube Music : un nombre ecrit en lettres cherche aussi en chiffres (« seventeen » trouve « 17 ») ; les titres qui contiennent ce que vous cherchez passent en tete ; artiste et duree completes pour toute la liste.

### 1.1.1 (synchronisation)
- Un fichier supprime sur ce poste (par exemple une image remplacee dans la bibliotheque) n'est plus propose a « recevoir » a chaque ouverture. Le groupe s'appelle « Recevoir du Drive » (il n'y a pas besoin d'un autre poste).

### 1.1.0 (animation libre)
- Fabrique IA › Animation › « Animation libre : decrivez-la, l'IA la construit… » : vous decrivez l'animation en phrases ; l'IA (Claude) ecrit une vraie composition HyperFrames (dessins SVG, graphiques, particules, textes, aux couleurs de votre charte).
- PhilCut verifie la composition (regles du rendu image par image, « hyperframes lint »), montre un apercu leger rendu gratuitement sur ce poste, puis vous demandez des changements en phrases (« Version d'avant » pour revenir) ; une erreur trouvee repart a l'IA d'un clic.
- Fabrication en qualite sur ce poste (gratuit) ou chez HeyGen, puis pose au-dessus du film ou a la ligne rouge ; « Ouvrir le projet HyperFrames » pour la retoucher dans HyperFrames Studio ou Claude Code.

### 1.0.9 (remplacer un element : deux facons, et une relecture)
- « Gemini trouve et remplace tout seul » (conseille, rien a tracer ; un cadre l'aide s'il le faut) ou « Je place moi-meme » (on trace ou va le nouvel element, a sa taille, et on choisit son orientation : vers la gauche, la droite, de face, de trois quarts, de profil).
- Apres chaque essai, une relecture par l'IA compare avant, apres et la fiche de la bibliotheque : ancien element remplace, ressemblance, personnes inchangees, decor inchange, avec les defauts vus. Clic sur le resultat : avant / apres.

### 1.0.8 (brouillon de toute la sequence)
- Brouillon Gemini Omni : chaque plan part de la derniere image du plan d'avant du brouillon (ou de l'image clef), comme dans la vraie fabrication. Avant, plusieurs plans repartaient de la photo de depart et la scene recommencait.
- Bouton « Ouvrir le dossier » a cote de « Revoir le brouillon » : la sequence entiere et chaque plan.

### 1.0.7 (enregistrement)
- « Enregistrer » ne s'arrete plus sur « WinError 32 : le fichier est utilise par un autre processus » (Google Drive, OneDrive ou l'antivirus qui lit le projet a ce moment-la) : PhilCut reessaie quelques secondes.

### 1.0.6 (retours du test du tarmac)
- Assistant : une carte renommee en la prenant dans la bibliotheque (« Maxime » devenu « Pilote Maxime ») garde ses plans ; avant, le personnage disparaissait des plans et n'avait pas de fiche.
- Plans coupes en deux : le sujet est repris en entier (« Les deux femmes marchent », et non « Les marchent »).
- HeyGen : « Recharger… » ouvre platform.heygen.com/billing.

### 1.0.5 (remplacer un element de l'image)
- Clic droit sur un plan › « Remplacer un element de l'image par un de ma bibliotheque… » : on trace un cadre autour de ce qui doit disparaitre (un avion, une voiture), on dit ce que c'est, on choisit l'element de la bibliotheque qui le remplace ; Gemini refait l'image, le reste (personnes, decor, lumiere) ne change pas. On regarde avant de poser ; environ 0,04 $ par essai, accord des personnes demande.

### 1.0.4 (plantage au demarrage)
- Corrige un plantage de Windows (code 0xc0000374) quand la mise a jour se telechargeait pendant la synchronisation : les verifications de certificats par Windows passent desormais une par une.

### 1.0.3 (Higgsfield : Seedance 2.5, console developpeur)
- Nouveau moteur video « Seedance 2.5 (Higgsfield) » : texte vers video, 4 a 30 s, 720p, tous les formats (9:16 compris), son du moteur seulement si demande.
- « Recharger… » et « Connecter » de Higgsfield ouvrent la console developpeur (open.higgsfield.ai, cles d'API et solde).

### 1.0.2 (retours du 20/11)
- Sous-titres animes en 9:16 plus gros d'office (texte une fois et un tiers plus grand, lignes plus courtes pour tenir dans l'ecran).
- Higgsfield : PhilCut precise que l'API se recharge sur la console (console.higgsfield.ai), en dollars ; les credits du site higgsfield.ai ne servent pas a l'API.

### 1.0.1 (neuf types d'animation de plus, « Recharger… » pour chaque modele)
- Animation : camembert (parts d'un total), jauge en pourcentage, comparaison avant / apres (avec l'evolution en %), classement en barres horizontales, chiffres clefs en tuiles, chronologie (frise, une ligne par date), liste a points, citation (mot par mot, puis l'auteur), appel a l'action (un bouton « S'abonner » que la souris vient cliquer, pose au-dessus du film).
- Ces types se calent eux aussi sur la voix (chaque element arrive quand il est dit) ou sur la musique, et sortent pareil avec les quatre moteurs (PhilCut, HyperFrames sur ce poste ou chez HeyGen, Remotion).
- « Preparer avec l'IA » connait les nouveaux types (lignes, texte du bouton) ; les vignettes des propositions gardent leurs proportions.
- Fabrique IA › « Credits et recharges des IA… » : chaque service payant (Claude, Gemini, fal.ai, Higgsfield, HeyGen), a quoi il sert, ses modeles, son credit, ce que PhilCut y a depense ce mois, « Recharger… » et « Connecter… ».
- Fabrique (plan genere par IA) : la ligne de credit suit le modele choisi ; Preferences › Assistant et IA : « Recharger… » a cote de chaque clef ; fenetre Animation : le credit de l'IA qui prepare et corrige.
- Remotion : le projet installe se met a jour tout seul avec PhilCut (pas besoin de reinstaller le moteur).

### 1.0.0 (sous-titres animes, habillage, animations calees sur la voix ou la musique)
- Sous-titres animes : les mots dits du montage (transcrits sur ce poste si besoin), en mot surligne, mots qui sautent, un grand mot a la fois ou karaoke ; poses au-dessus du film, exactement sous la voix.
- Habillage : bandeau nom et fonction, barre de progression sur toute la video avec vos reperes comme chapitres, capture qui defile dans un cadre.
- « Caler sur » la voix (le chiffre finit de monter quand il est dit, chaque barre arrive quand son mois est dit, le record quand il est dit) ou sur les temps de la musique du montage.
- Un seul horaire commun : le moteur PhilCut, HyperFrames (poste ou HeyGen) et Remotion donnent le meme film, cale au meme instant.

### 0.9.99 (animations : motion design dans PhilCut)
- Fabrique IA › Animation (motion design) : chiffre qui monte, barres qui poussent, courbe qui se trace, titre anime, ou les trois a la suite. On ecrit ce qu'on veut (« Preparer avec l'IA » remplit la fiche sans inventer de chiffres) ou on colle ses donnees (Excel, Sheets, CSV) ; apercu immediat, trois propositions (style de la charte, plus vif, plus sobre), curseurs (vitesse, rebond, decalage, epaisseur, lueur, taille du texte), remarque a l'instant corrigee par l'IA.
- Quatre moteurs au choix, PhilCut conseille (★) et dit pourquoi : moteur maison (rien a installer), HyperFrames sur ce poste (gratuit, installe une fois, environ 200 Mo), HyperFrames chez HeyGen (cloud, environ 0,10 $ la minute, credit affiche et « Recharger… »), Remotion sur ce poste (licence gratuite a confirmer une fois ; installe depuis npm). Le meme film quel que soit le moteur.
- Transparent (pose au-dessus du film, MOV ProRes 4444), formats 16:9, 9:16, 1:1, 4:5, zones sures de Reels, Shorts et TikTok, chiffres a la francaise (34 390), source affichee.
- « Ma charte » : couleurs, polices, logo, allure, mouvement, a eviter ; tiree d'un logo, d'une image ou de votre site ; contraste verifie (« Rendre lisible ») ; elle suit sur vos autres postes.
- « Projet HTML (HyperFrames, Claude Code)… » : pour qui veut retoucher l'animation a la main ; PhilCut suffit pour tout le reste.
- Nouveaux fournisseurs avec leur clef et leur credit : HeyGen (rendu des animations) et Higgsfield (plans video Kling, Hailuo… en paiement a l'usage, sans abonnement).

### 0.9.98 (le Realisateur et son correcteur)
- Assistant de creation : « Le Realisateur enchaine tout » (coche en premiere page, et dans Preferences). Il prend dans la bibliotheque ce qui porte le meme nom, prepare plans et images clefs, montre le brouillon gratuit et ne s'arrete que sur le brouillon et avant de payer. « ‹ Precedent » le met en pause, « Relancer le Realisateur » le reprend.
- Relecture des plans par l'IA (proposee apres la fabrication, environ 0,01 $ par plan) : visages, objets, gestes, raccords ; chaque defaut est note avec son instant.
- « Ce qui ne va pas » : vos remarques ecrites a l'instant de l'apercu, ou avec l'instant dans le texte (« a 0:12 le pilote n'a plus sa barbe »).
- « Proposer une correction » : la cause probable (plan, fiche ou image clef), ce qui est refait et le prix ; rien n'est paye sans votre accord.
- Deux remarques sur le meme element : proposition de l'ecrire dans sa fiche et dans la bibliotheque.

### 0.9.97 (synchronisation et Centre d'activite)
- Quitter : la synchronisation de fond ne bloque plus la sortie (elle reprend au prochain lancement, rien n'est perdu).
- Synchronisation avec Google Drive environ deux fois plus rapide (un dossier demande une fois au lieu de deux).
- Centre d'activite : plus de defilement horizontal ni de bouton coupe ; la colonne Tache passe a la ligne.


### 0.9.96 (retours du premier vrai essai)
- Fabrication d'un seul tenant : plus d'erreur 422 de Kling (« Prompt must not exceed 512 characters ») : chaque plan d'un meme calcul a une consigne courte (l'action d'abord ; visages et objets tenus par les fiches).
- « Reponse de l'IA illisible » : Gemini reflechit avant de repondre et cette reflexion mangeait la reponse ; la place est laissee, une reponse abimee est reparee ou redemandee une fois.
- Preparer les images : une erreur en route (reseau, credit) ne fait plus perdre les fiches et images deja faites ; un delai depasse est reessaye une fois.
- Bibliotheque, « Image d'un rush… » : apres le cadre, choix « Isoler par Gemini » (le sujet seul, entier, sur fond blanc, environ 0,04 $), « Garder le cadre tel quel » ou, pour une personne avec le modele installe, « Detourer sur ce poste ». Le detourage approximatif (qui melangeait le pilote et l'avion) est retire.
- « Nouveau… » : le nom se tape tout de suite.
- Credits : a cote de chaque service, ce que PhilCut a depense ce mois (images, videos) ; fal.ai ne donne son solde qu'a une clef de portee « ADMIN ».


### 0.9.95 (credit et Recharger partout)
- Les fenetres qui utilisent une IA payante montrent le credit restant et un bouton « Recharger… » : Ma bibliotheque de creations (Gemini, Claude), Clip de groupe et Narration (Gemini, fal.ai), Plan de liaison (Gemini, Claude), Atelier de logo et Fabrique musique (Claude, Gemini) ; deja la : assistant, Sequence IA, Prolonger, Faire parler, Transformer la voix, Tampons.
- Credit epuise : le bouton « Recharger… » du service concerne passe en rouge.


### 0.9.94 (credit epuise dit en clair)
- Quand le credit Gemini, Claude ou fal.ai est epuise, le message le dit en francais, precise que rien n'a ete fait ni facture et donne l'adresse ou recharger (au lieu de « 402 : Your prepayment credits are depleted… »).


### 0.9.92 et 0.9.93 (levres sur ce poste)
- Faire parler un plan sur votre son, gratuitement, sur votre carte NVIDIA de 8 Go : moteur "LatentSync 1.5 sur ce poste" (Windows). A installer une fois dans Preferences › IA locale, "Levres synchronisees sur ce poste" (environ 9 Go : programme et modeles).
- Quand il est installe, c'est le moteur propose d'abord ; aucun cout, la barre du bas suit le calcul (visage, levres, recollage). Si la memoire de la carte manque ou si le visage est introuvable, la raison est dite.
- Le reperage du visage (InsightFace) est reserve a un usage non commercial.


### 0.9.91 (brouillon de toute la sequence)
- Assistant, etape des images : "Brouillon de toute la sequence…" pour voir la sequence entiere, a la bonne duree, avant de payer la vraie fabrication. Rien n'est pose dans le film.
- Trois facons : images et textes plan par plan (gratuit, immediat ; fondu vers l'image clef), IA video de ce poste (gratuit, lent), Gemini Omni 360p (video bon marche, prix demande).
- "Revoir le brouillon" le rouvre.


### 0.9.90 (sequences continues)
- Avec Kling O3 Reference, les plans qui se suivent jusqu'a la prochaine image clef (15 s et six plans au plus) sont fabriques d'un seul calcul : les gestes continuent d'un plan a l'autre, sans arret ni saut ; la video est ensuite coupee en ses plans. Meme prix (a la seconde).
- Dans la liste des plans, ⛓ relie les plans faits ensemble ; "Refaire ce plan…" refait aussi les plans suivants du meme calcul (ils partent de sa fin).
- Meme chose dans la Sequence IA. Preferences › IA locale : "Faire d'un seul calcul les plans d'un meme moment" (decoche = plan par plan).
- Images d'exemple de la bibliotheque toute faite : 175 images (tenues, pieces, lieux, vehicules, avions, personnages types).


### 0.9.89 (bibliotheque toute faite)
- "Toute faite…" dans Ma bibliotheque de creations et sur les cartes de l'assistant : 188 descriptions pretes, avec leurs mots anglais pour les IA. Tenues completes ; pieces : hauts, bas, robes, vestes et manteaux, chaussures (baskets, mocassins, bottines, bottes, santiags, escarpins talons hauts, moyens ou petits, ballerines…), chapeaux (casquette, bonnet, borsalino, texan, panama…), accessoires, matieres (luxe, cachemire, cuir, daim, soie…) ; 33 lieux (piscine, bord de mer, monuments, maison, jardin…) ; vehicules (limousine, sportive, citadine, berline, SUV…) ; avions et autres transports (avion de ligne, jet, helicoptere…) ; personnages types inventes.
- Filtre Femme / Homme et recherche par mot ; image d'exemple quand elle existe. Une description prise devient la votre, modifiable ; vos creations s'ajoutent a cote.
- Tenue : "Composer…" piece par piece (haut, bas ou robe, veste, chaussures, chapeau, accessoire, matiere).


### 0.9.88 (atelier de creation : personnages, lieux, tenues)
- Ma bibliotheque de creations : chaque personnage, objet ou lieu se cree "Reel" (vos photos), "Inspire de photos" (ressemblance gardee, adapte par la description) ou "Invente" (description). Plusieurs photos par element ; "Image d'un rush…" prend une image a la ligne rouge dans n'importe quel rush, a encadrer. L'accord de la personne est demande pour "Reel" et "Inspire".
- Lieux : "Faire sa planche (Gemini)…" : quatre vues du meme lieu, meme lumiere ; elle sert de decor aux images clefs.
- Tenues : nouveau genre "Tenue" ; "Tenues toutes faites…" (bureau et ville, soiree, decontracte et sport, uniformes et metiers) ; image de la tenue par Gemini. Un personnage a sa tenue habituelle ; dans l'assistant, "Tenue dans cette scene" sur chaque carte de personne (la fiche est refaite avec la nouvelle tenue).
- Assistant : sur une carte, "Une photo a moi" › "Image d'un rush…" ; les images clefs disent pourquoi elles sont la.


### 0.9.87 (images clefs, relier deux rushes)
- Nouvelle facon de fabriquer : chaque plan part de la vraie fin de la video du plan d'avant (plus d'image de depart inventee) ; une image de fin n'est imposee qu'aux images clefs (nouveau lieu, quelqu'un qui attend ou arrive, la fin). Les gestes s'enchainent naturellement, les visages restent ceux des fiches.
- "Ce qui n'a pas ete filme entre ce plan et le suivant" : la video part de la derniere image du premier rush et arrive exactement sur la premiere image du suivant ; l'assistant voit l'avant et l'apres cote a cote et prevoit les images clefs entre les deux.
- Images clefs creees avec les fiches (personnes, objets, vehicules) et les photos reelles des lieux, ou prises dans un rush : "Image de la ligne rouge". Case "Image clef a la fin de ce plan" pour en ajouter ou en retirer.
- Jusqu'a quatre personnes ou objets suivis par plan (Kling O3).


### 0.9.86 (corrections de l'assistant de creation, image par image)
- Timeline : au-dessus des pistes, ◀| et |▶ avancent d'une image exactement, [ et ] choisissent les images (une seule image possible), "Supprimer N image(s)" les retire et recolle la suite. Maj + fleches : une image de plus ou de moins.
- Assistant : les images envoyees au moteur video sont agrandies si elles sont trop petites (fal refusait les decoupes : "image too small") ; la photo JPEG n'est plus annoncee PNG a Claude (erreur 400) ; si l'image est refusee, l'idee est relue sans elle.
- Les personnes decoupees sont detourees sur fond blanc ; la photo de groupe n'est plus envoyee comme reference d'une seule personne.
- Continuite : chaque plan dit qui on voit ("Qui", vide = personne) et ou sont les autres (au survol) ; nouvelle colonne "Cadrage" (plan large, serre, mouvement) ; "✨ Verifier la continuite". Les personnes montees en voiture ne reapparaissent plus ; l'image d'arrivee suit le cadrage.
- Revenir en arriere ne perd plus rien : "‹ Precedent" puis "Suivant" sans changement retrouve tout ; clic sur une etape du fil en haut ; seul ce qui a change est refait (et le plan qui en part).
- Une image corrigee est montree et entouree en orange ; l'assistant propose de refaire l'image suivante qui en part ; la consigne de correction parle du cadrage.
- "Images de controle" au choix : Gemini (fidele, payant), IA de ce poste (gratuite), aucune ; aussi dans Preferences › IA locale.
- Assistant visible et modifiable a chaque etape ; credits et "Recharger…" des IA utilisees (Claude, Gemini, fal.ai) ; explication de la phrase "dites-le en clair".
- "Regler moi-meme…" puis "‹ Retour a l'assistant" depuis la Sequence IA, avec les reglages faits.
- Exemples des champs neutres et varies (plus d'exemples personnels).


### 0.9.85 (catalogue des IA et mises a jour)
- Aide (ou Fabrique IA) › "Mises a jour des IA (locales et cloud)..." : onglet "Sur ce poste", les moteurs et modeles de l'IA locale qui ont une nouvelle version (ce qui change, pourquoi, taille) ; on coche, "Mettre a jour la selection". Le telechargement se fait en fond (fermer ou "Reduire" ne l'arrete pas), puis l'IA est essayee : si l'essai rate, l'ancienne version revient toute seule.
- L'ancienne version est gardee : "Revenir" la remet ; "Liberer la place" efface les anciennes versions. Un modele retire du catalogue est propose avec son remplacant (l'ancien reste installe).
- Chaque semaine, PhilCut regarde s'il y a du nouveau et le dit dans la barre du bas ("✦ IA : ... mise(s) a jour") ; rien ne s'installe sans vous. Preferences › IA locale : case "Chercher les mises a jour des IA" et bouton "Mises a jour des IA...".
- Onglet "Dans le cloud" : chaque service IA cloud (fond, suivi, levres, bruitages, voix, videos IA), a quoi il sert, son prix indicatif et son etat. Adresses et prix sont relus chaque jour dans le catalogue en ligne : un service retire est remplace par celui indique, et la barre du bas le dit. Le prix est toujours demande avant de payer.
- Cote projet : veille hebdomadaire des modeles (Hugging Face) avec essai reel avant publication, et des prix fal.ai.


### 0.9.84 (fond leve pour tout sujet, suivi precis par le cloud)
- Changer le fond d'un rush sans fond vert, quel que soit le sujet (personne, animal, objet, avion) : effet "Changer le fond (detourage)", Inspecteur › "Preparer par l'IA cloud (environ ... $)..." (Bria VRMBG 3.0 sur fal.ai, environ 0,05 $ la seconde, prix demande). La video rendue avec sa transparence est gardee sur ce poste : le meme passage n'est jamais repaye ; a l'export, elle sert de masque au plan (ses effets et son cadrage restent). Methode au choix : "IA de ce poste (personnes, gratuit)" ou "IA cloud, tout sujet".
- Suivi precis par le cloud (SAM 3 sur fal.ai, quelques centimes) : pour une zone (flou, cache), Inspecteur ou clic droit › "Suivre precisement (IA cloud)" ; pour une fleche, un texte ou un Goodie, "Accrocher..." › case "Suivi precis par l'IA cloud". Le sujet est suivi meme s'il se tourne, se cache un instant ou change de taille, en avant et en arriere.


### 0.9.83 (la bibliotheque partout)
- Sequence IA, onglet Personnages et lieux : bouton "Ma bibliotheque" (prendre un personnage, un objet ou un lieu garde, avec sa fiche ; ou garder la ligne choisie).
- Clip de groupe : "Depuis ma bibliotheque..." ajoute un musicien garde, avec son visage (il n'est pas redessine) ; "☆ Garder" range le musicien choisi.
- Fabrique musique : "A la maniere de..." › "Une voix de ma bibliotheque..." (voix decrite, ou timbre garde avec accord) ; "Choisir un morceau..." › "Un style de ma bibliotheque..." ; apres la creation, "☆ Garder dans ma bibliotheque" range le morceau, et aussi le style entendu et la voix decrite s'il y en a.


### 0.9.82 (intro et logo anime, de l'idee au resultat)
- Fabrique IA › Logo, intro et vignette › "Assistant de creation : une intro ou un logo anime..." (ou "Une intro ou un logo anime" dans l'assistant) : "une intro de 3 s style cinema avec mon logo et un impact" donne quatre cartes pre-remplies.
- Logo : un de vos logos (Atelier), une image a vous, dessine par l'IA (environ 0,04 $, confirme), de la bibliotheque, ou aucun. Style : un des modeles animes et sa couleur d'accent (ou choisi d'apres une description). Fond : degrade, couleur unie, images du film floutees, pose sur le film, une image (a vous, dessinee, de la bibliotheque). Son : un bruitage, un jingle cree sur ce poste, un son a vous, de la bibliotheque, ou aucun.
- Titre et sous-titre avec "✨ Ameliorer", duree, ou la poser (debut, fin, ligne rouge, medias) : l'apercu anime suit en direct.
- La fabrication mele le son a l'animation ; on regarde avec le son avant de poser. "☆ Garder ce style d'intro" range le modele, les couleurs et le fond dans la bibliotheque ; logo, fond et son se gardent aussi.
- "Regler moi-meme" ouvre la Fabrique habituelle avec le titre et le logo.


### 0.9.81 (ma bibliotheque de creations, lieux)
- Fabrique IA › "Ma bibliotheque de creations..." : personnages et musiciens (avec leur fiche), objets, lieux, voix (chanteur, chanteuse, narration ; voix decrite ou timbre garde avec accord), styles musicaux et visuels nommes, musiques, images. Chercher, renommer, retirer (corbeille, rien n'est efface), "Nouveau..." pour en creer : "Faire sa fiche", "Decrire d'apres un morceau", "Garder son timbre", "Ecouter un morceau".
- Rangee avec vos reglages : elle vous suit sur vos autres postes, et servira aux autres logiciels PhilFactory. On n'y range que sur clic : "☆ Garder" sur chaque carte de l'assistant, sur une fiche a l'etape des images, sur la musique creee.
- Chaque carte de l'assistant propose "Dans ma bibliotheque" : la fiche, la voix ou le style gardes sont repris tels quels (une fiche gardee n'est pas repayee).
- Assistant video : les lieux ont leur carte (le decor de l'image, une photo, decrit, ou de la bibliotheque) ; chaque plan sait dans quel lieu il se passe.


### 0.9.80 (de l'idee au resultat : video et musique)
- L'assistant de creation commence par une seule question, "Que voulez-vous faire ?" : vous l'ecrivez en quelques mots ; il devine s'il s'agit de la suite du plan, d'une scene, ou d'une musique ou chanson (modifiable d'un clic).
- Video : une carte par personne et par objet important, deduite et pre-remplie (une fiche par personne, jamais deux ; le chauffeur invente a la sienne). Sur la derniere image, l'IA propose le cadre de chaque personne ; un clic ou un trace le corrige, et c'est cette decoupe qui fait la fiche. Pour chaque carte : dans l'image, une photo a vous, ou invente d'apres la description ("Completer la description" par l'IA).
- Musique et chanson (Fabrique IA › Musique › "Assistant de creation") : "une ballade rock de 3 minutes, rapide avec au milieu un long passage lent, le style de mon groupe et sa voix plus feminine et chaude" donne trois cartes (style, voix, paroles) et un deroule. Style : un morceau a vous ou trouve en ligne, dont on s'inspire ou que l'on reorchestre (s'il est a vous, declare) ; voix : sa maniere de chanter decrite, ou son timbre garde (accord de la personne), avec ce qu'il faut changer ; paroles ecrites par vous ou par l'IA.
- La musique est creee partie par partie, chacune a son tempo, meme style, meme voix, meme tonalite, puis enchainee en fondu d'une mesure ; une partie se refait seule.
- Tout texte propose (idee, descriptions, plans, parties, paroles) a son bouton "✨ Ameliorer" : l'IA reformule sans changer le sens, les deux versions sont montrees, vous choisissez.
- "Regler moi-meme" ouvre ce qui est prepare dans la Sequence IA ou la Fabrique musique : rien n'est perdu.
- Budget : tant que rien n'est prevu, seul le depense s'affiche (plus de "depasse" rouge a tort apres la premiere lecture).


### 0.9.79 (assistant de creation : le mode assiste)
- Nouveau : Fabrique IA › Video › "Assistant de creation : guide pas a pas..." et, au clic droit sur un plan, "Continuer ce plan avec l'assistant IA...". Vous racontez la suite d'un trait ; l'assistant (Claude par defaut, Gemini ou l'IA de cet ordinateur, au choix) regarde la derniere image, propose les personnes, les objets importants et les plans d'une seule action ; vous corrigez dans les tableaux ou en clair ("le chauffeur plus age", "un plan de plus ou elles saluent").
- Il prepare ensuite les fiches et les images de depart et d'arrivee, vous les montre AVANT la video ("Corriger..." refait une image d'apres ce que vous ecrivez), fabrique les plans a la chaine puis relit chacun : ✓ ou ⚠ avec la raison (visages, action). Un plan rate est signale et propose a refaire : c'est vous qui decidez.
- Budget toujours affiche en bas : prevu et depense ; le depense passe en rouge avec "depasse" s'il franchit le prevu. Rien de payant ne part sans confirmation.
- "Le regler moi-meme..." ouvre la meme histoire dans la Sequence IA (mode manuel) ; "Prolonger ce plan" propose le mode assiste.
- Fiche d'un objet important (vehicule...) pour le garder identique d'un plan a l'autre ; "Style" = une allure "a la maniere de" (jamais un visage copie).
- A venir sur le meme modele : intro et logo, puis musique, voix et chanson.


### 0.9.78
- Fichier : "Exporter la video vers un emplacement (cloud, NAS)..." et "Envoyer une video deja exportee vers un emplacement..." ; dans la fenetre d'export, la case "Puis l'envoyer vers un emplacement (NAS, Google Drive, pCloud, OneDrive...)".
- Fondus donnes d'office aux musiques et sons : reglables dans Preferences › Export (0 = aucun).
- La disposition (largeur des medias, de l'apercu, du volet de droite, hauteur de la timeline) est remise a l'ouverture une fois PhilCut a sa vraie taille (avant, Qt la redistribuait).
- Tampons maison : ceux qui sont prets portent ✓ et se posent directement depuis leur onglet (double-clic ou "Mettre dans le film...") ; plus besoin d'aller les chercher dans "Ma bibliotheque".
- Bruitages (fenetre et listes des tampons IA) et modeles de tampons IA : par ordre alphabetique.
- Telecharger un son ou un extrait en ligne : quand FFmpeg echoue pendant le decoupage fait par yt-dlp (journal du 17/11 : "ffmpeg exited with code 3436169992"), le fichier est telecharge tel quel puis PhilCut coupe et convertit lui-meme.


### 0.9.77 (visages gardes sur toute l'histoire)
- Sequence IA : un plan enchaine demarre sur l'image d'arrivee validee du plan precedent (propre, visages d'apres la fiche) et non plus sur la derniere image de sa video, ou les visages avaient deja derive : la derive ne s'accumule plus de plan en plan.
- Image d'arrivee : les fiches des personnages passent en premier ; un visage qui a derive dans l'image de depart est corrige d'apres la fiche.
- Fiche personnage d'apres une photo de groupe : Gemini ne dessine que la personne decrite (ex. : "a gauche, cheveux longs bruns, manteau noir"). Un personnage nomme comme un groupe ("Les deux") est signale : une fiche = une personne.
- Personnage invente sans photo (le chauffeur) : sa fiche est dessinee d'apres sa description et le garde identique d'un plan a l'autre.
- Un plan dont le champ "Personnages" est vide recoit maintenant TOUS les personnages de l'histoire (avant : aucun, et le moteur inventait les visages).
- "pour que", "afin que", "pendant que" sont reconnus comme deux actions dans un plan (avertissement et "Couper en deux plans").
- Journal : le clic dans le guide qui provoquait une erreur ("CaseGuide already deleted") est corrige.


### 0.9.76 (prolonger un rush par l'IA, en une fois)
- "Prolonger ce plan" › "Prolonge par l'IA cloud, fidele" : une PHOTO etait prolongee en image fixe (zoom lent) au lieu d'etre animee : corrige, la photo est le point de depart de la video.
- Toute la suite se decrit d'un coup ("elles descendent les marches, puis vont vers la limousine, puis le chauffeur les aide a monter, puis la limousine demarre") : PhilCut en fait des etapes d'une seule action (une indication de camera reste avec son action), les montre avec leur duree et le prix total, puis les fabrique a la chaine, chaque etape partant de la derniere image de la precedente, et montre le tout avant de le poser. Duree jusqu'a 60 s.
- La confirmation dit ce qui part : la derniere image du plan (point de depart) et deux images de repere (debut et milieu) pour que le moteur connaisse les personnes ; pour une photo, la photo seule.
- "Recharger..." ouvre directement la page des credits de fal.ai.
- Bulles d'aide longues : elles passent a la ligne au lieu d'etre coupees par le bord de l'ecran. Prix de la Sequence IA avec une virgule.


### 0.9.75 (transformer une voix, guides)
- "Transformer la voix..." (Inspecteur, groupe Voix et son ; bouton Voix et son de la barre) : sur ce poste, gratuit, hauteur et timbre (formants) reglables, prereglages "Plus masculine", "Plus feminine", "Voix d'enfant", "Narrateur pose", "Grosse voix", "Petite voix" ; on ecoute avant d'appliquer, la transformation se rend a l'export et se retire. Par l'IA cloud (fal.ai, 0,30 $ la minute, prix demande) : la voix du plan est redite par une voix toute faite (femme ou homme) avec les memes intonations, bruit de fond retire au choix ; ecoutee avant d'etre posee sur la piste Voix (son d'origine coupe, un Annuler). Seulement sa voix ou celle d'une personne d'accord (case obligatoire).
- Guides : "Transformer une voix", "Une fleche, un texte ou un goodie qui suit une personne ou un objet" (c'etait deja possible : clic droit sur l'element, "Accrocher a une personne"), "Changer le fond" corrige (l'effet "Changer le fond (detourage)" detoure deja sur ce poste un rush filme n'importe ou).


### 0.9.74 (son des tampons IA par le cloud)
- Tampons IA : nouveau choix "Son" : sur ce poste (gratuit) ou "IA cloud : voix Gemini, bruitages d'apres la video (fal.ai)". Les bruitages sont fabriques d'apres la video du tampon (environ 0,001 $ la seconde), la phrase est dite par la voix Gemini dans le style choisi (grosse voix, petite voix, robot, radio...). Prix demande, credit fal.ai affiche.
- Nouveau champ "Son decrit" ("roulement de tambour, quelques cymbales"). La phrase d'image ne fait aucun son : ce qui y decrit le son ("en son...", "on entend...", "and the sound of...") en est retire et passe a "Son decrit".

### 0.9.73 (images vues avant la video, voix)
- Sequence IA, moteur Reference : avant toute video, la fenetre "Images des plans" montre pour chaque plan l'image de depart et l'image d'arrivee composees par Gemini (quelques centimes chacune). On garde, on refait avec une precision ("assise, l'ordinateur ouvert"), on met sa propre image ou l'image du film a la ligne rouge, ou on laisse le plan finir librement. Seuls les plans valides partent en video ("Fabriquer" renvoie vers cette fenetre sinon).
- Retouches de voix : "Ecouter avec ces retouches" marche (le son n'etait jamais joue) et part de la ligne rouge ; choisir une retouche depuis "Voix et son" la fait entendre aussitot ; un seul traitement complet a la fois (studio, narration...) : en cocher un remplace l'autre, grave et aigu s'excluent ; "Appliquer a..." recopie les retouches sur les plans selectionnes, la piste ou le meme rush.
- Continuer avec ma voix : un mot qui fait se perdre le modele ("video" avec accent) n'arrete plus la fabrication : la phrase est refaite sans accents ; sinon, le message dit quelle phrase coince.
- Guides : "Retoucher une voix et l'entendre", "Creer un tampon IA avec un vrai son".

## Nouveautes de 0.9.72

### 0.9.72 (personnage fidele d'un plan a l'autre, plans plus longs, rallonger un rush)
- Nouveau moteur "Kling O3 Reference : personnage fidele (fal)" : il recoit le personnage comme "element" (sa fiche et ses images) et le garde identique ; image de depart ET image d'arrivee ; jusqu'a 15 s par plan ; 0,084 $/s sans son.
- Sequence IA, onglet des personnages : "Fiche personnage..." compose avec Gemini une planche du personnage (face, trois quarts, profil, en pied) d'apres ses images ; on la regarde avant de la garder. Faite d'office avant le premier plan si elle manque (case "Image d'arrivee et fiche personnage").
- Image d'arrivee : la pose a la fin du plan est composee d'apres l'image de depart ; le moteur doit la rejoindre, il ne peut plus faire traverser la table ni changer de visage en route.
- "Enchainer" (coche d'office) : chaque plan demarre sur la derniere image exacte du plan precedent, raccord parfait. Un plan rate en cours de fabrication n'efface plus les plans deja payes.
- "Prolonger ce plan" : nouvelle maniere "Prolonge par l'IA cloud, fidele" (Kling O3 Reference) : la suite part de la derniere image du rush, avec ses personnes et objets en reference, jusqu'a 15 s, "Suite" a decrire dans votre langue ; prix demande avant.
- Credit restant : Sequence IA, Prolonger et Faire parler montrent le credit fal.ai restant et un bouton "Recharger..." (Google ne donne pas le solde d'une clef Gemini : le bouton ouvre le suivi des depenses).
- Fenetres de travail : toutes recoivent "Reduire" pendant un calcul (Tampons video compris) ; la vignette composee ne bloque plus PhilCut.
- Tampons, "Ma bibliotheque" : glisser une icone la met a la place de celle survolee ; elle ne part plus hors de vue.
- Faire parler : la case du visage et le cout restent visibles pres des boutons, et le message dit pourquoi "Faire parler" est grise.
- Guide "Comment faire" : "Garder le meme personnage d'un plan a l'autre", "Rallonger un rush ou creer sa suite", "Voir le credit restant et le recharger".

## Nouveautes de 0.9.71

### 0.9.71 (journal des plantages sans fausses alertes)
- "Installer et redemarrer" pendant une synchronisation ne laisse plus une fausse "access violation" dans le journal : la sortie voulue coupe d'abord la surveillance.
- La fenetre de fichiers de Windows ne laisse plus de fausse "Windows fatal exception 0x80040155" (erreur interne de Windows qu'il rattrape lui-meme).
- Google Drive lent ou injoignable n'est plus annonce comme "autorisation expiree, autorisez a nouveau" : "ne repond pas pour le moment, la synchronisation reessaiera seule".
- Feuille de test : les fiches validees par Philippe sont rangees dans "guideline-tests-validees.md".

## Nouveautes de 0.9.70


### 0.9.70 (Sequence IA : gestes coherents, personnage fidele a son image)
- Une action par plan : les moteurs video ne reussissent bien qu'une action simple ; deux actions enchainees ("contourne le bureau et s'assoit") donnent des gestes incoherents (traverser la table). PhilCut les repere (signe ⚠ dans la liste, avertissement sous "Ce qu'on voit" et avant de fabriquer), "Couper en deux plans" ou "Une action par plan" pour tous.
- Le decoupage par l'IA ne fait plus qu'une action simple par plan (4 a 6 s) ; la consigne envoyee au moteur demande une seule action lente et physiquement possible (on contourne les meubles, on ne traverse rien) ; les consignes ecrites par PhilCut avant cette version sont refaites a la fabrication.
- Personnage fidele : sans image de depart, le moteur reinventait le personnage d'apres sa description. Desormais, si le personnage (ou le lieu) a des images, l'image de depart est composee d'office avec elles par Gemini (0,04 $ par plan, compte dans le prix ; case "Image de depart par Gemini").

## Nouveautes de 0.9.69


### 0.9.69 (la voix : un seul reglage)
- Sequence IA, "Repliques" decide tout : "Aucune voix : personne ne parle" ; voix de ce poste ou voix Gemini posees ensuite par PhilCut ; ou nouveau "Voix du moteur video" : le moteur (Kling, Seedance, Gemini) fait parler les personnages avec la video, levres naturelles, d'apres les repliques ecrites.
- Avec "Voix du moteur", le son fabrique est demande et garde au montage ; sinon il n'est pas fabrique (Kling, Seedance) ou coupe au montage (Gemini). Le prix suit le reglage (Kling : 0,112 $/s sans son, 0,168 $/s avec).

## Nouveautes de 0.9.68


### 0.9.68 (fenetres qui ne bloquent plus, certificats, histoire sans voix)
- La Sequence IA ne bloque plus PhilCut : on continue a monter pendant la fabrication ; "Reduire (suivi dans la barre du bas)" pendant un calcul ; le menu la rouvre. Meme chose pour la presentation de photos, les modeles de montage, prolonger un plan, les tampons video, l'atelier de logo et la publication : fermer pendant un calcul range la fenetre, le calcul continue et la barre du bas le suit (l'atelier de logo ne fige plus PhilCut 30 s, la publication n'est plus arretee).
- Erreur "CERTIFICATE_VERIFY_FAILED" (fal.ai sous Windows) : toutes les connexions sont verifiees par Windows lui-meme, comme le navigateur (le correctif n'etait branche que pour la mise a jour).
- Sequence IA : "Repliques > Aucune voix : personne ne parle" ; la consigne demande des bouches fermees et le son invente par le moteur (Gemini) est coupe au montage.
- Kling 3.0 et Seedance (fal.ai) ne fabriquent plus de son ni de voix : PhilCut pose le sien. Kling passe de 0,14 a 0,112 $ la seconde.

## Nouveautes de 0.9.67


### 0.9.67 (video de narration d'apres ce qui est dit)
- Clic droit sur la voix > "Illustrer ce qui est dit (video de narration)..." (ou Fabrique IA > Video > "Video de narration d'apres ce qui est dit...").
- "Ecouter et decouper" : la voix est transcrite sur ce poste au mot pres, puis decoupee en idees de 2 a 8 secondes (fin de phrase, silences, virgules), sans trou.
- Une image animee proposee par idee, modifiable ; "Idees d'images avec l'IA" (Claude, Gemini ou ce poste) propose des plans concrets et varies, sans texte a l'ecran.
- Rendu : cinema realiste, documentaire, dessin anime, aquarelle animee, animation 3D ; paysage ou vertical.
- Presentateur facultatif : il apparait au debut, a la fin et de temps en temps, et dit exactement son passage de voix (levres calees, OmniHuman) ; son image : un fichier, ou creee par Gemini d'apres une description ; case du visage obligatoire.
- Fabrication par le cloud, prix total detaille et demande avant ; fermer la fenetre n'arrete rien ; un plan rate n'arrete pas les autres. Apercu de chaque plan, puis "Poser sous les mots" : chaque plan exactement sous les mots qu'il illustre, au-dessus du film, muet ; un seul Annuler. La narration est gardee avec la voix et se rouvre.
- Tableaux du clip et de la narration : les textes longs passent a la ligne (plus de texte coupe).
- Nouveau guide : "Illustrer ce qui est dit : video de narration".

## Nouveautes de 0.9.66


### 0.9.66 (clip de groupe deduit de la chanson)
- Clic droit sur une chanson > "Creer le clip du groupe d'apres ce morceau..." (ou Fabrique IA > Video > "Clip de groupe d'apres une chanson...").
- PhilCut ecoute le morceau sur ce poste : tempo, mesures, parties (intro, couplets, montee, refrains, solo, fin, en couleurs), voix separee pour savoir quand on chante.
- Il invente le groupe d'apres le son (ou d'apres le style de la Fabrique musique) : chanteur ou chanteuse, guitare, basse, batterie, claviers, machines, cordes, cuivres ; descriptions modifiables.
- Lieu : concert sur scene ou clip tourne ailleurs (lieu propose d'apres l'ambiance) ; dessin anime ou realiste ; paysage ou vertical.
- Decoupage plan par plan cale sur les mesures (plans longs au calme, courts au refrain), modifiable ; "Idees avec l'IA" d'apres l'ambiance et les paroles. Un refrain qui revient reprend les plans du premier : bien moins cher.
- Fabrication par le cloud (Gemini, fal.ai) : memes visages dans tous les plans (portraits puis images de depart), levres du chanteur calees sur la voix separee ; prix total detaille et demande avant ; fermer la fenetre n'arrete rien ; un plan rate n'arrete pas les autres.
- Apercu de chaque plan, puis "Poser le clip sous la chanson" : chaque coupe sur une mesure, plans muets, un seul Annuler. Le clip est garde avec le morceau et se rouvre.
- Fabrique musique : nouvelle ligne "Clip video" (concert, ailleurs, dessin anime) : la fenetre du clip s'ouvre des que le morceau est pose.
- Nouveau guide : "Creer le clip d'un groupe d'apres une chanson".

## Nouveautes de 0.9.65


### 0.9.65 (faire parler un personnage sur votre son)
- Le son d'abord : posez la voix (ou la chanson) sur la timeline, puis les levres sont fabriquees dessus.
- Clic droit sur un plan video > "Faire parler ce plan sur le son dessous..." : seule la bouche est refaite pour dire le son qui passe sous le plan (voix et musiques a leur place). LatentSync (0,20 $ jusqu'a 40 s) ou Sync lipsync-2 (3 $ la minute, le plus precis), par fal.ai.
- Fabrique IA > Video > "Personnage qui parle (une image et votre son)..." : une image du personnage devient une video qui dit votre son (levres, tete, regard). OmniHuman 1.5 (0,16 $ la seconde), attitude et gestes ecrits dans votre langue.
- "Isoler d'abord la voix" : pour une chanson ou une musique derriere, les levres suivent la voix seule.
- Cout annonce et demande avant ; apercu avant de poser ; le plan pose est muet (le son reste celui de la timeline) ; un seul Annuler. Case obligatoire : personnage invente, votre visage, ou une personne d'accord, jamais une personnalite.
- Fermer la fenetre ne perd rien : la barre du bas suit le calcul.
- Nouveau guide : "Faire parler un personnage sur ma voix".

## Nouveautes de 0.9.64


### 0.9.64 (fermer une fenetre ne perd plus une creation)
- Fermer la Fabrique musique (ou le plan de liaison, Continuer avec ma voix, Separer voix et musique, la Sequence IA) pendant un calcul : la fenetre se range, le calcul continue. La barre du bas le suit avec "Afficher la fenetre" ; a la fin, "Voir le resultat" rouvre la fenetre avec le resultat a ecouter ou regarder et a poser.
- Le Centre d'activite (barre du bas, clic) garde ces boutons : on retrouve le resultat meme plus tard.
- La Fabrique musique ne bloque plus PhilCut : on continue a monter pendant la creation ; Fabrique IA > Musique rouvre la meme fenetre tant qu'une creation est en route ou pas encore vue.
- Atelier IA (effets video et image) : "Voir le resultat" a la fin, comme les autres.

## Nouveautes de 0.9.63


### 0.9.63 (Fabrique musique : a la maniere de, voix, passage)
- "A la maniere de" : la liste passe de 74 a plus de 250 references (rock, metal, pop, chanson, rap, electro, jazz, musiques de film et compositeurs d'aujourd'hui, classique, musiques du monde). Elle vient aussi du catalogue en ligne : elle s'enrichit et suit la mode sans nouvelle version.
- Fenetre "a la maniere de" : filtre par famille, recherche tolerante ("metallic" trouve Metallica et tout le metal ; une faute de frappe passe), liste alphabetique. Un nom absent : "Utiliser", l'IA le decrira sur votre clic.
- Ligne Voix, bouton "A la maniere de..." : chanter a la maniere d'un chanteur ou d'un groupe ; ou "Decrire la voix d'un morceau" (de ce poste ou en ligne) : on choisit le passage ou la voix chante, PhilCut l'isole de la musique, mesure registre, etendue, vibrato, timbre, et l'ecrit dans la consigne. La voix n'est jamais copiee.
- S'inspirer d'un morceau : on choisit le passage (tout le morceau, un refrain, une intro) ; seul ce passage est analyse, et reorchestre si le morceau est libre.
- Musique en ligne : "Plus de resultats" (30 de plus a chaque clic, jusqu'a 300). "S'inspirer de ce morceau" (et "Poser dans le film") sont actifs des qu'un morceau est choisi : le clic telecharge puis continue tout seul.
- Le bouton "Style a la maniere de" de la ligne Phrase decrit maintenant l'orchestre ET la voix ; celui de la ligne Voix, la voix seule.
- Nouveau guide : "Creer une musique a la maniere de...".

## Nouveautes de 0.9.62


### 0.9.62 (dossiers des clouds)
- Dossier des projets (ou des rushes) pas encore cree sur le cloud : la fenetre "Choisir un dossier" s'ouvre dans le dossier parent et le dit, avec "Le creer maintenant".
- En validant les Preferences, si le role des comptes a change, PhilCut cree le dossier des projets et celui des rushes sur leurs comptes (resultat dans la barre du bas).
- Correction importante : envoyer un projet sur pCloud aurait cree un dossier portant le nom du fichier ; "Nouveau dossier" sur kDrive creait un dossier "_" en trop.
- Les fenetres Ouvrir / Enregistrer / Choisir un dossier d'un emplacement s'ouvrent centrees sur PhilCut et ne depassent plus de l'ecran.
- Mots de passe et clefs entre vos postes (Preferences > Comptes et synchro), comme PhilPDF : sous la case "Synchroniser aussi les mots de passe et clefs", l'etat (phrase gardee sur ce poste, indice, ce qui est partage, dernier envoi), les boutons "Phrase secrete..." et "Changer la phrase ou l'indice...", et l'explication. Cocher la case demande la phrase tout de suite. L'onglet Assistant et IA dit ou cela se regle.

## Nouveautes de 0.9.61

### 0.9.61 (consignes en anglais : on ecrit dans sa langue, on voit les deux)
- Partout ou une consigne doit partir en anglais (plan de liaison, sequence de personnages, tampons IA, musique IA) : une case "Dans votre langue", traduite en direct dans une case "En anglais, envoye au moteur". La traduction reste modifiable pour l'ameliorer ; corrigee a la main, c'est elle qui part.
- Une consigne redigee en anglais par l'IA (ou par "Rediger la consigne", ou une proposition du plan de liaison) est traduite dans votre langue pour que vous la lisiez.
- Fabrique : sous la phrase, l'anglais qui partira au moteur s'affiche en direct (avec la description du style "a la maniere de") ; corrige a la main, c'est lui qui part.
- Mots sans traduction : signales, a ecrire en anglais ; PhilCut en anglais : une seule case.

## Nouveautes de 0.9.60

### 0.9.60 (police du titre des vignettes)
- Vignette : nouvelle liste "Police du titre" dans le groupe Style. Par defaut "Celle du kit" (Anton pour Punchy, Bebas Neue pour Documentaire et Aviation, Poppins pour Editorial et Tech) ; sinon les polices livrees avec PhilCut, puis celles de l'ordinateur, chaque nom ecrit dans sa propre police. Le reste du style (contour, ombre, couleurs) ne change pas ; le choix reste modifiable en rouvrant la vignette.

## Nouveautes de 0.9.59

### 0.9.59 (correction)
- Le modele "Continuer avec ma voix" n'apparaissait pas dans Preferences > IA locale : PhilCut ne relisait le catalogue des modeles qu'une fois par jour. Il le relit maintenant aussitot apres une mise a jour de PhilCut, et quand une fonction demande un modele qu'il ne connait pas encore.
- Le bouton "Installer le modele..." des fenetres "Continuer avec ma voix" et "Separer voix, musique et bruits" lance directement le telechargement (progression dans la barre du bas) ; la fenetre se met a jour toute seule a la fin.

## Nouveautes de 0.9.58

### 0.9.58 (projets et rushes dans vos clouds, comme PhilPDF)
- Chaque compte a son role (Preferences > Comptes et synchro > "Role de chaque compte") : un pour les reglages et la session, un pour deposer et retrouver les projets (par exemple pCloud), un pour les rushes (gros fichiers). Le role de chaque compte est ecrit a cote de son nom dans la liste.
- Fichier > "Ouvrir un projet depuis un emplacement (cloud, NAS)..." (Ctrl+Maj+O) et "Enregistrer le projet vers un emplacement (cloud, NAS)..." : le compte des projets est propose d'abord, dans son dossier. Un projet ouvert depuis un compte y retourne a chaque Enregistrer (un nuage devant son nom). Si un autre poste l'a modifie entre-temps, PhilCut demande : remplacer, ou garder les deux.
- Projets recents du cloud sur l'Accueil et dans Fichier > Projets recents ; sur un autre poste avec le meme compte, double-clic : le projet est repris du cloud.
- Rushes : apres l'enregistrement, on peut aussi deposer les originaux sur le compte des rushes (jamais coche d'office). Sur un autre poste, "Medias introuvables sur ce poste" propose, rush par rush, "Telecharger la copie legere" ou "Telecharger l'original". Le compte des rushes n'est plus recu d'office : rien de lourd n'arrive sans clic.
- Fichier > "Importer des rushes depuis un emplacement (cloud, NAS)..." (plusieurs a la fois) et Outils > "Envoyer une video exportee vers un emplacement..." (aussi propose apres l'export).
- "Nouveau dossier" dans les fenetres Ouvrir / Enregistrer vers un emplacement.
- Guide "Retrouver mes projets et mes rushes sur un autre PC (cloud)".

## Nouveautes de 0.9.57

### 0.9.57 (continuer avec ma voix)
- Continuer avec ma voix : PhilCut fait dire une nouvelle phrase avec la voix d'un extrait de 5 a 15 secondes du film, pour continuer un commentaire ("Et maintenant, passons a autre chose...") sans tout reenregistrer. Clic droit sur le plan qui porte la voix > "Continuer avec cette voix...", Montage > Son, Fabrique IA > Musique, ou le bouton "Une phrase avec ma voix sur ce plan..." apres la pose d'un plan de liaison.
- L'extrait propose : les dernieres secondes de voix avant la ligne rouge (ou un fichier : un enregistrement de votre voix). "Isoler d'abord la voix" retire la musique derriere (si "Separer voix, musique et bruits" est installe).
- Uniquement votre voix ou celle d'une personne qui vous a donne son accord : case a cocher obligatoire qui engage l'auteur, jamais la voix d'une personne connue.
- Tout se fait sur ce poste, gratuitement : modele Chatterbox multilingue de Resemble AI (licence MIT, 17 langues proposees dont le francais, environ 1,6 Go a installer une fois dans Preferences > IA locale). Environ 4 secondes de calcul par seconde de voix sur un processeur ordinaire.
- La voix est posee sur la piste Voix, au meme niveau sonore que l'extrait ; le fichier porte la mention "voix fabriquee par IA". Un seul Annuler.
- Guide "Continuer un commentaire avec la meme voix" : faisable, avec "Montrez-moi".

## Nouveautes de 0.9.56

### 0.9.56 (plan de liaison intelligent)
- Plan de liaison : un plan qui part de la derniere image d'un rush et arrive a la premiere image du suivant, pour passer d'un lieu a l'autre sans coupe seche. Clic droit sur le premier plan > "Plan de liaison avec le plan suivant...", clic droit dans un vide > "Remplir ce vide par un plan de liaison...", Montage > Pistes et passage choisi, ou Fabrique IA > Video.
- La fenetre montre les deux images du raccord, mesure la lumiere, les couleurs et le mouvement de la camera, et propose des passages (mouvement continu, passage par la lumiere ou l'ombre, envolee, fondu des formes). "Analyser avec l'IA de ce poste" (gratuit) ou "avec l'IA cloud" (cout affiche avant) : l'IA regarde les deux images et propose trois passages. La consigne reste modifiable.
- Trois facons de fabriquer : transition 3D (gratuite, immediate) ; IA video de ce poste (part de l'image A, rejoint l'image B par un fondu) ; Gemini Omni (votre clef, prix maximal affiche et demande avant : part exactement de l'image A et arrive exactement sur l'image B). Pour une IA, case d'accord des personnes visibles obligatoire.
- On regarde le plan, on garde le morceau voulu, puis "Poser entre les deux plans" : il remplit le vide s'il y en a un, sinon la suite du film (plans, marqueurs, titres) se decale d'autant. Un seul Annuler revient en arriere.
- Guide "Lier deux rushes par un plan de passage" : faisable, avec "Montrez-moi".
- Garde-fou de plus : un contenu plus large que sa zone qui defile (coupe a droite sans prevenir) est detecte. Deux cas corriges : le volet Proposition et la colonne de la fenetre Vignette.

## Nouveautes de 0.9.55

### 0.9.55 (garde-fous, guides en ligne)
- Garde-fous automatiques : chaque regle de conception, et chaque incident passe, est verifie a chaque version (listes alphabetiques, rien de tronque, fenetres qui tiennent dans un ecran de 1024 x 768, reglages dans les Preferences, progression des taches, dossiers du systeme, aucun secret dans le code, jamais une erreur vide, aucune tache detruite en plein travail, guides qui ne citent que des menus existants, IA essayees en vrai, tout se defait d'un seul Annuler).
- 53 messages d'erreur qui pouvaient s'afficher vides disent maintenant au moins la nature de l'erreur. Trois autres taches de fond sont protegees contre le plantage de "Dites-le".
- La barre de lecture sous l'apercu passe a la ligne : PhilCut s'utilise des 1024 pixels de large (il en fallait 1113). La fenetre Vignette tient aussi.
- Guides "Comment faire..." : ils arrivent aussi par le catalogue en ligne, comme les Goodies (marques "Nouveau"). Premier guide livre ainsi : "Echanger ses rushes entre ses postes par pCloud".
- Sequence IA : sous le choix du moteur, ce que chacun garde du personnage (IA de ce poste : visage qui derive, levres immobiles ; Gemini : meme visage d'un plan a l'autre).

### 0.9.54 (pCloud direct)
- pCloud : connexion directe par l'application PhilFactory acceptee par pCloud (autorisation dans le navigateur, sans donner de mot de passe). Le WebDAV reste possible.

### 0.9.53 (separer voix, musique et bruits)
- Clic droit sur un plan (video ou son) > "Separer voix, musique et bruits..." ; aussi Fabrique IA > Musique pour un fichier. Trois choix tout faits : "Retirer la voix", "Garder la voix seule", "Les trois pistes". Calcul sur ce poste (gratuit, rien n'est envoye), avec sa progression ; on ecoute chaque piste ; "Poser dans le film" les pose sous le plan, a la place exacte, et coupe le son d'origine. Un seul Annuler revient en arriere.
- Les trois pistes ensemble redonnent exactement le son d'origine (rien ne se perd). Modele HT-Demucs (Meta, licence MIT, environ 170 Mo) a installer une fois : Preferences > IA locale. Verifie sur une vraie voix et une musique : voix retrouvee a 99 %, plus rapide que le temps reel sur un processeur ordinaire.
- La voix seule de la Fabrique musique utilise ce modele quand il est installe (meilleure et plus rapide).
- Guide "Retirer la voix d'une musique" : faisable, avec "Montrez-moi".

### 0.9.52 (guides pas a pas)
- Aide > "Comment faire... (guides pas a pas)" : des cas concrets (changer le fond, couper, faire parler des personnages, lier deux rushes, retirer la voix, suivre une personne, passer d'un rush a l'autre...), par ordre alphabetique, avec recherche. Chaque guide dit ce qui est faisable aujourd'hui, en partie, ou pas encore.
- Chaque etape a un bouton "Montrez-moi" : PhilCut ouvre lui-meme le bon menu en surlignant la bonne ligne, le menu du clic droit sur le plan, ou l'onglet du volet avec la bonne recherche. L'etape se coche toute seule quand c'est fait. La fenetre reste a cote du film, sans bloquer.
- Aussi depuis le bouton IA ("Comment faire..."), et en ecrivant une question dans Dites-le en clair ("comment retirer la voix ?").
- Sequence IA : avant de donner les images d'un personnage, l'auteur certifie l'accord de la personne (case a cocher qui l'engage).

### 0.9.51 (corrections apres les essais du 12/11 au soir)
- Plantage corrige : dans "Dites-le en clair" avec l'IA locale, cliquer sur une autre action pendant que l'IA reflechissait encore faisait fermer PhilCut d'un coup (Windows : Qt6Core.dll, code 0xc0000409). Une tache relancee avant la fin de la precedente ne peut plus faire planter PhilCut, partout dans le logiciel. Dans Dites-le, les boutons d'actions attendent la reponse, et seule la derniere demande compte.
- Timeline : le clic droit sur un endroit vide ne faisait rien (erreur). Il ouvre de nouveau son menu, et sur un vide entre deux plans propose "Refermer ce vide : recoller les plans" (annulable).
- Atelier IA non bloquant : on continue a travailler dans le film pendant le calcul. Le fermer pendant un calcul le range seulement ; "Afficher l'Atelier" dans la barre du bas le rouvre.
- Une erreur sans texte dit au moins sa nature, et son detail va au journal des plantages et erreurs.
- Tri des rushes : tremble mesure comme un stabilisateur (points suivis), la marche qui secoue est reperee ; le message nomme le rush et la raison ; le plan dans la timeline affiche aussi "⚠" et le probleme ; au survol de la vignette, une ligne "Mesures" donne les chiffres. La barre de progression vide ne reste plus affichee a cote des messages.

### 0.9.50 (plusieurs chaines YouTube, effets sur une image d'exemple)
- Publier : plusieurs chaines YouTube reliees. Liste "Chaine", bouton "Ajouter une chaine..." (le navigateur demande quel compte ou quelle chaine de marque), "Delier" ne delie que la chaine choisie. La confirmation rappelle la chaine qui recoit la video. Une chaine deja reliee est reprise telle quelle.
- Journal des plantages : Outils > Journal des plantages et erreurs. PhilCut y note les erreurs (avec le detail technique) et, en cas de plantage brutal, l'endroit ou il s'est arrete. Rien n'est envoye : c'est a copier pour me le transmettre. La fenetre de recuperation apres plantage propose de l'ouvrir.
- Volet Effets : sans plan video dans la timeline, les vignettes montrent chaque effet sur un paysage d'exemple dessine par PhilCut (fabrique une fois sur ce poste). Des qu'un plan est pose, elles le montrent sur vos images.

### 0.9.49 (tri des rushes)
- Tri des rushes, calcule sur ce poste (sans IA, rien n'est envoye ni retire) : pastilles sur les vignettes des medias. D = doublon (meme fichier, ou memes images et meme duree), F = flou, T = tremble (un panoramique regulier n'est pas signale), S = son rate (sature, tres faible, vent probable), ... = silences (le tiers du rush, ou un blanc de plus de 5 s). Detail au survol ; "a revoir", "flou", "doublon"... dans la recherche des medias.
- Propose a la fin de chaque import (Preferences > Import > Tri des rushes : proposer, toujours, jamais), clic droit sur les medias > Trier, bouton IA > "Trier les rushes", ou "trie les rushes" dans Dites-le en clair.
- La barre du bas ne cache plus un message tout juste affiche (un seul minuteur).

### 0.9.48 (bouton IA, marqueurs)
- Bouton "IA" toujours visible a droite de la barre d'outils : il ouvre "Dites-le en clair", avec des actions d'un clic (par ordre alphabetique). Le plan est toujours montre, case par case, avant d'agir ; tout se defait d'un coup.
- Nouvelles actions : etalonnage de toute la sequence (auto, "memes couleurs partout comme le plan 2", "un peu plus chaude / lumineuse / contrastee"), ranger les rushes de la bibliotheque (date de prise de vue, nom, type, duree), poser des marqueurs (a chaque plan, sur les temps forts de la musique, a un instant, avec un nom).
- Marqueurs : touche M (Montage > Pistes et passage choisi > Poser un marqueur a la ligne rouge) ; fanion sur la regle, clic pour y revenir, clic droit pour le nommer ou le supprimer.

### 0.9.47 (Audionautix)
- Musique en ligne : nouvelle source "Audionautix : musiques libres de Jason Shaw". Licence Creative Commons BY 4.0 donnee par l'auteur : utilisable meme dans une video monetisee, a condition de citer "Music by audionautix.com". PhilCut lit le catalogue du site (garde une semaine), cherche par titre ou genre (jazz, piano, calm...), telecharge sans yt-dlp, garde le credit avec le fichier et l'ajoute a la description quand vous publiez. Les sources sont classees par ordre alphabetique.

### 0.9.46 (menus ranges, IA partagees entre logiciels PhilFactory)
- Menu Montage en cinq sous-menus : Image du plan, Montage automatique, Pistes et passage choisi (partie jaune), Son, Textes et habillage ; tout par ordre alphabetique ; "Monter par le texte" devient "Couper en supprimant des phrases (texte de ce qui est dit)" ; la partie jaune est expliquee.
- Menu "Fabrique IA" : le seul endroit ou l'on cree (Image, Logo intro et vignette, Musique, Video), par ordre alphabetique ; le clic droit sur l'apercu et le bouton Musique ouvrent le meme menu.
- IA locale partagee entre les logiciels PhilFactory : dossier commun "IA PhilFactory" choisi par vous ; les modeles deja telecharges y sont ranges (deplaces sur le meme disque, sinon copies et verifies) ; un modele deja telecharge par un autre logiciel (dossier commun, portable range a cote, donnees d'un autre logiciel Phil...) est repris sans retelechargement ; un modele encore utilise par un autre logiciel n'est jamais efface. Preferences > IA locale > "Dossier commun des IA PhilFactory...".

### 0.9.45
- Tampons video > Chercher en ligne (YouTube) : comme sur le site, la suite arrive quand on descend en bas de la liste, ou par "30 resultats de plus" ; la liste garde l'endroit ou vous etiez.

### 0.9.44 (retours du 11 novembre, fin de soiree)
- Fenetre de mise a jour comme PhilPDF : plus de bouton de reduction de Windows ; "Reduire" la range dans la barre du bas, la croix et Echap aussi tant que le telechargement continue.
- Recherche YouTube (tampons video, musique en ligne) : vos mots exacts, YouTube ne les corrige plus ("tonton flingur" reste "tonton flingur") ; toujours 30 resultats en tout (20 videos puis 10 Shorts, ou 30 videos, ou 30 Shorts).
- Fabrique musique : "Choisir un morceau..." propose un fichier ou la recherche en ligne (archives libres, YouTube Music, YouTube) ; voix de reference : un enregistrement, la voix seule d'un morceau de ce poste ou trouve en ligne (separee sur ce poste, experimental, modele "Voix seule d'un morceau" a installer), toujours seulement votre voix ou celle d'une personne d'accord.
- Atelier de logo : en tete du menu Logo, intro et vignette ; votre logo se pose dans la vignette (coin au choix).
- Vignette de la video (miniature YouTube) : nom et explication clairs, bouton principal "Utiliser comme vignette de la video", aussi dans Outils et dans Publier, ou elle est envoyee a YouTube avec la video (si la chaine est validee par telephone).

### 0.9.43 (retours d'ergonomie du 11 novembre)
- Menu Fabrique range en trois sous-menus, chacun avec une phrase d'explication : Video, Musique, Logo intro et vignette ; noms plus clairs ; une seule entree pour la Sequence IA ("Nouvelle histoire..." est dans sa fenetre).
- Plan video a partir d'une phrase : l'IA de ce poste est proposee en premier (gratuite, 5 s au plus), puis Gemini, puis Google Flow ; le plan calcule se regarde avant d'etre integre.
- Sequence IA : texte plus grand, l'essentiel en gras ; video par ce poste d'abord, Gemini ensuite, Flow en dernier.
- Atelier IA : effets par ordre alphabetique, noms longs a la ligne (plus de defilement horizontal).
- pCloud par WebDAV (adresse e-mail et mot de passe, dans le coffre du systeme) : sans application a declarer chez pCloud. Envois et receptions WebDAV en flux (gros rushes).
- Menu Aide : "Guide de test de la premiere version" retire.

### 0.9.42
- pCloud en direct : autorisation dans le navigateur (aucun mot de passe donne a PhilCut), envoi des gros fichiers en flux.
- kDrive d'Infomaniak par son API : adresse ou numero du kDrive et jeton d'API (range dans le coffre du systeme), envoi par morceaux des gros fichiers.
- Preferences > Comptes et synchro > Projets entre vos appareils : choix du compte qui recoit les copies legeres des rushes (par exemple pCloud, et Google Drive pour les reglages) et du dossier d'echange des rushes sur ce compte (bouton "Choisir..."), le meme pour tous vos postes.

### 0.9.41
- Mise a jour et relance (theme, langue) : PhilCut se ferme proprement avant l'installation (memes questions qu'a la fermeture, arret des taches et du son), l'installation attend qu'il soit ferme puis le relance. Windows ne signale plus de "plantage" de PhilCut.exe au redemarrage.

### 0.9.40 (retours des essais du 9 novembre)
- Aucune fenetre ne depasse plus l'ecran, meme quand elle grandit apres coup (apercu d'un resultat, liste qui s'allonge) : son contenu defile.
- Plan video IA (Gemini, Kling...) : range dans Videos > PhilCut > Plans IA, avec un bouton "Ouvrir le dossier" ; pendant l'attente, le temps ecoule et une explication (le service ne donne pas son avancement) ; ses reglages sont gardes : clic droit > "Reprendre la creation" rouvre la Fabrique remplie. Meme chose pour un plan recu de Flow.
- Nouveau modele "Gemini Omni 1.2 Flash 720p" (avec repli automatique sur la 1.1 si votre clef n'y a pas encore acces).
- Aide Flow refaite d'apres notre essai : reglages a choisir, 50 credits par jour, Veo 3.1 Lite (10 credits pour 8 s), file d'attente, telechargement.
- Musique en ligne : bouton "Mettre a jour yt-dlp" ; artiste, album, annee et duree des titres YouTube Music ; curseur pour aller au passage voulu, ce qui est lu est affiche ; "Pause" ne reste plus affiche en changeant de morceau ; la case "libre de droits" n'est jamais cochee d'office, et la licence d'archive.org est signalee comme annoncee par la personne qui a depose le fichier.
- Menu Fabrique : l'IA locale est presentee pour ce qu'elle fait (effet ou image animee a partir du film).

### 0.9.39
- Mise a jour : la fenetre se reduit (bouton "Reduire" ou bouton de reduction) ; le telechargement se suit dans la barre du bas, avec "Afficher" pour la rouvrir et "Installer et redemarrer" a la fin. Plus d'estimation fantaisiste du temps restant pendant les premieres secondes.

### 0.9.38
- Creations a refaire ou a calculer : les images retouchees, logos et repliques se refont aussi depuis la liste, sur ce poste (gratuit) ou avec Gemini (cout total annonce et confirme, "deja payee une fois" signale). L'image de depart est gardee avec la recette, la creation se refait donc sur un autre appareil.
- Fabrique musique : pour ameliorer la consigne et ecrire les paroles, Claude est propose en premier (le meilleur pour ecrire), puis Gemini, puis l'IA locale.

### 0.9.37
- Fabrique musique (menu Fabrique, ou bouton Musique) : une fiche musicale (style, ambiance, tempo, tonalite, mesure, instruments, deroule, epoque et son, voix, paroles) devient une consigne solide en anglais, visible avant de creer. 42 styles en 8 familles, dont Symphonie, Classique, Baroque, Opera, Piano romantique, Valse, Choeur sacre, Chant gregorien, Marche, et des styles d'epoque (annees 30, musette, rock'n'roll, disco, synthwave). Nouvelles voix : tenor lyrique, mezzo-soprano, choeur de moines.
- "Ameliorer avec l'IA" : l'IA (locale, ou cloud avec cout annonce) reecrit la fiche comme un producteur ; on relit et on modifie avant de creer.
- "S'inspirer d'un morceau" : le morceau est analyse sur le poste (tempo, tonalite, mesure, son, deroule ; genre et instruments si le moteur le permet) ; seul le style est garde, jamais la melodie, les paroles ni le nom. Un morceau declare libre de droits ou a vous peut aussi etre reorchestre dans le style choisi.
- Voix de reference : votre voix, ou celle d'une personne d'accord (declare). Jamais un chanteur ou une personne connue : son style est decrit ("a la maniere de").
- Musique en ligne : chercher, ecouter et telecharger le son d'un titre YouTube Music, d'une video YouTube, ou d'un enregistrement libre d'archive.org ; texte clair sur les droits (oeuvre et enregistrement), source gardee dans le fichier.
- Creations a refaire ou a calculer (menu Fabrique) : les creations IA demandees ailleurs ou dont le fichier manque ; proposees, jamais lancees seules ; une creation deja faite ici ou sur le Drive est reprise, jamais payee deux fois ; comparaison avant / apres.

### 0.9.36
- 44 elements animes, en 6 familles (bouton Goodies) : Reactions et emoji (coeur qui bat, coeurs qui s'envolent, etincelles, visages, pouce, flamme), Fleches et reperes (fleches qui se tracent, cercle et soulignement a la main, coche, croix, !, ?, cible, curseur qui clique, chevrons), Vlog et reseaux (point d'enregistrement, cloche, bulles, chargement, epingle de lieu, avion qui passe, horloge, loupe), Meteo et nature (soleil, nuage, pluie, eclair, flocon, arc-en-ciel), Fete (feu d'artifice, ballons, etoile filante, cadeau, explosion de BD), Formes (ondes, bulles, pastille). Dessins vectoriels : nets a toute taille, couleurs modifiables, identiques sur PC et (bientot) telephone. Le catalogue s'enrichit chaque mois sans reinstaller.
- Galerie des Goodies : l'element choisi s'anime a droite ; recherche, favoris, utilises recemment.
- Inspecteur d'un element : ses couleurs, son animation (en boucle, s'arrete a la fin, disparait a la fin), sa vitesse.
- Plan grise ("Introuvable ici") : double-clic ou clic droit > "Ou est ce fichier ?" pour le rattacher directement.

### 0.9.35
- 51 nouveaux effets, en 7 familles (Effets du plan) : Retro (8 mm, Super 8, sepia, delave, raye), VHS et camescope, RVB decale, Glitch, Lentille (vignette, lampe, flou du bord, fisheye), Ouvertures (cercle, rideau, losange, coeur...), Cinematique (bandes, teal & orange, noir et blanc, projecteur), Mouvement (flash, zoom pulse, secousse, tourbillon), Lumieres (neon, contours, etoiles, lucioles, poussiere, neige, confettis, fuites de lumiere). Ils sont calcules par la carte graphique ; sans carte graphique, une version simplifiee est utilisee. Le catalogue se met a jour tout seul depuis Internet.
- Le "Lueur" ne rend plus les noirs violets.
- Projets entre vos appareils : un projet retrouve ses videos tout seul sur un autre poste (meme dossier, Telechargements, Drive...). Fichier > "Medias introuvables sur ce poste..." : on indique ou est un fichier, les autres du meme dossier suivent. Un media absent reste a sa place, grise ("Introuvable ici") : rien n'est supprime.
- Si un projet a ete modifie sur un autre appareil, votre version est enregistree et l'autre gardee dans les sauvegardes automatiques.
- A l'enregistrement, PhilCut peut proposer une copie legere 720p des videos et deposer les creations IA sur le Drive (jamais d'office) : on monte ailleurs sans l'original, et une creation IA n'est pas payee deux fois.
- Fichier > "Espace PhilCut sur le Drive..." : liste ce qui prend de la place, cases pre-cochees pour ce qui ne sert plus, suppression apres votre clic.
- Preferences > Comptes et synchro : copie legere, depot des creations, delai de nettoyage, superpositions avec transparence (attention : mal lues par certains telephones Android).

### 0.9.34
- Montage > Atelier IA : l'entree video s'appelle "Video IA sur la partie en jaune (animer l'image, dessin anime, ralenti...)" et "Sequence IA..." y est aussi, en plus du menu Fabrique.

### 0.9.33
- Sequence IA (Fabrique > "Sequence IA...") : une petite histoire devient plusieurs plans qui se suivent. L'IA (de ce poste ou cloud) propose les personnages, les lieux, les plans avec leur cadrage et des repliques ; chaque personnage garde la meme description d'un plan a l'autre, peut avoir un style "a la maniere de" (allure et jeu, jamais le visage) et des images de reference (personnes d'accord, lieux). Pour chaque plan : consigne detaillee en anglais (sans aucun nom), "Ameliorer" par l'IA, image de depart choisie ou composee (Gemini reunit personnages et lieu). Video par l'IA de ce poste, un generateur cloud avec votre clef (prix annonce), ou Google Flow pas a pas (consigne copiee, dossier des images de reference ouvert, video telechargee rattachee au plan). On regarde chaque plan, on le refait si besoin, puis "Monter la sequence" pose les plans, les repliques (dites avec la maniere de parler de chacun : froid pour un style Delon, gentleman pour un style Templar...) et une musique.
- Fabrique > Plan genere par IA : "a la maniere de ..." dans le sujet est transpose automatiquement (le nom n'est jamais envoye) ; bouton "Style a la maniere de..." ; consigne traduite en anglais.
- Nouveaux styles : Simon Templar, Roger Moore, Cary Grant ; maniere de parler "Gentleman britannique".
- Vignette composee, zone verte : ecrire OK ou NON apres chaque element (ou les boutons "Fait" / "Pas fait") ; la ligne "Pastilles" montre tout de suite ce que PhilCut a compris.

### 0.9.32
- Zones floutees (visage, plaque, ecran) : s'il y a une partie jaune, la zone tracee la couvre exactement ; le suivi part de l'image ou la zone a ete tracee, en avant et en arriere.
- Corriger le suivi : arreter la ou la zone decroche et la glisser a sa place (ou tirer un coin) ; la correction vaut a cet instant et s'estompe sur 0,6 s autour. Maj + glisser deplace toute la trajectoire. Explication dans l'Inspecteur.
- Google Flow : la Fabrique explique pas a pas ce que fait PhilCut et ce qu'il faut faire dans Flow ; l'attente du clip telecharge se voit dans la barre du bas (etape, temps ecoule, Arreter) ; le clip recu s'affiche d'abord en apercu : inserer a la ligne rouge, garder dans les medias ou jeter.
- Fabrique > "Mes plans IA deja fabriques (dossier)..." ouvre le dossier ou sont gardes les plans generes (Gemini, Kling...) et les logos, meme s'ils ne sont plus dans un projet.

### 0.9.31
- Goodies, titres, logos, tampons sur la piste du haut : on raccourcit ou allonge a la souris en tirant le bord gauche ou droit (la duree s'affiche pendant le geste).
- Modeles de montage : "Monter avec ce modele" marche aussi quand les rushes viennent d'etre ajoutes depuis la fenetre des modeles.
- Etalonnage : explication du rideau jaune (glisser pour comparer avant / apres), curseur "Image du plan" pour choisir l'image a la souris, image retrouvee de facon plus sure (sinon un message l'explique).
- Montage : Ctrl + molette (ou molette sur le nom des pistes) monte et descend dans les pistes ; ascenseurs plus larges et bien visibles.
- Menu Musique : icones accordees au reste du menu.
- Musiques : les numeros de piste ne collent plus au nom de l'artiste ("17 Queen" devient "Queen").
- Ecriture des paroles, transposition de style, replique : barre d'attente avec le temps ecoule et un bouton Arreter.
- Musique IA : temps restant, et explication quand la barre est a 100 % mais que le moteur finit le fichier. "Essayer la voix" fait 15 s pour l'ecouter avant. Onze voix de plus (crooner, rauque, soul, douce, folk, lyrique, grave, chanson, country, electro, gospel).
- Bouton "Style a la maniere de..." dans les creations : on choisit un chanteur, un acteur, un film dans une liste avec la description du style.
- "Ajouter aux medias seulement" devient "Garder dans les medias (sans poser)", avec une explication sur chaque choix.
- Transitions : leur nom est sur sa propre ligne, il ne chevauche plus le nom des plans.
- Synchro : cliquer sur "2 envoyes" montre ce qui a ete envoye et recu, avec une explication. Les reglages ne sont plus renvoyes chaque minute sans raison.
- Espace lit avec les effets quand il y en a devant la ligne rouge (option dans le clic droit de l'apercu).
- Journal des echanges et fenetre de reprise apres plantage : bouton Copier.
- Tampons : "Personnaliser (texte, duree)..." cree votre version d'un tampon.

### 0.9.30
- Presentation de photos : les images peuvent venir des videos du montage. "+ Derniere image du plan" ajoute la derniere image du plan a la ligne rouge (celui apres lequel la presentation est inseree : l'enchainement est parfait) ; "+ Images d'une video..." ouvre une planche d'images du plan (ou du plan selectionne) : on coche celles a garder, ou "Repartir sur tout le plan" en coche le nombre voulu. Les images retenues s'affichent dans une bande : glisser pour changer l'ordre, clic droit pour retirer.

### 0.9.29
- Presentation de photos animee : deux animations de plus, "Tourbillon" (la photo s'enroule en spirale et disparait au centre, la suivante en jaillit en tournoyant) et "Feuilles qui tombent" (les photos tombent comme des feuilles d'automne, en se balancant et en virevoltant, et se posent les unes sur les autres). Dix animations en tout.

### 0.9.28
- Etalonnage simple (clic droit sur un plan > "Etalonnage...", ou Montage > "Etalonnage du plan...", Ctrl+Maj+E) : l'image du plan a la ligne rouge avec un rideau avant / apres que l'on fait glisser ; trois roues de couleur (ombres, tons moyens, hautes lumieres) ; exposition, contraste, saturation, temperature, teinte. "Auto" retire une dominante et redonne du peps ; "Accorder sur ce plan" donne a un plan la lumiere et les couleurs d'un autre (deux cameras, deux heures de la journee) ; "Copier" sur les plans du meme rush ou sur tous. Meme rendu a l'apercu et a l'export ; Ctrl+Z revient.

### 0.9.27
- Presentation de photos animee (Montage > "Presentation de photos animee...") : une serie de photos devient un clip anime, dessine sur ce poste. Huit animations : lancer de cartes sur une table, explosion en particules (les fragments sont des morceaux de la photo, la suivante se reforme), puzzle qui s'assemble, pile de photos qui s'envole, mur de photos ou la camera plonge, carrousel 3D, eventail comme une main de cartes, polaroids sur une corde qui se balancent. La vignette de chaque animation bouge quand on la survole. Fond floute, sombre, table en bois ou clair ; duree par photo ; ordre de prise de vue. On regarde avant de poser ; "Ranger dans ma bibliotheque".
- 4 modeles de montage a photos (lancer de cartes, explosion, mur de souvenirs, polaroids sur une corde) : la presentation devient le montage, avec la musique et le titre anime.
- Les modeles integres evoluent par le catalogue en ligne (nouvelles transitions ajoutees, autre animation de photos) et le catalogue peut ajouter des variantes de presentations (premieres : "Confettis de photos", "Grand puzzle") ; le Diaporama passe a la pile qui s'envole.

### 0.9.26
- Nouveautes du catalogue (Aide > "Nouveautes du catalogue...", et bouton "Nouveautes..." dans la galerie des Goodies) : chaque mois, une veille automatique ajoute des Goodies, des modeles de montage, des styles "a la maniere de" et des modeles de tampons IA, sans reinstaller PhilCut. ✦ marque ce que vous n'avez pas encore vu (dans la liste, la galerie des Goodies et les modeles) ; "Verifier maintenant" interroge le catalogue et dit s'il y a du nouveau ; un double-clic ouvre l'endroit ou l'utiliser. Copie gardee pour les jours sans reseau.
- Premier envoi : packs de Goodies "Reactions" (coeur qui bat, pouce leve, etoile, eclair, point d'exclamation, bulle WOW) et "Meteo et nature" (soleil, nuage, pluie, flocon), animes ; 3 modeles de montage (recette de cuisine, avant/apres travaux, recap de l'annee) ; 9 styles (Top Gun, Le Grand Bleu, Les Bronzes, Fernandel, Jean Reno, Dalida, Claude Francois, Charles Trenet, Michel Legrand) ; 4 tampons IA (decollage d'avion, pause cafe, a suivre, flash meteo).
- Tout ce qui arrive est verifie par les tests avant publication (dessins sans script ni lien externe, transitions et sons existants, aucun nom dans les descriptions de style).

### 0.9.25
- Modeles de montage (Montage > "Modeles de montage...") : 10 modeles tout faits (Vlog voyage 30 s vertical, Vlog 2 min, Short dynamique 15 s, Vol en avion 1 min, Souvenirs de famille, Anniversaire, Bande-annonce cinema, Presentation d'un lieu, Annonce 20 s, Diaporama de photos). PhilCut analyse vos rushes sur ce poste et monte a la facon du modele : format, duree, rythme des coupes, transitions, look, titre anime, ecran de fin, musique du projet calee sur les temps forts. Tout reste modifiable ; Ctrl+Z revient au montage d'avant. Rien de payant, aucun filigrane.
- Exports en serie : dans la fenetre d'export, "Exporter aussi en" coche autant de formats que voulu (YouTube, 4K, Reels 9:16, carre, WhatsApp, ecran LED) : un fichier par format, d'un coup ; les plans qui suivent une personne la suivent dans chaque format, les autres passent en fond flou. Les formats coches sont retenus.

### 0.9.24
- Prolonger un plan trop court : clic droit sur un plan > "Prolonger ce plan (image tenue, ralenti ou IA)...". De 0,5 a 6 s, a la fin ou au debut, de trois facons : image tenue avec un lent zoom (instantane), ralenti de la derniere seconde avec images fondues, ou suite de la scene inventee par l'IA video locale. Le son du plan est prolonge (ambiance en fondu) ou silence. On regarde le resultat avant de le poser ; la suite du montage (plans, textes, Goodies, sous-titres) est decalee ; Ctrl+Z l'enleve.

### 0.9.23
- Monter par le texte (Montage > "Monter par le texte...", Ctrl+T) : les rushes sont transcrits sur ce poste (une seule fois, garde dans le projet) et le texte de ce qui est dit s'affiche dans l'ordre du montage. Selectionner des mots puis "Couper ce passage" (ou Suppr) coupe la video et recolle la suite ; "Garder seulement ce passage" ; un clic sur un mot y amene la ligne rouge ; pendant la lecture, le mot entendu est surligne en jaune ; recherche d'un mot.
- "Retirer les euh" (euh, hum, bah, ben isoles...) et "Retirer les silences de plus de 0,8 s" (reglable), avec leur nombre affiche avant de cliquer. La musique continue sous les coupes (au choix). Ctrl+Z annule.

### 0.9.22
- Sauvegarde automatique : chaque minute (reglable : 1, 2 ou 5 minutes, ou jamais), une copie de chaque projet modifie est faite a part, sans toucher a votre fichier ; les 5 dernieres versions sont gardees (reglable). La barre du bas l'indique discretement.
- Recuperation apres plantage : si PhilCut s'est mal ferme (plantage, coupure de courant, redemarrage de Windows), il propose au demarrage de recuperer chaque projet non enregistre ("Recuperer les projets coches", "Jeter", "Plus tard"). Le projet recupere garde son emplacement : "Enregistrer" ecrit au bon endroit.
- Fichier > "Revenir a une sauvegarde automatique..." : la liste des dernieres versions du projet ; un clic y revient, Ctrl+Z ramene l'etat actuel.
- Preferences > General > Sauvegarde automatique : intervalle, nombre de versions, "Ouvrir le dossier des sauvegardes".

### 0.9.21
- Replique dite dans un clip IA : la video donne le jeu, un moteur de voix a part donne le phrase, et les deux sont meles dans le meme clip. Atelier IA > un effet video > "Replique dite" : le texte, la maniere de parler (prise automatiquement du style de la phrase, ex. "joue comme Alain Delon" > froid et impassible, "a la John Wayne" > lent et trainant, "style Belmondo" > gouailleur ; ou au choix parmi 15 : bourru, nerveux, naif, detective de film noir, crooner, heros d'action, theatral, chuchote, conteur, bande-annonce...), et le moteur : voix locale (debit, pauses entre les phrases, expressivite, hauteur, grain) ou voix Gemini (joue vraiment la phrase d'apres la consigne de jeu ; prix affiche). "Ecouter la replique" avant de creer ; "Recrire la replique a sa maniere (IA)" change les tournures sans citer de replique de film ; "Refaire seulement la voix" garde le clip. Une replique plus longue que le clip tient la derniere image. Maniere de dire, jamais la voix d'une personne : aucun clonage.

### 0.9.20
- Styles "a la maniere de" dans l'Atelier IA : "une ballade chantee a la maniere de Sinatra, musique facon Liza Minnelli", "un cow-boy a la John Wayne, look Star Wars", "un gangster joue comme Alain Delon". Le nom est remplace par la description du style (grain et maniere de chanter, orchestre, epoque ; lumiere, pellicule, decors, costumes, attitude et maniere de parler de l'acteur). La fenetre montre la transposition sous la phrase ; le nom n'est jamais envoye au moteur. Environ 80 references connues hors ligne (chanteurs, groupes, compositeurs, acteurs, films, realisateurs) ; un nom inconnu se transpose par l'IA locale ou cloud, sur votre clic, et rejoint "Mes styles" (Preferences > Assistant et IA), modifiables et synchronises. Marche aussi pour l'image des tampons IA.
- Creations de l'IA : Preferences > Assistant et IA > "Ouvrir le dossier des creations", taille du dossier, "Nettoyer maintenant", et nettoyage automatique au choix (jamais, 30 jours, 90 jours, 1 an ; 90 jours par defaut) de ce qu'aucun projet recent ou ouvert n'utilise.

### 0.9.19
- Reprendre une creation IA : chaque musique, image ou clip cree garde sa "recette" (phrase, paroles, qui chante, langue, duree, force) a cote du fichier. Clic droit sur le plan dans la timeline (ou sur le media) > "Modifier la creation IA (phrase, paroles, duree)..." : l'Atelier IA se rouvre pre-rempli ; on change ce qu'on veut, on recree, on ecoute, puis "Remplacer le morceau d'origine" (meme place dans le film ; Annuler revient a l'ancienne version, qui reste dans les medias).
- Enregistrer une copie : "Enregistrer sous..." dans l'Atelier IA (musique, image, clip) et "Enregistrer une copie sous..." au clic droit d'un media, d'un plan de la timeline ou d'un tampon de la bibliotheque. Premiere fois dans le dossier Musique, Images ou Videos du systeme, ensuite le dernier dossier choisi. La recette IA suit la copie (et le rangement dans la bibliotheque).

### 0.9.18
- Musique IA avec paroles : qui chante (femme, homme, duo, choeur, enfant, rap), langue des paroles, paroles sur plusieurs lignes, et "Ecrire les paroles par l'IA" (locale ou cloud) a partir du theme et du debut que vous avez tape.
- "Ranger dans ma bibliotheque" : musiques et clips crees rejoignent la bibliotheque (celle des tampons : rangee, synchronisee).
- Tampons IA (Montage > Tampons video > Tampons IA) : 12 modeles preremplis (fusee cartoon, BOUM bande dessinee, soucoupe volante, robot, chat surpris, trophee, jackpot, eureka, hyperespace, dodo, "quelques heures plus tard", alerte) : image dessinee par l'IA (locale ou cloud), mouvement, texte qui claque, bruitages et phrase dite avec un style de voix (robot, aigue, grave, radio, echo). Tout est modifiable.
- Trajet : vraie carte OpenStreetMap (glisser, molette, double-clic pour poser un point), recherche d'aerodrome par code, nom ou ville, telechargement de tous les aerodromes du monde (OurAirports, libre), et "Mes points" gardes et synchronises.

### 0.9.17
- Medias du projet plus compacts, avec une vraie vignette : image du film, l'image elle-meme, et pour un son sa pochette (image integree au MP3, FLAC, M4A) ou sa forme d'onde dessinee, avec la duree et un badge "IA" pour ce que PhilCut a cree.
- Menu Fabrique : chaque entree dit ou elle travaille ("sur ce poste" ou "IA cloud") ; nouvelles entrees "Logo, intro ou miniature par IA locale" et "Plan ou effet video par IA locale".

### 0.9.16
- Atelier IA : une musique ou un clip cree n'est plus pose tout seul. On l'ecoute (ou le regarde) dans la fenetre, on garde le morceau voulu ("Debut ici", "Fin ici", fondus), puis "Poser sous la video", "Poser a la ligne rouge", "Ajouter aux medias seulement" ou "Recreer".
- Plusieurs pistes de musique : la piste M2 (et les suivantes) s'entend enfin a la lecture.

### 0.9.15
- Voix, Sous-titres, Musique, Cadrage, formes et modeles de logo : une vraie fenetre de choix (une ligne par choix, son explication, ✓ pour ce qui est deja en place) au lieu d'un petit menu sous la souris.
- Bruitages : 29 sons au lieu de 8 (whoosh inverse, montee, descente, boum, tic-tac, buzzer, validation, notification, laser, roulement de tambour, cymbale, gong, sonnette, battement de coeur, boing, machine a ecrire, sifflet, vent, pluie, glitch, caisse enregistreuse...), un clic pour ecouter, et "Plus de sons" ouvre la bibliotheque des tampons (vos sons, repliques, sons en ligne).

### 0.9.14
- YouTube : regarder et telecharger marchent a nouveau. YouTube oblige yt-dlp a utiliser Deno (petit programme libre, depot officiel) : PhilCut propose de l'installer (environ 45 Mo), aussi par "Mettre a jour yt-dlp".
- "Videos et Shorts" : les Shorts sont cherches a part (la recherche simple de YouTube n'en renvoie presque pas) et places a la fin ; toutes les vignettes ont la meme taille, le nombre annonce est celui affiche ("30 video(s) et 15 Short(s)").
- Choisir une image, une video, un son : la premiere fois le dossier du systeme (Images, Videos...), ensuite le dernier dossier utilise pour ce genre (Fabrique, Goodies, logo, rushes, tampons, sous-titres...).
- Volet Proposition : rien ne deborde quand on le retrecit (boutons et listes suivent sa largeur).
- Musique IA : le moteur Windows refait avec Visual C++ est en ligne (Reinstaller le moteur).

### 0.9.13 : test des modeles plus clair
- "Tester ce modele" efface tout de suite l'ancien resultat : "Test en cours..." avec sa barre d'avancement, puis le nouveau resultat (ou l'ancien remis si le test est arrete). Le cadre d'aide grandit avec son texte, les boutons restent a leur place.
- Tableau de bord, carte du trajet et manche a air ne sont plus dans le menu Montage ni dans le clic droit : ils sont dans les Goodies (bouton "Tableau de bord complet..." pour plusieurs instruments ensemble).
- Moteur de musique Windows : la fabrication avec Visual C++ est reparee (Visual Studio du serveur trouve automatiquement).

### 0.9.12 : musique IA reparee
- Le moteur de musique pour Windows avait ete fabrique avec le mauvais compilateur (MinGW) : il demandait libgomp-1.dll, libgcc_s_seh-1.dll, libstdc++-6.dll et libwinpthread-1.dll, absentes de Windows (code 3221225781). Il est refait avec Visual C++, sans aucune bibliotheque a installer. Preferences > IA locale > Musique > "Reinstaller le moteur".
- Chaque moteur Windows publie est desormais verifie : la fabrication echoue s'il demande une bibliotheque qui n'est ni livree ni dans Windows.

### 0.9.11 : agrandissement IA repare
- L'archive du moteur d'agrandissement (Real-ESRGAN) etait publiee sans ses modeles ("_wfopen models/realesrgan-x4plus.param failed") : elle est refaite avec ses modeles. Preferences > IA locale > Agrandissement IA > "Reinstaller le moteur" (ou decocher puis recocher) la telecharge.
- PhilCut verifie la presence du modele avant de lancer, et le diagnostic dit "Les modeles du moteur manquent" (ni la carte graphique ni le pilote ne sont en cause).

### 0.9.10 : la bonne solution, et la synchronisation des reglages
- Moteur d'IA qui ne demarre pas (code 3221225781) : PhilCut cherche lui-meme quelle bibliotheque manque et propose la seule bonne solution (Visual C++ de Microsoft, reinstaller le moteur, ou pilote Nvidia seulement si c'est son fichier qui manque).
- Outil a lancer a la main : outils/dll_manquantes.ps1 (PowerShell) liste les bibliotheques qui manquent a chaque moteur.
- Synchronisation avec un Drive en direct (Google Drive...), un NAS ou un FTP : elle est enfin faite. Au demarrage, comme PhilPDF, la fenetre "Synchronisation avec ..." montre ce qui arrive de vos autres postes ; ensuite, chaque minute et a la fermeture, les changements de ce poste partent sans rien demander ; la barre du bas dit ce qui a ete recu et envoye. Outils > "Synchroniser maintenant" refait l'echange complet.

### 0.9.9 : clarte
- IA locale en panne : la cause en clair et la solution en boutons (installer Visual C++ de Microsoft, passer sur le processeur, reinstaller le moteur, mettre a jour le pilote), dans Preferences > IA locale et dans l'Atelier IA. Musique et images : si la version carte graphique ne demarre pas, nouvel essai automatique sur le processeur. Agrandissement et ralenti : la carte dediee (Nvidia, AMD) est choisie toute seule sur un portable a deux cartes.
- Resultats des tests des modeles lisibles : une ligne verte ou rouge, les details replies.
- Tampons : fenetre "Ou mettre ce tampon ?" (debut, ligne rouge, partie en jaune, fin ; inserer, par-dessus, remplacer ; accelerer, ralentir ou couper ; format different du projet : fond flou, bandes, recadre, suivi de la personne).
- Bibliotheque des tampons rangee a votre idee (mon ordre par glisser, favoris, plus utilises...), qui suit sur vos autres postes. Nouvelle page Preferences > Tampons et extraits.
- Recherche YouTube : plus de resultats, avec vignettes, sur le YouTube de votre pays, sans traduction ; Shorts ; "Vouliez-vous dire ... ?" ; regarder la video dans PhilCut et choisir le morceau ; coller un lien (YouTube, Vimeo, fichier .mp4).
- Vignettes : chaque couleur expliquee avec un exemple ; chaque zone a son texte (pastilles, titre, etiquette de la fleche), lu aussi par l'IA.
- Mes musiques : classement par artiste et album corrige (etiquettes FLAC/OGG/M4A, artiste de l'album, ordre des pistes, plus de numeros pris pour un artiste), lecture des etiquettes plus rapide et visible.
- Menus : libelles courts avec l'explication au survol, "echanges radio" range dans Sous-titres, "tete de lecture" devient "ligne rouge".

### 0.9.8 : fiabilite
- Mise a jour : "Telecharger et installer" ouvre une fenetre qui montre le telechargement (Mo, vitesse, temps restant, Arreter), puis "Installer et redemarrer". Depuis une version 0.8.x, telecharger une fois la nouvelle version a la main.
- Fermeture : plus de plantage a l'arret (taches de fond encore vivantes) ; le son est arrete proprement avant de quitter ; l'attente des operations ne bloque plus la fenetre (3 s au plus en tout).
- Quitter avec des operations en cours : la liste de ce qui tourne (nom, pourcentage, etape), "Voir les operations", "Quitter quand meme" ou "Rester".
- Bibliotheque musicale : le dossier (disque reseau, NAS endormi) n'est plus touche a l'ouverture de la fenetre ; plus de gel.
- La fenetre ne depasse plus l'ecran a l'ouverture d'un projet ; la timeline peut retrecir davantage (petits ecrans).

### 0.9.7 : extraits de videos en ligne
- Tampons > Chercher en ligne > "Videos en ligne : YouTube et autres, par yt-dlp" : une adresse ou des mots, la liste des resultats (titre, chaine, duree, licence Creative Commons mise en avant), puis seul le morceau choisi (de ... a ...) est telecharge, video ou son seulement, et rangé dans la bibliotheque avec son credit.
- Ce qui est permis, clairement indique (70 ans apres la mort du dernier auteur en France et en Europe, licences libres, courte citation), avec une confirmation la premiere fois. yt-dlp est telecharge au premier usage depuis son depot officiel et se met a jour d'un clic.
- "Films du domaine public : Internet Archive" : recherche et morceau extrait sans telecharger tout le film.
- Preferences > IA : groupe "Extraits en ligne" (ajout automatique des telechargements, yt-dlp, ce qui est permis).
- ZoneSons retire.

### 0.9.6 : bibliotheque de sons et d'extraits
- Tampons > Chercher en ligne : Kaamelott (fspot) ; la recherche reste en francais sur ce site et sur Voicy (pas de traduction en anglais) ; pour Kaamelott, la replique tapee est copiee, a coller dans la recherche du site.
- Ce que vous telechargez depuis le site arrive tout seul dans votre bibliotheque : PhilCut guette le dossier Telechargements pendant 15 minutes (case "Ajouter tout seul ce que je telecharge").
- Ma bibliotheque : un clic sur un son l'ecoute (table de sons), bouton "Ecouter", "Raccourcir..." (garder seulement de ... a ..., avec ecoute avant).

### 0.9.5 : retirer le fond d'une image
- Une image sans transparence (JPG d'un logo sur fond blanc, photo d'un objet ou d'une personne) devient une copie PNG transparente, sur ce poste : bouton "Retirer le fond..." de la fenetre Goodie (propose tout seul quand on choisit un JPG), clic droit sur l'image dans les medias, ou sur son plan dans la timeline.
- Avant / apres sur damier, methode (automatique, fond uni, sujet d'une photo), tolerance, recadrage au sujet, interieur des lettres et des anneaux au choix. L'original est garde.

### 0.9.4 : timeline plus simple
- Un clic ou un glissement deplace toujours la tete de lecture rouge : plus de partie jaune creee par erreur.
- Partie jaune : double-clic sur la regle au debut, puis a la fin (fanion "Debut" entre les deux) ; ou boutons [ ] a cote de la tete rouge ; ses bords se tirent sur la regle pour l'ajuster.
- La molette zoome la timeline la ou est la souris (Maj + molette : defiler) ; un rappel "Zoom" anime en haut a gauche, clic dessus : tout voir.
- Le curseur et les bulles d'aide disent ce que fera le clic a chaque endroit de la regle.

### 0.9.3 : vignettes et images fixes composees
- Fabrique > "Vignette YouTube composee" (aussi au clic droit sur l'apercu et sur la regle de la timeline) : on prend une image du film et on entoure des zones a la souris. Rouge : ce qu'on veut montrer (objet ou personne du film, detoure, contour, effet loupe ou projecteur). Jaune : designer (fleche ou cercle). Bleu : le titre, ajuste tout seul. Vert : les elements precises (pastilles validees ou non). Blanc : zone a laisser libre.
- PhilCut dessine tout lui-meme d'apres un kit coherent (Punchy, Editorial, Documentaire, Tech, Aviation) et une palette tiree de l'image : pas d'aspect "fait par IA". Phrases pretes a l'emploi et modifiables ; l'IA locale ou cloud peut proposer le titre, les elements et le style.
- Avant / apres coupe en diagonale, apercu en taille telephone avec conseils de lisibilite, 3 variantes d'un clic.
- Resultat : miniature YouTube de l'export (integree au MP4 et JPG a cote), image enregistree, ou image fixe posee dans le film au-dessus de la video (duree au choix), que l'on rouvre par clic droit > "Modifier l'image composee".
- Preferences > IA locale > "Tester les modeles installes" (et "Tester" par modele) : un petit travail reel chronometre par modele, avec carte graphique ou processeur, progression et arret ; avertissement sur la qualite des images IA sans carte graphique dediee.

### 0.9.2
- Plus de sous-menu "Aviation" : tableau de bord, carte animee du trajet, indicateur de vent et sous-titres radio sont ranges avec les Goodies et les sous-titres, dans le menu Montage et au clic droit sur l'apercu.

### 0.9.1
- Fenetre d'un Goodie (double-clic) : apercu anime sur l'image du film, joue en boucle de son debut a sa fin ; chaque reglage (genre, style, position, taille, texte, valeurs) se voit tout de suite.

### 0.9.0
- Musique > "Mes musiques" s'ouvre dans une fenetre : recherche (titre, artiste, album, dossier), classement par dossier, album, artiste ou titre, groupes repliables, ecoute, double-clic pour poser sous la video. Fini le menu geant.
- Atelier IA : la phrase s'ecrit dans sa langue ; PhilCut la traduit en anglais avant de l'envoyer au moteur (images, video, musique) et montre le texte envoye. Sans traduction possible, il demande d'ecrire ces mots en anglais.
- Atelier IA : l'avancement se voit dans la fenetre (etape en cours, pourcentage, temps ecoule) ; en cas d'echec, message clair, journal du moteur et bouton Reessayer.
- Un clip plein cadre pose au-dessus du film (dessin anime IA, effet IA) se voit aussi en lecture normale, avec le son du passage, pas seulement a l'arret.
- Image creee par l'Atelier IA : "Poser au-dessus du film" sur la piste Video 2 (le film n'est plus coupe) ; "Inserer dans le film" reste au choix.
- Timeline plus grande : la barre entre l'apercu et la timeline est visible et descend bien plus haut (le volet de droite defile au lieu de bloquer la hauteur).
- Assistant de montage (Analyser et proposer) : le volet montre ce que fait la machine (lecture des rushes, demarrage du modele local ou envoi a l'IA cloud, verification), avec pourcentage, temps ecoule et bouton Arreter.
- Volet ouvert dans une fenetre plus grande (bouton agrandir) : plus de fenetre noire, le contenu s'affiche.

### 0.8.9
- Fenetre principale ouverte en plein ecran la premiere fois, puis a la taille et a la place de la derniere fois si elles tiennent dans l'ecran : la barre d'etat du bas (telechargements, taches) reste toujours visible.
- Proposition de mise a jour sur l'Accueil : les nouveautes de la version en quelques puces, au lieu des notes brutes.

### 0.8.8
- Telechargements de l'IA locale : une coupure (reseau, serveur, fichier incomplet) reprend toute seule la suite la ou elle s'etait arretee, jusqu'a 8 fois.
- Centre d'activite et fenetre des telechargements : bouton "Reprendre" sur un telechargement en erreur ou arrete ; il repart de ce qui est deja telecharge.

### 0.8.7
- Extraits de films : la recherche s'ouvre bien dans le navigateur par defaut.
- Traduction des recherches fiabilisee : seules la traduction automatique et les correspondances exactes sont gardees (fini « incroyable » -> « Business ») ; dictionnaire enrichi (incroyable, genial, c'est parti...).

### 0.8.6
- Bouton Musique : plus de gel avec un gros dossier de musiques (ou sur un NAS) ; le menu s'ouvre tout de suite, titres, albums et artistes sont lus en arriere-plan.
- Fenetre Effets : la zone Reglages explique quoi faire tant qu'aucun effet n'est pose, et indique quand un effet n'a pas de reglage.

### 0.8.5
- Preferences > IA : clefs Pixabay et Pexels (avec bouton "Creer ma clef"), dans le coffre du systeme.
- Tous les champs de mot de passe, phrase secrete ou clef ont un oeil pour afficher ce qui est tape ; l'indice de la phrase secrete passe au-dessus.
- Importer des rushes et "Rushes -> projet" s'ouvrent dans le dossier Videos du systeme, puis le dernier dossier utilise.
- La regle des temps explique comment choisir une partie en jaune (bulle d'aide).

### 0.8.4 : ecran de lancement, mise a jour reparee
- Ecran de lancement : logo, version, ce que PhilCut est en train de charger et barre de progression, jusqu'a l'ouverture de la fenetre.
- Mise a jour automatique reparee (erreur "takes 1 positional argument but 2 were given" au telechargement) ; la progression affiche les Mo recus. Depuis une version 0.4.x a 0.8.3, telecharger une fois la nouvelle version a la main.

### 0.8.3 : repliques et sons de films
- Tampons video > Chercher en ligne : repliques et sons de films sur Voicy, Movie-sounds.org, MovieSoundClips, WavSource, Sample Focus et QuoDB (recherche ouverte dans le navigateur, son telecharge par vous puis importe).
- Tampons sonores : un son (mp3, wav...) importe dans la bibliotheque se pose a la tete de lecture sur une piste de son libre, sans decaler le film.

### 0.8.2 : extraits de films, recherches traduites
- Tampons video > Chercher en ligne : extraits de films et de series sur clip.cafe, Yarn et PlayPhrase.me (recherche ouverte dans le navigateur, extrait telecharge par vous puis "Importer le clip telecharge" ; avertissement sur le droit d'auteur).
- On tape dans sa langue : PhilCut traduit en anglais les recherches de tampons (Wikimedia Commons, Pixabay, Pexels, extraits) et de musiques libres ; les mots sans traduction sont signales ("tapez en anglais").

### 0.8.1 : les clefs suivent sur vos autres postes
- Preferences > Comptes et synchro > "Synchroniser aussi les mots de passe et clefs" fonctionne : clefs IA, Pixabay, Pexels et mots de passe des comptes sont envoyes chiffres (phrase secrete choisie une fois) dans le dossier de synchronisation, et repris automatiquement sur les autres postes apres avoir donne la phrase une fois.

### 0.8.0 : langues, tampons video, Goodies dessines
- Anglais, allemand, espagnol et italien complets : tous les textes ajoutes depuis la 0.2 sont traduits (un test verifie qu'il n'en manque aucun).
- Montage > Tampons video : 12 tampons maison fabriques sur ce poste ("Quelques heures plus tard...", rembobinage VHS, tele qui s'eteint, bip de censure, tadaa, bravo, rate, amorce 3-2-1, idee, silence gene, fin...), vos propres clips, et des clips libres trouves sur Wikimedia Commons, Pixabay ou Pexels (cle gratuite dans le coffre du systeme) ; credit ajoute a la publication ; bibliotheque rangee dans le dossier de synchronisation.
- Goodies dessines et animes pour les packs Balade, Route, Fete, Maison et Commerce (montagne, sentier, profil, meteo, thermometre, compteur, compte a rebours, calendrier, ruban, panneau, etiquette de prix, pastille).
- Accueil : les projets ouverts sur vos autres postes apparaissent en gris ; double-clic pour les retrouver et les ouvrir ici.
- Catalogue d'effets en ligne rempli : 25 effets FFmpeg et 14 effets IA, mis a jour sans reinstaller.

## Nouveautes de 0.7.0

### 0.6 et 0.7 : IA creative sur ce poste (gratuite, rien n'est envoye)
- Montage > Atelier IA : image du film retouchee par une phrase (personnage 3D, anime, bande dessinee, aquarelle, peinture, croquis, neon, figurine, affiche), phrases modifiables et "mes effets".
- Logo, mascotte, embleme, fond d'intro et miniature YouTube par IA.
- Effets IA sur la partie en jaune : dessin anime (AnimeGANv3, ou OpenCV sans modele), flou d'arriere-plan, agrandissement Real-ESRGAN, ralenti fluide RIFE ; photo 3D ; transition 3D entre deux plans ; animer une image avec Wan 2.2 (experimental, carte graphique).
- Musique creee par IA selon un style (ACE-Step 1.5), a la duree du montage ; la Proposition l'utilise quand le modele est installe.
- Moteurs et modeles telecharges en cochant (Preferences > IA locale), mis a jour par la veille hebdomadaire.

### 0.5.2 : transitions automatiques
- Montage > Transitions automatiques : a chaque raccord, selon le mouvement de la camera, la ressemblance des images et les temps forts de la musique (styles Punchy, Clean, Cinema), liste cochable, annulable d'un coup.

### 0.5.1 : textes, transitions et logos modernes
- Outil Texte > Style moderne (dont deux "bas de l'ecran") ; huit transitions modernes ; gabarits de logo modernes.

### 0.5.0 : intros modernes et vignette du fichier
- Fabrique : dix intros en trois familles avec vignettes animees calculees avec votre texte ; fond "premieres images du film floutees" ; polices Poppins, Bebas Neue, Anton.
- Titre d'ouverture pose sur le film par l'assistant.
- Vignette du fichier choisie dans le film (integree au MP4 et JPG pour YouTube).
- Exemples et textes neutres partout.
