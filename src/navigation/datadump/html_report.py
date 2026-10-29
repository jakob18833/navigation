""" ? Write one self-contained HTML page per sensor: gps.html, imu.html, baro.html.

Each page is page_template.html with four slots filled: title, navigation links,
a one-line summary and a JSON blob with the data. The template's JavaScript draws
one Plotly time chart per entry in blob["charts"] and, when blob["geojson"] is not
null, a Leaflet map. Data is embedded inline because browsers refuse fetch() of
neighbouring files for pages opened from disk (file://).
"""

import html
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from string import Template

from navigation.datadump.parse_csv import IMU_PLAUSIBLE_VALUE_LIMITS

PAGE_TEMPLATE = Template((Path(__file__).with_name("res") / "page_template.html").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ChartDefinition:
    title: str
    y_axis_title: str
    series: tuple[tuple[str, str], ...]  # ? (legend label, key in the sensor's row dicts)
    draw_as_steps: bool = False  # ? for integer states such as fix type


@dataclass(frozen=True)
class SensorPageDefinition:
    file_name: str
    navigation_label: str
    heading: str
    row_tag: str  # ? key into parse_data_log()'s result: "G", "I" or "B"
    charts: tuple[ChartDefinition, ...]
    shows_gps_map: bool = False


SENSOR_PAGES = (
    SensorPageDefinition("gps.html", "GPS", "GPS (u-blox NAV-SOL)", "G", (
        ChartDefinition("Altitude above mean sea level", "m", (("altitude", "altitude_m"),)),
        ChartDefinition("Satellites and fix type", "count / fix type", (
            ("satellites used", "satellite_count"),
            ("fix type (0 none, 2 = 2D, 3 = 3D)", "fix_type"),
        ), draw_as_steps=True),
    ), shows_gps_map=True),
    SensorPageDefinition("imu.html", "IMU", "IMU (BNO055)", "I", (
        ChartDefinition("Linear acceleration (gravity removed)", "m/s²", (
            ("x", "linear_accel_x_mps2"), ("y", "linear_accel_y_mps2"), ("z", "linear_accel_z_mps2"),
        )),
        ChartDefinition("Euler angles", "deg", (
            ("pitch", "pitch_deg"), ("roll", "roll_deg"), ("yaw (heading)", "yaw_deg"),
        )),
    )),
    SensorPageDefinition("baro.html", "Barometer", "Barometer (BMP180)", "B", (
        ChartDefinition("Pressure", "Pa", (("pressure", "pressure_pa"),)),
        ChartDefinition("Temperature", "°C", (("temperature", "temperature_c"),)),
    )),
)


def write_sensor_pages(rows_by_tag: dict[str, list[dict]], log_name: str, gps_feature_collection: dict,
                       output_directory: Path) -> None:
    for page in SENSOR_PAGES:
        rows = rows_by_tag[page.row_tag]
        page_data = {
            "time_s": [row["time_ms"] / 1000 for row in rows],
            "charts": [chart_to_page_data(chart, rows) for chart in page.charts],
            "geojson": gps_feature_collection if page.shows_gps_map else None,
        }
        page_html = PAGE_TEMPLATE.substitute(
            page_title=html.escape(f"{log_name} · {page.heading}"),
            navigation_links=build_navigation_links(page),
            summary_text=html.escape(build_summary_text(page, rows)),
            page_data_json=to_script_tag_json(page_data),
        )
        (output_directory / page.file_name).write_text(page_html, encoding="utf-8")


def chart_to_page_data(chart: ChartDefinition, rows: list[dict]) -> dict:
    return {
        "title": chart.title,
        "y_axis_title": chart.y_axis_title,
        "draw_as_steps": chart.draw_as_steps,
        "series": [{"label": label, "values": [row[column_name] for row in rows]}
                   for label, column_name in chart.series],
    }


def build_navigation_links(current_page: SensorPageDefinition) -> str:
    links = []
    for page in SENSOR_PAGES:
        css_class = ' class="current"' if page is current_page else ""
        links.append(f'<a href="{page.file_name}"{css_class}>{page.navigation_label}</a>')
    return "".join(links)


def build_summary_text(page: SensorPageDefinition, rows: list[dict]) -> str:
    """ ? e.g. "602 samples · t = 1.8 … 845.6 s since power-on · median interval 1001 ms"."""
    if not rows:
        parts = ["no samples"]
    else:
        times_ms = [row["time_ms"] for row in rows]
        parts = [f"{len(rows)} samples", f"t = {times_ms[0] / 1000:.1f} … {times_ms[-1] / 1000:.1f} s since power-on"]
        if len(rows) >= 2:
            intervals_ms = [later - earlier for earlier, later in zip(times_ms, times_ms[1:])]
            parts.append(f"median interval {statistics.median(intervals_ms):.0f} ms")
    if page.shows_gps_map:
        fix_count = sum(row["latitude_deg"] is not None for row in rows)
        parts.append(f"{fix_count} with position fix")
    if page.row_tag == "I":
        blanked_row_count = sum(any(row[column_name] is None for column_name in IMU_PLAUSIBLE_VALUE_LIMITS)
                                for row in rows)
        if blanked_row_count:
            parts.append(f"{blanked_row_count} samples with physically impossible values (I2C read errors) not drawn")
    return " · ".join(parts)


def to_script_tag_json(page_data: dict) -> str:
    """ ? JSON safe to place inside <script>: "</" is escaped so the data cannot close the tag."""
    return json.dumps(page_data, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
