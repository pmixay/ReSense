#!/bin/bash
# resume Датасет.zip from the team storage (URL in /home/user/tools/.team_url, outside the repository)
U=$(cat /home/user/tools/.team_url)
for k in 1 2 3 4 5; do curl -fsSL -C - -o /data/dataset.zip "$U" && break; echo "attempt $k failed" >> /data/acc/team_dl.log; sleep 10; done
ls -l /data/dataset.zip >> /data/acc/team_dl.log
sha256sum /data/dataset.zip >> /data/acc/team_dl.log
echo DONE >> /data/acc/dl_zip.log
