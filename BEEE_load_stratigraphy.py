#!/usr/bin/env python3
"""
Build a stratigraphy JSON tree from ATS-like spreadsheets.

Assumptions (customizable):
- KUERZEL  -> acronym (unique-ish key)
- BEDEUTUNG -> name
- Vater    -> parent acronym
- Alter von / Alter bis -> age range (Ma)
- Level    -> hierarchy support + rank mapping

Outputs a JSON tree sorted by age_ma.from from youngest -> oldest (ascending Ma),
both at root level and for each node's members.

Works with .xlsx/.xls and .csv.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# -----------------------------
# Configuration
# -----------------------------

DEFAULT_COLS = {
    "acronym": "KUERZEL",
    "name": "BEDEUTUNG",
    "parent": "Vater",
    "level": "Level",
    "age_from": "Alter von",
    "age_to": "Alter bis",
    "type": "Strat_Typ"
}

# Map numeric "Level" to rank labels (change to your preferred ranks)
LEVEL_TO_RANK = {
    4: "member_L4",
    5: "bed_L5",
    6: "bed_L6",
    7: "bed_L7",
}


# -----------------------------
# Helpers
# -----------------------------

def _clean_str(x: Any) -> Optional[str]:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    s = str(x).strip()
    return s if s else None


def _to_int(x: Any) -> Optional[int]:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
        # handles "4", "4.0"
        return int(float(str(x).strip()))
    except Exception:
        return None


def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, float) and math.isnan(x):
            return None
        s = str(x).strip().replace(",", ".")
        if not s:
            return None
        return float(s)
    except Exception:
        return None


def _rank_from_level(level: Optional[int]) -> str:
    if level is None:
        return "unknown"
    return LEVEL_TO_RANK.get(level, f"level_{level}")


def _sort_key_age_from(node: Dict[str, Any]) -> Tuple[int, float, str]:
    """
    Sort youngest -> oldest by age_ma.from ASC (smaller Ma first).
    Nodes with unknown age go last.
    Tie-breaker: acronym.
    """
    age_from = ((node.get("age_ma") or {}).get("from"))
    if age_from is None:
        return (1, float("inf"), node.get("acronym", ""))
    return (0, float(age_from), node.get("acronym", ""))


def _compute_node_age_from_children(node: Dict[str, Any]) -> Optional[float]:
    """
    Optional: derive a parent's age.from from children when missing.
    Here: choose MIN(child.from) because we sort by youngest-first.
    (You can change this to max or something else.)
    """
    members = node.get("members") or []
    vals = []
    for ch in members:
        af = ((ch.get("age_ma") or {}).get("from"))
        if af is not None:
            vals.append(float(af))
    if not vals:
        return None
    return min(vals)


# -----------------------------
# Core builder
# -----------------------------

@dataclass
class Node:
    acronym: str
    name: Optional[str] = None
    parent: Optional[str] = None
    level: Optional[int] = None
    age_from: Optional[float] = None
    age_to: Optional[float] = None
    type: Optional[str] = None
    rank: str = "unknown"
    members: List[str] = field(default_factory=list)  # store children acronyms

    def to_dict(self, nodes_by_key: Dict[str, "Node"], derive_parent_age: bool) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "acronym": self.acronym,
            "name": self.name,
            "rank": self.rank,
            "level": self.level,
            "age_ma": {"from": self.age_from, "to": self.age_to},
            "type" : self.type
        }

        # build children
        if self.members:
            children = [nodes_by_key[k].to_dict(nodes_by_key, derive_parent_age) for k in self.members]
            children.sort(key=_sort_key_age_from)
            d["members"] = children

            # optionally fill missing parent age_from from children
            if derive_parent_age:
                if d["age_ma"]["from"] is None:
                    derived = _compute_node_age_from_children(d)
                    if derived is not None:
                        d["age_ma"]["from"] = derived

        return d


def build_tree_from_dataframe(
    df: pd.DataFrame,
    cols: Dict[str, str] = DEFAULT_COLS,
    derive_parent_age: bool = True,
) -> Dict[str, Any]:
    # Normalize column names (strip)
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    missing = [v for v in cols.values() if v not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Present: {list(df.columns)}")

    nodes: Dict[str, Node] = {}

    # 1) Create nodes for every row (acronyms)
    for _, row in df.iterrows():
        acronym = _clean_str(row[cols["acronym"]])

        if not acronym:
            continue
        type = _clean_str(row[cols["type"]])

        if type != "CH":
            continue

        name = _clean_str(row[cols["name"]])
        parent = _clean_str(row[cols["parent"]])
        level = _to_int(row[cols["level"]])
        age_from = _to_float(row[cols["age_from"]])
        age_to = _to_float(row[cols["age_to"]])


        # create or update
        n = nodes.get(acronym)
        if n is None:
            n = Node(acronym=acronym)
            nodes[acronym] = n

        # update (prefer non-null incoming data)
        n.name = name if name is not None else n.name
        n.parent = parent if parent is not None else n.parent
        n.level = level if level is not None else n.level
        n.age_from = age_from if age_from is not None else n.age_from
        n.age_to = age_to if age_to is not None else n.age_to
        n.type = type if type is not None else n.type
        n.rank = _rank_from_level(n.level)

    # 2) Ensure stub nodes exist for any parents that are referenced but not defined as rows
    for n in list(nodes.values()):
        if n.parent and n.parent not in nodes:
            nodes[n.parent] = Node(
                acronym=n.parent,
                name=None,
                parent=None,
                level=None,
                age_from=None,
                age_to=None,
                type=None,
                rank="unknown",
            )

    # 3) Build adjacency: parent -> children
    for n in nodes.values():
        if n.parent:
            # If parent exists, link
            if n.parent in nodes:
                nodes[n.parent].members.append(n.acronym)

    # 4) Identify roots (no parent OR parent missing/blank)
    roots = [n for n in nodes.values() if not n.parent]

    # 5) Convert roots to dict and sort youngest -> oldest
    root_dicts = [r.to_dict(nodes, derive_parent_age) for r in roots]
    root_dicts.sort(key=_sort_key_age_from)

    return {"stratigraphy": root_dicts}


def read_table(path: str, sheet: Optional[str] = None) -> pd.DataFrame:
    lower = path.lower()
    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(path, sheet_name=sheet if sheet is not None else 0)
    if lower.endswith(".csv"):
        # try common separators
        try:
            return pd.read_csv(path)
        except Exception:
            return pd.read_csv(path, sep=";")
    raise ValueError("Unsupported file type. Use .xlsx/.xls/.csv")


# -----------------------------
# CLI
# -----------------------------

def _load_BEEE_stratigraphy(fn) -> pd.DataFrame:
    """Load BEEE stratigraphy from Excel spreadsheet."""
    df = read_table(fn)
    colmap = DEFAULT_COLS
    tree = build_tree_from_dataframe(
        df,
        cols=colmap,
        derive_parent_age=("store_true"),
    )
    with open("test-strat.json", "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    #json.dumps(tree, ensure_ascii=False, indent=2)

    return tree

def main() -> None:
    ap = argparse.ArgumentParser(description="Generate stratigraphy JSON tree from a spreadsheet.")
    ap.add_argument("input", help="Input spreadsheet (.xlsx/.xls/.csv)")
    ap.add_argument("-o", "--output", default="stratigraphy_tree.json", help="Output JSON path")
    ap.add_argument("--sheet", default=None, help="Excel sheet name (optional)")
    ap.add_argument("--no-derive-parent-age", action="store_true",
                    help="Do not compute missing parent age_ma.from from children")
    ap.add_argument("--cols", default=None,
                    help=("Optional JSON string to override column mapping, e.g. "
                          '\'{"acronym":"KUERZEL","name":"BEDEUTUNG","parent":"Vater","level":"Level","age_from":"Alter von","age_to":"Alter bis"}\''))
    args = ap.parse_args()

    colmap = DEFAULT_COLS
    if args.cols:
        colmap = json.loads(args.cols)

    df = read_table(args.input, sheet=args.sheet)
    tree = build_tree_from_dataframe(
        df,
        cols=colmap,
        derive_parent_age=(not args.no_derive_parent_age),
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()