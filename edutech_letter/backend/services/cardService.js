const fs = require('fs');
const path = require('path');

const CARD_WIDTH = 1080;
const MAX_TITLE_CHARS = 40;
const MAX_LINES = 2;
const FONT_PATH = path.join(__dirname, '../assets/fonts/NotoSansKR-Bold.ttf');
let cachedFontCss = null;

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

function getFontCss() {
  if (!cachedFontCss) {
    const fontBase64 = fs.readFileSync(FONT_PATH).toString('base64');
    cachedFontCss = `
      @font-face {
        font-family: 'NotoSansKREmbedded';
        src: url(data:font/truetype;charset=utf-8;base64,${fontBase64}) format('truetype');
        font-weight: 700 900;
      }
      text { font-family: 'NotoSansKREmbedded', sans-serif; }
    `;
  }
  return cachedFontCss;
}

function createDigestCardSvg(digest) {
  const headlines = digest.headlines.slice(0, 5);
  const rowHeight = 132;
  const cardHeight = 320 + Math.max(headlines.length, 1) * rowHeight;
  const dateLabel = formatKoreanDate(new Date(digest.generatedAt));

  const rows = headlines.length
    ? headlines.map((article, index) => {
      const y = 280 + index * rowHeight;
      const titleLines = wrapText(article.reportTitle);
      const titleTspans = titleLines.map((line, lineIndex) => (
        `<tspan x="168" dy="${lineIndex === 0 ? 0 : 34}">${escapeXml(line)}</tspan>`
      )).join('');
      const keywords = (article.coreKeywords || []).join(' · ') || article.type || '에듀테크';

      return `
        <g>
          <circle cx="96" cy="${y + 42}" r="28" fill="#e8f3ff"/>
          <text x="96" y="${y + 51}" text-anchor="middle" font-size="25" font-weight="800" fill="#3182f6">${index + 1}</text>
          <text x="168" y="${y + 28}" font-size="30" font-weight="800" fill="#191f28">${titleTspans}</text>
          <text x="168" y="${y + 96}" font-size="22" font-weight="700" fill="#6b7684">${escapeXml(article.institution)} · ${escapeXml(keywords)}</text>
          <line x1="72" y1="${y + 122}" x2="1008" y2="${y + 122}" stroke="#e5e8eb" stroke-width="2"/>
        </g>
      `;
    }).join('')
    : `
      <text x="72" y="330" font-size="32" font-weight="700" fill="#4e5968">최근 ${digest.windowHours}시간 내 새 헤드라인이 없습니다.</text>
    `;

  return `<svg width="${CARD_WIDTH}" height="${cardHeight}" viewBox="0 0 ${CARD_WIDTH} ${cardHeight}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>${getFontCss()}</style>
  </defs>
  <rect width="${CARD_WIDTH}" height="${cardHeight}" fill="#f7f8f9"/>
  <rect x="36" y="36" width="1008" height="${cardHeight - 72}" rx="36" fill="#ffffff"/>
  <rect x="36" y="36" width="1008" height="190" rx="36" fill="#3182f6"/>
  <text x="72" y="98" font-size="26" font-weight="800" fill="#d9eaff">EduTech Letter</text>
  <text x="72" y="154" font-size="46" font-weight="900" fill="#ffffff">${escapeXml(dateLabel)} 아침 브리핑</text>
  <text x="72" y="198" font-size="24" font-weight="700" fill="#d9eaff">최근 ${digest.windowHours}시간 헤드라인 ${digest.count}건 · 전체 보기 edutech-letter.onrender.com</text>
  ${rows}
  <text x="72" y="${cardHeight - 44}" font-size="21" font-weight="700" fill="#8b95a1">https://edutech-letter.onrender.com</text>
</svg>`;
}

module.exports = {
  createDigestCardSvg,
  escapeXml,
  getFontCss,
  wrapText,
};
