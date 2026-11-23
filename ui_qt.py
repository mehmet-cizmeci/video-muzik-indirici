# -*- coding: utf-8 -*-
"""Video Müzik İndirici - modern arayüz (PySide6 / Qt 6)."""
import os
import queue
import subprocess
import sys
import threading
import time
import webbrowser

from PySide6.QtCore import QRect, QRectF, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import (QAction, QColor, QFont, QFontDatabase, QGuiApplication, QIcon, QKeySequence,
                           QPainter, QPainterPath, QPixmap, QShortcut)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog,
                               QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
                               QSizePolicy, QSlider, QSpinBox, QSplitter, QStackedWidget, QStyledItemDelegate,
                               QTableWidget, QTableWidgetItem, QTextBrowser, QToolButton, QVBoxLayout, QWidget)

import core
from core import (APP_NAME, APP_URL, APP_VERSION, AUDIO_FORMATS, AUDIO_QUALITIES, BIN_DIR, COMPAT_MODES, CONFIG_DIR,
                  CONVERT_RESOLUTIONS, DEFAULT_DIR, DEFAULTS, FPS_OPTIONS, FINAL, FROZEN, LOG_FILE, QUEUE_FILE, RESOLUTIONS, TYPES, UPDATE_INTERVAL,
                  VIDEO_FORMATS, Downloader, Job, find_exe, load_settings, parse_urls, save_settings)

RES_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
AUDIO_EXT = {".mp3", ".m4a", ".opus", ".flac", ".wav", ".ogg", ".aac"}

# ----------------------------------------------------------------- tema
THEMES = {
    "dark": dict(bg="#0b1020", card="#121a2e", card2="#18223b", border="#253151", text="#e8ebf4",
                 muted="#8c95ae", input="#0d1427", accent="#ff416c", accent2="#ff7a45", ok="#22c55e",
                 warn="#f5a524", err="#f05252", sel="rgba(255,65,108,0.20)", hover="#1d2846", media="#05080f"),
    "light": dict(bg="#f1f3f9", card="#ffffff", card2="#f6f7fb", border="#e0e4ee", text="#1a2033",
                  muted="#68718a", input="#f8f9fc", accent="#e8365a", accent2="#f26b3a", ok="#16a34a",
                  warn="#d97706", err="#dc2626", sel="rgba(232,54,90,0.13)", hover="#eceff7", media="#0f1424"),
}

G = dict(download=0xE896, play=0xE768, pause=0xE769, stop=0xE71A, cancel=0xE711, folder=0xE8B7,
         folder_open=0xE838, refresh=0xE72C, sync=0xE895, settings=0xE713, paste=0xE77F, delete=0xE74D,
         info=0xE946, check=0xE73E, error=0xE783, audio=0xE8D6, video=0xE714, silent=0xE786, search=0xE721,
         file=0xE8E5, volume=0xE767, mute=0xE74F, list=0xE8F1, clear=0xE894, copy=0xE8C8, warning=0xE7BA,
         moon=0xE708, sun=0xE706, cloud=0xEBD3, help=0xE9CE, chevron=0xE70D, link=0xE71B, view=0xE890,
         history=0xE81C, page=0xE8A5, globe=0xE774, convert=0xE8AB, add=0xE710)

ICON_FONT = "Segoe MDL2 Assets"


def _status_color(t, status):
    if status == "Tamamlandı":
        return t["ok"]
    if status == "Hata":
        return t["err"]
    if status in ("İptal edildi", "Duraklatıldı"):
        return t["muted"]
    if status in ("Bağlantı bekleniyor…", "Yeniden denenecek"):
        return t["warn"]
    if status.startswith(("İşleniyor", "Dönüştürülüyor", "İnceleniyor", "Kopyalanıyor")):
        return t["accent2"]
    if status == "İndiriliyor" or status.startswith("Devam"):
        return t["accent"]
    return t["text"]


def glyph_pixmap(cp, color, px=18):
    dpr = QGuiApplication.primaryScreen().devicePixelRatio() if QGuiApplication.primaryScreen() else 1.0
    pm = QPixmap(int(px * dpr), int(px * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
    f = QFont(ICON_FONT)
    f.setPixelSize(max(8, int(px * 0.86)))
    p.setFont(f)
    p.setPen(QColor(color))
    p.drawText(QRect(0, 0, px, px), Qt.AlignCenter, chr(cp))
    p.end()
    return pm


def glyph_icon(cp, color, px=18):
    return QIcon(glyph_pixmap(cp, color, px))


def build_qss(t, check_png, chev_png):
    c = dict(t, check=check_png.replace("\\", "/"), chev=chev_png.replace("\\", "/"))
    return """
    QWidget {{ color: {text}; font-family: "Segoe UI Variable Text", "Segoe UI"; font-size: 10pt; }}
    QMainWindow, QWidget#root, QDialog {{ background: {bg}; }}
    QFrame#card {{ background: {card}; border: 1px solid {border}; border-radius: 14px; }}
    QLabel {{ background: transparent; }}
    QLabel#cardTitle {{ font-size: 11pt; font-weight: 600; }}
    QLabel#muted, QLabel#hint {{ color: {muted}; }}
    QLabel#appTitle {{ font-size: 15pt; font-weight: 700; }}
    QLabel#chip {{ background: {card2}; border: 1px solid {border}; border-radius: 9px; padding: 2px 9px;
                  color: {muted}; font-size: 8.5pt; }}
    QLabel#mediaTitle {{ font-size: 11.5pt; font-weight: 600; }}
    QLabel#time {{ color: {muted}; font-size: 9pt; }}
    QPlainTextEdit, QLineEdit, QTextBrowser {{ background: {input}; border: 1px solid {border}; border-radius: 10px;
                  padding: 7px 10px; selection-background-color: {accent}; selection-color: white; }}
    QPlainTextEdit:focus, QLineEdit:focus {{ border: 1px solid {accent}; }}
    QPushButton {{ background: {card2}; border: 1px solid {border}; border-radius: 10px; padding: 7px 14px; }}
    QPushButton:hover {{ background: {hover}; }}
    QPushButton:pressed {{ background: {border}; }}
    QPushButton:disabled {{ color: {muted}; }}
    QPushButton#primary {{ border: none; color: white; font-weight: 600; padding: 10px 22px; font-size: 10.5pt;
                  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {accent2}); }}
    QPushButton#primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent2}, stop:1 {accent}); }}
    QPushButton#primary:disabled {{ background: {border}; color: {muted}; }}
    QPushButton#seg {{ background: {input}; padding: 9px 12px; text-align: center; }}
    QPushButton#seg:hover {{ background: {hover}; }}
    QPushButton#seg:checked {{ background: {sel}; border: 1px solid {accent}; font-weight: 600; }}
    QPushButton#update {{ background: rgba(34,197,94,0.14); border: 1px solid {ok}; color: {ok};
                  border-radius: 15px; padding: 5px 14px; font-weight: 600; }}
    QPushButton#update:hover {{ background: rgba(34,197,94,0.25); }}
    QToolButton {{ background: transparent; border: none; border-radius: 8px; padding: 6px; }}
    QToolButton:hover {{ background: {hover}; }}
    QToolButton:pressed {{ background: {border}; }}
    QToolButton#play {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {accent}, stop:1 {accent2});
                  border-radius: 18px; padding: 8px; }}
    QComboBox {{ background: {input}; border: 1px solid {border}; border-radius: 10px; padding: 6px 10px; min-width: 96px; }}
    QComboBox:hover {{ border-color: {accent}; }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox::down-arrow {{ image: url({chev}); width: 11px; height: 11px; }}
    QComboBox QAbstractItemView {{ background: {card}; border: 1px solid {border}; padding: 4px; outline: 0;
                  selection-background-color: {sel}; selection-color: {text}; }}
    QCheckBox {{ spacing: 8px; background: transparent; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {border}; background: {input}; }}
    QCheckBox::indicator:hover {{ border-color: {accent}; }}
    QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; image: url({check}); }}
    QCheckBox:disabled {{ color: {muted}; }}
    QSpinBox {{ background: {input}; border: 1px solid {border}; border-radius: 8px; padding: 5px 8px; }}
    QTableWidget {{ background: {card}; border: none; gridline-color: transparent; outline: 0;
                  selection-background-color: {sel}; selection-color: {text}; alternate-background-color: {card2}; }}
    QTableWidget::item {{ padding: 4px 6px; border: none; }}
    QHeaderView::section {{ background: {card}; color: {muted}; border: none; border-bottom: 1px solid {border};
                  padding: 7px 6px; font-size: 8.5pt; font-weight: 600; }}
    QTableCornerButton::section {{ background: {card}; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {border}; border-radius: 4px; min-height: 30px; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: {border}; border-radius: 4px; min-width: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ width: 0; height: 0; background: none; }}
    QSlider::groove:horizontal {{ height: 4px; background: {border}; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ background: white; border: 2px solid {accent}; width: 10px; height: 10px;
                  margin: -6px 0; border-radius: 7px; }}
    QSplitter::handle {{ background: transparent; }}
    QMenu {{ background: {card}; border: 1px solid {border}; border-radius: 10px; padding: 6px; }}
    QMenu::item {{ padding: 7px 22px 7px 10px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {sel}; }}
    QMenu::item:disabled {{ color: {muted}; }}
    QMenu::separator {{ height: 1px; background: {border}; margin: 4px 8px; }}
    QMenu::icon {{ padding-left: 6px; }}
    QToolTip {{ background: {card2}; color: {text}; border: 1px solid {border}; padding: 5px; border-radius: 6px; }}
    QStatusBar {{ background: {bg}; color: {muted}; }}
    QStatusBar QLabel {{ color: {muted}; font-size: 9pt; }}
    QStatusBar::item {{ border: none; }}
    QProgressBar {{ background: {input}; border: 1px solid {border}; border-radius: 6px; height: 12px;
                  text-align: center; font-size: 8pt; }}
    QProgressBar::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {accent2});
                  border-radius: 5px; }}
    QWidget#media {{ background: {media}; border-radius: 12px; }}
    QLabel#toast {{ background: {card2}; border: 1px solid {border}; border-radius: 12px; padding: 10px 16px; }}
    """.format(**c)


# ----------------------------------------------------------------- yardımcı bileşenler
def fmt_time(ms):
    s = max(0, int(ms // 1000))
    h, m, s = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_count(n):
    if n >= 1_000_000_000:
        return f"{n / 1e9:.1f} milyar".replace(".", ",")
    if n >= 1_000_000:
        return f"{n / 1e6:.1f} milyon".replace(".", ",")
    if n >= 1000:
        return f"{n / 1e3:.0f} bin"
    return str(n)


class Card(QFrame):
    def __init__(self, title="", glyph=None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(16, 14, 16, 16)
        self.lay.setSpacing(10)
        self.head = QHBoxLayout()
        self.head.setSpacing(8)
        self.icon_lbl = QLabel()
        self.glyph = glyph
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("cardTitle")
        if glyph:
            self.head.addWidget(self.icon_lbl)
        self.head.addWidget(self.title_lbl)
        self.head.addStretch(1)
        if title:
            self.lay.addLayout(self.head)

    def retheme(self, t):
        if self.glyph:
            self.icon_lbl.setPixmap(glyph_pixmap(self.glyph, t["accent"], 18))


class MediaView(QWidget):
    """Küçük resmi en-boy oranını koruyarak gösterir; üzerine oynat düğmesi / rozet çizer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("media")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.pix = None
        self.placeholder = ""
        self.badge = ""
        self.overlay = False
        self.theme = THEMES["dark"]
        self.setCursor(Qt.PointingHandCursor)
        self.on_click = None
        self.setMinimumHeight(150)

    def set_state(self, pix=None, placeholder="", overlay=False, badge=""):
        self.pix, self.placeholder, self.overlay, self.badge = pix, placeholder, overlay, badge
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.on_click:
            self.on_click()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        r = self.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(r), 12, 12)
        p.setClipPath(path)
        p.fillRect(r, QColor(self.theme["media"]))
        if self.pix and not self.pix.isNull():
            sp = self.pix.scaled(r.size() * self.devicePixelRatioF(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            sp.setDevicePixelRatio(self.devicePixelRatioF())
            w, h = sp.width() / sp.devicePixelRatio(), sp.height() / sp.devicePixelRatio()
            p.drawPixmap(int((r.width() - w) / 2), int((r.height() - h) / 2), sp)
        elif self.placeholder:
            f = QFont(ICON_FONT)
            f.setPixelSize(44)
            p.setFont(f)
            p.setPen(QColor(self.theme["muted"]))
            p.drawText(QRect(0, r.height() // 2 - 60, r.width(), 56), Qt.AlignCenter, chr(G["view"]))
            f2 = QFont("Segoe UI")
            f2.setPointSizeF(10)
            p.setFont(f2)
            p.drawText(QRect(20, r.height() // 2 + 4, r.width() - 40, 60), Qt.AlignHCenter | Qt.TextWordWrap,
                       self.placeholder)
        if self.overlay:
            d = 64
            cx, cy = r.width() / 2, r.height() / 2
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 140))
            p.drawEllipse(QRectF(cx - d / 2, cy - d / 2, d, d))
            f = QFont(ICON_FONT)
            f.setPixelSize(26)
            p.setFont(f)
            p.setPen(QColor("white"))
            p.drawText(QRectF(cx - d / 2 + 3, cy - d / 2, d, d), Qt.AlignCenter, chr(G["play"]))
        if self.badge:
            f = QFont("Segoe UI")
            f.setPointSizeF(9)
            f.setBold(True)
            p.setFont(f)
            tw = p.fontMetrics().horizontalAdvance(self.badge) + 22
            br = QRectF(12, r.height() - 40, tw, 28)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 170))
            p.drawRoundedRect(br, 14, 14)
            p.setPen(QColor("white"))
            p.drawText(br, Qt.AlignCenter, self.badge)
        p.end()


class ProgressDelegate(QStyledItemDelegate):
    def __init__(self, win):
        super().__init__(win)
        self.win = win

    def paint(self, p, opt, idx):
        t = self.win.t
        val = idx.data(Qt.UserRole)
        status = idx.data(Qt.UserRole + 1) or ""
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(opt.rect).adjusted(6, opt.rect.height() / 2 - 4, -46, -(opt.rect.height() / 2 - 4))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(t["border"]))
        p.drawRoundedRect(r, 4, 4)
        if val is not None:
            w = r.width() * max(0.0, min(100.0, val)) / 100
            p.setBrush(QColor(_status_color(t, status) if status in FINAL or status.startswith(("İşleniyor", "Dönüştürülüyor")) else t["accent"]))
            p.drawRoundedRect(QRectF(r.x(), r.y(), w, r.height()), 4, 4)
            p.setPen(QColor(t["muted"]))
            f = p.font()
            f.setPointSizeF(8.5)
            p.setFont(f)
            p.drawText(QRectF(r.right() + 4, opt.rect.y(), 42, opt.rect.height()),
                       Qt.AlignVCenter | Qt.AlignLeft, f"{val:.0f}%")
        p.restore()


# ----------------------------------------------------------------- pencereler
class InstallDialog(QDialog):
    def __init__(self, parent, need):
        super().__init__(parent)
        self.setWindowTitle(APP_NAME + " — kurulum")
        self.setModal(True)
        self.setFixedWidth(500)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(10)
        t = QLabel(f"<b>Gerekli araçlar kuruluyor</b><br><span>Bulunamadı: {', '.join(need)}. "
                   "Bir kereliğine otomatik indiriliyor.</span>")
        t.setWordWrap(True)
        lay.addWidget(t)
        self.lbl = QLabel("Başlıyor…")
        self.lbl.setObjectName("muted")
        lay.addWidget(self.lbl)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        lay.addWidget(self.bar)
        path = QLabel(f"Konum: {BIN_DIR}")
        path.setObjectName("hint")
        path.setWordWrap(True)
        lay.addWidget(path)

    def progress(self, text, pct):
        self.lbl.setText(text)
        if pct is None:
            self.bar.setRange(0, 0)
        else:
            self.bar.setRange(0, 100)
            self.bar.setValue(int(pct))

    def reject(self):  # Esc ile kapanmasın
        pass


class UpdateDialog(QDialog):
    def __init__(self, win, info):
        super().__init__(win)
        self.win, self.info = win, info
        self.setWindowTitle("Yeni sürüm")
        self.resize(560, 480)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(12)
        head = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(glyph_pixmap(G["cloud"], win.t["ok"], 34))
        head.addWidget(ic)
        tl = QLabel(f"<span style='font-size:14pt;font-weight:700'>Sürüm {info['version']} hazır</span><br>"
                    f"<span style='color:{win.t['muted']}'>Kullandığınız sürüm: {APP_VERSION}</span>")
        head.addWidget(tl, 1)
        lay.addLayout(head)
        notes = QTextBrowser()
        notes.setOpenExternalLinks(True)
        notes.setMarkdown(info.get("notes") or "Sürüm notu yok.")
        lay.addWidget(notes, 1)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.hide()
        lay.addWidget(self.bar)
        self.lbl = QLabel("")
        self.lbl.setObjectName("muted")
        self.lbl.hide()
        lay.addWidget(self.lbl)
        row = QHBoxLayout()
        self.skip = QPushButton("Bu sürümü atla")
        self.page = QPushButton("Sürüm sayfası")
        self.page.setIcon(glyph_icon(G["globe"], win.t["text"]))
        self.later = QPushButton("Sonra")
        self.go = QPushButton("  Şimdi güncelle")
        self.go.setObjectName("primary")
        self.go.setIcon(glyph_icon(G["download"], "white"))
        row.addWidget(self.skip)
        row.addWidget(self.page)
        row.addStretch(1)
        row.addWidget(self.later)
        row.addWidget(self.go)
        lay.addLayout(row)
        self.skip.clicked.connect(self._skip)
        self.page.clicked.connect(lambda: webbrowser.open(info["page"]))
        self.later.clicked.connect(self.reject)
        self.go.clicked.connect(self._go)
        if not FROZEN:
            self.go.setText("  İndirme sayfasını aç")

    def _skip(self):
        self.win.s["skipped_version"] = self.info["version"]
        save_settings(self.win.s)
        self.win.update_btn.hide()
        self.reject()

    def _go(self):
        if not FROZEN:
            webbrowser.open(self.info["page"])
            self.accept()
            return
        for b in (self.go, self.skip, self.later, self.page):
            b.setEnabled(False)
        self.bar.show()
        self.lbl.show()
        self.lbl.setText("İndiriliyor…")
        self.win.start_app_download(self.info, self)

    def progress(self, done, total):
        if total:
            self.bar.setValue(int(done * 100 / total))
        self.lbl.setText(f"İndiriliyor… {done / 1048576:.1f} / {total / 1048576:.1f} MB" if total
                         else f"İndiriliyor… {done / 1048576:.1f} MB")

    def failed(self, msg):
        self.lbl.setText("Güncelleme başarısız: " + msg)
        for b in (self.later, self.page, self.go):
            b.setEnabled(True)
        self.go.setText("  Tekrar dene")


class SettingsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        s = win.s
        t = win.t
        self.setWindowTitle("Ayarlar")
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(12)

        gen = Card("Genel", G["settings"])
        gen.retheme(t)
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(10)
        g.addWidget(QLabel("Aynı anda indirme sayısı"), 0, 0)
        self.par = QSpinBox()
        self.par.setRange(1, 5)
        self.par.setValue(int(s["parallel"]))
        g.addWidget(self.par, 0, 1, Qt.AlignLeft)
        g.addWidget(QLabel("Tema"), 1, 0)
        self.theme = QComboBox()
        self.theme.addItems(["Koyu", "Açık"])
        self.theme.setCurrentIndex(0 if s.get("theme", "dark") == "dark" else 1)
        g.addWidget(self.theme, 1, 1, Qt.AlignLeft)
        gen.lay.addLayout(g)
        self.awake = QCheckBox("İndirme sürerken bilgisayarın uyumasını engelle")
        self.awake.setChecked(bool(s["prevent_sleep"]))
        gen.lay.addWidget(self.awake)
        lay.addWidget(gen)

        upd = Card("Güncellemeler", G["sync"])
        upd.retheme(t)
        self.auto_yt = QCheckBox("Açılışta yt-dlp'yi otomatik güncelle (günde bir)")
        self.auto_yt.setChecked(bool(s["auto_update"]))
        self.auto_app = QCheckBox("Açılışta uygulamanın yeni sürümünü denetle")
        self.auto_app.setChecked(bool(s.get("app_update_check", True)))
        upd.lay.addWidget(self.auto_yt)
        upd.lay.addWidget(self.auto_app)
        r1 = QHBoxLayout()
        self.ver = QLabel(f"Uygulama <b>{APP_VERSION}</b> &nbsp;·&nbsp; yt-dlp <b>{win.ytdlp_ver or '—'}</b>")
        r1.addWidget(self.ver, 1)
        self.b_yt = QPushButton(" yt-dlp'yi güncelle")
        self.b_yt.setIcon(glyph_icon(G["refresh"], t["text"]))
        self.b_app = QPushButton(" Uygulama güncellemesini denetle")
        self.b_app.setIcon(glyph_icon(G["cloud"], t["text"]))
        upd.lay.addLayout(r1)
        r2 = QHBoxLayout()
        r2.addWidget(self.b_yt)
        r2.addWidget(self.b_app)
        r2.addStretch(1)
        upd.lay.addLayout(r2)
        lay.addWidget(upd)

        oth = Card("Dosyalar ve yardım", G["folder"])
        oth.retheme(t)
        r3 = QHBoxLayout()
        b_log = QPushButton(" Günlük dosyası")
        b_log.setIcon(glyph_icon(G["page"], t["text"]))
        b_cfg = QPushButton(" Ayarlar klasörü")
        b_cfg.setIcon(glyph_icon(G["folder_open"], t["text"]))
        b_help = QPushButton(" Kullanım kılavuzu")
        b_help.setIcon(glyph_icon(G["help"], t["text"]))
        for b in (b_log, b_cfg, b_help):
            r3.addWidget(b)
        r3.addStretch(1)
        oth.lay.addLayout(r3)
        lay.addWidget(oth)

        close = QPushButton("Tamam")
        close.setObjectName("primary")
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        lay.addLayout(row)

        close.clicked.connect(self.accept)
        self.b_yt.clicked.connect(lambda: win.update_ytdlp(auto=False))
        self.b_app.clicked.connect(lambda: win.check_app_update(manual=True))
        b_log.clicked.connect(lambda: os.path.exists(LOG_FILE) and os.startfile(LOG_FILE))
        b_cfg.clicked.connect(lambda: (os.makedirs(CONFIG_DIR, exist_ok=True), os.startfile(CONFIG_DIR)))
        b_help.clicked.connect(lambda: webbrowser.open(APP_URL + "/blob/main/docs/KULLANIM-KILAVUZU.md"))

    def accept(self):
        w = self.win
        w.s.update(parallel=self.par.value(), prevent_sleep=self.awake.isChecked(),
                   auto_update=self.auto_yt.isChecked(), app_update_check=self.auto_app.isChecked())
        w.dl.parallel = w.s["parallel"]
        w.dl.pump()
        theme = "dark" if self.theme.currentIndex() == 0 else "light"
        if theme != w.s.get("theme"):
            w.s["theme"] = theme
            w.apply_theme()
        save_settings(w.s)
        w.refresh_status()
        super().accept()


class ConverterDialog(QDialog):
    """Bilgisayardaki videoları Android / TV uyumlu MP4'e (H.264 + AAC) çevirir. Orijinallere dokunmaz."""
    COLS = ["Dosya", "Durum", "İlerleme", "Ayrıntı"]

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        t = win.t
        s = win.s
        self.events = queue.Queue()
        self.conv = core.Converter(win.ffmpeg, self.events)
        self.jobs = {}       # id -> ConvJob
        self.rows = {}       # id -> QTableWidgetItem
        self.ready = []      # henüz başlatılmamış dosyalar (ConvJob, status "Hazır")
        self.setWindowTitle("MP4 Dönüştürücü")
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.resize(940, 620)
        self.setAcceptDrops(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        intro = QLabel("Videoları her telefon, tablet ve TV'de <b>görüntülü</b> oynayan MP4 biçimine (H.264 + AAC) "
                       "çevirir. AV1 / VP9 / H.265, 60 fps veya yüksek çözünürlüklü videolar küçültülür. "
                       "<b>Orijinal dosyalara dokunulmaz</b>; çıktılar ayrı klasöre yazılır. "
                       "Dosya veya klasörleri bu pencereye sürükleyip bırakabilirsiniz.")
        intro.setWordWrap(True)
        intro.setObjectName("muted")
        lay.addWidget(intro)

        opt = Card("Dönüştürme seçenekleri", G["settings"])
        opt.retheme(t)
        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(6)
        for col, txt in enumerate(("Çözünürlük (en fazla)", "Kare hızı (FPS)")):
            lb = QLabel(txt)
            lb.setObjectName("muted")
            g.addWidget(lb, 0, col)
        self.cb_res = QComboBox()
        self.cb_res.addItems(CONVERT_RESOLUTIONS)
        self.cb_res.setCurrentText(s.get("conv_res") if s.get("conv_res") in CONVERT_RESOLUTIONS
                                   else CONVERT_RESOLUTIONS[0])
        self.cb_res.setToolTip("720p eski ve düşük güçlü cihazlar dahil her yerde oynar. "
                               "Küçük videolar büyütülmez.")
        self.cb_fps = QComboBox()
        self.cb_fps.addItems(FPS_OPTIONS)
        self.cb_fps.setCurrentText(s.get("conv_fps") if s.get("conv_fps") in FPS_OPTIONS else FPS_OPTIONS[0])
        g.addWidget(self.cb_res, 1, 0)
        g.addWidget(self.cb_fps, 1, 1)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)
        opt.lay.addLayout(g)
        chk = QHBoxLayout()
        chk.setSpacing(18)
        self.chk_clean = QCheckBox("Dosya adlarını düzelt")
        self.chk_clean.setToolTip("Emoji, ｜ ⧸ ： gibi karakterler ve sondaki [video kimliği] çıktı adından temizlenir")
        self.chk_clean.setChecked(bool(s.get("conv_clean", True)))
        self.chk_copy = QCheckBox("Zaten uyumlu olanları dönüştürmeden kopyala")
        self.chk_copy.setToolTip("Kalite kaybı olmaz ve çok hızlıdır")
        self.chk_copy.setChecked(bool(s.get("conv_copy_ok", True)))
        chk.addWidget(self.chk_clean)
        chk.addWidget(self.chk_copy)
        chk.addStretch(1)
        opt.lay.addLayout(chk)
        fr = QHBoxLayout()
        fr.setSpacing(8)
        lb = QLabel("Çıktı klasörü")
        lb.setObjectName("muted")
        fr.addWidget(lb)
        self.out_edit = QLineEdit(s.get("conv_out") or "")
        self.out_edit.setPlaceholderText(f"Her videonun yanında \"{core.CONV_SUBDIR}\" klasörü")
        fr.addWidget(self.out_edit, 1)
        b_out = QPushButton(" Gözat")
        b_out.setIcon(glyph_icon(G["folder_open"], t["text"]))
        b_out.clicked.connect(self._browse_out)
        b_def = QPushButton("")
        b_def.setIcon(glyph_icon(G["refresh"], t["text"]))
        b_def.setToolTip("Varsayılan (videonun yanında)")
        b_def.clicked.connect(lambda: self.out_edit.clear())
        fr.addWidget(b_out)
        fr.addWidget(b_def)
        opt.lay.addLayout(fr)
        lay.addWidget(opt)

        row = QHBoxLayout()
        row.setSpacing(8)
        b_files = QPushButton(" Dosya ekle")
        b_files.setIcon(glyph_icon(G["add"], t["text"]))
        b_files.clicked.connect(self._add_files)
        b_dir = QPushButton(" Klasör ekle")
        b_dir.setIcon(glyph_icon(G["folder"], t["text"]))
        b_dir.clicked.connect(self._add_folder)
        row.addWidget(b_files)
        row.addWidget(b_dir)
        row.addStretch(1)
        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("muted")
        row.addWidget(self.count_lbl)
        lay.addLayout(row)

        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.Interactive)
        hh.setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 260)
        self.table.setItemDelegateForColumn(2, ProgressDelegate(win))
        self.table.cellDoubleClicked.connect(self._on_double)
        lay.addWidget(self.table, 1)
        self.empty = QLabel("Henüz dosya yok — dosya veya klasör ekleyin ya da buraya sürükleyin.")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setObjectName("muted")
        lay.addWidget(self.empty, 1)

        bot = QHBoxLayout()
        self.b_cancel = QPushButton(" Seçilenleri iptal et")
        self.b_cancel.setIcon(glyph_icon(G["cancel"], t["text"]))
        self.b_cancel.clicked.connect(self._cancel_selected)
        b_clear = QPushButton(" Listeyi temizle")
        b_clear.setIcon(glyph_icon(G["clear"], t["text"]))
        b_clear.setToolTip("Biten, iptal edilen ve başlatılmamış dosyaları listeden kaldırır")
        b_clear.clicked.connect(self._clear_finished)
        self.b_open = QPushButton(" Çıktı klasörünü aç")
        self.b_open.setIcon(glyph_icon(G["folder_open"], t["text"]))
        self.b_open.clicked.connect(self._open_out)
        self.b_go = QPushButton("  Dönüştür")
        self.b_go.setObjectName("primary")
        self.b_go.setIcon(glyph_icon(G["convert"], "white"))
        self.b_go.clicked.connect(self._start)
        bot.addWidget(self.b_cancel)
        bot.addWidget(b_clear)
        bot.addWidget(self.b_open)
        bot.addStretch(1)
        bot.addWidget(self.b_go)
        lay.addLayout(bot)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(150)
        self._refresh_state()

    # ---- dosya ekleme
    def _add_paths(self, paths):
        files = core.collect_videos(paths)
        known = {os.path.normcase(os.path.abspath(j.src)) for j in self.jobs.values()
                 if j.status not in ("Tamamlandı", "Hata", "İptal edildi")}
        added = 0
        for f in files:
            if os.path.normcase(os.path.abspath(f)) in known:
                continue
            # kendi çıktı klasörümüzdeki dosyaları tekrar eklemeyelim
            if os.path.basename(os.path.dirname(f)) == core.CONV_SUBDIR and not self.out_edit.text().strip():
                continue
            j = core.ConvJob(f, {})
            j.status = "Hazır"
            self.jobs[j.id] = j
            self.ready.append(j)
            self._add_row(j)
            added += 1
        if paths and not added:
            self.win.toast("Eklenecek yeni video bulunamadı")
        self._refresh_state()

    def _add_files(self):
        exts = " ".join("*" + e for e in core.VIDEO_EXT)
        paths, _ = QFileDialog.getOpenFileNames(self, "Video seç", self._start_dir(),
                                                f"Videolar ({exts});;Tüm dosyalar (*.*)")
        self._add_paths(paths)

    def _add_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Video klasörü seç", self._start_dir())
        if d:
            self._add_paths([os.path.normpath(d)])

    def _start_dir(self):
        f = self.win._folder()
        return f if os.path.isdir(f) else os.path.expanduser("~")

    def _browse_out(self):
        d = QFileDialog.getExistingDirectory(self, "Çıktı klasörü seç", self.out_edit.text() or self._start_dir())
        if d:
            self.out_edit.setText(os.path.normpath(d))

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self._add_paths([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])

    # ---- tablo
    def _add_row(self, j):
        r = self.table.rowCount()
        self.table.insertRow(r)
        it = QTableWidgetItem(os.path.basename(j.src))
        it.setData(Qt.UserRole, j.id)
        it.setToolTip(j.src)
        self.table.setItem(r, 0, it)
        for col in range(1, len(self.COLS)):
            self.table.setItem(r, col, QTableWidgetItem(""))
        self.rows[j.id] = it
        self._refresh_row(j)

    def _refresh_row(self, j):
        it = self.rows.get(j.id)
        if it is None:
            return
        t = self.win.t
        r = it.row()
        it.setIcon(glyph_icon(G["video"], t["muted"], 16))
        st = self.table.item(r, 1)
        st.setText({"Hata": "Hata — çift tıklayın"}.get(j.status, j.status))
        color = _status_color(t, j.status)
        st.setForeground(QColor(color))
        glyph = {"Tamamlandı": G["check"], "Hata": G["error"], "İptal edildi": G["cancel"],
                 "Dönüştürülüyor": G["convert"], "Kopyalanıyor": G["copy"]}.get(j.status, G["history"])
        st.setIcon(glyph_icon(glyph, color, 14))
        try:
            val = float(j.percent.rstrip("%")) if j.percent else None
        except ValueError:
            val = None
        pr = self.table.item(r, 2)
        pr.setData(Qt.UserRole, 100.0 if j.status == "Tamamlandı" else val)
        pr.setData(Qt.UserRole + 1, j.status)
        info = self.table.item(r, 3)
        info.setText(j.error if j.status == "Hata" else j.info)
        info.setToolTip((j.error or j.info) + (f"\n→ {j.dst}" if j.dst else ""))
        info.setForeground(QColor(t["err"] if j.status == "Hata" else t["muted"]))

    def _job_at(self, row):
        it = self.table.item(row, 0)
        return self.jobs.get(it.data(Qt.UserRole)) if it else None

    def _on_double(self, row, _col):
        j = self._job_at(row)
        if not j:
            return
        if j.status == "Hata":
            QMessageBox.warning(self, "Dönüştürme hatası", f"{j.src}\n\n{j.error}")
        elif j.dst and os.path.exists(j.dst):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(j.dst)])
        elif os.path.exists(j.src):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(j.src)])

    # ---- işlemler
    def _opts(self):
        self.win.s.update(conv_res=self.cb_res.currentText(), conv_fps=self.cb_fps.currentText(),
                          conv_clean=self.chk_clean.isChecked(), conv_copy_ok=self.chk_copy.isChecked(),
                          conv_out=self.out_edit.text().strip())
        save_settings(self.win.s)
        return {k: self.win.s[k] for k in ("conv_res", "conv_fps", "conv_clean", "conv_copy_ok", "conv_out")}

    def _start(self):
        if not self.ready:
            self.win.toast("Önce dosya ekleyin")
            return
        out = self.out_edit.text().strip()
        if out:
            try:
                os.makedirs(out, exist_ok=True)
            except OSError as e:
                QMessageBox.warning(self, "MP4 Dönüştürücü", f"Çıktı klasörü oluşturulamadı:\n{e}")
                return
        opts = self._opts()
        self.conv.ffmpeg = self.win.ffmpeg
        for j in self.ready:
            j.opts = dict(opts)
            j.status = "Bekliyor"
            self.conv.add(j)
        self.ready = []
        self._refresh_state()

    def _cancel_selected(self):
        rows = sorted({i.row() for i in self.table.selectedItems()})
        for r in rows:
            j = self._job_at(r)
            if not j or j.status in ("Tamamlandı", "Hata", "İptal edildi"):
                continue
            if j in self.ready:
                self.ready.remove(j)
                j.status = "İptal edildi"
                self._refresh_row(j)
            else:
                self.conv.cancel(j)
        self._refresh_state()

    def cancel_all(self):
        for j in list(self.jobs.values()):
            if j.status not in ("Tamamlandı", "Hata", "İptal edildi", "Hazır"):
                self.conv.cancel(j)

    def _clear_finished(self):
        for r in range(self.table.rowCount() - 1, -1, -1):
            j = self._job_at(r)
            if j and j.status in ("Tamamlandı", "Hata", "İptal edildi", "Hazır"):
                self.table.removeRow(r)
                self.rows.pop(j.id, None)
                self.jobs.pop(j.id, None)
                if j in self.ready:
                    self.ready.remove(j)
        self._refresh_state()

    def _open_out(self):
        out = self.out_edit.text().strip()
        if not out:
            done = [j for j in self.jobs.values() if j.dst]
            src = done[-1].dst if done else (next(iter(self.jobs.values())).src if self.jobs else None)
            if not src:
                self.win.toast("Henüz çıktı yok")
                return
            out = os.path.dirname(src) if done else os.path.join(os.path.dirname(src), core.CONV_SUBDIR)
        if os.path.isdir(out):
            os.startfile(out)
        else:
            self.win.toast("Çıktı klasörü henüz oluşmadı")

    def _poll(self):
        changed, finished = set(), False
        try:
            for _ in range(300):
                kind, j = self.events.get_nowait()
                changed.add(j.id)
                finished = finished or kind == "conv_done"
        except queue.Empty:
            pass
        for jid in changed:
            if jid in self.jobs:
                self._refresh_row(self.jobs[jid])
        if changed:
            self._refresh_state()
        if finished and self.conv.active_count() == 0:
            vals = list(self.jobs.values())
            ok = sum(1 for j in vals if j.status == "Tamamlandı")
            err = sum(1 for j in vals if j.status == "Hata")
            self.win.toast(f"Dönüştürme bitti — {ok} başarılı" + (f", {err} hatalı" if err else ""))
            QApplication.alert(self)

    def _refresh_state(self):
        vals = list(self.jobs.values())
        n = len(vals)
        active = self.conv.active_count()
        done = sum(1 for j in vals if j.status == "Tamamlandı")
        self.table.setVisible(n > 0)
        self.empty.setVisible(n == 0)
        parts = []
        if self.ready:
            parts.append(f"{len(self.ready)} hazır")
        if active:
            parts.append(f"{active} sürüyor/bekliyor")
        if done:
            parts.append(f"{done} tamamlandı")
        self.count_lbl.setText("  ·  ".join(parts))
        self.b_go.setEnabled(bool(self.ready))
        self.b_go.setText(f"  Dönüştür ({len(self.ready)})" if self.ready else "  Dönüştür")
        self.setWindowTitle(f"MP4 Dönüştürücü ({active})" if active else "MP4 Dönüştürücü")

    def reject(self):   # pencere kapanınca dönüştürme arka planda sürer
        self.hide()

    def closeEvent(self, e):
        e.ignore()
        self.hide()


# ----------------------------------------------------------------- ana pencere
class MainWindow(QMainWindow):
    COLS = ["Başlık", "Durum", "İlerleme", "Hız", "Kalan", "Tür"]

    def __init__(self, just_updated=False):
        super().__init__()
        self.s = load_settings()
        self.t = THEMES.get(self.s.get("theme"), THEMES["dark"])
        self.events = queue.Queue()
        self.jobs = {}
        self.rows = {}           # job id -> QTableWidgetItem (sütun 0)
        self.updating = False
        self.ytdlp = find_exe("yt-dlp")
        self.ffmpeg = find_exe("ffmpeg")
        self.ytdlp_ver = ""
        self.dl = Downloader(self.ytdlp, self.ffmpeg, self.events)
        self.dl.parallel = int(self.s["parallel"])
        self.preview = None      # son önizleme bilgisi
        self.preview_token = 0
        self.last_probed = ""
        self.app_update = None
        self._awake = None
        self._restored = False
        self._install_dlg = None
        self._update_dlg = None
        self._conv_dlg = None

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(QIcon(os.path.join(RES_DIR, "indirici.ico")))
        self.resize(1320, 860)
        self.setMinimumSize(1040, 700)
        self.setAcceptDrops(True)
        self._build()
        self.apply_theme()
        self._load_options()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(120)
        self.probe_timer = QTimer(self)
        self.probe_timer.setSingleShot(True)
        self.probe_timer.timeout.connect(self._auto_probe)

        if just_updated:
            QTimer.singleShot(800, lambda: self.toast(f"Uygulama {APP_VERSION} sürümüne güncellendi"))
            threading.Thread(target=core.cleanup_old_update, daemon=True).start()
        if not self.ytdlp or not self.ffmpeg:
            QTimer.singleShot(300, self._install_missing)
        else:
            QTimer.singleShot(50, lambda: self._tools_ready(False))

    # ---------------------------------------------------------- yerleşim
    def _icon_btn(self, glyph, tip, slot, px=18):
        b = QToolButton()
        b.setToolTip(tip)
        b.setIconSize(QSize(px, px))
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(slot)
        b._glyph = glyph
        self._icon_widgets.append((b, glyph, "text", px))
        return b

    def _btn(self, text, glyph, slot, role="text", obj=None):
        b = QPushButton(("  " + text) if text else "")
        if obj:
            b.setObjectName(obj)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(slot)
        self._icon_widgets.append((b, glyph, role, 16))
        return b

    def _build(self):
        self._icon_widgets = []
        self._cards = []
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 14, 18, 8)
        outer.setSpacing(12)

        # --- başlık
        head = QHBoxLayout()
        head.setSpacing(10)
        logo = QLabel()
        lp = QPixmap(os.path.join(RES_DIR, "indirici.png"))
        if not lp.isNull():
            logo.setPixmap(lp.scaled(38, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        head.addWidget(logo)
        tbox = QVBoxLayout()
        tbox.setSpacing(0)
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        sub = QLabel("YouTube ve 1000+ siteden video ve müzik")
        sub.setObjectName("muted")
        tbox.addWidget(title)
        tbox.addWidget(sub)
        head.addLayout(tbox)
        chip = QLabel(f"v{APP_VERSION}")
        chip.setObjectName("chip")
        head.addWidget(chip, 0, Qt.AlignTop)
        head.addStretch(1)
        self.update_btn = QPushButton("  Yeni sürüm")
        self.update_btn.setObjectName("update")
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.clicked.connect(self._show_update_dialog)
        self.update_btn.hide()
        self._icon_widgets.append((self.update_btn, G["cloud"], "ok", 16))
        head.addWidget(self.update_btn)
        self.conv_btn = self._btn("MP4 Dönüştürücü", G["convert"], self._open_converter)
        self.conv_btn.setToolTip("Bilgisayardaki videoları Android / TV uyumlu MP4'e (H.264) çevir")
        head.addWidget(self.conv_btn)
        self.theme_btn = self._icon_btn(G["moon"], "Açık / koyu tema", self._toggle_theme, 20)
        head.addWidget(self.theme_btn)
        head.addWidget(self._icon_btn(G["help"], "Kullanım kılavuzu",
                                      lambda: webbrowser.open(APP_URL + "/blob/main/docs/KULLANIM-KILAVUZU.md"), 20))
        head.addWidget(self._icon_btn(G["settings"], "Ayarlar", self._open_settings, 20))
        outer.addLayout(head)

        # --- gövde: üst (bağlantı + seçenek | önizleme) ve alt (kuyruk)
        vsplit = QSplitter(Qt.Vertical)
        vsplit.setChildrenCollapsible(False)
        vsplit.setHandleWidth(10)
        top = QWidget()
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(0, 0, 0, 0)
        hsplit = QSplitter(Qt.Horizontal)
        hsplit.setChildrenCollapsible(False)
        hsplit.setHandleWidth(12)
        top_l.addWidget(hsplit)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(12)
        ll.addWidget(self._build_links())
        ll.addWidget(self._build_options())
        ll.addStretch(1)
        hsplit.addWidget(left)
        hsplit.addWidget(self._build_preview())
        hsplit.setStretchFactor(0, 5)
        hsplit.setStretchFactor(1, 4)
        hsplit.setSizes([700, 560])

        vsplit.addWidget(top)
        vsplit.addWidget(self._build_queue())
        vsplit.setStretchFactor(0, 3)
        vsplit.setStretchFactor(1, 2)
        vsplit.setSizes([470, 300])
        outer.addWidget(vsplit, 1)

        # --- durum çubuğu
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        sb.setContentsMargins(20, 0, 20, 4)
        self.st_left = QLabel("Hazır")
        self.st_right = QLabel("")
        sb.addWidget(self.st_left, 1)
        sb.addPermanentWidget(self.st_right)

        self.toast_lbl = QLabel(self)
        self.toast_lbl.setObjectName("toast")
        self.toast_lbl.hide()
        self.toast_timer = QTimer(self)
        self.toast_timer.setSingleShot(True)
        self.toast_timer.timeout.connect(self.toast_lbl.hide)

        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._add)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._add)

    def _build_links(self):
        c = Card("Bağlantılar", G["link"])
        self._cards.append(c)
        self.url_edit = QPlainTextEdit()
        self.url_edit.setPlaceholderText("Video, müzik veya oynatma listesi bağlantılarını buraya yapıştırın — "
                                         "her satıra bir tane.\nÖrnek: https://www.youtube.com/watch?v=…")
        self.url_edit.setFixedHeight(104)
        self.url_edit.textChanged.connect(lambda: self.probe_timer.start(900))
        c.lay.addWidget(self.url_edit)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self._btn("Yapıştır", G["paste"], self._paste))
        row.addWidget(self._btn("Listeden yükle", G["page"], self._load_list))
        row.addWidget(self._btn("", G["clear"], lambda: self.url_edit.clear()))
        row.itemAt(row.count() - 1).widget().setToolTip("Temizle")
        row.addStretch(1)
        self.b_preview = self._btn("Önizle", G["view"], self._preview_clicked)
        row.addWidget(self.b_preview)
        self.b_add = self._btn("İndir", G["download"], self._add, role="white", obj="primary")
        self.b_add.setToolTip("Kuyruğa ekle ve indir (Ctrl+Enter)")
        row.addWidget(self.b_add)
        c.lay.addLayout(row)
        return c

    def _build_options(self):
        c = Card("İndirme seçenekleri", G["settings"])
        self._cards.append(c)
        seg = QHBoxLayout()
        seg.setSpacing(8)
        self.seg_group = QButtonGroup(self)
        self.seg_btns = []
        for i, (label, glyph) in enumerate([("Video + Ses", G["video"]), ("Sadece Ses", G["audio"]),
                                            ("Sessiz Video", G["silent"])]):
            b = QPushButton("  " + label)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.seg_group.addButton(b, i)
            self._icon_widgets.append((b, glyph, "text", 16))
            self.seg_btns.append(b)
            seg.addWidget(b)
        self.seg_group.idClicked.connect(self._on_type_change)
        c.lay.addLayout(seg)

        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(6)
        lf = QLabel("Format")
        lf.setObjectName("muted")
        self.lbl_q = QLabel("Çözünürlük")
        self.lbl_q.setObjectName("muted")
        g.addWidget(lf, 0, 0)
        g.addWidget(self.lbl_q, 0, 1)
        self.cb_format = QComboBox()
        self.cb_q = QComboBox()
        self.cb_format.currentTextChanged.connect(self._on_format_change)
        self.cb_q.currentTextChanged.connect(self._on_q_change)
        g.addWidget(self.cb_format, 1, 0)
        g.addWidget(self.cb_q, 1, 1)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)
        self.lbl_compat = QLabel("Uyumluluk")
        self.lbl_compat.setObjectName("muted")
        self.lbl_fps = QLabel("Kare hızı (FPS)")
        self.lbl_fps.setObjectName("muted")
        g.addWidget(self.lbl_compat, 2, 0)
        g.addWidget(self.lbl_fps, 2, 1)
        self.cb_compat = QComboBox()
        self.cb_compat.addItems(COMPAT_MODES)
        self.cb_compat.setToolTip("Android uyumlu: H.264 + AAC MP4 indirilir; video yine de uyumsuz gelirse (AV1, VP9, "
                                  "60 fps…) indirme sonunda otomatik dönüştürülür.\nTüm telefon, tablet ve TV'lerde "
                                  "görüntülü oynar. Orijinal: sitenin en iyi biçimi (AV1/VP9 olabilir).")
        self.cb_fps = QComboBox()
        self.cb_fps.addItems(FPS_OPTIONS)
        self.cb_fps.setToolTip("Eski / düşük güçlü cihazlar 60 fps videoda görüntüyü gösteremeyebilir. "
                               "25 veya 30 fps her cihazda akıcı oynar.")
        self.cb_compat.currentTextChanged.connect(self._on_compat_change)
        self.cb_fps.currentTextChanged.connect(self._on_compat_change)
        g.addWidget(self.cb_compat, 3, 0)
        g.addWidget(self.cb_fps, 3, 1)
        c.lay.addLayout(g)
        self.q_hint = QLabel("")
        self.q_hint.setObjectName("hint")
        self.q_hint.hide()
        c.lay.addWidget(self.q_hint)

        chk = QHBoxLayout()
        chk.setSpacing(18)
        self.chk_playlist = QCheckBox("Listenin tamamı")
        self.chk_playlist.setToolTip("Bağlantı bir oynatma listesindeyse listedeki tüm videoları indir")
        self.chk_thumb = QCheckBox("Kapak resmi")
        self.chk_thumb.setToolTip("Kapak resmini dosyaya göm")
        self.chk_subs = QCheckBox("Altyazı (tr/en)")
        self.chk_clean = QCheckBox("Adları düzelt")
        self.chk_clean.setToolTip("Dosya adlarından emoji, ｜ ⧸ ： gibi garip karakterleri ve sondaki [video kimliği]ni "
                                  "temizler.\nBu karakterler bazı cihazlarda dosyanın / klasörün görünmemesine yol açar.")
        for w in (self.chk_playlist, self.chk_thumb, self.chk_subs, self.chk_clean):
            chk.addWidget(w)
            w.toggled.connect(self._save_options)
        chk.addStretch(1)
        c.lay.addLayout(chk)

        fr = QHBoxLayout()
        fr.setSpacing(8)
        self.folder_icon = QLabel()
        fr.addWidget(self.folder_icon)
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText(DEFAULT_DIR)
        self.folder_edit.editingFinished.connect(self._save_options)
        fr.addWidget(self.folder_edit, 1)
        b1 = self._btn("Gözat", G["folder_open"], self._browse)
        b2 = self._btn("", G["refresh"], lambda: (self.folder_edit.setText(DEFAULT_DIR), self._save_options()))
        b2.setToolTip("Varsayılan klasöre dön")
        b3 = self._btn("Aç", G["folder"], lambda: self._open_path(self._folder()))
        for b in (b1, b2, b3):
            fr.addWidget(b)
        c.lay.addLayout(fr)
        return c

    def _build_preview(self):
        c = Card("Önizleme", G["view"])
        self._cards.append(c)
        self.preview_site = QLabel("")
        self.preview_site.setObjectName("chip")
        self.preview_site.hide()
        c.head.addWidget(self.preview_site)
        self.stack = QStackedWidget()
        self.media = MediaView()
        self.media.on_click = self._play_toggle
        self.video = QVideoWidget()
        self.video.setAspectRatioMode(Qt.KeepAspectRatio)
        self.video.setAttribute(Qt.WA_StyledBackground, True)
        self.video.setStyleSheet("background: #000; border-radius: 12px;")
        self.stack.addWidget(self.media)
        self.stack.addWidget(self.video)
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        c.lay.addWidget(self.stack, 1)

        self.m_title = QLabel("Henüz önizleme yok")
        self.m_title.setObjectName("mediaTitle")
        self.m_title.setWordWrap(True)
        self.m_meta = QLabel("Bir bağlantı yapıştırın; bilgiler otomatik gelir. ▶ ile izleyin veya dinleyin.")
        self.m_meta.setObjectName("muted")
        self.m_meta.setWordWrap(True)
        c.lay.addWidget(self.m_title)
        c.lay.addWidget(self.m_meta)

        ctl = QHBoxLayout()
        ctl.setSpacing(8)
        self.b_play = QToolButton()
        self.b_play.setObjectName("play")
        self.b_play.setIconSize(QSize(18, 18))
        self.b_play.setCursor(Qt.PointingHandCursor)
        self.b_play.setToolTip("Oynat / duraklat")
        self.b_play.clicked.connect(self._play_toggle)
        ctl.addWidget(self.b_play)
        self.b_stop = self._icon_btn(G["stop"], "Durdur", self._stop_player)
        ctl.addWidget(self.b_stop)
        self.t_pos = QLabel("0:00")
        self.t_pos.setObjectName("time")
        ctl.addWidget(self.t_pos)
        self.seek = QSlider(Qt.Horizontal)
        self.seek.setRange(0, 0)
        self.seek.sliderMoved.connect(lambda v: self.player.setPosition(v))
        ctl.addWidget(self.seek, 1)
        self.t_dur = QLabel("0:00")
        self.t_dur.setObjectName("time")
        ctl.addWidget(self.t_dur)
        self.b_mute = self._icon_btn(G["volume"], "Sesi kapat / aç", self._toggle_mute)
        ctl.addWidget(self.b_mute)
        self.vol = QSlider(Qt.Horizontal)
        self.vol.setRange(0, 100)
        self.vol.setValue(int(self.s.get("volume", 70)))
        self.vol.setFixedWidth(80)
        ctl.addWidget(self.vol)
        c.lay.addLayout(ctl)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(self.vol.value() / 100)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.vol.valueChanged.connect(self._on_volume)
        self.player.positionChanged.connect(self._on_pos)
        self.player.durationChanged.connect(lambda d: (self.seek.setRange(0, d), self.t_dur.setText(fmt_time(d))))
        self.player.playbackStateChanged.connect(lambda _s: self._sync_play_icon())
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.errorOccurred.connect(self._on_player_error)
        self.preview_mode = None     # "remote" | "local"
        self.preview_audio = False
        self.preview_src = None
        self.thumb_pix = None
        return c

    def _build_queue(self):
        c = Card("İndirme kuyruğu", G["list"])
        self._cards.append(c)
        self.q_count = QLabel("")
        self.q_count.setObjectName("chip")
        c.head.insertWidget(c.head.count() - 1, self.q_count)   # başlığın hemen yanına (esneyen boşluktan önce)
        for text, glyph, slot in (("İptal", G["cancel"], self._cancel_selected),
                                  ("Yeniden dene", G["refresh"], self._retry_selected),
                                  ("Bitenleri temizle", G["clear"], self._clear_finished)):
            c.head.addWidget(self._btn(text, glyph, slot))
        tb = QTableWidget(0, len(self.COLS))
        tb.setHorizontalHeaderLabels(self.COLS)
        tb.verticalHeader().hide()
        tb.setShowGrid(False)
        tb.setAlternatingRowColors(True)
        tb.setSelectionBehavior(QAbstractItemView.SelectRows)
        tb.setSelectionMode(QAbstractItemView.ExtendedSelection)
        tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tb.setFocusPolicy(Qt.StrongFocus)
        tb.setWordWrap(False)
        tb.setIconSize(QSize(16, 16))
        tb.verticalHeader().setDefaultSectionSize(38)
        h = tb.horizontalHeader()
        h.setHighlightSections(False)
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for i, w in ((1, 150), (2, 170), (3, 100), (4, 70), (5, 160)):
            h.setSectionResizeMode(i, QHeaderView.Interactive)
            tb.setColumnWidth(i, w)
        h.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        tb.setItemDelegateForColumn(2, ProgressDelegate(self))
        tb.setContextMenuPolicy(Qt.CustomContextMenu)
        tb.customContextMenuRequested.connect(self._menu)
        tb.cellDoubleClicked.connect(self._on_double)
        QShortcut(QKeySequence.Delete, tb, activated=self._cancel_selected)
        self.table = tb
        c.lay.addWidget(tb, 1)
        self.empty_lbl = QLabel("Kuyruk boş. Bağlantı ekleyip “İndir”e basın; indirmeler burada görünür.")
        self.empty_lbl.setObjectName("muted")
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        c.lay.addWidget(self.empty_lbl)
        return c

    # ---------------------------------------------------------- tema
    def apply_theme(self):
        name = self.s.get("theme", "dark")
        self.t = t = THEMES.get(name, THEMES["dark"])
        cache = os.path.join(CONFIG_DIR, "ui")
        os.makedirs(cache, exist_ok=True)
        check = os.path.join(cache, "check.png")
        chev = os.path.join(cache, f"chev-{name}.png")
        glyph_pixmap(G["check"], "white", 16).save(check)
        glyph_pixmap(G["chevron"], t["muted"], 14).save(chev)
        QApplication.instance().setStyleSheet(build_qss(t, check, chev))
        roles = {"text": t["text"], "white": "white", "ok": t["ok"], "accent": t["accent"], "muted": t["muted"]}
        for w, glyph, role, px in self._icon_widgets:
            w.setIcon(glyph_icon(glyph, roles[role], px))
        for c in self._cards:
            c.retheme(t)
        self.theme_btn.setIcon(glyph_icon(G["sun"] if name == "dark" else G["moon"], t["text"], 20))
        self.folder_icon.setPixmap(glyph_pixmap(G["folder"], t["muted"], 18))
        self.media.theme = t
        self.media.update()
        self._sync_play_icon()
        self._dark_titlebar(name == "dark")
        for jid in list(self.jobs):
            self._refresh_row(self.jobs[jid])

    def _dark_titlebar(self, dark):
        if os.name != "nt":
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            val = ctypes.c_int(1 if dark else 0)
            for attr in (20, 19):
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), 4) == 0:
                    break
        except Exception:
            pass

    def _toggle_theme(self):
        self.s["theme"] = "light" if self.s.get("theme", "dark") == "dark" else "dark"
        save_settings(self.s)
        self.apply_theme()

    # ---------------------------------------------------------- seçenekler
    def _type_index(self):
        return max(0, self.seg_group.checkedId())

    def _load_options(self):
        # Yükleme sırasında kutucukların toggled sinyali _save_options'u tetiklemesin: aksi halde klasör alanı
        # henüz boşken ayarlar kaydedilir ve seçilen indirme klasörü varsayılana sıfırlanır.
        self._loading_opts = True
        s = self.s
        self.folder_edit.setText(s["folder"] or DEFAULT_DIR)
        idx = TYPES.index(s["type"]) if s["type"] in TYPES else 0
        self.seg_btns[idx].setChecked(True)
        self.chk_playlist.setChecked(bool(s["playlist"]))
        self.chk_thumb.setChecked(bool(s["thumbnail"]))
        self.chk_subs.setChecked(bool(s["subtitles"]))
        self.chk_clean.setChecked(bool(s.get("clean_names", True)))
        self.cb_compat.setCurrentText(s.get("compat") if s.get("compat") in COMPAT_MODES else COMPAT_MODES[0])
        self.cb_fps.setCurrentText(s.get("fps") if s.get("fps") in FPS_OPTIONS else FPS_OPTIONS[0])
        self._on_type_change(idx, save=False)
        self._loading_opts = False

    def _on_type_change(self, idx, save=True):
        audio = idx == 1
        self._loading = True
        self.cb_format.clear()
        self.cb_q.clear()
        if audio:
            self.cb_format.addItems(AUDIO_FORMATS)
            self.cb_format.setCurrentText(self.s["aformat"])
            self.cb_q.addItems(AUDIO_QUALITIES)
            self.cb_q.setCurrentText(self.s["aquality"])
            self.lbl_q.setText("Ses kalitesi")
        else:
            self.cb_format.addItems(VIDEO_FORMATS)
            self.cb_format.setCurrentText(self.s["vformat"])
            self.cb_q.addItems(RESOLUTIONS)
            self.cb_q.setCurrentText(self.s["resolution"])
            self.lbl_q.setText("Çözünürlük")
        self._loading = False
        self.chk_subs.setEnabled(idx == 0)
        for w in (self.lbl_compat, self.lbl_fps, self.cb_compat, self.cb_fps):
            w.setVisible(not audio)
        self._apply_compat_ui()
        self._update_hint()
        if save:
            self._save_options()

    def _apply_compat_ui(self):
        """Android uyumlu modda video biçimi her zaman MP4'tür; format seçimi kilitlenir."""
        video = self._type_index() != 1
        lock = video and self.cb_compat.currentText() == COMPAT_MODES[0]
        if video:
            self._loading = True
            self.cb_format.setCurrentText("mp4" if lock else self.s["vformat"])
            self._loading = False
        self.cb_format.setEnabled(not lock)
        self.cb_format.setToolTip("Android uyumlu modda biçim MP4'tür" if lock else "")

    def _on_compat_change(self, _v=None):
        if getattr(self, "_loading_opts", False):
            return
        self.s.update(compat=self.cb_compat.currentText(), fps=self.cb_fps.currentText())
        self._apply_compat_ui()
        save_settings(self.s)

    def _on_format_change(self, v):
        if getattr(self, "_loading", False) or not v:
            return
        self.s["aformat" if self._type_index() == 1 else "vformat"] = v
        save_settings(self.s)

    def _on_q_change(self, v):
        if getattr(self, "_loading", False) or not v:
            return
        self.s["aquality" if self._type_index() == 1 else "resolution"] = v
        save_settings(self.s)

    def _folder(self):
        return self.folder_edit.text().strip() or DEFAULT_DIR

    def _save_options(self):
        if getattr(self, "_loading_opts", False):
            return
        self.s.update(type=TYPES[self._type_index()], playlist=self.chk_playlist.isChecked(),
                      thumbnail=self.chk_thumb.isChecked(), subtitles=self.chk_subs.isChecked(),
                      clean_names=self.chk_clean.isChecked(), compat=self.cb_compat.currentText(),
                      fps=self.cb_fps.currentText(), folder=self._folder())
        save_settings(self.s)

    def _current_opts(self):
        self._save_options()
        return {k: self.s[k] for k in ("folder", "type", "vformat", "aformat", "resolution", "aquality",
                                         "playlist", "thumbnail", "subtitles", "parallel", "compat", "fps",
                                         "clean_names")}

    def _update_hint(self):
        p = self.preview
        if p and p.get("heights") and self._type_index() != 1:
            self.q_hint.setText(f"Bu videoda en yüksek çözünürlük: {p['heights'][0]}p")
            self.q_hint.show()
        else:
            self.q_hint.hide()

    @staticmethod
    def _kind_label(o):
        if o["type"] == "Sadece Ses":
            return f"Ses · {o['aformat']} · {o['aquality']}"
        short = "Video" if o["type"] == "Video + Ses" else "Sessiz video"
        fps = (o.get("fps") or "").split(" ")[0]
        fps = "" if not fps or fps == "Orijinal" else f" · {fps} fps"
        fmt = "Android MP4" if core.is_compat(o) else o["vformat"]
        return f"{short} · {fmt} · {o['resolution'].split(' ')[0]}{fps}"

    # ---------------------------------------------------------- eylemler
    def _paste(self):
        txt = QGuiApplication.clipboard().text().strip()
        if not txt:
            return
        cur = self.url_edit.toPlainText().strip()
        self.url_edit.setPlainText((cur + "\n" if cur else "") + txt)

    def _load_list(self):
        path, _ = QFileDialog.getOpenFileName(self, "URL listesi seç", "", "Metin dosyası (*.txt);;Tüm dosyalar (*.*)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                urls = parse_urls(f.read())
        except OSError as e:
            QMessageBox.critical(self, APP_NAME, str(e))
            return
        cur = self.url_edit.toPlainText().strip()
        self.url_edit.setPlainText((cur + "\n" if cur else "") + "\n".join(urls))
        self.toast(f"{len(urls)} bağlantı yüklendi")

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "İndirme klasörü seç",
                                             self._folder() if os.path.isdir(self._folder()) else os.path.expanduser("~"))
        if d:
            self.folder_edit.setText(os.path.normpath(d))
            self._save_options()

    def _open_path(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            os.startfile(path)
        except OSError:
            pass

    def _add(self):
        if not self.ytdlp:
            QMessageBox.warning(self, APP_NAME, "yt-dlp henüz kurulmadı.")
            return
        if self.updating:
            self.toast("yt-dlp güncelleniyor, birkaç saniye sonra tekrar deneyin")
            return
        urls = parse_urls(self.url_edit.toPlainText())
        if not urls:
            self.toast("Önce bir bağlantı yapıştırın")
            self.url_edit.setFocus()
            return
        opts = self._current_opts()
        for u in urls:
            title = self.preview["title"] if self.preview and self.preview.get("url") == u else None
            self._enqueue(u, dict(opts), title)
        self.url_edit.blockSignals(True)
        self.url_edit.clear()
        self.url_edit.blockSignals(False)
        self._save_queue()
        self.refresh_status()
        self.toast(f"{len(urls)} indirme kuyruğa eklendi")

    def _enqueue(self, url, opts, title=None):
        job = Job(url, opts, title)
        self.jobs[job.id] = job
        r = self.table.rowCount()
        self.table.insertRow(r)
        it = QTableWidgetItem(job.title)
        it.setData(Qt.UserRole, job.id)
        self.table.setItem(r, 0, it)
        for col in range(1, len(self.COLS)):
            self.table.setItem(r, col, QTableWidgetItem(""))
        self.rows[job.id] = it
        self._refresh_row(job)
        self.dl.add(job)
        return job

    def _refresh_row(self, j):
        it = self.rows.get(j.id)
        if it is None:
            return
        r = it.row()
        t = self.t
        audio = j.opts["type"] == "Sadece Ses"
        it.setText(j.title)
        it.setToolTip(f"{j.title}\n{j.url}")
        it.setIcon(glyph_icon(G["audio"] if audio else (G["video"] if j.opts["type"] == "Video + Ses" else G["silent"]),
                              t["muted"], 16))
        st = self.table.item(r, 1)
        label = {"Hata": "Hata — ayrıntı için çift tıklayın"}.get(j.status, j.status)
        st.setText(label)
        st.setForeground(QColor(_status_color(t, j.status)))
        glyph = {"Tamamlandı": G["check"], "Hata": G["error"], "İptal edildi": G["cancel"],
                 "Duraklatıldı": G["pause"], "Bağlantı bekleniyor…": G["warning"],
                 "Yeniden denenecek": G["history"], "İndiriliyor": G["download"],
                 "İşleniyor": G["sync"]}.get(j.status, G["convert"] if j.status.startswith("Dönüştür")
                                             else G["history"])
        st.setIcon(glyph_icon(glyph, _status_color(t, j.status), 14))
        pr = self.table.item(r, 2)
        try:
            val = float(j.percent.strip().rstrip("%")) if j.percent else None
        except ValueError:
            val = None
        if j.status == "Tamamlandı":
            val = 100.0
        pr.setData(Qt.UserRole, val)
        pr.setData(Qt.UserRole + 1, j.status)
        self.table.item(r, 3).setText(j.speed)
        self.table.item(r, 4).setText(j.eta)
        kd = self.table.item(r, 5)
        kd.setText(self._kind_label(j.opts))
        kd.setForeground(QColor(t["muted"]))

    def _selected_jobs(self):
        rows = sorted({i.row() for i in self.table.selectedItems()})
        out = []
        for r in rows:
            it = self.table.item(r, 0)
            jid = it.data(Qt.UserRole) if it else None
            if jid in self.jobs:
                out.append(self.jobs[jid])
        return out

    def _remove_row(self, j):
        it = self.rows.pop(j.id, None)
        if it is not None:
            self.table.removeRow(it.row())
        self.jobs.pop(j.id, None)

    def _cancel_selected(self):
        for j in self._selected_jobs():
            if j.status not in FINAL:
                self.dl.cancel(j)

    def _retry_selected(self):
        for j in self._selected_jobs():
            if j.status in ("Hata", "İptal edildi", "Duraklatıldı"):
                j.cancelled = j.shutdown = False
                j.status, j.percent, j.error = "Bekliyor", "", ""
                self._refresh_row(j)
                self.dl.add(j)
        self._save_queue()
        self.refresh_status()

    def _clear_finished(self):
        for j in list(self.jobs.values()):
            if j.status in ("Tamamlandı", "İptal edildi"):
                self._remove_row(j)
        self._save_queue()
        self.refresh_status()

    def _menu(self, pos):
        jobs = self._selected_jobs()
        if not jobs:
            return
        j = jobs[0]
        t = self.t
        m = QMenu(self)
        done = j.status == "Tamamlandı" and j.file and os.path.exists(j.file)

        def act(text, glyph, slot, enabled=True):
            a = QAction(glyph_icon(glyph, t["text"], 16), text, m)
            a.setEnabled(enabled)
            a.triggered.connect(slot)
            m.addAction(a)

        act("Önizle (oynat)", G["play"], lambda: self._preview_local(j) if done else self._preview_url(j.url))
        act("Dosyayı aç", G["file"], lambda: os.startfile(j.file), bool(done))
        act("Klasörde göster", G["folder_open"], lambda: self._show_in_folder(j))
        m.addSeparator()
        act("İptal et", G["cancel"], self._cancel_selected, j.status not in FINAL)
        act("Yeniden dene", G["refresh"], self._retry_selected, j.status in ("Hata", "İptal edildi", "Duraklatıldı"))
        act("Hata ayrıntısı", G["info"], lambda: self._show_error(j), j.status == "Hata")
        act("Bağlantıyı kopyala", G["copy"],
            lambda: QGuiApplication.clipboard().setText("\n".join(x.url for x in jobs)))
        m.addSeparator()
        act("Listeden kaldır", G["delete"], lambda: [self._remove_row(x) for x in jobs if x.status in FINAL]
            and (self._save_queue(), self.refresh_status()))
        m.exec(self.table.viewport().mapToGlobal(pos))

    def _show_in_folder(self, j):
        if j.file and os.path.exists(j.file):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(j.file)])
        else:
            self._open_path(j.opts["folder"])

    def _show_error(self, j):
        detail = "\n".join(j.tail[-15:])
        box = QMessageBox(self)
        box.setWindowTitle("Hata ayrıntısı")
        box.setIcon(QMessageBox.Warning)
        box.setText(j.error or "Hata kaydı yok.")
        box.setDetailedText((detail + "\n\n" if detail else "") + f"Günlük: {LOG_FILE}")
        box.exec()

    def _on_double(self, row, _col):
        it = self.table.item(row, 0)
        j = self.jobs.get(it.data(Qt.UserRole)) if it else None
        if not j:
            return
        if j.status == "Tamamlandı" and j.file and os.path.exists(j.file):
            self._preview_local(j)
        elif j.status == "Hata":
            self._show_error(j)
        else:
            self._preview_url(j.url)

    # ---------------------------------------------------------- önizleme
    def _auto_probe(self):
        urls = parse_urls(self.url_edit.toPlainText())
        if len(urls) == 1 and urls[0] != self.last_probed and urls[0].startswith("http"):
            self._preview_url(urls[0], autoplay=False)

    def _preview_clicked(self):
        urls = parse_urls(self.url_edit.toPlainText())
        if urls:
            self._preview_url(urls[0], autoplay=False)
        else:
            sel = self._selected_jobs()
            if sel:
                self._preview_url(sel[0].url, autoplay=False)
            else:
                self.toast("Önizlemek için bir bağlantı yapıştırın")

    def _preview_url(self, url, autoplay=False):
        if not self.ytdlp:
            return
        self._stop_player()
        self.last_probed = url
        self.preview_token += 1
        tok = self.preview_token
        self.preview = None
        self.preview_mode = "remote"
        self.preview_src = None
        self.thumb_pix = None
        self.stack.setCurrentWidget(self.media)
        self.media.set_state(None, "Bilgiler alınıyor…")
        self.m_title.setText("Yükleniyor…")
        self.m_meta.setText(url)
        self.preview_site.hide()
        self._autoplay = autoplay
        self._bg(lambda: core.probe(self.ytdlp, url), "probe", tok)

    def _on_probe(self, tok, ok, res):
        if tok != self.preview_token:
            return
        if not ok:
            self.preview = None
            self.media.set_state(None, "Önizleme alınamadı.")
            self.m_title.setText("Önizleme alınamadı")
            self.m_meta.setText(str(res)[:300])
            return
        p = res
        self.preview = p
        title = p["title"]
        if p["is_playlist"]:
            title = f"{p['playlist_title'] or 'Oynatma listesi'}  ·  {p['count']} öğe"
        self.m_title.setText(title)
        bits = []
        if p["is_playlist"]:
            bits.append(f"İlk öğe: {p['title']}")
        if p["uploader"]:
            bits.append(p["uploader"])
        if p["duration"]:
            bits.append(fmt_time(p["duration"] * 1000))
        if p["views"]:
            bits.append(f"{fmt_count(p['views'])} görüntülenme")
        if len(p["date"]) == 8:
            bits.append(f"{p['date'][6:]}.{p['date'][4:6]}.{p['date'][:4]}")
        if p["heights"]:
            bits.append(f"en yüksek {p['heights'][0]}p")
        self.m_meta.setText("  ·  ".join(bits))
        if p["site"]:
            self.preview_site.setText(p["site"])
            self.preview_site.show()
        if p["is_playlist"] and not self.chk_playlist.isChecked():
            self.toast("Bu bir oynatma listesi. Tamamı için “Oynatma listesinin tamamı”nı işaretleyin.")
        self.media.set_state(None, "", overlay=True)
        self.t_dur.setText(fmt_time(p["duration"] * 1000) if p["duration"] else "0:00")
        self._update_hint()
        if p["thumbnail"]:
            self._bg(lambda: core.fetch_bytes(p["thumbnail"]), "thumb", tok)
        if getattr(self, "_autoplay", False):
            self._play_toggle()

    def _on_thumb(self, tok, ok, data):
        if tok != self.preview_token or not ok:
            return
        pm = QPixmap()
        if pm.loadFromData(data):
            self.thumb_pix = pm
            if self.stack.currentWidget() is self.media:
                self.media.set_state(pm, "", overlay=self.player.playbackState() != QMediaPlayer.PlayingState,
                                     badge=self.media.badge)

    def _preview_local(self, j):
        self._stop_player()
        self.preview_token += 1
        self.preview_mode = "local"
        self.preview = None
        self.preview_audio = os.path.splitext(j.file)[1].lower() in AUDIO_EXT
        self.preview_src = QUrl.fromLocalFile(j.file)
        self.m_title.setText(os.path.basename(j.file))
        try:
            size = os.path.getsize(j.file) / 1048576
            self.m_meta.setText(f"İndirilen dosya  ·  {size:.1f} MB  ·  {os.path.dirname(j.file)}")
        except OSError:
            self.m_meta.setText(j.file)
        self.preview_site.setText("Yerel dosya")
        self.preview_site.show()
        self.thumb_pix = None
        self._start_playback()

    def _play_toggle(self):
        st = self.player.playbackState()
        if st == QMediaPlayer.PlayingState:
            self.player.pause()
            return
        if st == QMediaPlayer.PausedState and self.preview_src is not None:
            self.player.play()
            return
        if self.preview_mode == "local" and self.preview_src is not None:
            self._start_playback()
            return
        if not self.preview:
            self._preview_clicked() if not self.last_probed else self._preview_url(self.last_probed, autoplay=True)
            return
        audio = self._type_index() == 1 or not self.preview.get("has_video", True)
        self.preview_audio = audio
        self.media.set_state(self.thumb_pix, "" if self.thumb_pix else "Akış hazırlanıyor…",
                             badge="Akış hazırlanıyor…")
        self.stack.setCurrentWidget(self.media)
        tok = self.preview_token
        url = self.preview["item_url"]
        self._bg(lambda: core.stream_url(self.ytdlp, url, audio), "stream", tok)

    def _on_stream(self, tok, ok, res):
        if tok != self.preview_token:
            return
        if not ok:
            self.media.set_state(self.thumb_pix, "" if self.thumb_pix else "Oynatılamadı", overlay=True,
                                 badge="Oynatılamadı")
            self.toast("Önizleme oynatılamadı: " + str(res)[:120])
            return
        self.preview_src = QUrl(res)
        self._start_playback()

    def _start_playback(self):
        self.player.setSource(self.preview_src)
        if self.preview_audio:
            self.stack.setCurrentWidget(self.media)
            self.media.set_state(self.thumb_pix, "" if self.thumb_pix else " ", badge="♪  Ses önizlemesi")
        else:
            self.stack.setCurrentWidget(self.video)
        self.player.play()

    def _stop_player(self):
        self.player.stop()
        self.player.setSource(QUrl())
        self.seek.setValue(0)
        self.t_pos.setText("0:00")
        if self.stack.currentWidget() is self.video or self.media.badge:
            self.stack.setCurrentWidget(self.media)
            self.media.set_state(self.thumb_pix, "" if (self.thumb_pix or self.preview) else
                                 "Bir bağlantı yapıştırın; önizleme burada görünür.",
                                 overlay=bool(self.preview or self.preview_mode == "local"))

    def _on_pos(self, pos):
        if not self.seek.isSliderDown():
            self.seek.setValue(pos)
        self.t_pos.setText(fmt_time(pos))

    def _on_media_status(self, st):
        if st in (QMediaPlayer.LoadingMedia, QMediaPlayer.StalledMedia) and self.preview_audio:
            self.media.set_state(self.thumb_pix, "", badge="Yükleniyor…")
        elif st in (QMediaPlayer.BufferedMedia, QMediaPlayer.LoadedMedia) and self.preview_audio:
            self.media.set_state(self.thumb_pix, "" if self.thumb_pix else " ", badge="♪  Ses önizlemesi")
        elif st == QMediaPlayer.EndOfMedia:
            self._stop_player()

    def _on_player_error(self, _err, msg):
        if msg:
            self.toast("Oynatıcı hatası: " + msg[:120])

    def _sync_play_icon(self):
        playing = self.player.playbackState() == QMediaPlayer.PlayingState
        self.b_play.setIcon(glyph_icon(G["pause"] if playing else G["play"], "white", 18))
        if self.stack.currentWidget() is self.media and not self.media.badge:
            self.media.overlay = not playing and bool(self.preview or self.preview_mode == "local")
            self.media.update()

    def _on_volume(self, v):
        self.audio.setVolume(v / 100)
        self.audio.setMuted(False)
        self.b_mute.setIcon(glyph_icon(G["volume"], self.t["text"], 18))
        self.s["volume"] = v

    def _toggle_mute(self):
        self.audio.setMuted(not self.audio.isMuted())
        self.b_mute.setIcon(glyph_icon(G["mute"] if self.audio.isMuted() else G["volume"], self.t["text"], 18))

    # ---------------------------------------------------------- arka plan işleri
    def _bg(self, fn, kind, token=None):
        def run():
            try:
                self.events.put((kind, (token, True, fn())))
            except Exception as e:  # noqa: BLE001
                self.events.put((kind, (token, False, e)))
        threading.Thread(target=run, daemon=True).start()

    def _poll(self):
        changed, finished = set(), []
        try:
            for _ in range(500):
                kind, data = self.events.get_nowait()
                if kind == "update":
                    changed.add(data.id)
                elif kind == "done":
                    finished.append(data)
                elif kind == "probe":
                    self._on_probe(*data)
                elif kind == "thumb":
                    self._on_thumb(*data)
                elif kind == "stream":
                    self._on_stream(*data)
                elif kind == "install":
                    if self._install_dlg:
                        self._install_dlg.progress(*data)
                elif kind == "installed":
                    self._on_installed(*data)
                elif kind == "version":
                    self.ytdlp_ver = data[2] if data[1] else ""
                    self.refresh_status()
                elif kind == "ytdlp_updated":
                    self._on_ytdlp_updated(*data)
                elif kind == "app_check":
                    self._on_app_check(*data)
                elif kind == "app_dl_progress":
                    if self._update_dlg:
                        self._update_dlg.progress(*data)
                elif kind == "app_dl":
                    self._on_app_downloaded(*data)
        except queue.Empty:
            pass
        for jid in changed:
            if jid in self.jobs:
                self._refresh_row(self.jobs[jid])
        if finished:
            self._save_queue()
            self.refresh_status()
            if self.dl.active_count() == 0:
                ok = sum(1 for j in self.jobs.values() if j.status == "Tamamlandı")
                err = sum(1 for j in self.jobs.values() if j.status == "Hata")
                self.toast(f"Tüm indirmeler bitti — {ok} başarılı" + (f", {err} hatalı" if err else ""))
                QApplication.alert(self)
        elif changed:
            self.refresh_status()

    def refresh_status(self):
        n = self.dl.active_count()
        self._keep_awake(n > 0 and bool(self.s["prevent_sleep"]))
        total = len(self.jobs)
        done = sum(1 for j in self.jobs.values() if j.status == "Tamamlandı")
        self.q_count.setText(f"{done}/{total} tamamlandı" if total else "boş")
        self.empty_lbl.setVisible(total == 0)
        self.table.setVisible(total > 0)
        if n:
            self.st_left.setText(f"{n} indirme sürüyor / bekliyor  ·  aynı anda {self.dl.parallel}")
            self.setWindowTitle(f"({n}) {APP_NAME} {APP_VERSION}")
        else:
            self.st_left.setText("Hazır" if not total else f"Kuyruk boşta  ·  {done} indirme tamamlandı")
            self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.st_right.setText(f"yt-dlp {self.ytdlp_ver}  ·  ffmpeg {'hazır' if self.ffmpeg else 'yok'}"
                              if self.ytdlp else "yt-dlp kurulu değil")

    def toast(self, text, ms=4000):
        self.toast_lbl.setText(text)
        self.toast_lbl.adjustSize()
        w, h = self.toast_lbl.width(), self.toast_lbl.height()
        self.toast_lbl.move(self.width() - w - 24, self.height() - h - 44)
        self.toast_lbl.show()
        self.toast_lbl.raise_()
        self.toast_timer.start(ms)

    def _keep_awake(self, on):
        if os.name != "nt" or self._awake == on:
            return
        self._awake = on
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if on else 0))
        except Exception:
            pass

    # ---------------------------------------------------------- kalıcı kuyruk
    def _save_queue(self):
        import json
        items = [{"url": j.url, "opts": j.opts, "title": j.title}
                 for j in self.jobs.values() if j.status not in ("Tamamlandı", "İptal edildi", "Hata")]
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(QUEUE_FILE, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def _restore_queue(self):
        import json
        if self._restored:
            return
        self._restored = True
        try:
            with open(QUEUE_FILE, encoding="utf-8-sig") as f:
                items = json.load(f)
        except Exception:
            return
        for it in items:
            if it.get("url"):
                self._enqueue(it["url"], dict(DEFAULTS, **it.get("opts", {})), it.get("title"))
        if items:
            self.toast(f"Yarım kalan {len(items)} indirme kaldığı yerden sürdürülüyor")
        self.refresh_status()

    # ---------------------------------------------------------- araç kurulumu ve güncellemeler
    def _install_missing(self):
        need = [n for n, p in (("yt-dlp", self.ytdlp), ("ffmpeg", self.ffmpeg)) if not p]
        self.updating = True
        self._install_dlg = InstallDialog(self, need)
        self._install_dlg.show()

        def work():
            try:
                res = core.install_tools(not self.ytdlp, not self.ffmpeg,
                                         lambda t, p: self.events.put(("install", (t, p))))
                self.events.put(("installed", (True, res, "")))
            except Exception as e:  # noqa: BLE001
                self.events.put(("installed", (False, (None, None), str(e))))
        threading.Thread(target=work, daemon=True).start()

    def _on_installed(self, ok, paths, err):
        self.updating = False
        if self._install_dlg:
            self._install_dlg.hide()
            self._install_dlg.deleteLater()
            self._install_dlg = None
        self.ytdlp = self.ytdlp or paths[0]
        self.ffmpeg = self.ffmpeg or paths[1]
        self.dl.ytdlp, self.dl.ffmpeg = self.ytdlp, self.ffmpeg
        if ok and self.ytdlp and self.ffmpeg:
            self.toast("yt-dlp ve ffmpeg hazır")
            self._tools_ready(True)
        else:
            r = QMessageBox.question(self, APP_NAME, "yt-dlp / ffmpeg otomatik kurulamadı.\n\n"
                                     f"{err or 'Bilinmeyen hata'}\n\nTekrar denensin mi?",
                                     QMessageBox.Retry | QMessageBox.Cancel)
            if r == QMessageBox.Retry:
                self._install_missing()
        self.refresh_status()

    def _tools_ready(self, just_installed):
        self._bg(lambda: core.ytdlp_version(self.ytdlp), "version")
        self._restore_queue()
        if just_installed:
            self.s["last_update_check"] = time.time()
            save_settings(self.s)
        elif self.s.get("auto_update") and time.time() - float(self.s.get("last_update_check", 0)) > UPDATE_INTERVAL:
            QTimer.singleShot(2000, lambda: self.update_ytdlp(auto=True))
        if self.s.get("app_update_check", True):
            QTimer.singleShot(3000, lambda: self.check_app_update(manual=False))
        self.refresh_status()

    def update_ytdlp(self, auto=False):
        if self.updating or not self.ytdlp:
            return
        if self.dl.active_count():
            if auto:
                QTimer.singleShot(60000, lambda: self.update_ytdlp(auto=True))
            else:
                QMessageBox.information(self, APP_NAME, "İndirmeler sürerken yt-dlp güncellenemez.\n"
                                                        "Kuyruk bitince tekrar deneyin.")
            return
        self.updating = True
        self.st_left.setText("yt-dlp güncelleniyor…")
        self._bg(lambda: core.update_ytdlp(self.ytdlp), "ytdlp_updated", auto)

    def _on_ytdlp_updated(self, auto, ok, res):
        self.updating = False
        good, msg = res if ok else (False, str(res))
        if good:
            self.s["last_update_check"] = time.time()
            save_settings(self.s)
        self._bg(lambda: core.ytdlp_version(self.ytdlp), "version")
        if not auto:
            (QMessageBox.information if good else QMessageBox.warning)(self, APP_NAME, msg or "Bilinmeyen hata")
        elif good and "güncellendi" in msg:
            self.toast(msg)
        self.refresh_status()

    def check_app_update(self, manual=False):
        if manual:
            self.st_left.setText("Uygulama güncellemesi denetleniyor…")
        self._bg(core.check_app_update, "app_check", manual)

    def _on_app_check(self, manual, ok, res):
        self.refresh_status()
        if not ok:
            if manual:
                QMessageBox.warning(self, APP_NAME, f"Güncelleme denetlenemedi:\n{res}")
            return
        if not res:
            if manual:
                QMessageBox.information(self, APP_NAME, f"En güncel sürümü kullanıyorsunuz ({APP_VERSION}).")
            return
        self.app_update = res
        self.update_btn.setText(f"  Yeni sürüm {res['version']}")
        self.update_btn.show()
        if manual or res["version"] != self.s.get("skipped_version"):
            if manual:
                self._show_update_dialog()
            else:
                self.toast(f"Yeni sürüm {res['version']} hazır — sağ üstten güncelleyebilirsiniz", 7000)
        else:
            self.update_btn.hide()

    def _show_update_dialog(self):
        if not self.app_update:
            return
        self._update_dlg = UpdateDialog(self, self.app_update)
        self._update_dlg.exec()
        self._update_dlg = None

    def start_app_download(self, info, dlg):
        def work():
            try:
                path = core.download_app_update(info, lambda d, t: self.events.put(("app_dl_progress", (d, t))))
                self.events.put(("app_dl", (True, path)))
            except Exception as e:  # noqa: BLE001
                self.events.put(("app_dl", (False, str(e))))
        threading.Thread(target=work, daemon=True).start()

    def _on_app_downloaded(self, ok, res):
        dlg = self._update_dlg
        if not ok:
            if dlg:
                dlg.failed(res)
            else:
                QMessageBox.warning(self, APP_NAME, res)
            return
        n = self.dl.active_count()
        if n and QMessageBox.question(self, APP_NAME, f"{n} indirme sürüyor. Güncelleme için uygulama yeniden "
                                      "başlatılacak; indirmeler kaldığı yerden devam edecek.\n\nŞimdi yeniden başlatılsın mı?"
                                      ) != QMessageBox.Yes:
            if dlg:
                dlg.failed("Yeniden başlatma ertelendi. Güncellemeyi daha sonra yeniden başlatın.")
            return
        self._shutdown_jobs()
        try:
            core.apply_app_update(res)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, APP_NAME, f"Güncelleme uygulanamadı:\n{e}")
            return
        self._force_quit = True
        QApplication.quit()

    def _open_converter(self):
        if not self.ffmpeg:
            QMessageBox.warning(self, APP_NAME, "ffmpeg henüz kurulmadı.")
            return
        if self._conv_dlg is None:
            self._conv_dlg = ConverterDialog(self)
        self._conv_dlg.conv.ffmpeg = self.ffmpeg
        self._conv_dlg.show()
        self._conv_dlg.raise_()
        self._conv_dlg.activateWindow()

    def _open_settings(self):
        SettingsDialog(self).exec()

    # ---------------------------------------------------------- sürükle-bırak ve kapanış
    def dragEnterEvent(self, e):
        if e.mimeData().hasText() or e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        md = e.mimeData()
        text = "\n".join(u.toString() for u in md.urls()) if md.hasUrls() else md.text()
        cur = self.url_edit.toPlainText().strip()
        self.url_edit.setPlainText((cur + "\n" if cur else "") + text.strip())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.toast_lbl.isVisible():
            self.toast_lbl.move(self.width() - self.toast_lbl.width() - 24,
                                self.height() - self.toast_lbl.height() - 44)

    def _shutdown_jobs(self):
        self._save_queue()   # öldürmeden önce kaydet ki yarım kalanlar listede kalsın
        for j in list(self.jobs.values()):
            if j.status not in FINAL:
                j.shutdown = True
                self.dl.cancel(j)
        self._keep_awake(False)
        self._save_options()
        save_settings(self.s)

    def closeEvent(self, e):
        if getattr(self, "_force_quit", False):
            e.accept()
            return
        n = self.dl.active_count()
        if n and QMessageBox.question(
                self, APP_NAME, f"{n} indirme hâlâ sürüyor/bekliyor.\n\nKapatırsanız duraklatılacak ve "
                                "uygulamayı bir sonraki açışınızda kaldığı yerden otomatik devam edecek.\n\nÇıkılsın mı?"
        ) != QMessageBox.Yes:
            e.ignore()
            return
        conv = self._conv_dlg.conv.active_count() if self._conv_dlg else 0
        if conv and QMessageBox.question(
                self, APP_NAME, f"{conv} video dönüştürülüyor/bekliyor.\n\nKapatırsanız dönüştürme iptal edilecek "
                                "(orijinal dosyalar etkilenmez).\n\nÇıkılsın mı?") != QMessageBox.Yes:
            e.ignore()
            return
        if self._conv_dlg:
            self._conv_dlg.cancel_all()
        self.player.stop()
        self._shutdown_jobs()
        e.accept()


def create_app(argv=None):
    """QApplication'ı oluşturur ve ikon yazı tipini seçer (Windows 11: Fluent, Windows 10: MDL2)."""
    global ICON_FONT
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("VideoMuzikIndirici.App")
        except Exception:
            pass
    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    fams = QFontDatabase.families()
    ICON_FONT = "Segoe Fluent Icons" if "Segoe Fluent Icons" in fams else "Segoe MDL2 Assets"
    return app


def main():
    app = create_app()
    win = MainWindow(just_updated="--guncellendi" in sys.argv)
    win.show()
    win._dark_titlebar(win.s.get("theme", "dark") == "dark")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
