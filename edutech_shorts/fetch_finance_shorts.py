# -*- coding: utf-8 -*-
"""
협회(공식 금융기관) 채널의 '주식' 관련 유튜브 쇼츠 수집 스크립트
- 목적: 최근 1년 이내, 180초(3분) 이하 쇼츠 중 주식 관련 콘텐츠를
        채널별로 모아 '조회수 Top5' / '댓글수 Top5'로 정렬해 저장
- 특징: search.list(100유닛/회) 대신 채널 업로드 재생목록(playlistItems, 1유닛/회)을
        사용해 quota를 아끼고, 해당 채널 영상을 빠짐없이 훑는다 (공신력 + 재현성)
"""

import os                       # 환경변수에서 API 키를 읽기 위해 사용
import re                       # ISO8601 재생시간 문자열 파싱에 사용
import datetime as dt           # 최근 1년 기준 날짜 계산에 사용
import pandas as pd             # 수집 결과 정렬/저장(CSV)에 사용
from googleapiclient.discovery import build  # YouTube Data API v3 클라이언트
from dotenv import load_dotenv   # .env 파일에서 키 로드(python-dotenv)

# ─────────────────────────────────────────────────────────────
# 1) 설정: 여기만 바꾸면 됩니다
# ─────────────────────────────────────────────────────────────

load_dotenv()                            # 같은 폴더의 .env 를 읽어 환경변수로 주입
API_KEY = os.environ.get("YT_API_KEY")   # .env 의 YT_API_KEY 또는 시스템 환경변수

# 검증된 공식 채널 목록.
#   지정 방법 3가지 중 하나만 채우면 됨:
#   - handle:     채널 URL의 @뒤 문자열 (예: @fsskorea → "fsskorea")
#   - channel_id: URL의 /channel/ 뒤 UC로 시작하는 ID
#   - username:   레거시 /user/ 경로 문자열
CHANNELS = [
    # ── 최종 선정: 주식·ETF 콘텐츠 밀도 높은 3개 채널 ──
    {"name": "한국거래소KRX",         "handle": "KOREA_EXCHANGE"},               # ETF·주식 상장/거래 주체 (검증됨)
    {"name": "한국금융투자협회",       "channel_id": "UC0FnjiBx8AD-4V5j_9j94wA"}, # KOFIA, 펀드·ETF·투자교육 (검증됨)
    {"name": "전국투자자교육협의회TV", "username": "kcie01"},                     # 투교협, 주린이 교육·벤치마크 (검증됨)

    # 제외 사유:
    #   한국예탁결제원 = 예탁/결제 실무 위주, 주식 쇼츠 적음
    #   금융감독원/금융위원회 = 감독·정책 위주, 주식 콘텐츠 비중 낮음
    #   서민금융진흥원 = 서민·정책금융, 주식 무관 / 여신금융협회 = 공식 채널 미확인 + 카드·여신
]

# '주식' 분류로 인정할 키워드. 제목 또는 설명에 하나라도 포함되면 채택
STOCK_KEYWORDS = ["주식", "ETF", "주린이", "증시", "코스피", "코스닥",
                  "상장", "배당", "공모주", "펀드", "투자"]

MAX_DURATION_SEC = 180          # 쇼츠 판별 기준: 180초(3분) 이하
MONTHS_BACK = 12                # 최근 12개월(1년) 이내만
TOP_N = 5                       # 분류별 상위 몇 개를 뽑을지
OUTPUT_CSV = "stock_shorts_result.csv"  # 결과 저장 파일명

# ─────────────────────────────────────────────────────────────
# 2) 유틸 함수
# ─────────────────────────────────────────────────────────────

def parse_duration(iso: str) -> int:
    """ISO8601 재생시간(PT#M#S)을 초(int)로 변환. 예: 'PT1M30S' -> 90"""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)  # 시/분/초 그룹 추출
    if not m:                                                  # 형식이 안 맞으면
        return 0                                              # 0초로 처리
    h, mi, s = (int(x) if x else 0 for x in m.groups())        # None은 0으로
    return h * 3600 + mi * 60 + s                              # 총 초 반환


def resolve_channel_id(youtube, ch: dict) -> str | None:
    """채널의 channel_id/handle/username 중 지정된 값을 실제 channelId로 변환"""
    if ch.get("channel_id"):                                   # channelId를 직접 준 경우
        return ch["channel_id"]                                # 변환 없이 그대로 사용
    if ch.get("handle"):                                       # 핸들이 있으면
        res = youtube.channels().list(part="id", forHandle=ch["handle"]).execute()
    elif ch.get("username"):                                   # 레거시 username이 있으면
        res = youtube.channels().list(part="id", forUsername=ch["username"]).execute()
    else:                                                      # 아무것도 없으면
        return None
    items = res.get("items", [])                               # 결과 배열
    return items[0]["id"] if items else None                   # 첫 채널의 id 반환


def get_uploads_playlist(youtube, channel_id: str) -> str | None:
    """채널의 '업로드 전체' 재생목록 ID를 가져온다 (모든 영상이 여기 담김)"""
    res = youtube.channels().list(part="contentDetails", id=channel_id).execute()
    items = res.get("items", [])                               # 채널 정보
    if not items:
        return None
    # 업로드 재생목록 ID는 relatedPlaylists.uploads 에 들어있다
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def list_video_ids(youtube, playlist_id: str) -> list[str]:
    """업로드 재생목록을 페이지네이션하며 모든 videoId 수집"""
    ids, token = [], None                                      # 결과 리스트와 다음페이지 토큰
    while True:                                                # 페이지가 없을 때까지 반복
        res = youtube.playlistItems().list(
            part="contentDetails", playlistId=playlist_id,
            maxResults=50, pageToken=token                     # 한 번에 50개(최대)
        ).execute()
        for it in res.get("items", []):                        # 각 항목에서
            ids.append(it["contentDetails"]["videoId"])        # videoId만 추출
        token = res.get("nextPageToken")                       # 다음 페이지 토큰
        if not token:                                          # 더 없으면
            break                                              # 종료
    return ids


def fetch_video_details(youtube, video_ids: list[str]) -> list[dict]:
    """videoId 목록의 상세정보(제목/게시일/길이/조회수/댓글수)를 50개씩 받아온다"""
    rows = []                                                  # 결과 누적
    for i in range(0, len(video_ids), 50):                     # 50개 단위로 끊어서
        chunk = video_ids[i:i + 50]                            # 이번 배치
        res = youtube.videos().list(
            part="snippet,contentDetails,statistics",          # 필요한 3개 파트만
            id=",".join(chunk)                                 # 콤마로 연결한 id들
        ).execute()
        for v in res.get("items", []):                         # 각 영상마다
            stats = v.get("statistics", {})                    # 통계(비공개면 없을 수 있음)
            rows.append({
                "video_id": v["id"],
                "title": v["snippet"]["title"],
                "published_at": v["snippet"]["publishedAt"],
                "duration_sec": parse_duration(v["contentDetails"]["duration"]),
                "view_count": int(stats.get("viewCount", 0)),   # 없으면 0
                "comment_count": int(stats.get("commentCount", 0)),
                "description": v["snippet"].get("description", ""),
            })
    return rows


def is_stock_related(row: dict) -> bool:
    """제목 또는 설명에 주식 키워드가 있으면 True"""
    text = (row["title"] + " " + row["description"])            # 제목+설명 합치기
    return any(kw in text for kw in STOCK_KEYWORDS)             # 키워드 하나라도 포함되면 True


# ─────────────────────────────────────────────────────────────
# 3) 메인 로직
# ─────────────────────────────────────────────────────────────

def main():
    assert API_KEY, "환경변수 YT_API_KEY 가 없습니다. export YT_API_KEY='키' 로 설정하세요."
    youtube = build("youtube", "v3", developerKey=API_KEY)     # API 클라이언트 생성

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=MONTHS_BACK * 30)  # 1년 기준선
    all_rows = []                                              # 전체 채널 결과 누적

    for ch in CHANNELS:                                        # 채널마다 반복
        cid = resolve_channel_id(youtube, ch)                 # 채널ID 확인
        if not cid:                                           # 못 찾으면
            print(f"[경고] 채널을 찾지 못함: {ch['name']}")     # 알리고 건너뜀
            continue
        uploads = get_uploads_playlist(youtube, cid)          # 업로드 재생목록
        vids = list_video_ids(youtube, uploads)               # 모든 videoId
        details = fetch_video_details(youtube, vids)          # 상세정보

        for r in details:                                     # 각 영상 필터링
            pub = dt.datetime.fromisoformat(                  # 게시일 파싱(Z→+00:00)
                r["published_at"].replace("Z", "+00:00"))
            if r["duration_sec"] > MAX_DURATION_SEC:          # 3분 초과면 제외(쇼츠 아님)
                continue
            if pub < cutoff:                                  # 1년보다 오래되면 제외
                continue
            if not is_stock_related(r):                       # 주식 키워드 없으면 제외
                continue
            r["channel"] = ch["name"]                         # 출처 채널명 기록
            r["url"] = f"https://www.youtube.com/shorts/{r['video_id']}"  # 영상 URL
            r["collected_at"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")  # 수집일시(출처추적)
            all_rows.append(r)                                # 채택

    if not all_rows:                                          # 하나도 없으면
        print("조건에 맞는 쇼츠가 없습니다.")
        return

    df = pd.DataFrame(all_rows)                               # 표로 변환
    cols = ["channel", "title", "view_count", "comment_count",
            "duration_sec", "published_at", "url", "collected_at"]  # 저장할 열 순서

    # 채널(=협회)별로 조회수 Top5 / 댓글수 Top5를 각각 뽑아 출력
    results = []                                              # 최종 결과 누적
    for name, g in df.groupby("channel"):                    # 채널 단위 그룹
        top_view = g.sort_values("view_count", ascending=False).head(TOP_N).copy()
        top_view["rank_type"] = "조회수Top5"                  # 정렬 기준 표시
        top_cmt = g.sort_values("comment_count", ascending=False).head(TOP_N).copy()
        top_cmt["rank_type"] = "댓글수Top5"                   # 정렬 기준 표시
        results.extend([top_view, top_cmt])                  # 둘 다 추가

    out = pd.concat(results)[["rank_type"] + cols]           # 열 정리
    out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")  # 엑셀서 한글 안깨지게 utf-8-sig
    print(f"완료: {len(df)}개 수집 → {OUTPUT_CSV} 저장")      # 요약 출력
    print(out.to_string(index=False))                        # 콘솔에 미리보기


if __name__ == "__main__":                                   # 스크립트로 직접 실행할 때만
    main()
