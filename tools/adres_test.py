#!/usr/bin/env python3
"""adres_test.py -- READ-ONLY: which DPD addresses all 2888 blocks instead of wrapping at 1024?

With dpd_v3 (+0x18=0x0a) block b and b+1024 are the same physical block (measured 24 Sep:
die 0 page 0  b200=875398fb  b452=fdf079fa  b1000=7c71ebee, and 1224/2248 == 200, 1476/2500 == 452).
Candidate here: dpd_y5_b12_p9 (+0x18=0x0c block bits, +0x19=0x09 page bits kept: TLC 1536 pages
= 512 wordlines x 3, so 9 page bits is correct; the earlier y1 test also changed page bits and
shifted the whole address).
A correct DPD must reproduce the low-block reference hashes AND give 1224/2248/1476/2500 their own
values. Reading alone cannot prove it if high blocks happen to be erased (identical pattern), so the
raw hashes are printed; a write test follows only if needed.

  sudo python3 adres_test.py [dpd_file ...]      default: dpd_y5_b12_p9.bin
"""
import hashlib, sys
DPDLER = [a for a in sys.argv[1:] if a.endswith(".bin")] or ["dpd_y5_b12_p9.bin"]
sys.argv = [sys.argv[0], "x"]
sys.path.insert(0, "~/jd1024/port")
import jmsgdp as J

REF = {200: "875398fb", 452: "fdf079fa", 1000: "7c71ebee"}
BLOKLAR = [200, 452, 1000, 1224, 1476, 2024, 2248, 2500, 2263, 2855, 2887]

mn = J.kimlik()
if mn is None: sys.exit("Identify yok")
if "GDP" not in mn and not J.gdprun(): sys.exit("gdprun basarisiz")
for dpd in DPDLER:
    d = J.jdisk.JDisk(dpd=dpd, gdprun_gerekirse=False)
    J.P("--- %s  tur=%s ---" % (dpd, d.tur))
    h = {}
    for b in BLOKLAR:
        v = d.oku(b, 0, 0, 0, 0xC3); d.abort()
        h[b] = "yok" if v is None else hashlib.sha256(v).hexdigest()[:8]
    for b in BLOKLAR:
        not_ = ""
        if b in REF: not_ = "ref %s %s" % (REF[b], "OK" if h[b] == REF[b] else "FARKLI")
        elif b - 1024 in h or b - 2048 in h:
            alt = b - 1024 if b - 1024 in h else b - 2048
            not_ = "== blok %d (sariyor)" % alt if h[b] == h[alt] else "!= blok %d" % alt
        J.P("  blok %4d: %s   %s" % (b, h[b], not_))
    alt_ok = all(h[b] == REF[b] for b in REF)
    ayri = sum(1 for b in (1224, 1476, 2248, 2500) if h[b] != h[b - 1024 * (1 if b < 2048 else 2)])
    J.P("  => dusuk bloklar referansla ayni: %s | yuksek bloklardan ayri okunan: %d/4" % (alt_ok, ayri))
