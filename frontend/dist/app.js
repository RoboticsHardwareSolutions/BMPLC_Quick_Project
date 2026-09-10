(function () {
  'use strict';

  var API_URL_INFO = '/api/info';
  var infoHeader = document.getElementById('bmplc-type');
  var serialHeader = document.getElementById('serial');


  var API_URL_TASKS = '/api/tasks';
  var contentEl = document.getElementById('tasks-content');
  var refreshBtn = document.getElementById('refresh-btn');
  var inFlight = false;

  function get_info() {
    fetch(API_URL_INFO, { headers: { 'Accept': 'application/json' } })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        infoHeader.textContent = data.bmplcType || 'Unknown';
        serialHeader.textContent = data.serial || 'Unknown';
      })
      .catch(function () {
        showError('No data: server is not responding at ' + API_URL_INFO);
      })
  }

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
      var name = t.task || '?';
      var priority = t.priority || 0;
      var load = t.load || 0;
      var stackMinFree = t.stackMinFree || 0;
      var num = parseFloat(load);
      if (!isFinite(num)) num = null;
      return { name: name, load: num, priority: priority, stackMinFree: stackMinFree };
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
        '<td>' + esc(t.stackMinFree) + '</td></tr>';
    }).join('');
    contentEl.className = '';
    contentEl.innerHTML =
      '<table><tr><th>Task</th><th>Load</th><th>%</th><th>Priority</th><th>Stack Min Free</th></tr>' + rows + '</table>';
  }

  function showError(msg) {
    contentEl.className = 'status error';
    contentEl.textContent = msg;
  }

  function load() {
    if (inFlight) return;
    inFlight = true;
    fetch(API_URL_TASKS, { headers: { 'Accept': 'application/json' } })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        render(normalize(data));
      })
      .catch(function () {
        showError('No data: server is not responding at ' + API_URL_TASKS);
      })
      .then(function () {
        inFlight = false;
      });
  }

  refreshBtn.addEventListener('click', function () { load(); });
  get_info();
  load();
  setInterval(function () { load(); }, 500);

  // --- Discrete I/O panel ---
  var ioIndicators = document.querySelectorAll('.io-ind');
  var relayButtons = document.querySelectorAll('.relay-btn');
  var doButtons = document.querySelectorAll('.io-btn');
  var ioButtons = document.querySelectorAll('.relay-btn, .io-btn');
  var ioInFlight = false;

  function set_states(elements, values) {
    if (!values) return;
    for (var i = 0; i < elements.length; i++) {
      if (values[i]) {
        elements[i].classList.add('on');
      } else {
        elements[i].classList.remove('on');
      }
    }
  }

  function render_io(data) {
    // Bitmask: bits 0-4 inputs, bits 5-9 relays, bits 10-14 outputs
    if (typeof data !== 'number' || data < 0 || data > 32767) return;
    var bits = function (start) {
      var r = [];
      for (var i = 0; i < 5; i++)
        r.push(((data >> (start + i)) & 1) === 1);
      return r;
    };
    set_states(ioIndicators, bits(0));
    set_states(relayButtons, bits(5));
    set_states(doButtons, bits(10));
  }

  function load_io() {
    if (ioInFlight) return;
    ioInFlight = true;
    fetch('/api/io', { headers: { 'Accept': 'application/json' } })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        render_io(data);
      })
      .catch(function () {
        // IO endpoint may be unavailable on some boards: stay silent
      })
      .then(function () {
        ioInFlight = false;
      });
  }

  for (var b = 0; b < ioButtons.length; b++) {
    (function (btn) {
      btn.addEventListener('click', function () {
        var group = btn.getAttribute('data-group');
        var index = parseInt(btn.getAttribute('data-index'), 10);
        var on = !btn.classList.contains('on');
        fetch('/api/io', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ group: group, index: index, on: on })
        })
          .then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
          })
          .then(function () {
            if (on) {
              btn.classList.add('on');
            } else {
              btn.classList.remove('on');
            }
          })
          .catch(function () {
            // Ignore: the next poll restores the real state
          });
      });
    })(ioButtons[b]);
  }

  load_io();
  setInterval(function () { load_io(); }, 250);
})();
