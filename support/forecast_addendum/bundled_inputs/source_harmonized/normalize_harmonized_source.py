if not __debug__:
    raise RuntimeError("Run verification with Python optimization disabled.")
import csv
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "kosis_DT_1ES3B05J_H1_2013_2025_precision1_dom.json"
REGIONS = {
    "계": "KOR",
    "서울특별시": "KR011",
    "인천광역시": "KR012",
    "경기도": "KR013",
    "부산광역시": "KR021",
    "울산광역시": "KR022",
    "경상남도": "KR023",
    "대구광역시": "KR031",
    "경상북도": "KR032",
    "광주광역시": "KR041",
    "전라북도": "KR042",
    "전북특별자치도": "KR042",
    "전라남도": "KR043",
    "대전광역시": "KR051",
    "충청북도": "KR052",
    "충청남도": "KR053",
    "세종특별자치시": "KR054",
    "강원도": "KR061",
    "강원특별자치도": "KR061",
    "제주특별자치도": "KR071",
}
RANGES = {
    "01~03": "A",
    "05~08": "B",
    "10~34": "C",
    "35": "D",
    "36~39": "E",
    "41~42": "F",
    "45~47": "G",
    "49~52": "H",
    "55~56": "I",
    "58~63": "J",
    "64~66": "K",
    "68": "L",
    "70~73": "M",
    "74~76": "N",
    "84": "O",
    "85": "P",
    "86~87": "Q",
    "90~91": "R",
    "94~96": "S",
    "97~98": "T",
    "99": "U",
}
GROUPS = {
    "A": ["A"],
    "BTE": ["B", "C", "D", "E"],
    "F": ["F"],
    "GTI": ["G", "H", "I"],
    "J": ["J"],
    "K": ["K"],
    "L": ["L"],
    "M_N": ["M", "N"],
    "OTQ": ["O", "P", "Q"],
    "RTU": ["R", "S", "T", "U"],
    "_T": ["_T"],
}


def clean(s):
    return re.sub("\\s+", " ", s.replace("\xa0", " ")).strip()


def expand(rows):
    grid, occupied = ([], {})
    for ri, row in enumerate(rows):
        line = {c: v for (r, c), v in occupied.items() if r == ri}
        ci = 0
        for cell in row:
            while ci in line:
                ci += 1
            for dr in range(cell.get("rs", 1)):
                for dc in range(cell.get("cs", 1)):
                    if dr == 0:
                        line[ci + dc] = clean(cell["text"])
                    else:
                        occupied[ri + dr, ci + dc] = clean(cell["text"])
            ci += cell.get("cs", 1)
        grid.append([line.get(i, "") for i in range(max(line, default=-1) + 1)])
    return grid


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def normalize():
    source = json.loads(RAW.read_text(encoding="utf-8"))
    grid = expand(source["rows"])
    periods, measures = grid[:2]
    assert len(periods) == len(measures) == 28
    assert sorted(set(periods[2:])) == [f"{y}.1/2" for y in range(2013, 2026)]
    sections, region, seen = ([], "", set())
    for row in grid[2:]:
        if len(row) < 2 or not row[1]:
            continue
        if row[0]:
            region = row[0]
        if region not in REGIONS:
            raise ValueError(f"Unknown region {region}")
        label = row[1]
        m = re.search("\\(([^()]*)\\)$", label)
        section = (
            "_T"
            if label == "계"
            else RANGES.get(re.sub("\\s", "", m.group(1)))
            if m
            else None
        )
        if section is None:
            raise ValueError(f"Unknown industry {label}")
        for i in range(2, len(periods)):
            if "취업자" not in measures[i]:
                continue
            raw = row[i]
            number = raw.replace(",", "")
            numeric = bool(re.fullmatch("[+-]?\\d+(?:\\.\\d+)?", number))
            value = int(Decimal(number) * 1000) if numeric else None
            if numeric and Decimal(number) * 1000 != value:
                raise ValueError("Unexpected subperson precision")
            key = (REGIONS[region], periods[i], section)
            if key in seen:
                raise ValueError(f"Duplicate key {key}")
            seen.add(key)
            sections.append(
                dict(
                    region_code=REGIONS[region],
                    region_name_ko=region,
                    period=periods[i],
                    year=int(periods[i][:4]),
                    half=1,
                    section=section,
                    industry_label=label,
                    raw_cell=raw,
                    employment_persons=value,
                    missing_symbol="" if numeric else raw,
                    rse_flag=row[i + 1],
                    decimal_places_displayed=len(number.split(".")[1])
                    if numeric and "." in number
                    else None,
                    source_table=source["source"],
                    source_uri=source["url"],
                )
            )
    assert len(sections) == 18 * 22 * 13
    groups = {}
    for r in sections:
        groups.setdefault((r["region_code"], r["period"]), {})[r["section"]] = r
    panel = []
    for (region, period), d in sorted(groups.items()):
        assert set(d) == set("ABCDEFGHIJKLMNOPQRSTU") | {"_T"}
        for industry, components in GROUPS.items():
            h = [d[c] for c in components]
            complete = all((r["employment_persons"] is not None for r in h))
            total = sum((r["employment_persons"] for r in h)) if complete else None
            panel.append(
                dict(
                    region_code=region,
                    region_name_ko=h[0]["region_name_ko"],
                    period=period,
                    year=int(period[:4]),
                    half=1,
                    industry_code=industry,
                    employment_persons=total,
                    complete_components=complete,
                    components="+".join(components),
                    missing_components="+".join(
                        (r["section"] for r in h if r["employment_persons"] is None)
                    ),
                    source_raw_values="|".join((r["raw_cell"] for r in h)),
                    rse_any_star=any((r["rse_flag"] == "*" for r in h)),
                    source_rse_flags="|".join((r["rse_flag"] for r in h)),
                    display_rounding_halfwidth_persons=50 * len(h)
                    if complete
                    else None,
                    classification="KSIC11",
                    reference_period="H1 April",
                    source_table=source["source"],
                    source_uri=source["url"],
                )
            )
    provincial = [r for r in panel if r["region_code"] != "KOR"]
    national = [r for r in panel if r["region_code"] == "KOR"]
    write_csv(HERE / "kosis_ksic11_H1_2013_2025_sections.csv", sections)
    write_csv(HERE / "kosis_ksic11_H1_2013_2025_panel.csv", provincial)
    write_csv(HERE / "kosis_ksic11_H1_2013_2025_national_panel.csv", national)
    write_csv(
        HERE / "broad_activity_crosswalk.csv",
        [
            dict(
                industry_code=k,
                sections="+".join(v),
                rule="all components numeric; otherwise missing",
            )
            for k, v in GROUPS.items()
        ],
    )
    coverage = []
    for y in range(2013, 2026):
        s = [r for r in provincial if r["year"] == y and r["industry_code"] != "_T"]
        coverage.append(
            dict(
                year=y,
                expected_broad_cells=170,
                complete_numeric=sum((r["complete_components"] for r in s)),
                positive_numeric=sum(
                    (
                        r["employment_persons"] is not None
                        and r["employment_persons"] > 0
                        for r in s
                    )
                ),
                missing=sum((not r["complete_components"] for r in s)),
                numeric_zero=sum((r["employment_persons"] == 0 for r in s)),
                rse_any_star=sum((r["rse_any_star"] for r in s)),
            )
        )
    write_csv(HERE / "coverage_by_year.csv", coverage)
    write_csv(
        HERE / "incomplete_broad_cells.csv",
        [r for r in provincial if not r["complete_components"]],
    )
    (HERE / "table_metadata_and_notes.txt").write_text(
        source["header_and_notes"], encoding="utf-8"
    )
    manifest = dict(
        source_file=RAW.name,
        source_sha256=hashlib.sha256(RAW.read_bytes()).hexdigest(),
        captured_at_utc=source["captured_at_utc"],
        source_uri=source["url"],
        acquisition="Official rendered KOSIS mainTable DOM; UI selected all 2013–2025 H1 and one decimal place; no API approximation",
        reference_month=4,
        reference_half=1,
        classification="KSIC11; currently revised backcast from 2013H1",
        table_update_date="2026-05-13",
        data_vintage="retrieved 2026-09-26; not original historical publication vintage",
        displayed_unit="thousand persons",
        displayed_decimal_places=1,
        normalized_unit="persons",
        province_count=17,
        national_retained_separately=True,
        section_rows=len(sections),
        provincial_panel_rows=len(provincial),
        national_panel_rows=len(national),
        missing_rule="nonnumeric original symbols retained; component group not summed if any component missing",
        rse_rule="* indicates source section RSE >=25%; rse_any_star is any constituent flag, not the aggregate RSE",
        boundary_note="Gunwi (formerly Gyeongbuk) incorporated into Daegu July 2023; source does not assert geographical backcasting",
        sejong_note="No Sejong-specific boundary note in current J table comments; no continuity claim inferred",
        historic_availability_confirmed=False,
        model_losses_observed=False,
        coverage=coverage,
    )
    (HERE / "source_acquisition_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "section_rows": len(sections),
                "provincial_panel_rows": len(provincial),
                "national_panel_rows": len(national),
                "coverage": coverage,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    normalize()
