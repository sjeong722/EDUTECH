const DEFAULT_WINDOW_HOURS = 24;
const DEFAULT_LIMIT = 10;
const MAX_LIMIT = 20;

function clampNumber(value, fallback, min, max) {
  const number = Number.parseInt(value, 10);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(Math.max(number, min), max);
}

function createDailyDigest(articles, options = {}) {
  const windowHours = clampNumber(options.windowHours, DEFAULT_WINDOW_HOURS, 1, 168);
  const limit = clampNumber(options.limit, DEFAULT_LIMIT, 1, MAX_LIMIT);
  const now = options.now ? new Date(options.now) : new Date();
  const since = new Date(now.getTime() - windowHours * 60 * 60 * 1000);

  const headlines = articles
    .filter((article) => new Date(article.publishedAt) >= since)
    .sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt))
    .slice(0, limit);

  const dateLabel = new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(now);

  const lines = headlines.length
    ? headlines.flatMap((article, index) => [
      `${index + 1}. ${article.reportTitle}`,
      `   ${article.institution} | ${article.link}`,
    ])
    : [`최근 ${windowHours}시간 내 새로 발행된 기사가 없습니다.`];

  return {
    generatedAt: now.toISOString(),
    since: since.toISOString(),
    windowHours,
    count: headlines.length,
    headlines,
    message: [
      `[EduTech Letter] ${dateLabel} 아침 브리핑`,
      `최근 ${windowHours}시간 헤드라인 ${headlines.length}건`,
      '',
      ...lines,
      '',
      '전체 자료 보기: https://edutech-letter.onrender.com',
    ].join('\n'),
  };
}

module.exports = {
  createDailyDigest,
};
