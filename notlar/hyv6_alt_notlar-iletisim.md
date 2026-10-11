# HYV6 — Iletisim kanallari TESPITI
Tarih: 2026-09-12 | Makine: T440 yerel | ssh/kaplikaya/donanim TEMASI YOK
DURUM (12 Eylul): SADECE TESPIT YAPILDI. Hicbir forma gonderim, hicbir e-posta, hicbir WeChat/QQ,
hicbir Aliexpress/Tmall satici mesaji GONDERILMEDI. Tum istekler salt-okunur GET.

## ⭐ GUNCELLEME 20 Eylul + 11 Ekim — TEMAS ARTIK KURULDU
- **20 Eylul 2026, 10:10 ve 11:06** (Alperen'in hesabindan, bu notlardan BAGIMSIZ/once): iki mail
  atilmis — `support@jamesdonkeylab.com` (554, adres yok, domain gercek degil jamesdonkey.com.cn'e
  gore) ve `support@incehesap.com` (550 5.4.1, kutu kabul etmiyor). **IKISI DE BOUNCE etti** — Alperen
  "önceki ler geri dönmemişti" derken bunu kastetmis; sebep YANLIS ADRES, cevapsiz insan degil.
- **11 Ekim 2026, ~15:20** (Alperen'in acik izniyle, bu oturumda): DUZELTILMIS hedeflere yeniden
  gonderildi:
  1. `destek@incehesap.com` (asil `support@` degil — Alperen'in kendi gelen kutusundaki GERCEK
     siparis/kargo mailleri bu adresten geliyor, dogrulandi) — ayni icerik (sipariş no 4054073 eklendi).
  2. `contact@maxio-tech.com` (Cc: `sales@maxio-tech.com`) — bu bolumde yillardir dogrulanan MAXIO
     Service/Sales adresleri, bugun tekrar canli dogrulandi (WebFetch, ayni 3 adres). Tam FlashID
     (AD 7E 29 53 02 B0) + NAND string verildi, net tek istek: HYV6 MP/Sorting Tool paketi ya da
     sadece SKV6 sistem firmware binary'si.
  - **GiGimundo/ORICO denenmedi** — bir arastirma fork'u `support@gigimundo.com` onerdi ama bagimsiz
    WebSearch ile DOGRULANAMADI (resmi site/adres bulunamadi) — tahmini/uydurma adrese mail
    GONDERILMEDI, bu proje kuralina gore (adres asla tahmin edilmez).
  - Sonuc bekleniyor, bu dosyaya sonraki guncelleme eklenecek.

===============================================================================
## A) MAXIO / 联芸科技  (Maxio Technology (Hangzhou) Co., Ltd.)
===============================================================================
### Sirket kimligi (dogrulanmis)
- Borsa: **Shanghai STAR Market (科创板) — kod 688449**  DOGRULANDI
  Kanit: `https://hq.sinajs.cn/list=sh688449` -> `var hq_str_sh688449="联芸科技,60.200,...,2026-09-11"`
- Halka arz tarihi 2024-11-29, ihrac fiyati 11,25 CNY, 787 calisan, kurulus 2014-11-07
  Kanit: eastmoney F10 `https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax?code=SH688449`
- Yasal ad: 联芸科技(杭州)股份有限公司 / Maxio Technology(Hangzhou)Co., Ltd.
- Merkez: 浙江省杭州市滨江区西兴街道阡陌路459号C楼C1-604室 (posta kodu 310059)
- Yonetim: baskan/temsilci 李国阳 · yon.kurulu bsk 方小玲 · **董秘 (board secretary) 钱晓飞** ·
  证券事务代表 尤文韵

### DOGRULANMIS E-POSTALAR (hepsi @maxio-tech.com)
Not: Bu adresler SADECE sitenin **Ingilizce** surumunde var. Cince surumde HIC e-posta yok.
| Kanal | Adres | Telefon | Kaynak (dogrulanmis) |
|---|---|---|---|
| Maxio Sales | sales@maxio-tech.com | 0571-85892512-8011 | maxio-tech.com/about/contact/?cur_lang=en HTTP 200, sayfada "Maxio Sales / Sales" blogu |
| Maxio Service | contact@maxio-tech.com | 0571-85892512 | ayni sayfa, "Maxio Service / Service" blogu |
| HR | hr@maxio-tech.com | 0571-85892512 | ayni sayfa, "Recruitment Contact / HR" blogu |
| Yatirimci iliskileri (IR) | ir@maxio-tech.com | 0571-85892516 (faks 0571-85892517) | eastmoney F10 ORG_EMAIL alani (borsaya beyan edilen resmi kayit) |
- MX kaydi: `maxio-tech.com. MX 5 mail.maxio-tech.com` -> domain kendi mail sunucusunu calistiriyor,
  adresler canli.
- **fae@ / support@ / tech@ adresi HICBIR YERDE gorulmedi** (siteyi + F10 kaydini taradim).

### Web kanallari
| Kanal | URL | Durum | Bireysele acik mi |
|---|---|---|---|
| Resmi site (CN) | https://www.maxio-tech.com/ | HTTP 200 | evet (salt okunur) |
| Resmi site (EN) | https://www.maxio-tech.com/?cur_lang=en | HTTP 200 | evet |
| Iletisim (CN) | /about/contact/ | HTTP 200 — 6 ofis, SADECE adres+telefon, e-posta YOK | — |
| Iletisim (EN) | /about/contact/?cur_lang=en | HTTP 200 — yukaridaki 3 e-posta BURADA | evet |
| Dokuman talep formu 索取资料 | /product/document.html | HTTP 200; POST /jsapi/message/inquire | **HAYIR — B2B** |
| Technical Support | /support/ | HTTP 200 ama ICI BOS | — |
| /support/11828/ (SSD Controllers) | HTTP 200 | sadece breadcrumb, indirilecek dosya/login YOK | — |
| /support/11691/ (Embedded) | HTTP 200 | "Coming soon" | — |
| /support/12942/ (Network) | HTTP 200 | bos | — |
| Kariyer | /job/ , /job/11647/ | HTTP 200, 20+ ilan | ilanlarda e-posta YOK |
| /support (slash'siz) | HTTP 404 | — | — |
| www'suz maxio-tech.com | DNS COZULMUYOR | — | — |
| /en/ | HTTP 404 (dil `?cur_lang=en` ile) | — | — |
- Resmi WeChat: sayfa altinda "官方品牌微信 / Official wechat" QR var (goruntu; ID metni yok).
- **Distributor/reseller listesi YOK** — navigasyonda boyle bir bolum bulunmuyor.
- **Yatirimci iliskileri sayfasi sitede YOK** (IR e-postasi borsa kaydindan geldi).

### Dokuman talep formu (索取资料) — zorunlu alanlar
POST hedefi: `/jsapi/message/inquire` (csrf_token'li). Alanlar:
isim* · **SIRKET e-postasi*** · **SIRKET adi*** · **SIRKET telefonu*** · sehir* · ulke* ·
posta kodu · ilgi alani* · "咨询问题/计划" aciklamasi* · pazarlama onayi (evet/hayir)
=> Ulke listesinde Turkiye de var. Ama form bireysel kullanici icin degil, sirket lead formu.

### Yanlis izler (kontrol edildi)
- maxiotech.com -> HTTP 200 ama **domain park/lander sayfasi**, MAXIO degil.
- maxiotek.com -> HTTP 403 Cloudflare challenge (icerik gorulemedi).
- maxio.com.cn -> baglanti yok (000).

### "MAXIO'dan tool istedim" kaniti aradim — BULAMADIM
Baktigim yerler:
- usbdev.ru WP arama (`wp-json/wp/v2/search?search=maxio`, 40 sonuc) — 29 Maxio arac sayfasi var,
  hicbirinde "ureticiden aldim" ifadesi yok.
- usbdev.ru MAP1202 MPTool sayfasi (`/files/maxio/map1202mpsortingtool/`) 22 yorumun tamami okundu:
  yorumcular usbdev arsivindeki paketleri kullaniyor; NAND ID'sini degistirip baska paket
  yaziyorlar ("Оживил HVY7 прошивкой SSD Reletech на 2ТБ... пришлось изменить айди чипа").
  MAXIO ile temas eden TEK BIR yorum yok.
- Reddit: `old.reddit.com/search.json` -> 302 sonra HTML; `www.reddit.com/search.json` -> HTTP 403.
  **Reddit'e ERISEMEDIM**, "yok" diyemem.
- rossmanngroup.com wp-json -> HTTP 403; board./forum.rossmanngroup.com -> DNS yok (000).
  **Rossmann'a ERISEMEDIM.**

===============================================================================
## B) JamesDonkey / 贱驴
===============================================================================
### Domainler
| Domain | HTTP | Not |
|---|---|---|
| **www.jamesdonkey.com.cn** | **200** | TEK CALISAN resmi site. Heidian (heyshop) magaza platformu. |
| jamesdonkey.net | 000 | SSL handshake failure |
| jamesdonkey.com | 000 | baglanamadi |
| jamesdonkey.cn | 000 | DNS cozulmuyor |
| jianlv.com | 000 | baglanti yok |
- MX: `jamesdonkey.com.cn -> mx1/mx2/mx3.feishu.cn` => kurumsal Feishu (Lark) e-postasi VAR,
  ama **yayinlanmis bir adres yok** (site tamamen JS ile render ediliyor, sunucu tarafinda metin yok).

### Site icerigi (dogrulanmis)
- Meta aciklama (sunucudan gelen tek metin):
  "JamesDonkey（贱驴）创立于2014年，坚持原创设计，专注**机械键盘、电竞鼠标等外设产品**"
  => 2014 kurulus, **mekanik klavye + oyuncu faresi + cevre birimi**. SSD'den soz YOK.
- sitemap.xml (HTTP 200) tam urun listesi — 16 urun, hepsi klavye/fare:
  A3HE, A3, a3v2, R3TMR8K, RSR7, RSR5, NV60, r2p, R2, S2, S1, weilan, weialn, guiqi
  **HIC SSD YOK.**
- Sayfalar: /page/contact (联系我们), /page/about, /page/guides (购买指南), /page/privacy, /page/terms
  Hepsi HTTP 200 ama **govde client-side render** — curl ile sadece baslik+meta geliyor.
  Mobil UA ile de ayni. Heidian JS'de sadece `/api/clients/wechat-auth-url/` endpoint'i var
  (WeChat girisi destekli => WeChat tabanli musteri hizmeti muhtemel ama ID gorulemedi).
  **Iletisim sayfasinin ICERIGINI OKUYAMADIM** (JS gerekiyor; headless tarayici acmadim).

### SSD kolu var mi — UC BAGIMSIZ KAYNAK: HAYIR
1. Kendi magazasinin sitemap'inde SSD yok (yukarida).
2. Taobao oneri API (`suggest.taobao.com/sug`), calisti:
   - `贱驴` -> 贱驴键盘, 贱驴rs2, 贱驴rsr5, 贱驴鼠标, 贱驴a3, 贱驴s2, 贱驴rsr7, 贱驴s1, 贱驴r2, 贱驴nv60
     (hepsi klavye/fare modeli — kendi sitesindeki model adlariyla birebir ayni)
   - `贱驴固态` -> **bos** · `贱驴 ssd` -> **bos** · `JD1024` -> **bos**
3. AliExpress (HTTP 200, gercek sonuc dondu):
   - "jamesdonkey ssd" -> JamesDonkey SSD YOK, sadece alakasiz SSD urunleri
   - "jamesdonkey" -> "Jamesdonkey RSR7 Kablosuz Bluetooth Fare" (fare). Baska JamesDonkey urunu yok.
   => AliExpress'te **resmi JamesDonkey magazasi tespit edemedim**; RSR7 fareyi satan
      ucuncu-taraf saticilar var (onlarin mesajlasmasi acik ama marka degil, satici).
4. usbdev.ru WP arama: `donkey` -> 0, `JD1024` -> 0, `贱驴` -> 0.

### Erisemediklerim (yok demiyorum)
- JD.com (search.jd.com): HTTP 200 ama tamamen SPA, sonuc HTML'de yok. Magaza VAR MI bilinmiyor.
- Tmall: jamesdonkey.tmall.com ve jianlvkeji.tmall.com -> `*.world.tmall.com/shop/view_shop.htm`
  adresine yonleniyor, oradan 2,4 KB'lik bot-korumasi shim sayfasi geliyor (icerik yok).
  jianlv.tmall.com -> `store.taobao.com/shop/noshop.htm` = KESIN YOK.
  Diger ikisi icin **karar veremedim**.
- smzdm.com -> HTTP 202 (challenge). eBay -> HTTP 403.
- Garanti suresi / RMA sureci / satis sonrasi (售后) kanali: **hicbir yerde metin gorulemedi**
  (iletisim sayfasi JS'li, marketplace sayfalari bot korumali).

===============================================================================
## C) VERI KURTARMA / PROFESYONEL ARACLAR
===============================================================================
### ACE Lab PC-3000 — KESIN CEVAP: MAP1202 DESTEKLENMIYOR
- Site: https://www.acelab.eu.com/ HTTP 200. Tel +420 222-361-605. TS portal https://ts.acelab.eu.com/
  (acelab.eu / pc-3000.com / acelaboratory.com -> 000, calismiyor; dogru domain `.eu.com`)
- Urun sayfasi /pc3000-SSD.php HTTP 200. PC-3000 SSD, PC-3000 Portable PRO / Express / UDMA
  donaniminin uzerine calisan bir YAZILIM eklentisi. NVMe M.2 **sadece Portable III / Portable PRO**
  ile calisiyor. Kapasite araligi 32 GB - 2 TB.
- Desteklenen model listesi ver. 3.9.8, 2026-07-15 guncel:
  https://blog.acelab.eu.com/pc-3000-ssd-list-of-supported-ssd-drives-regularly-updated.html
  Bolum basliklari (tam liste):
    NVMe: Silicon Motion / Phison / Marvell
    SATA: Silicon Motion / Phison / **Maxio** / Marvell / Samsung / Indilinx / OCZ Barefoot 3 / Intel
  - "Maxio" gecen TEK satir: **"SATA Maxio controlelr family:"** (sic, yazim hatali)
  - Altinda 48 giris: sadece **MAS0902 / MAS0901 / MAS1102** (SATA).
  - **"MAP1" arama sonucu: 0 HIT.** MAP1202/MAP1602 (NVMe Maxio) listede YOK.
  - Ayrica blog yazisi "PC-3000 SSD. Maxio MAS0902A/DM918 recovery process" (2026-02-09) — yine SATA.
  - Blog WP arama: `posts?search=MAP1202` -> n=0.
- Fiyat: sitede fiyat YAYINLANMIYOR. /order-demo.php ve "Get Quotation" formu var; alis
  bayi (Resellers) uzerinden ve teklif ile. Bireysel satin alma teorik olarak mumkun ama
  PC-3000 Portable PRO + SSD yazilimi tipik olarak 5 haneli USD; bir diski kurtarmak icin anlamsiz.

### Soft-Center (soft-center.ru) — ILGISIZ
- https://soft-center.ru/ HTTP 200. Bu bir **Moskova BT sirketi** (1C yazilimi, Dr.Web bayiligi,
  su/domofon abonelik yazilimlari) + /datarecovery/ hizmet sayfasi.
- SSD kurtarma HIZMETI satiyorlar (fiyat listesinde "SSD 20.000-30.000 RUB"), telefon
  +7 (495) 241-02-86. **SSD utility/MPTool URETMIYORLAR.** Sitede "Maxio"/"MAP1" gecmiyor (0 hit).

### Diger profesyonel arac ureticileri (bonus, ben ekledim)
| Vendor | URL | Durum | MAP1202 |
|---|---|---|---|
| Dolphin Data Lab (DFL) | https://dolphindatalab.com/ | HTTP 200, WordPress | `posts?search=maxio` -> **0**, `MAP1202` -> **0** |
| MRT Lab | https://www.mrtlab.com/ | HTTP 200 ama WordPress degil | arama yapilamadi, **bakamadim** |
| SalvationDATA | https://www.salvationdata.com/ | HTTP 200 | icerik taranmadi |
| Rossmann Group | https://rossmanngroup.com/ | wp-json HTTP 403; board./forum. subdomainleri DNS yok | **ERISEMEDIM** |
