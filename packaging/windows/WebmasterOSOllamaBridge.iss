#define AppName "WebmasterOS Ollama Bridge"
#define AppVersion "0.1.0"
#define AppPublisher "WebmasterOS"
#define AppExeName "WebmasterOSOllamaBridge.exe"

#ifndef ProjectRoot
  #define ProjectRoot "..\.."
#endif

#ifndef StageRoot
  #define StageRoot ProjectRoot + "\dist\windows\stage"
#endif

#ifndef InstallerRoot
  #define InstallerRoot ProjectRoot + "\dist\windows\installer"
#endif

[Setup]
AppId={{8C3B6F8B-62B9-42F7-AE38-1048F03D64A1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\WebmasterOS\OllamaBridge
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir={#InstallerRoot}
OutputBaseFilename=WebmasterOSOllamaBridge-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}

[Files]
Source: "{#StageRoot}\WebmasterOSOllamaBridge\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "{#StageRoot}\install-ollama-bridge.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Run Bridge"; Filename: "{app}\{#AppExeName}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\WebmasterOS\OllamaBridge"
