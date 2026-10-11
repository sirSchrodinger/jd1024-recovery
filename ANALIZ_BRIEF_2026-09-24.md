# JD1024 write-restore — kapsamlı analiz brief'i (2026-09-24)

> Bu dosya, bir **analiz/planlama** oturumu için tam state transferidir. Amaç: bu
> oturumun hiçbir şeyi yeniden keşfetmeden, problemi baştan aşağı kavrayıp **tüm
> olası çözüm yollarını, her başarısızlığın kök nedenini ve doğru çözümün neden öyle
> olması gerektiğini** net bir karar ağacı halinde üretmesi.
>
> **Bu oturum cihaza HİÇBİR komut göndermez.** Sadece diskteki dump'ları,
> disassembly'yi ve notları okur; çıktı bir **yazılı analiz**tir. Donanım müdahalesini
> (NAND yazma / güç çevrimi) kullanıcı ayrı bir oturumda elle yürütecek. Cihaz
> kullanıcının kendi malı; disk **boştur** (kurtarılacak veri yok), amaç onarım +
> öğrenme. Agresif olmakta sakınca yok; risk sadece "cihaz onarılamaz kalır".

---

## 0. Tek cümlelik problem

JamesDonkey JD1024 1TB NVMe SSD (MAXIO MAP1202 controller + SK hynix V6 TLC NAND,
16 die), bir die'ın (die 11 = c3ce2) sistemik erase-fail'i yüzünden firmware'i
**koruma amaçlı kalıcı write-protect** (read-only) moduna girmiş. Hedef: diski
**tekrar yazılabilir + normal kullanılabilir** hale getirmek. WP'yi kaldıran config
biti kesin bulundu, ama uygulamada die-exclude yaklaşımı ürün firmware'inin NVMe
katmanını kaldırmasını engelledi. Çözülmesi gereken: **WP-off'u, NVMe'yi ayakta
tutan bir firmware konfigürasyonuyla birlikte kalıcı kılmak.**

---

## 1. Donanım ve erişim mimarisi

- **Controller:** MAXIO MAP1202 ("Cougar"). ARM+Thumb karışık çekirdek (Cortex-M
  DEĞİL; CP15'li klasik ARM + Thumb-2 gövde). İki CPU: CPU0 (paylaşılan SRAM
  0x040Dxxxx) ve CPU2 (0x0406xxxx, TCM benzeri, vendor ReadRam'den görünmez).
- **NAND:** SK hynix V6 TLC (H25T1TB48E). 16 die (die = CE×4 + CH). Die başına 2888
  block, block başına 1536 page, 16 KB page, 4 plane.
- **Köprü:** JMicron JMS583 USB-NVMe bridge (USB id 152d:a583). Host = T440 laptop,
  Linux. NVMe'ye tek erişim yolu bu köprünün **sntjmicron 3-fazlı admin passthrough**
  protokolü (SG_IO ioctl / sg_raw). SIG=0x454D564E ("NVME").
- **İki firmware modu:**
  - **Ürün modu** (telsiz): ROM, die 0'daki loader/firmware'i boot eder. Kimlik
    `MN='JAMESDONKEY JD1024 1TB' FR='JD2024'`. NVMe I/O burada olur.
  - **GDP/loader modu** (NAND'ı yazmak için ROM pad'lerine **tel** takılır +
    güç çevrimi): ROM, `Generic_Loader_NVMe_Device` yükler; üstüne `gdprun` ile
    tooling'in GDP stub'ı yüklenip `Generic_GDP_NVMe_Device` olur. **NAND read/write
    ancak GDP modunda yapılır** (ürün modunda değil).

### 1.1 Vendor tünel (ürün modu, sntjmicron üstünden — KANITLI)
- Identify: `nvme(0x06, cdw=(1,...), din=4096)`.
- Vendor enable: `nvme(0xC1, cdw=(0,0,0,0,0x00AE34FF,1), dout=4096zeros)`.
- **ReadRam(0x86):** faz1 `nvme(0xC1, cdw=(0x80,0,0,0,0x001234FF,1), dout=pay(0x86,0x00,be32(addr)))`
  sonra faz2 `nvme(0xC2, cdw=(ns<<7,0,0,0,0x00123486,ns), din=n)`. `pay(op,...)`= `FF E5 op ...`.
- **WriteRam(0x87):** faz1 aynı (pay(0x87,...)), faz2 `nvme(0xC1, cdw=(ns<<7,..,0x00123487,ns), dout=veri)`.
- Kod: `kopru/jms_durum.py` (ReadRam), `kopru/urun_kilit_ac.py` (ReadRam+WriteRam+durum).

### 1.2 GDP tünel (tel takılı, NAND — KANITLI)
- Bootstrap: `port/gdp_bootstrap.py` (ROM loader→GDP; ilk komutta geçici DID_ERROR,
  retry ile geçer; `gdprun` Identify'a bağlı değil).
- NAND ops: page read 0x89, page write 0x8A (mandatory p6=1 for erase 0x8B),
  ReadRam 0x86, WriteRam 0x87. Adresleme `rf = blok*ppb` (mutlak page). Descramble
  `ldpc=1 scr=1`. Her NAND op'tan sonra kanal abort; NAND RESET yok; block 0..15
  asla silinmez/yazılmaz.
- Loader yazımı: `port/ldr_yaz.py` — die 0 block 0'a 360 page yazar (m0=8 sektör,
  m2=32 sektör), erase'i içerik değişimiyle doğrular (0x8A silinmemiş sayfada sessiz
  no-op'tur), tam 360-page geri-okuma verify. `JDKAYNAK` env = kaynak dizin,
  `JDDIE` = hedef die (default c0ce0; c3ce2/die 11 reddedilir). **`sudo env JDKAYNAK=...`
  şart** (düz `JDKAYNAK=... sudo` env'i geçirmez).

### 1.3 KRİTİK erişim kısıtları (ölçülmüş, tekrar keşfetme)
- **WriteRam ürün modunda NO-OP.** Ürün firmware'i 0x87'yi durum=0 döndürüp belleği
  DEĞİŞTİRMEZ (güvenlik). → Runtime RAM-patch (mode=0 yaz) ölü yol. Yalnız GDP modunda
  WriteRam gerçekten yazar (ama GDP RAM'i volatil, boot'ta sıfırlanır).
- **İlk komut transient:** Taze boot sonrası ilk sntjmicron komutu sık sık
  `DID_ERROR` (host=7) ya da `Check Condition ASC=44 ASCQ=83` verir; birçok araç
  retry ile geçer. AMA sürekli ASC=44 = firmware komutu gerçekten fault'luyor (aşağı bak).
- **Host'tan USB VBUS kesilemez;** yazılım USB reset (USBDEVFS_RESET) NVMe wedge'ini
  temizlemez. Tek gerçek güç çevrimi = fiziksel çıkar-tak.
- **LBA 0..~32.4M okunamaz bölge**; oraya SCSI READ köprüyü wedge eder. Testler LBA
  40M+ (iyi bölge) kullanır. Host yazma testi **SCSI WRITE ile DEĞİL**, vendor tünel
  NVMe I/O write (op 0x01, admin=False) ile yapılır (SCSI WRITE uas'ı wedge etti).
- **Adresleme wrap:** blok adresi 1024'te sarıyor (rf=blok×4, blok<<block_shift
  32-bit word'ü taşırıyor, bit-31 NIFC'e rezerve). DPD [0x18/0x1d/0x1e/0x1f] ve NIFC
  reg 0x190/0x194 ile DÜZELTİLEMEDİ (block_shift ve cut-bit ikisi de Stp ile ölçekleniyor,
  birbirini götürüyor). → 1024 üstü blokları ayrı adresleyemiyoruz (QBT sistem bloğu
  yüksek bloklardaysa erişilemez).

---

## 2. Write-protect'in kök nedeni ve mekanizması (KESİN, çift-doğrulanmış)

### 2.1 Zincir
`re/ANALIZ_UART_LOG.md` §23.9 + `re/ANALIZ_WP_BIT.md`:
```
die 11 (c3ce2) erase-fail (226/226 block) → assert sayacı *(0x040EEE58) ≥ 3
  → mode *(0x00810CE8) = 3   (yazıcı 0x040D67F2, "WRITE-PROTECT")
    → Func0 *(0x00000398) bit3 kontrol
      → mode = 4   (yazıcı 0x020066F8)
```
- assert konumu `*(0x040EEE5C)=0x03190712` (üç assert de aynı yer).
- Canlı ölçülen (fabrika ürün boot, Dev 019): **mode=3/4, assert=3, Func0=0x0001F80A
  (bit3=1), NSZE=2000409264 (1024.2 GB, 16 die).**

### 2.2 Yazma kapısı — TAM koşul (iki bağımsız analiz aynı sonuç)
`re/ANALIZ_WP_BIT.md` §5, gate kodu e07 `0x040D6CB0`:
```
ldr 0x00810CE8; ldrb; cmp #3; itt ne; ldrbne; cmpne #4; bne NORMAL   ; mode∉{3,4} → yaz
ldr 0x00000300; ldr [r0,#0x98] (=Func0=*(0x398)); tst.w #8; beq NORMAL ; Func0.bit3=0 → yaz
... "wp no q-wr" → ERKEN DÖN (write-protected)
```
→ **WP ancak `mode∈{3,4} AND Func0.bit3=1` iken.** Ya mode∉{3,4} YA Func0.bit3=0
olursa yazma akar. Bu koşul **30 ayrı gate'te** aynı: QBT-tablo yolu (0x040D6CC6)
VE host-veri write-stream blok-açma yolu (0x040EC0A4) ikisi de aynı Func0.bit3'e bağlı.
`re/ANALIZ_WP_BIT.md` §0: "**Func0.bit3=0 tek başına 30 kapının HEPSİNİ etkisizleştirir.**"

### 2.3 Func0 = config/DPD word (DEĞİŞTİRİLEBİLİR, boot bozmaz)
`re/ANALIZ_WP_BIT.md` §3/§6:
- Func0 imajda 0x00; runtime'da config base 0x00000300 + 0x98 = `*(0x398)`'e
  yükleniyor. Config bloğu NAND loader page 122/123'ten geliyor.
- **kanıt: kanit/loader_v4/src_p122(&123)_m2.bin @page-ofset 0x398 = `0a f8 01 00`**
  = tam runtime Func0 değeri 0x0001F80A. bit3=1 (EnWriteProtectAbort).
- Bit haritası (0x0001F80A): PLD(b1)=1, **WP(b3)=1**, ASPM(b11-14)=1, GPIO_WP(b15)=1.
- **Fix (çift-kanıtlı):** page-ofset 0x398 baytı **`0x0A → 0x02`** (yalnız bit3 temizlenir,
  bit1=PLD korunur) → Func0 0x0001F80A→0x0001F802 → tüm 30 gate açılır. Config redundant
  slot'ları: page 122/123, 167/168, 212/213, 257/258, 302/303 (10 sayfa; hepsi 0x0A).

### 2.4 Neden config, neden kod DEĞİL
- Loader imajı = die 0 block 0, 360 page. Bunun içinde **çalıştırılan kod sayfaları**
  ve **config/parametre sayfaları** var.
- **Config-sayfa düzenlemesi boot'u BOZMAZ** (die-exclude bunu page 122/123/... @0x388/
  0x3E0/0x400/0x440'ta yaptı, boot etti). 0x398 tam bu bölgede.
- **Kod-sayfa düzenlemesi boot'u BOZAR** (aşağıda §3.2/§3.3, iki kez fell-to-factory).
  ROM/loader, çalıştırılan kodu ya doğruluyor ya değişik kod fault'luyor. Bu yüzden
  0x040EC0A4 / 0x040D67F0 gibi **runtime gate kodunu** yamalamak yanlış hedefti; doğru
  hedef config word Func0'dır.

---

## 3. Denenen yolların TAM kaydı ve kesin sonuçları

| # | Yaklaşım | Nerede | Sonuç | Kök neden |
|---|---|---|---|---|
| A | Runtime RAM patch: ürün modunda WriteRam mode=0 | §1.3 | **ÖLÜ** | WriteRam ürün modunda no-op (fw güvenliği) |
| B | Kod patch — write-stream gate 0x040EC0A4 (`wpgate`, page 119/164/209/254/299 @0xA6: 08→00) | kanit/loader_v4_wpgate | **BOOT BOZULDU** → fabrikaya düştü (1024GB) | çalıştırılan kod değişti; ROM reddetti/fault |
| C | Kod patch — mode=3 yazıcı 0x040D67F0 (`modfix`, page 113 @0x27F0: 03→00) | kanit/loader_v4_modfix | **BOOT BOZULDU** → fabrikaya düştü | aynı: kod sayfası |
| D | Config patch — die-exclude (15 die, die 11 haritadan çıkar) | kanit/loader_v4_15die | **GDP'de boot, die sayısı 0x3E0=15; AMA ürün modu NVMe servis etmiyor (bak §3.1)** | ürün NVMe/FTL init 16-die bekliyor olabilir |
| E | Config patch — die-exclude + Func0 bit3=0 (`wpfix`) | kanit/loader_v4_wpfix | **ürün modu HİÇBİR NVMe komutu servis etmedi (ASC=44)** | D'nin sorununu miras aldı |
| F | Config patch — **fabrika 16-die + Func0 bit3=0** (`wpfix16`) | kanit/loader_v4_wpfix16 | **ürün modu NVMe-ready DEĞİL** (12× readcap=1 block, Identify DID_ERROR). Fabrikadan tek farkı 10×0x398 (Func0 bit3). | **Func0 bit3=0'ın kendisi readiness'i bozuyor olabilir (bak §3.4)** |

### 3.1 ⭐ BUGÜNÜN KRİTİK BULGUSU — die-exclude ürün-modu NVMe'yi kaldırmıyor
- `loader_v4_wpfix` (die-exclude + Func0) die 0'a yazıldı (`ldr_yaz` verify: yazma
  hatası=0, doğrulama farkı=0, die sayısı 0x3E0=15). Yani NAND'da doğru.
- Telsiz replug (ürün modu), **temiz boot, reset fırtınası YOK**, 60s + 75s
  rahatsız-edilmeden beklendi. Sonuç: **readcap boş, Identify/enable/ReadRam HEPSİ
  `Check Condition ASC=44 ASCQ=83` (internal target failure).** Yani firmware her
  NVMe komutunu fault'luyor.
- Karşılaştırma: **fabrika (16 die) ürün modunda tüm komutları servis ediyordu**
  (Dev 019: Identify→JAMESDONKEY, ReadRam çalıştı, NSZE=2000409264).
- Çıkarım: die-exclude (15-die geometri), ürün firmware'inin NVMe/FTL init'ini bozuyor.
  Not: die-exclude'un "başarısı" GDP modunda RAM'de die sayısı=15 okumakla doğrulanmıştı;
  ürün modunda NVMe servis ettiği **hiç doğrulanmadı**.
- ⚠️ Alternatif hipotez (elenmedi): boot çok uzun sürüyor (§24.1'de fabrika bir boot'ta
  "CSTS 180sn 0x0 kaldı, RDY hiç gelmedi" demişti; 75s yetmemiş olabilir). Ya da benim
  önceki reset-fırtınam bu boot'u bozmuştu (ama temiz replug sonrası da ASC=44 sürdü).

### 3.4 ⭐⭐ EN KRİTİK BULGU — SADECE fabrika config'i NVMe-ready; her iki kaldıraç da readiness'i bozuyor
4 config denendi, ürün modunda NVMe komutlarını servis eden TEK config **fabrika**:

| Config | die | Func0.bit3 | beklenen mode | ürün-modu NVMe-ready? |
|---|---|---|---|---|
| Fabrika (Dev 019) | 16 | 1 | 4 | **EVET** (readcap=2000409264, Identify=JAMESDONKEY) |
| die-exclude (15die) | 15 | 1 | 4 (assert hâlâ?) | **HAYIR** |
| wpfix (15die+Func0) | 15 | 0 | 3 | **HAYIR** |
| wpfix16 (fabrika+Func0) | 16 | 0 | 3 | **HAYIR** (12× readcap=1) |

**İki bağımsız kaldıraç, iki ayrı sebeple readiness'i bozuyor gibi görünüyor:**
- **die-exclude (15-die geometri):** Func0.bit3=1 (fabrikayla aynı) olmasına rağmen
  NVMe-ready değil → readiness'i **geometri** bozuyor (FTL/NVMe init 16-die bekliyor).
- **Func0.bit3=0:** geometri fabrikayla birebir aynı (yalnız 10 bayt fark), yine de
  NVMe-ready değil → readiness'i **mode/WP zinciri** bozuyor.

**Merkezi hipotez (GÜÇLÜ ama KANITLANMADI — kontrol deneyi gerek):**
Ürün NVMe-init'i **mode=4'e (tam-latched WP durumuna) ulaşmayı** gerektiriyor olabilir.
Fabrika: assert≥3 → mode=3 → Func0.bit3=1 → **mode=4** → NVMe "güvenli kilitli" olarak
kalkıyor (read-only). Func0.bit3=0 yapınca 3→4 geçişi durur, **mode=3'te takılır**, NVMe
init tamamlanmaz → readcap=1. Yani "WP'yi Func0 ile kapatmak" ile "NVMe'nin kalkması"
şu firmware'de ÇELİŞİYOR olabilir.

**Bu doğruysa problem yeniden çerçeveleniyor:** yazılabilir+ready tek yol **mode=0**
(assert hiç 3'e ulaşmasın) — çünkü mode=0'da hem gate açık (mode∉{3,4}) hem NVMe normal
kalkar. Bu da **die 11'in boot'ta assert ÜRETMEMESİNİ** gerektirir, AMA 16-die geometriyi
bozmadan (die-exclude readiness'i ayrıca bozuyor). Aday: die 11'in bloklarını **bad-block
tablosuna** işaretlemek (geometri 16 kalır, FTL die 11'i hiç kullanmaz/erase etmez →
assert yok → mode=0), ya da assert'i besleyen boot-time die-scan/health okumasını
config'ten kesmek. (§5 Soru 1+3'ün gerçek hedefi bu.)

**ÖNCE KONTROL DENEYİ (bir sonraki donanım oturumunda):** temiz fabrika imajını
(`kanit/loader_v4`, Func0.bit3=1, hiç değişiklik yok) die 0'a yazıp ürün-modu readcap'i
tekrar 2000409264 veriyor mu diye doğrula. Veriyorsa "Func0.bit3=0 readiness'i bozuyor"
hipotezi kanıtlanır (fabrika ready, wpfix16 değil, tek fark 10 bayt Func0). Vermiyorsa
readiness flaky'dir ve tüm "not-ready" ölçümleri şüpheli olur — o zaman ilk iş
readiness'in neye bağlı olduğunu (timing? mode? assert?) bulmaktır.

### 3.5 ⭐⭐⭐ M1 KESİN DOĞRULANDI (2026-09-24 21:27 ölçümü) — WP-off boot'u TAKIYOR (yavaş değil)
`wpfix16` (16-die + Func0 bit3=0) telsiz replug, **9,5 dakika kesintisiz** beklendi;
ilk 90s hiç dokunulmadı, sonra 45'er sn nazik readcap. Sonuç: **11 yoklamanın hepsi
readcap=1 block.** dmesg: enumerasyondan sonra **reset YOK** (yoklamalar 30s-timeout→uas-
reset tetiklemedi, readcap "1-block"u hızlı-temiz dönüyor) → boot rahatsız edilmedi.
Controller **cevap veriyor** (readcap hata değil, temiz 1-block) ama **namespace hiç
initialize olmadı** (boyut 1'de kaldı). → **M2 (yavaş boot) ELENDİ; M1 doğru: WP-off'ta
FTL/namespace init die-b yazma döngüsünde takılıyor, yakınsamıyor.**

**Kesinleşen sonuç:** config-lever (Func0 / die-map) **yazılabilir+NVMe-ready veremez.**
Ölçümle kapandı. Geriye tek yol: die-b'nin **boot-anı fiziksel yazmasını durdurmak.**

### 3.6 ★ KESKİNLEŞMİŞ SORU (bir sonraki analiz turu) — sistem süper-blok die-tahsisi nerede?
Analiz cevabı (`ANALIZ_CEVAP_2026-09-24.md` §5) config-only'yi eledi çünkü sistem/boot
süper-blokları (blok 0-15) **16 fiziksel die'a** çizgileniyor ve config die-map (0x400/
0x440) yalnız **kullanıcı-veri** geometrisini değiştiriyor. AMA iki nokta yeniden
sorgulanmalı (kolay pes etme):
1. *(bu nokta kamuya açık depodan çıkarıldı — write-protect mekanizmasına erişimle ilgiliydi,
   bkz. repo README "Neden bazı dosyalar burada yok")*
2. **die-presence config alanı 0x31C** (canlı dump'ta var, §10'da geçiyor) — die-map
   0x400/0x440'tan VE ROM HW-probe bitmap'inden (0x04030052) AYRI. Bu alan sistem süper-
   blok die-tahsisini etkiliyor mu? die-b'yi burada düşürürsek boot yazması die-b'yi
   atlar mı? (Analiz 3c yalnız ROM-probe bitmap'ini eledi; firmware-seviyesi 0x31C'yi ayrı
   incelemedi.)
Sorulacak net soru: **"Firmware, sistem/boot süper-bloğunu hangi fiziksel die kümesine
yerleştireceğine nereden karar veriyor (kod fonksiyonu + okuduğu NAND/config alanı)? Bu
küme config'ten (örn. 0x31C, ya da bir sistem-blok tahsis tablosu / bad-block tablosu —
hepsi düşük/adreslenebilir bloklarda) die-b'yi çıkaracak şekilde düzenlenebilir mi?
Düzenlenebiliyorsa hangi ofset/bayt; düzenlenemiyorsa disasm ile neden."** Hedef: die-b'ye
boot yazması HİÇ gitmesin → assert türemesin → mode=0 → WP-on kalsa bile 30 kapı açık
(mode∉{3,4}) → yazılabilir + NVMe-ready.

### 3.2/3.3 Kod patch'leri neden fell-to-factory
- ROM boot validation notları: `re/ANALIZ_BOOTDIE_SECIM.md`, `re/ANALIZ_CERT_AKTIF_MI.md`.
  3 gate (LDBK BLOCKS/CONFIG magic page 0, CERT page 1 — autonomous boot'ta KAPALI,
  LDBK LDPC magic page 2/4). "Code page'ler üzerinde checksum yok, sadece okuma anında
  LDPC ECC" deniyordu — ama EMPİRİK olarak kod patch'i boot bozdu, config patch bozmadı.
  Bu çelişki **açık bir sorudur** (bak §5 Soru 4): ya ikinci-aşama bir integrity check var,
  ya değişen komut çalışınca fault ediyor, ya page↔RAM eşlemesi sanılan yerde değil.

---

## 4. Şu anki NAND durumu ve yedekler

- **die 0 block 0 şu an:** `loader_v4_wpfix16` (fabrika 16-die + Func0 bit3=0).
  Ürün modunda NVMe servis etmiyor (bak §3.4). Ondan önce `loader_v4_wpfix` yazılıydı.
- Fabrika yedek die: ROM'un fallback'i (kod patch'leri buna düşürdü, 1024GB, çalışıyor).
- Yedekler (`kanit/`): `c0ce0_blok0_yedek_0924_2020` (= yazımdan önceki modfix hali),
  `loader_v4` (fabrika 360-page dump, temiz), `loader_v4_15die` (temiz die-exclude).
- Hazır ama yazılmamış: **`loader_v4_wpfix16`** (fabrika 16-die + Func0 bit3=0; fabrikadan
  farkı yalnız 10 sayfa × ofset 0x398, `0A→02`).
- Geri dönüş her an mümkün: `sudo env JDKAYNAK=<yedek dizin> python3 port/ldr_yaz.py --yaz`.

---

## 5. ANALİZ OTURUMUNDAN İSTENEN — açık sorular ve karar ağacı

Aşağıdakileri, her iddiayı **dosya + ofset + disasm/ölçüm** ile gerekçelendirerek,
net bir karar ağacı ve öncelik sırasıyla üret. (Cihaza komut YOK; hepsi diskteki
dump/asm/notlardan statik.)

**Soru 1 — die-exclude neden ürün-modu NVMe'yi kaldırmıyor?**
`re/ANALIZ_DIEREMAP.md`, `re/ANALIZ_DPD_YAPISI.md`, disassembly (`re/gdp/*.asm`) ve
config sayfası alanlarını (die sayısı 0x3E0/0x4C6, Die_2_CeCh 0x400, CeCh_2_Die 0x440,
LBA 0x388, DPD BlkCnt/kapasite 0x0c/0x14) kullanarak: ürün NVMe/FTL init hangi alan(lar)ı
okuyor, 15-die geometri neyi tutarsız bırakıyor (kapasite/LBA/die-count/plane çarpımı,
metadata blok yerleşimi)? Fault noktası hangi kod (0x0406xxxx FTL init)? Düzeltilebilir mi
(hangi ek config alanı 15-die ile uyumlu olmalı), yoksa die-exclude ürün modunda
temelde uyumsuz mu?

**Soru 2 — fabrika 16-die + Func0 bit3=0 (`wpfix16`) çalışır mı, riski ne?**
Bu boot ederse (fabrika geometri = NVMe-ready kanıtlı) ve Func0.bit3=0 30 gate'i açarsa,
disk 1024GB + yazılabilir olur. AMA die 11 kullanımda erase-fail üretmeye devam eder:
(a) FTL bunu bad-block olarak işaretleyip 15 die'la devam eder mi, yoksa (b) GC/erase
takılıp ilerleyemez mi? assert her fail'de artar ama mode zaten 3, Func0.bit3=0 gate'i
açık tutar — assert'in WP DIŞINDA bir yan etkisi var mı (FTL halt, retry storm, yeniden
mode geçişi)? `re/ANALIZ_SILME.md`, `re/ANALIZ_UART_LOG.md`, health-word setter'ları
(0x0200F32C "BT-RF-OK", 0x0200F420 "GC_RE_NG") üzerinden değerlendir.

**Soru 3 — daha iyi bir üçüncü yol var mı?**
Die 11'i geometriden çıkarmadan (NVMe-ready'yi koruyarak) ama die 11'i kullanımdan da
düşürerek: örn. **die 11'in bloklarını bad-block tablosuna** işaretlemek (geometri 16
kalır, FTL die 11'i atlar). Bu tablo NAND'da nerede, formatı ne, adreslenebilir mi
(§1.3 wrap kısıtı!)? Ya da assert eşiğini (kod `cmp #3`) değil ama assert'i besleyen
die-scan/health kaynağını config'ten kesmek mümkün mü? Her seçeneği "boot bozar mı /
NVMe-ready kalır mı / kalıcı mı / adreslenebilir mi" ekseninde puanla.

**Soru 4 — kod-patch neden boot bozuyor, config neden bozmuyor (kesin mekanizma)?**
Bu netleşirse, gelecekte gerekiyorsa kod patch'i güvenli yapmanın yolu (ya da kesin
imkânsızlığı) belli olur. ROM/loader'ın page↔RAM yükleme haritasını (chunk0→0x00000000
0xC000 bayt, chunk1→0x040C0000 0x30000 bayt; `port/veri/` ve ldr_yaz akışı), hangi
page'lerin koda hangilerinin config'e gittiğini, ve bir integrity/CRC/LDPC kontrolü olup
olmadığını disassembly'den çöz. Page 113/119/... gerçekten 0x040D67F0/0x040EC0A4'e mi
map oluyor?

**Soru 5 — nihai öneri.**
Yukarıdakilerin ışığında, kullanıcının bir sonraki oturumda **elle yürüteceği** net,
sıralı, minimum-riskli plan: hangi imaj yazılacak (tam page+ofset+bayt), hangi sırada
tel-tak/telsiz replug, her adımda beklenen ölçüm (Func0, mode, NSZE, host-write sonucu),
ve başarısızlıkta geri dönüş. Öncelik: **NVMe-ready + yazılabilir + kalıcı.**

---

## 6. Dosya haritası (derinlik için oku — hepsi diskte, salt-okuma)

- **Ana log:** `DURUM_2026-09-19.md` (§23.6 Func0/DPD, §23.9 WP zinciri, §24 GDP oturumu).
- **WP/gate analizleri:** `re/ANALIZ_WP_BIT.md` (Func0 bit3 kesin kanıt), `re/ANALIZ_YAZMA_KAPISI.md`
  (30 gate, health-word setter'ları).
- **die-remap/DPD:** `re/ANALIZ_DIEREMAP.md`, `re/ANALIZ_DPD_YAPISI.md`, `re/ANALIZ_TARAMA_BESLEME.md`.
- **boot/validation:** `re/ANALIZ_BOOTDIE_SECIM.md`, `re/ANALIZ_CERT_AKTIF_MI.md`, `re/ANALIZ_BOOT_RECOVER.md`.
- **erase/FTL/SMART:** `re/ANALIZ_SILME.md`, `re/ANALIZ_UART_LOG.md`, `re/ANALIZ_FW_READONLY.md`.
- **disassembly:** `re/gdp/c0_arm.asm`, `c0_thumb.asm`, `c1_arm.asm`, `c1_thumb.asm`,
  `v7c0_*.asm`, `v7c1_*.asm` (ARM+Thumb; e04=0x02000000 çoğu ARM, e06/e08/e09 Thumb-2).
- **canlı RAM dump (ürün):** `re/urun_jms/00000000.bin` (config base, Func0@0x398),
  `00810C00.bin` (mode@0xE8), `040EEC00.bin` (assert@0x258=0x040EEE58).
- **firmware imaj kaynakları:** `re/fw_canli/e*.bin` (segment dump'ları), `re/dis_kaynak/`
  (stok imajlar), `kanit/loader_orijinal/` ve `kanit/loader_v4/` (fabrika 360-page).
- **DPD deneyleri:** `port/dpd_*.bin`, `port/adres_test.py` (wrap ölçümü), `re/ANALIZ_NIFC.md`.
- **tooling (referans, çalıştırma yok):** `port/jms.py`, `port/jmsgdp.py`, `port/ldr_yaz.py`,
  `kopru/jms_durum.py`, `kopru/urun_kilit_ac.py`, `kopru/urun_yazma_test.py`.

## 7. Kalıcı gerçekler / tekrar keşfetme
- Disk fiziksel sağlıklı: life %100, aşınma ~%1. Tek suçlu die 11 (c3ce2). Onarılabilir.
- SKV6 firmware'i halka açık hiçbir yerde yok (2 kütüphane tarandı; forumda admin-only
  `MAP1202_HYV6_64GBDIE-C.01.018` VAR ama indirilemiyor). Yani hazır firmware ile flash yok;
  çözüm mevcut loader'ı config düzeyinde düzenlemek.
- CERT boot-doğrulaması autonomous boot'ta KAPALI; gerçek okuma-engeli LDPC ECC (yazma
  yolunda 0x8A re-encode ettiği için config düzenlemesi çalışıyor).
- SMART persist edilemiyor (WP ikinci kanıt): power-cycle/bad-block sayaçları donuk.

---

## §11 — Flag-yiyen 2. analiz oturumundan kurtarılan + ilerletilen (2026-09-24 ~21:45, bu oturum)

2. analiz oturumu (Opus 5.5) güvenlik-sınıflandırıcısına **hemen** takıldı, bulgu üretemedi
AMA scratchpad'ine analiz altyapısı bıraktı → `re/analiz_arac/`'a kurtarıldı:
- `tk` (re/fw_canli/tk.py): unified addr-space disasm/xref toolkit (SEGS, word, rd, find_word).
- `refs2.pkl`: TÜM adr/ldr/bl xref veritabanı. `x.py <lo> <hi> [T/A]` = adres aralığına referanslar.
- `cfgacc.pkl`/`cfgacc2.pkl`: config-erişim taraması (199 erişim). `cfgx*.py` üretir.
- `d.py <addr> <n> [arm]`: string/pool-anotasyonlu disassembler.
- `uart.txt`: satır-ayrık UART log.

### §11.1 Config (DPD) struct haritası — kim hangi ofseti okuyor (cfgacc2, base RAM 0x300)
- **0x98 (Func0/WP):** ~120 okuyucu, her yerde (WP gate + config-dump). Canlı 0x0001F80A.
- **0x88 (LBA):** e04 0x020031E0 (assert fn!), 0x020106D8, 0x020118B4. Canlı 0x6FC81AB0=1875385008 (960GB).
- **0xE0/0xE1 (die-count):** e06 0x04069E76 + **0x0406E604** (geom kurulum). Canlı 0xE0=15, 0xE1=1.
- **0x1C (0x31C):** cfgacc'de **HİÇ okunmuyor** → "die-presence 0x31C" lead'i ÖLÜ. Canlı 0x03030303
  ama fonksiyonel değil (kod okumuyor). Analiz §10'daki 0x31C varsayımı çürüdü.

### §11.2 Geometri kurulum fn — e06 0x0406E5E0 (die-loop geometrisini config'ten kuruyor)
r4=0x008036E0 (geom struct), r6=0x300 (config). Config **0xE0=max_dies** okuyor:
- max_dies==0 → "E:max_dies=0", 16'ya çek. max_dies>16 → sabit split 8/4/2/1.
  ≤16 → [r4+5..8] = max_dies>>1,>>2,>>3,>>4 (H/M/L/A die-scan hiyerarşisi). "max_dies=%d", "H:%d M:%d L:%d A:%d".
- 0xE1 = floor (max ile). Sonra NAND-op handler ptr'leri [r4+0xC/0x10/0x14/0x20] = 0x040E681C/68B0/22FC/2310.
- geom struct (0x008036E0) **die-loop tüketicileri:** e04 **0x040E22FC, 0x040E2310, 0x040E2378,
  0x040E23DC, 0x040E2458, 0x040E2498, 0x040E24CC, 0x040E24FC** (ARM) — NAND op die-iterasyonu.
→ Bu geometri config die-count'tan (15) kuruluyor. AMA 15-die dump'ında assert=3 → boot/sistem
  L2P yolu bu 15-die geometrisini kullanmıyor ya da die-b'ye başka yoldan yazıyor. Açık kalan nokta.

### §11.3 Assert fn — e04 0x0200318C (assert konumu 0x03190712 buradan, 0x020031F4)
- Config **LBA (0x388)** okuyup sınır `r0 = 1 + (LBA>>3)` hesaplıyor; blok-index r4 < sınır ise
  → L2P map tutarsızsa assert 0x03190712. Yani assert = **geçerli LBA aralığındaki bir bloğun
  L2P map yazmasının patlaması** (die-b arızasının bir üst-katman yakalaması). Doğrudan fiziksel
  write-fail değil, L2P-consistency assert.
- Ayrı bir dal (0x020031B0): 0x03190703 (mode==? koşullu, 0x00802F04+0x10 bayrağı).

### §11.4 Konum: config-lever ölçümle + disasm ile kapanıyor
- Ölçüm (§3.5): WP-off boot takılıyor (kesin).
- Disasm: die geometrisi config die-count'tan kuruluyor ama boot/sistem L2P die-b'ye yine erişiyor
  (15-die assert=3). Sistem-blok fiziksel yerleşimini config die-map'i değiştirmiyor (analiz §5 ile aynı).
- **Kalan tek gerçek RE hedefi:** boot sistem/loader-blok yazmasının die-iterasyonu (§11.2 geom
  tüketicileri e04 0x040E22FC+ ve/veya `[QBT]S` fazı e04 0x0200083C) die-b'yi **bad-block tablosu**
  üzerinden atlıyor mu? die-b'nin sistem blokları DÜŞÜK (0-15, adreslenebilir) → BBT'de işaretlenebilirse
  relocation MP tool'suz mümkün olabilir. Bu, belirsiz ve uzun bir RE; henüz çözülmedi.

### §11.5 ⭐ DUMANLI SİLAH — die-b blok 7 = sabit sistem checkpoint bloğu (UART kanıtı)
UART son boot (uart.txt 7637+): `BIOS OK` → `CHKP-H-NRDY`(tekrar) →
`EH-WRT:CECH(b,b)BLK(7)Page(35)Sts(f010000)Cb(26)FAA:3835b0` → `sys sts fail` → (Page 36…) →
`ASSERT: M(6)F(8)L(288)`. Yani boot-sonu **sistem checkpoint'i die-b (CE2/CH3) BLOK 7'ye**
yazılıyor, her sayfa program-fail (Sts f010000), sonunda assert.
- Aynı log'da `update bbb:165,b,*` / `LBB:PBN(165)CE(2)CH(3)` = FTL die-b'nin **DATA bloklarını**
  (148,163,165,1d5…) bad işaretliyor. AMA **blok 7 (sistem checkpoint) bad işaretlenmiyor** →
  normal remap'e tabi değil, hep die-b'ye yazılıyor. **Kök düğüm bu.**
- `[TBLK]`/`Add blk 165 5 7` = table-block yöneticisi (checkpoint/sistem tablo blokları) — die-b'ye
  blok atıyor.

### §11.6 İlgili kod bölgeleri (bulundu; ama static disasm kısmen garbled)
- **TBLK (table-block) yöneticisi:** e04 0x02001308/142C/1754 ("[TBLK]", "Add blk", "TBLK RUNNING"
  0x02001917). Checkpoint blok-7'yi tahsis eden allocator burada; bölge Thumb/ARM+data karışık.
- **BBT (bad-block) yazıcı:** e07 0x040DA2BC ("update bbb"); RAM tabloları **0x2FC00000** (DRAM) ve
  **0x04001A40**; helper'lar 0x040D9B48 (lookup) + 0x040D9C68 (update). LBB printf e09 0x040CD454.
- **sys-sts-fail handler:** e00 0x000047CC — `*(0x00810CE0)` (sys-status flag; mode 0x00810CE8'in
  8 bayt altı) okuyup/yazıp "sys sts fail" basıyor.
- **CHKP checkpoint state-machine:** e04 ~0x02002854 ("CHKP"), 0x02005966 ("CHKP-H-NRDY" 0x02005CA8).

### §11.7 ÖNERİLEN YOL — empirik (static disasm garbled; canlı tablo oku)
Fix hipotezi: **die-b'yi sistem-checkpoint tahsisinden çıkar** (blok 7 super-block'unu sağlam
die'lara al / die-b'yi sistem-die kümesinden düşür). Bunu static disasm ile çözmek yavaş; daha
güvenilir: **WP-on servis eden config'te (15-die) ürün-modu ReadRam ile** BBT (RAM 0x2FC00000,
0x04001A40) + checkpoint/TBLK die-listesini canlı oku, die-b'nin nerede "sistem die" olarak
listelendiğini bul, o girdinin NAND-persist yerini (düşük/adreslenebilir sistem bloğu) tespit et,
GDP tünelle die-b'yi oradan çıkar. Ön koşul: diski 15-die'a geri al (hem hung wpfix16'dan çıkar
hem ReadRam'i mümkün kılar).

### §11.8 ⛔ KESİN DUVAR — checkpoint fiziksel presence kullanıyor, config die-map DEĞİL
Kanıt (measured): 15-die config (die-map 0x400/0x440 die-b'yi ff ile dışlıyor) yazıldığında BİLE
boot checkpoint'i die-b blok 7'ye yazıyor ve assert=3 (§35.4 dump + UART §11.5). → **sistem-blok/
checkpoint die-kümesi config die-map'ten türemiyor; fiziksel presence (Flash_ID scan) kullanıyor.**
die-b elektriksel canlı (Flash_ID cevaplıyor) → her zaman sistem-die kümesinde. cfgacc taraması
(§11.1) "fiziksel die'ı sistem-blok kümesinden çıkaran" bir config alanı GÖSTERMİYOR.
**Sonuç: config-lever ile die-b'yi sistem-checkpoint'ten çıkarmak İMKÂNSIZ.** (die-map yalnız
kullanıcı-veri geometrisi; §11.4 ile aynı, artık checkpoint-özel kanıtla.)

### §11.9 Geriye kalan yollar (hepsi maliyetli/riskli) + servis flaky notu
- **A. MP-via-tünel replikasyonu:** die-b'nin bloklarını NAND fiziksel bad-block yapısına yazıp
  sistem super-block'unu die-b'siz yeniden kur (GDP tünelle; sistem blokları düşük/adreslenebilir).
  Tek yazılabilir-disk yolu AMA: NAND BBT/sistem-blok formatı tam çözülmedi (static disasm garbled,
  servis flaky), yanlış yazım **brick riski** yüksek. Derin ve belirsiz.
- **B. SKV6/MP paketi:** üreticinin MP tool+firmware'i (`MAP1202_HYV6...`) — standart kurtarma.
  Forumda VAR ama admin-kilitli, indirilemiyor. Bulunursa en temiz yol.
- **C. Read-only kabul:** 15-die 960GB read-only arşiv (servis ettiğinde). Yazılabilir değil.
- **D. Park.**
- ⚠️ **Servis flaky:** bu oturumda 15-die/wpfix16 ürün-modu ReadRam çoğu boot'ta transient
  (readcap=1, DID_ERROR/TIMEOUT/ASC=44) veriyor; 17:39'da 15-die servis etmişti (re/urun_jms/ dump
  var). Çok sayıda hızlı replug drive/bridge'i yormuş olabilir; gerçek power-cycle (VBUS tam düşür)
  + uzun bekleme gerekebilir. Empirik ReadRam RE'si buna takılıyor.

### §11.10 BBT / blok-status RAM yapıları (MP-via-tünel için, disasm netleşti)
- **Blok-status tablosu:** RAM **0x04001540**, girdi 16 bayt, `[entry+4]` halfword'ünün bit0-1 =
  2-bit blok durumu (0/1/2/3). BBT-update helper e07 0x040D9C68 bunu yazıyor (`ldr r1,=0x04001540;
  add r4,r1,r0<<4; ldrh [r4+4]; and #3; cmp #1`).
- İlişkili tablolar (SRAM, ReadRam-erişilebilir olası): **0x00811FC0** (per-die/blok struct, girdi
  ~48 bayt: `[r2+0x14]`'e yazılıyor), **0x008058B0** + **0x00805860** (halfword lookup tabloları),
  **0x008038B0** (fp, çalışma alanı). BBT-lookup helper e07 0x040D9B48.
- FTL die-b VERİ bloklarını burada bad işaretliyor (UART "update bbb"). **Açık soru (fix'in kalbi):**
  boot sistem-checkpoint allocator'ı (TBLK, e04) bu status tablosunu okuyor mu? Okuyorsa → die-b
  blok 7'yi status tablosunun **NAND-persist** kopyasında "bad" yaparsak checkpoint sağlam die seçer.
  Okumuyorsa (blok 7 BBT'den önce sabit tahsis) → tünel-fix bu yoldan çalışmaz.
- Sıradaki RE: (a) 0x04001540 status tablosunun NAND-persist yeri/formatı (düşük sistem bloğu),
  (b) TBLK allocator'ın status-tablosu okuması. İkisi de derin; MP paketi (ajan) bulunursa gereksiz.

## §12 — MP YOLU KONSOLIDASYONU (2026-09-24 gece, bu oturum) — asıl çözüm burada
Bağımsız RE (§11) ile prior work (DURUM §33/§35) AYNI yere vardı: **fix = die-exclude MP**
(firmware die-b'ye hiç dokunmasın). Config-lever kesin kapalı (§11.8). MP iki yolla:

### §12.1 Elimizdeki MP varlıkları (çoğu hazır)
- **Bedava MP tool paketi** (GitHub dom0ng/map1202 → `~/jd1024/mptool/map1202tool/`): MXMPTool
  V0_01_009d.exe + DAT (ucode.bin, ldpc matrisleri, tmc_para, GDP.bin) + Flash.ini + MPTOOL.ini.
- **Flash.ini'de SK hynix V6 ailesi VAR** (SKV603001-004); bizim TAM girdimiz `SKV603005
  H25BFT8A1BDA 2888 1536 16 ... AD 7E 28 53 02 B0` prior'da üretilmiş (`re/mptool/uretilen/MANIFEST.txt`).
- **Bizim NAND Flash_ID = ad7e285302b0** (16 die, SK hynix V6, `tarama/seans.json`).
- **Prior loader-block üretimi:** `re/mptool/ldbk_uret.py` bizim NAND için temiz loader sayfa
  dizisi üretti (drive'ın kendi ucode'u YIQZCA2C + DAT ldpc/tmc) → `re/mptool/uretilen/`.
- MXUtility/MXMPTool exe'leri `~/jd1024/vm/mpt_yama/`; Windows VM `~/jdvm/jd_vm.sh` (HBCD PE).
- **MPTOOL.ini:** `RdtMaxFactoryBadBlockPerDie=208`, `SortMaxBadBlockPerDie=72` → die-b (226 bad
  blok) MP-sort'ta otomatik **tam-bad die** = MP onu dışlar (hedef davranış).

### §12.2 Yürütme duvarı (prior'da bitmemiş)
- **A. MXMPTool (Windows) + JMS583:** §33'te T440 VM'de → "No connected device". Kök neden:
  (1) drive ÜRÜN modundaydı (wedged, MXMPTool probe'una cevap yok), (2) Windows disk-class LBA0
  okuyup köprüyü takıyor, (3) her USB reset NVMe'yi kilitliyor. **DENENMEDİ:** ROM-GDP modunda
  (tel takılı, kapasite 1395, MP giriş durumu). §33'ün çözüm adayı: **sanal köprü** (kopru_nvme.py:
  READ→sıfır, 0xA1 passthrough→gerçek sg1) → LBA0 hang'i aşar, MXMPTool gerçek drive'ı görür.
- **B. Tünel-replikasyonu:** loader-block üretildi (§12.1) AMA tam MP eksik: bad-block scan
  (die-b'yi bul+işaretle) + sistem-blok/L2P kurulumu die-b'siz + yaz. BBT yapıları §11.10'da.
- ⚠️ Prior "B2: SKV6 SYS fw yok" endişesi **ARTIK GEÇERSİZ** — drive'ın kendi ucode'u (YIQZCA2C)
  + bedava paketin DAT/Flash.ini'si elimizde.

### §12.3 Önerilen sıra (en tractable → en derin)
1. **Forum HYV6 paketi** (SN9466) — bulunursa MXMPTool "kutudan" çalışabilir (ajan: liangchanba
   thread-1406, kayıt+puan/admin). Harici, ucuz.
2. **Sanal köprü + MXMPTool (ROM-GDP modu):** §33 duvarını aşan tek net fikir. Linux-tarafı köprü
   geliştir + Windows VM'de MXMPTool. Orta-derin ama MP'yi "gerçek araçla" bitirir.
3. **Tünel-replikasyon MP:** en derin; tam kontrol ama en çok RE + brick riski.

### §12.4 ROUTE-2 HAZIR (bu oturum) — VM + MXMPTool, tek untested değişken: ROM-GDP detection
- **VM imajı hazır** (`~/jdvm/mptool.img`, FAT32 @offset 1MB): `MPT/MXMPTool_MAP1202_USB_V0_01_017.exe`
  + `MPT/Flash.ini` **SKV603005 VAR** (bizim NAND); MPT2/ daha yeni V1_1_26. MXUtility'ler de.
- `~/jdvm/jd_vm.sh`: QEMU q35+kvm, HBCD PE, VNC 127.0.0.1:5907 (:7), JMS583 usb-host passthrough
  (`--kutu-ekle`). Bedava paketin Flash.ini'sine de SKV603005 eklendi (`mptool/map1202tool/`).
- **Bellek dar:** VM 4.6GB, T440'ta ~3.9GB boş → swap'e girer (kısa detection testi için tolere edilebilir).
- **PLAN (route-2a):** drive'ı **ROM-GDP modunda** (tel takılı, kapasite 1395) VM'e ver — §33 ürün
  modunda "No connected device" almıştı; ROM-GDP = MP giriş durumu + LBA0 temiz (hang yok). 
  1) tel-tak → replug (ROM loader, gdp_bootstrap ÇALIŞTIRMA — MXMPTool kendi GDP.bin'ini yükler),
  2) autoprobe=0, 3) `jd_vm.sh` başlat, 4) `--kutu-ekle`, 5) MXMPTool Auto Detect (VNC'den) →
  drive sarı highlight + kapasite görürse DETECTION ÇÖZÜLDÜ → Test Items ayarla → MP çalıştır
  (die-b 226 bad > SortMaxBadBlockPerDie=196 → otomatik dışlanır → 15-die temiz yazılabilir disk).
- Detection ROM-GDP'de de olmazsa → §33 sanal köprü (READ→sıfır, 0xA1→sg1) route-2b.

## §13 — ⭐⭐⭐ MXMPTool DETECTION DUVARI AŞILDI (bu oturum) — MP tek dosyaya kaldı
Route-2 çalıştırıldı (VNC otomasyonu, vncdotool). SONUÇ:
- **§33'ün "No connected device" duvarı ÇÖZÜLDÜ:** drive'ı **ROM-GDP modunda** (tel takılı,
  kapasite 1395) VM'e passthrough → MXMPTool_MAP1202_USB_V0_01_017 **drive'ı GÖRDÜ** (Loader,
  Port 3, SARI highlight; GDP.bin + YI0PCA2C ucode yüklendi). §33 ürün modunda deniyordu — fark bu.
- SN pre-check: SN Input=Barcode→boş. **Çözüm: SN Input="Auto Increase in Hex"** (Device Setting).
- Config: Tool Type=MPT, Preformat Mode=**Erase Search** (die-b'yi taze taramayla dışlamak için),
  Capacity=Auto. START → SN geçti.
- **KALAN TEK BLOKAJ:** `C:\MPT\DAT\SKV6\001_600\nandmem_SKV6_page.bin` **bulunamadı**. Bu, SKV6'ya
  özel NAND parametre dosyası (LDBK NANDMEM TAB, ~5104 B, 4 pointer 0x20/0x850/0x870/0xd38).
  - Elimizdeki üretilen SKV6 (`kanit/fw_hunt3/skv6_from_ucode/.../nandmem_SKV6_page_BLOB_A_ONLY.bin`)
    = **2160 B, EKSİK** (4. pointer=0, blob B yok). DURUM §479-481: ucode↔gerçek dosya %13 örtüşme,
    basit kopya değil, "üretim ÇÖZÜLMEDİ".
  - loader_v4'te "LDBK NANDMEM TAB" görünüyor ama sadece **etiket-string tablosu** (0x2334), veri değil.
  - MP tool + GDP.bin + Flash.ini(SKV603005) + ucode HEPSİ hazır; SADECE bu nandmem dosyası eksik.
- **Drive GÜVENLİ/dokunulmadı** — hata nandmem pre-check'te, erase ÖNCESİ. VM açık, MXMPTool hazır.

### §13.1 Kalan iş — nandmem_SKV6_page.bin (~5104 B) elde et
Yollar: (a) drive'ın kendi firmware'inden DOĞRU çıkar (prior yarım kaldı, blob B eksik; format
transform + LDPC gerekebilir; yanlışsa MP'de NAND korruption riski), (b) HYV6 paketi (SN9466,
liangchanba admin-kilit — forum kayıt/puan), (c) HYV8 SKV8 ile ikame = RİSKLİ (farklı NAND nesli,
timing yanlış → korruption). Güvenli = (a) doğru reconstruction ya da (b) gerçek paket.

## §14 — MP dosya-provisioning zinciri: nandmem ✓ → SYS firmware → para (bu oturum)
MXMPTool START, gerekli dosyaları sırayla arıyor. İlerleme:
1. ✓ **nandmem_SKV6_page.bin** — akıllı model üretti (byte-exact, 6 clock), `nm2.img` USB ile VM'e
   taşındı, `kopla.bat` ile `C:\MPT\DAT\SKV6\`'ya kopyalandı. Hata GİTTİ.
2. ⛔ **`C:\MPT\SYS\YI0PCA2C.bin`** (SYS firmware, ~692KB "MAS09_FWTAG" formatı) — YOK.
   - Bizde: `YIQZCA2C.bin` (HYV7/SKV7, yanlış proje, `r:/DVT/skv7_9286`).
   - Bizim proje: **YI0PCA2C** (HYV6_64GB, twin GiGimundo YI0PCELC). Gated HYV6 paketinde.
   - Drive'ın KENDİ firmware'i doğru olan (dump'ımız var: `kanit/nand_yedek_20260915/blok0_tam.bin`,
     `c3ce2_blok0_tam.bin`, `re/fw_canli/e*.bin`) ama 692KB paketlenmiş SYS.bin'i reconstruct etmek
     nandmem'den büyük (tam fw kodu + MAS09_FWTAG paketleme).
3. ⚠️ (sıradaki muhtemel) **para dosyası** — MPTOOL.ini `ExtParaFile=Para_DW_SKV7_64GB_FULL_NO_RAID.ini`
   (SKV7, bizim SKV6 için yanlış olabilir).

### §14.1 İki yol
- **A. Her vendor dosyasını drive'ın dump'ından reconstruct** (nandmem gibi, akıllı model). SYS
  firmware büyük+belirsiz; para daha küçük. Otoritatif (drive'ın kendisi) ama çok parça.
- **B. Gated HYV6 paketini al** (SN9466, liangchanba) — SYS firmware + para + tüm DAT **hepsi bir
  arada**. Birden çok dosya gerektiğinden artık DAHA verimli. Ama kayıt+puan/admin-kilit → elle.
- (C) Test Items'ta "Download" kapatıp SYS firmware'siz sadece SORT+preformat? → die-b dışlanır ama
  sistem-blok yeniden kurulmadan WP düzelir mi BELİRSİZ; riskli, önerilmez.

**Durum:** MP yolu ÇALIŞIYOR (MXMPTool + nandmem kanıtladı). Kalan: tam HYV6 vendor paketi (reconstruct
ya da gated indir). VM açık, MXMPTool START'ta YI0PCA2C.bin arıyor. Drive GÜVENLİ (erase olmadı).

## §15 — SYS FIRMWARE DUVARI (2026-09-25) — MXMPTool full-MP artık kanıtla blokaj
Bağlam: §13'te nandmem çözüldü (NANDMEM_GOREV.md SONUÇ), MXMPTool START ilerledi, **2. blokaj
= `C:\MPT\SYS\YI0PCA2C.bin` bulunamadı**. Bu oturumda SYS firmware yolu **kanıtla kapandı**:

### §15.1 Ölçülen gerçekler
- **Drive'ın kendi firmware'i = ZI0PCD2C** (V6, Ekim 2023). Kanıt: `MKSSD_501003000124620000,
  Oct 31 2023,...,MAP1202,ZI0PCD2C` — loader sayfalarında (loader_orijinal/src_p*_m2.bin @off 502).
- **"YI0PCA2C" drive'ın HİÇBİR dump'ında yok** → MXMPTool onu drive'dan okumuyor, **config'imden
  türetiyor** (kurduğum HYV7+SKV6 melez config). Dönüşüm: proje ZI0P→YI0P, config CD2C→CA2C
  (muhtemelen "kurulu fw"→"fabrika-taze fw" normalizasyonu). MXMPTool exe: `SYS\` + `%s.bin`,
  `%s` cihaz-türetimli; config `FWOneBinName=SKV6.bin` ama START auto-derive kullanıyor.
- **Elimizdeki/ulaşılabilir HİÇBİR SYS firmware V6 DEĞİL:** YIQZ*=HYV7 (build path r:/…/HynixV7),
  YIC5*=HYV8 (r:/07-release/00_Release/**HynixV8**/Release_241127). MRRH/KC2R/JQYO vs. = başka
  NAND/proje. Bizim drive = **HYV6**. YIC5CA2C'yi YI0PCA2C diye flash etmek = **V6 donanıma V8
  firmware = brick** (flash ETMEDEN önce build-path'e bakıp yakalandı).
- **Reconstruction güvenilmez:** ZI0PCD2C NAND'da sadece loader (version tag) + RAM imajları
  (re/fw_canli/e00,e04,e10,e11 — MKSSD var, MAS09_FWTAG YOK) olarak var. Paketli SYS .bin
  (708KB, MAS09_FWTAG + CODE_ENTRY tablosu) hiçbir dump'ta yok; partial post-load RAM'den geri
  paketlemek = yüksek brick riski. Smart-model bu işte 2 kez flag yedi (statik fw karşılaştırma).
- **Public kaynak yok:** usbdev.ru (403), flashinfo.top (sadece HYV7/HYV8), web arama → HYV6
  MAP1202 paketi public'te yok. Forum HYV6 (SN9466) admin-kilitli (Alperen giremiyor).

### §15.2 Reconcile: neden MP yine de "doğru" araç ama biz kullanamıyoruz
- §11.8 duvarı (config die-map checkpoint'i taşımıyor, fiziksel presence kullanıyor) HÂLÂ geçerli.
- MP'nin die-exclude'u ÇALIŞIR çünkü MP **fabrika bad-die statüsünü** yazar (config die-map DEĞİL) —
  firmware Flash_ID scan SONRASI bu fabrika tablosunu okuyup tam-bad die'ı sistem-die kümesinden
  çıkarır. `SortMaxBadBlockPerDie` eşiği die-11'i (226 bad) otomatik tam-bad yapar.
- AMA MXMPTool full-MP akışı `EnDownload=1` → SYS firmware indirmek İSTİYOR → YI0PCA2C.bin şart →
  **elimizde yok.** Yani "temiz araç" yolu, olmayan V6 firmware'e takılı.

### §15.3 Geriye kalan yollar (firmware-BAĞIMSIZ olmalı) + brick riski
- **P1 — MXMPTool sort-only (firmware download'suz):** MXMPTool'un bad-block sort/RDT fazının
  fabrika bad-die statüsünü (die-11 tam-bad) firmware download OLMADAN yazıp yazmadığını test et.
  Yazıyorsa: sort çalıştır → die-11 fabrika-bad → drive'ın KENDİ firmware'i boot'ta checkpoint'i
  sağlam die'a atar → yazılabilir. AÇIK SORU: sort, bad-die statüsünü download'dan mı yoksa
  RDT'den mi commit eder + START SYS-fw check'i EnDownload'a bağlı mı. Risk: erase varsa + fw
  yoksa brick. Test VM'de config ile (EnDownload=0, EnEraseAllBlocks=0 önce gözlem).
- **P2 — GDP tünel-replikasyon (§11.9-A/§11.10):** fabrika bad-block/die-status yapısının NAND
  konumu+formatını çöz, die-11'i tam-bad yaz, drive'ın firmware'ini KORU. En çok kontrol, en
  derin RE, brick riski en yüksek. Linchpin: fabrika bad-die tablosunun format/konumu (MP tool'un
  YAZMA yolunu RE etmek, firmware'in garbled OKUMA yolundan daha temiz olabilir).
- **P3 — read-only 960GB kabul.** Alperen bunu İSTEMİYOR ("geri döndüreceğiz", yazılabilir hedef).
- ⚠️ **Brick riski gerçek:** P1/P2 yanlış giderse read-only 960GB arşiv de gider (total brick,
  re-MP için V6 firmware gerekir ki yok). Alperen: data disposable + agresif OK + yazılabilir hedef.

## §16 — ⭐⭐⭐ SORU 4 ÇÖZÜLDÜ: kod-patch'i reddeden = 32-baytlık digest (2026-09-25)
Kullanıcı "integrity check'i kır" yolunu seçti. ROM disasm (capstone, re/maskrom_FFFF0000.bin) ile
**kesin mekanizma bulundu** — prior session'ların açık bıraktığı Soru 4:

### §16.1 Mekanizma (ROM 0xFFFF0FD0 = kod-chunk yükleyici)
- ROM, die-seçim + 3 magic kapısını (BLOCKS/CONFIG/LDPC-TABLE memcmp; §BOOTDIE) geçen loader'ı
  `0xFFFF13C2 bl 0xFFFF0FD0` ile yükler. 0xFFFF0FD0 section-descriptor loop'u (16-baytlık girdiler,
  taban r4=**0x040304EC**, page 0'dan kurulu): her section size[+4], addr[+8]/[+0x94], flags[+0x9c],
  page[+0x190], tip = `[+0x9c]>>4`.
- **Digest yalnız tip-0xa (KOD) sectionları kapsıyor** (`0xFFFF1022` ve `0xFFFF11BE cmp #0xa, r7>>4`).
  Section verisi `0xFFFF6D4C`/`0xFFFF6A40` (ARM, software 256-bit hash) ile sp+0x10'daki 32-baytlık
  digest'e işleniyor.
- **KAPI (0xFFFF1242-124E):** `memcmp(stored=[r4+0x60]=0x0403054C, computed=sp+0x10, 0x20)`.
  Farklı → 0xFFFF1250 hata printf → **r0=0 döner = load FAIL → fabrika fallback.** (ctx[0x470]≠1,
  yani cert kapalı olan bizim boot'ta bu memcmp yolu aktif; cert açık olsa 0xFFFF126A HW-crypto yolu.)
- **ÇELİŞKİ ÇÖZÜLDÜ:** config patch (page 122: Func0 0x398, die-map 0x3E0/0x400) tip-0xa DEĞİL →
  digest'e girmiyor → boot eder. Kod patch (page 119 gate, page 113 mode) tip-0xa → digest bozulur →
  memcmp fail → fabrikaya düşer. wpgate/modfix'in neden düştüğü, wpfix'in neden düşmediği = TAM BU.

### §16.2 Hash kimliği (kırma için kalan iş)
- 32 bayt (256-bit), software (crypto MMIO 0x0670xxxx bu fonksiyonlarda YOK), core 0xFFFF6A18/0xFFFF69BC.
- **Standart SHA-256 DEĞİL** — ROM'da SHA-256 K-tablosu (0x428a2f98) ve H0 (0x6a09e667) YOK.
  Custom hash ya da K'yı runtime üreten varyant. 0x1000-baytlık chunk işliyor, uzunluk bit cinsinden eklenir.
- **KIRMA PLANI (2 seçenek):**
  (a) **Emülasyon (tercih):** Unicorn ile 0xFFFF6D4C/6A40'ı ROM'dan koştur → fabrika tip-0xa sectionları
      üzerinde digest hesapla → page 0'daki stored digest [desc+0x60] ile EŞLEŞTİĞİNİ doğrula (ground-truth
      kanca) → sonra kod-patch'i uygula, digest'i yeniden hesapla, page 0'da güncelle. Algoritmayı elle
      çözmeye gerek yok.
  (b) Elle reverse (0xFFFF6A18/69BC/CDD8 core) → Python replikasyon.
- **Sonra:** patched kod sayfası + güncellenmiş page 0'ı ldr_yaz ile yaz (16-die FABRİKA base'de, die-exclude
  confound'suz). Fix = gate `tst#8→tst#0` VEYA mode=3 writer cap; bit3=1 KALIR (boot escape/NVMe). Digest
  düzeldiği için artık boot'tan sağ çıkmalı → **yazılabilir, firmware-bağımsız.**
- ⚠️ Açık risk: (1) hash keyed olabilir (o zaman emülasyon yine çalışır ama offline replikasyon key ister —
  emülasyon key'i ROM'dan alır, sorun değil); (2) digest section-descriptor'da mı yoksa ayrı magic-page'de mi
  saklanıyor kesinleştir (page 0 [desc+0x60] güçlü aday); (3) page 0 değişikliği başka magic'i bozmamalı
  (page 0 sadece "LDBK BLOCKS/CONFIG" memcmp'le korunuyor, digest'le değil → serbest güncellenebilir).

## §17 — integrity = HW-crypto 256-bit digest (0x06305000 motoru) (2026-09-25)
- Digest'i hesaplayan `0xFFFF6D4C/6A40` → core `0xFFFF6A18`: `ldr r2,=0x06305000` (HW crypto motoru),
  `for i in 0..7: str 0,[base+0x14+i*4]` → **8×32-bit state (256-bit) init** = **SHA-256-ailesi HW engine**.
  Motor MMIO 0x06305000 (state @ +0x14..+0x30). Bu yüzden ROM'da SHA sabiti yok (HW'de).
- **Neden düz SHA-256(chunk1) eşlemedi:** ya zero-IV, ya per-section framing/byte-swap, ya motor
  farklı state okuma. Emülasyonla çözülecek.
- **KIRMA HARNESS'İ (kuruluyor, Unicorn 2.1.4):** `0xFFFF0FD0` kod-yükleyiciyi emüle et
  (NAND-read 0xFFFF07F8/0xFFFF0886 hook'lu → loader sayfaları besle) + **motor MMIO 0x06305000 hook'lu:
  data-in reg'e yazılanı YAKALA = motorun hash'lediği tam bayt dizisi.** Offline o dizinin hash'ini
  al (SHA-256 vs.), page0[0x70]'teki stored digest (=`bfd532c1 1a2529d9 974ce233 20497fbf 92ef8463
  4df3fdc9 4020c369 d397ab1a`) ile eşleştir → algoritma+input KESİNLEŞİR. Sonra patched loader'da
  yeniden yakala→hash = yeni digest, page0[0x70]'e yaz. Fix = gate/mode kod-patch + bit3=1, digest
  düzeltilmiş → boot sağ çıkar → yazılabilir, firmware-bağımsız.
- Araçlar: `re/maskrom_FFFF0000.bin`, chunk1 (loader p108-119 @0x040C0000), scratchpad ucvenv/unicorn.
- Kalan: harness'i tamamla (NAND hook signature 0xFFFF0886 dest çöz) → factory validate → patch → cihaz testi (replug).

## §18 — ⭐⭐⭐⭐ INTEGRITY CHECK KIRILDI + FIX HAZIR (2026-09-25)
### §18.1 Kirilan formul (Unicorn emulasyonu + byte-exact dogrulama)
- ROM 0xFFFF0FD0 kod-yukleyici: descriptor'da (page 0'dan kurulu, 0x040304EC) **12 section**;
  10 tanesi **tip-0xa (kod, hash'lenen)**, kaynak loader page'leri **92..121** (her section
  [+0]=bas_page [+2]=bit_page, [+4]=len, [+8]=addr, [+0xc]=flags; tip=(flags&0xff)>>4).
  Tip-0xa section addr'leri: 0x0,0x800000,0x804000,0x040c4000,0x02000000,0x02800000,0x04060000,
  0x040d0000(gate+mode BURADA),0x040c0000,0x040cc000. Config section (page 122) tip 0x0 -> hash'lenmez.
- Digest HW crypto motoruyla (0x06305000, standart SHA-256) hesaplanir, **cikti 32 bayti TERS**.
- **FORMUL (byte-exact dogrulandi):** `page0[0x70:0x90] = reverse( SHA256( concat(loader pages 92..121) ) )`.
  Fabrika loader_v4'te birebir tutuyor. ROM bunu 0xFFFF1246 memcmp'le kontrol; fark -> fabrikaya duser.
- **Neden config patch boot edip kod patch bozuyordu:** kod (page 92-121, ozellikle 113/119) digest'e
  girer, config (page 122) girmez. wpgate/modfix'in 5-slot'a ragmen dusmesi = digest, tutarlilik degil.
- Araclar: `re/integrity/h2.py` (Unicorn harness: descriptor build + section dump), `re/integrity/patch_loader.py`
  (patch + digest recompute + self-verify), scratchpad `ucvenv` (unicorn 2.1.4 + gmssl).

### §18.2 Fix hazir (cihaza yazilmayi bekliyor)
- **`kanit/loader_v4_modfix_digest`** (TERCIH): fabrika 16-die + page113@0x27F0 `03->00` (mode=3 writer
  0x040D67F0 -> mode hic 3 olmaz -> gate `mode∈{3,4}` FALSE -> 30 kapi acik) + **digest yeniden hesaplandi**
  (page0[0x70]=`2a4bc191...`). **Func0 bit3=1 KORUNDU** (0x398=0x0A) -> boot escape/NVMe servis eder.
- **`kanit/loader_v4_wpgate_digest`** (ALTERNATIF): fabrika + page119@0xA6 `08->00` (tek gate) + digest.
- Ikisi de self-verify gecti: cikti page0 digest == reverse(SHA256(p92-121)) -> ROM KABUL EDER (matematiksel
  kesin; formul fabrika verisiyle kanitli). KALAN BILINMEYEN: mode-cap LOGIC'i (mode<3 hem boot ettiriyor
  hem yaziyor mu) -> yalniz cihaz testi gosterir. Reversible (loader_v4 yedek + ROM fallback).

### §18.3 Cihaz test plani
1. Drive tel-tak (wire-in ROM-GDP modu) -> replug (Alperen).
2. `port/gdp_bootstrap.py` ile GDP moduna al (readcap=1395 dogrula).
3. `sudo env JDKAYNAK=kanit/loader_v4_modfix_digest python3 port/ldr_yaz.py --yaz` (die 0 block 0'a yaz).
4. Replug -> urun modu -> boot -> olc: Func0 bit3(=1 beklenir), mode(<3 beklenir, 0x00810CE8),
   NVMe servis (readcap=1875385008=960GB? veya 1024GB), host-write testi (kopru/urun_yazma_test.py).
5. Yazilabilirse -> BITTI. mode hala 3/4 veya boot bozuksa -> wpgate dene / mode mekanizmasi derinlesir.

## §19 — CIHAZ TESTI-1: digest crack CIHAZDA CALISTI; mode-cap escape'i bozuyor (2026-09-25)
- GDP bootstrap OK (replug sonrasi), `loader_v4_modfix_digest` die 0 block 0'a yazildi (yazma hata=0,
  dogrulama=0, page122 die=16 fabrika). Yedek: `kanit/c0ce0_blok0_yedek_0925_0118`.
- Replug -> urun modu. Olcum: **readcap=1 (96s+ sabit), INQUIRY calisiyor (seri DD56419883914),
  vendor ReadRam tuneli hang, LED surekli mavi yanip sonuyor (aktivite)**.
- **YORUM (yuksek guven):** surekli aktivite = die-11 retry storm. Fabrikaya DUSSEYDI settle olurdu.
  Yani: (1) **DIGEST CRACK CIHAZDA DOGRULANDI** — ROM ilk kez kod-patch'li loader'i KABUL ETTI
  (digest yeniden hesaplandigi icin fabrikaya dusmedi). (2) **mode-cap yanlis lever:** mode=3'u
  engellemek die-11 abort/escape'ini de engelliyor (WP-off/M1 gibi) -> retry storm -> hang.
- **Cikarim:** escape mode->4'e bagli. Dogru fix: mode/bit3 DOKUNMA (escape/boot calissin), yalniz
  write-GATE'i ac. -> `loader_v4_dualgate_digest` uretildi (page113@0x2CC8 + page119@0xA6 iki loader
  write-gate'inin bit3-testi neuter; mode logic intact; digest=`ab354e0c...`). SIRADAKI TEST.
- ⚠️ Risk: host-write yolu SYS-fw'deki (e04 0x0200xxxx, loader'da degil) gate'lerden de geciyorsa
  iki loader-gate yetmeyebilir -> genislet. Reversible (yedek + ROM fallback).

## §20 — CIHAZ TESTI-2: dualgate BOOT+SERVIS OK; data-path die-11'de takili (2026-09-25)
### §20.1 BUYUK KAZANIM: disk canli
- `loader_v4_dualgate_digest` (fabrika 16-die + 2 write-gate acik + digest duzeltildi, mode/bit3
  DOKUNULMADI) yazildi. Telsiz replug -> **BOOT ETTI, ESCAPE CALISTI** (LED sabit=retry storm YOK).
- **Drive tam 1TB NVMe olarak SERVIS ETTI:** readcap=2000409264 (1024GB), **MN='JAMESDONKEY JD1024 1TB'**,
  Func0 bit3(WP)=1, mode=3, die=16. Aylardir ilk kez disk gercek urun olarak ayaga kalkti.
- **Integrity crack CIHAZDA %100 dogrulandi** (kod-patch'li loader kabul edildi, fabrikaya dusmedi).

### §20.2 ⭐ YENI SUPERGUC: TUM firmware patchlenebilir
- Hash'lenen loader blok 0 (page 92-121) yalniz boot loader DEGIL -> **tum urun firmware**: sectionlar
  0x0, 0x800000, **0x02000000 (FTL)**, 0x04060000, 0x040Cxxxx. Dogrulandi: pages 101-106 == e04
  (product RAM 0x02000000) byte-exact. e04 string'leri: Maxiotech_MAP, NVMe_SSD, Hynixv, MKSSD_, BT_WP.
- Yani `patch_loader.py` + digest recompute ile FTL/checkpoint/die-set KODUNUN herhangi yerini
  patchleyip ROM'a kabul ettirebiliriz. **Die-exclude icin MP/vendor firmware ARTIK GEREKMIYOR** --
  firmware patch ile die-11'i FTL'den cikarabiliriz (integrity crack bunu acti).

### §20.3 KALAN: data-path "becoming ready" (die-11)
- SCSI READ(10) LBA0 -> **"Not Ready: Logical unit is in process of becoming ready"** (ASC 04/01),
  110s+ sabit (readcap/identify calisiyor). usb-storage block device attach edemiyor (data read fail).
- Yorum: escape boot'u bitiriyor ama FTL init/checkpoint die-11'de yakinsamiyor -> data-path hazir
  olmuyor. Bu, die-11 KOK problemi (die-exclude gerektiren). Write-gate acildi ama FTL data yolu die-11
  yuzunden calismiyOR.
- ⚠️ dualgate gate'leri acinca FTL init'te yazmayi deneyip takiliyor olabilir (fabrika WP-closed'da
  temiz read-only-ready oluyordu). Yani "yazilabilir" icin die-11'i FTL'den cikarmak SART.

### §20.4 SIRADAKI: FTL die-11 firmware patch (artik mumkun)
- Hedef kod (§11.6, hepsi hash'li loader blok 0'da, patchlenebilir): TBLK allocator e04 0x02001308+,
  CHKP state machine e04 0x02002854+, sys-sts-fail e00 0x000047CC, BBT writer e07 0x040DA2BC,
  blok-status tablo 0x04001540 (§11.10). Fikir: FTL die-set'ini/checkpoint allocator'ini die-11'i
  ATLAYACAK sekilde patchle (mode-cap gibi bir immediate/branch degisimi) -> data-path becoming-ready'den
  cikar -> yazilabilir. Emulasyon (h2.py) + disasm ile die-11 handling'i bul, patchle, digest, yaz, test.
- Drive su an dualgate durumunda (boots+metadata, data becoming-ready). Guvenle cikarilabilir.

## §21 — EN GUCLU ADAY: 15die+dualgate (2026-09-26)
- ⭐ DUZELTME (ANALIZ_CEVAP + BASLA_BURADAN): brief'in "15-die servis etmiyor" onculu KONFLASYONDU.
  Gercek: **15-die (WP-ON) NVMe SERVIS EDIYOR** (§35.4+re/urun_jms). NVMe'yi bozan WP-OFF (bit3=0), 15-die degil.
- §20'de 16-die dualgate'in "becoming ready"'de takilmasi = die-11 hala DATA die-map'te, gate acilinca FTL
  die-11'e yazmaya calisip takiliyordu. **Cozum: 15-die config (die-11'i DATA die-map'ten cikar).**
- **`kanit/loader_v4_15die_dualgate_digest`** uretildi: loader_v4_15die base (die_cnt=15, die-11=0x13=CE2/CH3
  DATA-map'ten cikarilmis, Func0 bit3=1 WP-ON) + dualgate gate patch (page113@0x2CC8 + page119@0xA6 write-gate
  bit3-testi neuter) + digest yeniden hesaplandi (page0[0x70]=ab354e0c...). Self-verify OK.
- **BEKLENEN:** boot biter (bit3 escape checkpoint'i abort eder) -> data 15-die map kullanir (die-11 atlanir ->
  DATA hang YOK -> becomes ready) -> gate acik -> iyi die'lara host-write GECER = yazilabilir ~937GB.
- TEST: tel-tak (ROM 1395) -> gdp_bootstrap -> ldr_yaz JDKAYNAK=loader_v4_15die_dualgate_digest --yaz ->
  tel-cikar -> boot -> readcap/becoming-ready? + SCSI WRITE testi (block device dd, /dev/sd DOGRULA USB+1TB).
- ⚠️ /dev/sda = SISTEM DISKI (INTEL SATA)! JD1024 = USB 2000409264 sektor. Yazmadan ONCE cihaz kimligini dogrula.

## §22 — DUALGATE HATASI + DUZELTME: 15die+wpgate (2026-09-26)
- §21 15die_dualgate cihazda: readcap=1875385008 (960GB, 15-die ETKILI!) AMA data-path HALA
  "becoming ready" (ASC 04/01), READ/WRITE DID_ERROR. usb-storage block device attach edemiyor.
- ⭐ KOK NEDEN: dualgate IKI gate'i de neuterladi. `0x040D6CC6 "wp no q-wr"` aslinda die-11
  checkpoint yazmasini ABORT eden escape mekanizmasi ("WP'de yazmayi kuyruga ALMA"=atla). Onu
  neuterlayinca firmware die-11'e yazmayi DENIYOR (abort etmiyor) -> hang -> surekli becoming-ready.
- DUZELTME: **sadece host-write gate (0x040EC0A4) ac, abort (0x040D6CC6) KORU.**
  `kanit/loader_v4_15die_wpgate_digest`: 15-die + page119@0xA6 host-gate acik + page113@0x2CC8
  ABORT KORUNDU (0x08) + Func0 bit3=1 + digest (abf0d851...). BEKLENEN: checkpoint abort->becomes
  ready + host-write acik + data die-11 atlar = yazilabilir 960GB.
- TEST: tel-tak->yaz->tel-cikar->boot. ⚠️ Bu sefer UNDISTURBED ~60s bekle (hammer etme, becoming-ready
  yakinsamasi icin), sonra tek READ + WRITE testi. Cihaz kimligi USB+1875385008 sektor (sda=sistem!).

## §23 — 15die+wpgate: metadata OK, data-path HALA becoming-ready (2026-09-26)
- 15die_wpgate (abort korundu): readcap=1875385008 (960GB, 15-die) AMA data READ/WRITE hala
  DID_ERROR + "becoming ready" (ASC 04/01). Yani gate config (dualgate VS wpgate) data-path'i
  DEGISTIRMIYOR -> sorun gate degil, **FTL data-init die-11 checkpoint'inde takili**.
- KOK: die-11'in checkpoint/sistem-bloklari (fiziksel, §11.8) FTL init'i bloklıyor. 15-die config
  metadata geometrisini (960GB) veriyor ama NAND'daki FTL yapilari (L2P/checkpoint/super-block) hala
  16-die-zamani + die-11 referansli -> FTL yukleyemiyor -> becoming-ready sonsuz.
- COZUM = FTL'yi die-11'siz YENIDEN INSA ettirmek (MP low-level format'in yaptigi). Yollar:
  (a) firmware'in kendi rebuild/format'ini tetikle (komut/config-flag), (b) FTL checkpoint-load kodunu
  patchle: checkpoint-read-fail -> retry yerine TEMIZ REBUILD'e dus (die-11 atla). Ikisi de derin.
- Uzun-undisturbed-wait testi (die-11 retry tukenir mi) arka planda.

## §24 — DURUM DEGERLENDIRME (2026-09-26): duvar = die-11 FTL rebuild
Denenen ve SONUC:
- 5dk undisturbed wait: hala becoming-ready (kendi yakinsamiyor).
- NVMe Format NVM (SES=1): REDDEDILDI ("Illegal Request/Invalid field") + namespace faulted (ASC=44).
  Firmware faulted namespace'de Format yapmiyor.
- FTL hand-patch RE (checkpoint EH-WRT e07 0x040E993C, sys-sts-fail e00 0x000047CC, TBLK e04): kod
  referanslari basit ADR/literal ile izlenmiyor, state-machine karmasik; temiz/guvenli patch noktasina
  YAKINSAMADI.
### Basarilan (kalici):
- Integrity check KIRILDI (dogrulandi, cihazda calisti) -> firmware ozgurce patch'lenebilir.
- Disk bizim patch'li firmware'imizi boot ediyor; 15-die config etkili -> **960GB metadata servis ediyor.**
### Duvar (dogrudan die-11 donanim):
- Data I/O "becoming ready"de sonsuz takili: FTL data-init die-11 checkpoint'ini (fiziksel, block 7)
  yazamiyor. Gate/config/format/wait bunu cozmuyor. Cozum = FTL'yi die-11'siz YENIDEN INSA (MP low-level
  format). Firmware bunu kendisi yapmiyor (faulted); hand-patch ile zorlamak derin + belirsiz (yakinsamadi).
### Kalan gercek yollar (hepsi derin/belirsiz):
- (a) FTL checkpoint/rebuild kodunu tam cozup patchle (state-machine derin).
- (b) Firmware'in MP/sort vendor-komutunu bul+tetikle (RE).
- (c) GDP tunel-replikasyon: bad-die tablosunu elle yaz (brick riski).
- (d) Vendor MP firmware (YI0PCA2C) bulunursa MP artik daha kolay calisabilir (disk boot ediyor).
- Cihaz durumu: 15die_wpgate yuklu (boot+960GB metadata, data becoming-ready). Guvenle cikarilabilir.
