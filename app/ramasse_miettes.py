"""1.1.18 : le ramasse-miettes de Python ne tourne plus que dans le fil de l'interface.

Journal de Philippe (22/11 21h59 et 23h01) : « Windows fatal exception: code 0xc0000374 » (tas corrompu), chaque fois pendant un
« Garbage-collecting » dans le fil de la synchronisation. Python lance son ramasse-miettes dans le fil qui alloue à ce moment :
s'il y libère un objet de Qt (fenêtre, image, minuterie…), Qt est détruit hors de son fil, et le tas se corrompt. Méthode
connue des logiciels Qt en Python (pyqtgraph) : ramasse-miettes automatique coupé, et passage régulier par une minuterie du fil
de l'interface, avec les mêmes seuils que Python.
"""
import gc

_minuterie = None


def _passer():
    seuils, comptes = gc.get_threshold(), gc.get_count()
    gen = -1
    for k in range(3):
        if comptes[k] > seuils[k]:
            gen = k
    if gen >= 0:
        gc.collect(gen)


def installer(app, intervalle_ms=500):
    """Coupe le ramasse-miettes automatique et le fait passer dans le fil de l'interface (toutes les 0,5 s si besoin)."""
    global _minuterie
    from PySide6.QtCore import QTimer
    if _minuterie is not None:
        return _minuterie
    gc.disable()
    _minuterie = QTimer(app)
    _minuterie.timeout.connect(_passer)
    _minuterie.start(intervalle_ms)
    return _minuterie
