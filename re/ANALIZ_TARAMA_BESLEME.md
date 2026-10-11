# JD1024 / MAP1202 — part8 NAND boot-blok TARAMASI: beklenen veri, hedef adres, besleme mümkün mü?

Tarih: 2026-09-20 · **%100 statik analiz** — diske/kaplikaya'ya hiçbir komut gönderilmedi.
Kaynaklar: `fwram/jd_v6_dogru.bin` (12 section), `re/fw_canli/e*.bin`, `re/maskrom_FFFF0000.bin`,
`kanit/c3ce2_blok0_tam.bin`. Her iddia dosya+offset+disasm ile.
Araç: scratchpad `img.py` / `xref.py` / `litref.py` / `calls.py` (ROM + 12 section birleşik image map).

---

## KARAR (6 satır — önce bunu oku)

```
1. Tarama BİR VERİ ÜRETMİYOR. Okunan sayfa ROM'un 0x040019C0 buffer'ına DMA ediliyor ve
   firmware'de bu adresi okuyan TEK BİR kod yok (12 section + live dump tarandı: sıfır referans).
2. Döngü bir "NAND engine liveness probe"u: ROM read 1 dönüyor mu? Payload ATILIYOR.
   => "Veriyi elle besle" YOLU YOK. Beslenecek bir hedef yapı yok.
3. ASERT M(1)F(13)L(104) firmware kontrolü DEĞİL — CPU'nun PREFETCH ABORT handler'ı
   (vektör 0x0C -> 0x000007AC). "Çöp adrese atladı" demek; hangi veri eksik demiyor.
4. ASERT M(1)F(9)L(209) = 0x010900D1 = part8 0x040C0084 = "64 kombinasyonun hepsinde tarama
   başarısız" (yamadan ÖNCEKİ hata). İkisi tamamen farklı olaylar.
5. Crash penceresi KESİN: son SRIC log'u ile bir sonraki printf ("Stwo:%x %x") arasında,
   yani 0x040C6CD4 kuyruğu + `bl 0x040C2BA0` (PCIe/NVMe + IRQ bring-up).
6. TEK ATIŞLIK TEŞHİS: cihaz crash'te sonsuz döngüde duruyor, RAM sabit. `0x008094F8`'den
   0x1C bayt + `0x0081FB00`'den 4 bayt (=lr) OKU. lr, çöp adrese atlayan dalın HEMEN SONRASI.
```

---

## 1. Tarama döngüsünün TAM decode'u — `0x040C0000` (part8)

Dosya: `fwram/jd_v6_dogru.bin` foff **0x71000** (= `re/fw_canli/e08_0x040C0000.bin`), RAM 0x040C0000.

```
040c0000  2de9f04f  push.w {r4,r5,r6,r7,r8,sb,sl,fp,lr}
040c0004  ff48      ldr  r0,[pc,#0x3fc]   ; [040c0404]=06600140
040c0008  4ff00008  mov.w r8,#0
040c000c  416d      ldr  r1,[r0,#0x54]    ; r1 = reg[0x06600194]
040c000e  fe4a      ldr  r2,[pc,#0x3f8]   ; [040c0408]=04030058   <- ROM boot CONTEXT
040c0010  0192      str  r2,[sp,#4]       ; her okumanın arg0'ı
040c0014  c1f30461  ubfx r1,r1,#0x18,#5   ; r1 = (reg[0x06600194]>>24)&0x1F
040c0018  fc4a      ldr  r2,[pc,#0x3f0]   ; [040c040c]=0080a000
040c001a  0260      str  r2,[r0]          ; reg[0x06600140] = 0x0080A000  (cmd-ring base)
040c001e  41f20002  movw r2,#0x1000
040c0022  8260      str  r2,[r0,#8]       ; reg[0x06600148] = 0x1000     (ring size)
040c0024  a1f10809  sub.w sb,r1,#8        ; sb = blok kaydırması (ölçülen: 4)
040c0028  dff8e4b3  ldr.w fp,[pc,#0x3e4]  ; [040c0410]=ffff0887          (ROM NAND read, Thumb)
040c002c  4ff0040a  mov.w sl,#4           ; chunk sayısı = 4
--- DIŞ  r8 = 0..3 (0x040C0030) : r7 = 0x00000300 + r8
--- ORTA r5 = 0..3 (0x040C003A) : r6 = 0x00000300 + r5
--- İÇ   r4 = 0..3 (0x040C0044) :
040c0044  4ff04403  mov.w r3,#0x44         ; << PAGE = 0x44 = 68
040c0048  387b      ldrb r0,[r7,#0xc]      ; r0 = byte[0x0000030C + r8]   (CE tablosu)
040c004a  04fa09f2  lsl.w r2,r4,sb         ; r2 = r4<<sb  << BLOK = 0,16,32,48
040c004e  317d      ldrb r1,[r6,#0x14]     ; r1 = byte[0x00000314 + r5]   (CH tablosu)
040c0050  cdf800a0  str.w sl,[sp]          ; [sp] = 4  (5. argüman = chunk sayısı)
040c0054  41ea8000  orr.w r0,r1,r0,lsl #2  ; die = CH | (CE<<2)
040c0058  c1b2      uxtb r1,r0
040c005a  0198      ldr  r0,[sp,#4]        ; r0 = 0x04030058
040c005c  d847      blx  fp                ; ROM 0xFFFF0886
040c005e  0128      cmp  r0,#1             ; <<<< YAMA BURADA (cmp r0,r0 yapıldı)
040c0060  18d0      beq  #0x40c0094        ; BAŞARI -> dön
...
040c0080  0028      cmp  r0,#0
040c0082  07d1      bne  #0x40c0094        ; döngü sonunda r0!=0 da kabul
040c0084  e549      ldr  r1,[pc,#0x394]    ; [040c041c]=008096a0
040c0086  e448      ldr  r0,[pc,#0x390]    ; [040c0418]=010900d1  << ASERT M(1)F(9)L(209)
040c0088  0860      str  r0,[r1]
040c0090  07f018ba  b.w  #0x40c74c4        ; assert/halt
```

### 1.1 CE/CH tabloları GERÇEKTEN RAM'de ve DOLU
`0x0000030C..0x0000030F` ve `0x00000314..0x00000317`, part10 (RAM 0x00000000, foff 0x79000) içinde:

```
00000300: b4 00 00 01  10 01 01 01  01 02 10 00 | 00 01 02 03   <- 0x30C..0x30F = {0,1,2,3}
00000310: ff ff ff ff| 00 01 02 03 |ff ff ff ff  03 03 03 03   <- 0x314..0x317 = {0,1,2,3}
```
Yani CE ve CH tabloları kimlik tablosu; **bu veri zaten yerinde**, eksik değil.
(`kur.py`'deki `p[2][0x31C+idx]=0x00` yaması da aynı config bloğundaki **die-presence** tablosunu
hedefliyor: `0x0000031C + die`, 16 girdi, değer 0x03 = die var.)

> ⚠️ 0x00000000..0x00004000 aralığında **part10 part0'ı eziyor** (kur2.py sırası doğru).
> Tam diff: 68 run, hepsi **0x0000..0x04F5** arası = sadece config/kimlik bloğu, KOD AYNI.
> part0 = fabrika default'u ("MX_012345678", "_NVMe_SSD", "SVN1"), part10 = gerçek ürün
> ("JD20", "4 1TB", "20241205"). part4↔part11 aynı ilişki (0x02000000 = ikinci CPU).

---

## 2. ROM `0xFFFF0886` imzası ve **verinin indiği adres**

### 2.1 İmza (kanıt: ROM 0xFFFF0886 + 0xFFFF07F8 + çağıran 0xFFFF0D88)
```
0xFFFF0886(r0=ctx, r1=die, r2=block, r3=page, [sp+0]=nchunk)  -> 1 = OK
0xFFFF07F8(r0=ctx, r1=die, r2=block, r3=page, [sp+0]=bufID)   -> 1 = OK   (tek chunk)
```
`0xFFFF0D88` (LDBK BLOCKS kapısı) çağrısı: `r3=0 (page 0)`, `[sp]=0 (bufID 0)` → imza doğrulandı.

Adres paketleme `0xFFFF14D4`:
```
ffff14d4  lsls r1,r1,#0x10      ; r1 = block<<16
ffff14d6  ubfx r3,r0,#8,#8      ; r3 = die
ffff14da  uxtb r2,r0            ; r2 = sector/plane (0)
ffff14dc  lsrs r0,r0,#0x10      ; r0 = page
ffff14de  lsrs r1,r1,#2         ; r1 = block<<14
ffff14e0  orr.w r0,r1,r0,lsl #6
ffff14e4  orr.w r0,r0,r3,lsl #2
ffff14e8  orrs r0,r2
```
=> **fiziksel adres = (block<<14) | (page<<6) | (die<<2) | sector**
   bit[31:14]=blok · bit[13:6]=sayfa · bit[5:2]=die · bit[1:0]=sektör.

Yani part8'in `r3=0x44` argümanı **sayfa 68**'dir, blok değil. `r2 = r4<<sb` ise **blok**.

### 2.2 bufID → RAM adresi (KESİN, ROM'un kendi kodundan)
ROM `0xFFFF0FD0` (loader kod yükleyici), `0xFFFF0886`'dan döndükten sonra:
```
ffff1190  bd48      ldr  r0,[pc,#0x2f4]   ; [ffff1488]=040019c0
ffff1192  00eb0631  add.w r1,r0,r6,lsl #12 ; src = 0x040019C0 + chunkIdx*0x1000
ffff1196  4846      mov  r0,sb             ; dst = RAM yükleme adresi
ffff1198  0cf094e9  blx  #0xffffd4c4       ; memcpy(dst, src, 0x1000)
```
ve `[sp,#0xc] = cfg[0x31] << 12` (=nchunk*4096) → **chunk boyu = 4096 B**.

Çapraz doğrulama (aynı taban, üç farklı ROM kullanıcısı):
| ROM okuması | beklenen offset | kullanılan adres |
|---|---|---|
| `LDBK BLOCKS V00` = sayfa+0x000 | buf0+0x000 | `0x040019C0` (0xFFFF0DC8) |
| `LDBK CONFIG V00` = sayfa+0x200 | buf0+0x200 | `0x04001BC0` (0xFFFF0DDA) |
| `LDBK LDPC TABLE1` = sayfa+0x2000 | **buf2**+0x000 | `0x040039C0` (0xFFFF0EEC) |

=> **buffer N = `0x040019C0 + N*0x1000`**, 4 chunk = 16384 B = tam bir NAND sayfası. ✔

### 2.3 O hâlde tarama şunu okuyor
`die = CH|(CE<<2)` (16 die) × `blok ∈ {0,16,32,48}` × **sayfa 68** → 16 KB
→ **RAM `0x040019C0 .. 0x040059BF`**.

Sayfa 68 = `c3ce2_blok0_tam.bin` offset **0x110000**: `"LDBK NANDMEM TAB"` + `"2_CLT_5V_XINYH"`
(NAND micro-sequence / parametre tablosu).

---

## 3. ★ O VERİYİ OKUYAN KOD YOK — besleme yolu kapalı

12 section (`fw0..fw11`) + 12 live dump taraması (literal pool + ADR + MOVW/MOVT):

| aranan | firmware'de bulunan referans |
|---|---|
| `0x040019C0` | **0** (sadece ROM: 0xFFFF1074, 0xFFFF1488, 0xFFFF4D94, 0xFFFF5A10, 0xFFFF5C88) |
| `0x04001BC0` | **0** (sadece ROM 0xFFFF107C) |
| `0x040029C0` | **0** (sadece ROM 0xFFFF1090) |
| `0x040039C0` | **0** (sadece ROM 0xFFFF0C48, 0xFFFF10C8) |
| `0x040049C0` | **0** (hiçbir yerde) |

Firmware'in **kendi** NAND buffer'ları başka yerde. part6 (0x04060000) boot'ta hafıza haritasını
basıyor (0x0406A0E0 civarı, `adr` hedefleri ile doğrulandı):
```
FWSHPSQ [0x04001500, 0x04001528]
FWCQ    [0x04001540, 0x04001940]
SRAM LL [0x04001940, 0x04001A20]
DRAM LL [0x04001A40, 0x04001A40]
SRAM-Buf[0x04001A40, 0x04073640]     <- firmware veri buffer havuzu
RCT     [0x0531CC00, 0x0532CC00]
TBMT    [0x04073800, 0x040A3800]
```
ve part8 0x040C169A: `r1 = 0x04001A40 + ((i + i*64) << 6)` → **buffer adımı 65*64 = 0x1040**
(4096 veri + 64 spare). Yani firmware sayfa verisini `0x04001A40 + i*0x1040`'ta bekler,
`0x040019C0 + i*0x1000`'de değil.

**SONUÇ (S1/S2/S5'in cevabı):** `0x040C0000` döngüsünün RAM çıktısı YOK. Dönüş değeri (r0) dışında
hiçbir yapı dolmuyor; `0x04030058` ROM context'i de bu fonksiyonda güncellenmiyor. Döngü bir
**NAND engine canlılık testi**: "ROM read gerçekten tamamlanıyor mu?". Sayfa 68 seçilmiş çünkü
o sayfa her zaman yazılı → erased-page/ECC hatası dönmemeli. **Elle veri koyarak taramayı
"atlatmak" diye bir şey yok — atlatılacak veri tüketicisi yok.**

---

## 4. ASERT kodlarının decode'u

`0x008096A0` = assert-info word. Format: **(modül<<24) | (fonksiyon<<16) | satır(16 bit)**.

### 4.1 `M(1)F(9)L(209)` = `0x010900D1`
Tek geçtiği yer: part8 literal pool `0x040C0418` (foff 0x71418, `d1 00 09 01`), kullanan kod
`0x040C0084-0x040C0090`. Anlamı: **4×4×4 = 64 denemenin hepsinde ROM read başarısız**.
(Yamadan önceki durum. Kök neden BULGULAR C2/C3: `reg[0x066000C0]` bit31 hiç set olmuyor →
`@NO DID` → r0=0 → NAND command engine hiç bring-up edilmemiş.)

### 4.2 `M(1)F(13)L(104)` = `0x010D0068` — **firmware kontrolü DEĞİL, CPU exception**
Literal `0x000009A4` (part0/part10 foff 0x9A4), kullanan komut **`0x00000838`**:
```
00000834  60119fe5  ldr r1,[pc,#0x160]  ; [0000099c]=008096a0
00000838  64019fe5  ldr r0,[pc,#0x164]  ; [000009a4]=010d0068
0000083c  000081e5  str r0,[r1]
00000840  d80700fa  blx #0x27a8
00000844  feffffea  b   #0x844          ; SONSUZ DÖNGÜ
```
`0x00000838` → fonksiyon başı **`0x000007AC`** → vektör tablosu (RAM 0x00000000):
```
0x00 Reset 0x0000204C · 0x04 Undef 0x00000674 · 0x08 SVC 0x00000710
0x0C PREFETCH ABORT 0x000007AC  · 0x10 Data Abort 0x00000848 · 0x14 rsvd 0x000008E4
0x18 IRQ 0x00000664 · 0x1C FIQ 0x00000654
```
Aynı ailenin tamamı (literal havuzu `0x00000998..0x000009AC`):
| kod | = | handler |
|---|---|---|
| `0x010D004E` | M1 F13 L78 | Undef (0x674) |
| `0x010D005B` | M1 F13 L91 | SVC (0x710) |
| **`0x010D0068`** | **M1 F13 L104** | **Prefetch Abort (0x7AC)** |
| `0x010D0079` | M1 F13 L121 | Data Abort (0x848) |
| `0x010D0087` | M1 F13 L135 | reserved (0x8E4) |

`Er_type` bit haritası (her handler `[0x008094F8] |= bit` yapıyor):
bit0 Undef · bit1 SVC · **bit2 Prefetch Abort** · bit3 Data Abort · bit4 rsvd.
→ **`Er_type[4]` = sadece prefetch abort.** ✔

`IFSR[108]` = 0x108, FS[3:0]=8 = **synchronous external abort on instruction fetch**
= `0x0029D2C4` eşlenmemiş adres, bus hata döndürdü. (MPU değil, bus.)

> **S3'ün cevabı:** `0x0029D2C4` hiçbir tabloda/pointer'da YOK. 12 section + ROM + blok0 dump'ında
> `C4 D2 29 00` word'ü **sıfır kez** geçiyor; MOVW/MOVT ile de üretilmiyor. Yani bu adres
> **imajdan gelmiyor** — çalışma zamanında bir RAM hücresinden okunan artık/çöp bir pointer.
> Statik olarak hangi hücre olduğunu kanıtlayamadım (bkz. §7 açık uç). Ama nereden okunduğunu
> tek okumada bulmanın yolu var (§6.A).

---

## 5. Crash penceresi — KESİN daraltma

part8 ana akış (`0x040C02F4` entry → `0x040C023A`):
```
040c0284  bl  0x040C0000                 ; TARAMA (yamalı)
040c0288  movw r0,#0xf000 ; [sp]=0xF000 ; r1=0xF0000 ; r0=0 ; r2=1 ; r3=0
040c0296  blx 0x040C6CD4                 ; SRIC init  -> "SRIC-Init" / "SRIC-Update" / "SRIC-ecc-dummy"
040c029e  ldr r0,[0x00000398] ; tst #0x20000
040c02a6  beq 0x040C02C6                 ; ** bu image'da [0x398]=0x02C10000 -> DAL ALINIR **
040c02c6  bl  0x040C2BA0                 ; <<< iki log arasındaki TEK çağrı
040c02ca  r2=0x040C0000 ; r1=0x040BFA00 ; r0=0x00804054
040c02d0  bl  0x040C7530                 ; printf("Stwo:%x %x", ...)   << LOG'DA YOK
```
- `0x040C6CD4` gerçekten SRIC init: `r4=0x0600C000`, `add r0,pc,#0x298`→`0x040C6FAC`
  `"SRIC-Init:%x,%x,%x,%x"`; `add r0,pc,#0x270`→`0x040C6FC4` `"SRIC-Update..."`;
  `0x040C6EDC add r0,pc,#0x100`→`0x040C6FE4` `"SRIC-ecc-dummy..."`. Sonra `pop` (0x040C6F3C).
- `0x00804054` = part2'de **`"Stwo:%x %x\r"`** (doğrulandı).
- `[0x00000398]` hem part0 hem part10 değerinde `& 0x20000 == 0` → `bl 0x040C4424` **koşmuyor**.

**=> Çöp atlama ya `0x040C6CD4`'ün son print'inden sonraki kuyruğunda (0x040C6EE4..0x040C6F3C)
ya da `0x040C2BA0` alt ağacında.** `0x040C2BA0` = PCIe/NVMe + timer + IRQ bring-up
(`reg[0x06722000+p<<8]`, `reg[0x06713000+p<<8]`, `reg[0x060030A8]` 'NVMe'/'LOOT'/0x66994EE4 magic).

### 5.1 Bu penceredeki TEK kanıtlanabilir "uninitialised pointer üzerinden dallanma"
```
IRQ vektörü 0x00000664 -> bl 0x00000A74:
00000a78  ldr r4,[pc,#0x4c]   ; r4 = 0x06004000        (VIC)
00000a7c  ldr r0,[r4,#0xc]    ; r0 = reg[0x0600400C]   (aktif IRQ'nun vector address'i)
00000a80  cmp r0,#0 ; beq ret
00000a88  ldr r0,[r0]         ; r0 = *(vector)         <- HANDLER POINTER
00000a8c  blx r0              ; <<< TEK DOLAYLI ÇAĞRI
FIQ 0x00000654 -> 0x00000AA0 : aynı, reg[0x06004008] üzerinden.
```
Handler tablosu: `0x00000A14(r0=irq, r1=prio, r2=fn)` → `*(0x0080951C + irq*4) = fn`,
öncelik `reg[0x06004040 + (irq>>2)*4]`, sonra `reg[0x06004014] = 1<<irq` (enable).

VIC init `0x040C0600` (ARM), `blx` ile 0x040C024A'da çağrılıyor:
```
040c0600  r0=0x0080951C ; r1=0x80 ; bl 0x040C7590      ; bzero(0x0080951C, 0x80)  (32 girdi)
040c0610  r1=0x06004000 ; r0=0xFFFFFFFF
040c0618  reg[0x06004010]=0xFFFFFFFF                   ; TÜM IRQ'ları maskele
040c061c  reg[0x06004000]=0xFFFFFFFF ; reg[0x06004004]=0xFFFFFFFF
040c062c  reg[0x06004018]=0x0080951C                   ; VECTOR TABLE BASE
040c0638  reg[0x06004040+i*4]=0 (i=0..7)               ; öncelikler
```
**Sıralama problemi:** entry `0x040C02F4`:
```
040c02f8  blx 0x040C388C -> 0x00002364   ; SCTLR |= 0x1000|0x4  (I-cache + D-cache AÇ)
040c02fc  blx 0x040C3894 -> 0x000023F4   ; SCTLR &= ~0x2000     (low vectors: 0x00000000)
040c0300  mrs r0,apsr ; bic r0,#0xC0 ; msr cpsr_c,r0  << IRQ+FIQ AÇILIYOR (0x040C0308)
040c0310  r0=0x00810000 ; r1=0x00010000 ; blx 0x040C7590        ; bzero(0x810000, 0x10000)
040c035c  bl  0x040C023A -> ... -> 0x040C024A blx 0x040C0600     ; VIC ancak BURADA maskeleniyor
```
- `0x040C7590` → veneer → `0x00009CB8` = **bzero(ptr,len)** (doğrulandı, `stmhs.w r0!,{r2,r3,ip,lr}` döngüsü).
- Firmware **yalnızca `0x00810000..0x00820000`'ı sıfırlıyor**. `0x00808000..0x00810000` — ki içinde
  IRQ tablosu `0x0080951C`, hata kaydı `0x008094F8`, assert word `0x008096A0`, CPU id `0x00809514`,
  NAND ring `0x0080A000` var — **hiçbir section tarafından yüklenmiyor ve firmware tarafından
  sıfırlanmıyor**. Normal boot'ta soğuk SRAM sıfırdır; host'tan tekrar tekrar RAM-boot denerken
  DEĞİLDİR (önceki denemelerin artığı kalır).
- `0x040C0308` ile `0x040C024A` arasında (cache açık, vektörler 0x00000000'da, VIC hâlâ **ROM'un**
  konfigürasyonunda) alınan herhangi bir interrupt `blx r0` ile rastgele bir adrese gider.

> Dürüst sınır: bu mekanizmanın **var olduğu** kanıtlı; crash'in **bu** olduğu kanıtlı değil.
> Kesin cevap `lr`'de (§6.A).

---

## 6. UYGULANABİLİR ÖNERİLER (öncelik sırasıyla)

### A. ★ ÖNCE BUNU YAP — hata kaydını oku (tek atış, 30 saniye)
Crash'ten sonra firmware `0x00000844`'te `b .` ile **sonsuz döngüde**; RAM sabit ve okunabilir
(telsiz canlı RAM okuma yolunuz var). Oku:

| adres | uzunluk | ne |
|---|---|---|
| **`0x0081FB00`** | 4 | **lr** — çöp adrese atlayan dalın HEMEN SONRASI. Tek başına crash'i lokalize eder. |
| `0x008094F8` | 0x1C | +0x00 Er_type · +0x04 DFSR · +0x08 IFSR · +0x0C DFAR · +0x10 IFAR · +0x14 ADFSR · +0x18 AIFSR |
| `0x008096A0` | 4 | assert word (M/F/L) |
| `0x0080951C` | 0x80 | IRQ handler tablosu (32 girdi) — içinde `0x0029D2C4` çıkarsa §5.1 KANITLANIR |
| `0x0600400C` / `0x06004008` | 4+4 | VIC aktif IRQ/FIQ vector address |

`lr` değeri part8/part3/part0 aralığındaysa doğrudan `img.py <lr-4> 1` ile hangi `blx`/`bx`
olduğunu bulursunuz. **UART log'unda zaten basılıyor** (`Err_type[%x]lr[%x]`) — log satırının
tamamı elinizde varsa okumaya bile gerek yok.

### B. "Veriyi elle besle" → YAPMA, işe yaramaz
Beslenecek tüketici yok (§3). Yine de denemek isterseniz zararsız KOPYALA listesi (tam ve doğru):

| RAM hedefi | kaynak: `kanit/c3ce2_blok0_tam.bin` | uzunluk |
|---|---|---|
| `0x040019C0` | offset `0x110000` (sayfa 68, +0x0000) | 0x1000 |
| `0x040029C0` | offset `0x111000` (sayfa 68, +0x1000) | 0x1000 |
| `0x040039C0` | offset `0x112000` (sayfa 68, +0x2000) | 0x1000 |
| `0x040049C0` | offset `0x113000` (sayfa 68, +0x3000) | 0x1000 |

(sayfa 68 = `LDBK NANDMEM TAB`; döngünün ilk denemesi zaten blok 0 / r4=0.)
**Beklenen etki: SIFIR.** Bu buffer'ı okuyan kod yok; ayrıca ROM read başarısız olduğunda DMA
zaten hiç yazmıyor, dolayısıyla koyduğunuz veri orada kalır ama kimse bakmaz.

### C. ★ Asıl düzeltme: taramayı "başarılı say" değil, **gerçekten başarılı yap**
`@NO DID` = `reg[0x066000C0]` bit31 hiç set olmuyor = NAND command engine bring-up edilmemiş
(ROM `0xFFFF1A48` download mode'da atlanıyor — BULGULAR C2/C4). Yamayı kaldırın, yerine
tarama ÖNCESİ bir kez ROM bring-up'ını çağırın:
```
r0 = 0x04030058
blx 0xFFFF1A49        ; Thumb girişi
```
En pratik uygulama (part8'e dokunmadan): 0x82 JumpToPRAM ile zaten kendi stub'ınıza atlıyorsunuz —
stub'ı şöyle yapın:
```
  ldr r0, =0x04030058
  ldr r1, =0xFFFF1A49
  blx r1
  ldr r1, =<firmware entry, 0x040C02F4|1>
  bx  r1
```
⚠️ Her yeni stub'ı **yeni bir adrese** yazın (aynı adrese ikinci stub = I-cache'te bayat kod
çalışır — `feedback_enjekte_kod_icache_bayat`). Ayrıca part8 `0x040C0304` ile I-cache'i açıyor,
o noktadan sonra yazdığınız hiçbir kod güvenilir değil.

Bu çalışırsa `cmp r0,#1` yamasına gerek kalmaz ve **taramadan sonraki tüm NAND yolu (part7
sürücüsü, FWCQ, LDPC) da canlı** olur — zorlama yamasıyla o kısım ölü kalıyor.

### D. Erken interrupt penceresini kapat (ucuz, §5.1 sınıfını tamamen yok eder)
Firmware'e atlamadan ÖNCE host'tan:
1. `reg[0x06004010] = 0xFFFFFFFF`  (VIC tüm IRQ'ları maskele)
2. `bzero(0x00808000, 0x8000)`     (firmware'in hiç temizlemediği BSS; IRQ tablosu 0x0080951C,
   0x008094F8, 0x008096A0, ring 0x0080A000 burada)
3. (isteğe bağlı, daha agresif) `0x040C0308`'deki Thumb-2 `msr cpsr_c,r0`'yı NOP'la:
   dosya offset **`0x71308`**, `80 f3 00 81` → `00 bf 00 bf`.
   ⚠️ Bu akışta interrupt'ları tekrar açan başka bir yer görmedim; kalıcı bırakmayın, sadece
   "crash kayboluyor mu" testi için kullanın.

### E. Doğrulanmış patch offset'leri (referans)
| RAM | dosya offset (`jd_v6_dogru.bin`) | mevcut baytlar | not |
|---|---|---|---|
| `0x040C005E` | `0x7105E` | `01 28` (`cmp r0,#1`) | sizin yamanız `80 42` (`cmp r0,r0`) |
| `0x040C0308` | `0x71308` | `80 f3 00 81` (`msr cpsr_c,r0`) | D.3 |
| `0x040C0408` | `0x71408` | `58 00 03 04` (=0x04030058) | ROM ctx literali |
| `0x040C0410` | `0x71410` | `87 08 ff ff` (=0xFFFF0887) | ROM read pointer |
| `0x040C0418` | `0x71418` | `d1 00 09 01` (=M1F9L209) | sadece hata yolunda kullanılıyor |
| part8 tabanı | `0x71000` | — | RAM 0x040C0000, 0x4000 bayt |

---

## 7. ÇÖZEMEDİKLERİM (dürüst liste)

1. **`0x0029D2C4`'ün tam kaynağı.** Bu word hiçbir image'da yok (literal/ADR/MOVW-MOVT taraması
   12 section + ROM + blok0 dump üzerinde sıfır sonuç). Çalışma zamanı artığı. `lr` olmadan
   statik olarak hangi hücreden okunduğunu kanıtlayamadım. §6.A tek okumada çözer.
2. **Crash'in `0x040C6CD4` kuyruğunda mı `0x040C2BA0` içinde mi olduğu.** Pencere kanıtlı,
   nokta değil. `0x040C2BA0` ~200 komut + 10 alt çağrı; `lr` olmadan tek tek dolaşmak
   verimsiz olurdu.
3. **`sb` (`(reg[0x06600194]>>24)&0x1F) - 8`) değerinin canlı doğrulaması.** Sizin ölçtüğünüz
   4'ü kullandım → taranan bloklar {0,16,32,48}. Register statik olarak okunamıyor.
4. **`reg[0x0600400C]` (VIC vector-address) semantiğinin canlı doğrulaması.** ROM'un VIC'i nasıl
   bıraktığı bilinmiyor; §5.1 mekanizması kodla kanıtlı ama tetiklendiği kanıtlı değil.
5. **`0x00808000..0x00810000`'ın boot anındaki gerçek içeriği.** Dump'larda yok (section yok).
   §6.A'daki `0x0080951C` okuması bunu da cevaplar.
6. Diske/cihaza hiçbir komut gönderilmedi (görev sınırı) → hiçbir öneri canlı test edilmedi.

---

## 8. Adres haritası (bu analizden yeni çıkanlar)

| ne | adres |
|---|---|
| part8 tarama döngüsü | `0x040C0000` (çağıran `0x040C0284`) |
| part8 entry / init | `0x040C02F4` → `0x040C023A` |
| CE tablosu / CH tablosu | `0x0000030C` (4 bayt) / `0x00000314` (4 bayt) |
| die-presence tablosu (config) | `0x0000031C + die`, 16 girdi, 0x03 = var |
| ürün config bloğu (part10 overlay) | `0x00000000..0x000004F5` |
| ROM NAND read | `0xFFFF0886(ctx,die,block,page,[sp]=nchunk)` |
| ROM tek-chunk read | `0xFFFF07F8(ctx,die,block,page,[sp]=bufID)` |
| ROM adres paketleyici | `0xFFFF14D4` → `(blk<<14)\|(page<<6)\|(die<<2)\|sect` |
| **ROM NAND veri buffer'ı** | **`0x040019C0 + bufID*0x1000`** (chunk 4 KB) |
| firmware kendi buffer havuzu | `0x04001A40 + i*0x1040` (SRAM-Buf, 0x04001A40..0x04073640) |
| firmware FWCQ / SRAM LL | `0x04001540..0x04001940` / `0x04001940..0x04001A20` |
| NAND cmd-ring base/size reg | `reg[0x06600140]` (part8: 0x0080A000) / `reg[0x06600148]`=0x1000 |
| NAND geometri reg | `reg[0x06600194]` bit[28:24] |
| **assert-info word** | **`0x008096A0`** = (M<<24)\|(F<<16)\|L |
| **exception kayıt bloğu** | **`0x008094F8`** (+0 Er_type, +4 DFSR, +8 IFSR, +0xC DFAR, +0x10 IFAR, +0x14 ADFSR, +0x18 AIFSR) |
| **kaydedilmiş lr** | **`0x0081FB00`** |
| CPU id baytı | `0x00809514` (part8 `0x040C0244` ile 1 yazıyor → log'daki `CPU[1]`) |
| vektör tablosu | RAM `0x00000000` (0x0C prefetch abort → `0x000007AC`) |
| **VIC** | **`0x06004000`** (+0x08 FIQ vec, +0x0C IRQ vec, +0x10 maskele, +0x14 aç, +0x18 tablo tabanı, +0x40.. öncelik) |
| **IRQ handler tablosu** | **`0x0080951C`** (32 × 4 bayt) |
| IRQ / FIQ dispatcher | `0x00000A74` / `0x00000AA0` |
| IRQ kaydet / aç / kapa | `0x00000A14(irq,prio,fn)` / `0x000009CC(irq)` / `0x000009E0(irq)` |
| VIC init | `0x040C0600` |
| bzero(ptr,len) | `0x00009CB8` (part8 veneer `0x040C7590`) |
| printf | `0x040C7530` (part3) / ROM `0xFFFF613C` |
| SRIC init | `0x040C6CD4`, blok `0x0600C000`, IRQ 0x14 handler `0x040C6B6C` |
| part8 veneer tablosu | `0x040C387C..0x040C3B24` (84 girdi, hepsi geçerli) |
| part3 veneer tablosu | `0x040C74D0..0x040C7720` (55 girdi, hepsi geçerli) |
| assert/halt | `0x040C74C4` (part8), `0x000027A8` (part0) |
