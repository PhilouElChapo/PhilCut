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
6. Molette : zoom (Maj + molette : défiler) ; bouton « Tout voir » ; ← → image par image ; Origine / Fin.
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
5. **Corriger le suivi** : sur un plan suivi où la personne se perd, placer la ligne rouge au moment de l'erreur, clic droit › Cadrage › « Corriger le suivi à la ligne rouge… », redésigner la personne : l'avant est gardé, l'après refait.
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
2. **Téléchargements** : Préférences › IA locale, cocher deux modèles, OK : la fenêtre **Téléchargements** s'ouvre (taille, progression, état, vitesse, temps restant, file d'attente, bouton Arrêter). La fermer : les téléchargements continuent, le bouton « ⬇ Téléchargements : n — x % » en bas de la fenêtre (ou Outils › Téléchargements) la rouvre. Dans IA locale, un modèle en cours porte « ⬇ en cours de téléchargement ».
3. **Dossiers** : Importer et Exporter proposent d'abord le dossier **Vidéos** du système, puis le dernier dossier choisi.
4. **Volet** : le bouton Volet est à l'extrême droite de la barre ; 2e clic : une colonne d'icônes nommées (Proposition, Propriétés), un clic dessus rouvre le volet. Fiche vidéo a sa propre icône (i).
5. **Médias du projet** (ex-Bibliothèque) : une ligne explique à quoi sert la colonne.
6. **Timeline** : un rush court posé dans une timeline vide remplit la largeur (zoom automatique) ; clic droit dans la timeline › Zoom de la timeline (tout voir, agrandir, images plus grandes) ; les images ne sont plus écrasées ; Alt + molette (ou Affichage › Images de la timeline plus grandes) les agrandit ; la molette zoome dans le temps (rappel « Zoom » animé en haut à gauche).
7. **Image affichée** : clic droit sur la vidéo › « Enregistrer cette image », ou clic droit dans la timeline › « Enregistrer l'image à cet endroit », ou bouton image sous la vidéo : enregistre l'image du curseur en PNG pleine définition (dossier Images par défaut).
8. **Annuler / Rétablir** : la petite flèche à côté montre la liste (« Effets de … », « Coupe de … ») ; cliquer une ligne annule jusque-là.
9. **Partie de la vidéo, à la souris** : double-clic sur la règle des temps (au-dessus des pistes) au début voulu, puis double-clic à la fin : la partie est en jaune (ou boutons [ ] à côté de la tête rouge). Ou clic droit dans la timeline › Partie de la vidéo › « La partie commence ici », puis « La partie finit ici ». Clic droit sur la partie : effets sur cette partie, la supprimer, ou ne garder qu'elle. (Les touches I et O font la même chose, pour qui préfère le clavier.)
10. **Son** : bouton haut-parleur sous la vidéo : clic = tout couper ; flèche = choisir les pistes écoutées, « Ecouter seulement la voix off ». **La voix off s'entend maintenant à la lecture.**
11. **Effets** : cliquer sur un plan de la timeline (ou double-cliquer dessus), puis Effets. Cliquer un effet du catalogue : un aperçu de 2 à 3 s sur votre plan se fabrique et tourne en boucle à droite ; « Poser sur ce plan », régler, « Revoir avec les réglages », OK. Après OK, le plan porte ✦ et le bandeau du bas propose « Voir l'aperçu rendu » (la lecture normale ne montre pas les effets). Pour modifier ensuite : double-clic sur le plan, ou clic droit › Effets et transition. Une **transition** se pose sur le **2e plan** (celui qui arrive) : sur le premier plan, PhilCut l'explique.
11 bis. **Effet sur quelques secondes d'un long rush** : rush de 2 min ; double-clic sur la règle à 3 s puis à 8 s (partie en jaune) ; clic droit sur le plan › « Effets sur la partie en jaune seulement » (ou bouton Effets) : la fenêtre des effets s'ouvre ; les effets ajoutés ne couvrent que ces secondes (bande bleue, voir T20), le plan n'est pas coupé. « Couper ici » du clic droit coupe à l'endroit cliqué.
12. **Micro** : Voix › Enregistrer : la barre « Niveau » bouge quand vous parlez (test du micro) ; après l'enregistrement, « Ecouter la prise » avant de la poser.
13. **Stabiliser** et **Fabrique** : un texte explique ce que fait l'outil avant de l'appliquer.

## T50 — 0.9.32 : flou suivi et Google Flow

1. **Partie jaune** : faire une partie jaune sur la règle, ligne rouge au milieu, clic droit sur l'aperçu › « Tracer une zone à flouter… ». **Attendu** : la zone couvre exactement la partie jaune.
2. **Suivi dans les deux sens** : « Suivre ce qu'elle couvre ». **Attendu** : la zone suit la personne avant et après l'instant du tracé.
3. **Correction locale** : arrêter là où elle décroche, glisser la zone à sa place. **Attendu** : elle est corrigée à cet instant, le reste de la trajectoire ne bouge pas ; Maj + glisser déplace tout ; Ctrl+Z revient.
4. **Flow** : Fabrique › Plan généré par IA. **Attendu** : l'explication en 4 étapes ; « Fabriquer » ouvre Flow, la barre du bas montre l'attente et le temps écoulé ; après téléchargement, la fenêtre « Clip reçu de Flow » permet de regarder, insérer, garder ou jeter.

## T49 — 0.9.31 : retours du 8 novembre

1. **Durée des goodies** : poser un titre sur la piste du haut, tirer son bord droit puis gauche. **Attendu** : curseur ↔ au bord, durée affichée, minimum 0,2 s, Ctrl+Z revient.
2. **Modèles** : ouvrir Modèles de montage, « Ajouter des rushes… », puis « Monter avec ce modèle ». **Attendu** : le montage se fait sans double-clic.
3. **Étalonnage** : ouvrir sur un plan, lire l'explication du rideau, bouger « Image du plan ». **Attendu** : l'image change, jamais noire sans message.
4. **Pistes** : vignettes grandes, Ctrl + molette. **Attendu** : on atteint toutes les pistes ; ascenseur bien visible.
5. **Musiques** : un fichier « 17_Queen_-_Who_wants_to_live_forever.mp3 ». **Attendu** : artiste « Queen ».
6. **Attentes** : paroles IA, musique IA longue. **Attendu** : temps écoulé, temps restant, puis « Finition… » à 100 %.
7. **Voix** : « Essayer la voix » avec « Crooner ». **Attendu** : 15 s écoutables avant de créer.
8. **Style** : « Style « à la manière de »… », chercher Delon, double-clic. **Attendu** : la phrase reçoit « à la manière de Alain Delon ».
9. **Synchro** : cliquer sur le bouton ⇅ de la barre du bas. **Attendu** : liste des fichiers envoyés / reçus avec l'explication.
10. **Lecture** : un plan avec un effet, Espace. **Attendu** : l'effet se voit pendant la lecture.
11. **Journal** : Aide › Journal des échanges › Copier ; fenêtre de reprise › Copier.
12. **Tampons** : clic droit sur un tampon maison › Personnaliser, changer le texte. **Attendu** : aperçu en direct, la version rejoint la bibliothèque.

## T48 — 0.9.28 : étalonnage simple

1. **Ouvrir** : clic droit sur un plan › « Étalonnage (couleurs, avant / après)… ». **Attendu** : l'image du plan à la ligne rouge, rideau jaune AVANT / APRÈS que l'on fait glisser, trois roues, cinq curseurs.
2. **Roues** : pousser la pastille des tons moyens vers l'orange : l'image se réchauffe à droite du rideau ; double-clic : retour au neutre. Même chose pour ombres et hautes lumières.
3. **Auto** : sur un plan bleuté ou terne : la dominante disparaît, l'image reprend du contraste.
4. **Accorder** : deux plans de caméras différentes ; choisir l'autre plan, « Accorder sur ce plan » : lumière et couleurs se rapprochent.
5. **Copier** : « Copier sur les plans du même rush » : tous les morceaux du même rush prennent l'étalonnage.
6. **Appliquer** : l'aperçu à l'arrêt et l'export montrent le même résultat ; dans l'Inspecteur, l'effet « Étalonnage » ouvre la fenêtre ; Ctrl+Z revient.

## T47 — 0.9.27 : présentation de photos animée

1. **Fenêtre** : un projet avec 6 à 15 photos ; Montage › « Présentation de photos animée… ». **Attendu** : 10 animations depuis 0.9.29 (et les variantes du catalogue, ✦), chaque vignette bouge au survol ; le nombre de photos et la durée du clip sont affichés.
2. **Lancer de cartes** (fond « Table en bois »), « Fabriquer » : barre « Image 120 sur 600… », puis l'aperçu : les photos arrivent en tournoyant et s'empilent. « Poser à la ligne rouge » : le clip est inséré, la suite décalée ; Ctrl+Z revient.
3. **Explosion, puzzle, mur, carrousel, éventail, corde, pile, tourbillon, feuilles qui tombent (0.9.29)** : chacune fabriquée une fois, regardée ; photos verticales et horizontales mélangées bien cadrées.
4. **Ordre** : la case « Dans l'ordre de prise de vue » range les photos par date ; dans la bande, glisser une image change l'ordre, clic droit la retire (0.9.30).
4 bis. **Images d'une vidéo (0.9.30)** : ligne rouge sur un plan vidéo ; « + Dernière image du plan » ajoute sa dernière image ; « + Images d'une vidéo… » : planche d'images du plan, « Répartir sur tout le plan » avec 6, « Ajouter les images cochées ». Posée, la présentation enchaîne exactement sur la dernière image du plan.
5. **Modèles à photos** : Modèles de montage › « Photos : mur de souvenirs » : le montage devient la présentation, avec la musique du projet et le titre.
6. **Catalogue** : Aide › Nouveautés : « Confettis de photos », « Grand puzzle », « Diaporama » mis à jour.

## T46 — 0.9.26 : nouveautés du catalogue

1. **Au démarrage** : la barre du bas dit « ✦ 26 nouveauté(s) dans le catalogue : Aide › Nouveautés du catalogue ».
2. **Fenêtre** : Aide › « Nouveautés du catalogue… » : Goodies, modèles, styles, tampons IA, ✦ devant ce qui n'a pas été vu. « Vérifier maintenant » : « Catalogue à jour » ou le nombre d'arrivées. Double-clic sur un Goodie : la galerie s'ouvre ; sur un modèle : les modèles de montage.
3. **Goodies** : galerie des Goodies, familles « Réactions » et « Météo et nature » : cœur qui bat, pouce qui apparaît, étoile et soleil qui tournent, nuage qui flotte… Poser, lire, exporter : identiques.
4. **Modèles et styles** : « Récap de l'année » dans les modèles de montage (✦) ; dans l'Atelier IA, « un pilote à la Top Gun » donne la description du style.
5. **Tampons IA** : Montage › Tampons vidéo › Tampons IA : « Décollage d'avion », « Pause café », « À suivre… », « Flash météo ».
6. **Sans réseau** : la dernière copie reste utilisable.

## T45 — 0.9.25 : modèles de montage, exports en série

1. **Modèle** : nouveau projet, importer 4 à 10 rushes et une musique ; Montage › « Modèles de montage… » › « Short dynamique, 15 s » › « Monter avec ce modèle ». **Attendu** : barre d'analyse, puis un montage vertical d'environ 15 s, coupes très rapides sur les temps de la musique, transitions glitch et zoom, titre animé, écran de fin. Ctrl+Z revient au montage d'avant.
2. **Autres modèles** : refaire avec « Souvenirs de famille » puis « Bande-annonce cinéma » : rythme, transitions et look changent nettement. Modifier un plan ensuite : tout reste modifiable.
3. **Sans musique** : la fenêtre prévient que le montage n'en aura pas.
4. **Exports en série** : Fichier › Exporter, destination YouTube, cocher « Instagram / Reels », « Instagram carré » et « Ecran LED ». **Attendu** : quatre fichiers d'un coup (nom, nom_vertical, nom_carre, nom_ecran_led) ; une personne suivie reste cadrée dans chacun. A la fois suivante, les mêmes cases sont cochées.

## T44 — 0.9.24 : prolonger un plan trop court

1. **Image tenue** : clic droit sur un plan › « Prolonger ce plan… », 2 s, à la fin, « Image tenue », « Fabriquer ». **Attendu** : barre de progression, puis l'aperçu montre la dernière image avec un lent zoom et le son d'ambiance qui s'éteint ; rien n'est posé avant « Poser dans le film ». Après : le plan suivant, les textes et les sous-titres sont décalés de 2 s. Ctrl+Z revient.
2. **Ralenti** : même chose avec « Ralenti de la fin » : la dernière seconde ralentie en douceur, sans saccade.
3. **Au début** : « Au début du plan » : le morceau arrive avant le plan.
4. **IA** (avec un modèle vidéo installé) : « Prolongé par l'IA » : la scène continue (mouvement plausible) ; une à plusieurs minutes. Sans modèle, la ligne est grisée et dit quoi installer.

## T43 — 0.9.23 : monter par le texte

1. **Transcrire** : un projet avec un rush où l'on parle ; Montage › « Monter par le texte… » (Ctrl+T) › « Transcrire les rushes ». **Attendu** : barre de progression ; puis le texte s'affiche, un paragraphe par rush ou après une longue pause. Refermer et rouvrir : pas de nouvelle transcription (gardée dans le projet, aussi après Enregistrer et réouverture).
2. **Cliquer un mot** : la ligne rouge va à ce mot. Lire (Espace) : le mot entendu est surligné en jaune.
3. **Couper** : sélectionner une phrase à la souris, « ✂ Couper ce passage » (ou Suppr). **Attendu** : la phrase disparaît du texte et de la vidéo, la suite se recolle sans trou, la musique continue (case cochée). Ctrl+Z la remet.
4. **« euh » et silences** : le bouton dit combien il y en a ; un clic les enlève ; régler 1,5 s pour ne couper que les longues pauses.
5. **Garder seulement ce passage** : sélection, puis le bouton : il ne reste que ce passage.
6. **Chercher** : taper un mot, Entrée : il est sélectionné et la ligne rouge y va ; Entrée encore : l'occurrence suivante.

## T42 — 0.9.22 : sauvegarde automatique et récupération après plantage

1. **Copie automatique** : ouvrir un projet, poser un plan, attendre une minute. **Attendu** : « Sauvegarde automatique : 14h05 » dans la barre du bas ; votre fichier .philcut n'a pas changé (date de modification inchangée).
2. **Plantage simulé** : modifier le projet, attendre la copie, puis fermer PhilCut par le Gestionnaire des tâches (Fin de tâche). Relancer. **Attendu** : la fenêtre « Récupérer le travail » liste le projet (nom, il y a combien de temps, nombre de plans, emplacement) ; « Récupérer les projets cochés » le rouvre avec les modifications ; « Enregistrer » écrit à son emplacement d'origine.
3. **Plus tard / Jeter** : refaire le test, choisir « Plus tard » : la question revient au démarrage suivant ; « Jeter » : elle ne revient plus.
4. **Revenir à une version** : modifier plusieurs fois en attendant une minute entre chaque, puis Fichier › « Revenir à une sauvegarde automatique… ». **Attendu** : la liste des versions ; un double-clic y revient ; Ctrl+Z ramène l'état d'avant.
5. **Fermeture normale** : quitter en enregistrant (ou « Ne pas enregistrer ») : au démarrage suivant, aucune question.
6. **Réglages** : Préférences › Général › Sauvegarde automatique : 2 minutes, 10 versions, « Ouvrir le dossier des sauvegardes ».

## T41 — 0.9.21 : réplique dite avec le phrasé du style, mêlée au clip

1. **Réplique** : ligne rouge sur un plan ; Atelier IA › un effet vidéo (ex. « Dessin animé ») ; phrase « un gangster joué comme Alain Delon » ; « Réplique dite » : « Ici, c'est moi qui fais la loi. ». **Attendu** : « Phrasé : Froid, impassible, peu de mots (d'après « alain delon ») ». « ▶ Écouter la réplique » : la voix seule, lente, plate, grave.
2. **Changer la manière** : choisir « Gouailleur, rapide, charmeur », puis « Bande-annonce de film », réécouter. **Attendu** : débit, pauses, hauteur et grain changent nettement.
3. **Créer** : « Créer ». **Attendu** : le clip s'ouvre avec la voix dedans ; si la réplique est plus longue que le clip, la dernière image tient jusqu'à la fin de la phrase. « Refaire seulement la voix » (autre texte ou autre manière) garde l'image.
4. **Voix Gemini** : choisir « Voix Gemini ». **Attendu** : prix affiché et confirmation avant l'envoi ; la phrase est vraiment jouée (intonations).
5. **Récrire à sa manière** : « Récrire la réplique à sa manière (IA) » (locale ou cloud). **Attendu** : même sens, autres tournures ; aucune réplique de film connue.
6. **Reprendre** : clic droit sur le clip posé › « Modifier la création IA… ». **Attendu** : la réplique, la manière et le moteur reviennent.

## T40 — 0.9.20 : styles « à la manière de », dossier des créations

1. **Musique** : Atelier IA › Musique, phrase « une ballade chantée à la manière de Sinatra, musique façon Liza Minnelli ». **Attendu** : sous la phrase, en bleu, « 🎭 « sinatra » → smooth baritone crooner vocals… » et « liza minnelli » → Broadway cabaret… ; « Créer » : la ligne « Envoyé au moteur, en anglais » ne contient aucun nom. Écouter : voix de crooner, orchestre de cabaret.
2. **Vidéo ou image** : Atelier IA › Image, « un cow-boy à la John Wayne dans un look Star Wars » ; puis « un gangster joué comme Alain Delon ». **Attendu** : descriptions d'époque, de lumière, de costume et d'attitude ; aucun visage copié, aucun personnage ni logo.
3. **Nom inconnu** : « à la manière de » suivi d'un nom que PhilCut ne connaît pas. **Attendu** : « ❓ Style inconnu » et le bouton « Transposer ce style avec l'IA » (locale, ou cloud avec le coût affiché). Après la réponse, la description apparaît, et elle est dans Préférences › Assistant et IA › Styles (modifiable ; elle suit sur vos autres postes).
4. **Créations** : Préférences › Assistant et IA › « Créations de l'IA » : nombre et taille, « Ouvrir le dossier des créations », « Nettoyer maintenant », durée au choix. **Attendu** : ce qu'un projet récent ou ouvert utilise reste ; la barre du bas dit ce qui a été supprimé au démarrage (une fois par jour).

## T39 — 0.9.15 à 0.9.19 : écouter avant de poser, reprendre une création IA, enregistrer une copie

1. **Reprendre une musique IA** : Montage › Atelier IA › Musique, une phrase, des paroles, « Créer », écouter, « Poser sous la vidéo ». Puis clic droit sur ce morceau dans la timeline › « Modifier la création IA (phrase, paroles, durée)… ». **Attendu** : l'Atelier se rouvre sur le même effet, avec la même phrase, les mêmes paroles, la même voix, la même langue et la même durée. Changer une ligne des paroles, « Créer », écouter, « Remplacer le morceau d'origine ». **Attendu** : le morceau garde sa place dans le film ; Annuler (Ctrl+Z) remet l'ancienne version, qui reste dans les médias.
2. **Même chose depuis les médias** : clic droit sur la vignette du morceau dans les médias du projet › « Modifier la création IA… ». Un fichier qui ne vient pas de l'Atelier n'a pas cette ligne.
3. **Enregistrer une copie** : dans l'Atelier, après une création, « Enregistrer sous… » ; au clic droit d'un média, d'un plan de la timeline ou d'un tampon de la bibliothèque, « Enregistrer une copie sous… ». **Attendu** : la première fois, le dossier Musique (pour un son), Images (pour une image) ou Vidéos (pour un clip) du système ; la fois suivante, le dernier dossier choisi pour ce genre de fichier. Le fichier « .ia.json » à côté de la copie permet de la reprendre plus tard.
4. **Écouter avant de poser (0.9.16)** : une musique ou un clip créé n'est jamais posé tout seul : on l'écoute, « Début ici », « Fin ici », puis on choisit où le poser.
5. **Tampons IA (0.9.18)** : Montage › Tampons vidéo › Tampons IA : choisir un modèle (fusée, BOUM, robot…), le modifier, « Créer ce tampon ». **Attendu** : il arrive dans « Ma bibliothèque », avec image, mouvement, texte, bruitages et voix.
6. **Carte du trajet (0.9.18)** : Goodies › Aviation › Trajet : la carte OpenStreetMap se déplace à la souris, zoome à la molette ; un double-clic propose de garder le point dans « Mes points » ; la recherche trouve un aérodrome par code, nom ou ville après « Télécharger tous les aérodromes du monde ».

## T38 — 0.9.10 : la bibliothèque qui manque, synchronisation des réglages

1. **Musique IA (code 3221225781)** : Préférences › IA locale › « Tester ce modèle ». **Attendu** : le titre nomme le fichier qui manque (ex. « Il manque VCRUNTIME140_1.dll : Visual C++ de Microsoft ») et un seul bouton, le bon. Le bouton « pilote Nvidia » n'apparaît que si c'est nvcuda.dll qui manque.
2. **Synchronisation (Drive en direct, NAS, FTP)** : sur le PC A, changer un réglage commun (Préférences › Général, nom de la chaîne), OK, attendre une minute. Démarrer PhilCut sur le PC B. **Attendu** : la fenêtre « Synchronisation avec … » liste « Réglages » à recevoir ; après « Synchroniser la sélection », la barre du bas dit « ✓ … reçu(s), … envoyé(s). Réglages repris de « PC A » » et le réglage est là.
3. **Outils › Synchroniser maintenant** : même échange, à la demande.

## T37 — 0.9.9 : pannes de l'IA expliquées, tampons posés où l'on veut, recherche YouTube, zones des vignettes

1. **Test des modèles** (Préférences › IA locale › « Tester ce modèle ») : le résultat tient sur une ligne verte (✓, durée) ou rouge (✕, cause en clair), puis la carte et la date ; rien n'est coupé. En cas d'échec, un cadre dit pourquoi et propose des boutons : « Installer Visual C++ (Microsoft) », « Utiliser le processeur à la place », « Réinstaller le moteur », « Mettre à jour le pilote Nvidia »… ; « Détails techniques » montre le message brut.
2. **Musique IA qui s'arrêtait (code 3221225781)** : installer Visual C++ par le bouton, puis « Réessayer ». Sinon « Utiliser le processeur » : la version processeur du moteur s'installe toute seule, et la musique se fait. La même aide apparaît dans l'Atelier IA quand une création échoue.
3. **Agrandissement IA (code 3221226505)** sur un portable Intel + Nvidia : PhilCut réessaie tout seul sur la carte Nvidia et la garde pour la suite.
4. **Tampons, où et comment** : Montage › Tampons vidéo… › double-clic sur un tampon. **Attendu** : fenêtre « Où mettre … ? » : à la ligne rouge (avec l'heure), au début, à la place de la partie en jaune (proposée d'office si une partie est choisie), à la fin ; insérer (la suite se décale) ou par-dessus (rien ne bouge, son du tampon au choix) ; si le tampon n'a pas la durée de la partie : garder, accélérer/ralentir, couper ; un cadre dit en clair ce qui va se passer.
5. **Format différent** : projet 9:16, tampon 16:9 : la fenêtre propose fond flou, bandes noires, recadré (centre, gauche, droite) ou suivi de la personne.
6. **Bibliothèque des tampons** : « Classer » (mon ordre, récents, plus utilisés, nom, durée, vidéos puis sons) ; en « Mon ordre », glisser les vignettes ; clic droit › Monter, Descendre, Tout en haut, ★ Favori. L'ordre suit sur l'autre poste (lieu de synchronisation).
7. **Préférences › Tampons et extraits** : dossier de la bibliothèque (synchronisé ou non), classement, où et comment poser par défaut, format différent, clefs Pixabay/Pexels, yt-dlp, ce qui est permis, qualité YouTube, nombre de résultats. Le bouton « Réglages des tampons et extraits… » de la fenêtre des tampons y mène.
8. **Recherche YouTube** : « planette interdite » : 30 résultats avec vignettes, sur le YouTube de votre pays, mots non traduits ; « Vouliez-vous dire planète interdite ? » cliquable ; liste « Vidéos et Shorts / Shorts seulement / Vidéos ». « Regarder et choisir le morceau… » : la vidéo se lit dans PhilCut, « Début du morceau ici », « Fin du morceau ici », puis seul ce morceau est téléchargé.
9. **Lien direct** : copier le lien d'une vidéo (YouTube, Vimeo, fichier .mp4), « Coller un lien » : elle se lit, on choisit le morceau, téléchargement avec progression.
10. **Internet Archive, Pixabay, Pexels** : liste « Mots tapés et en anglais / tels que tapés / traduits en anglais ».
11. **Vignette** : chaque couleur a son explication avec un exemple ; chaque zone tracée a son champ « Qu'y a-t-il ici ? » : le texte de la zone verte devient ses pastilles, celui de la bleue son titre, celui de la jaune s'écrit au départ de la flèche ; l'IA lit ces textes.
12. **Mes musiques › Classer par artiste** : un groupe par artiste (artiste de l'album d'abord), albums dans l'ordre des pistes ; plus de « 01 » pris pour un artiste ; la lecture des étiquettes avance en bas (« 120 / 1538 ») et la liste se complète toute seule.
13. **Menus** : plus de sous-menu Aviation ; « Seulement les échanges radio » est dans Sous-titres ; libellés courts, l'explication au survol ; « tête de lecture » est devenue « ligne rouge ».

## T36 — 0.9.8 : mise à jour visible, fermeture fiable

1. **Mise à jour** (depuis 0.9.8 vers une version suivante) : Accueil › « Télécharger et installer ». **Attendu** : une fenêtre s'ouvre tout de suite (« Connexion à GitHub… »), puis Mo reçus / total, vitesse, temps restant, barre ; « Arrêter le téléchargement » ; à la fin « Installer et redémarrer ». Couper le réseau pendant le téléchargement : message clair, pas de silence.
2. **Quitter pendant une opération** (export, import, téléchargement) : la fenêtre liste chaque opération (nom, %, étape) ; « Voir les opérations » ouvre le Centre d'activité ; « Rester » ; « Quitter quand même » ferme en moins de 3 s.
3. **Fermeture** : ouvrir un projet, lire la vidéo et écouter un son (Mes musiques, tampons), puis fermer PhilCut. **Attendu** : aucun « PhilCut a cessé de fonctionner », ni « Audio Windows » dans Panneau de configuration › Sécurité et maintenance › Historique de fiabilité.
4. **Bibliothèque musicale** avec un dossier sur un NAS éteint : la fenêtre s'ouvre tout de suite ; le dossier est seulement affiché.
5. **Petit écran** (ou mise à l'échelle 150 %) : ouvrir un projet : la fenêtre reste dans l'écran, la barre d'état visible ; la barre entre l'aperçu et la timeline monte et descend.

## T35 — 0.9.7 : vidéos en ligne (yt-dlp) et films du domaine public (Internet Archive)

1. **Première fois** : Tampons vidéo › Chercher en ligne › « Vidéos en ligne : YouTube et autres, par yt-dlp », taper des mots, « Chercher ». **Attendu** : fenêtre « ce qui est permis » (70 ans après la mort du dernier auteur, licences libres, courte citation) ; OK seulement après avoir coché la confirmation ; puis proposition d'installer yt-dlp (dépôt officiel, environ 18 Mo), avec progression.
2. **Recherche** : des mots ou une adresse https://… **Attendu** : liste titre · chaîne · durée · licence (« ✓ Creative Commons… » quand c'est indiqué) ; texte « Ce qui est permis » sous la liste.
3. **Morceau** : vidéo de plus de 5 min sans « de … à … » : PhilCut demande le morceau. Avec « de 1:00 à 1:10 » : seul ce morceau est téléchargé (progression), il arrive dans « Ma bibliothèque » avec auteur, page et licence ; « Le son seulement » donne un son.
4. **Crédit** : un tampon venu de YouTube posé dans le montage : le crédit (titre, chaîne, page) est ajouté à la description à la publication.
5. **Mettre à jour yt-dlp** : bouton dans la fenêtre et dans Préférences › IA › Extraits en ligne.
6. **Internet Archive** : « Films du domaine public : Internet Archive », mots (traduits en anglais), choisir un film, « de 2:00 à 2:15 », « Ajouter » : seul le morceau est lu et rangé (pas tout le film).
7. **Préférences › IA › Extraits en ligne** : case d'ajout automatique des téléchargements, état de yt-dlp, texte de ce qui est permis, case de confirmation (la décocher : la fenêtre « ce qui est permis » revient au prochain usage).

## T34 — 0.9.6 : sons et extraits (Kaamelott, Voicy), table de sons, raccourcir

1. **Voicy** : Montage › Tampons vidéo › Chercher en ligne › « Répliques et sons de films : Voicy ». Taper une réplique en français, « Chercher ». **Attendu** : le navigateur s'ouvre sur la recherche (en français, pas traduite) ; la barre dit que PhilCut guette le dossier Téléchargements pendant 15 minutes.
2. **Téléchargement** : sur le site, écouter puis télécharger un son. **Attendu** : quelques secondes après la fin du téléchargement, « ✓ « … » ajouté à votre bibliothèque » ; le son est dans « Ma bibliothèque », nommé d'après le fichier, avec les mots de la recherche.
3. **Kaamelott (fspot)** : « Extraits de films et séries : Kaamelott (fspot) » ; taper une réplique, « Chercher ». **Attendu** : le site s'ouvre sur son accueil et la réplique est copiée ; Ctrl+V dans la recherche du site ; l'extrait téléchargé (MP4 ou MP3) arrive dans la bibliothèque.
4. **Case « Ajouter tout seul ce que je télécharge »** décochée : rien n'est ajouté, « Importer le clip téléchargé… » reste possible. Le choix est retenu.
5. **Table de sons** : dans « Ma bibliothèque », un clic sur un son l'écoute ; « ▶ Écouter » aussi pour un clip vidéo.
6. **Raccourcir** : « Raccourcir… » (bouton ou clic droit) : Début, Fin, « ▶ Écouter ce morceau », OK : le tampon ne garde que ce morceau, sa durée est mise à jour.

## T33 — 0.9.5 : retirer le fond d'une image

1. **Goodie** : genre « Image ou logo », « Image… » et choisir un JPG (logo sur fond blanc). **Attendu** : PhilCut signale qu'il n'a pas de fond transparent et propose de le retirer ; l'aperçu du Goodie montre bien le rectangle blanc avant.
2. **Fenêtre « Retirer le fond »** : avant / après sur damier ; méthode Automatique (fond uni détecté) ; tolérance plus haute ou plus basse ; « Recadrer au sujet » ; « Retirer aussi le fond enfermé » (intérieur des lettres, d'un anneau). « Garder l'image sans fond » : une copie « …_sans_fond.png » à côté de l'original, qui reste intact ; l'aperçu du Goodie n'a plus de rectangle blanc.
3. **Photo** : une photo d'un objet ou d'une personne, méthode « Sujet d'une photo » : le sujet est gardé, le décor devient transparent (meilleur avec le modèle de détourage installé).
4. **Médias et plan** : clic droit sur une image dans les médias › « Retirer le fond (copie PNG transparente)… » : la copie s'ajoute aux médias et les plans de cette image l'utilisent ; clic droit sur le plan d'une image › « Retirer le fond de l'image… » : ce plan seulement. La barre du bas le dit.

## T32 — 0.9.4 : timeline plus simple (ligne rouge, partie jaune, zoom)

1. **Clic et glisser** sur la règle ou dans une piste vide : la ligne rouge rouge se déplace, l'aperçu suit ; aucune partie jaune ne se crée par erreur.
2. **Partie jaune** : double-clic sur la règle au début voulu (fanion jaune « Début »), puis double-clic à la fin : la partie apparaît en jaune ; la barre du bas dit quoi faire à chaque étape. Un troisième double-clic recommence une nouvelle partie.
3. **Boutons [ ]** à côté de la tête rouge, sous la règle : [ = la partie commence ici, ] = elle finit ici (main au survol, bulle d'aide).
4. **Ajuster** : sur la règle, les bords de la partie jaune se tirent (curseur flèche double). × l'enlève ; Echap aussi.
5. **Molette = zoom** là où est la souris ; Maj + molette : défiler ; le rappel « Zoom » en haut à gauche (souris et loupe) s'anime à chaque cran ; clic dessus : tout voir.
6. **Bulles d'aide** de la règle : elles disent ce que fait le clic, le double-clic et la molette.

## T31 — 0.9.3 : vignettes et images fixes composées, test des modèles d'IA

1. **Ouvrir** : Fabrique › « Vignette YouTube composée… » (ou clic droit sur l'aperçu, ou sur la règle de la timeline). **Attendu** : l'image du film à la ligne rouge, au format 1280 × 720 ; la barre du bas de la fenêtre dit ce qui se passe.
2. **Zones** : choisir Rouge et entourer un objet ou une personne du film à main levée ; Bleu : un rectangle pour le titre ; Jaune : un petit détail ; Vert : une bande en bas. **Attendu** : le sujet rouge détouré, avec contour, le reste assombri ; la flèche part du titre vers le détail jaune (un cercle si la zone jaune est grande). Clic droit sur une zone › Supprimer ou Changer sa couleur.
3. **Contenu** : taper un titre, un mot en couleur, des éléments « Pistons ✓ », « Soupapes ✗ ». **Attendu** : titre ajusté à la zone bleue, mot en couleur, pastilles avec coche verte ou croix rouge, libellés entiers.
4. **Style** : changer de kit (Punchy, Éditorial, Documentaire, Tech, Aviation), d'effet rouge (loupe, projecteur), de flèche. « Proposer 3 variantes » puis cliquer une variante.
5. **Taille téléphone** : l'aperçu de droite et ses conseils (titre trop petit, trop long, zone verte vide…).
6. **Avant / après** : cocher, choisir l'image « après ». **Attendu** : image coupée en diagonale, étiquettes AVANT / APRÈS.
7. **IA** : écrire la phrase (ex. « moteur : pistons, soupapes, arbre à cames »), IA locale puis IA cloud, « Proposer par l'IA ». **Attendu** : progression et temps écoulé visibles, puis titre, éléments et style remplis, tous modifiables.
8. **Résultats** : « Miniature YouTube de l'export » puis exporter : la vignette du MP4 et le JPG à côté sont l'image composée. « Poser dans le film » : l'image arrive sur la piste Vidéo 2 pour la durée choisie ; clic droit sur ce plan › « Modifier l'image composée… » rouvre tout, « Poser » remplace l'ancien plan.
9. **Test des modèles** : Préférences › IA locale › « Tester les modèles installés ». **Attendu** : étape « Test 1/n : … », barre et temps écoulé, « Arrêter le test » ; sous chaque modèle : ✓ ou ✕, durée, carte graphique ou processeur. Sur la carte NVIDIA du portable, cocher « Utiliser la carte graphique ».

## T30 — 0.9.0 : Mes musiques, Atelier IA en anglais et avancement visible, effet IA visible à la lecture

1. **Mes musiques** : bouton Musique › « Mes musiques (chercher, écouter, poser)… ». **Attendu** : une fenêtre (plus de menu géant) ; la barre du bas de la fenêtre dit ce qui se passe (recherche des morceaux, lecture des titres en arrière-plan). Taper deux mots dans la recherche : la liste se réduit tout de suite. « Classer » : Par dossier, Par album, Par artiste, Tout par titre (retenu à la prochaine ouverture). Clic droit sur un morceau › Écouter, puis « Arrêter l'écoute ». Double-clic (ou « Poser sous la vidéo ») : la musique arrive sur la piste Musique.
2. **Phrase de l'Atelier IA traduite** : Montage › Atelier IA, un effet Image ou Musique, écrire la phrase en français (ex. « musique douce au piano pour un voyage en montagne »), « Créer ». **Attendu** : sous la phrase, « Envoyé au moteur, en anglais : « … » » montre ce qui part vraiment au moteur. Une phrase déjà en anglais (celles du catalogue) part telle quelle. Sans Internet, si des mots ne sont pas connus du petit dictionnaire : message « Pas de traduction pour … : écrivez ces mots en anglais », rien n'est lancé.
3. **Avancement de l'IA visible** : pendant une création, dans la fenêtre de l'Atelier : l'étape (« Étape 1/2 : composition », « Étape 2/2 : fabrication du son », « Dessin de l'image »…), une barre avec le pourcentage et le temps écoulé qui avance chaque seconde, en plus de la barre du bas et du Centre d'activité. En cas d'échec : message en rouge, boutons « Voir le journal du moteur » et « Réessayer ».
4. **Effet IA visible à la lecture** : Atelier IA › Dessin animé (vidéo) sur une partie en jaune. **Attendu** : le clip arrive sur la piste Vidéo 2 au même endroit ; en lecture normale (Espace), le dessin animé se voit à la place du film sur ce passage ; supprimer le clip ramène l'original.
5. **Image IA au-dessus** : Atelier IA › un effet Image, « Créer », puis « Poser au-dessus du film (3 s) ». **Attendu** : l'image arrive sur la piste Vidéo 2, le film de la piste Vidéo 1 n'est ni coupé ni décalé ; elle se voit en lecture.
6. **Taille de la timeline** : glisser la barre entre l'aperçu et la timeline (bulle d'aide au survol) vers le haut. **Attendu** : la timeline prend presque toute la hauteur, l'aperçu rétrécit ; le volet de droite défile. Réglage gardé à la prochaine ouverture.
7. **Volet agrandi** : bouton d'agrandissement en haut à droite du volet (Effets, Inspecteur ou Proposition). **Attendu** : une fenêtre avec le contenu visible (vignettes des effets), pas une fenêtre noire ; à la fermeture le volet revient à sa place.
8. **Analyser et proposer** : volet Proposition, Niveau « IA locale » puis « IA cloud », « Analyser et proposer ». **Attendu** : sous le bouton, l'étape en cours (« Étape 1/2 : lecture des rushes… », « Étape 2/2 : IA locale (modèle) : démarrage du modèle… » ou « envoi à l'IA cloud… »), une barre avec pourcentage et temps écoulé qui avance chaque seconde, et « Arrêter ». Si l'IA ne répond pas, la recette sans IA arrive avec le message orange qui dit pourquoi.
9. **Aperçu du Goodie** : double-clic sur un Goodie de la timeline. **Attendu** : à droite, l'image du film avec le Goodie qui s'anime en boucle de son début à sa fin ; changer la taille, la position, le texte ou le genre se voit aussitôt.

## T29 — 0.8.0 : langues, tampons vidéo, Goodies dessinés, Accueil partagé, catalogue en ligne

0. **Lancement et mise à jour (0.8.4)** : au lancement, un écran avec le logo, la version, l'étape en cours (réglages, moteur vidéo, effets, Goodies, timeline, fenêtre) et une barre de progression s'affiche jusqu'à la fenêtre. Aide › Rechercher une mise à jour, quand une version plus récente existe : « Télécharger et installer » montre la progression en Mo dans la barre du bas, puis propose de fermer PhilCut pour installer.
1. **Langues** : Edition › Préférences › Langue : English, puis relancer. **Attendu** : tous les menus, fenêtres, infobulles et messages sont en anglais, y compris ceux ajoutés depuis la 0.2 (Atelier IA, Dites-le en clair, transitions automatiques, tampons…). Même chose en Deutsch, Español, Italiano. Noter toute phrase restée en français ou mal tournée. Revenir en Français.
2. **Tampons vidéo** : Montage › Tampons vidéo (ou clic droit sur l'aperçu ou dans la timeline › « Tampon vidéo ici… »). Onglet « Tampons maison » : les vignettes bougent ; « Créer les 12 tampons maison manquants » (barre du bas). **Attendu** : ils arrivent dans « Ma bibliothèque » avec leur aperçu animé. Double-clic sur « Quelques heures plus tard… » : inséré à la ligne rouge, la suite du montage se décale, le son est là ; Edition › Annuler le retire.
3. **Mes tampons** : « Importer mon clip… » (nom, mots-clefs) ; « Partie en jaune → tampon » après avoir choisi 2 s en jaune ; recherche par mot-clef ; « Renommer, mots-clefs… » ; « Retirer ».
4. **Clips libres en ligne** : onglet « Chercher en ligne », Wikimedia Commons, chercher « applause » (anglais). **Attendu** : vignettes, auteur et licence ; « Ajouter et insérer ». A la publication (Outils › Publier), le crédit est déjà dans la description.
5. **Pixabay / Pexels** : créer la clef gratuite sur le site (« Ma clef… » › « Ouvrir la page »), la coller dans PhilCut (jamais dans la conversation) : elle va dans le coffre du système. Chercher, ajouter quelques clips à la bibliothèque.
6. **Bibliothèque partagée** : avec un emplacement de synchronisation (Drive, NAS), les tampons sont rangés dans PhilCut/tampons et se retrouvent sur l'autre poste.
7. **Goodies dessinés** : Goodies › packs Balade, Route, Fête, Maison, Commerce : altitude (montagne), distance (sentier), dénivelé (profil), météo (ciel réglable dans l'Inspecteur : soleil, éclaircies, nuageux, pluie, neige), température (thermomètre), compteur (arc), compte à rebours (anneau, « Compter à partir de »), date (page de calendrier), bandeau (ruban), horaires (panneau), prix (étiquette), pastille (étoile). Le style « HUD épuré » garde le badge sobre.
8. **Accueil partagé** : ouvrir un projet sur un poste, puis lancer PhilCut sur l'autre poste. **Attendu** : dans les projets récents, le projet de l'autre poste apparaît en gris, « ouvert sur « nom du poste » (date) » ; double-clic : PhilCut le cherche sur ce poste (même dossier, Drive, NAS) et l'ouvre.
4 bis. **Extraits de films (0.8.2)** : source « Extraits de films : clip.cafe », taper « merci beaucoup », Chercher : le navigateur s'ouvre sur clip.cafe avec « thank you very much » ; télécharger un extrait, puis « Importer le clip téléchargé… ». Même chose avec Yarn et PlayPhrase.me (ce dernier ne permet pas toujours de télécharger).
4 quater. **Répliques et sons de films (0.8.3)** : source « Répliques et sons de films : Voicy » (ou Movie-sounds.org, MovieSoundClips, WavSource, Sample Focus, QuoDB), taper une réplique, Chercher : le navigateur ouvre une recherche limitée à ce site ; télécharger le son (mp3), « Importer le clip téléchargé… ». Dans Ma bibliothèque il porte une icône de note ; double-clic : posé à la ligne rouge sur une piste de son, le film n'est pas décalé.
4 ter. **Recherche traduite** : Wikimedia Commons ou Pixabay, taper « applaudissements » : la barre du bas indique « Recherché en anglais : « applause » ». Musique › Bibliothèque musicale libre, « coucher de soleil » : même chose.
8 bis. **Clefs sur les autres postes (0.8.1)** : poste 1 : Préférences › Comptes et synchro, cocher « Synchroniser aussi les mots de passe et clefs », OK : choisir la phrase secrète (deux fois, indice facultatif). Poste 2 : au démarrage, l'Accueil propose « Donner la phrase… » ; après la phrase, la clef Pixabay ou Pexels (et les clefs IA) sont là sans les recopier. Une clef ajoutée ensuite sur un poste arrive sur l'autre en une minute environ.
9. **Catalogue d'effets en ligne** : Effets : 25 nouveaux effets (Bleu-orangé, Pellicule chaude, Nuit américaine, Cassette VHS, Pop art, Pixel art, Stroboscope, Niveaux automatiques, Enlever la brume…) avec leurs vignettes animées ; Atelier IA : 14 nouvelles phrases (carnet de voyage, pixel art, briques, papier découpé, neige, coucher de soleil, autocollant, badge rétro, musiques surf, suspense, chiptune, fanfare).

## T28 — 0.6 et 0.7 : IA créative sur ce poste (images, effets IA, logo, musique)

Préparation (une fois) : Edition › Préférences › IA locale : cocher « Images rapides (SD-Turbo) » ou « Images de qualité (SDXL-Turbo) » (carte graphique 8 Go), « Profondeur », un « Dessin animé », « Agrandissement IA », « Ralenti fluide IA », « Musique rapide » ou « Musique de qualité », et si l'on veut « Vidéo IA (Wan, expérimental) ». La taille s'affiche avant ; les téléchargements se mettent en pause et reprennent (T25).

1. **Retoucher l'image du film** : ligne rouge sur une belle image ; Montage › Atelier IA › « Retoucher l'image du film ». Choisir « Personnage 3D façon film d'animation », « Anime japonais », « Bande dessinée »… **Attendu** : à gauche l'image du film, à droite le résultat après « Créer » (barre du bas avec le pourcentage). « Force » : 20 % = proche de l'original, 80 % = très transformé. Puis « Insérer à la ligne rouge (3 s) » (la suite se décale, zoom lent), « Ajouter aux médias », « Logo dans la Fabrique… » ou « Enregistrer en JPG (miniature) ».
2. **Phrase modifiable** : changer la phrase d'un effet, « Garder ma phrase » (elle revient la fois suivante ; « Rétablir » revient à l'original), ou « Enregistrer comme mon effet » (il apparaît avec ★).
3. **Logo et miniature** : Atelier IA › « Logo, intro ou miniature » : « Mascotte cartoon à partir de l'image » (à partir de la personne ou de l'objet à l'écran), « Emblème rond » et « Fond d'intro » (sans image), « Miniature YouTube éclatante ».
4. **Effet sur la partie en jaune** : choisir 2 à 5 s en jaune sur un plan ; Atelier IA › « Effet IA sur la partie en jaune » : « Dessin animé (vidéo) » (sans modèle : version OpenCV, instantanée), « Flou d'arrière-plan (effet portrait) », « Agrandir ×2 », « Ralenti fluide ×4 ». **Attendu** : le clip traité est posé au-dessus, sur la piste Vidéo 2, plein cadre ; l'original reste dessous ; le supprimer revient à l'original.
5. **Photo 3D** : « Photo 3D à partir de l'image (3 s) » : la caméra avance dans l'image, le premier plan bouge plus que le fond.
5 bis. **Transition 3D** : ligne rouge près d'un raccord ; « Transition 3D entre deux plans » : la caméra plonge dans la dernière image du plan qui part et ressort de la première du suivant ; le clip est posé au-dessus du raccord.
6. **Animer l'image (Wan, expérimental)** : seulement avec la carte graphique ; plusieurs minutes pour 2 à 3 s. Dire si le résultat vaut l'attente.
7. **Musique IA** : bouton Musique › « Créer une musique par IA », ou Atelier IA › Musique : style (Pop aérienne, Cinématique épique, Lo-fi calme…), durée (par défaut celle du montage), « Sans paroles » ou des paroles. **Attendu** : le morceau arrive sur la piste Musique, coupé à la fin de la vidéo, avec des fondus. La Proposition (T25 point 9) utilise aussi la musique IA quand le modèle est là.
8. **Transitions automatiques** (T27) puis export : tout doit se retrouver dans la vidéo exportée.

## T27 — 0.5.1 et 0.5.2 : textes, transitions et logos modernes, transitions automatiques

1. **Texte moderne** : outil Texte › « Style moderne » (par exemple « Clean minimal — Bas de l'écran, sobre ») et un sous-titre. **Attendu** : le texte animé arrive sur la piste Goodies ; l'Inspecteur change texte, sous-titre et animation. « Aucun » garde le texte classique.
2. **Bas de l'écran** : les deux modèles « Bas de l'écran » (sobre, bloc couleur) pour présenter une personne ou un lieu.
3. **Transitions modernes** : catalogue des effets, famille Transitions : Zoom avant, Poussée douce, Filé vertical, Balayage radial, Coup de vent, Tranches, Recouvrement, Passage par le gris ; vignettes animées sur votre plan.
4. **Atelier de logo** : les gabarits « Moderne : … » (mot en gras + point, monogramme fin, bloc incliné, ligne et lettres espacées, pastille arrondie) en tête de liste.
5. **Transitions automatiques** : Montage › Transitions automatiques. Choisir le style (Punchy, Clean minimal, Cinéma). **Attendu** : une ligne par raccord avec la transition proposée et sa raison (panoramique → filé, même scène → coupe franche, temps fort de la musique ♪…) ; chaque ligne se décoche ou se change ; « Poser » ; Edition › Annuler défait tout.

## T26 — 0.5.0 : intros modernes, titre d'ouverture sur le film, vignette du fichier

1. **Fabrique › Logo et intro** : tapez un titre et un sous-titre. **Attendu** : dix vignettes animées, calculées avec VOTRE texte, rangées en trois styles (Punchy, Clean minimal, Cinéma) ; le modèle cliqué joue en grand à droite avec sa description. « Anciens modèles » dans la liste Style garde les modèles d'avant.
2. **Fond** : « Dégradé vivant », « Premières images du film, floutées » (prend une image du premier plan de votre projet), « Couleur unie » ; « Couleur d'accent » change la couleur des barres et traits ; les vignettes se recalculent.
3. **Fabriquer** : le clip arrive dans les médias et au début du montage. Vérifier : mouvements qui démarrent vite et freinent en douceur, polices nettes, aucun texte qui déborde.
4. **Assistant** : niveau Recettes, Analyser puis Appliquer. **Attendu** : le titre d'ouverture est posé SUR les premières images du film (piste Goodies, « Titre d'ouverture animé »), plus de plan noir en tête ; dans l'Inspecteur, texte, sous-titre et animation se changent.
5. **Goodies › Titres et flèches tendance › Titre d'ouverture animé** : même titre, posable n'importe où.
6. **Vignette du fichier** : clic droit sur la règle › « Prendre cette image comme vignette du fichier » : un petit cadre bleu apparaît sur la règle. Dans Exporter, ligne « Image du fichier » avec l'aperçu ; après l'export, l'explorateur de fichiers montre cette image, et un JPG « …_vignette.jpg » est à côté (miniature YouTube).

## T25 — 0.4.4 : musique retravaillée, téléchargements en pause, « Dites-le en clair », flèches et titres tendance, voix studio

1. **Musique trop longue** : importer une musique de 3 min sous une vidéo de 30 s. **Attendu** : la barre du bas dit « « … » dure plus longtemps que la vidéo (2:30 de trop) » avec un bouton « Couper à la fin de la vidéo » ; un clic et la musique s'arrête avec la vidéo, avec un fondu. Même chose par clic droit sur la musique › « Couper ce son à la fin de la vidéo ».
2. **Retravailler la musique** : cliquer la musique, Inspecteur › « Son : début, fondus, longueur » : « Commencer le morceau à » 32 s (on saute l'introduction, le plan garde sa place) ; fondu d'entrée et de sortie en secondes (0 = aucun) ; « Couper à la ligne rouge ». **Attendu** : les fondus se dessinent en rampes blanches aux deux bouts du plan et s'entendent à l'export.
3. **Se déplacer dans la timeline** : barre au-dessus de la timeline : ⇤ (début), ⇥ (fin du montage), − et + (zoom), « Tout voir » (tout le montage dans la largeur), ↕ (hauteur des pistes). La barre d'information dit ce que fait chaque bouton.
4. **Tête de lecture et partie jaune** : glisser la tête rouge en restant appuyé déplace la lecture sans rien sélectionner. Une partie jaune se retire par sa croix ×, par un simple clic sur la règle, par Echap, ou clic droit › « Enlever la partie jaune ».
5. **Effets visibles en balayant** : quand le passage a été préparé (barre « Préparation »), promener la ligne rouge montre l'image avec ses effets (badge « ✦ balayage avec effets »).
6. **Effets : erreur lisible et plusieurs effets** : dans la fenêtre Effets, un aperçu impossible affiche la vraie cause (et non les statistiques de l'encodeur) ; poser deux ou trois effets à la suite : tous restent dans la liste et à l'export.
7. **Téléchargements** : pendant un téléchargement de modèle, « ⏸ Pause » ; fermer PhilCut ; le rouvrir. **Attendu** : bandeau « ⏸ 1 téléchargement non terminé… » avec « ▶ Reprendre » ; il repart du pourcentage atteint. Colonnes élargissables à la souris (largeurs retenues), colonne Taille, « Tout reprendre ». Même chose dans le Centre d'activité.
8. **Musiques libres et Mes musiques** : bibliothèque musicale libre : « Dossier de téléchargement : … » avec « Changer de dossier… » et « Ouvrir le dossier » ; pendant une recherche, « ■ Arrêter la recherche ». Bouton Musique › « Mes musiques » : « Classer : Par dossier / Par album / Par artiste / Tout, par titre » (retenu) ; « Choisir mon dossier de musiques… ».
9. **Proposition avec musique** : niveau Recettes, sans musique importée, « Analyser et proposer » puis « Appliquer ». **Attendu** : une musique de vos dossiers qui colle à l'ambiance, sinon une musique libre téléchargée, est posée et coupée à la fin de la vidéo.
10. **Dites-le en clair** : volet Proposition, champ « Dites-le en clair » (ou Montage › Dites-le en clair) : « mets une musique calme et coupe-la à la fin de la vidéo, titre « Notre week-end » au début, une flèche rouge courbe à 2 s ». **Attendu** : la liste de ce qui va être fait, chaque ligne cochable ; « Faire » ; Edition › Annuler défait tout d'un coup. Niveaux IA locale et IA cloud (coût affiché avant l'envoi) pour les demandes plus libres.
11. **Flèches et titres tendance** : Goodies › famille « Titres et flèches tendance » : « Titre bandeau » (majuscules sur boîte inclinée, deux lignes avec « | », deux couleurs, gros contour), « Flèche » (courbe dessinée à la main, boucle, éclair, droite ; contour blanc, épaisseur, couleurs en un clic), « Mot surligné ». **Attendu** : avec deux images clefs, la flèche se déplace **et tourne** d'un endroit à l'autre pendant le plan (curseur Direction à chaque image clef).
12. **Voix studio** : Voix › Enregistrer : retouche « Voix studio, façon Insta (conseillé) » cochée ; écouter avant / après. **Attendu** : souffle et bruit de fond effacés par le débruitage à réseau de neurones (sur ce poste), voix proche, nette, niveau régulier. « Voix studio, plus naturelle » existe aussi dans les retouches.

## T24 — 0.4.3 : IA sur les rushes (sur ce poste) et derniers effets

1. **Analyser les rushes** : un modèle de vision doit être coché dans Préférences › IA locale. Clic droit sur un média (ou plusieurs sélectionnés) › « Analyser avec l'IA locale », ou « Analyser tous les rushes ». **Attendu** : barre du bas « Analyse de 3 rush(es) par l'IA locale, sur ce poste » avec le pourcentage ; rien n'est envoyé sur Internet. Ensuite, sous le nom du média, un nom court (« Décollage de Cannes ») ; au survol : la description et les « Textes lus » (immatriculations, panneaux). La fiche vidéo affiche « Vu par l'IA locale ».
2. **Rechercher** : champ « Rechercher : nom, lieu, objet, texte lu… » au-dessus des médias : « mer », « F-GHIJ », « decollage » (accents ignorés) ne laissent que les rushes concernés.
3. **Texte lu → étiquette** : clic droit sur un média analysé › « Etiquette « F-GHIJ » (texte lu) » : une étiquette est posée sur le premier plan de ce rush, réglable dans l'Inspecteur.
4. **Bullet time** : clic droit sur l'image › Figer l'image › Présentation « Bullet time » : la caméra semble tourner autour de l'image figée, teinte Matrix, whoosh. Effet « Orbite » aussi seul dans le catalogue.
5. **Personne en code** (pack Détourage) : effet « Personne en code » sur un plan avec une personne : la silhouette se remplit de caractères verts puis redevient réelle.

## T23 — 0.4.2 : confort de l'interface

1. **Petit écran** (portable 1366 × 768) : toutes les pistes de la timeline sont visibles sans défiler, jusqu'aux Titres et Goodies ; quand il y en a beaucoup, elles se tassent et les noms deviennent courts (V1, V2, M1…) avec les boutons M et S sur la ligne du nom (le verrou et V restent dans le clic droit › Pistes). Si vous agrandissez les images (Alt + molette), la timeline défile à nouveau.
2. **Colonne des médias repliable** : bouton ◂ à droite de « Médias du projet » (ou Affichage › Colonne des médias, F3) : elle devient une colonne d'icônes « Médias » et « Importer » ; l'image gagne la place. Retenu à la prochaine ouverture.
3. **Onglets du volet** : « Proposition », « Inspecteur », « Effets » s'affichent en entier, même volet étroit.
4. **Goodies** : le bouton Goodies ouvre une galerie de vignettes dessinées, par famille ; double-clic : le Goodie arrive à la ligne rouge, l'Inspecteur s'ouvre dessus. Croix de pharmacie verte qui pulse, confettis, lune, image ou logo (cadre « Votre image ou logo » tant qu'aucune n'est choisie). Les textes des badges se réduisent pour tenir.
5. **Accueil** : sans projet récent, la liste dit comment commencer au lieu d'un cadre vide.

## T22 — 0.4.1 : effets manquants

1. **Nouveaux effets** (catalogue de l'onglet Effets, ou fenêtre Effets) : « Tremblement » (secousse réglable, peut s'amortir comme un choc), « Zoom lent (Ken Burns) », « Cadre photo » (bord blanc incliné sur fond flou), « Mon look (fichier LUT) » (bouton « Choisir un fichier… » : un .cube ou .3dl, force réglable), « Avant / après » (choisir l'image ou la vidéo « avant » : rideau qui glisse, ou moitié / moitié, libellés AVANT / APRES). Chacun se voit à l'arrêt et à la lecture (barre verte).
2. **Nouvelles transitions** : « Choc » (flash et secousse), « Rotation » (le plan arrive en tournant), « Filé (whip pan) » (panoramique flou très rapide). A poser sur un raccord.
3. **Fondu au noir et flash blanc** : ils empêchaient l'aperçu fidèle et l'export (erreur du moteur) ; vérifier qu'un montage avec un fondu au noir s'exporte.
4. **Image figée** : ligne rouge sur l'image voulue, clic droit sur l'image (ou sur le plan, ou Montage) › « Figer l'image ici ». Durée, cadre photo ou image simple, zoom lent, légende, flash, déclic. **Attendu** : le plan s'arrête sur cette image (un plan « Image figée » orange dans la timeline), la suite est décalée d'autant, la légende est posée sur la piste Titres, le déclic sur une piste de son. Tout se reprend : rogner, effets, supprimer, Annuler.
5. **Bruitages** : Montage › « Bruitages… » (ou clic droit sur l'image › « Bruitage ici »). Whoosh, impact, déclic, bip, ding, pop, radio, moteur : « ▶ Ecouter », puis « Poser à la ligne rouge » : le son arrive sur une piste de son libre (une piste est ajoutée si toutes sont occupées). Clic droit sur une transition › « Ajouter un bruitage « whoosh » sur le raccord ».
6. **Autocollants** : bouton Goodies › pack « Autocollants » : Polaroïd (choisir la photo et la légende dans l'Inspecteur, rubrique Contenu), Post-it (texte, couleur), Flèche (direction, couleur). Ils arrivent animés (le polaroïd tombe, la flèche se trace), se déplacent et se redimensionnent dans l'image, peuvent suivre une personne.
7. **Toutes les fenêtres « OK »** : avec la dernière version de Qt, certaines fenêtres (Effets, Texte, Goodie, Vitesse…) ne faisaient rien après OK. Vérifier : Effets › poser un effet › OK : l'étiquette apparaît sur le plan.

## T21 — 0.4.0 : lot Aviation (tout réglé par vous)

1. **Tableau de bord** : Montage › Goodies › bouton « Tableau de bord complet… » (aussi clic droit sur l'image › Goodies). Cochez les instruments, réglez le profil : altitudes (terrain, croisière, arrivée), vitesse, régime, durées du roulage, de la montée, de la descente, caps. **Attendu** : les courbes (altitude, vitesse, cap) se redessinent à chaque réglage. « Poser le tableau de bord » : les instruments s'alignent en bas de l'image, l'aiguille de l'altimètre monte pendant la montée, le variomètre indique la vitesse de montée, l'horizon se cabre et s'incline dans les virages, le compte-tours suit le régime. Sur la piste Goodies, chaque instrument a sa ligne (elles s'empilent).
2. **Modifier** : clic sur un instrument (image ou piste Goodies) › Inspecteur : « Profil de vol… » rouvre la fenêtre et met à jour tous les instruments ; « Valeurs dans le temps » : tableau instant / valeur à corriger, « + Point à la ligne rouge », « Retirer la ligne ». Glisser et coins dans l'image comme tout Goodie.
3. **Trajet** : Goodies › « Carte du trajet » ou « Mini-carte ». Ajoutez les étapes (liste d'aérodromes : tapez « LFMD » ou « Cannes », Ajouter ; ou un point avec ses coordonnées), l'ordre se change par ↑ ↓ ou en glissant. L'aperçu de la carte se met à jour ; « 3 étapes · 139 NM ». Fond sombre ou papier, immobile au départ (roulage). **Attendu** : à la lecture, le trait jaune se dessine et l'avion avance sur la carte, orienté selon sa route ; la mini-carte ronde suit l'avion de près. Si une carte existe, le tableau de bord propose « le cap suit le trajet ».
4. **Manche à air** (Goodies › Manche à air) : direction du vent, force, rafales, côté où elle flotte. L'aperçu bouge dans la fenêtre ; dans la vidéo, elle se gonfle selon la force (pleine à 15 kt) et oscille avec les rafales ; « 250° / 12 kt » sous la manche (option).
5. **Radio** : Aviation › « Sous-titres des échanges radio » (modèle « Voix » de l'IA locale nécessaire). Le son des plans est écouté dans la bande de la radio ; les phrases qui ressemblent à des échanges (phraséologie, alphabet, immatriculation, fréquence) sont cochées, les autres listées décochées ; le texte se corrige. « Poser les phrases cochées » : en haut à gauche de l'image, « RADIO › … » en jaune sur fond sombre.

## T20 — 0.3.4 : la timeline complète (changer de piste, copier les effets, effet sur une partie, images clefs)

1. **Changer de piste** : ajoutez une piste Vidéo 2 (clic droit sur les noms de pistes). Glissez un plan de Vidéo 1 vers le haut : pendant le glissement, il saute sur Vidéo 2 et l'étiquette « → Vidéo 2 » s'affiche ; lâchez : c'est une incrustation (rubrique Incrustation de l'Inspecteur). Même chose entre Musique 1 et Musique 2. Une piste verrouillée ou d'un autre genre (vidéo vers son) refuse le plan. Aussi par clic droit sur le plan › « Déplacer vers la piste ».
2. **Copier / coller des effets** : clic droit sur un plan qui a des effets › « Copier les effets de ce plan (2) » (ou clic droit sur une étiquette › « Copier cet effet ») ; la barre du bas confirme. Clic droit sur un autre plan › « Coller les effets (2) ». Annuler les retire.
3. **Effet sur une partie du plan** : double-cliquez sur la règle au début puis à la fin pour faire une partie jaune au milieu d'un plan, puis glissez un effet du catalogue sur ce plan (ou bouton Effets) : l'effet devient une **bande bleue** sous le plan, de la partie jaune seulement ; le plan n'est plus coupé. Tirez les bords de la bande : l'étiquette du haut indique « Effet de 0:01.0 à 0:02.5 ». Clic droit sur la bande : « Sur tout le plan », « Seulement sur la partie en jaune ». Dans l'Inspecteur, l'effet déplié : « S'applique à : Tout le plan / Une partie du plan », De, A. Lecture : l'effet ne se voit que sur ces secondes.
4. **Images clefs** : plan en Vidéo 2 (incrustation), texte ou Goodie. Tête de lecture au début du mouvement, Inspecteur › « Animation (images clefs) » › « ◆ Image clef ici ». Avancez de 3 secondes, changez la taille ou la position (curseurs, ou glisser le texte dans l'image) : une seconde image clef se pose toute seule, un losange ◆ jaune apparaît sur le plan ou sur la barre du texte. **Attendu** : à l'arrêt entre les deux, l'image montre la position intermédiaire ; à la lecture (barre verte) et à l'export, l'incrustation glisse et grossit, le texte se déplace et grandit. Les curseurs de l'Inspecteur suivent la ligne rouge. Clic sur un losange : la ligne rouge y va ; clic droit : supprimer. ◀ ▶ : image clef précédente / suivante ; « Tout effacer » revient à des réglages fixes. Opacité : une incrustation peut aussi apparaître ou s'effacer.

## T19 — 0.3.3 : zones floutées et suivies, poignées dans l'image, catalogue animé, voix

1. **Tracer une zone** : curseur sur un plan où l'on voit un visage (ou une plaque, un écran). Bouton **Zone** de la barre d'outils (ou clic droit sur l'image › « Tracer une zone… », ou Montage › Zone). La barre du bas dit « Tracez la zone dans l'image… » et le curseur devient une croix : cliquez à un coin du visage et tirez jusqu'au coin opposé. **Attendu** : la zone apparaît (contour bleu pointillé, étiquette « Zone : Flou »), une barre bleue « Zone : Flou » sur la piste Goodies du début du plan à sa fin, l'Inspecteur ouvert dessus ; à l'arrêt, une seconde plus tard, l'image fidèle montre le vrai flou. Echap pendant le tracé : abandon.
2. **Régler** : dans l'Inspecteur, Effet : Flou, Mosaïque (gros pixels), Cache de couleur unie (bouton Couleur), Assombrir, Eclaircir, Noir et blanc ; Force ; Forme : Rectangle ou Ovale ; Début, Fin. Chaque réglage se voit à l'arrêt. Dans l'image : glisser la zone la déplace, tirer un de ses quatre coins carrés la redimensionne (librement), la molette la grossit ou la réduit. Annuler reprend chaque geste.
3. **Suivre** : Inspecteur › « Suivre ce qu'elle couvre » (ou clic droit sur la barre bleue). **Attendu** : barre du bas « Analyse de l'image : la zone suit ce qu'elle couvre » avec le pourcentage, puis « Zone suivie : N positions ». Avancez image par image (molette sur l'image) : la zone reste sur le visage. Barre bleue : « Zone : Flou · suivie ». Lecture ▶ : la barre rouge/verte prépare le passage et la lecture montre le flou qui suit.
4. **Corriger** : si la zone décroche (visage caché, demi-tour), mettez la ligne rouge à cet instant, « Corriger à la ligne rouge (retracer ici) », retracez la zone : le suivi est gardé avant, refait après. « Figer » : la zone ne bouge plus. Supprimer : bouton rouge de l'Inspecteur, ou clic droit › Supprimer.
5. **Poignées des textes et Goodies** : survolez un texte dans l'image : cadre jaune pointillé avec quatre coins carrés. Tirez un coin : le texte grandit ou rétrécit en gardant ses proportions (même effet que la molette) ; glissez au milieu : il se déplace.
6. **Catalogue animé** : volet de droite, onglet **Effets**. **Attendu** : une grille de vignettes ; en quelques secondes chacune se met à bouger et montre l'effet sur VOTRE plan (celui sous la ligne rouge) ; « Vignettes prêtes : 14 sur 42 ». Famille en haut (Toutes, ★ Favoris, Look…), recherche. Survol : description. **Glisser-déposer** : tirez une vignette d'effet sur un plan de la timeline : le plan s'entoure de jaune pendant le survol ; lâchez : l'étiquette ✦ apparaît, l'Inspecteur a ses réglages. Tirez une **transition** près du raccord entre deux plans : le raccord s'allume en jaune ; sur le premier plan, le dépôt est refusé. Double-clic sur une vignette : sur le plan sélectionné. Clic droit : favoris, fenêtre Effets.
7. **Voix de narration** : Voix › Enregistrer. « Amélioration de la voix » : Narration claire (conseillé), Narration chaude (radio), Pièce bruyante, ou Aucune ; « Retirer les blancs du début et de la fin ». Enregistrez, puis **▶ Avant (brut)** et **▶ Après (amélioré)** : on compare avant de poser. « Poser sur la piste Voix » pose la prise retouchée (le filtre reste modifiable dans l'Inspecteur). Dans l'Inspecteur d'un plan de voix : « ▶ Ecouter avec ces retouches » (15 s rendues avec les retouches cochées).
8. **Autotune** : clic sur un plan de voix chantée › Inspecteur › « Autotune… » (ou menu Voix). Tonalité (toutes les notes, ou Do majeur, La mineur…), Force (Naturel, Net, Robot). **▶ Avant** / **▶ Après (10 s corrigées)**, puis « Appliquer au plan » : le plan passe sur un nouveau fichier corrigé ; « Revenir à l'enregistrement d'origine » le rend tel quel.

## T18 — 0.3.2 : en-têtes de piste, rognage et aimantation visibles

1. **En-têtes** : sous le nom de chaque piste, **M** (son coupé), **S** (solo : on n'entend que les pistes en solo), **V** (image masquée, pistes vidéo 2 et plus), **🔒** (verrou). La flèche ▾ à droite du nom replie la piste (▸ la déplie). Survol : bulle d'aide. Clic droit sur le nom › Pistes : les mêmes, plus « Renommer ». Double-clic sur le nom : renommer.
2. **Verrou** : piste verrouillée : ses plans portent 🔒, le curseur devient « interdit », on ne peut ni les déplacer, ni les rogner, ni les couper, ni les supprimer ; on peut encore les sélectionner et voir leurs réglages.
3. **Rognage visible** : tirez le bord d'un plan : un trait jaune suit le bord et une étiquette indique « Début dans le rush : 0:01.5 · durée 3,0 s ».
4. **Aimantation visible** : en glissant un plan ou un bord près d'un autre plan ou du curseur, un trait bleu pointillé montre où il se colle (bouton Aimant de la barre pour l'arrêter).

## T17 — 0.3.1 : la lecture montre les effets

1. **Barre rouge / verte** : posez un effet sur un plan. **Attendu** : au-dessus de la timeline, juste sous la règle, une barre **rouge** apparaît sur les secondes concernées, passe à l'**orange** pendant la préparation, puis au **vert**. La barre du bas dit « Préparation de la lecture (0:08 → 0:12) ».
2. **Lecture simple** : placez le curseur avant la zone verte et appuyez sur ▶ (pas ▶✦). **Attendu** : en entrant dans le vert, l'image montre l'effet (bandeau « ✦ lecture avec effets »), puis redevient brute à la sortie ; le son suit sans coupure notable.
3. **Modifier** : changez un réglage de l'effet dans l'Inspecteur : seule la partie touchée redevient rouge puis verte. Annuler : elle redevient verte tout de suite (déjà préparée).
4. **Balayage** : tirez le curseur rouge à la souris sur un plan : les images suivent instantanément (petites images préparées une fois par rush) ; au lâcher, l'image exacte s'affiche.
5. **Poste lent** : le bouton ⟳ sous la vidéo coupe la préparation automatique (et ✦ l'image fidèle).

## T16 — 0.3.0 : tout ce qui est posé se voit et se reprend

Parcours à faire dans l'ordre, avec un rush de quelques secondes posé deux fois dans la timeline.

1. **Image fidèle** : cliquez sur un plan, Effets, posez « Noir et blanc », OK. **Attendu** : moins d'une seconde après, l'aperçu montre le plan en noir et blanc avec le bandeau « ✦ image avec effets » en haut à gauche ; à la lecture normale (▶), l'image redevient brute et le rendu revient dès la pause. **Lecture avec effets** : bouton **▶✦** à côté de Lecture : la barre du bas montre « Préparation de la lecture avec effets », puis les 15 secondes à partir du curseur se jouent dans l'aperçu avec tout (effets, transitions, incrustations, textes, son mélangé) et le bandeau « ✦ lecture avec effets ». Pendant qu'elles se jouent, les 15 s suivantes se préparent (barre du bas) et la lecture enchaîne sans arrêt tant que la préparation suit ; sinon elle continue avec les rushes bruts. Les passages préparés sont gardés : un second ▶✦ au même endroit part tout de suite. Déplacez le curseur : l'image se recalcule à chaque arrêt. Le bouton ✦ sous la vidéo désactive ce rendu sur un poste lent.
2. **Etiquettes d'effets** : sur le plan, une étiquette « ✦ Noir et blanc » apparaît en bas. Clic dessus : l'Inspecteur (volet de droite) s'ouvre avec ses réglages dépliés. Clic droit sur l'étiquette : Régler, Actif (décocher = l'effet reste posé mais ne s'applique plus, l'étiquette passe en gris « (off) » et l'aperçu le montre), Supprimer.
3. **Transition** : sur le **2e plan**, Effets › Transitions › Fondu enchaîné, Poser, OK. **Attendu** : un bloc jaune hachuré sur la jonction, large comme sa durée, avec « ⇆ Fondu enchaîné 0,8 s ». Tirez son bord droit : la durée change (et l'Inspecteur suit). Clic droit : Durée, Changer pour…, Active, Supprimer. Curseur dans le bloc : l'aperçu montre le mélange des deux plans.
4. **Inspecteur** : cliquez sur un plan : vitesse, cadrage, volume, muet, transition d'entrée, liste des effets (case Actif, ↑ ↓, poubelle, réglages dépliables), voix et son, « Supprimer ce plan ». Chaque réglage se voit tout de suite dans l'aperçu à l'arrêt. Une rafale de changements (un curseur qu'on tire) = un seul Annuler.
5. **Texte et Goodie dans l'Inspecteur** : cliquez sur le texte (piste Titres) : texte, animation, effet, taille, couleur, début, fin, position ; « Supprimer ce texte ». Même chose pour un Goodie.
6. **Volet agrandi** : bouton ⤢ en haut à droite du volet : l'Inspecteur (ou la Proposition) s'ouvre dans une fenêtre redimensionnable ; à sa fermeture il revient à sa place.
7. **Barre d'information** : en bas à droite, « ✓ Prêt » au repos ; pendant un export, un aperçu, un téléchargement : « ● Export … — 43 % · 1 autre(s) ». Clic : le **Centre d'activité** (toutes les tâches, état, détail, durée, reste, Arrêter ; Outils › Centre d'activité).
8. **Déplacer dans l'image** : survolez un texte ou un Goodie dans l'aperçu : un cadre pointillé jaune apparaît ; glissez-le : il se déplace (l'Inspecteur suit, Annuler possible). Molette sur le cadre : plus grand ou plus petit. Double-clic dessus : ses réglages. La molette ailleurs sur l'image avance ou recule d'une image.
9. **Pistes multiples** : clic droit sur les noms de pistes (colonne de gauche) ou dans une piste vide › Pistes › « Ajouter une piste vidéo au-dessus » : une piste **Vidéo 2** apparaît au-dessus de Vidéo 1 ; glissez-y un second rush. **Attendu** : à l'arrêt, l'aperçu montre le rush 2 par-dessus le rush 1. Dans l'Inspecteur du plan de Vidéo 2, rubrique « Incrustation » : « Petit, en bas à droite » → image dans l'image ; taille, position, opacité réglables. « Ajouter une piste de musique » donne Musique 2. Une piste ajoutée se retire par le même menu quand elle est vide. Sous le nom de chaque piste, le bouton **M** coupe son son (écoute et export) ; sur les pistes vidéo 2 et plus, **V** masque l'image ; les plans d'une piste coupée ou masquée sont grisés. A l'export, les incrustations et toutes les musiques sont là. (A la lecture, seule la vidéo 1 bouge : les incrustations se voient à l'arrêt et à l'export en 0.3.0.)
10. **Catalogue des effets** : familles dépliables (l'état est mémorisé), recherche en haut, clic droit sur un effet › « ★ Ajouter aux favoris » : il passe dans la famille « ★ Favoris » en tête ; « Récents » liste les derniers posés.

## T10 — Le JUGE (validation à l'aveugle)

1. Nouveau projet, importer uniquement la vidéo **JUGE**, aucune indication, niveau Recettes sans IA → Analyser. Appliquer, exporter.
2. Même chose en IA cloud.
3. Verdict de Philippe, en trois lignes : la recette était-elle celle qu'il aurait voulue ? Qu'est-ce qui manquait ? Qu'est-ce qui était de trop ?
4. Les écarts sont reportés dans les recettes (`app/recettes.py`) et dans les consignes de l'IA (`app/assistant.py`), puis on refait T10.

## Ce qui n'est pas encore là (ne pas tester)

- Flatpak Linux (archive tar.gz seulement), version Android.
- Correction du suivi à la main, plusieurs suivis dans un même plan, effet (halo, feu d'artifice) qui suit la personne : prévus dans une prochaine 0.2.x.
- Catalogue d'effets en ligne (le mécanisme est là, le fichier est vide).
- Doublage avec la voix de la personne elle-même (clonage de voix) : pas encore, la voix de synthèse est une voix toute faite.
- Packs de Goodies autres qu'Aviation et Maison : les genres existent, le dessin détaillé viendra.
- Télémétrie lue dans les fichiers GoPro : remplacée par le profil de vol réglable (T21) ; multicaméra calée par le son : plus tard.

## Comment remonter un KO utile

- Le numéro du point (ex. **T3.4**), ce que vous avez fait, ce qui s'est passé, ce que vous attendiez.
- Le fichier concerné (AV1, SV2…) et, si c'est un export, la vidéo obtenue.
- Outils › Journal des échanges : copier les dernières lignes s'il y a une erreur d'IA, de Drive ou d'export.
