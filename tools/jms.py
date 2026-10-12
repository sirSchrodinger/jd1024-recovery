#!/usr/bin/env python3
"""jms.py -- drop-in `Loader` for the kaplikaya JD1024 tooling, over a JMicron JMS583 USB bridge.

Why: jd_loader.py/jd_hack.py/ortak.py/jdisk.py reach the MAP1202 through /dev/mem BAR programming,
their own admin queue and a hugepage DMA buffer. Everything they send to the DEVICE is plain NVMe
admin commands (0x06, 0xC1/0xC2 vendor tunnel). The JMS583 forwards admin commands itself
(smartmontools sntjmicron 3-phase protocol, proven on this box 24 Sep), so we replace only the
transport and keep every proven recipe unchanged.

Emulated surface (what the old code touches):
  Loader.komut(op, nsid, cdw, veri, ta, gonder) -> {"durum", "dw0"} | None
  Loader.kur() -> True            (bridge owns the queue; nothing to set up)
  Loader.bar.r32(0x1c) -> 1       (CSTS.RDY; bridge only exposes a ready controller)
  Loader.dma: van/oku/temizle/r32 (host buffer; data-in lands at OFF_DATA like the real DMA page)
  GDP.komut_prp/oku_prp           (16 KB page transfers: one passthrough, no PRP list needed)

Never: controller reset, USB reset, SCSI READ/WRITE to the LUN (LBA0 hang -> NVMe wedge, DURUM §32).
"""
import ctypes, fcntl, glob, os, struct, time

SG_IO = 0x2285
SG_DXFER_NONE, SG_DXFER_TO_DEV, SG_DXFER_FROM_DEV = -1, -2, -3
SIG = 0x454D564E                     # "NVME" little-endian, sntjmicron
OFF_DATA, OFF_DATA2, OFF_BIG = 0x2000, 0x3000, 0x10000
BUFSZ = 0x40000


class SgIoHdr(ctypes.Structure):
    _fields_ = [("interface_id", ctypes.c_int), ("dxfer_direction", ctypes.c_int),
                ("cmd_len", ctypes.c_ubyte), ("mx_sb_len", ctypes.c_ubyte), ("iovec_count", ctypes.c_ushort),
                ("dxfer_len", ctypes.c_uint), ("dxferp", ctypes.c_void_p), ("cmdp", ctypes.c_void_p),
                ("sbp", ctypes.c_void_p), ("timeout", ctypes.c_uint), ("flags", ctypes.c_uint),
                ("pack_id", ctypes.c_int), ("usr_ptr", ctypes.c_void_p), ("status", ctypes.c_ubyte),
                ("masked_status", ctypes.c_ubyte), ("msg_status", ctypes.c_ubyte), ("sb_len_wr", ctypes.c_ubyte),
                ("host_status", ctypes.c_ushort), ("driver_status", ctypes.c_ushort), ("resid", ctypes.c_int),
                ("duration", ctypes.c_uint), ("info", ctypes.c_uint)]


def jms_sg():
    """The JMS583 LUN's sg node, found by model string (never a fixed sgN)."""
    for d in sorted(glob.glob("/sys/class/scsi_generic/sg*")):
        try:
            if open(d + "/device/vendor").read().strip() == "JMicron":
                return "/dev/" + os.path.basename(d)
        except OSError:
            pass
    raise SystemExit("JMS583 kutusu bulunamadi (sg yok)")


class Sg:
    def __init__(self, yol=None):
        self.yol = yol or jms_sg()
        self.fd = os.open(self.yol, os.O_RDWR)
        self.sense = (ctypes.c_ubyte * 32)()
        self.son_hata = ""

    def io(self, cdb, yon, buf, n, ta):
        c = (ctypes.c_ubyte * len(cdb)).from_buffer_copy(bytes(cdb))
        h = SgIoHdr(interface_id=ord("S"), dxfer_direction=yon, cmd_len=len(cdb), mx_sb_len=32,
                    dxfer_len=n, dxferp=buf, cmdp=ctypes.addressof(c), sbp=ctypes.addressof(self.sense),
                    timeout=int(ta * 1000))
        fcntl.ioctl(self.fd, SG_IO, h)
        ok = h.status == 0 and h.host_status == 0 and h.driver_status == 0
        if not ok:
            self.son_hata = "status=%d host=%d driver=%d sense=%s" % (
                h.status, h.host_status, h.driver_status, bytes(self.sense[:h.sb_len_wr]).hex())
        return ok


def _cdb(admin, proto, ln):
    return bytes([0xA1, (0x80 if admin else 0) | proto, 0, (ln >> 16) & 0xFF, (ln >> 8) & 0xFF, ln & 0xFF, 0, 0, 0, 0, 0, 0])


class Dma:
    """Host-side stand-in for the hugepage: same offsets, same accessors."""
    def __init__(self):
        self.b = (ctypes.c_uint8 * BUFSZ)()
        self.van = ctypes.addressof(self.b)
        self.phys = 0
        self.u32 = ctypes.cast(self.van, ctypes.POINTER(ctypes.c_uint32))
    def r32(self, o): return self.u32[o >> 2]
    def oku(self, off, n): return bytes(bytearray(self.b[off:off + n]))
    def temizle(self, off, n): ctypes.memset(self.van + off, 0, n)
    def yaz(self, off, data): ctypes.memmove(self.van + off, bytes(data), len(data))


class Bar:
    def r32(self, o): return 1 if o == 0x1C else 0
    def r64(self, o): return 0
    def w32(self, o, v): pass
    def w64(self, o, v): pass


class JmsLoader:
    """Loader() replacement. All device traffic = sntjmicron 3-phase admin passthrough."""
    def __init__(self, yol=None, log=None):
        self.sg = Sg(yol)
        self.dma = Dma()
        self.bar = Bar()
        self.cid = 1
        self.log = log
        self.sayac = 0

    def kur(self): return True

    def komut(self, op, nsid=0, cdw=(0,) * 6, veri=0, ta=4.0, gonder=None, hedef=OFF_DATA, admin=True):
        """veri>0 and gonder given -> data-out; veri>0 alone -> data-in into dma[hedef:]."""
        ta = max(ta, 5.0); t0 = time.time()
        blk = bytearray(512)
        struct.pack_into("<I", blk, 0, SIG)
        struct.pack_into("<I", blk, 8, op & 0xFF)
        struct.pack_into("<I", blk, 12, nsid)
        for i, v in enumerate(cdw):
            struct.pack_into("<I", blk, 48 + 4 * i, v & 0xFFFFFFFF)
        cb = (ctypes.c_ubyte * 512).from_buffer(blk)
        if not self.sg.io(_cdb(admin, 0x0, 512), SG_DXFER_TO_DEV, ctypes.addressof(cb), 512, ta):
            return self._hata("faz1", op)
        if veri and gonder is not None:
            g = bytes(gonder).ljust(veri, b"\x00")[:veri]
            ob = (ctypes.c_ubyte * veri).from_buffer_copy(g)
            ok = self.sg.io(_cdb(admin, 0x3, veri), SG_DXFER_TO_DEV, ctypes.addressof(ob), veri, ta)
        elif veri:
            ok = self.sg.io(_cdb(admin, 0x2, veri), SG_DXFER_FROM_DEV, self.dma.van + hedef, veri, ta)
        else:
            ok = self.sg.io(_cdb(admin, 0x1, 0), SG_DXFER_NONE, None, 0, ta)
        if not ok:
            return self._hata("faz2", op)
        rep = (ctypes.c_ubyte * 512)()
        if not self.sg.io(_cdb(admin, 0xF, 512), SG_DXFER_FROM_DEV, ctypes.addressof(rep), 512, ta):
            return self._hata("faz3", op)
        r = bytes(rep)
        if struct.unpack_from("<I", r, 0)[0] != SIG:
            return self._hata("imza", op)
        self.sayac += 1
        cid = self.cid & 0x7FFF; self.cid += 1
        return {"durum": (struct.unpack_from("<I", r, 20)[0] >> 17) & 0x7FFF,
                "dw0": struct.unpack_from("<I", r, 8)[0],
                "cid": cid, "gonderilen": cid, "sure": time.time() - t0}

    def _hata(self, faz, op):
        if self.log: self.log("JMS %s op=0x%02X: %s" % (faz, op, self.sg.son_hata))
        return None


def yukle(log=print):
    """Load jd_loader -> jd_hack -> ortak -> jdisk with JmsLoader patched in. Returns (G_loader, G_hack, ortak, jdisk)."""
    import sys, types
    port = os.path.dirname(os.path.abspath(__file__))
    tek = {"L": None}
    def loader_fabrikasi():
        if tek["L"] is None: tek["L"] = JmsLoader(log=log)
        return tek["L"]
    # jd_loader globals (for gdprun etc.)
    src = open(port + "/jd_loader.py").read().rstrip()
    GL = {"__name__": "jd_loader_mod", "__file__": port + "/jd_loader.py"}
    exec(compile(src[:-len("main()")] if src.endswith("main()") else src, "jd_loader.py", "exec"), GL)
    GL["Loader"] = loader_fabrikasi
    # jd_hack globals: its module-level exec of jd_loader reads SRC -> point it at our copy
    hsrc = open(port + "/jd_hack.py").read().replace('SRC = "/usr/local/bin/jd_loader.py"', 'SRC = %r' % (port + "/jd_loader.py"))
    hsrc = hsrc.rstrip()
    if hsrc.endswith("main()"): hsrc = hsrc[:-len("main()")]
    GH = {"__name__": "jdh", "__file__": port + "/jd_hack.py"}
    exec(compile(hsrc, "jd_hack.py", "exec"), GH)
    GH["Loader"] = loader_fabrikasi
    GH["_G"]["Loader"] = loader_fabrikasi
    GDP = GH["GDP"]
    def komut_prp(self, op, cdw, nbytes, gonder=None, ta=30.0):
        return self.L.komut(op, cdw=cdw, veri=nbytes, gonder=gonder, ta=ta, hedef=OFF_BIG)
    GDP.komut_prp = komut_prp
    GDP.oku_prp = lambda self, n: self.L.dma.oku(OFF_BIG, n)
    # ortak: normally execs /usr/local/bin/jd_hack.py itself; give it our patched namespace instead
    osrc = open(port + "/../lib_k/ortak.py").read()
    osrc = osrc.replace('src=open("/usr/local/bin/jd_hack.py").read().replace("\\nmain()\\n","\\n")\n'
                        'G={"__name__":"jdh"}; exec(compile(src,"jd_hack.py","exec"),G)', "G=_JMS_GH")
    assert "G=_JMS_GH" in osrc, "ortak.py yapisi degismis"
    ortak = types.ModuleType("ortak"); ortak.__dict__["_JMS_GH"] = GH
    argv = list(sys.argv); exec(compile(osrc, "ortak.py", "exec"), ortak.__dict__); sys.argv = argv
    sys.modules["ortak"] = ortak
    jsrc = open(port + "/../lib_k/jdisk.py").read()
    jdisk = types.ModuleType("jdisk"); exec(compile(jsrc, "jdisk.py", "exec"), jdisk.__dict__)
    sys.modules["jdisk"] = jdisk
    return GL, GH, ortak, jdisk, loader_fabrikasi
