# JD1024 (MAXIO MAP1202) — Boot doğrulama · code block recover · boot kopyası · etkisizleştirme

Kaynak imaj: `re/fw_canli/e*.bin` (diskin çalışan ürün FW'i, canlı RAM'den). Araçlar: `tk.py`/`tk2.py`/`refs.pkl`,
`d.py`, `c.py`, `br.py`, `fn.py`, `adr.py`. **Diske hiçbir komut gönderilmedi — salt statik.** Her iddiada dosya+ofset+disasm.
Bu rapor iki alt-analizle (S1 checksum, S3 boot kopyası paralel ajanlar) çapraz doğrulandı; sonuçlar bu dosyada birleşti.

---

## KARAR (4 satır)

```
S1 kod checksum'u : İMAJDA YOK — CodeMap +0xE alanı 0xFFFF ve hiç tüketilmiyor; CodeMap→RAM yükleyici imajda yok
                    (mask ROM'da); RSA/CRC/hash yok. CodeMap-parse kalıbı 12 segmentte 0 sonuç. ⚠️ ROM'da OLABİLİR,
                    imajda değil → statik olarak ne kanıtlanır ne çürütülür (aşağı bkz).
S2 recover        : Tetik = read-only/hata durumu (bit3), FTL bakım task'ından. Referans = tarama-sırası ilk OKUNABİLİR
                    kopya (die0=c0ce0). Hedef = diğer die'lar (erase+program). Yalnız CodeMap sayfa aralığı (sayfa-360
                    işareti bu yüzden sağ kaldı). ⚠️ Bu firmware yolu c0ce0'dan (YAMALI) kopyalar → tümü-orijinal
                    sonucunu AÇIKLAYAMAZ → asıl geri-yazan mask ROM (bkz S3).
S3 boot kopyası   : Kodu RAM'e yükleyen + kopya seçen kod MASK ROM'da (imajda YOK: "LDBK FWSLOT MARK"/sayfa-8/CodeMap
                    seçimi hiç geçmiyor). Firmware kendi tarafında die = CH|(CE<<2), "ilk başarılı okuma kazanır"
                    (die0=ch0/ce0=c0ce0). ROM'un sırası/doğrulaması görülemiyor.
S4 yapılacak      : Kod yaması ÇÖZÜM DEĞİL (ROM yamalı kopyayı kabul etmiyor; kabul etse bile bit3-tetikli re-sync ezer).
                    Tek statik-destekli kalıcı yol = KÖK NEDEN: DPD/die-config'te ölü die'ı (c3ce2) devre dışı bırakmak
                    → mismatch taraması bit3'ü hiç set etmez → read-only da re-sync de tetiklenmez. Kod değil CONFIG hedefle.
```

---

## 0. Bu turda öğrenilen kritik ölçüm (koordinatörden) ve nasıl uyuştu

- **Boot die = c0ce0** (0x04 SYS ReadPage, sayfa 360). → S3'ün firmware analiziyle **birebir**: firmware `die = CH|(CE<<2)`,
  tarama `plane→CE→CH`, ilk başarılı = die0 = **ch0/ce0 = c0ce0**; seçilen die global'i `*(0x00800210)` (e06 `0x0406D626`).
- **Bu turda recover ÇALIŞMADI** (sayfa-360 işaretleri 15 die'da kaldı). → Açıklama: re-sync **yalnız CodeMap aralığındaki
  kod sayfalarını** eşitler; sayfa 360 (slot 4 sonu 316'nın çok ötesi, CodeMap-dışı) hiç dokunulmuyor. Kod sayfaları bu
  turda tüm die'larda aynıydı → eşitleyecek bir fark yok → recover tetiklenmedi. **Tam tutarlı.**
- **Önceki turda 15 die yamalı, c3ce2 orijinal → sonuç tümü-orijinal.** → Aşağıda H1/H2/H3 ayrımıyla çözümlendi.

---

## 1. S1 — Boot kod doğrulaması (checksum/CRC/imza) VAR MI? → İMAJDA YOK

### 1.1 CodeMap'i RAM'e yükleyen (ve checksum'layabilecek) rutin imajda yok → mask ROM'da
16-baytlık CodeMap girdisini (`{u16 firstPage@0, u16 lastPage@2, u32 len@4, u32 loadAddr@8, u16 flags@0xC, u16 cksum@0xE}`)
o alan düzeniyle okuyan **hiçbir rutin yok**: tüm segmentler (e00–e11) `ldrh[base,#0]/[#2] + ldr[base,#4]/[#8] +
ldrh[#0xc]/[#0xe]` + 16-bayt stride kalıbı için tarandı → **0 sonuç**. Yani kodu NAND'dan RAM'e kopyalayan kısım
kontrolcü **mask ROM'unda**; imajda yok. `checksum` alanı (+0xE) firmware tarafından **hiç okunmuyor**.

### 1.2 Firmware'in memcmp'lediği tek şey 16-baytlık sabit sihirli imza — checksum değil
memcmp = `e07:0x040E3A10` (önce word `ldm`, sonra byte; dönüş 0=eşit — doğrulandı):
```
e07 0x040DA0AE  movs r2,#0x10
    0x040DA0B0  ldr  r1,=0x040EE2E4        ; "LDBK BLOCKS V00"
    0x040DA0BE  ldr  r5,[r0,#0x10]         ; okunan sayfa tamponu
    0x040DA0C2  bl   #0x40e3a10            ; memcmp(page, magic, 16)
    0x040DA0C6  cbz  r0,#0x40da10c         ; EŞLEŞTİ -> döngüden çık (başka kopyayla kıyas YOK)
```
Aynı kalıp: e06 `0x0406D896` (magic `0x040EE2F4`), e07 `0x040DA87E` (`0x040EE304`), e09 `0x040CCCC0/0x040CCD4A`.
Hepsi **"bu sayfa loader/param/config sayfası mı"** kimlik kontrolü — kod içeriği üzerinden bir toplam/CRC/imza değil.

### 1.3 checksum alanı = sabit 0xFFFF, standart CRC sabiti yok, kripto yok
- MPTool yazıcısı `wCheckSum`'ı **sabit 0xFFFF** yazıyor (`ANALIZ_MPTOOL.md`: `0x439035 mov word[ecx+edx+0xe],0xffff`).
- İmajda **standart CRC tablo sabiti yok**: CRC32 `0xEDB88320`/`0x04C11DB7`, CRC16 `0xA001`/`0x1021` → 0 eşleşme.
- Kod bağlamındaki `0xffff` kullanımları **boş-die-slot sentinel'i**, checksum değil:
```
e07 0x040D9DC4  movw r7,#0xffff
    0x040D9DDA  ldrh.w r1,[r1,r6,lsl#1]   ; 0x008058B0 die tablosu girdisi
    0x040D9DDE  cmp  r1,r7
    0x040D9DE0  beq  #0x40d9dea            ; 0xFFFF -> slot boş, atla
```
- `RSA|sign|verif|sha|hmac|ecdsa` string taraması → **0**. Tek gerçek CRC = **host veri-yolu CRC'si** (e00
  `host rd gdma crc err` `0x0000E550`, `merge_desc ... crc err` `0x00006F40`) = kullanıcı verisi koruması, kodla ilgisiz.
  `sy5Q-ChkSUM2:%x,%x` (`0x0406C7AD`) bir FTL debug log string'i, kod-doğrulama değil.

### 1.4 Kod sayfası header'ı = metin künyesi (MKSSD), sayısal checksum değil
Yüklü imajda (e00 `0x000001C0`, e04 `0x020001C0`): `"MKSSD_501003000124620000,Oct 31 2023,09:39:32,MAP1202,ZI0PCD2C"`
+ `0x00000180 "r:/code_release/Hynixv6/Cougar_Hynix_v6_12463"`. Bunlar **build künyesi**; imajda ayrı bir "MKSSD"
referans literali yok → boot yolu bunu memcmp bile etmiyor (sadece MPTool `VP_WriteCodeToFlash` yazıyor).

### 1.5 ECC/LDPC ≠ checksum, ve yamamız ECC'yi bozmadı
NAND ECC/LDPC donanımda (NIFC `0x06640000`, mikrokod `0x06649000`). Yamayı **loader ile yazdığımız için ECC yeniden
hesaplandı** → FW o sayfaları ECC-hatasız okur. Dolayısıyla revert'in sebebi "yama ECC'yi bozdu → uncorrectable" **değil**.

> **S1 SONUÇ:** Ürün firmware'i (imaj) yüklediği kodu bir checksum/CRC/imza ile **doğrulamıyor** — böyle bir kapı imajda
> yok. Yamanın geri gelmesi bir "checksum tutmadı → reddet" değil. **⚠️ Ama** kodu RAM'e yükleyen + kopya seçen kısım
> mask ROM'dadır (S3) ve **ROM'un kendi bütünlük kapısı statik imajdan görülemez** — bu boşluk aşağıda H1/H2'de belirleyici.

---

## 2. S2 — `code block recover` ve firmware'in re-sync yolları

İmajda kodu yeniden yazan **üç** mekanizma var. Hiçbiri boot'ta koşulsuz çalışmıyor; boot'taki LDBK taraması
**salt-okuma/doğrulama** (aşağıda 2.4).

### 2.1 `code block recover` — `e06:0x0406DD4C` (senin sorduğun dize `0x0406DEF4`)
- String bağlanışı: `0x0406DD52 adr r0,#0x1a0` → `0x0406DEF4 "code block recover\r"` (adr.py ile doğrulandı).
- **Tek çağıran:** `e07:0x040DAE2E bl #0x406dd4c`. Çağıran fonksiyon `0x040DAD74` ("[CodeBlk]S" banner, `0x040DB0EC`),
  içinde **yalnız hiçbir die'da geçerli "LDBK BLOCKS V00" bulunamazsa** buraya düşülüyor:
```
e07 0x040DADFA  lsl.w r0,sl,r4            ; die döngüsü, sl=1
    0x040DAE02  ldrh.w r0,[r6,r4,lsl#1]   ; r6=0x00805860 die tablosu
    0x040DAE08  ldr  r1,=0x040EE2E4       ; "LDBK BLOCKS V00"
    0x040DAE1A  bl   #0x40e3a10           ; memcmp
    0x040DAE1E  cbz  r0,#0x40dae7a        ; geçerli LDBK bulundu -> NORMAL boot (recover'a girme)
    ...
    0x040DAE2E  bl   #0x406dd4c           ; *** yalnız hiç geçerli LDBK yoksa ***
```
- İçinde `0x40d9b48`(oku), `0x40d9a08`(erase), `0x40d9a80`(program) çağırır; die kopyaları arasında bir referans
  dizisi (sp+0x10, 0xFFFF-init, "ilk görülen kazanır") kurup uyuşmayanları yeniden yazar. **Son-çare** yolu; koordinatörün
  "recover bu tur çalışmadı" gözlemiyle uyumlu (geçerli LDBK vardı → buraya hiç girilmedi).

### 2.2 ASIL aktif re-sync: `Codeblk rs` — `e09:0x040CD254`, **bit3-tetikli**
Tetik zinciri (hepsi FTL bakım **task**'ı, boot linear değil):
```
e04 task tablosu 0x0201632C -> (E51FF004 veneer) -> e07:0x040E63F1  (bakım task'ı)
e07 0x040E6498  bl #0x40dfc4c              ; task içinden
e07 0x040DFC6C  ldr r0,=0x00810CF4; ldrb; cbz -> çık
    0x040DFC74  ldr r7,=0x00810CF0; ldr r0,[r7]; bics r0,#7; beq -> çık
    0x040DFDFE  ldr r0,[r7]; tst.w r0,#8    ; *** bit3 (read-only/hata durumu) ***
    0x040DFE04  beq #0x40dfe76              ; bit3 yoksa restore YOK
    0x040DFE24  bl  #0x40daf64              ; -> wrapper -> e09:0x040CD254 (Codeblk rs)
```
`*(0x00810CF0)` CPU0 (e00) tarafından yazılan cross-CPU hata/durum kelimesi (writers: e00 `0x000133EE`, `0x00013596`);
**bit3 = recover/read-only tetiği**. Diskimiz read-only (bit3 set) olduğundan bu task **her koştuğunda** aday.

**Referans (kaynak) seçimi — `e09:0x040CCACC`:** die'ları tarayıp **ilk BAŞARIYLA OKUNANI** seç; **içerik doğrulaması
YOK** (fonksiyon içinde `0x40e3a10` memcmp çağrısı 0). Tarama `die = CH|(CE<<2)`, plane→CE→CH → **ilk = die0 = c0ce0**.

**Kopyalama — `e09:0x040CCB74`:** kaynaktan okur, hedefi siler+yazar:
```
e09 0x040CCBC6  ldr r1,[sp,#0xb4]; ldrd r0,r2,[sp,#0xac]; bl #0x40d9a08   ; ERASE  hedef (sp+0xb4)
    0x040CCC24  ldr r1,[sp,#0xa8]; ldrd r0,r2,[sp,#0x7c]; bl #0x40d9b48   ; READ   kaynak (sp+0xa8)
    0x040CD21E  ldr r1,[sp,#0xb4]; ldrd r0,r2,[sp,#0xac]; bl #0x40d9a80   ; PROGRAM hedef (sp+0xb4)
```
kaynak (sp+0xa8) ≠ hedef (sp+0xb4). Yani "kaynaktan diğer die'lara kopyala".

> **⚠️ KRİTİK ÇELİŞKİ (S2'nin en önemli bulgusu):** Firmware'in bu re-sync'i kaynağı **c0ce0 = YAMALI** kopyadan alır
> → diğerlerini **yamalıya** yazardı, sonuç **15 yamalı + 1 orijinal (c3ce2)** olurdu. Oysa gözlem **16'sı da ORİJİNAL**.
> Dolayısıyla tümü-orijinal sonucunu **firmware re-sync'i ÜRETEMEZ** → geri-yazan asıl fail **mask ROM** (bkz. 2.5, H1/H2).

### 2.3 `LB-RMP` reform (redundancy tazeleme) — `e09:0x040CF248`
8 loader-block slotunu gezip 24-baytlık descriptor'larla (`0x00809800`) NAND erase/program handler'larına fn-pointer
ile dispatch eder (`blx [r0,#0x38]/[...,#0x80]`); slot bitmap'i `[0x040EF078,#0x150/#0x152]`. Debug `EH-RFRM-LB RMP
START/END` (`0x040CF544/0x040CF618`). Sürücü: `0x040DFAD0 -> 0x040CF248`. Bu bir **redundancy relocate/refresh**; kaynak
seçimi yine firmware tarafı (die0) olduğundan tümü-orijinal sonucunu tek başına açıklamaz.

### 2.4 Boot yolu NAND'a YAZMIYOR (koşulsuz re-sync yok) — doğrulandı
Normal boot yolundaki tablo-doldurucular yalnız RAM tablolarını kurar; program/erase/kopya çağrısı **yok**:
- `e06:0x0406D65C`, `0x0406DA44`, `0x0406DC28`, `0x0406DCB4` → `0x40d9a80/0x40d9a08/0x40ccb74/0x40cd254/0x40cf248`
  çağrısı **0 adet** (fn.py+capstone taraması). Yani kod-sayfası yeniden-yazımı **yalnız** 2.2/2.3'teki bit3-tetikli
  bakım task'ında; boot'ta değil.

### 2.5 Öyleyse önceki turu ne geri-yazdı? — H1 / H2 / H3 ayrımı
| Hipotez | Statik hüküm | Gerekçe |
|---|---|---|
| **H1 imaj-checksum'u** | **YANLIŞ** | S1: imajda kod checksum'u yok; CodeMap +0xE tüketilmiyor. |
| **H1 ROM-checksum'u** | **OLASI, kanıtlanamaz** | Kod-yükleyici mask ROM'da (S3); ROM'un bütünlük kapısı imajda görülemez. "15 yamalı reddedildi / 1 orijinal kaldı" tam bir kabul-kapısının davranışı. |
| **H2 yama çökmesi** | **BİRİNCİL DEĞİL** | B/D boot'ta **no-op** (aşağı 4.2); A/C güvenli immediate (4.1). Basit boot-crash düşük olasılık. A/C'nin geç yan-etkisi (yazılabilir sanıp ölü die'a yazma) çökertebilir ama **kanıtlanmadı**. |
| **H3 replica re-sync (firmware)** | **VAR ama sonucu açıklamıyor** | Firmware kaynağı c0ce0=yamalı → tümü-yamalı üretirdi, tümü-orijinal değil (2.2 çelişkisi). |

**Eleme ile sonuç:** Tümü-orijinal sonucu firmware yollarından **hiçbiriyle** çıkmıyor (hepsi kaynağı yamalı c0ce0'dan
alır). Geri-yazan **mask ROM'dur**: ROM boot'ta 15 yamalı kopyayı **reddedip** (büyük olasılıkla bir ROM-seviyesi
bütünlük/kabul kapısı = **H1-ROM**) tek geçen orijinali (yazılamayan c3ce2) referans alıp redundant kopyaları oradan
onarıyor ve orijinali RAM'e yüklüyor. Bu, koordinatörün kendi hipoteziyle ("c0ce0'dan yüklendi, kabul edilmedi, c3ce2'ye
düşüldü, 15 die oradan geri yazıldı") **birebir**. **Bunun kesin kanıtı imajda YOK** — ROM imajda değil.

---

## 3. S3 — Boot kopyası nasıl seçiliyor

### 3.1 Kodu yükleyen + kopya seçen kod MASK ROM'da (imajda yok) — kanıt
- `"LDBK FWSLOT MARK"` string'i **hiçbir segmentte yok** (sayfa 8 = 8-slot CodeMap işaretçisi). Firmware'de var olanlar:
  `LDBK BLOCKS V00`, `LDBK NANDMEM TAB`, `LDBK FWTMC MARK`, `LDBK LDPC TABLE1/2` — FWSLOT/slot/CodeMap-seçimi **yok**.
- Firmware **sayfa 8'i hiç okumuyor**; okuduğu sayfalar: 0 (info), 2-7 (LDPC), 0x11/0x19/0x21/0x2A/0x2C-2F (param/code),
  0x44=68 (NANDMEM), 0x5B=91 (FWTMC). Sayfa-8/slot yok.
- Bu kod koşarken firmware **zaten RAM'de** (buffer mgr `0x00811FC0`, printf, task scheduler ayakta) → loader seçimi
  çoktan bitmiş. İmajdaki LDBK taraması = firmware'in kendi loader-block'unu **yeniden bulup** geometri/LDPC/NANDMEM/
  code-block-tazeleme için kullanması (bakım), boot-seçimi değil.
- Çalıştıran: `e06:0x0406A800`, `e07:0x040E66F8`, `e09:0x040CF506` = **FTL/NAND çekirdeği** (e00/NVMe değil; e00'da LDBK ref yok).

### 3.2 Firmware tarafı seçim mantığı (ROM'unki değil ama tutarlı)
"İlk başarılı okuma kazanır", sabit die/çoğunluk/sürüm/zaman-damgası **YOK**. Tarama `plane(0→1)→CE(0→3)→CH(0→3)`:
```
e07 0x040D9DB8  (ldbk_read_page_any_die)  r6=plane, r4=CE, r0=CH
    0x040D9DD2  orr.w r1,r0,r4,lsl#2       ; die = CH | (CE<<2)
    0x040D9DFA  bl #0x40d9b48              ; 4 kanal PARALEL oku
    0x040D9E00  bl #0x40d9c68              ; başarılı ch_bitmap
    0x040D9E06  bne #0x40d9e18             ; >=1 başarı -> DÖN (ilk kazanan)
```
Argüman adları koddaki string'le doğrulandı: `e07:0x040EE22C "read page fail:done(%x) ch_bitmap(%x) ce(%x) blk(%x)
page(%x) sts(%x)"`. **die_index = CH | (CE<<2)** = CH + 4·CE (e07 `0x040D9B86 orr r1,r1,r5,lsl#4` PAA descriptor).

### 3.3 (kanal,CE) ↔ firmware die indeksi + ölü die etkisi
- **die = CH|(CE<<2)** → ch3/ce2 = indeks 11; tarama CE0(die0-3)→CE1→CE2 sırasıyla. c0ce0 (die0) sağlıklı ve İLK →
  firmware seçtiği kopya = **c0ce0** (koordinatör ölçümü ile aynı).
- **Program/silme-ölü ama OKUNABİLİR die "geçerli kopya" sayılır:** `e07:0x040D9C68` yalnız okuma-hata bitini (bit2)
  kontrol eder:
```
e07 0x040D9D30  tst.w r0,#4    ; bit2 = UNC okuma hatası
    0x040D9D34  beq #0x40d9d84 ; temizse BAŞARI (program/silme sağlığına bakmaz)
```
  → c3ce2 (ölü ama okunabilir) her yerde geçerli referans; bu, "orijinali koruyan sabit kaynak"ın ta kendisi.
- **die tablosu `0x008058B0` fiziksel prob DEĞİL, CONFIG'ten:** `e06:0x0406D5A0` `memset(0xFF,64)` + `0x0000031C` die
  aday bitmap'inden dolduruyor; seçilen die `*(0x00800210)` (`0x0406D626`).

> **S3 SONUÇ:** Gerçek boot kopya-seçimi **mask ROM'da, imajda görülemez** (FWSLOT/sayfa-8/CodeMap yok). Firmware kendi
> tarafında die0=c0ce0 kullanır. ROM'un sırası/kabul-kapısı **BULUNAMADI** (imajda yok).

---

## 4. S4 — Etkisizleştirme: yapılacaklar ve yamaların değerlendirmesi

### 4.1 Dört yamanın kesin kodlaması + boot-güvenliği
| Yama | Adres | Ham bayt | Anlam | Değişecek bayt |
|---|---|---|---|---|
| A | e06 `0x040632E0` | `40 f0 08 00` | `orr.w r0,r0,#8` → `#0` | +2: `08`→`00` (@`0x040632E2`) |
| C | e06 `0x040665F8` | `41 f0 08 01` | `orr.w r1,r1,#8` → `#0` | +2: `08`→`00` (@`0x040665FA`) |
| B | e07 `0x040EC1B4` | `cc d0` | `beq 0x40ec150` → `b` | +1: `d0`→`e0` (@`0x040EC1B5`) |
| D | e07 `0x040EC23A` | `89 d0` | `beq 0x40ec150` → `b` | +1: `d0`→`e0` (@`0x040EC23B`) |

- **A/C güvenli:** 32-bit Thumb-2 `orr.w`; immediate 8→0, **uzunluk değişmez**, kod akışı değişmez. A `itt hs` bloğunda
  (`orrhs r0,r0,#8; strbhs`) — patch sonrası bit3 set edilmez, r0 yine saklanır (bit2 zaten `0x040632D8 orr r0,#4` ile
  set). **Sayısal/akış bozulması yok.**
- **B/D boot'ta NO-OP:** İçinde bulunduğu fonksiyon `e07:0x040EBF8C` bir **runtime flush TASK'ı** (e04 task tablosu
  `0x02016334` → veneer `E51FF004` → `0x040EBF8D`), boot-linear çağrı değil. Dal koşulu `*(0x040EF048)==0` iken alınır;
  **boot/durağan durumda flag=0 (canlı ölçüldü)** → orijinal `beq` de yamalı `b` de **aynı hedefe** (`0x40ec150`) gider →
  **davranış birebir aynı**. Fark yalnız flag≠0'da (bekleyen read-only yazma) ortaya çıkar, o da drain/discard'ı atlar.
  **B/D boot'u çökertemez.**
- Yani **H2 (yama çökmesi) birincil mekanizma değil.** (A/C'nin "yazılabilir sanıp ölü die'a yazma" geç yan-etkisi
  teorik; kanıtlanmadı.)

### 4.2 Neden kod yaması (A/B/C/D dahil) çözüm DEĞİL
1. **ROM yamalı kopyayı kabul etmiyor (ampirik):** RAM orijinal çıktı, tümü-orijinal'e döndü. Bu, ROM'un yamalı kod
   slotunu boot'a almadığını gösterir (2.5). ROM imajda olmadığından bunu **statik çürütemeyiz de kanıtlayamayız da**,
   ama gözlem güçlü. → Yamalı kod **hiç koşamıyor**, dolayısıyla A/C'nin "bit3'ü hiç set etme" etkisi devreye giremiyor.
2. **Girse bile:** bit3-tetikli firmware re-sync (2.2) CodeMap sayfalarını eşitler; kod yaması bir kopya-farkı yaratır,
   bu da re-sync/recover için yem olur. (Sayfa-360 işaretinin sağ kalması bunun **CodeMap-dışı** alanlar için geçerli
   OLMADIĞINI gösteriyor — yani config/işaret alanları güvenli, kod slotları değil.)
3. **Checksum düzeltme (S4'ün ilk çerçevesi) N/A:** İmajda düzeltilecek kod checksum'u **yok** (S1). ROM checksum'u
   varsa algoritması bilinmiyor/imajdan çıkarılamıyor → **forge edilemez**.

### 4.3 STATİK-DESTEKLİ TEK KALICI YOL — kök nedeni (config) hedefle, kodu değil
Read-only'nin kökü: ölü die (c3ce2) → blok-map tutarsızlığı → e06 `0x040632AC` taraması ≥512 mismatch → `0x040632E0`
bit3 set. **Ölü die "mevcut" sayılmazsa mismatch üretmez → bit3 hiç set edilmez → read-only da bit3-tetikli re-sync de
(2.2) çalışmaz.** Ve die-tablosu (`0x008058B0`) **fiziksel prob değil, CONFIG'ten** dolduruluyor (`0x0406D5A0`).

**Hedef = DPD/die-presence config** (kod slotu DEĞİL — CodeMap-dışı, sayfa-360 işareti gibi büyük olasılıkla
code-re-sync'e tabi değil):
- `0x0000031C` die aday bitmap'i (S3), `0x000003E0` max_dies (e06 `0x0406E604 ldrb [0x3E1... 0x3E0]`), `0x0000030C` CE
  map, `0x00000314` CH map. Bunlar boot'ta `0x00000300`'e (DPD) yükleniyor.
- Kapasite tavanı DPD `[0x18]/[0x19]` (proje notu). c3ce2'yi çıkarmak kapasiteyi düşürür → yeniden-init/veri kaybı riski.
- Bu, mevcut `re/ANALIZ_SILME.md` / `ANALIZ_FW_READONLY.md`'deki **"die-neutralize / dpd_clk200.bin"** yolunun ta kendisi.

**Uyarılar (dürüst):**
- **DOĞRULANMADI:** DPD/config'in NAND'da hangi sayfada/blokta tutulduğu ve ROM'un onu **checksum**'layıp
  layamadığı imajdan çıkmıyor (yükleyici ROM'da). DPD de ROM-korumalıysa bu yol da tıkanır — **önce DPD'nin nerede
  yazıldığı ve re-sync'e tabi olup olmadığı ölçülmeli** (sayfa-360 işareti gibi bir "kanarya" testiyle: DPD alanına
  zararsız bir bayt yaz, boot sonrası kalıcı mı diye bak — koordinatörün sayfa-360 yönteminin aynısı).
- Kod-yolu yaması istenirse **tek başına yetersiz**: ancak (a) ROM'un yamalı kopyayı kabul etmesi + (b) re-sync'in
  durması birlikte gerekir; (a) ampirik olarak sağlanmıyor.

### 4.4 Özet aksiyon sırası (statik temelli öneri)
1. **Kanarya testi:** DPD/config alanına (ör. `0x31C` bitmap veya kullanılmayan DPD baytı) zararsız bir işaret yaz,
   tel'siz boot sonrası kalıcılığını ölç (sayfa-360 yöntemi). → DPD re-sync'e/ROM-checksum'a tabi mi öğren.
2. Kalıcıysa: c3ce2'yi die bitmap'inden (`0x31C`) / max_dies (`0x3E0`) / kapasite (DPD `0x18/0x19`) düzenleyerek çıkar
   → mismatch yok → bit3 yok → read-only kalkar, re-sync tetiklenmez. (Kapasite düşer; yeniden-init gerekebilir.)
3. Kanarya kalıcı DEĞİLSE (DPD de korunuyorsa): tek yol yine **ROM download modu + GDP loader** (bu görevin dışı),
   çünkü ürün-FW/kod-yaması yolu ROM kabul kapısına takılıyor.

---

## 5. Bulunan/kullanılan adresler (ileriki iş için)
**e06:** `0x0406DD4C` code block recover · `0x040632AC` die-mismatch tarama (`0x040632E0`=A bit3 setter) · `0x040665F8`=C
bit3 setter · `0x0406D5A0` die-tablosu kurucu (config→`0x008058B0`, `0x0406D626`=seçilen die) · `0x0406D65C/0x0406DA44/
0x0406DC28/0x0406DCB4` boot tablo-doldurucular (NAND-yazmıyor) · `0x0406E5E4` max_dies init (`0x008036E0`) · `0x0406221A`
g_err_die (`0x0406E840`) · `0x0406819C` "No SysInfo block" (FTL, loader-seçimiyle ilgisiz) · `0x0406A800` [CodeBlk] çağrısı.
**e07:** `0x040EC1B4`=B / `0x040EC23A`=D FTL write-gate dalları · `0x040EBF8C` write-gate fonksiyonu (TASK, e04 tablo
`0x02016334`) · `0x040E3A10` memcmp · `0x040D9DB8` ldbk_read_any_die · `0x040D9B48` read-issue · `0x040D9C68` wait
(yalnız bit2 okuma-hata) · `0x040DA05C/0x040DA0B0` LDBK BLOCKS parser · `0x040DAD74` [CodeBlk] ana fn · `0x040DFC4C`
bakım-restore sürücü (bit3-tetik `0x040DFE00 tst r0,#8`) · `0x040E63F0` bakım task'ı · `0x040DFAD0` reform sürücü.
**e09:** `0x040CD254` Codeblk rs (aktif re-sync) · `0x040CCACC` kaynak seçici (ilk-okunan, doğrulamasız) · `0x040CCB74`
kopyala (kaynak=sp+0xa8 oku, hedef=sp+0xb4 erase+program) · `0x040CF248` LB-RMP reform.
**Global/HW:** `0x00810CF0` bit3 = restore tetiği (CPU0 yazar) · `0x040EE73C` media-status bit3 · `0x00806EC8` health
bit3 · `0x040EF048` transient write-gate · `0x008058B0` die×plane tablo · `0x00805870` kanal sayfa-tampon parçaları ·
`0x00800210` seçilen die · `0x0000031C` die bitmap · `0x000003E0` max_dies · `0x0000030C/0x00000314` CE/CH map · DPD `0x18/0x19` kapasite.
**Sihirler:** `0x040EE2E4` "LDBK BLOCKS V00" · `0x040EE334` "LDBK NANDMEM TAB" · `0x040EE344` "LDBK FWTMC MARK" ·
`0x040EE314` "MAS090X_PAR_V000" · `0x040EE2F4/304/324` {magic,"MAS09A0V000"}.

## 6. Dürüstlük / BULAMADIKLARIM
- **BULAMADIM (belirleyici):** Mask ROM'un kod-yükleme + kopya-seçim + **kabul/bütünlük** mantığı. İmajda yok
  (FWSLOT MARK/sayfa-8/CodeMap-seçimi string düzeyinde bile yok). "Yamalı kopya neden reddedildi" sorusunun kesin
  cevabı bu boşlukta. → H1-ROM en tutarlı açıklama ama **kanıtlanamaz**.
- **BULAMADIM:** DPD/config'in NAND'daki fiziksel yeri ve ROM/re-sync korumasına tabi olup olmadığı → 4.3 kanarya testi
  gerekli.
- **TAHMİN:** e10 canlı config (16 die: `0x31C..0x32B=0x03`, `max_dies=0x10`); e00 64-die şablonu. Kod birebir aynı, yalnız
  `0x0000-0x04F5` config bölgesi farklı.
- **TAHMİN (kanıtlanmadı):** H2'nin geç yan-etkisi (A/C ile yazılabilir sanıp ölü die'a yazma → çökme). B/D boot no-op'u ve
  A/C kodlama-güvenliği **kanıtlı**; asıl geri-yazımın ROM olması **eleme ile** güçlü ama ROM görülemediğinden mutlak değil.
- **YAPMADIM:** Diske hiçbir komut gönderilmedi (görev sınırı) → hiçbir hipotez canlı test edilmedi.
