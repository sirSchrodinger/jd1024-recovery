# MAP1202 GDP firmware — NVMe layer: static RE and "own firmware" feasibility

Scope: pure static RE of `c1.bin` (@`0x040C0000`, 192 KB) + `c0.bin` (@`0x00000000`, 48 KB)
with `d.py` / `fn.py` plus two new helpers written for this pass
(`br.py` = ARM/Thumb B/BL/BLX xref, `xr2.py` = literal/ADR xref, `lit.py` = literal-slot xref;
they live in the scratchpad, not in the repo).

**No hardware was touched for this analysis.** Everything below is read out of the two
images. Where I *infer* rather than read it is marked `[INFER]`. Where I could not
determine something it says so.

Companion document: `ANALIZ_DESC.md` (FCQ/NIFC/descriptor side).
State of the NAND side: `RAPOR.md` §51–§55.

---

## 0. Executive answer

**GDP is not "an NVMe-ish diagnostic shim". It is a complete NVMe 1.3 controller
personality with a dead I/O path.**

It already implements, in firmware, with addresses given below:

| NVMe admin opcode | implemented | handler |
|---|---|---|
| 0x00 Delete I/O SQ | yes | `0x040DFBD4` |
| 0x01 Create I/O SQ | **yes, fully** | `0x040DFA60` |
| 0x02 Get Log Page | yes | `0x040DF154` |
| 0x04 Delete I/O CQ | yes | `0x040DFD08` |
| 0x05 Create I/O CQ | **yes, fully** | `0x040DF96C` |
| 0x06 Identify | yes (CNS 0 and 1 only) | `0x040DF60C` |
| 0x08 Abort | yes | `0x040DFE74` |
| 0x09 Set Features | yes (FID 1..0x0B) | `0x040DF7BC` |
| 0x0A Get Features | yes | `0x040DF668` |
| 0x0C Async Event Request | yes | `0x040DF134` |
| 0x10 Firmware Commit | yes | inline @`0x040CA80C` |
| 0x11 Firmware Image Download | yes | inline @`0x040CA7D0` |
| 0xC1 / 0xC2 vendor | yes | `0x040E0974(0)` / `0x040E0974(1)` |

and the whole I/O queue path *exists and runs* — it fetches I/O commands, prints
`iop:%x`, and completes them. The firmware-FIFO I/O dispatcher answers
**"Invalid Command Opcode" to everything except Flush (0x00) and Dataset
Management (0x09)**:

```
040CA834  <-- NVMe I/O command dispatcher (firmware FIFO path)
040CA86C  cmp      r4, #0            ; r4 = NVMe opcode
040CA874  cmpne    r4, #9
040CA87C  moveq    r0, #0            ; opcode 0 (Flush) or 9 (DSM)  -> status 0
040CA880  movne    r0, #1            ; everything else              -> status 1 = Invalid Opcode
040CA898  bl       #0x40cd4ec        ; post completion
```

**But that is only half the story, and probably not the important half.** There is a
**second, hardware-assisted I/O path** (§T2b) in which the SQM classifies NVMe
Read/Write commands away from the firmware FIFO into dedicated hardware
WDMA/RDMA command queues; the hardware does the PRP fetch and the host DMA itself
and hands the firmware a 44-byte descriptor carrying {function, SQID, CID, SLBA,
NLB, data-buffer id}. GDP **already drains all four of those queues in its main
loop** (`0x040C127C`–`0x040C1288`) and **already implements Write as a 250 KB SRAM
RAM-disk at `0x04081800`**. That RAM-disk region — `0x04081800`…`0x040C0000` — is
exactly `0x3E800` bytes, which is the magic constant the namespace-size arithmetic
uses. GDP's "namespace" *is* that RAM disk.

Verdict: writing our own Read/Write into GDP is **feasible and small** — on the order
of **200–400 ARM instructions** total, with **two to six 32-bit word hooks**. It is
far less work than it sounds because the SQ fetch, PRP fetch, host DMA, CQ post,
MSI-X, CC.EN/shutdown and queue creation are all **hardware blocks plus
already-written firmware** that we simply call or replace in place.

**What must be resolved before writing a line of code** (one read-only experiment,
§B): does an NVMe Read on an I/O queue land in the firmware FIFO (`0x040CA834`,
"iop:02" on the console) or in the hardware RDMA queue (`0x040CC300`)? The answer
selects patch variant A or B in §T4.3.

---

## T1 — Where GDP's NVMe layer is

### T1.1 The command context (read, fully decoded)

Hardware delivers each NVMe command into SRAM as a **0x44-byte record**
(`memset(ctx,0,0x44)` at `0x040CAF30/0x040CAF4C/0x040CAF58`):

| ctx offset | field | evidence |
|---|---|---|
| `+0x00` u32 | HW header: `[31:24]` **opcode**, `[20:16]` **SQID**, `[13:10]` **PCIe function id** | `0x040CA6A8 lsr r3,r2,#24`; `ubfx …,#0x10,#5`; `ubfx …,#0xa,#4` |
| `+0x04` u16 | command flags (PSDT/FUSE) `[INFER]` | never read |
| `+0x06` u16 | **CID** | `ldrh r2,[ip,#6]` → passed to completion |
| `+0x08` u32 | **NSID** (CDW1) | `and r6,r0,#0xff` in Identify-NS |
| `+0x0C..0x1B` | CDW2..CDW5 (metadata ptr etc.) | copied wholesale by vendor path |
| `+0x1C` u64 | **PRP1** (CDW6/7) | `ldrd r2,r3,[r0,#0x1c]` |
| `+0x24` u64 | **PRP2** (CDW8/9) | `ldrd r2,r3,[fp,#0x24]` @`0x040E04FA` |
| `+0x2C` u32 | **CDW10** | Identify CNS, Get-Log LID, CreateCQ QID/QSIZE |
| `+0x30` u32 | **CDW11** | CreateCQ PC/IEN + IV, SetFeat value |
| `+0x34` u32 | CDW12 | |
| `+0x38` u32 | CDW13 | |
| `+0x3C` u32 | **CDW14** | vendor magic `0x00AE34FF` / `0x00BD34FF` |
| `+0x40` u32 | **CDW15** | vendor length in LBAs |

Three contexts, one per command class:

| class | context | dispatcher | task-node `fn` slot |
|---|---|---|---|
| 0 = **admin** | `0x0000C9A8` | `0x040CA67C` | `0x000093F0` |
| 1 = **I/O** | `0x0000CA0C` | `0x040CA834` | `0x00009404` |
| 2 = "fio" (3rd queue class, purpose not determined) | `0x0000CA50` | `0x040CA8A4` | `0x00009418` |

### T1.2 The single admin dispatcher, keyed on the NVMe opcode byte

**Yes — there is exactly one.** `0x040CA67C`:

```
040CA6A0  ldr      r2, [ip]           ; ip = 0x0000C9A8
040CA6A8  lsr      r3, r2, #0x18      ; r3 = NVMe admin opcode
...
040CA710  addlo    pc, pc, r3, lsl #2 ; jump table for opcodes 0..8, base 0x040CA718
040CA748  cmp      r3, #0xa   / 0xc / 0x10 / 0x11 / 0xc1 / 0xc2
040CA778  str      r4, [sp]           ; default: status 1 = Invalid Command Opcode
```

Jump-table (base `0x040CA718`, one word per opcode):

| opcode | lands at | handler |
|---|---|---|
| 0x00 Delete I/O SQ | `0x040CA7A8` | `bl 0x040DFBD4` |
| 0x01 Create I/O SQ | `0x040CA7A0` | `bl 0x040DFA60` |
| 0x02 Get Log Page | `0x040CA7C8` | `bl 0x040DF154` |
| 0x03 | `0x040CA778` | invalid |
| 0x04 Delete I/O CQ | `0x040CA7B0` | `bl 0x040DFD08` |
| 0x05 Create I/O CQ | `0x040CA798` | `bl 0x040DF96C` |
| 0x06 Identify | `0x040CA780` | `bl 0x040DF60C` |
| 0x07 | `0x040CA778` | invalid |
| 0x08 Abort | `0x040CA7B8` | `bl 0x040DFE74` |
| 0x09 Set Features | `0x040CA790` | `bl 0x040DF7BC` |
| 0x0A Get Features | `0x040CA788` | `bl 0x040DF668` |
| 0x0C Async Event Req | `0x040CA7C0` | `bl 0x040DF134` |
| 0x10 Firmware Commit | `0x040CA80C` | inline; `CDW10&7 > 1` → status `0x106` |
| 0x11 FW Image Download | `0x040CA7D0` | inline; writes ctx+0x30/0x3C/0x40, `blx 0x040E03BE` |
| **0xC1** | `0x040CA800` | `mov r0,#0 ; blx 0x040E0974` |
| **0xC2** | `0x040CA804` | `mov r0,#1 ; blx 0x040E0974` |

Before the switch there is an **Abort match** preamble (`0x040CA690`–`0x040CA6F8`):
the pending-abort record at `0x0000C9F6` is compared against the incoming
(SQID, CID); on a match the command is completed immediately with status **7**
(Command Abort Requested).

### T1.3 The vendor path (0xC1 / 0xC2)

`0x040E0974` (**Thumb**) is the vendor entry. Reading it:

* `ctx+0x3C` (CDW14) is the mode magic: `0x00AE34FF` = enable vendor mode,
  `0x00BD34FF` = disable. State byte at `0x0000CA98`, current-command byte at
  `0x00000EDC`, per-command record at `0x0000EAB0`.
* otherwise `CDW14 & 0x00FFFFFF` must equal `0x00123400 | current_cmd`.
* `ctx+0x40` (CDW15) = transfer length **in LBAs of HW namespace slot 7**
  (`0x040CC73C(0)` → `nsid-1 = -1` → slot 7 → 512 B today), i.e. bytes = `CDW15 << 9`.
* r0 = 0 (opcode 0xC1) → host→controller; r0 = 1 (0xC2) → controller→host.
* `0x040E0448` pre-fetches the vendor payload / PRP list into `0x0000CA98+0x18`.
* `0x040E04A8(dir, sram_buf)` is the **generic PRP walker** (see T4.4).
* Dispatch of the GDP sub-command byte then uses the 36-entry table at
  `0x040ED2F4` already documented in `RAPOR.md`; I re-dumped it and it matches
  exactly (cmd `0x89`→`0x040C4360`, `0x8A`→`0x040C3DB4`, `0x8B`→`0x040C3C90`,
  `0x88`→`0x040C488C`, `0x49`→`0x040C31A8`, `0x02`→`0x040C3AE8`, …).

### T1.4 Completion posting — one function

```
040CD4EC  nvme_post_completion(r0=func, r1=sqid, r2=cid, r3=cqe_dw0, [sp+0x10]=status15)
          CQM base 0x06738000
          +0x6C [2:1]   = func
          +0x6C [18:3]  = sqid
          +0x70 [15:0]  = cid
          +0x70 [30:16] = status (15 bits)
          +0x74         = CQE DW0 (result)
          +0x6C |= 1    = "post it"
040CD53C  returns 1 when (CQM+0x6C & 1) == 0, i.e. the poster is free
```

The 15-bit status maps onto CQE DW3[31:17]: `[7:0]=SC`, `[10:8]=SCT`,
`[12:11]=CRD`, `[13]=M`, **`[14]=DNR (0x4000)`**.

> ⚠ **Finding:** GDP **never sets DNR** on any error completion. Every error it
> returns has DNR = 0. This matters for Linux (see T4.2).

Observed status constants: `1` generic Invalid Opcode, `2` Invalid Field,
`6` Internal Error, `7` Command Abort Requested, `0xB` Invalid Namespace/Format,
`0x100` Completion Queue Invalid, `0x101` Invalid Queue Identifier,
`0x102` Invalid Queue Size, `0x106` Invalid Firmware Slot,
`0x108` Invalid Interrupt Vector, `0x109` Invalid Log Page, `0x114` Overlapping Range.
So SCT/SC are packed as `(SCT<<8)|SC` — confirms the mapping above.

### T1.5 How a command actually arrives (hardware does almost everything)

```
040CC8EC  nvme_fetch_command()
          r0 = [0x06700100] bits[11:6]        ; dword count to drain
          loop: [0x0000C9A8 + 4*i] = [0x0670010C]   ; drain the command FIFO
040CC83C  class_has_command(n): [0x06700108] & (0x40000 admin / 0x80000 io / 0x20000 fio)
040CC884  select_class(n)     : [0x06700108][2:1] = 2/4/0, then |= 1
040CC8D4  fetch_done()        : ([0x06700108] & 1) == 0
040DEF6C  set_pending(class, v) : byte at 0x0000B9A0 + class
040DEF94  get_pending(class)
```

Round-robin arbiter over the three classes: `0x040CA594` … `0x040CA670`.

### T1.6 Scheduler

Three task nodes registered at boot (`0x040CBAC4`), each `{fn, arg, prev, next}`,
linked into the list head at `0x000098BC` by `0x040CF8C8`:

```
0x000093F0 -> fn = 0x040CA67C   (admin dispatch)
0x00009404 -> fn = 0x040CA834   (I/O dispatch)
0x00009418 -> fn = 0x040CA8A4   (fio dispatch)
```

Each handler **rewrites its own node's `fn`** to the next state before returning.
The two states per class are:

```
040DEFC0  admin fetch state  -> installs 0x040CA67C into 0x000093F0
040DEFEC  I/O   fetch state  -> installs 0x040CA834 into 0x00009404
040DF018  fio   fetch state  -> installs 0x040CA8A4 into 0x00009418
```

**Critically, those three addresses are plain literal-pool words:**

| literal slot | current value |
|---|---|
| `0x040DF544` | `0x040CA67C`  (admin dispatcher) |
| `0x040DF548` | `0x000093F0` |
| **`0x040DF54C`** | **`0x040CA834`  (I/O dispatcher)** |
| `0x040DF550` | `0x00009404` |
| `0x040DF554` | `0x040CA8A4` |

Overwriting `0x040DF54C` with the address of our own function **replaces the whole
NVMe I/O command handler with zero instruction patching** — it is a data word, so
there is no I-cache coherency problem at all.

### T1.7 MMIO map (read out of the register-dump routine at `0x040CE9BA`)

| base | label in firmware | notes |
|---|---|---|
| `0x06700000` | `=======NVME TOP` (0x54 regs) | controller/function/namespace cfg + command FIFO (`+0x100`,`+0x108`,`+0x10C`) |
| `0x06710000` | `=======CTRL CFG` (3) | |
| `0x06711000 + f*0x100` | `FUNC:%#x INFO CFG` (4 regs × 4 functions) | |
| `0x06713000 + q*0x100` | `QUEUE:%#x INFO CFG` (4 regs × **0x14 = 20 queues**) | |
| `0x06720000 + f*0x100` | `FUNC:%#x STATUS CFG` | |
| `0x06722000 + q*0x100` | `QUEUE:%#x STATUS CFG` (20) | |
| `0x06730000` | `=======SQM CFG` (6) | submission-queue manager; `+0x48` = queue alloc/free, `+0x1C/0x20/0x24/0x28` per-function queue limits |
| `0x06738000` | `=======CQM CFG` (8) | completion poster (`+0x6C/+0x70/+0x74`), shutdown ack `+0x5C` |
| `0x06740000` | `=======FWDMA CFG` | firmware↔host DMA engine |
| `0x06742000 / 0x06744000 / 0x06746000` | FWDMA completion / aux | |
| `0x06748000` | `=======PWPC CFG` | |
| `0x0674C000` | `=======PRPC CFG` | **PRP fetch/cache engine** |
| `0x06750000 / 0x06758000` | HW WDMA / HW RDMA CTRL (SCLK) | the *hardware* data path a product FW would use |
| `0x06760100 / 0x06768100` | HW WDMA / RDMA CTRL (CCLK) | |
| `0x06770000` | `=======HC CLK RST CFG` | |
| `0x067C0000` | `=======PCIE CORE CFG` | |
| `0x067E0000` | `=======PCIE APB CFG` | interrupt status `+0x138/+0x140` |

(For contrast, the NAND side from `ANALIZ_DESC.md`: `0x06600000` FCQ,
`0x06610000/0x06620000` LDPC enc/dec, `0x0664x000` NIFC.)

BAR0 itself is not firmware-visible; the firmware sees the **decoded** view above.
CC.EN / CC.SHN / NSSR are handled at `0x040CB670`–`0x040CB760`
(strings `CCEN=0` `0x040CB7D0`, `CCEN=1` `0x040CB7E0`, `SHNE` `0x040CB7C4`,
`NSSRE` `0x040CB7D8`) — a real reset/enable state machine, which is why the drive
survives `nvme reset` today.

---

## T2 — Are I/O queues supported?  **Yes, fully implemented, not stubbed.**

### Create I/O CQ — `0x040DF96C`

```
qid    = CDW10[7:0]          (ctx+0x2C)
qsize  = CDW10[31:16]        (ctx+0x2E)
pc/ien = CDW11[15:0]         (ctx+0x30)
iv     = CDW11[31:16]        (ctx+0x32)
prp1   = ctx+0x1C (64-bit)

if qid == 0                        -> status 0x101 Invalid Queue Identifier
if qid > tbl[func].max_cq + 1      -> status 0x101
if iv  > tbl[func].max_iv          -> status 0x108 Invalid Interrupt Vector
if qsize > (u16)tbl[func].mqes     -> status 0x102 Invalid Queue Size
hwq = 0x040CCF60(func, qid)        -> allocate HW queue slot (0xFF = none)
if 0x040E0124() != 0               -> status 0x100 Completion Queue Invalid
0x040E0178(hwq, prp1_lo, prp1_hi, iv, qsize, pc_ien)   <- program the CQ into HW
status 0
```

### Create I/O SQ — `0x040DFA60`

```
qid   = CDW10[7:0]; qsize = CDW10[31:16]; cqid = CDW11[7:0] (ctx+0x32); pc = CDW11[15:0]
validates qid vs tbl[func].max_sq, cqid != 0, cqid vs tbl[func].max_cq,
qsize vs mqes, then
  0x040CCF60(func, cqid) ; 0x040E0124()     <- the CQ must already exist
  0x040CCF60(func, qid)  ; 0x040E0150()
  0x040E0200(hwq, prp1_lo, prp1_hi, cqid, qsize)        <- program the SQ into HW
status 0
```

Delete SQ `0x040DFBD4`, Delete CQ `0x040DFD08` likewise exist.

### Per-function queue-limit table — `0x000094E0`, stride **0x38**

Initialised by `0x040CAF14` (runs at boot **and on every CC.EN 0→1**, see `0x040CB74C`):

| offset | field | init value |
|---|---|---|
| `+0x00` u16 | max CQ id (NCQR, 0-based) | **3** |
| `+0x02` u16 | max SQ id (NSQR, 0-based) | **3** |
| `+0x04` u32 | Arbitration feature | 0 |
| `+0x08` u8 | Power Mgmt | 0 |
| `+0x09` u8 | Volatile Write Cache | 0 |
| `+0x0A` u16 | Error Recovery | 0 |
| `+0x0C` u32 | Temperature Threshold | 0 |
| `+0x10` u32 | max interrupt vector | **4** |
| `+0x14` u16 | Interrupt Coalescing | 0 |
| `+0x16` u16 | Async Event Config | 0 |
| `+0x18` u8 | Write Atomicity | 0 |
| `+0x24` u32 | MQES used for validation | **0xFFFF** |

`Set Features / FID 7 (Number of Queues)` at `0x040DF840` clamps both requested
counts to **7** and writes them into `+0x00/+0x02`, returning
`DW0 = NSQR | (NCQR<<16)`. So Linux asking for N queues gets **min(N, 8)**.
`Get Features / FID 7` at `0x040DF6E0` returns the same value (`ror #16`).

Hardware supports **20 queue contexts** (`0x06713000 + q*0x100`, loop bound `0x14`
at `0x040CBBC4` / `0x040CBC04`).

### Per-queue doorbells

Not touched by firmware at all — the SQ tail / CQ head doorbells are consumed
directly by the SQM/CQM hardware, which then pushes decoded commands into the
firmware FIFO at `0x0670010C`. That is why there is no doorbell code beyond the
admin queue: **there is none for the admin queue either.**

**Conclusion T2: I/O queues are real. Linux can create them today.** The only
thing missing is the media handler for opcodes 0x01/0x02 once commands arrive.

---

## T2b — The hardware-assisted Read/Write path (the important discovery)

`0x040C0DA8` is GDP's `main()`. Its steady-state loop is:

```
040C1270  bl 0x040CB15C     ; PCIe / link event processing
040C1274  bl 0x040CB43C
040C1278  bl 0x040CA540     ; NVMe command-class arbiter -> firmware FIFO path
040C127C  bl 0x040CBD5C     ; <-- HW WRITE command queue 0   ("w0lba")
040C1280  bl 0x040CC018     ; <-- HW WRITE command queue 1   ("w1lba")
040C1284  bl 0x040CC300     ; <-- HW READ  command queue 0   ("r0lba"/"r0buf")
040C1288  bl 0x040CC424     ; <-- HW READ  command queue 1   ("r1lba"/"r1buf")
040C12B8  4x: walk task list at 0x000098BC, call node->fn if node->arg != 0
040C12E4  b  0x040C104C     ; loop
```

(The same four calls appear in the bounded "extern flow" drain loop at
`0x040C11D4`, which prints `ftl process tim_out` after 0x10000 spins.)

### The hardware command-queue API

| function | register | meaning |
|---|---|---|
| `0x040CD898` | `[0x06760100] & 1` | HW **write** q0 has a command |
| `0x040CD8AC` | `[0x06760104] & 1` | HW **write** q1 has a command |
| `0x040CD8C0` | `[0x06768100] & 1` | HW **read** q0 has a command |
| `0x040CD8D4` | `[0x06768104] & 1` | HW **read** q1 has a command |
| `0x040CD938 / 954 / 970 / 98C` | same regs `>>16` | descriptor **index** (0xFFFF = none) |
| `0x040CD8E8 / 8FC / 910 / 924` | same regs `\|= 1` | pop / acknowledge |
| `0x040CD9A8(idx, flag)` | `[0x06758000+0x60]` `[31:16]=idx`, `[3]=flag`, clears 1/2/4/0x10 | hand a **read** descriptor back to the RDMA engine so it DMAs to the host |
| `0x040CDA78 / 0x040CDA90` | `[0x06758000+0x60] & 1` / `[+0x80] & 1` | RDMA submit slot free? |
| `0x040CCD9C(x)` | `[0x06700188]` `[23:16]=x`, `\|=1` | release a command tag |
| `0x040E7624(pool)` | `[0x06500070]` | allocate a data buffer id (returns `>>16`) |
| `0x040E75EC(id, pool)` | `[0x06500074/0x80]` | free a data buffer id |

`0x06760000` = HW WDMA CTRL (CCLK), `0x06768000` = HW RDMA CTRL (CCLK),
`0x06750000`/`0x06758000` = the same engines' SCLK halves,
`0x06500000` = the data-buffer manager. All named by the register-dump routine.

### The I/O command descriptor — `0x04000000 + idx * 0x2C`

Same 44-byte pool that the NAND driver's handle allocator uses
(`ANALIZ_DESC.md` T5: `handle = 0x04000000 + index*0x2C`) — it is a **unified
request object** shared by the host side and the media side.

| off | field | evidence |
|---|---|---|
| `+0x08` | flags: `0x20000` skip, `0x100000`/`0x200000` abort interlock, `0x400000`, `0x80000` | `0x040CBE98`, `0x040CBF50` |
| `+0x0C` `[1:0]` | PCIe function | `and r6,r0,#3` |
| `+0x10` `[15:0]` | **data buffer id / tag**; bit15 selects buffer pool | `0x040CBD B8`, `0x040CC414` |
| `+0x14` `[15:0]` | **CID**; `[31:16]` **SQID** | `0x040CBDD4` |
| `+0x18` | **SLBA** | `0x040CBDA0` |
| `+0x1C` `[15:8]` | **NLB / block count**; `[23:16]` tag to release via `0x040CCD9C` | `0x040CBDA8`, `0x040CBE40` |
| `+0x20` `[7:0]` | **NSID** | `0x040CBDC8` |

### What GDP currently does with them

**Write (`0x040CBD5C`, q0 — `0x040CC018` is the q1 twin):**

```
lbasize = 0x040CC73C(nsid)                 ; 0 -> print "w0lba", bail
0x040CC570(func, nsid)                     ; namespace -> media offset
q   = geom[4] / (geom[1]+1) / round3(0x20 >> c0[0x9255])
dst = 0x04081800 + slba*lbasize + (q<<4)   ; <-- the RAM DISK
src = (tag & 0x8000) ? 0x040612C0 + ((tag & ~0x8000) << 12)
                     : 0x0400F2C0 + (tag << 12)      ; <-- where HW DMA'd the host data
src += (slba & nsid) * lbasize
memcpy(dst, src, nlb * lbasize)            ; 0x040CBFD8 -> 0x040E854C
0x040CD4EC(func, sqid, cid, 0, status)     ; complete
0x040CCD9C(desc[0x1C] >> 16)               ; release the tag
```

**`0x040C0000 - 0x04081800 = 0x3E800` — byte-for-byte the constant used by the
namespace-size arithmetic at `0x040CAF7C`.** The 250 KB "namespace" and the RAM
disk are the same object. That closes the loop on T3.

**Read (`0x040CC300`, q0 — `0x040CC424` is the q1 twin):** pops the descriptor,
checks the abort record at `0x0000C9F6`, allocates a data buffer with
`0x040E7624(1)`, stores the id into `desc[0x10]`, and releases the descriptor to
the RDMA engine with `0x040CD9A8(idx, 1)`. It **never fills the buffer** — the FTL
that was supposed to do that does not exist in GDP. That is why the read side of
the RAM disk is a stub while the write side is complete.

### Why this matters

Everything on the host side of an NVMe Read/Write — doorbell, SQE fetch, PRP list
walk, host DMA, CQE, MSI-X, tag management — is **done by hardware** on this path.
The firmware contract is exactly:

> "descriptor says: function F, queue Q, command C, LBA L, count N, data buffer B.
>  Move N×lbasize bytes between buffer B and the media, then complete."

That is a ~120-instruction function, and `0x040CBD5C` is a working template for it.

---

## T3 — What Identify returns today

### Identify dispatcher — `0x040DF60C`

```
CNS = CDW10 (ctx+0x2C), full 32-bit compare
  CNS == 0 -> 0x040DF41C  Identify Namespace
  CNS == 1 -> 0x040DF2BC  Identify Controller
  else     -> status 0xB (Invalid Namespace or Format), DNR NOT set
```

**CNS 0x02 (Active Namespace ID list) and CNS 0x03 (Namespace Identification
Descriptor list) are not implemented.**

### Identify Controller — builder `0x040DF2BC`, buffer **`0x0000B9A8`** (4 KB)

All offsets are into the 4 KB Identify data structure. Read directly from the code:

| off | field | value | instruction |
|---|---|---|---|
| 0x00 | VID / SSVID | 0 (memset) | — |
| 0x04 | SN | `"SN0123456789ABCDEFGH"` | `0x040DF2E8`, 20 B |
| 0x18 | MN | `"Generic_GDP_NVMe_Device"` + 17 spaces | `0x040DF2F8`, 40 B, string @`0x040DF5CC` |
| 0x40 | FR | `"L190301R"` | `0x040DF308`, 9 B copied into an 8 B field |
| 0x48 | RAB | 0 | `0x040DF330` |
| 0x49 | IEEE OUI | `"MAX"` | `0x040DF32C` |
| 0x4C | CMIC | 0 | `0x040DF334` |
| **0x4D** | **MDTS** | `0x040CC5A0(func)` = `[0x06700000]` bits[23:16] — **runtime, HW-sourced, never written by firmware** | `0x040DF340/0x040DF344` |
| 0x4E | CNTLID | `ctx[0] bits[13:10]` (= function id) | `0x040DF35C` |
| 0x50 | VER | **`0x00010300` = NVMe 1.3.0** | `0x040DF360` |
| 0x100 | **OACS** | **6** = Format NVM + FW Download/Commit | `0x040DF36C` |
| 0x102 | ACL | 3 | `0x040DF374` |
| 0x103 | AERL | 3 | `0x040DF378` |
| 0x104 | FRMW | 2 | `0x040DF37C` |
| 0x105 | LPA | 2 | `0x040DF380` |
| 0x106 | ELPE | 0 | |
| 0x107 | NPSS | 0 | |
| 0x108 | AVSCC | 1 | |
| 0x109 | APSTA | 0 | |
| 0x10A | WCTEMP | `0x157` = 343 K | `0x040DF398` |
| 0x10C | CCTEMP | **0x10** (16 — looks like a firmware bug, harmless) | `0x040DF3A0` |
| 0x13E | DSTO | 1 | |
| 0x13F | FWUG | 1 | |
| 0x148 | SANICAP | 3 | |
| **0x200** | **SQES** | **0x66** (min 6 / max 6 → 64 B) | `0x040DF3A8` |
| **0x201** | **CQES** | **0x44** (min 4 / max 4 → 16 B) | `0x040DF3B0` |
| **0x204** | **NN** | **1** | `0x040DF3B8` |
| **0x208** | **ONCS** | **0** (never written — no DSM, no Write Zeroes, no Compare) | memset |
| 0x20A | FUSES | 0 | |
| 0x20C | FNA | 0 | |
| 0x20D | VWC | **1** (volatile write cache present → Linux will send Flush) | `0x040DF3D4` |
| 0x768.. | SUBNQN | 0 | memset |

Transfer is 4096 B: `0x040DF404 movw r0,#0x400` → the FWDMA length field is in
**dwords** (`0x040E03EC` does `lsrs r0, r7, #2`), so 0x400 dwords = 4096 B.

The fact that Linux shows `Generic_GDP_NVMe_Device` at all proves this whole path —
SQ fetch → firmware → Identify build → FWDMA to host PRP → CQE — works end to end.

### Identify Namespace — builder `0x040DF41C`, same 4 KB buffer

```
nsid = ctx+0x08 & 0xFF
active_mask = 0x040CC7F4(func)            ; func 0 -> [0x06700040] & 0xFF
if ((active_mask >> (nsid-1)) & 1) == 0 -> whole 4 KB is zeroed before DMA
NSZE = NCAP = NUSE = 0x040CC6F0(nsid)     ; select ns (nsid-1) in [0x06700004][18:16],
                                          ; then read u32 from [0x06700014]  (upper dword = 0)
+0x18 NSFEAT = 0
+0x19 NLBAF  = 3          -> 4 LBA formats
+0x1A FLBAS  = byte at 0x000095C0 + (nsid-1)*32
+0x1B MC     = 0 ; +0x1C DPC = 0 ; +0x1D DPS = 0
LBAF0 @0x80 : MS=0 LBADS=9  RP=0   ->  512 B
LBAF1 @0x84 : MS=0 LBADS=10 RP=0   -> 1024 B
LBAF2 @0x88 : MS=0 LBADS=11 RP=0   -> 2048 B
LBAF3 @0x8C : MS=0 LBADS=12 RP=0   -> 4096 B
```

`0x040CC7D0` (called from `0x040CBC90` on init) does
`[0x06700040] = ([0x06700040] & ~0xFF) | 1` → **NSID 1 is marked active**.

### The per-namespace table `0x000095C0` (stride 32) and what NSZE really is

Filled by `0x040CAF14` (boot + every CC.EN 0→1) for nsid slots 0..7:

```
040CAF7C  mov  r8, #0x3e800                  ; 256000
040CAFA4  r6 = 0x20 >> c0[0x9255]            ; LUN/CE shift base
040CAFB0  udivmod(r6*2, 3) -> rem in r1
040CAFB4  sb = (r6<<1) - r1                  ; round down to a multiple of 3
040CAFBC  c0[0x95C0 + n*32 + 0x00] = 0       ; FLBAS = 0  -> 512-byte LBAs
040CAFC0  q  = geom[1]                       ; geom = *(u32*)0x00000DCC
040CAFC8  q2 = geom[4] / (geom[1]+1)
040CAFD4  q3 = q2 / sb
040CAFD8  r0 = 0x3E800 - (q3 << 4)
040CAFE0  r1 = r0 >> 9
040CAFF4  c0[0x95C0 + n*32 + 0x18] = r1 ; +0x1C = 0     ; NSZE = NCAP = NUSE
```

`0x040CC5F8` then copies slot n into the hardware:
`[0x06700004][18:16] = n`, `[0x06700008][2:0] = table[n].FLBAS`,
`[0x0670000C] = table[n]+0x10`, **`[0x06700014] = table[n]+0x18`** (= NSZE).

**So today: FLBAS = 0 (512 B), NSZE ≤ 256000/512 = 500 LBAs ≈ 250 KB.**

And §T2b explains *why* 256000: `0x040C0000 - 0x04081800 = 0x3E800 = 256000`.
The "namespace" is the SRAM gap between the write handler's RAM disk base
(`0x04081800`) and the bottom of the `c1` code image. GDP's namespace is a
**250 KB RAM disk**, not a placeholder number someone typed in. `[INFER, strong]` — the arithmetic is read, the runtime
values of `geom[1]`, `geom[4]` and `c0[0x9255]` are not in the static image, but
the constant `0x3E800` caps the result at 500 LBAs no matter what they are.

A second variant `0x040CB858` (reached from `0x040CBC18`) takes FLBAS per-namespace
from the byte array at `0x00000E38` and divides by `0x200 << FLBAS` instead.

**Answers to the T3 asks:** `NN = 1`, `MDTS = whatever the hardware register says
(not determinable statically; firmware never writes it)`, `SQES = 0x66`,
`CQES = 0x44`, `ONCS = 0`. A namespace structure **does** exist:
`NSZE = NCAP = NUSE ≈ 500`, `FLBAS = 0`, four LBAFs 512/1024/2048/4096.

---

## T4 — Feasibility verdict and the patch plan

### T4.0 Verdict

**Feasible. This is the right path, and it is smaller than the NBD path.**

We are not writing an NVMe controller. We are writing **one function** that the
existing controller calls when an I/O command arrives, and it can call back into
existing firmware for every hard part: PRP walking, host DMA, completion posting,
and the NAND read/write.

### T4.1 The hooks

| # | what | where | how |
|---|---|---|---|
| H1 | replace the I/O dispatcher (**variant B only**) | literal word **`0x040DF54C`** (currently `0x040CA834`) | write our handler address. Also poke `0x00009404` once so the first cycle already uses it. **Data word — no I-cache issue.** |
| H1' | replace the HW-queue drains (**variant A**) | the four `BL`s at `0x040C127C / 80 / 84 / 88` | retarget to our routines. **Code words — needs ICIALLU.** |
| H2 | replace/extend the admin dispatcher | literal word **`0x040DF544`** (currently `0x040CA67C`) | our admin front-end; tail-branch to `0x040CA67C` for anything we don't handle. Also poke `0x000093F0`. |
| P1 | MDTS | word **`0x040DF340`** = `EBFFB496` (`bl 0x040CC5A0`) | → `E3A00003` (`mov r0,#3`) ⇒ MDTS = 3 ⇒ 32 KB max transfer. One word. |
| P2 | (alternative to doing Identify-NS ourselves) namespace size | word **`0x040CAFE0`** = `E1A014A0` (`lsr r1,r0,#9`) | → `mov r1, #imm8 ror 2n`, e.g. `E3A01401` = `mov r1,#0x1000000` ⇒ NSZE = 16 777 216 × 512 B = 8 GB. One word. |

P1/P2 are **code** words, so after writing them the stub must do
`mov r0,#0 ; mcr p15,0,r0,c7,c5,0 ; dsb ; isb` (invalidate I-cache) — see T6.

If we implement Identify Namespace ourselves in the H2 handler, P2 is unnecessary
and the fragile "recomputed on every CC.EN" behaviour stops mattering. **Recommended.**

### T4.2 Making Linux bind and create a block device

Three things must be true.

**(a) A namespace of the right size.** Two options:

* *Cheap:* P2 above + poke `c0[0x000095C0] = 3` (FLBAS → LBAF3 = 4096 B).
  But `0x040CAF14` rewrites both on every CC.EN, so the FLBAS poke does not stick —
  which is why P2 alone is not enough and you'd need a second code patch at
  `0x040CAFBC` (`strb r5,[r7,r4,lsl #5]` → `mov r5,#3` first, or just
  `E3A05003` in place of the zeroing `mov r5,#0` at `0x040CAF2C` — careful, r5 is
  reused as the zero register throughout that function, so this is *not* safe).
* *Clean (recommended):* the H2 admin handler implements **CNS 0 itself**:
  memset `0x0000B9A8` (4 KB), write `NSZE=NCAP=NUSE=<our value>` at +0/+8/+0x10,
  `NLBAF=3` at +0x19, `FLBAS=3` at +0x1A, the four LBAF entries at +0x80..+0x8F,
  then `0x040DF0AC(&req)` to DMA it out and complete. **~45 instructions.**

  **Use LBAF3 (4096 B logical blocks).** With 512 B blocks any sub-4 KB write turns
  into read-modify-write on a NAND that cannot rewrite in place; with 4 KB blocks
  one LBA is exactly one `0x89`/`0x8A` chunk and the problem disappears.
  Bonus: HW namespace slot 7 (which the *vendor* path uses for its CDW15 length
  units) is a different slot, so the existing `jd_hack.py` / `jdnand.py` tooling
  keeps working unchanged.

**(b) Namespace discovery.** `VER = 1.3` ⇒ Linux calls Identify **CNS 0x02**
(active namespace list) first. GDP answers `0xB` **with DNR clear**. Recent Linux
only falls back to the sequential scan when the status has DNR set
(`nvme_scan_work`: `if (ret > 0 && ret & NVME_STATUS_DNR) nvme_scan_ns_sequential(ctrl)`).
`[INFER — from kernel source knowledge, not verified against this machine's kernel]`

So **implement CNS 0x02** in the H2 handler: zero the 4 KB buffer, store `u32 1`
at offset 0, DMA it out. **~12 instructions.** Cheap insurance; do it.

CNS 0x03 (NS descriptor list) failing is non-fatal in Linux (it warns and sets
`NVME_QUIRK_NO_NS_DESC_LIST`), but returning a 4 KB buffer with a single
NIDT=3 (UUID) or simply an all-zero buffer is another ~10 instructions.

**(c) I/O queues.** Nothing to do — Create SQ/CQ already work and Set Features
FID 7 already grants 8 queues.

> **Can we instead serve Read/Write on the admin queue?**
> **No.** Say it plainly: the Linux `nvme` driver never issues opcode 0x01/0x02 on
> the admin queue. `nvme_alloc_ns` → `blk_mq_alloc_disk` uses `ctrl->tagset`, which
> is bound to the I/O queues created in `nvme_setup_io_queues`; the admin tagset
> (`ctrl->admin_tagset`) is used only by `nvme_submit_sync_cmd`/passthru. There is
> no switch, quirk or sysfs knob that routes block I/O to qid 0. If zero I/O queues
> come up, `nvme_setup_io_queues` fails and the controller is marked dead.
> Fortunately this is moot: I/O queue creation already works.

### T4.3 The I/O handler — two variants, pick after the §B experiment

#### Variant A (preferred if Read/Write land in the hardware queues — see §T2b)

Patch the four `BL`s in the main loop so they call our routines instead:

| addr | now | becomes |
|---|---|---|
| `0x040C127C` | `bl 0x040CBD5C` | `bl our_write_q0` |
| `0x040C1280` | `bl 0x040CC018` | `bl our_write_q1` |
| `0x040C1284` | `bl 0x040CC300` | `bl our_read_q0` |
| `0x040C1288` | `bl 0x040CC424` | `bl our_read_q1` |

(4 code words + one `ICIALLU`. Alternatively patch only the `bl 0x040E854C`
memcpy inside `0x040CBD5C` for a first "write goes to NAND" proof of life.)

```
our_write_qN():                     ; template: 0x040CBD5C, keep its head verbatim
    if !0x040CD898(): return
    idx = 0x040CD938(); if idx == 0xFFFF: return
    d = 0x04000000 + idx*0x2C
    0x040CD8E8()                                    ; pop
    func=d[0x0C]&3; cid=d[0x14]&0xFFFF; sqid=d[0x14]>>16
    nsid=d[0x20]&0xFF; slba=d[0x18]; nlb=(d[0x1C]>>8)&0xFF
    src = (d[0x10]&0x8000) ? 0x040612C0 + ((d[0x10]&~0x8000)<<12)
                           : 0x0400F2C0 +  (d[0x10]<<12)
    <abort-record interlock: copy 0x040CBDE0..0x040CBE94 verbatim>
    for i in 0..nlb-1:
        (ch,ce,rowfield,page,chunk) = lba_map(slba + i)
        fill 0x00009210+8..+0x13 ; move 4096 B from src+i*4096 into 0x0400F2C0 (or aim
        the HW buffer directly by using it as the page buffer) ; bl 0x040C3DB4
        on failure: status = 0x4280 | DNR ; break
    0x040CD4EC(func, sqid, cid, 0, status)
    0x040CCD9C(d[0x1C] >> 16)

our_read_qN():                      ; template: 0x040CC300
    ... same head ...
    buf = 0x040E7624(1); if buf == 0xFFFF: print "r0buf"; return
    for i in 0..nlb-1:
        bl 0x040C4360 into 0x0400F2C0 ; copy 4096 B to (buffer base for `buf`) + i*4096
    d[0x10] = buf
    0x040CD9A8(idx, 1)              ; HW now DMAs the buffer to the host and completes
```

Note the read side does **not** call `0x040CD4EC` — handing the descriptor back with
`0x040CD9A8` is what triggers the host DMA and the completion. Worth confirming on
hardware, because `0x040CC424` does end with an explicit completion in some paths.

**The one thing I could not resolve statically:** where the buffer id from
`0x040E7624` maps to in SRAM. The write side shows the mapping for *its* tags
(`0x0400F2C0 + tag*0x1000`, or `0x040612C0 + (tag & 0x7FFF)*0x1000`), and it is
`[INFER, likely]` the same for read buffers — but it must be verified before the
read path is trusted.

Size estimate variant A: **~120 instructions per direction**, most of it copied
verbatim from the existing handlers.

#### Variant B (if Read/Write arrive in the firmware FIFO)

```
our_io_handler():                                   ; installed via the H1 word
    if 0x040DEF94(1) != 1: return                   ;  4 insns
    ctx = 0x0000CA0C
    op  = ctx[0] >> 24
    if op != 1 and op != 2: b 0x040CA834            ;  4 insns  (Flush/DSM/invalid fall through)
    func = ctx[0] bits[13:10]; sqid = ctx[0] bits[20:16]; cid = ctx[6]
    slba = ctx[0x2C] | (ctx[0x30] << 32)            ; 4 KB LBAs -> 32 bits is plenty
    nlb  = (ctx[0x34] & 0xFFFF) + 1                 ; 1..8 with MDTS=3
    if slba + nlb > NSZE:  status = 0x280 (LBA Out of Range) ; complete; return
    for i in 0..nlb-1:
        (ch, ce, rowfield, page, chunk) = lba_map(slba + i)
        fill 0x00009210+8..+0x13 with the vendor PageRead/PageWrite parameter block
        if write: xfer_from_host(4096, 0x0400F2C0, prp_cursor)  ; then bl 0x040C3DB4
        else:     bl 0x040C4360 ; xfer_to_host(4096, 0x0400F2C0, prp_cursor)
        if failed: status = 0x2281 (read) / 0x2280 (write), DNR set; break
    0x040CD4EC(func, sqid, cid, 0, status)
    *(u32*)0x00009404 = 0x040DEFEC                  ; back to the fetch state
```

Size estimate variant B: **~120–160 ARM instructions** including the PRP cursor
(variant B is the one that needs its own PRP walker, §T4.4; variant A does not,
because the hardware already did the PRP walk).

Parameter block layout for the vendor NAND handlers (read out of `0x040C4360`
and `0x040C3DB4`, base `0x00009210`):

| offset | meaning |
|---|---|
| `+0x08` | channel (0..3) |
| `+0x09` | `[3:0]` bank/CE, `[7:4]` LUN |
| `+0x0A` u16 **big-endian** | rowfield = `block*planes + plane` |
| `+0x0C` u16 **big-endian** | page |
| `+0x0E` | LDPC enable |
| `+0x0F` | scrambler enable |
| `+0x10` | plane |
| `+0x11` | (write) chunk count |
| `+0x12` | (read) simulate-pattern index — must be **0**; (write) chunk index |
| `+0x13` | chunk index |
| `+0x02` | **output**: error code, 2 = failure |

Both handlers use **`0x0400F2C0`** as the 16 KB page buffer (read lands there,
write is programmed from there). Return value 1 = ok.

> **Optimisation worth taking:** `0x040C4360` does
> `memset(0x0400F2C0, 0, 1 << geom[0x1D])` — a **16 KB memset on every 4 KB read**
> (`0x040C4500`). At SRAM speeds that is tens of microseconds of pure waste per
> operation. Either patch that `blx 0x40c02b4` to a NOP (`E1A00000`), or skip the
> vendor wrapper entirely and call the internal sequence
> `0x040DB828` (handle alloc) → `0x040DE038` (page-read submit) → poll, the way
> `0x040C4360` does after the memset.

### T4.4 Host data movement — already written, just call it

```
0x040E03EC(len_bytes, sram_buf, prp_lo, prp_hi)   ; controller -> host   (Thumb)
0x040E041C(len_bytes, ?, prp_lo, prp_hi, [sp+0x10]=sram_buf)  ; host -> controller
```
Both build a 0x2C-byte request on the stack and call the **blocking** wrappers
`0x040CE7D0` (to host, dir byte 0) / `0x040CE814` (from host, dir byte 4), which
submit via `0x040CE31E` to FWDMA `0x06740000`, spin on `0x040CE5C6`, and free the
tag with `0x040CE5F6`. Request struct:

| off | field |
|---|---|
| `+0x00` | DMA tag (filled by `0x040CE294`) |
| `+0x04` | SRAM buffer |
| `+0x08/+0x0C/+0x10` | host address words (→ FWDMA `+0x20/+0x24/+0x28`) |
| `+0x14` | length **in dwords**, asserted ≤ `0x4000` ⇒ **64 KB per transfer** |
| `+0x1C` | sector-size selector (auto-chosen by `0x040CE744`) |
| `+0x1E` | sector count |
| `+0x20` | direction: 0 = to host, 4 = from host |

For multi-page transfers, `0x040E04A8` is a complete **PRP walker** already in the
image: chunk 0 from PRP1 up to the page boundary, chunk 1 from PRP2 if the total
fits in two pages, otherwise PRP2 is a list pointer and entries come from the
pre-fetched list buffer. We can either reuse its structure or write our own
~50-instruction version; with MDTS = 3 (32 KB) a PRP list is needed whenever the
transfer exceeds 2 pages, so the list case cannot be skipped unless MDTS = 1 (8 KB)
**and** we accept the 3-entry corner case. Cleanest: write our own walker that
does PRP1, PRP2, and a PRP list fetched with one `0x040E041C` call.

### T4.5 LBA → (channel, CE, block, page, chunk) mapping

With 4 KB logical blocks and one 4 KB chunk per `0x89`/`0x8A`, the natural map is

```
usable_chunks_per_page = 1            (today; 4 if RAPOR §55.4 gets solved)
die        = lba % 16                 ; 16 dies = 4 ch x 4 CE  -> interleave for future parallelism
within     = lba / 16
page       = within % PAGES_PER_BLOCK
block_idx  = within / PAGES_PER_BLOCK
block      = good_block_table[die][block_idx]     ; skip list
ch = die & 3 ; ce = die >> 2
rowfield   = block * PLANES + plane               ; RAPOR §51.4: rowfield = block*4 + plane
```

`PLANES` is 4 per `RAPOR.md` §51.4 (`rowfield = block*4 + plane`); `PAGES_PER_BLOCK`
is **not known** — 64 pages were verified working in §55.1 and no upper bound was
found. It must be measured (write page N, read back, bisect) before the table is built.

**Bad-block skipping.** There is no block-level bad-block table in GDP; the only
map in RAM is a **die**-level exclusion byte array at `geom + 0x310`
(index `(lun<<6)|(bank<<3)|ch`, `0xFF` = excluded), checked at `0x040C44C4`.
So the good-block list is ours to build and ours to store. Per `RAPOR.md` §55.2 the
only valid test is **erase → page 0 and page 8 must read back all `0xFF`**;
the `sts0 & 0xE1` FAIL bit alone is not sufficient.

Plan: run the strict scan once over all 16 × ~2310 blocks from the host with the
existing vendor tooling (≈ 6 vendor commands per block at ~0.6 ms ⇒ roughly
10–30 minutes including erase time), then write the resulting good-block list
**into the NAND itself** (a few blocks at a known location, e.g. die 0 block 8+,
written with `ldpc=1 scr=1`), and have the firmware patch load it into SRAM at
boot. Until that is built, a first version can simply ship the table from the host
via a new vendor sub-command into a spare SRAM buffer.

Capacity: `16 dies × good_blocks × PAGES_PER_BLOCK × 4 KB`.
At ~2310 blocks/die and ~85 % good that is ~31 400 blocks; with 288 pages/block
≈ **36 GB**, with 1152 pages/block ≈ **145 GB**. ×4 if the full-page (4 chunks per
page) path is ever solved. All of this is `[INFER]` until PAGES_PER_BLOCK is measured.

### T4.6 Size summary

| piece | instructions | difficulty |
|---|---|---|
| H1/H2 hook words | 4 stores | trivial |
| MDTS patch (P1) | 1 word + ICIALLU | trivial |
| admin front-end: gate, opcode/CNS decode, tail-branch | ~30 | easy |
| Identify NS (CNS 0) built by us | ~45 | easy |
| Identify active-NS list (CNS 2) | ~12 | easy |
| Identify NS descriptors (CNS 3) | ~12 | easy |
| I/O handler skeleton + completion + state restore | ~50 | easy |
| PRP walker (PRP1 + PRP2 + list) — **variant B only** | ~55 | **medium** — the list case is where bugs hide |
| LBA → (ch,ce,block,page) with good-block table lookup | ~45 | easy, but depends on the table |
| good-block table: build (host) + store in NAND + load at boot | ~80 fw + host script | **medium** |
| **total firmware** | **~330** | |

**Genuinely hard parts, honestly:**

1. **Write ordering / no FTL.** A plain LBA→block map means every write to an
   already-written LBA needs an erase of a whole block. Without an FTL, the device
   is effectively **write-once per erase cycle**. A filesystem will corrupt data on
   the second write to the same LBA. Two honest ways out:
   * ship it read-mostly: format once, `dd` the image on, then mount read-only; or
   * put the translation layer **in the host** (see T5) and keep the firmware dumb.
   This — not the NVMe plumbing — is the real design decision.
2. **PAGES_PER_BLOCK and the strict bad-block map** are unknown and must be measured.
3. **Program order inside a block.** 3D TLC normally requires sequential page
   programming within a block; random-order page writes are a documented way to
   lose data. Our allocator must write pages strictly in order.
4. The **PRP-list** path — the one piece with no existing simple helper we can call
   verbatim.
5. **Multi-die parallelism.** The firmware serialises (T5b). Getting past ~1 NAND
   op in flight means driving the FCQ with several outstanding descriptors, which
   is a much bigger job than everything above combined. Skip it for v1.

---

## T5 — Is there a cheaper path?

### (a) Userspace NBD over the existing vendor commands

Throughput ceiling, from measured numbers in `RAPOR.md` §53.4 / §55.5:

* one 4 KB read = `0x89` (admin cmd) + `0xC2` (admin cmd) = **2 NVMe commands**
* measured per-command turnaround ≈ **556 µs**, attributed to the controller
* measured end to end: read **1.15–3.6 MB/s**, write **1.9–3.7 MB/s**

So the ceiling is ~**3.5 MB/s**, and NBD adds nothing on top except protocol
overhead (loopback NBD is ~µs, irrelevant here). Batching helps a little: 4 × `0x89`
into the 16 KB buffer followed by one 16 KB `0xC2` would be 5 commands per 16 KB
≈ 2.8 ms ⇒ **~5.7 MB/s** for reads — but `RAPOR.md` §55.4 says the 4-chunk *write*
path does not work yet, so writes stay at ~3.5 MB/s.

At 3.5 MB/s, filling a 36 GB volume takes ~3 hours; a full verify pass another 3.
Usable, but it is a rescue appliance, not a disk.

### (b) Can multiple NVMe commands be in flight against GDP?

**No. The firmware serialises, hard.** Four independent pieces of evidence:

1. **One context buffer per class.** `0x0000C9A8` (admin), `0x0000CA0C` (I/O),
   `0x0000CA50` (fio) — a second concurrent admin command would overwrite the
   first one's SQE in place.
2. **A single "command pending" byte per class** at `0x0000B9A0 + class`
   (`0x040DEF6C` / `0x040DEF94`), set by the fetch state and cleared by the
   dispatcher. The fetch state cannot re-arm until the dispatcher has run.
3. **A single completion poster.** `0x040CD53C` gates the whole fetch on
   `(CQM 0x06738000 + 0x6C) & 1 == 0`, i.e. the previous CQE must already be posted.
4. **Vendor-protocol state is global**: current-command byte `0x00000EDC`,
   phase/record at `0x0000EAB0`, payload buffer `0x0000CA98+0x18`, page buffer
   `0x0400F2C0`, parameter block `0x00009210`. Two overlapping vendor commands
   would corrupt each other's page buffer. This is also exactly the failure mode
   described in `RAPOR.md` §54.3 item 1 ("never skip phase 2 — the DMA engine locks").

The three *classes* can overlap with each other (one admin + one I/O + one fio),
but all vendor traffic is admin, so **queue depth > 1 buys nothing and risks
corruption**. Do not try it.

### (c) ublk / vduse instead of NBD

Both are better plumbing than NBD — `ublk` avoids the socket round trip and the
NBD kernel thread, `vduse` avoids the copy. But the bottleneck here is **556 µs of
controller latency per command**, ~500× larger than any of these differences.
`ublk` would change 3.5 MB/s into 3.5 MB/s.

The one real argument for `ublk` over NBD is robustness: NBD has a long history of
deadlocking when the backing store is slow and the kernel is under memory pressure
(the classic `nbd` + writeback deadlock), whereas `ublk` was designed for exactly
this. If you do go the userspace route, **use `ublk`, not NBD** — same speed, fewer
ways to hang the box.

### Recommendation

**Do both, in this order:**

1. **`ublk` first, this week.** It needs no new firmware, no new risk, and it gives
   an immediately usable `/dev/ublkb0` at ~3.5 MB/s that you can `dd`, `fsck`,
   image, and — most importantly — **use to build and validate the strict
   good-block table and to measure PAGES_PER_BLOCK**, which the firmware patch
   needs as an input anyway. It also gives a reference implementation of the
   LBA→(ch,ce,block,page) map in Python, where it is cheap to debug, before that
   same map has to be written in ARM assembly with no debugger.

2. **Then the firmware patch.** It is a ~200–330-instruction job whose hardest parts
   (the good-block table, the geometry constants, the mapping) are exactly the
   things step 1 produces. Expected gain: the host round trip disappears entirely;
   per-4 KB cost drops to NAND tR (~60–100 µs TLC) plus FWDMA, so roughly
   **10–30 MB/s** single-threaded `[INFER — no in-firmware timing was measured;
   RAPOR §51.1 only says the read "completes in 0.0 s" after the poll-timeout fix]`.
   That is ~5–10× and turns it from a rescue appliance into a slow but real disk.

What would change my ordering: if `PAGES_PER_BLOCK` and the good-block map were
already known, I would go straight to the firmware patch, because the NVMe plumbing
really is that close to done.

---

## T6 — Hard blockers

I looked for all four categories. **None of them blocks us.**

### Signature / RSA / CRC checks on loaded code — **none found**

* No strings matching `rsa|sign|verif|auth|sha|hmac|crc` anywhere in `c0`/`c1`
  (1180 extracted strings scanned).
* We already load a 240 KB unsigned image (`gdprun`) and jump to it, and we already
  install and execute our own stub at `0x040FF100` by rewriting a dispatch-table
  entry. That is the empirical proof.
* `PreCheckCodeBlock` (vendor cmd `0x3A`, handler `0x040C379C`) exists but is a
  *NAND* code-block precheck, and per `RAPOR.md` §54.5 it hard-locks the controller —
  **do not call it**.

### Memory protection — **MPU present, and our regions are already RWX**

The reset handler at `0x00000B1C` programs 8 ARMv7-R PMSA regions:

| rgn | base | size | DRACR | meaning |
|---|---|---|---|---|
| 0 | `0x00000000` | 4 GB | `0x1308` | background: RW, C=1, **XN** |
| 1 | `0x00000000` | 128 KB, subregions 6–7 disabled (⇒ 0–96 KB) | `0x329` | **RWX** — `c0` lives here |
| 2 | `0x00800000` | 64 KB | `0x329` | RWX |
| 3 | `0x00810000` | 64 KB | `0x1308` | RW, XN |
| 4 | `0x04000000` | 512 KB | `0x1308` | RW, XN — the NAND handle/descriptor area |
| 5 | **`0x04080000`** | **512 KB** | **`0x308`** | **RWX** — `c1` (`0x040C0000`), our stub (`0x040FF100`), and the DMA buffer are all inside |
| 6 | `0x06000000` | 1 MB | `0x310` | device memory |
| 7 | `0xFFFF0000` | 64 KB | `0x608` | RO |

All higher regions are explicitly disabled (`0x00000CA4` loop). So:

* `0x040C0000`–`0x040FFFFF` is **read/write/execute**. Patching firmware code and
  running injected code are both permitted by the MPU. ✔
* Note the MMIO blocks we use (`0x06600000`, `0x06700000`, `0x067E0000`) fall
  **outside** region 6 and land on the cacheable background region 0 — which would
  be wrong, except that the D-cache is off at that point (see next item) and is
  only enabled later. `[INFER]` the hardware must be aliasing or the accesses are
  tolerated; in any case this is the firmware's existing behaviour, not something
  we change.

### Caches — **on, so one extra instruction is required after code patches**

The reset handler leaves SCTLR with M=1, C=0, I=0, but `0x040CF580` later calls
`0x040EC514`, which sets SCTLR bits 12 (I) and 2 (C). Region 5's DRACR `0x308`
is TEX=0/C=1/B=0 = **write-through**, so data stores reach memory immediately and
there is no D-cache writeback problem. The **I-cache is the issue**: after writing
instruction bytes, stale lines can persist. There is exactly one `ICIALLU` in the
whole image (`0x00000B50`, inside the reset path) and no callable helper.

**Fix:** append to our injected stub

```
    mov  r0, #0
    mcr  p15, 0, r0, c7, c5, 0     ; ICIALLU - invalidate entire I-cache
    dsb  sy
    isb  sy
```

and run it after any code-word patch. Four instructions. Not a blocker — but if
it is forgotten, the symptom is "the patch silently did nothing", which is exactly
the kind of thing that wasted days earlier in this project.

Better still: **the two primary hooks (H1/H2) are literal-pool data words, not
instructions**, so if we implement Identify NS ourselves and skip the MDTS patch,
**no instruction byte in the existing firmware needs to change at all.**

### Watchdog — **none found**

No `wdt|watchdog|wdog` strings, no obvious timer-reload loop in the scheduler.
The only timeout-like constants are software poll counters:
`0x040DBD44` (FCQ poll, the one already reduced from 10 000 000 to 300 000) and
`0x040DFECC` (`0x100000` spins in Abort). A long NAND operation inside our I/O
handler will not be killed by hardware — but it *will* be killed by the host:
Linux's default I/O timeout is 30 s (`/sys/block/nvmeXnY/device/io_timeout`), and
an NVMe timeout triggers a controller reset, which re-runs `0x040CAF14` and would
wipe a poked (as opposed to patched) namespace table.

### Other things that could bite, that I did *not* find a blocker for

* **CC.EN 0→1 re-init.** `0x040CB74C` → `0x040CAF14` recomputes the namespace and
  queue tables on every controller enable. Anything we *poke* into `0x000095C0`,
  `0x000094E0` or `[0x06700014]` is erased at the next `nvme reset` / driver reload.
  Anything we *patch* (code) or *hook* (the literal words, which `0x040CAF14` never
  touches) survives. Design accordingly.
* **`0x040E88C8` / `0x040E8A00`** are an unreferenced duplicate of the same init —
  dead code carried over from the product firmware source. Harmless, but do not
  patch it by mistake thinking it is the live one; the live one is `0x040CAF14`.
* **Commands that hard-lock the controller** (`RAPOR.md` §54.5): vendor `0x3A`,
  `0x53`, `0x55`, `0x57`. Our handler must never reach them.

---

## Appendix A — address quick reference

### NVMe layer
| addr | what |
|---|---|
| `0x040CA67C` | **admin command dispatcher** (switch on opcode) |
| `0x040CA834` | **I/O command dispatcher** (rejects everything but 0x00/0x09) |
| `0x040CA8A4` | third-class ("fio") dispatcher, always status 1 |
| `0x040CC83C/884/8D4/8EC` | class-has-cmd / select-class / fetch-done / drain command FIFO |
| `0x040CD4EC` | post completion (CQM) |
| `0x040CD53C` | completion poster free? |
| `0x040DEF6C / 0x040DEF94` | set / get per-class "command pending" |
| `0x040DEFC0 / 0x040DEFEC / 0x040DF018` | fetch states (admin / io / fio) |
| `0x040DF044` | admin "DMA done → complete" state |
| `0x040DF0AC` | admin "start FWDMA of a 4 KB buffer, then complete" |
| `0x040DF134` | Async Event Request |
| `0x040DF154` | Get Log Page |
| `0x040DF2BC` | **Identify Controller** builder (buffer `0x0000B9A8`) |
| `0x040DF41C` | **Identify Namespace** builder |
| `0x040DF60C` | Identify dispatcher (CNS 0 / 1 only) |
| `0x040DF668` | Get Features |
| `0x040DF7BC` | Set Features (FID 7 at `0x040DF840`) |
| `0x040DF96C` | **Create I/O CQ** |
| `0x040DFA60` | **Create I/O SQ** |
| `0x040DFBD4` / `0x040DFD08` | Delete I/O SQ / CQ |
| `0x040DFE74` | Abort |
| `0x040E0974` | vendor 0xC1/0xC2 entry (Thumb) |
| `0x040E0448` | vendor payload / PRP-list prefetch (Thumb) |
| `0x040E04A8` | **generic PRP walker** (Thumb) |
| `0x040E03EC` | DMA controller→host `(len, sram, prp_lo, prp_hi)` (Thumb) |
| `0x040E041C` | DMA host→controller (Thumb) |
| `0x040CE7D0 / 0x040CE814` | blocking FWDMA wrappers (to host / from host) |
| `0x040CE31E` | FWDMA submit (Thumb) |
| `0x040CE294 / 0x040CE5C6 / 0x040CE5F6` | FWDMA tag alloc / poll / free |
| `0x040CAF14` | **namespace + queue table init** (boot and every CC.EN 0→1) |
| `0x040CC5F8` | copy namespace table → HW registers |
| `0x040CC7D0` | mark NSID 1 active (`[0x06700040] |= 1`) |
| `0x040CC6F0 / 0x040CC73C / 0x040CC7F4 / 0x040CC5A0` | NSZE / LBA size / active mask / MDTS readers |
| `0x040CCF60` | HW queue allocate |
| `0x040CB670…0x040CB760` | CC.EN / shutdown / NSSR state machine |

### Hardware-assisted I/O path (T2b)
| addr | what |
|---|---|
| `0x040C0DA8` | GDP `main()` |
| `0x040C1270…0x040C12E4` | **main loop** |
| `0x040C127C / 0x040C1280` | `bl` HW **write** queue 0 / 1 drain |
| `0x040C1284 / 0x040C1288` | `bl` HW **read** queue 0 / 1 drain |
| `0x040CBD5C / 0x040CC018` | HW write q0 / q1 handler (**RAM-disk memcpy at `0x040CBFD8`**) |
| `0x040CC300 / 0x040CC424` | HW read q0 / q1 handler (buffer alloc only — no data) |
| `0x040CD898/8AC/8C0/8D4` | "queue has a command" |
| `0x040CD938/954/970/98C` | descriptor index |
| `0x040CD8E8/8FC/910/924` | pop / ack |
| `0x040CD9A8` | hand a read descriptor back to the RDMA engine |
| `0x040CDA78 / 0x040CDA90` | RDMA submit slot free? |
| `0x040CCD9C` | release command tag (`[0x06700188]`) |
| `0x040E7624 / 0x040E75EC` | data-buffer id alloc / free (`0x06500000`) |
| `0x040CC570` | namespace → media offset |
| `0x04000000 + idx*0x2C` | I/O command descriptor (shared with the NAND handle pool) |
| `0x04081800 … 0x040C0000` | **the 250 KB RAM disk** (`0x3E800` bytes) |
| `0x0400F2C0 + tag*0x1000` | HW DMA data buffers (pool 0) |
| `0x040612C0 + tag*0x1000` | HW DMA data buffers (pool 1) |

### RAM objects
| addr | what |
|---|---|
| `0x0000B9A0` | 3 × "command pending" bytes |
| `0x0000B9A8` | 4 KB admin data buffer (Identify / Log Page) |
| `0x000093F0 / 0x00009404 / 0x00009418` | task nodes (admin / io / fio), `fn` at +0 |
| `0x000094E0` | per-function queue/feature table, stride 0x38 |
| `0x000095C0` | per-namespace table, stride 0x20 (+0 FLBAS, +0x18 NSZE) |
| `0x00009210` | vendor sub-command parameter block |
| `0x0000C9A8 / 0x0000CA0C / 0x0000CA50` | admin / io / fio command contexts (0x44 B) |
| `0x0000C9F6` | pending-abort record |
| `0x0000CA98` | vendor state; `+0x18` = payload / PRP list buffer |
| `0x00000DCC` | pointer to the flash geometry struct |
| `0x0400F2C0` | 16 KB NAND page buffer (read lands / write sources) |
| `0x040FF100` | our existing injected stub |

### Patch words
| addr | now | proposed |
|---|---|---|
| `0x040DF54C` | `040CA834` | our I/O handler (**data**, no I-cache flush needed) |
| `0x040DF544` | `040CA67C` | our admin front-end (**data**) |
| `0x040DF340` | `EBFFB496` | `E3A00003` → MDTS = 3 (**code**, needs ICIALLU) |
| `0x040CAFE0` | `E1A014A0` | `E3A01401` → NSZE = 0x1000000 (**code**; unnecessary if we build Identify NS ourselves) |
| `0x040C4500` | `blx 0x040C02B4` | `E1A00000` NOP — kills the 16 KB memset per 4 KB read (**code**) |
| `0x040C127C` | `bl 0x040CBD5C` | variant A: `bl our_write_q0` (**code**) |
| `0x040C1280` | `bl 0x040CC018` | variant A: `bl our_write_q1` (**code**) |
| `0x040C1284` | `bl 0x040CC300` | variant A: `bl our_read_q0` (**code**) |
| `0x040C1288` | `bl 0x040CC424` | variant A: `bl our_read_q1` (**code**) |
| `0x040CBFD8` | `bl 0x040E854C` (RAM-disk memcpy) | variant A minimal proof-of-life: `bl our_nand_write` (**code**) |

---

## Appendix B — what I could not determine

* **⭐ Which path an NVMe Read/Write actually takes.** Both landing zones exist and
  both are serviced every main-loop iteration: the firmware FIFO dispatcher
  `0x040CA834` (which rejects opcode 1/2) and the hardware WDMA/RDMA queues
  (`0x040CBD5C` / `0x040CC300`). Statically I could not find the SQM configuration
  bit that decides. This is the single most important open question, because it
  selects patch variant A or B in §T4.3.

  **Decisive experiment (cheap, and mostly read-only):** with the current unpatched
  GDP, bring the drive up, let Linux create an I/O queue, and issue one 4 KB read
  at LBA 0 (`dd if=/dev/nvme0n1 bs=4k count=1` if a namespace node exists, or
  `nvme io-passthru` on an I/O queue). Then:
  * console/UART prints `iop:02` and the command fails with *Invalid Opcode*
    ⇒ **firmware FIFO path ⇒ variant B**;
  * no `iop:` line, and the command returns success with garbage or zeros
    ⇒ **hardware RDMA path ⇒ variant A**.
  A write to LBA 0 followed by a read of LBA 0 returning the same bytes would
  additionally prove the `0x04081800` RAM disk is live.

* **Where the read-side data-buffer ids from `0x040E7624` map in SRAM.** The write
  side's tag→address mapping is read (`0x0400F2C0 + tag*0x1000` /
  `0x040612C0 + (tag & 0x7FFF)*0x1000`); `[INFER]` the read pool is the same, but
  the read handler never touches data so the code does not show it.

* **Whether `0x040CD9A8` alone completes a read**, or whether an explicit
  `0x040CD4EC` is also required. `0x040CC300` returns without completing;
  `0x040CC424` has completion paths. Needs one experiment.

* **MDTS's current value.** `0x040CC5A0` reads `[0x06700000]` bits[23:16]; no
  firmware code ever writes that field. It is a hardware/strap/`LDBK CONFIG`
  default. Read it live with the existing RAM/MMIO peek before relying on it.
* **`PAGES_PER_BLOCK`** and the true block count per die. 64 pages verified in
  `RAPOR.md` §55.1; the loader block suggests ~2310–2315 blocks/die. Must be measured.
* **The runtime contents of `0x000095C0`** (and therefore the exact current NSZE).
  The arithmetic is read; `geom[1]`, `geom[4]`, `c0[0x9255]` are runtime values.
  Worth one RAM peek — it will confirm or refute "the namespace is ~250 KB".
* **Whether a `/dev/nvme0nX` node exists today.** Everything points to "no, or a
  useless 250 KB one", but I did not (and must not) touch the device to check.
  `cat /sys/class/nvme/nvme*/nvme*n*/size` answers it in one read-only command.
* **What the third command class ("fio", ctx `0x0000CA50`, dispatcher
  `0x040CA8A4`) is for.** It is wired up, arbitrated and always answers "invalid".
  Best guess `[INFER]`: the second PCIe function / VF path, or a firmware-internal
  queue. Not needed for anything here.
* **The exact in-firmware cost of a 4 KB NAND read.** All timing in `RAPOR.md` is
  host-side and dominated by the ~556 µs command turnaround. The 10–30 MB/s
  estimate for the patched path is an inference from NAND tR, not a measurement.
* **FWDMA "sector size" auto-config (`0x040CE744`) for unusual lengths.** It refuses
  (prints an assert and spins on the UART-busy byte at `0x00000E58`) if the length
  exceeds `0x4000` dwords = 64 KB, and otherwise searches divisors 0x1F…1 for the
  largest count ≤ 31 that divides the length exactly. 1024 dwords (a 4 KB transfer)
  resolves to count 16 / sector 64 dwords, so 4 KB is fine — as is the 1024-dword
  Identify that demonstrably works today. **Any length that is not divisible by a
  value ≤ 31 will make it fall through without configuring**, so our handler must
  only ever hand it power-of-two lengths.
