# -*- coding: utf-8 -*-
"""
Video Müzik İndirici - yt-dlp tabanlı masaüstü video / müzik indirme yöneticisi.
https://github.com/mehmet-cizmeci/video-muzik-indirici
Tek URL veya URL listesi alır, indirmeleri arka planda (kuyrukta) yürütür.
"""
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "Video Müzik İndirici"
APP_VERSION = "1.0.0"
APP_URL = "https://github.com/mehmet-cizmeci/video-muzik-indirici"
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "VideoMuzikIndirici")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "Video Muzik Indirici")
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
FROZEN = getattr(sys, "frozen", False)
APP_DIR = os.path.dirname(sys.executable if FROZEN else os.path.abspath(__file__))
# otomatik kurulan yt-dlp / ffmpeg buraya iner (yazma izni gerektirmez)
BIN_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "VideoMuzikIndirici", "bin")
QUEUE_FILE = os.path.join(CONFIG_DIR, "queue.json")
LOG_FILE = os.path.join(CONFIG_DIR, "indirici.log")
FINAL = ("Tamamlandı", "Hata", "İptal edildi", "Duraklatıldı")
STALL_SECONDS = 90        # bu kadar süre veri gelmezse bağlantı askıda sayılır, yeniden başlatılır
MAX_FAILS = 8             # internet varken üst üste ilerlemesiz hata sayısı sınırı
PERMANENT_ERRORS = (
    "unsupported url", "is not a valid url", "video unavailable", "private video",
    "this video is unavailable", "has been removed", "copyright", "sign in to confirm your age",
    "members-only", "join this channel", "http error 404", "no video formats found",
    "requested format is not available", "account associated with this video has been terminated",
)
YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL = ("https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/"
              "ffmpeg-master-latest-win64-gpl.zip")

TYPES = ["Video + Ses", "Sadece Ses", "Sadece Video (sessiz)"]
VIDEO_FORMATS = ["mp4", "mkv", "webm"]
AUDIO_FORMATS = ["mp3", "m4a", "opus", "flac", "wav"]
RESOLUTIONS = ["En iyi", "2160p (4K)", "1440p", "1080p", "720p", "480p", "360p", "240p"]
AUDIO_QUALITIES = ["En iyi", "320 kbps", "256 kbps", "192 kbps", "128 kbps", "96 kbps"]
THUMB_OK = {"mp3", "m4a", "mp4", "mkv", "flac", "opus"}

DEFAULTS = {
    "folder": DEFAULT_DIR,
    "type": TYPES[0],
    "vformat": "mp4",
    "aformat": "mp3",
    "resolution": "1080p",
    "aquality": "En iyi",
    "playlist": False,
    "thumbnail": True,
    "subtitles": False,
    "parallel": 2,
    "auto_update": True,
    "prevent_sleep": True,
    "last_update_check": 0,
}
UPDATE_INTERVAL = 24 * 3600  # otomatik güncelleme en fazla günde bir


# ----------------------------------------------------------------- yardımcılar
def find_exe(name):
    path = shutil.which(name)
    if path:
        return path
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(BIN_DIR, name + ".exe"),
        os.path.join(local, "Microsoft", "WinGet", "Links", name + ".exe"),
        os.path.join(APP_DIR, name + ".exe"),
    ]
    pkg_root = os.path.join(local, "Microsoft", "WinGet", "Packages")
    if os.path.isdir(pkg_root):
        for root, _dirs, files in os.walk(pkg_root):
            if name + ".exe" in files:
                candidates.append(os.path.join(root, name + ".exe"))
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def download_file(url, dest, progress):
    """url'yi dest'e indirir; progress(indirilen, toplam) çağrılır."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "VideoMuzikIndirici/" + APP_VERSION})
    tmp = dest + ".part"
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            progress(done, total)
    os.replace(tmp, dest)


def install_tools(need_ytdlp, need_ffmpeg, report):
    """Eksik araçları BIN_DIR'e kurar. report(metin, yüzde|None). (ytdlp, ffmpeg) yollarını döner."""
    import zipfile
    os.makedirs(BIN_DIR, exist_ok=True)
    mb = lambda b: f"{b / 1048576:.1f} MB"  # noqa: E731

    def prog(label):
        def f(done, total):
            pct = done * 100 / total if total else None
            report(f"{label} indiriliyor… {mb(done)}" + (f" / {mb(total)}" if total else ""), pct)
        return f

    if need_ytdlp:
        download_file(YTDLP_URL, os.path.join(BIN_DIR, "yt-dlp.exe"), prog("yt-dlp"))
    if need_ffmpeg:
        zpath = os.path.join(BIN_DIR, "ffmpeg.zip")
        download_file(FFMPEG_URL, zpath, prog("ffmpeg"))
        report("ffmpeg arşivden çıkarılıyor…", None)
        with zipfile.ZipFile(zpath) as z:
            for member in z.namelist():
                base = os.path.basename(member)
                if base in ("ffmpeg.exe", "ffprobe.exe"):
                    with z.open(member) as src, open(os.path.join(BIN_DIR, base), "wb") as dst:
                        shutil.copyfileobj(src, dst)
        os.remove(zpath)
    return find_exe("yt-dlp"), find_exe("ffmpeg")


def load_settings():
    s = dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, encoding="utf-8-sig") as f:
            s.update(json.load(f))
    except Exception:
        pass
    return s


def save_settings(s):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def parse_urls(text):
    urls = []
    for line in text.replace(",", "\n").split():
        line = line.strip()
        if line and not line.startswith("#") and line not in urls:
            urls.append(line)
    return urls


def build_command(ytdlp, ffmpeg, url, opts):
    """opts: indirme anındaki seçeneklerin kopyası."""
    cmd = [
        ytdlp, url,
        "--newline", "--no-colors", "--encoding", "utf-8",
        "--no-simulate", "--ignore-config",
        "--print", "before_dl:TITLE|%(playlist_index|)s|%(n_entries|)s|%(title)s",
        "--print", "after_move:FILE|%(filepath)s",
        "--no-quiet", "--progress",  # --print sessiz moda geçirir; ilerleme ve log satırları geri açılır
        "-P", opts["folder"],
        "-o", "%(title).180B [%(id)s].%(ext)s",
        "--progress-template",
        "download:PROG|%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
        "--embed-metadata",
        # ağ kesintilerine dayanıklılık: yarım kalan .part dosyasından devam eder
        "--continue", "--socket-timeout", "30",
        "--retries", "15", "--fragment-retries", "15", "--file-access-retries", "10",
        "--retry-sleep", "http:exp=1:30", "--retry-sleep", "fragment:exp=1:30",
        "--yes-playlist" if opts["playlist"] else "--no-playlist",
    ]
    if opts["playlist"]:
        cmd += ["-o", "%(playlist_title|Liste).100B/%(playlist_index|0)03d - %(title).160B [%(id)s].%(ext)s"]
    if ffmpeg:
        cmd += ["--ffmpeg-location", ffmpeg]

    kind = opts["type"]
    res = opts["resolution"]
    height = None if res == "En iyi" else res.split("p")[0]

    if kind == "Sadece Ses":
        fmt = opts["aformat"]
        q = opts["aquality"]
        quality = "0" if q == "En iyi" else q.split()[0] + "K"
        cmd += ["-f", "ba/b", "-x", "--audio-format", fmt, "--audio-quality", quality]
        if opts["thumbnail"] and fmt in THUMB_OK:
            cmd += ["--embed-thumbnail", "--convert-thumbnails", "jpg"]
    else:
        fmt = opts["vformat"]
        sort = []
        if height:
            sort.append("res:" + height)
        if fmt == "mp4":
            sort.append("ext:mp4:m4a")
        elif fmt == "webm":
            sort.append("ext:webm:webm")
        if kind == "Video + Ses":
            cmd += ["-f", "bv*+ba/b", "--merge-output-format", fmt]
        else:
            cmd += ["-f", "bv/b"]
        if sort:
            cmd += ["-S", ",".join(sort)]
        if fmt in ("mp4", "mkv"):
            cmd += ["--remux-video", fmt]
        if opts["thumbnail"] and fmt in THUMB_OK:
            cmd += ["--embed-thumbnail", "--convert-thumbnails", "jpg"]
        if opts["subtitles"] and kind == "Video + Ses":
            cmd += ["--write-subs", "--sub-langs", "tr.*,en.*", "--embed-subs"]
    return cmd


# ----------------------------------------------------------------- iş öğesi
def internet_ok():
    import socket
    for host, port in (("1.1.1.1", 443), ("8.8.8.8", 53), ("www.google.com", 443)):
        try:
            socket.create_connection((host, port), timeout=4).close()
            return True
        except OSError:
            continue
    return False


def write_log(job):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 2_000_000:
            os.replace(LOG_FILE, LOG_FILE + ".old")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} | {job.status} | {job.url}\n")
            if job.status != "Tamamlandı":
                f.write("\n".join(job.tail) + "\n")
    except Exception:
        pass


def is_permanent(err):
    low = (err or "").lower()
    return any(p in low for p in PERMANENT_ERRORS)


class Job:
    _next = 1

    def __init__(self, url, opts, title=None):
        self.id = Job._next
        Job._next += 1
        self.url = url
        self.opts = opts
        self.title = title or url
        self.status = "Bekliyor"
        self.percent = ""
        self.speed = ""
        self.eta = ""
        self.file = None
        self.error = ""
        self.proc = None
        self.cancelled = False
        self.shutdown = False   # uygulama kapanırken durduruldu (sonraki açılışta devam)
        self.stalled = False
        self.last_out = 0.0
        self.tail = []          # son çıktı satırları (hata ayrıntısı için)


class Downloader:
    """Kuyruk ve işçi iş parçacıkları. Arayüze olayları self.events ile iletir."""

    def __init__(self, ytdlp, ffmpeg, events):
        self.ytdlp = ytdlp
        self.ffmpeg = ffmpeg
        self.events = events
        self.pending = []
        self.running = set()
        self.lock = threading.Lock()
        self.parallel = 2

    def add(self, job):
        with self.lock:
            self.pending.append(job)
        self.pump()

    def pump(self):
        with self.lock:
            while self.pending and len(self.running) < self.parallel:
                job = self.pending.pop(0)
                if job.cancelled:
                    continue
                self.running.add(job.id)
                threading.Thread(target=self._run, args=(job,), daemon=True).start()

    def active_count(self):
        with self.lock:
            return len(self.running) + len(self.pending)

    def _kill(self, job):
        p = job.proc
        if p and p.poll() is None:
            try:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)],
                               creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                p.kill()

    def cancel(self, job):
        job.cancelled = True
        with self.lock:
            if job in self.pending:
                self.pending.remove(job)
                job.status = "Duraklatıldı" if job.shutdown else "İptal edildi"
                self.events.put(("update", job))
                return
        self._kill(job)

    def _set(self, job, status, eta=""):
        job.status, job.speed, job.eta = status, "", eta
        self.events.put(("update", job))

    def _sleep(self, job, seconds):
        """İptal edilebilir bekleme. İptal edilirse False döner."""
        end = time.time() + seconds
        while time.time() < end:
            if job.cancelled:
                return False
            time.sleep(0.5)
        return not job.cancelled

    def _run(self, job):
        fails = 0
        attempt = 0
        try:
            while True:
                attempt += 1
                code, err, progressed = self._attempt(job, attempt)
                if job.cancelled:
                    job.status = "Duraklatıldı" if job.shutdown else "İptal edildi"
                    break
                if code == 0:
                    job.status, job.percent, job.error = "Tamamlandı", "100%", ""
                    break
                job.error = err or f"yt-dlp çıkış kodu {code}"
                if is_permanent(job.error):
                    job.status = "Hata"
                    break
                # geçici hata: bağlantıyı bekle, sonra .part dosyasından kaldığı yerden devam et
                net = internet_ok()
                if progressed or not net:
                    fails = 0
                if net:
                    fails += 1
                if fails > MAX_FAILS:
                    job.status = "Hata"
                    break
                while not internet_ok():
                    self._set(job, "Bağlantı bekleniyor…")
                    if not self._sleep(job, 5):
                        break
                if job.cancelled:
                    continue
                delay = 3 if job.stalled else min(5 * (2 ** max(fails - 1, 0)), 120)
                end = time.time() + delay
                while time.time() < end and not job.cancelled:
                    self._set(job, "Yeniden denenecek", f"{int(end - time.time()) + 1} sn")
                    time.sleep(1)
        except Exception as e:  # noqa: BLE001
            job.status = "Hata"
            job.error = str(e)
        finally:
            job.speed = job.eta = ""
            job.proc = None
            with self.lock:
                self.running.discard(job.id)
            self.events.put(("update", job))
            self.events.put(("done", job))
            write_log(job)
            self.pump()

    def _attempt(self, job, attempt):
        """Tek bir yt-dlp çalıştırması. (çıkış kodu, son hata, ilerleme oldu mu) döner."""
        self._set(job, "Başlıyor" if attempt == 1 else f"Devam ediyor ({attempt}. deneme)")
        os.makedirs(job.opts["folder"], exist_ok=True)
        cmd = build_command(self.ytdlp, self.ffmpeg, job.url, job.opts)
        job.stalled = False
        job.last_out = time.time()
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW,
        )
        job.proc = proc
        if job.cancelled:  # başlatılırken iptal geldiyse
            self._kill(job)

        def watchdog():  # indirme sırasında veri akışı durursa (uyku/kopukluk) süreci yeniden başlat
            while proc.poll() is None:
                time.sleep(2)
                if job.status == "İndiriliyor" and time.time() - job.last_out > STALL_SECONDS:
                    job.stalled = True
                    self._kill(job)
                    return

        threading.Thread(target=watchdog, daemon=True).start()
        last_err, progressed, start_pct = "", False, None
        for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip()
            if not line:
                continue
            job.last_out = time.time()
            if not line.startswith("PROG|"):
                job.tail = (job.tail + [line])[-40:]
            if line.startswith("PROG|"):
                parts = (line.split("|") + ["", "", ""])[1:4]
                job.percent, job.speed, job.eta = (p.strip() for p in parts)
                job.status = "İndiriliyor"
                if start_pct is None:
                    start_pct = job.percent
                elif job.percent != start_pct:
                    progressed = True
            elif line.startswith("TITLE|"):
                _, idx, total, title = line.split("|", 3)
                job.title = f"[{idx}/{total}] {title}" if idx and total and idx != "NA" else title
                job.percent = job.speed = job.eta = ""
                start_pct = None
            elif line.startswith("FILE|"):
                job.file = line[5:]
                progressed = True
            elif line.startswith(("[Merger]", "[ExtractAudio]", "[VideoRemuxer]", "[EmbedThumbnail]")):
                job.status = "İşleniyor"
                job.speed = job.eta = ""
            elif line.startswith("ERROR:"):
                last_err = line[6:].strip()
            self.events.put(("update", job))
        code = proc.wait()
        job.proc = None
        if job.stalled and not job.cancelled:
            last_err = "Bağlantı askıda kaldı (veri gelmiyor), yeniden bağlanılıyor"
            code = code or 1
        return code, last_err, progressed


# ----------------------------------------------------------------- arayüz
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1040x700")
        self.minsize(900, 560)
        self.settings = load_settings()
        self.jobs = {}
        self.events = queue.Queue()

        self.ytdlp = find_exe("yt-dlp")
        self.ffmpeg = find_exe("ffmpeg")
        self.dl = Downloader(self.ytdlp, self.ffmpeg, self.events)

        ico = os.path.join(getattr(sys, "_MEIPASS", APP_DIR), "indirici.ico")
        if os.path.isfile(ico):
            try:
                self.iconbitmap(default=ico)
            except tk.TclError:
                pass

        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=24)
        style.configure("Big.TButton", padding=(14, 6))

        self.updating = False
        self._build()
        self._on_type_change()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll)
        if not self.ytdlp or not self.ffmpeg:
            self.after(300, self._install_missing)
        else:
            self._after_tools_ready(just_installed=False)

    def _after_tools_ready(self, just_installed):
        threading.Thread(target=self._read_version, daemon=True).start()
        self.dl.parallel = int(self.v_parallel.get())
        self._restore_queue()
        if just_installed:
            self.settings["last_update_check"] = time.time()
            save_settings(self.settings)
        elif self.settings.get("auto_update") and \
                time.time() - float(self.settings.get("last_update_check", 0)) > UPDATE_INTERVAL:
            self.after(1500, lambda: self._update_ytdlp(auto=True))

    # ---- eksik araçların otomatik kurulumu
    def _install_missing(self):
        need = [n for n, p in (("yt-dlp", self.ytdlp), ("ffmpeg", self.ffmpeg)) if not p]
        self.updating = True
        self.btn_update.state(["disabled"])
        win = tk.Toplevel(self)
        win.title(APP_NAME + " — kurulum")
        win.resizable(False, False)
        win.transient(self)
        win.protocol("WM_DELETE_WINDOW", lambda: None)
        frm = ttk.Frame(win, padding=16)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=f"Gerekli araçlar bulunamadı: {', '.join(need)}\n"
                            f"Otomatik olarak indirilip kuruluyor…",
                  justify="left").pack(anchor="w")
        lbl = ttk.Label(frm, text="Başlıyor…", width=60)
        lbl.pack(anchor="w", pady=(10, 4))
        bar = ttk.Progressbar(frm, length=420, mode="determinate", maximum=100)
        bar.pack(fill="x")
        ttk.Label(frm, text=f"Konum: {BIN_DIR}", foreground="#777").pack(anchor="w", pady=(8, 0))
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_rooty() + 120
        win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        win.grab_set()
        self._inst_win, self._inst_lbl, self._inst_bar = win, lbl, bar
        self.status_lbl.configure(text="Gerekli araçlar kuruluyor…")

        def worker():
            try:
                res = install_tools(not self.ytdlp, not self.ffmpeg,
                                    lambda t, p: self.events.put(("install", (t, p))))
                self.events.put(("installed", (True, res, "")))
            except Exception as e:  # noqa: BLE001
                self.events.put(("installed", (False, (None, None), str(e))))

        threading.Thread(target=worker, daemon=True).start()

    def _on_install_progress(self, text, pct):
        if not getattr(self, "_inst_win", None):
            return
        self._inst_lbl.configure(text=text)
        if pct is None:
            if str(self._inst_bar["mode"]) != "indeterminate":
                self._inst_bar.configure(mode="indeterminate")
                self._inst_bar.start(15)
        else:
            if str(self._inst_bar["mode"]) != "determinate":
                self._inst_bar.stop()
                self._inst_bar.configure(mode="determinate")
            self._inst_bar["value"] = pct

    def _on_installed(self, ok, paths, err):
        self.updating = False
        self.btn_update.state(["!disabled"])
        if getattr(self, "_inst_win", None):
            self._inst_win.grab_release()
            self._inst_win.destroy()
            self._inst_win = None
        ytdlp, ffmpeg = paths
        self.ytdlp = self.ytdlp or ytdlp
        self.ffmpeg = self.ffmpeg or ffmpeg
        self.dl.ytdlp, self.dl.ffmpeg = self.ytdlp, self.ffmpeg
        if ok and self.ytdlp and self.ffmpeg:
            self.status_lbl.configure(text="yt-dlp ve ffmpeg hazır")
            self._after_tools_ready(just_installed=True)
        else:
            self.status_lbl.configure(text="Araç kurulumu başarısız")
            if messagebox.askretrycancel(
                    APP_NAME, "yt-dlp / ffmpeg otomatik kurulamadı.\n\n"
                              f"{err or 'Bilinmeyen hata'}\n\nİnternet bağlantınızı kontrol edip tekrar deneyin."):
                self._install_missing()

    # ---- yerleşim
    def _build(self):
        s = self.settings
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        # URL girişi
        top = ttk.LabelFrame(root, text=" URL'ler (her satıra bir tane — tek URL de olur) ", padding=8)
        top.pack(fill="x")
        txt_frame = ttk.Frame(top)
        txt_frame.pack(fill="x")
        self.url_text = tk.Text(txt_frame, height=5, wrap="none", font=("Segoe UI", 10), undo=True)
        sb = ttk.Scrollbar(txt_frame, orient="vertical", command=self.url_text.yview)
        self.url_text.configure(yscrollcommand=sb.set)
        self.url_text.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")
        self.url_text.bind("<Control-Return>", lambda e: (self._add(), "break")[1])

        row = ttk.Frame(top)
        row.pack(fill="x", pady=(6, 0))
        ttk.Button(row, text="Panodan yapıştır", command=self._paste).pack(side="left")
        ttk.Button(row, text="Dosyadan liste yükle (.txt)…", command=self._load_list).pack(side="left", padx=6)
        ttk.Button(row, text="Temizle", command=lambda: self.url_text.delete("1.0", "end")).pack(side="left")
        ttk.Label(row, text="Ctrl+Enter = kuyruğa ekle", foreground="#777").pack(side="left", padx=10)
        ttk.Button(row, text="⬇  İndir / Kuyruğa ekle", style="Big.TButton",
                   command=self._add).pack(side="right")

        # Seçenekler
        opt = ttk.LabelFrame(root, text=" Seçenekler ", padding=8)
        opt.pack(fill="x", pady=8)

        self.v_type = tk.StringVar(value=s["type"])
        self.v_vformat = tk.StringVar(value=s["vformat"])
        self.v_aformat = tk.StringVar(value=s["aformat"])
        self.v_res = tk.StringVar(value=s["resolution"])
        self.v_aq = tk.StringVar(value=s["aquality"])
        self.v_playlist = tk.BooleanVar(value=s["playlist"])
        self.v_thumb = tk.BooleanVar(value=s["thumbnail"])
        self.v_subs = tk.BooleanVar(value=s["subtitles"])
        self.v_parallel = tk.IntVar(value=s["parallel"])
        self.v_folder = tk.StringVar(value=s["folder"] or DEFAULT_DIR)

        ttk.Label(opt, text="İndirme türü:").grid(row=0, column=0, sticky="w")
        cb_type = ttk.Combobox(opt, textvariable=self.v_type, values=TYPES, state="readonly", width=20)
        cb_type.grid(row=0, column=1, sticky="w", padx=(4, 16))
        cb_type.bind("<<ComboboxSelected>>", lambda e: self._on_type_change())

        ttk.Label(opt, text="Format:").grid(row=0, column=2, sticky="w")
        self.cb_format = ttk.Combobox(opt, state="readonly", width=8)
        self.cb_format.grid(row=0, column=3, sticky="w", padx=(4, 16))
        self.cb_format.bind("<<ComboboxSelected>>", lambda e: self._on_format_change())

        self.lbl_q = ttk.Label(opt, text="Çözünürlük:")
        self.lbl_q.grid(row=0, column=4, sticky="w")
        self.cb_q = ttk.Combobox(opt, state="readonly", width=12)
        self.cb_q.grid(row=0, column=5, sticky="w", padx=(4, 16))
        self.cb_q.bind("<<ComboboxSelected>>", lambda e: self._on_q_change())

        ttk.Label(opt, text="Aynı anda:").grid(row=0, column=6, sticky="w")
        sp = ttk.Spinbox(opt, from_=1, to=5, width=4, textvariable=self.v_parallel, state="readonly",
                         command=self._on_parallel)
        sp.grid(row=0, column=7, sticky="w", padx=4)

        chk = ttk.Frame(opt)
        chk.grid(row=1, column=0, columnspan=8, sticky="w", pady=(8, 0))
        ttk.Checkbutton(chk, text="Oynatma listesinin tamamını indir", variable=self.v_playlist).pack(side="left")
        ttk.Checkbutton(chk, text="Kapak resmi göm", variable=self.v_thumb).pack(side="left", padx=14)
        self.chk_subs = ttk.Checkbutton(chk, text="Altyazı göm (tr/en)", variable=self.v_subs)
        self.chk_subs.pack(side="left")
        self.v_awake = tk.BooleanVar(value=bool(s.get("prevent_sleep", True)))
        ttk.Checkbutton(chk, text="İndirme sürerken bilgisayarın uyumasını engelle", variable=self.v_awake,
                        command=self._on_awake_toggle).pack(side="left", padx=14)

        fr = ttk.Frame(opt)
        fr.grid(row=2, column=0, columnspan=8, sticky="we", pady=(8, 0))
        opt.columnconfigure(7, weight=1)
        ttk.Label(fr, text="İndirme yeri:").pack(side="left")
        ttk.Entry(fr, textvariable=self.v_folder).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(fr, text="Gözat…", command=self._browse).pack(side="left")
        ttk.Button(fr, text="Varsayılan", command=lambda: self.v_folder.set(DEFAULT_DIR)).pack(side="left", padx=4)
        ttk.Button(fr, text="Klasörü aç", command=lambda: self._open_path(self.v_folder.get())).pack(side="left")

        # Kuyruk
        qf = ttk.LabelFrame(root, text=" İndirme kuyruğu ", padding=8)
        qf.pack(fill="both", expand=True)
        cols = ("title", "status", "percent", "speed", "eta", "kind")
        self.tree = ttk.Treeview(qf, columns=cols, show="headings", selectmode="extended")
        heads = {"title": ("Başlık / URL", 420), "status": ("Durum", 100), "percent": ("İlerleme", 80),
                 "speed": ("Hız", 100), "eta": ("Kalan", 70), "kind": ("Tür", 140)}
        for c, (h, w) in heads.items():
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w" if c in ("title", "kind") else "center",
                             stretch=(c == "title"))
        vsb = ttk.Scrollbar(qf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.tag_configure("ok", foreground="#1a7f37")
        self.tree.tag_configure("err", foreground="#c62828")
        self.tree.tag_configure("cancel", foreground="#888")
        self.tree.tag_configure("wait", foreground="#b26a00")
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<Button-3>", self._on_right)
        self.tree.bind("<Delete>", lambda e: self._cancel_selected())

        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Dosyayı aç", command=self._open_selected_file)
        self.menu.add_command(label="Klasörde göster", command=self._show_selected_in_folder)
        self.menu.add_separator()
        self.menu.add_command(label="İptal et", command=self._cancel_selected)
        self.menu.add_command(label="Yeniden dene", command=self._retry_selected)
        self.menu.add_command(label="Hata ayrıntısı", command=self._show_error)
        self.menu.add_command(label="URL'yi kopyala", command=self._copy_url)
        self.menu.add_separator()
        self.menu.add_command(label="Listeden kaldır", command=self._remove_selected)

        bottom = ttk.Frame(root)
        bottom.pack(side="bottom", fill="x", pady=(8, 0), before=qf)  # kuyruk büyüse de alt çubuk hep görünür
        ttk.Button(bottom, text="Seçileni iptal et", command=self._cancel_selected).pack(side="left")
        ttk.Button(bottom, text="Yeniden dene", command=self._retry_selected).pack(side="left", padx=6)
        ttk.Button(bottom, text="Bitenleri temizle", command=self._clear_finished).pack(side="left")
        ttk.Separator(bottom, orient="vertical").pack(side="left", fill="y", padx=10)
        self.btn_update = ttk.Button(bottom, text="⟳ yt-dlp güncelle", command=self._update_ytdlp)
        self.btn_update.pack(side="left")
        self.v_auto = tk.BooleanVar(value=bool(self.settings.get("auto_update", True)))
        ttk.Checkbutton(bottom, text="Açılışta otomatik güncelle", variable=self.v_auto,
                        command=self._on_auto_toggle).pack(side="left", padx=6)
        self.ver_lbl = ttk.Label(bottom, text="", foreground="#777")
        self.ver_lbl.pack(side="left", padx=4)
        help_lbl = ttk.Label(bottom, text="Yardım / Kılavuz", foreground="#1565c0", cursor="hand2")
        help_lbl.pack(side="left", padx=8)
        help_lbl.bind("<Button-1>", lambda e: __import__("webbrowser").open(APP_URL + "#readme"))
        self.status_lbl = ttk.Label(bottom, text="Hazır", foreground="#555")
        self.status_lbl.pack(side="right")

    # ---- yt-dlp güncelleme
    def _on_awake_toggle(self):
        self.settings["prevent_sleep"] = bool(self.v_awake.get())
        save_settings(self.settings)
        self._update_status()

    def _on_auto_toggle(self):
        self.settings["auto_update"] = bool(self.v_auto.get())
        save_settings(self.settings)

    def _read_version(self):
        try:
            out = subprocess.run([self.ytdlp, "--version"], capture_output=True, text=True,
                                 stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW, timeout=30).stdout.strip()
        except Exception:
            out = ""
        self.events.put(("version", out))

    def _update_ytdlp(self, auto=False):
        if self.updating or not self.ytdlp:
            return
        if self.dl.active_count():
            if auto:  # indirme sürerken exe değiştirilemez; sonra tekrar dene
                self.after(60000, lambda: self._update_ytdlp(auto=True))
            else:
                messagebox.showinfo(APP_NAME, "İndirmeler sürerken güncelleme yapılamaz.\n"
                                              "Kuyruk bitince tekrar deneyin.")
            return
        self.updating = True
        self.btn_update.state(["disabled"])
        self.status_lbl.configure(text="yt-dlp güncelleniyor…")
        threading.Thread(target=self._update_worker, args=(auto,), daemon=True).start()

    def _update_worker(self, auto):
        def run(cmd, timeout=300):
            r = subprocess.run(cmd, capture_output=True, creationflags=CREATE_NO_WINDOW,
                               stdin=subprocess.DEVNULL, timeout=timeout)
            text = (r.stdout + r.stderr).decode("utf-8", errors="replace")
            return r.returncode, text

        ok, msg = False, ""
        try:
            code, out = run([self.ytdlp, "-U"])
            low = out.lower()
            if code == 0 and ("up to date" in low or "updated yt-dlp to" in low):
                ok = True
                msg = "yt-dlp zaten güncel." if "up to date" in low else "yt-dlp güncellendi."
            else:
                # Kendi kendini güncelleyemediyse winget ile dene
                winget = shutil.which("winget")
                if winget:
                    code, out2 = run([winget, "upgrade", "--id", "yt-dlp.yt-dlp", "-e", "--silent",
                                      "--accept-source-agreements", "--accept-package-agreements",
                                      "--disable-interactivity"], timeout=600)
                    low2 = out2.lower()
                    if code == 0 or "no available upgrade" in low2 or "no newer package" in low2 \
                            or "zaten yüklü" in low2:
                        ok = True
                        msg = "yt-dlp winget ile güncellendi / güncel."
                    else:
                        msg = (out + "\n" + out2).strip()[-800:]
                else:
                    msg = out.strip()[-800:]
        except Exception as e:  # noqa: BLE001
            msg = str(e)
        self.events.put(("updated", (ok, msg, auto)))

    def _on_updated(self, ok, msg, auto):
        self.updating = False
        self.btn_update.state(["!disabled"])
        if ok:
            self.settings["last_update_check"] = time.time()
            save_settings(self.settings)
        self.status_lbl.configure(text=msg.splitlines()[0] if ok else "yt-dlp güncellenemedi")
        threading.Thread(target=self._read_version, daemon=True).start()
        if not auto:
            (messagebox.showinfo if ok else messagebox.showerror)(APP_NAME, msg or "Bilinmeyen hata")

    # ---- seçenek mantığı
    def _on_type_change(self):
        kind = self.v_type.get()
        if kind == "Sadece Ses":
            self.cb_format.configure(values=AUDIO_FORMATS)
            self.cb_format.set(self.v_aformat.get())
            self.lbl_q.configure(text="Ses kalitesi:")
            self.cb_q.configure(values=AUDIO_QUALITIES)
            self.cb_q.set(self.v_aq.get())
            self.chk_subs.state(["disabled"])
        else:
            self.cb_format.configure(values=VIDEO_FORMATS)
            self.cb_format.set(self.v_vformat.get())
            self.lbl_q.configure(text="Çözünürlük:")
            self.cb_q.configure(values=RESOLUTIONS)
            self.cb_q.set(self.v_res.get())
            if kind == "Video + Ses":
                self.chk_subs.state(["!disabled"])
            else:
                self.chk_subs.state(["disabled"])

    def _on_format_change(self):
        if self.v_type.get() == "Sadece Ses":
            self.v_aformat.set(self.cb_format.get())
        else:
            self.v_vformat.set(self.cb_format.get())

    def _on_q_change(self):
        if self.v_type.get() == "Sadece Ses":
            self.v_aq.set(self.cb_q.get())
        else:
            self.v_res.set(self.cb_q.get())

    def _on_parallel(self):
        self.dl.parallel = int(self.v_parallel.get())
        self.dl.pump()

    def _current_opts(self):
        self._on_format_change()
        self._on_q_change()
        opts = {
            "folder": self.v_folder.get().strip() or DEFAULT_DIR,
            "type": self.v_type.get(),
            "vformat": self.v_vformat.get(),
            "aformat": self.v_aformat.get(),
            "resolution": self.v_res.get(),
            "aquality": self.v_aq.get(),
            "playlist": self.v_playlist.get(),
            "thumbnail": self.v_thumb.get(),
            "subtitles": self.v_subs.get(),
            "parallel": int(self.v_parallel.get()),
        }
        self.settings.update(opts)
        save_settings(self.settings)
        return opts

    @staticmethod
    def _kind_label(o):
        if o["type"] == "Sadece Ses":
            return f"Ses · {o['aformat']} · {o['aquality']}"
        short = "Video" if o["type"] == "Video + Ses" else "Sessiz video"
        return f"{short} · {o['vformat']} · {o['resolution'].split(' ')[0]}"

    # ---- eylemler
    # ---- kuyruğun kalıcı kaydı (kapanınca / çökünce sonraki açılışta devam)
    def _save_queue(self):
        items = [{"url": j.url, "opts": j.opts, "title": j.title}
                 for j in self.jobs.values() if j.status not in ("Tamamlandı", "İptal edildi", "Hata")]
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(QUEUE_FILE, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def _restore_queue(self):
        if getattr(self, "_restored", False):
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
            self._update_status()
            self.status_lbl.configure(text=f"Yarım kalan {len(items)} indirme kaldığı yerden sürdürülüyor")

    def _enqueue(self, url, opts, title=None):
        job = Job(url, opts, title)
        self.jobs[job.id] = job
        self.tree.insert("", "end", iid=str(job.id),
                         values=(job.title, job.status, "", "", "", self._kind_label(opts)))
        self.dl.add(job)
        return job

    def _add(self):
        if not self.ytdlp:
            messagebox.showerror(APP_NAME, "yt-dlp bulunamadı.")
            return
        if self.updating:
            messagebox.showinfo(APP_NAME, "yt-dlp şu an güncelleniyor, birkaç saniye sonra tekrar deneyin.")
            return
        urls = parse_urls(self.url_text.get("1.0", "end"))
        if not urls:
            messagebox.showinfo(APP_NAME, "Lütfen en az bir URL girin.")
            return
        opts = self._current_opts()
        self.dl.parallel = opts["parallel"]
        for u in urls:
            self._enqueue(u, dict(opts))
        self.url_text.delete("1.0", "end")
        self._save_queue()
        self._update_status()

    def _paste(self):
        try:
            data = self.clipboard_get()
        except tk.TclError:
            return
        cur = self.url_text.get("1.0", "end").strip()
        self.url_text.insert("end", ("\n" if cur else "") + data.strip() + "\n")

    def _load_list(self):
        path = filedialog.askopenfilename(title="URL listesi seç",
                                          filetypes=[("Metin dosyası", "*.txt"), ("Tüm dosyalar", "*.*")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                data = f.read()
        except OSError as e:
            messagebox.showerror(APP_NAME, str(e))
            return
        urls = parse_urls(data)
        cur = self.url_text.get("1.0", "end").strip()
        self.url_text.insert("end", ("\n" if cur else "") + "\n".join(urls) + "\n")

    def _browse(self):
        start = self.v_folder.get() if os.path.isdir(self.v_folder.get()) else os.path.expanduser("~")
        d = filedialog.askdirectory(title="İndirme klasörü seç", initialdir=start)
        if d:
            self.v_folder.set(os.path.normpath(d))
            self.settings["folder"] = self.v_folder.get()
            save_settings(self.settings)

    def _open_path(self, path):
        if not path:
            return
        if not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
            except OSError:
                return
        os.startfile(path)

    def _selected_jobs(self):
        return [self.jobs[int(i)] for i in self.tree.selection() if int(i) in self.jobs]

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
        self._update_status()

    def _remove_selected(self):
        for j in self._selected_jobs():
            if j.status in FINAL:
                self.tree.delete(str(j.id))
                del self.jobs[j.id]
        self._save_queue()

    def _clear_finished(self):
        for jid, j in list(self.jobs.items()):
            if j.status in ("Tamamlandı", "İptal edildi"):
                self.tree.delete(str(jid))
                del self.jobs[jid]
        self._save_queue()

    def _open_selected_file(self):
        for j in self._selected_jobs()[:1]:
            if j.file and os.path.exists(j.file):
                os.startfile(j.file)
            else:
                self._open_path(j.opts["folder"])

    def _show_selected_in_folder(self):
        for j in self._selected_jobs()[:1]:
            if j.file and os.path.exists(j.file):
                subprocess.Popen(["explorer", "/select,", os.path.normpath(j.file)])
            else:
                self._open_path(j.opts["folder"])

    def _show_error(self):
        for j in self._selected_jobs()[:1]:
            detail = "\n".join(j.tail[-15:])
            messagebox.showinfo(APP_NAME, (j.error or "Hata kaydı yok.") +
                                (f"\n\n--- son çıktı ---\n{detail}" if detail else "") +
                                f"\n\nGünlük: {LOG_FILE}")

    def _copy_url(self):
        jobs = self._selected_jobs()
        if jobs:
            self.clipboard_clear()
            self.clipboard_append("\n".join(j.url for j in jobs))

    def _on_double(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        j = self.jobs.get(int(iid))
        if not j:
            return
        if j.status == "Tamamlandı":
            self.tree.selection_set(iid)
            self._show_selected_in_folder()
        elif j.status == "Hata":
            messagebox.showinfo(APP_NAME, j.error)

    def _on_right(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            if iid not in self.tree.selection():
                self.tree.selection_set(iid)
            self.menu.tk_popup(event.x_root, event.y_root)

    # ---- güncelleme döngüsü
    def _refresh_row(self, j):
        iid = str(j.id)
        if not self.tree.exists(iid):
            return
        status = j.status if j.status != "Hata" else "Hata ⚠"
        tag = {"Tamamlandı": "ok", "Hata": "err", "İptal edildi": "cancel",
               "Duraklatıldı": "cancel", "Bağlantı bekleniyor…": "wait",
               "Yeniden denenecek": "wait"}.get(j.status, "")
        self.tree.item(iid, values=(j.title, status, j.percent, j.speed, j.eta, self._kind_label(j.opts)),
                       tags=(tag,) if tag else ())

    def _poll(self):
        changed = set()
        finished = []
        try:
            while True:
                kind, job = self.events.get_nowait()
                if kind == "install":
                    self._on_install_progress(*job)
                elif kind == "installed":
                    self._on_installed(*job)
                elif kind == "version":
                    self.ver_lbl.configure(text=f"sürüm: {job}" if job else "")
                elif kind == "updated":
                    self._on_updated(*job)
                elif kind == "update":
                    changed.add(job.id)
                elif kind == "done":
                    finished.append(job)
        except queue.Empty:
            pass
        for jid in changed:
            if jid in self.jobs:
                self._refresh_row(self.jobs[jid])
        if finished:
            self._save_queue()
        if changed or finished:
            self._update_status()
        if finished and self.dl.active_count() == 0:
            ok = sum(1 for j in self.jobs.values() if j.status == "Tamamlandı")
            err = sum(1 for j in self.jobs.values() if j.status == "Hata")
            self.status_lbl.configure(text=f"Tüm indirmeler bitti — {ok} başarılı, {err} hatalı")
            if self.state() == "iconic" or self.focus_displayof() is None:
                self.bell()
        self.after(150, self._poll)

    def _update_status(self):
        n = self.dl.active_count()
        self._keep_awake(n > 0 and self.v_awake.get())
        if n:
            self.status_lbl.configure(text=f"{n} indirme aktif/beklemede")
            self.title(f"({n}) {APP_NAME} {APP_VERSION}")
        else:
            self.title(f"{APP_NAME} {APP_VERSION}")

    def _keep_awake(self, on):
        """İndirme sürerken Windows'un otomatik uykuya geçmesini engeller."""
        if os.name != "nt" or getattr(self, "_awake", None) == on:
            return
        self._awake = on
        try:
            import ctypes
            ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))
        except Exception:
            pass

    def _on_close(self):
        n = self.dl.active_count()
        if n and not messagebox.askyesno(
                APP_NAME, f"{n} indirme hâlâ sürüyor/bekliyor.\n\n"
                          "Kapatırsanız duraklatılacak ve uygulamayı bir sonraki açışınızda "
                          "kaldığı yerden otomatik devam edecek.\n\nÇıkılsın mı?"):
            return
        self._save_queue()  # öldürmeden önce kaydet ki yarım kalanlar listede kalsın
        for j in list(self.jobs.values()):
            if j.status not in FINAL:
                j.shutdown = True
                self.dl.cancel(j)
        self._keep_awake(False)
        self._current_opts()
        self.destroy()


def main():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("VideoMuzikIndirici.App")
        except Exception:
            pass
    App().mainloop()


if __name__ == "__main__":
    main()
