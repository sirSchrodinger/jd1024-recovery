# HYV6 / SKV6 — Rus & Doğu-Avrupa kaynak taraması (ham notlar)

Tarih: 2026-09-11/12. Ortam: T440 yerel. Hicbir donanima dokunulmadi.
ARAC NOTU: WebSearch kotasi (200/200) bu oturumda TUKENMISTI. Tum arama
dogrudan curl + WebFetch ile, site-ici gezinme (sitemap, board crawl) uzerinden yapildi.
Google/Bing/DDG/Mojeek/searx/Yandex/Startpage/Brave => hepsi captcha/403/429 verdi (asagida liste).

---------------------------------------------------------------------------
## 1. EN ONEMLI BULGU — usbdev forumunda AYNI SORU, MART 2026

URL: https://www.usbdev.ru/f/index.php?topic=13429.0
Baslik: "MAP1202 HYV6 (hynix6) — ищу MPTool/прошивку"
Yazar: angelmxycry, 01 Mart 2026 00:03:24
Cihaz: Fanxiang NVMe 256 GB, MAP1202 + SK hynix V6 / HYV6, ROM mode.

Alinti (orijinal):
> Для HYV6, похоже, есть отдельный комплект, но он пока не опубликован:
> Maxio MAP1202 MP/Sorting Tool: C.0.01018_HYV6
> https://club.liangchanba.com/thread-1761-1-1.html
> Файлы прошивки: ZI0PCABC, ZI0PCADC, ZI0PCD2C, ZI0PCPDLC
> Serial: SN09466
> Статус: «к публикации / ещё не открыт»
> Разница по именам прошивок:
> HYV7: YI + QZ (например YIQZCADC.bin)
> HYV6: ZI + 0P (например ZI0PCADC.bin)

TR: HYV6 icin ayri bir paket VAR ama yayinlanmamis: **C.0.01018_HYV6**, SN09466,
SYS binary'leri **ZI0PCABC / ZI0PCADC / ZI0PCD2C / ZI0PC(D)LC**.
Isim kurali: HYV7 = YIQZ*, HYV6 = ZI0P*.

CEVAP — hardmaster (Global Moderator, "ЭКСПЕРТ", 997 mesaj), 02 Mart 2026 11:25:03:
> Этой прошивки нет даже у китайцев за деньги.
> У нас то откуда?
TR: "Bu firmware Cinlilerde bile PARAYLA yok. Bizde nereden olsun?"

=> Bu, "paket halka acik degil" iddiasinin en yetkili tek cumlelik kaniti.

---------------------------------------------------------------------------
## 2. AYNI NAND'IN SAGLAM IKIZI — dogrulanmis HYV6 firmware kimligi

URL: https://www.usbdev.ru/f/index.php?topic=13552.0
Baslik: "KingSpec NX-256 SN8878 MAP1202 H25BFT8A1BDA" — magnitnyi_yozh, 08 Nisan 2026
maxio_nvme_fid ciktisi (calisan ikiz diskten):

    Fw      : SN8878
    Firmware id string[1C0] : MKSSD_501003000088780000,Apr 26 2022,21:25:49,MAP1202,ZI0PCADC
    Project id string[180]  : r:/hynix_v6_8878
    Controller  : MAP1202
    NAND string : H25BFT8A1BDA
    Ch*CE*: 0xad,0x7e,0x28,0x53,0x2,0xb0,0x0 - Hynix 3dv6-128L TLC 16k 512Gb/CE 512Gb/die

ONEMLI: Alperen'in diski AD 7E **29** 53 02 B0; burada AD 7E **28** 53 02 B0.
Ayni aile (3dv6-128L TLC, 512Gbit/die, 0xB0 = V6), byte3 farki paket/die sayisi varyanti.
=> HYV6 branch'inin gercek adi **hynix_v6_8878**, SYS binary **ZI0PCADC**, FW etiketi **SN8878**.
   (angelmxycry'nin bahsettigi C.0.01018_HYV6 ise SN09466 — daha yeni bir revizyon.)
Konu cozumsuz kapandi (Secure Erase onerildi, ise yaramadi).

---------------------------------------------------------------------------
## 3. usbdev.ru MAP1202 paket listesi — SKV6 YOK (dogrulandi)

Sayfa: https://www.usbdev.ru/files/maxio/map1202mpsortingtool/
19 paket. Nesiller: B37R, B47R, WD_BICS5, YMTC_JGS/X2_9060, HYV7 (C.0.01.017 SN09286),
N38B, N4PA, HYV8 (C.1.1.26 SN26637 = MAP1202_H25TXTD2XCX6.rar 3 627 774 B).
Sayfanin kendi bin listesinde ZI0P* ile baslayan HICBIR dosya yok
(sadece ZIC5CB5C.bin var, o V6 degil).
=> Alperen'in elindeki 19 paket = usbdev'in tam listesi. Eksik olan gercekten yok.

Indirme linkleri WP-Filebase: https://www.usbdev.ru/?wpfb_dl=<id>
 (orn. HYV7 = dl=11155, HYV8 = MAP1202_H25TXTD2XCX6.rar)

---------------------------------------------------------------------------
## 4. Baktigim diger Maxio sayfalari (SKV6 yok)

- /files/maxio/map1602mptool/     : B58R, N58R, X2-9060, X3-9060, X3-9070. Hynix yok.
- /files/maxio/mxutilitymap1202/  : sadece MXUtility v0.02..v1.11 (firmware yok)
- /files/maxio/mxutilitymap1602/, /mxutilitymap160x/ : MXUtility
- /files/maxio/mas1102mptool/     : B17A,B37R,B47R,N28A,N38A,YMTC*,**SSV6**(=Samsung, Hynix DEGIL)
- /files/maxio/map100xmpsortingtool/ : B16A,B17A,JGS2
- /files/maxio/ (kategori indeksi)  : sitenin WordPress'i 500 veriyor (kirik)
- usbdev WordPress arama (?s=SKV6)  : HTTP 500, arama fonksiyonu bozuk
- usbdev SMF forum aramasi          : misafire kapali (403 "Вы не можете зайти в этот раздел")

---------------------------------------------------------------------------
## 5. usbdev forum — Maxio board (board=21) TAM tarama

10 sayfa, 236 konu indirildi ve gruplandi. V6/SKV6/3dv6/ZI0P gecen SADECE 6 konu:
- 13429 MAP1202 HYV6 — yukarida (paket yok)
- 13552 KingSpec NX-256 H25BFT8A1BDA — yukarida (calisan ikizin FW kimligi)
- 12504 "MAS1102 Hynix 3DV6 нужна прошивка" (10 Mart 2025, vrtheworld)
        Flash ID 0xAD,0x5E,0x28,0x53,0x02,0xB0 — QI#FCV2C.bin isteniyor. SIFIR cevap.
- 13389 SK Hynix H25JGT883MDA
- 13816 / 10960 / 13562 — teget
=> Rusca dunyada MAP1202+HYV6 icin tek bir paylasim/ipucu bile yok.

---------------------------------------------------------------------------
## 6. TASK 2 — "YANLIS NESIL FIRMWARE ILE ZORLA YAZMA" — SOMUT VAKALAR

### Vaka A — HYV7-QLC: arac taniyor, dosya yok, ZORLAMA CALISMIYOR
https://www.usbdev.ru/f/index.php?topic=13572.0
"Нужна прошивка или файлы для связки MAP1202 + Hynix V7 QLC" (Gafus, 16 Nis 2026)

Gate007, 31 Mayis 2026 — iki paketi de denemis:
> 0xAD 0x89 0x2C 0x1B 0x30 0xC0 - Hynix 3dv7-176L QLC 16k 1024Gb/CE
> Испробовано:
> HYV7-SN09286 - не может определить мою память вообще
> HYV8-SN26637 - видит мою память, но ему не хватает файлов:
> \SKV7\002_600\nandmem_SKV7_page.bin
> \MPT\SYS\YIM3CA3H.bin
TR: HYV7 paketi NAND'i hic tanimiyor; HYV8 paketi taniyor ama
    DAT/SKV7/.../nandmem_SKV7_page.bin ve SYS/YIM3CA3H.bin eksik.
=> Alperen'in durumunun BIREBIR ayni yapisal formu (arac taniyor, FW paketi eksik).

DarwinLudwig (Global Moderator, EXPERT), 31 Tem 2026:
> ессесна нет, под hyv7q нужна специальная прошивка
> MAP1202-HYV7Q-C1.1.27-256GB-2TB-GT975FCK
> sys бинари: AIM3CA1H.bin - 4H
TR: "Tabii ki hayir — hyv7q icin OZEL firmware lazim."
DarwinLudwig, 09 Agu 2026:
> Ну, много китайских заводов ей обладают, но просто так не выудить
TR: "Bircok Cin fabrikasinda var ama oylece cekip alinmiyor."
=> Nesil/tip atlamasi icin "esdeger paket" yok; spesifik paket sart.

### Vaka B — SYS binary'sini YENIDEN ADLANDIRIP zorlama => sadece FAIL
https://www.usbdev.ru/f/index.php?topic=13445.0
"MAXIO MAP1202 + Sandisk BIC505015" (old-boy77, ADATA Legend 750 500GB)

old-boy77, 11 Mart 2026 12:35:
> И ещё просит в папке SYS прошивку с именем YN6TCDJC.bin, но я с таким именем
> не нашёл ни где, по этому подсовывал похожие переименнованные,
> но результат на всех один и тот же.
TR: "SYS klasorunde YN6TCDJC.bin istiyor, hicbir yerde bulamadim, bu yuzden
     BENZERLERINI YENIDEN ADLANDIRIP verdim — hepsinde sonuc ayni."
Sonuc: hep "(p35) check calibration fail" / "(p24) sorting result fail".
Disk bricklenmedi; ROM mode'da kaldi (generic loader nvme device olarak gorunuyor).
=> Yanlis SYS bin zorlamasi: kalici hasar yok, sadece kalibrasyon/sorting asamasinda dusuyor.

### Vaka C — "neredeyse ayni" NAND kaydi secmek: kirmizi bar, ama toparlandi
Ayni konu, DMleon #18 (11 Mart 2026):
> в кучи программ скачанных я не находил свою память в списках и подставлял
> почти похожую, только в одной цифре не совпадения было, то же всякие ошибки
> лезли, прошивка проходила в красную полосу, что означает что с ошибкой
> прошилась ... я решил просто авто детект сделать зайти в настройки IDEMA
> и сменить с 128 на 120 нажать сет а потом нажал старт и тогда успешно прошилось
TR: Listede kendi NAND'i yoktu, TEK HANE farkli olani secti; hatalar cikti,
    yazim "kirmizi bar" ile hatali bitti; disk olmedi, IDEMA kapasitesini
    duzeltince ayni araclarla basarili yazdi.
=> Yanlis kayitla yazmak NAND'i oldurmedi; islem basarisiz oldu, tekrar denenebildi.

### Vaka D — Farkli paketin loader'ini KASITLI kullanma (calisan tarif)
Ayni konu, DMleon #21 — alintiladigi standart tarif:
> С usbdev берём недавно появившийся тул для B47R
> (MAS1102-B47R-D2.1-V2.000.020-D.0.01.005e-SN12980-Normal.rar),
> служебный лоадер в его составе умеет работать с N48R ...
> выбор ... критического значения не имеет, т.к. новая прошивка в диск не
> загружается, по этому можно выбрать "TMC_ARRAY_Default" ...
> в списке тестов отключаем Download ... Preformat Mode = Inherit FW BB
TR: B47R paketinin SERVIS LOADER'i N48R bellekle calisiyor; TMC/timing secimi
    kritik degil CUNKU **Download kapatiliyor** (diske yeni FW yazilmiyor),
    sadece Preformat + Inherit FW BB yapiliyor.
=> "Yabanci paketle" guvenli kullanim bicimi budur: Download OFF.
   Yani zorlama, NAND'a program/erase voltaji uygulayan asamayi devre disi
   birakarak yapiliyor — rastgele timing ile yazmak degil.

### Vaka E — Kapasite/die ID'sini ELLE degistirip yazma: BASARILI (ayni nesil)
https://www.usbdev.ru/files/maxio/map1202mpsortingtool/ yorumlari, "Димка", 17 Oca 2026:
> Оживил HVY7 прошивкой SSD Reletech на 2ТБ. Правда вот прошивки под обьем
> на 2ТБ нет, пришлось изменить айди чипа и его DIE и лить 1ТБ.
> Все работает, тесты проходит.
TR: 2TB Reletech'i canlandirdi; 2TB icin paket yok, **cip ID'sini ve DIE sayisini
    degistirip 1TB firmware'ini yazdi**. "Her sey calisiyor, testleri geciyor."
=> ID/DIE elle degistirme AYNI NESIL icinde calisiyor.

### Vaka F — Yanlis/eksik TIMING (TMC) dosyasi takviyesi => sadece hata, hasar yok
https://www.usbdev.ru/f/index.php?topic=13886.0  (megrottv, 30 Tem 2026)
"MAS1102 (N28A-C2.1) — ошибка TIMING_SETTING_TYPE_0003300 is not exist"
Kullanici, MPT\TMC\...\TMC_LGC dosyasinin 5 KB (bozuk/kirpik) oldugunu,
RDT\TMC\... altindaki AYNI ISIMLI dosyanin 101 KB oldugunu bulup
**buyuk olani kucugun uzerine kopyalamis**. Auto Detect duzelmis,
ama Start Flash'ta ayni TIMING_SETTING_TYPE hatasi geri gelmis.
Ayrica manuel olarak SDPx2-Micron-266MHz timing profilini secmesi yeni hata uretmis.
=> Timing dosyasini elle degistirmek: aracin ic tutarlilik kontrolune takiliyor.
   Disk olmedi, tekrar tekrar denendi.

### Vaka G — Uzman kurali: "firmware var" != "uyar"
https://www.usbdev.ru/f/index.php?topic=13562.0 — Nayhel (EXPERT, 958 mesaj), 11 Nis 2026:
> То что прошивка есть не значит что подойдет. Соберите тестовый SSD и проверьте
> подойдут ли бинарники из папки SYS. ... В Flash.ini нет памяти с
> идентификаторами 98 3e 98 03 76 e4.
TR: "Firmware'in var olmasi uyacagi anlamina gelmez. TEST SSD'si kurup SYS
     klasorundeki binary'lerin uyup uymadigina bak."
=> Uzman tavsiyesi: denemeyi KURBAN diskte yap, Flash.ini kaydi yoksa zorlama.

### Vaka H — MAS1102 + Hynix V8: "prosivka yok" (nesil bazli kesin ret)
https://www.usbdev.ru/f/index.php?topic=13617.0 — hardmaster, 04 May 2026:
> Hynix V8 прошивок нет.
Kullanici: "Flash.ini Hynix modelleri iceriyor ama benimki yok" (H25T1TC48CX490)
=> Flash.ini'de kayit olmasi bile yetmiyor; SYS binary'si olmadan is bitmiyor.

---------------------------------------------------------------------------
## 7. Baktigim ama SONUC VERMEYEN yerler

- www.usbdev.ru/files/maxio/* (tum Maxio sayfalari) — SKV6 yok
- www.usbdev.ru/f/ (SMF forum) board=21 236 konu tam tarama — sadece yukaridaki 6
- www.usbdev.ru/f/ board=9 ("Добавления новых файлов") konu listesi — MAP1202 basliklari
  var ama N38B/N38A ve genel; HYV6 yok
- usbdev WP arama + SMF arama: ikisi de erisilemez (500 / 403-misafir yasak)
- vlo.name:3000 (HFS dosya sunucusu, vlo = maxio_nvme_fid yazari)
  /ssdtool/ : sadece TESHIS araclari (Maxio nvme flash id vb.), MPTool/firmware YOK
  /hw/, /chipsets/, /tmph/ : alakasiz
- GitHub kod aramasi (gh api search/code, kimlik dogrulanmis):
  "SKV606412" -> 2 sonuc, "SKV6064" -> 3, "H25BFT8A1BDA" -> 2
  HEPSI sadece iTXTech/fdfdb (ma/map1202_43.ini, ma/map1602_44.ini, ma/mas1102_16.ini)
  "ZI0PCADC" -> 0 sonuc; "hynix_v6_8878" -> 0 sonuc
  => GitHub'da HYV6 firmware/paket izi YOK.
- flashboot.ru — /files/maxio/ 301, ayri URL semasi
- Arama motorlari: Google(kota bitti), Bing/DDG/Brave/Mojeek/Startpage/Yandex/
  searx.be/baresearch/priv.au/searxng.site/opnxng/inetol => captcha, 403, 429 veya
  JS-challenge. Bu yuzden tum tarama site-ici gezinme ile yapildi.

---------------------------------------------------------------------------
## 8. EK BULGULAR (ikinci tur)

### 8.1 liangchanba (angelmxycry'nin verdigi kaynak) — HYV6 BOLUMU YOK
https://club.liangchanba.com/thread-1761-1-1.html  ("Maxio MAP1202 MP/Sorting Tool")
Sayfa curl ile okunabiliyor (giris gerekmiyor, sadece 24 saatte 4 link limiti).
10 navigasyon basligi: HYV7, HYV8, B37R, B47R/B47T, WD_BICS5, YMTC X1-9050(JGS),
YMTC X2-9060(TAS), N38A, N38B, N4PA.  **HYV6 / ZI0P / C.0.01018 ham HTML'de 0 kez geciyor.**
Arsiv sifresi: `maxio`.
liangchanba'da usbdev'DE OLMAYAN MAP1202 paketleri var (ama hicbiri V6):
  C.0.01.020_HYV7 (SN09286) MAP1202-Hynix_V7-0x39-V0.01.020-128GB-1TB-SN9286-H220719b.rar
  C.0.01.003_B37R SN06051 · C.0.01.010_B47R SN10179 · B47T varyanti (2C,C3,08,32,EA,34)
  X2-9060 SN08327 / SN09273 / SN09843(add_1TB)_MOD · C2.1.29 SN11795 / SN14824
  (bircogu "1金币" + yildizli uyelik gerektiriyor)
=> hardmaster'in "Cinlilerde bile yok" sozu, Cin'in en buyuk 量产 sitesinde dogrulaniyor.

### 8.2 Diger indirme kaynaklari — HYV6 yok
- file.diyflash.top (RU forumda kaynak olarak verildi): toplam ~17 dosya.
  MAP1202 icin sadece: MAP1202_YMTC_JGS_SN6760.7z, MAP1202_N4PA_SN26904.zip, MAP1202+N38B-.7z
- github.com/dom0ng/map1202 : icinde `map1202too-unlocked.zip` (4 407 539 B) —
  Alperen'in elindekiyle AYNI dosya. README = seri no / model / FW versiyonu SPOOF rehberi
  (Test Items: Modify Serial/Model/FW Version/Device Settings). NAND flash'lama YOK.
- github.com/EEUUAA/MAP1202 : "added support for fresh YMTC nand's", tek commit
  "success flashing confirmed". Base = MXMPTool_MAP1202_USB_V0_01_009d.
  Flash.ini FlashIniVer=**033**. SYS: IQYOCE2C, JQYOCD2C, JQYOCDLC (JGS) +
  KRRHCE2C, MRRHCABC/CD2C/CDDC/CDLC/CELC (X2-9060). DAT/: JGS2, JGS3 timing klasorleri.
  **SKV6/HYV6 yok** (Flash.ini'de SKV5/SKV6 SATIRLARI var ama SYS bin ve DAT/SKV* klasoru YOK).
  => "Flash.ini satiri var, firmware yok" durumunun bir baska ornegi.

### 8.3 MPTOOL.ini'de gercekten `EnCheckFlashID` VAR (dogrulandi)
https://github.com/EEUUAA/MAP1202/blob/main/MPTOOL.ini
    EnCheckFlashID=1
    EnCheckTables=1 · EnCheckModuleCHCE=1 · EnCheckNandReset=0 · EnCheckLDPC=1
    EnCheckDataPath=1 · EnCheckSRAM=1 · EnCheckNandTime=0 · EnCheckDQS=0
    EnCheckDPDParam=1 · EnModifyDeviceSetting=0 · CheckFlashMask=63
`EnModifyFlashID` diye bir anahtar YOK (GitHub kod aramasi: 0 sonuc).
Flash.ini kayit formati dosyanin kendi basliginda TAM dokumante:
  UniName, FullName, Vendor, Type, CE/Package, Blocks/CE, PageNum, PageSize, Die/CE,
  ECC, ID0~ID5, ExtBlk/Die, DieOffset, PairPage, Interface, Plane, Endurance,
  **Nandmem**, SpareByte, **GpioSet(GPIO6,GPIO7,GPIO16)**
  - `Nandmem` = DAT/<GEN>/<xxx_yyy>/nandmem_<GEN>_page.bin secimi
  - `GpioSet` = KARTIN uzerindeki strap direncleriyle eslesmek ZORUNDA
Ornek SKV6 satirlari (FlashIniVer=033):
  Name003=SKV603001 H25JGT8A1M8R 3 2 1 5752 1536 16 1 2 0xAD 0x89 0x28 0x53 0x00 0xB0 ... 100
=> Elle satir eklemek MUMKUN ve format acik; ama satir sadece "hangi nandmem +
   hangi SYS bin" diye ISARET EDER. O dosyalar yoksa satir hicbir sey yaratmaz.

### 8.4 ★ MPTool ic yapisi + zorlamanin gercek sonucu — UZMAN ACIKLAMASI
DarwinLudwig (Global Moderator/EXPERT), 16 Haz 2026, "ССЫЛКИ КИДАТЬ СЮДА"
https://www.usbdev.ru/f/index.php?topic=2.0  (mesaj #94, sayfa .80)
> По сути как и любой мптул он устроен просто:
> База флеша с конфигами ..., **набор бинарей под конкретную память** и базовый набор бинарей.
> ...
> **Внаглую взять от другого контроллера приведет к ошибке в виде "isp fail".**
> **Некорректный порт в .dat приведет к глюку софтины и она всегда будет писать noflash**
> **Некорректный импорт бинарей приводит к ошибке которая напишет что он тупо не нашел
>  папочку с именем папки которая прописана в конфиге**
> **В самих бинарях С-шные скомпилленные процедуры для работы с конкретной памятью и всего-то**
> ... чем больше новых тулов всплывёт тем больше новых тулов можно будет **собрать из кусков**,
> как например b57t, hyv8 для 95n/ht
TR OZET:
 - NAND'a ozel bin = O BELLEK ICIN DERLENMIS C KODU. Baska bir seyle degistirilemez.
 - Baska controller'dan zorla almak => "isp fail"
 - .dat'ta yanlis port => yazilim "noflash" der, takilir
 - Yanlis binary import => "config'te yazan klasoru bulamadim" hatasi
 => HEPSI YAZILIM HATASI. Hicbirinde "NAND yandi/bozuldu" YOK.
 => Ayrica: paketleri "parcalardan birlestirmek" (собрать из кусков) YERLESIK BIR PRATIK —
    ama ancak o parcalar BASKA BIR PAKETTE MEVCUTSA.

### 8.5 ★★ AYNI NESIL (Hynix 3dv6-128L, 0xB0) NAND'da BASARILI "yanlis profille" yazma
https://www.usbdev.ru/f/index.php?topic=11478.0
"Не прошло и полгода мучений PS3111+Hynix 3dv6-128L" — dmitry7020, 12 Eyl 2023
Controller: Phison PS3111 (SATA), NAND: 0xad,0x5e,0x28,0x53,0x2,0xb0 = Hynix 3dv6-128L TLC
16k 512Gb/CE 512Gb/die  (Alperen'inkiyle AYNI NESIL, ayni 0xB0)
> ...так и не получилось с HYNIX, ничего корректно не работало ... взял основу сначала
> 2258 - не пошло ... в базе на сайте нашем 1 вроде должна, но не пошла ...
> а потом думаю дай с MPTOOL возьму ту что определяла эту память,
> **создал через (toshiba) прошивку по параметрам описанным подходит**.
> Вот в итоге запаяв 2 банки памяти по 500 гигов ... получил 1тб винт.
> **Прошивку взял SBFQX1.3.bin из MPTOOL.** Я был в шоке.
> SBFMX1.2_11062021.BIN из базы и многие другие не канают
TR: 6 ay ugrasti; hazir Hynix profilleri calismadi; sonunda **TOSHIBA girdisinden,
    parametreleri eslesen bir profil olusturdu** ve baska bir FW bin'i (SBFQX1.3) kullandi
    => 1TB disk calisti, tam hiz.
Uyarisi: "format sirasinda 300-350 hiz gorursen beladan kork, bank'larda sorun var."
=> Phison'da "vendor kimligi degil PARAMETRE eslesmesi" onemli; zorlama CALISTI.
   (MAP1202'de ayni sey gecerli DEGIL cunku SYS bin'i derlenmis NAND-ozel koddur — bkz 8.4)

### 8.6 ★ MAP1202'de dosya adlarini yeniden adlandirip zorlama: KISMEN CALISTI
https://www.usbdev.ru/f/index.php?topic=12338.0 ("Maxio MAP1202 изучение, прошивки, особенности")
JenDos_50, 21 Sub 2026 (#12) — Apacer 1TB, MAP1202 + Intel N38A QLC (o zaman public tool yoktu):
> Попался точно такой же. **Переименовал всё в N38A + определился KC1UCA3H тоже исправил.**
> После прошивки отвалился на 390gb, прошил sort барабанил ~9 часов.
> Прошил Inherit RDT + Sort, заткнулся на 450gb. Оставил 400gb. Пока пашет.
> Видимо флэшь полное г... под конец скорость скачет.
TR: "Her seyi N38A'ya YENIDEN ADLANDIRDIM, KC1UCA3H olarak algilandi, onu da duzelttim.
     Yazimdan sonra 390GB'da dustu; SORT 9 saat dondu; Inherit RDT+Sort ile 450GB'da tikandi.
     400GB'a birakip biraktim. Simdilik calisiyor."
=> Zorlama disk oldurmedi; 1TB yerine 400GB'lik CALISAN disk verdi.

### 8.7 ★ Elle "birlestirilmis" paketle yazma: PASS aliyor, sonra AGIR YAZIMDA COKUYOR
https://www.usbdev.ru/f/index.php?topic=13304.0 ("Maxio MAP1202 MPSortingTool N38B N38A")
fayer2356, 30 Oca 2026:
> Моя **модернизированная утилита** для N38A на базе прошивки выше. Помогла оживить Apacer 1TB
  (kaynak: https://file.diyflash.top/ , paylasim: disk.yandex.ru/d/na18EUL3Y9ssPw)
dimiknik, 31 Oca 2026: "Прошился без проблем" ... sonra:
> У меня где-то на **310-320гб тормоза и отвал в финале. прошивка слетала.**
> Ставил винду норм, Кристалом тест - то норм, то заниженная ... но **слет прошивки
> наблюдался при записи больших файлов**
fayer2356: > Да, тоже самое ... поэтому пока прошивку убрал. Значит **дело именно в прошивке**.
Nayhel (EXPERT) ayni desen: YS9085N + N38B — "шьются, но после заполнения SLC и начала записи
в QLC, SSD перестает определяться после переподключения питания."
=> Uydurma/karma config'in TIPIK arizasi: MPTool PASS verir, disk acilir, kisa testleri
   gecer, sonra SLC cache dolunca / buyuk yazimda firmware ucar. Fiziksel olum degil,
   ama VERI GUVENLIGI YOK.

### 8.8 Ek dogrulama noktalari
- ZaFFer, 05 Agu 2026, https://www.usbdev.ru/f/index.php?topic=13814.0 :
  "поддержка памяти есть но прошивки не все в доступе а **без доступного конфига
   не поможет ничего другого**"
- DarwinLudwig, 19 Tem 2026 (topic 12338 #14): "единственная великая сложность в maxio -
  подбор gpio для пересадки памяти ... больше ничего нет сложного, **если есть у вас
  совместимый инструмент**. точка."
- DarwinLudwig, 18 Haz 2026 (topic 13572 #13): NAND gorulmuyorsa
  "можно один страп сместить, вычистить его eraseall, а потом вернуть обратно"
- SMI tarafinda HYV6 paketleri VAR (Maxio'da yok):
  usbdev /files/smi/sm2258xtmptool/ icinde `SM2258XT(AD)_Support_some_HYNV6.rar`
  ve `SM2258XTAD_HYV6_PKGU0406A_FWU0326A0` — baska controller, MAP1202'ye uymaz.
- roman2013 (topic 12338): MAP1202'nin ic prosivkasini blok blok okudu; UART log'u aldi.
  Diski cift Secure Erase denemesinden sonra "sdoh" (oldu). vlo: "gdp yukleyip olu diskten
  bloklari okuyabilirsin". Prosivkayi bloklardan geri toplamak DENENDI ve OLMADI
  ("Собрать прошивку пробовал, не получилось" — 4K header formati bilinmiyor).

---------------------------------------------------------------------------
## 9. TEK GERCEK EDINME YOLU (bulunan en somut kanal)

DarwinLudwig — usbdev Global Moderator, "Рекламирую свои услуги"
https://www.usbdev.ru/f/index.php?topic=13782.0   (son duzenleme 09 Eylul 2026)
Hizmet: MPTool ve benzeri yazilim modifikasyonu. Odeme YA DA takas
("либо прямая оплата, либо обмен на иное ПО которого нет у меня/в открытом доступе").
Yaptiklari arasinda: lisans anahtari kontrolunu kapatma, program mantigini degistirme,
gizli fonksiyonlari acma, sifreli/sikistirilmis dosyalari plaintext'e cozup geri yazma
(yeestor, ffw, phison, marvell).

Ilan ettigi "elimde var, takasla verebilirim" listesinde:
> ALLFLASH:
> MAP1202
> MAP1602a
> MAP1608
("ALLFLASH" = tum NAND tiplerini destekleyen birlestirilmis build)
Ayrica "У меня можно также получить MPTOOLS 2023 – 2025."

Ayni ilanda ✔ ПОЛУЧЕНО (edinildi) isaretlileri:
> HYV6 / HYV7 **MAS1102** MPTool sort+fw — ✔ ПОЛУЧЕНО
> N48R **MAP1202** MPTool sort+fw — получено, но данный инструмент **не может быть
>   распространён без последствий — не спрашивайте**
=> HYV6 Maxio paketleri OZEL ellerde DOLASIYOR; MAS1102 (SATA) tarafi onda var.
   MAP1202 HYV6 icin acik bir "var" beyani yok, ama "ALLFLASH MAP1202" iddiasi var.

Ayrica 09 Eyl 2026 (#3):
> успешно собран N4PA из **обновлятора** и мптул для N38A
TR: "N4PA, bir FIRMWARE UPDATER'dan + N38A MPTool'undan basariyla BIRLESTIRILDI."
=> ★ Yeni bir yol: retail FIRMWARE UPDATER icinden NAND-ozel .bin cekip komsu
   nesil MPTool'una monte etmek. Basarili ornegi var.

### 9.1 Updater yolu — public MAP1202 updater'larinda HYV6 YOK (kontrol edildi)
- /files/maxio/adatalegend750fwupdate/ -> SVN9902 (WD_BICS5) / SVN9954 (B47R) / SVN9843 (YMTC)
  ADATA_LEGEND750_FWUpdater_SVN9902_SVN9954_SVN9843.rar (8 416 201 B)
- /files/maxio/tiplus5000updatetool/ -> YMTC, SVN7151/ZTA08322 -> ZTA09139
- /files/maxio/zhitaitiplus5000smarttool/ -> ZTA10613 (KRRHCE2C/MRRHCD2C/MRRHCDLC) = YMTC
- /files/maxio/vipervp4300l1tbupdatetool/ -> MAP1602, Micron
- /files/maxio/historssdupdatefwutility/ -> MAS0902
=> ARANMASI GEREKEN: HYV6 tabanli bir perakende SSD'nin resmi FW updater'i
   (KingSpec NX serisi SN8878, Fanxiang, JamesDonkey). Icinde ZI0PCADC.bin / ZI0PCA*.bin
   olma ihtimali yuksek. Bunlarin hicbiri usbdev'de yok.

---------------------------------------------------------------------------
## 10. TASK 2 — NET SONUC (kanitlarla)

S1: V7/V8 paketiyle V6 NAND'a ZORLA yazilabilir mi?
CEVAP: HAYIR — ve zaten "zorlamaya" bile sira gelmiyor. Arac, NAND'i tanidiktan sonra
DAT/SKV6/<timing>/nandmem_SKV6_page.bin + SYS/ZI0PC*.bin dosyalarini ISIMLE arar,
bulamayinca durur (Gate007'nin HYV8-vs-V7Q vakasi, topic 13572).
EnCheckFlashID=0 yapmak sadece ID dogrulamasini atlar; eksik dosyayi yaratmaz.

S2: Flash.ini'ye elle satir eklemek ise yarar mi?
CEVAP: Satir eklemek teknik olarak kolay (format dokumante), AMA satir sadece
nandmem klasorunu + SYS bin'i + GpioSet'i ISARET EDER. Uc sart:
 (a) DAT/SKV6/... timing dosyasi VAR OLMALI
 (b) SYS/ZI0PC*.bin VAR OLMALI — ve bu bin **o NAND icin derlenmis C kodudur**
     (DarwinLudwig: "В самих бинарях С-шные скомпилленные процедуры для работы
      с конкретной памятью") => baska nesilden bin ile ikame edilemez
 (c) Kartin GPIO strap direncleri satirdaki GpioSet ile eslesmeli
Uzman ozeti (ZaFFer): "без доступного конфига не поможет ничего другого."

S3: Yanlis nesil/isim ile zorlamak NAND'a KALICI ZARAR verir mi?
CEVAP: Toplanan hicbir vakada FIZIKSEL NAND HASARI YOK. Gozlenen sonuclar:
 - "isp fail" (baska controller'in binary'si) — DarwinLudwig
 - "noflash" (dat'ta yanlis port) — DarwinLudwig
 - "klasor bulunamadi" (yanlis binary import) — DarwinLudwig
 - "check calibration fail (p35)" / "sorting result fail (p24)" — old-boy77, topic 13445
 - "TIMING_SETTING_TYPE_xxx is not exist" — megrottv, topic 13886
 - kirmizi bar / hatali yazim, sonra tekrar deneme => sonunda basari — DMleon, topic 13445
Yani basarisizlik YAZILIM DUZEYINDE. Program/erase voltajlari NAND die'in KENDI
charge pump'lari tarafindan uretilir; MPTool ONFI/Toggle komutlari ve timing gonderir,
Vpgm'i set etmez. Bu yuzden "yanlis timing = asiri voltaj = yanmis hucre" senaryosunun
tek bir somut vakasini bulamadim.
 ⚠ TEK GERCEK FIZIKSEL RISK: MPTool'daki **Nand Voltage 2,5 V / 3,3 V** ayari.
   Bu VCCQ'yu degistirir ve autodetect ile DEGISMIYOR (topic 12627, 21street, 11 May 2025:
   "Странно, что при автодетекте эта настройка не изменяется").
   Yanlis pakette yanlis kalmis bir NAND Voltage, yanlis timing'den cok daha tehlikeli.

S4: Peki gercek risk ne?
CEVAP: SESSIZ VERI KAYBI. Uydurma/karma config'le yazilan disk PASS verir, acilir,
kisa testleri gecer — sonra SLC cache dolunca / buyuk yazimda firmware ucar
(topic 13304: 310-320 GB'da "прошивка слетала"; Nayhel'in YS9085N+N38B vakasi:
guc kesince disk kayboluyor). JenDos_50'nin vakasinda 1TB disk ancak 400GB'a
kirpilinca stabil oldu.
Uzman kurali (Nayhel, topic 13562): "Соберите тестовый SSD и проверьте подойдут ли
бинарники из папки SYS" — denemeyi KURBAN diskte yap.
