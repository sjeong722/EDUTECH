const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const { collectEdutechNews } = require('./services/newsService');
const { createDailyDigest } = require('./services/digestService');
const { createDigestCardSvg } = require('./services/cardService');

const app = express();
const PORT = process.env.PORT || 3000;
const CACHE_TTL_MS = 30 * 60 * 1000;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../frontend')));

let cachedNews = null;
let lastCollectedAt = null;

async function getNews(forceRefresh = false) {
  const cacheExpired = !lastCollectedAt || Date.now() - lastCollectedAt > CACHE_TTL_MS;

  if (!cachedNews || cacheExpired || forceRefresh) {
    console.log('[뉴스 수집] 최신 에듀테크 뉴스를 수집합니다.');
    cachedNews = await collectEdutechNews();
    lastCollectedAt = Date.now();
  } else {
    console.log('[캐시] 기존 뉴스 데이터를 반환합니다.');
  }
  return cachedNews;
}

app.get('/api/news', async (req, res) => {
  try {
    const news = await getNews(req.query.refresh === 'true');
    res.json({ success: true, data: news });
  } catch (error) {
    console.error('뉴스 수집 API 오류:', error.message || error);
    res.status(500).json({
      success: false,
      error: '뉴스 수집 중 오류가 발생했습니다.',
    });
  }
});

app.get('/api/digest', async (req, res) => {
  try {
    const news = await getNews(req.query.refresh === 'true');
    const digest = createDailyDigest(news.articles, {
      windowHours: req.query.hours,
      limit: req.query.limit,
    });
    res.json({ success: true, data: digest });
  } catch (error) {
    console.error('아침 브리핑 API 오류:', error.message || error);
    res.status(500).json({
      success: false,
      error: '아침 브리핑 생성 중 오류가 발생했습니다.',
    });
  }
});

app.get('/api/digest-card.svg', async (req, res) => {
  try {
    const news = await getNews(req.query.refresh === 'true');
    const digest = createDailyDigest(news.articles, {
      windowHours: req.query.hours,
      limit: req.query.limit || 5,
    });
    res.setHeader('Content-Type', 'image/svg+xml; charset=utf-8');
    res.setHeader('Cache-Control', 'public, max-age=300');
    res.send(createDigestCardSvg(digest));
  } catch (error) {
    console.error('브리핑 카드 API 오류:', error.message || error);
    res.status(500).send('브리핑 카드 생성 중 오류가 발생했습니다.');
  }
});

app.get('/api/health', (_req, res) => {
  res.json({ success: true, service: 'edutech-letter' });
});

app.listen(PORT, () => {
  console.log(`EduTech Letter: http://localhost:${PORT}`);
});
