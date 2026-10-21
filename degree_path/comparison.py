"""Display rules for database comparisons; no overall ranking is implied."""

MAJOR_METRICS = [
    {"key": "earnings", "label": "Median of reported program earnings", "format": "money", "direction": "higher",
     "note": "Median across program-level four-year earnings medians in the database; not a graduate-weighted median."},
    {"key": "program_count", "label": "Programs in our database", "format": "number", "direction": None},
    {"key": "school_count", "label": "Schools in our database", "format": "number", "direction": None},
    {"key": "description", "label": "About this major", "format": "text", "direction": None},
    {"key": "description_source", "label": "Description source", "format": "text", "direction": None},
]

PROGRAM_METRICS = [
    {"key": "college", "label": "School", "format": "text", "direction": None},
    {"key": "location", "label": "Location", "format": "text", "direction": None},
    {"key": "credential", "label": "Credential", "format": "text", "direction": None},
    {"key": "earnings", "label": "Median annual earnings", "format": "money", "direction": "higher", "note": "Four years after program completion."},
]
for key, label in [
    ("npt4", "Average annual net price"),
    ("tuitionfee_in", "In-state tuition and fees"),
    ("tuitionfee_out", "Out-of-state tuition and fees"),
    ("npt41", "Net price · household income $0–30,000"),
    ("npt42", "Net price · household income $30,001–48,000"),
    ("npt43", "Net price · household income $48,001–75,000"),
    ("npt44", "Net price · household income $75,001–110,000"),
    ("npt45", "Net price · household income over $110,000"),
]:
    PROGRAM_METRICS.append({"key": key, "label": label, "format": "money", "direction": "lower", "note": "School-level annual cost, not specific to this program."})
PROGRAM_METRICS += [
    {"key": "adm_rate", "label": "Admission rate", "format": "percent", "direction": None, "note": "School-level rate; not your individual admission probability."},
    {"key": "enrollment", "label": "Undergraduate enrollment (12 months)", "format": "number", "direction": None},
]
for key, label in [("satmt", "SAT math"), ("satvr", "SAT reading"), ("satwr", "SAT writing"), ("actmt", "ACT math"), ("acten", "ACT English"), ("actwr", "ACT writing")]:
    PROGRAM_METRICS.append({"key": key, "label": label + " · middle 50%", "format": "range", "direction": None, "note": "School-level 25th–75th percentile scores."})

CREDENTIALS = {1: "Undergraduate certificate", 2: "Associate degree", 3: "Bachelor’s degree", 4: "Post-baccalaureate certificate", 5: "Master’s degree", 6: "Doctoral degree", 7: "First professional degree", 8: "Graduate/professional certificate"}


def comparison_payload(kind, rows):
    items = []
    for row in rows:
        item = dict(row)
        if kind == "programs":
            item["credential"] = CREDENTIALS.get(item.get("credlev"), "Not reported")
            item["location"] = ", ".join(value for value in (item.get("city"), item.get("state")) if value)
            for key in ("satmt", "satvr", "satwr", "actmt", "acten", "actwr"):
                item[key] = [item.pop(key + "25", None), item.pop(key + "75", None)]
            if item.get("adm_rate") is not None:
                item["adm_rate"] = float(item["adm_rate"])
        items.append(item)
    return {"kind": kind, "items": items, "metrics": MAJOR_METRICS if kind == "majors" else PROGRAM_METRICS}
