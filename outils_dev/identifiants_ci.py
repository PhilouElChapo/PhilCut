"""Fabrication GitHub : ecrit app/identifiants.py a partir des secrets du depot PhilCut (jamais dans le code public).

Secrets attendus (Settings > Secrets and variables > Actions du depot PhilouElChapo/PhilCut) :
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, ONEDRIVE_CLIENT_ID, DROPBOX_CLIENT_ID, BOX_CLIENT_ID, BOX_CLIENT_SECRET.
Un secret absent = ce Drive n'est pas propose « en direct » (le dossier du Drive de bureau reste utilisable)."""
import os

ids = {}
for cle, env in (("gdrive", "GOOGLE"), ("onedrive", "ONEDRIVE"), ("dropbox", "DROPBOX"), ("box", "BOX")):
    i = "".join(os.environ.get(env + "_CLIENT_ID", "").split())
    s = "".join(os.environ.get(env + "_CLIENT_SECRET", "").split())
    if i:
        ids[cle] = {"id": i, "secret": s or None}
    print(f"::notice title=Identifiants::{cle} : " + ("identifiant present" if i else "absent") + (" + secret" if s else ""))
chemin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "identifiants.py")
with open(chemin, "w", encoding="utf-8") as f:
    f.write("IDENTIFIANTS = " + repr(ids) + "\n")
