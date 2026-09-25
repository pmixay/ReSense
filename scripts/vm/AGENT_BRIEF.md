# VM Run Kit: Agent Brief

> **Purpose:** what a Claude Code session on the team's temporary Yandex Cloud VM runs, in order,
> and how the results come back into the repository: the 8-core bench, the dry run with the
> original bags, the host-console player, the regression gate over every real frame, the image
> export and the offline rehearsal.
> **Audience:** the agent on the VM, P1, anyone running the same commands by hand · **Owner:** P1 ·
> **Language:** EN
> **Last verified:** 2026-09-25 against `2b3cbd0` (every script run in dry mode in the dev sandbox;
> the gate's fallback run for real on the six recordings and set O; not yet run on the VM) ·
> **Status:** current

## 0. Why this VM, and what it must produce

The organizers' test machine (i7-9700E, 8 cores, RTX 4070 Ti SUPER, Ubuntu 22.04, ROS 2 Humble,
Docker) has **no internet** and the team gets **no access** to it before the upload
([`../../docs/organizers/answers.md`](../../docs/organizers/answers.md) §6–§7). The dev sandbox
has no Docker daemon and too little disk for the 20-minute ride. This VM is the only place for:

| run | kit command | board item it closes |
|---|---|---|
| 8-core bench, native and numpy kernels | `run_plan.sh bench` | CAPTAIN action 7, C8 |
| clean-machine dry run with the **original** bags | `run_plan.sh dryrun` | action 15 rehearsal, C7 |
| `ros2 bag play` from the host console, stock Fast DDS (and CycloneDDS) | `run_plan.sh dryrun` (steps `host_*`) | C4 |
| regression gate over all 13 759 real frames incl. the ride | `run_plan.sh gate [--ref <branch>]` | action 11 (P3 / P4 go / no-go) |
| image archive + sha256 | `run_plan.sh export [--ref <tag>]` | actions 14b, 16 |
| offline rehearsal: archive loaded and run with outbound internet blocked | `run_plan.sh offline` | C25, action 15 |

All commands below run from the checkout (`~/ReSense`). Every run writes
`~/resense_results/<date>/<subcommand>/` (`result.txt` says PASS / FAIL per step; `run_log.txt` has
everything). A failing criterion is a **finding to report**, not something to fix on the VM.

## 1. Before the session (the human, once)

* **VM**: Ubuntu **22.04** image (24.04 has no ROS 2 Humble packages: the kit then runs
  Docker-only and C4 cannot be shown). For C8, 16 vCPU at 100 % core fraction = 8 physical cores
  (a Yandex Cloud vCPU is one hyper-thread: 8 vCPU are 4 cores); 16 GB RAM or more. Free disk
  (Docker's 8 GiB reserve included): ~32 GiB covers the dry-run bags and every cache except the
  ride's, ~40 GiB adds the ride's cache (the full gate), ~65 GiB keeps all six bags too, ~150 GiB
  the 90 GB ride bag as well (a 20-minute replay); `scripts/vm/fetch_data.sh --plan
  --assume-free-gb N` sizes it.
* **Serial console**: enable it in the VM's settings in the Yandex Cloud console. It is the way
  in if SSH ever breaks (the offline step is built not to break it, §5).
* Work inside `tmux` (installed by the setup): long runs survive a dropped SSH connection.
* **Claude Code** (official installer, one line), then log in with the URL it prints:

  ```bash
  curl -fsSL https://claude.ai/install.sh | bash && claude
  ```

  (or `npm install -g @anthropic-ai/claude-code` with Node.js 18+). Give it the task:
  *"Read scripts/vm/AGENT_BRIEF.md in ~/ReSense and carry it out, step by step."*
* **GitHub** for the result PR: `sudo apt-get install -y gh && gh auth login && gh auth setup-git`
  (a personal login stays on the VM; never commit it). A private repository needs this before
  the clone, or `GITHUB_TOKEN=<token>` for `setup_vm.sh`.

## 2. Task list, in order

Times are rough, for 8–16 vCPU. "Done" is what to check before the next step.

**T1. Setup (15–25 min).**

```bash
git clone --branch claude/nifty-pascal-lzgl78 https://github.com/pmixay/ReSense ~/ReSense
~/ReSense/scripts/vm/setup_vm.sh            # --registry-mirror https://mirror.gcr.io if Docker Hub fails
newgrp docker   # or log out and in again; run_plan.sh also re-execs itself with 'sg docker'
source ~/resense_env.sh && cd ~/ReSense
```

Done: the summary ends with `READY`; `ros` says `OK` (on 24.04: `SKIPPED ... Docker-only mode`);
`native` shows the C++ kernels. It detects CPU / RAM / disk and warns when the VM is not an 8-core
analogue or has a spare unmounted disk (it prints the mount commands; it never formats a disk).

**T2. Data (1–2 h, in tmux).**

```bash
scripts/vm/fetch_data.sh --plan             # what fits on this disk
scripts/vm/fetch_data.sh                    # re-run to resume; finished items are skipped
```

Done: `DATA READY`; the inventory shows the bags `doubleT_obstacle` and `roundT_doubleT`, caches
of all six recordings and `cloud_with_fake_obj`, and `new_data` 221 of 221 split files (or the
plan says why the ride was skipped: then the gate in T5 is not the full go / no-go). If Google
Drive refuses the download, copy `Датасет.zip` over (`scp`) and run with `DATASET_ZIP=<path>`.

**T3. Dry run with the original bags, host console (20–35 min).**

```bash
scripts/vm/run_plan.sh dryrun
```

Runs `scripts/dry_run.sh` (a `--no-cache` build, i.e. the clean machine) on `doubleT_obstacle`,
then on `roundT_doubleT --expect-clear --max-alarm-frames 2`, `scripts/console_test.sh` (player as
uid 1000 from the image, and with `PLAYER_DDS=stock` where the script supports it), then the
organizers' console: the node container on its default command and **`ros2 bag play` +
`ros2 topic echo /resense/decision` from the host** as this user, with the stock RMW
(`rmw_fastrtps_cpp`, no XML profile) and again with `rmw_cyclonedds_cpp`. Plays the whole ride
too when its bag is kept (`RIDE_REPLAY=0` skips it). Done: `result.txt` PASS for
`original_bags`, `dry_obstacle` (person at 50–62 m in ≥ 3 frames, p95 ≤ 100 ms, no frame dropped
after 5 s), `dry_clear`, `console_*`, `host_fastdds` (C4). A latency or drop failure on this VM is
a result to record with the vCPU count, not a reason to change code.

**T4. 8-core bench (20–30 min).**

```bash
scripts/vm/run_plan.sh bench
```

Uses `scripts/bench_8core.sh` when the branch has it (the node on the native kernels and on
numpy, `console_test.sh` with the image's and the stock DDS, `docker stats`, host timing;
`bench/bench_<date>/summary.txt`), otherwise a fallback (build, `dry_run.sh` with `docker stats`,
`bench_node_path.py` and `resense bench` on the host with `RESENSE_NATIVE=1` and `0`) and says so
in `result.txt`. Keep the VM otherwise idle. Done: `result.txt` and the per-run numbers; the
notes state vCPU / physical cores and the CPU steal measured before the runs.

**T5. Regression gate (10–40 min per run).**

```bash
scripts/vm/run_plan.sh gate                              # HEAD: the committed baseline must reproduce here
scripts/vm/run_plan.sh gate --ref <P3 or P4 branch>      # each late-change candidate (action 11)
GATE_PATHS="native numpy" scripts/vm/run_plan.sh gate    # optional: both kernel paths
```

Uses `scripts/regression_gate.py` with the newest `docs/evidence/results/regression_baseline_*.json`
when the branch has them (exit 0 identical or better, 1 a gated metric worse, 2 missing data);
otherwise `scripts/eval_real.py` + `scripts/score_fake_objects.py` without a comparison (the note
says so: compare with EXPERIMENTS "Current results" by hand). `--ref` checks the candidate out in
its own worktree (`~/resense_ref/`), builds its kernels, and runs the same caches. Done: HEAD is
PASS (identical); each candidate has its `result.txt` and, if worse, the rows that are worse; the
note says the ride was included (221 split files).

**T6. Image archive (15–20 min, needs the internet).**

```bash
scripts/vm/run_plan.sh export                        # rehearsal: HEAD as <version>-<sha>
scripts/vm/run_plan.sh export --ref v1.0.0-rc1       # after the tag (action 14b); --ref v1.0.0 on 29.09
```

Calls `scripts/export_image.sh` (clean `--no-cache` build from `git archive`, gzip, `.sha256`) into
`~/resense_dist/`, then `scripts/load_image.sh` on it. `--ref` builds from a clean clone of the tag.
A dirty checkout is refused by `export_image.sh`: commit first, or use `--ref`. Done: `archive.txt`
with the size and the sha256, `load_check` PASS. Since 25.09 a pushed `v1.0.0-rcN` / `v1.0.0` tag
also gets its archive published by `.github/workflows/release.yml`; `scripts/verify_release.sh
<tag>` fetches it into `dist/` with its sum checked, and this task is then the cross-check.

**T7. Offline rehearsal (10–20 min; after T6).**

```bash
scripts/vm/run_plan.sh offline --minutes 30 --allow-host api.anthropic.com   # the agent
scripts/vm/run_plan.sh offline --minutes 30                                    # a human in tmux: nothing allowed
```

Blocks all outbound traffic (§5), checks that the internet is unreachable
(`scripts/check_no_network.py` on the host), removes the `resense` images, loads the newest
archive with `scripts/load_image.sh`, runs `dry_run.sh` with `OFFLINE=1` (`--network none`) on both
bags, then the README jury commands from the host console (`docker run ... resense`,
`ros2 bag play`, `ros2 topic echo /resense/decision`), records what tried to go out
(`blocked_attempts.txt`), and restores the network. **The agent's own connection:** without
`--allow-host api.anthropic.com` the session cannot reach the API until the restore (at most
`--minutes`); with it, only DNS and HTTPS to that host stay open, and `result.txt` says so. Done:
PASS for `verify_blocked`, `load_image`, `dry_obstacle`, `dry_clear`, `jury_console`;
`window.txt` ends with `restored` and GitHub answering again.

**T8. Collect (1 min).**

```bash
scripts/vm/run_plan.sh collect --to-repo
```

Packs `~/resense_results_<date>.tar.gz` with `summary.md` (keep it: it is the copy to download if
the PR goes wrong) and copies each run into `docs/evidence/<name>_<date>/` in the checkout
(`*.log` renamed `*_log.txt`, `*.jsonl` gzipped, files over 20 MB and the gate's work directories
dropped). Nothing is committed yet. `summary.md` lists files that look like personal data.

**T9. Commit the evidence (PR only).** See §3. Done: a PR is open and its description holds
`summary.md`'s table.

`scripts/vm/run_plan.sh all` runs T3–T8 in a row (for a human in tmux; it asks for the SSH check
in T7 when it has a terminal). `scripts/vm/run_plan.sh status` shows what is installed, fetched,
built and measured at any time.

## 3. Bringing the results back

```bash
git fetch origin && git switch -c vm/evidence-$(date +%F) origin/claude/nifty-pascal-lzgl78
git add docs/evidence/*_$(date +%F)
```

| folder (from `collect --to-repo`) | edit | how |
|---|---|---|
| `docs/evidence/bench_<date>/` | [`EXPERIMENTS.md`](../../docs/EXPERIMENTS.md) §3 | append one subsection "8-core bench on the team VM (<date>)": machine (CPU model, vCPU / physical cores, RAM), the table of fps, latency mean / p95 / max, dropped frames, CPU %, memory, native vs numpy; P1 appends timing only |
| same | [`CAPTAIN.md`](../../docs/CAPTAIN.md) C8, action 7 | DONE only with ≥ 8 physical cores; otherwise PARTIAL with the core count; link the folder |
| `docs/evidence/dry_run_<date>/` | [`SUBMISSION.md`](../../docs/SUBMISSION.md) "Dry run" | one paragraph: date, VM, original bags, each criterion's number, PASS / FAIL |
| same | CAPTAIN C7, C4, action 15 | C7 = the dry run on the original bags; C4 = `host_fastdds` (and `host_cyclonedds`); action 15 stays open for 28.09 unless that was the run |
| `docs/evidence/offline_<date>/` | CAPTAIN C25; SUBMISSION "Dry run" | the offline result, what was allowed (`--allow-host`), the blocked attempts |
| `docs/evidence/export_<date>/` | CAPTAIN actions 14b / 16, §5 | size and sha256 of the archive (never commit the archive) |
| `docs/evidence/gate_<date>/` | CAPTAIN action 11 | the numbers only; the go / no-go itself is the human captain's decision (§9) |
| `docs/evidence/vm_<date>/` | — | machine facts, data plan and inventory |
| all | [`../../docs/evidence/README.md`](../../docs/evidence/README.md) §2 | one short subsection per new folder: how it ran and the result |

Then `git commit` (message: what ran, where, the headline result), `git push -u origin
vm/evidence-<date>`, `gh pr create --base claude/nifty-pascal-lzgl78` (or the base the captain
names). Numbers go into the docs exactly as the evidence has them; if a number disagrees with
EXPERIMENTS "Current results", say so in the PR instead of editing the current results.

## 4. Rules

* **PR only.** Never push to `main`, never force-push, never merge your own PR (the captain merges
  after CI is green and another lane reviewed it; CAPTAIN §6).
* **Freeze** (CAPTAIN §6): detector and config 26.09 20:00, docs 27.09 20:00, from 28.09 blockers
  only, last merge 29.09 12:00. Evidence of the planned runs (actions 14b, 15, 16) is expected
  after the docs freeze; nothing else is.
* **Lanes.** This session adds evidence and edits the P1 rows above. It does not change
  `resense/`, `configs/`, `native/`, `labels/`, `docs/evidence/results/`, `web/`, the deck or the
  tests; a finding for another lane goes into the PR description.
* **No personal data** in commits: names, e-mails, tokens, SSH keys, IP addresses, the VM's
  public address, team photos (`docs/presentation/private/` is git-ignored). Check the list at the
  end of `summary.md`. Never commit `~/.resense_vm.env`, bags, caches, `*.npy`, `*.db3`, the image
  archive or the gate's work directories.
* **Never** apply the offline block by other means than `run_plan.sh offline`, and never stop its
  timer while the block is on.
* Report failures as they are: a FAIL row is evidence too.

## 5. How the offline rehearsal avoids locking anyone out

1. **The restore is armed before anything is blocked**: a transient systemd timer
   (`resense-offline-restore.timer`, `--minutes`, default 30, at most 180) runs
   `/var/lib/resense-offline/restore.sh`, whatever happens to the script or the SSH session; if
   systemd cannot arm it, a detached `sleep; restore` does; if neither works, nothing is blocked.
2. **Only outbound traffic is filtered, in one own chain** (`RESENSE_OFFLINE`, first in `OUTPUT`;
   `RESENSE_OFFLINE_FWD` in `DOCKER-USER` for bridge containers; the same for IPv6). `INPUT` is not
   touched, so a new SSH login still arrives; its replies pass because the chain accepts
   `ESTABLISHED,RELATED` and anything from sshd's ports (read from `sshd -T` and `$SSH_CONNECTION`).
   Loopback, DDS discovery multicast (224.0.0.0/4, so the host player finds the node), the cloud
   metadata service (169.254.169.254: OS Login keys) and DHCP stay open; everything else is logged
   (rate-limited) and rejected at once (no hanging tools).
3. **Restored on every exit** of the script (normal end, error, Ctrl-C, SIGHUP of a dropped
   session), and the timer is then stopped. The rules are never saved: a **reboot** from the cloud
   console also clears them.
4. **Checked, not assumed**: after the block the host must fail `scripts/check_no_network.py`,
   otherwise the rehearsal stops (and restores); in a terminal it asks you to open a second SSH
   session and type `yes` within 120 s, else it restores at once. After the restore it records
   whether GitHub answers again.
5. **By hand at any time**: `scripts/vm/run_plan.sh restore-network`, or
   `sudo sh /var/lib/resense-offline/restore.sh`; `run_plan.sh status` shows whether a block is on.

## 6. Run it by hand

```bash
git clone --branch claude/nifty-pascal-lzgl78 https://github.com/pmixay/ReSense ~/ReSense
~/ReSense/scripts/vm/setup_vm.sh && newgrp docker
source ~/resense_env.sh && cd ~/ReSense && tmux new -s resense
scripts/vm/fetch_data.sh --plan && scripts/vm/fetch_data.sh
scripts/vm/run_plan.sh dryrun
scripts/vm/run_plan.sh bench
scripts/vm/run_plan.sh gate                         # and: gate --ref <candidate branch>
scripts/vm/run_plan.sh export                       # and after the rc1 tag: export --ref v1.0.0-rc1
scripts/vm/run_plan.sh offline --minutes 30         # answer 'yes' from a second SSH session
scripts/vm/run_plan.sh collect --to-repo            # then §3
```

Every script takes `--help`; `-n` (or `DRY_RUN=1`) prints the commands without running them.

## 7. When something goes wrong

| symptom | what to do |
|---|---|
| `permission denied ... docker.sock` | `newgrp docker` or a new login (the setup added you to the group) |
| the base image cannot be pulled | `setup_vm.sh --registry-mirror https://mirror.gcr.io`, then re-run the step |
| Google Drive answers with a page | download `Датасет.zip` elsewhere, `scp` it, `DATASET_ZIP=~/Датасет.zip scripts/vm/fetch_data.sh` |
| disk full / ride skipped | `fetch_data.sh --plan --assume-free-gb N`; attach a disk, mount it at `/data` (setup prints how), re-run |
| the ride stream broke off | re-run `fetch_data.sh`: cached split files are skipped |
| offline block still on | `scripts/vm/run_plan.sh restore-network`; else `sudo sh /var/lib/resense-offline/restore.sh`; else reboot from the cloud console |
| Ubuntu 24.04 | Docker-only mode: T3's host steps are skipped and C4 stays open; everything else runs |
| a step FAILs | keep its folder; the step's own `<step>.txt` and `run_log.txt` have the output; report it in the PR |
