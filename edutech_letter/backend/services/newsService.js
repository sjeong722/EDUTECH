const crypto = require('crypto');
const COLLECTION_DAYS = 14;

// Ask! EdTech Insight는 공개 아카이브 URL 확인 전까지 수집 및 UI에서 제외합니다.
const SOURCES = [
  { institution: 'Google News', domain: null, type: '뉴스', query: '에듀테크 OR "AI 교육" OR "디지털 교육"', terms: ['에듀테크', 'ai 교육', '인공지능 교육', '디지털 교육'] },
  { institution: 'KERIS', domain: 'keris.or.kr', type: '연구·보고서', query: '에듀테크 OR 디지털교육 OR AI교육', terms: ['에듀테크', '디지털', 'ai', '인공지능', '교육정보화'] },
  { institution: 'SPRi', domain: 'spri.kr', type: '연구·보고서', query: 'AI 교육 OR 인재양성 OR 에듀테크', terms: ['교육', '인재', '역량', '리터러시', '에듀테크'] },
  { institution: 'HolonIQ', domain: 'holoniq.com', type: '글로벌 인사이트', query: 'EdTech OR education trends OR education investment', terms: ['edtech', 'education', 'learning', 'skills', 'student'] },
  { institution: '한국벤처캐피탈협회', domain: 'kvca.or.kr', type: '투자동향', query: '에듀테크 OR 교육 투자', terms: ['에듀테크', '교육'] },
  { institution: '교육부', domain: 'moe.go.kr', type: '정책·보도자료', query: '에듀테크 OR AI교육 OR 디지털교육', terms: ['에듀테크', 'ai', '인공지능', '디지털'] },
  { institution: '대한민국 정책브리핑', domain: 'korea.kr', type: '정책·보도자료', query: '교육부 에듀테크 OR 교육부 AI교육 OR 교육부 디지털교육', terms: ['교육', '학교', '학습', '교사', '학생', '에듀테크'] },
  { institution: '에듀테크 데일리', domain: 'edutechdaily.co.kr', type: '전문 뉴스', query: '에듀테크 OR AI교육', terms: ['에듀테크', '교육', '학습'] },
  { institution: '대한민국교육신문', domain: 'kedupress.com', type: '교육 현장', query: '에듀테크 OR AI교육 OR 디지털교육', terms: ['에듀테크', 'ai', '인공지능', '디지털'] },
];

const KEYWORD_RULES = [
  ['생성형 AI', ['생성형', 'chatgpt', '챗gpt', 'llm']],
  ['AI 교육', ['ai', '인공지능', '인공 지능']],
  ['디지털 교육', ['디지털', '에듀테크', 'edtech']],
  ['교수학습', ['교수', '학습', '수업', '교실', '교사']],
  ['교육정책', ['교육부', '교육청', '정책', '공교육', '학교']],
  ['투자·시장', ['투자', '펀드', '벤처', '시장', '매출', 'funding']],
  ['인재·역량', ['인재', '역량', '리터러시', 'skills', 'workforce']],
  ['플랫폼·LMS', ['플랫폼', 'lms', '서비스', '솔루션']],
  ['글로벌', ['global', '글로벌', '해외']],
];

function extractKeywords(title, source) {
  const text = title.toLowerCase();
  const matches = KEYWORD_RULES
    .filter(([, terms]) => terms.some((term) => text.includes(term)))
    .map(([name]) => name);
  return [...new Set(matches)].slice(0, 3);
}

function isRelevant(title, source) {
  const text = title.toLowerCase();
  return source.terms.some((term) => text.includes(term));
}

function normalizeTitle(title) {
  return title.replace(/\s+-\s+[^-]+$/, '').replace(/\s+/g, ' ').trim();
}

function makeId(link, title) {
  return crypto.createHash('sha1').update(`${link}|${title}`).digest('hex').slice(0, 12);
}

async function fetchSource(source) {
  const axios = require('axios');
  const cheerio = require('cheerio');
  const siteFilter = source.domain ? ` site:${source.domain}` : '';
  const query = `${source.query}${siteFilter} when:${COLLECTION_DAYS}d`;
  const url = `https://news.google.com/rss/search?q=${encodeURIComponent(query)}&hl=ko&gl=KR&ceid=KR:ko`;
  const { data } = await axios.get(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (compatible; EduTechLetter/1.0)',
      Accept: 'application/rss+xml, application/xml, text/xml',
    },
    timeout: 12000,
  });

  const $ = cheerio.load(data, { xmlMode: true });
  const articles = [];
  $('item').each((_index, item) => {
    const title = normalizeTitle($(item).find('title').first().text().trim());
    const link = $(item).find('link').first().text().trim();
    const rssSource = $(item).find('source').first().text().trim();
    const publishedAt = $(item).find('pubDate').first().text().trim();
    if (!title || !link || !publishedAt || !isRelevant(title, source)) return;

    const coreKeywords = extractKeywords(title, source);
    articles.push({
      id: makeId(link, title),
      reportTitle: title,
      institution: source.institution === 'Google News' ? (rssSource || 'Google News') : source.institution,
      type: source.type,
      coreKeywords,
      link,
      publishedAt: new Date(publishedAt).toISOString(),
    });
  });
  return articles;
}

function deduplicate(articles) {
  const seen = new Set();
  return articles.filter((article) => {
    const key = article.reportTitle.toLowerCase().replace(/[^a-z0-9가-힣]/g, '');
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function balanceByInstitution(articles, maxPerInstitution = 24) {
  const counts = new Map();
  return articles.filter((article) => {
    const count = counts.get(article.institution) || 0;
    if (count >= maxPerInstitution) return false;
    counts.set(article.institution, count + 1);
    return true;
  });
}

async function collectEdutechNews() {
  const results = await Promise.allSettled(SOURCES.map(fetchSource));
  results.filter((result) => result.status === 'rejected').forEach((result) => {
    console.error('[수집 실패]', result.reason?.message || result.reason);
  });

  const articles = balanceByInstitution(
    deduplicate(results.flatMap((result) => (result.status === 'fulfilled' ? result.value : [])))
      .sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt)),
  )
    .slice(0, 150);

  const typeCounts = Object.fromEntries(
    [...new Set(SOURCES.map((source) => source.type))].map((type) => [
      type,
      articles.filter((article) => article.type === type).length,
    ]),
  );

  return {
    collectedAt: new Date().toISOString(),
    collectionDays: COLLECTION_DAYS,
    totalCount: articles.length,
    sourceCount: new Set(articles.map((article) => article.institution)).size,
    typeCounts,
    sources: SOURCES.map(({ institution, type }) => ({ institution, type })),
    articles,
  };
}

module.exports = {
  SOURCES,
  balanceByInstitution,
  collectEdutechNews,
  deduplicate,
  extractKeywords,
  isRelevant,
};
