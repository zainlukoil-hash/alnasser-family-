#!/bin/bash
cd /tmp/vid
export OUTDIR=/tmp/vid/out3 PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
python3 render.py scene5 70 98 > renderB10_s5.log 2>&1
python3 render.py scene4 52 70 > renderB10_s4.log 2>&1
python3 render.py scene7 113 125 > renderB10_s7.log 2>&1
python3 render.py scene1 0 15 > renderB10_s1.log 2>&1
echo DONE > doneB10
