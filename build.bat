@echo off
rem Video Muzik Indirici - tek dosyalik exe derleme betigi
rem Gereksinim: Python 3.9+ (tkinter dahil)
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller pillow || goto :err
python make_icon.py || goto :err
python -m PyInstaller --noconfirm --onefile --windowed ^
  --name VideoMuzikIndirici ^
  --icon indirici.ico --add-data "indirici.ico;." ^
  --distpath dist --workpath build --specpath build ^
  indirici.pyw || goto :err
echo.
echo Tamam: dist\VideoMuzikIndirici.exe
exit /b 0
:err
echo Derleme basarisiz oldu.
exit /b 1
