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
- Assistant de montage à trois niveaux : recettes sans IA (gratuit), IA locale 100 % portable (moteurs llama.cpp et whisper.cpp et modèles rangés dans le dossier de PhilCut, lancés seulement à la demande, en priorité basse ; testée et mesurée sur le poste), IA cloud (Claude ou Gemini avec votre clef). Volet Proposition avec cases à cocher et « autre idée ».
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

FFmpeg (GPL, build BtbN), Qt / PySide6 (LGPL), OpenCV (Apache 2.0), NumPy (BSD), Pillow (MIT-CMU), police Nunito (SIL OFL). Packs optionnels : rembg + onnxruntime (détourage), faster-whisper (sous-titres).
