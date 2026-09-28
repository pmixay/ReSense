#!/usr/bin/env bash
cd /home/user/judge
for r in 1 2 3; do for img in base464 latest; do IMAGE=resense:$img ./run_chain2.sh doubleT_obstacle ab/${img}_obst_warm$r warm; done; done
for r in 1 2; do for img in base464 latest; do IMAGE=resense:$img ./run_chain2.sh doubleT_obstacle ab/${img}_obst_cold$r cold; done; done
for img in base464 latest; do IMAGE=resense:$img ./run_chain2.sh roundT_doubleT ab/${img}_clear_warm1 warm; done
for img in base464 latest; do IMAGE=resense:$img ./run_chain2.sh roundT_doubleT ab/${img}_clear_cold1 cold; done
for img in base464 latest; do PLAYER_ARGS="" IMAGE=resense:$img ./run_chain2.sh doubleT_obstacle ab/${img}_obst_plain1 warm; done
echo AB DONE
