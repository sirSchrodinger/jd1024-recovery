# DENETİM — taze göz, RAPOR.md (5076 satır) baştan sona okundu

_15 Eylül 2026 · offline · yorum değil, rapordan alıntı + satır numarası_

Kapsam: `RAPOR.md` tamamı + çapraz kontrol için `takim/*.py`, `takim/OKUMA.md`,
`re/ANALIZ_*.md`, `re/gdp_local/BULGULAR.md`, `araclar_20260915/*.py`.

---

## A) ÇELİŞKİLER

### A1 · §52 başlığı hâlâ "fiziksel hasar YOK" diyor, §76/§78 "fiziksel olarak ölü" diyor
- L3852: `## §52 — ✅ **KALICILIK KANITLANDI: veri NAND'da duruyor. Fiziksel hasar YOK.**`
- L4980: "Program/silme yolu **fiziksel olarak ölü** ve arıza **tüm die'lar tarafından paylaşılıyor**"
- L5069-5070: "→ **§76'nın sonucu, tel değişkeni düzgün elendikten sonra da geçerli.**"
- §52 hiçbir yerde geri alınmadı; belge iki zıt hükmü aynı anda taşıyor.

### A2 · "Tek sahtelenemez kanıt" protokolü sonradan çürütüldü, ama ona dayanan sonuçlar ayakta
- L4151-4152 (§56.3): "**Reload:** yaz → `gdprun` → oku. Tek sahtelenemez kanıt budur. §52'nin 6/6'sı bu protokolle alındı; **o sonuç gerçekti**."
- L4498-4501 (§63): "Staging tamponu `0x04074EC0`, GDP imajının DIŞINDA. `gdprun` onu silmiyor. Dolayısıyla **'reload testi' de sahtelenebilir** — projede iki kez 'tek sahtelenemez kanıt' diye kullandığım protokol **aslında kanıt değilmiş**."
- Buna rağmen L4297 (§58.3) hâlâ "§52'nin 6/6 kalıcılığı alındı" diye olumlu atıf yapıyor.
- Sonuç: §51 (L3774), §52 (L3852), §55 (L4037) başlıklarının tamamı kanıt temeli kalkmış hâlde ✅ işaretiyle duruyor.

### A3 · "ch2/ch3'e dokunma" kuralı çürütüldü ama HÂLÂ TESLİM EDİLEN KODDA
- L4293 (§58.3 KURAL): "**ch2 ve ch3'e asla işlem gönderme.** Tek bir silme bile diski bozar."
- L4303: "Kapasite tavanı 16 die değil, en fazla **8 die** (ch0 + ch1) → ~512 GB"
- L4322-4323 (§60): "§58'in 'ch2/ch3'e dokunma' kuralı ve §59'un ... teşhisi **ikisi de yanlış premise dayanıyordu.**"
- L4364-4366: "**'ch2/ch3'te die yok' (§58) YANLIŞ.** ... Sekiz die'ın sekizi de legacy'de doğru ID veriyor."
- L4831 (§73): "`[legacy] bulunan die = 16`"
- **Ama:** `takim/jdmap.py:36-37` → `# §58: ch2/ch3'te die YOK — dokunma, tum okuma yolunu bozar` / `KANAL_GUVENLI=(0,1)`. Harita aracı hâlâ yarım diski atlıyor.

### A4 · Blok 1500 aynı belgede hem sağlam, hem kötü, hem kontrol bloğu
- L3818 (§51.3): "Blok 1500 `0101e0ff` verdi → **sağlam**, tur tamamlandı."
- L3883-3884 (§52.3): "blok 1500 turunda 15/16 die yaz/oku turunu geçti"
- L3889 (§52.4, kötü blok listesi): "`1320 1440 **1500** 1560 ...`"
- L4058 (§55.2): "| 1024, 1500 | temiz (`e1` yok!) | başarısız (`sts0=00000080`...) |"
- **Ve:** `takim/tezgah.py` → `kontrol=(1200,1500)` — şaibeli blok, *dokunulmamış kontrol bloğu* olarak kullanılıyor.

### A5 · NAND kimliği üç kez değişti, §1 hiç düzeltilmedi
- L52-53 (§1): "**SK hynix H25T1TB48E** ... 512 Gbit/die, 4 die/paket → toplam 16 die"
- L3456 (§48.1): "NAND'ımız `H25T1TB48E` **değil**, **`H25BFT8A1BDA`**"
- L4770 (§72): "model | **`H25BFT8D4B8R-BDJ`** (kayıtlardaki `H25BFT8A1BDA` değil)"
- Raporun kimlik tablosu (§1) hâlâ ilk, iki kez çürütülmüş adı taşıyor.

### A6 · Blok sayısı: her yerde 2888, die'ın kendi beyanı 2732 — DPD hiç güncellenmedi
- L3045/L3453: `Blk=2888` (Flash.ini `SKV606411`), L4215/L4256: "2888 blok × 1536 sayfa × 16 KB × 16 die"
- L4773 (§72, die'ın JEDEC parametre sayfası): "| LUN başına blok | **2732** |"
- `takim/ortak.py:26-29` hâlâ `dpd_clk200.bin` (SKV606411 = 2888/4-plane) yüklüyor; `takim/jdmap.py:16` "die basina 2888 blok".
- §72 farkı prosa olarak not etti (L4776), **hiçbir ölçüme/adreslemeye yansıtmadı.**

### A7 · Plane sayısı: 4 mü, 2 mi, etkisiz mi?
- L4205-4208 (§57.3): "**Plane 1..3 hiç kullanılmamış** ... Flash.ini bu parçanın **4 plane**'i olduğunu söylüyor → **bir 4× daha.**"
- L4730 (§70): "plane 0/1/2/3 | dördü de AYNI -> **plane parametresi etkisiz**"
- L4776 (§72): "**plane sayısı** | **2** (eski kayıtta 4 yazıyordu — yanlış)"
- `takim/cekirdek.py` hâlâ `rf=b*4+plane` (yani 4-plane varsayımı) kullanıyor.

### A8 · FlashID byte2: §31.1 "birebir bizim" dediği kayıt yanlış çıktı, §31.1 düzeltilmedi
- L1646-1649 (§31.1): "`Name005=SKV606412 ... 0xAD 0x7E 0x29 0x53 0x02 0xB0` = **bizim FlashID'imiz, birebir.**"
- L2231-2236 (§38): "`AD 7E 28 53 02 B0` ... **Byte 2 = 0x28, beklediğimiz 0x29 DEĞİL.**"

### A9 · FLR üç farklı hükümle kayıtlı
- L3098 (§46.9): "**PCIe FLR ... kilitlenmiş kontrolcüyü TAMAMEN kurtarıyor**"
- L3319 (§47.9): "~10 FLR'nin 2'sinde cihaz config space'e geri dönmedi"
- L4484 (§62b): "PCIe FLR ... **DURUMU KÖTÜLEŞTİRİR** — cihaz veri yolundan tamamen düşer"

### A10 · "Güç çevrimi gerekmiyor" vs "tam soğuk güç çevrimi şart"
- L2519 (§42.3): "Sonuç: **güç çevrimi gerekmiyor.** Bekle ve yeniden yokla."
- L4030 (§54.5): "`0x3A PreCheckCodeBlock` | **kontrolcüyü tamamen kilitler** ... **tam soğuk güç çevrimi şart.**"

### A11 · §43.7'nin ilan ettiği kök neden hiç geri alınmadı
- L2663: "**NAND, SET FEATURE komutuna cevap vermiyor.**" — "arıza noktası kesinleşti" başlığı altında.
- L3598 (§49.1): `0x49 → **DONE, 1. turda, getfTO=0**` — yamasız. §43.7 sessizce geçersizleşti, kayda geçmedi.

### A12 · LDPC yazma yolu: "çalışıyor" ve "çalışmıyor"
- L4071-4073 (§55.3): "`yaz(ldpc=1,scr=1) -> oku(ldpc=1,scr=1)  ESLESTI` ... **ECC korumalı yazma/okuma da elde.**"
- L4682-4683 (§68): "**LDPC encoder.** Okuma (decoder) çalışıyor, **yazma (encoder) çalışmıyor.**"

### A13 · Silme adres kodlaması açıkta bırakıldı, araç yine de tek kodlamayı sabitliyor
- L3998 (§54.2 komut kartı): "silme | ... | **doğrudan blok no**"
- L4546 (§65): "| **`b*1536`** | BAŞARILI | **EVET** — içerik değişti"
- L4596 (§67): "**§65'in ... sonucu YANLIŞTI.**"
- Geriye doğrulanmış tek kodlama kalmadı; `takim/cekirdek.py:sil()` ve `tezgah.py:sil()` düz blok numarasını sabitliyor.

### A14 · "Mod geçişi yasak" kuralı ile §78'in kendi protokolü çelişiyor
- L4887-4888 (§74): "**Geçerli protokol:** mod geçişini ölçümden ÖNCE yap, sonra duruma dokunma"
- `takim/tezgah.py` docstring: "MOD GECISI deney sirasinda toggle<->legacy gecisi **YASAK**"
- L5033-5035 (§77, çalıştırılan betik): "`telsiz.py`: toggle ID'leri → referanslar → **legacy** die durumu → silme → 16 die taraması → **toggle'a dönüp** içerik karşılaştırması"
- L5065 (§78): "Ölçümün geçerliliği: ... **mod geçişi yok**". İki ifade aynı koşu için verilmiş.

### A15 · §59 diye bir bölüm YOK
- L4322 §59'a atıf yapıyor ("zamanlayıcılar 125× kısaydı" teşhisi), belgede `§59` başlığı hiç yok. Geri alınan bir bölüm silinmiş, atıf kalmış.

### A16 · ÖZET (L6-37) hâlâ 12 Eylül'ün dünyasında
- L13-14: "En olası neden ... BGA mikro çatlak (~%25) · NAND besleme rayı (~%15) · saat/PLL (~%5-10)" — L1480-1482'de %2/%2/%0'a indirildi.
- L23-24: "Asıl çözüm yolu **MPTool ile yeniden açma**" — L3550 (§48.5): "**Hüküm: ... Bu yol kapalı; tek yol RE.**"
- Raporu baştan okuyan biri üç gün eski bir teşhisle başlıyor.

### A17 · Kapasite: 16 die / 8 die / 1 die / 1 TB / 20 GB
- L3883 (§52.3): "16 die'ın (4 kanal × 4 CE) **tamamı adreslenebiliyor**"
- L4303 (§58.4): "en fazla **8 die** ... → ~512 GB"
- L4528 (§64): "Okuyan die sayısı | ⚠️ **1/16** (ch0 ce0)"
- L4734 (§70): "≈ **20 GB**. 1024 GB'nin **~%2'si**."
- L4845 (§73): "**1 TB NAND fiziksel olarak orada.**"

### A18 · Doğru LDPC tabloları diskin kendisinde bulundu, yine EXE kopyası kullanılıyor
- L3931-3932 (§53.2): "`00 55 11 11` = **rate 2** — §48'de MPTool EXE'sinden çıkarmak zorunda kaldığım doğru LDPC matrisleri **zaten diskin kendi NAND'ında duruyormuş.**"
- L3988 (§54.1, güncel tarif): hâlâ `ldpc_r2/dec_rate2.bin` / `enc_rate2.bin` (EXE'den) yükleniyor.
- Aynı bölümdeki `LDBK CONFIG V00` = "**kontrolcü register başlangıç listesi** ... Boot'ta uygulanan donanım konfigürasyonu" (L3944-3946) hiç uygulanmadı.

---

## B) HİÇ DENENMEMİŞ / TAKİP EDİLMEMİŞ YOLLAR

| # | Ne | Nerede | Neden bırakılmış |
|---|---|---|---|
| B1 | **`0x47 ScanResultBlk` → `0x48 GetResultBlk`** (fabrika RDT sonuç bloğu) | `re/ANALIZ_TAMSAYFA.md:567`; firmware görevi `gdp_task_scan_rdt_rslt` `re/gdp_local/BULGULAR.md:136`; prob `araclar_20260915/s10.py:58`; RAPOR'da tek dolaylı iz L3936 ("0x47'nin bildirdigi wStopBlock 0x906=2310") | Hiçbir §'de sonuç yok. Tüketicisi `0x31 GetDefectBadTab` L2824/L2869'da `C0,**B37486**,L0 RDT rslt lost` veriyor — blok 37486 imkânsız (LUN'da 2732 blok var) → tarama parametresi zaten bozuk. Kimse dönmemiş. |
| B2 | **ONFI `E1h` Volume Select** | Tüm depoda **sıfır** geçiş | Hiç akla gelmemiş. Die "LUN sayısı = 1" diyor (L4774), DPD die haritası `(lun<<6)\|(ce<<3)\|ch` ile adresliyor (L2530). |
| B3 | **`EEh GET FEATURE` / `EFh SET FEATURE` doğrudan die'a** | Yalnız firmware-içi kontrol L3508-3509, RAM feature tablosu L2632-2638, `0x77 SET PARAMETER` L4965-4975 | Bizim elimizle hiç okunmadı; §43.7'nin "NAND SET FEATURE'a cevap vermiyor" iddiası (L2663) hiç doğrudan sınanmadı. |
| B4 | **Satır adresi `b<<11` (2048) / `b<<12` (4096)** | Denenen küme: `b`, `b*4`, `b*4+1`, `b*384`, `b*1536`, `b<<2` (L4543-4547, L4947) | 2'nin kuvvetine hizalı stride hiç denenmemiş. |
| B5 | **Blok adresinin 1024'te dönmesi** | L4731: "blok adresi **1024'te doniyor** (blok 900 == blok 1924)" | Raporun en açıklanmamış ölçümü. Hiçbir bölüm peşine düşmüyor — oysa "die'a ~10-11 blok biti gidiyor" demek ve tek başına silme FAIL'ini açıklayabilir. |
| B6 | **2732'den büyük blok numaralarıyla test** | Silme 2800/2801 L2865, L2927-2929; kötü blok listesinde 2760/2820 L3889 | Aralık dışı olduğu hiç fark edilmemiş; §72 geometriyi öğrendikten sonra da geriye dönülmemiş. |
| B7 | **SKV6 NAND zamanlama mikrokodu, 8 frekans** | L4018-4024 (§54.4): "`kanit/skv6_ucode/` ... **Bugüne kadar hiç yüklenmedi**" | "Okuma/yazma zaten çalışıyor" gerekçesiyle ertelendi — o varsayım §62-§67'de çöktü, konu yeniden açılmadı. |
| B8 | **Üreticinin eğitilmiş DQS/LCDL değerleri (TMC array `+0x14..0xB3`, `+0xC0..0xCF`)** | L3770-3772 (§50.5): "Denenmemiş kalan" | `TMC_ARRAY_*HynixV6*` pakette yok denip bırakıldı; V8 dosyasından türetme denenmedi. |
| B9 | **Mikrokod `0x1C` routine'i (`2D,5A,00,98` hynix vendor dizisi), `0x86`(4B)/`0x87`(4A) tek bayt vendor komutları** | L4637-4639 (§67): "hiç çağrılmadı ... aday" | Ertesi bölüm (§69) PIO harness'ını geçersiz ilan edince konu düştü, harness düzeltilince geri dönülmedi. |
| B10 | **`0x040DE16C` (program gönderimi) ↔ `0x040DE038` (okuma gönderimi) statik farkı** | L4685-4687 (§68, 3. hat) | Hiç yapılmadı. "Okuma bu zincirden geçip çalışıyor, yazma geçip çalışmıyor; fark **statik olarak bulunabilir**" deniyor ve bırakılıyor. |
| B11 | **LDPC encoder'ın adresi/içeriği (`0x00003928`)** | L4682-4684 (§68, 2. hat): "bu adres ya da içerik yanlışsa program hiçbir bit programlamaz. **Simetri dikkat çekici.**" | Doğrulanmadı. |
| B12 | **§69'un kendi zorunlu kapısı: `ECh` ONFI imzası** | L4717-4720: "Elle yazılan hiçbir NAND dizisi, **`ECh` ONFI imzasını getirene kadar** delil sayılmayacak." | Hiç geçilmedi — ama §75'in PIO tabanlı 16-die kanıtı bu kapıdan geçmeden kabul edildi. |
| B13 | **NAND VCC/VCCQ'yu yük altında ölçmek** | L4994-4997 (§76): "**Geriye kalan tek fiziksel doğrulama**" | Yapılmadı; §78 (L5069) yine de §76'yı "geçerli" ilan etti. |
| B14 | **GDP komut tablosunun 24 komutu** | L3441-3442: "36 komut var ve **24'ünü hiç incelemedik**"; L2570 (§42.8): "`0x0B`, `0x84`, `0x86` ... **denenmedi**" | Teşhis değeri yüksek ve hâlâ koşulmamış olanlar (`re/ANALIZ_TAMSAYFA.md:560-570`): `0x21 FlashDiagnostic`, `0xE4 ReadVref`, `0xE1 GetProgramLoop`, `0x4B CheckNandTime`, `0x4C PageWriteInterleave`, `0x4F ReadEfuse`, `0x4D InitGDP2`, `0x0A/0x0C SPI`. |
| B15 | **Blok 0'daki `LDBK CONFIG V00` register init listesi** | L3944-3946 (§53.2) | "Boot'ta uygulanan donanım konfigürasyonu" diye tarif edildi, GDP modunda hiç uygulanmadı. |
| B16 | **GDP'yi gerçek NVMe namespace sunacak hâle getirmek (~200-330 instruction)** | L4221-4244 (§57.5), yama noktaları adresli | Yerine NBD yolu seçildi (`takim/OKUMA.md`); statik analiz raftakalmış durumda. |
| B17 | **Tam sayfa ham okuma tek kelimelik yama `0x040C4528 ← E1A00000`** | L4202-4203 (§57.2), "geri alınabilir" | Uygulandığına dair kayıt yok. |
| B18 | **DarwinLudwig (usbdev moderatörü) — HYV6 MPTool + fw takas/satın alma** | L1727-1736 (§31.4/2): "**Temas kararı Alperen'in.**" | Karar hiç verilmedi. Eksik tek parça `ZI0PCADC.bin` (L3529-3531) ve bilinen tek kaynak bu. |
| B19 | **UART fiziksel portu** | L664-675 ("bilinmiyor, dürüst cevap"), L2564, L2673-2675 ("tek yol") | CP2102 hiç alınmadı; §44.1'de yazılım konsolu bulununca konu kapandı — ama **ürün firmware'inin** boot log'u hâlâ okunmadı (yazılım kancası yalnız GDP'de çalışıyor). |
| B20 | **İkinci makine (i3-6100, farklı UEFI/root complex)** | L1132-1147 (§23), L1283-1285 (§26-1h) | "Kontrol edilecek" deniyor, sonucu hiçbir yerde yok. |
| B21 | **R/B (hazır) algılama yolunu onarmak** | L4820-4822 (§72): "**Sıradaki hedef net** ... `0x040C3358`, NIFC `+0x21C` bit0, FCQ `+0x70/+0x74`, `0x040DBDCC`" | Ertesi bölüm (§73) "legacy'de 16 die görünüyor" deyince hedef bırakıldı — ama silme/programlama tamamlanma algılaması hiç düzeltilmedi. |
| B22 | **Sıkı kötü blok taraması tüm sürücüde** | L4063: "Sıkı tarama tüm sürücüde **henüz yapılmadı**" | Ve dayandığı "sil→FF" ölçütü artık silmenin çalışmadığı hükmüyle çelişiyor. |

---

## C) ZAYIF KANIT

### C1 · ⭐ Ana iddia: "silme/programlama 16/16 die'da FAIL" — kanıt zinciri
Zincir: §75 (L4904-4917) + §76 (L4952-4976) + §78 (L5057-5070).

**Ne kadar ölçüm var:**
- §75: `bosta, 16 die: e0` → `firmware SILME sonrasi: e1` — **die başına tek blok**.
- §76: "A) RESET, SET PARAMETER YOK: **blok 930**" / "C) SET PARAMETER uygulandi: **blok 934**" (L4971-4972) — yine tek blok, tek tekrar.
- §67: blok 850 (L4624). §74: blok 886 (L4895). §78: tek geçiş, n=1.
- **Blok süpürmesi yok, tekrar yok, die×blok matrisi yok.**

**Kontrol grubu yok — bu en ağır eksik:**
- Projede **hiçbir zaman**, geçerli protokolle (nöbetçi + soğuk çevrim + dokunulmamış kontrol bloğu) **başarılı bir silme gösterilmedi**. Tüm "silme çalışıyor" kayıtları echo/staging dönemine ait ve §62-§63 ile geçersiz: L2865 (§45.6), L3697 (§50.1), L3797 (§51.2), L3898 (§52), L4047 (§55.1).
- Yani "FAIL" ölçümünün karşılaştırılacağı bir "PASS" referansı hiç var olmadı. "Die reddediyor" ile "biz geçerli bir silme hiç göndermedik" bu aparatla ayrılamıyor.

**Adres geçerliliği hiç kurulmadı:**
- §65 tek işleyen kodlamayı ilan etti (L4546), §67 geri aldı (L4596) → geriye doğrulanmış kodlama kalmadı.
- §70 blok adresinin 1024'te döndüğünü ölçtü (L4731) ama bağlamadı.
- 2800/2801 gibi aralık dışı bloklara silme gönderildi (L2865, L2927-2929).
- Aralık dışı / desteklenmeyen satır adresi, NAND'da **ERASE status FAIL**'in ders kitabı sebebidir ve hiç elenmedi. §76'nın "geriye kalan tek açıklama" cümlesi (L4978) bu yüzden erken.

**`e1` yorumu kendi de çürük dönemden geliyor:**
- `sts0` bayt anlamları §51.3'te (L3804-3818) türetildi — §51'in tamamı echo dönemine ait. Datasheet'le ya da kasıtlı bilinen-FAIL vakasıyla (ör. fabrika kötü bloğu silmek, WP# çekiliyken silmek) hiç doğrulanmadı.
- Tek destek: `NAND RESET FAIL'i temizliyor (e1 -> e0)` (L4960) — mandalın sağlam olduğunu gösterir, bit anlamını değil.

**Mod kirlenmesi:** A14'teki çelişki doğrudan §78'in geçerlilik iddiasını (L5065) vuruyor.

**Baz oran:** Bu projede **beş kez** "fiziksel/donanımsal" teşhis, sonradan ölçüm artefaktı çıktı —
L3140 (§47 "iki gündür kovaladığımız şey ölçüm artefaktıymış"), L3776 (§51.1 "§50'nin teşhisi YANLIŞTI, sebebi tek bir sayı"), L4322 (§60 "§58 ve §59 yanlış premise"), L4464-4475 (§62 echo), L4596 (§67). Altıncısının da artefakt olma önselliği yüksek; rapor bunu kendi kaydına rağmen tartmıyor.

**Dürüst yanı (kayda geçsin):** §78 doğru şeyleri yaptı — dokunulmamış kontrol blokları (850/900/984/986), referans kararlılığı, tek geçiş (L5065-5066). Zayıflık yöntemde değil, **n'de, kontrol grubunda ve adres geçerliliğinde.**

### C2 · "~20 GB erişilebilir" (§70, L4722-4735)
- Tek die (ch0 ce0), **64 blokluk örnek** (50/64) 1024 bloğa ekstrapole edildi.
- Aynı bölüm blok adresinin 1024'te döndüğünü söylüyor (L4731) → "1024 blok" aynı fiziksel pencerenin aliası olabilir; o zaman 20 GB *ayrı* kapasite değil.
- Güç çevrimleri arası tekrarlanabilirlik (L4611-4614) kanıt hiyerarşisinin en üstü ama **n=4 blok**.

### C3 · "16 die canlı" (L4522, L4831)
- Dayanak yalnız Read-ID ve durum baytı. ID okunması dizinin erişilebilir olduğunu göstermez; aynı belgede okuyan die 1/16 (L4528) ve legacy'de okuma tamamen ölü (L4876).

### C4 · Kötü blok istatistikleri
- "%87,6" ve "%34" (L4062-4063), 49 örnekli liste (L3889) — hepsi echo döneminden.
- Bu ölçüt `takim/OKUMA.md:26-27` ve `jdmap.py` tarama protokolüne gömülü; üstelik protokol **çalışan bir silmeyi varsayıyor** (`OKUMA.md:167` "45 184 blok × (silme + 2 okuma)"), §75-§78 ise silmenin ölü olduğunu söylüyor. Teslim edilen araç ile son teşhis birbirini dışlıyor.

### C5 · §61'in "%99,22 doğru, 512 baytlık başlık bölgesi" (L4401-4431)
- Son derece yapısal, ikna edici bir sonuçtu ve **echo çıktı** (L4472-4475). Ders kayda geçmiş ama §61 başlığı hâlâ "Kalan %3 çözüldü" diyor.

### C6 · Tekrarlanabilirlik riski — kazanan tarifin girdileri arşivde YOK
- §49.1/§54.1'in tarifi `dpd_clk200.bin`, `ldpc_r2/dec_rate2.bin`, `ldpc_r2/enc_rate2.bin`, `gdp_init_param.py`, `scratchpad/tmc.py` istiyor; `takim/ortak.py:26-28` bunları `/home/schrodinger/jd1024/re/gdp/` altından okuyor.
- O dizinde yalnız `c0.bin`, `c1.bin` var; `ldpc_r2/` dizini `~/jd1024` altında hiç yok; `sys.path` `/tmp/jdlib` (uçucu).
- Eğer bu dosyalar sadece kaplıkaya'da/scratchpad'de duruyorsa, doğrulanmış tek yol bir temizlikle kaybolur. **Kontrol edilmeli.**

---

## SPESİFİK SORULARIN CEVAPLARI

**1) Silme TOGGLE modunda hiç denendi mi?**
Kısmen — ama hiçbiri geçerli protokolle değil.
- §60 öncesi firmware bring-up'ı **varsayılan olarak TOGGLE**: L4332 `0x040E38EC  mov r0, #1  ; <<<< 1 = TOGGLE (DDR) modu`. Yani §45-§55'in tüm silme deneyleri toggle'daydı — ve hepsi "silme çalışıyor" dedi (L2865, L3697, L3797, L3898). Bunlar başka sebeplerle (echo) geçersizleşti, **toggle'da tekrar edilmedi.**
- §60'tan sonra `ortak.py` bring-up'ı varsayılan olarak legacy'e yamalıyor (L4378-4383; `takim/ortak.py:100-108`), yani §65/§67/§68/§75/§76 legacy bring-up'ta koştu.
- §74 (L4890-4897) ve §78 hibrit: legacy bring-up → harita → toggle'a dön → tek silme. §74'ün kendi kuralı ve `tezgah.py` bunu geçersiz sayıyor.
- **Sonuç: §60 sonrası, nöbetçili + tek modlu + kontrol bloklu saf TOGGLE silme testi HİÇ yapılmadı.** `tezgah.py` varsayılanı zaten `legacy=False` — deney bir satır uzakta.

**2) Firmware'in kendi geometri/flash parametre tablosu dump edildi mi, gerçek die parametreleriyle karşılaştırıldı mı?**
Die'ın beyanı dump edildi, firmware'e beslenen tablo **karşılaştırılmadı ve düzeltilmedi**.
- §72 `0x10` ile JEDEC parametre sayfasını okudu (L4760-4778): `H25BFT8D4B8R-BDJ`, 2732 blok/LUN, LUN=1, **plane 2**, 1536 sayfa, 16384+2048.
- Bizim beslediğimiz DPD hâlâ Flash.ini `SKV606411` türevi: **2888 blok, 4 plane, 1 CE, 1 die** (L3045, L3453) — `takim/ortak.py:26` `dpd_clk200.bin`.
- §72 yalnız prosa olarak "plane 4 yanlıştı" dedi (L4776); DPD yeniden üretilmedi, `0x11`+`0x49` gerçek geometriyle hiç koşulmadı, `jdmap.py:16` hâlâ 2888 diyor. **Raporun en büyük işlenmemiş tutarsızlığı bu.**

**3) 2732'den büyük blok numaraları kullanıldı mı?**
Evet, ve hiç fark edilmedi.
- L2865: `BlockErase` log `[0,0,0,AF0,0,0]` — **AF0 = 2800**.
- L2927-2929: "BlockErase **2800** BAŞARILI" / "BlockErase **2801** başarısız".
- L3889: kötü blok listesinde **2760, 2820**.
- L2824: `0x31` log'unda `C0,**B37486**,L0 RDT rslt lost` — 37486 tamamen imkânsız.
- §72 gerçek sınırı (2732) öğrendikten sonra bu kayıtların hiçbiri gözden geçirilmedi.

**4) `b<<11` / `b<<12` kodlaması denendi mi?**
**Hayır.** Denenen tam küme L4543-4547 ve L4947: `b`, `b*4`, `b*4+1`, `b*384`, `b*1536`, `b<<2`. 2'nin kuvvetine hizalı hiçbir stride yok. §70'in "1024'te dönüyor" bulgusu (L4731) tam olarak bu ailenin işareti.

**5) `EFh SET FEATURE` / `EEh GET FEATURE` ile die'ın özellik register'ları okundu mu?**
**Hayır, hiç doğrudan okunmadı.**
- Var olan tek şeyler: firmware'in kendi init'i içindeki GET FEATURE kontrolü (L3508-3513), RAM'deki feature descriptor tablosu `0xE7C` (L2632-2638), hynix `0x77 SET PARAMETER`'lı/sız karşılaştırma (L4965-4975).
- §44.6 (L2750-2755) GET FEATURE geri okumasının "bir değer geriden geldiğini" ölçtü — bu, doğrudan okumanın ne kadar bilgi vereceğinin kanıtı; yine de yapılmadı.
- §43.7'nin "NAND SET FEATURE'a cevap vermiyor" hükmü (L2663) hiç doğrudan sınanmadan geçersizleşti.

**6) ONFI Volume Select (`E1h`) denendi mi?**
**Hayır — depoda tek bir geçiş bile yok.** (`araclar_20260915/s9.py:58`'deki `0xE1`, MAXIO vendor tablosundaki `GetProgramLoop`; ONFI `E1h` ile ilgisi yok — o da RAPOR'a hiç girmemiş.)

**7) `0x47 search rdt rslt` / `0x48 RSLT_BLK` takip edildi mi?**
**Hayır.**
- Kimlikleri belli: `re/ANALIZ_TAMSAYFA.md:567` → "`0x47`/`0xDC-0x48` **ScanResultBlk/GetResultBlk**"; firmware görevi `gdp_task_scan_rdt_rslt` (`re/gdp_local/BULGULAR.md:136`); dispatch girdileri `0x47→0x040C5544`, `0x48→0x040C55C4` (`re/gdp_local/BULGULAR.md:110-111`).
- Prob yazılmış: `araclar_20260915/s10.py:58` `(0x47,"0x47 scan rdt",1),(0x48,"0x48 rslt blk",2)`.
- RAPOR'da tek iz dolaylı: L3936 "`0x47`'nin bildirdigi wStopBlock 0x906=2310".
- **Hiçbir bölüm 0x47→0x48 çiftinin çıktısını kaydetmiyor.** Oysa bu çift, diskin **fabrika RDT / kötü blok tablosunu** verir ve tüketicisi `0x31` L2824'te `RDT rslt lost` diyor. Sildiğimiz blokların fabrika-kötü olup olmadığı sorusu — C1'in en zayıf halkası — tam olarak buradan cevaplanır.

---

## ŞİMDİ DENENMESİ GEREKEN 10 DENEY

1. `tezgah.py(legacy=False)` ile **saf TOGGLE tek silme** (850/900/984), mod geçişi yok, nöbetçi + dokunulmamış kontrol bloğu — §78'in legacy sonucuna kontrol grubu.
2. Silme/okuma satır kodlaması süpürmesi: **`b<<11` (2048)**, `b<<12` (4096), `b*1536+sayfa` — §70'in "1024'te dönüyor" bulgusunun tek makul açıklaması.
3. `0x47 ScanResultBlk` → bekle → `0x48 GetResultBlk` → `0x31 GetDefectBadTab`: fabrika RDT/kötü blok tablosunu al; sildiğimiz blokların fabrika-kötü olup olmadığını tek atışta söyler.
4. DPD'yi §72'nin **gerçek** geometrisiyle yeniden üret (2732 blok, plane=2, LUN=1) + `E1h` Volume Select yoklaması; `0x11`+`0x49`'u öyle koş.
5. Önce `ECh` ONFI imzası kapısını geç (§69 ölçütü), sonra **`EEh GET FEATURE` addr 0x01/0x80** ile 16 die'ın feature register'larını **silme öncesi ve sonrası** oku.
6. Hiç koşulmamış teşhis opcode'ları: **`0xE1 GetProgramLoop`**, `0x21 FlashDiagnostic`, `0xE4 ReadVref`, `0x4B CheckNandTime` — programlama arızası için doğrudan ölçüm.
7. `0x040DE16C` (program gönderimi) ile `0x040DE038` (okuma gönderimi) descriptor kurulumunu **statik olarak diff'le** (§68 hat 3, hiç yapılmadı).
8. `kanit/skv6_ucode/` içindeki **SKV6 NIFC mikrokodunu** (8 frekans) yükle, silmeyi tekrarla — bugüne kadar hiç yüklenmedi (§54.4).
9. Blok 0'daki **`LDBK CONFIG V00` register init listesini** ve NAND'ın kendi rate-2 LDPC tablolarını GDP moduna uygula (§53.2) — EXE kopyası yerine diskin kendi konfigürasyonu.
10. §76'nın kendi kararlaştırıp atladığı fiziksel ölçüm: **NAND VCC/VCCQ'yu yük altında** (okuma anında vs silme anında) ölç — "fiziksel ölü" hükmü bu yapılmadan verildi.
