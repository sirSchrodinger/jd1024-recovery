# JD1024 kurtarma — tedarik notları (2026-09-12)

## Kaynak durumu
- WebSearch bütçesi tükendi → curl + WebFetch ile doğrudan site araması yapıldı.
- Fiyatlar sitelerin JSON-LD `offers.price` alanından okundu (KDV dahil liste fiyatı).

## ⭐ ANKARA YEREL: Robo90 (robo90.com)
- Adres: Ostim OSB Mah. Turan Çiğdem Cd. No:35, Yenimahalle/ANKARA
- Saatler: Hafta içi 09:00-18:00, Cumartesi 11:00-14:00
- "Mağazadan Teslim Al" seçeneği VAR (sipariş sırasında kargo yerine seçiliyor) → AYNI GÜN elden alınabilir
- 1500 TL üzeri kargo ücretsiz; aynı gün kargo
- Stokta (InStock, doğrulandı):
  - CP2102 USB-TTL Dönüştürücü Kartı - 3.3V/5V ....... 115,92 TL
    https://www.robo90.com/cp2102-usb-ttl-donusturucu-karti-3-3v-5v
  - FT232RL FTDI USB-TTL Dönüştürücü-Programlayıcı ... 98,53 TL  (3.3V/5V seçilebilir, DTR RXD TXD VCC CTS GND, 36x18mm)
    https://www.robo90.com/ft232rl-ftdi-usb-ttl-donusturucu-programlayici
  - CH340G USB TTL Seri Haberleşme Dönüştürücü ....... 115,92 TL
  - FTDI FT232 USB-TTL UART 5v/3.3v çevirici ......... 144,90 TL
  - ESD Anti-statik Cımbız Seti - 6 Parça ............ 243,43 TL
  - DT-830D Dijital Multimetre (sarı) ................ 173,88 TL / siyah 191,27 TL
  - ANENG AN8205C Dijital Multimetre ................. 347,76 TL
  - XL830L Mini Multimetre ........................... 231,84 TL
  - 40'lı Dişi-Dişi Jumper Kablo 20cm ................ 40,57 TL
  - 4'lü 0.22mm Çok Telli Montaj Kablo - 1 Metre ..... 34,78 TL
  - 8'li Lojik Seviye Dönüştürücü (TXS0108E tipi) .... 86,94 TL
  - ZD30B 30W Kalem Havya ............................ 301,39 TL
- Stokta YOK: tekil ESD-10..15 cımbızlar (28,98 TL), BSS138 lojik çevirici (17,39 TL)
- Robo90'da M.2 NVMe adaptör / sıcak hava istasyonu YOK

## direnc.net (İstanbul, Ümraniye — kargo)
- CP2102 6-Pin USB 2.0 UART TTL Seri Dönüştürücü .... 102,67 TL  (pinler: 3.3V, RST, TXD, RXD, GND, 5V)
- CP2102 USB 2.0 UART TTL HW-598 (5 pin) ............ 106,55 TL  (3.3V, TXD, RXD, GND, 5V)
- CP2102 Micro USB 6 pin ............................ 102,67 TL  (3.3V, DTR, TXD, RXI, GND, 5V)
- USB-TTL CH343G Endüstriyel ........................ 396,65 TL
- FT232 USB-TTL kablo: TÜKENDİ

## motorobit.com (İstanbul, Halkalı — kargo)
- USB to TTL UART CH340G Dönüştürücü Modülü ......... 81,68 TL  InStock (3V3/5V jumper seçimli)
- USB - TTL UART CP2102 Modül ....................... 138,60 TL InStock
- CP2102 USB-TTL Seri Dönüştürücü Modülü ............ 155,92 TL InStock
- CP2102 Micro USB 6Pin ............................. 148,50 TL InStock (DTR RXD TXD 5V GND)
- 3in1 5V/3.3V USB-RS485/RS232/TTL .................. 297,00 TL InStock

## robotistan.com (İstanbul, Başakşehir)
- Ucuz USB-TTL'lerin HEPSİ TÜKENDİ (CH340G 99,28 / CP2102 134,74 / FT232RL 474,53 hepsi OutOfStock)
- Sadece WaveShare CP2102 USB UART 300,79 TL InStock → pahalı, gerek yok

## Teknik karar notları
- CP2102 = donanımsal olarak DAİMA 3.3V lojik (çipin IO'su dahili 3.3V regülatöründen beslenir).
  Jumper yanlış konumda kalsa bile TX'ten 5V çıkamaz → 5V riski SIFIR. Bu iş için en güvenli seçim.
- FT232RL modüllerinde 3.3V/5V jumper VCCIO'yu değiştirir; klon kartlarda bazen sadece VCC çıkış
  pinini değiştirip VCCIO'yu 5V'ta bırakır → SESSİZ 5V riski. Daha ucuz ama daha riskli.
- CH340G jumper'lı modül de aynı riski taşır.
- PL2303: Linux'ta yeni çekirdeklerde HX klonları sorunlu → ALMA.
- FTDI klon "bricking" sorunu sadece Windows sürücüsündeydi; Linux ftdi_sio klonları sorunsuz sürer.
- Linux sürücü durumu: cp210x (CP2102) ve ch341 (CH340) çekirdekte hazır, ekstra kurulum yok.
- ⚠️ 1.8V İHTİMALİ: Bazı NVMe kontrolcülerinin UART'ı 1.8V. 3.3V adaptörün VIH eşiği ~2.3V →
  1.8V sinyali OKUYAMAZ. Önce multimetre ile TX pad'inin boştaki (idle-high) gerilimini ölç.
  Güvenli sıra: önce SADECE RX+GND bağla (dinle), TX'i bağlama. TX'e 1k seri direnç koy.

## Robo90 konum / ulaşım (doğrulandı)
- Turan Çiğdem Caddesi (Ostim OSB, Yenimahalle) → Nominatim: 39.9762, 32.7406
- OSTİM metro istasyonuna (M1 Kızılay–Batıkent hattı) **760 m** yürüme
- Bilkent'ten kuş uçuşu 12 km. Bilkent → Kızılay → M1 metro → OSTİM → 10 dk yürüyüş
- DT-830D multimetre: "Diyot testi bulunmaktadır. Buzzer bulunmaktadır." → süreklilik sesi VAR ✅
  DC 200mV–1000V, AC 200–750V, direnç 200Ω–2MΩ

## MAP1202 MPTool — doğrulanan kaynak
- github.com/dom0ng/map1202 (README + map1202.pdf, 5 sayfa)
- Araç adı: MXMPTool_MAP1202_USB_V0_01_009d.exe · Windows gerekiyor
- Resmî/topluluk rehberi sadece "an M.2 to USB adapter" diyor, ÇİPSET BELİRTMİYOR.
  → "JMS583 şart" iddiası forum bilgisi, yazılı rehberde teyit YOK. Yine de JMS583
    NVMe passthrough'u tam desteklediği için en güvenli bahis.
- Uyumlu olduğu bilinen diskler: fanxiang S500 Pro, Fikwot FN501 Pro, TeamGroup MP33 Pro,
  Verbatim Vi3000, Origin Inception TLC 830 Pro (JamesDonkey JD1024 listede yok ama
  aynı kontrolcü)
- Sorun giderme tablosu: "Drive not recognized / program freezes → yönetici olarak çalıştır,
  BAŞKA USB portu/yuvası dene"

## Engellenen kaynaklar (kayıt)
- trendyol.com, hepsiburada.com → curl ve WebFetch'e Cloudflare 403
- duckduckgo/mojeek → bot challenge; bing → alakasız sonuç
- direnc.net → WebFetch'e 403 ama curl+UA ile 200

## Robo90 iletişim / sipariş
- WhatsApp (sadece yazılı): +90 554 027 03 90 · info@robo90.com
- Sipariş sırasında kargo yerine "Mağazadan Teslim Al" seçilirse ofisten alınabilir
- CP2102 kartı: stok kodu R001556, KDV %20 dahil 115,92 TL (liste 127,51 TL), available:true

## 1.8V araştırması
- robo90 / direnc / motorobit'te 1.8V destekli USB-TTL adaptör YOK.
- Plan B: Robo90'daki 8'li lojik seviye dönüştürücü 86,94 TL (TXS0108E tipi; VccA 1.2-3.6V
  olduğu için 1.8V<->3.3V çevirebilir) — sadece gerekirse.

## akakce "JMS583" araması (fiyat karşılaştırma)
- Türkiye'de "JMS583" kelimesiyle indekslenen TEK ürün: **Hadron HDX1768 Type-C M.2 SSD Kutusu**
  En ucuz 690,36 TL (14 satıcı) — https://www.akakce.com/harddisk-kutusu/en-ucuz-hadron-hdx-1768-m-2-ssd-kutusu-fiyati,645997069.html
- akakce'de "jmicron" / "ASM2362" / "RTL9210" araması sonuç vermedi → TR perakendeciler
  çipset yazmıyor.

## ⭐⭐ İKİNCİ ANKARA MAĞAZASI: Smallman (HDX1768 / JMS583 için)
- Adres: Cevizlidere Cad. No:6 **Balgat, Çankaya, ANKARA** — "Mağazalarımız: Balgat" (fiziksel mağaza VAR)
- Çalışma: Pazartesi–Cuma 09:00–18:00 · Tel 0850 210 9200 · info@smallman.com.tr
- Hadron HDX1768 (JMS583) = **690,36 TL**, schema InStock, "1-2 İş gününde Kargoda"
  https://www.smallman.com.tr/hadron-hdx1768-ssd-kutu-type-c31-usb30-nvme-m2
  (kargo bedava sadece 5000 TL üzeri → +110 TL kargo, ya da mağazadan al)
- Mesafe: Cevizlidere Cad. ≈ Bilkent kampüsüne **6 km** (Balgat/Öveçler). M2 metroda Bilkent
  istasyonu var; Söğütözü 2-4 km. Otobüs/taksi ile 15-20 dk.
- ⚠️ Smallman'ın ÜRÜN SAYFASINDA "JMS583" YAZMIYOR. Çipset iddiası Hadron'un kendi
  açıklamasından ve diğer bayilerden geliyor. Mağazadan alırken kutunun üstünde
  "CHIP JMS583" yazdığını GÖZLE DOĞRULA.
- İkinci Ankara satıcısı: Ofisomi (Eryaman, Yenimahalle/Ankara) 721,74 TL + 99,90 kargo,
  ürün sayfasında "Chipset: JMS583" AÇIKÇA YAZIYOR → çipset kanıtı burada daha güçlü.

## Satın alma sonrası KESİN çipset testi
`lsusb` çıktısında **152d:0583** = JMicron JMS583 (linux-usb usb.ids ile doğrulandı).
RTL9210 olsaydı 0bda:9210 · ASM2362 olsaydı 174c:2362 görünürdü.
Kutu yanlış çipsetle gelirse 14 gün cayma hakkıyla iade.

## ⚠️ SIRALAMA UYARISI — USB-TTL tek başına yetmez
UART log'unu okumak için SSD'nin ENERJİLİ olması gerekiyor. Enerji verecek tek şey:
  (a) bir M.2 NVMe yuvası, ya da (b) USB kutusu/adaptörü.
T440'ta M.2 NVMe yuvası YOK (mSATA var). kaplıkaya şu an dokunulmaz.
=> JMS583 kutusu sadece MPTool için değil, UART oturumu için GÜÇ KAYNAĞI olarak da gerekli.
=> Alperen'in elinde başka M.2 NVMe yuvalı makine yoksa iki parça da AYNI ANDA alınmalı.

## Robo90 CP2102 kartı — ÜRÜN FOTOĞRAFINDAN DOĞRULANDI
- Çip üstünde "SILABS CP2102 DCL00X 1612+" yazıyor → gerçek Silicon Labs CP2102
- USB-A ERKEK fiş (kablo yok, doğrudan porta takılıyor)
- 6 pin ERKEK header, silkscreen: **DTR · RXD · TXD · +5V · GND · 3V3**
- Kartta 3.3V/5V lojik jumper'ı YOK → başlıktaki "3.3V/5V" sadece iki GÜÇ ÇIKIŞ pini demek.
  Lojik seviye CP2102'nin dahili 3.3V regülatöründen sabit → **TX'ten asla 5V çıkamaz**. ✅
- Pinler erkek olduğu için **dişi-dişi jumper** doğru seçim (bir ucu kesilip SSD pad'ine lehimlenir)

## Ofisomi (Ankara/Eryaman) — çipset iddiası BAĞIMSIZ TEYİT (kendim doğruladım)
Ürün sayfası metninde birebir: "– Chipset: JMS583 yüksek performans kontrolleri"
Ayrıca: NVMe M.2 (M-Key/B+M Key), USB Type-C 3.1 Gen2 & USB 3.0, 10 Gbps,
"Tool-free (alet gerektirmeyen) montaj", 2230/2242/2260/2280
Fiyat 721,74 TL · schema InStock · "hafta içi 16:30'a kadar sipariş = AYNI GÜN kargo"
Kargo: Sürat / Hepsijet / DHL
=> "Tool-free montaj" = kutunun vidasız açıldığının satıcı beyanı → PCB'ye erişim mümkün.

## ESD cımbız seti — FOTOĞRAFTAN DOĞRULANDI (kritik!)
Robo90 "ESD Anti-statik Cımbız Seti - 6 Parça" = ESD-10, -11, -12, -13, -14, -15 (Vetus tipi).
Gövde siyah anti-statik kaplı **paslanmaz çelik**, UÇLAR ÇIPLAK PARLAK METAL → İLETKEN. ✅
ROM pad kısa devresi için uygun. (Uyarı: piyasadaki bazı "anti-statik" cımbızlar plastik/karbon
elyaf uçlu olur ve HİÇBİR ŞEYİ kısa devre yapmaz — bu set öyle değil.)
ESD-11 / ESD-10 = çok ince düz uç (pad işi için ideal), ESD-15 = eğri uç.
opsiyonel ek: USB uzatma kablosu dişi-erkek 1.5m — 69,55 TL (Robo90) https://www.robo90.com/usb-uzatma-kablosu-disi-erkek-15-metre

## Ek Soru A — M.2 NVMe -> PCIe x4 kartı mantıklı mı? (kendi analizim)
KISA CEVAP: İlk turda ALMA. Şu nedenlerle:
1. MPTool USB istiyor; PCIe kartı MPTool'u ÇALIŞTIRAMAZ → yerine geçmez.
2. PCIe kartı bir MASAÜSTÜ + boş PCIe yuvası istiyor. T440 laptop (yuva yok),
   kaplıkaya şu an dokunulmaz. Yani bugün kullanılamaz.
3. Açık kart tipi bir JMS583 USB adaptörü zaten SSD'nin iki yüzünü de açıkta bırakır
   → PCIe kartının tek gerçek avantajını (pad erişimi) o da veriyor.
4. MPTool Windows-only. USB köprüsü bir Windows VM'e **USB passthrough** ile 2 tıkta
   verilebilir (VirtualBox/QEMU). PCIe cihazı VM'e vermek VT-d + masaüstü ister.
   → USB rotası T440'ta tek başına tamamlanabilir; PCIe rotası tamamlanamaz.
NE ZAMAN ALINIR: Faz 1 (UART + MPTool) tıkanırsa, "kontrolcü gerçek bir NVMe linkinde
ayağa kalkıyor mu" sorusunu bağımsız sınamak için. O zaman `echo 1 > /sys/bus/pci/rescan`
ile ROM-short sonrası yeniden tarama yapılabilir (reboot gerekmez).
Alternatif: M.2 NVMe uzatma (riser) kablosu — diski yuvadan çıkarıp iki yüzünü açar.

## Ek Soru A ekstra not — T440'ta M.2 NVMe yuvası yok
T440 = 2.5" SATA + mSATA/mini-PCIe. NVMe yuvası YOK.
=> SSD'yi enerjilendirmenin tek yolu USB kutusu. Bu, USB adaptörünü "orta öncelik"ten
   "olmazsa olmaz"a taşıyor.

# ==== ÖNCELİK GÜNCELLEMESİ SONRASI (UART birinci) ====

## 1.8V sorusu — CEVAP
- **FT232H Türkiye'de pratik değil**: direnc.net'te Adafruit FT232H Breakout **1.279,22 TL ve TÜKENDİ**.
  Robotistan/Robo90/Motorobit'te FT232H YOK. Ayrıca Adafruit kartında VCCIO zaten 3.3V'a sabitli,
  1.8V'ı kutudan çıkar çıkmaz vermez. → FT232H rotası KAPALI.
- **ÇÖZÜM: TXS0108E 8 Kanal Mantık Seviye Dönüştürücü — 57,96 TL, Robo90, STOKTA**
  https://www.robo90.com/txs0108e-8-kanal-mantik-seviye-donusturucu
  Ürün sayfası: "Gerilim seviyesi: 1.8V-6V", 8 kanal, çift yönlü, otomatik yön.
  TI datasheet: VCCA 1.2–3.6V, VCCB 1.65–5.5V, VCCA<VCCB → 1.8V(A) ↔ 3.3V(B) tam spec içinde.
  ⚠️ VCCA'ya 1.8V referans lazım: SSD kartının kendi 1.8V rayından alınır (multimetreyle bulunur).
- Alternatif (stokta yok): BSS138 4 kanal lojik çevirici 17,39 TL — Robo90 OutOfStock.
- **NEDEN 1.8V ÖNEMLİ**: CP2102'nin VIH ≈ 0.7×3.3 = 2.31V. 1.8V'lik bir TX sinyalini HIGH
  olarak GÖREMEZ → ekranda çöp ya da hiçbir şey. Ama bu kalıcı hasar değil, sadece okunmaz.
- **ÖNCE ÖLÇ**: SSD enerjiliyken UART TX pad'inin boştaki (idle) DC gerilimini multimetreyle oku.
  ~3.3V → doğrudan CP2102. ~1.8V → araya TXS0108E.

## Stok/kargo — istenen kesinleştirme
| Ürün | Satıcı | Fiyat | Stok | Ankara'ya |
|---|---|---|---|---|
| CP2102 USB-TTL 3.3V/5V | Robo90 (Ostim/ANKARA) | 115,92 | InStock (available:true) | **AYNI GÜN, mağazadan teslim** |
| USB-TTL CH340G | Robotistan (İst) | 99,28 | **TÜKENDİ (OutOfStock)** | — |
| CP2102 6-Pin | direnc.net (İst) | 102,67 | InStock | 1-2 iş günü (tahmin; kargo sayfası açılmadı) |
| CP2102 HW-598 5-pin | direnc.net (İst) | 106,55 | InStock | aynı |
| USB-TTL CH340G | motorobit (İst) | 81,68 | InStock | 1-2 iş günü (tahmin) |
| FT232RL 3.3V/5V jumper | Robo90 (ANKARA) | 98,53 | InStock | aynı gün |
- Robotistan kargo politikası: sipariş 48 saat içinde kargoya verilir, Yurtiçi/Aras.
  1500 TL üzeri ücretsiz. → İstanbul'dan Ankara'ya toplam 2-4 gün. Rekabetçi değil.
- Robo90: 1500 TL üzeri ücretsiz kargo, aynı gün kargo, "Mağazadan Teslim Al" seçeneği.

## Ankara fiziksel mağaza — SONUÇ
✅ **Robo90** — Ostim OSB Mah. Turan Çiğdem Cd. No:35, Yenimahalle. Pzt-Cu 09:00-18:00, Cmt 11:00-14:00.
   OSTİM metro (M1) istasyonuna 760 m. Bilkent'e 12 km. WhatsApp +90 554 027 03 90 (yazılı).
   Sipariş sırasında "Mağazadan Teslim Al" seçilir.
❌ Konur Sokak / Ulus elektronikçiler: **DOĞRULAYAMADIM.** Tüm arama motorları (DDG, Mojeek,
   Startpage, searx, Bing) bot koruması verdi; OpenStreetMap'te Kızılay bbox'ında 143 dükkândan
   sadece 1 tanesi elektronik (GENMAK, Yeşilırmak Sk. 5). Yani "Konur Sokak'ta var" DİYEMEM,
   "yok" da diyemem — ölçemedim. Robo90 doğrulanmış seçenek, onu kullan.

## 3. KALEM: PCIe → M.2 adaptör kartı (Türkiye fiyatları, akakce)
| Ürün | En ucuz | Not |
|---|---|---|
| **Alfais 4391 M.2 NVMe SSD NGFF→PCIe 3.0 x1, M-Key** | **279,99 TL** ÜCRETSİZ KARGO | "Stokta 1 adet" · 12 satıcı · https://www.akakce.com/pci-donusturucu/en-ucuz-alfais-4391-m-2-donusturucu-fiyati,736173775.html |
| Lunatic 9143 M.2 NVMe NGFF→PCIe 3.0 x1 (M-Key only) | 300,11 TL | 2 satıcı |
| Alfais 5225 PCIe Dönüştürücü | 309,90 TL | 3 satıcı |
| Dark DK-AC-PEM1X NGFF/NVMe M.2 → PCIe x1 | 349,00 TL | 12 satıcı, marka garantili |
| Dark DK-AC-PEM2 NGFF/NVMe M.2 → PCIe | 412,25 TL | 13 satıcı |
=> Koordinatörün beklediği 100-200 TL bandı ARTIK YOK; gerçek taban ~280 TL.
=> x1 olması sorun değil: NVMe x1 linkte de enumerate olur, tespit/ROM testi için yeterli.

## ⚠️ GEOMETRİ DÜZELTMESİ — "kart dik durur, iki yüzü de açıkta" TAM DOĞRU DEĞİL
PCIe adaptöründe de SSD, adaptör PCB'sinin ÜSTÜNE yatar; SSD'nin ALT yüzü adaptör kartına bakar,
arada sadece ~2-4 mm vardır (M.2 konnektör yüksekliği + standoff). Yani ROM pad'leri alt yüzdeyse
üstten değil, YANDAN dar bir aralıktan girmek gerekir. USB kutusunda da durum aynı.
Gerçek çözümler, iyiden kötüye:
 1. **PAD'LERE İNCE TEL LEHİMLE** (0.1-0.2 mm emaye tel), telleri dışarı çıkar, açılışta
    jumper'la kısa devre et. Geometri sorunu TAMAMEN ortadan kalkar, cımbızla nişan almak yok.
    → Bu yüzden "ince tel + havya" listede cımbızdan DAHA kritik.
 2. SSD'yi vidalamadan eğik bırak (M.2 modülü serbestken ~20-25° kalkar) → uzak uçta birkaç mm
    fazladan boşluk; kenara yakın pad'lere ince cımbız girer.
 3. M.2 uzatma/riser kablosu — SSD tamamen serbest kalır, iki yüz de açık. **Türkiye'de
    BULAMADIM** (akakce'de sonuç yok, HB/Trendyol Cloudflare'a takıldı). AliExpress'te var ama yavaş.

## İnce tel — Robo90'da ne var
- "4'lü 0.22mm Çok Telli Montaj Kablo - 1 Metre" 34,78 TL (InStock)
  https://www.robo90.com/4lu-022mm-cok-telli-montaj-kablo-1-metre
  PÜF NOKTA: çok telli kablonun içinden TEK bir damar çekilirse ~0.08 mm tel elde edilir —
  pad'e lehimlemek için emaye telden bile rahat. Ayrı emaye tel almaya gerek yok.
- "Çok Damarlı 22 AWG Montaj Kablosu 15 Metre" 101,43 TL (fazla, gerekmez)
- Robo90'da emaye/lak tel YOK.

## GÜÇ SORUSU DÜZELTMESİ
Masaüstünde (ASUS PRIME B650M-R) M.2 yuvası var → SSD'yi enerjilendirmek için USB kutusu ŞART DEĞİL.
Ama anakart M.2 yuvasında da SSD alt yüzü anakarta bakar (~2-3 mm) → alt yüzdeki pad'lere erişim
yine dar. UART pad'leri ÜST (bileşen) yüzdeyse sorun yok — kontrolcü test noktaları genelde üsttedir.

## Alfais 4391 (M.2 NVMe M-Key → PCIe 3.0 x1) — satıcı bazlı (akakce satıcı listesi)
| Satıcı | Fiyat | Kargo | Teslim | Toplam |
|---|---|---|---|---|
| **Hepsiburada** | 309,95 | 0 | 1 iş günü | **309,95 TL** ← en iyi |
| Trendyol | 289,00 | 44,99 | 1 iş günü | 333,99 TL |
| Trendyol (2.) | 294,90 | 44,99 | 1 iş günü | 339,89 TL |
| Pttavm | 408,27 | 0 | 1 iş günü | 408,27 TL |
| Pazarama | 423,00 | 0 | 1 iş günü | 423,00 TL |
Akakçe manşetindeki "279,99 ücretsiz kargo" satıcı listesiyle uyuşmuyor (bayat olabilir) →
gerçekçi bant **290-310 TL, 1 iş günü**.
Ürün adı tam: "Alfais 4391 M.2 Nvme Ssd Ngff To Pcie 3.0 X1 Adaptör M Key Kart Çevirici Dönüştürücü"
(M-Key NVMe destekler, M.2 SATA B-Key desteklemez — bizim disk NVMe, uygun.)

# ==== KESİN KANIT: JMS583 GERÇEKTEN ŞART ====
github.com/xiaobodeluo/MAP1202-B47R-SSD-Repair-Tool — README (Çince), birinci elden onarım günlüğü.
Vaka: Hikvision C500 1TB, **MAP1202A-F1C** + Micron B47R. Tamamen ölü (BIOS görmüyor, kutuda
sadece LED yanıyor). 30 saatte kurtarılmış.
Birebir alıntılar:
- "必须用 JMS583 主控的硬盘盒" = **JMS583 kontrolcülü kutu KULLANILMALI**
- "RTL9210 主控的盒子识别不了 ROM 模式" = **RTL9210 kutular ROM modunu tanıyamıyor**
- "我换了 3 个硬盘盒才发现这个问题" = 3 kutu değiştirdikten sonra anlamış
Prosedür:
  1. ROM pad'lerini kısa devre et (cımbız/tel)
  2. **KISA DEVREYİ KORUYARAK** USB'ye tak
  3. MPTool'da "Scan Drive"
  4. Cihaz görününce kısa devreyi BIRAK  ("erken bırakırsan boşa, geç bırakırsan araç tanımaz")
  5. Tool Type: **MPT** (Sort ya da MPTP değil) · Preformat Mode: **Inherit FW BB** · Capacity: otomatik
  6. Start → 3-5 dk → PASS
- **ROM pad'lerinin yeri: "通常在主控旁边，标着 ROM / J1"** = genelde KONTROLCÜNÜN YANINDA,
  üzerinde "ROM" ya da "J1" yazar. (Yani illa arka yüzde olmayabilir — önce kontrolcünün
  çevresine bak.)
- ⚠️ **NAND'a göre farklı firmware paketi**: onunki B47R için `MAP1202_B47R-C_0_01_009d-SVN09954`.
  "别下成 B37R 的" = B37R paketini indirme. **BİZİM NAND SK hynix H25T1TB48E** → B47R paketi
  DEĞİL, SK hynix paketi lazım. Kaynak: 穗穗工具站 xmrom.kmdns.net:5000 · usbdev.ru/files/maxio/
- MPTool = tam silme. Veri gider. (Alperen'in amacı zaten diski çalıştırmak.)
- Sonuç: 0 GB → 1024 GB, CDM ~3500/3000 MB/s.

# ==== EK SORU B CEVABI: PROFESYONEL KURTARMA MANTIKSIZ ====
- **ACE Lab PC-3000 SSD desteklenen liste**: Maxio ailesinden SADECE SATA MAS0902 ve MAS1102 var.
  **MAP1202 (NVMe) LİSTEDE YOK.**
- **Rossmann Group** (dünyanın en bilinen board-level onarımcılarından) resmi sayfası:
  "The MAP family is absent from ACELab's PC-3000 SSD supported-controller list, and no firmware
  utility we operate covers them." + "Rossmann does not currently offer in-lab recovery for
  Maxio MAP1202, MAP1602, or MAP1602A drives." + şifreleme anahtarı kontrolcüye bağlı → chip-off
  da işe yaramıyor.
=> PC-3000'i olan firma bile bu diskte firmware seviyesinde iş yapamaz. **DIY tek yol.**
- Ankara'da PC-3000 SSD iddiası olan tek firma: **BilgiKoru** (Uğur Mumcu Mah. 1179. Cad. No:5/54,
  Yenimahalle · 0312 354 77 33) — ücretsiz ön analiz. Ama MAP1202 kapsam dışı olduğu için
  bu diskte işe yaramaz.
- Fiyat referansı: Teknik Nokta (İst) SSD/NVMe **400-1500 USD ≈ 19.400-72.800 TL**.
  1000 TL'lik disk için tamamen anlamsız.

# ==== ANKARA ELEKTRONİK BÖLGELERİ (agent doğruladı) ====
- **Parça alımı: Ulus, Konya Sokak — "Ankara Elektronikçiler Çarşısı"**
  Kale Mah., Konya Sok. No:17, Altındağ (Ulus metro yanı)
- Tamir/servis yoğunluğu: Kızılay Konur Sokak (bilgisayar/telefon servisleri)
- Ankara'da BGA/reballing: Polat Electronic / ankaralaptoponarim.com, İzmir Cad. Can İş Hanı
  No:3 D:2 Kızılay, 0535 419 48 40 — fiyat yayınlamıyor. Agregatör aralığı 230-2.300 TL.
- İskitler = sanayi, Siteler = mobilya → alakasız.

# ==== EK ÜRÜNLER (agent) ====
- Vetus ESD-15 antistatik cımbız 120mm paslanmaz — direnc.net **96,86 TL**
  https://www.direnc.net/esd-15-antistatik-cimbiz-120mm
- DT-830**B**'de BUZZER YOK, DT-830**D**'de VAR (iki bağımsız kaynakla doğrulandı) → D al.
  DT-830D — motorobit 173,25 TL · Robo90/ANKARA 173,88 TL
- 0.2mm emaye bobin teli 1 m — roboshop.com.tr **12,15 TL**
- **Alfais 6086 M.2 NVMe PCIe 4.0 x4 UZATMA (riser) kablosu** — n11 sepette **510,41 TL**
  (Aras ücretsiz, 2 gün) / hepsiburada 614,95 TL. M-Key NVMe, 2230-2280, SATA uyumsuz.
- Alfais 4391 M.2 NVMe M-Key → PCIe 3.0 x1 — hepsiburada **289,00 TL** (300 TL üzeri kargo bedava)
