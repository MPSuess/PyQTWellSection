#!/usr/bin/env python3
"""
ATS Stratigraphy Tool (consolidated, cleaned)

Implements all requested rules:
- Build stratigraphy tree from ATS (KUERZEL/BEDEUTUNG/Vater/Alter von/bis/Level/REGION/Strat_Typ/VERBOTEN)
- Analyse Schichtenverzeichnis:
  * Sort input by depth before analysis
  * If column E (base_code) empty -> use column F as Top and ALWAYS keep it,
    but remove rows above with the SAME depth
  * If base_code exists -> convert Base->equivalent Top using hierarchy + preferences
  * De-dup at equal depth among base_code rows via:
      CH preferred > region==selected_region preferred > higher rank (smaller level) preferred
  * Fault handling:
      Above a fault => same-level restriction is disabled
      Faults detected from column F text using regex when column E is empty
- Candidate filters:
  * Reject candidates with VERBOTEN == "*"
  * Reject candidates with parent == "-" (no parent)
  * Strict region filter option: only allow units whose REGION contains selected_region
  * Down to level <= same_level_upto: candidates must be same level (unless above_fault)
  * Down to level <= force_ch_upto_level: candidates must be Strat_Typ == "CH"
- Boundary matching:
  * Compare base Alter von (age_from) vs candidate Alter bis (age_to)
  * Pick candidate with smallest absolute difference (best fit)
- If base exists but no equivalent found -> return f"{base_code},BASE"
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np


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
    "verboten": "VERBOTEN",
}

LEVEL_TO_RANK_DEFAULT = {
    0: "Eothem_L0",
    1: "Era_L1",
    2: "System_L2",
    3: "Series_L3",
    4: "regional_unit_L4",
    5: "subunit_L5",
    6: "subunit_L6",
    7: "subunit_L7",
}

# Schichtenverzeichnis columns (1-based indices)
DEFAULT_SCHICHT_COL_BASECODE = 5     # Column E
DEFAULT_SCHICHT_COL_DEPTH = 3        # Column C
DEFAULT_SCHICHT_COL_TOPF = 6         # Column F


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
    verboten: bool = False
    members: List[str] = field(default_factory=list)

    def to_dict(self, nodes_by_key: Dict[str, "Node"], sort_key_fn) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "acronym": self.acronym,
            "name": self.name,
            "parent": self.parent,  # IMPORTANT (needed for candidate exclusion)
            "rank": self.rank,
            "level": self.level,
            "region": "".join(sorted(self.region)) if self.region else None,
            "strat_type": self.strat_type,
            "verboten": self.verboten,
            "age_ma": {"from": self.age_from, "to": self.age_to},
        }
        if self.members:
            children = [nodes_by_key[k].to_dict(nodes_by_key, sort_key_fn) for k in self.members]
            children.sort(key=sort_key_fn)  # youngest -> oldest
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
        region_unknown_ok: bool = True,
        selected_region: Optional[str] = None,
        strict_region_filter: bool = False,
        force_ch_upto_level: int = 2,
        same_level_upto: int = 2,
        fault_regex: str = r"(Stoerung)",
    ) -> None:
        self.cols = cols
        self.level_to_rank = level_to_rank

        self.region_unknown_ok = bool(region_unknown_ok)
        self.selected_region = selected_region.upper() if selected_region else None
        self.strict_region_filter = bool(strict_region_filter)

        self.force_ch_upto_level = int(force_ch_upto_level)
        self.same_level_upto = int(same_level_upto)
        fault_regex = r"(ST)"
        self.fault_regex = re.compile(fault_regex, re.IGNORECASE)

        self.tree: Optional[Dict[str, Any]] = None
        self.index: Dict[str, Dict[str, Any]] = {}
        self.parent_of: Dict[str, Optional[str]] = {}
        self.siblings_by_parent: Dict[str, List[str]] = {}

    # ---------- parsing helpers ----------

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
        if self.region_unknown_ok and (not a or not b):
            return True
        if not a or not b:
            return False
        return len(a.intersection(b)) > 0

    @staticmethod
    def _sort_key_age_from(node_dict: Dict[str, Any]) -> Tuple[int, float, str]:
        af = ((node_dict.get("age_ma") or {}).get("from"))
        if af is None:
            return (1, float("inf"), node_dict.get("acronym", ""))
        return (0, float(af), node_dict.get("acronym", ""))

    # ---------- build / index ----------

    def build_from_file(self, ats_path: str, sheet: Optional[str] = None) -> Dict[str, Any]:
        df = read_table(ats_path, sheet=sheet)
        return self.build_from_dataframe(df)

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
            parent_raw = self._clean_str(row[c["parent"]])
            # Normalize "no parent" markers to None
            parent = None if parent_raw in (None, "", "-") else parent_raw

            level = self._to_int(row[c["level"]])
            age_from = self._to_float(row[c["age_from"]])
            age_to = self._to_float(row[c["age_to"]])

            verboten_val = self._clean_str(row.get(c.get("verboten")))
            verboten = (verboten_val == "*")

            region = self._parse_regions(row[c["region"]]) if c.get("region") in df.columns else None
            strat_type = self._clean_str(row[c["strat_type"]]) if c.get("strat_type") in df.columns else None

            n = nodes.get(acronym) or Node(acronym=acronym)
            nodes[acronym] = n

            n.name = name if name is not None else n.name
            n.parent = parent
            n.level = level if level is not None else n.level
            n.age_from = age_from if age_from is not None else n.age_from
            n.age_to = age_to if age_to is not None else n.age_to
            n.rank = self._rank_from_level(n.level)
            n.verboten = verboten

            n.region = region if region is not None else n.region
            n.strat_type = strat_type if strat_type is not None else n.strat_type

        # stubs for referenced parents
        for n in list(nodes.values()):
            if n.parent and n.parent not in nodes:
                nodes[n.parent] = Node(acronym=n.parent, parent=None, rank="unknown")

        # adjacency
        for n in nodes.values():
            if n.parent and n.parent in nodes:
                nodes[n.parent].members.append(n.acronym)

        roots = [n for n in nodes.values() if not n.parent]
        root_dicts = [r.to_dict(nodes, self._sort_key_age_from) for r in roots]
        root_dicts.sort(key=self._sort_key_age_from)

        self.tree = {"stratigraphy": root_dicts}
        self._index_tree()
        return self.tree

    def _index_tree(self) -> None:
        if not self.tree:
            raise RuntimeError("Tree not built yet.")

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
            siblings_by_parent[p] = sorted(
                kids,
                key=lambda a: self._sort_key_age_from(index.get(a, {"acronym": a, "age_ma": {"from": None}}))
            )

        self.index = index
        self.parent_of = parent_of
        self.siblings_by_parent = siblings_by_parent

    # ---------- node attribute helpers ----------

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

    def _is_valid_for_selected_region(self, node: Dict[str, Any]) -> bool:
        if not self.strict_region_filter or not self.selected_region:
            return True
        regs = self._node_regions(node)
        return bool(regs and self.selected_region in regs)

    def _must_force_ch(self, base_node: Dict[str, Any]) -> bool:
        try:
            lvl = base_node.get("level")
            return lvl is not None and int(lvl) <= self.force_ch_upto_level
        except Exception:
            return False

    def _must_force_same_level(self, base_node: Dict[str, Any], above_fault: bool) -> bool:
        if above_fault:
            return False
        try:
            lvl = base_node.get("level")
            return lvl is not None and int(lvl) <= self.same_level_upto
        except Exception:
            return False

    # ---------- boundary helpers (requested) ----------

    def _base_boundary_from(self, base_node: Dict[str, Any]) -> Optional[float]:
        """Base boundary uses Alter von == age_from."""
        af = (base_node.get("age_ma") or {}).get("from")
        return float(af) if af is not None else None

    @staticmethod
    def _cand_boundary_to(cand_node: Dict[str, Any]) -> Optional[float]:
        """Candidate boundary uses Alter bis == age_to."""
        at = (cand_node.get("age_ma") or {}).get("to")
        return float(at) if at is not None else None

    # ---------- candidate filter ----------

    def _candidate_ok(
        self,
        base_node: Dict[str, Any],
        cand_node: Dict[str, Any],
        require_same_strat_type: bool,
        above_fault: bool,
    ) -> bool:
        # Reject VERBOTEN
        if cand_node.get("verboten") is True:
            return False

        # NEW RULE: candidate must not be younger than base (by Alter von)
        base_from = (base_node.get("age_ma") or {}).get("from")
        cand_from = (cand_node.get("age_ma") or {}).get("from")
        if base_from is not None and cand_from is not None:
            # younger => smaller Ma; reject if candidate starts younger than base
            if float(cand_from) < float(base_from):
                return False

        # NEW RULE: reject candidates with the same "Alter bis" (age_ma.to) as the base unit
        base_to = (base_node.get("age_ma") or {}).get("to")
        cand_to = (cand_node.get("age_ma") or {}).get("to")
        if base_to is not None and cand_to is not None:
            if float(cand_to) == float(base_to):
                return False


        # NEW RULE: If base_code contains ".", candidate must also contain "."
        base_code = base_node.get("acronym")
        cand_code = cand_node.get("acronym")

        if base_code and "." in base_code:
            if not cand_code or "," in cand_code:
                return False

        # Reject candidates with no parent (Vater == "-" / None / "")
        cand_parent = cand_node.get("parent")
        if cand_parent is None or str(cand_parent).strip() in ("", "-"):
            return False

        # Strict region restriction
        if not self._is_valid_for_selected_region(cand_node):
            return False

        # Same-level restriction down to level N (except above_fault)
        if self._must_force_same_level(base_node, above_fault=above_fault):
            try:
                if int(cand_node.get("level")) != int(base_node.get("level")):
                    return False
            except Exception:
                return False

        # Force CH down to level N
        if self._must_force_ch(base_node):
            if self._node_strat_type(cand_node) != "CH":
                return False

        # Region overlap preference
        if not self._region_overlap(self._node_regions(base_node), self._node_regions(cand_node)):
            return False

        # Strat type preference
        if require_same_strat_type:
            return self._node_strat_type(base_node) == self._node_strat_type(cand_node)

        return True


    def _level_value(self, node: Optional[Dict[str, Any]]) -> int:
        try:
            return int(node.get("level")) if node and node.get("level") is not None else 999
        except Exception:
            return 999

    def _is_sibling_of_unit(self, base_code: str, cand_code: str) -> bool:
        pb = self.parent_of.get(base_code)
        pc = self.parent_of.get(cand_code)
        return bool(pb and pc and pb == pc)

    def _is_sibling_of_parent(self, base_code: str, cand_code: str) -> bool:
        pb = self.parent_of.get(base_code)
        if not pb:
            return False
        gpb = self.parent_of.get(pb)
        if not gpb:
            return False
        pc = self.parent_of.get(cand_code)
        return bool(pc and pc == gpb)

    def _prefer_below_candidate(
            self,
            base_code: str,
            base_node: Dict[str, Any],
            preferred_code: Optional[str],
            above_fault: bool,
    ) -> Optional[Tuple[str, str]]:
        """
        Returns (cand_code, status) if preferred_code should be used, else None.
        Hard exclusions still apply via _candidate_ok(...).
        """
        if not preferred_code:
            return None

        preferred_code = self._clean_str(preferred_code)
        if not preferred_code:
            return None

        cand_node = self.index.get(preferred_code)
        if not cand_node:
            return None

        # same or higher rank => cand.level <= base.level
        if self._level_value(cand_node) > self._level_value(base_node):
            return None

        # sibling of unit OR sibling of parent
        if not (self._is_sibling_of_unit(base_code, preferred_code) or self._is_sibling_of_parent(base_code,
                                                                                                  preferred_code)):
            return None

        # must still pass candidate filters (use relaxed strat_type preference)
        if not self._candidate_ok(base_node, cand_node, require_same_strat_type=False, above_fault=above_fault):
            return None

        return (preferred_code, "preferred_below_unit")

    # -------------------------
    # 2) Change signature + logic of find_equivalent_top_for_base_code
    #    Replace your method header and add the "preferred below" block near the start
    # -------------------------


    # -------------------------
    # 3) Update analyse_schichtenverzeichnis to pass the below unit code
    #    In your loop, BEFORE calling find_equivalent..., compute below_unit_code from row i+1
    # -------------------------

    # Inside analyse_schichtenverzeichnis() loop, just before:
    #   found, top_code, top_name, status = self.find_equivalent_top_for_base_code(...)
    # insert this:



    # =========================
    # END PATCH
    # =========================


    def _pick_best_older_sibling_by_boundary(
        self,
        base_code: str,
        base_node: Dict[str, Any],
        siblings: List[str],
        above_fault: bool,
    ) -> Optional[str]:
        """
        Among older siblings, pick candidate minimizing:
          abs(base.age_from - candidate.age_to)
        Two passes:
          pass1 same Strat_Typ
          pass2 relaxed Strat_Typ
        """
        if base_code not in siblings:
            return None

        base_from = self._base_boundary_from(base_node)
        if base_from is None:
            return None

        i = siblings.index(base_code)
        older = siblings[i + 1 :]

        def best(require_same: bool) -> Optional[str]:
            scored: List[Tuple[float, str]] = []
            for c in older:
                cn = self.index.get(c)
                if not cn:
                    continue
                if not self._candidate_ok(base_node, cn, require_same_strat_type=require_same, above_fault=above_fault):
                    continue
                cand_to = self._cand_boundary_to(cn)
                if cand_to is None:
                    continue
                diff = abs(float(base_from) - float(cand_to))
                scored.append((diff, c))
            if not scored:
                return None
            scored.sort()
            return scored[0][1]

        return best(True) or best(False)

    def _choose_best_child_by_boundary(
        self,
        children: List[str],
        base_node: Dict[str, Any],
        above_fault: bool,
    ) -> Optional[str]:
        """
        Choose child minimizing abs(base.age_from - child.age_to),
        with same-type pass first then relaxed.
        """
        base_from = self._base_boundary_from(base_node)
        if base_from is None:
            return None

        def best(require_same: bool) -> Optional[str]:
            scored: List[Tuple[float, str]] = []
            for c in children:
                cn = self.index.get(c)
                if not cn:
                    continue
                if not self._candidate_ok(base_node, cn, require_same_strat_type=require_same, above_fault=above_fault):
                    continue
                cand_to = self._cand_boundary_to(cn)
                if cand_to is None:
                    continue
                diff = abs(float(base_from) - float(cand_to))
                scored.append((diff, c))
            if not scored:
                return None
            scored.sort()
            return scored[0][1]

        return best(True) or best(False)

    # ---------- main equivalence ----------
    def find_equivalent_top_for_base_code(
            self,
            base_code: str,
            above_fault: bool = False,
            preferred_candidate_code: Optional[str] = None,  # NEW
    ) -> Tuple[bool, Optional[str], Optional[str], str]:

        base_code = self._clean_str(base_code) or ""
        if not base_code:
            return (False, None, None, "empty code")

        base_node = self.index.get(base_code)
        if not base_node:
            return (False, None, None, "not found in stratigraphy tree")

        if not self._is_valid_for_selected_region(base_node):
            return (False, None, None, "base_not_valid_in_selected_region")

        # NEW: Prefer unit below if it qualifies (before all other considerations)
        preferred = self._prefer_below_candidate(
            base_code=base_code,
            base_node=base_node,
            preferred_code=preferred_candidate_code,
            above_fault=above_fault,
        )
        if preferred:
            cand_code, status = preferred
            return (True, cand_code, self.index.get(cand_code, {}).get("name"), status)

        parent = self.parent_of.get(base_code)

        # 1) Older sibling under same parent (best-fit boundary)
        if parent and parent in self.siblings_by_parent:
            sibs = self.siblings_by_parent[parent]
            chosen = self._pick_best_older_sibling_by_boundary(base_code, base_node, sibs, above_fault=above_fault)
            if chosen:
                return (True, chosen, self.index.get(chosen, {}).get("name"), "ok_filtered_sibling_bestfit")

        # 2) Fallback: parent's older sibling under grandparent
        if not parent:
            fb = f"{base_code},BASE"
            return (True, fb, base_node.get("name"), "no_equivalent_found_using_base_BASE")

        grandparent = self.parent_of.get(parent)
        if not grandparent or grandparent not in self.siblings_by_parent:
            fb = f"{base_code},BASE"
            return (True, fb, base_node.get("name"), "no_equivalent_found_using_base_BASE")

        parent_sibs = self.siblings_by_parent[grandparent]
        if parent not in parent_sibs:
            fb = f"{base_code},BASE"
            return (True, fb, base_node.get("name"), "no_equivalent_found_using_base_BASE")

        pi = parent_sibs.index(parent)
        if pi + 1 >= len(parent_sibs):
            fb = f"{base_code},BASE"
            return (True, fb, base_node.get("name"), "no_equivalent_found_using_base_BASE")

        older_parent_sib = parent_sibs[pi + 1]
        children = self.siblings_by_parent.get(older_parent_sib, [])

        if not children:
            cand = self.index.get(older_parent_sib)
            if cand and self._candidate_ok(base_node, cand, require_same_strat_type=True, above_fault=above_fault):
                return (True, older_parent_sib, cand.get("name"), "fallback_parent_older_sibling_no_children_same_type")
            if cand and self._candidate_ok(base_node, cand, require_same_strat_type=False, above_fault=above_fault):
                return (True, older_parent_sib, cand.get("name"), "fallback_parent_older_sibling_no_children_any_type")

            fb = f"{base_code},BASE"
            return (True, fb, base_node.get("name"), "no_equivalent_found_using_base_BASE")

        chosen = self._choose_best_child_by_boundary(children, base_node, above_fault=above_fault)
        if chosen:
            return (True, chosen, self.index.get(chosen, {}).get("name"), "fallback_ok_child_bestfit")

        fb = f"{base_code},BASE"
        return (True, fb, base_node.get("name"), "no_equivalent_found_using_base_BASE")



    def find_equivalent_top_for_base_code_o(
        self,
        base_code: str,
        above_fault: bool = False,
    ) -> Tuple[bool, Optional[str], Optional[str], str]:
        base_code = self._clean_str(base_code) or ""
        if not base_code:
            return (False, None, None, "empty code")

        base_node = self.index.get(base_code)
        if not base_node:
            return (False, None, None, "not found in stratigraphy tree")

        if not self._is_valid_for_selected_region(base_node):
            return (False, None, None, "base_not_valid_in_selected_region")

        parent = self.parent_of.get(base_code)

        # 1) Older sibling under same parent
        if parent and parent in self.siblings_by_parent:
            sibs = self.siblings_by_parent[parent]
            chosen = self._pick_best_older_sibling_by_boundary(base_code, base_node, sibs, above_fault=above_fault)
            if chosen:
                return (True, chosen, self.index.get(chosen, {}).get("name"), "ok_filtered_sibling_bestfit")

        # 2) Fallback: parent's older sibling under grandparent
        if not parent:
            fb = f"{base_code},BASE"
            return (True, fb, base_node.get("name"), "no_equivalent_found_using_base_BASE")

        grandparent = self.parent_of.get(parent)
        if not grandparent or grandparent not in self.siblings_by_parent:
            fb = f"{base_code},BASE"
            return (True, fb, base_node.get("name"), "no_equivalent_found_using_base_BASE")

        parent_sibs = self.siblings_by_parent[grandparent]
        if parent not in parent_sibs:
            fb = f"{base_code},BASE"
            return (True, fb, base_node.get("name"), "no_equivalent_found_using_base_BASE")

        pi = parent_sibs.index(parent)
        if pi + 1 >= len(parent_sibs):
            fb = f"{base_code},BASE"
            return (True, fb, base_node.get("name"), "no_equivalent_found_using_base_BASE")

        older_parent_sib = parent_sibs[pi + 1]
        children = self.siblings_by_parent.get(older_parent_sib, [])

        # 2a) If no children: try using the older parent sibling itself
        if not children:
            cand = self.index.get(older_parent_sib)
            if cand and self._candidate_ok(base_node, cand, require_same_strat_type=True, above_fault=above_fault):
                return (True, older_parent_sib, cand.get("name"), "fallback_parent_older_sibling_no_children_same_type")
            if cand and self._candidate_ok(base_node, cand, require_same_strat_type=False, above_fault=above_fault):
                return (True, older_parent_sib, cand.get("name"), "fallback_parent_older_sibling_no_children_any_type")

            fb = f"{base_code},BASE"
            return (True, fb, base_node.get("name"), "no_equivalent_found_using_base_BASE")

        # 2b) Choose best child by boundary
        chosen = self._choose_best_child_by_boundary(children, base_node, above_fault=above_fault)
        if chosen:
            return (True, chosen, self.index.get(chosen, {}).get("name"), "fallback_ok_child_bestfit")

        fb = f"{base_code},BASE"
        return (True, fb, base_node.get("name"), "no_equivalent_found_using_base_BASE")

    # ---------- Schichtenverzeichnis analysis ----------

    def analyse_schichtenverzeichnis(
        self,
        schichten_xlsx_path: str,
        sheet: Optional[str] = None,
        start_row: int = 2,
        col_basecode_1based: int = DEFAULT_SCHICHT_COL_BASECODE,  # E
        col_depth_1based: int = DEFAULT_SCHICHT_COL_DEPTH,        # C
        col_top_1based: int = DEFAULT_SCHICHT_COL_TOPF,           # F
    ) -> pd.DataFrame:
        if not self.tree:
            raise RuntimeError("Tree not built yet. Call build_from_file/build_from_dataframe first.")

        #df = pd.read_excel(schichten_xlsx_path, sheet_name=sheet if sheet is not None else 0)
        df = pd.read_excel(schichten_xlsx_path, sheet_name=sheet if sheet is not None else 0, engine="openpyxl")


        idx_basecode = col_basecode_1based - 1
        idx_depth = col_depth_1based - 1
        idx_top = col_top_1based - 1

        # ---- sort by depth (requested) ----
        if idx_depth < df.shape[1]:
            df["_depth_numeric"] = pd.to_numeric(df.iloc[:, idx_depth], errors="coerce")
            df = df[df["_depth_numeric"].notna()].copy()
            df = df.sort_values("_depth_numeric", ascending=True).reset_index(drop=True)
            df.iloc[:, idx_depth] = df["_depth_numeric"]
            df = df.drop(columns=["_depth_numeric"])

        # ---- detect faults (for "above_fault" rule) ----
        fault_depths: List[float] = []
        for r in range(len(df)):
            dep = self._to_float(df.iloc[r, idx_depth]) if idx_depth < df.shape[1] else None
            if dep is None:
                continue
            e_code = self._clean_str(df.iloc[r, idx_basecode]) if idx_basecode < df.shape[1] else None
            f_txt = self._clean_str(df.iloc[r, idx_top]) if idx_top < df.shape[1] else None
            if (not e_code) and f_txt and self.fault_regex.search(f_txt):
                fault_depths.append(float(dep))
        fault_depths = sorted(set(fault_depths))

        def is_above_fault(depth: float) -> bool:
            # True if there exists a fault deeper than this depth
            for fd in fault_depths:
                if fd > depth:
                    return True
            return False

        out_rows: List[Dict[str, Any]] = []

        def append_with_dedup(new_row: Dict[str, Any]) -> None:
            """
            De-dup rules at same depth:

            - If new_row has empty base_code:
                ALWAYS keep new_row,
                BUT remove all rows above with SAME depth, then append.

            - If new_row has base_code:
                If same depth and previous row has base_code -> tie-break keep better:
                    CH > region==selected_region > higher rank (smaller level) > keep new
                If previous has empty base_code -> never drop it; keep both
            """
            def same_depth(a: Any, b: Any) -> bool:
                try:
                    return a is not None and b is not None and float(a) == float(b)
                except Exception:
                    return False

            if not out_rows:
                out_rows.append(new_row)
                return

            new_depth = new_row.get("top_depth")
            if new_depth is None:
                out_rows.append(new_row)
                return

            # Empty base_code rows: remove rows above with same depth, then keep
            if not new_row.get("base_code"):
                while out_rows and same_depth(out_rows[-1].get("top_depth"), new_depth):
                    out_rows.pop()
                out_rows.append(new_row)
                return

            prev_row = out_rows[-1]
            prev_depth = prev_row.get("top_depth")

            if not same_depth(prev_depth, new_depth):
                out_rows.append(new_row)
                return

            # if previous is empty base_code -> keep both
            if not prev_row.get("base_code"):
                out_rows.append(new_row)
                return

            # tie-break among base_code rows at same depth
            def node_for_row(r: Dict[str, Any]) -> Optional[Dict[str, Any]]:
                code = r.get("base_code") or r.get("equivalent_top_code")
                return self.index.get(code) if code else None

            def score(r: Dict[str, Any]) -> Tuple[int, int, int]:
                n = node_for_row(r)
                st = n.get("strat_type") if n else None
                ch_penalty = 0 if st == "CH" else 1

                if not self.selected_region:
                    region_penalty = 0
                else:
                    regs = self._node_regions(n) if n else None
                    region_penalty = 0 if regs and self.selected_region in regs else 1

                try:
                    lvl = int(n.get("level")) if n else 999
                except Exception:
                    lvl = 999

                return (ch_penalty, region_penalty, lvl)

            if score(new_row) <= score(prev_row):
                out_rows.pop()
                out_rows.append(new_row)
            # else keep prev

        # iteration
        start_i = max(0, start_row - 2)
        for i in range(start_i, len(df)):
            base_code = self._clean_str(df.iloc[i, idx_basecode]) if idx_basecode < df.shape[1] else None
            depth = self._to_float(df.iloc[i, idx_depth]) if idx_depth < df.shape[1] else None
            top_from_f = self._clean_str(df.iloc[i, idx_top]) if idx_top < df.shape[1] else None

            if depth is None:
                continue

            # Case 1: Column E empty -> use Column F as Top (always keep; also drives fault markers)
            if not base_code and top_from_f:
                top_node = self.index.get(top_from_f)
                top_name = top_node.get("name") if top_node else top_from_f
                top_rank = top_node.get("rank") if top_node else None

                #print(top_name)
                if top_name:
                    print(top_name,self.fault_regex.search(top_name))
                    # print(f"{base_code} -> {top_code} ({status})")
                    pattern = re.compile(r"\*")
                    if pattern.findall(top_name):
                        type = "other"
                    if self.fault_regex.search(top_name):
                        #print("fault")
                        type = "fault"
                    if top_rank: type = "stratigraphy"
                else:
                    type = "other"



                row_out = {
                    "row": i + 2,
                    "base_code": None,
                    "equivalent_base_name": None,
                    "base_rank": None,
                    "base_depth": depth,
                    "equivalent_top_code": top_from_f,
                    "equivalent_top_name": top_name,
                    "top_rank": top_rank,
                    "top_depth": depth,
                    "status": "top_from_column_F",
                    "type": type,
                }
                append_with_dedup(row_out)
                continue

            # Case 2: Column E filled -> convert base -> top
            if not base_code:
                continue

            base_node = self.index.get(base_code)
            base_name = base_node.get("name") if base_node else None
            base_rank = base_node.get("rank") if base_node else None

            above_fault = is_above_fault(float(depth))

            below_unit_code: Optional[str] = None
            if i + 1 < len(df):
                below_base = self._clean_str(df.iloc[i + 1, idx_basecode]) if idx_basecode < df.shape[1] else None
                below_topf = self._clean_str(df.iloc[i + 1, idx_top]) if idx_top < df.shape[1] else None
                below_unit_code = below_base if below_base else below_topf

            # Then change the call to:
            found, top_code, top_name, status = self.find_equivalent_top_for_base_code(
                base_code,
                above_fault=above_fault,
                preferred_candidate_code=below_unit_code,
            )


            #found, top_code, top_name, status = self.find_equivalent_top_for_base_code(base_code, above_fault=above_fault)

            top_node = self.index.get(top_code) if top_code else None
            top_rank = top_node.get("rank") if top_node else None
            #print(top_code)
            if top_name:
                #print(f"{base_code} -> {top_code} ({status})")
                if self.fault_regex.search(top_name):
                    #print("fault")
                    type = "fault"
                else: "other"
                if top_rank: type = "stratigraphy"
            else:
                type = "other"

            row_out = {
                "row": i + 2,
                "base_code": base_code,
                "equivalent_base_name": base_name,
                "base_rank": base_rank,
                "base_depth": depth,
                "equivalent_top_code": top_code if found else f"{base_code},BASE",
                "equivalent_top_name": top_name if found else base_name,
                "top_rank": top_rank,
                "top_depth": depth,
                "status": status,
                "type": type,
                "above_fault": above_fault,
            }
            append_with_dedup(row_out)

        return pd.DataFrame(out_rows)

import random

def random_strat_color(seed=None):
    """
    Generate a random, visually pleasant color for stratigraphic units.

    Parameters
    ----------
    seed : Optional[int]
        If provided, color generation becomes reproducible.

    Returns
    -------
    str
        Hex color string, e.g. '#7fbf7f'
    """
    if seed is not None:
        random.seed(seed)

    # avoid extremes (too dark / too bright)
    r = random.randint(60, 220)
    g = random.randint(60, 220)
    b = random.randint(60, 220)

    return f"#{r:02x}{g:02x}{b:02x}"

# -----------------------------
# CLI
# -----------------------------
def bgr_sv_load_tree(tree_path: str, schichten_xlsx_path: str):
    colmap = DEFAULT_COLS

    model = StratigraphyModel(
        cols=colmap,
        level_to_rank=LEVEL_TO_RANK_DEFAULT,
        region_unknown_ok=False,
        selected_region="N",
        strict_region_filter=True,
        force_ch_upto_level=3,
    )

    tree = model.build_from_file(ats_path=tree_path)
    #with open("testxxx.json", "w", encoding="utf-8") as f:
    #    json.dump(tree, f, ensure_ascii=False, indent=2)

    result = model.analyse_schichtenverzeichnis(
        schichten_xlsx_path=schichten_xlsx_path,
        start_row=2
    )
    #with open("testx.json", "w", encoding="utf-8") as f:
    #    json.dump(result.to_json(), f, ensure_ascii=False, indent=2)

    key = result["equivalent_top_code"].tolist()
    role = result["type"].tolist()
    level = result["top_rank"].tolist()
    full_name = result["equivalent_top_name"].tolist()
    base_d = top_d = result["base_depth"].tolist()

    tops: List[Dict[str, Any]] = []
    strat_updates: Dict[str, Dict[str, Any]] = {}
    td=0

    #for t in result:

    for i in range(len(key)):


        # Required: Use abbreviation as top key

        # If abbreviation is missing: generate deterministic key
        # if not key[i]:
        #     if role[i] == "fault":
        #         key[i] = f"*ST_{top_d:.2f}"
        #     elif role[i] == "other":
        #         key[i] = f"*OTHER_{top_d:.2f}"
        #     else:
        #         # keep a readable fallback
        #         fn = full_name if full_name else "TOP"
        #         key[i] = f"{fn}_{top_d:.2f}"

        # Track stratigraphy update:
        # - store "Full Name" (requested exact field)
        # - store role/level
        if key[i] not in strat_updates:
            strat_updates[key[i]] = {"Full Name": full_name[i], "role": role[i], "level": level[i], "color": random_strat_color(),
                                  "hatch": "-"}
        else:
            # keep first full name if already set; but fill if missing
            if not strat_updates[key[i]].get("Full Name"):
                strat_updates[key[i]]["Full Name"] = full_name
            strat_updates[key[i]].setdefault("role", role[i])
            strat_updates[key[i]].setdefault("level", level[i])
            strat_updates[key[i]].setdefault("color", random_strat_color())
            strat_updates[key[i]].setdefault("hatch", "-")

        tops.append({"key": key[i], "full_name": full_name[i], "depth": top_d[i], "role": role[i], "color": random_strat_color(),
                     "hatch": "-"})

        td = max(td, base_d[i])

    return tops, float(td), strat_updates





def main() -> None:
    ap = argparse.ArgumentParser(description="ATS stratigraphy tree + Schichtenverzeichnis equivalent tops.")
    ap.add_argument("--ats", required=True, help="ATS catalogue file (.xlsx/.csv)")
    ap.add_argument("--ats-sheet", default=None, help="ATS sheet name (optional)")
    ap.add_argument("--schichten", required=True, help="Schichtenverzeichnis Excel (.xlsx)")
    ap.add_argument("--schichten-sheet", default=None, help="Schichtenverzeichnis sheet name (optional)")
    ap.add_argument("--start-row", type=int, default=2, help="Start row in Schichtenverzeichnis (Excel-like, default 2)")
    ap.add_argument("--code-col", type=int, default=DEFAULT_SCHICHT_COL_BASECODE, help="Base code column (1-based, default 5=E)")
    ap.add_argument("--depth-col", type=int, default=DEFAULT_SCHICHT_COL_DEPTH, help="Depth column (1-based, default 3=C)")
    ap.add_argument("--top-col", type=int, default=DEFAULT_SCHICHT_COL_TOPF, help="Top/Fallback column (1-based, default 6=F)")
    ap.add_argument("--region", default=None, help="Selected region letter (e.g. N, S, R, O)")
    ap.add_argument("--strict-region-filter", action="store_true", help="Only consider ATS units valid in selected region")
    ap.add_argument("--strict-region-overlap", action="store_true", help="If set, missing REGION does NOT match (region_unknown_ok=False)")
    ap.add_argument("--force-ch-upto-level", type=int, default=2, help="For base.level<=N: candidates must be CH (default 2)")
    ap.add_argument("--same-level-upto", type=int, default=2, help="For base.level<=N: candidates must be same level (unless above fault) (default 2)")
    ap.add_argument("--fault-regex", default=r"(fault|störung|stoerung)", help="Regex for fault detection in column F")
    ap.add_argument("--cols", default=None, help="Optional JSON to override ATS column mapping")
    ap.add_argument("--out-tree", default="stratigraphy_tree.json", help="Output stratigraphy tree JSON path")
    ap.add_argument("--out-csv", default="schichten_equiv_tops.csv", help="Output analysis CSV path")
    args = ap.parse_args()

    colmap = DEFAULT_COLS
    if args.cols:
        colmap = json.loads(args.cols)

    print (args.strict_region_filter, args.ats, args.ats_sheet)

    model = StratigraphyModel(
        cols=colmap,
        level_to_rank=LEVEL_TO_RANK_DEFAULT,
        region_unknown_ok=(not args.strict_region_overlap),
        selected_region=args.region,
        strict_region_filter=args.strict_region_filter,
        force_ch_upto_level=args.force_ch_upto_level,
        same_level_upto=args.same_level_upto,
        fault_regex=args.fault_regex,
    )

    tree = model.build_from_file(args.ats, sheet=args.ats_sheet)
    with open(args.out_tree, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    result = model.analyse_schichtenverzeichnis(
        schichten_xlsx_path=args.schichten,
        sheet=args.schichten_sheet,
        start_row=args.start_row,
        col_basecode_1based=args.code_col,
        col_depth_1based=args.depth_col,
        col_top_1based=args.top_col,
    )
    result.to_csv(args.out_csv, index=False, encoding="utf-8")

    print(f"Wrote tree: {args.out_tree}")
    print(f"Wrote analysis: {args.out_csv}")


if __name__ == "__main__":
    main()