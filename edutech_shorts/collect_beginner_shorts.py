# -*- coding: utf-8 -*-
"""
collect_beginner_shorts.py — 금융투자 HOWTO 쇼츠 기획용 '초보 타깃' 표본 수집기
  설계 핵심: 같은 키워드를 [인기순 + 최신순] 2층으로 수집 → 인기 vs 평균 대조군 확보
  (v1 벤치마킹 가설을 통계적으로 검증하기 위한 표본 설계)
  실행: export YT_API_KEY="키" 후 python collect_beginner_shorts.py
  출력: beginner_shorts.csv
  쿼터: 9키워드 × 2정렬 × 1페이지 × 100유닛 = 1,800유닛 (일일 한도 10,000 내)
"""

import os                                          # 환경변수에서 API 키 읽기
import re                                          # ISO8601 재생시간 파싱
import datetime as dt                              # 날짜 계산
import pandas as pd                                # 표 정리/저장
from googleapiclient.discovery import build       # YouTube Data API v3 클라이언트

API_KEY = os.environ.get("YT_API_KEY")             # API 키 (환경변수 필수)

# 쇼츠 4편 + OX퀴즈 트랙과 1:1로 맞춘 초보 키워드 (기획안 근거와 직결되도록 구성)
SEARCH_QUERIES = [
    "주식 계좌 개설",      # 쇼츠 후보: 계좌 개설
    "MTS 사용법",          # 쇼츠 #1: HTS vs MTS
    "예수금",              # 쇼츠 #2: 매수 안 될 때(D+2) / OX 문제은행
    "호가창 보는법",        # 4강 핵심 화면(기준가·희망가·대기물량)
    "우선주 보통주",        # 쇼츠 #3: '우'가 붙은 이유
    "주식 차트 보는법",     # 쇼츠 #4: 52주 고저
    "주식 초보",           # 타깃 일반 키워드
    "주린이",              # 타깃 페르소나 키워드
    "금융 퀴즈",           # OX퀴즈형 시장 존재 확인용
]
MONTHS_BACK = 12                                   # 최근 1년
MAX_DURATION = 180                                 # 쇼츠 판별 상한(3분)
OUT = "beginner_shorts.csv"                        # 출력 파일명

def parse_dur(iso):
    """ISO8601(PT#M#S) → 초 단위 변환"""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")   # 시/분/초 추출
    h, mi, s = ((int(x) if x else 0) for x in (m.groups() if m else (0,0,0)))  # None→0
    return h*3600 + mi*60 + s                       # 총 초 반환

def search_ids(yt, q, order, after):
    """키워드 × 정렬 기준으로 쇼츠 후보 videoId 50개 수집 (search.list=100유닛)"""
    r = yt.search().list(part="id", q=q, type="video",
                         videoDuration="short",     # 4분 미만(쇼츠 근사)
                         order=order,               # viewCount(인기층) / date(최신층)
                         publishedAfter=after,      # 최근 1년만
                         regionCode="KR", relevanceLanguage="ko",
                         maxResults=50).execute()   # 1페이지=50개
    return [i["id"]["videoId"] for i in r.get("items", []) if i["id"].get("videoId")]

def fetch(yt, ids):
    """videoId 상세정보 일괄 조회 (videos.list=50개당 1유닛)"""
    rows = []                                       # 결과 누적 리스트
    uniq = list(dict.fromkeys(ids))                 # 중복 제거(순서 유지)
    for i in range(0, len(uniq), 50):               # 50개 단위 배치
        r = yt.videos().list(part="snippet,contentDetails,statistics",
                             id=",".join(uniq[i:i+50])).execute()
        for v in r.get("items", []):                # 각 영상 파싱
            st = v.get("statistics", {})            # 통계(비공개 시 없음)
            rows.append({
                "video_id": v["id"],
                "title": v["snippet"]["title"],
                "channel": v["snippet"]["channelTitle"],
                "channel_id": v["snippet"]["channelId"],       # 구독자수 조인용
                "published_at": v["snippet"]["publishedAt"],
                "duration_sec": parse_dur(v["contentDetails"]["duration"]),
                "view_count": int(st.get("viewCount", 0)),
                "like_count": int(st.get("likeCount", 0)),
                "comment_count": int(st.get("commentCount", 0)),
            })
    return rows

def add_subs(yt, df):
    """channels.list로 구독자수 추가 → 채널 규모 정규화 지표의 재료 (50개당 1유닛)"""
    cids = df["channel_id"].dropna().unique().tolist()          # 고유 채널 ID
    subs = {}                                                   # id→구독자수 매핑
    for i in range(0, len(cids), 50):                           # 50개 배치
        r = yt.channels().list(part="statistics", id=",".join(cids[i:i+50])).execute()
        for c in r.get("items", []):                            # 각 채널 파싱
            subs[c["id"]] = int(c["statistics"].get("subscriberCount", 0))
    df["subscribers"] = df["channel_id"].map(subs).fillna(0).astype(int)  # 매핑
    return df

def main():
    assert API_KEY, "YT_API_KEY 환경변수가 없습니다."           # 키 확인
    yt = build("youtube", "v3", developerKey=API_KEY)          # 클라이언트 생성
    after = (dt.datetime.now(dt.timezone.utc)
             - dt.timedelta(days=MONTHS_BACK*30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    tag = {}                                                    # videoId→(키워드, 층)
    for q in SEARCH_QUERIES:                                    # 키워드 루프
        for order, layer in [("viewCount", "인기"), ("date", "최신")]:  # 2층 수집
            for vid in search_ids(yt, q, order, after):         # 검색 실행
                tag.setdefault(vid, (q, layer))                 # 첫 출처만 유지

    df = pd.DataFrame(fetch(yt, list(tag.keys())))              # 상세정보 수집
    df["keyword"] = df["video_id"].map(lambda v: tag[v][0])     # 키워드 태그
    df["layer"] = df["video_id"].map(lambda v: tag[v][1])       # 인기/최신 층 태그
    df = df[df["duration_sec"] <= MAX_DURATION]                 # 쇼츠 길이 필터

    df = add_subs(yt, df)                                       # 구독자수 조인
    now = dt.datetime.now(dt.timezone.utc)                      # 현재 시각
    pub = pd.to_datetime(df["published_at"], utc=True)          # 게시일 파싱
    df["days_since"] = ((now-pub).dt.total_seconds()/86400).clip(lower=1).round(1)  # 경과일
    df["vpd"] = (df["view_count"]/df["days_since"]).round(0)    # 조회 속도(경과일 보정)
    v = df["view_count"].clip(lower=1)                          # 0 나눗셈 방지
    df["engagement_rate"] = ((df["like_count"]+df["comment_count"])/v*100).round(3)  # 참여율
    df["views_per_sub"] = (df["view_count"]/df["subscribers"].clip(lower=1)).round(2) # 도달배율

    df.to_csv(OUT, index=False, encoding="utf-8-sig")           # 한글 안 깨지게 저장
    print(f"완료: {len(df)}개 → {OUT}")                          # 결과 요약 출력
    print(df.groupby(["keyword","layer"]).size())               # 키워드×층 분포 확인

if __name__ == "__main__":
    main()
