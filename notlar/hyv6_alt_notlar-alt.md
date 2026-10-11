# HYV6 — Alternatif kaynak arastirmasi (MAXIO MAP1202 + SK hynix V6)
Tarih: 2026-09-12
Hedef: SKV6 (H25BFT8A1BDA / FlashID AD 7E 29 53 02 B0) firmware iceren MPTool / vendor updater bulmak.

## Ham notlar

## ARAC ORTAMI
- WebSearch kotasi (200/200) TUKENDI. Bing/DDG/Mojeek/SearXNG hepsi captcha veya zehirli sonuc.
- CALISAN YOL: dogrudan site erisimi + WordPress REST API arama.
  `curl 'https://www.usbdev.ru/wp-json/wp/v2/search?search=MAP1202&per_page=50'` -> JSON, calisiyor.
- Arsiv acmak icin statik 7-Zip indirildi: `alt/7zbin/7zz` (7-Zip 25.01 x64). Sistemde 7z/unrar YOKTU.
  Kullanim: `./7zbin/7zz l dosya.rar`, `./7zbin/7zz x -y -ohedef dosya.rar`

## *** EN ONEMLI BULGU: EKSIK OLAN SEY DARALDI ***
usbdev'deki EN YENI MAP1202 paketi indirildi ve acildi:
  dl/MAP1202_H25TXTD2XCX6.rar  (C.1.1.26 [HYV8-SN26637], 3 627 774 B)
  acilmis: xh8/MAP1202_H25TXTD2XCX6/
Bu pakette:
  - Flash.ini **FlashIniVer=043** ve icinde bizim kayit AYNEN var:
      Name005=SKV606412 H25BFT8A1BDA  ... 0xAD 0x7E 0x29 0x53 0x02 0xB0 ...
  - SORT/mem.ini icinde **[SKV6_001_1]** read-retry tablosu VAR
  - MXMPTool_MAP1202_USB_V1_1_26.exe icinde **SKV4 SKV5 SKV6 SKV7 SKV8** stringleri VAR
Ayrica EEUUAA/MAP1202 (GitHub) paketinde Flash.ini **v033** ve DAT/mem.ini icinde de
  [SKV6_001_1] / [SKV6_001_2] retry tablolari VAR.
HYV7 paketi (dl/MAP1202_HYV7_64GB_Die_128G-1T.rar) DAT/mem.ini'sinde de [SKV6_001_1/2] VAR.

=> YANI: Flash.ini kaydi + read-retry tablosu + MPTool exe destegi ZATEN ELIMIZDE.
   EKSIK OLAN sadece SU 4 SEY:
   1. DAT/SKV6/001_<freq>/nandmem_SKV6_page.bin      (NAND zamanlama mikrokodu; SKV8'de 8104 bayt)
   2. PARA/Para_DW_SKV6_*.ini                        (SKV7'de: Para_DW_SKV7_64GB_FULL_NO_RAID.ini)
   3. TMC/TMC_ARRAY_*_M2_HynixV6.ini                 (SKV7'de: TMC_ARRAY_Default_M2_HynixV7.ini)
   4. SYS/<8 karakter>.bin                            (SKV6 icin derlenmis sistem firmware'i) <- ASIL ZOR OLAN
   MPTool exe'den cikan yol sablonu: `%s\%03d_%03d\nandmem_%s_page.bin` -> DAT\SKV6\001_600\nandmem_SKV6_page.bin
   MPTOOL.ini'de karsiligi: FWOneBinName=SKV8.bin , TMCFolder=TMC_ARRAY_M2_HynixV8.ini
   SYS bin adlandirmasi: SKV7 -> YIQZCA2C/YIQZCABC/YIQZCADC/YIQZCALC ; SKV8 -> YIC5CA1C..YIC5CA4C/YIC5CB4C/ZIC5CB5C
   ucode.bin ESKI bir paket (uCodeInfo.txt sadece SKV4'e kadar gidiyor) -> icinden SKV6 cikmaz.

## SSV6 YANLIS IZ (kapatildi)
usbdev'de "ADATA MAS1102 Update Firmware Utility [B47R,N38A,B58R,SSV5,SSV6,YMTC]" ve
"MAS1102-SSV6-MPT-D.0.01.002d" var. Indirildi (dl/MAS1102-SSV6.rar) ve Flash.ini'sine bakildi:
  SSV6 = **SAMSUNG** (0xEC ile baslayan FlashID, K9AFGD8J0C/K9AF123333). SK hynix DEGIL.
  SK hynix = SKV*. Bizim ise yaramaz. (Ama ayni Flash.ini'de SKV606454/55 H25BFT8A1B8R
  = AD 7E 28/29 53 02 B0 var, yani ayni FlashID MAS1102 icin de tanimli.)

## [B] MAP1202 ICIN ARACLAR — TESPIT EDILENLER
Kaynak sayfa: https://www.usbdev.ru/files/maxio/  (Maxio bolumu, 40+ paket)

1. **MXMPTool / MP-Sorting Tool** (MXMPTool_MAP1202_USB_Vx_xx_xxx.exe)
   Uretim prosesi araci. Iki mod ayni exe icinde:
   - SORT: fabrika oz-tanilama firmware'i (SORT/SORT.bin) yazar, bad-block taramasi yaptirir,
     bad block tablosu olusturur. Fabrikada ~70 C firinda yapilir (usbdev yorumu).
   - MP (Mass Production): calisir firmware'i (SYS/*.bin) + FTL parametrelerini yazar.
   19 surum: https://www.usbdev.ru/files/maxio/map1202mpsortingtool/
2. **MXUtility_MAP1202** (v0.02 ... v1.11) — TANILAMA araci, yazmaz.
   Yaptiklari (exe stringlerinden): Check Flash ID · Check NAND Time · Average/Max Erase Count ·
   SMART oku/temizle · Check RDT FW / Check RDT Result · Check GPIO · Check Efuse_thermal ·
   bSLCShiftReadCnt / bTLCShiftReadCnt.
   7 surum: https://www.usbdev.ru/files/maxio/mxutilitymap1202/
   INDIRILDI -> dl/MXUtility_MAP1202_V1_11.rar (acilmis: xu/MXUtility_MAP1202_V1_11.exe)
3. **MXUpdater_MAP1202_V1_10.exe** — firmware GUNCELLEYICI (MPTool degil).
   HYV8 paketinin ICINDE geliyor: xh8/MAP1202_H25TXTD2XCX6/MXUpdater_MAP1202_V1_10.exe
   Ayarlari Update.ini'de. "Disk %d, Update Succeeded! Please Power Cycle!" · USB ve PCIe yolu var.
   Eski adi **MKUpdater_MAP1202_V0_03a.exe** (EEUUAA/MAP1202 deposunda var).
4. **maxio_nvme_fid v0.382a (vlo / Ochkin Vadim)** — MAP1002/1202/1602'de FlashID okur.
   INDIRILDI -> dl/maxio_nvme_fid-0.382a.rar ve vlo/maxio_nvme_fid.rar (acilmis: x/)
   Iki kaynak: https://www.usbdev.ru/files/maxio/maxionvmefid/ ve http://vlo.name:3000/tmph/maxio_nvme_fid.rar
   ONEMLI: "rom mode'da CALISMAZ, gdp mode'da SINIRLI calisir". v0.38'den beri
   "detect map1202/gdp mode" + "read fid/pp in gdp mode for map1202" var.
   Ciktisi: her Ch/CE icin 7 baytlik FlashID + NAND string + MaxPE + Freq + SLC cache ayarlari + genisletilmis SMART.
   Windows exe. Surucu sarti var (stornvme W10 / intel / samsung / phison ...). JMS583 / ASM2362-4 / RTL9210B
   USB koprusu uzerinden de calisiyor.
5. **NAND Parameter page decoder (parpg17.exe)** + **parameter page ornekleri** — vlo.
   INDIRILDI -> vlo/parpg.rar, vlo/parpage.rar. 164 ornek var ama **SK hynix ornegi YOK** (hepsi
   intel/micron/toshiba/samsung/ymtc). Hynix ONFI parameter page yayinlamiyor.
6. **RDT** — ayri bir arac DEGIL, MAXIO surecinin bir parcasi:
   MXMPTool binary'sinde `AP_RDT_PARA_MAP`, `VP_InheritRDT`; MPTOOL.ini'de `EnSkipRDTResult`;
   MXUtility'de `Check RDT FW` / `Check RDT Result`. Ayrica usbdev'de RDT etiketli bir paket var:
   MAS1102-JGS-X1-9050-SN9125-**RDT**.rar. RDT = fabrika dayaniklilik/burn-in testi firmware'i.
7. **MHU Updater** — BAKTIM, YOK. usbdev'de, GitHub kod aramasinda, MXMPTool/MXUpdater/MXUtility
   binary stringlerinde "MHU" gecmiyor. MAXIO'nun guncelleyicisi MXUpdater/MKUpdater adiyla aniliyor.
   (MPTOOL.ini'deki `EnHMUI=0` farkli bir sey — "HM UI".)

### ROM MODE / HAM NAND OKUMA — VAR
MAP1202'de UC mod var (MXMPTool stringleri): normal · **Loader** (`Boot_Into_Loader_Mode`,
`VP_GetCurrentMode is Loader`) · **GDP** (`VP_IsGDPMode`, GDP.bin yuklenir).
GDP modunda MPTool'un yaptigi ham islemler (exe stringleri):
   `Read C:%d B:%d Block:%d Page:%d`  ·  `Write C:%d B:%d Block:%d Page:%d`  ·  `Erase C:%d B:%d Block:%d`
   `VC_GDP_ChangeFlashID start/end`  ·  `VP_WriteNandMemPage`  ·  `VC_GDP_CmdSwitchToLegacy`
=> Yani kanal/bank/blok/sayfa duzeyinde HAM NAND okuma-yazma-silme MPTool'un GDP yolunda MEVCUT,
   ve FlashID'yi degistirme komutu da var.
ROM MODE'a girme yontemi (usbdev yorumu, dogrudan alinti):
   "Открываешь утиль, втыкаешь диск с замкнутыми ROM контактами, как определился – отпускаешь.
    Потом жмешь на Auto Detect и выбираешь память – потом жмешь Старт"
   = Araci ac, diski **ROM kontaklari kisali** olarak tak, tanindiginda kisayi birak,
     Auto Detect'e bas, hafizayi sec, Start.

### nvme-cli / smartmontools
- linux-nvme/nvme-cli eklenti listesinde **maxio YOK** (amzn config dapustor dell dera fdp huawei ibm
  innogrit inspur intel memblaze micron netapp nvidia ocp samsung sandisk scaleflux seagate shannon
  solidigm ssstc toshiba transcend virtium wdc ymtc zns). Kod aramasi: repo icinde "maxio" 0 sonuc.
- smartmontools drivedb.h: sadece "JMicron/Maxiotek based SSDs" (SATA JMF61x/66x/MAS0902A). MAP1202 YOK.
- Ama maxio_nvme_fid raporundan MAP1xxx'in destekledigi admin opcode listesi goruluyor:
  0x00 0x01 0x02 0x04 0x05 0x06 0x08 0x09 0x0A 0x0C 0x10 0x11 **0x80 0x84 0xC1 0xC2**
  (0x80/0x84/0xC1/0xC2 = vendor-unique). Linux'ta `nvme admin-passthru` ile bunlar gonderilebilir
  ama komut formati ACIK KAYNAKTA BELGELENMEMIS. Tersine muhendislik gerekir (maxio_nvme_fid.exe
  102400 bayt, tek dosya — analiz edilebilir).

### KAYNAK SITELERIN DURUMU
- usbdev.ru : CALISIYOR. Ana kaynak. Indirmeler uyeliksiz. Arama: wp-json REST API.
- vlo.name  : SADECE **http://vlo.name:3000/** (https ve 80 portu KAPALI). Dizin: /ssdtool/, dosyalar /tmph/
- flashboot.ru : **Maxio kategorisi YOK** ("Категории не существует"). Sadece USB flash kontrolculeri
  (alcor, chipsbank, phison, smi, skymedi, innostor...) + ssd/hdd/netac/wd/seagate. baktim, yok.
- usbdev FORUM (usbdev.ru/f/) : arama UYELIK istiyor (HTTP 403 "Вы не можете зайти в этот раздел"). Girmedim.
- 52pojie.cn : kendi aramasi Bing'e yonlendiriyor -> kullanilamaz.
- upan.cc, ipcas.com.cn : erisilemiyor (HTTP 000, baglanti kurulamadi). chiphell.com: HTTP 567.
- upantool.com : ana sayfa acik ama /search.asp ve /plus/search.php 404.
- GitHub mirror: **CLAMOWO/enpuresys** = vlo.name/tmph ve /ssdtool tam kopyasi (Subat 2025).

## GitHub'da MAP1202 DEPOLARI (4 tane, hepsi bakildi)
- dom0ng/map1202 (57 yildiz) — YMTC JGS3, seri no sahteleme amacli. SKV6 YOK. (parent zaten inceledi)
- **EEUUAA/MAP1202** (YENI BULUNDU) — "added support for fresh YMTC nand's".
  Birlestirilmis paket: DAT/JGS2 + DAT/JGS3, 9 adet SYS/*.bin, Flash.ini **v033**,
  MKUpdater_MAP1202_V0_03a.exe. DAT/mem.ini'sinde **[SKV6_001_1] ve [SKV6_001_2] VAR**.
  => Farkli NAND destegini TEK pakette BIRLESTIRMENIN mumkun oldugunu kanitliyor.
  https://github.com/EEUUAA/MAP1202
- xiaobodeluo/MAP1202-B47R-SSD-Repair-Tool — Hikvision C500 1TB, Micron B47R. Iki .7z (usbdev kopyasi).
- mghs15/test_map1202 — alakasiz (harita yazilimi).

## usbdev YORUMLARINDAN CIKAN PRATIK BILGI (tam metin: yorumlar_map1202.txt)
- [32] "Оживил HVY7 прошивкой SSD Reletech на 2ТБ ... прошивки под обьем на 2ТБ нет, пришлось
  **изменить айди чипа и его DIE** и лить 1ТБ. Все работает, тесты проходит."
  => Birisi HYV7 diski **Flash ID'yi ve DIE sayisini degistirerek** farkli kapasitedeki firmware ile
     canlandirmis. Yani Flash.ini kaydini duzenlemek CALISAN bir teknik. **Reletech** markasi da MAP1202'li.
- [33] "Оживил Apacer на 1TB с памятью Intel N38A. ... ещё нету прошивки под эту память, но скоро её
  загрузят" => usbdev zamanla yeni NAND buildlerini ekliyor. **Apacer** de MAP1202'li.
- Netac **NV3000** (500G/1T/512G) ve **NV2000** 1TB kullanicilarca MAP1202 paketleriyle kurtarilmis.
- KingSpec 128GB, Patriot P300 128GB (YMTC) kurtarilmis.
- USB koprusu **JMS583** yaygin kullaniliyor ve calisiyor.

## *** [A] ANA BULGU: AYNI NAND'I KULLANAN URUN BULUNDU = GiGimundo G3500 1TB ***
Kaynak: https://ssd-tester.de/gigimundo_g3500_1tb.html  (sayfada vlo maxio_nvme_fid v0.35a raporu TAM olarak var)
ssd-tester.de'nin **461 modellik TUM veritabani** tarandi (sstd_all/); HYV6 / H25BFT8A1BDA /
FlashID 0x7e,0x29,0x53 gecen **TEK model** bu.

GiGimundo G3500 1TB raporu (bizim diskle bire bir ayni):
  Controller            : MAP1202
  NAND string           : **H25BFT8A1BDA**
  Ch*CE*: 0xad,0x7e,0x29,0x53,0x2,0xb0 - **Hynix 3dv6-128L TLC 16k 1024Gb/CE 512Gb/die**
  Channel 4 · CE 2 · Total bank 16 · Blocks/CE 5776 · Pages/Block 1536 · Page 16K · Planes 4 · Die/CE 2
  NAND MaxPE 3000 · NAND Freq 1200 · Size 1024.2 GB
  Fw                    : **SN19644**
  Firmware id string    : MKSSD_501003000132020000,Feb  1 2024,12:16:26,MAP1202,**YI0PCELC**
  Project id string     : **r:/0Project/HYV6_64GB_SVN13202**

=> ARADIGIMIZ SYS FIRMWARE DOSYASININ ADI: **YI0PCELC.bin**
   Proje/build: **HYV6_64GB_SVN13202**, surum etiketi **SN19644**
   (Karsilastirma: SKV7 -> YIQZC*, SKV8 -> YIC5C*/ZIC5C*. usbdev'in yayinladigi 38 binlik
    SYS listesinde **YI0PCELC YOK** — yani hicbir usbdev paketinde HYV6 firmware'i yok, teyit.)
   Paket adi muhtemelen: MAP1202_HYV6_64GB_...SVN13202 veya ...SN19644 seklinde olurdu.

### GiGimundo kim?
- gigimundo.com (Shopify, HTTP 200) — G3500 NVMe SSD hala satista ($29.99-$269.99, 256GB-2TB).
- gigimundo.cn (HTTP 200) — **indirmeler cms.oricogroup.com'da barindiriliyor** ve ayni sayfada
  **Yottamaster** urunleri listeleniyor => GiGimundo = **ORICO Group** (Changsha, Hunan) markasi.
  Not: ORICO D10 ve ORICO J-10 de MAP1202'li. Ayni firma.
- Indirme sayfalari: gigimundo.cn/index/download/index?file_type_id=1 (surucu) ve =2 (kilavuz).
  Icerik SADECE Yottamaster RAID/uyku araclari ve PDF kilavuzlar. **SSD firmware'i YOK.** Baktim, yok.
- Iletisim (SADECE TESPIT, temas kurulmadi): support@gigimundo.com · +86 400-107-8656 ·
  Yuelu Ave 369, Xianjiahu Street, Changsha, Hunan, China.

### Diger MAP1202 modellerinin NAND'i (ssd-tester detay sayfalarindan, kanit var)
  SK hynix V7 (SKV7): Goodram PX500 256/512GB (H25G9TC1X488, proj skv7_12221, SYS YIQZCADC/YIQZCALC)
                      TeamGroup MP33 Pro 1TB (H25G9TC18488, proj skv7_9286, SYS YIQZCA2C, Fw SVN9286)
                      -> usbdev'deki "MAP1202_HYV7_64GB_Die_128G-1T.rar [HYV7-SN09286]" = **bu TeamGroup firmware'i**
  Micron: Acer FA100 1TB (B47R), Lexar NM620 512GB (B47R), ORICO D10 512GB/2TB (B47R/B58R),
          Patriot P320 256/512GB (B47R/B58R)
  YMTC/CYxx: fanxiang S500 Pro 2TB, Origin Inception TLC 830 Pro 2TB, KingSpec NX 512GB
  Intel/Solidigm (PF29F...): fanxiang S501Q 2TB, Fikwot FX550 MARS, PHIXERO P3000, Patriot P320 2TB

## [A] DIGER MARKA KONTROLLERI (kendim baktiklarim)
- **GiGimundo / ORICO Group**: SSD firmware indirmesi YOK. gigimundo.cn indirme sayfasi sadece
  Yottamaster RAID/uyku araclari + PDF kilavuz. orico.cc'de tek indirme sayfasi NAS icin
  (/index/topic/nas/download.html). SSD firmware YOK. Baktim, yok.
- **Reletech**: reletech.com CANLI ama GoDaddy tek sayfa; sadece /contact-us. Indirme/destek/firmware
  bolumu YOK. reletech.cn/.net erisilemiyor (HTTP 000). Baktim, yok.
  (Not: usbdev yorumunda "Reletech 2TB firmware'i ile HYV7 diski canlandirdim" deniyor — o firmware
   usbdev'den degil, muhtemelen elden ele dolasan bir paket.)
- **ADATA Legend 750 FW Updater** (usbdev wpfb_dl=12117, 6,7 MB indirildi ama sunucu yavas,
  arsiv EKSIK indi - vendor/ADATA_LEGEND750_FWUpdater.rar). Icerigi: sadece
  `MX Updater Tool V1.01(1202).exe` + `Update.ini`. Firmware exe'nin ICINE gomulu.
  Kapsam SVN9902 (WD BiCS5) / SVN9954 (Micron B47R) / SVN9843 (YMTC X2-9060) — **hynix YOK**.
  Update.ini: EnCheckVID=1, VID=0x1CC1 (ADATA) -> baska markanin diskinde CALISMAZ.
- **ZHITAI TiPlus5000** araclari MAP1202'li ama TiPlus5000 = YMTC NAND. Bizim ise yaramaz.

## [B] EK ARAC: iTXTech ekosistemi
- **fm.itxtech.org** (FlashMaster, "Memory Chip Intelligence Platform") CANLI (HTTP 200), aktif
  gelistiriliyor (son push 11 Eyl 2026). NAND part number cozucu + FlashID arama motoru.
- iTXTech/fdfdb icindeki tum Maxio ini'leri: map1002_29 · **map1202_43** · map1602_44 · mas0902_61 · mas1102_16
- fd.itxtech.org (eski FlashDetector) HTTP 200 ama 61 bayt (bos/yonlendirme).

## ARAMA ANAHTARLARI (bundan sonrasi icin)
Bir yerde HYV6 paketi varsa su stringlerden biriyle bulunur:
  `YI0PCELC`  ·  `HYV6_64GB`  ·  `SVN13202`  ·  `SN19644`  ·  `MAP1202 HYV6`  ·  `H25BFT8A1BDA`
  ·  `nandmem_SKV6_page.bin`  ·  `Para_DW_SKV6`  ·  `TMC_ARRAY*HynixV6`
GitHub kod aramasinda hepsi denendi: YI0PCELC=0, HYV6_64GB=0, SVN13202=0, nandmem_SKV6=0,
H25BFT8A1BDA=2 (sadece iTXTech/fdfdb ini'leri), SKV606412=2 (ayni).

## DOGRULAMA: YI0PCELC usbdev'de YOK
usbdev MAP1202 MPTool sayfasi 19 arsivin ICINDEKI TUM SYS binlerini listeliyor (39 adet):
IC2RCDDC IQYOCE2C JC2RCDDC JQYOCD2C JQYOCDLC KC2RCABC KC2RCD2C KC2RCDDC KC2RCDLC KCIUCA2H
KCIUCA3H KCIUCA4H KCZPCD2C KCZPCDDC KCZPCDLC KRRHCE2C LC2RCE2C MCB6AA2H MCB6AA3H MRRHCABC
MRRHCD2C MRRHCDDC MRRHCDLC MRRHCELC XN6TCGDC YIC5CA1C YIC5CA2C YIC5CA3C YIC5CA4C YIC5CB4C
YIQZCA2C YIQZCABC YIQZCADC YIQZCALC YN6TCD2C YN6TCDLC YN6TCGDC YN6TCGLC ZIC5CB5C
**YI0PCELC listede YOK** -> hicbir usbdev paketinde HYV6 firmware'i olmadigi KESIN.

## ARAMA MOTORU DURUMU (hepsi denendi, hicbiri kullanilamiyor)
Bing (RSS + HTML): alakasiz/zehirli sonuc · DuckDuckGo html+lite: CAPTCHA · Mojeek: CAPTCHA ·
SearXNG (searx.be, baresearch.org, search.inetol.net, priv.au): anti-bot · Yandex: CAPTCHA ·
Startpage: CAPTCHA · Brave: HTTP 429 · marginalia: CAPTCHA · stract: 404 · TechPowerUp: bot-check/403.
Calisan tek yontem: dogrudan site + site-ici API (usbdev wp-json, HFS API, GitHub API).

## C) ILETISIM KANALLARI -> ayri dosya: notlar-iletisim.md
Ozet: MAXIO contact@maxio-tech.com / sales@maxio-tech.com (borsada 688449, Hangzhou) tek gercek kanal.
JamesDonkey = klavye/fare markasi, SSD kolu yayinlanmis degil, e-posta adresi yok.
ACE Lab PC-3000 SSD: MAP1202 DESTEKLEMIYOR (sadece SATA MAS0902/0901/1102).

## KUCUK EK ARAC
- **SSD-Z** (http://aezay.dk/aezay/ssdz/) — kontrolcu/NAND tanima araci, ssd-tester.de'nin onerdigi
  arac listesinde. MAP1202'yi tanir ama firmware yazmaz. Tanilama.
- Wayback (web.archive.org/cdx) usbdev MAP1202 sayfasi icin TEK snapshot ve o da HTTP 403 ->
  "eskiden HYV6 paketi vardi sonra kaldirildi" ihtimali dogrulanamiyor/curutulemiyor.
- usbdev'de wpfb (dosya eklentisi) icin REST API YOK; sitemap sadece sayfa URL'leri. Toplu
  dosya listesi cikarilamiyor (indirmeler ?wpfb_dl=<id> seklinde, id'ler sirali).

## *** BUYUK IPUCU: VENDOR UPDATER = HAM SYS FIRMWARE KUTUSU ***
ADATA LEGEND 750 FW Updater TAM olarak indirildi (8 416 201 B, dogrulandi):
  vendor/ADATA_LEGEND750_FWUpdater.rar  -> acilmis: vendor/adata/
Icerigi:
  MX Updater Tool V1.01(1202).exe   (40 MB)
  Update.ini                        (134 B)
  **12 adet CIPLAK SYS firmware .bin** (her biri ~692 KB, arsivde duz duruyor):
    IC2RCDDC JC2RCDDC KC2RCD2C KC2RCDDC KC2RCDLC KRRHCE2C MRRHCABC MRRHCD2C MRRHCDDC MRRHCDLC
    YN6TCD2C YN6TCDLC
=> ONEMLI SONUC: **Tam MPTool paketine gerek YOK.** Bir marka MAP1202 + hynix V6'li diski icin
   "firmware updater" yayinladiysa, o arsivin icinde **YI0PCELC.bin** ciplak halde bulunur.
   Aranacak dosya: ~690-725 KB, basliginda `MAS09_FWTAG_V001` magic'i,
   icinde `MKSSD_501003000132020000,Feb  1 2024,...,MAP1202,YI0PCELC` ve `r:/0Project/HYV6_64GB_SVN13202`.
   (Karsilastirma: HYV8 SYS binleri 708608/724992 B, basliklari da `MAS09_FWTAG_V001`,
    proje stringi `r:/07-release/00_Release/HynixV8/Release_241127`.)

### Update.ini marka kilidi ve nasil asilir
ADATA'nin Update.ini'si:
  [DeviceSetting] ModifyFWV=0 PackBin=0 FWVersion=0 EnCheckFWBinInfo=0
  EnAutoUpdate=1 **EnCheckVID=1  VID=0x1CC1**  EnCheckVersion=1
`EnCheckVID=1` + `VID=0x1CC1` -> arac sadece ADATA diskinde calisir. **EnCheckVID=0** yapilinca
kontrol kalkar (HYV8 paketindeki Update.ini'de zaten `EnCheckVID=0, VID=0x0000`).
Yani yabanci markanin updater'i, dogru SYS bin ile birlikte, Update.ini duzenlenerek kullanilabilir.

## HANGI DOSYA NAND'A OZEL, HANGISI DEGIL (HYV7 C.0.01.017 vs HYV8 C.1.1.26 md5 karsilastirmasi)
  AYNI (NAND'dan bagimsiz):  SORT/sort_spi.bin (1792) · DAT/ldr23_nifc_cmd.bin (512) ·
                             DAT/ldr23_nops_op.bin (256) · DAT/opal.bin (65536) ·
                             DAT/NvmExpressDxe.rom (55808)
  FARKLI (surum/NAND bagimli): GDP.bin (233472 -> 249856) · SORT/SORT.bin (282624 -> 348160) ·
                             DAT/tmc_para.bin (16384, icerik farkli)
  **nandmem GERCEKTEN NAND'A OZEL ve boyutu bile degisiyor**:
      nandmem_SKV7_page.bin = 5 544 B   ·   nandmem_SKV8_page.bin = 8 104 B
  => SKV7/SKV8 nandmem'i SKV6 yerine KOYULAMAZ. nandmem_SKV6_page.bin mutlaka bulunmali
     (ya da MPTool'un GDP yolu ile NAND'dan uretilmeli).

## archive.org
advancedsearch API: MAP1202 -> 0 · MXMPTool -> 0 · "Maxio MPTool" -> 0 · HYV6 -> 14 (hepsi alakasiz
perma.cc arsivi). Baktim, yok.

## usbdev MAP1202 MPTool indirme kimlikleri (19 paket, referans icin)
11156 MAP1202-B37R-D3.0-C.0.01.003-SN5313 | 12869 MAP1202_YMTC_JGS_SN6760 |
14069 MAP1202-Micron_B37R-C.0.01.009d-SN05313-SN06051 | 14073 MAP1202_B47R-C_0_01_009d-SVN09954 |
14071 MAP1202-WD_BICS5_64GB-SN09902 | 13620 MAP1202-YMTC-JGS-C.0.01.009d-SN6760 |
13691 X2_9060-SN07939 | 13690 X2_9060-SN09142 | 13668 X2_9060-SN9843 | 13692 X2_9060-SN10093 |
13669 X2_9060-SN10613 | 13667 X2_9060-SVN11795 | 13666 X2_9060-SN14824 |
14070 B47R-0x39-V0.01.010-128GB-2TB-SVN9250 | 14074 WD_BICS5_64GB-SN08919 |
**11155 MAP1202_HYV7_64GB_Die_128G-1T** | 14305 N38B-SN19515 | 14072 N4PA-SN26904 |
**14809 MAP1202_H25TXTD2XCX6 (HYV8, EN YENI, Flash.ini v043)**
Indirme: https://www.usbdev.ru/?wpfb_dl=<id>   (uyelik gerekmiyor; sunucu yavas ~70 KB/s,
curl -m 400 kullan yoksa arsiv yarim iner ve 7zz "Unexpected end of archive" verir)

## TUM MAXIO AILESI TARANDI — HICBIRINDE HYV6 YOK
  MAP1202 (19 paket): HYV7 (SN09286) ve HYV8 (SN26637) VAR, **HYV6 YOK**
  MAP1602 (14 paket): B58R / N58R / X2-9060 / X3-9060 / X3-9070 — hynix HIC YOK
  MAP100x (4 paket) : B16A / B17A / JGS2 — hynix YOK
  MAS1102 (33 paket): B17A B37R B47R N28A N38A **SSV6(Samsung)** YMTC JGS X1/X2/X3 TAS — hynix YOK
  MAS0902 (23 paket): B0KB L06B B16 B17A B27A BICS3/4 N18A N28A SSV4 YMTC + **HYV4** — HYV6 YOK
=> usbdev.ru'nun TUM MAXIO arsivinde (93 paket) SK hynix V6 destegi yok. Kesin.

## *** BULGU: SKV6 NAND MIKROKODU ZATEN ELIMIZDE (ucode.bin icinde) ***
`ucode.bin` = 16384 baytlik sabit kayitlardan olusan duz bir arsiv.
Kayit yapisi: [0..15] ASCII etiket "<NANDKOD>_<nandmem>_<freq>" · [16..47] 4 adet (offset,uzunluk)
cifti (little-endian u32): (0x100,0x100) (0x200,0x400) (0x1000,lenA) (0x2000,lenB) · sonra payload.

**Her iki MAP1202 paketinde de SKV6 kayitlari VAR:**
  xh8/MAP1202_H25TXTD2XCX6/**SORT/ucode.bin** (4 797 560 B, 293 kayit, Eyl 2024):
      SKV6_001_200/333/400/533/667/800/1066/1200  — 8 frekans · lenA=2256 lenB=3424
  h7full/.../T1/**DAT/ucode.bin** (2 142 128 B, 130 kayit, May 2022):
      ayni 8 SKV6 frekansi · lenA=2192 lenB=3344
  (Ayrica SKV4/SKV5/SKV7/SKV8, SSV6/7/8, tum Micron/YMTC/Kioxia kodlari da ayni dosyada.)
Hepsi cikarildi -> **skv6_cikarim/** (16 kayit x 3 dosya = 48 dosya: .rec16k.bin, .A_*.bin, .B_*.bin)

### AMA: ucode.bin kaydi != DAT/<KOD>/nandmem_<KOD>_page.bin
Bunlar AYNI YAPI ama AYNI ICERIK DEGIL. SKV8 001_800 uzerinde olculdu:
  gercek nandmem dosyasi: 8104 B = 32 B baslik ("LDBK NANDMEM TAB " + 0x20 + lenA + offB + lenB)
                          + A (3216 B, adi "LS_CLT_8V_XINYH") + B (4856 B)
  ucode kaydi           : ayni lenA=3216 ama adi **"LM_CLT_8V_XINYH"**, B=4864 B
  A bolumunde 32. bayttan sonra fark VAR; B bolumunde 4856 baytin 1067'si farkli.
SKV7 icin ayni olcum (HYV7 paketi): lenA 2128 = 2128 (birebir uzunluk), farkA 189 bayt,
  lenB 3352 vs 3384, farkB 1929 bayt. Isim "CLT_7V_XINYH".
=> ucode.bin'deki = **SORT akisinin mikrokodu (LM_)**, DAT'taki = **MP akisinin mikrokodu (LS_)**.
   Birebir kopyalanamaz. Ama:
   (a) SORT adimi icin SKV6 mikrokodu ZATEN mevcut -> bad-block taramasi teorik olarak yapilabilir;
   (b) DAT dosyasinin cerceve formati tam olarak bilindigi icin aday bir nandmem_SKV6_page.bin
       (32 B baslik + A 2256 + B 3424 = 5712 B; gercegi muhtemelen ~5704-5712 B) ASSEMBLE EDILEBILIR.
       DOGRULANMADI — donanimda denenmedi, dogru olup olmadigi bilinmiyor. Iddia degil, aday.
SKV6 kaydinin ic isim alani: HYV8'de "...2_CLT_5V_XINYH", HYV7'de "CLT_5V_XINYH"
  (MAXIO ic adlandirmasinda hynix V6 -> "5V" profili; etiket yine de SKV6).

### UYARI — bilerek URETMEDIM
Aday nandmem_SKV6_page.bin dosyasini BILEREK olusturmadim. LM_ (SORT) ve LS_ (MP) varyantlari
arasindaki fark buyuk (SKV8'de B bolumunun %22'si, SKV7'de %57'si). Yanlis NAND zamanlama
mikrokodu ile program/erase yapmak NAND'a fiziksel zarar verebilir. Cikarilan ham kayitlar
skv6_cikarim/ altinda duruyor; birlestirme karari ve riski Alperen'in.

## *** MXUtility DE GDP MODUNDA HAM NAND OKUYOR (tek exe, NAND verisi gerektirmiyor) ***
xu/MXUtility_MAP1202_V1_11.exe (5 726 208 B, tek dosya, dl/MXUtility_MAP1202_V1_11.rar icinden)
stringleri:
  `Read  C:%d B:%d Block:%d Page:%d Success!` / `... Status Fail! - (%d)`
  `Erase C:%d B:%d Block:%d Success!`
  `Erase Blocks` / `EraseAllData` / `DumpRAWFile` / `DPD_Dump_%02d.raw`
  `VC_GDP_ChangeFlashID start/end` · `Ch %d, Bank %d, Loader Block is 0x%02X`
=> "kontrolcuyu ROM/GDP moduna sokup NAND'i ham oku/yaz" sorusunun cevabi: **EVET, arac VAR**
   ve bu is icin SKV6 firmware'ine gerek YOK — MXUtility tek basina calisiyor
   (MPTool'un aksine DAT/PARA/TMC/SYS klasorleri gerekmiyor).
   MPTool'da ayrica `VC_GDP_CmdSwitchToLegacy` var = dusuk hizli legacy zamanlamaya dusme.
   ROM moduna girme: PCB'deki ROM noktalarini kisa devre yaparak tak, taninca birak (usbdev yorumu).

## 461 MODELLIK TAM TARAMA SONUCU (MAP1202'li 29 model, NAND'lariyla)
  **hynix 3dv6-128L (SKV6)**: gigimundo_g3500_1tb  H25BFT8A1BDA  SYS **YI0PCELC**  <- TEK VE HEDEFIMIZ
  hynix 3dv7-176L (SKV7)  : goodram_px500_256gb (YIQZCADC) · goodram_px500_512gb (YIQZCALC)
                            teamgroup_mp33_pro_1tb (YIQZCA2C)
  Micron 176L B47R        : acer_fa100_1tb (**KC2RCELC**) · lexar_nm620_512gb · orico_d10_512gb (KC2RCDLC)
                            patriot_p320_256gb (KC2RCDDC)
  Micron 232L B58R        : orico_d10_2tb (**KTH1CA2C**) · patriot_p320_512gb (**KTH1CADC**)
  YMTC x2-9060            : fanxiang_s500_pro_2tb (KRRHCE2C) · origin_inception_2tb (KRRHCE2C)
                            kingspec_nx_512gb (MRRHCDLC)
  Intel/Solidigm          : fanxiang_s501q_2tb (KC1UCA4H) · fikwot_fx550 (MCB6AA2H)
                            phixero_p3000_1tb (MCB6AA3H) · phixero_p3000_512gb (KC1UCA2H)
                            patriot_p320_2tb (KCIUCA4H)

### DIKKAT: usbdev'de OLMAYAN firmware buildleri var
KC2RCELC (Acer FA100 1TB), KTH1CA2C (ORICO D10 2TB), KTH1CADC (Patriot P320 512GB) —
bu ucu de usbdev'in yayinladigi 39 SYS bin listesinde YOK. Yani MAP1202 icin usbdev arsivinden
DAHA FAZLA firmware build'i piyasada dolasiyor ve bunlar **marka guncelleyicileri** icinden geliyor.
Bu, YI0PCELC'nin bir yerlerde (GiGimundo/ORICO'nun servis kanalinda) bulunabilecegi anlamina gelir.
