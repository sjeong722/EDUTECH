const test = require('node:test');
const assert = require('node:assert/strict');

const { balanceByInstitution, deduplicate, extractKeywords, isRelevant } = require('./newsService');

test('자료명에서 핵심 키워드를 추출한다', () => {
  const keywords = extractKeywords('생성형 AI 교육 스타트업 투자 동향');
  assert.deepEqual(keywords, ['생성형 AI', 'AI 교육', '투자·시장']);
});

test('같은 자료명의 항목을 중복 제거한다', () => {
  const articles = [
    { reportTitle: 'AI 교육의 미래', link: 'https://a.example' },
    { reportTitle: 'AI 교육의 미래', link: 'https://b.example' },
    { reportTitle: '새로운 LMS 출시', link: 'https://c.example' },
  ];
  assert.equal(deduplicate(articles).length, 2);
});

test('특정 발행기관의 자료 쏠림을 제한한다', () => {
  const articles = Array.from({ length: 5 }, (_, index) => ({
    institution: '교육부',
    reportTitle: `자료 ${index}`,
  }));
  assert.equal(balanceByInstitution(articles, 2).length, 2);
});

test('자료 제목이 지정 기관의 관심 주제와 관련 있는지 확인한다', () => {
  const source = { terms: ['교육', '학교'] };
  assert.equal(isRelevant('AI 교육 정책 발표', source), true);
  assert.equal(isRelevant('위성 산업 정책 발표', source), false);
});
