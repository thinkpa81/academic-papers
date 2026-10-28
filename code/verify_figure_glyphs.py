"""Check ASCII minus signs and source-backed labels in the publication figures."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
NAMES = ["paper_figure_01", "paper_figure_02", "paper_figure_03", "paper_figure_A1"]
FORBIDDEN_MINUS = "\u2212\ufe63\uff0d\u2013\u2014"


def svg_text(path):
    return ["".join(e.itertext()) for e in ET.parse(path).getroot().iter()
            if e.tag.rsplit("}", 1)[-1] == "text"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results/figure_glyph_check_261028_v3.json")
    args = parser.parse_args()
    checks = []
    figures = {}

    def check(name, passed, observed):
        checks.append({"check": name, "passed": bool(passed), "observed": observed})

    for name in NAMES:
        texts = svg_text(FIGURES / (name + ".svg"))
        forbidden = {f"U+{ord(c):04X}": sum(t.count(c) for t in texts)
                     for c in FORBIDDEN_MINUS}
        check(name + "_ascii_minus", not any(forbidden.values()), forbidden)
        with Image.open(FIGURES / (name + ".png")) as image:
            dimensions = image.size
            dpi = image.info.get("dpi")
            image.verify()
        check(name + "_450dpi", dpi and min(dpi) >= 449, dpi)
        figures[name] = {
            "text_nodes": len(texts), "ascii_hyphen_count": sum(t.count("-") for t in texts),
            "forbidden_minus_counts": forbidden, "png_dimensions": dimensions,
            "files": {ext: {"sha256": hashlib.sha256((FIGURES / f"{name}.{ext}").read_bytes()).hexdigest(),
                             "bytes": (FIGURES / f"{name}.{ext}").stat().st_size}
                      for ext in ("png", "pdf", "svg")},
        }

    with (FIGURES / "matrix_rendered_cells.csv").open(encoding="utf-8-sig", newline="") as stream:
        matrix = list(csv.DictReader(stream))
    matrix_labels = [t for t in svg_text(FIGURES / "paper_figure_03.svg")
                     if re.fullmatch(r"[+-]\d+\.\d+\*?|×", t)]
    check("figure3_80_ordered_cell_labels", matrix_labels == [r["label"] for r in matrix], matrix_labels)

    annual_source = ROOT / "support/baseline/base_v11/extensions/analysis/rolling_annual_metrics.csv"
    with annual_source.open(encoding="utf-8-sig", newline="") as stream:
        annual = {(int(r["target_year"]), r["model"]): float(r["MAE"]) for r in csv.DictReader(stream)}
    annual_texts = svg_text(FIGURES / "paper_figure_A1.svg")
    appendix_values = {}
    for year in range(2015, 2024):
        value = annual[year, "validation_best_baseline"] - annual[year, "validation_best_all"]
        label = f"{value:+.2f}"
        appendix_values[str(year)] = {"difference": value, "label": label}
        check(f"appendix_A1_source_label_{year}", label in annual_texts, label)

    result = {"all_passed": all(c["passed"] for c in checks),
              "checks_passed": sum(c["passed"] for c in checks),
              "checks_total": len(checks), "minus_character": "U+002D HYPHEN-MINUS",
              "figures": figures, "appendix_A1_values": appendix_values, "checks": checks}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    assert result["all_passed"], [c for c in checks if not c["passed"]]
    print(json.dumps({k: result[k] for k in ("all_passed", "checks_passed", "checks_total", "minus_character")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
