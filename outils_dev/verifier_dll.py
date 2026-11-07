"""Vérifie qu'un moteur Windows n'a besoin d'aucune bibliothèque absente d'un Windows neuf (0.9.12).

python outils_dev/verifier_dll.py <dossier> : liste les DLL demandées par chaque .exe/.dll du dossier ; échoue si l'une
d'elles n'est ni dans le dossier, ni une DLL de Windows (System32 d'un Windows neuf, sans Visual C++ ni MinGW).
Cas vécu : acestep.cpp compilé par MinGW demandait libgomp-1.dll, libgcc_s_seh-1.dll, libstdc++-6.dll,
libwinpthread-1.dll, absentes chez l'utilisateur (le moteur s'arrêtait avec le code 3221225781)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app.diagnostic_ia import imports_pe   # noqa: E402

# présentes sur tout Windows 10/11 (pas besoin de les livrer)
SYSTEME = {"kernel32.dll", "user32.dll", "gdi32.dll", "advapi32.dll", "shell32.dll", "ole32.dll", "oleaut32.dll", "ws2_32.dll",
           "bcrypt.dll", "crypt32.dll", "ntdll.dll", "shlwapi.dll", "comdlg32.dll", "comctl32.dll", "winmm.dll", "version.dll",
           "dbghelp.dll", "psapi.dll", "setupapi.dll", "cfgmgr32.dll", "dxgi.dll", "d3d11.dll", "d3d12.dll", "dxcore.dll", "iphlpapi.dll",
           "secur32.dll", "userenv.dll", "rpcrt4.dll", "msvcrt.dll", "ucrtbase.dll", "powrprof.dll", "imm32.dll", "winhttp.dll",
           "wininet.dll", "normaliz.dll", "mswsock.dll", "vulkan-1.dll", "nvcuda.dll", "opengl32.dll", "dwmapi.dll", "uxtheme.dll"}


def verifier(dossier):
    fichiers = []
    for base, _s, noms in os.walk(dossier):
        fichiers += [os.path.join(base, n) for n in noms if n.lower().endswith((".exe", ".dll"))]
    livres = {os.path.basename(f).lower() for f in fichiers}
    manque = {}
    for f in fichiers:
        demandes = imports_pe(f)
        print(f"{os.path.basename(f)} : {', '.join(demandes)}")
        for d in demandes:
            dl = d.lower()
            if dl.startswith(("api-ms-", "ext-ms-")) or dl in SYSTEME or dl in livres:
                continue
            manque.setdefault(d, []).append(os.path.basename(f))
    for d, qui in manque.items():
        print(f"::error title=DLL non livrée::{d} demandée par {', '.join(sorted(set(qui)))}")
    return 1 if manque else 0


if __name__ == "__main__":
    sys.exit(verifier(sys.argv[1]))
