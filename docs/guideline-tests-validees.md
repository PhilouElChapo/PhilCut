# Fiches de test validées par Philippe

Fiches retirées de la feuille de test le 14 novembre 2026 (tests de Philippe, 21 h 12), gardées ici pour mémoire.

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

## T9 — Projets, synchro, préférences, mises à jour

1. Enregistrer (Ctrl+S) : fichier `.philcut` + vignette ; il apparaît dans les projets récents de l'Accueil avec la date.
2. Fermer PhilCut, déplacer le dossier des rushes, rouvrir le projet : les rushes sont retrouvés par leur empreinte ou signalés « introuvables » sans planter ; proxys refaits en arrière-plan.
3. Sur le **deuxième poste** (même emplacement de synchro) : l'Accueil propose « Sur « pharmacie », 1 projet était ouvert : … Reprendre ».
4. Préférences : chaque onglet s'ouvre ; changer thème clair → demande de relance ; barre personnalisée (clic droit : icône seule / nom seul / taille ; Personnaliser : ordre, séparateurs) ; volet complet → icônes → masqué (F4) ; export / import des préférences (avec et sans phrase secrète).
5. Mises à jour : Aide › Vérifier. Quand une 0.1.(x+1) est publiée par GitHub, la proposition apparaît sur l'Accueil ; téléchargement, puis installation seulement après confirmation.
6. Packs (0.2) : Préférences › IA locale, cocher « Détourage léger » (5 Mo) puis « Détourage précis » ; effet Halo et feu d'artifice derrière la personne possibles ensuite, depuis la version portable.
7. Clefs IA (0.2) : saisir les clefs Claude et Gemini, fermer PhilCut, ouvrir `donnees\parametres.json` de la portable avec le Bloc-notes : **aucune clef n'y figure**. Rouvrir PhilCut : les clefs sont toujours là (coffre de Windows). Une 0.1 qui avait des clefs en clair : elles disparaissent du fichier au premier démarrage de la 0.2, sans être perdues.
8. Comptes (0.2) : relier Google Drive, OneDrive et Dropbox : la page de connexion affiche « PhilCut » (et non PhilPDF), puis le compte apparaît dans PhilCut.

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

## T83 — 0.9.68 : fenêtres non bloquantes, certificats, histoire sans voix

1. Séquence IA : « Fabriquer les plans manquants » ; pendant le calcul, cliquer dans la timeline : PhilCut répond. « Réduire (suivi dans la barre du bas) » : la fenêtre disparaît, la barre du bas suit ; « Afficher la fenêtre » la rouvre.
2. Même essai avec Atelier de logo (générer puis Fermer) et la publication YouTube (Fermer pendant l'envoi) : l'envoi continue.
3. Séquence IA avec Kling (fal.ai) : plus d'erreur CERTIFICATE_VERIFY_FAILED ; le prix affiché est 0,112 $/s ; le plan reçu n'a pas de son.
4. Séquence IA, « Répliques » › « Aucune voix : personne ne parle », moteur Gemini : les personnages ne parlent pas ; monté sur la timeline, le plan est muet.
5. (0.9.69) « Répliques » › « Voix du moteur vidéo » avec Kling : le prix passe à 0,168 $/s ; une réplique écrite (« Hélène : Bonjour. ») est dite par le personnage dans le plan reçu ; montée, le son du plan est gardé. Revenir à « Voix de ce poste » : le prix redescend, le plan fabriqué est muet et la réplique est posée sur la piste Voix.

## T78 — 0.9.63 : Fabrique musique, « à la manière de », voix, passage

1. Fabrique IA › Musique › Fabrique musique, ligne Phrase › « Style « à la manière de »… » : taper « metallic » : Metallica, Iron Maiden, Gojira… apparaissent. Famille « Musiques de film, de série, de jeu » : Einaudi, Göransson, Hans Zimmer… Taper un nom absent : « Utiliser « … » » l'ajoute à la phrase.
2. Ligne Voix › « À la manière de… » › « Chanter à la manière d'un chanteur, d'un groupe… » : « chanté à la manière de … » s'ajoute ; la consigne anglaise ne contient que la description de la voix.
3. Ligne Voix › « Décrire la voix d'un morceau de ce poste… » : une chanson avec musique ; choisir 20 à 30 s où l'on chante, « Garder ce passage » ; après la séparation, la ligne bleue « Voix décrite d'après … » (ex. voix de femme, léger vibrato) ; la consigne anglaise la reprend ; « Ne plus utiliser cette voix décrite » la retire.
4. S'inspirer d'un morceau › Chercher en ligne : Audionautix, « calm » : 30 résultats, puis « Plus de résultats » : 60. Choisir un morceau sans le télécharger : « S'inspirer de ce morceau » est actif ; cliquer : il se télécharge puis la fenêtre du passage s'ouvre.
5. Garder un passage (ex. 0:30 à 1:10) : l'analyse dit « (de 0:30 à 1:10) » ; morceau libre : « Partir de ce morceau » réorchestre ce passage.

## T77 — 0.9.62 : dossiers des projets et des rushes sur le cloud

1. Préférences › Comptes et synchro › Rôle de chaque compte : « Dossier des projets » › Choisir… : la fenêtre est centrée et entière ; elle s'ouvre dans /PhilCut avec le bandeau « Le dossier /PhilCut/Projets n'existe pas encore… Le créer maintenant ». Cliquer : il est créé et ouvert.
2. Changer le dossier (ex. /PhilCut/Projets 2026), OK : la barre du bas indique « ✓ Dossiers prêts — pCloud : /PhilCut/Projets 2026 ; … ». Vérifier sur le site de pCloud.
3. Fichier › Enregistrer le projet vers un emplacement : sur pCloud, le projet arrive bien comme FICHIER dans le dossier (pas de dossier portant le nom du projet).
4. Comptes et synchro, sous « Synchroniser aussi les mots de passe et clefs » : l'état en vert (« ✓ Phrase secrète gardée… Indice : … Partagés : Clef Claude, Clef Gemini… Dernier envoi : … »). Si la case n'était pas cochée : la cocher demande la phrase (avec l'indice) tout de suite ; Annuler la décoche.
5. « Changer la phrase ou l'indice… » : changer seulement l'indice (la phrase actuelle dans les trois cases) ; l'état affiche le nouvel indice. Sur l'autre PC, l'indice apparaît quand la phrase est demandée.

## T76 — 0.9.61 : consignes écrites dans votre langue, anglais visible

1. Plan de liaison (clic droit sur un plan › Plan de liaison avec le plan suivant…) : choisir une proposition ; la consigne anglaise apparaît en bas et sa traduction française au-dessus (quelques secondes).
2. Ecrire dans la case du haut : « la caméra s'élève au-dessus du village » : l'anglais se met à jour tout seul ; « ✓ Traduit en anglais ».
3. Corriger un mot de l'anglais à la main : « Traduction corrigée à la main » ; fabriquer : c'est votre anglais qui part.
4. Séquence de personnages : « Rédiger la consigne » : l'anglais et sa traduction ; écrire en français, l'anglais suit.
5. Fabrique › Image : taper une phrase en français : l'anglais s'affiche dessous en direct ; avec « à la manière de … », la description du style y est ajoutée.
6. Tampons IA et Musique IA (« Améliorer avec l'IA ») : les deux cases.

## T71 — 0.9.56 : plan de liaison intelligent

1. Deux rushes de lieux différents l'un après l'autre dans la timeline. Clic droit sur le premier › « Plan de liaison avec le plan suivant… » : la fenêtre ne bloque pas le film ; les deux images (dernière de A, première de B) s'affichent avec la ligne des mesures.
2. Lire les trois propositions ; en choisir une autre : la consigne change. Me dire si la direction de la caméra mesurée est juste.
3. « Analyser avec l'IA de ce poste » (avec un modèle de vision installé) : trois propositions qui parlent de ce que montrent vraiment les images ? Puis « Analyser avec l'IA cloud… » : le coût est demandé avant.
4. « Transition 3D (gratuite) » › Fabriquer le plan : la progression avance ; regarder le plan, puis « Poser entre les deux plans » : la suite du film recule d'autant, marqueurs et titres compris. Edition › Annuler : tout revient d'un coup.
5. Mettre un vide entre deux plans ; clic droit dans le vide › « Remplir ce vide par un plan de liaison… ». Si le plan tient dans le vide, rien d'autre ne bouge.
6. « Gemini Omni » (si crédits) : la case d'accord est obligatoire ; le prix maximal est demandé avant. Le plan doit commencer exactement sur l'image A et finir exactement sur l'image B : me le confirmer.
7. Aide › Comment faire… › « Lier deux rushes par un plan de passage » : ✓ faisable ; « Montrez-moi » ouvre le clic droit avec la bonne ligne surlignée.

## T70 — 0.9.55 : garde-fous, guides en ligne, petit écran

1. Fenêtre de PhilCut réduite à environ 1024 de large : la barre de lecture sous l'aperçu passe sur deux lignes, rien n'est coupé, tout reste cliquable.
2. Aide › Comment faire… : « Echanger ses rushes entre ses postes par pCloud » est marqué « Nouveau » ; l'ouvrir : le badge disparaît ensuite. « Montrez-moi » ouvre Edition › Préférences…, puis Outils › Synchroniser maintenant.
3. Séquence IA : changer le moteur (ce poste, Gemini, Flow) : la phrase grise sous le choix explique ce que chacun garde du personnage.
4. Provoquer une erreur (par exemple une recherche de musique sans réseau) : le message « ✕ … » n'est jamais vide.

## T69 — 0.9.53 : séparer voix, musique et bruits

1. Edition › Préférences › IA locale : installer « Séparer voix, musique et bruits » (environ 170 Mo).
2. Un rush avec une voix et de la musique ou du vent : clic droit sur le plan › « Séparer voix, musique et bruits… ». La fenêtre ne bloque pas le film.
3. « Les trois pistes », puis « Séparer » : la progression avance par morceaux de 7,8 s. Noter le temps pour une minute de son.
4. Ecouter Voix, Musique, Bruits : la voix doit être nette ; me dire ce qui reste de musique dans la voix, et si le vent part bien dans « Bruits ».
5. « Poser dans le film » : trois pistes sous le plan, au même endroit, son d'origine coupé (🔇). Lecture : le film sonne comme avant. Edition › Annuler : tout revient d'un coup.
6. « Retirer la voix » sur une chanson (Fabrique IA › Musique › Séparer… › un fichier) : « Ajouter aux médias du projet ».
7. Aide › Comment faire… › « Retirer la voix d'une musique » : ✓ faisable, « Montrez-moi » ouvre le bon menu.

## T68 — 0.9.52 : guides pas à pas

1. Aide › « Comment faire… (guides pas à pas) » (en tête, en gras) : une fenêtre s'ouvre à droite du film. La liste est par ordre alphabétique ; ✓ faisable, ◐ en partie, … pas encore.
2. Taper « voix » dans la recherche : les guides sur la voix restent. Ouvrir « Couper des images dans un rush ».
3. Avec un plan dans la timeline : « Montrez-moi » de l'étape 2 ouvre le menu du clic droit avec « Couper ici » surligné ; celui de l'étape 4 ouvre Montage › Pistes et passage choisi avec « Partie jaune : supprimer ce passage » surligné.
4. Guide « Suivre une personne » : cliquer le plan dans la timeline coche l'étape 1 toute seule ; poser le suivi coche l'étape 2.
5. Pendant ce temps, travailler dans le film : la fenêtre des guides ne bloque rien.
6. Bouton IA › « Comment faire… » ; et écrire « comment retirer la voix d'une musique ? » puis Comprendre : le bon guide s'ouvre.
7. Séquence IA › personnage › « Images du personnage… » : la case « Je certifie… » est obligatoire avant de choisir les images.

## T67 — 0.9.51 : plus de plantage dans Dites-le en clair

1. Niveau « IA de ce poste » dans Dites-le en clair. Cliquer sur une action : pendant « Je lis votre demande… », les autres boutons sont grisés.
2. Ecrire une phrase et cliquer plusieurs fois très vite sur « Comprendre », fermer la fenêtre pendant que l'IA réfléchit, la rouvrir : PhilCut ne doit jamais se fermer.
3. Outils › Journal des plantages et erreurs : pas de ligne « Fatal » ni « ERREUR » liée à ces essais.
4. Deux plans séparés par un vide : clic droit dans le vide › « Refermer ce vide » : le second plan se colle au premier ; Edition › Annuler le remet.
5. Atelier IA (Fabrique IA › Vidéo, ou effet sur la partie en jaune) : « Créer », puis cliquer dans la timeline, déplacer la ligne rouge : tout répond. Fermer l'Atelier pendant le calcul : la barre du bas propose « Afficher l'Atelier ».
6. Refaire le tri sur le rush filmé en marchant (clic droit sur sa vignette › Trier) : pastille T attendue ; survol : ligne « Mesures ». Me donner les chiffres de « tremblement » d'un plan stable et d'un plan en marchant.

## T66 — 0.9.50 : plusieurs chaînes YouTube, effets sur une image d'exemple

1. Nouveau projet vide, volet Effets : « Préparation d'une image d'exemple… », puis les vignettes s'animent sur un paysage (soleil, montagnes, mer). Le texte sous la grille dit que c'est un exemple.
2. Glisser un plan vidéo dans la timeline : les vignettes se refont sur ce plan.
3. Exporter › Publier : la chaîne déjà reliée apparaît dans la liste « Chaîne ». « Ajouter une chaîne… » : le navigateur demande le compte (et, pour un compte avec chaîne de marque, la chaîne). Accepter : la nouvelle chaîne apparaît, choisie.
4. Si le navigateur affiche une alerte sur une autorisation « voir votre compte YouTube » : c'est la lecture du nom de la chaîne, ajoutée en 0.9.50. Si Google la refuse, PhilCut demande le nom de la chaîne à la main.
5. Choisir une chaîne puis « Publier sur YouTube » : la confirmation nomme la chaîne. « Délier » ne retire que la chaîne choisie.
6. Outils › « Journal des plantages et erreurs… » : la fenêtre s'ouvre (au moins les lignes « démarrage »). Après un plantage, le relancer : la fenêtre de récupération propose « Voir le journal des plantages » ; « Copier » puis me le coller.

## T65 — 0.9.49 : tri des rushes

1. Importer quelques vrais rushes, dont si possible : une copie d'un même fichier (renommée), un plan flou, un plan pris en marchant, un plan venté, un plan avec un long silence. A la fin de l'import, la barre du bas propose « Trier les rushes » (30 s) ; rien n'est calculé avant votre clic.
2. « Trier les rushes » : progression dans la barre du bas, puis « N rush(es) à revoir… ». Pastilles en haut à gauche des vignettes : D doublon, F flou, T tremblé, S son raté, … silences. Survoler une vignette : la phrase explique chaque pastille.
3. « Ne montrer qu'eux » : la recherche des médias se remplit avec « à revoir ». Essayer aussi « flou », « doublon », « son ».
4. Un panoramique régulier ne doit pas être marqué T ; un plan net ne doit pas être marqué F. Me dire chaque erreur (nom du rush, ce qui est faux) : je règlerai les seuils.
5. Relancer le tri : il est immédiat (déjà fait). Préférences › Import › Tri des rushes : « Le faire tout seul » puis importer : le tri part seul. « Ne pas le proposer » : plus de question.
6. Clic droit sur les médias › « Trier les rushes… », bouton IA › « Trier les rushes (doublons, flou, tremblé, son) », et la phrase « repère les rushes ratés » : même chose.

## T64 — 0.9.48 : bouton IA, Dites-le en clair élargi, marqueurs

1. Ouvrir un projet avec quelques plans. A droite de la barre d'outils, à côté de « Volet » : le bouton « IA ». Clic droit sur la barre › Personnaliser la barre : même en retirant des boutons, « IA » reste.
2. Clic sur « IA » : la fenêtre « Dites-le en clair » montre des boutons d'actions (ordre alphabétique). « Étalonnage auto de toute la séquence » : la phrase s'écrit, le plan s'affiche avec une case ; rien n'a changé dans le film.
3. « Faire » : « Lecture des plans : … % » défile, puis les plans sont étalonnés. Clic droit sur un plan › Étalonnage : les réglages sont là. Edition › Annuler : tout revient d'un coup.
4. « Mêmes couleurs partout (comme le plan 1) », puis « Toute la séquence un peu plus chaude » : même chose.
5. « Ranger les rushes par date », « par type » : l'ordre des médias à gauche change ; Annuler le remet.
6. « Un marqueur à chaque plan » : des fanions bleus sur la règle, numérotés au survol. Avec une musique : « Marqueurs sur les temps forts de la musique ».
7. Touche M : un marqueur à la ligne rouge. Clic sur un fanion : la ligne rouge y va. Clic droit : Renommer, Supprimer, Supprimer tous.
8. Écrire soi-même : « marqueur « discours » à 12 s », « plus lumineux sur le plan 3 », « range les rushes par nom ».

## T63 — 0.9.47 : musiques libres d'Audionautix

1. Bouton Musique › Chercher en ligne : la liste des sources est par ordre alphabétique et contient « Audionautix : musiques libres de Jason Shaw (crédit à citer) ». Aucun bouton yt-dlp pour cette source.
2. Chercher « jazz », puis « piano », puis « calm » : des titres de Jason Shaw, le genre en album. La première recherche lit le site (quelques secondes), les suivantes sont immédiates. Si rien n'arrive alors que le site marche dans le navigateur : me le dire (la page du site a changé).
3. Choisir un titre : la note orange parle de la licence CC BY 4.0 et du crédit ; la case « libre de droits » est cochée. Écouter, puis télécharger : le MP3 arrive avec, à côté, un fichier « .credit.txt ».
4. Poser ce morceau dans un film, puis Publier : la description contient « … — Music by audionautix.com (Jason Shaw), CC BY 4.0 ».

## T62 — 0.9.46 : menus rangés, IA partagées entre logiciels PhilFactory

1. Menu Montage : cinq sous-menus (Image du plan, Montage automatique, Pistes et passage choisi (partie jaune), Son, Textes et habillage), entrées par ordre alphabétique ; plus d'« Atelier IA » ici.
2. Menu Fabrique IA : Image, Logo intro et vignette, Musique, Vidéo, puis « Créations à refaire ou à calculer… ». Clic droit sur l'aperçu › Fabrique IA : le même menu. Bouton Musique › « Fabrique IA › Musique… » : le sous-menu Musique.
3. Au démarrage, si vous avez déjà des IA locales : l'Accueil propose « Choisir le dossier commun… ». Fenêtre : explication, dossier proposé (à côté des portables : C:\Prog\Windows\IA PhilFactory), case « Partager mes IA… ». « Ranger mes IA ici » : progression, puis le bilan (fichiers rangés, doubles libérés).
4. Vérifier dans l'Explorateur : les modèles sont dans « IA PhilFactory\modeles », le fichier « philfactory-ia.json » à sa racine ; le dossier « ia\modeles » de PhilCut est vide. La musique et les effets IA marchent comme avant.
5. Préférences › IA locale : la ligne dit où sont rangés les modèles ; « Dossier commun des IA PhilFactory… » rouvre la fenêtre.
6. Débrancher le disque du dossier commun (ou le renommer), relancer : l'Accueil le dit et propose « Le retrouver… ».

## T61 — 0.9.45 : la suite des résultats YouTube

1. Tampons vidéo › Chercher en ligne, YouTube, une recherche : 30 résultats.
2. Descendre en bas de la liste : « Recherche de la suite sur YouTube… », puis 30 de plus ; la liste reste à l'endroit où vous étiez. Le bouton « 30 résultats de plus » fait la même chose.
3. Quand YouTube n'a plus rien, le bouton disparaît.

## T60 — 0.9.44 : mise à jour comme PhilPDF, recherche exacte, musique, logo et vignette

1. Mise à jour : la fenêtre n'a plus le bouton de réduction de Windows ; « Réduire », la croix ou Echap la rangent dans la barre du bas, le téléchargement continue ; « Afficher » la rouvre.
2. Tampons vidéo › Chercher en ligne : « tonton flingur » ; les résultats suivent vos mots exacts. « Vidéos et Shorts » : 30 résultats (20 vidéos puis 10 Shorts), le message le dit ; « Vidéos » : 30 vidéos.
3. Fabrique musique › « Choisir un morceau… » › « Chercher en ligne… » : chercher, télécharger, « S'inspirer de ce morceau » : la fenêtre se ferme et l'analyse du morceau démarre.
4. Fabrique musique › Voix de référence › « Garder seulement la voix d'un morceau de ce poste… » : question « De qui est cette voix ? », puis séparation (modèle « Voix seule d'un morceau » à installer d'abord, sinon PhilCut dit où). Ecouter le fichier « _voix.wav » obtenu avant de créer.
5. Fabrique › Logo, intro et vignette : « Mon logo… » en premier ; « Vignette de la vidéo (miniature YouTube)… » : explication en haut, « Votre logo » (choisir, Atelier de logo…, coin), bouton principal « Utiliser comme vignette de la vidéo ».
6. Outils › Publier : la vignette est montrée, « Composer la vignette… » ; à l'envoi, la vignette part avec la vidéo (ou le message dit pourquoi YouTube la refuse).

