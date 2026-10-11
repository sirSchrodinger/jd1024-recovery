# DIŞ ARAŞTIRMA — MAXIO MAP1202 / JD1024 (20 Eylül 2026)

Kapsam: A1..A6. Sadece okuma/indirme yapıldı; hiçbir hesap açılmadı, hiçbir foruma
yazılmadı, kimseye mesaj gönderilmedi.

**Erişim notu (önemli, KAYNAKLAR.md'yi günceller):** `usbdev.ru` artık Frankfurt
Oracle VM'inden de **HTTP 403** veriyor (daha önce 200'dü) — tarayıcı UA, Accept
başlıkları, çerez ve referer denendi, hepsi 403. Ama **okuma** için çalışan bir yol
bulundu: Google Translate proxy'si
`https://www-usbdev-ru.translate.goog/<yol>?_x_tr_sl=ru&_x_tr_tl=en&_x_tr_hl=en`
→ HTTP 200, tam sayfa. **İndirme bu yoldan çalışmıyor** (`?wpfb_dl=` ana sayfaya
redirect ediyor). allorigins / codetabs proxy'leri de indirme için çalışmadı.

---

## A1 — MAP1202 MPTool ile mass production nasıl yapılıyor (gerçek prosedür)

### A1.1 Fiziksel bağlantı: PCIe DEĞİL, USB köprü — ve köprü markası kritik

Bulunan **bütün** gerçek kullanım anlatıları (Çin, Rusya) MPTool'u **USB-NVMe köprü
üzerinden** kullanıyor. Doğrudan M.2/PCIe slotunda başarılı bir MPTool açılışı
anlatan tek bir kayıt bulunamadı.

- 量产帮/lcb.club, *"联芸MAP1202、MAP1602量产开卡建议用JMicron的转接板"*
  (http://lcb.club/post/59.html, erişim 20 Eyl 2026):
  > "联芸MAP1202/MAP1602量产开卡，建议用JMicron的转接板，例如：JMS583。"
- Aynı sitenin uzun rehberi (http://lcb.club/post/277.html):
  > "使用JMS583主控硬盘盒（**RTL9210系列不兼容**）"
  ve *"尽量不要使用机箱前置USB接口开卡，把开卡板直接插到电脑机箱后面的USB接口开卡更稳定"*
  (kasa ön panel USB'si kullanma, arka porta tak).
- pitfalls.ru, Netac NV3000 (MAP1202) kurtarma yazısı, **02.07.2026**
  (https://pitfalls.ru/восстанавливаем-прошивку-ssd-nvme-диска-netac-nv3000-250gb/):
  yazar önce Ugreen NVMe-USB kutusuyla **başaramadı**, JMS583 tabanlı Çin kutusuyla
  başardı. ROM kısa devredeyken cihaz Aygıt Yöneticisi'nde
  **`Generic_Loader_NVMe_Devi SCSI Disk Device`** olarak göründü.
- usbdev forum, `topic=11517` ("Помогите найти программу для прошивки MAP1202"):
  kullanıcı RELETECH P600 2TB'ı **anakart NVMe slotunda, PCIE-NVMe adaptöründe ve
  RTL9210B köprüsünde** denedi — hiçbirinde görünmedi:
  > "Пробовали в слоте NVMe на материнской плате, через переходник USB-NVMe (чип
  > RTL9210B), через переходник PCIE-NVMe. Не видятся."
  Sonraki mesajı: *"Пришел переходник USB-NVMe На JMS583. Удалось увидеть этот диск
  в программаторе Maxio MAP1202 MP/Sorting Tool C.0.01.017."*
  → **JMS583 gelince aynı disk aynı araçta göründü.**

Pratik sonuç: bizdeki `MXMPTool_MAP1202_PCIe_A.exe` / `_PCIe_B.exe` ikilileri
mevcut ama **topluluk kanıtı yok**; çalışan tek kanıtlanmış yol `_USB_*.exe` +
JMS583. Bizim vfio-pci passthrough kurulumumuz bu yüzden yanlış eksende olabilir.

### A1.2 ROM kısa devre (short pin) — zamanlama kuralı

Bu adım **atlanabilir değil**; aracın diski görmesinin şartı.

lcb.club post/277 ve /55, juejin.cn/post/7512339903402426394 (yazar
`用户754523903096`, **2025-06-06**) aynı cümleyi kullanıyor:
> "用金属镊子短接固态硬盘板子上的两个ROM点（不确定哪个是ROM点的可以自己多次短接测试），
> **保持短接**，然后把固态硬盘用硬盘盒连接电脑，软件即识别固态，**拿下镊子断开短接**。"

Ve kritik uyarı (lcb.club/post/277, madde 5):
> "短接ROM点后需保持连接状态直至软件识别，软件识别后断开短接。
> **过早断开会导致软件不识别固态硬盘，而不断开则会导致量产失败。**"
> (Çok erken bırakırsan araç diski görmez; hiç bırakmazsan **量产失败** = MP fail.)

Bu MAXIO'ya özgü: Rossmann'ın ROM-mode sayfası
(https://rossmanngroup.com/services/ssd-data-recovery/firmware-panics-rom-mode)
SM2258 için tersini söylüyor —
> "The SM2258 needs the ROM pin held to ground throughout initialization, not just
> at power-on."
Yani aile başına davranış farklı; MAXIO'da **tanındıktan sonra bırak**.

ROM noktasının ne olduğu (CSDN, "固态硬盘：量产、开卡、ROM短接是指什么？",
https://blog.csdn.net/ot512csdn/article/details/142320484):
> "ROM短接是将ROM数据脚从高电平设置为低电平…将此脚与地短接后，电平变低，清除了只读模式，可以写入。"

### A1.3 Araçtaki tıklama sırası

lcb.club/post/277 + juejin + lcb.club/post/210 birleşimi:

1. MPTool ana programını **önce aç** (disk takılmadan).
2. ROM kısa devre + kutuyu tak → araç diski görür → cımbızı çek.
3. **Main Page → `Auto Detect`** → açılan pencereden hedef diski seç.
4. **Device Setting**: model, seri no, üretici, kapasite.
5. **Test Items**:
   - `Tool Type` = **`MPT`** (üretim) veya **`SORT`** (RDT servis firmware'i yazar).
   - `Preformat Mode` = **`Inherit FW BB`** / **`Auto Inherit`** / **`Erase Search`** —
     *"一个不行就换另一个多试试"* (biri olmazsa diğerini dene).
6. **`START`** → yeşil `Pass` barı = başarı.
7. Çıkar-tak, Disk Yönetimi'nde bölümle.

dom0ng/map1202 README (https://github.com/dom0ng/map1202) UI renk kodunu veriyor:
doğru algılanan cihaz satırı **sarı**, başarılı işlem sonrası **yeşil** olur.

**RDT akışı** (lcb.club/post/210, MAS0902 için ama aynı araç ailesi):
> "先讲RDT，选择SORT…设置完了点START，写入RDT固件之后，拔下来插到充电头上跑RDT，跑完了电流会变小。
> 开卡部分，选择MPT，一般来说Preformat Mode选自动就行，**如果没跑RDT可能要选擦除或者继承使用坏块**"

Yani SORT ile RDT firmware'i yazılır, disk **şarj adaptörüne** takılıp kendi başına
tarama yapar (akım düşünce biter), sonra MPT çalıştırılır.

### A1.4 ★ MPTOOL.ini gizli anahtarları (bizde denenmemiş)

Bu, A1'in en somut kazancı. 量产部落'nun yayınladığı, lcb.club'da aynen mirror'lanan
üç ayrı ayar:

| Anahtar | Bölüm | Etki | Kaynak |
|---|---|---|---|
| `ToolModeSetting=0` | `[Setting]` | MAP1202/MAP1602'de **tüm `Tool Type` modları açılır** (QC, MDI, Updater…) | http://lcb.club/post/13.html |
| `EnToolType=0xFF` | `[Setting]` | MAS1102'de "Device Set/Test" sekmesinde **tüm `Tool` fonksiyonları açılır** | http://lcb.club/post/47.html |
| `EnSMARTCheck=1` + `EnClearSMART=1` | `[TestItems]` | Arayüze **`Clear/Set SMART`** kutusu gelir (SMART sıfırlama) | http://lcb.club/post/14.html |

post/13 tam metni:
> "2、用记事本或者Notepad++打开"MPTOOL.ini"文件；3、在"[Setting]"下添加
> "ToolModeSetting=0"，并保存设置；4、打开量产工具"Test Items"选项卡，查看左上角
> "Tool Type"区域，此时已开启全部"Tool Type"功能。"

post/14 tam metni:
> "在"[TestItems]"下，将"EnSMARTCheck"和"EnClearSMART"的值改为1。如果没有…则直接添加两行…
> 4、打开量产工具主程序，选择"Test Items"选项卡，在"Tool Type"下选择"MPT"，
> 发现左侧界面已经显示"Clear/Set SMART"复选框"

**Ayrıca bulunan ama içeriğine ulaşılamayan dördüncü ayar:** 量产部落'nun ek
listesinde (aşağıda A3'teki xlsx) şu başlıklı bir "量产技巧分享" konusu var:
> `联芸MAP1202、MAP1602主控量产工具开启"SYS FW Setting"和"SORT FW Setting"工程界面`
> (ekler: `Maxio-1.png` aid=11926, `Maxio-2.png` aid=11927, yükleme 2020-09-25)

Yani MPTool'da **SYS firmware'ini ve SORT firmware'ini elle seçtiren bir mühendislik
paneli var** ve bir MPTOOL.ini anahtarıyla açılıyor. Bu bizim durumumuz için en
alakalı ayar; makalenin gövdesi liangchanba'da login arkasında, lcb.club'a
mirror'lanmamış. **Kendi MPTOOL.ini'mizde `SysFwSetting` / `SortFwSetting` /
`EnFwSetting` benzeri anahtarları aramak gerek** (aşağıda aksiyon listesinde).

### A1.5 MPTool ayar şifresi

liangchanba MAP1202 indeks konusu (https://club.liangchanba.com/thread-1761-1-1.html,
erişim 20 Eyl 2026) sayfanın başında açıkça yazıyor:
> "**设置密码：maxio**"

MPTool/Utility bir ayar (Parameter/Edit) şifresi sorarsa cevap `maxio`.
(Karşılaştırma: flashinfo.top'un YS9205 sayfası aynı yerde "boş bırak veya 123456"
diyor — üretici başına değişiyor.)

### A1.6 "FAIL" mutlaka başarısızlık demek değil

usbdev.ru MAS0902 sayfasındaki Rusça yorum, **4 Haziran 2023**:
> "Замкнуть перемычку ROM / Вставить SSD… Start \ **по окончании получил ошибку
> Fail**. Снял перемычку. **SSD заработал**, Заполнил данными больше половины,
> полет нормальный!"

Aynı desen usbdev topic 12338'de de var: JenDos_50 (21 Şub 2026) N38B paketini
N38A'ya yeniden adlandırıp kullandı, ilk deneme 390 GB'da düştü, `Inherit RDT + Sort`
ile tekrar denedi, 450 GB'da takıldı, 400 GB'a sabitleyip çalışır hale getirdi.

---

## A2 — MAXIO'da write protect / read-only kilidini kaldırma

### A2.1 Açık gerçek: MAXIO'ya özgü yayınlanmış bir "WP kaldır" yordamı YOK

`EnWriteProtectAbort`, `WriteProtectAbort`, `BWP`, "SSD protect mode" terimleri için
yapılan aramalar **hiçbir MAXIO kaynağında karşılık vermiyor**. Bu isimler bizim
firmware disassembly'mizden geliyor; internette indekslenmiş değiller. Aynı şekilde
`mod=4` diye bir kavramı anlatan tek bir MAXIO kaynağı bulunamadı.

Genel NVMe seviyesinde durum (DiskTuna, **20 Haziran 2023**,
https://www.disktuna.com/a-write-protected-ssd-nvme-read-only/):
> "If set to '1', then the media has been placed in read only mode." (Critical
> Warning **bit 3**)
> "As far as I know **the only way to cancel this firmware decision are vendor
> specific commands**."

### A2.2 Kanıtlanmış tek pratik çıkış yolu: ROM mode + MPTool ile yeniden initialize

Bulunan bütün somut vakalar aynı: **ani güç kesintisi → firmware/FTL bozuldu →
disk tanınmıyor veya kapasite yanlış → ROM short + MPTool ile 开卡 → disk geri
çalışıyor, veri gidiyor.**

- lcb.club/post/55 (ve aynı metnin juejin mirror'ı, 2025-06-06):
  > "最近手里有个MAP1202主控的移动固态硬盘损坏了，**估计是突然断电导致固件掉了**，
  > 没办法，只能量产开卡了。" → sonrasında adım adım başarı.
- lcb.club/post/40: aynı senaryo MAP1602'de, "电脑突然断电" → 开卡 ile düzeltildi.
- usbdev topic 12241 (kullanıcı, 20 Eki 2024):
  > "у меня с SSD прошивка слетела **после отключения питания**. До этого прекрасно
  > работал."
- CSDN genel açıklama (https://blog.csdn.net/qq_26230027/article/details/140507185):
  > "异常掉电会导致映射表来不及更新和保存，导致映射表丢失…一般返厂后是通过重新开卡量产的方式进行维修。"

**Oran/koşul sorusu:** bu tür bir "başarı oranı" istatistiği hiçbir yerde
yayınlanmamış. Elimizdeki en yakın sayısal veri profesyonel taraftan:
hddguru forum, thread "Maxio SSDs now recoverable" (kullanıcı `northwind`,
**30 Mayıs 2025**, https://forum.hddguru.com/viewtopic.php?f=13&t=45359):
> "We're happy to announce that we can now support Maxio SSDs (both 0902 and 1102)."
> "It is still under development, but we have a **70% success rate** so far."
> — ve kritik sınır: çözüm **panic/safe mode'a düşmüş** sürücülerde çalışmıyor,
> sadece BSY durumlarında çalışıyor. MAP1202A (NVMe) desteklenmiyor.

Yani: SATA MAXIO'da bile %70, ve "panic mode"da çalışmıyor. Bizim disk
assert+mod=4 ile tam da o kategoride.

### A2.3 Neden MPTool "WP bayrağını temizlemez" ama işe yarayabilir

MPTool write-protect bayrağını *okumaz/temizlemez*; bayrağı taşıyan yapıyı
(FTL/config/SYS firmware) **baştan yazar**. Bu yüzden ROM short şart: ROM mode'da
NAND'daki bozuk firmware **hiç boot etmez**, dolayısıyla `mod=4` mantığı hiç
çalışmaz. Rossmann'ın tanımı (aynı ROM-mode sayfası):
> "SSD ROM mode is the controller's fallback boot state when its on-NAND firmware is
> unreadable." … ROM/safe mode "allows technicians to inject a volatile microcode
> loader (LDR) into the controller's volatile memory through vendor-specific commands."

### A2.4 MAXIO vendor komut kanalı — yayınlanmış dokümantasyon var

`pseudolabel/ssd-flash-id` (MIT, son commit **2026-02-04**,
https://github.com/pseudolabel/ssd-flash-id) `src/controllers/maxio.rs` içinde
protokol açık:

```
opcode 0xC1 = vendor write/arm   (payload header sabit: FF E5 <subcmd> <channel> <ce>)
opcode 0xC2 = vendor read
cdw12       = 0x1234 << 8 | subcmd
bilinen subcmd: 0xFF (arm), 0x86 (bulk info, 4096 B), 0x36 (flash id, 512 B)
```

Bu bizim bulduğumuz `0x00AE34FF / 0x001234FF / 0x00123486` magic'leriyle birebir
tutuyor ve **subcommand uzayının 1 bayt olduğunu** gösteriyor. Yayınlanmış bir
"write protect clear" subcommand'ı yok — ama kanal adreslenebilir ve 256 değer
sonlu.

Önemli negatif (usbdev `maxio_nvme_fid` sayfası, arşiv 2026-02-04):
> "Проверена работоспособность на MAP1002, MAP1202, MAP1602. **Не работает в rom mode.**"
→ vendor kanalı ürün firmware'i koşarken açık, **ROM mode'da kapalı**.
Ama GDP mode'da kısmen çalışıyor: `v0.38` sürüm notu "detect map1202/gdp mode",
"read fid/pp in gdp mode for map1202".

---

## A3 — Daha yeni MPT_Cougar kiti var mı? (ve HYV6 paketi gerçekten var mı?)

### A3.1 ★ KESİN CEVAP: `MAP1202_HYV6_64GBDIE-C.01.018-SN9466.rar` GERÇEKTEN VAR

Şimdiye kadar bu dosya adı bizde sadece bir çıkarımdı. Artık **birincil kanıt** var.

`file.diyflash.top` (闪存量产资料共享站, kayıtsız/ücretsiz dosya paylaşım sitesi)
üzerinde şu dosya bulundu ve indirildi:

> `(量产部落所有附件一览表爬虫破解版)lcb_list_20240915_guide.xlsx`
> = 量产部落'nun **tüm eklerinin crawler ile çıkarılmış tam listesi**, 15 Eylül 2024

14.429 satır, sütunlar: `Aid | Position | Title | Size | Download Count | Permission | Upload Time`.
İlgili satır **aynen**:

```
7498 | 量产部落 > 联芸(Maxio) > Maxio MAP1202 MP/Sorting Tool
     | MAP1202_HYV6_64GBDIE-C.01.018-SN9466.rar
     | 资料大小: 2.64 MB | 下载次数: 131
     | 下载权限:苦逼管理或更高级别 | 上传时间: 2022-12-06
```

Yorumu:
- **aid = 7498**, boyut **2,64 MB**, **131 kez indirilmiş**, yükleme **6 Ara 2022**.
- İzin: `苦逼管理或更高级别` = **"yönetici veya üstü"**. Para/üyelikle alınamıyor.
- Bu yüzden sitenin herkese açık MAP1202 indeksinde (thread-1761) **hiç görünmüyor**:
  o sayfadaki navigasyon sadece HYV7, HYV8, B37R, B47R/B47T, WD_BICS5, YMTC X1-9050,
  YMTC X2-9060, N38A, N38B, N4PA kategorilerini listeliyor — **HYV6 kategorisi yok**.

Yani "halka açık katalogda SKV6 yok" tespiti doğru, ama nedeni "hiç üretilmedi"
değil: **paket var, admin kilidi arkasında.**

### A3.2 Bizde olmayan, gerçekten daha yeni MAP1202 kitleri

Aynı xlsx + thread-1761 canlı sayfası birleşiminden. Bizim kit `C_0_1_017`
(20220527). Bundan **yeni** olanlar:

| Paket | Sürüm | Boyut | İzin (2024 / 2026) | aid |
|---|---|---|---|---|
| `MAP1202_HYV6_64GBDIE-C.01.018-SN9466.rar` | **C.01.018** | 2.64 MB | admin / listelenmiyor | 7498 |
| `MAP1202_WD_BICS5_64GBDie-C.0.01.018-SN9946-H221112a.rar` | **C.0.01.018** | — | admin | — |
| `MAP1202-Hynix_V7-0x39-V0.01.020-128GB-1TB-SN9286-H220719b.rar` | **V0.01.020** | 5.48 MB | 围观游客(2024) / 一星+1金币(2026) | 15746 |
| `MAP1202-SDBICS5-128GBDie-V0.01.021-512GB-2TB-SN10287-H221205a.rar` | **V0.01.021** | 3.55 MB | admin | 13826 |
| `MPT_MAP1202_C2-C-N38A-D3.1-V0.01.00-C.1.1.09_SN10526_20230407.rar` | C.1.1.09 | — | — | — |
| `MAP1202_YMTC_X2-9060_MPT_C2.1.29-SN11795/SN14824` | **C2.1.29** | 3.24 MB | 注册会员+1金币 | — |
| `MAP1202-HynixV8-C1.1.26_SN26637_20241204.rar` | C1.1.26 | 3.47 MB | 二星+1金币 | 3981 |

**En kritik olan `V0.01.020 HYV7` (aid 15746)**: bizim diskle *yapısal ikiz* olan
HYV7 ailesinin **017'den 3 sürüm daha yenisi**, aynı SN9286, 5.48 MB (bizimkinin
3.23 MB'ına karşı — yani **içinde daha fazla dosya var**). 2024 taramasında izin
"围观游客" (misafir) yazıyordu, 2026'da "一星会员 + 1金币"a çekilmiş; indirme sayısı
2 → 121 olmuş.

### A3.3 İndirme neden yapılamadı

`club.liangchanba.com` misafir indirmelerini **tamamen** engelliyor. Test edildi:
her ek isteği `source/plugin/xinshu_denydown/static/deny.rar` adlı 467 baytlık bir
stub'a 302 yapıyor (içinde tek bir Çince .txt). Ücretsiz görünen ekler dahil.
Sayısal `aid` ile doğrudan istek 3408 baytlık login HTML'i döndürüyor.
Kayıt açmak görev kuralı gereği yapılmadı.

Aranan iki dosya için bulunabilen **hiçbir ayna yok**: usbdev (19 MAP1202 paketi),
flashinfo.top (1666 paketlik tam katalog tarandı), file.diyflash.top (43 dosya),
inhdd.com (paywall), ssdtool.cc (aşağıya bak) — hiçbirinde `HYV6` ya da
`C.01.018` MAP1202 paketi yok.

### A3.4 Kapanan kapılar

- **ssdtool.cc** — usbdev topic 10671'de (1 Tem 2023) doğrudan indirme linkleri
  verilmişti (`https://www.ssdtool.cc/wp-content/uploads/1691028982-MAP1202_HYV7_...rar`).
  Site bugün "SSDTool 固件中心" adıyla yeniden yazılmış bir SPA ve
  `GET https://www.ssdtool.cc/api/stats` → `{"firmware":0,"downloads":0,"users":4}`
  yani **katalog tamamen boş**. Eski wp-content yolları da ölü.
  *(Yan not, vlo, 4 Nis 2024: o eski ssdtool.cc rar'larının başında ~100 bayt çöp
  vardı — "там в начале архивов ~ сотня байт какого-то мусора"; WinHex ile kırpınca
  açılıyorlardı. Aynı tuzak başka aynalarda da çıkabilir.)*
- **flashinfo.top** — 1666 kayıtlık MPTool kataloğu tarandı. MAP1202 tarafında bizde
  olmayan bir NAND ailesi yok. İndirme **VIP üyelik** arkasında
  (`downloadFlag:false`, "开通会员" diyaloğu).

### A3.5 ★ flashinfo.top'ta tam bizim flash ID'mizi taşıyan paket (farklı controller)

> `YS9205_16.806_2XB4827E_HYV6_**AD7E285302B0**.7z` — 7.14 MB, 2026-08-06
> https://flashinfo.top/MPTool/Detail/1712 — vendor: 得一微(YEESTOR)

Dosya adındaki `AD7E285302B0` bizim flash ID'mizin (`AD 7E 28 53 02 B0`) birebir
aynısı. Kontrolcü farklı (YEESTOR YS9205), ama bu, o die'ın NAND parametrelerinin
yayınlanmış olduğunu gösterir. Kardeşleri: `YS9205_17.639_2XB5821D_HYV6_2Lun_AD7E295302B0.7z`
(2-Lun), `YS9205_17.305_2XB4A15E_HYV5+HYV6+HYV7+HYV8.7z`.
**VIP arkasında, indirilemedi.**

### A3.6 SKV6 mikrokodu zaten elimizde (teyit)

KAYNAKLAR.md "tekrar etmeyin" diyordu; teyit ediyorum ve bir ayrıntı ekliyorum:
**her MAP1202 kitinin `DAT/ucode.bin`'i SKV6 taşıyor**, 8 hız kademesiyle:

```
SKV6_001_200 / _333 / _400 / _533 / _667 / _800 / _1066 / _1200
EEUUAA_MAP1202/DAT/ucode.bin (1.436.016 B) içinde 0xB0000..0xCFFFF, her kayıt 0x4000
```

`MPT/SORT/ucode.bin` (N38B 4.176.680 B, N4PA 4.797.560 B) de aynı SKV6 setini
içeriyor. Kayıt formatı: `<NAND>_<001>_<hız>` + 0x00 dolgulu başlık.
Diskin UART logunda MAXIO'nun kendi `DDR:1200` satırı görüldüğü için (usbdev
topic 12338) ilgili kayıt büyük ihtimalle **`SKV6_001_1200`**.

**🔴 DÜZELTME — mevcut çıkarma eksik çalışmış.** `kanit/fw_hunt3/skv6_from_ucode/`
altındaki `…BLOB_A_ONLY.bin` dosyaları **2.160 bayt**; gerçek kayıt **16.384 bayt**.
Yani repodaki SKV6 çıkarımı kırık. Tam 16 KB'lık 8 blok bu turda yeniden çıkarıldı:
`araclar_indirilen/yeni_2026-09-20/a4_skv6_ucode_from_github/`.
(GitHub'dan inen `a4f_github_EEUUAA_DAT_ucode.bin`, repodaki
`MAP1202_YMTC_JGS_SN6760/MPT/DAT/ucode.bin` ile **byte-identical** — sha
`0797f51f…`; yeni dosya değil, ama kırık çıkarımı ortaya çıkardı.)

Ayrıca: resmî `MXUpdater_MAP1202_V1_11.exe` (Kimtigo) **zaten SKV6 tanıyor** —
`FlashBINType` tablosunda `… B37R SKV6 SKV7 SKV8 B47R …` ve
`####[%d] hynix v6 - ProgramLoop = %d`. Ama repoda zaten duran
`MXUpdater_MAP1202_V1_10.exe` (HYV8 paketi içinde, aynı 4.758.528 B) **aynı
string'leri aynı offsetlerde** taşıyor (`SKV6`@3390256, `hynix v6`@4228005) —
V1_11 sadece sürüm bump'ı, anlamlı diff yok. Yani "resmî updater SKV6'yı tanıyor"
yeni bir keşif değil, ama **araç tarafında SKV6 desteğinin var olduğunu** kesinleştiriyor:
eksik olan tek şey **derlenmiş `ZI0P*` SYS bin'i**.

---

## A4 — Aynı donanımın kardeşleri / resmî firmware paketleri

> **Dürüstlük notu:** bu av 12 Eylül'de zaten bir kez koşulmuş
> (`notlar/hyv6_updater_notlar-bati.md`, `…-cin.md`). Aşağıda gerçekten **yeni**
> olanları ayrıca işaretledim. Net sonuç: **`ZI0PC*` / `MKSSD_5010030001246*`
> içeren hiçbir resmî paket bulunamadı** — bugün inen 86 dosyanın (957 MB)
> tamamında case-sensitive grep = 0.

### A4.0 ★ YENİ — Diskimizin üçüncü-taraf ikizi belgelendi

`https://ssd-tester.com/gigimundo_g3500_1tb.html` (test **16 Mayıs 2025**),
GiGimundo G3500 1TB:
```
Firmware id string[1C0]: MKSSD_501003000132020000,Feb 1 2024,12:16:26,MAP1202,YI0PCELC
Project id string[180] : r:/0Project/HYV6_64GB_SVN13202
NAND string            : H25BFT8A1BDA
Ch0CE0: 0xad,0x7e,0x29,0x53,0x2,0xb0 - Hynix 3dv6-128L TLC
```
4ch × 2CE × 2die = 16 die × 64 GB = 1024 GB. Yani JD1024'ün HYV6 kimliği artık
**bizim çıkarımımızdan bağımsız, üçüncü taraf bir ölçümle** doğrulanmış durumda:
proje yolu resmen `HYV6_64GB`, FW tag `YI0PC***` (bizimki `ZI0PCD2C`).

### A4.0b ★ YENİ — Kimtigo TP3000: canlı, resmî, en yeni MAP1202 firmware kanalı

`https://www.kimtigo.com.cn/download/?lang=cn` (yükleme **2026-08-14**) →
`https://www.kimtigo.com.cn/u_file/fileUpload/2026-08/14/2026081478506.rar`
(uzantı `.rar` ama içerik ZIP). İçinde:
- `MCB6AA2H.bin` — **774.144 B**, tag `MKSSD_1010000059404e3100,Apr 10 2026,22:44:21,MAP1202,MCB6AA2H`
  → **gördüğümüz en yeni MAP1202 build'i**; `LOADER_CERT_TAG` + Maxio X.509 zinciri içeriyor.
- `MXUpdater_MAP1202_V1_11.exe` (4.758.528 B), `Update.ini`, SOP PDF.

`MC` öneki = N4PA ailesi, **HYV6 değil**. Ama iki işe yarıyor: (a) güncel imzalı
bir SYS bin referansı, (b) aşağıdaki `Update.ini` anahtarları.

### A4.0c ★ YENİ ve doğrudan kullanılabilir — `Update.ini` sürüm kontrolü anahtarları

DURUM'daki *"MXUpdater: Firmware does not need to be updated!"* tıkanıklığı için
dört resmî paketin `Update.ini`'si yan yana:

| paket | `ModifyFWV` | `EnCheckVID` | `EnCheckVersion` | `EnAutoUpdate` |
|---|---|---|---|---|
| ADATA LEGEND750 | 0 | **1** (VID=0x1CC1) | **1** | 1 |
| ZHITAI TiPlus5000 V1/V2 | 1 | 0 | *(anahtar yok)* | 1 |
| **Kimtigo TP3000** | 1 | 0 | *(anahtar yok)* | 1 |
| Patriot VP4300L | 1 | 0 | *(anahtar yok)* | 0 |

Anahtarın **yokluğu** = kontrol kapalı. Denenecek ilk kombinasyon:
`ModifyFWV=1`, `EnCheckVID=0`, `EnCheckVersion=0`, `EnCheckFWBinInfo=0`
(sonuncusu dördünde de zaten 0).

### A4.0d Bağımsız üçüncü-taraf teyit: "V6 için firmware yok"

- `https://www.usbdev.ru/f/index.php?topic=13389.0` (**18 Şub 2026**) — TWSC 512GB,
  `H25JGT883MDA` (SK hynix 128-katman V6 TLC) + MAP1202. Moderatör cevabı:
  > «**на V6 нет прошивки**»
- ⚠️ **`topic=13429` bağımsız kanıt DEĞİL** — o konu Alperen'in kendi konusu
  (`angelmxycry`), dolayısıyla onu "bağımsız doğrulama" diye saymak dairesel olur.
  Oradan alınabilecek tek bağımsız veri moderatör `hardmaster`'ın cevabı
  (**2 Mar 2026**):
  > «Этой прошивки нет даже у китайцев за деньги.» (Bu firmware Çinlilerde parayla bile yok.)
  Aynı konuda listelenen bin adları `ZI0PCABC, ZI0PCADC, ZI0PCD2C, ZI0PCPDLC`,
  paket `C.0.01018_HYV6`, `SN09466` — A3.1'deki xlsx satırıyla birebir tutuyor.

### A4.1 MAP1202'nin doğrulanmış rebrand'leri (marka → gerçek kontrolcü)

lcb.club'ın "主控揭秘" (kontrolcü ifşası) serisinden, hepsi 20 Eyl 2026'da okundu:

| Marka kodu | Gerçekte | Kaynak |
|---|---|---|
| **Lexar DM630** | 联芸 MAP1202 | http://lcb.club/post/359.html — *"雷克沙固态硬盘所用的DM630主控，实际就是联芸MAP1202主控。"* |
| **HIKSEMI/Maxio HKP10204A** | 联芸 MAP1202 | http://lcb.club/post/345.html — *"HKP10204A主控，实际就是联芸MAP1202主控。"* |
| HIKSEMI HKP10304A | 联芸 MAP1602 | http://lcb.club/post/348.html |
| Lexar DM928 | 联芸 MAS1102 | http://lcb.club/post/334.html |
| Lexar DM918 / FORESEE DM918 | 联芸 MAS0902 | http://lcb.club/post/325.html, /327.html |

Bu, **Lexar**'ın MAP1202 tabanlı ürünlerinin resmî firmware updater'ının bizim
kontrolcümüz için bir MAXIO updater olduğu anlamına gelir — A4 için en umutlu
resmî kanal.

### A4.2 usbdev'de bulunan resmî OEM updater'lar (MAXIO NVMe)

usbdev'in Maxio bölüm indeksi (translate proxy ile okundu, 20 Eyl 2026):

- `ADATA LEGEND 750 FW Update (Maxio MAP1202)` — **bizde var**
- `ZHITAI TiPlus5000 Firmware Update Tool (Maxio MAP1202)` [2] — **bizde var**
- `ZHITAI TiPlus5000 Smart Tool (Maxio MAP1202)` [4] — **bizde var**
- `Patriot Viper VP4300L Update Tool (Maxio MAP1602A)` [2] — **bizde yoktu**
  (`Viper_VP4300L_1TB_update_Tool_20230724.rar`, `..._2TB_...`, `MKUpdater_MAP160x_V0_04.exe`)
- `ZHITAI TiPlus7100 Smart Tool (MAP1602)` [7], `ZHITAI Ti600 Smart Tool (MAP1602)` [3]
- `Maxio MAP1602 MP/Sorting Tool` **[14 paket]** — bizde **hiç yok**; en yenisi
  `MAP1602-N58R-F0.1.50-512GB-2TB-GTab67df-SY8686k-...-H250811a.rar` (**F0.1.50, Ağu 2025**)
- `Maxio MAP160x Utility` [3] — `MXUtility_MAP160x_V0_16 / V0_19 / V0_20`

usbdev'den **indirme şu an mümkün değil** (403, yukarıdaki erişim notu). Okuma
çalışıyor, indirme çalışmıyor.

### A4.3 liangchanba'da olan, bizde olmayan MAP1202 yardımcı araçları

xlsx'ten (hepsi login arkasında):
`MXUtility_MAP1202_PCIe_V0_09a.rar` (**PCIe sürümü!**), `MXUtility_MAP1202_V0_013 /
V0_014 / V0_016 / V0_017 / V1_05`, `MKUpdater_MAP1202_V0_03a / V0_07 / V0_08 /
V0_09_RC-SVN9273 / V0_10 / V0_12 / V1_04`, `Maxio PCIe SSD MDI Tool [MAP1002\MAP1202]`
→ `MX_MDITool_V1.07.rar` (1.22 MB, 1012 indirme).

`MXUtility_MAP1202_PCIe_V0_09a.rar` bizim passthrough kurulumumuz için doğrudan
alakalı: **MXUtility'nin PCIe varyantı gerçekten var.**

---

## A5 — Profesyonel servis/veri kurtarma ekosistemi

Ayrı ajan taraması; özeti:

| Araç | MAP1202 | Kanıt |
|---|---|---|
| **ACE Lab PC-3000 SSD** | ❌ | Desteklenen liste v3.9.8 (**15 Tem 2026**): `SATA Maxio controlelr family: MAS0902 / Lexar DM918 · MAS1102 / Lexar DM928`. Sayfada `MAP1[0-9]{3}` = 0 eşleşme. NVMe tarafında sadece SMI/Phison/Marvell. |
| **Rusolut VNR** | ❌ | vnr-supported-controllers-list ve Catalog 2025 PDF'inde "maxio" = 0. Platform 11.2 (8 Eyl 2026) tek yeni controller: Phison PS2251-70-25. |
| **MRT Lab** | ❌ | us.mrtlab.com/SSDDE/ ve upgrade log'da Maxio = 0. En yeni sürüm 3.1.2.0 (10 Mar 2026). |
| **DFL** | ❌ | "SSD Firmware Repair Controllers and Families Support" (**17 Kas 2025**): sadece SM2246XT/2256K/2258XT/2259XT ve PS3109/3110/3111 — hepsi SATA. |
| **Atola / SalvationDATA / UFS Explorer** | ❌/bilinmiyor | Atola NVMe'ye sadece JMS583 köprüsüyle imaging yapıyor, firmware'e girmiyor. Diğerlerinde yayınlanmış liste yok. |

ACE Lab release note 3.9.8 (15 Tem 2026) aynen:
> "This update now covers **all major Maxio controllers** and their modifications—
> MAS0902, Lexar DM918, MAS1102, and Lexar DM928."
— dördü de SATA. NVMe MAP ailesi 2026 ortası itibarıyla **hiçbir profesyonel araçta yok**.

hddguru'da 13 Nisan 2026'da açılan "Maxio MAP1202A NVMe… ACE Lab development status"
sorusu (https://forum.hddguru.com/viewtopic.php?f=10&t=45982) **bugüne kadar
cevapsız** — profesyonel toplulukta bilginin olmadığının doğrudan kanıtı.

**Aktarılabilir teknikler** (MAXIO'ya özel değil, ama mekanizma bizimkine oturuyor):

- **"Clear Translator"** — PC-3000 SSD 3.9.8'e eklenen yeni test, aynen:
  > "ADDED a new test, 'SSD repair functions' - 'Clear Translator', which can restore
  > functionality to a drive stuck in a 'busy' state due to translator corruption.
  > **Warning! User data will be erased in this case**"
  Bizim senaryonun birebir karşılığı: bozuk FTL sayfası → firmware assert → FTL'i
  sıfırla → assert biter, veri gider (bizde önemsiz).
- **Hata anında otomatik loader yeniden yükleme** — aynı sürümün JMicron/Maxio
  changelog'u: *"ADDED automatic loader uploading when SSD operation errors occur."*
- **RAM'e volatile loader + ROM short** — ACE Lab, SM2258XT yazısı (13 Eki 2023):
  loader'ın özellikleri arasında *"Unlocked Techno-Mode functions"* ve
  *"Unlocked hidden factory functions (password management, factory reset, etc)"*.

---

## A6 — Genel "SSD salt-okunur kaldı" literatürü (elenmişleri tekrar etmeden)

Elenmiş olanlar (format NS / sanitize / secure erase / fw-commit) **tekrarlanmıyor**.
Yeni/denenmemiş olanlar:

### A6.1 NVMe FID `0x84` — Namespace Write Protect (standart, denenmemiş)

NVMe 1.4c'den beri standart. Kontrol ve temizleme:
```
nvme id-ctrl /dev/nvmeX | grep -i nwpc        # feature destekleniyor mu
nvme get-feature /dev/nvmeX -f 0x84 -n 1      # mevcut durum
nvme set-feature /dev/nvmeX -f 0x84 -n 1 -v 0 # (--save ile kalıcı)
```
Kaynak: Ubuntu manpage `nvme_set_features_write_protect(2)`
(https://manpages.ubuntu.com/manpages/noble/man2/nvme_set_features_write_protect.2.html),
`nvme-set-feature(1)`. Not: NVMe'de "Permanent Write Protect" durumu geri alınamaz;
diğer üç durum alınabilir.
→ Bu bizim `mod=4`'ümüz **değil** büyük ihtimalle, ama **10 saniyelik bir testle
hangi katmanda olduğumuzu kesinleştirir** ve listede denenmiş görünmüyor.

### A6.2 SMART Critical Warning bit 3 — hangi katman olduğunu söyler

`nvme smart-log /dev/nvmeX` → `critical_warning`. Bit 3 = 1 ise **standart NVMe
read-only** ilan edilmiş (0x08); 0 ise kilit tamamen firmware-içi/vendor seviyesinde
ve NVMe katmanından görünmüyor. Kaynak: DiskTuna, 20 Haz 2023 (yukarıda).
Bu ikisi birlikte "A6.1 işe yarar mı" sorusunu deneysel olarak kapatır.

### A6.3 Vendor subcommand uzayını taramak (en yüksek beklenen değer)

`ssd-flash-id`'nin açıkladığı yapı (A2.4) subcommand'ın **tek bayt** olduğunu
gösteriyor ve bizde zaten `0x86` (ReadRam) çalışıyor, `0x87` (WriteRam) ürün
modunda NO-OP. Yayınlanmış subcmd listesi sadece `{0xFF, 0x86, 0x36}` — yani
**uzayın büyük kısmı belgelenmemiş ve 256 ile sınırlı**. Disk feda edilebilir
olduğu için bu tarama bizde ucuz, başkalarında değil. Literatürde bunu yapan yok.

### A6.4 Kendi NAND'ımızdan firmware'i geri okumak (vlo yöntemi)

usbdev topic 12338, vlo (**20 Şub 2026**):
> "так если загрузить в него gdp, ничто не мешает их вычитать с 'дохлого' диска.
> сколько ж там копий прошивки лежит... **в одном только блоке 5шт, и это в каждом
> ce/ch**, и похоже не только в 0 блоке, но и в 1 тоже."
> "в принципе в сравнении с образами в файлах **не хватает только 4к заголовка в
> начале**. но как его формируют..."

İki somut iddia:
1. Firmware'in NAND'da **blok başına ~5 kopyası** var, **her ce/ch'de**, hem blok 0
   hem blok 1'de. 16 die'lı bizde bu ~160 kopya demek.
2. NAND'dan okunan imaj ile paketteki `SYS/*.bin` arasındaki fark **sadece baştaki
   4 KB'lık header**.

Bizim RAM dump'larımız 495.616 / 528.384 B, hedef ~692.224 B. GDP mode'da NAND'dan
blok okuyarak **tam imajı** toplamak, RAM dump'ındaki eksikliği kapatmanın
belgelenmiş yolu. roman2013 aynı threadde blok-blok dump'larını paylaşmış
(https://disk.yandex.ru/d/5JyAptvLvHKRGg) — format referansı olarak kullanılabilir.

### A6.5 Paketi başka NAND'a uyarlamak — tek gerçek zorluk GPIO

usbdev topic 12338, vlo (son mesaj, 21 Şub 2026):
> "единственная великая сложность в maxio — **подбор gpio для пересадки памяти**,
> иногда его можно вытащить и узнать прямо из инструмента, а иногда... перебором...
> больше ничего нет сложного, если есть у вас совместимый инструмент."

Bizim `Flash.ini` SKV6 satırının son alanı `... 001 2048 **100**` — `Gpio=100`.
Yani uyarlama probleminin "çözülmemiş" sayılan kısmı aslında **tek bir sayı** ve
gerekirse brute-force edilebilir bir sayı.

Aynı threadde JenDos_50 (21 Şub 2026) bunu fiilen yaptı: N38B paketini N38A'ya
yeniden adlandırdı, algılanan FW adını (`KC1UCA3H`) elle düzeltti, `Inherit RDT +
Sort` ile yazdı, kapasiteyi kırparak çalışır hale getirdi.

### A6.6 İşe YARAMAYAN olarak belgelenenler (zaman harcamayın)

- **"BIOS'ta 30 dk bekletme / power-cycle CPR"** — Rossmann, *The Power-Cycle CPR
  Method for a Dead SSD*: bu "idle trick" sadece **sağlıklı** bir controller'ın GC
  yapmasına izin verir; *"does nothing for a firmware panic, a BSY lockup, or an
  LDPC read-retry collapse, because the controller is halted the entire time."*
- **Chip-off / donor PCB** — MAXIO NVMe'de AES anahtarı silikona bağlı:
  *"the key is generated on & bound to the original controller, so desoldering the
  NAND yields ciphertext."* (Rossmann, maxio-architecture, güncelleme Ağu 2026)
- **PSID revert / Opal** — MAP1202 DRAM-less tüketici kontrolcüsünde Opal/PSID
  desteği belgelenmemiş; PSID etiket üzerinde basılı olmalı, JD1024'te yok.

---

## İNDİRİLEN DOSYALAR (bu tur)

Konum: `/home/schrodinger/jd1024/araclar_indirilen/yeni_2026-09-20/`
Hepsi magic-byte ile doğrulandı (`file` + `head -c 8 | xxd`).

| Dosya | Bayt | sha256 (ilk 16) | Tür | Kaynak |
|---|---|---|---|---|
| `a3_lcb_tum_ekler_listesi_20240915.xlsx` | 897.616 | `73026107e2d8b65c` | XLSX (OK) | https://file.diyflash.top/down.php/c28fd1aa8200d383763fa98b2b9855fe.xlsx |
| `a3_lcb_HYV7_acildi.jpg` | 161.134 | `928c9ad8d17898b4` | JPEG (OK) | https://file.diyflash.top/down.php/6365e97533c34814f959efa9ca990f67.jpg |
| `a3_lcb_firmware_kaynagi.jpg` | 194.427 | `8ea7fcab0c90f63b` | JPEG (OK) | https://file.diyflash.top/down.php/b24f95ca126bc8d6b0a3ac15bed489a3.jpg |

Ayrıca `a5_*` (15 dosya, A5 ajanı) ve `a4*` (A4 ajanı, ~50 dosya) aynı dizinde;
toplam **86 dosya / 957 MB**. Tam sha256 tablosu:
`yeni_2026-09-20/a4w_verification_table.txt`. Öne çıkanlar:

| Dosya | Bayt | sha256 (ilk 16) | Not |
|---|---|---|---|
| `a4c_kimtigo_TP3000_512GB_FW_GT59404e.rar` | 2.203.772 | `3b12937169f4d02a` | ZIP içerik; `MCB6AA2H.bin` 774.144 B + `MXUpdater_MAP1202_V1_11.exe` |
| `a4w_patriot_VP4300L_1TB_update_20230724.zip` | 1.786.410 | `614b51d21b0d438c` | MAP1602A resmî updater |
| `a4_zhitai_UNIMASTER_SSD_V6.1_20260903.zip` | 66.495.024 | `12d55a59b65caf1c` | 3 Eyl 2026 |
| `a4f_github_EEUUAA_DAT_ucode.bin` | 1.436.016 | `0797f51f7d4e4d9e` | SKV6 ×8 blok; repodakiyle birebir aynı |
| `a4f_github_fdfdb_map1202_43.ini` | 12.011 | `731e1df5a5b3d1ec` | Flash.ini v043 |
| `a4f_github_fdfdb_map1602_44.ini` | 13.085 | `c9ddc0ae612a3787` | **v044 — v043'ten yeni** |
| `a4_flashinfo_mptool_catalog.txt` | 66.471 | `5207e2ae9755a6ef` | flashinfo.top tam katalog (1548 paket) |

**🔧 İNDİRME DOĞRULAMASI — kural güncellendi.** `a4w_lexar_DiskMaster_EN_V1.2.0.zip`
ilk indirmede **59.146.240 B** geldi (gerçek boyut 65.620.746), `PK` magic'i
**doğruydu**, `file` "Zip archive" dedi — yani KAYNAKLAR.md'deki magic-byte kuralı
bu kesilmeyi **yakalamadı**. `unzip -t` yakaladı.
→ Yeni kural: **magic-byte + `unzip -t` / `unrar t`** (RAR5'te `7z t` bazı metotları
desteklemediği için yanlış FAIL verir; `unrar t` kullan).

**İndirilemeyenler ve nedeni:**
- `MAP1202_HYV6_64GBDIE-C.01.018-SN9466.rar` (aid 7498) — liangchanba, **admin izni**;
  misafir indirmesi `deny.rar` stub'ına 302. Kayıt açmak görev kuralıyla yasak.
- `MAP1202-Hynix_V7-0x39-V0.01.020-...-H220719b.rar` (aid 15746) — aynı site,
  1-yıldız üye + 1 金币.
- `YS9205_16.806_2XB4827E_HYV6_AD7E285302B0.7z` — flashinfo.top, VIP üyelik.
- usbdev `MAP1602 MP/Sorting Tool` [14] ve `Viper VP4300L Update Tool` — usbdev
  **indirme** 403 (okuma translate proxy ile çalışıyor, indirme çalışmıyor;
  allorigins ve codetabs proxy'leri de başarısız).
- lcb.club/post/195 ("SSD开卡转接板/硬盘盒SPI Flash短接方法及图示" — ROM nokta şemaları)
  ve /post/193 — site bizi rate-limit'ledi (bağlantı düşüyor); başlık doğrulandı,
  gövde alınamadı.

**⚠️ Ortam uyarısı:** çalışma sırasında `/` **%100 doldu** (164 G'nin 155 G'si;
`/home/schrodinger/yedek-kaplikaya` tek başına 119 GB). Bash çıktıları ENOSPC ile
kayboldu. `npm cache clean --force` ile ~1,5 GB açıldı (cache, geri gelir) — ama
kök sorun duruyor, sonraki indirmelerden önce yer açılmalı.

---

# ★ BİZİM DURUMUMUZ İÇİN SIRALI AKSİYON LİSTESİ

*(en yüksek beklenen değer üstte; parantezde maliyet)*

**1. MPTOOL.ini'ye `[Setting] ToolModeSetting=0` ekle ve Test Items'ı tekrar aç.** (5 dk)
Tüm `Tool Type` modları (MPT/SORT/QC/MDI/Updater) açılır. Şu an muhtemelen
göremediğimiz modlar var. Ayrıca `[TestItems]` altına `EnSMARTCheck=1` ve
`EnClearSMART=1` ekle → `Clear/Set SMART` kutusu gelir; **assert sayacını (3)
sıfırlama ihtimali** olan tek GUI fonksiyonu bu.
Kaynak: lcb.club/post/13, /post/14, /post/47.

**2. MPTOOL.ini'de "SYS FW Setting" / "SORT FW Setting" mühendislik panelini aç.** (30 dk)
Böyle bir panelin var olduğu kanıtlı (量产部落 konu başlığı, ekler 2020-09-25).
Anahtar adı elde yok → elimizdeki tüm MAP1202/MAP1602 kitlerinin MPTOOL.ini'lerini
birleştirip `Sys`/`Sort`/`Fw`/`Setting`/`En...` geçen **tüm** anahtarları diff'le;
`MXMPTool_MAP1202_*.exe` içinde ini anahtar stringlerini `strings`/r2 ile çıkar.
Bu panel, diskin kendi `ZI0PCD2C` imajını araca elle verdirmenin yolu olabilir.

**3. MPTOOL.ini'yi V7 → V6'ya çevir ve `Preformat Mode` süpürmesi yap.** (1 saat)
Şu an yanlış ayarlı (`FlashUniName=SKV703001`, `FWOneBinName=SKV7.bin`,
`TMC_ARRAY_Default_M2_HynixV7.ini`, `Para_DW_SKV7_*`). Hedef:
`FlashUniName=SKV606411`, SKV6 PARA/TMC. Sonra `Tool Type=MPT` ile
`Inherit FW BB` → `Auto Inherit` → `Erase Search` → `Inherit RDT+Sort` sırayla
denenir. "Biri olmazsa diğerini dene" topluluğun standart tavsiyesi ve JenDos_50
bununla mismatched NAND'da başardı.
**Ve `Fail` çıkarsa hemen pes etme:** jumper'ı çek, gücü kes-ver, diski tekrar
bak — usbdev'de "Fail aldım ama disk çalıştı" vakası var.

**4. SORT/RDT yolunu MPT'den önce dene.** (yazma hızlı, RDT saatler sürer)
`Tool Type = SORT` → SORT.bin (MAXIO imzalı, ROM cert duvarını doğal geçer) yazılır
→ disk salt-güç kaynağına takılıp RDT'yi kendi koşar (akım düşünce biter) → sonra
MPT + `Inherit RDT`. JenDos_50'de ~9 saat sürdü ama işe yaradı. Bu, bozuk FTL'i
tamamen atlayıp bad-block tablosunu sıfırdan kurar.

**5. Bağlantı eksenini değiştir: JMS583 USB köprüsü al/kullan.** (donanım, ~200-400 TL)
MPTool'un çalıştığı **kanıtlı tek yol** bu. PCIe passthrough ile MPTool'un çalıştığı
tek bir topluluk kaydı yok; buna karşılık "anakart NVMe slotu + PCIE adaptör +
RTL9210B hiçbiri görmedi, JMS583 gelince gördü" diye net bir vaka var (usbdev 11517).
**RTL9210/RTL9210B alma** — açıkça uyumsuz.

**5b. MXUpdater sürüm kontrolünü `Update.ini` ile kapat.** (10 dk)
"Firmware does not need to be updated!" tıkanıklığı için dört resmî paketin
karşılaştırması net bir reçete veriyor (A4.0c): `ModifyFWV=1`, `EnCheckVID=0`,
`EnCheckVersion=0`, `EnCheckFWBinInfo=0`. `EnCheckVersion` anahtarının **yokluğu**
da kontrolü kapatıyor — ZHITAI/Kimtigo/Patriot paketlerinin üçünde de yok.
Referans olarak Kimtigo TP3000 paketindeki `MXUpdater_MAP1202_V1_11.exe` +
`Update.ini` kullan (V1_11 ile repodaki V1_10 arasında anlamlı fark yok).

**5c. Kırık SKV6 çıkarımını düzelt.** (15 dk)
`kanit/fw_hunt3/skv6_from_ucode/…BLOB_A_ONLY.bin` dosyaları **2.160 B**, gerçek
kayıt **16.384 B** — mevcut çıkarma scripti eksik çalışmış ve bu sessiz bir hata.
Doğrusu `yeni_2026-09-20/a4_skv6_ucode_from_github/` altında; `kanit/`'e taşı ve
eski kırık dosyaları etiketle, yoksa ileride yanlış veriyle çalışılır.

**6. İki dakikalık katman testi: NVMe standart WP mi, firmware-içi mi?** (2 dk)
`nvme id-ctrl | grep -i nwpc`, `nvme smart-log` → `critical_warning` bit 3,
`nvme get-feature -f 0x84 -n 1`. Bit 3 = 0 ve nwpc desteklenmiyorsa kilit tamamen
vendor seviyesinde demektir ve A6.1 yolu kapanır — ama bunu **ölçerek** kapatmış
oluruz. Bit 3 = 1 ise `set-feature -f 0x84 -v 0 --save` bedava bir deneme.

**7. Vendor subcommand uzayını tara (0x00–0xFF).** (yarım gün script)
`cdw12 = 0x1234<<8 | subcmd`, opcode `0xC1` (arm/write) ve `0xC2` (read).
Bilinen: `0xFF` arm, `0x86` bulk info, `0x36` flash id, `0x87` WriteRam (ürün
modunda NO-OP). Kalan ~250 değer belgelenmemiş. Her denemeden sonra `mod (0x00810CE8)`,
`assert (0x040EEE58)`, `Func0 (0x00000398)` register'larını `0x86` ile oku → durum
değiştiren subcmd'i **ölçerek** bul. Disk feda edilebilir; bu taramayı yapabilecek
konumdaki tek kişi biziz.

**8. GDP mode'da NAND'dan tam firmware imajını topla.** (1 gün)
vlo: her ce/ch'de blok 0 ve blok 1'de **~5'er kopya**; NAND'daki imaj paketteki
`SYS/*.bin`'den **sadece 4 KB header** eksik. 16 die → ~160 kopya; çoğunluk oyuyla
temiz bir `ZI0PCD2C` (~692.224 B) çıkarılabilir. Bu, RAM dump'larımızdaki
164–197 KB eksiği kapatmanın belgelenmiş yolu.
Araç: `maxio_nvme_fid` v0.38+ (GDP mode desteği var, ROM mode'da çalışmaz) —
14 sürüm zaten `araclar_indirilen/usbdev/` altında.

**9. Gpio değerini brute-force listesine al.** (uyarlama sırasında)
vlo'ya göre MAXIO'da NAND uyarlamanın **tek gerçek zorluğu** Gpio seçimi ve
"bazen brute-force" ediliyor. Bizim `Flash.ini` satırında `Gpio=100`. MPT bu
yüzden reddediyorsa, değeri süpürmek meşru bir adım.

**10. (Düşük öncelik, dış bağımlı) Eksik iki dosyayı edinme yolları.**
`MAP1202_HYV6_64GBDIE-C.01.018-SN9466.rar` (2,64 MB, aid 7498) ve
`MAP1202-Hynix_V7-0x39-V0.01.020-...` (5,48 MB, aid 15746) **var ama
club.liangchanba.com'da izin arkasında**; kayıt açmak bu görevin kuralına aykırı
olduğu için yapılmadı. Alperen isterse bu tek adımlık bir karar (site ücretsiz
kayıt + yıldız/金币 sistemi). **Ama HYV6 paketi para/üyelikle de alınamıyor** —
izni `苦逼管理` (yönetici). Moderatör `hardmaster` (usbdev, 2 Mar 2026):
> «Этой прошивки нет даже у китайцев за деньги.»
Ayna aranan yerler: usbdev (19 MAP1202 paketi), flashinfo.top (1548-1666 kayıtlık
tam katalog), file.diyflash.top (43 dosya), inhdd.com, ssdtool.cc (katalog boş) —
**hiçbirinde yok**. Yalnızca `V0.01.020 HYV7` (aid 15746) üyelikle erişilebilir
durumda ve o da HYV6 değil, ama bizim yapısal ikizimizin daha yeni sürümü.

**11. Kapanmamış tek batı leadi: Lexar NM610 PRO `.pkg` şifre çözümü.** (RE işi)
Lexar'ın dağıttığı firmware paketleri **TEA/XTEA ile şifreli**; anahtar
`SSD Dash.exe` içinde. Lexar DM630 = MAP1202 olduğu için (A4.1) çözülürse resmî
MAP1202 firmware'lerine erişim açılır. İndirme değil, disassembly işi.
