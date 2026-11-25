; Dodown Inno Setup Installer Script
; https://averybeuth.xyz

#ifndef MyAppVersion
  #define MyAppVersion "4.5.11"
#endif
#ifndef MyAppArchitectures
  #define MyAppArchitectures "x64compatible"
#endif

#define MyAppName "Dodown"
#define MyAppPublisher "Avery"
#define MyAppURL "https://averybeuth.xyz"
#define MyAppExeName "Dodown.exe"

[Setup]
AppId={{8F3B92A1-4D6E-4C12-9B87-3E5A6C1D04F2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL=https://github.com/averywsc/downloader/issues
AppUpdatesURL=https://github.com/averywsc/downloader/releases
SourceDir=..
DefaultDirName={autopf}\{#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed={#MyAppArchitectures}
ArchitecturesInstallIn64BitMode={#MyAppArchitectures}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
PrivilegesRequired=lowest
ChangesEnvironment=yes
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=Dodown-v{#MyAppVersion}-Windows-Setup
SetupIconFile=app/assets/installer_logo.ico
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist/Dodown.dist/{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist/Dodown.dist/*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\Dodown.torrent"; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Dodown.m3u8"; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Dodown.m3u"; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Dodown.mpd"; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.torrent\OpenWithProgids"; ValueType: none; ValueName: "Dodown.torrent"; Flags: dontcreatekey uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.m3u8\OpenWithProgids"; ValueType: none; ValueName: "Dodown.m3u8"; Flags: dontcreatekey uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.m3u\OpenWithProgids"; ValueType: none; ValueName: "Dodown.m3u"; Flags: dontcreatekey uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\.mpd\OpenWithProgids"; ValueType: none; ValueName: "Dodown.mpd"; Flags: dontcreatekey uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\dodown"; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\magnet"; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\ed2k"; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\ftp"; Flags: dontcreatekey uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\ftps"; Flags: dontcreatekey uninsdeletekey

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\Dodown"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
