# HYV7 GDP uyarlamasi — V8 sabitlerinin HYV7 karsiliklari

**Tarih:** 2026-09-16 · **Yontem:** tamamen cevrimdisi ikili analiz (cihaza hic komut gitmedi).

| | V8 (su an kullanilan) | HYV7 (hedef) |
|---|---|---|
| imza | `MKGDP_000001013148030000, Nov 5 2024` | `MKGDP_000001006091730000, May 31 2022` |
| GDP.bin | 249856 B | 233472 B |
| c0 | ofs 0x1000, adr 0x00000000, boy 0xC000 | ayni |
| c1 | ofs 0xD000, adr 0x040C0000, boy **0x30000** (bitis 0x040F0000) | ofs 0xD000, adr 0x040C0000, boy **0x2C000** (bitis 0x040EC000) |
| dagitim tablosu | 0x040ED2F4, **36** girdi | 0x040E7398, **27** girdi |

Dosyalar: `re/gdp/c0.bin`+`c1.bin` (V8), `re/gdp_hyv7/c0.bin`+`c1.bin` (HYV7).

---

## 0. En onemli iki bulgu (once bunlar)

### 0.1 `chunk0` KODU iki surumde birebir ayni
`c0.bin` (48 KB) dosyalari yalnizca **265 baytta** farkli ve farklarin hepsi
`0x160-0x1EC`, `0x2C0-0x2CF`, `0xDB0-0xF1C` **veri** araliklarinda. `0x1000-0xC000`
arasi **bayt bayt ayni**. Sonuclari:

* LDPC matris alani (`ldpc_yaz()` -> `0x00001000` ve `0x00003928`) **degismedi**.
* TMC tablosu (`0x00000200`) ve kopyasi (`0x00000590`) **degismedi**
  (`02 02 c8 00 7c 02 46 06` deseni iki imajda da ayni iki adreste).
* Exception vektor tablosu (`0x20..0x38`) degismedi; isleyici adresleri
  `0x040C013C/0140/0144/0148/012C/011C` **iki imajda da ayni**.

### 0.2 `0x86`/`0x87`/`0x84` GDP komutu DEGIL, boot ROM komutu — HYV7'de de calisir
HYV7 dagitim tablosunda `0x00`, `0x84`, `0x86` **yok**. Bu, RAM peek/poke'un
oldugu anlamina **gelmiyor**:

* `cmp #0x84/#0x86/#0x87` iki imajin **hicbirinde** yok (c0 Thumb + c1 ARM tarandi).
* `ANALIZ_MPTOOL.md §2`: `VC_LDR_CmdGetReg 0x84`, `VC_LDR_CmdReadRam 0x86`,
  `VC_LDR_CmdWriteRam 0x87` — hepsi **LDR (loader/ROM)** komutu.
* V8 GDP'sinin kendi `0x86` isleyicisi `"READ RAM ADDR:[%08X]"` basiyor. Log
  kancasi takiliyken binlerce `rd()` yapildi ve bu dizgi RAPOR'daki hicbir
  firmware logunda **gecmiyor** -> istegi GDP degil ROM karsiliyor.

=> `poke_blok`, `peek`, `reg()` HYV7 GDP'siyle de calisir. **Kesin degil ama
kanit guclu**; ilk canli adim yine de tek bir `jd_hack.py peek 0x040C0000` olmali.

---

## 1. Sabit esleme tablosu

| sabit | V8 | HYV7 | guven | esleme kaniti |
|---|---|---|---|---|
| `C1` taban/boy | 0x040C0000 / 0x30000 | 0x040C0000 / **0x2C000** | kesin | GDP basligi `0x74+i*0x10` |
| `STUBA` | 0x040FF100 | **degismedi** | kesin | §2 |
| `KAZI` | 0x040FF200 | **degismedi** | kesin | §2 |
| `STUB` (kod) | 19 kelime | **bayt bayt ayni** | kesin | §2 |
| `TRAMP` | 0x040FF000 | **degismedi** | kesin | §2 |
| `LOGBASE`/`LOGDATA` | 0x040F0000 / +0x10 | **degismedi** | kesin | §2 |
| `CMDTBL` | 0x040ED2F4 (36) | **0x040E7398 (27)** | kesin | §3 |
| CMDTBL girdi#2 `+4` | 0x040ED30C | **0x040E73B4** | kesin | §3 |
| `NIFC` | 0x06641000 | **degismedi** | kesin | §4 |
| `FCQ` | 0x06600000 | **degismedi** | kesin | §4 |
| `MOD_SEC` | 0x040E38EC | **0x040DD6D8** | kesin | §5 |
| `F_MOD` | 0x040E2B48 | **0x040DC910** | kesin | §5 |
| `F_NRST` | 0x040E3898 | **0x040DD684** | kesin | §5 |
| `F_POLL` | 0x040E3600 | **0x040DD3EC** | kesin | §5 |
| `F_SETP` | 0x040E37E8 | **0x040DD5D4** | kesin | §5 |
| FWCQ poll timeout (`cekirdek.py`) | 0x040DBD44 | **0x040D5FB4** | kesin | §6 |
| `YAMA_ADR[0]` (DDR kurulumu) | 0x040C8B3C | **0x040C6C18** | kesin | §7.1 |
| `YAMA_ADR[1]` (LDPC tuzagi) | 0x040C8D8C | **KARSILIGI YOK** | kesin | §7.2 |
| `YAMA_ADR[2]` (LDPC tuzagi) | 0x040C8D90 | **KARSILIGI YOK** | kesin | §7.2 |
| `YAMA_ADR[3]` (NAND saati) | 0x040C3328 | **0x040C2AEC** | kesin | §7.3 |
| `YAMA_ADR[4..6]` (GET FEATURE) | 0x040E3474/78/7C | **0x040DD26C/70/74** | kesin | §7.4 |
| SDR/legacy alt rutin (`bl` hedefi) | 0x040E305C | **0x040DCE88** | kesin | §7.1 |
| DDR/toggle alt rutin | 0x040E3070 | **0x040DCE9C** | kesin | §7.1 |
| TMC tablosu | RAM 0x200 | **degismedi** | kesin | §8 |
| LDPC dec / enc hedefi | 0x00001000 / 0x00003928 | **degismedi** | kesin | §0.1 |
| `putc` (log kancasi) | 0x040CF6E0 | **0x040CC09C** | kesin | §9 |
| `printf` | 0x040CF704 | **0x040CC0C0** | kesin | §9 |
| `memcpy` | 0x040E854C | **0x040E23F8** | kesin | §5 |
| ASSERT spin bayragi | 0x00000E58 | **0x00000E32** | kesin | §10 |
| 0xE4/0xE1 NAND komut secici | 0x00000E6E | **0x00000E46** | kesin | §10 |
| GET/SET FEATURE yapisi | 0x00000E7C | **0x00000E54** | kesin | §10 |
| geometri isaretcisi (`jdisk.GEOM_PTR`) | 0x00000DCC | **0x00000DC4** | kesin | §11 |
| komut durum yapisi | 0x00009210 | **0x000091BA** | kesin | §3 |
| isleyici durum bayti (`getreturn`) | 0x00009227 | **0x000091D1** | kesin | §3 |
| die/ce sayaci global | 0x00009244 | **0x000091D4** | kesin | §5 |
| `LAND` (host->cihaz payload) | 0x0400F2C0 | **0x0400F8C0** | kesin | §11 |
| cihaz->host veri tamponu | 0x040612C0 | **0x040618C0** | kesin | §11 |
| `STAG` (ara tampon) | 0x04074EC0 | **0x040754C0** | **olasi** | §11 |

---

## 2. STUBA / KAZI / LOGBASE / STUB — **degistirilmedi** (kasitli)

Iki imajda da **imaj sonunun ustune tek bir referans yok**: c1 icindeki tum
32-bit kelimeler `0x04000000-0x04200000` araliginda tarandi, `>= imaj sonu` olan
**0 adet**. Yani GDP'nin BSS/heap/stack'i imajin ICINDE; `0x040F0000` ustu bos.

* V8 imaji `0x040F0000`'de bitiyor, HYV7 `0x040EC000`'de -> HYV7'de **daha cok**
  bos alan var, V8 adresleri hala imajin disinda.
* `0x040F0000` / `0x040FF000` / `0x040FF100` / `0x040FF200` V8 ile fiilen
  yazilip geri okundu (RAPOR §45.1) -> o SRAM fiziksel olarak var.
* `STUB` tamamen konum bagimsiz (tek mutlak deger sondaki `KAZI` literal'i,
  `ldr r4,[pc,#0x3c]`). `STUBA`/`KAZI` degismedigi icin **bayt dizisi ayni**.
* Tek not: c0'da `0x040FA68C` degerini tasiyan bir literal var (`c0+0x6a88`,
  iki imajda da ayni). Bu adres `LOGBASE+LOGSIZE` (0x040F7000) ile `TRAMP`
  (0x040FF000) arasinda kaliyor — bizim kullandigimiz uc noktaya degmiyor.

---

## 3. `CMDTBL` = **0x040E7398**, 27 girdi

Tablo bicimi: 12 bayt/girdi = `op, yon, 0, 0, u32 isleyici, 4 bayrak baytı`.
`yon`: 0 = veri yok, 1 = host->cihaz, 2 = cihaz->host.

Bulus yontemi: ardisik 12 baytlik kayit taramasi (girdi `+4`'u imaj icine isaret
eden hizali isaretci, `+2`/`+3` sifir). Iki imajda da **tek** aday cikti.
Dogrulama: dispatcher dongusu

```
V8    0x040C66B4  add r2,r4,r4,lsl #1 ; ldrb r2,[r1,r2,lsl #2] ; cmp r2,r0
      0x040C66CC  cmp r4, #0x24          <-- 36 girdi
HYV7  0x040C5448  add r2,r4,r4,lsl #1 ; ldrb r2,[r1,r2,lsl #2] ; cmp r2,r0
      0x040C5460  cmp r4, #0x1b          <-- 27 girdi
```
ve tabloyu yukleyen tek literal: V8 `0x040C686C`, HYV7 `0x040C55CC = 0x040E7398`.

Tablonun basi (HYV7 `0x040E7398`): `3b 02 00 00 | 24 2c 0c 04 | 00 00 00 00`,
girdi #2 `0x040E73B0`: `02 00 00 00 | 78 31 0c 04 | 01 00 01 00`
-> `stub_kur()` yazacagi alan **`0x040E73B4`**.

### 3.1 Opcode farklari (kritik)

| op | V8 | HYV7 |
|---|---|---|
| `0x00` GetReturn | yon 2, `0x040C5830` | **YOK** |
| `0x49` SwitchToLegacy / nand_init | **yon 2** | **yon 0** |
| `0x57`,`0x58`,`0x5A`,`0x5B`,`0xE1`,`0xE4` | var | **YOK** |
| `0x84`,`0x86` | var (ROM'da da var) | **YOK** (ROM'da var, §0.2) |
| diger 25 opcode | — | **yon ve payload alanlari birebir ayni** |

`0x49`'un yonu MPTool tablosundaki orijinaline (`VC_GDP_CmdSwitchToLegacy ... –`)
donmus; veri-in fazini 2024 surumu eklemis.

### 3.2 `getreturn()` yerine RAM peek
Dispatcher her iki surumde de isleyici durum baytini `[durum_yapisi + 0x17]`'e
yaziyor (`mov r1,#0xaa ; strb r1,[r4,#0x17]` -> V8 `0x040C67A0`, HYV7 `0x040C5534`).
Yapi adresi dispatcher literal'inden: V8 `0x00009210`, HYV7 `0x000091BA`.
=> HYV7'de `getreturn()` = `peek(0x000091D1, 1)`.

---

## 4. `NIFC` / `FCQ` — degismedi

`F_MOD`'un literal havuzu: V8 `0x040E2EE0 = 0x06641000`, HYV7 `0x040DCB30 = 0x06641000`.
Legacy zamanlama sabiti de ayni: V8 `0x040E2F18 = 0x02020202`, HYV7 `0x040DCB68 = 0x02020202`.
`FCQ` icin HYV7'de `0x040D1FA8: mov r1, #0x6600000`.

---

## 5. `MOD_SEC` / `F_MOD` / `F_NRST` / `F_POLL` / `F_SETP`

`F_NRST`/`F_POLL`/`F_SETP` maskeli (dal ofsetleri + `[pc,#imm]` maskelenmis)
16 komutluk imza ile **tek** eslesme verdi; ucu de ayni `-0x6214` kaymasinda:

```
V8 0x040E3898 -> HYV7 0x040DD684   (F_NRST)
V8 0x040E3600 -> HYV7 0x040DD3EC   (F_POLL)
V8 0x040E37E8 -> HYV7 0x040DD5D4   (F_SETP)
```
Ucunun de ilk literal'i die sayaci globali: V8 `0x9244`, HYV7 `0x91D4`.

`MOD_SEC` = `0x040E38EC + (-0x6214)` = **0x040DD6D8**, disasm ile dogrulandi —
cagri dizisi V8 ile birebir:

```
HYV7 040dd6d8  mov  r0, #1
     040dd6dc  bl   0x040DC910      <-- F_MOD
     040dd6e0  ldr r1,[pc,#0x194] ; movw r2,#0x900 ; ldr r0,[pc,#0x190]
     040dd6ec  bl   0x040E23F8      <-- memcpy  (V8: 0x040E854C)
     040dd6f0  bl   0x040DD684      <-- F_NRST
     040dd6f4  ldr r1,... ; movw r2,#0x328 ; ldr r0,...
     040dd700  bl   0x040E23F8
     040dd704  bl   0x040DD3EC      <-- F_POLL
     040dd708  bl   0x040DD5D4      <-- F_SETP
```

`F_MOD` maskeli imzayla **eslesmedi** (register tahsisi degismis: V8
`push {r4,r5,r6,r7,lr}`, HYV7 `push {r4..fp,lr}`), ama `MOD_SEC`'in ilk
`bl` hedefi zaten adresi veriyor: **0x040DC910**. Govde semantik olarak ayni:

```
V8   040e2b68  ldr r4,[r1,#0x204] ; bfi r4,r0,#0,#1 ; str r4,[r1,#0x204]
               ldr r4,[r1,#0x34]  ; cmp r0,#0 ; orreq/bicne #0x10000 ; str
               str r6,[r1,#0x200]                          (r6 = 0x02020202)
HYV7 040dc934  ldr r0,[r1,#0x204] ; bfi r0,r6,#0,#1 ; str r0,[r1,#0x204]
               ldr r0,[r1,#0x34]  ; cmp r6,#0 ; orreq/bicne #0x10000 ; str
               str r8,[r1,#0x200]                          (r8 = 0x02020202)
```
`legacy_yama()` yine `MOD_SEC`'e `mov r0,#0/#1` (`E3A00000`/`E3A00001`) yaziyor.

---

## 6. FWCQ poll timeout = **0x040D5FB4**

`"[%s]poll fwcq timeout\r\n"` dizgisi iki imajda da **tek**:
V8 `0x040DBD50`, HYV7 `0x040D5FC0`. Hemen oncesindeki literal havuzu birebir
ayni duzende:

```
V8   040dbd38  40 e1 00 04 | 00 c9 00 04 | 44 92 00 00 | 00 e1 f5 05 | 38 e7 0e 04 | "[%s]poll fwc...
HYV7 040d5fa8  40 e7 00 04 | 00 c9 00 04 | d4 91 00 00 | 00 e1 f5 05 | 04 7b 0e 04 | "[%s]poll fwc...
                                                          ^^^^^^^^^^^ 0x05F5E100 = 100_000_000
```
`0x05F5E100` iki imajda da **tek** yerde geciyor (V8 `0x040DBD44`, HYV7 `0x040D5FB4`)
ve **her ikisinde de 5 ayri `ldr` bu literal'i kullaniyor** (V8: 0x040DBAE0,
0x040DBD08, 0x040DC168, 0x040DC404, 0x040DC7C4 — HYV7: 0x040D5D48, 0x040D5F78,
0x040D6354, 0x040D664C, 0x040D6A00). Yapisal esleme tam.

=> `cekirdek.py`'deki `poke_blok(0x040DBD44, poll)` -> **`poke_blok(0x040D5FB4, poll)`**
(`ortak_hyv7.POLLVAR` olarak disa aciliyor).

---

## 7. `YAMA_ADR` — 5'i eslesti, 2'sinin karsiligi YOK

`init()` bu adreslere **orijinal** baytlari geri yaziyor (eski deneylerin
"KAZANAN" yamalarini geri almak icin). Taze yuklenmis GDP'de etkisiz ama
uyumluluk icin esledim.

### 7.1 `0x040C8B3C` -> **0x040C6C18**
Dizgi capasi: `"No TimingMode or IF need to setf for SAMSUNG\r"` (V8 `0x040C8C58`,
HYV7 `0x040C6DC0`), her ikisinde de **tek** pc-goreli referans:

```
V8   040c8b30  add r0,pc,#0x120   ; "No TimingMode..."
     040c8b34  blx 0x040CF704     ; printf
     040c8b38  ldr r0,[sp,#8]
     040c8b3c  bl  0x040E3070     <-- YAMA_ADR[0]
HYV7 040c6c0c  add r0,pc,#0x1ac   ; "No TimingMode..."
     040c6c10  blx 0x040CC0C0     ; printf
     040c6c14  mov r0,r6
     040c6c18  bl  0x040DCE9C     <-- karsilik
```
`0x040E3070` <-> `0x040DCE9C` ayrica govde ile dogrulandi (ikisi de
`bl <ayni alt rutin> ; mov r0,#1 ; b F_MOD`). Bir onceki fonksiyon da esliyor:
`0x040E305C` <-> `0x040DCE88` = ayni sey ama `mov r0,#0` (SDR/legacy).
=> V8'in "KAZANAN" yamasi `0x040C8B3C = bl 0x040E305C` -> HYV7'de
`0x040C6C18 = bl 0x040DCE88` (bayt: `9a 58 00 eb`; imajdaki orijinal `9f 58 00 eb` = `bl 0x040DCE9C`).
Kodlayici V8'in belgelenmis `466900eb` degerini birebir uretiyor, yani dogrulandi.

### 7.2 `0x040C8D8C` / `0x040C8D90` — **HYV7'de karsiligi YOK**
Bunlar V8'in "LDPC-rate tuzagi"ni atliyordu. HYV7 imajinda o kontrol hic yok:

* `"ldpc rate mismatch between MPT[ %d ] and HW[ %d ]"`, `"No matched ldpc rate"`,
  `"LDPC matrix check fail"` dizgileri **sadece V8'de** (tam dizgi diff'i yapildi:
  ortak 483, V8'e ozel 165, HYV7'ye ozel 25 dizgi).
* Fonksiyon HYV7'de erken bitiyor:
```
V8   040c8d78  cmp r0,#0x320 ; movhs r0,#1 ; blhs 0x040E2788
     040c8d84  ldr r0,[sp,#8] ; bl 0x040C86E8
     040c8d8c  ldr r0,[r8]          <-- yama 1
     040c8d90  ldrh r1,[r0,#0xe]    <-- yama 2   (LDPC rate kontrolu)
     ...       040c8dd0 / 040c8ddc  `b .` tuzaklari
HYV7 040c6d20  cmp r6,#0x320 ; movhs r0,#1 ; blhs 0x040DC550
     040c6d2c  mov r0,r4
     040c6d30  pop {r4-r8,pc}       <-- fonksiyon BITIYOR
```
`ortak_hyv7.py`'de bu iki adres listeye konmadi (uydurma adres yazmamak icin).

### 7.3 `0x040C3328` -> **0x040C2AEC**
`mov r1,#0xc8` (`E3A010C8`) V8 imajinda **tek**; HYV7'de iki yerde ama biri
alakasiz (`bfi/blx` baglami). Dogru olan 5 komutluk diziyle birebir esliyor:

```
V8   040c3324  ldrb r0,[r5] ; mov r1,#0xc8 ; bl 0x040C89BC ; and r0,r0,#1 ; cmp r0,#1
HYV7 040c2ae8  ldrb r0,[r6] ; mov r1,#0xc8 ; bl 0x040C6B74 ; and r0,r0,#1 ; cmp r0,#1
```

### 7.4 `0x040E3474/78/7C` -> **0x040DD26C/70/74**
Maskeli pencere eslemesi (tek aday) + disasm:

```
V8   040e3464  ldr r1,[r0,#0x21c] ; tst r1,#1 ; beq -8 ; ldr r1,[r0,#0x240]
     040e3474  str r1,[r5] ; ldr r0,[r0,#0x218] ; and r0,r0,#0xff ; pop {r4,r5,r6,pc}
HYV7 040dd25c  ldr r1,[r0,#0x21c] ; tst r1,#1 ; beq -8 ; ldr r1,[r0,#0x240]
     040dd26c  str r1,[r5] ; ldr r0,[r0,#0x218] ; and r0,r0,#0xff ; pop {r4,r5,r6,pc}
```

---

## 8. TMC (`RAM 0x200`) — taban ve ofsetler ayni, 4 alan **olu**

* `0x200..0x3FF` iki c0 imajinda sadece `0xC0-0xCF` araliginda farkli.
* `02 02 c8 00 7c 02 46 06` deseni iki imajda da `0x200` ve `0x590`'da.
* `0x49` isleyicisinin okudugu alanlar birebir ayni:
```
V8   040c31dc  ldrb r0,[r5,#6]  -> [yapi+4]     (ODS)
     040c31e4  ldrb r0,[r5,#5]  -> [yapi+0x10]  (HSS)
     040c31f4  ldrb r0,[r5,#4]  -> [yapi+0x1c]  (timing)
     040c3228  ldr  r1,[r5,#0xd4] -> [yapi+0x10]
HYV7 040c29c0  ldrb r0,[r6,#6]  -> [yapi+4]
     040c29c8  ldrb r0,[r6,#5]  -> [yapi+0x10]
     040c29d8  ldrb r0,[r6,#4]  -> [yapi+0x1c]
     040c2a08  ldr  r2,[r6,#0xd4] -> [yapi+0x10]
```
* **Taban-izli tam tarama** (0x200 literal'ini yukleyen her register izlendi):
  * V8 okunan ofsetler: `00 02 04 05 06 08 0A 0C 0D B4 B6 B8 BA C0 C2 C4 C6 C8 CA CC CE D0 D2 D4`
  * HYV7 okunan ofsetler: `00 02 04 05 06 08 0C 0D D0 D2 D4`
* => `tmc_yaz()`'in yazdigi `0xB4/0xB6/0xB8/0xBA` (nops_tmr_un0..3) HYV7'de
  **hic okunmuyor** (`ldrh [x,#0xb4]` HYV7'de yok; V8'de tek yer: `0x040E2C48`).
  `0xBF` ve `0xD8` **iki imajda da** okunmuyor. Bu yazmalar zararsiz ama etkisiz.
  `0x00`, `0x05`, `0x06`, `0xD4` gecerli ve degismedi.

---

## 9. `putc` (log kancasi) = **0x040CC09C**

Ayni 12 bayt (`44 49 0a 7d 92 06 fc d5 08 70 70 47`) iki imajda da **tek** yerde:
V8 `0x040CF6E0`, HYV7 `0x040CC09C` — **literal ofseti dahil birebir ayni**.
UART taban adresi de ayni: V8 `lit@0x040CF7F4 = 0x06007000`,
HYV7 `lit@0x040CC1B0 = 0x06007000`. `printf` her ikisinde de `putc + 0x24`
(V8 `0x040CF704`, HYV7 `0x040CC0C0`).

`TRAMP`/`LOGBASE` degismedigi icin `jd_hack.HOOK_ASM`'in derlenmis hali de ayni;
`kampanya/hazirla_hyv7.py` onu `jd_hack.derle()` ile ayni sekilde uretiyor.

---

## 10. ASSERT silahsizlandirma: `0x0E58 -> 0x0E32`, `0x0E6E -> 0x0E46`

**ASSERT bayragi.** ASSERT govdesi: `printf(...) ; while (*(u8*)FLAG) ;`
Kod deseninden (`ldr r0,[pc,#0xe0] ; ldrb r1,[r0] ; cmp r1,#0 ; bne -4`) tum
ASSERT noktalari tarandi:

```
V8   6 nokta (0x040CB350, 0x040CDE18, 0x040CDFA8, 0x040CF440, 0x040CFDFC, 0x040E3044) -> hepsi 0x00000E58
HYV7 5 nokta (0x040C8C2C, 0x040CB7F0, 0x040CB980, 0x040CBEF4, 0x040DCE70)             -> hepsi 0x00000E32
```
Imajdaki deger iki tarafta da `0x01` (silahli). Guven: **kesin** (adres koddan,
veri hizalamasindan tahmin degil).

**0xE4/0xE1 secici.** `moveq r1,#0xe4` (`03A010E4`) iki imajda da **tek**:

```
V8   040dbd90  ldr r1,[pc,#0x2ec]  -> lit = 0x00000E6E
     040dbd94  ldrb r1,[r1] ; cmp r1,#0 ; moveq r1,#0xe4 ; cmp r1,#1 ; moveq r1,#0xe1
HYV7 040d6000  ldr r1,[pc,#0x374]  -> lit = 0x00000E46
     040d6004  ldrb r1,[r1] ; cmp r1,#0 ; moveq r1,#0xe4 ; cmp r1,#1 ; moveq r1,#0xe1
```
Imajdaki deger iki tarafta da `0xFF`. Guven: **kesin**.

**GET/SET FEATURE yapisi** (RAPOR §44.5'teki "RAM 0x00000E7C"): `0x49`
isleyicisinin literal'i — V8 `0x00000E7C`, HYV7 `0x00000E54` (ayni `-0x28` kaymasi).

---

## 11. Tampon adresleri: tum blok **+0x600** kaymis

c1 icindeki `0x04000000-0x040C0000` kelimelerinin histogrami:

| V8 | HYV7 | not |
|---|---|---|
| `0x0400F2C0` (18 ref) | `0x0400F8C0` (16 ref) | host->cihaz payload (`LAND`) |
| `0x040612C0` (6 ref) | `0x040618C0` (6 ref) | cihaz->host veri tamponu |
| `0x04070EC0` (7) | `0x040714C0` (5) | |
| `0x04074EC0` (3) | `0x040754C0` (2) | `STAG` — **olasi** |
| `0x040753C0`,`0x04075800`,`0x04075840`,`0x04075980`,`0x04075A00` | `0x040759C0`,`0x04075E00`,`0x04075E40`,`0x04075F80`,`0x04076000` | hepsi tam `+0x600` |

`LAND` ve cihaz->host tamponu **kesin** (DPD kopyalama rutini ve `0x49`
isleyicisinin literal'lerinden dogrudan okundu):

```
V8   040c3018  ldr r1,[pc,#0x104] -> 0x0400F2C0 ; movw r2,#0x600 (DPD 1536 B)
     040c31b4  ldr r6,[pc,#0x318] -> 0x040612C0 ; strbeq r8,[r6] (DONE=1) / strbne sb,[r6] (FAIL=0)
HYV7 040c2904  ldr r1,[pc,#0x234] -> 0x0400F8C0 ; movw r2,#0x600
     040c2998  ldr r5,[pc,#0x1e0] -> 0x040618C0 ; strb r7,[r5] (DONE=1) / strb r8,[r5] (FAIL=0)
```
`STAG` icin dogrudan disasm kaniti bulamadim (V8'de `0x89` isleyicisinin
`parca` kolunda kullaniliyor, HYV7'de o kol yok) — sadece `+0x600` desenine
dayaniyor, bu yuzden **olasi** isaretli.

**Geometri isaretcisi.** DPD kopyalama rutini: V8 `ldr r0,[r4,#0x14]`,
HYV7 `ldr r0,[r4,#0xc]`, iki tarafta da `r4 = 0x00000DB8`.
=> `jdisk.GEOM_PTR` 0x00000DCC -> **0x00000DC4**.

---

## 12. `b .` tuzaklari + ONEMLI bir duzeltme

Tuzak listesi (bagimsiz olarak dosyadan cikarildi, verilen listeyle birebir ayni):

```
c0  : 0x00000014                                      (reserved vektor, dokunma)
c1  : 040c013c 040c0140 040c0144 040c0148             (undef/svc/pabt/dabt)
      040c2b10 040c316c 040c31f8 040cd26c 040d165c
      040d1fe8 040d203c 040d27f4 040d2800 040d3cc4
      040d46f8 040d4a38 040d6028 040d7bdc 040d7cd8 040d7e44
```

### 12.1 `bx lr` tuzaklarin cogunda ETKISIZ
HYV7'deki 16 govde tuzaginin **12'si** dogrudan bir `bl`/`blx`'ten sonra geliyor.
Orada `lr` = tuzagin kendi adresi -> `bx lr` tuzaga geri atlar. (V8'de de ayni
durum vardi: 25 govde tuzagindan 19'u.) Yani `jd_hack dayanikli`'nin bu kismi
buyuk olcude bir **no-op**'mus.

`kampanya/hazirla_hyv7.py` varsayilan olarak "akilli" politika kullaniyor:
tuzagin ardindaki kelime gecerli kod ise `nop` (dusup devam et), degilse
dogrulanmis temiz cikisa `b`, dogrulanamadiysa **ATLA**. `--uyumlu` bayragi
V8'in birebir davranisini (hepsi `bx lr`) veriyor ve etkisiz olanlari isaretliyor.

### 12.2 ⚠ `0x040C2B10` = gdp_nand_init FAIL yolu — V8'de YOKTU
```
HYV7 040c2b00  ldr r1,[pc,#0x100] ; add r0,pc,#0x68   ; "[%s] FAIL\r"
     040c2b08  strb r8,[r5]        <- sonuc bayti = 0 (0x040618C0)
     040c2b0c  blx 0x040CC0C0      ; printf
     040c2b10  b .                 <-- SONSUZ DONGU
     ...
     040c2c14  strb r7,[r5]        <- DONE yolu, sonuc bayti = 1
     040c2c18  blx printf
     040c2c1c  mov r0,#1
     040c2c20  pop {r4,r5,r6,r7,r8,pc}
```
V8'in ayni yeri (`0x040C3344`) `blx printf ; mov r0,#1 ; pop` ile **donuyordu**.
Yani **HYV7'de init FAIL ederse firmware asilir.** Bu, "GDP yukleniyor ve
calisiyor ama init dusuyor" tablosuyla birebir ortusuyor.

Yama: `0x040C2B10 = b 0x040C2C1C`; komut kelimesi `0xEA000041`, bayt dizisi `41 00 00 ea`.
Ayni fonksiyonun (`push {r4,r5,r6,r7,r8,lr}` @ `0x040C298C`) temiz cikisi;
sonuc bayti FAIL yolunda zaten 0 yazilmis oluyor.

`0x040CD26C` ve `0x040D1FE8` icin ardindaki kelime veri/yeni fonksiyon oldugu
icin guvenli bir hedef **dogrulanamadi** -> betik bunlara **dokunmuyor**.

---

## 13. `init()` icin gereken mantik degisikligi

| | V8 | HYV7 |
|---|---|---|
| `0x49` yonu | 2 (data-in) | **0 (veri yok)** |
| DONE tespiti | `send(0x49, read=True)` -> `OFF_DATA[0]==1` | `_faz1(0x49)` + **`peek(0x040618C0)`** veya logda `"[gdp_nand_init] DONE"` |

`"[%s] DONE\r"` / `"[%s] FAIL\r"` dizgileri HYV7'de de var (`0x040C2B68` /
`0x040C2B74`), `%s` = `"gdp_nand_init"` (`0x040E74FE`). Yani log tabanli
kontrol de gecerli. `ortak_hyv7.init()` ikisini birden bakiyor.

Diger komutlarin payload duzeni degismedi (taban-izli tarama ile dogrulandi):

| op | V8 okunan payload ofsetleri | HYV7 |
|---|---|---|
| `0x8B` erase | 08,09,0A(BE16),0C,0D | **ayni** |
| `0x89` read | 08,09,0A(BE16),0C(BE16),0E,0F,10,**12** | 08,09,0A,0C,0E,0F,10 (**0x12 yok**) |
| `0x8A` write | 08,09,0A,0C,0E,0F,10,11,12 | 08,09,0A,0C,0E,0F,10 |
| `0x88` flashid | 08,09,0x204 | **ayni** |
| `0x11` DPD | memcpy 0x600 | **ayni** |

=> `sayfa_oku(..., parca=N)` HYV7'de **etkisiz** (alan okunmuyor).

---

## 14. Ciktilar

* `takim/ortak_hyv7.py` — `ortak.py`'nin HYV7 surumu (`ortak.py` degistirilmedi).
* `kampanya/hazirla_hyv7.py` — tuzak/vektor/ASSERT + log kancasi; **varsayilan
  kuru calisma**, yazmak icin `--uygula`. `--sabitler` ile `ortak_hyv7.py`'nin
  tasidigi 19 adres + tablo boyu imaja karsi dogrulaniyor (19/19 + 27 girdi
  gecti); `--uygula` da yazmadan once ayni dogrulamayi kosuyor.
* `cekirdek.py` icin tek degisiklik: `from ortak import *` -> `from ortak_hyv7 import *`
  ve `poke_blok(0x040DBD44, poll)` -> `poke_blok(POLLVAR, poll)` (= `0x040D5FB4`).
* `jdisk.py`/`jdoku.py`/`tezgah.py` de V8 sabiti tasiyor:
  `LAND 0x0400F2C0 -> 0x0400F8C0`, `GEOM_PTR 0x00000DCC -> 0x00000DC4`,
  `STAG 0x04074EC0 -> 0x040754C0 (olasi)`.

## 15. Bulamadiklarim (durust kayit)

| ne | durum |
|---|---|
| `YAMA_ADR[1]`/`[2]` (0x040C8D8C/90) HYV7 karsiligi | **YOK** — o kontrol HYV7'de mevcut degil (dizgi + disasm kaniti §7.2). Uydurma adres yazilmadi. |
| `STAG` (0x04074EC0) | **olasi** 0x040754C0 — sadece `+0x600` tampon deseni; dogrudan disasm kaniti yok. |
| `0x040CD26C`, `0x040D1FE8` tuzaklari icin guvenli cikis | **bulunamadi** — betik bu ikisine dokunmuyor. |
| `0x86`/`0x87`/`0x84`'un ROM'dan mi geldigi | **kanit guclu ama olcum degil** — ilk canli adim tek bir `peek` olmali. |
