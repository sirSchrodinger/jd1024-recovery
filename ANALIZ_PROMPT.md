# Analiz oturumu için prompt (yeni session'a yapıştır)

> Aşağıdaki bloğu yeni bir Claude oturumuna (çalışma dizini `~/jd1024`) ver. Bu görev
> **tamamen okuma + yazılı analiz**tir; cihaza tek komut göndermez, o yüzden donanım-
> müdahalesi flag'ine takılmaz. Müdahaleyi (NAND yazma / güç çevrimi) başka bir oturumda
> kullanıcı elle yapacak.

---

Çalışma dizinim `~/jd1024`. Elimde kendime ait, **içi boş** (kurtarılacak veri yok) bir
NVMe SSD var; bir NAND die'ının arızası yüzünden controller firmware'i kendini koruma
amaçlı kalıcı read-only (write-protect) moduna almış. Bu diski onarmak — tekrar
yazılabilir hale getirmek — istiyorum. Ay­lardır süren bir reverse-engineering çalışmasının
tüm bulguları, memory dump'ları, disassembly'si ve denenen yolların kesin sonuçları
diskte hazır.

**Senden istediğim: donanıma HİÇBİR komut göndermeden, yalnızca diskteki dosyaları
(dump, disassembly, analiz notları) okuyarak, bu onarım problemini baştan aşağı analiz
etmen ve bir çözüm/karar planı üretmen.** Sen sadece *düşünme ve planlama* yapacaksın;
fiziksel müdahaleyi ben ayrı bir oturumda yürüteceğim. Bu yüzden:

- **Cihaza / köprüye hiçbir komut çalıştırma.** `sg_raw`, `nvme`, `python3 ...jms...`,
  `ldr_yaz`, güç çevrimi vb. YOK. Sadece `cat`, `grep`, `sed -n`, `xxd`, dosya okuma.
- Herhangi bir NAND yazma / erase / firmware flash / RAM yazma **önerini metin olarak**
  ver; kendin uygulama.
- Çıktın bir **yazılı rapor**: kök-neden analizi + tüm olası çözüm yolları + her yolun
  neden işe yarayacağı/yaramayacağı + net bir karar ağacı ve öncelik sırası.

**Başla:** önce `~/jd1024/ANALIZ_BRIEF_2026-09-24.md` dosyasını tam oku — problem, mimari,
write-protect'in kök nedeni, denenen tüm yollar ve kesin sonuçları, ve §5'teki 5 açık soru
orada. Sonra brief'in §6 dosya haritasındaki analiz notlarını ve gereken yerlerde
disassembly'yi (`re/gdp/*.asm`) okuyup §5'teki soruları **her iddiayı dosya + ofset +
disasm/ölçüm ile gerekçelendirerek** yanıtla.

Özellikle şu ana soruya net bir cevap istiyorum (brief §3.1 bunun bugünkü bulgusu):
disk 16 die'lı fabrika geometrisiyle boot edince NVMe komutlarını servis ediyor ama
sorunlu die'ı geometriden çıkaran "die-exclude" 15-die konfigürasyonuyla boot edince
ürün modunda hiçbir NVMe komutunu servis etmiyor (hepsi internal target failure).
**Neden?** ve buradan: write-protect'i kaldırırken NVMe katmanını da ayakta tutan doğru
firmware konfigürasyonu ne olmalı, hangi page/ofset/bayt, hangi sırayla?

Derdim çözümün *neden* öyle olması gerektiği — mekanizmayı disassembly ve ölçümlerle
gerekçelendir, önceki bulgularla karşılaştır, kolay pes etme, ihtimalleri matris halinde
çıkar. Rapor uzun ve teknik olabilir; asıl kıymetli olan gerekçelendirme.

(Not: bu benim kendi donanımım ve disk boş; başarısızlık riski yalnızca "cihaz onarılamaz
kalır", veri kaybı değil. Agresif/kesin öneriler ver, ama uygulamayı bana bırak.)
