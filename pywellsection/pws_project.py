from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
import datetime
import copy


# ============================================================
# 1) Window spec schema (for project.all_windows)
# ============================================================

@dataclass
class PWSWindowSpec:
    """
    Serializable window/dock spec.
    Keep this simple and forward-compatible: store only what you need
    to recreate windows and restore user layout later.

    Typical usage:
      - type: "wellpanel" | "map" | "table" | ...
      - title: shown in dock tab / window tree
      - id: stable UUID-like string (optional)
      - is_floating / geometry: optional
      - area/tab_group: optional
      - payload: type-specific content (e.g. which wells/tracks are shown)
    """
    id: str = ""
    type: str = "wellpanel"
    title: str = ""

    # Dock placement hints (optional)
    dock_area: Optional[str] = None        # "left"|"right"|"top"|"bottom"
    tab_group: Optional[str] = None        # group key to tab docks together
    is_floating: bool = False

    # Geometry (optional). You can store Qt saveGeometry bytes separately if desired.
    geometry: Optional[Dict[str, Any]] = None

    # Type-specific settings
    payload: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PWSWindowSpec":
        dd = dict(d or {})
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore
        init_kwargs = {k: dd.get(k) for k in known if k in dd}
        obj = cls(**init_kwargs)  # type: ignore
        obj.payload = dict(obj.payload or {})
        obj.geometry = dict(obj.geometry or {}) if obj.geometry is not None else None
        return obj

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# 2) Project container (as before, plus window spec helpers)
# ============================================================

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
import datetime
import copy


@dataclass
class PWSProject:
    # ---- identity / metadata ----
    name: str = ""
    type: str = "project"
    version: str = "0.0.1"
    project_file_version: str = "2.0"

    # ---- spatial metadata ----
    crs: Optional[Any] = None
    extent: Optional[Tuple[float, float, float, float]] = None
    projection: Optional[Any] = None
    units: Optional[Dict[str, str]] = None

    # NEW: preserve file metadata + UI layout blobs
    metadata: Dict[str, Any] = field(default_factory=dict)
    ui_layout: Dict[str, Any] = field(default_factory=dict)

    # ---- generic registry ----
    object_list: List[Dict[str, Any]] = field(default_factory=list)

    # ---- primary collections ----
    all_wells: List[Dict[str, Any]] = field(default_factory=list)
    all_stratigraphy: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    all_tracks: List[Dict[str, Any]] = field(default_factory=list)
    all_windows: List[Dict[str, Any]] = field(default_factory=list)  # list of PWSWindowSpec dicts

    # ---- derived/optional registries ----
    all_logs: Dict[str, Any] = field(default_factory=dict)
    all_discrete_logs: Dict[str, Any] = field(default_factory=dict)
    all_bitmaps: Dict[str, Any] = field(default_factory=dict)
    all_profiles: List[Dict[str, Any]] = field(default_factory=list)

    created_utc: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z")
    modified_utc: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z")

    def touch_modified(self):
        self.modified_utc = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def reset(self, keep_metadata: bool = True):
        meta = {}
        if keep_metadata:
            meta = {
                "name": self.name,
                "type": self.type,
                "version": self.version,
                "project_file_version": self.project_file_version,
                "crs": self.crs,
                "extent": self.extent,
                "projection": self.projection,
                "units": copy.deepcopy(self.units),
                "metadata": copy.deepcopy(self.metadata),
                "ui_layout": copy.deepcopy(self.ui_layout),
            }

        self.object_list.clear()
        self.all_wells.clear()
        self.all_stratigraphy.clear()
        self.all_tracks.clear()
        self.all_windows.clear()
        self.all_logs.clear()
        self.all_discrete_logs.clear()
        self.all_bitmaps.clear()
        self.all_profiles.clear()

        if keep_metadata:
            for k, v in meta.items():
                setattr(self, k, v)

        self.touch_modified()

    class pws_project:
        ...

        # --------------------------------------------------------
        # PUBLIC: get object by uid
        # --------------------------------------------------------
        def get_object_by_uid(self, uid: str):
            """
            Search the entire project for an object with matching id.

            Returns:
                (obj, parent, object_type)
            or:
                (None, None, None)
            """

            if not uid:
                return None, None, None

            # search wells
            for well in (self.all_wells or []):
                obj = self._search_dict_recursive(well, uid)
                if obj:
                    return obj

            # search tracks
            for track in (self.all_tracks or []):
                obj = self._search_dict_recursive(track, uid)
                if obj:
                    return obj

            # search stratigraphy
            for name, meta in (self.all_stratigraphy or {}).items():
                if isinstance(meta, dict) and meta.get("id") == uid:
                    return meta, self.all_stratigraphy, "stratigraphy"

            return None, None, None

        # --------------------------------------------------------
        # INTERNAL recursive search helper
        # --------------------------------------------------------
        def _search_dict_recursive(self, obj, uid):
            """
            Recursively search dicts/lists for object with id == uid.
            Returns (obj, parent, type) or None.
            """

            if isinstance(obj, dict):

                # direct hit
                if obj.get("id") == uid:
                    return obj, None, self._infer_object_type(obj)

                for key, val in obj.items():

                    # nested dict
                    if isinstance(val, dict):
                        result = self._search_dict_recursive(val, uid)
                        if result:
                            found, parent, typ = result
                            return found, obj, typ

                    # nested list
                    elif isinstance(val, list):
                        for item in val:
                            result = self._search_dict_recursive(item, uid)
                            if result:
                                found, parent, typ = result
                                return found, obj, typ

            return None



# ============================================================
# 3) Migration helper: legacy JSON -> PWSProject
# ============================================================
from typing import Any, Dict, List
import uuid


def _ensure_top_role_in_well(well: Dict[str, Any], default_role="stratigraphy"):
    tops = well.get("tops") or {}
    for name, tv in list(tops.items()):
        if isinstance(tv, dict):
            if not tv.get("role"):
                tv["role"] = default_role
    well["tops"] = tops


def _ensure_top_role_in_stratigraphy(strat: Dict[str, Any], default_role="stratigraphy"):
    for name, meta in (strat or {}).items():
        if isinstance(meta, dict) and not meta.get("role"):
            meta["role"] = default_role


def _normalize_bitmaps(well: Dict[str, Any]):
    """
    Your sample duplicates bitmaps:
      well["bitmaps"]["cp001"] ... and also well["cp001"] ...
    Normalize to only well["bitmaps"].
    """
    bmaps = dict(well.get("bitmaps") or {})

    # absorb any top-level entries that look like bitmap dicts (cp001, cp002, ...)
    for k in list(well.keys()):
        if k.startswith("cp") and isinstance(well.get(k), dict) and "path" in well[k]:
            bmaps.setdefault(k, well[k])
            # remove duplicate
            del well[k]

    well["bitmaps"] = bmaps


def _normalize_continuous_logs(well: Dict[str, Any]):
    """
    Ensure each continuous log has matching depth/data lengths.
    Clamp to min length if mismatch.
    """
    logs = well.get("logs") or {}
    for ln, ld in list(logs.items()):
        if not isinstance(ld, dict):
            continue
        d = ld.get("depth") or []
        v = ld.get("data") or []
        if isinstance(d, list) and isinstance(v, list):
            n = min(len(d), len(v))
            if n < len(d) or n < len(v):
                ld["depth"] = d[:n]
                ld["data"] = v[:n]
        logs[ln] = ld
    well["logs"] = logs


def _normalize_discrete_logs(well: Dict[str, Any]):
    """
    Your discrete format is depth[] + values[] with -999 indicating no value below depth.
    Ensure lengths match (clamp).
    """
    dlogs = well.get("discrete_logs") or {}
    for ln, ld in list(dlogs.items()):
        if not isinstance(ld, dict):
            continue
        d = ld.get("depth") or []
        v = ld.get("values") or []
        if isinstance(d, list) and isinstance(v, list):
            n = min(len(d), len(v))
            if n < len(d) or n < len(v):
                ld["depth"] = d[:n]
                ld["values"] = v[:n]
        dlogs[ln] = ld
    well["discrete_logs"] = dlogs


def _migrate_window_dict_item_to_spec(wd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert your legacy window_dict item to a PWSWindowSpec-like dict.
    """
    wtype = wd.get("type", "WellSection")
    title = wd.get("window_title", wtype)

    # Normalize visible_tops: can be dict (your first entry) or list (your second)
    vt = wd.get("visible_tops", None)
    if isinstance(vt, dict):
        visible_tops = list(vt.keys())
    elif isinstance(vt, list):
        visible_tops = vt
    else:
        visible_tops = None

    panel_settings = wd.get("panel_settings") or {}

    spec = {
        "id": wd.get("id") or str(uuid.uuid4()),
        "type": "wellpanel" if wtype == "WellSection" else wtype.lower(),
        "title": title,
        "dock_area": None,
        "tab_group": None,
        "is_floating": bool(wd.get("floating", False)),
        "geometry": None,
        "payload": {
            "visible": bool(wd.get("visible", True)),
            "visible_wells": wd.get("visible_wells", None),
            "visible_tracks": wd.get("visible_tracks", None),
            "visible_logs": wd.get("visible_logs", None),
            "visible_tops": visible_tops,
            "panel_settings": panel_settings,
        },
    }
    return spec


def migrate_legacy_to_project_v2(legacy: Dict[str, Any], project_name: str = "") -> PWSProject:
    """
    Migration tailored to your JSON example:
      - wells/tracks/stratigraphy/metadata/window_dict/ui_layout
    """
    src = dict(legacy or {})

    proj = PWSProject()
    proj.name = project_name or src.get("name", "") or ""

    proj.metadata = dict(src.get("metadata") or {})
    proj.ui_layout = dict(src.get("ui_layout") or {})

    proj.all_wells = list(src.get("wells") or [])
    proj.all_tracks = list(src.get("tracks") or [])
    proj.all_stratigraphy = dict(src.get("stratigraphy") or {})

    # Ensure stratigraphy role default
    _ensure_top_role_in_stratigraphy(proj.all_stratigraphy, default_role="stratigraphy")

    # Normalize wells content
    for w in proj.all_wells:
        w.setdefault("logs", {})
        w.setdefault("discrete_logs", {})
        w.setdefault("tops", {})
        w.setdefault("bitmaps", {})
        w.setdefault("facies_intervals", [])

        _normalize_bitmaps(w)
        _normalize_continuous_logs(w)
        _normalize_discrete_logs(w)
        _ensure_top_role_in_well(w, default_role="stratigraphy")

        # also default well reference fields if missing
        w.setdefault("reference_type", "KB")
        w.setdefault("reference_depth", 0.0)
        w.setdefault("total_depth", 0.0)

    # Windows
    win_list = src.get("window_dict") or src.get("windows") or []
    proj.all_windows = []
    for wd in win_list:
        if isinstance(wd, dict):
            proj.all_windows.append(_migrate_window_dict_item_to_spec(wd))

    # If no windows, create one default wellpanel spec
    if not proj.all_windows:
        proj.all_windows = [{
            "id": "main",
            "type": "wellpanel",
            "title": "Main Well Panel",
            "dock_area": "right",
            "tab_group": "main",
            "is_floating": False,
            "geometry": None,
            "payload": {
                "visible": True,
                "visible_wells": None,
                "visible_tracks": None,
                "visible_logs": None,
                "visible_tops": None,
                "panel_settings": {},
            },
        }]

    proj.touch_modified()
    return proj