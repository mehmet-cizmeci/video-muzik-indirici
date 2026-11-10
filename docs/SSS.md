# ❓ Sık Sorulan Sorular ve Sorun Giderme

[← Ana sayfa](../README.md) · [Kullanım Kılavuzu](KULLANIM-KILAVUZU.md) · [Teknik Bilgi](TEKNIK.md)

## İçindekiler

**Genel**
- [Ücretsiz mi? Reklam veya virüs var mı?](#ücretsiz-mi-reklam-veya-virüs-var-mı)
- [Hangi sitelerden indirebilirim?](#hangi-sitelerden-indirebilirim)
- [İndirmek yasal mı?](#i̇ndirmek-yasal-mı)
- [Mac veya Linux'ta çalışır mı?](#mac-veya-linuxta-çalışır-mı)

**Kurulum ve açılış**
- ["Windows bilgisayarınızı korudu" uyarısı çıkıyor](#windows-bilgisayarınızı-korudu-uyarısı-çıkıyor)
- [Antivirüs programı exe'yi engelliyor](#antivirüs-programı-exeyi-engelliyor)
- [İlk açılışta "araç kurulumu başarısız" hatası](#i̇lk-açılışta-araç-kurulumu-başarısız-hatası)
- [Uygulama açılıyor ama hemen kapanıyor / açılmıyor](#uygulama-açılıyor-ama-hemen-kapanıyor--açılmıyor)

**İndirme sorunları**
- [Hiçbir video inmiyor, hepsi "Hata" veriyor](#hiçbir-video-inmiyor-hepsi-hata-veriyor)
- ["Sign in to confirm you're not a bot" hatası](#sign-in-to-confirm-youre-not-a-bot-hatası)
- ["Video unavailable" / "Private video" hatası](#video-unavailable--private-video-hatası)
- ["Requested format is not available" hatası](#requested-format-is-not-available-hatası)
- [Sürekli "Yeniden denenecek" durumunda kalıyor](#sürekli-yeniden-denenecek-durumunda-kalıyor)
- [İndirme çok yavaş](#i̇ndirme-çok-yavaş)
- [Yaş sınırlı veya üyelere özel videolar inmiyor](#yaş-sınırlı-veya-üyelere-özel-videolar-inmiyor)

**Önizleme**
- [Önizleme bilgileri gelmiyor](#önizleme-bilgileri-gelmiyor)
- [▶'ye basınca oynatmıyor veya "Oynatılamadı" diyor](#ye-basınca-oynatmıyor-veya-oynatılamadı-diyor)
- [Önizlemenin kalitesi düşük](#önizlemenin-kalitesi-düşük)

**Uygulama güncellemesi**
- [Yeni sürüm düğmesi hiç çıkmıyor](#yeni-sürüm-düğmesi-hiç-çıkmıyor)
- ["Uygulama klasörüne yazılamıyor" hatası](#uygulama-klasörüne-yazılamıyor-hatası)
- [Güncelleme yarıda kesildi, uygulama açılmıyor](#güncelleme-yarıda-kesildi-uygulama-açılmıyor)
- [1.0.0 sürümünden nasıl geçerim?](#100-sürümünden-nasıl-geçerim)
- [Exe neden eskisinden büyük?](#exe-neden-eskisinden-büyük)
- [İkonlar farklı / kare kutu görünüyor](#i̇konlar-farklı--kare-kutu-görünüyor)

**Dosyalar ve kalite**
- [Seçtiğim çözünürlükte inmedi](#seçtiğim-çözünürlükte-inmedi)
- [Videonun sesi yok](#videonun-sesi-yok)
- [Video telefonumda / TV'de açılmıyor](#video-telefonumda--tvde-açılmıyor)
- [İndirilen dosyalar nerede?](#i̇ndirilen-dosyalar-nerede)
- [Klasörde .part veya .ytdl uzantılı dosyalar var](#klasörde-part-veya-ytdl-uzantılı-dosyalar-var)
- [Kapak resmi görünmüyor](#kapak-resmi-görünmüyor)

**Diğer**
- [Ayarlarımı nasıl sıfırlarım?](#ayarlarımı-nasıl-sıfırlarım)
- [Uygulamayı nasıl kaldırırım?](#uygulamayı-nasıl-kaldırırım)
- [Hata bildirmek / öneride bulunmak istiyorum](#hata-bildirmek--öneride-bulunmak-istiyorum)

---

## Genel

### Ücretsiz mi? Reklam veya virüs var mı?

Evet, tamamen ücretsiz ve açık kaynaklıdır ([MIT lisansı](../LICENSE)). Reklam, izleme, veri toplama yoktur. Kaynak kodun tamamı bu depoda (`core.py`, `ui_qt.py`) okunabilir; isterseniz exe'yi kendiniz [derleyebilirsiniz](TEKNIK.md#kaynaktan-derleme).

Uygulamanın internete bağlandığı yerler yalnızca şunlardır: indirdiğiniz ve önizlediğiniz video siteleri, yt-dlp/FFmpeg'in resmi GitHub sürüm sayfaları (kurulum ve güncelleme için), bu deponun GitHub sürüm bilgisi (`api.github.com`, uygulama güncellemesi için) ve bağlantı kontrolü için `1.1.1.1` / `8.8.8.8` adreslerine kısa bir bağlantı denemesi.

### Hangi sitelerden indirebilirim?

yt-dlp'nin desteklediği her siteden: YouTube, YouTube Music, Vimeo, Dailymotion, SoundCloud, Twitter/X, Instagram, TikTok, Facebook, Twitch, Bandcamp, Reddit ve daha fazlası. Tam liste: [supportedsites.md](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

### İndirmek yasal mı?

Bu, içeriğe ve bulunduğunuz ülkenin yasalarına bağlıdır. Kendi videolarınızı, kamu malı veya Creative Commons lisanslı içerikleri ve sahibinin izin verdiği içerikleri indirmek genellikle sorun değildir. Telif hakkıyla korunan içerikleri izinsiz indirmek/dağıtmak yasalara ve platformların kullanım koşullarına aykırı olabilir. Sorumluluk kullanıcıya aittir.

### Mac veya Linux'ta çalışır mı?

Hazır exe yalnızca Windows içindir. Kaynak kod Python ve Qt (PySide6) ile yazıldığı için büyük ölçüde taşınabilirdir; ancak otomatik kurulum, uyku engelleme gibi bazı özellikler Windows'a özgüdür ve diğer sistemlerde test edilmemiştir.

---

## Kurulum ve açılış

### "Windows bilgisayarınızı korudu" uyarısı çıkıyor

Bu, Windows SmartScreen'in **dijital olarak imzalanmamış** ve henüz çok indirilmemiş programlar için gösterdiği standart uyarıdır; programın zararlı olduğu anlamına gelmez (kod imzalama sertifikaları ücretlidir).

Çalıştırmak için:
1. Uyarı penceresinde **Ek bilgi** bağlantısına tıklayın.
2. Görünen **Yine de çalıştır** düğmesine tıklayın.

Bu yalnızca ilk çalıştırmada sorulur.

Dosya tarayıcıdan indirildiği için "engellendi" işareti taşıyorsa: exe'ye sağ tıklayın → **Özellikler** → alttaki **Engellemeyi kaldır** kutusunu işaretleyin → **Tamam**.

### Antivirüs programı exe'yi engelliyor

PyInstaller ile paketlenmiş Python programları bazı antivirüs yazılımlarında **yanlış pozitif** uyarı verebilir. Seçenekleriniz:

- Dosyayı [VirusTotal](https://www.virustotal.com/)'da taratın.
- Antivirüs programınızda dosya için istisna tanımlayın.
- En güvenli yol: exe'yi kaynak koddan [kendiniz derleyin](TEKNIK.md#kaynaktan-derleme) ya da PySide6 kurup doğrudan `python indirici.pyw` ile çalıştırın.

### İlk açılışta "araç kurulumu başarısız" hatası

Uygulama yt-dlp ve FFmpeg'i GitHub'dan indiremedi demektir. Olası sebepler:

- **İnternet bağlantısı yok** → bağlantıyı kontrol edip **Tekrar dene**'ye basın.
- **Şirket/okul ağı GitHub'ı engelliyor** veya proxy kullanıyor → başka bir ağda deneyin.
- **Antivirüs indirilen exe'yi siliyor** → `%LOCALAPPDATA%\VideoMuzikIndirici\bin` klasörü için istisna tanımlayın.

**Elle kurulum** da mümkündür. Aşağıdakilerden biri yeterlidir:

- PowerShell veya Komut İstemi'nde (winget ile):
  ```
  winget install yt-dlp.yt-dlp
  winget install yt-dlp.FFmpeg
  ```
- Ya da dosyaları elle indirip `%LOCALAPPDATA%\VideoMuzikIndirici\bin` klasörüne koyun:
  - [yt-dlp.exe](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe)
  - [ffmpeg-master-latest-win64-gpl.zip](https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip) arşivinin `bin` klasöründeki `ffmpeg.exe` ve `ffprobe.exe`

Uygulama açılışta önce sistem `PATH`'ine, sonra bu klasöre bakar.

### Uygulama açılıyor ama hemen kapanıyor / açılmıyor

- Görev Yöneticisi'nde arka planda kalmış bir `VideoMuzikIndirici.exe` varsa sonlandırıp tekrar deneyin.
- Exe'yi `C:\Program Files` gibi yazma izni olmayan bir yerden değil, kendi klasörlerinizden çalıştırın.
- Antivirüs karantinasını kontrol edin.
- Sorun sürerse kaynak koddan `python indirici.pyw` ile çalıştırarak hata mesajını görebilir ve [bildirebilirsiniz](#hata-bildirmek--öneride-bulunmak-istiyorum).

---

## İndirme sorunları

### Hiçbir video inmiyor, hepsi "Hata" veriyor

En yaygın sebep **yt-dlp'nin eski kalmasıdır**; YouTube sık sık değişir.

1. Alt çubuktaki **⟳ yt-dlp güncelle** düğmesine basın.
2. Hatalı satırları seçip **Yeniden dene** deyin.

Hâlâ olmuyorsa sağ tık → **Hata ayrıntısı** ile mesajı okuyun ve aşağıdaki maddelere bakın.

### "Sign in to confirm you're not a bot" hatası

YouTube, kısa sürede çok fazla istek gelen IP adreslerinden doğrulama isteyebilir. Şunları deneyin:

- yt-dlp'yi güncelleyin (çoğu zaman yeni sürümler bu durumu aşar).
- **Aynı anda** değerini 1'e düşürün ve bir süre bekleyin.
- VPN kullanıyorsanız kapatın veya farklı bir sunucu seçin.

### "Video unavailable" / "Private video" hatası

Video silinmiş, gizli yapılmış ya da bölgenizde engelli demektir. Uygulama bu tür kalıcı hatalarda yeniden denemez. Bağlantıyı tarayıcıda açıp videonun gerçekten izlenebildiğini kontrol edin.

### "Requested format is not available" hatası

Seçtiğiniz tür/format bu videoda yok demektir (örneğin canlı yayınlar veya çok eski videolar). Formatı `mkv` veya çözünürlüğü `En iyi` yapıp tekrar deneyin.

### Sürekli "Yeniden denenecek" durumunda kalıyor

Uygulama geçici hatalarda kendiliğinden yeniden dener; bekleme süresi her denemede artar (5 sn → 2 dk). İnternet varken art arda 8 deneme hiç ilerleme olmadan başarısız olursa satır **Hata** olur.

- Sağ tık → **Hata ayrıntısı** ile sebebi görün.
- Satırı iptal edip yt-dlp'yi güncelleyin, sonra **Yeniden dene** deyin.

### İndirme çok yavaş

- **Aynı anda** değerini azaltın; çok sayıda paralel indirme bant genişliğini böler.
- Bazı siteler indirme hızını sunucu tarafında sınırlar; bu durumda yapılabilecek bir şey yoktur.
- yt-dlp'yi güncelleyin; YouTube'un hız sınırlaması bazen yalnızca yeni sürümlerle aşılabilir.

### Yaş sınırlı veya üyelere özel videolar inmiyor

Bu videolar oturum açmayı gerektirir. Video Müzik İndirici şu an hesap/çerez desteği sunmaz; bu tür içerikler indirilemez.

---

## Önizleme

### Önizleme bilgileri gelmiyor

- Bilgiler, kutuda **tek bir bağlantı** varken kendiliğinden gelir. Birden fazla bağlantı varsa **Önizle** düğmesine basın (ilk bağlantı gösterilir).
- Panelde "Önizleme alınamadı" ve altında bir mesaj yazıyorsa sebep çoğunlukla indirmedeki gibidir: video silinmiş/gizli, bağlantı hatalı veya yt-dlp eski. **Ayarlar → yt-dlp'yi güncelle** ile güncelleyip tekrar deneyin.
- Bazı siteler küçük resim vermez; bu durumda yalnızca başlık ve bilgiler görünür.

### ▶'ye basınca oynatmıyor veya "Oynatılamadı" diyor

- Önizleme internetten akış olarak oynar; bağlantınızı kontrol edin.
- Akış adresleri birkaç saat geçerlidir. Uzun süre bekledikten sonra oynamazsa **Önizle**'ye yeniden basın.
- Bazı siteler (veya yaş/üyelik gerektiren videolar) doğrudan oynatılabilir akış vermez. Bu durumda önizleme yapılamaz ama indirme genellikle yine çalışır.
- Ses gelmiyorsa ses simgesinin kapalı (🔇) olmadığına ve ses çubuğunun açık olduğuna bakın.

### Önizlemenin kalitesi düşük

Önizleme hızlı başlasın ve az veri harcasın diye en fazla ~480p akış kullanır. **İndirilen dosya seçtiğiniz kalitede olur**; indirme bitince satıra çift tıklayarak gerçek kaliteyi uygulama içinde izleyebilirsiniz.

---

## Uygulama güncellemesi

### Yeni sürüm düğmesi hiç çıkmıyor

- Zaten en güncel sürümü kullanıyor olabilirsiniz: **Ayarlar → Uygulama güncellemesini denetle** ile kontrol edin.
- **Ayarlar → Açılışta uygulamanın yeni sürümünü denetle** kapalı olabilir.
- Bir sürüm için **Bu sürümü atla** dediyseniz o sürüm için düğme gösterilmez (elle denetlediğinizde yine görünür).
- Kaynaktan (`python indirici.pyw`) çalıştırıyorsanız güncelleme, exe'yi değiştirmek yerine sürüm sayfasını açar.

### "Uygulama klasörüne yazılamıyor" hatası

Güncelleyici yeni exe'yi mevcut exe'nin yanına indirip yerini değiştirir. Exe `C:\Program Files` gibi yazma izniniz olmayan bir klasördeyse bu yapılamaz. Exe'yi **Belgeler** veya **Masaüstü** gibi bir klasöre taşıyın ya da yeni sürümü sürüm sayfasından elle indirin.

### Güncelleme yarıda kesildi, uygulama açılmıyor

Güncelleyici, indirilen dosyayı boyut ve SHA-256 özetiyle doğrulamadan eskisinin yerine koymaz; eksik veya bozuk indirme uygulanmaz. Yine de bir sorun olursa:

1. Exe'nin bulunduğu klasörde `VideoMuzikIndirici.exe.old` dosyası varsa, bu önceki sürümdür. Adını `VideoMuzikIndirici.exe` yapın.
2. Ya da son sürümü [Releases](https://github.com/mehmet-cizmeci/video-muzik-indirici/releases/latest) sayfasından yeniden indirin.

Ayarlarınız ve yarım kalan indirmeleriniz `%APPDATA%\VideoMuzikIndirici` klasöründe durduğu için kaybolmaz.

### 1.0.0 sürümünden nasıl geçerim?

1.0.0 kendini güncelleyemez. 2.0.0'ı bir kez [Releases](https://github.com/mehmet-cizmeci/video-muzik-indirici/releases/latest) sayfasından indirip eski exe'nin yerine koyun. Ayarlarınız (klasör, format, kalite) ve yarım kalan indirmeleriniz korunur. Bundan sonraki sürümler uygulama içinden gelir.

### Exe neden eskisinden büyük?

2.0 sürümü modern arayüz ve **yerleşik video/ses oynatıcı** için Qt kütüphanelerini içerir; bu yüzden exe ~10 MB'tan ~55 MB'a çıktı. yt-dlp ve FFmpeg hâlâ exe'nin içinde değildir, ilk açılışta ayrıca indirilir.

### İkonlar farklı / kare kutu görünüyor

Uygulama ikonları Windows'un yerleşik ikon yazı tipiyle çizilir (Windows 11'de *Segoe Fluent Icons*, Windows 10'da *Segoe MDL2 Assets*). Windows 10'da bazı ikonlar biraz farklı görünebilir. Kare kutular görünüyorsa Windows güncellemelerini yükleyin.

---

## Dosyalar ve kalite

### Seçtiğim çözünürlükte inmedi

Seçilen çözünürlük bir **üst sınırdır**. Video o çözünürlükte yoksa, altındaki en iyi kalite indirilir. Örneğin 720p yüklenmiş bir videoda 1080p seçmek 720p dosya verir.

`mp4` formatında, uyumluluk için H.264/AV1 + AAC akışları tercih edilir. YouTube'da 1440p ve 4K genellikle yalnızca VP9 ile sunulduğundan bu çözünürlükler için **mkv** seçin.

### Videonun sesi yok

**İndirme türü** olarak `Sadece Video (sessiz)` seçilmiş olabilir. `Video + Ses` seçip yeniden indirin.

Ses var ama bazı oynatıcılarda duyulmuyorsa, dosya `opus` ses içeriyor olabilir; [VLC](https://www.videolan.org/) ile açmayı deneyin veya `mp4` formatını kullanın.

### Video telefonumda / TV'de açılmıyor

Formatı **mp4** seçin. mkv ve webm dosyaları bazı cihazlarda desteklenmez. 4K/AV1 videolar eski cihazlarda donabilir; 1080p seçmeyi deneyin.

### İndirilen dosyalar nerede?

Varsayılan olarak `C:\Users\<kullanıcı adınız>\Downloads\Video Muzik Indirici` klasöründe. Hızlı ulaşmak için indirme yeri satırındaki **Aç** düğmesine basın veya biten satıra sağ tıklayıp **Klasörde göster**'i seçin. Oynatma listeleri bu klasörün içinde, liste adını taşıyan alt klasörlere iner.

### Klasörde .part veya .ytdl uzantılı dosyalar var

Bunlar **yarım kalmış** indirmelerin geçici dosyalarıdır ve kaldığı yerden devam etmeyi sağlar. İndirme tamamlanınca kendiliğinden silinir. İlgili indirmeyi iptal ettiyseniz ve devam etmeyecekseniz elle silebilirsiniz.

### Kapak resmi görünmüyor

- **Kapak resmi göm** seçeneğinin işaretli olduğundan emin olun.
- `wav` ve `webm` formatları gömülü kapağı desteklemez.
- Windows Gezgini küçük resim önbelleğini geç yenileyebilir; dosyayı bir müzik çalarda açarak kontrol edin.

---

## Diğer

### Ayarlarımı nasıl sıfırlarım?

Uygulamayı kapatın ve şu dosyayı silin:

```
%APPDATA%\VideoMuzikIndirici\settings.json
```

(Windows Gezgini'nin adres çubuğuna `%APPDATA%\VideoMuzikIndirici` yazıp Enter'a basarak klasöre ulaşabilirsiniz.) Yarım kalan kuyruğu da temizlemek isterseniz aynı klasördeki `queue.json` dosyasını silin.

### Uygulamayı nasıl kaldırırım?

Kurulum yapılmadığı için kaldırma da basittir:

1. `VideoMuzikIndirici.exe` dosyasını (ve varsa kısayolunu) silin.
2. İsterseniz şu klasörleri de silin:
   - `%APPDATA%\VideoMuzikIndirici` — ayarlar, kuyruk, günlük
   - `%LOCALAPPDATA%\VideoMuzikIndirici` — otomatik kurulan yt-dlp ve FFmpeg

İndirdiğiniz dosyalar bu işlemden etkilenmez.

### Hata bildirmek / öneride bulunmak istiyorum

[GitHub Issues](https://github.com/mehmet-cizmeci/video-muzik-indirici/issues) sayfasından yeni bir kayıt açın. Lütfen şunları ekleyin:

- Uygulama sürümü (pencere başlığında) ve yt-dlp sürümü (alt çubukta)
- Ne yaptığınız ve ne olduğu
- Sağ tık → **Hata ayrıntısı** metni veya `%APPDATA%\VideoMuzikIndirici\indirici.log` dosyasının ilgili kısmı

> Özel/kişisel bağlantılarınızı paylaşmamaya dikkat edin.
