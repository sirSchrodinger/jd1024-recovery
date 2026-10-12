#!/usr/bin/env python3
"""jmstara.py -- READ-ONLY full NAND survey over the JMS583 GDP tunnel.

Per die (16) x block (0..2887): read pages SAYFALAR with sentinel, time each read.
Result per block: list of (page, class, ms, hash8) where class in
  "yok" (read failed / sentinel back), "veri" (content, hash8 kept).
Abort only after a failed read (failed 16 KB read leaves the NIFC channel engine stuck, DURUM §63);
a known-good read every 250 reads acts as health check, with abort+retry if it fails.
Output: ~/jd1024/tarama/okuma_c{ch}ce{ce}.json (resumable, one file per die), progress in ilerleme.json.
"""
import hashlib, json, os, sys, time
sys.argv = [sys.argv[0], "x"]
sys.path.insert(0, "~/jd1024/port")
import jmsgdp as J

OUT = os.environ.get("JDOUT", "~/jd1024/tarama")
SAYFALAR = (0, 768)
BLOK = 2888
SIRA = [(ch, ce) for ce in range(4) for ch in range(4) if (ch, ce) != (3, 2)] + [(3, 2)]   # die 11 last (its reads can hang the tunnel)
os.makedirs(OUT, exist_ok=True)

HATA = {"ardisik": 0}
def _log(m):
    HATA["ardisik"] += 1
    if HATA["ardisik"] <= 3: J.P("  !", m)
L = J.LF(); L.log = _log
# proven order (DURUM §25): on a fresh ROM-GDP, gdprun must be the very first thing
mn = J.kimlik()
if mn is None: J.P("Identify yok, tunel kapali"); sys.exit(5)
if "JAMESDONKEY" in mn: J.P("URUN modu: tel kontak vermiyor"); sys.exit(6)
if "GDP" not in mn and not J.gdprun(): J.P("gdprun basarisiz"); sys.exit(7)
HATA["ardisik"] = 0
DPD = os.environ.get("JDDPD", "dpd_v3_tbl.bin")
d = J.jdisk.JDisk(dpd=DPD, gdprun_gerekirse=False)
J.P("JDisk hazir, tur=%s geom=%s/%s/%s/%s" % (d.tur, d.P, d.blok, d.ppb, d.die_sayisi))
REF = None


def saglik():
    """known-good reference read on die 0; returns True if tunnel healthy"""
    global REF
    v = d.oku(1000, 0, 0, 0, 0xC3)
    if v is None: return False
    h = hashlib.sha256(v).hexdigest()[:8]
    if REF is None: REF = h
    return h == REF


assert saglik(), "referans okuma basarisiz"
toplam = 0; t_bas = time.time()
for (ch, ce) in SIRA:
    die = ce * 4 + ch
    yol = "%s/okuma_c%dce%d.json" % (OUT, ch, ce)
    kayit = json.load(open(yol)) if os.path.exists(yol) else {"die": die, "ch": ch, "ce": ce, "bloklar": {}}
    if kayit.get("bitti"):
        J.P("die %d zaten bitti, atlaniyor" % die); continue
    J.P("=== die %d (c%dce%d) basliyor, %d blok kayitli ===" % (die, ch, ce, len(kayit["bloklar"])))
    for b in range(BLOK):
        if str(b) in kayit["bloklar"]: continue
        sat = []
        kayit["simdi"] = b
        if die == 11 or b % 50 == 0: json.dump(kayit, open(yol, "w"))
        for pg in SAYFALAR:
            HATA["ardisik"] = 0
            t0 = time.time(); v = d.oku(b, pg, ch, ce, 0xC3); ms = int((time.time() - t0) * 1000)
            if die == 11 or v is None:
                d.abort()
            if HATA["ardisik"] >= 1:        # _log fires only on bridge/transport failures, never on NAND read errors
                kayit.setdefault("kopma", []).append([b, pg, time.strftime("%T")])
                json.dump(kayit, open(yol, "w"))
                J.P("  !! TUNEL KOPTU @die %d blok %d sayfa %d -> kaydedildi, cikiliyor" % (die, b, pg)); sys.exit(4)
            if v is None:
                sat.append([pg, "yok", ms, ""])
            else:
                ff = v.count(0xFF)
                sat.append([pg, "veri", ms, hashlib.sha256(v).hexdigest()[:8], ff])
            toplam += 1
            if toplam % 250 == 0 and not saglik():
                J.P("  ! saglik kontrolu basarisiz @die %d blok %d -> abort+tekrar" % (die, b))
                d.abort()
                if not saglik():
                    J.P("  !! tunel olu. kayit edildi, durduruluyor.")
                    json.dump(kayit, open(yol, "w")); sys.exit(3)
        kayit["bloklar"][str(b)] = sat
        if b % 200 == 199:
            json.dump(kayit, open(yol, "w"))
            gecen = time.time() - t_bas
            J.P("  die %2d blok %4d  okuma=%d  hiz=%.1f/s" % (die, b, toplam, toplam / gecen))
    kayit["bitti"] = True
    json.dump(kayit, open(yol, "w"))
    yok = sum(1 for s in kayit["bloklar"].values() for x in s if x[1] == "yok")
    J.P("=== die %d bitti: okunamayan sayfa %d / %d ===" % (die, yok, BLOK * len(SAYFALAR)))
J.P("TARAMA BITTI, toplam okuma %d, sure %.0f dk" % (toplam, (time.time() - t_bas) / 60))
