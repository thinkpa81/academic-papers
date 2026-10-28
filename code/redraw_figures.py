"""Reproducible publication figures; all displayed values read from verified sources."""

import argparse
import csv
import json
import os
from collections import Counter
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle, FancyArrowPatch

INPUT = Path(__file__).resolve().parents[1] / "figures"
ROOT = INPUT
for f in (ROOT.parent / "support/baseline/base_v11/original/fonts").glob("*.ttf"):
    fm.fontManager.addfont(f)
plt.rcParams.update(
    {
        "font.family": ["NanumMyeongjo", "DejaVu Sans"],
        "font.size": 9,
        "axes.unicode_minus": False,
        "text.parse_math": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
        "axes.labelcolor": "#20262A",
        "text.color": "#20262A",
    }
)
INK = "#20262A"
SLATE = "#445D6B"
TEAL = "#457B83"
RULE = "#AAB4BB"
LIGHT = "#EDF0F2"


def base(w, h):
    f = plt.figure(figsize=(w / 25.4, h / 25.4), dpi=300)

    def txt(x, y, s, size=9, weight="normal", ha="left", color=INK, va="center", **kw):
        return f.text(
            x / w,
            y / h,
            s,
            fontsize=size,
            fontweight=weight,
            ha=ha,
            va=va,
            color=color,
            **kw,
        )

    def line(x1, x2, y, lw=0.6, color=RULE):
        f.add_artist(
            plt.Line2D(
                [x1 / w, x2 / w],
                [y / h, y / h],
                transform=f.transFigure,
                lw=lw,
                color=color,
            )
        )

    def box(x, y, bw, bh, face="white", edge=RULE, lw=0.6):
        f.add_artist(
            Rectangle(
                (x / w, y / h),
                bw / w,
                bh / h,
                transform=f.transFigure,
                facecolor=face,
                edgecolor=edge,
                lw=lw,
            )
        )

    return f, txt, line, box


def save(f, name):
    # Full canvas is deliberate; avoids silent changes in physical figure size.
    temporary = ROOT / (name + ".temporary.png")
    f.savefig(temporary, dpi=450)
    with temporary.open("rb") as stream:
        os.fsync(stream.fileno())
    from docx.image.image import Image as DocxImage
    from PIL import Image as PILImage

    with PILImage.open(temporary) as im:
        im.verify()
    DocxImage.from_file(str(temporary))
    os.replace(temporary, ROOT / (name + ".png"))
    f.savefig(ROOT / (name + ".pdf"))
    f.savefig(ROOT / (name + ".svg"))
    canonical = {"figure1_final": "paper_figure_01", "figure2_final": "paper_figure_A1",
                 "figure3_final": "paper_figure_02", "figure4_final": "paper_figure_03"}.get(name)
    if canonical:
        import shutil
        for extension in ("png", "pdf", "svg"):
            shutil.copyfile(ROOT / f"{name}.{extension}", ROOT / f"{canonical}.{extension}")
    plt.close(f)


def draw3():
    """Main-text Figure 2: source-backed Seoul BTE evidence display."""
    d = json.loads((INPUT / "fig3_validation.json").read_text())
    card_path = INPUT.parent / "support/model_swap_addendum/guard_snapshot/source_snapshot/reproduced_service/evidence_card_2025_seoul_BTE.json"
    card = json.loads(card_path.read_text())
    ridge = d["ridge"]
    basev = d["baseline"]
    vals = [
        d["intercept"],
        d["shown_contributions"]["own_growth"],
        d["shown_contributions"]["log_employment"],
        d["shown_contributions"]["region_total_growth"],
        d["other_five_sum"],
        ridge,
    ]
    assert abs(sum(vals[:-1]) - ridge) < 1e-12
    assert d["maintain_band"] == [-0.5, 0.5]
    W, H = 147, 158
    f, t, line, box = base(W, H)
    t(3, 153, "서울 BTE 산업군(B·C·D·E)의 예측근거와 검토 절차", 10.5, "bold")
    t(
        3,
        146.8,
        "동일 기준 주분석 | 2024년 상반기 입력 → 2025년 상반기",
        9,
        color="#59656D",
    )
    line(3, 144, 142.3)
    t(3, 138.5, "(가) 예측값과 기준모형 대비 편차", 9.5, "bold")
    ax = f.add_axes([18 / W, 113.5 / H, 123 / W, 22 / H])
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-0.32, 1.1)
    ax.axvspan(-0.5, 0.5, color=LIGHT, zorder=0)
    ax.axvline(-0.5, lw=0.65, color="#A9B4BA", ls="--")
    ax.axvline(0.5, lw=0.65, color="#A9B4BA", ls="--")
    ax.axvline(0, lw=0.6, color="#B3BDC3")
    ax.axhline(0.46, color="#8D9AA3", lw=0.7)
    ax.scatter(
        [ridge], [0.46], s=42, color=TEAL, edgecolor="white", linewidth=0.75, zorder=5
    )
    ax.scatter(
        [basev],
        [0.46],
        s=40,
        color=SLATE,
        marker="D",
        edgecolor="white",
        linewidth=0.75,
        zorder=5,
    )
    ax.text(ridge, 0.81, f"릿지 {ridge:+.2f}", fontsize=9, ha="center", color=TEAL)
    ax.text(basev, 0.81, f"기준모형 {basev:+.2f}", fontsize=9, ha="center", color=SLATE)
    ax.text(0, 1.01, "유지 범위", fontsize=8.3, ha="center", color="#59656D")
    ax.plot([ridge, ridge, basev, basev], [0.30, 0.12, 0.12, 0.30], color=SLATE, lw=0.8)
    ax.text(
        (ridge + basev) / 2,
        -0.16,
        f"편차 {ridge-basev:+.2f} · {card['relative_deviation']['class']}",
        fontsize=9,
        ha="center",
        color=SLATE,
    )
    ax.set_xticks([-1, -0.5, 0, 0.5, 1])
    ax.set_xticklabels(["-1.0", "-0.5", "0", "+0.5", "+1.0"], fontsize=8.5)
    ax.tick_params(axis="x", length=2.6, pad=2.5, color=RULE)
    ax.set_yticks([])
    for sp in ["top", "left", "right"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.spines["bottom"].set_linewidth(0.65)
    t(3, 106.2, "기준모형: 전체 과거평균(전 관측치 공통)", 8.4, color="#59656D")
    t(144, 106.2, "단위: 로그포인트", 8.4, ha="right", color="#59656D")
    t(
        3,
        101.6,
        "음영: [-0.5, +0.5]의 고용변동을 구분하기 위한 표시 범위",
        8.5,
        color="#59656D",
    )
    t(3, 95.4, "(나) 릿지 예측값의 가법 분해", 9.5, "bold")
    ax2 = f.add_axes([46 / W, 56.5 / H, 94 / W, 35 / H])
    labs = [
        "릿지 절편",
        "직전 고용변동",
        "로그 고용수준",
        "시도 총고용 변동",
        "기타 5개 항 합계",
        "릿지 예측값",
    ]
    yy = np.arange(6)
    colors = [SLATE, TEAL, TEAL, SLATE, TEAL, "#253E4C"]
    ax2.barh(yy, vals, height=0.49, color=colors, zorder=3)
    ax2.set_ylim(5.6, -0.55)
    ax2.set_xlim(-1.07, 0.93)
    ax2.axvline(0, color="#8D9AA3", lw=0.7, zorder=2)
    for x in [-1, -0.5, 0.5]:
        ax2.axvline(x, color="#E2E6E9", lw=0.55, zorder=1)
    ax2.axhline(4.5, color=RULE, lw=0.65)
    ax2.set_yticks(yy)
    ax2.set_yticklabels(labs, fontsize=9)
    ax2.tick_params(axis="y", length=0, pad=6)
    ax2.set_xticks([-1, -0.5, 0, 0.5])
    ax2.set_xticklabels(["-1.0", "-0.5", "0", "+0.5"], fontsize=8.5)
    ax2.tick_params(axis="x", length=2.5, pad=2, color=RULE)
    for i, v in enumerate(vals):
        label = f"{v:+.2f}"
        ax2.text(
            v + (0.035 if v >= 0 else -0.035),
            i,
            label,
            ha="left" if v >= 0 else "right",
            va="center",
            fontsize=9,
        )
    for sp in ["top", "left", "right"]:
        ax2.spines[sp].set_visible(False)
    ax2.spines["bottom"].set_color(RULE)
    ax2.spines["bottom"].set_linewidth(0.65)
    t(
        3,
        48.6,
        f"반올림 전 합계 = {sum(vals[:-1]):.4f}; 각 항은 모형 내부의 기여분",
        8.5,
        color="#59656D",
    )
    t(3, 42.4, "(다) 검증 범위와 후속 검토 과업", 9.5, "bold")
    t(3, 36.7, f"동일 지역·산업의 검증사례 {d['validation_cell_n']}개: 칸별 검증성능 산출 불가", 8.7)
    xs = [3, 52, 101]
    labels = ["원표·분류 연계 확인", "현장 수요조사 계획", "담당자 검토기록"]
    for i, (x, label) in enumerate(zip(xs, labels)):
        box(x, 24, 43, 8, face="white")
        t(x + 21.5, 28, label, 8.8, ha="center")
        if i < 2:
            f.add_artist(FancyArrowPatch(((x+43.5)/W,28/H), ((x+48.5)/W,28/H),
                                          transform=f.transFigure, arrowstyle="-|>",
                                          mutation_scale=8, linewidth=.7, color=SLATE))
    t(73.5, 19, "제안된 업무 절차: 실제 담당자 수행 결과는 미측정", 8.7, ha="center")
    line(3, 144, 15)
    t(3, 10.8, (f"사후 관측값: {card['historical_outcome_audit']['observed_logpoints']:.2f} 로그포인트"
                  f"({card['historical_outcome_audit']['observed_simple_change_pct']:.2f}%)"), 9)
    t(
        3,
        5.4,
        "사후 관측값은 예측·편차 산정에 사용하지 않음; 과거 공표본 미확인",
        8.5,
        color="#59656D",
    )
    save(f, "figure3_final")


def draw4():
    """Main-text Figure 3: relative forecast differences and coverage."""
    rows = list(
        csv.DictReader((INPUT / "matrix_rendered_cells.csv").open(encoding="utf-8-sig"))
    )
    regs = list(dict.fromkeys(r["superregion"] for r in rows))
    inds = list(dict.fromkeys(r["industry_code"] for r in rows))
    counts = Counter(r["class"] for r in rows)
    cov = Counter(r["coverage"] for r in rows)
    assert counts == {"하회": 17, "근접": 35, "상회": 13, "": 15}, counts
    assert cov == {"완전": 61, "부분": 4, "자료없음": 15}, cov
    assert len(rows) == 80
    W, H = 147, 132
    f, t, line, box = base(W, H)
    t(3, 127.2, "2025년 권역-산업별 예측편차와 자료 적용범위", 10.5, "bold")
    t(
        3,
        121.1,
        "예측편차 Δ = 릿지 예측값 - 전체 과거평균 예측값 (로그포인트)",
        8.8,
        color="#59656D",
    )
    ax = f.add_axes([17 / W, 53 / H, 127 / W, 60 / H])
    ax.set_xlim(0, 10)
    ax.set_ylim(8, 0)
    cmap = {"하회": "#C1D9DD", "근접": "#EEF0F2", "상회": "#E9CEC1", "": "#FFFFFF"}
    for r in rows:
        i = regs.index(r["superregion"])
        j = inds.index(r["industry_code"])
        ax.add_patch(
            Rectangle(
                (j, i),
                1,
                1,
                facecolor=cmap[r["class"]],
                edgecolor="#ADB7BE",
                linewidth=0.45,
            )
        )
        if r["coverage"] == "부분":
            ax.add_patch(Rectangle((j + .035, i + .04), .93, .92, fill=False,
                                   edgecolor="#70828E", linewidth=.65, linestyle="--"))
        # Marker * is retained exactly as supplied; all cell labels are immutable.
        ax.text(
            j + 0.5,
            i + 0.5,
            r["label"],
            fontsize=8.6 if r["class"] else 11,
            ha="center",
            va="center",
            color=INK if r["class"] else "#9AA3AA",
        )
    for k in range(9):
        ax.axhline(k, color="#AEB8BE", lw=0.35, zorder=4)
    for k in range(11):
        ax.axvline(k, color="#C3CBD0", lw=0.3, zorder=4)
    ax.set_xticks(np.arange(10) + 0.5)
    ax.set_xticklabels(inds, fontsize=9)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=4.5)
    ax.set_yticks(np.arange(8) + 0.5)
    ax.set_yticklabels(regs, fontsize=9)
    ax.tick_params(axis="y", length=0, pad=4.5)
    for sp in ax.spines.values():
        sp.set_color("#8C9AA4")
        sp.set_linewidth(0.6)
    legend = [
        (3, "하회 17개 (Δ < -0.5)", "하회"),
        (51, "근접 35개 (|Δ| ≤ 0.5)", "근접"),
        (101, "상회 13개 (Δ > 0.5)", "상회"),
    ]
    for x, s, k in legend:
        box(x, 45, 3.3, 3.3, face=cmap[k], edge="#AAB4BB", lw=0.45)
        t(x + 4.7, 46.65, s, 8.4)
    t(3, 39.2, "*·점선 테두리: 일부 시도 집계(4개)     ×: 미산출(15개)", 8.7)
    t(3, 33, "산출 65/80개 조합: 전체 시도 포함 61개 · 일부 시도 포함 4개", 9)
    t(3, 26.8, "검증 편차 부호 일치: 91/188 = 48.40% (2020~2022년)", 9)
    line(3, 144, 22.5)
    t(
        3,
        17.3,
        "±0.5는 예측편차의 크기를 구분하기 위해 설정한 표시 기준",
        8.6,
        color="#59656D",
    )
    t(
        3,
        11.8,
        "상회·근접·하회는 상대적 편차이며 고용 증감 방향과 구분하여 해석.",
        8.6,
        color="#59656D",
    )
    t(
        3,
        6.3,
        "2026년 9월 확보한 개정자료 기반 평가; 대경권은 경계 조건으로 미산출.",
        8.3,
        color="#59656D",
    )
    save(f, "figure4_final")


def draw1():
    from reviewability_figure import draw
    import shutil
    draw(ROOT)
    for extension in ["png", "pdf", "svg"]:
        shutil.copyfile(ROOT / ("paper_figure_01." + extension), ROOT / ("figure1_final." + extension))


def draw2():
    """Rebuild Appendix Figure A1 from the recorded annual strategy losses."""
    source = (
        INPUT.parent
        / "support/baseline/base_v11/extensions/analysis/rolling_annual_metrics.csv"
    )
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    years = list(range(2015, 2024))
    lookup = {
        (int(row["target_year"]), row["model"]): float(row["MAE"]) for row in rows
    }
    differences = [
        lookup[year, "validation_best_baseline"] - lookup[year, "validation_best_all"]
        for year in years
    ]
    figure, axis = plt.subplots(figsize=(7.6, 3.3))
    axis.bar(
        years,
        differences,
        width=0.65,
        color=["#444444" if value >= 0 else "#cccccc" for value in differences],
        edgecolor="#444444",
        linewidth=0.6,
    )
    axis.axhline(0, color="black", linewidth=0.8)
    axis.set_xticks(years)
    axis.set_xlabel("평가연도")
    axis.set_ylabel("MAE 차이(로그포인트)")
    axis.set_ylim(-0.74, 0.68)
    axis.set_axisbelow(True)
    axis.grid(axis="y", color="#dddddd", linewidth=0.6)
    axis.spines[["top", "right"]].set_visible(False)
    for year, value in zip(years, differences):
        axis.text(
            year,
            value + (0.03 if value >= 0 else -0.03),
            f"{value:+.2f}",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=9,
        )
    figure.tight_layout()
    save(figure, "figure2_final")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=INPUT.parent / "generated_figures",
        help="Directory for regenerated PNG, PDF and SVG files.",
    )
    args = parser.parse_args()
    ROOT = args.out.expanduser().resolve()
    ROOT.mkdir(parents=True, exist_ok=True)
    draw1()
    draw2()
    draw3()
    draw4()
    print(f"Created four figures in {ROOT}")
