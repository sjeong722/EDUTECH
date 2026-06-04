const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const { collectEdutechNews } = require('./services/newsService');

const app = express();
const PORT = process.env.PORT || 3000;
const CACHE_TTL_MS = 30 * 60 * 1000;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../frontend')));

let cachedNews = null;
let lastCollectedAt = null;

app.get('/api/news', async (req, res) => {
  try {
    const forceRefresh = req.query.refresh === 'true';
    const cacheExpired = !lastCollectedAt || Date.now() - lastCollectedAt > CACHE_TTL_MS;

    if (!cachedNews || cacheExpired || forceRefresh) {
      console.log('[뉴스 수집] 최신 에듀테크 뉴스를 수집합니다.');
      cachedNews = await collectEdutechNews();
      lastCollectedAt = Date.now();
    } else {
      console.log('[캐시] 기존 뉴스 데이터를 반환합니다.');
    }

    res.json({ success: true, data: cachedNews });
  } catch (error) {
    console.error('뉴스 수집 API 오류:', error.message || error);
    res.status(500).json({
      success: false,
      error: '뉴스 수집 중 오류가 발생했습니다.',
    });
  }
});

app.get('/api/health', (_req, res) => {
  res.json({ success: true, service: 'edutech-letter' });
});

app.listen(PORT, () => {
  console.log(`EduTech Letter: http://localhost:${PORT}`);
});
