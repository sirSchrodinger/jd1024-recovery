# AJAN BRIFINGI — JD1024 / MAXIO MAP1202 MPTool hatti (20 Eyl 2026)

## Hedef
1 TB JamesDonkey JD1024 (MAXIO MAP1202 DRAM-less, SK hynix V6 TLC, 16 die) salt-okunur
kaldi. Firmware kendi ic durumu `mod=4` ile yazmalari yutuyor. Diskin icerigi FEDA
EDILEBILIR — amac diski tekrar yazilabilir hale getirmek. Yikici islem serbest.

## Simdiye kadarki kanitlar (tekrar arastirma, dogru kabul et)
- ROM boot loader'i **donanim kripto ile imza dogruluyor** (`LOADER_CERT_TAG1`, motor
  reg `0x06700480/484/488`). Bizim yamaladigimiz loader'lar ASLA boot edemedi.
  MAXIO'nun kendi imzali loader'i (GDP.bin/SORT.bin) bu duvari dogal olarak gecer.
- Urun firmware modunda vendor tunel (`0xC1`/`0xC2`, magic `0x00AE34FF` enable /
  `0x001234FF` send / `0x00123486` receive) sadece `0x86 ReadRam` isleyicisine sahip.
  `0x87 WriteRam` urun modunda NO-OP. Tel takip ROM/GDP moduna alininca `0x87` gercek
  calisiyor ve NAND yazma 15 die'da aciliyor.
- Canli register: `mod (0x00810CE8) = 4`, `assert sayaci (0x040EEE58) = 3`,
  `Func0 (0x00000398) = 0x0001F80A` (bit3 = EnWriteProtectAbort).
- Disk asinmamis: life left %100, erase fail 0. Arizanin kaynagi ani guc kesintileri
  (520 unsafe shutdown) -> die 12 blok 77 sayfa 1'de FTL sayfasi oldu -> assert -> mod=4.

## Elimizdeki MPTool kiti (Windows PE VM icinde C:\, host'ta /mnt/mpt)
- `/mnt/mpt/MPT/`  = MPT_Cougar_C_0_1_017 kiti (ReleaseNote.txt: "Support SKV6-128GB/die",
  SORT.bin "update SKV6 ucode", GDP.bin "support hynix v6 1Tb")
  - `MXMPTool_MAP1202_PCIe_A.exe` / `_PCIe_B.exe` / `_USB_V0_01_017.exe` (6494840 B, ayni boy)
  - `MXUtility_MAP1202_V0_011.exe` (CALISIYOR — diski goruyor, tarama yapiyor)
  - `GDP.bin` (233472 B), `SORT/SORT.bin` (282624 B), `Flash.ini`, `MPTOOL.ini`
  - `DAT/mem.ini` — icinde `[SKV6_001_1]`, `[SKV6_001_2]` bolumleri VAR
  - `SYS/YIQZCA2C.bin` vb. (MKSSD_501003000092860000, Jun 21 2022)
  - `PARA/Para_DW_SKV7_64GB_FULL_NO_RAID.ini`, `PARA/Para_NULL.ini`
  - `TMC/TMC_ARRAY_Default_M2_HynixV7.ini` + TMC0..TMC14.ini
- `/mnt/mpt/MPT2/` = daha yeni kit: `MXMPTool_MAP1202_USB_V1_1_26.exe`,
  `MXUpdater_MAP1202_V1_10.exe`, `MXUtility_MAP1202_V1_11.exe` (bu surum bizim FW'de
  "doesn't run on system mode" hatasi veriyor — aracin bug'i, cozuldu)

## Diskin gercek kimligi
- Flash ID: `0xAD 0x7E 0x28 0x53 0x02 0xB0` -> Flash.ini `[Hynix] Name007`:
  `SKV603005  H25BFT8A1BDA  3 2 1  2888 1536 16 1 2 ... 11 4 3000 001 2048 100`
  (Vendor=Hynix, Type=TLC, CE/Package=1, Blocks/CE=2888, PageNum=1536, PageSize=16K,
   Die/CE=1, ECC=Rate2, Interface=11, Plane=4, Endurance=3000, SpareByte=2048, Gpio=100)
- 4 kanal, 16 flash ID (4ch x 4CE), FW surumu `ZI0PCD2C`
  (`MKSSD_501003000124620000, Oct 31 2023`)
- MPTOOL.ini SU AN YANLIS AYARLI: `FlashUniName=SKV703001` (V7!), `FWOneBinName=SKV7.bin`,
  `TMCFolder=TMC_ARRAY_Default_M2_HynixV7.ini`, `ExtParaFile=Para_DW_SKV7_64GB_FULL_NO_RAID.ini`

## Ortam
- kaplikaya (`ssh kaplikaya`), r2/radare2 var. T440'ta objdump var.
- Diski Windows PE VM'e vfio-pci ile passthrough ettik; VM acik (VNC kaplikaya:5907).
- Imaj host'tan `/mnt/mpt` olarak salt-okunur mount'lu.

## KURAL
- Sadece OKU/INDIR/ANALIZ ET. Hesap acma, foruma yazma, DM/mail YOK.
- KIOXIA sistem diskine (`01:00.0`, `1e0f:003b`) DOKUNMA. Cihazi MODELE gore bul.
- "Komut basarili dondu" kanit DEGIL. Iddiayi disasm satiri / dosya ofseti ile destekle.

═══════════════════════════════════════════════════════════════════════════
## EK BRİFİNG (gece) — WIRE/GDP oturumu durumu + yeni hedef
═══════════════════════════════════════════════════════════════════════════
DURUM: Tel takılı, JD ROM/GDP moduna geldi (`Generic_Loader_NVMe_Device L190301R`), vendor
tünel çalıştı (0xC1/0xC2, ReadRam/Identify OK). AMA ev-yapımı NAND tooling'i (JDisk/JD.init)
ROM-GDP ile UYUMSUZ: `stub_kur` CMDTBL(0x040ED2F4) okuyamadı (farklı bellek haritası), ve
`JD.init` stub tabanlı RAM-poke'lar (YAMA_ADR/LDPC/TMC @0x040Cxxxx) yapıyor — ROM-GDP'de yanlış.
`jd_loader.py gdprun` koşuldu → ROM-GDP'yi ezip vendor tüneli ÖLDÜRDÜ (tekrarlanmayacak).

YENİ HEDEF: **MPTool-native, STUB'SIZ GDP protokolü.** MPTool NAND'ı sadece temiz vendor
komutlarıyla sürüyor: InitGDP(0x11,DPD) → ReadFlashID(0x88) → PageRead(0x89)/PageWrite(0x8A)/
BlockErase(0x8B). Komut encoding'leri `ANALIZ_MPT_KOMUT_TABLOSU.md`'de tam. Kaynak loader elde:
`kanit/c3ce2_blok0_tam.bin`. Fix: DPD Func0(@0x98) bit3=0 (WP off), boot-öncelikli die'a yaz.
