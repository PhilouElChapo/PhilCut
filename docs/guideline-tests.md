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

## T8 — Export

1. Exporter le projet aviation en **YouTube** (16:9) : encodeur Nvidia NVENC proposé par défaut ; durée de l'export ; le fichier se lit dans VLC et dans le lecteur Windows ; poids raisonnable.
2. Exporter le même en **Insta 9:16** (changer le format du projet via une recette 9:16 ou un nouveau projet) : plans horizontaux avec fond flou.
3. **WhatsApp** et **Ecran LED vertical** : poids et définition conformes.
4. Faire échouer volontairement NVENC (encodeur absent sur un autre poste) : PhilCut retombe sur x264 et le note dans le journal.
5. « Déposer sur le Drive » après export : le fichier arrive dans `PhilCut/Exports` de l'emplacement de synchro.

## T85 — 0.9.72 : personnage fidèle, plans plus longs, rallonger un rush

Il faut une clef fal.ai avec un peu de crédit, et une clef Gemini.

1. Séquence IA, onglet « Personnages et lieux » : cliquer la ligne du personnage, « Images du personnage… » (ton personnage IA, de face), puis « Fiche personnage… » : la planche (face, trois quarts, profil, en pied) s'affiche avant d'être gardée ; la colonne Images dit « + fiche ».
2. Moteur « Kling O3 Référence : personnage fidèle (fal) » : l'explication change, la ligne « Crédit fal.ai restant » s'affiche ; « Recharger… » ouvre la page de facturation de fal.ai.
3. Onglet Plans : durée jusqu'à 15 s ; « Enchaîner » coché d'office (sauf le premier plan) ; pas de défilement horizontal.
4. « Fabriquer les plans manquants » : le prix compte la fiche et l'image d'arrivée (0,04 $ chacune). Le personnage ressemble-t-il à son image, du début à la fin du plan ? Plus de traversée de table ? Le plan 2 démarre-t-il exactement où finit le plan 1 ?
5. Un rush (filmé ou IA) : clic droit sur le plan › « Prolonger ce plan… » › « Prolongé par l'IA cloud, fidèle », 8 s, « Suite » : « elle ouvre l'ordinateur et sourit » ; le prix est demandé ; regarder, poser.
6. Tampons vidéo, onglet « Tampons IA » : pendant la création, « Réduire » apparaît en bas ; la fenêtre se range, la barre du bas suit, « Voir le résultat » la rouvre.
7. Tampons, « Ma bibliothèque » : glisser une icône sur une autre (vers la droite, vers la gauche) : elle prend sa place, rien ne disparaît.
8. « Faire parler » (image + son) : sans cocher la case du visage, le message en bas dit de la cocher ; cochée, le bouton s'active.

## T84 — 0.9.70 : Séquence IA, gestes cohérents et personnage fidèle

1. Reprendre l'histoire d'Hélène : dans la liste des plans, les plans à deux actions portent ⚠ ; sous « Ce qu'on voit », l'avertissement et « Couper en deux plans ». Essayer « Une action par plan » : chaque plan double devient deux plans (durées partagées).
2. Le personnage a une image (onglet Personnages et lieux) : case « Image de départ par Gemini » cochée ; le prix compte 0,04 $ par plan.
3. Fabriquer un plan avec Gemini Omni : l'onglet Plans montre l'image de départ composée ; le personnage ressemble-t-il à son image ? les gestes sont-ils cohérents (plus de traversée de table) ?
4. Nouvelle histoire, « Découper en plans (IA cloud) » : chaque plan n'a qu'une action.

## T82 — 0.9.67 : vidéo de narration d'après ce qui est dit

Il faut une clef Gemini ou fal.ai (et fal.ai pour le présentateur), et un modèle de voix (Préférences › IA locale) pour la transcription.

1. Enregistrez (ou posez) 30 s à 1 min de voix sur la piste Voix, qui raconte quelque chose de concret.
2. Clic droit sur la voix › « Illustrer ce qui est dit (vidéo de narration)… » : la ligne bleue nomme la piste et la durée.
3. « Ecouter et découper » : la barre du bas suit ; le tableau montre les idées (2 à 8 s), le texte entier, sans rien de coupé.
4. Essayer « Idées d'images avec l'IA » : les images proposées deviennent concrètes ; en modifier une à la main.
5. Cocher « Un présentateur… » : il est proposé au début et à la fin ; « Le créer avec Gemini », regarder la vignette ; cocher la case du visage.
6. Choisir le moteur (Omni 360p d'abord), lire le prix détaillé, « Fabriquer les plans », confirmer ; fermer la fenêtre, attendre « Voir le résultat ».
7. Cliquer chaque ligne : les images collent-elles aux mots ? Le présentateur dit-il bien sa phrase ?
8. « Poser sous les mots » : chaque plan tombe sous ses mots, au-dessus du film, muet. Lecture. Edition › Annuler.
9. Rouvrir par le clic droit : la narration est reprise.

## T81 — 0.9.66 : clip de groupe d'après une chanson

Il faut une clef Gemini et/ou fal.ai avec un peu de crédit ; « Séparer voix, musique et bruits » installé (conseillé).

1. Fabrique IA › Musique › Fabrique musique : un morceau chanté, ligne « Clip vidéo » › « Clip : concert sur scène », créer, poser. La fenêtre « Clip de groupe d'après la chanson » s'ouvre seule sur ce morceau.
2. « Ecouter le morceau » : la barre du bas suit ; la bande de couleurs montre intro, couplets, refrains… Vérifier à l'oreille que les refrains tombent au bon endroit (survol : les heures).
3. Le groupe : les rôles correspondent-ils au morceau (chant, batterie, basse…) ? Changer une description.
4. Les plans : plans longs au calme, courts au refrain ; les lignes grises du 2e refrain « reprend n ». Décocher puis recocher « Un refrain qui revient… » : le nombre de plans à fabriquer et le prix changent. Essayer « Idées avec l'IA ».
5. Choisir le moteur (essayer d'abord Omni 360p, le moins cher), cocher « Musiciens inventés », « Fabriquer les plans », lire le prix détaillé, confirmer. Fermer la fenêtre : la barre du bas suit, « Voir le résultat » à la fin.
6. Cliquer chaque ligne : l'aperçu montre le plan ; les plans chantés ont les lèvres sur la voix.
7. « Poser le clip sous la chanson » : les plans sont posés sur une piste vidéo libre, chaque coupe sur une mesure, muets. Lecture : le clip suit la chanson. Edition › Annuler.
8. Clic droit sur la chanson › « Créer le clip du groupe d'après ce morceau… » : la fenêtre se rouvre avec le même clip.
9. Refaire avec « Clip : tourné ailleurs » et « Dessin animé ».

## T80 — 0.9.65 : faire parler un personnage sur votre son

Il faut une clef fal.ai (Préférences › Assistant et IA, « Clef fal.ai ») avec un peu de crédit.

1. Posez une voix de 5 à 10 s sur la piste Voix, sous un plan où l'on voit un visage (un plan IA ou un personnage inventé).
2. Clic droit sur le plan › « Faire parler ce plan sur le son dessous… » : la ligne bleue nomme la voix (et la musique s'il y en a) ; le coût s'affiche (LatentSync : 0,20 $).
3. « Faire parler » reste gris tant que la case du visage n'est pas cochée. Cocher, « Faire parler », confirmer le prix. Fermer la fenêtre : la barre du bas suit ; « Voir le résultat » à la fin.
4. Regarder l'aperçu : les lèvres suivent-elles la voix ? « Poser à la place du plan » : le plan est remplacé, muet ; on entend la voix de la piste Voix. Edition › Annuler revient au plan d'origine.
5. Fabrique IA › Vidéo › « Personnage qui parle (une image et votre son)… » : partie en jaune sur la voix, « L'image du film à la ligne rouge » (ou une image), OmniHuman, 720p ; écrire « parle calmement en souriant » (l'anglais suit) ; faire parler, poser au-dessus du film.
6. Avec une chanson (musique et voix) : cocher « Isoler d'abord la voix » et comparer.

## T79 — 0.9.64 : fermer une fenêtre pendant une création

1. Fabrique IA › Musique › Fabrique musique : « Créer la musique », puis « Fermer » tout de suite. La fenêtre disparaît ; la barre du bas montre « Fabrique musique : création du morceau » avec la progression et « Afficher la fenêtre ». Continuer à monter : PhilCut n'est pas bloqué.
2. Cliquer « Afficher la fenêtre » : la Fabrique revient avec sa barre. La refermer.
3. A la fin : « ✓ Fabrique musique… » et « Voir le résultat » : la fenêtre revient avec le morceau à écouter, « Poser sous la vidéo ».
4. Plus tard (après la disparition du bouton) : clic sur la barre du bas › Centre d'activité : la ligne a « Voir le résultat ».
5. Même essai avec le plan de liaison (« Fabriquer le plan »), « Continuer avec ma voix » et « Séparer voix, musique et bruits ».

## T75 — 0.9.60 : police du titre de la vignette

1. Outils › Vignette de la vidéo : groupe Style › « Police du titre » : « Celle du kit (Anton) », puis Anton, Bebas Neue, Nunito, Poppins, un trait, puis les polices de votre PC ; chaque nom est écrit dans sa police.
2. Choisir une autre police : le titre change aussitôt dans l'aperçu (contour et ombre gardés).
3. Changer de kit : la première ligne indique la police du nouveau kit ; si une police est choisie, elle reste.
4. Poser la vignette, la rouvrir : la police choisie est toujours là.

## T74 — 0.9.59 : modèle « Continuer avec ma voix » visible et installable

1. Après la mise à jour, Edition › Préférences › IA locale : le groupe « Continuer avec ma voix » apparaît (environ 1,6 Go).
2. Ou directement : clic droit sur un plan › « Continuer avec cette voix… » › « Installer le modèle… » : le téléchargement démarre (barre du bas), le bouton se grise, le texte l'explique ; à la fin, le message disparaît et « Fabriquer la voix » devient possible (après la case d'accord et le texte).
3. Même chose dans « Séparer voix, musique et bruits » si le modèle n'y est pas.

## T73 — 0.9.58 : projets et rushes dans vos clouds

1. Edition › Préférences › Comptes et synchro : vos comptes (Google Drive, pCloud…) ; groupe « Rôle de chaque compte » : réglages = Google Drive (par exemple), projets = pCloud, rushes = pCloud. OK. Rouvrir : la liste des comptes affiche le rôle de chacun entre crochets.
2. Un projet ouvert : Fichier › « Enregistrer le projet vers un emplacement (cloud, NAS)… » : la fenêtre s'ouvre sur pCloud (★ en tête), dans /PhilCut/Projets (créé s'il manque). Essayer « Nouveau dossier ». Enregistrer : l'onglet porte ☁ ; la barre du bas montre l'envoi.
3. Modifier le projet, Ctrl+S : « ✓ Projet renvoyé sur pCloud ». Vérifier dans pCloud (site web) que la date du fichier a changé.
4. Proposition après l'enregistrement : cocher « Les originaux de N rush(es) sur pCloud » (décoché d'office) ; l'envoi se suit dans l'encart.
5. Sur l'autre PC : Accueil (☁ pCloud : /PhilCut/Projets) ou Fichier › « Ouvrir un projet depuis un emplacement… ». Médias absents : Fichier › Médias introuvables : « Télécharger la copie légère (… Mo) » / « Télécharger l'original (… Go) » selon ce qui a été déposé ; le plan se met à jour.
6. Conflit : modifier le même projet sur les deux PC sans rouvrir, enregistrer sur l'un puis sur l'autre : la question « Remplacer celle du cloud / Garder les deux / Plus tard » apparaît.
7. Fichier › « Importer des rushes depuis un emplacement… » : en choisir plusieurs (Ctrl + clic) ; ils arrivent dans Vidéos/PhilCut — pCloud et sont importés.
8. Exporter une vidéo, puis Outils › « Envoyer une vidéo exportée vers un emplacement… » : dossier /PhilCut/Exports proposé.
9. Vérifier que les copies légères ne se téléchargent plus toutes seules sur l'autre PC (seulement l'index).

## T72 — 0.9.57 : continuer avec ma voix

1. Edition › Préférences › IA locale : installer « Continuer avec ma voix » (environ 1,6 Go). La progression s'affiche dans la barre du bas.
2. Mettre un rush où vous parlez. Placer la ligne rouge juste après une de vos phrases. Clic droit sur le plan › « Continuer avec cette voix… » : la fenêtre ne bloque pas ; l'extrait proposé = les 12 dernières secondes avant la ligne rouge. « ▶ Ecouter l'extrait » : est-ce bien votre voix, sans trop de bruit ?
3. Sans cocher l'accord, « Fabriquer la voix » reste grisé. Cocher, écrire « Et maintenant, passons à autre chose. », Fabriquer : la barre avance phrase par phrase. Noter le temps de calcul.
4. « ▶ Ecouter » : me dire si la voix vous ressemble (timbre, accent, débit), et si le niveau est le même que l'extrait.
5. Essayer l'expressivité plus haute, et une ponctuation différente (« Et maintenant… passons à autre chose ! ») : la voix change-t-elle ?
6. Rush avec musique derrière : cocher « Isoler d'abord la voix » (si la séparation est installée) et comparer.
7. « Poser dans le film » : la phrase est sur la piste Voix à la ligne rouge ; Edition › Annuler la retire d'un coup.
8. Après un plan de liaison (T71) : bouton « Une phrase avec ma voix sur ce plan… » : la voix est posée au début du plan de liaison.
9. Aide › Comment faire… › « Continuer un commentaire avec la même voix » : ✓ faisable, « Montrez-moi » ouvre le clic droit sur la bonne ligne.

## T59 — 0.9.43 : Fabrique rangée, plan par ce poste, pCloud par WebDAV

1. Menu Fabrique : trois sous-menus (Vidéo, Musique, Logo, intro et vignette), chacun avec une phrase d'explication en tête, puis « Créations à refaire ou à calculer… ». Menu Aide : plus de « Guide de test ».
2. Fabrique › Vidéo › Plan vidéo à partir d'une phrase : le premier choix est « IA de ce poste » (coché si le modèle vidéo est installé), puis Gemini, puis Google Flow. Sujet, « Fabriquer » : la barre du bas suit le calcul ; à la fin, le plan s'affiche pour être regardé, puis inséré, gardé ou jeté.
3. Fabrique › Vidéo › Histoire en plusieurs plans : texte plus grand, l'essentiel en gras ; « Vidéo » propose d'abord ce poste, Gemini, puis Flow en dernier ; « Nouvelle histoire… » en bas à gauche.
4. Atelier IA (Effet IA sur le film) : liste de gauche par ordre alphabétique, noms longs à la ligne, pas de barre de défilement horizontale.
5. Préférences › Comptes et emplacements › Ajouter › pCloud (WebDAV) : adresse déjà remplie (https://ewebdav.pcloud.com), adresse e-mail et mot de passe pCloud, « Tester la connexion ». Puis, dans Projets entre vos appareils, choisir ce compte pour les rushes et son dossier d'échange (T58, étapes 3 à 6).

## T58 — 0.9.42 : pCloud, kDrive et lieu d'échange des rushes

1. Préférences › Comptes et emplacements › Ajouter › pCloud : « Autoriser l'accès à pCloud… ». Le navigateur s'ouvre sur pCloud ; après « Allow », la page PhilCut dit « C'est fait » et PhilCut annonce « Connexion réussie : PhilCut accède au pCloud de … ».
2. « Tester la connexion » : nombre d'éléments à la racine de votre pCloud.
3. Préférences › Comptes et synchro › Projets entre vos appareils : « Envoyer les copies légères des rushes sur » = le compte pCloud ; « Dossier d'échange des rushes » › « Choisir… » : parcourir pCloud, choisir (ou taper) un dossier, par exemple /Rushes PhilCut.
4. Enregistrer un projet et accepter la copie légère d'une vidéo : la barre du bas montre « Copies légères des rushes avec pCloud : envoi et réception… » ; dans pCloud, le fichier apparaît dans /Rushes PhilCut/Medias.
5. Sur un autre poste avec les mêmes réglages : la copie arrive, et le projet s'ouvre avec elle si l'original manque.
6. Fichier › Espace PhilCut sur le Drive : la copie est listée avec « (pCloud) » ; la supprimer la met dans la corbeille de pCloud.
7. kDrive (sans compte payant, à valider plus tard) : ajouter un compte kDrive, coller l'adresse du kDrive et un jeton d'API (Manager › Développeur › Jetons d'API, portée drive), « Tester la connexion ».

## T57 — 0.9.41 : mise à jour sans plantage

1. Avec un projet modifié non enregistré, lancer la mise à jour suivante puis « Installer et redémarrer » : PhilCut demande s'il faut enregistrer ; « Annuler » laisse PhilCut ouvert et la fenêtre de mise à jour revient.
2. Recommencer et accepter : PhilCut se ferme, l'installation se fait, PhilCut redémarre seul dans la nouvelle version.
3. Ouvrir l'Observateur d'événements de Windows (ou « Historique de fiabilité ») : aucun nouveau « APPCRASH PhilCut.exe ».
4. Préférences : changer le thème, accepter de relancer : même fermeture propre, PhilCut revient avec le nouveau thème.

## T56 — 0.9.40 : retours des essais du 9 novembre

1. **Fenêtres** : Atelier IA › Dessin animé (vidéo) sur un plan, « Créer » : à l'arrivée du résultat, la fenêtre reste dans l'écran (le contenu défile).
2. **Plan IA cloud** : Fabrique › plan vidéo, Gemini Omni Flash 360p : pendant l'attente, « … calcule le plan : N s écoulées » ; à la fin, message « Plan IA rangé dans … Vidéos\PhilCut\Plans IA » et « Ouvrir le dossier ». Clic droit sur le plan › « Reprendre la création » : la Fabrique se rouvre avec la consigne, la durée et le modèle.
3. **Omni 1.2** : modèle « Gemini Omni 1.2 Flash 720p (nouveau) » : le plan arrive (avec la 1.1 si la 1.2 n'est pas ouverte à votre clef).
4. **Aide Flow** : Fabrique › plan vidéo › Google Flow : l'aide décrit les réglages, les crédits et l'« Approuver ».
5. **Musique en ligne** : bouton « Mettre à jour yt-dlp » ; YouTube Music : artiste et durée sous chaque titre ; écouter : « Lecture : … » et un curseur pour aller au passage voulu ; changer de morceau : le bouton redevient « Écouter ». Archives libres : la case « libre » reste décochée, avertissement orange sur la licence annoncée.

## T55 — 0.9.38 : recettes refaites avec Gemini, Claude pour écrire

1. **Image** : Atelier IA › un style d'image sur la ligne rouge, poser. Renommer le fichier créé (dossier des créations), rouvrir le projet : message « création(s) IA à refaire ». Liste : « Sur ce poste (gratuit) » et « Gemini (votre clef, payant) » ; choisir Gemini : fenêtre « Créations payantes » avec le total ; puis avant / après.
2. **Recommencer** la même ligne : le résultat déjà fait est repris (« Reprendre le résultat déjà fait (gratuit) »), aucune nouvelle dépense.
3. **Réplique** : une réplique dite (Atelier IA), fichier renommé : la liste propose sur ce poste ou Gemini.
4. **Fabrique musique** : la liste « Claude (cloud, le meilleur pour écrire) / Gemini / IA locale » à côté d'« Améliorer avec l'IA » et des paroles ; le coût annoncé nomme bien l'IA choisie.

## T54 — 0.9.37 : fabrique musique, musique en ligne, créations à refaire

1. **Ouvrir** : Fabrique › « Fabrique musique… » (ou bouton Musique). **Attendu** : sections Style et ambiance, Fiche musicale, S'inspirer d'un morceau, Voix de référence, Consigne envoyée au moteur.
2. **Styles** : famille « Classique, opéra, sacré » : Symphonie, Opéra, Chant grégorien… La consigne en bas change à chaque réglage (tempo, tonalité « ré mineur », mesure).
3. **À la manière de** : écrire « chanté à la manière de Frank Sinatra » : ligne bleue avec la description ; la consigne ne contient ni « Sinatra » ni « chanté ».
4. **Améliorer** : « Améliorer avec l'IA » (locale, puis cloud : coût demandé) : consigne réécrite, cochée, modifiable.
5. **Créer** : « Créer la musique » : étape, temps écoulé et restant, explication quand la barre est pleine ; écouter, garder un passage, « Poser sous la vidéo ».
6. **S'inspirer** : « Choisir un morceau… » (un MP3 à vous) : résumé (tempo, tonalité, mesure, son) et l'alerte orange. « Partir de ce morceau » reste grisé tant que « Ce morceau est libre de droits ou à moi… » n'est pas déclaré ; ensuite réorchestration possible (curseur Proche / Libre).
7. **Voix de référence** : choisir un enregistrement : PhilCut demande « C'est ma voix » ou « Une personne d'accord » ; annuler = pas de voix de référence.
8. **Musique en ligne** : Fabrique › « Musique en ligne… » : texte sur les droits ; YouTube Music, YouTube, archives libres ; installer yt-dlp si demandé ; chercher « Dies irae », écouter (double-clic), télécharger (confirmation la première fois), « Poser dans le film ». Le MP3 a son titre, son artiste et la source en commentaire.
9. **Créations à refaire** : déplacer un morceau créé par la fabrique, rouvrir le projet : message « création(s) IA à refaire » ; la liste propose « Sur ce poste (gratuit) » ; lancer, comparer avant / après, « Prendre le nouveau ».

## T53 — 0.9.36 : éléments animés

1. **Galerie** : bouton Goodies. Familles « ✶ Réactions et emoji », « ✶ Flèches et repères animés », « ✶ Vlog et réseaux », « ✶ Météo et nature », « ✶ Fête animée », « ✶ Formes animées ». **Attendu** : cliquer un élément, il s'anime dans le cadre de droite.
2. **Recherche** : taper « flèche », puis « soleil » : la liste se réduit.
3. **Favoris et récents** : « ☆ Ajouter aux favoris » ; famille « ★ Mes favoris » : il y est. Poser un élément : il apparaît dans « ⟲ Utilisés récemment ».
4. **Poser** : « Flèche courbe qui se trace » : elle se dessine, puis reste. Glisser, tirer un coin, suivre une personne comme un Goodie.
5. **Inspecteur** : changer la couleur (pastilles ou nuancier), « Couleurs d'origine » ; Animation « En boucle / S'arrête à la fin / Disparaît à la fin » ; Vitesse.
6. **Export** : le film exporté montre l'élément, fluide et net.
7. **Plan gris** : renommer le dossier d'un rush, rouvrir le projet ; double-clic sur le plan gris : « Où est ce fichier ? » s'ouvre directement sur lui. Ne rien faire : le plan reste gris ; réenregistrer, remettre le dossier, rouvrir : tout est comme au début.

## T52 — 0.9.35 : nouveaux effets et projets entre appareils

1. **Effets** : un plan, Effets : familles Rétro, Glitch, Lentille, Ouvertures, Cinématique, Mouvement, Lumières. Cliquer « Super 8 », « Ouvrir en cercle », « Lucioles », « Néon rose » : l'aperçu tourne. **Attendu** : effet visible, ouverture qui progresse sur la durée du plan.
2. **Export** : poser 2 effets de familles différentes, exporter : la barre avance, le film les montre. Le journal indique « carte graphique » ou « version simplifiée ».
3. **Lueur** : sur une vidéo sombre, effet Lueur : **Attendu** : plus de noirs violets.
4. **Média déplacé** : enregistrer un projet, renommer le dossier d'un rush, rouvrir. **Attendu** : message « introuvable(s) », plan grisé « Introuvable ici » ; « Où sont-ils ? » › « Où est ce fichier ? » : le plan revient, les autres du même dossier aussi.
5. **Autre poste** : copier le projet sur un autre PC où les rushs sont dans Vidéos ou Téléchargements : **Attendu** : retrouvés sans rien faire.
6. **Conflit** : ouvrir le même projet (dossier synchronisé) sur deux postes, enregistrer sur l'un puis sur l'autre. **Attendu** : message « modifié aussi sur … », « Voir les versions » montre l'autre.
7. **Drive** : lieu de synchronisation choisi, enregistrer : fenêtre « Retrouver ce projet sur vos autres appareils » ; cocher la copie légère : la barre avance, `PhilCut/Medias/…_720p.mp4` apparaît.
8. **Espace Drive** : Fichier › « Espace PhilCut sur le Drive… » : catégories, cases pré-cochées pour ce qui est ancien ou plus utilisé, réglages jamais cochés ; décocher, « Supprimer la sélection » : confirmation, puis suppression.
9. **Préférences** : Comptes et synchro › Projets entre vos appareils : les 4 réglages, note orange sur la transparence.

## T51 — 0.9.33 : séquence IA

1. **Ouvrir** : Fabrique › « Séquence IA… » (ou Fabrique › Plan généré par IA › « Plusieurs plans… »). **Attendu** : trois onglets Histoire, Personnages et lieux, Plans.
2. **Découper** : écrire l'histoire des deux pilotes (l'un à la manière d'Alain Delon, l'autre de Simon Templar), « Découper en plans (IA cloud) ». **Attendu** : personnages, lieu, 4 à 8 plans avec cadrage et répliques.
3. **Styles** : onglet 2, « Choisir le style… » ; manière de parler « Selon le style (Froid…) » et « (Gentleman…) ».
4. **Consigne** : onglet 3, « Rédiger la consigne » : en anglais, « Character A / B », aucun nom ; « Améliorer » garde les fiches des personnages.
5. **Image de départ** : ajouter des photos au lieu, « Composer avec Gemini » : vignette ; confirmation avant l'envoi.
6. **Flow** : moteur Google Flow, « Copier pour Flow… » : Flow et le dossier des images s'ouvrent ; la barre d'attente compte ; la vidéo téléchargée s'attache au plan (✓) et se regarde.
7. **Cloud** : moteur Gemini Omni : prix annoncé, confirmation, avancement par plan.
8. **Monter** : « Monter la séquence à la ligne rouge » : plans dans l'ordre, répliques sur la piste Voix, musique ; Ctrl+Z revient. Rouvrir : la séquence est reprise.
9. **Vignette** : zone verte « Pistons OK / Soupapes NON » : la ligne « Pastilles » affiche ✓ et ✗.

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
