from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
import datetime
import copy
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
import datetime
import copy
from typing import Any, Dict, List
import uuid

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






@dataclass

class UIDMeta:
    uid: str
    type: str
    name: Optional[str]
    container: Any          # dict or list that holds the object
    key: Optional[KeyType]  # dict key or list index
    path: Tuple[Any, ...]   # lightweight path descriptor (debug/UI)

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

    def rebuild_uid_index(self) -> int:
        """
        Rebuild full UID index from scratch.
        Call after project load, or after large changes.

        Returns number of indexed objects.
        """
        self._uid_obj.clear()
        self._uid_meta.clear()

        # Stratigraphy units (dict key is the unit name)
        if isinstance(self.all_stratigraphy, dict):
            for strat_name, meta in self.all_stratigraphy.items():
                if isinstance(meta, dict):
                    self._index_object(meta, obj_type="stratigraphy", name=strat_name,
                                       container=self.all_stratigraphy, key=strat_name,
                                       path=("stratigraphy", strat_name))

        # Tracks
        if isinstance(self.all_tracks, list):
            for ti, tr in enumerate(self.all_tracks):
                if isinstance(tr, dict):
                    tr_name = tr.get("name", f"Track {ti+1}")
                    self._index_object(tr, obj_type="track", name=tr_name,
                                       container=self.all_tracks, key=ti,
                                       path=("tracks", ti, tr_name))

                    # Optional: nested track config objects
                    for li, lc in enumerate(tr.get("logs") or []):
                        if isinstance(lc, dict):
                            nm = lc.get("log") or lc.get("label") or f"log_cfg_{li}"
                            self._index_object(lc, obj_type="track_log_cfg", name=nm,
                                               container=tr.get("logs"), key=li,
                                               path=("tracks", ti, tr_name, "logs_cfg", li, nm))

                    if isinstance(tr.get("discrete"), dict):
                        self._index_object(tr["discrete"], obj_type="track_discrete_cfg", name=tr_name,
                                           container=tr, key="discrete",
                                           path=("tracks", ti, tr_name, "discrete_cfg"))

                    if isinstance(tr.get("bitmap"), dict):
                        self._index_object(tr["bitmap"], obj_type="track_bitmap_cfg", name=tr_name,
                                           container=tr, key="bitmap",
                                           path=("tracks", ti, tr_name, "bitmap_cfg"))

        # Wells + nested
        if isinstance(self.all_wells, list):
            for wi, w in enumerate(self.all_wells):
                if not isinstance(w, dict):
                    continue
                wname = w.get("name", f"Well {wi+1}")

                self._index_object(w, obj_type="well", name=wname,
                                   container=self.all_wells, key=wi,
                                   path=("wells", wi, wname))

                # tops: dict key is top name
                tops = w.get("tops") or {}
                if isinstance(tops, dict):
                    for top_name, tval in tops.items():
                        if isinstance(tval, dict):
                            self._index_object(tval, obj_type="top", name=top_name,
                                               container=tops, key=top_name,
                                               path=("wells", wi, wname, "tops", top_name))

                # continuous logs: dict key is log name
                logs = w.get("logs") or {}
                if isinstance(logs, dict):
                    for log_name, ldef in logs.items():
                        if isinstance(ldef, dict):
                            self._index_object(ldef, obj_type="continuous_log", name=log_name,
                                               container=logs, key=log_name,
                                               path=("wells", wi, wname, "logs", log_name))

                # discrete logs
                dlogs = w.get("discrete_logs") or {}
                if isinstance(dlogs, dict):
                    for dlog_name, ddef in dlogs.items():
                        if isinstance(ddef, dict):
                            self._index_object(ddef, obj_type="discrete_log", name=dlog_name,
                                               container=dlogs, key=dlog_name,
                                               path=("wells", wi, wname, "discrete_logs", dlog_name))

                # bitmaps
                bms = w.get("bitmaps") or {}
                if isinstance(bms, dict):
                    for bm_key, bdef in bms.items():
                        if isinstance(bdef, dict):
                            nm = bdef.get("name") or bm_key
                            self._index_object(bdef, obj_type="bitmap", name=nm,
                                               container=bms, key=bm_key,
                                               path=("wells", wi, wname, "bitmaps", bm_key, nm))

                # facies intervals: list
                fins = w.get("facies_intervals") or []
                if isinstance(fins, list):
                    for fi, fdef in enumerate(fins):
                        if isinstance(fdef, dict):
                            nm = fdef.get("uid") or f"facies_{fi}"
                            self._index_object(fdef, obj_type="facies_interval", name=str(nm),
                                               container=fins, key=fi,
                                               path=("wells", wi, wname, "facies_intervals", fi))

        self._uid_built = True
        return len(self._uid_obj)

    def _index_object(self, obj: dict, obj_type: str, name: Optional[str],
                      container: Any, key: Optional[KeyType], path: Tuple[Any, ...]) -> None:
        uid = obj.get("uid")
        if not uid:
            return

        self._uid_obj[uid] = obj
        self._uid_meta[uid] = UIDMeta(
            uid=uid,
            type=obj_type,
            name=name,
            container=container,
            key=key,
            path=path
        )

    def ensure_uid_index(self) -> None:
        if not getattr(self, "_uid_built", False):
            self.rebuild_uid_index()

    # ============================================================
    # O(1) getters
    # ============================================================

    def get_object_by_uid(self, uid: str):
        """Returns (obj, meta) or (None, None)."""
        if not uid:
            return None, None
        self.ensure_uid_index()
        return self._uid_obj.get(uid), self._uid_meta.get(uid)

    def get_object_name_by_uid(self, uid: str) -> Optional[str]:
        if not uid:
            return None
        self.ensure_uid_index()
        meta = self._uid_meta.get(uid)
        return meta.name if meta else None

    def get_object_type_by_uid(self, uid: str) -> Optional[str]:
        if not uid:
            return None
        self.ensure_uid_index()
        meta = self._uid_meta.get(uid)
        return meta.type if meta else None

    # ============================================================
    # O(1) delete
    # ============================================================

    def delete_object_by_uid(self, uid: str):
        """
        Delete object identified by uid using index.

        Returns:
            (success: bool, obj_type: str|None, obj_name: str|None)
        """
        if not uid:
            return False, None, None

        self.ensure_uid_index()

        obj = self._uid_obj.get(uid)
        meta = self._uid_meta.get(uid)
        if obj is None or meta is None:
            return False, None, None

        # Remove from container
        try:
            if isinstance(meta.container, dict):
                if meta.key in meta.container:
                    meta.container.pop(meta.key, None)
                else:
                    # fallback: search by uid
                    for k, v in list(meta.container.items()):
                        if isinstance(v, dict) and v.get("uid") == uid:
                            meta.container.pop(k, None)
                            break

            elif isinstance(meta.container, list):
                # list deletion shifts indices -> fix subsequent entries
                if isinstance(meta.key, int) and 0 <= meta.key < len(meta.container):
                    meta.container.pop(meta.key)
                    self._fix_list_container_indices(meta.container, start_index=meta.key)
                else:
                    for i, v in enumerate(list(meta.container)):
                        if isinstance(v, dict) and v.get("uid") == uid:
                            meta.container.pop(i)
                            self._fix_list_container_indices(meta.container, start_index=i)
                            break
            else:
                return False, None, None

        except Exception:
            return False, None, None

        # Remove from index
        self._uid_obj.pop(uid, None)
        self._uid_meta.pop(uid, None)

        return True, meta.type, meta.name

    def _fix_list_container_indices(self, container_list: list, start_index: int):
        """
        After deleting an item from a list container, update meta.key for all indexed
        objects stored in that same list container with key >= start_index.
        """
        for u, m in list(self._uid_meta.items()):
            if m.container is container_list and isinstance(m.key, int) and m.key >= start_index:
                self._uid_meta[u] = UIDMeta(
                    uid=m.uid,
                    type=m.type,
                    name=m.name,
                    container=m.container,
                    key=m.key - 1,
                    path=m.path
                )

    # ============================================================
    # Incremental updates (optional)
    # ============================================================

    def register_object(self, obj: dict, obj_type: str, name: Optional[str],
                        container: Any, key: Optional[KeyType], path: Tuple[Any, ...]) -> None:
        """Register a newly created object into the index (no full rebuild)."""
        uid = obj.get("uid")
        if not uid:
            return
        self.ensure_uid_index()
        self._index_object(obj, obj_type=obj_type, name=name, container=container, key=key, path=path)

    def unregister_uid(self, uid: str) -> None:
        """Remove uid from index only (does not delete from data)."""
        self.ensure_uid_index()
        self._uid_obj.pop(uid, None)
        self._uid_meta.pop(uid, None)



# ============================================================
# 3) Migration helper: legacy JSON -> PWSProject
# ============================================================



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