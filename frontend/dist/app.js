(function () {
  'use strict';

  var I18N = {
    ru: {
      ioTitle: 'Ввод / вывод',
      groupRelays: 'Реле',
      groupInputs: 'Входы',
      groupOutputs: 'Выходы',
      tasksTitle: 'Панель задач',
      noData: 'Нет данных',
      unknown: 'Неизвестно',
      errPrefix: 'Нет данных: сервер не отвечает по адресу ',
      relayPrefix: 'Реле ',
      doPrefix: 'Выход ',
      inPrefix: 'Вход ',
      thTask: 'Задача',
      thLoad: 'Нагрузка',
      thPriority: 'Приоритет',
      thStack: 'Стек, мин. свободно',
      bridgesTitle: 'Мосты', bridgeBaud: 'Скорость', bridgeIp: 'IP-адрес', bridgeEnable: 'Включен', bridgeNoSettings: 'Нет настроек', bridgeNone: 'Мосты не обнаружены',
      bridgeWarn: 'USB-устройство переконфигурируется; веб-интерфейс будет недоступен'
    },
    en: {
      ioTitle: 'I/O',
      groupRelays: 'Relays',
      groupInputs: 'Inputs',
      groupOutputs: 'Outputs',
      tasksTitle: 'Task Load',
      noData: 'No data',
      unknown: 'Unknown',
      errPrefix: 'No data: server is not responding at ',
      relayPrefix: 'Relay ',
      doPrefix: 'Output ',
      inPrefix: 'Input ',
      thTask: 'Task',
      thLoad: 'Load',
      thPriority: 'Priority',
      thStack: 'Stack Min Free',
      bridgesTitle: 'Bridges', bridgeBaud: 'Baud rate', bridgeIp: 'IP address', bridgeEnable: 'Enabled', bridgeNoSettings: 'No settings', bridgeNone: 'No bridges found',
      bridgeWarn: 'USB device is being reconfigured; the web interface will be unavailable'
    }
  };
  var currentLang = 'ru';

  var API_URL_INFO = '/api/info';
  var infoHeader = document.getElementById('bmplc-type');
  var serialHeader = document.getElementById('serial');
  var versionHeader = document.getElementById('version');


  var API_URL_TASKS = '/api/tasks';
  var contentEl = document.getElementById('tasks-content');
  var inFlight = false;

  function t(key) {
    return I18N[currentLang][key];
  }

  function apply(lang) {
    if (!I18N[lang]) {
      lang = 'ru';
    }
    currentLang = lang;
    document.documentElement.lang = lang;
    localStorage.setItem('bmplc-lang', lang);

    document.querySelector('.io-card h2').textContent = t('ioTitle');

    var groupTitles = document.querySelectorAll('.io-group-title');
    for (var i = 0; i < groupTitles.length; i++) {
      groupTitles[i].textContent = t(i === 0 ? 'groupRelays' : i === 1 ? 'groupInputs' : 'groupOutputs');
    }

    document.querySelector('.tasks-card h2').textContent = t('tasksTitle');

    var relayButtons = document.querySelectorAll('.relay-btn');
    for (var r = 0; r < relayButtons.length; r++) {
      var rn = parseInt(relayButtons[r].getAttribute('data-index'), 10) + 1;
      var rt = t('relayPrefix') + rn;
      relayButtons[r].setAttribute('title', rt);
      relayButtons[r].setAttribute('aria-label', rt);
    }
    var doButtons = document.querySelectorAll('.io-btn');
    for (var d = 0; d < doButtons.length; d++) {
      var dn = parseInt(doButtons[d].getAttribute('data-index'), 10) + 1;
      var dt = t('doPrefix') + dn;
      doButtons[d].setAttribute('title', dt);
      doButtons[d].setAttribute('aria-label', dt);
    }
    var ioIndicators = document.querySelectorAll('.io-ind');
    for (var n = 0; n < ioIndicators.length; n++) {
      ioIndicators[n].setAttribute('title', t('inPrefix') + (n + 1));
    }

    var langButtons = document.querySelectorAll('.lang-btn');
    for (var b = 0; b < langButtons.length; b++) {
      if (langButtons[b].getAttribute('data-lang') === lang) {
        langButtons[b].classList.add('active');
      } else {
        langButtons[b].classList.remove('active');
      }
    }

    var bridgeTitle = document.getElementById('bridge-title');
    if (bridgeTitle) bridgeTitle.textContent = t('bridgesTitle');
    renderBridges();
  }

  var langButtons = document.querySelectorAll('.lang-btn');
  for (var lb = 0; lb < langButtons.length; lb++) {
    langButtons[lb].addEventListener('click', function () {
      apply(this.getAttribute('data-lang'));
    });
  }

  function get_info() {
    fetch(API_URL_INFO, { headers: { 'Accept': 'application/json' } })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        infoHeader.textContent = data.bmplcType || 'BMPLC';
        serialHeader.textContent = data.serial || 'xxxx-xxxx-xxxxxxxx-xxxxxxxx';
        versionHeader.textContent = data.version || 'v0.0.0';
      })
      .catch(function () {
        infoHeader.textContent = 'BMPLC';
        serialHeader.textContent = 'xxxx-xxxx-xxxxxxxx-xxxxxxxx';
        versionHeader.textContent = 'v0.0.0';
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
      contentEl.textContent = t('noData');
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
    contentEl.innerHTML =
      '<table><tr><th>' + t('thTask') + '</th><th>' + t('thLoad') + '</th><th>' + '%' + '</th><th>' + t('thPriority') + '</th><th>' + t('thStack') + '</th></tr>' + rows + '</table>';
  }

  function showError(msg) {
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
        showError(t('errPrefix') + API_URL_TASKS);
      })
      .then(function () {
        inFlight = false;
      });
  }

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
  apply(localStorage.getItem('bmplc-lang') || 'ru');

  var API_URL_BRIDGES = '/api/bridges';
  var bridgeListEl = document.getElementById('bridge-list');
  var bridgesData = null;

  function normalizeBridges(data) {
    if (!data || !Array.isArray(data.bridges)) return [];
    return data.bridges.map(function (item) {
      for (var k in item) {
        if (Object.prototype.hasOwnProperty.call(item, k)) {
          return { port: k, type: item[k] };
        }
      }
      return { port: '?', type: '?' };
    });
  }

  function renderBridges() {
    if (!bridgeListEl || !bridgesData || !bridgesData.length) return;
    document.getElementById('bridge-panel').style.visibility = 'visible';
    bridgeListEl.innerHTML = bridgesData.map(function (b) {
      var isUsb = (b.port + ':' + b.type).indexOf('usb') !== -1;
      var warn = isUsb
        ? '<span class="bridge-warn" data-tip="' + esc(t('bridgeWarn')) + '">!</span>'
        : '';
      return '<button class="bridge-btn" type="button" data-port="' + esc(b.port) + '" data-type="' + esc(b.type) + '">' + esc(b.port + ':' + b.type) + warn + '</button>';
    }).join('');
  }

  function loadBridges() {
    fetch(API_URL_BRIDGES).then(function (res) {
      if (res.status === 204) return { bridges: [] };
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    }).then(function (data) {
      bridgesData = normalizeBridges(data);
      renderBridges();
    }).catch(function () {
      bridgesData = [];
      renderBridges();
    });
  }

  if (bridgeListEl) {
    bridgeListEl.addEventListener('click', function (e) {
      var btn = e.target.closest('.bridge-btn');
      if (!btn) return;
      var port = btn.getAttribute('data-port');
      var type = btn.getAttribute('data-type');
      fetch(API_URL_BRIDGES, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port: port, type: type })
      })
        .then(function (res) {
          if (!res.ok) throw new Error('HTTP ' + res.status);
          return res.json();
        })
        .catch(function () {
          // Ignore errors: the backend stub will handle retries
        });
    });
  }

  loadBridges();
})();
