; Установщик для Windows. Собирается из tools/build.py, версия и папка
; со сборкой приходят ключами /D — чтобы номер версии жил в одном месте.
;
; Ставим для текущего пользователя: прав администратора не требуется,
; и это честнее для программы, которая держит свои данные в профиле.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\Transcriber-cpu"
#endif
#ifndef Variant
  #define Variant "cpu"
#endif

[Setup]
AppId={{6F2B9E64-7E4C-4E7E-9A6E-0D4C2F1A8C11}
AppName=Transcriber
AppVersion={#AppVersion}
AppPublisher=Transcriber
DefaultDirName={autopf}\Transcriber
DefaultGroupName=Transcriber
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
#ifndef OutputName
  #define OutputName "Transcriber-" + AppVersion + "-win64-" + Variant + "-setup"
#endif
OutputBaseFilename={#OutputName}
SetupIconFile=..\app\icons\build\app.ico
UninstallDisplayIcon={app}\Transcriber-{#Variant}.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Transcriber"; Filename: "{app}\Transcriber-{#Variant}.exe"
Name: "{autodesktop}\Transcriber"; Filename: "{app}\Transcriber-{#Variant}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Transcriber-{#Variant}.exe"; Description: "{cm:LaunchProgram,Transcriber}"; Flags: nowait postinstall skipifsilent
