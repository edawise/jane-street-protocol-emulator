#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate the ReqSpec against its JSON Schema and cross-reference it.

The modular YAML files under requirements/ are the single source of truth.
Nothing is generated: this script only validates and reports. Exit code is
non-zero if any check fails, so it can gate CI and pre-commit.

Gates (hard failures):

  1. JSON Schema for every document type. A document that fails here is not safe
     to walk semantically, so validation stops instead of crashing on a None list.
  2. Requirement identity, and agreement between `obligation` and
     `source_provenance`.
  3. Architectural-decision cross-references: every `satisfies_reqs` names a real
     requirement, and a decision declaring no `satisfies_reqs` must carry its own
     acceptance criteria and verification, so no capability becomes untestable.
  4. No binding requirement may be orphaned: an architecture-scoped /
     candidate-specific requirement, or an internal MUST requirement, must be
     claimed by some candidate decision in `satisfies_reqs`.
  5. The hand-written overview must not restate derived metrics.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REQ_DIR = Path(__file__).resolve().parent.parent
ROOT = REQ_DIR.parent
SCHEMA_FILE = REQ_DIR / "schema" / "reqspec.schema.json"
AMB_FILE = REQ_DIR / "ambiguities" / "AMB_spec_open_issues.yaml"
OVERVIEW_FILE = REQ_DIR / "specification.md"
ARCH_ROOT = ROOT / "architectures"

# Directories that hold schemas or tooling rather than requirement documents.
NON_DOCUMENT_DIRS = {"schema", "tools"}

EXTERNAL_PROVENANCE = {"js-brief", "tt-template", "external-standard"}
INTERNAL_PROVENANCE = {"engineered", "specialist-spec"}
# Scopes that are not architecture-neutral, so they must be claimed by a decision.
SCOPED = {"architecture-scoped", "candidate-specific"}


class ParseError(Exception):
    """Raised when a document cannot be parsed at all."""


def load(path: Path):
    try:
        return yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ParseError(f"{path}: not valid YAML ({exc.__class__.__name__})") from exc


def document_files() -> list[Path]:
    """Every requirement document, discovered rather than from a hardcoded list.

    A new category directory is picked up automatically instead of being
    silently ignored because it was missing from a tuple in this file.
    """
    return sorted(
        p for p in REQ_DIR.glob("*/*.yaml") if p.parent.name not in NON_DOCUMENT_DIRS
    )


def decision_files() -> list[Path]:
    """Candidate decision documents: architectures/<candidate>/decisions.yaml."""
    return sorted(ARCH_ROOT.glob("*/decisions.yaml"))


def report(errors: list[str], stats: dict | None) -> int:
    if stats:
        print(
            f"requirements: {stats['reqs']}   arch decisions: {stats['arch']}"
            f"   ambiguities: {stats['amb']}   candidates: {len(stats['candidates'])}"
        )
    if errors:
        print(f"\nVALIDATION FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"  - {e}")
        return 1
    if stats:
        print("\nOK: schema and cross-reference checks passed.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate the ReqSpec and report counts.")
    args = ap.parse_args()
    errors: list[str] = []

    # Loading is separated from analysis so that an unparseable document is
    # reported as a failure instead of surfacing as a traceback.
    try:
        schema = json.loads(SCHEMA_FILE.read_text())
        sources = [(p, load(p)) for p in document_files()]
        arch_paths = decision_files()
        arch_docs = [(p, load(p) or {}) for p in arch_paths]
        amb = load(AMB_FILE) or {}
    except ParseError as exc:
        return report([str(exc)], None)

    validator = Draft202012Validator(schema)
    decisions = [d for _, doc in arch_docs for d in (doc.get("decisions") or [])]
    candidates = [str(p.relative_to(ROOT).parent) for p in arch_paths]

    if not arch_docs:
        errors.append(
            f"no candidate decision documents found under {ARCH_ROOT.relative_to(ROOT)}/"
            f"<candidate>/decisions.yaml"
        )

    # 1) JSON Schema validation. Bail out on failure: a document with, say,
    #    `requirements:` left empty parses to None, and walking it would raise
    #    instead of reporting the schema error we already have.
    for path, doc in [*sources, *arch_docs, (AMB_FILE, amb)]:
        rel = path.relative_to(ROOT)
        for e in validator.iter_errors(doc):
            errors.append(f"{rel}: {getattr(e, 'json_path', '$')}: {e.message}")
    if errors:
        return report(errors, None)

    # 2) Requirement identity, and obligation/provenance agreement
    reqs: list[dict] = []
    seen: dict[str, str] = {}
    for path, doc in sources:
        for r in doc.get("requirements") or []:
            rid = r["id"]
            if rid in seen:
                errors.append(f"{rid}: duplicate requirement ID (also in {seen[rid]})")
            seen[rid] = path.name
            reqs.append(r)

            if r["obligation"] == "external" and r["source_provenance"] not in EXTERNAL_PROVENANCE:
                errors.append(
                    f"{rid}: obligation 'external' requires provenance in "
                    f"{sorted(EXTERNAL_PROVENANCE)}, got '{r['source_provenance']}'"
                )
            if r["obligation"] == "internal" and r["source_provenance"] not in INTERNAL_PROVENANCE:
                errors.append(
                    f"{rid}: obligation 'internal' requires provenance in "
                    f"{sorted(INTERNAL_PROVENANCE)}, got '{r['source_provenance']}'"
                )

    # 3) Architectural decisions: references, and standalone decisions
    for d in decisions:
        for req in d["satisfies_reqs"]:
            if req not in seen:
                errors.append(f"{d['id']}: satisfies_reqs references unknown requirement '{req}'")
        if not d["satisfies_reqs"] and not (d.get("acceptance_criteria") and d.get("verification")):
            errors.append(
                f"{d['id']}: declares no satisfies_reqs, so it is a standalone architecture "
                f"decision and must carry its own acceptance_criteria and verification"
            )

    # 4) Coverage: a binding requirement that the frozen testbench does not cover
    #    must be realised by at least one architectural decision. Binding means
    #    architecture-scoped/candidate-specific, or an internal MUST. SHOULD/MAY
    #    items are goals, not requirements, and need no realisation. The link is
    #    recorded only on the candidate side, so the requirements tree never has
    #    to name a candidate.
    satisfied = {rid for d in decisions for rid in d["satisfies_reqs"]}
    for r in reqs:
        if (r["arch_scope"] in SCOPED
                or (r["obligation"] == "internal" and r["priority"] == "MUST")) \
                and r["id"] not in satisfied:
            errors.append(
                f"{r['id']} ({r['arch_scope']}, {r['obligation']}, {r['priority']}): "
                f"binding but not in the frozen contract and not claimed by any "
                f"decision in satisfies_reqs"
            )

    # 5) The hand-written overview must not restate derived metrics. The file is
    #    non-normative, so its absence is not a validation failure: skip the lint
    #    (with a note) rather than crashing on a missing document.
    if OVERVIEW_FILE.exists():
        for i, line in enumerate(OVERVIEW_FILE.read_text().splitlines(), 1):
            if re.search(r"\b\d+\s+REQs?\b", line):
                errors.append(f"specification.md:{i}: derived requirement count must not be hardcoded")
            if re.search(r"\b\d+\.\d\s*%", line):
                errors.append(f"specification.md:{i}: derived coverage percentage must not be hardcoded")
    else:
        print("note: specification.md not found; skipping overview-metrics lint", file=sys.stderr)

    stats = {
        "reqs": len(reqs),
        "arch": len(decisions),
        "candidates": candidates,
        "amb": len(amb.get("ambiguities") or []),
    }
    return report(errors, stats)


if __name__ == "__main__":
    sys.exit(main())
