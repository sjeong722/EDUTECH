# -*- coding: utf-8 -*-
"""
kcie_channel_analysis.py

금융투자아카데미(@kcie01) YouTube 채널의 전체 업로드 콘텐츠를 수집·분석한다.

범위:
- 최신 360일 제한 없음
- 채널 업로드 재생목록 전체
- 롱폼, 쇼츠 추정 콘텐츠 모두 포함

출력:
- kcie_channel_all.csv
- kcie_chart_form_compare.png
- kcie_chart_timeline.png
- kcie_channel_summary.md
"""

import datetime as dt
import os
import re
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from googleapiclient.discovery import build

try:
    import koreanize_matplotlib
except Exception:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

API_KEY = os.environ.get("YT_API_KEY")
HANDLE_CANDIDATES = ["kcie01", "@kcie01"]
USERNAME_CANDIDATE = "kcie01"
SHORTS_MAX_SEC = 180
OUT_CSV = "kcie_channel_all.csv"

BEGINNER_BASE_COLUMNS = [
    "video_id",
    "title",
    "channel",
    "channel_id",
    "published_at",
    "duration_sec",
    "view_count",
    "like_count",
    "comment_count",
    "keyword",
    "layer",
    "subscribers",
    "days_since",
    "vpd",
    "engagement_rate",
    "views_per_sub",
]


def execute(req, label, tries=3):
    """YouTube API request with a small retry cushion for transient network resets."""
    last = None
    for attempt in range(1, tries + 1):
        try:
            return req.execute()
        except Exception as exc:
            last = exc
            if attempt == tries:
                raise
            wait = attempt * 2
            print(f"{label} 재시도 {attempt}/{tries - 1}: {exc} ({wait}s 대기)")
            time.sleep(wait)
    raise last


def parse_dur(iso):
    """ISO8601 duration such as PT1M23S -> seconds."""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    h, mi, s = ((int(x) if x else 0) for x in (m.groups() if m else (0, 0, 0)))
    return h * 3600 + mi * 60 + s


def classify_form(duration_sec):
    """Approximate Shorts/longform classification. YouTube API has no official Shorts flag."""
    if duration_sec <= 60:
        return "쇼츠(60s이하)"
    if duration_sec <= SHORTS_MAX_SEC:
        return "쇼츠추정(61-180s)"
    return "롱폼"


def get_channel(yt):
    """Resolve @kcie01 / legacy username into channel metadata and uploads playlist."""
    for handle in HANDLE_CANDIDATES:
        res = execute(
            yt.channels().list(part="id,snippet,statistics,contentDetails", forHandle=handle),
            f"channels.list forHandle={handle}",
        )
        if res.get("items"):
            item = res["items"][0]
            break
    else:
        res = execute(
            yt.channels().list(part="id,snippet,statistics,contentDetails", forUsername=USERNAME_CANDIDATE),
            f"channels.list forUsername={USERNAME_CANDIDATE}",
        )
        if not res.get("items"):
            raise RuntimeError("@kcie01 채널을 찾지 못했습니다.")
        item = res["items"][0]

    stats = item.get("statistics", {})
    return {
        "channel_id": item["id"],
        "channel_title": item["snippet"]["title"],
        "uploads": item["contentDetails"]["relatedPlaylists"]["uploads"],
        "video_count": int(stats.get("videoCount", 0)),
        "subscribers": int(stats.get("subscriberCount", 0)),
    }


def all_video_ids(yt, uploads_id):
    """Collect all uploaded video IDs from the channel uploads playlist."""
    ids, token = [], None
    while True:
        res = execute(
            yt.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_id,
                maxResults=50,
                pageToken=token,
            ),
            "playlistItems.list uploads",
        )
        ids.extend(i["contentDetails"]["videoId"] for i in res.get("items", []))
        token = res.get("nextPageToken")
        if not token:
            break
    return ids


def fetch_details(yt, ids):
    """Fetch snippet/content/statistics for all video IDs in 50-item batches."""
    rows = []
    for i in range(0, len(ids), 50):
        batch = ids[i : i + 50]
        res = execute(
            yt.videos().list(part="snippet,contentDetails,statistics", id=",".join(batch)),
            f"videos.list {i + 1}-{i + len(batch)}",
        )
        for video in res.get("items", []):
            snippet = video.get("snippet", {})
            stats = video.get("statistics", {})
            duration_sec = parse_dur(video.get("contentDetails", {}).get("duration"))
            rows.append(
                {
                    "video_id": video["id"],
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "channel_id": snippet.get("channelId", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "duration_sec": duration_sec,
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                    "keyword": "금융투자아카데미 전체",
                    "layer": "전체업로드",
                    "description": snippet.get("description", ""),
                    "url": f"https://www.youtube.com/watch?v={video['id']}",
                    "form": classify_form(duration_sec),
                }
            )
    return rows


def add_metrics(df, subscribers):
    """Add normalized metrics aligned with beginner_shorts.csv."""
    df["subscribers"] = subscribers
    now = dt.datetime.now(dt.timezone.utc)
    pub = pd.to_datetime(df["published_at"], utc=True)
    df["days_since"] = ((now - pub).dt.total_seconds() / 86400).clip(lower=1).round(1)
    df["vpd"] = (df["view_count"] / df["days_since"]).round(1)
    views = df["view_count"].clip(lower=1)
    df["engagement_rate"] = ((df["like_count"] + df["comment_count"]) / views * 100).round(3)
    df["views_per_sub"] = (df["view_count"] / max(subscribers, 1)).round(4)
    df["year"] = pub.dt.year
    df["published_date"] = pub.dt.strftime("%Y-%m-%d")
    df["content_type"] = df["form"].map(
        {
            "쇼츠(60s이하)": "shorts",
            "쇼츠추정(61-180s)": "shorts_estimated",
            "롱폼": "longform",
        }
    )
    return df


def save_ordered_csv(df):
    extra = [c for c in df.columns if c not in BEGINNER_BASE_COLUMNS]
    df[BEGINNER_BASE_COLUMNS + extra].to_csv(OUT_CSV, index=False, encoding="utf-8-sig")


def charts_and_report(df, info):
    by_form = df.groupby("form", observed=True)["view_count"].agg(["median", "count"]).sort_values("median", ascending=False)
    by_form_eng = df.groupby("form", observed=True)["engagement_rate"].median().reindex(by_form.index)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8))
    axes[0].bar(by_form.index.astype(str), by_form["median"], color="#1F2A44")
    axes[0].set_title("형태별 조회수 중앙값")
    axes[0].set_ylabel("views median")
    axes[0].tick_params(axis="x", rotation=20)
    for i, (median, count) in enumerate(zip(by_form["median"], by_form["count"])):
        axes[0].text(i, median, f"{int(median):,}\n(n={count})", ha="center", va="bottom", fontsize=8)

    axes[1].bar(by_form_eng.index.astype(str), by_form_eng.values, color="#C0392B")
    axes[1].set_title("형태별 참여율 중앙값")
    axes[1].set_ylabel("%")
    axes[1].tick_params(axis="x", rotation=20)
    fig.suptitle("금융투자아카데미 채널 전체 콘텐츠")
    plt.tight_layout()
    plt.savefig("kcie_chart_form_compare.png", dpi=130)
    plt.close()

    yearly = df.groupby("year")["view_count"].agg(["count", "median"])
    fig, ax1 = plt.subplots(figsize=(10, 4.8))
    ax1.bar(yearly.index.astype(int).astype(str), yearly["count"], color="#95A5A6")
    ax1.set_ylabel("업로드 편수")
    ax2 = ax1.twinx()
    ax2.plot(yearly.index.astype(int).astype(str), yearly["median"], color="#C0392B", marker="o")
    ax2.set_ylabel("조회수 중앙값")
    plt.title("연도별 업로드 편수와 조회수 중앙값")
    plt.tight_layout()
    plt.savefig("kcie_chart_timeline.png", dpi=130)
    plt.close()

    top = df.sort_values("view_count", ascending=False).head(10)
    lines = [
        "# 금융투자아카데미 채널 전체 콘텐츠 탐색 요약\n",
        "\n",
        f"- 채널명: {info['channel_title']}\n",
        f"- API 기준 전체 영상 수: {info['video_count']}개\n",
        f"- 실제 수집 영상 수: {len(df)}개\n",
        f"- 구독자 수: {info['subscribers']:,}명\n",
        f"- 형태 분포: {df['form'].value_counts().to_dict()}\n",
        f"- 형태별 조회수 중앙값: {by_form['median'].round(1).to_dict()}\n",
        "\n",
        "## 조회수 상위 10개\n",
    ]
    for _, row in top.iterrows():
        lines.append(f"- [{int(row['view_count']):,}회] {row['title']} ({row['form']}, {row['published_date']})\n")
    lines.extend(
        [
            "\n",
            "## 해석 시 주의\n",
            "- 쇼츠/롱폼 구분은 영상 길이 기반 추정이다. YouTube Data API에는 공식 Shorts 여부 플래그가 없다.\n",
            "- 오래된 영상은 조회수 누적에 유리하므로 조회수와 함께 VPD(일평균 조회)를 같이 봐야 한다.\n",
            "- 이 자료는 시장 및 채널 현황을 보기 위한 탐색 자료이며, 최종 성과 판단 자료는 아니다.\n",
        ]
    )
    with open("kcie_channel_summary.md", "w", encoding="utf-8") as f:
        f.writelines(lines)


def main():
    if not API_KEY:
        raise RuntimeError("YT_API_KEY 환경변수가 없습니다. .env에 YT_API_KEY를 넣거나 export 후 실행하세요.")

    yt = build("youtube", "v3", developerKey=API_KEY)
    info = get_channel(yt)
    print(f"채널 확인: {info['channel_title']} / API 기준 전체 영상 {info['video_count']}개")

    ids = all_video_ids(yt, info["uploads"])
    print(f"업로드 재생목록에서 videoId {len(ids)}개 확인")

    df = pd.DataFrame(fetch_details(yt, ids))
    df = add_metrics(df, info["subscribers"])
    save_ordered_csv(df)
    charts_and_report(df, info)
    print(f"완료: {len(df)}개 → {OUT_CSV} + 차트 2종 + kcie_channel_summary.md")


if __name__ == "__main__":
    main()
