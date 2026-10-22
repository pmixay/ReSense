#!/bin/bash
# restartable: six caches, then the final-tree Pandar rows, then gate / ICP / range / X3
[ -f /data/acc/six.log ] && grep -q SIX_DONE /data/acc/six.log || /home/user/tools/six.sh > /data/acc/six.log 2>&1
/home/user/tools/fin_pandar.sh > /data/acc/fin_pandar.log 2>&1
/home/user/tools/rest.sh > /data/acc/rest.log 2>&1
