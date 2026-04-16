from typing import Any, Dict, List, Optional, Tuple
import difflib
import csv
import os

# ---------- Strat tree helpers ----------

def _strat_get_children(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    return node.get("members") or node.get("children") or []

def _strat_key(node: Dict[str, Any]) -> str:
    # acronym is your leaf naming convention; fall back to name
    a = (node.get("acronym") or "").strip()
    if a:
        return a
    return (node.get("name") or "").strip()

def _strat_full_name(node: Dict[str, Any]) -> str:
    return (node.get("name") or "").strip()

def flatten_strat_tree(strat_roots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build indices for:
      - key_to_node: acronym/name -> node
      - parent_map: child_key -> parent_key
      - children_map: parent_key -> [child_keys] (in original order!)
      - all_keys: list of all keys
      - key_to_fullname: key -> full name
    """
    key_to_node: Dict[str, Dict[str, Any]] = {}
    parent_map: Dict[str, Optional[str]] = {}
    children_map: Dict[str, List[str]] = {}
    key_to_fullname: Dict[str, str] = {}

    def walk(node: Dict[str, Any], parent_key: Optional[str]):
        k = _strat_key(node)
        if not k:
            return
        # store
        key_to_node[k] = node
        parent_map[k] = parent_key
        key_to_fullname[k] = _strat_full_name(node)

        # children
        kids = _strat_get_children(node)
        ck = []
        for ch in kids:
            ckey = _strat_key(ch)
            if ckey:
                ck.append(ckey)
        children_map[k] = ck

        for ch in kids:
            walk(ch, k)

    for root in strat_roots or []:
        walk(root, None)

    all_keys = list(key_to_node.keys())
    return {
        "key_to_node": key_to_node,
        "parent_map": parent_map,
        "children_map": children_map,
        "all_keys": all_keys,
        "key_to_fullname": key_to_fullname,
    }


def find_node_key_by_name_or_acronym(idx: Dict[str, Any], base_name: str) -> Optional[str]:
    """
    Try exact match by:
      - acronym key
      - full name (node['name'])
      - case-insensitive
    """
    base_name = (base_name or "").strip()
    if not base_name:
        return None

    k2n = idx["key_to_node"]
    if base_name in k2n:
        return base_name

    # case-insensitive match against keys
    low = base_name.lower()
    for k in k2n.keys():
        if k.lower() == low:
            return k

    # match full names
    for k, node in k2n.items():
        fn = (_strat_full_name(node) or "")
        if fn == base_name:
            return k
        if fn.lower() == low:
            return k

    return None


def equivalent_top_for_base(idx: Dict[str, Any], base_unit_key: str) -> Optional[str]:
    """
    Implements: Base(Unit) == Top(Underlying)
    - If Unit has a parent: use sibling immediately BELOW it (next older sibling) within parent.
      Example: Upper Jurassic -> Middle Jurassic (next sibling)
    - If Unit is the last sibling (oldest): then "below" is parent's next older sibling (recursively)
      (works for many hierarchies; best effort)
    - If Unit is a root: no mapping.
    """
    parent_map = idx["parent_map"]
    children_map = idx["children_map"]

    k = base_unit_key
    parent = parent_map.get(k)
    if not parent:
        return None

    siblings = children_map.get(parent, [])
    if k not in siblings:
        return None

    i = siblings.index(k)

    # "below" means next older sibling (assuming order young->old in the BEEE column)
    if i + 1 < len(siblings):
        return siblings[i + 1]

    # if no older sibling: go down a level (parent's below)
    # Base of oldest subunit ~ Top of unit below the parent in its own sibling list
    return equivalent_top_for_base(idx, parent)

def map_sv_bases_to_tops(
    sv_rows: List[Dict[str, Any]],
    beee_idx: Dict[str, Any],
    *,
    only_base_rows: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns:
      mapped: rows where we could map Base(Unit) -> Top(Underlying)
      unresolved: rows needing user choice

    Output row format for mapped:
      {
        "well": ..., "md": ..., "sv_name": ..., "mapped_top": ...,
        "role": "stratigraphy", "type": "Top"
      }
    """
    mapped = []
    unresolved = []

    all_keys = beee_idx["all_keys"]
    # also allow matching on full names
    fullnames = beee_idx["key_to_fullname"]
    full_to_key = { (v or "").lower(): k for k, v in fullnames.items() if v }

    for r in sv_rows:
        typ = (r.get("type") or "").strip().lower()
        if only_base_rows and typ and typ != "base":
            # skip non-Base if file contains mixed
            continue

        base_name = (r.get("name") or "").strip()
        if not base_name:
            continue

        # 1) exact resolve base name to BEEE node key
        key = find_node_key_by_name_or_acronym(beee_idx, base_name)

        # also try full-name match
        if key is None:
            key = full_to_key.get(base_name.lower())

        if key is not None:
            eq_top = equivalent_top_for_base(beee_idx, key)
            if eq_top is not None:
                mapped.append({
                    "well": r.get("well",""),
                    "md": r.get("md", None),
                    "sv_name": base_name,
                    "beee_base_key": key,
                    "mapped_top": eq_top,
                    "role": "stratigraphy",
                    "type": "Top",
                })
                continue

        # 2) unresolved -> propose fuzzy matches against both keys and full names
        candidates = difflib.get_close_matches(base_name, all_keys, n=8, cutoff=0.55)

        # add full name fuzzy candidates too (mapped back to key)
        fn_matches = difflib.get_close_matches(base_name.lower(), list(full_to_key.keys()), n=8, cutoff=0.55)
        for fn in fn_matches:
            k = full_to_key.get(fn)
            if k and k not in candidates:
                candidates.append(k)

        unresolved.append({
            "well": r.get("well",""),
            "md": r.get("md", None),
            "sv_name": base_name,
            "candidates": candidates,  # list of beee keys
        })

    return mapped, unresolved