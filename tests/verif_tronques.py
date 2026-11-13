"""Garde-fou G7 : aucun texte tronqué, aucune fenêtre plus grande que l'écran (1024×768), pas de défilement horizontal.

Une fenêtre est montrée à sa taille d'ouverture (bornée à 1024×768) ; on regarde chaque bouton, case et étiquette
visibles : le texte doit tenir dans la place qu'il a (un QPushButton ou une QCheckBox coupe sans prévenir ; une
étiquette sans retour à la ligne aussi). Et le contenu d'une zone qui défile ne doit pas être plus large qu'elle (0.9.56)."""
from PySide6.QtWidgets import (QAbstractButton, QAbstractScrollArea, QApplication, QCheckBox, QLabel, QPushButton, QRadioButton,
                               QScrollArea, QToolButton)
from PySide6.QtCore import Qt

ECRAN = (1024, 768)


def _visible(w, fen):
    return w.isVisibleTo(fen) and w.width() > 4 and w.height() > 4


def tronques(fen, ecran=ECRAN):
    """Les problèmes trouvés dans une fenêtre déjà montrée : [(nature, texte, détail)]."""
    app = QApplication.instance()
    fen.resize(min(fen.width(), ecran[0]), min(fen.height(), ecran[1]))
    for _ in range(3):
        app.processEvents()
    pb = []
    if fen.minimumSizeHint().width() > ecran[0] or fen.minimumSizeHint().height() > ecran[1] + 40:
        pb.append(("fenêtre", fen.windowTitle(), f"taille minimale {fen.minimumSizeHint().width()}×{fen.minimumSizeHint().height()}"))
    for w in fen.findChildren(QAbstractButton):
        if not _visible(w, fen) or isinstance(w, QToolButton):
            continue
        t = w.text().replace("&", "")
        if not t.strip():
            continue
        fm = w.fontMetrics()
        place = w.width() - (w.iconSize().width() + 6 if not w.icon().isNull() else 0)
        place -= 26 if isinstance(w, (QCheckBox, QRadioButton)) else 14
        large = max(fm.horizontalAdvance(x) for x in t.split("\n"))
        if large > place + 2:
            pb.append(("bouton" if isinstance(w, QPushButton) else "case", t, f"{large} px pour {place} px"))
    for w in fen.findChildren(QLabel):
        if not _visible(w, fen) or w.wordWrap() or w.pixmap() is not None and not w.pixmap().isNull():
            continue
        t = w.text()
        if not t.strip() or w.textFormat() == Qt.RichText or "<" in t:
            continue
        large = max(w.fontMetrics().horizontalAdvance(x) for x in t.split("\n"))
        if large > w.width() + 2:
            pb.append(("étiquette", t, f"{large} px pour {w.width()} px"))
    for w in fen.findChildren(QAbstractScrollArea):
        if _visible(w, fen) and w.horizontalScrollBar().isVisible() and w.horizontalScrollBarPolicy() != Qt.ScrollBarAlwaysOn:
            if type(w).__name__ in ("Timeline", "QGraphicsView", "QTableWidget", "QTableView", "QPlainTextEdit", "QTextEdit"):
                continue                                        # la timeline et les tableaux défilent par nature
            pb.append(("défilement horizontal", type(w).__name__, ""))
    # 0.9.56 : un contenu plus large que sa zone de défilement, sans barre horizontale, est coupé à droite sans prévenir
    for w in fen.findChildren(QScrollArea):
        c = w.widget()
        if c is not None and _visible(w, fen) and not w.horizontalScrollBar().isVisible() \
                and c.width() > w.viewport().width() + 2:
            pb.append(("coupé par la zone de défilement", type(c).__name__, f"{c.width()} px pour {w.viewport().width()} px"))
    return pb
