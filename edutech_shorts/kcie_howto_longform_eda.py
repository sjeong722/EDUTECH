# -*- coding: utf-8 -*-
"""
kcie_howto_longform_eda.py

금융투자아카데미 '금융투자 HOWTO' 재생목록의 1~7편 롱폼만 따로 추출해
차시별 성과를 탐색한다.

입력:
- kcie_howto.csv

출력:
- kcie_howto_longform_7.csv
- howto7_chart_views_vpd.png
- howto7_chart_engagement.png
- howto7_chart_metric_table.png
- howto7_eda_summary.md
"""

import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

try:
    import koreanize_matplotlib
except Exception:
    pass

SRC = "kcie_howto.csv"
OUT = "kcie_howto_longform_7.csv"


def episode_no(title):
    m = re.search(r"금융투자\s*HOWTO\s*(\d+)편", str(title), flags=re.I)
    return int(m.group(1)) if m else None


def short_topic(title):
    text = str(title)
    text = re.sub(r"\s*[ㅣ|l]\s*금융투자\s*HOWTO\s*\d+편.*$", "", text, flags=re.I)
    return text.strip()


def fmt_int(x):
    return f"{int(round(x)):,}"


def main():
    df = pd.read_csv(SRC)
    df["episode_no"] = df["title"].map(episode_no)
    hw7 = df[
        (df["episode_no"].between(1, 7))
        & (df["howto_playlist_titles"].fillna("").str.contains("금융투자 HOWTO"))
        & (df["content_type"].eq("longform"))
    ].copy()

    if len(hw7) != 7:
        print(f"주의: 금융투자 HOWTO 1~7편으로 추정된 영상이 {len(hw7)}개입니다.")

    hw7["episode_topic"] = hw7["title"].map(short_topic)
    hw7 = hw7.sort_values("episode_no").reset_index(drop=True)
    hw7.to_csv(OUT, index=False, encoding="utf-8-sig")

    labels = [f"{int(r.episode_no)}편\n{r.episode_topic[:14]}…" if len(r.episode_topic) > 14 else f"{int(r.episode_no)}편\n{r.episode_topic}" for r in hw7.itertuples()]

    # 1) 조회수 + VPD
    fig, ax1 = plt.subplots(figsize=(11, 5.2))
    bars = ax1.bar(range(len(hw7)), hw7["view_count"], color="#1F2A44")
    ax1.set_ylabel("조회수")
    ax1.set_xticks(range(len(hw7)))
    ax1.set_xticklabels(labels, rotation=0, fontsize=8)
    for bar, value in zip(bars, hw7["view_count"]):
        ax1.text(bar.get_x() + bar.get_width() / 2, value, fmt_int(value), ha="center", va="bottom", fontsize=8)
    ax2 = ax1.twinx()
    ax2.plot(range(len(hw7)), hw7["vpd"], color="#E67E22", marker="o", linewidth=2)
    ax2.set_ylabel("VPD(일평균 조회)")
    plt.title("금융투자 HOWTO 1~7편: 누적 조회수와 VPD")
    plt.tight_layout()
    plt.savefig("howto7_chart_views_vpd.png", dpi=140)
    plt.close()

    # 2) 참여율 + 좋아요/댓글
    fig, ax = plt.subplots(figsize=(11, 5.2))
    bars = ax.bar(range(len(hw7)), hw7["engagement_rate"], color="#C0392B")
    ax.set_ylabel("참여율(%)")
    ax.set_xticks(range(len(hw7)))
    ax.set_xticklabels(labels, fontsize=8)
    for bar, value in zip(bars, hw7["engagement_rate"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}%", ha="center", va="bottom", fontsize=8)
    plt.title("금융투자 HOWTO 1~7편: 조회수 대비 좋아요+댓글 참여율")
    plt.tight_layout()
    plt.savefig("howto7_chart_engagement.png", dpi=140)
    plt.close()

    # 3) 핵심 지표 테이블 이미지
    table_df = hw7[
        [
            "episode_no",
            "episode_topic",
            "published_date",
            "duration_sec",
            "view_count",
            "like_count",
            "comment_count",
            "vpd",
            "engagement_rate",
        ]
    ].copy()
    table_df.columns = ["편", "주제", "업로드일", "길이(초)", "조회수", "좋아요", "댓글", "VPD", "참여율(%)"]
    for col in ["조회수", "좋아요", "댓글"]:
        table_df[col] = table_df[col].map(lambda x: f"{int(x):,}")
    table_df["VPD"] = table_df["VPD"].map(lambda x: f"{x:,.1f}")
    table_df["참여율(%)"] = table_df["참여율(%)"].map(lambda x: f"{x:.3f}")

    fig, ax = plt.subplots(figsize=(14, 3.8))
    ax.axis("off")
    tbl = ax.table(
        cellText=table_df.values,
        colLabels=table_df.columns,
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.6)
    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_facecolor("#1F2A44")
            cell.set_text_props(color="white", weight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#F2F4F7")
    plt.title("금융투자 HOWTO 1~7편 핵심 지표", pad=12)
    plt.tight_layout()
    plt.savefig("howto7_chart_metric_table.png", dpi=160)
    plt.close()

    top_views = hw7.loc[hw7["view_count"].idxmax()]
    top_vpd = hw7.loc[hw7["vpd"].idxmax()]
    top_eng = hw7.loc[hw7["engagement_rate"].idxmax()]
    median_views = hw7["view_count"].median()
    median_vpd = hw7["vpd"].median()
    median_eng = hw7["engagement_rate"].median()

    lines = [
        "# 금융투자 HOWTO 1~7편 롱폼 EDA\n",
        "\n",
        "## 범위\n",
        "\n",
        "- 대상: 금융투자아카데미 `금융투자 HOWTO` 재생목록의 1~7편 롱폼\n",
        "- 제외: 예전 `How To 주식투자`, `How to ELS/DLS` 재생목록 및 HOWTO 표기만 있는 기타 영상\n",
        "- 기준 데이터: `kcie_howto.csv`\n",
        "- 표본 수: 7개\n",
        "\n",
        "## 핵심 요약\n",
        "\n",
        f"- 조회수 중앙값: {fmt_int(median_views)}회\n",
        f"- VPD 중앙값: {median_vpd:,.1f}\n",
        f"- 참여율 중앙값: {median_eng:.3f}%\n",
        f"- 조회수 1위: {int(top_views['episode_no'])}편 `{top_views['episode_topic']}` ({fmt_int(top_views['view_count'])}회)\n",
        f"- VPD 1위: {int(top_vpd['episode_no'])}편 `{top_vpd['episode_topic']}` ({top_vpd['vpd']:,.1f})\n",
        f"- 참여율 1위: {int(top_eng['episode_no'])}편 `{top_eng['episode_topic']}` ({top_eng['engagement_rate']:.3f}%)\n",
        "\n",
        "## 차시별 지표\n",
        "\n",
        "| 편 | 주제 | 업로드일 | 길이(초) | 조회수 | 좋아요 | 댓글 | VPD | 참여율(%) |\n",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|\n",
    ]
    for _, row in hw7.iterrows():
        lines.append(
            f"| {int(row['episode_no'])} | {row['episode_topic']} | {row['published_date']} | "
            f"{int(row['duration_sec'])} | {fmt_int(row['view_count'])} | {fmt_int(row['like_count'])} | "
            f"{fmt_int(row['comment_count'])} | {row['vpd']:,.1f} | {row['engagement_rate']:.3f} |\n"
        )

    lines.extend(
        [
            "\n",
            "## 읽는 법\n",
            "\n",
            "- `조회수`는 누적 성과다. 먼저 올라온 영상일수록 누적에 유리할 수 있다.\n",
            "- `VPD`는 업로드 이후 하루 평균 조회수다. 업로드 시점 차이를 어느 정도 보정해서 보는 참고 지표다.\n",
            "- `참여율`은 `(좋아요 수 + 댓글 수) / 조회수 × 100`이다. 조회수 100회당 좋아요+댓글이 얼마나 발생했는지 보는 비율이다.\n",
            "- 표본이 7개뿐이므로 통계적 결론이 아니라 차시별 현황 확인용으로 해석해야 한다.\n",
            "\n",
            "## 산출물\n",
            "\n",
            "- `kcie_howto_longform_7.csv`: 1~7편 롱폼 필터링 CSV\n",
            "- `howto7_chart_views_vpd.png`: 누적 조회수와 VPD 비교\n",
            "- `howto7_chart_engagement.png`: 참여율 비교\n",
            "- `howto7_chart_metric_table.png`: 핵심 지표 테이블 이미지\n",
        ]
    )

    with open("howto7_eda_summary.md", "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"완료: {len(hw7)}개 → {OUT}, 차트 3종, howto7_eda_summary.md")


if __name__ == "__main__":
    main()
