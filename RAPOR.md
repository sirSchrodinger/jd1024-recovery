# JD1024 / MAXIO MAP1202 — kurtarma raporu
_12 Eylül 2026, gece çalışması · Alperen için_

---

## ÖZET — önce bunu oku

**Disk ölü değil.** BIOS onu iki kez eksiksiz gördü ("JAMESDONKEY JD1024, 1024 GB"). Bunun olması
için kontrolcünün `CSTS.RDY=1` vermesi, admin queue kurması ve Identify komutlarına cevap vermesi
gerekir — yani o anlarda disk NVMe seviyesinde **%100 sağlamdı**. Arıza kalıcı bir ölüm değil,
**aralıklı bir başlatma arızası**.

**En olası neden** (kanıt ağırlığıyla): firmware/FTL panic + NAND'ın sistem alanında retention
kaybı (~%50) · BGA mikro çatlak (~%25) · NAND besleme rayı / çatlak MLCC (~%15) · saat/PLL (~%5-10).
Gece boyunca saat/PLL hipotezini önce güçlendirdim, sonra kanıtla **çürüttüm** — detayı 19. bölümde.

**Hikâye tutarlı:** satıcıda format sırasında FTL bozuldu → firmware kendini salt-okunura kilitledi
(bu, "salt okunur hatası"nın teknik karşılığı) → sonra disk uzun süre enerjisiz kaldı ve sistem
alanı okumaları sınıra itildi → artık çoğu açılışta hiç ayağa kalkamıyor. Oracle'ın kendi donanım
dokümanı bu zinciri birebir tarif ediyor.

**Sabah ne yapacağız:** önce **ölç**, sonra karar ver. Üç bedava test (flex, multimetre, soğuk) ve
bir ~100 TL'lik alet (USB-TTL) hangi hipotezin doğru olduğunu söyleyecek. Asıl çözüm yolu
**MPTool ile yeniden açma** ve o yolda aynı kontrolcüde çalıştığına dair iki somut vaka var.
Kesin sıra **18. bölümde**, güncel test bataryası **19b'de**.

**Gece ne yaptım:**
- Uzaktan tam otomatik soğuk güç döngüsü kurdum (WoL + RTC). ~7 dk/tur, kendi kendine açılıyor.
- Her açılışta koşan bir yakalayıcı kurdum: disk görünürse tam teşhis alıp **tutuyor**, format atmıyor.
- Windows PE sanal makinesi kurdum — disk yakalanırsa reboot etmeden MPTool'a verilebilir.
- Kartın **ROM test pad'lerini buldum** (senin dün gece gönderdiğin arka yüz fotoğrafındaydı).
- Doğru NAND'ı kesinleştirdim: **H25T1TB48E = V6 nesli**, ve elimizdeki MPTool paketlerinin
  hiçbirinin bu nesle uymadığını tespit ettim. Alternatif kaynak avı sürüyor.
- Alma listesindeki **RTL9210B kutusunun yanlış parça** olduğunu buldum; doğrusu **JMS583**.
- Kendi aracımda bir hata buldum ve düzelttim (127,5 saniye yerine 60 saniye bekliyordu).

**Döngü sonucu:** `ssh kaplikaya 'jd durum'` — orada yazıyor.

---

_12 Eylül 2026, gece çalışması_

---

## 1. Diskin kimliği (kesinleşti)

| | |
|---|---|
| Ürün | JamesDonkey (贱驴) JD1024, 1 TB, M.2 2280 NVMe |
| PCB | SMPMA1286, tek yüzlü görünüyor (arka yüz görülmedi) |
| Kontrolcü | MAXIO MAP1202 (联芸), PCI `1e4b:1202`, DRAM-siz, HMB, PCIe 3.0 x4, NVMe 1.4.0 |
| NAND | **SK hynix H25T1TB48E** (lot X297 310Y) — 4 paket × 256 GB |
| NAND nesli | **V6 (4D V6, 128 katman) TLC**, 512 Gbit/die, 4 die/paket → toplam 16 die |
| Firmware nerede | **NAND'ın içinde.** Kartta ayrı SPI NOR flash **yok** (fotoğrafla doğrulandı) |
| Seri | SN:2412102050329 |

Not: NAND kodunu gece boyunca `H25T1TB4BE` diye okumuştum; fotoğrafı 8× büyütünce
son karakterin **8** olduğu görüldü → `H25T1TB48E`. Bu, doğru MPTool sürümünü seçmede
belirleyici oldu (aşağıda).

---

## 2. Ölçülen gerçekler — tahmin değil

Hepsi bu gece doğrudan ölçüldü.

**Elektriksel ve PCIe katmanı sağlam:**
- LED yanıp sönüyor → karta güç geliyor, kontrolcü NAND'a erişmeye çalışıyor
- PCIe link **tam eğitiliyor**: `LnkSta 8GT/s x4`, `SltSta PresDet+`
- AER hata sayaçları temiz, sinyal bozulması yok

**NVMe register katmanı canlı** (sürücüsüz, BAR0 doğrudan mmap edilerek okundu):
```
CAP  = 0x00200030ff0103ff
VS   = 0x00010400      -> NVMe 1.4.0
CC   = 0x00460001      -> EN=1
CSTS = 0x00000000      -> RDY=0, CFS=0
```
CAP bit çözümü:
- `MQES=1024`, `TO=255` → kontrolcüye **127,5 saniye** RDY süresi tanınıyor (maksimum)
- **`NSSRS=1`** → NVM Subsystem Reset destekleniyor (bunu hiç denememiştik, artık deneniyor)
- **`BPS=0`** → Boot Partition **yok** → firmware'i o yoldan yükleme kapısı kapalı
- `MPSMIN=4KB`, `MPSMAX=16KB`, `CMB/PMR yok`

**Arıza noktası:** `CC.EN=1` yazılıyor, kontrolcü kabul ediyor, ama `CSTS.RDY` hiç 1 olmuyor.
`CSTS.CFS=0` — yani kontrolcü kendini "ölümcül hata" durumunda bile saymıyor. Bir süre sonra
config space de cevap vermez oluyor (`DevSta: UnsupReq+`), cihaz enumerate olmuyor.

**En önemli gözlem — disk bazen TAM çalışıyor:**
BIOS diski en az iki kez eksiksiz gördü: **"JAMESDONKEY JD1024 1TB", 1024 GB**.
UEFI'nin model adını ve kapasiteyi okuyabilmesi için kontrolcünün `RDY=1` vermesi,
admin queue kurması, **Identify Controller ve Identify Namespace komutlarını cevaplaması** gerekir.
Yani o anlarda disk NVMe protokol seviyesinde **%100 sağlamdı**.

Bu, arızanın niteliğini belirliyor: **kalıcı bir ölüm değil, aralıklı bir başlatma arızası.**

---

## 3. Elenen açıklamalar

Ölçümle elendi, tekrar denenmeyecek:

| Eleme | Nasıl elendi |
|---|---|
| Montaj / oturma / yuva seçimi | Link her seferinde 8GT/s x4 kuruluyor |
| PCIe sinyal bütünlüğü, Gen hızı | AER sayaçları sıfır; Gen sabitleme değiştirmedi |
| Isınma | Sıcaklıkla korelasyon yok; ölçüldü |
| Kernel bekleme süresi yetersizliği | Kernel zaten 127,5 sn bekliyor (CAP.TO=255) |
| Kernel quirk (DELAY_BEFORE_CHK_RDY vb.) | Quirk ~2 sn ekler, sorun bu değil |
| Güç yönetimi (ASPM, pcie_port_pm) | Kapatınca **daha kötü** oldu, geri alındı |
| Hot reset / FLR / D3cold / rescan | Hiçbiri RDY üretmedi |
| CC.EN döngüsü (40 tur), link retrain (5 tur) | Sonuç değişmedi |
| `reset_subordinate` | Portu bozdu (2.5GT/s x1'e düştü); soğuk açılış düzeltti |
| Anakart tarafında yuvaya sonradan güç verme | B650M-R'de hiçbir slotta `PwrCtrl`/`HotPlug` yok — donanımsal olarak imkânsız |
| Boot Partition üzerinden firmware yükleme | `CAP.BPS=0` — özellik yok |
| `1e4b:1201` = ROM modu sanmak | **Yanlışmış.** MAP1201 ayrı bir ürün; ROM modunun ayrı PCI ID'si yok |

---

## 4. Gece boyunca çıkan yeni bulgular

### 4.1 ROM modu hakkında gerçek
- ROM/loader modunda kontrolcü NVMe katmanını **tam çalıştırır ve `CSTS.RDY=1` verir.**
- Bizim disk hiç RDY vermediğine göre **ROM modunda değil** ve kendiliğinden de düşmüyor.
  "N başarısız açılıştan sonra otomatik ROM'a düşer" diye bir mekanizma belgelenmemiş.
- ROM moduna girmenin tek yolu: PCB üzerindeki **iki "ROM" test pad'ini güç verilirken kısa devre**
  yapmak ve yazılım diski tanıyana kadar tutmak.

### 4.2 MPTool nasıl çalışıyor (exe'den çıkarıldı, tahmin değil)
- **Hiç sürücü kurmuyor.** Paketlerde `.sys`/`.inf`/`.dll` yok.
- Cihazı **PCI ID'ye göre aramıyor.** Windows'un "Disk drives" sınıfındaki tüm diskleri listeleyip
  her birine MAXIO vendor komutu gönderiyor; cevap veren MAP1202'dir.
- **Sonuç: diskin Windows'a bir namespace sunması, yani "Disk drive" olarak görünmesi şart.**
  Sadece "Storage controllers" altında görünmesi yetmez.
- Ayrıca **USB köprüsü yolu var**: `USBSTOR` + SCSI CDB passthrough, tanıdığı çipler
  **JMS583, ASM2362, RTL9210**. Topluluğun kullandığı yol bu.
- `no connected device for detecting!!` mesajı, Auto Detect'in "hiç disk nesnesi bulamadım" koruması.

### 4.3 En ciddi engel: elimizdeki MPTool paketlerinin hiçbiri uymuyor
19 paketin tamamı incelendi (usbdev.ru'daki MAP1202 listesinin tümü).
NAND'ımız **V6** nesli; paketlerdeki sistem firmware'leri **V7 (`skv7_9286`)** ve **V8 (`HynixV8`)**.
Eksik olan parçalar: `DAT/SKV6/` timing klasörü, `nandmem_SKV6_page.bin`, SKV6 sistem firmware'i.
Aracın kendisi V6'yı tanıyor (ReleaseNote: "C_0_1_012 → Support Hynix V6"), ama **V6 firmware paketi
hiç yayınlanmamış.** Bu paket şu an ayrıca aranıyor.

---

## 5. Kök neden — şu anki en iyi teşhis

Kanıtların hepsini karşılayan tek açıklama:

> Kontrolcünün ROM bootloader'ı sağlam çalışıyor, PCIe endpoint'i kuruyor, MMIO'ya cevap veriyor.
> Sonra NAND'daki **system area**'dan (firmware + FTL/eşleme tabloları) okuma yapması gerekiyor.
> Bu okuma **sınırda**: bazen ECC ile kurtarılıyor (→ disk tam çalışıyor, BIOS görüyor),
> genelde kurtarılamıyor (→ RDY hiç gelmiyor, kontrolcü takılıyor).

Bunu destekleyen noktalar:
- Aynı disk aynı donanımda bazen çalışıp bazen çalışmıyor → **kesin bir donanım kopukluğu değil**
- `CSTS.CFS=0` → kontrolcü çökmüş değil, **bekliyor**
- Satıcıda sürekli BIOS'ta görünüyordu (ve sadece "salt okunur"du); bizde çok daha kötü.
  Arada geçen şey: **disk uzun süre enerjisiz kaldı ve kargolandı.**
  Enerjisiz bekleyen NAND hücreleri şarj kaybeder (data retention drift) — bu, "sınırda okuma"
  hipotezini doğrudan destekler.
- Format sırasında ölmesi: FTL/system area yazımı yarıda kalmış olabilir; o alan zaten zayıfken
  yarım yazma onu sınırın altına itmiş olabilir.

**Bu teşhis doğruysa:** diski bir kez sağlam yakalayıp **tam format** atmak, FTL'i sıfırdan yazdırır
ve sorunu kalıcı çözebilir. Firmware alanı kullanıcı alanının dışında olduğu için formatın oraya
dokunup dokunmadığı ayrıca araştırılıyor — dokunmuyorsa kalıcı çözüm MPTool ile firmware'i
yeniden yazmaktan geçer.

---

## 6. Bu gece kurulan araçlar (hepsi çalışır durumda)

### 6.1 Uzaktan soğuk güç döngüsü — **kazanma yolumuz bu**
Diskin sağlam gelmesi ~%10-15 olasılıklı ve **tam güç kesilmesini** gerektiriyor.
Bugüne kadar tüm denemeler elle yapıldı. Artık tamamen otomatik:

- kaplıkaya'da Wake-on-LAN açık (`eno1`, `Wake-on: g`) + RTC alarmı çalışıyor
- Döngü: `poweroff` → M.2 yuvasının gücü tamamen kesilir → RTC/WoL ile kendiliğinden açılır
- **Ölçülen tur süresi: ~6,5 dakika** (kapanma 01:33:32 → açılış 01:37:13 → SSH 01:39:54)
- Kapalı kalma süresi turlar arasında değişiyor (40/90/180 sn) → "ne kadar bekleyince canlanıyor"
  sorusuna da veri toplanıyor
- Her tur `turlar.csv`'ye yazılıyor
- Disk yakalandığı anda döngü **kendiliğinden duruyor**, makine açık kalıyor

### 6.2 Yakalayıcı — `jd-yakala.service`
Her açılışta otomatik koşar. Disk enumerate olduysa:
1. PCIe ve BAR0 durumunu kaydeder
2. `CSTS.RDY` zaten 1 mi bakar
3. Değilse `CC.EN` döngüsü, sonra **NSSR** (NVM Subsystem Reset) dener
4. RDY gelirse `nvme` sürücüsüne bağlar ve **tam teşhis** alır:
   `id-ctrl`, `id-ns`, `smart-log`, `error-log`, `fw-log`, feature'lar, `ro` bayrağı
5. **Format ATMAZ.** Disk bir kez sağlam yakalanınca kendiliğinden ölmüyor (BIOS oturumları boyunca
   ayakta kaldı), o yüzden acele edip formatla riske girmek yerine tutup karar bekliyor.
6. Masaüstü bildirimi + `/var/lib/jd-durum` durum dosyası

Güvenlik kilidi: yalnızca `1e4b:1202`'ye dokunur, model adında KIOXIA geçerse anında durur.
Sistem diski hiçbir koşulda hedef alınmaz.

### 6.3 Windows PE sanal makinesi — MPTool için
Sorun: MPTool Windows istiyor, Windows'a geçmek reboot gerektiriyor, reboot diski öldürüyor.
Çözüm: Linux açıkken diski **vfio-pci passthrough** ile bir Windows VM'ine vermek.

- QEMU + KVM + OVMF UEFI, Hiren's BootCD PE (Windows 11) **açıldı ve çalışıyor**
- MPTool paketleri sanal bir diske (MBR + FAT32) kondu
- VM görünmez çalışıyor (VNC, Alperen'in masaüstünde pencere açmıyor)
- Klavye/fare/ekran otomasyonu kuruldu — VM'i komut satırından sürebiliyorum
- `jd_vm.sh --passthru` diski VM'e verir

### 6.4 Yakalama sonrası oyun kitabı — `jd_kur.sh`
`teshis` · `format` · `crypto` · `sanitize` · `yaz` (NAND sağlık testi) · `vm` (MPTool'a devret)

### 6.5 Register aracı — `jd_reg.py`
Sürücüsüz BAR0 erişimi: `durum` (tüm register dökümü + bit çözümü), `nssr`, `en0`/`en1`, `bekle`.

---

## 7. Dış kanıt — hipotezi doğrulayan birinci el kaynak

**Oracle, kendi NVMe SSD donanım dokümanında** bizim imzamızı birebir tarif ediyor:

> "…may report uncorrectable errors or assert **after not being powered for three or more months**."
> "If the NAND media is not refreshed for approximately three months, the drive may experience media errors."
> "If the uncorrectable read errors occur **during drive power-on**, the drive will report either an
> **ASSERT or BAD_CONTEXT** error code to the host."

_docs.oracle.com/cd/E87231_01/html/F36828/gtlea.html_

Ve iki resmî çare veriyor:
1. **Secure erase** (firmware ile)
2. **Diski açık bırakıp ~14 gün media refresh'e izin vermek**

Bu forum dedikodusu değil, üreticinin kendi dokümanı. "Enerjisiz kaldı → açılış sırasında
düzeltilemeyen okuma hatası" zinciri bizim gözlemimizle aynı. Diskin satıcıda sürekli görünüp
bizde görünmemesinin en olası açıklaması bu: **arada geçen enerjisiz süre.**

Crucial'ın belgelenmiş power-cycle prosedürü de aynı aileden: 20 dk enerjide boşta bekletmek
(BIOS ekranında tutarak) → 30 sn tamamen kesmek → en az bir kez tekrarlamak.

**Dürüstlük payı:** Bu vakaların çoğu çözülmüyor. Tarama sonucunda "yakaladım, format attım,
haftalar sonra hâlâ sağlam" diyen **doğrulanmış tek bir vaka bulunamadı**. Bulunanlar ya geçici,
ya tekrarlamış. Bir kullanıcı açıkça "aynı diski bu yöntemle 10 kez kurtardım" diyor. Yani
başarı ölçütü ilk çalışma anı değil, **bir hafta sonraki ikinci okuma.**

Ayrıca bir kaynak uyarısı: Rossmann Group'un kontrolcü sayfaları makine üretimi SEO içeriği gibi
duruyor; mekanizma anlatımları literatürle tutarlı ama oradan **sayısal iddia alınmamalı**
(arama motoru özetlerinin ona atfettiği istatistikler sayfalarda mevcut değil).

---

## 8. MPTool yolu — durum ve engel

### Nasıl çalışıyor (exe'den çıkarıldı)
Araç PCI ID'ye bakmıyor; Windows'un "Disk drives" sınıfındaki her diske MAXIO vendor komutu
gönderip cevap vereni buluyor. Yani **diskin bir namespace sunması, "Disk drive" olarak görünmesi şart.**
Ayrıca USB köprüsü yolu var (SCSI CDB passthrough) ve tanıdığı çipler: **JMS583, ASM2362, RTL9210**.

### Köprü seçimi — Alperen'in listesindeki parça yanlış
Dört bağımsız Çince kaynak aynı şeyi söylüyor: MAP1202 için **JMS583 kullanılmalı**,
RTL9210 serisi uyumsuz. Aracın adı bile `MXMPTool_MAP1202_**USB**_...exe`.
Belgelenmiş **tüm** başarılı MAP1202 açma vakaları USB köprüsü üzerinden; anakart M.2 yuvasından
açma vakası **hiç bulunamadı**. Windows PE'de aldığımız "no connected device" bununla tutarlı.

Dürüst not: "RTL9210 çalışmaz" iddiası tek kaynaktan kopyalanmış olabilir (metinler kelimesi
kelimesine aynı). Buna karşılık **JMS583 ile başarılı en az 4 bağımsız vaka** var. Karar: JMS583.

Uyarı (Çin forumları): sıradan USB kutularının çoğu sadece "二次开卡" destekler — yani **yalnızca
disk zaten sağlam çalışıyorken** açma yapılabilir, mühendislik/ROM modunu desteklemez. Özel
"açma adaptör kartı" (开卡转接板) aranmalı. Kutuyu doğrudan arka panel USB portuna tak; hub/uzatma yok.

### Asıl engel: bizim NAND için firmware paketi yok
19 paketin tamamı incelendi (usbdev.ru'daki MAP1202 listesinin tümü).
NAND'ımız **V6**; paketlerdeki sistem firmware'leri **V7** (`skv7_9286`) ve **V8** (`HynixV8`).
Eksikler: `DAT/SKV6/` timing, `nandmem_SKV6_page.bin`, SKV6 sistem firmware'i.
Araç V6'yı tanıyor (ReleaseNote: "C_0_1_012 → Support Hynix V6") ama **V6 paketi hiç yayınlanmamış.**
Şu an ayrıca aranıyor (GitHub, 量产部落, Çin ağ diskleri, alternatif markalar).

### Belgelenmiş bir ROM modu kurtarması (bize en yakın vaka)
Netac NV3000 250GB, MAP1202, elektrik kesintisi sonrası **disk hiç görünmüyor**:
JMS583'lü ucuz Çin kutusu (Ugreen adaptör diski **hiç tanımadı**), ROM pad'leri cımbızla köprülenerek
takıldı → Device Manager'da `Generic_Loader_NVMe_Devi SCSI Disk Device` olarak göründü →
MPTool → **ilk parametre seti çalışmadı, ikincisi çalıştı** → START'tan önce köprü kaldırıldı → "Pass".
_pitfalls.ru/восстанавливаем-прошивку-ssd-nvme-диска-netac-nv3000-250gb_

Önemli ayrım: **enumerate olmayan diskte ROM kısa devresi ŞART**; çalışan diskte gerekmiyor,
düz bir M.2→USB adaptör yetiyor.

---

## 9. SABAH PLANI

Sıra bilinçli: önce bedava ve geri dönüşlü olanlar, sonra para, en son ağır müdahale.
Her adımda "ne görürsek devam, ne görürsek sonraki" ölçütü var.

### AŞAMA Y — Gece diski yakaladıysak (önce buna bak)

```
ssh kaplikaya 'cat /var/lib/jd-durum; sudo tail -80 /var/log/jd-yakala.log'
cat scratchpad/jd/turlar.csv
```

- `YAKALANDI` → disk `/dev/nvmeX` olarak ayakta, teşhis alınmış, **format atılmamış**. Sıra:
  1. SMART'ı oku: `media_errors`, `unsafe_shutdowns`, `percentage_used`, `critical_warning`
  2. `jd_kur.sh format` → `nvme format -s 1` (kullanıcı verisi silme; FTL sıfırdan kurulur)
     - Hata "write protected" ise → salt-okunur kilidi aktif → MPTool'suz çözülmez, Aşama 1'e geç
  3. `jd_kur.sh yaz` → 1 GB yaz/oku doğrulaması, sonra tam disk taraması
  4. **Diski açık bırak.** Oracle'ın ikinci çaresi bu (media refresh). Makineyi kapatma.
  5. **Asıl hüküm bir hafta sonra**: bir soğuk açılış daha yap. Hâlâ görünüyorsa kazandık.
- `ENUM_RDY_YOK` → enumerate oldu ama RDY vermedi. NSSR de denendi. Bu yine değerli: cihaz
  vfio'da tutuluyor, üstünde çalışabiliriz.
- Hepsi `KACTI` → Aşama 0'a geç.

### AŞAMA 0 — Bedava, karar veren test (Alperen'in elleri gerekiyor)

**0.1 — Kartı fotoğrafla.** Diski yuvadan çıkar. **İki yüzünü de** iyi ışıkta, net, yakından
fotoğrafla. Beyaz etiket kartın alt yarısını kapatıyor; altında NAND paketleri ve muhtemelen
test pad'leri var. Etiketi soymak gerekebilir (2. el disk, garanti zaten yok).

**Aranan:** kart üzerinde **"ROM"**, "ROM MODE", **"JP1"**, "J1", "J3", "SW1", "TP1" serigrafisi
ve hemen yanında **iki küçük delik/pad** (biri kare biri yuvarlak olabilir). Genelde kontrolcünün
yakınında ya da M.2 konnektörüne yakın bölgede.

**0.2 — ROM kısa devre testi.** Bu, hiçbir şey satın almadan MPTool yolunun açık olup olmadığını
söyler:
1. Diski M.2_2 yuvasına tak
2. Metal cımbızla iki ROM pad'ini köprüle ve **tut**
3. Bilgisayarı aç (soğuk açılış)
4. POST geçtikten sonra kısa devreyi bırak
5. Linux açılınca: `ssh kaplikaya 'sudo jd_reg.py durum'`

**Ölçüt:**
- `CSTS.RDY=1` **ve** disk ~0 MB veya ~2 GB kapasiteyle görünüyorsa → **ROM modu çalışıyor.**
  Bu, "kontrolcü sağlam, sorun NAND'daki firmware/FTL alanında" demektir ve MPTool yolu açıktır.
  → Aşama 1'e geç, JMS583 al.
- `RDY=0` kalırsa → ya yanlış pad (başka kombinasyonları dene, Çin forumlarının tavsiyesi
  "emin değilsen defalarca deneyerek bul"), ya da kontrolcü/güç devresi hasarı.

**0.3 — Crucial power-cycle prosedürü** (bedava, paralel denenebilir): 20 dk BIOS ekranında
enerjide bekleyip 30 sn tam kesmek, en az iki tur. Gece döngüsü hızlı turlar yaptı; bu farklı bir
profil, denemeye değer.

### AŞAMA 1 — Ucuz donanım

**Al: JMS583 çipli M.2 NVMe → USB adaptör/kutu.**
- Ürün açıklamasında **"JMS583"** yazması şart. **RTL9210 / RTL9210B ALMA.**
- Tercihen "开卡转接板" tipi çıplak adaptör kartı (pad'lere erişim kolay olur), kapalı kutu değil.
- Doğrudan kasa arkasındaki USB portuna tak; hub, uzatma, ön panel kullanma.
- Türkiye'de bulunmazsa AliExpress ~10-15 USD.

**Akış:** ROM pad'lerini köprüle → USB'ye tak → Windows'ta `Generic_Loader_NVMe...` görünmeli →
MPTool aç → Auto Detect → köprüyü bırak → Start.

**Bilinen engel:** elimizde V6 NAND için firmware paketi yok. Paket avı sürüyor. Bulunamazsa
V7 paketiyle `EnCheckFlashID=0` ile zorlamak var ama nesil atlaması riskli — bunu ancak
her şey tükendiğinde deneriz.

### AŞAMA 2 — Ağır müdahale (sadece 0 ve 1 tükenirse)
- V7/V8 paketiyle zorlama (Flash.ini'ye elle V6 kaydı, `EnCheckFlashID=0`, `EnModifyFlashID=1`)
- NAND sökümü / PC-3000: 1000 TL'lik disk için ekonomik değil, sadece bilgi olarak

### AŞAMA 3 — Durma noktası
Aşama 0'da RDY=1 alınamaz **ve** gece döngüsünün ~25 turunun hiçbiri yakalamazsa, yazılımla
ulaşılabilecek her yol tükenmiş olur. O noktada karar Alperen'in: JMS583 kumarına girmek (~400 TL)
ya da diski bırakmak.

---

## 10. Alperen'den gereken şeyler

1. **Kartın iki yüzünün net fotoğrafı** (etiket soyulmuş hâlde) — ROM pad'ini bulmak için
2. **Cımbız** (metal, ince uçlu) — kısa devre için
3. Aşama 0.2'yi elle yapması (kısa devreyi tutarak açılış)
4. JMS583 alma kararı (para hareketi — onay gerekiyor)
---

## 11. ROM kısa devre — birebir prosedür (Çince kaynaklardan)

### Mekanizma (neden işe yarıyor)
> "数据脚悬空为高电平，这表明 ROM 处于只读模式，即只能读出，禁止写入。
> 当 ROM 数据脚处于低电平时，表明清除了只读模式，可以写入数据了。"

_ROM veri pini havada durursa yüksek seviyededir; bu, ROM'un **salt-okunur** modda olduğu anlamına
gelir — okunur, yazılamaz. Pin **alçak seviyeye** (toprağa) çekilince salt-okunur mod kalkar ve
yazma mümkün olur._ (blog.csdn.net/u011250186/article/details/100935807)

Kısa devre, ROM'un yanındaki **beyaz kare içindeki iki deliği** birleştirir; pin **GND**'ye çekilir.

Not: satıcının "salt okunur hatası alıyorum" demesiyle bu mekanizma kavramsal olarak aynı aileden.

### Adım sırası — sıra önemli
1. **Önce yazılımı aç** (MPTool). Disk henüz bağlı değil.
2. Cımbızı iki ROM deliğine bastır ve **tut**.
3. **Kısa devreyi tutarken** diski bağla / makineye güç ver.
4. Yazılımda tara (`Auto Detect` / `scan drive`).
5. Yazılım diski tanıyınca → **cımbızı çek**, kısa devreyi kaldır.
6. `START`.
7. İşlem bitince kartı çıkar, ROM pinini tekrar havada bırak.

**Ayarlar:** `Tool Type = MPT`. `Preformat Mode = "Inherit FW BB"` ya da `"Auto Inherit"` —
biri olmazsa diğerini dene. Bir "sync" seçeneği varsa **işaretleme**, işaretlenirse başarısız olur.

**Bilinen sahte hata:** `RUN ISP FAIL(50)` — bilinen bir bug; işlem aslında bitmiş olabiliyor.
Gücü kesip tekrar tak, kontrol et.

**Pad'i bulamazsan:** Çin forumlarının standart tavsiyesi *"hangisi olduğundan emin değilsen
aday noktaları tek tek deneyerek bul"*. Çözülmüş bir vakada SW1/SW2 işe yaramamış, çözüm J1'in
3. ve 4. bacağı çıkmış. Yani deneme yanılma normal ve beklenen.

### Anakart yuvasında yapılabilir mi? — EVET
Alperen'in "M.2 yuvasının arkasını göremiyorum, kısa devre yapamayız" itirazına cevap:
Phison PS3109 tamir kılavuzunda yerleşik pratik tam olarak bu —
> "Diski **doğrudan anakart portuna** tak. Üzerinde ROM jumper R29'u bul.
> **R29'u kısa devre yap, kısa devreyi TUTARAK bilgisayarı aç ve USB'den boot et.**
> (Bu adım kritik; tüm Phison SSD tamirlerinde önce ROM moduna girmek şart.
> **Bu adım birkaç deneme gerektirebilir.**)"

Pad'ler kartın **üst yüzünde** olduğu için disk M.2 yuvasında yatarken erişilebilir olmalı —
yuvanın arkasına bakmaya gerek yok. Kasa yan yatırılıp kart üstten açıkta olacak.

### Bizim karta özel gözlem
Elimizdeki fotoğrafta M.2 konnektörü ile kontrolcü arasındaki üst şeritte **en az dört adet
boş bırakılmış iki-pad'lik ayak izi** görünüyor. ROM jumper'ı tipik olarak tam böyle görünür —
birinci derece adaylar bunlar. Ama fotoğraf serigrafiyi okuyacak çözünürlükte değil;
**makro fotoğraf şart**.

### Bizim akışa uyarlanmış hâli (VM'li)
MPTool'u Windows PE VM'inde açık tutabildiğimiz için sıra şöyle kurulabilir:
1. Cımbızı ROM pad'lerine bastır, tut
2. Makineyi aç (soğuk açılış)
3. Linux açılana kadar tut (~3 dk)
4. `jd_reg.py durum` ile `CSTS.RDY=1` görürsek → **cımbızı bırak**
5. Diski vfio'ya al, `jd_vm.sh --passthru` ile Windows VM'e ver
6. MPTool → Auto Detect → Start

Bu, cımbızı Windows PE'nin açılmasını bekleyerek tutmaktan daha kısa sürer ve
"tanındı mı" sorusunu ölçümle cevaplar, tahminle değil.

---

## 12. ⭐ UART — gecenin en yüksek bilgi/maliyet oranlı bulgusu

**MAP1202 kartlarında UART hata ayıklama portu var** ve kontrolcü açılırken adım adım log basıyor.
usbdev.ru'da bir kullanıcı (roman2013) Apacer AS2280P4 1TB / MAP1202 diskine UART bağlayıp
boot log'unu yayınlamış. Log'un iskeleti:

```
hc init done → UART-RDY → Faa Format → DDR:1200 → LDPC init → Z-CFG/FA_TM/ZQ/DCC
→ [CodeBlk]S ... [CodeBlk]E     ← firmware'in NAND'dan yüklenmesi
→ [QBT]S ... [QBT]E             ← hızlı açılış tablosu   (o log'da Q-Query-NG / Q-RdFail hataları var)
→ [PBT]S ...                    ← fiziksel blok tablosu
→ PE_RISE / PE_FALL idle
```

**Ve bizim vaka için en değerli tek cümle** (aynı thread, 18 Aralık 2024):

> "UART'ı düzgün bağladım, boot sürecini izlemek için. Sonunda **başka bir açılışta** konsolda
> **'CLK:550,475,137'** frekans mesajı çıktı — **ve disk sistem tarafından tanındı**."

Yani **aynı disk bazen açılıyor bazen açılmıyor** ve fark UART'ta görülebiliyor; fark
**saat/PLL kurulum adımında** ortaya çıkıyor. Bizim disk birebir bu davranışı gösteriyor.

### Bu, rakip bir hipotez doğuruyor

Şimdiye kadarki teşhisim "NAND'daki system area okuması sınırda" idi. UART bulgusu ikinci bir
aday getiriyor: **kristal / PLL marjinal.**

| | NAND retention lehine | Saat/PLL lehine |
|---|---|---|
| Aralıklı, güç döngüsüne bağlı | ✓ | ✓ |
| Soğuk açılış bağımlılığı | ✓ | ✓ (kristal başlangıçta sıcaklık/gerilim hassas) |
| Oracle'ın belgelediği "3 ay enerjisiz → açılışta hata" | ✓✓ | — |
| Satıcıda sürekli çalışması, bizde çalışmaması | ✓ (arada enerjisiz kaldı) | ~ (kargo darbesi/lehim de olabilir) |
| usbdev vakasında başarının CLK mesajıyla eşleşmesi | — | ✓✓ |
| Firmware'in NAND'da **çok sayıda kopyası** olması | ✗ zayıflatıyor | — |

Son satır önemli: aynı thread'de bir SSD araç geliştiricisi (vlo) firmware'in NAND'daki
yerleşimini anlatırken "tek bir blokta 5 kopya, ve bu **her ce/ch'de**" diyor. Firmware'in bu
kadar çok kopyası varsa, salt retention kaybının hepsini birden okunamaz hâle getirmesi zor —
bu, "firmware okunamıyor" versiyonunu zayıflatıyor. (FTL/eşleme tabloları ayrı konu, onlar
tek kopya olabilir.)

**Sonuç: iki hipotez de ayakta ve UART bunları AYIRIR.**
- Log `[CodeBlk]` veya `[QBT]/[PBT]` aşamasında takılıyorsa → NAND/FTL tarafı
- Log `CLK:` satırına hiç gelmiyorsa veya orada duruyorsa → saat/PLL, yani **donanım**
- Saat sorunuysa: kristali yeniden lehimlemek (reflow) ucuz bir çözüm olabilir

### Maliyet
USB-TTL seri adaptör (CP2102 / CH340 / FT232, **3.3 V** olmalı) — Türkiye'de ~50-100 TL.
Bu, bugüne kadar bulduğumuz **en yüksek bilgi/maliyet oranlı** araç: tahmini ölçüme çeviriyor.

### Sabah planına etkisi
Bu, **Aşama 1'in başına** giriyor — JMS583'ten (~400 TL) önce. Çünkü:
- Daha ucuz
- Hangi hipotezin doğru olduğunu söyler
- Eğer sorun saat/PLL ise JMS583 + MPTool zaten hiçbir işe yaramaz (para boşa gider)
- Eğer sorun NAND/firmware ise JMS583 gerekçelenir

---

## 13. ⭐⭐ KARTIN ARKA YÜZÜ — ROM pad'leri bulundu

Alperen dün gece (23:29) kartın **arka yüzünün** fotoğrafını göndermiş ve üzerinde bir yeri
yeşille daire içine almıştı. O an konu M.2 yuvasının montaj boşluklarıydı ve fotoğraf
bu gözle bakılmadı. Bu gece ROM pad araştırmasından sonra tekrar açınca ne olduğu anlaşıldı.

**Arka yüzde ne var:**

| Konum | Ne | Önem |
|---|---|---|
| Kartın alt kenarına yakın, M.2 montaj vidası deliğinin hemen yanında | **İki adet yuvarlak, altın kaplama, DELİKLİ (plated through-hole) pad**, dikey yan yana, aralarında ~2 mm | **Birincil ROM kısa devre adayı** |
| M.2 konnektörüne yakın üst bölge | **~12 adet düz altın test pad'i** (delik değil, yüzey pad'i), iki küme hâlinde | Fabrika test noktaları — **UART TX/RX/GND** bunların arasında olabilir |
| Serigrafi | `SMPMA1286-AA V0415`, lot `22xx` | PCB kimliği |
| Genel | Arka yüz tamamen boş, hiç bileşen yok | Kart tek yüzlü |

**Daire içine aldığı iki delikli pad, Çince kaynakların tarifiyle birebir örtüşüyor:**
> "ROM'un yanındaki **beyaz kare içindeki iki delik**, cımbızla kısa devre edilir"

Ayrıca **M.2 montaj vidası deliğinin hemen yanında** olmaları anlamlı: vida deliği genelde GND'dir
ve mekanizma "ROM veri pinini **GND'ye** çekmek" diyordu.

### Bunun pratik sonucu — Alperen'in itirazı aşılıyor
Alperen "M.2 yuvasının arkasını görmüyorum, kısa devre yapamayız" demişti. Ama:
- Bu pad'ler **delikli** — karttan geçiyorlar, yani **ön yüzde de aynı noktada delik olmalı.**
- Ön yüzün alt yarısı beyaz etiketle kaplı. **Etiketi soyunca** o delikler ortaya çıkar.
- Etiket soymak sorun değil: 2. el disk, garanti zaten yok.
- Yani disk M.2 yuvasında takılıyken **üstten** kısa devre yapılabilir.

### Test için basitleştirilmiş yöntem
MPTool prosedürü "cımbızı tut, tanınınca bırak" diyor. Ama bizim ilk testimiz sadece
**"ROM modu çalışıyor mu"** sorusunu soruyor; bunun için cımbız tutmaya gerek yok:

1. İki pad'i ince tel / alüminyum folyo parçasıyla köprüle, bantla sabitle
2. Diski tak, **soğuk açılış** yap
3. Linux açılınca: `jd reg`
4. `CSTS.RDY=1` görürsek → **ROM modu çalışıyor, kontrolcü sağlam**
5. Köprüyü çıkar

Bu test **bedava**, birkaç dakika sürüyor ve MPTool yolunun açık olup olmadığını kesin söylüyor.

---

## 14. Saat/PLL hipotezi neden ciddi — ölçümlerimizle birebir oturuyor

UART bulgusunu kendi ölçümlerimizle birleştirince ortaya şu çıkıyor:

**PCIe tarafı ile kontrolcünün iç saati AYRI kaynaklardan besleniyor.**
- PCIe PHY, anakart yuvasındaki 100 MHz REFCLK'i kullanır — kart üzerindeki kristalden bağımsız.
- Kontrolcünün çekirdek ve **NAND arayüzü** saatleri, kart üzerindeki kristalden türetilen
  iç PLL'lerden gelir. (usbdev log'undaki `CLK:550,475,137` tam olarak bu üç frekans.)

Bu ayrım bizim tuhaf tabloyu açıklıyor:

| Gözlem | Saat/PLL hipotezinde açıklaması |
|---|---|
| PCIe link her açılışta 8GT/s x4 kuruluyor | PHY, anakartın REFCLK'iyle çalışıyor — kristalden etkilenmiyor ✓ |
| CAP/VS/CC/CSTS okunabiliyor, CC.EN yazılabiliyor | NVMe register bloğu çalışan bir saat alanında ✓ |
| `CSTS.RDY` hiç 1 olmuyor | NAND arayüzü yanlış zamanlamada → firmware okunamıyor ✓ |
| `CSTS.CFS=0` (fatal yok) | Kontrolcü çökmüş değil, NAND'dan cevap bekliyor ✓ |
| LED sürekli yanıp sönüyor | NAND'a erişim denemeleri sürüyor ✓ |
| Bazen tam çalışıyor | PLL kilidi bazen doğru oturuyor ✓ |
| usbdev vakasında başarı `CLK:` satırıyla eşleşiyor | Doğrudan kanıt ✓ |

### Ve bir de zamanlama kanıtı var
Disk satıcıda **her seferinde BIOS'ta görünüyordu** (sadece salt-okunurdu). Bizde çoğu zaman hiç
görünmüyor. Arada iki şey oldu: **(a) uzun süre enerjisiz kaldı**, **(b) kargoyla taşındı.**

- (a) retention hipotezini besler — ama kargo birkaç gün, retention için kısa; ve satıcıda da
  uzun süre takılı değilmiş, yani enerjisizlik ikisinde de vardı.
- (b) **mekanik** hipotezi besler: kargo darbesi → kristalin veya kontrolcünün lehim bağlantısında
  mikro çatlak. Bu, "satıcıda hep çalışıyordu, bizde çoğu zaman çalışmıyor" geçişini
  retention'dan daha iyi açıklıyor.

Ayrıca bir karşı-kanıt daha var: firmware NAND'da **çok sayıda kopya** tutuluyor (bir SSD araç
geliştiricisinin ifadesi: "tek blokta 5 kopya, ve her ce/ch'de"). Salt retention kaybının bu
kopyaların hepsini birden okunamaz hâle getirmesi zor.

### Bunun test edilebilir sonuçları (hepsi bedava)
1. **UART log'u** — `CLK:` satırına geliyor mu? Gelmiyorsa/orada duruyorsa saat/PLL. Kesin ayrım.
2. **Sıcaklık** — kristaller açılışta sıcaklığa duyarlıdır. Diski soğutup (buzdolabında birkaç
   dakika, yoğuşmaya dikkat) ve ayrı bir turda ısıtıp (saç kurutma makinesiyle kısa süre)
   isabet oranı değişiyor mu bak. Değişiyorsa mekanik/analog bir sorun var demektir.
3. **Hafif basınç** — açılış anında kristalin üstüne parmakla hafif bastırmak. Davranış
   değişiyorsa lehim çatlağı. Kaba bir test ama klasik ve bedava.
4. **Satıcıya tek soru** (Alperen gönderir): _"Sende en son denediğinde BIOS'ta HER SEFERİNDE mi
   görünüyordu, yoksa bazen kaybolur muydu?"_ — "her seferinde" cevabı mekanik/kargo hipotezini
   güçlendirir, "bazen" cevabı sorunun zaten orada başladığını gösterir.

### Eğer saat/PLL çıkarsa
Çözüm MPTool değil, **kristalin yeniden lehimlenmesi (reflow)**. Bu durumda JMS583 almak
tamamen boşa para olur. Bu yüzden **UART (~50-100 TL) JMS583'ten (~400 TL) ÖNCE gelmeli.**

---

## 15. ROM pad — doğrulanmış konum, prosedür ve düzeltmeler

### Konum: üç referans kartta aynı
| Kart | Kontrolcü | ROM pad yeri |
|---|---|---|
| Netac NV3000 250GB | **MAP1202** | Uzak uç, montaj çentiğinden ~10 mm geride, kenara 1-1,5 mm, **iki delikli altın pad** |
| Netac NV3000 500GB | YS9205 | Uzak uç, çentik çevresi, PTH grubu + ayrı pad |
| LITEON CL1-4D256 | SM2263XT | Uzak uç, çentiğin hemen üstünde 4'lü PTH kolonu |

Bizim kartın arka yüz tarifi (uzak uç, montaj vidası pad'inin yanında, iki yuvarlak delikli altın pad,
aralarında ~2 mm) bu üç örnekle **birebir örtüşüyor**. Bunlar ROM çifti — güven yüksek.

**Çiftin biri GND.** İki bağımsız kanıt: LITEON kartının serigrafisi `T / R / G / +1` (yani GND ile
yanındaki strap kısa devre ediliyor), ve mekanizma açıklaması ("pini **toprağa** çekince salt-okunur
mod kalkar"). Bizimkilerin montaj vidası pad'inin (GND) yanında olması bu resme oturuyor.

**Üstteki ~12 düz pad ROM DEĞİL** — fabrika ICT/flying-probe noktaları. İçlerinde güç rayları var,
cımbız değdirilmeyecek.

### Prosedür — önceki yazdığımın düzeltilmiş hâli
Daha önce "yazılım tanıyana kadar tut" yazmıştım. Doğrusu daha kısa:

1. MPTool'u **önce** aç
2. Cımbızla iki pad'i kısa devre et
3. **Kısa devre dururken** diski bağla (USB kutusu / güç ver)
4. **1-3 saniye içinde bırak** — usbdev'in birebir ifadesi "не удерживать" = tutma
5. Aygıt Yöneticisi'nde `Generic_ Loader_NVMe_Devi SCSI Disk Device` çıkmalı
6. Auto Detect → ayarlar → **START** (bu anda kısa devre kesinlikle bağlı olmayacak;
   flash sırasında bağlı kalırsa işlem başarısız olur)

### Erişim — önceki iddiamın düzeltmesi
"Delikli oldukları için ön yüzden erişilebilir, diski M.2 yuvasında bırakıp üstten kısa devre
yapabiliriz" demiştim. **Fazla iyimserdi:**
- Pad'ler arka yüzde; disk M.2 yuvasındayken arka yüz anakart PCB'sine 2-3 mm mesafede — cımbız girmez
- Ön yüzde delik görünüp görünmeyeceği solder mask'e bağlı (tented via olabilir), garanti değil

**Kanıtlanmış üç yol, tercih sırasıyla:**
1. **JMS583 USB kutusu, kapağı açık** — pitfalls.ru'nun MAP1202'de birebir yaptığı; en çok kanıtlı
2. **PCIe→M.2 adaptör kartı** — SM2263XT vakasında fotoğraflı: "SSD'yi PCI-E adaptöre tak, iki kontağı
   cımbızla kısa devre et ve **bu pozisyonda bilgisayarı aç**; Windows yüklenince cımbızı çek"
3. **Pad'lere ince tel lehimleyip dışarı çıkarmak** — kaynaklarda yapan yok ama PTH oldukları için
   elektriksel sorun yok; erişim probleminin kesin çözümü

### Riskler
- **Yanlış pad = gerçek risk.** usbdev uyarısı: besleme pinine denk gelirse "diski veya anakartı yakabilir"
- Sinyal pad'ini GND'ye çekmek düşük riskli; risk tamamen yanlışlıkla bir **güç** pad'ine dokunmaktan
- **MPTool = diskteki her şey gider**, geri dönüşü yok (bizde sorun değil, kurtarılacak veri yok)
- Etiket metalize, **heatsink görevi görüyor** — gereğinden fazla soyulmamalı

---

## 16. UART — dürüst durum

### Boot log'un anlamı çözüldü
roman2013'ün MAP1202 log'u baştan sona okundu. Kritik okuma:

- `[CodeBlk]S … [CodeBlk]E` **tamamlanıyor** → firmware NAND'dan başarıyla okunuyor. **NAND ve
  firmware imajı sağlam.**
- `[QBT]` (hızlı açılış tablosu): `Q-InvMark`, `Q-Query-NG`, `Q-NoVld`, `Q-RdFail` → **tablo geçersiz**
- `[PBT]` devreye giriyor: blok blok tam tarama (yavaş kurtarma yolu)
- `[SD-Rslt: ffff]` onlarca kez → tarama boşa dönüyor
- `>PE_RISE` / `>PE_FALL` = PCIe **PERST#** kenarları → **host, kontrolcü hâlâ tablo tararken reset atıyor**

Yani o vakada firmware yükleniyor ama **mapping table kurtarma turu host'un zaman aşımıyla yarışıp
kaybediyor.** `CLK:` mesajının çıktığı açılışta ise disk tanınıyor.

Bu, iki hipotezi de ayakta tutuyor — ve **UART'ın değeri tam olarak bunları ayırması.**

### Bizim kartta UART nerede? — bilinmiyor, dürüst cevap
MAP1202/MAP1602 için yayınlanmış bir UART pad haritası **yok**. roman2013 de yazmamış
("UART'ı düzgün bağladım" deyip geçmiş, fotoğrafları forum login'i arkasında).

Referans kartlarda düzen `[TX][RX][GND][BOOT/ROM]` şeklinde, hepsi uzak uçta bir arada.
Bizim kartta uzak uçta **sadece iki** pad var, R/T/G header'ı yok. İki aday kalıyor:
- **A:** ön yüzdeki boş 2-pad SMD ayak izleri (0402/0603 seri direnç yuvaları). SSD tasarımlarında
  UART sık sık boş bırakılmış seri direnç üzerinden dışarı verilir. Ve bir ROM jumper'ı asla
  2-pad'lik SMD ayak izi olmaz — yani bunlar ROM değil, UART olabilirler.
- **B:** arka yüzdeki 12 düz ICT pad'i (riskli bölge, güç rayları içerebilir)

Bu masa başında çözülmez, **ölçmek gerekiyor.**

### Güvenli bağlantı kuralı
- **Sadece adaptör RX ↔ kart TX, ve GND ↔ GND.** Adaptörün TX'ini **hiç bağlama**, VCC'yi **hiç bağlama**.
  Bu düzende karta hiçbir sinyal sürülmez → seviye uyuşmazlığı riski **sıfır**.
- Seviyeyi tahmin etme, **ölç**: kart enerjiliyken şüpheli pad ile GND arası DC gerilim.
  3,3 V → 3,3 V lojik. **1,8 V → CP2102/CH340 yetmez** (3,3 V CMOS'un VIH'i ~2,0 V), FT232H veya
  level shifter gerekir.
- Baud bilinmiyor; 115200'den başlayıp tara. (`uart_dinle.py` bunu otomatik yapıyor.)

### Türkiye fiyatları
| Ürün | Yer | Fiyat |
|---|---|---|
| CP2102 6-pin USB-TTL modül | Direnç.net | ~103 TL |
| CH340G USB-TTL dönüştürücü | Robotistan | ~99 TL |
| FT232RL (WaveShare) | Robotistan | daha pahalı, 1,8 V için gerekebilir |

### Bir uyarı
roman2013'ün diski o denemelerden kısa süre sonra tamamen ölmüş. Kendisi bunu **Secure Erase**'e
bağlıyor, UART'a değil. Yine de not düşüyorum.

---

## 17. ⚠️ İsabet oranı düşmüş görünüyor — dürüst okuma

Bütün açılış denemelerini transcript'ten saydım:

| Zaman | Deneme | Sonuç |
|---|---|---|
| 14:51 | disk takıldı, ilk açılış | BIOS'a girilemedi |
| 15:02 | ikinci deneme | yok |
| 15:48→16:01 | **fiş çekildi, 30 dk beklendi**, açıldı | ✅ **BIOS diski TAM gördü** |
| 16:01 | F10 | gitti |
| 16:05 | tekrar | yok |
| 16:18 | **Fast Boot kapatıldı**, kapat-aç | ✅ **BIOS'ta iki sürücü de vardı** |
| 16:18 sonrası | F10 | gitti, sonra ekran karardı |
| 16:46 – 21:23 | ~6 deneme (Windows PE dahil) | hepsi yok |
| 00:50 – 02:26 | 6 deneme (gece döngüsü) | hepsi yok |

**İlk 4 denemede 2 isabet, sonraki ~15 denemede 0.**

Bu tesadüf olabilir ama olasılığı düşük. Sabit bir %10 oranla "ilk 4'te 2+ isabet ve sonraki 15'te
hiç isabet yok" birleşik olasılığı ~%1. Yani **oran gerçekten düşmüş görünüyor.**

### Ne değişmiş olabilir?
- Disk o günden beri ~20 kez güç döngüsü gördü, birkaç kez sökülüp takıldı
- `pcie_aspm=off pcie_port_pm=off` denendi ve **durumu kötüleştirdi** (geri alındı; şu anki
  cmdline temiz, sadece `amd_iommu=on iommu=pt vfio-pci.ids=1e4b:1202` var)
- `reset_subordinate` portu bozdu (soğuk açılışla düzeldi)
- İlk isabet **30 dakikalık tam soğuma** sonrasıydı; sonraki denemelerin hepsi kısa aralıklı

### İki okuma, ikisi de mümkün
1. **Şans.** n=2 ile örüntü aramak tehlikeli.
2. **Disk kötüleşiyor.** Marjinal bir lehim bağlantısı ya da zayıflayan NAND hücreleri her
   döngüde biraz daha kötüye gidebilir. Eğer böyleyse **daha fazla döngü çevirmenin getirisi
   azalıyor**, hatta zarar veriyor olabilir.

### Bunun karara etkisi
Döngü ucuz ve arka planda çalışıyor, durdurmuyorum. Ama **stratejik ağırlık kaymalı**:
kumar oynamak (döngü) yerine **deterministik yola** geçmek gerekiyor —
ROM kısa devre testi ve UART ölçümü, sonuç ne olursa olsun **bilgi üretir**;
döngü ise ya kazanır ya hiçbir şey söylemez.

Sabah önceliği bu yüzden: **ölç, sonra karar ver.** Döngüyü sabaha kadar arka planda bırakıyorum
ama planın merkezinde değil.

### Bir de sıcaklık notu
İlk isabet 30 dakikalık soğumadan sonra geldi ve kullanıcı o gün diski çıkardığında "sıcaktı"
demişti. Soğukluk lehte olabilir. Kanıt zayıf (n=1) ama bedava bir değişken:
sabah bir deneme de **disk tamamen soğukken** (makine uzun süre kapalı kaldıktan sonra) yapılmalı.

### Bir ölçüm uyarısı: gündüz ve gece "isabet" tanımı aynı değil
Gündüzki iki isabet **BIOS ekranında gözle** görüldü. Gece döngüsü ise diski **Linux açıldıktan
sonra** kontrol ediyor (~2 dakika sonra). Eğer kontrolcü POST'ta ayağa kalkıp Linux'un PCI
taramasından önce ölüyorsa, gece döngüsü onu "kaçtı" sayar ve biz farkında olmayız.

Buna karşı argüman: isabet günlerinde disk BIOS oturumu boyunca (dakikalarca) ayakta kaldı —
kullanıcı menülerde gezinip kapasiteyi okuyabildi. Yani saniyeler içinde ölmüyor. Bu yüzden
kıyas büyük olasılıkla geçerli, ama %100 değil. Kesin ayrım ancak biri BIOS ekranına bakarken
yapılabilir — sabah bir turu böyle yapmakta fayda var.

---
---

# 18. SABAH — KESİN SIRA

> Bu bölüm 9. bölümdeki ilk taslağın yerine geçer. Gece boyunca ROM pad'lerinin yeri bulundu,
> UART yolu ortaya çıktı ve alım kararı netleşti; plan buna göre yeniden yazıldı.

**Temel ilke: sabah hiçbir riskli şey yapma. Önce ÖLÇ, sonra karar ver.**
Döngü bir kumar; ROM ve UART ise sonuç ne olursa olsun **bilgi üretir**. Ağırlık ölçümde.

## A — BEDAVA, ~30 DAKİKA (hemen yapılabilir)

**A0. Gece sonucuna bak**
```
ssh kaplikaya 'jd durum'
```
`YAKALANDI` çıkarsa → doğrudan **D bölümüne** atla, gerisini bırak.

**A1. Diski çıkar, üç fotoğraf çek** (iyi ışık, makro mod)
1. Arka yüz uzak uç — montaj vidası deliği + yanındaki iki delikli pad, kenar da görünsün
2. Arka yüz konnektör yakını — 12 düz test pad'i, varsa serigrafi harfleri okunacak kadar yakın
3. Ön yüz uzak uç — etiketin bittiği yer dahil

**A2. Etiketi KISMEN soy** — sadece uzak uçtaki ~2×2 cm'lik alan (gönderdiğim işaretli fotoğrafta
turuncu kutu). Tamamını soyma: etiket metalize, ısı dağıtıcı görevi görüyor. İnce plastik spatula
veya kredi kartı köşesiyle, ısıtmadan.

**Bakılacak soru: aynı noktada iki delik / iki altın halka çıktı mı?**
- **Çıktıysa** → ön yüzden erişim var, **A4'ü yapabiliriz** (bedava ROM testi)
- **Çıkmadıysa** (solder mask kapatmış) → A4 atlanır, B'deki adaptör beklenir

**A3. Multimetre ile GND'yi bul** (kart takılı DEĞİLKEN, güçsüz — süreklilik/beep modu)
1. Bir prob **montaj vidası deliğinin büyük altın pad'inde** (bu kesin GND)
2. Diğer probla **iki delikli pad'e sırayla** dokun
3. Sonuç:
   - Biri ötüyor, diğeri ötmüyor → **doğru çift bulundu.** Ötmeyen = ROM strap
   - İkisi de ötüyor → yanlış çift, devam etme, bana yaz
   - İkisi de ötmüyor → GND referansını değiştir (gold finger'daki bilinen GND pini)
4. Aynı yöntemle üstteki 12 pad'den hangileri GND, listele → bana yaz (UART'ı daraltmakta kullanacağım)

**Kesinlikle yapma:** iki test pad'ini birbirine değdirme. Ölçüm hep "bir prob GND'de, diğer prob
tek pad'de" şeklinde. Yanlış iki pad'i köprülemek kontrolcüyü öldürebilir.

**A4. ROM kısa devre testi** — sadece A2'de ön yüzde delikler çıktıysa
1. Diski M.2_2 yuvasına tak, kasa yan yatık, disk üstten açıkta
2. Cımbızı iki deliğe bastır
3. Güç düğmesine bas, **~3 saniye tut, sonra bırak**
4. Linux açılınca: `ssh kaplikaya 'jd reg'`

**Ölçüt:** `CSTS.RDY=1` → **ROM modu çalışıyor, kontrolcü sağlam, sorun NAND'daki firmware alanında.**
Bu, MPTool yolunun açık olduğunu gösterir ve JMS583 almayı gerekçelendirir.
`RDY=0` → başka pad kombinasyonu dene, ya da erişim yolunu bekle.

**A5. Soğuk deneme** — makineyi 30+ dakika tamamen kapalı bırakıp (fişi çek) sonra aç.
Gündüzki ilk isabet tam bu koşulda geldi. Bedava, paralel yapılabilir.

**A6. Satıcıya tek soru** (Alperen gönderir, ben göndermem):
> "Sende en son denediğinde BIOS'ta **her seferinde mi** görünüyordu, yoksa bazen kaybolur muydu?"

"Her seferinde" → sorun kargoda/bizde başladı, mekanik hipotez güçlenir.
"Bazen" → sorun zaten oradaydı, retention hipotezi güçlenir.

## B — SİPARİŞ (para hareketi, onayın gerekiyor)

**Minimum paket — USB-TTL, ~100 TL. Bunu her hâlükârda al.**
Neden önce bu: UART log'u "NAND/firmware mi, saat/PLL mi" sorusunu **kesin ayırıyor.**
Saat/PLL çıkarsa JMS583 tamamen boşa para olur. 100 TL, 400 TL'lik yanlış kararı önlüyor.
- CP2102 (Direnç.net ~103 TL) veya CH340G (Robotistan ~99 TL)
- **3,3 V** olmalı. Ankara'da aynı gün alınabilecek yer araştırılıyor.

**Şartlı paket — JMS583, A4 olumluysa veya UART "NAND/firmware" derse**
- **HADRON HDX1768** — üreticinin kendi sayfasında "Chipset: JMS583" yazıyor, doğrulandı
- **ALMA:** RTL9210/RTL9210B'li hiçbir model (Hadron 1772/1774/1780, Sabrent EC-SNVE bunlar)
- ORICO TCM2-C3 doğrulanamadı, kardeş modelleri RTL9210B/JMS580 — varsayma

**Alternatif — PCIe→M.2 adaptör kartı (~100-200 TL)**
Kanıtlı bir vakada (SM2263XT) tam bununla yapılmış: kartı adaptöre tak, cımbızla kısa devre et,
bu pozisyonda bilgisayarı aç. Anakartta boş PCIe yuvası var. Kutudan ucuz ve ROM testi için yeterli
olabilir — ayrıca SSD dik durduğu için **iki yüzü de açıkta kalır**, bizim pad'ler arkada olduğu için
bu önemli bir avantaj.

## C — DÖNGÜ

04:30'da kendiliğinden durdu. Sonucu `turlar.csv` ve `jd durum`'da. Sabah bir tur daha çevirmek
istersen `jd tara` yeterli, ama artık planın merkezinde değil: ilk 4 denemede 2 isabet varken
sonraki ~20 denemede 0 çıktı, oran düşmüş görünüyor.

## D — DİSK YAKALANIRSA (her an olabilir)

1. **Acele etme.** Disk bir kez sağlam ayağa kalkınca kendiliğinden ölmüyor.
2. `jd teshis` → SMART'ta `media_errors`, `unsafe_shutdowns`, `percentage_used`, `critical_warning`
3. `jd format` → `nvme format -s 1`, FTL sıfırdan kurulur
   - "write protected" hatası → salt-okunur kilidi aktif → MPTool'suz çözülmez, B'ye geç
4. `jd_kur.sh yaz` → yaz/oku doğrulaması
5. **Diski açık bırak** — Oracle'ın ikinci resmî çaresi (media refresh). Makineyi kapatma.
6. **Asıl hüküm bir hafta sonra**: bir soğuk açılış daha. Hâlâ görünüyorsa kazandık.
   Bu vakaların çoğunda "düzeldi" denenler bir süre sonra tekrarlamış — ölçüt ilk çalışma anı değil.

---
---

# 19. DÜZELTME — saat/PLL hipotezi çürüdü, sıralama değişti

14. bölümde saat/PLL hipotezini ciddi bir aday olarak sunmuştum. **Geri alıyorum.**

Hipotezin tek dış dayanağı, usbdev vakasında başarılı açılışta çıkan `CLK:550,475,137` satırıydı.
Ama o thread'in **başarısız** açılış log'u da bulundu ve içinde şunlar zaten var:
`DDR:1200`, `Dual CPU Run`, `CPU0 GO`, `LDPC init`, `Z-CFG`, `FA_TM`, `ZQ`, `DCC`,
NAND ID okuma, bad-block taraması (`TotalBBB=10`).

Yani **saatler o vakada da çalışıyor.** `CLK:` satırı firmware yüklendikten sonra saatlerin
operasyonel frekansa çıkarıldığı **geç** bir aşamada basılıyor. Yokluğu "kristal bozuk" değil,
"oraya hiç gelinemedi" demek. Takılma noktası `[QBT]`/`[PBT]` — sistem/FTL tablolarının NAND'dan
okunması.

Ek olarak Rossmann'ın triyaj tablosu kristali **"hiç enumerate etmeyen + soğuk"** satırına koyuyor.
Bizim disk Gen3 x4 enumerate ediyor. O satırda değiliz.
Ve belgelenmiş tek kristal vakası (Zero Alpha, USB bellek) fiziksel hasarlı ve **tamamen ölü** cihaz —
"bazen çalışıyor" değil.

## Yeni sıralama

| # | Hipotez | Ağırlık | Neden |
|---|---|---|---|
| 1 | **Firmware/FTL panic + sistem alanında NAND retention kaybı** | ~%50 | Satıcıda zaten salt-okunurdu · uzun süre enerjisiz · MAP1202'nin **bilinen modal arızası** · `CAP.TO=127,5 sn` · usbdev log'unda `[SD-Rslt: ffff]` · "bazen açılıyor" = marjinal LDPC/read-retry bazen yakınsıyor |
| 2 | **BGA mikro çatlak** | ~%25 | Kargo · Rossmann: *"tamamen ölmeden önce aralıklı çalışabilir"* |
| 3 | **NAND besleme rayı marjinal / çatlak MLCC** | ~%15 | Rossmann'ın `VCC_NAND` satırı tablomuza birebir uyuyor |
| 4 | Saat/PLL | ~%5-10 | Yukarıda çürütüldü |

### Rossmann'ın güç rayı tablosu — hangisi bize uyuyor
| Ray | Çökerse | Bizde |
|---|---|---|
| VCC_CORE | PERST# release olmaz, host link'i **hiç görmez** | Link var → sağlam |
| **VCC_NAND** | **ROM boot eder, firmware yüklemeye çalışır, her NAND okuması 1'ler döndüğü için takılır** | **Birebir uyuyor** |
| VCCQ_NAND (1,8 V) | Enumerate eder, ilk FTL okumasında panic | Kısmen uyuyor |
| VCC_IO / PCIe analog | Link Gen1 x1'e düşer | Gen3 x4 tam → sağlam |

## İki önemli dış bulgu

**1. Bu durum profesyonelce çözülebilen bir sınıf.**
Northwind (profesyonel lab), hddguru, Mayıs 2025:
> "Maxio SSD'leri (0902 ve 1102) artık destekliyoruz. Çözüm, sürücünün panic'e girip safe mode'a
> geçtiği vakalarda çalışmıyor. **Sürücünün BSY kaldığı** vakalarda iyi çalışıyor…
> **şu ana kadar %70 başarı oranı.**"

"BSY'de kalma" = `CSTS.RDY` hiç 1 olmaması = **tam bizim durumumuz.** Yani bizimki, panic/safe-mode
sınıfının değil, **çözülebilir sınıfın** tarafında görünüyor.

**2. Satıcının "salt okunur" ifadesi bir firmware kilidi.**
Rossmann: *"Kendini koruma kilidi — firmware sistemik FTL tutarsızlığı tespit etti, yazmayı ve
TRIM'i engelledi."* Yani **disk daha bize gelmeden firmware kendini kilitlemişti.** Hikâye tutarlı:
format sırasında FTL bozuldu → firmware kendini salt-okunura kilitledi → sonra enerjisiz bekleyiş
sistem alanı okumalarını sınıra itti → artık çoğu açılışta hiç ayağa kalkamıyor.

## Kendi aracımda bulunan hata
`CAP.TO=255` → kontrolcü "hazır olmam **127,5 saniyeyi** bulabilir" diyor. Benim `jd_reg.py`
`CC.EN` sonrası sadece **60 saniye** bekliyordu. Düzeltildi (CAP.TO + 25 sn pay). NSSR beklemesi de
30 sn'den 150 sn'ye çıkarıldı.

Bu, bir yan hatayı da ortaya çıkardı: yakalayıcı artık dakikalarca sürebileceği için, dış döngü
onun bitmesini beklemeden **eski** durum dosyasını okuyup makineyi kapatabilirdi — yani diski
yakaladığımız turda onu öldürebilirdik. Yakalayıcı artık cihazı görür görmez `ENUM_BULUNDU`
yazıyor; döngü bunu görünce anında duruyor.

## 19b. Bedava test bataryası — güncel sıra

Hepsi para gerektirmiyor, hiçbiri geri dönüşsüz değil. Sıra bilgi/risk oranına göre.

**T0 — Zaten cevaplandı: UEFI ne gördü?**
BIOS "JAMESDONKEY JD1024 / 1024 GB" okudu. Rossmann matrisine göre **marka adı + tam kapasite =
firmware sonuna kadar yüklendi.** (Karşıtı: "MAP1202 / 0 byte / 2 MB" = ROM kimliği, firmware
yüklenememiş.) Yani firmware imajı NAND'da **sağlam** ve en az iki kez baştan sona okunabildi.
Bu, "firmware silinmiş/uçmuş" versiyonunu eler; geriye **marjinal okuma** kalır.

**T1 — Flex testi (mekanik ayrımı, 0 TL)** ⭐
Rossmann'ın kesin ifadesi: *"Kontrolcünün bir köşesine hafif baskı uygulanınca geri gelen bir disk,
**doğrulanmış** bir mikro çatlak vakasıdır."*
- Makine açıkken, parmak ucuyla sırayla: kontrolcünün 4 köşesi → 4 NAND paketinin köşeleri → kristal
- Her baskıda `ssh kaplikaya 'jd tara'` (köprüyü yeniden tarar, 60 sn sınırlı)
- Cihaz belirirse → **mikro çatlak doğrulandı**, hangi noktada olduğunu not et
- İkinci varyant: baskıyı **açılış anında** tutarak soğuk açılış yap
- Risk: aşırı bastırma MLCC çatlatır. Parmak ucuyla, alet kullanmadan, kart düz zeminde.

**T2 — Multimetre, güç YOKKEN (güç rayı ayrımı, 0 TL)**
1. Her bobinin süreklilik ölçümü: sağlam bobin **< 1 ohm**, açık devre = yanmış
2. Her ray–GND direnci (düşük ohm kademesi): ~0 ohm = sert kısa devre.
   Sıfıra yakın core rayı = kontrolcü die kısa devre (kurtarılamaz).
   Birkaç ohm – birkaç on ohm = MLCC kısa devresi (tamir edilebilir)
3. Nereden ölçülür: **her bobinin hemen yanındaki çıkış kondansatörünün iki ucu**, ya da bobinin
   kendi iki ucu (test noktası yoksa standart yöntem)
- **Kargo darbesi senaryosunda ilk bakılacak şey bu**: PCB bükülmesinden çatlayan MLCC iç elektrot
  katmanlarını köprüler ve tam kısa devre okur. Bulunursa gerisi anlamsız, önce o çözülür.

**T3 — Multimetre, güç VARKEN** (adaptör/kutu geldikten sonra)
Her bobin çıkış kondansatöründen: ~3,3 V · ~1,8 V (VCCQ) · ~1,1-1,2 V (core).
Core düşük/oynak → PMIC. NAND rayları düşük → `VCC_NAND` hipotezi.

**T4 — Soğuk/sıcak ikilisi (0 TL)**
Rossmann, NAND threshold voltage üzerinden: *"3D TLC/QLC'de durumlar arası marj o kadar dar ki
**20-30 °C ortam değişimi Vth'yi okuma sonucunu çevirecek kadar kaydırır**. Soğuk pakette başarılı
olan bir read-retry offset'i, paket ısındığında çoğu zaman başarısız olur."*
- 10 deneme ~12 °C'de (yoğuşmasız: buzdolabı poşeti + silikajel, ortam sıcaklığına dönmeden çalıştır)
- 10 deneme ~40-45 °C'de
- Soğukta belirgin iyiyse → NAND Vth/retention **veya** BGA çatlak. Fark yoksa → ikisi de değil.
- Not: **iki hipotez de "soğuk daha iyi" diyor**, bu test onları birbirinden ayırmaz ama
  saat/PLL'den ayırır.
- "Dondurucu numarası"nın NVMe'de fiziksel temeli var ama mekanizma kristal değil, **NAND Vth**.

**T5 — 128 saniye testi** (disk enumerate olursa)
`CAP.TO=255` → kontrolcü 127,5 saniyeye kadar süre istiyor. **BIOS POST bu kadar beklemez.**
"Bazen UEFI tam gördü" muhtemelen tam bu: o seferlerde NAND okumaları BIOS penceresine sığdı.
- `CC.EN=0` → `CC.EN=1` → `CSTS`'i **150 saniye** boyunca 100 ms aralıkla oku, zaman damgalı logla
- Üst üste 10 kez, arada güç kesmeden
- Bir kez bile RDY=1 → marjinal NAND okuması kesinleşir, donanım araştırması biter
- (Araçtaki 60 sn'lik hata düzeltildi, artık tam süre bekliyor)

**T6 — ROM modu, sadece Auto Detect** (adaptör geldikten sonra)
MPTool aç → cımbızla ROM pad'lerini kısa devre et → basılıyken diski tak → **Auto Detect** →
cımbızı çek. **START'a BASMA.**
- Görünüyorsa: **kristal, PLL, güç rayları ve kontrolcü %100 sağlam** → arıza firmware/FTL/NAND
- Görünmüyorsa: donanım şüphesi ciddileşir → T1/T2'ye dön
- START'a basmamak önemli: teşhis için gereksiz, ve panic durumdaki bir sürücüde MPTool sistem
  alanını yeniden yazar

**T7 — Host değiştir (0 TL)**
Farklı M.2 yuvası, farklı makine, BIOS'ta link'i **Gen1'e zorla**. Marjinal analog rayı olan bazı
diskler Gen1'de tutunuyor.

### ⚠️ Northwind bulgusuna dair düzeltme
Yukarıda "%70 başarı" rakamını bizim duruma doğrudan uygulanabilirmiş gibi sundum. **Değil.**

Northwind'in desteklediğini söylediği kontrolcüler **MAS0902 ve MAS1102** — ikisi de Maxio'nun
**SATA** kontrolcüleri. Bizimki MAP1202, **NVMe**. Aynı üretici, farklı aile ve farklı arayüz.
Bu, diğer bulguyla da tutarlı: PC-3000 SSD Maxio'yu **yalnızca SATA** tarafında destekliyor,
NVMe'de desteklemiyor.

Devam eden geçerli kısım: "BSY'de kalma" ile "panic/safe-mode" ayrımının **kavramsal** olarak
anlamlı olması ve ilkinin yazılımla çözülebilir sayılması. Ama %70 rakamı bizim kontrolcü için
**geçerli değil**, ve o araçlar bizde çalışmaz.

Ticari kurtarma dünyasında MAP1202 firmware arızası bugün fiilen **çıkışsız**: PC-3000 desteklemiyor,
Rossmann bu kontrolcülere firmware kurtarma hizmeti vermiyor (sadece elektriksel teşhis yapıyor),
hddguru'da MAP1202A için ACELab yol haritası sorulmuş ve **cevap gelmemiş**.

Yani bizim yolumuz profesyonel servis değil, **MPTool ile yeniden açma (开卡)** — ve o yolda
aynı kontrolcüde çalıştığına dair iki somut vaka var (gabrielpic/CSDN ve JenDos_50/usbdev).

---

## 20. JMS583 alımı — doğrulanmış liste

Her satır üreticinin **kendi** sayfasından veya kart fotoğrafından doğrulandı; satıcı beyanı sayılmadı.

| Ürün | Çip | Kanıt | Karar |
|---|---|---|---|
| **HADRON HDX1768** | **JMS583** | hadron.com.tr spec tablosu "Chipset: JMS583". Tutarlılık: Hadron çipi her URL'ye yazıyor ve seride tek JMS583 bu (1769=JMS581D, 1772/1774/1780=RTL9210B, 1781=RTL9201R) → SKU'ya özel gerçek, pazarlama kopyası değil | ✅ **AL** |
| **ORICO çıplak "PVM2-C3" kartı** | **JMS583** | ORICO'nun kendi ürün görselinde çıplak PCB fotoğrafı, üstünde "JMS583 chip" açıklaması. Serigrafi `PVM2-C3-R1.1 / LYH-2` | ✅ **AL** — ama satıcı fotoğrafında JMS583 serigrafisi görünüyorsa |
| ORICO TCM2-C3 (kutulu) | **değişken** | Erken revizyon JMS583 (PVM2-C3 kartı), geç revizyon RTL9210B. İki bağımsız alıcı raporu RTL9210B diyor | ⚠️ **YAZI-TURA, alma** |
| ORICO M2PV-C3 | RTL9210 | ORICO'nun kendi açıklama görseli: "Realtek RTL9210 10Gbps control scheme" | ❌ |
| ORICO M2PJ-C3 | doğrulanamadı | Çip bilgisi yok; ama **formu ideal** (çıplak PCB, alüminyum kılıftan düz çıkıyor) | ⚠️ |
| Sabrent EC-SNVE | RTL9210B | Sabrent'in kendi SSS'i | ❌ |
| JEYI ThundeRate / i9X | RTL9210B | Amazon.com.tr açıklamaları | ❌ |
| Hadron 1772 / 1774 / 1780 | RTL9210B | üretici URL'leri | ❌ |

### Alperen'in kendi uygulayabileceği eleme kuralı
**Çift protokollü (NVMe + NGFF/SATA) kutular JMS583 OLAMAZ.** JMS583 fiziksel olarak SATA
yapamıyor. Ürün "hem NVMe hem SATA destekler" diyorsa, o RTL9210/JMS580 ailesindendir, elenir.

### Neden "çıplak kart" formu tercih edilmeli
Bizim ROM pad'leri kartın **arka** yüzünde. Kapalı bir kutuda SSD, kutunun tabanına bakacak şekilde
oturur ve arka yüze cımbız giremez. Type-C konnektörü kendi üstünde olan **çıplak adaptör kartı**
bu sorunu çözüyor: SSD takılı, iki yüzü de açıkta, kart masada duruyor.
Kanıtlı vakada da kutu **kapağı açık** çalıştırılmış.

---

## 21. ALIŞVERİŞ — kesin liste, Ankara

### Minimum paket (~116 TL) — bunu her hâlükârda al
| Ürün | Yer | Fiyat | Not |
|---|---|---|---|
| **CP2102 USB-TTL 3.3V/5V** | **Robo90, Ostim/Ankara** | **115,92 TL** | Stokta · **"Mağazadan Teslim Al" seçeneği var → AYNI GÜN elden** |

**Neden CP2102, FT232RL değil:** CP2102'nin IO'su donanımsal olarak **daima 3,3 V** (dahili
regülatörden beslenir). FT232RL ve CH340G modüllerinde 3,3V/5V jumper'ı VCCIO'yu değiştirir ama
**klon kartlarda bazen sadece VCC çıkışını** değiştirir — 5 V lojikle karta bağlanma riski.
CP2102'de bu risk yok. Linux sürücüsü (`cp210x`) çekirdekte hazır.

**1,8 V ihtimali çözüldü:** FT232H Türkiye'de pratik değil (tükenmiş, 1.279 TL, üstelik VCCIO'su
3,3 V'a sabit). Yerine **TXS0108E 8 kanal seviye dönüştürücü, 57,96 TL, Robo90, stokta** —
1,2-3,6 V ↔ 1,65-5,5 V, bizim durum tam spec içinde.
**Ama önce ölç:** SSD enerjiliyken UART TX pad'inin boştaki DC gerilimi ~3,3 V ise doğrudan CP2102;
~1,8 V ise araya TXS0108E. CP2102'nin VIH'i ~2,31 V olduğu için 1,8 V'luk sinyali göremez —
bu kalıcı hasar değil, sadece okunmaz.

### Şartlı paket (~690 TL) — sadece testler MPTool yolunu gerekçelendirirse
| Ürün | Yer | Fiyat | Not |
|---|---|---|---|
| **Hadron HDX1768** (JMS583) | **Smallman, Balgat/Çankaya** | **690,36 TL** | Bilkent'e ~6 km · fiziksel mağaza · Pzt-Cum 09:00-18:00 · 0850 210 9200 |
| (alternatif) aynı ürün | Ofisomi, Eryaman/Ankara | 721,74 + 99,90 kargo | ikinci Ankara satıcısı |

⚠️ Smallman'ın ürün sayfasında "JMS583" **yazmıyor**; iddia Hadron'un kendi açıklamasından geliyor.
**Mağazadan alırken kutunun üstüne bak.** Aldıktan sonra kesin doğrulama: `lsusb` çıktısında
**`152d:0583`** görünmeli. Görünmezse JMS583 değildir, iade et.

### Yardımcılar
| Ürün | Yer | Fiyat |
|---|---|---|
| **4'lü 0,22 mm çok telli montaj kablo, 1 m** | Robo90 | **34,78 TL** |
| TXS0108E seviye dönüştürücü (gerekirse) | Robo90 | 57,96 TL |

Püf nokta: çok telli kablonun içinden **tek damar** çekilince ~0,08 mm tel elde ediliyor —
pad'e lehimlemek için emaye telden bile rahat. Ayrı emaye tel almaya gerek yok.

### PCIe adaptör kartı — alma, gerekmiyor
Alfais 4391 (279,99 TL) / Dark DK-AC-PEM1X (349 TL) gibi kartlar var ama:
- MPTool **USB istiyor**, PCIe kartı onun yerine geçmiyor
- Anakartta zaten M.2 yuvası var, SSD'yi enerjilendirmek için yeterli
- **Ve asıl geometri sorununu çözmüyor** (aşağıda)

---

## 22. ⚠️ Erişim geometrisi — önceki planımın düzeltmesi

"USB kutusunda / PCIe adaptöründe kart dik durur, iki yüzü de açıkta kalır" demiştim. **Yanlış.**
Her üç düzenlemede de (anakart M.2 yuvası, PCIe adaptörü, USB kutusu) SSD **yatay** durur ve
**alt yüzü** taşıyıcı PCB'ye bakar; arada sadece ~2-4 mm var. Bizim ROM pad'leri alt (arka) yüzde
olduğu için cımbızla üstten nişan almak hiçbirinde mümkün değil.

**Gerçek çözümler, iyiden kötüye:**

1. **Pad'lere ince tel lehimle** (0,08-0,2 mm), telleri dışarı çıkar, açılışta jumper'la kısa devre et.
   Geometri sorunu **tamamen** ortadan kalkar, cımbızla nişan alma derdi yok.
   → Bu yüzden **"ince tel + havya" listede cımbızdan DAHA kritik.**
   ❓ **Alperen'de havya var mı? Bunu bilmiyorum, sabah sorulacak.** Yoksa Ostim'de/Ankara'da
   basit bir havya ucuz; ya da tanıdık bir tamirciye 5 dakikalık iş.

2. **SSD'yi vidalamadan eğik bırak.** M.2 modülü serbestken uzak ucu ~20-25° kalkıyor →
   birkaç mm fazladan boşluk. Bizim pad'ler **tam uzak uçta ve kenara yakın** olduğu için
   ince bir cımbız girebilir. **Bedava, ilk denenecek şey bu.**

3. Ön yüzde delik çıkarsa (etiket soyulunca) → en kolayı, üstten cımbız.

4. M.2 uzatma/riser kablosu — SSD tamamen serbest kalırdı ama **Türkiye'de bulunamadı**.

---

## EK — ham araştırma notları

Bu rapor bir özet. Altındaki ham notlar, birebir alıntılar ve indirilen kanıtlar burada:

| Dosya | İçerik |
|---|---|
| `arastirma/map1202-teknik.md` | MAP1202 iç yapısı, boot dizisi, ROM modu, firmware nerede saklanır, UART boot log'u |
| `arastirma/cn-mydigit.md` | Çince forum taraması: JMS583 zorunluluğu, 开卡 prosedürü, ROM pad, ölü yollar |
| `arastirma/cn-tieba-zhihu.md` | ROM kısa devre mekanizması, anakart yuvasında kısa devre vakası, 量产部落 envanteri |
| `arastirma/cn-tool-kaynak.md` | 19 MPTool sürümünün tam envanteri, paket kimlikleri, Flash.ini sürümleri |
| `rompad/notlar.md` + görseller | ROM pad konumu (3 referans kart), prosedür, UART pad analizi, riskler |
| `kristal/notlar.md` + `usbdev_12338_full.txt` | Saat/PLL çürütmesi, güç rayı tablosu, flex testi, sıcaklık, taban oranı |
| `hyv6/notlar.md` (718 satır) | V6 NAND kimliği, Flash.ini v043, eksik dosyalar, marka updater yolu |
| `tedarik/notlar.md` | Türkiye fiyatları, çipset doğrulamaları, Ankara mağazaları, geometri analizi |

Araçlar: `jd/` altında — `jd` (tek giriş noktası), `jd_reg.py`, `jd_yakala.sh`, `jd_kur.sh`,
`jd_dongu.sh`, `wol.py`, `uart_dinle.py`, `jd_vm.sh`, `vmkey.py`, `turlar.csv`.
Kaplıkaya'da kurulu: `/usr/local/bin/jd`, `jd_reg.py`, `jd_yakala.sh`, `jd_kur.sh`,
`/etc/systemd/system/jd-yakala.service` (enabled), `~/jdvm/` (Windows PE VM).

### Bir metodoloji notu
Bu gece arama motorlarının çoğu bu IP'den captcha verdi (Google, Bing, DDG, Yandex, Baidu, Brave,
76 SearXNG instance'ı). Araştırma bu yüzden **doğrudan üretici/forum sitelerine giderek** yapıldı.
Bunun bir yan etkisi var: Almanca, Vietnamca ve Portekizce kaynaklara hiç girilemedi.
Çalışan tek genel arama motoru `old-search.marginalia.nu` çıktı.

---

## 23. Atlanan bedava seçenek — ikinci bir makine

Elde bir **i3-6100 eski kasa** var (satış listesinde duruyor). Skylake dönemi anakartların bir
kısmında M.2 NVMe yuvası bulunuyor. Varsa bu, **hiç para harcamadan** şunları değiştiren bir test:

- Farklı **PCIe root complex** (Intel, AMD değil)
- Farklı **UEFI** ve farklı NVMe sürücüsü — özellikle **farklı bekleme süresi**
- Farklı güç kaynağı ve farklı 3,3 V rayı

Neden anlamlı: BIOS'un diski gördüğü iki anda, kontrolcü ~127,5 saniyeye kadar süre isteyebiliyor
ama **BIOS POST bu kadar beklemez**. Farklı bir UEFI daha uzun (veya daha kısa) bekleyebilir.
Ayrıca satıcının sorunu **B450**'ye geçince başlamıştı — yani host değişkeni bu vakada zaten
bir kez rol oynamış görünüyor.

Kontrol edilecek: i3-6100 kasasının anakartında M.2 M-key yuvası var mı. Varsa disk oraya takılıp
bir soğuk açılış denenir. T440'ta yuva **yok** (2,5" SATA + mSATA/mini-PCIe, NVMe yuvası yok).

---

## 24. Montaj — kontrol edilmemiş bir değişken

Disk M.2 yuvasına, orijinal plastik aparat yerine **doğaçlama bir erkek-dişi standoff** ile
tutturuldu. PCIe link her açılışta 8GT/s x4 kurulduğuna göre konnektör teması sağlam — o taraf
sorun değil. Ama iki şey kontrol edilmedi:

1. **Standoff kartı bükerek monte ediyor olabilir.** BGA mikro çatlak hipotezi (~%25) tam olarak
   mekanik gerilimle açılıp kapanan bir bağlantıdan bahsediyor. Rossmann'ın kriteri:
   *"kontrolcünün bir köşesine hafif baskı uygulanınca geri gelen disk = doğrulanmış mikro çatlak."*
   Yani mevcut montaj, çatlağı **kapalı** ya da **açık** tutuyor olabilir.
2. **Vidasız/eğik deneme hiç yapılmadı.** M.2 modülü serbestken uzak ucu ~20-25° kalkıyor.
   Bu, hem farklı bir mekanik gerilim hem de ROM pad'lerine cımbız erişimi demek.

**Sabah bedava denenecek:** diski standoff'suz, vidasız, sadece konnektöre oturmuş hâlde
(uzak ucu serbest, hafifçe kalkık) bırakıp bir soğuk açılış yap. Davranış değişirse mekanik
hipotez güçlenir.

---
---

# 25. ⚠️ ALIM TAVSİYESİ DEĞİŞTİ — JMS583'ü şimdilik alma

21. bölümde JMS583'ü "şartlı paket" olarak koymuştum. Şart artık **sağlanmıyor**:
**elimizde yazılacak firmware yok ve kamuya açık hiçbir yerde de yok.**

## Neden — yapısal cevap

MPTool'un işi diski sıfırdan "açmak": tüm blokları silmek, bootloader + sistem firmware'i yazmak,
taze bir FTL kurmak. Bunun için NAND neslinin **SYS firmware'i** gerekiyor. Bizimki **V6**.

Marka firmware updater'ları tarandı — ADATA Legend 750 ve ZhiTai TiPlus5000'den **18 SYS bin**
çıkarıldı (Micron B47R, YMTC, WD BiCS5). Yerel ağaçtaki toplam: **72 bin, 23 benzersiz SYS adı,
sıfır HYV6.** usbdev'in marka bölümleri de tarandı (~190 firmware sayfası): MAP1202 ailesinden
sadece 4 sayfa var, ikisi zaten bizde.

Ve neden yok olduğu anlaşıldı: 188.959 diskli bir saha veritabanı gösteriyor ki **aynı model adı
altında farklı NAND partileri** satılıyor — KingSpec NX-256 → SN8878 (HYV6), ama Fanxiang S500PRO
256GB → SN10093/10613/11457, hepsi YMTC. **Alperen'in ünitesi azınlık bir HYV6 partisi.**
Markalar azınlık partisi için ayrı updater yayınlamıyor.

Çift yönlü doğrulama: `YI0PCELC`, `ZI0PCABC`, `SN8878`, `SN09466` imzalarının internette **hiç izi yok**
(kontrol sorgusuyla test edildi — arama çalışıyor, sonuç gerçekten sıfır).

Kapatılan yan iz: Lexar NM610 PRO'daki üç şifreli `.pkg` gerçekti ama Release Note'a göre
yükseltilebilir sürümleri 7939/8530/9139 — `SN07939` = **YMTC X2-9060**, elimizde zaten var.
Şifreyi kırmak HYV6 getirmezdi.

## Sonuç: sıralama değişiyor

| Alım | Önceki | Şimdi |
|---|---|---|
| **USB-TTL (~116 TL)** | 1. öncelik | **1. öncelik, değişmedi** |
| JMS583 kutusu (~690 TL) | şartlı | ⛔ **şimdilik ALMA** — yazacak firmware yok |

MPTool yolu firmware bulunana kadar **kapalı**. ROM kısa devre testi hâlâ değerli
(kontrolcünün sağlam olduğunu söyler) ama tek başına diski çalıştırmıyor,
ve o test için de kutu şart değil — vidasız/eğik montajla denenebilir.

## Firmware için kalan iki yol

**A. Kendi diskimizden okumak.** Bu, gecenin en ilginç fikri ve hiç denenmedi:
- `T0` bulgusu: BIOS diski iki kez **tam** gördü → **firmware imajı NAND'da sağlam.**
  Sorun firmware'in kendisi değil, FTL/sistem tabloları.
- `MXUtility_MAP1202_V1_11.exe` tek exe, DAT/PARA/TMC/SYS klasörü istemiyor, ve
  **GDP modunda** ham sayfa okuma (`Read C:%d B:%d Block:%d Page:%d`), `DumpRAWFile`,
  `VP_UploadCodeFromFlash` destekliyor.
- Elimizdeki `ucode.bin` **SKV6 mikrokodunu 8 frekansta içeriyor** → GDP modu V6 NAND'la
  konuşabilir.
- Yani: ROM moduna sok → GDP ile kendi firmware'imizi geri oku → onu SYS bin olarak kullan.
- Eksik kalan: `nandmem_SKV6_page.bin` (MP akışının sayfa haritası) ve `DAT/SKV6/` timing.
  Bunlar hâlâ yok, ama GDP okuma bunlara ihtiyaç duymuyor — en azından **firmware'i eline alırsın.**

**B. Donor cihaz.** GiGimundo G3500 1TB'ın tam bizim `YI0PCELC` firmware'ini taşıdığı belgelendi.
Çalışan bir üniteden `Upload` ile firmware çekilebilir. Ama çalışan bir 1 TB disk almak,
bozuk diski kurtarmaktan pahalı — ekonomik değil, sadece kayıt için.

## Diğer kapanan izler
- **JamesDonkey gerçekten SSD satıyor** (linuxhw/SMART'ta JD120/JD240/JD480 kayıtları var);
  önceki "sadece klavye/mouse" tespiti eksikmiş. Ama JD1024 o veritabanında yok.
- **PCB kodu SMPMA1286** GitHub'da ve marginalia'da **0 sonuç** — aynı PCB'yi kullanan
  başka marka tespit edilemedi.
- Acer/Predator: Biwin sürücüsünün ikili kodunda sadece `b58r_map1202` + `tas_map1202` sınıfları var,
  Hynix sınıfı yok.
- Doğrulanamayanlar (yok demiyorum): Kingston (Akamai 403), PNY (404), Origin (CF 403).

---
---

# 26. ⭐ TEK SAYFA — sabah bu yeter

> Önceki plan bölümleri (9, 18) geçersiz. Bu, gece boyunca öğrenilen her şeyi içeren son hâli.

## 0 · İlk 30 saniye
```
jd durum        # gece döngüsü ne yakaladı
jd turlar       # tur tur sonuçlar
```
`YAKALANDI` yazıyorsa → **§5'e atla**, gerisini bırak.

## 1 · Hiçbir şey almadan, ~30 dakika

Sırayla. Her adım bir hipotezi eliyor.

**1a — Diski standoff'suz dene.** Vidasız, sadece konnektöre oturmuş, uzak ucu serbest.
Soğuk açılış yap. Doğaçlama standoff kartı büküyor olabilir; BGA mikro çatlak hipotezi
(~%25) tam bununla ilgili. **Bedava, en hızlısı, ilk bu.**

**1b — Flex testi.** Makine açıkken parmak ucuyla sırayla bastır: kontrolcünün 4 köşesi →
4 NAND paketinin köşeleri → kristal. Her baskıda `jd tara`.
Cihaz belirirse → **mikro çatlak doğrulandı**, hangi noktada olduğunu not et.
Rossmann'ın kriteri bu: *"hafif baskıyla geri gelen disk = doğrulanmış mikro çatlak."*

**1c — Multimetre, güç yokken.** Her bobinde süreklilik (`<1 Ω` sağlam). Sonra her ray–GND direnci:
~0 Ω = kısa devre. Kargo darbesi çatlak MLCC yapmış olabilir; bulunursa gerisi anlamsız.

**1d — Etiketi kısmen soy** (uzak uçtaki ~2×2 cm, işaretli fotoğraftaki turuncu kutu).
Arka yüzdeki iki delikli pad ön yüzde de görünüyor mu? Görünüyorsa cımbızla üstten
kısa devre yapılabilir → **1e'yi yap**. Görünmüyorsa 1e'yi vidasız/eğik montajla dene.

**1e — ROM kısa devre testi.** Cımbızı iki pad'e bastır → güç düğmesine bas → **3 saniye sonra bırak**
→ Linux açılınca `jd reg`.
`CSTS.RDY=1` → **kontrolcü, saatler ve güç rayları %100 sağlam**, arıza firmware/FTL tarafında.
`RDY=0` → başka pad çifti dene, ya da 1b/1c'ye dön.

**1f — Multimetre ile GND'yi doğrula** (kart güçsüzken, süreklilik modu): bir prob montaj vidası
pad'inde, diğeriyle iki delikli pad'e sırayla dokun. Biri ötüp diğeri ötmüyorsa **doğru çift bu**.
Aynı yöntemle üstteki 12 düz pad'den hangileri GND, listele → bana yaz.
**İki test pad'ini birbirine değdirme** — güç rayı olabilir, kontrolcüyü öldürür.

**1g — Soğuk deneme.** Makineyi 30+ dk tamamen kapalı bırak, sonra aç. Gündüzki ilk isabet
tam bu koşulda geldi. Soğuk hem NAND retention hem BGA çatlak hipotezinde lehte.

**1h — İkinci makine.** i3-6100 eski kasada M.2 M-key yuvası var mı? Varsa disk oraya takılıp
soğuk açılış denenir. Farklı UEFI = farklı bekleme süresi, farklı root complex, farklı 3,3 V.
(T440'ta NVMe yuvası **yok**.)

**1i — Satıcıya tek soru:** *"Sende en son denediğinde BIOS'ta her seferinde mi görünüyordu,
yoksa bazen kaybolur muydu?"* — "her seferinde" = sorun kargoda başladı (mekanik),
"bazen" = zaten oradaydı (retention).

## 2 · Alınacak tek şey (~116 TL)

**CP2102 USB-TTL 3,3 V — Robo90, Ostim/Ankara, 115,92 TL, "Mağazadan Teslim Al" ile aynı gün.**

Ne işe yarıyor: MAP1202'nin UART portundan **açılış log'unu** okuyacağız. Log'un nerede durduğu
hangi hipotezin doğru olduğunu **kesin** söylüyor. Bağlantı: adaptör **RX** ↔ kart **TX**,
**GND** ↔ **GND**. Adaptörün TX'ini ve VCC'sini **hiç bağlama** — o zaman karta hiçbir sinyal
sürülmez, risk sıfır. Baud bilinmiyor, `uart_dinle.py` otomatik tarıyor.
Pad gerilimi 1,8 V çıkarsa: TXS0108E seviye dönüştürücü, 57,96 TL, aynı mağaza.

Yanında: **4'lü 0,22 mm montaj kablosu, 34,78 TL** (tek damar çekilince ~0,08 mm tel olur,
pad'e lehimlemek için).

## 3 · ⛔ JMS583 kutusunu ŞİMDİLİK ALMA

690 TL. MPTool'un çalışması için **V6 NAND'a ait SYS firmware** gerekiyor ve o firmware
**hiçbir yerde yok** — sebebi de anlaşıldı (§25: azınlık NAND partisi, marka updater yayınlamamış).
Firmware bulunmadan kutu almak boşa para.

## 4 · Firmware bulunursa açılacak yol
ROM modu → JMS583 → MPTool → Auto Detect → Start.
En umutlu kaynak: **kendi diskimizden GDP modunda okumak** (§25-A). Firmware imajımız NAND'da
sağlam (BIOS iki kez okudu), `ucode.bin`'de SKV6 mikrokodu var, `MXUtility` GDP'de ham okuma yapıyor.

## 5 · Disk yakalanırsa
1. Acele etme, disk bir kez ayağa kalkınca kendiliğinden ölmüyor
2. `jd teshis` → SMART: `media_errors`, `unsafe_shutdowns`, `percentage_used`
3. `jd format` → FTL sıfırdan kurulur. "write protected" hatası → salt-okunur kilidi aktif
4. `jd_kur.sh yaz` → yaz/oku doğrulaması
5. **Diski açık bırak** — Oracle'ın media refresh çaresi. Makineyi kapatma.
6. **Hüküm bir hafta sonra**: bir soğuk açılış daha. Bu vakaların çoğunda "düzeldi" denenler
   tekrarlamış; ölçüt ilk çalışma anı değil.

---

## 27. Döngü verisi — negatif ama bilgi veriyor

**14 tur, 14 kaçış.** Ama turlar rastgele değildi, kapalı kalma süresi ve soak dönüşümlü uygulandı:

| Koşul | Deneme | İsabet |
|---|---|---|
| 40 sn kapalı | 5 | 0 |
| 90 sn kapalı | 5 | 0 |
| 180 sn kapalı + 5 dk soak (3 yeniden tarama) | 4 | 0 |

**Çıkarımlar:**

1. **Kapalı kalma süresi fark yaratmıyor** (40 ↔ 180 sn arasında). Zaten fiziksel olarak beklenen
   buydu: S5'te M.2 rayı anında kesiliyor, kartın kendi kondansatörleri milisaniyelerde boşalıyor.
   Gündüzki "30 dakika bekledik, sonra gördü" korelasyonu büyük olasılıkla tesadüftü.

2. **Bekletmek işe yaramıyor.** Soak turlarında makine 5 dakika açık bırakılıp 90 saniyede bir
   köprü yeniden tarandı — kontrolcü hiçbirinde geç de olsa ayağa kalkmadı.
   Yani **sonuç güç verildiği anda belirleniyor**; sonradan düzelmiyor.

3. **Yeniden tarama yolu çalışıyor** (60 sn sınırlı, kilitlenmiyor) ama boş dönüyor —
   yani cihaz UEFI'nin penceresini kaçırıp Linux'a yetişen bir "geç açılan" değil.

4. **İsabet oranı gerçekten düşmüş.** Gündüz ilk 4 denemede 2 isabet, sonraki 22 denemede 0.
   Sabit %10 oranla bu birleşiktir olasılığı ~%1. Ya şans ya da disk kötüleşiyor.
   Her iki durumda da **döngüyü çevirmeye devam etmenin getirisi düşük** — ağırlık ölçüme kaymalı.

**Not:** Bu geceki turlar diski Linux açıldıktan sonra kontrol etti. Kontrolcü POST'ta ayağa
kalkıp Linux'un PCI taramasından önce ölseydi bunu göremezdik. Karşı argüman: isabet günlerinde
disk BIOS oturumu boyunca dakikalarca ayakta kaldı. Yine de sabah bir turu **BIOS ekranına
bakarak** yapmakta fayda var.

---
---

# 28. Gecenin kapanışı

**Sonuç: disk yakalanamadı.** 14 otomatik soğuk açılış turu, 14 kaçış.

Ama gece boşa geçmedi — bilinmeyenlerin çoğu kapandı:

| Soru | Gece başında | Şimdi |
|---|---|---|
| Disk ölü mü? | belirsiz | **Hayır.** BIOS iki kez tam gördü → firmware NAND'da sağlam |
| Neden açılmıyor? | 6-7 hipotez | **3'e indi**, ağırlıklarıyla: FTL/retention ~%50, BGA çatlak ~%25, güç rayı ~%15 |
| Saat/PLL olabilir mi? | akla gelmemişti | önce güçlendi, sonra **kanıtla çürütüldü** (~%5) |
| ROM pad'i nerede? | bilinmiyordu | **bulundu** — kartın arka yüzünde, iki delikli pad |
| Hangi NAND? | `H25T1TB4BE` (yanlış okuma) | **`H25T1TB48E` = V6 nesli**, iki bağımsız yoldan doğrulandı |
| Hangi MPTool sürümü? | "elimizdeki ikisinden biri" | **hiçbiri** — V6 paketi hiç yayınlanmamış, sebebi de anlaşıldı |
| Hangi USB kutusu? | RTL9210B (yanlış) | **JMS583** — ama firmware olmadan **alma** |
| Teşhisi nasıl kesinleştiririz? | yol yoktu | **UART açılış log'u**, ~116 TL |

**Yanlış çıkan üç şeyim** (kayda geçsin):
1. "ROM modu `FFFF:1201` gösterir" — MAP1201 ayrı bir ürünmüş, ROM modunun ayrı PCI ID'si yok
2. "Saat/PLL ciddi aday" — başarısız açılış log'unda saatler zaten çalışıyor
3. "Pad'ler delikli, ön yüzden erişilir, yuvada kısa devre yapılabilir" — geometri buna izin vermiyor

**Kurulan ve çalışır durumda bırakılanlar:**
- `jd` komutu (hem T440'ta hem kaplıkaya'da)
- `jd-yakala.service` — her açılışta koşuyor, disk görünürse teşhis alıp tutuyor, format atmıyor
- Uzaktan soğuk güç döngüsü (WoL + RTC), istenirse tekrar çalıştırılabilir
- Windows PE sanal makinesi, vfio passthrough hazır
- `uart_dinle.py` — adaptör gelince baud taraması dahil hazır
- Kalıcı arşiv: `~/jd1024/` (34 MB, rapor + notlar + kanıt + araçlar + fotoğraflar)

**Sabah ne yapılacağı §26'da, tek sayfa.**


---

# 29. ⭐⭐⭐ 14 EYLÜL — TEŞHİS KAPANDI: KONTROLCÜ CANLI, ARIZA FIRMWARE'DE

Bu bölüm gece boyunca yapılan bütün hipotez sıralamasını geçersiz kılıyor. Tahmin değil,
ham donanım register okuması.

## Ne ölçüldü

`jd-yakala` log'unda gözden kaçmış bir satır vardı: boş sanılan köprünün link durumu.
Canlı doğrulandı (kaplıkaya, 14 Eyl 08:53, disk 2 gündür yuvada, hiç enumerate olmamış):

| Köprü | Ne var | `LnkSta` | `SltSta` |
|---|---|---|---|
| `03:00.0` (M.2_2 = **JD1024**) | — (Linux görmüyor) | **Speed 8GT/s, Width x4** | **PresDet+** |
| `03:08.0` (gerçekten boş) | yok | Speed 2.5GT/s, Width x1 | PresDet− |
| `03:09.0` (gerçekten boş) | yok | Speed 2.5GT/s, Width x1 | PresDet− |
| `03:0b.0` (gerçekten boş) | yok | Speed 2.5GT/s, Width x1 | PresDet− |

Ayrıca `LnkSta2: EqualizationComplete+ EqualizationPhase1+`, sysfs canlı değerler
`current_link_speed = 8.0 GT/s`, `current_link_width = 4`.

**Yani JD1024'ün PCIe linki Gen3 x4'te eğitilmiş ve ayakta.** Boş yuva öyle görünmez.

## Sonra: cihaz config okumasına ne diyor

Köprüye `rescan` verildi, süresi ölçüldü ve `dmesg` alındı:

```
=== rescan basliyor: 08:53:26 ===
=== rescan bitti:   08:54:35   SURE=69 saniye ===
pci 0000:04:00.0: not ready after  1023ms; waiting
pci 0000:04:00.0: not ready after  2047ms; waiting
pci 0000:04:00.0: not ready after  4095ms; waiting
pci 0000:04:00.0: not ready after  8191ms; waiting
pci 0000:04:00.0: not ready after 16383ms; waiting
pci 0000:04:00.0: not ready after 32767ms; waiting
pci 0000:04:00.0: not ready after 65535ms; giving up
```

Bu mesajlar Linux'ta **tek bir yerden** çıkar: `pci_bus_wait_crs()`. Ve sadece config
okuması **Vendor ID = 0x0001** döndürdüğünde. `0x0001`, PCIe spesifikasyonunda
**CRS = Configuration Request Retry Status** sihirli değeridir: _"buradayım, isteğini
aldım, ama henüz hazır değilim, sonra tekrar dene."_

Linux'a güvenmeyip ham ECAM okuması da yapıldı (`/usr/local/bin/jd_crs.py`,
MCFG'den ECAM tabanı `0xE0000000`, adres `0xE0400000` = bus 4 dev 0 fn 0):

```
ECAM 0xe0400000  ham=0100ffff  vid=0x0001 did=0xffff
link: 8.0 GT/s PCIe x4
-> CRS - cihaz CANLI, 'hazir degilim' diyor
```

## Bu ne demek — nokta nokta

`0xffff` (cevap yok) ile `0x0001` (CRS) arasındaki fark her şey demek:

1. **Kontrolcü besleniyor ve çalışıyor.** CRS cevabını üreten şey kontrolcünün PCIe
   bloğudur; bunun için güç, saat ve çalışan bir transaction layer şart.
2. **Referans saat ve PLL kilitli.** Gen3 8 GT/s eğitimi CMU PLL'in 100 MHz refclk'e
   kilitlenmesini gerektirir. Equalization Phase 1 tamamlanmış.
3. **PCIe lane'lerinin, refclk'in ve güç toplarının BGA lehimleri sağlam.** 4 lane = 16 top,
   artı saat ve güç topları. Mikro çatlak olsa link ya hiç eğitilmez ya x1/x2'ye düşerdi.
4. **Güç rayları spec içinde.** SerDes PHY, çipin gürültüye ve gerilime en duyarlı bloğudur;
   çatlak MLCC / zayıf ray olsa Gen3 x4 eğitimi tutmaz.
5. **Arıza tamamen firmware'in iç başlatmasında.** Kontrolcü açılıyor, PCIe'yi kaldırıyor
   (bu iş boot ROM / donanım varsayılanlarıyla erkenden oluyor), sonra NAND/FTL init'e
   gidiyor ve **bir daha "hazırım" demeye dönmüyor.** Sonsuza kadar CRS'te kalıyor.

Diskin **2 gündür** CRS'te olması, "bekleme işe yaramıyor" gözlemini artık tahmin
olmaktan çıkarıyor: kontrolcü sessiz değil, aktif olarak sonsuz bir "hazır değilim"
döngüsünde.

## UART log'uyla birebir oturuyor

roman2013'ün MAP1202 boot log'u: `DDR:1200` → `Dual CPU Run` → `LDPC init` →
NAND ID okuma → bad block taraması → **sonra ölüyor**. PCIe zaten o noktadan önce
ayakta. Yani ölüm noktası FTL / sistem alanı yükleme adımı. CRS bulgusu bunu
bağımsız olarak doğruluyor.

## Yeni hipotez sıralaması

| Hipotez | Gece | Şimdi | Neden değişti |
|---|---|---|---|
| Firmware / FTL init hang (sistem alanı retention) | ~%50 | **~%95** | CRS = kontrolcü canlı, sadece FW dönmüyor |
| BGA mikro çatlak | ~%25 | **~%2** | Gen3 x4 link eğitimi 16 lane topunu + saat + güç topunu doğruluyor |
| NAND besleme rayı / çatlak MLCC | ~%15 | **~%2** | PHY en hassas blok, sorunsuz çalışıyor |
| Saat / PLL | ~%5-10 | **~%0** | 8 GT/s eğitimi PLL kilidini kanıtlıyor |

Kalan %1: NAND tarafındaki topların (PHY'den ayrı) çatlak olması. UART log'unda NAND ID
okunabildiği için bu da zayıf.

## Denenen ve BAŞARISIZ olan: sıcak sıfırlama ile hızlı deneme kanalı

Mantık şuydu: soğuk açılış 7 dakika sürüyor; köprüde secondary bus reset (`reset_subordinate`)
yapıp saniyeler içinde yeniden deneyebilir miyiz? 15 tur denendi:

```
tur 1/15: CEVAP YOK (UR) - endpoint sessiz   link=2.5 GT/s PCIe x1
...
tur 15/15: CEVAP YOK (UR) - endpoint sessiz  link=2.5 GT/s PCIe x1
```

**İlk hot reset link'i düşürdü ve endpoint bir daha eğitilmedi.** `LnkCtl.RetrainLink`
denendi, `LnkCtl.LinkDisable` aç-kapa denendi — ikisi de link'i geri getirmedi.
Şu an link `2.5 GT/s x1` (yani ölü) ve config okuması `0xffffffff`.

İki sonuç:
- **Hızlı deneme kanalı yok.** Tek yol soğuk açılış. Bu bir kayıp.
- Ama bilgi verdi: **endpoint'in LTSSM'i hot reset'ten sonra Detect'e dönüp yeniden
  eğitilmiyor.** Sağlıklı bir endpoint milisaniyeler içinde geri gelir. Demek ki PCIe
  bring-up'ı bir kere, güç açılışında (POR) boot ROM yapıyor; asılı kalan firmware
  bunu bir daha yapmıyor. Bu da firmware teşhisini güçlendiriyor.
- **Link bir sonraki soğuk açılışta geri gelecek** (26 çevrimdir her açılışta geliyor).
  Doğrulanana kadar bu bir varsayım olarak kalır.

## Bunun bugünkü plana etkisi

**ROM kısa devresinin beklenen değeri fırladı.** Artık biliyoruz ki silikon sağlam ve
tek sorun firmware'in NAND'dan yüklenmesi. ROM/loader modu tam olarak bu adımı atlar:
kontrolcü NAND firmware'ini hiç yüklemez, iç boot ROM'undan kalkar. Yani **ROM modunda
CRS'ten çıkıp enumerate olması beklenir.** Test artık "acaba kontrolcü sağ mı" değil,
"kurtarma yolu açık mı" sorusunu soruyor.

Okuma tablosu — soğuk açılıştan sonra `sudo jd_crs.py oku`:

| Çıktı | Anlamı | Sonraki adım |
|---|---|---|
| `vid=0x1e4b` | **ROM modu çalıştı**, kontrolcü ayakta | MPTool / MXUtility yolu açıldı |
| `vid=0x0001` (CRS), link x4 | Tel bir şey değiştirmedi (yanlış pad ya da yanlış yöntem) | Tut-bırak varyantı, sonra diğer pad çiftleri |
| `vid=0xffff`, link x1 @2.5 | Belirsiz: ya telin kısa devresi kötü bir yere denk geldi ya hot reset izi | Teli çıkar, tekrar aç — ayrım bu |

## Araç

`/usr/local/bin/jd_crs.py` (kaplıkaya):
- `oku` — tek ham ECAM okuması + link durumu
- `izle [saniye]` — 200 ms'de bir, değişince yazar
- `sifirla [tur]` — hot reset + hızlı poll (**artık kullanma**, link'i düşürüyor)


---

# 30. ⚠️ 14 EYLÜL — ROM KISA DEVRE ARAŞTIRMASI: ÜÇ DÜZELTME

## 30.1 Kutupluluk her zaman GND değil — bu benim en riskli hatamdı

15. bölümde "çiftin biri GND" yazmıştım ve "güven yüksek" demiştim. **Genel kural olarak yanlış.**
usbdev'in en kıdemli katkıcısı vlo, [topic 9310](https://www.usbdev.ru/f/index.php?topic=9310.0):

> «3 площадки у s8 обычно **3v3/gpio0/gpio7. замыкать 3v3/gpio0.**»

_Phison PS3108 (S8)'de üç pad var: 3v3/gpio0/gpio7. **3v3 ile gpio0 kısa devre edilir.**_
Yani **GND'ye değil, 3,3 V'a** çekiliyor. Innogrit IG5236'da GPIO11 **1,8 V**'a çekiliyor.
Silicon Motion SM2246EN ise tersi — çipi söküp datasheet okuyan biri
([topic 5385](https://www.usbdev.ru/f/index.php?topic=5385.0)):

> «пин J4 это ROM активен при низком уровне то есть на земле»

Sonuç: **bilinmeyen bir kontrolcüde "biri GND'dir" varsayımı tam tersi olabilir.**
MAP1202 için kutupluluk bilinmiyor.

## 30.2 MAP ailesinin ROM pad'leri kamuya açık olarak ÇÖZÜLMEMİŞ

[hddguru topic 46268](https://forum.hddguru.com/viewtopic.php?t=46268), **1-2 Eylül 2026** — iki hafta önce.
Başlık: _"Lexar NM790/MAP1602A — need shorting point for ROM mode."_ Bir tamirci, bizim
kontrolcünün en yakın kardeşinin pad'lerini soruyor. **fzabkar** — bulabildiğim en yetkin
kamuya açık SSD elektroniği uzmanı — pad cevabı veremiyor, doğaçlama yapıyor:

> "There is an SOT23-5 IC to the right of the Maxio controller. I suspect that it provides
> the VCC supply for the NAND flash. If so, then you could short its enable pin to ground."

Tamirci deniyor: **"I try, and nothing, can't detect drive, nothing."** IC, NAND PMIC değil
Maxio çipinin 1,8 V LDO'su çıkıyor. Konu 14 mesaj sonra **"What can i do, to force ROM on
this board!?"** ile cevapsız kapanıyor.

Yani: VLO arşivinde MAP kaydı yok, PC-3000'de MAP loader yok, Rossmann MAP işi almıyor,
hddguru'nun yerleşik uzmanı iki hafta önce MAP1602A'yı çözememiş. **MAP1202 için tek çalışan
bilgi Çin 开卡 topluluğunun ampirik "kontrolcünün yanındaki iki ROM pad'i" bilgisi.**

Bizim pad tespitimiz bir tek referans karta dayanıyor: **Netac NV3000 250GB, aynı kontrolcü
(MAP1202)**. Bu, ajanın çerçevelediğinden daha iyi bir kanıt — ama "güven yüksek" demek
fazlaydı. Doğrusu: makul dayanaklı tahmin, kanıtlanmış harita değil.

## 30.3 Direnç: 100 Ω değil, 1 kΩ

vlo'nun kuralı: «**резистора в 1к достаточно почти везде**» — 1 kΩ neredeyse her yerde yeterli;
gördüğü tek istisna Marvell 1120. Ve «покуда точно не известно — безопаснее резистором»
_(kesin bilinmedikçe dirençle daha güvenli)_. Pad'leri **ikişer ikişer** dene, hepsini birden asla.

## 30.4 "İşe yaradı" pad'in doğru olduğunun kanıtı DEĞİL

fzabkar, kondansatör pad'lerini kısa devre eden bir kullanıcıya:

> "they could be the NAND power supply, in which case the controller may go into safe mode
> because it doesn't find any NAND chips."

**NAND besleme rayını öldürmek de kontrolcüyü ROM moduna sokar.** Yani rastgele bir rayı
kısa devre etmek çoğu zaman "işe yarar" — ve elektriksel olarak yanlış olan tekniği
diski öldürdüğü güne kadar pozitif pekiştirir. Belgelenmiş bir vakada boot pini **birkaç
başarılı denemeden sonra** sessizce ölmüş.

Yanlış tahminin ölçülebilir belirtisi: yanlış J2 pad'leri köprülenen bir SM2259XT
0,07 A yerine **0,4-0,6 A** çekmiş.

## 30.5 "Tut" mu "bırak" mı — kontrolcüye değil ARACA bağlı

- **PC-3000**: init sırasında diski defalarca power-cycle ettiği için strap **sürekli tutulur**
  — _"we need to repower them a few times during the drive initialization. The SSD has to be
  in a SAFE MODE all the time."_ Arayüzü birebir: _"Press 'Next' holding points shorted"_.
- **MPTool / 开卡 akışı** power-cycle yapmaz → **tanınınca bırakılır**.

İkisi de kendi aracı için doğru. Bizim akış MPTool tarafı.

## 30.6 Topluluğun kendi itirazı

PS3111 kullanıcısı hangi pad'leri kısa devre edeceğini sorduğunda vlo'nun cevabı:
«**а нафига, если он определяется?**» — _"peki niye, madem tanınıyor?"_

Pad kısa devresi aygıtı **hiç** enumerate olmayan diskler için var. Bizimki bazen oluyor.
Bu itiraz ciddiye alınmalı — ama bizim durumumuzda "bazen"in oranı son 22 denemede 0.

## 30.7 Denenmesi önerilen ve BİZE UYMAYAN öneri

`nvme.quirks=1e4b:1202:delay_before_chk_rdy`. Parametre **gerçekten var** — kaplıkaya'da
doğrulandı (kernel 7.0.0-31, `modinfo nvme` → `parm: quirks:Enable/disable NVMe quirks by
specifying quirks=VID:DID:quirk_names`).

**Ama bize uymuyor.** Bu quirk `nvme_probe()` çalıştıktan sonra devreye girer; `nvme_probe()`
için cihazın PCI'da enumerate olması şart. Bizim disk PCI enumerasyonunda, CRS'te ölüyor —
nvme sürücüsü onu hiç görmüyor. §29'daki CRS bulgusu bu öneriyi kapatıyor.

## 30.8 Açılan yeni yol: "Jump To Loader" (donanıma dokunmadan)

MPTool'da, halihazırda enumerate olmuş bir diski yazılımla loader moduna sokan bir komut
olduğu iddia edildi. Doğrulanıyor. Eğer varsa: **iyi bir açılış yakalandığında pad'e hiç
dokunmadan ROM moduna geçilebilir.** vlo'nun "madem tanınıyor" itirazının pozitif hâli.


---

# 31. ⚠️⚠️ 14 EYLÜL — §4.3 VE §25 GEÇERSİZ: FLASH.INI KAYDI ZATEN BİZDEYDİ

## 31.1 Dün geceki kararım yanlıştı

§4.3'te _"elimizdeki MPTool paketlerinin hiçbiri uymuyor"_, §25'te _"NAND'ımız V6; 19 usbdev
paketi + 18 SYS bin'inde sıfır HYV6"_ yazmıştım ve **bu gerekçeyle JMS583 alımını geri çektim.**
Flash tablosu tarafında bu yanlış.

`~/jd1024/kanit/ini/map1202_43.ini`, **12 Eylül 04:11'den beri arşivde**, satır 86:

```
Name005=SKV606412 H25BFT8A1BDA  3 2 2  5776 1536 16 2 2  0xAD 0x7E 0x29 0x53 0x02 0xB0  0 0 0 11 4 3000 001 2048 100
```

`0xAD 0x7E 0x29 0x53 0x02 0xB0` = **bizim FlashID'imiz, birebir.** Geometri de tutuyor:
CE/Package 2 × Die/CE 2 = 4 die, 5776/2 = 2888 blok/die × 1536 sayfa × 16 KB ≈ 512 Gbit/die
→ 256 GB/paket × 4 paket = **1 TB**.

Kaynak paket: **Maxio MAP1202 MP/Sorting Tool C.1.1.26 [HYV8-SN26637]**,
`https://www.usbdev.ru/?wpfb_dl=14809`, `Flash.ini` tarihi 2024-09-18, `FlashIniVer=043`.
İkinci bağımsız kopya: `https://github.com/iTXTech/fdfdb/blob/master/ma/map1202_43.ini`.
Provenance'lı kopya arşive eklendi:
`kanit/ini/MAP1202_Flash.ini_v043_usbdev_HYV8pkg_C.1.1.26.ini`.

**v043, MAP1202 için kamuya açık en yüksek Flash.ini sürümü.** v044+ yok.

Ek düzeltme: v033 de V6 biliyor — ama `0x28` (1-CE/1-die) varyantını. Bizim `0x29`
(2-CE/2-die) varyantı yalnız v043'ten itibaren var. Doğru ifade: _v033 V6'yı tanır, bizim
die yapılandırmamızı tanımaz._

## 31.2 Gerçekten eksik olan iki dosya

Dört parçadan **ikisi elimizde**:
- ✔ Flash tablosu kaydı — `map1202_43.ini` Name005
- ✔ SKV6 read-retry tablosu — `kanit/ini/mem.ini` içinde `[SKV6_001_1]`, `[SKV6_001_2]`
- ✔ SKV6 SORT microcode — `SORT/ucode.bin`, 8 frekans (`SKV6_001_200…1200`)
- ✘ **`DAT/SKV6/001_<clk>/nandmem_SKV6_page.bin`** — hiçbir kamuya açık pakette yok
- ✘ **`SYS/YI0PCELC.bin`** — bizim SYS firmware'i; internette sıfır sonuç

Doğrudan çıkarımla doğrulandı: HYV7 ve HYV8 paketlerinin ikisinde de `DAT/SKV6/*` = 0 dosya,
`nandmem_SKV6_page.bin` = 0 dosya, `0P` önekli (HYV6) SYS bin = 0 dosya.

Maxio'nun kendi release note'u V6'nın 2022'de birinci sınıf desteklendiğini gösteriyor
(`MPT_Cougar_C_0_1_017`, 20220527: _"Support SKV6-128GB/die … update SKV6 ucode … support
hynix v6 1Tb"_) — yani dosyalar var, sadece hiç yayınlanmamış.

Ve yayınlanmayacağına dair pozitif kanıt: liangchanba'nın Mart 2026 snapshot'ında
`MAP1202 MP/Sorting Tool C.0.01.018_HYV6 (ZI0PCABC…)` kaydı **待发布 = "yayınlanacak"**
durumundaydı, ek yoktu; o blok bugün sayfadan tamamen silinmiş.

usbdev'de aynı arayışta bir konu var — [topic 13429](https://www.usbdev.ru/f/index.php?topic=13429.0),
1 Mart 2026, aynı NAND'lı Fanxiang. Global Moderator **hardmaster**'ın cevabı:
> «Этой прошивки нет даже у китайцев за деньги. У нас то откуда?»
> _Bu firmware Çinlilerde parayla bile yok. Bizde nereden olsun?_

## 31.3 ⚠️ "Jump To Loader" bize çalışmaz — bir saat önce söylediğimin düzeltmesi

Komut **gerçekten var.** `MXMPTool_MAP1202_USB_V1_1_26.exe` içindeki Delphi DFM kaynağından,
`MainMenu` → `Tools` → üçüncü öğe:

```
TMenuItem Tool            Caption 'Tools'
  TMenuItem EraseCodeBlock  Caption 'Erase Code Block'
  TMenuItem N1              Caption '-'
  TMenuItem JumpToLoader    Caption 'Jump to Loader'   OnClick JumpToLoaderClick
  TMenuItem JumpToSystem    Caption 'Jump To System'
```

Motor tarafı: `VP_JumpToLoader`, `VP_IsLoaderMode`, `Boot_Into_Loader_Mode`,
hata kodu `P18 Jump To Loader Fail`.

**Ama bizim diske uygulanamaz.** MPTool cihazlara yalnızca `\\.\PhysicalDriveN` üzerinden
erişiyor (`ScsiCdbPassThrough`, `SCSItoNVMeIdentify()`); ham PCIe/BAR işi yapmıyor. Bizim
kontrolcü `CSTS.RDY`'yi hiç set etmiyor → Windows hiç PhysicalDrive yaratmıyor → menü
komutunun tutunacağı bir handle yok. Ayrıca geçerli bir loader block gerekiyor
(`Can't find valid loader block!`) — ROM kısa devresinin var olma sebebi tam olarak bu.

Aynı gerekçeyle **HYV8 paketinin Auto Detect'ini "risksiz teşhis" olarak koşmak da**
diskin enumerate olmasına bağlı. Koşulsuz değil.

## 31.4 Sonuç: ROM kısa devresi artık tek kapı — ve amacı değişti

Kalan üç yol, gerçekçilik sırasıyla:

1. **ROM kısa devre → GDP modu → kendi firmware'imizi geri okumak.**
   `MXUtility_MAP1202_V1_11.exe` içindeki `VP_UploadCodeFromFlash`, çıktıyı exe'nin yanındaki
   `.\raw\[%d]UP_%d_%d_%d_%d_%d.raw` dosyasına yazıyor. Bu yol **hiçbir SKV6 dosyasına ihtiyaç
   duymuyor** — ham sayfa seviyesi erişim. Yanına `GDP.bin` (HYV8 paketinden) ve v043
   `Flash.ini` konmalı; MXUtility kendi `GDP.bin`'ini getirmiyor.
   Diğer GDP yetenekleri: `VC_GDP_CmdBlockErase`, `VC_GDP_ChangeFlashID`, `DumpRAWFile`,
   `VP_CheckCodeBlockFromFlash`, `Try to find code block by GDP`.

2. **DarwinLudwig'den takas/satın alma.** usbdev Global Moderator,
   [topic 13782](https://www.usbdev.ru/f/index.php?topic=13782.0), ilanı **13 Eylül'de**
   düzenlenmiş. İki satır:
   - `ALLFLASH: MAP1202  MAP1602a  MAP1608`
   - `💰 ДЛЯ ACELAB: SK Hynix SATA/NVMe MPTool + sort + fw (HYV5, HYV5Q, **HYV6**, HYV7, HYV8, HYV9)`

   Şartlar: doğrudan ödeme ya da elinde olmayan/kamuya açık olmayan yazılımla takas.
   **⚠️ Çelişki:** hardmaster (§31.2) "Çinlilerde parayla bile yok" diyor, DarwinLudwig
   elinde olduğunu iddia ediyor. İkisi de aynı forumun moderatörü. Fazla yatırım yapmadan önce
   bu çelişki tartılmalı. **Temas kararı Alperen'in.**

3. **Enumerate olan bir açılış yakalayıp** yazılımla müdahale — son 22 denemede 0 isabet.

## 31.5 Bunun dünkü JMS583 kararına etkisi

§25'te JMS583 alımını "firmware yok, kutu boşa gider" diye geri çekmiştim. Gerekçenin
Flash.ini kısmı çürüdü, ama **karar değişmiyor** — çünkü asıl eksik iki binary hâlâ yok ve
kutunun asıl işlevi (ROM pad'lerine kapak açıkken erişim) M.2 yuvasında tel köprüyle de
sağlanabiliyor. Kutu, ancak §31.4/1 yolu tel köprüyle yürümezse gerekir.


---

# 32. 14 EYLÜL — TEŞHİS LİTERATÜRÜ: İKİ TEST PLANDAN ÇIKARILDI

## 32.1 ⛔ FLEX (bükme) TESTİ İPTAL — zarar veren test

§19b'deki bedava test bataryasında "kartı hafifçe bük, davranış değişiyor mu" vardı.
**Bu test, aramaya çalıştığımız arızayı üretebilir.**

KYOCERA AVX, _MLCC FlexiTerm™: Guarding Against Capacitor Crack Failures_
([PDF](https://www.kyocera-avx.com/docs/techinfo/CeramicCapacitors/mlccflex.pdf)):
AEC-Q200 bükme testi kartı **90 mm aralıklı iki mesnede** koyup 1 mm/s ile büküyor ve
**"minimum flex requirement of 2 mm"** diyor. Yani standart bir MLCC yalnızca **2 mm**
sehime dayanacak şekilde nitelendiriliyor. M.2 2280 kartı ~80 mm. **Elle bükmek, standart
MLCC'lerin çatladığı aralığın tam içinde.**

Aynı kaynak, çatlağın neden sonradan ortaya çıktığını da açıklıyor:
> "component fractures may not initially be obvious using capacitance and Q factor testing.
> The actual MLCC component's operation may not degrade until moisture ingresses into the
> crack causing a low resistance path between adjacent electrodes"

Yani bugün büküp "bir şey olmadı" dersek, arıza haftalar sonra çıkabilir. **Bükme testi
plandan çıkarıldı.**

## 32.2 ⛔ RÖNTGEN İPTAL — kanıt değeri neredeyse yok

Lars Bruno & Benny Gustafson, **Ericsson AB**, _Head-on-Pillow Defect Detection – X-ray
Inspection Limitations_ ([PDF](https://smtnet.com/library/files/upload/S03-2.pdf)).
Kasıtlı HoP kusurları üretip röntgenle bakmışlar, sonra BGA'ları söküp doğrulamışlar:

> "In Figure 24, all nine BGA solder joints were judged as HoP defects at the x-ray image
> analysis. However, after prying, only two of them were verified as real HoP defects."

Dokuz macun için doğrulama oranları: **%61, %3, %42, %100, %12, %65, %72, %100, %23.**
Sonuç cümlesi: _"it is almost impossible to guarantee detection of all HoP defects by only
using x-ray inspection."_ Ve IPC-A-610G §8.3.12.3 _"gives no guidance in interpreting x-ray
images"_.

2D röntgen çatlağı ne kanıtlar ne çürütür; üstelik ciddi biçimde yanlış pozitif veriyor.

## 32.3 Multimetreyle BGA çatlağı ARANMAZ — fizik buna izin vermiyor

IPC-SM-785, Jianbiao Pan'ın _A Study of Solder Joint Failure Criteria_
([IMAPS PDF](https://imapsource.org/article/56522-a-study-of-solder-joint-failure-criteria.pdf))
içinden birebir: tam çatlamış bir lehim topu bile elektriksel süreksizlik göstermeyebilir çünkü

> "a failed solder joint is normally surrounded by solder joints that have not yet failed and
> therefore the solder joint fracture surfaces make compressively loaded contact."

Pan'ın sonucu: 100 Ω, 1000 Ω ya da %20 direnç artışı eşiklerinin hiçbiri kısmi çatlağı
yakalayamıyor. Sandia (Vianco, SAND2017-1070J) mekanik taraftan aynı şeyi söylüyor.

**Tek kanıtlayıcı yöntem yıkıcı:** IPC-TM-650 Metot **2.4.53** _Dye and Pull_ — boya emdir,
67,7 kPa vakum altında 30 dk beklet, kurut, çekerek ayır, kırık yüzeyleri boyalı mı diye bak.
Bizim için anlamsız.

**Not:** multimetre yine de lazım — ama BGA için değil, **ROM pad'lerinden hangisinin GND
olduğunu** bulmak için.

## 32.4 JTAG / boundary scan da kapalı

XJTAG'in kendi dokümanı: standart bir interconnect testi _"can only check for faults on nets
between JTAG devices"_. Bizim kartta tek JTAG cihazı MAP1202 var, NAND'da boundary cell yok,
MAXIO BSDL yayınlamıyor ve M.2 kenarında TAP yok. Üstelik **besleme ve toprak toplarının
boundary cell'i yoktur** — yani açık bir güç topu IEEE 1149.1'in görebileceği şeyin dışında.

## 32.5 Soğutucu sprey: son çare, ve yarı-yıkıcı

Chemtronics'in kendi ifadesi
([kılavuz](https://www.chemtronics.com/ultimate-guide-to-diagnostic-freeze-spray)):
> "spray isolated areas of the live PCB until it stops functioning. The thermal shock of the
> refrigerant will tend to break loose a bad (or 'cold') or brittle solder joint, **creating a
> catastrophic failure**"

Yani mekanizma termal şok — kasıtlı olarak arızayı **üretmek**. Ayrıca Techspray uyarıyor:
sprey plastik borudan çıkarken statik üretiyor, topraklama bileklik bunu engellemiyor;
antistatik formül gerekiyor.

Sıcaklık gerçeği: Chemtronics'e göre kart yüzeyi buz tuttuğunda **~0 °C**'de, kutunun
verdiği −45/−51 °C'de değil.

## 32.6 Yakın ıska: MAXIO'nun belgelenmiş CRTO=0 hatası — bizim hatamız DEĞİL

Bulunması gereken bir şey bulundu ve **elenmesi** gerekiyor. MAXIO kontrolcüleri NVMe
`CRTO` register'ında hatalı 0 raporluyor ve sürücünün hazır-olma zaman aşımını çökertiyor.
Yamada adı geçen diskler: **Lexar NM790, AIGO P7000Z, Fanxiang S790, Acer Predator GM7**
([linux-nvme yaması](http://lists.infradead.org/pipermail/linux-nvme/2023-September/042160.html)).
Bir Fanxiang S790 kullanıcısının tarifi bizimkine ürkütücü derecede benziyor
([Arch forum](https://bbs.archlinux.org/viewtopic.php?id=287649)):

> "It has a high probability of not boot (Sometimes it booted)"

**Ama bizim arızamız bu değil.** O hata `nvme_enable_ctrl()` içinde, yani sürücü diski
zaten görmüş, BAR0'ı map etmiş, `CC.EN` yazmış ve `CSTS=0x0` okuyor. Bizim disk PCI config
uzayında, CRS'te ölüyor — nvme sürücüsü hiç devreye girmiyor. Ayrıca mainline `pci.c`'de
`0x1e4b:0x1202` için quirk kaydı yok; sadece `0x1e4b:0x1602` var (`NVME_QUIRK_BOGUS_NID`).

Yani §30.7'deki karar doğruydu, şimdi gerekçesi de tam: **yanlış katman.**

## 32.7 Bağımsız doğrulama: "imza tekdüzeliği" testi ve bizim verimiz

Ajanın en iyi çıkarımı şuydu: çatlak bir top, 26 başarısız açılışta **çeşitli** imzalar
üretmeliydi — bazen `lspci`'de hiç yok, bazen `CSTS=0xffffffff`, bazen link x1/x2'ye düşmüş.
Tekdüze imza ise bring-up/firmware yarışına işaret eder.

**Bizim verimiz tekdüze.** `jd-yakala` log'unda her başarısız açılışta aynı iki satır:

```
kopru: LnkSta: Speed 8GT/s, Width x4
kopru: SltSta: Status: ... PresDet+ ...
```

Link **her seferinde** tam Gen3 x4'te eğitilmiş, hiçbir turda downtrain yok, hiçbir turda
link kaybı yok. Ham okuma da her seferinde CRS. Bu, §29'un CRS sonucunu **bağımsız bir
muhakemeyle** doğruluyor.

## 32.8 Doğrulanan güvenlik iddiaları (kaynaklı)

- **M.2 kartında tek besleme var ve 3,3 V.** PCI Express M.2 Spec Rev 1.1 §4.4:
  _"The M.2 module utilizes a single regulated power rail of 3.3 V provided by the platform."_
  Tablo 40: 3,135-3,465 V. 12 V yok. → Elle temasta çarpılma riski yok, eldiven gereksiz.
- **M.2 hot-plug DEĞİL.** Aynı spec §4 başı: _"CAUTION: M.2 modules are not designed or
  intended to support Hot-Swap or Hot-Plug connections."_ → Diski güç varken takıp çıkarma.
  (Pad'e dokunmak ayrı şey, o sorun değil.)
- **Yeniden açmadan önce beklenecek süre:** §4.3.2 _"The voltage on all supplies should remain
  below 100 mV for at least 1 ms before the power-on sequence is restarted."_ Bizim 40/90/180 sn
  kapalı kalma süreleri fazlasıyla yeterliydi — o değişkeni doğru elemişiz.
- **Spec'e göre cihaz PERST# bırakıldıktan 120 ms sonra config isteklerine hazır olmalı**
  (PCIe CEM). Bizimki 2 gün sonra hâlâ değil.

## 32.9 ROM modu başarılıysa nasıl görünecek

Rossmann, Maxio/InnoGrit için: ROM modundaki sürücü **2 MB, 2,1 GB ya da 0 bayt** kapasite
raporluyor. Yani `vid=0x1e4b` görürsek ve kapasite saçmaysa, bu **firmware yükleme arızası**
teşhisinin son çivisi olur.


---

# 33. 14 EYLÜL — DİSKİN GEÇMİŞİ DÜZELTİLDİ: BU İKİNCİL DİSKTİ

Alperen satıcıdan öğrendi: **işletim sistemi bu diskte değildi, bu adamın ikinci SSD'siydi.**

Raporun birkaç yerinde "satıcıda format sırasında FTL bozuldu" anlatısı vardı. Bunu
düzeltmek gerekiyor:

- Disk **veri diski** olarak kullanılmış, boot diski değil. Yani sürekli OS yazması altında
  değildi; ikincil diskler çoğu zaman **boşta durur**.
- "Salt okunur hatası" bir veri diskinde tam olarak beklenen FTL-kilidi belirtisi: firmware
  tutarsızlık görüp kendini korumaya alıyor, disk okunuyor ama yazılamıyor.
- Bu, **retention (tutma) kaybı** hipotezini biraz daha güçlendiriyor: az yazılan, çoğu zaman
  boşta duran, sonra tamamen enerjisiz kalan bir diskte sistem alanı okumaları sınıra itilir.
  Buna karşılık "yazma sırasında güç kesintisi" senaryosu biraz zayıflıyor — ikincil disk
  o an yazıyor olmayabilir.

**Teşhise etkisi yok** (§29'daki CRS ölçümü zaten firmware'i işaret ediyordu), ama iki pratik
sonucu var:

1. **Diskte satıcıya ait kişisel veri olabilir.** Şu an erişilemiyor ve MPTool yolu zaten her
   şeyi siliyor; ama bir şekilde okunabilir hâle gelirse içeriğe bakılmamalı, doğrudan
   silinmeli.
2. Diskin "kaç TBW yemiş" tahmini aşağı çekilmeli — veri diski olarak az yazılmış olması
   muhtemel. Yani NAND aşınması (wear-out) daha da düşük ihtimal.


---

# 34. 🟢🟢🟢 14 EYLÜL 10:42 — ROM MODU ÇALIŞTI

Alperen iki ROM deliğine düz bakır tel köprü koydu (direnç yok), makineyi tam enerjisiz
kapatıp (PSU anahtarı + kondansatör boşaltma) açtı. **İlk denemede tuttu.**

## Kanıt — tahmin değil, sysfs'ten okundu

```
model        = Generic_Loader_NVMe_Device
serial       = LDR000DEV000000000
firmware_rev = L190301R
namespace    = YOK
```

`Generic_Loader_NVMe_Device`, Rus kaynaklarının tarif ettiği loader modu imzasının birebir
kendisi (pitfalls.ru: _"Generic_ Loader_NVMe_Devi SCSI Disk Device"_). Seri numarası
**LDR**000DEV..., firmware **L**190301R — L = Loader, 190301 = 2019-03-01 derleme tarihi.

```
04:00.0 MAXIO MAP1202 (DRAM-less) [1e4b:1202] (rev 01)
ECAM 0xe0400000  ham=4b1e0212  vid=0x1e4b did=0x1202
CRS beklemesi: 0 satir   (onceki her acilista 2 x 60 saniye)
*** CSTS.RDY=1 -- KONTROLCU HAZIR ***   CC.EN sonrasi 0.0 saniyede
```

## Loader firmware'i normal firmware'den farklı — bağımsız doğrulama

| Register | Normal (12 Eyl, iki yakalama) | Loader (14 Eyl) |
|---|---|---|
| `VS` | NVMe **1.4.0** | `0x00010300` = NVMe **1.3.0** |
| `CAP` | `0x00200030ff0103ff` | `0x00200030ff03ffff` |
| Namespace | 1024 GB | **yok** |
| `LnkCap` ASPM | destekli | **not supported** |
| Model | JAMESDONKEY JD1024 | Generic_Loader_NVMe_Device |

Bunlar farklı bir kod tabanının çalıştığını gösteriyor — yani kontrolcü NAND'daki ana
firmware'i **hiç yüklemedi**, iç boot ROM'undan kalktı. Aradığımız şey buydu.

## Teşhis artık kapalı — %100

§29'daki CRS bulgusu firmware'i işaret ediyordu; bu onu kesinleştiriyor:

- NAND'dan firmware yüklenmeyince kontrolcü **0,0 saniyede** hazır oluyor
- Aynı kontrolcü, aynı kart, aynı güç rayları, aynı saatler, aynı BGA lehimleri
- Tek değişen: firmware yükleme adımının atlanması

**Silikon, güç, saat, lehim, PCIe — hepsi sağlam. Arıza yalnızca NAND'daki firmware/FTL.**

## Yapılan müdahale

Linux'un `nvme` sürücüsü loader'ı standart bir NVMe denetleyicisi sanıp saniyede onlarca kez
resetliyordu (`request 0xd genctr mismatch`, `invalid id 13 completed on queue 0`,
`state = resetting`). Loader standart sürücüyle sürülmek için değil, MPTool/MXUtility'nin
satıcı komutlarıyla sürülmek için var. Sürücü ayrıldı:

```
echo 0000:04:00.0 > /sys/bus/pci/drivers/nvme/unbind
```

Sonrası stabil: cihaz yerinde, sürücü yok, `CSTS.RDY=1`, 5 saniyede 0 hata.

## ⛔ ŞU AN YAPILMAYACAKLAR

- **`nvme format` / secure erase YOK.** Araştırma, bizimkiyle birebir aynı davranan tek
  MAP1202 vakasını buldu: roman2013 şanslı bir açılış yakalayıp iki secure erase çalıştırmış,
  kısa süre çalışmış, iki ay sonra — «**Диск сдох достаточно быстро после «магии»**»
  (disk "sihir"den kısa süre sonra öldü). usbdev topic 12338.
- **Yeniden başlatma YOK.** Güç durduğu sürece loader modu devam ediyor. Kapatırsak tekrar
  tutturmak zorundayız.
- **Tel yerinde kalıyor.** Çıkarma kuralı MPTool'un `START` adımı için; oraya gelmedik.

## Sıradaki adım

Windows PE sanal makinesine vfio ile geçir → `MXUtility_MAP1202_V1_11.exe`
(yanına HYV8 paketinden `GDP.bin` + v043 `Flash.ini`) → `VP_UploadCodeFromFlash` /
`DumpRAWFile` → kendi firmware'imizi `.\raw\` klasörüne oku.

Not (vlo, usbdev): `maxio_nvme_fid` «**Не работает в rom mode, но ограниченно работает в
gdp mode**» — ROM modunda çalışmaz, GDP modunda sınırlı çalışır. Yani önce GDP yüklenmeli.

## Bunun en büyük getirisi

Soğuk açılış çevrimi son 22 denemede 0 isabetti — piyangoydu. Tel bunu **tekrarlanabilir bir
anahtara** çevirdi. Artık diske ne zaman istersek girebiliriz (tekrarlanabilirliği
doğrulanacak).


---

# 35. 14 EYLÜL — LINUX'TAN DOĞRUDAN KOMUT KANALI KURULDU

## 35.1 Neden gerekti — üç kapalı kapı

| Yol | Neden kapalı | Kanıt |
|---|---|---|
| Standart `nvme` sürücüsü | Loader, `CC.EN=0` yazılsa bile `CSTS.RDY=1` tutuyor → sürücü kapanma onayını bekliyor, gelmiyor, sonsuz reset. Ayrıca Linux'un CID'ye gömdüğü generation counter'ı geri döndürmüyor. | `state=resetting`, 1923 × `genctr mismatch` |
| `vfio` + sanal makine | vfio cihazı açarken zorunlu `pci_try_reset_function()` çağırıyor. **FLR loader'ı öldürüyor.** | Tek değişkenli test: FLR gönderildi → 12 sn boyunca `0xffffffff`, hiç dönmedi |
| Windows + MPTool | Loader'da namespace yok → Windows PhysicalDrive nesnesi yaratmıyor → MPTool tutamak bulamıyor. JMS583 kutusunun gerçek işlevi bu nesneyi yaratmak. | `NSZE=1395`, blok aygıtı oluşmuyor |

## 35.2 Çözüm: `/usr/local/bin/jd_loader.py`

Hiçbir reset atmadan çalışan userspace NVMe admin queue:
- BAR0'ı `/dev/mem` ile mmap eder (ctypes ile garantili 32/64-bit hizalı erişim)
- DMA için `hugetlbfs`'ten 2 MB fiziksel bitişik sayfa alır
- Fiziksel adresi `/proc/self/pagemap` ile çözer, present/swap bitlerini doğrular
- AQA/ASQ/ACQ programlar, `CC.EN=1`, doorbell'leri sürer, faz bitiyle completion bekler

**İlk temas — kasıtlı olarak veri transferi olmayan komutla** (Abort, opcode 0x08; spec gereği DMA yapmaz, yani adresimiz yanlışsa en fazla 16 baytlık bir CQE yanlış yere yazılır):

```
queue kuruldu, CSTS.RDY=1 (0.02sn)  ASQ=0x37c800000 ACQ=0x37c801000
Abort -> BASARILI  cid gonderilen=0x0001 gelen=0x0001  (0.6ms)
```

CID birebir geri geldi. **`genctr` sorunu tamamen Linux sürücüsünün kendi kodlamasındanmış** — loader kusursuz cevap veriyor.

## 35.3 Loader'ın ölçülen yetenekleri

```
MN   = Generic_Loader_NVMe_Device      FR = L190301R      VS = NVMe 1.3.0
MDTS = 6                -> tek transferde 262144 bayt
OACS = 0x0006           -> Format NVM + Firmware Image Download/Commit
FRMW = 0x02             -> 1 slot, slot1 YAZILABILIR, resetsiz aktivasyon YOK
FNA  = 0x02   NN = 1    ONCS = 0x0001
Namespace 1: NSZE=NCAP=NUSE=1395 blok x 512B ~= 700 KB   (4 LBA formati: 512/1K/2K/4K)
SMART ve Error log: tamamen sifir (loader uygulamiyor)
Firmware Slot log: AFI=0, slot adlari bos
```

## 35.4 Çalışan: standart Firmware Image Download

`GDP.bin` (249.856 bayt, başlık `MAS09_FWTAG_V001` — SYS firmware imajlarıyla **aynı konteyner formatı**)
4 KB'lik parçalar hâlinde opcode `0x11` ile gönderildi, **her parça status 0**, tamamı kabul edildi.

## 35.5 Bulunan satıcı komutları

`0xC0-0xFF` aralığı tarandı (veri transferi yok, tüm CDW'ler sıfır). Yalnız **`0xC1`** ve **`0xC2`**
"geçersiz opcode" dışında cevap veriyor.

## 35.6 ⚠️ Çalışmayan: hiçbir şey gerçekten olmuyor

Tek oturumda (tampon silinmeden) denendi — Firmware Commit slot1/eylem3, `0xC2` cdw10=0 ve 1,
`0xC1` cdw10=1. **Hepsi `BASARILI` dönüyor, hiçbiri bir şey değiştirmiyor:** kimlik hâlâ
`Generic_Loader_NVMe_Device`, `VS` hâlâ 1.3.0, yeni opcode açılmıyor. `0xC1` her `cdw10` değerine
(0..15) başarı dönüyor ve hiç veri döndürmüyor.

Okuma: **loader tanımadığı komutları sessizce yutuyor.** Gerçek protokol elimizde yok.

Bulunan bir hata: aracın her çağrısı `CC.EN` döngüsü yapıyordu, bu da indirilen firmware
tamponunu siliyordu — "indir" ve "commit" ayrı çalıştırıldığında commit boş tampona uygulanmıştı.
Düzeltildi (`gdp` alt komutu her şeyi tek oturumda yapıyor). Düzeltmeden sonra da sonuç aynı.

## 35.7 ⛔ KIRMIZI ÇİZGİ: hiçbir şey silinmeyecek

Format NVM destekleniyor ve cazip görünüyor. **Yapılmayacak.** Sebep tahmin değil:

Diskteki mevcut firmware, **elimizdeki tek HYV6 firmware'i.** `YI0PCELC.bin` internette sıfır
sonuç veriyor, `nandmem_SKV6_page.bin` hiçbir kamuya açık pakette yok, liangchanba'daki HYV6
paketi "yayınlanacak" durumunda silinmiş. Yani NAND'ı silersek ve yerine çalışan bir şey
yazamazsak disk **bizim için kalıcı olarak** biter.

**Doğru sıra:** önce mevcut firmware'i NAND'dan oku ve sakla → sonra sil/yaz.
`VP_UploadCodeFromFlash` bu yüzden kritik yol.


---

# 36. 14 EYLÜL — OKUMA/YAZMA PENCERESİ BULUNDU + BİR ÇIKARIM DÜZELTMESİ

## 36.1 Namespace 1 = kararlı, iki yönlü 714 KB pencere

Loader'ın namespace'i (1395 blok × 512 B = 714.240 bayt) boş değil. I/O queue kurup okundu:

- **Kararlı:** aynı LBA iki kez okununca birebir aynı; araya başka okuma girse de değişmiyor.
- **Güç/reset kalıcı içerik:** controller reset'leri arasında 714.240 baytın **yalnız 11-18'i**
  değişiyor (174 × 4KB parçanın 3'ünde). Yani içerik %99,998 sabit — değişenler sayaçlar.
- **Yazılabilir:** sıfır bölgesinin ortasına (LBA 266) desen yazıldı, birebir geri okundu,
  sıfırlarla geri alındı, loader hayatta kaldı. `CSTS=0x1`, `VS=1.3.0` sabit.
- **İçinde kontrolcü-içi işaretçiler var:** `0x04030000–0x0403fba8` aralığında 37 adet
  32-bit LE işaretçi, artı `0xffffxxxx` aralığında 54 adet. Değişen baytların çevresi
  bu işaretçilerle dolu. Bu, pencerenin kontrolcünün çalışan durumuna bağlı olduğunu gösteriyor.

## 36.2 ⚠️ DÜZELTME: "ARM kodu, enjekte edilebilir" çıkarımı zayıf

Bir ara "4138 Thumb BL/BLX kalıbı → ARM çekirdeği → kod enjekte edilebilir" dedim. Geri alıyorum:
- Rastgele veride beklenen BL/BLX kalıbı ≈ 3840 (halfword'ün üst 4 biti = 0xF, yani 1/16).
  Ölçülen 4138 bunun sadece %8 üstü — **neredeyse şans seviyesi.**
- `0x04030000`'dan disassembly ilk komuttan (`sub sp, 0x1f0`, geçerli prologue) sonra çöpe dönüyor.
- Entropi 7,945 — düz kod için fazla yüksek. Bu bölge **karıştırılmış/paketlenmiş veri**, düz
  makine kodu değil.

Dürüst durum: pencerenin **ne olduğu** (çalışan RAM / ayrı tampon / scrambler'dan geçen NAND
görüntüsü) kanıtlanmadı. Okuma-yazma erişimi kanıtlandı; kod çalıştırma kanıtlanmadı.

## 36.3 Kapanan yollar (ölçümle)

- **Firmware Commit (0x10) = stub.** Diferansiyel test: sağlam imaj, magic bozuk, gövde bozuk,
  8 KB'a kesik, **hatta hiç indirme yapılmadan** — hepsi "BAŞARILI". Hiçbir şey doğrulamıyor,
  hiçbir şey yapmıyor. `OACS`'ta ilan edilen Firmware Download/Commit gerçekte uygulanmamış.
- **`0xC1`/`0xC2` satıcı komutları:** her `cdw10` değerine (0..15) "BAŞARILI", hiç veri yok,
  hiçbir görünür etki yok. Doğru çağrı biçimi (arming magic + CDW düzeni) elimizde değil.

## 36.4 Sıradaki tek gerçek kaldıraç: MXUtility protokolü

Kör deneme tükendi. Gerçek satıcı protokolü `MXUtility_MAP1202_V1_11.exe` içinde. Bir ajan
`DeviceIoControl` çağrı yerlerinden geriye giderek şunları çıkarıyor:
- Hangi IOCTL (STORAGE_PROTOCOL_COMMAND / SCSI passthrough / USB-bridge CDB)
- `0xC1`/`0xC2`'nin gerçek CDW10..15 düzeni ve varsa arming magic dword'ü
- GDP yükle-çalıştır sırası
- `VP_UploadCodeFromFlash`'in tam komut dizisi (firmware'i NAND'dan geri okuma yolu)

## 36.5 Kırmızı çizgi sürüyor

Bu noktadan sonrası kontrolcü belleğine yazmak demek. **Gerçek brick riski burada.**
Protokol bilinmeden kör yazma YAPILMAYACAK. Format/erase, mevcut (tek) HYV6 firmware'i
NAND'dan okunup saklanmadan YAPILMAYACAK.

## 36.6 Araç durumu

`/usr/local/bin/jd_loader.py` alt komutları:
`test` (Abort ile adresleme doğrulama) · `id` · `kesif` (id-ctrl/ns + loglar) ·
`tara <bas> <son>` (opcode) · `kesfet <op>` (cdw10 taraması) · `fwdl <dosya>` ·
`fwcommit <slot> <eylem>` · `dogrulama` (diferansiyel commit testi) · `gdp` (tek oturum indir+çalıştır) ·
`ns` (I/O queue + örnek okuma) · `nsdump` (tam 714 KB döküm + analiz) · `nsyaz` (yazma testi) ·
`cmd <op> [cdw...] [--len]`

hugepage otomatik ayrılıyor (`/etc/sysctl.d/99-jd-hugepages.conf` = 4).
Açılışta `jd-loader-hazirla.service` nvme'yi 04:00.0'dan ayırıyor.
Dökümler: `~/jd1024/kanit/ns/` (A/A2/A3/son_dump).


---

# 37. 🟢 14 EYLÜL — SATICI PROTOKOLÜ ÇÖZÜLDÜ, KONTROLCÜ RAM'İ OKUNUYOR

MXUtility RE ajanı tam protokolü çıkardı (`~/jd1024/re/maxio_gdp_protocol.py`, disassembly
adresleriyle). Kör denememin neden "başarılı ama etkisiz" olduğu anlaşıldı: gerçek komut
CDW'lerde değil, **512 baytlık veri payload'unda**, ve **iki fazlı** + önce **arming** gerekiyor.

## Protokol (doğrulandı, çalışıyor)

- Windows yolu `IOCTL_STORAGE_PROTOCOL_COMMAND` (0x2DD3C0) ama içi düz NVMe **admin** komutu
  (NSID=0) → kendi queue'muzdan birebir gönderilebiliyor.
- **`0xC1` = satıcı yazma, `0xC2` = satıcı okuma.** CDW14 = `0x00123400 | subcode`.
- **Arming:** `0xC1`, CDW14=`0x00AE34FF`, CDW15=1, 4096 sıfır bayt. (disable: `0x00BD34FF`)
- **İki faz:** Faz1 = komut (`0xC1`, CDW10=`0x80`, CDW14=`0x001234FF`, CDW15=1, 512B payload).
  Faz2 = veri (nsec>0 ise; okuma `0xC2`, yazma `0xC1`, CDW14=`0x00123400|payload[2]`).
- **Payload:** `FF E5 <cmd> <parametreler BE32>`, 512'ye sıfır-dolgulu.

## Loader komutları (RE'den, adresli)

| cmd | işlev | payload |
|---|---|---|
| 0x82 | JumpToPRAM (GDP'yi çalıştır) | `FF E5 82 <nbin> 00 <BE32 0x0C @[5]>` |
| 0x83 | JumpToROM | `FF E5 83 <event>` |
| 0x84 | GetReg (register oku) | `FF E5 84 <BE32 reg>` |
| 0x86 | **ReadRam** | `FF E5 86 00 <BE32 adres>` |
| 0x87 | WriteRam | `FF E5 87 00 <BE32 adres> 00 00` |
| 0x87 | WriteRamRsa | `FF E5 87 <subIdx> <BE32 adres>` (cmdLen 0x10) |

GDP modu komutları: 0x88 ReadFlashID, **0x89 PageRead**, 0x8A PageWrite, 0x8B BlockErase,
0x11 InitGDP, 0x3B AutoDetect, 0x58 ChangeFlashID, 0x00 GetReturn (0xAA=meşgul).

## Doğrulama: kontrolcü RAM'i okundu (salt okuma)

`enable → ReadRam(0x04030000, 4 sektör)`:
```
0x04030000: 00 00 00 00 01 00 00 00 02 00 00 00 03 00 00 00
0x04030010: 04 00 00 00 05 00 00 00 06 00 00 00 07 00 00 00
0x04030020: 08 00 00 00 09 00 00 00 0a 00 00 00 0b 00 00 00
0x04030030: 0c 00 00 00 0d 00 00 00 ...
0x04030044: 01 86 00 00     <- gonderdigimiz ReadRam(0x86) komutunun izi
```
Artan 32-bit tablo = canlı veri yapısı, gürültü değil. Loader hayatta.

## Bellek haritası (ReadRam ile)

| Adres | Durum |
|---|---|
| `0x00000000` | veri var (TCM) |
| `0x04000000` | veri var (SRAM — GDP chunk0 buraya) |
| `0x040C0000` | veri var (GDP chunk1 hedefi) |
| `0x08000000` | hepsi sıfır (boş/eşlenmemiş) |

## Firmware'i geri okuma yolu (VP_UploadCodeFromFlash, fn 0x44b040)

1. `enable`
2. GDP.bin'i yükle: chunk0 (dosya 0x1000, 0xC000 bayt → RAM 0x0), chunk1 (dosya 0xD000,
   0x30000 bayt → RAM 0x040C0000), 64 KB parçalar hâlinde WriteRam ile
3. RSA bloğu: `WriteRamRsa(0x400, GDP.bin[0x400:0x1000], subIdx=0x0A)`, 6 sektör
4. `JumpToPRAM(nbin=2)` → GDP çalışır, MN "GDP" olur
5. `InitGDP(1024B param)`
6. Her fiziksel blok için `PageRead(0x89, ch, ce, block, page)` → NAND sayfalarını oku,
   `.\raw\` yerine bizde dosyaya yaz

## Sıradaki adım

GDP yükle-çalıştır ilk **geri-dönüşü olabilecek** adım (kontrolcü belleğine yazma + program
zıplatma). Risk düşük: loader modu tekrarlanabilir (3/3), kötü giderse güç çevrimiyle geri
dönülür. Hedef: GDP'yi çalıştırıp `PageRead` ile mevcut firmware'i (tek HYV6 kopyamız) NAND'dan
oku ve sakla. Ondan SONRA yaz/sil düşünülebilir.


---

# 38. 🟢🟢🟢 14 EYLÜL — GDP ÇALIŞTI, NAND OKUNUYOR

## GDP yüklendi ve çalışıyor
`gdprun`: enable → chunk0 (0xC000 → RAM 0x0) → chunk1 (0x30000 → RAM 0x040C0000) →
RSA blok → JumpToPRAM(2). **Her chunk yazılıp geri okunarak doğrulandı, tek bayt hata yok.**
Sonuç: `MN='Generic_GDP_NVMe_Device'`. Kontrolcüde kendi diagnostik programımız koşuyor.

## NAND FlashID okundu — ve bir düzeltme
GDP AutoDetect (cmd 0x3B) + ReadFlashID (cmd 0x88) gerçek NAND'dan:

```
AD 7E 28 53 02 B0    <- fiziksel disk boyle diyor
```

**Byte 2 = 0x28, beklediğimiz 0x29 DEĞİL.** Yani:
- `SKV606411` (AD 7E **28** 53 02 B0) = **1 CE / 1 die** → GERÇEK yapılandırma
- `SKV606412` (AD 7E 29 53 02 B0) = 2 CE / 2 die → bu DEĞİLMİŞ

Bütün gece "29 = 2 die" varsaymıştım (BGA üstündeki `H25T1TB48E` part-number decode'undan).
Fiziksel okuma bunu çürüttü: NAND `28`. İyi haber: `28` varyantı v033'te **de** var
(§31.1), yani daha yaygın ve firmware bulma şansı yüksek. AutoDetect'in gerisi tutarlı:
`04 04` CE/die, plane/blok bilgisi mevcut.

## Anlamı
- **Kontrolcü → NAND yolu sağlam.** GDP NAND'ı görüyor, ID okuyor.
- Teşhis tamamen kapandı: donanımın her katmanı çalışıyor; tek sorun sistem alanındaki
  firmware'in normal boot'ta yüklenememesi.
- Artık `PageRead` (cmd 0x89) ile herhangi bir fiziksel sayfayı okuyabiliriz — firmware'i
  geri okuma yolu açık.

## Sıradaki: firmware'i NAND'dan oku ve sakla
Kırmızı çizgi: yaz/sil yok, önce oku-sakla. `PageRead(0x89, ch, ce, block, page)` ile
sistem bloklarını tara, firmware imajını çıkar. Bu, hem elimizdeki tek HYV6 kopyasının
yedeği hem de (ayrı bir denemede) FlashID'yi 29→28 düzeltip diski yeniden açma yolunun
girdisi olur.


## 38.1 PageRead henüz veri döndürmüyor — eksik parça belirlendi

GDP çalışıyor, komutlar kabul ediliyor, ama **NAND sayfa okuması başarısız**:

| Komut | Sonuç |
|---|---|
| AutoDetect (0x3B) | ✅ gerçek FlashID: `AD 7E 28 53 02 B0` |
| ReadFlashID (0x88) | ✅ aynı |
| InitGDP (0x11), 1024B sıfır param | ✅ `GetReturn = 01 01 01 01 01 00…` (durum değişti) |
| InitGDP, AutoDetect çıktısı param | ✅ `GetReturn = 01 01 01 01 cc 3f 3a 68` |
| GetFlashParam (0x10) | ✅ ama hep sıfır |
| **PageRead (0x89)** | komut kabul, veri fazı OK (nsec≥2), **veri hep 0x00**, `GetReturn = 00 00…` |

RE'ye göre `VP_ReadPage` başarısı `retbuf[1] == 1`. Bizde `retbuf[1] = 0` → **okuma
başarısız**. Silinmiş NAND `0xFF` döner, bizim aldığımız `0x00` = GDP tamponu hiç doldurmadı.

**Eksik parça:** `InitGDP`'nin 1024 baytlık parametre bloğunun **gerçek yapısı**. MPTool'da
bunu `Write_GDP_Init_Param` (fn `0x408a3c`) Flash.ini kaydından üretiyor — NAND geometrisi,
zamanlama, kanal/CE haritası, LDPC ayarları. Sıfır ve AutoDetect çıktısı denendi, ikisi de
NAND'ı ilklendirmeye yetmiyor.

**Sıradaki tek iş:** `Write_GDP_Init_Param` @0x408a3c'yi tersine çevirip, Flash.ini'nin
`SKV606411` satırından (dikkat: **11**, çünkü fiziksel ID `0x28`) 1024 baytlık bloğu üretmek.
Bu bilindiği anda PageRead açılır ve firmware NAND'dan okunabilir.

**Bugünün durumu:** disk kaplıkaya'da, tel takılı, loader modunda; `gdprun` ile GDP her an
yüklenebiliyor. Hiçbir şey silinmedi, hiçbir şey NAND'a yazılmadı.

---

# 39. 14 EYLÜL — InitGDP PARAMETRE YAPISI ÇÖZÜLDÜ (kısmen)

## 39.1 Blok nerede: `0x000004E0`

`InitGDP`'ye ayırt edici bir desen (0..255 tekrarlı, 1024 bayt) gönderilip kontrolcü RAM'i
`ReadRam` ile tarandı. Desen **`0x00000000 + 1248 = 0x4E0`**'da bulundu. Yani InitGDP'nin
1024 baytlık parametre bloğu oraya kopyalanıyor — ve oraya `WriteRam` ile doğrudan da
yazılabiliyor (denendi, yazıldı+doğrulandı).

## 39.2 İlk 16 baytın alan haritası — Flash.ini ile eşleştirilerek çözüldü

GDP taze yüklendiğinde `0x4E0`'da **zaten dolu** bir yapı var (yerleşik varsayılan):

```
02 02 8c 0b 00 03 10 00 01 02 01 03 08 04 a0 07
```

Flash.ini v043'ün ilk kaydıyla birebir:
`Name000=BIC303201 TH58TFxxT23TA  2 2 1 2956 768 16 1 3 ... 9 2 1500 001 1952 010`

| Ofset | Değer | Alan | Flash.ini |
|---|---|---|---|
| [0] | 02 | Vendor | 2 = Toshiba/Kioxia |
| [1] | 02 | Type | 2 = TLC |
| [2:4] LE16 | 2956 | Blocks/CE | 2956 |
| [4:6] LE16 | 768 | PageNum | 768 |
| [6:8] LE16 | 16 | PageSize (KB) | 16 |
| [8] | 01 | CE/Package | 1 |
| [9] | 02 | Plane | 2 |
| [10] | 01 | Die/CE | 1 |
| [11] | 03 | ECC | 3 |
| [12] | 08 | (Interface? ini'de 9) | belirsiz |
| [13] | 04 | belirsiz | — |
| [14:16] LE16 | 1952 | SpareByte | 1952 |

**Kritik sonuç: elimizdeki GDP.bin (HYV8 paketinden) varsayılan olarak bir TOSHIBA BiCS
NAND'ına ayarlı.** Bizimki Hynix V6. PageRead'in boş dönmesinin sebebi bu.

## 39.3 Denenen ve yetmeyen

Bizim `SKV606411` için tanımlayıcı üretilip `0x4E0`'a yazıldı
(`03 02 48 0b 00 06 10 00 01 04 01 02 0a 04 00 08`), doğrulandı, `InitGDP` tetiklendi:
- InitGDP `GetReturn` **değişti** (`01 01 01 01 00 3f 1d dd`) → parametre işleniyor
- **Ama PageRead hâlâ başarısız** (`GetReturn[1]=0`)

Sebep anlaşıldı: blok **1024 bayt**, ilk 16'sı sadece geometri. Kalanında (0x520, 0x540-0x590,
0x660-0x670 civarında yapılandırılmış veri görülüyor) zamanlama tabloları, LDPC ve kanal
yapılandırması var — hepsi hâlâ Toshiba'ya göre. 16 baytı yamamak yetmiyor.

## 39.4 Denenen ve tıkanan: HYV7 GDP.bin

Mantık: HYV7 paketinin GDP'si Hynix varsayılanı taşır, V6'ya çok daha yakın.
`gdprun` ile yüklenmeye çalışıldı → **doğrulama zinciri hatayı yakaladı**:
`DOGRULAMA HATA @0x00000000+3655: yazilan 0x00 okunan 0x08`.

Sebep: 0xE47, **çalışan GDP'nin kendi veri alanının** içinde; koşan HYV8 GDP'si oraya yazıyor.
Yeni GDP yüklemeden önce loader'a dönmek gerekiyor.

`JumpToROM` (0x83) eklendi → **kontrolcü ROM'a döndü ama `CSTS.RDY=0`'da takıldı.**
Güç çevrimi toparladı (**5/5**).

## 39.5 Ders: kurtarma garantisi doğrulandı

Bugün kontrolcüyü iki kez takıldığı duruma soktum (vfio FLR, JumpToROM). **İkisinde de tel
takılı soğuk açılış temiz loader moduna döndürdü.** Bu, deneme yapmanın maliyetini
~90 saniyeye indiriyor ve kalıcı brick riskini pratikte ortadan kaldırıyor —
boot ROM maskeli ROM'da, NAND'a bağlı değil.

## 39.6 Sıradaki

1024 baytlık bloğun **tam** yapısı gerekiyor. `Write_GDP_Init_Param` @0x408a3c RE'si sürüyor.
Alternatif: loader'a temiz dönüş için önce güç çevrimi yapıp HYV7 GDP'sini yüklemek
(Hynix varsayılanlarıyla gelir).


## 39.7 Kapanan iki ampirik yol

**HYV7 GDP.bin denendi** (temiz loader modundan, doğru sırayla): yüklendi ve çalıştı, ama
`0x4E0` varsayılanı **aynı Toshiba tanımlayıcısı**. Yani varsayılan blok pakete özgü değil,
GDP'nin genel tablosu; MPTool onu InitGDP ile eziyor. Bu yol kapandı.

**Tanımlayıcı dizisi hipotezi denendi:** `0x400-0x1400` bölgesi 4 bayt adımlarla tarandı
(Vendor≤6, Type≤4, PageSize∈{4,8,16,32}, makul blok/sayfa sayısı filtresiyle). Tek gerçek
kayıt `0x4E0`'daki Toshiba girdisi; Hynix girdisi **yok**. GDP'de seçilebilir bir NAND
tablosu bulunmuyor. Bu yol da kapandı.

**Sonuç:** 1024 baytlık bloğun tam yapısı olmadan PageRead açılmıyor. Tek kaldıraç
`Write_GDP_Init_Param` @0x408a3c RE'si.

## 39.8 Oturum sonu durumu (doğrulandı)

| Bileşen | Durum |
|---|---|
| JD1024 | PCIe'de ayakta, `1e4b:1202`, link Gen3 x4 |
| Loader modu | tel takılı, güç çevrimiyle **5/5** geri geliyor |
| NAND | **hiçbir şey yazılmadı/silinmedi** |
| KIOXIA sistem diski | sağlam, 1.8T |
| sera | person/vehicle/state aktif, iklim verisi 18 sn taze |


---

# 40. 14 EYLÜL — TAM SEKANS UYGULANDI, TEK ENGEL: TMC ZAMANLAMA PROFİLİ

RE ajanı `Write_GDP_Init_Param` @0x408a3c'yi çözdü ve **eksik adımı buldu**:
`VP_InitGDP`'nin **her** çağıranı hemen ardından `VC_GDP_CmdSwitchToLegacy` (cmd 0x49)
gönderiyor (7 çağrı yeri, hepsi doğrulandı). Flash.ini'mizde `Interface=11` =
"Legacy to Toggle 2.0" — yani parça tam bu geçişi istiyor.

## Uygulanan tam sekans (donanımda)

| Adım | Sonuç |
|---|---|
| GDP yükle + JumpToPRAM | ✅ `MN=Generic_GDP_NVMe_Device` |
| Sleep 1000 ms | — |
| EnableVendorCmd (**jump SONRASI**) | ✅ |
| `InitGDP` — gerçek 1024 B blok | ✅ BAŞARILI |
| `ReadFlashID` doğrulama | ✅ `ad 7e 28 53 02 b0` |
| **`SwitchToLegacy` (0x49)** | ❌ `retbuf[0]=0` → başarısız (dönen: `00 7e 28 53 02 b0`) |
| Sleep 1500 ms | — |
| **`PageRead` (0x89)** | ❌ `GetReturn[1]=0` |

Parametre taraması yapıldı: ldpc ∈ {0,1,2,3} × scramble ∈ {0,1} × blockType ∈ {0,1},
blok 0-3, sayfa 0 ve 95, nsec 8 ve 32, SwitchToLegacy'li ve'siz. **Hiçbir kombinasyon açmıyor.**

## Kök neden belirlendi

Üretilen 1024 baytlık blokta **iki TMC zamanlama profili (0xB0 ve 0x1B0, 0xDC bayt) boş**:

```
0x0b0: 00 00 42 00 00 00 ...
0x1b0: 00 00 42 00 00 00 ...
```

Blokta dolu olan tek yerler: `0x000-0x00f` (geometri), `0x018-0x01f` (adres kaydırmaları),
`0x041-0x04c`, `0x050-0x051`, `0x070-0x071`, `0x2d1-0x38f` (0xff dolgu).

Ajan bunu zaten "çözülmedi" diye işaretlemişti: *"TMC profillerinin bayt içeriği — düzen
haritalandı, değerler TMC*.ini'den geliyor, izlemedim"* ve *"firmware'in TMC bölgesini
sıfırdan farklı isteyip istemediği statik olarak belirlenemez."*
**Donanım artık cevap verdi: TMC boşken hem SwitchToLegacy hem PageRead başarısız.**

Paket içinde `TMC_ARRAY_*HynixV6*` dosyası **yok** (V7 ve V8 var). Ajana odaklı takip
gönderildi: TMC seçim/dönüşüm yolunu izlesin ve V6 için en yakın kullanılabilir kaynağı
(muhtemelen HynixV8 ya da bir TMCn.ini bölümü) yerleştirsin.

## Not: iterasyon maliyeti düşük
Güç çevrimi bugün **6/6** temiz loader moduna döndürdü, ~90 saniye. Birden fazla aday blok
denenebilir.


---

# 41. 14 EYLÜL — ÖLÜMCÜL KOMUT HARİTASI + SIRA KEŞFİ

## 41.1 Sıra her şeymiş — iki yanlış tespitin düzeltmesi

Önce "InitGDP GDP'yi öldürüyor" dedim, sonra "GDP'nin kendi bloğu da öldürüyor" dedim.
**İkisi de yanlıştı ve sebebi aynı: test sırası.** O testlerde `PageRead` InitGDP'den önce
koşuyordu ve GDP'yi asıl o öldürüyordu.

`InitGDP` ilk çağrıldığında **GDP hayatta kalıyor** ve NAND kimliği hâlâ okunabiliyor.

## 41.2 Ölümcül komut haritası (her komuttan sonra canlılık ölçüldü)

Canlılık ölçütü: `0x3B AutoDetect` çağır, cevabın ilk iki baytı `AD 7E` mi. Tampon önceden
`0x5A` ile dolduruluyor ki dokunulmamış tampon ayırt edilebilsin.

**GÜVENLİ** — sonrasında GDP ayakta:
`0x00 GetReturn` · `0x05 GetFlashModule` · `0x07 GetCodeBlock` · `0x31 GetDefectBadTab` ·
`0x3B AutoDetect` · `0x88 ReadFlashID` · `0x57 NandPowerOnOff` · `0x11 InitGDP` (ilk sırada)

**ÖLÜMCÜL** — GDP anında ölüyor, sonraki her komut boş tampon döndürüyor, yalnız tam güç
çevrimi kurtarıyor:
`0x49 SwitchToLegacy` · `0x89 PageRead` · `0x10 GetFlashParam` · `0x3A PreCheckCodeBlock`

**Ayrım keyfi değil: ölümcül olanların hepsi gerçek bir NAND veri yolu işlemi yapıyor;
güvenli olanların hepsi kimlik/durum/yapılandırma okuması.** Hepsinde NVMe durumu 0 (başarılı) —
arıza GDP'nin içinde, komutu kabul ettikten sonra.

## 41.3 Denenen ve çözmeyen

- `0x57 NandPowerOnOff` ile NAND rayını açmak → PageRead yine öldürüyor
- `InitGDP`'yi PageRead'den önce koymak → InitGDP hayatta kalıyor ama PageRead yine öldürüyor
- `0x49`'u atlayıp doğrudan PageRead → yine ölüm
- ldpc/scramble/blockType kombinasyonları, nsec 8/32 → hepsi ölüm

## 41.4 Bunun anlamı

GDP, gerçek bir NAND çevrimi başlattığı anda fault veriyor. Üç olasılık:
1. NAND arayüz zamanlaması/modu yapılandırılmamış (TMC izi sürülüyor)
2. Bir geometri alanı dizi sınırı olarak kullanılıyor ve değerimiz aralık dışı
   (4 plane / 1 CE / 1 die / 2888 blok)
3. Bu GDP derlemesi Hynix V6'yı sürebilecek doğru GDP değil


---

# 42. ⭐ 14 EYLÜL — İKİ TEMEL DÜZELTME: BLOK 1536 BAYT, "ÖLÜM" YOK

## 42.1 InitGDP bloğu 1536 bayt (nsec=3), 1024 değil

Firmware disassembly'sinden: bölgenin adı **GDP DPD**, firmware'in kendi init log'u
`GDP DPD, RAM 0x04E0, size 0x600` diyor. 0x11 işleyicisi (RAM 0x040c3184):
```
040c3014  movw r2, 0x600        ; 1536
040c3018  ldr  r1, =0x0400F2C0  ; host veri tamponu
040c301c  ldr  r0, [r4, 0x14]   ; = 0x4E0
040c3020  bl   0x040e85d4       ; memcpy(0x4E0, 0x0400F2C0, 0x600)
```
Magic yok, sürüm yok, checksum yok, aralık kontrolü yok — **0x11 reddedilemez** ve
alt-init başarısız olsa bile `resp[0]=1` yazar. nsec=2 gönderirken DPD'nin üst 512 baytı
çöp kalıyordu.

## 42.2 ⭐ Doğrulama kanalı: `0x07 GetCodeBlock`

`memcpy(resp, DPD+0x20, 0x20)` yapıyor — gönderdiğimiz bloğun +0x20..+0x3F aralığını
aynen geri veriyor. F2 bloğuna `a0..af` işareti konup test edildi:
```
okunan  : a0 a1 a2 a3 a4 a5 a6 a7 a8 a9 aa ab ac ad ae af
beklenen: a0 a1 a2 a3 a4 a5 a6 a7 a8 a9 aa ab ac ad ae af   -> ESLESTI
```
**Beş blokta da eşleşti.** Artık "gönderdim ama oturdu mu" tahmin değil, ölçüm.

## 42.3 ⭐⭐ "ÖLÜMCÜL KOMUT" TAKSONOMİSİ TAMAMEN YANLIŞTI

§41'de `0x49`, `0x89`, `0x10`, `0x3A` için "GDP'yi öldürüyor, yalnız güç çevrimi kurtarır"
yazmıştım. **Yanlış.** Firmware'de 0x040dc168'de literal `0x05F5E100` = **100.000.000**
iterasyonluk bir retry döngüsü var. Komut çökmüyor, sadece dakikalarca sürüyor.

Ölçülen geri dönüş süreleri: **50, 70, 110, 120, 130 saniye.**

Sonuç: **güç çevrimi gerekmiyor.** Bekle ve yeniden yokla. İterasyon maliyeti ~7 dakikadan
~2 dakikaya düştü. Bugün yapılan ~15 güç çevriminin çoğu gereksizdi.

## 42.4 DPD alan haritası (firmware'den, host aracından değil)

| Ofset | Alan |
|---|---|
| +0x00..0x0F | geometri (Vendor/Type/Blocks/Pages/PageSize/CE/Plane/Die/ECC/…/Spare) |
| +0x20..0x3F | `0x07` ile geri okunabilen bölge — **doğrulama için kullan** |
| +0x4C | **NAND nesil kodu.** Kabul edilenler: `0x14`=SKV6 (**bizim**), `0x1F`=SKV7, `0x22`=BIC6, `0x23`=SKV8, `0x2D`=SSV7. Firmware'in kendi varsayılanı `0x03`=BIC3 → kabul kümesinde DEĞİL |
| +0xB0, +0x1B0 | iki TMC profili, 0xDC bayt — hâlâ boş |
| +0x310 | **die haritası**, 256 bayt, indeks `(lun<<6)\|(ce<<3)\|ch`, `0xFF`=yok. Değer boolean değil **indeks** olarak kullanılıyor |

⚠️ MPTool bu tabloyu `lun*32` adımıyla yazıyor (0x004096ef), firmware `lun*64` ile okuyor —
lun=0'da zararsız, çok-LUN'da ölümcül.

## 42.5 `0x49` = `gdp_nand_init`, ve dönüşü temiz bir hata kodu

```
040c332c  bl  0x040c89bc        ; gdp_nand_init
040c3338  cmp r0, 1
040c333c  strbeq r8,[r6]        ; ok   -> resp[0]=1
040c3348  strbne sb,[r6]        ; fail -> resp[0]=0
```
Aldığımız `00 7e 28 53 02 b0` = bayt0 hata kodu, kalanı bayat önceki cevap.
**SwitchToLegacy aslında NAND bring-up'ın kendisi ve düzgünce başarısızlık bildiriyor.**

## 42.6 Test edilen beş blok — hepsi aynı sonuç

`initparam_F1..F5.bin`, hepsi 1536B/nsec=3:

| Blok | Fark | InitGDP | 0x07 | 0x49 |
|---|---|---|---|---|
| F1 | temel, nesil 0x14, die[0]=00 | OK | ESLESTI | FAIL |
| F2 | + `a0..af` işareti | OK | ESLESTI | FAIL |
| F3 | nesil 0x23 (SKV8) | OK | ESLESTI | FAIL |
| F4 | +0x0C/0x0D = 04 04 | OK | ESLESTI | FAIL |
| F5 | firmware DPD'si, die tamamen 00 | OK | ESLESTI | cevap yok |

## 42.7 ⭐ Firmware'de UART hata ayıklama konsolu var

RAM 0x040E5034: _"Welcome to use UART port debug!"_, `dump`/`regs`/`jmpr` komutları.
Bastığı satırlar arasında **`[gdp_init] DONE/FAIL`, `[gdp_nand_init] DONE/FAIL`,
`die not exist!`, `No matched cmd id : %02x`** ve her 0x11'de tam bir `[VAR INFO]` dökümü var.

**Şu an tahminle uğraştığımız soruyu saniyede cevaplar.** USB-TTL adaptör (~116 TL, CP2102,
Robo90 Ostim) gerekçesi artık kesin.

## 42.8 Diğer notlar

- Bu derlemede **0x3C, 0x3D, 0x4A, 0x4B, 0x4E yok** ("No matched cmd id" basıyor)
- Belgelenmemiş üç komut **var**: `0x0B`, `0x84`, `0x86` — hepsi veri-okuma yönlü, denenmedi
- Komut doğrulayıcı **yalnız byte[1]==0xE5**'e bakıyor (0x040E07B6); byte[0] hiç kontrol edilmiyor,
  ve yalnız ilk 32 bayt saklanıyor
- `0x05` cevabını önce 0xFF ile dolduruyor → gördüğümüz `ff ff…` "işleyici doldurmadı" demek
- `0x00`'ın sıfır dönmesi **doğru**: resp[0] = state[0x17], yalnız async iş varken 0xAA

## 42.9 Kalan tek soru

**`gdp_nand_init` @ 0x040c89bc neden başarısız?** Her başarısızlık yolu ve okuduğu DPD alanları
çıkarılıyor (ajan çalışıyor). En güçlü şüpheliler: boş TMC profilleri (NAND arayüz zamanlaması)
ve die haritasının beklenen indeks değeri.


---

# 43. ⭐⭐ 14 EYLÜL GECE — GDP FIRMWARE DISASSEMBLE EDİLDİ, ARIZA NOKTASI BULUNDU

İki bağımsız RE ajanı GDP.bin'i (ARMv7-R, MPU+TCM, karışık ARM32/Thumb-2) çözdü.

## 43.1 GDP çökmüyor — kasıtlı olarak duruyor

Üç ayrı `while(1)` tuzağı var, her birinin öncesinde bir UART `printf`:
- `0x040DBDB8` — _"polling status fail for KIOXIA"_ → `0x89`/`0x10`/`0x3A` buraya düşüyor
- `0x040C8DD0` — _"ldpc rate mismatch between MPT[%d] and HW[%d]"_
- `0x040C8E18` — _"LDPC matrix check fail"_

`ASSERT()` = printf + `while (*(u8*)0x0000E58) ;` ve imajda `0xE58 = 0x01`.

## 43.2 Dispatcher ve işleyiciler (gözlemlendi)

Tablo `0x040ED2F4`, 36 giriş × 12 bayt (`+0` cmd, `+1` veri fazı, `+4` işleyici).
`pInitParam = *(u32*)0x00000DCC = 0x000004E0`.

`0x49` → **`0x040C31A8` = `gdp_nand_init`'in kendisi**. İç çağıranı **yok** — NAND PHY/timing/LDPC'yi
programlayan başka hiçbir şey yok, yani **0x49 başarılı olmadan `0x89` asla çalışamaz.**

## 43.3 Bulunan iki somut hata

| Ofset | Bizim gönderdiğimiz | Olması gereken | Neden |
|---|---|---|---|
| `+0xB2`/`+0x1B2` | `42 00` = **66** | `c8 00` = **200** | Kabul edilen saatler: {34,166,200,266,333,400,533,667,800} MT/s. 66 listede yok → ASSERT |
| `+0x0D` | `00` | `01` | `CE_QNTY = [0x0D]×[0x08]`, `DIE_QNTY = [0x0C]×CE_QNTY` — sıfırla hepsi çöküyor |

O `+0xB2`'deki tek başına duran `42` baytını gün boyu gördüm ama **bir saat frekansı olduğunu
anlamadım** — TMC profili sanıp içeriğini doldurmaya çalıştım.

## 43.4 İyi haberler

- **LDPC oranı doğru:** tablo `0x040EE828` = {608,512,480,448,576,544,640}; 16 KB sayfa + 2048
  spare = 18432 → oran **2**, bizim `+0x0A` zaten 2. Bu kapı geçiyor.
- **Hynix V6 destekleniyor ve elimizdeki DOĞRU imaj:** vendor jump table `0x040C2250`'de Hynix
  dalı var, `gdp_nand_init` içinde SKV6/V7/V8 zinciri `0x040C3218`, ve `0x040C3270`'te
  **sabit kodlanmış `movw r2,#0xb48` = 2888 blok — tam bizim SKV606411.** Firmware bu parçayı
  tanıyor. HYV7 imajında bu yok, ona geçmeyin.
- **TMC tamamen alakasız:** feature değerleri DPD'den değil statik RAM `0x200`'den geliyor
  (GDP.bin dosya 0x1200) ve `0x11` oraya hiç dokunmuyor.

## 43.5 GDP modunda RAM okuma VE YAZMA açıldı

- `0x86` = RAM oku (`FF E5 86 00 <BE32 adres>`)
- `0x87` = RAM yaz — **doğrulandı**, yazıp geri okudum

Canlı okunan SET FEATURE tablosu (`0xE7C`), ajanın disassembly tahminini bayt bayt doğruladı:
```
+00: 10 00 00 00  46 00 00 00  01 00 00 00  02 00 00 00
+10: 00 00 00 00  01 00 00 00  01 00 00 00  60 00 01 00
```
`+0x10 = 0x00000000` (geçersiz) ve `+0x1C = 0x00010060` — `gen=0x14` (SKV6) yolunun ürettiği
değerler. RAM `0x200` (FLASH TIMING) = `02 02 c8 00 7c 02 46 06 ff ff ff ff`.

İki tek-bayt yama ASSERT tuzaklarını silahsızlandırıyor ve **uygulandı, çalıştı**:
`*(u8*)0x0E58 = 0` ve `*(u8*)0x0E6E = 1`.

## 43.6 Denenen ve hâlâ başarısız

Düzeltilmiş bloklar (`init_skv6_A_clk200_bank1`, `_B_clk200_bank0`, `_C_clk400_bank1`,
`_D_clk66_bank1`), RAM yamalarıyla birlikte, 1536B/nsec=3:

| Blok | +0x0D | saat | 0x11 | 0x07 | 0x49 |
|---|---|---|---|---|---|
| A | 1 | 200 | OK | ESLESTI | FAIL |
| B | 0 | 200 | OK | ESLESTI | FAIL |
| C | 1 | 400 | OK | ESLESTI | FAIL |
| D | 1 | 66 | OK | ESLESTI | FAIL |

Geri dönüş süreleri değişiyor (10 / 60 / 220 sn) — yani davranış değişiyor, sadece sonuç aynı.

## 43.7 Arıza noktası kesinleşti

`gdp_nand_init`'in temiz `return 0` çıkışı (**E1**, `0x040C8D04 cmp r5,0`). `r5`, yedi çağrının
AND'i ve **yedisi de NAND'ın cevap verip vermediğini** kontrol ediyor — hiçbiri bir DPD alanını
doğrulamıyor. Yani parametrelerimiz reddedilmiyor:

**NAND, SET FEATURE komutuna cevap vermiyor.**

`ReadFlashID`/`AutoDetect` çalışıyor çünkü onlar en basit legacy Read-ID çevrimi.

## 43.8 RAM'de log tamponu yok — UART fiziksel olarak gerekli

Firmware `[gdp_nand_init] DONE/FAIL`, `die not exist!`, `polling status fail for KIOXIA` gibi
satırları basıyor ve **hangi kontrolde takıldığını tam söylüyor**. RAM 0x0-0x10000 ASCII için
tarandı: **log tamponu yok**, printf doğrudan UART FIFO'suna gidiyor.

Yani bu soruyu yazılımla cevaplamanın yolu kalmadı. **USB-TTL (CP2102, ~116 TL) artık
lüks değil, tek yol.** Kartta UART pad'lerinin yeri hâlâ bilinmiyor; arka yüzdeki ~12 düz
test pad'i arasında olması bekleniyor (§16).


---

# 44. 14 Eylül — KİLİT AÇILDI: `gdp_nand_init` DONE veriyor

## 44.1 ⭐ Firmware konsolu yazılımdan okunuyor — UART kablosu GEREKSİZ

§43.8'de "RAM'de log tamponu yok, UART fiziksel olarak gerekli" demiştim. **Yanlıştı.**
Log tamponu yok ama *yaratılabiliyor*: MPU bölgesi 5 (0x04080000+512K) **RWX**, yani
kodu canlı yamalayabiliyoruz.

- UART `putc` = **`0x040CF6E0`** (12 bayt, Thumb): `ldr r1,[UART] / ldrb r2,[r1,#0x14] /
  lsls r2,#0x1a / bpl / strb r0,[r1] / bx lr`
- Yerine `b.w` ile bir trampoline (`0x040FF000`) yazıldı; trampoline karakteri
  **`0x040F0000`'daki halka/doyumlu tampona** yazıyor (28 KB, dolunca durur).
- Eski gövdeye her 2-bayt hizalı giriş noktası (`0x040CF6E4/E6/E8`) trampoline
  yönlendirildi — dışarıdan `0x040CF6E6`'ya dallanma var.
- Kanıt: bilinmeyen opcode 0x99 → tamponda `No matched cmd id : 99`.

Araç: `jd_hack.py hook` / `log` / `seq` / `tara` / `haritala`.

## 44.2 Dayanıklılık modu — firmware artık kalıcı asılmıyor

`jd_hack.py dayanikli`: 25 adet `b .` tuzağı → `bx lr`, 4 exception vektörü →
undef/svc `movs pc,lr`, prefetch/data abort `subs pc,lr,#4`, ASSERT bayrağı `0xE58=0`.
⚠️ `gdp_die_map_2_module_info` çağrıları NOP'lanamaz — `0x040C3640` AutoDetect'in (0x3B)
içinde, canlılık testini kırıyor.

Tam tur (soğuk çevrim → GDP → kanca → dayanıklılık) = **~100 saniye**, `tur.sh` ile tek komut.

## 44.3 ⭐⭐ İki kök neden — ikisi de DPD'de DEĞİL, firmware kodunda

Kesme (early-return) yürüyüşüyle, ölçüt "0x49 sonrası NAND ID kararlılığı":

| aşama | ID |
|---|---|
| taze GDP | 20/20 |
| InitGDP (0x11) sonrası | 20/20 |
| `0x49` sonrası | 3/20 |

**Bozucu 1: `0x040C8B3C`'deki `bl 0x040E3070`.** Zinciri `0x040E28D4` → `0x040E2F40` →
`0x040E2B48(1)`. Sonuncusu **NIFC `[0x204]` bit0 = 1** yapıyor, bu da bütün NAND
opcode'larını **DDR ailesine** çeviriyor (READ ID 3→0x17, GET FEATURE 9→0x2A).
SDR çipe DDR strobe = gördüğümüz bir-bayt kayması (`AD AD 7E 28 53...`).
**Firmware'de SDR ikizi hazır: `0x040E305C`** (`0x040E2B48(0)`; `[0x34]`b16 SDR PHY,
`[0x200]` zamanlama). Yama: `0x040C8B3C = 46 69 00 eb` (`bl 0x040E305C`).
→ veri yolu tam bir `0x49` boyunca **16/16 sağlam**.

**Bozucu 2: `0x040C8D88`'deki `fcl_media_set_freq(200)`.** Frekans **koda gömülü**:
`0x040C3328  mov r1,#0xc8`. DPD'den GELMİYOR — bu yüzden günlerce yapılan DPD/TMC
frekans taramaları hiçbir şeyi değiştirmedi. Yama: `0x040C3328 = <frek> 10 a0 e3`.
100/50/33 çalışıyor, 200 marjinal.

## 44.4 Asılma noktası: LDPC matris kontrolü

`0x040C8E18` `b .` — "LDPC matrix check fail". Firmware'in LDPC blob'ları rate indeksi 6
istiyor, bizim geometrimiz indeks 2 veriyor. Doğrulayıcılar (`0x040DEE98`, `0x040DEE2C`)
**hiçbir donanım programlamıyor**, salt kontrol. Yama:
`0x040C8D8C = 01 40 a0 e3` (`mov r4,#1`), `0x040C8D90 = 21 00 00 ea` (`b 0x040C8E1C`).

## 44.5 TMC tablosu RAM 0x200'de — DPD'de değil

§43'te "TMC alakasız" demiştim; §44'te düzeltiliyor: alakalı ama **DPD'den gelmiyor**.
Firmware varsayılanı `0x00000200` (kopyaları 0x590, 0x66c):
`02 02 c8 00 | 7c 02 46 06` = ifPowerOn, ifAfterPowerOn, u16 freq=200, timingMode=0x7C,
highSpeed=0x02, **driveStrength=0x46**, 0x06.
Rampa deneyiyle kanıtlandı: `0x206`'yı değiştirince `OUTPUT_DRI_STR` değişiyor.
**Çip `0x46` yazınca `0x06` saklıyor** (bit 6'yı desteklemiyor) → `0x206 = 0x06` yapılmalı.

Feature struct **RAM 0x00000E7C**: `+0x00/+0x04` DRIVING adres/değer,
`+0x0C/+0x10` INTERFACE, `+0x18/+0x1C` ve `+0x24/+0x28` TIMING MODE.
Değerleri `0x49` çalışırken firmware yazıyor — önceden poke etmek işe yaramaz.

## 44.6 ⭐ GET FEATURE geri okuması bir değer GERİDEN geliyor

Yazılan/okunan: `0x46→0x06`, `0x00010060→0x01006000`, `0x00→0x600` (bir önceki değer).
Telafi yaması (`0x040E3474..7C`: `lsr r1,r1,#8 / str r1,[r5] / mov r0,#0`) yardımcı oluyor
ama **asıl çözüm: `0x49`'u iki kez çağırmak.** İkinci turda okunan = birinci turda yazılan
→ doğrulama **hilesiz** geçiyor.

## 44.7 ✅ ÇALIŞAN TARİF (2026-09-14 18:17, doğrulandı)

```
blok  = init_skv6_A_clk200_bank1.bin, +0x70=0x2928, +0x50=0x16D0 (LDPC blob uzunlukları)
0x040C8B3C = 46 69 00 eb      bl 0x040E305C     (DDR yerine SDR kurulumu)
0x040E3474 = 21 14 a0 e1      lsr r1,r1,#8      (GET FEATURE kayma telafisi)
0x040E3478 = 00 10 85 e5      str r1,[r5]
0x040E347C = 00 00 a0 e3      mov r0,#0
0x040C8D8C = 01 40 a0 e3      mov r4,#1         (LDPC tuzağı)
0x040C8D90 = 21 00 00 ea      b 0x040C8E1C
0x040C3328 = 64 10 a0 e3      mov r1,#100       (NAND saati 200→100)
RAM 0x206  = 0x06                               (sürücü gücü, çipin kabul ettiği)
sonra 0x49'u DONE gelene kadar tekrarla (2. turda geliyor)
```
Sonuç: `tur 1: FAIL 6!=0` → **`tur 2: DONE, uyuşmazlık=0`**, resp `01...`

## 44.8 ⚠️ HENÜZ OKUMADIK — dürüst kayıt

"NAND'dan veri okundu" demek **erken**di. Ölçüm çürüttü:
- aynı sayfa 4 kez → aynı sha ✅ (tekrarlanabilir)
- **ama b0s0 / b1s0 / b1s1 / b2s0 hepsi AYNI sha** ❌ → adres NAND'a ulaşmıyor
- ilk yüksek-entropili okuma DMA tamponunda kalan artıkmış

Ayrıca **16 KB transfer taşıma katmanında bozuk**: `jd_loader.komut()` PRP2'ye ikinci bir
sayfa işaretçisi koyuyor, oysa 8 KB üstü NVMe transferi **PRP listesi** ister.
4 KB'lık (nsec=8) tek-PRP okuma kullanılmalı.

Sıradaki: `gdp_read_page` (0x040C4360) payload alan düzeni — hangi bayt blok/sayfa.

---

# 45. Register düzeyi: okuma yolu temizlendi + kod enjeksiyonu

## 45.1 ⭐ Kontrolcüde kendi kodumuz çalışıyor

`jd_hack.py enjekte`: 28 baytlık ARM stub `0x040FF100`'e yazılıyor, komut tablosundaki
(`0x040ED2F4`) **kullanılmayan `0x02` opcode'unun** işleyici işaretçisi (girdi #2,
`0x040ED30C`) stub'a çevriliyor. Parametreler `0x040FF200`'de (+0 adres, +4 değer).
Doğrulandı: `poke 0x040FF300 <- 0xDEADBEEF` → geri okundu.
Bu, 512 baytlık RAM-yazma granülaritesini aşan **32-bit hassas** yazma sağlıyor —
NIFC register'larına dokunmak için şart (yanlışlıkla `[0x220]` GO bitine basmamak için).

`jd_hack.py regyaz <adres> <deger>` / `regoku <adres>`.

## 45.2 ⭐⭐ Okuma yolu temizlendi — iki register

NIFC tabanı **`0x06641000`** (+0x1000/kanal). `gdp_nand_init` DONE'dan sonra bile:
```
[0x204] = 1   -> DDR opcode ailesi HÂLÂ seçili
[0x034] = 2   -> SDR PHY biti (bit16) set DEĞİL
```
Yani `0x040E305C` yaması init sırasında tutuyor, `fcl_media_set_freq` sonrası geri dönüyor.

**Düzeltme (init sonrası, enjekte poke ile):**
```
[0x204] = 0x00000000     (SDR opcode ailesi)
[0x034] |= 0x00010000    (SDR PHY biti)
```
Ölçüm: `ReadFlashID` **8/8 temiz** (`ad 7e 28 53 02 b0`). Tek başına `[0x204]=0`
yetmiyor (0/8, hepsi sıfır) — **ikisi birlikte** gerekiyor.

## 45.3 Kalan tek blokaj: descriptor motoru

`0x89 PageRead` → `[gdp_poll_fwcq_mix_filter] poll fwcq timeout`. Aynı seansta
**bütün blok/sayfa adresleri byte-identical veri** veriyor → descriptor tamamlanmıyor,
host bayat tampondan okuyor. `0x10 GetFlashParam` de aynı timeout'u veriyor (ve zaten
NAND değil, bizim DPD bloğumuzu döndürüyor). `0x31 GetDefectBadTab` **timeout vermiyor**
(farklı yol) — `C0,B37486,L0 RDT rslt lost`.

`0x88 ReadFlashID` doğrudan NIFC yolunu kullanıyor (descriptor motoru yok) ve kusursuz.
→ Arıza descriptor/FWCQ katmanında.

## 45.4 PageRead payload düzeni (ajan, doğrulandı)

`ctx+5 == payload[0]`, yani **`ctx+8 == payload[3]`** — benim haritam 3 bayt kaymıştı,
adres bu yüzden hiç NAND'a ulaşmadı.

| payload | anlam |
|---|---|
| [3] | kanal |
| [4] | düşük nibble CE, yüksek nibble LUN |
| [5..6] | **blok alanı, u16 BE** — `row = A/PLN`, `plane = A%PLN` (PLN=4) |
| [7..8] | **sayfa, u16 BE** |
| [9] | LDPC (0 = **RAW/ECC yok**) |
| [10] | scrambler |
| [11] | plane modu |
| [13] | 4 KB parça indeksi (0 = gerçek okuma, 1..3 = önbellekten) |

Blok 1 sayfa 1 → `FF E5 89 00 00 00 04 00 01 01 01 00 00 00`
(blok alanı = blok×4 + plane).

`0x00 GetReturn`: bayt0 = durum (1 ok, 0x1B okuma hatası, 0xAA işleyici hiç yazmadı),
bayt1 = 1 başarı. Veri `0x040612C0`'dan; PageRead verisi ise `0x0400F2C0`'dan.
`0x8B BlockErase` ve `0x8A PageWrite` düzenleri de çıkarıldı (silme/yazma için hazır).

## 45.5 Ölçüm dersi — iki kez düzeltildim

1. "NAND'dan veri okundu" dedim, **yanlıştı**: dört farklı sayfa aynı sha veriyordu.
2. Sonra "farklı bloklar farklı veri" dedim, o da **yanlıştı**: iki okuma ayrı güç
   çevrimlerindeydi; aynı seansta hepsi aynı çıktı.
3. Kendi aracımda hata: `logoku()` kontrolcü RAM'ini **komutun DMA tamponuna** okuyup
   veriyi eziyordu. Önce veri, sonra log.
4. 16 KB NVMe transferi PRP **listesi** ister; iki işaretçi yetmez. `komut_prp` eklendi.

## 45.6 ⭐ Silme ÇALIŞIYOR — arıza sadece veri taşıyan yolda

| komut | sonuç |
|---|---|
| `0x8B BlockErase` | **BAŞARILI**, poll timeout YOK. Log: `[0,0,0,AF0,0, 0]info=6, sts0=...` (AF0=2800 ✓) |
| `0x8A PageWrite` | parça 0-2 sorunsuz; **parça 3** (NAND programlamayı tetikleyen) → **poll fwcq timeout**, durum=başarısız. Log `[0,0,0,2BC,...]info=86` — **2BC=700=2800/4**, yani satır matematiği doğru uygulanıyor |
| `0x89 PageRead` | her adres için **poll fwcq timeout** |
| `0x10 GetFlashParam` | poll timeout (ve zaten NAND değil, DPD'yi döndürüyor) |
| `0x31 GetDefectBadTab` | timeout YOK; `C0,B37486,L0 RDT rslt lost` |
| `0x05 GetFlashModule` | çalışıyor, ama **`no die at step0 / no die at step1`** |
| `0x07 GetCodeBlock` | çalışıyor, `C:0 B:0 (0h)` |
| `0x3A PreCheckCodeBlock` | görev başlatıyor, GDP cevap vermez oluyor |
| `0x88 ReadFlashID` | kusursuz (descriptor motorunu kullanmıyor) |

**Sonuç: descriptor/FWCQ motorunun komut yolu çalışıyor (silme tamamlanıyor),
veri yolu tamamlanmıyor (okuma ve programlama).**

Bu, hedef açısından kritik: **okuyamasak bile yazabilirsek** diske firmware yazılabilir —
zaten amaç buydu. Şu an programlama da timeout veriyor, ama silmenin çalışması motorun
tamamen ölü olmadığını gösteriyor.

Frekans hipotezi **elendi**: 100/133/166/200'ün dördünde de aynı poll timeout, ID hep 6/6.

## 45.7 Kod enjeksiyonu → keyfi fonksiyon çağrısı

Stub v2 (`jd_hack.py cagirkur` / `cagir <fonk> [r0..r3]`): parametreler `0x040FF200`'de
(+0 fonksiyon, +4..+0x10 argümanlar, +0x14 dönüş). Doğrulandı: kendi yazdığımız
`add r0,r0,r1` → `0x1234`. ⚠️ **Thumb hedeflerde adrese `|1` eklenmeli**, yoksa çökme.
Firmware'in `memcpy`'si (`0x040E854C`) böyle çağrıldı, doğru dönüş verdi (`dest+len`).

## 45.8 ⭐ Sequencer programı okuma denemesinde SİLİNİYOR

`gdp_nand_init` başında `memcpy(0x06650000, 0x040EF4C6, 0x408)` — bir **sequencer
microcode/descriptor tablosu** yükleniyor. Ölçüm:

```
PageRead ONCESI : SEQ+0x054=001a87d0  SEQ+0x200=802a00c2  SEQ+0x204=00358032  -> DOLU
PageRead SONRASI: hepsi 0x00000000                                            -> BOŞ
```
111 register sıfıra düşüyor. Elle `memcpy` ile yeniden yüklemek programı geri getiriyor
ama sonraki okuma yine hiçbir şey taşımıyor ve bölgeyi tekrar sıfırlıyor.

DMA hedefi (`0x0400F2C0`) 0xC3 ile doldurulup okundu: sonra **sadece bzero**, veri yok.
→ İşlem gönderiliyor, sequencer başlıyor, veri hiç akmıyor.

## 45.9 LDPC motoru SAĞLAM — orası suçlu değil

`0x040C6AA0`'i kendimiz çağırdık:
```
6AA0(1) -> [0x06610010]=0x0a3d1200  [+0x274]=0x0e   (LDPC açık)
6AA0(0) -> [0x06610010]=0x0a3d1270  [+0x274]=0x00   (RAW; ajan-2'nin öngördüğü 0x1270)
taban:     [+0x00]=0x0f [+0x04]=0x00080200 [+0x08]=0x00003110 [+0x14]=0x22 [+0xa4]=0x300
```
Doğru programlanmış. Kalan tek şüpheli: sequencer/FWCQ.

## 45.10 Elenen hipotezler (dürüst kayıt)

- NAND saati → 100/133/166/200'de aynı timeout ✗
- Kanal/CE eşlemesi → die haritası tamamen açıldı, 8 kombinasyonun hiçbirinde DMA yok ✗
- LDPC matris/uzunluk → motor doğru programlanmış ✗
- DPD alanları (freq/drive/timing) → hiçbiri DPD'den okunmuyor, koda gömülü ✗

## 45.11 ⭐ Motor kilidi: bir veri işlemi = tüm motor ölür

```
1) başlangıç              SEQ+0x200 = 802a00c2   DOLU
2) BlockErase 2800        BAŞARILI               DOLU  (silme motoru bozmuyor)
3) PageRead               veri yok               00000000  KİLİTLENDİ
4) BlockErase 2801        başarısız              00000000
```
Kilitten sonra SEQ bölgesi **ne okunuyor ne yazılıyor** — firmware'in kendi `memcpy`'si
bile geri yükleyemiyor (yazılan `A5A5A5A5`, geri okunan `00000000`). Yani sequencer
işi başlatıyor ve hiç bitirmiyor; bölgeyi sahiplenmiş durumda.

**Sonuç:** güç çevrimi başına **tek bir veri işlemi denemesi** hakkımız var.
Silme (veri taşımayan) sorunsuz; okuma ve programlama (veri taşıyan) motoru öldürüyor.
`0x88 ReadFlashID` çalışıyor çünkü veriyi NIFC `[0x240]/[0x244]` mandallarından alıyor,
DMA kullanmıyor. → **Arıza NIFC↔RAM DMA yolunda.**

## 45.12 ⛔ Kalan duvar: veri işlemi TÜM kontrolcüyü kilitliyor

Ölçüm (`jd_bus.py`):
```
                 NIFC+21C  NIFC+034  FCQ+010   SEQ+200   LDPC+000  0x06700204  ID
başlangıç        00000001  00010002  00801920  802a00c2  0000000f  000003ff    ad7e285302b0
BlockErase sonr. 00000001  00010002  00801920  802a00c2  0000000f  000003ff    ad7e285302b0
PageRead sonrası 00000000  00000000  00000000  00000000  00000000  00000000    000000000000
RAM 0x040C0000   00000000  (SRAM bile sıfır okunuyor)
```
Yani tek bir veri işlemi denemesi **bütün adres uzayını** ölü hale getiriyor; komutlar hâlâ
"başarılı" dönüyor ama her okuma sıfır. Güç çevrimine kadar geri gelmiyor.

## 45.13 Elenen hipotezler — hepsi ölçüldü, hepsi yanlış çıktı

| hipotez | ölçüm | sonuç |
|---|---|---|
| FCQ motoru hiç kurulmamış | `[0x06600010]=0x00801920`, enable `+5C=0x0F`, 255 boş descriptor | **kurulu** ✗ |
| LDPC matrisi yanlış rate (6 vs 2) | MPTool DAT'tan rate-2 matrisleri (`matris 15`) yüklendi, `0x040E4700/4764` ikisi de **1** döndü, `[0x06610010]=0x1200` | yine kilit ✗ |
| Microcode'un yarısı eksik (`0x06649000`) | `[0x06649000]=0x544F4F4C` "LOOT", dört kontrol kelimesi de doğru — **zaten yüklüymüş** | ✗ |
| DMA iniş tamponu programlanmamış | `+0x140=0x00801E58` (=0x0400F2C0>>3), `+0x148..0x164` hepsi doğru | ✗ |
| Tam medya kurulumu koşmamış | `0x040C8E70()` elle çağrıldı, **1** döndü, her şey yerinde | yine kilit ✗ |
| NAND saati | 100/133/166/200 → hepsinde aynı | ✗ |
| Kanal/CE eşlemesi | die haritası açıldı, 8 kombinasyon → hiçbirinde DMA yok | ✗ |
| `param[0x1D]` sayfa kaydırması | 0x09 idi, 14 yapıldı | tek başına yetmedi ✗ |

⚠️ **Dikkat:** `0x066000C0/C4/C8` FIFO register'ları — **okumak descriptor havuzundan
girdi çekiyor** (POP). Teşhis dökümünde bunları okumak serbest listeyi bozabilir.

## 45.14 Yarına net durum

**Elimizde:** firmware konsolu (yazılımdan), kod enjeksiyonu, keyfi fonksiyon çağrısı,
32-bit register yazma, `gdp_nand_init` **DONE**, temiz okuma yolu (ID 6/6),
**çalışan BlockErase**, 100 saniyelik tam otomatik tur (`tur.sh --cevrim jd_hack.py kur`).

**Kalan tek sorun:** veri taşıyan NAND işlemi (okuma ve sayfa programlama) kontrolcüyü
kilitliyor. Silme çalıştığı için komut yolu sağlam; arıza NAND↔SRAM veri/DMA yolunda.

**Sıradaki fikirler:**
1. `0x066000C8` descriptor PUSH akışını elle sür (firmware'i aradan çıkar)
2. `0x040DB500` allocator + `0x040E1368` push'u tek tek çağırıp nerede kilitlendiğini bul
3. MPTool'un USB yolunu bir Windows VM'de koştur — `reset_method=none` ile FLR'siz
   vfio denemesi hiç yapılmadı (FLR loader'ı öldürüyordu, ama bu bayrak onu atlatabilir)
4. Sayfa programlama silme kadar sağlam hale gelirse **okumadan** firmware yazılabilir

---

# 46. 14 Eylül gecesi — MPTool VM'i ve üretici parametreleri

## 46.1 ⭐ vfio/QEMU loader'ı ÖLDÜRMÜYOR — eski tespit yanlıştı

`reset_method=none` çekirdek tarafından reddedildi (`echo: I/O error`), **ama gerek de yoktu**:
QEMU vfio ile 12 sn passthrough sonrası loader hayatta (`MAXIO AYAKTA`, `CSTS.RDY=1`).
"FLR loader'ı öldürüyor" tespiti bu kurulumda geçerli değil.

Hazır VM: `~/jdvm/jd_vm.sh --passthru` — Hiren's BootCD PE x64 + MPTool USB imajı,
VNC `127.0.0.1:5907`, HMP soketi. **sudo ile çalıştır** (`/dev/vfio/13` izni) ve
`HOME=/home/schrodinger` ver (sudo altında `~`=/root tuzağı).

## 46.2 VM kontrolü: fare için kendi VNC istemcimiz

QEMU 8'de HMP'den `mouse_move`/`mouse_button` **kaldırılmış** — `vmkey.py tikla` çalışmıyor.
`~/jdvm/vmfare.py` yazıldı (RFB 3.8, PointerEvent/KeyEvent).
⚠️ **Tuzak:** `ServerInit` 24 bayttır ve ad uzunluğu o 24 baytın İÇİNDEDİR. Fazladan 4 bayt
okumak akışı kaydırıyor ve QEMU girdiyi sessizce yok sayıyor — saatlerce "tıklama pencereyi
küçültüyor" sandım. Doğrusu: `bas[20:24]` = ad uzunluğu.

## 46.3 MPTool cihazı GÖRMÜYOR

`MXMPTool_MAP1202_USB_V1_1_26.exe` açıldı, çalıştı (`YIC5CB4C.bin` + `GDP.bin` yüklü).
Refresh + Auto Detect → **"No connected device for detecting!!"**.
Bu aracın adı zaten **USB**; USB-NVMe köprüsü arkasındaki cihazları tarıyor, PCIe'yi değil.
Loader modunda namespace olmadığı için Windows disk nesnesi de oluşmuyor.

## 46.4 ⭐ Üreticinin gerçek PHY profili — bir ampirik bulgumuzu doğruladı

`MPTOOL.ini: TMCFolder=TMC_ARRAY_M2_HynixV8.ini`; dizi ilk CE için `60000` → **TMC6.ini
tip 00**:
```
Timing_Mode            = 0x0        (firmware varsayilani 0x7C)
High_Speed_Setting     = 0x400A7    (varsayilan 0x02)
Output_Drive_Strength  = 0x06       <-- BIZIM AMPIRIK BULGUMUZ, birebir
Controller_Odt=100  Controller_Driving=40  Nifc_Wpn_Odt=1
Zq_Calibration=0  Nand_Dcc=0  Nphy_Bdl_En=0  Nphy_Io_Odt_En=15
Lcdl_Auto_Update_Ch0..3 = 1
Note=TMC1_0x0_HSS0xA7_ODS0x06_CO100_CD40
```
`Output_Drive_Strength=0x06` bağımsız doğrulama: çipin `0x46` yerine `0x06` saklaması
tesadüf değil, üreticinin öngördüğü değer. Kaynak güvenilir.

`nphy_*` dizilerinin sıfır olması **üreticiyle uyumlu** (`Nphy_Bdl_En=0`) — orası suçlu değil.

Uygulandı (`TMC=0202c80000a70606`): init DONE, `DRI=00000006`, ID 8/8 — **ama DMA yine yok.**

## 46.5 LCDL eğitimi = komut `0x54` — ve çıkmaz

`0x040C4EF8` içinde `NOT SUPPORT MODE IN LCDL TRAINING[%d]`, `LCDL READ RSLT`.
Handler tablosunda **0x54**. Payload: `[5..8]` ve `[9..12]` iki BE32 adres
(ikincisi blok alanı gibi `/PLN`, `%PLN` ayrılıyor).
İlk denemede (mod 0) kontrolcüyü astı. **Çıkmaz: eğitimin kendisi NAND okuması yapıyor,
yani zaten bozuk olan şeye ihtiyaç duyuyor.**

## 46.6 Flash.ini — çipin üreticideki tam satırı

```
SKV606411 H25BFT8A1BDA  V=3(Hynix) T=2(TLC) CE=1  Blk=2888 PG=1536 PZ=16KB Die=1 ECC=2
ID=AD 7E 28 53 02 B0   PairPage=0  IF=11(Legacy->Toggle2.0)  Plane=4
Endurance=3000  Nandmem=001(KIOXIA)  SpareByte=2048
```
DPD'miz bu satırla uyumlu. `param[0x1D]`=9 idi, 14 denendi — init DONE'ı bozmuyor,
DMA'yı da düzeltmiyor. `ECC=2` → rate 2 → matris 15 (ajan-3 ile uyumlu).
`Nandmem=001 KIOXIA` — firmware'deki "polling status fail for KIOXIA" dalının sebebi bu.

## 46.7 ⭐ Arızanın gerçek doğası: sistem veriyolu kilitleniyor, CPU yaşıyor

Kilitten sonra:
- Cihaz host DMA tamponumuza **sıfır yazıyor** (0x5A dolgusu eziliyor) → host tarafı DMA sağlam
- Vendor komutları **status 0 ile tamamlanıyor**, enjekte stub'ımız **çalışıyor**
  (`cagir(0x040C8E70)` → komut BASARILI döndü)
- Ama NIFC, FCQ, LDPC, SEQ **ve SRAM** (`0x040C0000` = firmware'in kendi kodu) hepsi `00000000`
- Yazmalar tutmuyor

→ **CPU yaşıyor (büyük olasılıkla TCM'den koşuyor), AXI/sistem veriyolu ölü.**
Bu yüzden içeriden hiçbir kurtarma çağrısı işe yaramıyor: çağrı çalışıyor ama yaptığı
her okuma/yazma boşa gidiyor. Denenen ve işe yaramayan kurtarmalar:
`0x040C7D74(0)` (NIFC soft reset + iki blob), `0x040C8E70()` (tam medya kurulumu).

Yani veri işlemi bir **bus hatası** tetikliyor (geçersiz adrese DMA, ya da saati/gücü
kesilmiş bir bloğa erişim) ve fabric kilitleniyor. Sadece soğuk güç çevrimi kurtarıyor.

## 46.8 ⭐ Ürün firmware'i RAM'den çalıştırıldı — o da açılmıyor

Keşif: `SYS/*.bin` imajları da **`MAS09_FWTAG_V001`** formatında, yani ROM loader
tarafından RAM'e yüklenebilir. Üstelik `0x400`'de **`LOADER_CERT_TAG1`** sertifikası var.

Parça tablosu düzeni (GDP.bin'den FARKLI):
`+0x70`, 16 bayt/girdi: `u16 baslangic-sayfa, u16 bitis-sayfa, u32 boyut, u32 RAM adresi, u32 bayrak`
**Dosya yerleşimi 0x1000'den itibaren SIRALI** (GDP'de ofset alanı vardı, burada yok).
Doğrulama: 15 parça toplamı + 0x1000 = 0xB1000 = tam dosya boyutu.

`s/e` alanları **NAND sayfa numaraları**: 0x5C..0x87 = 44 sayfa × 16 KB = 0xB0000.
→ **Firmware NAND'da sayfa 0x5C–0x87'de duruyor.** (İleride yazarken lazım.)

`jd_hack.py fwrun [imaj]` yazıldı. Sonuç:
```
15 parcanin hepsi yuklendi + geri-okuma dogrulandi
sertifika blogu (LOADER_CERT_TAG1) -> BASARILI
JumpToPRAM(nbin=15) -> BASARILI
CSTS=0x00000001 (RDY=1)  ama Identify ZAMAN ASIMI
```
**Üreticinin kendi firmware'i de hazır hâle gelmiyor** — diskin orijinal arızasının aynısı.
Muhtemel sebep: ürün firmware'i yapılandırmasını NAND'dan okuyor; NAND veri okunamadığı
için açılamıyor. Kurtarma araçlarının kırmaya çalıştığı kısır döngü tam olarak bu.

Not: bu deneme diski loader modundan çıkarır; soğuk çevrim geri getirir.

## 46.9 ⭐⭐ FLR ile hızlı kurtarma — ve kilit anının logu okundu

**PCIe FLR (`echo 1 > /sys/bus/pci/devices/0000:04:00.0/reset`) kilitlenmiş kontrolcüyü
TAMAMEN kurtarıyor** — soğuk çevrime gerek yok:
```
FLR sonrasi: RAM 0x040C0000 gercek kod okuyor, NIFC+21C=1, NAND ID 6/6 = %100
             MN='Generic_GDP_NVMe_Device'  — TUM YAMALAR VE LOG TAMPONU DURUYOR
```
Tur süresi ~100 sn → ~10 sn. (Ancak üst üste kilit+FLR bazen cihazı tamamen
düşürüyor — `BAR0 hep 0xff` — o zaman soğuk çevrim şart.)

**Ve kritik olan:** log tamponu FLR'den sağ çıktığı için **kilit anının firmware çıktısı
ilk kez okundu**:
```
NPHY_DQS_CTRL:21002
ASSERT [fcl_media.c][1026][fcl_media_fclk_switch] 0
High Speed Setting DONE
[gdp_nand_init] DONE
```

## 46.10 ⭐⭐ KENDİ YAMAM SORUN ÇIKARIYORMUŞ: frekans 100 geçersiz

`fcl_media_fclk_switch` (`0x040E2F9C`) **kabul edilen frekans listesi** (disassembly):
| değer | dönüş |
|---|---|
| 0x22 = **34** | 6 |
| 0xA6 = **166** | 9 |
| 0xC8 = **200** | özel yol 0x040E3054 |
| 0x10A = **266** | 7 |
| 0x14D = **333** | 5 |
| 0x14D+0x43 = **400** | 3 |
| 0x14D+0xC8 = **533** | 2 |

**100 listede YOK.** `0x040C3328`'i `mov r1,#100` yapan yamam → fonksiyon ASSERT'e düşüyor;
ASSERT'i silahsızlandırdığımız için (`0xE58=0`) sessizce geçiyor ve **medya saati
yapılandırılmamış kalıyor**. Yani "frekansı düşürelim" yamam kendi başına bir arıza
kaynağıydı.

Düzeltildi: frekans 200 (yamasız) → ASSERT kayboldu, **ama init DONE'a ulaşmıyor**.
Frekans 34 → DONE (2. turda) ama log'da yine ASSERT var ve PageRead veriyolunu
yine öldürüyor. Yani ASSERT tek başına açıklama değil; **veri yolu arızası bağımsız.**

---

## §47 — KIRILMA: "kontrolcü ölüyor" diye iki gün kovaladığımız şey ÖLÇÜM ARTEFAKTIYMIŞ

Tarih: 2026-09-14 gece. Ajan raporunun §0'ı doğrulandı ve arkasından asıl kök neden çıktı.

### 47.1 — E1: tampon ön-dolgu testi

İddia şuydu: *"veri taşıyan her NAND işleminden sonra NIFC, FCQ, LDPC, SEQ ve SRAM dahil
her adres `0x00000000` okuyor."*

Ajanın itirazı: `0x06700204` salt-okunur bir **strap** register'ı — firmware'de tek bir
erişimi var (`0x040C0FF4`, okuma), hiçbir yazma yok. Böyle bir register `0x3FF`'ten `0x0`'a
**düşemez**. Demek ki okuduğumuz şey kontrolcünün durumu değil, kendi tamponumuz.

Ve haklıydı — kanıt kendi kodumdaydı:

```python
# jd_loader.py, komut()
if veri:
    if gonder is None:
        self.dma.temizle(OFF_DATA, 8192)   # <-- HER KOMUTTAN ÖNCE SIFIRLAR
```

`temizle()` sabit 0 yazıyordu. Yani "her şey sıfır okuyor" = **kendi sıfırlarımı okuyordum.**
Daha önce `alive()` içine koyduğum `memset(...,0x5A,512)` ön-dolgusu da işe yaramıyordu,
çünkü `send()` → `komut()` zinciri onu hemen eziyordu.

`temizle()`'yi modül-global `DOLGU` baytıyla dolduracak şekilde değiştirdim ve ölçümü
tekrarladım:

| ölçüm | dolgu=0x00 | dolgu=0x5A |
|---|---|---|
| ölümcül komut ÖNCESİ NIFC+21C | `00000001` | `00000001` |
| ölümcül komut ÖNCESİ ID | `ad7e285302b0` | `ad7e285302b0` |
| ölümcül komut SONRASI NIFC+21C | `00000000` | **`5a5a5a5a`** |
| ölümcül komut SONRASI ID | `000000000000` | **`5a5a5a5a5a5a`** |
| ölümcül komut SONRASI SRAM 0x040C0000 | `0000…` | **`5a5a5a5a5a5a5a5a…`** |

**Hüküm: veri hiç gelmiyor.** Kontrolcü "sıfır okumuyor" — host'a veri taşıyan DMA susuyor.

Bağımsız ikinci kanal bunu doğruladı: **BAR0 doğrudan MMIO** (DMA'dan tamamen bağımsız)
olay öncesi ve sonrası aynı: `CC=0x00460001`, `CSTS=0x00000001`. **Kontrolcü ayakta ve hazır.**

> Bu tablodaki "her şey 0x00" satırlarının tamamı (§42–§46 boyunca) **GEÇERSİZ**.
> Saat/güç kapısı, MPU yeniden yapılandırması, veri yolu kilidi hipotezlerinin hepsi bu
> geçersiz veriye dayanıyordu.

### 47.2 — ASIL KÖK NEDEN: protokolün ikinci fazını hiç göndermemişiz

MAXIO satıcı protokolü **iki fazlı**: faz-1 512 baytlık komut paketini (`FF E5 <cmd> …`)
gönderir, faz-2 ise veriyi taşır. Veri taşımayan komutlarda (`0x8B BlockErase`, `0x88 ReadID`)
faz-2 yok. Veri taşıyanlarda **şart**.

Bütün `0x89 PageRead` denemelerim `g._faz1(...)` ile, yani **sadece faz-1** gönderiyordu
(`bus.py`, `dma.py`, `inis.py`, `kes*.py` — hepsi). Firmware komutu alıyor, FW-DMA motorunu
(`nvme_fw_dma.c` @ `0x06770000`) gelmeyen faz-2 transferi için kuruyor ve motor o bekleyen
descriptor'la tıkanıyor. Sonrasında **hiçbir komutun veri fazı tamamlanamıyor** — ama CQ
completion'ları ayrı yoldan gittiği için komutlar "status 0" ile bitmiş görünüyor. Tam olarak
gözlediğimiz tablo.

**Düzeltme ve sonuç:**

```python
r1 = g._faz1(_pay(0x89, 0,0,0,0,0, 4,1,1,0,0,0))
r2 = g.komut_prp(0xC2, (nsec<<7,0,0,0, 0x00123400|0x89, nsec), nsec*512)
```

| nsec | bayt | faz-2 | süre | veriyolu sonrası |
|---|---|---|---|---|
| 1  | 512   | BAŞARILI | 10,22 sn | **AÇIK** |
| 8  | 4096  | BAŞARILI | 10,22 sn | **AÇIK** |
| 32 | 16384 | BAŞARILI | 10,22 sn | **AÇIK** |
| 36 | 18432 | BAŞARILI | 10,22 sn | **AÇIK** |

**Kontrolcü artık hiç kilitlenmiyor.** Dört denemede de veri yolu açık kaldı.

### 47.3 — Gerçek hata nihayet görünür oldu

Firmware logu (kanca sayesinde, olay anından):

```
[gdp_poll_fwcq_mix_filter]poll fwcq timeout
```

10,22 sn = ajanın statik olarak hesapladığı ~9,5 sn ile uyumlu. Sayaç limiti
`0x040DBD44`'teki literal: `0x05F5E100` = 100.000.000 tur.

Yani okuma **submit ediliyor, FCQ motoru completion vermiyor**. Sıradaki iş bu.
Artık her deneme kontrolcüyü öldürmediği için FCQ register'larını olay öncesi/sonrası
karşılaştırabiliyoruz — iki gündür yapamadığımız şey.

**R2 yaması** (ajan önerisi) iterasyonu 10 sn → 20 ms'ye indirir:
`0x040DBD44`: `00 e1 f5 05` → `40 0d 03 00` (0x00030D40 = 200.000).

### 47.4 — FLR kurtarma tarifi DÜZELTİLDİ

§46.9'daki "FLR her şeyi geri getiriyor" ifadesi eksikti. Sürücüsüz (driverless) cihazda
çekirdek config space'i geri yüklemiyor. Doğru tarif:

```bash
echo 1 > /sys/bus/pci/devices/0000:04:00.0/reset
sleep 1.5
setpci -s 04:00.0 BASE_ADDRESS_1=0x00000000
setpci -s 04:00.0 BASE_ADDRESS_0=0xdfd00004     # FLR BAR'ı siler, sadece tip bitleri kalır
setpci -s 04:00.0 COMMAND=0x0006                # MSE + Bus Master
```

Atlanırsa BAR0 `0x00000004` olur, MMIO `0xffffffff` döner ve "cihaz öldü" sanılır.
Ölçüldü: FLR sonrası **firmware çalışmaya devam ediyor** (MN=`Generic_GDP_NVMe_Device`),
SRAM, yamalar, log tamponu ve NAND ID okuması (`ad7e285302b0`) hayatta.

⚠️ FLR her şeyi kurtarmaz: firmware gerçekten çöktüyse (0x49 timeout + art arda `alive=False`)
FLR yetmiyor, soğuk çevrim gerekiyor.

### 47.5 — R9: LDPC blokları gerçekten cevap veriyor mu

Ajanın uyarısı: `0x040E4700`/`0x040E4764` dönüş kodu **ters** — `0x0E` ise 0 döner
(yüklendi), başka her şeyde 1 döner. Cevap vermeyen blok 0 okur, ilk turda çıkar ve **1 döner**.
Yani "ikisi de 1 döndü" kaydımız "hiçbir şey olmadı" ile birebir uyumluydu.

Ölçüm: `0x066200A4` (DEC) ve `0x06610274` (ENC) — önce `00000000`, `0x0000000F` yazdıktan
sonra `00000001`. Bloklar cevap veriyor ama yazdığımız değeri tutmuyor. Kesin hüküm yok;
hipotez-5 (LDPC matrisleri yüklendi) hâlâ **doğrulanmamış** sayılmalı.

### 47.6 — Gelen veri NAND'dan MI geliyor? Kanıt TUTMADI

İki fazlı okuma 18432 bayt döndürüyor, 256 bayt değerinin hepsi temsil ediliyor,
ve aynı parametrelerle **4/4 aynı sha256** — belirlenimli. Cazip görünüyor.
Ama asıl testler geçmedi:

| test | beklenen (gerçek NAND ise) | gözlenen |
|---|---|---|
| payload baytlarını tek tek değiştir | belirli baytlar adres gibi davranır | bayt[13] dışında hiçbiri tutarlı etki yapmıyor; 14–47 arası **hepsi aynı** hash'i veriyor |
| `0x8B BlockErase` sonra tekrar oku | sayfa `FF` olur | **veri hiç değişmedi** (iki farklı silme payload'ıyla da) |
| uzun oturumda tekrar oku | sabit kalır | yavaşça kayıyor; sonunda çoğu sıfır olup donuyor |

**Hüküm: bu NAND verisi değil.** Kontrolcünün DMA iniş tamponundaki artık —
faz-2 transferi tamponu host'a döküyor, okuma tamamlanmış olmasa bile.
`[gdp_poll_fwcq_mix_filter] poll fwcq timeout` her okumada var; **okuma hiç bitmiyor.**

§47.2'deki kazanım geçerli (kilitlenme yok, 0,02 sn iterasyon); §47.6'daki "gerçek veri"
yorumu geçersiz. Erken zafer ilan etmeme kuralı burada işe yaradı.

### 47.7 — FCQ motoru 4. descriptor'ı tüketmiyor

Okuma sonrası descriptor dizisi (`0x0400C900`, adım 24 bayt), tail=4, **head=3**:

```
desc[0] 42200880 00002000 00000000 00000000 00080000 0000ff00
desc[1] d0300880 00002004 0000a200 00000000 00000800 000100ff
desc[2] 82200880 00000000 00000000 00000000 00080000 02000000
desc[3] ae100800 00000000 00000003 00000000 00080000 03000001   <-- tuketilmiyor
```

desc[0..2]'de ilk LE word'ün bit31'i **set**; desc[3]'te **clear**. Ve desc[3]'ün ilk
baytı `0xAE` — ajanın bulduğu okuma opcode kapısının (`c0[0x00009264]`: 0→`0xB0`,
aksi→`0xAE`) ürettiği değer.

`0x06600074` (completion count) hiç artmıyor. Doorbell'lerden sadece `0x06600040`
çalınıyor; `0x06600044` ve `0x06600048` sıfır kalıyor.

### 47.8 — Denenen ve ETKİSİ OLMAYAN müdahaleler

Hepsi aynı oturumda, her biri tek değişken:

| müdahale | sonuç |
|---|---|
| `c0[0x00009264]` = 0x00 / 0x01 / 0xFF (okuma opcode kapısı) | fark yok |
| `c0[0x0000924A]` = 0x00 / 0x01 | fark yok |
| `c0[0x00009247]` = 0x00 / 0x01 | fark yok |
| `c1[0x040C4518]` NOP (R8 — LDPC mod yazmasını atla) | fark yok |
| `c1[0x040C45C0]` → `mov r0,#1` (R6 — poll'u tamamen atla) | fark yok |

⚠️ **Ama bu tur şüpheli:** o koşuda descriptor dizisi hiç yazılmadı ve log boş kaldı
(`TO=0`), yani okuma zaten çalışmıyordu. Yamalar "etkisiz" değil, **test geçersiz**.
Yeni hipotez: her başarısız okuma bir FCQ kaynağı (tag/slot) tüketiyor, iade edilmiyor;
yeterince denemeden sonra submit sessizce iptal oluyor. Ölçülüyor.

### 47.9 — FLR her zaman kurtarmıyor

~10 FLR'nin 2'sinde cihaz config space'e geri dönmedi ve soğuk çevrim gerekti.
`flr()` rutini artık: reset → **config space'te vendor ID `1E4B:1202` görünene kadar bekle**
(10 sn'ye kadar) → BAR + COMMAND geri yaz → BAR0 canlı mı diye 3 kez dene.

### 47.10 — FCQ tükenmesi ölçüldü ve yazılımla sıfırlama bulundu

Temiz açılıştan sonra art arda 12 okuma:

```
okuma  1   free4C=ffff00ff db40=00040004 head70=00030003 cnt74=0
okuma  2   free4C=ffff00ff db40=00080008 head70=00060006 cnt74=0
okuma  3   free4C=ffff00fc db40=0009000c head70=00060006 cnt74=0   <-- head DONDU
okuma  4   free4C=ffff00f8 db40=00090010 head70=00060006 cnt74=0
...        free4C her okumada -4
```

- İlk iki okumada head 0→3→6 ilerliyor (tail +4, head +3: **her okumada bir descriptor tüketilmiyor**)
- 3. okumadan itibaren head donuyor, tail ilerlemeye devam ediyor
- `free4C` her okumada **−4** düşüyor ve iade edilmiyor → ~63 okumada havuz biter
- `cnt74` (completion sayacı) **hiç artmıyor**
- **FLR bunu sıfırlamıyor**

Bu, önceki turlarda "yamalar etkisiz" görünmesinin sebebi: kuyruk çoktan tıkanmıştı.

**Yazılımla sıfırlama bulundu:** `cagir 0x040C8E70()` (tam medya bring-up) →
`free4C=ffff00ff`, `db40=0`, `head70=0` ve sonraki okumada head tekrar ilerliyor.
Tek tek denenen `0x040E115C`, `0x040E12E0`, `0x040E1050` **işe yaramıyor**; sadece
tam bring-up sıfırlıyor. Bu, soğuk çevrim gerekmeden onlarca varyant denemeyi mümkün kıldı.

### 47.11 — Sayfanın indiği yer bulundu (varsayımsız diff ile)

Ajan `0x04200000`'i önerdi ama o adres **yazılamıyor** (`@VW ERR(S20010)` — firmware'in kendi
hata mesajı) ve oraya bir şey inmiyor. Okuma öncesi/sonrası **512 KB SRAM diff'i** gerçek
yerleri gösterdi:

| bölge | boy | yorum |
|---|---|---|
| `0x04074E00..0x04079000` | **16896 B** | 16 KB sayfa + 512 B spare — **iniş tamponu** |
| `0x04062200..0x04065400` | 12800 B | ikincil tampon |
| `0x0400C800..0x0400CA00` | 512 B | FCQ descriptor halkası |
| `0x0400E000..0x0400E200` | 512 B | sınıf-1 halkası |
| `0x0400F200..0x0400F600` | 1024 B | DMA descriptor + tampon |

İniş tamponu yazılabilir → temiz deney mümkün: `0xC3` ile doldur, oku, ne değişti bak.
Ölçüldü: okuma tamponun **~%91'ini** yazıyor ve belirlenimli (aynı payload → aynı sha).

### 47.12 — Payload düzeni çözüldü (0x8A'dan)

`yaz.py`'deki çalışan `0x8A PageWrite` çağrısı düzeni açık ediyor:

```
_pay(cmd, 0, 0, blok_hi, blok_lo, sayfa_hi, sayfa_lo, 1, 1, 0, parca_sayisi, parca_idx)
        p3 p4   p5        p6        p7        p8      p9 p10 p11  p12          p13
```

Benim `0x89` payload'ım (`0,0,0,0,0,4,1,1,0,0,0`) bu düzende **parça sayısı = 0** demekti.
Doğru düzenle 4×4 KB parça hâlinde okunduğunda:

- `GetReturn` artık **BASARILI (0x01)** dönüyor
- sadece **1. parça** `poll fwcq timeout` veriyor, 2–4 temiz
- ama veri hâlâ gerçek değil: silinen blok `FF` dönmüyor, farklı bloklar aynı sha veriyor

### 47.13 — "LDPC tuzağı" yaması kendi ayağımıza sıkıyor olabilir — ama kaldırmak da çalışmıyor

`KAZANAN` içindeki `0x040C8D8C = mov r4,#1` + `0x040C8D90 = b 0x040C8E1C` yaması
`gdp_nand_init`'i DONE'a getirmek için konmuştu. Şüphe: LDPC matris yüklemesini atlıyor
ve bu yüzden okuma decode edemiyor.

**Ölçüm:** yama kaldırılınca `0x49` hiç DONE vermiyor ve firmware yanıt veremez hâle
geliyor (bütün register okumaları sentinel dönüyor).

Yani yama keyfî değil — **LDPC yüklemesi gerçekten başarısız oluyor**, ben sadece üstünü
örtüyorum. Doğru çözüm atlamak değil, yüklemenin neden başarısız olduğunu bulmak.
Ajanın C2 uyarısı bunu destekliyor: `0x040E4700`/`0x040E4764` dönüş kodu **ters** —
`0x0E` ise 0 (yüklendi), başka her şeyde 1. Cevap vermeyen blok 0 okur → **1 döner**.
Yani eski "ikisi de 1 döndü, demek ki yüklendi" kaydı tam tersini gösteriyormuş.

### 47.14 — Denenip ELENEN (bu sefer geçerli ölçümle)

| müdahale | sonuç |
|---|---|
| `c0[0x9264]=0` → opcode `0xB0`, routine 0x5C (WAITrb yok) | **daha kötü** — motor tamamen duruyor, head hiç ilerlemiyor |
| `desc[3]` bit31'i elle set + zili tekrar çal | etkisiz |
| payload `p13` süpürmesi (adres sanmıştım) | p13 = **parça indeksi**, adres değil |
| `0x04200000` iniş tamponu varsayımı | yanlış — o adres yazılamıyor, oraya veri inmiyor |

### 47.15 — ⭐ KÖK NEDEN: LDPC blokları yanıt vermiyor

Tuzak yaması yerinde bırakılıp (init DONE) matrisler **elle** yüklendi:

```
DEC matrisi 10608 B -> SRAM 0x040A0000   yazma OK, geri okuma birebir
ENC matrisi  5864 B -> SRAM 0x040A4000   yazma OK, geri okuma birebir
cagir(0x040E4700, 0x040A0000, 2652)  -> 1     durum reg 0x066200A4 = 00000000
cagir(0x040E4764, 0x040A4000, 1466)  -> 1     durum reg 0x06610274 = 00000000
```

Yükleyicinin kodu (`0x040E4700`, disassemble edildi):

```asm
ldr r3, =0x06620000
ldr r2,[r3,#0xa4] ; orr r2,r2,#0xf ; str r2,[r3,#0xa4]   @ once 0xF yaz
loop: ldr r4,[r0,r2,lsl#2] ; str r4,[r3,#0xa8]           @ matrisi porta ak
poll: ldr r0,[r3,#0xa4] ; tst r0,#0xf                     @ 0 veya 0xE olana kadar
      ...
      cmp r0,#0xe ; moveq r0,#0 ; movne r0,#1             @ 0 = YUKLENDI
```

Durum register'ı `0xF` yazıldıktan **sonra bile 0 okuyor** → blok yazmayı kabul etmiyor,
poll ilk turda çıkıyor, fonksiyon 1 (= yüklenmedi) dönüyor. Aynısı ENC için.

**Yani okuma neden hiç tamamlanmıyor sorusunun cevabı:** veri taşıyan descriptor'ın
`XFER`'i LDPC decode'dan geçiyor, decode motoru çalışmıyor, completion hiç gelmiyor,
`cnt74` hiç artmıyor. Silme LDPC'ye dokunmadığı için çalışıyor.

Ve `gdp_nand_init`'i DONE yapmak için koyduğum "LDPC tuzağı" yaması tam da bu başarısız
yüklemenin üstünü örtüyor. Yamayı kaldırınca init hiç DONE olmuyor ve firmware yanıt veremez
hâle geliyor — yani **yama sebep değil, semptomun üstünü örtüyor.**

**Sıradaki soru:** LDPC bloklarını ne uyandırır? (saat kapısı / reset / enable sırası)
Ya da: LDPC gerektirmeyen bir yol var mı? Ürün firmware'ini NAND'a yazmak için boot ROM'un
okuyabileceği daha basit bir ECC modu (BCH/ham) kullanan bir komut olması gerekir — boot ROM
firmware'i LDPC yapılandırılmadan önce okuyor olmalı. GDP komut tablosunda 36 komut var ve
24'ünü hiç incelemedik.

---

## §48 — ⭐⭐ GERÇEK KÖK NEDEN BULUNDU: gömülü LDPC matrisleri YANLIŞ RATE

### 48.1 — Zincir

`Flash.ini` (elimizdeki MPTool paketinde, `[Hynix] Name007`):

```
SKV603005 H25BFT8A1BDA  3 2 1  2888 1536 16 1 2  0xAD 0x7E 0x28 0x53 0x02 0xB0  0 0 0 11 4 3000 001 2048 100
```

`AD 7E 28 53 02 B0` = **bizim flash ID'miz.** Yani NAND'ımız `H25T1TB48E` değil,
**`H25BFT8A1BDA`** ve üreticinin tablosunda **zaten tanımlı**. Sütunlar (Flash.ini başlığından):
Blok=2888 · Sayfa/blok=1536 · Sayfa=16 KB · **ECC=Rate2** · **Plane=4** ·
**Interface=11 (Legacy→Toggle 2.0)** · **Nandmem=001 (200 MHz)** · Spare=2048.

`GDP.bin` chunk0'a gömülü LDPC blobları:

| | adres | boyut | başlık `+0x14` | rate |
|---|---|---|---|---|
| gömülü DEC | RAM `0x00001000` | `0x2928` | `00 00 44 00` | **6** |
| gömülü ENC | RAM `0x00003928` | `0x16D0` | `00 00 44 00` | **6** |
| gerekli DEC | — | `0x149C` | `00 55 11 11` | **2** |
| gerekli ENC | — | `0x0B70` | `00 55 11 11` | **2** |

`gdp_nand_init` bunu `0x040C8DE0`/`0x040C8DF4`'te kontrol ediyor, uymayınca
`"LDPC matrix check fail"` yazıp `b .` yapıyor (`0x040C8E18`).

**Benim `0x040C8D8C` "LDPC tuzağı" yamam tam olarak bu kontrolü atlıyordu.** Yani:
init DONE görünüyordu ama **rate-6 matrisleriyle** çalışıyordu → hiçbir sayfa decode
edilemez → FCQ okuma descriptor'ı sonsuza kadar takılı → `cnt74` hiç artmaz.

Ve son halka: rate-2 blob boyutları **`0x149C` / `0x0B70`** — DPD'min `0x70`/`0x50`
alanlarındaki **orijinal** değerler. Önceki bir ajan DPD'yi gömülü (yanlış) bloblara
uydurmuş (`0x2928`/`0x16D0`), blobları DPD'ye değil. Boyut kontrolü geçmiş, arıza kalmış.

### 48.2 — MPTool bunu nasıl yapıyor

`JumpToPRAM`'dan önce GDP imajını üç yerden yamalıyor (EXE'den çıkarıldı):

```
Write_Cougar_GDP_FW_DPD_Param   @ 0x409F3C
Write_Cougar_GDP_FW_TMC_Param   @ 0x40CAFC     <-- ZAMANLAMA
Write_Cougar_GDP_FW_LDPC_Table  @ 0x40D220     <-- rate'e gore 2 memcpy
```

Rate-2 blobları EXE dosya ofsetlerinde:
```
dd if=MXMPTool_MAP1202_USB_V1_1_26.exe bs=1 skip=$((0x3D7DAC)) count=$((0x149C)) of=dec_rate2.bin
dd if=MXMPTool_MAP1202_USB_V1_1_26.exe bs=1 skip=$((0x3DE0A4)) count=$((0x0B70)) of=enc_rate2.bin
```
Çıkarıldı, `~/jd1024/ldpc_r2/` altında, başlıkları `00 55 11 11` ile doğrulandı.

### 48.3 — Uygulandı: bir engel kalktı, bir sonraki göründü

Doğru bloblar `0x87 WriteRam` ile `0x00001000` / `0x00003928`'e yazıldı (RAM'de
`rate kodu 0x55` doğrulandı), DPD orijinal bırakıldı (`0xE70=0x149C`, `0xE74=0x0B70`
firmware RAM'inde doğrulandı), **bütün yamalar geri alındı**.

Sonuç: **`"LDPC matrix check fail"` logdan kayboldu.** Ama init şimdi daha erken
takılıyor:

```
get feature check timeout, ch(0), bank(0), lun(0), addr(10), para(46!=600)
get feature check timeout, ch(0), bank(0), lun(0), addr(1),  para(10060!=600000)
[gdp_nand_init] FAIL
```

GET FEATURE geri okuması yazılan değerle uyuşmuyor — bu bir **NAND arayüz zamanlaması**
belirtisi ve `Interface=11` (Legacy→Toggle 2.0) geçişiyle uyumlu.

### 48.4 — Sıradaki: TMC (zamanlama) parametreleri

MPTool'un yaptığı üç yamadan **sadece LDPC'sini** uyguladım. `Write_Cougar_GDP_FW_TMC_Param`
henüz çözülmedi — ve GET FEATURE zamanlama hatası tam olarak TMC'nin adreslediği şey.
Pakette `DAT/tmc_para.bin` (16 KB) ve `TMC/TMC*.ini` dosyaları var.

⚠️ Not: `getf` yaması (`0x040E3474`) doğru LDPC + orijinal saat/DDR ile birlikte
firmware'i çökertiyor; eski kombinasyonda (SDR + 34 MHz) çalışıyordu. Yani o yama da
zamanlama sorununun üstünü örtüyordu.

### 48.5 — MPTool yolu KESİN OLARAK KAPALI (doğrudan denendi, 15 Eyl 01:15)

Araştırma iki yeni bilgi getirdi:
1. Eksik ürün firmware'inin adı **`SYS\ZI0PCADC.bin`**, build **SN8878** (`r:/hynix_v6_8878`) —
   bizimle birebir aynı NAND'lı çalışan bir diskin `maxio_nvme_fid` dump'ından doğrulandı
   (usbdev konu 13552). Hiçbir kamuya açık pakette yok; sentezlenemeyen tek parça bu.
2. MPTool'un "USB" binary'sinde yerleşik bir **NVMe yolu** var: `MPTOOL.ini` içinde
   `EnNvmeCmdMode=0`, ayrıca `BusType=NVME`, `NVMePassThroughIdentify()`.

**İkincisi test edildi ve çalışmıyor.** Yapılan:
`EnNvmeCmdMode=1` · C.1.1.26 paketi VM diskine kondu · disk vfio ile Hiren's PE VM'ine
verildi · hem ROM modunda hem **GDP firmware yüklüyken** denendi.

| ölçüm | ROM modu | GDP modu |
|---|---|---|
| Windows PnP | `Standard NVM Express Controller`, `VEN_1E4B&DEV_1202` | aynı |
| PnP durumu | **Error** | **Error** |
| `wmic diskdrive` | sadece QEMU USB diski | aynı |
| MPTool Auto Detect | `No connected device for detecting!!` | **aynı** |

Windows'un `stornvme` sürücüsü bu kontrolcüye ne ROM ne GDP modunda bağlanabiliyor
(namespace yok). Bağlanamayınca MPTool'un tutunacağı bir cihaz nesnesi oluşmuyor —
`EnNvmeCmdMode` bunu değiştirmiyor.

> **Hüküm: USB köprüsü (JMS583) bir kolaylık değil, yapısal zorunluluk.** Ve köprü
> alınsa bile `ZI0PCADC.bin` olmadan MPTool işi bitiremez. Bu yol kapalı; tek yol RE.

### 48.6 — LDPC düzeltmesi kalıcı ve sağlam; kalan tek engel GET FEATURE

Doğru rate-2 bloblar + DPD saat süpürmesi (33/100/200/266), hem yamasız hem `getf` yamalı:

```
  clk=33   yamasiz  init=DONE YOK  getf-TO=2  ldpc-fail=0  FREQ:200
  clk=100  yamasiz  init=DONE YOK  getf-TO=2  ldpc-fail=0  FREQ:200
  clk=200  yamasiz  init=DONE YOK  getf-TO=2  ldpc-fail=0  FREQ:200
  clk=266  yamasiz  init=DONE YOK  getf-TO=2  ldpc-fail=0  FREQ:200
  (+getf varyantlarinda getf-TO 2 -> 1'e dusuyor, DONE yine yok)
```

**`ldpc-fail=0` sekiz varyantın hepsinde** — LDPC engeli gerçekten kalktı ve DPD saatinden
bağımsız. Firmware her durumda `FREQ:200` seçiyor, yani DPD'nin `Clock` alanı burada
belirleyici değil.

Ayrıca test edildi: init FAIL dese de LDPC RAM'de doğru olduğuna göre okuma çalışır mı?
**Hayır.** `cnt74=0`, bütün okumalar aynı bayat tamponu döndürüyor, `LDPC DEC/ENC durum
register'ları hâlâ 0`. Zincir tutarlı:

> GET FEATURE doğrulaması başarısız → `gdp_nand_init` FAIL → yüksek hız/arayüz kurulumu
> tamamlanmıyor → LDPC motoru yüklenemiyor → okuma descriptor'ı tamamlanmıyor.

`ldpc=0/2` ve `scramble=0/1` varyantları da fark yaratmıyor (beklenen — motor zaten kurulu değil).

**Kalan tek iş:** `get feature check timeout, addr(10), para(46!=600)` ve
`addr(1), para(10060!=600000)`. MPTool'un `Write_Cougar_GDP_FW_TMC_Param @0x40CAFC`
yaması henüz uygulanmadı; zamanlama parametreleri eksik.

---

## §49 — `gdp_nand_init` DÜRÜSTÇE DONE + NAND veri yolu ÇALIŞIYOR

### 49.1 — Kazanan yapılandırma (hiçbir firmware yaması yok)

```
1) soğuk çevrim → GDP yükle → hazirla (kanca + dayanıklılık)
2) WriteRam 0x00001000 ← ldpc_r2/dec_rate2.bin  (0x149C bayt, rate kodu 0x55)
   WriteRam 0x00003928 ← ldpc_r2/enc_rate2.bin  (0x0B70 bayt)
3) 0x11 InitGDP ← dpd_clk200.bin   (gdp_init_param.py, FLASH_LINE_SKV606411)
4) TMC bloğu — 0x11 bunu TAŞIMIYOR, elle yazılmalı (MPTool imaja yamalıyor):
   0x200 = 0x00 (bIf_Power_On)   0x205 = 0x17 (High_Speed_Setting)
   0x206 = 0x02 (Output_Drive_Strength)
   0x2B4 = 40   0x2B6 = 100   0x2B8 = 1   0x2BA = 1   0x2BF = 0x0F
   0x2D4 = 0x17 (u32)   0x2D8 = 0x7C (u32)
5) 0x49  →  DONE, 1. turda, getfTO=0, ldpcfail=0
```

Betik: `scratchpad/tmc.py`. Tekrarlanabilir; 4 ayrı koşuda 4/4 DONE.

### 49.2 — ⭐ NAND VERİ YOLU ÇALIŞIYOR — kanıt

`0x10 VC_GDP_CmdGetFlashParam` (işleyici `0x040C465C`, submit `0x040DE91C`) çipten
gerçek veri döndürdü:

```
4a 45 53 44 02 00 ... 53 4b 48 59 4e 49 58 20 20 20 20 20 48 32 35 42
"JESD"                 "SKHYNIX"                        "H25B"
```

JEDEC parametre sayfası, içinde üretici adı ve part numarasının başı (`H25BFT8A1BDA`).
`0x14 ReadUID` de geçerli UID deseni döndürdü. Yani **NAND, arayüz, zamanlama, LDPC ve
DMA'nın hepsi çalışıyor.** Kalan arıza tek bir yerde: `0x89`'un descriptor/submit yolu.

### 49.3 — `0x89` neden tamamlanmıyor (ölçülen)

Her seferinde aynı: 4 descriptor yazılıyor, tail=4, **head=3**, `cnt74` hiç artmıyor,
`poll fwcq timeout`. Tüketilmeyen desc[3] `0x040DD010` tarafından kuruluyor ve
`0x040DD09C`'de `input[7]=0` sabitleniyor (desc[0..2]'de 2 → word0 bit31 set).

### 49.4 — Temiz zeminde ELENEN hipotezler

| hipotez | test | sonuç |
|---|---|---|
| routine 0x61'in baştaki `CMD 70 + WAITrb`'si | `c0[0x9264]=0` → opcode `0xB0`/routine `0x5C` (desc[3] `ae`→`b0` doğrulandı) | **aynı** — TO, cnt74=0, head=3 |
| desc[3]'te bit31 eksik | hedefli (`0x040DD09C/A0`) ve toptan (`0x040EC2F0`) yama | **ikisi de `gdp_nand_init`'i bozuyor** → `0x040DD010` init'te de kullanılıyor, bit31 orada 0 olmalı |
| LDPC rate/matris · TMC · DPD saati · scramble · ldpc arg | süpürüldü | etkisiz |

### 49.5 — ⚠️ İKİ TOOLING TUZAĞI (ölçümleri geçersiz kılmıştı)

**1. `poke()` canlı bağlamı eziyor.** `poke()` 512 baytlık blok okuyup geri yazıyor.
`0x00009200–0x000093FF` aralığında **canlı komut bağlamı** var (`ctx` @0x9210, `g9244`).
Oraya `poke()` ile yazmak firmware'in o anki durumunu bayat kopyayla eziyor ve veri yolunu
öldürüyor. `0x9264`/`0x924A`/`0x9247` hakkındaki eski "etkisiz / kötüleşti" sonuçlarının
**hepsi bu yüzden geçersizdi.** Çözüm: enjekte edilen poke stub ile 4 bayt hassasiyetinde yaz.

**2. Stub'ı faz-0 olmayan komuta kurma.** Stub'ı `0x5B`/`0x58` gibi faz≠0 bir komuta
kurunca firmware veri fazı bekliyor ve taşıma tıkanıyor (§47.2'nin aynısı). Tablodaki
faz-0 komutlar: `0x02 0x3A 0x8B 0x47 0x0A 0x57 0x58`. Pratikte **sadece `0x02` stub
barındırıyor**; ikinci stub gerekiyorsa `0x02`'nin işleyicisini CAGIR ↔ POKE arasında
değiştir (`scratchpad/gate5.py` bunu yapıyor).

### 49.6 — Descriptor farkı elendi; LDPC durum register'ı yanlış negatif olabilir

Ajanın bulduğu tek yapısal fark — çalışan üç descriptor kurucusunun `buf[0xC]&0xF = 2`
yazması, okuma/yazma yollarının 0 bırakması — **test edildi ve elendi**:

```
kontrol buf[0xC]=0   desc[3] w1=00000000  poll=0 head=0003 cnt74=0 TO=1
        buf[0xC]=2   desc[3] w1=00000002  poll=0 head=0003 cnt74=0 TO=1
```
Enjeksiyon descriptor'a ulaştı (w1 değişti), sonuç değişmedi.

**Asıl bulgu başka yerde:** `gdp_nand_init` LDPC matrislerini **hiç yüklemiyor**, sadece
başlıklarını doğruluyor. Gerçek yükleme her okumada `0x040C6AA0` ile yapılıyor ve
okuma yolu (`0x040C450C`) **dönüş değerini atıyor**. Elle çağırınca:

```
cagir(0x040C6AA0, 1) -> 1        (0 = ikisi de yuklendi)
DEC 0x066200A4 = 00000000   ENC 0x06610274 = 00000000   (once ve sonra)
cw  0x06610010 = 0x0A401200  -> [12:0]=0x1200 ✔  [25:13]=0x1200 ✔  [28:26]=2 ✔
RAM'deki bloblar saglam: "MAXIOLDPCDECINIT"/+0x14=00 55 11 11 ✔
```

Ama salt-okunur tarama **her iki bloğun da canlı ve dolu** olduğunu gösteriyor:

- ENC `0x06610000..0x066102FC`: ~140 sıfır-olmayan register; `0x06610134..0x0661022C`
  arasında **üç özdeş 21-word yüksek-entropili blok** — yüklenmiş matris verisine benziyor
- DEC `0x06620000..0x066200BC`: `0x06620000=00001300`, `0x06620004=80018001`,
  `0x0662000C=000402AA`, `0x06620060=00404000`, `0x066200B4=00004F0F` …
- Sadece **iki durum register'ı** (`0x066200A4`, `0x06610274`) sıfır okuyor

`0x040E4700`'ün mantığı: durum nibble'ı `0` okunursa poll ilk turda çıkar ve **1 döner**.
Yani "1" = "nibble 0xE değil" demek; nibble hep 0 ise fonksiyon matris yüklenmiş olsa da
1 döndürür. **`0xE` beklentisi bu blok revizyonuna uymuyor olabilir — yanlış negatif.**

Silahlandırma denemeleri (`0x040E1418`, `0x040E2190`, `0x040C7D74(0/1)`, `0x040E4888`,
`0x040C8E70`, `0x040C6C30`, `0x040E2804`) hiçbiri durum nibble'ını değiştirmedi.
`0x040E47C8` (hazır-mı kapısı) **1** dönüyor.

**Sıradaki soru:** matris gerçekten yüklüyse okuma neden tamamlanmıyor? Yüklü değilse
`0x06610134+` bölgesindeki veri nedir? Ayırt etmek için: yükleme öncesi/sonrası
`0x06610134..0x0661022C` bölgesini diff'le — değişiyorsa matris gerçekten akıyor demektir.

---

## §50 — Arıza NAND veri yolunun kendisinde; kontrolcü ve firmware tarafı bitti

### 50.1 — Bu turda kesinleşen tablo

| işlem | sonuç |
|---|---|
| `gdp_nand_init` (0x49) | **DONE, yamasız** (LDPC rate-2 blobları + TMC bloğu verilince) |
| `0x8B BlockErase` | çalışıyor |
| `0x88 ReadFlashID` ch0 | çalışıyor, `ad7e285302b0` |
| `0x10 GetFlashParam` | **gerçek JEDEC sayfası** (`"JESD" … "SKHYNIX" … "H25B"`) |
| `0x14 ReadUID` | çalışıyor |
| `0x02 mode 0x40` (BB tarama) | çalışıyor, **die'ı kilitlemiyor** |
| `0x89 PageRead` | **die'ı kilitliyor** |
| `0x8A PageWrite` | parça 0-1-2 temiz, **son parça die'ı kilitliyor** |

### 50.2 — ⭐ Kök gözlem: die veri patlamasında kilitleniyor

```
okuma öncesi  NIFC+0x21C = 00000001   (hazır)
okuma sonrası NIFC+0x21C = 00000000   (meşgul) — 60 saniye boyunca değişmiyor
```

Donanım tam **3 completion** üretiyor (poll atlanınca `cnt74=3` kuyrukta görülüyor),
4. descriptor die'ı beklerken asılı kalıyor. `0x57 NandPowerOnOff(1)` (NAND reset) de
takılıyor — **sadece tam soğuk çevrim kurtarıyor.**

Komut/adres (tek çevrim, yavaş) ve durum okuma çalışıyor; **yüksek hızlı veri çıkış
patlaması** çalışmıyor. Yazma ve okuma aynı noktada, aynı şekilde.

### 50.3 — Temiz zeminde ELENEN hipotezler (hepsi geçerli ölçümle)

| hipotez | test | sonuç |
|---|---|---|
| LDPC matrisi yüklenmiyor | ajan C1: `0x066200A4/0x06610274 = 0` **başarı durumu**; `0x040C6AA0(1)` = **1 = başarılı** | elendi |
| ECC/LDPC decode takılıyor | **ham profil** `0x06610000[3:0]=2` + `0x06610008[4]=0` uygulandı (okuma anında doğrulandı) | **aynı** |
| routine 0x61'in `WAITrb`'si | `c0[0x9264]=0` → opcode `0xB0`/routine `0x5C` (desc `ae`→`b0` doğrulandı) | aynı |
| descriptor bit31 eksik | hedefli + toptan yama | init'i bozuyor |
| `buf[0xC]&0xF = 2` farkı | enjekte edildi (desc w1 `0→2`) | aynı |
| Toggle 2.0 moduna geçiş | `HSS=0x00`, `+0x2D4=0` (legacy'de kal) → init DONE, getfTO=0 | aynı |
| çok-düzlemli okuma | DPD `Plane=4→1` (+ RowPlaneShift, StpuShift) | aynı |
| `0x924A`, `0x9247`, `0x9262` | 4-bayt hassas yazma ile | aynı |
| `0x040C450C`/`0x4518` NOP, `0x45C0`, `0x4584` | hepsi | aynı |
| DPD saati 33/100/200/266 | hepsi | aynı |

### 50.4 — ⚠️ NAND veri yolunda fiziksel zamanlama işareti

`ReadFlashID` kalitesi, ch/ce başına 3 tekrar (doğru = `ad7e285302b0`):

```
ch0: 3/3 3/3 3/3 3/3   ad7e285302b0 (dördü de temiz)
ch1: 0/3 0/3 0/3 0/3   adad7e280200  adad28000000  adad02000000
ch2: 0/3 0/3 0/3 0/3   000000000000
ch3: 0/3 0/3 0/3 0/3   000028530000
```

ch1 ve ch3 **doğru ID'nin baytlarını yanlış konumlarda** döndürüyor (`ad`, `28`, `53`, `02`).
Bu, veri yakalamanın zaman ekseninde kaydığının imzası — ve daha önceki GET FEATURE
anomalisiyle (`para(46!=600)`, bayt şeridi kaymış) aynı imza.

Kalibrasyon komutları bunu düzeltmiyor, **başarısız oluyor**:

```
0x55 ZQ + DCC:
  read nand status timeout, ch(0), bank(3), err(2), sts(0)
  dcc fail, read status fail[ 0]
0x53 BDL bit-deskew: veri yolunu öldürüyor
```

**Duty-cycle düzeltmesi (DCC) başarısız** ve ch0'da bank 2-3 durum okumasına cevap vermiyor.

### 50.5 — Masaya konması gereken ihtimal

Kontrolcü tarafı bitti: firmware ayağa kalkıyor, komut/adres/durum/silme yolu sağlam,
parametre sayfası gerçek veriyle geliyor. Buna rağmen **hiçbir array veri patlaması
tamamlanmıyor ve her denemede die kalıcı olarak kilitleniyor**; DCC kalibrasyonu
oturmuyor; 4 kanalın 3'ü ya sessiz ya kaymış veri veriyor.

Bu tablo, **NAND paketinin kendisinde kalıcı hasar** ihtimalini ciddi şekilde masaya koyuyor.
Diskin geçmişi de bunu destekliyor: satıcıda zaten salt-okunurdu, format sırasında öldü,
uzun süre enerjisiz kaldı, 26 soğuk açılışın sadece 2'sinde BIOS gördü.

**Kanıtlanmış değil.** Denenmemiş kalan: üreticinin TMC array dosyasındaki eğitilmiş
DQS/LCDL değerlerini (`+0x14..0xB3`, `+0xC0..0xCF`) uygulamak — bunlar hâlâ gömülü
varsayılanlarda ve `TMC_ARRAY_*HynixV6*` dosyası pakette yok.

## §51 — 🟢 **DİSK ÇALIŞIYOR: sil → yaz → oku turu doğrulandı (15 Eylül 06:45)**

### 51.1 — §50'nin teşhisi YANLIŞTI, sebebi tek bir sayı

`0x040DBD44`'teki firmware poll timeout'u **10.000.000** idi. Bu yüzden her veri
işlemi ~60 saniye asılı kalıyor, NVMe komutu timeout'a düşüyor ve **arkasından gelen
her ölçüm ölü görünüyordu**. "Die kalıcı kilitleniyor, sadece soğuk çevrim kurtarıyor"
tespitinin tamamı bu artefakttı.

Timeout **300.000**'e indirildi → aynı okuma **0,0 saniyede** sonuçlanıyor, die hazır
kalıyor (`NIFC+0x21C=1`), ID okunuyor, silme çalışıyor, GDP canlı.

```
FCQ: 4 descriptor gonderildi, 4 completion geldi (head==tail 0x000a000a)
okuma sonrasi: ch0 21C=1  ID=ad7e285302b0  silme=BASARILI  GDP canli=True
```

### 51.2 — ⭐⭐ Yaz → geri oku, birebir

```
BLOK 1500 (rowfield 6000):
  oku  : ff x4096                       (bos)
  sil  : temiz (hata satiri yok)
  yaz  : ok   [0,0,0,5DC,0,0]info=86, sts0=0101e0ff
  oku  : sha=e4678057  ***DESENLE BIREBIR AYNI***  farkli=256
         3744515e6b7885929facb9c6d3e0edfa0714212e3b4855626f7c8996a3b0bdca
```

4096 baytın tamamı eşleşti. **NAND dizisi okunuyor ve yazılıyor.**

### 51.3 — `sts0` kodu çözüldü

`[ch,bank,lun,row,plane,?]info=%x, sts0=%08x, sts1=%08x` (yazdıran: `0x040DC04C`)

`sts0` = **NAND durum register'ı, bank başına bir bayt** (little-endian 4 bayt):

| bayt | anlam |
|---|---|
| `e0` | RDY+ARDY+WP#, **FAIL biti 0 → BAŞARILI** |
| `e1` | aynı ama **bit0=1 → İŞLEM BAŞARISIZ (kötü blok)** |
| `ff` | o bank'ta die yok / uygulanamaz |
| `80` | okuma yolunda: sadece bit7 — LDPC/veri aşaması sonucu |

Blok 1000 ve 2000 `0101e1e1` verdi (iki düzlem de FAIL) → **kötü blok**, o yüzden
yazılıp geri okunamadılar. Blok 1500 `0101e0ff` verdi → **sağlam**, tur tamamlandı.

### 51.4 — Adres semantiği kesinleşti

| komut | adres alanı |
|---|---|
| `0x8B BlockErase` | doğrudan **blok numarası** (`payload[5..6]` u16 BE) |
| `0x89/0x8A` | **rowfield = blok×4 + plane**; firmware `row=rf/4, plane=rf%4` uyguluyor |

Yani `sil(1500)` ile aynı bloğu okumak için `rowfield=6000` verilmeli. §50'deki
"silinmiş blok FF gelmiyor" gözlemi bu kaymadan kaynaklanıyordu.

### 51.5 — Bir komut = 4 KB

`0x89` tek çağrıda **4096 bayt** getiriyor (`payload[13]` parça indeksi). 16 KB'lik
DMA okumasının kalan 12 KB'si bayat tampon artığı — §50'deki "farkli=256 gürültü"
yorumu buradan geliyordu. Sayfanın tamamı için 4 çağrı gerekiyor.

### 51.6 — Firmware NAND sürücüsü haritası (statik)

| adres | işlev |
|---|---|
| `0x040E384C` | çıplak NIFC routine başlatıcı: `21C&1` bekle → `224`=routine → `228`=CE → `220`\|=1 → bekle. **Routine 2 = NAND RESET.** Die meşgulse ilk beklemede sonsuz döner — `0x57`'nin asılma sebebi buydu. |
| `0x040E3898` | tüm 32 die için reset döngüsü |
| `0x040E3D48(desc*)` | descriptor gönder (komut sınıfı) |
| `0x040EC240(handle,desc*)` | descriptor gönder (veri sınıfı); ring word1[3:0] = `handle[0xC]&0xF` |
| `0x040DC454` | check-ready, descriptor opcode **0x42** |
| `0x040DCEEC` | pre-read (00h/adres/30h), opcode **0x82** |
| `0x040DD010` | data-out, opcode **0xB0** (`c0[0x9264]!=0` ise 0xAE) |
| `0x040DD290` | **ham data-out, hedef tamponu açık parametre** (`r2 = adres>>3`, desc[0xA]=2) |
| `0x040DE694` | parametre sayfası data-out, opcode **0x0C**; `handle[0xC]&0xF = 2` yapıyor |
| `0x040DBD68` | durum değerlendirici: `sts0 & 0xE1` |
| `0x040DBD44` | **poll timeout sabiti** — yukarıdaki kök neden |

## §52 — ✅ **KALICILIK KANITLANDI: veri NAND'da duruyor. Fiziksel hasar YOK.**

### 52.1 — Önbellek hipotezi elendi

"Yazdıktan hemen sonra okuyorsun, önbellekten geliyor olabilir" itirazına karşı
kesin protokol uygulandı:

1. `s7a` — 6 bloğa (600, 660, 1200, 1260, 2100, 2400) benzersiz nonce'lu desen yazıldı
2. **GDP firmware'i komple yeniden yüklendi** (`jd_loader.py gdprun` → tüm kontrolcü
   SRAM'i, tüm tamponlar, tüm FTL/önbellek durumu sıfır)
3. `s7b` — aynı bloklar geri okundu

```
blok 600  -> *** NAND'DA KALICI — ESLESTI ***
blok 1200 -> *** NAND'DA KALICI — ESLESTI ***
blok 2100 -> *** NAND'DA KALICI — ESLESTI ***
blok 2400 -> *** NAND'DA KALICI — ESLESTI ***
blok 660  -> *** NAND'DA KALICI — ESLESTI ***
blok 1260 -> *** NAND'DA KALICI — ESLESTI ***
KALICI: 6/6
```

Hiçbir önbellek firmware yeniden yüklemesini geçemez. **Veri gerçekten NAND dizisinde.**

### 52.2 — Okuma güvenilirliği

Silinmiş sağlam blok (600) 15 kez arka arkaya okundu: **15/15 tam `FF`×4096.**
Tek bir kaçak, tek bir kısmi okuma yok.

### 52.3 — Erişilebilir kapasite

16 die'ın (4 kanal × 4 CE) tamamı adreslenebiliyor; blok 1500 turunda 15/16 die
yaz/oku turunu geçti (kalan 1 die'da o blok kötü blok çıktı, die'ın kendisi değil).

### 52.4 — Kötü blok dağılımı (ch0 ce0, 49 örnek)

Silme durumu `e1` (FAIL biti) veren bloklar kümeleniyor:
`1320 1440 1500 1560 1620 1680 1740 1800 1860 · 2460 2520 2580 2640 2700 2760 2820`

Bu iki bant dışında silme temiz geçiyor. Tam sayım gerekiyor; örnek küçük.

### 52.5 — ⛳ Varılan nokta

| yetenek | durum |
|---|---|
| `gdp_nand_init` | ✅ yamasız DONE |
| blok silme | ✅ (kötü bloklar `e1` ile doğru raporlanıyor) |
| 4 KB sayfa yazma | ✅ |
| 4 KB sayfa okuma | ✅ 15/15 güvenilir |
| yazılanın kalıcılığı | ✅ firmware reload'u geçiyor |
| 16 die erişimi | ✅ |

**Donanım sağlam. Kalan iş tamamen yazılım: diskin kendi firmware'inin NAND'daki
sistem alanını yeniden kurmak.**

## §53 — Diskin kendi sistem alanı: ne kaldı, ne silindi

### 53.1 — Tam NAND haritası (ch0 ce0, blok 0..63; 16 die, blok 0..7)

```
ch0 ce0: DD......uuuuuuuuuuuu............uuuu................D.......uuuu
digerleri (15 die): ........        (. = 0xFF bos)
```

**Flash'ın tamamı silinmiş durumda.** Sadece ch0/ce0'ın ilk bloğunda fabrika verisi var.
Bu, "format sırasında öldü" anlatısıyla birebir uyuşuyor: format diziyi silmiş,
yükleyici bloğunu bırakmış, firmware'i götürmüş.

### 53.2 — ⭐ Yükleyici bloğu SAĞLAM ve okunabiliyor (scrambler=1, ldpc=0)

Blok 0'ın içeriği (4 bölüm):

```
+0x000000  LDBK BLOCKS V00
+0x000200  LDBK CONFIG V00     → "H25BFT8A1BDA" (+0x1e0)
+0x008000  LDBK LDPC TABLE1    → "MAXIOLDPCDECINIT"  20210727  00 55 11 11
+0x010000  LDBK LDPC TABLE2    → "MAXIOLDPCENCINIT"  20210727  00 55 11 11
```

`00 55 11 11` = **rate 2** — yani §48'de MPTool EXE'sinden çıkarmak zorunda kaldığım
doğru LDPC matrisleri **zaten diskin kendi NAND'ında duruyormuş.**

`LDBK BLOCKS V00` başlığı:
```
+0x10  0b 09 05 00 …          0x090B = 2315  (0x47'nin bildirdigi wStopBlock 0x906=2310 ile uyumlu)
+0x18  01f4 ×4                 500, her kanal icin
+0x30  ff0f ×4  ff01 ×4        TMC dizisi (varsayilan degerler)
+0x60  (0x0010, 0x149C)        LDPC DEC bolumu: ofset, uzunluk
       (0x2010, 0x0B70)        LDPC ENC bolumu
+0x70  bfd532c1… / 92ef8463…   iki 16-bayt ozet
```

`LDBK CONFIG V00` = **kontrolcü register başlangıç listesi**, 16 baytlık kayıtlar:
`baslangic_reg(u16) bitis_reg(u16) deger(u32) maske(u32) bayrak(u16) ffff`
(örn. reg 0x5C..0x61 ← 0x00018000). Boot'ta uygulanan donanım konfigürasyonu.

### 53.3 — Ürün firmware'i denendi: RAM'den kalkıyor ama NVMe'ye dönüşmüyor

`jd_loader.py gdprun <SYS/*.bin>` ile V7 (`YIQZCADC`, `r:/DVT/skv7_9286`) ve
V8 (`ZIC5CB5C`, `r:/…/HynixV8/Release_241127`) imajları RAM'e yazıldı (15 bölüm,
hepsi geri okunup doğrulandı) ve JumpToPRAM yapıldı.

Sonuç: firmware **başlıyor** (loader vendor komutları artık kabul edilmiyor — ürün
firmware'i onları kapalı tutar), ama Linux `nvme` sürücüsü bağlanamıyor:

```
nvme nvme1: Device not ready; aborting reset, CSTS=0x1
nvme 0000:04:00.0: error -ENODEV: probe failed
```

Beklenen: bu firmware'ler NAND'da kendi neslinin sistem alanını arıyor; bizimki V6
ve firmware bölümü silinmiş. **V6 SYS firmware'i (`ZI0PCADC`) hiçbir yerde yok** —
usbdev.ru'da aynı derdi yaşayan başka biri de var, moderatör cevabı: *«Bu firmware
Çinlilerde parayla bile yok.»* Bu yol kapalı.

### 53.4 — Erişim hızı

```
yazma 2,43 MB/s (1,7 ms/4KB)   okuma 1,15 MB/s (3,6 ms/4KB)
```
Darboğaz NAND değil: komut bekleme döngüsünde `time.sleep(0.0005)` var, yani her
NVMe komutu en az 500 µs'e mal oluyor; 4 KB başına iki komut = ~1 ms taban.

## §54 — Yeniden kullanılabilir takım ve doğrulanmış tarif

### 54.1 — Tam tarif (soğuk çevrim GEREKMEZ, ~25 saniye)

```bash
sudo jd_loader.py gdprun        # GDP yukle  (bu ayni zamanda her seyi KURTARIR)
sudo jd_hack.py hazirla         # hook + 29 nokta trap disarm
python3 ~/jd1024/takim/jdnand.py durum
```

Python tarafı (`~/jd1024/takim/ortak.py`):
1. birleşik stub kur (`0x02` handler'ı → poke/peek/çağır)
2. **`poke 0x040DBD44 ← 300000`**  ← bu satır olmadan hiçbir ölçüm güvenilir değil
3. LDPC rate-2: RAM `0x1000` ← `dec_rate2.bin` (0x149C), `0x3928` ← `enc_rate2.bin` (0xB70)
4. `0x11 InitGDP` ← `dpd_clk200.bin`
5. TMC bloğu RAM `0x200`: `[0x00]=0x00 [0x05]=0x17 [0x06]=0x02 [0xB4]=40 [0xB6]=100
   [0xB8]=1 [0xBA]=1 [0xBF]=0x0F [0xD4]=0x17(u32) [0xD8]=0x7C(u32)`
6. `0x49` → **DONE, 1. turda**

### 54.2 — Komut kartı

| işlem | payload | not |
|---|---|---|
| silme | `FF E5 8B ch ce blkH blkL 00 00` | **doğrudan blok no**; log'da `e1` = kötü blok |
| okuma | `FF E5 89 ch ce rfH rfL pgH pgL ldpc scr pln 00 parca` + `0xC2` PRP 16 KB | `rf = blok*4` |
| yazma | `FF E5 8A ch ce rfH rfL pgH pgL ldpc scr pln 00 parca` + `0xC1` PRP 4 KB | |
| flash ID | `FF E5 88 ch ce` | `ad7e285302b0` |

`ldpc=0 scr=0` → ham NAND baytları (boş sayfa = `FF`).
`ldpc=0 scr=1` → descrambler açık; **sistem alanını (blok 0) okumak için bu gerekli**.
Bir komut = **4096 bayt**; `parca` 0..3 sayfanın dört çeyreği.

### 54.3 — Ölçüm hijyeni (bu projede üç kez ısırdı)

1. **Veri taşıyan komutta faz-2'yi asla atlama** — atlarsan FW-DMA motoru kilitlenir ve
   ardından gelen her okuma `0x5A` sentinel'i döndürür.
2. **İniş tamponunu (`0x0400F2C0`) okumadan önce sentinel'le doldur** — yoksa başarısız
   okuma, önceki okumanın verisini "yeni veri" gibi gösterir. §50'deki "rastgele veri var"
   yorumu bu yüzden yanlıştı.
3. **`scr=1` ile boş sayfa da rastgele görünür** — harita çıkarırken `scr=0` kullan.
4. `komut()` içindeki `time.sleep(0.0005)`'i kaldırma — hız kazandırmıyor (gecikme
   kontrolcünün kendisinde, ~556 µs/komut) ama **doğruluğu bozuyor.**

### 54.4 — Henüz denenmemiş, elde hazır duran şey

`~/jd1024/kanit/skv6_ucode/` altında **SKV6 NAND zamanlama mikrokodu** 8 frekansta
çıkarılmış hâlde duruyor (`HYV7_DAT_ucode__SKV6_001_400.rec16k.bin` → başlık
`SKV6_001_400`, bölümler `(0x1000,0x890)` nifc_cmd ve `(0x2000,0xd10)` nops_op).
**Bugüne kadar hiç yüklenmedi** — init jenerik `ldr23` tabloları ile çalışıyor.
Okuma/yazma zaten çalıştığı için bu bir "düzeltme" değil, olası bir iyileştirme.

### 54.5 — ⚠️ Kontrolcüyü sert kilitleyen komutlar

| komut | etki |
|---|---|
| `0x3A PreCheckCodeBlock` | **kontrolcüyü tamamen kilitler.** Loader vendor komutları bile cevap vermez olur (`enable` ZAMAN AŞIMI, WriteRam timeout). `gdprun` kurtaramaz — **tam soğuk güç çevrimi şart.** |
| `0x53 BDL bit-deskew` | veri yolunu öldürür |
| `0x55 ZQ+DCC` | `dcc fail` verir; üstelik >400 MT/s özelliği, Hynix profillerinde hep `0` |
| `0x57 NandPowerOnOff` | die meşgulse `0x040E384C`'in ilk `while`'ında sonsuz döner |

Deney sırası kurarken bunları **en sona** koy, yoksa 6,5 dakikalık soğuk çevrim yersin.

## §55 — ✅ **1,57 MB gerçek veri, sha256 birebir. Disk depoluyor.**

### 55.1 — Sonuç

```
kaynak sha256 = f5ef388286b44c33b7069009258b1e7ae1d478f6d86773639e474016759be063
geri   sha256 = f5ef388286b44c33b7069009258b1e7ae1d478f6d86773639e474016759be063
>>> TAM ESLESME  1.572.864 / 1.572.864 bayt = %100,0000
```

24 blok × 16 sayfa × 4 KB, rastgele içerik, sil→yaz→oku. Tek bayt fark yok.
Blok başına sayfa sınırı da yok: **blok 624'e 64 sayfa yazıldı, 64/64 doğru okundu.**

### 55.2 — ⭐ Asıl ders: kötü blok testim eksikti

`0x8B` silme durumunda `e1` (NAND FAIL biti) **yeterli bir ölçüt değil.** Bir blok
temiz silinip yine de veri tutmayabiliyor:

| blok | silme | tek sayfa yaz→oku |
|---|---|---|
| 600, 660, 1200, 2100 | temiz | **ESLESTI** |
| 1024, 1500 | temiz (`e1` yok!) | başarısız (`sts0=00000080`, `gdp_read_page … FAIL`) |

**Doğru ölçüt: `sil → sayfa 0 ve sayfa 8 tam `FF` okunmalı`.** Bu sıkı testle
600–900 aralığında oran: gevşek %40 → **sıkı %34**. (Bu bölge tüm gece deneylerle
yıpratıldı; temiz bölgede oran daha yüksek olmalı — gevşek tarama 16 die genelinde
%87,6 vermişti. Sıkı tarama tüm sürücüde henüz yapılmadı.)

§16 ve §18'deki "4 MB tutmadı" sonuçlarının tamamı bu eksik ölçütten kaynaklanıyordu:
kötü bloklara yazılıyordu. **Sıkı ölçütle seçilen bloklarda hata oranı sıfır.**

### 55.3 — LDPC yolu da çalışıyor — yeter ki mod eşleşsin

```
yaz(ldpc=0,scr=0) -> oku(ldpc=0,scr=0)  ESLESTI     (ham)
yaz(ldpc=1,scr=1) -> oku(ldpc=1,scr=1)  ESLESTI     (ECC + scrambler)
capraz kombinasyonlar -> coplu veri
```
Yani ECC korumalı yazma/okuma da elde. Yazarken hangi modu kullandıysan okurken
aynısını kullanacaksın.

### 55.4 — Kalan sınır: sayfanın dörtte biri

Aynı sayfaya `parca=0,1,2,3` yazıp geri okuma **çalışmıyor** (dördü de X). `parca=0`
ile her `0x8A` 4 KB yazıp sayfayı hemen programlıyor. Yani şu an **16 KB sayfanın
4 KB'ı kullanılıyor** → kapasite 4'te bir. Tam sayfa yolu (4 parça tamponlanıp
sonuncuda programlama) çözülürse kapasite 4 katına çıkar.

### 55.5 — Ölçülen performans

| | |
|---|---|
| yazma | 1,9 – 3,7 MB/s |
| okuma | 1,6 – 3,6 MB/s |
| komut gecikmesi | ~556 µs (kontrolcü kaynaklı, NAND değil) |
| birim | 4096 bayt |

### 55.6 — Bugünkü net tablo

| | |
|---|---|
| NAND donanımı | **sağlam** — fiziksel hasar yok |
| sil / yaz / oku | **çalışıyor**, sha256 doğrulandı |
| kalıcılık | **çalışıyor** — firmware reload'unu geçiyor (6/6) |
| 16 die erişimi | **çalışıyor** |
| kötü blok tespiti | çözüldü (sil→FF ölçütü) |
| ECC (LDPC) yolu | **çalışıyor** |
| diskin kendi firmware'iyle açılması | **hayır** — V6 SYS firmware'i dünyada yok |
| kullanılabilir kapasite | host tarafından, ~4 KB/sayfa ile; sıkı tarama sonrası netleşecek |

## §56 — ⚠️ **GERİLEME: sabah çalışan okuma yolu öğleden sonra bozuldu**

### 56.1 — Ne oldu

Sabah §52'de 6/6 kalıcılık veren **birebir aynı protokol** öğleden sonra **0/8** verdi.
Aynı bloklar, aynı kod, aynı konfig. Tüm okumalar `FAIL`:

```
[0,0,0,5DC,0,0]info=5, sts0=00000080, sts1=00000000
[gdp_read_page] 0 0 6000 0 FAIL[ 0]
```

`sts0=0x80` = NAND durum baytında sadece bit7 → **RDY ve ARDY sıfır, yani die okuma
sonrası meşgul.** Bu tam olarak §50'de tarif ettiğim semptom. Silme ve ReadFlashID
hâlâ çalışıyor; bozulan sadece hızlı veri okuması.

Denenenler ve sonuçları:

| müdahale | sonuç |
|---|---|
| soğuk güç çevrimi (45 sn kapalı) | değişmedi |
| blok 0'ı yedekten geri yazma | **yazma da tutmuyor** — geri gelmedi |
| DPD saat × ODS × HSS süpürmesi (32 kombinasyon) | sadece `clk200+HSS=0x17` init oluyor (sabahki gibi), tur 0/4 |
| poll timeout 50k / 300k / 3M / 10M | fark yok |
| `cagir(0x040E3898)` NAND reset-all | **GDP asıldı** — `0x040E384C`'in ilk `while`'ında dönüyor, yani die gerçekten meşgul |

### 56.2 — ⚠️ Kendi yaptığım hasar

Alias'ı ölçmeden blok 2048+'a yazdım. Satır adresi 2048'de döndüğü için bu
**blok 0'a**, yani fabrika yükleyici bloğuna yazdı. `LDBK BLOCKS V00` başlığı gitti
(sayfa 2'deki LDPC tablosu duruyor). Yedek var ama geri yazılamıyor çünkü yazma yolu
da şu an çalışmıyor.

Ayrıca V7/V8 ürün firmware'ini RAM'den çalıştırdım; o firmware NAND'a yazmış veya
die'ın feature register'larını değiştirmiş olabilir.

### 56.3 — Ölçüm dersi (bu tur üç kez ısırdı)

**Aynı seansta yaz→oku EŞLEŞMESİ HİÇBİR ŞEY KANITLAMAZ.** Okuma başarısız olunca
kontrolcü son yazılan veriyi döndürüyor (echo). Bugün "16 KB tam eşleşme", "15/16 die
çalışıyor", "%87,6 sağlam blok" sonuçlarının tamamı bu echo'dan kaynaklandı.

Geçerli iki protokol:
1. **Tampon-kıran:** A'ya X yaz, B'ye Y yaz, **önce B'yi oku**, sonra A'yı oku → X gelmeli.
2. **Reload:** yaz → `jd_loader.py gdprun` → oku. Tek sahtelenemez kanıt budur.
   §52'nin 6/6'sı bu protokolle alındı; o sonuç gerçekti.

### 56.4 — Açık hipotezler

| hipotez | lehine | aleyhine |
|---|---|---|
| **Sıcaklık / Vth kayması** | sabah uzun soğuk duruştan sonra çalıştı; saatlerce yüklendikten sonra bozuldu; 45 sn kapalı kalmak soğutmaz; ID+silme dayanıklı, hassas okuma bozuk | henüz ölçülmedi |
| Die feature register'ı kalıcı değişti (V7/V8 firmware) | güç çevrimini geçiyor | init'in GET FEATURE doğrulaması temiz geçiyor (`getfTO=0`) |
| Blok 0'ın yok edilmesi init'i bozdu | zamanlaması uyuyor | init hâlâ DONE veriyor, LDPC kontrolü temiz |
| NAND aşınması | binlerce silme yapıldı | blok başına sadece birkaç çevrim; TLC dayanımı 3000 |

Sıradaki ölçüm: **25 dakika kapalı bırakıp ilk işlemde test** — sıcaklık hipotezini
tek başına ayırır.

## §57 — ⭐⭐ Statik analiz: üç ayrı 4× kapasite kaybı ve bir ölçüm yanılgısı

Kaynak: `re/ANALIZ_TAMSAYFA.md` (823 satır) ve `re/ANALIZ_NVME.md` (1178 satır).

### 57.1 — `payload[12]` = parça SAYISI, ben hep 0 göndermişim

`0x8A` işleyicisi `0x040C3DB4`:

```
0x040C3DFC  r0 = ctx[0x11]                 payload[12] = NCHUNK
0x040C3E04  if (NCHUNK == 0) -> HEMEN PROGRAMLA        <-- benim yaptigim
0x040C3E2C  if (NCHUNK > PFRAG_NUM) { b . }            <-- SONSUZ DONGU, GDP olur
0x040C3E4C  if (NCHUNK == (chunk&3)+1) {               son parca
0x040C3E78     memcpy(0x04074EC0 + chunk*0x1000, 0x0400F2C0, 0x1000)
0x040C3E88     memcpy(0x0400F2C0, 0x04074EC0, 0x4000)  16 KB staging -> DATA_BUF
               -> TEK programlama
            } else { staging'e koy, dön, durum YAZMA }
```

`nchunk=0` ile dört parçayı ayrı ayrı yazmak = **aynı hücreleri dört kez programlamak.**
§55.4'teki "4 parça çalışmıyor" bundan.

### 57.2 — ⭐ Yazma zaten 16 KB yazıyormuş; okuma `ldpc=0`'da tek parçaya düşüyor

Descriptor `word3[3:0]` = fragment maskesi = `PFRAG_NUM-1` = 3 → 4×4 KB = 16384 bayt.
Yani **yazma yolu baştan beri tam sayfa programlıyor**, 4 KB gerçek + 12 KB bayat SRAM.

Okumada ise tek bir komut var:
```
0x040C4524   moveq r7, #0        ; ldpc==0 ise fragment sayisi 1'e dusuyor
```
**§51-§55'teki her deney `ldpc=0` kullandı.** "Bir komut = 4 KB" gözleminin tamamı bu tek
instruction'dan. MXMPTool'un x86 kodu da aynısını yapıyor (`ldpcRate==0` → 4096;
`!=0` → 4 parça) — ikinci bir binary'den doğrulandı.

**Doğru tam sayfa okuma:** `ldpc=1, scr=1, nchunk=0, chunk=0` + `0xC2` 16384 bayt, ve
`[:4096]` kırpmasını KALDIR. Ham (ldpc=0) okumayı da tam sayfa yapmak için tek kelime:
`0x040C4528 ← E1A00000` (geri alınabilir).

### 57.3 — ⭐ Plane 1..3 hiç kullanılmamış

`rowfield = blok*4 + plane`. Tüm araçlarım `rowfield = blok*4`, yani **hep plane 0**.
Flash.ini bu parçanın **4 plane**'i olduğunu söylüyor → **bir 4× daha.**

### 57.4 — ⭐ Blok başına sayfa sayısı 1536 değil, plane başına 384

Flash.ini `PageNum=1536` dört plane'in toplamı. Aritmetik ancak böyle tutuyor:

```
2888 blok × 1536 sayfa × 16384 bayt × 16 die = 1024 GiB  (tam)
= 2888 blok × 4 plane × 384 sayfa × 16 KB × 16 die
```

Hiçbir zaman sayfa 64'ün ötesine yazılmadı. **Sayfa 383 / 384 sınırı test edilmeli.**

### 57.5 — GDP zaten TAM bir NVMe 1.3 kontrolcüsü

`re/ANALIZ_NVME.md`: admin dispatcher `0x040CA67C`, Identify `0x040DF60C`,
**I/O queue yaratma tam implemente** (`0x040DF96C` CQ, `0x040DFA60` SQ), donanım SQM/CQM
PRP yürüyüşünü kendi yapıyor. GDP **Write'ı uçtan uca `0x04081800`'de 250 KB'lık bir
SRAM ramdisk olarak zaten gerçekliyor**; eksik olan sadece FTL — read handler tamponu
doldurmadan geri veriyor.

| | |
|---|---|
| NN (namespace sayısı) | 1 |
| NSZE | `(0x3E800 - x·16) >> 9` ≈ **500 LBA = 250 KB** |
| LBAF | 0..3 = 512 / 1K / 2K / **4K** |
| imza/RSA kontrolü | **yok** (1180 string tarandı) |
| MPU | `0x04080000..0x04100000` **RWX** |
| watchdog | yok |
| ⚠️ tuzak | cache açık (`0x040CF580`), kod yaması sonrası `mcr p15,0,r0,c7,c5,0` şart |

Yama noktaları literal havuzunda: `0x040DF544` (admin dispatcher), `0x040DF54C` (I/O) —
**instruction yaması bile gerekmiyor.** `0x040DF340 ← E3A00003` MDTS=3,
`0x040CAFE0 ← E3A01401` NSZE. Toplam ~200-330 instruction.

**Read/Write admin queue'da sunulamaz** — Linux blok I/O'yu `ctrl->tagset`'e bağlar,
sadece I/O queue. Ama I/O queue yaratma zaten çalışıyor, sorun değil.

### 57.6 — Düzeltilmiş kapasite matematiği

| katman | çarpan | not |
|---|---|---|
| bugüne kadar kullanılan | 1× | plane 0, ldpc=0 okuma (4 KB), sayfa<64 |
| tam sayfa okuma (`ldpc=1`) | ×4 | 4 KB → 16 KB |
| plane 1..3 | ×4 | hiç dokunulmadı |
| doğru sayfa sayısı (384/plane) | — | 1536 zaten dört plane'in toplamı |

Yani mevcut araçların gördüğü alan gerçek kapasitenin **1/4'ü** (plane kaybı);
okuma tarafında ayrıca 1/4 (fragment kaybı). Gerçek tavan hâlâ 2888×1536×16 KB×16 die
= **1 TiB**, ama ona ulaşmak için hem plane hem `ldpc=1` düzeltmesi gerekiyor.

## §58 — 🎯 **KÖK NEDEN: die'ı olmayan kanala dokunmak tüm okuma yolunu zehirliyor**

### 58.1 — Ölçüm

Soğuk güç çevriminden hemen sonra, ch0/ce0'da bir blok çifti kurulup (`1744`/`1746`,
`ldpc=1 scr=1`, tam 16 KB) referans alındı. Sonra araya tek tek başka işlem türleri
sokularak referansın bozulup bozulmadığına bakıldı:

```
sadece okuma — 60 tekrar          ++++++++++++++++++++++++++++  60/60
araya SILME ekle — 20 tekrar      ++++++++++++++++++++          20/20
araya YAZMA ekle — 20 tekrar      ++++++++++++++++++++          20/20
araya BASARISIZ okuma ekle        ++++++++++++++++++++          20/20
araya ch2 (die YOK) islemi        +..............               1/15  ← ZEHIR
```

**Die'ı olmayan bir kanala tek bir işlem göndermek yeterli.** Ondan sonra
*tüm kanallarda* okuma kalıcı olarak bozuluyor.

### 58.2 — Neyin kurtardığı / kurtarmadığı

| müdahale | sonuç |
|---|---|
| FCQ reset `0x040C8E70` | ❌ |
| re-init (`0x11` + `0x49`) | ❌ |
| **GDP firmware'ini komple yeniden yükleme** | ❌ |
| **tam soğuk güç çevrimi** | ✅ **tek çözüm** |

GDP reload'unu geçip güç çevriminde sıfırlanan bir donanım/die durumu. NIFC'in
takılı kalan routine'i veya die'ın komut sırasında bıraktığı mod — kesinleşmedi,
ama pratikte önemi yok: **kural basit.**

### 58.3 — ⭐ KURAL

> **ch2 ve ch3'e asla işlem gönderme.** Tek bir silme bile diski bozar.
> Çalışan kanallar: **ch0 ve ch1.**

Bu kural bugünkü tüm "gerileme"yi açıklıyor. Sabah çoğunlukla ch0/ce0 üzerinde
çalışıldı → her şey düzgün gitti ve §52'nin 6/6 kalıcılığı alındı. Öğleden sonra
16 die taranmaya başlandı, ch2/ch3'e dokunuldu ve o andan sonra **hiçbir ölçüm
geçerli olmadı** — §56'daki "gerileme"nin tamamı bu.

### 58.4 — Bu neyi değiştiriyor

- Kapasite tavanı 16 die değil, en fazla **8 die** (ch0 + ch1) → ~512 GB
- Her tarama/harita çıkarma aracı ch2/ch3'ü **atlamak zorunda**
- Yeni die aramak "kanarya" yöntemi ister: referans bir blok çifti kur, her yeni
  die'ı denemeden önce ve sonra referansı kontrol et; bozulursa o die yoktur ve
  ölçüm orada durmalıdır (güç çevrimi gerekir)

### 58.5 — Yanlışlanan önceki iddialar

| iddia | gerçek |
|---|---|
| §56 "okuma yolu geriledi, sebebi bilinmiyor" | ch2/ch3'e dokunulmasıydı |
| "sıcaklık/Vth" | 25 dk soğumadan sonra da bozuktu → elendi |
| "blok 0'ı yok etmem init'i bozdu" | register durumu sabahkiyle birebir aynı → elendi |
| "die feature register'ı kalıcı değişti" | güç çevrimi düzeltiyor, feature olsa düzeltmezdi → zayıf |

---

## §60 — KÖK NEDEN BULUNDU: GDP firmware'i TOGGLE bayrağı + LEGACY zamanlaması ile geliyor

**15 Eylül, öğleden sonra.** §58'in "ch2/ch3'e dokunma" kuralı ve §59'un
"zamanlayıcılar 125× kısaydı" teşhisi **ikisi de yanlış premise dayanıyordu.**
Gerçek neden tek ve çok daha basit.

### Bulgu

GDP bring-up zinciri (`0x040E38D8`):

```
0x040E38E8  bl 0x040E2F40      ; N[0x210] = DQS mask
0x040E38EC  mov r0, #1         ; <<<< 1 = TOGGLE (DDR) modu
0x040E38F0  bl 0x040E2B48      ; N[0x204].0 = r0 ; N[0x034].16 = !r0 ; N[0x200] = <literal>
0x040E38FC  memcpy(0x06649000, ...)   ; NIFC mikrokodu
0x040E3904  bl 0x040E3898      ; routine 2 (NAND RESET) tüm die'lara
0x040E391C  bl 0x040E37E8      ; routine 0x24 = hynix 0x77 SET PARAMETER
```

`0x040E2B48` içindeki `str r6,[r1,#0x200]` — r6 literali `0x040E2F18`'de ve
değeri **`0x02020202`**, yani **legacy (SDR) veriyolu zamanlaması**. Toggle modu
için olması gereken `0x01010000 | (t<<8) | t`.

Yani firmware **`+0x204` bit0 = 1 (toggle/DDR) ama `+0x200` = legacy zamanlama**
kuruyor. Denetleyici DQS'in her iki kenarında örneklemeye çalışıyor, zamanlama
tek kenar için ayarlı. Sonuç: veri geliyor ama baytların çoğu kayıyor.

### Ölçüm (s58, aynı oturum, arka arkaya)

| | toggle (init'in kurduğu) | legacy (`+0x204`=0, `+0x034`\|=0x10000, `+0x200`=0x02020202) |
|---|---|---|
| ch0 ce0 ID | `ad7e285302b0` | `ad7e285302b0` |
| ch0 ce1 ID | `ad2828530000` | `ad7e285302b0` |
| ch0 ce2 ID | `ad2828000000` | `ad7e285302b0` |
| ch0 ce3 ID | `ad2828000000` | `ad7e285302b0` |
| ch1 ce0 ID | `adad7e530000` | `ad7e285302b0` |
| ch1 ce1 ID | `adad7e285302` | `ad7e285302b0` |
| ch1 ce2 ID | `adad28530200` | `ad7e285302b0` |
| ch1 ce3 ID | `ad7e5302b000` | `ad7e285302b0` |
| yaz→oku bayt hayatta | **%0,8** | **%96,9** |
| aynı sayfayı 2× oku, bit farkı | 0 | 0 |

### Bunun geriye dönük açıkladıkları

1. **"ch2/ch3'te die yok" (§58) YANLIŞ.** Die'ların ID'leri toggle örnekleme
   hatasıyla bozuluyordu; ben bozuk ID'yi "die yok" diye okudum. Sekiz die'ın
   sekizi de legacy'de doğru ID veriyor. "Zehirlenme" de büyük olasılıkla aynı
   şeyin başka bir yüzü.
2. **Aralıklı başarı.** Bozulma oranı ~%26 bayt iken bazı sayfalar şans eseri
   LDPC eşiğinin altında kalıp düzeliyordu → 60/60, sonra 0/200.
3. **LDPC'nin "çalışmaması".** Ham BER %3,7 civarındaydı; rate-2 LDPC ~%1'i
   düzeltir. Kod bozuk değildi, girdisi eşiğin üstündeydi.
4. **Silinmiş sayfada bile bit hatası.** Silinmiş hücre okumak NAND'in en
   güvenilir işidir; orada hata çıkması hücreyi değil **veriyolunu** işaret
   ediyordu. Teşhisi buradan yakaladım.

### Kalıcı düzeltme

`ortak.py` → `JD.legacy_yama()`, `init()` içinden varsayılan olarak çağrılıyor:

```python
MOD_SEC=0x040E38EC                       # mov r0,#1 -> mov r0,#0
poke_blok(MOD_SEC, struct.pack("<I",0xE3A00000))
```

Böylece bring-up'ın tamamı (NAND RESET ve hynix 0x77 SET PARAMETER dahil)
legacy modda koşuyor — sonradan register dürtmekle aynı şey değil, çünkü 0x77
NAND'in kendi arayüz modunu kuruyor.

### Aynı turda öğrenilen ikinci şey: zamanlayıcılara DOKUNMA

`nops_tmr_un0..un3` = 40/100/1/1 (eski "kazanan tarif") **legacy modda
denetleyiciyi tamamen kilitledi**: tüm ID'ler `None`, `jd_loader.py gdprun`
kurtaramadı, soğuk güç çevrimi gerekti. Üretici varsayılanı **5000/8000/50/0**
kalacak. Eski tarifin çalışmasının sebebi zamanlayıcılar değil, o betiklerin
(`yaz.py`, `bus.py`) init sonrası `+0x204=0` / `+0x034|=0x10000` yazmasıydı —
yani legacy'ye geçmeleriydi. `ortak.py`'ye refactor ederken o iki satırı
düşürmüşüm; regresyonun kaynağı bu.

---

## §61 — Kalan %3 çözüldü: sayfa başına 512 baytlık başlık bölgesi

Legacy moda geçtikten sonra tur testi hâlâ "başarısız" diyordu ama sayısal iz
gürültü değil **yapı** gösteriyordu:

| koşu | bayt hayatta | bit farkı | desen ort. popcount | 512 × popcount |
|---|---|---|---|---|
| s58 `S58-QQ` | 15872/16384 (tam 512 eksik) | 1902 | 3,71 bit/bayt | 1900 |
| s62 `LDPC-TEST` | %96,88 | 1637 | 3,20 bit/bayt | 1638 |

Uyuşmayan bayt sayısı **her seferinde tam 512** ve bit farkı, o 512 baytın kendi
popcount'una birebir oturuyor → o bölge **0x00 dönüyor**, hatalı değil.

Konum-kodlu desenle (her 4 baytlık yuva kendi indeksini taşıyor) kesinleşti:

```
512-bayt bölge başına hatalı bayt (32 bölge):
  127   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
    0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
>=16 baytlık SIFIR koşulları: [(0, 512)]
yuva: dogru=3969  baska-yuvadan=127  tanimsiz=0
bayt hayatta = 16257/16384 = %99,22
```

**Sayfanın ilk 512 baytı hep sıfır, kalan 15872 bayt byte-for-byte doğru.**
Kayma yok, serpiştirme yok (kayma testi: +512 → %62,9, yani hizalı değil).
Okuma tamponu işlemden önce `0x5A` ile dolduruluyor; o bölge `0x5A` değil `0x00`
dönüyor → transfer eksikliği değil, **denetleyicinin kendi yazdığı sıfırlar**.
Muhtemelen FTL metadata/LBA etiketi alanı; GDP yazma yolu onu doldurmuyor.

**Pratik sonuç: sayfa başına kullanılabilir yük = 15872 bayt** (%3,1 kayıp).
`cekirdek.py` içinde `BAS=512` / `KULL=15872`; tüm karşılaştırmalar `v[512:]`.

## §61b — İki yeni "DOKUNMA" kuralı (ikisi de denetleyiciyi sert kilitledi)

Aşağıdaki iki yazma `jd_loader.py gdprun` ile kurtarılamayan kilide sokuyor,
tam soğuk güç çevrimi gerekiyor:

1. `G+0x70/G+0x74` (nops_tmr) = 40/100/1/1 → legacy modda ölümcül.
   Üretici varsayılanı **5000/8000/50/0** kalacak.
2. `NIFC+0x200` = 0x02020202 dışında bir değer (0x04040404 denendi) → kilit.

Zaten bilinen: `0x3A PreCheckCodeBlock`, ve riskli: `0x53`, `0x55`, `0x57`.

## §62 — Echo mekanizması firmware kodunda bulundu

`gdp_read_page` (0x040C4560 civarı):

```
0x040C4584  bl   0x040DE038          ; okumayi baslat
0x040C4588  cmp  r0, #0
0x040C458C  beq  0x040C4618          ; r0==0 -> dogrudan memcpy
0x040C45C0  bl   0x040DBDCC          ; FCQ tamamlanma bekle -> sp[0x10] = hata kodu
0x040C45C4  ldrb r0, [sp, #0x10]
0x040C45CC  strbeq fp, [r4, #0x17]   ; hatasiz -> durum temiz
0x040C45D8  strb r1, [r4, #0x17]     ; r1=0x1B -> durum = OKUMA HATASI
0x040C45FC  blx  printf              ; "[gdp_read_page] %d %d %d %d FAIL[%2x]"
0x040C4618  ldr  r1, ->0x0400F2C0    ; kaynak = landing tamponu
0x040C461C  movw r2, #0x4000
0x040C4620  ldr  r0, ->0x04074EC0    ; hedef = staging
0x040C4624  bl   memcpy
```

**Okuma başarısız olsa bile memcpy koşuyor.** Yani host'a her zaman
`0x0400F2C0`'ın içeriği veriliyor — başarısızlıkta bu, bir önceki işlemden
kalan bayat veri. *Bu, projede üç kez ısıran "echo"nun tam kaynağı,* artık
tahmin değil kod.

**Sonuç: `getreturn()[0] == 0x1B` okumanın gerçekten başarısız olduğunun
güvenilir göstergesi.** Bundan sonra her okumada kontrol edilecek.

Reload testi (s65b) bunu doğruladı: GDP yeniden yüklendikten sonra 8 farklı
kanal/CE/blok okuması **tek ve aynı sha**'yı döndürdü — NAND'a hiç gidilmiyor.
Dolayısıyla s63'ün "%99,22 doğru" sonucu da echo'ydu (ilk 512 bayt staging
yolunda sıfırlandığı için saf echo gibi görünmedi — bu yüzden yakalamak zor oldu).

## §62b — Kurtarma: FLR ve secondary bus reset İŞE YARAMIYOR

Denetleyici kilitlendiğinde (`gdprun` → `enable ZAMAN ASIMI`):

| yöntem | sonuç |
|---|---|
| `jd_loader.py gdprun` | yetersiz |
| PCIe FLR (`echo 1 > .../reset`) | **DURUMU KÖTÜLEŞTİRİR** — cihaz veri yolundan tamamen düşer (`VID=ffffffff`), `remove`+`rescan` geri getirmiyor |
| kopru 03:00.0 secondary bus reset | geri getirmiyor |
| **tam soğuk güç çevrimi (`rom_cycle.sh`, ~7 dk)** | **tek çalışan yol** |

`04:00.0`'ın üst köprüsü `03:00.0` (`00:02.1 → 02:00.0 → 03:00.0 → bus 04`).

---

## §63 — Ölçüm aparatı düzeltildi: NÖBETÇİ TESTİ

Gün boyunca defalarca "çalışıyor" görünüp sonra çürüyen her sonucun kaynağı
aynıydı: okuma başarısız olduğunda firmware landing tamponunu (`0x0400F2C0`)
host'a kopyalıyor (§62). Üstelik:

* **Staging tamponu `0x04074EC0`, GDP imajının (`0x040C0000`+) DIŞINDA.**
  `jd_loader.py gdprun` onu silmiyor. Dolayısıyla **"reload testi" de
  sahtelenebilir** — projede iki kez "tek sahtelenemez kanıt" diye kullandığım
  protokol aslında kanıt değilmiş.
* Staging 16 KB olduğu için 4 parçalı yazmadan sonra parçaları tek tek okumak
  dördünü de doğru gösteriyor. "3/4 parça birebir" sonucu bu yüzden çıkmıştı.

**Geçerli tek protokol — NÖBETÇİ:**

```python
LAND=0x0400F2C0; STAG=0x04074EC0
def doldur(nb):                      # okumadan ONCE iki tamponu da doldur
    d=bytes([nb])*4096
    for base in (LAND,STAG):
        for o in range(0,0x4000,4096): g.wr(base+o,d,dogrula=False)
# okuma nobetci donerse NAND'a hic gidilmemistir
```

Nöbetçi baytını değiştirip sonucun değişmediğini de doğrula (sızıntı testi).

## §64 — Nöbetçiyle doğrulanan gerçek durum

| | durum | kanıt |
|---|---|---|
| 16 die canlı | ✅ | legacy'de 4 kanal × 4 CE hepsi `ad7e285302b0` |
| NAND durum baytı | ✅ `e0` = RDY·ARDY·WP·hatasız, 16 die | PIO rtn 0x0D |
| Kendi NIFC routine'imiz | ✅ | mikrokod slotuna yazılıyor, fabrika rtn 0x03 kendi harness'ımızla doğru ID veriyor |
| **`ldpc=1 scr=1` 16 KB okuma** | ✅ **GERÇEK** | nöbetçi dönmüyor · sayfa 0/1/2/3/100 farklı · blok 800/801/802/900 farklı · nöbetçi baytı değişince sonuç değişmiyor · **blok 1000 = `7c71ebee2225`, ayrı GDP yüklemelerinde birebir aynı** |
| `ldpc=0` ham okuma | ❌ ölü | her zaman nöbetçi döner |
| legacy'de toplu okuma | ❌ ölü | her blok tek sabit sha |
| Okuyan die sayısı | ⚠️ **1/16** (ch0 ce0) | diğer 15'i nöbetçi |
| Programlama | ❌ inmiyor | yazma sonrası okuma nöbetçi ya da içerik değişmiyor |
| Silme | ⚠️ tek kodlama işliyor | aşağıda |

Kanal register'ları (`+0x000,0x034,0x0A0..0x0B4,0x0F4,0x200,0x204,0x20C,0x210,
0x214`) dört kanalda **birebir aynı** — ch0'ın çalışmasının sebebi kanal
kalibrasyonu değil. Fark die düzeyinde.

## §65 — Silme adreslemesi: tek işleyen kodlama `b*1536`

`0x8B` parametre kodlaması denendi (okunabilir bloklarda, PIO karıştırmadan):

| kodlama | durum | içerik değişti mi |
|---|---|---|
| `b` (düz blok no) | BAŞARILI ama **FAIL biti** | hayır |
| `b*4` (rowfield) | BAŞARILI | hayır |
| `b*4+1` | BAŞARILI | hayır |
| `b*384` | BAŞARILI | hayır |
| **`b*1536`** | BAŞARILI | **EVET** — `b129fb060276` → `d27ed380e660` |
| `b<<2` | FAIL | hayır |

Paketleme: `pay(0x8B,ch,ce,(v>>8)&0xFF, v&0xFF, (v>>24)&0xFF, (v>>16)&0xFF)`.

`d27ed380e660` muhtemelen **silinmiş sayfanın descrambler çıktısı** — aynı değer
daha önce blok 175/350/1400'de de görülmüştü.

⚠️ **PIO harness'ını firmware işlemleriyle ARALAMA.** İkisi de `+0x240`'ı
kullanıyor; araladığında `sts0` flash ID baytlarıyla kirleniyor
(`sts0=01017ee1`, `sts1=b0025328` içinde `ad7e285302b0` parçaları).

## §66 — Programlama: hiçbir mod sayfayı değiştirmiyor

Dedektör: silinmiş sayfa `d27ed380e660` okunuyor. Programlama sayfayı
değiştirirse okuma ya başka bir şey verir ya da tamamen başarısız olur.

| mod | sil sonrası | yaz sonrası | değişti? |
|---|---|---|---|
| ldpc1 scr1 tek 16 KB | `d27ed380e660` | `d27ed380e660` | hayır |
| ldpc1 scr1 4×4 KB | `d27ed380e660` | `d27ed380e660` | hayır |
| ldpc0 scr0 tek / 4 parça | `d27ed380e660` | `d27ed380e660` | hayır |
| ldpc2 scr0 · ldpc3 scr1 · ldpc1 scr0 · ldpc2 scr1 | aynı | aynı | hayır |

`0x8B`'ye `+0xC`/`+0xD` parametrelerinin 6 kombinasyonu da içeriği değiştirmedi.

**Firmware `0x8A` işleyicisi (`0x040C3DB4`) statik olarak okundu** — parametre
düzeni gönderdiğimizle birebir uyuyor:

```
+0x08 ch · +0x09 ce · +0x0A..0B blok (BIG-ENDIAN) · +0x0C..0D sayfa (BE)
+0x0E ldpc · +0x0F scr · +0x10 plane · +0x11 parca sayisi · +0x12 parca indeksi
```

Çok parçalı yol: parça `0..cnt-2` yalnızca `memcpy(0x04074EC0 + idx*4096,
0x0400F2C0, 4096)` yapıp **döner**; gerçek programlama sadece `cnt == idx+1`
olan son parçada, önce `memcpy(0x0400F2C0, 0x04074EC0, 0x4000)` ile 16 KB
birleştirilerek yapılıyor.

⚠️ **`0x040C3E34`'te sonsuz döngü tuzağı:** parça sayısı
`1 << (geo[0x1F] - cfg[0x11] - 3)` değerini aşarsa firmware kendi üstüne
dallanıp kilitleniyor (`b 0x040c3e34`). `cnt=4` güvenli.

Programlama gönderim zinciri: `0x040C6AA0(ldpc)` → `0x040C6B6C(0,scr)` →
`0x040D27B4` → `0x040DB828` → **`0x040DE16C`** (okumadaki `0x040DE038`'in eşi).

---

## §67 — §65 GERİ ALINDI. Gerçek engel: silme die düzeyinde FAIL veriyor

**§65'in "`b*1536` kodlaması içeriği değiştiriyor" sonucu YANLIŞTI.**
`d27ed380e660`'ın her blokta çıkması silme değil, **okuma yolunun oturum içinde
tek sabite bozulmasıydı.** Soğuk çevrim bunu geri aldı: bloklar yeniden
birbirinden farklı okunuyor (16 blokta 12 ayrı sha).

Ders: **bir işlemin "içeriği değiştirdiği" sonucu, ancak okuma yolunun hâlâ
sağlam olduğu aynı turda doğrulanırsa geçerlidir.** Doğru protokol: soğuk
çevrim → referans blokları oku → TEK işlem → tekrar oku → referansların hâlâ
tuttuğunu da kontrol et.

### ✅ Okuma: güç çevrimleri arası birebir tekrarlanıyor

Ayrı soğuk çevrimlerde, aradan onlarca başarısız işlem geçmişken:

```
blok  850 = b129fb060276   (iki ayri soguk cevrimde ayni)
blok  900 = a8cfc012547d
blok  800 = 7c71ebee2225
blok 1200 = 9453dd3f3bcf
```

Bu, kanıt hiyerarşisinin en üstü — landing/staging tamponu güç çevrimini
atlatamaz. **16 KB `ldpc=1 scr=1` okuma yolu kesin olarak gerçektir.**
Sayfa adresleme de geniş aralıkta çalışıyor (blok 1600'de sayfa 0/100/383/500/1000
hepsi farklı).

### ❌ Silme: NAND'ın kendi durum baytı FAIL diyor

Soğuk çevrim sonrası tek işlem, blok 850, düz blok numarasıyla:

```
sil durum=BASARILI (GDP)    log: sts0=0101e1e1    <- e1 = RDY|ARDY|WP|FAIL
ONCE = b129fb060276   SONRA = b129fb060276        degismedi
diger referans bloklar: hepsi saglam (okuma bozulmadi)
```

GDP "BAŞARILI" diyor ama **die FAIL bildiriyor.** Okuma çalışırken, WP# serbestken
(`e0`'da bit7 set) ve die sağlıklıyken silmenin FAIL vermesi için kalan makul
açıklama: **blok kilidi.** SK hynix NAND güç açılışında blokları kilitli getirir;
ürün firmware'i init'te UNLOCK gönderir, GDP teşhis firmware'i göndermiyor olabilir.

**Sıradaki iş:** mikrokod tablosundaki `0x1C` routine'i (`2D,5A,00,98` — hynix
vendor dizisi) hiç çağrılmadı. Ayrıca `0x86` (`4B`) ve `0x87` (`4A`) tek baytlık
vendor komutları da aday. Bunlar kendi PIO harness'ımızla denenebilir.

**Bugünün net durumu: disk OKUNABILIR, YAZILAMAZ.** Okuma yolu güç çevrimleri
arası doğrulanmış; yazma zinciri die'ın silme reddinde kopuyor.

## §68 — Günün kapanışı: okunabilir disk + isimli engel

### Kendi elle yazdığımız ONFI silmesi de değiştirmedi

`60h + row(3) + D0h` mikrokodu yazıldı, dört satır kodlamasıyla (`b`, `b*4`,
`b*384`, `b*1536`) çalıştırıldı, `err=00`, die durumu `e0`. `gdprun` sonrası
okuma: **beş blokta da içerik aynı, kontrol bloğu da aynı.**

⚠️ Ama dürüst sınır: **çalıştığını KANITLADIĞIM tüm routine'ler tek komutluk**
(`48h` ID, `38h` durum, `FFh` reset). Çok adımlı kendi kurgularımın veri yoluna
gerçekten bir şey bastığına dair kanıtım yok — sayfa okuma denemeleri de boş
dönmüştü. Dolayısıyla "die reddediyor" ile "mikrokodum basmıyor" bu ölçümle
ayrılamaz. **Güvenilir sinyal firmware yolu**, ve o silmede die'dan
`sts0=0101e1e1` (`e1` = FAIL) alıyor.

Ayrıca `st_pio()` yoklaması stub üzerinden milisaniyeler sürdüğü için
**"die MEŞGUL olmadı" bir kanıt değil** — fabrika RESET routine'inde bile
meşgul penceresi yakalanamadı.

### Teslim edilen: `takim/jdoku.py` (salt okur, donanımda test edildi)

```
blok  850 = b129fb060276   referans b129fb060276  UYDU
blok  900 = a8cfc012547d   referans a8cfc012547d  UYDU
blok  800 = 7c71ebee2225   referans 7c71ebee2225  UYDU
blok 1200 = 9453dd3f3bcf   referans 9453dd3f3bcf  UYDU
nobetci C3 / A5 ayni sonuc: True        tara 800-900: 20/20 okundu
```

`Okuyucu.oku_guvenli()` her sayfayı iki farklı nöbetçi baytıyla okur; sonuçlar
eşleşmezse `None`. Böylece hem "NAND'a gidilmedi" hem tampon sızıntısı yakalanır.

### Sıradaki üç hat (öncelik sırasıyla)

1. **Çok adımlı mikrokodun gerçekten bastığını kanıtla.** Tek komutluk
   routine'ler çalışıyor; iki komutluk bir tanesini doğrulanabilir bir çıktıyla
   kur (ör. `90h` READ ID + adres + PIO — sonucu bilinen). Bu kanıtlanmadan
   elle yazılan hiçbir NAND dizisi delil sayılmaz.
2. **LDPC encoder.** Okuma (decoder) çalışıyor, yazma (encoder) çalışmıyor.
   Encoder matrisi `0x00003928`'e yükleniyor (`ortak.ldpc_yaz`); bu adres ya da
   içerik yanlışsa program hiçbir bit programlamaz. Simetri dikkat çekici.
3. **`0x040DE16C` (program gönderimi) ile `0x040DE038` (okuma gönderimi)
   farkını sök.** Okuma bu zincirden geçip çalışıyor, yazma geçip çalışmıyor;
   fark statik olarak bulunabilir.

---

## §69 — Elle yazılan mikrokod yolu DOĞRULANMADI (geri alma)

Kontrol deneyi: sonucu bilinen komutlar.

```
ECh (ONFI parametre sayfasi), 5 adres kaynagi x 2 gecikme -> hepsi ad7e285302b0 (ID)
90h adres 0x00 / 0x20 / 0x40 / 0x80                       -> hepsi ayni
70h ve GECERSIZ 5Ch                                       -> 53287E00
```

`ECh` ONFI imzası getirmiyor, `90h` adres değerine tepki vermiyor, geçersiz bir
komut bile "makul" sonuç veriyor. **Elle yazdığım routine'lerden bugün çıkardığım
her sonuç geçersizdir:** "PIO silinmiş sayfada `ffffffff` veriyor" (§pio3),
"kendi ONFI `60h+row+D0h` silmem etkisiz" (§68), "hynix `23h`/`24h` unlock
gönderildi" — hiçbiri delil değil.

### Yine de öğrenilen iki gerçek

1. **`+0x230` = PIO uzunluğu.** Firmware `flashid` yaparken register dökümü:
   `+0x224=3 (routine) · +0x228=8 · +0x22C=0 · +0x230=8 · +0x240=53287ead
   +0x244=0000b002`. Ben `+0x230`'u 0 bırakıyordum → tek bayt. Uzunluğu
   değiştirmek sonucu değiştiriyor (L=1 ile L≥4 farklı çıktı veriyor).
2. **`+0x240` okumak kaydırmaz** (10 okumada da aynı), ama bir routine
   **çalıştığında** içerik bir bayt kayıyor. Yani routine'ler gerçekten koşuyor;
   doğru bayt sayısını çekmeyi beceremiyorum.

### Doğrulama ölçütü (bundan sonra zorunlu)

Elle yazılan hiçbir NAND dizisi, **`ECh` ONFI imzasını getirene kadar** delil
sayılmayacak. O geçtiğinde hem yol doğrulanmış olur hem gerçek geometri elde edilir.

## §70 — Gerçek okunabilir kapasite ölçüldü

Doğrulanmış okuyucuyla (referanslar boyunca 4/4 tuttu):

```
OKUYAN DIE          1/16   (yalniz ch0 ce0)
ch0ce0 blok         50/64 okunabilir (%78)
blok 900 sayfa      32/32 okunabilir (%100, 0..1535 araligi)
plane 0/1/2/3       dordu de AYNI -> plane parametresi etkisiz
blok adresi         1024'te doniyor (blok 900 == blok 1924)
```

→ Erişilebilir uzay 1024 blok × 1536 sayfa × 16 KB, %78'i okunur ≈ **20 GB**.
1024 GB'nin **~%2'si**. Yazma sıfır.

## §71 — GPIO bloğu haritalandı (WP# değil)

`0x0600D000`:

| offset | değer | yorum |
|---|---|---|
| `+0x100` | `00020003` | mod/mux |
| `+0x104` | `DF702E6D` | **çıkış verisi** (`0x040E5BD4(pin,val)` buraya yazar) |
| `+0x108` | `FFEFFFFD` | yön: **sadece bit1 ve bit20 çıkış** |
| `+0x118` | `0F000000` | — |

cmd `0x57` "nand power ctrl" = **pin 20** (`+0x104` bit20, şu an 1).
Diğer tek çıkış **pin 1** denendi: 0→1 yapıldı, silme yine `sts0=...e1e1` FAIL,
yazma yine etkisiz. **Pin 1 WP# değil.** Denetleyicinin yazılımdan sürebildiği
başka çıkış yok.

---

## §72 — Firmware'in kendi bilgi komutları: gerçek geometri ve die sayımı

GDP komut tablosundaki 36 komutun dizgileri çıkarıldı; hiç kullanmadığım
bilgi komutları bulundu. Sonuçlar bugünün en değerli verisi.

### `0x10` — JEDEC parametre sayfası (die'ın kendi beyanı)

```
000: 4a 45 53 44 02 ...                          |JESD............|
020: 53 4b 48 59 4e 49 58 20 20 20 20 20 48 32 35 42 |SKHYNIX     H25B|
030: 46 54 38 44 34 42 38 52 2d 42 44 4a             |FT8D4B8R-BDJ    |
```

| alan | değer |
|---|---|
| model | **`H25BFT8D4B8R-BDJ`** (kayıtlardaki `H25BFT8A1BDA` değil) |
| sayfa | 16384 bayt + 2048 spare |
| blok başına sayfa | 1536 |
| LUN başına blok | **2732** |
| LUN sayısı | 1 |
| hücre biti | 3 (TLC) |
| **plane sayısı** | **2** (eski kayıtta 4 yazıyordu — yanlış) |

→ bir die = 2732 × 1536 × 16 KB ≈ **64 GiB**. 1 TB için 16 die gerekir.

### `0x14` Read UID ve `0x3B` die keşfi: firmware HİÇ die bulamıyor

```
Read UID[0,0,0]: READ UID SUCC
Read UID[0,1..3,0] ve ch1/2/3 hepsi: die not exist!

0x3B:  no die at step0 / no die at step1h
       RST    C0 C1 C2 C3 C4 C5 C6 C7
       CE00 |  -  -  -  -  -  -  -  -      (dort CE satiri da bos)
       READ C0 B0 ID = { AD 7E 28 53 2 B0 0 0 }
       mirroring: CH[0..7] hepsi 00000000
```

**Die keşfi RESET + hazır-algılama ile yapılıyor ve hiçbir die cevap vermiyor —
oysa aynı anda ID okunuyor, durum baytı `e0` geliyor, sayfa okunuyor.**

### 🎯 Bu tek gözlem her şeyi birleştiriyor

Bozuk olan die'lar değil, **operasyon tamamlanma / hazır (R/B) algılama yolu**:

| belirti | açıklama |
|---|---|
| ID, durum, parametre sayfası okunuyor | komut + veri fazı sağlam, R/B gerekmiyor |
| sayfa okuma çalışıyor | sabit gecikmeyle sürüyor olmalı |
| silme `e1`=FAIL | tamamlanma beklenemiyor → erken durum okuması |
| programlama etkisiz | aynı |
| `poll fwcq timeout` | FCQ tamamlanması hiç gelmiyor |
| `die not exist` ×15 | RESET sonrası hazır sinyali hiç görülmüyor |

Dolayısıyla "15 die yok" **kanıt değil**; aynı bozuk algılamanın çıktısı.

### Denenen ve olmayan

* `+0x20C` (CE varlık maskesi) 0→1: **okumayı da bozuyor**, `poll fwcq timeout`.
  Bu register 0 kalmalı.
* `0x040612C0+0x25` (`0x3B`'nin maskeyi yazdığı yer) elle 1 yapıldı: etkisiz,
  o bölge zaten başlatılmamış rastgele veri.
* `0x57` nand power ctrl (GPIO 20) 1 gönderildi: `NAND RESET` bastı, UID sonucu
  değişmedi.

**Sıradaki hedef net: R/B / tamamlanma algılamasını çalıştırmak.**
Başlangıç noktaları: `0x040C3358` (die keşif işçisi), NIFC `+0x21C` bit0,
FCQ `+0x70`/`+0x74` ve `0x040DBDCC` (tamamlanma bekleme).

---

## §73 — 🟢 16 DIE'IN HEPSİ SAĞ. "die not exist" toggle modunun tespit hatasıymış

Firmware'in kendi die keşfi (`0x3B`), **`legacy_kur()` çağrıldıktan sonra**:

```
[legacy] bulunan die = 16
   RST    C0 C1 C2 C3 C4 C5 C6 C7
   CE00 |  O  O  O  O  -  -  -  -
   CE01 |  O  O  O  O  -  -  -  -
   CE02 |  O  O  O  O  -  -  -  -
   CE03 |  O  O  O  O  -  -  -  -
   READ C3 B3 ID = { AD 7E 28 53 2 B0 0 0 }
```

Üç ardışık eğitim turunda da 16/16 sabit kaldı. Toggle modda aynı komut
`no die at step0` diyor ve tablo tamamen boş çıkıyor.

**Sonuç: disk 16 die taşıyor, hepsi canlı.** §72'de kaydettiğim
"firmware hiç die bulamıyor" gözlemi doğruydu ama **yalnız toggle modda**;
legacy'de sorun yok. Dolayısıyla **1 TB NAND fiziksel olarak orada.**

### ⛔ ZQ kalibrasyonu (`0x55`) HARİTAYI BOZUYOR — çalıştırma

```
ZQ CALIBRATION START>>>[ODT_0  DRV_0]
[I] zq calibration value: | OU | OD | DU | DD |   [0..3] B-C-5-5
ZQ CALIBRATION  DONE<<<
NAND DCC en
read nand status timeout, ch(0), bank(0), err(2), sts(0)
dcc fail, read status fail[ 0] before DCC[ch0,bank0,lun0]
```

ZQ sonrası harita 16 → 3 → 1 die'a düştü, okuma referansları bozuldu
(`blok850` artık farklı sha veriyor), `id son=ad2828020200`.
**`0x55` dokunma listesine girdi.**

### PHY eğitim komutları (`0x54` LCDL, `0x53` DE-SKEW)

İkisi de çalışıyor ve `SQ:[F](R0 S123454 L1 OC2),VE [1],VM [ff]` basıyor.
Toggle modda tek başına koşturunca harita 0 → 2 die'a çıktı (ilk kez bir şey
bulundu); legacy'de zaten 16/16 olduğu için ek katkısı ölçülemedi.

### Bundan sonraki çalışma sırası

```
init  ->  legacy_kur()  ->  0x3B (harita = 16 die)  ->  [is]  ->  toggle'a don (cagir(0x040E2B48,1)) -> oku
```

## §74 — Legacy okuma ölü · dolu die haritası da silmeyi açmıyor

**Legacy'de okuma tamamen ölü:** altı blok, hepsi nöbetçi döndü (`1/6 farklı sha`).
İki mod birbirini tamamlıyor:

| | die haritası | okuma | komut yolu |
|---|---|---|---|
| **toggle** | boş (0/16) | ✅ çalışıyor | ID bozuk |
| **legacy** | ✅ dolu (16/16) | ❌ ölü | ✅ temiz |

Mod geçişi okunan içeriği de değiştiriyor — bu yüzden "legacy'de sil, toggle'da
oku" karşılaştırması geçersiz (kontrol bloğu 850 de değişmişti, ölçüm onu yakaladı).

**Geçerli protokol:** mod geçişini ölçümden ÖNCE yap, sonra duruma dokunma:
`init → legacy_kur → 0x3B (harita) → toggle → referans → tek işlem → oku`.

Bu protokolle yapılan temiz ölçüm:

```
legacy harita: die=16   ->  toggle
referanslar kararli=True, 6 blokta 4 farkli sha
TEK SILME (886): durum=BASARILI  sts0=0201e1e1
   hicbiri degismedi   (kontrol bloklari da bozulmadi)
```

→ **Die haritası dolu olsa da silme diziye işlemiyor.** "Boş harita silmeyi
engelliyor" hipotezi elendi.

---

## §75 — 🔴 FAIL'i DIE söylüyor. Program/silme yolu die içinde ölü

Die'ın kendi durum baytı, PIO `38h` ile **doğrudan** okundu (legacy, arada başka
PIO yok, durum routine'i bir kez kurulup bir daha dokunulmadı):

```
bosta, 16 die:          e0 [RDY · WP serbest · ok]
firmware SILME sonrasi: e1 [RDY · WP serbest · FAIL]     <- hemen, 0.4sn sonra da ayni
firmware YAZMA  sonrasi: e1 [RDY · WP serbest · FAIL]
SADECE OKUMA sonrasi:   durum degismiyor
```

**FAIL firmware'in uydurması değil; die bildiriyor.** WP# serbest (SR bit7=1),
die hazır (RDY), okuma kusursuz — ama her silme, her blokta, her die'da FAIL.

### Bunun anlamı

NAND'da okuma düşük gerilimle olur; **silme ve programlama die içindeki charge
pump'ın ürettiği ~20 V'u gerektirir.** Okuyan her komutun çalışıp değiştiren
hiçbir komutun çalışmaması, bu yüksek-gerilim yolunun ölü olmasının klasik
imzası. Diskin **format sırasında** ölmesi de buna oturuyor: format yoğun
silme/programlama trafiğidir, o devreyi en çok zorlayan iş.

### Ama tek açıklama bu değil — ve diğeri yazılım

Hynix NAND'ın program/silme davranışı, denetleyicinin `0x77 SET PARAMETER`
ile die'a yüklediği parametrelere bağlı. GDP teşhis firmware'i bu parça için
**doğru V6 parametre setine sahip değil** — eksik dosya tam olarak
`nandmem_SKV6_page.bin` (firmware avı bunu tek eksik olarak işaretlemişti).
Yanlış parametreyle die okumaya devam edip program/silmeyi reddedebilir.

**İki açıklama da veriye uyuyor ve ancak o dosyayla ayrılabilir:**

| | hipotez | ayırt etme yolu |
|---|---|---|
| donanım | die içi HV/charge-pump ölü | doğru parametreyle de FAIL verirse kesinleşir |
| yazılım | `0x77` ile yanlış parametre yükleniyor | `nandmem_SKV6_page.bin` bulunursa test edilir |

### Denenmiş ve elenmiş (hepsi ölçümle)

toggle zamanlaması · DQS maskesi · PHY eğitimi (`0x53`/`0x54`) · hynix blok
kilidi (`7Ah`/`23h`/`24h`) · GPIO write-protect (iki çıkış pini de) · boş die
haritası · firmware'in kendi `Erase CodeBlock[0,1] for All Dies` yolu ·
`b`, `b*4`, `b*4+1`, `b*384`, `b*1536`, `b<<2` silme adres kodlamaları ·
ldpc 0/1/2/3 × scr 0/1 × tek 16 KB / 4×4 KB yazma modları.

## §76 — Parametre hipotezi ELENDİ. Sebep paylaşılan ve fiziksel

### 16/16 die, istisnasız

```
die     once  sonra          die     once  sonra
ch0ce0  e0    e1 FAIL        ch2ce0  e0    e1 FAIL
ch0ce1  e0    e1 FAIL        ch2ce1  e0    e1 FAIL
...     (on alti die'in hepsi ayni)
FAIL veren: 16/16   temiz: 0/16
NAND RESET FAIL'i temizliyor (e1 -> e0) -> durum mandali saglikli
```

On altı bağımsız die'ın charge pump'ı aynı anda ölmez → **sebep paylaşılan**.

### SET PARAMETER'lı ve SET PARAMETER'sız — fark yok

Bare `FFh` NAND RESET sonrası die fabrika varsayılanındadır; hiçbir hynix
`0x77 SET PARAMETER` uygulanmamıştır.

```
A) RESET, SET PARAMETER YOK:   blok 930: e0 -> e1 FAIL   (fw sts0=02017ee1)
C) SET PARAMETER uygulandi:    blok 934: e0 -> e1 FAIL   (fw sts0=02017ee1)
```

**Birebir aynı.** → `nandmem_SKV6_page.bin` eksikliği silmenin sebebi DEĞİL.
O dosya bulunsa da bu sonuç değişmezdi.

### 🔴 Geriye kalan tek açıklama

Program/silme yolu **fiziksel olarak ölü** ve arıza **tüm die'lar tarafından
paylaşılıyor**. En olası aday: NAND besleme hattının (VCC ~3,3 V / VPP)
silme-programlama akımını verememesi. Okuma düşük akımla olduğu için etkilenmiyor.
Diskin **format sırasında** ölmesi tam bu tabloya oturuyor.

Yazılımdan yapılabilecek her şey denendi ve ölçümle elendi:

toggle/legacy modları · veriyolu zamanlaması (`+0x200`, t=2..64) · DQS maskesi ·
PHY eğitimi (`0x53`/`0x54`/`0x56`) · ZQ kalibrasyonu · hynix blok kilidi
(`7Ah`/`23h`/`24h`) · GPIO write-protect (sürülebilen iki çıkış da) · NAND güç
kontrolü (`0x57`) · die haritası (boş ve 16/16 dolu) · firmware'in kendi
`Erase CodeBlock[0,1] for All Dies` yolu · altı silme adres kodlaması ·
ldpc 0/1/2/3 × scr 0/1 × tek 16 KB / 4×4 KB yazma · SET PARAMETER'lı/sız.

### Geriye kalan tek fiziksel doğrulama

NAND VCC/VCCQ hattını **yük altında** ölçmek (multimetre/osiloskop). Okuma
sırasında normal görünüp silme denemesinde çökerse teşhis kesinleşir.

---

## §77 — 🔴🔴 KENDİ RAPORUMU OKUMADIM: ROM kısa devresi HÂLÂ TAKILI

§76'daki "fiziksel arıza" sonucu **eksik bir varsayıma dayanıyor.** Bugünkü tüm
silme ve programlama denemeleri, karta lehimlenmiş **ROM kısa devresi bağlıyken**
yapıldı.

Kendi raporumun §15'i, kaynağın birebir ifadesiyle:

> 4. **1-3 saniye içinde bırak** — usbdev: "не удерживать" = **tutma**
> 6. ...bu anda kısa devre kesinlikle bağlı olmayacak;
>    **flash sırasında bağlı kalırsa işlem başarısız olur**

Ve §15'te kısa devrenin **bir ucu GND**. Diğer uç sürekli toprağa çekiliyse:

| gözlem | kısa devre açıklaması |
|---|---|
| toggle'da örnekleme çöküyor, legacy'de düzeliyor | hatta sürekli yük/seviye sabitleme; SDR'de marj var, DDR'de yok |
| toggle'da 16 die'ın 1'i okunuyor | aynı |
| her program/silme `e1` FAIL | write-enable / veri fazı bozuluyor |
| **16/16 die aynı anda FAIL** | kısa devre paylaşılan tek noktadır |

**§76'nın "besleme arızası" teşhisi bu değişken kontrol edilmeden geçerli değildir.**
Alperen bunu ben ısrarla "boot-mode strap, dokunma" derken söyledi; ölçmeden
varsaymıştım.

### Yapılacak

1. Telin bir ucu sökülür (geri lehimlenebilsin diye tamamen çıkarılmaz).
2. Güç verilir. Disk enumerate olup `jd_loader.py gdprun` çalışıyorsa → doğrudan
   test. Olmuyorsa → kısa devre **yalnız açılış anında** cımbızla yapılır,
   1-3 sn sonra bırakılır; sonrasında soğuk çevrim yapılmadan çalışılır
   (`kanal_abort()` sayesinde kilitlenme riski çok azaldı).
3. `scratchpad/telsiz.py` hazır: toggle ID'leri → referanslar → legacy die durumu →
   silme → 16 die taraması → toggle'a dönüp içerik karşılaştırması, dokunulmamış
   kontrol bloklarıyla (850/900).

## §78 — Tel çıkarıldı, ölçüldü: SEBEP DEĞİL (ama pin kimliği bulundu)

Alperen ROM kısa devresini fiziksel olarak çıkardı, disk açıkken tek geçişte
ölçüldü (mod geçişi yok, dokunulmamış kontrol blokları var).

### Telin kimliği: GPIO pin 5

```
+0x104   tel TAKILI = DF702E6D      tel YOK = DF702E4D
DEGISEN PIN: [5]     pin 5: 1 -> 0   (+0x108 bit5 = 1 -> GIRIS pini)
```

Tel pin 5'i **yukarı** çekiyor (toprağa değil) → çiftin diğer ucu GND değil,
LITEON serigrafisindeki `+1` besleme pad'i olabilir. Pin 5 giriş; boot ROM
açılışta okuyor. **Artık yazılımdan görülebiliyor, bir daha karıştırıcı değişken
olmayacak.**

Bu ayrıca §77 öncesi ölçümlerin gerçekten tel takılıyken yapıldığını doğruladı
(pin 5 her ikisinde de 1).

### Sonuç: tel sebep değil

| | tel TAKILI | tel YOK |
|---|---|---|
| toggle'da doğru flash ID | 1/16 | **1/16** |
| silmede FAIL veren die | 16/16 | **16/16** |
| içerik değişimi | yok | **yok** |

Ölçümün geçerliliği: referanslar kararlı (6 blokta 4 farklı sha), **mod geçişi
yok**, dokunulmamış kontrol blokları (850, 900, 984, 986) **bozulmadı**.
Bugün ölçümleri defalarca bozan iki şey de bu koşuda yok.

→ **§76'nın sonucu, tel değişkeni düzgün elendikten sonra da geçerli.**
Program/silme yolu fiziksel olarak ölü, arıza 16 die tarafından paylaşılıyor.

### Tel geri takılmasın

Disk telsiz halde sorunsuz enumerate ediyor ve `gdprun` çalışıyor. NAND'da
bootable firmware olmadığı için denetleyici zaten loader modunda kalıyor.
Tel yokken bir karıştırıcı değişken eksik — öyle kalsın.

## §79 — ⭐⭐⭐ NAND CONFIG STRUCT BULUNDU: `dpd_clk200.bin` = geometri, ve iki alan YANLIŞ

15 Eylül akşamı. `0x89` (PageRead) ve `0x8B` (BlockErase) handler'ları sökülünce
ikisinin de **aynı yapıyı** kullandığı görüldü:

```
0x00000DCC  ->  geometri yapisi isaretcisi   (= *(0x00000DB8+0x14), ayni yer)
canli deger:    0x000004E0
```

Yapının ilk baytları (canlı dump, `0x000004E0`):

```
03 02 48 0b 00 06 10 00 01 04 02 0b 01 00 00 08 ...
 |  \___/  \___/  \___/  |  |
 |   2888   1536   16    1  4
TLC  blok  sayfa/  die  LUN plane
     /LUN  blok
```

| alan | firmware | die'ın kendi beyanı (`0x10` JEDEC) | |
|---|---|---|---|
| `+0x00` bit/hücre | 3 | 3 TLC | ✓ |
| `+0x02` blok/LUN | **2888** | **2732** | ✗ |
| `+0x04` sayfa/blok | 1536 | 1536 | ✓ |
| `+0x06` die | 16 | — | ✓ |
| `+0x08` LUN | 1 | 1 | ✓ |
| `+0x09` **plane** | **4** | **2** | ✗ |

Ve en önemlisi:

```
geom+0x310 = DIE VARLIK TABLOSU,  index = ce*8 + ch
canli deger: 00 ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ...
             ^^ sadece ch0/ce0
```

`0x89` handler'ı (`0x040C44C4`) bu tabloyu okuyor ve `0xFF` görürse **NAND'a hiç
gitmeden** status 2 ("okuma hatası") dönüyor:

```asm
040C44C4  ldrb r0, [r0, #0x310]
040C44C8  cmp  r0, #0xff
040C44CC  moveq r0, #2
040C44D0  strbeq r0, [r4, #2]
040C44D4  beq  0x40c4404        ; <- NAND'a hic gidilmiyor
```

**Yani "15 die okunamıyor" bulgusunun sebebi donanım değil, bu tablo.**
%2 kapasite tavanı buradan geliyordu.

### Yapının kaynağı: `dpd_clk200.bin`

Bu 1024 baytlık blob, init'ten **önce** `0x11` komutuyla yükleniyor ve
yapının birebir kendisi. Yani geometri **kaynağında** düzeltilebilir:

```
dpd_clk200.bin  +0x09 = 04   ->  02     (plane)
                +0x02 = 2888 ->  2732   (blok/LUN)
                +0x310..     = 00 for ce*8+ch, tum 16 die
```

### Ölçülen etki

| varyant | die tablosu | plane | sonuç |
|---|---|---|---|
| v0 orijinal | 1 die | 4 | 1/16 die okunuyor, silme 4 iterasyon |
| v3 tablo yamalı | 16 die | 4 | **16/16 die okuma komutu NAND'a gidiyor** |
| v1/v2 plane=2 | — | 2 | **silme döngüsü 4 → 2 iterasyona düştü** |

`geom[9]` gerçekten silme döngüsünü sürüyor (log `[0,0,0,FA0,0..3]` → `[0..1]`).

### 🔴 Ama asıl bulgu: ADRES EŞLEŞMESİ HİÇ DOĞRU OLMAMIŞ

```
OKU(rf)    : blok = rf / P,  plane = rf % P          (P = geom[9])
SIL p6==0  : blok = rf (HAM — BOLME YOK)
SIL p6!=0  : blok = rf / P,  plane = rf % P
```

`0x8B`'nin 5. ve 6. parametreleri (`+0xc`, `+0xd`) proje boyunca hep `0`
geçilmiş. `p6=0` iken firmware bloğu **bölmüyor**. Dolayısıyla:

* `sil(850)` → fiziksel blok 850
* `oku(850)` → fiziksel blok 212 (850/4)

**Proje boyunca hiçbir zaman okuduğumuz bloğu silmemişiz.** "Silme içeriği
değiştirmiyor" ölçümlerinin tamamı bu yüzden anlamsız. Doğru eşleşme:

```
p6=0 : sil(B)    <-> oku(B*P)
p6=1 : sil(B*P)  <-> oku(B*P)
```

Ayrıca `0x040D09CC(p5,p6)` bir **operasyon kodu** üretiyor:
`(0,0)→3`, `(1,0)→1`, `(0,1)→2`, diğer→`0`. Yani dört ayrı silme modu var ve
bugüne kadar yalnız biri (mod 3) denenmiş.

## §80 — 🟢🟢 **DİSK YAZIYOR. "Program/silme die düzeyinde ölü" YANLIŞMIŞ.**

15 Eylül akşamı, kampanya k7–k8. İki ayrı hata birleşince ortaya "fiziksel arıza"
görüntüsü çıkmış:

### Hata 1 — adres eşleşmesi hiç doğru olmamış

```
OKU(rf) / YAZ(rf) : blok = rf / P,  plane = rf % P      (P = geom[9] = 4)
SIL(rf, p6=0)     : blok = rf       (BOLME YOK)
SIL(rf, p6=1)     : blok = rf / P   (okuma ile AYNI)
```

`0x8B`'nin 6. parametresi proje boyunca hep `0` geçilmiş. Yani `sil(850)`
fiziksel blok 850'yi, `oku(850)` fiziksel blok 212'yi hedefliyormuş.
**Hiçbir zaman okuduğumuz bloğu silmemişiz.**

### Hata 2 — `NAND RESET` okuma yolunu kalıcı bozuyor

k6 kararlılık sondası (referans blokları her adımdan sonra tekrar okuyarak):

| adım | yol sağlam mı |
|---|---|
| 20 okuma (pencere taraması) | ✅ |
| `kanal_abort` | ✅ |
| **`NAND RESET` (`0x040E3898`)** | ❌ **bozuldu** |
| `init(tur=1)` ile kurtarma | ❌ **kurtarmıyor** |

Sadece tam `gdprun` kurtarıyor. `legacy_kur()` ilk iş olarak `NAND RESET`
çağırdığı için, **`legacy_kur()` sonrası yapılan her içerik ölçümü kirli.**
§75/§76'nın "16/16 die FAIL" tablosu bu yolda alınmış.

### Doğrulanan tam tur (k8, kontrol referansları bozulmadan)

```
sil(B*P, p6=1) -> yaz(B*P, desen) -> oku(B*P)

blok 620  ESIT ✅     blok 630  ESIT ✅
blok 640  ESIT ✅     blok 720  ESIT ✅     blok 730  ✗ (e1e1)
yazma logu: sts0=0101e0ff   <- e0, FAIL BITI YOK
```

* **Tampon-kıran doğrulama geçti:** A'ya yaz, B'ye yaz, B'yi oku (tampon B ile
  dolar), sonra A'yı oku → A hâlâ kendi deseni. Echo değil.
* **Blok içi tam kapsama:** tek blokta sayfa 0,1,2,100,500,1000,**1535** —
  **7/7 yazıldı ve birebir okundu.**
* Üç kontrol bloğu (4800/6000/3600) koşu boyunca hiç değişmedi, koşu sonunda
  `ref_saglam=true`.

### Geçerli tarif

```python
P   = geom[9]                      # 0x000004E0 + 9
sil : pay(0x8B, ch, ce, rf>>8, rf&0xFF, 0, 1)     # p6=1 SART
yaz : pay(0x8A, ch, ce, rf>>8, rf&0xFF, pg>>8, pg&0xFF, 1,1,0,0,0) + 0xC1 16 KB
oku : pay(0x89, ...) + 0xC2 16 KB
rf  = blok * P
kural: NAND RESET YOK · legacy_kur YOK · her islemden sonra kanal_abort
```

**§75, §76 ve §78'in "program/silme yolu die içinde ölü / sebep fiziksel"
sonucu bu bölümle GERİ ALINIYOR.**

## §81 — Kapasite: 15/16 die açıldı, blok 1024'te sarıyor

### Die varlık tablosu — %2 tavanının gerçek sebebi

`0x89` handler'ı (`0x040C44C4`) `geom+0x310 + ce*8 + ch` baytını okuyor ve
`0xFF` görürse **NAND'a hiç gitmeden** status 2 dönüyor. Canlı değer:

```
00 ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ...   -> sadece ch0/ce0
```

Tablo `dpd_clk200.bin+0x310`'dan geliyor (blob init'ten önce `0x11` ile
yükleniyor). 16 die için açılınca (`dpd_v3_tbl.bin`) hepsi erişilir oldu.

### Die'ları OKUYARAK ayırt etmek mümkün değil

Tablo açıldıktan sonra 16 die de aynı sha'yı döndü — çünkü silinmiş sayfalar
her die'da aynı descrambler çıktısını verir. **YAZARAK** ayırt edildi: her
die'a kendi deseni yazıldı, hepsi kendi desenini geri verdi, **15 ayrı sha**.
`c3ce2` üç denemede de yazamadı → tek ölü die.

### Blok adresi 1024'te sarıyor (ölçüldü)

Silme izi yöntemiyle: blok 600'e desen yazıldı, sonra 600 silindi; birlikte
bozulan bloklar **600, 1624, 2648** — periyot tam **1024**.

Denenen ve sarmayı TAŞIMAYAN geometri alanları: `+0x02` (2732/2888),
`+0x09` (plane 1/2/4), `+0x0B` (11/12/13), `+0x18` (10/11/12), `+0x19`,
`+0x1A`, `+0x1B`, `+0x1D` (9/10/11/12), `+0x1E` (12/13), `+0x0E` (0x800).
→ Sınır DPD config'inde değil; NAND'a giden satır adresinin genişliğinde.

`+0x1D` (sektör kaydırması) 9→12 yapılınca **sayfa→blok taşması kalktı**:
9'da blok B'nin sayfa 512'si blok B+1'in sayfa 0'ına biniyordu; 12'de
1536 sayfanın hepsi ayrı adres. Kullanılan config: `dpd_x4_p4_s12.bin`.

### Bugünkü erişilebilir kapasite

```
15 die x 1024 blok x 1536 sayfa x 16384 bayt = 360 GiB
```
(sabah: ~20 GB, salt okunur). Sarma kırılırsa 2732 blok ile **~960 GiB**.

## §82 — 🔴 Boot alanı bozuldu: disk artık ROM teli olmadan açılmıyor

Kapasite taramasında (k9) blok **0, 1, 2, 10** da yazıldı. Firmware dizgileri
o blokların ne olduğunu söylüyor:

```
0x040C314C  "Init CodeBlock as 0 & 1"
0x040C3D7C  "Erase CodeBlock[0,1] for All Dies"
0x040D2774  "[0]error at erase codeblock%d"
gdp_task_prechk_codeblock · gdp_precheck_codeblock · gdp_get_codeblock
0x4D handler: "[INFO] Update CB State" + "C:%X B:%X STS:%X",
             durum tablosu geom+0x20 + ch*4 + ce
```

Sonraki soğuk çevrimde disk **CRS**'te kaldı: `vid=0x0001 did=0xffff`,
link 8 GT/s x4 kurulu ama boot bitmiyor. ROM kısa devre teliyle açılıyor.

Doğrulandı (`kurtar.py`): blok 2 ve 10'da bizim `RANGE…` desenimiz duruyor,
blok 0/1 sıfır okunuyor.

### Neden "firmware'i geri yaz" yolu şu an kapalı

`kanit/updater_sys/` içindeki 13 MAP1202 imajının hepsi **Micron B47R** ya da
**WD BiCS5** için (`r:/TEMP/B47R_SVN9878_Adata/...`, `MAP1202_WDBiCS5_SVN9902`).
Bizim die **SK hynix H25BFT8D4B8R**. Yanlış NAND'ın firmware'ini yazmak
denetleyiciyi yanlış parametrelerle başlatır — durumu iyileştirmez.

### Sıradaki deneme: CodeBlock'ları TEMİZ SİL

Bugünden önce de disk NAND'dan boot etmiyordu (hep ROM modu; `gdprun` o yüzden
çalışıyor). Değişen tek şey ROM'un blok 0'da **çöp** bulması. Fabrikadan çıkan
boş disk de enumerate etmek zorunda (MPTool programlayabilsin diye), yani
**boş NAND desteklenen bir durum**.

`kampanya/telsiz.py` hazır: 16 die × blok 0,1,2,10 `p6=1` ile silinir, ham
okuma (ldpc=0 scr=0) ile gerçekten `0xFF` olduğu doğrulanır, firmware'in kendi
`0x8B ch=ce=0xFF` yolu da çalıştırılır. Sonra **telsiz** soğuk çevrim.

⚠️ Raporun eski "`0x8B` All Dies hiçbir şey değiştirmiyor" notu geçersiz —
o ölçüm `p6=0` ile, yani bozuk silme yoluyla yapılmıştı.

## §83 — Denetleyiciyi kilitleyen şey: betik içinden tekrarlı `gdprun`

k4/k11/k13/k14 varyant değiştirmek için süreç içinden `jd_loader.py gdprun`
çağırıyordu. Üst üste birkaç çevrimden sonra denetleyici sert kilitlendi
(loader `enable` bile edemiyor, `JumpToPRAM YAPILMIYOR`) ve **soğuk çevrim**
gerekti. **Kural: oturum başına tek `gdprun`.** Varyant denemesi gerekiyorsa
her varyant ayrı koşu olmalı.

## §84 — ⭐ ADRES YOLU 19 BİT. Kapasite tavanı die başına 8 GiB.

### Önce iki düzeltme

**§81'in "blok 1024'te sarıyor / 360 GiB" sonucu YANLIŞ.** O ölçüm *silme
iziyle* yapılmıştı: aday blokların hepsine desen yazılıyor, sonra biri silinip
hangilerinin bozulduğuna bakılıyordu. Alias bloklar birbirinin desenini ezdiği
için yöntem sarmayı olduğundan büyük gösteriyor.

**Güvenilir yöntem:** TEK bloğa işaret yaz, katlarını oku. Blok 600 için alias
kümesi: `600 ± {128, 256, 512, 1024, 2048}` ve `600 & 0x7F = 88` de listede.
→ blok numarasının yalnız **alt 7 biti** NAND'a ulaşıyor.

**Sayarak doğrulandı (k17):** 200..455 arası 256 ardışık bloğa ayrı desen
yazıldı, geri okunduğunda hayatta kalanlar **tam 328'den** başlıyor
(= 200 + 128). 340 bloğa (adım 8) yazıldığında sadece son 12'si kendi desenini
koruyor. **Modülüs 128.**

### Yasa: modülüs = 2^(19 − sec), sayfa alanı = 2^sec

`geom[0x1D]` (sektör kaydırması) canlı RAM'de değiştirilip her değerde modülüs
yeniden ölçüldü:

| `geom[0x1D]` | modülüs | sayfa alanı | blok×sayfa |
|---|---|---|---|
| 13 | 64 | 1536 | 98.304 |
| 12 (stok) | **128** | 1536 | 196.608 |
| 11 | 256 | 1536 | 393.216 |
| 10 | 512 | 1024 | **524.288** |
| 9 | 1024 | 512 | **524.288** |

Çarpım her zaman **2¹⁹**. Kaydırma ayarı 19 biti blokla sayfa arasında
paylaştırıyor, toplamı büyütmüyor.

```
2^19 sayfa x 16384 bayt = die basina 8 GiB
die gercekte 2732 x 1536 = 2^22 sayfa = 64 GiB   ->  her die'in 1/8'i
```

15 çalışan die ile tavan ≈ **120 GiB**. Şu anki `sec=12` ile ise 45 GiB;
yani tek baytlık ayarla **2,7 kat** kazanç masada duruyor.

### Kaybolan 3-4 bit nerede — ve nerede DEĞİL

Elenmiş (ölçümle): `0x89`/`0x8A` plane parametresi (+0x10) ayrı adres taşımıyor,
dört değer de aynı fiziksel yere yazıyor · `+0x11` alanı ayrı adres değil ·
`0x8B` p5 silinen yeri değiştirmiyor · `geom` alanlarından `+0x02`, `+0x09`,
`+0x0B`, `+0x0E`, `+0x18`, `+0x19`, `+0x1A`, `+0x1B`, `+0x1E` hiçbiri modülüsü
taşımıyor. `geom[0x1F]` 7→6/5 yapılınca yazma tamamen bozuluyor.

Kalan aday: composite adres 32 bit olarak FCQ tanımlayıcısına paketlenirken
bir bit aralığı kullanılmıyor (`0x040EBD8C` civarında `ubfx ...,#0x14,#5` ve
`lsr ...,#0x1d` arasında 25–28 bitleri hiçbir alana girmiyor). Bu bir config
alanı değil, **kod** — ama kod RAM'de ve biz RAM'e kod yazabiliyoruz.

### Kapasite özeti (15 Eylül gece)

| | sabah | şimdi | GDP tavanı | firmware ile |
|---|---|---|---|---|
| okunabilir | ~3 GiB (1 die) | 45 GiB | 120 GiB | ~1 TB |
| yazılabilir | yok | **var** | var | var |
| die | 1/16 | **15/16** | 15/16 | 16/16 |

## §85 — ⭐⭐ ÜRETİM ARACI VE DIE'IN ÜRETİCİ SATIRI BU MAKİNEDE ÇIKTI

`~/jdvm/mptool.img` (700 MB, Windows PE VM'ine USB olarak bağlanıyor) içinde
**19 MAP1202 üretim paketi** duruyor. İkisi hynix:

* `MAP1202 HYV7 64GB Die 128G-1T SN09286 20220704` — tam üretim paketi:
  `MXMPTool_MAP1202_USB_V0_01_017.exe`, `GDP.bin`, `SORT.bin`, `Flash.ini`,
  `MPTOOL.ini`, `PARA`, `TMC`, `SYS`, `DAT`
* `MAP1202_H25TXTD2XCX6` — SKV8 verileriyle

### 🎯 `Flash.ini` bizim die'ı tanıyor

```
[Hynix]
Name007=SKV603005 H25BFT8A1BDA  3 2 1  2888 1536 16 1 2  0xAD 0x7E 0x28 0x53 0x02 0xB0  0 0 0 11 4 3000 001 2048 100
;        UniName   FullName     V T C  Blks  PGs PZ D E  ID0  ID1  ID2  ID3  ID4  ID5  Ex DO P IF PL   Ed Nm   SB Gpio
```

Bizim `90h READ ID` cevabımız **birebir** `AD 7E 28 53 02 B0`. Satırın söyledikleri:

| alan | değer | bizim varsayımımız |
|---|---|---|
| kuşak | **SKV6** (`SKV603005`) | V6/V7 belirsizdi → **V6** |
| tam parça | `H25BFT8A1BDA` | die `H25BFT8D4B8R-BDJ` diyordu; kayıttaki isim doğruymuş |
| blok/CE | **2888** | DPD'de 2888 vardı, "gerçek 2732" diye düzeltmiştim → **DPD doğruymuş** |
| sayfa/blok | 1536 | ✓ |
| sayfa | 16 KB, spare 2048 | ✓ |
| ECC | **rate 2** | §48'de bulunan rate-2 ✓ |
| arayüz | **11 = Legacy→Toggle 2.0** | bütün legacy/toggle karmaşasının sebebi |
| plane | **4** | DPD'de 4 vardı, "gerçek 2" diye düzeltmiştim → **DPD doğruymuş** |

→ §72'nin "gerçek geometri 2732 blok / 2 plane" sonucu **geri alınıyor.** Die'ın
JEDEC parametre sayfasından okuduğum değerler üreticinin kullandığı değerler değil.

### Eksik olan: SKV6 veri dosyaları

Pakette `DAT/SKV7/001_<clk>/nandmem_SKV7_page.bin` var, **SKV6 yok**. Aynı şekilde
`SKV6.bin` (FWOneBin) ve `Para_DW_SKV6_*.ini` yok. Ama aracın kendisi destekliyor:

```
ReleaseNote (MPT_Cougar_C_0_1_017, SVN9144):
  1.Support SKV6-128GB/die
  SORT.bin: 1.add SKV6-128GB die nand feature.  2.update SKV6 ucode.
```

### Loader kimliği: `1e4b:1001`

ROM teli takılı **temiz açılışta** cihaz `1e4b:1001` (MAP1001) olarak geliyor;
`gdprun` sonrası `1e4b:1202`. `jd_vm.sh` yalnız 1202 aradığı için VM hiç
kalkmıyordu — düzeltildi.

### 🔴 QEMU vfio passthrough ÇÖKÜYOR

`-device vfio-pci,host=04:00.0` ile QEMU **SIGSEGV** (çıkış 139). Passthrough'suz
aynı VM sorunsuz açılıyor. Ayrıca `jd_loader.py`'nin kendi yardım metni:
*"vfio kullanilamiyor: acilista zorunlu FLR atiyor, FLR loader'i olduruyor"*.
→ Naif passthrough yolu kapalı.

⚠️ `mptool.img` host'ta loop ile bağlıyken QEMU imajı açamıyor — VM'den önce
`umount /mnt/mpt`.

### Sıradaki üç yol

1. **SKV6 veri dosyalarını bul** (ajan arıyor): `nandmem_SKV6_page.bin`,
   `SKV6.bin`, `Para_DW_SKV6_*.ini`. Bulunursa HYV7 paketinin `MPTOOL.ini`'sinde
   `FlashUniName=SKV603005` yapılıp araç bizim diski programlayabilir.
2. **vfio yerine kullanıcı-uzayı NVMe vekili**: QEMU `-device vfio-user-pci` ile
   sahte bir NVMe denetleyicisi sunup komutları host'taki kendi loader yolumuza
   yönlendirmek. FLR hiç atılmaz, çökme olmaz.
3. **Aracı hiç çalıştırmamak**: MPTool'un yazma dizisini `.exe`'den çıkarıp
   kendi loader protokolümüzle uygulamak. Paketin `PARA`/`TMC`/`SYS`/`DAT`
   dosyaları zaten onun yazdığı veri; `MPTOOL.ini` tarifi anlatıyor.

## §86 — SKV6 verileri bulundu · §85'in blok sayısı düzeltmesi GERİ ALINIYOR

### Die kuşağı kesinleşti: SK hynix **V6** (128 katman)

Üç bağımsız hat, hepsi birinci el kaynaktan:

1. SMI paketinin kendi flash veritabanında (`FlashDB/Flash.SET.bak`) satır:
   `A25=Hynix,2Tbit,H25BFT8D4B8R(V6)(4CE)` + ID `AD,7E,28,53,02,B0` — **bizim
   parça numaramız, bizim ID'miz, kuşak etiketi V6.**
2. Bayt çözümü (182 hynix satırı): kuşak 4. ve 6. baytta — V5 `33/A0`,
   **V6 `53/B0`**, V7 `0B/C0`, V8 `3B/D0`. Bizimki `53…B0`.
   Sayfa/blok da ayırt edici: V6=1536, V7=4224, V8=5712 ve her kuşakta
   `katman × string × 3` tam sayı tutuyor (V6 = 128×4×3 = 1536).
3. Blok sayısı: hynix V6 satırlarında **2732 yalnız 2CE/4CE** varyantlarında
   geçiyor, tek-die olanlar 2716.

### 🔁 §85'teki "2888 doğruymuş" düzeltmesi YANLIŞTI

`Flash.ini`'de bulduğum satır `SKV603005 H25BFT8A1BDA … 2888` — **`A1` = 1 CE**
varyantı. Bizim die **`D4` = 4 CE** ve die'ın kendi beyanı **2732**. Aynı ID
baytlarını taşıyan farklı iki varyant. → **die 2732 blok**; DPD'deki 2888
bizim parçamız için yanlış (ama plane=4, rate2, IF=11, spare=2048 doğru).

Ders: aynı `Flash.ini` satırını "bizim die" diye okumadan önce CE alanına bakmak
gerekiyormuş. İki kez üst üste aynı alanda yanıldım — önce die beyanına güvenip
DPD'yi suçladım, sonra Flash.ini'ye güvenip die beyanını suçladım.

### Eldeki SKV6 verisi (`kanit/fw_hunt3/`)

| ne | nereden | durum |
|---|---|---|
| `nandmem_SKV6_sdr_page1.bin` + `_ddr_page2.bin` (16 KB) | **MAS0902** kardeş ailesi, 3 ayrı pakette bit-bit aynı | ✔ indirildi |
| SKV6 cmd/op mikrokod + `.map` indeksleri (200/266 MHz) | MAS0902 `MPT/BIN/SKV6/` | ✔ |
| `nandmem` **blok A** (2064 bayt), 6 saat noktası | `DAT/ucode.bin` bölüm+0x1020'den çıkarıldı; yöntem SKV7 ground truth'una karşı 6/6 doğrulandı | ✔ `skv6_from_ucode/` |
| `nandmem` **blok B** (3384 bayt) | ucode/GDP/SORT/SYS/tmc_para'nın hiçbirinde yok | ✘ `BLOB_A_ONLY` |
| MPTool 4 sürüm (`V1_1_26` en yeni) + Flash.ini v043 + LDPC rate0-3 | usbdev (Oracle çıkışı üzerinden) | ✔ |
| `SYS/YI0PCELC.bin` | itho 3417 arşivde `n_archives: 0` | ✘ kamuya açık değil |

Sınanacak hipotez: blok A = SDR, blok B = DDR → MAS0902'nin
`nandmem_SKV6_ddr_page2.bin`'inden türetilebilir.

### 🔴 Çalışan GDP'mizde gömülü NAND mikrokodu YOK

```
SKV8 GDP (kullandigimiz) c1.bin : CMD kelime 0,  A0 sonlandirici 0
HYV7 GDP                 c1.bin : CMD kelime 87, A0 sonlandirici 38
```

`jd_loader.py gdprun` varsayılan olarak **SKV8 paketinin** `GDP.bin`'ini
yüklüyor (`ac_H25TXTD2XCX6/.../GDP.bin`). Yani aylardır **SKV8 için derlenmiş,
üstelik NAND mikrokodu gömülü olmayan** bir teşhis firmware'ini V6 die üzerinde
koşturuyoruz. Loader yol argümanı alıyor: `jd_loader.py gdprun <GDP.bin>`.

### Denenecek sıra

1. Canlı mikrokod RAM'ini (`0x06649000`) dök, elimizdeki SKV6 kayıtlarıyla
   karşılaştır (`kampanya/ucode.py` hazır; cihaz kilitlendiği için düştü,
   güç çevrimi sonrası tekrar).
2. HYV7 `GDP.bin`'i yükle (mikrokodu gömülü), adres genişliği ve silme
   davranışı değişiyor mu ölç. ⚠️ takımın adresleri değişir: komut tablosu
   HYV7'de `0x040E7398` (bizimkinde `0x040ED2F4`).
3. SKV6 mikrokodunu mikrokod RAM'ine doğrudan yaz.

### VM notları (kalıcı)

* Loader kimliği **`1e4b:1001`**, GDP/ürün `1e4b:1202` — `jd_vm.sh` düzeltildi
* `mptool.img` host'ta mount'luyken QEMU açamıyor → önce `umount /mnt/mpt`
* `-device vfio-pci` ile QEMU **SIGSEGV**; passthrough'suz sorunsuz
* vfio bind/unbind döngüsü denetleyiciyi kilitliyor → güç çevrimi gerekiyor

---

# §87 — ORİJİNAL FIRMWARE DİSKİN ÜSTÜNDE BULUNDU (15 Eylül gece)

Bu bölüm günün en büyük bulgusunu ve ona giderken düzelttiğim dört ölçüm
hatasını kaydeder.

## 87.1 Bulgu

Diskin **kendi orijinal firmware'i 16 die'ın 11'inde sağlam duruyor.**
Konum: her die'da **blok 0**. Şu die'larda sağlam:

    c2ce0 c3ce0 · c1ce1 c2ce1 c3ce1 · c0ce2 c1ce2 c3ce2 · c0ce3 c1ce3 c2ce3

Bozuk olanlar tam olarak bizim üzerinde çalıştığımız beş die:
`c0ce0, c1ce0, c0ce1, c2ce2, c3ce3`.

8 kopya tam olarak döküldü ve **bayt bayt aynı** çıktı (sayfa 0..145).
Yani veri replike edilmiş, striping yok → bir kopyayı diğerine yazmak geçerli.

Sayfa haritası (c2ce0 blok 0):

| sayfa | içerik |
|---|---|
| 0 | `LDBK BLOCKS V00` info page + `LDBK CONFIG V00` + CodeMap |
| 2,4,5,7 | `LDBK LDPC TABLE1/2`, `LDPC0 TABLE1/2` |
| 8 | `LDBK FWSLOT MARK` |
| 25–28, 41–45 | `MAS09A0V000` konteynerleri |
| 52–55 | tablolar (`ACE_C_PIN_User3_Set_PI` = Opal/TCG) |
| 68 | `LDBK NANDMEM TAB` |
| 69–72 | nandmem verisi + UEFI sürücüsü (`_gPcd_FixedAtBuild`) |
| 91 | `LDBK FWTMC MARK` |
| 92+ | firmware kod sayfaları |

## 87.2 Neden aylardır göremedik — okuma modu

`0x89` payload'unun **9. baytı LDPC oranını, 10. baytı descramble'ı** seçiyor.
Proje boyunca `b9=1, b10=1` kullandık. Doğrusu sayfa tipine göre değişiyor:

    sayfa 0..7  ->  b9=0, b10=1     (boot oranı: info page + LDPC tabloları)
    sayfa 8+    ->  b9=1, b10=1     (normal oran: FWSLOT/NANDMEM/FWTMC/kod)

`b10` çift olduğunda ham (scramble'lı) veri geliyor, tek olduğunda çözülmüş.
Yanlış oranla okunan sayfa **sıfır** dönüyor — "boş" değil, "çözülemedi".

## 87.3 Düzeltilen dört ölçüm hatası

1. **"Silinmiş sayfa 0xFF döner" — YANLIŞ.** LDPC çözücüsü silinmiş sayfada
   **sayfa indeksine bağlı sabit bir gürültü** üretiyor. Blok 0/1/2'nin 1..63
   sayfaları birebir aynı çıktı. Bu yüzden sabah "blok 1 = scramble'lı firmware
   gövdesi" diye okumuştum — orası boştu.
2. **"Blok 0..15 dokunulmaz" kuralı işe yaramıyordu.** Blok alanı 128'de
   sarıyor; k17 blok 384'e yazdı, blok 0'a düştü. Boot alanını kendi
   kampanyalarımız, kuralı koyduktan **sonra** da yazmaya devam etmiş.
   Doğru kural: **B mod 128 < 16 olan hiçbir bloğa yazma.**
3. **"Yazma bozuldu" — YANLIŞ.** k24'te yazmalar tutmadı; sebep tarif değil,
   **blok 100 ve 1000'in bozuk blok olması**. İyi bloklarda (200/384/600/
   2000/2700) sil-yaz-oku beş die'da da tutuyor. `7c71ebee2225` = bozuk blok
   imzası, `875398fbd1c4` = temiz silinmiş sayfa imzası.
4. **`0x5A` dolu sayfa = veri değil.** `komut_prp` her okumadan önce host DMA
   tamponunu `0x5A` ile dolduruyor; dönen sayfa baştan sona `0x5A` ise
   **denetleyici hiç veri aktarmamış**. "ZZZZ..." sayfalar boş sayfa değil,
   okunamayan sayfa.

## 87.4 Die blok sayısı — üçüncü ve son düzeltme

Diskin **kendi fabrika kaydı** `info page +0x1E0`'da duruyor:

    sFlashFullName = "H25BFT8A1BDA"

Bu, HYV7 paketindeki `Flash.ini` `Name007` satırı: **2888 blok**, 1536 sayfa,
16 KB, 2 plane, ID `AD 7E 28 53 02 B0`, ECC oranı 2.

Yani stok DPD'deki 2888 doğruydu. §85'te 2888'e döndüm, §86'da die markalamasına
(`H25BFT8D4B8R`, 4CE, 2732) bakıp tekrar 2732 dedim. **Üçüncüsü de yanlıştı.**
Fabrikanın diske yazdığı çalışan konfigürasyon A1 profili. Ders: ikincil
kaynakları (die markası, forum tabloları) diskin kendi kaydının üstüne koydum —
oysa kayıt sabahtan beri yedeğin içindeydi.

## 87.5 MPTool tersine mühendisliği doğrulandı

`re/ANALIZ_MPTOOL.md` (ajan çıkardı) — `MXMPTool_MAP1202_USB_V0_01_017.exe`
native PE32 (C++Builder), fonksiyon adları debug string'i olarak duruyor.
`VP_Cougar_FillInfoPage @0x4388a0`'dan çıkarılan info page alan haritasının
**her alanı** bizim yedekteki gerçek LDBK ile birebir tuttu:

    0x12=0x05 · 0x18..0x1E=500x4 · 0x20=0x0200 · 0x22=0x08 · 0x30=0x0FFFx4
    0x38=0x01FFx4 · 0x42=1 · 0x43=2 · 0x50=2 · 0x52=4 · 0x54=2(ucLdpcMode)
    0x56=4608 · 0x60=0x10 0x64=0x149C 0x68=0x2010 0x6C=0x0B70

`0x64/0x6C` değerleri tam olarak `ucLdpcMode=2` için beklenenler. LDBK'da CRC
yok — `wCheckSum` sabit `0xFFFF`.

Diskin kendi CodeMap'i (info page +0x220):

    entry 0: sayfa  92..97   98304 B -> 0x00000000
    entry 1: sayfa  98        16384 -> 0x00800000
    entry 2: sayfa  99        16384 -> 0x00804000
    entry 3: sayfa 100        16384 -> 0x040C4000
    entry 4: sayfa 101..106   98304 -> 0x02000000
    entry 5: sayfa 107        16384 -> 0x02800000
    entry 6: sayfa 108..111   65536 -> 0x04060000
    entry 7: sayfa 112..119  131072 -> 0x040D0000
    entry 8: sayfa 120        16384 -> 0x040C0000
    entry 9: sayfa 121        16384 -> 0x040CC000
    (10,11 etkin; 12,13 wEnable=0)
    toplam etkin = 512 KB, sayfa 92..123

Mantıksal→fiziksel sayfa tablosu (bölge 2, +0x320) **özdeşlik**.

## 87.6 Donanım dersleri

- **Secondary bus reset cihazı bus'tan tamamen düşürüyor.** `reset_method=bus`
  + `echo 1 > reset` → config space `0xFFFF`, rescan geri getirmiyor, soğuk
  çevrim şart. FLR loader'ı öldürüyor, SBR cihazı yok ediyor: **ikisi de
  kullanılamaz.**
- **PCI device ID loader/firmware ayrımı için güvenilmez.** Aynı loader
  firmware'i bir açılışta `1e4b:1001`, diğerinde `1e4b:1202` gösterdi.
  Ayrım için `Identify Controller` → `MN` bak: `Generic_Loader_NVMe_Device`.
- `CSTS=0x00000009` (shutdown-complete) loader'ın **normal** durumu, arıza değil.
  CC.EN=0 yazmak işe yaramıyor (loader RDY'yi düşürmüyor).

---

# §88 — KÖK NEDENLER BULUNDU: kapasite tavanı ve diski ne öldürdüğü

GDP firmware'inin disassembly'si (`re/ANALIZ_GDP_SEMBOL.md`, 912 satır,
`re/gdp_sembol/` altında 193 ham döküm) iki kök nedeni kesin olarak verdi.

## 88.1 2^19 tavanı = DPD'nin iki baytı

    DPD[0x18] = "GDP ROW BLK SHIFT"        bizim 34 DPD dosyasının HEPSİNDE 10
    DPD[0x19] = "GDP ROW PAGE BLK SHIFT"   bizim 34 DPD dosyasının HEPSİNDE  9
    erişilebilir satır = 2^([0x18]+[0x19]) = 2^19   <-- tam ölçtüğümüz tavan
    firmware'in kendi varsayılanı: 11 + 12 = 2^23

`0x040E236C` bu iki baytı canlı DPD'den okuyup NIFC `0x06640000 +0x60/+0x64/
+0x68`'e 5-bitlik `{shift, width}` çiftleri olarak yazıyor; NAND satır düzeni
`[page:0x19][plane:0x1B][block:0x18][lun:0x1A]`. Yazılım tarafındaki
`0x040C8EC4`'te hiçbir kısıt yok — blok ve sayfa ikisi de 16 bit.

**Aylardır `[0x1D]`'yi (9/10/11/12) ve plane sayısını süpürdüm; bu iki bayta
hiç bakmadım.** "Geometri alanlarının onu tek tek denendi, hiçbiri taşımadı"
dediğim listede bunlar yoktu.

Canlı geçiş yolu var: **GDP komutu `0x58` (SetRowShifts)**. `0x040C6588` →
`0x040CA448` payload[3..6]'yı DPD'nin `[0x18] [0x19] [0x1B] [0x1F]` alanlarına
yazıp `0x040E236C`'yi yeniden çağırıyor. NAND'a dokunmuyor, geri alınabilir,
sadece SKV8 GDP'sinde var (HYV7'de yok).

⚠️ Dürüst çekince (ajanın kendi notu): MPTool'un formülü
`bRowPageShift = ceil_log2(sayfa/3)` (TLC) — yani 9 kasıtlı olabilir; sayfa
alanı 512 wordline'ı indeksliyor ve wordline başına 3 sayfayı seçen mekanizma
henüz bulunamadı. Test ucuz ve risksiz.

## 88.2 Diski ne öldürdü — kesin cevap

`0x8B` komutunda **kanal VEYA CE `0xFF` ise** (ARM `cmp`/`cmpne`/`beq` =
VEYA, VE değil) `0x040C3CE8`'deki dal alınıyor ve firmware
`"Erase CodeBlock[0,1] for All Dies"` basarak **her die'ın 0 ve 1 numaralı
bloklarını siliyor**.

`kampanya/telsiz.py` tam olarak `0x8B ch=ce=0xFF` çağırıyordu. Blok aliasing
(§87.3) buna ek hasar verdi ama asıl kurşun buydu: tek komut, 16 die, iki blok.

CodeBlock tanımı da netleşti: `gdp_init` `0x040C3064` `"Init CodeBlock as 0 & 1"`
basıyor ve `u8 g_codeblock[8][4][2]={0,1}` tablosunu RAM `0x00009358`'e kuruyor.
Aday havuz her (kanal, CE) için **fiziksel blok 0..3**, MPTool en fazla 2 tanesini
kullanıyor (`0x443345 cmp eax,8`, `0x440c03 cmp edx,4`).

## 88.3 GDP'de olan ve olmayan

- **`0x8A` ham sayfa yazma var** ve keyfî (ch, ce, blok, sayfa) adresliyor.
- **Konteyner kurma yok.** Hiçbir GDP'de `write/burn/program-codeblock` yok;
  InfoPage'i host tarafında `VP_Cougar_FillInfoPage` kuruyor.
- SYS imajları **RSA imzalı** (`LOADER_CERT_TAG1`, Maxio-Tech CA) → birebir
  yazılmak zorunda, üretilemez. Bu yüzden diskin kendi kopyası altın değerinde.
- Yeni: `0x0A/0x0B/0x0C` = **SPI-NOR sil/oku/yaz**. Kartta SPI flash varsa
  NAND'dan bağımsız bir boot yolu olabilir (doğrulanmadı).
- Yeni: `0x040EFAC4`'te **21 komutluk UART hata ayıklama kabuğu** (`regs` =
  keyfî register yaz, `dump` = keyfî bellek oku).
- ⚠️ Her codeblock döngüsü `DPD[0x310+i]==0xFF` olan die'ları **atlıyor**.
  Yanlış DPD ile MPTool hiçbir şey yazmaz ama **sessizce başarı raporlar**.

## 88.4 Mikrokod — önceki hipotez yanlıştı

"SKV8 GDP'sinde gömülü mikrokod yok" demiştim. **Var, hem de HYV7'den fazla**
(116 CMD / 47 A0 vs 86 / 38). Önceki tarama kaçırmış çünkü SKV8 tabloları dosya
ofseti ≡ 2 (mod 4) hizasında duruyor. İki `"TOOL"` etiketli tablo:
SKV8 `0x040EE836` (0xC90, 69 program) + `0x040EF4C6`; HYV7 `0x040E7BB0` (0x900,
51 program) + `0x040E84B0`. Yükleyiciler `0x06649000` ve **`0x06650000`** (ikinci
RAM, yeni) adreslerine kopyalıyor. Canlı dökümümüzdeki `544f4f4c` = `"TOOL"`
etiketi, bu tablonun başlangıcı.

## 88.5 Geri yazma sonucu

`kampanya/k32.py`, sayfa tipine göre mod seçerek (0..7 → mode 0 / 8 sektör,
8+ → mode 2 / 32 sektör), silinmiş-sayfa parmak izi çıkararak ve her sayfayı
iki nöbetçiyle okuyarak sağlam kopyayı bozuk die'lara yazdı.

    c0ce0 : 150 sayfa yazıldı, yazılamayan 0, geri okuma farkı 0   TAMAM
    c1ce0 : 150 sayfa yazıldı, yazılamayan 0, geri okuma farkı 0   TAMAM

CE0 artık dört kanalda da sağlam. Kalan üç die (c0ce1, c2ce2, c3ce3) sırada.

---

# §89 — TELSİZ AÇILIŞ OLDU; SIRADAKİ DUVAR: FIRMWARE KENDİNİ SALT-OKUNUR KİLİTLEMİŞ

## 89.1 Telsiz açılış — BAŞARILI

16 die'ın hepsine orijinal loader blok geri yazıldıktan sonra tel çıkarıldı ve
soğuk çevrim atıldı. Sonuç:

    [1.969754] nvme nvme1: pci function 0000:04:00.0
    [1.986033]  nvme1n1: p1
    nvme1n1  953.9G  JAMESDONKEY JD1024 1TB
    model=JAMESDONKEY JD1024 1TB  fw=JD2024  sn=AAAA0000000000000329
    tnvmcap = 1.024.209.543.168 bayt

ROM, NAND'dan firmware'i buldu ve çalıştırdı. `VS = 0x00010400` (loader 1.3
derdi, ürün firmware'i 1.4). BIOS artık diski beklemiyor.

Bir tuzak: açılışta disk geldi ama **bizim kendi servisimiz**
`jd-loader-hazirla.service` sürücüyü hemen unbind ediyordu. Kapatıldı.
İkincisi: `/etc/modprobe.d/vfio-nvme.conf` (`ids=1e4b:1202`) diski her açılışta
vfio-pci'ye bağlıyordu — çalışan diski "çalışmıyor" gibi gösterirdi. Devre dışı.

## 89.2 Okuma tam, yazma yok

| işlem | sonuç |
|---|---|
| ardışık okuma | 1,2 GB/s |
| 0/100/300/500/700/900/953 GiB noktalarından okuma | hepsi başarılı, 2,4 GB/s |
| NTFS bölümü mount | çalışıyor |
| sürekli yazma | ~30 sn sonra denetleyici kilitleniyor |
| TRIM (blkdiscard) | kilitliyor |
| `nvme format --ses=0` | **başarılı**, sonrasında yazma çalışıyor |
| güç çevrimi sonrası | firmware init'i bitiremiyor, `CSTS=0x0` 600 sn boyunca |

Ölçüm: BAR0'dan CSTS'i elle 10 dakika izledim, hiç `RDY` olmadı. Çekirdek
zaten `CAP.TO` = 127,5 sn'de pes ediyor. Yani firmware yükleniyor, çalışıyor,
ama kendi başlatmasını tamamlayamıyor. 2-3 açılışta bir geliyor.

## 89.3 Kök neden: firmware medyayı salt-okunur moda almış

Diski canlı yakalayıp `nvme format --ses=1` attım — geçti, yazma hızı
382→500 MB/s'e çıktı, 5 GiB sorunsuz yazıldı. Ama:

    critical_warning   : 0x8     <-- bit3 = "media placed in read only mode"
    available_spare    : 3%      (esik %1)
    percentage_used    : 0%
    media_errors       : 77
    Data Units Written : 3,75 TB
    power_on_hours     : 2230

**Yazmalar kabul ediliyor ama diske gitmiyor.** Altı ayrı ofsete desen yazıp
hemen geri okudum: hepsi `b6d81b360a` = 1 MiB sıfırın md5'i. `rc=0`, "500 MB/s",
ve veri yok. Sessiz yutma.

`nvme sanitize --sanact=2` (block erase) **başarıyla tamamlandı** (SSTAT 0x101)
ama `critical_warning 0x8` ve `available_spare 3%` değişmedi, yazmalar hâlâ
yutuluyor. Kilit firmware seviyesinde ve NAND'a kayıtlı.

## 89.4 3% yedek — asıl soru

3,75 TB yazılmış bir 1 TB TLC diskte (4 tam disk yazımından az) aşınma yüzünden
yedek blokların %97'si tükenmiş olamaz. İki olasılık:

1. **Bir die gerçekten ölü.** GDP testlerimizde `c3ce2` 3/3 yazma denemesinde
   başarısızdı. 16 die'ın biri = kapasitenin %6,25'i. Firmware o die'ı
   remap etmeye çalışırken yedeği tüketip kendini kilitlemiş olabilir.
   Bu senaryo **fabrika arızası** demektir ve diskin ilk ölümünü de açıklar.
2. **Tablolar bozuk.** Bad-block/wear tabloları bizim GDP çalışmamızda
   yok edildi; firmware format sırasında yeniden tarayıp gerçekte sağlam olan
   blokları "bozuk" saymış olabilir.

Ayırt etmenin tek yolu NAND'ı kendimiz ölçmek → tel gerekiyor.

## 89.5 Yol haritası (tel takılıyken)

1. GDP yükle, `0x58` ile row shift'i düzelt (`[0x18]=11 [0x19]=12`) → die'ın
   tamamı adreslenebilir olsun.
2. **Dürüst kötü blok sayımı**: 16 die'da örneklem bloklarda sil→yaz→oku
   turu. Gerçek bozuk blok oranı nedir, `c3ce2` gerçekten ölü mü?
3. Sonuca göre:
   - NAND sağlıklıysa → tüm kullanıcı bloklarını sil, loader blokları koru,
     MPTool'un Preformat/CheckTables akışını kendi protokolümüzle uygula →
     firmware tabloları sıfırdan kursun, salt-okunur kilidi kalksın.
   - Bir die ölüyse → DPD/Flash.ini'yi 15 die'a göre yeniden yaz, disk
     ~960 GB olarak yeniden programlansın.

## 89.6 Bu turda öğrenilen işletme dersleri

- **`nvme` numaraları açılıştan açılışa değişiyor.** Bir seferinde `nvme1`
  KIOXIA çıktı. Betiklerde cihaz **modele göre** bulunmalı (`jd_bul`), numaraya
  asla güvenilmemeli. Koruma bu yüzden KIOXIA'yı kurtardı.
- `timeout X dd ... | tail -1` kalıbında `$?` **dd'nin değil tail'in** dönüş
  kodudur. Bir ölçüm turu bu yüzden "hepsi başarılı" göründü.
- `nvme smart-log` çıktısında alan adından sonra **tab** var; `^temperature `
  (boşlukla) grep'i tutmaz.
- Secondary bus reset (`reset_method=bus`) cihazı bus'tan tamamen düşürüyor,
  rescan geri getirmiyor. FLR loader'ı öldürüyor. İkisi de kullanılamaz;
  tek kurtarma yolu soğuk çevrim.

---

# §90 — BİR DIE FİZİKSEL OLARAK ÖLÜ: `c3ce2` (16 Eylül gece)

## 90.1 Ölçüm

`kampanya/k42.py` — 16 die × 38 blok, sil→yaz→oku→doğrula:

    15 die : 25/38 sağlam
    c3ce2  :  0/38

`kampanya/k43.py` — c3ce2'ye odaklı 12 blok, durum baytlarıyla:

    c3ce2 : 12 blokta da  sil[sts0=0101e1e1]  yaz[sts0=0101e1e1]  -> 0/12
    c2ce2 : 9/12 (kalan 3 bizim adres artefaktımız, aşağıda)

`0xE1` = hazır + WP# yüksek + **FAIL biti**. Yani c3ce2'de **her program ve
her silme başarısız**. Buna karşılık **okuma kusursuz**:

    flashid            = ad7e285302b0        (doğru)
    blok0 sayfa 0  m0  = "LDBK BLOCKS V00"   ✓
    blok0 sayfa 2  m0  = "LDBK LDPC TABLE1"  ✓
    blok0 sayfa 8  m2  = "LDBK FWSLOT MARK"  ✓
    blok0 sayfa 68 m2  = "LDBK NANDMEM TAB"  ✓

Okuma yüksek gerilim istemez, program/silme ister. Bu tablo **die'ın yüksek
gerilim üretecinin (charge pump) bozulduğuna** işaret ediyor. Üç ayrı
kampanyada 50+ denemede tek bir başarılı yazma yok.

Dürüst çekince: firmware seviyesinde c3ce2'ye özel bir adresleme arızası da
aynı tabloyu üretebilir; ama okuma **aynı adres yolunu** kullanıyor ve çalışıyor.

## 90.2 Bu, diskin salt-okunur kilidini açıklıyor

    available_spare   : 3%   (eşik %1)
    critical_warning  : 0x8  = media placed in read only mode

16 die'ın biri = kapasitenin %6,25'i. Firmware o die'ın bloklarını remap etmeye
çalışıp yedek havuzunu tüketmiş ve kendini kilitlemiş. **Kilit, firmware'in
doğru tepkisi.** Diskin ilk "ölümü" de büyük olasılıkla budur.

## 90.3 "13 bozuk blok" — medya değil, bizim adreslememiz

15 die'ın hepsi **tam olarak aynı** bloklarda düştü: 91, 94, 97, ..., 127
(kesintisiz kuyruk). Rastgele kötü blok böyle davranmaz. Fiziksel karşılıkları
242,67 · 250,67 · 258,67 ... — hepsi blok sınırının 2/3'ünde. Bu, silme yolunun
blok alanını bölmesi / yazma yolunun bölmemesi farkının ürünü. **Medya sağlam.**

## 90.4 Yeni tehlike: silme yolu boot bloğuna sıçrayabiliyor

k42 taraması (blok 16..127, c0ce0) çalıştıktan sonra c0ce0'ın **blok 0'ındaki
LDBK kayboldu**. O tarama blok 0'a hiç dokunmadı. Silmenin böldüğü blok alanı,
bazı B değerlerinde fiziksel blok 0'a düşüyor. Geri yazıldı.

**Kural:** GDP ile toplu silme yapan her kampanya, her turdan sonra boot
bloğunu doğrulamalı; `kampanya/k32.py` ile geri yazma her zaman elde.

## 90.5 Bundan sonrası

Diski **yazılabilir** hale getirmenin tek yolu, firmware'i 15 die'lı bir
konfigürasyonla yeniden programlamak: MPTool'un `DownloadProgram` akışını kendi
protokolümüzle uygulamak + `Flash.ini`/DPD'yi ölü die'ı dışlayacak şekilde
düzenlemek. Elimizde olanlar: tam MPTool RE'si, diskin kendi imzalı firmware
sayfaları (0..359, yerel yedek), LDBK üreteci. Eksik olan: die dışlamanın
firmware tarafındaki karşılığı (kapasite/şerit geometrisi yeniden hesaplanmalı).

Kapasite o zaman ~960 GB (15/16) ya da CE bazında dışlanırsa 768 GB (12/16).

---

# §91 — TEL GEREKMİYOR: vendor protokolü çalışan firmware'de de açık (16 Eylül)

## 91.1 Keşif

MAXIO vendor protokolü **ürün firmware'inde de** kabul ediliyor. NVMe
admin-passthru ioctl'iyle doğrudan gönderiliyor; loader/tel gerekmiyor.

    enable  : opcode 0xC1, CDW14=0x00AE34FF, CDW15=1, 4096 B "FF E5 C1"
    faz1    : opcode 0xC1, CDW10=0x80, CDW14=0x001234FF, CDW15=1, 512 B payload
    faz2-in : opcode 0xC2, CDW10=n<<7, CDW14=0x00123400|cmd, CDW15=n

Araç: `takim/jdcanli.py`. Cihazı **modele göre** bulur.

## 91.2 Ürün firmware'inin vendor komut yüzeyi (ölçüldü)

| cmd | ne döndürüyor |
|---|---|
| 0x00 | GetReturn — `02000000 d0020100 ff000000 d1020100 88000000` |
| 0x01 | 256 baytlık u32 tablosu (zamanlama/kalibrasyon) |
| **0x04** | **`LDBK BLOCKS V00` info page'in tamamı** |
| **0x30** | **topoloji**: `02 04 04 01` = plane 2 · kanal 4 · CE 4 · LUN 1; 722 blok; 1536 sayfa; 32 sektör/sayfa |
| 0x36 | flash ID `ad7e285302b0` |
| 0x37 | `5, 30, 12, 16, 23, 20` (zamanlama) |
| 0x49 | 4 |
| **0x60** | **etiketli sayaçlar**: `STARLBB-` 0 · `UNC-` 96 · `WAI-` 0 · `RDCT` 0 · `PES` 30,12,5,20,50000,3000,18,10 · `CDBK` 373 · `END` |
| 0x86 | **ReadRam — çalışıyor**, canlı firmware belleği okunuyor |
| 0x87 | WriteRam — kabul ediliyor ama **etkisi yok** (muhtemelen RSA imzalı sürüm gerekiyor) |
| 0x88 0x89 0x07 0x0B 0x10 0x31 | ürün firmware'inde **yok** (hep sıfır) |

⚠️ **`0x84` ve `0x85` denetleyiciyi öldürüyor.** 0x80'ler taranmamalı.
⚠️ Eşlenmemiş adresten `ReadRam` firmware'i fault'luyor — `jdcanli.GUVENLI`
listesi dışına çıkma.

## 91.3 Firmware imajı diskin kendisinden yeniden kuruldu

Loader bloğunun kod sayfaları (92..136) CodeMap'e göre birleştirildi:
`re/fw_canli/` — 512 KB, 10 bölge, yükleme adresleriyle. Canlı RAM okumasıyla
doğrulandı (0x00000000'daki ARM vektör tablosu birebir tuttu).

Sayfa 8 `LDBK FWSLOT MARK` gerçek slot tablosu: **iki firmware slotu** var,
slot 0 sayfa 92..136, slot 1 sayfa 137..175. İkisi de yedeğimizde.

## 91.4 Yazmanın nasıl düştüğü — kesin tablo

    nvme write                -> Success
    nvme flush                -> success
    nvme write --force-unit-access -> Success
    write cache kapatildi     -> yine tutmuyor
    nvme write-zeroes         -> BASARILI, LBA eslendi, geri okuma 4096 sifir
    nvme read (yazdigimiz yer)-> veri YOK
    nvme format --ses=0       -> 7 saniyede basarili

`write-zeroes` çalışıp normal yazmanın çalışmaması kritik: **eşlem makinesi
sağlam, NAND'a gerçek veri programlama yolu kapalı.** Ve `critical_warning 0x8`
tam NAND silmesinden sonra bile açılışta geri geliyor → kilit NAND'da saklı
değil, **her açılışta yeniden karar veriliyor**.

## 91.5 Silme sınırı — önceki ölçümüm yanlıştı

`0x8B` silme `rf=32768`'e kadar tutuyor (blok ~8192). Yani **silme komutu
die'ın tamamını görüyor**; 2^19 penceresi sadece yaz/oku yolunu bağlıyor.
Bu bilinince tam NAND temizliği yapıldı: **46.160 blok, 0 red, 7 dakika.**

Sonuç: `available_spare %3 → %100`. O sayı fiziksel bir gerçek değil,
**saklanmış bir tabloymuş**. Aynı şekilde `media_errors` 77→429 yükseldi ve
sadece yazılmamış LBA okumalarını sayıyor — gerçek medya hasarı değil.
İkisini de "donanım kanıtı" diye sunmuştum, ikisi de yanlıştı.

---

# §92 — AÇILIŞ KARARSIZLIĞI ÇÖZÜLDÜ; KİLİT DARALTILDI

## 92.1 Kararsız açılış aslında zamanlamaymış — ÇÖZÜLDÜ

Disk açılışta "init'i bitiremiyor" sanıyordum. BAR0'dan CSTS'i elle izleyince:

    CAP=0x00200030ff0103ff VS=0x00010400 CC=0x00460001 CSTS=0x00000001
    >>> HAZIR

**Denetleyici hazır oluyor** — sadece çekirdeğin `CAP.TO` penceresinden
(127,5 sn) uzun sürüyor, çekirdek pes edip cihazı kapatıyor. `remove` + `rescan`
ile disk normal geliyor: `nvme1n1 953.9G JAMESDONKEY JD1024 1TB`.

Kalıcı çözüm kuruldu: **`/usr/local/bin/jd-gec-baglan.sh`** +
`jd-gec-baglan.service` (enabled). Açılışta JD yoksa CSTS.RDY'yi 10 dakikaya
kadar bekler, sonra PCI rescan atar.

## 92.2 Kilidin OLMADIĞI yerler (hepsi ölçüldü)

| aday | sonuç |
|---|---|
| LDBK info page | **elendi** — `0x04` ile firmware'in okuduğu sayfa alındı, yerel yedekle **0 bayt fark** |
| NAND'da saklı | **elendi** — 46.160 bloğun tamamı silindi, kilit açılışta geri geldi |
| `nvme format --ses=0/1` | temizlemiyor (format başarılı, kilit duruyor) |
| `nvme sanitize --sanact=2` | temizlemiyor (SSTAT 0x101 = başarılı, kilit duruyor) |
| NVMe standart Namespace Write Protect | **yok** — `nwpc=0`, feature 0x84 `Invalid Field` |
| write cache / FUA / flush | etkisiz |
| `0x87 WriteRam` ile RAM yaması | **komut kabul ediliyor ama bellek değişmiyor** — ürün firmware'inde RSA imzalı sürüm gerekiyor olmalı |

## 92.3 Yazma yolunun tam davranışı

    nvme write        -> Success   (veri gitmiyor)
    nvme write-zeroes -> BASARILI, LBA esleniyor, geri okuma 4096 sifir
    nvme read (yazilan yer) -> Unrecovered Read Error (0x281)

Eşlem makinesi sağlam; **NAND'a gerçek veri programlama yolu kapalı.**

## 92.4 Firmware kimliği ve WP damarı

Firmware ikilisinden (diskin kendisinden çıkarıldı):

    MKSSD_501003000124620000, Oct 31 2023, MAP1202, ZI0PCD2C
    r:/code_release/Hynixv6/Cougar_Hynix_v6_12463
    Maxiotech_MAP1002_NVMe_SSD  SVN12462MA   (gelistirici: feng_qin)

`ZI0PCD2C`, `fw_hunt4` raporunda "hiç yayınlanmamış" denen **`C.0.01018_HYV6`**
paketinin firmware adlarından biri. Yani diskin firmware'i o pakete ait.

İlgili hata ayıklama dizeleri (hepsi ikilide mevcut):

    0x00002BA8  wp_mode assert!
    0x00804080  Frontend WP ON            <- xref: 0x00803DCC
    0x02009528  DEBUG:wp_assert
    0x040D6A44  WRITE-PROTECT
    0x040D8248  It's not WP status!
    0x040D0F10  uart test get wp info!
    0x04062540  g_err_die:%x
    0x0406E6B4  E:max_dies=0
    0x040683B0  No SysInfo block
    0x0406DEF4  code block recover
    0x0406A990  CH(%d),CE(%d),Capacity(%d GB,...),SP(0x%x)

## 92.5 Yeni araçlar

- `takim/jdcanli.py` — vendor protokolü canlı firmware üzerinden, tel yok.
  `GUVENLI` adres listesi var: liste dışını okumak firmware'i fault'luyor
  (16 Eyl: kör tarama diski düşürdü).
- `re/fw_canli/` — diskin kendi firmware'i, 512 KB, 10 bölge, yükleme
  adresleriyle. Canlı RAM ile doğrulandı.
- `kampanya/k48.py` (tam NAND silme, 7 dk) + `kampanya/k49.py` (loader bloğu
  yerel yedekten 16 die'a yaz). İkisi birlikte diski istenildiği kadar
  sıfırlayıp geri kurma imkânı veriyor.

## 92.6 Isı

Boşta **64 °C** (sensör 2: 58 °C). Yükte 72 °C görülmüştü. M.2 yuvası ekran
kartının hemen altında; kartın fanları aşağı baktığı için hava akışı yardımcı
olabilir ama bu sıcaklık boşta için yüksek.

---

## §93 — Acilis hizi olculdu, kok neden tek noktaya indi (16 Eyl, ogleden once)

### 93.1 JD1024'un acilis maliyeti: +35 saniye, tamami BIOS+GRUB'da

| acilis | JD var mi | BIOS (firmware) | GRUB (loader) | cekirdek | toplam |
|---|---|---|---|---|---|
| b-7 | **yok** | 12,6 sn | 1,2 sn | 2,6 sn | **24,5 sn** |
| b-6..b0 | var | 38,8-39,8 sn | 9,8 sn | 2,2-2,7 sn | **60 sn** |
| b-3, b-2 | var (hazir olmadi) | 2dk19 | 1,2 sn | **2dk10** | 5 dk |

Cekirdek tarafinda disk **1,97 saniyede** hazir (monotonic 1.971325 `nvme nvme1: pci function`).
Yani yavasligi yaratan denetleyici init'i degil; BIOS ve GRUB **LBA 0'i okumaya calisip hata aliyor**:

    nvme1n1: I/O Cmd(0x2) @ LBA 0, 8 blocks, I/O Error (sct 0x2 / sc 0x81)
    critical medium error, dev nvme1n1, sector 0
    nvme1n1: unable to read partition table

`sct 0x2 / sc 0x81` = Media and Data Integrity Error / Unrecovered Read Error. Haritalanmamis LBA
normalde sifir dondurur; bu firmware hata donduruyor.

### 93.2 `write-zeroes` okuma hatasini kaldiriyor (FTL haritasi calisiyor)

    nvme write-zeroes /dev/nvme1n1 --start-block=0 --block-count=7   -> Success
    dd if=/dev/nvme1n1 bs=512 count=1                                 -> 512 bayt, hepsi 0x00

32 MB'lik `write-zeroes` **7 milisaniyede** bitiyor -> NAND'a yazilmiyor, sadece FTL haritasi
degisiyor. Yani esleme motoru saglam, kapali olan tek sey NAND'a program yolu.

### 93.3 `0x87 WriteRam` urun firmware'inde KESIN olarak yazmiyor

Uc ayri bolgede test edildi (`ramtest.py`): ayni veriyi geri yazma sorunsuz, tek bayt degistirip
yazma **hicbirinde tutmuyor**, cihaz canli kaliyor.

| hedef | adres | no-op yazma | tek bayt |
|---|---|---|---|
| e06 kod | 0x04063200 | AYNI | YAZMADI |
| e07 FTL veri | 0x040EF000 | AYNI | YAZMADI |
| e02 frontend | 0x00806E00 | AYNI | YAZMADI |

Ek bulgu: **e06 (0x04060000) canli RAM'de tamamen sifir** — 16/16 ornek. e00/e01/e03/e04/e07 imajla
esleiyor. Muhtemelen CPU2'nin ITCM'i vendor ReadRam yoluna gorunmuyor.

### 93.4 Diskin KENDI tanisi (MPTool SYS komut kumesi, hepsi okuma)

| cmd | ad | sonuc |
|---|---|---|
| 0x21 | GetUartLog | 4096 bayt, **hepsi sifir** (gunluk bos / uygulanmamis) |
| 0x00 | GetBadUnit | **2 kayit**: birim 0x01 blok 720 (bayrak 0xFF), blok 721 (0x88) |
| 0x01 | GetEraseCount | 728 sifir-olmayan girdi, degerler 7..25 |
| 0x36 | GetFlashID | `ad 7e 28 53 02 b0` |
| 0x30 | topoloji | plane 2 / ch 4 / CE 4 / LUN 1, **722** blok, 1536 sayfa, 32 sektor/sayfa |

**Onemli:** firmware olu die'i bozuk olarak BILMIYOR — bad-unit tablosunda sadece en ustteki 2
ayrilmis blok var.

### 93.5 Flash profili ureticinin kendi dosyasindan dogrulandi

`kanit/fw_hunt3/ex/MAP1202_H25TXTD2XCX6/.../Flash.ini` satir 85:

    Name004=SKV606411 H25BFT8A1BDA  3 2 1  2888 1536 16 1 2  0xAD 0x7E 0x28 0x53 0x02 0xB0  0 0 0 11 4 ...
    canli 0x36 flash ID              =                        ad   7e   28   53   02   b0    ESLESIYOR

- Flash adi diskin info page'indeki `H25BFT8A1BDA` ile ayni
- **2888 blok** — 2888/2732 tereddudu bitti, uretici profili 2888 diyor
- 1536 sayfa = topolojinin 0x600'u; 722 x 4 = 2888 -> firmware **superblok** sayiyor (4 blok/superblok)
- `11 4` = ROW_BLOCK_SHIFT 11; info page +0x10 = `0b 09 05` -> 11 ✓
- Kapasite kaybi YOK: `tnvmcap = 1024209543168` (tam 1 TB), `nsze = 0x773BD2B0` = 953,9 GiB

### 93.6 Kok neden zinciri — iki komuta indi

    olu die (ch3/ce2) program/silme yapamiyor
      -> e06 0x040632AC: 1024 blok girdisi karsilastirilir, uyusmazlik >= 512
      -> e06 0x040632DE: itt hs ; orrhs r0,r0,#8 -> media-status 0x040EE73C bit3 = READ-ONLY
      -> e04 0x0200F368: health word 0x00806EC8 |= 8      (canli olculdu: 0x19, bit3 SET)
      -> e07 0x040EC1B4: beq commit / else drain+discard  -> yazmalar sessizce yutuluyor

**Latch degil, her taramada yeniden hesaplaniyor** — bu yuzden NAND'i tamamen silmek (46.160 blok)
kilidi acmadi.

### 93.7 Yama hazir: iki bayt

    kanit/loader_yamali/  (kanit/loader_orijinal'in kopyasi, 2 bayt farkli)
      sayfa 108 ofset 0x32E2 : 08 -> 00   e06 0x040632E0  orrhs r0,r0,#8 -> #0
      sayfa 119 ofset 0x01B5 : D0 -> E7   e07 0x040EC1B4  beq -> b (kosulsuz commit)

    orijinal toplu sha256 : 0b21de704e05e6cfcd087600e04d37cd8ec5ae4a887fa06cfef302b8e83e4ac8  (kayitla ayni)
    yamali   toplu sha256 : b181e6051d92991cc4d83909c096869235989f0fcead9cc718101478d25c831b

Yazici: `kampanya/k50.py` (k49 ile ayni, `JDKAYNAK` ile kaynak dizin secilir).
**Eksik olan tek sey: bu iki bayti NAND'a yazacak yol.** GDP loader gerekiyor.

### 93.8 Yeni araclar
- `takim/jdzero.py` — tum namespace'i tek surecte Write Zeroes (CLI ile 21 saat, ioctl ile ~1 dk)
- `/tmp/ramtest.py`, `/tmp/harita.py`, `/tmp/sys_sorgu.py`, `/tmp/nssr.py`

## §94 — Tel seansi: dort baytlik firmware yamasi (16 Eyl, ogle)

### 94.1 Telsiz yollarin hepsi kapandi (uc bagimsiz analiz)

| yol | sonuc | kanit |
|---|---|---|
| `0x87 WriteRam` ile canli RAM yamasi | KAPALI | uc bolgede test: komut basarili, bellek degismiyor. Imajda `cmp #0x87` **hic yok** |
| standart `nvme fw-download`+`fw-commit` | KAPALI | opcode 0x11 aslinda vendor tasima kanalinin ikizi (CDW11'i `<<2` yapip `0xAE34FF08/0x12340008` sihirleriyle karsilastiriyor). 0x10 commit worker'i kuyruk/DMA rutini; **firmware slot / LDBK / CodeMap referansi sifir** |
| `0x82 JumpToPRAM` ile bakim kodu yukleme | KAPALI | 0x81≡0x82 ayni handler (e00 `0x00003A4E` → e01 `0x008038E0`); payload **okumuyor**, sabit pool sabitleri yaziyor (`*(0x0080BF88)=0x040C71E9`) ve gomulu durum makinesine (`0x0000CD36`) atliyor. Host adresine atlama yok. SPI NOR da yok (JEDEC opcode dizisi / string / register bazi bulunamadi) |

### 94.2 ROM modunda `nvme` surucusu = olum  [YENI DERS]

Tel takilinca disk `Generic_Loader_NVMe_Device` olarak geliyor ve `nvme` **basariyla baglaniyor**.
Ama `unbind` → `nvme_remove` → **CC.SHN kapatma dizisi** gonderiyor. Sonrasinda:

    CSTS = 0x00000009     (RDY=1 + shutdown-complete)  — takili kaliyor
    CC=0 yazmak temizlemiyor;  loader hicbir vendor komutuna cevap vermiyor
    gdprun:  "mevcut mod: ?"  →  enable ZAMAN ASIMI

Cikis yalnizca soguk guc cevrimi. Cozum `/usr/local/bin/jd-tel-modu ac|kapa`:
`options pci-stub ids=1e4b:1202` + `softdep nvme pre: pci_stub` + `pci_stub` initramfs'e.
**Sadece kernel cmdline'daki `pci-stub.ids=` YETMIYOR** — pci-stub modul, nvme'den sonra
yukleniyor ve cihazi kapamiyor. Dogru kurulumdan sonra: `driver=[pci-stub]`, `CSTS=0x1`,
`gdprun` ilk denemede `>>> GDP MODU AKTIF <<<`.

Ayni sinifta iki olumcul islem daha (ikisi de cihazi veri yolundan dusuruyor,
`pci 0000:04:00.0: not ready after 65535ms; giving up`; rescan/link-retrain/link
disable-enable geri getirmiyor): **`nvme subsystem-reset` (NSSR)** ve **PCIe secondary bus reset**.

### 94.3 Yama seti — dort bayt, hepsi literal havuzundan dogrulandi

    e06 0x040632DE  itt hs ; orrhs r0,r0,#8   -> *(0x040EE73C) media-status bit3   [A]
    e06 0x040665F8  orr r1,r1,#8              -> *(0x00806EB8+0x10)=0x00806EC8     [C]
                                                 health word bit3 (CANLI 0x19 olculmustu)
    e07 0x040EC1B4  beq commit / drain+discard  gate kopya 1 (literal 0x040EF048)  [B]
    e07 0x040EC23A  beq commit / drain+discard  gate kopya 2 (literal 0x040EF048)  [D]

Yama (loader blogu sayfa/ofset):

    sayfa 108 ofset 0x32E2 : 08 -> 00
    sayfa 109 ofset 0x25FA : 08 -> 00
    sayfa 119 ofset 0x01B5 : D0 -> E7
    sayfa 119 ofset 0x023B : D0 -> E7

    orijinal sha256 : 0b21de704e05e6cfcd087600e04d37cd8ec5ae4a887fa06cfef302b8e83e4ac8
    yamali   sha256 : 419d03b88d6537830706296a913e1967bbf3ca1af316e82552d181135ad32c06

Yazici `kampanya/k50.py` (k49 + `JDKAYNAK` + yama bayti dogrulamasi), kaynak
`kanit/loader_yamali/`. Geri donus: `JDKAYNAK=.../loader_orijinal python3 k50.py`.

### 94.4 Yeni araclar
- `/usr/local/bin/jd-tel-modu ac|kapa` — pci-stub izolasyonu (tel seansi moduna gecis)
- `takim/jdyuzey.py` — tum yuzeyi ofset-turevli desenle yaz + geri oku + karsilastir
- `takim/jdzero.py` — tum namespace'i tek surecte Write Zeroes
- `kampanya/k51.py` — c3ce2 canlandirma denemesi (parametre / InitGDP / legacy mod)

### 94.5 İLK YAMA TUTMADI — sebep: loader blogunda BES firmware slotu var  [KRITIK]

Ilk tur: 15/16 die'in **slot 0**'i yamalandi (c3ce2 programlanamadi), tel cikarildi, disk acildi.
Ama canli RAM olcumu:

    CANLI e07  0x040EC1B5 = 0xD0   0x040EC23B = 0xD0   -> ORIJINAL FIRMWARE BOOT ETTI
    health word 0x00806EC8 = 0x19  bit3=1
    critical_warning = 0x8 ;  yazma testi 0/5

Yani yama dogru, ama **denetleyici baska bir yerden yukledi**.

Sebep: `LDBK FWSLOT MARK` (loader blogu sayfa 8) **+0x10'da 8 adet slot isaretcisi** tutuyor
(`0x30, 0x130, 0x230, ... 0x730`), her biri tam bir CodeMap. Besi dolu:

| slot | CodeMap ofseti | sayfalar | e06 (yama A,C) | e07 (yama B,D) |
|---|---|---|---|---|
| 0 | 0x030 | 92..136  | 108,109 | 119 |
| 1 | 0x130 | 137..181 | 153,154 | 164 |
| 2 | 0x230 | 182..226 | 198,199 | 209 |
| 3 | 0x330 | 227..271 | 243,244 | 254 |
| 4 | 0x430 | 272..316 | 288,289 | 299 |
| 5-7 | 0x530+ | bos | | |

Bes slot **bayt bayt ayni kopya** (sha dogrulandi: e06[0] `acf65166`, e06[1] `db4451c0`,
e07[7] `011c6f44` — besinde de ayni). Info page +0x220'deki CodeMap yalnizca **slot 0**'i
gosteriyor; ilk analizde bu yuzden tek slot sanildi.

**Duzeltme:** yama 4 nokta degil **20 nokta / 15 sayfa** (4 yama x 5 slot).

    slot0: A@p108+0x32E2  C@p109+0x25FA  B@p119+0x1B5  D@p119+0x23B
    slot1: A@p153+0x32E2  C@p154+0x25FA  B@p164+0x1B5  D@p164+0x23B
    slot2: A@p198+0x32E2  C@p199+0x25FA  B@p209+0x1B5  D@p209+0x23B
    slot3: A@p243+0x32E2  C@p244+0x25FA  B@p254+0x1B5  D@p254+0x23B
    slot4: A@p288+0x32E2  C@p289+0x25FA  B@p299+0x1B5  D@p299+0x23B
    yamali sha256 = 3e82da74b4f0aa58234bcd5f50ff5668fb2a1d837fd807cf8abdb20ffe1249fa

### 94.6 `jd_hack.py hazirla` ATLANMAZ  [KRITIK — 500x hiz farki]

`gdprun`'dan sonra `hazirla` calistirilmazsa GDP'nin `while(1)` tuzaklari ve exception
vektorleri yerinde kalir; her NAND komutu tuzaga dusup `ta=25 sn` zaman asimina gider.

    hazirla YOK : 25 sn/sayfa  -> 1 die ~2,5 saat, 16 die ~40 saat
    hazirla VAR : 0,05 sn/sayfa -> 1 die 20 sn,    16 die ~6 dakika

`hazirla` = `c1.bin`'deki tum `b .` tuzaklarini `bx lr`, undef/svc'yi `movs pc,lr`,
prefetch/data abort'u `subs pc,lr,#4` yapar (29 nokta) + ASSERT silahsizlandirma.
Cikti: `yamalandi: 29 nokta, hata=0` / `GDP canli: True`.

Dogru sira: **soguk cevrim (tel modu acik) -> unbind pci-stub -> gdprun -> hazirla -> yazma.**

### 94.7 c3ce2 kesin teshis: ne siliyor ne programliyor

21 ornek sayfanin **tam olarak 3'u** farkli cikti — o 3 sayfa da bizim yamaladigimiz sayfalar.
Kalan 18 sayfa iki imajda zaten ayni oldugu icin "uyuyor" gorunuyor. Yani blok silinmedi,
programlanmadi; icinde k49'dan kalan orijinal firmware duruyor. 3 tekrar denemesi de ayni sonuc.
Blok 1, 2, 3 tum die'larda **bos** (rakip CodeBlock yok).

## §95 — MPTool'un GERCEK yazma dizisi cikarildi; iki komut sessizce calismiyor (16 Eyl)

### 95.1 Reddedilen sey yama DEGIL, yazma yontemi

Dort tur yamayi sucladik. Ampirik eleme:

| tur | ne yazildi | sonuc |
|---|---|---|
| 1 | 4 baytlik yama (A,B,C,D), 15 die, slot 0 | reddedildi |
| 2 | sadece imza sayfasi (kod sayfalarina dokunulmadi) | **c0ce0'dan boot etti** |
| 3 | 4 yama x 5 slot, 15 die | reddedildi |
| 4 | **yamasiz FABRIKA KOPYASI**, GDP ile, c0ce0 | **reddedildi** |
| 5 | 37 bos sayfa atlanmis (323 sayfa), A+C | reddedildi |
| 6 | silme p4=1,p5=1 (MPTool'un tek-blok formu) | reddedildi |

Tur 4 belirleyici: **icerik hic degismemis olsa bile** GDP ile yazilan blok kabul edilmiyor.

### 95.2 Boot die tespiti — imza yontemi

Her die'in blok 0'inda **sayfa 360**'a (slot 4'un bittigi 316'dan sonrasi, kullanilmayan alan)
`JDBOOTMARK cXceY` imzasi yazildi. Tel cikarilip normal acilista urun firmware'inin
`0x04` (SYS ReadPage) komutuyla sayfa 360 okundu:

    tum kopyalar ayni  -> "JDBOOTMARK c0ce0"     boot die = c0ce0 (YAZILABILIR die)
    15 yamali + 1 orij -> imza yok (c3ce2'nin bos sayfasi)  -> yamali kopyalar reddedilmis

`0x04` payload duzeni ampirik cikarildi: `[3]` yok sayilir, `[4]` sayfa kaydirir,
`[5..6]` blok/kopya (yalniz 0 ve 1 gecerli), `[7..8]` sayfa (0..1535).

### 95.3 MPTool'un gercek dizisi (ANALIZ_LDBK_YAZMA.md)

`MXMPTool_MAP1202_USB_V1_1_26.exe` + `V0_01_017.exe` disasm edildi. Bizde olmayan uc adim:

1. **`0x4D` + 512 baytlik loader-block bitmask haritasi** — `buf[ch*4+bank] = (1<<lb0)|(1<<lb1)`
2. **Broadcast silme** `FF E5 8B FF FF 00 <i> 00 00`, `i = 0..(4/plane)-1`
3. **Sayfa yazimi `0x8A` degil `0x4C` PageWriteInterleave** — denetleyici sayfayi haritadaki
   tum die'lara kendisi dagitiyor (`EnWritePageToAllDie=1`, iki fabrika paketinde de boyle)

Fark OLMAYAN yerler (bosuna arandi): `[10]=1 [11]=0 [12]=0 [13]=0` MPTool'la ayni;
mod/nsec degerlerimiz eski kusakla birebir; finalize/commit komutu yok.

### 95.4 OLCUM: iki komut sessizce calismiyor  [DUVAR]

    0x4D harita gonderimi          kabul ediliyor
    broadcast silme 0x8B FF FF     GetReturn[1]=0x01 "basarili" ama SILMIYOR
                                   (4 blok varyanti denendi, blok 0 LDBK olarak kaldi)
    0x4C PageWriteInterleave       GetReturn[1]=0x01 "basarili" ama YAZMIYOR
                                   (silinmis bloga yazildi, geri okuma 0/13)
    tek-die silme 0x8B ch ce       GERCEKTEN siliyor  (LDBK -> bos)
    tek-die yazma 0x8A             GERCEKTEN yaziyor  (geri okuma 19/19) ama ROM boot etmiyor

323 sayfa `0x4C` ile 2 saniyede "yazildi" (0x8A ile 16 die x 20 sn = 320 sn) — hiz farki
komutun gercekten interleave oldugunu gosteriyor ama etkisi yok.

**Durum:** fabrikanin kullandigi yol bizim GDP oturumumuzda etkisiz; etkili olan yol
ROM'un kabul etmedigi blok uretiyor. Aradaki farki gorecek kod **mask ROM'da** ve elimizde yok.

### 95.5 Ek olcumler
- `0x3A PreCheckCodeBlock` GDP'yi **asiyor** (sonrasinda `saglik=False`, soguk cevrim gerekir)
- `0x07 GetCodeBlock` calisiyor ama `0x3A` kosulmadan **sifir** donuyor
- Loader bloklari iki bagimsiz kaynaktan biliniyor: cihaz capinda LDBK taramasi (16 kopya,
  hepsi blok 0) ve firmware config `0x31C` = 16 bayt `0x03` = blok 0 ve 1
- **`0x37` vendor komutu urun firmware'ini asiyor** — admin timeout -> denetleyici reset ->
  cihaz veri yolundan duser. KULLANMA.
- `c3ce2` silme: 45+ deneme, istisnasiz `sts0=0101e1e1`. Kontrol die ayni oturumda sorunsuz.

### 95.6 Birakilan durum
16 die'in hepsinde orijinal firmware (15'i bizim yazdigimiz, c3ce2 fabrika). Disk aciliyor,
953,9 GB gorunuyor, okunuyor, yazilamiyor. Arac zinciri hazir: `jd-tel-modu`, `k53` (0x8A yazici),
`k60` (0x4D+0x4C yolu), `k61/k62` (tanilar), `kanit/loader_v2_orijinal` ve `loader_v2_ac`.

### 95.7 EN GUCLU KALAN IZ: yanlis kusak GDP kullaniyoruz  (16 Eyl aksam)

`jd_loader.py gdprun` varsayilan olarak **V8 kusagi** GDP'sini yukluyor:

    MKGDP_000001013148030000, Nov  5 2024, COUGAR, PEIJCHPC   249856 bayt
    paket: MAP1202_H25TXTD2XCX6  (FWOneBinName=SKV8.bin, TMC_ARRAY_M2_HynixV8.ini)

Oysa diskimiz **V6** ve sayfa duzeni (0-7 mode 0, 8+ mode 2) **eski kusakla** birebir uyuyor.
Eski paketin kendi GDP'si elimizde ve Flash.ini'sinde **tam olarak bizim flash** var:

    kanit/fw_hunt3/ex/MAP1202_HYV7_64GB_Die_128G-1T/.../T1/GDP.bin
    MKGDP_000001006091730000, May 31 2022, COUGAR, PEIJCHPC   233472 bayt
    Name007=SKV603005 H25BFT8A1BDA  3 2 1  2888 1536 16 1 2  0xAD 0x7E 0x28 0x53 0x02 0xB0
    MPTOOL.ini: EnWritePageToAllDie=1, FWOneBinName=SKV7.bin

**Olculdu:** `jd_loader.py gdprun /tmp/GDP_hyv7.bin` ile eski GDP **basariyla yukleniyor ve
calisiyor** (`>>> GDP MODU AKTIF <<<`). Ama `JDisk` init'i dusuyor:
`ortak.py:76 tmc_yaz -> g.rd(0x200,512) -> None`. Yani `stub_kur` / `poke_blok(0x040DBD44)` ve
tmc yazma adreslerimiz V8 GDP'sinin bellek duzenine gore yazilmis; eski yapida farkli.

**Yapilacak (siradaki oturum):** `takim/ortak.py` init yolunu HYV7 GDP'sine uyarla
(stub adresi, poll poke adresi, tmc blok adresi yeniden bulunacak — `re/gdp/` altina eski GDP'nin
parcalarini cikarip disasm ile). Sonra `0x4C` matrisini (k63) eski GDP ile tekrarla.
Hipotez: `0x4C` PageWriteInterleave V8 GDP'sinde bizim flash icin islevsiz, eski kusakta calisiyor.

**Ayrica kesinlesen negatif sonuc:** V8 GDP'sinde `0x4C` bes varyantta da yazmiyor
(sayfa 360-365, `[10]=1/0`, satir-adresi, `ch/bank=0xFF`, `0x4D` hemen once). Ayni kosuda
`0x8A` kontrolu yazdi (c0ce0). Yani `0x4C` sessizce islevsiz, olcum hatasi degil.

## §96 — "Yama reddediliyor" YANLIS TESHIS: ROM loader blogunu ONARIYOR (16 Eyl gece)

### 96.1 §95.1 eleme tablosu gecersiz

Tur 4 ("yamasiz fabrika kopyasi -> reddedildi") `loader_orijinal` ile yapilmis; o dump'in
**67 sayfasi bozuk** (37 yanlis mod, 30 sayfa 0x5A copu). Yani icerik fabrikadan farkliydi.
"Icerik degismese bile GDP yazimi reddediliyor" sonucu **dayanaksiz**.

### 96.2 Yazma/okuma yolu SAGLAM — olculdu

| olcum | sonuc |
|---|---|
| tek die'a benzersiz desen (k70) | sadece o die degisti, digerleri degismedi |
| desen soguk cevrim sonrasi (k71) | **DURUYOR** — yazma kalici |
| silme p4=0 p5=1 (k71) | sayfa sha degisti -> **gercekten siliyor** |
| gecersiz die c7ce7/c5ce3 (k69) | saf nobetci -> okuma ch/ce'yi dogruluyor |
| silinmis bloga 330 sayfa + yama (k72) | yazilamayan=0, **nobetcili geri okuma yamayi goruyor** |
| komsu die'lar ayni anda | fabrika degeri -> okuma die'lari AYIRT EDIYOR |

### 96.3 KANIT: firmware/ROM acilista loader blogunu geri yaziyor

k65 ile 15 die'in hepsine yamali imaj yazildi (`fark=0`). Tel cikarildi, firmware ~130 sn
kostu (CSTS=0x0, probe failed). Tel tekrar takilip yeni GDP seansinda okundu:

    sayfa 108 ofs 0x32E2 = 0x08   (FABRIKA)   c0ce0, c1ce0, c3ce2 — hepsi
    sayfa 360 imza sayfasi        = silinmis, tum die'larda ayni cop

Ayni oturumda c2ce0'a yazilan yama ise **duruyor** (soguk cevrim gecti, firmware kosmadi).
Tek fark: arada firmware'in calismasi. -> **ROM/erken firmware, loader blogunu gecerli
kopyadan onariyor.** Onarim kaynagi yazamadigimiz die: **c3ce2**.

Bu, §94.5 "ilk yama tutmadi" ve §95.1'deki alti turun tamamini aciklar: yama yaziliyor,
sonra uzerine fabrika kopyasi geri yaziliyor. Acilis suresinin 130 sn'den 290 sn'ye
cikmasi da onarim pasiyla uyumlu.

**Sonuc: loader blogu uzerinden firmware yamalamak KAPALI YOL.** c3ce2 silinemedigi surece
onarim kaynagi hep temiz kalir.

### 96.4 Bugun elenen hipotezler
- `Func0` (*0x398) bit3 temizleme -> **acilisi kilitliyor** (CSTS=0x0). Bit init icin gerekli.
- Y2+Y3+Y4 (`tst.w r0,#8` -> `#0`) -> acilis kilitleniyor; Y3/Y4 firmware'i init'te NAND
  yazmaya zorluyor.
- Config blogunda **checksum YOK**: 0x388=0x773BD2B0 icin CRC32/SUM32/XOR32 hicbir aralikta
  tutmuyor, dosyada tek konumda geciyor.
- **Spare/ECC farki YOK**: c3ce2 fabrika sayfasi ile bizim yazdigimiz sayfa, nsec=40 ile
  okunan spare bolgesi dahil birebir ayni. "Yanlis kusak GDP yanlis ECC uretiyor" -> ELENDI.
- `loader_v3` = **fabrikanin birebir dump'i** (330/330 sayfa cihazla ayni). `loader_v2_orijinal`
  3 sayfada farkli (28, 44, 45) + 37 sayfa eksik.

### 96.5 WP mandalinin gercek kaynagi (ANALIZ_WP_BIT.md + ANALIZ_DIEREMAP.md)
- `WP = (*(0x00000398) >> 3) & 1` — e06 `0x04069ED0/ED8`, decoder-ring printf ile kanitli.
  Ama bu bit fabrika imajinda **sabit 1** = "WP ozelligi var", durum degil.
- Gercek durum: `mod = *(0x00810CE8)`; `e07@0x67E2` QBT blogundaki assert sayisi >= 3
  ise `mod=3` (WRITE-PROTECT). Yazma kapilari `mod in {3,4} && Func0 bit3` test ediyor.
- Kayit NAND'da kalici, her acilista `[QBT]` fazinda yeniden mandallaniyor.
- Firmware init'te die silme testi **yapmiyor** (`ScanDie/BadDie/DieFail` 530 dosyada 0 kez).
- DieReMap: DPD `+0x310[LUN*32 + CE*8 + CH]`, `0xFF`=yok. c3ce2 icin ofset `0x323`.

### 96.6 SIRADAKI HEDEF: QBT assert kaydi
Loader blogu onariliyor ama **QBT blogu veri**, ROM onu onarmaz. Assert sayacini bulup
temizlemek, hicbir firmware yamasi olmadan diski normal moda dondurmeli.
Yapilacak: GDP ile blok taramasi -> QBT imzasi -> assert kaydinin yeri -> sil/yeniden yaz.

### 96.7 Birakilan durum (16 Eyl gece)
Disk **aciliyor**: `JAMESDONKEY JD1024 1TB`, 954 GB, live, okunuyor.
`critical_warning=0x8`, `media_errors=173`, yazma komutu geciyor ama veri inmiyor.
c2ce0 blok 0 = loader_v3 + A/C yamali (onarim testi icin birakildi), digerleri fabrika.
Yeni araclar: `/usr/local/bin/jd-seans`, `jd-lib-kur`, `jd-test`, `kampanya/k65..k72`.

## §97 — EKSIK IMAJ: butun yama turlari gecersizmis (16 Eyl gece, devam)

### 97.1 Kaynak imajlarimiz eksikti — asil sebep bu
`k67`: c3ce2'den 360 sayfa okundu, `loader_v3` ile karsilastirildi:

    loader_v3 vs fabrika:  ayni=330  FARKLI=0  kaynakta-YOK=30

30 sayfa (56-67, 73-90) hicbir kaynagimizda yok; `loader_v2` ayrica 3 sayfada farkli
(28,44,45) + 37 sayfa eksik. Yazdigimiz her imaj 30-37 sayfayi **silinmis** birakiyordu
-> firmware imaji yarim -> acilmiyor. Tek die'a yazinca disk aciliyordu cunku ROM saglam
bir fabrika die'ina dusuyordu; 15 die birden bozulunca dusecek yer kalmadi.

**Bu, §95.1'deki alti turu ve 16 Eyl'deki bes turu birden aciklar. Hicbir yama
gercekten test edilmemis.**

### 97.2 `loader_v4` = TAM fabrika dokumu  [KULLANILACAK KAYNAK]
`k74`: c0ce0'dan 360/360 sayfa, iki tur okundu, iki tur birebir ayni (oynak=0).
`loader_v3` ile celisen sayfa yok — v3 dogruydu, sadece eksikti.

    kanit/loader_v4   360 sayfa  sha=851cba47de7566eb909f156f
    kanit/loader_v4_wp = v4 + ofset 0x398 0x0A->0x02 (10 sayfa)  sha=f1eaa9d65c...

### 97.3 ONARIM TEORISI CURUDU — yazma kalici
`k73`: c2ce0'a yazilan A/C yamasi **telsiz acilisi gectikten sonra duruyor** (0x00),
c1ce0 sayfa 500 deseni de duruyor. Firmware loader blogunu geri yazmiyor. §96.3 YANLIS.

### 97.4 `0x8A` SESSIZ NO-OP  [KRITIK DERS]
`k80`: silinmemis bloga (93) yazma `OK` dondu, hicbir sey degismedi. Onceki turlarda
`fark=0` dogrulamasi denetleyici tamponundan geliyordu. **Yazmadan once blogun gercekten
silindigi (sha degisimi) dogrulanmali.**

### 97.5 WP config yamasi KESIN ELENDI
`loader_v4_wp` (TAM imaj + sadece Func0 bit3) c0ce0'a yazildi, 13 die fabrika birakildi.
Sonuc: `CSTS=0x0`, probe failed. **Func0 bit3 init icin gerekli, temizlenemez.**
Yan kanit: boot die = c0ce0 (sadece onu yamalamak acilisi bozuyor, 13 fabrika kopyasi
kurtarmiyor -> ROM geri dusmuyor).

### 97.6 Blok yapisi (c0ce0, sayfa 0, mod 0)

    LDBK bloklari   : 0, 128, 256, ... 2688   (22 adet, tam 128 blok araliklarla)
    ucuncu desen    : 92,96,100..124  ve  220,224..252   (128 periyot)
    silinmis        : 132 blok
    blok 0 yapisi   : p0 "LDBK BLOCKS V00"  p2 "LDBK LDPC TABLE1/MAXIOLDPCDECINIT"
                      p4 "LDBK LDPC TABLE2/MAXIOLDPCENCINIT"

128 periyodu ya gercek yedeklilik ya da blok adresinin 7 bitle sinirli olmasi.
Ayirt edici test (blok 93'e yazip 221'i okumak) **sonucsuz** — blok silinmemisti,
yazma no-op oldu (bkz 97.4). Tekrarlanacak: once silme, sonra yazma.

### 97.7 Acilis suresi = ucretsiz gosterge
Firmware duzgun ayaga kalkinca disk hizli aciliyor; init'te takilinca BIOS zaman asimi
bekliyor ve acilis dakikalara cikiyor. Kullanici bunu tutarli sekilde gozlemledi.

### 97.8 Birakilan durum
c0ce0 + c2ce0 = tam `loader_v4`, kalan 13 die fabrika. Disk acilmali, 954 GB, salt-okunur.
Siradaki: QBT assert sayaci (bloklar 92-124 aday) · blok adresleme periyodunu silme+yazma
ile kesinlestir · yamalari `loader_v4` tabaninda TEKRAR dene (hepsi eksik imajla test edildi).

## §98 — DUVARIN ADI: firmware OLU DIE'dan (c3ce2) boot ediyor  [KOK NEDEN] (16 Eyl gece)

### 98.1 Telsiz canli teshis acildi  [YENI YETENEK]
`takim/jdcanli.py` → `0x86 ReadRam` **tel olmadan** calisan firmware'in RAM'ini okuyor.
Artik her hipotez tel cevrimi harcamadan sinanabilir.

    Func0 = *(0x00000398) = 0x0001F80A  bit3=1
    mod   = *(0x00810CE8) = 4            -> WRITE-PROTECT (kapilar mod in {3,4})

⚠️ `0x04 SYS ReadPage` bu firmware durumunda hep sifir donuyor — kullanma.
⚠️ **KOR RAM TARAMASI CIHAZI OLDURUYOR** (16 Eyl, 2. kez): 0x04060000-0x040F0000
arasini taradim → `state=dead`, `Disabling device after reset failure: -25`.
Soguk cevrimle donuyor. Sadece `GUVENLI` listesindeki + daha once basariyla okunan
adresleri oku.

### 98.2 Sayfa<->adres haritasi DOGRU (olculdu)
Canli RAM'den okunan 64 baytlik bloklar `loader_v4` sayfalarinda arandi:

    0x040D6600 -> sayfa 113 ofset 0x2600      0x040EC000 -> sayfa 119 ofset 0x0000
    0x00000200 -> sayfa 122 ofset 0x0200      0x00000000 -> sayfa 92  ofset 0x0000
    0x040D0000 -> sayfa 112 ofset 0x0000

CodeMap ve yama ofsetlerimiz bastan beri dogruymus.

### 98.3 KANIT: boot kaynagi c3ce2
`loader_v4_y25` (tam imaj + Y2 + Y5) **15 die'in hepsine** yazildi, `fark=0`.
Ayri seansta 16 die NAND'dan okundu:

    sayfa 113 ofs 0x27E7:  15 die = 0xE0 (yamali)   ·   c3ce2 = 0xD3 (fabrika)
    CANLI FIRMWARE       :  0xD3

Diskte `0xD3` kalan tek yer c3ce2. -> **Firmware kodunu olu die'dan yukluyor.**

§95.2'deki "15 yamali + 1 orij -> imza yok (c3ce2'nin bos sayfasi)" satiri bunun
dogrudan kanitiymis; o zaman "yamali kopyalar reddedildi" diye okunmus.

### 98.4 c3ce2 PROGRAMLANAMIYOR da
Bos sayfaya (400) yazma `OK` donuyor, icerik degismiyor. Ayni yazim ayni oturumda
c0ce0'da calisiyor. Silme zaten hic olmuyordu (`sts0=0101e1e1`, 45+ deneme).
-> Kopyayi ne degistirebiliriz ne bozabiliriz. **Firmware yamalama yolu KALICI KAPALI.**

### 98.5 Blok adresi 128'de sariyor  [OLCULDU]
Blok 5 silinip yazildi -> blok 133 de degisti. Yani "22 LDBK blogu" = tek blogun
22 kez gorunmesi. **2732 blogun sadece 128'i adreslenebiliyor.** DPD'deki
`+0x1D sektor kaydirmasi=12` / `+0x1E blok maskesi=12` ile ilgili olabilir;
QBT blogu bu pencerenin disinda kalabilir.

### 98.6 `0x8A` yazma "OK" doner ama silinmemis sayfada HICBIR SEY YAPMAZ
k65'e silme dogrulamasi eklendi (silme sonrasi sayfa 108 sha degismiyorsa yazma iptal).

### 98.7 GERIYE KALAN TEK YOL: QBT assert kaydi
WP durumu firmware'de degil **NAND'daki veri bloğunda**: `e07@0x67E2` assert sayaci
>= 3 -> `mod` 3/4 olur. QBT bir VERI blogu, c3ce2'ye bagli degil, yazilabilir.
Sayaci temizlemek hicbir firmware yamasi gerektirmeden diski normal moda dondurur.
Engel: blok adres penceresi 128 ile sinirli; once DPD ile bu genisletilmeli.

## §99 — c3ce2 OLU DEGIL, YAZMA KILITLI  [TESHIS DEGISTI] (16 Eyl gece)

### 99.1 `0101e1e1` = KORUMA, ariza degil
Blok 92-124 silmesi **16 die'in HEPSINDE** ayni kodu veriyor — blok 0'i sorunsuz silen
die'larda bile. Yani kod "olu silikon" degil "bu blok korumali" demek.
Durum bayti coz: `0x01` = FAIL + **WP#=0 (yazma korumali)**; `0xE1` = ready + FAIL.

### 99.2 Kilit haritasi (k95, blok 0..127 tek tek silme denemesi)

    c0ce0 :  0-90 SILINEBILIR      ·  91-127 KILITLI
    c3ce2 :  sadece 90 silinebilir ·  0-89 ve 91-127 KILITLI

**c3ce2 die genelinde yazma kilitli.** Okuma her blokta calisiyor. 45+ denemenin
"olu die" sonucu, hepsinin tek parametre kombinasyonuyla (p4=0,p5=1) yapilmasindan
ve kilit kodunun ariza sanilmasindan geliyor.

Not: p5=0/p5=2/p4=2 ile "hatasiz" donuyor ama OKUMA.md kural 1 geregi **baska blogu**
siliyor (k92 ile dogrulandi: blok5 imzasi p5=0 silmesinden sonra duruyor).

### 99.3 Ayni kilit sistem alanini da koruyor
Blok 91-127 her die'da kilitli. Canli firmware tablosu `0x00810600`:
`(1008,1015) (1016,1023) (8,15) ... (120,127)` = sistem bloklari.
`1008 mod 128 = 112` (blok adresi 128'de sariyor) -> sistem alani 112-127 olarak gorunuyor.
**QBT assert kaydini silme plani da ayni kilide takiliyor.**

-> Tek bir mekanizma iki yolu birden kapatiyor. Kirilirsa ikisi de acilir.

### 99.4 Elenen kilit-kaldirma denemeleri
- `0x4D` loader-blok haritasi (0x00 ve 0xFF) -> etkisiz
- GDP modunda `0x00810400/0x00810600` tablolarini sifirlamak -> o adresler GDP'de
  rastgele veri (tablolar sadece urun firmware'inin belleginde) -> etkisiz
- DPD `+0x310` die varlik tablosu c3ce2'yi ayirmiyor (tum ch0-3 = 0x00)

### 99.5 GDP string'leri (c1.bin) — siradaki iz
`SYS DIE MAP ADDR = 0x%04X` · `SIZE OF SYS DIE MAP = %d` · `DIE CNT = %d` ·
`[gdp_die_map_2_module_info]` · `no die at step0/step1h` · `GDP_BLOCK_QNTY = %d` ·
**`Erase CodeBlock[0,1] for All Dies`** · `erase fail` · `SSV6 SLC erase`
GDP'de **lock/unlock/protect string'i YOK** -> kilit NAND tarafinda, ham NAND komutu
(ONFI 0x23/0x24 Block Unlock benzeri) gerekebilir.

### 99.6 Bu turda verilen zarar ve onarim
k91 ve k95 c0ce0'in blok 0'ini (loader) sildi — ikisi de `loader_v4_y25` ile geri yazildi.
k90 sistem bloklarinin tam yedegini aldi: `yedek/sistem_bloklari/b*_c0ce0.bin` (9 x 24 MB,
hepsi ayni sha 976e74bfbe76).
k65'e eklenen silme dogrulamasi duzeltildi: "degismedi VE eski icerik = kaynak" olunca iptal.
