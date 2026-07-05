# 주식 쇼츠 시장 EDA — 사용법

투교협 [How to] 롱폼 유입용 홍보 쇼츠 기획을 위해,
"시장에서 인기 있는 주식 쇼츠가 무엇이고 왜 인기인지"를 객관적 지표로 분석하는 도구.

## 파일 구성
| 파일 | 역할 |
|---|---|
| `benchmark_seed.csv` | 팀(윤소정·김동현)이 고른 10개 벤치마크 (10가지 유형) |
| `collect_shorts.py` | YouTube API 수집기 → `shorts_raw.csv` 생성 |
| `eda_analysis.py` | 분석·시각화 → 차트 PNG + `insight_report.md` 생성 |
| `fetch_finance_shorts.py` | (구버전) 협회 3채널 Top5만 뽑는 단순 스크립트 |

## 실행 순서

### 0. 준비 (한 번만)
```bash
pip install google-api-python-client pandas matplotlib koreanize-matplotlib --break-system-packages
export YT_API_KEY="본인_API_키"          # mac/linux
# Windows PowerShell:  $env:YT_API_KEY="키"
```

### 1. 데이터 수집
```bash
python collect_shorts.py     # → shorts_raw.csv
```
- 소스 A: 협회 3채널(KRX·KOFIA·투교협) = 우리 채널 baseline
- 소스 B: 키워드 검색(주식·ETF·주린이 등) = 시장 인기 쇼츠
- 정규화 지표 자동 계산: 참여율(engagement_rate), 댓글율, VPD(조회수/경과일)

### 2. EDA 분석
```bash
python eda_analysis.py       # → chart_*.png + insight_report.md
```
- `shorts_raw.csv`가 있으면 자동 병합 분석, 없으면 seed 10개만으로 시연

## 인기 지표 설계 (MECE)
| 구분 | 지표 | 의미 |
|---|---|---|
| 절대치 | view_count, comment_count | 규모. 단, 채널 크기·경과일에 편향 |
| 정규화 | engagement_rate=(좋아요+댓글)/조회 | 참여 밀도. 채널 규모 편향 완화 |
| 정규화 | comment_rate=댓글/조회 | 토론·바이럴성 |
| 정규화 | vpd=조회수/게시경과일 | 조회 '속도'. 오래된 영상 유리함 보정 |

## 분석 축
1. **유형별 인기** — 10유형 중 어떤 유형이 조회수·참여율이 높은가
2. **제목·형식 특징** — 숫자/질문형/N가지·Top/파워워드가 인기와 어떻게 연관되나
3. **길이** — 60초 경계로 최적 구간 탐색

## 반드시 유의 (데이터 정직성)
- seed 10개는 **유형당 1개**라 통계 결론이 아니라 '경향 참고'. 결론은 수집 데이터로.
- 조회수만으로 순위 매기지 말 것 → 참여율·VPD 병행.
- 자동 유형 라벨은 제목 기반 **추정**이므로 수동 검수 필요.
- **쇼츠→롱폼 유입/전환은 공개 API로 측정 불가.** 성과 검증은 투교협 YouTube Studio
  애널리틱스(트래픽 소스)가 있어야 하며, 이 도구는 그 전 단계인 '시장 분석'용.

## 실무/코테 응용 포인트
- **정규화 지표 설계**: 절대치 편향을 보정하는 비율 지표는 실무 지표 설계의 핵심.
- **특징 추출(feature engineering)**: 텍스트(제목)에서 정규식으로 특징 뽑기 = NLP 전처리 기본.
- **groupby + median 비교**: 평균 대신 중앙값을 쓰는 이유 = 조회수 롱테일(이상치) 방어.
