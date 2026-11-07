PhilCut pour Windows, tout en un (Python, Qt, OpenCV et FFmpeg embarques).
- PhilCut_portable.zip : a decompresser, aucune trace sur le PC (c'est la version de test).
- PhilCut_Setup.exe : installation sans droits administrateur.
Linux : PhilCut_linux_x86_64.tar.gz (FFmpeg du systeme : paquet ffmpeg). Flatpak a venir.
Guide de test : docs/guideline-tests.md

## Nouveautes de 0.9.7 (comprend tout ce qui est sorti depuis la 0.4.4)

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
