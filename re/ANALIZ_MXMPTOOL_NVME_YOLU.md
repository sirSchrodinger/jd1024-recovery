# MXMPTool_MAP1202_PCIe — adaptörsüz (native NVMe / vfio-PCIe) tarama yolu analizi

Tarih: 2026-09-20
Soru: **MXMPTool_MAP1202_PCIe_A.exe**, bir MAP1202 SSD'yi USB bridge OLMADAN, MXUtility'nin
kullandığı gibi native **NVMe PhysicalDrive** (vfio-PCIe) olarak keşfedip SCAN/MP/SORT/RDT
yapabilir mi?

Ortam: kaplikaya, r2/radare2 5.5.0, READ-ONLY statik disasm. Her iddia adresle. `[K]`=binary'den
kanıtlı, `[H]`=hipotez/çıkarım.

Analiz edilen dosyalar (kaplikaya):
- `~/jd1024/vm/mpt_yama/MXMPTool_MAP1202_PCIe_A.exe`  (md5 `aad8436a79d72cd2057b0f58fed4bfa7`)
- `~/jd1024/vm/mpt_yama/MXMPTool_MAP1202_PCIe_B.exe`  (md5 `8e006cb60d0d75d0a1be17752fc92636`)
- `~/jd1024/vm/mpt_yama/MXMPTool_MAP1202_USB_V0_01_017.ORIGINAL.exe`  (ikisinin de temeli)
- `~/jd1024/kanit/fw_hunt4/ex/.../MPT/MXMPSORT_MAS090x_V2.exe`  (bonus)

PE haritası (rabin2 -S): `.text` VA 0x401000–0x79c000 (kod), `.data` VA 0x79c000+ (stringler
0x7f7ac4/0x811839/0x8a62f4/0x920857 burada). Overlay+.rsrc packed değil (lsyms/linenum true,
Delphi/C++ statik link). `file_off → VA`: `.text` için `VA = fileoff + 0x400A00`. `[K]`

---

## 0. TL;DR — kesin cevap

**EVET.** MXMPTool'un keşif, cihaz-açma ve vendor-komut transport'unun tamamı native
NVMe/PhysicalDrive'dır — MXUtility ile **birebir aynı** — ve USB bridge GEREKMEZ. Önceki
ajanın "USB-only" sonucu **yanlış**: yanıltıcı string isimlerine (`EnumUSBDevice`,
`TotalUSBPortCount`) dayanıyor; oysa gerçek enumerator **GUID_DEVINTERFACE_DISK** ile TÜM
fiziksel diskleri (SATA/USB/NVMe) tarıyor.

**En güçlü tek kanıt:** Keşif fonksiyonu `fcn.00404ffc`, `SetupDiGetClassDevs`'i (call @
0x40508f, `0x79abf6`) **ClassGuid = ptr 0x79ee4c** ile çağırıyor. 0x79ee4c'deki 16 bayt =
`07 63 f5 53 bf b6 d0 11 94 f2 00 a0 c9 1e fb 8b` = **{53F56307-B6BF-11D0-94F2-00A0C91EFB8B}
= GUID_DEVINTERFACE_DISK** `[K]`. Bu, USB değil DİSK arayüz sınıfıdır → native NVMe diskler
de listeye girer.

**Seçim mekanizması tek bir "NVMe mode" anahtarı DEĞİL; üç ayrı katman:**
1. **Keşif** zaten PhysicalDrive/DISK-class — USB'ye özel değil, seçilecek bir şey yok. `[K]`
2. **Transport encoding+IOCTL** = ini key **`EnNvmeCmdMode`** ([Setting]) → byte `[0x1703de8]`.
   `0` → `IOCTL_STORAGE_PROTOCOL_COMMAND` (0x2d1400, native NVMe passthrough — istediğimiz,
   default). `1` → `IOCTL_SCSI_MINIPORT`+`"FIRMWARE"` SRB (0x4d008 / ctl 0x1b0780, bridge/
   miniport). `[K]`
3. **Gerçek engel** = cihaz-kabul FILTER'ı (`fcn.0047a958` içinde). Native (USB-bridge'siz)
   MAP1202 diskini bu filter eliyor. **A/B binary yamaları tam bu filter'ı devre dışı bırakıyor.**
   ini'den kapatılamaz; kod yaması şart. `[K]`

`ToolMode` (byte `[0x16f2516]`) transport DEĞİL; operating-mode/UI seçici (MPT/SORT/RDT/panel).

**Diskin hangi modda olması gerektiği:** SCAN + identify için product/system mode (mod=4)
native NVMe üzerinden yeterli olmalı — MXUtility bunu zaten yapıyor. Gerçek MP/SORT/RDT NAND
işlemleri için disk, aracın beklediği GDP/loader moduna alınmalı (adaptör sorusundan bağımsız,
her MP akışının ortak gereği). `[H]`

---

## 1. Patch anatomisi — "PCIe" yamaları ne yapıyor (cmp -l + disasm)

Üç binary de **6494840 bayt, aynı boy**. A ve B, USB orijinalinin bayt-yamaları:

**USB-ORIGINAL → PCIe_A: 16 bayt fark** (`cmp -l`): 2'si PE header (file 0x258–0x259,
checksum), 14'ü kod. Kod yamaları (`fcn.0047a958` cihaz-kabul döngüsü içinde):

- **VA 0x47AA25:** `83 38 01  0F 85 4D020000` = `cmp dword [eax],1 ; jne 0x47ac7b`
  → yamalı `C7 00 01000000  90 90 90` = **`mov dword [eax],1 ; nop×3`**.
  Yani "field0 != 1 ise cihazı ATLA" kontrolü kaldırılıp field0 **zorla 1** yapılıyor. `[K]`
- **VA 0x47AAAE:** `0F 85 14010000` = `jne 0x47abc8` → **`90×6`** (nop). deviceDesc
  eşleşmesinden sonraki ikinci "reddet" dalı kaldırılıyor. `[K]`

**PCIe_B: A'nın iki yaması + bir fazlası** (USB→B = 21 bayt; A→B = 7 bayt):
- **VA 0x47AB39:** `E8 BEABF8FF` = `call 0x4056fc` → **`B8 FFFF0000`** = `mov eax,0xFFFF`.
  `0x4056fc` = PhysicalDrive'ı açıp vendor probe atan yardımcı (aşağıda). Dönüş değeri hemen
  `mov [ecx+0xc],eax` (0x47ab42) ile `pPortDevInfo+0xc`'ye yazılıyor; bu alan 0x47abda'da
  `cmp [edx+0xc],0 ; je 0x47ac56` ile cihazın eklenip eklenmeyeceğini belirliyor. B, probe'u
  **atlayıp** sonucu sabit `0xFFFF` (non-zero) yaparak cihazı **koşulsuz** kabul ettiriyor. `[K]`

**Yorum:** A = deviceDesc/type filtresini kaldırır ama gerçek vendor probe'u (0x4056fc)
KORUR → cihaz DISK-class'tan gelir, native NVMe ile prob edilir, prob başarılıysa eklenir.
B = ek olarak probe'u da stub'lar → prob başarısız/timeout olsa bile cihaz eklenir. B'nin
varlığı, patcher'ın probe'un hedefte takıldığını gözlemleyip zorladığına işaret. `[H]`

---

## 2. Keşif/SCAN yolu — buton'dan PhysicalDrive'a tam xref zinciri `[K]`

Canlı SCAN handler ve zinciri (`aac` + `axt` ile doğrulandı):

```
[UI buton/timer] fcn.00449f54 (0x44a138,0x44a5b1) · fcn.0047a81c (0x47a860) · fcn.004b1ba4 (0x4b1c28)
   └─> fcn.0047ac98  = SCAN/DETECT handler
         0x47acc5  log "######### - EnumUSBDevice"          (isim yanıltıcı — bkz. GUID)
         0x47 acd9  CreateFile "MKMPAcess"  → handle 0x176af9c   (opsiyonel MAXIO sürücüsü;
                    açılış 0 dönerse "cmp/jne continue" ile TOLERE edilir, akış durmaz)
         0x47ad2a  call fcn.0047a958                          ; << enumerate + FILTER
         0x47ad2f  mov [0x8a62f4], eax                        ; g_nPortConnectedNum = sonuç
         0x47ad34  log "g_nPortConnectedNum = %d"
         0x47ad76  cmp [0x8a62f4],0 ; je 0x47b4fb             ; 0 ise → panel'i boş göster
         0x47ae10  cmp [0x16f2516],0 ...                      ; ToolMode: sadece device-type 6/5 seçimi (UI)
```

`fcn.0047a958` (enumerate + kabul filter'ı — **A/B'nin yamaladığı fonksiyon**):
```
0x47a965  call fcn.0045d884                        ; deviceCount (enumerator wrapper)
0x47a97f  mov [0x8a62f8],0
0x47a99e  log "System disk is %c"                  ; boot diskini dışlamak için
          … her cihaz (ii=[ebp-0x10]) için:
0x47aa25  cmp [pPortDevInfo],1 ; jne skip          ; << A: mov [..],1 (filter kaldırıldı)
0x47aa64  log "pPortDevInfo->deviceDesc is %s"
0x47aa8f  call 0x404e58(deviceDesc) ; call 0x77b7d8 ; deviceDesc eşleştirme
0x47aaae  jne 0x47abc8                             ; << A: nop×6 (ikinci reddet kaldırıldı)
0x47ab39  call fcn.004056fc → [pPortDevInfo+0xc]   ; << B: mov eax,0xFFFF (probe stub)
0x47ab1e  mov byte [ecx*8+0xec80ec],1              ; port-aktif flag
0x47abbf  mov [ebx*8+0xec80e8], (pPortDevInfo+0x10c) ; port→PhysicalDrive tablosu
```

`fcn.0045d884` (enumerator wrapper):
```
0x45d897  memset(0x176afa4, 0, 0x1d000)            ; 128 slotluk DevInfo dizisi
0x45d8a3  call fcn.00406650 → [0x8a62f0]           ; "TotalUSBPortCount = %d" (isim yanıltıcı)
0x45d8e7  call fcn.00404ffc(0x1709960, &count)     ; << ASIL keşif
```

`fcn.00404ffc` (asıl enumerator):
```
0x405018  CreateFile "JMUSBAcess" → 0x79c954       ; JMicron sürücüsü (opsiyonel; 0 dönerse
                                                     tekrar dener, sonra yine de devam eder)
0x40508a  push 0x79ee4c (ClassGuid) ; ... ; Flags 0x12 (DIGCF_PRESENT|DIGCF_DEVICEINTERFACE)
0x40508f  call 0x79abf6                            ; = SetupDiGetClassDevs
0x4050d1  call 0x79abfc  (döngü)                   ; = SetupDiEnumDeviceInterfaces
```

**ClassGuid @ 0x79ee4c = {53F56307-B6BF-11D0-94F2-00A0C91EFB8B} = GUID_DEVINTERFACE_DISK.** `[K]`
→ Enumerator TÜM fiziksel diskleri (bus tipinden bağımsız: SATA/USB/NVMe) tarar. JMUSBAcess ve
MKMPAcess yardımcı sürücü handle'larıdır (JMicron/MAXIO); açılış başarısızlığı tolere edilir,
ANA veri yolu bunlar DEĞİL. `[K]`

---

## 3. Cihaz açma + transport = native NVMe PhysicalDrive (MXUtility ile aynı) `[K]`

Kabul edilen her port için PhysicalDrive numarası `[0xec80e8 + port*0x2066*8]` tablosuna yazılıyor
(yukarıda filter tarafından). Açma katmanı:

`fcn.004269c4` (GetPhysicalDriver): 
```
0x4269d8  mov ecx, [edx*8 + 0xec80e8]              ; port→drive number (filter'ın yazdığı)
0x4269f1  sprintf(buf, "\\.\PhysicalDrive%d", n)   ; 0x7f7ab0
0x426a0c  log "######### - GetPhysicalDriver = %s" ; 0x7f7ac4
```
Çağıran: `fcn.00426ba8` (0x426c1f) — bu da `fcn.004056fc` (0x4057cd/0x405873) ve `fcn.004335d0`
tarafından çağrılıyor. `fcn.00426ba8` `\\.\PhysicalDrive%d` (0x7f7bd5) açıp "devPhyFileName %s"
logluyor. `[K]`

Vendor komut gönderimi — `NVMeVendorCmdWrite fcn.00403884`:
```
0x4038a8  CreateFile(devPath, GENERIC_RW 0xc0000000)
0x4038d8  DeviceIoControl(h, 0x2d1080 = IOCTL_STORAGE_GET_DEVICE_NUMBER) → diskNumber.DeviceNumber
0x403941  sprintf "\\.\PHYSICALDRIVE%d" ile yeniden aç
   … (gönderim, EnNvmeCmdMode'a göre):
```
`fcn.00403040` bloğu (native NVMe passthrough gönderimi):
```
0x40306b  push 0x2d1400                            ; IOCTL_STORAGE_PROTOCOL_COMMAND
0x403070  push [ebp-4]                             ; \\.\PhysicalDrive handle
0x403073  call 0x79acce                            ; DeviceIoControl
```
`[K]` Bu, MXUtility'nin çalışan yoluyla **birebir aynı**: `\\.\PhysicalDrive` + NVMe passthrough.

Alternatif (EnNvmeCmdMode=1): SCSI miniport — `0x4d008 = IOCTL_SCSI_MINIPORT` (0x4040f3, 0x404312,
0x404564, 0x404836, 0x404ac7, 0x404d27) + `0x1b0780` FIRMWARE ctl (0x404c03). `[K]`

---

## 4. Seçim mekanizmaları — adreslerle

### 4.1 `EnNvmeCmdMode` — transport encoding + IOCTL (keşif DEĞİL)
ini okuma (config loader): `push "EnNvmeCmdMode"(0x811839) ; push "Setting"(0x811831) ;
call 0x429e04 ; mov byte [0x1703de8], al` @ 0x42aacd–0x42aadf. `[K]`
Runtime byte `[0x1703de8]` 20+ yerde test ediliyor (0x416040, 0x424181, 0x4244ef, 0x424ae3,
0x424baf, 0x424c90, … 0x425fe7 …) — her vendor komutta encoding (0x86↔0xD1, 0x3B↔0xD5, 0x88↔…)
VE IOCTL (0x2d1400 ↔ 0x4d008/0x1b0780) seçimi. `[K]`

**Önceki iddia doğrulama:** "EnNvmeCmdMode yalnız command ENCODING'ini değiştirir, keşfi değil"
→ **kısmen düzeltiliyor:** hem encoding'i hem IOCTL transport'unu değiştirir; keşfi gerçekten
değiştirmez (keşif zaten DISK-class). Ama bundan "araç USB keşfeder" sonucu çıkmaz — çıkarılmıştı,
**yanlıştı.** İstediğimiz native yol için **EnNvmeCmdMode=0** (default).

### 4.2 `ToolMode` — operating/UI mode (transport DEĞİL)
`push "ToolMode"(0x811527) ; push "Setting"(0x81151f) ; call 0x429e04 ; mov byte [0x16f2516], al`
@ 0x42a743–0x42a755. `[K]` Byte `[0x16f2516]` 53+ yerde kullanılıyor; SCAN handler'da tek etkisi
device-panel tip kodu 6 vs 5 seçimi (0x47ae10 `cmp [0x16f2516],0`, 0x47ae42 `dec eax`). Yani
MPT/SORT/RDT/panel operating-mode; USB-vs-NVMe DEĞİL. `EnPCIe/DirectMode/ScanMode` gibi bir
transport anahtarı YOK (tam string taraması: yok). `[K]`

### 4.3 `[DeviceSetting]` ModelNum — NVMe kimlik beklentisi (configurable)
0x42afff–0x42b067: [DeviceSetting] `FirmwareVer`="12345678", **`ModelNum`="MX NVMe SSD"**
(0x811d21), `OUI`="000000", `EUI64`="0000…". "MX NVMe SSD" = beklenen NVMe model string'inin
DEFAULT'u; ini'den değiştirilebilir. `[K]` (Ayrıca native NVMe identify makinesi: `BusType=NVME`
0x91d926 @ ref 0x464478, `SCSItoNVMeIdentify.raw`, `NVMePassThroughIdentify.raw` — hepsi mevcut.)

### 4.4 Gerçek engel = kod içi kabul filter'ı (ini'den kapatılamaz)
`fcn.0047a958`'deki `cmp [pPortDevInfo],1` (0x47aa25) + deviceDesc reddet (0x47aaae). Native
(USB-bridge'siz) MAP1202 için field0 muhtemelen 1 olmuyor → cihaz eleniyor → g_nPortConnectedNum=0
→ "No connected device". A/B yamaları tam bu kapıyı açıyor. field0'ı sıfır-dışı yapan yazıcı
pointer-tabanlı (immediate taramasıyla yakalanmadı); bu yüzden "native disk neden field0=0" tam
kanıt değil — ama yamanın semantiği (field0:=1 zorla) engelin burası olduğunu kanıtlıyor. field0
kaynağı `[H]`, yamanın etkisi `[K]`.

---

## 5. Per-device probe (Q3) — AutoDetect vendor paketi

`VC_GDP_CmdAutoDetect` (ANALIZ_MPTOOL.md: `0x425dc4`, sub `0x3B`, EnNvmeCmdMode!=0 ise `0xD5`,
data-in) vendor paketi, yukarıdaki aynı PhysicalDrive + `IOCTL_STORAGE_PROTOCOL_COMMAND` (0x2d1400)
yolundan gider (encoding EnNvmeCmdMode'a bağlı). Yani **NVMe vendor passthrough** olarak gönderilir.
`[K]` (transport), `[H]` (bu spesifik paketin bizim diskçe cevaplanması).

**Sonuç:** Disk ROM-GDP/loader modunda ("Generic_Loader_NVMe_Device") ve vfio-NVMe ile
PhysicalDrive olarak sunulursa: AutoDetect (0xC1/0x3B) zaten bir GDP komutu olduğundan, temiz
vendor-komut (stub'sız) bekleyen ROM-GDP ile **en uyumlu** konfigürasyon budur. MXMPTool stub
KULLANMAZ (ev-yapımı JD tooling'in ROM-GDP ile uyumsuzluğu MXMPTool için geçerli değil). `[H,
güçlü]`. Product/system mode'da ise transport 0x86 ReadRam bazlı identify ile MXUtility gibi
çalışmalı, ama AutoDetect'in (0x3B) product mode'da tam cevaplanıp cevaplanmayacağı runtime sorusu.

**Kritik caveat `[H]`:** `IOCTL_STORAGE_PROTOCOL_COMMAND` bir DİSK handle'ı (`\\.\PhysicalDriveN`)
gerektirir; bu da NVMe cihazının bir namespace sunmasına bağlıdır. Product mode'da namespace var
(MXUtility çalışıyor). ROM-GDP modunun namespace/PhysicalDrive sunup sunmadığı donanım/runtime
sorusudur — MXUtility'nin GDP/RDT/Loader modlarını aynı PhysicalDrive yolundan desteklemesi
sunacağına işaret eder ama statik olarak kesinleştirilemez.

---

## 6. PCIe_B farkları (Q4)
B = A'nın iki filter yaması + `0x47AB39: call 0x4056fc → mov eax,0xFFFF` (probe stub) + farklı
header baytı. Keşif/transport mimarisi A ile AYNI (DISK-class + PhysicalDrive + STORAGE_PROTOCOL).
Tek davranış farkı: B, per-device vendor probe'unu atlayıp cihazı koşulsuz kabul+sınıflandırır
(pPortDevInfo+0xc = 0xFFFF). A'da probe başarısız olup cihaz görünmezse B'yi kullan. `[K]`

---

## 7. MXMPSORT_MAS090x_V2.exe (Q5, bonus)
`rabin2 -z`: `USBSTOR`, `JMUSBAcess`, `EnumUSBDevice`, `TotalUSBPortCount`, `\\.\PHYSICALDRIVE%u`,
`\\.\PHYSICALDRIVE4` VAR; ama **`GetPhysicalDriver`, `NVMePassThroughIdentify`, `SCSItoNVMeIdentify`,
`BusType=NVME`, `MX NVMe SSD`, `EnNvmeCmdMode`, `STORAGE_PROTOCOL` YOK.** `[K]`
→ Bu SORT aracı (2020, MAS090x — MAP1202 değil FARKLI kontrolcü) PhysicalDrive açıyor ama native
NVMe passthrough makinesine sahip DEĞİL; büyük olasılıkla USB bridge üzerinden SCSI passthrough.
MAP1202 için SORT/RDT adımları MXMPTool'un kendi mode'larıyla (aynı NVMe yolu) yürür; ayrı
MXMPSORT_MAS090x native-NVMe için uygun aday değil.

---

## 8. Önceki "USB-only" sonucunun çürütülmesi
Önceki ajan `fcn.004925ba` ("No connected device for detecting!!" 0x920857) + `EnumUSBDevice` +
`g_nPortConnectedNum` string'lerine bakıp USB-only demiş. Düzeltmeler:
- `fcn.004925ba` bir **tüketici/operasyon handler**'ıdır (g_nPortConnectedNum'ı OKUYUP boşsa mesaj
  basar); keşif/sayım mekanizması DEĞİL. Sayımı yapan `fcn.0047ac98 → fcn.0047a958`. `[K]`
- Gerçek enumerator DISK-class GUID kullanır (madde 2), USB değil. `EnumUSBDevice`/
  `TotalUSBPortCount` sadece yanıltıcı log/isimler. `[K]`
- Transport `\\.\PhysicalDrive` + `IOCTL_STORAGE_PROTOCOL_COMMAND` — MXUtility ile aynı. `[K]`

---

## 9. vfio üzerinden çalıştırma — somut adımlar (uygulanabilirse)
Ön koşullar MXUtility ile aynı (o zaten bu yoldan çalışıyor):
1. Diski Windows PE VM'e vfio-pci ile NVMe PhysicalDrive olarak passthrough et (mevcut kurulum).
2. `MPTOOL.ini [Setting] EnNvmeCmdMode=0` (default) — transport = STORAGE_PROTOCOL_COMMAND (native).
   `ToolMode`'a dokunma (UI/operating).
3. **PCIe_A** ile başla (filter kaldırılmış, gerçek vendor probe korunmuş). Cihaz listede
   görünürse (g_nPortConnectedNum>0) → native NVMe keşif çalışıyor demektir.
4. Görünmezse **PCIe_B** (probe stub'lı → koşulsuz kabul) dene.
5. `MPTOOL.ini`'yi doğru SKV6 profiline çek (BRIFING: şu an yanlışlıkla V7'ye ayarlı —
   `FlashUniName=SKV703001`, `FWOneBinName=SKV7.bin`, TMC/Para V7). Aksi halde kabul edilse bile
   MP/SORT yanlış NAND profiliyle koşar.
6. SCAN → device panel'de sürücüyü doğrula. Sonra SORT/RDT/MPT: NAND yazma gerçek GDP komutları
   (0x88/0x89/0x8A/0x8B) ister; bunun için disk aracın beklediği GDP/loader modunda olmalı
   (adaptör sorusundan bağımsız gereksinim; BRIFING: product mode'da 0x87 WriteRam NO-OP,
   ROM-GDP'de gerçek).

**Dürüst sınır `[H]`:** Statik analiz, (a) bizim diskin MXMPTool'un per-device probe'unu
cevaplayacağını, (b) ROM-GDP modunun Windows'a `\\.\PhysicalDrive` (namespace) sunacağını, ve
(c) MP/SORT'un tamamlanacağını KANITLAMAZ — bunlar runtime testleri. Kanıtlanan: keşif (DISK-class),
cihaz-açma (`\\.\PhysicalDrive`) ve vendor transport (`IOCTL_STORAGE_PROTOCOL_COMMAND`) makinesi
**net biçimde native-NVMe** ve MXUtility ile aynı; USB bridge mimari olarak gerekli değil.

---

## Ek: kullanılan komutlar/kanıt adresleri (özet tablo)
| İddia | Adres(ler) | K/H |
|---|---|---|
| .text/.data haritası | rabin2 -S | K |
| A yaması (filter kaldır) | 0x47AA25, 0x47AAAE | K |
| B yaması (probe stub) | 0x47AB39 → call 0x4056fc | K |
| SCAN handler & callerlar | fcn.0047ac98; 0x44a138/0x47a860/0x4b1c28 | K |
| g_nPortConnectedNum | mov [0x8a62f4] @0x47ad2f | K |
| enumerator zinciri | 0x47a965→0045d884→0x45d8e7→00404ffc | K |
| SetupDiGetClassDevs ClassGuid | call @0x40508f, ptr 0x79ee4c | K |
| **GUID = GUID_DEVINTERFACE_DISK** | 0x79ee4c = 53F56307-B6BF-11D0-94F2-00A0C91EFB8B | K |
| GetPhysicalDriver / \\.\PhysicalDrive | fcn.004269c4; 0x7f7ab0/0x7f7ac4 | K |
| port→drive tablosu | [0xec80e8], filter yazımı 0x47abbf/0x47ab1e | K |
| IOCTL_STORAGE_PROTOCOL_COMMAND gönderim | push 0x2d1400 @0x40306b; DIoC @0x403073 | K |
| IOCTL_SCSI_MINIPORT / FIRMWARE | 0x4d008 (0x4040f3…); 0x1b0780 @0x404c03 | K |
| EnNvmeCmdMode ini→byte | 0x42aacd → [0x1703de8]; 20+ test | K |
| ToolMode ini→byte | 0x42a743 → [0x16f2516]; UI-only in scan | K |
| [DeviceSetting] ModelNum="MX NVMe SSD" | 0x42b020 (0x811d21) | K |
| "No connected device for detecting" = tüketici | fcn.004925ba (0x920857) | K |
| MXMPSORT native-NVMe YOK | rabin2 -z (string yokluğu) | K |
| native disk field0=0 (reddin nedeni) | — (pointer-tabanlı yazıcı) | H |
| probe/mode runtime sonucu | — | H |
