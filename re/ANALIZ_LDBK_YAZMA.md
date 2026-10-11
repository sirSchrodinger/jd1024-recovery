# `VP_DownloadToLoaderBlock` — loader block yazma dizisinin tam komut/payload dökümü

Hedef sorusu: *MPTool loader block'u NAND'a yazarken baştan sona hangi vendor komutlarını,
hangi sırayla, hangi tam payload baytlarıyla gönderiyor?*

Analiz edilen ikililer (ikisi de statik, cihaza hiçbir komut gönderilmedi):

| kısa ad | dosya | .text | not |
|---|---|---|---|
| **YENİ** | `/home/schrodinger/jd1024/kanit/fw_hunt3/ex/MAP1202_H25TXTD2XCX6/MAP1202_H25TXTD2XCX6/MXMPTool_MAP1202_USB_V1_1_26.exe` | `0x401000..0x7CC000` (file = vma − 0x400A00) | SKV8 paketi |
| **ESKİ** | `/home/schrodinger/jd1024/kanit/fw_hunt3/ex/MAP1202_HYV7_64GB_Die_128G-1T/MAP1202 HYV7 64GB Die 128G-1T SN09286 20220704/T1/MXMPTool_MAP1202_USB_V0_01_017.exe` | `0x401000..0x79C000` (file = vma − 0x400A00) | `ANALIZ_MPTOOL.md`'nin kaynağı |

> **Önemli:** senin diskindeki sayfa düzeni (**sayfa 0–7 mode 0, sayfa 8+ mode 2**) **ESKİ**
> kuşakla birebir uyuyor (info + cert + **6** LDPC = 8 sayfa mode 0; veri sayfaları
> `ucLdpcMode` = Flash.ini ECC = 2). YENİ sürümde 9 LDPC sayfası var (0–10 mode 0) ve veri
> sayfalarında mode sabit `1`. Bu yüzden aşağıdaki reçete **ESKİ sürüm** temel alınarak
> yazıldı; YENİ sürümdeki farklar ayrıca işaretlendi.

---

## 0. TL;DR — kayıp adım

1. **`0x4D InitGDP` + 512 baytlık loader-block bitmask haritası hiç gönderilmemiş.**
   MPTool yazmadan önce GDP'ye "her (kanal, CE) için loader block'lar şunlar" diye bir
   harita yüklüyor. `EnWritePageToAllDie=1` olan her pakette bu adım var.
2. **Silme tek tek die'a `0x8B` ile yapılmıyor.** MPTool `ch=0xFF, bank=0xFF,
   block=<süper-blok indeksi>, p4=0, p5=0` ile **broadcast** siliyor. Sizin denediğiniz
   `p4=0,p5=1` ve `p4=1,p5=1` kombinasyonlarının ikisi de gerçek `ch/bank/blk` ile gönderilen
   **farklı bir kod yolundan** (`VP_PROC_EraseValidLoaderBlock`, UI'dan çağrılan tek-blok silme)
   geliyor; download yolunda kullanılmıyor.
3. **Sayfalar `0x8A` ile tek tek die'a yazılmıyor.** `EnWritePageToAllDie=1` iken MPTool her
   sayfa için **tek bir `0x4C` (PageWriteInterleave)** komutu gönderiyor; denetleyici sayfayı
   `0x4D` haritasındaki bütün die'lara kendisi dağıtıyor.

Bu üçü aynı bayrağa (`MPTOOL.ini [RDSetting] EnWritePageToAllDie`) bağlı ve elimizdeki
**her iki** MAP1202 paketinde de `EnWritePageToAllDie=1`.

Deneme sırası önerisi (ucuzdan pahalıya, her adımda tek değişken):

1. Mevcut prosedüre **yalnız `0x4D` haritasını** ekle (silmeden önce ve ilk sayfadan önce),
   gerisi aynı kalsın. Tek komut, geri dönülebilir.
2. Silmeyi `FF E5 8B FF FF 00 00 00 00` broadcast formuna çevir (`0x4D`'den sonra).
3. Sayfa yazmayı `0x8A` yerine `0x4C` interleave'e çevir (ch=0, bank=0,
   blk=aLoaderBlockNo[0][0][0], payload düzeni §1 adım 6a).
4. Hâlâ olmuyorsa: sayfaları **tüm** (ch, bank, lb) kopyalarına yazdığından emin ol (F5).

---

## 1. REÇETE — kopyalanabilir adım adım dizi

Notasyon: payload = 512 baytlık **sıfırlanmış** tampon, `[i]` = i'inci bayt.
NVMe taşıma (EnNvmeCmdMode=0, `MPTOOL.ini`'de öyle):

```
faz-1 (komut):  opcode 0xC1, CDW10 = 0x80,       CDW14 = 0x001234FF, CDW15 = 1
                data-out 512 bayt = payload
faz-2 (veri):   opcode 0xC1 (yaz) / 0xC2 (oku),
                CDW10 = nsec<<7, CDW14 = 0x00123400 | <cmd baytı>, CDW15 = nsec
                data = nsec*512 bayt
```
Kanıt: `NVMeVendorCmdWrite` @`0x00405070`:
`0x0040528A: or ecx,0x123400` · `0x0040527C: shl eax,7` · `0x004052A4: cmp ecx,0xff` (faz-1/faz-2 ayrımı) ·
`0x0040529C: mov [eax+0x3c],edx` (CDW15=nsec).
Komut baytı faz-2'ye `VC_Bridge_VendorCmdWrite` @`0x0042D0B4` içinde payload[2]'den alınıyor:
`0x0042D0C0: mov dl,[eax+2]` → `0x0042D0C3: mov [ebp-1],dl`.

### Girdiler
* `MaxPhyChannel` = `MPTOOL.ini [FlashSetting] Channel`  (YENİ: `ds:0x111DA0C`, ESKİ: `ds:0x16F2C36`)
* `MaxPhyBank`    = `MPTOOL.ini [FlashSetting] Bank`     (YENİ: `ds:0x111DA0D`, ESKİ: `ds:0x16F2C37`)
* `plane`         = Flash.ini `PL` sütunu                (YENİ: `ds:0xC36313`, ESKİ: `ds:0xA2FBAB`)
* `ucLdpcMode`    = Flash.ini `ECC` sütunu               (YENİ: `ds:0xC3631A`, ESKİ: `ds:0xA2FBB2`)
* `bPageSector`   = sayfa boyutu/512 (16 KB → 32)        (YENİ: `ds:0xC36310`, ESKİ: `ds:0xA2FBA8`)
* `aLoaderBlockNo[ch][bank][lb]`, `lb ∈ {0,1}` — adım 3'te GDP'den geliyor.

---

```
 1. VC_EnableVendorCmd
    NVMe: opcode 0xC1, CDW14 = 0x00AE34FF, CDW15 = 1, 4096 bayt veri "FF E5 C1 00 .."
    (vendor modunu açar; zaten yapıyorsunuz)

 2. VC_GDP_CmdInitGDP  (0x11)     payload: FF E5 11   + data-out 2 sektör (1024 bayt)
    GDP_INIT_PARAM bloğu:
        [0x00] bVendor      [0x01] bType(cell)   [0x02..03] wBlocks   [0x04..05] wPages
        [0x06..07] wPageSize                     [0x08] bDiePerCE     [0x09] bPlane
        [0x0A] ucLdpcMode   [0x0B] bMode         [0x0C] bMaxChans     [0x0D] bMaxBanks
    (neden: GDP'ye NAND geometrisini verir; bu olmadan blok/sayfa adresleme anlamsız)
    Kanıt ESKİ: builder @0x004069C0-0x00406A7A; VP_InitGDP @0x00436B5C -> 0x00436B9F call 0x42505C
          YENİ: builder @0x00408A3C-0x00408BA6; VP_InitGDP @0x00443B54 -> 0x00443B97 call 0x42DDF8
                0x00443B8E: push 2   <- nsec = 2 sektör

 3. Loader blokları öğren  (VP_PROC_GetLoaderBlock, GDP yolu)
 3a. VC_GDP_CmdPreCheckCodeBlock (0x3A)
        payload: FF E5 3A | [3]=0x00 (mode==0 ise; mode!=0 ise 0x07) | [4]=0x00
        veri fazı YOK
        sonra: Sleep(1000) + VC_GDP_CmdGetReturn döngüsü, buf[0] != 0xAA olana kadar
     Kanıt YENİ: builder @0x0042EDE8 (0x0042EE19: mov byte[ebp-0xffe],0x3a;
                 0x0042EE26: mov byte[ebp-0xffd],0 / 0x0042EE2F: ...,7; 0x0042EE39: [4]=arg2)
                 çağrı @0x0044B3BA (VP_GDP_ExecProg prog==2, arg2=0)
                 GetReturn döngüsü @0x0044B3D4 (push 0x3e8 = Sleep 1000) .. 0x0044B404 cmp edx,0xAA
 3b. VC_GDP_CmdGetCodeBlock (0x07)
        payload: FF E5 07      veri fazı: IN, 1 sektör = 512 bayt
        dönen: buf[ch*4 + bank] = 4 bitlik "sağlam blok" maskesi (fiziksel blok 0..3)
        her (ch,bank) için set bitleri küçükten büyüğe tara, ilk 2 tanesini al:
            aLoaderBlockNo[ch][bank][0], aLoaderBlockNo[ch][bank][1]
        (MPTool 2'den az bulursa hata veriyor)
     Kanıt YENİ: builder @0x0042ED58 (0x0042ED9B: [2]=7; 0x0042EDA9: push 1 = 1 sektör, isRead=1)
                 çağrı @0x0044E933; bit tarama @0x0044EA46-0x0044EB08 (0x0044EAF3: cmp ecx,2)
                 dump "LDR_BLK.raw" @0x0044E959

 4. SİLME — VP_PROC_ClearCodeBlock
    for i = 0 .. (4 / plane) - 1:
        VC_GDP_CmdBlockErase (0x8B)
        payload:  FF E5 8B | [3]=0xFF | [4]=0xFF | [5]=0x00 | [6]=i | [7]=0x00 | [8]=0x00
                  ^ channel  ^ bank     ^ blockHi  ^ blockLo  ^ p4      ^ p5
        veri fazı YOK, payloadLen = 0x0C
        sonra: VC_GDP_CmdGetReturn -> buf[1] == 1 bekle   (0xAA yoklama YOK, tek atış)
    (plane=4 ise TEK komut: FF E5 8B FF FF 00 00 00 00)
    Kanıt ESKİ: VP_PROC_ClearCodeBlock @0x00440458
                0x00440486: push 0xff        <- bank
                0x0044048B: push 0xff        <- channel
                0x0044047C/0x0044047E: push 0 ; push 0   <- p5, p4
                0x00440482: mov dl,[ebp-1] ; push edx    <- block = i
                0x004404AA: mov dl,[0xa2fbab] ; 0x004404B0: mov eax,4 ; idiv  -> döngü 4/plane
          YENİ: VP_PROC_ClearCodeBlock @0x0044D59C, 0x0044D7DD-0x0044D7F8 ve 0x0044D81B-0x0044D836
                (aynı 0xFF/0xFF/i/0/0), döngü 0x0044D849-0x0044D862 (4/[0xc36313])
    Kanıt payload düzeni: VC_GDP_CmdBlockErase @0x0042EAE8
                0x0042EB19: mov byte[ebp-0xffe],0x8b
                0x0042EB23: [3]=arg2(ch)   0x0042EB2C: [4]=arg3(bank)
                0x0042EB32-0x0042EB45: [5]=blk>>8 , [6]=blk&0xFF   (u16, BIG-ENDIAN)
                0x0042EB4E: [7]=arg5(p4)   0x0042EB57: [8]=arg6(p5)
                0x0042EB6A: push 0xc  <- payloadLen; dataBuf=0, dataLen=0 (veri fazı yok)

 5. LOADER BLOCK HARİTASINI GDP'YE YÜKLE  ***BU ADIM BİZDE HİÇ YOK***
    512 baytlık tamponu sıfırla, sonra:
        for ch = 0..7:
          for bank = 0..3:
             (die yoksa atla)
             v0 = aLoaderBlockNo[ch][bank][0];  if v0 != 0xFF: buf[ch*4+bank]  = (1 << v0)
             v1 = aLoaderBlockNo[ch][bank][1];  if v1 != 0xFF: buf[ch*4+bank] |= (1 << v1)
    (yalnız ilk 32 bayt doluyor, kalan 480 bayt 0)
    VC_GDP_CmdInitGDP (0x4D)
        payload: FF E5 4D        veri fazı: OUT, 1 sektör = 512 bayt (yukarıdaki harita)
        ARDINDAN GetReturn ÇAĞRILMIYOR.
    Kanıt ESKİ: VP_DownloadToLoaderBlock @0x0043DDD0 başı:
                0x0043DDE8: cmp byte[0x16f2d0c],0   <- EnWritePageToAllDie
                0x0043DDF5: push 0x200 ; push 0 ; memset(buf,0,512)
                0x0043DE98: mov cx,[ecx+ebx*4]   <- aLoaderBlockNo[..][0]
                0x0043DE9C: mov al,1 ; 0x0043DE9E: shl al,cl
                0x0043DEB0: mov [edx+ecx],al     <- buf[ch*4+bank] = 1<<v0   (ATAMA)
                0x0043DED5..0x0043DEED: ikinci giriş, `or byte[edx+ecx],al`  (VEYA)
                0x0043DF01/0x0043DF04: ch döngüsü 0..7 ; 0x0043DEF8: bank döngüsü 0..3
                0x0043DF1A: push "LDR_BLK_W.raw"  (dump)
                0x0043DF27: push 1 ; 0x0043DF30: call 0x426334  <- InitGDP cmd 0x4D, 1 sektör
          YENİ: aynı blok VP_PROC_ClearCodeBlock içine taşınmış ve **koşulsuz**:
                0x0044D5B8: push 0x200 ; memset
                0x0044D6C3-0x0044D6D7: buf[ch*4+bank] = 1<<v0
                0x0044D72D-0x0044D741: |= 1<<v1
                0x0044D7AC: push "LDR_BLK_W.raw" ; 0x0044D7C2: call 0x42F548 (cmd 0x4D, 1 sektör)
    Kanıt payload: VC_GDP_CmdInitGDP(0x4D) @0x0042F548
                0x0042F579: mov byte[ebp-0xffe],0x4d
                0x0042F589: push [ebp+0x10] (dataLen) ; 0x0042F58C: push [ebp+0xc] (dataBuf)
                0x0042F58F: push 0xc (payloadLen) ; isRead=0 -> OUT

    >>> SIRALAMA NOTU: ESKİ sürümde sıra  4 (silme) -> 5 (0x4D) -> 6 (sayfalar).
        YENİ sürümde sıra  5 (0x4D) -> 4 (silme) -> 6 (sayfalar).
        İki sürüm de 0x4D'yi ilk sayfa yazımından ÖNCE gönderiyor. Emniyetli yol:
        0x4D'yi silmeden önce VE ilk sayfadan önce bir kez daha göndermek.

 6. SAYFA YAZMA
 6a. EnWritePageToAllDie = 1 (fabrika paketlerinin ikisinde de böyle):
     her sayfa için SADECE BİR komut:
        VC_GDP_CmdPageWriteInterleave (0x4C)
        ch   = ilk mevcut kanal (pratikte 0)
        bank = ilk mevcut bank  (pratikte 0)
        blk  = aLoaderBlockNo[ch][bank][lb]
        payload: FF E5 4C | [3]=ch | [4]=bank | [5]=blk>>8 | [6]=blk&0xFF
                          | [7]=page>>8 | [8]=page&0xFF
                          | [9]=mode | [10]=argB(=1) | [11]=0 | [12]=0 | [13]=0
        veri fazı: OUT, nsec*512 bayt
        sonra: VC_GDP_CmdGetReturn -> buf[1]==1
     ESKİ sürüm bunu `lb = 0..ucLoaderBlockNum-1` için tekrarlıyor (yani sayfa başına 2 komut),
     YENİ sürüm yalnız lb=0 için bir kez.
     Kanıt ESKİ: VP_WriteDataToLoaderBlock @0x00437F10
                 0x00437F82: cmp byte[0x16f2d0c],0 ; je 0x438071  <- EnWritePageToAllDie dalı
                 0x00437FD5: blk = aLoaderBlockNo[port][ch][bank][lb]
                 0x00438003: call 0x4379B4 (VP_WritePageInterleave)
                 0x00438016: [ebp-1]=1 ; 0x0043801E/0x00438038: ilk başarıda iki döngüden de çık
                 plain-NVMe dalı: 0x00437C90-0x00437CBC -> call 0x00425804 (0x4C)
                 GetReturn @0x00437CE4
           YENİ: VP_WriteDataToLoaderBlock @0x00444F00, 0x00444F72: cmp byte[0x111daf5],0
                 0x00444FEE: call 0x004449A0 -> 0x00444CA8 call 0x0042E8A8 (0x4C)
     Kanıt payload: VC_GDP_CmdPageWriteInterleave @0x0042E8A8
                 0x0042E8D9: [2]=0x4c
                 0x0042E92C: [10] = arg7  (0x8A'daki ((argA&3)<<2) maskesi YOK)
                 0x0042E935: [11] = arg8
                 0x0042E93E: [12] = [ebp+0x34] ; 0x0042E947: [13] = [ebp+0x30]

 6b. EnWritePageToAllDie = 0 ise (sizin şu anki yaptığınız):
     for lb = 0 .. ucLoaderBlockNum-1:
       for ch = 0 .. MaxPhyChannel-1:
         for bank = 0 .. MaxPhyBank-1:
            blk = aLoaderBlockNo[ch][bank][lb]
            VC_GDP_CmdPageWrite (0x8A)
            payload: FF E5 8A | [3]=ch | [4]=bank | [5]=blk>>8 | [6]=blk&0xFF
                              | [7]=page>>8 | [8]=page&0xFF
                              | [9]=mode | [10]=((argA&3)<<2)|argB | [11]=argC
                              | [12]=argE | [13]=argD
            loader-block yazımlarının HEPSİNDE: argA=0, argB=1, argC=0, argD=0, argE=0
            => [10]=0x01, [11]=0x00, [12]=0x00, [13]=0x00
            veri fazı: OUT, nsec*512 bayt
            sonra: VC_GDP_CmdGetReturn -> buf[1]==1
     Kanıt: VP_WritePage @0x00444420 (YENİ) plain-NVMe dalı 0x00444881-0x004448B1:
            0x00444881: push 0 (argE) · 0x00444883: push 0 (argD) · 0x00444885: push [ebp+0x30] (argA)
            0x00444889: push [ebp+0x2c] (nsec) · 0x0044488C: push [ebp+0x28] (pBuf)
            0x0044488F: push [ebp+0x24] (argC) · 0x00444893: push [ebp+0x20] (argB)
            0x00444897: push [ebp+0x1c] (mode)
            GetReturn @0x004448D9, başarı testi 0x004448EB-0x004448F2 (buf[1]-1 == 0)
     Kanıt payload: VC_GDP_CmdPageWrite @0x0042E7AC
            0x0042E7DD: [2]=0x8a
            0x0042E830-0x0042E83C: [10] = ((byte[ebp+0x30] << 2) & 0x0C) | byte[ebp+0x20]
            0x0042E842: [11]=[ebp+0x24] · 0x0042E84B: [12]=[ebp+0x38] · 0x0042E854: [13]=[ebp+0x34]

 6c. SAYFA SIRASI / mode / nsec  (ESKİ sürüm = sizin diskinizin düzeni)
     mantıksal sayfa -> fiziksel sayfa: wPageNo[] tablosu (Flash.ini PairPage sütunu; P=0 ise özdeşlik)

      idx   ne                       mode          nsec            bayt
      ----  -----------------------  ------------  --------------  -----
      0     InfoPage (LDBK BLOCKS)   0             8               4096
      1     CertPage                 0             8               4096
      2..7  LDPC sayfaları (6 adet)  0             8               4096
      8     SlotPage                 ucLdpcMode    bPageSector     16384
      9..51 Table sayfaları          ucLdpcMode    bPageSector     16384
      52+   Opal sayfaları           ucLdpcMode    bPageSector     16384
      68    NandMem sayfası          ucLdpcMode    bPageSector     16384
      69+   UEFI sayfaları           ucLdpcMode    bPageSector     16384
      91    TMC table sayfası        ucLdpcMode    0x20 (sabit)    16384
      92..  Kod sayfaları (SYS/*.bin) ucLdpcMode   bPageSector     16384
      sonra dummy sayfalar (0xAA dolgu) ucLdpcMode bPageSector     16384

     Kanıt ESKİ: InfoPage @0x0043A883-0x0043A893 (push 0(argA); push 8(nsec); push buf;
                 push 1(argB); push 0(mode); push 0(pageNo); push port)
                 Cert @0x0043AEC9 (pageNo=word[0xa2fbe6]=wPageNo[1], mode=0, nsec=8)
                 LDPC @0x0043A995,AA80,AB6B,AC56,AD41,AE2C (wPageNo[2..7], mode=0, nsec=8)
                 Slot @0x0043B1C7 (wPageNo[8]); Table @0x0043B5D7, döngü [ebp-2]=9..0x33
                    0x0043B5BF: mov dl,[0xa2fbb2] ; push edx   <- mode = ucLdpcMode
                    0x0043B5B4: mov al,[0xa2fba8] ; push eax   <- nsec = bPageSector
                 Opal wPageNo[52+i] @0x0043B87E; NandMem wPageNo[68] @0x0043BA00
                 UEFI wPageNo[69+i] @0x0043BBC5; TMC wPageNo[91] @0x0043BD06
                 Kod sayfaları: VP_WriteCodeToFlash @0x0043D75F
                    0x0043D74F: mov dl,[0xa2fbb2] ; push edx   <- mode = ucLdpcMode

 7. FINALIZE / COMMIT KOMUTU YOK.
    VP_PROC_DownloadProgram @0x0044FF0C (YENİ) / eşleniği (ESKİ) sırası:
       VP_GetTables -> VP_PROC_ClearCodeBlock -> VP_DownloadToLoaderBlock
       -> [EnSecondDownload ise: EnableVendorCmd + ClearCodeBlock + DownloadToLoaderBlock tekrar]
       -> VP_UploadCodeFromFlash (yalnız geri OKUMA, 0x89)
       -> VP_PROC_Check_Code_Block_Info (yalnız doğrulama)
    Yazma sonrası 0x3A / 0x07 / 0x4C / başka bir "commit" gönderilmiyor.
    Kanıt: 0x00450007 (ClearCodeBlock), 0x00450051 (Download), 0x00450063 (EnSecondDownload
           bayrağı 0x111d12d), 0x00450166 (UploadCodeFromFlash), 0x00450184 (Check_Code_Block_Info).
```

---

## 2. Bizim prosedürden farklar — madde madde

| # | Bizim yaptığımız | MPTool'un yaptığı | Kanıt |
|---|---|---|---|
| **F1** | `0x4D` hiç gönderilmiyor | Yazmadan önce **512 baytlık loader-block bitmask haritası** `FF E5 4D` + 1 sektör OUT ile gönderiliyor. `buf[ch*4+bank] = (1<<lb0) \| (1<<lb1)`, geri kalan 480 bayt 0. | ESKİ `0x0043DDF5`–`0x0043DF35`; YENİ `0x0044D5B8`–`0x0044D7C7` |
| **F2** | Silme: her die için gerçek `ch/bank/blk`, `p4/p5` = 0/1 ya da 1/1 | Silme: **`ch=0xFF, bank=0xFF, block=i, p4=0, p5=0`**, `i = 0..(4/plane)-1`. Gerçek blok numarası GÖNDERİLMİYOR; blok bilgisi `0x4D` haritasından geliyor. | ESKİ `0x00440479`–`0x004404C1`; YENİ `0x0044D7DD`–`0x0044D862` |
| **F3** | `p4=1,p5=1` denemesi | `p4=1,p5=1` **download yolunda hiç kullanılmıyor**. O kombinasyon yalnız `VP_PROC_EraseValidLoaderBlock` (UI'dan çağrılan, `ch/bank/blk` = 0..7/0..3/0..3 üçlü döngüsü) içinde var ve `VP_PROC_DownloadProgram`'dan çağrılmıyor. | YENİ `0x004524A0` (`0x004524CC: push 1` / `0x004524CE: push 1`), tek çağıran `0x004D35AC`. ESKİ `0x004432AC` (`0x004432FC: push 1` / `0x004432FE: push 1`), tek çağıran `0x004AAD92` — ikisinde de `VP_PROC_DownloadProgram` çağırmıyor. |
| **F4** | Her sayfa `0x8A` ile tek tek die'a | `EnWritePageToAllDie=1` iken sayfa başına **tek `0x4C` PageWriteInterleave**; ch=0, bank=0, blk=aLoaderBlockNo[0][0][lb]. Denetleyici sayfayı `0x4D` haritasındaki tüm die'lara kendisi yazıyor. | ESKİ `0x00437F82` (bayrak), `0x00438003`→`0x004379B4`→`0x00437CBC`→`0x00425804`; paket `MPTOOL.ini` satır 354 `EnWritePageToAllDie=1` |
| **F5** | Tek kopya yazılıyor (muhtemelen) | `EnWritePageToAllDie=0` yolunda bile MPTool her sayfayı **bütün** `(lb, ch, bank)` üçlüleri için yazıyor — yani her kanal × her CE × `ucLoaderBlockNum` (≤2) kopya. Sayfa-öncelikli sıra: sayfa N tüm kopyalara yazılır, sonra sayfa N+1. | YENİ `0x00445041`–`0x00445213` (3'lü döngü: lb `[ebp-7]`, ch `[ebp-8]`, bank `[ebp-9]`) |
| **F6** | `[10] = 1` | Aynı: `[10] = ((argA&3)<<2) \| argB` ve loader-block yazımlarının hepsinde `argA=0, argB=1` → `0x01`. **Fark yok.** | `0x0042E830`–`0x0042E83C`; tüm çağrı yerlerinde `push 1` (argB), `push 0` (argA) |
| **F7** | `[11]=0, [12]=0, [13]=0` | Aynı. `argC` `VP_WriteDataToLoaderBlock`→`VP_WritePage` geçişinde sabit `0` (`0x00445118: push 0`), `argD/argE` plain-NVMe dalında sabit `0` (`0x00444881`, `0x00444883`). **Fark yok.** | — |
| **F8** | `mode`: sayfa 0–7 → 0, 8+ → 2 | ESKİ sürüm birebir aynı (0 ve `ucLdpcMode`=Flash.ini ECC). **Fark yok.** YENİ sürüm 0–10 → 0, 11+ → sabit `1`. | ESKİ `0x0043B5BF: mov dl,[0xa2fbb2]`; YENİ `0x00447A63: push 1` |
| **F9** | `nsec`: ? | İlk 8 sayfa **8 sektör (4096 bayt)**, sonrakiler `bPageSector` (16 KB için 32). TMC sayfası sabit `0x20`. | ESKİ `0x0043A885: push 8`; `0x0043B5B4: mov al,[0xa2fba8]`; YENİ TMC `0x00448293: push 0x20` |
| **F10** | Boş sayfa bırakma / atlama | MPTool **hiçbir sayfayı atlamıyor.** Kod sayfaları bittikten sonra tamponu `0xAA` ile doldurup dummy sayfa yazmaya devam ediyor: sayfa indeksi 24'ün katına gelene kadar + 24 sayfa daha. "Erased kalan 37 sayfa" bu dolgunun bittiği yerden sonrası. | YENİ `VP_WriteCodePage` @`0x0044A9AF`–`0x0044AB15`: `0x0044A9CE: push 0xaa` (memset), `0x0044AA38: mov ecx,0x18` / `0x0044AA40: cmp edx,0x17`, son `0x0044AB12: cmp edx,0x18` |
| **F11** | Silme sonrası bekleme | `0x8B` sonrası `Sleep(10)` + **tek** `GetReturn`; `buf[0]==0xAA` yoklaması YOK, doğrudan `buf[1]==1` isteniyor. (`0x3A`/`0x02` prog komutlarında ise `Sleep(1000)` + `buf[0]!=0xAA` döngüsü var — farklı mekanizma.) | YENİ `0x00444E37: push 0xa; call Sleep`, `0x00444E4D: call GetReturn`, `0x00444E5B-0x00444E62: buf[1]-1 == 0` |
| **F12** | `0x11 InitGDP` payload'ı | `FF E5 11` + **2 sektör (1024 bayt)** `GDP_INIT_PARAM`; içinde `bPlane` (+0x09) ve `ucLdpcMode` (+0x0A) var. GDP'nin süper-blok/plane davranışı buradan geliyor; bu blok yanlışsa `0x8B FF FF ...` broadcast'i yanlış geometride siler. | YENİ `0x00443B8E: push 2`; builder `0x00408A3C`–`0x00408BA6` |
| **F13** | `0x8A` payloadLen | ESKİ sürüm `payloadLen = 0x0C` gönderiyor (12 bayt), YENİ sürüm `0x1000`. Telde ikisi de 512 bayt taşıdığı için **davranış farkı yok** ([12]/[13] zaten 0). | ESKİ `0x004257CE: push 0xc`; YENİ `0x0042E86C: push 0x1000` |

---

## 3. Sorulara tek tek cevap

### 3.1 Yazmadan önce hangi hazırlık komutları gidiyor?

Download akışının tamamı (`VP_PROC_DownloadProgram` @`0x0044FF0C` YENİ):

```
[daha önce, ana MP akışında]
  VP_WriteCodeToMemNew2   -> 0x87 VC_LDR_CmdWriteRam ile GDP.bin'i SRAM'e
  VP_JumpToLoader/PRAM    -> 0x82
  VP_InitGDP              -> 0x11 + 1024 bayt GDP_INIT_PARAM        <- var
  VP_PROC_CheckFlashModule-> 0x88 ReadFlashID / 0x05 GetFlashModule
  VC_GDP_CmdSwitchToLegacy-> 0x49
  VP_PROC_GetLoaderBlock  -> 0x3A PreCheckCodeBlock + 0x07 GetCodeBlock   <- var
  VP_PROC_Preformat       -> 0x02 ScanDefectBad + 0x31 GetDefectBadTab
  VC_GDP_CmdEraseSPI      -> 0x0A
  VP_PROC_EraseAllBlock   -> sorting sonuç bloklarını siler (0x8B, ch/bank gerçek, p4=0 p5=1)
[VP_PROC_DownloadProgram]
  VP_GetTables                (host tarafı, komut yok)
  VP_PROC_ClearCodeBlock      -> 0x4D harita + 0x8B broadcast silme     <- KRİTİK
  VP_DownloadToLoaderBlock    -> sayfalar
  VP_UploadCodeFromFlash      -> 0x89 geri okuma
  VP_PROC_Check_Code_Block_Info
```

* **`0x4D` bitmask haritası: VAR.** Ayrıntı ve payload → reçete adım 5. 512 baytın
  yalnız ilk 32'si kullanılıyor: `buf[ch*4 + bank]`, alt 4 bit = fiziksel blok 0..3 için
  "bu bir loader block" bayrağı. `0x07 GetCodeBlock`'un döndürdüğü formatın **aynısı**,
  ters yönde.
* **`0x11` InitGDP: VAR**, ama download'dan çok önce, GDP'ye atlarken bir kez.
  Payload `FF E5 11` + 1024 bayt parametre bloğu.
* **`0x3A` PreCheckCodeBlock: VAR** — `FF E5 3A 00 00`, `VP_PROC_GetLoaderBlock` içinde,
  `0x07`'den hemen önce. Ardından `Sleep(1000)` + `GetReturn` döngüsü (`buf[0] != 0xAA`).
* **`0x07` GetCodeBlock: VAR** — `FF E5 07`, IN 512 bayt; `aLoaderBlockNo` bundan doluyor.

Bu ikisi (`0x3A`+`0x07`) yazma için zorunlu değil *ama* `0x4D` haritasının içeriğini üretiyorlar.
Eğer blok numaralarını başka yoldan biliyorsanız haritayı elle kurabilirsiniz.

### 3.2 Silme tam olarak nasıl?

```
FF E5 8B | [3]=0xFF | [4]=0xFF | [5]=0x00 | [6]=i | [7]=0x00 | [8]=0x00
```
* `[3]`/`[4]` = `0xFF` → **broadcast**, tüm kanal/CE.
* `[5..6]` = 16-bit **big-endian** ve burada gerçek fiziksel blok numarası **değil**,
  `i = 0..(4/plane)-1` sayacı. `plane=4` için tek komut, `i=0`.
* `[7]`/`[8]` = 0/0.
* Veri fazı yok, `payloadLen = 0x0C`.

`[5..6]`'nın "blok mu satır mı" sorusu: **fonksiyon imzası blok numarası** (`VP_EraseBlock`'un
4. argümanı `u16 blk`, `VC_GDP_CmdBlockErase` bunu `[5]=blk>>8, [6]=blk&0xFF` yapıyor —
`0x0042EB32: movzx eax,word[ebp+0x14]` / `0x0042EB36: sar eax,8`). Satır (row) adresi
hesaplaması host tarafında **yok**. Ama download yolunda gönderilen değer fiziksel blok
numarası değil, `4/plane` döngü sayacı. Bu değerin GDP içinde "süper-blok indeksi"ne mi
karşılık geldiğini **host binary'sinden kanıtlayamadım** — GDP (ARM) tarafındaki `0x8B`
işleyicisini bulamadım (`c1.bin` içinde `cmp rX,#0x8b` / `sub rX,#0x8b` deseni komut
dağıtıcısına götürmedi; dispatcher tablo tabanlı görünüyor). **`p4`/`p5` baytlarının
semantiği: bulamadım.** Kesin olan tek şey: download yolu `0/0`, tek-blok UI yolu `1/1`,
sorting-sonuç blokları `0/1`.

### 3.3 `0x8A` alan alan hangi sayfada hangi değer?

Loader-block yazımlarının **hepsinde** aynı:

```
[9]  = mode   : sayfa 0..7 -> 0 ,  sayfa 8+ -> ucLdpcMode (Flash.ini ECC; sizin diskte 2)
[10] = 0x01   : ((argA & 3) << 2) | argB , argA = 0 ve argB = 1 (istisnasız)
[11] = 0x00   : argC, VP_WriteDataToLoaderBlock -> VP_WritePage geçişinde sabit 0
[12] = 0x00   : argE, plain-NVMe dalında sabit 0
[13] = 0x00   : argD, plain-NVMe dalında sabit 0
```

**`argE`'nin 1 olduğu yer loader-block yazımında YOK.** `argE=1`/`argD=0` yalnız
`EnNvmeCmdMode != 0` (USB-bridge / miniport) dalında ve orada da `nsec` sabit `8` ile
kullanılıyor (`0x004444B8: push 1` / `0x004444BA: push 0` / `0x004444C0: push 8` —
`VP_WritePage`'in bridge dalı). NVMe yolunda o dal çalışmıyor. Yani bizim gönderdiğimiz
`[10]=1, [11]=0, [12]=0, [13]=0` **doğru**; burada hata yok.

`nsec` (veri fazı uzunluğu) sayfa tipine göre değişiyor: 8 sektör (sayfa 0..7),
`bPageSector` (sayfa 8+), `0x20` (TMC sayfası).

### 3.4 Yazma sırası ve `GetReturn`

Sıra (ESKİ sürüm, sizin diskin düzeni):

```
VP_Cougar_FillInfoPage   -> sayfa 0            (mode 0, 8 sektör)   hata kodu 0xA0
VP_WriteCertPage         -> wPageNo[1]         (mode 0, 8 sektör)
VP_Cougar_WriteLdpcPage  -> wPageNo[2..7]      (mode 0, 8 sektör)   hata kodu 0xA1
  (ToolMode==0 ise)
  VP_WriteSlotPage       -> wPageNo[8]
  VP_WriteTablePage      -> wPageNo[9..51]                          hata kodu 0xA2
  VP_WriteOpalPage       -> wPageNo[52+i]                           hata kodu 0xA3
  VP_WriteNandMemPage    -> wPageNo[68]                             hata kodu 0xA4
  VP_WriteUefiPage       -> wPageNo[69+i]                           hata kodu 0xA5
  VP_WriteTMCTablePage   -> wPageNo[91]                             hata kodu 0xA6
  (ToolMode==1 ise onun yerine VP_WritePatternPage)
VP_WriteCodePage         -> wPageNo[92..]  SYS/*.bin kod sayfaları  hata kodu 0xA6
dummy sayfalar (0xAA)
```

Her sayfa yazımından sonra:

```
VC_GDP_CmdGetReturn :  FF E5 00 , veri fazı IN 1 sektör (512 bayt)
    dönüş != 0  ve  buf[1] == 1  -> başarı ("Write C:%d B:%d Block:%d Page:%d Success!")
    buf[1] != 1                  -> hata, 512 bayt "Status Fail" olarak dump ediliyor
```
`buf[0] == 0xAA` (meşgul) yoklaması sayfa/silme yolunda **yapılmıyor**; yalnız
`VP_GDP_ExecProg` (0x02/0x3A) ve `VP_GetProgramLoop` yollarında var.
Kanıt: `VC_GDP_CmdGetReturn` @`0x0042DE78` (`0x0042DEBB: [2]=0x00`, `0x0042DEC9/CB: push 1; push 1`
= 1 sektör IN); test `0x0044467B-0x00444684`.

### 3.5 Yazma bittikten sonra finalize/commit var mı?

**Yok.** `VP_DownloadToLoaderBlock` son dummy sayfadan sonra doğrudan dönüyor
(`0x0044B038: mov al,1 ; ret`). Sonrasında yalnız okuma/doğrulama:
`VP_UploadCodeFromFlash` (0x89) ve `VP_PROC_Check_Code_Block_Info`. `0x3A`, `0x07`, `0x4C`
veya başka bir komut **gönderilmiyor**.

ESKİ sürümde de aynı: `VP_PROC_DownloadProgram` @`0x00441ED4` →
`0x00441F8F` VP_GetTables → `0x00441FA7` VP_PROC_ClearCodeBlock → `0x0044203E`
VP_DownloadToLoaderBlock → `0x00442062` VP_UploadCodeFromFlash → `0x00442080`
VP_PROC_CheckDPDPara → `0x0044209E` VP_CheckCodeBlockFromFlash. Yazma sonrası komut yok.

Tek istisna: `MPTOOL.ini [Setting] EnSecondDownload != 0` ise tüm dizi bir kez daha
tekrarlanıyor (EnableVendorCmd → ClearCodeBlock → DownloadToLoaderBlock).
Kanıt `0x00450061: cmp byte[0x111d12d],0` ; anahtar adı `0x0043492D: push "EnSecondDownload"`.

### 3.6 Boş bırakılan sayfalar hangileri, karar nasıl veriliyor?

MPTool **hiçbir sayfayı bilerek boş bırakmıyor.** Kod sayfalarından sonra tamponu
`0xAA` ile doldurup dummy sayfa yazıyor:

```
p = son kod sayfasından sonraki mantıksal sayfa
while ((p - 1) % 24) != 23:            # yani p, 24'ün katı olana kadar
    write dummy(wPageNo[p]); p++
    if (p % 24) == 23: write dummy(wPageNo[p]); p++
for k in 0..23: write dummy(wPageNo[p + k])
```
Yani blok, 24 sayfalık gruba hizalanana kadar + tam bir 24 sayfalık grup daha
`0xAA` ile dolduruluyor; bundan sonrası erased kalıyor.
Kanıt: `0x0044A9CE: push 0xaa` (memset), `0x0044AA38: mov ecx,0x18` / `0x0044AA40: cmp edx,0x17`,
`0x0044AB12: cmp edx,0x18`.

Ayrı bir özel durum (YENİ sürüm, `N4PA`/`N38B` flash + `[Setting] EnCodeBlockWriteAllPage != 0`):
info page'den **önce** bloğun üst 2/3'ü `0xAA` ile programlanıyor —
önce `[2N/3 .. N-1]`, sonra `[N/3 .. 2N/3-1]`, `N = wPages / (1,2,3,4 hücre tipine göre)`, `mode=1`.
Kanıt `VP_DownloadToLoaderBlock` @`0x0044AB3D`–`0x0044AD34`; bayrak `0x0044AB71: cmp byte[0x1137246],0`,
anahtar adı `0x004349BA: push "EnCodeBlockWriteAllPage"`.
Hynix V7/V8 için bu dal çalışmıyor.

---

## 4. Yan bulgular (işe yarayabilir)

* **`EnWritePageToAllDie` tek bayrak, üç davranışı birden açıyor** (`[RDSetting]`,
  ESKİ `ds:0x16F2D0C` @`0x0042CDF1`, YENİ `ds:0x111DAF5` @`0x00437079`):
  `0x4D` haritası + `0x4C` interleave yazma. Elimizdeki iki MAP1202 paketinde de `=1`.
* **`ToolMode`** (`[Setting]`, YENİ `ds:0x111D0C7` @`0x00434529`): `0` = normal MP,
  `1` = SORT/RDT (pattern page yolu). HYV7 paketinde `ToolMode=1`, SKV8 paketinde `0`.
* **`MKSSD` imzasının yeri sürüme göre değişmiş**: ESKİ sürüm `+0x1C0`'a bakıyor,
  YENİ sürüm SYS için `+0xC0`, RDT (`MKRDT`) için `+0x1C0`.
  Kanıt YENİ `0x0044CF99: add ecx,0xc0` (MKSSD) vs `0x0044CFE8: add edx,0x1c0` (MKRDT).
* **Loader block havuzu sabit: fiziksel blok 0..3**, her (kanal, CE) için en fazla **2** tanesi
  kullanılıyor (`0x0044EAF3: cmp ecx,2`). `MPTCodeBlkThreshold` (`ds:0x111E0E9`) 0 ise her die'da
  2 sağlam blok şart.
* **Bank/LUN kodlaması**: `bank >= MaxPhyBank` ise `bank = ((bank/MaxPhyBank) << 4) | (bank % MaxPhyBank)`
  (üst nibble = LUN). `bank == 0xFF` ise bu dönüşüm atlanıyor.
  Kanıt `VP_EraseBlock` `0x00444DC4: cmp edx,0xff ; je`, `0x00444DE7`–`0x00444E02`.
* **`VP_WriteDataToLoaderBlock` sayfa-öncelikli yazıyor**: bir sayfa bütün kopyalara
  (lb × ch × bank) yazıldıktan sonra sonraki sayfaya geçiliyor.
* **`EnReadBackAfterWrite`** benzeri bayrak `ds:0xC37034`: 1 ise her sayfa yazımından sonra
  `0x89` ile geri okuyup `R_CP_%d_%d_%d_%04d.raw` dump ediliyor (`0x0044517C`).

---

## 5. Bulamadıklarım (dürüst liste)

* **`0x8B`'nin `[7]`/`[8]` (p4/p5) baytlarının anlamı.** Host binary'sinde isim yok, GDP
  (ARM, `re/gdp/c1.bin`) içindeki `0x8B` işleyicisini bulamadım — komut dağıtıcı immediate
  karşılaştırma kullanmıyor, tablo tabanlı görünüyor. Elde sadece kullanım deseni var:
  download `0/0` + `ch/bank=0xFF`, tek-blok UI silme `1/1` + gerçek `ch/bank/blk`,
  sorting-sonuç bloğu `0/1` + gerçek `ch/bank/blk`.
* **`0x4D` haritasının GDP içinde tam olarak neyi değiştirdiği.** Host tarafında sadece
  "gönderiliyor" kanıtı var; GDP'nin bunu `0x8B FF FF` broadcast'i ve `0x4C` interleave
  yazması için kullandığı çıkarımı davranışsal (aynı bayrağa bağlı olmaları), disasm'dan
  kanıtlanmadı.
* **YENİ sürümün veri sayfalarında `mode`'u neden sabit `1` yaptığı.** `ucLdpcMode`
  globali (`ds:0xC3631A`) hâlâ Flash.ini ECC'den doluyor ve GDP init param'a (+0x0A)
  yazılıyor, ama sayfa yazıcıları onu kullanmıyor (`0x00447A63: push 1`). Bir build
  tercihi mi, GDP'de anlamın değişmesi mi — çözemedim. **Sizin diskiniz için ESKİ sürümün
  davranışı (`0` / `ucLdpcMode=2`) geçerli; ölçümünüzle de uyuyor.**
* **`VP_WriteCertPage`'in içeriğini üreten kod** (blob `ds:0xA31694`/YENİ karşılığı) —
  önceki raporda da bulunamamıştı, bu turda da bulamadım.
* **`VP_PROC_EraseValidLoaderBlock`'un download akışında çağrıldığı bir yer** — YENİ
  binary'de `0x004524A0`'ın tek çağıranı `0x004D35AC` (ayrı bir bakım fonksiyonu),
  ana MP akışında yok.

---

## 6. Yeniden üretme (analiz araçları)

Bu raporun bütün adresleri şu araçlarla üretildi (geçici dizinde, projeye yazılmadı):

```
/tmp/.../scratchpad/mpt/pe.py       PE32 parser + vma<->file
/tmp/.../scratchpad/mpt/strs.py     string tablosu
/tmp/.../scratchpad/mpt/idx.py      immediate + ham dword xref indeksi
/tmp/.../scratchpad/mpt/fnames.py   debug format string'lerinden fonksiyon adı haritası (140 ad)
/tmp/.../scratchpad/mpt/dd.py       capstone disasm + string/isim şerhi
/tmp/.../scratchpad/mpt/callers.py  E8 call xref
/tmp/.../scratchpad/mpt/args2.py    çağrı yerindeki push dizisini çözer
/tmp/.../scratchpad/old/            aynı araçlar, V0_01_017 için
```

Fonksiyon adresi eşlemesi (YENİ / ESKİ):

| fonksiyon | V1_1_26 | V0_01_017 |
|---|---|---|
| `VP_PROC_DownloadProgram` | `0x0044FF0C` | `0x00441ED4` |
| `VP_PROC_ClearCodeBlock` | `0x0044D59C` | `0x00440458` |
| `VP_DownloadToLoaderBlock` | `0x0044AB20` | `0x0043DDD0` |
| `VP_WriteDataToLoaderBlock` | `0x00444F00` | `0x00437F10` |
| `VP_WritePage` | `0x00444420` | `0x00437434` |
| `VP_WritePageInterleave` | `0x004449A0` | `0x004379B4` |
| `VP_EraseBlock` | `0x00444D98` | `0x00437DAC` |
| `VP_ReadPage` | `0x00443DF4` | `0x00436DF0` |
| `VP_PROC_GetLoaderBlock` | `0x0044D9AC` | `0x004404C8` |
| `VP_PROC_EraseValidLoaderBlock` | `0x004524A0` | `0x004432AC` |
| `VP_GDP_ExecProg` | `0x0044B344` | `0x0043E78C` |
| `VC_GDP_CmdPageWrite (0x8A)` | `0x0042E7AC` | `0x00425710` |
| `VC_GDP_CmdPageWriteInterleave (0x4C)` | `0x0042E8A8` | `0x00425804` |
| `VC_GDP_CmdBlockErase (0x8B)` | `0x0042EAE8` | `0x00425A40` |
| `VC_GDP_CmdInitGDP (0x11)` | `0x0042DDF8` | `0x0042505C` |
| `VC_GDP_CmdInitGDP (0x4D)` | `0x0042F548` | `0x00426334` |
| `VC_GDP_CmdGetReturn (0x00)` | `0x0042DE78` | `0x004250D8` |
| `VC_GDP_CmdGetCodeBlock (0x07)` | `0x0042ED58` | `0x00425C9C` |
| `VC_GDP_CmdPreCheckCodeBlock (0x3A)` | `0x0042EDE8` | `0x00425D2C` |
| `VC_Bridge_VendorCmdWrite` | `0x0042D0B4` | `0x004244E4` |
| `NVMeVendorCmdWrite` | `0x00405070` | `0x00403884` |
