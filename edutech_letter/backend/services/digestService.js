const DEFAULT_WINDOW_HOURS = 24;
const DEFAULT_LIMIT = 10;
const MAX_LIMIT = 20;
const SITE_URL = 'https://edutech-letter.onrender.com';

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

  const subject = `[EduTech Letter] ${dateLabel} 에듀테크 헤드라인`;

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
      `전체 자료 보기: ${SITE_URL}`,
    ].join('\n'),
    subject,
    html: createDigestHtml({ dateLabel, windowHours, headlines }),
  };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function createDigestHtml({ dateLabel, windowHours, headlines }) {
  const headlineHtml = headlines.length
    ? headlines.map((article, index) => `
      <tr>
        <td style="padding:18px 0;border-bottom:1px solid #e5e8eb;">
          <p style="margin:0 0 6px;color:#8b95a1;font-size:12px;font-weight:700;">${index + 1} · ${escapeHtml(article.institution)}</p>
          <a href="${escapeHtml(article.link)}" style="color:#191f28;text-decoration:none;font-size:17px;font-weight:700;line-height:1.55;">${escapeHtml(article.reportTitle)}</a>
          <p style="margin:8px 0 0;color:#4e5968;font-size:13px;">${escapeHtml((article.coreKeywords || []).join(' · ') || article.type || '에듀테크')}</p>
        </td>
      </tr>
    `).join('')
    : `
      <tr>
        <td style="padding:22px 0;color:#4e5968;font-size:15px;">최근 ${windowHours}시간 내 새로 발행된 기사가 없습니다.</td>
      </tr>
    `;

  return `<!doctype html>
<html lang="ko">
<body style="margin:0;padding:0;background:#f7f8f9;font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',Arial,sans-serif;color:#191f28;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f7f8f9;padding:28px 14px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#ffffff;border-radius:20px;overflow:hidden;">
          <tr>
            <td style="padding:30px 28px;background:#3182f6;color:#ffffff;">
              <p style="margin:0 0 10px;font-size:13px;font-weight:700;opacity:.86;">EduTech Letter</p>
              <h1 style="margin:0;font-size:26px;line-height:1.35;letter-spacing:-.04em;">${escapeHtml(dateLabel)}<br>에듀테크 아침 브리핑</h1>
              <p style="margin:16px 0 0;font-size:14px;opacity:.82;">최근 ${windowHours}시간 헤드라인 ${headlines.length}건</p>
            </td>
          </tr>
          <tr>
            <td style="padding:6px 28px 0;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                ${headlineHtml}
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:26px 28px 30px;">
              <a href="${SITE_URL}" style="display:inline-block;background:#3182f6;color:#ffffff;text-decoration:none;border-radius:12px;padding:13px 18px;font-size:14px;font-weight:700;">전체 자료 보기</a>
              <p style="margin:18px 0 0;color:#8b95a1;font-size:12px;line-height:1.6;">이 메일은 EduTech Letter 브리핑 API를 통해 자동 생성되었습니다.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
}

module.exports = {
  createDailyDigest,
  createDigestHtml,
};
