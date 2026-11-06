PhilCut pour Windows, tout en un (Python, Qt, OpenCV et FFmpeg embarques).
- PhilCut_portable.zip : a decompresser, aucune trace sur le PC (c'est la version de test).
- PhilCut_Setup.exe : installation sans droits administrateur.
Linux : PhilCut_linux_x86_64.tar.gz (FFmpeg du systeme : paquet ffmpeg). Flatpak a venir.
Guide de test : docs/guideline-tests.md

## Nouveautes de 0.8.7 (comprend tout ce qui est sorti depuis la 0.4.4)

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
