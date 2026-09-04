@echo off
setlocal
cd /d "%~dp0"
py -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name DDBeekeeperClassVita ^
  --icon "assets\image.ico" ^
  --paths patcher ^
  --hidden-import dd_beekeeper_vita_patcher ^
  --add-data "patcher\translations.json;patcher" ^
  --add-data "assets\darkest_dungeon_logo.png;assets" ^
  --add-data "assets\image.ico;assets" ^
  gui\dd_beekeeper_vita_gui.py
if errorlevel 1 exit /b %errorlevel%
echo.
echo Built: dist\DDBeekeeperClassVita.exe
