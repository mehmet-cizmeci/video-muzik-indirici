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

Evet, tamamen ücretsiz ve açık kaynaklıdır ([MIT lisansı](../LICENSE)). Reklam, izleme, veri toplama yoktur. Kaynak kodun tamamı bu depoda (`indirici.pyw`) okunabilir; isterseniz exe'yi kendiniz [derleyebilirsiniz](TEKNIK.md#kaynaktan-derleme).

Uygulamanın internete bağlandığı yerler yalnızca şunlardır: indirdiğiniz video siteleri, yt-dlp/FFmpeg'in resmi GitHub sürüm sayfaları (kurulum ve güncelleme için) ve bağlantı kontrolü için `1.1.1.1` / `8.8.8.8` adreslerine kısa bir bağlantı denemesi.

### Hangi sitelerden indirebilirim?

yt-dlp'nin desteklediği her siteden: YouTube, YouTube Music, Vimeo, Dailymotion, SoundCloud, Twitter/X, Instagram, TikTok, Facebook, Twitch, Bandcamp, Reddit ve daha fazlası. Tam liste: [supportedsites.md](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

### İndirmek yasal mı?

Bu, içeriğe ve bulunduğunuz ülkenin yasalarına bağlıdır. Kendi videolarınızı, kamu malı veya Creative Commons lisanslı içerikleri ve sahibinin izin verdiği içerikleri indirmek genellikle sorun değildir. Telif hakkıyla korunan içerikleri izinsiz indirmek/dağıtmak yasalara ve platformların kullanım koşullarına aykırı olabilir. Sorumluluk kullanıcıya aittir.

### Mac veya Linux'ta çalışır mı?

Hazır exe yalnızca Windows içindir. Kaynak kod Python/Tkinter ile yazıldığı için büyük ölçüde taşınabilirdir; ancak otomatik kurulum, uyku engelleme gibi bazı özellikler Windows'a özgüdür ve diğer sistemlerde test edilmemiştir.

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
- En güvenli yol: exe'yi kaynak koddan [kendiniz derleyin](TEKNIK.md#kaynaktan-derleme) ya da doğrudan `python indirici.pyw` ile çalıştırın.

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

Varsayılan olarak `C:\Users\<kullanıcı adınız>\Downloads\Video Muzik Indirici` klasöründe. Hızlı ulaşmak için **Klasörü aç** düğmesine basın veya biten satıra çift tıklayın. Oynatma listeleri bu klasörün içinde, liste adını taşıyan alt klasörlere iner.

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
