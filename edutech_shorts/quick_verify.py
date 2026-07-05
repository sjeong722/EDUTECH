# -*- coding: utf-8 -*-
"""
quick_verify.py — 미팅용 '미니 검증' 차트 3종 + 요약 리포트 생성
  입력: beginner_shorts.csv (collect_beginner_shorts.py 결과)
  출력: v_chart1_keyword_demand.png  (키워드별 시장 수요)
        v_chart2_quiz_effect.png     (퀴즈형 vs 비퀴즈형 — 인기층 내부 비교)
        v_chart3_layer_gap.png       (인기층 vs 최신층 갭 = 시장 기회)
        verify_summary.md            (수치 요약 + 해석 주의사항)
  원칙: 그룹 분리 비교(심슨의 역설 방지) / 중앙값 사용 / n 항상 병기
"""

import pandas as pd                                 # 데이터프레임
import numpy as np                                  # 수치 처리
import matplotlib                                   # 시각화 백엔드
matplotlib.use("Agg")                               # 화면 없이 PNG 저장
import matplotlib.pyplot as plt                     # 플롯

try:
    import koreanize_matplotlib                     # 한글 폰트 자동 등록
except Exception:
    pass                                            # 없으면 기본 폰트(라벨 깨짐 가능)

df = pd.read_csv("beginner_shorts.csv")             # 수집 결과 로드
t = df["title"].fillna("")                          # 제목 결측 방지

# 퀴즈형 추정 라벨: 제목 기반 '추정'이므로 상위권은 반드시 수동 검수할 것
df["is_quiz"] = t.str.contains(r"퀴즈|OX|O/X|맞혀|맞춰|정답|문제|Q&A|몇 개").astype(int)
# 질문형 훅 추정 라벨
df["has_question"] = t.str.contains(r"\?|까\?|나요|을까|ㄹ까").astype(int)

pop = df[df["layer"] == "인기"]                      # 인기층만 분리(그룹 혼합 금지)
new = df[df["layer"] == "최신"]                      # 최신층(대조군)

def fmt(x):
    """조회수 축약 표기"""
    return f"{x/1e6:.1f}M" if x >= 1e6 else (f"{x/1e3:.0f}K" if x >= 1e3 else f"{int(x)}")

# ── 차트 1: 키워드별 시장 수요(인기층 조회수 중앙값 + n) ──
g = pop.groupby("keyword")["view_count"].agg(["median", "count"]).sort_values("median", ascending=False)
plt.figure(figsize=(10, 5))                         # 캔버스 생성
plt.bar(g.index, g["median"], color="#1F2A44")      # 막대 그리기
plt.title("초보 키워드별 쇼츠 시장 수요 — 인기층 조회수 중앙값 (최근 1년)")
plt.ylabel("views (median)")                        # y축 라벨
plt.xticks(rotation=30, ha="right")                 # x축 라벨 회전
for i, (m, n) in enumerate(zip(g["median"], g["count"])):   # 값+표본수 표기
    plt.text(i, m, f"{fmt(m)}\n(n={n})", ha="center", va="bottom", fontsize=8)
plt.tight_layout(); plt.savefig("v_chart1_keyword_demand.png", dpi=130); plt.close()

# ── 차트 2: 퀴즈형 vs 비퀴즈형 (인기층 내부에서만 비교) ──
q1 = pop[pop["is_quiz"] == 1]["view_count"]         # 퀴즈형 조회수
q0 = pop[pop["is_quiz"] == 0]["view_count"]         # 비퀴즈형 조회수
e1 = pop[pop["is_quiz"] == 1]["engagement_rate"]    # 퀴즈형 참여율
e0 = pop[pop["is_quiz"] == 0]["engagement_rate"]    # 비퀴즈형 참여율
fig, ax = plt.subplots(1, 2, figsize=(10, 4.5))     # 2패널
ax[0].bar(["퀴즈형", "비퀴즈형"], [q1.median(), q0.median()], color=["#C0392B", "#95A5A6"])
ax[0].set_title(f"조회수 중앙값 (n={len(q1)} vs {len(q0)})")   # n 병기
ax[1].bar(["퀴즈형", "비퀴즈형"], [e1.median(), e0.median()], color=["#C0392B", "#95A5A6"])
ax[1].set_title("참여율 중앙값 (%)")                  # 참여율 병행(조회수 단독 판단 금지)
fig.suptitle("퀴즈형 효과 — 인기층 내부 비교 (제목 기반 추정 라벨)")
plt.tight_layout(); plt.savefig("v_chart2_quiz_effect.png", dpi=130); plt.close()

# ── 차트 3: 인기층 vs 최신층 갭 (키워드별) = 시장 기회 크기 ──
gap = df.groupby(["keyword", "layer"])["view_count"].median().unstack()  # 층별 중앙값
gap = gap.reindex(g.index)                          # 수요 순으로 정렬
x = np.arange(len(gap)); w = 0.38                   # 막대 위치
plt.figure(figsize=(10, 5))
plt.bar(x - w/2, gap["인기"], w, label="인기층", color="#1F2A44")
plt.bar(x + w/2, gap["최신"], w, label="최신층(평균적 신규 영상)", color="#95A5A6")
plt.yscale("log")                                   # 격차가 커서 로그축
plt.xticks(x, gap.index, rotation=30, ha="right")
plt.ylabel("views (median, log)")
plt.title("인기층 vs 최신층 조회수 갭 — 갭이 클수록 '훅 설계'가 성패를 가르는 키워드")
plt.legend(); plt.tight_layout(); plt.savefig("v_chart3_layer_gap.png", dpi=130); plt.close()

# ── 요약 리포트 ──
L = ["# 미니 검증 요약 (미팅용)\n",
     f"- 표본: 총 {len(df)}개 (인기층 {len(pop)}, 최신층 {len(new)}) / 최근 1년 / KR\n",
     f"- 수요 1위 키워드: {g.index[0]} (중앙값 {fmt(g['median'].iloc[0])}, n={g['count'].iloc[0]})\n",
     f"- 퀴즈형 효과(인기층): 조회수 {fmt(q1.median())} vs {fmt(q0.median())}, "
     f"참여율 {e1.median():.2f}% vs {e0.median():.2f}% (n={len(q1)}/{len(q0)})\n",
     "\n## 해석 시 주의(미팅에서 그대로 말할 것)\n",
     "- 퀴즈형 라벨은 제목 기반 추정 → 상위 표본 수동 검수 후 확정 결론.\n",
     "- n<30 셀은 '경향 참고'로만 사용, 결론 금지.\n",
     "- 조회수는 채널 규모 편향 존재 → views_per_sub·참여율 병행 확인.\n",
     "- 이 1장은 '검증의 시작'이지 결론이 아님 — 2주 내 표본 확대·수동 코딩 예정.\n"]
with open("verify_summary.md", "w", encoding="utf-8") as f:
    f.writelines(L)                                 # 리포트 저장
print("완료: 차트 3종 + verify_summary.md 생성")     # 종료 메시지
