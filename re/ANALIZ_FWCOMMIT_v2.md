# JD1024 (MAXIO MAP1202) — fw-commit / fw-download handler ve imaj-doğrulama analizi (v2)

Kaynak: yalnız `re/fw_canli/e*.bin` (2023 ürün FW canlı RAM dökümü) + `fwram/*.bin` imaj dosyaları.
Diske hiçbir komut gönderilmedi. Her iddianın yanında dosya+offset+disasm var.
Statik-analiz sınırları AÇIKÇA işaretlendi ("DÖKÜMDE YOK").

Mimari düzeltme: 0x02000000 bölgesi (e04, CPU2) **Thumb** çözülüyor (ARM değil — refs [T]);
önceki task notundaki "ARM" yanlış. e00/e01/e02/e03/e07/e08/e09 = CPU1 Thumb.

---

## 0. TL;DR — kanıtlanan kök neden

Gözlenen status kodlarını ÜRETEN kod, dökümün tamamında **tek noktada** ve hepsi CPU1'de:

| status | üretildiği adres | seg | koşul |
|---|---|---|---|
| `0x107` Invalid Image | `0x040C509E` | e03 | invalid-flag `[0x0081E738] != 0` |
| `0x10B` (spec: Requires Conv. Reset) | `0x040C513C` | e03 | activation-state `[0x00809966] == 1` |
| `0x112` (time violation) | `0x040C6022` | e03 | geçen süre > `0x1F40` tick |
| `0x114` Overlapping Range | `0x00011B24` | e00 | **Set Features (0x09)** handler'ında (aşağıya bak) |

`0x107/0x10B/0x112` ürettiği kod **e03'teki FW-activation state machine**'dir (fonksiyon `0x040C5044`
ve kardeşleri). Bu üç değerin başka üretici yeri YOK (tam tarama, iki mod, movw + pool sabiti dahil —
`c.py`/pool-scan boş döndü).

Ama asıl **imaj parse/validate** kodu (sha256, section/CodeMap parse, overlap testi, invalid-flag'i
SET eden kod) bu segmentlerde **YOK** — FTL main (`0x040C8000–0x040CC000` boşluğu) ve/veya yakalanmamış
CPU2/FTL bölgesinde. Kanıt: invalid-flag `0x0081E738`'in tüm dökümde **tek** referansı init-to-zero
(`0x040C018E`); non-zero yazan kod hiçbir yerde görünmüyor.

**Fakat** imaj dosyalarını format kurallarıyla parse edince kök neden dökümden bağımsız olarak
KESİN çıkıyor (§6): bizim imaj yapısal olarak bozuk (sha=0, 0x420 count=çöp, CodeMap=çöp, section 10/11
= s0/s4'ün RAM adresini tekrarlıyor → gerçek overlap).

---

## 1. NVMe admin dispatcher ve 0x10/0x11 yönlendirmesi [KANIT]

Dispatcher e00 `0x000037F0`, selector = opcode = `ctx[0]>>24`, ctx = `0x0080BA60`.
Dağıtım (`0x000038E0` cmp-zinciri + `0x38EA tbb`):

```
0x38E0 cmp r0,#0x10 ; 0x38E2 beq 0x39DC → b 0x3B3C     ; opcode 0x10 (FW Commit)
0x391C cmp r0,#0x11 ; beq 0x3A18 → b 0x3AC2            ; opcode 0x11 (FW Download)
0x3920 cmp r0,#0x14 ; beq 0x3A1A → b 0x3B64            ; opcode 0x14 (Self-test)
tbb[0x09] → 0x3976 → b.w 0x118B0                        ; opcode 0x09 (Set Features)
tbb[0x02] → 0x3A02 ; tbb[0x0A]→0x3968→0x12392           ; Get/Set diğer
0xC1/0xC2 → 0x3AA6/0x3AB4 (vendor engine 0x40F0)
```

Bu tablo v1 analiziyle tutarlı ve sağlam.

---

## 2. fw-commit (0x10) gerçek kod yolu [KANIT] — RELAY, doğrulama yapmıyor

```
opcode 0x10 → 0x39DC → 0x3B3C:
  0x3B3C cbz r4,0x3B56            ; r4=NSID; NSID!=0 → erken hata completion
  0x3B56 … b.w 0x3E18
0x3E18: blx 0x61FC(log) ; mov r0,ctx ; blx 0x14790(veneer) → 0x040C08AE (e08)
```

Worker `0x040C08AE` (Thumb, tam çözüldü):
- `r5 = 0x0080BA60`, ctx'ten func/sqid/cid/CDW10 çıkarır.
- **relay struct'a yazar:** `0x0080BB42` (= `0x0080BA60 + 0xE2`): `[+0xc/+0xd]=func`, `[+0xe]=sqid`,
  `[+0x10]=cid`, `[+8]=CDW10.lo`. (Bkz. `0x040C08E6` `ldr r0,=0x0080BB42; strb …`.)
- HW mailbox: poll CQM `0x06738000+0x6C`; WDMA CTRL `0x06750000+0x48`, RDMA CTRL `0x06758000+0x48`;
  `0x06700470` üzerinden yanıt okur.
- Ürettiği status: `0x103` (`0x040C0982`), `0xAC` (`0x040C09AA`), `strh r0,[0x0080BB46]` (relay'e).
- **Firmware slot / CodeMap / sha / NAND-program referansı YOK.** Bu bir WDMA/RDMA komut-relay'i;
  komutu CPU2/FTL'e mailbox'la geçiriyor. Gözlenen `0x107/0x10B/0x114`'ü ÜRETMİYOR.

Sonuç: 0x10 handler'ı imajı doğrulamaz; komutu asenkron olarak arka-uca geçirir. Doğrulama arka-uçta.

---

## 3. fw-download (0x11) kod yolu [KANIT]

```
opcode 0x11 → 0x3A18 → 0x3AC2:
  0x3AC2 cbz r4,0x3AE8            ; NSID==0 → 0x3AE8
  0x3AE8: (CDW11<<2) vs 0xAE34FF08 / 0x12340008 / 0xBD34FF08  (miniport vendor magic)
          magic VAR  → 0x3B0E: vendor transfer kur, status 0, b.w 0x40F0
          magic YOK  → 0x3B30 → b.w 0x3DF6
0x3DF6: blx 0x61FC(log) ; blx 0x14788(veneer) → 0x040C0C0B
```

Veneer `0x14788 → 0x040C0C0B`; asıl fonksiyon prologue'u `0x040C0BA2`
(`push {r3..fp,lr}`; `0x040C0C0A–0x2F` fonksiyonun literal pool'u, ortada — capstone orada desync olur).
Fonksiyon `0x040C0BA2`:
- `r5 = 0x0080BA60 + 0xE2 = 0x0080BB42` → **aynı relay struct**'a yazıyor (`[+8]=CDW10`, `[+0xa]=CDW10.hi`,
  `[+0xc/d]=func`, `[+0xe]=sqid`, `[+0x10]=cid`).
- chunk sayacı `0x00809958[0]` artırır; `>3` ise status `0x103`.
- `[r5+8]/[r5+0xa]`'yı `0x0080442A/2C/2E/30/32`'deki değerlerle kıyaslıyor. **UYARI:** bu adresler
  canlı dökümde yüksek-entropili runtime verisi (ör. `[0x0080442A]=0xEB9A`), statik "page bound" değil —
  bu yüzden download page-range semantiğini KESİN çıkaramadım (statik sınır).

Yani 0x11 de asıl imajı buffer'layıp arka-uca relay ediyor; standart host (`fw-download`, CDW11=OFST=0)
magic'e uymaz, `0x3DF6` yoluna girer.

---

## 4. FW-activation state machine (e03) — 0x107/0x10B/0x112'nin GERÇEK üreticisi [KANIT]

Fonksiyon `0x040C5044` (Thumb). **Admin yolundan doğrudan çağrılmıyor** — dökümde ona ne branch ne
pointer var (tam tarama). FTL/task-scheduler tarafından (yakalanmamış kod) çağrılıyor.

Akış:
```
0x040C5048 ldrb r0,[0x0080BF69]; cmp #2
   ==2 → r0=[0x0080BF6A] (kayıtlı slot)   ;  !=2 → r0=CDW10 & 7 (FW SLOT alanı)
0x040C5060 cmp r0,#0 ; beq 0x50C0         ; slot==0 → default slot ([0x0080C438+0x4E0]&7)
0x040C5064 [0x00810CE4]=0; [0x00810CEC]=0; [0x0081E73C]=0
0x040C5072 r1=0x0081E738 ; r2=[0x0081E738]
0x040C5080 cbz r2,0x50D4                  ; invalid-flag==0 → geçerli yol (0x50D4)
           …flag!=0 yolu…
0x040C509E movw r0,#0x107                 ; *** INVALID IMAGE ***
0x040C50A6 str r0,[sp] ; blx 0x40C7544 (=completion post 0x2E34)
0x040C50BC r0=0x00003B6F → [0x0080C094]   ; "komut bitti" işaretçisi
```
Geçerli yol `0x50D4`:
```
0x50D4 slot tablosundan kopya: [0x0081E740 + slot*8] → aktif config [0x0080C438 + slot*8 + 0x480/0x484]
0x50EC [0x0080C438+0x4E0] = [0x0081E744]  (aktif slot)
0x50FE ldrb r0,[0x00809966] ; cmp #2 ; bhs 0x514A (abort/log)
       … state 0/1 işlemleri, [r7]=0x10, log …
0x5134 ldrb r0,[0x00809966] ; cmp #1 ; bne 0x5146
0x513C movw r0,#0x10B                     ; *** 0x0B (spec: activation requires conventional reset) ***
0x5140 strh r0,[0x00804750+0xa] ; [0x0080995E]=1
```
Kardeş fonksiyon `0x040C5FF0` (timeout):
```
64-bit timestamp [0x0080D280] − [0x00809958+0x50]; > 0x1F40 tick ise:
0x6022 movw r0,#0x112 → completion       ; *** activation TIMEOUT ***
```

Kanıt-özeti: `0x107/0x10B/0x112` immediate'ları dökümde **yalnız** bu üç adreste
(`c.py 0x107 0x10b 0x112` + pool-scan boş). Yani gözlenen bu üç kod bu state machine'den çıkıyor.

**Ama** invalid-flag `0x0081E738`'i non-zero yapan (yani "imaj neden invalid" kararını veren) kod
DÖKÜMDE YOK: tüm dökümde `0x0081E738`'e tek pool referansı `0x040C018E` (e08 init, sıfırlama).
FW-control struct'ı `0x0081E5E8–0x0081E788`; alanlarına e06/e07/e09'dan base+offset ile erişiliyor
(bu yüzden refs.pkl absolute pool taraması setter'ı yakalamıyor — statik sınır).

---

## 5. "Activation Prohibited" (0x0B) neyle ilişkili? [KISMİ]

- Kod tarafı: `0x040C513C`'de `0x10B`, koşul = activation-state byte `[0x00809966] == 1`. Bu state'i
  FTL/activation sequencer set ediyor (yakalanmamış).
- Task'ın sorduğu `0x00810CE8`: bu **CPU2 (e04) boot/mode değişkeni**. e04'te `0x0200092C
  ldrb [0x00810CE8]; cmp #3` ve `0x020009B8 [0x00810CE8]=1` — değerleri 1/3, CPU2 durumu. 37 referans
  (çoğu e04/e07). Write-protect göstergesi olabilir ama `0x040C5044`'ün `0x10B` yolu **doğrudan
  `0x00810CE8`'i okumuyor** — bağlantıyı statikte kuramadım (DÖKÜMDE bağ YOK).
- Empirik (senin ölçümün): CA=0 → 0x0B, CA=1 → 0x07. Spec'e göre SC 0x0B = "Firmware Activation Requires
  **Conventional Reset**" (task'taki "Prohibited" etiketi spec'te 0x13). Bu okuma CA semantiğiyle
  uyumlu: **CA=0 = slota yaz, aktive etme → "reset gerekli" (0x0B) = imaj SAKLANMIŞ olabilir**;
  **CA=1 = yaz+aktive → tam doğrulama → sha=0 olduğu için 0x07**. CA→dallanma yakalanmamış parse'ta.

---

## 6. İmaj dosyalarının analizi — KÖK NEDEN, dökümden bağımsız KANIT

Format kurallarıyla parse (senin verdiğin MAS09 layout'u):

### Geçerli 3 referans (JQYOCD2C / IQYOCE2C / JQYOCDLC) — hepsi birebir:
- `0x12`=7 **ve** `0x420`=7 (tutarlı), 7 section.
- loads: `0x00000000, 0x00800000, 0x00805800, 0x02000000, 0x02800000, 0x04052000, 0x040D2000`
- `sha256(dosya[0x1000:])` byte-reversed @ `0x270` **DOĞRU** (üçünde de eşleşiyor).
- **CodeMap @0x430 == section tablosu** (her entry `{ram=load, size=len}`, birebir).

### Bizim imajlar:
```
                     0x12  0x420(u32)    sha   CodeMap==sec  loads[10],[11]
jd_v6_dogru.bin       12   0x03020100     ✗       ✗          0x00000000, 0x02000000
jd_m10_v2.bin         10   0x03020100     ✓       ✗          (yok — 10 section)
jd_m12z_v5.bin        12   0x03020100     ✓       ✗          0x00000000, 0x00000000
```

**Bozukluklar (hepsi kanıtlı):**
1. **`0x420` ikinci count = `0x03020100` (çöp)** — tüm imajlarımızda. Referansta doğru (7). Bu alan
   00 01 02 03 = init'lenmemiş artan patern.
2. **CodeMap @0x430 = tamamen çöp** (`0x03020100`, `0xB0A0908`, `0xFFFFFFFF…`). Referansta section'ları
   birebir aynalıyor. Bizimki doldurulmamış/rastgele.
3. **sha256 @0x270 = sıfır** (jd_v6_dogru). → sha kontrolü FAIL → **Invalid Image 0x2107**. (Bu senin
   "CA=1 → 0x2107" ve "temiz-format → 0x2107" gözlemini açıklar.) m10/m12z'de sha düzeltilmiş.
4. **Section 10 ve 11 sahte kopya:** s10 `load=0x00000000` (foff=`0x079000`!) s0'ın adresini,
   s11 `load=0x02000000` s4'ün adresini tekrarlıyor. GERÇEK RAM overlap:
   ```
   OVERLAP s0[0x00000000-0x00018000] vs s10[0x00000000-0x00004000]   ← foff 0x079000 = section 10
   OVERLAP s4[0x02000000-0x02018000] vs s11[0x02000000-0x02004000]
   ```
   Bu, senin "CodeMap doldurunca 0x2114, tam offset 0x079000 (section 10)" gözleminle **birebir**
   uyuşuyor. s10/s11 aslında e10/e11 RAM dökümleri (16KB shadow bölgeler; e10≠e00[:16K], e11≠e04[:16K])
   ve "MKSSD" marker taşıdıkları için kod-section sanılıp eklenmişler.

### Overlap kontrol semantiği [KISMİ]:
Referans GEÇERLİ imajda da bir overlap VAR: `c1[0x800000-0x808000]` vs `c2[0x805800-0x809800]`
(kısmi, iç içe) — ama kabul ediliyor. Bizimkinde s10/s11 **aynı BAŞLANGIÇ adresini** (0x00000000,
0x02000000) tekrarlıyor. Yani kontrol muhtemelen "aynı/çakışan base address" (duplicate load) durumunu
flag'liyor, iç içe nesting'i değil. Kesin predicate yakalanmamış parse'ta (statik sınır) — ama
empirik kural bu.

---

## 7. Section count beklentisi ve 12→10 timeout [KISMİ]

- Kanonik count = **7** (üç referansta da). Bizim yaklaşım (her RAM bölgesini bir section yapmak)
  yanlış: RAM dökümü flash-image section layout'una 1:1 map OLMUYOR.
- 12→10 indirince download ilk chunk'ta timeout: **statik koddan mekanizmayı KANITLAYAMADIM** (download
  header parser yakalanmamış). Ama kesin olan: `jd_m10_v2` (10 section, sha ✓) hâlâ `0x420`=çöp ve
  CodeMap=çöp taşıyor. En güçlü adaylar: (a) çöp `0x420` count'un parser'ı file[0x1000:] header'ında
  vahşi iterasyona sokması; (b) toplam-boyut/last-page beklentisi (10-sec dosya `0x79000`B, 12-sec
  `0x81000`B; last page 121 vs 123); (c) önceki commit denemelerinin controller'ı "update pending"
  durumunda bırakması. Bunları **önce `0x420` ve CodeMap'i düzeltip** tekrar test etmeden ayıramayız.

---

## 8. Geçerli imaj için DEĞİŞTİRİLMESİ GEREKEN alanlar (öncelik sırasıyla)

Referans imajları "doğru format" örneği olarak alarak:

1. **`0x270–0x28F` sha256**: `sha256(dosya[0x1000:])` hesapla, **byte-reverse** et, yaz.
   (jd_v6_dogru'da sıfır → mutlaka düzelt.)
2. **`0x420` u32 count**: `0x03020100` çöp → `0x12`'deki count ile aynı yap.
3. **`0x430+` CodeMap**: her section için `{u32 ram=loadAddr, u32 size=length}`, section tablosunu
   BİREBİR aynala (referanslardaki gibi `codemap==sections`). Çöp değerleri temizle.
4. **Section 10 ve 11'i çıkar** (load `0x00000000` ve `0x02000000` — s0/s4 kopyası). e10/e11 shadow
   dökümlerini section yapma. Bu, overlap 0x2114'ü giderir.
5. **Section layout'u yeniden düşün**: kanonik imaj 7 section; e00–e11'i tek tek section yapmak yanlış
   yapı üretiyor (fazladan 0x040C0000/0x040C4000/0x040CC000 section'ları referansta ayrı section değil).

### ⚠️ KRİTİK UYARI (yeni bulgu):
Referans imajlar **hedef diskle AYNI firmware DEĞİL**. Referans `MKSSD_500003000067600000, Aug 23 2021`;
hedef diskin RAM dökümü `MKSSD_501003000124620000, Oct 31 2023`. Section 0 verisi yalnız **%5** eşleşiyor.
Yani referanslar doğru **FORMAT** örneği ama bu diske **drop-in firmware DEĞİL** — content farklı, memory
map farklı (ref 0x04052000/0x040D2000 vs döküm 0x04060000/0x040D0000). Bu diskin kendi 2023 firmware'ini
patch'lemek istiyorsan, imajı kendi RAM/flash içeriğinden değil, diskin **kendi orijinal flash imajından**
üretmelisin (RAM dökümü runtime-mutated; flash section'a 1:1 gitmez).

---

## 9. Statik-analizle ÇÖZÜLEMEYEN (dürüst liste)

- Invalid-flag `0x0081E738`'i non-zero yapan kod (imaj-neden-invalid kararı) — FTL/parse, DÖKÜMDE YOK.
- Firmware CodeMap overlap → `0x14` üreten kesin kod satırı — dökümde `0x114`'ün tek immediate üreticisi
  Set Features handler'ı (`0x00011B24`, e00); firmware-parse tarafındaki üretici YOK. (İmaj-parse ile
  overlap'ın VARLIĞINI kanıtladım; status'u basan satırı bulamadım.)
- `0x00810CE8` ↔ `0x10B` (write-protect ↔ activation-prohibited) bağı — statikte kurulamadı.
- 10-section download timeout mekanizması — download header parser yakalanmamış.
- Download page-range check semantiği — kıyas hedefleri (`0x0080442A+`) runtime verisi, statik değil.

Bu boşlukların hepsi ya `0x040C8000–0x040CC000` FTL-main boşluğunda ya da dökülmemiş CPU2/FTL
bölgesinde. Kesin cevap için o bölgelerin de canlı dökümü lazım.
