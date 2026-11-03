"""Fabrique philcut.ico (et philcut.png) a partir du logo SVG de app/icones.py : rien a dessiner a la main."""
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtCore import QSize
QGuiApplication([])
from app.icones import logo
racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
images = []
for t in (16, 24, 32, 48, 64, 128, 256):
    px = logo(t).pixmap(t, t)
    images.append(px.toImage())
    if t == 256:
        px.save(os.path.join(racine, "philcut.png"))
# ICO : conteneur simple de PNG (accepte par Windows depuis Vista)
from PIL import Image
pil = []
for img in images:
    img = img.convertToFormat(QImage.Format_ARGB32)
    b = img.bits().tobytes()
    pil.append(Image.frombytes("RGBA", (img.width(), img.height()), b, "raw", "BGRA"))
pil[-1].save(os.path.join(racine, "philcut.ico"), format="ICO", sizes=[(i.width, i.height) for i in pil], append_images=pil[:-1])
print("philcut.ico et philcut.png ecrits")
