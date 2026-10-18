"""Re-score frozen N5 annotations from the committed historical detector archive."""
from __future__ import annotations

import hashlib
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    from scripts.score_team_labels import score

    evidence = Path(__file__).resolve().parent
    archive = ROOT / "docs/evidence/synthetic_labels_2026-10-17/runs/detector_runs.tar.xz"
    summary = {"archive": str(archive.relative_to(ROOT)), "archive_sha256": digest(archive.read_bytes()),
               "scorer_sha256": digest((ROOT / "scripts/score_team_labels.py").read_bytes()), "bags": {}}
    with tarfile.open(archive) as source:
        for bag in ("synthetic_platform", "synthetic_switch", "synthetic_tunnels"):
            label_path = evidence / f"labels_{bag}.json"
            labels = json.loads(label_path.read_text())
            reports = {}
            for version in ("v100", "v110"):
                member = f"{version}_{bag}.jsonl"
                raw = source.extractfile(member).read()
                report = score([json.loads(line) for line in raw.splitlines() if line.strip()], labels)
                report["inputs"] = {
                    "archive": summary["archive"], "archive_sha256": summary["archive_sha256"],
                    "member": member, "results_sha256": digest(raw),
                    "labels": str(label_path.relative_to(ROOT)), "labels_sha256": digest(label_path.read_bytes()),
                    "scorer_sha256": summary["scorer_sha256"],
                }
                (evidence / f"score_{bag}_{version}.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
                reports[version] = report
            summary["bags"][bag] = {
                "frames": reports["v110"]["frames"], "labels_sha256": reports["v110"]["inputs"]["labels_sha256"],
                "v100_v110_scores_identical": ({k: v for k, v in reports["v100"].items() if k != "inputs"}
                                               == {k: v for k, v in reports["v110"].items() if k != "inputs"}),
                "summary": reports["v110"]["summary"],
                "objects": {name: {k: v for k, v in entry.items() if k != "observations"}
                            for name, entry in reports["v110"]["objects"].items()},
            }
    (evidence / "scoring_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps({bag: item["summary"] for bag, item in summary["bags"].items()}))


if __name__ == "__main__":
    main()
