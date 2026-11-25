""" ? Euler angles -> unit quaternions in Rerun's (x, y, z, w) component order."""

import math


def intrinsic_zyx_angles_to_quaternion_xyzw(
    angle_about_z_radians: float,
    angle_about_y_radians: float,
    angle_about_x_radians: float,
) -> list[float]:
    """ ? Rotate about Z, then about the rotated Y, then about the twice-rotated X
    (the aerospace yaw -> pitch -> roll order). Returns [x, y, z, w]."""
    cos_z, sin_z = math.cos(angle_about_z_radians / 2), math.sin(angle_about_z_radians / 2)
    cos_y, sin_y = math.cos(angle_about_y_radians / 2), math.sin(angle_about_y_radians / 2)
    cos_x, sin_x = math.cos(angle_about_x_radians / 2), math.sin(angle_about_x_radians / 2)
    return [
        sin_x * cos_y * cos_z - cos_x * sin_y * sin_z,
        cos_x * sin_y * cos_z + sin_x * cos_y * sin_z,
        cos_x * cos_y * sin_z - sin_x * sin_y * cos_z,
        cos_x * cos_y * cos_z + sin_x * sin_y * sin_z,
    ]
