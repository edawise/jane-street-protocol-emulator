# `architectures/` — candidate solutions

One directory per candidate architecture. `../requirements/` states problems; this tree
states solutions.

Nothing here is part of the frozen behavioural contract, and `verification/` must not depend
on it.

## Layout

```text
architectures/
├── README.md
└── candidate_001/
    └── decisions.yaml
```

Each candidate will later also hold `rtl/`, `synthesis/`, and `physical/` — those are outputs
of a specific candidate, so they belong inside it rather than beside it.

## Candidate 001 — PEX

**PEX (Programmable Protocol Emulator eXecutive)**, v0.2.0, 27 decisions in
`candidate_001/decisions.yaml`.

Four independent single-cycle execution lanes running 24-bit microcode from a shared
1024×24-bit SRAM (one 256-word bank per lane); per-lane scratch/shift registers, side-set
pins, and 8-entry TX/RX FIFOs; 16 virtual pins mapped through a crossbar to the 24 real
GPIOs; a mask-ROM UART loader fills the SRAM at boot; a 256-byte CSR space reached over a
10-byte binary packet. 12 opcodes.

`../requirements/REQUIREMENTS_GUIDE.md` Part 5 has a one-line explanation of each decision.

## The link to the spec

The link is recorded in **one direction only**: from the candidate to the requirements it
satisfies. Nothing in the requirements tree names a candidate.

```yaml
# architectures/candidate_001/decisions.yaml
- id: ARCH-PEX-001
  title: "Quad Execution Lanes (SM0 to SM3)"
  satisfies_reqs: ["REQ-FUNC-008"]
```

`../requirements/tools/validate_reqspec.py` reads `architectures/*/decisions.yaml` and checks
two things: every ID in `satisfies_reqs` names a real requirement, and no architecture-scoped
requirement is left orphaned — i.e. some candidate decision claims it.

## Adding a candidate

1. `mkdir architectures/candidate_002/`
2. Write `decisions.yaml` with a `candidate:` block and a `decisions:` list of `ARCH-*-NNN`
   entries, each with `satisfies_reqs`.
3. Run `python3 ../requirements/tools/validate_reqspec.py`.

A decision with no `satisfies_reqs` is treated as standalone and must carry its own
`acceptance_criteria` and `verification`, so no capability becomes untestable.

The frozen contract is computed from `arch_scope` and `obligation` alone, so adding or removing
candidates never changes it.
