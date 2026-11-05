
import json
import math
from pathlib import Path
from statistics import median

from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Parallel, Sequence
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    LineSegs,
    Point3,
)


def rotate_acceleration_to_world(ax, ay, az, yaw, pitch, roll):
    """
    Predpostavke:
    - koti so v stopinjah;
    - pospešek je podan v koordinatnem sistemu senzorja;
    - gravitacija je že odstranjena;
    - orientacija uporablja rotacijo yaw-pitch-roll (Z-Y-X).
    """
    yaw, pitch, roll = map(
        math.radians, (yaw, pitch, roll)
    )

    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)

    # R = Rz(yaw) @ Ry(pitch) @ Rx(roll)
    ax_world = (
        cy * cp * ax
        + (cy * sp * sr - sy * cr) * ay
        + (cy * sp * cr + sy * sr) * az
    )

    ay_world = (
        sy * cp * ax
        + (sy * sp * sr + cy * cr) * ay
        + (sy * sp * cr - cy * sr) * az
    )

    az_world = (
        -sp * ax
        + cp * sr * ay
        + cp * cr * az
    )

    return Point3(ax_world, ay_world, az_world)


def integrate_acceleration(samples):
    """
    Trapezna integracija pospeška v hitrost in položaj.
    Čas v vhodnih podatkih je v milisekundah.
    """
    if not samples:
        return []

    positions = [Point3(0, 0, 0)]
    velocity = Point3(0, 0, 0)

    accelerations = []

    for s in samples:
        a = rotate_acceleration_to_world(
            s["ax"], s["ay"], s["az"],
            s["yaw"], s["pitch"], s["roll"]
        )
        accelerations.append(a)

    for i in range(1, len(samples)):
        dt = (
            samples[i]["time"] - samples[i - 1]["time"]
        ) / 1000.0

        if dt <= 0:
            positions.append(Point3(positions[-1]))
            continue

        if dt > 1.0:
            # Velik časovni preskok: ne integriraj čez vrzel.
            velocity = Point3(0, 0, 0)
            positions.append(Point3(positions[-1]))
            continue

        a0 = accelerations[i - 1]
        a1 = accelerations[i]

        # Integracija pospeška -> hitrost.
        new_velocity = velocity + (a0 + a1) * (0.5 * dt)

        # Integracija hitrosti -> položaj.
        new_position = positions[-1] + (
            velocity + new_velocity
        ) * (0.5 * dt)

        new_position[2] = 0

        positions.append(new_position)
        velocity = new_velocity

    return positions


class SensorVisualization(ShowBase):
    def __init__(self):
        super().__init__()

        # --------------------------------------------------
        # SCENE
        # --------------------------------------------------
        self.setBackgroundColor(0.06, 0.07, 0.10, 1)
        self.disableMouse()

        self.camera.setPos(0, -15, 5)
        self.camera.lookAt(0, 0, 0)

        # Lighting
        ambient = AmbientLight("ambient")
        ambient.setColor((0.65, 0.65, 0.70, 1))
        ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_np)

        sunlight = DirectionalLight("sunlight")
        sunlight.setColor((1, 1, 1, 1))
        sunlight_np = self.render.attachNewNode(sunlight)
        sunlight_np.setHpr(-35, -50, 0)
        self.render.setLight(sunlight_np)

        # Ground grid
        self.create_grid()

        # --------------------------------------------------
        # PANDA
        # --------------------------------------------------
        self.panda = Actor(
            "models/panda-model",
            {"walk": "models/panda-walk4"},
        )
        self.panda.setScale(0.005)
        self.panda.setPos(0, 0, 0)
        self.panda.reparentTo(self.render)
        self.panda.loop("walk")

        # --------------------------------------------------
        # CAMERA CONTROLS
        # W/S: forward/backward
        # A/D: left/right
        # Q/E: up/down
        # Arrow keys: rotate
        # --------------------------------------------------
        self.camera_speed = 10.0
        self.camera_rotation_speed = 60.0

        self.keys = {
            "w": False,
            "s": False,
            "a": False,
            "d": False,
            "q": False,
            "e": False,
            "arrow_up": False,
            "arrow_down": False,
            "arrow_left": False,
            "arrow_right": False,
        }

        for key in self.keys:
            self.accept(key, self.set_key, [key, True])
            self.accept(key + "-up", self.set_key, [key, False])

        self.taskMgr.add(self.update_camera, "update_camera")

        # --------------------------------------------------
        # TRAJECTORY
        # --------------------------------------------------
        self.trail_points = []
        self.trail_node = None
        self.trail_update_distance = 0.03

        self.taskMgr.add(self.update_trail, "update_trail")

        # --------------------------------------------------
        # LOAD SENSOR DATA
        # --------------------------------------------------
        data_path = Path(__file__).resolve().parent / "DATA_LOG.json"

        with data_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        samples = []

        for row in data["I"]:
            try:
                samples.append({
                    "ax": float(row["linear_accel_x_mps2"]),
                    "ay": float(row["linear_accel_y_mps2"]),
                    "az": float(row["linear_accel_z_mps2"]),
                    "pitch": float(row["pitch_deg"]),
                    "roll": float(row["roll_deg"]),
                    "yaw": float(row["yaw_deg"]),
                    "time": float(row["time_ms"]),
                })
            except (KeyError, TypeError, ValueError):
                continue

        if not samples:
            raise ValueError("No valid sensor records in DATA_LOG.json")


        positions = integrate_acceleration(samples)

        # --------------------------------------------------
        # TIME INTERVALS
        # Assumes time_ms contains absolute timestamps.
        # --------------------------------------------------
        time_deltas = [
            (samples[i + 1]["time"] - samples[i]["time"]) / 1000.0
            for i in range(len(samples) - 1)
            if samples[i + 1]["time"] > samples[i]["time"]
        ]

        default_duration = median(time_deltas) if time_deltas else 0.02

        # --------------------------------------------------
        # BUILD ANIMATION
        # --------------------------------------------------
        intervals = []

        start_pos = Point3(0, 0, 0)
        start_hpr = Point3(0, 0, 0)

        for i, sample in enumerate(samples):
            if i < len(samples) - 1:
                duration = (
                    samples[i + 1]["time"] - sample["time"]
                ) / 1000.0
            else:
                duration = default_duration

            # Ignore invalid or excessively long intervals.
            if duration <= 0 or duration > 10:
                continue

            ax = sample["ax"]
            ay = sample["ay"]
            az = sample["az"]

            # Illustrative movement, not physical position reconstruction.
            # new_pos = start_pos + Point3(ax, ay, az) * duration
            new_pos = positions[i]


            # Panda3D HPR order: heading, pitch, roll.
            new_hpr = Point3(
                sample["yaw"],
                sample["pitch"],
                sample["roll"],
            )

            # Move and rotate at the same time.
            intervals.append(
                Parallel(
                    self.panda.posInterval(
                        duration,
                        new_pos,
                        startPos=start_pos,
                    ),
                    self.panda.hprInterval(
                        duration,
                        new_hpr,
                        startHpr=start_hpr,
                    ),
                )
            )

            start_pos = new_pos
            start_hpr = new_hpr

        if not intervals:
            raise ValueError("No valid animation intervals were created")

        self.animation = Sequence(
            *intervals,
            name="sensor_animation",
        )
        self.animation.loop()

    # ==================================================
    # GROUND GRID
    # ==================================================
    def create_grid(self):
        lines = LineSegs("ground_grid")
        lines.setThickness(1)
        lines.setColor(0.20, 0.24, 0.30, 1)

        grid_size = 50
        spacing = 1

        for i in range(-grid_size, grid_size + 1, spacing):
            lines.moveTo(i, -grid_size, -0.02)
            lines.drawTo(i, grid_size, -0.02)

            lines.moveTo(-grid_size, i, -0.02)
            lines.drawTo(grid_size, i, -0.02)

        grid_node = self.render.attachNewNode(lines.create())
        grid_node.setLightOff()

    # ==================================================
    # CAMERA
    # ==================================================
    def set_key(self, key, value):
        self.keys[key] = value

    def update_camera(self, task):
        dt = globalClock.getDt()

        movement = Point3(0, 0, 0)

        if self.keys["w"]:
            movement.y += 1
        if self.keys["s"]:
            movement.y -= 1
        if self.keys["a"]:
            movement.x -= 1
        if self.keys["d"]:
            movement.x += 1
        if self.keys["q"]:
            movement.z += 1
        if self.keys["e"]:
            movement.z -= 1

        if movement.lengthSquared() > 0:
            movement.normalize()
            movement *= self.camera_speed * dt

            self.camera.setPos(
                self.camera,
                movement.x,
                movement.y,
                movement.z,
            )

        hpr = self.camera.getHpr()
        rotation = self.camera_rotation_speed * dt

        if self.keys["arrow_left"]:
            hpr.x += rotation
        if self.keys["arrow_right"]:
            hpr.x -= rotation
        if self.keys["arrow_up"]:
            hpr.y += rotation
        if self.keys["arrow_down"]:
            hpr.y -= rotation

        self.camera.setHpr(hpr)

        return task.cont

    # ==================================================
    # TRAJECTORY TRAIL
    # ==================================================
    def update_trail(self, task):
        pos = self.panda.getPos(self.render)

        if (
            not self.trail_points
            or (pos - self.trail_points[-1]).length()
            >= self.trail_update_distance
        ):
            self.trail_points.append(Point3(pos))

            if self.trail_node is not None:
                self.trail_node.removeNode()

            if len(self.trail_points) >= 2:
                lines = LineSegs("trajectory")
                lines.setThickness(3)
                lines.setColor(0.1, 1.0, 0.4, 1)

                lines.moveTo(self.trail_points[0])

                for point in self.trail_points[1:]:
                    lines.drawTo(point)

                self.trail_node = self.render.attachNewNode(
                    lines.create()
                )
                self.trail_node.setLightOff()

        return task.cont


app = SensorVisualization()
app.run()
