const state = { articles: [], type: '전체', query: '' };

const elements = {
  date: document.getElementById('current-date'),
  totalCount: document.getElementById('total-count'),
  sourceCount: document.getElementById('source-count'),
  sources: document.getElementById('source-list'),
  filters: document.getElementById('filters'),
  list: document.getElementById('research-list'),
  loading: document.getElementById('loading-state'),
  empty: document.getElementById('empty-state'),
  search: document.getElementById('search-input'),
  refresh: document.getElementById('refresh-button'),
};

elements.date.textContent = new Intl.DateTimeFormat('ko-KR', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
}).format(new Date());

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value;
  return div.innerHTML;
}

function formatDate(value) {
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date(value));
}

function renderFilters(typeCounts) {
  const types = ['전체', ...Object.keys(typeCounts)];
  elements.filters.innerHTML = types.map((type) => `
    <button class="filter ${type === state.type ? 'active' : ''}" data-type="${escapeHtml(type)}">
      ${escapeHtml(type)} <span>${type === '전체' ? state.articles.length : typeCounts[type]}</span>
    </button>
  `).join('');
  elements.filters.querySelectorAll('.filter').forEach((button) => {
    button.addEventListener('click', () => {
      state.type = button.dataset.type;
      renderFilters(typeCounts);
      renderArticles();
    });
  });
}

function renderArticles() {
  const query = state.query.toLowerCase();
  const filtered = state.articles.filter((article) => {
    const matchesType = state.type === '전체' || article.type === state.type;
    const haystack = `${article.reportTitle} ${article.institution} ${article.coreKeywords.join(' ')}`.toLowerCase();
    return matchesType && haystack.includes(query);
  });

  elements.loading.hidden = true;
  elements.list.hidden = filtered.length === 0;
  elements.empty.hidden = filtered.length !== 0;
  elements.list.innerHTML = filtered.map((article) => `
    <article class="research-card">
      <div class="card-main">
        <div class="card-meta">
          <span class="type-badge">${escapeHtml(article.type)}</span>
          <span>발행일 ${formatDate(article.publishedAt)}</span>
        </div>
        <h3>${escapeHtml(article.reportTitle)}</h3>
        <div class="keyword-list">
          ${(article.coreKeywords.length ? article.coreKeywords : ['교육 트렌드'])
            .map((keyword) => `<span>${escapeHtml(keyword)}</span>`).join('')}
        </div>
      </div>
      <dl class="card-details">
        <div><dt>발행기관</dt><dd>${escapeHtml(article.institution)}</dd></div>
      </dl>
      <a class="article-link" href="${article.link}" target="_blank" rel="noopener noreferrer" aria-label="${escapeHtml(article.reportTitle)} 원문 보기">원문 보기 <span>↗</span></a>
    </article>
  `).join('');
}

async function loadNews(forceRefresh = false) {
  elements.loading.hidden = false;
  elements.list.hidden = true;
  elements.empty.hidden = true;
  elements.refresh.disabled = true;
  try {
    const response = await fetch(forceRefresh ? '/api/news?refresh=true' : '/api/news');
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error || '자료를 불러오지 못했습니다.');
    const data = result.data;
    state.articles = data.articles;
    elements.totalCount.textContent = data.totalCount;
    elements.sourceCount.textContent = data.sourceCount;
    elements.sources.innerHTML = data.sources
      .filter((source) => source.institution !== 'Google News')
      .map((source) => `<span>${escapeHtml(source.institution)}</span>`).join('');
    renderFilters(data.typeCounts);
    renderArticles();
  } catch (error) {
    console.error(error);
    elements.loading.hidden = true;
    elements.empty.hidden = false;
    elements.empty.querySelector('p').textContent = '자료를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.';
  } finally {
    elements.refresh.disabled = false;
  }
}

elements.search.addEventListener('input', (event) => {
  state.query = event.target.value.trim();
  renderArticles();
});
elements.refresh.addEventListener('click', () => loadNews(true));
loadNews();
