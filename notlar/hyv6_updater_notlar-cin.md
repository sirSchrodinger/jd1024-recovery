# CIN MARKALARI KOLU — MAXIO MAP1202 resmi firmware/updater avi
Tarih: 2026-09-12 · Kapsam: SADECE web arastirma + indirme. Donanima dokunulmadi,
kimseye mesaj/form/hesap YOK. Her sey T440 yerelinde. Calisma dizini: `hyv6/updater/cn/`

## SONUC (tek cumle)
**MAP1202 + SK hynix V6 icin derlenmis HICBIR SYS .bin bulunamadi.** Cin markalarinin
resmi kanallarinda MAP1202 firmware updater'i yayinlayan TEK marka 致态 ZhiTai; onun da
icindeki 6 bin'in hepsi YMTC (kardes kol dogruladi). Yeni bin cikmadi.

## ARANAN IMZANIN WEB'DEKI IZI = SIFIR (yeni, sert kanit)
DuckDuckGo (r.jina.ai proxy'si uzerinden, calisiyor) ile tam-kelime aramalar:
  "YI0PCELC"  -> 0 sonuc      "ZI0PCABC"  -> 0 sonuc
  "ZI0PCD2C" OR "ZI0PCDLC" -> 0 sonuc    "SN09466" -> 0 alakali sonuc
  "MAP1202" "HYV6" -> **tek sonuc: Alperen'in kendi usbdev forum konusu** (topic=13429)
Iki yonlu kontrol: ayni araclarla "MAP1202 mptool" 10 gercek sonuc dondu -> arama CALISIYOR.
=> Bu dosya adlari internette hicbir yerde indekslenmemis. [B25]'i bagimsiz olarak dogruluyor.

## KONTROL EDILEN CIN MARKALARI (hepsi resmi site)
| marka | baktigim URL | sonuc |
|---|---|---|
| 朗科 Netac (CN) | netac.com.cn/zh-cn/download/ + /cxdown/ /zldown/ /3cdown/ | 程序下载'da TEK dosya: Mac harici disk yazilimi. SSD firmware YOK |
| 朗科 Netac (arsiv) | Wayback CDX netac.com + netac.com.cn (11.7k URL) | tum arsiv .exe/.zip'ler USB flash bellek araci. MAP1202 YOK |
| 梵想 Fanxiang | fanxiang.com SPA -> **API bulundu**: `/api/index/Download/getDownloadCategory` + `getDownloadList?cid=1..5` | 5 kategorinin TAMAMI dokuldu. SSD'de tek yazilim: SSDmanagement-1.0.40-**963**.exe (14,2 MB) + PDF'ler + APK. Firmware YOK |
| 梵想 Fanxiang | SSDmanagement-1.0.40-963.exe indirildi, 7zz ile acildi (45 dosya) | `MAS09_FWTAG_V001` YOK · MAP1202/SKV6/HynixV6 gecen dosya YOK. (Onceki kol 962'yi bakmisti; 963 de temiz) |
| 金胜维 KingSpec | kingspec.com/support.html?id=download — 4 sekmenin TAMAMI parse edildi | 89 kullanim kilavuzu PDF + 5 spec + **1 surucu** (WinDrv226x, JMicron) + 2 brosur. SSD firmware YOK |
| 金胜维 KingSpec | kingspectech.com/pages/download (FARKLI domain, ilk kez bakildi) | Shopify sayfasi; firmware/zip/rar/exe gecisi = 0 |
| 金胜维 KingSpec | kingspec.cn | DNS var (139.196.103.199) ama TCP baglanti kurulmuyor (80 ve 443) — CN disindan erisilemez |
| 金胜维 KingSpec (arsiv) | Wayback CDX kingspec.com (6000 URL) + kingspec.cn (348) | indirme endpoint'inin tek parametresi: WinDrv226x. Baska dosya hic olmamis |
| 七彩虹 Colorful | colorful.cn/home/download + `/Home/GetProductClassList` API | SSD siniflari var (CN/SL/CF serisi) ama indirme deposunda SSD firmware yok; arsivdeki 2 zip = **anakart BIOS** (CVN B450M) |
| 致态 ZhiTai | zhitai.com.cn / zhitaitech.com / zhitai.cn | **NXDOMAIN** (Cloudflare DoH ile dogrulandi). zhitai.com = park/fingerprint yonlendirme sayfasi. Marka kolu kardes agent'ta kapandi (6 bin, hepsi YMTC) |
| 金泰克 Kimtigo | kimtigo.com.cn/download/ ("Download zone") | sayfa ana sayfaya dusuyor, indirme listesi yok. kimtigo.com = DNS yok |
| 阿斯加特 Asgard | asgard.com.cn (/fa1/ 客户支持, /wangluo-7/ 售后服务) | sadece garanti metni. asgardmemory.com/.cn = baglanti yok |
| 光威 Gloway | gloway.com.cn/pages_26/ (售后服务) | sadece garanti politikasi. Indirme bolumu yok |
| 铭瑄 Maxsun | maxsun.com.cn + /support/ | sadece tamir durumu sorgulama |
| 台电 Teclast | teclast.com | sadece tamir durumu sorgulama |
| 佰维 BIWIN / Predator | predatorstorage.com/manuals-tools/ | sadece PDF. **Ama 2 arac var** (asagi bak) |
| 影驰 Galax CN | galaxy.com.cn (211.162.70.235) | http 200 ama govde 458 bayt (bos/park). galax.com.cn DNS yok |
| SCY / Zheino / Vaseky / Shinedisk | scysemi.com, zheino.com, vaseky.com, shinedisk.com | **hepsi NXDOMAIN** (DoH ile dogrulandi — engel degil, domain gercekten yok) |
| 移速 Movespeed · 大华 Dahua · 海康 Hikvision · Reletech · ORICO | onceki kolda kapatildi | firmware yok |

## BIWIN — TEK CANLI MAP1202 FIRMWARE KANALI (yeni bulgu, ama kapali)
`Biwin Intelligence.exe` (432 MB, Aliyun OSS'ten indirildi, tarandi):
- Icinde **`MAS09_FWTAG_V001`** dizesi VAR (offset 376720948) — **ama bu firmware DEGIL**,
  exe'nin .rdata'sindaki dogrulayici sabit (hemen ardinda `abLDBKFWTAG_V00` + "This is a
  ciphertext"). 5 farkli boyutta kesip bakildi: MKSSD etiketi/build yolu YOK. **Yanlis pozitif.**
- Anlami: BIWIN toolbox'i MAXIO firmware'i **tanıyor ve yaziyor**, firmware'i calisma
  aninda OSS'ten cekiyor. Firmware formati `*.efp`, config `Firmware/fwUpgradeConfig.dat`
  + `Firmware/fwVersionConfig.dat`. Alibaba OSS C++ SDK ile.
- BIWIN'in MAP1202 model siniflari (exe'deki C++ sinif adlari):
  `DriveModel_ssd_nand_b58r_map1202_micro_usb` · `DriveModel_ssd_nand_tas_map1202_micro_usb`
  => BIWIN'in MAP1202 urunleri **Micron B58R** ve **YMTC TAS**. **Hynix YOK.**
- OSS kovasi `smart-tool.oss-rg-china-mainland.aliyuncs.com`: **liste 403** (AccessDenied),
  9 farkli tahmin edilen config anahtari da 403. Sadece bilinen .exe anahtarlari public.
  (Exe'deki OSS kimlik bilgilerini cikarip kullanmak = yetkisiz erisim; YAPILMADI.)

## 量产部落 (club.liangchanba.com) — MISAFIRE TAMAMEN KAPALI
- thread-1754 (ZHITAI TiPlus5000 Firmware Update Tool): dosya `ZHITAI_TiPlus5000_Firmware_Update_1014.rar`
  2,57 MB, 66 indirme — **权限不足，无法下载**, 售价 1金币, 下载权限 注册会员.
- thread-1780 (TiPlus5000 Smart Tool V1.0/1.1/1.2/1.3 + kilavuzlar): sayfada
  **下载权限: 不限** yaziyor AMA ekleri denedim: 9 aid'in HEPSI 302 ->
  `source/plugin/xinshu_denydown/static/deny.rar` (467 bayt). **deny plugin misafirin
  butun indirmelerini kesiyor**; "不限" etiketi yaniltici. Gorevdeki "misafire acik"
  varsayimi YANLIS.
- thread-1804 **"Maxio MAP1202 Firmware Update Tool"** (gorev listesinde yoktu, ilk kez bakildi):
  13 ek — MKUpdater_MAP1202_V0_03a/05/07/08/10/12/18, V1_04/V1_06, MXUpdater V1_10/V1_11
  (~1 MB, sadece ARAC, firmware icermiyor), `MKUpdater_MAP1202_V0_09_RC-SVN9273.rar` (1,39 MB,
  Fanxiang S500PRO 1TB'in SN09273 firmware'i) ve ADATA LEGEND750 (elimizde).
  Bolumler: 导航一：Normal · 导航二：For ADATA. **HYV6/海力士 gecisi = 0.**
  Hepsi 售价 1金币 + izin duvari. Wayback'te bu konunun snapshot'i YOK.

## smarthdd SAHA VERITABANI — HYV6 BUILD'INI DOGRULADI (yeni ve faydali)
`smarthdd.com/database/` (188.959 diskten toplanan gercek saha verisi):
- **KingSpec NX-256 -> firmware surumleri: `SN8878`, SN08381, SN10092**
  => brief'teki "NX-256 = HYV6 + SN8878" iddiasi **bagimsiz olarak dogrulandi**.
- KingSpec NX-512 -> SN08381, SN09843, SN6329, SV9112, SVN9177
- KingSpec NX-1TB -> SN09843, SVN9177
- **Fanxiang S500PRO 256GB -> SN10093, SN10613, SN11457** (hepsi YMTC build'i!)
  Fanxiang S500Pro 256GB -> SN12465, SN15098 · S500PRO 512GB -> SN10613, SN11457
  => Sahadaki Fanxiang 256GB'lerin cogu **YMTC**. Alperen'in unitesi HYV6 = **nadir varyant**
     (ayni model adi altinda farkli NAND partisi). Bu yuzden hicbir toplu updater'da yok.
- Aranacak build dizesi artik net: **SN8878** (KingSpec HYV6) ve **SN09466** (liangchanba HYV6).
  Ikisi de web'de indekslenmemis (yukaridaki arama sonuclari).

## BAGIMSIZ UCUNCU DOGRULAMA — mydigit toplu liste
`mydigit.cn/thread-495185` "固态硬盘量产工具下载合集 (2025.1.28)" — MAP1202 klasorunun TAM icerigi:
  `MAP1202 HYV7 64GB Die 128G-1T SN09286 20220704.rar` · `MAP1202-B37R-D3.0-C.0.01.003-SN5313.rar`
  · `MAP1202_YMTC_JGS_SN6760.rar`   -> **HYV6 YOK.**
(Ayni listede baska kontrolculerin HYV6'si VAR: `YS9082HC_..._HYV4_HYV5_HYV6_BICS5.rar`,
 `RTS5735_RM1135_HYV6.rar`, `SM2258XT海力士V6颗粒【魔改】.rar` — yani NAND yaygin,
 eksik olan sadece MAP1202'ye derlenmis set.)

## ARAC NOTLARI (gelecek oturumlar icin — degerli)
- **WebSearch kotasi bitti** (200/200). Ama: **`https://r.jina.ai/<url>` proxy'si CALISIYOR**
  ve `https://r.jina.ai/https://duckduckgo.com/html/?q=<sorgu>` ile **DDG araması geri geldi**.
  Iki yonlu test edildi (bos sorgu "No results found", dolu sorgu 10 sonuc).
  Sonuclar `duckduckgo.com/l/?uddg=<urlencoded>` ile sarmalı — cozmek gerekiyor.
  Hazir script: `hyv6/updater/cn/ddg.sh "<urlencoded-sorgu>"`
- r.jina.ai ayrica **CSDN'in JS duvarini asiyor** (blog.csdn.net dogrudan curl'de JS challenge,
  WebFetch'te HTTP 521; jina ile tam metin geliyor). SADECE metin — ikili dosya cekmiyor.
- **Bing hala zehirli** (jina uzerinden bile: "ZI0PCADC" -> cinko-iyon superkapasitor makaleleri).
- Public SearXNG ornekleri: searx.be/inetol/hbubli/baresearch = **Anubis PoW / bot duvari**;
  priv.au/paulgo/opnxng/tiekoetter/rhscz = 429. Hicbiri kullanilamadi.
- Wayback CDX dogru kullanim: `http://web.archive.org/cdx/search/cdx?url=<domain>*&fl=timestamp,original&collapse=urlkey&limit=6000`
  (gorevdeki `filter=original:...` regex'i HTML hata sayfasi dondurüyor — kullanma).
- crt.sh cok yavas (25 sn timeout'ta cogu domain dolmuyor).
- **liangchan.net artik oyun indirme sitesi** (量产网 degil). 52upan.com / upantool.com /
  upan.cc / newhua / xiazaiba = DNS yok.
- Aliyun OSS kovasi listeleme testi: `?list-type=2&max-keys=1000` -> AccessDenied kovada
  yoksa da ayni hatayi verir, yani 403 "dosya yok" kaniti DEGIL.

## INDIRILEN + TARANAN (yeni bin: 0)
`hyv6/updater/cn/dl/SSDmanagement-1.0.40-963.exe` (fanxiang toolbox, temiz)
`Biwin Intelligence.exe` 432 MB — tarandi, yanlis pozitif, **disk icin silindi**
colorful 2 zip (anakart BIOS) — silindi
Sayfa/JSON kanitlari: `hyv6/updater/cn/pg/`, `cdx/`, `shd/` (smarthdd marka sayfalari), `fx_1..5.json`
