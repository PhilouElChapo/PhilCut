"""Ce qui a servi à créer un fichier par l'IA (0.9.19) : rangé à côté du fichier (« musique.mp3.ia.json »), pour pouvoir
rouvrir l'Atelier IA avec la même phrase, les mêmes paroles, la même durée, et refaire ou modifier la création."""
import json
import os


def chemin_recette(fichier):
    return f"{fichier}.ia.json"


def ecrire(fichier, recette):
    try:
        with open(chemin_recette(fichier), "w", encoding="utf-8") as f:
            json.dump(recette, f, ensure_ascii=False, indent=1)
    except OSError:
        pass


def lire(fichier):
    try:
        with open(chemin_recette(fichier), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return None


def copier(source, cible):
    """Copie le fichier (et sa recette) ; renvoie la cible."""
    import shutil
    shutil.copy2(source, cible)
    if os.path.exists(chemin_recette(source)):
        shutil.copy2(chemin_recette(source), chemin_recette(cible))
    return cible
