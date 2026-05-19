# 🦦 취준하는 수달이 — AI 쇼츠 영상 자동화 워크플로우

> Claude + Gemini + Kling + n8n 기반 캐릭터 IP 콘텐츠 자동 제작 시스템

---

## 📌 프로젝트 개요

**"취준하는 수달이"** 캐릭터 IP를 활용한 쇼츠 영상 콘텐츠를 AI로 반자동화하여,  
매일 일관된 시리즈 콘텐츠를 최소한의 수동 작업으로 제작하는 워크플로우입니다.

| 항목 | 내용 |
|---|---|
| 캐릭터 | 취업 준비 중인 귀여운 3D 수달 |
| 타겟 | 취준생, 사회초년생, 직장인 |
| 스타일 | Pixar풍 3D CGI, 따뜻한 조명, 공감 스토리텔링 |
| 업로드 플랫폼 | YouTube Shorts |

---

## 🗂️ 버전 히스토리

### v1 — 스크립트 + 이미지 자동화
- Claude API로 스크립트 + 씬별 이미지 프롬프트 + SRT 자막 + BGM 키워드 생성
- Gemini API로 씬별 9:16 이미지 자동 생성
- Google Drive에 이미지, 자막, 스크립트 자동 저장
- Telegram으로 완료 알림
- **영상 생성(Genspark R2V), 편집(CapCut), 업로드는 수동**

### v2 — 영상 생성까지 자동화 (현재)
- v1 기능 전부 포함
- **Kling API로 이미지 → 5초 영상 클립 자동 생성**
- **Loop Over Items으로 씬 5개 순차 처리**
- 완성된 클립 5개를 Google Drive `5s 영상` 폴더에 자동 저장
- **CapCut 편집, 업로드만 수동**

---

## 🔧 기술 스택

| 분류 | 도구 | 용도 |
|---|---|---|
| 자동화 플랫폼 | n8n Cloud | 전체 워크플로우 오케스트레이션 |
| 스크립트 생성 | Claude API (claude-sonnet-4-5) | 씬별 스크립트, 이미지 프롬프트, SRT 자막, BGM 키워드 |
| 이미지 생성 | Gemini API (gemini-3.1-flash-image-preview) | 9:16 세로형 씬 이미지 생성 |
| 영상 생성 | Kling API (kling-v2-6) | 이미지 → 5초 영상 클립 자동 변환 |
| 파일 저장 | Google Drive | 이미지, SRT 자막, 스크립트, 영상 클립 중앙 관리 |
| 알림 | Telegram Bot (@otter_shorts_bot) | 완료 알림 + 파일 정보 전송 |
| 편집 | CapCut | 클립 연결, 자막 임포트, BGM 추가 (수동) |
| 음악 | Suno AI | BGM 사전 제작 후 Drive 업로드 |

---

## 🔄 워크플로우 전체 흐름 (v2)

```
[자동] ① Schedule Trigger (매일 오전 9시 Cron)
         ↓
[자동] ② Claude API → 스크립트 + 씬별 이미지 프롬프트 + SRT 자막 + BGM 키워드 (JSON)
         ↓
[자동] ③ Code 노드 → Claude 응답 파싱 → 씬별 개별 아이템 분리 (4~5개)
         ↓
[자동] ④ Google Drive → 스크립트 .txt 파일 저장
         ↓
[자동] ⑤ Loop Over Items → 씬별 반복 시작
         ↓
[자동] ⑥ Gemini API → 씬별 9:16 이미지 생성 (씬당 약 30~40초)
         ↓
[자동] ⑦ Code 노드 → base64 이미지 추출 → binary 변환
         ↓
[자동] ⑧ Google Drive → 씬별 이미지 저장 (scene_N_날짜.png)
         ↓
[자동] ⑨ Code 노드 → JWT 토큰 생성 (Kling 인증)
         ↓
[자동] ⑩ Kling API → 이미지 → 5초 영상 클립 생성 요청
         ↓
[자동] ⑪ Wait 90초 → 영상 생성 대기
         ↓
[자동] ⑫ Kling API → 생성 결과 조회 + 영상 URL 추출
         ↓
[자동] ⑬ HTTP Request → 영상 다운로드
         ↓
[자동] ⑭ Google Drive → 클립 저장 (clip_N_날짜.mp4) → Loop 반복
         ↓ (모든 씬 완료 후)
[자동] ⑮ Google Drive → SRT 자막 파일 저장
         ↓
[자동] ⑯ Code 노드 → BGM 분위기 키워드 기반 파일 자동 매칭
         ↓
[자동] ⑰ Telegram Bot → 완료 알림 전송

─────────────────────────────────────────────
[수동] ⑱ CapCut → 클립 5개 연결 + SRT 자막 임포트 + BGM 추가
[수동] ⑲ 플랫폼 업로드
```

---

## ⚡ 자동화 vs 수동 구간

| 구분 | v1 | v2 |
|---|---|---|
| 자동 | 스크립트, 이미지, Drive 저장, 알림 | 스크립트, 이미지, **영상 클립**, Drive 저장, 알림 |
| 수동 | Genspark 영상 생성, CapCut 편집, 업로드 | CapCut 편집, 업로드 |
| 자동화 소요 시간 | 약 3~5분 | 약 10~12분 |
| 수동 소요 시간 | 약 30~40분 | 약 20~30분 |

---

## 📁 Google Drive 폴더 구조

```
edu_otter_image/
├── scene_1_2026-05-19.png
├── scene_2_2026-05-19.png
├── scene_3_2026-05-19.png
├── scene_4_2026-05-19.png
├── scene_5_2026-05-19.png
├── 2026-05-19_script.txt
├── 2026-05-19_subtitle.srt
├── 수달_bgm_1.mp3
├── 수달_bgm_2.mp3
└── 5s 영상/
    ├── clip_1_2026-05-19.mp4
    ├── clip_2_2026-05-19.mp4
    ├── clip_3_2026-05-19.mp4
    ├── clip_4_2026-05-19.mp4
    └── clip_5_2026-05-19.mp4
```

---

## 🤖 Claude 프롬프트 설계

한 번의 API 호출로 생성되는 데이터:
- 영상 제목 및 컨셉
- 씬별 나레이션 텍스트
- 씬별 Gemini 이미지 생성용 영어 프롬프트
- 씬별 자막 텍스트
- SRT 자막 파일 전체 내용 (타임코드 포함)
- BGM 분위기 키워드

---

## 🎨 이미지 일관성 전략

Gemini API 레퍼런스 이미지 전달 방식의 제한으로 프롬프트 고정 방식으로 캐릭터 일관성을 확보합니다.

**고정 캐릭터 묘사 (모든 씬 공통 적용):**
```
round chubby face, very large dark glossy eyes like black marbles,
short dense brown fur, cream/white colored cheeks and chin area,
tiny dark round nose, Pixar Disney 3D CGI animation style,
subsurface scattering on fur, warm golden soft lighting from upper left,
shallow depth of field background
```

---

## 🎬 Kling API 설정

| 항목 | 값 |
|---|---|
| 모델 | kling-v2-6 |
| 모드 | std |
| 영상 길이 | 5초 |
| 사운드 | off |
| 인증 | JWT (Access Key + Secret Key) |
| 크레딧 소모 | 약 4 units/클립 (5초 std 기준) |

**JWT 토큰:** Access Key + Secret Key로 매 실행 시 자동 생성 (유효시간 30분)

---

## 📱 텔레그램 알림 예시

```
🦦 수달이 콘텐츠 준비 완료!

📅 날짜: 2026-05-19
🎬 제목: 면접 대기실에서 생긴 일
💡 컨셉: 면접 대기 중 긴장한 수달이의 공감 스토리
🎵 BGM 분위기: lofi, 잔잔한
🎶 선택된 BGM: 수달_bgm_1.mp3

📁 구글 드라이브 확인
→ 이미지 5장 저장 완료
→ 5초 영상 클립 5개 저장 완료
→ 자막 파일(.srt) 저장 완료

✅ 다음 단계
1. Drive 5s 영상 폴더에서 클립 확인
2. CapCut에서 클립 연결 + .srt 자막 임포트
3. BGM 추가 후 업로드
```

---

## 🚧 현재 한계 및 개선 계획

| 항목 | 현재 | 개선 계획 |
|---|---|---|
| 이미지 일관성 | 프롬프트 고정 방식 (80~90% 유사도) | Self-hosted n8n 전환 후 레퍼런스 이미지 직접 전달 |
| 업로드 | 수동 업로드 | YouTube API 연동 자동 업로드 |
| BGM | 사전 제작 2종 | Suno BGM 풀 확장 (분위기별 5~10종) |
| Kling 크레딧 | 월 30편 기준 약 $63 | 채널 수익화 후 확장 |

---

## 💰 운영 비용 (월 예상, 영상 30편 기준)

| 항목 | 비용 |
|---|---|
| n8n Cloud | $20/월 |
| Claude API | 약 $1~2 |
| Gemini API | 약 $6.75 (이미지 150장) |
| Kling API | 약 $63 (클립 150개 std 모드) |
| **합계** | **약 $91/월** |

---

## 📋 n8n 워크플로우 노드 구성 (v2)

| 노드명 | 타입 | 역할 |
|---|---|---|
| 매일 오전 9시 트리거 | Schedule Trigger | Cron 실행 (0 9 * * *) |
| Claude - 스크립트 생성 | HTTP Request | Anthropic API 호출 |
| 스크립트 파싱 + 씬 분리 | Code (JS) | JSON 파싱 및 씬 분리 |
| 스크립트 txt 생성 | Google Drive | 스크립트 텍스트 파일 저장 |
| Loop Over Items | Loop | 씬별 반복 처리 |
| Gemini - 이미지 생성 | HTTP Request | Gemini API 호출 (timeout: 120초) |
| 이미지 추출 | Code (JS) | base64 → binary 변환 |
| Google Drive - 이미지 저장 | Google Drive | 씬 이미지 업로드 |
| JWT 토큰생성 | Code (JS) | Kling 인증용 JWT 토큰 생성 |
| Kling - 영상 생성 요청 | HTTP Request | Kling API 영상 생성 요청 |
| Wait | Wait | 90초 대기 (영상 생성 시간) |
| Kling - 결과 조회 | HTTP Request | 생성 완료 여부 확인 + URL 획득 |
| 영상 URL 추출 | Code (JS) | 결과에서 영상 URL 추출 |
| 영상 다운로드 | HTTP Request | 영상 파일 다운로드 |
| 클립 저장 | Google Drive | 5s 영상 폴더에 클립 업로드 |
| Google Drive - 자막 저장 | Google Drive | SRT 파일 생성 |
| BGM 매칭 | Code (JS) | 키워드 기반 BGM 선택 |
| Telegram - 완료 알림 | Telegram | 완료 메시지 전송 |
