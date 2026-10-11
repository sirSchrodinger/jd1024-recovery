# JD1024 / MAXIO MAP1202 — donanimsal ariza arastirmasi (kristal/PLL/guc/lehim)
Tarih: 2026-09-12

## ARAC NOTU
- WebSearch kotasi bitmis. Bing/DDG/Google/Yandex/Baidu/Sogou bu cikis IP'sinden
  anti-bot ile "poison" ediliyor (alakasiz cached SERP donuyor). Calisan yollar:
  - dogrudan site fetch (curl / WebFetch)
  - forum.hddguru.com phpBB arama (calisiyor)
  - so.csdn.net /api/v3/search (calisiyor, CN)
  - api.stackexchange.com (calisiyor)
  - api.marginalia.nu/public/search (calisiyor, nis)
  - search.bilibili.com (calisiyor)

## BULGU 1 — usbdev.ru topic 12338 TAM OKUNDU  [SOMUT VAKA]
URL: https://www.usbdev.ru/f/index.php?topic=12338.0
Baslik: "Maxio MAP1202 изучение, прошивки, особенности" (roman2013, 15 Ara 2024)
Tek sayfa, 15 mesaj (#0..#14), son mesaj 19 Tem 2026.

Disk: Apacer AS2280P4 1TB, MAP1202 + Intel 144L N38A QLC (bizimki SK hynix V6 —
kontrolcu ayni, NAND farkli).

### #2 (17 Ara 2024) — BASARISIZ acilisin TAM UART logu
Onemli satirlar (sirayla):
  @BM(4,0) / @DIE 3 3 3 3 / hc init done / UART-RDY 00 / B1TCM-Over
  SRAM Cache:40cd200 40ce800 / UART-RDY 01
  Faa Format:9,14,3,2,2
  DDR:1200                      <-- ic DDR/PLL saati kurulmus
  trim_op(e) trim_bg(1e) ...    <-- NAND trim parametreleri
  RAID:4,4,4 / E2E
  Dual CPU Run / CPU0 GO        <-- CPU'lar kosuyor
  matrix size is (2994,16f4) / LDPC init
  FA_DRV 4 / FA_IF 37 / Z-CFG:45 3f c b (x4) / FA_TM 3c / ZQ / DCC
  DS init 4,5265c00
  [CodeBlk]S ... Fix SLC:d,5 / TblPart:a,8
  PBN-#19,BAD-8 ... TotalBBB=10 / Bad(161)LogBlk(212)Rate(24)   <-- NAND OKUNUYOR
  [CodeBlk]E
  [QBT]S ... Q-Query-NG / Q-NoVld / Q-RdFail / [QBT]E,3,ms      <-- SISTEM TABLOSU OKUNAMIYOR
  [PBT]S ... #BB / #BadCnt:3 ...
  # HeadSrch / # B-Srch / # HDieSrch ... chkptr-faa ...
  blk_list3 / blk_list4 / [T]blk-restore,1,0.013,13742
  [SD-Rslt: ffff] a6 1c 754c80  (onlarca kez tekrar)            <-- NAND okuma sonucu 0xFFFF
  HOT PLUG:0 / >PE_RISE / >PE_FALL idle:1                       <-- PCIe olaylari akiyor
  ... sonsuz [SD-Rslt: ffff] dongusu

### #3 (18 Ara 2024) — BASARILI acilis
"Zacepil UART normalno... В итоге при очередном старте в консоле появилось
сообщение о частоте 'CLK:550,475,137'. Диск распознался системой."
= "UART'i duzgun bagladim... nihayet bir sonraki acilista konsolda frekans mesaji
   'CLK:550,475,137' cikti. Disk sistem tarafindan taninmis oldu."
Ardindan tam kimlik dokumu: MKSSD_...,Jul 28 2022,10:25:35,MAP1202,KC1UCA3H
NAND Freq: 48920, Channel number 15, CE number 22, HMB 16384 KB.

### KRITIK YORUM (bizim hipotez icin)
"CLK:550,475,137" satiri BASARISIZ logda hic yok AMA basarisiz logda da
DDR:1200, Dual CPU Run, LDPC init, NAND ID okuma, bad-block tarama var.
=> Kristal/PLL zaten calisiyor. "CLK:" satiri GEC bir asamada (firmware yuklendikten
   sonra saatlerin operasyonel frekansa cikarilmasi) basiliyor.
=> "CLK yok" = "gec asamaya hic gelinemedi" demek; "kristal yok" demek DEGIL.
=> Bu vakada takilma noktasi [QBT]/[PBT] = sistem/FTL tablolarinin NAND'den okunmasi;
   [SD-Rslt: ffff] = NAND okumasi hep 0xFFFF (silinmis/okunamayan sayfa).
=> usbdev vakasi KRISTAL DEGIL, NAND/FTL-tablo arizasi.

### Diger notlar
- #8: roman2013: "Диск сдох достаточно быстро после 'магии'" — disk kisa surede tamamen oldu.
- #12 JenDos_50: ayni tip diski MPTool ile yeniden acti (N38A + KC1UCA3H olarak yeniden
  adlandirdi); prosedur: reflash -> 390GB'da dustu -> Sort ~9 saat -> Inherit RDT+Sort ->
  450GB'da takildi -> 400GB'a kirparak calisir hale getirdi. => yazilimla kurtarilabiliyor.
- #14 DarwinLudwig (Global Moderator, "EKSPERT"): "maxio'da tek buyuk zorluk hafiza
  degisimi icin GPIO secimi... uygun aracin varsa geri kalan her sey trivial."
- MAP1202 icin acik MPTool YOK (N38A/B58R gibi bazi NAND'lerde). MAP1602 icin var.
- Cin kaynakli firmware deposu: https://file.diyflash.top/

## BULGU 2 — ROM MODE (kisa devre) = EN UCUZ AYIRT EDICI TEST  [SOMUT VAKA + PROSEDUR]
CSDN, gabrielpic, 2024:
https://blog.csdn.net/gabrielpic/article/details/137383904
"MAP1202 anakontrolculu tasinabilir SSD bozuldu, muhtemelen ani elektrik kesintisi
firmware'i dusurdu... yarim ay arastirdim, sonunda hallettim."
Prosedur:
 1. Kontrolcu modeli + NAND process belirle (or. MAP1202 + YMTC X2-9060)
 2. liangchan buluo (量产部落) sitesinden "MAP1202 + <NAND>" MPTool indir
 3. MPTool'u ac; **METAL CIMBIZLA kart uzerindeki IKI ROM NOKTASINI KISA DEVRE ET**
    ("hangisi ROM noktasi bilmiyorsan defalarca deneyerek bul")
 4. Kisa devre BASILI iken diski bilgisayara tak -> yazilim diski TANIR
 5. Cimbizi cek (kisa devreyi kaldir), Auto Detect -> Tool Type: MPT ->
    Preformat Mode: "Inherit FW BB" / "Auto Inherit" -> START -> yesil "Pass"
 6. Tekrar tak, disk yoneticisinden bolumle/formatla
Uyari: acma (开卡) VERIYI SILER.

Genel prosedur (CSDN m0_55207244):
https://blog.csdn.net/m0_55207244/article/details/126171747
"Acma araciyla SSD arizalarinin %90'indan fazlasi duzeltilebilir."
- ROM jumper genelde "ROM", "JP1" (JMicron'da J1; Intel/ADATA'da cok modelde J3)
  yazisinin yanindaki iki delik/pad.
- Bilgisayar yeni cihazi taniyinca kisa devreyi KALDIR; acma sirasinda kisa devre
  BIRAKMA, aksi halde islem basarisiz olur.
- On panel USB / USB hub / uzatma kullanma; dogrudan arka panel USB. Guc yetersizligi
  acma hatasi yapiyor.
- "Ikinci el acma" destekleyen ucuz kutular (JM20329E) ise yaramiyor; sadece disk
  zaten calisirken acabiliyorlar. Muhendislik modu icin gercek acma karti gerekiyor
  (JM20329C/D vb.).

### NEDEN AYIRT EDICI
ROM mode, kontrolcunun ICINDEKI maske ROM'undan boot eder; NAND'deki firmware'i
tamamen ATLAR. Yani:
- ROM mode'da cihaz gorunuyorsa -> kontrolcu, ic PLL'ler, kristal, guc raylari SAGLAM.
  Ariza = firmware/FTL tablolari/NAND.
- ROM mode'da bile hicbir sey yoksa -> donanim supheli.
Maliyet: 0 TL (cimbiz). Risk: kisa devreyi yanlis pada yaparsan riskli; ama pad'ler
genelde ROM/JP1 etiketli.

## BULGU 3 — M.2 M-key (Socket 3) pinout, 3.3V noktalari  [BELGE]
https://pinoutguide.com/HD/M.2_NGFF_connector_pinout.shtml
3.3V besleme pinleri (M-key): **2, 4, 12, 14, 16, 18, 70, 72, 74**
GND: 3, 9, 15, 27, 33, 39, 45, 51, 57, 71, 73
PERST# = 50, CLKREQ# = 52, REFCLKN = 53, REFCLKP = 55 (100 MHz host REFCLK),
PEWAKE# = 54, MFG1 = 56, MFG2 = 58, SUSCLK(32.768 kHz) = 68,
CONFIG_0=21, CONFIG_1=69, CONFIG_2=75, CONFIG_3=1, DEVSLP=38, DAS/DSS=10
=> Karta giren TEK guc rayi 3.3V'tir. Karttaki DC-DC (8 pinli cip + bobin) bundan
   ic 1.2V/1.8V (ve NAND icin ~1.8V/2.5V) uretir.

## BULGU 4 — ROSSMANN GROUP "Maxio SSD Architecture" sayfasi (EN DEGERLI KAYNAK) [UZMAN GORUSU]
https://rossmanngroup.com/services/ssd-data-recovery/maxio-architecture
(Louis Rossmann, Austin lab; guncelleme Agustos 2026; 25 bolum)

### Ariza triyaj tablosu (dogrudan alinti)
| Belirti | Tespit | Termal | Muhtemel ariza | Yol |
| "MAP1602" olarak gorunur, 0 byte / 2MB | BIOS'ta GORUNUR | normal sicaklik | **Firmware Panic / FTL bozulmasi** | PC-3000 (SATA) / board repair (NVMe) |
| Hicbir yerde gorunmez | enumerate YOK | **soguk** | **Olu kontrolcu VEYA SAAT KRISTALI** | komponent seviyesi mikro-lehim |
| Hicbir yerde gorunmez | enumerate YOK | **kizgin** | kisa devreli PMIC/kondansator | board repair |
=> Rossmann "clock crystal"i ACIKCA sayiyor AMA "hic enumerate ETMEYEN + soguk" satirinda.
   Bizim disk 8GT/s x4 enumerate ediyor, config space cevapliyor, LED yanip sonuyor.

### MAP1202 hakkinda
- MAP1202 = Gen3 x4, DRAM-siz, FTL'i HMB ile host RAM'inde tutar.
- **Tipik ariza imzasi (Rossmann'in kendi tablosu): "FTL corruption, 0 bytes, HMB loss after power cut"**
- PC-3000 SSD MAP-serisini DESTEKLEMIYOR (MAS0902/MAS1102 destekli, MAP1202/1602/1602A degil).
- "Guc kesilince ucusan FTL delta'si host RAM'de kalir, NAND journal'ina hic yazilmaz.
   Sonraki acilista kontrolcu, fiziksel konumlari artik uymayan bir journal okur.
   Guvenli duruma gecer ve 0 byte bildirir."
- **MPTool UYARISI: Uzerinde veri olan diske MPTool uygulamak = ani veri yok olusu.**

### NVMe kart guc alanlari (3.3V M.2 girisinden turetilir) — SEMPTOM ESLESMESI
- **VCC_CORE** cokerse: 3.3V'ten standby akim ceker ama PERST# release'i hic asserte etmez
  -> host PCIe link'i HIC gormez.        [bizde link VAR -> VCC_CORE saglam]
- **VCC_NAND** olurse: kontrolcu ROM'unu boot eder, sistem alanindan firmware yuklemeye
  calisir ve **her NAND okumasi 1'ler dondugu icin TAKILIR**.   [bizim tabloya BIREBIR uyar;
  usbdev UART logundaki `[SD-Rslt: ffff]` = hep 0xFFFF ile de birebir uyar]
- **VCCQ_NAND** cokerse: PCIe'de enumerate eder, ilk FTL okumasinda panic, ham "MAP1602"
  descriptor + kucucuk kapasite.          [kismen uyar]
- **VCC_IO / PCIe analog** toleransta degilse: link Gen1 x1'e duser ya da LTSSM basarisiz.
  [bizde Gen3 x4 tam -> VCC_IO saglam]

### Multimetre protokolu (Rossmann'in kendi bench sirasi)
1. Stereo mikroskopla gorsel: yanik, eksik komponent, kalkmis pad, korozyon.
2. **Guc YOKKEN** her buck regulator bobininde sureklilik: saglam bobin <1 ohm; acik = yanmis.
3. **Ray-toprak direnci** (guc yokken, dusuk-ohm kademesi): VCC_CORE(1.1/1.2V),
   VCCQ_NAND(1.8V), VCC_NAND(3.3V). **Sifira yakin = sert ariza.**
   - ~0 ohm cekirdek rayi = kontrolcu die kisa devre (kurtarilamaz)
   - birkac ohm ~ birkac on ohm = MLCC kisa devresi (tamir edilebilir)
4. 10 ohm altindaki raya 1V/1A akim-sinirli enjeksiyon + termal kamera.
5. Bench supply'dan calistirip her rayda AKTIF gerilim dogrulamasi.

### BGA mikro-catlak / FLEX TESTI  [bu SORU 5'in cevabi]
- "Tekrarli termal cevrim, kontrolcu IC ile PCB arasindaki BGA lehim toplarinda
  mikro-catlaklar yaratir. **Bu catlaklar ciplak gozle gorunmez. Disk tamamen
  olmeden once ARALIKLI CALISABILIR.**"
- **"Kontrolcunun BIR KOSESINE HAFIF BASKI uygulayinca geri gelen bir disk = DOGRULANMIS
  mikro-catlak vakasidir."** (Rossmann, birebir) -> flex testi gecerli bir teshis.
  Hangi kose oldugu not edilir, reflow profilini o belirler.
- Reflow vs reball: once Zhuo Mao BGA istasyonunda profil ile reflow; basarisizsa tam reball.

### SICAKLIK / Vth  [SORU 4]
- "3D TLC & QLC'de durumlar arasi marj o kadar dar ki **20-30 °C'lik ortam sicakligi
  degisimi Vth'yi okuma sonucunu ceviren kadar kaydirir**."
- "**SOGUK pakette basarili olan bir Read Retry offset'i, paket isindiginda cogu zaman
  basarisiz olur.**" -> yasli/sarji kacmis hucreler icin SOGUK/SABIT sicaklik daha iyi.
- Lab hedefi maksimum sogutma degil, **SABIT** paket sicakligi.
=> "Dondurucu numarasi" NVMe'de fiziksel temeli VAR ama mekanizma kristal degil,
   NAND Vth'si. Yogusma riski nedeniyle dondurucu degil, ~10-15 °C serinlik mantikli.

## BULGU 5 — Northwind (profesyonel lab), hddguru 2025 [UZMAN GORUSU]
https://forum.hddguru.com/viewtopic.php?f=13&t=45359  ("Maxio SSDs now recoverable", May 2025)
"Maxio SSD'leri (hem 0902 hem 1102) artik destekliyoruz. Cozum, surucunun panic'e girip
 safe mode'a gectigi vakalarda CALISMIYOR. Ornegin **surucunun BSY kaldigi** vakalarda
 iyi calisiyor. Hala gelistirme asamasinda ama **su ana kadar %70 basari orani**."
=> "BSY'de kalma" (= CSTS.RDY hic 1 olmama) Maxio'da BILINEN, YAZILIMLA cozulebilen bir
   durum. Donanim arizasi olarak siniflandirilmiyor.

## BULGU 6 — Linux cekirdegi: CAP.TO ve bekleme suresi [BELGE]
drivers/nvme/host/core.c (nvme_enable_ctrl / nvme_wait_ready), include/linux/nvme.h
  #define NVME_CAP_TIMEOUT(cap) (((cap) >> 24) & 0xff)
  return nvme_wait_ready(ctrl, NVME_CSTS_RDY, NVME_CSTS_RDY, (timeout + 1) / 2, "initialisation");
Hata mesaji: "Device not ready; aborting initialisation, CSTS=0x%x"
BIZIM CAP = 0x00200030ff0103ff -> TO = 0xFF = 255 -> **255 * 500 ms = 127,5 saniye**
Linux (255+1)/2 = **128 saniye** bekler. Yani firmware, hazir olmasinin 2 dakikaya kadar
surebilecegini ilan ediyor. Elle test edilirken bu kadar beklenmediyse yanlis negatif olur.
CAP'in geri kalani tutarli: MQES=1023, CQR=1, DSTRD=0, NSSRS=1, CSS=NVM, MPSMIN=4K, MPSMAX=16K.
VS=0x00010400 -> NVMe 1.4.0. CC=0x00460001 -> EN=1, IOSQES=6, IOCQES=4 (normal).

## BULGU 7 — SSD'de kristal arizasi: gercek ama NADIR + MEKANIK HASARLA BIRLIKTE
[SOMUT VAKA] Zero Alpha (AU data recovery), "Bad Crystal Oscillator Fixed! USB Flash Drive
Stopped Working" https://youtu.be/kbekvU3qth8
"Bu 4GB Comsol USB bellek **BUKULMUSTU** ve daha once bir teknisyen ustunde calismisti.
 Zavalli kucuk kristal osilator sorunun kaynagiydi. Teshisi ve yenisiyle degistirmeyi
 gostereyim." Kontrolcu SM3255Q-AB. Not: "USB 2.0 cihazlarda kontrolcu ve hafizanin
 saat/zamanlama islevleri icin 12.000 MHz osilator yaygindir."
=> Kristal arizasi GERCEK ama bu vakada **fiziksel bukulme** var; ve cihaz TAMAMEN olmustu.

[UZMAN GORUSU] electronics.stackexchange 684589 "32kHz crystal long start time on 10% of
PCBs we order" https://electronics.stackexchange.com/questions/684589
Marjinal osilator baslatma gercek bir olgu; nedenleri: yanlis yuk kondansatoru (12.5pF
kristale 22pF yerine 12pF takinca duzeldi), asiri surme seviyesi, **fluks kalintisi/kacak
yollari** (kursunsuz gecisinde ilk partide kartlarin sadece %10'u calismisti), marj testi =
seri direnc ekleyerek osilasyonun durdugu noktayi bulma.
!! AMA: bu 32 kHz, alti-mikrowatt suruculu bir osilator. SSD'nin MHz'lik kristali cok daha
   yuksek surme seviyesinde calisir ve kacak/kirlilige karsi cok daha az hassastir.
   Bu vakayi dogrudan SSD'ye tasimak yanlis olur.

## BULGU 8 — Rossmann "SSD Power Loss Recovery" [UZMAN GORUSU]
https://rossmanngroup.com/services/ssd-data-recovery/power-loss-recovery
### Guc kesintisi sonrasi belirti matrisi (ilgili satirlar)
- "BIOS no-detect, no link" -> olu/beslenmeyen -> patlamis PMIC/regulator/kisa devreli cikis kondansatoru
- "**BSY (busy), hangs POST**" -> **sonsuz init dongusu** -> "kontrolcu, bozulmus FTL bloklarinda
   **read-retry dongusune girmis**" -> PC-3000 vendor komutu ile takilmis init'i asma
- "Enumerates at 0 capacity" -> safe mode, default kimlik -> FTL okunamiyor
- "**Drive forced into read-only**" -> **kendini koruma kilidi** -> "firmware sistemik FTL
   tutarsizligi tespit etti, yazma ve TRIM'i engelledi" -> hemen imaj al, chkdsk/fsck YAPMA
   [!! Saticida disk "SALT OKUNUR" idi — bu satira birebir uyuyor]
- "Reports raw controller name (... MAP1602)" -> ROM kimligi, firmware yuklenmemis
### M.2 NVMe acilis el sikismasi (osiloskopla, ama mantigi bize lazim)
1. 3.3V ray monotonik yukselmeli
2. PMIC PWR_EN -> 1.8V, 1.2V, core sirali kalkar. 3.3V var ama PWR_EN yok = PMIC'in kendisi
3. 100 MHz REFCLK PERST# birakilmadan >=100 us once kararli olmali (T_PERST#-CLK).
   "REFCLK yoksa sorun host root complex'tedir, SSD'de degil."
4. PERST# (M.2 pin 50) host tarafindan; T_PVPERL >= 100 ms
5. **"PERST# birakildiktan sonra kontrolcunun LTSSM link training'e baslamak icin 20 ms'i var.
   Link training HIC baslamiyorsa kontrolcunun BOOT ROM'u takilmistir; basliyor sonra
   cokuyorsa firmware yuklenmis ama PANIK etmistir. Ustteki NVMe katmani CSTS.RDY=1'i
   HIC set etmez ve cihaz BIOS enumerasyonundan kaybolur."**
   [!! BIZDE link training TAM basariyla bitiyor (Gen3 x4) -> boot ROM calisti, saatler calisti
       -> "firmware yuklendi ama panik etti" satiri]
### NAND veri tutma
"NAND hucreleri gucsuz aylarca-yillarca sarj tutar (**JEDEC tuketici SSD'leri 30 °C'de
 52 hafta gucsuz tutma** icin derecelendirir)."
### Catlak MLCC
"PCB bukulmesinden ya da surge'den catlayan MLCC'ler ic elektrot katmanlarini
 kopruler ve bypass dugumunde **tam kisa devre** okur. Bu ariza multimetrede GURULTULUDUR."
 (Tantal polimer ise sessizdir — ama bizim kartta tantal yok.)

## BULGU 9 — fzabkar (hddguru elektronik uzmani) olcum metodu [UZMAN GORUSU]
https://forum.hddguru.com/viewtopic.php?f=10&t=30547 (SanDisk X100, 2015)
"L1, L2, L3 bobinleri 3 anahtarlamali regulator oldugunu gosteriyor. Kontrolcu Vcore ve Vio
 ister. NAND dizisi 3.3V'ten beslenir sanirim. **C33/C34, C21/C22 ve C3 uzerinden gerilim
 olcerdim — bunlar her regulatorun cikis gerilimleridir.**"
Ayni konuda: "Vcore (1.1V) ve Vio (1.8V, 3.3V) beslemeleri iyi gorunuyor."
=> Test noktasi olmayan kartta OLCUM NOKTASI = her bobinin yanindaki cikis kondansatorunun
   iki ucu (ya da bobinin kendi iki ucu).

## BULGU 10 — Ev sartlarinda reflow: gercek bir basari vakasi [SOMUT VAKA]
XNL Future Technologies, "Dead M.2 SSD Data Recovery (Simple reflow solution)"
https://youtu.be/TPRKxfU3kuk (15k izlenme)
- "Bir M.2 SSD'den veriyi **sadece bir sicak hava istasyonuyla**, cok basit bir reflow
  cozumuyle kurtardim."
- "Bu SORUNU COK KEZ gordum" — sadece M.2 degil SATA/mSATA'da da; ama en cok M.2'de.
  Tahmini nedenler: kotu lehim kalitesi, M.2'nin fazla gerilimle monte edilmesi,
  ve/veya sogutucusuzluktan asiri isinma (BGA'nin sik isinip sogumasi).
- **On isitma (preheat) yapmadi**: "boyle kucuk bir kart icin bence boyle yapmak sorun degil.
  Zaten sadece **GECICI bir 'yara bandi'**, veriyi kurtarmak icin."
- Sicak hava istasyonu fiyati: "artik 60-80 dolara epey iyisi alinabiliyor."
- **"Bu sekilde sorun yasamis bir SSD'ye ben artik hicbir veri icin guvenmem."**
- "NAND cipleriyle ugrasmaktan %100 emin degilsen dokunma. Ya da daha iyisi: yedegi olmayan
  onemli veri varsa hic denemeye kalkma."
- Videoda kart uc klipsle, komponentlere basmayan noktalardan sabitleniyor (03:45, 04:03).

## BULGU 11 — "Busy / undetected SSD" + soguk lehim baglantisi [UZMAN GORUSU]
Dolphin Data Lab (profesyonel veri kurtarma ekipmani ureticisi):
"How To Fix Busy Undetected SSD Due To Cold Poor Soldering" https://youtu.be/276d9r14GlA
=> "BSY + taninmiyor" tablosunun soguk/kotu lehimden gelebilecegi profesyonelce kabul ediliyor.

## BULGU 12 — MAP1202 tamir ekosistemi (2026 itibariyla)
- PC-3000 SSD: MAP1202/1602/1602A DESTEKLENMIYOR (ACELab listesinde yok).
  Rossmann bu kontrolculere firmware kurtarma HIZMETI VERMIYOR.
- Northwind (northwind.gr): MAS0902/MAS1102 icin cozum var, %70; MAP icin yok.
- MPTool (acma/量产) MAP1202 icin VAR — 量产部落 (liangchanbuluo) uzerinden, uyeliğe/odemeye tabi;
  NAND process'ine gore ayri surumler (or. "Maxio MAP1202 MP/Sorting Tool C.0.01.009d_YMTC X2-9060").
  usbdev'de JenDos_50 ayni tip diski MPTool ile yeniden hayata dondurdu (400 GB'a kirparak).
- **MPTool VERIYI YOK EDER.** Rossmann: "panik durumdaki bir surucude MPTool calistirmak
  sistem alanini yeniden yazar, FTL'i sifirlar, NAND'a taze format atar — kurtarilamaz."
- usbdev DarwinLudwig (moderator/uzman): "maxio'da tek buyuk zorluk hafiza degisimi icin
  GPIO strap secimi; uygun arac varsa gerisi trivial."

## SENTEZ

### Kristal/PLL hipotezinin ZAYIF olmasinin nedenleri
1. Kontrolcunun boot ROM'u calisiyor: PERST# birakildiktan sonra 20 ms icinde LTSSM
   baslamasi ve Gen3 x4 TAM egitim = cekirdek saat var. (Rossmann, handshake)
2. Config space register'lari (CAP/VS/CC/CSTS) tutarli degerler donuyor = register blogu
   saatleniyor, CAP decode'u anlamli (MQES=1023, CSS=NVM, MPS 4K-16K, NVMe 1.4.0).
3. LED yanip sonuyor = firmware DAS/DSS'i (M.2 pin 10) surmeye devam ediyor.
4. usbdev'in AYNI kontrolcudeki UART logu, basarisiz acilista bile DDR:1200, Dual CPU Run,
   LDPC init, NAND ID okuma, bad-block tarama gosteriyor -> saatler tamam; takilma noktasi
   [QBT]/[PBT] = sistem tablosu okuma; [SD-Rslt: ffff] = NAND'dan hep 1'ler.
   "CLK:550,475,137" satiri GEC asamada basiliyor; yoklugu "kristal yok" demek DEGIL.
5. Rossmann'in triyaj tablosu "clock crystal"i "HIC enumerate etmeyen + soguk" satirina koyuyor.
6. Kartta kristal arizasi diye belgelenmis vakalar (Zero Alpha) FIZIKSEL HASARLI ve
   cihaz TAMAMEN olu; "bazen calisiyor" degil.

### Kristal hipotezinin AYAKTA KALAN tek versiyonu
Kristal calisiyor ama FREKANSI/kararliligi marjinal -> NAND arayuz zamanlamasi ihlal ediliyor
-> NAND okumalari basarisiz. Ama bu genelde COP/ECC hatasi verir; surekli 0xFFFF vermez.
Ayrica marjinal kristal PCIe'yi etkilemez (PCIe host REFCLK'ini kullanir) — bu, hipotezin
"aciklama gucu" gorunumunu yaratan sey; fakat ayni tabloyu NAND rayi / NAND retention /
FTL bozulmasi da aciklıyor ve onlarin BELGELENMIS taban orani cok daha yuksek.

### Daha guclu 3 alternatif (siralamayla)
A) **Firmware/FTL panic + sistem alani NAND retention kaybi** (en guclu)
   - Saticida zaten "SALT OKUNUR" idi = firmware kendini koruma kilidi (Rossmann matrisi)
   - Uzun sure enerjisiz kaldi (JEDEC: 30 °C'de 52 hafta)
   - MAP1202'nin BILINEN imzasi: "FTL corruption, HMB loss after power cut"
   - "Bazen aciliyor" = marjinal LDPC/read-retry: bazen yakinsiyor bazen yakinsamiyor
   - CAP.TO = 127,5 s = firmware'in kendisi cok uzun boot suresi beyan ediyor
B) **BGA mikro-catlak (kargo darbesi / termal cevrim)**
   - Rossmann: "disk tamamen olmeden once ARALIKLI CALISABILIR"; flex testi kesin kriter
C) **NAND besleme rayi (VCC_NAND / VCCQ_NAND) marjinal, ya da catlak MLCC**
   - Rossmann: VCC_NAND olu -> "ROM boot eder, firmware yuklemeye calisir, her NAND okumasi
     1'ler dondugu icin takilir" — bizim tabloya birebir
