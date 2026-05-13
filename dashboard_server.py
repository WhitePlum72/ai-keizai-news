"""
AI経済新聞 ローカル管理ダッシュボード
起動: python dashboard_server.py
ブラウザ: http://localhost:5555
"""

import sqlite3
import subprocess
import threading
import os
import sys
import json
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ============================================================
# 設定（環境に合わせて変更）
# ============================================================
PROJECT_ROOT = r"C:\Users\info\Desktop\dev\tools\projects\ai-daily-jp"
DB_PATH      = os.path.join(PROJECT_ROOT, "articles.db")   # DBファイル名が違う場合は変更
PYTHON_EXE   = r"C:\Users\info\AppData\Local\Programs\Python\Python311\python.exe"
PORT         = 5555
DB_TABLE     = "articles"   # テーブル名が違う場合は変更
DATE_COL     = "published_at"  # 日付カラム名
# ============================================================

running_tasks = {}  # タスクの実行状態を管理


def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_stats():
    from datetime import timezone
    JST_OFFSET = timedelta(hours=9)
    now = datetime.utcnow() + JST_OFFSET
    today = now.date()
    yesterday = today - timedelta(days=1)

    week_start   = today - timedelta(days=today.weekday())
    prev_week_start = week_start - timedelta(weeks=1)
    prev_week_end   = week_start - timedelta(days=1)

    month_start      = today.replace(day=1)
    prev_month_end   = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    try:
        conn = db_connect()
        cur  = conn.cursor()

        def count(d_from, d_to):
            cur.execute(
                f"SELECT COUNT(*) FROM {DB_TABLE} WHERE DATE({DATE_COL}) >= ? AND DATE({DATE_COL}) <= ?",
                (str(d_from), str(d_to))
            )
            return cur.fetchone()[0]

        today_n      = count(today,           today)
        yesterday_n  = count(yesterday,       yesterday)
        week_n       = count(week_start,      today)
        prev_week_n  = count(prev_week_start, prev_week_end)
        month_n      = count(month_start,     today)
        prev_month_n = count(prev_month_start, prev_month_end)

        cur.execute(f"SELECT COUNT(*) FROM {DB_TABLE}")
        total = cur.fetchone()[0]

        cur.execute(f"""
            SELECT title, category_slug, {DATE_COL}, buzz_score, source, source_label
            FROM {DB_TABLE}
            ORDER BY {DATE_COL} DESC
            LIMIT 30
        """)
        recent = [dict(r) for r in cur.fetchall()]

        cur.execute(f"""
            SELECT category_slug, COUNT(*) as cnt
            FROM {DB_TABLE}
            WHERE DATE({DATE_COL}) = ?
            GROUP BY category_slug
            ORDER BY cnt DESC
        """, (str(today),))
        cat_today = [dict(r) for r in cur.fetchall()]

        cur.execute(f"""
            SELECT DATE({DATE_COL}) as d, COUNT(*) as cnt
            FROM {DB_TABLE}
            WHERE DATE({DATE_COL}) >= ?
            GROUP BY d
            ORDER BY d
        """, (str(today - timedelta(days=13)),))
        daily_14 = [dict(r) for r in cur.fetchall()]

        conn.close()

        return {
            "ok": True,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S JST"),
            "today": today_n,
            "yesterday": yesterday_n,
            "today_diff": today_n - yesterday_n,
            "week": week_n,
            "prev_week": prev_week_n,
            "week_diff": week_n - prev_week_n,
            "month": month_n,
            "prev_month": prev_month_n,
            "month_diff": month_n - prev_month_n,
            "total": total,
            "recent": recent,
            "cat_today": cat_today,
            "daily_14": daily_14,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_script(name, script):
    """バックグラウンドでスクリプトを実行"""
    if running_tasks.get(name):
        return {"ok": False, "msg": f"{name} は既に実行中です"}

    def worker():
        running_tasks[name] = True
        try:
            subprocess.run(
                [PYTHON_EXE, os.path.join(PROJECT_ROOT, script)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
        finally:
            running_tasks[name] = False

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return {"ok": True, "msg": f"{name} を開始しました"}


# ============================================================
# HTML
# ============================================================
HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI経済新聞 ダッシュボード</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Noto+Sans+JP:wght@400;700;900&display=swap');

  :root {
    --bg:      #0a0c10;
    --surface: #111418;
    --border:  #1e2530;
    --accent:  #00d4ff;
    --green:   #00e676;
    --red:     #ff4444;
    --yellow:  #ffd740;
    --text:    #e2e8f0;
    --muted:   #64748b;
    --mono:    'JetBrains Mono', monospace;
    --sans:    'Noto Sans JP', sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--sans); font-size: 14px; min-height: 100vh; }
  a { color: var(--accent); text-decoration: none; }

  /* ヘッダー */
  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 14px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky; top: 0; z-index: 100;
  }
  .logo { font-family: var(--mono); font-size: 15px; font-weight: 700; color: var(--accent); letter-spacing: .05em; }
  .logo span { color: var(--muted); font-weight: 400; }
  #clock { font-family: var(--mono); font-size: 12px; color: var(--muted); }
  #status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); display: inline-block; margin-right: 6px; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

  /* レイアウト */
  .wrap { max-width: 1400px; margin: 0 auto; padding: 20px 20px 40px; }
  .grid-4 { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 20px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
  .grid-3 { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 20px; }

  /* KPIカード */
  .kpi {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
  }
  .kpi::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--accent);
  }
  .kpi-label { font-size: 11px; color: var(--muted); font-family: var(--mono); letter-spacing: .08em; text-transform: uppercase; margin-bottom: 10px; }
  .kpi-val { font-size: 38px; font-weight: 900; font-family: var(--mono); color: var(--text); line-height: 1; margin-bottom: 8px; }
  .kpi-sub { font-size: 11px; color: var(--muted); display: flex; align-items: center; gap: 6px; }
  .diff-pos { color: var(--green); font-weight: 700; }
  .diff-neg { color: var(--red); font-weight: 700; }
  .diff-zero { color: var(--muted); }
  .kpi.total::before { background: var(--yellow); }

  /* パネル */
  .panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }
  .panel-head {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    font-family: var(--mono);
    color: var(--accent);
    font-weight: 700;
    letter-spacing: .06em;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .panel-body { padding: 14px 16px; }

  /* 棒グラフ */
  .bar-chart { display: flex; flex-direction: column; gap: 6px; }
  .bar-row { display: flex; align-items: center; gap: 8px; }
  .bar-label { font-size: 11px; color: var(--muted); font-family: var(--mono); width: 80px; flex-shrink: 0; text-align: right; }
  .bar-track { flex: 1; background: var(--border); border-radius: 2px; height: 14px; overflow: hidden; }
  .bar-fill { height: 100%; background: var(--accent); border-radius: 2px; transition: width .6s ease; }
  .bar-count { font-size: 11px; font-family: var(--mono); color: var(--text); width: 28px; text-align: right; }

  /* ミニ折れ線グラフ */
  .sparkline-wrap { position: relative; }
  svg.spark { width: 100%; height: 80px; overflow: visible; }

  /* カテゴリドーナツ代替：水平バー */
  .cat-bar { display: flex; flex-direction: column; gap: 8px; padding: 4px 0; }
  .cat-row { display: flex; align-items: center; gap: 10px; }
  .cat-name { width: 90px; font-size: 11px; color: var(--muted); flex-shrink: 0; }
  .cat-track { flex: 1; background: var(--border); border-radius: 2px; height: 10px; }
  .cat-fill { height: 100%; border-radius: 2px; }
  .cat-n { font-size: 11px; font-family: var(--mono); width: 24px; text-align: right; }
  .cat-colors { model:'#003f88', business:'#c0392b', markets:'#b7770d', infrastructure:'#2e7d32', research:'#6a1b9a', policy:'#00695c', products:'#0277bd' }

  /* ボタングループ */
  .btn-group { display: flex; flex-wrap: wrap; gap: 8px; }
  .btn {
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 700;
    padding: 9px 16px;
    border-radius: 5px;
    border: 1px solid var(--border);
    background: var(--border);
    color: var(--text);
    cursor: pointer;
    letter-spacing: .04em;
    transition: all .15s;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .btn:hover { background: var(--accent); color: #000; border-color: var(--accent); }
  .btn.running { background: var(--yellow); color: #000; border-color: var(--yellow); animation: pulse 1s infinite; }
  .btn.trigger { border-color: var(--green); color: var(--green); }
  .btn.trigger:hover { background: var(--green); color: #000; }
  .btn.pipeline { border-color: var(--accent); color: var(--accent); }
  .btn.pipeline:hover { background: var(--accent); color: #000; }
  .btn.danger { border-color: var(--red); color: var(--red); }
  .btn.danger:hover { background: var(--red); color: #fff; }

  /* ログ */
  #log {
    background: #050709;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--green);
    height: 100px;
    overflow-y: auto;
    margin-top: 12px;
    line-height: 1.6;
  }

  /* 記事リスト */
  .art-list { display: flex; flex-direction: column; }
  .art-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 9px 16px;
    border-bottom: 1px solid var(--border);
    transition: background .1s;
  }
  .art-item:hover { background: #141820; }
  .art-item:last-child { border-bottom: none; }
  .art-cat {
    font-size: 9px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 3px;
    color: #fff;
    flex-shrink: 0;
    margin-top: 2px;
    font-family: var(--mono);
  }
  .art-title { font-size: 12px; line-height: 1.5; flex: 1; }
  .art-meta { font-size: 10px; color: var(--muted); font-family: var(--mono); flex-shrink: 0; text-align: right; }
  .score { color: var(--yellow); }

  /* GA placeholder */
  .ga-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 120px;
    color: var(--muted);
    font-family: var(--mono);
    font-size: 12px;
    flex-direction: column;
    gap: 8px;
  }
  .ga-note { font-size: 10px; color: var(--border); }

  /* トースト */
  #toast {
    position: fixed;
    bottom: 24px; right: 24px;
    background: var(--surface);
    border: 1px solid var(--accent);
    border-radius: 6px;
    padding: 12px 18px;
    font-family: var(--mono);
    font-size: 12px;
    color: var(--accent);
    opacity: 0;
    transition: opacity .3s;
    z-index: 9999;
  }
  #toast.show { opacity: 1; }

  @media (max-width: 900px) {
    .grid-4 { grid-template-columns: repeat(2,1fr); }
    .grid-2, .grid-3 { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<header>
  <div class="logo">AI経済新聞 <span>/ OPS DASHBOARD</span></div>
  <div style="display:flex;align-items:center;gap:16px;">
    <span><span id="status-dot"></span><span id="status-txt" style="font-size:12px;color:var(--muted);">接続中...</span></span>
    <span id="clock"></span>
    <button class="btn" onclick="loadStats()" style="padding:6px 12px;">⟳ 更新</button>
  </div>
</header>

<div class="wrap">

  <!-- KPI 4枚 -->
  <div class="grid-4" id="kpi-area">
    <div class="kpi"><div class="kpi-label">TODAY</div><div class="kpi-val" id="k-today">—</div><div class="kpi-sub" id="k-today-sub">前日比 —</div></div>
    <div class="kpi"><div class="kpi-label">THIS WEEK</div><div class="kpi-val" id="k-week">—</div><div class="kpi-sub" id="k-week-sub">前週比 —</div></div>
    <div class="kpi"><div class="kpi-label">THIS MONTH</div><div class="kpi-val" id="k-month">—</div><div class="kpi-sub" id="k-month-sub">前月比 —</div></div>
    <div class="kpi total"><div class="kpi-label">TOTAL</div><div class="kpi-val" id="k-total">—</div><div class="kpi-sub">累計公開記事数</div></div>
  </div>

  <!-- スパークライン + カテゴリ -->
  <div class="grid-3">
    <div class="panel">
      <div class="panel-head">📈 過去14日間 公開本数</div>
      <div class="panel-body">
        <div class="sparkline-wrap">
          <svg class="spark" id="spark-svg" viewBox="0 0 600 80" preserveAspectRatio="none"></svg>
        </div>
        <div id="spark-labels" style="display:flex;justify-content:space-between;margin-top:4px;font-size:10px;color:var(--muted);font-family:var(--mono);"></div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-head">🗂 本日カテゴリ別</div>
      <div class="panel-body">
        <div class="cat-bar" id="cat-bar"></div>
      </div>
    </div>
  </div>

  <!-- パイプライン操作 + PV -->
  <div class="grid-2">
    <div class="panel">
      <div class="panel-head">⚙️ パイプライン操作</div>
      <div class="panel-body">
        <div class="btn-group">
          <button class="btn trigger" id="btn-trigger" onclick="runTask('trigger','trigger_check.py')">⚡ トリガーチェック</button>
          <button class="btn pipeline" id="btn-collect" onclick="runTask('collect','collector.py')">📡 collector</button>
          <button class="btn pipeline" id="btn-score"   onclick="runTask('score','scorer.py')">📊 scorer</button>
          <button class="btn pipeline" id="btn-trans"   onclick="runTask('trans','translator.py')">✍️ translator</button>
          <button class="btn pipeline" id="btn-pub"     onclick="runTask('pub','publisher.py')">🚀 publisher</button>
          <button class="btn danger"   id="btn-full"    onclick="runFull()">▶▶ フル実行</button>
        </div>
        <div id="log">// ログ出力エリア</div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-head">📊 PV数（Google Analytics）
        <span style="font-size:10px;color:var(--muted);">GA Data API</span>
      </div>
      <div class="panel-body">
        <div class="ga-placeholder">
          <div>🔗 GA Data API 未接続</div>
          <div class="ga-note">setup手順: README_GA.md を参照</div>
          <div style="margin-top:12px;" id="ga-data"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- 最新記事 -->
  <div class="panel">
    <div class="panel-head">📰 最新公開記事 <span id="art-count" style="font-size:10px;color:var(--muted);"></span></div>
    <div class="art-list" id="art-list"></div>
  </div>

</div>

<div id="toast"></div>

<script>
const CAT_COLOR = {
  model:'#003f88', business:'#c0392b', markets:'#b7770d',
  infrastructure:'#2e7d32', research:'#6a1b9a', policy:'#00695c', products:'#0277bd'
};
const CAT_JP = {
  model:'モデル', business:'ビジネス', markets:'AI関連株',
  infrastructure:'インフラ', research:'研究', policy:'政策', products:'プロダクト'
};

function toast(msg, err=false) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.borderColor = err ? 'var(--red)' : 'var(--accent)';
  el.style.color = err ? 'var(--red)' : 'var(--accent)';
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
}

function log(msg) {
  const el = document.getElementById('log');
  const ts = new Date().toLocaleTimeString('ja-JP');
  el.innerHTML += `<div>[${ts}] ${msg}</div>`;
  el.scrollTop = el.scrollHeight;
}

function diff(n) {
  if (n > 0) return `<span class="diff-pos">+${n}</span>`;
  if (n < 0) return `<span class="diff-neg">${n}</span>`;
  return `<span class="diff-zero">±0</span>`;
}

async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const d = await res.json();
    if (!d.ok) { document.getElementById('status-txt').textContent = 'DBエラー: ' + d.error; return; }

    document.getElementById('status-txt').textContent = d.timestamp;

    // KPI
    document.getElementById('k-today').textContent = d.today;
    document.getElementById('k-today-sub').innerHTML = `前日(${d.yesterday}本) ${diff(d.today_diff)}`;
    document.getElementById('k-week').textContent = d.week;
    document.getElementById('k-week-sub').innerHTML = `前週(${d.prev_week}本) ${diff(d.week_diff)}`;
    document.getElementById('k-month').textContent = d.month;
    document.getElementById('k-month-sub').innerHTML = `前月(${d.prev_month}本) ${diff(d.month_diff)}`;
    document.getElementById('k-total').textContent = d.total.toLocaleString();

    // スパークライン
    drawSparkline(d.daily_14);

    // カテゴリ別
    const catEl = document.getElementById('cat-bar');
    catEl.innerHTML = '';
    const maxCat = Math.max(...d.cat_today.map(c => c.cnt), 1);
    d.cat_today.forEach(c => {
      const pct = Math.round(c.cnt / maxCat * 100);
      const color = CAT_COLOR[c.category_slug] || '#555';
      const jp = CAT_JP[c.category_slug] || c.category_slug;
      catEl.innerHTML += `
        <div class="cat-row">
          <div class="cat-name">${jp}</div>
          <div class="cat-track"><div class="cat-fill" style="width:${pct}%;background:${color}"></div></div>
          <div class="cat-n">${c.cnt}</div>
        </div>`;
    });
    if (!d.cat_today.length) catEl.innerHTML = '<div style="color:var(--muted);font-size:12px;">本日のデータなし</div>';

    // 記事リスト
    const artEl = document.getElementById('art-list');
    document.getElementById('art-count').textContent = `直近${d.recent.length}件`;
    artEl.innerHTML = '';
    d.recent.forEach(a => {
      const color = CAT_COLOR[a.category_slug] || '#555';
      const jp = CAT_JP[a.category_slug] || a.category_slug || '';
      const dt = a[Object.keys(a).find(k=>k.includes('published'))||'published_at'] || '';
      const score = a.buzz_score || 0;
      const date = dt ? dt.slice(0,16).replace('T',' ') : '';
      artEl.innerHTML += `
        <div class="art-item">
          <span class="art-cat" style="background:${color}">${jp}</span>
          <span class="art-title">${a.title || ''}</span>
          <span class="art-meta"><span class="score">🔥${score}</span><br>${date}</span>
        </div>`;
    });
  } catch(e) {
    document.getElementById('status-txt').textContent = '接続失敗';
  }
}

function drawSparkline(data) {
  const svg = document.getElementById('spark-svg');
  const labEl = document.getElementById('spark-labels');
  if (!data || !data.length) return;

  const max = Math.max(...data.map(d=>d.cnt), 1);
  const W = 600, H = 70, PAD = 10;
  const xStep = (W - PAD*2) / Math.max(data.length-1, 1);

  const pts = data.map((d,i) => {
    const x = PAD + i * xStep;
    const y = H - PAD - (d.cnt / max) * (H - PAD*2);
    return [x, y];
  });

  const polyline = pts.map(p=>p.join(',')).join(' ');
  const areaPath = `M${pts[0][0]},${H} ` + pts.map(p=>`L${p[0]},${p[1]}`).join(' ') + ` L${pts[pts.length-1][0]},${H} Z`;

  svg.innerHTML = `
    <defs>
      <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#00d4ff" stop-opacity=".3"/>
        <stop offset="100%" stop-color="#00d4ff" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <path d="${areaPath}" fill="url(#grad)"/>
    <polyline points="${polyline}" fill="none" stroke="#00d4ff" stroke-width="2" stroke-linejoin="round"/>
    ${pts.map((p,i)=>`<circle cx="${p[0]}" cy="${p[1]}" r="3" fill="#00d4ff"/>`).join('')}
    ${pts.map((p,i)=>`<text x="${p[0]}" y="${p[1]-8}" text-anchor="middle" font-size="9" fill="#94a3b8" font-family="JetBrains Mono,monospace">${data[i].cnt}</text>`).join('')}
  `;

  // 日付ラベル（最初・中間・最後）
  labEl.innerHTML = '';
  [0, Math.floor(data.length/2), data.length-1].forEach(i => {
    if (data[i]) labEl.innerHTML += `<span>${data[i].d.slice(5)}</span>`;
  });
}

const taskNames = {
  trigger:'トリガーチェック', collect:'collector', score:'scorer', trans:'translator', pub:'publisher'
};
const taskBtns = {
  trigger:'btn-trigger', collect:'btn-collect', score:'btn-score', trans:'btn-trans', pub:'btn-pub'
};

async function runTask(name, script) {
  const btn = document.getElementById(taskBtns[name]);
  btn.classList.add('running');
  btn.disabled = true;
  log(`▶ ${taskNames[name]} 開始...`);
  toast(`▶ ${taskNames[name]} 実行中`);
  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({script})
    });
    const d = await res.json();
    log(d.msg);
    toast(d.msg, !d.ok);
    setTimeout(() => { btn.classList.remove('running'); btn.disabled = false; loadStats(); }, 8000);
  } catch(e) {
    log('エラー: ' + e.message);
    btn.classList.remove('running');
    btn.disabled = false;
  }
}

async function runFull() {
  const scripts = ['collector.py','scorer.py','translator.py','publisher.py'];
  const btn = document.getElementById('btn-full');
  btn.classList.add('running');
  btn.disabled = true;
  log('▶▶ フルパイプライン開始...');
  try {
    const res = await fetch('/api/run_full', { method:'POST' });
    const d = await res.json();
    log(d.msg);
    toast(d.msg, !d.ok);
    setTimeout(() => { btn.classList.remove('running'); btn.disabled = false; loadStats(); }, 30000);
  } catch(e) {
    log('エラー: ' + e.message);
    btn.classList.remove('running');
    btn.disabled = false;
  }
}

// 時計
setInterval(() => {
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('ja-JP', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
}, 1000);

// 自動更新（30秒）
loadStats();
setInterval(loadStats, 30000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # アクセスログ抑制

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/stats":
            self.send_json(get_stats())
        else:
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw) if raw else {}
        except Exception:
            data = {}

        if path == "/api/run":
            script = data.get("script", "")
            if not script:
                self.send_json({"ok": False, "msg": "script未指定"})
                return
            name = script.replace(".py", "")
            result = run_script(name, script)
            self.send_json(result)

        elif path == "/api/run_full":
            def full_pipeline():
                for s in ["collector.py", "scorer.py", "translator.py", "publisher.py"]:
                    name = s.replace(".py", "")
                    if running_tasks.get(name):
                        continue
                    running_tasks[name] = True
                    try:
                        subprocess.run(
                            [PYTHON_EXE, os.path.join(PROJECT_ROOT, s)],
                            cwd=PROJECT_ROOT,
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            errors="replace"
                        )
                    finally:
                        running_tasks[name] = False

            t = threading.Thread(target=full_pipeline, daemon=True)
            t.start()
            self.send_json({"ok": True, "msg": "フルパイプライン開始（バックグラウンド実行中）"})

        else:
            self.send_json({"ok": False, "msg": "not found"}, 404)


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"[警告] DBが見つかりません: {DB_PATH}")
        print("DB_PATH を正しく設定してください（dashboard_server.py 冒頭）")

    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"✅ ダッシュボード起動: http://localhost:{PORT}")
    print("Ctrl+C で停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました")
