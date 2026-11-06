PhilCut pour Windows, tout en un (Python, Qt, OpenCV et FFmpeg embarques).
- PhilCut_portable.zip : a decompresser, aucune trace sur le PC (c'est la version de test).
- PhilCut_Setup.exe : installation sans droits administrateur.
Linux : PhilCut_linux_x86_64.tar.gz (FFmpeg du systeme : paquet ffmpeg). Flatpak a venir.
Guide de test : docs/guideline-tests.md

## Nouveautes de 0.7.0 (comprend tout ce qui est sorti depuis la 0.4.4)

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
