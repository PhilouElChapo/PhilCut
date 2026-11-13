PhilCut pour Windows, tout en un (Python, Qt, OpenCV et FFmpeg embarques).
- PhilCut_portable.zip : a decompresser, aucune trace sur le PC (c'est la version de test).
- PhilCut_Setup.exe : installation sans droits administrateur.
Linux : PhilCut_linux_x86_64.tar.gz (FFmpeg du systeme : paquet ffmpeg). Flatpak a venir.
Guide de test : docs/guideline-tests.md

## Nouveautes de 0.9.63 (comprend tout ce qui est sorti depuis la 0.4.4)

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
