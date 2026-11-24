#!/bin/bash
cd /tmp/vid
export OUTDIR=/tmp/vid/out3 PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
python3 render.py scene3 30 52 > renderA10_s3.log 2>&1
python3 render.py scene2 15 30 > renderA10_s2.log 2>&1
python3 render.py scene6 98 113 > renderA10_s6.log 2>&1
python3 render.py scene8 125 135 > renderA10_s8.log 2>&1
echo DONE > doneA10
