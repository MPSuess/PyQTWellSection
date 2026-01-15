import math

def _is_latlon(x, y) -> bool:
    """Heuristic: looks like degrees."""
    try:
        x = float(x); y = float(y)
    except Exception:
        return False
    return abs(x) <= 180 and abs(y) <= 90

def _haversine_m(lon1, lat1, lon2, lat2) -> float:
    """Distance on sphere in meters (good enough for display)."""
    R = 6371000.0
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def _well_distance_m(w1: dict, w2: dict) -> float | None:
    """
    Returns distance in meters between w1 and w2 using:
      - (x,y) if present
      - else (longitude, latitude) if present
    """
    # Prefer projected x/y (meters)
    x1, y1 = w1.get("x"), w1.get("y")
    x2, y2 = w2.get("x"), w2.get("y")

    if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
        try:
            x1f, y1f = float(x1), float(y1)
            x2f, y2f = float(x2), float(y2)
        except Exception:
            return None

        # If these look like degrees, treat as lon/lat
        if _is_latlon(x1f, y1f) and _is_latlon(x2f, y2f):
            return _haversine_m(x1f, y1f, x2f, y2f)

        # Else assume projected meters (e.g., UTM)
        return math.hypot(x2f - x1f, y2f - y1f)

    # Fallback: lat/lon keys (if you store them)
    lon1, lat1 = w1.get("longitude"), w1.get("latitude")
    lon2, lat2 = w2.get("longitude"), w2.get("latitude")
    if None not in (lon1, lat1, lon2, lat2):
        try:
            return _haversine_m(float(lon1), float(lat1), float(lon2), float(lat2))
        except Exception:
            return None

    return None