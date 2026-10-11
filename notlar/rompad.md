# MAP1202 ROM pad + UART arastirma notlari
Tarih: 2026-09-12. Arac: WebFetch (Brave search proxy) + curl. WebSearch butcesi tukenmisti.

## A. KAYNAKLAR

### A1. pitfalls.ru — Netac NV3000 250GB / MAP1202 (ANA KAYNAK)
URL: https://pitfalls.ru/восстанавливаем-прошивку-ssd-nvme-диска-netac-nv3000-250gb/
Gorseller (indirildi): ROM.jpg, IMG_6410, IMG_6403, IMG_6399, IMG_6395, IMG_6389, box_jms583.jpg
Onemli birebir alintilar (RU):
- "но когда я сменил свой любимый NVME-USB бокс от Ugreen на китайский с чипом JMS583 ...
   все же диск определило в ROM-режиме с замыканием контактов"
  -> Ugreen kutusu ISE YARAMADI; JMS583 cipli ucuz Cin kutusu ROM modunu gecirdi.
- "Вводим диск в ROM-режим, для этого подключаем через переходник JMS583-USB диск с замкнутыми контактами ROM"
  -> Kisa devre ONCE yapilir, sonra disk takilir (guc verilir).
- Aygit Yoneticisi'nde: "Generic_ Loader_NVMe_Devi SCSI Disk Device"
- "Далее убрал перемычку-пинцет и нажал «START»"
  -> Cimbiz-jumper CIKARILIR, SONRA START'a basilir.
- Yazilim: MPTool_MAP1202_USB. Firmware: MAP1202-X2_9060-SN07939 + MAP1202-YMTC-JGS-C.0.01.009d-SN6760 (usbdev.ru)

### A2. pitfalls.ru — SM2263XT / LITEON CL1-4D256  (M.2 2242)  *** EN KRITIK ***
URL: https://pitfalls.ru/sm2263xt/
- "Ставим SSD диск в переходник PCI-E, замыкаем два контакта пинцетом на SSD диске
   и в таком положении включаем компьютер. Это приведет диск в режим ROM прошивки контроллера."
  -> Disk PCI-E adaptorde TAKILIYKEN, iki kontak cimbizla kisa devre edilir ve
     BU POZISYONDA BILGISAYAR ACILIR. (Yani yuvada/adaptorde yapilabiliyor!)
- "После включения ПК и загрузки Windows пинцет убираем."
  -> PC acilip Windows yuklendikten SONRA cimbiz cekilir.
- Gorsel: rom.png (pad yeri), IMG_7100/7101 (PCIe adaptorde cimbiz), photo_..._12-15-39 (adaptor)

### A3. pitfalls.ru — Yeestor YS9205 / Netac NV3000 500GB
URL: https://pitfalls.ru/ys9205_ssd_firmware_restore/
- "Методом перебора определил контакты, нужные для попадания в ROM режим"
  -> Pad'ler etiketsizse DENEME-YANILMA ile bulunuyor.
- "Замкнул контакты ROM пинцетом, подключил к ПК, разомкнул контакты"
- JMS583 cipli Cin NVME-USB kutusu.
- "Внимание! В процессе восстановления прошивки накопителя — данные безвозвратно уничтожаются!"
- Gorsel: rom.jpg (PCB: YSP8-PC-CYS-S-001-00)

### A4. CSDN 126171747 — genel acma-kart (kaikai) rehberi
- "板子上有一个ROM MODE的标识，字母的边上的两个洞就是进入工程模式的短接位置，短接后再插入电脑"
- "其他固态硬盘的短接位置其实都差不多，基本都是有ROM、JP1这样的字母标识
   （另外，JMF主控一般是J1；英特尔、威刚很多型号是J3）"
- "电脑识别到新设备后，就可以取下短接跳线了，开卡过程中不要短接，否则会导致开卡失败。"
- "尽量不要使用机箱前置USB接口开卡，更不要使用USB HUB、USB延长线之类的东西"
- "NVME接口需要NVME转USB转接盒（经验证，JMS583芯片可用）"
- "很多普通硬盘盒，包括JM20329E，仅仅支持二次开卡" (muhendislik modunu GECIRMEZ)

### A5. CSDN 142320484 — ELEKTRIKSEL ACIKLAMA (birebir)
"如何进入电路板工程模式：需要拆下SSD固态硬盘外壳，将ROM旁边，白色方框中的两孔，用摄子短路，
 其目的是将ROM数据脚从高电平，平时此脚使用时悬空，保持高电平，这样，ROM中的固件程序就永久固化了，
 变成了只读模式。将此脚与地短接后，电平变低，清除了只读模式，可以写入了。"
-> Pad'lerden biri strap/ROM pini (normalde bosta, dahili pull-up ile YUKSEK),
   digeri GND. Kisa devre = pini LOW'a cekmek -> kontrolcu NAND'daki firmware'i
   atlayip ROM/loader moduna duser.

### A6. juejin 7512339903402426394 — MAP1202'ye OZEL prosedur (birebir)
"准备一个JMS583主控的硬盘盒，比较适合量产开卡，而RTL9210系列的不行。
 双击打开MAP1202量产工具主程序，用金属镊子短接固态硬盘板子上的两个ROM点
 （不确定哪个是ROM点的可以自己多次短接测试），保持短接，然后把固态硬盘用硬盘盒连接电脑，
 软件即识别固态，拿下镊子断开短接。"
-> JMS583 CALISIR, RTL9210 CALISMAZ. Once tool acilir, sonra kisa devre, sonra tak, tanindi -> birak.
"注意在量产操作前要备份数据，因为开卡后数据将不保留且无法恢复" (veri gider)

### A7. CSDN 140499419
"短接你硬盘上的ROM，如果没有ROM那就是JP1，如果都没有标识，就找单独的两个焊盘"
-> Etiket yoksa "tek basina duran iki pad" aranir.

### A8. usbdev.ru — flash test modu genel makalesi
http://www.usbdev.ru/articles/testmod/   (https 500 veriyor, http calisiyor)
- "подключаем флешку в USB-порт, удерживаем 1-2 секунды и размыкаем контакты"
- "После определения флэшка в системе разомкнуть выводы (почти сразу разомкнуть после подключения – т.е. не удерживать)"
- Uyari: "если что-то пойдёт не так ... может стать причинной того что у Вас сгорит флэшка или вообще материнская плата"
- Uyari: "Замыкать нужно очень осторожно, чтобы не попасть на вывод питающий микросхему памяти"

### A9. rossmanngroup.com
- firmware-panics-rom-mode: "ROM_CS test pad ... shorts it to ground with precision tweezers
  at the exact moment bench power is applied"; "open-drain operation that stops the controller
  from parsing the corrupted firmware payload out of the NAND"
- maxio-architecture: "On MAS0902 SATA boards, these are typically two through-hole pads near
  the controller IC, sometimes labeled in silkscreen"
- Risk: "Connecting a 3.3V terminal to an 88SS1074 will damage the controller die"
- MAP1202/1602 icin PC-3000 destegi YOK.
- Uyari: panige girmis MAP NVMe'de MPTool = yikici reformat.

### A10. usbdev.ru forum topic=12338 "Maxio MAP1202 изучение, прошивки, особенности"
https://www.usbdev.ru/f/index.php?topic=12338.0  (tek sayfa, 15 mesaj)
- roman2013, Apacer AS2280P4 1TB, MAP1202 + Intel 144L N38A QLC
- post#1: "При запуске через jms583 нет никаких признаков активности" (JMS583'te hicbir isaret yok)
- post#3: "Получен лог через USART при старте" -> UART boot log (asagida)
- post#4: "Зацепил UART нормально для наблюдений за процессом загрузки.
   В итоге при очередном старте в консоле появилось сообщение о частоте 'CLK:550,475,137'
   Диск распознался системой."
- post#9: "Диск сдох достаточно быстро после 'магии'" (disk kisa surede oldu) <-- RISK
- roman2013 UART pad yerini/baud'u YAZMAMIS. Fotograf ekleri login istiyor
  ("Вы не можете просматривать это вложение").
- post#15 (DarwinLudwig): "единственная великая сложность в maxio - подбор gpio для пересадки
  памяти ... перебором"

## B. ROM PAD YERI — GORSEL KANIT OZETI

| Kart | Kontrolcu | Pad yeri |
|---|---|---|
| Netac NV3000 250GB (ROM.jpg + IMG_6389) | MAP1202 | UST yuz, kartin UZAK ucu (vida centigi ucu), uzun kenarda, centikten ~9-11 mm geride, 2 yuvarlak altin pad yan yana |
| Netac NV3000 500GB (rom_ys9205.jpg) | YS9205 | UZAK uc, yarim daire centigin USTUNDE 2x4 pad grubu + ALTINDA 1x4 (serigrafi R/T/G) — ROM cifti bunlarin icinde |
| LITEON CL1-4D256 2242 (rom_sm2263xt.png) | SM2263XT | UZAK uc, centigin ustunde 4'lu dikey pad kolonu; ustteki ikisi serigrafi "T" ve "R" (UART), ALTTAKI IKISI = ROM |

ORUNTU: M.2 SSD'lerde test pad kumesi kartin UZAK UCUNDA, vida centiginin cevresinde.
Ayni kumede UART (T/R/G) de var. ROM cifti bu kumenin icinde.

## C. UART BOOT LOG (roman2013, MAP1202 + Intel N38A, USART)
Asamalar: @BM/@DIE -> hc init done -> UART-RDY 00 -> B1TCM-Over -> SRAM Cache -> UART-RDY 01
-> Faa Format -> DDR:1200 -> RAID:4,4,4 -> E2E -> Dual CPU Run / CPU0 GO -> LDPC init
-> FA_DRV/FA_IF -> Z-CFG -> FA_TM -> ZQ -> DCC -> DS init
-> [CodeBlk]S ... TblPart/PBN-#xx BAD-n / TotalBBB=10 / Bad(161)LogBlk(212)Rate(24) ... [CodeBlk]E
-> [QBT]S ... Q-HP / Q-InvMark / Q-Query-NG / Q-NoVld / Q-RdFail ... [QBT]E,3,ms
-> [PBT]S ... #BB / chkptr blk / HeadSrch / B-Srch / HDieSrch / H_PG / H_CHKPTR / blk_list
-> [SD-Rslt: ffff] ... -> HOT PLUG:0 -> >PE_RISE -> >PE_FALL idle:1
Basarili acilis farki: konsola "CLK:550,475,137" mesaji dusuyor ve disk taniniyor.

## D. PAD TIPI — DOGRULANDI
z_rom_pads_macro.png: pitfalls MAP1202 ROM pad'leri = **plated through-hole (delikli)**,
altin halka + ortada gorunur delik, ~1,5-2 mm merkez arasi, beyaz serigrafi cerceve icinde,
kenar SMD kondansator sirasinin arasinda. Bizim karttaki iki delikli pad ile AYNI tip.

## E. SERIGRAFI KANITI — UART, ROM'un YANINDA
- LITEON CL1-4D256 (SM2263XT): uzak ucta, montaj centiginin hemen USTUNDE **4'lu dikey PTH kolonu**.
  Ustten alta serigrafi: T (TX), R (RX), G (GND), + 4. pad.
  KIRMIZI KUTU = **alttaki iki pad (G + 4.)** -> yani "strap'i GND'ye kisa devre et".
- Netac NV3000 500GB (YS9205, PCB YSP8-PC-CYS-S-001-00): uzak uc.
  Centigin ALTINDA beyaz parantezle gruplanmis **3'lu header: R / T / G** (=RX/TX/GND, UART!),
  onun altinda AYRI tek pad "2". Centigin USTUNDE 2x4 PTH grubu, alt sirasi "2" ve "1".
  Kirmizi oklar: **pad "1" (ust grup) <-> pad "2" (alt tek pad)** = ROM cifti.
  Kirmizi "ROM" yazisi bu duzeni etiketliyor.
-> SONUC: M.2 SSD'lerde UART (T/R/G) ile ROM pad'leri AYNI kumede, kartin uzak ucunda,
   montaj centiginin cevresinde. ROM ciftinin biri cogu zaman GND.

## F. YUVADA/ADAPTORDE KISA DEVRE — KANIT
pcie_tweezer_7100.jpg / 7101.jpg: SSD dikey PCIe->M.2 adaptor kartinda, x16 yuvasinda.
Ust yuz tamamen acikta, cimbiz rahat ulasiyor. Yazar PC'yi cimbiz basiliyken aciyor.
-> M.2 yuvasinda degil ama **PCIe adaptor kartinda** pratik ve kanitli.

## G. UART — NE BULUNDU / NE BULUNAMADI
BULUNDU: roman2013'un tam boot log'u (yukarida C).
BULUNAMADI (hicbir kaynakta yok): MAP1202 UART pad'inin kart uzerindeki yeri, baud rate,
lojik seviye. roman2013 yazmamis; forum ekleri login istiyor. Cince kaynaklarda da yok
(Baidu + Brave + usbdev tarandi). -> Ampirik belirlemek gerekiyor.
Genel pratik (hardware hacking kaynaklari): ilk deneme **115200 8N1**; seviye multimetre ile
TX pad'inin bosta duran gerilimi olculerek anlasilir (1,8 V mi 3,3 V mi).

## H. TURKIYE USB-TTL (2026-09 fiyat)
- Robotistan: "USB-TTL Serial UART Dönüştürücü CH340G" ~99,28 TL
- Direnç.net: "CP2102 6-Pin USB 2.0 UART TTL Seri Dönüştürücü" ~102,67 TL
- Ayrica: FT232RL (WaveShare orijinal), FT232 USB-TTL kablo, CP2102 Micro USB / HW-598
- CP2102 6-pin modul VCCIO/3V3 cikisi olanı tercih; 1,8 V icin FT232H/FT2232H ya da
  level shifter gerekir (CH340/CP2102 klasik modulleri 3,3 V/5 V).

## I. UART — SON TARAMA SONUCU
Brave/Baidu/usbdev taramalari: MAP1202 veya MAP1602 icin **yayinlanmis UART pad haritasi,
baud rate ya da lojik seviye YOK**. Sadece genel hardware-hacking tavsiyesi:
- Ilk deneme 115200 8N1; sonra 9600/19200/38400/57600/921600 taranir
  (HardwareAllTheThings, swisskyrepo)
- r/hardwarehacking'de sahte bir M.2 SSD'de 4800 baud cikmis -> baud sabit degil, taranmali
- "Look for unpopulated header pads near the processor or marked TX, RX, GND, VCC.
   Use a multimeter to identify ground (continuity to chassis)" (redfoxsec)

## J. INDIRILEN GORSELLER (bu klasor)
ROM.jpg                 pitfalls MAP1202 ROM pad'i (kirmizi kutu)
z_rom_farend.png        ^ uzak uc buyutulmus
z_rom_pads_macro.png    ^ iki pad makro (delikli oldugu net)
IMG_6389.jpg            cimbiz + JMS583 kutusu, kapak acik, canli
z_6389_board.png        ^ parlatilmis, tum kart
IMG_6399.jpg            MAXIO MAP1202A kontrolcu + kristal + M.2 fingers
IMG_6403/6410.jpg       Netac NV3000 etiketli on/arka
rom_ys9205.jpg          YS9205 kart, ROM + R/T/G UART header
z_ys9205_pads.png       ^ buyutulmus
z_ys_lower.png          ^ R/T/G serigrafisi net
rom_sm2263xt.png        LITEON CL1-4D256, 4'lu PTH kolon T/R/G/+
z_sm_col.png            ^ buyutulmus
pcie_tweezer_7100.jpg   PCIe->M.2 adaptorde cimbizla kisa devre (calisan PC)
pcie_tweezer_7101.jpg   ^ ayni, cimbiz cekilmis
pcie_adapter.jpg        cift M.2 PCIe adaptor karti
map1202.pdf             GitHub dom0ng/map1202 - SAGLAM diskte spoof (ROM gerekmez)
