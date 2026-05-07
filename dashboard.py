"""
dashboard.py
Minimal Flask dashboard for tunnel health and events.
"""
from flask import Flask, jsonify, render_template_string
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
LOGS_DIR = Path("logs")

HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Secure Campus Fabric | Dashboard</title>
  <style>
    :root { --bg:#f4f6f8; --card:#fff; --accent:#2563eb; --danger:#dc2626; --success:#16a34a; --warn:#ea580c; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif; background:var(--bg); color:#111; }
    header { background:var(--card); border-bottom:1px solid #e5e7eb; padding:1.25rem 2rem; display:flex; align-items:center; justify-content:space-between; }
    header h1 { margin:0; font-size:1.25rem; }
    .container { max-width:1100px; margin:2rem auto; padding:0 1rem; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:1rem; margin-bottom:2rem; }
    .card { background:var(--card); border-radius:.75rem; padding:1.25rem; box-shadow:0 1px 2px rgba(0,0,0,.05); }
    .card h2 { margin:0 0 .75rem; font-size:1rem; color:#374151; }
    .metric { font-size:1.75rem; font-weight:700; color:var(--accent); }
    .metric.down { color:var(--danger); }
    table { width:100%; border-collapse:collapse; font-size:.9rem; }
    th,td { text-align:left; padding:.6rem .5rem; border-bottom:1px solid #e5e7eb; }
    th { color:#6b7280; font-weight:500; text-transform:uppercase; font-size:.75rem; letter-spacing:.03em; }
    tr:last-child td { border-bottom:none; }
    .badge { display:inline-block; padding:.15rem .5rem; border-radius:999px; font-size:.75rem; font-weight:600; }
    .badge.up { background:#dcfce7; color:var(--success); }
    .badge.down { background:#fee2e2; color:var(--danger); }
    .badge.failover { background:#ffedd5; color:var(--warn); }
    .mono { font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace; font-size:.85rem; }
    .events { max-height:320px; overflow:auto; }
  </style>
</head>
<body>
  <header>
    <h1>🏫 Secure Campus Fabric</h1>
    <div class="mono" style="color:#6b7280;font-size:.9rem;">{{ now }}</div>
  </header>
  <div class="container">
    <div class="grid">
      <div class="card">
        <h2>Branches</h2>
        <div class="metric">{{ branches|length }}</div>
      </div>
      <div class="card">
        <h2>Tunnels Up</h2>
        <div class="metric {{ 'down' if up_count < branches|length else '' }}">{{ up_count }} / {{ branches|length }}</div>
      </div>
      <div class="card">
        <h2>Recent Events</h2>
        <div class="metric">{{ events|length }}</div>
      </div>
    </div>

    <div class="card">
      <h2>Tunnel State</h2>
      <table>
        <thead>
          <tr><th>Branch</th><th>Status</th><th>Active Link</th><th>Latency</th><th>Last Check</th></tr>
        </thead>
        <tbody>
          {% for b in branches %}
          <tr>
            <td><strong>{{ b.name }}</strong></td>
            <td><span class="badge {{ 'up' if b.status=='UP' else 'down' }}">{{ b.status }}</span></td>
            <td>
              {{ b.link }}
              {% if b.link_state=='backup' %}<span class="badge failover">FAILOVER</span>{% endif %}
            </td>
            <td>{{ b.latency_ms|round(1) if b.latency_ms else '—' }} ms</td>
            <td class="mono">{{ b.checked_at[11:19] if b.checked_at else '—' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card events">
      <h2>Recent Events</h2>
      <table>
        <thead>
          <tr><th>Time</th><th>Branch</th><th>Type</th><th>Message</th></tr>
        </thead>
        <tbody>
          {% for e in events %}
          <tr>
            <td class="mono">{{ e.timestamp[11:19] }}</td>
            <td>{{ e.branch }}</td>
            <td><span class="badge {{ 'down' if 'DOWN' in e.type else 'up' if 'UP' in e.type else 'failover' }}">{{ e.type }}</span></td>
            <td>{{ e.message }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>
"""


def _load_json(path):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


@app.route("/")
def index():
    state = _load_json(LOGS_DIR / "tunnel_state.json")
    events = _load_json(LOGS_DIR / "events.json")
    branches = list(state.values())
    branches.sort(key=lambda x: x.get("name", ""))
    events = sorted(events, key=lambda x: x.get("timestamp", ""), reverse=True)[:50]
    up_count = sum(1 for b in branches if b.get("status") == "UP")
    return render_template_string(
        HTML, branches=branches, events=events,
        up_count=up_count, now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


@app.route("/api/state")
def api_state():
    return jsonify(_load_json(LOGS_DIR / "tunnel_state.json"))


@app.route("/api/events")
def api_events():
    return jsonify(_load_json(LOGS_DIR / "events.json"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
