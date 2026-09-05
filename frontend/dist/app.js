(function () {
  'use strict';

  var API_URL = '/api/tasks';
  var contentEl = document.getElementById('tasks-content');
  var refreshBtn = document.getElementById('refresh-btn');
  var inFlight = false;

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  function normalize(data) {
    // Accepts: [...] | {tasks:[...]} | {Task,Time,AbsTime,Load...} table rows
    var list = Array.isArray(data) ? data
      : (data && Array.isArray(data.tasks)) ? data.tasks
        : null;
    if (!list) return [];
    return list.map(function (t) {
      var name = t.task || t.name || t.Task || '?';
      var priority = t.priority != null ? t.priority : (t.Priority != null ? t.Priority : null);
      var load = t.load != null ? t.load : (t.Load != null ? t.Load : t.cpu != null ? t.cpu : null);
      var stack_min_free = t.stack_min_free != null ? t.stack_min_free : (t.StackMinFree != null ? t.StackMinFree : null);
      var num = parseFloat(load);
      if (!isFinite(num)) num = null;
      return { name: name, load: num, priority: priority, stack_min_free: stack_min_free };
    });
  }

  function render(tasks) {
    if (!tasks.length) {
      contentEl.className = 'status';
      contentEl.textContent = 'No data';
      return;
    }
    var rows = tasks.map(function (t) {
      var pct = t.load == null ? '—' : t.load.toFixed(1) + '%';
      var width = t.load == null ? 0 : Math.max(0, Math.min(100, t.load));
      return '<tr><td>' + esc(t.name) + '</td>' +
        '<td><div class="bar"><div class="bar-fill" style="width:' + width + '%"></div></div></td>' +
        '<td class="pct">' + esc(pct) + '</td>' +
        '<td>' + esc(t.priority) + '</td>' +
        '<td>' + esc(t.stack_min_free) + '</td></tr>';
    }).join('');
    contentEl.className = '';
    contentEl.innerHTML =
      '<table><tr><th>Task</th><th>Load</th><th>%</th><th>Priority</th><th>Stack Min Free</th></tr>' + rows + '</table>';
  }

  function showError(msg) {
    contentEl.className = 'status error';
    contentEl.textContent = msg;
  }

  function load(background) {
    if (inFlight) return;
    inFlight = true;
    if (!background) {
      contentEl.className = 'status';
      contentEl.textContent = 'Loading...';
    }
    fetch(API_URL, { headers: { 'Accept': 'application/json' } })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        render(normalize(data));
      })
      .catch(function () {
        showError('No data: server is not responding at ' + API_URL);
      })
      .then(function () {
        inFlight = false;
      });
  }

  refreshBtn.addEventListener('click', function () { load(false); });
  load(false);
  setInterval(function () { load(true); }, 100);
})();
