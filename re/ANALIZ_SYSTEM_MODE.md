# "The SSD doesn't run on system mode now" — tam çözüm

Tarih: 2026-09-20
Hedef: `FAIL!!! The SSD[52270284] doesn't run on system mode now.` hatasının kök nedeni.

## TL;DR — SONUÇ

**Disk "system mode"da. Araç yanlış yere bakıyor.**

`VP_GetCurrentMode` diskin RAM adres `0x00000000`'ından 4096 bayt okuyup içinde `"MKSSD"`
imzasını arıyor. Bulursa mode = **4** = system mode.

- Bizim disk imzayı **buffer+0x1C0**'ta taşıyor (ölçülmüş, aşağıda kanıt).
- **MXUtility V1_09 ve V1_11** imzayı **buffer+0xC0**'ta arıyor → bulamıyor → mode 1 (Loader)
  sanıyor → hatayı basıyor.
- **Diğer TÜM sürümler** (V0_011, V0.09a, V0_09b, USB_0_05b, MKUtility V0.02,
  MXMPTool V0_01_009d / V0_01_015) **buffer+0x1C0**'ta arıyor → **bizim disk geçer.**

İki çözüm (ikisi de bugün uygulanabilir):

1. **Sıfır riskli:** `MXUtility_MAP1202_V0_011.exe` kullan. Aynı transport, aynı vendor
   paketleri, aynı recovery özellikleri (`EnWriteProtectAbort`, `EnWriteProtectGPIO`,
   `EnPreFormat`, `ClearSmartAttr`). Kontrol +0x1C0'ta → geçer.
2. **Tek-bayt yama:** `MXUtility_MAP1202_V1_11.exe` dosya ofseti **`0x10AA0`**: `0xF0` → `0xF1`.
   Yamalı kopya hazır: `MXUtility_MAP1202_V1_11_sysmode_patch.exe` (aynı dizinde).

---

## 1. Kontrolün tam kod yolu

### 1.1 Hata mesajını basan yer

Binary: `/home/schrodinger/jd1024/araclar_indirilen/extract/usbdev/MXUtility_MAP1202_V1_11/MXUtility_MAP1202_V1_11.exe`
(PE32 GUI, ImageBase 0x400000, `.text` VA 0x401000 / raw 0x600 → `file = vma - 0x400a00`;
`.data` VA 0x6C1000 / raw 0x2BFE00 → `file = vma - 0x401200`)

String: file `0x5085D9`, vma **`0x9097D9`** = `"FAIL!!! The SSD[%d] doesn't run on system mode now."`
Tek xref: `push 0x9097d9` @ vma `0x42B6F4` (file `0x2ACF4`).

Kapsayan fonksiyon: **`0x0042A838`** — debug string'inden adı belli:
`"UpdateInfo bInstance = %d\n"` (0x42a8f5). Yani cihaz tarama / bilgi doldurma rutini;
kullanıcının "%10'da duruyor" dediği yer burası.

Kritik blok (kanıt, capstone x86-32):

```
0042b678  e82358feff     call 0x410ea0
0042b67d  6a01           push 1
0042b67f  6a01           push 1
0042b681  8a951efeffff   mov  dl, byte [ebp-0x1e2]        ; bInstance (port)
0042b687  52             push edx
0042b688  e8f35bfeff     call 0x411280                    ; VP_EnableVendorCmd(port,1,1)
0042b68d  83c40c         add  esp, 0xc
0042b690  84c0           test al, al
0042b692  7546           jne  0x42b6da                    ; OK -> devam
   ; başarısızsa: "FAIL!!! VP_EnableVendorCmd Fail!!!." (0x9097b5)  -> jmp 0x42dbd4

0042b6da  8a8d1efeffff   mov  cl, byte [ebp-0x1e2]        ; port
0042b6e0  51             push ecx
0042b6e1  e84a5dfeff     call 0x411430                    ; VP_GetCurrentMode(port)
0042b6e6  59             pop  ecx
0042b6e7  25ff000000     and  eax, 0xff
0042b6ec  83f804         cmp  eax, 4                      ; <<< SYSTEM MODE == 4
0042b6ef  7459           je   0x42b74a                    ; geçti -> Identify oku, IDFY_C.raw
0042b6f1  ff75e4         push dword [ebp-0x1c]
0042b6f4  68d9979000     push 0x9097d9                    ; "...doesn't run on system mode now."
0042b6f9  8d55dc         lea  edx, [ebp-0x24]
0042b6fd  e81677ffff     call 0x422e18                    ; sprintf(UnicodeString&, fmt, ...)
   ...
0042b745  e98a240000     jmp  0x42dbd4                    ; fonksiyondan çık
```

`0x411430`'un **tek** çağrı yeri budur (tüm `.text` `e8 rel32` taraması yapıldı → 1 call site).
Yani gate tekil; başka gizli "system mode" kontrolü yok.

Mesaj basıldıktan sonra `jmp 0x42dbd4` ile fonksiyon sonlanıyor; geçerse `0x42b74a`'da
`0x4111dc(port, buf, 1)` → Identify Controller okunup `IDFY_C.raw` yazılıyor ve akış devam ediyor.

### 1.2 `VP_GetCurrentMode` @ `0x00411430` — kontrolün kendisi

```
00411430  55                 push ebp
00411431  8bec               mov  ebp, esp
00411433  81c404f0ffff       add  esp, 0xfffff004          ; 4 KB yerel tampon
...
00411451  8dbddcefffff       lea  edi, [ebp-0x1024]        ; buf = ebp-0x1024
00411457  b900040000         mov  ecx, 0x400
0041145c  f3a5               rep  movsd                     ; 0x75de84'ten 0x1000 bayt (hemen üzerine yazılıyor)
0041145e  6800100000         push 0x1000
00411463  6a00               push 0
00411465  8d85dcefffff       lea  eax, [ebp-0x1024]
0041146b  50                 push eax
0041146c  e862d62900         call 0x6aead3                  ; memset(buf, 0, 0x1000)

00411474  6a01               push 1                         ; arg5 (kullanılmıyor, bkz. §3)
00411476  6a00               push 0                         ; arg4 = RAM ADRESİ = 0x00000000
00411478  6a08               push 8                         ; arg3 = 8 sektör = 4096 bayt
0041147a  8d95dcefffff       lea  edx, [ebp-0x1024]
00411480  52                 push edx                       ; arg2 = buf
00411481  8a4d08             mov  cl, byte [ebp+8]
00411484  51                 push ecx                       ; arg1 = port
00411485  e81aeeffff         call 0x4102a4                  ; VC_LDR_CmdReadRam
0041148a  83c414             add  esp, 0x14
0041148d  83f801             cmp  eax, 1
00411490  0f8532010000       jne  0x4115c8                  ; -> mode 0, "VC_LDR_CmdReadRam fail!"

00411496  6a05               push 5
00411498  688ba28100         push 0x81a28b                  ; "MKSSD"
0041149d  8d859cf0ffff       lea  eax, [ebp-0xf64]          ; <<<<< buf + 0xC0
004114a3  50                 push eax
004114a4  e8f3d32900         call 0x6ae89c                  ; memcmp
004114ac  85c0               test eax, eax
004114ae  753c               jne  0x4114ec
   ; eşitse: "[%d]VP_GetCurrentMode is SYS FW"
004114ce  c604853ebbf50004   mov  byte [eax*4+0xf5bb3e], 4  ; cache[port] = 4
004114d6  b004               mov  al, 4                     ; return 4   <<< SYSTEM MODE

004114ec  6a05               push 5
004114ee  68bea28100         push 0x81a2be                  ; "MKGDP"
004114f3  8d8d9cf1ffff       lea  ecx, [ebp-0xe64]          ; buf + 0x1C0
   ... eşitse mode = 2 ("is GDP")

00411542  6a05               push 5
00411544  68eea28100         push 0x81a2ee                  ; "MKRDT"
00411549  8d8d9cf1ffff       lea  ecx, [ebp-0xe64]          ; buf + 0x1C0
   ... eşitse mode = 3 ("is RDT")

00411592  ...                                               ; hiçbiri değilse
00411598  68 1ea38100        push 0x81a31e                  ; "[%d]VP_GetCurrentMode is Loader"
004115b0  c604953ebbf50001   mov  byte [edx*4+0xf5bb3e], 1
004115b8  b001               mov  al, 1                     ; return 1   <<< BİZİM DİSKİN DÜŞTÜĞÜ YER
```

Ofset aritmetiği: `buf = ebp-0x1024`.
`0x1024-0xF64 = 0xC0` · `0x1024-0xE64 = 0x1C0`.

### 1.3 Mode sabitleri (firmware'in değil, ARACIN tanımı)

| değer | anlam | nasıl tespit ediliyor |
|---|---|---|
| 0 | okunamadı | `VC_LDR_CmdReadRam` başarısız |
| 1 | Loader | hiçbir imza tutmadı (fallback) |
| 2 | GDP | `buf+0x1C0 == "MKGDP"` |
| 3 | RDT | `buf+0x1C0 == "MKRDT"` |
| **4** | **SYS FW = "system mode"** | `buf+0xC0 == "MKSSD"` (V1_09/V1_11) / `buf+0x1C0 == "MKSSD"` (diğerleri) |

Cache: `ds:0xF5BB3E + port*0xC5*4` (V1_11).

**Bu kontrolün `0x00810CE8`'deki `mod=4` write-protect değişkeniyle HİÇBİR İLGİSİ YOK.**
Sayısal olarak ikisi de 4 ama tamamen farklı şeyler: biri firmware'in iç WP state'i,
diğeri aracın "hangi imaj koşuyor" sınıflandırması. Aynı sayı olması tesadüf.

---

## 2. Gönderilen komut — bayt seviyesinde

`VC_LDR_CmdReadRam` @ `0x004102A4` (V1_11). Paket kurulumu:

```
004102c7  c68500f0ffffff   mov byte [buf+0], 0xFF
004102ce  c68501f0ffffe5   mov byte [buf+1], 0xE5
004102d5  803d01eaf90000   cmp byte [0xf9ea01], 0        ; EnNvmeCmdMode
004102dc  7409             je  0x4102e7
004102de  c68502f0ffffd1   mov byte [buf+2], 0xD1        ; bridge/miniport yolu
004102e5  eb07             jmp 0x4102ee
004102e7  c68502f0ffff86   mov byte [buf+2], 0x86        ; plain-NVMe yolu  <<< BİZİM YOL
004102ee  c68503f0ffff00   mov byte [buf+3], 0x00
004102f5..0041031c         buf[4..7] = ramAddr big-endian (>>24, >>16, >>8, &0xFF)
```

Sonra `VC_VendorCmd(port, packet, payloadLen=0x0C, pBuf, sectors, bIsRead=1, maxLen=0x1000, extra)`.

**Tel üzerindeki gerçek istek:**

```
faz-1 (komut):  NVMe opcode 0xC1, CDW14 = 0x001234FF, CDW15 = 1, CDW10 = 0x80
                512 bayt veri, ilk 12 baytı:
                FF E5 86 00 00 00 00 00 00 00 00 00
                          ^^ ^^ ^^^^^^^^^^^
                          |  |  RAM adresi = 0x00000000 (big-endian)
                          |  +-- sabit 0
                          +----- cmd = 0x86 = LDR_ReadRam

faz-2 (veri):   4096 bayt data-in (8 sektör)
```

Beklenen cevap: **4096 baytlık RAM dump'ı; +0xC0 (V1_11) ya da +0x1C0 (diğerleri) ofsetinde
ASCII `"MKSSD"` (5 bayt).**

Not: `VP_EnableVendorCmd` (CDW14 = `0x00AE34FF`) zaten geçiyor — hata mesajının kendisi bunun
kanıtı, çünkü EnableVendorCmd başarısız olsa farklı string basılırdı (`0x9097b5`).

---

## 3. "V1_11 farklı bir şey okuyor olabilir mi?" — ELENDİ

V1_11'in `VC_LDR_CmdReadRam`'i eski sürümlere göre **bir fazla argüman** alıyor
(`add esp,0x20` vs `add esp,0x1c`). Bu 8. argüman veriyi kaydırıyor olabilir miydi?

Hayır. `VC_VendorCmd` @ `0x0040FD48` gövdesi `0x40FD48`–`0x4102A0` (ret @ `0x4102A0`).
Bu aralıkta `[ebp+0x24]`'e **hiç erişilmiyor** (tam fonksiyon disasm'ı tarandı, 0 hit).
Ölü parametre. Paket kurulumu V0_011 (`0x4093E4`) ile **bayt bayt aynı**:

```
V0_011 @0x409407: mov byte [buf+0],0xFF ; [buf+1],0xE5 ; [0x15e6c14]?0xD1:0x86 ; [buf+3],0
                  buf[4..7] = addr BE  ->  call 0x408da0 (7 arg)
V1_11  @0x4102C7: aynı                 ->  call 0x40fd48 (8 arg, 8.si kullanılmıyor)
```

Yani iki sürüm **aynı 4096 baytı** alıyor, sadece **farklı ofsette** karşılaştırıyor.

---

## 4. Diskin gerçek durumu — ÖLÇÜLMÜŞ KANIT

`/home/schrodinger/jd1024/re/fw_canli/e00_0x00000000.bin` = 0x86 ReadRam ile canlı diskten
okunmuş RAM adres 0 dump'ı (98304 bayt).

```
000000c0: 0000 0000 0000 0000 0000 0000 0000 0000   <-- V1_11 buraya bakıyor: BOŞ
000000d0: 4b1e 0210 4b1e 0210 4b1e 0210 02aa 00ff
...
00000160: 6665 6e67 5f71 696e                       "feng_qin"
00000180: 723a 2f63 6f64 655f 7265 6c65 6173 652f   "r:/code_release/"
00000190: 4879 6e69 7876 362f 436f 7567 6172 5f48   "Hynixv6/Cougar_H"
000001a0: 796e 6978 5f76 365f 3132 3436 3300 0000   "ynix_v6_12463"
000001c0: 4d4b 5353 445f 3530 3130 3033 3030 3031   "MKSSD_5010030001   <-- İMZA BURADA
000001d0: 3234 3632 3030 3030 2c4f 6374 2033 3120    24620000,Oct 31
000001e0: 3230 3233 2c30 393a 3339 3a33 322c 4d41    2023,09:39:32,MA
000001f0: 5031 3230 322c 5a49 3050 4344 3243 0000    P1202,ZI0PCD2C"
```

Tam imza: `MKSSD_50100300012462000 0,Oct 31 2023,09:39:32,MAP1202,ZI0PCD2C`
Ayrıca +0x60'ta `MX_0123456789 Maxiotech_MAP1002_NVMe_SSD SVN12462MAX`.

→ **Disk SYS FW koşuyor. Mode 4. Sistem modunda.** V1_11'in kontrolü sadece 0x100 bayt şaşıyor.

### Neden iki farklı ofset var — firmware kuşak farkı

`araclar_indirilen/extract` altındaki **tüm** firmware `.bin`'lerinde `MKSSD`'nin dosya
ofseti tarandı (`grep -abo MKSSD`; imaj verisi `binOff 0x1000`'de başlıyor):

| dosya ofseti | imaj içi ofset | adet | kuşak |
|---|---|---|---|
| 4544 = 0x11C0 | **+0x1C0** | 109 | `MKSSD_5010xxxx...` 2022–2023 (**bizimki**) |
| 4288 = 0x10C0 | **+0xC0**  | 11 | `MKSSD_1010xxxx...` 2024+ |
| 768 = 0x300 | – | 898 | MK8115, alakasız kontrolcü |

+0xC0 kuşağı örnekleri:
- `usbdev/MAP1202_H25TXTD2XCX6/.../SYS/YIC5CA1C.bin` → `MKSSD_101000000266373100,Nov 27 2024,...`
- `usbdev/MAP1202-N38B-SN19515/.../MPT/SYS/KCIUCA2H.bin` → `MKSSD_101000000195153100,Mar 28 2024,...`
- `usbdev/MAP1202-N4PA-SN26904/.../MPT/SYS/MCB6AA2H.bin` → `MKSSD_101000000269043100,Dec 13 2024,...`

MAXIO 2024'te firmware imaj başlığını değiştirmiş, imza 0x100 bayt öne kaymış.
V1_09/V1_11 yeni kuşağa göre derlenmiş ve **eski kuşak desteğini düşürmüş** (fallback yok,
sadece tek offset deniyor). Bizim disk 2023 kuşağı → yeni araç tanımıyor.

---

## 5. Sürüm matrisi — hangi araç nereye bakıyor

Otomatik tarama (`MKSSD` string xref → fonksiyon başı → `lea [ebp-X]` displacement'ı,
buffer tabanı her sürümde `ebp-0x1024`):

| exe | fonksiyon | MKSSD | MKGDP | MKRDT | bizim disk |
|---|---|---|---|---|---|
| MXUtility_MAP1202_V1_11 | 0x411430 | **+0xC0** | +0x1C0 | +0x1C0 | ❌ FAIL |
| MXUtility_MAP1202_V1_09 | 0x4114F4 | **+0xC0** | +0x1C0 | +0x1C0 | ❌ FAIL |
| MXUtility_MAP1202_V0_011 | 0x40A5C4 | **+0x1C0** | +0x1C0 | +0x1C0 | ✅ GEÇER |
| MXUtility_MAP1202_V0.09a | 0x4093F4 | +0x1C0 | +0x1C0 | +0x1C0 | ✅ GEÇER |
| MXUtility_MAP1202_V0_09b | 0x40A550 | +0x1C0 | +0x1C0 | +0x1C0 | ✅ GEÇER |
| MXUtility_MAP1202_USB_0_05b | 0x407934 | +0x1C0 | +0x1C0 | +0x1C0 | ✅ GEÇER |
| MKUtility_MAP1202_USB_V0.02 | 0x40679C | +0x1C0 | +0x1C0 | +0x1C0 | ✅ GEÇER |
| MXMPTool_MAP1202_USB_V0_01_009d | 0x42F0D4 | +0x1C0 | +0x1C0 | +0x1C0 | ✅ GEÇER |
| MXMPTool_MAP1202_USB_V0_01_015 | 0x433B24 | +0x1C0 | +0x1C0 | +0x1C0 | ✅ GEÇER |

Hepsinde `ReadRam(port, buf, sectors=8, ramAddr=0)` ve paket `FF E5 86 00 00 00 00 00`.

---

## 6. ÇÖZÜM A — eski araç (risksiz, önerilen ilk deneme)

```
/home/schrodinger/jd1024/araclar_indirilen/extract/usbdev/MXUtility_MAP1202_V0_011/MXUtility_MAP1202_V0_011.exe
```

V0_011, +0x1C0 ailesinin en yenisi. Uyumluluk doğrulandı:
- Aynı transport string'leri: `\\.\PhysicalDrive%d`, `\\.\Scsi%d:`, `EnNvmeCmdMode`,
  `NvmeIntelVMDCmd`, `FIRMWARE` SRB. Yani aynı Win10 NVMe passthrough yolu.
- Aynı vendor paket kurulumu (`FF E5 86 ...`), aynı `0xC1` opcode ailesi.
- Aynı kurtarma özellikleri: `EnWriteProtectAbort`, `EnWriteProtectGPIO`, `EnPreFormat`,
  `EnClearSMART`, `ClearSmartAttr Port(%d)`, `VP_PROC_Preformat - Mode %d`.

V1_11'de fazladan olan tek şey `EnDisplayClearSMART` / `VP_PROC_ClearSMARTInfo` (kozmetik).

## 7. ÇÖZÜM B — tek-bayt yama

`lea eax,[ebp-0xF64]` (buf+0xC0) → `lea eax,[ebp-0xE64]` (buf+0x1C0).
Sadece displacement'ın 4. baytı değişiyor.

| exe | instr VMA | file offset | eski | yeni |
|---|---|---|---|---|
| MXUtility_MAP1202_V1_11.exe | 0x0041149D | **0x10AA0** | `F0` | `F1` |
| MXUtility_MAP1202_V1_09.exe | 0x00411561 | **0x10B64** | `F0` | `F1` |

```
8d 85 9c f0 ff ff   lea eax, [ebp - 0xf64]     ; buf+0xC0   (orijinal)
8d 85 9c f1 ff ff   lea eax, [ebp - 0xe64]     ; buf+0x1C0  (yamalı)
```

Güvenlik kontrolleri yapıldı:
- Authenticode SECURITY directory **boş** (rva=0, size=0) → imza yok, bozulacak bir şey yok.
- PE `CheckSum` alanı **0** → Windows loader zaten doğrulamıyor (sadece driver'larda şart).
- Base relocation tablosu tarandı: `0x41149D..0x4114A3` aralığını kapsayan **reloc yok**
  (ebp-relative displacement, mutlak adres değil) → yama güvenli.
- `VP_GetCurrentMode`'un tek çağrı yeri var → yan etki yok.

Hazır yamalı kopya (üretildi ve doğrulandı):

```
/home/schrodinger/jd1024/araclar_indirilen/extract/usbdev/MXUtility_MAP1202_V1_11/MXUtility_MAP1202_V1_11_sysmode_patch.exe

md5 orijinal: d31c98a30f7d6b7a175c5a35c0b2b2a7
md5 yamalı  : ec626e608534ef9ae351d13b97f6cf4a
cmp -l      : tek fark -> bayt 68257 (1-based, = 0x10AA0): 360 -> 361 (oktal) = 0xF0 -> 0xF1
```

Yamalı disasm doğrulandı:
```
00411498  688ba28100      push 0x81a28b            ; "MKSSD"
0041149d  8d859cf1ffff    lea  eax, [ebp - 0xe64]  ; buf+0x1C0  <-- yeni
```

---

## 8. "Diski system mode'a SOKMA" komutu var mı?

**Aracın kendisinde yok** — çünkü buna gerek yok, disk zaten o modda.

MXUtility (V0_011 ve V1_11) `VP_JumpToSystem` debug string'lerini `.data`'da taşıyor ama
**hiçbiri koddan referans edilmiyor** (`0x81a0d8`, `0x81a0f9`, `0x820f1d` için tüm dosyada
4-bayt adres araması → 0 hit). Yani MXUtility'de o fonksiyon linklenmemiş.

`VP_JumpToSystem` sadece **MPTool**'da canlı — `MXMPTool_MAP1202_USB_V0_01_009d.exe` @ `0x0042EDC4`:

```
0042eddd  mov byte [ebp-1], 1
0042ede5  call 0x42eeac(port)          ; IsGDPMode? gibi
0042edf3  call 0x42efc0(port)          ; IsRDTMode? gibi
   ; ikisi de false ise -> zaten system'dasın, 1 döndür
0042ee09  call 0x42ebec(port,0,0)      ; VP_JumpToLoader ("VP_JumpToLoader - Event %d")
0042ee1f  call Sleep(0x5DC = 1500 ms)
0042ee2d  call 0x42ea28(port, arg2, 1) ; firmware'i indir/boot et
0042ee4b  call 0x42f0d4(port)          ; VP_GetCurrentMode
0042ee55  cmp  ecx, 4                  ; yine 4 bekliyor
```

Yani "system mode'a geçiş" = **loader'a düş → SYS firmware'i NAND'dan/dosyadan yükle → boot et**.
Kısa yol / tek vendor komut ("enter system mode") **YOK**. Ve bu yol bizim için hem gereksiz
hem tehlikeli: `VP_JumpToLoader` diski ROM/loader moduna atar, oradan geri dönmek için
firmware yazmak gerekir — `0x87 WriteRam` bizim diskte çalışmıyor
(bkz. `ANALIZ_FW_FLASH.md`, canlı tarama: sadece `0x86` cevap veriyor).

**Kesinlikle denenmemeli.**

---

## 9. `52270284` sayısı ne?

**Araç bug'ı. Anlamlı bir ID değil — bir heap adresi.**

`0x42B6F1: push dword [ebp-0x1c]` ile `%d` formatına basılan değer bir `UnicodeString`
nesnesinin iç pointer'ı. `[ebp-0x1c]`'nin fonksiyondaki **tüm** kullanımları:

| vma | kullanım |
|---|---|
| 0x42AA2B | `lea edx,[ebp-0x1c]; call 0x4154B4` — string ctor/init |
| 0x42AAC3 | `lea eax,[ebp-0x1c]; call 0x4155A4` — `operator=`, kaynak: `0x42DCE0(dst, [instance*0x314 + 0xF5B9D4])` |
| 0x42ABE3 | `lea edx,[ebp-0x1c]; call 0x415614` — string `operator+` |
| 0x42AEB6 | `lea eax,[ebp-0x1c]; call 0x415614` — string `operator+` |
| 0x42B6F1 | `push dword [ebp-0x1c]` — **değerle** push (pointer) |

`0x42DCE0` içi: `sprintf(UnicodeString&, "%lu", value)` (format string `0x90A272 = "%lu"`).
Yani `[ebp-0x1c]` bir **string**; `%d` ile basılınca pointer'ın kendisi yazdırılıyor.
`52270284 = 0x031D4B8C` → 32-bit process heap adresi.

Niyet `"The SSD[<sürücü no>]"` idi (`%s` olmalıydı). Sayı **tamamen anlamsız**, her
çalıştırmada değişir. Seri no / SSD index / hash DEĞİL.

---

## 10. Doğrulanmamış / bilinmeyen

- Gate geçildikten **sonra** aracın hangi işlemleri başarıyla yapabileceği test edilmedi.
  Bu analiz sadece 10%'daki bloğu açıklar. Disk `mod=4` write-protect'te olduğu için
  `EnWriteProtectAbort` / `Preformat` yollarının firmware tarafında nasıl karşılanacağı ayrı iş.
- V1_11'in +0xC0 kontrolünün MAXIO tarafında "bilinçli kuşak kesme" mi yoksa regresyon mu
  olduğu bilinmiyor — dışarıdan ayırt edilemez. Pratik sonuç aynı.
- Yamalı exe Windows PE VM'de **çalıştırılmadı** (bu makinede Windows yok). Yama statik
  olarak doğrulandı (tek bayt, doğru disasm, reloc/imza/checksum temiz); çalışma zamanı
  davranışı Alperen'in testine bağlı.

---

## Ek: kullanılan araçlar

r2 yok; capstone 5.0.7 ile elle PE32 parser + disassembler yazıldı:
`/tmp/claude-1000/-home-schrodinger/f9e2f0fd-89cc-4aae-8b79-57025378141b/scratchpad/`
(`d.py` = vma-bazlı disasm + string annotation, `findstart.py` = fonksiyon başı bulma,
`xref.py` = string xref, `scanmode2.py` = sürüm matrisi çıkarıcı)
