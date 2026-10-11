# ANALIZ_DIEREMAP — MAXIO MAP1202 "Cougar" ölü die dışlama (DieReMap) mekanizması

Tarih: 2026-09-16 · **%100 statik analiz** — hiçbir diske/cihaza komut gönderilmedi,
hiçbir hesap açılmadı, kimseyle iletişime geçilmedi.

Kaynak: `MXMPTool_MAP1202_USB_V0_01_017.exe` (SK hynix V7 paketi, T1/T3/T5),
çapraz kontrol `MXMPTool_MAP1202_USB_V0_01_009d.exe` (EEUUAA/JGS3) ve
`MXMPTool_MAP1202_USB_C0_1_003_A1_RC.exe` (B37R). Hepsi 32-bit
C++Builder PE, ImageBase `0x400000`.

> **Kanıt etiketleri:** `[K]` = binary'den doğrudan okundu (adres verildi) ·
> `[T]` = ekibin kendi ölçümü · `[H]` = hipotez, **kanıtlanmadı**.

---

## 0. TL;DR

| Soru | Cevap |
|---|---|
| Die dışlama mümkün mü? | **Evet, resmî mekanizma var ve DPD'de yaşıyor.** Bizim `dpd_*.bin` dosyasının **+0x2D0** ve **+0x310** alanları tam olarak MPTool'un ürettiği die-remap tablolarıdır. `[K]` |
| (ch3, ce2)'yi kapatmak için | **`dpd_x4_p4_s12.bin` ofset `0x323` → `0xFF`.** Tek bayt. `[K]` |
| Kapasiteyi ne belirliyor | `AP_INIState.bDieNumCount = Count / bVirCntPerDie`; `Count` = canlı die sayısı. 16→15 düşer, otomatik. `[K]` |
| 15 (2'nin kuvveti değil) sorun mu | Kodda 2'nin kuvveti şartı **yok**; sayaç düz tamsayı bölen olarak kullanılıyor. `[K]` |
| Kapasite nasıl seçiliyor | `bDieNumCount` → Para dosyasında `PARA_<n>` bölümü → `CAPACITY` (GB) → `LBA = 1953504*GB + 21168`. **`[PARA_15]` hiçbir ürün Para dosyasında YOK, elle eklenmeli.** `[K]` |
| 15 die (2'nin kuvveti değil) sorun mu | Kodda 2'nin kuvveti / kanal katı şartı **yok**. `[K]` |
| **Ölü die salt-okunur modun sebebi mi** | **HAYIR — doğrudan değil.** WP mandalı = NAND'daki QBT bloğunda **≥3 kalıcı assert kaydı** + `Func0` bit3. Init'te die silme testi yok. §6 `[K]` |
| 15 die yapmak WP'yi açar mı | **HAYIR.** İki ayrı problem. §6.7 |

---

## 1. `DieReMap` INI anahtarı — tam çözüm `[K]`

### 1.1 Ayrıştırıcı
`[FlashSetting] DieReMap=...` → `0x0042B5FC`–`0x0042B69C`:

```
GetPrivateProfileString("FlashSetting","DieReMap", default="00", buf, 0xC8, ini)
tok = strtok(buf, ",")                       ; ayırıcı @0x812258 = ","
i = 0
while tok:
    val = hex(tok[0])<<4 | hex(tok[1])       ; 2 haneli HEX, 0x42712c = nibble çevirici
    local[i++] = val
    tok = strtok(NULL, ",")
memcpy(0x016F2A7F, local, 0x20)              ; DieReMapINI[32]
memset(0x016F2A9F, 0, 0x20)                  ; DieStatus[32]
memset(0x016F2ABF, 0, 0x80)                  ; bChBankUI[8][4][4]
```

Yani **32 slot, her slot 2 haneli hex bayt**. Depolandığı yer `0x016F2A7F`.

### 1.2 Slot indeksi = `PhyCh*4 + PhyCe`
`0x0042B6E4`–`0x0042B75F`:

```
for ch: for ce:
    v = DieReMapINI[ch*4 + ce]
    if v == 0xFF:
        DieStatus[ch*4 + ce]      = 0
        bChBankUI[ch*16+ce*4+0..3] = 0
    else:
        (die var)
```

`lea edx, [eax*4 + 0x16f2a7f]` → **stride 4 = CE eksenli**, dış indeks kanal.
32 slot = **8 kanal × 4 CE**.

**Bağımsız doğrulama — iki gerçek üretim paketi:**

| Paket | `Channel` | `Bank` | `DieReMap` | `ch*4+ce` ile tutarlı mı |
|---|---|---|---|---|
| EEUUAA / YMTC JGS3 | 4 | 1 | `01,FF,FF,FF` ×4 sonra `FF`×16 | slot 0,4,8,12 = ch0..3 / ce0 ✓ |
| B37R SN5313 | 4 | 4 | `01`×16 sonra `FF`×16 | slot 0..15 = ch0..3 × ce0..3 ✓ |

`ce*8+ch` varsayımı B37R'yi **açıklayamıyor** (01'ler 0-3, 8-11, 16-19, 24-27'ye
düşerdi) → INI tarafında indeks kesin `ch*4+ce`.

### 1.3 `01` ve `FF` anlamı — **değer = 4 bitlik LUN varlık maskesi** `[K]`
`0x0042B75F`–`0x0042B7E4` (INI'nin "die var" dalı):

```
DieStatus[ch*4+ce] = 1
bChBankUI[ch*16 + ce*4 + 0] = (DieReMapINI[ch*4+ce] >> 0) & 1     ; LUN0
bChBankUI[ch*16 + ce*4 + 1] = (DieReMapINI[ch*4+ce] >> 1) & 1     ; LUN1
bChBankUI[ch*16 + ce*4 + 2] = (DieReMapINI[ch*4+ce] >> 2) & 1     ; LUN2
bChBankUI[ch*16 + ce*4 + 3] = (DieReMapINI[ch*4+ce] >> 3) & 1     ; LUN3
```

- **`0xFF` = o (ch,ce) konumunda CE hiç yok** (`DieStatus = 0`, 4 LUN de 0).
- **`0xFF` dışı = CE var; düşük 4 bit hangi LUN'ların dolu olduğunu söyler.**
  - `01` = yalnız LUN0 → **1 die/CE** (tüm MAP1202 paketleri, bizim durum)
  - `03` = LUN0+LUN1 → 2 die/CE (MAP1602 ODPx2 paketi, `Bank=2`, 8 CE × 2 LUN = 16 die)
  - varsayılan string `"00"` (@`0x812255`) = CE var ama hiç LUN yok (dejenere)

Yani **`DieReMap` hem varlık hem LUN topolojisini taşıyor**, sadece bayrak değil.

---

## 2. `bRemapDieMap` ve `bPhyCh/bPhyCe` — bellek formatı `[K]`

### 2.1 `fn_ProcessDieRemap` @ `0x0045C79C`

```
memset(0x016F2B3F, 0xFF, 0x20)                ; OriginalDieMap[32]
memset(0x016F2B9F, 0xFF, 0x20)                ; AP_INIState.bRemapDieMap[32]

; --- 1) Orijinal harita: DEĞER = fiziksel adres
for ch in 0..7: for ce in 0..3:
    if DieStatus[ch*4+ce] != 0:
        OriginalDieMap[ch*4+ce] = (ch << 4) | ce        ; <<< DEĞER FORMATI
memcpy(bRemapDieMap, OriginalDieMap, 0x20)

; --- 2) SIKIŞTIRMA-1: her kanalda CE deliklerini yukarıdan aşağı çek
for ch in 0..7: for ce in 0..3:
    if map[ch*4+ce]==0xFF:
        for k in ce+1..3:
            if map[ch*4+k]!=0xFF: map[ch*4+ce]=map[ch*4+k]; map[ch*4+k]=0xFF; break

; --- 3) SIKIŞTIRMA-2: her CE sütununda kanal deliklerini çek
for ce in 0..3: for ch in 0..7:
    if map[ch*4+ce]==0xFF:
        for k in ch+1..7:
            if map[k*4+ce]!=0xFF: map[ch*4+ce]=map[k*4+ce]; map[k*4+ce]=0xFF; break
```

→ **`bRemapDieMap[ch*4+ce]` = `(PhyCh<<4) | PhyCe`, `0xFF` = boş.** Slot pozisyonu
sıkıştırma sonrası fiziksel konumu **temsil etmez**; fiziksel konum DEĞERDE.

### 2.2 `bRemapDieMap is %02X, bPhyCh is %d, bPhyCe is %d, Count is %X`
Tek xref: `0x0040BD5A` (fonksiyon `0x0040BB18`). Argüman sırası (sağdan sola push):

```
push counter            ; Count is %X
push [ebp-0x11]         ; bPhyCe is %d      <- v & 0x0F
push [ebp-0x10]         ; bPhyCh is %d      <- (v & 0xF0) >> 4
push v                  ; bRemapDieMap is %02X
```

**`bPhyCh = değer>>4`, `bPhyCe = değer&0xF`.** Kesin. `[K]`

### 2.3 Sayım döngüsü (aynı kod 4 yerde tekrar ediyor)
`0x0045CAC2`–`0x0045CC0B`, `0x0040BB18`, `0x004069C0`, `0x00407C24`:

```
cnt = 0
for L   in 0 .. bVirCntPerDie-1:              ; 0x016F2CC3
  for lun in 0 .. ucDiePerCENum-1:            ; 0x00A2FBA9
    for ce in 0..3:
      for ch in 0..7:                          ; <<< kanal hızlı eksen
        v = bRemapDieMap[ch*4 + ce]
        if v == 0xFF: continue
        PhyCh = v>>4 ;  PhyCe = v & 0xF
        packed = (lun<<6) | (PhyCe<<3) | PhyCh
        list[cnt] = packed
        if L == 0: rev[lun*32 + PhyCe*8 + PhyCh] = cnt
        cnt++
AP_INIState.bDieNumCount = cnt / bVirCntPerDie      ; 0x016F2CC2 = 0x0045CC0B
```

**Paketlenmiş die kimliği: bit0-2 = kanal, bit3-5 = CE, bit6-7 = LUN.** `[K]`

> Çok-LUN (`ucDiePerCENum >= 2`) dalında (`0x00407287`, `0x0040BB83`) düşük nibble
> `ucDiePerCENum`'a bölünüp `PhyCe = low % D`, `LUN = low / D` olarak ayrılıyor.
> Bizde `ucDiePerCENum = 1` olduğu için **tek-LUN dalı** geçerli. `[K]`

---

## 3. ★ DPD +0x310 GERÇEKTEN aynı tablo mu? — **EVET** `[K]`

### 3.1 DPD = `pInitData`; üreteci `Write_GDP_Init_Param` @ `0x004069C0`
Fonksiyon `memset(buf, 0, 0x600)` ile başlıyor — ekibin GDP analizindeki
`movw r2,#0x600 (DPD 1536 B)` ile birebir. MPTool bunun ilk **1024 baytını**
(`push 2` = 2 sektör, ekip notu `0x00443B8E`) `0x11 InitGDP` ile gönderiyor.

Aynı yapı iki yerde daha kuruluyor:
| Fonksiyon | Adres | Hedef |
|---|---|---|
| `Write_GDP_Init_Param` | `0x004069C0` | GDP'ye RAM'de gönderilen DPD |
| `Write_Cougar_GDP_FW_DPD_Param` | `0x00407C24` | `param.raw` **+0x4E0** (NAND'a yazılan parametre bloğu) |
| `Write_Cougar_GDP_FW_DPD_Param` (RDT) | `0x00408EAC` | `param.raw` + `AP_RDT_PARA_MAP.dwDPDOffset` |

Üçü de **aynı** `+0x2B0 / +0x2D0 / +0x310` kodunu içeriyor
(`0x407333/0x40743B`, `0x40858B/0x408693`, `0x409913/0x409A1B`). 009d ve
C0_1_003 sürümlerinde de `add ecx,0x310` / `add edx,0x2d0` kalıpları mevcut
(3 ve 4 kez) → **sürümler arası sabit ABI**. `[K]`

### 3.2 Başlık alanları — Flash.ini sütun lejandıyla birebir eşleşme
`Flash.ini` kendi lejandını taşıyor:
```
; UniName, FullName, Vendor, Type, CE/Package, Blocks/CE, PageNum, PageSize,
;   Die/CE, ECC, ID0~ID5, ExtBlk/Die, DieOffset, PairPage, Interface, Plane,
;   Endurance, Nandmem, SpareByte, GpioSet
Name004=SKV606411 H25BFT8A1BDA  3 2 1  2888 1536 16 1 2  0xAD 0x7E 0x28 0x53 0x02 0xB0  0 0 0 11 4 3000 001 2048 100
```
(bizim NAND'ımız — `kanit/ini/map1202_43.ini:85`, `map1202_33.ini:146`)

`0x004A42xx`'teki geometri log'u global→isim eşlemesini kesinleştiriyor:

| DPD ofs | global | MPTool adı | bizim DPD | Flash.ini |
|---|---|---|---|---|
| +0x00 | `0xA2FBA0` | Vendor | `03` | 3 (Hynix) ✓ |
| +0x01 | `0xA2FBA1` | Type | `02` | 2 (TLC) ✓ |
| +0x02 u16 | `0xA2FBA2` | **wBlocksNum** | 2888 | 2888 ✓ |
| +0x04 u16 | `0xA2FBA4` | **wPagesNum** | 1536 | 1536 ✓ |
| +0x06 u16 | `0xA2FBA6` | **wPageSizeNum** | 16 | 16 (KB) ✓ |
| +0x08 | `0xA2FBA9` | **ucDiePerCENum** | 1 | 1 ✓ |
| +0x09 | `0xA2FBAB` | **ucPlanesNum** | 4 | PL=4 ✓ |
| +0x0A | — | ECC/LDPC rate | 2 | E=2 ✓ |
| +0x0B | `0xA2FBBB` | `bMode` (Interface) | 0x0B | IF=11 ✓ |
| +0x0C | `0xA2FBBE` | `bMaxChans` | **1** | — |
| +0x0D | `0xA2FBBF` | `bMaxBanks` | **0** | — |
| +0x0E u16 | `0xA2FEF0` | SpareByte | 2048 | 2048 ✓ |
| +0x1D | `0xA2FEF7` | (sektör kaydırma) | 9 → **12** `[T]` | — |
| +0x1E | `0xA2FEF8` | (blok maske biti) | 12 | — |
| +0x20..0x3F | — | `bLdrBlockSts[8][4]` (`ch*4+ce`) | 0 | — |
| +0x40..0x47 | `0x16F2C44` | `bFwCh[8]` ← `MPFwChannelSet0..7` | `00 FF×7` | — |
| +0x48..0x4B | `0x16F2C38` | `bFwBank[4]` ← `MPFwBankSet0..3` | `00 FF×3` | — |
| +0x4C | — | **NAND tipi** | `0x14` = **SKV6** | SK hynix V6 ✓ |
| +0x50 / +0x70 / +0xB2 / +0x1B2 | — | timing sabitleri | 0x0B70 / 0x149C / 0x190 / 0x190 | koddaki sabitlerle ✓ |
| **+0x2B0..0x2CF** | `0x16F2A9F` | **`DieStatus[8][4]`** (`ch*4+ce`, 1/0) | **hepsi 00** | — |
| **+0x2D0..0x30F** | — | **die listesi**, `list[logicalDie] = (LUN<<6)|(CE<<3)|CH` | `00 FF×63` | — |
| **+0x310..0x38F** | — | **ters harita**, `rev[LUN*32 + CE*8 + CH] = logicalDie` | (§3.4) | — |
| +0x396 | `0x16F2CFD` | — | 0 | — |

> ### ⚠️ DÜZELTME — `takim/OKUMA.md` yanlış
> `OKUMA.md` `+0x06 u16 = die sayısı = 16` diyor. **Bu yanlış.** `+0x06` =
> `wPageSizeNum` = **sayfa boyu 16 KB**. 16 değeri tesadüfen hem die sayımıza hem
> sayfa boyumuza eşit. Kanıt: `0x004A436D` `movzx eax, word [ebp-0xd6]` →
> `"wPageSizeNum = %d"`, ve `[ebp-0xd6] <- word [0xA2FBA6] -> pInitData+0x06`;
> ayrıca Flash.ini lejandı. **DPD'de die SAYISI diye bir alan yok** — die sayısı
> tamamen +0x2D0/+0x310 tablolarından türüyor. `[K]`

### 3.3 Kod — tabloların kurulumu (`0x0040720D`–`0x00407480`)
```
; +0x2B0: tek-LUN dalında
memcpy(pInitData+0x2B0, DieStatus /*0x16F2A9F*/, 0x20)
; tabloları temizle
memset(pInitData+0x2D0, 0xFF, 0x40)      ; 64 giriş — logical -> physical
memset(pInitData+0x310, 0xFF, 0x80)      ; 128 giriş — physical -> logical
; §2.3'teki sayım döngüsü:
pInitData[0x2D0 + cnt]                       = (LUN<<6)|(PhyCe<<3)|PhyCh
pInitData[0x310 + LUN*32 + PhyCe*8 + PhyCh]  = cnt        (yalnız L==0'da)
```

→ **`+0x310` indeksi = `LUN*32 + PhyCe*8 + PhyCh`. LUN=0 olduğumuz için
`index = ce*8 + ch`. Ekibin `OKUMA.md`'deki formülü DOĞRU** — ve artık
üreticinin kendi kodundan kanıtlı, ampirik tahmin değil. `[K]`

**Ama değerin anlamı farklı:** `0xFF` = die yok; `0xFF` dışı = **mantıksal die
numarası** (varlık bayrağı değil).

### 3.4 Bizim dosyalarımızın hexdump'ı

```
dpd_v0_orij.bin                        dpd_x4_p4_s12.bin  (ekip düzenlemesi)
02b0: 00×16   (DieStatus boş)          02b0: 00×16
02d0: 00 FF FF FF ... FF               02d0: 00 FF FF FF ... FF   (DEĞİŞMEMİŞ)
0310: 00 FF FF FF ... FF               0310: 00 00 00 00 FF FF FF FF
                                       0320: 00 00 00 00 FF FF FF FF
                                       (0x310,311,312,313, 318..31b,
                                        320..323, 328..32b = 00)
```

- **Stok DPD tek-die bir "bring-up" yapılandırması**: `bMaxChans=1`,
  `bMaxBanks=0`, `+0x2D0` listesinde 1 giriş, `+0x310` ters haritasında 1 giriş.
- Ekip **sadece** `+0x310`'da `{0,1,2,3, 8,9,10,11, 16,17,18,19, 24,25,26,27}`
  slotlarını `0x00` yaptı — yani `ce*8+ch`, ce 0..3 × ch 0..3. `+0x2D0`'a hiç
  dokunulmadı. `[T]`
- Ekibin tablosu MPTool'un üreteceğinden **farklı** (hepsi 0x00 yerine 00..0F
  sıralı olmalıydı, §3.5) ama **çalışıyor** `[T]` →
  **GDP'nin die erişim kapısı sadece `rev[...] != 0xFF` kontrolü.** `[K]+[T]`

### 3.5 MPTool'un üreteceği doğru tablolar (simülasyon, §2.3 kodunun birebir taklidi)

**16 die (hepsi sağlam), `Count=16`, `bDieNumCount=16`:**
```
bRemapDieMap : 00 01 02 03 10 11 12 13 20 21 22 23 30 31 32 33 FF×16
+0x2D0 [0:16]: 00 01 02 03 08 09 0A 0B 10 11 12 13 18 19 1A 1B   (kalan FF)
+0x310 [0:32]: 00 01 02 03 FF FF FF FF  04 05 06 07 FF FF FF FF
               08 09 0A 0B FF FF FF FF  0C 0D 0E 0F FF FF FF FF   (kalan FF)
```

**15 die — (ch3, ce2) dışlanmış, `Count=15`, `bDieNumCount=15`:**
```
bRemapDieMap : 00 01 02 03 10 11 12 13 20 21 22 23 30 31 33 FF FF×16
                                                        ^^ sıkıştırma: ce3 -> ce2 slotuna
+0x2D0 [0:16]: 00 01 02 03 08 09 0A 0B 10 11 12 1B 18 19 1A FF   (kalan FF)
+0x310 [0:32]: 00 01 02 03 FF FF FF FF  04 05 06 07 FF FF FF FF
               08 09 0A FF FF FF FF FF  0C 0D 0E 0B FF FF FF FF   (kalan FF)
                        ^^ ofset 0x323 = (ce2,ch3) = ÖLÜ DIE
```

**(ch=3, ce=2) → `+0x310` indeksi = `2*8 + 3` = 19 = 0x13 → DPD ofseti `0x310+0x13` = `0x323`.**

---

## 4. Kapasite `[K]`

### 4.1 `bDieNumCount` zinciri
```
0x0045CBFD:  cl  = bVirCntPerDie        (0x016F2CC3, INI [FwSetting] bVirCntPerDie)
             eax = Count                 (canlı die sayısı × ucDiePerCE × bVirCntPerDie)
             idiv
             AP_INIState.bDieNumCount (0x016F2CC2) = Count / bVirCntPerDie
```
Bizde `bVirCntPerDie=1`, `ucDiePerCENum=1` → **`bDieNumCount` = canlı die sayısı.**
16 → 15 otomatik. **Ayrı bir INI anahtarı yok**; `[DeviceSetting] DieNumCount`
(B37R'de 8) sadece bir kontrol/beklenen değer — hesaplanan değer INI'den değil,
`DieReMap`'ten türüyor. `[K]`

### 4.2 Kapasite formülü (EXE'de birebir, `0x00923131`)
```
wBadBlock = ceil( (float)(wBlockUnitNum - ucSYSBlockUnitNum - ucFixSLCBlockUnitNum)
          - (float)( (float)((wVDSuperBU + ucMergeBUNUM + wRollRateBU) * ucVDNUM)
                     / (float)(AP_INIState.bDieNumCount) ) )
```
→ kapasite doğrudan `bDieNumCount`'a bağlı. **15 (2'nin kuvveti olmayan) bir değer
kodda hiçbir yerde reddedilmiyor**; düz `idiv` operandı. `[K]`
(`EnUnbalance` anahtarı da mevcut — bizim INI'lerde `0`.)

### 4.3 `PARA_<n>` merdiveni — seçici doğrudan `bDieNumCount` `[K]`
`0x0042E562` → `[ebp-0x2e] = byte[0x016F2CC2]` (= `bDieNumCount`);
`0x0042E5BF/C4` → `sprintf(buf, "PARA_%01d", bDieNumCount)` (string @`0x00814542`).
Aynı kalıp 009d/B37R/1602 sürümlerinde de var. **Yani Para dosyasındaki bölüm adı
canlı die sayısıdır.** 16 die → `[PARA_16]`, 15 die → **`[PARA_15]`**.

Zincir (uçtan uca kanıtlı):
```
DieReMap(INI) -> DieStatus + LunEn -> fn_ProcessDieRemap (delik sıkıştırma)
  -> sayım Count -> bDieNumCount = Count / bVirCntPerDie
     -> ExtParaFile'da "PARA_<bDieNumCount>" bölümü -> CAPACITY (tam GB)
        -> AP_INIState.IDEMACapacity -> LBA = 1.953.504 x GB + 21.168
           -> CapacitySectorHigh/Low  (NVMe'nin bildirdiği kapasite)
  ve paralelde -> DPD +0x2D0 (mantıksal->fiziksel liste), +0x310 (ters harita)
```

Birim tablosu `[K]`:

| anahtar | dosya | birim |
|---|---|---|
| `[FwSetting] IDEMACapacity` | MPTOOL.ini | **0,1 GB** (onda birlik) — okunup 10'a bölünüyor |
| `[PARA_n] CAPACITY` | Para_*.ini | **tam GB** — `IDEMACapacity`'yi ezer |
| `CapacitySectorHigh/Low` | MPTOOL.ini | **512 B LBA**, türetilmiş: `1953504*GB + 21168` (IDEMA LBA1-02) |
| `[PARA_n] HSPD_CAPACITY` | Para | GB, pSLC önbellek; UI `> IDEMA/3` reddediyor |
| `[PARA_n] DCO` | Para | GB |
| `[DeviceSetting] CapacityIndex` | MPTOOL.ini | okunuyor ama **kapasite kaynağı değil** |

Doğrulama — her pakette `CAPACITY` ↔ `CapacitySectorLow` tutuyor:

| paket | die | rung | CAPACITY | IDEMACapacity | CapacitySectorLow |
|---|---|---|---|---|---|
| **SKV7 (HYV7)** — bize en yakın | 16 | `[PARA_16]` | **1024** | 10240 | 2.000.409.264 ✓ |
| B37R | 16 | `[PARA_16]` | 1024 | 10240 | 2.000.409.264 ✓ |
| JGS3 (EEUUAA) | **4** | `[PARA_4]` | 256 | 2560 | 500.118.192 ✓ |
| JGS2 | 16 | `[PARA_16]` | 512 | 5120 | 1.000.215.216 ✓ |
| X397 (MAP1602 2TB) | 16 | `[PARA_16]` | 2048 | 20480 | 4.000.797.360 ✓ |

Ayrıca gerçek üretim logu doğruluyor: `repo/EEUUAA_MAP1202/log/PFT_19_*.log:327`
→ `AP_INIState.bDieNumCount=4`, aynı logda 4 die listeleniyor (`C:0 B:0 … C:3 B:0`)
ve `DieReMap` 4 slot açık. `[K]`

### 4.4 §4.2'deki `wBadBlock` formülü kapasite DEĞİL — düzeltme `[K]`
Formül `EN_VD != 0` kapısının arkasında (`0x0049E456` 009d: `cmp byte[EN_VD],0; je`).
`EN_VD=0` (bizim SKV7 profili dahil tüm rung'larda) olduğunda **öbür dal**
çalışıyor ve orada `bDieNumCount` **hiç geçmiyor**:
`wBadBlock = wBlockUnitNum - ucSYSBlockUnitNum - ucFixSLCBlockUnitNum - (wVDSuperBU + ucMergeBUNUM + wRollRateBU)`.
Yani bu formül **bad-block bütçesi**, kullanıcı kapasitesi değil. Kapasite
`PARA_<n>.CAPACITY`'den geliyor (§4.3). BULGULAR.md §5.2'nin "kapasite doğrudan
`bDieNumCount`'tan türüyor" cümlesi bu yüzden **yanıltıcı** — doğrusu:
`bDieNumCount` **rung seçiyor**, kapasite rung'ta yazılı.

### 4.5 ★ 15 die temsil edilebilir mi? — EVET, ama `[PARA_15]` YOK `[K]`
**Temsil edilebilirlik:** `bDieNumCount` düz `u8`; tek sınır `Count <= 64`
(`"Logical die count is over 64!"`). Kodda 2'nin kuvveti / kanal katı şartı
**yok** (`power of` / `multiple of` / `even number` / `symmetric` → hiçbir EXE'de
geçmiyor). `fn_ProcessDieRemap` zaten delik sıkıştırıyor → asimetrik yerleşim
**tasarlanmış durum**. `EnUnbalance` anahtarı var (`0x0042 8254` → `byte[0x16E73A4]`,
UI `Unbalance FW`) ama **tüm stok INI'ler `EnUnbalance=0`** ve semantiği
**kanıtlanmadı** `[H]`. RAID kısıtları (`EnVD`, `VDieRaidNum`, `EnSuperDie`,
`bVirTblPerDie`) bizim profilde kapalı (`SKV7_64GB_FULL_NO_RAID`: `EnVD=0`,
`VD_NUM=0`, `EnSuperDie=0`, `bVirCntPerDie=1`).

**Ama:** korpustaki **9 ürün Para dosyasının hiçbirinde `[PARA_15]` yok** —
hepsi sadece `{64,32,16,8,4,2,1}`. Yalnızca şablon `Para_NULL.ini` 64 rung'un
tamamını içeriyor (`[PARA_15]`: `CAPACITY=450`, `DCO=30`, `HSPD_CAPACITY=60`,
`THROTTLE_MAX=15` — 30 GB/die yer tutucu, bizim 64 GiB/die parçamız için yanlış).
`[PARA_15]` yoksa `ReadPara` → `"ReadPara INI PARA_15 (X) - Load default value"`,
dönüş `0x10`, çağıran **`Error: Please check Para.ini`** kutusu açıyor; `CAPACITY`
varsayılanı **0** → `"Please input a correct IDEMA capacity(not equal to 0)"`. `[K]`

> `"Die count is mismatch!"` string'i 4 build'in hepsinde var ama **hiçbirinde
> koda referansı yok** (32-bit ref taraması, 0 hit) — ölü string, bu mesajı
> beklemeyin. `[K]`

### 4.6 Beklenen kapasite — sayılar

| | değer |
|---|---|
| die başına ham (2732 blok × 1536 sayfa × 16384 B) | 68.753.031.168 B = **64,031 GiB** |
| 16 die ham | 1.100.048.498.688 B = **1024,50 GiB** (MPTool `fTotalSize`=1024,50 ✓) |
| 16 die sevkiyat kapasitesi (`[PARA_16]` SKV7) | `CAPACITY=1024` → **2.000.409.264 LBA** = 1024,21 GB (OP %6,91) |
| **15 die ham** | 1.031.295.467.520 B = **960,47 GiB** (`fTotalSize`=960,47 ✓) |
| **15 die, aynı OP oranıyla (naif 15/16)** | **960 GB** → **1.875.385.008 LBA** = 960,20 GB |
| merdivende hazır rung | **yok** — `[PARA_15]` eklenmeli |
| `Para_NULL.ini [PARA_15]` | 450 GB — şablon, bizim parça için yanlış |

---

## 5. Uygulanabilir reçete

> ⚠️ **Önce §6'yı okuyun.** Salt-okunur mod ölü die'ın DOĞRUDAN sonucu değil;
> die'ı dışlamak tek başına diski yazılabilir yapmaz.

### 5.1 A yolu — GDP oturumu (ekibin kendi FTL'i, `takim/jdnbd4.py`) ✅ ÖNERİLEN
**Tek bayt:**
```
dosya : re/gdp/dpd_x4_p4_s12.bin   (yeni ad: dpd_x4_p4_s12_15die.bin)
ofset : 0x323          (= 0x310 + ce*8 + ch = 0x310 + 2*8 + 3)
eski  : 0x00
yeni  : 0xFF
```
- Yöntem: mevcut `0x11 InitGDP` akışı — **ürün firmware'i gerekmez**.
- Kapasite: 15 die × 1024 blok × 1536 sayfa = **337,5 GiB** (mevcut 1024-blok
  sarma limiti ile); sarma kırılırsa 15 × 2732 × 1536 ≈ **900 GiB**.
- Risk: düşük, geri alınabilir (dosya değişikliği).
- **Not:** Bu adım **GDP'nin o die'a yayın (broadcast, `ch=FF ce=FF`) komutu
  göndermesini engeller** hipotezine dayanıyor `[H]`. Ekibin kendi yazılımı zaten
  die'ı atlayabilir — DPD değişikliği "kemer + askı".

### 5.2 B yolu — ürün firmware'ini 15 die ile çalıştırmak ⚠️ KANITLANMADI
Ürün firmware'i die haritasını **NAND'daki parametre bloğundan** okur; MPTool o
bloğu `Write_Cougar_GDP_FW_DPD_Param` ile `param.raw + 0x4E0` konumuna aynı
düzende yazar `[K]`. Yani gereken:
1. NAND'daki parametre sayfasını bul (ekip: `LDBK CONFIG V00`, `ANALIZ_LDBK_YAZMA.md`),
2. içindeki DPD alt-bloğunun `+0x310 + 19` baytını `0xFF` yap (ve tutarlılık için
   `+0x2D0` listesini §3.5'teki 15-die haline getir),
3. geri yaz + `VP_PROC_CheckDPDPara` tarzı sayfa-sayfa doğrula.

**Kanıtlanmayanlar:** (a) parametre sayfasının NAND'daki tam yeri/biçimi
(CRC/imza var mı), (b) ürün firmware'inin gerçekten bu tabloyu okuduğu,
(c) kapasitenin otomatik düşeceği. Hepsi `[H]`.

### 5.3 Ham "MPTool-doğru" 16-die DPD (isteğe bağlı deney)
Ekibin `+0x310` tablosu hepsi `0x00`. MPTool `00 01 02 03 FF FF FF FF 04 05 ...`
üretirdi ve `+0x2D0` listesini de doldururdu. **Şu an çalışan yapılandırmayı
bozmamak için dokunmayın**; ayrı bir deney olarak denenebilir. Aynı şekilde
`bMaxChans` (+0x0C) şu an **1**, `bMaxBanks` (+0x0D) **0** — fabrika değeri
4 ve 4 olmalıydı. Bunlar GDP'nin die kapısını etkilemiyor gibi görünüyor `[T]`
ama ürün firmware'i için yanlış. `[H]`

---

## 6. ★ KRİTİK SORU — ölü die salt-okunur modun SEBEBİ mi? `[K]`

### 6.1 Cevap: **HAYIR — doğrudan değil.** Firmware init'te die silme testi YAPMIYOR.

Salt-okunur bayrağı **kalıcı assert sayacı** eşiğinden geliyor:

```
; e07_0x040D0000.bin @0x067CE  (VA 0x040D67CE, Thumb) — BAĞIMSIZ DOĞRULANDI
0x040D67CE  adr  r0, #0x250     -> 0x040D6A20 "ASSERT happened:M(%d)F(%d)L(%d)"
0x040D67DC  adds r4, r4, #1
0x040D67DE  cmp  r4, #3
0x040D67E0  blo  0x040D67BC     ; en fazla 3 kaydı yazdır
0x040D67E2  ldr  r0, [r6]       ; r6 = 0x040EEE58 -> assert kayıt SAYISI
0x040D67E4  cmp  r0, #3
0x040D67E6  blo  0x040D67F4     ; sayı < 3  -> hiçbir şey yapma
0x040D67E8  adr  r0, #0x258     -> 0x040D6A44 "WRITE-PROTECT"
0x040D67EA  bl   printf
0x040D67EE  ldr  r1, [pc,#0x264]-> 0x00810CE8        (literal @e07:0x6A54 doğrulandı)
0x040D67F0  movs r0, #3
0x040D67F2  strb r0, [r1]       ; *** mod = 3 = WRITE-PROTECT ***
0x040D67F4  pop  {r4,r5,r6,pc}
```

**Koşul:** `NAND'daki QBT sistem bloğunda saklı assert kayıt sayısı >= 3`
→ `*(0x00810CE8) = 3`.

**İkinci koşul (yazma kapısı):** her yazma kapısı
`mod ∈ {3,4} && *(0x00000398) bit3 == 1` test ediyor
(`e07@0x06CB0` → `"wp no q-wr"`; `e07@0x1C090` → yeni yazma bloğu hiç açılmıyor).
Canlı değer: `e10@0x398 = e11@0x398 = 0A F8 01 00` → `Func0 = 0x0001F80A`,
**bit3 = 1**. `[K]`

### 6.2 Yapışkan mı, her açılışta mı türetiliyor? — **İkisi de**
- **Sebep kalıcı:** assert kayıtları NAND'daki **QBT sistem bloğunda**
  (`e04@0x09248`, op `0x17` = "QBT'ye assert kaydı ekle"; taşınca
  `"OVER ASSERT_THRESHOLD"` @`e04:0x94FC`). En fazla 3 kayıt.
- **Bayrak geçici:** RAM'deki mod baytı (`0x00810CE8`) ve assert kaydı
  (`0x040EEE58`) her açılışta **sıfırlanıyor** (`e08@0x0015C`, `e06@0xC5A0`),
  sonra `[QBT]` boot fazında NAND'dan yeniden okunup yeniden mandallanıyor
  (`e04@0x0083C` → `0x0406C600 "[QBT]S"`), ardından boot yolu
  `"[WP-BT]S"` (write-protect boot) / `"[PBT]S"` (normal boot) diye ayrılıyor.

→ **Kullanıcı verisini silmek bunu TEMİZLEMEZ**; QBT/sistem bloğu silinmedikçe kalır.

### 6.3 Aranan string'ler — negatif bulgular `[K]`
`ScanDie`, `BadDie`, `Bad Die`, `bad die`, `DieFail`, `ROMode`, `RO Mode`,
`LaterBad`, `RunTimeBad` → **`dis_kaynak/` altındaki 530 dosyanın 0'ında,
12 canlı dökümün 0'ında.** Init'te die taraması/silme testi **yok**:
die sayısı config'ten geliyor (`e06@0x0E5E4`: `ldrb [0x300+0xE0]`, 0 ise
`"E:max_dies=0"` + varsayılan 16). Silme hataları retry döngüsüne gidiyor
(`"erase loop bad"`, `"ERA NG:Cnt:%d"` — `e07@0x055C0/0x056B0`) ve normal
later-bad işaretlemesiyle bitiyor; WP tetiklemiyor.

### 6.4 Ölü die ile bağlantı — dolaylı `[H]`
`0x0406C0C8`'de assert kontrolüne giden tetik, son NAND işlemi etiketi
`-0xBC` olduğunda çalışıyor; bu etiket yalnız op `0x17` = **QBT'ye assert
kaydı yazma** tarafından üretiliyor (`e07@0x05D54`). Yani zincir muhtemelen:

```
ölü die (ch3,ce2) -> o die'daki tablo/QBT yazması başarısız -> assert
   -> QBT'ye assert kaydı  -> 3'e ulaştı  -> WRITE-PROTECT mandalı
```

ama **firmware'in doğrudan "die öldü → salt-okunur" kararı YOK.** Bu zincirin
son halkası (assert'ların gerçekten ölü die yüzünden atıldığı) `[H]` —
kanıtı firmware'in kendisi verir: vendor yolu `VA 0x040D7FAA`
`"TOOL assert_info:" / "assert_location = %x"` (`*(0x040EEE5C)`) ile ilk
assert'ın Modül/Dosya/Satır'ını döndürüyor. (Bu **canlı okuma gerektirir,
bu analizde yapılmadı.**)

### 6.5 Bu WP özelliği stok firmware'de YOK `[K]`
`WRITE-PROTECT`, `OVER ASSERT_THRESHOLD`, `wp no q-wr`, `assert cnt`,
`ASSERT happened`, `It's not WP status`, `QBT insert assert`, `TOOL assert_info`,
`Frontend WP ON`, `wp_mode assert` → **37 stok MAP1202/MAP1602 imajının
HİÇBİRİNDE yok.** Stok 2022 HYV7 build'inde (`YIQZCA2C.bin@0x058288`) aynı
komşu string bloğu (`Q-Wr:%x … QBT Wr in Sntz`) var ama bu 4 assert/WP string'i
**bizim OEM build'imize eklenmiş**. `Func0` bit3 ↔ INI anahtarı eşlemesi hâlâ
`[H]`: en olası aday `EnWriteProtectAbort=1` ("abort/assert'ta yaz-koru"),
BULGULAR.md'deki `Function0` iddiası **kanıtlanmadı**.

### 6.6 Önceki analizlere düzeltme
- `ANALIZ_FW_READONLY.md` §2'deki "die blok-harita tutarlılık taraması ≥512
  uyuşmazlık → salt-okunur (`e06 0x040632AC`)" **mekanizma DEĞİL**. O kod bir
  *medya durumu* baytı (`0x040EE73C`) yazıyor, canlı değeri `0x00`. Gerçek
  yazma kapıları `mod + Func0.bit3` test ediyor.
- `fw_canli/tk2.py` Thumb `ADR`'yi yanlış çözüyor (ham immediate'i saklıyor) →
  `refs.pkl` bu string'lerin hiçbiri için xref içermiyor. Düzeltilmiş tarayıcı:
  `scratchpad/adr2.py` (5642 hedef, ARM+Thumb ADR/ADR.W/LDR-literal).

### 6.7 SONUÇ — reçete üzerindeki etkisi ⚠️
**DieReMap ile ölü die'ı dışlamak, salt-okunur modu KENDİ BAŞINA AÇMAZ.**
Yazılabilir bir disk için iki ayrı iş gerekir:

| # | İş | Durum |
|---|---|---|
| 1 | Ölü die'ı dışla (`DPD 0x323 = FF`) | §5, kanıtlı yol |
| 2 | *(bu satır kamuya açık depodan çıkarıldı — write-protect mekanizmasının kendisini devre dışı bırakma yöntemiyle ilgiliydi, bkz. repo README "Neden bazı dosyalar burada yok")* | — |

Bunlar **sıralı değil, bağımsız**. (2) yapılmadan (1) diski yazılabilir yapmaz;
(1) yapılmadan (2) muhtemelen yeni assert'lar üretip diski tekrar WP'ye düşürür.

---

## 7. MPTool ile fabrika yolu (C yolu) — tam INI reçetesi `[K]` + `[H]`

Eğer bir gün MPTool'u ROM modunda çalıştırıp diski **fabrika yoluyla 15 die ile**
yeniden formatlamak istenirse:

```ini
[FlashSetting]
; slot index = ch*4 + ce ;  değer = 4-bit LUN maskesi ; FF = CE yok
; (ch3,ce2) = slot 3*4+2 = 14  ->  15. alan  ->  FF
DieReMap=01,01,01,01,01,01,01,01,01,01,01,01,01,01,FF,01,FF,FF,FF,FF,FF,FF,FF,FF,FF,FF,FF,FF,FF,FF,FF,FF,
Channel=4
Bank=4

[FwSetting]
IDEMACapacity=9600            ; 0,1 GB birimi -> 960 GB
CapacitySectorHigh=0
CapacitySectorLow=1875385008  ; 1953504*960 + 21168
bVirCntPerDie=1
EnVD=0
EnSuperDie=0
```

ve Para dosyasına (`Para_DW_SKV7_64GB_FULL_NO_RAID.ini`) **`[PARA_15]` eklenmeli**,
`[PARA_16]`'dan klonlanarak:

```ini
[PARA_15]
CAPACITY=960          ; 1024 * 15/16
THROTTLE_MAX=15
DCO=75                ; 80 * 15/16
HSPD_CAPACITY=290     ; 310 * 15/16 ; IDEMA/3 = 320 sınırının altında kalmalı
; diğer tüm alanlar [PARA_16] ile aynı
```

**Kanıt durumu:** `DieReMap` alan indeksi ve `FF` anlamı `[K]`; `PARA_<n>` seçimi
`[K]`; LBA formülü `[K]`. **`CAPACITY=960` / `DCO=75` / `HSPD=290` sayıları
`[H]` — oranlama benim, üreticinin merdiveninde 15-die basamağı yok.**
`EnUnbalance=1` gerekli mi **bilinmiyor** `[H]`.

### ⚠️ Fabrika yolunun kendi engeli: Flash.ini satırı yok
Korpustaki hiçbir `Flash.ini`'de **`D4` (4 CE) SK hynix V6 satırı yok.** En yakın
satır tek-CE kardeşi:
```
Name004=SKV606411 H25BFT8A1BDA  3 2 1  2888 1536 16 1 2  0xAD 0x7E 0x28 0x53 0x02 0xB0  0 0 0 11 4 3000 001 2048 100
                                V T C  Blks  PGs PZ D E   ID0  ID1  ID2  ID3  ID4  ID5           IF PL  Ed  Nm   SB Gpio
```
(`kanit/ini/map1202_43.ini:85`) — geometri doğru (2732 ölçülen/2888 nominal blok,
1536 sayfa, 16 KB, 4 plane, 2048 spare) ama `C=1`. Doğru `FlashUniName` satırı
olmadan `wBlockUnitNum` ve tüm MEET-CAPACITY kontrolü yanlış çıkar. `[K]`

---

## 8. KANITLANMAYANLAR — dürüst envanter

| # | İddia | Durum |
|---|---|---|
| 1 | GDP'nin die erişim kapısı **sadece** `DPD[0x310+idx] != 0xFF` | `[T]` ampirik (ekip 16 slotu `00` yapınca 16 die açıldı) + `[K]` MPTool kodu. **GDP'nin ARM kodunda doğrudan okuma kanıtı YOK.** |
| 2 | `DPD[0x323]=FF` yayın (broadcast `ch=FF ce=FF`) komutunu o die'a göndermeyi durdurur | **`[H]` — kanıtlanmadı.** Test gerekir. |
| 3 | Ürün firmware'i die haritasını NAND parametre sayfasındaki aynı `+0x2D0/+0x310` yapısından okur | `[K]` MPTool aynı yapıyı `param.raw+0x4E0`'a yazıyor; **firmware tarafında okuma kanıtı YOK** `[H]` |
| 4 | NAND'daki parametre sayfasının yeri/biçimi (CRC/imza?) | **bilinmiyor** |
| 5 | Assert'ların gerçekten ölü die yüzünden atıldığı | `[H]` — firmware kendi söyleyebilir (`VA 0x040D7FAA`, `assert_location`), **canlı okuma gerekir** |
| 6 | `Func0` bit3 ↔ hangi INI anahtarı | `[H]`. En olası: `EnWriteProtectAbort`. BULGULAR.md'nin `Function0` iddiası **kanıtlanmadı** |
| 7 | 15 die kapasite sayıları (960/75/290) | `[H]` — oran benim, üretici merdiveninde 15 basamağı yok |
| 8 | `EnUnbalance` semantiği | `[H]` — 12 okuma noktası izlenmedi |
| 9 | `dpd_v0_orij.bin`'in kaynağı (fabrika mı, GDP varsayılanı mı) | bilinmiyor; `bMaxChans=1/bMaxBanks=0` fabrika değeri **olamaz** → muhtemelen bring-up varsayılanı `[H]` |
| 10 | Canlı dökümün kapsamı | 12 bölge / ~500 KB. Bu bölgelerin **dışında** die testi olmadığı kanıtlanmadı |

---

## 9. Kullanılan araçlar
`scratchpad/re/pe.py` (PE parser), `scratchpad/re/xdis.py` (capstone x86-32 +
string/xref anotasyonu), `scratchpad/re/sim.py` (fn_ProcessDieRemap + die tablosu
simülatörü), `scratchpad/adr2.py` (düzeltilmiş ARM/Thumb ADR xref tarayıcı).
Hiçbir cihaza komut gönderilmedi.
