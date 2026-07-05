# -*- coding: utf-8 -*-
"""
collect_shorts.py — 주식 관련 유튜브 쇼츠 수집기 (2소스 통합)
  소스 A) 협회 채널(KRX·KOFIA·투교협) = '우리 채널' baseline
  소스 B) 키워드 검색               = 시장에서 대중적으로 인기 있는 쇼츠

수집 후 정규화 지표(참여율·VPD)까지 계산해 shorts_raw.csv 로 저장한다.
이 CSV를 eda_analysis.py 에 넣으면 분석·시각화가 돌아간다.
"""

import os                       # 환경변수에서 API 키 읽기
import re                       # ISO8601 재생시간 파싱
import datetime as dt           # 날짜 계산
import pandas as pd             # 표 정리/저장
from googleapiclient.discovery import build  # YouTube Data API v3
from dotenv import load_dotenv   # .env 파일에서 키 로드(python-dotenv)

# ─────────────────────────────────────────────────────────────
# 1) 설정
# ─────────────────────────────────────────────────────────────
load_dotenv()                            # 같은 폴더의 .env 를 읽어 환경변수로 주입
API_KEY = os.environ.get("YT_API_KEY")   # .env 의 YT_API_KEY 또는 시스템 환경변수

# (소스 A) 협회 채널 = 우리 채널 baseline
CHANNELS = [
    {"name": "한국거래소KRX",         "handle": "KOREA_EXCHANGE"},
    {"name": "한국금융투자협회",       "channel_id": "UC0FnjiBx8AD-4V5j_9j94wA"},
    {"name": "전국투자자교육협의회TV", "username": "kcie01"},
]

# (소스 B) 시장 인기 쇼츠 검색어. 유형별 표본을 넓히기 위해 다양하게 구성
SEARCH_QUERIES = ["주식 투자", "ETF 투자", "주린이", "재테크 주식", "주식 초보", "배당주"]

MAX_DURATION_SEC = 180          # 쇼츠 판별: 180초(3분) 이하
MONTHS_BACK = 12                # 최근 1년
PAGES_PER_QUERY = 1             # 검색어당 페이지 수(1페이지=50개). quota 아끼려면 1 권장
REGION = "KR"                   # 한국 지역
OUTPUT_CSV = "shorts_raw.csv"   # 결과 파일

# ─────────────────────────────────────────────────────────────
# 2) 유틸
# ─────────────────────────────────────────────────────────────
def parse_duration(iso: str) -> int:
    """ISO8601(PT#M#S) → 초. 예: 'PT1M16S' → 76"""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)  # 시/분/초 추출
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())         # None→0
    return h * 3600 + mi * 60 + s


def resolve_channel_id(youtube, ch: dict) -> str | None:
    """channel_id/handle/username → 실제 channelId"""
    if ch.get("channel_id"):                                    # 이미 ID면 그대로
        return ch["channel_id"]
    if ch.get("handle"):                                        # 핸들 조회
        res = youtube.channels().list(part="id", forHandle=ch["handle"]).execute()
    elif ch.get("username"):                                    # 레거시 username 조회
        res = youtube.channels().list(part="id", forUsername=ch["username"]).execute()
    else:
        return None
    items = res.get("items", [])
    return items[0]["id"] if items else None


def channel_video_ids(youtube, channel_id: str) -> list[str]:
    """채널 업로드 재생목록에서 모든 videoId 수집 (playlistItems=1유닛/회)"""
    res = youtube.channels().list(part="contentDetails", id=channel_id).execute()
    items = res.get("items", [])
    if not items:
        return []
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]  # 업로드 재생목록
    ids, token = [], None
    while True:                                                 # 페이지네이션
        r = youtube.playlistItems().list(
            part="contentDetails", playlistId=uploads,
            maxResults=50, pageToken=token).execute()
        ids += [it["contentDetails"]["videoId"] for it in r.get("items", [])]
        token = r.get("nextPageToken")
        if not token:
            break
    return ids


def search_video_ids(youtube, query: str, after_iso: str) -> list[str]:
    """키워드로 인기순 쇼츠 후보 videoId 수집 (search.list=100유닛/회)"""
    ids, token = [], None
    for _ in range(PAGES_PER_QUERY):                            # 검색어당 지정 페이지 수만
        r = youtube.search().list(
            part="id", q=query, type="video",
            videoDuration="short",                              # 4분 미만(쇼츠 근사)
            order="viewCount",                                  # 조회수 높은 순
            publishedAfter=after_iso,                           # 최근 1년
            regionCode=REGION, relevanceLanguage="ko",          # 한국·한국어
            maxResults=50, pageToken=token).execute()
        ids += [it["id"]["videoId"] for it in r.get("items", []) if it["id"].get("videoId")]
        token = r.get("nextPageToken")
        if not token:
            break
    return ids


def fetch_details(youtube, video_ids: list[str]) -> list[dict]:
    """videoId들의 상세정보 수집 (videos.list=50개당 1유닛)"""
    rows, uniq = [], list(dict.fromkeys(video_ids))             # 중복 제거(순서 유지)
    for i in range(0, len(uniq), 50):                           # 50개씩
        r = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=",".join(uniq[i:i + 50])).execute()
        for v in r.get("items", []):
            st = v.get("statistics", {})                        # 통계(비공개 가능)
            rows.append({
                "video_id": v["id"],
                "title": v["snippet"]["title"],
                "channel": v["snippet"]["channelTitle"],
                "published_at": v["snippet"]["publishedAt"],
                "duration_sec": parse_duration(v["contentDetails"]["duration"]),
                "view_count": int(st.get("viewCount", 0)),
                "like_count": int(st.get("likeCount", 0)),      # 비공개면 0
                "comment_count": int(st.get("commentCount", 0)),
                "description": v["snippet"].get("description", ""),
            })
    return rows

# ─────────────────────────────────────────────────────────────
# 3) 지표 계산
# ─────────────────────────────────────────────────────────────
def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """정규화 지표(참여율·VPD) 추가로 채널 규모·게시시점 편향 보정"""
    now = dt.datetime.now(dt.timezone.utc)                      # 현재(UTC)
    pub = pd.to_datetime(df["published_at"], utc=True)          # 게시일 파싱
    df["days_since"] = ((now - pub).dt.total_seconds() / 86400).round(1)  # 경과일
    df["days_since"] = df["days_since"].clip(lower=1)           # 0일 나눗셈 방지
    df["vpd"] = (df["view_count"] / df["days_since"]).round(0)  # 하루평균 조회수(속도)
    v = df["view_count"].clip(lower=1)                          # 0 조회수 나눗셈 방지
    df["comment_rate"] = (df["comment_count"] / v * 100).round(3)   # 댓글참여율(%)
    df["like_rate"] = (df["like_count"] / v * 100).round(3)         # 좋아요율(%)
    df["engagement_rate"] = (((df["like_count"] + df["comment_count"]) / v) * 100).round(3)  # 종합참여율(%)
    return df

# ─────────────────────────────────────────────────────────────
# 4) 메인
# ─────────────────────────────────────────────────────────────
def main():
    assert API_KEY, "환경변수 YT_API_KEY 가 없습니다. export YT_API_KEY='키' 로 설정하세요."
    yt = build("youtube", "v3", developerKey=API_KEY)          # 클라이언트
    after = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=MONTHS_BACK * 30)
             ).strftime("%Y-%m-%dT%H:%M:%SZ")                  # 1년 전 ISO

    collected = []                                             # (videoId, source) 모음

    # 소스 A: 협회 채널
    for ch in CHANNELS:
        cid = resolve_channel_id(yt, ch)
        if not cid:
            print(f"[경고] 채널 못 찾음: {ch['name']}")
            continue
        for vid in channel_video_ids(yt, cid):
            collected.append((vid, f"협회:{ch['name']}"))

    # 소스 B: 키워드 검색
    for q in SEARCH_QUERIES:
        for vid in search_video_ids(yt, q, after):
            collected.append((vid, f"시장검색:{q}"))

    # 상세정보 일괄 조회
    src_map = {}                                               # videoId→source(첫 출처 유지)
    for vid, src in collected:
        src_map.setdefault(vid, src)
    details = fetch_details(yt, list(src_map.keys()))

    # 필터: 쇼츠(≤180s) + 최근 1년
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=MONTHS_BACK * 30)
    rows = []
    for r in details:
        pub = dt.datetime.fromisoformat(r["published_at"].replace("Z", "+00:00"))
        if r["duration_sec"] > MAX_DURATION_SEC or pub < cutoff:  # 조건 미달 제외
            continue
        r["source"] = src_map.get(r["video_id"], "")           # 출처 태그
        r["url"] = f"https://www.youtube.com/shorts/{r['video_id']}"
        rows.append(r)

    if not rows:
        print("조건에 맞는 쇼츠가 없습니다.")
        return

    df = add_metrics(pd.DataFrame(rows))                       # 지표 추가
    df = df.sort_values("view_count", ascending=False)         # 조회수순 정렬
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")   # 한글 안깨지게 저장
    print(f"완료: {len(df)}개 수집 → {OUTPUT_CSV}")
    print(f"  - 협회 baseline: {df['source'].str.startswith('협회').sum()}개")
    print(f"  - 시장검색: {df['source'].str.startswith('시장').sum()}개")


if __name__ == "__main__":
    main()
