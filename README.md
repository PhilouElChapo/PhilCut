# PhilCut

Montage vidéo libre pour Windows et Linux : simple, efficace, « effet wahou ». Bande vidéo, bande son, et à partir de là on coupe, on insère, on rajoute. Un assistant analyse les rushes et propose un montage complet (logo, musique, plans, textes, effets, Goodies) que l'on accepte élément par élément. Vos rushes restent où ils sont ; rien n'est envoyé à une IA sans votre clic.

**Licence : GNU GPL v3** (voir [LICENSE](LICENSE)). PhilCut est fourni sans aucune garantie.

## Télécharger

Dernière version : [Releases](https://github.com/PhilouElChapo/PhilCut/releases/latest)

- Windows : `PhilCut_portable.zip` (à décompresser, aucune trace sur le PC — la version de test) ou `PhilCut_Setup.exe` (installation sans droits administrateur). FFmpeg est embarqué.
- Linux : `PhilCut_linux_x86_64.tar.gz` (FFmpeg du système : `sudo apt install ffmpeg`). Flatpak à venir.
- Depuis les sources : `lancer.bat` (Windows) ou `./lancer.sh` (Linux), avec Python 3.10+ et FFmpeg dans le PATH.

## Ce que fait la première version

- Import de rushes (téléphone, GoPro, lunettes), proxys légers en tâche de fond, rotation et cadence variable corrigées, HDR ramené en SDR.
- Timeline : couper (C), supprimer, déplacer, rogner aux bords, vitesse et speed ramp, cadrage (remplir, bandes, fond flou), aimant, zoom.
- Aperçu en temps réel sur les proxys, titres et Goodies dessinés par-dessus ; « Aperçu rendu » pour juger les effets.
- Effets : looks (ciel et altitude, nuit chaude, cinéma, Y2K…), glow, glitch, double exposition, fond vert, flou de mouvement, ralenti fluide, stabilisation, feu d'artifice, éclairs, fuites de lumière, pluie de code et étalonnage Matrix, bullet time ; transitions fondu, flash, puzzle, explosion, glitch, zoom, balayage, dissolution en code.
- Textes animés (fondu, zoom, glissé, machine à écrire, néon, feu, tournoyant, mots au rythme) et étiquettes accrochées à une personne (suivi OpenCV).
- Goodies : altimètre, anémomètre, cap, horizon, variomètre, chrono, horloge, boussole, badges… valeurs saisies ou tirées d'une trace GPX.
- Tout ce qui est posé se voit et se reprend : image fidèle à l'arrêt (effets, transitions, textes, Goodies rendus en moins d'une seconde), étiquettes d'effets et blocs de transition cliquables sur la timeline, Inspecteur à droite avec réglages en direct, Actif et Supprimer sur chaque élément, Centre d'activité et barre d'information en bas.
- Zones tracées dans l'image (0.3.3) : flou, mosaïque, cache de couleur, assombrir, éclaircir, noir et blanc, rectangle ou ovale ; la zone peut suivre ce qu'elle couvre (analyse de l'image image par image, correction à n'importe quel instant). Poignées dans l'aperçu pour déplacer et redimensionner textes, Goodies et zones. Catalogue des effets à vignettes animées sur votre plan, à glisser-déposer sur la timeline.
- Timeline complète (0.3.4) : plans glissés d'une piste à l'autre, effets copiés / collés, effet sur une partie du plan avec bornes tirables, images clefs (incrustation, texte, Goodie qui bouge, grossit ou s'efface), losanges cliquables.
- Aviation (0.4.0) : tableau de bord de vol fabriqué à partir d'un profil réglable (altitudes, vitesse, durées des phases, caps), carte animée du trajet et mini-carte (aérodromes ou coordonnées), manche à air, sous-titres des échanges radio reconnus à leur phraséologie.
- 0.5.2 : textes animés modernes (titres, bas de l'écran), huit transitions modernes, gabarits de logo modernes ; transitions automatiques choisies à chaque raccord selon le mouvement de la caméra, la ressemblance des images et les temps forts de la musique.
- 0.5.0 : intros et logos animés modernes en trois familles (Punchy, Clean minimal, Cinéma), courbes de mouvement, polices actuelles, fonds vivants ou premières images du film floutées, vignettes animées calculées avec votre texte ; titre d'ouverture posé sur le film ; vignette du fichier (image intégrée au MP4 et JPG pour YouTube).
- 0.4.4 : musique retravaillée dans l'Inspecteur (début dans le morceau, fondus dessinés, couper à la fin de la vidéo), téléchargements en pause et repris à la session suivante, Mes musiques classées par dossier, album ou artiste, « Dites-le en clair » (une phrase devient des actions de montage, montrées puis faites d'un coup), flèches courbes à contour et titres bandeau façon miniature qui se déplacent et tournent avec les images clefs, voix studio (débruitage RNNoise local, présence, niveau régulier).
- Effets (0.4.1) : tremblement, zoom lent (Ken Burns), cadre photo, look par fichier LUT, avant / après ; transitions choc, rotation, filé ; image figée avec légende ; bruitages synthétisés sur le poste ; autocollants (polaroïd, post-it, flèche).
- Assistant de montage à trois niveaux : recettes sans IA (gratuit), IA locale 100 % portable (moteurs llama.cpp et whisper.cpp et modèles rangés dans le dossier de PhilCut, lancés seulement à la demande, en priorité basse ; testée et mesurée sur le poste), IA cloud (Claude ou Gemini avec votre clef). Volet Proposition avec cases à cocher et « autre idée ».
- Voix : voix off au micro sur une piste Voix (la musique baisse toute seule), retouches non destructives (voix harmonieuse, « s » adoucis, moins nasale, timbre, radio), voix de synthèse locale (Piper, portable) ou Gemini en option, doublage dans une autre langue (écoute et voix sur le poste, traduction locale ou Claude/Gemini), sous-titres karaoké mot à mot ; filtre de narration (débruitage, égalisation, compression, de-esser), écoute avant / après avant de poser la prise, autotune (justesse corrigée note par note, tonalité et force au choix).
- Fabrique : logos et intros animés (tracé, particules, code, éclat, lucioles, carnet, glitch, rotation) ; plans générés par IA via Flow (abonnement, dossier surveillé) ou Veo (API, prix affiché).
- Son : musique avec baisse automatique sous la voix, débruitage, voix embellie, réverbération, écho, normalisation YouTube ; sous-titres .srt ou Whisper local (pack).
- Export YouTube, Insta, WhatsApp, écran LED, avec l'encodeur de la carte (NVENC, QuickSync, AMF, VA-API) ou x264.
- Repris de PhilPDF : Préférences, barre d'outils personnalisable, volets repliables, comptes (Drives, NAS, FTP), synchronisation des projets ouverts et des préférences entre postes, mises à jour proposées (jamais imposées), journaux depuis l'Aide, langues.

Le [guide de test](docs/guideline-tests.md) liste, dans l'ordre, ce qui est à vérifier sur la première portable.

## Participer

- Un problème, une idée : ouvrez un ticket (*Issues*).
- Une correction : proposez-la (*Pull request*). Seule la version publiée ici est distribuée par la mise à jour automatique.
- Les moteurs open source embarqués sont surveillés chaque semaine (`veille_moteurs.yml`) : nouvelle version → recompilation, tests, publication.

## Composants

FFmpeg (GPL, build BtbN), Qt / PySide6 (LGPL), OpenCV (Apache 2.0), NumPy (BSD), Pillow (MIT-CMU), polices Nunito, Anton, Poppins et Bebas Neue (SIL OFL), modèles RNNoise de rnnoise-models (G. Richards, hors droit d'auteur selon leur auteur). Packs optionnels : rembg + onnxruntime (détourage), faster-whisper (sous-titres).
