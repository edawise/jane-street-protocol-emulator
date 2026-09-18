#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Select the frozen, architecture-independent verification contract.

The ReqSpec is a superset: it also carries candidate microarchitecture choices
(`arch_scope: candidate-specific`) and self-imposed engineering targets
(`obligation: internal`). The behavioural reference model (Phase II) and the generic
verification environment (Phase III) must be built from the *intersection* of
the two axes only:

    arch_scope in {independent, constrained}   AND   obligation == "external"

Anything that fails that filter is verified at the architecture level (Phase IV)
instead, so the generic testbench never has to change when a new candidate is
introduced.

Usage:
    python3 requirements/tools/select_contract.py                    # JSON to stdout
    python3 requirements/tools/select_contract.py --md contract.md   # human-readable
    python3 requirements/tools/select_contract.py --intents verification/intent
    python3 requirements/tools/select_contract.py --check-intents    # exit 1 on violation
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REQ_DIR = Path(__file__).resolve().parent.parent
ROOT = REQ_DIR.parent
INTENT_SCHEMA_FILE = ROOT / "verification" / "intent.schema.json"
# Directories that hold schemas or tooling rather than requirement documents.
NON_DOCUMENT_DIRS = {"schema", "tools"}
IN_SCOPE = {"independent", "constrained"}
GATING_OBLIGATION = "external"


def load_requirements() -> list[dict]:
    """Discover requirement documents instead of globbing a hardcoded category list."""
    reqs: list[dict] = []
    for path in sorted(REQ_DIR.glob("*/*.yaml")):
        if path.parent.name in NON_DOCUMENT_DIRS:
            continue
        doc = yaml.safe_load(path.read_text()) or {}
        for req in doc.get("requirements") or []:
            req["_file"] = str(path.relative_to(ROOT))
            reqs.append(req)
    return reqs


def classify(reqs: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (contract, excluded_scoped, excluded_internal) as disjoint buckets.

    A requirement is excluded as architecture-scoped first, because that is the
    axis that decides whether the frozen testbench may depend on it at all.
    """
    contract, excluded_scoped, excluded_internal = [], [], []
    for req in reqs:
        if req["arch_scope"] not in IN_SCOPE:
            excluded_scoped.append(req)
        elif req["obligation"] != GATING_OBLIGATION:
            excluded_internal.append(req)
        else:
            contract.append(req)
    return contract, excluded_scoped, excluded_internal


def project(req: dict) -> dict:
    return {
        "id": req["id"],
        "category": req["category"],
        "priority": req["priority"],
        "status": req["status"],
        "arch_scope": req["arch_scope"],
        "statement": req["statement"].strip(),
        "parameters": req.get("parameters") or {},
        "acceptance_criteria": req.get("acceptance_criteria") or [],
        "source_provenance": req["source_provenance"],
        "standards": (req.get("traceability") or {}).get("standards") or [],
        "generic_test_id": (req.get("verification") or {}).get("generic_test_id"),
    }


def build(reqs: list[dict]) -> dict:
    contract, excluded_scoped, excluded_internal = classify(reqs)
    return {
        "contract_version": "1.0.0",
        "filter": {
            "arch_scope": sorted(IN_SCOPE),
            "obligation": GATING_OBLIGATION,
        },
        "counts": {
            "total_requirements": len(reqs),
            "in_contract": len(contract),
            "excluded_architecture_scoped": len(excluded_scoped),
            "excluded_internal": len(excluded_internal),
        },
        "requirements": [project(r) for r in contract],
        "excluded": {
            "architecture_scoped": [
                {"id": r["id"], "arch_scope": r["arch_scope"], "file": r["_file"]}
                for r in excluded_scoped
            ],
            "internal": [
                {"id": r["id"], "file": r["_file"]} for r in excluded_internal
            ],
        },
    }


def to_markdown(contract: dict) -> str:
    c = contract["counts"]
    lines = [
        "# Frozen Verification Contract",
        "",
        f"- Total requirements in ReqSpec: {c['total_requirements']}",
        f"- In frozen contract: {c['in_contract']}",
        f"- Excluded (architecture-scoped): {c['excluded_architecture_scoped']}",
        f"- Excluded (internal obligation): {c['excluded_internal']}",
        "",
        f"Filter: `arch_scope in {contract['filter']['arch_scope']}` AND "
        f"`obligation == \"{contract['filter']['obligation']}\"`.",
        "",
        "| ID | Cat | Pri | Statement | Standards | Test |",
        "|---|---|---|---|---|---|",
    ]
    for r in contract["requirements"]:
        statement = " ".join(r["statement"].split()).replace("|", "\\|")
        stds = ", ".join(s["id"] for s in r["standards"]) or "-"
        lines.append(
            f"| {r['id']} | {r['category']} | {r['priority']} | {statement} | {stds} | {r['generic_test_id']} |"
        )

    lines += ["", "## Excluded from the frozen contract", ""]
    for label, key in (("Architecture-scoped (verified at architecture level)", "architecture_scoped"),
                       ("Internal obligation (deliberate, non-contractual)", "internal")):
        ids = contract["excluded"][key]
        lines.append(f"### {label}")
        lines.append("")
        lines.append(", ".join(f"`{e['id']}`" for e in ids) if ids else "_none_")
        lines.append("")
    return "\n".join(lines) + "\n"


def check_intents(contract: dict, target: Path) -> list[str]:
    """Validate intent files and ensure they only reference contract requirements."""
    errors: list[str] = []
    schema = json.loads(INTENT_SCHEMA_FILE.read_text())
    validator = Draft202012Validator(schema)
    allowed = {r["id"] for r in contract["requirements"]}
    files = sorted(target.glob("*.y*ml")) if target.is_dir() else [target]
    for path in files:
        doc = yaml.safe_load(path.read_text())
        rel = path.relative_to(ROOT) if ROOT in path.parents else path
        for err in validator.iter_errors(doc):
            errors.append(f"{rel}: {err.json_path}: {err.message}")
        for intent in (doc or {}).get("intents", []) or []:
            for rid in intent.get("requires", []) or []:
                if rid not in allowed:
                    errors.append(
                        f"{rel}: intent {intent.get('id')} requires {rid}, which is not in the "
                        f"frozen contract (architecture-scoped or self-imposed). Intents must only "
                        f"reference architecture-independent, externally-mandated requirements."
                    )
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", metavar="PATH", help="write a Markdown summary instead of JSON")
    ap.add_argument("--out", metavar="PATH", help="write JSON to PATH (default: stdout)")
    ap.add_argument("--intents", metavar="PATH", help="validate an intent file or directory")
    ap.add_argument("--quiet", action="store_true", help="suppress the JSON dump (for CI/pre-commit gates)")
    args = ap.parse_args()

    contract = build(load_requirements())

    if args.md:
        Path(args.md).write_text(to_markdown(contract))
        print(f"wrote {args.md}", file=sys.stderr)
    else:
        text = json.dumps(contract, indent=2, sort_keys=False) + "\n"
        if args.out:
            Path(args.out).write_text(text)
            print(f"wrote {args.out}", file=sys.stderr)
        elif not args.quiet:
            sys.stdout.write(text)

    c = contract["counts"]
    print(
        f"contract: {c['in_contract']}/{c['total_requirements']} requirements "
        f"(excluded: {c['excluded_architecture_scoped']} architecture-scoped, "
        f"{c['excluded_internal']} internal-obligation)",
        file=sys.stderr,
    )

    if args.intents:
        errors = check_intents(contract, Path(args.intents))
        if errors:
            print(f"\nINTENT CHECK FAILED ({len(errors)} error(s)):", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1
        print("intents: OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
