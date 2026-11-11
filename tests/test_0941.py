"""0.9.41 : fermeture pour mise à jour ou redémarrage sans plantage (sortie directe après lancement)."""
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["PHILCUT_SANS_RESEAU"] = "1"
os.environ["PHILCUT_TEST_SORTIE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from app.fenetre import Fenetre

f = Fenetre([])
for ed in f.editeurs():
    ed.projet.modifie = False
appels = []
ok = f.quitter_pour_maj(lambda: appels.append("lance"))
assert ok and appels == ["lance"], (ok, appels)
assert os.environ["PHILCUT_TEST_SORTIE"] == "appelee"

# annulation : rien n'est lancé
os.environ["PHILCUT_TEST_SORTIE"] = "1"
f2 = Fenetre([])
f2._quitter_malgre = lambda en_cours: False
class T:
    def isRunning(self): return True
    def stopper(self): pass
    def wait(self, ms): return True
f2.taches.append(T())
appels.clear()
assert f2.quitter_pour_maj(lambda: appels.append("x")) is False and not appels
assert getattr(f2, "_apres_fermeture", None) is None

src = open(os.path.join(os.path.dirname(__file__), "..", "app", "mise_a_jour.py"), encoding="utf-8").read()
assert "/CLOSEAPPLICATIONS" not in src and "goto attente" in src
print("OK")
