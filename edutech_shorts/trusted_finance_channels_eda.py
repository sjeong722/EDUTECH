# -*- coding: utf-8 -*-
"""
trusted_finance_channels_eda.py

국내 공공·협회·금융교육 기관이 운영하거나 주관하는 YouTube 채널을 모아
"처음 투자 공부를 할 때는 공신력 있는 기관 콘텐츠부터 참고하자"는 메시지를
뒷받침하기 위한 탐색 자료를 만든다.

출력:
- trusted_finance_official_channels.csv
- trusted_finance_official_contents.csv
- trusted_finance_investment_contents.csv
- trusted_finance_channels_report.md
- trusted_eda_01_channel_inventory.png
- trusted_eda_02_investment_content_mix.png
- trusted_eda_03_content_type_by_channel.png
- trusted_eda_04_top_investment_vpd.png
- trusted_eda_05_message_evidence.png
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
SHORTS_MAX_SEC = 180

CHANNELS = [
    {
        "institution": "한국거래소",
        "channel_name_expected": "KRX 한국거래소",
        "channel_id": "UCS9GDeqpgGtDYy_Nx8opCZw",
        "institution_type": "시장 인프라",
        "credibility_note": "증권·파생상품 시장 운영기관",
        "official_status": "공식 채널",
    },
    {
        "institution": "한국거래소",
        "channel_name_expected": "베짱이하우스 by KRX",
        "channel_id": "UC9x7FeCs47yZ7Hio5RHq9eQ",
        "institution_type": "시장 인프라",
        "credibility_note": "KRX 투자교육/콘텐츠 채널",
        "official_status": "기관 운영 채널",
    },
    {
        "institution": "한국금융투자협회",
        "channel_name_expected": "한국금융투자협회",
        "channel_id": "UC0FnjiBx8AD-4V5j_9j94wA",
        "institution_type": "금융투자 협회",
        "credibility_note": "금융투자회사 협회 공식 채널",
        "official_status": "공식 채널",
    },
    {
        "institution": "전국투자자교육협의회",
        "channel_name_expected": "금융투자아카데미",
        "channel_id": "UCBryaPNZJE5bcaKxJO-PasA",
        "institution_type": "투자자 교육",
        "credibility_note": "투자자교육협의회 교육 채널",
        "official_status": "기관 운영 채널",
    },
    {
        "institution": "금융감독원",
        "channel_name_expected": "금융감독원(Financial Supervisory Service)",
        "channel_id": "UCjA-tHJ2xLwZRXzqXq0UaqA",
        "institution_type": "감독·소비자보호",
        "credibility_note": "금융감독원 공식 채널",
        "official_status": "공식 채널",
    },
    {
        "institution": "금융위원회",
        "channel_name_expected": "금융위원회",
        "channel_id": "UCuJz-PXNMdWQr6TNM4htENw",
        "institution_type": "정책기관",
        "credibility_note": "금융정책 담당 정부기관 공식 채널",
        "official_status": "공식 채널",
    },
    {
        "institution": "한국예탁결제원",
        "channel_name_expected": "한국예탁결제원",
        "channel_id": "UCCkOHu8cifMUsfrlv2tBB_A",
        "institution_type": "시장 인프라",
        "credibility_note": "자본시장 예탁·결제 인프라 기관 채널",
        "official_status": "공식 채널",
    },
    {
        "institution": "예금보험공사",
        "channel_name_expected": "예금보험공사 예보TV",
        "channel_id": "UCq_FlkcUOP6iPyZ44SBkkzQ",
        "institution_type": "금융소비자 보호",
        "credibility_note": "예금자보호 제도 담당 공공기관 공식 채널",
        "official_status": "공식 채널",
    },
    {
        "institution": "서민금융진흥원",
        "channel_name_expected": "서민금융진흥원",
        "channel_id": "UC1Ke0iC2-bJ6kbDZ86ye4GA",
        "institution_type": "정책서민금융",
        "credibility_note": "정책서민금융 지원기관 공식 채널",
        "official_status": "공식 채널",
    },
    {
        "institution": "신용회복위원회",
        "channel_name_expected": "신용회복위원회 CCRS",
        "channel_id": "UCkgdp_3RuH6Lcn2pqwPINIQ",
        "institution_type": "신용회복·상담",
        "credibility_note": "신용회복위원회 공식 채널",
        "official_status": "공식 채널",
    },
    {
        "institution": "여신금융협회",
        "channel_name_expected": "여신금융협회 서포크레딧",
        "channel_id": "UCZd7eGYZDaYoDtmHt6tvk4w",
        "institution_type": "여신·신용교육",
        "credibility_note": "여신금융협회 주관 신용교육 성격의 채널",
        "official_status": "협회 주관 채널",
    },
]

INVESTMENT_KEYWORDS = [
    "주식", "투자", "ETF", "펀드", "증권", "자산관리", "재테크", "연금",
    "ISA", "IRP", "공모주", "배당", "코스피", "코스닥", "상장", "금융투자",
    "채권", "ELS", "DLS", "MTS", "계좌", "주린이", "초보",
]

RISK_KEYWORDS = [
    "사기", "불법", "주의", "피해", "보이스피싱", "리딩방", "투자사기", "불공정",
    "분쟁", "소비자", "보호", "경고", "유의",
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


def parse_duration(iso):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    h, mi, s = ((int(x) if x else 0) for x in (m.groups() if m else (0, 0, 0)))
    return h * 3600 + mi * 60 + s


def classify_form(duration_sec):
    if duration_sec <= 60:
        return "쇼츠(60s이하)"
    if duration_sec <= SHORTS_MAX_SEC:
        return "쇼츠추정(61-180s)"
    return "롱폼"


def text_has_any(text, keywords):
    text = str(text)
    return int(any(k.lower() in text.lower() for k in keywords))


def fetch_channel_info(yt, channel):
    res = execute(
        yt.channels().list(part="id,snippet,statistics,contentDetails", id=channel["channel_id"]),
        f"channels.list {channel['institution']}",
    )
    if not res.get("items"):
        raise RuntimeError(f"채널 조회 실패: {channel}")
    item = res["items"][0]
    stats = item.get("statistics", {})
    return {
        **channel,
        "channel_id": item["id"],
        "channel": item["snippet"].get("title", channel["channel_name_expected"]),
        "description": item["snippet"].get("description", ""),
        "published_at": item["snippet"].get("publishedAt", ""),
        "subscribers": int(stats.get("subscriberCount", 0)),
        "channel_view_count": int(stats.get("viewCount", 0)),
        "api_video_count": int(stats.get("videoCount", 0)),
        "uploads_playlist": item["contentDetails"]["relatedPlaylists"]["uploads"],
    }


def list_video_ids(yt, playlist_id):
    ids, token = [], None
    while True:
        res = execute(
            yt.playlistItems().list(part="contentDetails", playlistId=playlist_id, maxResults=50, pageToken=token),
            "playlistItems.list uploads",
        )
        ids.extend(x["contentDetails"]["videoId"] for x in res.get("items", []))
        token = res.get("nextPageToken")
        if not token:
            break
    return ids


def fetch_video_details(yt, ids, channel_info):
    rows = []
    for i in range(0, len(ids), 50):
        batch = ids[i : i + 50]
        res = execute(
            yt.videos().list(part="snippet,contentDetails,statistics", id=",".join(batch)),
            f"videos.list {channel_info['institution']} {i + 1}-{i + len(batch)}",
        )
        for video in res.get("items", []):
            snippet = video.get("snippet", {})
            stats = video.get("statistics", {})
            duration_sec = parse_duration(video.get("contentDetails", {}).get("duration"))
            text = f"{snippet.get('title', '')} {snippet.get('description', '')}"
            view_count = int(stats.get("viewCount", 0))
            like_count = int(stats.get("likeCount", 0))
            comment_count = int(stats.get("commentCount", 0))
            rows.append(
                {
                    "video_id": video["id"],
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", channel_info["channel"]),
                    "channel_id": snippet.get("channelId", channel_info["channel_id"]),
                    "institution": channel_info["institution"],
                    "institution_type": channel_info["institution_type"],
                    "official_status": channel_info["official_status"],
                    "credibility_note": channel_info["credibility_note"],
                    "published_at": snippet.get("publishedAt", ""),
                    "duration_sec": duration_sec,
                    "view_count": view_count,
                    "like_count": like_count,
                    "comment_count": comment_count,
                    "description": snippet.get("description", ""),
                    "url": f"https://www.youtube.com/watch?v={video['id']}",
                    "form": classify_form(duration_sec),
                    "content_type": {
                        "쇼츠(60s이하)": "shorts",
                        "쇼츠추정(61-180s)": "shorts_estimated",
                        "롱폼": "longform",
                    }[classify_form(duration_sec)],
                    "is_investment_related": text_has_any(text, INVESTMENT_KEYWORDS),
                    "is_risk_safety_related": text_has_any(text, RISK_KEYWORDS),
                    "matched_investment_keywords": ", ".join([k for k in INVESTMENT_KEYWORDS if k.lower() in text.lower()]),
                    "matched_risk_keywords": ", ".join([k for k in RISK_KEYWORDS if k.lower() in text.lower()]),
                    "subscribers": channel_info["subscribers"],
                }
            )
    return rows


def add_metrics(df):
    now = dt.datetime.now(dt.timezone.utc)
    pub = pd.to_datetime(df["published_at"], utc=True)
    df["published_date"] = pub.dt.strftime("%Y-%m-%d")
    df["year"] = pub.dt.year
    df["days_since"] = ((now - pub).dt.total_seconds() / 86400).clip(lower=1).round(1)
    df["vpd"] = (df["view_count"] / df["days_since"]).round(1)
    views = df["view_count"].clip(lower=1)
    df["engagement_rate"] = ((df["like_count"] + df["comment_count"]) / views * 100).round(3)
    df["views_per_sub"] = (df["view_count"] / df["subscribers"].clip(lower=1)).round(4)
    return df


def fmt_int(x):
    return f"{int(round(float(x))):,}"


def shorten(text, n=36):
    text = re.sub(r"\s+", " ", str(text)).strip()
    text = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf\u200d\ufe0f]", "", text)
    return text if len(text) <= n else text[: n - 1] + "…"


def save_charts(channels_df, contents_df, invest_df):
    # 1. 채널별 전체 업로드 수
    ch = channels_df.sort_values("collected_video_count", ascending=True)
    plt.figure(figsize=(10, 6))
    plt.barh(ch["channel"], ch["collected_video_count"], color="#1F2A44")
    plt.title("공공·협회 금융기관 YouTube 채널 보유 콘텐츠 수")
    plt.xlabel("수집된 업로드 영상 수")
    for i, v in enumerate(ch["collected_video_count"]):
        plt.text(v, i, f" {int(v):,}", va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig("trusted_eda_01_channel_inventory.png", dpi=150)
    plt.close()

    # 2. 투자 관련 콘텐츠 수
    mix = (
        contents_df.groupby("channel")
        .agg(total=("video_id", "count"), investment=("is_investment_related", "sum"), safety=("is_risk_safety_related", "sum"))
        .sort_values("investment", ascending=True)
    )
    plt.figure(figsize=(10, 6))
    plt.barh(mix.index, mix["investment"], color="#C0392B", label="투자/주식/ETF 관련")
    plt.barh(mix.index, mix["safety"], left=mix["investment"], color="#E67E22", label="위험/피해예방 관련")
    plt.title("채널별 투자·위험예방 관련 콘텐츠 수")
    plt.xlabel("콘텐츠 수")
    plt.legend()
    plt.tight_layout()
    plt.savefig("trusted_eda_02_investment_content_mix.png", dpi=150)
    plt.close()

    # 3. 콘텐츠 형태 비중
    pivot = contents_df.pivot_table(index="channel", columns="form", values="video_id", aggfunc="count", fill_value=0)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]
    pivot.plot(kind="barh", stacked=True, figsize=(10, 6), color=["#1F2A44", "#C0392B", "#95A5A6"])
    plt.title("채널별 롱폼·쇼츠 구성")
    plt.xlabel("콘텐츠 수")
    plt.tight_layout()
    plt.savefig("trusted_eda_03_content_type_by_channel.png", dpi=150)
    plt.close()

    # 4. 투자 관련 VPD 상위
    top = invest_df.sort_values("vpd", ascending=False).head(12).iloc[::-1]
    labels = [f"{shorten(t, 42)}\n({c})" for t, c in zip(top["title"], top["channel"])]
    plt.figure(figsize=(11, 7))
    plt.barh(labels, top["vpd"], color="#1F2A44")
    plt.title("공신력 채널 투자 관련 콘텐츠 VPD 상위")
    plt.xlabel("VPD(일평균 조회수)")
    for i, v in enumerate(top["vpd"]):
        plt.text(v, i, f" {v:,.1f}", va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig("trusted_eda_04_top_investment_vpd.png", dpi=150)
    plt.close()

    # 5. 메시지 증거용 요약 카드
    total_channels = len(channels_df)
    total_contents = len(contents_df)
    invest_count = int(contents_df["is_investment_related"].sum())
    safety_count = int(contents_df["is_risk_safety_related"].sum())
    shorts_count = int(contents_df["content_type"].isin(["shorts", "shorts_estimated"]).sum())

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.axis("off")
    items = [
        ("공공·협회성 채널", f"{total_channels}개"),
        ("전체 수집 콘텐츠", f"{total_contents:,}개"),
        ("투자·주식·ETF 관련", f"{invest_count:,}개"),
        ("위험·피해예방 관련", f"{safety_count:,}개"),
        ("쇼츠·쇼츠추정 콘텐츠", f"{shorts_count:,}개"),
    ]
    y = 0.83
    ax.text(0.02, 0.95, "공신력 있는 기관 채널에서도 투자 공부 콘텐츠를 찾을 수 있다", fontsize=17, weight="bold")
    ax.text(0.02, 0.89, "처음 투자 정보를 접할 때는 출처가 확인되는 채널부터 보는 것이 안전하다.", fontsize=11)
    for label, value in items:
        ax.text(0.04, y, label, fontsize=13, color="#1F2A44")
        ax.text(0.72, y, value, fontsize=18, weight="bold", color="#C0392B")
        y -= 0.13
    ax.text(0.02, 0.08, "주의: 채널 목록은 YouTube API 검색과 채널 설명을 기준으로 구성한 탐색용 목록이며, 투자 권유가 아니다.", fontsize=9, color="#555555")
    plt.tight_layout()
    plt.savefig("trusted_eda_05_message_evidence.png", dpi=150)
    plt.close()


def markdown_table(rows, headers):
    out = ["| " + " | ".join(headers) + " |\n", "|" + "|".join(["---"] * len(headers)) + "|\n"]
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |\n")
    return "".join(out)


def save_report(channels_df, contents_df, invest_df):
    top_invest = invest_df.sort_values("vpd", ascending=False).head(10)
    channel_rows = []
    for _, r in channels_df.sort_values("investment_content_count", ascending=False).iterrows():
        channel_rows.append([
            r["institution"],
            r["channel"],
            r["institution_type"],
            r["official_status"],
            fmt_int(r["collected_video_count"]),
            fmt_int(r["investment_content_count"]),
            fmt_int(r["risk_safety_content_count"]),
        ])

    top_rows = []
    for _, r in top_invest.iterrows():
        top_rows.append([
            shorten(r["title"], 46),
            r["channel"],
            r["published_date"],
            r["form"],
            fmt_int(r["view_count"]),
            f"{r['vpd']:,.1f}",
        ])

    lines = [
        "# 공신력 있는 금융기관 YouTube 채널 탐색 EDA\n",
        "\n",
        "## 핵심 메시지\n",
        "\n",
        "> 유튜브에는 투자 관련 정보가 많지만 출처와 신뢰도가 제각각이다. 처음 주식·ETF·펀드 공부를 시작할 때는 한국거래소, 금융투자협회, 투자자교육협의회, 금융감독원 등 공공·협회성 기관이 운영하거나 주관하는 채널의 콘텐츠를 먼저 참고하는 것이 더 안전하다.\n",
        "\n",
        "## 데이터 범위\n",
        "\n",
        f"- 채널 수: {len(channels_df)}개\n",
        f"- 전체 수집 콘텐츠: {len(contents_df):,}개\n",
        f"- 투자·주식·ETF 관련 콘텐츠: {int(contents_df['is_investment_related'].sum()):,}개\n",
        f"- 위험·피해예방 관련 콘텐츠: {int(contents_df['is_risk_safety_related'].sum()):,}개\n",
        "- 수집 방식: 각 채널의 업로드 재생목록 전체를 YouTube Data API로 조회\n",
        "- 날짜 제한: 없음. 채널에 남아 있는 전체 업로드 기준\n",
        "\n",
        "## 채널별 요약\n",
        "\n",
        markdown_table(channel_rows, ["기관", "채널", "기관 유형", "공식성 구분", "전체 콘텐츠", "투자 관련", "위험예방 관련"]),
        "\n",
        "## VPD 기준 투자 관련 콘텐츠 상위\n",
        "\n",
        markdown_table(top_rows, ["제목", "채널", "업로드일", "형태", "조회수", "VPD"]),
        "\n",
        "## 발표에 사용할 수 있는 해석\n",
        "\n",
        "- 공공기관·협회 채널에도 투자 입문, ETF, 주식, 연금, 피해예방 등 다양한 교육 콘텐츠가 존재한다.\n",
        "- 특히 금융투자아카데미, 한국거래소, 한국금융투자협회는 투자·자본시장 주제와 직접 연결된다.\n",
        "- 금융감독원·금융위원회·예금보험공사·신용회복위원회 등은 투자 수익률보다 금융소비자 보호와 위험 예방 관점에서 참고 가치가 있다.\n",
        "- 여신금융협회 관련 채널은 본협회 공식 본채널이라기보다 협회 주관 신용교육 채널 성격으로 구분해 설명하는 것이 안전하다.\n",
        "\n",
        "## 주의사항\n",
        "\n",
        "- 이 자료는 공신력 있는 출처를 소개하기 위한 탐색 자료이며, 특정 상품·종목·투자 결정을 권유하는 자료가 아니다.\n",
        "- `투자 관련` 여부는 제목과 설명의 키워드 기반 자동 분류다. 발표에서 개별 콘텐츠를 추천하려면 수동 검수가 필요하다.\n",
        "- YouTube API는 공식 Shorts 여부를 제공하지 않으므로 쇼츠 구분은 길이 기반 추정이다.\n",
        "- 조회수는 오래된 콘텐츠가 유리하므로 최신 반응은 VPD와 함께 확인해야 한다.\n",
        "\n",
        "## 산출물\n",
        "\n",
        "- `trusted_finance_official_channels.csv`: 채널 단위 요약\n",
        "- `trusted_finance_official_contents.csv`: 채널 전체 콘텐츠 단위 데이터\n",
        "- `trusted_finance_investment_contents.csv`: 투자 관련 키워드로 필터링한 콘텐츠\n",
        "- `trusted_eda_01_channel_inventory.png`: 채널별 콘텐츠 수\n",
        "- `trusted_eda_02_investment_content_mix.png`: 투자/위험예방 관련 콘텐츠 수\n",
        "- `trusted_eda_03_content_type_by_channel.png`: 채널별 롱폼·쇼츠 구성\n",
        "- `trusted_eda_04_top_investment_vpd.png`: 투자 관련 콘텐츠 VPD 상위\n",
        "- `trusted_eda_05_message_evidence.png`: 발표 메시지용 요약 카드\n",
    ]
    with open("trusted_finance_channels_report.md", "w", encoding="utf-8") as f:
        f.writelines(lines)


def main():
    if not API_KEY:
        raise RuntimeError("YT_API_KEY 환경변수가 없습니다. .env에 YT_API_KEY를 넣고 실행하세요.")

    yt = build("youtube", "v3", developerKey=API_KEY)
    channel_infos = []
    content_rows = []

    for ch in CHANNELS:
        info = fetch_channel_info(yt, ch)
        print(f"채널 확인: {info['institution']} / {info['channel']} / API 영상 {info['api_video_count']}개")
        ids = list_video_ids(yt, info["uploads_playlist"])
        info["collected_video_count"] = len(ids)
        rows = fetch_video_details(yt, ids, info)
        channel_infos.append(info)
        content_rows.extend(rows)

    contents_df = add_metrics(pd.DataFrame(content_rows))
    channels_df = pd.DataFrame(channel_infos)

    channel_content = contents_df.groupby("channel").agg(
        collected_video_count=("video_id", "count"),
        investment_content_count=("is_investment_related", "sum"),
        risk_safety_content_count=("is_risk_safety_related", "sum"),
        shorts_count=("content_type", lambda s: s.isin(["shorts", "shorts_estimated"]).sum()),
        median_views=("view_count", "median"),
        median_vpd=("vpd", "median"),
    ).reset_index()
    channels_df = channels_df.drop(columns=["collected_video_count"], errors="ignore").merge(channel_content, on="channel", how="left")

    invest_df = contents_df[contents_df["is_investment_related"].eq(1)].copy()

    channels_df.to_csv("trusted_finance_official_channels.csv", index=False, encoding="utf-8-sig")
    contents_df.to_csv("trusted_finance_official_contents.csv", index=False, encoding="utf-8-sig")
    invest_df.to_csv("trusted_finance_investment_contents.csv", index=False, encoding="utf-8-sig")

    save_charts(channels_df, contents_df, invest_df)
    save_report(channels_df, contents_df, invest_df)
    print(
        f"완료: 채널 {len(channels_df)}개, 전체 콘텐츠 {len(contents_df):,}개, "
        f"투자 관련 {len(invest_df):,}개"
    )


if __name__ == "__main__":
    main()
