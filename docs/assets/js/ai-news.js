(function () {
  'use strict';

  var state = {
    allItems: [],
    archiveIndex: [],
    loadedByDate: {},
    dates: [],
    activeDate: '',
    activeCategory: '',
    sourceHealth: {},
    page: document.body.getAttribute('data-page') || 'today'
  };

  var weekdayNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  var themeStorageKey = 'ai-news-theme';
  var typePriority = {
    '政策': 0,
    '运营商': 1,
    '算力芯片': 2,
    'AI技术': 3,
    'AI模型': 4,
    'AI Agent': 5,
    '智能驾驶': 6,
    '机器人': 7,
    'AI硬件': 8,
    'AI安全': 9,
    'AI编程': 10,
    'AI资讯': 11
  };
  var categoryPriority = {
    '政策与监管': 0,
    '南通市官方AI动态': 1,
    '运营商与央国企动态': 2,
    '算力、数据中心与云基础设施': 3,
    'AI技术与产业应用': 4,
    '投融资与竞争格局': 5,
    '风险、安全与合规': 6,
    '技术社区观察': 7
  };
  var legacyCategoryMap = {
    'AI模型与智能体技术': 'AI技术与产业应用',
    '行业应用与商业化': 'AI技术与产业应用',
    'AI终端、机器人与硬件': 'AI技术与产业应用'
  };
  var alwaysVisibleCategories = ['南通市官方AI动态'];
  var categoryAnchors = {
    '政策与监管': 'category-policy',
    '南通市官方AI动态': 'category-nantong',
    '运营商与央国企动态': 'category-telecom',
    '算力、数据中心与云基础设施': 'category-infrastructure',
    'AI技术与产业应用': 'category-ai-application',
    '投融资与竞争格局': 'category-investment',
    '风险、安全与合规': 'category-risk',
    '技术社区观察': 'category-community'
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function preferredTheme() {
    var saved = window.localStorage.getItem(themeStorageKey);
    if (saved === 'light' || saved === 'dark') return saved;
    return 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    var button = byId('theme-toggle');
    if (button) {
      button.textContent = theme === 'dark' ? '☼' : '◐';
      button.setAttribute('aria-label', theme === 'dark' ? '切换为浅色模式' : '切换为深色模式');
      button.setAttribute('title', theme === 'dark' ? '切换为浅色模式' : '切换为深色模式');
    }
  }

  function bindThemeToggle() {
    var button = byId('theme-toggle');
    if (!button) return;
    button.addEventListener('click', function () {
      var current = document.documentElement.getAttribute('data-theme') || preferredTheme();
      var next = current === 'dark' ? 'light' : 'dark';
      window.localStorage.setItem(themeStorageKey, next);
      applyTheme(next);
    });
  }

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, function (char) {
      return {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      }[char];
    });
  }

  function unique(values) {
    var seen = {};
    return values.filter(function (value) {
      value = String(value || '').trim();
      if (!value || seen[value]) return false;
      seen[value] = true;
      return true;
    }).sort().reverse();
  }

  function formatDateLabel(dateText) {
    var parts = String(dateText || '').split('-').map(Number);
    if (parts.length !== 3) return '📅 ' + dateText;
    var date = new Date(parts[0], parts[1] - 1, parts[2]);
    var month = String(parts[1]).padStart(2, '0');
    var day = String(parts[2]).padStart(2, '0');
    return '📅 ' + parts[0] + '年' + month + '月' + day + '日 · ' + weekdayNames[date.getDay()];
  }

  function sourceVariant(source) {
    var text = String(source || '未知来源');
    var hash = 0;
    for (var i = 0; i < text.length; i += 1) {
      hash = (hash + text.charCodeAt(i) * (i + 1)) % 5;
    }
    return 'source-pill--' + hash;
  }

  function readDateFromUrl() {
    return new URLSearchParams(window.location.search).get('date') || '';
  }

  function normalizeCategory(category) {
    return legacyCategoryMap[category] || category || 'AI技术与产业应用';
  }

  function normalizeItems(items) {
    return (items || []).map(function (item) {
      item.leadership_category = normalizeCategory(item.leadership_category);
      return item;
    });
  }

  function categoryAnchor(category) {
    return categoryAnchors[category] || 'category-' + String(category || '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  }

  function itemsForActiveDate() {
    return (state.loadedByDate[state.activeDate] || []).slice().sort(compareItems);
  }

  function compareItems(a, b) {
    var categoryA = categoryPriority[a.leadership_category] == null ? 99 : categoryPriority[a.leadership_category];
    var categoryB = categoryPriority[b.leadership_category] == null ? 99 : categoryPriority[b.leadership_category];
    if (categoryA !== categoryB) return categoryA - categoryB;
    var priorityA = typePriority[a.type] == null ? 99 : typePriority[a.type];
    var priorityB = typePriority[b.type] == null ? 99 : typePriority[b.type];
    if (priorityA !== priorityB) return priorityA - priorityB;
    return String(b.published_at || '').localeCompare(String(a.published_at || ''));
  }

  function groupItems(items) {
    var groups = {};
    items.forEach(function (item) {
      var category = normalizeCategory(item.leadership_category);
      if (!groups[category]) groups[category] = [];
      groups[category].push(item);
    });
    alwaysVisibleCategories.forEach(function (category) {
      if (!groups[category]) groups[category] = [];
    });
    return Object.keys(groups).sort(function (a, b) {
      var priorityA = categoryPriority[a] == null ? 99 : categoryPriority[a];
      var priorityB = categoryPriority[b] == null ? 99 : categoryPriority[b];
      return priorityA - priorityB;
    }).map(function (category) {
      return { category: category, items: groups[category].sort(compareItems) };
    });
  }

  function firstItem(items, categoryNames) {
    for (var i = 0; i < categoryNames.length; i += 1) {
      var found = items.find(function (item) {
        return item.leadership_category === categoryNames[i];
      });
      if (found) return found;
    }
    return null;
  }

  function shortTitle(item) {
    if (!item) return '暂无重点事项';
    var title = String(item.title || '').replace(/\s+/g, ' ').trim();
    return title.length > 42 ? title.slice(0, 41) + '…' : title;
  }

  function categorySummary(category, items) {
    var count = items.length;
    var sourceCount = unique(items.map(function (item) { return item.source_site; })).length;
    var top = shortTitle(items[0]);
    var templates = {
      '政策与监管': '政策和监管信号优先关注，今日共 ' + count + ' 条，重点是“' + top + '”。',
      '南通市官方AI动态': count
        ? '南通本地 AI 动态共 ' + count + ' 条，重点是“' + top + '”。'
        : '已完成南通市级、区县政府及媒体转载监控，今日暂无新增 AI 动态。',
      '运营商与央国企动态': '央国企与运营商动态共 ' + count + ' 条，可关注政企协同、云网融合和行业客户机会。',
      '算力、数据中心与云基础设施': '算力、数据中心和云基础设施共 ' + count + ' 条，反映 AI 基建投入、国产算力和边缘能力进展。',
      'AI技术与产业应用': 'AI 模型、智能体、行业应用、终端与机器人共 ' + count + ' 条，关注能力演进和产业落地。',
      '投融资与竞争格局': '投融资和竞争格局共 ' + count + ' 条，辅助判断产业热度和资本流向。',
      '风险、安全与合规': '风险、安全与合规共 ' + count + ' 条，适合纳入治理、风控和合规跟踪。',
      '技术社区观察': '技术社区观察共 ' + count + ' 条，主要用于捕捉开发者工具和一线实践反馈。'
    };
    return (templates[category] || ('该类共 ' + count + ' 条，来自 ' + sourceCount + ' 个来源。'));
  }

  function renderLeadershipPanel(items) {
    var panel = byId('leadership-panel');
    if (!panel) return;
    if (!items.length) {
      panel.innerHTML = '';
      return;
    }
    var policy = firstItem(items, ['政策与监管']);
    var nantong = firstItem(items.filter(function (item) {
      return normalizeCategory(item.leadership_category) === '南通市官方AI动态';
    }), ['南通市官方AI动态']);
    var infra = firstItem(items, ['运营商与央国企动态', '算力、数据中心与云基础设施']);
    var tech = firstItem(items, ['AI技术与产业应用']);
    var categories = groupItems(items);
    var sourceCount = unique(items.map(function (item) { return item.source_site; })).length;
    var bullets = [
      { label: '政策信号', text: policy ? shortTitle(policy) : '今日暂无明确政策信号' },
      { label: '南通关注', text: nantong ? shortTitle(nantong) : '今日暂无南通市 AI 动态' },
      { label: '电信关注', text: infra ? shortTitle(infra) : '今日暂无运营商或算力基础设施重点' },
      { label: '技术趋势', text: tech ? shortTitle(tech) : '今日暂无 AI 技术与产业应用重点' }
    ];
    panel.innerHTML = [
      '<div class="leadership-head">',
      '  <div><span class="eyebrow">领导摘要</span><h2>' + escapeHtml(state.activeDate) + ' AI 情报速览</h2></div>',
      '  <div class="metric-row">',
      '    <span><strong>' + items.length + '</strong> 条资讯</span>',
      '    <span><strong>' + categories.length + '</strong> 类主题</span>',
      '    <span><strong>' + sourceCount + '</strong> 个来源</span>',
      '  </div>',
      '</div>',
      '<div class="insight-list">',
      bullets.map(function (bullet) {
        return '<article class="insight-item"><span>' + escapeHtml(bullet.label) + '</span><p>' + escapeHtml(bullet.text) + '</p></article>';
      }).join(''),
      '</div>'
    ].join('');
  }

  function renderCategoryOverview(items) {
    var wrap = byId('category-overview');
    if (!wrap) return;
    var groups = groupItems(items);
    wrap.innerHTML = groups.map(function (group) {
      var anchor = categoryAnchor(group.category);
      var expanded = state.activeCategory === group.category;
      return '<button class="category-brief' + (expanded ? ' active' : '') + '" type="button" data-category="' +
        escapeHtml(group.category) + '" aria-expanded="' + expanded + '" aria-controls="' + escapeHtml(anchor) + '-panel">' +
        '<div><h3>' + escapeHtml(group.category) + '</h3><p>' + escapeHtml(categorySummary(group.category, group.items)) + '</p></div>' +
        '<span class="category-brief-side"><strong>' + group.items.length + '</strong><i aria-hidden="true"></i></span>' +
        '</button>';
    }).join('');
    renderCategoryNav(groups);
  }

  function renderCategoryNav(groups) {
    var wrap = byId('category-nav-list');
    if (!wrap) return;
    wrap.innerHTML = groups.map(function (group) {
      var active = state.activeCategory === group.category;
      return '<button class="category-nav-chip' + (active ? ' active' : '') + '" type="button" data-category="' +
        escapeHtml(group.category) + '" aria-expanded="' + active + '">' +
        '<span>' + escapeHtml(group.category) + '</span><strong>' + group.items.length + '</strong></button>';
    }).join('');
  }

  function renderSourceHealth() {
    var wrap = byId('source-health');
    if (!wrap) return;
    var health = state.sourceHealth || {};
    if (!health.official_total) {
      wrap.hidden = true;
      return;
    }
    wrap.hidden = false;
    var failing = Number(health.official_failing || 0);
    wrap.className = 'source-health' + (failing ? ' source-health--warning' : '');
    wrap.innerHTML = '<span class="health-dot" aria-hidden="true"></span>' +
      '<strong>官方信源 ' + escapeHtml(health.official_checked || 0) + '/' + escapeHtml(health.official_total) + '</strong>' +
      '<span>' + (failing ? escapeHtml(failing) + ' 个源暂时异常' : '运行正常') + '</span>' +
      '<span>每 6 小时更新</span>';
  }

  function renderArchiveDates() {
    var wrap = byId('date-list');
    if (!wrap) return;
    wrap.innerHTML = state.dates.map(function (date) {
      var entry = state.archiveIndex.find(function (item) { return item.date === date; }) || {};
      var count = entry.count || 0;
      var active = date === state.activeDate ? ' active' : '';
      return '<button class="date-chip' + active + '" type="button" data-date="' + escapeHtml(date) + '">' +
        '<span>' + escapeHtml(date) + '</span><strong>' + count + '</strong>' +
        '</button>';
    }).join('');
  }

  function loadDateItems(date) {
    if (!date) return Promise.resolve([]);
    if (state.loadedByDate[date]) return Promise.resolve(state.loadedByDate[date]);
    return fetch('archive/' + encodeURIComponent(date) + '.json', { cache: 'no-store' })
      .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
      })
      .then(function (payload) {
        var items = normalizeItems(payload.items || []);
        state.loadedByDate[date] = items;
        return items;
      });
  }

  function setActiveDate(date, pushUrl) {
    state.activeDate = date;
    state.activeCategory = '';
    byId('active-date').textContent = formatDateLabel(date);
    if (pushUrl && state.page === 'archive') {
      window.history.replaceState(null, '', 'ai-news-archive.html?date=' + encodeURIComponent(date));
    }
    renderArchiveDates();
    var brief = byId('brief-line');
    if (brief) brief.textContent = date ? date + ' · 正在读取归档' : '暂无归档数据';
    loadDateItems(date)
      .then(function () { render(true); })
      .catch(function () {
        if (brief) brief.textContent = date + ' · 归档数据加载失败';
        state.loadedByDate[date] = [];
        render(true);
      });
  }

  function categoryFromHash(groups) {
    var hash = window.location.hash.replace(/^#/, '');
    var found = groups.find(function (group) {
      return categoryAnchor(group.category) === hash;
    });
    return found ? found.category : '';
  }

  function defaultCategory(groups) {
    var fromHash = categoryFromHash(groups);
    if (fromHash) return fromHash;
    var nonEmpty = groups.find(function (group) { return group.items.length > 0; });
    return nonEmpty ? nonEmpty.category : (groups[0] ? groups[0].category : '');
  }

  function render(resetCategory) {
    var items = itemsForActiveDate();
    var groups = groupItems(items);
    var board = byId('news-board');
    var empty = byId('empty-state');
    var brief = byId('brief-line');

    if (brief) {
      brief.textContent = state.activeDate + ' · 已同步 ' + items.length + ' 条 AI 资讯';
    }
    empty.hidden = items.length > 0;
    if (resetCategory || !groups.some(function (group) { return group.category === state.activeCategory; })) {
      state.activeCategory = defaultCategory(groups);
    }
    renderLeadershipPanel(items);
    renderCategoryOverview(items);
    renderSourceHealth();

    board.innerHTML = groups.map(function (group) {
      var anchor = categoryAnchor(group.category);
      var expanded = state.activeCategory === group.category;
      return [
        '<section class="category-section' + (expanded ? ' expanded' : '') + '" id="' + escapeHtml(anchor) + '">',
        '  <button class="category-section-head" type="button" data-category="' + escapeHtml(group.category) +
          '" aria-expanded="' + expanded + '" aria-controls="' + escapeHtml(anchor) + '-panel">',
        '    <div><h2>' + escapeHtml(group.category) + '</h2><p>' + escapeHtml(categorySummary(group.category, group.items)) + '</p></div>',
        '    <span class="section-head-side"><strong>' + group.items.length + '</strong><i aria-hidden="true"></i></span>',
        '  </button>',
        '  <div class="category-news-grid" id="' + escapeHtml(anchor) + '-panel"' + (expanded ? '' : ' hidden') + '>',
        group.items.length ? group.items.map(function (item, index) {
          var serial = String(index + 1).padStart(2, '0');
          var source = item.source_site || '未知来源';
          var sourceClass = 'source-pill ' + sourceVariant(source);
          return [
            '<article class="news-card">',
            '  <div class="card-index">' + serial + '</div>',
            '  <div class="card-body">',
            '    <div class="card-meta">',
            '      <span class="' + sourceClass + '">' + escapeHtml(source) + '</span>',
            item.source_tier === 'official' ? '      <span class="official-pill">官方</span>' : '',
            item.language === 'en' ? '      <span class="language-pill">EN</span>' : '',
            '      <span class="type-pill">' + escapeHtml(item.type || 'AI资讯') + '</span>',
            '      <time datetime="' + escapeHtml(item.date) + '">' + escapeHtml(item.date) + '</time>',
            '    </div>',
            '    <h2><a href="' + escapeHtml(item.detail_link) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(item.title) + '</a></h2>',
            '    <p>' + escapeHtml(item.content_summary || '暂无摘要') + '</p>',
            '    <a class="detail-link" href="' + escapeHtml(item.detail_link) + '" target="_blank" rel="noopener noreferrer">打开原文</a>',
            '  </div>',
            '</article>'
          ].join('');
        }).join('') : '<div class="category-empty">今日暂无新增</div>',
        '  </div>',
        '</section>'
      ].join('');
    }).join('');
  }

  function toggleCategory(category, shouldScroll, updateHash) {
    var next = state.activeCategory === category ? '' : category;
    state.activeCategory = next;
    renderCategoryOverview(itemsForActiveDate());
    var sections = byId('news-board').querySelectorAll('.category-section');
    sections.forEach(function (section) {
      var button = section.querySelector('[data-category]');
      var panel = section.querySelector('.category-news-grid');
      var expanded = Boolean(button && button.getAttribute('data-category') === next);
      section.classList.toggle('expanded', expanded);
      if (button) button.setAttribute('aria-expanded', String(expanded));
      if (panel) panel.hidden = !expanded;
    });
    if (updateHash) {
      var base = window.location.pathname + window.location.search;
      window.history.replaceState(null, '', next ? base + '#' + categoryAnchor(next) : base);
    }
    if (next && shouldScroll) {
      var target = byId(categoryAnchor(next));
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function bindCategories() {
    document.addEventListener('click', function (event) {
      var button = event.target.closest('[data-category]');
      if (!button) return;
      toggleCategory(button.getAttribute('data-category'), true, true);
    });
    window.addEventListener('hashchange', function () {
      var category = categoryFromHash(groupItems(itemsForActiveDate()));
      if (category && category !== state.activeCategory) toggleCategory(category, true, false);
    });
  }

  function bindArchive() {
    var dateList = byId('date-list');
    if (!dateList) return;
    dateList.addEventListener('click', function (event) {
      var button = event.target.closest('[data-date]');
      if (!button) return;
      setActiveDate(button.getAttribute('data-date'), true);
    });
  }

  function init(data) {
    state.archiveIndex = (data.dates || []).slice();
    state.dates = state.archiveIndex.map(function (item) { return item.date; }).filter(Boolean);

    var urlDate = readDateFromUrl();
    state.activeDate = state.page === 'archive' && state.dates.indexOf(urlDate) >= 0
      ? urlDate
      : data.latest_date || state.dates[0] || '';

    bindArchive();
    bindCategories();
    bindThemeToggle();
    applyTheme(preferredTheme());
    setActiveDate(state.activeDate, state.page === 'archive');
  }

  function initLegacyPayload(data) {
    var items = normalizeItems(data.items || []).slice().sort(compareItems);
    state.allItems = items;
    state.dates = unique(items.map(function (item) { return item.date; }));
    state.archiveIndex = state.dates.map(function (date) {
      var count = items.filter(function (item) { return item.date === date; }).length;
      return { date: date, count: count };
    });
    state.dates.forEach(function (date) {
      state.loadedByDate[date] = items.filter(function (item) { return item.date === date; });
    });
    init({ dates: state.archiveIndex, latest_date: state.dates[0] || '' });
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyTheme(preferredTheme());
    Promise.all([
      fetch('archive/index.json', { cache: 'no-store' }).then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
      }),
      fetch('assets/data/source-health.json', { cache: 'no-store' })
        .then(function (response) { return response.ok ? response.json() : {}; })
        .catch(function () { return {}; })
    ])
      .then(function (payloads) {
        state.sourceHealth = payloads[1] || {};
        init(payloads[0]);
      })
      .catch(function () {
        return fetch('assets/data/ai-news.json', { cache: 'no-store' })
          .then(function (response) {
            if (!response.ok) throw new Error('HTTP ' + response.status);
            return response.json();
          })
          .then(initLegacyPayload);
      })
      .catch(function () {
        byId('active-date').textContent = '📅 数据加载失败';
        byId('empty-state').hidden = false;
      });
  });
})();
