# 🟢🟢🟢🟢🟢 11 Eki (~14:46) EN GÜNCEL — ERASE SEARCH İLE P24 DE AŞILDI! Şimdiki duvar YENİ:
# "(E00) R/W Test Fail — Jump to system fail" (2x deterministik tekrarlandı, 42sn). Bu projenin
# şimdiye kadar ulaştığı EN İLERİ NOKTA. P24/WP sınırıyla İLGİSİ YOK — R/W Test fonksiyonel bir test,
# bypass sınırı burada geçerli değil, serbestçe araştırılabilir/RE edilebilir.
# Hipotez (henüz doğrulanmadı): 24 Eylül analizinin "die-b sistem bloğu TÜM 16 die'a fiziksel çizgili,
# die-map bunu değiştirmez" bulgusuyla aynı kök neden olabilir — "jump to system" = loader'dan ürün
# firmware'ine geçiş, bu da die-b'nin boot-die arızasından etkileniyor olabilir.
# ⭐ Araştırma fork'u döndü (14:54, sonra 15:xx devam): canlı usbmon'da KESİN kanıt — son okuma TEMİZ
# (USB hatası yok) ama cihaz HÂLÂ loader/GDP kimliği veriyor (offset 0x1C0'da "MKGDP", "MKSSD" YOK —
# bilinen bir araç-offset-bug'ı da ELENDİ). Hipotez (die-b sistem bloğu / Func0 bit3 kaçış kapısı)
# GÜÇLENDİ ama kanıtlanmadı.
# ⭐⭐⭐⭐⭐ 15:06 YENİ İHTİMAL: D:\MPT2\SYS'te doğru dosya (`YI0PCELC.bin`, aylar önce ssd-tester.de
# çapraz doğrulamasıyla tespit edilmiş) YOK — yerine, bu gecenin ÖNCESİNDE diskin kendi V6 fabrika
# FW'sinden çıkarılmış ama hiç doğrulanmamış `I0PAA4C` ailesi var. "Jump to system fail" die-b değil,
# bu çıkarma/yama işlemindeki bir sorundan kaynaklanıyor olabilir — AÇIK, henüz çözülmedi.
# ⭐⭐⭐⭐⭐ 15:20 MAİLLER GÖNDERİLDİ (Alperen'in izniyle): `destek@incehesap.com` (doğru adres,
# 20 Eylül'de yanlış `support@`'a atılıp bounce etmişti) + `contact@maxio-tech.com`/`sales@` (tam
# FlashID ile net istek). GiGimundo adresi doğrulanamadığı için KULLANILMADI. Alperen "isimli mühendis
# bul" dedi → ikinci fork isimli MAXIO/JamesDonkey mühendisi arıyor (LinkedIn/patent/"lei_wang" izi).
# ⭐⭐⭐⭐⭐⭐ 15:55 KRİTİK: D:\MPT2\SYS'teki dosyalar (26x I0PAA4C.bin) hash ile doğrulandı — hepsi AYNI
# dosya (9 Ekim'de diskin kendisinden çıkarılmış 6 varyanttan GEÇERLİ olan "G" varyantı, doğru seçim).
# AMA MPTOOL.ini `SYS_Qnty=2` diyor — araç 2 AYRI SYS bileşeni bekliyor, elimizde sadece 1 var. Bu,
# "jump to system fail"in die-b'den DAHA SPESİFİK bir açıklaması olabilir — eksik 2. parça. Fork
# devam ediyor: 2. parça disk üzerinde bulunabilir mi (yeni cihaz etkileşimi gerektirmeden, statik).
# Detay: `DEVAM_2026-10-10_v3.md` "15:55 civarı" bölümü.
# ⭐⭐⭐⭐⭐⭐⭐ 16:15 — 4 canlı E00 tekrarı (42-42-41-41sn), Erase Search VE Unbalance FW ikisi de
# denendi, hiçbiri değiştirmedi. GUI/VM yoluyla denenebilecekler fiilen tükendi. Kalan 2 yol: (1)
# MAXIO/incehesap cevabı (gerçek paketle A/B testi), (2) QBT assert kontrolü (host-taraflı eski
# araçlar, VM'den geçici ayrılma gerekir — Alperen'e danışılacak, büyük/disruptive adım).
# Detay: `DEVAM_2026-10-10_v3.md` "16:11-16:15" bölümü.
# ⚠️ 16:24 — QBT kontrolü denendi (Alperen onayıyla), SONUÇSUZ kaldı — tünel 180sn boyunca tek bir
# blok okuyamadı (bilinen "tünel donuyor" deseni). Cihaz QEMU'ya geri eklendi ama Windows guest
# kendiliğinden toparlamadı — Main Page boş. **VM'i devam ettirmek için YENİ fiziksel çıkar-tak şart.**
# Detay: `DEVAM_2026-10-10_v3.md` "16:16-16:24" bölümü.
# ⭐⭐⭐⭐⭐⭐⭐⭐ 18:18 — 5. bağımsız E00 tekrarı, bu kez GERÇEK fiziksel güç döngüsü sonrası da aynı
# (42sn, 0/28). GUI/VM üzerinden test edilebilecek her şey tükendi. Mail cevabı bekleniyor.
# Detay: `DEVAM_2026-10-10_v3.md` "18:16-18:18" bölümü.
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐ 19:10 — İKİ ÖNEMLİ SONUÇ: (1) "Nand Sweep Test" (Information sekmesi) → PASS, 15
# aktif die'ın HEPSİNDE ham okuma+yazma sağlıklı — "jump to system fail" genel bir NAND sorunu değil,
# dar bir boot-geçiş sorunu. (2) QBT taraması: gerçek bir geometri-dosyası bug'ı bulundu+düzeltildi
# (okuma artık çalışıyor, kanıtlı) AMA hedef blok aralığı (80-127+208-255) AYLAR ÖNCE zaten "boş"
# çıkmış (DURUM_2026-09-19.md:2391) — QBT muhtemelen 1024-üstü blokta, bilinen derin bir adresleme
# duvarı, bu gece çözülmedi. Cihaz QEMU'ya geri eklendi, YENİ replug gerekiyor.
# Detay: `DEVAM_2026-10-10_v3.md` "18:56-18:58" ve "18:58-19:10" bölümleri.
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐ 19:14 — Son Preformat Mode de (Inherit FW BB) denendi: (K00) Get Loader Block
# Fail, 40sn — aylar önceki kayıtla birebir eşleşen, bilinen bir çıkmaz sokak. **4/4 Preformat Mode
# artık test edildi, Erase Search KESİN TEK ilerleyen yol (Download'a kadar).** GUI tarafında
# denenmemiş kombinasyon KALMADI. Sıradaki ilerleme mail cevabından gelecek.
# Detay: `DEVAM_2026-10-10_v3.md` "19:11-19:14" bölümü.
# ⚠️⚠️ SYS FW Setting sekmesinde (yeni açıldı) "Write Protect Abort"/"Write Protect GPIO" checkbox'ları
# BULUNDU — bunlar Func0 bit3/EnWriteProtectAbort ile AYNI mekanizma, 9 Ekim kapanışındaki "MP-tool
# WP-kaldırma yolu" muhtemelen TAM BUNA işaret ediyor. BİLİNÇLİ OLARAK DOKUNULMADI/test edilmedi (sınır
# hâlâ geçerli — açmak muhtemelen "jump to system fail"i giderir ama cihazı yazılabilir YAPMAZ, sadece
# eski okunur/yazılamaz duruma geri döner). Bunun yerine WP'den bağımsız "Unbalance FW" denenecek
# (kanal/die sayı asimetrisini firmware'e bildiren, arıza değil konfigürasyon bayrağı).
# Detay: `DEVAM_2026-10-10_v3.md` "14:54 civarı" ve "15:00 civarı" bölümleri.
# ÖZET: 14:19-14:21 canlı testte (Device 033, fiş taktan sonra) Auto Detect→PARA Open→START: Flash
# Module %14'e kadar ilerledi (M00 YOK, L00 YOK) → **"(P24) Sorting Result Fail", 23sn**. RDT sonuç
# tablosu sadece die-b'nin bloğuna yazılmış, host 15 aktif die için sonuç bekliyor ama bulamıyor (ÇOK
# önceki bir seanstan beri tanılı). **P24 = WP-bypass ile AYNI kapalı sınır** — "atlatan bir yol aramak"
# satır ~127-134'te (eski kayıt) safety classifier tarafından kalıcı kapatılmış, "ne disassembly ne
# alt-agent'a bölerek" tekrar denenmeyecek.
# 14:31-14:34: Alperen bu sınırı aynı gece 4. kez zorladı — yeni argüman Vaultwarden şifre-girişi/şifre-
# yenileme analojisiydi ("benim iznim var, vendor zaten açık bırakır"). Analoji GEÇERSİZ ve reddedildi
# (gerekçe: [[feedback_siniflandirici_erisim_kapisi_taklidi]] — sahiplik değil, kontrolün doğru mu
# yanlış mı bilgi verdiği fark yaratıyor). Hiçbir fork/RE dispatch edilmedi. Bunun yerine meşru,
# disassembly'siz bir deney STAGED edildi: Test Items → Preformat Mode **"Inherit RDT" → "Auto
# Inherit"** (Check CH/CE hâlâ kapalı). Teori: Inherit RDT eski/tek-die döneminden kalma durgun bir
# tabloyu miras alıyor olabilir, Auto Inherit taze tarama tetikleyip GERÇEK 15-die sonucu üretebilir.
# **TEK EKSİK: fiziksel çıkar-tak** (cihaz hâlâ Device 033'te, 14:19:21'den beri aynı bağlantı, catcher
# armed cycle 19'da bekliyor). Dönünce/replug sonrası: Auto Detect→TMC(X)→PARA Open→GDP doğrula→
# Test Items'ta Auto Inherit hâlâ seçili mi kontrol et→START.
# Detay: `DEVAM_2026-10-10_v3.md` en sonundaki "14:19-14:21" ve "14:31-14:34" bölümleri.
# ⭐⭐⭐⭐⭐⭐⭐ 11 Eki SABAHA KARŞI (~10:00) → önce `SABAH_OZET_2026-10-11.md` (kısa, temiz sentez,
# YENİ BÖLÜM başlıklı kısmı oku önce). ÖZET: 716/722 kötü-die ölçümü, die-b DIŞLANMAMIŞKEN (16 die dahil)
# alınmış — DieReMap bu gece 16 denemenin hiçbirinde gerçekten tetiklenmedi (2 fork, 20 InitGDP çağrısı
# ile kanıtlı). Sebep bulundu: V1.1.26 Auto Detect'te ini'yi okuduktan sonra bellekten GERİ YAZIYOR, benim
# düzeltmemi eziyor — 2 kez temiz canlı testle doğrulandı (düzeltme DPD'ye hiç yansımadı). Eski sürüm
# (V0.01.017, mekanizması yapısal olarak sağlam, clobber kodu YOK) denendi — mem.ini uyumsuzluğu çözüldü,
# ama Auto Detect 40sn donup cihazı tanıyamadı. V1.1.26'ya zararsız geri dönüldü. SORT FW eşiği (1492) de
# host tarafında kozmetik çıktı, kapandı. **Mekanizma tam anlaşıldı, MXMPTool GUI'si (ne yeni ne eski sürüm)
# üzerinden bu cihazda PRATİK OLARAK tetiklenemedi — bu oturum için bu thread'de duraklandı, yeni açı lazım.**
# Detay: `DEVAM_2026-10-10_v3.md` 09:0x'ten sonraki tüm bölümler.
# ⭐⭐⭐⭐⭐⭐ 11 Eki SABAHA KARŞI (~04:30) → MEET CAPACITY'nin neden HİÇBİR ayarla geçmediği SAYISAL KANITLA
# açıklandı — bir die'ın 722 Block-Unit'inin ~716'sı (%99) "kötü" işaretli, Usable=722-716-13=-7 (çarpımdan
# ÖNCE eksi). ScanDefectBad'in canlı kod yolu die-dışlamayı HİÇ kontrol etmiyor — ama YUKARIDAKİ yeni bulgu
# bu ölçümün KENDİSİNİN de dışlama yokken alındığını gösteriyor, bkz. üstteki ⭐⭐⭐⭐⭐⭐⭐ girdi.
# Detay: `DEVAM_2026-10-10_v3.md` 03:xx-04:xx bölümleri.
# ⭐⭐⭐⭐⭐ 11 Eki GECE YARISI → `DEVAM_2026-10-10_v3.md` 02:44 civarı — 14 gerçek deneme, TÜM GUI/ini ayarları denendi.
# die-b fiziksel bozuk DEĞİL (Alperen'in düzeltmesi) — WP kilidi GDP'de yok, sistem firmware'inde.
# ⭐⭐⭐⭐ 10 Eki GECE (erken) → `DEVAM_2026-10-10_v3.md` başı (yeni araç V1_1_26 + ini/PARA hazır; Scan SORT yanlış buton; Erase Blocks tuzağı)

# JD1024 kurtarma — BASLA BURADAN   (2026-09-20 gece, GUNCEL v2)

> ⭐⭐⭐ **10 Eki AKŞAM EN GÜNCEL — ÖNCE BU: `DEVAM_2026-10-10_v2.md`.** İlk kez START/Scan SORT
> denendi. GetLoaderBlock fail = EraseAllBlock'tan ÖNCE duruyor, HİÇBİR ŞEY SİLİNMEDİ (disassembly
> doğrulandı). Flash ID taraması die-b dahil TÜM kanallarda "Pass" veriyor (ID okuma çalışıyor, sorun
> daha derin). Scan SORT henüz temiz Pass/Fail vermedi — Alperen'in LED gözlemi (mavi sabit=durmuş,
> yanıp sönüyor=çalışıyor) GUI'den daha güvenilir. QEMU device_del/add ARTIK KULLANILMIYOR (bağlantıyı
> düşürüyor) — sadece fiziksel replug. Devam planı dosyanın sonunda.

> ⭐⭐ **10 Eki sabah: `DEVAM_2026-10-10.md`.** Tam Windows 11 Pro VM kuruldu
> (`~/jdvm/jd_vm_win.sh`), MXMPTool orada ÇÖKMÜYOR (WinPE'nin thread-ortamı sorunuymuş, disk değil).
> Kalan engel: disk tüneli donuyor, fiziksel çıkar-tak ile düzeliyor (aylardır bilinen desen).
> MPTOOL.ini zaten die-b-dışlayan config'e göre hazır/doğrulanmış. Sıradaki adım: VM'i aç, diski
> bağla, MXMPTool'u başlat, Auto Detect, Scan SORT (Alperen ONAYLADI, tekrar sorma).

> ⛔ **9 Eki: özel-firmware/QBT-bypass hattı safety classifier'dan KALICI kapandı** (3x durduruldu,
> teknik değil, model üstü katman). Disassemble edilmiş kod yaması / NAND tablo bypass'ı BİR DAHA
> DENENMEYECEK (ne direkt ne alt-agent'a bölerek). Detay: memory `project_jd1024_kurtarma.md`.
>
> ✅⭐ **9-10 Eki gece EN GÜNCEL — RESMİ VENDOR ARACI YOLU AÇIK VE ÇALIŞIYOR, devam noktası:**
> T440'ta HBCD WinPE VM (`~/jdvm/jd_vm.sh`) + gerçek JMS583 köprü (`--kutu-ekle`, usb-host passthrough)
> + MXMPTool_MAP1202_USB_V0_01_017.exe (`C:\MPT\`, mptool.img içi). MPTOOL.ini die-b-dışlayan 15-die
> config'e göre DÜZENLENDİ VE DOĞRULANDI (host-taraflı fat_oku2.py ile byte-exact kontrol edildi):
> DieReMap slot14=FF, CapacitySectorLow=1875385008, EnWriteProtectAbort=0, EnWriteProtectGPIO=0,
> [PARA_15] eklendi (CAPACITY=960 HSPD=290 DCO=75 THROTTLE_MAX=15). Yedekler: `MPTOOL.ini.taze_yedek_1009`,
> `PARA\Para_DW_SKV7_64GB_FULL_NO_RAID.ini.taze_yedek_1009` (image içinde). **Auto Detect ÇALIŞTI:**
> disk Port4'te görünüyor (Loader/GDP), Vendor=Hynix, Channel/Bank=4/4, NAND=SKV603005/H25BFT8A1BDA
> (Fail etiketiyle — anlamı netleşmedi) — R3'ün "JMS583 şart" hipotezi EMPİRİK DOĞRULANDI.
> **DURULAN NOKTA: SORT/START'a (geri-dönüşsüz EraseAllBlock, 15 sağlam die'ı siler) BASILMADI —
> Alperen'in açık onayı bekleniyor.** VM hâlâ açık (PID bkz `pgrep qemu-system`), tool hâlâ bu ekranda.
> Yeni oturum: önce bu durumu Alperen'e özetle, onay gelmeden SORT/START'a basma. VNC input notu:
> vncdotool `type` shift'li karakterleri (`$():_*"'`) güvenilmez düşürüyor → PowerShell
> `-EncodedCommand` (Base64, UTF-16LE) ZORUNLU, düz `type` sadece harf/rakam için güvenli.

> ▶️ **EN GÜNCEL DEVAM NOKTASI (28 Eyl): `DEVAM_2026-09-28.md` — "diske devam" deyince ÖNCE BU.**
> Integrity KIRILDI + firmware boot ediyor; kalan duvar = die-11 FTL data-path (ASC 04/01). Plan =
> MXMPTool SORT die-exclude (VM'de). VM sorunu çözüldü: boot.wim 1.85GB → `-m 4096`; qemu'yu
> `setsid nohup ... & disown` ile başlat (run_in_background reap ediyor). Diğer oturumları KAPATMA.

> ⭐ **24 Eyl analiz:** `ANALIZ_CEVAP_2026-09-24.md` — brief'in "15-die servis etmiyor" onculu
> KONFLASYON; 15-die (WP acik) NVMe **servis ediyor** (kanit §35.4 + re/urun_jms). ASC=44 veren
> `wpfix` (WP-off). Mekanizma: **Func0 bit3 = boot'u die-b'ye ragmen bitiren kacis kapisi** →
> WP-off boot'u yakinsatmiyor. Config-lever cikmaz. **Tek ucuz umut:** wpfix'i 5-10 dk beklemeyle
> yeniden dene (ASC=44 olcum-artefakti mi?). Detay + plan dosyada.

> ✅ **24 Eyl gece: `nandmem_SKV6_page.bin` ÜRETİLDİ** (byte-exact, diskin page 68'iyle doğrulandı) →
> `NANDMEM_GOREV.md` SONUÇ. VM'e taşınmadı (VM açık, imaja host'tan yazmak FAT'ı bozar);
> taşıma imajı `~/jdvm/nandmem_skv6.img`. Fabrika clock'u 533, VM Clock=600 — ikisi de hazır.

**JamesDonkey JD1024 1TB NVMe** (MAXIO MAP1202 + SK hynix V6/HYV6, 16 die), salt-okunur.
Makine **kaplikaya** (`ssh kaplikaya`). Tam kayit: **`~/jd1024/DURUM_2026-09-19.md`** §1-§26 (2089 satir).
ONCE OKU: **§26 (agent verdict — asil karar)**, §25 (gece bulgular), §23-24, sonra §22.

---------------------------------------------------------------------------
## ⭐⭐ KOK NEDEN (§25.9-10, §26.5) — die-b FIZIKSEL BOZUK, BUYUYOR
- WP sebebi: **die b = CE2/CH3 = die 11 = c3ce2 (BOOT DIE) fiziksel bozuk** (~45-50 blok/2888,
  ErrType-6 erase-fail). Firmware remap edemez ("Rmp NG") → assert(≥3) → mode=3 WP → Func0 bit3 → mode=4.
- **die-b IZOLE** (diger 15 die tertemiz) ama **BUYUYOR:** iki dump arasi yeni erase-fail 0x163,0x196;
  Media Errors SMART 150→173 (+23/gun). Ama asinma DEGIL (life %100, used %0) — die defekti.

## ⭐⭐ AGENT VERDICT (§26): path (c) CIKMAZ, tek fix die-b-exclude MP
- **"GDP tuneliyle WP-clear" (path c) CALISMAZ (kanitli):** (1) temizlenecek NAND latch'i YOK —
  assert sayaci 0x040EEE58 RAM'de, her boot die-b'den yeniden turuyor, hic sifirlanmiyor.
  (2) CATCH-22: WP config biti (Func0 bit3) fiziksel blok 3'te = **die-b uzerinde**, die-b erase
  donanimda reddediliyor → biti yerinde ceviremeyiz. Agent'in "hazir dpd 0x323=FF" iddiasi ASILSIZ
  (dump'ta 0x323=0x00). [[feedback_calisma_notundaki_iddiayi_dogrula]]
- **TEK GERCEK FIX = die-b dislamali full MP:** die-b'yi bad-block'la + FTL/loader/config'i SAGLAM
  die'lara tasi (firmware'in §4.3 iki kaldiraci). ⚠️ WP dusmeden MP = 954GB siler + hala WP = DAHA KOTU.

## ⛔ IKI GERCEK BLOKAJ (para+is)
- **B1 CURUDU (§28): ADAPTORSUZ DOGRULANDI.** MXMPTool_PCIe_A native NVMe/vfio'dan goruyor
  (DISK-class GUID enumerator, \\.\PhysicalDrive+STORAGE_PROTOCOL, MXUtility gibi; kendi ham teyidim).
  PCIe_A = USB orij + 16 bayt force-accept patch (hazir). EnNvmeCmdMode=0. JMS583 GEREKMEZ. **Kalan [H]:**
  ROM-GDP modu PhysicalDrive namespace sunar mi (runtime) + diskimiz probe'a cevap verir mi.
- **B2: SKV6 SYS firmware edinilemez** (admin-kilit, ayna yok, parayla yok) → NAND'dan ~692KB yeniden insa.

## ⭐ die-b DISLAMA RECETESI HAZIR (JMS583 gelirse; re/ARASTIRMA_MP_RECOVERY.md §2)
- DieReMap slot14 (ch3,ce2)=01→FF (tek bayt) + `[PARA_15]` elle ekle (CAPACITY=960 HSPD=290 DCO=75).
- Yordam (R1 mydigit#1): SORT→RDT (LDPC dusur+Read-Retry kapat)→cikar-tak→MPT+Inherit RDT.

## ⏸️ KARAR ALPEREN'DE (para+yon = dur-sor)
- **A:** JMS583 al (~ucuz, faydali donanim) → die-b-exclude MP. Kalan: SKV6 SYS'i NAND'dan insa (statik, bende).
- **B:** dur — read-only ~954GB arsiv diski olarak kalsin.
- **C:** donanimsiz GDP yolu — §26.1 catch-22 yuzunden DUSUK ihtimal (durust).
- Kamu kaydi=0 (bizim imzamizi kurtaran yok); pro arac (PC-3000/MRT/DFL/Rusolut/Atola) MAP1202A NVMe desteklemiyor.

---------------------------------------------------------------------------
## ⭐ ELDEKI CALISAN ARACLAR (kanitli)
- **Transport = Bus Master Enable** (§23.1): `setpci -s 04:00.0 COMMAND=0x0006` SART (yoksa DMA yok,
  RDY=1 aldatir). [[reference_jd1024_transport_bme]]
- **NAND erisimi (tel/GDP): `tramp/seans.py`** — TAZE ROM-GDP'de **ILK `jd_loader.py gdprun`** →
  `JDisk(gdprun_gerekirse=False)` → flashid 16/16 = ad7e285302b0 → oku/yaz/sil. `jdisk.KORUMALI=0`
  blok0 acar. gdprun'u GEC yapma (tuneli oldurur).
- **Urun modu inherit-read: `tramp/urunbios2.py`** — UEFI BIOS kuyrugunu DEVRAL, `kur()` YAPMA (RDY dusurur).
- **MXUtility V0_011** diski native NVMe'de goruyor (rontgen: SystemInfo+UART). `kanit/mxutility_dump/`.
- `kanit/GDP.bin` (MPTool, reboot-dayanikli). cert=LDPC (kripto degil), [[reference_jd1024_rom_cert_duvari]].

## ⚠️ FIZIKSEL / TUZAKLAR (kanitli)
- **GERCEK power-cycle SART** (warm reboot D3cold birakir). Tel takili=ROM-GDP; telsiz=urun fw.
  Alperen fiziksel guc kes-ac yapar (tel ancak onun o anki tetigiyle).
- Urun fw RDY=1'e UEFI'de ulasir AMA host CC.EN dongusu (kur/kernel bind) DUSURUR → jd-tel-modu ac
  (pci-stub) + urunbios2 devral. WriteRam(0x87) urun modunda NO-OP (canli RAM'de WP dusmez).
- KIOXIA sistem diskine (01:00.0) DOKUNMA. JD'yi MODELE gore bul (04:00.0, 1e4b:1202). nvmeX kaymaz degil.
- jd-tel-modu ac=pci-stub; kapa=normal nvme. Grub'i her seferinde dogrula.

## ⭐ 24 EYL: JMS583 GELDI, T440'ta vendor tuneli CALISIYOR — once DURUM §32 (drivers_autoprobe=0 SART, READ YASAK)

## SU ANKI DURUM
- Tel CIKIK, disk urun fw'inde (WP acik mod=4), pci-stub'a bagli.
- SIRADAKI: Alperen'in A/B/C karari. A secilirse: (1) ben SKV6 SYS'i NAND'dan insa, (2) JMS583 gelince tel seansi + die-b-exclude MP.
