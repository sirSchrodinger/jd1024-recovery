# JD1024 (MAP1202) — Bakım kodunu NVMe ile SRAM'e yükleyip çalıştırma yolu (ISP) — STATİK ANALİZ

**Bakım kodunu NVMe üzerinden SRAM'e yükleyip çalıştırmak mümkün: HAYIR — çünkü (a) ürün firmware'inin
vendor kanalında SRAM'e yazan hiçbir alt-komut yok (`cmp #0x87` tüm segmentlerde HİÇ yok; canlı `0x87` no-op),
ve (b) tek "PRAM'e devret" işlevi olan 0x81/0x82, host'un verdiği bir adrese atlamıyor — worker `e01:0x008038E0`
yalnız SABİT pool sabitlerini (`0x040C71E9`, `0x0000CD37`) `*(0x0080BF88)`/`*(0x0080C094)`'e yazıp gömülü
`0x0000CD36`'ya atlıyor (`0x008038F6 str r0,[r1]`, `0x00803920 b.w #0xcd36`). Yani ne kod SRAM'e konabiliyor
ne de host adresine dallanılıyor.**

Kaynak: `re/fw_canli/e*.bin` (diskin çalışan ürün FW'i, canlı RAM'den). Araçlar: `tk.py`/`tk2.py`/`refs.pkl`,
`d.py`, `c.py`, `br.py`. Diske hiçbir komut gönderilmedi; salt statik. `[READ]`=imajdan bire bir, adres verildi.

> **DİKKAT — kritik ayrım:** `re/ANALIZ_SILME.md` ve `ANALIZ_NVME.md` **GDP loader'ını** (`c1.bin`/`c0.bin`, ARM)
> inceler; oradaki `0x040ED2F4` dispatch tablosu, `0x8A/0x8B` handler'ları ve `VC_LDR_CmdJumpToPRAM` **ROM/loader
> modu** içindir. Bu rapor **çalışan ürün firmware'ini** (fw_canli, Thumb-2) inceler. İkisi aynı çip ama ayrı
> program; ürün FW'de o tablo/handler'lar YOK (`tk.find_word(0x040C3DB4)` → boş). MPTool'un "önce 0x87 ile GDP'yi
> SRAM'e yükle, sonra 0x82 ile atla" akışı **ROM download modunu** gerektirir; aşağıdaki analiz bunun ürün FW
> üzerinden (tel'siz) **kapalı** olduğunu gösteriyor.

---

## 0. Yönetici özeti

| Soru | Cevap | Ana kanıt |
|---|---|---|
| 0x80/0x81/0x82 = "kodu SRAM'e koy + devret" mi? | **Kısmen: mod geçişi VAR, host-kod yürütme YOK** | worker `0x008038E0` sabit adres kuruyor, payload okumuyor |
| `*(0x0080BF88)`/`*(0x0080C094)` kim okuyor? | **Durum makinesi `0x0000CD36`** | `0x0000CDF8 ldr r1,[BF88]; 0x0000CE0C bx r1` |
| İmza/RSA doğrulaması var mı? | **HAYIR (ve gereksiz)** | "RSA/sign/verify/sha" string YOK; `cmp #0x87` YOK |
| SRAM'e yazan alt-komut var mı (0x87)? | **HAYIR** | `cmp #0x87` tüm segmentlerde 0 adet; canlı no-op |
| 0x0C/0x0D/0x14/0x15 seri-flash mı? | **Ürün FW'de kanıt YOK** | SPI/NOR string yok; temiz handler bulunamadı (kısmen bulamadım) |
| Liste-dışı komut nasıl reddediliyor? | **Mod-kapılı `0x040C7208` + default `0x393e`** | aşağıda §4 |
| e02'de fabrika-format / sistem-alanı komutu? | **YOK; e02 zaten DATA segmenti** | entropi 5.425, tabloya pool-ref 0 |

**Sonuç:** İki bağımsız kilit var. (1) Kod SRAM'e konamıyor (WriteRam yok). (2) Konsa bile 0x82 host adresine
atlamıyor (sabit gömülü hedef). ISP tarzı "kendi bakım kodunu yükle+çalıştır" yolu ürün FW üzerinden KAPALI.

---

## 1. 0x81/0x82 işleyicisi — tam disassembly (görev madde 1)

### 1.1 Dağıtıcıya kadar
Ürün FW NVMe admin dağıtıcısı `e00:0x000037F0`; anahtar = NVMe opcode (`ctx[0]>>24`, ctx=`0x0080BA60`)
[ANALIZ_FW_FLASH §1 ile tutarlı]. Opcode dağıtımı `0x00003914`:
```
00003916  cmp  r0,#0x81
00003918  beq  #0x3a16              ; 0x81 -> 0x3a16
0000392E  cmp  r0,#0x82
00003930  beq  #0x3a16              ; 0x82 -> 0x3a16  (0x81 ile AYNI handler)
00003932  cmp  r0,#0x84
00003934  beq  #0x3a1e              ; 0x84 ayrı
00003A16  b    #0x3a4e              ; ortak 0x81/0x82 gövdesi
```
[READ] Yani **0x81 ve 0x82 aynı handler'ı** (`0x00003A4E`) paylaşıyor, 0x80 ve 0x84 ayrı (§1.4).

### 1.2 Ortak gövde `e00:0x00003A4E` — iki kapı + tail-call [READ]
```
00003A4E  ldr  r0,=0x00804750
00003A50  ldrb r1,[r0]              ; *(0x00804750)
00003A52  ldrb r0,[r0,#3]           ; *(0x00804753)
00003A54  orrs r0,r1
00003A56  bne  #0x3a3e              ; KAPI-1: ikisi de 0 değilse -> reddet (0x3a3e = hata/status)
00003A58  ldr  r0,=0x0080BA60
00003A5A  ldrb.w r0,[r0,#0x2f]      ; *(0x0080BA8F)
00003A5E  cmp  r0,#0xef
00003A60  beq  #0x3a80
00003A62  cbz  r0,#0x3a80           ; KAPI-2: *(0x0080BA8F) ∈ {0, 0xEF} ise devam, aksi reddet
00003A80  add  sp,#0x14
00003A82  pop  {r4,r5,r6,r7,r8,sb,sl,fp,lr}
00003A86  b.w  #0x8038e0            ; *** worker'a TAIL-CALL (e01) ***
```
[READ] Handler payload'dan **hiçbir bayt okumuyor** — sadece iki global durum baytını kapı olarak kullanıyor,
sonra `0x008038E0`'a atlıyor. `br.py 0x008038E0` → tek çağıran bu `0x3a86` (yani worker yalnız 0x81/0x82'ye ait).

### 1.3 JumpToPRAM worker `e01:0x008038E0` — ASIL İŞ [READ] (KİLİT KANIT)
```
008038E4  ldr  r2,=0x008058A0
008038EC  movs r1,#0x10
008038EE  strb r1,[r2]             ; *(0x008058A0) = 0x10   <-- "loader/maintenance mod" baytı
008038F0  ldr  r1,=0x0080BF88
008038F4  ldr  r0,=0x040C71E9      ; SABİT (Thumb 0x040C71E8, e03 içi)
008038F6  str  r0,[r1]             ; *(0x0080BF88) = 0x040C71E9   <<< 1. işaretçi kuruluyor
008038FC  bl   #0x4d1c
00803900  ldr  r2,=0x06301000
0080390C  str  r1,[r2,#0x40]       ; *(0x06301040) = 0x000493E0   <<< çekirdek entry/vektör HW register'ı
0080390E  ldr  r1,=0x008058A4
00803910  strb r0,[r1]             ; *(0x008058A4)=1
00803912  ldr  r1,=0x00804750
00803914  strb r0,[r1]             ; *(0x00804750)=1  (kapı-1'i işaretler)
00803916  ldr  r1,=0x0080C094
00803918  ldr  r0,=0x0000CD37      ; SABİT (Thumb 0x0000CD36, e00 içi)
0080391A  str  r0,[r1]             ; *(0x0080C094) = 0x0000CD37   <<< 2. işaretçi kuruluyor
0080391C  pop  {r4,lr}
00803920  b.w  #0xcd36             ; *** gömülü 0x0000CD36'ya ATLA ***
```
[READ] **Bu, "kodu SRAM'e koyup oraya devretme" DEĞİL, "gömülü loader durum makinesine geçiş"tir:**
- Kurulan iki işaretçi de **imajın içindeki sabit adresler** (`0x040C71E8`, `0x0000CD36`) — host'un yüklediği
  bir tampon değil.
- Worker **payload'ı hiç okumuyor** (pool sabitleri dışında girdi yok). MPTool'un `payload[4]=0x5A` "magic"i
  ürün FW'de **kontrol edilmiyor** (0x3a4e ve 0x8038e0'da payload baytı okuması yok).
- `0x06301040`'a bir kod adresi (`0x000493E0`) yazılıyor = MAP1202'nin çok-çekirdekli boot/entry register'ı
  (bkz. §1.6). Bu da sabit.

### 1.4 0x80 ve 0x84 (karşılaştırma) [READ]
```
0x80: 0x3a0c  bl 0x00803440 (link/HW durum kontrolü: 0x06740000/0x06744000/0x06722000 okur)
              -> cbz ise hata(0xc); değilse b.w 0x3d6a -> blx 0x61fc(id) ; blx veneer 0x14768 -> e03:0x040C0DB0
0x84: 0x3db2  blx 0x61fc(id=0x1be3) ; blx veneer 0x14778 -> e03:0x040C0CAC   (task: 0x84 canlıda FW'i düşürüyor)
```
[READ] 0x80/0x84 de **loader bölgesi (e03) fonksiyonlarına veneer'le** delege eder; hiçbiri SRAM'e host kodu
yazmaz/host adresine atlamaz. 0x84'ün loader hedefi (`0x040C0CAC`) task'ın "0x84 FW'i düşürüyor" gözlemiyle
uyumlu (kırılgan/kısmen-resident loader).

### 1.5 İşaretçileri KİM okuyor? (görev madde 1'in açık sorusu) [READ]
`*(0x0080BF88)` ve `*(0x0080C094)`, bir **callback/durum-makinesi mimarisinin slotları**; onlarca yerden
YAZILIYOR (`callers.py` çıktısı: BF88'e 18, C094'e 30+ yazma; e00/e01/e03/e08). Asıl **okuyup çalıştıran**,
0x82'nin atladığı durum makinesi `e00:0x0000CD36`:
```
0000CD58  ldr  r2,=0x0080C094          ; slot[0]
0000CD5C  ldr  r3,=0x0080C0A8          ; slot[1]
0000CD60  ldr.w ip,=0x0080C3C0         ; slot[2]     -> BF88'deki fn, duruma göre bu 3 slottan birine yazılır
0000CD80  ldr  r1,=0x040C62B1          ; kurulacak loader fn (Thumb 0x040C62B0)
...
0000CDF6  ldr  r1,=0x0080BF88
0000CDF8  ldr  r1,[r1]                 ; r1 = *(0x0080BF88)  (= 0x82'nin kurduğu 0x040C71E8)
0000CE04  str.w r1,[ip]                ; *(0x0080C3C0)=r1
0000CE0C  bx   r1                      ; *** BF88'deki fonksiyonu ÇALIŞTIR ***
0000CE0E  str  r1,[r2]                 ; ya da *(0x0080C094)=r1
0000CE14  bx   r1                      ; *** çalıştır ***
0000CE16  str  r1,[r3]                 ; ya da *(0x0080C0A8)=r1
0000CE1C  bx   r1
```
[READ] **`*(0x0080BF88)` okunup `bx r1` ile yürütülüyor** (`0x0000CE0C/CE14/CE1C`) ve aynı değer per-slot
diziye (`0x0080C094 / 0x0080C0A8 / 0x0080C3C0`) dağıtılıyor. `*(0x0080C094)` = "geçerli vendor/ana-durum
handler'ı" slotu: 0x82 onu `0x0000CD36`'ya, temizlik yolu (`0x00004258 str r0,[r8=C094]`, r0=`0x00003B6F`)
`0x00003B6E`'ye set eder. Yani bu slotlar **her zaman gömülü FW adreslerini** tutar.
> Bu slotların **son tüketici çağrı yeri** (scheduler) `ldr;ldr;blx` kalıbıyla temiz eşleşmedi (`callers2.py`
> 0 sonuç) — muhtemelen HW-vektör (`0x06301040`) ve/veya indeksli dağıtım üzerinden. Kesin son çağrı noktasını
> **bulamadım**; ama `0x0000CD36`'nın `*(0x0080BF88)`'i `bx`'lemesi kesin ve host-kontrolü için yeterli reddi sağlar.

**Neden host-kod yürütülemiyor (özet):** BF88'i değiştirebilmek için çalışan bir SRAM-yazma primitifi lazım —
yok (§2). 0x8A NAND'a yazar (SRAM'e değil), 0x86 sadece okur. Dolayısıyla BF88/C094 host tarafından
saptırılamaz.

### 1.6 `0x06301000` = çok-çekirdek boot/entry register bloğu [INFER, güçlü]
`0x82` worker'ı (`0x0080390C`) ve durum makinesi (`0x0000CD7C str r6,[r5,#0x40]`, r5=`0x06301000`, r6=`0x000493E0`)
bu register'a kod adresleri yazıyor; temizlik yolu (`0x0000422C str r4,[r0,#0x40]`, r4=0) 0 yazıyor.
Bir HW register'a fonksiyon adresi yazmak = ikinci çekirdeğin entry/reset vektörünü kurmak (MAP1202 3-çekirdek).
Yine sabit (`0x000493E0`), host-kontrollü değil.

---

## 2. İmza/RSA + SRAM'e yazma (görev madde 1 alt-sorular)

### 2.1 SRAM'e yazan alt-komut (WriteRam 0x87) YOK [READ + CANLI]
- Tüm ürün-FW segmentlerinde `cmp #0x87` **0 adet**; `cmp #0x86` de **0 adet** (`c.py 0x86 0x87` → boş).
  Yani 0x86 (ReadRam, canlı çalışıyor) ve 0x87 **cmp-zinciriyle değil, tablo/indeks ile** dağıtılıyor; tabloda
  0x86'nın geçerli girişi var, 0x87'nin **yok/no-op**.
- Canlı doğrulama (ANALIZ_FW_FLASH §5, önceki oturum): `jdcanli.ram_yaz` (0x87) ioctl `True` dönüyor ama
  **4 farklı bölgede hiçbir baytı kalıcı yazmıyor** — no-op. Task'ın "0x87 belleği değiştirmiyor" bulgusuyla birebir.
- **Sonuç:** bakım kodunu SRAM'e koymanın TEK vendor yolu (WriteRam) ürün FW'de yok. Bu tek başına ISP'yi kapatır.

### 2.2 İmza/RSA doğrulaması YOK (ve gereksiz) [READ]
- String taraması: `RSA / rsa / sign / Sign / verify / Verify / sha / SHA` → **hiçbir segmentte yok**.
  (Sadece e07'de "Serial Number:", e06'da bağımsız "Format" log'u var.)
- MPTool'daki `VC_LDR_CmdWriteRamRsa` (imzalı RAM yazma) ürün FW'de karşılıksız: yazma komutu hiç olmadığından
  imza kapısı da yok. **İmza kontrolü yok** — ama bu bir açık değil, çünkü yazılacak komut da yok.

---

## 3. 0x0C / 0x0D / 0x14 / 0x15 işleyicileri + ayrı seri flash? (görev madde 2)

- Ürün-FW **kodunda** bu alt-komutlar için temiz `cmp`/handler **bulunamadı** (bkz. §4: bunlar veri-güdümlü
  loader dağıtımında). MPTool tablosunda `0x0A=EraseSPI`, `0x0C=SPI-write` **GDP loader** komutlarıdır.
- **Ayrı seri flash (SPI NOR) kanıtı YOK:** `SPI/spi/NorFlash/nor(as word)` string yok (tek "nor" isabetleri
  "ignore/normal/nore buf" içindeki tesadüf). Register kanıtı da bulunamadı. Ürün FW'nin firmware'i **NAND'da**
  (kod sayfalarında `+0x1C0` = `"MKSSD_501003000124620000,...,MAP1202,ZI0PCD2C"`; canlı e00 `0x000001C0`,
  e04 `0x020001C0`) [ANALIZ_FW_FLASH §4]. Yani bu diskte vendor yolundan erişilen ayrı bir seri flash
  **görünmüyor**.
- Not: 0x82 sonrası mod=0x10'da validator (§4) `cmd ≤ 0x0C` (0x0A/0x0C dahil), `0x14`, `0x84`'e izin verir;
  yani mimari olarak "loader modunda 0x0A/0x0C" kapısı açılıyor ama ürün FW dökümünde bu handler'ların gövdesini
  ve bir SPI hedefini **doğrulayamadım (bulamadım)**. GDP loader'daki (`c1.bin`) EraseSPI/SPI-write ürün FW'e
  taşınmış görünmüyor.

---

## 4. Dispatcher + liste-dışı komut reddi (görev madde 3) [READ]

### 4.1 Mod-kapılı izin fonksiyonu `e03:0x040C7208` (task'ın "izin listesi"nin GERÇEĞİ)
Bu adres bir **veri tablosu değil**, bir **fonksiyon**. `e00:0x000038D0 blx #0x1470c` (veneer `0x0001470C
ldr pc,[=0x040C7209]`) ile çağrılıyor; çağıranlar `e00:0x000038D0`, `e01:0x00800D5E`. r1=cmd, r2=`*(0x0080CA8F)`
(=`*(0x0080C438+0x657)`, mod baytı):
```
040C7208  ldr r2,=0x0080C438 ; ldrb.w r2,[r2,#0x657]  ; r2 = mod baytı
040C720E  cbz r0,#0x7242
040C7210  cmp r1,#0x81 ; it ne ; cmpne r1,#0x82 ; beq 0x7246   ; 0x81/0x82 -> HER modda İZİN
040C7218  cmp r2,#0x10 ; beq 0x7222                            ; mod 0x10 -> grup A
040C721C  cmp r2,#0x40 ; beq 0x7230                            ; mod 0x40 -> grup B
040C7220  b   0x7246                                           ; diğer mod -> İZİN
; grup A (mod 0x10): cmd<=0x0C -> izin ; cmd==0x14||0x84 -> izin ; aksi RED (0x724a)
; grup B (mod 0x40): cmd==0x0D||0x15 -> RED ; cmd==0x80||0x86 -> RED ; aksi izin
040C7246  movs r0,#1 ; bx lr    ; İZİN
040C724A  movs r0,#0 ; bx lr    ; RED
```
[READ] Task'ın verdiği küme `{0x0C,0x0D,0x14,0x15,0x80,0x81,0x82,0x84,0x86}` bu fonksiyonun cmp
immediate'larıdır. Yani "izin listesi" aslında **mod-bağımlı bir komut geçidi**; hangi komutun geçtiği
`*(0x0080CA8F)` mod baytına bağlı. (0x82 worker'ı `*(0x008058A0)=0x10` set eder; validator FARKLI bir bayt
`*(0x0080CA8F)` okur — ikisi ilişkili durum baytları ama aynı adres değil; `0x0080CA8F` dökümde yok, canlı
değeri okunamadı.)

### 4.2 Reddin sonucu
- Validator `0` dönerse e00 dağıtıcısı `0x000038D4 cbz r0,#0x38fc` ile hata yoluna girer.
- Dağıtımda eşleşmeyen opcode → **default `0x0000393E`**: `strb.w fp,[sl,#8]` (sl=response ctx `0x00809958`) +
  `bl 0x2e34` (NVMe completion post) = **hata/statü ile geri dön**, handler'a girmeden. [READ]
- Düşük komutlar `0x00–0x0C` için `0x000038EA tbb [pc,r0]` jump table (13 giriş; ör. cmd0→0x399c, cmd2→0x3a02);
  `0x0D–0x0F` ve eşleşmeyenler → `0x393e`.

---

## 5. e02 "komut tablosu" (görev madde 4) — GERÇEĞİ: e02 bir VERİ segmenti

- **e02 packed/şifreli DEĞİL:** entropi **5.425** (e00'un 6.243'ünden düşük), **%41 sıfır**. Önceki analizin
  "yüksek-entropili/packed" notu yanlış; bölge sadece **veri**.
- **Ağırlıklı veri kanıtı:** e02 adresleri (0x00804000–0x00808000) tüm kod segmentlerinden **pool sabiti** olarak
  yükleniyor: e07 474, e00 442, e04 326, e06 135, e03 119, e01 93, e08 79, e09 73 kez. Bunlar **global durum
  değişkenleri** (ör. `0x00804750`, `0x00804878`, `0x008058A0`=mod, `0x008058C4`=durum dizisi tabanı,
  `0x00805888`, `0x0080BA60` civarı) — yani e02 = SRAM/global veri alanı.
- **`0x00806540–0x008066A0` bir dispatch tablosu DEĞİL:** bu aralığa **tek bir pool referansı bile yok**
  (`tk2` taraması: 0 sonuç). Kod bu "tablonun" tabanını hiç yüklemiyor → komut-indeksli bir handler tablosu değil.
- Task'ın işaret ettiği `cmp #0x89 @0x00804776`, `#0x8B @0x0080658A`, `#0x58 @0x0080496A`, `#0x83 @0x00804ACC`
  **linear-disasm artefaktlarıdır**: veri baytları Thumb `cmp Rn,#imm8` (`0x28..0x2F` üst-bayt) olarak çözülüyor
  (ör. `8B 28` → `cmp r0,#0x8b`, `82 2C` → `cmp r4,#0x82`). Kanıt: bu "cmp"lerin ardından **branch yok, arka
  arkaya iki cmp** geliyor (`0x00805BD0 cmp r4,#0x82` hemen ardından `0x00805BD2 cmp r5,#0x42`) — geçerli
  cmp-zinciri değil.
- **Gerçek alt-komut dağıtımı** e02'de değil: 0xC1/0xC2 → `e00:0x000040F0` (vendor engine) →
  `blx veneer 0x147a8` → `e03:0x040C2636` (loader bölgesi olay/komut işleme) ve `e00:0x00004114` (NVMe SQE
  relay; `sb=*(0x00805888+2)` ∈ {0xC2..0xC5} akışı) üzerinden yürüyor.

**Fabrika-format / sistem-alanı yeniden-kurma komutu var mı?** — **HAYIR (vendor yolundan erişilebilir yok).**
- `format/factory/sanitize/purge/EraseAll` string taraması: sadece **e06** (FTL backend) `0x0406B8CD "Faa Format:%d,%d,%d"`
  = iç FTL log'u; vendor komutuyla tetiklenmiyor.
- Gerçek on-NAND FW formatını (LDBK info page + CodeMap + MKSSD kod sayfaları) yazan kod **yalnız FTL/boot
  tarafında** (e06/e07/e09) ve NVMe admin/vendor yolundan **erişilemez** [ANALIZ_FW_FLASH §4]. Yani host
  komutundan "sistem alanını yeniden kur/formatla" köprüsü yok.

---

## 6. Neden ISP kapalı — zincir halinde (headline'ın gerekçesi)

1. **SRAM'e host kodu koyma primitifi yok:** `cmp #0x87` (WriteRam) 0 adet; canlı 0x87 no-op. Başka SRAM-yazan
   alt-komut yok (0x8A NAND'a yazar, 0x86 okur). → Bakım kodunu SRAM'e **koyamıyoruz**.
2. **0x82 host adresine atlamıyor:** worker `0x008038E0` payload okumadan **sabit** `0x040C71E8` ve `0x0000CD36`
   kurup gömülü `0x0000CD36`'ya atlıyor. `0x0000CD36` de `*(0x0080BF88)`'deki (yine sabit) fonksiyonu `bx`'liyor.
   → Kod konsa bile **oraya dallanılmıyor**.
3. **İmza kapısı gereksiz:** yazma yolu hiç olmadığından RSA/imza da yok.

Bu üçü birlikte: "kendi bakım kodunu (GDP.bin) NVMe ile yükleyip çalıştır" yolu ürün FW üzerinden **KAPALI**.

**İkincil bulgu (yanıltmasın diye):** 0x82, host kodu çalıştırmasa da controller'ı **gömülü loader/bakım moduna**
(mod baytı 0x10, `0x0000CD36` durum makinesi, `0x040C62B0/0x040C71E8` resident loader fonksiyonları) geçiriyor.
Yani "GDP'yi yükle" değil ama "**resident** loader'ı ayağa kaldır" mümkün olabilir. Ancak (a) resident loader'ın
tam yeteneği (özellikle flash-yazma) bu dökümden doğrulanamadı, (b) mod-0x10 komut geçidi 0x8A/0x8B'yi (page
write/erase) İÇERMİYOR (sadece ≤0x0C, 0x14, 0x84), (c) task'ın gözlemi 0x84'ün FW'i düşürdüğü ve silme/programın
die seviyesinde FAIL olduğu (ANALIZ_SILME: fiziksel/charge-pump şüphesi) yönünde. Bu yol **kanıtlanmadı** ve
canlı denenmemeli (task sınırı). Somut bir onarım için asıl kök-neden büyük olasılıkla firmware değil fiziksel.

---

## 7. Dürüstlük / bulunamayanlar
- `*(0x0080C094)` slotunun **son scheduler çağrı noktası** temiz eşleşmedi (HW-vektör/indeksli olabilir) —
  **bulamadım**. `*(0x0080BF88)`'in `bx`'lendiği kesin (§1.5).
- 0x0C/0x0D/0x14/0x15 alt-komut **gövdeleri** ürün FW dökümünde temiz izole edilemedi (veri-güdümlü loader
  dağıtımı) — **kısmen bulamadım**; ama SPI/seri-flash hedefi için hiçbir string/register kanıtı yok.
- `*(0x0080CA8F)` (validator mod baytı) dökümde yok; canlı değeri okunmadı (statik sınır).
- `0x040C8000–0x040CC000` fw_canli'de eksik (GDP dispatcher bölgesi) ama ürün FW yolu e00/e01/e03'te tam
  çıkarıldığından sonucu etkilemiyor.

## 8. Bu çalışmada üretilen yeni adresler
- `e00:0x000037F0` NVMe admin dağıtıcı (opcode anahtarı) · `0x00003914` opcode dağıtım · `0x00003A4E`
  0x81/0x82 gövdesi (iki kapı) · `0x00003A86` worker tail-call
- `e01:0x008038E0` **JumpToPRAM worker** (sabit işaretçi kur + `b.w 0xcd36`); yalnız 0x3a86'dan çağrılır
- `e00:0x0000CD36` loader **durum makinesi** (BF88'i `bx`'ler, slot dizisini doldurur); `0x0000CDF8/CE0C` okuma+yürütme
- `e03:0x040C7208` **mod-kapılı komut geçidi** (validator); veneer `0x0001470C`
- `e00:0x000040F0` vendor engine (0xC1/0xC2) → veneer `0x147a8` → `e03:0x040C2636`
- işaretçi slotları: `0x0080BF88` (bx'lenen), `0x0080C094/0x0080C0A8/0x0080C3C0` (durum handler dizisi)
- HW: `0x06301040` çekirdek entry/vektör register'ı · mod baytları `0x008058A0`, `0x0080CA8F`
- veneer tablosu `e00:0x000146EC–0x000147B0` (25 giriş; loader API e03/e08'e köprü)
