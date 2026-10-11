# TEL TAKINCA — DENEME PLANI  (20 Eyl, telsiz hat tukendikten sonra)

Telsiz hat duvari: fw-commit imaji NAND'a yazamiyor (mod=4 senkron blokluyor, §21.14).
Tel takilinca disk ROM/loader moduna girer; orada `0x87 WriteRam` VAR (urun modunda yoktu).
Bu, kapali olan iki seyi acar: (a) RAM'e kod/mod yazma, (b) GDP loader -> MPTool firmware yazma.

## KURULUM (tel takili, HER seansta)
    ~/bin/jd-tel-modu ac        # pci-stub izolasyonu + update-grub + update-initramfs + soguk cevrim SART
    # (jd-tel-modu nvme surucusunun loader'i oldurmesini engeller — §feedback_rom_modunda_nvme)
    ~/bin/jd-cevrim
    ssh kaplikaya "sudo -n /usr/local/bin/jd-seans"   # pci-stub'dan al + GDP yukle + hazirla

## YOL 1 — RAM-boot firmware, NAND completion hatasini coz  [EN UMUT VERICI]
§18.3: yamali firmware RAM'den ayaga kalkiyor, TEK takildigi yer ROM NAND okuma:
`0xFFFF1528` completion 0.0sn'de "return 0" donuyor cunku NAND motoru komutu HATA ile
tamamliyor. Cevap `[0x06600074]&0xFFFF` completion durum kodunda.
ADIMLAR:
1. `jd-kos` ile yamali firmware'i (Y5+Y2) RAM'den boot et (HEDEF=0x204C).
2. ROM NAND okuma cagrisindan HEMEN SONRA §18.5 listesini oku:
     [0x06600074]&0xFFFF  <- completion DURUM (asil cevap)
     [0x06600070]>>16     <- completion id
     [0x0660004C] [0x06600040] [0x06600044]  <- kuyruk sayaclari
     0x04000E40+id*24 : +0x14 +0x16 +0x17    <- komut slotu bayraklari
     0x04001780+(id&0x1F)*16 : +0x00 +0x03 +0x04(bit2=HATA)  <- completion tablosu
3. UART log'da hangi mesaj basiliyor: "@NO DID" / "@SMBT FAIL" / hicbiri (§18.3 dallari).
4. Durum kodu belliyse: NIFC kanal register'larini (0x06641000+ch*0x1000) duzelt, tekrar dene.

## YOL 2 — 0x87 WriteRam ile mod=4'u RAM'de sifirla, sonra fw-commit  [TELSIZ DUVARI ASAR]
Tel modunda `0x87` var. Fikir:
1. GDP/loader modunda calisan firmware'e gec (ya da urun FW'ye tel takiliyken eris).
2. `0x87 WriteRam` ile `*(0x00810CE8) = 0` (mod=4 -> mod=0) yaz. GERI OKU dogrula (0x8A tuzagi: I-cache §16.3, taze adres).
3. mod=0 iken fw-commit CA=1 (jd_m12z_v4.bin) -> NAND yazma artik acik olabilir.
4. Ya da dogrudan LBA yazma testi: mod=0 iken yazma yutuluyor mu?
DIKKAT: 0x87 no-op tuzagi urun modundaydi; tel/GDP modunda gercek yaziyor mu ONCE dogrula
(bilinen adrese yaz-geri oku).

## YOL 3 — GDP loader -> MPTool USB kopru  [kopru_nvme.py HAZIR]
1. `jd-kopru kur` + `kopru_nvme.py --dry-run` (kuru tur SART).
2. MPTool'u (vm/mpt_yama/ ya da usbdev HYV8 paketi) baglan, `0xA1` faz-1 payload'i
   `4e564d45` ("NVME") ile basliyor mu bak. Basliyorsa canliya gec.
3. MPTool GDP loader'i 0x87 ile yukler (tel modunda calisir) -> firmware yazar.
NOT: usbdev HYV8 paketi indiriliyor (agent). HYV6 bizim NAND; HYV8 farkli ama MPTool+DAT yapisi ayni.

## YOL 4 — fw-commit'i tel modunda dene (mod farkli olabilir)
Urun modunda commit mod=4'e takiliyordu. Tel/loader modunda mod degeri farkli olabilir;
jd_m12z_v4.bin commit'i tel takiliyken tekrar denenebilir (dusuk olasilik ama ucuz).

## SIRALAMA (1,5 gun icin)
Once YOL 2 (en dogrudan: mod=0 yaz, LBA yazma acildi mi bak — 1 cevrimde belli olur).
Acilirsa: fw-commit ya da dogrudan kullanim. Acilmazsa YOL 1 (RAM-boot completion).
Paralelde YOL 3 kuru tur (MPTool konusuyor mu). YOL 4 firsat olursa.
