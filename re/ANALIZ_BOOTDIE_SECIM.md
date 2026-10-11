# JD1024 (MAXIO MAP1202) — ROM boot die tarama + loader seçim mekanizması

Tarih: 2026-09-20 · **%100 statik analiz** — diske/kaplikaya'ya hiçbir komut gönderilmedi.
Kaynak: `re/maskrom_FFFF0000.bin` (64 KB mask ROM, RAM tabanı `0xFFFF0000`). Her iddiaya dosya+offset+disasm.
Araçlar: `re/rom/rd2.py`, scratchpad `xall.py`/`litref.py`/`cg.py` (ADR/literal/callgraph tarayıcı).

Bu dosya, `ANALIZ_BOOT_RECOVER.md`'nin "boot kopya-seçimi mask ROM'da, imajda görülemez" boşluğunu
**doldurur** — tarama döngüsünü, magic kontrolünü ve die seçim kriterini ROM içinde bulur.

---

## KARAR (5 satır)

```
1. ROM die TARIYOR ve magic'i olmayan die'ı ATLIYOR — kanıtlı (0xFFFF1300 döngüsü, 0xFFFF1364 skip-branch).
2. Her die 3 kapıdan geçmeli: LDBK BLOCKS/CONFIG magic (memcmp) + CERT imza (HW crypto, ctx[0x470] geçitli) + LDBK LDPC magic.
3. Seçim = (blok-sırası × die-sırası) ilk TÜM-kapıları-geçen die. Blok tablosu ROM-sabit {0,4,1,8,2,...}.
4. c3ce2'nin seçilmesi = ondan ÖNCE taranan yamalı die'ların REDDEDİLDİĞİNİ kanıtlar (imza kapısı).
5. ÖNGÖRÜ: c3ce2 silmek boot'u 15 yamalı die'a DÜŞÜRMEZ. Yamalılar imza-red; c3ce2 gidince @ALL NOFC = boot ölür.
   (Ayrıca blok-0-tek silme muhtemelen ETKİSİZ: ROM 16 yedek bloğu tarıyor, c3ce2 başka blokta hâlâ geçerli.)
```

---

## 1. Boot zinciri: reset → loader load

Reset vektörü `0xFFFF0020` = `0xFFFF0324` (reset handler, ARM) → MPU/stack init → `blx 0xFFFF0044`
(Thumb scatter-load) → **boot-main (ARM, ~`0xFFFF00C0`)**.

Boot-main literal pool'u `0xFFFF02C4..0xFFFF0320`'de (string'ler `@EFFL/@NoSI/@NoFlash/@Boot LDR/LK:%x`
inline gömülü). Kanıt: `litref.py 0xFFFF02C4 0xFFFF0320` → 16 `ldr rX,[pc,#..]` hepsi bu pool'a.

Kritik çağrı dizisi (boot-main, ARM):
```
ffff01d8  ldr  r1,[pc,#0x110]   ; r1 = 0x04030052   (die-presence bitmap, 4 bayt)
ffff01dc  add  r0,r1,#6         ; r0 = 0x04030058   (boot context tabanı)
ffff01e0  blx  #0xffff1a48      ; << NAND engine bring-up + DIE PROBE, r0=sonuç
ffff01e4  cmp  r0,#0
ffff01e8  mov  r8,#1
ffff01ec  beq  #0xffff01f8       ; r0==0 -> "@NoFlash", status|=0x20
ffff01f0  blx  #0xffff1300      ; << r0!=0: LOADER LOAD + DIE SCAN  (asıl seçim BURADA)
...
ffff0214  add  r0,pc,#0xe4      ; -> 0xFFFF0300 "@Boot LDR" (banner, boot yolu doğrulaması)
ffff0218  blx  #0xffff613c      ; printf
```
- `0xFFFF1A48` = NAND motor bring-up (BULGULAR C2) + `0xFFFF1860` die-probe. **Hangi die'ların fiziksel
  yanıt verdiğini** (READ status == `0xE0`) bulur, `0x04030052` presence-bitmap'ini doldurur.
- `0xFFFF1300` = **loader okuma + die tarama + seçim + RAM'e yükleme**. Asıl cevap burada.

---

## 2. ★ DIE TARAMA DÖNGÜSÜ — `0xFFFF1300` (üç iç-içe döngü)

```
ffff1300  push {...}
ffff1304  movs r0,#0 ; mov r8,r0            ; r8 = 0
ffff130c  bl  #0xffff12d0                    ; r0 = CE0/CE1'de mevcut die sayısı
ffff1310  strb r0,[sp,#4]
ffff1314  cbnz r0,#0xffff131a               ; CE0/1'de die VARSA -> r8 kalır 0
ffff1316  mov.w r8,#2                        ; CE0/1 BOŞSA -> r8 = 2
ffff131a  ldr  fp,[pc]=04030052             ; fp = presence bitmap
ffff1320  OUTER r6 = 0..15:                  ; (0xffff13a6 cmp r6,#0x10)
            r0 = [0x46b]==1 ? 0x04030000(RAM ctx) : 0xFFFFF35C(ROM tablo)
ffff133a    ldr r0,[base, r6, lsl#2]         ; blk = table[r6]   (blok numarası)
ffff133e    str r0,[sp]
ffff1334    sl = r8+2 ; r5 = r8
ffff1342    MIDDLE r5 = r8 .. r8+1:          ; (0xffff139e cmp r5,sl)  r5 = CE
ffff1346      sb = 1<<r5
ffff134a      INNER r4 = 0..3:               ; (0xffff1396 cmp r4,#4)  r4 = CH (kanal)
                r0 = *(0x04030052 + r4)       ; kanal r4'ün CE-bitmap'i
ffff134e        tst r0, (1<<r5)
ffff1352        beq 0xffff1392               ; die (r4,r5) yoksa -> sıradaki
ffff1354        r7 = r4 | (r5<<2)            ; << DIE INDEX = CH | (CE<<2)
ffff1360        bl 0xffff0d88(ctx,0x040304ec,die=r7,blk)   ; OKU + magic kontrol
ffff1364        cbnz r0, 0xffff138c          ; r0!=0 (magic/oku HATA) -> ATLA, sıradaki die
ffff1368        ldrb r0,[ctx+0x470] ; cmp #1 ; bne 0xffff137e
ffff1378        bl 0xffff0e62(...)           ; ctx[0x470]==1 ise: CERT imza kontrol
ffff137c        cbnz r0, 0xffff138c          ; cert HATA -> ATLA
ffff137e        bl 0xffff0eec(...)           ; LDBK LDPC TABLE magic kontrol
ffff138a        cbz r0, 0xffff13b2           ; HEPSİ GEÇTİ -> 0xFFFF13B2 (YÜKLE, seçildi)
ffff138c   :FAIL  ldr r0=0x04030051 ; movs r1,#0x40 ; strb r1,[r0]   ; status |= 0x40
ffff1392   :NEXT  r4++ (sonraki kanal/die)
...
ffff13a2  r6++ (sonraki blok)
ffff13aa  cmp r8,#0 ; beq 0xffff13e8 (r8==0) / else 0xffff1446   ; hiçbir die geçmediyse
```

### 2.1 Tarama sırası (kesin)
- **Dış: blok** — `table[16]` @ `0xFFFFF35C` (ROM) = `{0,4,1,8,2,0x20,0x10,6,0xc,3,0x18,0x30,0x40,0x60,0x80,0xc0}`.
  (RAM ctx `0x04030000` varyantı ctx[0x46b]==1 iken.) Bunlar **yedek loader blok numaraları**. Blok 0 önce.
- **Orta: CE** (`r5`), aralık `[r8, r8+2)` — yani 2 CE değeri.
- **İç: kanal CH** (`r4`), 0..3.
- **die = CH | (CE<<2)** — `orr.w r7,r4,r5,lsl#2` @ `0xFFFF1354`. `ANALIZ_BOOT_RECOVER §3.2`'deki
  firmware konvansiyonuyla (die = CH|(CE<<2)) **birebir aynı**.
- Presence geçidi: `*(0x04030052 + CH)` baytının `bit CE`'si set değilse die atlanır (`0xFFFF134E tst`).

### 2.2 `r8` (CE-yarısı seçici) — `0xFFFF12D0`
```
ffff12d0: r0=0 girişle; r5=0x04030052; for CE=0..1: for CH=0..3: if bitmap[CH]&(1<<CE): cnt++
          return cnt
```
- CE0/CE1'de mevcut die varsa → `r8=0` → tarama **CE0,1** (die 0-7).
- CE0/CE1 boşsa → `r8=2` → tarama **CE2,3** (die 8-15).
- **Sonuç: ROM her boot'ta yalnız BİR CE-yarısını (8 die) aday görür**, 16 blok × 2 CE × 4 CH.
- c3ce2 = CH3,CE2 = die `3|(2<<2)=11` (CE2). **Seçilmesi için `r8=2`** (CE0/1 taranmıyor/boş) gerekir; o
  hâlde c3ce2, CE2 içinde CH sırasıyla **4.** die'dır: c0ce2(8), c1ce2(9), c2ce2(10), **c3ce2(11)**.

> ⚠️ `r8` presence-bitmap'e bağlı; bitmap değeri canlı dump'ta yok (`0x04030052` bölgesi
> `fw_canli/e*.bin`'de dökülmedi). "c3ce2 boot ediyor" gerçeği r8=2'yi ima eder. CE/CH ekseninin
> ters olma ihtimali sonucu değiştirmez (aşağıdaki red-mantığı sıra-bağımsız).

---

## 3. ★ MAGIC / İMZA KONTROLÜ — bir die'ı ne "geçerli" yapar

### 3.1 `0xFFFF0D88` — LDBK BLOCKS + CONFIG magic (birincil kapı)
```
ffff0d88  push {...}                          ; r0=ctx r1=0x040304ec r2=die r3=blk
ffff0d9e  bl  #0xffff07f8                      ; (die,blk,page0) OKU -> r0; ==1 başarı
ffff0da2  cmp r0,#1 ; beq 0xffff0dc8            ; oku OK -> magic'e geç
ffff0da6  ...0x0660022c=0x20200323;=0 ; bl 0xffff07f8 (2. deneme) ; cmp #1 beq 0xffff0dc8
ffff0dc2  movs r0,#2 ; ret                      ; 2 kez oku başarısız -> dön 2 (FAIL)
ffff0dc8  ldr r5=0x040019c0 ; movs r2,#0x10 ; ldr r1=0xFFFFF32C("LDBK BLOCKS V00") ; r0=r5
ffff0dd0  bl  #0xffffd2b4                       ; memcmp(okunan_sayfa, "LDBK BLOCKS V00", 16)
ffff0dd4  cbnz r0, 0xffff0de4                   ; eşleşmezse -> FAIL(1)
ffff0dd6  ldr r1=0xFFFFF32C ; adds r1,#0x10 (-> "LDBK CONFIG V00") ; r0=0x04001bc0
ffff0dde  bl  #0xffffd2b4                       ; memcmp(config_buf, "LDBK CONFIG V00", 16)
ffff0de2  cbz r0, 0xffff0de8                    ; eşleşirse -> YÜKLE (config alanlarını kopyala)
ffff0de4  movs r0,#1 ; ret                      ; eşleşmezse -> FAIL(1)
```
- `0xFFFFD2B4` = word-word memcmp (eşit=0, farklı=±1) — doğrulandı (`0xFFFFD2C8 cmp r4,r3`).
- **İki magic zorunlu: "LDBK BLOCKS V00" (`0xFFFFF32C`) + "LDBK CONFIG V00" (`0xFFFFF33C`).**
- **Blok 0'ı 0xFF yaparsan:** oku başarılı olsa bile `0xFF != 'L'` → memcmp≠0 → `0xFFFF0D88` **1 döner**.

### 3.2 `0xFFFF0E62` — CERT imza kontrolü (KOŞULLU: `ctx[0x470]==1`)
Tarama döngüsü yalnız `*(0x04030058+0x470)==1` iken çağırır (`0xFFFF1368 ldrb;cmp#1;bne`).
```
ffff0ece  bl  #0xffff24ce                       ; cert verify -> r0
ffff0ed2  cbz r0, 0xffff0ede                    ; r0==0 -> "@CRT FAIL" dön 1
ffff0ed4  adr r0->"@CRT OK" ; printf ; movs r0,#0 ; ret   ; r0!=0 -> OK
```
`0xFFFF24CE` (cert verify):
```
ffff24ea  bl 0xffffd2b4                          ; memcmp(buf, "LOADER_CERT_TAG1" @0xFFFFF3C0, 16)
ffff24ee  cbnz r0, 0xffff2558                    ; TAG yoksa -> dön 0 (cert FAIL)
ffff2520  bl 0xffff227a                          ; cert başlık alanlarından hash/hazırlık
ffff2552  blx 0xffff5308                         ; << HW CRYPTO imza doğrulama
ffff2556  cbz r0, 0xffff2568                     ; sonuç
```
`0xFFFF5308` (ARM) = **donanım kripto/hash motoru sürücüsü**: veriyi `reg[0x06700494/48C/490/49C]`
data-in register'larına akıtır, `reg[0x06700480]|=1` (start), `reg[0x06700484]&1` (busy) poll, sonucu
`reg[0x06700488]` ile karşılaştırır (`0xFFFF5418 cmp r2,#0`), key/config `ctx[0x4bb/0x4bc]`'den. Bu
**gerçek imza/MAC doğrulaması** — basit memcmp değil. Cert sayfası MPTool'un `VP_WriteCertPage`'iyle
yazılıyor (`ANALIZ_LDBK_YAZMA.md:230,243,373`).

> **Anlam:** İçeriği yamalanmış (yeniden imzalanmamış) bir loader bu kapıyı **geçemez** — gizli anahtar
> olmadan imza forge edilemez. `ctx[0x470]==1` ise yamalı die'lar cert-red.

### 3.3 `0xFFFF0EEC` — LDBK LDPC TABLE magic (üçüncü kapı, her zaman)
```
ffff0f78  ldr r1=0xFFFFF32C ; adds r1,#0x20 (-> "LDBK LDPC TABLE1") ; r0=0x040039c0
ffff0f80  bl 0xffffd2b4 ; cmp r0,#0 ; beq ...    ; memcmp(buf,"LDBK LDPC TABLE1",16)
```
LDPC (ECC) tablolarını okur, "LDBK LDPC TABLE1" magic'ini doğrular. Bulamazsa hata (@LDPF/@LPMF).

### 3.4 Geçince — yükleme `0xFFFF13B2 → 0xFFFF0D70 → 0xFFFF0FD0`
`0xFFFF0FD0` = CodeMap-güdümlü loader kod segmentlerini `0xFFFF0886` (NAND desc oku) ile RAM'e kopyalar.
Seçilen die o an sabittir; boot devam eder (boot-main `0xFFFF01F0` sonrası).

---

## 4. Anlamlı string'ler ve ne anlatıyorlar (ROM boot yolu)

| string | adr | koştuğu yer / anlam |
|---|---|---|
| `@Boot LDR` | `0xFFFF0300` | boot-main banner, yükleme denemesi sonrası (`0xFFFF0214`) |
| `@NoFlash` | `0xFFFF02F4` | `0xFFFF1A48` (bring-up+probe) **0 döndü** (`0xFFFF0200`) |
| `@NoSI` | `0xFFFF02E8` | No SysInfo (`0xFFFF01C0`) |
| `@EFFL` | `0xFFFF02E0` | (empty/fail, `0xFFFF0188`) |
| `@NO DID` | `0xFFFF0C1C` | NAND desc alloc yok (`0xFFFF0886` yolu; BULGULAR C3) |
| `@SMBT FAIL` | `0xFFFF0C2C` | submit fail (`0xFFFF0886` yolu) |
| `@DIE` | `0xFFFF14B8` | die probe/status baskısı (`0xFFFF190E`, `0xFFFF1426`) — 4 kanal status |
| **`@ALL NOFC`** | `0xFFFF14C8` | **HİÇBİR die'da geçerli loader yok** (terminal, `0xFFFF145A`) |
| `@CRT OK/FAIL` | `0xFFFF1094/A0` | cert verify sonucu (`0xFFFF0E62`) |
| `@LD1F/@LDPF/@LPMF` | `0xFFFF1080..` | loader/LDPC sayfa oku hataları (`0xFFFF0E62/0EEC`) |
| `@RRC MAX` | `0xFFFF10E8` | read-retry-count max |

> `"no die at step0"`, `"SYS DIE MAP"`, `"DIE CNT"`, `"GDP_BLOCK_QNTY"`, `"Erase CodeBlock"` string'leri
> **ROM'da YOK** — bunlar GDP loader / ürün firmware'ine ait (ROM'un işi bitince yüklenen katman).

---

## 5. Neden c3ce2 seçiliyor — ve yamalı die'ların durumu (mantıksal kanıt)

**Gözlem (görev gerçeği):** 16 die, 15'i yamalı (0xE0 imzalı), c3ce2 fabrika (0xD3); boot **c3ce2**'den.

**ROM sıra-analizi:** Blok-dış tarama → blok 0 tüm (aday) die'larda önce. c3ce2, tarama sırasında
**ilk değil** (CE2 içinde 4., ondan önce c0ce2/c1ce2/c2ce2). Eğer bu 3 yamalı die geçerli sayılsaydı,
biri (c0ce2) blok 0'da c3ce2'den **önce kazanırdı**. Kazanmıyor → **bu 3 yamalı die REDDEDİLİYOR**.

**⇒ Yamalı loader'lar ROM tarafından reddediliyor.** En olası mekanizma: §3.2 CERT imza kapısı
(`0xFFFF5308` HW crypto). Ayrıca "tek-bayt imza yaması 15 die'ı boot-dışı bıraktı" gerçeğinin kendisi,
o imza baytının **doğrulandığını** (cert aktif) gösteren bağımsız kanıttır — cert kapalı ve bayt kozmetik
olsaydı yama işe yarar / boot die'ı değiştirirdi.

> Bu, `ANALIZ_BOOT_RECOVER.md`'nin H1-ROM hipotezini ("ROM yamalı kopyayı reddediyor") **mekanizmayla
> doğrular**: ret = ROM-seviyesi cert/imza kapısı (`0xFFFF24CE → 0xFFFF5308`, ctx[0x470] geçitli).

---

## 6. ★ ÖNGÖRÜ — c3ce2 blok 0 silinirse ne olur (kanıt-temelli, "kesin" değil)

### 6.1 Doğrudan cevap
**Boot 15 yamalı die'a DÜŞMEZ.** İki bağımsız sebep:

**(a) Blok-0-tek silme muhtemelen ETKİSİZ (c3ce2 hâlâ boot eder).**
ROM her die için **16 yedek blok** tarıyor (`table = {0,4,1,8,2,0x20,...}` @ `0xFFFFF35C`). Yalnız blok 0
silinirse: blok 0'da c3ce2 magic-fail → ama tarama blok 4, 1, 8, ...'e geçer; c3ce2'nin bu bloklardan
**herhangi birinde** yedek loader kopyası varsa `0xFFFF0D88` geçer → **yine c3ce2'den boot**. (Fabrika
loader'ının kaç blokta durduğu c3ce2 okunmadan bilinemez; MPTool çoklu kopya yazıyor → yedek olası.)

**(b) c3ce2'nin TÜM kopyaları silinse bile → boot ÖLÜR, yamalıya düşmez.**
c3ce2 hiçbir blokta geçerli değilse: tarama diğer die'lara bakar → hepsi yamalı → **cert-red** (§5) →
hiçbir die tüm kapıları geçmez → `0xFFFF13AA` → terminal **`@ALL NOFC`** (+ boot-main `@NoFlash`,
status `0x20/0x40/0x80`) → **boot başarısız**. Fallback YOK (cert-fail → skip; downgrade/insecure-retry
yolu ROM'da yok — `0xFFFF138C`'den sonra yalnız "sonraki die").

### 6.2 Kanıt gücü / belirsizlikler (dürüst)
- **KANITLI (ROM disasm):** die tarama var; magic-yoksa-skip var; cert kapısı gerçek HW crypto; terminal
  @ALL NOFC; blok-dış 16-yedek tarama; die=CH|(CE<<2) sırası; fallback-to-insecure YOK.
- **KANITLI (mantık+gözlem):** yamalı die'lar reddediliyor (c3ce2 sıra-4 olmasına rağmen kazanıyor).
- **KANITLANAMADI (statik):** `ctx[0x470]` (cert-enable) canlı değeri — presence/config bölgesi
  (`0x04030052`, `0x040304c8`) dump'ta yok; bulk-copy ile doluyor, ROM'da sabit yazıcı yok. Ama §5'teki
  gözlem cert'in **fiilen aktif** olduğunu güçlü ima ediyor.
- **KANITLANAMADI:** c3ce2 fabrika loader'ının kaç/hangi bloklarda olduğu (c3ce2 okunmadan bilinemez).
- **Not:** Bu, geri-dönüşsüz bir silme kararı. Kanıtlar **"silme = boot ölür veya etkisiz; işe yaramaz"**
  yönünü destekliyor; **"silme = yamalıya düşer"** yönünü destekleyen hiçbir ROM-kanıtı YOK.

### 6.3 Neden plan (c3ce2 sil → yamalıdan boot) çalışmaz — özet
ROM boot **imza-doğrulamalı** loader seçiyor. Yamalı loader'lar imzayı geçmiyor (zaten bu yüzden
etkisizler). c3ce2, cert'i geçen **tek** die. Onu silmek = ROM'un boot edebileceği tek loader'ı yok
etmek → boot ölür. c3ce2'yi silmek yamalıları geçerli yapmaz.

---

## 7. ALTERNATİFLER (die-map/DPD/sıra ile boot die değiştirilebilir mi?)

| Yol | Mümkün mü? | Kanıt |
|---|---|---|
| ROM tarama **sırasını** değiştir (blok/die order) | **Hayır** | Blok tablosu `0xFFFFF35C` ROM-sabit; die döngüsü ROM-kodu. NAND'dan değiştirilemez. |
| ROM'a c3ce2'yi **presence-bitmap**'ten atlatmak | Pratikte hayır | `0x04030052` fiziksel probe'dan (`0xFFFF1860`, READ status==0xE0) doluyor; c3ce2 okunabildiği için probe'a yanıt verir. |
| **DPD die-remap** ile boot die değiştir | Hayır (ROM için) | DPD `+0x2D0/+0x310` (`ANALIZ_DIEREMAP`) **GDP/ürün-firmware** die kapısı; ROM boot loader seçimini etkilemez (ROM DPD'yi bu aşamada okumuyor; presence HW-probe). |
| Yamalı die'ı cert'ten geçirmek | Hayır | Geçerli imza gerekir (gizli anahtar) veya `ctx[0x470]=0` (o da güvenilir config'ten gelir). |
| **ROM download modu + GDP loader** | **Evet (bu görevin dışı)** | Boot-main bootstrap `0x040304cf` != 5/7 → `0xFFFF2596` vendor/download yolu. GDP loader NAND loader-seçimini **tamamen baypas eder** (ekibin `jdnbd4.py`/`InitGDP` yolu). Kalıcı çözüm bu tarafta. |

> **Öneri:** c3ce2 silme, boot'u yamalıya düşürme amacına hizmet etmez (yüksek olasılıkla ya etkisiz ya
> boot-öldürücü). Boot die'ı gerçekten değiştirmek isteniyorsa tek gerçekçi yol imza-geçerli bir loader
> ya da ROM-download-modu/GDP yolu — kod/blok silme değil.

---

## 8. İleri iş için adres haritası (ROM boot yolu)

| ne | adres |
|---|---|
| Reset handler (ARM) | `0xFFFF0324` |
| Boot-main (ARM) | ~`0xFFFF00C0` (literal pool `0xFFFF02C4..0xFFFF0320`) |
| Bring-up + die probe | `0xFFFF1A48` (→ `0xFFFF1860` probe, `0xFFFF1764/17F8` per-kanal oku, `0xFFFF3292` cmd, status==0xE0) |
| **Die tarama + seçim + yükle** | **`0xFFFF1300`** (dış blok `r6`, orta CE `r5`, iç CH `r4`) |
| r8 / CE-yarısı seçici | `0xFFFF12D0` |
| Blok tablosu (16 yedek) | `0xFFFFF35C` = `{0,4,1,8,2,0x20,0x10,6,0xc,3,0x18,0x30,0x40,0x60,0x80,0xc0}` |
| **LDBK BLOCKS+CONFIG magic** | **`0xFFFF0D88`** (memcmp `0xFFFFD2B4`) |
| CERT imza (koşullu ctx[0x470]) | `0xFFFF0E62` → `0xFFFF24CE` → **`0xFFFF5308`** (HW crypto `0x06700400`) |
| LDBK LDPC magic | `0xFFFF0EEC` |
| Loader kod yükle (CodeMap) | `0xFFFF0FD0` → `0xFFFF0886` (NAND desc oku) |
| NAND page read primitive | `0xFFFF07F8` (dön ==1 başarı) |
| skip-on-fail dalı | `0xFFFF1364 cbnz` / `0xFFFF137C` / `0xFFFF138C` (status\|=0x40) → `0xFFFF1392` next die |
| success dalı | `0xFFFF138A cbz → 0xFFFF13B2` (yükle) |
| terminal "hiç yok" | `0xFFFF13AA → 0xFFFF13E8/1446` → `@ALL NOFC` |
| magic string'ler | `0xFFFFF32C` BLOCKS · `0xFFFFF33C` CONFIG · `0xFFFFF34C` LDPC TABLE1 · `0xFFFFF3C0` LOADER_CERT_TAG1 |
| die-presence bitmap | `0x04030052` (4 bayt, [CH] baytı, bit CE) |
| boot context tabanı | `0x04030058` (ctx[0x470]=cert-enable, ctx[0x46b], ctx[0x477]=boot-mode, ctx[0x467/47f/488]=geometri) |

## 9. BULAMADIKLARIM / yapılmayanlar
- `ctx[0x470]` (cert-enable) canlı **değeri** — statik olarak çıkmıyor (config bölgesi dump'ta yok);
  §5 gözlemi aktif olduğunu ima ediyor ama sayısal doğrulama yok.
- `0xFFFF5308` kripto algoritmasının **tam kimliği** (RSA mı, AES-CMAC mı, keyed-hash mı) — HW motoru,
  keyed olduğu (context'ten key okuyor) görülüyor; kesin isim çıkarılmadı.
- c3ce2 fabrika loader'ının **kaç blokta** durduğu — c3ce2 okunmadan bilinemez (silme etkinliği buna bağlı).
- GDP loader (`re/gdp/c1.bin`) die tarama — ROM cevabı kesin olduğu için derinlemesine bakılmadı; GDP
  yalnız download-modu alternatifi (§7).
- Diske hiçbir komut gönderilmedi (görev sınırı) → hiçbir öngörü canlı test edilmedi.
