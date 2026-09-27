# Organizer point fixture

`points.npz` contains only the organizers' appended synthetic object points from
`cloud_with_fake_obj`, extracted before evaluation by `scripts/novel_placement_eval.py`.
It is a deliberate 113 KB exception to the repository's general `*.npz` exclusion.
Raw bags and background frame caches remain excluded.

The source is the [organizers' public recording](https://disk.yandex.ru/d/KpkG_yKoGk-vHQ).
`manifest.json` records the original bag SHA256, exact source frame identities and timestamps,
object sizes and fixture SHA256. Coordinates use the fixed sensor-axis map `-y, +x, +z`.
Only points at a nearest X distance of 15–80 m are selected. Original X, Z, intensity and
sampling/dropouts are retained; no detector output selects or positions these points.

This fixture supports a sensitivity experiment on novel placements and seen backgrounds.
It does not establish surveyed rail membership, correct destination bed height, synchronized
background motion or real unseen-obstacle recall. The complete limitations and frozen cases
are recorded in the [pre-evaluation protocol](../p4_novel_protocol_2026-09-26.json).

After fetching and caching the original recordings as described in `docs/VM_GUIDE.md`, run the
committed plan on another machine without editing it:

```bash
python scripts/novel_placement_eval.py run \
  --plan docs/evidence/results/p4_novel_plan_2026-09-26.json \
  --cache-root /path/to/cache \
  --source-root docs/evidence/results/p4_novel_source_2026-09-26 \
  --out /path/to/novel_results.json
```

The overrides change only where files are read. Every input hash and the original plan hash
remain checked. The detector and evaluator must match the versions pinned in the plan.
