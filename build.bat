@echo off
rem Video Muzik Indirici - tek dosyalik exe derleme betigi
rem Gereksinim: Python 3.9+ (tkinter dahil)
rem Kod imzalama sertifikasi bagliysa (Certum SimplySign) exe otomatik imzalanir; yoksa imzasiz kalir.
rem Imzasiz cikmasin istiyorsaniz:  build.bat /imzazorunlu
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller pillow || goto :err
python make_icon.py || goto :err
python -m PyInstaller --noconfirm --onefile --windowed ^
  --name VideoMuzikIndirici ^
  --icon indirici.ico --add-data "indirici.ico;." ^
  --distpath dist --workpath build --specpath build ^
  indirici.pyw || goto :err

set IMZA_EK=
if /i "%~1"=="/imzazorunlu" set IMZA_EK=-Zorunlu
powershell -NoProfile -ExecutionPolicy Bypass -File tools\imzala.ps1 %IMZA_EK% ^
  -Aciklama "Video Muzik Indirici" -Adres "https://github.com/mehmet-cizmeci/video-muzik-indirici" ^
  dist\VideoMuzikIndirici.exe || goto :err

echo.
echo Tamam: dist\VideoMuzikIndirici.exe
exit /b 0
:err
echo Derleme basarisiz oldu.
exit /b 1
