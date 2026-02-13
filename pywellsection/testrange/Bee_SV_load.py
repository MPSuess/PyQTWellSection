#!/usr/bin/env python3
"""
Refactored ATS Stratigraphy Tool (class-based, no globals mutation)

Features
--------
1) Build stratigraphy tree from ATS-like table:
   - KUERZEL -> acronym
   - BEDEUTUNG -> name
   - Vater -> parent
   - Level -> rank support
   - Alter von / Alter bis -> age range (Ma)
   - REGION -> region letters (e.g. "NSRO" => {"N","S","R","O"})
   - Strat_Typ -> stratigraphy type (e.g. "A")

2) Analyse a Schichtenverzeichnis:
   - Read base units listed in column E (default)
   - Find equivalent TOP using hierarchy + preferences:
     A) Prefer older sibling under same parent with:
        - REGION overlap AND same Strat_Typ
        if none: REGION overlap AND any Strat_Typ
     B) If no older sibling exists:
        - Use parent's older sibling (same grandparent)
        - Choose its daughter (child) whose age_to best matches boundary:
          candidate.age_to ~= base.age_from
        - Same preference passes as above
   - Output includes:
     base_code, equivalent_base_name, base_rank, base_depth,
     equivalent_top_code, equivalent_top_name, top_rank, top_depth, status

Notes
-----
- Sorting youngest -> oldest == ascending Ma (smaller from-age is younger).
- Region matching: if either region is missing, it's treated as "unknown OK" (not a hard fail).
  You can make it strict via config.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# -----------------------------
# Defaults / Config
# -----------------------------

DEFAULT_COLS = {
    "acronym": "KUERZEL",
    "name": "BEDEUTUNG",
    "parent": "Vater",
    "level": "Level",
    "age_from": "Alter von",
    "age_to": "Alter bis",
    "region": "REGION",
    "strat_type": "Strat_Typ",
}

LEVEL_TO_RANK_DEFAULT = {
    0: "Global_eon_L0",
    1: "Global_era_L1",
    2: "Global_system_L2",
    3: "Global_series_l3",
    4: "regional_unit_L4",
    5: "subunit_L5",
    6: "subunit_L6",
    7: "subunit_L7",
}

# Schichtenverzeichnis columns (1-based indices)
DEFAULT_SCHICHT_COL_CODE = 5       # Column E
DEFAULT_SCHICHT_COL_BASEDEPTH = 3  # Column C


# -----------------------------
# IO Helpers
# -----------------------------

def read_table(path: str, sheet: Optional[str] = None) -> pd.DataFrame:
    lower = path.lower()
    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(path, sheet_name=sheet if sheet is not None else 0)
    if lower.endswith(".csv"):
        try:
            return pd.read_csv(path)
        except Exception:
            return pd.read_csv(path, sep=";")
    raise ValueError("Unsupported file type. Use .xlsx/.xls/.csv")


# -----------------------------
# Data model
# -----------------------------

@dataclass
class Node:
    acronym: str
    name: Optional[str] = None
    parent: Optional[str] = None
    level: Optional[int] = None
    age_from: Optional[float] = None
    age_to: Optional[float] = None
    rank: str = "unknown"
    region: Optional[set[str]] = None
    strat_type: Optional[str] = None
    members: List[str] = field(default_factory=list)  # children acronyms

    def to_dict(self, nodes_by_key: Dict[str, "Node"], sort_key_fn) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "acronym": self.acronym,
            "name": self.name,
            "rank": self.rank,
            "level": self.level,
            "region": "".join(sorted(self.region)) if self.region else None,
            "strat_type": self.strat_type,
            "age_ma": {"from": self.age_from, "to": self.age_to},
        }
        if self.members:
            children = [nodes_by_key[k].to_dict(nodes_by_key, sort_key_fn) for k in self.members]
            children.sort(key=sort_key_fn)
            d["members"] = children
        return d


# -----------------------------
# StratigraphyModel
# -----------------------------

class StratigraphyModel:
    def __init__(
        self,
        cols: Dict[str, str] = DEFAULT_COLS,
        level_to_rank: Dict[int, str] = LEVEL_TO_RANK_DEFAULT,
        boundary_tol_ma: float = 0.05,
        region_unknown_ok: bool = True,
    ) -> None:
        self.cols = cols
        self.level_to_rank = level_to_rank
        self.boundary_tol_ma = float(boundary_tol_ma)
        self.region_unknown_ok = bool(region_unknown_ok)

        # Built artifacts
        self.tree: Optional[Dict[str, Any]] = None
        self.index: Dict[str, Dict[str, Any]] = {}
        self.parent_of: Dict[str, Optional[str]] = {}
        self.siblings_by_parent: Dict[str, List[str]] = {}

    # ---------- low-level parsing ----------

    @staticmethod
    def _clean_str(x: Any) -> Optional[str]:
        if x is None:
            return None
        if isinstance(x, float) and math.isnan(x):
            return None
        s = str(x).strip()
        return s if s else None

    @staticmethod
    def _to_int(x: Any) -> Optional[int]:
        try:
            if x is None or (isinstance(x, float) and math.isnan(x)):
                return None
            return int(float(str(x).strip()))
        except Exception:
            return None

    @staticmethod
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

    def _rank_from_level(self, level: Optional[int]) -> str:
        if level is None:
            return "unknown"
        return self.level_to_rank.get(level, f"level_{level}")

    @staticmethod
    def _parse_regions(s: Any) -> Optional[set[str]]:
        v = StratigraphyModel._clean_str(s)
        if not v:
            return None
        return {ch for ch in v if ch.isalpha()}

    def _region_overlap(self, a: Optional[set[str]], b: Optional[set[str]]) -> bool:
        # region_unknown_ok=True => missing region is not a hard fail
        if self.region_unknown_ok and (not a or not b):
            return True
        if not a or not b:
            return False
        return len(a.intersection(b)) > 0

    @staticmethod
    def _sort_key_age_from(node_dict: Dict[str, Any]) -> Tuple[int, float, str]:
        """
        Sort youngest -> oldest by age_ma.from ASC (smaller Ma first).
        Nodes with unknown age go last. Tie-breaker: acronym.
        """
        af = ((node_dict.get("age_ma") or {}).get("from"))
        if af is None:
            return (1, float("inf"), node_dict.get("acronym", ""))
        return (0, float(af), node_dict.get("acronym", ""))

    # ---------- build / index ----------

    def build_from_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]

        c = self.cols
        required = [c["acronym"], c["name"], c["parent"], c["level"], c["age_from"], c["age_to"]]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}. Present: {list(df.columns)}")

        nodes: Dict[str, Node] = {}

        for _, row in df.iterrows():
            acronym = self._clean_str(row[c["acronym"]])
            if not acronym:
                continue

            name = self._clean_str(row[c["name"]])
            parent = self._clean_str(row[c["parent"]])
            level = self._to_int(row[c["level"]])
            age_from = self._to_float(row[c["age_from"]])
            age_to = self._to_float(row[c["age_to"]])

            region = self._parse_regions(row[c["region"]]) if c.get("region") in df.columns else None
            strat_type = self._clean_str(row[c["strat_type"]]) if c.get("strat_type") in df.columns else None

            n = nodes.get(acronym)
            if n is None:
                n = Node(acronym=acronym)
                nodes[acronym] = n

            n.name = name if name is not None else n.name
            n.parent = parent if parent is not None else n.parent
            n.level = level if level is not None else n.level
            n.age_from = age_from if age_from is not None else n.age_from
            n.age_to = age_to if age_to is not None else n.age_to
            n.rank = self._rank_from_level(n.level)

            n.region = region if region is not None else n.region
            n.strat_type = strat_type if strat_type is not None else n.strat_type

        # stubs for referenced parents
        for n in list(nodes.values()):
            if n.parent and n.parent not in nodes:
                nodes[n.parent] = Node(acronym=n.parent, rank="unknown")

        # adjacency
        for n in nodes.values():
            if n.parent and n.parent in nodes:
                nodes[n.parent].members.append(n.acronym)

        roots = [n for n in nodes.values() if not n.parent]
        root_dicts = [r.to_dict(nodes, self._sort_key_age_from) for r in roots]
        root_dicts.sort(key=self._sort_key_age_from)

        self.tree = {"stratigraphy": root_dicts}
        self._index_tree()  # build index structures
        return self.tree

    def build_from_file(self, ats_path: str, sheet: Optional[str] = None) -> Dict[str, Any]:
        df = read_table(ats_path, sheet=sheet)
        return self.build_from_dataframe(df)

    def _index_tree(self) -> None:
        if not self.tree:
            raise RuntimeError("Tree not built yet. Call build_from_dataframe/build_from_file first.")

        index: Dict[str, Dict[str, Any]] = {}
        parent_of: Dict[str, Optional[str]] = {}
        children_tmp: Dict[str, List[str]] = {}

        def walk(node: Dict[str, Any], parent: Optional[str]) -> None:
            acr = node.get("acronym")
            if not acr:
                return
            index[acr] = node
            parent_of[acr] = parent

            members = node.get("members") or []
            if members:
                children_tmp.setdefault(acr, [])
                for ch in members:
                    ch_acr = ch.get("acronym")
                    if ch_acr:
                        children_tmp[acr].append(ch_acr)
                    walk(ch, acr)

        for r in self.tree.get("stratigraphy", []) or []:
            walk(r, None)

        siblings_by_parent: Dict[str, List[str]] = {}
        for p, kids in children_tmp.items():
            kids_sorted = sorted(
                kids,
                key=lambda a: self._sort_key_age_from(index.get(a, {"acronym": a, "age_ma": {"from": None}}))
            )
            siblings_by_parent[p] = kids_sorted

        self.index = index
        self.parent_of = parent_of
        self.siblings_by_parent = siblings_by_parent

    # ---------- region/type helpers ----------

    def _node_regions(self, node: Optional[Dict[str, Any]]) -> Optional[set[str]]:
        if not node:
            return None
        s = node.get("region")
        if not s:
            return None
        return {ch for ch in str(s) if ch.isalpha()}

    def _node_strat_type(self, node: Optional[Dict[str, Any]]) -> Optional[str]:
        if not node:
            return None
        return self._clean_str(node.get("strat_type"))

    def _candidate_ok(
            self,
            base_node: Dict[str, Any],
            cand_node: Dict[str, Any],
            require_same_strat_type: bool,
    ) -> bool:
        # 0) Hard rule: for level<=2 bases, candidates must be CH
        if self._must_force_ch(base_node):
            if self._node_strat_type(cand_node) != "CH":
                return False

        # 1) REGION overlap rule
        if not self._region_overlap(self._node_regions(base_node), self._node_regions(cand_node)):
            return False

        # 2) Strat_Typ preference rule (only applies if we aren't forcing CH)
        if require_same_strat_type:
            return self._node_strat_type(base_node) == self._node_strat_type(cand_node)

        return True

    def _must_force_ch(self, base_node: Dict[str, Any]) -> bool:
        """
        If base level <= 2, only consider CH candidates (per user rule).
        """
        lvl = base_node.get("level")
        try:
            return lvl is not None and int(lvl) <= 2
        except Exception:
            return False

    # ---------- equivalence search ----------

    def _pick_first_older_sibling_with_filters(
        self,
        base_code: str,
        base_node: Dict[str, Any],
        siblings: List[str],  # youngest -> oldest
    ) -> Optional[str]:
        if base_code not in siblings:
            return None
        i = siblings.index(base_code)
        older = siblings[i + 1 :]

        # pass1: REGION overlap + same Strat_Typ
        for c in older:
            cn = self.index.get(c)
            if cn and self._candidate_ok(base_node, cn, require_same_strat_type=True):
                return c

        # pass2: REGION overlap + any Strat_Typ
        for c in older:
            cn = self.index.get(c)
            if cn and self._candidate_ok(base_node, cn, require_same_strat_type=False):
                return c

        return None

    def _choose_child_by_boundary_filtered(
            self,
            children: List[str],
            base_node: Dict[str, Any],
            target_boundary_ma: float,
            require_same_strat_type: bool,
    ) -> Optional[str]:
        """
        Choose child whose age_from best matches the boundary (child.age_from ~= boundary),
        respecting region + (optionally) strat_type preferences.
        """
        scored: List[Tuple[float, float, str]] = []
        for c in children:
            cn = self.index.get(c)
            if not cn:
                continue
            if not self._candidate_ok(base_node, cn, require_same_strat_type=require_same_strat_type):
                continue

            child_from = (cn.get("age_ma") or {}).get("from")
            child_to = (cn.get("age_ma") or {}).get("to")
            if child_from is None:
                continue

            diff = abs(float(child_from) - float(target_boundary_ma))
            # tie-breaker: prefer the youngest matching unit (smaller child_from)
            tie = float(child_from)
            scored.append((diff, tie, c))

        if not scored:
            return None

        scored.sort()
        best_diff, _, best = scored[0]

        # Optional strict tolerance:
        # if best_diff > self.boundary_tol_ma:
        #     return None

        return best

    def find_equivalent_top_for_base_code(self, base_code: str) -> Tuple[bool, Optional[str], Optional[str], str]:
        """
        Returns: (found_base_in_tree, top_code, top_name, status)

        Base boundary convention:
        - Base of a unit = its older boundary = age_ma.to (typically larger Ma).
        - If ages are reversed/missing, we use the max(from,to).
        """
        base_code = self._clean_str(base_code) or ""
        if not base_code:
            return (False, None, None, "empty code")

        base_node = self.index.get(base_code)
        if not base_node:
            return (False, None, None, "not found in stratigraphy tree")

        af = (base_node.get("age_ma") or {}).get("from")
        at = (base_node.get("age_ma") or {}).get("to")
        # Base boundary should be the older one (typically 'to')
        if af is None and at is None:
            base_boundary = None
        elif af is None:
            base_boundary = float(at)
        elif at is None:
            base_boundary = float(af)
        else:
            base_boundary = float(max(af, at))

        parent = self.parent_of.get(base_code)

        # 1) Normal: older sibling (same parent) with REGION/Strat_Typ preferences
        if parent and parent in self.siblings_by_parent:
            sibs = self.siblings_by_parent[parent]
            chosen = self._pick_first_older_sibling_with_filters(base_code, base_node, sibs)
            if chosen:
                return (True, chosen, self.index.get(chosen, {}).get("name"), "ok_filtered_sibling")

        # 2) Fallback: parent's older sibling (same grandparent)
        if not parent:
            return (True, None, None, "found, but no parent available for fallback")

        grandparent = self.parent_of.get(parent)
        if not grandparent or grandparent not in self.siblings_by_parent:
            return (True, None, None, "found, but no grandparent/parent-siblings available for fallback")

        parent_sibs = self.siblings_by_parent[grandparent]
        if parent not in parent_sibs:
            return (True, None, None, "tree inconsistency at fallback")

        pi = parent_sibs.index(parent)
        if pi + 1 >= len(parent_sibs):
            return (True, None, None, "found, but parent has no older sibling for fallback")

        older_parent_sib = parent_sibs[pi + 1]
        children = self.siblings_by_parent.get(older_parent_sib, [])

        # If older_parent_sib has NO children: use it directly (as requested previously)
        if not children:
            cand = self.index.get(older_parent_sib)
            if not cand:
                return (True, None, None, "fallback: parent older sibling missing in index")

            if self._candidate_ok(base_node, cand, require_same_strat_type=True):
                return (True, older_parent_sib, cand.get("name"),
                        "fallback_ok_parent_older_sibling_no_children_same_type")

            if self._candidate_ok(base_node, cand, require_same_strat_type=False):
                return (True, older_parent_sib, cand.get("name"),
                        "fallback_ok_parent_older_sibling_no_children_any_type")

            return (True, None, None, "fallback: parent older sibling fails region/type constraints")

        # Otherwise: choose the child whose age_from matches the base boundary
        if base_boundary is None:
            return (True, None, None, "fallback: missing base boundary age")

        # pass1: REGION overlap + same Strat_Typ
        chosen = self._choose_child_by_boundary_filtered(
            children=children,
            base_node=base_node,
            target_boundary_ma=float(base_boundary),
            require_same_strat_type=True,
        )

        # pass2: REGION overlap + any Strat_Typ
        if not chosen:
            chosen = self._choose_child_by_boundary_filtered(
                children=children,
                base_node=base_node,
                target_boundary_ma=float(base_boundary),
                require_same_strat_type=False,
            )

        if not chosen:
            #return (True, None, None, "fallback: no child matches boundary with region/type preferences")
            # If no equivalent found after all logic:
            fallback_code = f"{base_code},BASE"
            return (
                True,
                fallback_code,
                base_node.get("name"),
                "no_equivalent_found_using_base_BASE"
            )

        return (True, chosen, self.index.get(chosen, {}).get("name"), "fallback_ok_boundary_child_filtered")

    # ---------- Schichtenverzeichnis analysis ----------

    def analyse_schichtenverzeichnis(
        self,
        schichten_xlsx_path: str,
        sheet: Optional[str] = None,
        start_row: int = 2,
        col_code_1based: int = DEFAULT_SCHICHT_COL_CODE,
        col_base_depth_1based: int = DEFAULT_SCHICHT_COL_BASEDEPTH,
    ) -> pd.DataFrame:
        if not self.tree:
            raise RuntimeError("Tree not built yet. Call build_from_file/build_from_dataframe first.")

        df = pd.read_excel(schichten_xlsx_path, sheet_name=sheet if sheet is not None else 0)

        idx_code = col_code_1based - 1
        idx_base_depth = col_base_depth_1based - 1

        out_rows: List[Dict[str, Any]] = []
        start_i = max(0, start_row - 2)

        for i in range(start_i, len(df)):
            code = self._clean_str(df.iloc[i, idx_code]) if idx_code < df.shape[1] else None
            base_depth = self._to_float(df.iloc[i, idx_base_depth]) if idx_base_depth < df.shape[1] else None

            if not code:
                continue

            base_node = self.index.get(code)
            base_name = base_node.get("name") if base_node else None
            base_rank = base_node.get("rank") if base_node else None

            found, top_code, top_name, status = self.find_equivalent_top_for_base_code(code)

            top_node = self.index.get(top_code) if top_code else None
            top_rank = top_node.get("rank") if top_node else None

            out_rows.append({
                "row": i + 2,  # approximate Excel row number
                "base_code": code,
                "equivalent_base_name": base_name,
                "base_rank": base_rank,
                "base_depth": base_depth,
                "equivalent_top_code": top_code if found else None,
                "equivalent_top_name": top_name if found else None,
                "top_rank": top_rank,
                "top_depth": base_depth if found and top_code else None,
                "status": status if found else "not found",
            })

        return pd.DataFrame(out_rows)


# -----------------------------
# CLI
# -----------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="ATS stratigraphy tree + Schichtenverzeichnis equivalent tops (class-based).")
    ap.add_argument("--ats", required=True, help="ATS catalogue file (.xlsx/.csv)")
    ap.add_argument("--ats-sheet", default=None, help="ATS sheet name (optional)")
    ap.add_argument("--schichten", required=True, help="Schichtenverzeichnis Excel (.xlsx)")
    ap.add_argument("--schichten-sheet", default=None, help="Schichtenverzeichnis sheet name (optional)")
    ap.add_argument("--start-row", type=int, default=2, help="Start row in Schichtenverzeichnis (Excel-like, default 2)")
    ap.add_argument("--code-col", type=int, default=DEFAULT_SCHICHT_COL_CODE, help="Schichten code column (1-based, default 5=E)")
    ap.add_argument("--depth-col", type=int, default=DEFAULT_SCHICHT_COL_BASEDEPTH, help="Base depth column (1-based, default 3=C)")
    ap.add_argument("--boundary-tol", type=float, default=0.05, help="Boundary tolerance (Ma) for age_to ~= base.age_from matching")
    ap.add_argument("--strict-region", action="store_true", help="If set, missing REGION will NOT match (region_unknown_ok=False)")
    ap.add_argument("--cols", default=None,
                    help=("Optional JSON to override ATS column mapping, e.g. "
                          '\'{"acronym":"KUERZEL","name":"BEDEUTUNG","parent":"Vater","level":"Level",'
                          '"age_from":"Alter von","age_to":"Alter bis","region":"REGION","strat_type":"Strat_Typ"}\''))
    ap.add_argument("--out-tree", default="stratigraphy_tree.json", help="Output stratigraphy tree JSON path")
    ap.add_argument("-o", "--out-csv", default="schichten_equiv_tops.csv", help="Output analysis CSV path")
    args = ap.parse_args()

    colmap = DEFAULT_COLS
    if args.cols:
        colmap = json.loads(args.cols)

    model = StratigraphyModel(
        cols=colmap,
        level_to_rank=LEVEL_TO_RANK_DEFAULT,
        boundary_tol_ma=args.boundary_tol,
        region_unknown_ok=(not args.strict_region),
    )

    tree = model.build_from_file(args.ats, sheet=args.ats_sheet)
    with open(args.out_tree, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    result = model.analyse_schichtenverzeichnis(
        schichten_xlsx_path=args.schichten,
        sheet=args.schichten_sheet,
        start_row=args.start_row,
        col_code_1based=args.code_col,
        col_base_depth_1based=args.depth_col,
    )
    result.to_csv(args.out_csv, index=False, encoding="utf-8")

    print(f"Wrote tree: {args.out_tree}")
    print(f"Wrote analysis: {args.out_csv}")


if __name__ == "__main__":
    main()