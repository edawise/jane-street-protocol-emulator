# `requirements/` — the spec tree

States **problems**. `../architectures/` states **solutions**.

Nothing here names a candidate architecture, and anything that presupposes a mechanism is
tagged so it stays out of the verification contract.

## Contents

| Document | Count | Top-level key |
|---|---|---|
| Requirement | 48 | `requirements:` |
| Ambiguity | 5 | `ambiguities:` |

Architectural decisions live in `../architectures/<candidate>/decisions.yaml`, not here.

## The two axes

| Tag | Values |
|---|---|
| `arch_scope` | `independent`, `constrained`, `architecture-scoped`, `candidate-specific` |
| `obligation` | `external`, `internal` |

* `independent` / `constrained` — architecture-neutral. `constrained` means fixed by the Tiny
  Tapeout harness.
* `architecture-scoped` — imposes a capability on our design that is portable across
  candidates (a channel count, a host link, a delay primitive). Not architecture-neutral, so
  not in the contract.
* `candidate-specific` — true only for one named candidate (an exact lane count, an opcode
  encoding). Currently unused.
* `external` / `internal` — required by the brief, a standard, or the harness; versus our own
  target.

A third axis, `priority`, separates **requirements** from **goals**:

* `MUST` — a **requirement**: the design is bound to meet it. If it is not in the frozen
  contract, some architectural decision must claim it in `satisfies_reqs`.
* `SHOULD` / `MAY` — a **goal**: an elective target a candidate may pursue or drop.

So `obligation` says *who imposed it*, `priority` says *whether it binds*, and `arch_scope`
says *whether the generic testbench can see it*.

The **frozen verification contract** is the intersection:

```
arch_scope ∈ {independent, constrained}   AND   obligation = external
```

`tools/select_contract.py` computes it and prints the counts.

### Derived requirements are frozen too

A requirement need not be written verbatim in the brief to be frozen. "Start with UART, SPI,
and I2C" is unfalsifiable until you define what those protocols *are*, so the definitional
details — UART framing and baud rates, SPI CPOL/CPHA modes, I2C timing, open-drain behaviour —
are derived requirements sourced from published standards (`source_provenance:
external-standard`) and are frozen with the directly-mandated set.

The litmus test for the `obligation` axis: **can a design satisfy the brief without this
requirement?**

* **No** — it is mandated, or it is the necessary definition of a mandated item (UART means
  receive *and* transmit) → `external`, frozen.
* **Yes** — it is a capability we chose beyond the mandate (SPI slave mode, a 25 MHz SPI
  target, a host link, ≥2 concurrent channels) → `internal` or `architecture-scoped`, not frozen.

## Folders

| Folder | Holds |
|---|---|
| `functional/` | UART/SPI/I2C, and the core "protocols are firmware, not fixed logic" requirement |
| `timing/` | Cycle-exact determinism, cumulative drift, free-running cycle counter |
| `interfaces/` | 24-pin harness, `uio_oe` tri-state, clock, reset |
| `physical/` | IHP 130 nm PDK, 6×4 tile budget, area, 50 MHz STA, Apache-2.0 |
| `performance/` | UART baud accuracy, SPI rate target, I2C timing compliance |
| `optional/` | Stretch protocols: USB, Ethernet, CAN, JTAG/SWD, 1-Wire, sniffing |
| `verification/` | Verification deliverables: ISS/reference model, formal + randomised testing |
| `architecture/` | 13 architecture-scoped requirements (concurrency, buffering, host link, delay primitives). The link to a candidate is recorded only on the candidate side, in each decision's `satisfies_reqs` |
| `ambiguities/` | Open and resolved specification gaps, each with impact, resolution, verification check |
| `schema/` | `reqspec.schema.json` |
| `tools/` | `validate_reqspec.py`, `select_contract.py` |

Ambiguities live here because they are facts about the *problem* — the brief is silent on
open-drain pads, the harness gives 16 dedicated pins and a host link needs two. They exist
whether or not a candidate is ever built. A decision is one answer to a problem, so it lives
with the candidate.

Architecture-scoped requirements stay here rather than moving to a candidate because each has
its own acceptance criteria and test ID that must survive one-to-one, and the
requirement↔decision relation is many-to-many. They remain *constraints on our design*, not
descriptions of how any one candidate meets them, so nothing here names a candidate. The
validator enforces that none of them is orphaned.

## Where a new item goes

| You have… | Put it in… |
|---|---|
| Behaviour the brief or a standard mandates | matching `functional/`, `timing/`, `interfaces/`, `physical/`, `performance/`, `optional/`, or `verification/` |
| A capability our design must have, but which a different architecture could avoid | `architecture/`, with `arch_scope: architecture-scoped` |
| A gap or conflict in the sources | `ambiguities/AMB_spec_open_issues.yaml` |
| A design choice that answers a requirement | `../architectures/<candidate>/decisions.yaml` |

## Gates

```bash
pip install -r ../requirements-dev.txt

python3 tools/validate_reqspec.py
python3 tools/select_contract.py --quiet --intents ../verification/intent
python3 tools/select_contract.py --md contract.md      # human-readable snapshot
```

Both gates run in CI and as pre-commit hooks. The validator reads `requirements/` and
`../architectures/` together, because the orphan check needs the decisions' `satisfies_reqs`.

## References

* `specification.md` — system overview and directory rationale
* `REQUIREMENTS_GUIDE.md` — plain-English explanation of every requirement, ambiguity, and decision
* `PROVENANCE_AUDIT.md` — where each requirement's content came from
