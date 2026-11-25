import subprocess
import sys
from pathlib import Path

import numpy as np
import rerun as rr

from src.navigation.rerun.config import *


DIR = RERUN_DIR + "get_started2.rrd"


def record_helix_flight() -> None:
    rr.init("helix_demo")
    rr.save(DIR)  # ? sink = file, replaces spawn()/connect_grpc()
    rr.log("world", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)
    rr.log("world/body/box", rr.Boxes3D(half_sizes=[0.2, 0.1, 0.05]), static=True)

    trajectory_points = []
    for step_index in range(200):
        time_seconds = step_index * 0.05
        position = np.array(
            [np.cos(time_seconds), np.sin(time_seconds), 0.1 * time_seconds]
        )
        trajectory_points.append(position)
        quaternion_xyzw = [0.0, 0.0, np.sin(time_seconds / 2), np.cos(time_seconds / 2)]

        rr.set_time("time", duration=time_seconds)
        rr.log(
            "world/body",
            rr.Transform3D(
                translation=position, quaternion=rr.Quaternion(xyzw=quaternion_xyzw)
            ),
        )
        rr.log("world/trajectory", rr.LineStrips3D([trajectory_points]))
        rr.log("plots/height", rr.Scalars(position[2]))

    rr.disconnect()  # ? flushes and closes the .rrd file


if __name__ == "__main__":
    record_helix_flight()
    subprocess.run([sys.executable, "-m", "rerun", str(DIR)], check=True)
