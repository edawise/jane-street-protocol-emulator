# Requirements Guide — What Each Item Actually Means

> Plain-English explanation of everything in the ReqSpec: the 48 requirements
> (`REQ-*`) — 35 architecture-neutral and 13 architecture-scoped — the 5 ambiguities
> (`AMB-*`), and the 27 architectural decisions (`ARCH-PEX-*`) belonging to candidate 001 in
> [`../architectures/candidate_001/decisions.yaml`](../architectures/candidate_001/decisions.yaml).
>
> Companions: [`PROVENANCE_AUDIT.md`](./PROVENANCE_AUDIT.md) (where each fact comes from)
> and [`tools/select_contract.py`](./tools/select_contract.py) (the frozen-contract filter).

---

## 0. How to read a requirement

Every `REQ-*` carries four tags that tell you how to treat it:

| Tag | Values | Meaning |
|---|---|---|
| `arch_scope` | `independent` / `constrained` / `architecture-scoped` / `candidate-specific` | Can this be tested without knowing the microarchitecture? |
| `obligation` | `external` / `internal` | Who imposes it: the brief/standard/harness, or us? Independent of `priority`. |
| `priority` | `MUST` / `SHOULD` / `MAY` | Is it a **requirement** (binding) or a **goal** (elective)? |
| `status` | `CONFIRMED` / `ASSUMED` / `AMBIGUOUS` | Is it pinned by an external source, or assumed? |
| `source_provenance` | `js-brief` / `tt-template` / `external-standard` / `specialist-spec` / `engineered` | Where the content came from |

…plus a `verification` block naming the test, checker, and reference model.

**The frozen contract** (what the architecture-independent reference model and the
one-time generic testbench must cover) is:

```
arch_scope ∈ {independent, constrained}  AND  obligation = external   →  22 requirements
```

Everything else is real work, but it is verified elsewhere so the testbench never changes.

**Reading order below:** Part 1 = the frozen contract. Part 2 = in scope but non-gating.
Part 3 = architecture-scoped. Parts 4–5 = ambiguities and the PEX architecture.

---

# Part 1 — The frozen verification contract (22 requirements)

## 1.1 The core idea

### REQ-FUNC-007 — It must be firmware, not fixed logic
* **What:** All protocol framing, state, and bit sequencing live in reloadable firmware in
  volatile program memory. There must be **no** hard-wired UART/SPI/I2C controller blocks
  in the RTL.
* **Why:** This *is* the competition. The brief says the goal "isn't to put a UART block, an
  SPI block, and an I2C block on one die and call it done" and that the chip must be
  "reprogrammable enough to support new protocols *after* fabrication."
* **How checked:** `TEST-PROG-001` — the *same unmodified RTL* must implement two different
  protocols purely by swapping firmware; plus a structural check that no dedicated
  peripheral controller exists in the synthesised netlist. This is the single most
  important requirement in the repo.

## 1.2 Protocol coverage

The brief only says "Start with UART, SPI, and I2C." Everything below defines what those
words *mean*; the parameters are governed by published standards, not by the blog.

### REQ-FUNC-001 — UART transmit
* **What:** Serialise bytes into UART frames on any output/bidirectional pin: start bit,
  5–8 data bits LSB-first, optional even/odd parity, 1–2 stop bits, configurable bit period.
* **Why:** Brief names UART; framing conventions come from ITU-T V.24 / EIA-232-F / the
  16550 UART model.
* **How checked:** `TEST-UART-001` against `uart_tx_reference_model`; validated at 9600 →
  115200 baud, start bit within 1 cycle, ≤1.0% bit-period error.

### REQ-FUNC-002 — UART receive
* **What:** Detect the start-bit falling edge, sample each bit near its midpoint, verify
  parity and stop bits, present the byte, and flag framing/parity errors.
* **Why:** "UART" is a receiver-transmitter pair by definition (ITU-T V.24 / the 16550
  model), so the brief's "start with UART" covers both directions; "get a UART transmitter
  out of a pin" is the *first* milestone, not the whole requirement.
* **How checked:** `TEST-UART-002`; sampling point 50% ±10%, ±2.5% baud tolerance, injected
  bad stop/parity bits must raise the right error flags.

### REQ-FUNC-003 — SPI master, all four modes
* **What:** Generate SCLK and CS_N, drive MOSI, sample MISO — across CPOL 0/1 × CPHA 0/1,
  8- and 16-bit frames, MSB- and LSB-first.
* **Why:** Brief names SPI; the mode semantics are the Motorola SPI Block Guide.
* **How checked:** `TEST-SPI-001` asserts the exact drive/sample edge for each of modes 0–3
  plus CS setup/hold ≥ 0.5 SCLK period.

### REQ-FUNC-005 — I2C master
* **What:** Act as I2C bus master: START, repeated START, STOP, address/RW, 9th-cycle
  ACK/NACK sampling, byte transfer.
* **Why:** Brief names I2C; semantics per NXP UM10204.
* **How checked:** `TEST-I2C-001` — SDA may only change while SCL is low (except START/STOP),
  ACK/NACK must be latched correctly, transactions checked against a slave memory model.

### REQ-FUNC-006 — Open-drain emulation and clock stretching
* **What:** Never drive high. Emulate open-drain by driving 0 with OE=1, and releasing to
  high-impedance with OE=0 so an external pull-up pulls the line up. Pause when a slave
  holds SCL low (clock stretching), with a timeout.
* **Why:** The Tiny Tapeout pads are push-pull. Driving high during a slave's ACK or stretch
  would cause a crowbar current. This is the resolution of `AMB-001`.
* **How checked:** `TEST-I2C-002` — an assertion that `uio_out` and `uio_oe` are never
  simultaneously 1 on I2C/1-Wire pins; stretching up to 100 SCL periods must not lock up.

### REQ-PERF-001 — UART rate coverage and accuracy
* **What:** Generate and receive at the standard rates 9600/19200/38400/57600/115200 with
  bit-period error better than 1.0% (≈434 cycles per bit at 115200 on a 50 MHz clock).
* **Why:** Promoted to the external contract because standard baud rates are defined by the
  serial standard — "support UART" is undefined without them.
* **How checked:** `TEST-PERF-001` — measure the bit cell (8.68 µs ±20 ns) and push 256 bytes
  back-to-back with zero errors.

### REQ-PERF-003 — I2C timing compliance
* **What:** Meet Standard-mode (100 kHz) and Fast-mode (400 kHz) SCL timing including the
  minimum high/low intervals (4.0/4.7 µs and 0.6/1.3 µs).
* **Why:** NXP UM10204 is normative here; a bus that is "roughly 400 kHz" will fail real
  slaves.
* **How checked:** `TEST-PERF-003` against the UM10204 tables, including SDA setup/hold.

## 1.3 Determinism

### REQ-TIME-001 — Cycle-exact, jitter-free execution
* **What:** Every operation has a fixed, documented integer cycle cost. No pipeline hazards,
  no speculation, no caches. Identical program + inputs ⇒ bit-identical pin waveforms in
  simulation, on FPGA, and in silicon.
* **Why:** Bit-banging only works if you know exactly how long each thing takes. This is the
  requirement that justifies the whole "tiny CPU with an instruction set designed for
  counting cycles" framing in the brief.
* **How checked:** `TEST-TIME-001` — compare cycle numbers of every pin transition across
  RTL sim, gate-level sim, and silicon; assert no branch prediction/caches exist.

## 1.4 Harness interface (fixed by Tiny Tapeout, not by the brief)

These are `constrained`: the microarchitecture is free, but the pad ring is not.

### REQ-IF-001 — Exactly 24 I/O pins
* **What:** 8 dedicated inputs (`ui_in[7:0]`), 8 dedicated outputs (`uo_out[7:0]`), 8
  bidirectional (`uio[7:0]`), presented internally as one logical GPIO bus (GPIO 0–23).
* **Why:** Fixed by the Tiny Tapeout `tt_um_*` top-module interface.
* **How checked:** `TEST-GPIO-001` — port declaration matches the template; sampling and
  driving a pin is observable on the corresponding GPIO bit.

### REQ-IF-002 — Software-controlled tri-state on `uio`
* **What:** Firmware controls both the value (`uio_out`) and the output enable (`uio_oe`) for
  all 8 bidirectional pins, switching within one clock cycle.
* **Why:** This is the mechanism that makes open-drain emulation and bus turnaround possible
  at all.
* **How checked:** `TEST-GPIO-002` — deasserting OE floats the pin within 1 cycle and readback
  reflects the true external level.

### REQ-IF-004 — Safe default pin state
* **What:** Unused dedicated outputs are driven low; unused bidirectional pins keep their
  output enables deasserted (high-Z).
* **Why:** Floating CMOS inputs cause shoot-through current and spurious oscillation. The
  template says "All output pins must be assigned. If not used, assign to 0."
* **How checked:** `TEST-GPIO-004` — immediately after reset, `uo_out == 0` and `uio_oe == 0`.

### REQ-IF-005 — Single 50 MHz clock domain
* **What:** All logic — datapath, counters, memory, baud generators — runs on the one external
  `clk`, nominally 50 MHz (20.0 ns).
* **Why:** 50 MHz comes from the linked template (`"CLOCK_PERIOD": 20` → 50 MHz) and the TT
  FAQ ("top clock speed? At least 50MHz"). The blog never states a frequency.
* **How checked:** `TEST-CLK-001` — STA closes at 50 MHz and no core CDC synchronisers are
  needed.

### REQ-IF-006 — Async-assert, sync-deassert reset
* **What:** `rst_n` low forces all registers to their reset state immediately; releasing it
  passes through a 2-stage synchroniser so no register sees a metastable recovery.
* **Why:** Standard robust reset practice on the harness's `nreset (low to reset)` signal.
* **How checked:** `TEST-CLK-002` — state clears within 5 ns regardless of clock activity;
  no setup/hold recovery violations; a clean entry into the boot state.

## 1.5 Physical / foundry

### REQ-PHYS-001 — IHP 130 nm CMOS5L, open flow, no proprietary IP
* **What:** Synthesise to GDS-II on IHP's 130 nm CMOS5L PDK through the LibreLane/Tiny
  Tapeout flow with zero proprietary or NDA-encumbered blocks.
* **Why:** The brief's Process rule.
* **How checked:** `TEST-PHYS-001` — clean DRC against CMOS5L rules, clean LVS, no encrypted IP.

### REQ-PHYS-002 — Fit in 6×4 tiles
* **What:** Baseline 6×4 = 24 tiles (~0.72 mm², ~24,000 cells nominal), with post-synthesis
  standard cells capped at 18,000 (75%) so clock-tree and routing have headroom. 8×4 (32
  tiles, 24,000-cell target) only if the organisers confirm the scale-up.
* **Why:** The brief's Area rule. The 75% figure is *our* margin; the brief only says "leave
  room for clock-tree buffers and routing."
* **How checked:** `TEST-PHYS-002` — cell-count report ≤18,000 and detailed routing with 0
  shorts/opens. This is the gate most likely to kill a candidate, so it is checked early
  (see `ARCH-PEX-024`).

### REQ-PHYS-003 — Instruction memory must fit
* **What:** The program-memory subsystem (SRAM macro, latch array, or ROM/RAM hybrid) must
  not crowd out the datapath, routing, or buffers.
* **Why:** The brief notes "SRAM can be more area-efficient than flip-flops" and links a
  working SRAM example on this process node.
* **How checked:** `TEST-PHYS-003` — macro + core footprint fits the tile boundary and
  supports single-cycle fetch at 50 MHz.

### REQ-PHYS-004 — Timing closure at 50 MHz across PVT
* **What:** Setup and hold both have non-negative worst negative slack at the slow and fast
  corners, including clock-tree insertion and pad delays.
* **Why:** `CLOCK_PERIOD = 20.0 ns` from the linked template.
* **How checked:** `TEST-PHYS-004` — OpenSTA WNS ≥ 0 and no max-transition/capacitance
  violations on clock nets.

### REQ-PHYS-005 — Open-source submission
* **What:** RTL, verification environment, reference firmware, and build flow are all
  publicly released under a license permitting reuse and derivative works.
* **Why:** The brief's Open source rule ("so others can use and build on it"). Distinct from
  `REQ-PHYS-001`, which is about the *PDK*, not our *deliverables*.
* **How checked:** `TEST-PHYS-005` — license review; the template example is Apache-2.0.

## 1.6 Stretch protocols

### REQ-OPT-001 — Low-Speed USB (1.5 Mbit/s)
* **What:** Bit-level USB LS signalling: NRZI encode/decode, bit-stuffing after six 1s, Sync
  (0x80), EOP (SE0 then J). ≈33 cycles per bit at 50 MHz.
* **Why:** The brief's explicit stretch goal.
* **How checked:** `TEST-OPT-001` — NRZI/bit-stuffed waveform matches the USB 2.0 LS physical
  spec; EOP is driven correctly.

### REQ-OPT-002 — 10BASE-T Ethernet (10 Mbit/s)
* **What:** Manchester-encoded bit-level signalling — preamble and Start Frame Delimiter.
* **Why:** The brief's other explicit stretch goal.
* **How checked:** `TEST-OPT-002` — mid-bit transitions on every cell; a 10BASE-T receiver
  model decodes the preamble. **Bit-level only** — see `AMB-003`.

## 1.7 Verification deliverable

### REQ-VERIF-002 — Constrained-random + formal verification
* **What:** The verification suite must include SystemVerilog assertions/formal proof and
  constrained-random generation, stressing FIFO full/empty boundaries, rapid pin turnaround,
  illegal opcodes, and reset during transmission. Target ≥95% functional coverage on edge
  cases.
* **Why:** The brief says it is "excited to see … formal methods, random constrained tests,
  AI-assisted verification" and that verification "will be an extremely important aspect of
  the ASIC design flow."
* **How checked:** `TEST-VERIF-002` — runs under open tools (cocotb/Verilator); formal proof
  of no FIFO corruption or crossbar deadlock.

---

# Part 2 — In scope, but internally imposed (`obligation: internal`, 13 items)

These are architecture-neutral and *could* be tested by the generic environment, but nobody
externally requires them. They split into **requirements** (MUST — the design is bound to
meet them, and a decision must realise them) and **goals** (SHOULD/MAY — elective targets a
candidate may pursue or drop). All are `ASSUMED`.

* **Requirements (MUST):** `REQ-IF-003`, `REQ-TIME-002`, `REQ-TIME-003`, `REQ-PHYS-006`.
* **Goals (SHOULD/MAY):** `REQ-FUNC-004`, `REQ-PERF-002`, `REQ-OPT-003…008`, `REQ-VERIF-001`.

### REQ-FUNC-004 — SPI slave mode
* **What:** Accept an external CS_N and SCLK, shift MISO out and sample MOSI, honouring
  programmed CPOL/CPHA.
* **Why:** Not in the brief; added because a protocol emulator that can only be a master
  cannot impersonate a device under test.
* **How checked:** `TEST-SPI-002` — MISO tri-stated while CS_N high; full-duplex loopback at
  an engineered ≤10 MHz target.

### REQ-IF-003 — Pins are assignable from firmware
* **What:** A protocol signal can be moved to a different physical GPIO purely by
  configuration, with no RTL edit or re-synthesis.
* **Why:** Follows from the brief's requirement to support new protocols "within its timing
  and I/O constraints" after fabrication. The *mechanism* (e.g. a 16-to-24 crossbar) is left
  to the architecture — see `ARCH-PEX-003`.
* **How checked:** `TEST-GPIO-003` — remap SCLK/TX to GPIO 8, 9, or 16 by configuration only.

### REQ-TIME-002 — Zero cumulative drift
* **What:** Over a long transmission, edges stay locked to the nominal baud/clock grid. A
  1000-byte 115200 UART frame consumes exactly the theoretical integer cycle count; a 50%
  duty square wave never drifts phase.
* **Why:** Rounding errors in a delay engine accumulate; at byte 900 the receiver is sampling
  the wrong place. Stronger than `REQ-TIME-001`, which only demands fixed *per-operation* cost.
* **How checked:** `TEST-TIME-002` — drift/jitter checker over long frames.

### REQ-TIME-003 — A free-running cycle counter
* **What:** A monotonic counter increments once per system clock, readable by firmware and
  host, and must not pause during stalls or prescaling. Its width is an architecture
  decision (it just must not roll over within one transaction).
* **Why:** The brief's "instruction set designed for … counting cycles"; you need a time base
  for absolute scheduling, profiling, and pulse-width measurement.
* **How checked:** `TEST-TIME-003` — increments by exactly 1 per edge, never pauses, reads
  atomically.

### REQ-PERF-002 — SPI clock up to 25 MHz
* **What:** SCLK from ~100 kHz up to an engineered 25 MHz target at 50% duty.
* **Why:** Explicitly a self-imposed stretch — 25 MHz is the Nyquist limit of a 50 MHz clock
  (1 cycle high, 1 low). The only external obligation is that the SPI clock is *configurable*
  (`REQ-FUNC-003`).
* **How checked:** `TEST-PERF-002` — 40.0 ns period exactly; data changes on the correct edge
  for the mode; setup/hold respected.

### REQ-OPT-003 — CAN bus
* **What:** Up to 1 Mbit/s: dominant/recessive generation, bit-stuffing, and sampling the bus
  while transmitting to detect arbitration loss.
* **Why:** Named in the brief's "other interesting protocols to consider" list, which is
  non-normative, so this is a self-imposed optional target.
* **How checked:** `TEST-OPT-003` — dominant overrides recessive; losing arbitration halts
  transmission without corrupting the bus.

### REQ-OPT-005 — JTAG / SWD
* **What:** Bit-bang the 16-state JTAG TAP (TMS/TCK/TDI/TDO) and/or SWD (SWCLK/SWDIO).
* **Why:** Named in the brief only as a protocol "to consider", so this is self-imposed.
* **How checked:** `TEST-OPT-005` — TAP walks Reset→Idle→DR-Scan→IR-Scan; reads a 32-bit
  IDCODE from a TAP model at ≤10 MHz TCK.

### REQ-OPT-004 — 1-Wire / WS2812
* **What:** Microsecond and sub-microsecond pulse shaping (WS2812 T0H/T0L/T1H/T1L; 1-Wire
  reset and time slots).
* **Why:** **Self-imposed.** The brief lists JTAG, SWD, PS/2, and CAN — not these. Kept
  because they are excellent stress tests of the delay engine.
* **How checked:** `TEST-OPT-004` — pulse widths within ±150 ns of the WS2812 table.

### REQ-OPT-006 — Bus sniffing and fault injection
* **What:** One routine passively samples a bus and timestamps transactions into the host
  buffer while another injects programmable glitches or parity/ACK errors.
* **Why:** From the brief's non-normative "show us anything else your architecture makes
  possible." A differentiator, not an obligation — and it presupposes concurrency
  (`REQ-FUNC-008`).
* **How checked:** `TEST-OPT-006` — sniffer captures all transitions with timestamps; injector
  produces a 20 ns single-cycle glitch on command.

### REQ-OPT-007 — At least one extra protocol
* **What:** Demonstrate one protocol beyond UART/SPI/I2C, out of JTAG, SWD, PS/2, CAN,
  1-Wire, or another bit-banged bus.
* **Why:** **Self-imposed.** The brief only says "to consider". Satisfied by discharging any
  one of `REQ-OPT-003`, `REQ-OPT-004`, or `REQ-OPT-005`.
* **How checked:** `TEST-OPT-007` — one extra protocol demonstrated end-to-end.

### REQ-OPT-008 — USB/Ethernet *plus* another protocol
* **What:** Demonstrate Low-Speed USB and/or 10BASE-T bit-level framing **and** at least one
  of JTAG/SWD/PS/2/CAN/1-Wire.
* **Why:** The USB/Ethernet half is genuinely from the brief; the "plus at least one other"
  conjunction is self-imposed.
* **How checked:** `TEST-OPT-008` — scope checker; bit-level-only scope is permitted for
  Ethernet/USB per `AMB-003`.

### REQ-VERIF-001 — Cycle-accurate ISS and reference model
* **What:** A software instruction-set simulator and behavioural model that reproduces pin
  transitions, stalls, and register state bit- and cycle-identically to the RTL, usable as a
  differential-verification golden reference.
* **Why:** The brief calls verification critical for AI-assisted design; the specific
  deliverable is ours. This is the mechanism that makes differential verification possible.
* **How checked:** `TEST-VERIF-001` — zero mismatches between ISS and RTL for identical
  program and stimulus; the model must be independent of the RTL codebase.

### REQ-PHYS-006 — 75% cell-count margin
* **What:** Post-synthesis mapped cells must stay at or below 18,000 (75% of the ~24,000-cell
  6×4 budget) so clock-tree buffers and routing keep headroom; 24,000 if 8×4 is confirmed.
* **Why:** The brief says "leave room for clock-tree buffers and routing" but sets no number;
  the 75% figure is our own margin, split out of the external `REQ-PHYS-002`.
* **How checked:** `TEST-PHYS-006` — post-synthesis cell-count report ≤18,000 for the 6×4
  baseline.

---

# Part 3 — Architecture-scoped requirements (13, excluded from the frozen testbench)

These constrain **our** design but are not architecture-neutral: a different architecture
could satisfy the brief without them. So they are excluded from the frozen contract and
verified at the architecture level instead.

Most are **capability** requirements — our design must have at least two concurrent channels,
hardware buffering, a host link, delay primitives. That is why they are tagged
`architecture-scoped` rather than `candidate-specific`: they are portable across candidates of
the intended class, and they stay in the spec tree at
[`architecture/REQ_ARCH_scoped.yaml`](./architecture/REQ_ARCH_scoped.yaml). Each keeps its
`REQ-*` ID, acceptance criteria, and test ID. The link to a candidate is recorded only on the
candidate side — each decision in `../architectures/<candidate>/decisions.yaml` lists the
requirements it satisfies in `satisfies_reqs` — so nothing here names a candidate. The
validator reads the candidate tree and checks that no architecture-scoped requirement is
orphaned.

The candidate's answers — the actual mechanisms — live in
[`../architectures/candidate_001/decisions.yaml`](../architectures/candidate_001/decisions.yaml)
and are documented in Part 5.

**Why the separation matters:** a frozen testbench must not assert that a design has a serial
bootloader on GPIO 0/8, or four lanes, or a 5-bit delay field. Those are candidate 001's
answers. Replacing it changes the decisions, and may retire a requirement whose ambition we
drop, but nothing in Part 1 or Part 2 moves.

### REQ-FUNC-008 — ≥2 concurrent hardware channels
* **What:** Run at least two protocols simultaneously on non-overlapping pins with zero
  cross-channel jitter.
* **Why:** Realised by `ARCH-PEX-001` (4 lanes). A single-lane design could not satisfy it, so
  it is not architecture-neutral. Grounded loosely in the brief's RP2040 PIO / TI PRU
  inspiration, which the brief does not link or quantify.
* **How checked:** `TEST-PROG-002` — UART TX must be bit-identical whether SPI is idle or
  running flat out.

### REQ-FUNC-009 — Channel-to-channel synchronisation
* **What:** Deterministic, low-latency event signalling between concurrent routines (shared
  flags or trigger lines), with 1-cycle propagation, without host involvement.
* **Why:** Needed only if you have concurrent channels; realised by `ARCH-PEX-016`
  (8-line latched-flag IRQ system). Self-imposed.
* **How checked:** `TEST-PROG-003` — a waiting routine resumes exactly 1 cycle after the
  trigger asserts.

### REQ-FUNC-010 — Hardware TX/RX buffering
* **What:** Buffers between the host interface and the protocol engine, so neither side has to
  synchronise at the bit level.
* **Why:** Realised by `ARCH-PEX-004` (per-lane 8×16-bit TX/RX FIFOs). A design with direct
  register access and no FIFOs satisfies the brief too.
* **How checked:** `TEST-BUFF-001` — host can burst-write up to capacity with no drops; the
  engine drains at full line speed; occupancy is reported correctly.

### REQ-FUNC-011 — Lossless stall on empty TX / full RX
* **What:** Attempting to pop an empty TX buffer or push to a full RX buffer freezes execution
  and resumes without losing, corrupting, **or duplicating** the stalled operation.
* **Why:** Realised by `ARCH-PEX-021` and the lane FSM `ARCH-PEX-017`. An architectural
  flow-control policy, not a behavioural contract. (The *no-corruption* intent is universal;
  the *stalling* mechanism is a choice.)
* **How checked:** `TEST-BUFF-002` — PC and pin states freeze; execution resumes cleanly with
  no duplicated effect.

### REQ-FUNC-012 — Configurable watermark thresholds
* **What:** Programmable RX high-watermark and TX low-watermark that raise an event flag.
* **Why:** Realised by `ARCH-PEX-013` (`RXTHR`/`TXTHR` → `FIFO_EV`). Depends on buffering
  (`REQ-FUNC-010`).
* **How checked:** `TEST-BUFF-003` — flag asserts/deasserts exactly at the programmed
  occupancy boundaries.

### REQ-IF-007 — Execution-rate prescaler
* **What:** Divide routine execution by an integer factor (1–65536) while the timestamp
  counter keeps running at full rate.
* **Why:** Realised by `ARCH-PEX-010` (16-bit `CLKDIV` at CSR 0x20). No external source
  requires a prescaler.
* **How checked:** `TEST-CLK-003` — scale 5 runs one operation per 5 cycles; the timestamp
  advances 5 during that operation.

### REQ-IF-008 — In-system firmware load path
* **What:** After reset, receive, verify, and write a firmware image into program memory
  over the host link, without an external JTAG/SWD programmer. Execution is held until a
  complete valid image arrives; corrupt frames abort and return to sync-wait.
* **Why:** Self-imposed, but implied by the brief's "Then make it programmable". The *pins*
  and *framing* the host link uses are **not** part of this requirement — they are candidate
  001's answer, recorded in `ARCH-PEX-011` (GPIO 0/8, 8-N-1, `0xAA` framing, divisor 434).
* **How checked:** `TEST-BOOT-001` — streamed load, no execution from a partial image,
  `boot_done` only on success, corrupt frames rejected.

### REQ-IF-009 — Post-boot host register/streaming link
* **What:** A bidirectional packet protocol letting the host start/halt routines, read status
  and timestamps, service interrupts, and stream payload data without disturbing real-time
  pin execution.
* **Why:** Realised by `ARCH-PEX-006` (10-byte binary packet) and `ARCH-PEX-012` (CSR map).
  Entirely self-imposed.
* **How checked:** `TEST-HOST-001` — register read/write, FIFO streaming, and graceful
  handling of corrupted transactions.

### REQ-IF-010 — Soft reset / firmware reload
* **What:** Reload firmware and restart at any time over the host link (≤4 cycles recovery)
  with no power cycle; volatile program memory survives until overwritten.
* **Why:** Realised by `ARCH-PEX-023` (`CTRL.soft_reset`). Self-imposed convenience, not a
  brief requirement.
* **How checked:** `TEST-BOOT-002` — routines stop, the device returns to bootstrap sync-wait,
  and a new image loads without cycling `rst_n`.

### REQ-IF-011 — Re-purpose the host-link pins after boot
* **What:** After loading, firmware may claim the host-link pins for protocol I/O; the
  register link suspends, and a reset always reclaims them.
* **Why:** Resolves `AMB-002` — with only 8 input-only and 8 output-only pins, a host link
  costs one of each. Which indices are involved is candidate 001's choice (`ARCH-PEX-027`),
  not part of this requirement.
* **How checked:** `TEST-HOST-002` — pin ownership transfers to the lane and is unconditionally
  reclaimed on reset.

### REQ-TIME-004 — Fine delay, 1-cycle resolution
* **What:** Hold pins stable for k cycles, k up to at least 31, at single-cycle resolution,
  with no polling loops.
* **Why:** Candidate 001 satisfies this with `ARCH-PEX-008`, a 5-bit `DELAY[4:0]` field
  carried in every instruction word. The requirement is a floor on capability, not an
  encoding: a wider delay field satisfies it too, so the encoding stays an architecture
  decision.
* **How checked:** `TEST-TIME-004` — a delay step holds pins for exactly k cycles with zero
  jitter.

### REQ-TIME-005 — Coarse delay up to 65,536 cycles
* **What:** A single operational step that stalls from 1 to ≥65,536 cycles, so long idle
  periods need no unrolled loops.
* **Why:** Candidate 001 satisfies this with `ARCH-PEX-009`, opcode `0x9` with an 8-bit
  immediate or the 16-bit X register as the count. As with the fine delay, the operand width
  and instruction form are architecture decisions; the requirement is the 65,536-cycle floor.
* **How checked:** `TEST-TIME-005` — a single step stalls ≥65,536 cycles; PC is frozen until
  the countdown completes.

### REQ-TIME-006 — Event-conditioned stalling (`WAIT`)
* **What:** Block advancement until a hardware condition holds: pin high/low, event flag,
  buffer ready, or `timestamp ≥ target`.
* **Why:** Realised by `ARCH-PEX-025` (TS capture + `WAIT` condition 0x5) and `ARCH-PEX-016`
  (IRQ lines). The *capability* is arguably universal (e.g. I2C clock stretching needs it),
  but the encoding is architectural.
* **How checked:** `TEST-TIME-006` — no advancement and stable pins while waiting; resumes on
  the exact cycle the condition becomes true.

---

# Part 4 — Ambiguities (5)

These record places where the sources are silent, conflicting, or physically awkward. They
are *not* requirements; they are decision records with a resolution and a verification check.

| ID | The problem | Resolution |
|---|---|---|
| **AMB-001** | Tiny Tapeout pads are push-pull, but I2C and 1-Wire need open-drain. Driving high into a slave pulling low causes crowbar current. | **RESOLVED** — emulate open-drain: drive 0 with `uio_oe=1`; release to high-Z with `uio_oe=0`. Firmware must never set `uio_out=1` with `uio_oe=1`. Checked by an assertion. |
| **AMB-002** | The host link consumes GPIO 0 and GPIO 8, but a protocol may want all 8 inputs or all 8 outputs. | **RESOLVED** — host pins stay dedicated during boot; after `boot_done` firmware may claim them, suspending the link; hardware reset always reclaims them. Generic tests default to GPIO 1–7, 9–15, 16–23. |
| **AMB-003** | At 50 MHz, 10BASE-T has only 5 cycles per bit and USB Full-Speed ≈4.17 — no room for CRC-32 or MAC framing in software. | **RESOLVED** — Ethernet and USB Full-Speed are **bit-level framing only**; Low-Speed USB (33 cycles/bit) remains the full-packet target. |
| **AMB-004** | Open-drain rise time depends on external pull-ups and board capacitance; Fast-mode I2C allows only 300 ns. The demo board is unspecified. | **OPEN** — assumed 2.2–4.7 kΩ pull-up and <100 pF, pending organiser clarification. The only unresolved item in the repo. |
| **AMB-005** | The brief says 6×4 tiles; the imported Specialist spec asserted 8×4 / 32K as settled. | **RESOLVED** — the brief wins: 6×4 baseline, ≤18,000 cells, 8×4 conditional only. The stale figures are not used as the budget source. |

---

# Part 5 — Candidate 001's decisions (PEX, 27 decisions)

The `ARCH-PEX-*` entries are **candidate 001**, not requirements. Removing any of them does
not change what is being asked for; it changes *one possible answer*. They live in
[`../architectures/candidate_001/decisions.yaml`](../architectures/candidate_001/decisions.yaml)
and give every architecture-scoped requirement a realised counterpart.

**PEX (Programmable Protocol Emulator eXecutive) in one paragraph:** four independent
single-cycle execution lanes, each running 24-bit microcode from a shared 1024×24-bit SRAM
(256-word bank per lane); each lane has 16 scratch/shift registers, 3 side-set pin bits, an
8-entry TX and RX FIFO, and a 16-bit stall counter, and drives 16 virtual pins mapped through
a crossbar to the 24 real GPIOs; a mask-ROM UART loader fills the SRAM at boot; a 256-byte CSR
space lets the host control lanes and stream data over a 10-byte binary packet.

| Group | Decisions | Note |
|---|---|---|
| Execution | 001 (4 lanes), 007 (non-pipelined), 017 (lane FSM), 019 (X/Y registers) | The core bet: single-cycle, non-pipelined = deterministic by construction |
| ISA | 002 (24-bit word), 008 (5-bit DELAY), 009 (DELAY opcode), 015 (12 opcodes + trap), 025 (TS/WAIT timing) | 12 opcodes: JMP, WAIT, IN, OUT, PUSH, PULL, MOV, IRQ, SET, DELAY, TS, HALT |
| Pins | 003 (16→24 crossbar), 014 (static lane priority), 020 (per-lane OE mask) | Crossbar decouples firmware from pad assignment |
| Memory | 005 (1024×24 SRAM, 4 banks), 024 (75% pre-P&R gate) | Directly answers the brief's SRAM hint, bounded by `REQ-PHYS-002` |
| Data flow | 004 (per-lane FIFOs), 013 (watermarks), 021 (stall semantics), 022 (FIFO data port) | Makes streaming lossless without polling |
| Host/boot | 006 (10-byte packet), 011 (ROM loader), 012 (CSR map), 018 (boot FSM), 023 (soft reset), 026 (autostart) | The entire host link, none of which is on the website |
| Timing | 010 (16-bit CLKDIV), 016 (8-line IRQ), 025 (timestamp) | 025 also realises the timestamp and WAIT timing requirements |
| Pin ownership | 027 (host-pin handover) | Owns the GPIO 0/8 handover |

### Every decision, one line each

| ID | Decision | What it commits to |
|---|---|---|
| ARCH-PEX-001 | Quad execution lanes | 4 independent single-cycle lanes (SM0–SM3), each with its own PC, X/Y, OSR/ISR, side-set latch, stall counter |
| ARCH-PEX-002 | 24-bit instruction word | One uniform word packing `DELAY[4:0]`, `SIDE[2:0]`, `OPCODE[3:0]`, `PORT[3:0]`, `IMM[7:0]` |
| ARCH-PEX-003 | Virtual pin crossbar | Each lane has `VPINS[15:0]`; 4-bit config maps each to GPIO 0–23, const 0/1, or an internal flag; identity at reset |
| ARCH-PEX-004 | Per-lane FIFOs | Independent 8-deep × 16-bit TX and RX FIFOs per lane (1,024 flip-flops total) |
| ARCH-PEX-005 | Shared program SRAM | One 1024×24-bit macro, four 256-word banks; each lane's PC defaults into its own bank |
| ARCH-PEX-006 | Host packet protocol | 10-byte frame `0x5A`, TYPE, ADDR, DATA, XSUM for all post-boot CSR and FIFO access |
| ARCH-PEX-007 | Non-pipelined execution | Fetch, decode, ALU, pin update, and write-back all in one `posedge clk` — no hazards to model |
| ARCH-PEX-008 | 5-bit DELAY field | Every instruction can stall 0–31 cycles at no extra program-word cost |
| ARCH-PEX-009 | DELAY opcode | Opcode `0x9` stalls N+1 cycles, N from the 8-bit immediate or the 16-bit X register |
| ARCH-PEX-010 | CLKDIV prescaler | 16-bit `CLKDIV` at CSR 0x20 divides lane execution by `CLKDIV+1` (0 = full speed) |
| ARCH-PEX-011 | ROM bootstrap loader | ~64×24 mask ROM listening at 115200 baud: `0xAA` sync, 16-bit LE length, 3-byte LE words, `0x55` end |
| ARCH-PEX-012 | CSR map | 256-byte, 32-bit-word-granular register space: global 0x00–0x3F, per-lane 0x40–0xBF, reserved 0xC0–0xFF |
| ARCH-PEX-013 | Watermarks | 4-bit `RXTHR`/`TXTHR` in `PCTRL` drive a level-sensitive `FIFO_EV` flag usable as a `WAIT` condition |
| ARCH-PEX-014 | Output contention | If two lanes drive the same GPIO, fixed priority SM0 > SM1 > SM2 > SM3 |
| ARCH-PEX-015 | ISA | 12 opcodes (JMP, WAIT, IN, OUT, PUSH, PULL, MOV, IRQ, SET, DELAY, TS, HALT); `0xC`–`0xF` trap the lane to IDLE |
| ARCH-PEX-016 | IRQ system | Exactly 8 global latched IRQ lines, manipulated by the `IRQ` opcode, sampled only at instruction boundaries |
| ARCH-PEX-017 | Lane FSM | 5 states — RESET, IDLE, RUN, STALL, PAUSED; STALL freezes PC without duplicating instruction effects |
| ARCH-PEX-018 | Boot FSM | 5 states — RESET, BOOT, LOAD, READY, RUN; invalid frames return to BOOT |
| ARCH-PEX-019 | Scratch registers | 16-bit X and Y per lane for counts, shift data, far jumps; host-readable via CSR when paused |
| ARCH-PEX-020 | Output-enable mask | 16-bit `OE_MASK` in `PCTRL` controls pad driving — the mechanism behind open-drain emulation |
| ARCH-PEX-021 | FIFO stall semantics | `PULL` on empty TX or `PUSH` to full RX moves the lane to STALL with no dropped words |
| ARCH-PEX-022 | FIFO data port | Reading `FIFO_DATA` (+0x18) pops RX; writing pushes TX |
| ARCH-PEX-023 | Soft reset | `CTRL.soft_reset` returns to BOOT without clearing SRAM; `PCTRL.RESET` restarts an individual lane |
| ARCH-PEX-024 | Area gate | Synthesis must run before P&R and mapped cells must stay ≤75% of the tile budget |
| ARCH-PEX-025 | Absolute-time scheduling | `TS` captures the 32-bit timestamp into `TS_REG`; `WAIT` condition `0x5` blocks until `timestamp ≥ TS_REG` |
| ARCH-PEX-026 | Boot autostart | `CTRL.autostart` makes the bootloader assert GO on lane 0 upon reaching READY |
| ARCH-PEX-027 | Host-pin handover | GPIO 0/8 are owned by the host UART until `boot_done`; firmware may then claim them as protocol pins, and any reset reclaims them |

**The thing to watch:** decisions 004, 006, 008, 009, 010, 011, 012, 013, 016, 018, 021, 022,
023, 025 are the *realisations* of the Part 3 architecture-scoped requirements. If PEX is
replaced by Candidate 002, all of Part 3 is reconsidered — and nothing in Part 1 or Part 2
needs to move, which is exactly why the frozen contract excludes Part 3.

---

# Part 6 — Quick reference

## Frozen contract (22)

| ID | One line | Test |
|---|---|---|
| REQ-FUNC-001 | UART transmit, 5–8 data bits, parity, 1–2 stop bits | TEST-UART-001 |
| REQ-FUNC-002 | UART receive with midpoint sampling and error flags | TEST-UART-002 |
| REQ-FUNC-003 | SPI master, all four CPOL/CPHA modes | TEST-SPI-001 |
| REQ-FUNC-005 | I2C master: START/STOP/ACK, 7-bit addressing | TEST-I2C-001 |
| REQ-FUNC-006 | I2C open-drain emulation and clock stretching | TEST-I2C-002 |
| REQ-FUNC-007 | All protocols in reloadable firmware; no fixed controllers | TEST-PROG-001 |
| REQ-TIME-001 | Fixed integer cycle costs, zero jitter, bit-identical across sim/FPGA/silicon | TEST-TIME-001 |
| REQ-IF-001 | 24 pins: 8 in, 8 out, 8 bidirectional | TEST-GPIO-001 |
| REQ-IF-002 | Software tri-state control on `uio` | TEST-GPIO-002 |
| REQ-IF-004 | Unused outputs low, unused bidirectional high-Z | TEST-GPIO-004 |
| REQ-IF-005 | Single 50 MHz clock domain | TEST-CLK-001 |
| REQ-IF-006 | Async-assert, sync-deassert reset | TEST-CLK-002 |
| REQ-PERF-001 | 9600–115200 baud within 1.0% | TEST-PERF-001 |
| REQ-PERF-003 | I2C 100 kHz / 400 kHz timing compliance | TEST-PERF-003 |
| REQ-PHYS-001 | IHP 130 nm CMOS5L, open flow, no proprietary IP | TEST-PHYS-001 |
| REQ-PHYS-002 | Fit 6×4 tiles (24K cells nominal) | TEST-PHYS-002 |
| REQ-PHYS-003 | Instruction memory fits the area budget | TEST-PHYS-003 |
| REQ-PHYS-004 | STA closure at 50 MHz across PVT | TEST-PHYS-004 |
| REQ-PHYS-005 | Open-source deliverables | TEST-PHYS-005 |
| REQ-OPT-001 | Low-Speed USB bit-level signalling | TEST-OPT-001 |
| REQ-OPT-002 | 10BASE-T Manchester bit-level signalling | TEST-OPT-002 |
| REQ-VERIF-002 | Constrained-random + formal verification | TEST-VERIF-002 |

## Self-imposed requirements & goals (13)

| ID | One line | Test |
|---|---|---|
| REQ-FUNC-004 | SPI slave mode | TEST-SPI-002 |
| REQ-IF-003 | Firmware-configurable pin assignment | TEST-GPIO-003 |
| REQ-TIME-002 | Zero cumulative drift over long frames | TEST-TIME-002 |
| REQ-TIME-003 | Free-running cycle counter | TEST-TIME-003 |
| REQ-PERF-002 | SPI SCLK up to 25 MHz | TEST-PERF-002 |
| REQ-OPT-003 | CAN up to 1 Mbit/s with arbitration | TEST-OPT-003 |
| REQ-OPT-004 | 1-Wire / WS2812 pulse shaping | TEST-OPT-004 |
| REQ-OPT-005 | JTAG / SWD bit-banging | TEST-OPT-005 |
| REQ-OPT-006 | Bus sniffing and fault injection | TEST-OPT-006 |
| REQ-OPT-007 | At least one extra protocol | TEST-OPT-007 |
| REQ-OPT-008 | USB/Ethernet plus another protocol | TEST-OPT-008 |
| REQ-VERIF-001 | Cycle-accurate ISS + reference model | TEST-VERIF-001 |
| REQ-PHYS-006 | ≤18,000 cells (75% margin) | TEST-PHYS-006 |

## Architecture-scoped requirements (13)

| ID | One line | Test |
|---|---|---|
| REQ-FUNC-008 | ≥2 concurrent non-interfering channels | TEST-PROG-002 |
| REQ-FUNC-009 | Channel-to-channel synchronisation | TEST-PROG-003 |
| REQ-FUNC-010 | Host↔engine data buffering | TEST-BUFF-001 |
| REQ-FUNC-011 | Lossless stall on empty TX / full RX | TEST-BUFF-002 |
| REQ-FUNC-012 | Configurable watermark thresholds | TEST-BUFF-003 |
| REQ-IF-007 | Execution-rate prescaler | TEST-CLK-003 |
| REQ-IF-008 | Serial bootstrap loader on GPIO 0/8 | TEST-BOOT-001 |
| REQ-IF-009 | Post-boot host register/streaming link | TEST-HOST-001 |
| REQ-IF-010 | Soft reset and firmware reload | TEST-BOOT-002 |
| REQ-IF-011 | Repurpose host pins after boot | TEST-HOST-002 || REQ-TIME-004 | Fine delay, 0–31 cycles, 1-cycle resolution | TEST-TIME-004 |
| REQ-TIME-005 | Coarse delay up to 65,536 cycles | TEST-TIME-005 |
| REQ-TIME-006 | Event-conditioned stalling (`WAIT`) | TEST-TIME-006 |
