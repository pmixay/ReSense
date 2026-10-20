#!/bin/bash
# Regenerates every out/*.txt of the final-bundle review from the committed archives.
#   usage:  run_all.sh <work dir>          (run from the repository checkout at f56ad5e or a later docs-only commit)
# Needs: python3 with numpy, scipy, pyyaml, scikit-learn (and pytest + open3d for the node/proxy controls).
# Nothing under resense/ native/ configs/ or the ROS package is touched; PYTHONPATH is the checkout.
set -u
W=${1:?work dir}; R=$PWD; E=$R/docs/evidence; D=$E/p4_review_final_bundle_2026-10-20; S=$D/scripts; O=$D/out
mkdir -p "$W/r3" "$W/h1" "$W/p4f" "$O"
export PYTHONPATH=$R OMP_NUM_THREADS=1 OPENBLAS_CORETYPE=Haswell RESENSE_REPO=$R
PY="python3"
[ -f "$W/r3/.done" ] || { tar xzf $E/r3_completion_2026-10-20/raw-replay.tar.gz -C "$W/r3" && tar xzf $E/r3_completion_2026-10-20/raw-controls.tar.gz -C "$W/r3" && touch "$W/r3/.done"; }
[ -f "$W/h1/.done" ] || { tar xzf $E/h1_partial_integration_2026-10-20/raw-evidence.tar.gz -C "$W/h1" && touch "$W/h1/.done"; }
M=$E/p4_review_r3_h1_2026-10-20/out/main_f56ad5e
[ -f "$W/p4f/.done" ] || { (cd "$W/p4f" && tar xJf $M/gatework_default.tar.xz && tar xJf $M/x3_raw_default.tar.xz && xz -dc $M/falcon/default.jsonl.xz > falcon_default.jsonl && touch .done); }
cd $S
{ $PY identity.py hashes "$W/r3" $E/r3_completion_2026-10-20/raw-manifest.json; $PY identity.py hashes "$W/h1" $E/h1_partial_integration_2026-10-20/raw-manifest.json; } > $O/01_archive_hashes.txt 2>&1
( cd $R; { echo "== R3 archives (candidate must equal f56ad5e; the reference is the base 5fa865b = positive control)"; $PY $S/identity.py source "$W/r3" f56ad5e 5fa865b;
           echo "== H1 archives (measured on 0f02b28)"; $PY $S/identity.py source "$W/h1" 0f02b28 f56ad5e;
           echo "== tree identity"; for r in f56ad5e 0a472d6 47b220c HEAD; do echo "$r $(git ls-tree -r $r -- resense native configs setup.py pyproject.toml ros2_ws/src/resense_ros/config | sha256sum | cut -c1-64)"; done;
           echo "== seal"; $PY scripts/detector_freeze.py verify; } > $O/02_source_identity.txt 2>&1 )
{ $PY compare_rows.py gate "$W/r3/gate-a-candidate" "$W/r3/gate-a-reference" "gate: R3 candidate vs fresh base replay";
  $PY compare_rows.py gate "$W/r3/gate-a-candidate" "$W/r3/gate-a-reference" "gate" --control;
  $PY compare_rows.py x3 "$W/r3/x3-a-candidate.raw" "$W/r3/x3-a-reference.raw" "X3: R3 candidate vs fresh base replay";
  $PY compare_rows.py x3 "$W/r3/x3-a-candidate.raw" "$W/r3/x3-a-reference.raw" "X3" --control;
  $PY compare_rows.py jsonl "$W/r3/falcon-a-candidate.jsonl" "$W/r3/falcon-a-reference.jsonl" "Falcon: R3 candidate vs fresh base replay";
  $PY compare_rows.py jsonl "$W/r3/falcon-a-candidate.jsonl" "$W/r3/falcon-a-reference.jsonl" "Falcon" --control; } > $O/03_rows_p3_pairs.txt 2>&1
{ echo "== gate: P3 candidate vs P4's own run on f56ad5e"; $PY cross_run_fields.py gate "$W/r3/gate-a-candidate" "$W/p4f/gate_default";
  echo "== X3: P3 candidate vs P4's own run on f56ad5e"; $PY cross_run_fields.py x3 "$W/r3/x3-a-candidate.raw" "$W/p4f/x3_default.raw";
  echo "== Falcon: P3 candidate vs P4's own stream on f56ad5e"; $PY cross_run_fields.py jsonl "$W/r3/falcon-a-candidate.jsonl" "$W/p4f/falcon_default.jsonl"; } > $O/04_rows_p3_vs_p4_runs.txt 2>&1
( cd $R; $PY $S/gate_metrics.py "$W/r3" $E/r3_completion_2026-10-20 $M/gate_default.json ) > $O/05_gate_metrics.txt 2>&1
$PY setf_rows.py "$W/r3/gate-a-candidate/setF_straight.json" "$W/r3/gate-a-reference/setF_straight.json" > $O/06_setF_rows.txt 2>&1
{ $PY x3_entries.py "$W/r3/x3-a-candidate.json" "$W/r3/x3-a-candidate.raw"; } > $O/07_x3_entries.txt 2>&1
$PY junit_audit.py "$W/r3/tests-a-candidate.xml" "$W/r3/tests-merged-candidate.xml" "$W/r3/diagnose-merged-candidate.xml" "$W/r3/diagnose-merged-reference.xml" "$W/r3/integrity-tests.xml" > $O/08_junit.txt 2>&1
( cd $R; bash $S/proxy_hook_control.sh ) > $O/09_proxy_hook_control.txt 2>&1
( cd $R/docs/evidence/p4_review_shipping_2026-10-20/scripts && PYTHONPATH=$R:. $PY ../../p4_review_r3_h1_2026-10-20/scripts/b2_yaml.py $R/configs/default.yaml > $O/10_b2_here.txt 2>&1;
  diff $O/10_b2_here.txt $E/p4_review_r3_h1_2026-10-20/out/b2_yaml_main_f56ad5e.txt > /dev/null && echo "IDENTICAL to p4_review_r3_h1_2026-10-20/out/b2_yaml_main_f56ad5e.txt ($(wc -l < $O/10_b2_here.txt) lines)" >> $O/10_b2_here.txt || echo "DIFFERS" >> $O/10_b2_here.txt )
{ echo "== H1 archive X3 (0f02b28) vs R3 candidate X3 (f56ad5e)"; $PY cross_run_fields.py x3 "$W/h1/x3.raw" "$W/r3/x3-a-candidate.raw"; } > $O/11_h1_x3_to_final.txt 2>&1
$PY analytic_rows.py "$W/r3/analytic-a-candidate.json" "$W/r3/analytic-a-reference.json" > $O/15_analytic_rows.txt 2>&1
( cd $R; $PY $S/n5_final_scoring.py ) > $O/16_n5_final_scoring.txt 2>&1
$PY x3_entries.py "$W/h1/x3.json" "$W/h1/x3.raw" > $O/19_h1_x3_entries.txt 2>&1
$PY e6_rows.py "$W/r3/range-a-candidate.json" "$W/r3/range-a-reference.json" > $O/18_e6_rows.txt 2>&1
# out/12 (H1 physical replay) needs ~3 min per run and is made by:  python3 docs/evidence/h1_reference_2026-10-19/physical_e.py --baseline <h1 archive physical.json> --out <file>
#   with RESENSE_REPO=PYTHONPATH=<checkout>; the two reports used are out/runs/h1_physical_*_py313.json.xz; compare with scripts/physical_compare.py.
# out/13 (node delay), out/14 (quiet timing), out/17 (full suite) were run by hand: see the README, section "Reproduce".
sed -i "s#$W#<work>#g; s#$R/#<repo>/#g" $O/*.txt
echo finished
