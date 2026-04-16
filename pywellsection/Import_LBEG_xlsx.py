#!/usr/bin/env python3
"""
XLSX -> consolidated strat marker CSV (; delimiter), BGR/DIN-oriented ranks + QA columns.

Levels:
- System:   q, pg, kr, j, t
- Series:   kro/kru, jo/jm/ju, ko_k, ko_r (and pragmatic qp, pg_e if present)
- Formation: lithostrat/subseries markers like kro_tu, jm_a, ju_z, wd, krv, ...
- Bed:      below-formation members/beds like Rhät-Schiefer etc.

Adds source acronyms for QA:
- SrcCode_5 = column "Hauptformation.1" (XLSX col 5 in your file)
- SrcCode_6 = column "tekt. Attrib."   (XLSX col 6 in your file)

Output columns:
Level;Marker;Name;Top_m;SrcCode_5;SrcCode_6
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd


# -----------------------------
# Helpers
# -----------------------------
def norm(x) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    s = str(x).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def low(x) -> str:
    return norm(x).lower()


EXCLUDE_NAMES = {
    "lücke", "störung", "endteufe", "transgression",
    # broad container rows:
    "o.kreide", "malm", "dogger", "lias", "tertiär",
}


# -----------------------------
# Classification (System/Series)
# -----------------------------
def classify_system_series(name: str) -> Tuple[str, str]:
    u = low(name)

    # Quaternary
    if u.startswith("pleist"):
        return "Quaternary", "Pleistocene"

    # Paleogene
    if "eoz" in u or "septar" in u:
        return "Paleogene", "Eocene"

    # Cretaceous
    if any(k in u for k in ["turon", "cenoman"]):
        return "Cretaceous", "Upper Cretaceous"
    if any(k in u for k in ["alb", "apt", "barrem", "hauter", "valend", "wealden"]):
        return "Cretaceous", "Lower Cretaceous"

    # Jurassic
    if any(k in u for k in ["portland", "gigas", "kimmer", "korallen", "heersum"]):
        return "Jurassic", "Upper Jurassic (Malm)"
    if "ornaten" in u or "dogger" in u:
        return "Jurassic", "Middle Jurassic (Dogger)"
    if "psilonoten" in u or "lias" in u:
        return "Jurassic", "Lower Jurassic (Lias)"

    # Triassic
    if "rhät" in u or "rhaet" in u:
        return "Triassic", "Upper Triassic (Rhaetian)"
    if "keuper" in u or "steinmergel" in u:
        return "Triassic", "Upper Triassic (Keuper)"

    return "", ""


def system_code(system: str) -> str:
    return {
        "Quaternary": "Q",
        "Paleogene": "PG",
        "Cretaceous": "KR",
        "Jurassic": "J",
        "Triassic": "T",
    }.get(system, "")


def series_code(series: str) -> str:
    # Requested series-level codes
    mapping = {
        "Upper Cretaceous": "KRo",
        "Lower Cretaceous": "KRu",
        "Upper Jurassic (Malm)": "Jo",
        "Middle Jurassic (Dogger)": "Jm",
        "Lower Jurassic (Lias)": "Ju",
        "Upper Triassic (Keuper)": "To.k",      # FIXED (was k)
        "Upper Triassic (Rhaetian)": "To.r",
        # pragmatic add-ons (keep if present in your log)
        "Pleistocene": "Qp",
        "Eocene": "PG.e",
    }
    return mapping.get(series, "")


# -----------------------------
# Formation coding (your requested examples: kro_tu, ju_z, jm_a...)
# -----------------------------
def formation_code(name: str) -> str:
    u = low(name)

    # Upper Cretaceous
    if "turon" in u:
        return "KRo.tu"
    if "cenoman" in u:
        return "KRo.ce"

    # Lower Cretaceous (North German style)
    if "wealden" in u:
        return "KRu.wd"
    if "valend" in u:
        return "KRu.v"
    if "hauter" in u:
        return "KRu.h"
    if "barrem" in u:
        return "KRu.u"
    if u.startswith("apt"):
        return "KRu.apt"
    if "alb" in u:
        return "KRu.al"   # generic Alb (your file has O/M/U)

    # Upper Jurassic (Malm)
    if "portland" in u:
        return "Jo.po"
    if "gigas" in u:
        return "Jo, gi"
    if "kimmer" in u:
        return "Jo.ki"
    if "korallen" in u:
        return "Jo,ko"
    if "heersum" in u:
        return "Jo,he"

    # Middle Jurassic (Dogger)
    if "ornaten" in u:
        return "Jm.ot"
    if "dogger" in u:
        if "epsilon" in u:
            return "Jm.e"
        if "delta" in u:
            return "Jm.d"
        if "gamma" in u:
            return "Jm.g"
        if "beta" in u:
            return "Jm.b"
        if "alpha" in u:
            return "Jm.a"

    # Lower Jurassic (Lias)
    if "psilonoten" in u:
        return "Ju.p"
    if "lias" in u:
        if "zeta" in u:
            return "Ju.z"
        if "epsilon" in u:
            return "Ju.e"
        if "delta" in u:
            return "Ju.d"
        if "gamma" in u:
            return "Ju.g"
        if "beta" in u:
            return "Ju.b"
        if "alpha" in u:
            return "Ju.a"

    # We keep Triassic members out of Formation here; they go to Bed.
    return ""


# -----------------------------
# Bed coding (members below formation)
# -----------------------------
def bed_code(name: str, ser_code: str) -> str:
    """
    Beds below Formation.
    Examples requested: Rhät-Schiefer as Bed under ko_r.
    """
    u = low(name)

    # Rhät beds (ko_r)
    if ser_code == "Ko.r" or ("rhät" in u or "rhaet" in u):
        if "schiefer" in u:
            return "Ko.r,rs"
        if "haupt" in u and "sand" in u:
            return "Ko.r,rhs"
        if "sandstein" in u:
            return "Ko.r,rsa"
        if "tonstein" in u or ("ton" in u and "sand" not in u):
            return "Ko.r,rt"
        # fallback Rhät bed
        return "Ko.r,bed"

    # Keuper beds (ko_k)
    if ser_code == "Ko.k" or ("keuper" in u or "steinmergel" in u):
        if "steinmergel" in u:
            return "Ko.k.smk"
        return "Ko.k,bed"

    return ""


# -----------------------------
# Derive tops from running bases
# -----------------------------
def derive_tops_from_bases(df: pd.DataFrame, base_col: str = "Basistiefe") -> pd.DataFrame:
    top = 0.0
    tops: List[float] = []
    bases: List[float] = []

    for _, r in df.iterrows():
        b = r.get(base_col)
        tops.append(float(top))
        if pd.notna(b):
            b = float(b)
            bases.append(b)
            top = b
        else:
            bases.append(np.nan)

    out = df.copy()
    out["Top_m"] = tops
    out["Base_m"] = bases
    return out


# -----------------------------
# Output row model
# -----------------------------
@dataclass(frozen=True)
class OutRow:
    Level: str
    Marker: str
    Name: str
    Top_m: float
    SrcCode_5: str
    SrcCode_6: str


# -----------------------------
# Build markers
# -----------------------------
def build_markers(df: pd.DataFrame) -> pd.DataFrame:
    required = {"Hauptformation", "Basistiefe"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # Prepare rows and pick first occurrence (top) per Hauptformation name
    d = df[df["Hauptformation"].notna()].copy()
    d["Name"] = d["Hauptformation"].map(norm)
    d["_low"] = d["Name"].map(low)

    # attach source acronym cols for QA (if missing, fill blank)
    d["SrcCode_5"] = d.get("Hauptformation.1", "").map(norm) if "Hauptformation.1" in d.columns else ""
    d["SrcCode_6"] = d.get("tekt. Attrib.", "").map(norm) if "tekt. Attrib." in d.columns else ""

    # remove excluded non-strat rows
    d = d[~d["_low"].isin(EXCLUDE_NAMES)].copy()

    # first occurrence = shallowest Top_m
    d = d.sort_values("Top_m", ascending=True).drop_duplicates(subset=["Name"], keep="first").reset_index(drop=True)

    # classify and code
    d["System"] = d["Name"].apply(lambda x: classify_system_series(x)[0])
    d["Series"] = d["Name"].apply(lambda x: classify_system_series(x)[1])
    d["SysCode"] = d["System"].apply(system_code)
    d["SerCode"] = d["Series"].apply(series_code)
    d["FormCode"] = d["Name"].apply(formation_code)
    d["BedCode"] = d.apply(lambda r: bed_code(r["Name"], r["SerCode"]), axis=1)

    out_rows: List[OutRow] = []

    # Formation rows (with QA)
    for _, r in d[d["FormCode"] != ""].iterrows():
        out_rows.append(
            OutRow("Formation", r["FormCode"], r["Name"], float(r["Top_m"]), r["SrcCode_5"], r["SrcCode_6"])
        )

    # Bed rows (with QA)
    for _, r in d[d["BedCode"] != ""].iterrows():
        out_rows.append(
            OutRow("Bed", r["BedCode"], r["Name"], float(r["Top_m"]), r["SrcCode_5"], r["SrcCode_6"])
        )

    # Series tops: min Top_m among coded rows (formation or bed) within that series code
    coded = d[(d["SerCode"] != "") & ((d["FormCode"] != "") | (d["BedCode"] != ""))].copy()
    for (ser_name, ser_code), g in coded.groupby(["Series", "SerCode"], as_index=False):
        top = float(g["Top_m"].min())
        # QA columns blank for derived rollups
        out_rows.append(OutRow("Series", ser_code, ser_name, top, "", ""))

    # System tops: min Top_m among coded rows within that system code
    for (sys_name, sys_code), g in coded.groupby(["System", "SysCode"], as_index=False):
        top = float(g["Top_m"].min())
        out_rows.append(OutRow("System", sys_code, sys_name, top, "", ""))

    out = pd.DataFrame([r.__dict__ for r in out_rows])

    # Sort by depth then hierarchy
    rank = {"System": 0, "Series": 1, "Formation": 2, "Bed": 3}
    out["_rank"] = out["Level"].map(rank).astype(int)
    out = out.sort_values(["Top_m", "_rank", "Marker"], ascending=[True, True, True]).drop(columns="_rank")

    # Deduplicate exact duplicates
    out = out.drop_duplicates(subset=["Level", "Marker", "Top_m"], keep="first").reset_index(drop=True)

    out["SrcCode_5"] = out.apply(
        lambda r: normalize_srccode5(r["SrcCode_5"], r["Marker"]),
        axis=1
    )

    return out[["Level", "Marker", "Name", "Top_m", "SrcCode_5", "SrcCode_6"]]

def normalize_srccode5(src: str, marker: str) -> str:
    """
    If SrcCode_5 is empty, use Marker instead.
    Then convert to UPPER CASE and replace '_' by '.'.
    """
    val = src if src else marker
    return val.upper().replace("_", ".")


def load_LBEG_SV(fn):
    df = pd.read_excel(fn)
    df = derive_tops_from_bases(df, base_col="Basistiefe")
    out = build_markers(df)

    print (out[["Top_m", "SrcCode_5", "Level",]])


if __name__ == "__main__":
    load_LBEG_SV("055689800201_Wagenhoff-2_GeolProfile.xlsx")