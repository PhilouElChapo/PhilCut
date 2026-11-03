; Installateur PhilCut (Inno Setup) : installation pour l'utilisateur courant, sans droits administrateur.
; Aucune association de fichiers video ici ; les projets .philcut s'associent dans PhilCut (Preferences), reversible.
#ifndef Version
  #define Version "0.1"
#endif

[Setup]
AppId={{7E2C7B7A-5C3B-4F1E-9D5A-0C1A2B3C4D5E}
AppName=PhilCut
AppVersion={#Version}
AppPublisher=PhilouElChapo
DefaultDirName={localappdata}\Programs\PhilCut
DefaultGroupName=PhilCut
PrivilegesRequired=lowest
OutputBaseFilename=PhilCut_Setup
SetupIconFile=philcut.ico
UninstallDisplayIcon={app}\PhilCut.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=auto
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=yes

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[CustomMessages]
en.Bureau=Create a desktop icon
fr.Bureau=Créer une icône sur le Bureau
en.Lancer=Launch PhilCut
fr.Lancer=Lancer PhilCut

[Tasks]
Name: "bureau"; Description: "{cm:Bureau}"; Flags: unchecked

[Files]
Source: "dist\PhilCut\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "LISEZMOI.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\PhilCut"; Filename: "{app}\PhilCut.exe"
Name: "{userdesktop}\PhilCut"; Filename: "{app}\PhilCut.exe"; Tasks: bureau

[Run]
Filename: "{app}\PhilCut.exe"; Description: "{cm:Lancer}"; Flags: nowait postinstall skipifsilent
