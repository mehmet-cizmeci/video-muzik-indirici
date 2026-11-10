@echo off
rem Video Muzik Indirici - tek dosyalik exe derleme betigi
rem Gereksinim: Python 3.9+ (pip ile PySide6, PyInstaller ve Pillow kurulur)
rem Kod imzalama sertifikasi bagliysa exe otomatik imzalanir; yoksa imzasiz kalir (bkz. docs\IMZALAMA.md).
rem Imzasiz cikmasin istiyorsaniz:  build.bat /imzazorunlu
cd /d "%~dp0"
rem Python baslaticisi (py) varsa onu kullan; yoksa PATH'teki python
set PY=python
where py >nul 2>nul && set PY=py -3
%PY% -m pip install --upgrade pyside6 pyinstaller pillow || goto :err
%PY% make_icon.py || goto :err
%PY% -m PyInstaller --noconfirm --onefile --windowed ^
  --name VideoMuzikIndirici ^
  --icon "%~dp0indirici.ico" --add-data "%~dp0indirici.ico;." --add-data "%~dp0indirici.png;." ^
  --exclude-module tkinter --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick ^
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.Qt3DCore --exclude-module PySide6.QtPdf ^
  --distpath dist --workpath build --specpath build ^
  indirici.pyw || goto :err

set IMZA_EK=
if /i "%~1"=="/imzazorunlu" set IMZA_EK=-Zorunlu
powershell -NoProfile -ExecutionPolicy Bypass -File tools\imzala.ps1 %IMZA_EK% ^
  -Aciklama "Video Muzik Indirici" -Adres "https://github.com/mehmet-cizmeci/video-muzik-indirici" ^
  dist\VideoMuzikIndirici.exe || goto :err

rem guncelleyicinin dogrulamasi icin SHA-256 ozeti (GitHub Release'e exe ile birlikte yuklenir)
powershell -NoProfile -Command "(Get-FileHash dist\VideoMuzikIndirici.exe -Algorithm SHA256).Hash.ToLower() + '  VideoMuzikIndirici.exe' | Set-Content -Encoding ascii dist\VideoMuzikIndirici.exe.sha256" || goto :err

echo.
echo Tamam: dist\VideoMuzikIndirici.exe
exit /b 0
:err
echo Derleme basarisiz oldu.
exit /b 1
