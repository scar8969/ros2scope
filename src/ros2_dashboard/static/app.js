/* Client half of the served pages.
 *
 * The templates are complete without this file: every control is a real <form>
 * submit or a plain <a href>.  What a static document cannot do is poll the JSON
 * API, so that is the only thing this file adds, together with the two <button>s
 * the markup wraps in an <a>, and a local CSV export for the one table the
 * server does not expose as CSV.  Every lookup is guarded, so the same file is
 * served by every page of the app and is a no-op where an element is absent.
 *
 * Endpoints used: GET /api/status and POST /api/record, both documented in
 * openapi/ros2scope.yaml.
 */
(function () {
  "use strict";
  if (!window.fetch || !window.Blob || !document.querySelector) { return; }

  var byId = function (id) { return document.getElementById(id); };
  var api = function (path) { return new URL(path, document.baseURI).toString(); };

  function note(ids, text) {
    for (var i = 0; i < ids.length; i++) {
      var el = byId(ids[i]);
      if (el) { el.textContent = text; return true; }
    }
    return false;
  }

  function csvOf(table) {
    var out = [], i, j;
    for (i = 0; i < table.rows.length; i++) {
      var cells = [];
      for (j = 0; j < table.rows[i].cells.length; j++) {
        var t = (table.rows[i].cells[j].innerText || "").trim();
        cells.push('"' + t.replace(/"/g, '""') + '"');
      }
      out.push(cells.join(","));
    }
    return out.join("\n");
  }

  function download(name, text) {
    var href = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
    var a = document.createElement("a");
    a.href = href;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.setTimeout(function () { URL.revokeObjectURL(href); }, 0);
  }

  /* The state the templates already rendered, refreshed from the JSON API. */
  function paint(s) {
    var state = byId("bridge-state");
    if (state) {
      state.textContent = s.active_recording ? "recording #" + s.active_recording : "idle";
      state.className = s.active_recording ? "tag warn" : "tag";
    }
    var bridge = byId("bridge-id");
    if (bridge && s.bridge) { bridge.textContent = s.bridge; }
    var count = byId("rec-count");
    if (count && s.recordings) {
      count.textContent = count.textContent.replace(/\d+/, String(s.recordings.length));
    }
    var pose = byId("pose-source");
    if (pose && s.pose) {
      pose.textContent = "live /api/status \u00b7 x " + s.pose.x + " y " + s.pose.y +
                         " \u03b8 " + s.pose.theta;
    }
    if (s.log) { note(["record-result"], s.log); }
  }

  function refresh() {
    fetch(api("api/status"), { headers: { Accept: "application/json" },
                              credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (s) { if (s) { paint(s); } })
      .catch(function () { /* server restarting: keep the last good frame */ });
  }

  var ticker = null;
  function follow(el) {
    if (ticker) {
      window.clearInterval(ticker);
      ticker = null;
      el.textContent = "follow robot";
      return;
    }
    refresh();
    ticker = window.setInterval(refresh, 2000);
    el.textContent = "following (2 s)";
  }

  function record(el, topics, suffix) {
    var nameEl = byId("recording-name");
    var body = {
      name: ((nameEl && nameEl.value) || "run1") + (suffix || ""),
      topics: topics || []
    };
    el.setAttribute("aria-busy", "true");
    fetch(api("api/record"), { method: "POST", credentials: "same-origin",
                               headers: { "Content-Type": "application/json" },
                               body: JSON.stringify(body) })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        note(["record-result"], "POST /api/record -> recording #" + d.id + " on " +
                                (body.topics.join(", ") || "the default topics"));
        window.location.reload();
      })
      .catch(function (err) {
        el.removeAttribute("aria-busy");
        note(["record-result"], "POST /api/record failed: " + err);
      });
  }

  function exportCsv(el) {
    var card = el.closest ? el.closest(".card") : null;
    var table = (card && card.querySelector("table")) || document.querySelector("table");
    if (!table || !table.rows.length) {
      note(["export-note", "series-output", "record-result"],
           "no rendered table to export on this page");
      return;
    }
    var name = (document.title || "export").replace(/[^\w.-]+/g, "_") + ".csv";
    download(name, csvOf(table));
    note(["export-note", "series-output", "record-result"],
         "downloaded " + name + " with " + (table.rows.length - 1) +
         " data row(s) from the rendered table");
  }

  /* One delegated handler covers every control the pages ship. */
  document.addEventListener("click", function (ev) {
    var el = ev.target && ev.target.closest ? ev.target.closest("[id]") : null;
    if (!el) { return; }
    var link = el.closest ? el.closest("a[href]") : null;

    if (el.id === "joystick") {
      /* Teleop: the relay in web/ws.py publishes /cmd_vel; this records it. */
      ev.preventDefault();
      record(el, ["cmd_vel"], "-teleop");
    } else if (el.id === "follow-btn") {
      ev.preventDefault();
      follow(el);
    } else if (el.id === "export-csv") {
      ev.preventDefault();
      if (link) { window.location.assign(link.href); } else { exportCsv(el); }
    } else if (el.id === "signal-btn") {
      /* A <button> inside an <a> takes the click, so the link the template
       * built has to be followed explicitly. */
      if (link) { ev.preventDefault(); window.location.assign(link.href); }
    } else if (el.id === "refresh" && !el.form) {
      ev.preventDefault();
      window.location.reload();
    }
  });

  /* Submitting twice in a row creates two rows, so the second is dropped. */
  var last = 0;
  document.addEventListener("submit", function (ev) {
    var now = Date.now();
    if (now - last < 1500) { ev.preventDefault(); return; }
    last = now;
  });

  /* The can_id box filters the rendered rows while you type; Enter still
   * submits the GET form so the server re-queries SQLite. */
  var filter = byId("log-filter");
  if (filter) {
    var apply = function () {
      var want = filter.value.trim().toUpperCase();
      var rows = document.querySelectorAll(".scroll tr");
      var shown = 0, total = 0;
      for (var i = 0; i < rows.length; i++) {
        if (rows[i].cells.length < 2 || rows[i].querySelector("th")) { continue; }
        total += 1;
        var cell = (rows[i].cells[1].innerText || "").toUpperCase();
        var hit = !want || cell.indexOf(want) >= 0;
        rows[i].style.display = hit ? "" : "none";
        if (hit) { shown += 1; }
      }
      note(["state-line"], shown + " of " + total + " rendered row(s) match can_id " +
                            (want || "*"));
    };
    filter.addEventListener("input", apply);
    filter.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" && filter.form) {
        ev.preventDefault();
        if (filter.form.requestSubmit) { filter.form.requestSubmit(); }
        else { filter.form.submit(); }
      }
    });
  }
})();
