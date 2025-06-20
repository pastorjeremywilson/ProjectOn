; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "ProjectOn"
#define MyAppVersion "1.7.1"
#define MyAppPublisher "Wilson's Widgets"
#define MyAppExeName "ProjectOn.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".pro"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt
#define ResourceLocation "C:\Users\pasto\Desktop\output\ProjectOn\_internal"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{0169236A-0685-4EB2-85F1-98E78ADBD784}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
ChangesAssociations=yes
DisableProgramGroupPage=yes
LicenseFile=C:\Users\pasto\Desktop\output\ProjectOn\_internal\resources\gpl-3.0.rtf
SourceDir={#ResourceLocation}\resources
; Uncomment the following line to run in non administrative install mode (install for current user only.)
;PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=C:\Users\pasto\Desktop\output\ProjectOn\installer
OutputBaseFilename=Setup Projecton v.{#MyAppVersion}
SetupIconFile=C:\Users\pasto\Desktop\output\ProjectOn\_internal\resources\logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

WizardImageFile={#ResourceLocation}\resources\branding\install_image_large.bmp
WizardSmallImageFile = {#ResourceLocation}\resources\branding\install_image_small.bmp

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\Users\pasto\Desktop\output\ProjectOn\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\pasto\Desktop\output\ProjectOn\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\Users\pasto\Desktop\output\ProjectOn\_internal\README.html"; DestDir: "{app}\_internal"; Flags: isreadme
Source: "C:\Users\pasto\Desktop\output\ProjectOn\_internal\resources\defaults\data\*"; DestDir: "{userappdata}\ProjectOn\data\"; Flags: createallsubdirs recursesubdirs onlyifdoesntexist uninsneveruninstall
Source: "C:\Users\pasto\Desktop\output\ProjectOn\_internal\resources\defaults\localConfig.json"; DestDir: "{userappdata}\ProjectOn\"; Flags: onlyifdoesntexist uninsneveruninstall
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Registry]
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".myp"; ValueData: ""
Root: HKCR; Subkey: ".pro"; ValueData: "{#MyAppName}"; Flags: uninsdeletevalue; ValueType: string; ValueName: ""
Root: HKCR; Subkey: "{#MyAppName}"; ValueData: "Program {#MyAppName}"; Flags: uninsdeletekey;  ValueType: string; ValueName: ""
Root: HKCR; Subkey: "{#MyAppName}\DefaultIcon"; ValueData: "{app}\{#MyAppExeName},0";  ValueType: string; ValueName: ""
Root: HKCR; Subkey: "{#MyAppName}\shell\open\command"; ValueData: """{app}\{#MyAppExeName}"" ""%1""";  ValueType: string; ValueName: ""

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

