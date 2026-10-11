# MAP1202 — NIFC register map, routine microcode, and bare-metal NAND driving

Pure static RE of `c1.bin` (@`0x040C0000`, 0x30000 bytes) + `c0.bin` (@`0x00000000`, 0xC000 bytes).
No hardware was touched to produce this document.

Conventions:
* **READ** = literally decoded out of the image (address given).
* **[INFER]** = my interpretation on top of what is read. Weight noted.
* **[UNKNOWN]** = cannot be answered from these images; said so instead of guessed.

`N(ch)` throughout means the per-channel NIFC block base `0x06641000 + ch*0x1000`.
`G` means the global NIFC block `0x06640000`. Note `N(ch) == G + 0x1000 + ch*0x1000`;
the firmware itself uses both forms (e.g. `0x040E4998`), so they are the same aperture.

---

## 0. Executive summary — the two things that matter

1. **The NIFC routine number IS an address.** The "routine microcode" is a table the
   firmware *uploads at init*: `memcpy(0x06649000, 0x040EE836, 0xC90)` at `0x040C7DA4`
   and `0x040E3900`. **Routine `N` executes the program at `0x06649000 + N*0x10`.**
   Proven below by five independent legacy/toggle routine pairs. This means you can
   **write your own routine** into the microcode RAM and then trigger it with a normal
   `+0x224` / `+0x220` launch — a fully programmable NAND sequencer, no descriptors.

2. **The firmware already contains four complete bare-metal PIO primitives** that never
   touch the FCQ/descriptor engine. The best one is `0x040E3150`
   (read NAND status → byte in `+0x240`). They all begin with a *channel soft reset*
   (`+0x004` bit0 low/high), which is why they cannot hang — and which is exactly what
   `0x040E384C` (the RESET launcher that does hang) is missing.

---

## 1. NIFC register map

### 1.1 Per-channel block `N(ch) = 0x06641000 + ch*0x1000`

| off | dir | meaning | evidence |
|-----|-----|---------|----------|
| `+0x000` | rw | bits 0,1,2 set then cleared around PHY training; DQ/DQS gate enables **[INFER]** | `0x040E2A28`…`0x040E2A88` |
| `+0x004` | rw | **bit0 = channel FSM enable / soft-reset.** Clear → 3×NOP → set = abort + resync. Used at the head of *every* non-hanging primitive | `0x040E28E0`, `0x040C6FEC`, `0x040E3168`, `0x040E33B4`, `0x040E4470`, `0x040E4578` |
| `+0x010..+0x02C` | — | never accessed by GDP firmware. The `aaaaaaaa/00555555/00aaaaaa` you observed are power-on defaults or come from `LDBK CONFIG` at product-fw boot | absence in full scan |
| `+0x018/+0x01C` | rw | pair, written in the PHY block | `0x040E27D0`, `0x040E2E30` |
| `+0x020/+0x024` | rw | pair, PHY | `0x040C7D04`, `0x040E2CD8`, `0x040E2E74` |
| `+0x030` | rw | PHY | `0x040C6D58`, `0x040E27E4`, `0x040E2E48` |
| `+0x034` | rw | bit16 = **legacy(=1) / toggle(=0)** companion to `+0x204` bit0; bit1 set by `0x040E2C8C` | `0x040E2B74`, `0x040E2C18`, `0x040E2C9C` |
| `+0x044` | rw | per-lane trim, 8 slots — used by the BDL/deskew sweep | `0x040D51E4`…`0x040D52A0` |
| `+0x074` | rw | **delay-line selector**: `[3:0]` = DQ lane index, `[18:16]` = sub-line (0/1/2) | `0x040C81B8`, `0x040E30A0` |
| `+0x078` | rw | `[8:0]` = 9-bit delay value (second bank) | `0x040C81E0` |
| `+0x07C` | rw | `[8:0]` = 9-bit delay value (`0x100` = mid-scale default) | `0x040C81D0`, `0x040E30BC` |
| `+0x0A0..+0x0B4,+0x0F4` | rw | DCC / duty-cycle block | `0x040C9BE8`…`0x040C9C94` |
| `+0x200` | w | 4×8-bit bus timing. Legacy: `0x02020202`. Toggle: `(v\|v<<8)\|0x01010000` where `v = (0x1F3F + freq_MHz*284)/0x1F40` | `0x040E2B88`, `0x040E2C2C` |
| `+0x204` | rw | **bit0 = DDR/toggle-mode flag.** Every primitive reads it to pick between the legacy and toggle routine number | write `0x040E2B70`, `0x040E2C14`; read ×12 incl. `0x040E3198`, `0x040E441C`, `0x040E45A8` |
| `+0x208` | — | **never read or written** by c0/c1. [UNKNOWN] |
| `+0x20C` | rw | `[7:0]` = per-channel CE/bank presence mask (one byte per channel, from the geometry probe) | `0x040C3468`, `0x040C358C`, `0x040C8E58` |
| `+0x210` | rw | **DQS MASK** (string `"DQS MASK [%X]"` @`0x040C8B58`). `0x0F000400` / `0x0F000800`, or `*(u32)(0x200+0x94+ch*4)` from the TMC block | `0x040C843C`, `0x040C8B50`, `0x040E2F50`, `0x040E2F84` |
| `+0x214` | — | **never read or written** by c0/c1. Your observed `0x1f001f00` is a reset default or a `LDBK CONFIG` boot write. [UNKNOWN] |
| `+0x218` | rw | **engine status / error latch.** Write `\|= 0x1F` = write-1-to-clear of 5 sticky bits; read `& 0xFF` = the value every primitive returns as `err`. `0 == clean` | clear: `0x040E3164`, `0x040E33B0`, `0x040E446C`, `0x040E4574`, `0x040C6FE8`; read: `0x040E3208`, `0x040E3478`, `0x040E4530`, `0x040E4624`, `0x040C7070` |
| `+0x21C` | r | **bit0 = engine idle / routine complete.** 45 read sites, 0 writes | e.g. `0x040E318C` |
| `+0x220` | rw | **bit0 = GO** (start the routine in `+0x224`). Set with `orr #1`; hardware self-clears | 24 sites, e.g. `0x040E31E8` |
| `+0x224` | rw | `[15:0]` = **routine number** (see §2). Always written with `bfi rX,rN,#0,#16` so bits 31:16 are preserved | 25 sites |
| `+0x228` | rw | `[3:0]` = **CE / bank index** (0..7). Special value **8** = "take the CE from `+0x22C[3:0]`" (selected by the global flag at `0x00010AD0`) | 26 sites |
| `+0x22C` | w(r) | **parameter word 0.** `[3:0]` = CE/bank (alternate path), `[11:8]` = LUN/target, `[31:16]` = address bytes 0,1 | 32 writes |
| `+0x230` | w | **parameter word 1.** `[15:0]` = address bytes 2,3; `[31:16]` = length / extra | 12 writes |
| `+0x234` | w | **row address**, full 32-bit, pre-shifted by the geometry | `0x040C76B8`, `0x040CFEDC`, `0x040CFF5C`, `0x040D014C`, `0x040E44DC` |
| `+0x238` | rw | `[7:0]` = a count, written as `r2 + 0xF1` | `0x040CFCEC/0x040CFCF4` |
| `+0x240` | r | **PIO data-in register, word 0.** This is where the NAND status byte and the 8-byte ID land | `0x040CFD1C`, `0x040D00D8`, `0x040E3200`, `0x040E3470`, `0x040E4528`, `0x040E461C` |
| `+0x244` | r | **PIO data-in register, word 1** (bytes 4..7) | `0x040E4618` |
| `+0x24C`, `+0x250` | — | **never accessed.** [UNKNOWN] |
| `+0x280` | rw | misc | `0x040C7A5C`, `0x040E2D24` |
| `+0x310` | rw | bit0 set per channel during the init handshake | `0x040E49A4` |

**`+0x240` is not "the last command byte"** — it is the head of the PIO read path. Every
primitive that wants data reads `+0x240` (and `+0x244` for 8-byte reads) *after* the
routine reports idle. **READ**.

### 1.2 Global block `G = 0x06640000`

| off | meaning | evidence |
|-----|---------|----------|
| `+0x000` | global cfg, `[15:0]=0x8079` | `0x040C7BA0`, `0x040C7C40`, `0x040E2854` |
| `+0x008` | `0x39D807F0`, later `[15:0]=0x07F0` | `0x040C7BA8`, `0x040C7C50` |
| `+0x010` | `[31:16] += 0x0278` | `0x040C7BB8` |
| `+0x01C..+0x03C` | PHY constant block: `0x127803F8`, `0x3398027C`, `0x00193018`, `0x07F207F4`, `0xB83896F8`, `0x06743218`, `0x783856F8`, `0x22184079` | `0x040C7BC0`…`0x040C7C04`, mirrored at `0x040E2864`…`0x040E289C` |
| `+0x040/+0x044` | `[15:0]=0x1278` / `0x8079`, then `+0x040 += 0x30180000` | `0x040C7C0C`… |
| `+0x060..+0x06C` | 4 registers × 4 channels of PHY trim | `0x040E2538`… |
| **`+0x070`** | `[15:0]` and `[31:16]` = **two 16-bit counters**. Default `0x1388`(5000) / `0x1F40`(8000); overridden from TMC `*(u16)(0x200+0xB4)` and `*(u16)(0x200+0xB6)` | `0x040E2B8C`, `0x040E2C4C` |
| **`+0x074`** | `[15:0]` / `[31:16]` = two more. Default `0x32`(50) / `0`; from TMC `*(u16)(0x200+0xB8)` / `*(u16)(0x200+0xBA)` | `0x040E2BA8`, `0x040E2C6C` |
| `+0x07C..+0x088` | 4 more PHY regs × 2 | `0x040E2650`… |
| `+0x100` | bit0 = enable; `[10:8]` = `geo[0x18]+geo[0x1B]-9` (address-width) | `0x040E4968`, `0x040E498C` |
| `+0x114`,`+0x11C`,`+0x120`,`+0x124`,`+0x128` | calibration block | `0x040E49F4`…`0x040E4AD0` |
| `+0x130` | bit0 = start | `0x040E49BC` |
| `+0x134` | bit0 = **busy**; the init spins `while (G[0x134]&1)` | `0x040E49CC` |
| `+0x300/+0x304` | PHY | `0x040E295C`, `0x040E2A00` |
| `+0x344/+0x348` | used by the BB-scan / read-retry path | `0x040D4D9C`… |

---

## 2. T1 — the routine table and the microcode

### 2.1 Where the microcode comes from (READ)

Two `memcpy(dst,src,len)` calls (`0x040E854C` is a plain byte/word memcpy, verified at
`0x040E855C`: `ldrb r3,[r1],#1 / strb r3,[r0],#1`):

```
0x040C7D98 / 0x040E38F4 :  memcpy(0x06649000, 0x040EE836, 0x0C90)   ; "A" table
0x040C7DA8 / 0x040E3908 :  memcpy(0x06650000, 0x040EF4C6, 0x0408)   ; "B" table
```

Source bytes live in `c1.bin` at file offsets `0x2E836` (len `0xC90`) and `0x2F4C6`
(len `0x408`) — the two blobs are **contiguous** in the image.

Full NAND bring-up sequence, `0x040E38D8` (READ):

```
0x040E38DC  bl 0x040E27B8          ; PHY pre
0x040E38E0  bl 0x040E4A8C          ; G+0x114 block
0x040E38E4  bl 0x040E28D4          ; NIFC soft reset, all 4 channels  (see T4)
0x040E38E8  bl 0x040E2F40          ; N[0x210] = 0x0F000800 (DQS mask), all ch
0x040E38F0  bl 0x040E2B48(r0=1)    ; mode=toggle, N[0x204].0, N[0x034].16, N[0x200], G[0x70/0x74]
0x040E38FC  memcpy(0x06649000, 0x040EE836, 0xC90)     <-- UCODE A UPLOAD
0x040E3904  bl 0x040E3898          ; routine 2 on all 32 dies (RESET)
0x040E3910  memcpy(0x06650000, 0x040EF4C6, 0x408)     <-- UCODE B UPLOAD
0x040E3918  bl 0x040E3600          ; poll status on all 32 dies
0x040E391C  bl 0x040E37E8          ; routine 5/0x24 (or 7/0x27) on all 32 dies
0x040E392C  b  0x040E3718
```

Note the A table is uploaded **before** the first RESET — it has to be, because RESET is
routine 2 and routine 2 lives in that table.

The other upload site is in the controller init chain, and it *is* on the path your
recipe takes: `0x040C0DA8` (the top-level init that prints `"normal flow"`,
`bIf_Power_On`, `wFreq_Val`, `bTiming_Mode`, `bHigh_Speed_Set`,
`bOutput_Drive_Strength`, `nops_rty_*`, `nphy_io_tx[]` — i.e. the `0x11 InitGDP`
parameter dump **[INFER, strong]**) → `0x040C1014` → `0x040C8E70` → `0x040C8EB0` →
`0x040C7D74` → the two memcpys at `0x040C7DA4` / `0x040C7DB4`. **So the microcode is
already in `0x06649000` after your `0x11 InitGDP` step**, and a level-3 channel reset
does not disturb it.

### 2.2 File format (READ + [INFER] on field widths)

Both blobs share a 32-byte header then a flat array of 16-byte slots:

```
+0x00  16 bytes : name, ours = "LOOT" + 12×00
+0x10  u16 0x0021, u16 0x0016, u32 0x13163154, u32 0x00002408, u32 0x00010112
+0x20  first routine slot
```

The header is 2 slots long, so **routine 0 and routine 1 are the header** — they are
reserved/unused. Slot `N` starts at blob offset `N*0x10`, i.e. at
**`0x06649000 + N*0x10`** once uploaded.

The vendor's own per-frequency ucode files in `~/jd1024/kanit/skv6_ucode/` are the
same format with a different name field: `HYV7_DAT_ucode__SKV6_001_400.A_2192.bin`
starts `"CLT_5V_XINYH"` + `21 00 04 00 …` and its body begins
`0b08 0000 eb28 0000 4805 80ff` — byte-for-byte the same opcodes as our A table
(`0b08 0000 eb30 0000 4805 80ff`), only the delay constants differ. The `.rec16k`
container's section table at offset `0x20` is `(0x1000, 0x890)` and `(0x2000, 0xd10)`
= the A and B sections. **So the vendor ships per-frequency replacements for exactly
these two blobs.** Our build's A is `0xC90` and B is `0x408` (different sizes from the
HYV7 `0x890`/`0xD10`, i.e. a different routine set).

### 2.3 Instruction encoding

A routine is a list of **32-bit little-endian words**, terminated by a word with
**bit 31 set**, then zero-padded up to the next 16-byte boundary. Parsing all 0xC90
bytes of the A blob with that single rule yields **69 routines, every one 16-byte
aligned, every one zero-padded — zero exceptions**. That self-consistency is the proof
that the rule is right. (Parser: `.../scratchpad/nifc/parse.py`.)

Word layout: `byte0 = opcode`, `byte1 = sub-field`, `bytes[3:2] = operand16`,
bit31 = END.

| opcode | count | meaning | evidence |
|--------|-------|---------|----------|
| `0x48` | 116 | **ISSUE NAND COMMAND**, command byte = bits `[31:24]`, bit23 = flag. `byte1` always `0x05` | routine 2 = `FF800548` and routine 2 is the RESET routine (`0x040E384C`, `0x040E3898`) → command byte `0xFF` = NAND RESET. Cross-checks: routine `0x30` = `0x70`, routine `0x3D` = `0x30`, routine `0x3F/0x41/0x57/0x66/0x88` start with `0x00` |
| `0xEB` | 171 | **DELAY**, count = bits `[30:8]`. Seen: 8, 9, 0x14, 0x30, 0x3C, 0x50, 0xA0, 0xE0, 0x100, 0x1E0, 0x280, 0x320, 0x700, 0x820 | — |
| `0x50` | 94 | **ADDRESS / operand cycles**, count-or-selector in `[30:24]`, source field in `byte1` (`0x05`, `0x09`, `0x0D`, `0x15`). `val=0` on routines that take no address (routine `0x30` = 70h) | [INFER, strong] |
| `0xA0` | 47 | always `058005A0`; appears right after a `0x50` — second half of an address phase, or R/B wait | [INFER] |
| `0x0B` | 76 | prologue `0000080B` (legacy) and epilogue `8000290B`; also `8000150B`, `8000A10B`, `8002300B`, `8007800B` | [INFER: CE assert / deassert + END] |
| `0x52` | 8 | **PIO DATA-IN terminator.** `81000452` (1 unit) on the 1-byte status routines that `0x040E3150`/`0x040E4410` read from `+0x240`; `82001252` (2 units) on routine 3 = ReadFlashID, which reads **both** `+0x240` and `+0x244` (8 bytes). So `val` = number of 32-bit words latched into the PIO registers | [INFER, strong — the val matches the byte count the firmware reads] |
| `0x3B` | 20 | burst terminator on the toggle-mode and data-out routines | [INFER] |
| `0x41`,`0x45`,`0x56`,`0x58`,`0x40` | few | other terminators | [INFER] |
| `0x1B`,`0x8B`,`0x2B`,`0xD2`,`0x76`,`0x7B`,`0x65`,`0x98`,`0xC1`,`0xFB` | many | the DDR/toggle burst block: `1B 09 / 8B 05 / 2B 29 / 76 13 / 2B 31 / 3B 29` appears verbatim at the end of every data-out routine | [INFER: FIFO/DMA burst control] |

### 2.4 The proof that routine N ↔ `0x06649000 + N*0x10`

The firmware picks between a *legacy* and a *toggle* routine number based on
`N[0x204] & 1`. Five such pairs are visible in the code; decoding both slots and
comparing the NAND command byte:

| firmware site | legacy rtn | toggle rtn | slot `0x*10` cmd (legacy) | slot cmd (toggle) | match |
|---|---|---|---|---|---|
| `0x040E45BC` (`0x040E455C`, ReadFlashID) | 3 | 0x17 | `0x48` | `0x48` | ✅ |
| `0x040E32F8` (`0x040E32C0`) | 5 | 0x24 | `0x77` | `0x77` | ✅ |
| `0x040E3400` (`0x040E3398`) | 9 | 0x2A | `0x77` | `0x77` | ✅ |
| `0x040E31A4` (`0x040E3150`, read status) | 0x0D | 0x32 | `0x38` | `0x38` | ✅ |
| `0x040E4548` (`0x040E4410`) | 0x0F | 0x35 | `0x3C` | `0x3C` | ✅ |
| `0x040E348C` (`0x040E3398` alt) | 0x0B | 0x2D | `0x6A` | `0x6A` | ✅ |
| `0x040E3390` (`0x040E32C0` alt) | 7 | 0x27 | `0x6A` | `0x6A` | ✅ |

Seven independent pairs, each landing on the same NAND command byte, at slots computed
purely as `routine*0x10`. Plus routine 2 → `0xFF` = RESET, which is independently known
from the firmware. **This is READ, not inference.**

### 2.5 Complete routine catalogue (A table @ `0x06649000`)

`slots` = how many 16-byte slots the routine occupies (so the next free routine number
is `rtn + slots`). "NAND cmd bytes" = the `0x48`-opcode operands in program order.

| rtn | ucode addr | slots | NAND cmd bytes |
|-----|-----------|-------|----------------|
| **0x02** | `0x06649020` | 1 | FF |
| **0x03** | `0x06649030` | 2 | 48 |
| **0x05** | `0x06649050` | 2 | 77 |
| **0x07** | `0x06649070` | 2 | 6A |
| **0x09** | `0x06649090` | 2 | 77 |
| **0x0B** | `0x066490B0` | 2 | 6A |
| **0x0D** | `0x066490D0` | 2 | 38 |
| **0x0F** | `0x066490F0` | 2 | 3C |
| **0x11** | `0x06649110` | 2 | 3C |
| **0x13** | `0x06649130` | 2 | 02,70 |
| **0x15** | `0x06649150` | 2 | 40,88 |
| **0x17** | `0x06649170` | 3 | 48 |
| **0x1A** | `0x066491A0` | 1 | 76 |
| **0x1B** | `0x066491B0` | 1 | 76 |
| **0x1C** | `0x066491C0` | 2 | 2D,5A,00,98 |
| **0x1E** | `0x066491E0` | 3 | 71 |
| **0x21** | `0x06649210` | 3 | 71 |
| **0x24** | `0x06649240` | 3 | 77 |
| **0x27** | `0x06649270` | 3 | 6A |
| **0x2A** | `0x066492A0` | 3 | 77 |
| **0x2D** | `0x066492D0` | 3 | 6A |
| **0x30** | `0x06649300` | 2 | 70 |
| **0x32** | `0x06649320` | 3 | 38 |
| **0x35** | `0x06649350` | 3 | 3C |
| **0x38** | `0x06649380` | 3 | 3C |
| **0x3B** | `0x066493B0` | 2 | 30,E8 |
| **0x3D** | `0x066493D0` | 2 | 30 |
| **0x3F** | `0x066493F0` | 2 | 00,98 |
| **0x41** | `0x06649410` | 2 | 00,99 |
| **0x43** | `0x06649430` | 3 | 40 |
| **0x46** | `0x06649460` | 3 | 40 |
| **0x49** | `0x06649490` | 3 | 40 |
| **0x4C** | `0x066494C0` | 3 | 40 |
| **0x4F** | `0x066494F0` | 3 | 02,70 |
| **0x52** | `0x06649520` | 5 | 3C,02,70 |
| **0x57** | `0x06649570` | 5 | 3C,00,02,70 |
| **0x5C** | `0x066495C0` | 5 | 3C,03,70 |
| **0x61** | `0x06649610` | 5 | 70,3C,02,70 |
| **0x66** | `0x06649660` | 6 | 70,3C,00,02,70 |
| **0x6C** | `0x066496C0` | 5 | 70,3C,03,70 |
| **0x71** | `0x06649710` | 4 | 3C,42 |
| **0x75** | `0x06649750` | 4 | 3C,42 |
| **0x79** | `0x06649790` | 5 | 70,3C,42 |
| **0x7E** | `0x066497E0` | 5 | 70,3C,42 |
| **0x83** | `0x06649830` | 1 | — |
| **0x84** | `0x06649840` | 2 | 6D,40,88 |
| **0x86** | `0x06649860` | 1 | 4B |
| **0x87** | `0x06649870` | 1 | 4A |
| **0x88** | `0x06649880` | 4 | 00,02,70 |
| **0x8C** | `0x066498C0` | 2 | 7C |
| **0x8E** | `0x066498E0` | 2 | 6C |
| **0x90** | `0x06649900` | 4 | 02,70 |
| **0x94** | `0x06649940` | 3 | 02,70 |
| **0x97** | `0x06649970` | 1 | — |
| **0x98** | `0x06649980` | 3 | 38 |
| **0x9B** | `0x066499B0` | 4 | 3C,1B,8B |
| **0x9F** | `0x066499F0` | 6 | 3C,1B,8B |
| **0xA5** | `0x06649A50` | 8 | 3C,1B,8B |
| **0xAD** | `0x06649AD0` | 4 | 3C,1B |
| **0xB1** | `0x06649B10` | 3 | 2E,62,2A,FF |
| **0xB4** | `0x06649B40` | 2 | — |
| **0xB6** | `0x06649B60` | 1 | — |
| **0xB7** | `0x06649B70` | 2 | — |
| **0xB9** | `0x06649B90` | 2 | 42,88 |
| **0xBB** | `0x06649BB0` | 2 | 00,DD |
| **0xBD** | `0x06649BD0` | 4 | 3C,42 |
| **0xC1** | `0x06649C10` | 2 | 38 |
| **0xC3** | `0x06649C30` | 4 | 51,D7 |
| **0xC7** | `0x06649C70` | 2 | 50 |

### 2.6 Vendor names for the two tables (corroborated independently)

The MPTool/SORT images name these objects explicitly:

* `nifc_cmd_bin` = the A table → our `0x06649000`
* `nops_op_bin`  = the B table → our `0x06650000`
* `bNifcCmdMap`  = `uint8[256]`: *logical firmware op* → *routine slot*. **The GDP does not use it** — it writes raw slot numbers into `+0x224`.
* `wNopsCmdMap`  = `uint16[512]`: *logical op* → *nops entry byte offset* (value/2 = entry index).
* Host-side upload entry points in `MXMPTool_MAP1202_USB_V1_1_26.exe`:
  `Write_Cougar_GDP_FW_CMD_BIN` / `Write_Cougar_GDP_FW_OP_BIN` — one per table,
  matching the GDP's two separate memcpys.

`nops_op_bin` entry = **8 bytes**:

```
+0 u16 flags/cond
+2 u16 opcode/next
+4 u16 wait      : bits[13:0] = count, bits[15:14] = which nops_tmr_unN to count in
+6 u8  NIFC routine number   <-- the same 16-byte slot index
+7 u8  flags {00,10,50,80,90}
```
In the vendor SKV6 image **414/414** entries have a `+6` byte that is a valid parsed
routine start — so NOPS is the higher-level flow engine and NIFC routines are its
instruction set.

### 2.7 ⭐ The vendor tables contain routines ours does not

Our GDP `nifc_cmd` image contains **no `0x90` command byte at all** — there is no
JEDEC READ-ID routine in it. The vendor SKV6 (Hynix V6, our exact NAND family) image
`~/jd1024/kanit/skv6_ucode/HYV7_DAT_ucode__SKV6_001_400.A_2192.bin` **does**:
its slot `0x39` is `00 90` (READ ID). Since the table is position-independent
microcode and the slot addressing is `base + N*0x10`, **a routine can be lifted out of
the vendor image and dropped into a free slot of ours.** That is the cleanest way to
get a capability the GDP build lacks.

---

## 3. T2 — the PIO data path

| you want to… | register | notes |
|---|---|---|
| **(a) place a command byte** | **not a register.** The command byte is baked into the microcode `0x48` instruction at `ucode_slot + k*4`, bits `[31:24]` | so "issue command X" = write X into the routine, or pick a routine that already issues X |
| **(b) place address bytes** | `+0x22C` `[3:0]`=CE (alt), `[11:8]`=LUN/plane, `[31:16]`=addr bytes 0,1 · `+0x230` `[15:0]`=addr bytes 2,3, `[31:16]`=length · `+0x234`=full 32-bit row address | see the three packings in §3.1 |
| **(c) read data bytes back** | **`+0x240`** (bytes 0-3) and **`+0x244`** (bytes 4-7), read *after* `+0x21C` bit0 goes 1 | `0x040E4618/0x040E461C` reads both; `0x040E3200` reads one byte |
| **(d) read the die's raw status** | **`+0x240` bits[7:0]** after running a status routine | `0x040E3204: strb r1,[r2]` where `r1 = N[0x240]` |
| engine error/timeout | **`+0x218` bits[7:0]**, `0` = clean; clear with `+0x218 \|= 0x1F` | `0x040E3208` |

`0x040E455C` disassembled in full (the `0x88 ReadFlashID` worker, called from
`0x040C48C4`; its 8 result bytes are printed as the flash ID):

```
0x040E455C  f(r0=ch, r1=ce, r2=hi16, r3=lo16, [sp+0x10]=u32 out[2])
  n  = 0x06641000 + ch*0x1000
  r5 = out
  n[0x218] |= 0x1F                       ; W1C error latch
  n[0x004] &= ~1 ; nop;nop;nop ; n[0x004] |= 1     ; channel soft reset
  while (!(n[0x21C] & 1)) ;
  rtn = (n[0x204] & 1) ? 0x17 : 0x03     ; both = NAND command 0x48
  n[0x224] = (n[0x224] & ~0xFFFF) | rtn
  n[0x22C] = r1 & 0xF
  n[0x230] = (r2 << 16) | r3             ; ReadFlashID passes r2=0, r3=8  -> 8 bytes
  if (*(u8*)0x00010AD0) { n[0x22C] |= (r1 & 0xF); r1 = 8; }
  n[0x228] = (n[0x228] & ~0xF) | r1
  n[0x220] |= 1                          ; GO
  while (!(n[0x21C] & 1)) ;
  out[0] = n[0x240] ; out[1] = n[0x244]  ; <-- 8 PIO bytes
  return n[0x218] & 0xFF
```

`0x040C48B0 mov r3,#8` is the *byte count* that lands in `+0x230`, and routine 3's
terminator is `0x52` with operand **2** (= 2 words = 8 bytes). The two agree, which is
why I read `0x52`'s operand as a **PIO word count** and `+0x230[15:0]` as a **length**.
[INFER, strong.]

### 3.1 The three address packings the firmware uses

```
A) status style      (0x040E3150)   n[0x22C] = bank & 0xF
B) lun/plane style   (0x040E4410)   n[0x22C] = (lun & 0xF) << 8
                                    n[0x234] = target << (geo[0x18]+geo[0x1B]+geo[0x19])
C) full address      (0x040E32C0)   n[0x22C] = ((lun&0xF)<<8) | ((a&0xFF)<<16) | (((a>>8)&0xFF)<<24)
                                    n[0x230] = ((a>>16)&0xFF) | (((a>>24)&0xFF)<<8) | (extra<<16)
D) row-register      (0x040CFE80)   n[0x22C] = (plane & 0xF) << 8
                                    n[0x230] = 0
                                    n[0x234] = row, pre-shifted by *(u16*)(0x9934+0x10/0x12/0x14)
```

Style **D** (`0x040CFE80`, `0x040CFF08`, `0x040CFFEC`, `0x040D00EC`, `0x040D011C`) is
the **generic "run any routine with a full row address"** family: the routine number
itself is read from RAM (`*(u16*)(0x9934 + 0/2/4/6/8/0xA/0xC/0xE)`), not from an
immediate. If you can write `0x9934`, you have a host-settable arbitrary-routine
launcher inside the firmware already. (`0x9934` is in the BSS area — `0xAA` in the
static image, so its live contents must be read at runtime.)

### 3.2 Correction to the prior register notes

* `+0x228` is a **4-bit field**, not a bitmask (`bfi rX, rCE, #0, #4` everywhere). It
  carries the CE/bank *index* 0..7. The special value **8** means "CE comes from
  `+0x22C[3:0]`" and is selected by the byte at `0x00010AD0`.
* `+0x240` is **not** "the last NAND command byte" — it is the PIO read register.
* Routine `0x21` is **not** READ ID. Its microcode issues NAND command **`0x71`**.

---

## 4. T3 — hand-rolled READ STATUS ⭐

This is `0x040E3150` transcribed literally. It is the firmware's own primitive; the
polling wrapper around it is `0x040E3250`, which accepts when
`((status | 0x10) == 0xF0) && (err == 0)` and gives up after 1000 tries with
`"read nand status timeout, ch(%d), bank(%d), err(%x), sts(%x)"` (`0x040E3494`).

**Channel 0, CE 0** — all addresses pre-computed:

```python
# ---- one-time: read the CE-routing flag the firmware consults -------------
ALT_CE = peek8(0x00010AD0)      # 0 on the normal path

def nifc_read_status(bank=0):           # bank == CE index 0..3 on this drive
    B = 0x06641000                      # ch 0.  ch N -> 0x06641000 + N*0x1000

    # 1. clear the sticky error latch                     [0x040E315C]
    write32(B+0x218, read32(B+0x218) | 0x1F)

    # 2. channel soft reset = abort anything in flight     [0x040E3168]
    write32(B+0x004, read32(B+0x004) & ~1)
    #    firmware inserts 3 NOPs here; any host round-trip is longer than that
    write32(B+0x004, read32(B+0x004) | 1)

    # 3. wait for the engine to be idle                    [0x040E318C]
    while not (read32(B+0x21C) & 1): pass

    # 4. pick the routine for the current bus mode         [0x040E3198]
    rtn = 0x32 if (read32(B+0x204) & 1) else 0x0D     # both = NAND cmd 0x38
    write32(B+0x224, (read32(B+0x224) & ~0xFFFF) | rtn)

    # 5. target                                            [0x040E31B4]
    write32(B+0x22C, bank & 0xF)
    ce_field = 8 if ALT_CE else (bank & 0xF)
    write32(B+0x228, (read32(B+0x228) & ~0xF) | ce_field)

    # 6. GO                                                [0x040E31E8]
    write32(B+0x220, read32(B+0x220) | 1)

    # 7. wait for completion                               [0x040E31F4]
    while not (read32(B+0x21C) & 1): pass

    # 8. results                                           [0x040E3200 / 0x040E3208]
    status = read32(B+0x240) & 0xFF     # <-- the die's status byte
    err    = read32(B+0x218) & 0xFF     # <-- engine error flags, 0 == clean
    return status, err

# firmware's own accept test  [0x040E3280]
ready = ((status | 0x10) == 0xF0) and (err == 0)
```

Bit meaning of `status` (standard ONFI, **confirmed** — the firmware nowhere shifts or
reorders it): `bit0 = FAIL`, `bit1 = FAILC`, `bit4 = don't care` (the firmware ORs it
in before comparing), `bit5 = ARDY`, `bit6 = RDY`, `bit7 = WP#`.
Pass condition used by the descriptor path: `(sts & 0xE1) == 0xE0` (`0x040DBD68`).

### 4.1 If you want a literal `70h` READ STATUS instead of `38h`

The stock table has one: **routine `0x30`** @ `0x06649300`
`= DLY 9 / DLY 0x30 / CMD 70h / ADR(0) / DLY 0x50 + END`.
Drive it exactly as above but with `rtn = 0x30` and `n[0x22C] = (lun & 0xF) << 8`
(that is what `0x040C7DC8` does).

⚠️ **Routine 0x30 has no PIO-read instruction** — it ends on a delay, not on the `0x52`
op, so `+0x240` is *not* refreshed by it. Both of its firmware users
(`0x040C6FC0`, `0x040C7DC8`) only look at `+0x218`. If you want `70h` **and** a byte
back, clone routine `0x30` into a free slot and append routine `0x0D`'s terminator:

```
free_slot = 0x06649000 + 0xD0*0x10        # routine 0xD0, past the end of the image
write32(free_slot + 0x00, 0x000009EB)     # DLY 9
write32(free_slot + 0x04, 0x000030EB)     # DLY 0x30
write32(free_slot + 0x08, 0x70800548)     # CMD 70h
write32(free_slot + 0x0C, 0x00000550)     # ADR / operand, count 0
# second 16-byte slot:
write32(free_slot + 0x10, 0x00003CEB)     # DLY 0x3C   (tWHR)
write32(free_slot + 0x14, 0x81000452)     # PIO-IN 1 word + END   <- copied from routine 0x0D
write32(free_slot + 0x18, 0)
write32(free_slot + 0x1C, 0)
# then run it with rtn = 0xD0 and read +0x240
```
[INFER on the `0x52`/`0xEB` operand semantics — but every word above is copied verbatim
from routines that the firmware demonstrably runs, so the risk is that the routine does
nothing, not that it does something destructive.]

**Do the cheap validation first:** read back `0x06649000..0x06649C90` with your existing
RAM-read primitive and compare against `c1.bin[0x2E836 : 0x2E836+0xC90]`. If it matches,
the microcode RAM is CPU-readable and the whole "write your own routine" plan is on solid
ground. If it reads back as garbage, the RAM is write-only and you can still write, but
you cannot verify. **This single read is the highest-value next experiment.**

---

## 5. T4 — a RESET that cannot hang, and the abort mechanism

### 5.1 Why `0x040E384C` hangs

```
040E3854  ldr r2,[r0,#0x21C] ; tst r2,#1 ; beq 0x040E3854      <-- unbounded
040E3860  n[0x224] = 2
040E3870  n[0x228] = ce
040E387C  n[0x220] |= 1
040E3888  ldr r1,[r0,#0x21C] ; tst r1,#1 ; beq 0x040E3888      <-- unbounded
```

It is the **only** launcher in the image that does not perform the
`+0x218 |= 0x1F` / `+0x004` toggle first. Every other primitive
(`0x040E3150`, `0x040E3398`, `0x040E4410`, `0x040E455C`, `0x040C6FC0`) does, which is
precisely why they survive a wedged engine and it does not.

### 5.2 The abort

**`N(ch)+0x004` bit0 is the channel FSM enable/reset.** Clearing it and setting it again
resynchronises the NIFC sequencer; the firmware always follows it with a fresh
`while (!(N[0x21C]&1))`. Applied *before* the idle wait it is an **abort**; applied after
a timeout it is a **recovery**. Evidence: `0x040E28E0`, `0x040C6FEC`, `0x040E3168`,
`0x040E33B4`, `0x040E4470`, `0x040E4578`, `0x040CFCA4`, `0x040D0068`, `0x040E28F8`.

There is a ladder of increasingly heavy resets, all read out of the image:

| level | what | code |
|---|---|---|
| 1 | one channel: `+0x218 \|= 0x1F` · `+0x004` low/3 NOP/high | inline everywhere |
| 2 | all 4 channels: same + `+0x084 \|= 2` | `0x040E28D4` |
| 3 | level 2 + `+0x210` DQS mask + `+0x204/+0x034/+0x200` mode & timing re-init | `0x040E3070` (toggle) / `0x040E305C` (legacy) — **does NOT need the microcode re-uploaded** |
| 4 | full NAND bring-up incl. both microcode uploads | `0x040E38D8` |

No "abort" bit was found in `+0x220`, `+0x200` or `+0x204`; `+0x220` bit0 is a
write-1-to-start that the hardware clears. **READ** (exhaustive scan of all writes).

### 5.3 Bounded RESET — channel 0, CE 0

```python
B = 0x06641000                     # ch 0

def nifc_abort(B):
    write32(B+0x218, read32(B+0x218) | 0x1F)      # clear error latch
    write32(B+0x004, read32(B+0x004) & ~1)        # FSM reset low
    write32(B+0x004, read32(B+0x004) | 1)         # FSM reset high

def wait_idle(B, tries=2000):
    for _ in range(tries):
        if read32(B+0x21C) & 1: return True
    return False

def nifc_reset_die(ce=0, tries=2000):
    nifc_abort(B)                                  # <-- the line 0x040E384C is missing
    if not wait_idle(B, tries):
        return "ENGINE_STUCK_BEFORE_START"

    write32(B+0x224, (read32(B+0x224) & ~0xFFFF) | 0x0002)   # routine 2 = NAND FFh
    write32(B+0x228, (read32(B+0x228) & ~0xF) | (ce & 0xF))
    write32(B+0x220, read32(B+0x220) | 1)                    # GO

    if not wait_idle(B, tries):
        nifc_abort(B)                              # recover, do not spin forever
        return "RESET_TIMEOUT"
    return read32(B+0x218) & 0xFF                  # 0 == clean
```

If `nifc_abort` + `wait_idle` still will not go idle, escalate to level 3 by hand
(all four channels):

```python
for ch in range(4):
    b = 0x06641000 + ch*0x1000
    write32(b+0x004, read32(b+0x004) & ~1)
    write32(b+0x004, read32(b+0x004) |  1)
    write32(b+0x084, read32(b+0x084) |  2)        # 0x040E2904
for ch in range(4):
    write32(0x06641000+ch*0x1000 + 0x210, 0x0F000800)          # 0x040E2F40
for ch in range(4):
    b = 0x06641000 + ch*0x1000
    v = read32(b+0x204); write32(b+0x204, (v & ~1) | 1)        # toggle mode = 1
    write32(b+0x034, read32(b+0x034) & ~0x10000)
    write32(b+0x200, 0x01010000 | (t<<8) | t)  # t = (0x1F3F + freq_MHz*284)//0x1F40
```
(`0x040E2B48` / `0x040E2BD4`. Use `write32(b+0x200, 0x02020202)` for legacy mode.)

---

## 6. T5 — a hand-rolled PAGE READ

### 6.1 Honest headline

**There is no stock routine that delivers page data into a PIO register.** The routines
that read the array (`0x52`, `0x57`, `0x5C`, `0x61`, `0x66`, `0x6C`, `0x88`, `0x90`,
`0x94`) all end with the same six-instruction burst block
`1B 09 / 8B 05 / 2B 29 / 76|7B 13 / 2B 31 / 3B 29+END`, which hands the data to the
FIFO/DMA side, not to `+0x240`. Only the short routines terminate with the `0x52` PIO
op, and the largest PIO transfer in the whole table is **2 words (8 bytes)**
(routine 3 = ReadFlashID). So:

* PIO page read requires **authoring a routine** (or repeating an 8-byte PIO read with a
  column change), OR
* driving the existing command/data-out routines and draining the data the way the
  FCQ does — which is what you are trying to bypass.

### 6.2 What the stock table gives you, bare-metal

| step | routine | microcode | notes |
|---|---|---|---|
| read-page issue, single plane | **0x41** @ `0x06649410` | `PRE 08 / DLY 0x30 / CMD 00h / ADR(3,sub15) / A0 / CMD 99h +END` | descriptor `0x82` ("pre-read") family |
| read-page issue, multi plane | **0x3F** @ `0x066493F0` | same but final `CMD 98h` | descriptor `0x7E` family |
| read-confirm / tR wait | **0x3D** @ `0x066493D0` | `PRE 08 / DLY 0x30 / CMD 30h / ADR(4,sub0D) / A0 +END` | contains the ONFI `30h` |
| data-out, ECC path | **0x61** @ `0x06649610` | `70h / 3Ch+addr / 02h+addr / 70h / burst` | = descriptor `0xB0` |
| data-out, raw path | **0x5C** @ `0x066495C0` | `3Ch+addr / 03h+addr / 70h / burst` | = descriptor `0xAE` |
| whole page read in one routine | **0x88** @ `0x06649880` | `00h+addr / 02h+addr / 70h / burst` | self-contained |
| status | **0x30** (70h) / **0x0D** (38h) | | §4 |

Register setup for any of these: use packing **D** (§3.1) —
`+0x22C = (plane&0xF)<<8`, `+0x230 = 0`, `+0x234 = row`, `+0x228 = ce`, then
`+0x224 = routine`, `+0x220 |= 1`.

### 6.3 Recommended construction — a PIO page read you author yourself

Build it from instruction words that already appear in routines the firmware runs, so
every opcode is known-good:

```python
UC   = 0x06649000                  # nifc_cmd microcode RAM
RTN  = 0xD2                        # a free slot, well past the 0xC9-slot image
A    = UC + RTN*0x10

# program: 00h + row addr + 30h  -> wait tR -> 8-byte PIO read
write32(A+0x00, 0x0000080B)        # PRE                 (from rtn 0x41)
write32(A+0x04, 0x000030EB)        # DLY 0x30
write32(A+0x08, 0x00000548)        # CMD 00h
write32(A+0x0C, 0x03001550)        # ADR, operand 3, sub 0x15   (row/col from +0x234)
write32(A+0x10, 0x058005A0)        # A0 address-phase terminator
write32(A+0x14, 0x30000548)        # CMD 30h                     (from rtn 0x3D)
write32(A+0x18, 0x000280EB)        # DLY 0x280   (tR)            (from rtn 0x88)
write32(A+0x1C, 0x82001252)        # PIO-IN 2 words + END        (from rtn 0x03)
write32(A+0x20, 0); write32(A+0x24, 0); write32(A+0x28, 0); write32(A+0x2C, 0)

def pio_page_read8(ce=0, plane=0, row=0):
    B = 0x06641000
    write32(B+0x218, read32(B+0x218) | 0x1F)
    write32(B+0x004, read32(B+0x004) & ~1)
    write32(B+0x004, read32(B+0x004) |  1)
    while not (read32(B+0x21C) & 1): pass
    write32(B+0x224, (read32(B+0x224) & ~0xFFFF) | RTN)
    write32(B+0x22C, (plane & 0xF) << 8)
    write32(B+0x230, 8)                       # length, as ReadFlashID does
    write32(B+0x234, row)                     # full row address
    write32(B+0x228, (read32(B+0x228) & ~0xF) | (ce & 0xF))
    write32(B+0x220, read32(B+0x220) | 1)
    while not (read32(B+0x21C) & 1): pass
    return read32(B+0x240), read32(B+0x244), read32(B+0x218) & 0xFF
```

Then, to walk the page, either
(a) **test whether `+0x240` is a FIFO head**: run the routine once, then read `+0x240`
repeatedly and see whether successive words appear (this costs nothing and would make a
whole page readable in one shot), or
(b) raise the `0x52` operand from 2 towards `0x7F` (`write32(A+0x1C, 0x827F1252)` —
keep `sub=0x12`, keep bit31) and see whether more than 8 bytes become available, or
(c) append a column-change step (`CMD 05h/ CMD E0h` equivalents in this table are the
`02h`/`03h` ops at `0x02800548` / `0x03000548` with `ADR 03 sub=0x15`) and re-run the
PIO read for each 8-byte chunk. 512 iterations per 4 KB. Slow, deterministic, and it
never touches the descriptor engine.

**Every one of (a)/(b)/(c) is an experiment, not a fact.** I can read the microcode but
I cannot read the NIFC's data-path datasheet out of it.

---

## 7. T6 — what `sts0` actually is

**`sts0` is not a NIFC register and not a CPU-issued NAND status read.** It is a field
of the FCQ hardware completion ring.

```
0x040DBDF4  r0 = 0x06600000
0x040DBDFC  cnt  = FCQ[0x74] & 0xFFFF        ; completions pending
0x040DBE00  head = (FCQ[0x70] >> 16) & 0xFF
0x040DBE20  r4   = 0x0400E140 + head*0x10    ; completion entry, stride 16
...
0x040DC028  add r0, r4, #4
0x040DC034  ldm r0, {r0,r1,r2}               ; r0=+4 info, r1=+8 sts0, r2=+0xC sts1
0x040DC04C  printf("[%d,%d,%d,%3X,%d,%3d]info=%x, sts0=%08x, sts1=%08x")
```

So **`sts0 = *(u32*)(0x0400E140 + head*16 + 8)`**, written by the FCQ engine, never by
firmware. (`0x040E113C` memsets the ring once; no other store touches it.)

### 7.1 The meaning of `sts0` depends on the descriptor class

| descriptor opcode | firmware's own test | meaning of `sts0` |
|---|---|---|
| `0x42` check-ready / program / erase status | `(sts0 & 0xE1) == 0xE0` → pass (`0x040DBD68`, inline copy `0x040DBA78`) | **byte 0 = raw ONFI NAND status** |
| `0xB0` / `0xAE` data-out | **`sts0 == 0x00000080` → OK**, anything else → "NG" (`0x040D3900`–`0x040D3920`; same idiom `0x040DA78C`, `0x040DCAE0`) | **the whole word is an engine completion code** |
| any | `bits[31:24]` = per-plane bitmap, masked with `(1 << geo[+9]) - 1` (`0x040DBC80`, `0x040DC810`, `0x040DCCCC`, `0x040DCE60`) | |
| any | `bits[23:8]` — **never read by a single instruction in the image** | |

### 7.2 ⚠️ `sts0 = 0x00000080` does **not** mean "die busy"

Verified at `0x040D3910`:

```
040D3900  cmp    r2, r0, lsl #20      ; r2 = 0x0B000000  -> (desc[0] & 0xFFF) == 0x0B0
040D3904  movne  r2, #0xAE00000
040D3908  cmpne  r2, r0, lsl #20      ;                  -> or == 0x0AE
040D390C  bne    ...
040D3910  ldrh   r0, [r4, #4]
040D3914  tst    r0, #4               ; status word valid
040D3918  ldrne  r0, [r4, #8]
040D391C  cmpne  r0, #0x80
040D3920  beq    OK                   ; prints " OK C:%d B:%d L:%d ..."
                                      ; else   " NG ... STS:%X"
```

For a **data-out** descriptor the firmware's own definition of success is
`sts0 == 0x80`. Reading `0x80` as "ONFI status with only WP# set, RDY=0 ⇒ die busy"
is the opposite of what the code says. **The §56 diagnosis ("RDY and ARDY zero, die
busy after read") is not supported by the firmware.**

### 7.3 So why did the read say FAIL?

`gdp_read_page` @ `0x040C4360` calls the poller with **mode 1**:

```
040C45AC  mov r1, #1                  ; mode
040C45BC  add r0, r0, #4              ; expect 4 (or 5) completions
040C45C0  bl  0x040DBDCC
040C45C4  ldrb r0,[sp,#0x10] ; cmp r0,#0 ; != 0 -> FAIL
```
and inside the poller, mode 1 flags a completion **purely on `info & 3 == 1`**:

```
040DBF1C  info = completion[+4]
040DBF20  tst  info, #4               ; status word valid, else ignore
040DBF38  cmp  r6, #1 ; beq 0x040DBFFC
040DBFFC  and  r0, info, #3
040DC000  cmp  r0, #1                 ; class 1 -> mark result buffer
```

Your failing line is `info=5` → `info & 4 = 4` (valid) and `info & 3 = 1` → flagged →
`gdp_read_page` prints FAIL. The passing write line was `info=0x86` → `info & 3 = 2`.

**Therefore: the read failure is an `info[1:0]` completion-class condition, not a NAND
status condition.** The `sts0=0x80` printed alongside it is, by the firmware's own
data-out test, a *good* value.

`FAIL[ 0]` is **not** a status: format `"[%s] %d %d %d %d FAIL[%2x]\r"` @ `0x040C4640`,
and the `%2x` argument is `r6` computed at `0x040C442C` as
`r6 = (bankplane >> 4) & ((1 << c0[0x9244]) - 1)` = the **plane index**.
(There is a firmware bug here: the real result byte is pushed at `0x040C45E4` as a 7th
vararg but the format has only 6 conversions, so it is never printed.)

### 7.4 `0x50`

There is **no comparison against `0x50` anywhere in the status path** in `c1.bin`; every
`cmp rX,#0x50` (`0x040E642C`, `0x040E6468`, `0x040E6508`) is a PLL frequency check.
**[UNKNOWN]** — it cannot be decoded from this image. Given `0x80` is the data-out OK
code in the same field, `0x50` is most plausibly another engine completion/abort code
rather than a NAND status byte, but that is a guess and I am flagging it as one.

### 7.5 `0x0101e1e1` — the byte-per-bank reading is **refuted**

`0x0101E1E1` as a little-endian u32: byte0 = `0xE1`, byte1 = `0xE1`, byte2 = `0x01`,
byte3 = `0x01`.

* **byte 0 = `0xE1`** — this is the real ONFI status the evaluator sees
  (`0x040DC014: ldr r0,[r4,#8] ; and r0,r0,#0xff ; bl 0x040DBD68`).
  `0xE1 & 0xE1 = 0xE1 ≠ 0xE0` → FAIL. RDY+ARDY+WP# set **and bit0 FAIL set** =
  a genuine erase failure. ✔
* **byte 3 = `0x01`** — a **per-plane bitmap**, masked by `(1 << geo[+9]) - 1`
  (`0x040DBC80: and r6, r6, r7, lsr #24`). `0x01` = plane 0. It is *not* a status byte:
  `0x01` alone would mean FAIL set with RDY clear, which is not a legal ONFI state.
* **bytes 1 and 2 are never read by any instruction.** Their values cannot be
  interpreted from the firmware.

So the correct model is **one status byte + one plane bitmap**, not four bank bytes.
By the same token `0x0101E0FF` has byte0 = `0xFF`, and `0xFF & 0xE1 = 0xE1 ≠ 0xE0`, so
`0x040DBD68` would call that a **failure** as well — `0xFF` is a floating/absent-die
bus, not "success". The §51.3 table in `RAPOR.md` needs correcting on both points.

One more thing worth knowing: `0x040DBD68` reads a NAND-class byte from
`*(*(u32*)0x00000DCC)` and, for class 2 or 5, switches the mask to **`0xE4`** (fail bit
becomes **bit 2**, not bit 0) depending on `*(u8*)0x00000E6E`; if that byte is neither 0
nor 1 it prints `"polling status fail for KIOXIA"` and **hangs in a `b .` at
`0x040DBDB8`**. The static value of `0x0DCC`'s target byte is `0x02` and `0x0E6E` is
`0xFF` in the image — i.e. if `0x0E6E` is not initialised at runtime, the status
evaluator dead-loops. Worth checking live.

---

## 8. T7 — timeouts

### 8.1 The NIFC per-channel candidates

| register | verdict |
|---|---|
| `+0x208` | **never accessed** by c0/c1. [UNKNOWN] |
| `+0x20C` | **not a timeout** — `[7:0]` per-channel CE presence mask (`0x040C3468`, `0x040C358C`, `0x040C8E58`) |
| `+0x210` | **not a timeout** — DQS mask, string `"DQS MASK [%X]"` @ `0x040C8B58` |
| `+0x214` | **never accessed.** Your live `0x1f001f00` is a reset default. [UNKNOWN] |
| `+0x234` | **not a timeout** — the row-address register |
| `+0x238` | `[7:0]` = a count written as `r2 + 0xF1`; only one site (`0x040CFCEC`). Not the R/B wait. |
| `+0x24C`, `+0x250` | **never accessed.** [UNKNOWN] |

**None of the per-channel registers you listed bounds the R/B# wait.** The per-step
waits inside a routine are the `0xEB` DELAY instructions *in the microcode itself*
(`0x000280EB` = 0x280 ticks is the post-read wait used by every data-out routine), and
those are fixed-length delays, not R/B#-polled timeouts.

### 8.2 Where the real timeout lives ⭐

The NOPS scheduler owns it, and its registers are in the **global** NIFC block. Both
groups are loaded from the TMC parameter block at RAM `0x200`:

```
0x040E2C40 (G = 0x06640000, T = 0x200) :
  G[0x70][15:0]  = *(u16*)(T+0xB4)      nops_tmr_un0
  G[0x70][31:16] = *(u16*)(T+0xB6)      nops_tmr_un1
  G[0x74][15:0]  = *(u16*)(T+0xB8)      nops_tmr_un2
  G[0x74][31:16] = *(u16*)(T+0xBA)      nops_tmr_un3

0x040E264C :
  G[0x7C][15:0]  = *(u16*)(T+0xC0)      nops_rty_wrn_th0
  G[0x7C][31:16] = *(u16*)(T+0xC2)      nops_rty_wrn_th1
  G[0x80][15:0]  = *(u16*)(T+0xC4)      nops_rty_wrn_th2
  G[0x80][31:16] = *(u16*)(T+0xC6)      nops_rty_wrn_th3
  G[0x84][15:0]  = *(u16*)(T+0xC8)      nops_rty_tmo_th0
  G[0x84][31:16] = *(u16*)(T+0xCA)      nops_rty_tmo_th1
  G[0x88][15:0]  = *(u16*)(T+0xCC)      nops_rty_tmo_th2
  G[0x88][31:16] = *(u16*)(T+0xCE)      nops_rty_tmo_th3
```

The names come from the GDP's own settings printer at `0x040C13D8`…`0x040C142C`
(`"nops_rty_wrn_th0 = 0x%08X"` … `"nops_rty_tmo_th3 = 0x%08X"`, reading the same
TMC struct offsets `+0xC0`…`+0xCE` off the stack copy), and `nops_tmr_un0..un3` is a
vendor symbol from the SORT firmware's register dump. **[READ for the register↔TMC
mapping; INFER, strong, for `G+0x70/0x74 == nops_tmr_un0..3` — they are the only other
four TMC-driven u16s in the NIFC global block and there are exactly four `nops_tmr_un*`
names.]**

**Field layout.** Each NOPS step selects one of the four timer units and a count:

```
nops_op entry +4 (u16):  bits[13:0] = count       max 16383
                         bits[15:14] = timer unit 0..3
nops_tmr_unN (u16):      the tick period for unit N,  max 65535
```

So the wait a NAND operation gets is `count × unit`, and **the thing that bounds the
wait for R/B# after a read command is `nops_tmr_unN` together with the step's count**
— configured from `TMC[0xB4..0xBB]`, not from any per-channel register.

### 8.3 ⚠️ This is a live lead on the §56 regression

**Two different functions write these four registers, and they disagree:**

* `0x040E2B48` writes **hardcoded** values (`0x040E2B58 movw r7,#0x1388`,
  `0x040E2BA0 add r1,r1,#0x1F40000`, `0x040E2B60 mov ip,#0x32`). Reached from
  `0x040E3070`/`0x040E305C` (the channel re-init) and from `0x040E38F0` (the NAND
  bring-up).
* `0x040E2BD4` writes the **TMC** values (`0x040E2C40` onwards). Reached from
  `0x040C8148`, `0x040C8730`, `0x040C9AD8`, `0x040E37AC`.
* `0x040E236C` (the TMC-apply function) writes both groups from TMC and runs during
  `InitGDP` at `0x040C8EA4`, i.e. **before** `0x040C8EB0 → 0x040C7D74 → 0x040E3070 →
  0x040E2B48`, which then overwrites `G+0x70/0x74` with the hardcoded numbers again.

So **which values are live at the end of your recipe cannot be settled statically** —
it depends on which of the two ran last. That is exactly why experiment 1 below (read
the registers back) matters more than any argument from the code.

Hardcoded defaults (`0x040E2B48`):

```
nops_tmr_un0 = 0x1388 = 5000
nops_tmr_un1 = 0x1F40 = 8000
nops_tmr_un2 = 0x0032 = 50
nops_tmr_un3 = 0
```

The recipe in `RAPOR.md` §54.1 writes the TMC block as
`[0xB4]=40  [0xB6]=100  [0xB8]=1  [0xBA]=1`. If the mapping above is right *and* a
TMC-applying path (`0x040E2BD4` / `0x040E236C`) ran last, the live values are
`40 / 100 / 1 / 1` — **~125× shorter** on unit 0 and 80× on unit 1. A page read needs the full `tR`; an erase needs milliseconds. A timeout that is
two orders of magnitude tighter than the vendor default is exactly the kind of thing
that passes on a cold, fast die in the morning and fails after hours of self-heating —
which is the §56.4 "temperature" hypothesis with an actual mechanism behind it.

Two cheap, non-destructive experiments:

1. **Read back** `0x06640070`, `0x06640074`, `0x0664007C`, `0x06640080`, `0x06640084`,
   `0x06640088` after `0x49 gdp_nand_init` and see what is actually in them.
2. **Restore the vendor defaults** before init by setting `TMC[0xB4]=0x1388`,
   `[0xB6]=0x1F40`, `[0xB8]=0x32`, `[0xBA]=0`, or simply poke the registers directly
   after init:
   ```
   write32(0x06640070, 0x1F401388)
   write32(0x06640074, 0x00000032)
   ```
   and re-run the read that currently fails. If the failure is a NOPS timeout, this
   flips it.

The other three TMC values in that recipe are now identified too, which is a useful
cross-check that the struct offsets are right: `TMC[0x00] = bIf_Power_On`,
`TMC[0x05] = bHigh_Speed_Set` (= `0x17`), `TMC[0x06] = bOutput_Drive_Strength` (= `0x02`)
— printed at `0x040C1390`, `0x040C13BC`, `0x040C13CC`.

---

## 9. What I could not answer

* `N+0x208`, `N+0x214`, `N+0x24C`, `N+0x250`: never touched by this firmware. `+0x214`'s
  `0x1f001f00` is a power-on default or a `LDBK CONFIG` boot write; the GDP does not run
  the `LDBK CONFIG` register list.
* `N+0x010..0x02C` (`aaaaaaaa` / `00555555` / `00aaaaaa`): same — never accessed. The
  delay lines the GDP *does* drive are `+0x074`/`+0x078`/`+0x07C` (index + 9-bit value)
  and `+0x044`.
* The datasheet meaning of most NAND command bytes in the table (`0x48`, `0x3C`, `0x38`,
  `0x77`, `0x6A`, `0x71`, `0x02`, `0x03`, `0x98`, `0x99`, `0x42`, `0x40`). `0xFF`, `0x70`,
  `0x30`, `0x00` are unambiguous; the rest are SK hynix vendor commands and this image
  contains no name for them.
* The exact bit semantics of microcode opcodes `0xA0`, `0x0B`, `0x1B`, `0x2B`, `0x3B`,
  `0x76`, `0x7B`, `0x65`, `0x98`, `0xC1`, `0xD2`, `0xFB`. The `0x48`/`0xEB`/`0x50`/`0x52`
  ones are pinned by cross-checks; these are not.
* Whether the microcode RAM at `0x06649000` is **readable** (the firmware only ever
  writes it). Test this first.
* The value of `sts0` byte 1 and byte 2 — no instruction in the image reads them.
* `0x50` as a `sts0` value — no decode site exists.

---

## 10. Artifacts

| file | content |
|---|---|
| `.../scratchpad/nifc/ucode_06649000.bin` | the A table as uploaded (0xC90 B), = `c1.bin[0x2E836:0x2F4C6]` |
| `.../scratchpad/nifc/ucode_06650000.bin` | the B table as uploaded (0x408 B), = `c1.bin[0x2F4C6:0x2F8CE]` |
| `.../scratchpad/nifc/parse.py` | the microcode disassembler used above |
| `.../scratchpad/nifc/A.txt` | every routine, fully decoded, instruction by instruction |
| `.../scratchpad/nifc/map2.txt` | the exhaustive NIFC/FCQ/LDPC register access map |
| `.../scratchpad/nifc/c1.asm` | full linear ARM disassembly of `c1.bin` with literals resolved |

(`.../scratchpad` = `/tmp/claude-1000/-home-schrodinger/b1ff2e18-627f-48b1-9fbf-4f33803bfa07/scratchpad`)
