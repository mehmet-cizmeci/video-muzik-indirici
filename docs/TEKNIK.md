# ⚙ Teknik Bilgi

[← Ana sayfa](../README.md) · [Kullanım Kılavuzu](KULLANIM-KILAVUZU.md) · [Sık Sorulan Sorular](SSS.md)

Bu sayfa uygulamanın nasıl çalıştığını, dosyalarını nerede tuttuğunu ve kaynaktan nasıl derleneceğini anlatır.

## İçindekiler

- [Mimari](#mimari)
- [Dosya ve klasör konumları](#dosya-ve-klasör-konumları)
- [yt-dlp ve FFmpeg'in bulunması ve kurulumu](#yt-dlp-ve-ffmpegin-bulunması-ve-kurulumu)
- [Kullanılan yt-dlp ayarları](#kullanılan-yt-dlp-ayarları)
- [Kesinti ve yeniden deneme mantığı](#kesinti-ve-yeniden-deneme-mantığı)
- [Kaynaktan çalıştırma](#kaynaktan-çalıştırma)
- [Kaynaktan derleme](#kaynaktan-derleme)
- [Depo yapısı](#depo-yapısı)

---

## Mimari

Uygulama tek bir Python dosyasıdır (`indirici.pyw`) ve yalnızca standart kütüphaneyi kullanır (Tkinter arayüz, `subprocess`, `threading`, `urllib`).

```
┌────────────────────────── Arayüz (Tkinter, ana iş parçacığı) ──────────────────────────┐
│  URL kutusu · Seçenekler · Kuyruk tablosu · Alt çubuk                                   │
│        ▲  150 ms'de bir olay kuyruğunu okur ve tabloyu günceller                        │
└────────┼────────────────────────────────────────────────────────────────────────────────┘
         │ queue.Queue (olaylar: update / done / install / updated / version)
┌────────┴─────────────── Downloader ─────────────────────────────────────────────────────┐
│  bekleyenler listesi ──► en fazla N işçi iş parçacığı (Aynı anda = N)                   │
│        her işçi:  yt-dlp.exe alt sürecini başlatır, çıktısını satır satır ayrıştırır    │
│                   + izleme (watchdog) iş parçacığı: 90 sn veri yoksa süreci yeniden     │
│                     başlatır                                                            │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

- İndirmeler **yt-dlp.exe alt süreci** olarak çalışır. Bu sayede bir indirme iptal edildiğinde süreç ağacı (`taskkill /T`) temizce sonlandırılabilir ve yt-dlp kendi kendini güncelleyebilir.
- yt-dlp'nin ilerlemesi `--progress-template` ile makine tarafından okunabilir satırlara (`PROG|yüzde|hız|kalan`) dönüştürülür. Başlık ve dosya yolu `--print` ile alınır.
- Arayüz hiçbir zaman ağ veya disk işlemi beklemez; tüm uzun işler iş parçacıklarında yürür ve sonuçlarını olay kuyruğu üzerinden bildirir.

## Dosya ve klasör konumları

| Konum | İçerik |
|---|---|
| `%APPDATA%\VideoMuzikIndirici\settings.json` | Seçenekler (tür, format, kalite, klasör, paralel sayısı, otomatik güncelleme vb.) |
| `%APPDATA%\VideoMuzikIndirici\queue.json` | Tamamlanmamış indirmeler (uygulama yeniden açıldığında sürdürülür) |
| `%APPDATA%\VideoMuzikIndirici\indirici.log` | Her indirmenin sonucu; başarısız olanlar için yt-dlp'nin son 40 satırı. 2 MB'ı geçince `.old` olarak döndürülür |
| `%LOCALAPPDATA%\VideoMuzikIndirici\bin\` | Otomatik kurulan `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe` |
| `%USERPROFILE%\Downloads\Video Muzik Indirici\` | Varsayılan indirme klasörü |

> **Not (Microsoft Store Python):** Kaynaktan, Microsoft Store'dan kurulmuş Python ile çalıştırırsanız Windows `%APPDATA%` yazımlarını paketin sanal klasörüne (`%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.x_...\LocalCache\Roaming\...`) yönlendirir. Exe sürümünde bu durum yoktur.

## yt-dlp ve FFmpeg'in bulunması ve kurulumu

Açılışta her araç şu sırayla aranır:

1. Sistem `PATH`'i (`shutil.which`)
2. `%LOCALAPPDATA%\VideoMuzikIndirici\bin\`
3. `%LOCALAPPDATA%\Microsoft\WinGet\Links\`
4. Uygulamanın kendi klasörü
5. `%LOCALAPPDATA%\Microsoft\WinGet\Packages\` altı (winget ile kurulmuş paketler)

Biri bulunamazsa resmi sürümler `bin` klasörüne indirilir:

| Araç | Kaynak |
|---|---|
| yt-dlp | `https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe` |
| FFmpeg | `https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip` (yalnızca `ffmpeg.exe` ve `ffprobe.exe` çıkarılır) |

**Güncelleme:** önce `yt-dlp -U` denenir; başarısız olursa (örneğin paket yöneticisiyle kurulmuşsa) `winget upgrade --id yt-dlp.yt-dlp` çalıştırılır. Otomatik güncelleme açılışta, son başarılı kontrolden 24 saat geçmişse yapılır. Aktif indirme varken güncelleme yapılmaz (çalışan exe değiştirilemez).

## Kullanılan yt-dlp ayarları

Her indirme için oluşturulan komutun ortak kısmı:

| Ayar | Amaç |
|---|---|
| `--ignore-config` | Kullanıcının kendi yt-dlp yapılandırması uygulamanın davranışını bozmasın |
| `--newline --no-colors --encoding utf-8` | Ayrıştırılabilir, Türkçe karakterleri bozmayan çıktı |
| `--progress-template "download:PROG\|…"` | Makine tarafından okunabilir ilerleme satırları |
| `--print before_dl:TITLE\|…` / `--print after_move:FILE\|…` | Başlık, liste sırası ve son dosya yolu |
| `--no-simulate --no-quiet --progress` | `--print` kullanılırken indirmenin ve ilerlemenin sürmesi |
| `-P <klasör> -o "%(title).180B [%(id)s].%(ext)s"` | Dosya adı (Windows yol uzunluğu sınırına karşı kısaltılmış) |
| `--embed-metadata` | Başlık, kanal, tarih vb. etiketleri dosyaya yazar |
| `--continue` | Yarım kalan `.part` dosyasından devam eder |
| `--socket-timeout 30` | Askıda kalan bağlantıları 30 sn'de keser |
| `--retries 15 --fragment-retries 15 --file-access-retries 10` | yt-dlp içi yeniden denemeler |
| `--retry-sleep http:exp=1:30 --retry-sleep fragment:exp=1:30` | Denemeler arasında üstel bekleme |
| `--ffmpeg-location <yol>` | Bulunan FFmpeg'in kullanılması |

Türe göre eklenenler:

| Seçim | Eklenen ayarlar |
|---|---|
| Video + Ses | `-f "bv*+ba/b" --merge-output-format <fmt>` ve `-S "res:<yükseklik>[,ext:mp4:m4a]"`; mp4/mkv için `--remux-video <fmt>` |
| Sadece Video | `-f "bv/b"` ve aynı `-S` sıralaması |
| Sadece Ses | `-f "ba/b" -x --audio-format <fmt> --audio-quality <0 \| 320K …>` |
| Kapak resmi | `--embed-thumbnail --convert-thumbnails jpg` (mp3, m4a, opus, flac, mp4, mkv) |
| Altyazı | `--write-subs --sub-langs "tr.*,en.*" --embed-subs` |
| Oynatma listesi | `--yes-playlist` ve `-o "%(playlist_title)s/%(playlist_index)03d - %(title)s [%(id)s].%(ext)s"`; değilse `--no-playlist` |

Çözünürlük `-f` filtresi yerine `-S res:N` **sıralaması** ile uygulanır: bu yöntem tam eşleşme yoksa hata vermek yerine N'nin altındaki en iyi kaliteyi seçer.

## Kesinti ve yeniden deneme mantığı

Her indirme, uygulama düzeyinde bir döngü içinde yürür:

```
deneme:
    yt-dlp'yi çalıştır (yarım dosyadan devam eder)
    başarılı           → Tamamlandı
    kullanıcı iptali   → İptal edildi / (kapanışta) kuyruğa kaydedildi
    kalıcı hata        → Hata  (video silinmiş, gizli, geçersiz URL, 404, desteklenmeyen site …)
    geçici hata:
        internet yoksa → "Bağlantı bekleniyor…", 5 sn'de bir kontrol, sayaç artmaz
        bu denemede ilerleme olduysa sayaç sıfırlanır
        internet varken üst üste 8 ilerlemesiz hata → Hata
        bekle: 5, 10, 20, 40, 80, 120 sn … ("Yeniden denenecek")
        tekrar dene
```

- **İnternet kontrolü:** `1.1.1.1:443`, `8.8.8.8:53` veya `www.google.com:443` adreslerinden birine 4 sn içinde TCP bağlantısı kurulabiliyorsa internet var sayılır.
- **Askıda kalma (watchdog):** Durum *İndiriliyor* iken 90 sn boyunca yt-dlp'den hiç çıktı gelmezse (tipik olarak uyku/uyanma sonrası ölü bağlantı), süreç sonlandırılır ve 3 sn sonra kaldığı yerden yeniden başlatılır. *İşleniyor* aşamasında (FFmpeg dönüştürmesi) bu kontrol uygulanmaz.
- **Uyku engelleme:** Aktif indirme varken `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)` çağrılır; kuyruk boşalınca eski duruma döner.
- **Kalıcı kuyruk:** Her ekleme/bitişte ve kapanışta tamamlanmamış işler `queue.json`'a yazılır. Açılışta bu dosya okunur ve işler kuyruğa yeniden eklenir; yt-dlp `.part` dosyaları ve mevcut dosyaları atlaması sayesinde kaldığı yerden devam eder.

## Kaynaktan çalıştırma

Gereksinim: Windows ve **Python 3.9+** (python.org kurulumu veya Microsoft Store; Tkinter dahil gelir). Ek paket gerekmez.

```bash
git clone https://github.com/mehmet-cizmeci/video-muzik-indirici.git
cd video-muzik-indirici
python indirici.pyw
```

`.pyw` uzantısı sayesinde dosyaya çift tıklayarak konsol penceresi açmadan da çalıştırabilirsiniz.

## Kaynaktan derleme

Tek dosyalık exe için:

```bash
build.bat
```

Betik şunları yapar:

1. `pip install pyinstaller pillow`
2. `python make_icon.py` → `indirici.ico` simgesini üretir
3. `PyInstaller --onefile --windowed --name VideoMuzikIndirici --icon indirici.ico --add-data "indirici.ico;." indirici.pyw`

Çıktı: `dist\VideoMuzikIndirici.exe` (~10 MB). yt-dlp ve FFmpeg exe'nin **içine gömülmez**; böylece exe küçük kalır ve yt-dlp bağımsız olarak güncellenebilir.

## Depo yapısı

```
video-muzik-indirici/
├── indirici.pyw            # uygulamanın tamamı
├── make_icon.py            # simge üretici (Pillow)
├── indirici.ico            # uygulama simgesi
├── build.bat               # exe derleme betiği
├── README.md
├── CHANGELOG.md
├── LICENSE
└── docs/
    ├── KULLANIM-KILAVUZU.md
    ├── SSS.md
    ├── TEKNIK.md
    └── img/ana-ekran.png
```

Katkılar memnuniyetle karşılanır: [Issues](https://github.com/mehmet-cizmeci/video-muzik-indirici/issues) üzerinden öneri veya hata bildirebilir, Pull Request gönderebilirsiniz.
