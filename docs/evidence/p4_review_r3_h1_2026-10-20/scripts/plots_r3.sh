#!/bin/bash
W=/home/user/wt_ship; O=/home/user/p4r/png; mkdir -p $O
export PATH=/home/user/venv/rs/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$W PYTHONPATH=$W
cd $W
python /home/user/p4r/scripts/plot_frame.py /home/user/data/cache cloud_with_fake_obj -1 785,786,788 $O/setO_786_788_r3_on.png --d 34 --win 6 --title "R3 on (shipped)"
python /home/user/p4r/scripts/plot_frame.py /home/user/data/cache cloud_with_fake_obj -1 785,786,788 $O/setO_786_788_r3_off.png --d 34 --win 6 --set tracking.cable_confirm_time_s=0 --title "R3 off"
echo PLOTS_DONE
