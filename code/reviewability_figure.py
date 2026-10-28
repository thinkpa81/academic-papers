"""Draw Figure 1 with one arrowhead per workflow edge and a separate review loop.

No analysis values are changed. Solid edges are implemented review transitions;
the dashed edge is a prospective connection to field work, not observed impact.
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.path import Path as MplPath

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'support/baseline/base_v11/original/fonts').glob('*.ttf'):
    font_manager.fontManager.addfont(p)
plt.rcParams.update({'font.family': ['NanumMyeongjo', 'DejaVu Sans'],
                     'axes.unicode_minus': False, 'text.parse_math': False, 'pdf.fonttype': 42,
                     'svg.fonttype': 'none'})


def draw(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    width, height = 147, 164
    fig, ax = plt.subplots(figsize=(width / 25.4, height / 25.4))
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis('off')
    ink, blue, line = '#202E38', '#E5ECEF', '#8699A4'

    def box(x, y, w, h, title, body, face='white', dashed=False, body_size=8.3):
        ax.add_patch(Rectangle((x, y), w, h, facecolor=face,
                               edgecolor=line, lw=0.8,
                               linestyle='--' if dashed else '-'))
        ax.text(x + w / 2, y + h - 4.0, title, ha='center', va='center',
                size=9.1, weight='bold', color=ink)
        ax.text(x + w / 2, y + (h - 5.0) / 2 - 1, body,
                ha='center', va='center', size=body_size, linespacing=1.4,
                color=ink)

    def arrow(points, dashed=False):
        # One continuous path is one logical edge: bends have no arrowheads.
        path = MplPath(points, [MplPath.MOVETO] + [MplPath.LINETO] * (len(points) - 1))
        ax.add_patch(FancyArrowPatch(path=path, arrowstyle='-|>',
                                    mutation_scale=9, linewidth=0.9, color=ink,
                                    linestyle='--' if dashed else '-'))

    ax.text(3, 159, '지역고용 예측의 근거 확인과 검토 절차',
            size=11, weight='bold', color=ink)
    ax.text(3, 152.5, '예측 식별자: 시도·산업·목표시점  |  근거판본: 자료·모형',
            size=8.2, color=ink)

    x, w = 53, 81
    box(x, 126, w, 18, '① 자료 사용조건 확인 · DP2',
        '상반기·분류·경계·결측\n관측·공표·확보 시점', blue)
    box(x, 103, w, 18, '② 모형 비교근거 제시 · DP1·DP3',
        '기준·학습모형의 예측값\n검증오차·사례 수·적용범위', blue)
    box(x, 80, w, 18, '③ 현재 근거와 기록 연결 · DP4',
        '예측근거 카드·권역 비교표\n현재 근거판본에 연결된 판단사유', blue)
    box(x, 57, w, 18, '④ 검토 완료 요건 확인',
        '자료·수치의 적격성\n현재 검토기록·등록 근거의 일치', blue)
    box(x, 34, w, 18, '연구용 검토 상태 기록',
        '요건 충족: 완료기록 보존\n변경·불일치: 보완 및 재검토', blue)
    box(x, 8, w, 18, '후속 현장 업무',
        'RSC 수요조사·훈련계획\n담당자 판단·기관 승인', dashed=True)
    for upper, lower in [(126, 121), (103, 98), (80, 75), (57, 52)]:
        arrow([(93.5, upper - .5), (93.5, lower + .5)])
    arrow([(93.5, 33.5), (93.5, 26.5)], dashed=True)
    ax.text(90, 30, '요건 충족 후', ha='right', va='center', size=7.4, color=ink)

    box(3, 57, 43, 18, '별도 등록 근거',
        '모형·입력·검증요약\n신뢰성·갱신권한 관리', body_size=7.8)
    arrow([(46.5, 66), (52.5, 66)])

    box(3, 103, 43, 41, '평가 근거',
        '과거자료 기반 예측평가\n\n결함·정상 입력 비교\n기능 제거·모형 교체\n도구 비교·자료 이식',
        body_size=7.8)
    ax.text(3, 93, '기술평가 대상: 구현 기능과\n명세한 검사 요건의 작동',
            size=7.8, color=ink, va='top', linespacing=1.5)
    ax.text(3, 43, '현장 사용자의 판단과\n업무성과는 후속 평가',
            size=7.8, color=ink, va='top', linespacing=1.5)

    # Reconnect the current evidence/review record after evidence changes.
    arrow([(134.5, 43), (140, 43), (140, 89), (134.5, 89)])
    ax.text(143.4, 66, '근거 변경 시 재검토', rotation=90,
            ha='center', va='center', size=7.6, color=ink)
    ax.text(3, 2, '실선: 구현·기술평가 범위  |  점선: 후속 현장 적용',
            size=7.5, color=ink)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    for ext in ['png', 'svg', 'pdf']:
        fig.savefig(out / f'paper_figure_01.{ext}', dpi=450, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    draw(ROOT / 'figures')
