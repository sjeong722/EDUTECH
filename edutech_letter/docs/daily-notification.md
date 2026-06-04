# 매일 아침 알림 연동

## 아침 브리핑 API

```text
GET https://edutech-letter.onrender.com/api/digest
GET https://edutech-letter.onrender.com/api/digest?hours=24&limit=10
GET https://edutech-letter.onrender.com/api/digest-card.svg?hours=24&limit=5
```

최근 24시간 내 발행된 기사 제목, 발행기관, 원문 링크와 발송용 완성 문장을 반환합니다.

- n8n에서 사용할 메시지: `{{$json.data.message}}`
- 메일 제목: `{{$json.data.subject}}`
- HTML 메일 본문: `{{$json.data.html}}`
- 기사 배열: `{{$json.data.headlines}}`
- 새 기사 수: `{{$json.data.count}}`

## 사이트 링크 + 헤드라인 이미지 첨부

메일 본문은 사이트 주소만 보내고, 헤드라인 카드를 이미지로 첨부하려면 아래 URL을 사용합니다.

```text
https://edutech-letter.onrender.com/api/digest-card.svg?hours=24&limit=5
```

n8n 흐름:

1. **Schedule Trigger**: 매일 오전 8시, `Asia/Seoul`
2. **HTTP Request**: `GET https://edutech-letter.onrender.com/api/digest-card.svg?hours=24&limit=5`
   - Response Format: `File`
   - Binary Property: `digest_card`
3. **Gmail Send** 또는 메일 발송 노드
   - Subject: `[EduTech Letter] 오늘의 에듀테크 브리핑`
   - Body: `오늘의 EduTech Letter가 업데이트되었습니다.\nhttps://edutech-letter.onrender.com/`
   - Attachment Binary Property: `digest_card`

## 권장 n8n 흐름

1. **Schedule Trigger**: 매일 오전 8시, 시간대 `Asia/Seoul`
2. **HTTP Request**: `GET https://edutech-letter.onrender.com/api/digest?hours=24&limit=10`
3. **IF**: `{{$json.data.count}}`가 0보다 큰 경우만 발송
4. **메시지 발송 노드**: `{{$json.data.message}}` 전송

## Brevo 또는 SendGrid로 BCC 메일 발송

### Brevo HTTP Request 예시

1. **Schedule Trigger**: 매일 오전 8시, `Asia/Seoul`
2. **HTTP Request**: `GET https://edutech-letter.onrender.com/api/digest?hours=24&limit=10`
3. **IF**: `{{$json.data.count}} > 0`
4. **HTTP Request**: `POST https://api.brevo.com/v3/smtp/email`

Headers:

```text
x-api-key: <BREVO_API_KEY>
content-type: application/json
```

Body:

```json
{
  "sender": {
    "name": "EduTech Letter",
    "email": "verified-sender@example.com"
  },
  "to": [
    {
      "email": "owner@example.com",
      "name": "EduTech Letter"
    }
  ],
  "bcc": [
    { "email": "subscriber1@example.com" },
    { "email": "subscriber2@example.com" }
  ],
  "subject": "={{$json.data.subject}}",
  "htmlContent": "={{$json.data.html}}",
  "textContent": "={{$json.data.message}}"
}
```

`to`에는 본인 또는 대표 수신자 1명을 넣고, 구독자는 `bcc`에 넣으면 서로의 이메일 주소가 노출되지 않습니다.

### SendGrid HTTP Request 예시

`POST https://api.sendgrid.com/v3/mail/send`

Headers:

```text
Authorization: Bearer <SENDGRID_API_KEY>
content-type: application/json
```

Body:

```json
{
  "personalizations": [
    {
      "to": [{ "email": "owner@example.com" }],
      "bcc": [
        { "email": "subscriber1@example.com" },
        { "email": "subscriber2@example.com" }
      ]
    }
  ],
  "from": {
    "email": "verified-sender@example.com",
    "name": "EduTech Letter"
  },
  "subject": "={{$json.data.subject}}",
  "content": [
    {
      "type": "text/plain",
      "value": "={{$json.data.message}}"
    },
    {
      "type": "text/html",
      "value": "={{$json.data.html}}"
    }
  ]
}
```

## 발송 채널 선택

### 카카오톡 나와의 채팅

카카오 Developers의 메시지 API에서 `나에게 보내기`를 사용합니다. 개인 액세스 토큰과 갱신 처리가 필요합니다. 일반 단체 채팅방 ID로 자동 발송하는 공식 API는 제공되지 않습니다.

### 카카오 알림톡

Solapi 같은 알림톡 제공자를 n8n HTTP Request 또는 커뮤니티 노드로 연결할 수 있습니다. 카카오 비즈니스 채널과 사전 승인된 메시지 템플릿이 필요하며, 채팅방이 아니라 등록된 전화번호로 전송됩니다.

### Telegram·Slack·Discord

여러 명이 함께 보는 채팅방 자동 발송에는 이 방식이 가장 간단하고 안정적입니다. Bot 또는 Webhook을 채팅방에 추가한 뒤 n8n의 마지막 노드에서 `data.message`를 전송합니다.
