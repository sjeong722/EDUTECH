# -*- coding: utf-8 -*-
"""
eda_analysis.py — 주식 쇼츠 인기 요인 EDA
  입력: benchmark_seed.csv (팀이 고른 10개, 항상)
        shorts_raw.csv    (collect_shorts.py 수집 결과, 있으면 자동 병합)
  출력: chart_*.png (시각화) + insight_report.md (인사이트 리포트)

분석 축:
  1) 유형별 인기 (조회수/참여율)
  2) 제목·형식 특징(숫자·질문·파워워드·길이)과 인기의 관계
  3) 협회 baseline vs 시장 인기 비교 (수집 데이터 있을 때)
목적: '주관적 선택'이 아닌 '객관적 지표'로 인기 요인을 검증한다.
"""

import os                       # 파일 존재 확인
import re                       # 제목 패턴 추출
import datetime as dt           # 경과일 계산
import numpy as np              # 수치 처리
import pandas as pd             # 데이터프레임
import matplotlib                # 시각화 백엔드 설정
matplotlib.use("Agg")           # 화면 없이 PNG 저장
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm  # 한글 폰트 탐지

# ─────────────────────────────────────────────────────────────
# 0) 한글 폰트 자동 설정 (없으면 유형명을 영문으로 대체)
# ─────────────────────────────────────────────────────────────
def setup_font() -> bool:
    """나눔/맑은고딕 등 한글 폰트가 있으면 등록하고 True 반환"""
    try:
        import koreanize_matplotlib  # 설치돼 있으면 나눔고딕 자동 등록(pip install koreanize-matplotlib)
        return True                  # 등록 성공 → 한글 사용 가능
    except Exception:
        pass                         # 없으면 아래 시스템 폰트 탐색으로
    for name in ["NanumGothic", "Malgun Gothic", "AppleGothic", "Noto Sans CJK KR"]:
        try:
            path = fm.findfont(name, fallback_to_default=False)  # 폰트 탐색
            fm.fontManager.addfont(path)                         # 등록
            plt.rcParams["font.family"] = fm.FontProperties(fname=path).get_name()
            plt.rcParams["axes.unicode_minus"] = False           # 마이너스 깨짐 방지
            return True
        except Exception:
            continue
    plt.rcParams["axes.unicode_minus"] = False
    return False

HAS_KFONT = setup_font()        # 한글 폰트 사용 가능 여부

# 한글 폰트 없을 때 차트 라벨용 영문 매핑
TYPE_EN = {
    "설명형": "Explain", "Q&A형": "Q&A", "발표형": "Present",
    "사례·스토리텔링형": "Story", "전·후 비교형": "Before/After",
    "리스트형": "List", "밈·유머형": "Meme", "그래프·숫자": "Chart/Num",
    "뉴스브리핑형": "News", "CTA 유도형": "CTA", "미분류": "Etc",
}
def lab(korean: str) -> str:
    """한글 폰트 있으면 한글, 없으면 영문 라벨"""
    return korean if HAS_KFONT else TYPE_EN.get(korean, korean)

# ─────────────────────────────────────────────────────────────
# 1) 제목·형식 특징 추출
# ─────────────────────────────────────────────────────────────
# 파워워드: 재테크 쇼츠 제목에서 클릭을 유발하는 표현들(감정·긴급·이득 소구)
POWER_WORDS = ["무조건", "후회", "당장", "부자", "비밀", "진짜", "이유", "절대",
               "꿀팁", "실수", "총정리", "끝", "완벽", "주의", "위험", "돈",
               "성공", "초보", "누구나", "이것", "제발", "왜"]

def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """제목에서 객관적으로 셀 수 있는 특징을 뽑는다(자동·재현 가능)"""
    t = df["title"].fillna("")                                  # 제목 결측 방지
    df["title_len"] = t.str.len()                               # 제목 글자수
    df["has_number"] = t.str.contains(r"\d").astype(int)        # 숫자 포함 여부
    df["has_question"] = t.str.contains(r"\?|까\?|나요|까$|을까|ㄹ까").astype(int)  # 질문형
    df["has_list_num"] = t.str.contains(r"\d+\s*(?:가지|개|위|선|단계)").astype(int)  # N가지/Top류
    df["has_rank"] = t.str.contains(r"[Tt][Oo][Pp]\s*\d|톱\s*\d|\d+위").astype(int) # 순위형
    df["power_word_cnt"] = t.apply(lambda s: sum(w in s for w in POWER_WORDS))     # 파워워드 개수
    df["has_power"] = (df["power_word_cnt"] > 0).astype(int)    # 파워워드 유무
    return df

def auto_label_type(title: str) -> str:
    """수집 데이터의 유형을 제목으로 '추정'(휴리스틱, 정확도 낮음 → 수동 검수 권장)"""
    s = str(title)
    if re.search(r"OX|퀴즈|Q&A|맞혀|정답", s): return "Q&A형"
    if re.search(r"[Tt][Oo][Pp]\s*\d|\d+위", s): return "CTA 유도형"
    if re.search(r"\d+\s*(가지|개|선)", s): return "리스트형"
    if re.search(r"차트|그래프|수익률|%|주가|지표", s): return "그래프·숫자"
    if re.search(r"\d+년\s*차|후회|경험|썰|실화", s): return "사례·스토리텔링형"
    if re.search(r"속보|뉴스|발표|투자한다|공시", s): return "뉴스브리핑형"
    if re.search(r"무조건|성공하는|vs|비교", s): return "전·후 비교형"
    if re.search(r"왜|이유|란\?|무엇|뭘까", s): return "설명형"
    return "미분류"

# ─────────────────────────────────────────────────────────────
# 2) 데이터 로드 (seed + 수집분 병합)
# ─────────────────────────────────────────────────────────────
def load_data():
    seed = pd.read_csv("benchmark_seed.csv")                    # 팀 벤치마크 10개
    seed["dataset"] = "seed"                                    # 구분 태그
    frames = [seed]

    if os.path.exists("shorts_raw.csv"):                        # 수집 데이터 있으면
        raw = pd.read_csv("shorts_raw.csv")
        raw["dataset"] = "collected"
        raw["type"] = raw["title"].apply(auto_label_type)       # 유형 자동 추정
        frames.append(raw)

    df = pd.concat(frames, ignore_index=True)                   # 병합

    # seed엔 없는 지표 컬럼 보강(있으면 유지)
    now = dt.datetime.now(dt.timezone.utc)
    pub = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    df["days_since"] = ((now - pub).dt.total_seconds() / 86400).round(1).clip(lower=1)
    df["vpd"] = (df["view_count"] / df["days_since"]).round(0)  # 조회 속도(공정 비교용)
    return extract_features(df)                                 # 특징 추출까지

# ─────────────────────────────────────────────────────────────
# 3) 시각화
# ─────────────────────────────────────────────────────────────
def fmt_k(x):
    """조회수 축약 표기(1200000→1.2M)"""
    return f"{x/1e6:.1f}M" if x >= 1e6 else (f"{x/1e3:.0f}K" if x >= 1e3 else f"{int(x)}")

def chart_type_views(df):
    """유형별 조회수(중앙값) 막대 — 어떤 유형이 인기인가"""
    g = df.groupby("type")["view_count"].median().sort_values(ascending=False)
    plt.figure(figsize=(9, 5))
    plt.bar([lab(t) for t in g.index], g.values, color="#1F2A44")
    plt.title(lab("유형별 조회수(중앙값)"))
    plt.ylabel("views (median)")
    plt.xticks(rotation=35, ha="right")
    for i, v in enumerate(g.values):
        plt.text(i, v, fmt_k(v), ha="center", va="bottom", fontsize=9)
    plt.tight_layout(); plt.savefig("chart_type_views.png", dpi=130); plt.close()

def chart_title_features(df):
    """제목 특징 유무별 조회수(중앙값) 비교 — 무엇이 조회수와 연관되나"""
    feats = [("has_number", "숫자"), ("has_question", "질문형"),
             ("has_list_num", "N가지"), ("has_power", "파워워드")]
    labels, withv, without = [], [], []
    for col, name in feats:
        labels.append(lab(name))
        withv.append(df[df[col] == 1]["view_count"].median())
        without.append(df[df[col] == 0]["view_count"].median())
    x = np.arange(len(labels)); w = 0.38
    plt.figure(figsize=(9, 5))
    plt.bar(x - w/2, withv, w, label=lab("있음"), color="#C0392B")
    plt.bar(x + w/2, without, w, label=lab("없음"), color="#95A5A6")
    plt.xticks(x, labels); plt.ylabel("views (median)")
    plt.title(lab("제목 특징별 조회수 비교"))
    plt.legend(); plt.tight_layout()
    plt.savefig("chart_title_features.png", dpi=130); plt.close()

def chart_length_scatter(df):
    """영상 길이 vs 조회수 산점도 — 최적 길이 구간 탐색"""
    plt.figure(figsize=(9, 5))
    plt.scatter(df["duration_sec"], df["view_count"], alpha=0.6, color="#1F2A44")
    plt.xlabel("duration (sec)"); plt.ylabel("views")
    plt.yscale("log")                                           # 조회수 편차 커서 로그축
    plt.title(lab("영상 길이 vs 조회수"))
    plt.axvline(60, ls="--", c="gray"); plt.text(61, plt.ylim()[1], "60s", fontsize=8)
    plt.tight_layout(); plt.savefig("chart_length_vs_views.png", dpi=130); plt.close()

def chart_baseline_vs_market(df):
    """협회 baseline vs 시장검색 조회수 분포 비교(수집 데이터 있을 때만)"""
    col = df[df["dataset"] == "collected"].copy()
    if col.empty:
        return False
    col["group"] = np.where(col["source"].astype(str).str.startswith("협회"),
                            "협회(우리)", "시장(인기)")
    g = col.groupby("group")["view_count"].median()
    plt.figure(figsize=(7, 5))
    plt.bar([lab(i) for i in g.index], g.values, color=["#1F2A44", "#C0392B"])
    plt.ylabel("views (median)"); plt.title(lab("협회 vs 시장 조회수(중앙값)"))
    for i, v in enumerate(g.values):
        plt.text(i, v, fmt_k(v), ha="center", va="bottom")
    plt.tight_layout(); plt.savefig("chart_baseline_vs_market.png", dpi=130); plt.close()
    return True

# ─────────────────────────────────────────────────────────────
# 4) 인사이트 리포트 자동 생성
# ─────────────────────────────────────────────────────────────
def write_report(df):
    has_collected = (df["dataset"] == "collected").any()        # 수집 데이터 유무
    n_total = len(df)
    seed = df[df["dataset"] == "seed"]

    # 특징별 조회수 중앙값 비교(있음/없음)로 '연관' 방향 파악
    def med_gap(col):
        a = df[df[col] == 1]["view_count"].median()
        b = df[df[col] == 0]["view_count"].median()
        return a, b, (a / b if b else float("nan"))

    lines = []
    lines.append("# 주식 쇼츠 인기 요인 EDA 리포트\n")
    lines.append(f"- 분석 표본: 총 {n_total}개 "
                 f"(seed 벤치마크 {len(seed)}개"
                 + (f", 수집 {int((df['dataset']=='collected').sum())}개" if has_collected else "")
                 + ")\n")
    lines.append(f"- 한글 폰트: {'적용됨' if HAS_KFONT else '미적용(차트 라벨 영문)'}\n")

    lines.append("\n## 1. 유형별 인기 순위 (조회수 중앙값)\n")
    g = df.groupby("type")["view_count"].median().sort_values(ascending=False)
    for t, v in g.items():
        lines.append(f"- {t}: {fmt_k(v)}\n")

    lines.append("\n## 2. 제목·형식 특징과 조회수의 관계\n")
    for col, name in [("has_number", "숫자 포함"), ("has_question", "질문형 제목"),
                      ("has_list_num", "N가지/Top형"), ("has_power", "파워워드 포함")]:
        a, b, ratio = med_gap(col)
        if not np.isnan(ratio):
            direction = "높음" if ratio >= 1 else "낮음"
            lines.append(f"- {name}: 있음 {fmt_k(a)} vs 없음 {fmt_k(b)} "
                         f"→ 있을 때 조회수 중앙값이 {ratio:.1f}배 {direction}\n")

    lines.append("\n## 3. 길이 분석\n")
    short = df[df["duration_sec"] <= 60]["view_count"].median()
    long_ = df[df["duration_sec"] > 60]["view_count"].median()
    lines.append(f"- 60초 이하 중앙값 {fmt_k(short)} vs 60초 초과 중앙값 {fmt_k(long_)}\n")

    if has_collected:
        col = df[df["dataset"] == "collected"]
        top = col.sort_values("view_count", ascending=False).head(10)
        lines.append("\n## 4. 시장 인기 쇼츠 Top10 (수집 기준)\n")
        for _, r in top.iterrows():
            lines.append(f"- [{fmt_k(r['view_count'])}] {r['title']} — {r['channel']}\n")

    lines.append("\n## 5. 해석 시 주의(한계)\n")
    lines.append("- seed 10개는 유형당 1개라 통계적 결론이 아니라 '경향 참고'입니다.\n")
    lines.append("- 조회수는 채널 규모·게시 경과일에 좌우되므로 참여율·VPD를 함께 보세요.\n")
    lines.append("- 자동 유형 라벨은 제목 기반 추정이라 수동 검수가 필요합니다.\n")
    lines.append("- 쇼츠→롱폼 유입은 공개 API로 측정 불가(채널 애널리틱스 필요).\n")

    lines.append("\n## 6. 스토리보드 반영 제안(가설)\n")
    lines.append("- 위 '있을 때 조회수 높은' 특징을 훅·제목에 우선 적용해 A/B 테스트.\n")
    lines.append("- 투교협의 '신뢰·안전' 강점을 제목/자막에 명시해 차별화.\n")
    lines.append("- 발행 후 롱폼 조회수 시계열을 별도 추적해 성과 검증.\n")

    with open("insight_report.md", "w", encoding="utf-8") as f:
        f.writelines(lines)

# ─────────────────────────────────────────────────────────────
# 5) 메인
# ─────────────────────────────────────────────────────────────
def main():
    df = load_data()                                            # 로드+특징추출
    chart_type_views(df)                                        # 차트1
    chart_title_features(df)                                    # 차트2
    chart_length_scatter(df)                                    # 차트3
    made = chart_baseline_vs_market(df)                         # 차트4(수집시)
    write_report(df)                                            # 리포트
    print(f"완료: 차트 {'4' if made else '3'}개 + insight_report.md 생성")
    print(f"한글 폰트: {'적용' if HAS_KFONT else '미적용(영문 라벨)'}")


if __name__ == "__main__":
    main()
