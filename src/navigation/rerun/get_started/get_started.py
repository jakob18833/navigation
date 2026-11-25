import math

import rerun as rr

from src.navigation.rerun.config import *

with rr.RecordingStream("application1", recording_id="recording1") as rec:
    rec.save(RERUN_DIR + "demo.rrd")
    for t in range(10):
        rec.set_time("timeline1", sequence=t)
        rec.set_time("timeline2", timestamp=t/2)
        rec.log("/entity1/component1", rr.Scalars(math.sin(t * 0.5)))
        rec.log("/entity1/component2", rr.Scalars(-math.sin(t * 0.5)))
        rec.log("/entity2/component3", rr.Scalars(math.cos(t * 0.5)))


