const test = require('node:test');
const assert = require('node:assert/strict');

const { createDigestCardSvg, escapeXml, getFontData, wrapText } = require('./cardService');

test('XML 특수문자를 이스케이프한다', () => {
  assert.equal(escapeXml('AI & <교육>'), 'AI &amp; &lt;교육&gt;');
});

test('긴 제목을 여러 줄로 나눈다', () => {
  const lines = wrapText('AI 교육을 위한 매우 긴 제목 문장을 카드 안에서 보기 좋게 줄바꿈한다', 14, 2);
  assert.equal(lines.length, 2);
});

test('브리핑 카드 SVG를 생성한다', async () => {
  const svg = await createDigestCardSvg({
    generatedAt: '2026-06-05T00:00:00.000Z',
    windowHours: 24,
    count: 1,
    headlines: [
      {
        reportTitle: 'AI 교육 헤드라인',
        institution: '테스트 기관',
        type: '뉴스',
        coreKeywords: ['AI 교육'],
      },
    ],
  });

  assert.match(svg, /^<svg/);
  assert.match(svg, /<path/);
  assert.match(svg, /#3182f6/);
});

test('한글 렌더링용 내장 폰트 CSS를 생성한다', () => {
  assert.ok(getFontData().length > 1000);
});
