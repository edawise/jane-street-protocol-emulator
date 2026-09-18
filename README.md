# Autonomous Protocol Emulator

An open-source, agentic approach to hardware design and verification for the
[Jane Street Protocol Emulator ASIC Competition](https://blog.janestreet.com/protocol-emulator-asic-competition/).
Using [edawise/edagent](https://github.com/edawise/edagent).

## Status

Requirements and verification infrastructure. There is no RTL, no reference model, and no
synthesis output yet.

## Layout

The repository separates **problems** from **solutions**:

* `requirements/` — the spec tree. States what is required. It holds the frozen contract plus
  self-imposed targets and architecture-scoped capabilities, and it never names a candidate.
* `architectures/` — one directory per candidate architecture. States how a candidate answers
  the requirements. Churns.
* `verification/` — the frozen interface the generic testbench will be built against.

```text
.
├── LICENSE                         # Apache-2.0
├── README.md
├── requirements-dev.txt            # PyYAML + jsonschema
│
├── requirements/                   # PROBLEMS
│   ├── functional/ timing/ interfaces/ physical/ performance/ optional/ verification/
│   ├── architecture/               # architecture-scoped requirements (capabilities of our design)
│   ├── ambiguities/
│   ├── schema/                     # JSON Schema for the requirement documents
│   ├── tools/                      # validator, frozen-contract selector
│   ├── specification.md
│   └── README.md  REQUIREMENTS_GUIDE.md  PROVENANCE_AUDIT.md
│
├── architectures/                  # SOLUTIONS
│   ├── README.md
│   └── candidate_001/decisions.yaml
│
└── verification/
    ├── intent.schema.json
    └── intent/example_uart_8n1.yaml
```

Not present yet: `models/`, per-candidate `rtl/`, `synthesis/`, `physical/`, `research/`,
`agents/`.

## The two axes

Whether the architecture-independent testbench may depend on a requirement is decided by two
tags on the requirement itself, not by which folder it sits in:

| Tag | Values |
|---|---|
| `arch_scope` | `independent`, `constrained`, `architecture-scoped`, `candidate-specific` |
| `obligation` | `external`, `internal` |

The **frozen verification contract** is the intersection:

```
arch_scope ∈ {independent, constrained}   AND   obligation = external
```

That subset must not change: it is what the generic testbench is built against. Everything
else in the tree is iterable — self-imposed targets and architecture-scoped capabilities are
expected to move as the design does. Replacing a candidate never changes the contract.
`tools/select_contract.py` computes it and prints the counts.

## Gates

```bash
pip install -r requirements-dev.txt

python3 requirements/tools/validate_reqspec.py
python3 requirements/tools/select_contract.py --quiet --intents verification/intent
```

Both run in CI and as pre-commit hooks. The validator reads `requirements/` and
`architectures/` together.

## Principles

1. Specification before implementation — an architectural assumption must never become a requirement.
2. Verify behaviour, not implementation.
3. Keep design and verification independent — the design agent does not define its own
   correctness criteria.
4. Failures are research signals, not merely code patches.
5. Synthesise early; simulation success does not imply physical feasibility.
6. Everything is versioned and traceable.
7. Prefer measurable improvement.
8. Open-source the methodology, not just the submission.

## Reading order

1. This file
2. `requirements/README.md` — how the spec tree is organised
3. `requirements/REQUIREMENTS_GUIDE.md` — plain-English explanation of every entry
4. `requirements/PROVENANCE_AUDIT.md` — where each requirement came from
5. `architectures/README.md` — the candidate layout