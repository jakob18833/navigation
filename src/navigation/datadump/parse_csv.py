""" ? Parse a NAV_BOX SD-card log (DATA_LOG) into one column table per sensor.

The firmware (NAV_BOX/Core/Src/main.c, sd_store()) appends one CSV row per sample,
the first field being a sensor tag:

    G,time_ms,fix_type,satellite_count,latitude_deg,longitude_deg,altitude_m
    I,accel_x,accel_y,accel_z,pitch_deg,roll_deg,yaw_deg,time_ms
    B,temperature_c,pressure_pa,time_ms

time_ms is HAL_GetTick(): milliseconds since power-on, captured when the sample was
read. Rows reach the file later, in main-loop order, so file order is not time order
across sensors. Each table is therefore sorted by time_ms here.
"""
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# ? u-blox gpsFix values that carry a position: 2 = 2D, 3 = 3D, 4 = GPS + dead reckoning.
POSITION_FIX_TYPES = frozenset({2, 3, 4})

# ? Values outside these limits cannot come from the BNO055; they are I2C read errors
# ? where bit 7 of one byte reads as 0 (e.g. +327.68 m/s^2, +2048 deg), see main.c.

MAX_ACCEL = sys.float_info.max
IMU_PLAUSIBLE_VALUE_LIMITS = {
    "linear_accel_x_mps2": (-MAX_ACCEL, MAX_ACCEL),  # ? ±10 g, the sensor's widest range
    "linear_accel_y_mps2": (-MAX_ACCEL, MAX_ACCEL),
    "linear_accel_z_mps2": (-MAX_ACCEL, MAX_ACCEL),
    "pitch_deg": (-180.0, 180.0),
    "roll_deg": (-180.0, 180.0),
    "yaw_deg": (0.0, 360.0),
}


@dataclass(frozen=True)
class SensorRowFormat:
    """ ? How one tagged row maps to named, typed columns (listed in file order)."""

    sensor_name: str
    columns: tuple[tuple[str, type], ...]


ROW_FORMAT_BY_TAG = {
    "G": SensorRowFormat("gps", (
        ("time_ms", int),
        ("fix_type", int),
        ("satellite_count", int),
        ("latitude_deg", float),
        ("longitude_deg", float),
        ("altitude_m", float),
    )),
    "I": SensorRowFormat("imu", (
        ("linear_accel_x_mps2", float),
        ("linear_accel_y_mps2", float),
        ("linear_accel_z_mps2", float),
        ("pitch_deg", float),
        ("roll_deg", float),
        ("yaw_deg", float),
        ("time_ms", int),
    )),
    "B": SensorRowFormat("baro", (
        ("temperature_c", float),
        ("pressure_pa", int),
        ("time_ms", int),
    )),
}




def parse_data_log(log_path: Path):
    """ ? Read every row of log_path; rows that do not match their tag's format are
    only counted (by line number), never guessed at. A power cut typically leaves
    one truncated last line."""

    rows_by_tag: dict[str, list[dict]] = {tag: [] for tag in ROW_FORMAT_BY_TAG}
    malformed_line_numbers: list[int] = []

    # 1. parse csv
    print(log_path)
    with log_path.open(encoding="utf-8-sig", errors="replace", newline="") as log_file:
        for line_number, line in enumerate(log_file, start=1):
            fields = [field.strip() for field in line.split(",")]
            if fields == [""]:
                continue
            tag = fields[0].upper()
            row_format = ROW_FORMAT_BY_TAG.get(tag)
            converted_row = convert_row(fields[1:], row_format) if row_format else None
            if converted_row is None:
                malformed_line_numbers.append(line_number)
                continue
            rows_by_tag[tag].append(converted_row)

    # 2. sort, handle invalid data 
    rows_by_tag = { tag: sorted(rows, key=lambda x: x["time_ms"]) for tag, rows in rows_by_tag.items() }
    gps, gps_dropped = blank_positions_without_fix(rows_by_tag["G"], drop=False) 
    imu, imu_dropped = blank_impossible_imu_values(rows_by_tag["I"], drop=False) 
    print(f"Dropped {gps_dropped} GPS packets due to fix type")
    print(f"Dropped {imu_dropped} IMU packets due to invalid number")

    rows_by_tag["G"] = gps
    rows_by_tag["I"] = imu

    # 3. dump to json
    output_path = log_path.parent / "out" / log_path.with_suffix(".json").name    
    with open(output_path, "w") as f:
        json.dump(rows_by_tag, f, indent=4)

    return rows_by_tag

def convert_row(raw_values: list[str], row_format: SensorRowFormat) -> dict | None:
    if len(raw_values) != len(row_format.columns):
        return None
    converted_values = {}
    for raw_value, (column_name, column_type) in zip(raw_values, row_format.columns):
        try:
            number = float(raw_value)
        except ValueError:
            return None
        if not math.isfinite(number):
            return None
        converted_values[column_name] = (int(number) if column_type is int else number)
    return converted_values




def blank_positions_without_fix(rows: list[dict], drop) -> tuple[list[dict], int]:
    new_rows = []
    blanked = 0
    for row in rows:
        if row["fix_type"] is None:
            raise RuntimeError("provided row contains no fix_type: ", row)
        fix_type = row["fix_type"]
        if fix_type not in POSITION_FIX_TYPES:
            blanked += 1
            if not drop:
                for key in ("latitude_deg", "longitude_deg", "altitude_m"):
                    row[key] = None
                new_rows.append(row)
        else:
            new_rows.append(row)

    return new_rows, blanked



def blank_impossible_imu_values(imu_rows: list[dict], drop=False) -> tuple[list[dict], int]:
    """ Replace each IMU value outside IMU_PLAUSIBLE_VALUE_LIMITS by None and return how
    many were replaced. Per value, not per row: a read error hits one register."""
    blanked = 0
    new_imu_rows: list[dict] = []
    for imu in imu_rows:
        row, blank_row = _check_imu_row(imu)
        blanked += blank_row
        if not (drop and blank_row):
            new_imu_rows.append(row)

    return new_imu_rows, blanked

def _check_imu_row(imu) -> tuple[dict, bool]:
    for column_name, (lowest_value, highest_value) in IMU_PLAUSIBLE_VALUE_LIMITS.items():
        if not lowest_value <= imu[column_name] <= highest_value:
            # print(imu, lowest_value, highest_value, column_name)
            for key in ("linear_accel_x_mps2", "linear_accel_y_mps2", "linear_accel_z_mps2", "pitch_deg", "roll_deg", "yaw_deg"):
                imu[key] = None
            return imu, True

    return imu, False


if __name__ == "__main__":
    parse_data_log(Path("src/navigation/datadump/logs/undated_1/DATA_LOG.csv"))