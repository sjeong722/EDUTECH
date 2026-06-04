const test = require('node:test');
const assert = require('node:assert/strict');

const { createDailyDigest } = require('./digestService');

test('최근 시간 범위에 해당하는 기사만 브리핑에 포함한다', () => {
  const now = '2026-06-05T00:00:00.000Z';
  const digest = createDailyDigest([
    { reportTitle: '새 기사', institution: '테스트', link: 'https://example.com/new', publishedAt: '2026-06-04T12:00:00.000Z' },
    { reportTitle: '오래된 기사', institution: '테스트', link: 'https://example.com/old', publishedAt: '2026-06-03T12:00:00.000Z' },
  ], { now, windowHours: 24 });

  assert.equal(digest.count, 1);
  assert.match(digest.message, /새 기사/);
  assert.doesNotMatch(digest.message, /오래된 기사/);
});

test('기사 수 제한을 적용한다', () => {
  const articles = Array.from({ length: 5 }, (_, index) => ({
    reportTitle: `기사 ${index}`,
    institution: '테스트',
    link: `https://example.com/${index}`,
    publishedAt: '2026-06-04T12:00:00.000Z',
  }));
  const digest = createDailyDigest(articles, { now: '2026-06-05T00:00:00.000Z', limit: 2 });
  assert.equal(digest.count, 2);
});
