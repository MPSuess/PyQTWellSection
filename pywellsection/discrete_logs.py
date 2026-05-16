import math

import numpy as np


DISCRETE_COLOR_PALETTE = [
    "#4e79a7",
    "#f28e2b",
    "#e15759",
    "#76b7b2",
    "#59a14f",
    "#edc948",
    "#b07aa1",
    "#ff9da7",
    "#9c755f",
    "#bab0ab",
]


def discrete_color_for_index(index):
    return DISCRETE_COLOR_PALETTE[index % len(DISCRETE_COLOR_PALETTE)]


def normalize_discrete_dictionary(dictionary=None, values=None):
    """Return a JSON-friendly number -> {name, color, hatch} dictionary."""
    result = {}
    source = dictionary or {}
    if isinstance(source, dict):
        for raw_key, raw_entry in source.items():
            code = _as_positive_int(raw_key)
            if code is None:
                continue
            if isinstance(raw_entry, dict):
                name = str(raw_entry.get("name", code)).strip() or str(code)
                color = str(raw_entry.get("color", "")).strip()
                hatch = str(raw_entry.get("hatch", "")).strip()
            else:
                name = str(raw_entry).strip() or str(code)
                color = ""
                hatch = ""
            result[str(code)] = {
                "name": name,
                "color": color or discrete_color_for_index(len(result)),
                "hatch": hatch,
            }

    if values is None:
        values = []
    for code in sorted(set(_iter_positive_codes(values))):
        key = str(code)
        if key not in result:
            result[key] = {
                "name": str(code),
                "color": discrete_color_for_index(len(result)),
                "hatch": "",
            }
    return result


def normalize_discrete_log_definition(log_def):
    """
    Normalize a discrete log to:
        {"depth": [...], "values": [positive int, ...], "dictionary": {...}}

    Legacy string categories are translated into positive integer codes while
    preserving first-seen category order.
    """
    if not isinstance(log_def, dict):
        return {"depth": [], "values": [], "dictionary": {}}

    if "top_depths" in log_def:
        depths = log_def.get("top_depths")
    else:
        depths = log_def.get("depth")
    values = log_def.get("values")
    if depths is None:
        depths = []
    if values is None:
        values = []

    n = min(len(depths), len(values))
    depths = list(depths)[:n]
    values = list(values)[:n]

    existing_dictionary = log_def.get("dictionary") or log_def.get("value_dictionary")
    codes, dictionary = values_to_positive_int_codes(
        values,
        existing_dictionary=existing_dictionary,
    )
    return {
        "depth": depths,
        "values": codes,
        "dictionary": dictionary,
    }


def values_to_positive_int_codes(values, existing_dictionary=None):
    """
    Convert arbitrary old values or calculator results into positive int codes.

    Positive integer-like inputs remain their own code. Other labels are assigned
    codes starting at 1 or the next free number, and their label is kept as the
    dictionary name.
    """
    dictionary = normalize_discrete_dictionary(existing_dictionary)
    label_to_code = {
        str(entry.get("name", "")).strip(): int(code)
        for code, entry in dictionary.items()
        if str(entry.get("name", "")).strip()
    }
    used_codes = {int(code) for code in dictionary.keys()}
    next_code = 1

    def allocate_code(label):
        nonlocal next_code
        if label in label_to_code:
            return label_to_code[label]
        while next_code in used_codes:
            next_code += 1
        code = next_code
        used_codes.add(code)
        label_to_code[label] = code
        dictionary[str(code)] = {
            "name": label,
            "color": discrete_color_for_index(len(dictionary)),
            "hatch": "",
        }
        return code

    codes = []
    for value in values:
        code = _as_positive_int(value)
        if code is not None:
            codes.append(code)
            used_codes.add(code)
            key = str(code)
            if key not in dictionary:
                dictionary[key] = {
                    "name": str(code),
                    "color": discrete_color_for_index(len(dictionary)),
                    "hatch": "",
                }
            continue

        label = str(value).strip()
        if not label or label in {"-999", "nan", "NaN", "None"}:
            label = "No value"
        codes.append(allocate_code(label))

    return codes, normalize_discrete_dictionary(dictionary, codes)


def numeric_result_to_positive_codes(values):
    """
    Convert calculator output to positive integer discrete values.

    Non-finite values and values below 1 become code 1, so generated discrete
    logs never contain zero or negative category numbers.
    """
    arr = np.asarray(values, dtype=float)
    codes = np.rint(arr).astype(float)
    invalid = ~np.isfinite(arr) | ~np.isfinite(codes) | (codes < 1)
    codes[invalid] = 1
    codes = codes.astype(int).tolist()
    dictionary = normalize_discrete_dictionary(values=codes)
    return codes, dictionary


def discrete_step_to_depth(depths, values, target_depth):
    """Sample interval-style discrete values onto a target depth grid."""
    depths = np.asarray(depths, dtype=float)
    values = np.asarray(values, dtype=float)
    target_depth = np.asarray(target_depth, dtype=float)
    if depths.size == 0 or values.size == 0 or target_depth.size == 0:
        return np.full_like(target_depth, np.nan, dtype=float)

    n = min(depths.size, values.size)
    depths = depths[:n]
    values = values[:n]
    order = np.argsort(depths)
    depths = depths[order]
    values = values[order]

    idx = np.searchsorted(depths, target_depth, side="right") - 1
    out = np.full_like(target_depth, np.nan, dtype=float)
    mask = idx >= 0
    out[mask] = values[idx[mask]]
    return out


def _iter_positive_codes(values):
    for value in values:
        code = _as_positive_int(value)
        if code is not None:
            yield code


def _as_positive_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, np.integer)):
        return int(value) if int(value) > 0 else None
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            return None
        rounded = int(round(float(value)))
        if rounded > 0 and abs(float(value) - rounded) < 1e-9:
            return rounded
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        f = float(text)
    except ValueError:
        return None
    if not math.isfinite(f):
        return None
    rounded = int(round(f))
    if rounded > 0 and abs(f - rounded) < 1e-9:
        return rounded
    return None
