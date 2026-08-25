"""
סקריפט עצמאי (ללא תלות בקבצים מקומיים) שמוריד את נתוני הלוטו העדכניים
ממפעל הפיס, מחשב סטטיסטיקות, ובונה report.html. מיועד לריצה בסביבת ענן.
"""
import base64
import csv
import datetime
import io
import random

import requests

CSV_URL = "https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx"
OUT_PATH = "report.html"

REGULAR_RANGE = range(1, 38)
STRONG_RANGE = range(1, 8)
CURRENT_FORMAT_START_DATE = datetime.date(2011, 3, 5)

ICON_B64 = "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"


def fetch():
    resp = requests.get(CSV_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.raise_for_status()
    return resp.content.decode("cp1255")


def parse_and_filter(text):
    rows = []
    for line in text.splitlines()[1:]:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 9:
            continue
        try:
            draw_id = int(parts[0])
            day, month, year = parts[1].split("/")
            date = datetime.date(int(year), int(month), int(day))
            nums = [int(x) for x in parts[2:8]]
            strong = int(parts[8])
        except ValueError:
            continue
        if date < CURRENT_FORMAT_START_DATE:
            continue
        assert all(1 <= n <= 37 for n in nums), line
        assert 1 <= strong <= 7, line
        rows.append({"draw_id": draw_id, "date": date, "numbers": nums, "strong": strong})
    rows.sort(key=lambda r: r["date"])
    return rows


def compute_stats(rows):
    n_draws = len(rows)
    reg_count = {n: 0 for n in REGULAR_RANGE}
    reg_last_seen_idx = {n: None for n in REGULAR_RANGE}
    strong_count = {n: 0 for n in STRONG_RANGE}
    strong_last_seen_idx = {n: None for n in STRONG_RANGE}

    for idx, r in enumerate(rows):
        for n in r["numbers"]:
            reg_count[n] += 1
            reg_last_seen_idx[n] = idx
        strong_count[r["strong"]] += 1
        strong_last_seen_idx[r["strong"]] = idx

    reg_gap = {n: (n_draws - 1 - reg_last_seen_idx[n]) if reg_last_seen_idx[n] is not None else n_draws
               for n in REGULAR_RANGE}
    reg_last_date = {n: (rows[reg_last_seen_idx[n]]["date"] if reg_last_seen_idx[n] is not None else None)
                      for n in REGULAR_RANGE}

    hottest = sorted(REGULAR_RANGE, key=lambda n: (-reg_count[n], n))
    coldest = sorted(REGULAR_RANGE, key=lambda n: (reg_count[n], n))
    most_overdue = sorted(REGULAR_RANGE, key=lambda n: (-reg_gap[n], n))

    return {
        "n_draws": n_draws,
        "first_date": rows[0]["date"],
        "last_date": rows[-1]["date"],
        "reg_count": reg_count,
        "reg_gap": reg_gap,
        "reg_last_date": reg_last_date,
        "strong_count": strong_count,
        "hottest": hottest,
        "coldest": coldest,
        "most_overdue": most_overdue,
    }


def _one_pick(rng, stats):
    weights = [stats["reg_count"][n] for n in REGULAR_RANGE]
    pool = list(REGULAR_RANGE)
    picked = []
    w = weights[:]
    while len(picked) < 6:
        total = sum(w)
        r = rng.uniform(0, total)
        acc = 0
        for i, n in enumerate(pool):
            acc += w[i]
            if acc >= r:
                picked.append(n)
                del pool[i]
                del w[i]
                break
    picked.sort()
    strong_weights = [stats["strong_count"][n] for n in STRONG_RANGE]
    strong_pick = rng.choices(list(STRONG_RANGE), weights=strong_weights, k=1)[0]
    return picked, strong_pick


def suggest_picks(stats, count=10, seed=None):
    rng = random.Random(seed)
    picks, seen, attempts = [], set(), 0
    while len(picks) < count and attempts < count * 20:
        attempts += 1
        picked, strong_pick = _one_pick(rng, stats)
        key = (tuple(picked), strong_pick)
        if key in seen:
            continue
        seen.add(key)
        picks.append((picked, strong_pick))
    return picks


def bar_chart_svg(counts, value_range, chart_id, width=900, height=260, highlight=None):
    highlight = highlight or set()
    n = len(value_range)
    margin_left, margin_right, margin_top, margin_bottom = 36, 12, 16, 28
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    max_v = max(counts.values()) if counts else 1
    bar_gap = 4
    bar_w = (plot_w - bar_gap * (n - 1)) / n

    bars = []
    for i, val in enumerate(value_range):
        c = counts[val]
        bar_h = (c / max_v) * plot_h if max_v else 0
        x = margin_left + i * (bar_w + bar_gap)
        y = margin_top + (plot_h - bar_h)
        cls = "bar bar-hot" if val in highlight else "bar"
        bars.append(
            f'<rect class="{cls}" data-num="{val}" data-count="{c}" '
            f'x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{max(bar_h,1):.2f}" rx="3"></rect>'
        )
        if n <= 40:
            label_x = x + bar_w / 2
            bars.append(
                f'<text class="bar-axis-label" x="{label_x:.2f}" y="{height - margin_bottom + 16}" '
                f'text-anchor="middle">{val}</text>'
            )

    gridlines = []
    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        y = margin_top + plot_h * (1 - frac)
        gridlines.append(f'<line class="gridline" x1="{margin_left}" x2="{width - margin_right}" y1="{y:.2f}" y2="{y:.2f}"></line>')
        gridlines.append(f'<text class="bar-axis-label" x="{margin_left - 8}" y="{y+4:.2f}" text-anchor="end">{round(max_v*frac)}</text>')

    return f'''<svg class="bar-chart" id="{chart_id}" viewBox="0 0 {width} {height}" role="img" aria-label="תרשים תדירות מספרים">
  {''.join(gridlines)}
  {''.join(bars)}
</svg>'''


def fmt_date(d):
    return d.strftime("%d/%m/%Y")


def render_html(stats, picks):
    icon_tags = (
        f'<link rel="apple-touch-icon" href="data:image/png;base64,{ICON_B64}">\n'
        f'<link rel="icon" type="image/png" href="data:image/png;base64,{ICON_B64}">'
    )

    reg_svg = bar_chart_svg(stats["reg_count"], list(REGULAR_RANGE), "chart-regular", highlight=set(stats["hottest"][:6]))
    strong_svg = bar_chart_svg(stats["strong_count"], list(STRONG_RANGE), "chart-strong", width=420,
                                highlight={stats["hottest"][0]} & set(STRONG_RANGE))

    def hot_cold_rows(nums, extra_label):
        return "".join(
            f'<tr><td class="num-cell"><span class="num-pill">{n}</span></td>'
            f'<td>{stats["reg_count"][n]}</td><td>{extra_label(n)}</td></tr>'
            for n in nums
        )

    hot_rows = hot_cold_rows(stats["hottest"][:10], lambda n: fmt_date(stats["reg_last_date"][n]))
    cold_rows = hot_cold_rows(stats["coldest"][:10], lambda n: fmt_date(stats["reg_last_date"][n]))
    overdue_rows = hot_cold_rows(stats["most_overdue"][:10], lambda n: f'{stats["reg_gap"][n]} הגרלות')

    picks_rows = []
    for i, (pick, strong_pick) in enumerate(picks, start=1):
        nums_html = "".join(f'<span class="num-pill">{n}</span>' for n in pick)
        strong_pill = f'<span class="num-pill num-pill-strong">{strong_pick}</span>'
        picks_rows.append(
            f'<div class="pick-row"><span class="pick-idx">#{i}</span>'
            f'<span class="pick-nums">{nums_html}<span class="pick-plus">+</span>{strong_pill}</span></div>'
        )
    picks_html = "".join(picks_rows)

    updated_stamp = datetime.date.today().strftime("%d/%m/%Y")

    html = f'''<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>סטטיסטיקת הגרלות הלוטו</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#2a78d6">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="לוטו סטטיסטיקה">
{icon_tags}
<style>
  .viz-root {{
    color-scheme: light;
    --surface-1:      #fcfcfb;
    --page:           #f9f9f7;
    --text-primary:   #0b0b0b;
    --text-secondary: #52514e;
    --text-muted:     #898781;
    --gridline:       #e1e0d9;
    --baseline:       #c3c2b7;
    --series-1:       #2a78d6;
    --series-1-dark:  #1c5cab;
    --series-hot:     #eb6834;
    --border:         rgba(11,11,11,0.10);
    --card:           #ffffff;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:where(:not([data-theme="light"])) .viz-root {{
      color-scheme: dark;
      --surface-1:      #1a1a19;
      --page:           #0d0d0d;
      --text-primary:   #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted:     #898781;
      --gridline:       #2c2c2a;
      --baseline:       #383835;
      --series-1:       #3987e5;
      --series-1-dark:  #184f95;
      --series-hot:     #d95926;
      --border:         rgba(255,255,255,0.10);
      --card:           #202020;
    }}
  }}
  :root[data-theme="dark"] .viz-root {{
    color-scheme: dark;
    --surface-1:      #1a1a19;
    --page:           #0d0d0d;
    --text-primary:   #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted:     #898781;
    --gridline:       #2c2c2a;
    --baseline:       #383835;
    --series-1:       #3987e5;
    --series-1-dark:  #184f95;
    --series-hot:     #d95926;
    --border:         rgba(255,255,255,0.10);
    --card:           #202020;
  }}

  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: system-ui, -apple-system, "Segoe UI", Arial, sans-serif;
    background: var(--page);
    color: var(--text-primary);
  }}
  .wrap {{ max-width: 1000px; margin: 0 auto; padding: 32px 20px 80px; }}
  h1 {{ font-size: 1.6rem; margin: 0 0 4px; }}
  .subtitle {{ color: var(--text-secondary); margin: 0 0 24px; font-size: 0.95rem; }}
  .disclaimer {{
    background: var(--card);
    border: 1px solid var(--border);
    border-right: 4px solid var(--series-hot);
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 28px;
    font-size: 0.92rem;
    color: var(--text-secondary);
    line-height: 1.6;
  }}
  .disclaimer strong {{ color: var(--text-primary); }}

  .tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 28px; }}
  .tile {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
  }}
  .tile .value {{ font-size: 1.5rem; font-weight: 600; }}
  .tile .label {{ font-size: 0.8rem; color: var(--text-muted); margin-top: 2px; }}

  section {{ margin-bottom: 36px; }}
  h2 {{ font-size: 1.15rem; margin: 0 0 4px; }}
  .section-desc {{ color: var(--text-secondary); font-size: 0.88rem; margin: 0 0 14px; }}

  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px;
  }}

  .bar-chart {{ width: 100%; height: auto; overflow: visible; }}
  .bar {{ fill: var(--series-1); cursor: pointer; transition: fill 0.1s; }}
  .bar:hover {{ fill: var(--series-1-dark); }}
  .bar-hot {{ fill: var(--series-hot); }}
  .bar-axis-label {{ fill: var(--text-muted); font-size: 10px; }}
  .gridline {{ stroke: var(--gridline); stroke-width: 1; }}

  .tooltip {{
    position: fixed;
    pointer-events: none;
    background: var(--text-primary);
    color: var(--page);
    font-size: 0.8rem;
    padding: 6px 10px;
    border-radius: 6px;
    opacity: 0;
    transform: translate(-50%, -110%);
    transition: opacity 0.08s;
    white-space: nowrap;
    z-index: 10;
  }}
  .tooltip.show {{ opacity: 1; }}

  .tables {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
  th {{ text-align: right; color: var(--text-muted); font-weight: 500; font-size: 0.78rem; padding: 4px 6px; border-bottom: 1px solid var(--gridline); }}
  td {{ padding: 6px; border-bottom: 1px solid var(--gridline); }}
  .num-cell {{ width: 44px; }}
  .num-pill {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 50%;
    background: var(--series-1); color: #fff; font-weight: 600; font-size: 0.85rem;
  }}
  .num-pill-strong {{ background: var(--series-hot); }}

  .pick-plus {{ color: var(--text-muted); margin: 0 6px; font-size: 1.2rem; }}
  .picks-list {{ display: flex; flex-direction: column; gap: 10px; }}
  .pick-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 8px 4px; border-bottom: 1px solid var(--gridline);
  }}
  .pick-row:last-child {{ border-bottom: none; }}
  .pick-idx {{ color: var(--text-muted); font-size: 0.85rem; width: 28px; flex-shrink: 0; }}
  .pick-nums {{ display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }}

  footer {{ color: var(--text-muted); font-size: 0.8rem; margin-top: 40px; line-height: 1.7; }}
  footer a {{ color: var(--text-secondary); }}
</style>
</head>
<body>
<div class="viz-root">
<div class="wrap">
  <h1>סטטיסטיקת הגרלות הלוטו הישראלי</h1>
  <p class="subtitle">מבוסס על {stats['n_draws']} הגרלות בפורמט הנוכחי (6 מתוך 1–37 + מספר חזק 1–7), מ-{fmt_date(stats['first_date'])} עד {fmt_date(stats['last_date'])}. מקור: ארכיון מפעל הפיס. עודכן אוטומטית ב-{updated_stamp}.</p>

  <div class="disclaimer">
    <strong>חשוב:</strong> הגרלת הלוטו היא אירוע אקראי לחלוטין ובלתי תלוי בהגרלות
    קודמות — לכל מספר יש בכל הגרלה בדיוק אותו סיכוי סטטיסטי להיבחר, בלי קשר
    לכמה פעמים הוא הופיע בעבר. הנתונים כאן הם <strong>תיאור היסטורי</strong> של מה שכבר
    קרה, לא ניבוי של מה שיקרה. ה"הצעות" בתחתית הדף הן לשעשוע בלבד.
  </div>

  <div class="tiles">
    <div class="tile"><div class="value">{stats['n_draws']}</div><div class="label">הגרלות שנותחו</div></div>
    <div class="tile"><div class="value">{stats['hottest'][0]}</div><div class="label">המספר השכיח ביותר ({stats['reg_count'][stats['hottest'][0]]} פעמים)</div></div>
    <div class="tile"><div class="value">{stats['coldest'][0]}</div><div class="label">המספר הפחות שכיח ({stats['reg_count'][stats['coldest'][0]]} פעמים)</div></div>
    <div class="tile"><div class="value">{stats['most_overdue'][0]}</div><div class="label">הכי הרבה זמן שלא הופיע ({stats['reg_gap'][stats['most_overdue'][0]]} הגרלות)</div></div>
  </div>

  <section>
    <h2>תדירות מספרים רגילים (1–37)</h2>
    <p class="section-desc">כמה פעמים הופיע כל מספר לאורך ההיסטוריה. 6 המספרים השכיחים ביותר מסומנים בכתום. העבר עכבר מעל עמודה לפרטים.</p>
    <div class="card">{reg_svg}</div>
  </section>

  <section>
    <h2>תדירות המספר החזק (1–7)</h2>
    <p class="section-desc">כמה פעמים נבחר כל מספר חזק.</p>
    <div class="card">{strong_svg}</div>
  </section>

  <section>
    <h2>מספרים חמים, קרים ו"באיחור"</h2>
    <p class="section-desc">חמים = השכיחים ביותר בהיסטוריה. קרים = הפחות שכיחים. באיחור = הכי הרבה הגרלות מאז שהופיעו לאחרונה.</p>
    <div class="tables">
      <div class="card">
        <h3 style="margin-top:0;font-size:0.95rem;">🔥 10 המספרים החמים</h3>
        <table><thead><tr><th>מספר</th><th>הופעות</th><th>הופעה אחרונה</th></tr></thead>
        <tbody>{hot_rows}</tbody></table>
      </div>
      <div class="card">
        <h3 style="margin-top:0;font-size:0.95rem;">❄️ 10 המספרים הקרים</h3>
        <table><thead><tr><th>מספר</th><th>הופעות</th><th>הופעה אחרונה</th></tr></thead>
        <tbody>{cold_rows}</tbody></table>
      </div>
      <div class="card">
        <h3 style="margin-top:0;font-size:0.95rem;">⏳ 10 המספרים "באיחור"</h3>
        <table><thead><tr><th>מספר</th><th>הופעות</th><th>לא הופיע כבר</th></tr></thead>
        <tbody>{overdue_rows}</tbody></table>
      </div>
    </div>
  </section>

  <section>
    <h2>10 הצעות משעשעות להגרלה הבאה</h2>
    <p class="section-desc">
      כל שורה נבחרה אקראית בנפרד, כשההסתברות של כל מספר להיבחר משוקללת לפי
      תדירותו ההיסטורית. <strong>אלה לא תחזיות אמיתיות</strong> — ראו את ההבהרה למעלה.
    </p>
    <div class="card">
      <div class="picks-list">{picks_html}</div>
    </div>
  </section>

  <footer>
    מקור הנתונים: <a href="https://www.pais.co.il/lotto/archive.aspx" target="_blank" rel="noopener">ארכיון תוצאות הלוטו, מפעל הפיס</a>.
    התוצאות המוצגות אינן רשמיות ואינן מחייבות; לתוצאות הרשמיות יש לפנות למפעל הפיס.
    הדוח מתעדכן אוטומטית מדי שבוע.
  </footer>
</div>
</div>

<div class="tooltip" id="tooltip"></div>
<script>
  const tooltip = document.getElementById('tooltip');
  document.querySelectorAll('.bar').forEach(bar => {{
    bar.addEventListener('mousemove', (e) => {{
      const num = bar.getAttribute('data-num');
      const count = bar.getAttribute('data-count');
      tooltip.textContent = `מספר ${{num}}: ${{count}} הופעות`;
      tooltip.style.left = e.clientX + 'px';
      tooltip.style.top = e.clientY + 'px';
      tooltip.classList.add('show');
    }});
    bar.addEventListener('mouseleave', () => tooltip.classList.remove('show'));
  }});
</script>
</body>
</html>
'''
    return html


def main():
    text = fetch()
    rows = parse_and_filter(text)
    stats = compute_stats(rows)
    picks = suggest_picks(stats, count=10)
    html = render_html(stats, picks)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK: {stats['n_draws']} draws, {fmt_date(stats['first_date'])} - {fmt_date(stats['last_date'])}")


if __name__ == "__main__":
    main()
