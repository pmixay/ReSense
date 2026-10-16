"""Development P3 probes, unchanged published range driver and placements."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path("/source/repo")
OUT = Path("/out/results")
BAGS = dict(A="roundT_squareT_pressureGate_squareT", B="roundT_doubleT",
            C="roundT_pressureGate_roundT", S="squareT_platform_squareT_switch")


def main(cfg, mode):
    sys.path.insert(0, str(ROOT / "docs/evidence/judgement_2026-10-13/scripts"))
    import range_test
    import resense.clustering as cl
    original = cl.top_is_free
    state = dict(case=None, calls=[], proof=[])
    own_original, follow_original, vault_original = cl._own_rays_pass, cl._follow, cl._local_vault

    def own(*args, **kwargs):
        ans = own_original(*args, **kwargs)
        qa, qe, beyond, above, s0, s1 = args
        state["proof"].append(dict(kind="own", answer=bool(ans), span=[s0, s1], kwargs=kwargs,
                                  qa=qa[above].tolist(), qe=qe[above].tolist(), beyond=beyond[above].tolist()))
        return ans

    def follow(*args, **kwargs):
        ans = follow_original(*args, **kwargs)
        state["proof"].append(dict(kind="follow", before=list(args[-2:]), after=list(ans[:2]),
                                  moved=ans[2] is not None))
        return ans

    def vault(*args, **kwargs):
        ans = vault_original(*args, **kwargs)
        state["proof"].append(dict(kind="vault", answer=ans))
        return ans
    cl._own_rays_pass, cl._follow, cl._local_vault = own, follow, vault

    def observed(rays, idx, *args, **kwargs):
        state["proof"] = []
        ans = original(rays, idx, *args, **kwargs)
        p = rays.xyz[idx].astype(float)
        az = np.degrees(np.arctan2(p[:, 1], p[:, 0]))
        el = np.degrees(np.arctan2(p[:, 2], np.hypot(p[:, 0], p[:, 1])))
        w = rays.window(float(az.min()) - .12, float(az.max()) + .12)
        q = rays.xyz[w].astype(float)
        state["calls"].append(dict(answer=bool(ans), x=float(np.median(p[:, 0])),
                                   top=float(el.max()), hmax=float(rays.h[idx].max()),
                                   body_dy=[float(rays.dy[idx].min()), float(rays.dy[idx].max())],
                                   az=[float(az.min()), float(az.max())],
                                   xyz=q.tolist(), h=rays.h[w].tolist(),
                                   dy=rays.dy[w].tolist(), kwargs=kwargs, proof=state["proof"]))
        return ans
    cl.top_is_free = observed
    a = ["--start", "150", "--d0", "230", "--end", "340"]
    b = ["--start", "50", "--d0", "230"]
    c = ["--start", "0", "--d0", "230"]
    s = ["--start", "360", "--end", "620", "--lat", ".7"]
    cases = [("pole_c", "A", ".3,.3,2.8", a), ("C_person", "C", ".5,.5,1.75", c)]
    if mode == "all":
        cases += [("pole_side", "A", ".3,.3,2.8", a + ["--lat", ".7"]),
                  ("pole_sideN", "A", ".3,.3,2.8", a + ["--lat", "-.7"]),
                  ("post_c", "A", ".5,.5,2.5", a), ("post_side", "A", ".5,.5,2.5", a + ["--lat", ".7"]),
                  ("pole_c_drop", "A", ".3,.3,2.8", a + ["--dropout"]),
                  ("pole_side_drop", "A", ".3,.3,2.8", a + ["--lat", ".7", "--dropout"]),
                  ("A_person", "A", ".5,.5,1.75", a),
                  ("S_pole_side60", "S", ".3,.3,2.8", s + ["--d0", "60"]),
                  ("S_pole_side100", "S", ".3,.3,2.8", s + ["--d0", "100"]),
                  ("B_pole_c", "B", ".3,.3,2.8", b), ("B_pole_side", "B", ".3,.3,2.8", b + ["--lat", ".7"]),
                  ("C_pole_c", "C", ".3,.3,2.8", c), ("C_pole_side", "C", ".3,.3,2.8", c + ["--lat", ".7"])]
        cases += [(f"pole{int(h * 10)}_{suffix}", "A", f".3,.3,{h}", a + ["--lat", str(lat)])
                  for h in (3.2, 3.6) for suffix, lat in [("c", 0), ("side", .7), ("sideN", -.7)]]
    summary = {}
    for name, bag, obj, args in cases:
        cache = "/data/decoded/" + BAGS[bag]
        prefix = str(OUT / name)
        state.update(case=name, calls=[])
        sys.argv = [range_test.__file__, cache, "/data/odometry/icp_" + BAGS[bag] + ".json", prefix,
                    "--obj", obj, *args]
        range_test.main()
        (OUT / (name + "-sight.json")).write_text(json.dumps(state["calls"]))
        data = json.loads(Path(prefix + ".json").read_text())
        summary[name] = data["summary"]
        summary[name]["matched_stop_frames"] = [r["k"] for r in data["rows"] if r["hit"]]
        (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
