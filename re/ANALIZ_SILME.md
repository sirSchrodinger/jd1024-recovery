# MAP1202 GDP — SİLME (BlockErase) yolu tam disassembly analizi

Kapsam: sadece statik RE — `c1.bin` (@`0x040C0000`, 0x30000) + `c0.bin` (@`0x0`, 0xC000).
Hiçbir donanıma dokunulmadı. `[READ]` = imajdan bire bir çözüldü, adres verildi.
`[INFER]` = yorum, ağırlık belirtildi. `[UNKNOWN]` = imajdan çıkmıyor, öyle denildi.

Semptom (görevden): disk OKUYOR; SİLME ve PROGRAM 16/16 die'da anında FAIL
(ONFI status `0xE0 -> 0xE1`, bit0=FAIL, WP serbest, die hazır).

---

## 0. Yönetici özeti — önce bunu oku

1. **Silme handler'ı temiz. Die'a doğru komut gidiyor, die kendisi FAIL dönüyor.**
   `0x8B` handler'ında **hiçbir** write-protect / read-only / factory / locked / secure
   bayrağı kontrolü YOK. Erken dönüş yok. Silme, okuma ve programın **aynı** ön-hazırlığını
   (0xBA→0x42→0xD0) kullanır; okuma bu ön-hazırlıkla ÇALIŞTIĞINA göre ön-hazırlık sağlam.
   Silmeyle okumanın tek farkı **son komut**: silme FCQ opcode `0x44/0x4C/0x50/0x58`,
   okuma `0x82/0xB0`. Yani arıza son silme komutunda; die komutu kabul edip (status
   `0xE0` = hazır, yazma serbest) `0xE1` (FAIL) döndürüyor — bu **die seviyesinde
   gerçek bir erase-fail**, firmware'de bir WP/kilit/güç kapısı değil.

2. **Firmware'de 60h/D0h ONFI silme mikrokodu YOK.** Tüm imajdaki her `0x48`-opcode
   (ISSUE CMD) mikrokod kelimesi tarandı: **60h komutu 0 adet, D0h komutu 0 adet**.
   Silme, MAP1202'nin **FCQ donanım sequencer'ına** (`0x06600000`) verilen bir *lojik
   opcode* (`0x44` tek-plane / `0x4C,0x50,0x58` çok-plane) ile yapılır; 60h-satır-D0h-70h
   dizisini **FCQ silikonu üretir**, yüklenebilir mikrokod değil. (Ayrıntı §2.)

3. **Blok 0 silmesi geometriye bağlı değil.** "Erase CodeBlock[0,1] for All Dies" blok
   0/1'i siler; blok 0 plane 0 → NAND row `0` (herhangi bir geometri shift'iyle `0<<n=0`).
   Yani geometri uyuşmazlığı (§4) blok-0 silme FAIL'ini AÇIKLAMAZ. Bu, kök nedenin
   fiziksel olduğu (erase yüksek-gerilim / on-die charge pump ya da GDP'nin temizleyemediği
   bir die block-lock durumu) yönündeki en güçlü kanıt. [INFER, güçlü]

4. Güç tarafı: silme yolu **hiçbir** GPIO / PMIC / vpp / charge-pump register'ı açmıyor.
   `0x0600D000` (GPIO) sadece 5 silme-dışı yerde kullanılıyor. (§6)

---

## 1. Handler'lar, tam silme dizisi, her register yazması ve her koşul

### 1.1 Dispatch tablosu (`0x040ED2F4`, 36 × 12 bayt) — ilgili girişler [READ]

```
idx  cmd phase  handler
 3   8A   01    0x040C3DB4   PageWrite
11   8B   00    0x040C3C90   BlockErase
12   88   02    0x040C488C   ReadFlashID
 6   89   02    0x040C4360   PageRead
```

### 1.2 `0x8B` BlockErase handler `0x040C3C90` [READ]

```
040C3C90  push {r4-r7,lr} ; sub sp,#0x44
040C3C9C  mov r1,#0x40 ; add r0,sp,#4 ; blx 0x040C02B4     ; 64 baytlık stack payload'ı sıfırla
040C3CA4  r6 = 0x00009210                                  ; komut ctx tabanı
040C3CAC  r0 = ctx[8]   (ch)      ; r2 = ctx[0xA] (rowfield u16) ; r1 = ctx[9] (ce|lun)
040C3CB8  cmp r0,#0xff                                     ; ** KOŞUL 1: ch==0xFF ? **
040C3CBC  r3=ctx[0xC] r4=ctx[0xD] (page)
040C3CC4  rev16 r2,r2                                       ; rowfield BE->LE
040C3CC8  cmpne r1,#0xff                                    ; ** KOŞUL 1b: ce==0xFF ? **
040C3CCC  strb r7(=1),[r6,#0x17]                            ; ctx result = 1 (varsayılan OK)
040C3CD0  beq 0x040C3CE8                                    ; ch==FF veya ce==FF -> "tüm die" özel yol
   ; --- NORMAL yol (tek hedef) ---
040C3CD4  str r4,[sp]                                       ; page arg
040C3CD8  bl 0x040D0DB8                                     ; *** SİLME ÇEKİRDEĞİ ***
040C3CE0  mov r0,#1 ; pop -> return 1
   ; --- "tüm die" özel yolu ---
040C3CE8  add r0,pc,#0x8c   ; "Erase CodeBlock[0,1] for All Dies" ; blx print
040C3CF0  add r0,sp,#4 ; mov r1,#1 ; bl 0x040D22DC             ; die listesini kur
040C3CFC  r0 = 0x00009244 ; r1=[r0] (LUN_SHIFT) ; r0=[r0+0x1D] ; r1 = 1<<r1
040C3D14  blx 0x040ED290 (sdiv)                               ; die sayısı
040C3D18  <loop> ctx[0x17] = 0x20 hata ya da 1 ; her die için 0x040D0DB8'e döner
```
`0x8B` handler'ında **WP / kilit / factory / secure / readonly kontrolü YOK.** Tek
koşul `ch/ce == 0xFF` (tek-hedef mi "tüm die" mi). Doğrudan silme çekirdeğine gider.

### 1.3 Silme çekirdeği `0x040D0DB8` — geometri + döngü [READ]

```
040D0DBC  sl_ptr = 0x00000DCC          ; geo pointer'ı (aşağıda)
040D0DDC  r1 = *(0x0DCC) = geo         ; r8 = geo[+4] (PAGE_QNTY u16)
040D0DE8  cmp [sp+0x50],#0             ; ** KOŞUL 2: op-arg (tek/çok plane) **
040D0E14  bl 0x040D09CC               ; (plane_a,plane_b) -> op kodu {0,1,2,3}, [sp+8]'e
040D0E2C  fp = geo[9] (PLN_QNTY)       ; plane sayısı
040D0E78  r0 = geo[0x1F](STPU) - c0[0x9255](PLANE_SHIFT) - 3 ; lsl -> CE alanı
040D0E88  bfi sl, ..., #0,#8           ; row düşük bayt (CE/plane composite)
040D0E90  bfi sl, r6, #0,#0x10         ; blok alanı
040D0EE0  <die/plane döngüsü>:
040D0EE8    blx 0x040ED2AC (udiv: geo[4]/3) ; = per-plane blok stride
040D0EEC    mul r0,r0,r4               ; * plane_index
040D0EF8    bfi sl, r0, #0x10,#0x10    ; row yüksek 16 bit = plane offset
040D0EFC    mov r0, sl                 ; ROW ADRESİ
040D0F00    bl 0x040DDF74             ; *** SİLMEYİ YAYINLA (aşağıda) ***
040D0F04    [sp+0x14] = sonuç
040D0F08    cmp c0[0x9247],#0          ; ** KOŞUL 3: silme-yol bayrağı (durum-okuma yöntemi) **
040D0F3C    bl 0x040DBDCC             ; FCQ completion poll (status kontrol)
040D0F44    "-------..."  ; 0x040DC5A4 ; per-die "%d,%d,%d,%d" bas
```
Blok 0 için `rowfield=0 -> blok=0, plane=0 -> sl=0`. Row = 0. **[READ]**

### 1.4 Silme yayın dağıtıcısı `0x040DDF74` [READ]

```
040DDF74  cmp c0[0x9247],#0
040DDF80  beq 0x040DDF88 -> b 0x040DDC24   ; [0x9247]==0 : normal sequencer
040DDF84  b   0x040DDDD0                    ; [0x9247]!=0 : alternatif sequencer
```
İki farklı silme dizisi motoru var; runtime bayrağı `c0[0x9247]` seçer. Her ikisi de
aynı 3 yapıtaşını kullanır (aşağıda 0x040DDC24 için gösterildi; 0x040DDDD0 aynı sırayla
0xBA→0x42→0xD0→erase yapar, sadece çok-plane döngüsü farklı).

### 1.5 Normal silme sequencer `0x040DDC24` — SIRALI KOŞUL + KOMUT ZİNCİRİ [READ]

```
040DDC3C  cmp c0[0x924A],#0                 ; ** KOŞUL 4: SLC-mode bayrağı **
040DDC48  blne 0x040DC50C                   ;   !=0 ise: 0xBA "SLC prefix" komutu yayınla
040DDC60  bl 0x040DC454                     ; (A) 0x42 CHECK-READY yayınla
040DDC64  cmp r0,#0 ; popeq                 ;   enqueue başarısızsa ABORT (die'a hiç gitmez)
040DDC6C  cmp r4,#0 ; cmpne r4,#1 ; beq ->0x040DDC90   ; op {0,1}
040DDC78  cmp r4,#2 ; cmpne r4,#3 ; beq ->0x040DDCA0   ; op {2,3}
040DDC84  "unknown operation"               ; aksi halde hata
040DDC90  bl 0x040DD850                     ; (B) 0xD0 SWITCH-TO-SLC (set-feature) [op 0/1]
040DDCA0  bl 0x040DDA70                     ; (B') 0xD0 set-feature varyantı        [op 2/3]
040DDCAC  cmp r0,#0 ; popeq                 ;   enqueue başarısızsa ABORT
040DDCC4  b 0x040DD5FC                      ; (C) *** ASIL SİLME: opcode 0x44/4C/50/58 ***
```

**Silmenin die'a giden komutları, gerçek sırayla:**
1. (SLC ise) `0xBA`  — SLC prefix  (`0x040DC50C` → subA2 `0x040E3F28`)
2. `0x42`  — CHECK NAND READY (içeride 70h read-status) (`0x040DC454` → subA `0x040E3D48`)
3. `0xD0`  — SWITCH TO SLC / set-feature (`0x040DD850`/`0x040DDA70` → subA2)
4. **`0x44`** (1-plane) / `0x4C` (2) / `0x50` (3) / `0x58` (4-plane) — **BLOCK ERASE**
   (`0x040DD5FC` → subA `0x040E3D48`)

Silme opcode'u plane sayısına göre `0x040DD5AC` ile seçilir:
`geo[9]==2 → 0x4C`, `==4 → 0x50`, `==6 → 0x58`, aksi `0x44`. Tablo `0x040EE7A8` = {44,4C,50,58}. [READ]

### 1.6 Die'a giden HER register yazması — `0x040E3D48` (subA) [READ]

Yukarıdaki (2)(3)(4)'ün her biri stack'te ~0x1C baytlık bir descriptor kurup subA'yı çağırır.
subA **NIFC `+0x224` PIO yolunu kullanmaz**; FCQ donanım kuyruğuna yazar. Sıralı yazmalar:

```
040E3D4C  desc+4 (opcode) == 0xFFFF ? -> return 0            ; ** KOŞUL 5 **
040E3D5C  desc+0xC (kanal seçici): 0 -> kuyruk FCQ+0x40 (ring 0x0400C900)
                                    2 -> FCQ+0x48 ; else -> FCQ+0x44 (ring 0x0400E100)
040E3D80  boş-slot indexini FCQ+0x4C/+0x40/+0x48'den oku
040E3DA0  tst slot[0x17],#1  (busy biti) -> set ise return 0 ; ** KOŞUL 6: slot boş mu **
   ; --- slot (SRAM ring, 24 baytlık) yazmaları ---
040E3DE0  slot[0x00] = opcode | (d6<<14)|(d7<<17)|(d8<<20)|(dB<<27)|(d9<<29) | 0x80000000 | 0x2000
040E3DF8  slot[0x04] = (dD<<21) | (dF<<24) ;  slot[0x08] = 0
040E3E28  slot[0x0C] = (dE<<4)|((d12&3)<<6)|((d10&0xF)<<8)|((d11&0xF)<<12)   ; plane/LUN/CE
040E3E30  slot[0x10] = desc[0]      ; *** ROW ADRESİ ***
040E3E38  slot[0x16] = desc[0x13]   ; CE bit-maskesi (check-ready'de 0xFF = tüm CE)
040E3E5C  slot[0x14] = FCQ+0x44 (tail idx) ; slot[0x17] = (eski&0xF9)|1  (+2 faz)
040E3E70  dmb sy
040E3E7C  FCQ+0x44 = (eski & ~0xFFFF) | 1     ; *** KAPI ZİLİ (doorbell) — komut motora verildi ***
```

**Silmenin dokunduğu tek donanım register'ları: FCQ ring SRAM (`0x0400E100`/`0x0400C900`)
ve FCQ doorbell `0x06600040/44/48`.** GPIO yok, güç yok, WP yok, NIFC `+0x224` yok. [READ]

### 1.7 `0x8A` PageWrite — aynı iskelet (karşılaştırma için)

`0x040C3DB4` → (staging) → `0x040DE16C`:
```
040DE18C  cmp c0[0x924A],#1 ; blne 0x040DC50C   ; 0xBA SLC prefix
040DE1AC  bl 0x040DC454                          ; 0x42 check-ready
040DE1C4  bl 0x040DD850                          ; 0xD0 switch-to-slc
040DE1E4  bl 0x040DD384                          ; 0x64 PROGRAM (data-in)
          bl 0x040DC454                          ; 0x42 check-ready
```
Program ve OKUMA (`0x040DE038`: 0x42→0xD0→0x82→0xB0) da **tıpatıp aynı** 0xBA/0x42/0xD0
ön-hazırlığını kullanır. Okuma çalıştığına göre ön-hazırlık (SLC set-feature dahil) sağlam.

---

## 2. Silme mikrokodu: NEREDE OLMADIĞI

Mikrokod A tablosu init'te `memcpy(0x06649000, c1@0x2E836, 0xC90)` ile yüklenir; rutin `N`
= `0x06649000 + N*0x10`'daki program. Çözüm kuralları (görevden) doğrulandı: rutin 2 =
`FF800548` = CMD `0xFF` = NAND RESET. ✔

**Tüm imaj tarandı — her `48 05 xx yy` (ISSUE CMD) kelimesi:**
```
CMD 60 (ERASE SETUP)   : 0 adet   <-- YOK
CMD D0 (ERASE CONFIRM) : 0 adet   <-- YOK
CMD 70 (READ STATUS)   : 17 adet
CMD 42                 : 6 adet
```
A tablosundaki 69 rutinin ürettiği TÜM komut baytları:
`00 02 03 1B 2A 2D 2E 30 38 3C 40 42 48 4A 4B 50 51 5A 62 6A 6C 6D 70 71 76 77 7C 88 8B 98 99 D7 DD E8 FF`.
**60h ve D0h bu kümede yok.** Dolayısıyla klasik `60h-satır-D0h-bekle-70h` dizisi
**yüklenebilir mikrokodda mevcut değildir.** [READ]

İlgili rutinlerin çözümü (kural doğrulaması + ne VAR):
```
rutin 0x02 (RESET) : FF800548  CMD FF no-addr END
rutin 0x30 (70h)   : 000009EB DLY9 ; 000030EB DLY48 ; 70800548 CMD70 no-addr ;
                     00000550 ADR n=0 ; 800050EB DLY80 END
rutin 0x13 (02+70) : 0000080B CE ; 000008EB DLY8 ; 02800548 CMD02 ; 03001550 ADR n=3 ;
                     058005A0 A0term ; 70000548 CMD70 addr ; 000050EB DLY80 ; 80001256 PIO END
```

### Silme aslında nasıl yapılıyor
Silme = **FCQ lojik opcode** `0x44/0x4C/0x50/0x58` (descriptor+4'e yazılır, subA ile FCQ
ring word0[13:0]'a girer). ONFI 60h/D0h/70h dizisini FCQ donanım sequencer'ı
(`0x06600000`) silikonda üretir. Kanıt: (a) imajda opcode→rutin çeviren bir tablo yok
(ANALIZ_DESC T3), (b) okuma da aynı FCQ yolundan (opcode 0xB0) çalışıyor, (c) die
gerçek bir erase-fail statüsü (`0xE1`) döndürüyor — bu ancak die'a geçerli bir 60h-D0h
ulaştıysa üretilir. Yani **die dizisi doğru gidiyor.** [INFER, güçlü]

`c1.bin`'de bNifcCmdMap/wNopsCmdMap (lojik→rutin) tabloları yok; nops (B) tablosu
`0x06650000`'e yüklenir ama onun `+6` rutin alanlarının işaret ettiği rutinlerin
hiçbiri de 60h/D0h üretmiyor (yukarıdaki komut kümesi tüm rutinleri kapsıyor).

---

## 3. Row (satır) adresi hesabı

Host `rowfield`'i **u16 BE** yollar; anlamı `rowfield = blok × PLN_QNTY + plane`
(geo[9]=PLN_QNTY). Firmware:
* `blok  = rowfield / PLN_QNTY`, `plane = rowfield mod PLN_QNTY` (program: `0x040C3EC8`
  `blx 0x040ED2B2` udivmod; silme benzer).
* Fiziksel NAND row'u `0x040C8EC4` **bit-shift'lerle** kurar — **1536/2732/16384 gibi bir
  çarpan KULLANILMAZ.** [READ] (`0x040C8EC4`):

```
r4 = addr[7:0]                          ; CE/plane composite düşük
r3 = addr[15:8]                         ; bank/plane
r5 = addr[31:16]                        ; blok
r6 = col (2. arg = page/kolon)
STPU = geo[0x1F](=7) ; PLANE = c0[0x9255](=2) ; PAGE = geo[0x1D](=12) ; LUN = c0[0x9244]
row =  addr[7:0]
    | (addr[15:8]  << (STPU-3      = 4))
    | (addr[31:16] << (3+STPU-1    = 9))          ; <-- BLOK alanı, bit 9
    | (col         << (PAGE+3+STPU-1 = 21))       ; <-- PAGE/kolon alanı, bit 21
```
(LUN_SHIFT `c0[0x9244]` bu shift'lerde sadeleşir; asıl CE/LUN hedefi descriptor'ın
`+0x10/+0x11/+0x12` alanlarına gider — row'a değil.)

* **plane** row'a `ROW_PLANE_SHIFT = geo[0x1B] = 2` ve düşük composite üzerinden girer.
* **LUN biti VAR**: `ROW_LUN_SHIFT = geo[0x1A] = 1`. Ama bu die 1 LUN olduğu için değeri 0.
* Sabitler kodda **shift** olarak duruyor (geo yapısı, aşağıda): ROW_BLOCK_SHIFT=11,
  ROW_PAGE_SHIFT=12, ROW_PLANE_SHIFT=2, ROW_LUN_SHIFT=1, STPU_SHIFT=7.
  `1536/2732/16384` **row çarpanı olarak geçmez**; blok/sayfa SAYILARI geo yapısında u16.

**Sonuç (kritik):** blok 0, plane 0 → tüm shift'ler `0<<n = 0` → **row = 0**. Silme
blok 0'ı NAND row 0'a yollar; geometri ne olursa olsun. Bu yüzden geometri uyuşmazlığı
blok-0 silme FAIL'ini açıklamaz.

---

## 4. NAND geometri yapısı — bellekte yeri, içeriği, uyum kontrolü

Geo pointer `*(u32*)0x00000DCC = 0x000004E0` (statik). Yapı **c0.bin @ `0x4E0`'da gerçek
varsayılan veriyle** duruyor (BSS değil). Banner yazıcısı `0x040C0308` alan adlarını verir.

Statik `0x4E0` dökümü + çözüm [READ]:
```
+0x00: 02 02 8c 0b 00 03 10 00 01 02 01 03 08 04 a0 07
+0x10: 03 00 00 01 01 00 00 00 0b 0c 01 02 01 0c 09 07
```
| offset | alan (banner) | statik değer | GERÇEK die (H25BFT8D4B8R) | uyum |
|---|---|---|---|---|
| +0x02 u16 | **BLOCK_QNTY** | `0x0B8C` = **2956** | **2732** (0xAAC) | ❌ **UYUŞMUYOR** |
| +0x04 u16 | **PAGE_QNTY** | `0x0300` = **768** | 1536 (ya da 384×4) | ❌ **UYUŞMUYOR** |
| +0x06 u16 | PAGE_SIZE tabanı | `0x10`=16 → 16384 | 16384 | ✔ |
| +0x0E u16 | spare bayt | `0x07A0` = **1952** | **2048** (0x800) | ❌ **UYUŞMUYOR** |
| +0x09 | PLN_QNTY | 2 | 2 plane | ✔ (canlıda 4 gözlendiği iddiası ANALIZ_TAMSAYFA'da) |
| +0x18 | ROW_BLOCK_SHIFT | 0x0B=11 | — | shift |
| +0x19 | ROW_PAGE_SHIFT | 0x0C=12 | — | shift |
| +0x1A | ROW_LUN_SHIFT | 0x01=1 | 1 LUN | ✔ |
| +0x1B | ROW_PLANE_SHIFT | 0x02=2 | — | shift |
| +0x1D | PAGE_SHIFT | 0x0C=12 | — | shift |
| +0x1E | BLOCK_SHIFT | 0x09=9 | — | shift |
| +0x1F | STPU_SHIFT | 0x07=7 | — | shift |

**⚠️ Uyuşmayan alanlar (kritik olarak işaretle):** BLOCK_QNTY (2956≠2732), PAGE_QNTY
(768≠1536), spare (1952≠2048). BUNLAR STATİK VARSAYILAN — canlı geo, boot'taki flash-ID
eşleşmesiyle doldurulur. Ama görevdeki gerçek die **H25BFT8D4B8R-BDJ**; ANALIZ_TAMSAYFA'nın
eşleştirdiği FPT girişi **H25BFT8A1BDA** (ID `AD 7E 28 53 02 B0`, 2888 blok) — **farklı bir
parça**. Yani GDP bu die'ı yanlış eşleştirip yanlış geometriyle çalışıyor olabilir.
Bu, **adresleme doğruluğu** için kritik (yüksek bloklara erişim bozulur) AMA blok-0 silme
FAIL'ini açıklamaz (§3). Canlı değerleri poke ederek doğrulanmalı: `*(0x0DCC)` → yapı,
`c0[0x9244]/[0x9255]/[0x924A]` runtime'da 0xAA (statik) — canlıda okunmalı.

---

## 5. WP / read-only / factory / locked / secure bayrağı var mı? — HAYIR

* `0x8B` handler (`0x040C3C90`), silme çekirdeği (`0x040D0DB8`), sequencer'lar
  (`0x040DDC24`/`0x040DDDD0`) ve subA (`0x040E3D48`) — **hiçbirinde** write-protect /
  read-only / factory / locked / secure bayrağı okuması YOK. [READ]
* İmaj genelinde string taraması: "write protect", "readonly", "locked", "secure",
  "vpp", "charge pump" **yok**. Sadece `f_Power_On`, `l_power_on_flow fail`,
  `factory_mark_*` (bad-block factory işaretleri — silme kapısı değil) var.
* Handler erken dönmüyor; gerçekten die'a komut gönderiyor (§1.6 doorbell).
* Silmeyi yöneten runtime bayrakları sadece **davranış** seçer, **kilit** değil:
  `c0[0x9247]` (sequencer seçimi), `c0[0x924A]` (SLC-mode), `c0[0x9262]==3` (0xD0→0x3A),
  `c0[0x9264]` (data-out opcode — silmeyi etkilemez).
* Die'ın kendi status'u zaten `0xE0` = bit7 (WP#)=1 **yazma serbest** diyor; ardından
  `0xE1` = bit0 FAIL. Yani kilit die tarafında da bildirilmiyor — die komutu kabul edip
  silmeyi gerçekten başaramıyor.

---

## 6. Silmeden önce GPIO / PMIC / güç / vpp / charge-pump açılıyor mu? — HAYIR

* Silme yolundaki hiçbir fonksiyon `0x0600D000` (GPIO) ya da başka bir güç register'ına
  yazmıyor. Silme sadece FCQ (`0x06600000`) + FCQ ring SRAM'e dokunur. [READ]
* `0x0600D000` literal'i imajda 5 yerde: `0x040CB3DC, 0x040CF2DC, 0x040CFBC0, 0x040E0AB4,
  0x040E5EC8` — hiçbiri silme çağrı grafiğinde değil.
* `0x0600xxxx` aperture'ünde başka bloklar var (`0x06000500` 14 ref, `0x06003000` 6 ref)
  ama silme bunlara da dokunmaz; büyük ihtimalle init/PHY/clock. [INFER]
* Sonuç: silme, güç/WP'nin init'te kurulmuş olduğunu varsayar; kendisi vpp/charge-pump
  açmaz. NAND erase gerilimi zaten **die içi charge-pump** ile Vcc'den üretilir — firmware
  register'ı değil. 16/16 die'ın tıpatıp aynı FAIL'i, **paylaşılan bir güç rayı / erase
  yüksek-gerilim sorunu** ile birebir uyumlu. [INFER, orta-güçlü]

---

## 7. Silmeyi açmak için denenebilecek somut yama listesi (HEPSİ TEST EDİLMEDİ — hipotez)

> Dürüstlük notu: aşağıdakiler statik analizden çıkan *adaylar*. Hiçbiri donanımda
> koşturulmadı. Kök neden en olası olarak fiziksel (erase yüksek-gerilim / charge-pump
> ya da die block-lock) — firmware yaması bunu **aşamayabilir**. Sırayla, ucuzdan pahalıya:

| # | yama (adres = değer) | gerekçe | öncelik |
|---|---|---|---|
| P1 | **Ölç, yama değil:** canlıda `*(u8)c0[0x924A]`, `*(u8)c0[0x9247]`, `*(u8)c0[0x9244]`, `*(u8)c0[0x9255]` ve geo (`*(0x0DCC)`, 0x20 bayt) oku. | Statikte hepsi 0xAA/varsayılan; silme davranışı bunlara bağlı. Yamadan önce gerçek değerler şart. | **ÖNCE BU** |
| P2 | `c0[0x924A] = 0` (SLC bayrağını kapat) | Silme her seferinde 0xBA+0xD0 SLC set-feature yapıyor; die yanlış array-mode'da siliniyorsa TLC/normal moda zorla. (Okuma da bunu yapıp çalışıyor → zayıf ama ucuz.) | orta |
| P3 | `c0[0x9247]` değerini ters çevir (0↔1) | `0x040DDC24` ↔ `0x040DDDD0`: iki farklı silme sequencer'ı. Diğerini dene. | orta |
| P4 | geo yapısını gerçek die'a göre poke: `*(u16)(*(0x0DCC)+0x02)=0x0AAC` (2732 blok), `*(u16)(*(0x0DCC)+0x0E)=0x0800` (2048 spare), PAGE_QNTY'yi ölçüp düzelt | GDP yanlış parça (A1BDA) eşleştirmiş olabilir; yüksek blok/adres doğruluğu için. Blok-0 için gereksiz. | adresleme için yüksek, silme-fail için düşük |
| P5 | Silme ön-hazırlığındaki 0xD0 set-feature'ı atla: `0x040DDC90`/`0x040DDCA0`'daki `bl 0x040DD850`/`0x040DDA70`'i NOP'la (ya da içine `mov r0,#1;bx lr`) | Herhangi bir mod-değişim yan etkisini ele. (Okuma da bunu yapıp çalışıyor → zayıf.) | düşük |
| P6 | **Özel mikrokod: ONFI block-unlock + erase.** Boş slota (örn. rutin `0xD0` = `0x06649000+0xD0*0x10 = 0x06649D00`) `23h`/`24h`/`2Ah` (BLOCK UNLOCK) yayınlayan bir rutin yaz (ANALIZ_NIFC §2.7 boş-slot mekanizması), `0x040CFF08` dinamik launcher ile (`*(u16)0x9934`=slot) çalıştır; sonra sil. | Firmware'de standart unlock rutini YOK (60h/D0h gibi 23h/24h da yok). Die power-on'da bloklar kilitli açıldıysa (okuma OK, erase/prog FAIL, die "hazır") tek firmware yolu bu. | die-kilit hipotezi doğruysa yüksek; SPEKÜLATİF |
| P7 | **Donanım (firmware değil):** silme yükü altında NAND Vcc/Vccq'yı ve erase yüksek-gerilimini ölç. Die gerçek FAIL dönüyor; firmware bunu geçersiz kılamaz. | §0.3, §6: 16/16 tıpatıp FAIL + okuma OK + die "hazır" = charge-pump/güç ya da die-kilit imzası. | **gerçek kök neden en olası burada** |

Erişim primitifleri: bellek poke için ANALIZ_NVME/TAMSAYFA'daki `0xC1/0xC2` (MAGIC
`0x001234xx`) yolu; bare-metal doğrulama için `0x040E384C` (RESET rutin 2) ve
`0x040E4630` (READ ID) die'ın FCQ'dan bağımsız cevap verdiğini kontrol eder.

---

## Ek — bu çalışmada üretilen yeni adresler
* `0x040D0DB8` — çok-die silme çekirdeği (0x8B handler'dan)
* `0x040DDF74` — silme yayın dağıtıcısı (`c0[0x9247]` ile 0x040DDC24/0x040DDDD0)
* `0x040DDC24` / `0x040DDDD0` — iki silme sequencer'ı
* `0x040DD5FC` — asıl BLOCK ERASE yayıncısı; opcode tablosu `0x040EE7A8` = {44,4C,50,58}
* `0x040DC454` (0x42 check-ready), `0x040DD850`/`0x040DDA70` (0xD0 set-feature),
  `0x040DC50C` (0xBA SLC prefix)
* `0x040C8EC4` — row adres paketleyici (shift tabanlı, §3)
* geo yapısı: `*(0x0DCC)=0x4E0`, alan haritası §4 (banner `0x040C0308`)
