# -*- coding: utf-8 -*-
"""
kcie_howto_analysis.py

금융투자아카데미(@kcie01) 채널 전체 데이터 중 HOW TO 재생목록 및 HOW TO 표기와 관련된
롱폼·쇼츠 콘텐츠를 추출·분석한다.

선행 입력:
- kcie_channel_all.csv

출력:
- kcie_howto.csv
- howto_chart_series.png
- howto_summary.md
"""

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
SRC = "kcie_channel_all.csv"
OUT_CSV = "kcie_howto.csv"
FALLBACK_HOWTO_PLAYLIST_IDS = ["PL8XSXtoKTTP5RvjND768FcjUB4QMnhItg"]
HOWTO_TITLE_PAT = r"HOW\s*TO|HOWTO|하우투|금융투자\s*HOW\s*TO|금융투자\s*HOWTO"

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


def list_howto_playlists(yt, channel_id):
    """Find channel playlists whose title looks like HOW TO, with fallback ID included."""
    playlists = {}
    token = None
    while True:
        res = execute(
            yt.playlists().list(
                part="id,snippet",
                channelId=channel_id,
                maxResults=50,
                pageToken=token,
            ),
            "playlists.list",
        )
        for item in res.get("items", []):
            title = item.get("snippet", {}).get("title", "")
            if re.search(HOWTO_TITLE_PAT, title, flags=re.I):
                playlists[item["id"]] = title
        token = res.get("nextPageToken")
        if not token:
            break

    for playlist_id in FALLBACK_HOWTO_PLAYLIST_IDS:
        playlists.setdefault(playlist_id, "금융투자 HOW TO 재생목록(후보)")
    return playlists


def playlist_video_ids(yt, playlist_id):
    ids, token = [], None
    while True:
        res = execute(
            yt.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=token,
            ),
            f"playlistItems.list {playlist_id}",
        )
        ids.extend(i["contentDetails"]["videoId"] for i in res.get("items", []))
        token = res.get("nextPageToken")
        if not token:
            break
    return ids


def collect_playlist_memberships(yt, playlists):
    video_to_playlists = {}
    for playlist_id, title in playlists.items():
        try:
            for video_id in playlist_video_ids(yt, playlist_id):
                video_to_playlists.setdefault(video_id, []).append(title)
        except Exception as exc:
            print(f"재생목록 조회 실패: {playlist_id} / {title} / {exc}")
    return video_to_playlists


def relation_label(in_playlist, text_match):
    if in_playlist and text_match:
        return "재생목록+표기매칭"
    if in_playlist:
        return "재생목록"
    return "표기매칭"


def save_ordered_csv(df):
    extra = [c for c in df.columns if c not in BEGINNER_BASE_COLUMNS]
    df[BEGINNER_BASE_COLUMNS + extra].to_csv(OUT_CSV, index=False, encoding="utf-8-sig")


def chart_and_report(hw, playlists):
    if hw.empty:
        with open("howto_summary.md", "w", encoding="utf-8") as f:
            f.write("# 금융투자 HOW TO 관련 콘텐츠 탐색 요약\n\n- 추출된 콘텐츠가 없습니다.\n")
        return

    ordered = hw.sort_values("published_at").reset_index(drop=True)
    colors = ordered["content_type"].map({"longform": "#1F2A44"}).fillna("#C0392B")
    labels = [t[:18] + "…" if len(t) > 18 else t for t in ordered["title"]]

    fig, ax1 = plt.subplots(figsize=(12, 5.5))
    ax1.bar(range(len(ordered)), ordered["view_count"], color=colors)
    ax1.set_ylabel("조회수")
    ax1.set_xticks(range(len(ordered)))
    ax1.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax2 = ax1.twinx()
    ax2.plot(range(len(ordered)), ordered["vpd"], color="#E67E22", marker="o", linewidth=1.2)
    ax2.set_ylabel("VPD(일평균 조회)")
    plt.title("금융투자 HOW TO 관련 콘텐츠: 조회수와 VPD")
    plt.tight_layout()
    plt.savefig("howto_chart_series.png", dpi=130)
    plt.close()

    longform = hw[hw["content_type"] == "longform"]
    shorts = hw[hw["content_type"] != "longform"]
    top = hw.sort_values("view_count", ascending=False).head(10)
    playlist_titles = ", ".join(playlists.values()) if playlists else "확인된 HOW TO 재생목록 없음"

    lines = [
        "# 금융투자 HOW TO 관련 콘텐츠 탐색 요약\n",
        "\n",
        f"- 추출 기준 재생목록: {playlist_titles}\n",
        f"- HOW TO 관련 콘텐츠: 총 {len(hw)}개\n",
        f"- 재생목록 포함: {int(hw['in_howto_playlist'].sum())}개\n",
        f"- 제목/설명 표기 매칭: {int(hw['howto_text_match'].sum())}개\n",
        f"- 롱폼: {len(longform)}개 / 조회수 중앙값 {int(longform['view_count'].median()) if len(longform) else 0:,}회 / VPD 중앙값 {longform['vpd'].median() if len(longform) else 0:.1f}\n",
        f"- 쇼츠·쇼츠추정: {len(shorts)}개 / 조회수 중앙값 {int(shorts['view_count'].median()) if len(shorts) else 0:,}회 / VPD 중앙값 {shorts['vpd'].median() if len(shorts) else 0:.1f}\n",
        "\n",
        "## 조회수 상위 10개\n",
    ]
    for _, row in top.iterrows():
        lines.append(
            f"- [{int(row['view_count']):,}회] {row['title']} "
            f"({row['form']}, {row['relation']}, {row['published_date']})\n"
        )
    lines.extend(
        [
            "\n",
            "## 해석 시 주의\n",
            "- HOW TO 관련 여부는 재생목록 포함 여부와 제목/설명 표기 매칭을 함께 사용한 탐색 기준이다.\n",
            "- 표기매칭만으로 잡힌 영상은 실제 관련성이 낮을 수 있어 수동 확인이 필요하다.\n",
            "- 쇼츠/롱폼 구분은 길이 기반 추정이며, YouTube Data API의 공식 Shorts 플래그가 아니다.\n",
            "- 오래된 롱폼은 조회수 누적에 유리하므로 VPD와 함께 봐야 한다.\n",
        ]
    )
    with open("howto_summary.md", "w", encoding="utf-8") as f:
        f.writelines(lines)


def main():
    if not os.path.exists(SRC):
        raise RuntimeError(f"{SRC}가 없습니다. kcie_channel_analysis.py를 먼저 실행하세요.")
    if not API_KEY:
        raise RuntimeError("YT_API_KEY 환경변수가 없습니다. .env에 YT_API_KEY를 넣거나 export 후 실행하세요.")

    df = pd.read_csv(SRC)
    channel_id = df["channel_id"].dropna().iloc[0]

    yt = build("youtube", "v3", developerKey=API_KEY)
    playlists = list_howto_playlists(yt, channel_id)
    memberships = collect_playlist_memberships(yt, playlists)
    playlist_ids = set(memberships.keys())

    text = df["title"].fillna("") + " " + df.get("description", "").fillna("")
    df["in_howto_playlist"] = df["video_id"].isin(playlist_ids).astype(int)
    df["howto_text_match"] = text.str.contains(HOWTO_TITLE_PAT, regex=True, flags=re.I).astype(int)
    df["howto_playlist_titles"] = df["video_id"].map(lambda x: " | ".join(memberships.get(x, [])))

    hw = df[(df["in_howto_playlist"] == 1) | (df["howto_text_match"] == 1)].copy()
    hw["relation"] = hw.apply(lambda r: relation_label(bool(r["in_howto_playlist"]), bool(r["howto_text_match"])), axis=1)
    hw["keyword"] = "금융투자 HOW TO"
    hw["layer"] = hw["relation"]
    hw = hw.sort_values(["published_at", "title"])

    save_ordered_csv(hw)
    chart_and_report(hw, playlists)
    print(f"완료: HOW TO 관련 {len(hw)}개 → {OUT_CSV} + howto_chart_series.png + howto_summary.md")


if __name__ == "__main__":
    main()
