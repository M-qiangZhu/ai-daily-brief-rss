(function () {
  'use strict';

  var state = {
    allItems: [],
    dates: [],
    activeDate: '',
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

  function byId(id) {
    return document.getElementById(id);
  }

  function preferredTheme() {
    var saved = window.localStorage.getItem(themeStorageKey);
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
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

  function itemsForActiveDate() {
    return state.allItems.filter(function (item) {
      return item.date === state.activeDate;
    }).sort(compareItems);
  }

  function compareItems(a, b) {
    var priorityA = typePriority[a.type] == null ? 99 : typePriority[a.type];
    var priorityB = typePriority[b.type] == null ? 99 : typePriority[b.type];
    if (priorityA !== priorityB) return priorityA - priorityB;
    return String(b.published_at || '').localeCompare(String(a.published_at || ''));
  }

  function renderArchiveDates() {
    var wrap = byId('date-list');
    if (!wrap) return;
    wrap.innerHTML = state.dates.map(function (date) {
      var count = state.allItems.filter(function (item) { return item.date === date; }).length;
      var active = date === state.activeDate ? ' active' : '';
      return '<button class="date-chip' + active + '" type="button" data-date="' + escapeHtml(date) + '">' +
        '<span>' + escapeHtml(date) + '</span><strong>' + count + '</strong>' +
        '</button>';
    }).join('');
  }

  function setActiveDate(date, pushUrl) {
    state.activeDate = date;
    byId('active-date').textContent = formatDateLabel(date);
    if (pushUrl && state.page === 'archive') {
      window.history.replaceState(null, '', 'ai-news-archive.html?date=' + encodeURIComponent(date));
    }
    renderArchiveDates();
    render();
  }

  function render() {
    var items = itemsForActiveDate();
    var board = byId('news-board');
    var empty = byId('empty-state');
    var brief = byId('brief-line');

    if (brief) {
      brief.textContent = state.activeDate + ' · 已同步 ' + items.length + ' 条 AI 资讯';
    }
    empty.hidden = items.length > 0;

    board.innerHTML = items.map(function (item, index) {
      var serial = String(index + 1).padStart(2, '0');
      var source = item.source_site || '未知来源';
      var sourceClass = 'source-pill ' + sourceVariant(source);
      return [
        '<article class="news-card">',
        '  <div class="card-index">' + serial + '</div>',
        '  <div class="card-body">',
        '    <div class="card-meta">',
        '      <span class="' + sourceClass + '">' + escapeHtml(source) + '</span>',
        '      <time datetime="' + escapeHtml(item.date) + '">' + escapeHtml(item.date) + '</time>',
        '    </div>',
        '    <h2><a href="' + escapeHtml(item.detail_link) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(item.title) + '</a></h2>',
        '    <p>' + escapeHtml(item.content_summary || '暂无摘要') + '</p>',
        '    <a class="detail-link" href="' + escapeHtml(item.detail_link) + '" target="_blank" rel="noopener noreferrer">打开原文</a>',
        '  </div>',
        '</article>'
      ].join('');
    }).join('');
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
    state.allItems = (data.items || []).slice().sort(function (a, b) {
      var dateOrder = String(b.date || '').localeCompare(String(a.date || ''));
      if (dateOrder !== 0) return dateOrder;
      return compareItems(a, b);
    });
    state.dates = unique(state.allItems.map(function (item) { return item.date; }));

    var urlDate = readDateFromUrl();
    state.activeDate = state.page === 'archive' && state.dates.indexOf(urlDate) >= 0
      ? urlDate
      : state.dates[0] || '';

    bindArchive();
    bindThemeToggle();
    applyTheme(preferredTheme());
    setActiveDate(state.activeDate, state.page === 'archive');
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyTheme(preferredTheme());
    fetch('assets/data/ai-news.json', { cache: 'no-store' })
      .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
      })
      .then(init)
      .catch(function () {
        byId('active-date').textContent = '📅 数据加载失败';
        byId('empty-state').hidden = false;
      });
  });
})();
