from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union

KeyType = Union[str, int]

@dataclass(frozen=True)
class UIDMeta:
    uid: str
    type: str
    name: Optional[str]
    container: Any          # dict or list that holds the object
    key: Optional[KeyType]  # dict key or list index
    path: Tuple[Any, ...]   # lightweight path descriptor (debug/UI)


class pws_project:
    def __init__(self):
        # --- your project data ---
        self.all_wells = []
        self.all_tracks = []
        self.all_stratigraphy = {}

        # --- indexes ---
        self._uid_obj: Dict[str, Any] = {}
        self._uid_meta: Dict[str, UIDMeta] = {}
        self._uid_built: bool = False

    # ============================================================
    # Index build / rebuild
    # ============================================================

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