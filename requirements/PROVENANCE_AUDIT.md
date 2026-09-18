# Requirement Provenance Audit

> **Purpose:** For every requirement (`REQ-*`) and ambiguity (`AMB-*`), record **where the
> information actually comes from** on the competition website or the pages it links to.
>
> **Primary source:** <https://blog.janestreet.com/protocol-emulator-asic-competition/>
> (Jane Street blog, "Announcing the protocol emulator ASIC competition", Sep 10 2026).
>
> **Method:** The blog post was retrieved verbatim and every outbound link was followed. Each
> requirement was classified against the retrieved text.

---

## 1. Source inventory

### 1.1 The blog post itself (`S1`)

| Anchor | Content that bears on requirements |
|---|---|
| `#the-challenge` | open-source general-purpose protocol emulator ASIC; bit-banging; "a tiny CPU with an instruction set designed for reading pins, writing pins, counting cycles, and hitting timing precisely"; firmware-not-fixed-logic; post-fabrication reprogrammability; RP2040 PIO / TI PRU inspiration; protocol list; FPGA testing; verification & AI-assisted design |
| `#the-rules` | Process (IHP 130 nm CMOS5L, Tiny Tapeout, `cmos5l` template, tile size 6x4); Area (6x4 max, possible 8x4); Open source; Teams; Deadline (Jan 18 2027); Prize (Mar 2027 shuttle) |
| `#how-much-fits` | 6x4 = 24 tiles; ~200 µm × 150 µm/tile ≈ 0.7 mm²; ~1K logic cells/tile; SRAM more area-efficient than flops; run synthesis early |
| `#getting-started` | "get a UART transmitter out of a pin"; sign-up form |

**Verified absent from the blog post:** any mention of a clock frequency, pin counts, baud
rates, SPI modes, I2C speeds, open-drain pads, FIFOs, interrupts, CSRs, crossbars, instruction
sets, execution lanes, timestamp counters, bootloaders, or host links. **Every such detail in
this ReqSpec is sourced elsewhere (or nowhere).**

### 1.2 Pages linked from the blog (`S2`–`S4`)

| ID | Link | Requirement-bearing content |
|---|---|---|
| `S2` | tinytapeout.com FAQ | "8 ins, 8 outs, 8 bidirectional IOs" + "clock and nreset (low to reset)"; "top clock speed? At least 50MHz" |
| `S3` | `ttihp-verilog-template` (`cmos5l` branch) | `tt_um_*` port list (`ui_in[7:0]`, `uo_out[7:0]`, `uio_in/out/oe[7:0]`, `ena`, `clk`, `rst_n`); `"CLOCK_PERIOD": 20` → 50 MHz; Apache-2.0; "All output pins must be assigned. If not used, assign to 0." |
| `S4` | tinytapeout.com SRAM example | 1024×8 SRAM on this process node |

---

## 2. Classification legend

| Verdict | Meaning |
|---|---|
| **DIRECT** | The substance of the requirement is stated on the website or a linked page |
| **PARTIAL** | The *subject* is named on the website, but the specific parameter/behaviour is not |
| **NONE** | No basis on the website or any linked page (internal spec, engineered target, or external standard) |

> `obligation` (external/internal) is a **separate axis** from this verdict. A requirement can
> be `DIRECT` on the website yet only *suggested* there (e.g. the "to consider" protocol list),
> so its obligation is tagged `internal`. Conversely a requirement with `NONE` website basis can
> still be `external` when a published standard governs it (e.g. UART baud rates, I2C timing).

---

## 3. Summary

| Verdict | Count (of 48 `REQ-*`) | Requirement IDs |
|---|---|---|
| **DIRECT** | 16 | FUNC-007; IF-001, IF-002, IF-004, IF-005, IF-006; OPT-001, OPT-002, OPT-003, OPT-005; PHYS-001…005; VERIF-002 |
| **PARTIAL** | 12 | FUNC-001, FUNC-002, FUNC-003, FUNC-005, FUNC-006; IF-003; OPT-006, OPT-007, OPT-008; TIME-001, TIME-003; VERIF-001 |
| **NONE** | 20 | FUNC-004, FUNC-008…012; IF-007…011; OPT-004; PERF-001, PERF-002, PERF-003; TIME-002, TIME-004…006; PHYS-006 |

**Bottom line:** only the brief's hard rules (firmware-not-logic, IHP 130 nm CMOS5L, 6×4 area,
open source) plus the harness interface are directly mandated. Everything else is either
standards-derived (testable, kept external) or self-imposed (kept internal).

---

## 4. Notable provenance findings

1. **All protocol parameters** (baud rates, SPI CPOL/CPHA, I2C 100k/400k, open-drain, clock
   stretching) are absent from the blog; they come from published standards (ITU-T V.24,
   NS16550A, Motorola SPI, NXP UM10204). They are kept `external` because a testbench cannot
   judge "UART/SPI/I2C" without a concrete definition.
2. **UART RX (`REQ-FUNC-002`)** is derived, not stated verbatim: the brief says "start with
   UART" and names a transmitter as the first milestone, but UART is a receiver-transmitter
   pair by definition, so RX is kept `external` (sourced from ITU-T V.24 / NS16550A).
3. **CAN (`REQ-OPT-003`) and JTAG/SWD (`REQ-OPT-005`)** are named only in the non-normative
   "other interesting protocols to consider" list. Tagged `internal`. Low-speed USB and
   10BASE-T Ethernet are genuine "stretch goals" and stay `external`.
4. **50 MHz** is not in the blog; it comes from the linked template (`CLOCK_PERIOD: 20`) and
   the TT FAQ ("at least 50MHz"). Tagged `constrained` (harness-fixed).
5. **The 18,000-cell / 75% margin** is self-imposed; the blog only says "leave room for
   clock-tree buffers and routing". Split out as `REQ-PHYS-006` (`internal`), leaving
   `REQ-PHYS-002` as the external 6×4 tile mandate.
6. **Determinism (`REQ-TIME-001`)** is brief-grounded only in "hitting timing precisely"; the
   "no caches/speculation" clause was an architectural leak and has been moved to the
   candidate decision `ARCH-PEX-007`.

---

## 5. Ambiguities

| ID | Title | Verdict | Basis |
|---|---|---|---|
| AMB-001 | Open-drain on push-pull pads | PARTIAL | `S3` `uio_oe` semantics; contention analysis is internal |
| AMB-002 | Host-link pin multiplexing | NONE | Entire host link is self-imposed |
| AMB-003 | 50 MHz vs 10BASE-T / USB FS budgets | PARTIAL | 50 MHz from `S3`/`S2`; cycle-budget analysis internal |
| AMB-004 | External pull-up / bus capacitance | NONE | Pure engineering; status OPEN |
| AMB-005 | Tile budget 6×4 (blog) vs 8×4 (imported spec) | DIRECT | The blog is authoritative |

---

## 6. Architectural decisions

All 27 `ARCH-PEX-*` decisions have no basis on the website; they are candidate
microarchitecture choices. The one thread that is traceable is the area-budget spirit of
`ARCH-PEX-024` (run synthesis early, leave routing headroom).
