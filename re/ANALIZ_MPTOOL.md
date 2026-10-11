# MXMPTool_MAP1202_USB_V0_01_017.exe — tersine mühendislik notları

Hedef: MAXIO MAP1202 MPTool'un NAND'a firmware yazma dizisini çıkarmak.

Kaynak paket: `/home/schrodinger/jd1024/kanit/mpt/ac_HYV7_64GB_Die_128G-1T/MAP1202 HYV7 64GB Die 128G-1T SN09286 20220704/T1/`
(T1 == T3 == T5; exe/GDP/SORT md5 aynı, sadece `MPTOOL.ini` T1'de biraz farklı.)

Ham çıktılar: `/home/schrodinger/jd1024/re/mptool/`
- `MPT.exe` (analiz kopyası), `mpt.asm` (tam objdump, 1.39M komut), `idx.pkl` (fonksiyon + string xref indeksi)
- `mptool_ascii.txt`, `mptool_utf16.txt`, `mxutil_*.txt`, `gdp_ascii.txt`, `sort_ascii.txt`, `sys_YIQZCA2C_ascii.txt`, `ucode_ascii.txt`
- `mptool_debuglog.txt` (1090 debug format string), `mptool_vsyms.txt` (161 iç fonksiyon adı)
- `cmd_builders.txt` (otomatik çıkarılan 45 vendor-komut paket kurucusu)
- `region_494000_49a000.txt`, `region_3f5000_3f9000.txt` (string bölgeleri)
- `releasenote_pdf.txt`, `MPTOOL.ini`, `Flash.ini`, `ReleaseNote.txt`
- Yardımcı scriptler: `rs.py` (string çöz), `idx.py`, `q.py` (fonksiyon ara), `fn.py`, `dis.py` (string yorumlu disasm), `cg.py` (çağrı grafiği), `cmds.py`

---

## 0. Binary türü (soru 5)

.NET DEĞİL, native.
- `file`: `PE32 executable (GUI) Intel 80386, 9 sections`
- `mscorlib` / `BSJB` / `_CorExeMain` yok (grep 0 sonuç).
- Embarcadero C++Builder / VCL: `Vcl::Forms::TForm`, `System::DelphiInterface<...>`, `TAboutForm`, `DELPHICLASS TRttiMethod` → `mptool_ascii.txt` satır 583, 592, 5582
- Kaynak dosya adı string olarak var: `..\MKLib\V_Proc.cpp` (vma 0x89707d)
- Şanslıyız: binary'de fonksiyon adları debug printf string'i olarak duruyor (`######### - [%d]VP_WriteCodePage\n` gibi). 161 iç sembol adı çıkarıldı (`mptool_vsyms.txt`).

PE yerleşimi (adres → dosya ofseti dönüşümü için):

    .text  file 0x000600..0x39b400   VMA 0x401000   (file = vma - 0x400a00)
    .data  file 0x39b400..0x57e200   VMA 0x79c000   (file = vma - 0x400c00)

---

## 1. Vendor protokolü — taşıma katmanı

### 1.1 Dispatcher `VC_VendorCmd` @ 0x4244e4

    BOOL VC_VendorCmd(BYTE port, void* payload, DWORD payloadLen /*=0x0C*/,
                      void* dataBuf, DWORD dataLen, BYTE bIsRead, DWORD maxLen /*=0x1000*/)

İki global anahtar seçim yapar:
- `ds:0x1703DE8` = EnNvmeCmdMode  (0 → Windows `IOCTL_STORAGE_PROTOCOL_COMMAND`; 1 → `IOCTL_SCSI_MINIPORT` + `"FIRMWARE"` SRB, ControlCode 0x1B0780)
- `ds:0x1703DE9` = NvmeIntelVMDCmd (1 → `\\.\Scsi%d:` + SRB imzası `"IntelNvm"`, ControlCode 0xF0002808)

Senin kullandığın yol = EnNvmeCmdMode==0, yani `NVMeVendorCmdWrite` @ 0x403884 / `NVMeVendorCmdRead` @ 0x403bb0.

### 1.2 `NVMeVendorCmdWrite` @ 0x403884 — doğrulanmış SQE kurulumu

`STORAGE_PROTOCOL_COMMAND` (IOCTL_STORAGE_PROTOCOL_COMMAND, `\\.\PHYSICALDRIVE%d`):

    +0x00 Version                     = 1
    +0x04 Length                      = 0x54
    +0x08 ProtocolType                = 3   (ProtocolTypeNvme)
    +0x0C Flags                       = 0x80000000 (ADAPTER_REQUEST)
    +0x18 CommandLength               = 0x40
    +0x1C ErrorInfoLength             = 0x40
    +0x20 DataToDeviceTransferLength  = sectors << 9
    +0x28 TimeOutValue                = 10
    +0x2C ErrorInfoOffset             = 0x90
    +0x30 DataToDeviceBufferOffset    = 0x90 + 0x40 = 0xD0
    +0x38 CommandSpecific             = 1   (NVME ADMIN command)
    +0x50 Command[64] = NVMe SQE

SQE (offset 0x50):

    byte  0x00  opcode = 0xC1
    dword 0x28  CDW10  = sectors << 7      (transfer / 4, yani dword sayısı)
    dword 0x38  CDW14  = 0x00123400 | subcode
    dword 0x3C  CDW15  = sectors

Kanıt: `0x403aa0: 81 c9 00 34 12 00  or ecx,0x123400` ; `0x403a80: 0c c1  or al,0xc1` ; `0x403a90: c1 e0 07  shl eax,7`.

İki faz (fonksiyon içinde `######### - First write` / `Second write`):
- faz-1 (komut): `subcode = 0xFF`, `sectors = 1` → CDW14 = 0x001234FF, CDW10 = 0x80, CDW15 = 1.
  Veri = 512 bayt; ilk 12 baytı payload (`memcpy(buf+0xD0, payload, payloadLen=0x0C)` @ 0x403acb), gerisi 0.
  DİKKAT: paket kurucuları payload[12] ve payload[13]'ü de yazıyor ama NVMe yolunda bu 2 bayt
  gönderilmiyor (payloadLen sabit 0x0C). USB-bridge yolunda tam 0x400 bayt gönderiliyor.
- faz-2 (veri): bridge/miniport yolunda `CDW14 = 0x12340000 | (cmdByte<<8) | 0x08` (`0x4246b1`).
  Plain-NVMe yolunda `CDW14 = 0x00123400 | subcode`, subcode'u çağıran geçirir.
  Yazma: opcode 0xC1; okuma: `NVMeVendorCmdRead` @ 0x403bb0.

### 1.3 Vendor modunu açma/kapama — BUNU ATLAMA

`VC_EnableVendorCmd` @ 0x424160 → plain-NVMe alt yolu 0x40331c:

    opcode  = 0xC1
    CDW14   = 0x00AE34FF          <-- 0x1234 DEĞİL, 0xAE34 (unlock magic)
    CDW15   = 1
    data    = 4096 bayt, içerik: FF E5 C1 00 00 ...

Kanıt: `0x40351b: c7 41 38 ff 34 ae 00  mov [ecx+0x38],0xae34ff` ; `0x403511: 0c c1  or al,0xc1` ; `0x4034de: mov [edx+0x20],0x1000`.

`VC_DisableVendorCmd` @ 0x424440 → CDW14 = 0x00BD34FF, opcode 0xC1, 4096 bayt
(`0x4037cf: c7 41 38 ff 34 bd 00`).

Miniport (EnNvmeCmdMode=1) karşılıkları: enable `0xAE34FF08`, normal `0x1234FF08`, bridge `0x1234FF08>>2 = 0x048D3FC2`.

---

## 2. Vendor komut seti (soru 1)

Paket düzeni: `FF E5 <cmd> <p0> <p1> ...` — 512 (NVMe) / 1024 (bridge) baytlık sıfırlanmış tampon.

ÖNEMLİ: okuma yönlü komutların iki farklı komut baytı var. `ds:0x1703DE8` (EnNvmeCmdMode)
0 ise soldaki, 1 ise sağdaki kullanılıyor. Senin doğruladığın 0x89/0x8A/0x8B/0x11 kümesi = EnNvmeCmdMode=0 kolonu.

| Fonksiyon | addr | cmd (mode0) | cmd (mode1) | yön |
|---|---|---|---|---|
| VC_EnableVendorCmd | 0x424160 | 0xC1 | 0xC1 | out |
| VC_LDR_CmdJumpToPRAM | 0x424a4c | 0x82 | – | out |
| VC_LDR_CmdJumpToROM | 0x424b6c | 0x83 | – | out |
| VC_LDR_CmdGetReg | 0x424c38 | 0x84 | 0xD0 | in |
| VC_LDR_CmdReadRam | 0x424f6c | 0x86 | 0xD1 | in |
| VC_LDR_CmdWriteRam | 0x424e08 | 0x87 | – | out |
| VC_LDR_CmdWriteRamRsa | 0x424eb8 | 0x87 | – | out |
| VC_GDP_CmdGetReturn | 0x4250d8 | 0x00 | 0xD2 | in |
| VC_GDP_CmdInitGDP | 0x42505c | 0x11 | – | out |
| VC_GDP_CmdInitGDP (2) | 0x426334 | 0x4D | – | out |
| VC_GDP_CmdGetFlashParam | 0x425184 | 0x10 | 0xD7 | in |
| VC_GDP_CmdReadFlashID | 0x425224 | 0x88 | 0xD8 | in |
| VC_GDP_BDL_Test | 0x4252fc | 0x53 | – | |
| VC_GDP_LCDL_Test | 0x4253c4 / 0x4254cc | 0x54 / 0x56 | – / 0xDF | |
| VC_GDP_ZQ_Calibration | 0x425570 | 0x55 | 0xDE | |
| VC_GDP_CmdPageRead | 0x425610 | 0x89 | 0xD9 | in |
| VC_GDP_CmdPageWrite | 0x425710 | 0x8A | – | out |
| VC_GDP_CmdPageWriteInterleave | 0x425804 | 0x4C | – | out |
| VC_GDP_CmdEraseSPI | 0x4258f0 | 0x0A | – | – |
| (adsız, SPI yaz?) | 0x42596c | 0x0C | – | out |
| VC_GDP_CmdBlockErase | 0x425a40 | 0x8B | – | – |
| VC_GDP_CmdScanDefectBad | 0x425af8 | 0x02 | – | – |
| VC_GDP_CmdGetDefectBadTab | 0x425b7c | 0x31 | 0xD6 | in |
| VC_GDP_CmdGetFlashModule | 0x425c0c | 0x05 | 0xD3 | in |
| VC_GDP_CmdGetCodeBlock | 0x425c9c | 0x07 | 0xD4 | in |
| VC_GDP_CmdPreCheckCodeBlock | 0x425d2c | 0x3A | – | – |
| VC_GDP_CmdAutoDetect | 0x425dc4 | 0x3B | 0xD5 | in |
| VC_GDP_CmdFlashDiagnostic | 0x425e54 | 0x21 | 0xDB | in |
| VC_GDP_CmdScanResultBlk | 0x425f2c | 0x47 | – | – |
| VC_GDP_CmdGetResultBlk | 0x425fb4 | 0x48 | 0xDC | in |
| VC_GDP_CmdSwitchToLegacy | 0x426044 | 0x49 | – | – |
| VC_RDT_CmdGetSORTStatus | 0x4260c0 | 0x3C | 0xE0 | in |
| VC_GDP_CmdDramTest | 0x426160 | 0x4A | – | – |
| VC_GDP_CmdCheckNandTime | 0x42620c | 0x4B | – | – |
| VC_GDP_CmdPcie_LoopBack | 0x4262b8 | 0x4E | – | – |
| VC_GDP_CmdReadEfuse | 0x4263b0 | 0x4F | 0xDD | in |
| VC_SYS_ReadPage | 0x426448 | 0x04 | 0xC4 | in |
| VC_SYS_GetBadUnit | 0x426564 | 0x00 | 0xC2 | in |
| VC_SYS_GetEraseCount | 0x4266c8 | 0x01 | 0xC3 | in |
| VC_SYS_GetUartLog | 0x42677c | 0x21 | 0xC5 | in |
| VC_SYS_GetFlashID | 0x426618 | 0x36 | 0xC9 | in |
| VC_SYS_SetDeviceInfo | 0x426834 | 0x05 | – | out |
| (ClearSmartAttr) | 0x4268cc | 0x40 | – | – |

Tam otomatik dökümü: `mptool/cmd_builders.txt`.

### 2.1 Paket düzenleri (bayt bayt)

0x8A — Page Write (`0x425710`):

    [0]=FF [1]=E5 [2]=8A
    [3]  = channel
    [4]  = bank/CE
    [5]  = block >> 8        (big-endian)
    [6]  = block & 0xFF
    [7]  = page  >> 8
    [8]  = page  & 0xFF
    [9]  = mode      (VP_WritePage arg5; loader-block yazımında 0 veya ucLdpcMode = ds:0xA2FBB2)
    [10] = ((argA & 3) << 2) | argB     ; loader-block yazımında argB=1, argA=0
    [11] = argC      (0)
    [12] = argE      (0/1)
    [13] = argD      (0)
    veri fazı: pBuf, uzunluk = sectorCount * 512

0x89 — Page Read (`0x425610`): aynı düzen, [10]/[12]/[13] doğrudan arg; yön = read.

0x8B — Block Erase (`0x425a40`):

    [0]=FF [1]=E5 [2]=8B
    [3] = channel
    [4] = bank/CE
    [5] = block >> 8
    [6] = block & 0xFF
    [7] = p4
    [8] = p5
    veri fazı yok

Çağrı yerleri (kritik):
- `VP_PROC_EraseValidLoaderBlock` @0x4432ac → `0x443312: p4=1, p5=1` (gerçek loader/code block silme)
- `VP_PROC_ClearCodeBlock` @0x440458 → `0x440494: channel=0xFF, bank=0xFF, p4=0, p5=0` (broadcast)

Senin "0x8B p6=1 şart" bulgun bununla uyumlu: MPTool code-block silmede `[7]=[8]=1` gönderiyor.
Bu iki baytın resmi adı binary'de yok; 0/0 yalnızca `ch=0xFF, bank=0xFF` broadcast temizliğinde kullanılıyor,
yani multi-plane / super-block bayrağı gibi davranıyor.

0x11 / 0x4D — InitGDP: `FF E5 11` (parametresiz) ve `FF E5 4D` + 512 baytlık loader-block bitmask haritası
(`VP_DownloadToLoaderBlock` başında kuruluyor, `LDR_BLK_W.raw` olarak da dump ediliyor).

### 2.2 Tamamlanma / durum okuma — VC_GDP_CmdGetReturn (cmd 0x00)

Her erase/write/read sonrası `VC_GDP_CmdGetReturn` (`FF E5 00`, data-in 512 bayt) çağrılıyor:

    buf[0] == 0xAA   -> hâlâ meşgul, tekrar yokla (~100ms/1s bekleme döngüsü)
    buf[1] == 1      -> BAŞARILI
    buf[1] != 1      -> hata kodu

Kanıt: `0x437e5a` (erase sonrası) → `0x437e68: mov dl,[ebp-0x1003]; dec edx; jne <fail>` ; busy kontrolü `0x4401e1: cmp edx,0xAA`.

---

## 3. LDBK boot descriptor formatı (soru 2)

### 3.1 Sihirli dizeler

`.data`'da: `LDBK BLOCKS V00`, `LDBK CONFIG V00` (vma 0x7F7C60 / 0x7F7C70 ve 0x7AEE62 / 0x7AEE72),
`LDBK FWSLOT MARK`, `LDBK FWTMC MARK`, `LDBK LDPC TABLE1/2`, `LDBK NANDMEM TAB`.
Aynı dizeler firmware imajında da var (`SYS/YIQZCA2C.bin` @0x6D3C0, @0x9A0F0) — yani FW bunları NAND'da arıyor.

### 3.2 Info page'i kuran fonksiyon: `VP_Cougar_FillInfoPage` @ 0x4388a0

Bir sayfa tamponu doldurup loader block'un page 0'ına yazıyor
(`0x43a894`: `VP_WriteDataToLoaderBlock(port, pageNo=0, mode=0, 1, buf, 8 sektör = 4096B, 0)`).

Sayfa yerleşimi:

    0x0000  LDBK BLOCKS bloğu  (0x1E0 bayt, önce sıfırlanır)
    0x01E0  0x20 bayt: AP_FlashSet.sFlashFullName (ds:0xA2FBC4)
    0x0200  LDBK CONFIG bloğu  (0x20 bayt)
    0x0220  CodeMap bölgesi 1  (0x100 bayt = 16 x 16B CODE_ENTRY)
    0x0320  CodeMap bölgesi 2  (0x300 bayt)
    0x0620  CodeMap bölgesi 3  (0x410 bayt)
    0x0A30  CodeMap bölgesi 4

LDBK BLOCKS (@0x0000) — çıkarılan alanlar (hepsi 0x4388a0-0x438CFF arası sabit yazımlar):

    0x00  char[16] "LDBK BLOCKS V00"
    0x10  u8   bit-index(wBlocks / ucDiePerCE)        (helper 0x427098)
    0x11  u8   bit-index(wPages) ya da wPages/3, LDPC moduna göre
    0x12  u8   0x05
    0x18  u16  0x01F4 (500)   ecnt_thrshd0      <- MPTOOL.ini ecnt_thrshd0..3 = 500
    0x1A  u16  0x01F4         ecnt_thrshd1
    0x1C  u16  0x01F4         ecnt_thrshd2
    0x1E  u16  0x01F4         ecnt_thrshd3
    0x20  u16  0x0200
    0x22  u8   0x08
    0x23..0x27 u8 0
    0x28  u8   1
    0x29  u8   0
    0x2A  u8   1
    0x2B..0x2F u8 0
    0x30  u16  0x0FFF  x4   (0x30, 0x32, 0x34, 0x36)
    0x38  u16  0x01FF  x4   (0x38, 0x3A, 0x3C, 0x3E)
    0x40  u8   (ds:0xA30CAB + 2)   [RDT modunda ds:0xA30CA4 + 1]
    0x41  u8   (bPageSector/2)/4          ; SKV7: (32/2)/4 = 4
    0x42  u8   1
    0x43  u8   2
    0x45  u8   0
    0x46  u16  0
    0x48  u8   0/1   (ds:0x1703607)
    0x49  u8   1
    0x4A  u8   0/1
    0x4B  u8   0/1/2 (ds:0xA2FEFA = 100/110 -> 1 ; = 10/1 -> 2 ; aksi 0)
    0x50  u16  2
    0x52  u16  4
    0x54  u8   1/2/3   (ucLdpcMode, ds:0xA2FBB2)
    0x56  u16  ((wPageSize<<10) + wSpareByte) / 4     ; SKV7: (16<<10 + 2048)/4 = 4608
    0x60  u32  LDPC decode offset  = 0x00000010
    0x64  u32  LDPC decode length  = 0x14C0 / 0x149C / 0x1478   (ucLdpcMode 1/2/3)
    0x68  u32  LDPC encode offset  = 0x00002010
    0x6C  u32  LDPC encode length  = 0x0B7C / 0x0B70 / 0x0B64
    0x70  u8[32] ds:0xA32294 kopyası (LDPC matris seçim tablosu)
    0x93  u8   1

LDBK CONFIG (@0x0200):

    0x00  char[16] "LDBK CONFIG V00"
    0x10  u32 0x00000220   ; CodeMap bölge 1 ofseti
    0x14  u32 0x00000320   ; bölge 2
    0x18  u32 0x00000620   ; bölge 3
    0x1C  u32 0x00000A30   ; bölge 4

CODE_ENTRY (16 bayt/kayıt, @0x0220'den itibaren) — `pCodeMap->aCodeEntry[]`:

    +0x00 u16 wFirstPageNo     (mantıksal sayfa sayacı; 0x005C = 92'den başlar)
    +0x02 u16 wLastPageNo      (= wFirstPageNo + wPageLength - 1)
    +0x04 u32 dwLength         (bayt cinsinden kod parçası uzunluğu)
    +0x08 u32 dwOffset         (hedef yükleme adresi — SRAM/DRAM)
    +0x0C u16 wEnable
    +0x0E u16 wCheckSum        <-- MPTool sabit 0xFFFF yazıyor (0x439035)

`wPageLength = ceil(dwLength / pageSize)`; sayaç her kayıttan sonra `+= wPageLength`.

### 3.3 CRC / checksum

- Info page'deki `wCheckSum` hesaplanmıyor, sabit 0xFFFF. Kanıt: `0x439035: mov WORD PTR [ecx+edx*1+0xe],0xffff`.
- LDBK bloklarında başka CRC yazımı bulunamadı (0x4388a0-0x43a8ac tarandı).
- Efuse termal değeri için ayrı bir CRC kontrolü var (`Check Efuse_thermal CRC Fail!!!`) ama LDBK ile ilgisi yok.

Bulgu: LDBK BLOCKS / CONFIG sayfasında gerçek bir CRC yok.

### 3.4 Kaç kopya, hangi blok/sayfa

`VP_WriteDataToLoaderBlock` @ 0x437f10:

    for lb = 0 .. AP_Instance[port].ucLoaderBlockNum-1     (ds: 0xEC8170 + port*0x2066*8)
      for ch = 0 .. MaxPhyChannel-1   (ds:0x16F2C36)
        for bk = 0 .. MaxPhyBank-1    (ds:0x16F2C37)
           blk = aLoaderBlockNo[port][ch][bk][lb]
                 ; u16 dizi @ 0xEC80F0 + port*0x2066*8 + ch*0x10 + bk*4
           VP_WritePage(port, ch, bk, blk, pageNo, mode, 1, 0, buf, lenSectors, 0)

Yani her kanal x her CE x ucLoaderBlockNum blok için aynı sayfa yazılıyor → çok kopyalı boot bölgesi.
`MPTOOL.ini`: `FWBlkQnty=11`, `SYS_Qnty=2`, `TBLBlkQnty=4`, `Channel=4`, `Bank=4`.
Loader blok numaraları ya son MP'den miras alınıyor ya da `VC_GDP_CmdGetCodeBlock` (0x07) ile
firmware'den okunuyor (`VP_PROC_GetLoaderBlock` @0x4404c8, `LDR_BLK.raw` dump'ı).

---

## 4. SYS/*.bin imaj formatı ve NAND'a yerleşimi (soru 3)

### 4.1 Konteyner: MAS09_FWTAG_V001

`SYS/*.bin`, `GDP.bin`, `SORT/SORT.bin` hepsi aynı konteyner:

    0x0000  char[16] "MAS09_FWTAG_V001"
    0x0010  u16  0x0000        (?)
    0x0012  u16  nEntries      ; SYS = 0x000C (12), GDP = 0x0002, SORT = 0x0002
    0x0014  16 x 0xFF          (rezerve)
    0x0020  16 bayt sürüm/parametre blobu: 00 01 cb 03 00 01 0d 01 e0 7f 01 00 00 00 01 04
    0x0030  0x40 bayt 0xAE dolgu
    0x0070  BIN_ENTRY[nEntries], 16 bayt/kayıt
    0x1000  ilk kod parçasının verisi (entry[0].dwBinOffset)

BIN_ENTRY (16 bayt):

    +0x00 u16 wFirstPageNo     (mantıksal sayfa)
    +0x02 u16 wLastPageNo
    +0x04 u32 dwLength         (bayt)
    +0x08 u32 dwOffset         (hedef yükleme adresi)
    +0x0C u32 dwBinOffset      (bu .bin dosyası içindeki veri ofseti)

İlk 4 alan birebir info page'deki CODE_ENTRY ile aynı (MPTool kopyalıyor, wCheckSum'ı 0xFFFF yapıyor).

`SYS/YIQZCA2C.bin` (692224 bayt) çözümü — dosya ile birebir doğrulandı:

    #   first last  length     dest        binOff     pages
    0   0x5C  0x61  0x00018000 0x00000000  0x00001000  6
    1   0x62  0x62  0x00004000 0x00800000  0x00019000  1
    2   0x63  0x63  0x00004000 0x00804000  0x0001D000  1
    3   0x64  0x64  0x00004000 0x040D6000  0x00021000  1
    4   0x65  0x6A  0x00018000 0x02000000  0x00025000  6
    5   0x6B  0x6B  0x00004000 0x02800000  0x0003D000  1
    6   0x6C  0x6F  0x00010000 0x04060000  0x00041000  4
    7   0x70  0x77  0x00020000 0x040E0000  0x00051000  8
    8   0x78  0x78  0x00004000 0x040D2000  0x00071000  1
    9   0x79  0x79  0x00004000 0x040DC000  0x00075000  1
    10  0x7A  0x80  0x0001C000 0x040D2000  0x00079000  7
    11  0x81  0x85  0x00014000 0x040DC000  0x00095000  5
    Toplam: 0x1000 + 0xA8000 = 0xA9000 = 692224  == dosya boyutu (OK)

Sayfa boyutu = 0x18000/6 = 0x4000 = 16 KB (= `bPageSector 32 x 512`, Flash.ini `PZ=16`).

`GDP.bin` (233472): entry0 `0x59..0x5B len 0xC000 dest 0 binOff 0x1000`; entry1 `0x5C..0x66 len 0x2C000 dest 0x040C0000 binOff 0xD000` → 0xD000+0x2C000 = 0x39000 (OK)
`SORT.bin` (282624): `0x59..0x5B len 0xC000`; `0x5C..0x69 len 0x38000 dest 0x040C0000 binOff 0xD000` (OK)

### 4.2 "MKSSD" imzası — doğrulandı

İlk kod sayfasının (page 0x5C) +0x1C0 ofsetinde imza duruyor:

    SYS/YIQZCA2C.bin @0x11C0:  "MKSSD_50100300000092860000,Jun 21 2022,14:33:58,MAP1202,YIQZCA2C"
    SORT/SORT.bin    @0x11C0:  "MKRDT_000005004091430000,May 27 2022,10:16:50,CO..."

- `VP_WriteCodeToFlash` @0x43D14C: sayfayı dosyadan okur, `memcmp(buf+0x1C0,"MKSSD",5)` (0x43D1D6).
  Eşleşirse → "Find param code page!" → SN/MN/FWver/DPD parametrelerini bu sayfanın içine yamalar
  (0x40BF10, 0x40B1B8, 0x40BB18, 0x40BE38, 0x40B11C) ve `param.raw` dump'lar.
- `VP_IsValidLoaderBlock` @0x440034: bloğun `wPageNo[92]` sayfasını okur, +0x1C0'da "MKSSD" → SYS FW
  code block (durum = 2), "MKRDT" → RDT FW code block (durum = 1).

### 4.3 Mantıksal sayfa → fiziksel sayfa haritası

`wPageNo[384]` (u16) dizisi `ds:0xA2FBE4`'te. Flash.ini'deki PairPage (`P`) kolonuna göre 9 statik
tablodan biri kopyalanıyor (fonksiyon 0x42759C, dallar 0x427F61-0x4280D9):

    P = 4 veya 9 -> tablo @0x7FAC0C   (0,1,2,3,6,7,10,11,14,15,...)
    P = 5        -> 0x7FBC0C          (0,1,3,5,7,9,...)
    P = 6        -> 0x7FCC0C
    P = 7        -> 0x7FDC0C
    P = 8        -> 0x7FEC0C
    P = 10       -> 0x800C0C
    P = 11       -> 0x801C0C
    P = 12       -> 0x802C0C
    diğer        -> 0x7FA90C          (özdeşlik: wPageNo[i] = i)

SKHynix V7 için Flash.ini satırı:

    Name008=SKV703001 H25G9TC18488 3 2 1 1084 4224 16 1 2 0xAD 0x7E 0x28 0x0B 0x00 0xC0 0 0 0 11 4 1500 001 2048 100

Sütunlar (Flash.ini legend): V=3(Hynix) T=2(TLC) CE=1 Blks=1084 PGs=4224 PZ=16(KB)
Die/CE=1 ECC=2 ID=AD 7E 28 0B 00 C0 Ex=0 DO=0 P=0 IF=11 PL=4 Ed=1500 Nm=001 SB=2048 Gpio=100

→ P = 0 → özdeşlik tablosu: SKV7'de mantıksal sayfa = fiziksel sayfa.
(Alan eşlemesi kanıtı: parser 0x45C2BC-0x45C35B sırayla record+0x56=DO, +0x58=P, +0x59=IF, +0x5A=PL;
 `ds:0xA2FEF2 <- record+0x58` @0x427AB3 ve `ds:0xA2FEF0 <- record+0x62 = SpareByte = 2048` @0x427AA1.)

### 4.4 Loader block'un sayfa haritası (ne, hangi sayfaya)

`VP_WriteDataToLoaderBlock` çağrıları (`pageNo` = `wPageNo[idx]`):

    idx 0    page 0         Info page (LDBK BLOCKS + CONFIG + CodeMap)  4096 B  VP_Cougar_FillInfoPage 0x4388A0
    idx 1    wPageNo[1]     (fn 0x43AE50, info page 2. kısım)           4096 B
    idx 2    wPageNo[2]     LDPC Page1  (AP_Param.sLdpcPage1Bin)        4096 B  \
    idx 3    wPageNo[3]     LDPC Page2                                          |
    idx 4    wPageNo[4]     LDPC Page3                                          | VP_Cougar_WriteLdpcPage
    idx 5    wPageNo[5]     LDPC0 Page5 (DAT/ldpc_matrix0_page5.bin)            | 0x43A8AC
    idx 6    wPageNo[6]     LDPC0 Page6                                         |
    idx 7    wPageNo[7]     LDPC0 Page7                                        /
    idx 8    wPageNo[8]     Table page (EC_W_xx_xx.raw)  tam sayfa  VP_WriteTablePage    0x43B1EC
    idx ?    wPageNo[?]     FW slot page                           VP_WriteSlotPage     0x43AEE8
    idx 52+  wPageNo[52+i]  OPAL page (DAT/opal.bin)               VP_WriteOpalPage     0x43B60C
    idx 68   wPageNo[68]    NandMem page (DAT/SKV7/001_xxx/...)    VP_WriteNandMemPage  0x43B92C
    idx 69+  wPageNo[69+i]  UEFI page (DAT/NvmExpressDxe.rom)      VP_WriteUefiPage     0x43BA2C
    idx 91   wPageNo[91]    TMC table page (DAT/tmc_para.bin)      VP_WriteTMCTablePage 0x43BC68
    idx 92.. wPageNo[92..]  KOD SAYFALARI (SYS/*.bin)              VP_WriteCodePage     0x43D9F4
    sonra                   dummy sayfalar, tampon 0xAA ile doldurulur (0x43DCE6)

Kod sayfası yazma döngüsü (`VP_WriteCodePage` @0x43D9F4, gövde 0x43DAB0-0x43DC80):

    for CodeIndex = 0 .. ds:0xA30C90-1
      for PartIndex = 0 .. bCodeNum[CodeIndex]-1          (ds:0xA358E8)
         page    = wStartPageNo[CodeIndex][PartIndex]     (ds:0xA35E38)
         nPages  = wPageLength[CodeIndex][PartIndex]      (ds:0xA35F18)
         wEnable = ds:0xA35FF8[...]
         marker  = 0x00
         if (wEnable & 0xFF) == 1              -> marker = 0xFF   (param/MKSSD sayfası)
         if wEnable == 3 && page == first+1    -> marker = 0xFE
         if wEnable == 3 && page == first+2    -> marker = 0xFD
         VP_WriteCodeToFlash(port, buf, fileHandle, wPageNo[page], marker, ...)

`VP_WriteCodeToFlash` yalnız marker != 0 olan sayfaları içerikten okuyup yamalıyor; diğerleri
doğrudan dosyadan sayfa sayfa aktarılıyor.

### 4.5 ECC / scramble

LDPC ayarı komut parametresiyle veriliyor, dosya içinde değil:
- `VP_WritePage` arg5 → payload[9] = `ucLdpcMode` (`ds:0xA2FBB2`, Flash.ini ECC kolonu; SKV7 = 2 = Rate2).
  Info page'de 0, tablo ve kod sayfalarında `ucLdpcMode`.
- LDPC matris/rate tabloları ayrı sayfalar olarak NAND'a yazılıyor (`DAT/ldpc_rate*_page*.bin`,
  `DAT/ldpc_matrix0_page*.bin`); info page 0x60..0x6C alanları decode/encode ofset-uzunluk verir.
- Ayrı bir scramble anahtarı/ayarı bulunamadı — donanımda LDPC/scrambler mod baytı üzerinden.

---

## 5. MPTool akış sırası (soru 4)

Ana MP sürücüsü: fonksiyon 0x495CE4 (`VP_PROC_DownloadProgram` çağrısı @0x499677).
Çağrı sırası (`cg.py 495ce4 49b000` çıktısı):

     1. VP_GetCurrentMode / VP_JumpToSystem            0x433C7C / 0x43396C
     2. VP_PROC_GetEraseCount                          0x442A94
     3. VP_PROC_GetSerialNumber                        0x442D58
     4. VP_WriteCodeToMemNew2                          0x4368F0   <- GDP.bin'i SRAM'e yükle (VC_LDR_CmdWriteRam 0x87)
     5. VP_InitGDP                                     0x436B5C   <- VC_GDP_CmdInitGDP
     6. VP_PROC_CheckFlashModule                       0x440F68   <- VC_GDP_CmdReadFlashID / CmdGetFlashModule
     7. VC_GDP_CmdSwitchToLegacy (0x49)                0x426044
     8. VP_GetGPIOValue                                0x435320
     9. VP_PROC_GetSortingResultBlock / CheckSortingResult
    10. VP_PROC_BusInterfaceTest                       0x4415AC   [EnBusTest]
    11. VP_PROC_FlashInterfaceTest                     0x4415F0   [EnFlashTest: SRAM/NandReset/DataPath/LDPC/NandTime]
    12. VC_GDP_Cmd_ZQ_Calibration_Test                 0x43616C   [EnCalibration]
    13. VP_PROC_DramTest                               0x441994   [EnDramTest]
    14. VP_PROC_GetLoaderBlock                         0x4404C8   <- geçerli code blockları bul
    15. VP_PROC_Preformat                              0x441CB8   [EnPreFormat] + InheritLatterBB / InheritRDT / Remap
    16. VC_GDP_CmdEraseSPI (0x0A)                      0x4258F0
    17. VP_PROC_EraseAllBlock                          0x443098   [EnEraseAllBlocks]  (VP_EraseBlock 0x437DAC)
    18. VP_GDP_ExecProg / VC_GDP_CmdGetDefectBadTab    0x43E78C / 0x425B7C
    19. VP_check_efuse_temperature                     0x4439D8   [EnCheckEfuseThermal]
    20. VP_PROC_DownloadProgram                        0x441ED4   [EnDownload]   <-- FW YAZMA
    21. VP_PROC_RWTest                                 0x4420C8   [EnRWTest]
    22. VP_PROC_CheckTables                            0x4425F4   [EnCheckTables]
    23. ClearSmartAttr                                 0x4268CC   [EnClearSMART]
    24. VP_JumpToSystem / VP_JumpToSorting             0x43396C / 0x4337E0

Bu sıra `MPTOOL.ini [TestItems]` anahtarlarıyla birebir eşleşiyor
(`EnFlashTest, EnDramTest, EnPreFormat, EnEraseAllBlocks, EnDownload, EnRWTest, EnCheckTables, ...`).
Hata etiketleri `.data` 0x7F70E0+ tablosunda: "Flash Module", "Bus Interface", "Flash Interface",
"Dram Test", "Erase Blocks", "Pre-Format", "Download FW", "Upload Firmware", "R/W Test",
"Check Tables", "Clear SMART Info", ...

### 5.1 `VP_PROC_DownloadProgram` @0x441ED4 (asıl FW yazma)

    VP_GetTables                 0x438254   <- tablolar/DPD parametreleri (yoksa "Get Tables Or Get DPD Param fail")
    VP_PROC_ClearCodeBlock       0x440458   <- VP_EraseBlock(ch=0xFF, bk=0xFF, blk, 0, 0) = eski code blockları sil
    VP_DownloadToLoaderBlock     0x43DDD0   <- ASIL YAZMA (aşağıda)
    VP_UploadCodeFromFlash       0x43E1A8   <- geri oku (UP_*.raw)
    VP_PROC_CheckDPDPara         0x443C74
    VP_CheckCodeBlockFromFlash   0x43E4B0   <- doğrula

### 5.2 `VP_DownloadToLoaderBlock` @0x43DDD0 — sayfa yazma sırası

    opsiyonel: aLoaderBlockNo'dan 512B bitmask kur -> LDR_BLK_W.raw -> VC_GDP_CmdInitGDP(0x4D, buf)
     1. VP_Cougar_FillInfoPage   0x4388A0   page 0        (LDBK BLOCKS+CONFIG+CodeMap)  hata 0xA0
     2. fn 0x43AE50                         wPageNo[1]                                  (hata kodu yok)
     3. VP_Cougar_WriteLdpcPage  0x43A8AC   wPageNo[2..7] (LDPC1-3, LDPC0 p5-p7)        hata 0xA1
        if ds:0x16F2516 == 0 (normal MP, RDT değil):
     4.   VP_WriteSlotPage       0x43AEE8   (fw slot page)
     5.   VP_WriteTablePage      0x43B1EC   wPageNo[8]                                  hata 0xA2
     6.   VP_WriteOpalPage       0x43B60C   (DAT/opal.bin)                              hata 0xA3
     7.   VP_WriteNandMemPage    0x43B92C   wPageNo[68] (DAT/SKV7/001_xxx/nandmem)      hata 0xA4
     8.   VP_WriteUefiPage       0x43BA2C   (DAT/NvmExpressDxe.rom)                     hata 0xA5
     9.   VP_WriteTMCTablePage   0x43BC68   wPageNo[91] (DAT/tmc_para.bin)              hata 0xA6
        else if ds:0x16F2516 == 1 (RDT/SORT):
     4b.  VP_WritePatternPage    0x43CFBC   ("Write Pattern Page")
    10. VP_WriteCodePage         0x43D9F4   wPageNo[92..] SYS/*.bin kod sayfaları       hata 0xA6
    11. dummy sayfalar (0xAA dolgu)

Her adım: `VP_WriteDataToLoaderBlock` → `VP_WritePage` → `VC_GDP_CmdPageWrite(0x8A)` + `VC_GDP_CmdGetReturn(0x00)`.

---

## 6. Sıfırdan araç yazmak için minimum dizi

    1.  VC_EnableVendorCmd            opcode 0xC1, CDW14=0x00AE34FF, CDW15=1, 4096B payload "FF E5 C1"
    2.  (loader modundaysa) VC_LDR_CmdWriteRam (0x87) ile GDP.bin'i SRAM'e yükle,
        VC_LDR_CmdJumpToPRAM (0x82, payload[4]=0x5A) ile GDP'ye atla
    3.  VC_GDP_CmdInitGDP  (0x11)  -> NAND config/DPD yükle
    4.  VC_GDP_CmdReadFlashID (0x88) / CmdGetFlashModule (0x05) ile die haritasını doğrula
    5.  VC_GDP_CmdGetCodeBlock (0x07) ile mevcut loader blocklarını oku (veya kendin seç)
    6.  her (ch, bank, loaderBlk) için: VC_GDP_CmdBlockErase (0x8B) p4=1 p5=1
    7.  page 0: LDBK BLOCKS/CONFIG/CodeMap info page   -> 0x8A, mode=0, 4096B
    8.  LDPC/table/opal/nandmem/uefi/tmc sayfaları     -> 0x8A, mode=ucLdpcMode, tam sayfa
    9.  page 92..: SYS/*.bin BIN_ENTRY'lerine göre kod sayfaları -> 0x8A, mode=ucLdpcMode
        (ilk kod sayfasının +0x1C0'ında "MKSSD..." imzası dosyada zaten var)
    10. her yazımdan sonra VC_GDP_CmdGetReturn (0x00): buf[0]!=0xAA bekle, buf[1]==1 iste
    11. doğrulama: VC_GDP_CmdPageRead (0x89) ile geri oku, +0x1C0'da "MKSSD" ara

---

## 7. Bulunamayanlar / belirsizler

- `payload[9..13]` alanlarının semantik adları binary'de yok; yalnız çağrı yerlerinden değer çıkarıldı.
- `VC_GDP_CmdBlockErase` `[7]`/`[8]` baytlarının resmi adı yok. MPTool loader-block silmede 1/1,
  broadcast temizlikte (ch=bk=0xFF) 0/0 kullanıyor.
- LDBK BLOCKS'taki 0x40, 0x48, 0x4A, 0x4B baytlarının kaynağı global (ds:0xA30CAB, ds:0x1703607,
  ds:0xA2FEFA) — INI/Para eşlemesi tam çözülmedi.
- CodeMap bölge 2/3/4 (0x320 / 0x620 / 0xA30) içerikleri `VP_Cougar_FillInfoPage`in 0x439100+ kısmında
  dolduruluyor; alan düzeni bölge 1 ile aynı 16B CODE_ENTRY ama hangi kod sınıfına ait olduğu
  (2. SYS kopyası / RDT / TMC) kesinleştirilmedi.
- `wCheckSum` sabit 0xFFFF yazıldığı için gerçek bir imza/CRC doğrulaması bulunamadı.
- PDF release note bilgi içermiyor (sadece "First Release, SN09286, MPTool C.0.01.017").

---

## 8. Ek doğrulama: `parse_fwtag.py` çıktısı

`/home/schrodinger/jd1024/re/mptool/parse_fwtag.py` konteyner ayrıştırıcısı; çıktısı
`/home/schrodinger/jd1024/re/mptool/fwtag_entries.txt`. Dört imajın dördü de MATCH veriyor
(son parçanın sonu == dosya boyutu), yani BIN_ENTRY yorumu kesin.

    SYS/YIQZCA2C.bin  692224 (0xA9000)  12 entry
    SYS/YIQZCALC.bin  692224 (0xA9000)  12 entry   (aynı sayfa/uzunluk haritası, farklı içerik)
    GDP.bin           233472 (0x39000)   2 entry
    SORT/SORT.bin     282624 (0x45000)   2 entry

Yeni bulgular:
- SYS imajında `+0x1C0` imzası **iki** parçada var: entry 0 (page 0x5C, load 0x00000000) ve
  entry 4 (page 0x65, load 0x02000000) — ikisi de "MKSSD". Bu `MPTOOL.ini` `SYS_Qnty=2` ile uyumlu:
  firmware iki kopya halinde yazılıyor.
- `GDP.bin` entry 0 (+0x1C0) = **"MKGDP"**; `SORT.bin` entry 0 = **"MKRDT"**.
  `MKGDP` dizesi exe'de de var (vma 0x894e06, `VP_LoadGDPFromBuffer` içinde) — GDP imajı doğrulaması.
- GDP/SORT ilk parçası page 0x59'da başlıyor (SYS 0x5C), yani code-map sayfa sayacının başlangıcı
  imaj tipine göre değişiyor: GDP/SORT 0x59, SYS 0x5C.
- Tüm imajlarda 0x20'deki 16 baytlık blob aynı: `00 01 cb 03 00 01 0d 01 e0 7f 01 00 00 00 01 04`.

---

## 9. Önceki oturumla çapraz doğrulama

`/home/schrodinger/jd1024/re/maxio_gdp_protocol.py` (14 Eyl) **farklı ve daha yeni** bir sürümden
(`MXMPTool_MAP1202_USB_V1_1_26.exe`) çıkarılmış. Bu oturumdaki V0_01_017 analizi onunla **birebir uyuyor**:

| Değer | V1_1_26 (önceki) | V0_01_017 (bu oturum) | durum |
|---|---|---|---|
| vendor write opcode | 0xC1 (fn 0x405070) | 0xC1 (fn 0x403884, `0x403a85: or al,0xc1`) | uyumlu |
| vendor read opcode | 0xC2 (fn 0x40539C) | 0xC2 (fn 0x403bb0, `0x403db1: or dl,0xc2`) | uyumlu |
| CDW14 komut magic | 0x00123400 \| sub | 0x00123400 \| sub (`0x403aa0`) | uyumlu |
| faz-1 subcode | 0xFF | 0xFF (`0x4248dc: push 0xff`) | uyumlu |
| CDW10 | nsec << 7 | nsec << 7 (`0x403a90 / 0x403dbc`) | uyumlu |
| CDW15 | nsec | nsec (`0x403ab0 / 0x403ddc`) | uyumlu |
| enable CDW14 | 0x00AE34FF | 0x00AE34FF (`0x40351b`) | uyumlu |
| disable CDW14 | 0x00BD34FF | 0x00BD34FF (`0x4037cf`) | uyumlu |
| payload başı | FF E5 | FF E5 | uyumlu |
| IOCTL | 0x2DD3C0 STORAGE_PROTOCOL_COMMAND | 0x2DD3C0 (`0x403b36: push 0x2dd3c0`) | uyumlu |

Yani taşıma katmanı iki MPTool kuşağı arasında değişmemiş. Bu oturumun yeni katkısı:
**komut baytı tablosu (dual mode0/mode1), LDBK sayfa formatı, MAS09_FWTAG konteyneri,
loader-block sayfa haritası ve download akış sırası.**


---

# 10. Ikinci tur: canli disk dogrulamasi ve uretec

Yeni dosyalar:
- `/home/schrodinger/jd1024/re/mptool/ldbk_uret.py` — loader-block sayfa dizisi ureteci
- `/home/schrodinger/jd1024/re/mptool/diff_infopage.py` — canli yedekle karsilastirma
- `/home/schrodinger/jd1024/re/mptool/uret_calistir.py` — `uretilen/` dizinini doldurur
- `/home/schrodinger/jd1024/re/mptool/uretilen/` — 52 sayfa + `MANIFEST.txt` + `infopage_V3.bin`
- `/home/schrodinger/jd1024/re/mptool/DIFF_INFOPAGE.md` — bayt bayt diff raporu

Sonuc: uretilen info page canli diskin orijinaliyle **4096 baytin 4071'inde ayni (%99.39)**.

## 10.1 `mode` ve `nsec` — her sayfa tipi icin

`VP_WriteDataToLoaderBlock(port, pageNo, A, B, buf, nsec, D)` @0x437f10
→ `VP_WritePage(port, ch, bank, blk, page, A, B, 0, buf, nsec, D)` @0x437434
→ `VC_GDP_CmdPageWrite` @0x425710:  payload[9] = **A** ("mode"), payload[10] = ((D&3)<<2)|B

| sayfa | cagri adresi | pageNo | **mode** (payload[9]) | **nsec** | bayt |
|---|---|---|---|---|---|
| InfoPage | 0x43a883 | 0 | **0** | **8** | 4096 |
| CertPage | 0x43aeb2 | wPageNo[1] | **0** | **8** | 4096 |
| LDPC x6 | 0x43a97e, aa69, ab54, ac3f, ad2a, ae15 | wPageNo[2..7] | **0** | **8** | 4096 |
| TablePage | 0x43b1a6 | wPageNo[8] | **ucLdpcMode** | **bPageSector** | 16384 |
| SlotPage | 0x43b5b0 | wPageNo[degisken] | **ucLdpcMode** | bPageSector | 16384 |
| OpalPage | 0x43b864 | wPageNo[52+i] | **ucLdpcMode** | bPageSector | 16384 |
| NandMemPage | 0x43b9e9 | wPageNo[68] | **ucLdpcMode** | bPageSector | 16384 |
| UefiPage | 0x43bba9 | wPageNo[69+i] | **ucLdpcMode** | bPageSector | 16384 |
| TMCTablePage | 0x43bce8 | wPageNo[91] | **ucLdpcMode** | **0x20** (sabit) | 16384 |
| PatternPage | 0x43d074, d0f6 | wPageNo[degisken] | **ucLdpcMode** | bPageSector | 16384 |
| **Kod sayfalari** | 0x43d740 | wPageNo[92..] | **ucLdpcMode** | bPageSector | 16384 |
| dummy | 0x43dcfb, dd5f | — | **ucLdpcMode** | bPageSector | 16384 |

SKV6 H25BFT8A1BDA icin: `ucLdpcMode = Flash.ini ECC = 2`, `bPageSector = 16 KB/512 = 32`.

**Sizin "her seyi mode=1 / 32 sektor okuduk" durumunuz ILK 8 SAYFA ICIN YANLIS.**
Sayfa 0..7 `mode=0` ve **yalniz 4096 bayt** (8 sektor) ile yazilmis; 32 sektor / mode=2 ile
okumak bu sayfalarda anlamsiz veri verir. Canli yedeginiz de zaten sayfa basina 4096 bayt
tutuyor (`b0_p*_c*.bin`), yani sayfa 0..7 icin dogru okumussunuz.
Sayfa 8+ ise mode=ucLdpcMode=2 / nsec=32.

Diger payload baytlari (loader-block yazimlarinin hepsinde): `payload[10]=1` (B=1, D=0),
`payload[11]=0`, `payload[12]=0`, `payload[13]=0` (0x437895-0x4378c5 ve 0x4375a3-0x4375e6).

## 10.2 `0x89` PageRead payload — bayt bayt

`VC_GDP_CmdPageRead` @0x425610. `0x8A` ile **ayni duzen**, tek fark komut bayti ve yon:

```
[0] = 0xFF
[1] = 0xE5
[2] = 0x89        (EnNvmeCmdMode != 0 ise 0xD9 — 0x425641: cmp ds:0x1703de8,0)
[3] = channel                       <- arg2
[4] = bank/CE                       <- arg3
[5] = (block >> 8) & 0xFF           <- arg4 (u16, BIG-ENDIAN)
[6] =  block       & 0xFF
[7] = (page  >> 8) & 0xFF           <- arg5 (u16, BIG-ENDIAN)
[8] =  page        & 0xFF
[9] = MODE                          <- arg6   ** mode burada **
[10]= arg7                          (0x8A'da ((arg11&3)<<2)|arg7, 0x89'da duz arg7)
[11]= arg8
[12]= arg11                         (0x8A'da arg13)
[13]= arg10                         (0x8A'da arg12)
veri fazi: IN, arg9 tampona, arg10 x 512 bayt
```
Tek fark 0x8A'ya gore: `[10]`'da 0x8A `((D&3)<<2)|B` maskesi uygularken (0x425794-0x42579d)
0x89 dogrudan arg7'yi yaziyor (0x4256a6); ve `[12]/[13]` kaynak argumanlari 4 bayt kayiyor.

**Okurken mode'u yazarkenki ile ayni vermelisiniz**: sayfa 0..7 icin `payload[9]=0` + 8 sektor,
sayfa 8+ icin `payload[9]=2` + 32 sektor.

`VP_ReadPage` @0x436df0 ayni sarmalayici; okuma sonrasi yine
`VC_GDP_CmdGetReturn` (`FF E5 00`) ile `buf[0]!=0xAA` beklenir, `buf[1]==1` istenir.

## 10.3 `VC_GDP_CmdGetCodeBlock` (0x07) — cagri ve donen yapi

Fonksiyon `0x425c9c`. Tek basina cagrilmaz; `VP_PROC_GetLoaderBlock` @0x4404c8 icinde
(0x440c5d-0x440cdd) su sirayla:

```
1) VP_GDP_ExecProg(port, prog=2, mode, &st, 1)            @0x43e78c
      prog==2  -> VC_GDP_CmdPreCheckCodeBlock(port, 0, mode)   = FF E5 3A 00 <mode>
      sonra Sleep(1000) + VC_GDP_CmdGetReturn dongusu, st[0]!=0xAA olana kadar
2) VC_GDP_CmdGetCodeBlock(port, buf, 1)                   @0x425caa
      payload = FF E5 07                (EnNvmeCmdMode!=0 ise 0xD4)
      veri fazi: IN, 1 sektor = 512 bayt
      (MPTool bu 512 bayti LDR_BLK.raw olarak dump ediyor - 0x440cc8)
```

**Donen 512 baytin yorumu** (0x440d7d-0x440ea3):
```
buf[ch*4 + bank]  =  u8  block map,  alt 4 bit = fiziksel blok 0..3 icin "kullanilabilir"
```
- `ch`   0 .. MaxPhyChannel-1   (`ds:0x16F2C36`)
- `bank` 0 .. MaxPhyBank-1      (`ds:0x16F2C37`)
- die yoksa atlanir: `ds:0x16F2B5F[ch*8+bank]` (multi-LUN) veya `ds:0x16F2B3F[ch*4+bank]`
  degeri 0xFF ise o (ch,bank) atlanir (0x440d35-0x440d78)

MPTool bit tarama dongusu:
```
n = 0
for blk in 0..3:
    if blockMap & (1 << blk):
        aLoaderBlockNo[port][ch][bank][n] = blk       ; u16
        n += 1
        if n == 2: break                               ; 0x440e96 cmp edx,2
ucLoaderBlockNum = n
```
Hata yolu (0x440ed3): esik yoksa ve `n < 2` ise **basarisiz**, ve buf'a su yazilir:
`buf[0]=1, buf[1]=ch, buf[2]=bank, buf[3]=n` (hangi die'in yetersiz oldugunu bildirir).

`MPTOOL.ini MPTCodeBlkThreshold` / `CodeBlockThreshold` (`ds:0x16F32ED`) != 0 ise
tek tek die yerine "gecerli die sayisi >= esik" kontrolu yapilir (0x440f29-0x440f55,
log: `Valid Code Block Die count(%d) is under Code Block Die Threshold(%d)!`).

## 10.4 Loader blok secim kurali — 11 blok DEGIL

**Duzeltme:** ilk raporda `MPTOOL.ini FWBlkQnty=11`i loader blok sayisi sandim. **Yanlis.**

Gercek kural, iki bagimsiz yerden kanitli:

**(a) `VP_PROC_EraseValidLoaderBlock` @0x4432ac** — sabit ic ice dongu:
```
for ch   = 0 .. 7      (0x443345: cmp eax,8)
  for bank = 0 .. 3    (0x443338: cmp ecx,4)
    for blk  = 0 .. 3  (0x44332b: cmp edx,4)
        if VP_IsValidLoaderBlock(port, buf, ch, bank, blk, 0):
            VP_EraseBlock(port, ch, bank, blk, 1, 1, buf)
```
**(b) `VP_PROC_GetLoaderBlock` inherit yolu @0x44054b** — `blk` dongusu yine `0..3`
(0x440c03: `cmp edx,4`).

→ **Loader blok adaylari her (kanal, CE) icin fiziksel blok 0, 1, 2, 3.**
→ GDP'nin 4 bitlik haritasi hangilerinin saglam oldugunu soyler.
→ MPTool her (kanal, CE) icin **en fazla 2** tanesini kullanir (en dusuk iki set bit).
→ Yani kotu blok atlanarak seciliyor, ama havuz sabit: 0..3.

`FWBlkQnty=11` ve `TBLBlkQnty=4`, `SYS_Qnty=2` sistem alani parametreleridir, loader blok
sayisi degil. `ucLoaderBlockNum` calisma zamaninda `ds:0xEC8170 + port*0x2066*8` icinde tutulur.

## 10.5 GetLoaderBlock / Preformat / EraseAllBlock — gonderilen komutlar

### `VP_PROC_GetLoaderBlock` @0x4404c8
Iki yol var.

**A) Inherit yolu** (onceki MP'den miras; `ds:0x16F2C28`/`0x16F2C2C` bayraklariyla secilir):
```
for ch, bank, blk(0..3):
    VP_IsValidLoaderBlock(port, buf, ch, bank, blk, 1)          @0x440034
        -> VP_ReadPage(...) page = wPageNo[92] (ds:0xA2FC9C), mode=ds:0xA2FBB2, nsec=ds:0xA2FBA8
           = FF E5 89 ch bank blkHi blkLo pgHi pgLo <ucLdpcMode> ...  (IN, 32 sektor)
        -> memcmp(buf+0x1C0, "MKSSD", 5) -> SYS FW   (0x4400a0)
           memcmp(buf+0x1C0, "MKRDT", 5) -> RDT FW   (0x4400ef)
    eslesirse:
        VP_ReadPage page = wPageNo[0] = 0, mode=0, nsec=8   -> info page  (0x440599)
        bCodeNum   = infoPage[0x40]                          (0x4405b4)
        lastPage   = infoPage[0x220 + (bCodeNum-1)*0x10 + 2] (0x4405df)
        VP_ReadPage page = wPageNo[lastPage], mode=ucLdpcMode, nsec=32  (0x440638)
        pTbl = sonKodSayfasi + 0x300
        for i in 0..0x3F:                                    (0x440b53: cmp eax,0x40)
            if pTbl[0x1C+i] & 1:
                aLoaderBlockNo[port][i/4][i%4][n++] = <bit indeksi>
        ; ayrica miras alinan FW parametreleri:
        ;   pTbl[0x74] -> ds:0xEC81E4 ,  pTbl[0x7A]+ds:0x16F2C54+ds:0x16F2C4E -> ds:0xEC81E6
        ;   pTbl[0xB4] -> ds:0xEC8172 ,  pTbl[0xB6] -> ds:0xEC8174 , pTbl[0xE4] -> ds:0xEC81EE
```
**B) GDP yolu** (inherit basarisizsa): §10.3'teki `0x3A` + `0x07` dizisi.

### `VP_PROC_Preformat` @0x441cb8
```
[opsiyonel] VP_InheritLatterBB @0x43ed88 / VP_InheritRDT @0x43f6fc   (dosya tabanli, komut yok)
VP_GDP_ExecProg(port, prog=1, mode, &st, 1)          @0x441d81
     prog==1 -> VC_GDP_CmdScanDefectBad(port, mode)  = FF E5 02 <mode>
     mode = 0x20 veya 0x04  (0x441d67 / 0x441d6d)
     ardindan GetReturn dongusu (st[0]!=0xAA)
     basarisizsa log: "GDP_PROG_GATHER fail!"
VC_GDP_CmdGetDefectBadTab(port, buf, 0x20)           @0x441da8
     = FF E5 31   (EnNvmeCmdMode!=0 ise 0xD6),  veri fazi IN, 0x20 sektor = 16 KB
     MPTool bunu DefBad.raw olarak dump ediyor
bRM_NewRemap(...)                                    @0x4163d8   (host tarafi hesap)
```

### `VP_PROC_EraseAllBlock` @0x443098
Isminin aksine **tum blogu suepuermiyor**; yalniz `wRsltBlk` (sorting sonuc blogu) tablosunda
kayitli bloklari siliyor. `ds:0x16F34EA` bayragi kapaliysa hic calismiyor (0x4430fd).
```
for ch(=[ebp-5]), bank(=[ebp-6]), lun(=[ebp-7] 0..MaxPhyBank-1):
    blk = u16 @ (0xEC4086 + port*0x80 + bank*0x10 + (ch*MaxPhyBank+lun)*2)
    if blk != 0:
        VP_EraseBlock(port, ch=[ebp-6], bank=ch*MaxPhyBank+lun, blk, p4=0, p5=1, buf)
        = FF E5 8B <ch> <bank> <blkHi> <blkLo> 00 01
```
Dikkat: loader blok silmede `p4=p5=1`, burada `p4=0 p5=1`, `VP_PROC_ClearCodeBlock`ta
`ch=0xFF bank=0xFF p4=0 p5=0`. Uc farkli kullanim.

## 10.6 Info page — ikinci turda eklenen/duzeltilen alanlar

| ofset | ne | kanit |
|---|---|---|
| 0x40 | **bCodeNum** (wEnable != 0 olan CodeMap kaydi sayisi) | 0x4405b4 `pParamS->Param.bCodeNum`; canli=12 |
| 0x70..0x8F | 32 baytlik blob (`ds:0xA32294`) | 0x438ce9 memcpy 0x20 |
| 0x90 | u16 **endpage** | 0x43a70e / 0x43a741, log "endpage is %d" |
| 0x92 | **bSlotNum** (`ds:0xA30C90`) | 0x43a2a2, log "pParamS->Param.bSlotNum = %d"; canli=5 |
| 0x140+i*0x20 | ayni 32 baytlik blob, i = 0..bSlotNum-1 | 0x43a2c7-0x43a2f4; canli 0x140,160,180,1A0,1C0 |
| 0x320 | **wPageNo[384]** (mantiksal->fiziksel sayfa) | 0x43a771-0x43a790; canli = ozdeslik |
| 0x620+0x08..0x0F | 01 01 01 01, u16 0x0064, 00, 0x0F | 0x43a79d-0x43a7cc; canli birebir |
| 0xA30 | RegMap kayit 0: 0x06000520 / (coef<<24 &0x0F000000)\|0x30202 / 0x10 | 0x43a813-0x43a83a; canli birebir |

Yardimci `0x427098`: `bit_index(v)` → `(floor(log2(v)), v_tam_ikinin_kuvveti_mi)`.
`0x11` hesabi Type'a gore dallaniyor: Type in {0,1,4,6} → `bit_index(wPages)`,
Type in {2,3,5} (MLC/TLC/QLC) → `bit_index(wPages/3)`; tam kuvvet degilse sonuc +1
(0x43897c / 0x4389db).

## 10.7 Sayfa 1 = `VP_WriteCertPage` (yeni)

Ilk raporda "info page 2. kismi" dedim — **yanlis**. Fonksiyon `0x43AE50` =
`VP_WriteCertPage`, `CertPage.raw` dump ediyor, icerik
`memcpy(buf, ds:0xA31694, ds:0xA30C96)` (0x43ae87). Blob'un uretimi **BILINMIYOR**.

Canli diskteki sayfa 1 icerigi gozlemle cozuldu (yalniz 40 bayt dolu):
```
+0x20 u32 = adet (canli 12 = bCodeNum)
+0x30 itibaren (u32 dest, u32 length) ciftleri
wEnable == 1 olan CODE_ENTRY'ler listeye DAHIL DEGIL
```
Canli 12 cift, CodeMap kayitlari 0..9 + 12,13 ile birebir ortusuyor (10 ve 11'in
wEnable'i 0x0001). `ldbk_uret.py` bunu bu gozleme gore uretir — `guven = GOZLEM`.

## 10.8 Uretecin uretemedigi sayfalar (durust liste)

| sayfa | neden |
|---|---|
| wPageNo[8] TablePage | icerik calisma zamani erase-count/remap tablolarindan; statik kaynak YOK |
| SlotPage | sayfa indeksi degisken, kaynagi izlenemedi |
| OpalPage (52+i) | `DAT/opal.bin` var ama sayfa indeksi tam dogrulanmadi |
| UefiPage (69+i) | `DAT/NvmExpressDxe.rom` var ama sayfa indeksi tam dogrulanmadi |
| NandMemPage (68) | dosya yolu `DAT/<SKVx>/<Nandmem>_<clock>/nandmem_*.bin`, SKV6 karsiligi pakette YOK |
| CODE_ENTRY.wEnable | `ds:0xA35FF8` dizisini dolduran kod bulunamadi; SYS/*.bin basliginda da YOK (0x130..0x16F sifir, 0x170..0x26F 0xEE dolgu, 0x270..0x28F 32 baytlik hash) |
| 0x48 / 0x4A / 0x4B | MPTool surum farki |
| 0x90 endpage | formul kanitli, coklu-slot sayac birikimi degil |
| 0x70..0x8F blob | uretimi bilinmiyor |
| 0xA40+ RegMap 1..4 | bu build yazmiyor |

Bu alanlarin hepsi icin **orijinal yedegi kopyalamak** dogru yaklasim; uretec
`orijinal_info_page=` ve `slot_blob32=`/`bslotnum=`/`code_wenable=` parametreleriyle
bunu destekliyor.
