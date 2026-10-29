""" ? Turn the GPS rows into an RFC 7946 GeoJSON FeatureCollection.

The collection holds one LineString (the whole track, in time order) followed by one
Point per GPS row that has a position fix. Rows without a fix were already blanked
to None by parse_csv.py and are skipped. GeoJSON positions are ordered
[longitude, latitude, altitude], longitude first.
"""

import json
from pathlib import Path


def build_gps_feature_collection(gps_rows: list[dict], log_name: str) -> dict:
    track_positions = []
    point_features = []
    for gps_row in gps_rows:
        if gps_row["latitude_deg"] is None:
            continue
        position = [
            round(gps_row["longitude_deg"], 7),
            round(gps_row["latitude_deg"], 7),
            round(gps_row["altitude_m"], 2),
        ]
        track_positions.append(position)
        point_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": position},
            "properties": {
                "time_since_power_on_s": gps_row["time_ms"] / 1000,
                "fix_type": gps_row["fix_type"],
                "satellite_count": gps_row["satellite_count"],
            },
        })

    features = []
    # ? A LineString needs at least two positions to be valid GeoJSON.
    if len(track_positions) >= 2:
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": track_positions},
            "properties": {"name": f"{log_name} track", "fix_count": len(track_positions)},
        })
    features.extend(point_features)
    return {"type": "FeatureCollection", "features": features}


def write_geojson(feature_collection: dict, output_path: Path) -> None:
    output_path.write_text(json.dumps(feature_collection, separators=(",", ":")), encoding="utf-8")
