# JD1024 (MAXIO MAP1202) — Ürün firmware'ine standart NVMe 0x11/0x10 ile FW yazılabilir mi?

Kaynak imaj: `re/fw_canli/e*.bin` (diskin çalışan ürün firmware'inden, JD2024, canlı RAM'den çıkarıldı).
Araçlar: `re/fw_canli/tk.py` + `tk2.py`/`refs.pkl`. Karşılaştırma imajı: `re/gdp/c1.bin` (GDP **loader**, ayrı firmware).
Mimari doğrulama: ürün FW = **Thumb-2**; GDP loader = **ARM** (aşağıda kanıt). Her iddianın yanında dosya+ofset+disasm var.
Diske hiçbir yazma/komut gönderilmedi — salt statik analiz.

---

## KARAR

> **fw-download/fw-commit (standart NVMe opcode 0x11 + 0x10) ile, tel/loader olmadan bu diskin çalışan ürün
> firmware'ine yeni firmware imajı YAZILAMAZ — HAYIR.**
>
> Çünkü ürün firmware'inin NVMe admin dağıtıcısında (e00 `0x000037F0`) opcode **0x11 gerçek bir "Firmware Image
> Download" DEĞİL**: MAXIO onu miniport/bridge modundaki **vendor komut taşıma kanalı** olarak gasp etmiş
> (`0x00003AE8`: CDW11'i `<<2` yapıp `0xAE34FF08 / 0x12340008 / 0xBD34FF08` vendor sihirli sayılarıyla
> karşılaştırıyor — MPTool'un miniport kodlamasının birebir aynısı). Sihir yoksa (standart host'un
> yolladığı CDW11=OFST=0 durumu) `0x00003DF6` üzerinden imaj tamponlamayan bir worker'a düşüyor.
> Opcode **0x10 handler'ı** (`0x00003B3C` → worker `0x040C08AE`) bir **WDMA/RDMA kuyruk/DMA** rutinidir;
> firmware slot'u / LDBK info page / CodeMap / NAND sistem-alanı programı **hiç referans etmez** — yani bir FW
> aktivasyonu yapmaz. Gerçek on-NAND firmware formatını (LDBK + CodeMap + MKSSD kod sayfaları) işleyen kod
> **yalnızca FTL boot/system-area** tarafındadır (e06/e07/e09) ve NVMe admin yolundan erişilemez. Ayrıca ürün
> FW vendor kanalı **salt-okunur** (kodda `cmp #0x87` (RAM-write) YOK; jdcanli ile canlı doğrulandı ki `0x87`
> no-op). Dolayısıyla ne standart 0x11/0x10, ne de vendor yolu firmware'i NAND'a yazabilir. **Firmware yazımı
> sadece GDP loader'ı üzerinden mümkün** (MPTool da öyle yapıyor), o da ROM download moduna girmeyi gerektirir.

---

## 0. Kritik ayrım: GDP loader ≠ ürün firmware (önceki analiz hangisiydi?)

`ANALIZ_NVME.md` (0x11@`0x040CA7D0`, 0x10@`0x040CA80C`, dispatcher `0x040CA67C`) **GDP loader'ı** (`c1.bin`,
@0x040C0000, 192KB) inceler ve **ARM** modunda çözülür. Bu, ürün firmware'i DEĞİL. Doğrulama:

- Ürün FW (fw_canli) Thumb'da temiz çözülüyor. Örn. e07 `0x040EC198 ldrb.w r0,[sl,#2]; bics r0,r0,#8` (readonly
  doc §3 ile birebir). GDP `c1.bin` ise ARM'da temiz (`d.py`).
- GDP dispatcher'ının bulunduğu bölge ürün dökümünde **YOK**: `0x040C8000–0x040CC000` fw_canli'de eksik
  (`tk.seg_for(0x040CA67C)` → MISSING). Yani GDP'nin 0x11/0x10 handler'ı ürün FW hakkında bilgi vermez.
- Ürün FW'nin admin dağıtıcısı **başka yerde** (e00, aşağıda) — ve tamamen çıkarılmış durumda, analiz eksiksiz.

Sonuç: soruyu ürün firmware'i (fw_canli) üzerinden yeni baştan cevapladım.

---

## 1. Ürün FW NVMe admin komut dağıtıcısı — e00 `0x000037F0` [KANIT]

Selector = NVMe opcode (`ctx[0] >> 24`). Komut context'i `0x0080BA60` (GDP context layout'uyla aynı:
`[0]`=HW header {opcode[31:24], sqid[20:16], func[13:10]}, `[6]`=CID, `[8]`=NSID(CDW1), `[0x2c]`=CDW10,
`[0x30]`=CDW11, `[0x1c/0x24]`=PRP1/PRP2).

```
000037F0  ldr  r1,=0x0080BA60      ; NVMe komut context'i
000037F2  ldr  r0,[r1]             ; ctx[0] = HW header
000037F4  ubfx r2,r0,#0xa,#4       ; func id
000037FA  ubfx r2,r0,#0x10,#5      ; sqid
00003800  lsr.w sl,r0,#0x18        ; sl = OPCODE  <-- dağıtım anahtarı = NVMe opcode
00003804  ldrh r0,[r1,#6]          ; cid
0000380A  ldr  r4,[r1,#8]          ; r4 = NSID (0x11/0x10 için "cbz r4" = NSID==0 şartı)
```

Her komut önce mode-kapılı bir izin kontrolünden geçiyor (`0x000038D0 blx 0x1470c` → veneer → e03 `0x040C7208`;
bu fonksiyon coherent, veneer tablosunun güvenilir olduğunu da kanıtlıyor). Normal modda (`*(0x0080C438+0x657)`
∉ {0x10,0x40}) tüm opcode'lara izin veriyor → 0x10/0x11 handler'a ulaşıyor.

Dağıtım (e00 `0x000038E0` ve `0x00003914`), opcode → hedef:

| opcode | dal | handler |
|---|---|---|
| 0x00–0x0c | `0x38EA tbb [pc,r0]` | jump table |
| **0x10 Firmware Commit** | `0x38E2 beq 0x39dc` → `b 0x3b3c` | **`0x00003B3C`** |
| **0x11 Firmware Download** | `0x391C cmp #0x11; beq 0x3a18` → `b 0x3ac2` | **`0x00003AC2`** |
| 0x14 | → `0x3b64` | |
| 0x7c | → `0x3a8a` | |
| 0x80/0x81/0x82 | → `0x3a0c/0x3a4e` | Security-benzeri |
| 0x84 | → `0x3db2` | |
| **0xC1 / 0xC2 vendor** | `0x3936/0x393a` → `0x3aa6/0x3ab4` → `b.w 0x40f0` | vendor engine `0x000040F0` |
| default | `0x393e` | invalid |

`0xC1→0x3aa6 (mov r0,#0; b.w 0x40f0)`, `0xC2→0x3ab4 (mov r0,#1; b.w 0x40f0)` — jdcanli'nin canlı doğruladığı
vendor kanalı budur, yani bu **gerçekten çalışan, canlı dağıtıcı**.

---

## 2. Opcode 0x11 (Firmware Download) handler'ı — vendor kanalı, gerçek download DEĞİL [KANIT]

`0x00003AC2` (NSID==0 → `0x3ae8`, aksi halde erken completion):

```
00003AC2  cbz  r4,#0x3ae8           ; NSID==0 ise gerçek yola
; --- 0x3ae8: CDW11'i vendor sihirli sayılarıyla karşılaştır ---
00003AE8  ldr  r1,=0x0080BA60
00003AEA  mvn  ip,#0xff00           ; ip = 0xFFFF00FF (byte1 maskesi)
00003AEE  ldr  r4,=0x12340008
00003AF0  ldr  r0,[r1,#0x30]        ; r0 = CDW11
00003AF2  and.w ip,ip,r0,lsl #2     ; (CDW11<<2) & 0xFFFF00FF
00003AF6  cmp  ip,r4                 ; == 0x12340008 ? (miniport "normal" magic)
00003AF8  beq  #0x3b0e
00003AFA  ldr.w ip,=0xAE34FF08       ; enable magic (miniport)
00003AFE  cmp.w ip,r0,lsl #2         ; (CDW11<<2) == 0xAE34FF08 ?
00003B04  ldrne.w ip,=0xBD34FF08     ; disable magic (miniport)
00003B08  cmpne.w ip,r0,lsl #2
00003B0C  bne  #0x3b30               ; sihir YOK -> 0x3b30 -> b.w 0x3df6
; --- 0x3b0e: sihir VAR -> vendor transfer kur, başarı dön ---
00003B12  ubfx r0,r0,#6,#0x18        ; uzunluk = CDW11 bit[29:6]
00003B16  ldr  r2,=0x0080487C; str r0,[r2]
00003B1A  ldr  r0,[r1,#0x2c]         ; CDW10
00003B1E  lsls r0,r0,#2; adds r0,#4  ; bayt = CDW10*4 + 4
00003B22  str  r0,[=0x00804880]
00003B26  movs r0,#0                 ; status 0 (başarı)
00003B2C  b.w  #0x40f0               ; vendor data-transfer engine
```

**Yorum:** Bu, MPTool'un `ANALIZ_MPTOOL.md §1.3`'te belgelenen **miniport/bridge vendor kodlamasıdır**:
"Miniport enable = `0xAE34FF08`, normal = `0x1234FF08`, bridge = `0x1234FF08>>2`". Firmware `CDW11<<2` yapıp
karşılaştırıyor; yani NVMe opcode 0x11, 0xC1/0xC2'nin miniport-modu ikizi olarak **vendor komut taşımaya**
tahsis edilmiş. Standart bir host (`nvme fw-download`) CDW11=OFST=0 gönderir → `(0<<2)=0`, hiçbir sihre
uymaz → **sihirsiz yol** `0x3df6`. Yani standart FW download bu kanala hiç girmez.

Sihirsiz yol `0x00003DF6` (imaj tamponlamaz):
```
00003DF6  movs r0,#1; movw r1,#0x1d48; push {r4,lr}
00003DFE  blx  #0x61fc              ; indeksli logger(1, str=0x1d48)
00003E04  blx  #0x14788             ; worker (ARM veneer)
00003E08  cmp  r4,#1; cmpne r4,#3; ... (dönüşe göre bir bayrağı temizler)
```
Veneer `0x14788` (`0xE51FF004 = ldr pc,[pc,#-4]` + hedef) dökümde `0x040C0C0A`'yı gösteriyor; ama o adres
`0x040C0BA2` fonksiyonunun **inline literal pool'unun ortası** (`0x040C0BCA b #0x40c0c30` pool'u atlıyor;
`0x040C0C0C=0x06758000` vb. peripheral adresleri). Yani bu slot dökümde ya bayat ya da ölü bir handler.
Her hâlükârda: bu zincirde **imaj-tamponlama / staging buffer / offset-biriktirme kodu yok**. (Diğer veneer
slotları — gate `0x1470c`→`0x040C7208`, commit `0x14790`→`0x040C08AE` — coherent olduğundan tablo genelde
güvenilir; anomali sadece download slotunda.)

---

## 3. Opcode 0x10 (Firmware Commit) handler'ı — kuyruk/DMA worker'ı, FW aktivasyonu DEĞİL [KANIT]

`0x00003B3C` (NSID==0 → `0x3b56` → `b.w 0x3e18`):
```
00003B3C  cbz  r4,#0x3b56
00003B56  strb r5,[r3]; ...; ldr r0,=0x0080BA60
00003B60  b.w  #0x3e18
; 0x3e18: log + worker
00003E18  push {r4,r5,r6,lr}; mov r5,r0
00003E1C  movw r1,#0x1f5f; movs r0,#1; blx #0x61fc   ; logger(1, str=0x1f5f)
00003E28  mov  r0,r5; blx #0x14790                    ; worker -> veneer -> 0x040C08AE
```

Worker `0x040C08AE` (Thumb, tam çözüldü):
```
040C08AE  ...ctx'ten func/sqid/cid/CDW10 çıkar (ubfx/ldrh)
040C08C8  blx 0x40c7624                     ; (veneer -> e01 0x008012AC)
040C08D0  ...poll CQM 0x06738000+0x6c        ; completion-queue manager busy-wait
040C08E6  ...relay struct 0x0080BB42'ye yaz  ; func/sqid/cid/CDW10 (FW-cmd DEĞİL, komut-relay struct)
040C08FC  blx 0x40c762c (mode 1) / (mode 2)  ; okuma
040C0932  blx 0x40c38f0 / 0x40c38f8 / 0x40c3900  ; e01 kuyruk yardımcıları (0x00801Cxx)
040C0968  ...HW WDMA CTRL 0x06750000+0x48 ve RDMA CTRL 0x06758000+0x48 durumları
040C0982  movw r2,#0x103; ...                ; status 0x103
040C09xx  ...blx 0x40c7544                   ; -> 0x00002E34 = NVMe completion POST
```
Veneer hedefleri doğrulandı: `0x40c7544→0x00002E34` (completion post), `0x40c38e8/f0/f8/3900→e01 0x00801Cxx`
(kuyruk yardımcıları), `0x40c762c→e00 0x00010C00`. **Hiçbiri** firmware slot'u, LDBK, CodeMap veya NAND-program
çağırmıyor. Bu rutin bir **WDMA/RDMA kuyruk + completion** işlemidir; MAXIO opcode 0x10'u da bu amaçla
yeniden kullanmış görünüyor. **Firmware commit/aktivasyon yok.**

---

## 4. Gerçek on-NAND firmware formatı ve neden admin yolundan erişilemez [KANIT]

Firmware imaj formatı (MPTool `ANALIZ_MPTOOL.md §3` + ürün FW string'leri ile doğrulandı):
- **Info page (page 0):** `"LDBK BLOCKS V00"` magic + `"LDBK CONFIG V00"` + **CodeMap** (`+0x220`'den 16-baytlık
  `CODE_ENTRY {u16 firstPage, u16 lastPage, u32 length, u32 loadAddr, u16 enable, u16 checksum}`).
- **FW slot page, table page, opal, nandmem, uefi, TMC table** (LDBK marker'ları e07'de: `0x040EE2E4
  "LDBK BLOCKS V00"`, `0x040EE334 "LDBK NANDMEM TAB"`, `0x040EE344 "LDBK FWTMC MARK"`, `0x040EE354 "LDBK LDPC
  TABLE1/2"`).
- **Kod sayfaları:** her 4KB sayfada `+0x1C0`'da `"MKSSD..."` marker'ı. Ürün FW'nin kendi kod imajlarında canlı:
  e00 `0x000001C0`, e04 `0x020001C0` = `"MKSSD_501003000124620000,Oct 31 2023,...,MAP1202,ZI0PCD2C"`. (MPTool
  `VP_WriteCodeToFlash` de `memcmp(buf+0x1C0,"MKSSD",5)` yapıyor — birebir.)

**Ama:** bu LDBK/CodeMap string'lerine yapılan TÜM referanslar (refs.pkl) yalnız FTL/backend'de:
`0x0406D6BE/0x0406D896 (e06)`, `0x040CCCC0/0x040CCD4A (e09)`, `0x040DA0B0/0x040DAE08/0x040DB320 (e07)`.
Bunlar boot-zamanı **loader-block tarama/doğrulama** kodu (örn. `0x040DA0B0` → `"LDBK BLOCKS V00"` yükleyip
`bl 0x40e3a10` ile 4 aday bloğu memcmp'liyor). NVMe admin dağıtıcısı (e00) veya 0x10/0x11 worker'ları bu
yapılara **hiç dokunmuyor**. Yani host komutundan "LDBK firmware sayfalarını NAND'a yaz" yoluna köprü yok.

---

## 5. Vendor komut seti — firmware/NAND-write alt-komutu var mı? [KANIT + CANLI]

- Vendor engine (0xC1/0xC2/0x11-magic'in ortak hedefi) = `0x000040F0`. Alt-komut dağıtımı e02'de (task'ın işaret
  ettiği `cmp #0x89 @0x00804776`, `#0x8B @0x0080658A`, `#0x58 @0x0080496A`, `#0x83 @0x00804ACC`); ancak bu
  bölge (0x00806540–0x008066A0 tablosu ve 0x00804Axx civarı) **yüksek-entropili/packed** — linear disasm orada
  desync oluyor ve o "cmp" isabetlerinin çoğu **veri içindeki sahte eşleşmeler**. Tabloyu bayt-bayt temiz
  çıkaramadım (önceki denemelerle tutarlı — dürüst not: bu tablo statikte çözülemedi).
- **Kesin ve yöntemden-bağımsız kanıt:** tüm ürün FW segmentlerinde `cmp #0x87` (VC_LDR_CmdWriteRam = RAM'e
  yazma; GDP.bin'i SRAM'e yüklemenin TEK yolu) **hiç yok** (tam tarama: 0x82/0x83/0x88/0x89/0x8a/0x8b/0x58/0x4d
  var, **0x87 yok**). Canlı doğrulama (readonly doc §4/§5): jdcanli `ram_yaz` (0x87) ioctl True dönüyor ama
  **hiçbir baytı kalıcı yazmıyor** — 4 farklı bölgede test edildi, hepsi no-op. Yani vendor kanalı **salt-okunur**
  (0x84 reg-read, 0x86 ram-read, 0x00 getreturn çalışıyor; yazma yok).
- Dolayısıyla firmware/NAND-system-area yazan **kullanılabilir bir vendor alt-komutu YOK**, ve ürün FW üzerinden
  GDP loader'ı RAM'e yükleyip çalıştırmak da (0x87 olmadan) mümkün değil.

---

## 6. MPTool referansı — MAXIO firmware'i nasıl yazıyor (standart 0x11/0x10 DEĞİL) [KANIT]

`ANALIZ_MPTOOL.md §4–5`: firmware yazımı `VP_PROC_DownloadProgram @0x441ED4` ile, ve **önce GDP loader'ı SRAM'e
yükleyip** (adım 4: `VP_WriteCodeToMemNew2 @0x4368F0` → vendor `0x87` WriteRam) sonra GDP'ye zıplayarak yapılıyor.
GDP, LDBK-yapılı sayfaları NAND'a yazıyor (`VP_Cougar_FillInfoPage` info+CodeMap, `VP_WriteSlotPage`,
`VP_WriteCodePage` → `VP_WriteCodeToFlash` → `VP_WritePage`). **Standart NVMe opcode 0x11/0x10 hiç kullanılmıyor.**
(Not: MPTool tablosundaki "0x11" = vendor payload alt-komut baytı `FF E5 11` = `VC_GDP_CmdInitGDP`, NVMe opcode
0x11 DEĞİL — isim çakışması.)

---

## 7. En yakın alternatif yol (HAYIR ise ne yapılır)

Firmware yazımı **yalnızca GDP loader** üzerinden mümkün ve GDP'ye ulaşmak ROM download moduna girmeyi gerektirir:

1. **ROM download modu (tel/pin-short) → GDP loader → MPTool/GDP protokolü.** Task'ın hariç tuttuğu yol; ama
   MAP1202 için firmware yazmanın gerçek yolu bu. Format = §4'teki LDBK info page + CodeMap + MKSSD kod sayfaları
   (MPTool DAT/SYS setiyle üretilir).
2. **Yazılımdan ROM'a zıplama (0x83 JumpToROM) ile tel'siz download modu?** Ürün FW'de `cmp #0x83 @0x00804ACC`
   var ama o bölge packed/desync — handler'ın gerçekten ROM download moduna reset atıp atmadığını statik olarak
   **doğrulayamadım**, ve vendor yazma kanalı salt-okunur olduğundan sonrasını beslemek zaten şüpheli. Bunu
   "kanıtlanmadı" olarak bırakıyorum; test edilecekse **önce zararsız okuma ile** (getreturn 0x00) yanıt modu
   izlenmeli, canlı 0x83 denemesi risklidir (brick).
3. Standart `nvme fw-download`/`fw-commit` denemek **anlamsız ve güvenli-etkisiz**: 0x11 sihirsiz yola (ölü
   worker) düşer, 0x10 kuyruk-DMA yapar; ikisi de NAND'a firmware yazmaz. (Yine de diske komut GÖNDERİLMEDİ.)

---

## 8. Dürüstlük / sınırlar

- **Çözülemeyen:** e02 vendor alt-komut tablosu (0x00806540–0x008066A0) packed/desync — temiz çıkarılamadı
  (item 5 kısmen). Sonuç buna bağlı değil: yazma-yeteneği karşılaştırması (`cmp #0x87`) provably yok + canlı
  0x87 no-op.
- **Anomali:** download sihirsiz-yol veneer'i (`0x14788`) dökümde bir literal pool'u gösteriyor; ya bayat ya ölü
  handler. Zincirde imaj-staging kodu olmadığı kesin, ama o worker'ın tam davranışını disasm edemedim.
- **Eksik bölge:** `0x040C8000–0x040CC000` fw_canli'de yok (GDP'nin dispatcher bölgesi). Ürün FW admin yolu e00'da
  ve tamamen çıkarılmış olduğundan bu boşluk cevabı etkilemiyor.
- **oacs=0x17** (bit2 FW D/C) host'a ilan ediliyor (ölçülmüş) ama §2/§3 gösteriyor ki handler'lar bunu
  gerçek firmware güncellemesiyle onurlandırmıyor — ilan edilen ≠ işlevsel. fw-log'un 5 slotta "JD2024"
  dönmesi de statik/kozmetik.
