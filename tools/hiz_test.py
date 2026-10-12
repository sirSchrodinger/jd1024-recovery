import sys, time, hashlib
sys.argv = [sys.argv[0], "x"]
sys.path.insert(0, "~/jd1024/port")
import jmsgdp as J
d = J.jdisk.JDisk(gdprun_gerekirse=False)
J.P("JDisk hazir, tur=%s" % d.tur)
for (ch, ce) in ((0, 0), (3, 2)):
    for blok in (200, 1000, 2500):
        t0 = time.time(); v = d.oku(blok, 0, ch, ce, 0xC3); t1 = time.time(); d.abort(); t2 = time.time()
        tur = "OKUNAMADI" if v is None else ("FF(silinmis)" if v.count(0xFF) > 16000 else ("00" if v.count(0) > 16000 else "VERI " + hashlib.sha256(v).hexdigest()[:8]))
        J.P("c%dce%d blok %4d p0: %-22s oku %.3fs abort %.3fs" % (ch, ce, blok, tur, t1 - t0, t2 - t1))
