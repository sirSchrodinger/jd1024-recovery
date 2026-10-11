# MAP1202 GDP firmware — descriptor / FCQ / NIFC static analysis

Scope: pure static RE of `c1.bin` (@0x040C0000) + `c0.bin` (@0x00000000).
Everything below is read out of the two images with `d.py`/`xref.py`. Where I
**infer** rather than read, it is marked `[INFER]`.

Config globals (`c0`) referenced everywhere are **runtime-populated** — in the
static image they read 0xAA (BSS/uninit), so their live values come from the
flash-geometry probe:
- `0x9244` = row-address shift `SH` (mask helper `(1<<(3-SH))-1`)
- `0x924A` = **SLC-mode flag** (0 = TLC/normal, 1/!=0 = SLC path)
- `0x9255` = LUN/CE shift base
- `0x9262` = SLC feature-address selector index
- `0x9264` = **data-out opcode selector** (0 → 0xB0, !=0 → 0xAE)
- `0x9266` = address-width flag (1 or 0x80)
- `0x926C` = configurable PROGRAM opcode
- `0x9210` = command payload buffer base (mode byte at +8, addr bytes at +9…)
- `0x0DCC` = pointer to geometry struct (fields: +0x1D LUN shift, +0x1E, +0x1F row-bits, +0xA planes, +9 CE count, +0x310 bad-block map base…)

---

## T1 — Descriptor struct (built on the stack, then submitted)

The **same** stack struct is built by ~25 builder functions and consumed by
**four** different ring-packer/submit functions, each of which packs the fields
into HW ring words differently. So the struct has one *semantic* layout (set by
builders) and four *packing* layouts (T4). Struct size 0x14 / 0x18 / 0x1C; it is
`memset(0)` first (`0x040C02B4` = zero-fill) in every builder except `0x040DC454`.

Builders find them by scanning `BL` to the four submit fns:
`0x040E3D48` (subA), `0x040E3F28` (subA2), `0x040EC240` (subB, takes handle+desc),
`0x040EBD8C` (subC, program), plus `0x040E3B54` (subD, raw-data-out).

### Semantic field map (from the builders)
| off | type | meaning | notes |
|-----|------|---------|-------|
| +0x00 | u32 | **NAND row/page address** (output of `0x040C8EC4`) — or a raw buffer pointer for data descriptors | becomes ring **word4** in every packer |
| +0x04 | u16 | **descriptor OPCODE** (FCQ command selector) | see T2 catalogue |
| +0x06 | u8  | cmd-phase / cmd-length modifier | 0,1,4 seen |
| +0x07 | u8  | address-cycle count | 4 normal, 1 in SLC |
| +0x08 | u8  | sub-field (low nibble used) | usually 0 |
| +0x09 | u8  | flag | usually 0 |
| +0x0A | u8  | **ring selector for subB/subD** (0 / 2 / else) | (in subA the selector is +0x0C) |
| +0x0B | u8  | flag / packed into word3 | usually 0 |
| +0x0C | u8  | subB→ word1[31:24]; **subA/subA2 ring selector** | usually 0 |
| +0x0D | u8  | flag (=1 in check-ready builders) | word1<<21 in subA |
| +0x0E | u16 (with +0x0F) | **column / byte count** (e.g. data-out length `strh r7`) | word3<<16 in subB |
| +0x10 | u8  | **CE/LUN index** (target die); becomes **8** in SLC | word3 nibble |
| +0x11 | u8  | **plane** = addr[9:8] | word3 field |
| +0x12 | u8  | 0 normally; **CE/LUN again in SLC** | word3 field |
| +0x13 | u8  | **CE bit-mask** — `0xFF` (all CEs) in check-ready; else small | subA→slot+0x16 |
| +0x14 | u16 | completion tag / length | subB→ word2[15:0] |
| +0x16 | u8  | extra addr byte (subA2/subD) | |
| +0x17 | u8  | control byte / addr (subA2/subD) | |

`0x040C8EC4(logical_addr,col)` packs the HW row address from CE|LUN|plane|block|page
using the geometry shifts (`0x0DCC`, `0x9255`, `0x9244`) — this is the address
the NIFC actually drives.

---

## T2 — Descriptor opcode catalogue (value stored at desc+4)

Extracted by locating every builder that `BL`s a submit fn and reading its
`strh rX,[sp,#4]`.

| opcode | builder | submit | sets handle[0xC]nib=2? | name / role |
|--------|---------|--------|------|-------------|
| 0x0C | 0x040DE694 | subB | **YES** | **READ PARAMETER PAGE / GetFlashParam** — WORKS, DMAs to 0x0400F2C0 |
| 0x1A | 0x040DE774 | subB | **YES** | read-param variant `[INFER read status/features page]` |
| 0x20 | 0x040DE848 | subB | **YES** | read variant `[INFER]` |
| 0x42 | 0x040DC454 | subA | n/a | **CHECK NAND READY** (auto read-status 0x70h) `[INFER 0x70]` |
| 0xF4 | 0x040DDB98 | subA | n/a | check-ready (prog / read-path-2) |
| 0x82 | 0x040DCEEC | subA | n/a | **PRE-READ** (issue 00h-30h, single-plane) `[INFER SP]` |
| 0x7E | 0x040DCF90 | subA | n/a | pre-read variant (multi-plane / cache) `[INFER MP]` |
| 0xB0 | 0x040DD010 / 0x040DD290 | subB / subD | **NO** | **DATA-OUT** (read data → DRAM), ECC path |
| 0xAE | (same, when `c0[0x9264]!=0`) | subB / subD | **NO** | **DATA-OUT alternate** = raw/ECC-bypass selector |
| 0xF2 | 0x040DD0E4 | subB | **NO** | data-out variant (cache / 2nd plane) |
| 0xD0 | 0x040DD850 | subA2 | n/a | **SWITCH TO SLC** (set-feature) |
| 0x3A | 0x040DD850 (when `c0[0x9262]==3`) | subA2 | n/a | switch-to-SLC variant |
| 0xE6 | 0x040DD954 | subA2 | n/a | slc/feature variant `[INFER]` |
| 0xBA | 0x040DC50C | subA2 | n/a | **SLC-mode prefix cmd** (issued before check-ready when SLC) |
| 0x64 | 0x040DD384 | subC | n/a | **PROGRAM (data-in, "prog wo")** |
| 0xF6 | 0x040DD43C | subC | n/a | program variant |
| (var) | 0x040DD4F4 | subC | n/a | program, opcode = `c0[0x926C]` |
| 0xE8/0xEC | 0x040DEA3C | subA2 | n/a | **PATTERN SET / raw data-in** (writes full row+col addr bytes) |
| 0xF8 | 0x040DEB34 | subA2 | n/a | **GET FEATURE** ("gbMatrixOdtEn get feature pev cmd") |
| 0xBC | 0x040DE5D4 | subA | n/a | unidentified `[INFER feature/read]` |
| 0xCE | 0x040DEC04 | subA2 | n/a | unidentified |
| 0x14 | 0x040DD604 | subA | n/a | unidentified |
| 0x46 | 0x040DD778 | subA | n/a | unidentified |
| 0xDA | 0x040DD6E0 | subA | n/a | unidentified |

**Answers to the specific asks:**
- **Raw / ECC-bypassed data-out**: opcode **0xAE** (0xB0 with `c0[0x9264]!=0`), and
  the *raw driver* is `gdp_nand_drv_raw_data_out` = **0x040DD290**, which submits
  via **subD 0x040E3B54** (word0 control bits `0x19000`, explicit buffer in word2)
  and does **not** use the ECC-handle nibble. This is the path the (working)
  bad-block scan uses.
- **Single-plane read**: pre-read **0x82** + data-out **0xB0** `[INFER]` (the
  0x7E/0xF2 pair is the multi-plane/cache variant used by read-path-2 0x040DE0E0).
- **Status read (0x70h)**: descriptor opcode **0x42** ("check nand ready") `[INFER]`.
- **RESET (0xFFh)**: NOT a descriptor — bare NIFC **routine 2** via `0x040E384C`.
- **READ ID (0x90h)**: NOT a descriptor — bare NIFC **routine 0x21** via `0x040E4630`
  `[INFER]` (or the dynamic-routine launcher 0x040CFF08).

---

## T3 — Opcode → NIFC routine number

**There is no firmware lookup table that maps a descriptor opcode to a NIFC
`+0x224` routine number.** Evidence:

- The descriptor opcode (desc+4) is written verbatim into **FCQ ring word0
  bits[15:0]** by all four packers and then the ring doorbell (`FCQ+0x40/0x44/0x48`)
  is rung. Nothing in firmware reads that opcode back to program `+0x224`.
- Every firmware site that *does* write NIFC `+0x224` is a **bare launcher**
  (non-descriptor path):
  - `0x040E384C` / `0x040E37E8` / `0x040C6DA0` → **routine 2 = NAND RESET (0xFFh)**
  - `0x040E4630` → **routine 0x21** (params → +0x22C/+0x230, CE=8) `[INFER READ ID / GET-FEATURE]`
  - `0x040CFF08` → routine = `*(u16)0x9934` (dynamic, from a config struct) — a
    generic single-command launcher (params from geometry shifts at 0x9934+0x10/0x12/0x14)

Conclusion `[INFER, strong]`: the **FCQ descriptor engine (HW @0x06600000)
consumes the 16-bit ring-word0 opcode and internally sequences the NIFC**; the
opcode *is* the routine selector for that engine. The only firmware-visible
routine numbers (2, 0x21, and the `0x9934` dynamic value) belong to the parallel
*bare* NIFC path, not to the descriptor path. No opcode→routine data table exists
in c0/c1.

---

## T4 — subB (0x040EC240) ring word bit map (and sub-paths)

`0x040EC240(handle=r6, desc=r4)`; slot base from desc+0x0A selector:
0 → ring `0x0400C900` (doorbell FCQ+0x40), 2 → `0x0400E100`+alt (FCQ+0x48),
else → `0x0400E100` (FCQ+0x44). Free-slot gate: `FCQ+0x4C/0x50` low16; a slot
whose control byte (`slot+0x17`) bit0 is set is busy → returns 0.

**word0** `[slot+0]`:
- [11:0] = desc[4] opcode  · [12] = **1 (const)**  · [14] = handle[8].bit3
- [17..] = desc[6]  · [22:20] = handle[0xC][31:29]  · [26:23] = desc[8][3:0]
- [28:27] = desc[9]  · [29] = handle[8].bit18  · [31:30] = desc[7]

**word1** `[slot+4]`:
- **[3:0] = handle[0xC][3:0]**  ← data-path / queue-mode nibble (see T5, the bug)
- [5:4] = handle[0xC][7:6]  · [15:12] = handle[0xC][19:16]  · [20:16] = handle[0xC][24:20]
- [21] = handle[8].bit4  · [31:24] = desc[0xC]

**word2** `[slot+8]`:
- [15:0] = desc[0x14]  · [31:16] = **handle index** = `(handle-0x04000000)/0x2C`
  (`0x040ED290` = signed divide; 0x2C = 44 = handle-struct size)

**word3** `[slot+0xC]`:
- [3:0] = desc[0x10] (CE/LUN)  · [.:4] = desc[0xB]  · [7:6] = desc[0x13]&3
- [11:8] = desc[0x11]&0xF (plane)  · [15:12] = desc[0x12]&0xF  · [31:16] = desc[0x0E] (u16)

**word4** `[slot+0x10]` = desc[0] (row address).  **slot+0x16** = handle[6]&0x7F.
**slot+0x17** = control: `(old&0xF9)|1`, then +2 (else-path) / +0 (sel0) / +4 (sel2)
= set "busy" bit0 and stamp the queue phase; `strh FCQ+0x40/44/48 → slot+0x14` (tail idx).

Sub-paths: `desc[0x0A]==0` (0x040EC42C) uses FCQ+0x40 ring 0x0400C900, control +0;
`desc[0x0A]==2` (0x040EC458) uses FCQ+0x48, control +4; else FCQ+0x44, control +2.

subA (0x040E3D48) differs: opcode|desc[6]<<14|desc[7]<<17|desc[8]<<20|desc[0xB]<<27|
desc[9]<<29|**0x2000**; word1 = desc[0xD]<<21|desc[0xF]<<24; **word2 = 0**.
subD (0x040E3B54) differs: word0 const **0x19000**, **word2 = caller buffer ptr**.

---

## T5 — Handle allocator (0x040DB828 → inner 0x040DB500)

`0x040DB500` calls `0x040E1384` to get a free index (0xFFFF ⇒ fail⇒return 0), then:

    handle = 0x04000000 + index*0x2C          (44-byte structs, based at 0x04000000)

Init (all handles):
- `+0x00` u16 = 0xFFFF  (completion tag = "pending")
- `+0x02` u16 = 0 ; `+0x04` u16 = 0
- `+0x06`  &= ~0x7F  (low-7 completion index cleared; feeds subB slot+0x16)
- **`+0x08` = 0**   (flags word; bits 3,4,18 feed word0/word1 — start 0)
- **`+0x0C` = 0**   (flags word; bits [3:0],[7:6],[19:16],[24:20],[31:29] feed word1/word0 — start 0)
- `+0x10` = `(CE & lunmask) | (plane<<lunshift) | 0x00FF0000 | 0xFF000000`  (CE/addr composite)
- `+0x14` = `0x040C8EC4(addr)` (row address) ; `+0x18` = 0
- if SLC (`c0[0x924A]!=0`): `+0x08 &= ~8` ; `+0x0C &= ~0xE0000000`

`0x040DB828` wraps it and stores the **handle index** (`(handle-0x04000000)/0x2C`)
as a u16 for the completion path.

**What sets the other handle[0xC] bits:** only the *builders* touch them, and only
the low nibble: **0x040DE694 / 0x040DE774 / 0x040DE848** do
`handle[0xC] = (handle[0xC] & ~0xF) | 2` right before their subB submit.
**0x040DD010 (0xB0 data-out) and 0x040DD0E4 (0xF2) do NOT.** Bits
[7:6]/[19:16]/[24:20]/[31:29] of handle[0xC] and 3/4/18 of handle[8] are left 0
throughout the read/param flow (no geometry-prep writes them in this path) —
they would only matter if some other command family set them `[INFER]`.

---

## T6 — Completion poller (0x040DBDCC; twin at 0x040DC198)

Signature `poll(count=r0, mode=r1, resultbuf=r2, r3, …)`.
- **What it polls:** FCQ `+0x74` low16 = #completions available; `+0x70`>>16 = head
  index. Completion ring at **0x0400E140** stride 16. Per completion it decodes
  CE/plane/block/page from `entry[0]` via the geometry shifts, validates with
  `0x040DBD68`, and on `mode` (r1 = 0/1/3/4) copies status bytes from
  `entry[+8]/[+0xC]` into `resultbuf`. It then clears the submit slot's busy bit
  (`0x0400C900 + idx*24 + 0x17` &= ~1) and bumps FCQ+0x70 consumer index.
- **`op`/count argument (r0):** it is the **number of completions to wait for**,
  not an opcode. Loop exits success when matched-count `sb >= count`.
  PageRead (0x040C4360) passes `count = (SLC?1:0)+4` = **4 or 5**;
  GetFlashParam (0x040C465C) passes `(SLC?1:0)+1` = **1 or 2**. (Task brief said
  5/6 and 2/3 — same idea, off-by-one vs my read; the value is a completion count.)
- **Timeout:** spin counter `r8` vs `*(u32)0x040DBD44 = 0x05F5E100 = 100,000,000`;
  on exceed prints `"[%s]poll fwcq timeout"` (fmt @0x040DBD4C, %s = "gdp_poll_fwcq_mix_filter"
  @0x040EE75E) and returns 0.

---

## T7 — Command 0x02 handler (0x040C3AE8) = "SCAN BB"

Confirmed dispatch-table entry: cmd 0x02 → 0x040C3AE8 (phase 0). It reads the mode
byte at `*(0x9210+8)` and prints `"[INFO] SCAN BB MODE:%02X gdp_scan_bb_way:%2X"`.
It is a **bad-block-scan command only** — it is a *bitmask* of scan strategies, NOT
a raw-dump/format entry point.

| mode | action |
|------|--------|
| 0x01 | reset BB counters (0x0DB8+4=0), then per-way scan via table 0x040D1530 (way0) or 0x040D2064 (way1) [sel = `c0[0x9245]`], driver 0x040CF8C8 |
| 0x04 | `0x040C3A68` → way0 `0x040D41A0` / way1 `0x040D4230` (the raw-read scan loop, see below) |
| 0x08 | `0x040D4400` (scan, resets BB@0x0DBC/0x0DBE, then `0x040C6AA0`) |
| 0x20 | `0x040C3A68` (same as mode 4) |
| 0x40 | `0x040D4370` → `0x040C6AA0` — **the confirmed-working bad-block scan** |
| other | ignored, returns 1 |

The scan loop (0x040D40C4…) issues **pre-read 0x82** per die/plane then polls; the
partner **raw data-out** is `gdp_nand_drv_raw_data_out` **0x040DD290** (opcode
0xB0/0xAE via subD 0x040E3B54), string "raw data out err" @0x040D4160.

**No mode of 0x02 does a full low-level format or system-area write.** A
`[PreFormat]` string exists @0x040C59E4 (a *different* command), and a UART-console
`"dump <addr> <row_cnt> <col_cnt>"` help string @0x040E5058 belongs to a separate
debug console, not the GDP dispatch table. Raw page data IS reachable through the
0x02 scan (modes 4/0x20/0x40) because those drive `raw_data_out` into DRAM at
0x0400F2C0 — that is the working raw-read reference.

---

## T8 — `0x040DC454` return / "nand not ready in read process"

Read process `0x040DE038`:
1. `r4 = 0x040DC454(handle,addr)` (op 0x42 check-ready) — `if r4==0 → "nand not ready in read process"`
2. `tst(0x040DD850(...), r4)` (switch-to-slc) — `if ==0 → "switch to slc submit cmd fail"`
3. `0x040DCEEC` (op 0x82 pre-read) — `→ "pre read submit cmd fail"`
4. `0x040DD010` (op 0xB0/0xAE data-out) — `→ "data out submit cmd fail"`

**Precise truth:** `0x040DC454` does **not** return a NAND ready *status* bitmask.
It returns the **boolean enqueue-success of subA (0x040E3D48)**: 1 iff the FCQ ring
accepted the 0x42 descriptor (engine present, a free slot exists, and the target
slot's control-byte bit0 was clear); 0 otherwise. `0x040DE038` `tst`s it with the
SLC-switch flag, but both are 1-bit values. The plane/CE *targeting* the task calls
a "mask" is computed inside the builder — `plane = addr[9:8]` (desc+0x11),
`CE/LUN = (addr>>10) & ((1<<(3-c0[0x9244]))-1)` (desc+0x10), and CE-bitmask
`desc+0x13 = 0xFF` (all CEs) — but that is written *into the descriptor*, not
returned. So "nand not ready in read process" fires when the **0x42 descriptor
could not be queued**, e.g. FCQ has no free slot or the engine isn't idle — a
queue/engine condition, despite the wording.

---

## THE LIKELY BUG (why PageRead 0x89 returns no data while 0x0C works)

Only structural difference between the **working** param-read and the **failing**
PageRead data-out, both subB→0x0400F2C0:

| | GetFlashParam 0x0C (0x040DE694) | PageRead data-out 0xB0 (0x040DD010) |
|--|--|--|
| submit | subB 0x040EC240 | subB 0x040EC240 |
| `handle[0xC] = (…&~0xF)|2` before submit | **YES** | **NO (stays 0)** |
| ⇒ ring **word1[3:0]** | **2** | **0** |

`word1[3:0]` (= handle[0xC][3:0]) is the only differing engine field. The working
raw-scan read avoids the issue entirely by using subD (0x040E3B54), which ignores
handle[0xC]. => word1[3:0]=2 is very likely the "produce a data-out DMA" mode the
data-out descriptor is missing.

---

## RANKED, DIRECTLY ACTIONABLE EXPERIMENTS (for the hardware side)

**E1 — Set the missing data-path nibble on PageRead's data-out (primary fix).**
In builder `0x040DD010` the handle is `sb`(=r9) and it is loaded into r0 right
before `bl 0x040EC240` at `0x040DD0D8`. Make it mirror the working param-read:
insert (code-cave / trampoline) immediately before `0x040DD0D8`:

    ldr r0,[r9,#0xc]        ; E599_000C
    bic r0,r0,#0xf          ; E3C0_000F
    add r0,r0,#2            ; E280_0002
    str r0,[r9,#0xc]        ; E589_000C
    mov r0, r9   (restore)  ; the original 0x040DD0D4 already does mov r0,sb

Equivalent DRAM poke if a memory-write primitive exists: at
`handle = 0x04000000 + handle_index*0x2C`, set `*(u8)(handle+0x0C) = (*(u8)(handle+0x0C) & ~0x0F) | 0x02`
between the pre-read and the data-out. Expected: cmd 0x89 starts returning page
data at 0x0400F2C0 (this is the ONLY engine field that differs from the working
cmd 0x10 / 0x0C).

**E2 — Confirm the hypothesis without patching: instrument ring word1.**
Run cmd 0x10 (GetFlashParam, works) and cmd 0x89 (PageRead) and dump the FCQ ring
slot at `0x0400E100 + slot*24 + 4` (word1) for the data-out descriptor. Predicted:
works → word1[3:0]=2, PageRead → word1[3:0]=0. Confirms E1 before committing a patch.

**E3 — Read raw NAND today via the already-working path.**
Issue cmd **0x02 with mode byte (payload+0) = 0x40** (or 0x04) — the bad-block scan
that works. It drives `gdp_nand_drv_raw_data_out` (0x040DD290 → subD 0x040E3B54)
and lands raw page bytes in DRAM at **0x0400F2C0**; read that buffer back. This is
the fastest way to get NAND contents while PageRead is being fixed.

**E4 — Direct raw dump call.** Call `0x040DD290(rowaddr, col, r2, r3, buf@sp+0x24,
c0[0x9264]-selects-0xAE/0xB0, len@sp+0x20…)` — the `gdp_nand_drv_raw_data_out`
driver — with a DRAM buffer; it bypasses the handle[0xC] issue entirely (subD does
not read handle[0xC]).

**E5 — ECC vs raw toggle.** Flip `c0[0x9264]` (0 → opcode 0xB0, !=0 → 0xAE) and
repeat E1/E3 to see whether the delivered data is ECC-corrected (0xB0) or raw
(0xAE). Tells you which opcode gives ECC-bypassed bytes.

**E6 — Ring sub-path.** On the data-out descriptor, try `desc+0x0A = 2` (routes via
FCQ+0x48 alt ring, control phase +4) instead of 0/else, to test whether the
data-producing queue is a different ring than the command queue.

**E7 — RESET / READ-ID sanity (bare NIFC path, no descriptors):**
`0x040E384C(ch, ce_mask)` = routine 2 = NAND RESET(0xFF);
`0x040E4630(ch, r1, r2, r3)` = routine 0x21 [INFER READ ID/GET-FEATURE] — use to
verify the die responds independently of the FCQ descriptor engine.
