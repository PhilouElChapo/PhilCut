# PhilCut — guideline de test (versions 0.1.x et 0.2.x)

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
7. Niveau **IA locale** (sur le mini PC du travail et sur le PC Nvidia) : Préférences › **IA locale**. **Attendu** : rien n'est installé avant de cocher ; le modèle conseillé pour ce poste porte une étoile ; tailles affichées. Cocher « Vision légère » : confirmation avec la taille totale, téléchargement dans l'encart (relancer après une coupure : il reprend). Puis « Tester l'IA locale maintenant » : temps estimé et qualité annoncés. Pendant le test et pendant une recette, **ouvrir le Gestionnaire des tâches** : `llama-server` apparaît en priorité basse, sur la moitié des cœurs en mode poste léger, et **disparaît à la fin**. Le poste reste utilisable. Vérifier qu'aucune entrée n'est ajoutée au démarrage de Windows. Décocher : la place est libérée (dossier `donnees\ia` de la portable).
8. « Autre idée » en IA cloud : un seul élément change.

## T6 — Fabrique

1. Fabrique › Logo : texte « Phil Aviation », animation **Code Matrix**, 2,5 s, « Au début ». **Attendu** : clip fabriqué, posé en tête, tout le reste décalé. Essayer Tracé, Particules, Eclat, Lucioles, Carnet, Glitch, Rotation ; avec une image PNG de logo.
2. Fabrique › Plan généré › **Flow** : sujet, style, « Rédiger la consigne », Fabriquer. **Attendu** : consigne dans le presse-papiers, Flow ouvert ; après génération et téléchargement du clip, PhilCut l'importe tout seul (dossier surveillé = Téléchargements).
3. **Veo** (seulement si « Autoriser Veo » est coché) : prix annoncé, confirmation, clip importé. **Noter** le coût réel.

## T7 — Son et sous-titres

1. Musique importée sous une vidéo avec voix : à l'export, la musique baisse sous la voix (ducking) et le niveau global est normalisé (pas de saturation, contrairement à AV2).
2. Outil **Voix et son** sur un plan : Débruiter, Voix embellie, Réverbération, Echo, volume, muet ; juger à l'export.
3. Sous-titres : importer un .srt → rendus à l'export et écrits en .srt à côté si coché. Whisper (0.2) : Préférences › IA locale, cocher « Voix légère » ou « Voix standard », puis transcrire AV1 : sous-titres en français, sans rien installer sur le poste.

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
6. Packs (0.2) : Préférences › IA locale, cocher « Détourage léger » (5 Mo) puis « Détourage précis » ; effet Halo et feu d'artifice derrière la personne possibles ensuite, depuis la version portable.
7. Clefs IA (0.2) : saisir les clefs Claude et Gemini, fermer PhilCut, ouvrir `donnees\parametres.json` de la portable avec le Bloc-notes : **aucune clef n'y figure**. Rouvrir PhilCut : les clefs sont toujours là (coffre de Windows). Une 0.1 qui avait des clefs en clair : elles disparaissent du fichier au premier démarrage de la 0.2, sans être perdues.
8. Comptes (0.2) : relier Google Drive, OneDrive et Dropbox : la page de connexion affiche « PhilCut » (et non PhilPDF), puis le compte apparaît dans PhilCut.

## T11 — Suivi d'une personne et recadrage (0.2)

1. Projet **16:9**, importer **AV1** (vertical). Clic droit sur le plan › Cadrage › **Suivre la personne (recadrage automatique)…**. **Attendu** : l'image du plan, les personnes trouvées encadrées et numérotées ; un clic en choisit une (cadre vert). Essayer aussi de **tracer un cadre** à la souris autour de l'avion F-GDLJ.
2. Zoom 1,0 et mouvement « Normal », OK : l'encart montre le suivi, puis l'aperçu montre un plan **horizontal qui suit la personne** (ou l'avion). Lire le plan : le cadre bouge sans trembler. Essayer « Doux (cinéma) » et « Réactif », et un zoom de 1,5.
3. Exporter en YouTube : même cadrage que dans l'aperçu.
4. L'inverse : projet **9:16** avec un plan horizontal (SV1) : le cadre vertical suit la personne qui marche.
5. Texte « le Pilote » posé sur le plan, clic droit sur le texte dans la timeline › **Accrocher à une personne…** : le texte suit la tête. « Décrocher » le remet à sa place fixe.
6. Goodie (altimètre) : même manipulation, le Goodie suit l'avion. Export : identique à l'aperçu.
7. Cas difficile : la personne passe derrière l'aile ou sort du cadre. **Noter** si le suivi la retrouve ensuite ou s'il reste figé (on réglera la reprise d'après vos essais).

## T12 — IA locale sur le portable Nvidia (0.2)

1. Préférences › IA locale : la case **« Utiliser la carte graphique (Vulkan) : NVIDIA GeForce RTX 3070 Laptop GPU »** est cochée ; « Vision avancée » porte l'étoile « conseillé ici » (sinon « Vision standard »).
2. **Brancher le secteur**. Cocher le modèle conseillé : taille totale annoncée, téléchargement dans l'encart. Couper le Wi-Fi au milieu puis relancer : il reprend.
3. Tester l'IA locale : le résultat indique **« Calcul sur : carte graphique (NVIDIA…, Vulkan) »**, avec le temps par vidéo. Ouvrir le Gestionnaire des tâches › Performances : le **GPU 1 (Nvidia)** travaille pendant le test, pas seulement le GPU 0 (Intel).
4. Décocher « Utiliser la carte graphique » et refaire le test : « Calcul sur : processeur ». **Noter** les deux temps : c'est ce qui décidera si une option CUDA vaut la peine.
5. Assistant en niveau **IA locale** sur SV1 + SV2 : recette proposée, source « locale:… » affichée.
6. Fermer PhilCut : plus aucun `llama-server` dans le Gestionnaire des tâches. Supprimer le dossier de la portable : rien ne reste sur le poste (ni au démarrage de Windows, ni dans le registre).

## T13 — Nouveautés 0.2.1

1. **Fondu enchaîné** : deux plans, clic droit › Effets et transition sur le second, « Fondu enchaîné » 1 s. Export : les deux images se mélangent, la durée totale ne change pas. Essayer Cercle, Glissé, Pixels, Fondu flou, Diagonale, Dissolution.
2. **Rythme** : trois plans et une musique entraînante ; Montage › « Caler les coupes sur les temps de la musique ». **Attendu** : message « n coupe(s) calée(s) (xxx BPM) » ; à la lecture, les coupes tombent sur les temps. Refaire avec « débuts de mesure ». Une recette de l'assistant avec musique cale aussi ses coupes.
3. **Changer le fond** : Préférences › IA locale › « Détourage précis » coché. Sur un plan avec une personne : Effets › Personne › « Changer le fond » : fond = couleur, puis fond flouté, puis une image du projet ; « Bords adoucis » de 0 à 3. Export : la personne reste nette devant le nouveau fond.
4. **Image ou logo accroché** : Goodie › « Mes images · Image ou logo », choisir un PNG transparent ; puis clic droit › Accrocher à une personne : le logo la suit.
5. **Corriger le suivi** : sur un plan suivi où la personne se perd, placer la tête de lecture au moment de l'erreur, clic droit › Cadrage › « Corriger le suivi à la tête de lecture… », redésigner la personne : l'avant est gardé, l'après refait.
6. **Effets de texte** : Texte › Effet du texte : Contour épais, Ombre portée, Contour et ombre, Lueur, Relief, Couleur qui change ; couleur de l'effet ; police au choix. Export identique à l'aperçu rendu.
7. **Connecter une IA** : Assistant › Connecter une IA : pour chaque onglet, le bouton ouvre la bonne page, « Tester (gratuit) » valide ou refuse la clef. Coût estimé affiché avant l'envoi en IA cloud (case dans Préférences pour le masquer).
8. **Plan vidéo par IA** : Fabrique › Plan généré par IA › Générateur IA payant : Omni Flash 360p, prix annoncé, confirmation, clip importé. Avec une clef fal.ai : Kling 3.0 Pro ou Seedance 2.0 (prix plus élevé, annoncé avant).

## T14 — Nouveautés 0.2.2 (logo, publication, musique, voix)

1. **Atelier de logo** : Fabrique › Atelier de logo. Partir d'un gabarit, changer texte, police, couleurs, formes ; « Proposer avec l'IA » (Claude ou Gemini, coût affiché) donne trois pistes modifiables. Enregistrer : le logo est dans Mes images et s'accroche comme un goodie.
2. **Double export** : Exporter, cocher « Exporter aussi en » vertical (ou horizontal) : deux fichiers en une fois, le suivi de personne est gardé, sinon fond flou.
3. **Bibliothèque musicale** : Outils › Bibliothèque musicale : chercher « aventure », écouter, « Utiliser » : le morceau se pose sur la piste Musique, un fichier .credit.txt est écrit à côté.
4. **Publier** : après un export, « Publier… ». YouTube : relier le compte une fois (avertissement « application non validée » normal : Paramètres avancés › Accéder à PhilCut), titre, description avec le crédit musical, envoi. **Attendu** : la vidéo arrive en **privée** tant que Google n'a pas validé PhilCut. Instagram / TikTok : légende copiée et page ouverte.
5. **Voix off au micro** : curseur à 5 s, bouton Voix › « Enregistrer une voix off au micro… », casque sur les oreilles, « Faire défiler la vidéo » coché, parler 10 s, Arrêter. **Attendu** : un plan sur la piste **Voix** à 5 s ; à l'export la musique baisse pendant que vous parlez.
6. **Retouches de voix** : sélectionner ce plan, Voix : essayer Voix harmonieuse, Adoucir les « s », Moins nasale, Plus chaude, Plus claire, Timbre plus grave ou plus aigu, Effet radio. Rendu rapide pour écouter ; le fichier d'origine n'est jamais modifié.
7. **Voix de synthèse** : Préférences › IA locale › Voix de synthèse : cocher « Voix française, femme » (environ 60 Mo). Voix › « Voix off lue par une voix de synthèse… », taper deux phrases, Lire : le plan arrive sur la piste Voix, gratuit et hors ligne. Avec la clef Gemini : choisir une voix Gemini, le prix (quelques millièmes de $) est annoncé avant.
8. **Sous-titres karaoké** : un plan où l'on parle, Sous-titres › « Sous-titres karaoké » : chaque mot se colore en jaune au moment où il est dit (rendu rapide ou export).
9. **Doublage** : cocher aussi « English voice » et un modèle de vision (ou avoir une clef Claude/Gemini). Voix › « Doubler la vidéo dans une autre langue… », Anglais. **Attendu** : la voix d'origine baisse, la voix anglaise arrive sur la piste Voix, phrase par phrase au bon moment, sous-titres anglais ajoutés.

## T15 — Corrections 0.2.3 (retours du premier test)

1. **Préférences** : Edition › Préférences : **aucune fenêtre noire de console** ne s'ouvre. Aucun onglet ne défile de côté ; les textes longs passent à la ligne ; les boutons (« Connecter une IA », « Vérifier maintenant »…) sont à leur taille, à gauche.
2. **Téléchargement des packs** : sans projet ouvert, cocher une voix dans IA locale, OK : la progression s'affiche **en bas de la fenêtre**.
3. **Dossiers** : Importer et Exporter proposent d'abord le dossier **Vidéos** du système, puis le dernier dossier choisi.
4. **Volet** : le bouton Volet est à l'extrême droite de la barre ; 2e clic : une colonne d'icônes nommées (Proposition, Propriétés), un clic dessus rouvre le volet. Fiche vidéo a sa propre icône (i).
5. **Médias du projet** (ex-Bibliothèque) : une ligne explique à quoi sert la colonne.
6. **Timeline** : les images ne sont plus écrasées ; Alt + molette (ou Affichage › Images de la timeline plus grandes) les agrandit ; Ctrl + molette zoome dans le temps.
7. **Image affichée** : bouton image sous la vidéo : enregistre l'image du curseur en PNG pleine définition (dossier Images par défaut).
8. **Annuler / Rétablir** : la petite flèche à côté montre la liste (« Effets de … », « Coupe de … ») ; cliquer une ligne annule jusque-là.
9. **Partie de la vidéo** : curseur au début, touche I ; curseur à la fin, touche O : la partie est en jaune. Montage › « Supprimer la partie sélectionnée » ou « Garder seulement la partie sélectionnée ». Echap annule la sélection.
10. **Son** : bouton haut-parleur sous la vidéo : clic = tout couper ; flèche = choisir les pistes écoutées, « Ecouter seulement la voix off ». **La voix off s'entend maintenant à la lecture.**
11. **Effets** : cliquer sur un plan de la timeline (ou double-cliquer dessus), puis Effets. Cliquer un effet du catalogue : un aperçu de 2 à 3 s sur votre plan se fabrique et tourne en boucle à droite ; « Poser sur ce plan », régler, « Revoir avec les réglages », OK. Après OK, le plan porte ✦ et le bandeau du bas propose « Voir l'aperçu rendu » (la lecture normale ne montre pas les effets). Pour modifier ensuite : double-clic sur le plan, ou clic droit › Effets et transition. Une **transition** se pose sur le **2e plan** (celui qui arrive) : sur le premier plan, PhilCut l'explique.
12. **Micro** : Voix › Enregistrer : la barre « Niveau » bouge quand vous parlez (test du micro) ; après l'enregistrement, « Ecouter la prise » avant de la poser.
13. **Stabiliser** et **Fabrique** : un texte explique ce que fait l'outil avant de l'appliquer.

## T10 — Le JUGE (validation à l'aveugle)

1. Nouveau projet, importer uniquement la vidéo **JUGE**, aucune indication, niveau Recettes sans IA → Analyser. Appliquer, exporter.
2. Même chose en IA cloud.
3. Verdict de Philippe, en trois lignes : la recette était-elle celle qu'il aurait voulue ? Qu'est-ce qui manquait ? Qu'est-ce qui était de trop ?
4. Les écarts sont reportés dans les recettes (`app/recettes.py`) et dans les consignes de l'IA (`app/assistant.py`), puis on refait T10.

## Ce qui n'est pas encore là (ne pas tester)

- Flatpak Linux (archive tar.gz seulement), version Android.
- Correction du suivi à la main, plusieurs suivis dans un même plan, effet (halo, feu d'artifice) qui suit la personne : prévus dans une prochaine 0.2.x.
- Vrai autotune de chant (une approximation est posée), catalogue d'effets en ligne (le mécanisme est là, le fichier est vide).
- Doublage avec la voix de la personne elle-même (clonage de voix) : pas encore, la voix de synthèse est une voix toute faite.
- Packs de Goodies autres qu'Aviation et Maison : les genres existent, le dessin détaillé viendra.

## Comment remonter un KO utile

- Le numéro du point (ex. **T3.4**), ce que vous avez fait, ce qui s'est passé, ce que vous attendiez.
- Le fichier concerné (AV1, SV2…) et, si c'est un export, la vidéo obtenue.
- Outils › Journal des échanges : copier les dernières lignes s'il y a une erreur d'IA, de Drive ou d'export.
