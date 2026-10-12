#!/usr/bin/env python3
"""jmsgdp.py -- JD1024 NAND session over the JMS583 box (T440). Proven kaplikaya recipe, new transport.

  sudo python3 jmsgdp.py kimlik     Identify: which firmware answers (product / ROM Loader / GDP)
  sudo python3 jmsgdp.py seans      ROM-GDP (wire in): gdprun FIRST -> hazirla -> JDisk -> flashid x16
  sudo python3 jmsgdp.py tara [--blok-adim N]   after seans: per-die block health scan -> ~/jd1024/tarama/

Rules carried over (jdisk.py header, DURUM): gdprun must be the first thing on a fresh ROM-GDP;
blocks 0..15 are never written/erased; erase is p6=1; kanal abort after every NAND op; no NAND RESET.
"""
import io, json, os, sys, time, contextlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jms

GDP_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "veri", "GDP_stub.bin")
OUT = "~/jd1024/tarama"
KOMUT = sys.argv[1] if len(sys.argv) > 1 else "kimlik"
ARGV = list(sys.argv)


def P(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)


GL, GH, ortak, jdisk, LF = jms.yukle(log=lambda m: P("  !", m))


def cagir_main(G, *args):
    """run a tool's own main() with argv, capture its stdout"""
    sys.argv = list(args); buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            G["main"]()
    except SystemExit:
        pass
    finally:
        sys.argv = ARGV
    return buf.getvalue()


def kimlik():
    L = LF()
    r = L.komut(0x06, cdw=(1, 0, 0, 0, 0, 0), veri=4096, ta=10.0)
    if not (r and r["durum"] == 0):
        P("Identify cevap yok:", r); return None
    d = L.dma.oku(jms.OFF_DATA, 4096)
    mn, fr = d[24:64].decode("latin1").strip(), d[64:72].decode("latin1").strip()
    P("Identify: MN=%r FR=%r" % (mn, fr)); return mn


def gdprun():
    out = cagir_main(GL, "jd_loader.py", "gdprun", GDP_BIN)
    open("/tmp/_jms_gdprun.log", "w").write(out)
    ok = "GDP MODU AKTIF" in out
    P("gdprun:", "GDP AKTIF" if ok else "BASARISIZ"); print(out[-1500:])
    if ok:
        for alt in ("hook", "dayanikli"):
            o = cagir_main(GH, "jd_hack.py", alt)
            P("hazirla/%s:" % alt, o.strip().splitlines()[-1] if o.strip() else "(cikti yok)")
    return ok


jdisk.JDisk.gdprun = staticmethod(lambda deneme=1: gdprun())


def seans():
    mn = kimlik()
    if mn is None: return None
    if "JAMESDONKEY" in mn:
        P("URUN modunda (tel yok). NAND tuneli icin tel + guc cevrimi gerekli."); return None
    if "GDP" not in mn and not gdprun():
        return None
    d = jdisk.JDisk(gdprun_gerekirse=False)
    P("geom P=%s blok=%s ppb=%s die=%s" % (d.P, d.blok, d.ppb, d.die_sayisi))
    ids = {}
    for ce in range(4):
        for ch in range(4):
            ids["c%dce%d" % (ch, ce)] = d.j.flashid(ch, ce)
        P("  ce%d: %s" % (ce, "  ".join(ids["c%dce%d" % (ch, ce)] or "----" for ch in range(4))))
    canli = sum(1 for v in ids.values() if v and v not in ("000000000000", "ffffffffffff"))
    P(">>> flashid: %d/16 die cevap verdi" % canli)
    os.makedirs(OUT, exist_ok=True)
    json.dump({"zaman": time.strftime("%F %T"), "geom": [d.P, d.blok, d.ppb, d.die_sayisi], "flashid": ids},
              open(OUT + "/seans.json", "w"), indent=1)
    return d


if __name__ == "__main__":
    if KOMUT == "kimlik":
        kimlik()
    elif KOMUT == "seans":
        seans()
    else:
        print(__doc__)
