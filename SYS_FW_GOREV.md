# Görev: `YI0PCA2C.bin` (SYS firmware) — JD1024 MP'nin 2. eksik dosyası

> Kendime ait, boş, arızalı NVMe SSD onarımı (MAP1202 + SK hynix V6, NAND H25BFT8A1BDA,
> ID `AD 7E 28 53 02 B0`). MXMPTool çalışıyor; nandmem'i (senin ürettiğin) geçti, şimdi
> **SYS firmware** istiyor. Cihaza komut YOK — sadece diskteki dosyalardan analiz + üretim.
> Çıktı: geçerli bir `.bin` (~692–725 KB, `MAS09_FWTAG_V001` formatı).

## 0. Tek cümlelik
MXMPTool START → `C:\MPT\SYS\YI0PCA2C.bin` bulunamadı diyor. Bu, bizim diskin product
firmware'i. Ya elimizdeki en-yakın firmware'i (aynı NAND) uyarla/doğrula, ya diskin kendi
dump'ından üret; sonuç `mptool/map1202tool/SYS/YI0PCA2C.bin` (VM'e taşınacak).

## 1. SYS firmware isim yapısı (KANIT)
İsim = `[proje 4]` + `[config 4]`. Elimizdeki örnekler, **config `CA2C` ORTAK**:
- MP'nin istediği: **`YI0P`+`CA2C`** (bizim diskin projesi; gated HYV6 paketinde).
- `YIQZCA2C.bin` (HYV7 paketi, proje `YIQZ`, 2022-06 build, SKV7): `re/dis_kaynak/.../HYV7.../T1/SYS/`
- **`YIC5CA2C.bin` (proje `YIC5`, 2024-11 build) — AYNI config `CA2C`, ve paketi BİZİM TAM NAND'ı
  destekliyor** (bak §2). `kanit/fw_hunt3/ex/MAP1202_H25TXTD2XCX6/.../SYS/YIC5CA2C.bin` (708608 B).
Format: header `MAS09_FWTAG_V001`; içinde `MKSSD_...,MAP1202,<proje><config>` + `r:/...` build path.

## 2. ⭐ EN YAKIN KAYNAK: H25TXTD2XCX6 paketi (nandmem de buradan geldi)
`kanit/fw_hunt3/ex/MAP1202_H25TXTD2XCX6/MAP1202_H25TXTD2XCX6/`:
- **Flash.ini'de BİZİM TAM NAND:** `Name004=SKV606411 H25BFT8A1BDA 2888 1536 16 ... AD 7E 28 53 02 B0`
  (bizim ID birebir). Yani bu paket bizim NAND'ı resmen destekliyor.
- SYS: `YIC5CA{1,2,3,4}C.bin`, `YIC5CB4C.bin` (proje YIC5, 708–725 KB).
- SORT/ucode.bin: **nandmem'in byte-exact geldiği 2023-05-26 SKV6 build** (sen doğruladın).
- ⚠️ DAT/ = `SKV8` (nandmem'i değil), PARA = `Para_DW_SKV8_PGR_FULL.ini`, MPTOOL.ini `Clock=600` —
  yani paket **çok-NAND** (SKV6+SKV8); DAT/para SKV8-yönelimli. SYS firmware'in NAND'a bağlı kısmı
  Flash.ini + nandmem + para ile besleniyor; SYS kod tarafı proje-build.

## 3. GROUND TRUTH: diskin KENDİ firmware'i (nandmem'de olduğu gibi doğrulama kaynağı)
Diskin çalışan firmware'i NAND'da; dump'larımız:
- `kanit/nand_yedek_20260915/blok0_tam.bin`, `kanit/c3ce2_blok0_tam.bin` (blok 0 ham),
- `kanit/loader_v4/src_p*.bin` (die 0 blok 0 loader, 360 decoded sayfa),
- `re/fw_canli/e*.bin` (firmware segment/RAM dump'ları — MAS09_FWTAG SYS içeriği burada olabilir).
- Diskin proje string'ini bul (`MAP1202,YI0PC??` / `MKSSD_...` / `HYV6_64GB_SVN13202`) → hangi
  config (`CA2C`?) ve build bizimki, kesinleştir. (nandmem'de page 68 ground-truth'tu; burada da
  diskin kendi SYS içeriği ground-truth.)

## 4. Karar (senin) — 3 aday, en güvenlisini seç + gerekçelendir
- **(a) YIC5CA2C.bin'i kullan** (aynı NAND, aynı `CA2C` config, sadece proje YIC5≠YI0P). `YI0PCA2C.bin`
  olarak yeniden adlandır. En hızlı; ama içindeki proje/tag string'i YIC5 kalır — MP kabul eder mi,
  ve diskin gerçek firmware'iyle kod olarak uyumlu mu, diskin dump'ıyla **karşılaştırarak** doğrula.
- **(b) YIC5CA2C tabanı + bizim proje/NAND alanlarını yamala** (ldbk_uret.py / nandmem yaklaşımı gibi;
  MAS09_FWTAG içindeki proje string + NAND-parametre section'larını diskinkine hizala).
- **(c) Diskin kendi SYS firmware'ini dump'tan yeniden paketle** (en otoritatif; en zor — MAS09_FWTAG
  section'larını ham NAND/loader'dan çıkar).
En az risk hangisiyse onu üret; her iddiayı MAS09_FWTAG format + diskin kendi dump'ıyla doğrula.
**Yanlış SYS firmware = MP Download'da diski bozar; emin değilsen üretme.**

## 5. Ek: para dosyası (sıradaki muhtemel blokaj)
VM MPTOOL.ini `ExtParaFile=Para_DW_SKV7_64GB_FULL_NO_RAID.ini` (SKV7). Bizim NAND SKV6. H25TXTD2XCX6
paketinde `PARA/Para_DW_SKV8_PGR_FULL.ini` (SKV8) var. Doğru SKV6 para dosyası gerekebilir —
mümkünse onu da diskin config'inden türet/uyarla, ya da hangi para'nın NO_RAID/capacity açısından
bizim 15-die (die-b dışlanmış) hedefimize uygun olduğunu belirle.

## 6. Doğrulama + teslim
- Üretilen `YI0PCA2C.bin`'i `mptool/map1202tool/SYS/`'e koy + VM taşıma imajına ekle (nandmem'deki
  `nm2.img` + `kopla.bat` desenini kullan; kopla.bat'a `SYS` kopyasını da ekle).
- Başarı ölçütü: Alperen START'a basınca "YI0PCA2C.bin bulunamadı" GİTMELİ ve MP Download/Flash
  Interface adımlarını geçmeli. (Sonraki hata para dosyasıysa §5.)
- Bağlam: `ANALIZ_BRIEF_2026-09-24.md` §13-§14, `NANDMEM_GOREV.md` (senin nandmem çözümün).
