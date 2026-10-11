# Full-page (16 KB) read/write on MAP1202 GDP — static analysis

Source: `c0.bin` @0x00000000, `c1.bin` @0x040C0000, disassembled with `re/dis/d.py`.
Everything below is **read out of the image** unless tagged `[INFER]`.
New helper added: `re/dis/bl.py <addr>` — finds every ARM `B`/`BL` to an address.

---

## 0. TL;DR — three separate facts, only one of which was known

1. **payload[12] (ctx `0x9210+0x11`) is `nchunk` — the number of 4 KB chunks in this
   transfer.** The host has always sent `0`. With `nchunk=0` the staging logic is
   skipped entirely and **every** `0x8A` programs the page immediately. That is why
   writing chunks 0,1,2,3 corrupts the page: it is four overlapping programs of the
   same cells. Set `payload[12]=4` and chunks 0..2 only stage; chunk 3 assembles
   16 KB and programs **once**.

2. **The NAND descriptor already moves 16384 bytes, not 4096.** The transfer size is
   FCQ ring `word3[3:0]` = *fragment-count mask* = `PFRAG_NUM-1` = **3** → 4 × 4 KB.
   It is computed in both handlers from `(1 << (STPU_SHIFT − PLANE_SHIFT − 3)) − 1`.
   `word3[31:16]` is the **column address**, hard-coded 0. So there is no "byte count"
   to raise — it is already at full page.

3. **…except on the read side, where `ldpc==0` collapses it to one fragment.**
   `0x040C4520`: `if (payload[9]==0) mask = 0;` → a raw read fetches **4096 bytes only**.
   Every verified experiment in §51–§55 used `ldpc=0`. That single line is the whole
   "one command = 4 KB" observation (RAPOR §51.5). The **write** handler has no such
   conditional — it has been programming full 16 KB pages all along, with 12 KB of
   stale SRAM as filler.

**Consequence: full-page read costs zero firmware changes — switch to `ldpc=1` and keep
all 16384 bytes of the `0xC2` data phase. Full-page write costs one payload byte.**

All three are independently confirmed from the vendor's own `MXMPTool` x86 code (T5):
it names the fields `chunkCnt`/`chunkIdx`, its 4-chunk loop writes each chunk to
`pBuf + i*4096` for a 16384-byte page, and it drops to a single 4096-byte chunk exactly
when `ucLdpcRate == 0`. Its **shipped default** (`EnNvmeCmdMode=0`) is `chunkCnt = 0`
plus one data phase of the whole page — which is RECIPE C below.

**And a second, equally large find (see "Two capacity questions"): `rowfield = blk*4 +
plane` has always been called with `plane = 0`, so three quarters of the array has never
been addressed at all; while `jdblk.SAYFA_BLOK = 1536` is almost certainly 4x too large
(the vendor flash table says 384 pages per block-plane). Net: 16 KB pages are 4x, the
plane axis is another 4x, and the page count needs fixing before either.**

---

## 1. Command context layout (`0x9210`) — confirmed, not inferred

`0x040C6698` (command parser) does
`memcpy(0x9210+5, 0x0000EAB0, 0x10)` at `0x040C671C` when table-entry byte `+8 == 1`.
So **ctx offset = payload index + 5**, for all 16 bytes.

| ctx | payload | field |
|---|---|---|
| `0x9210+0` | – | busy flag (parser sets 1) |
| `+1` | – | "run me" flag polled by the main loop at `0x040C12A0` |
| `+2` | – | data-source select: handler writes **2** ⇒ host reads from `0x0400F2C0`, otherwise `0x040612C0` |
| `+3` | – | dispatch-table **index** (not the opcode) |
| `+4` | – | phase, = table entry `+0xA` |
| `+5..+7` | [0..2] | `FF E5 <opcode>` |
| `+8` | [3] | channel |
| `+9` | [4] | low nibble CE, high nibble LUN |
| `+0xA..B` | [5..6] | rowfield, u16 **BE** (= block×PLN_QNTY + plane) |
| `+0xC..D` | [7..8] | page, u16 **BE** |
| `+0xE` | [9] | **`ucLdpcRate`** — 0 = bypass, non-zero = LDPC on (this build only tests `!=0`) |
| `+0xF` | [10] | **`ucScrambleMode`** — only bit 0 reaches the HW (`0x040C6B6C`) |
| `+0x10` | [11] | **`ucBlockType`** (vendor name). Handler: `0` → planecount arg 0; `1` or `2` → `PLN_QNTY-1`; `8` = loader-block (used by `VP_WriteDataToLoaderBlock`) |
| `+0x11` | [12] | **nchunk — chunk count (was always 0)** |
| `+0x12` | [13] | **chunk index** |
| `+0x15` | – | set from parser arg when entry `+9 == 1` |
| `+0x16` | – | sequence counter |
| `+0x17` | – | **result byte** (`0x01` ok, `0x1B` read error, `0xAA` handler never wrote) |

Dispatch table `0x040ED2F4`, 36 × 12 bytes: `{u8 cmd; u8 phase; u16 pad; u32 handler; u8 f8; u8 f9; u8 fA; u8 fB}`.
`fB == 1` ⇒ parser arms the host **write**-data landing buffer at **`0x0400F2C0`**
(`0x040C6760`: `0x040EC68C(0, 0x0400F2C0)`, a veneer to Thumb `0x040E04A8`).
`fB == 2` ⇒ read direction.
`0x8A` → `01 01 00 01`, `0x89` → `01 01 00 02`.

### Phase ordering — settled, not assumed

`jd_hack.GDP._faz1` is itself an **NVMe write**:
`komut(0xC1, cdw=(0x80,0,0,0,0x001234FF,1), veri=512, gonder=payload)`.
So the 16-byte vendor payload arrives as the *data* of a 512-byte `0xC1` with
`CDW14 = 0x001234FF`; it lands at `0x0000EAB0` and the write-completion path
`0x040E0624` calls the parser `0x040C6698(cmd, phase=1)` at `0x040E063C`.
The parser only sets `ctx[+1] = 1`; the **main loop** at `0x040C12A0` picks that up and
calls `0x040C6770`, which invokes the handler. The bulk data command
(`0xC1`/`0xC2` with `CDW14 = 0x00123400 | opcode`) is matched at `0x040E09C2`
(`bic r4,r2,#0xff000000; cmp r4, 0x00123400|pending`) and moved before that.

⇒ **the handler always runs after the bulk data has landed**, which is why a single-chunk
write has never shown an off-by-one page. The chunked write in RECIPE B is therefore
safe: each `0x8A` stages the 4 KB that its own `0xC1` just delivered.

---

## T1 — `0x8A` PageWrite handler `0x040C3DB4`, chunk logic

```
040C3DC8  r5  = ctx[9]      payload[4]  ce|lun
040C3DCC  sb  = ctx[8]      payload[3]  ch
040C3DD0  [sp+4]    = ctx[0xE]   ldpc
040C3DD8  [sp+0x10] = ctx[0xF]   scr
040C3DE0  [sp]      = rev16(ctx[0xA])   rowfield
040C3DE4  r4  = ctx[0x10]   plane mode
040C3DF0  sl  = rev16(ctx[0xC])  page
040C3DF4  r1  = ctx[0x12]   chunk
040C3DFC  r0  = ctx[0x11]   NCHUNK
040C3E00  cmp r0,#0
040C3E04  beq 0x040C3E8C        <-- NCHUNK==0: skip staging, program NOW
```

### staging block (only when `NCHUNK != 0`)

```
040C3E08  geo  = *(u32*)0x00000DCC          ; via *(0x0DB8+0x14)
040C3E10  r3   = geo[0x1F]                  ; STPU_SHIFT
040C3E18  r2   = c0[0x9255]                 ; PLANE_SHIFT
040C3E28  r2   = 1 << (STPU_SHIFT - PLANE_SHIFT - 3)     ; = PFRAG_NUM
040C3E2C  cmp  NCHUNK, PFRAG_NUM
040C3E30  ble  0x040C3E38
040C3E34  b    0x040C3E34                   ; *** INFINITE LOOP — hard hang ***

040C3E3C  r1 = chunk & 3
040C3E44  r2 = (chunk&3) + 1
040C3E58  r3 = 0x04074EC0 + (chunk&3)*0x1000
040C3E4C  cmp NCHUNK, chunk+1
040C3E60  beq 0x040C3E70                    ; last chunk?

  ; NOT last chunk:
040C3E68  memcpy(0x04074EC0 + chunk*0x1000, 0x0400F2C0, 0x1000)
040C3E6C  b 0x040C404C                      ; return 1, NO NAND ACCESS,
                                            ; and ctx[0x17] is NOT updated

  ; LAST chunk (NCHUNK == chunk+1):
040C3E78  memcpy(0x04074EC0 + chunk*0x1000, 0x0400F2C0, 0x1000)
040C3E88  memcpy(0x0400F2C0, 0x04074EC0, 0x4000)       ; 16 KB staging -> DATA_BUF
          fall through to 0x040C3E8C -> real program
```

`0x040E854C` and `0x040E85D4` are both `memcpy(dst=r0, src=r1, n=r2)` (the first is the
unaligned entry, it falls through into the second).

### program path (`0x040C3E8C` onwards)

```
040C3EB0  sb  = ch | ((ce | lun<<(3-LUN_SHIFT)) << 2)        ; "composite"
040C3EC8  q,r = divmod(rowfield, geo[9]=PLN_QNTY)
          [sp+0xC]        = q                                 ; block
          sb bits[31:16]  = page
          sb bits[15:8]   = composite
040C3F14  sb bits[7:0]    = r << (STPU_SHIFT-PLANE_SHIFT-3)   ; = plane * PFRAG_NUM
                                                              ; = starting 4 KB frag index
040C3F10  r6 = (ucBlockType==1||2) ? PLN_QNTY-1 : 0   ; NOTE: no else-branch, r6 is
                                                     ; left uninitialised for other values
040C3F38  0x040C6AA0(ldpc)        ; LDPC on/off + set engine length  (see T3)
040C3F44  0x040C6B6C(0, scr)      ; scrambler enable
040C3F50  0x040D27B4(sb,[sp+0xC]) ; no-op unless c0[0x0DC8]==2 (static 0)
040C3F84  r0 = (1 << (STPU_SHIFT-PLANE_SHIFT-3)) - 1 = PFRAG_NUM-1 = 3   <-- FRAG MASK
040C3F94  handle = 0x040DB828(sb, block, r6, 0, [sp]=mask, 0)
040C3FD0  ok = 0x040DE16C(sb, block, handle, r3=0 /*column*/, [sp]=mask)
040C4000  0x040DBDCC(4 or 5 completions, ...)
040C4018  0x040DB680(handle)          ; free
040C4024  ctx[0x17] = ok ? 1 : 0
```

`0x040DE16C` = check-ready(0x42) → switch-SLC(0xD0) → **program(0x64) `0x040DD384`** →
check-ready(0x42). Program data always comes from the global DMA base
`FCQ+0x140 = 0x0400F2C0>>3` (measured in RAPOR §45.13).

### Independent corroboration: cmd `0x4C` uses the identical mechanism

`0x4C` (`0x040C4058`, table index 4, `fB=1` ⇒ data-in to `0x0400F2C0`) carries a
byte-for-byte copy of the same staging block at `0x040C40A4..0x040C4124`: same
`ctx[0x11]` / `ctx[0x12]` pair, same `1 << (STPU−PLANE−3)` bound with its own
`b .` at `0x040C40D4`, same `0x04074EC0 + chunk*0x1000` slots, same
`memcpy(0x0400F2C0, 0x04074EC0, 0x4000)` on the last chunk. It then calls
`0x040D2D68` → `0x040DDF8C` → **program `0x64` (`0x040DD384`)** over multiple dies.
`0x4D` (`0x040C4208`) is its partner, printing `"[INFO] Update CB State"` /
`"C:%X B:%X STS:%X"` — so `0x4C` is the vendor's **code-block writer**, and the chunk
staging is simply the firmware's standard way of receiving a **full 16 KB page in four
4 KB NVMe data phases**. That is what `payload[12]` exists for.

**Answers to T1:**
* Incoming 4096 bytes land at **`0x0400F2C0`** (`DATA_BUF_SRAM_BASE`, the firmware's own
  name — printed at `0x040C04A4`). Armed by the parser, not by the handler.
* Staging buffer: **`0x04074EC0`, 4 slots × 4096 = 16384 bytes exactly**
  (`0x04074EC0 .. 0x04078EC0`). Shared with the read cache and with cmd `0x4C`.
* Program trigger condition: **`payload[12] == (payload[13] & 3) + 1`**.
* `payload[12] == 0` bypasses staging completely → immediate program.
* `payload[12] > PFRAG_NUM` → **`b .` infinite loop at `0x040C3E34`**, the GDP main loop
  never returns. Recoverable with `gdprun` (~25 s), no cold cycle needed.
* On a staging chunk the handler returns 1 **without writing `ctx[0x17]`** — the host's
  `getreturn()` will report the *previous* command's status. Only check status on the
  last chunk.

---

## T2 — `0x89` PageRead handler `0x040C4360`, cache semantics

```
040C43AC  r0 = ctx[0x12]           ; chunk  (payload[13]) — NOT masked with 3 here
040C43B0  cmp r0,#0
040C43B4  beq 0x040C4410           ; chunk 0 -> real NAND read

  ; chunk != 0 : pure cache replay, no NAND
040C43C8  memcpy(0x0400F2C0, 0x04074EC0 + chunk*0x1000, 0x4000)
040C43E0  0x040CF608(*(0x0E48+8)/1000 - 1)      ; short delay
040C43F0  memcpy(0x040612C0, 0x0400F2C0, 0x4000)
040C43F4  ctx[2] = 2               ; -> host data source = 0x0400F2C0
040C440C  return 1

  ; chunk == 0 : real read
040C44C4  if (geo[0x310 + (ch | ce<<3 | lun<<6)] == 0xFF) { ctx[2]=2; return; }   ; die absent
040C4504  zerofill(0x0400F2C0, 1 << geo[0x1D])        ; only 1<<PAGE_SHIFT bytes!
040C4508  0x040C6AA0(ldpc)
040C4518  0x040C6B6C(0, scr)
040C4520  if (ldpc == 0) mask = 0;                    ; *** 1 fragment = 4096 bytes ***
040C4550  else            mask = PFRAG_NUM-1 = 3;     ;     4 fragments = 16384 bytes
040C456C  handle = 0x040DB828(addrword, block, r5, 0, mask, 0)
040C4584  ok = 0x040DE038(addrword, block, handle, r3=0 /*column*/, mask)
040C45C0  0x040DBDCC(4 or 5, ...)
040C4618  memcpy(0x04074EC0, 0x0400F2C0, 0x4000)      ; fill the chunk cache, 16 KB
040C462C  free handle
040C4630  b 0x040C43E4  -> memcpy(0x040612C0, 0x0400F2C0, 0x4000); ctx[2]=2; return 1
```

**Answers to T2:**
* The cache at `0x04074EC0` **is** filled by the chunk-0 read, with **`0x4000` = 16384
  bytes**, copied out of `0x0400F2C0` after the descriptor completes.
* `memcpy(0x0400F2C0, 0x04074EC0 + chunk*0x1000, 0x4000)` is a **16 KB window sliding by
  4 KB**. It is a quirk, not a 28 KB cache: for `chunk=3` it reads 12288 bytes **past the
  end** of the 16 KB cache (`0x04078EC0 .. 0x0407BEC0` is unrelated SRAM).
  Only the **first 4096 bytes** of the returned 16384 are meaningful for `chunk != 0`.
* For `chunk == 0` **all 16384 bytes are meaningful** — the cache replay is pure overhead.
  This is why the whole chunk mechanism is unnecessary on the read side.
* The cache was always stale for chunks 1..3 in the experiments because `ldpc=0` made the
  real read fetch only 4096 bytes, so bytes 4096..16383 of `0x0400F2C0` (and therefore of
  the cache) were leftovers. The pre-read `zerofill` only clears `1<<geo[0x1D]` bytes,
  which is 4096 with the static geometry — it never clears the rest.

---

## T3 — where the transfer length and column actually live

There are **two** length knobs, at two different layers.

### (a) NAND-bus length — `LDPCENC+0x10` bits[12:0], in dwords

`0x040C6AA0(ldpc)`:

```
 ldpc != 0 :  LDPCENC[0x10].bits[12:0] = (geo[0xE] + (geo[6]<<10)) >> 2
              = NAND_PAGE_SIZE/4 = (16384 + 2048)/4 = 4608 = 0x1200   ->  18432 bytes
              + loads dec matrix from RAM 0x1000 (len *(0x0E70)/4) via 0x040E4700
              + loads enc matrix from RAM 0x3928 (len *(0x0E74)/4) via 0x040E4764
 ldpc == 0 :  LDPCENC[0x10].bits[12:0] = 0x1270 = 4720               ->  18880 bytes
              + 0x040E4888 loads the bypass matrices (0x4FF8 len 0xA80, 0x79F8 len 0x5C6)
```

Matches RAPOR §45.9 exactly (`6AA0(1)→0x0a3d1200`, `6AA0(0)→0x0a3d1270`).
`bits[25:13]` (= 4584 in the measurement = 18336/4) is set once at boot
(`0x040E22B8`) from the *default* geometry and is not touched per command.
`bits[28:26]=2` set at `0x040E22C8`.

So the NAND side already streams the **entire physical page including spare** on every
`0x89`/`0x8A`. There is nothing to raise here.

Cross-check from `ANALIZ` work already on disk (`re/gdp_local/BULGULAR.md` line 265):
`ldpc_find_rate` @`0x040DEE98` rejects any codeword `cw <= 16384` and indexes its rate
table with `((cw-16384)>>2) & ~31`. With `cw = 18432` that is `512` — i.e. the engine
itself treats **16384 as the user payload and the 2048-byte remainder as parity**.

### (b) SRAM-side length — FCQ ring `word3[3:0]` = fragment-count mask

All four ring packers put the same descriptor field into `word3[3:0]`:

| builder | descriptor byte | packer |
|---|---|---|
| `0x040DD010` data-out 0xB0/0xAE | `desc+0x10` | subB `0x040EC240` |
| `0x040DD384` program 0x64 | `desc+0x0E` | subC `0x040EBD8C` (`0x040EBF00`: `ldrb r0,[r4,#0xe]`, then bits 4..31 overwritten) |
| `0x040DD290` raw data-out | `desc+0x10` | subD `0x040E3B54` |

and in every case that byte is the **5th (stack) argument** of the builder, which the
read/program wrappers pass straight through from **their own 5th argument**.

Evidence that it is a fragment count and not a CE mask: the bad-block scan
(`0x040D3F3C`) calls `0x040DD290` with `arg5 = 0` while still targeting a specific die
through the address word, and it reads exactly **one** 4 KB fragment into a per-die
`0x0400F2C0 + n*0x1000` slot. The `0x89`/`0x8A` handlers pass `PFRAG_NUM-1 = 3` and get
four fragments.

### (c) column address — FCQ ring `word3[31:16]`

`0x040DD010`: `strh r7,[sp,#0xe]` with `r7 = arg4`.
`0x040DD384`: `strh r7,[sp,#0x10]` with `r7 = arg4`.
`0x040DD290`: `strh r8,[sp,#0x12]` with `r8 = arg4`.
subB/subC/subD all pack that u16 into `word3[31:16]`.
Both GDP handlers pass **`r3 = 0`** (`0x040C457C`, `0x040C3FA4`). The bad-block scan also
passes 0. **The column address is 0 everywhere in this firmware.**

### (d) the address word

`0x040C8EC4(addrword, block)`:

```
result = block   << (PAGE_SHIFT + STPU_SHIFT + 3 - 1)
       | page    << (STPU_SHIFT + 3 - 1)
       | composite << (STPU_SHIFT - 3)
       | frag                                  ; addrword[7:0], bits [3:0] of the result
```
with `addrword = page<<16 | composite<<8 | frag`, `frag = plane * PFRAG_NUM`.
So the low 4 bits of the hardware address are the **4 KB fragment index inside the
64 KB super-page** (4 planes × 16 KB), and the fragment mask says how many consecutive
fragments to move. `plane` selects a different *plane*, not a different quarter of one
page — so in raw mode there is no payload-level way to reach fragments 1..3 of a page.

### Geometry constants (names from the firmware's own boot banner, `0x040C0308`)

| name | source | static default | live value |
|---|---|---|---|
| `PAGE_SIZE` | `geo[6] << 10` | 16 KB | 16384 |
| `NAND_PAGE_SIZE` | `geo[0xE] + geo[6]<<10` | 18336 (spare 1952) | **18432 (spare 2048)** — derived from the measured `0x1200` |
| `PLN_QNTY` | `geo[9]` | 2 | 4 (rowfield = blk×4 + plane) |
| `STPU_SHIFT` | `geo[0x1F]` | **7** | 7 |
| `PLANE_SHIFT` | `c0[0x9255]` | (BSS) | 2 |
| `LUN_SHIFT` | `c0[0x9244]` | (BSS) | – |
| `PAGE_SHIFT` | `geo[0x1D]` | 12 | – |
| `FRAG_NUM` | `1<<(STPU−3)` | 16 | 16 (64 KB super-page) |
| **`PFRAG_NUM`** | `1<<(STPU−PLANE−3)` | – | **4** |
| `DATA_BUF_SRAM_BASE` | literal | `0x0400F2C0` | `0x0400F2C0` |
| `FCL_IF_META_DATA_SIZE` | literal | 3 | 3 |

`geo` pointer = `*(u32*)0x00000DCC` (static `0x000004E0`).

**Answer to T3:** nothing needs to be raised to move 16384 bytes — the firmware already
does. The only value that ever caps a transfer below a full page is the
`if (ldpc == 0) mask = 0` at `0x040C4524` in the read handler.

---

## T4 — recipes, ranked by risk

Notation: `pay(op, a3..a13)` is the existing `jd_hack._pay` helper; it emits
`FF E5 op a3 a4 …`. `komut_prp(0xC1|0xC2, (n>>2, 0,0,0, MAGIC, n>>9), n, …)`
with `MAGIC = 0x0012348A` for write, `0x00123489` for read.

### R0 (do this first, zero risk) — confirm `PFRAG_NUM` at runtime

```python
g   = struct.unpack("<I", jd.g.rd(0x00000DCC, 4))[0]     # geometry pointer
geo = jd.g.rd(g, 0x40)
stpu = geo[0x1F]                                          # STPU_SHIFT
plsh = jd.g.rd(0x00009254, 2)[1]                          # c0[0x9255] PLANE_SHIFT
PFRAG = 1 << (stpu - plsh - 3)          # must be 4 ; if it is not, DO NOT use nchunk=4
spare = struct.unpack("<H", geo[0x0E:0x10])[0]
```
Cross-check: after any `ldpc=1` command, `jd.reg(0x06610010) & 0x1FFF` must be
`(spare + 16384)//4` (expected `0x1200`).

### RECIPE A — full-page READ (16384 B), **risk: none, no firmware change**

1. `_faz1(pay(0x89, ch, ce, rfH, rfL, pgH, pgL, 1, 1, 0, 0, 0))`
   — `ldpc=1`, `scr=1`, plane_mode=0, **nchunk=0**, **chunk=0**.
2. `komut_prp(0xC2, (4096, 0,0,0, 0x00123489, 32), 16384)`
3. `oku_prp(16384)` → **keep all 16384 bytes**. Do not slice `[:4096]`.
4. `getreturn()[0]` must be `0x01`.

Nothing else changes. The current code's only defect on the read path is
`ldpc=0` (which makes the descriptor fetch one fragment) plus the `[:4096]` slice.

**Migration caveat:** read mode must match write mode (RAPOR §55.3). Everything already
stored on the drive was written raw (`ldpc=0`), so RECIPE A cannot read it — old data
stays 4 KB/page until you either rewrite it with `ldpc=1` or apply patch E1.

### RECIPE B — full-page WRITE (16384 B), chunked, **risk: low; this is the vendor path**

Pre-condition: block erased (`0x8B`), and `PFRAG_NUM == 4` verified (R0).

For `i` in `0,1,2,3`:
1. `_faz1(pay(0x8A, ch, ce, rfH, rfL, pgH, pgL, 1, 1, 0, 4, i))`
   — byte 12 = **4** (nchunk), byte 13 = `i`.
2. `komut_prp(0xC1, (1024, 0,0,0, 0x0012348A, 8), 4096, gonder=data[i*4096:(i+1)*4096])`

Only after `i == 3`: `getreturn()[0]` must be `0x01`. After `i = 0,1,2` the status byte
is stale — ignore it.

Constraints:
* Do **not** issue any `0x89`, `0x4C` or `0x4D` between chunk 0 and chunk 3 — they all
  use the same `0x04074EC0` staging buffer.
* Read back with RECIPE A (`ldpc=1, scr=1`) — mode must match the write (RAPOR §55.3).

### RECIPE C — full-page WRITE, single 16 KB data phase, **risk: low — this is the vendor's shipped default**

1. `_faz1(pay(0x8A, ch, ce, rfH, rfL, pgH, pgL, 1, 1, 0, 0, 0))`  — nchunk **0**
2. `komut_prp(0xC1, (4096, 0,0,0, 0x0012348A, 32), 16384, gonder=data)`

Why it works: the PRP copier is Thumb `0x040E04A8`, used for **both** directions
(`r0=0` host→controller, `r0!=0` controller→host — the branch at `0x040E0592`).
The struct it reads sits at **`0x0000C9A8`, which is the NVMe SQE minus 4**:
`[+0x1C]` = SQE+0x18 = PRP1 (`ubfx sl,r0,#0,#0xc` takes its page offset),
`[+0x24/0x28]` = SQE+0x20 = PRP2, `[+0x3C]` = SQE+0x38 = CDW14 (the
`0x00123400|op` match at `0x040E09C2`), and

```
040E04D8  ldr  r6, [r6, #0x40]     ; = SQE+0x3C = CDW15 = nsec
040E04DE  lsls r6, r0              ; << LBA shift (9)
```

so the byte count is **`CDW15 << 9`, entirely host-chosen**, and the loop at
`0x040E0570..0x040E05BE` walks the PRP list in 0x1000 steps for as many pages as needed.
`komut_prp` already builds a real PRP list above 8 KB. With `nchunk=0` the handler skips
staging and programs straight out of `0x0400F2C0`.
Saves 6 of 8 NVMe commands per page (~4× host-side throughput on top of the 4× capacity).

**MXMPTool ships configured to do exactly this** — `MPTOOL.ini [Setting] EnNvmeCmdMode=0`
selects `VP_WritePage`'s case C: `chunkCnt = 0`, `chunkIdx = 0`, one data phase of
`dwSectorCnt` sectors straight out of the caller's buffer with no staging memcpy. So
this is not the risky variant; it is the normal one. B is listed first only because it
exercises the staging path you can inspect in SRAM if something goes wrong.

### RECIPE D — direct call, bypassing the payload entirely, **risk: medium**

Both handlers are thin wrappers. With the `cagir` stub (4 register args + stack is not
available, so this needs a 5-arg trampoline in the code cave):

```
read :  0x040DE038(addrword, block, handle, column, fragmask)
write:  0x040DE16C(addrword, block, handle, column, fragmask)
        addrword = page<<16 | (ch | ((ce | lun<<(3-LUN_SHIFT))<<2))<<8 | plane*PFRAG_NUM
        block    = rowfield / PLN_QNTY
        handle   = 0x040DB828(addrword, block, planecount, 0, fragmask, 0)
        free     = 0x040DB680(handle)
        poll     = 0x040DBDCC(4, 1, &statusbyte, 1, 1, 0)
```
Use this only for things the payload cannot express — arbitrary `column`, or
`fragmask != PFRAG_NUM-1`. The existing stub passes only r0..r3, so arg5 needs a
6-instruction shim in the cave at `0x040FF100`.

### RECIPE E — one-instruction patches (keep for last, **risk: medium-high**)

**E1 — make the RAW read full-page (one word).** Verified encodings:

```
0x040C4520   E3500000   cmp    r0, #0          ; r0 = payload[9] = ldpc
0x040C4524   03A07000   moveq  r7, #0          ; mask = 0  -> 1 fragment
0x040C4528   0A000009   beq    0x040C4554      ; skip the real mask computation
0x040C452C.. E51F022C   (mask = PFRAG_NUM-1)
0x040C4550   E20070FF   and    r7, r0, #0xff
```
Patch **`0x040C4528` ← `E1A00000`** (`mov r0,r0`, a NOP). The `moveq r7,#0` becomes
harmless because `0x040C4550` overwrites `r7` unconditionally. One word, reversible
with `orij(0x040C4528)` exactly like the existing `YAMA_ADR` list in `ortak.py`.

Why you may need it: **RECIPE A only reads back pages written with `ldpc=1`.** All data
already on the drive — the 1.57 MB from §55, and the vendor loader block 0 (`LDBK`,
read with `ldpc=0 scr=1`) — is raw. To read those at full page you need E1 or D.

**E2 — raise the fragment mask above `PFRAG_NUM-1`.** `sub r0,r0,#1` (`E2400001`) at
**`0x040C3F80`** (write) and **`0x040C454C`** (read) is what turns `PFRAG_NUM` into the
mask. NOPping it gives mask = 4 → 5 fragments = 20480 bytes, i.e. it would pull the
spare into the host transfer. Speculative; do not try before T6 is settled.

### Ranking

| # | what | risk | payoff |
|---|---|---|---|
| R0 | read `PFRAG_NUM` | none | prevents the `b .` hang |
| A | `ldpc=1` read, keep 16 KB | none | **full-page read** |
| B | `nchunk=4`, 4 chunks | low | **full-page write** |
| C | `nchunk=0`, one 16 KB data phase | low (vendor default) | 4× host throughput on top of A+B |
| D | direct `0x040DE038/16C` call | med | arbitrary column / frag count |
| E | code patches | med-high | raw-mode full page, >16 KB |

### Capacity

4096 → 16384 bytes per page = **exactly 4×**. See "Two capacity questions" below for a
second, independent 4× (the plane axis) and for why `jdblk.SAYFA_BLOK` must be checked
before either number is real.

---

## T5 — vendor MPTool host-side builders (recovered from the EXEs)

**Our running GDP is byte-identical to the HYV8 package's `GDP.bin`.** The first 64
bytes of the `0x8A` handler (`0x040C3DB4`) appear verbatim at file offset `0x10DB4` in
`hunt/hyv8/MAP1202_H25TXTD2XCX6/GDP.bin`; with chunk1 at file `0xD000` → RAM
`0x040C0000` that is exactly `0x040C3DB4`. So `MXMPTool_MAP1202_USB_V1_1_26.exe`
drives precisely the code analysed above. (HYV7's `GDP.bin` is packed differently.)

### Recovered prototypes (x86 disassembly of `MXMPTool_MAP1202_USB_V1_1_26.exe`)

```c
// VA 0x42E6A8 (file 0x2DCA8)
BOOL VC_GDP_CmdPageRead (u8 port, u8 ch, u8 bank, u16 block, u16 page,
                         u8 ucLdpcRate, u8 ucScrambleMode, u8 ucBlockType,
                         void *pData, u32 dwSectorCnt, u8 chunkIdx, u8 chunkCnt);
// VA 0x42E7AC (file 0x2DDAC)
BOOL VC_GDP_CmdPageWrite(u8 port, u8 ch, u8 bank, u16 block, u16 page,
                         u8 ucLdpcRate, u8 ucScrambleMode, u8 ucBlockType,
                         void *pData, u32 dwSectorCnt,
                         u8 extra2bits, u8 chunkIdx, u8 chunkCnt);
// VA 0x42E8A8 — VC_GDP_CmdPageWriteInterleave, opcode 0x4C, same shape as PageRead
```
Byte fill, read verbatim out of the code (`mov byte [ebp-0x1000+i], …`):

| payload | vendor name | note |
|---|---|---|
| [0],[1] | `0xFF`, `0xE5` | built byte-by-byte, never a literal in the file |
| [2] | opcode | `0x8A` write (unconditional); read `0x89`, **or `0xD9` when `EnNvmeCmdMode!=0`** |
| [3] | `ucChNo` | |
| [4] | `ucBankNo` | |
| [5],[6] | `wBlockNo` hi,lo | |
| [7],[8] | `wPageNo` hi,lo | |
| [9] | **`ucLdpcRate`** | a *rate* 0..4, not a boolean — GUI radio "LDPC Rate 1..4" |
| [10] | **`ucScrambleMode`** | write path also ORs `(arg11 & 3) << 2`; that field is always 0 |
| [11] | **`ucBlockType`** | **not** a plane number. GUI passes 0; `VP_WriteDataToLoaderBlock` passes 8 |
| [12] | **chunk COUNT** | |
| [13] | **chunk INDEX** | |

### The vendor's own three call shapes (`VP_ReadPage` @0x443DF4 / `VP_WritePage` @0x444420)

| mode | condition | count | idx | dwSectorCnt | bytes |
|---|---|---|---|---|---|
| A | `EnNvmeCmdMode!=0` **and `ldpcRate==0`** | 1 | 0 | 8 | **4096, one call** |
| B | `EnNvmeCmdMode!=0` and `ldpcRate!=0` | **4** | 0..3 | 8 | 4×4096 → `pBuf + i*4096` = **16384** |
| C | `EnNvmeCmdMode==0` (**the shipped default**) | **0** | 0 | caller's `dwLen` | **one transfer, whole page** |

An exhaustive sweep of every call site in the EXE found **only counts 0, 1 and 4**.

**Two things this settles:**
1. Mode A is the host-side mirror of the firmware's `if (ldpcRate == 0) mask = 0` at
   `0x040C4524`. The vendor tool *knows* a raw transfer is one 4 KB fragment. This is
   independent confirmation of TL;DR fact 3, from a completely different binary.
2. Mode C — count 0, one data phase of the full page — is **the vendor's shipped
   default** (`MPTOOL.ini [Setting] EnNvmeCmdMode=0`). That is exactly RECIPE C. It is
   not a guess; it is what MXMPTool does every day.

### Transport (confirms the two-phase framing)

`0x42D0B4` builds, per GDP command:
* **phase 1** — NVMe admin **`0xC1`**, 512-byte data-out carrying `FF E5 op …`,
  `CDW10 = 1<<7`, **`CDW14 = 0x001234FF`**, `CDW15 = 1`.
* **phase 2** — admin **`0xC1`** (write) / **`0xC2`** (read),
  `CDW10 = nSect<<7`, **`CDW14 = 0x00123400 | payload[2]`**, `CDW15 = nSect`,
  `nSect*512` bytes.

Identical to `jd_hack.GDP._faz1` / `send` / `komut_prp`. Nothing to change.

### `VC_GDP_CmdReadBuffer` / `VC_GDP_CmdWriteBuffer`

The error strings exist (`0x49E306`, `0x49E32E`) but have **zero code xrefs** in any of
the four EXEs — they were never implemented on the host side. Our GDP dispatch table has
no entry for them either. Dead end; ignore.

### Vendor opcode table (53 construction sites, `A/B` = `EnNvmeCmdMode!=0` / `==0`)

`0x82/0x83` JumpToPRAM/ROM · `0xD0/0x84` GetReg · `0x87` WriteRam · `0xD1/0x86` ReadRam ·
`0x11` InitGDP · `0xD2` GetReturn · `0xE4` ReadVref · `0x14` ReadUID ·
`0xD7/0x10` GetFlashParam · `0xD8/0x88` ReadFlashID · `0x53/0x5B/0x54` BDL/LCDL ·
`0xDE/0x55` ZQ · **`0xD9/0x89` PageRead** · **`0x8A` PageWrite** ·
**`0x4C` PageWriteInterleave** · `0x0A/0x0C` SPI · `0x8B` BlockErase ·
`0xD6/0x31` GetDefectBadTab · `0xD3/0xD4` GetFlashModule/GetCodeBlock ·
`0x3A` PreCheckCodeBlock · `0xD5/0x3B` AutoDetect · `0xDB/0x21` FlashDiagnostic ·
`0x47`/`0xDC-0x48` ScanResultBlk/GetResultBlk · `0xE0/0x49` SwitchToLegacy ·
`0x58/0x57` ChangeFlashID/NandPowerOnOff · `0x4A/0x4B/0x4E/0x4D` DramTest/CheckNandTime/
Pcie_LoopBack/InitGDP2 · `0xDD/0x4F` ReadEfuse · `0x5A/0xE1` Start/GetProgramLoop ·
`0xC4/0xC2/0xC3/0xC5` SYS ReadPage/GetBadUnit/GetEraseCount/GetUartLog.

**Our GDP build implements only the `B` column** — there is no `0xD9`, `0xD7`, `0xD8`,
`0xD2`… in the dispatch table at `0x040ED2F4`. So keep using `0x89`, and keep
`nchunk`/`chunk` in payload[12]/[13]; the `0xD9` variant does not exist here.

### `page` goes through a lookup table in the vendor tool

The GUI does `ax = AP_FlashSet.wPageOrderTable[wPageNo]` (384 entries at `0xC3634C`)
before calling `VP_ReadPage`. The table is filled from `0x8A157C` for everything except
`BIC6`, and that default table is **pure identity** — so for Hynix parts the page number
passes straight through. No remapping needed for us. (Note the table has **384**
entries; see the capacity section.)

---

## T6 — spare area (2048 bytes)

**Confirmed spare size.** `Flash.ini` (`FlashIniVer=043`), `[Hynix] Name004/005
SKV606411/12 = H25BFT8A1BDA`, ID `AD 7E 28 53 02 B0` — **our exact flash ID**:

```
UniName  FullName      V T C  Blks  PGs PZ D E  ID0  ID1  ID2  ID3  ID4  ID5 Ex DO P IF PL   Ed  Nm   SB  Gpio
SKV606411 H25BFT8A1BDA 3 2 1  2888 1536 16 1 2 0xAD 0x7E 0x28 0x53 0x02 0xB0 0  0 0 11  4 3000 001 2048 100
```
→ PageSize **16 KB**, SpareByte **2048**, Planes **4**, ECC **Rate 2**, TLC,
2888 blocks/CE, PageNum 1536. This nails `PLANE_SHIFT = 2` ⇒ **`PFRAG_NUM = 4`** and
`NAND_PAGE_SIZE = 18432`, which is exactly the `0x1200` measured in `LDPCENC+0x10`.

**Status: reachable in principle, not reachable through the existing payload.**
Neither MPTool version ever requests more than 16384 bytes from `CmdPageRead`, in any
configuration — **the vendor tool never touches the spare either.**

* In **LDPC mode** the spare is **not free**: `LDPCENC+0x10[12:0] = 18432` = 16384 user
  + 2048 parity. The 2048 bytes *are* the ECC. There is no metadata room there.
* In **raw mode** (`ldpc=0`) the NAND-bus length is 18880 bytes while the descriptor
  only sources 4 × 4096 = 16384 from SRAM. The remaining 2496 bytes are streamed from
  `0x0400F2C0 + 0x4000 = 0x040132C0` onwards `[INFER — the engine has a single length
  and a single base, so it must keep reading]`. So a raw full-page program can carry
  host-chosen spare bytes by `poke`-ing `0x040132C0..0x04013C3F` **before** the final
  chunk (the last-chunk `memcpy` only rewrites the first 16 KB, so the poke survives).
* Reading the spare back needs a non-zero **column**: `0x040DE038(addrword, block,
  handle, column=16384, fragmask=0)` → one 4 KB fragment starting at byte 16384.
  That is RECIPE D; the payload cannot express it.
* Cheap zero-risk probe before committing to any of this: do a chunk-0 read of a
  *programmed* page with `ldpc=1` and then `jd.g.rd(0x040132C0, 256)`. If the NAND→SRAM
  DMA really lands 18432 bytes at `0x0400F2C0`, that window will contain the ECC parity
  (high-entropy, not `0x5A`/`0x00`). On an *erased* page read raw it should be `0xFF`.

**Recommendation:** do not build the bad-block/metadata layer on the spare. Reserve
whole fragments or whole pages instead — e.g. page 0 of each block for a block header.
Cost is 1/1536 of capacity versus an unproven firmware path.

---

## ⚠️ Two capacity questions the vendor flash table opens up

`Flash.ini` for our part: `Blocks/CE = 2888`, `PageNum = 1536`, `PageSize = 16 KB`,
`Planes = 4`, `Die/CE = 1`. Sanity check against the drive:

```
2888 blocks x 1536 pages x 16384 B            = 72.7 GB = 1 die  (HYV7 readme: "64GB Die")
x 16 die (4 ch x 4 CE)                        = 1.16 TB = 1024 GiB = JD1024   <-- exact
```
That only balances if **`PageNum = 1536` counts all four planes**, i.e.
`1536 / 4 planes = 384 pages per (block, plane)`. Cross-checks: 384 = 128 word lines x 3
(TLC) and V6 is a 128-layer part; the vendor's `wPageOrderTable` has exactly **384**
entries; V7 gives 4224/4 = 1056 and V8 5712/4 = 1428, same 3x pattern.

### Q1 — `jdblk.SAYFA_BLOK = 1536` is probably 4x too large

`jdblk.r()/w()` use `rf = blk*4`, i.e. **plane 0 only**, and then index pages `0..1535`.
If a (block, plane) really holds 384 pages, everything from page 384 on is out of range
and will alias or fail. It has never been tested: §55.1 wrote 24 blocks x 16 pages, and
the deepest single-block test was **64 pages** on block 624.

`1536 x 4 KB` and `384 x 16 KB` are both 6 MB, which is why the current capacity figure
*looks* right — but today only the first 384 pages are real, so the true usable figure
is `384 x 4 KB = 1.5 MB` per entry, not 6 MB. Moving to 16 KB pages therefore restores
the 6 MB that `jdblk.py` already advertises.

**Test (cheap, 2 erases):** erase a good block; write page 0 and page 383 with distinct
patterns and read both back; then write page 384 and re-read page 0. If page 0 changed,
the page field wraps at 384. Set `SAYFA_BLOK = 384` and `PARCA = 4`.

### Q2 — three quarters of the drive is unaddressed: the plane axis

`rowfield = blk*4 + plane`, and `jdblk` always passes `plane = 0`. Planes 1, 2, 3 of
every block have never been written. If they are independent storage (they should be —
`0x8B BlockErase` takes a bare block number and erases the whole 4-plane unit, while
`0x89/0x8A` address one plane at a time), that is another **4x**.

**Test (cheap):** erase block B; write `rowfield = B*4+0` page 0 with pattern P0 and
`rowfield = B*4+1` page 0 with pattern P1; read both. Distinct data back ⇒ 4 independent
planes.

### Capacity ladder

| step | per (ch,ce,block) | total (if ~90 % good blocks) |
|---|---|---|
| today, honest (plane 0, 384 real pages, 4 KB) | 1.5 MB | ~62 GB |
| + RECIPE A/B (16 KB pages) | 6 MB | ~250 GB |
| + plane axis Q2 (4 planes) | 24 MB | **~1.0 TB** |

The 16 KB page is the prize you asked about; the plane axis is the same size again and
costs one changed line (`rf = blk*4 + plane`) plus the Q2 test.

## Hazards found while reading this code

| where | effect |
|---|---|
| `0x040C3E34` | `b .` — `nchunk > PFRAG_NUM` hangs the GDP main loop. Recover with `gdprun`. |
| `0x040C3E6C` | staging chunks return without writing `ctx[0x17]`; `getreturn()` reports the previous command |
| `0x04074EC0` | single 16 KB buffer shared by `0x8A` staging, `0x89` cache and cmd `0x4C` |
| `0x040C43C0` | `0x89` chunk index is **not** masked with 3 — `chunk>3` reads far past the cache |
| `0x040C4504` | pre-read zerofill is only `1<<geo[0x1D]` bytes (4096), so a failed read leaves 12 KB of stale data that looks like page content |
| `0x040C44C4` | `0x89` silently returns success-ish if `geo[0x310 + (ch|ce<<3|lun<<6)] == 0xFF` (die absent) |

---

## If the 16 KB round-trip fails — ordered checklist

1. **Fragment 0 correct, 1..3 wrong on a RECIPE-B write.** The staging chunks
   (`i=0,1,2`) never reach `0x040C3F38`, so they never touch the LDPC engine — only
   chunk 3 configures it. Suspect the chunk data going to the wrong slot: peek
   `0x04074EC0`, `0x04075EC0`, `0x04076EC0`, `0x04077EC0` after chunks 0..2 and before
   chunk 3; each must hold the corresponding 4 KB.
2. **All four wrong, status `0x01`.** The page was not erased, or an earlier
   `nchunk=0` write already programmed it. Erase and retry.
3. **Status `0x1B` / `poll fwcq timeout` on the read.** `0x040DBD44` timeout constant
   must be `300000` (RAPOR §51.1) — `jdblk.Blk.__init__` already pokes it, but a
   `gdprun` reload resets it.
4. **Fragment 0 correct, 1..3 wrong on a RECIPE-A read of an `ldpc=1` page.** Check
   the LDPC matrix load lengths: `0x040C6AA0` loads `*(u32)0x00000E70` bytes from RAM
   `0x1000` and `*(u32)0x00000E74` bytes from RAM `0x3928` (static `0x2928` / `0x16D0`),
   but `ortak.py:ldpc_yaz()` writes only `0x149C` / `0xB70` bytes. Verify what
   `jd.g.rd(0x0E70,8)` actually holds at runtime.
5. **Controller stops answering after the first `0x8A` with `nchunk=4`.** You hit the
   `b .` at `0x040C3E34`, i.e. `nchunk > PFRAG_NUM`. Run R0. `gdprun` recovers.
6. **`getreturn()` shows `0xAA` or a stale value.** Expected after chunks 0..2 — the
   staging return path at `0x040C3E6C` does not write `ctx[0x17]`.
7. **First ~4 KB valid, the rest `0x5A` or stale, status `0x01`.** The completion poll
   `0x040DBDCC(4, …)` counts **descriptors**, not fragments (4 descriptors:
   check-ready, switch-SLC, pre-read/program, data-out). A 16 KB data-out takes four
   times as long as the 4 KB one that path was tuned on. If the poll returns before the
   DMA drains, raise the timeout at `0x040DBD44` above 300000, or insert a short delay
   before the `0xC2`. Fill `0x0400F2C0` with `0x5A` before the read (RAPOR §54.3 rule 2)
   so a short transfer is visible instead of masquerading as data.

---

## Drop-in host code (not applied — `jdblk.py` left untouched on purpose)

```python
# --- add to jdblk.Blk ---------------------------------------------------------
# NOTE: plane is now an explicit axis (see "Two capacity questions", Q2).
BIRIM16 = 16384

def pfrag(s):
    """Read PFRAG_NUM live. MUST be 4 before using nchunk=4, else 0x8A hangs at 0x040C3E34."""
    import struct
    geo_ptr = struct.unpack("<I", s.g.rd(0x00000DCC, 4))[0]
    stpu    = s.g.rd(geo_ptr + 0x1C, 4)[3]          # geo[0x1F] STPU_SHIFT
    plsh    = s.g.rd(0x00009254, 2)[1]              # c0[0x9255] PLANE_SHIFT
    return 1 << (stpu - plsh - 3)

def r16(s, blk, pg, ch, ce, pln=0, ta=25.0):
    """Full 16 KB page read. The page must have been written with ldpc!=0."""
    rf = blk * 4 + pln
    r1 = s.g._faz1(pay(0x89, ch, ce, (rf >> 8) & 0xFF, rf & 0xFF,
                       (pg >> 8) & 0xFF, pg & 0xFF, 1, 1, 0, 0, 0), ta=ta)
    if not (r1 and r1["durum"] == 0):
        return None
    r2 = s.g.komut_prp(0xC2, (16384 >> 2, 0, 0, 0, 0x00123489, 16384 >> 9),
                       16384, ta=ta)
    return s.g.oku_prp(16384) if (r2 and r2["durum"] == 0) else None

def w16(s, blk, pg, ch, ce, d, pln=0, ta=25.0):
    """RECIPE C — vendor default: nchunk=0, one 16 KB data phase."""
    assert len(d) == 16384
    rf = blk * 4 + pln
    r1 = s.g._faz1(pay(0x8A, ch, ce, (rf >> 8) & 0xFF, rf & 0xFF,
                       (pg >> 8) & 0xFF, pg & 0xFF, 1, 1, 0, 0, 0), ta=ta)
    if not (r1 and r1["durum"] == 0):
        return False
    r2 = s.g.komut_prp(0xC1, (16384 >> 2, 0, 0, 0, 0x0012348A, 16384 >> 9),
                       16384, gonder=d, ta=ta)
    if not (r2 and r2["durum"] == 0):
        return False
    gr = s.j.getreturn()
    return bool(gr) and gr[0] == 0x01

def w16c(s, blk, pg, ch, ce, d, pln=0, ta=25.0):
    """RECIPE B fallback — chunked: 3 staging chunks + 1 that commits."""
    assert len(d) == 16384 and s.pfrag() == 4
    rf = blk * 4 + pln
    for i in range(4):
        r1 = s.g._faz1(pay(0x8A, ch, ce, (rf >> 8) & 0xFF, rf & 0xFF,
                           (pg >> 8) & 0xFF, pg & 0xFF, 1, 1, 0, 4, i), ta=ta)
        if not (r1 and r1["durum"] == 0):
            return False
        r2 = s.g.komut_prp(0xC1, (4096 >> 2, 0, 0, 0, 0x0012348A, 4096 >> 9),
                           4096, gonder=d[i * 4096:(i + 1) * 4096], ta=ta)
        if not (r2 and r2["durum"] == 0):
            return False
        # after i<3 the status byte is stale: the staging path at 0x040C3E6C
        # returns without writing ctx[0x17]
    gr = s.j.getreturn()
    return bool(gr) and gr[0] == 0x01
```

Bring-up order (each step is independently checkable, each is cheap):

1. `pfrag()` must return **4**. If not, stop — `nchunk=4` would hang the controller.
2. Erase a known-good block. `w16(blk, 0, ch, ce, os.urandom(16384))`, then
   `r16(blk, 0, ch, ce)`, compare all 16384 bytes. If it fails, try `w16c` (RECIPE B).
   → this alone is the 4x.
3. **Q1, page range:** write page 0 and page 383 with distinct patterns, read both back;
   then write page 384 and re-read page 0. If page 0 changed, `SAYFA_BLOK = 384`.
4. **Q2, plane axis:** erase block B, `w16(B, 0, ch, ce, P0, pln=0)` and
   `w16(B, 0, ch, ce, P1, pln=1)`, read both. Distinct data back ⇒ another 4x; make
   `plane` part of `jdblk.yer()`.
5. Re-run the strict bad-block scan over **full** pages — §55.2's criterion only ever
   looked at fragment 0 of plane 0.

Existing raw-written content is unreadable in `ldpc=1` mode — see the migration caveat
under RECIPE A.

---

## Consequences for conclusions already in RAPOR.md

* **§51.5 "one command = 4096 bytes"** — true only for `ldpc=0`, and only on the
  **read** side. It is one `moveq` at `0x040C4524`, not an architectural limit.
* **§51.5 / §50 "the other 12 KB is stale buffer leftovers"** — half right. The read
  never fetched them (mask 0), *and* the pre-read `zerofill` at `0x040C4504` only clears
  `1<<geo[0x1D]` = 4096 bytes, so the stale bytes were the previous command's.
* **§55.4 "writing chunks 0,1,2,3 doesn't work"** — with `payload[12]=0` that is four
  full 16 KB programs of the *same* cells. Not a firmware limitation, a missing byte.
* **Every page already on the drive holds 12 KB of junk after the 4 KB of real data**,
  because the program descriptor has always used mask 3. Harmless, but it means the
  drive is not "3/4 empty" — those cells are programmed and the blocks must be erased
  before any 16 KB rewrite.
* **§53.1/§53.2, the block-0 loader dump, is only 1/4 complete.** It was read at
  4 KB per page with `ldpc=0`, so the linear offsets in that section
  (`+0x000000`, `+0x000200`, `+0x008000`, `+0x010000`) are *fragment-0-only* offsets:
  `+0x8000` is really page 8 fragment 0, i.e. byte `8*16384 = 0x20000` of the block.
  Fragments 1..3 of every page in block 0 have **never been read**. If the `LDBK LDPC
  TABLE1/TABLE2` sections are larger than 4 KB, most of them is still unseen. Re-dump
  block 0 with patch **E1** (raw + full page) before concluding anything further about
  the vendor system area.
* **§52.4 / §55.2 bad-block criteria** only ever inspected fragment 0. A block that
  reads `FF` in fragment 0 can still be bad in fragments 1..3. The strict test must be
  re-run over full pages once RECIPE A/B work.
