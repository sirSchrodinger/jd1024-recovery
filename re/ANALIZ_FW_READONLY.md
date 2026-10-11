# JD1024 (MAXIO MAP1202) — Salt-okunur (read-only / WP) kilidi: FW analizi + canlı doğrulama

Kaynak imaj: `re/fw_canli/e*.bin` (diskin kendisinden çıkarıldı). Araçlar: `re/fw_canli/tk.py`,
`tk2.py` (+`refs.pkl`, 13420 PC-relative xref). Statik analiz t440'ta lokal kopyada; canlı okuma/yazma
kaplıkaya'daki cihazda (`jdcanli`, nvme numarası boot'tan boota değişir — bu oturumda **nvme1**).
Her iddia dosya+ofset+disasm ile. **Canlı ölçüm birkaç statik iddiayı çürüttü — düzeltmeler ⚠️ ile.**

## TL;DR — sonuç
1. `critical_warning=0x08` (bit3=read-only) canlı doğrulandı (standart Get Log Page).
2. Bit3, **die block-map tutarlılık taraması** ≥512 mismatch bulunca set ediliyor (ölü die ch3/ce2). **Latch değil, yeniden hesaplanıyor** — NAND silmek bu yüzden kilidi kaldırmadı.
3. Yazmayı yutan gate **FTL (e07) write yolunda**; efektif read-only durumu backend flag'lerinde (`0x040EE73C` bit3, health word `0x00806EC8` bit3, transient `0x040EF048`).
4. **CANLI RAM PATCH MÜMKÜN DEĞİL:** ürün firmware'inde **çalışan bir vendor RAM-yazma komutu yok** (`0x87` no-op — 4 farklı bölgede test edildi, hiçbirinde kalıcı olmadı; kodda `cmp #0x87` yok). Dolayısıyla "tek bayt yaz → yazma açılır" canlıda **uygulanamıyor**; üstelik durum sürekli yeniden hesaplandığı için uygulanabilse bile geçici olurdu. Kalıcı çözüm die-seviyesi (die-presence / offline reflash) veya kod patch'i (GDP yolu) gerektirir.

---

## 0. Bellek haritası / 3 CPU
| segment | VMA | rol |
|---|---|---|
| e00 (+e01 0x00800000, e02 0x00804000) | 0x00000000 | CPU0 SİSTEM/SMART; verisi 0x0080xxxx SRAM |
| e04,e05 | 0x02000000/0x02800000 | CPU1 queue/flush |
| e03,e06,e07,e08,e09 | 0x040C0000..0x040F0000 | CPU2 FTL/HOST-CMD — **read-only gate burada** |

Debug string'leri ("wp no q-wr","WRITE-PROTECT","BT_WP" ...) indeksli logger'dan geçiyor → string-xref onları
bulmuyor; WP mantığı **veri akışı (flag değişkenleri)** izlenerek çıkarıldı. `jdcanli` GÜVENLİ okuma listesi =
yüklü kod segmentleri; onun dışını okumak firmware'i fault'luyor (kod-erişim kanıtı olan adresler `zorla=True`).

## 1. `critical_warning` baytı — CANLI DOĞRULANDI
Standart `Get Log Page` (opcode 0x02, LID 2, 512B) canlı:
```
SMART[0]=0x08 (bit3 read-only)  SMART[1:3]=331K  SMART[3]=100 spare  SMART[4]=1 thr  SMART[5]=0
```
NVMe bit semantiği (e00 debug printer `0x0000C2BE`, r7=0x0080C438; `ldr [r7,#0xe8]` + per-bit print):
bit0 "smart spare"(0xC4A4) · bit1 "smart temp"(0xC4B4) · bit2 "NVM subsystem Reliability"(0xC4C4) ·
**bit3 "WP:%x"(0xC4E4) = read-only**. Backend media-status byte layout aynı (e06 `0x040632D0`):
bit0 spare, bit1 temp, bit2 reliability, **bit3 read-only**.

⚠️ Statikte "critical_warning kelimesi = *(0x0080C520)" demiştim; **canlı 0x0080C520=0x00000200 (düşük bayt 0x00)**
→ bu, host critical_warning kaynağı DEĞİL (bir iç event-mask). Host'a giden 0x08, backend read-only durumundan
türüyor (§2/§3). Exact frontend→SMART[0] memcpy baytını canlı değerlerle kesin sabitleyemedim (aday 0x0080C520,
0x0080CD88 canlıda 0x08 tutmadı); **kesinlik: SMART[0]=0x08 canlı ölçüldü, kaynağı backend read-only state.**

## 2. Bit 3'ü kim set ediyor + koşul  [KANIT]
Kök latch = **die block-map tutarlılık taraması**, e06 `0x040632AC`:
```
0x040632AC loop: ldr r2,[r0,r4<<2]; ldr r3,[r1,r4<<2]; cmp r2,r3; bne -> sb++ ; adds r4; cmp r4,#0x400; blo  (1024 girdi)
0x040632D0 ldr r1,=0x040EE73C ; cmp sb,#0x200               ; mismatch >= 512 ?
0x040632D6 ldrb r0,[r1]; orr r0,#4; strb                    ; bit2 reliability HER ZAMAN
0x040632DE itt hs; orrhs r0,#8; strbhs r0,[r1]              ; >=512 -> bit3 READ-ONLY  ->  *(0x040EE73C)
```
Sonra read-only "entry" (e04 `0x0200F368`: `*(0x00806EC8) |= 8`; `0x0200F378`: `*(0x040EF048)=nonzero`).
Aynı çift e04 `0x0200F588`, e06 `0x040665F4/FE`. Kök sebep: die ch3/ce2 program/silme yapamıyor → blok-map
tutarsız → ≥512 mismatch → read-only.

⚠️ **Yeniden hesaplanıyor, latch değil.** Proje geçmişi: NAND silinip spare %3→%100 olmasına rağmen kilit kaldı —
bu mekanizmayla birebir tutarlı (ölü die her boot taramada mismatch üretiyor). (Canlı: sağlık baytı sürekli 0x19
okunuyor; RAM'e yazamadığım için "yazınca hemen geri gelir mi" testini yapamadım — aşağıya bkz. §4.)

## 3. Yazmaları yutan gate  [KANIT + CANLI]
Frontend gate YOK (host'a "başarı" dönüyor). Drop **FTL (e07)**:
```
0x040EC198 ldrb r0,[sl,#2]; 0x040EC19C bics r0,#8; strb r0,[sl,#2]   ; media-status bit3 temizleme (recovery)
0x040EC1AA ldr r4,=0x040EF048 ; 0x040EC1B0 ldrb r0,[r4]; cmp r0,#0
0x040EC1B4 beq 0x40ec150       ; ==0 -> NORMAL COMMIT (yazma işlenir)
0x040EC1B6 blx 0x40ed348/40ed340 ; !=0 -> pending yazmaları DRAIN
0x040EC1C4 bl  0x40d62b8         ; -> DISCARD (sessiz yutma)  ; 0x040EC1C8 strb sb,[r4] (bayrağı temizle)
```
Gate ayrıca `0x040EC230`; okuyucular e07 `0x040DCDAC`, e04 flush `0x0200AD78`. Kural: **0 = yazma açık, nonzero
= read-only.** Persistent read-only göstergesi **health word `0x00806EC8` bit3** (base 0x00806EB8, FTL'de 28 ref).

### Canlı flag ölçümü
```
*(0x040EF048) = 0x00   (transient write-gate; durağanda 0 — drain sonrası temizleniyor, beklenen)
*(0x040EE73C) = 0x00   (media-status bit3=0; bu boot'ta scan set etmemiş)
*(0x00806EC8) = 0x19   (bit3=1  <-- read-only durumunu gösteren TEK sabit RAM flag)
Baseline yazma testi (patch'siz): TUTMADI — 1MB @500MB yazıldı, geri okuma tamamen sıfır.
```

## 4. Canlı RAM'de yazmayı açan tek bayt — DENENDİ, UYGULANAMADI
**Prensipte hedef:** read-only state flag'ini 0'lamak — birincil aday **`0x00806EC8` bit3** (0x19→0x11),
destek **`0x040EF048`→0** ve **`0x040EE73C` bit3→0** (ikisi de canlıda zaten 0).

**DENEME (görev item 4, canlı):**
- `ram_yaz` (vendor 0x87) önce zararsız test edildi (blok değiştirmeden geri yazma) → ioctl **True**, cihaz **live**.
- `0x00806EC8` bit3 temizlenip yazıldı → geri okuma **hâlâ 0x19** (patch tutmadı).
- Kalıcılık probu: 0x0080xxxx / e00 / e04 / 0x0081E6xx bölgelerinde bir bayta test değeri yazıldı → **hiçbirinde
  kalıcı olmadı** (PERSISTS=False), cihaz her seferinde live.
- Kodda **`cmp #0x87` yok**; e03 komut allow-list'i (`0x040C7208`) 0x84/0x86/0x80/0x81/0x82/0x0c/0x0d/0x14/0x15'e
  izin veriyor — **0x87 yok.**

**SONUÇ (dürüst):** **Ürün firmware'i canlı RAM yazmayı desteklemiyor** — `jdcanli.ram_yaz`'ın kullandığı vendor
0x87 komutu bu firmware'de tanımlı değil; başarı dönüyor ama hiçbir şey yazmıyor. Dolayısıyla **"şu tek baytı
yaz → yazma açılır" canlıda uygulanamıyor.** Ayrıca uygulanabilse bile read-only durumu die-mismatch
taramasından sürekli yeniden türediği için (§2) etki **geçici** olurdu.

**Yazmayı gerçekten açmanın yolu (RAM poke değil):**
1. **Die neutralize** — ölü die'ı (ch3/ce2) die-presence tablosundan çıkarmak (proje notu: `dpd_clk200.bin+0x310`,
   loader/offline yol) → tarama mismatch üretmez → read-only tetiklenmez.
2. **Kod patch (GDP yolu):** gate dalını (`0x040EC1B4`) ya da setter'ı (e06 `0x040632DE` / e04 `0x0200F368`)
   NOP'lamak. Canlı 0x87 olmadığı için bu ancak loader (GDP) üzerinden yüklenebilir; ⚠️ NAND RESET okuma yolunu
   kalıcı bozuyor (proje notu) — dikkatli olun.
3. Eğer başka bir vendor RAM/register-yazma komutu bulunursa (§5 tam çözülemedi), §4'teki flag'ler + baseline
   yazma testi ile denenebilir; ama (2)/(1) kalıcı, RAM poke değil.

## 5. Vendor komut / kilit temizleme  [KISMİ]
Vendor dispatch table-tabanlı (Fork analizinde e02 ~0x00806540-0x008066A0; linear disasm data'da desync).
Doğrulanan komutlar: 0x00 GetReturn, 0x84 reg-oku, 0x86 ram-oku (hepsi jdcanli'de çalışıyor). e03 allow-list
`0x040C7208`: izinli = {0x0c,0x0d,0x14,0x15,0x80,0x81,0x82,0x84,0x86} (moda göre). **Kilidi temizleyen özel
vendor komutu YOK**; RO flag sadece FTL içinde drain sonrası temizleniyor (`0x040EC1C8`). **Çalışan bir RAM/
reg-yazma vendor komutu tespit edilemedi** — bu, item 4'ün canlı uygulanamamasının kök sebebi.

---
### Ölçüm dürüstlüğü notu
- KANIT (statik+canlı): §1 SMART=0x08, §2 die-mismatch setter, §3 FTL gate + flag'ler, §4 0x87 no-op.
- ÇÜRÜTÜLEN statik iddialar (canlı ile): critical_warning kaynağı 0x0080C520 DEĞİL; 0x0081E6B0 bit3 canlı 0;
  0x00807250 flag değil (skipdata disasm artefaktıydı).
- YAPAMADIĞIM: canlı RAM yazma (araç/firmware desteklemiyor) → item 4 canlı "TUTTU" gösterimi mümkün olmadı;
  exact SMART[0] memcpy kaynak baytı kesin sabitlenemedi.
