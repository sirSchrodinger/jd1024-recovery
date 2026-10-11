# JD1024 write-restore — analiz cevabı (2026-09-24)

> Bu, `ANALIZ_BRIEF_2026-09-24.md`'nin istediği yazılı analiz. **Cihaza hiçbir komut
> gönderilmedi**; tümü diskteki dump/disasm/notlardan statik. Her iddia dosya+ofset+disasm
> veya ölçümle gerekçelendirildi. Müdahaleyi (NAND yazma / power-cycle) Alperen ayrı bir
> oturumda yürütecek.

---

## 0. TL;DR — iki cümlelik cevap

1. **Brief'in ana öncülü (§3.1 / Soru 1) yanlış kurgulanmış.** "die-exclude (15-die) ürün
   modunda NVMe servis etmiyor" iddiası ham kayıtla **çelişiyor**: 15-die config (`loader_v4_15die`,
   WP açık) ürün modunda NVMe'yi **servis etti** (§35.4 ölçümü + `re/urun_jms/` canlı RAM dump'ı:
   mode=3, assert=3, 15 die, 960 GB, ReadRam çalıştı). ASC=44 veren config **die-exclude değil,
   `wpfix`** (15-die + Func0 bit3=0, yani **WP'nin kapatıldığı** config).

2. **Gerçek mekanizma:** `Func0` bit3 (`EnWriteProtectAbort`) sadece bir yazma-kilidi değil,
   firmware'in **boot'u die-b arızasına rağmen tamamlamasını sağlayan kaçış kapısı**. WP açıkken
   die-b'nin boot-anı sistem-blok yazması patlayınca firmware "abort" edip read-only'e geçiyor ve
   **boot bitiyor** → NVMe servis ediliyor. WP'yi kapatınca (bit3=0) bu kaçış yok oluyor; firmware
   die-b'ye program/erase denemeye devam ediyor, boot yakınsamıyor → her komuta **internal target
   failure (ASC=44)**. Yani: **die-exclude NVMe'yi bozmuyor; WP'yi kaldırmak bozuyor.**

**Sonuç:** Config/loader düzeyinde "yazılabilir + NVMe-ready + kalıcı" **aynı anda imkânsız**,
çünkü die-b fiziksel olarak dizide durdukça: WP açık → yazılamaz; WP kapalı → boot bitmez.
Bu üçlüyü ancak **die-b'ye fiziksel yazmayı tümüyle durduran** bir çözüm (sistem-blok relocation =
MP-eşdeğeri) kırabilir. **AMA** ASC=44'ün ölçüm-artefaktı (boot çok yavaş) olma ihtimali kesin
elenmedi — ve elenirse `wpfix` **zaten çalışıyor** olabilir. O yüzden bir sonraki oturumun **tek
en değerli adımı** ucuz-kesin bir testtir (§Soru 5, Adım 1): `wpfix`'i **uzun beklemeyle** (5-10 dk +
CSTS.RDY poll) yeniden dene.

---

## 1. Kritik düzeltme — brief §3.1 bir konflasyon

Brief §3 tablosu D satırı ("die-exclude: ürün modu NVMe servis etmiyor (bak §3.1)") ile §3.1
(tamamen `wpfix` hakkında) **aynı sonucu iki farklı config'e** atfediyor. Ham kayıt bunları ayırıyor:

| Config | Func0@0x398 | die | LBA | Ürün-modu sonucu | Kaynak |
|---|---|---|---|---|---|
| Fabrika 16-die (`loader_v4`) | `0x0001F80A` (bit3=1, WP açık) | 16 | 2000409264 (1024 GB) | **Servis ediyor** (Identify/ReadRam OK, mode 3/4) | §32.2, Dev 019 |
| **15-die (`loader_v4_15die`)** | `0x0001F80A` (**bit3=1, WP açık**) | 15 | 1875385008 (960 GB) | **SERVİS EDİYOR** (mode=3, assert=3, ReadRam OK) | **§35.4 + `re/urun_jms/`** |
| `wpfix` (15-die + bit3=0) | `0x0001F802` (**bit3=0, WP kapalı**) | 15 | 1875385008 | **ASC=44 (hiçbir komut)** | §3.1 |
| `wpfix16` (16-die + bit3=0) | `0x0001F802` (bit3=0) | 16 | 2000409264 | **TEST EDİLMEDİ** | — |

**Doğrulama (ben, bu oturumda):** `re/urun_jms/00000000.bin` (17:39, telsiz ürün modu) →
`0x388=1875385008`, `0x398=0x0001F80A`, `0x3E0=15`, `0x4C6=15`, `Die_2_CeCh(0x400)=00 01 02 03 08 09
0a 0b 10 11 12 18 19 1a 1b ff` (die-b=`0x13` **çıkarılmış**), `00810C00.bin@0xE8 (mode)=3`,
`040EEC00.bin@0x258 (assert)=3`, konum `0x03190712`×3. Bu dump **ReadRam ile alındı** — yani 15-die
config ürün modunda vendor tüneli/NVMe'yi **servis ediyordu**. `loader_v4_15die` ile `loader_v4`
farkı sadece 10 sayfa × 30 bayt config (0x389/0x3E0/0x40b… = die-count/die-map/LBA), Func0'a
**dokunmuyor** (diff doğrulandı).

`loader_v4_15die` → `wpfix` farkı **tek bayt**: sayfa 122/123/…/303 ofset **`0x398`**, `0x0A→0x02`
(sadece bit3). `wpfix` ölçümü (§3.1) **temiz replug, reset fırtınası yok, 60+75 sn** bekleme sonrası
ASC=44 verdi. Yani serves→ASC=44 geçişinin **tek değişkeni Func0.bit3=0 (WP kapatma)**.

> Ders (hafıza kuralı: "özetindeki iddiayı ham kayıttan doğrula"): brief'in ⭐ "bugünkü kritik
> bulgusu" bir konflasyondu. Soru 1'i doğru haliyle sormak gerekiyor: **"WP'yi kapatmak (Func0
> bit3=0) neden ürün-modu NVMe'yi kaldırıyor?"** — die-exclude değil.

---

## 2. Kök-neden zinciri (kesin, disasm+ölçüm)

Tek fiziksel arıza: **die-b = CE2/CH3 = die 11 = c3ce2**, sistem/boot bloklarında erase/program
reddi (`ErrT(6)`, `Sts(f010000)`/`Sts(…e1e1)`). NAND fiziksel sağlam (life %100, aşınma ~%1,
16/16 Flash_ID okunuyor). Zincir:

```
die-b sistem-blok yazması patlar  (EH-WRT CECH(b,b)BLK(7)Sts(f010000), her boot)
  → L2P/map checkpoint yazımı patlar → assert kaydı (op 0x17 → QBT sistem bloğu)
    → assert sayacı *(0x040EEE58) = 3     [artıran: e04 0x0200924C, doygun `cmp #3;bhs`; temizleyen: YOK]
      → mode *(0x00810CE8) = 3            [yazıcı: e07 0x040D67F2, "WRITE-PROTECT", koşul assert≥3]
        → Func0 *(0x398) bit3 == 1?
          → mode = 4                       [yazıcı: e04 0x02006718, koşul mode==3 && Func0.bit3]
```

- assert konumu `*(0x040EEE5C)=0x03190712`, tek bir assert site'ından: e04 **`0x020031F4`**
  (`ldr r0,=0x03190712; str r0,[0x008038B0]; bl 0x2000580`) — L2P/map tutarlılık fonksiyonu
  `0x0200318C` içinde. Bu fonksiyon FTL op-tablosuna kayıtlı (`0x00802E98+0x64`, kayıt e06
  `0x040EB1F8`; ayrıca `0x00800420+0x20` slot'undan `0x0406379E` ile çağrılıyor = L2P map-write).
  Yani kalıcı assert, **die-b üzerindeki L2P map/checkpoint yazmasının** patlaması.

- **Yazma kapıları (30 nokta, hepsi aynı polarite):** `mode∈{3,4} && *(0x398)&8`. Örnek:
  e07 `0x040D6CC6` (`tst.w r0,#8` → "wp no q-wr" = QBT/checkpoint yazmayı iptal),
  e07 `0x040EC0A4` (→ yeni write-stream bloğu **hiç açılmıyor**). bit3=0 → 30'un hepsi normal yola
  döner (kaynak: `re/ANALIZ_WP_BIT.md §5`, `re/ANALIZ_YAZMA_KAPISI.md §2.5`).

- **mode her boot 0'dan başlıyor** (soğuk RAM + e04 `0x020009BA` / e08 global zero), sonra
  `[QBT]S` fazında (e04 `0x0200083C`) NAND'daki assert kayıtları okunup + boot-anı die-b
  yazma hataları **canlı olarak** yeniden birikerek mode 3/4'e tırmanıyor. Yani WP **saklanan bir
  kilit değil, her boot die-b'den yeniden türetilen** bir durum (`re/ANALIZ_DIEREMAP.md §6.2`,
  UART log B5-B7: her boot `EH-WRT CECH(b,b)` → `sys sts fail`).

---

## 3. ★ SORU 1 (yeniden kurgulanmış) — WP'yi kapatmak ürün-modu NVMe'yi neden kaldırıyor?

**Cevap: WP-abort, die-b varlığında boot'un tamamlanmasını sağlayan yük-taşıyan kaçış kapısı.**

Kanıt zinciri:

1. **Boot her seferinde die-b sistem-blok yazmasını deniyor ve patlıyor** — die-count/die-map
   config'ten **bağımsız**. En yeni boot (UART `uart_new` L60127+, `[2231:36:41]`): `BIOS OK` →
   `check ata state` → hemen `EH-WRT:CECH(b,b)BLK(7)Page(2d)Sts(f010000)` → `sys sts fail`. Bu,
   **15-die dump'ında da assert=3 görülmesinin** sebebi: sistem/boot süper-blokları (0-15) fiziksel
   olarak **tüm 16 fiziksel die'a** çizgileniyor; logical die-map (0x400/0x440) sadece **kullanıcı
   veri** geometrisini değiştiriyor, boot-anı fiziksel sistem-blok yerleşimini değil. (SystemInfo:
   `LDR Block=0x03` = loader fiziksel blok 3'te, her die'da.)

2. **WP açıkken (bit3=1) firmware "abort" edip boot'u bitiriyor.** die-b yazması patlayınca yazma
   kapıları (`0x040D6CC6` "wp no q-wr", `0x040EC0A4` blok-açma iptali) devreye girip yazmayı
   **atlıyor**; firmware read-only'e geçip `check ata state` → idle ile boot'u tamamlıyor →
   Identify/ReadRam servis ediliyor. **Bu, fabrika-16 ve 15-die'ın gözlenen davranışı** (ikisi de
   servis ediyor, ikisi de mode 3/4).

3. **WP kapalıyken (bit3=0) kaçış yok.** assert yine 3'e çıkıp mode=3 kuruyor (assert-tetikli, Func0
   bağımsız) ama Func0.bit3=0 olduğu için: (a) mode 4'e yükselmiyor, (b) 30 kapının **hepsi açık**.
   Böylece firmware die-b'ye program/erase/relocate denemeye **devam ediyor**, her seferinde
   patlıyor; boot-kritik commit yakınsamıyor → controller servis edilebilir duruma **hiç ulaşmıyor**
   → köprü her komuta `Check Condition ASC=44 ASCQ=83 (internal target failure)` döndürüyor. Bu,
   `wpfix`'in gözlenen davranışı.

4. **Boot-variant seçimi bunu destekliyor ama asıl kanıt değil:** e04 `0x02000928`–`0x02000944`:
   `mode==3 && Func0.bit3` → `blx 0x2000568` (=`0x04065825`, "[WP-BT]" write-protect boot-table)
   ELSE `blx 0x2000570` (=`0x04065B85`, "[PBT]" normal boot-table). **Ampirik:** UART log'unda
   `[WP-BT]` = **0 kez**, `[PBT]` = 4 kez (ben saydım). Yani pratikte hep normal [PBT] variant
   koşuyor (mode seçim anında henüz 0). Bu, "WP açıkken bile normal boot-table koşuyor ama die-b
   yazması abort edilerek tolere ediliyor" resmini doğruluyor.

**Net:** ASC=44'ün sebebi die-exclude'un geometriyi tutarsız bırakması **değil** (15-die
tutarlı çalışıyor). Sebep, WP-abort'un kaldırılmasıyla firmware'in die-b arızasında **yakınsamayan
bir yazma/relocate döngüsüne** girmesi. WP-abort = fault-tolerance escape.

### 3.1 Rakip hipotez (dürüstçe, elenmedi)
`wpfix` ASC=44'ü için iki mekanizma:
- **M1 (yük-taşıyan kaçış):** yukarıdaki. → `wpfix16` de patlar.
- **M2 (ölçüm artefaktı):** boot gerçekten uzun sürüyor / önceki bir wedge kaldı. §9.2: bir
  açılışta CSTS.RDY **127,5 sn**'de bile gelmemişti; `wpfix` testi 60+75 sn bekledi. Eğer WP-off
  boot'u 135 sn'nin ötesine uzatıyorsa, ASC=44 **erken okuma** olabilir — ve o hâlde `wpfix`
  aslında **çalışıyor**, sadece sabır gerekiyor.

M1 lehine: tek config-biti flip'inin boot'a ~100 sn eklemesi mantıksız; 15-die +37 sn'de RDY
verdi. M2 lehine: §9.2'de gerçekten uzun/takılan RDY görüldü. **Ayırıcı test §Soru 5 Adım 1.**
Bu ayrım kritik çünkü M2 doğruysa **hedef zaten elde** (WP-off yazılabilir disk demek).

---

## 4. SORU 2 — `wpfix16` (fabrika 16-die + Func0 bit3=0) çalışır mı?

**Öngörü: HAYIR (M1 doğruysa) — `wpfix` ile aynı ASC=44.** Gerekçe: problem geometri değil,
"die-b dizide + WP kapalı". 16-die geometrisi die-b'yi **daha da** dahil ediyor; die-b'nin
boot-anı sistem-blok yazması yine patlar, WP-abort yine yok → boot yine yakınsamaz. `wpfix16`'ın
16-die olması bir avantaj sağlamaz çünkü NVMe-ready'yi bozan die-count değil, WP-off.

**Ne zaman anlamlı:** `wpfix16`'ı **başarı beklentisiyle yazmak yanlış**. Tek değeri M1↔M2 ayrımı;
onu da `wpfix` üzerinde daha ucuz yapabiliriz (zaten yazılı; §Soru 5). Eğer yine de test edilirse,
**uzun bekleme + RDY poll** ile ve "beklenen sonuç ASC=44" diye test edilmeli.

**Alt-soru (die-b assert'in WP dışı yan etkisi):** Evet, var ve `wpfix16`'ı riskli yapan da bu.
WP-off'ta assert→mode=3 yine oluyor (assert-tetikli), ama abort kapıları kapalı olduğundan firmware
die-b'ye **gerçekten yazmayı deniyor**. UART log'u die-b'nin **büyüdüğünü** gösteriyor (iki dump
arası yeni erase-fail `0x163,0x196`; Media Errors 150→173). WP-off boot'ları die-b'ye yazma baskısı
uygulayacağından **die-b'yi daha hızlı aşındırabilir** — geri-dönüşsüz değil (life %100) ama net
kazanç yokken die-b'yi hırpalamanın anlamı yok. Bu, `wpfix16`'ı "önce dene" listesinden düşürür.

---

## 5. SORU 3 — daha iyi bir üçüncü yol var mı? (die-b'yi geometriden çıkarmadan kullanımdan düşür)

**Aranan:** NVMe-ready'yi koru (boot'u bozma = WP açık kalsın) AMA die-b'ye fiziksel yazmayı durdur
ki assert hiç türemesin → mode 0'da kalsın → disk normal yazılabilir olsun. Bu, **doğru hedef**:
gerçek suçlu, die-b'nin **sistem/boot bloklarını** tutması ve boot'ta onlara yazılmak zorunda olması.
Normal veri-blok erase-fail'i WP tetiklemiyor (later-bad marking'e gidiyor, `re/ANALIZ_DIEREMAP.md
§6.3`); **sadece sistem/QBT/checkpoint bloğu yazma-fail'i** assert→WP tetikliyor.

Seçenekleri "boot bozar mı / NVMe-ready kalır mı / kalıcı mı / adreslenebilir mi" ile puanladım:

| # | Fikir | Boot | NVMe-ready | Kalıcı | Adreslenebilir | Verdikt |
|---|---|---|---|---|---|---|
| 3a | Config die-remap (0x400/0x440/0x3E0) ile die-b'yi çıkar | OK | Evet (15-die kanıtlı) | Evet | — | **Yetersiz** — sistem blokları fiziksel; die-b yine yazılıyor (§3.1). assert yine türer. |
| 3b | Firmware'e "bu fiziksel die bad, atla" dedirt (config) | — | — | — | — | **Yok** — `BadDie/ScanDie/DieFail/ROMode` string'i 530 dosya + 12 dump'ta **0** (`DIEREMAP §6.3`). Runtime fiziksel die-exclude knob'u YOK; bad-block sadece **blok** düzeyinde. |
| 3c | ROM presence-bitmap'ten die-b'yi düşür (`0x04030052`) | Bozar | — | — | — | **Hayır** — bitmap HW-probe'dan doluyor (`0xFFFF1860`, READ status==0xE0); die-b okunabildiği için probe'a yanıt veriyor (`ANALIZ_BOOTDIE_SECIM §2.1/§7`). Config değil. |
| 3d | assert eşiğini yükselt (`cmp #3`) | Bozar (kod) | — | — | — | **Hayır** — eşik CODE'da (e07 `0x040D67DE/E4`, e04 `0x02009254`), sabit `#3`. Kod-patch ROM tarafından reddediliyor (§Soru 4). |
| 3e | QBT'deki assert kaydını temizle (GDP tünel) | OK | Evet | **HAYIR** | **Hayır** | die-b bir sonraki boot'ta yine yazıp patlar → assert **canlı yeniden birikir** (UART B7). Ayrıca QBT muhtemelen blok>1024'te → **adresleme duvarı** (§35.6). Temizlik kalıcı değil. |
| 3f | Sistem/boot süper-bloklarını **sağlam die'lara relocate et** + die-b'yi fiziksel bad-block | OK | Evet | **Evet** | zor | **Tek gerçek çözüm** — ama bu tam olarak **MP-eşdeğeri** (§6). Config-lever bunu ifade edemiyor. |

**Sonuç:** Temiz bir config-only üçüncü yol **yok**. die-b fiziksel olarak sistem-alanını tuttuğu ve
firmware'in fiziksel "die-skip" knob'u olmadığı için, WP'yi türetmeyi durdurmanın tek yolu die-b'nin
sistem-bloklarını fiziksel olarak devreden çıkarmak = sistem relocation + fiziksel bad-block = MP.
Bu, önceki agent verdict'iyle (§26: "tek fix die-b dışlamalı full MP") **aynı yere** çıkıyor, ama
artık **nedeni disasm ile net**: config die-exclude sistem-blok fizikselliğini değil, yalnız veri
geometrisini değiştiriyor.

---

## 6. SORU 4 — kod-patch neden boot bozuyor, config neden bozmuyor?

**Mekanizma: ROM boot loader seçimi bir bütünlük kapısıdır; config sayfaları o kapının içinde
"veri", kod sayfaları "doğrulanan içerik".**

ROM her die'ın blok 0 sayfa 0'ını okuyup **üç magic memcmp**'i geçiriyor (`ANALIZ_BOOTDIE_SECIM
§3`): `"LDBK BLOCKS V00"` + `"LDBK CONFIG V00"` (`0xFFFF0D88`, memcmp `0xFFFFD2B4`) ve
`"LDBK LDPC TABLE1"` (`0xFFFF0EEC`). Bu magic'ler ve onları taşıyan sayfalar **LDPC (ECC) ile
korunuyor**: ROM sayfayı **kendi hardcoded ldpc/scr modunda** okuyor.

- **Config-sayfa düzenlemesi (Func0, die-map, LBA @ 0x389/0x398/0x3E0/0x400/0x440):** magic
  bölgelerine ve kod bölgelerine dokunmuyor; sadece parametre alanı değişiyor. LDPC yazma yolunda
  (GDP 0x8A) **yeniden encode** edildiği için ROM okumada tutarlı → magic'ler geçiyor → boot ediyor.
  (Empirik: 15-die, wpfix, wpfix16 hepsi bu bölgede; 15-die kanıtlı boot etti.)
- **Kod-sayfa düzenlemesi (`wpgate` p119@0xA6, `modfix` p113@0x27F0):** çalıştırılan Thumb kodunu
  değiştiriyor. İki mekanizmadan biri boot'u bozuyor: **(a)** değişen sayfa bir magic/LDPC-korumalı
  sayfaya denk gelip ROM okuma-modu tutarsızlığı yaratıyor (memcmp fail → die reddi → fabrikaya
  düşme), **veya (b)** kod gerçekten çalışıp farklı davranınca bir sonraki init fault ediyor.
  Empirik: `wpgate` ve `modfix` **ikisi de fabrikaya düştü** (brief §3 B/C). Config patch'leri
  düşmedi.

**Page↔RAM haritası (chunk0→0x00000000 0xC000, chunk1→0x040C0000 0x30000):** Func0 sayfa 122/123'ün
ilk 16 KB'i = canlı RAM `0x00000000`/`0x02000000` (birebir: `kanit/loader_orijinal/src_p122_m2.bin
== re/fw_canli/e10`, 16384/16384; p123==e11). Yani config sayfaları düşük-RAM'e map oluyor ve
`0x398`=Func0 orada. Kod sayfaları (113/119…) e07/e04 kod bölgelerine map oluyor.

**Pratik çıkarım:** Gelecekte kod-patch gerekiyorsa güvenli değil — ROM'un LDPC-korumalı okuma modu
ve magic memcmp'i, değişen kod sayfasını ya reddediyor ya fault'luyor. Bu, **WP'yi kod düzeyinde
(0x040D67F0 mode-yazıcı, 0x040EC0A4 gate) yamalamayı ölü yol** yapıyor; doğru hedef zaten config'ti,
ama config-lever de (§3) NVMe-ready ile uyumsuz. İkisi de çıkmaz → §6/§Soru 5.

---

## 7. SORU 5 — nihai öneri (Alperen'in ayrı oturumda yürüteceği sıralı plan)

Öncelik: **NVMe-ready + yazılabilir + kalıcı.** Analiz, config-lever'ın bu üçlüyü tek başına
veremeyeceğini gösteriyor — **tek çürütülmemiş umut**, `wpfix` ASC=44'ünün ölçüm artefaktı (M2)
olması. O yüzden plan bununla başlıyor.

### Adım 0 — diski servis eden bir config'e geri getir (güvenlik tabanı)
Şu an c0ce0'da `wpfix` var (servis etmiyor). Önce **`loader_v4_15die`** yaz (kanıtlı servis eden,
WP açık, 960 GB, die-b veriden çıkık):
```
sudo env JDKAYNAK=/home/schrodinger/jd1024/kanit/loader_v4_15die python3 port/ldr_yaz.py --yaz
```
Telsiz replug → `kopru/jms_durum.py` ile doğrula: NSZE≈1875385008, mode=3, ReadRam OK. (Beklenen:
servis ediyor.) Bu, disk en azından çalışan bir **read-only 960 GB** disk.

### Adım 1 — ★ EN DEĞERLİ: `wpfix`'i UZUN beklemeyle yeniden dene (M1↔M2 ayrımı)
`wpfix` zaten `kanit/loader_v4_wpfix`'te hazır.
1. `sudo env JDKAYNAK=.../kanit/loader_v4_wpfix python3 port/ldr_yaz.py --yaz` → verify 0 hata.
2. Tel çıkar, **gerçek power-cycle** (`~/bin/jd-cevrim`).
3. Telsiz ürün modu; **köprüyü hemen yoklama.** `sg_readcap`/Identify'ı **döngüde, 5-10 dakika**
   boyunca ~15 sn arayla dene. Mümkünse BAR0'dan CSTS.RDY'yi izle (§9.2 yolu): RDY 0→1 geçişi
   arıyoruz.
   - **RDY=1 gelir + Identify/readcap servis ederse → M2 doğru: `wpfix` ÇALIŞIYOR.** Host-write
     testi (vendor tünel NVMe I/O write op 0x01, LBA 40M+, admin=False) yap; geri oku. **Yazılabilir
     disk = hedef elde.** Bitti.
   - **5-10 dk sonra hâlâ ASC=44 / RDY hiç gelmezse → M1 doğru:** WP-abort yük-taşıyan. Config-lever
     ölü. Adım 0'a dön (15-die servise geri al) ve Adım 2'ye geç.

Ölçüm hedefleri (Adım 1): CSTS.RDY, NSZE, Identify sonucu, ilk başarılı host-write'ın geri-okuması.
Geri dönüş: Adım 0 (15-die) her an yazılabilir.

### Adım 2 — M1 doğruysa: tek kalıcı yol MP-eşdeğeri (die-b fiziksel dışlama)
Config-lever kapandığında geriye §26'nın vardığı yer kalıyor, ama artık gerekçeli: die-b'nin
**sistem/boot bloklarını sağlam die'lara taşı + die-b'yi fiziksel bad-block**. İki alt-yol, ikisi de
gerçek maliyet:
- **2a. MP tool + SKV6 SYS firmware:** JMS583 köprü tüneli çalışıyor (§32), ama SKV6 SYS paketi
  edinilemiyor (B2: admin-kilit, aynasız, parayla yok). Kapalı kalırsa 2a düşer.
- **2b. GDP tüneliyle MP replikasyonu:** kendi tünelimizle bad-block tablosu + sistem-blok
  relocation. Bloke eden **adresleme duvarı** (blok>1024 erişilemiyor, §35.6) çözülmeli — bu, komut
  0x89 handler'ında rf→row maskesi (c1.bin) veya GDP.bin'de hardcoded. Uzun RE işi.

Bu adımda **`wpfix16` yazma** — öngörü onu ASC=44 (M1) sayıyor ve die-b'yi hırpalıyor; kazanç yok.

### Adım 3 — hiçbiri açılmıyorsa dürüst karar (Alperen'de)
- **Park:** 15-die, read-only ~960 GB arşiv diski olarak kalsın (Adım 0 durumu). Onarım için
  adresleme-duvarı RE'si (2b) veya SKV6 paketi (2a) bekleyen bloklar.
- Bu bir "para+yön" kararı → dur-sor.

---

## 8. Olasılık matrisi (özet)

| Yol | Yazılabilir? | NVMe-ready? | Kalıcı? | Neden (disasm/ölçüm) |
|---|---|---|---|---|
| Fabrika 16-die (mevcut fallback) | Hayır (WP açık) | Evet | Evet | assert→mode 4; 30 kapı kapalı |
| 15-die (WP açık) | Hayır (WP açık) | **Evet** (kanıtlı §35.4) | Evet | die-b veriden çıkık ama sistem-blok fiziksel; WP yine türer, abort boot'u bitirir |
| `wpfix` = 15-die + WP-off | **? (M2 ise evet)** | **? (M1 ise hayır)** | Evet | ASC=44 ölçüldü; M1=kaçış-kapısı yok / M2=boot yavaş — **Adım 1 ayıracak** |
| `wpfix16` = 16-die + WP-off | Öngörü hayır | Öngörü hayır (ASC=44) | — | WP-off + die-b var; geometri sebep değil; die-b'yi hırpalar |
| Kod-patch (wpgate/modfix) | — | **Hayır (boot bozuldu)** | — | ROM LDPC/magic kapısı değişen kod sayfasını reddediyor |
| QBT assert temizleme (3e) | Kısmen | Evet | **Hayır** | die-b yeniden yazıp assert'i canlı besliyor; adresleme duvarı |
| **MP-eşdeğeri: sistem relocation + die-b bad-block (3f/2)** | **Evet** | **Evet** | **Evet** | die-b'ye fiziksel yazma hiç olmaz → assert hiç türemez; **tek tam çözüm**, ama SKV6 paketi (2a) / adresleme duvarı (2b) blokajı |

---

## 9. Doğrulamadıklarım / iddia etmediklerim (dürüstlük)

- **M1 vs M2 kesin ayrılmadı.** `wpfix` ASC=44'ünün mekanizması (kaçış-kapısı mı, yavaş-boot mu)
  canlı test gerektiriyor (Adım 1). M1'i disasm+ölçüm **güçlü** destekliyor (tek config-biti,
  serves→ASC=44), ama M2'yi §9.2'nin uzun-RDY gözlemi ayakta tutuyor.
- **"Boot yakınsamaz" (M1) bir çıkarım.** WP-off'ta firmware'in tam takılma noktasını (sonsuz
  retry mi, fault mı, RDY-hang mı) canlı izlemedim; ASC=44 + WP-abort'un kaldırılması + boot-anı
  die-b yazma-fail'inden çıkardım.
- **Boot-variant [WP-BT]/[PBT] seçim sırası ile QBT re-latch sırasının** tam etkileşimini (mode
  seçim anında 0 mı 3 mü) kesin çözmedim; ama ampirik `[WP-BT]=0, [PBT]=4` sonucu değiştirmiyor.
- **`wpfix16` test edilmedi** — öngörü, ölçüm değil.
- Cihaza hiçbir komut gönderilmedi; tüm değerler diskteki dump/asm/notlardan (`re/urun_jms/`,
  `re/fw_canli/e*.bin`, `kanit/loader_v4*`, UART log) okundu.

## 10. Kullanılan başlıca adresler/dosyalar
Func0 `*(0x398)` bit3 (WP) · mode `*(0x00810CE8)` · assert sayaç `*(0x040EEE58)` (art. e04
`0x0200924C`) · assert konum `*(0x040EEE5C)=0x03190712` (yaz. e04 `0x020031F4`, L2P fn `0x0200318C`)
· mode=3 e07 `0x040D67F2` · mode=4 e04 `0x02006718` · WP kapıları e07 `0x040D6CC6`,`0x040EC0A4` ·
boot-variant seçimi e04 `0x02000928` (WP-BT `0x04065825` / PBT `0x04065B85`) · ROM presence probe
`0xFFFF1860`→`0x04030052` · LDBK magic kapısı `0xFFFF0D88`/`0xFFFF0EEC`.
Config alanları (canlı `re/urun_jms/00000000.bin`): 0x388 LBA · 0x398 Func0 · 0x3E0/0x4C6 die-count ·
0x400 Die_2_CeCh · 0x440 CeCh_2_Die · 0x31C die-presence.
Dosyalar: `kanit/loader_v4{,_15die,_wpfix,_wpfix16}` · `re/urun_jms/*.bin` · `re/fw_canli/e*.bin` ·
`kanit/mxutility_dump/*UARTLogInfo.txt` · `re/ANALIZ_{WP_BIT,YAZMA_KAPISI,UART_LOG,DIEREMAP,BOOTDIE_SECIM}.md`.
