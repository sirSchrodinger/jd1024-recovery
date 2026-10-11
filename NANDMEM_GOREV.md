# Görev: `nandmem_SKV6_page.bin` reconstruction (JD1024 onarımı — son parça)

## ✅ SONUÇ (2026-09-24 gece) — ÜRETİLDİ, byte-exact doğrulandı
- **Çıktı:** `mptool/map1202tool/DAT/SKV6/001_{200,266,333,400,533,600}/nandmem_SKV6_page.bin`
  (her biri 5712 B). VM'e taşıma imajı: `~/jdvm/nandmem_skv6.img` (FAT, içinde `SKV6/`).
  Araç: `re/mptool/nandmem_uret.py` (`--selftest`, `--verify-page`).
- **Format (219/219 vendor dosyasında tutuyor):** header pointerları `(offA, lenA, offB, lenB)`;
  `offB = 0x20+lenA`, `offB+lenB = dosya boyu`. Blob = tag(0x20) + payload. Stamp[2:4] = ucode
  clock BCD (`10 66` = 1066).
- **Kaynak kuralı:** ucode section header'ı (+0x10, 8×u32) → blob A = section+0x1000 (lenA),
  **blob B = section+0x2000 (lenB)**. DAT = header + ikisi. Aynı paketteki ucode'dan
  **JGS3 001_600 referansı byte-identical**; ayrıca JGS2 ve N38B tüm clock'lar (34/34 aynı-build
  identical; 111 non-identical'ın hepsi farklı build stamp'i, karşı-örnek 0).
- **Doğru build:** `MAP1202_H25TXTD2XCX6/SORT/ucode.bin` (sha1 227c4336…) içindeki SKV6
  2023-05-26 build'i. `SKV6_001_1066` → üretilen dosya, diskin page 68'iyle (die c0ce0 + die
  c3ce2, 8+ okuma) **5712 B byte-identical** → `001_533` = fabrika dosyasının kendisi.
  `001_600` aynı build'in 1200 section'ı; farkı sadece gecikme operand'ları (clock'la lineer).
- **Fabrika 001_533 (1066 MT/s) kullanmış**, VM'deki MPTOOL.ini `Clock=600` istiyor. İkisi de
  hazır; en muhafazakâr = `Clock=533` + 001_533 (fabrika dosyası birebir).
- **001_800 ÜRETİLMEDİ:** hiçbir ucode'da SKV6_1600 section yok; uydurmak = spec dışı timing.
- **Aşağıdaki orijinal brief'teki yanlışlar:** (1) "SKV6 pointerları 0x20/0x850/0x870/0xd38"
  aslında SKV7'nin; SKV6 = 0x20/0x8d0/0x8f0/0xd60. (2) "blob B ucode'da yok" yanlış (+0x2000).
  (3) BLOB_A_ONLY dosyası 2022-04 build'den + payload'ı kırpık (0x810/0x830) — KULLANMA.
  (4) ucode blob A + loader blob B birleştirme planı iki farklı build'i karıştırırdı.
- **Açık risk notları:** VM `DAT/ucode.bin` (HYV7) SKV6'yı 2022-04 build'iyle taşıyor (MP-time
  ↔ runtime build farkı; vendor paketlerinde de olağan). VM MPTOOL.ini
  `ExtParaFile=Para_DW_SKV7_…ini` — SKV6 disk için SKV7 para dosyası, ayrıca bakılmalı.

> Bu, kendime ait, içi **boş**, arızalı bir NVMe SSD'yi (JamesDonkey JD1024, MAXIO MAP1202 +
> SK hynix V6 NAND) onarmanın SON adımı. Fabrika MP aracı (MXMPTool) çalışıyor ve diski gördü;
> tek eksik, SK hynix V6 NAND'ın **NAND parametre dosyası** `nandmem_SKV6_page.bin`. Bu dosyayı
> diskin KENDİ firmware dump'ından yeniden inşa etmen gerekiyor. Tümü diskteki dosyalardan
> statik + dosya üretimi; cihaza komut YOK. Çıktı: geçerli bir ~5104 baytlık `.bin`.

## 0. Tek cümlelik görev
Diskin kendi loader dump'ından (`kanit/loader_v4/src_p68_m2.bin`) SK hynix V6 NAND'ın nandmem
tablosunu çıkarıp, MXMPTool'un beklediği **MP DAT formatında** `nandmem_SKV6_page.bin` üret
(hedef: `001_600` clock; ideal olarak tüm clock'lar 001_200..001_600).

## 1. Neden gerekli (bağlam)
- MXMPTool_MAP1202_USB, diski ROM-GDP modunda görüyor, MP'yi başlatıyor, ama şu dosyayı arayıp
  bulamıyor: `C:\MPT\DAT\SKV6\001_600\nandmem_SKV6_page.bin` (ve muhtemelen `001_800`).
- Bu dosya konunca MP tamamlanacak: erase + bad-block sort → arızalı die-b (CE2/CH3, 226 bad blok)
  otomatik dışlanır → 15-die temiz, **yazılabilir** disk. (Tüm diğer parçalar hazır: MP tool,
  GDP.bin, Flash.ini'de bizim `SKV603005 H25BFT8A1BDA` girdisi, ucode.)
- Geniş bağlam: `ANALIZ_BRIEF_2026-09-24.md` §13 (MXMPTool detection çözümü + bu blokaj).

## 2. Dosya formatı (KANITLI — `kanit/fw_hunt3/ucode_nandmem.py` başlığından + ölçümlerden)
`DAT/<NAND>/001_<clk>/nandmem_<NAND>_page.bin` = **iki ardışık LDBK blob'u**:
- **blob A** = `[0x0000 .. 0x0870)` : header(0x20) + tag/stamp(0x20) + payload **2064 B**.
- **blob B** = `[0x0870 .. EOF)` : ikinci header + tag/stamp + payload **3384 B**.
- header(0x20): `"LDBK NANDMEM TAB "` (0x10) + 4 little-endian pointer (0x10).
- name (blob başı +0x20): `"CLT_5V_XINYH\x00\x00"` (SKV6 profil adı) + build stamp.

**Referans (tam, çalışan) dosya:** `mptool/map1202tool/DAT/JGS3/001_600/nandmem_JGS3_page.bin`
(5104 B). Header pointerları: `0x20, 0x730, 0x750, 0xca0`. İsim `LOV_0609_2X_CTMY`. Yapıyı buradan
birebir çıkar (blob A/B sınırları, tag/stamp/payload düzeni). 001_800 versiyonu 4992 B.

**Gerçek SKV6 dosyasının pointerları (DURUM §481'de ölçülmüş):** `0x20, 0x850, 0x870, 0xd38`.
Yani blob A payload biraz farklı boyda; JGS3 ile birebir aynı offset DEĞİL — SKV6 kendi
pointerlarını taşır. Referans yapıyı anla, SKV6 verisiyle doldur.

## 3. blob A: ZATEN ÜRETİLDİ (ucode'dan)
`kanit/fw_hunt3/skv6_from_ucode/DAT/SKV6/001_600/nandmem_SKV6_page_BLOB_A_ONLY.bin` (2160 B).
- `ucode_nandmem.py`: blob A payload = `DAT/ucode.bin` içindeki CLT_5V section'ın `+0x1020`'si
  (SKV7'de 6 clock'ta byte-identical doğrulandı). ucode'da CLT_5V offsetleri: 905216, 909312, ...
  (0x4000'lik section'lar; section: name@+0x000, tag@+0x1000, payload@+0x1020).
- Clock eşlemesi: **DAT label = ucode label / 2 (DDR)**. DAT 600 ← ucode 1200; 533←1066; 400←800;
  333←667; 266←533; 200←400.

## 4. ⭐ blob B: EKSİK KAYNAK BULUNDU — diskin kendi loader'ı
`ucode_nandmem.py` "blob B ucode/GDP/SORT/SYS/tmc'de YOK" diyor — AMA **diskin kendi loader
dump'ına bakmamış**. Bu oturumda bulundu:
- **`kanit/loader_v4/src_p68_m2.bin`** (16384 B decoded loader sayfası): başında `"LDBK NANDMEM
  TAB"` (@0x00), `"CLT_5V_XINYH"` (@0x22), ardından NAND komut tablosu (payload):
  `0b 08 00 00 eb 6c 00 00 48 05 80 ff / ...80 fe / ...80 fd ...` (12-baytlık entry'ler,
  clock/mode başına azalan sayaç).
- Bu, diskin ÇALIŞAN runtime nandmem'i = blob A + blob B payload'unun ikisini de taşıyor olmalı.
  Loader runtime formatı ≠ DAT dosya formatı; eşlemeyi çöz.
- Ayrıca `kanit/loader_v4/src_p68_m2.bin` dışında loader'ın NANDMEM'i pages 68/119/164/209/254/299'da
  (bunlar aynı LDBK NANDMEM içeriğinin slot kopyaları olabilir — karşılaştır).
- **Doğrulama kancası:** blob A payload'u ZATEN elimizde (§3). Loader'daki payload bölgesinin blob A
  ile ÖRTÜŞEN kısmını bul (aynı `0b 08 00 00 eb 6c...` dizisi) → hemen ardından/başka slotta gelen
  kısım blob B payload'udur. blob A ile hizala, kalanı blob B olarak çıkar.

## 5. Alternatif kaynaklar (blob B için, loader olmazsa)
- `kanit/fw_hunt3/ex/A2-YMTC-...-SN08413-V2/.../BIN/SKV6/nandmem_SKV6_{sdr_page1,ddr_page2}.bin`
  (16384 B × 2, ESKİ MAS0902 2-dosya formatı). Farklı controller ama AYNI SKV6 NAND → payload
  içeriği eşleşebilir; formatı MAP1202 DAT'ına dönüştür.
- `re/fw_canli/e*.bin` (canlı segment dump'ları) — nandmem RAM'e yüklenmiş olabilir.
- Diskin diğer 15 die'ının blok 0 kopyaları (loader her die'da) — `re/` ve GDP-tünel dump'ları.

## 6. Üretim + doğrulama
1. Referans JGS3 dosyasının tam yapısını byte-byte çöz (blob A/B header, pointer, payload sınırları).
2. blob A (§3, ucode'dan) + blob B (§4, loader'dan) payload'larını doğru header/pointer/tag ile
   birleştir → `nandmem_SKV6_page.bin` (~5104 B). En az `001_600`; mümkünse tüm clock'lar.
3. `re/mptool/ldbk_uret.py` ve `kanit/fw_hunt3/ucode_nandmem.py`'yi yeniden kullan/genişlet.
4. **Doğrulama:** üretilen dosyayı `mptool/map1202tool/DAT/SKV6/001_600/` (ve 001_800) altına koy
   + mptool.img'e kopyala. Alperen MXMPTool'da START'a basınca "nandmem bulunamadı" hatası GİTMELİ
   ve MP Flash Interface (Check LDPC / Data Path / Calibration) adımlarını geçmeli. Geçmezse
   payload/pointer hizalaması yanlış — JGS3 ile diff'le.
5. ⚠️ **Yanlış nandmem = MP sırasında NAND korruption riski.** Güvenlik: her iddiayı JGS3 referans
   yapısıyla doğrula; blob A'nın ucode↔üretilen byte-identical'liğini teyit et; blob B'yi loader'dan
   çıkarırken payload dizisinin blob A'nın devamıyla tutarlı olduğunu göster. Emin değilsen ÜRETME.

## 7. Ana dosyalar
- Kaynak: `kanit/loader_v4/src_p68_m2.bin` (blob B!), `mptool/map1202tool/DAT/ucode.bin` (blob A,
  CLT_5V@905216+), `kanit/fw_hunt3/skv6_from_ucode/DAT/SKV6/*/nandmem_SKV6_page_BLOB_A_ONLY.bin`.
- Referans format: `mptool/map1202tool/DAT/JGS3/001_600/nandmem_JGS3_page.bin` (5104 B, tam).
- Araçlar: `kanit/fw_hunt3/ucode_nandmem.py`, `re/mptool/ldbk_uret.py`.
- Hedef: `mptool/map1202tool/DAT/SKV6/001_600/nandmem_SKV6_page.bin` (+ 001_800).
- Bağlam: `ANALIZ_BRIEF_2026-09-24.md` §12-§13, `DURUM_2026-09-19.md` §479-481.
