#!/bin/sh
unset LD_LIBRARY_PATH
export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6
export LIBGL_DRIVERS_PATH=/usr/lib/x86_64-linux-gnu/dri
exec /home/omega/miniconda3/python /home/omega/noordunglabs/gps/sol.py
