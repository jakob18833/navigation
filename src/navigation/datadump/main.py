""" ? Rebuild the GeoJSON and HTML reports of NAV_BOX SD-card logs.

    python log_parser.py                   # ? every log folder in logs/
    python log_parser.py 2026-07-01_spar   # ? one log, by folder name or path

Every log lives in its own folder as logs/<name>/DATA_LOG.csv, the raw file exactly as
copied from the SD card (renamed only). Parsing writes logs/<name>/DATA_LOG.json next to it.
logs/<name>/out/ is generated: it is deleted and rewritten on every run, so never edit it by hand.
"""

import argparse
import shutil
import sys
from pathlib import Path

from navigation.datadump.geojson_export import (
    build_gps_feature_collection,
    write_geojson,
)
from navigation.datadump.html_report import write_sensor_pages
from navigation.datadump.parse_csv import parse_data_log

LOGS_DIRECTORY = Path(__file__).resolve().parent / "logs"
RAW_LOG_FILE_NAME = "DATA_LOG.csv"
OUTPUT_DIRECTORY_NAME = "out"


def find_log_directories(logs_directory: Path) -> list[Path]:
    """ ? Every logs/<name>/ that holds a DATA_LOG; anything else is reported and skipped."""
    log_directories = []
    for entry in sorted(logs_directory.iterdir()):
        if entry.is_dir() and (entry / RAW_LOG_FILE_NAME).is_file():
            log_directories.append(entry)
        elif entry.is_file():
            print(f"warning: skipping loose file {entry.name}, move it to logs/<name>/{RAW_LOG_FILE_NAME}")
        else:
            print(f"warning: skipping {entry.name}/, it has no {RAW_LOG_FILE_NAME} inside")
    return log_directories


def resolve_requested_log_directory(log_argument: str) -> Path:
    """ ? Accept either a folder name inside logs/ or a path to a log folder."""
    for candidate in (LOGS_DIRECTORY / log_argument, Path(log_argument)):
        if (candidate / RAW_LOG_FILE_NAME).is_file():
            return candidate.resolve()
    sys.exit(f"error: no {RAW_LOG_FILE_NAME} found for '{log_argument}' (looked in logs/ and as a path)")


def rebuild_log_outputs(log_directory: Path) -> None:
    rows_by_tag = parse_data_log(log_directory / RAW_LOG_FILE_NAME)
    output_directory = log_directory / OUTPUT_DIRECTORY_NAME
    shutil.rmtree(output_directory, ignore_errors=True)
    output_directory.mkdir()

    gps_feature_collection = build_gps_feature_collection(rows_by_tag["G"], log_directory.name)
    write_geojson(gps_feature_collection, output_directory / "gps.geojson")
    write_sensor_pages(rows_by_tag, log_directory.name, gps_feature_collection, output_directory)

    fix_count = sum(feature["geometry"]["type"] == "Point" for feature in gps_feature_collection["features"])
    print(f"{log_directory.name}: "
          f"{len(rows_by_tag['I'])} imu, "
          f"{len(rows_by_tag['B'])} baro, "
          f"{len(rows_by_tag['G'])} gps rows ({fix_count} with fix)")


def main() -> None:
    argument_parser = argparse.ArgumentParser(description="Rebuild GeoJSON + HTML reports of NAV_BOX logs.")
    argument_parser.add_argument("log", nargs="?", help="log folder name in logs/ (or a path); default: all logs")
    arguments = argument_parser.parse_args()

    if arguments.log:
        log_directories = [resolve_requested_log_directory(arguments.log)]
    else:
        log_directories = find_log_directories(LOGS_DIRECTORY)
    for log_directory in log_directories:
        rebuild_log_outputs(log_directory)


if __name__ == "__main__":
    main()
