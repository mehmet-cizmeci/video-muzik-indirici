# Değişiklik Günlüğü

## [2.0.0] — 2026-11-10

Yeni arayüz, önizleme ve kendini güncelleme.

### Yeni
- **Modern arayüz** (Qt / PySide6): kartlı düzen, koyu ve açık tema (tek tıkla değişir), Windows 11 ikonları, yeni uygulama simgesi, koyu başlık çubuğu
- **Video ve ses önizleme**: bağlantı yapıştırılınca başlık, kanal, süre, görüntülenme, tarih, küçük resim ve en yüksek çözünürlük otomatik gelir; ▶ ile indirmeden izleme/dinleme; tamamlanan dosyaları uygulama içinde oynatma
- **Uygulama güncellemesi**: GitHub'daki yeni sürümü açılışta denetler; tek tıkla indirir, boyut ve SHA-256 ile doğrular, kendini değiştirip yeniden başlar; süren indirmeler kaldığı yerden devam eder; sürüm atlama ve elle denetleme
- **Ayarlar penceresi**: paralel indirme sayısı, tema, uyku engelleme, yt-dlp ve uygulama güncelleme tercihleri, günlük ve ayar klasörü kısayolları
- İndirme kuyruğunda ilerleme çubukları, renkli durum ikonları ve tür ikonları
- Bağlantıları pencereye **sürükle-bırak**
- İndirmeler bitince görev çubuğu bildirimi; sağ altta kısa bilgi mesajları
- Release'lerde güncelleyicinin doğrulaması için `.sha256` dosyası

### Değişen
- Kod ikiye ayrıldı: `core.py` (arayüzden bağımsız çekirdek) ve `ui_qt.py` (arayüz)
- Biten satıra çift tıklamak artık dosyayı önizlemede oynatır (klasörde göstermek için sağ tık → Klasörde göster)
- "Aynı anda" ayarı ana ekrandan Ayarlar penceresine taşındı
- Exe boyutu ~55 MB (Qt ve yerleşik oynatıcı nedeniyle)

### Düzeltilen
- Açılışta seçenekler yüklenirken indirme klasörünün varsayılana sıfırlanabilmesi önlendi

## [1.0.0] — 2026-11-05

İlk herkese açık sürüm.

### Özellikler
- Tek URL veya URL listesi girişi; `.txt` dosyasından liste yükleme
- İndirme türleri: Video + Ses, Sadece Ses, Sadece Video
- Video formatları: mp4, mkv, webm — 240p'den 4K'ya çözünürlük seçimi
- Ses formatları: mp3, m4a, opus, flac, wav — 96–320 kbps kalite seçimi
- Arka planda indirme kuyruğu, 1–5 paralel indirme
- Varsayılan ve seçilebilir indirme klasörü; tüm seçimlerin hatırlanması
- Oynatma listesi indirme (liste adlı klasöre, sıra numaralı)
- Kapak resmi ve etiket gömme, isteğe bağlı altyazı gömme
- Bağlantı kopmasında bekleyip kaldığı yerden devam etme
- Uyku/uyanma sonrası askıda kalan indirmeleri otomatik yeniden başlatma
- İndirme sürerken otomatik uykuyu engelleme
- Uygulama kapatılınca yarım kalan indirmeleri kaydedip sonraki açılışta sürdürme
- yt-dlp'yi tek tıkla veya açılışta otomatik güncelleme
- yt-dlp / FFmpeg yoksa ilk açılışta otomatik kurulum
- Hata ayrıntısı penceresi ve günlük dosyası
- Tek dosyalık Windows exe
