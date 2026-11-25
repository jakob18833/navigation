import subprocess
import sys

import numpy as np
import rerun as rr

from src.navigation.rerun.config import *

PATH = RERUN_DIR + "get_started3.rrd"


def task():
    rr.init("get_started3")
    rr.save(PATH)
    rr.log("world", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)
    rr.log("world/car", rr.Boxes3D(half_sizes=[0.5, 0.1, 0.1]), static=True)
    rr.log("world/car/sensor", rr.Ellipsoids3D(half_sizes=[0.1, 0.1, 0.1], colors=[255, 0, 0]), static=True)


    radius = 5
    offset = np.array([0, 0, 0.5])

    for t in np.linspace(0, 10, 500):
        rr.set_time("time", duration=t)

        position = np.array([np.cos(t)*radius, np.sin(t)*radius, 0])
        rotation = rr.RotationAxisAngle([0, 0, 1], t)
        rr.log("world/car", rr.Transform3D(
            translation=position,
            rotation=rotation
        ))
        rr.log("world/car/sensor", rr.Transform3D(
            translation=offset,
            rotation=rotation
        ))


    blueprint = rr.blueprint.Grid(
        rr.blueprint.Spatial3DView(
            name="Main view",
            origin="/",
            eye_controls=rr.blueprint.EyeControls3D(
                position=[0, -10, 10],
                look_target=[0.0, 0.0, 0.0],
                eye_up=[0.0, 0.0, 1.0],
            ),
        ),
    )
    rr.send_blueprint(blueprint, make_active=True)

    rr.disconnect()

if __name__ == "__main__":
    task()
    subprocess.run([sys.executable, "-m", "rerun", str(PATH)], check=True)
