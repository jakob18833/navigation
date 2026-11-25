import os

RERUN_DIR = "recordings/"


DIRS = [RERUN_DIR,]

for dir in DIRS:
    if not os.path.exists(dir):
        os.makedirs(dir)



APPLICATION_ID = "navigation"