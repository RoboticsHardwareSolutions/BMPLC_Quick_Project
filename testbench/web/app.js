(() => {
  const POLL_MS = 300;

  const inputsRows = document.getElementById("inputs-rows");
  const outputsRows = document.getElementById("outputs-rows");
  const ifaceBadges = document.getElementById("iface-badges");
  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("status-text");
  const footerStats = document.getElementById("footer-stats");

  // label -> DOM node, built lazily the first time each label is seen (labels come
  // entirely from the server's /api/state response, which sources them from
  // testbench.toml -- nothing here is hardcoded).
  const inputNodes = {};
  const outputNodes = {};
  const ifaceNodes = {};

  function makeRow(container, label, interactive) {
    const row = document.createElement("div");
    row.className = "row";

    const name = document.createElement("span");
    name.className = "row-label";
    name.textContent = label;
    row.appendChild(name);

    let indicator;
    if (interactive) {
      indicator = document.createElement("button");
      indicator.className = "toggle";
      indicator.addEventListener("click", () => {
        const next = !indicator.classList.contains("on");
        setOutput(label, next);
      });
    } else {
      indicator = document.createElement("span");
      indicator.className = "led";
    }
    row.appendChild(indicator);
    container.appendChild(row);
    return indicator;
  }

  function setBit(nodes, container, label, value, interactive) {
    if (!(label in nodes)) {
      nodes[label] = makeRow(container, label, interactive);
    }
    nodes[label].classList.toggle("on", !!value);
  }

  function setIface(name, found) {
    if (!(name in ifaceNodes)) {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = name;
      ifaceBadges.appendChild(badge);
      ifaceNodes[name] = badge;
    }
    ifaceNodes[name].classList.toggle("found", !!found);
    ifaceNodes[name].title = found ? "detected" : "not detected";
  }

  async function setOutput(label, value) {
    try {
      await fetch("/api/outputs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [label]: value }),
      });
    } catch (e) {
      // next poll will reconcile the toggle's visual state regardless
    }
  }

  async function load() {
    try {
      const res = await fetch("/api/state", { headers: { Accept: "application/json" } });
      if (!res.ok) throw new Error("http " + res.status);
      const data = await res.json();

      for (const [label, value] of Object.entries(data.inputs || {})) {
        setBit(inputNodes, inputsRows, label, value, false);
      }
      for (const [label, value] of Object.entries(data.outputs || {})) {
        setBit(outputNodes, outputsRows, label, value, true);
      }
      for (const [name, found] of Object.entries(data.iface || {})) {
        setIface(name, found);
      }

      statusDot.className = "dot ok";
      statusText.textContent = data.status.input_valid ? "polling" : "inputs unreachable";
      footerStats.textContent =
        `polls=${data.status.poll_count} errors=${data.status.poll_errors} ` +
        `uptime=${Math.round(data.status.uptime_ms / 1000)}s`;
    } catch (e) {
      statusDot.className = "dot err";
      statusText.textContent = "daemon unreachable";
    }
  }

  load();
  setInterval(load, POLL_MS);
})();
