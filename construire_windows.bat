@echo off
REM Fabrique PhilCut pour Windows sur ce PC (la fabrication officielle se fait sur GitHub) :
REM    dist\PhilCut\                     (dossier tout-en-un : Python, Qt, OpenCV, FFmpeg dans bin\)
REM    dist\PhilCut_portable.zip         (version portable, rien dans le registre)
REM Prerequis : Python 3.10+, et FFmpeg (ffmpeg.exe + ffprobe.exe, build GPL) copie dans bin\
cd /d "%~dp0"
if not exist bin\ffmpeg.exe (
  echo bin\ffmpeg.exe manquant : telechargez une build GPL de FFmpeg (ex. BtbN ffmpeg-master-latest-win64-gpl)
  echo et copiez ffmpeg.exe et ffprobe.exe dans le dossier bin\ puis relancez.
  pause
  goto :eof
)
python -m venv .venv || goto erreur
.venv\Scripts\pip install -r requirements.txt pyinstaller || goto erreur
.venv\Scripts\python outils_dev\icone.py || goto erreur
.venv\Scripts\pyinstaller --noconfirm --clean --windowed --name PhilCut --icon philcut.ico ^
  --add-data "fonts;fonts" --add-data "langues;langues" --add-data "catalogue;catalogue" --add-binary "bin\ffmpeg.exe;bin" --add-binary "bin\ffprobe.exe;bin" ^
  --collect-submodules app --collect-submodules keyring --collect-submodules truststore --hidden-import PySide6.QtNetwork ^
  --hidden-import PySide6.QtMultimedia --hidden-import PySide6.QtMultimediaWidgets --hidden-import win32ctypes.core ^
  --exclude-module scipy --exclude-module matplotlib --exclude-module pandas --exclude-module tkinter philcut.py || goto erreur
copy LISEZMOI.txt dist\PhilCut\ >nul
copy LICENSE dist\PhilCut\ >nul
echo Version portable...
echo PhilCut portable : parametres, proxys et projets recents ranges dans le dossier "donnees" > dist\PhilCut\portable.txt
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\PhilCut\*' -DestinationPath 'dist\PhilCut_portable.zip'"
del dist\PhilCut\portable.txt
echo.
echo Termine :
echo   dist\PhilCut\PhilCut.exe
echo   dist\PhilCut_portable.zip
goto :eof
:erreur
echo La fabrication a echoue (voir le message ci-dessus).
pause
