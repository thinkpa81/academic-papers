"""Draw Figure 1 as a service workflow with its evidence and evaluation boundary."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, Rectangle

ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT/'support/baseline/base_v11/original/fonts').glob('*.ttf'):font_manager.fontManager.addfont(p)
plt.rcParams.update({'font.family':['NanumMyeongjo','DejaVu Sans'],'axes.unicode_minus':False,'pdf.fonttype':42,'svg.fonttype':'none'})

def draw(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(figsize=(6.0,4.6));ax.set_xlim(0,104);ax.set_ylim(0,74);ax.axis('off')
    ink='#202e38';blue='#dce6eb';line='#7d929e'
    def box(x,y,w,h,title,body,face='white',dashed=False):
        ax.add_patch(Rectangle((x,y),w,h,facecolor=face,edgecolor=line,lw=1.1,linestyle='--' if dashed else '-'))
        ax.text(x+w/2,y+h-3,title,ha='center',va='center',size=9.3,weight='bold',color=ink)
        ax.text(x+w/2,y+(h-3)/2-1,body,ha='center',va='center',size=7.7,linespacing=1.45,color=ink)
    def arrow(a,b,dashed=False):
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=11,lw=1.1,color=ink,linestyle='--' if dashed else '-'))
    ax.text(2,71,'예측 단위의 검토가능성',size=12,weight='bold',color=ink)
    ax.text(2,67.6,'공통 식별자  시도 · 산업 · 목표시점 · 자료판본 · 모형',size=8.1,color=ink)
    box(2,48,30,16,'① 사용조건 · DP2','상반기·분류·경계·결측\n관측·공표·확보 시점',blue)
    box(37,48,30,16,'② 비교근거 · DP1·DP3','기준·학습모형 비교\n오차·사례 수·적용범위',blue)
    box(72,48,30,16,'③ 현재 근거 · DP4','카드·비교표·판단사유\n현재 판본과 기록 연결',blue)
    arrow((32.4,56),(36.6,56));arrow((67.4,56),(71.6,56))
    box(2,26,30,16,'별도 등록 근거','모형·입력·검증요약\n기관이 신뢰·갱신권한 관리')
    box(37,26,30,16,'④ 완료 요건 확인','자료·수치의 적격성\n현재 기록·등록근거 일치',blue)
    box(72,26,30,16,'연구용 검토 상태','충족: 완료기록 보존\n변경·불일치: 보완·재검토',blue)
    arrow((87,47.6),(52,42.4));arrow((32.4,34),(36.6,34));arrow((67.4,34),(71.6,34))
    arrow((102,41),(102,46));arrow((102,46),(89,46));arrow((89,46),(89,47.6))
    ax.text(82,44.2,'근거 갱신 시 다시 연결',size=7,ha='center',color=ink)
    box(2,5,65,15,'평가근거와 적용조건','회고적 예측평가 · 결함/정상 비교 · 기능 제거\n모형 교체 · 같은 정보의 도구 비교 · 다른 집계자료 적용')
    box(72,5,30,15,'현장 업무 연계','RSC 수요조사 · 훈련계획\n담당자 판단과 기관 승인',dashed=True)
    arrow((87,25.6),(87,20.4),True)
    ax.text(2,1.3,'실선: 구현·기술평가 범위    점선: 후속 현장 적용    사용자 판단·업무성과: 후속 평가',size=7.1,color=ink)
    fig.subplots_adjust(left=0,right=1,bottom=0,top=1)
    for ext in ['png','svg','pdf']:fig.savefig(out/f'paper_figure_01.{ext}',dpi=360,facecolor='white')
    plt.close(fig)

if __name__=='__main__':draw(ROOT/'figures')
