"""Run prompt versions on every test case and save the results.

Usage (from the repo root):
    python eval/run_eval.py --versions v0 v1 v2 v3 --runs 3

Writes, under eval/results/<timestamp>/:
    results.csv   one row per (version, case, run)
    summary.md    averages per version, ready to paste into the report
    raw/          the full model output for every run (keep this as evidence)
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from resumeiq.cases import load_cases  # noqa: E402
from resumeiq.llm import ConfigError, LLMClient, load_config  # noqa: E402
from resumeiq.metrics import score_case  # noqa: E402
from resumeiq.pipeline import VERSIONS, analyse  # noqa: E402

FIELDS = [
    "version", "case", "run", "ok", "error", "seconds", "score", "score_in_range",
    "gaps_found", "gaps_expected", "gap_recall", "trap_claims", "trap_terms",
    "unsupported_matches", "matches_checked", "score_issues", "human_rating_1to5",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--versions", nargs="+", default=list(VERSIONS), choices=list(VERSIONS))
    parser.add_argument("--runs", type=int, default=3, help="runs per case (to measure consistency)")
    parser.add_argument("--cases", nargs="*", help="only run these case ids")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    try:
        config = load_config()
    except ConfigError as error:
        sys.exit(str(error))
    client = LLMClient(config)
    cases = load_cases()
    if args.cases:
        cases = [c for c in cases if c["id"] in args.cases]

    out_dir = ROOT / "eval" / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    (out_dir / "raw").mkdir(parents=True)
    rows = []

    for version in args.versions:
        for case in cases:
            for run in range(1, args.runs + 1):
                print(f"{version} | {case['id']} | run {run} ...", flush=True)
                row = {"version": version, "case": case["id"], "run": run, "human_rating_1to5": ""}
                start = time.time()
                try:
                    result = analyse(case["resume"], case["jd"], version, client)
                    row.update(score_case(result, case["expected"]), ok=True, error="")
                    raw_path = out_dir / "raw" / f"{version}_{case['id']}_run{run}.json"
                    raw_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
                except Exception as error:  # keep going; failures are results too
                    row.update(ok=False, error=str(error)[:200])
                row["seconds"] = round(time.time() - start, 1)
                rows.append(row)

    with open(out_dir / "results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    summary = summarise(rows, args.versions, config.model, args.runs)
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    print("\n" + summary)
    print(f"Saved to {out_dir.relative_to(ROOT)}")


def summarise(rows: list[dict], versions: list[str], model: str, runs: int) -> str:
    lines = [
        f"Model: `{model}` | runs per case: {runs} | date: {datetime.now():%Y-%m-%d}",
        "",
        "| Version | Valid output | Score in expected range | Missing-skill recall | Trap claims | Unsupported matches | Avg score spread (max-min) |",
        "|---|---|---|---|---|---|---|",
    ]
    for version in versions:
        vrows = [r for r in rows if r["version"] == version]
        ok = [r for r in vrows if r.get("ok")]
        if not vrows:
            continue
        in_range = [r for r in ok if r.get("score_in_range")]
        recalls = [r["gap_recall"] for r in ok if r.get("gap_recall") is not None]
        spreads = []
        for case_id in {r["case"] for r in ok}:
            scores = [r["score"] for r in ok if r["case"] == case_id and r.get("score") is not None]
            if len(scores) > 1:
                spreads.append(max(scores) - min(scores))
        recall = f"{statistics.mean(recalls):.2f}" if recalls else "-"
        spread = f"{statistics.mean(spreads):.1f}" if spreads else "-"
        traps = sum(r.get("trap_claims", 0) for r in ok)
        unsupported = sum(r.get("unsupported_matches", 0) for r in ok)
        lines.append(
            f"| {VERSIONS[version]} | {len(ok)}/{len(vrows)} | {len(in_range)}/{len(ok)} | "
            f"{recall} | {traps} | {unsupported} | {spread} |"
        )
    lines += [
        "",
        "Trap claims = skills listed as matches that the job never asked for (e.g. C++ in case 03).",
        "Unsupported matches = matches whose quote/skill could not be found in the resume or job description.",
        "Fill in human_rating_1to5 in results.csv yourselves before quoting usefulness.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
