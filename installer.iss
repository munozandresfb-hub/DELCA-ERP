; DELCA ERP — Inno Setup Installer
; Build with: ISCC.exe installer.iss
; Requires Inno Setup 6+ (https://jrsoftware.org/isdl.php)

#define MyAppName "DELCA ERP"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "DELCA"
#define MyAppURL "https://delca.com"
#define MyAppExeName "DELCA_ERP.exe"

[Setup]
AppId={{B8A3C8D0-4E7F-4A9C-9F2D-1E5F3B7C8D9E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={pf}\DELCA ERP
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=DELCA_ERP_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin
DisableProgramGroupPage=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Dirs]
Name: "{app}\data"; Permissions: users-modify
Name: "{app}\backups"; Permissions: users-modify
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\docs"; Permissions: users-modify

[Files]
; PyInstaller single-folder deployment
Source: "dist\DELCA_ERP\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; .env configuration (only if not exists)
Source: ".env"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion

; Documentation
Source: "CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "Stack.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "Database_er.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "project_structure.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "business_rules.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "BUILD.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Preserve data on uninstall by default (comment out to clean)
; Filename: "{cmd}"; Parameters: "/c rmdir /s /q ""{app}\data"""; Flags: runhidden
; Filename: "{cmd}"; Parameters: "/c rmdir /s /q ""{app}\backups"""; Flags: runhidden

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create a default .env pointing to {app}\data if none exists
    if not FileExists(ExpandConstant('{app}\.env')) then
    begin
      SaveStringToFile(
        ExpandConstant('{app}\.env'),
        '# DELCA ERP Configuration' + #13#10 +
        '# Created by installer on ' +
        GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':') + #13#10 +
        #13#10 +
        '# Database (SQLite)' + #13#10 +
        'DATABASE_URL=sqlite:///{app}\data\delca.db' + #13#10 +
        #13#10 +
        '# Paths' + #13#10 +
        'LOG_DIR={app}\logs' + #13#10 +
        'BACKUP_DIR={app}\backups' + #13#10 +
        'DATA_DIR={app}\data' + #13#10,
        False
      );
    end;
  end;
end;
