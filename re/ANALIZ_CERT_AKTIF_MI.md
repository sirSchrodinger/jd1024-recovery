# JD1024 (MAXIO MAP1202) — ROM cert kapısı AÇIK mı? (statik analiz)

Tarih: 2026-09-20 · **%100 offline statik analiz** — cihaza hiçbir komut gönderilmedi.
Kaynak: `re/maskrom_FFFF0000.bin` (64 KB mask ROM, taban `0xFFFF0000`, ARM+Thumb-2),
`kanit/c3ce2_blok0_tam.bin` (360 sayfa × 16384 = boot EDEN fabrika loader bloğu, blok 0).
Araç: capstone 5.0.7 (`.cctmp/rd.py` disassembler), python3.
Her iddiada adres+disasm veya dosya-ofseti+hex. Kanıtlanamayan yerler **ZAYIF** işaretli.

---

## HÜKÜM (en başta)

```
Cert kapısı bu cihazın OTONOM BOOT'unda KAPALI. İKİ bağımsız kanıt:
 (A) EMPİRİK: cert sayfası = mantıksal sayfa 1 = fiziksel sayfa 1 (page-map identity).
     c3ce2 blok-0'ın page 1'i TAMAMEN BOŞ (0x00). Dump'ta "LOADER_CERT_TAG1" 0 kez.
     Cert AÇIK olsaydı memcmp(page1,"LOADER_CERT_TAG1") başarısız -> c3ce2 REDDEDİLİRDİ.
     Ama c3ce2 boot ediyor. => ctx[0x470] != 1 (kanıtlanmış).
 (B) MEKANİZMA: ctx[0x470]'i yazan TEK kod bit-4 çıkarımı (0xFFFF2004), o da yalnız
     vendor/download config-parser'ında (giriş 0xFFFF1EC8/1E16, çağıran 0xFFFF226E/2342/2464).
     Otonom boot (reset->0xFFFF0140 mode-dispatch->bring-up 0xFFFF1A48->scan 0xFFFF1300)
     bu parser'ı ASLA çağırmıyor. Boot'ta ctx[0x470] hiç yazılmıyor, ZI-init değerinde kalır.
=> Yamalı loader'ları reddeden şey CERT DEĞİL. Gerçek kapı: NAND LDPC ECC (okuma-fail).
```

Bu, `ANALIZ_BOOTDIE_SECIM §5` ve `reference_jd1024_rom_cert_duvari` ("ROM kripto imza
duvarı, yamalı loader ASLA boot edemez") iddiasını **ÇÜRÜTÜR**: kripto motoru (`0xFFFF5308`)
var ve cert *etkinleştirilebilir*, ama bu cihazın boot'unda **etkin değil**.

---

## C1 — Cert buffer'ı nereden geliyor? (sayfa 1, dump'ın İÇİNDE)

**Çağrı zinciri:** scan `0xFFFF1300` → gate `0xFFFF1378 bl 0xFFFF0E62` → `0xFFFF0ECE bl 0xFFFF24CE`.

`0xFFFF24CE` (cert verify), arg2 (`r2`) = kontrol edilecek buffer:
```
FFFF24DA  mov  r4, r2                 ; r4 = arg2 = buffer
FFFF24E4  ldr  r1,[pc]=0xFFFFF3C0     ; "LOADER_CERT_TAG1"
FFFF24E8  mov  r0, r4
FFFF24EA  bl   0xFFFFD2B4             ; memcmp(buffer, "LOADER_CERT_TAG1", 0x10)
FFFF24EE  cbnz r0, 0xFFFF2558         ; TAG yoksa -> return 0 (cert FAIL)
```
Çağıran `0xFFFF0E62`, arg2 = **`0x040029C0`** (sabit RAM buffer):
```
FFFF0E72  ldrh r3,[r1,#0x192]         ; r1=descriptor(0x040304EC); page = desc[0x192]
FFFF0E7A  bl   0xFFFF07F8             ; NAND page-read (die, blk, page=desc[0x192], arg5=1)
FFFF0ECA  ldr  r2,[pc]=0x040029C0     ; cert buffer
FFFF0ECE  bl   0xFFFF24CE             ; verify(ctx, ctx, buf=0x040029C0)
```
Buffer seçimi (`0xFFFF07F8` arg5): BLOCKS=0, CERT=1, LDPC=2 → buffer = `0x040019C0 + arg5*0x1000`
= {`0x040019C0`,`0x040029C0`,`0x040039C0`}. (arg5: `0xFFFF0D9C str r5=0`, `0xFFFF0E6E str r5=1`,
`0xFFFF0F04 str r5=2`.)

**Cert sayfa numarası — dökümden hesaplandı:**
- `desc[0x190..0x48F]` = `page0[desc[0x84] .. +0x300]` (kopya `0xFFFF0E14`, `memcpy 0xFFFFD438`).
- `desc[0x84]` = LE word `page0[0x214]` = **0x320** (hex `page0[0x210..0x21F]=200200002003000020060000300a0000`).
- Yani `desc[0x190]` = `page0[0x320]` bir **page-map dizisi**: hex `page0[0x320..]=00000100 02000300 0400...`
  = halfword `[0,1,2,3,4,...]` (identity; 0x180 elemanda 0 non-identity).
- `desc[0x192]` = page-map[1] = **1**.

**⇒ Cert sayfası = (die, blk, fiziksel sayfa 1).** c3ce2 blok-0 için = dump'taki page 1
(`kanit/c3ce2_blok0_tam.bin` offset `0x4000`). **Dump'ın İÇİNDE (0-359).**

**Page 1 içeriği (dökümden):** `page1[0:0x40]` neredeyse tamamen `00`; `LOADER_CERT_TAG1`/`CERT`/`TAG`
**yok**. Tüm 360 sayfada `LOADER_CERT_TAG1` = 0 kez, `CERT` = 0 kez.

**⇒ Cert AÇIK olsaydı bu boş sayfa TAG-memcmp'ini geçemez, c3ce2 cert-FAIL alır, boot edemezdi.
Ediyor. Tag'in yokluğu KESİN kanıt: cert kapısı bu boot'ta işletilmedi.**

---

## C2 — `ctx[0x470]` nereden set ediliyor? (yalnız download; boot'ta yazılmıyor)

`ctx = 0x04030058`, `ctx[0x470] = 0x040304C8`. Gate: `0xFFFF1366 ldr r0=0x04030058; 0xFFFF1368
ldrb r0,[r0,#0x470]; 0xFFFF136C cmp #1; 0xFFFF136E bne` → cert yalnız `ctx[0x470]==1` iken çağrılır.

**Tüm ROM'da `strb/str [reg,#0x470]` YOK.** (Bütün ROM taraması: 0x466-0x46e, 0x474, 0x477, 0x480
offset'lerine store var; **0x470'e HİÇ store yok**; her `#0x470` erişimi `ldrb` = okuma. Literal
havuzunda `0x040304C8` de yok.) → `ctx[0x470]` yalnız bir yerde yazılır:

```
FFFF1FEA  ldr  r0,[sp,#0x11c]         ; r0 = deserialize edilmiş config dword
FFFF1FEC  addw r4,r4,#0x46f           ; r4 = ctx+0x46f
FFFF2000  ubfx r2,r0,#4,#1            ; r2 = config dword'un BIT 4'ü
FFFF2004  strb r2,[r4,#1]             ; ctx[0x470] = bit4   << TEK yazıcı
```
Yani `ctx[0x470]` **basit bir memcpy alanı DEĞİL** (görev hipotezi burada yanlış); bir config
dword'un **bit 4'ü**. `sp[0x11c]` = config bit-stream'inden HW-destekli extractor `0xFFFF C7C4`
(ARM; spec index'i HW reg'e yazıp okuyan bitstream okuyucu) ile üretiliyor; kaynak pointer =
`ctx[0x484]`.

**Bu parser otonom boot'ta ÇALIŞMIYOR:** giriş noktaları `0xFFFF1EC8` (`addw r6,r0,#0x484;
ldr r2,[r0,#0x484]`) ve `0xFFFF1E16`. Tüm `bl` çağıranları: **`0xFFFF226E`, `0xFFFF2342`,
`0xFFFF2464`** — hepsi `0xFFFF22xx-24xx` vendor/download komut bloğunda (aynı küme cert-verify
`0xFFFF24CE`'yi ve download giriş `0xFFFF2596`'yı içeriyor). Boot scan `0xFFFF1300` ve bring-up
`0xFFFF1A48` bu parser'ı çağırmıyor.

**Otonom boot mode-dispatch (boot-main, ARM):**
```
FFFF0150  ldrb r0,[0x04030478]        ; boot strap
FFFF0154  cmp #5 / FFFF015C cmp #7
FFFF0198  ldr r0=0x66994EE4; FFFF019C blx 0xFFFF2596   ; strap==7 -> DOWNLOAD (parser buradan)
```
Normal boot (strap!=7) download yoluna girmez → parser çalışmaz → `ctx[0x470]` yazılmaz →
scatter-loader (`0xFFFF0044`, ZI-clear `0xFFFF0094`) ile sıfırlanan değerinde (0) kalır.

**⇒ Kaynak "page 0 baytı ve değeri" sorusunun cevabı:** Otonom boot'ta `ctx[0x470]`'i besleyen
bir page-0 baytı YOK; değer ZI-init = **0**. (Download modunda config dword bit4 olur; bit4'ün
kesin değerini HW-destekli deserializer nedeniyle statik çıkaramadım — **ZAYIF** — ama fabrika
config'inin cert'i kapalı tuttuğu, page-1 cert-slot'unun BOŞ olmasıyla kanıtlı.) Her iki yolda da
`ctx[0x470] != 1`.

---

## C3 — Yamalı loader'lar gerçekte neden reddedildi? (LDPC ECC, cert değil, checksum değil)

Cert kapalı olduğu için ret başka kapıdan. Kod kanıtı:

**(b) Kriptografik checksum/CRC kapısı YOK.** Seçim (`0xFFFF0D88` magic, `0xFFFF0EEC` LDPC-magic)
sadece memcmp yapıyor. Yükleme (`0xFFFF0FD0`) CodeMap segment-tag'leri (`0xa1/0xa3`, memcmp
`0xFFFFD2B4`) + kopya/decompress (`0xFFFF6A40/6D4C`) kullanıyor; loader üzerinde toplam/CRC
hesaplayıp saklı değerle karşılaştıran kod **bulunamadı**. → (b) kapı değil.

**(c) LDPC ECC = gerçek kapı (KANITLI).** Okuma sonuç yolu `0xFFFF1528`:
```
FFFF1554  ldrb r0,[r4,#3]; FFFF1556 ubfx r1,r0,#1,#2   ; 2-bit ECC-seviye alanı
FFFF1566  ldrh r0,[r4,#4]; FFFF1568 lsls r0,#0x1d
FFFF156A  bmi  0xFFFF1546  -> return 0 (FAIL)           ; ECC-uncorrectable biti -> okuma FAIL
```
Loader bloğu LDPC decode (`page2 "LDBK LDPC TABLE1"`) + encode (`page4 "LDBK LDPC TABLE2"`)
matrisleri taşıyor; ROM her sayfayı controller LDPC'sinden geçirerek okuyor. Ham NAND'a
parity yeniden hesaplanmadan yazılan yama:
  - küçükse → LDPC düzeltir, okuma **orijinal baytı** döndürür (yama sessizce geri alınır;
    `feedback_enjekte_kod_icache_bayat` tarzı sessiz arıza),
  - parity'i bozacak/büyükse → **uncorrectable → okuma FAIL** → o sayfa seçim-okuması ise die
    atlanır (`0xFFFF1364 cbnz`), kod sayfası ise yükleme çöker.

**(a) LDPC-magic kapısı (`0xFFFF0EEC`)** yalnız LDPC sayfası (page 2) yamalanırsa tetiklenir;
kod yamasıyla ilgisiz.

**⇒ C3 cevabı:** Ret mekanizması **LDPC/ECC (c)** — cert değil, checksum değil. Görevin C3(c)
öngörüsü doğru. Yama yazarken sayfanın LDPC codeword'ü **yeniden encode edilmeli** ki decoder
yamalı baytı üretsin. Kesin mod (ldpc-index / scramble `scr`) ROM'da değil MPTool yazma yolunda
(`ANALIZ_LDBK_YAZMA.md`); block encode matrisi "LDBK LDPC TABLE2"/"LDPC0 TABLE2" — kesin
`ldpc=?/scr=?` **ZAYIF**, yazma-yolu analizinden doğrulanmalı.

---

## C4 — `Func0` (loader ofset `0x398`) bütünlük kontrolünde mi? (HAYIR — sadece ECC)

`page122[0x398]` = **0x0A** (dökümde doğrulandı; `page122[0x390..0x3A0]=24f40000000000000af8010000000000`,
bit3=EnWriteProtectAbort). 5 kopya **birebir aynı**: page 122==167==212==257==302 (hepsi eşit).
Page 122 başı `18f09fe5`× = ARM vektör tablosu (loader image başı).

**Bütünlük durumu:**
- Cert: KAPALI (C1/C2).
- Seçim magic kapıları page 0, cert-page(1), LDPC-page(2)'yi okur — **page 122'yi OKUMAZ**. Kod
  sayfası yalnız yükleme (`0xFFFF0FD0` → `0xFFFF0886`) sırasında, seçimden SONRA okunur.
- Kriptografik checksum/imza YOK (C3-b).

**⇒ `page122[0x398]` baytı ROM'un hiçbir kripto/checksum kapısında değil; tek koruması NAND LDPC
ECC.** Bayt serbestçe değiştirilebilir — **koşul: o sayfanın LDPC parity'si yeniden hesaplanmalı**
(yoksa ECC düzeltip 0x0A'ya geri döndürür ve yama etkisiz kalır). Kripto duvarı yok = kurtarma
için iyi haber.

---

## C5 — Loader bloğunun tam haritası (360 sayfa dökümü + 1176 sayfa çıkarımı)

Sayfa = 16384 B. Blok = 1536 sayfa (Flash.ini `PageNum 1536`); 360 döküldü.

| sayfa | içerik | rol |
|---|---|---|
| 0 | `LDBK BLOCKS V00` (+`LDBK CONFIG V00`@0x200) | blok başlık + config (page-map@0x320, geometri) |
| **1** | **BOŞ (0x00)** | **cert-page slot — cert YOK** (desc[0x192]=1 buraya işaret eder) |
| 2 | `LDBK LDPC TABLE1` | LDPC **decode** matrisi (desc[0x40]=2 → page-map[2]) |
| 3 | binary | LDPC decode verisi |
| 4 | `LDBK LDPC TABLE2` | LDPC **encode** matrisi |
| 5 / 7 | `LDPC0 TABLE1` / `TABLE2` | ikinci LDPC profil (kanal-0) |
| 6 | binary | LDPC verisi |
| 8 | `LDBK FWSLOT MARK` | firmware-slot işaret başlığı |
| 9-12,17-20 | `...UMAS09A0V000` | FW-slot işaretleri (arada 13-16,21-24,29-32 = boş) |
| 33-40 | `MAS090X_PAR_V000` | parametre bloğu |
| 42-55 | binary | veri |
| 56-67, 73-90 | `ZZZZ...` | rezerve/dolgu |
| 68 | `LDBK NANDMEM TAB` | NAND-mem tablosu |
| 91 | `LDBK FWTMC MARK` | FWTMC (TMC) işaret başlığı |
| 92-98 | binary | TMC/veri |
| **99-143** | **loader KOD slot #0** (99=`DFSR[%x]IFSR[%x]..` debug str, 122=ARM vektör) | boot loader image |
| 144-188 | KOD slot #1 | slot #0 ile **byte-aynı** (sha1 758fe1e1..) |
| 189-233 | KOD slot #2 | aynı |
| 234-278 | KOD slot #3 | aynı |
| 279-323 | KOD slot #4 | ~aynı (dump 359'da kesiliyor) |
| 324-359 | binary | 6. slot başı (kısmi) |

**Slot yapısı (kesin):** kod slot periyodu = **45 sayfa** (`DFSR` işareti sayfa 99,144,189,234,279;
Δ=45). Func0 baytı slot-offset 23'te (page 99+23=122, +45×k → 167,212,257,302). İlk 4 kod slot'u
**birebir aynı** → saf redundancy. Yani metadata (page 0-98) + 45-sayfalık kod slot'unun N kopyası.

**Kalan 1176 sayfa (360-1535) çıkarımı:** ROM her die için 16 yedek blok tarıyor
(`table@0xFFFFF35C={0,4,1,8,...}`) ve slot-kopya deseni 45-periyotlu. Blok içinde 45-sayfalık kod
slot'u page 99'dan itibaren tekrarlanıyor; (1535-99)/45 ≈ 31 → blokta **~30+ redundant kod slot
kopyası** olması beklenir (çoğu boş-erased de olabilir). ROM seçim için yalnız page 0 (magic/config),
page 1 (cert; kapalı) ve LDPC page'i okur; kod page-map (identity) üzerinden yüklenir. **ZAYIF:**
360 ötesi doğrudan görülmedi; bu çıkarım ROM tarama koduna + gözlenen 45-periyotlu redundancy'ye
dayanıyor.

---

## Adres haritası (bu analiz)

| ne | adres |
|---|---|
| cert gate (ctx[0x470]==1?) | `0xFFFF1366-136E` (ctx `0x04030058`, byte `0x040304C8`) |
| cert wrapper (page-read + verify) | `0xFFFF0E62` (page=desc[0x192], buf=`0x040029C0`) |
| cert verify (memcmp TAG + HW crypto) | `0xFFFF24CE` → `0xFFFF5308` (`0x06700480/84/88`) |
| "LOADER_CERT_TAG1" string | `0xFFFFF3C0` (dump'ta 0 kez) |
| ctx[0x470] TEK yazıcı (bit4) | `0xFFFF2004` (parser `0xFFFF1EC8/1E16`) |
| parser çağıranları (download) | `0xFFFF226E, 0xFFFF2342, 0xFFFF2464` |
| download giriş | `0xFFFF2596` (strap==7 @ `0xFFFF0198`) |
| okuma ECC-fail kapısı | `0xFFFF156A bmi -> 0xFFFF1546` (completion[+4] bit2) |
| descriptor / page-map | `0x040304EC` / `desc[0x190]` = identity |
| config-copy (page0→desc) | `0xFFFF0DE8..0E46` (`memcpy 0xFFFFD438`) |
| loader kod yükle | `0xFFFF0FD0` (CodeMap; checksum YOK) |
| page-read primitive | `0xFFFF07F8` (arg5 → buffer `0x040019C0+arg5*0x1000`) |

## Bulamadıklarım / ZAYIF
- Download config dword bit4'ün kesin sayısal değeri — HW-destekli deserializer (`0xFFFF C7C4`)
  statik çözülemedi; page-1 boşluğu cert-kapalıyı dolaylı kanıtlıyor.
- LDPC yeniden-encode kesin modu (`ldpc/scr` index) — ROM'da değil, MPTool yazma yolunda.
- 360-1535 sayfaları doğrudan görülmedi (blok tam dökülmedi); slot çıkarımı tarama koduna dayalı.
- ctx SRAM ZI-init'inin 0x040304C8'i kapsadığı bölge-tablosundan tek tek doğrulanmadı; ama
  ctx[0x470]'in boot'ta hiç yazılmadığı ve !=1 olduğu bağımsızca kanıtlı.

---

## TEK CÜMLELİK HÜKÜM
**Cert kapısı bu cihazda KAPALI, çünkü cert sayfası fiziksel page 1'e (dump içinde, tamamen boş)
işaret ediyor ve c3ce2 buna rağmen boot ediyor — dolayısıyla `ctx[0x470] != 1` (kanıtlı) ve
`ctx[0x470]`'i 1 yapan tek kod yalnız vendor/download modunda çalışıyor; yamalı loader'ları reddeden
gerçek mekanizma cert değil NAND LDPC ECC'dir.**
