# ⚙ Teknik Bilgi

[← Ana sayfa](../README.md) · [Kullanım Kılavuzu](KULLANIM-KILAVUZU.md) · [Sık Sorulan Sorular](SSS.md)

Bu sayfa uygulamanın nasıl çalıştığını, dosyalarını nerede tuttuğunu ve kaynaktan nasıl derleneceğini anlatır.

## İçindekiler

- [Mimari](#mimari)
- [Dosya ve klasör konumları](#dosya-ve-klasör-konumları)
- [yt-dlp ve FFmpeg'in bulunması ve kurulumu](#yt-dlp-ve-ffmpegin-bulunması-ve-kurulumu)
- [Kullanılan yt-dlp ayarları](#kullanılan-yt-dlp-ayarları)
- [Kesinti ve yeniden deneme mantığı](#kesinti-ve-yeniden-deneme-mantığı)
- [Önizleme](#önizleme)
- [Uygulama güncellemesi](#uygulama-güncellemesi)
- [Kaynaktan çalıştırma](#kaynaktan-çalıştırma)
- [Kaynaktan derleme](#kaynaktan-derleme)
- [Depo yapısı](#depo-yapısı)

---

## Mimari

Uygulama üç Python dosyasından oluşur:

| Dosya | Görevi |
|---|---|
| `indirici.pyw` | Giriş noktası; yalnızca arayüzü başlatır |
| `core.py` | Arayüzden bağımsız çekirdek: indirme kuyruğu ve yt-dlp çalıştırma, yeniden deneme, ayarlar, kalıcı kuyruk, araç kurulumu, yt-dlp güncelleme, önizleme bilgisi/akış adresi, uygulama güncellemesi. Yalnızca standart kütüphaneyi kullanır |
| `ui_qt.py` | **PySide6 (Qt 6)** arayüzü: tema/stil (QSS), kartlar, kuyruk tablosu, önizleme oynatıcısı (`QMediaPlayer` + `QVideoWidget`), ayarlar/güncelleme/kurulum pencereleri |

```
┌────────────────────────── Arayüz (Qt, ana iş parçacığı) ───────────────────────────────┐
│  Bağlantılar · Seçenekler · Önizleme (QMediaPlayer) · Kuyruk tablosu · Ayarlar          │
│        ▲  QTimer ile 120 ms'de bir olay kuyruğunu okur ve ekranı günceller              │
└────────┼────────────────────────────────────────────────────────────────────────────────┘
         │ queue.Queue (update / done / probe / thumb / stream / install / app_check …)
┌────────┴───────────── core.Downloader ve arka plan işleri ──────────────────────────────┐
│  bekleyenler ──► en fazla N işçi iş parçacığı (Aynı anda = N)                           │
│     her işçi: yt-dlp.exe alt sürecini başlatır, çıktısını satır satır ayrıştırır        │
│               + izleme (watchdog): 90 sn veri yoksa süreci yeniden başlatır             │
│  önizleme:    yt-dlp -J (bilgi) · yt-dlp -g (akış adresi) · küçük resim indirme         │
│  güncelleme:  GitHub Releases API · exe indirme + SHA-256 doğrulama · exe değiştirme    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

- İndirmeler **yt-dlp.exe alt süreci** olarak çalışır; iptalde süreç ağacı (`taskkill /T`) temizce sonlandırılır ve yt-dlp kendi kendini güncelleyebilir.
- yt-dlp'nin ilerlemesi `--progress-template` ile makine tarafından okunabilir satırlara (`PROG|yüzde|hız|kalan`) dönüştürülür; başlık ve dosya yolu `--print` ile alınır.
- Arayüz hiçbir zaman ağ veya disk işlemi beklemez; uzun işler iş parçacıklarında yürür ve sonuçlarını olay kuyruğuyla bildirir. Önizleme isteklerinde bir **jeton** (token) tutulur; kullanıcı arada başka bir bağlantıya geçtiyse eski sonuç yok sayılır.
- **İkonlar** Windows'un yerleşik ikon yazı tipinden çizilir (Windows 11: *Segoe Fluent Icons*, Windows 10: *Segoe MDL2 Assets*); ek görsel dosyası gerekmez. Tema değişince ikonlar yeni renkle yeniden çizilir.
- **Tema**: iki renk paleti (`THEMES` sözlüğü) ve bunlardan üretilen bir Qt stil sayfası. Koyu temada pencere başlık çubuğu da `DwmSetWindowAttribute` ile koyulaştırılır.

## Dosya ve klasör konumları

| Konum | İçerik |
|---|---|
| `%APPDATA%\VideoMuzikIndirici\settings.json` | Seçenekler (tür, format, kalite, klasör, paralel sayısı, tema, ses düzeyi, güncelleme tercihleri, atlanan sürüm vb.) |
| `%APPDATA%\VideoMuzikIndirici\ui\` | Tema için üretilen küçük ikon görselleri (onay işareti, açılır ok) |
| `%APPDATA%\VideoMuzikIndirici\queue.json` | Tamamlanmamış indirmeler (uygulama yeniden açıldığında sürdürülür) |
| `%APPDATA%\VideoMuzikIndirici\indirici.log` | Her indirmenin sonucu; başarısız olanlar için yt-dlp'nin son 40 satırı. 2 MB'ı geçince `.old` olarak döndürülür |
| `%LOCALAPPDATA%\VideoMuzikIndirici\bin\` | Otomatik kurulan `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe` |
| Exe'nin klasörü: `VideoMuzikIndirici.exe.new` / `.old` | Güncelleme sırasında geçici olarak oluşur, işlem bitince silinir |
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

## Önizleme

1. **Bilgi:** `yt-dlp <url> -J --flat-playlist` ile video bilgisi (JSON) alınır. Oynatma listesiyse liste adı ve öğe sayısı okunur, ardından ilk öğe için `-J --no-playlist` çalıştırılır. Başlık, kanal, süre, görüntülenme, tarih, ~640 px civarı bir küçük resim ve formatlardaki yükseklikler (en yüksek çözünürlük ipucu için) çıkarılır.
2. **Otomatik tetikleme:** bağlantı kutusu değiştikten 0,9 sn sonra, kutuda tek bir bağlantı varsa ve daha önce önizlenmediyse bilgi alınır.
3. **Oynatma:** ▶'ye basılınca `yt-dlp -g` ile doğrudan oynatılabilir **tek** bir akış adresi istenir:
   - video: `18/b[height<=480][vcodec!=none][acodec!=none]/…` (görüntü ve sesi bir arada olan, hızlı başlayan bir akış),
   - ses: `ba[ext=m4a]/ba/b`.
   Adres Qt'nin `QMediaPlayer`'ına verilir (Qt 6'nın FFmpeg arka ucu HTTPS akışlarını doğrudan oynatır). Ses önizlemesinde video yüzeyi yerine küçük resim ve "♪ Ses önizlemesi" rozeti gösterilir.
4. **Yerel dosya:** tamamlanan bir indirmeye çift tıklanınca dosya `QUrl.fromLocalFile` ile aynı oynatıcıda açılır.

## Uygulama güncellemesi

```
açılış (veya Ayarlar → denetle)
   └─► GET https://api.github.com/repos/mehmet-cizmeci/video-muzik-indirici/releases/latest
         tag_name > APP_VERSION ?  (taslak / ön sürüm yok sayılır)
            hayır → bir şey yapma (elle denetimde "en güncel" mesajı)
            evet  → sağ üstte "Yeni sürüm x.y.z" düğmesi, sürüm notları penceresi
                      "Şimdi güncelle":
                        1. VideoMuzikIndirici.exe  → <exe klasörü>\VideoMuzikIndirici.exe.new
                        2. doğrulama: "MZ" başlığı, boyut = Release'teki boyut,
                           SHA-256 = VideoMuzikIndirici.exe.sha256 dosyasındaki özet
                        3. süren indirmeler queue.json'a kaydedilir ve durdurulur
                        4. çalışan exe → .old  (Windows çalışan exe'nin yeniden adlandırılmasına izin verir)
                           .new → VideoMuzikIndirici.exe   (hata olursa .old geri alınır)
                        5. yeni exe "--guncellendi" ile başlatılır, eski süreç kapanır
                        6. yeni süreç .old dosyasını siler, "güncellendi" bildirimi gösterir,
                           kuyruğu geri yükleyip indirmeleri sürdürür
```

- Yeni süreç `PYINSTALLER_RESET_ENVIRONMENT=1` ile başlatılır; böylece PyInstaller'ın tek dosyalık exe'si eski sürecin geçici klasörünü değil kendi klasörünü kullanır.
- Kaynaktan çalışırken (`FROZEN` değilken) exe değiştirilmez; güncelleme düğmesi sürüm sayfasını açar.
- Test için `VMI_RELEASE_API` ortam değişkeniyle sürüm bilgisinin alınacağı adres değiştirilebilir (ör. yerel bir sunucu).
- **Yayınlama:** her sürümde Release'e hem `VideoMuzikIndirici.exe` hem de `VideoMuzikIndirici.exe.sha256` yüklenmelidir; `build.bat` ikisini de üretir. Sürüm etiketi `vX.Y.Z` biçiminde olmalı ve `core.py` içindeki `APP_VERSION` ile aynı olmalıdır.

## Kaynaktan çalıştırma

Gereksinim: Windows ve **Python 3.9+** ile **PySide6** (`python -m pip install pyside6`).

```bash
git clone https://github.com/mehmet-cizmeci/video-muzik-indirici.git
cd video-muzik-indirici
python -m pip install pyside6
python indirici.pyw
```

`.pyw` uzantısı sayesinde dosyaya çift tıklayarak konsol penceresi açmadan da çalıştırabilirsiniz.

## Kaynaktan derleme

Tek dosyalık exe için:

```bash
build.bat
```

Betik şunları yapar:

1. `pip install pyside6 pyinstaller pillow`
2. `python make_icon.py` → `indirici.ico` ve `indirici.png` simgelerini üretir
3. PyInstaller ile tek dosyalık, konsolsuz exe derler (`--onefile --windowed`; simgeler gömülür; tkinter ve kullanılmayan Qt modülleri — QML/Quick, WebEngine, 3D, PDF — dışarıda bırakılır)
4. `tools\imzala.ps1` ile exe'yi imzalar (sertifika bağlı değilse imzasız bırakıp uyarır; `build.bat /imzazorunlu` ile hata verir). Ayrıntılar: [Dijital İmza Rehberi](IMZALAMA.md)
5. Güncelleyicinin doğrulaması için `dist\VideoMuzikIndirici.exe.sha256` dosyasını üretir

Çıktı: `dist\VideoMuzikIndirici.exe` (~55 MB; Qt ve oynatıcı için FFmpeg kitaplıkları dahil). yt-dlp ve FFmpeg komut satırı araçları exe'nin **içine gömülmez**; ilk açılışta indirilir ve bağımsız olarak güncellenir.

## Depo yapısı

```
video-muzik-indirici/
├── indirici.pyw            # giriş noktası
├── core.py                 # indirme, kuyruk, kurulum, önizleme, güncelleme (arayüzsüz)
├── ui_qt.py                # PySide6 arayüzü
├── make_icon.py            # simge üretici (Pillow)
├── indirici.ico / .png     # uygulama simgesi
├── build.bat               # exe derleme (+ imzalama, SHA-256) betiği
├── tools/imzala.ps1        # ortak kod imzalama betiği
├── README.md
├── CHANGELOG.md
├── LICENSE
└── docs/
    ├── KULLANIM-KILAVUZU.md
    ├── SSS.md
    ├── TEKNIK.md
    ├── IMZALAMA.md
    └── img/                # ekran görüntüleri
```

Katkılar memnuniyetle karşılanır: [Issues](https://github.com/mehmet-cizmeci/video-muzik-indirici/issues) üzerinden öneri veya hata bildirebilir, Pull Request gönderebilirsiniz.
