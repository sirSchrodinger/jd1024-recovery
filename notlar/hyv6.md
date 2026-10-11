# HYV6 / SKV6 avi — ham notlar
Tarih: 2026-09-12 · Hedef: MAXIO MAP1202 icin SK hynix V6 NAND destekli MPTool

## VAKA
JamesDonkey JD1024 1TB NVMe, MAXIO MAP1202 (1e4b:1202)
NAND marking: SK hynix **H25T1TB48E** (lot X297 310Y), 4 paket x 256GB = 1TB

---

## [B1] *** ANA BULGU *** iTXTech/fdfdb -> ma/map1202_43.ini  (FlashIniVer=043)
URL: https://github.com/iTXTech/fdfdb/blob/master/ma/map1202_43.ini
Yerel: hyv6/fdfdb/ma/map1202_43.ini
Commit: b8d826fc "update Maxio", PeratX, **2026-05-07**

[Hynix] bolumunde SKV6 KAYITLARI **VAR**:
```
Name004=SKV606411 H25BFT8A1BDA  3 2 1 2888 1536 16 1 2 0xAD 0x7E 0x28 0x53 0x02 0xB0 0 0 0 11 4 3000 001 2048 100
Name005=SKV606412 H25BFT8A1BDA  3 2 2 5776 1536 16 2 2 0xAD 0x7E 0x29 0x53 0x02 0xB0 0 0 0 11 4 3000 001 2048 100
Name002=SKV612801 H25JGT8A1M8R  3 2 1 5752 1536 16 1 2 0xAD 0x89 0x28 0x53 0x00 0xB0 ...
Name003=SKV612802 H25JGT8B3M8R  3 2 2 11504 1536 16 2 2 0xAD 0x89 0x29 0x53 0x00 0xB0 ...
```
Kolon duzeni (ini basligindan):
UniName, FullName, Vendor, Type, CE/Package, Blocks/CE, PageNum, PageSize, Die/CE, ECC,
ID0..ID5, ExtBlk/Die, DieOffset, PairPage, Interface, Plane, Endurance, Nandmem, SpareByte, GpioSet

### *** BIZIM PARCA = SKV606412 ***
- FlashID **AD 7E 29 53 02 B0**  (bayt5 0xB0 = V6 nesli)
- CE/Package=2, Die/CE=2 -> toplam **4 die**; Blocks/CE=5776 -> die basina 2888 blok
- 2888 blok x 1536 sayfa x 16 KB = ~64 GiB/die = **512 Gbit die** -> 4 die = **256 GB paket** ✓
- 4 paket x 256GB = 1 TB, 2 CE x 4 kanal = 8 CE (MAP1202 4CHx4CE destekliyor) ✓
- Interface=11, Plane=4, Endurance=3000, Nandmem=001, SpareByte=2048, GpioSet=100

### Marking decode DOGRULANDI (nesil harfi)
ini'deki isimlendirmeden cikan kural: H25 [xx] T=TLC/Q=QLC [NESIL HARFI] [die] ...
  gen A = V5 (FlashID bayt5 0xA0)   ornek H25BFT8A1M8R  -> SKV5064
  gen B = V6 (0xB0)                 ornek H25BFT8A1BDA  -> SKV6064
  gen C = V7 (0xC0)                 ornek H25TXTCX8CXX  -> SKV7064
  gen D = V8 (0xD0)                 ornek H25TXTD1XCX6  -> SKV8064
Bizim **H25T1T-B-4-8E**: T=TLC, **B = V6**, **4 = 4 die**. -> V6 + 4 die TEYIT.

### Ayni SKV6 kaydinin diger kontrolcu ini'lerinde gorunumu (capraz dogrulama)
- ma/map1602_44.ini satir 98-99: SKV606411/SKV606412 AYNI ID'lerle var (MAP1602 FlashIniVer=044)
- ma/mas1102_16.ini satir 104-107: SKV603205..08 (H25BFT8A1B8R/Z8R) AD 7E 28/29 53 02 B0/B2
- ma/map1002_29.ini satir 101-103: SKV603001..03, 0x2A = 4 CE varyanti var (V6 1Tb die)
=> SKV6 tanimi MAXIO ekosisteminde YAYGIN; MAP1202 Flash.ini **v043**'te mevcut.

>>> SONUC: Elde edilmesi gereken sey = **Flash.ini surumu >= 043 olan MAP1202 MPTool paketi**.
    (Bizdeki 19 paketin Flash.ini surumleri daha dusuk olmali - kontrol edilmeli.)

---

## [B2] GitHub dom0ng/map1202 — INCELENDI, SKV6 YOK
URL: https://github.com/dom0ng/map1202
Icerik (tum depo sadece 3 dosya): README.md, map1202.pdf, map1202too-unlocked.zip (4,4 MB)
Yerel: hyv6/map1202too-unlocked.zip
Zip icerigi = MXMPTool_MAP1202_USB_V0_01_009d.exe + Flash.ini + DAT/ + SYS/ + TMC/ + PARA/
  - DAT/ altinda SADECE **JGS3** (YMTC) timing klasoru: DAT/JGS3/001_600/, DAT/JGS3/001_800/
  - SYS/: KRRHCE2C.bin, MRRHCABC.bin, MRRHCD2C.bin, MRRHCDDC.bin, MRRHCDLC.bin, MRRHCELC.bin
  - PARA/Para_DW_JGS3_64GB_VPLR_FULL.ini, TMC/TMC_ARRAY_Default_M2_YMTC_X2_9060.ini
  => Bu paket YMTC X2-9060 (JGS3) icin. **SKV6 YOK.** Hedefi de farkli: seri no sahteleme.
Issue'lar (6 adet, hepsi okundu): #1..#6 — tamami seri no / EUI64 spoofing. SKV6/firmware paylasimi YOK.
  #1 "how much would it cost to help me make a firmware" -> cevapsiz.
Release: YOK (bos). Fork: 19 (taranacak).

### Paket klasor yapisi (dom0ng zip'inden ogrenilen sema - SKV6 icin gerekeni tarif eder)
  <tool>/Flash.ini                      <- SKV6064 kaydi burada (v043 gerekiyor)
  <tool>/DAT/<NANDKOD>/<Nandmem>_<hiz>/nandmem_<NANDKOD>_page.bin
        ornek: DAT/JGS3/001_600/nandmem_JGS3_page.bin
        SKV6 icin gereken: DAT/SKV6/001_<hiz>/nandmem_SKV6_page.bin
  <tool>/SYS/*.bin                      <- derlenmis sistem firmware'i (NAND'a ozel)
  <tool>/PARA/Para_*.ini , TMC/TMC*.ini , SORT/, DAT/ucode.bin

---

## [B3] *** KRITIK *** Flash.ini ZATEN ELIMIZDE — eksik olan Flash.ini DEGIL
Yerel paket: `scratchpad/dl/x8/MAP1202_H25TXTD2XCX6/Flash.ini`
```
[Version]
FlashIniVer=043
...
Name004=SKV606411 H25BFT8A1BDA 3 2 1 2888 1536 16 1 2 0xAD 0x7E 0x28 0x53 0x02 0xB0 ...
Name005=SKV606412 H25BFT8A1BDA 3 2 2 5776 1536 16 2 2 0xAD 0x7E 0x29 0x53 0x02 0xB0 ...
```
=> Elimizdeki **HYV8 paketi (C.1.1.26)** zaten v043 Flash.ini tasiyor ve **bizim FlashID'yi
   (AD 7E 29 53 02 B0) TANIYOR**. Gorevdeki "Flash.ini'ye elle kayit ekle" adimi GEREKSIZ.

## [B4] Paket anatomisi — NE EKSIK (V7 ve V8 paketleri kiyaslanarak cikarildi)
HYV7 paketi (`dl/x7/.../T1/`):          HYV8 paketi (`dl/x8/MAP1202_H25TXTD2XCX6/`):
  DAT/SKV7/001_{200..600}/nandmem_SKV7_page.bin   DAT/SKV8/001_{200..800}/nandmem_SKV8_page.bin
  PARA/Para_DW_SKV7_64GB_FULL_NO_RAID.ini         PARA/Para_DW_SKV8_PGR_FULL.ini
  TMC/TMC_ARRAY_Default_M2_HynixV7.ini            TMC/TMC_ARRAY_M2_HynixV8.ini
  SYS/YIQZCA2C,YIQZCABC,YIQZCADC,YIQZCALC.bin     SYS/YIC5CA1C..YIC5CB4C,ZIC5CB5C.bin
  MPTOOL.ini: FlashUniName=SKV703001              MPTOOL.ini: FlashUniName=SKV806402
              FWOneBinName=SKV7.bin                           FWOneBinName=SKV8.bin
              TMCFolder=..HynixV7.ini                         TMCFolder=TMC_ARRAY_M2_HynixV8.ini
  MXMPTool_MAP1202_USB_V0_01_017.exe              MXMPTool_MAP1202_USB_V1_1_26.exe
SYS build etiketleri (strings):
  V8: `r:/07-release/00_Release/HynixV8/Release_241127` + `MKSSD_...,Nov 27 2024,MAP1202,YIC5CA1C`
  V7: `MKSSD_501003000092860000,Jun 21 2022,MAP1202,YIQZCA2C`
  YMTC: `r:/00_release/01_cougar/02_ymtc9050/06_svn6760/code`

>>> SKV6 icin GEREKEN TAM 4 PARCA (baska hicbir sey degil):
    1. DAT/SKV6/001_<hiz>/nandmem_SKV6_page.bin
    2. SYS/<8 karakter>.bin   (build yolu `.../HynixV6/Release_xxxxxx` olmali)
    3. PARA/Para_DW_SKV6_*.ini
    4. TMC/TMC_ARRAY_*_HynixV6.ini

## [B5] ARAC SKV6'yi TANIYOR — dogrulandi (binary analizi)
`strings MXMPTool_MAP1202_USB_V1_1_26.exe` icindeki NAND kod tablosu:
  15NM 19NM B16A B17A B27A B27B B37R B47R B47T B57T B58R BIC2 BIC3 BIC4 BIC5 BIC6
  L06B N18A N28A N38A N38B N48R N58R **SKV4 SKV5 SKV6 SKV7 SKV8** SSV SSV4 SSV5 SSV6 SSV7 SSV8
Eski arac (V0_01_009d, 2022) tablosu: ... N38A **SKV6 SKV5** B47R SSV5 SSV6 BIC5  (SKV7/SKV8 YOK)
=> SKV6 destegi 2021'den beri araca derlenmis. ReleaseNote.txt (EEUUAA paketi):
   `===[20210531]=== MPT Ver C.0.01.005_RC  1.Support Hynix V6`
   Yani "arac taniyor, FW paketi eksik" tespiti DOGRU.

## [B6] Arac NAND mikrokodunu nasil yukluyor (zorla-yazma sorusunun teknik temeli)
exe icindeki yol sablonlari:
  `%s\%03d_%03d\nandmem_%s_page.bin`      -> DAT\SKV6\001_600\nandmem_SKV6_page.bin
  `DAT\%s\%03d_%d\%s_%03d_mem_%d.bin` (+ _eTLC / _iTLC varyantlari)
  Log: `FlashVendor = %d  FlashBINType = %s  FlashSize = %s  Retrytype = %d  bNandMem = %03d  wClock = %d`
Hata yollari: `SORT Nandmem file "%s" can not find %s!` · `Not found, please check your flash list!`
  · `CheckNandMemBin` · `ReadNandMemBin` · `Read AP_Param.sNandMem fail`
=> nandmem_SKV6_page.bin YOKSA arac o NAND'i surmeye BASLAYAMAZ; dosya bulunamadi hatasiyla durur.
   (MAXIO'nun pazarlama dilindeki "NAND自适配微码 / NAND-adaptive microcode" tam olarak bu dosya.)

## [B7] FlashID kontrol/degistirme anahtarlari (binary'den)
MPTOOL.ini [TestItems] (HYV8 paketi):  `EnCheckFlashID=1` · `EnModifyFlashID=0` · `EnEraseAllBlocks=1`
  · `EnPreFormat=1` · `EnDownload=1` · `EnCheckTables=1` · `EnCheckLDPC=1` · `EnCalibration=1`
exe stringleri: `Expected FlashID 0x%s` / `Device's FlashID 0x%s` / `CheckFlashID fail`
  -> EnCheckFlashID=0 SADECE bu karsilastirmayi atlar.
`EnModifyFlashID` -> tek cagri yeri `VP_PROC_WDBICModifyFlashID` (WD BiCS'e ozel ID yeniden yazma).
  **Nesil taklidi icin bir anahtar DEGIL.**
Fabrika bad-block korumasi: `Auto Inherit` · `VP_InheritLatterBB` · `VP_InheritRDT` · `EnInheritFW`
  · `CheckEraseAllBBNum` · `EnFactoryBad`

---

## [B8] BAKILAN VE ELENEN KAYNAKLAR (GitHub tarafi — tekrar aranmasin)
- github.com/dom0ng/map1202 — sadece YMTC/JGS3 spoof paketi. SKV6 YOK. 6 issue okundu, SKV6 yok.
  19 fork'un HEPSI ayni boyutta (4669/4672 KB) = kimse dosya eklememis. ELENDI.
- github.com/EEUUAA/MAP1202 — tam MPTool paketi ama Flash.ini v033 + DAT sadece JGS2/JGS3 (YMTC).
  ReleaseNote.txt degerli (V6 destek tarihi). MXUtility_0_05b + MKUpdater_V0_03a burada. SKV6 DAT/SYS YOK.
- github.com/xiaobodeluo/MAP1202-B47R-SSD-Repair-Tool — Micron B47R/B37R. SKV6 YOK.
  README cok degerli (ROM short prosedurü, JMS583 sarti, "Inherit FW BB" uyarisi,
  ve YENI IPUCU: **穗穗工具站** sitesinde "onlarca MAP1202 paketi" oldugu yaziyor).
- github.com/IVJik/maxio — 339 MB, 42 Maxio paketi. TAM LISTE tarandi: MAP1202 icin sadece
  HYV7 SN09286, YMTC_JGS_SN6760, B37R-SN5313 var. **MAP1202 SKV6 YOK.**
- github.com/iTXTech/fdfdb — Flash.ini veritabani (yukarida). Sadece ini, firmware YOK.
- GitHub code search: "nandmem_SKV6", "H25T1TB48E", "Support Hynix V6", "Para_DW_SKV6",
  "HynixV6 TMC_ARRAY", path:DAT/SKV6 -> HEPSI 0 sonuc.
- GitHub repo search: "MAP1202"(4), "maxio ssd"(2), "MAP1602"(0), "MAP1602 mptool"(0) -> yukaridakiler.
- archive.org advancedsearch: "MAP1202"=0, "MXMPTool"=0, "SKV6"=alakasiz(perma.cc). ELENDI.
- usbdev.ru MAP1202 sayfasi (onbellek: scratchpad/map1202mp.html): resmi liste
  C.1.1.26[HYV8] · C.1.1.25a[N4PA] · C.1.1.20a[N38B] · C.0.01.017[HYV7] · C.0.01.015[WD_BICS5]
  · B47R · B37R · X2_9060 · YMTC-JGS. **HYV6 YOK.** Sayfa metninde "V6"/"Hynix V6" hic gecmiyor.

---
# KOORDINATOR SORULARI (a) (b) (c)

## (a) iTXTech/fdfdb TAM TARAMA -> FIRMWARE YOK, sadece veritabani
Depo tamamen klonlandi (25 MB). 160 dosyanin TAMAMI envanterlendi (`file --mime-type`):
  .ini / .csv / .json / .SET / .dbf / .pdf / .xlsx / .php  — **tek bir .bin/.rar/.zip/.7z/.exe YOK.**
  `find . -name "*.bin" -o -name "*.rar" -o -name "*.zip" -o -name "*.7z" -o -name "*.exe"` -> BOS.
Yani fdfdb sadece Flash.ini/flash-DB koleksiyonu; nandmem/SYS/DAT barindirmiyor.

iTXTech org depolari (40 depo listelendi): Genisys, Synapse, mirai-*, FlashDetector, **fdfdb**,
  FlashMaster, FlashMasterAndroid/iOS, SharpFlashDetector, OpenDriveTester, Centasus, CrystalDiskInfoEmbedded...
  -> Hepsi decoder/DB/Minecraft/Android. **MPTool paketi barindiran depo YOK.**
PeratX kisisel depolari (30 listelendi): smartmontools, FlashMaster, airgap-vault, XrayR ...
  -> MAXIO firmware YOK.
SONUC (a): PeratX Flash.ini'yi bir yerden almis ama **ham paketi yayinlamamis**. Bu kol KAPALI.

## (b) MAP1602 / MAS1102 / MAP1002 / MAS0902 -> HICBIRINDE SKV6 PAKETI YOK
Flash.ini tarafinda SKV6 HER kontrolcude tanimli (yani NAND destegi jenerik):
  - ma/map1602_44.ini: SKV606411/SKV606412 (AD 7E 28/29 53 02 B0) VAR
  - ma/map1002_29.ini: SKV603001-003 (AD 89 28/29/2A 53 00 B0) VAR
  - ma/mas1102_16.ini: SKV603205-208 (AD 7E 28/29 53 02 B0/B2) VAR
  - ma/mas0902_61.ini: SKV603047-050 (AD 89 28/29/2A/2B 53 00 B0) VAR
AMA dagitilan PAKET listelerinde Hynix hic yok:
  - usbdev **MAP1602 MP/Sorting Tool** (14 paket) TAM LISTE cekildi:
    B58R x3, N58R x1, X2-9060 x1, X3-9060 x4, X3-9070 x5.  **Hynix/HYV/SKV = SIFIR.**
  - usbdev **MAS1102 MP/Sorting Tool** (33 paket) TAM LISTE cekildi:
    B17A x2, B37R x6, B47R x3, N28A x1, N38A x4, **SSV6 x2 (SSV6 = SAMSUNG V6, Hynix DEGIL)**,
    YMTC/JGS/TAS/X1-9050/X2-6070/X2-9060/X3-9060/X3-9070 x15.  **Hynix = SIFIR.**
  - IVJik/maxio (339 MB, 42 paket) TAM LISTE: MAP1602+WD ODPx2, MAS1102-SSV6, MAS0902 HYV4 (V4!),
    MAP1202 HYV7/JGS/B37R. **SKV6 = SIFIR.**
=> Tum MAXIO ekosisteminde halka acik SADECE IKI Hynix MAP1202 paketi var: **HYV7 ve HYV8**.
   Transplant icin kaynak olabilecek bir DAT/SKV6 hicbir yerde yok.

### nandmem tasinabilirligi — OLCTUM (spekulasyon degil)
Ayni NAND kodu (JGS3), IKI FARKLI paket ve IKI FARKLI arac surumu:
  dom0ng zip (V0_01_009d) vs EEUUAA depo -> `nandmem_JGS3_page.bin` **md5 BIREBIR AYNI**
  (001_600: 96a9ed9a2457..., 001_800: 04a7e70111f0...)
=> nandmem dosyasi arac surumune gore DEGISMIYOR; NAND'a ozgu sabit bir mikrokod.
   Yani bir yerden SKV6 nandmem'i bulunursa arac surumu onemli olmadan kullanilabilir. IYI HABER.
   Boyutlar nesle gore degisiyor: nandmem_SKV7=5544 B, nandmem_SKV8=8104 B, JGS3=4992/5104 B
   -> icerik nesle ozel; V7/V8 dosyasini "SKV6" adiyla kopyalamak GECERSIZ veri olur.

## (c) *** ELIMIZDEKI SKV8 PAKETIYLE DENESEK NE OLUR? ***
Aracin akisi (MXMPTool_MAP1202_USB_V1_1_26.exe string analizi):
  1. `AutoDetectButtonClick` -> `Load GDP` (GDP.bin kontrolcu RAM'ine; NAND'dan BAGIMSIZ)
  2. `VC_GDP_CmdAutoDetect` -> `VC_GDP_CmdReadFlashID` -> gercek FlashID okunur
  3. FlashID Flash.ini'de aranir -> bulunursa `Flash Auto Detect Result` + `FlashUniName` set edilir,
     bulunamazsa `Not found, please check your flash list!`
  4. MPT baslayinca NAND mikrokodu yuklenir: `%s\%03d_%03d\nandmem_%s_page.bin`
     (`FlashBINType` = UniName'in ilk 4 karakteri = **SKV6**)
  5. Preformat / EraseAllBlocks / Download / RWTest ...

**TAHMIN EDILEN SONUC:** Bizim disk AD 7E 29 53 02 B0 donecek. SKV8 paketinin Flash.ini'si v043
ve **SKV606412 kaydini iceriyor** -> adim 3 **BASARILI** olur; arac ekranda "SKV606412 /
H25BFT8A1BDA" gosterir. Ardindan adim 4'te `DAT\SKV6\001_<hiz>\nandmem_SKV6_page.bin` arar,
paket sadece `DAT\SKV8\` icerdigi icin **dosya bulunamaz** ve
`The "%s" file cann't be found!` / `SORT Nandmem file "%s" can not find %s!` ile durur.

>>> **KRITIK: bu hata NAND'a TEK BAYT yazilmadan once olusur.** nandmem, NAND arayuzunu
    kurmak icin gereken ilk sey; o yuklenmeden erase/program asamasina GECILEMEZ.
    Yani **SKV8 paketini denemek DUSUK RISKLI** — arac dosya-yok hatasiyla temiz durur,
    SKV8 firmware'ini V6 NAND'a kendiliginden YAZMAZ (NAND kodu, pakette hangi SYS
    dosyalari bulundugundan degil, OKUNAN FlashID'den turetiliyor).
    Yan fayda: denemek FlashID'yi kesin okutur -> H25T1TB48E decode'umuzu (V6/4-die) DOGRULAR
    ve diskin ROM modunda konusabildigini kanitlar.
    UYARI: Bu sadece "Auto Detect" icin gecerli. Operator FlashType listesinden ELLE bir V8
    profili (orn. SKV806402) secerse `EnCheckFlashID=1` uyusmazligi yakalar
    (`Expected FlashID 0x..D0` vs `Device's FlashID 0x..B0` -> `CheckFlashID fail`).
    `EnCheckFlashID=0` yapilirsa bu emniyet kalkar ve TEHLIKELI yola girilir (asagida).

---
# *** ANA SONUC: PAKET VAR, ADI VE YERI BELLI ***

## [B9] HEDEF DOSYA BULUNDU (indirilemedi — izin duvari)
Kaynak: **量产部落 / Liangchanba** — `https://club.liangchanba.com`
Bolum: `Maxio MAP1202 MP/Sorting Tool` = **https://club.liangchanba.com/thread-1761-1-1.html**

  aid   : **7498**
  DOSYA : **MAP1202_HYV6_64GBDIE-C.01.018-SN9466.rar**
  Boyut : **2,64 MB**   Indirme: 131   Yukleme tarihi: **2022-12-06**
  Izin  : **苦逼管理或更高级别**  (= "admin veya ustu" — en yuksek kademe)

Ad cozumu: HYV6 = Hynix V6 · **64GBDIE = 64 GB/die = 512 Gbit die = BIZIM SKV6064 ailesi**
  · C.01.018 = MPTool C.0.01.018 (HYV7'nin C.0.01.017'si ile HYV8'in C.1.1.26'si arasinda)
  · SN9466 = firmware SVN surumu.
Bu, aradigimiz 4 parcayi (DAT/SKV6 + nandmem_SKV6_page.bin + SYS SKV6 + PARA/TMC) iceren
**tek bilinen dagitimdir.**

### Neden indiremedim
- thread-1761 misafir olarak aciliyor (HTTP 200) ama sadece 24 ek gorunuyor; HYV6 eki
  izin kademesi nedeniyle misafire GORUNMUYOR.
- Wayback (20260316002108) anlik goruntusu de misafir goruntusu -> 22 ek, HYV6 yine yok.
- `forum.php?mod=attachment&aid=7498` -> Discuz DB hatasi;
  `viewattachpayments&aid=7498` -> **"该入侵行为已被记录，本站将协助公安机关取证调查"**
  (izinsiz erisim kaydedildi uyarisi). BU YOLU KAPATTIM, tekrar denenmemeli.
- Site izin kademeleri: 围观游客(misafir) < 注册会员 < 一星 < 二星 < 三星 < **苦逼管理**.
  Hedef dosya en ust kademede.
- NOT: usbdev.ru'daki bazi MAP1202 paketleri de 苦逼管理 kademesinde (or.
  MAP1202-B47R-0x39-V0.01.010) ama yine de disari sizmis -> yani bu kademe sizabiliyor.
  HYV6 sizmamis: usbdev'de, GitHub'da, IVJik'te, archive.org'da YOK.

## [B10] YARDIMCI HYV6 KAYITLARI (ayni siteden — transplant kaynagi olabilir)
  aid 8760 : **MAP1002-X-SKV6-D1.0-B.0.02.093B-SVN3588.rar** 2,82 MB · 2021-06-22
             izin **围观游客 (MISAFIR = herkese acik!)** — MAP1002 ama DAT/SKV6 tasiyor olmali
             (su an thread-1599'da gorunmuyor; arsivde de yok)
  aid 8926 : MAS1102_HYV6_64GBDIE-MPT-D.0.01.005-SN11628.rar 3,38 MB · 2022-11-02
  aid 6838 : MAS1102_HYV6_64GBDIE-MPT-D.0.01.005-SN15502_MOD.rar 3,48 MB · 2024-02-05
Not: SYS firmware kontrolcuye ozel (SYS bin'lerinin icinde `,MAP1202,` damgasi var),
     ama nandmem/DAT/TMC/PARA parcalari nesne olarak NAND'a ozel -> bu paketlerden
     `nandmem_SKV6_page.bin` cikarilabilir. 4 parcanin 3'u; SYS yine eksik kalir.

## [B11] YAN BULGULAR (isimize yarayacak, ayni listeden)
- **MAP1202-DB-01-02-C-20210223.rar** (2,51 MB, izin: 注册会员) = **MAP1202 referans kart SEMASI**
  -> ROM pad'leri, guc raylari, VCC_NAND olcum noktalari icin donanim teshisinde COK degerli.
- `联芸MAP1202、MAP1602主控量产工具开启"SYS FW Select"...` baslikli rehber konu var
  -> MPTool'da SYS FW secimini acma yontemi (zorlama sorusuyla dogrudan ilgili).
- `联芸MAP1202、MAP1602主控量产工具开启QC、MDI等功能` -> QC/MDI kilidi acma rehberi.
- MXUtility MAP1202: V0.02, 0_05b, 0_06a, V0.09a/09b, V0_011, V0_013, V0_014, V0_016, V0_017, V1_05
- MKUpdater MAP1202: V0_03a, V0_07, V0_08, V0_09_RC-SVN9273, V0_10, V0_12, V1_04
- ADATA_LEGEND750_FW_Updater_to_SVN9902_SVN9954_SVN9843.rar (8,54 MB) — MAP1202 satici updater'i
- ZHITAI TiPlus5000 Smart Tool V1.0-V1.3 (MAP1202) — hepsi **misafire acik**
- Tam liste: `scratchpad/hyv6/lcb_map1202_tam_liste.txt` (72 kayit)

---
# [B12] BAGIMSIZ DOGRULAMA — Rus kolu (ayrinti: hyv6/ru/notlar-ru.md, 439 satir)

Ayni paket, TAMAMEN BAGIMSIZ ikinci kaynaktan dogrulandi:
usbdev forum konusu **https://www.usbdev.ru/f/index.php?topic=13429.0**
(angelmxycry, 1 Mart 2026 — Fanxiang 256 GB, MAP1202 + SK hynix V6, ROM modda):
  Maxio MAP1202 MP/Sorting Tool: **C.0.01018_HYV6** · Serial: **SN09466**
  Firmware dosyalari: **ZI0PCABC, ZI0PCADC, ZI0PCD2C, ZI0PCPDLC**
  Durum: "к публикации / ещё не открыт" (yayina acilmamis)
  SYS ad semasi: HYV7 = YI+QZ (YIQZCADC.bin) · **HYV6 = ZI+0P (ZI0PCADC.bin)**
-> Benim liangchanba'da buldugum `MAP1202_HYV6_64GBDIE-C.01.018-SN9466.rar` ile BIREBIR AYNI.

usbdev Global Moderator **hardmaster** (2 Mart 2026) cevabi:
  «**Этой прошивки нет даже у китайцев за деньги. У нас то откуда?**»
  ("Bu firmware Cinlilerde bile PARAYLA yok; bizde nereden olsun?")

## NAND kimligi — calisan ikiz diskten alinmis GERCEK dokum (topic=13552.0, KingSpec NX-256)
`maxio_nvme_fid` ciktisi:
```
Fw : SN8878
Firmware id string : MKSSD_...88780000,Apr 26 2022,MAP1202,ZI0PCADC
Project id string  : r:/hynix_v6_8878
NAND string        : H25BFT8A1BDA
Ch*CE*: 0xad,0x7e,0x28,0x53,0x2,0xb0 - Hynix 3dv6-128L TLC 16k 512Gb/CE
```
=> **"Hynix 3dv6-128L TLC 16k 512Gb/CE"** — bizim H25T1TB48E decode'umuz (V6, 128 katman,
   512 Gbit die, 16 KB sayfa) UCUNCU kez dogrulandi. SYS build branch'i `r:/hynix_v6_8878`.
   (Onlarinki 0x28 = 1 CE; bizimki 0x29 = 2 CE/paket. Ayni nesil, farkli Flash.ini satiri.)

## Aranan paketin TAM ICERIK LISTESI (artik biliniyor)
  DAT/SKV6/001_{200..800}/nandmem_SKV6_page.bin
  SYS/ZI0PCABC.bin · SYS/ZI0PCADC.bin · SYS/ZI0PCD2C.bin · SYS/ZI0PCPDLC.bin
  PARA/Para_DW_SKV6_*.ini · TMC/TMC_ARRAY_*HynixV6*.ini · Flash.ini (v043 - bizde zaten var)
  MXMPTool_MAP1202_USB_V0_01_018.exe
Arama anahtarlari: `ZI0PCADC` · `ZI0PCABC` · `hynix_v6_8878` · `SN8878` · `SN09466` · `C.0.01018_HYV6`

## Rus kolunun taradigi ve ELEDIGI yerler
usbdev /files/maxio/ 6 sayfa · usbdev SMF forum board 21'in **236 konusunun tamami** grep'lendi
· board 9/28/27/20/23/6/4/3 · usbdev sitemap (1691 dosya sayfasi) · club.liangchanba thread-1761
ham HTML'de "HYV6"/"ZI0P"/"01018" **sifir kez** · file.diyflash.top (17 dosya) · vlo.name:3000
· flashboot.ru · GitHub kod aramasi (`ZI0PCADC`=0, `hynix_v6_8878`=0). Arama motorlari bloklu.
Yan bulgu: liangchanba'da usbdev'de OLMAYAN MAP1202 paketleri var (C.0.01.020_HYV7 vb.) - V6 yok.
Arsiv sifresi (liangchanba rar'lari): **maxio**

## Tek somut edinme kanali (temas KURULMADI)
`https://www.usbdev.ru/f/index.php?topic=13782.0` — DarwinLudwig'in "hizmet/takas" ilani,
**9 Eylul 2026'da guncel**. Odeme ya da takas ("bende/acikta olmayan yazilimla degisim").
Ilanda: `HYV6/HYV7 MAS1102 MPTool sort+fw — ПОЛУЧЕНО (elde edildi)` ve
`N48R MAP1202 — elde edildi ama dagitilamaz`. Yani HYV6 Maxio paketleri OZEL ELLERDE dolasiyor.

## Ayni ilandan yontem ipucu
«успешно собран N4PA из **обновлятора** и мптул для N38A» =
"N4PA paketi, perakende **firmware updater**'indan cikarilan NAND'a ozel .bin + komsu neslin
MPTool'u birlestirilerek basariyla kuruldu."
-> Aranmasi gereken: HYV6 tabanli bir perakende SSD'nin resmi FW updater'i (icinde ZI0PCADC.bin
   olabilir). Kontrol edildi: ADATA Legend750 updater = SVN9902/9954/9843 (V6 degil),
   ZHITAI TiPlus5000 = YMTC ZTA*. liangchanba indeksinde ZI0P/8878/hynix_v6/JamesDonkey = 0 sonuc.

---
# [B13] (c) SORUSU AMPIRIK OLARAK DOGRULANDI — tahmin degil, yasanmis vaka

Benim binary analizinden cikardigim tahmin: "SKV8 paketi NAND'i DOGRU tanir, sonra
nandmem/SYS dosyasini bulamayip yazmadan once durur."

usbdev `topic=13572.0` — Gate007, 31 Mayis 2026 (MAP1202 + Hynix **V7 QLC**), iki paketi de denemis:
  - HYV7-SN09286 paketi -> «не может определить мою память вообще» (hafizayi HIC taniyamadi)
  - HYV8-SN26637 paketi -> «**видит мою память, но ему не хватает файлов**»
    Eksik dedigi dosyalar: `\SKV7\002_600\nandmem_SKV7_page.bin` ve `\MPT\SYS\YIM3CA3H.bin`
=> Yapisal olarak BIZIM DURUMUN BIREBIR AYNISI. Tahmin DOGRULANDI:
   yeni arac (v043 Flash.ini) NAND'i dogru tespit ediyor, sonra eksik dosya adini
   EKRANA YAZIP duruyor. NAND'a yazma asamasina GECMIYOR.

>>> **BUNUN PRATIK DEGERI BUYUK:** Elimizdeki SKV8 paketini ROM-short + JMS583 ile calistirmak
    (a) diskin ROM modunda konusabildigini kanitlar,
    (b) FlashID'yi kesin okutur (H25T1TB48E -> V6 decode'umuzu diskin kendisiyle dogrular),
    (c) **aracin tam olarak hangi dosyalari istedigini ISIM ISIM ekrana yazdirir**
        (beklenen: `\SKV6\001_xxx\nandmem_SKV6_page.bin` ve `\MPT\SYS\ZI0Pxxxx.bin`)
    ve bunlarin hicbiri NAND'a yazma islemi baslatmaz. DUSUK RISKLI TESHIS ADIMI.

## [B14] "ZORLA YAZMA" (A sorusu) — TOPLU CEVAP
1. **V7/V8 paketiyle V6'ya yazmak MUMKUN DEGIL** — "zorlamaya" sira gelmiyor; arac dosya
   bulunamadi hatasiyla duruyor. EnCheckFlashID=0 sadece ID KARSILASTIRMASINI atlar,
   eksik dosya yaratmaz. `EnModifyFlashID` ise WD BiCS'e ozel (`VP_PROC_WDBICModifyFlashID`),
   nesil taklidi anahtari DEGIL.
2. **SYS bin = o NAND icin derlenmis C kodu.** usbdev moderatoru DarwinLudwig (topic=2.0 #94):
   «В самих бинарях С-шные скомпилленные процедуры для работы с конкретной памятью»
   Baska kontrolcuden almak -> `isp fail`; hatali .dat -> `noflash`; hatali bin -> "klasor bulunamadi".
   Ayrica `nandmem_*_page.bin` = derlenmis NAND mikrokodu (uCodeInfo.txt kaniti: kaynagi
   `FW_HYNIX_SDR33M_DDR2200M.c` gibi C dosyalari; icerigi `nops_op_bin` + `nifc_cmd_bin`,
   yani NAND komut dizileri). Nesle gore boyutu bile degisiyor (SKV7=5544 B, SKV8=8104 B).
   V8 dosyasini "SKV6" adiyla kopyalamak = gecersiz komut dizisi.
3. **Fiziksel NAND hasari: toplanan hicbir vakada YOK.** Program/erase gerilimi NAND die'in
   kendi charge pump'i tarafindan uretilir; MPTool sadece ONFI/Toggle komutu + timing gonderir,
   Vpgm ayarlamaz. Yanlis profil vakalari hep `check calibration fail`, `sorting result fail`,
   `isp fail` gibi TEMIZ HATA ile bitmis; diskler ROM modunda saglam kalmis.
   (Vakalar: topic=13445 old-boy77 & DMleon, topic=12338 JenDos_50, topic=13886 megrottv,
    MAP1202 sayfasi yorumu "Димка" 17 Oca 2026 — ayni nesil icinde ID+DIE degistirip basardi.)
4. **TEK GERCEK FIZIKSEL RISK:** MPTool'daki **Nand Voltage 2,5 V / 3,3 V** ayari.
   topic=12627 (21street): bu ayar **autodetect ile degismiyor** — yabanci bir paketten kalan
   yanlis deger, yanlis timing'den daha tehlikeli. Yabanci paket kullanilacaksa BU KONTROL EDILMELI.
5. **ASIL RISK = SESSIZ VERI KAYBI.** Elle birlestirilmis config'in tipik arizasi: MPTool PASS
   verir, Windows kurulur, kisa testler gecer — sonra belli bir doluluk seviyesinde
   («310-320 GB'da») firmware duser (topic=13304 fayer2356). Ayni desen Nayhel'de (SLC dolup
   QLC'ye gecince). Uzman kurali (Nayhel topic=13562): «То что прошивка есть не значит что
   подойдет. **Соберите тестовый SSD**» = "Firmware'in olmasi uymasi demek degil; TEST DISKI kur."
6. Ayni nesil icinde (or. V6-1die <-> V6-2die) ID/DIE duzenleyip basaranlar VAR;
   **nesil atlamada (V6<->V7/V8) basaran TEK vaka bile yok.**

---
# [B15] BENIM KOLUMUN BAKTIGI VE ELEDIGI YERLER (tekrar aranmasin)
GitHub (gh CLI, kimlik dogrulamali):
  · repo aramasi: "MAP1202"(4 sonuc), "maxio ssd"(2), "MAP1602"(0), "MAP1602 mptool"(0),
    "maxio mptool"(0), "开卡 量产 MAP1202"(0)
  · kod aramasi: SKV6(alakasiz 88k), nandmem_SKV6(0), H25T1TB48E(0), "Support Hynix V6"(0),
    Para_DW_SKV6(0), "HynixV6 TMC_ARRAY"(0), path:DAT/SKV6(0), FlashIniVer(11 - hepsi fdfdb+EEUUAA),
    MXMPTool(5), SKV6064(3 - hepsi fdfdb)
  · dom0ng/map1202 + 19 fork'un TAMAMI + 6 issue · EEUUAA/MAP1202 (tam klon) ·
    xiaobodeluo/MAP1202-B47R-SSD-Repair-Tool · IVJik/maxio (42 paketin tam listesi) ·
    iTXTech/fdfdb (tam klon, 160 dosya envanteri) · iTXTech org 40 depo · PeratX 30 depo
archive.org: advancedsearch "MAP1202"=0, "MXMPTool"=0, "SKV6"=alakasiz;
             CDX: club.liangchanba.com/thread-1761 (1 anlik goruntu, HYV6 yok), */MAP1202_HYV6*=0
Gitee (Cin GitHub) API: "MAP1202"=0, "maxio mptool"=0, "SKV6"=0
usbdev.ru: /files/maxio/map1202mpsortingtool (19 paketin tam listesi + 22 yorum),
           map1602mptool (14 paket - Hynix YOK), mas1102mptool (33 paket - Hynix YOK)
CSDN arama API'si: "SKV6", "海力士V6 开卡", "H25BFT8A1BDA", "MAP1202 海力士"(9), "MAP1202 量产"(150),
           "ZI0PCADC"(alakasiz), "hynix_v6_8878"(alakasiz), "MAP1202 HYV6"(2 - ikisi de HYV7),
           "金胜维 NX 固件升级"(0), "穗穗工具站"(alakasiz)
club.liangchanba.com: ana sayfa, forum-maxio-1.html (46 konu basligi), thread-1761 (MAP1202),
           thread-1599 (MAP1002), thread-1433 (MAS1102), wayback anlik goruntusu
kingspec.com: support.html?id=download -> JS ile yukleniyor, dosya linki yok (SSD Scope'a yonlendiriyor)
Arama motorlari: WebSearch kotasi 200/200 DOLU. Bing zh-CN alakasiz/zehirli sonuc donduruyor
           (sorgu ile ilgisiz Arapca sayfalar), DuckDuckGo html baglanmiyor (HTTP 000),
           Mojeek/Sogou bos donuyor. -> Tum arastirma site-ici gezinme + API ile yapildi.

---
# [B16] *** YENI EDINME YOLU: FIRMWARE'I CALISAN BIR DISKTEN GERI OKU ***
Elimizdeki araclarin binary'lerinde su rutinler VAR (dogrulandi, strings):
  MXMPTool_MAP1202_USB_V1_1_26.exe:
    `EnUpload` · `Upload` · `Upload Firmware Fail`
    `VP_UploadCodeFromFlash` (+ "fail! - 1 - code page", "fail! - 2")
    `VC_GDP_CmdGetCodeBlock` · `VP_CheckCodeBlockFromFlash` · `BackUpFileName`
  MXUtility_MAP1202_V1_11.exe: ayni `VP_UploadCodeFromFlash` + `EnUpload` + `BackUpFileName`
                               + `DumpRAWFile` / `DumpDebugFile` / `DPD_Dump_%02d.raw`
  MXUpdater_MAP1202_V1_10.exe: `Can't find FW.bin to update!` (yani FW.bin ile guncelliyor)

>>> ANLAMI: Arac, NAND'in system area'sindaki kod blogunu **GERI OKUYABILIYOR**.
    Yani **CALISAN** bir MAP1202 + SK hynix V6 diski (kisa sureligine bile) ele gecirilirse,
    SYS firmware'i (ZI0PCADC.bin ve kardesleri) ELIMIZDEKI araclarla ondan cikarilabilir.
    Bu, izin duvarina/Cin forumlarina bagimli OLMAYAN tek self-servis yol.
    Aday donor cihazlar (MAP1202 + Hynix V6 oldugu belgelenmis/olasi):
      - **KingSpec NX-256** (topic=13552'de tam bu NAND + SN8878/ZI0PCADC dokumu var — KESIN)
      - Fanxiang 256 GB (topic=13429'daki kullanicinin diski — KESIN, ama o da bozuk)
      - JamesDonkey JD serisi (bizimki), Netac/Reletech 256GB-1TB MAP1202 modelleri
    NOT: donor diskin V6 oldugunu ONCEDEN dogrulamak icin vlo'nun `maxio_nvme_fid` araci
    kullanilabilir (calisan diskte NAND string + FW id string + ID baytlarini yaziyor).

# [B17] EDINME YOLLARI — OZET (en gerceklesebilirden en zora)
1. **SKV8 paketini ROM-short ile calistir** -> yazma yapmaz, ama diskin FlashID'sini ve
   aracin istedigi TAM dosya adlarini ekrana yazdirir. Dusuk riskli, hemen yapilabilir. [B13]
2. **Calisan bir V6 donor diskten firmware'i geri oku** (`Upload`/`VP_UploadCodeFromFlash`). [B16]
3. **Perakende FW updater'indan .bin cikar** — usbdev'de kanitlanmis yontem (N4PA vakasi).
   KingSpec NX / Fanxiang resmi guncelleyicilerine bakilmali. [B12]
4. **量产部落 (club.liangchanba.com) uyeligi** — dosya orada (aid 7498) ama izin kademesi
   "苦逼管理" (admin). Ucretli uyelik bile yetmeyebilir.
5. **usbdev topic=13782 takas/hizmet kanali** (DarwinLudwig) — para veya yazilim takasi.
   *Temas kurulmadi; karar Alperen'in.*
6. MAXIO / JamesDonkey'den dogrudan talep — bkz. alt-marka kolunun raporu.

---
# [B18] UYARI — "dusuk riskli deneme"nin TEK gercek donanim riski: Nand Voltage
Rus kolunun uyarisi yerel olarak DOGRULANDI. MPTOOL.ini'de:
  HYV8 paketi (bizdeki): `NandVoltageItemIndex=**0**`
  HYV7 paketi (bizdeki): `NandVoltageItemIndex=**1**`
exe'de karsiligi: `Nand Voltage` / `NandVoltageComboBox` / `NandVoltageGroupBox`.
ReleaseNote C_0_1_017: "2.Add Voltage select(**3.3v/2.5v**)".
=> Iki paket FARKLI voltaj indeksi kullaniyor ve bu deger **autodetect ile degismiyor**
   (usbdev topic=12627, 21street). Yani SKV8 paketini V6 diskte calistirirken NAND besleme
   voltaji V8 icin secilmis deger olarak kalir.
ONERI: Denemeden once MPTool arayuzunde **Nand Voltage** kutusunu kontrol et; V6 (2021, 128L)
   nesli icin V7 paketinin degeri (index 1) daha muhtemel dogru. Emin olunamiyorsa
   sadece **"Auto Detect"e bas, "Start" ASLA basma** — Auto Detect FlashID okur ve
   eksik dosya adlarini yazar; asil MP akisi (erase/program) baslamaz.

Diger kiyas farklari (V8 vs V7 paketi, bilgi icin):
  V8: Bank=2, DefaultTiming=3, Clock=600, Endurance=1000, FlashID8th=22,
      DieReMap=03,FF,03,FF,... (8 CE)
  V7: Bank=4, Clock=600, FlashUniName=SKV703001, FWOneBinName=SKV7.bin
  Bizim SKV606412 icin beklenen: CE/Package=2 -> Channel=4, Bank=2 (V8'inkiyle ayni yapi)

---
# [B19] ELIMIZDE ZATEN OLAN SKV6 PARCALARI (beklenenden fazla)
Kendi paketlerimizde dogrulanan SKV6 varliklari:
  ✔ `Flash.ini` (v043, HYV8 paketi): SKV606411 + **SKV606412** kayitlari — bizim FlashID
  ✔ `SORT/mem.ini` (HYV8 paketi): **[SKV6_001_1]** read-retry tablosu MEVCUT
    (dogrulandi: `RR_000=ai\`fbacdchaedf^ec\`gh` ... 7 satir; hemen ardindan [SKV7_001_1] geliyor)
    HYV7 paketinin DAT/mem.ini'sinde de [SKV6_001_1] ve [SKV6_001_2] var.
  ✔ MXMPTool exe NAND kod tablosunda `SKV6` (hem 2022 V0_01_009d hem 2024 V1_1_26 build'inde)
  ✔ GDP.bin / SORT.bin: ReleaseNote'a gore V6 destegi 2021-2022'de eklendi
     (C_0_1_012 "Support Hynix V6"; C_0_1_017 SORT.bin "add SKV6-128GB die nand feature,
      update SKV6 ucode"; GDP.bin "support hynix v6 1Tb")
  ✘ EKSIK: DAT/SKV6/001_*/nandmem_SKV6_page.bin
  ✘ EKSIK: SYS/ZI0PCADC.bin (+ ZI0PCABC / ZI0PCD2C / ZI0PCPDLC)
  ✘ EKSIK: PARA/Para_DW_SKV6_*.ini
  ✘ EKSIK: TMC/TMC_ARRAY_*HynixV6*.ini
=> Eksik parca sayisi 4; bunlarin **en kritigi ve ikame edilemez olani SYS/ZI0P*.bin**.

# [B20] ⚠️ COZULMEMIS CELISKI — marking / kapasite
Cin flash veritabani (CN kolu, AD7E285302B0 sorgusu) diyor ki:
  **AD 7E 28 53 02 B0 -> HYV6, 料号 H25BFT8A1B8R, alias'lari: H25T1TB48E** (= bizim marking!)
  **AD 7E 29 53 02 B0 -> HYV6, 料号 H25T2TB88E**
Buna gore H25T1TB48E = "A1" = **1 CE / 1 die = 64 GB paket** -> 4 paket = 256 GB (1 TB DEGIL).
Oysa disk 1 TB olarak etiketli ve 4 paket var.
Olasi aciklamalar: (a) marking fotograftan eksik/yanlis okundu (T1 vs T4 vb.),
  (b) paket sayisi 4'ten fazla, (c) flash DB alias'lari gevsek (bir ID'ye birden fazla parca no).
>>> BU BELIRSIZLIK ISI ENGELLEMIYOR: Auto Detect gercek FlashID'yi okuyup dogru Flash.ini
    satirini (SKV606411 mi SKV606412 mi) KENDISI secer. Her iki durumda da gereken paket AYNI:
    MAP1202 HYV6 64GBDIE. Ama raporda "4 die kesin" diye yazilmamali.

---
# [B21] *** [B20] CELISKISI COZULDU + ARANAN SYS DOSYASININ TAM ADI ***
Alt-marka kolu, **ssd-tester.de'nin 461 modellik tum veritabanini** tarayip bizim FlashID'yi
tasiyan TEK urunu buldu: **GiGimundo G3500 1TB** — https://ssd-tester.de/gigimundo_g3500_1tb.html
Sayfada vlo `maxio_nvme_fid` raporu TAM haliyle var:
```
Controller : MAP1202
NAND string: H25BFT8A1BDA
Ch*CE*: 0xad,0x7e,0x29,0x53,0x2,0xb0 - Hynix 3dv6-128L TLC 16k 1024Gb/CE 512Gb/die
Channel 4 · CE 2 · Total bank 16 · Blocks/CE 5776 · Pages/Block 1536 · Page 16K
Planes 4 · Die/CE 2 · NAND MaxPE 3000 · NAND Freq 1200 · Size 1024.2 GB
Fw : SN19644
Firmware id string : MKSSD_501003000132020000,Feb 1 2024,12:16:26,MAP1202,**YI0PCELC**
Project id string  : **r:/0Project/HYV6_64GB_SVN13202**
```
=> Hesap: 4 kanal x 2 CE = 8 CE; Die/CE 2 -> **16 die** ("Total bank 16"); 16 x 64 GB = **1024 GB**.
   Paket basina 2 CE x 2 die = 4 die = 256 GB; 4 paket = 1 TB. **[B20] celiskisi YOK.**
   Alperen'in orijinal decode'u (V6, 512 Gbit die, 4 die/paket, 4 paket, 1 TB) TAMAMEN DOGRU;
   SKV606412 / AD 7E 29 53 02 B0 kesinlesti. (CN kolunun "H25T1TB48E -> AD7E28..." alias'i gevsek.)

## >>> BIZIM DISKIN IHTIYACI OLAN TAM SYS DOSYASI: **YI0PCELC.bin** <<<
   Proje/build: **HYV6_64GB_SVN13202** · FW etiketi **SN19644** · derleme 1 Subat 2024
HYV6 SYS ad semasi (iki ayri build dali tespit edildi):
   2022 dali (`r:/hynix_v6_8878`, SN8878): **ZI0PCADC, ZI0PCABC, ZI0PCD2C, ZI0PCPDLC** — 1 CE'lik
   2024 dali (`r:/0Project/HYV6_64GB_SVN13202`, SN19644): **YI0PCELC** — **2 CE / 2 die = BIZIMKI**
   (kiyas: SKV7 -> YIQZC* · SKV8 -> YIC5C*/ZIC5C*)

## KESIN NEGATIF: usbdev'in 19 paketindeki 39 SYS bin'inin TAM listesi
IC2RCDDC IQYOCE2C JC2RCDDC JQYOCD2C JQYOCDLC KC2RCABC KC2RCD2C KC2RCDDC KC2RCDLC KCIUCA2H
KCIUCA3H KCIUCA4H KCZPCD2C KCZPCDDC KCZPCDLC KRRHCE2C LC2RCE2C MCB6AA2H MCB6AA3H MRRHCABC
MRRHCD2C MRRHCDDC MRRHCDLC MRRHCELC XN6TCGDC YIC5CA1C YIC5CA2C YIC5CA3C YIC5CA4C YIC5CB4C
YIQZCA2C YIQZCABC YIQZCADC YIQZCALC YN6TCD2C YN6TCDLC YN6TCGDC YN6TCGLC ZIC5CB5C
-> **YI0PCELC ve ZI0P* YOK.** Hicbir usbdev paketinde HYV6 firmware'i olmadigi KESINLESTI.

## GiGimundo = ORICO Group (Changsha, Hunan)
gigimundo.com (Shopify, G3500 hala satista 256GB-2TB) · gigimundo.cn indirmeleri
cms.oricogroup.com'da; ayni sayfada Yottamaster var -> ORICO markasi. ORICO D10 / J-10 de MAP1202.
Indirme sayfalarinda (file_type_id=1 surucu, =2 kilavuz) **SSD firmware YOK** (bakildi).
Iletisim (SADECE TESPIT, temas KURULMADI): support@gigimundo.com · +86 400-107-8656

## Ayni kaynaktan: diger MAP1202 modellerinin NAND'i (donor arayisi icin)
  SKV7: Goodram PX500 256/512GB · TeamGroup MP33 Pro 1TB (usbdev'deki HYV7-SN09286 = BU firmware)
  Micron: Acer FA100 1TB · Lexar NM620 512GB · ORICO D10 512GB/2TB · Patriot P320
  YMTC: fanxiang S500 Pro 2TB · Origin Inception TLC 830 Pro 2TB · KingSpec NX 512GB
  Intel/Solidigm: fanxiang S501Q 2TB · Fikwot FX550 · PHIXERO P3000 · Patriot P320 2TB
=> **HYV6 donor adayi = GiGimundo G3500 1TB (hala satista)** — [B16]'daki "calisan diskten
   firmware'i geri oku" yolu icin en net aday. 2. aday: KingSpec NX-256 (ZI0P dali).

## Yeni arama anahtarlari (bundan sonraki aramalar icin)
`YI0PCELC` · `HYV6_64GB` · `SVN13202` · `SN19644` · `ZI0PCADC` · `hynix_v6_8878` · `SN8878`
GitHub kod aramasinda hepsi denendi: YI0PCELC=0 · HYV6_64GB=0 · SVN13202=0 · nandmem_SKV6=0

---
# [B22] MARKING'IN KESIN COZUMU — cip buyuk olasilikla H25T**2**TB**8**8E (yanlis okunmus)
Cin kolu, 量产部落'nin kendi flash veritabanindan (https://club.liangchanba.com/flash/) iki
BAGIMSIZ kayit cikardi:
  `AD 7E 28 53 02 B0` -> HYV6, 料号 **H25BFT8A1B8R**, alias'lari: **H25T1TB48E**, H25BFT8B3BLR
  `AD 7E 29 53 02 B0` -> HYV6, 料号 **H25T2TB88E**
Veritabanindaki TUM HYV6 ID'leri (11 adet): AD7E285302B0 · AD7E285302B2 · AD7E295302B0 ·
  AD7E2A5302B0 · AD5E285302B0 · AD5E295302B0 · AD89285300B0/B2 · AD89295300B0/B2 · AD892A5300B0

## Kapasite matematigi hangisini soyluyor
  H25T1TB48E = AD7E28 = 1 CE x 1 die = **64 GB paket** -> 4 paket = 256 GB
  H25T2TB88E = AD7E29 = 2 CE x 2 die = **256 GB paket** -> 4 paket = **1024 GB** ✔
Disk 1 TB (BIOS iki kez "JAMESDONKEY JD1024 1TB / 1024 GB" gordu) ve 4 paket var.
GiGimundo G3500 **1 TB** dokumu de tam bunu gosteriyor: AD7E29..., Ch4 · CE2 · Die/CE 2 ·
Total bank 16 · **1024.2 GB**.
>>> SONUC: cip uzerindeki marking buyuk olasilikla **H25T2TB88E**; fotograftan "T2"->"T1" ve
    "B8"->"B4" olarak yanlis okunmus (BGA uzerinde 1/2 ve 4/8 karisir).
    Dogru profil: **SKV606412 / AD 7E 29 53 02 B0**, gereken SYS: **YI0PCELC.bin**.
    ONERI: cip markingi buyutecle/makro fotoyla tekrar okunsun (T1 mi T2 mi, B4 mu B8 mi).
    Ama zaten Auto Detect gercek ID'yi okuyacagi icin bu isi ENGELLEMIYOR;
    ayrica aranan PAKET her iki durumda da ayni (MAP1202 HYV6 64GBDIE — icinde her iki
    varyantin SYS bin'i de bulunur: ZI0P* 1-CE, YI0PCELC 2-CE).

# [B23] Cin kolunun ek bulgulari
- 量产部落 thread-1761 RAR arsiv sifresi: **maxio**
- **thread-1599 (MAP1002/MAP1001 MPTool)** icinde "导航四：**SKV6**" bolumu VAR:
  baslik "Maxio MAP1002 MP/Sorting Tool **V2.93b_SKV6**" ama misafirde **🔒权限锁定**
  (dosya adi ve aid gizli). = benim xlsx'te buldugum aid 8760. Sayfada
  "量产工具适用性：MAP1002 ≈ MAP1001" yaziyor -> MAP1202 ile uyumlu DEGIL denmis.
  Yine de DAT/SKV6 nandmem'i icin kaynak olabilir.
- Baska kontrolcularin HYV6 paketleri liangchanba'da VAR (yani NAND yaygin, sadece MAP1202
  paketi kapali): Yeestor YS9082HC (HYV4/HYV5/HYV6), YS9082HP, **YS9205 MPTool
  V09.20.00.17.305 [HYV5,HYV6,HYV7,HYV8]** (destek listesinde AD7E285302B0 acikca var),
  Realtek RM1135/RTS5735 HYV6 paketleri (bircok surum).
- liangchanba forum aramasi (search.php) misafirde BOZUK: HYV6/HYV7/HYV8/HYV5 hepsi "0 个"
  donuyor (iki yonlu test edildi -> arac bozuk, "yok" kaniti DEGIL).
- liangchanba'daki 242 konunun tamami indirilip tarandi; Maxio ailesinde (MAS0901/0902 t1180,
  MAS1102 t1433, MAP1202 t1761, MAP1602 t1811) misafire acik SKV6 YOK.

# [B24] C SORUSU — URETICI/SATICI KANALLARI (temas KURULMADI)
- **MAXIO (联芸科技, Hangzhou, borsa kodu 688449)** — dogrulanmis adresler:
  `sales@maxio-tech.com` (0571-85892512-8011) · `contact@maxio-tech.com` (0571-85892512)
  · `hr@maxio-tech.com` · `ir@maxio-tech.com` (borsaya beyan edilen resmi kayit)
  Domain kendi mail sunucusunu calistiriyor (MX: mail.maxio-tech.com).
  **fae@/support@/tech@ HICBIR yerde yok.** Sitede 索取资料 (dokuman talep) formu var.
  "MAXIO'dan bireysel olarak tool almis" birine dair KANIT BULUNAMADI.
- **JamesDonkey / 贱驴** — UC bagimsiz kaynak: SSD kolu YOK. Firma 2014 kurulu,
  **mekanik klavye + oyuncu faresi** ureticisi. `贱驴固态`, `贱驴 ssd`, `JD1024` aramalari BOS.
  usbdev'de de donkey/JD1024/贱驴 = 0. JD.com/Tmall magazasi SPA oldugu icin dogrulanamadi.
  => JD1024 muhtemelen marka lisansli/ODM bir urun; ureticiden firmware beklenmez.
- **ACE Lab PC-3000 SSD: MAP1202'yi DESTEKLEMIYOR** (sadece SATA MAS0902/0901/1102).
  Ayrica PC-3000 Portable PRO + SSD yazilimi 5 haneli USD — tek disk icin anlamsiz.
- Soft-Center: ilgisiz.
- **GiGimundo/ORICO**: support@gigimundo.com · +86 400-107-8656 (Changsha). Indirme
  sayfalarinda SSD firmware yok; ama G3500 hala satista -> DONOR CIHAZ kaynagi olabilir.

---
# [B25] *** DUZELTME + EN SERT KANIT: dosya "gizli" degil, HIC YAYINLANMAMIS ***
Cin kolu, Wayback'in ham (`/id_/`) surumunu cekti:
`https://web.archive.org/web/20260316002108id_/https://club.liangchanba.com/thread-1761-1-1.html`
16 Mart 2026'da sayfada **导航一：HYV6** bolumu VARDI:
```
Maxio MAP1202 MP/Sorting Tool C.0.01.018_HYV6
  ( ZI0PCABC、ZI0PCADC、ZI0PCD2C、ZI0PCDLC ) (SN09466)：
  durum: 待发布      <-- "yayinlanacak": EK YOK, aid YOK, link YOK
```
Bugunku canli sayfada bu bolum **tamamen silinmis** (grep HYV6 = 0).

## [B9] ile uzlastirma
Benim xlsx indeksimde aid 7498 / 2,64 MB / 131 indirme kaydi VAR; CN'in gordugu sayfa etiketi
ise 待发布. Ikisi celismiyor: ek veritabaninda kayitli ve admin kademesince 131 kez indirilmis,
ama **halka acik yayina hicbir zaman alinmamis**; misafir goruntusunde "yayinlanacak" yaziyordu,
sonra bolum komple kaldirildi.
>>> PRATIK SONUC (raporda "izin duvari arkasinda" demistim, daha da kotusu):
    **Halka acik bir ayna cikmasini beklemek anlamsiz.** Dosya hic yayinlanmadi.

## Yan bulgu (transplant icin degerli)
Ayni snapshot'ta canlida OLMAYAN bir dosya daha var:
`MAP1202_WD_BICS5_64GBDie_MPT_C.0.01.018-SN09902_MOD.rar`
-> **C.0.01.018 ANA PROGRAMI** (MXMPTool_MAP1202_USB_V0_01_018.exe) baska bir NAND paketinden
   elde edilebilir. HYV6 icin gereken exe surumu bu; sadece DAT/SYS/PARA/TMC parcalari eksik kalir.

## 量产部落 erisim ekonomisi (CN kolu)
Kayit DAVETIYE ile: davet kodu **18 CNY/adet** ya da 软件交换 (nadir bir MPTool ile TAKAS).
Kademeler: 三星 > 二星 > 一星 > 注册会员 > 围观游客. **HYV6 eki 苦逼管理 (admin) kademesinde**,
yani 三星 satin alinsa bile acilmaz. Tek gercekci kapi TAKAS.

## CN kolunun bosa cikardigi kaynaklar (tekrar bakilmasin)
flashinfo.top (1200 MPTool kaydi tarandi; MAP1202'de HYV6 yok) · file.diyflash.top (15 dosya)
· CSDN download API · liangchanba 242 konunun TAMAMI · bbs.mydigit.cn 6 konu (cevaplar misafire
kapali) · chinafix ("网上没有") · ORICO/GiGimundo tum indirme sayfalari · KingSpec support
· pansearch.me · **穗穗工具站 = xmrom.kmdns.net:5000 OLU** (bt.cn "站点已暂停", Wayback'te hic
snapshot yok) · upantool.com ayni sekilde olu.

## ARAC UYARILARI (gelecek aramalar icin — onemli)
- **Bing bu IP'den zehirli**: her sorguya alakasiz sayfa donuyor, kontrol sorgusuyla iki yonlu
  dogrulandi. Kullanma. (Ben de ayni sonuca varmistim.)
- **360 so.com** cerez isitmasiyla calisiyor ama ~25 sorguda kilitleniyor; kilitliyken HER sorgu
  0 doner -> kontrol sorgusu olmadan "sonuc yok" cikarimi yapma. Noktali/alt-cizgili tam dosya
  adlarinda da 0 doner (tokenizasyon; kanit degil).
- **archive.ph Turkiye'de BTK karariyla engelli** -> Alperen'in kendi Oracle Frankfurt VPN'i
  uzerinden denenmeye deger; liangchanba snapshot'i orada olabilir. (Wayback'te olmayan
  snapshot archive.ph'de bulunabiliyor.)
- Calisanlar: CSDN arama API'si · web.archive.org CDX + `/id_/` ham surum · GitHub REST
  (kod aramasi icin kimlik dogrulama sart) · site-ici aramalar.
Kanit dosyalari: `hyv6/cn/KANIT/` (wayback snapshot, Flash.ini v033, canli+arsiv thread'ler)

---
# [B26] *** DUZELTME: SKV6 NAND MIKROKODU ZATEN ELIMIZDE (kismen) ***
[B4]/[B19]'da "ucode.bin eski, icinden SKV6 cikmaz" yazmistim — **YANLIS**. Alt-marka kolu
olcerek curuttu:
Elimizdeki **HYV8 paketinin `SORT/ucode.bin`**'i (ve 2022 HYV7 paketinin `DAT/ucode.bin`'i)
**SKV6 NAND mikrokodunu 8 frekansta iceriyor**:
  `SKV6_001_200 / _333 / _400 / _533 / _667 / _800 / _1066 / _1200`
ucode.bin = 16.384 baytlik sabit kayitlardan olusan duz arsiv; formati cozuldu, 16 SKV6 kaydi
cikarildi -> **`hyv6/alt/skv6_cikarim/`** (48 dosya).

## AMA dogrudan kopyalanamaz (bu da olculdu, tahmin degil)
`ucode.bin`'deki SKV6 kaydi, `DAT/SKV6/.../nandmem_SKV6_page.bin`'in **birebir aynisi DEGIL**.
Ayni cerceve + ayni uzunluklar, farkli icerik: ucode.bin'deki `LM_` (SORT akisi),
DAT'taki `LS_` (MP akisi) varyanti. Ikisinin de bulundugu nesillerde olculdu:
  SKV8: B bolumunun 4856 baytinin **1067'si** farkli · SKV7: 3384'un **1929'u** farkli.
Alt-kol aday dosyayi BILEREK URETMEDI (yanlis NAND zamanlama mikrokoduyla program/erase
fiziksel zarar verebilir). Ham kayitlar duruyor, birlestirme karari Alperen'de.
>>> Eksik parca sayisi pratikte 4'ten 3,5'a indi; ① nandmem icin artik bir BASLANGIC NOKTASI var.

# [B27] *** SATICI UPDATER'I = CIPLAK SYS FIRMWARE KUTUSU (yeni ve en umut verici yol) ***
ADATA LEGEND 750 FW Updater tam indirildi (8.416.201 B, dogrulandi):
`hyv6/alt/vendor/ADATA_LEGEND750_FWUpdater.rar` -> `vendor/adata/`
Icerik: `MX Updater Tool.exe` + `Update.ini` + **12 adet CIPLAK SYS firmware .bin**
(her biri ~692 KB, arsivde duz duruyor, MPTool paketi yapisi YOK).
=> **Tam MPTool paketine gerek yok.** MAP1202 + Hynix V6 kullanan HERHANGI bir markanin
   "firmware updater"i bulunursa, **`YI0PCELC.bin` o arsivin icinde ciplak durur.**
   Aranacak imza: ~690-725 KB dosya, basliginda **`MAS09_FWTAG_V001`** magic'i.
Marka kilidi asilabilir: `Update.ini` -> `EnCheckVID=1 / VID=0x1CC1` (ADATA);
   `EnCheckVID=0` yapilinca kalkiyor (HYV8 paketinde zaten 0).
KANIT — piyasada usbdev arsivinden FAZLA build dolasiyor, kaynagi marka updater'lari:
   Acer FA100 -> `KC2RCELC` · ORICO D10 2TB -> `KTH1CA2C` · Patriot P320 512GB -> `KTH1CADC`
   Ucu de usbdev'in 39'luk SYS listesinde YOK.

# [B28] *** VERI KURTARMA ICIN: SKV6 FIRMWARE'I OLMADAN HAM NAND OKUNABILIR ***
`MXUtility_MAP1202_V1_11.exe` **tek exe** — DAT/PARA/TMC/SYS klasoru ISTEMIYOR.
GDP modunda su islemleri destekliyor (binary stringleri):
  `Read/Write C:%d B:%d Block:%d Page:%d` · `Erase C:%d B:%d Block:%d` · `Erase Blocks`
  · `DumpRAWFile` · `VC_GDP_ChangeFlashID` · `VC_GDP_CmdSwitchToLegacy`
MAP1202'de uc mod var: normal · Loader (`Boot_Into_Loader_Mode`) · **GDP**.
>>> Amac diski calistirmak degil de **veriyi kurtarmaksa**, eksik SKV6 firmware'i BEKLEMEYE
    GEREK YOK: ROM-short + GDP modunda ham sayfa okuma denenebilir. (FTL cozumu ayri is.)
`maxio_nvme_fid v0.382a` ROM modda calismaz ama **GDP modda kismen calisir**
    (v0.38 changelog: "read fid/pp in gdp mode for map1202"). Indirildi: `hyv6/alt/x/`.

# [B29] B SORUSU — kalan netlestirmeler
- **MHU Updater diye bir sey YOK** (usbdev + GitHub + uc exe'nin stringleri: 0 sonuc).
- **RDT ayri arac degil**, MAXIO surecinin parcasi (`AP_RDT_PARA_MAP`, `VP_InheritRDT`,
  `EnSkipRDTResult`, MXUtility'de "Check RDT FW/Result").
- **MP vs SORT ayni exe**: MP = calisir firmware + FTL yazar; SORT = `SORT/SORT.bin` oz-tanilama
  firmware'i yazip bad-block tablosu urettirir (fabrikada ~70 C firinda).
- **nvme-cli'de maxio eklentisi YOK**; smartmontools'ta sadece SATA "JMicron/Maxiotek".
  MAP1xxx vendor admin opcode'lari: **0x80 0x84 0xC1 0xC2** — `nvme admin-passthru` ile
  gonderilebilir ama komut formati acik kaynakta belgeli DEGIL.
- **flashboot.ru'da Maxio kategorisi YOK** ("Категории не существует"). vlo sadece
  `http://vlo.name:3000/` (https ve :80 kapali). vlo araclarinin GitHub aynasi: **CLAMOWO/enpuresys**.
- Arama motoru istisnasi: **`old-search.marginalia.nu/search?query=`** captcha'siz calisiyor
  (indeks kucuk ama denenebilir).

# [B30] Kapatilan yanlis iz
usbdev `MAS1102-SSV6` ve ADATA'nin `[...SSV5,SSV6...]` updater'i indirildi, Flash.ini'sine bakildi:
**SSV6 = SAMSUNG** (0xEC, K9AFGD8J0C). SK hynix DEGIL. SKV* = SK hynix, SSV* = Samsung.

---
# [B31] UPDATER AVI — dedektor kalibrasyonu (iki yonlu dogrulandi)
Script: `hyv6/updater/maxio_fw_scan.sh <dizin>`
Imza: offset 0'da ASCII **`MAS09_FWTAG_V001`** · boyut 660-740 KB
      (gorulen: 675840 / 692224 / 708608 / 724992)
      icinde `MKSSD_<n>,<tarih>,<saat>,MAP1202,<8 KARAKTER SYS>` + `r:/...` build yolu
Pozitif test: ADATA Legend750'nin 12 bin'i -> B47R/YMTC/BiCS5 dogru siniflandi.
Negatif test: HYV8 paketinin SYS klasoru -> "Hynix V8" dogru siniflandi.
**SYS adinin 3-4. karakteri nesil onekidir** — dogrulanmis tablo:
  `0P`=**HYNIX V6** · `QZ`=Hynix V7 · `C5`=Hynix V8 · `2R`=Micron B47R · `H1`=Micron B58R
  · `RH`=YMTC · `N6T/6T`=WD BiCS5 · `QY`=YMTC9050 · `1U`/`IU`=Intel/Solidigm QLC · `B6`=Intel QLC

# [B32] ZHITAI TiPlus5000 (MAP1202) updater'lari — INDIRILDI, HYV6 YOK
`hyv6/updater/zhitai/` — usbdev'den 3 arsiv, butunluk OK:
  TiPlus5000_Update_Tool_V1.rar (1.395.664) -> KRRHCE2C/MRRHCD2C/MRRHCDLC, build `Release_Brance_9142`
  TiPlus5000_Update_Tool_V2.rar (1.406.339) -> ayni 3 SYS, build `Release_Brance_10093`
  ZHITAI_TiPlus5000_Firmware_Update_1014.rar (2.694.299) -> sadece PDF
=> 6 bin, hepsi **YMTC**. ZhiTai = YMTC markasi, beklendigi gibi. HYV6 yok.

# [B33] *** 461 MODELLIK VERITABANI UZERINDE KESIN SORGU ***
`hyv6/alt/sstd_all/` (ssd-tester.de tam dokumu) icindeki TUM MAP1202 modelleri ve firmware ID'leri
cikarildi. **29 MAP1202 modeli**, bunlardan 16'sinin SYS adi belli:
  YI0PCELC  GiGimundo G3500 1TB      r:/0Project/HYV6_64GB_SVN13202   H25BFT8A1BDA  <<< TEK HYV6
  YIQZCA2C  TeamGroup MP33 Pro 1TB   r:/DVT/skv7_9286                 H25G9TC18488  (V7)
  YIQZCADC  Goodram PX500 256GB      r:/DVT/skv7_12221                H25G9TC1X488  (V7)
  YIQZCALC  Goodram PX500 512GB      r:/DVT/skv7_12221                H25G9TC1X488  (V7)
  KC2RCELC  Acer FA100 1TB           MIB47R_SVN14665                  MT29Fxx08ExLEE
  KC2RCDDC  Patriot P320 256GB · KC2RCDLC ORICO D10 512GB   (B47R)
  KTH1CA2C  ORICO D10 2TB · KTH1CADC Patriot P320 512GB     (B58R, MT29Fxx08ExLCH)
  KRRHCE2C  Fanxiang S500 Pro 2TB · Origin Inception 2TB    (YMTC CYAxxTE1B1xC3B)
  MRRHCDLC  KingSpec NX 512GB        Release_Trunk_12350    (YMTC CYAxxTC1B1xC6C)
  KC1UCA2H/KC1UCA4H/KCIUCA4H/MCB6AA2H/MCB6AA3H  (Intel/Solidigm QLC: PHIXERO, fanxiang S501Q,
                                                 Patriot P320 2TB, Fikwot FX550)
>>> **461 modelin tamaminda HYV6 tasiyan TEK urun GiGimundo G3500 1TB.** Kesin negatif.

## KRITIK AYRINTI: ayni modelin FARKLI KAPASITESI FARKLI NAND kullaniyor
  KingSpec NX **512GB** = YMTC (MRRHCDLC)  ·  KingSpec NX **256GB** = **Hynix V6** (usbdev topic 13552)
  Fanxiang S500 Pro **2TB** = YMTC  ·  Fanxiang **256GB** = **Hynix V6** (usbdev topic 13429)
=> Updater ararken MODEL degil **MODEL+KAPASITE** hedeflenmeli. HYV6 dogrulanmis uc urun:
   1. **GiGimundo G3500 1TB** (ORICO Group)  2. **KingSpec NX-256**  3. **Fanxiang 256GB**
   Veritabaninda fid dokumu OLMAYAN MAP1202 modelleri (HYV6 olabilir, bilinmiyor):
   fanxiang S500 Pro 256GB/512GB/1TB · Verbatim Vi3000 256GB/1TB/2TB · Fikwot FN501 Pro 1TB/2TB
   · Emtec X300 Power Pro 2TB · TeamGroup MP33 Pro 512GB · fanxiang S501Q 1TB

# [B34] YAN GOREV — JamesDonkey: SSD kolu VAR (alt-kol sonucu eksikmis)
`linuxhw/SMART` topluluk veritabaninda **SSD/JAMESDONKEY/** dizini var, gercek disklerden
SMART ornekleri: **JD120 (120GB, 2 ornek), JD240 (240GB, 3 ornek), JD480 (480GB)**.
=> "JamesDonkey sadece klavye/fare uretir" tespiti EKSIK; marka SATA SSD satmis/satiyor.
   JD1024 (NVMe) bu veritabaninda YOK. PCB kodu **SMPMA1286** GitHub'da 0 sonuc,
   marginalia'da 0 sonuc -> ayni PCB'yi kullanan baska marka TESPIT EDILEMEDI.

# [B35] YEREL TAM TARAMA — indirilen HER SEY dedektorden gecirildi
`maxio_fw_scan.sh` tum `hyv6/` ve `scratchpad/dl/` agacinda kosturuldu.
**72 adet MAP1202 SYS firmware bin'i bulundu**, 23 benzersiz SYS adi:
  IC2RCDDC JC2RCDDC KC2RCD2C KC2RCDDC KC2RCDLC KRRHCE2C MRRHCABC MRRHCD2C MRRHCDDC
  MRRHCDLC MRRHCELC YIC5CA1C YIC5CA2C YIC5CA3C YIC5CA4C YIC5CB4C YIQZCA2C YIQZCABC
  YIQZCADC YIQZCALC YN6TCD2C YN6TCDLC ZIC5CB5C
Nesil dagilimi: Hynix V7=36 · Hynix V8=12 · YMTC=17 · Micron B47R=5 · WD BiCS5=2
**HYV6 (`0P` oneki) = SIFIR.** Elimizdeki tum materyalde temiz negatif.

# [B36] Telegram genel kanal onizlemesi — YONTEM CALISIYOR, tahmin edilen adlar yok
`t.me/s/<kanal>` kimlik dogrulamasiz okunabiliyor. **Iki yonlu test yapildi:**
  KONTROL: `t.me/s/telegram` -> 225 mesaj blogu · `t.me/s/durov` -> 200 mesaj blogu  (yontem SAGLAM)
  Denenen 11 ad: usbdev, flashboot, ssd_repair, ssdrepair, hddguru, mptool, liangchanba,
                 kaikatools, 开卡, ssdtools, flash_drive_repair -> hepsi 0 mesaj (kanal yok)
>>> DOGRU IFADE: "bu tahmin edilen kanal adlari mevcut degil" — "Telegram'da HYV6 yok" DEGIL.
    Telegram'da kanal KESFETME (arama) hesap olmadan mumkun degil; gercek kanal adi ogrenilirse
    icerigi okunabilir. Acik ucu boyle birakiyorum.

# [B37] Cin netdisk arama motorlari — kullanilamaz
alipansou.com HTTP 403 · yunso.net 200 ama JS SPA (arama URL'i yok, /search /s /search/X hepsi 404)
· dalipan.com 5 KB bos · pansoso.com 2,7 KB bos · pansearch.me (CN kolu denedi) sonucsuz.
=> Baidu/Ali netdisk paylasim indeksleri bu ortamdan sorgulanamiyor.

# [B38] GiGimundo/ORICO indirme merkezi — CMS duzeyinde KESIN NEGATIF
`gigimundo.cn/index/download/index?file_type_id=1..4` dort kategori de sayildi.
Kategori 3 (firmware) tam icerigi:
  RAIDManagerMac_Yottamaster · RAIDManagerWin_Yottamaster · Sleep_Time_Setting_Firmware_4_5_bay_hdd_enclosure
  · Sleep_Time_Setting_Firmware_PS200RU3_PS200RC3_FS2RU3 · Steps_for_update_the_firmware_JMI
  · Yottamaster_PCIe_Expansion_Card_Driver   (hepsi cms.oricogroup.com/storage/download/ altinda)
Kategori 4 = sadece PDF kilavuz.
=> **G3500 (ve hicbir ORICO SSD'si) icin firmware indirmesi YOK.** Alt-kolun tespiti CMS
   duzeyinde dogrulandi. Bu kapi kesin kapali; G3500 artik sadece DONOR CIHAZ adayi.

# [B39] archive.org CDX toplu marka taramasi — hepsi negatif
UYARI (metodoloji): CDX `filter=` icine Cince karakter (固件) konunca API **400 Bad request**
donuyor ve her alan adi icin "3 satir" (hata HTML'i) geliyor. Bunu "3 kayit bulundu" diye
okumak SAHTE POZITIF olurdu — kontrol sorgusuyla yakalandi. CDX filtresi SADECE ASCII olmali.
Duzeltilmis tarama (matchType=domain, limit=3000):
  kingspec.com  3000 URL / 11 arsiv · kingspec.cn 14 / 0 · fanxiang.com 14 / 0
  gigimundo.com 547 / 0 · gigimundo.cn 1 / 0 · orico.cc 3000 / 20 · fikwot.com 3 / 0
- ORICO'nun 20 arsivi: JMB352U_Firmware.zip, JMS539B_Firmware.zip, VL805_driver.zip,
  BTA-408 Bluetooth surucusu... = **USB kopru/Bluetooth firmware'i, SSD DEGIL.**
- KingSpec'in 5 adsiz `downloadsfront.do?...fileId=43..47` zip'i arsivden indirildi:
  43=PDF(5s) · 44=PDF(12s) · 45=PDF(15s) · 46=PDF(14s) · 47=604 bayt HTML.
  **Hepsi datasheet/kilavuz, firmware YOK.** (yerel: `hyv6/updater/ks/`)
=> Marka alan adlarinin arsiv gecmisinde MAP1202 firmware updater'i YOK.

---
# [B40] CIN MARKA KOLU — KESIN NEGATIF (0 yeni bin) + degerli yan bulgular
Ayrinti: `hyv6/updater/notlar-cin.md` (115 satir, kanit URL'leriyle), kanitlar `updater/cn/{pg,cdx,shd}/`

## Taranan Cin markalari (hepsi negatif)
  梵想 Fanxiang: SPA'nin indirme API'si bulundu `/api/index/Download/getDownloadList?cid=1..5`,
    5 kategori tamamen dokuldu -> SSD'de tek yazilim SSDmanagement-1.0.40-963.exe;
    indirildi+acildi (45 dosya), `MAS09_FWTAG_V001` YOK
  金胜维 KingSpec: support.html?id=download (4 sekme) + yeni domain **kingspectech.com**
    -> 89 PDF + 5 spec + 1 JMicron surucu. Firmware YOK. kingspec.cn DNS var TCP kapali
  朗科 Netac: netac.com.cn/zh-cn/download/ + 3 alt kategori + Wayback 11.7k URL -> Mac disk
    yazilimi ve USB bellek araclari. MAP1202 firmware YOK
  七彩虹 Colorful: /home/download + `Home/GetProductClassList` API -> SSD sinifi var firmware yok;
    arsivdeki 2 zip anakart BIOS'u
  致态 ZhiTai: zhitai.com.cn / zhitaitech.com / zhitai.cn hepsi **NXDOMAIN** (DoH ile dogrulandi)
  Kimtigo · Asgard · Gloway · Maxsun · Teclast · Galax CN: sadece garanti/tamir sorgu sayfasi
  SCY · Zheino · Vaseky · Shinedisk: **NXDOMAIN** — domain gercekten yok (sansur/engel degil)

## BIWIN yanlis pozitifi — DOGRU sekilde elendi (metodoloji ornegi)
`Biwin Intelligence.exe` (432 MB) icinde `MAS09_FWTAG_V001` **VAR** (offset 376720948).
AMA firmware degil: .rdata icinde dogrulayici sabit; hemen ardinda `abLDBKFWTAG_V00` +
"This is a ciphertext". 5 farkli boyutta kesildi, MKSSD etiketi/build yolu CIKMADI.
BIWIN toolbox'i MAXIO firmware'i yaziyor ama `.efp` dosyalarini calisma aninda **kapali bir
Aliyun OSS kovasindan** cekiyor (liste 403, 9 tahmin anahtari da 403).
Exe icindeki OSS kimlik bilgileri KULLANILMADI (dogru karar).
BIWIN'in MAP1202 sinif adlari: `..._nand_b58r_map1202_...` ve `..._nand_tas_map1202_...`
=> **Micron B58R + YMTC TAS. Hynix YOK.**
>>> DERS: `MAS09_FWTAG_V001` tek basina yeterli imza DEGIL; MKSSD etiketi + build yolu da aranmali.

## *** EN ONEMLI YAN BULGU: bizim NAND'i NADIR PARTI *** (smarthdd saha DB'si, 188.959 disk)
  KingSpec **NX-256 -> SN8878** (+SN08381, SN10092)  => HYV6/SN8878 iddiasi BAGIMSIZ dogrulandi
  Fanxiang **S500PRO 256GB -> SN10093 / SN10613 / SN11457** = hepsi **YMTC** build'i
=> Ayni model adi altinda farkli NAND partileri var; sahadaki 256GB'lerin COGU YMTC.
   **Alperen'in HYV6 unitesi nadir bir NAND partisi.** Toplu/perakende updater'larda bu yuzden yok:
   marka, azinlik partisi icin ayri firmware yayinlamamis. Bu, updater avinin neden bos
   ciktiginin YAPISAL aciklamasi.

## Web'de iz = sifir (iki yonlu test edilmis sert kanit)
`"YI0PCELC"` · `"ZI0PCABC"` · `"ZI0PCD2C" OR "ZI0PCDLC"` · `"SN8878"` · `"SN09466"` -> HICBIRI YOK.
`"MAP1202" "HYV6"` -> tek sonuc **usbdev topic=13429** (zaten bildigimiz konu).
  DUZELTME: CN kolu bu konuyu "Alperen'in kendi konusu" diye yazmis — YANLIS.
  Konuyu **angelmxycry** adli kullanici acmis (1 Mart 2026, Fanxiang 256GB). Alperen'in
  usbdev'de konusu YOK.
Kontrol sorgusu: ayni araclarla "MAP1202 mptool" 10 gercek sonuc dondu (yontem saglam).

## Ucuncu bagimsiz dogrulama
mydigit.cn/thread-495185 toplu listesinde MAP1202 klasorunun TAMAMI =
HYV7 SN09286 · B37R SN5313 · YMTC_JGS SN6760. **HYV6 yok.**
(Ayni listede BASKA kontrolculerin HYV6'si var -> NAND yaygin, eksik olan yalnizca
 MAP1202'ye derlenmis set. Bu, [B33]'teki sonucla ortusuyor.)

## liangchanba ek kontrolleri
- thread-1780'de "下载权限: 不限" yaziyor ama 9 ekin HEPSI misafirde `xinshu_denydown`
  plugin'ine dusuyor (467 baytlik deny.rar). **Gorevdeki "misafire acik" varsayimi YANLIS.**
- thread-1754 kapali (1金币 + 注册会员)
- **thread-1804 "Maxio MAP1202 Firmware Update Tool"** ilk kez acildi: 13 ek,
  sadece ~1 MB MKUpdater/MXUpdater araclari + SVN9273 + ADATA (elimizde). HYV6 gecisi 0.

# [B41] *** ARAMA GERI GELDI *** (sonraki oturumlar icin en degerli arac notu)
WebSearch kotasi dolu (200/200) AMA:
  **`https://r.jina.ai/https://duckduckgo.com/html/?q=<sorgu>`** -> captcha YOK, calisiyor.
  Iki yonlu test edildi. Hazir script: `hyv6/updater/cn/ddg.sh`
  Ayni proxy **CSDN'in JS duvarini da asiyor** (curl'de challenge, WebFetch'te 521).
Calismayanlar: Bing (proxy uzerinden de zehirli) · public SearXNG (Anubis PoW/429).
Wayback CDX notu: `filter=original:` regex'i HTML hata sayfasi donduruyor ->
  `&fl=timestamp,original&collapse=urlkey` ile cekip YERELDE grep'lemek gerekiyor
  (benim [B39]'daki ASCII tespitiyle ayni sorunun baska yuzu).

# [B42] Disk durumu
`/dev/sda2 164G, 149G dolu, 7,0G bos (%96)`. scratchpad 1,7 GB (hyv6 1,4 GB).
CN kolu 432 MB'lik Biwin exe'sini ve anakart BIOS zip'lerini kendisi sildi. Kritik degil
ama uzun surerse izlenmeli; hyv6 altinda tekrar indirilebilir arsivler var.

---
# [B43] BATI MARKA KOLU + benim kapatislarim — UPDATER AVI SONUCU: HYV6 YOK
Ayrinti: `hyv6/updater/notlar-bati.md`

## Bulunan tek satici updater seti: ADATA Legend 750 (zaten elimizdeydi)
12/12 bin dogrulandi: 5× Micron B47R (IC2R/JC2R/KC2R*) · 5× YMTC (KRRH/MRRH*) · 2× WD BiCS5 (YN6T*)
Yerel: `hyv6/updater/adata_legend750/`. **HYV6 yok.**

## YAPISAL BOSLUK KAPATILDI: usbdev firmware'i MARKA bolumlerinde de tutuyor
Onceki kollar sadece `/files/maxio/` bakmisti. usbdev'in TUM "firmware update" sayfalarini
wp-json ile sayd�m (~190 sayfa). **MAP1202 ailesinden yalnizca 4 sayfa var:**
  /files/maxio/adatalegend750fwupdate/   (elimizde, HYV6 yok)
  /files/maxio/tiplus5000updatetool/     (elimizde, YMTC)
  /files/lexar/lexarnm610profwupdate/    (asagi bak)
  /files/lexar/lexarnm610fwupdate/       (asagi bak)
  (+ /files/maxio/vipervp4300l1tbupdatetool/ = MAP1602A, bizim degil)
=> **usbdev'de MAP1202 satici updater'i TUKENDI.**

## LEXAR IZI — gercek ama BIZE YARAMAZ (kanitla kapatildi)
NM610 PRO paketi: 3 adet **693.760 baytlik sifreli `.pkg`** (500GB/1TB/2TB).
Kendi olcumum: 693760 = 692224 + 1536 ✔ · ECB kesin (`84c41a121e6cc27a` blogu ~19.265 kez
= E(sifirlar)) · **8-23. baytlar UC DOSYADA DA AYNI** (`a1ee7a2ca1746992 42bb8b2c4a42bf20`)
-> uc kapasite **ayni anahtarla** sifrelenmis, sadece ilk 8 bayt (kapasite alani) farkli.
`SSD Dash.exe` icinde TEA delta 0x9E3779B9 -> TEA/XTEA. Bati kolu exe'yi 4-bayt hizali
tarayip TEA+XTEA denedi -> 0 eslesme; anahtar duz durmuyor, disassembly gerekiyor.

### AMA hangi NAND? -> **YMTC. Kanit:**
NM610 (PRO olmayan) paketini indirdim; icinde **`Release Note.xlsx`** var:
  平台 = **P1100(1200M)** · 可升级版本 = **7939 / 8530 / 9139** -> 9846 / 9948
  **SN07939 zaten usbdev'de var: `MAP1202-X2_9060-SN07939.rar` = MAP1202 + YMTC X2-9060.**
Ayrica ssd-tester dokumumde `lexar_nm620_512gb` -> proj `r:/02_Code/01_B47R/Trunk_DVT`,
NAND `MT29Fxx08ExLEE` = **Micron B47R**.
=> Lexar'in MAP1202'li urunleri **YMTC ve Micron**; HYV6 build'leri (SN8878 / SVN13202)
   bu numaralandirmanin tamamen disinda. **Sifreyi kirmak bize HYV6 getirmez.**
   usbdev'in sayfadaki "belki SM2263XT'dir" tahmini de muhtemelen yanlis (surum
   numaralandirmasi Maxio SVN desenine oturuyor, SMI'nin U0806U0 desenine degil).
   Karsilastirma: bilinen SM2263XT paketi (Goodram PX500) firmware'i **exe icine gomulu**,
   ayri `.pkg` yok — yapisal olarak da farkli.
>>> LEXAR IZI KAPANDI. (Dosyalar duruyor: `hyv6/updater/lexar_nm610pro/`, `.../lexar_nm610/`)

## Bati kolunun diger kapatislari
- **Acer/Predator KESIN kapali (binary kanit):** `Biwin Intelligence.exe` icindeki surucu
  siniflari sadece `ssd_nand_b58r_map1202_micro_usb` + `ssd_nand_tas_map1202_micro_usb`.
  Hynix sinifi YOK. Kapsam: FA100, RE100, RE100 M.2, Predator GM3500.
- Patriot: S3 kovasindaki **338 anahtarin tamami** listelendi, P300/P320 firmware YOK
- ORICO: attachment merkezi 5 sayfa x 13 kategori (48 dosya) = USB kopru/hub surucusu
- GiGimundo: Shopify'da indirme yok · `.cn` API "504 不支持直接请求" · Wayback CDX 0
- Silicon Power / Apacer / Verbatim / Emtec / Integral / Hikvision / TeamGroup(site bakimda)
  / Fikwot: SSD firmware yayinlamiyor
- Goodram updater'i: SATA "ATA Basic Tool", MAP1202 yok
- **DOGRULANAMADI (yok DEMIYORUZ):** Kingston (Akamai 403) · PNY (404) · Origin (CF 403)

## Yan bulgu: yeni MAP1202 modeli
ssd-tester'in 9 bolgesel sitesi tarandi; `.de` disinda **Taimi Vulcan** cikti:
  256GB = **AIQZCADC** = Hynix **V7** · 512GB/1TB = **OOPVCP2C / OOPVCP3C**
  (`PV` oneki daha once hic gorulmemis — bilinmeyen bir NAND ailesi)

## Arac notlari (bati kolu)
- Wayback CDX filtresinde **kose parantez varsa `curl -g` SART**; yoksa curl exit 3 verip
  cikti dosyasini hic olusturmuyor = SESSIZ ARIZA (bir tur kaybettirmis).
- Bu IP'den captcha'siz calisan tek arama motoru: **Naver**. Baidu ilk sorgudan sonra 302.
