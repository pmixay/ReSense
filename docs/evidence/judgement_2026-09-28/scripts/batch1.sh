#!/usr/bin/env bash
# The repeat runs of the jury chain (the first obstacle run, obst_warm1, and the PLAYER_ARGS="" runs
# were started by hand with run_chain.sh).
cd "$(dirname "$0")"
for r in 2 3; do ./run_chain.sh doubleT_obstacle runs/obst_warm$r warm; done
for r in 1 2; do ./run_chain.sh doubleT_obstacle runs/obst_cold$r cold; done
for r in 1 2; do ./run_chain.sh roundT_doubleT runs/clear_warm$r warm; done
./run_chain.sh roundT_doubleT runs/clear_cold1 cold
