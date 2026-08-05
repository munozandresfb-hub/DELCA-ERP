# Building DELCA ERP Installer

## Prerequisites
1. [Inno Setup 6](https://jrsoftware.org/isdl.php) installed
2. PyInstaller EXE already built (`dist/DELCA_ERP.exe` or `dist/DELCA_ERP/`)

## Build EXE
```powershell
& ".venv\Scripts\python.exe" -m PyInstaller --name "DELCA_ERP" --windowed --add-data ".env;." --add-data "src;src" main.py
```

## Build Installer
Open `installer.iss` in Inno Setup Compiler and press Compile, or run:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

The installer will be created in `dist/DELCA_ERP_Setup_2.0.0.exe`.

## Output
- `dist/DELCA_ERP_Setup_2.0.0.exe` — Standalone Windows installer
- Installs to `C:\Program Files\DELCA ERP\`
- Creates `data/`, `backups/`, `logs/` directories
- Desktop shortcut (optional)
- Uninstaller via Windows Programs & Features
