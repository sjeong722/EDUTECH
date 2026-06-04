# EduTech Letter

최근 에듀테크 뉴스 기사를 한곳에서 모아보는 웹 대시보드입니다. `edutech_job`의 Node.js/Express 수집 구조와 Bento 스타일 UI를 활용해 만들었습니다.

> 공개 URL: https://edutech-letter.onrender.com

## 주요 기능

- Google News RSS와 지정 사이트 범위 검색을 통한 자료 자동 수집
- 최근 14일 이내 자료 수집
- 뉴스 / 연구·보고서 / 글로벌 인사이트 / 투자동향 / 정책·보도자료 / 교육 현장 구분
- 자료명, 발행기관, 발행일, 핵심 키워드와 원문 링크 제공
- 중복 자료 제거, 최신순 정렬, 통합 검색
- 30분 메모리 캐시 및 새로고침 버튼
- 매일 아침 알림 자동화를 위한 최근 24시간 헤드라인 API

## 실행 방법

```bash
npm install
npm start
```

브라우저에서 `http://localhost:3000`으로 접속합니다. 다른 포트를 사용하려면 `.env`에 `PORT=3001`처럼 설정하세요.

## 구조

```text
edutech_letter/
├── backend/
│   ├── server.js
│   └── services/
│       ├── newsService.js
│       └── newsService.test.js
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── package.json
└── README.md
```

## 데이터 출처

Google News RSS 검색 결과와 `site:도메인` 범위 검색을 활용합니다. 지정 사이트의 HTML을 직접 크롤링하지는 않습니다.

| 발행기관 | 지정 도메인 | 자료 유형 | 수집 방식 |
|---|---|---|---|
| KERIS 한국교육학술정보원 | `keris.or.kr` | 연구·보고서 | Google News RSS 사이트 범위 검색 |
| SPRi 소프트웨어정책연구소 | `spri.kr` | 연구·보고서 | Google News RSS 사이트 범위 검색 |
| HolonIQ | `holoniq.com` | 글로벌 인사이트 | Google News RSS 사이트 범위 검색 |
| 한국벤처캐피탈협회 | `kvca.or.kr` | 투자동향 | Google News RSS 사이트 범위 검색 |
| 교육부 보도자료실 | `moe.go.kr` | 정책·보도자료 | Google News RSS 사이트 범위 검색 |
| 대한민국 정책브리핑 | `korea.kr` | 정책·보도자료 | Google News RSS 사이트 범위 검색 |
| 에듀테크 데일리 | `edutechdaily.co.kr` | 전문 뉴스 | Google News RSS 사이트 범위 검색 |
| 대한민국교육신문 | `kedupress.com` | 교육 현장 | Google News RSS 사이트 범위 검색 |

Google News 일반 검색에서는 최근 에듀테크·AI 교육·디지털 교육 관련 뉴스도 함께 가져옵니다. 자료 저작권은 각 발행기관에 있으며, 이 서비스는 제목, 메타데이터와 원문 링크만 제공합니다.

`Ask! EdTech Insight`는 공개 아카이브 URL 확인 전까지 수집 및 UI에서 제외합니다.

## 아침 브리핑 자동화

`GET https://edutech-letter.onrender.com/api/digest?hours=24&limit=10`에서 최근 24시간 헤드라인과 발송용 메시지를 받을 수 있습니다.

n8n 연동 및 카카오톡·Telegram·Slack 발송 방식은 [`docs/daily-notification.md`](docs/daily-notification.md)를 참고하세요.

## Render 공개 배포

이 프로젝트는 저장소 루트의 `render.yaml` 설정으로 Render에 배포할 수 있습니다.

1. GitHub의 `sjeong722/EDUTECH` 저장소를 Render에 연결합니다.
2. Render에서 **New > Blueprint**를 선택합니다.
3. `EDUTECH` 저장소를 선택하고 Blueprint를 적용합니다.
4. 배포가 끝나면 Render가 제공하는 공개 URL로 누구나 접속할 수 있습니다.
