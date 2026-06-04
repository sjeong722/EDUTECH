const fs = require('fs');
const path = require('path');

const satori = require('satori').default;

const CARD_WIDTH = 1080;
const MAX_TITLE_CHARS = 42;
const MAX_LINES = 2;
const FONT_PATH = path.join(__dirname, '../assets/fonts/NotoSansKR-Bold.ttf');
let cachedFont = null;

function getFontData() {
  if (!cachedFont) cachedFont = fs.readFileSync(FONT_PATH);
  return cachedFont;
}

function escapeXml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;');
}

function wrapText(text, maxChars = MAX_TITLE_CHARS, maxLines = MAX_LINES) {
  const words = String(text).split(/\s+/).filter(Boolean);
  const lines = [];
  let current = '';

  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > maxChars && current) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
    if (lines.length === maxLines) break;
  }
  if (lines.length < maxLines && current) lines.push(current);
  if (lines.length === maxLines && words.join(' ').length > lines.join(' ').length) {
    lines[maxLines - 1] = `${lines[maxLines - 1].replace(/…$/, '')}…`;
  }
  return lines;
}

function formatKoreanDate(date) {
  return new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(date);
}

function text(value, style = {}) {
  return { type: 'div', props: { style, children: String(value) } };
}

function createRow(article, index) {
  const keywords = (article.coreKeywords || []).join(' · ') || article.type || '에듀테크';
  return {
    type: 'div',
    props: {
      style: {
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'flex-start',
        width: '100%',
        padding: '24px 0',
        borderBottom: '2px solid #e5e8eb',
      },
      children: [
        {
          type: 'div',
          props: {
            style: {
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 56,
              height: 56,
              borderRadius: 28,
              backgroundColor: '#e8f3ff',
              color: '#3182f6',
              fontSize: 25,
              fontWeight: 700,
              flexShrink: 0,
              marginTop: 4,
            },
            children: String(index + 1),
          },
        },
        {
          type: 'div',
          props: {
            style: {
              display: 'flex',
              flexDirection: 'column',
              marginLeft: 40,
              flex: 1,
            },
            children: [
              text(wrapText(article.reportTitle).join('\n'), {
                color: '#191f28',
                fontSize: 30,
                lineHeight: 1.35,
                fontWeight: 700,
                whiteSpace: 'pre-wrap',
              }),
              text(`${article.institution} · ${keywords}`, {
                marginTop: 18,
                color: '#6b7684',
                fontSize: 22,
                lineHeight: 1.25,
                fontWeight: 700,
              }),
            ],
          },
        },
      ],
    },
  };
}

async function createDigestCardSvg(digest) {
  const headlines = digest.headlines.slice(0, 5);
  const rowHeight = 150;
  const cardHeight = 250 + Math.max(headlines.length, 1) * rowHeight;
  const dateLabel = formatKoreanDate(new Date(digest.generatedAt));

  const tree = {
    type: 'div',
    props: {
      style: {
        display: 'flex',
        width: CARD_WIDTH,
        height: cardHeight,
        padding: 36,
        backgroundColor: '#f7f8f9',
        fontFamily: 'NotoSansKR',
      },
      children: {
        type: 'div',
        props: {
          style: {
            display: 'flex',
            flexDirection: 'column',
            width: '100%',
            height: '100%',
            backgroundColor: '#ffffff',
            borderRadius: 36,
            overflow: 'hidden',
          },
          children: [
            {
              type: 'div',
              props: {
                style: {
                  display: 'flex',
                  flexDirection: 'column',
                  padding: '34px 36px 28px',
                  height: 190,
                  backgroundColor: '#3182f6',
                },
                children: [
                  text('EduTech Letter', { color: '#d9eaff', fontSize: 26, lineHeight: 1.2, fontWeight: 700 }),
                  text(`${dateLabel} 아침 브리핑`, {
                    marginTop: 14,
                    color: '#ffffff',
                    fontSize: 46,
                    lineHeight: 1.15,
                    fontWeight: 700,
                  }),
                  text(`최근 ${digest.windowHours}시간 헤드라인 ${digest.count}건 · 전체 보기 edutech-letter.onrender.com`, {
                    marginTop: 14,
                    color: '#d9eaff',
                    fontSize: 24,
                    lineHeight: 1.25,
                    fontWeight: 700,
                  }),
                ],
              },
            },
            {
              type: 'div',
              props: {
                style: { display: 'flex', flexDirection: 'column', padding: '36px 36px 0', flex: 1 },
                children: headlines.length
                  ? headlines.map(createRow)
                  : [text(`최근 ${digest.windowHours}시간 내 새 헤드라인이 없습니다.`, {
                    color: '#4e5968',
                    fontSize: 32,
                    lineHeight: 1.4,
                    fontWeight: 700,
                  })],
              },
            },
          ],
        },
      },
    },
  };

  return satori(tree, {
    width: CARD_WIDTH,
    height: cardHeight,
    fonts: [{ name: 'NotoSansKR', data: getFontData(), weight: 700, style: 'normal' }],
  });
}

module.exports = {
  createDigestCardSvg,
  escapeXml,
  getFontData,
  wrapText,
};
