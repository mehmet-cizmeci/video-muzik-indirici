# -*- coding: utf-8 -*-
"""
Video Müzik İndirici - çekirdek (arayüzden bağımsız) işlemler.
https://github.com/mehmet-cizmeci/video-muzik-indirici

İndirme kuyruğu ve yt-dlp çalıştırma, kesintiye dayanıklı yeniden deneme, ayarlar ve kalıcı kuyruk,
yt-dlp/FFmpeg otomatik kurulumu ve güncellemesi, önizleme bilgileri ve uygulamanın kendi güncellemesi.
Arayüz bu modüle yalnızca `events` kuyruğu üzerinden bağlanır.
"""
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time

APP_NAME = "Video Müzik İndirici"
APP_VERSION = "2.1.0"
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
# Android uyumlu: H.264 + AAC MP4. YouTube'un yeni AV1 biçimini Android 9 ve öncesi oynatamaz; eski / düşük güçlü
# cihazlar 1080p ve 60 fps'i kaldıramayabilir (ses gelir, görüntü gelmez).
COMPAT_MODES = ["Android uyumlu (H.264)", "Orijinal (en iyi kalite)"]
FPS_OPTIONS = ["30 fps (önerilen)", "25 fps", "Orijinal", "60 fps"]
CONVERT_RESOLUTIONS = ["720p (önerilen)", "1080p", "480p", "Orijinal"]
VIDEO_EXT = (".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".flv", ".wmv", ".ts", ".mts", ".3gp", ".mpg", ".mpeg")

DEFAULTS = {
    "folder": DEFAULT_DIR,
    "type": TYPES[0],
    "vformat": "mp4",
    "aformat": "mp3",
    "resolution": "720p",
    "compat": COMPAT_MODES[0],
    "fps": FPS_OPTIONS[0],
    "clean_names": True,
    "conv_res": CONVERT_RESOLUTIONS[0],
    "conv_fps": FPS_OPTIONS[0],
    "conv_clean": True,
    "conv_copy_ok": True,
    "conv_out": "",
    "aquality": "En iyi",
    "playlist": False,
    "thumbnail": True,
    "subtitles": False,
    "parallel": 2,
    "auto_update": True,
    "prevent_sleep": True,
    "last_update_check": 0,
    "theme": "dark",
    "app_update_check": True,
    "skipped_version": "",
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
        compat = is_compat(opts)
        fmt = "mp4" if compat else opts["vformat"]
        fps = fps_limit(opts.get("fps"))
        sort = []
        if compat:
            # Önce H.264 seçilir (AV1/VP9 yerine); yine de uyumsuz gelirse indirme sonunda dönüştürülür
            sort += ["vcodec:h264", "acodec:aac"]
        if height:
            sort.append("res:" + height)
        if fps:
            sort.append(f"fps:{fps}")
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


# ----------------------------------------------------------------- Android uyumluluğu ve dönüştürme
def is_compat(opts):
    return opts.get("compat", COMPAT_MODES[0]) == COMPAT_MODES[0]


def fps_limit(choice):
    """FPS seçeneğinden üst sınır (int) döner; 'Orijinal' için None."""
    import re
    m = re.match(r"\s*(\d+)", choice or "")
    return int(m.group(1)) if m else None


def height_limit(choice):
    """'720p (önerilen)', '1080p', '2160p (4K)' → 720/1080/2160; 'En iyi' / 'Orijinal' → None."""
    import re
    m = re.match(r"\s*(\d+)p", choice or "")
    return int(m.group(1)) if m else None


def find_ffprobe(ffmpeg):
    if ffmpeg:
        p = os.path.join(os.path.dirname(ffmpeg), "ffprobe.exe" if os.name == "nt" else "ffprobe")
        if os.path.isfile(p):
            return p
    return find_exe("ffprobe")


def probe_media(ffprobe, path):
    """Dosyanın video/ses bilgilerini döner: vcodec, width, height, fps, pix_fmt, profile, acodec, duration."""
    r = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                       capture_output=True, stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", errors="replace").strip()[-300:] or "ffprobe okuyamadı")
    data = json.loads(r.stdout.decode("utf-8", errors="replace"))
    streams = data.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"
              and not (s.get("disposition") or {}).get("attached_pic")), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fps = 0.0
    rate = (v or {}).get("avg_frame_rate") or (v or {}).get("r_frame_rate") or "0/1"
    try:
        num, den = rate.split("/")
        fps = float(num) / float(den) if float(den) else 0.0
    except (ValueError, ZeroDivisionError):
        pass
    try:
        duration = float((data.get("format") or {}).get("duration") or 0)
    except ValueError:
        duration = 0.0
    return {
        "vcodec": (v or {}).get("codec_name"), "width": int((v or {}).get("width") or 0),
        "height": int((v or {}).get("height") or 0), "fps": fps, "pix_fmt": (v or {}).get("pix_fmt") or "",
        "profile": (v or {}).get("profile") or "", "acodec": (a or {}).get("codec_name"), "duration": duration,
        "format": (data.get("format") or {}).get("format_name") or "",
        "vindex": (v or {}).get("index"),
    }


def compat_plan(info, max_height=None, max_fps=None):
    """Android uyumlu MP4 için ne gerektiğini döner: 'ok' (uyumlu), 'remux' (yalnızca kap/ses) veya 'encode'."""
    if not info.get("vcodec"):
        return "encode" if info.get("acodec") not in (None, "aac", "mp3") else "remux"
    video_ok = (info["vcodec"] == "h264" and info["pix_fmt"] in ("yuv420p", "yuvj420p")
                and "10" not in info["profile"] and "4:4:4" not in info["profile"]
                and not (max_height and info["height"] > max_height)
                and not (max_fps and info["fps"] > max_fps + 0.5))
    if not video_ok:
        return "encode"
    audio_ok = info["acodec"] in (None, "aac", "mp3")
    return "ok" if audio_ok and "mp4" in info["format"] else "remux"


def transcode(ffmpeg, src, dst, info, max_height=None, max_fps=None, mode="encode", on_proc=None, progress=None):
    """src'yi Android uyumlu MP4 olarak dst'ye yazar (H.264 Main/High + AAC, faststart).
    mode='remux' videoyu yeniden kodlamaz. progress(yüzde) çağrılır; on_proc(süreç) iptal için verilir."""
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", src]
    # kapak resmi (attached_pic) değil, asıl video akışı seçilir
    vi = info.get("vindex")
    cmd += ["-map", f"0:{vi}" if vi is not None else "0:v:0?", "-map", "0:a:0?", "-sn", "-dn"]
    if mode == "encode" and info.get("vcodec"):
        h = info.get("height") or 0
        target_h = min(h, max_height) if (max_height and h) else h
        vf = [f"scale=-2:'min({max_height},ih)'"] if max_height else []
        if max_fps and info.get("fps", 0) > max_fps + 0.5:
            vf.append(f"fps={max_fps}")
        vf.append("format=yuv420p")
        level = "3.0" if target_h <= 480 else "3.1" if target_h <= 720 else "4.0" if target_h <= 1080 else "5.1"
        cmd += ["-vf", ",".join(vf), "-c:v", "libx264", "-profile:v", "main" if target_h <= 1080 else "high",
                "-level", level, "-preset", "veryfast", "-crf", "23"]
    else:
        cmd += ["-c:v", "copy"]
    cmd += ["-c:a", "copy"] if info.get("acodec") == "aac" else ["-c:a", "aac", "-b:a", "128k", "-ac", "2"]
    cmd += ["-movflags", "+faststart", "-progress", "pipe:1", "-nostats", dst]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                            creationflags=CREATE_NO_WINDOW)
    if on_proc:
        on_proc(proc)
    err_tail = []

    def read_err():
        for raw in proc.stderr:
            err_tail.append(raw.decode("utf-8", errors="replace").rstrip())
            del err_tail[:-20]
    threading.Thread(target=read_err, daemon=True).start()
    dur = info.get("duration") or 0
    for raw in proc.stdout:
        line = raw.decode("utf-8", errors="replace").strip()
        if progress and dur and line.startswith("out_time_us=") and line[12:].isdigit():
            progress(min(99.9, int(line[12:]) / 1e6 / dur * 100))
    code = proc.wait()
    if code != 0:
        try:
            os.remove(dst)
        except OSError:
            pass
        raise RuntimeError("ffmpeg dönüştürme hatası: " + (" | ".join(l for l in err_tail if l)[-400:] or f"kod {code}"))


def clean_filename(name):
    """Dosya adından emoji, garip simgeler ve sondaki [YouTube kimliği]ni temizler (uzantı korunur).
    Bu karakterler bazı cihazlarda (ör. eski Android) dosya adının bozulmasına ve klasörün okunamamasına yol açar."""
    import re
    import unicodedata
    base, ext = os.path.splitext(name)
    base = unicodedata.normalize("NFC", base)
    base = re.sub(r"\s*\[[A-Za-z0-9_-]{11}\]\s*$", "", base)              # YouTube kimliği
    base = "".join(c for c in base if ord(c) <= 0xFFFF)                    # emoji vb. (BMP dışı)
    base = re.sub(r"[☀-➿⬀-⯿︀-️​-‍⃣̇⁠]", "", base)
    base = re.sub(r"[｜|⧸/\\]", " - ", base)                              # yt-dlp'nin Windows yerine koyduğu karakterler
    base = re.sub(r"[：:]", " -", base)
    base = re.sub(r"[＂\"＊*？?＜<＞>]", "", base).replace("•", "-")
    base = re.sub(r"\s+", " ", base)
    base = re.sub(r"(\s*-\s*){2,}", " - ", base).strip(" -._")
    return (base or "video") + ext.lower()


def unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{base} ({n}){ext}"):
        n += 1
    return f"{base} ({n}){ext}"


def rename_clean(path):
    """Dosyayı temiz adla yeniden adlandırır; yeni yolu döner (değişmediyse aynısı)."""
    folder, name = os.path.split(path)
    new_name = clean_filename(name)
    if new_name == name:
        return path
    target = unique_path(os.path.join(folder, new_name))
    os.replace(path, target)
    return target


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
        self.files = []         # bu işte inen tüm dosyalar (oynatma listesinde birden çok)
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
                    self._postprocess(job)
                    if job.cancelled:
                        job.status = "Duraklatıldı" if job.shutdown else "İptal edildi"
                    else:
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

    def _postprocess(self, job):
        """İndirme sonrası: Android uyumlu değilse H.264 MP4'e dönüştürür, bozuk dosya adlarını temizler."""
        opts = job.opts
        video = opts["type"] != "Sadece Ses"
        compat = video and is_compat(opts)
        ffprobe = find_ffprobe(self.ffmpeg) if (compat and self.ffmpeg) else None
        max_h, max_fps = height_limit(opts.get("resolution")), fps_limit(opts.get("fps"))
        n = len(job.files)
        for i, path in enumerate(list(job.files)):
            if job.cancelled:
                return
            if not os.path.isfile(path):
                continue
            new = path
            if ffprobe:
                info = probe_media(ffprobe, path)
                plan = compat_plan(info, max_h, max_fps)
                if plan != "ok":
                    label = "Dönüştürülüyor" if plan == "encode" else "İşleniyor"
                    if n > 1:
                        label += f" ({i + 1}/{n})"
                    self._set(job, label)
                    job.percent = "0%"
                    base = os.path.splitext(path)[0]
                    tmp = base + ".uyumlu.tmp.mp4"

                    def prog(p, label=label):
                        job.percent = f"{p:.0f}%"
                        job.status = label
                        self.events.put(("update", job))

                    def on_proc(proc):
                        job.proc = proc
                        if job.cancelled:
                            self._kill(job)
                    try:
                        transcode(self.ffmpeg, path, tmp, info, max_h, max_fps, plan, on_proc, prog)
                    except RuntimeError:
                        if job.cancelled:
                            return
                        raise
                    finally:
                        job.proc = None
                    new = base + ".mp4"
                    os.replace(tmp, new)
                    if os.path.normcase(new) != os.path.normcase(path):
                        os.remove(path)
            if opts.get("clean_names", True):
                new = rename_clean(new)
            job.files[i] = new
            if job.file == path:
                job.file = new

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
                if job.file not in job.files:
                    job.files.append(job.file)
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


# ----------------------------------------------------------------- MP4 dönüştürücü (yerel dosyalar)
CONV_SUBDIR = "Android uyumlu"


def collect_videos(paths):
    """Dosya ve klasör listesinden video dosyalarını toplar (klasörlerde alt klasörler dahil değil)."""
    out = []
    for p in paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p), key=str.lower):
                full = os.path.join(p, name)
                if os.path.isfile(full) and name.lower().endswith(VIDEO_EXT) and ".tmp." not in name:
                    out.append(full)
        elif os.path.isfile(p) and p.lower().endswith(VIDEO_EXT):
            out.append(p)
    seen, uniq = set(), []
    for p in out:
        k = os.path.normcase(os.path.abspath(p))
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


class ConvJob:
    _next = 1

    def __init__(self, src, opts):
        self.id = ConvJob._next
        ConvJob._next += 1
        self.src = src
        self.opts = opts        # conv_res, conv_fps, conv_clean, conv_copy_ok, conv_out
        self.dst = None
        self.status = "Bekliyor"
        self.percent = ""
        self.info = ""          # ör. "AV1 1920x1080 60fps → H.264 720p 30fps"
        self.error = ""
        self.proc = None
        self.cancelled = False


def conv_out_dir(job):
    out = (job.opts.get("conv_out") or "").strip()
    return out or os.path.join(os.path.dirname(job.src), CONV_SUBDIR)


class Converter:
    """Yerel videoları Android uyumlu MP4'e (H.264 + AAC) çevirir. Orijinallere dokunmaz;
    çıktılar ayrı bir klasöre yazılır. Olaylar: ("conv_update", iş), ("conv_done", iş)."""

    def __init__(self, ffmpeg, events, parallel=None):
        self.ffmpeg = ffmpeg
        self.events = events
        self.pending = []
        self.running = set()
        self.lock = threading.Lock()
        self.parallel = parallel or (2 if (os.cpu_count() or 2) >= 8 else 1)

    def add(self, job):
        with self.lock:
            self.pending.append(job)
        self.events.put(("conv_update", job))
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

    def cancel(self, job):
        job.cancelled = True
        with self.lock:
            if job in self.pending:
                self.pending.remove(job)
                job.status = "İptal edildi"
                self.events.put(("conv_update", job))
                self.events.put(("conv_done", job))
                return
        p = job.proc
        if p and p.poll() is None:
            p.kill()

    def _upd(self, job, status=None):
        if status:
            job.status = status
        self.events.put(("conv_update", job))

    def _run(self, job):
        tmp = None
        try:
            ffprobe = find_ffprobe(self.ffmpeg)
            if not (self.ffmpeg and ffprobe):
                raise RuntimeError("ffmpeg / ffprobe bulunamadı")
            self._upd(job, "İnceleniyor")
            info = probe_media(ffprobe, job.src)
            if not info.get("vcodec"):
                raise RuntimeError("Dosyada video bulunamadı")
            max_h = height_limit(job.opts.get("conv_res"))
            max_fps = fps_limit(job.opts.get("conv_fps"))
            plan = compat_plan(info, max_h, max_fps)
            out_dir = conv_out_dir(job)
            os.makedirs(out_dir, exist_ok=True)
            name = os.path.splitext(os.path.basename(job.src))[0] + ".mp4"
            if job.opts.get("conv_clean", True):
                name = clean_filename(name)
            dst = unique_path(os.path.join(out_dir, name))
            if os.path.normcase(os.path.abspath(dst)) == os.path.normcase(os.path.abspath(job.src)):
                raise RuntimeError("Çıktı dosyası kaynakla aynı olamaz")
            src_desc = describe(info)
            if plan == "ok" and job.opts.get("conv_copy_ok", True):
                job.info = src_desc + " → zaten uyumlu, kopyalandı"
                self._upd(job, "Kopyalanıyor")
                tmp = dst + ".tmp"
                shutil.copyfile(job.src, tmp)
                os.replace(tmp, dst)
            else:
                mode = "remux" if plan in ("ok", "remux") else "encode"
                h = min(info["height"], max_h) if max_h else info["height"]
                f = min(info["fps"], max_fps) if max_fps else info["fps"]
                job.info = src_desc + (" → H.264 " + f"{h}p {round(f)}fps" if mode == "encode"
                                       else " → yalnızca MP4 kabı / AAC ses")
                self._upd(job, "Dönüştürülüyor")
                job.percent = "0%"
                tmp = os.path.splitext(dst)[0] + ".tmp.mp4"

                def prog(p):
                    job.percent = f"{p:.0f}%"
                    self._upd(job)

                def on_proc(proc):
                    job.proc = proc
                    if job.cancelled:
                        proc.kill()
                transcode(self.ffmpeg, job.src, tmp, info, max_h, max_fps, mode, on_proc, prog)
                os.replace(tmp, dst)
            tmp = None
            job.dst = dst
            job.percent = "100%"
            job.status = "Tamamlandı"
        except Exception as e:  # noqa: BLE001
            if job.cancelled:
                job.status = "İptal edildi"
            else:
                job.status, job.error = "Hata", str(e)
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            job.proc = None
            with self.lock:
                self.running.discard(job.id)
            self.events.put(("conv_update", job))
            self.events.put(("conv_done", job))
            self.pump()


def describe(info):
    names = {"h264": "H.264", "hevc": "H.265", "av1": "AV1", "vp9": "VP9", "vp8": "VP8", "mpeg4": "MPEG-4"}
    v = names.get(info.get("vcodec"), (info.get("vcodec") or "?").upper())
    return f"{v} {info.get('height', 0)}p {round(info.get('fps') or 0)}fps"


# ----------------------------------------------------------------- yt-dlp sürümü / güncelleme
def ytdlp_version(ytdlp):
    try:
        return subprocess.run([ytdlp, "--version"], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                              creationflags=CREATE_NO_WINDOW, timeout=30).stdout.strip()
    except Exception:
        return ""


def update_ytdlp(ytdlp):
    """yt-dlp'yi günceller. (başarılı mı, mesaj) döner."""
    def run(cmd, timeout=300):
        r = subprocess.run(cmd, capture_output=True, creationflags=CREATE_NO_WINDOW,
                           stdin=subprocess.DEVNULL, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).decode("utf-8", errors="replace")

    try:
        code, out = run([ytdlp, "-U"])
        low = out.lower()
        if code == 0 and ("up to date" in low or "updated yt-dlp to" in low):
            return True, ("yt-dlp zaten güncel." if "up to date" in low else "yt-dlp güncellendi.")
        winget = shutil.which("winget")  # kendi kendini güncelleyemediyse (paket yöneticisiyle kurulmuş)
        if winget:
            code, out2 = run([winget, "upgrade", "--id", "yt-dlp.yt-dlp", "-e", "--silent",
                              "--accept-source-agreements", "--accept-package-agreements",
                              "--disable-interactivity"], timeout=600)
            low2 = out2.lower()
            if code == 0 or "no available upgrade" in low2 or "no newer package" in low2 or "zaten yüklü" in low2:
                return True, "yt-dlp winget ile güncellendi / güncel."
            return False, (out + "\n" + out2).strip()[-800:]
        return False, out.strip()[-800:]
    except Exception as e:  # noqa: BLE001
        return False, str(e)


# ----------------------------------------------------------------- önizleme
def _run_json(cmd, timeout=90):
    r = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL,
                       creationflags=CREATE_NO_WINDOW, timeout=timeout)
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", errors="replace").strip().splitlines()
        msg = next((l[6:].strip() for l in reversed(err) if l.startswith("ERROR:")), err[-1] if err else "")
        raise RuntimeError(msg or f"yt-dlp çıkış kodu {r.returncode}")
    return json.loads(r.stdout.decode("utf-8", errors="replace"))


def probe(ytdlp, url):
    """Bağlantının bilgilerini döner (indirmeden). Oynatma listelerinde ilk öğe önizlenir."""
    data = _run_json([ytdlp, url, "-J", "--flat-playlist", "--no-warnings", "--ignore-config",
                      "--encoding", "utf-8", "--socket-timeout", "20"])
    info = {"url": url, "is_playlist": False, "count": 0, "playlist_title": ""}
    if data.get("_type") == "playlist" or data.get("entries"):
        entries = [e for e in (data.get("entries") or []) if e]
        info.update(is_playlist=True, count=len(entries), playlist_title=data.get("title") or "")
        if not entries:
            raise RuntimeError("Oynatma listesi boş.")
        first = entries[0]
        url = first.get("url") or first.get("webpage_url") or url
        if not url.startswith("http"):
            url = f"https://www.youtube.com/watch?v={first.get('id')}"
        data = _run_json([ytdlp, url, "-J", "--no-playlist", "--no-warnings", "--ignore-config",
                          "--encoding", "utf-8", "--socket-timeout", "20"])
    heights = sorted({f.get("height") for f in data.get("formats") or [] if f.get("height")}, reverse=True)
    thumb = data.get("thumbnail") or ""
    for t in reversed(data.get("thumbnails") or []):  # ~640px civarı bir küçük resim yeterli
        if t.get("url") and (t.get("width") or 0) and 320 <= t["width"] <= 1280:
            thumb = t["url"]
            break
    info.update(
        item_url=data.get("webpage_url") or url,
        title=data.get("title") or url,
        uploader=data.get("uploader") or data.get("channel") or data.get("extractor_key") or "",
        duration=data.get("duration") or 0,
        views=data.get("view_count") or 0,
        date=data.get("upload_date") or "",
        thumbnail=thumb,
        heights=heights,
        has_video=any(f.get("vcodec") not in (None, "none") for f in data.get("formats") or []) or bool(heights),
        site=data.get("extractor_key") or "",
    )
    return info


def stream_url(ytdlp, url, audio_only):
    """Önizleme için doğrudan oynatılabilir tek bir akış adresi döner."""
    fmt = "ba[ext=m4a]/ba/b" if audio_only else "18/b[height<=480][vcodec!=none][acodec!=none]/b[vcodec!=none][acodec!=none]/b"
    r = subprocess.run([ytdlp, url, "-g", "-f", fmt, "--no-playlist", "--no-warnings", "--ignore-config"],
                       capture_output=True, stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW, timeout=90)
    lines = r.stdout.decode("utf-8", errors="replace").split()
    if r.returncode != 0 or not lines:
        err = r.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise RuntimeError(err[-1] if err else "Akış adresi alınamadı.")
    return lines[0]


def fetch_bytes(url, timeout=30, limit=20_000_000):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 VideoMuzikIndirici/" + APP_VERSION})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit)


# ----------------------------------------------------------------- uygulama güncelleme (GitHub Releases)
GITHUB_REPO = "mehmet-cizmeci/video-muzik-indirici"
RELEASE_API = os.environ.get("VMI_RELEASE_API") or f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
EXE_NAME = "VideoMuzikIndirici.exe"


def parse_version(v):
    import re
    nums = re.findall(r"\d+", v or "")
    return tuple(int(n) for n in nums[:3]) + (0,) * (3 - len(nums[:3]))


def check_app_update():
    """GitHub'daki son sürümü denetler. Daha yeniyse bilgi sözlüğü, değilse None döner."""
    import urllib.request
    req = urllib.request.Request(RELEASE_API, headers={
        "User-Agent": "VideoMuzikIndirici/" + APP_VERSION, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        rel = json.loads(r.read().decode("utf-8"))
    tag = rel.get("tag_name") or ""
    if rel.get("draft") or rel.get("prerelease") or parse_version(tag) <= parse_version(APP_VERSION):
        return None
    assets = {a.get("name"): a for a in rel.get("assets") or []}
    exe = assets.get(EXE_NAME)
    sha = assets.get(EXE_NAME + ".sha256")
    return {
        "version": tag.lstrip("vV"),
        "tag": tag,
        "name": rel.get("name") or tag,
        "notes": rel.get("body") or "",
        "page": rel.get("html_url") or f"https://github.com/{GITHUB_REPO}/releases/latest",
        "asset_url": exe.get("browser_download_url") if exe else "",
        "asset_size": exe.get("size", 0) if exe else 0,
        "sha_url": sha.get("browser_download_url") if sha else "",
    }


def download_app_update(info, progress):
    """Yeni exe'yi uygulamanın yanına indirir ve doğrular. İndirilen dosyanın yolunu döner."""
    import hashlib
    if not info.get("asset_url"):
        raise RuntimeError("Bu sürümde indirilecek exe dosyası yok. Sürüm sayfasından elle indirin.")
    target_dir = os.path.dirname(sys.executable)
    if not os.access(target_dir, os.W_OK):
        raise RuntimeError(f"Uygulama klasörüne yazılamıyor: {target_dir}\n"
                           "Exe'yi yazılabilir bir klasöre (ör. Masaüstü) taşıyın veya yeni sürümü elle indirin.")
    new_path = os.path.join(target_dir, EXE_NAME + ".new")
    download_file(info["asset_url"], new_path, progress)
    with open(new_path, "rb") as f:
        head = f.read(2)
    size = os.path.getsize(new_path)
    if head != b"MZ" or size < 1_000_000 or (info.get("asset_size") and size != info["asset_size"]):
        os.remove(new_path)
        raise RuntimeError("İndirilen dosya geçerli bir uygulama değil (eksik veya bozuk indirme).")
    if info.get("sha_url"):
        expected = fetch_bytes(info["sha_url"], limit=4096).decode("ascii", errors="ignore").split()[0].lower()
        h = hashlib.sha256()
        with open(new_path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest().lower() != expected:
            os.remove(new_path)
            raise RuntimeError("İndirilen dosyanın SHA-256 özeti tutmuyor; güncelleme iptal edildi.")
    return new_path


def apply_app_update(new_path):
    """Çalışan exe'yi yenisiyle değiştirir ve yeni sürümü başlatır. Çağıran ardından kapanmalıdır."""
    current = sys.executable
    old = current + ".old"
    if os.path.exists(old):
        os.remove(old)
    os.replace(current, old)          # Windows çalışan exe'nin yeniden adlandırılmasına izin verir
    try:
        os.replace(new_path, current)
    except Exception:
        os.replace(old, current)      # geri al
        raise
    env = {k: v for k, v in os.environ.items() if not k.startswith(("_MEI", "_PYI"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"   # yeni süreç kendi geçici klasörünü açsın
    subprocess.Popen([current, "--guncellendi"], env=env, close_fds=True,
                     creationflags=0x00000008 | 0x00000200)  # DETACHED_PROCESS | NEW_PROCESS_GROUP


def cleanup_old_update():
    """Önceki güncellemeden kalan .old dosyasını siler (eski süreç kapanana kadar birkaç kez dener)."""
    if not FROZEN:
        return
    old = sys.executable + ".old"
    for _ in range(20):
        if not os.path.exists(old):
            return
        try:
            os.remove(old)
            return
        except OSError:
            time.sleep(0.5)
