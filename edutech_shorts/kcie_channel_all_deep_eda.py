# -*- coding: utf-8 -*-
"""
kcie_channel_all_deep_eda.py

금융투자아카데미 전체 콘텐츠 CSV(kcie_channel_all.csv)를 발표 자료용으로
다각도 EDA하고 컬럼 설명/해석 주의사항을 Markdown으로 정리한다.

출력:
- kcie_channel_all_eda_report.md
- kcie_channel_column_dictionary.md
- kcie_eda_01_form_overview.png
- kcie_eda_02_year_trend.png
- kcie_eda_03_top_views.png
- kcie_eda_04_top_vpd.png
- kcie_eda_05_duration_scatter.png
- kcie_eda_06_engagement_by_form.png
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import koreanize_matplotlib
except Exception:
    pass

SRC = Path("kcie_channel_all.csv")


COLUMN_DICTIONARY = [
    ("video_id", "YouTube 영상 고유 ID", "영상 URL을 만들거나 중복을 식별할 때 쓰는 값"),
    ("title", "영상 제목", "콘텐츠 주제, 시리즈명, 제목 훅을 확인하는 기본 텍스트"),
    ("channel", "채널명", "이번 데이터에서는 모두 금융투자아카데미"),
    ("channel_id", "YouTube 채널 고유 ID", "채널을 API에서 식별하는 값"),
    ("published_at", "영상 업로드 일시", "UTC 기준 원본 업로드 시각"),
    ("duration_sec", "영상 길이(초)", "쇼츠/롱폼 추정과 길이별 성과 비교에 사용"),
    ("view_count", "누적 조회수", "수집 시점까지 쌓인 영상별 전체 조회수"),
    ("like_count", "좋아요 수", "공개 API에서 제공되는 좋아요 수"),
    ("comment_count", "댓글 수", "공개 API에서 제공되는 댓글 수"),
    ("keyword", "수집/분류 기준", "이번 전체 채널 CSV에서는 `금융투자아카데미 전체`"),
    ("layer", "수집 층위", "이번 전체 채널 CSV에서는 `전체업로드`"),
    ("subscribers", "수집 시점 기준 채널 구독자 수", "영상 업로드 당시 구독자 수가 아니라 스크립트 실행일 기준 현재 구독자 수"),
    ("days_since", "업로드 후 경과일", "수집 시점 - 업로드일. 오래된 영상 보정 참고값"),
    ("vpd", "Views Per Day", "조회수 / 경과일. 업로드 시점 차이를 완화해 보는 일평균 조회수"),
    ("engagement_rate", "참여율(%)", "(좋아요 수 + 댓글 수) / 조회수 * 100. 조회수 100회당 좋아요+댓글 비율"),
    ("views_per_sub", "현재 구독자 수 대비 조회수", "조회수 / 수집 시점 구독자 수. 현재 채널 규모 대비 참고 지표"),
    ("description", "영상 설명란", "해시태그, 타임라인, 링크, 설명 문구 확인에 사용"),
    ("url", "영상 URL", "YouTube 영상으로 바로 이동할 수 있는 링크"),
    ("form", "영상 형태", "길이 기반 추정값: 롱폼, 쇼츠(60s이하), 쇼츠추정(61-180s)"),
    ("year", "업로드 연도", "연도별 업로드/성과 추이에 사용"),
    ("published_date", "업로드 날짜", "YYYY-MM-DD 형태의 날짜"),
    ("content_type", "콘텐츠 타입", "영문 분류값: longform, shorts, shorts_estimated"),
]


def fmt_int(value) -> str:
    if pd.isna(value):
        return "-"
    return f"{int(round(float(value))):,}"


def fmt_float(value, digits=1) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}"


def shorten(text: str, n=34) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def save_column_dictionary() -> None:
    lines = [
        "# kcie_channel_all.csv 컬럼 설명\n",
        "\n",
        "이 문서는 금융투자아카데미 전체 콘텐츠 CSV의 각 컬럼이 무엇을 의미하는지 정리한 자료다.\n",
        "\n",
        "| 컬럼명 | 의미 | 해석/주의 |\n",
        "|---|---|---|\n",
    ]
    for col, meaning, note in COLUMN_DICTIONARY:
        lines.append(f"| `{col}` | {meaning} | {note} |\n")
    lines.extend(
        [
            "\n",
            "## 핵심 주의사항\n",
            "\n",
            "- `subscribers`는 영상 업로드 당시 구독자 수가 아니라, 데이터를 수집한 시점의 채널 현재 구독자 수다.\n",
            "- `views_per_sub`는 현재 구독자 수를 기준으로 한 참고 지표이므로 과거 영상의 당시 성과율로 해석하면 안 된다.\n",
            "- `form`, `content_type`의 쇼츠/롱폼 구분은 영상 길이 기반 추정이다. YouTube Data API는 공식 Shorts 여부 플래그를 제공하지 않는다.\n",
            "- `view_count`는 누적 조회수이므로 오래된 영상이 유리하다. 최신 콘텐츠와 비교할 때는 `vpd`를 함께 보는 편이 안전하다.\n",
        ]
    )
    Path("kcie_channel_column_dictionary.md").write_text("".join(lines), encoding="utf-8")


def plot_form_overview(df: pd.DataFrame) -> None:
    g = (
        df.groupby("form", observed=True)
        .agg(count=("video_id", "count"), median_views=("view_count", "median"), median_vpd=("vpd", "median"))
        .sort_values("count", ascending=False)
    )
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    colors = ["#1F2A44", "#C0392B", "#95A5A6"]
    axes[0].bar(g.index.astype(str), g["count"], color=colors[: len(g)])
    axes[0].set_title("형태별 콘텐츠 수")
    axes[0].set_ylabel("편수")
    axes[1].bar(g.index.astype(str), g["median_views"], color=colors[: len(g)])
    axes[1].set_title("형태별 조회수 중앙값")
    axes[1].set_ylabel("views median")
    axes[2].bar(g.index.astype(str), g["median_vpd"], color=colors[: len(g)])
    axes[2].set_title("형태별 VPD 중앙값")
    axes[2].set_ylabel("views/day median")
    for ax in axes:
        ax.tick_params(axis="x", rotation=20)
    plt.suptitle("금융투자아카데미 전체 콘텐츠 형태별 개요")
    plt.tight_layout()
    plt.savefig("kcie_eda_01_form_overview.png", dpi=150)
    plt.close()


def plot_year_trend(df: pd.DataFrame) -> None:
    yearly = (
        df.groupby("year")
        .agg(count=("video_id", "count"), median_views=("view_count", "median"), median_vpd=("vpd", "median"))
        .sort_index()
    )
    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.bar(yearly.index.astype(str), yearly["count"], color="#95A5A6", label="업로드 편수")
    ax1.set_ylabel("업로드 편수")
    ax1.tick_params(axis="x", rotation=45)
    ax2 = ax1.twinx()
    ax2.plot(yearly.index.astype(str), yearly["median_views"], color="#C0392B", marker="o", label="조회수 중앙값")
    ax2.plot(yearly.index.astype(str), yearly["median_vpd"], color="#1F2A44", marker="o", label="VPD 중앙값")
    ax2.set_ylabel("중앙값")
    ax2.legend(loc="upper left")
    plt.title("연도별 업로드 편수, 조회수 중앙값, VPD 중앙값")
    plt.tight_layout()
    plt.savefig("kcie_eda_02_year_trend.png", dpi=150)
    plt.close()


def plot_top_bar(df: pd.DataFrame, metric: str, filename: str, title: str, color: str) -> None:
    top = df.sort_values(metric, ascending=False).head(12).iloc[::-1]
    labels = [shorten(t, 42) for t in top["title"]]
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.barh(labels, top[metric], color=color)
    ax.set_title(title)
    ax.set_xlabel(metric)
    for i, value in enumerate(top[metric]):
        label = fmt_float(value, 1) if metric in {"vpd", "engagement_rate"} else fmt_int(value)
        ax.text(value, i, f" {label}", va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()


def plot_duration_scatter(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5))
    color_map = {"longform": "#1F2A44", "shorts": "#C0392B", "shorts_estimated": "#E67E22"}
    for ctype, sub in df.groupby("content_type"):
        ax.scatter(
            sub["duration_sec"] / 60,
            sub["view_count"].clip(lower=1),
            s=np.sqrt(sub["like_count"] + sub["comment_count"] + 1) * 10,
            alpha=0.55,
            label=ctype,
            color=color_map.get(ctype, "#95A5A6"),
        )
    ax.set_yscale("log")
    ax.set_xlabel("영상 길이(분)")
    ax.set_ylabel("조회수(log)")
    ax.set_title("영상 길이와 조회수 분포")
    ax.legend()
    plt.tight_layout()
    plt.savefig("kcie_eda_05_duration_scatter.png", dpi=150)
    plt.close()


def plot_engagement_by_form(df: pd.DataFrame) -> None:
    order = df.groupby("form")["engagement_rate"].median().sort_values(ascending=False).index.tolist()
    data = [df[df["form"] == form]["engagement_rate"].clip(upper=df["engagement_rate"].quantile(0.98)) for form in order]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.boxplot(data, tick_labels=order, showfliers=False)
    ax.set_ylabel("참여율(%, 상위 2% 절단 표시)")
    ax.set_title("형태별 참여율 분포")
    ax.tick_params(axis="x", rotation=15)
    plt.tight_layout()
    plt.savefig("kcie_eda_06_engagement_by_form.png", dpi=150)
    plt.close()


def markdown_table(rows, headers) -> str:
    out = ["| " + " | ".join(headers) + " |\n", "|" + "|".join(["---"] * len(headers)) + "|\n"]
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |\n")
    return "".join(out)


def build_report(df: pd.DataFrame) -> None:
    total = len(df)
    snapshot_date = (pd.to_datetime(df["published_at"], utc=True) + pd.to_timedelta(df["days_since"], unit="D")).median()
    snapshot_text = snapshot_date.strftime("%Y-%m-%d") if not pd.isna(snapshot_date) else "수집일 확인 필요"
    subscribers = int(df["subscribers"].iloc[0]) if "subscribers" in df else 0

    form_stats = (
        df.groupby("form", observed=True)
        .agg(
            n=("video_id", "count"),
            median_views=("view_count", "median"),
            mean_views=("view_count", "mean"),
            median_vpd=("vpd", "median"),
            median_eng=("engagement_rate", "median"),
            median_duration=("duration_sec", "median"),
        )
        .sort_values("n", ascending=False)
    )
    form_rows = []
    for form, row in form_stats.iterrows():
        form_rows.append(
            [
                form,
                fmt_int(row["n"]),
                fmt_int(row["median_views"]),
                fmt_int(row["mean_views"]),
                fmt_float(row["median_vpd"], 1),
                fmt_float(row["median_eng"], 3) + "%",
                fmt_int(row["median_duration"]),
            ]
        )

    year_stats = (
        df.groupby("year")
        .agg(n=("video_id", "count"), median_views=("view_count", "median"), median_vpd=("vpd", "median"))
        .sort_index(ascending=False)
        .head(8)
    )
    year_rows = [[int(y), fmt_int(r["n"]), fmt_int(r["median_views"]), fmt_float(r["median_vpd"], 1)] for y, r in year_stats.iterrows()]

    top_views = df.sort_values("view_count", ascending=False).head(10)
    top_vpd = df.sort_values("vpd", ascending=False).head(10)
    top_eng = df[df["view_count"] >= 100].sort_values("engagement_rate", ascending=False).head(10)

    def top_rows(frame, metric):
        rows = []
        for _, r in frame.iterrows():
            metric_value = fmt_float(r[metric], 1) if metric in {"vpd", "engagement_rate"} else fmt_int(r[metric])
            if metric == "engagement_rate":
                metric_value += "%"
            rows.append([shorten(r["title"], 48), r["published_date"], r["form"], metric_value, fmt_int(r["view_count"])])
        return rows

    corr = df[["duration_sec", "view_count", "vpd", "engagement_rate", "days_since"]].corr(numeric_only=True, method="spearman")
    corr_rows = [
        ["길이 vs 조회수", fmt_float(corr.loc["duration_sec", "view_count"], 3)],
        ["길이 vs VPD", fmt_float(corr.loc["duration_sec", "vpd"], 3)],
        ["경과일 vs 조회수", fmt_float(corr.loc["days_since", "view_count"], 3)],
        ["조회수 vs 참여율", fmt_float(corr.loc["view_count", "engagement_rate"], 3)],
    ]

    desc_nonempty = df["description"].fillna("").str.len().gt(0).mean() * 100
    hashtags = df["description"].fillna("").str.findall(r"#[0-9A-Za-z가-힣_]+").explode().dropna().str.lower()
    top_tags = hashtags.value_counts().head(12)
    tag_rows = [[tag, fmt_int(count)] for tag, count in top_tags.items()]

    lines = [
        "# 금융투자아카데미 전체 콘텐츠 EDA\n",
        "\n",
        "## 1. 데이터 개요\n",
        "\n",
        f"- 대상 파일: `kcie_channel_all.csv`\n",
        f"- 대상 채널: 금융투자아카데미\n",
        f"- 콘텐츠 수: {fmt_int(total)}개\n",
        f"- 수집 시점 추정: {snapshot_text}\n",
        f"- 수집 시점 기준 구독자 수: {fmt_int(subscribers)}명\n",
        f"- 업로드 기간: {df['published_date'].min()} ~ {df['published_date'].max()}\n",
        f"- 설명란이 비어 있지 않은 영상 비율: {fmt_float(desc_nonempty, 1)}%\n",
        "\n",
        "이 데이터는 채널 업로드 재생목록을 기준으로 가져온 전체 콘텐츠 목록이다. 최신 360일 제한 없이 채널에 남아 있는 업로드 영상을 모두 대상으로 한다.\n",
        "\n",
        "## 2. 컬럼 의미 요약\n",
        "\n",
        "전체 컬럼 설명은 `kcie_channel_column_dictionary.md`에 따로 정리했다. 발표에서 특히 주의해야 할 컬럼은 다음과 같다.\n",
        "\n",
        "- `subscribers`: 영상 업로드 당시 구독자 수가 아니라 수집 시점 기준 채널 현재 구독자 수다.\n",
        "- `views_per_sub`: `view_count / subscribers`로 계산한 현재 채널 규모 대비 조회수 참고 지표다.\n",
        "- `vpd`: `view_count / days_since`로 계산한 일평균 조회수다. 오래된 영상과 최근 영상을 같이 볼 때 보조 지표로 유용하다.\n",
        "- `engagement_rate`: `(like_count + comment_count) / view_count * 100`이다. 값이 1이면 조회수 100회당 좋아요+댓글이 약 1개라는 뜻이다.\n",
        "- `form`: 영상 길이 기반 추정 분류다. YouTube API에는 공식 Shorts 플래그가 없으므로 `쇼츠(60s이하)`, `쇼츠추정(61-180s)`, `롱폼`으로 나누었다.\n",
        "\n",
        "## 3. 형태별 요약\n",
        "\n",
        markdown_table(
            form_rows,
            ["형태", "편수", "조회수 중앙값", "조회수 평균", "VPD 중앙값", "참여율 중앙값", "길이 중앙값(초)"],
        ),
        "\n",
        "해석 포인트:\n",
        "\n",
        "- 채널 전체 콘텐츠는 롱폼 중심이다.\n",
        "- 쇼츠/쇼츠추정은 편수가 상대적으로 적어, 채널 전체 성과를 대표한다고 보기 어렵다.\n",
        "- 조회수 평균은 일부 대형 영상의 영향을 크게 받으므로 중앙값과 같이 봐야 한다.\n",
        "\n",
        "## 4. 최근 연도별 흐름\n",
        "\n",
        markdown_table(year_rows, ["연도", "편수", "조회수 중앙값", "VPD 중앙값"]),
        "\n",
        "연도별 표는 최근 연도부터 8개년만 표시했다. 조회수는 누적값이라 오래된 연도가 유리할 수 있고, 최근 영상은 `VPD`를 같이 봐야 한다.\n",
        "\n",
        "## 5. 조회수 상위 콘텐츠\n",
        "\n",
        markdown_table(top_rows(top_views, "view_count"), ["제목", "업로드일", "형태", "조회수", "참고 조회수"]),
        "\n",
        "조회수 상위권에는 오래된 특강 영상과 최근 기획성 콘텐츠가 함께 섞여 있다. 누적 조회수만으로 최근 콘텐츠 경쟁력을 판단하면 왜곡될 수 있다.\n",
        "\n",
        "## 6. VPD 상위 콘텐츠\n",
        "\n",
        markdown_table(top_rows(top_vpd, "vpd"), ["제목", "업로드일", "형태", "VPD", "조회수"]),
        "\n",
        "VPD는 업로드 후 하루 평균 조회수다. 최근 콘텐츠의 초기 반응을 비교할 때 누적 조회수보다 더 적합한 보조 지표다.\n",
        "\n",
        "## 7. 참여율 상위 콘텐츠(조회수 100 이상)\n",
        "\n",
        markdown_table(top_rows(top_eng, "engagement_rate"), ["제목", "업로드일", "형태", "참여율", "조회수"]),
        "\n",
        "참여율은 조회수 대비 좋아요+댓글 비율이다. 조회수가 낮은 영상은 참여율이 쉽게 튈 수 있어, 여기서는 조회수 100 이상 영상만 참고했다.\n",
        "\n",
        "## 8. 간단 상관 확인(Spearman)\n",
        "\n",
        markdown_table(corr_rows, ["비교", "상관계수"]),
        "\n",
        "상관계수는 선형 인과관계가 아니라 순위 기반 동행 정도를 보는 참고값이다. 표본에는 업로드 시기, 시리즈, 채널 운영 방식이 섞여 있으므로 과도하게 해석하면 안 된다.\n",
        "\n",
        "## 9. 설명란 해시태그 상위\n",
        "\n",
        markdown_table(tag_rows, ["해시태그", "등장 횟수"]),
        "\n",
        "해시태그는 설명란 기준 단순 집계다. 콘텐츠 주제 분류의 보조 단서로만 활용하는 것이 안전하다.\n",
        "\n",
        "## 10. 차트 산출물\n",
        "\n",
        "- `kcie_eda_01_form_overview.png`: 형태별 편수, 조회수 중앙값, VPD 중앙값\n",
        "- `kcie_eda_02_year_trend.png`: 연도별 업로드 편수, 조회수 중앙값, VPD 중앙값\n",
        "- `kcie_eda_03_top_views.png`: 조회수 상위 콘텐츠\n",
        "- `kcie_eda_04_top_vpd.png`: VPD 상위 콘텐츠\n",
        "- `kcie_eda_05_duration_scatter.png`: 영상 길이와 조회수 분포\n",
        "- `kcie_eda_06_engagement_by_form.png`: 형태별 참여율 분포\n",
        "\n",
        "## 11. 발표용 한 줄 정리\n",
        "\n",
        "> 금융투자아카데미 채널 전체 817개 콘텐츠를 보면 롱폼 비중이 압도적으로 높고, 누적 조회수는 오래된 특강성 콘텐츠의 영향이 크다. 최근 콘텐츠나 HOWTO 계열의 반응을 볼 때는 단순 누적 조회수보다 VPD와 참여율을 함께 확인하는 것이 더 안전하다.\n",
    ]

    Path("kcie_channel_all_eda_report.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(f"{SRC} not found")
    df = pd.read_csv(SRC)
    df["published_at_dt"] = pd.to_datetime(df["published_at"], utc=True)
    df["published_date"] = pd.to_datetime(df["published_date"]).dt.strftime("%Y-%m-%d")

    save_column_dictionary()
    plot_form_overview(df)
    plot_year_trend(df)
    plot_top_bar(df, "view_count", "kcie_eda_03_top_views.png", "조회수 상위 콘텐츠", "#1F2A44")
    plot_top_bar(df, "vpd", "kcie_eda_04_top_vpd.png", "VPD 상위 콘텐츠", "#C0392B")
    plot_duration_scatter(df)
    plot_engagement_by_form(df)
    build_report(df)
    print("완료: 컬럼 설명 + EDA 리포트 + 차트 6종 생성")


if __name__ == "__main__":
    main()
