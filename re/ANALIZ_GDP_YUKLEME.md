# ANALIZ — GDP.bin'i loader/ROM moduna yukleme (MPTool-native, byte seviyesi)

Hedef exe (yamasiz orijinal): `/mnt/mpt/MPT/MXMPTool_MAP1202_USB_V0_01_017.exe`
(6.494.840 B, Win32 PE, ImageBase 0x400000). GDP imaji: `/mnt/mpt/MPT/GDP.bin` (233472 B).
Butun VMA'lar bu binary icindir. **Statik analiz — cihaza HICBIR komut gonderilmedi.**
Tunel primitifleri briefing'deki `adm`/`pay` (FAZ1/FAZ2, magic 0x001234FF / 0x00123400|sub).

Kaynak fonksiyonlar (r2 `pdf`, kanit):
- `VC_LDR_CmdWriteRam`     = fcn.0x424e08  (sub 0x87)
- `VC_LDR_CmdWriteRamRsa`  = fcn.0x424eb8  (sub 0x87 + tip baytı)
- `VC_LDR_CmdJumpToPRAM`   = fcn.0x424a4c  (sub 0x82)
- `VC_LDR_CmdJumpToROM`    = fcn.0x424b6c  (sub 0x83, kiyas)
- `VP_WriteCodeToMemNew2`  = fcn.0x4368f0  (GDP.bin'i acar, entry dongusu, jump)
- `sub_WriteRegion`        = fcn.0x434f9c  (chunk dongusu; WriteRam/WriteRamRsa secimi)
- tasiyici                 = fcn.0x4244e4  (7 arg; FAZ1+FAZ2)

===============================================================================
## G1 — VC_LDR_CmdWriteRam (0x424e08, sub 0x87): TAM ENCODING
===============================================================================
Imza: `fcn.0x424e08(port, dataPtr, nsec, addr)`  (arg_8h, arg_ch, arg_10h, arg_14h).

Payload kurulumu (kanit 0x424e2b..0x424e6e):
```
payload[0] = 0xFF                       ; 0x424e2b
payload[1] = 0xE5                       ; 0x424e32
payload[2] = 0x87   <- sub              ; 0x424e39
payload[3] = 0x00   <- SABIT (tip=0)    ; 0x424e40
payload[4] = (addr >> 24) & 0xFF        ; 0x424e47  shr edx,0x18
payload[5] = (addr >> 16) & 0xFF        ; 0x424e53  shr ecx,0x10
payload[6] = (addr >>  8) & 0xFF        ; 0x424e5f  shr eax,8
payload[7] =  addr        & 0xFF        ; 0x424e6b
```
=> **RAM hedef adresi payload[4..7]'te, BIG-ENDIAN 32-bit** (MSB once). payload[8..11]=0.

Tasiyici cagrisi (kanit 0x424e74..0x424e8e):
```
fcn.0x4244e4(port, payloadPtr, payloadLen=0x0C, dataPtr, nsec, dir=0, 0x1000)
```
- **payloadLen = 0x0C (12)** ; **dir = 0 => FAZ2 YAZMA** ; nsec = arg_10h.
- Chunk uzunlugu payload'da DEGIL; **yalniz nsec ile** (FAZ2 = nsec*512 bayt data-out).
- Bir cagrida max chunk: cagiran (0x434f9c) belirler = **0x10000 (64 KB = 128 sektor)** legacy modda
  (NVMe-mode 0x1000). Bkz G4.

Kopyalanabilir:
```python
def WriteRam(addr, data):
    # FAZ1 (komut): FF E5 87 00 <addr BE32>
    adm(0xC1, cdw=(0x80,0,0,0,0x001234FF,1), veri=512,
        gonder=pay(0x87, 0x00, (addr>>24)&0xFF,(addr>>16)&0xFF,(addr>>8)&0xFF,addr&0xFF))
    # FAZ2 (data-out): nsec = ceil(len/512), sub=0x87 -> CDW14=0x00123487
    nsec = (len(data)+511)//512
    buf  = data + b"\x00"*(nsec*512 - len(data))
    adm(0xC1, cdw=(nsec<<7,0,0,0,0x00123487,nsec), veri=nsec*512, gonder=buf)
```
Not: WriteRam sonrasi GetReturn/status POLL YOK (0x434f9c yalniz al==1 doner mi bakar, devam eder).

===============================================================================
## G2 — VC_LDR_CmdWriteRamRsa (0x424eb8): FARK ve NE ZAMAN
===============================================================================
Imza: `fcn.0x424eb8(port, dataPtr, addr, nsec, -, type)` (arg_8h,ch,10h,14h,1ch).

Duz WriteRam'den 2 fark (kanit 0x424ee9..0x424f45):
1. `payload[3] = type` (arg_1ch & 0xFF)  — WriteRam'de sabit 0x00 idi; burada **cagiranin
   verdigi tip/imza baytı**. Adres yine BE32 payload[4..7] (ama arg_10h'ten).
2. `payloadLen = 0x10 (16)` (WriteRam'de 0x0C). Ekstra payload[8..15] gonderilir (bu kod yolunda
   memset=0 kaldigi icin fiilen 0). dir=0 (YAZMA), nsec=arg_14h.

**Ne zaman kullaniliyor (kanit 0x434f9c):** secim `arg_20h` (RSA bayragi) ile:
- `arg_20h == 0` -> **duz WriteRam (0x424e08)**  (0x435251 / 0x435158 legacy dallari)
- `arg_20h != 0` -> **WriteRamRsa (0x424eb8)**    (0x435226 / 0x435122 legacy dallari)

`VP_WriteCodeToMemNew2` GDP.bin'in **2 kod entry'sini arg_20h=0 ile** yazar (duz WriteRam).
RSA varyanti YALNIZ ayri "RSA data" blogunda cagriliyor (kanit 0x436ac5..0x436b03):
`dest=0x400, len=0xC00 (3072), type=0x0A, arg_20h=1`, kaynak = GDP.bin dosya ofseti 0x400.
**AMA GDP.bin[0x400:0x1000] = tamamen 0xFF** (xxd ile dogrulandi) => bu imajda gercek RSA yuku
YOK; RSA blogu **dummy/no-op** (3072 bayt 0xFF, RAM 0x400'e). **Bizim replikasyonda ATLANABILIR.**

**Imza dogrulama var mi?** Aracin kendisinde KRIPTO dogrulama YOK. Tek kontrol: 0x434f9c @0x435014
`memcmp(buffer+0x1C0, "MKGDP", 5)` — sadece kimlik/param cikarma icin (GDP_Para.raw dump'ini
tetikler), yaz/atla kararını degistirmez. Gercek imza duvari cihaz ROM'unda (LOADER_CERT_TAG1);
MAXIO'nun kendi GDP.bin'i onu dogal geçer. Yani biz GDP.bin'i **oldugu gibi** yukleriz.

===============================================================================
## G3 — VC_LDR_CmdJumpToPRAM (0x424a4c, sub 0x82): TAM ENCODING
===============================================================================
Imza: `fcn.0x424a4c(port, event)`  (arg_8h, arg_ch). Payload (kanit 0x424a84..0x424adb):
```
payload[0] = 0xFF
payload[1] = 0xE5
payload[2] = 0x82   <- sub
payload[3] = event  (arg_ch & 0xFF)         ; 0x424a99
payload[4] = 0x5A   <- SABIT                 ; 0x424aa2
payload[5..8] = BE32(0x0000000C) = 00 00 00 0C   ; var_4h=0xC, shr 24/16/8/0  (0x424aa9..)
```
=> operatif bayt dizisi: **`FF E5 82 <event> 5A 00 00 00 0C`**. (0x5A = jump-magic; 0x0000000C
= sabit 12 = tanımlayıcı uzunlugu, payloadLen ile ayni.)

Iki yol, `[0x1703de8]`=EnNvmeCmdMode'a gore (kanit 0x424ae1 `cmp byte [0x1703de8],0; je ...`):
- `!=0` (NVMe-mode): tasiyici payloadLen=0x1000, nsec=0.
- `==0` (**LEGACY = BIZIM tunel**, r2: `[0x1703de8]=0`): tasiyici **payloadLen=0x0C, nsec=0,
  dir=0 => FAZ2 YOK**. Sadece FAZ1 komut. (kanit 0x424b2e-0x424b43: push 0xc payloadLen.)

`event` degeri = cagiranin `var_5h`'i = **basariyla yuklenen bin sayisi = GDP.bin icin 1**
(VP_WriteCodeToMemNew2 @0x436b3a: `mov cl,[var_5h]; JumpToPRAM(port, var_5h)`; var_5h dis
dongude 0x436b1c'te bin basina +1). Tek GDP.bin -> event=1.

**Jump SONRASI:** cihaz yuklenen GDP'yi (ARM reset vektoru @0x00000000) calistirir. Arac
JumpToPRAM'den sonra WCM2'den doner ve ust akista **dogrudan VP_InitGDP (0x436B5C) ->
InitGDP(0x11)** cagirir; **reset/re-enumerate bekleme YOK** (1s Sleep yalniz JumpTo**ROM**'dan
sonra var, JumpToPRAM'den sonra degil). Tunel kopmaz; InitGDP ile devam. (Pratikte GDP boot'u
icin InitGDP oncesi kisa bir bekleme/poll onerilir.)

Kiyas — JumpToROM (0x424b6c, sub 0x83): payload = `FF E5 83 <event>` (0x5A/0x0C YOK). ROM'a
doner (Jump to Loader menusu). PRAM'a atlamak icin 0x82 + 0x5A + 0x0C sart.

```python
def JumpToPRAM(event=1):
    # FF E5 82 <event> 5A 00 00 00 0C  (legacy: FAZ2 yok)
    adm(0xC1, cdw=(0x80,0,0,0,0x001234FF,1), veri=512,
        gonder=pay(0x82, event, 0x5A, 0x00, 0x00, 0x00, 0x0C))
```

===============================================================================
## G4 — GDP.bin YUKLEME DUZENI (header + chunk dongusu)
===============================================================================
### GDP.bin header (xxd, dogrulandi)
```
0x0000  "MAS09_FWTAG_V001"
0x0010  u16 0x0000
0x0012  u16 nEntries = 0x0002
0x0014  12 x 0xFF
0x0020  16B surum blobu: 00 01 cb 03 00 01 0d 01 e0 7f 01 00 00 00 01 04
0x0030  0x40 x 0xAE dolgu
0x0070  BIN_ENTRY[2]  (16 bayt/kayit)
0x0090..0x0FFF  0xFF dolgu
0x1000  ilk kod parcasi (entry0)
```
**BIN_ENTRY tablosu (@0x70), ham baytlardan cozuldu:**
```
# firstPg lastPg  dwLength    dwOffset(DEST)  dwBinOffset(file)
0  0x0059 0x005B  0x0000C000  0x00000000      0x00001000
1  0x005C 0x0066  0x0002C000  0x040C0000      0x0000D000
```
Kontrol: 0xD000 + 0x2C000 = 0x39000 = 233472 = dosya boyu (OK).
=> **Hedef RAM taban adresi TEK degil; her entry KENDI dest adresini header'da tasiyor**
(`dwOffset` alani, entry+0x08). chunk0 -> 0x00000000, chunk1 -> 0x040C0000.

### chunk0 @ dest 0x00000000 = ARM vektor tablosu (kanit xxd @0x1000)
```
1000: 18 f0 9f e5   LDR PC,[PC,#0x18]   ; Reset  -> lit@0x20 = 0x00000B1C
1004: 18 f0 9f e5   LDR PC,[PC,#0x18]   ; Undef  -> 0x040C013C
1008: 18 f0 9f e5   ; SWI              -> 0x040C0140
100C: 18 f0 9f e5   ; Prefetch abort   -> 0x040C0144
1010: 18 f0 9f e5   ; Data abort       -> 0x040C0148
1014: fe ff ff ea   B .  (rezerve, sonsuz dongu)
1018: 14 f0 9f e5   ; IRQ              -> 0x040C012C
101C: 14 f0 9f e5   ; FIQ              -> 0x040C011C
1020: literal pool: 1c0b0000 3c010c04 40010c04 44010c04 48010c04 2c010c04 1c010c04
```
=> **Giris noktasi = 0x00000000 (ARM reset vektoru), reset handler 0x00000B1C.** Bu yuzden
chunk0 MUTLAKA 0x00000000'a yazilmali; JumpToPRAM adresi payload'da tasimaz (sabit PRAM girisi).
chunk1 @0x040C0000 = Thumb-2 govde (kanit @0xD000: `6e29 22f0 ...` = f0-prefiksli T2). Istisna
handler'lari 0x040C01xx'te = chunk1 bolgesinde. GDP imza dizesi chunk0+0x1C0 = "MKGDP_...COUGAR".

### chunk dongusu (kanit fcn.0x434f9c)
`VP_WriteCodeToMemNew2` her entry icin: `fseek(GDP, dwBinOffset, 0)` (0x4369ef) sonra
`0x434f9c(port, -, FILE, dest=dwOffset, len=dwLength, 0,0,0, verify)` (0x436a92).
0x434f9c ici: `buffer=malloc(len)` (0x434fba), `fread(buffer,1,len,FILE)` (0x434fe6), sonra
**CHUNK dongusu** — legacy dal (`[0x1703de8]==0`, @0x4351ab):
```
CHUNK = 0x10000            ; var_30h = 0x10000  (64 KB)   <-- LEGACY (bizim)
for off in range(0, len, CHUNK):
    n    = min(CHUNK, len-off)
    nsec = ceil(n/512)     ; tam 0x10000 -> 0x80=128 sektor; son parca kesirli
    WriteRam(dest+off, buffer[off:off+n])   ; adres BE, her chunk'ta dest+off
```
(NVMe-mode dal @0x4350a3: CHUNK=0x1000. Bizde gecerli DEGIL.)
=> **chunk0 (0xC000)** = 1 WriteRam, 96 sektor, adr 0x00000000.
=> **chunk1 (0x2C000)** = 3 WriteRam: 128,128,96 sektor -> 0x040C0000, 0x040D0000, 0x040E0000.
Toplam 4 WriteRam cagrisi.

===============================================================================
## G5 — YUKLEME ONCESI / SONRASI ADIMLAR (tam sira)
===============================================================================
`VP_WriteCodeToMemNew2` on-kosullari (kanit 0x4368ff..0x43695f):
1. `VP_IsGDPMode(port)` (0x433b68): zaten GDP modundaysa VE force yoksa -> "GDP mode, no need
   to load GDP" ATLA (return 1). (0x43690f)
2. degilse `VP_IsLoaderMode(port)` (0x433a54): loader modunda DEGILSE ->
   `VP_JumpToLoader(port,1,0)` (0x433794 = JumpToROM 0x83) + `Sleep(1000)` (0x79b010). (0x436937/0x43694a)
3. yukleme (G4). 4. `JumpToPRAM(port, binCount)` (0x424a4c, event=1).

**Vendor tunel enable:** WCM2 ICINDE enable YOK. Enable global/bir-kez: `VC_EnableVendorCmd`
CDW14=**0x00AE34FF** (briefing, canli dogrulanmis). Tunel zaten aciksa tekrar gerekmez.

**Yukleme sonrasi** (ust MP akisi, ANALIZ_MPTOOL.md §5 adim 5-6): JumpToPRAM'den sonra
`VP_InitGDP` -> **InitGDP (sub 0x11)**, sonra `VP_PROC_CheckFlashModule` -> **ReadFlashID
(0x88)** / GetFlashModule (0x05). InitGDP encoding: `FF E5 11` (FAZ1) + faz2-YAZMA param blogu
(1024B DPD/config). InitGDP oncesi enable gerekmez (tunel acik varsayilir).

### TAM SIRA (kopyalanabilir)
```python
import struct
GDP = open("/mnt/mpt/MPT/GDP.bin","rb").read()          # 233472 B
assert GDP[:16]==b"MAS09_FWTAG_V001"
n = struct.unpack_from("<H", GDP, 0x12)[0]              # =2
entries=[]
for i in range(n):
    b=0x70+i*16
    dwLen,dwDest,dwBin = struct.unpack_from("<III", GDP, b+4)
    entries.append((dwDest, dwLen, dwBin))              # [(0,0xC000,0x1000),(0x40C0000,0x2C000,0xD000)]

CHUNK = 0x10000   # legacy 64KB (fcn 0x434f9c @0x4351ab var_30h=0x10000)

def WriteRam(addr, data):
    adm(0xC1, cdw=(0x80,0,0,0,0x001234FF,1), veri=512,
        gonder=pay(0x87, 0x00,(addr>>24)&0xFF,(addr>>16)&0xFF,(addr>>8)&0xFF,addr&0xFF))
    nsec=(len(data)+511)//512; buf=data+b"\x00"*(nsec*512-len(data))
    adm(0xC1, cdw=(nsec<<7,0,0,0,0x00123487,nsec), veri=nsec*512, gonder=buf)

def JumpToPRAM(event=1):
    adm(0xC1, cdw=(0x80,0,0,0,0x001234FF,1), veri=512,
        gonder=pay(0x82, event, 0x5A, 0,0,0, 0x0C))

# 0) (gerekiyorsa) enable: adm(0xC1, cdw=(0,0,0,0,0x00AE34FF,1), veri=4096, gonder=<FF E5 ...>)
# 0b) on-kosul: JD ROM/loader modunda olmali (bizde tel takili => hazir). GDP modundaysa atla.

# 1) GDP.bin'in 2 entry'sini 64KB chunk'larla yukle
for dwDest, dwLen, dwBin in entries:
    data = GDP[dwBin:dwBin+dwLen]
    for off in range(0, dwLen, CHUNK):
        WriteRam(dwDest+off, data[off:off+min(CHUNK, dwLen-off)])

# 2) (OPSIYONEL/DUMMY) RSA blok — GDP.bin[0x400:0x1000] hep 0xFF => ATLA.
#    Byte-birebir istenirse: WriteRamRsa(dest=0x400, GDP[0x400:0x1000], type=0x0A) ama etkisiz.

# 3) yuklenen GDP'ye atla  (ARM reset vektoru @0x00000000)
JumpToPRAM(1)

# 4) sonra: InitGDP(0x11)+param, ReadFlashID(0x88) ... (ANALIZ_MPT_KOMUT_TABLOSU.md)
```

WriteRamRsa (byte-birebir replikasyon isterse, normalde gereksiz):
```python
def WriteRamRsa(addr, data, type_):
    # payload: FF E5 87 <type> <addr BE32>  ; payloadLen 0x10
    adm(0xC1, cdw=(0x80,0,0,0,0x001234FF,1), veri=512,
        gonder=pay(0x87, type_,(addr>>24)&0xFF,(addr>>16)&0xFF,(addr>>8)&0xFF,addr&0xFF))
    nsec=(len(data)+511)//512; buf=data+b"\x00"*(nsec*512-len(data))
    adm(0xC1, cdw=(nsec<<7,0,0,0,0x00123487,nsec), veri=nsec*512, gonder=buf)
```

===============================================================================
## Belirsizler (uydurmuyorum)
===============================================================================
- RSA blogunun (dest 0x400, len 0xC00, type 0x0A) amaci imzali imajlar icin; GDP.bin'de kaynak
  0xFF oldugundan **etkisiz**. Cihazin bunu tolere edip etmedigi statikten cikmiyor -> `?`.
  Guvenli varsayilan: ATLA (2 entry + JumpToPRAM yeterli).
- JumpToPRAM payload[5..8]=0x0000000C sabitinin firmware'ce yorumu (uzunluk mu, mod mu) `?`;
  deger her cagrida sabit 12.
- InitGDP faz2 param blogunun (DPD, Func0@0x98) tam alan haritasi bu binary'de kod-tarafi acik
  degil (dosyadan/DPD.raw'dan geliyor) -> ANALIZ_MPT_AYAR_WP / DPD isinde ayrica ele alinacak.
- `event` (JumpToPRAM) = yuklenen bin sayisi (GDP.bin tek => 1); firmware bunu selektor mu yoksa
  bilgi olarak mi kullaniyor statikten netlesmedi -> 1 kullan.
