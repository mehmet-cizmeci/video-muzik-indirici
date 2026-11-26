# Belgelerdeki ekran görüntülerini üretir: gerçek arayüz, örnek verilerle (indirme yapılmaz).
# Kullanım (depo kökünde):  python tools/ekran-goruntuleri.py          -> koyu tema + diğer pencereler
#                           python tools/ekran-goruntuleri.py light    -> açık tema ana ekran
# Çıktı: docs/img/*.png. Ayarlar geçici klasörde tutulur; kullanıcının kendi ayarlarına dokunulmaz.
import os, sys, tempfile, re
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "img")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="vmi-ekran-")
sys.path.insert(0, REPO)

import core, ui_qt
from ui_qt import *  # noqa
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

ui_qt.find_exe = lambda n: rf"C:\araclar\{n}.exe"
ui_qt.MainWindow._tools_ready = lambda self, j: None
core.Downloader.add = lambda self, j: None
THEME = sys.argv[1] if len(sys.argv) > 1 else "dark"

def thumb_bytes():
    return core.fetch_bytes("https://i.ytimg.com/vi/aqz-KE-bpKQ/maxresdefault.jpg")

def latest_notes():
    log = open(os.path.join(REPO, "CHANGELOG.md"), encoding="utf-8").read()
    parts = re.findall(r"^## \[([^\]]+)\][^\n]*\n(.*?)(?=^## \[|\Z)", log, re.S | re.M)
    (ver, notes), prev = parts[0], (parts[1][0] if len(parts) > 1 else "")
    return ver, prev, notes.strip()


app = ui_qt.create_app()
s = core.load_settings()
s["theme"] = THEME
s["folder"] = r"D:\İndirilenler\Video Müzik"
core.save_settings(s)
win = ui_qt.MainWindow()
win.dl.active_count = lambda: 3
win.ytdlp_ver = "2026.11.18"
win.resize(1320, 960)
win.show()
win.folder_edit.setText(r"D:\İndirilenler\Video Müzik")

URL = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"
win.url_edit.blockSignals(True)
win.url_edit.setPlainText(URL)
win.url_edit.blockSignals(False)

def fill():
    win.preview_token = 1
    win._on_probe(1, True, {
        "url": URL, "title": "Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film",
        "is_playlist": False, "playlist_title": "", "count": 0, "uploader": "Blender",
        "duration": 635, "views": 23500000, "date": "20141110", "heights": [2160, 1440, 1080, 720],
        "site": "Youtube", "thumbnail": "", "has_video": True})
    win._on_thumb(1, True, thumb_bytes())

    base = dict(win._current_opts())
    def job(title, status, pct="", speed="", eta="", **o):
        opts = dict(base); opts.update(o)
        j = win._enqueue("https://www.youtube.com/watch?v=x", opts, title)
        j.status, j.percent, j.speed, j.eta = status, pct, speed, eta
        win._refresh_row(j)
    job("Me at the zoo", "Tamamlandı", "100%", type="Sadece Ses", aformat="mp3", aquality="320 kbps")
    job("Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film", "Dönüştürülüyor", "64%", "", "00:38")
    job("Doğa belgeseli - Kuşların göçü", "İndiriliyor", "37%", "6.12MiB/s", "00:52")
    job("Ders anlatımı: Basit elektrik devreleri", "Bekliyor")
    job("Çocuk şarkıları derlemesi", "Tamamlandı", "100%")
    win.refresh_status()

def shot_main():
    fill()
    QTimer.singleShot(600, lambda: grab_main())

def grab_main():
    win.grab().save(os.path.join(OUT, f"ana-ekran-{THEME}.png"))
    if THEME != "dark":
        os._exit(0); return
    # önizleme kartı
    card = win.stack.parentWidget()
    while card is not None and not isinstance(card, ui_qt.Card):
        card = card.parentWidget()
    card.grab().save(os.path.join(OUT, "onizleme.png"))
    # dönüştürücü
    dlg = ui_qt.ConverterDialog(win)
    rows = [
        ("Çocuk şarkıları - 1. bölüm 🎵 ｜ Eğlenceli [Xy12AbC].webm", "Tamamlandı", "100", "VP9 1920x1080 60fps → H.264 720p 30fps"),
        ("Doğa belgeseli ： Kuşlar.mkv", "Dönüştürülüyor", "58", "AV1 1920x1080 30fps → H.264 720p 30fps"),
        ("Tatil 2025.mp4", "Kopyalanıyor", "81", "Zaten uyumlu → kopyalanıyor"),
        ("Masal saati ⧸ Uyku öncesi.mp4", "Bekliyor", "", ""),
        ("Okul gösterisi.mov", "Bekliyor", "", ""),
    ]
    for name, st, pct, info in rows:
        j = core.ConvJob(os.path.join(r"D:\Videolar", name), {})
        j.status, j.percent, j.info = st, pct, info
        dlg.jobs[j.id] = j
        dlg._add_row(j)
    dlg._refresh_state()
    dlg.show()
    QTimer.singleShot(500, lambda: (dlg.grab().save(os.path.join(OUT, "donusturucu.png")), dlg.hide(), shot_settings()))

def shot_settings():
    d = ui_qt.SettingsDialog(win)
    d.show()
    QTimer.singleShot(400, lambda: (d.grab().save(os.path.join(OUT, "ayarlar.png")), d.hide(), shot_update()))

def shot_update():
    ver, prev, notes = latest_notes()
    ui_qt.APP_VERSION = prev
    ui_qt.FROZEN = True
    d = ui_qt.UpdateDialog(win, {"version": ver, "notes": notes, "page": ""})
    d.show()
    QTimer.singleShot(400, lambda: (d.grab().save(os.path.join(OUT, "guncelleme.png")), os._exit(0)))

QTimer.singleShot(800, shot_main)
app.exec()
