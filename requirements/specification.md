# Jane Street Protocol Emulator ASIC: Requirements Specification

> **Document Type:** Non-Normative System Overview & Specification Index  
> **Target Shuttle:** Tiny Tapeout IHP 130 nm CMOS5L (March 2027)  
> **Submission Deadline:** January 18, 2027  
> **Canonical Source of Truth:** Machine-readable YAML specifications in [`requirements/`](./)  

---

## 1. Scope & Purpose

This document provides a high-level technical overview of the requirement specification for the [Jane Street Protocol Emulator ASIC Competition](https://blog.janestreet.com/protocol-emulator-asic-competition/).

The competition goal is to build an open-source, general-purpose protocol emulator ASIC capable of emulating diverse serial and parallel hardware protocols (UART, SPI, I2C, USB, Ethernet, CAN, and others) via reloadable firmware rather than fixed hardware controller logic.

### Canonical Machine-Readable Source of Truth
In accordance with the governance principles defined in `README.md`, all normative requirements, parameter ranges, and verification criteria are defined in machine-readable, schema-validated YAML files. This document serves solely as an introductory guide.

- **Requirements (architecture-neutral):** [`functional/`](./functional/), [`timing/`](./timing/), [`interfaces/`](./interfaces/), [`physical/`](./physical/), [`performance/`](./performance/), [`optional/`](./optional/), [`verification/`](./verification/)
- **Architecture-scoped requirements:** [`architecture/REQ_ARCH_scoped.yaml`](./architecture/REQ_ARCH_scoped.yaml)
- **Candidate decisions (separate tree):** [`../architectures/<candidate>/decisions.yaml`](../architectures/)
- **Ambiguities & open issues:** [`ambiguities/AMB_spec_open_issues.yaml`](./ambiguities/AMB_spec_open_issues.yaml)
- **JSON Schema:** [`schema/reqspec.schema.json`](./schema/reqspec.schema.json)
- **Validation tool:** `pip install -r requirements-dev.txt && python3 requirements/tools/validate_reqspec.py`
- **Frozen-contract selector:** `python3 requirements/tools/select_contract.py --md contract.md`

---

## 2. Architectural Independence Principle

A foundational principle of this project is the strict separation between:
1. **Behavioral Requirements (`REQ-*`)**: Architecture-agnostic contracts specifying observable pin behaviors, timing precision, physical constraints, and host communication.
2. **Architecture-scoped Requirements (`REQ-*` with `arch_scope: architecture-scoped`)**: Capabilities our own design must have but which a different architecture could avoid (channel count, host link, delay primitives). They live in [`architecture/`](./architecture/) and are excluded from the frozen contract.
3. **Candidate Decisions (`ARCH-*-*`)**: Concrete microarchitectural choices made by one candidate. These live in the separate [`../architectures/`](../architectures/) tree, not here, because a decision is one instantiation of the problem rather than a statement of it.
4. **Ambiguities & Open Issues (`AMB-*`)**: Underspecified hardware behaviors (e.g. open-drain emulation on push-pull pads) with explicit resolution strategies.

This separation ensures that the **Behavioral Reference Model (Phase II)** and the **Generic Verification Environment (Phase III)** remain stable across multiple microarchitectural candidates (such as minimal RISC-V cores, PIO state machines, or protocol-specific VLIW engines) without altering the requirement contract.

**Note on the `arch_scope` filter:** the ReqSpec is a superset of the frozen verification contract. Consumers build the architecture-neutral contract by selecting requirements whose `arch_scope` is `independent` or `constrained` **and** whose `obligation` is `external`. Requirements that impose a capability on our design but are not architecture-neutral are `architecture-scoped` (they live in `architecture/`); requirements true only for one named candidate are `candidate-specific`. Neither reaches the frozen contract, so the generic testbench never has to change when a candidate is replaced. The filter is executable: `python3 requirements/tools/select_contract.py --md contract.md`. Requirement counts and coverage percentages are computed by the validator and are intentionally not restated here.

---

## 3. Physical & Environment Overview

```text
                                Tiny Tapeout Harness (6x4 Baseline)
                   ┌─────────────────────────────────────────────────────────┐
                   │                                                         │
   ui_in[7:0]  ───▶│──▶ Dedicated Inputs (GPIO 0..7)                         │
  (incl. HOST_RX)  │                                                         │
                   │                                                         │
   uo_out[7:0] ◀───│◀── Dedicated Outputs (GPIO 8..15)                       │
  (incl. HOST_TX)  │                                                         │
                   │                                                         │
   uio[7:0]    ◀──▶│◀─▶ Bidirectional I/O with OE (GPIO 16..23)              │
                   │                                                         │
   clk (50MHz) ───▶│──▶ Single Synchronous Clock Domain                      │
   rst_n       ───▶│──▶ Asynchronous Reset (Synchronous Deassertion)         │
   ena         ───▶│──▶ Harness Power Enable                                 │
                   │                                                         │
                   │   ┌─────────────────────────────────────────────────┐   │
                   │   │         Protocol Emulator Execution Core        │   │
                   │   │   (Fixed integer cycle latency, zero jitter)    │   │
                   │   └─────────────────────────────────────────────────┘   │
                   │   ┌────────────────────────┐  ┌─────────────────────┐   │
                   │   │ Program Memory         │  │ Host Serial Link    │   │
                   │   │ (Fits tile area budget)│  │ (Bootstrap & CSR)   │   │
                   │   └────────────────────────┘  └─────────────────────┘   │
                   └─────────────────────────────────────────────────────────┘
```

- **Process Node:** IHP 130 nm CMOS5L (open PDK via LibreLane / OpenLane 2).
- **Silicon Area Budget:** Baseline **6×4 tiles** (~24 tiles, ~24,000 logic cells maximum). Target pre-layout cell count <= 18,000 cells (75% budget rule). Conditionally scalable to **8×4 tiles** (~32 tiles, ~32,000 cells; target <= 24,000 cells) if shuttle scale-up is confirmed.
- **Clock Domain:** Single 50 MHz clock domain (`CLOCK_PERIOD = 20.0 ns`), active-low asynchronous reset with internal synchronous deassertion.
- **Pin Ring:** 24 physical GPIOs (8 dedicated inputs `ui_in`, 8 dedicated outputs `uo_out`, 8 bidirectional `uio` with `uio_oe` control).

---

## 4. Requirements Taxonomy & Directory Structure

```text
requirements/
├── schema/
│   └── reqspec.schema.json             # JSON Schema for requirement, decision, and ambiguity documents
├── tools/
│   ├── validate_reqspec.py             # Schema + cross-reference validator (no generation)
│   └── select_contract.py              # Frozen-contract selector + intent checker
├── functional/
│   ├── REQ_FUNC_protocols.yaml         # UART (TX/RX), SPI (Master/Slave), I2C (Master/Open-Drain)
│   └── REQ_FUNC_reprogram.yaml         # Dynamic SRAM programmability (behavioural core)
├── architecture/
│   └── REQ_ARCH_scoped.yaml            # Architecture-scoped requirements (excluded from the frozen contract)
├── timing/
│   ├── REQ_TIME_determinism.yaml       # Fixed integer cycle latency, zero cumulative timing drift
│   └── REQ_TIME_control.yaml           # Free-running cycle counter
├── interfaces/
│   ├── REQ_IF_gpio.yaml                # Tiny Tapeout 24-pin harness, OE tri-state, crossbar routing
│   └── REQ_IF_clock_reset.yaml         # 50 MHz clk, asynchronous reset
├── physical/
│   └── REQ_PHYS_constraints.yaml       # IHP 130nm PDK, 6x4 tile budget (<=18K cells), 50 MHz STA
├── performance/
│   └── REQ_PERF_rates.yaml             # 115.2k UART, 100k & 400k I2C
├── optional/
│   └── REQ_OPT_stretch.yaml            # Low-Speed USB, 10BASE-T Ethernet, CAN, 1-Wire, JTAG/SWD
├── verification/
│   └── REQ_VERIF_deliverables.yaml     # Cycle-accurate ISS reference model, constrained-random/formal
├── ambiguities/
│   └── AMB_spec_open_issues.yaml       # Open/resolved specification gaps with technical rationales

../architectures/                       # Candidate solutions (separate tree)
└── <candidate>/
    └── decisions.yaml                  # one candidate's microarchitectural decisions
```

---

## 5. Verification Framework Contract

The requirement catalog directly feeds Phase II and Phase III:
1. **Behavioral Reference Model (Phase II):** reads the modular YAML under `requirements/`, applies the frozen-contract filter (`arch_scope` in {`independent`, `constrained`} and `obligation` = `external`), then builds a Python/SystemVerilog software model producing expected cycle-by-cycle pin waveforms. Its inputs are **protocol intents** conforming to [`../verification/intent.schema.json`](../verification/intent.schema.json), never ISA programs or register addresses; each candidate architecture supplies its own intent-to-program adapter.
2. **Generic Verification Environment (Phase III):** Reusable testbenches instantiate bus functional models and checkers for UART, SPI, and I2C, mapped directly to each requirement's `generic_test_id` (`TEST-*`). Because intents are protocol-level and pin roles are abstract, this environment is frozen for the life of the project and is re-run unchanged against every architecture candidate.
3. **Traceability:** every requirement records its parameter-level external basis in `traceability.standards`; every architectural decision records the requirements it satisfies in `satisfies_reqs`. The link runs in one direction only — from the candidate to the spec — so the requirements tree never names a candidate. The validator enforces two things: no architecture-scoped requirement may be **orphaned** (some candidate decision must claim it), and a decision that declares no `satisfies_reqs` must instead carry its own `acceptance_criteria` and `verification`, so no capability becomes untestable.
