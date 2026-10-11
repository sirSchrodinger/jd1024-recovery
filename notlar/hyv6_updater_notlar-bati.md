# BATI/TAYVAN MARKA KOLU — MAXIO MAP1202 SYS firmware avi (HYV6 hedefli)
Tarih: 2026-09-12 · Kapsam: SADECE web arastirmasi + indirme. Donanima/kaplikaya'ya dokunulmadi.
Hicbir kisiye/kuruma mesaj atilmadi, form doldurulmadi, hesap acilmadi.

## 0. OZET
- Taranan marka: 20+ · Indirilen arsiv: 8 · Cikarilan MAP1202 SYS bin: **12 (hepsi ADATA Legend750)**
- **HYV6 (`?I0P????` / YI0PCELC / ZI0P*) BULUNAMADI.**
- Yeni ve degerli bulgu: **Lexar NM610 PRO resmi updater'i 3 adet MAP1202 SYS firmware iceriyor
  ama TEA/XTEA ile SIFRELI** (asagida [L1]). Nesli bilinmiyor — tek acik kalan Bati kapisi bu.
- Ikinci bulgu: **BIWIN (Acer/Predator) MAP1202 urun hattinda hynix YOK** — ikili kanit [A1].

## 1. BULUNAN MAP1202 SYS BIN'LERI
### ADATA Legend 750 FW Updater (elimizde zaten vardi; siniflandirildi + kopyalandi)
Arsiv: `ADATA_LEGEND750_FWUpdater_SVN9902_SVN9954_SVN9843.rar` (8.416.201 B, usbdev aynasi)
Kaynak sayfa: https://www.usbdev.ru/files/maxio/adatalegend750fwupdate/
Yerel: `hyv6/updater/adata_legend750/` (12 bin + Update.ini)
Hepsi 692224 B (YN6T* 675840 B), ctl=MAP1202:
  IC2RCDDC 692224 B47R      5b6df4a962d60e008dcc691acb1db134
  JC2RCDDC 692224 B47R      1b403f1044c8363063effddb0c5bd168
  KC2RCD2C 692224 B47R      27375bf805ab9901d1516ab99f8f2010
  KC2RCDDC 692224 B47R      53594b4be387be4f8d0a66eaa671597f
  KC2RCDLC 692224 B47R      aefb55cafa9520bdc5ed8e3df5151f90
  KRRHCE2C 692224 YMTC      de8615fb724db047fff9fa5e825b2d59
  MRRHCABC 692224 YMTC      b6b7927ec991ef00354337c8b722ea54
  MRRHCD2C 692224 YMTC      0d64ecdfcda7dac9ce02b08ccb10c17e
  MRRHCDDC 692224 YMTC      3072b7e075a4e6261ddfc759edd9b70a
  MRRHCDLC 692224 YMTC      6b9b623bad00ff037092b6a395020901
  YN6TCD2C 675840 WD BiCS5  72ba251c998ced2ea7d4d53d420dbfe0
  YN6TCDLC 675840 WD BiCS5  5e759194f9bc3ffd7e7db93089c26bbd
Build yollari: B47R -> `r:/TEMP/B47R_SVN9878_Adata/1202_B47R_Base8319_Adata`
               YMTC -> `r:/00_release/2_Release_9843/Release_Brance_9843`
=> HYV6 YOK.

## 2. [L1] *** LEXAR NM610 PRO — SIFRELI MAP1202 FIRMWARE (EN UMUT VERICI ACIK UÇ) ***
usbdev'in **maxio degil `lexar` bolumunde** duruyor; onceki kollar sadece /files/maxio/ taradigi
icin kacmis:
  https://www.usbdev.ru/files/lexar/lexarnm610profwupdate/   (wpfb_dl=11631, 11630)
  https://www.usbdev.ru/files/lexar/lexarnm610fwupdate/      (wpfb_dl=11645, 11646)
  https://www.usbdev.ru/files/lexar/lexarns100fwupdate/      (wpfb_dl=11629)
Indirilenler (`hyv6/updater/arch/`):
  Lexar_NM610PRO_500GB&1TB&2TB_5915&9114_upgrade_to_9442.rar  9.508.440 B  a820eee3d73416390e5b95f4695a8bc6
  Lexar_NM610_250GB&500G_8530&9139_update_to_9846.rar         5.180.975 B  714e8224b83abbc9b53865a6bb8c55d9
  Lexar_NM610P_500GB&1TB_9139_update_to_9846.rar              5.180.988 B  aeff8b29245e0d3560eb029c42c1d5af
  Lexar_NM610_256GB&512GB&1TB_..._update_to_9846.rar          (kismi indi)  d1cc71913cf128eb98629dc85a47fa9a
  Lexar_NS100_256GB&512GB&1TB_update_to_D910R140.rar          5.030.073 B  (SATA/MAS0902 — ilgisiz)

### Icerik
`Lexar NM610PRO_.../` altinda **3 adet 693.760 baytlik .pkg** (`hyv6/updater/lexar_nm610pro/`):
  NM610 PRO 500GB FW Update 5915 to 9442.pkg   48a6d6adaf88973dc64855e628e2ea62
  NM610 PRO 1TB   FW Update 5915 to 9442.pkg   ca9fa4a8ff1fe267d05b4d84944b49ab
  NM610 PRO 2TB   FW Update 5915 to 9442.pkg   c5be90d088d581c61c1f5bce77479ded

### Bunlarin MAP1202 SYS firmware oldugu OLCULDU (tahmin degil)
1. Boyut: 693760 = **692224 (SYS bin) + 1536** (sarmalayici). Bizdeki tum MAP1202 SYS
   bin'leri tam 692224 B.
2. Blok profili (8 baytlik bloklar, ECB):
   duz ADATA SYS bin  : 86528 blok, ~53k benzersiz, en sik blok `0000000000000000` x23622
   Lexar .pkg         : 86720 blok (=86528+192), ~56k benzersiz,
                        en sik blok `84c41a121e6cc27a` x19265  (= E(0x00..00))
   Ayni "tek baskin blok" imzasi + ayni blok sayisi => ECB modda sifrelenmis SYS bin.
3. Uc dosyanin ilk bloklari ayni: blok1/2 sabit, blok3+ tekrarli => ECB, sabit anahtar.
4. `SSD Dash.exe` icinde **TEA delta sabiti 0x9E3779B9 (LE `b979379e`) x2** bulundu
   => sifre **TEA/XTEA** (64-bit blok, 128-bit anahtar). AES/Blowfish/DES sabiti YOK.
   Ayrica string: `Error:PHY Paramter from PKG is not right.`
5. Bilinen aciktan-metin cifti elde: **E(0x0000000000000000) = 84c41a121e6cc27a**
   -> dogru anahtar tek islemle DOGRULANABILIR.

### Anahtar arayisi — su ana kadar BASARISIZ
`tea_crack.py`: yazdirilabilir 16-baytlik pencereler + delta sabitinin ±4 KB'i (20.942 aday),
TEA/XTEA × enc/dec × LE/BE -> **0 eslesme**.
`tea_sweep.py` (arka planda): exe'nin TAMAMI, 4-bayt hizali pencereler, TEA-enc + XTEA-enc LE.
Sonuc: **0 eslesme** (tam exe tarandi, 973k hizali pencere x TEA+XTEA). Anahtar exe icinde duz 16 bayt olarak DURMUYOR — runtime'da uretiliyor. Tek yol `SSD Dash.exe` disassembly.
o durumda tek yol `SSD Dash.exe` disassembly.
>>> **Neden onemli:** NM610 PRO'nun 1TB varyanti, HYV6 G3500 1TB ile ayni kapasite sinifinda.
    Sifre cozulurse 3 yeni MAP1202 SYS bin'i aciga cikar ve nesilleri okunur.
    (NM610/NM610P'nin 3.465.728 B'lik .pkg'leri de ayni sekilde sifreli — muhtemelen 5 bin bir arada.)

## 3. [A1] ACER / PREDATOR (BIWIN) — HYNIX YOK, IKILI KANIT
- Resmi siteler: `acerstorage.com` ve `predatorstorage.com` (ikisi de BIWIN isletiyor).
  `/manuals-tools/` sayfalari + WP REST media kitapligi (472 kalem) TAM tarandi:
  **sadece PDF** (spec + kullanim kilavuzu). Firmware/updater dosyasi YOK.
  acer.com bu agdan erisilemiyor (curl 000); global-download.acer.com 200 ama arama arayuzu yok.
- Tek indirilebilir arac, urun sayfalarinda linkli:
  `https://smart-tool.oss-rg-china-mainland.aliyuncs.com/Public/Software/Biwin%20Intelligence/Biwin%20Intelligence.exe`
  (432.534.184 B) — **indirildi**: `hyv6/updater/arch/Biwin_Intelligence.exe`
- Binary analizi:
  · `MAS09_FWTAG_V001` stringi VAR ama sadece dogrulama sabiti (offset 376.720.948, kod/string
    tablosu icinde; etrafinda firmware govdesi YOK — tum exe'de tek gecis).
  · Desteklenen urunler: **Acer SSD FA100 · Acer SSD RE100 · RE100 M.2 · Predator SSD GM3500**
  · MAP1202 surucu sinifi SADECE IKI TANE:
      `DriveModel_ssd_nand_b58r_map1202_micro_usb`   (Micron B58R)
      `DriveModel_ssd_nand_tas_map1202_micro_usb`    (YMTC TAS)
    **Hynix/SKV sinifi YOK.**
  · Firmware calisma aninda OSS'ten cekiliyor: `Firmware/fwVersionConfig.dat`,
    `Firmware/fwUpgradeConfig.dat`. Bucket listelemesi kapali (AccessDenied);
    tahmin edilen 7 yol denendi, hepsi 403.
=> Acer/Predator hattinda HYV6 firmware'i BULUNMUYOR (marka beyani degil, kendi binary'lerinin kaniti).
Ek: usbdev `biwin/biwinintelligence` sayfasi eski surumleri (2.0.0.1 … 5.0.0.1) files.sberdisk.ru'da
    barindiriyor; Sberdisk SPA olduğu icin curl ile inilemedi (tarayici gerekir). Dusuk oncelik.

## 4. MARKA MARKA SONUC (baktigim URL -> sonuc)
| marka | bakilan URL | sonuc |
|---|---|---|
| ADATA | nexus-api.adata.com/api/page/bu/consumer/downloads (en/tw/cn) | Sadece SSD Toolbox + Backup ToGo. Legend 700/710/750 firmware YOK. Endustriyel API: sadece ia_toolbox.rar |
| ADATA | assets.adata.com / webapi3.adata.com/storage/support/ (Wayback CDX) | Tek firmware: `ec700g_extenal_enclosure_firmware_v13117102022.zip` (harici kutu, SSD degil) |
| ADATA | usbdev /files/maxio/adatalegend750fwupdate/ | **12 MAP1202 SYS bin — B47R/YMTC/BiCS5, HYV6 YOK** |
| Acer/Predator | acerstorage.com/manuals-tools + WP media API + predatorstorage.com | Sadece PDF. Firmware YOK. |
| Acer/Predator | Biwin Intelligence.exe (432 MB, indirildi) | MAP1202 destegi var ama **sadece B58R + YMTC TAS**. Gomulu bin YOK. |
| Patriot | s3.us-west-2.amazonaws.com/downloads.patriotmemory.com (338 anahtarin tamami) | `info/firmware/` = Javelin_S4, PCUSBWAC*, Valkyrie, burstfirmware. **P300/P320 firmware YOK.** |
| Patriot | patriotmemory.com Wayback CDX (400 kayit) | Sadece 2011 forum konulari (SandForce donemi) |
| ORICO | orico.cc/index/attachment/index.html — 5 sayfa × 13 kategori TAM tarandi (48 dosya) | Hepsi USB koprusu/hub/kart okuyucu surucusu. **SSD firmware YOK.** |
| ORICO | orico.cc + oricogroup.com Wayback CDX (100+12 kayit) | Ayni: enclosure/RAID/Bluetooth. SSD YOK. |
| GiGimundo | gigimundo.com (Shopify; sitemap+products.json), gigimundo.cn `download/index?file_type_id=1..8` | .cn API "504 不支持直接请求". Shopify'da indirme sayfasi yok. Wayback CDX gigimundo.com/.cn firmware filtresi = **0 kayit**. |
| Yottamaster | yottamaster.com + Wayback CDX (12 kayit) | JMS578/RTL9210B enclosure firmware'leri. SSD YOK. |
| Lexar | lexar.com/global/download/ (Nuxt payload) + Wayback CDX (143) | Sitede NM620/NM610 firmware yok; arsivde sadece kart okuyucu/USB. |
| Lexar | **usbdev /files/lexar/** | **NM610 / NM610 PRO / NS100 firmware updater'lari VAR — bkz [L1]** |
| Silicon Power | silicon-power.com/download/firmware-updates/ | SSD bolumunde sadece "SSD韌體更新軟體使用手冊" PDF. UD70/A60/US70 firmware YOK. |
| Silicon Power | Wayback CDX (310) | A80/Diamond D03 (harici disk) + `SSD_Firmware_Update_Software_EN.rar` (link olu, 404) |
| Team Group | support.teamgroupinc.com/en/support/download.php | **Sistem bakiminda** (12 Eyl 2026 itibariyla kapali). Wayback CDX: firmware kaydi 0. Onceki kol: sadece MP34 (Realtek) araci vardi. |
| Apacer | apacer.com/en/download/personal-downloads + Wayback CDX (279) | Listede sadece PDF/eDM. Arsivde AU/AS/CD/CP serisi USB+SATA firmware'i; **MAP1202 yok.** |
| Kingston | kingston.com (403 Akamai, WebFetch de 403) · media.kingston.com/support/downloads/ (bos) · Wayback CDX (14) | Erisilemedi / SSD firmware bulunamadi. **DOGRULANAMADI.** |
| Verbatim | verbatim.com/support/, verbatim-europe.com/en/support, Wayback CDX (75+28) | Indirme dizini bos; arsivde sadece 2000'lerin CD/DVD yazici firmware'i. **Vi3000 firmware YOK.** |
| Fikwot | fikwot.net (Shopify) — /pages/support, /pages/download 404; Wayback CDX = 0 | Destek/indirme sayfasi hic yok. |
| Goodram | goodram.com/en/download/ + Wayback CDX (152) | `GOODRAM-SSD-firmware-updater_20211026.zip` (21,3 MB) **indirildi** -> ici `ATA Basic Tool.EXE` (FW ISP Tool, RMA Tool). 397 kaynak cikarildi: `MAS09_FWTAG` 0, `MAP1202` 0, `MKSSD` 0. **SATA araci.** Ayrica Firmware_PX500 = SM2263XT. |
| Hikvision/HIKSEMI | hiksemitech.com/en/hiksemi/support/download.html + Wayback CDX (14) | Sadece spec PDF + MagicalBox/MDR1/RGB yazilimi. E3000 firmware YOK. |
| Emtec | emtec-international.com/en/firmware | Sadece Movie Cube medya oynatici + P600 WiFi HDD firmware'i. **SSD firmware YOK.** |
| Integral | integralmemory.com/support (/downloads/ 404) | Indirilebilir SSD firmware bulunamadi. |
| PNY | pny.com/support/downloads -> 404 sayfasi | Indirme merkezi bulunamadi. **DOGRULANAMADI.** |
| Origin Storage | originstorage.com (Cloudflare 403), origin-storage.com (000) | Erisilemedi. **DOGRULANAMADI.** |

## 5. ARAC/YONTEM NOTLARI (sonraki kollar icin)
- **WebSearch kotasi 200/200 DOLU** — bu oturumda arama araci yok.
  Denenen alternatifler: Bing (zehirli), DDG lite/html (202 challenge), Mojeek (captcha),
  Brave (429), Ecosia (403), Yahoo (000), AOL (404), searx.be/priv.au/searxng.site/
  tiekoetter/paulgo/opnxng/rhscz (429 veya bot-duvari), disroot (Anubis bot-check),
  stract (404), yep (403), 4get.ca (bos), marginalia (indeks cok kucuk),
  **Baidu ILK sorguda calisti, sonra 302 ile kapandi** (cookie jar da kurtarmadi),
  **Naver `search.naver.com/search.naver?where=web&query=` CALISIYOR** ama alaka cok dusuk;
  yine de `acerstorage.com`'u bu buldu — son care olarak kullanilabilir.
- **Wayback CDX aralikli kesiliyor** ("Internet Archive: Temporarily Offline"). Ayrica
  `curl` URL globbing'i `[Ff]irmware` gibi filtreleri BOZUYOR -> **`curl -g` sart** (yoksa exit 3,
  cikti dosyasi hic olusmuyor, sessiz hata).
- **usbdev sadece /files/maxio/ degil, MARKA bolumlerinde de firmware barindiriyor.**
  Sitemap'ten cikarilan tam liste: `hyv6/updater/_dl/usbdev_all.txt` (1270 sayfa).
  Halen bakilmamis, MAP1202 olma ihtimali dusuk ama sifir olmayan bolumler:
  `apacer/apacertoolbox`, `kingston/kssdmanager` (14 arsiv), `siliconpower/spssdupdatetool`
  (Phison), `team/tgsmarttool` (9 surum), `goodram/smartgoodram`, `fanxiang/fxdssdmanagement`.
- station-drivers.com'da "maxio"/"MAP1202" = 0 sonuc (Joomla finder ile arandi). ELENDI.
- ssd-tester **bolgesel siteleri** (.com/.co.uk/.fr/.es/.it/.nl/.pl/.in/.au) tarandi:
  .au'da 516 sayfa, digerlerinde .au'da olmayan sadece 19 sayfa (hepsi "achtung_fake" uyarisi).
  .au'daki TUM MAP1202 fid'leri: AIQZCADC(Taimi Vulcan 256GB=**Hynix V7**), KC1UCA4H, KC2RCELC,
  KCIUCA4H, KRRHCE2C, KTH1CA2C, MCB6AA3H, MCB6BA4H, OOPVCP2C/OOPVCP3C(Taimi Vulcan 512GB/1TB,
  bilinmeyen `PV` oneki). **`?I0P????` YOK.**
  Yeni model: **Taimi Vulcan** — MAP1202'li, 256GB'si Hynix V7. 512GB/1TB'nin `PV` oneki
  su ana kadar hic gorulmemis bir NAND; kimlik kolu bakabilir.

## 6. YEREL DOSYA HARITASI
  hyv6/updater/adata_legend750/      12 SYS bin + Update.ini (ADATA, siniflandirildi)
  hyv6/updater/lexar_nm610pro/       3 sifreli .pkg (NM610 PRO 500GB/1TB/2TB)
  hyv6/updater/lexar_nm610/          2 sifreli .pkg (NM610, NM610P — 3.465.728 B)
  hyv6/updater/arch/                 indirilen ham arsivler (Lexar x5, GOODRAM, Biwin 432 MB)
  hyv6/updater/x/                    acilan agaclar (lexar, lexar_pro, lexar_ns100, goodram*)
  hyv6/updater/_dl/                  HTML/CDX/arama ham ciktilari, usbdev_all.txt, sstau/, sstall/
  hyv6/updater/tea_crack.py          hedefli TEA/XTEA anahtar denemesi (basarisiz)
  hyv6/updater/tea_sweep.py          tam-exe TEA/XTEA anahtar taramasi (arka planda) -> tea_sweep.log
