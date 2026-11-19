#define AppName "Ordner-Organigramm"
#define AppExe "Organigramm.exe"
#define ProgramDir AddBackslash(SourcePath) + "..\dist\Ordner-Organigramm"
#dim VersionParts[4]
#define FileVersion GetVersionComponents(ProgramDir + "\" + AppExe, VersionParts[0], VersionParts[1], VersionParts[2], VersionParts[3])
#if FileVersion == ""
  #error "Programm fehlt. Zuerst bauen.bat ausführen."
#endif
#define AppVersion Str(VersionParts[0]) + "." + Str(VersionParts[1]) + "." + Str(VersionParts[2])

[Setup]
AppId={{6DFF9578-C054-4BA2-B52E-1CBC949361F8}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#FileVersion}
AppPublisher=Ordner-Organigramm
AppPublisherURL=https://github.com/zerox80/organigramm_python
AppUpdatesURL=https://github.com/zerox80/organigramm_python/releases/latest
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\organigramm.ico
UninstallDisplayIcon={app}\{#AppExe}
WizardStyle=modern dynamic windows11
OutputDir=..\dist
OutputBaseFilename={#AppName}-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; Flags: unchecked

[Files]
Source: "{#ProgramDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{#AppName} starten"; Flags: postinstall nowait skipifsilent
