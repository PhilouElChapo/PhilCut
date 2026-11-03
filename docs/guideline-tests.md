# PhilCut — guideline de test de la première version (0.1.x)

Ce document est la feuille de route des tests. On s'y tient : chaque point est testé dans l'ordre, sur la **version portable Windows** (poste Nvidia), avec les vidéos de référence. Pour chaque point, noter : **OK**, **KO** (avec ce qui s'est passé) ou **à revoir** (ça marche mais ce n'est pas ce qu'on voulait). Les remarques se font dans la conversation du projet « Programmation » ou dans un ticket GitHub, en citant le numéro du point (ex. « T3.4 KO »).

## Vidéos de référence

| Code | Fichier | Rôle |
|---|---|---|
| **AV1** | rush hangar (1000037802.mp4, 15 s, vertical, S24) | base de travail : import, rotation, cadence variable, étiquette sur l'avion |
| **AV2** | montage CapCut aviation (1 min 16, vertical) | référence du « wahou » : ce que PhilCut doit savoir refaire |
| **SV1, SV2** | Saint-Vallier de nuit (14 juin, 1 min 19 et 1 min 37) | test de l'assistant sur une « visite / ambiance » ; nuit, passages noirs |
| **SV3** | Saint-Vallier crépuscule (21 juin, 6 s, vertical) | avant / après |
| **TER** | terrasse Vidma (11 s, 1952×1080, muet) | clip IA : taille hors norme, piste son vide |
| **JUGE** | la vidéo que Claude ne connaît pas | validation finale à l'aveugle, en dernier |

Avant de commencer : copier ces fichiers dans un dossier `PhilCut-tests` sur le PC. Ne pas les renommer pendant les tests (on vérifie aussi la reconnaissance des rushes déplacés, au point T9).

## T1 — Installation et démarrage (portable)

1. Décompresser `PhilCut_portable.zip`, lancer `PhilCut.exe`. **Attendu** : la fenêtre s'ouvre en thème sombre, aucune fenêtre bloquante sauf l'assistant de bienvenue (une fois).
2. Bienvenue : langue, nom, poste, emplacement de synchronisation (Drive). Valider. **Attendu** : plus jamais redemandé ; modifiable dans Edition › Préférences.
3. Vérifier que rien n'est écrit ailleurs : un dossier `donnees` à côté de l'exe, rien dans `%APPDATA%\PhilCut`.
4. Barre d'état : « PhilCut 0.1.x · version portable · FFmpeg … ». **Attendu** : FFmpeg trouvé (embarqué dans `bin`).
5. Aide › A propos, Aide › Raccourcis, Outils › Journal des échanges : s'ouvrent.
6. Fermer et relancer : l'Accueil se souvient (pas de bienvenue, projets récents vides).

## T2 — Import et bibliothèque

1. Accueil › **Nouveau projet 16:9**. Importer **AV1** (bouton Importer ou glisser sur la fenêtre). **Attendu** : encart de progression en bas (import, proxy), vignette dans la bibliothèque, plan posé automatiquement dans la timeline, image **droite** (pas couchée) dans l'aperçu.
2. Clic droit sur AV1 › **Fiche vidéo**. **Attendu** : 1920×1080 vertical, rotation 90°, cadence ≈ 30 i/s *variable*, appareil Samsung, date 1er juin 2025, son présent.
3. Importer **TER**. **Attendu** : fiche « sans son » (piste muette détectée), 1952×1080.
4. Importer une musique (mp3). **Attendu** : icône musique, glisser-déposer sur la bande « Son » la pose où on la lâche.
5. Importer une photo (jpg). **Attendu** : posée comme plan de 5 s.
6. Glisser une vidéo directement sur la timeline depuis l'explorateur Windows. **Attendu** : importée et posée à l'endroit lâché.
7. Retirer un média utilisé : question de confirmation, puis ses plans disparaissent.

## T3 — Timeline et aperçu

1. Espace : lecture ; l'image suit le curseur ; le son est là. Espace : pause. **Noter** la fluidité (proxy 540p).
2. Cliquer dans la règle, glisser le curseur : l'aperçu suit.
3. **C** au milieu d'un plan : deux plans. Sélectionner le second, **Suppr** : il disparaît et le suivant se recolle. **Maj+Suppr** : laisse un trou (noir à l'aperçu). Edition › Resserrer : le trou disparaît.
4. Tirer le bord droit d'un plan vers la gauche : il se raccourcit, l'aperçu montre la dernière image pendant le tirage. Tirer le bord gauche. Glisser un plan : il ne chevauche jamais son voisin (il le pousse).
5. **Aimant** : en déplaçant un plan près du bord d'un autre ou du curseur, il « colle ». Désactiver : plus de collage.
6. Ctrl+molette : zoom ; bouton « Tout voir » ; ← → image par image ; Origine / Fin.
7. Ctrl+Z / Ctrl+Y après chaque opération ci-dessus. **Attendu** : tout est annulable, plusieurs niveaux.
8. Clic droit sur un plan : Vitesse ×0,5 (le plan s'allonge), ×2 (raccourcit), Cadrage « contenir, fond flou » sur AV1 dans un projet 16:9 (fond flou visible à l'aperçu et à l'export), Muet.
9. Outil **Vitesse** › « Speed ramp » : le plan se coupe en trois (lent, rapide, lent).
10. Double-clic sur un plan : fenêtre Effets. Poser **Glow** puis **Transition Puzzle** sur le deuxième plan. L'aperçu ne montre PAS le glow (normal : « Aperçu rendu » pour ça). Le nom du plan affiche ✦ et ⇥.
11. Bouton **Aperçu rendu** : au bout de quelques secondes, bouton « Ouvrir » ; le clip de 10 s montre le glow et le puzzle.

## T4 — Textes, étiquettes, Goodies

1. Outil **Texte** : « Survol de Cannes », animation Néon, 0,5 → 3 s. **Attendu** : visible à l'aperçu, barre rose dans la bande Titres, déplaçable à la souris ; double-clic pour modifier.
2. Essayer chaque animation (fondu, zoom, glissé, machine à écrire, néon, feu, tournoyant, mots au rythme) sur un Aperçu rendu. **Noter** celles à retravailler.
3. Etiquette accrochée : Texte › Style « Etiquette », « Suivre le visage dans AV1 » (disponible après l'analyse de l'assistant, T5). **Attendu** : encart « Suivi de la personne », puis l'étiquette suit la personne à l'aperçu et à l'export.
4. Outil **Goodies** : Altimètre, valeurs `0 0` et `10 2500`, cadran. **Attendu** : cadre à l'aperçu, cadran dessiné (aiguille qui monte) à l'export. Essayer Horloge, Compas, Horizon, Immatriculation (texte « F-GDLJ »), style HUD.
5. Goodie › **Depuis une trace GPX** (si vous avez un GPX du S24 ou de la GoPro). **Attendu** : valeurs remplies.

## T5 — Assistant de montage

1. Nouveau projet, importer **SV1, SV2, SV3** (rien d'autre). Volet Proposition : niveau **Recettes sans IA**, indications vides, « Analyser et proposer ». **Attendu** : encart d'analyse (fiche de chaque rush), puis une recette de type **Visite / ambiance d'un lieu**, format 16:9 ou 9:16 selon les rushes, plans qui évitent les passages noirs, look « nuit chaude », texte d'ouverture, écran de fin, Goodie horloge.
2. Comparer avec la recette proposée par Claude le 30 octobre (section 13.6 du cahier des charges). **Noter** les écarts.
3. Décocher un plan et un Goodie, « autre idée » sur le logo et sur un texte, puis **Appliquer (remplace la timeline)**. **Attendu** : timeline remplie, musique sous la vidéo si une musique est importée, titres placés, durée annoncée respectée à peu près.
4. Exporter en WhatsApp (rapide) et juger : rythme, coupes, lisibilité des textes, look de nuit (éclairci, débruité).
5. Refaire avec **AV1 + TER + une musique** et l'indication « vol avion ». **Attendu** : type **Vol**, look ciel et altitude, étiquette « le Pilote » si un visage est vu, Goodies altimètre et anémomètre, plan à générer (intro) proposé.
6. Niveau **IA cloud** (clef Gemini puis clef Claude dans Préférences › Assistant et IA) : même projet. **Attendu** : rappel « données sensibles ? » puis recette plus « inspirée » ; la source est affichée (cloud:Gemini / cloud:Claude). **Noter** le temps et le coût constaté (console Google / Anthropic).
7. Niveau **IA locale** : Préférences › Assistant et IA › « Tester l'IA locale ». Sans Ollama : message clair qui dit quoi installer. Avec Ollama + modèle : temps estimé et qualité annoncés, puis une recette.
8. « Autre idée » en IA cloud : un seul élément change.

## T6 — Fabrique

1. Fabrique › Logo : texte « Phil Aviation », animation **Code Matrix**, 2,5 s, « Au début ». **Attendu** : clip fabriqué, posé en tête, tout le reste décalé. Essayer Tracé, Particules, Eclat, Lucioles, Carnet, Glitch, Rotation ; avec une image PNG de logo.
2. Fabrique › Plan généré › **Flow** : sujet, style, « Rédiger la consigne », Fabriquer. **Attendu** : consigne dans le presse-papiers, Flow ouvert ; après génération et téléchargement du clip, PhilCut l'importe tout seul (dossier surveillé = Téléchargements).
3. **Veo** (seulement si « Autoriser Veo » est coché) : prix annoncé, confirmation, clip importé. **Noter** le coût réel.

## T7 — Son et sous-titres

1. Musique importée sous une vidéo avec voix : à l'export, la musique baisse sous la voix (ducking) et le niveau global est normalisé (pas de saturation, contrairement à AV2).
2. Outil **Voix et son** sur un plan : Débruiter, Voix embellie, Réverbération, Echo, volume, muet ; juger à l'export.
3. Sous-titres : importer un .srt → rendus à l'export et écrits en .srt à côté si coché. Whisper : cocher le pack (depuis les sources seulement pour l'instant), transcrire AV1.

## T8 — Export

1. Exporter le projet aviation en **YouTube** (16:9) : encodeur Nvidia NVENC proposé par défaut ; durée de l'export ; le fichier se lit dans VLC et dans le lecteur Windows ; poids raisonnable.
2. Exporter le même en **Insta 9:16** (changer le format du projet via une recette 9:16 ou un nouveau projet) : plans horizontaux avec fond flou.
3. **WhatsApp** et **Ecran LED vertical** : poids et définition conformes.
4. Faire échouer volontairement NVENC (encodeur absent sur un autre poste) : PhilCut retombe sur x264 et le note dans le journal.
5. « Déposer sur le Drive » après export : le fichier arrive dans `PhilCut/Exports` de l'emplacement de synchro.

## T9 — Projets, synchro, préférences, mises à jour

1. Enregistrer (Ctrl+S) : fichier `.philcut` + vignette ; il apparaît dans les projets récents de l'Accueil avec la date.
2. Fermer PhilCut, déplacer le dossier des rushes, rouvrir le projet : les rushes sont retrouvés par leur empreinte ou signalés « introuvables » sans planter ; proxys refaits en arrière-plan.
3. Sur le **deuxième poste** (même emplacement de synchro) : l'Accueil propose « Sur « pharmacie », 1 projet était ouvert : … Reprendre ».
4. Préférences : chaque onglet s'ouvre ; changer thème clair → demande de relance ; barre personnalisée (clic droit : icône seule / nom seul / taille ; Personnaliser : ordre, séparateurs) ; volet complet → icônes → masqué (F4) ; export / import des préférences (avec et sans phrase secrète).
5. Mises à jour : Aide › Vérifier. Quand une 0.1.(x+1) est publiée par GitHub, la proposition apparaît sur l'Accueil ; téléchargement, puis installation seulement après confirmation.
6. Packs : cocher « Détourage » (depuis les sources : pip l'installe) ; effet Halo possible ensuite.

## T10 — Le JUGE (validation à l'aveugle)

1. Nouveau projet, importer uniquement la vidéo **JUGE**, aucune indication, niveau Recettes sans IA → Analyser. Appliquer, exporter.
2. Même chose en IA cloud.
3. Verdict de Philippe, en trois lignes : la recette était-elle celle qu'il aurait voulue ? Qu'est-ce qui manquait ? Qu'est-ce qui était de trop ?
4. Les écarts sont reportés dans les recettes (`app/recettes.py`) et dans les consignes de l'IA (`app/assistant.py`), puis on refait T10.

## Ce qui n'est pas encore dans la 0.1 (ne pas tester)

- Flatpak Linux (archive tar.gz seulement), version Android.
- Recadrage automatique par suivi de personne (l'étiquette accrochée existe, pas encore le recadrage).
- Effets sur personne (halo, feu d'artifice derrière, personne en code) dans la version tout-en-un : ils demandent le pack « Détourage », installable depuis les sources pour l'instant.
- Vrai autotune de chant (une approximation est posée), bibliothèque musicale libre en ligne (lien vers Free Music Archive en attendant), catalogue d'effets en ligne (le mécanisme est là, le fichier est vide).
- Packs de Goodies autres qu'Aviation et Maison : les genres existent, le dessin détaillé viendra.

## Comment remonter un KO utile

- Le numéro du point (ex. **T3.4**), ce que vous avez fait, ce qui s'est passé, ce que vous attendiez.
- Le fichier concerné (AV1, SV2…) et, si c'est un export, la vidéo obtenue.
- Outils › Journal des échanges : copier les dernières lignes s'il y a une erreur d'IA, de Drive ou d'export.
