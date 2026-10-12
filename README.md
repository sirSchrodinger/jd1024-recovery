# JD1024 recovery — a personal SSD, MAXIO MAP1202 + SK hynix V6, stuck in read-only

This is a running log of me trying to recover my own 1TB NVMe SSD (JamesDonkey JD1024, MAXIO
MAP1202 controller, SK hynix V6 NAND) after it dropped into a read-only state. No data-recovery
service, no warranty claim — just DIY, with a lot of reverse engineering, documented as it
happened. I'm posting it because I'm stuck on one specific thing and could use outside
knowledge.

## TL;DR

- **Root cause (confirmed):** one physical die (channel 3 / CE 2) developed a cluster of erase
  failures. That die happens to be the controller's boot die, so its system-block errors trip
  an internal assert counter; past a threshold, the firmware engages write-protection as a
  safety fallback instead of risking a harder failure. The other 15 dies are healthy.
- **What I did:** recovered using MAXIO's own vendor MP/Sorting tool (MXMPTool), run in a
  Windows VM with the drive passed through over a USB-NVMe bridge. Found and patched two
  independent bugs in the tool's own die-exclusion feature (it's a legitimate, vendor-supported
  mechanism for excluding a known-bad die from the active capacity; the tool itself just never
  applied it correctly). That broke a "MEET CAPACITY" wall that had blocked every attempt for
  weeks. Worked through two more walls after that via plain tool configuration.
- **Where I'm stuck now:** the process gets all the way through preformat and firmware
  download, then fails trying to boot into the freshly-written system firmware
  ("(E00) R/W Test Fail — Jump to system fail"). Best evidence: my tool package was built for a
  different NAND generation (SK hynix V8) and is missing the correct SK hynix V6
  system-firmware binary. I've confirmed the correct package exists (independently
  cross-referenced two separate sources) but haven't been able to get it.
- **What would help:** anyone who's dealt with MAXIO MAP1202 + SK hynix V6 and has, or can
  point me to, the matching MP/Sorting Tool package or just the compiled system-firmware file —
  or anyone who recognizes this exact failure mode and has an idea I haven't tried.

## Update, 12 Oct

- **Nand Sweep Test passes on all 15 active dies** (raw read + write). So the "Jump to system fail" is not a general NAND problem, it's something narrow around the boot handoff.
- **E00 reproduced 5 times** (42 s each), including after a real physical power cycle. Erase Search and the Unbalance FW option made no difference.
- **Suspect now: missing second SYS component.** `MPTOOL.ini` has `SYS_Qnty=2`, but the package only has one system binary. All 26 copies in the SYS folder are byte-identical (the one variant extracted from the drive itself that checks out). That fits "needs a second piece" better than a die-b problem.
- Two mails sent: the reseller and MAXIO. No reply yet.
- A scan tool I used had a wrong geometry file default, which made every read time out. Fixed, reads work now. Nothing new came out of it.
- Added `tools/` (read-only survey scripts over a JMS583 USB bridge, they need the unpublished loader to run, so they are for reading, not a drop-in) and `logs/`. Full day-by-day notes are in `DEVAM_2026-10-10_v3.md`.

If you have the MAP1202 + SK hynix V6 MP tool package, or know what the second SYS piece should be, that's the thing I'm missing.

## Straight answer: yes, I tried the write-protect bypass

I did. Early on I went after the write-protect latch directly: reading the fault record from NAND through the debug tunnel and trying to clear it so the drive would accept writes. It was 90+ attempts across several sessions. It never gave me a durable writable drive. In the one case I pushed far enough, the drive got worse (stopped booting cleanly), because the bad die just trips the counter again on the next boot.

After that I stopped and switched to the vendor-tool route (exclude the bad die properly). I still don't publish the register addresses or patch bytes for the bypass, because they would not fix anything for you either, and they are a good way to brick a drive. The reasoning is in the section below. I'm saying this plainly so nobody thinks I started on the clean path. I didn't.

## Made with AI (Claude), and how far that got

Most of the reverse engineering, scripts and these notes were done with Claude (Claude Code) running in my terminal, with me deciding direction and doing the physical steps (plugging, unplugging, power cycles). Several `ANALIZ_*` files are written analyses by Claude sessions from disassembly and dumps.

If you try the same with Claude, GPT or any other assistant, expect this:

- It gets surprisingly deep. Disassembling the vendor tool, finding the capacity check, patching the die-exclusion bugs, building a USB-bridge tunnel to the controller. All of that came out of these sessions.
- It also gets stuck exactly where I'm stuck: it can't produce a firmware binary that isn't on the disk. Don't expect a model to invent the missing V6 system FW.
- On the write-protect clearing direction the assistant's safety layer stopped later attempts, and I didn't push it. The early attempts happened before that.
- Check its claims. A few of my notes had to be corrected after the fact (see the "denetim" file in `notlar/`). Anything marked as hypothesis in the notes really is one.

## A boundary, stated up front

I am **no longer** trying to find a way around the controller's own write-protect check. That
assert-driven write-protect is a deliberate safety mechanism responding to a genuine, confirmed
hardware fault on one die — not a bug to route around. Everything in this repo is about getting
the *legitimate* vendor recovery tool to do a real, correct recovery (exclude the bad die
properly, write genuine vendor firmware, let the drive boot clean) — not about defeating the
protection that's currently keeping a partially-faulty drive from making things worse.

I mention this explicitly because some of the files below document *ruling out* a
write-protect-removal approach early in the process, including why it wouldn't actually solve
anything (the underlying die fault would just regenerate the condition). Some other files from
that same early phase went further than I'm comfortable publishing — concrete, actionable
procedures and byte-level patches for defeating the write-protect latch directly. Those are
**not included here**, regardless of how they turned out. This isn't a legal disclaimer, it's

### What was tried, in general terms (so nobody has to rediscover this)

So the "ruling out" above isn't just an assertion, here's the actual shape of it, with enough
detail to be useful and not enough to be a recipe:

- The controller tracks an internal fault counter that increments when the firmware hits a
  write/verify error during its own housekeeping (not host I/O). Past a threshold, a flag in a
  config structure flips, and that flag is what the firmware checks before allowing host writes.
  Both the counter and the flag live in NAND, in the controller's own system-data region.
- In principle, both are reachable and individually resettable through the same hardware debug
  tunnel this whole project uses for legitimate diagnosis — reading them is how the root cause
  got confirmed in the first place.
- It doesn't durably work, for a structural reason, not a tooling limitation: the fault
  counter exists because the firmware's own housekeeping keeps failing against the physically
  bad die on every boot. Clearing the counter, or clearing the flag it drives, doesn't touch
  that underlying cause — the next boot cycle just fails the same housekeeping operation again
  and re-trips the same mechanism. In the one case where this was tried far enough to observe
  the result, the drive got *worse* (failed to boot cleanly at all) rather than better.
- The only way anyone got a MAXIO MAP1202-family drive back to a genuinely stable, writable
  state (per every account I could find, including this one) is excluding the bad die from
  the active capacity *before* the drive boots normally — i.e. the legitimate path this repo
  documents — not clearing the fault record after the fact.

If you came here because you're facing the same assert/write-protect pattern on a MAXIO
controller: this is why I'd point you at die-exclusion rather than fault-clearing. Exact
register addresses and patch bytes aren't published here on purpose, for the reasons above the
line — but if you're doing serious, careful work on your own hardware and that's genuinely the
piece you're missing, open an issue and we can talk about it directly rather than as a public
how-to.
the actual line I've held through the whole process, and a few spots in the files that *are*
published had a sentence or a table row redacted for the same reason (marked inline where it
happened).

## Where to start reading

- **`BASLA_BURADAN.md`** ("start here") — the single pointer file I keep up to date with
  whatever's most current; everything else is reached from its top few lines.
- **`DEVAM_2026-10-10_v3.md`** — the detailed, timestamped running log for the most recent
  stretch of work (this is the file with the real blow-by-blow: what was tried, what broke,
  what the evidence showed). Long, raw, written for continuity across sessions rather than for
  readability — but it's the ground truth.
- **`SABAH_OZET_2026-10-11.md`** — a shorter synthesis of where things stood partway through.
- **`RAPOR.md`** — the original diagnostic report from the very first night, in a more
  narrative style; good for the "how did you even figure out the root cause" story.
- **`re/`** — the reverse-engineering notes: controller/firmware analysis, the DieReMap
  die-exclusion mechanism (`ANALIZ_DIEREMAP.md`), capacity-threshold math, DPD/geometry
  structure, etc.
- **`notlar/`** — research notes, including a long, independently-verified trail on where the
  correct SK hynix V6 MAP1202 firmware package is known to exist and why I still can't get it
  (`hyv6.md` and siblings) — this is the most directly relevant thing if you want to help with
  the current blocker.

Everything is written in Turkish (that's the language I think in for this), except this README.
Happy to translate/clarify specific parts on request.

## Why some files aren't here

The working directory this came from is much bigger than this repo. Left out, deliberately:

- **MAXIO's own tools and firmware files** (MXMPTool itself, NAND microcode/firmware binaries,
  flash-definition databases). Not mine to redistribute.
- **Raw forensic captures** (USB traffic dumps, full NAND block dumps, VM disk images) — large,
  not independently useful without the proprietary tooling above, and not needed to follow the
  story; relevant excerpts are already quoted inline in the analysis files.
- **My own Python tooling for direct NAND access over the hardware debug tunnel** (raw block
  read/write/erase against this exact controller, used for low-level diagnosis). Some of it is
  read-only and harmless on its own, but it all shares a common library that also provides raw
  erase/write and code-injection against the controller — publishing any of it would effectively
  hand over a working low-level access toolkit for this exact chip, and I'd rather describe
  what I found than publish the means to reproduce it on someone else's drive without having
  thought about it as carefully as I have about my own.
- **A handful of analysis files, and a few redacted lines inside otherwise-published files**,
  specifically where the content was a concrete, actionable procedure for clearing the
  controller's write-protect/assert mechanism directly (as opposed to the *legitimate*
  die-exclusion path, which is published in full). See the boundary note above.

If you're a recovery professional, a MAXIO engineer, or genuinely need more detail than this to
help, open an issue or reach out — I'm not trying to be cagey, I just didn't want "ask for help
recovering my own drive" to double as "here's a write-protect bypass guide for this controller."

## Status

Still stuck on the system-firmware boot step. If you know MAXIO MAP1202, SK hynix V6 NAND, or
have ideas about the "Jump to system fail" failure mode specifically, I'd genuinely appreciate
hearing from you.
