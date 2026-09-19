# `architectures/` — candidate solutions

One directory per candidate architecture. `../requirements/` states problems; this tree
states solutions.

Nothing here is part of the frozen behavioural contract, and `verification/` must not depend
on it.

## Layout

```text
architectures/
└── README.md
```

No candidate architecture has been designed yet. Each future candidate will hold
`decisions.yaml`, and later — once it reaches implementation — its own `rtl/`, `synthesis/`,
and `physical/` outputs.

## The link to the spec

The link is recorded in **one direction only**: from the candidate to the requirements it
satisfies. Nothing in the requirements tree names a candidate.

```yaml
# architectures/<candidate>/decisions.yaml
- id: ARCH-XXX-001
  title: "…"
  satisfies_reqs: ["REQ-FUNC-008"]
```

`../requirements/tools/validate_reqspec.py` reads `architectures/*/decisions.yaml` and checks
two things: every ID in `satisfies_reqs` names a real requirement, and no architecture-scoped
(or internal MUST) requirement is left orphaned — i.e. some candidate decision claims it. The
orphan check only applies once at least one candidate exists.

## Adding a candidate

1. `mkdir architectures/<candidate>/`
2. Write `decisions.yaml` with a `candidate:` block and a `decisions:` list of `ARCH-*-NNN`
   entries, each with `satisfies_reqs`.
3. Run `python3 ../requirements/tools/validate_reqspec.py`.

A decision with no `satisfies_reqs` is treated as standalone and must carry its own
`acceptance_criteria` and `verification`, so no capability becomes untestable.

The frozen contract is computed from `arch_scope` and `obligation` alone, so adding or removing
candidates never changes it.
