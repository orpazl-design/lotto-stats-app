"""
קורא את data/lotto_raw.csv (שנוצר ע"י fetch_data.py), מחשב סטטיסטיקות
על הגרלות הלוטו, ומייצר דוח HTML עצמאי (report.html) שאפשר לפתוח בדפדפן.
"""
import base64
import csv
import datetime
import json
import os
import random
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "data", "lotto_raw.csv")
PICKS_HISTORY_PATH = os.path.join(BASE_DIR, "data", "picks_history.json")
OUT_PATH = os.path.join(BASE_DIR, "report.html")
ICON_PATH = os.path.join(BASE_DIR, "icon-180.png")


def load_icon_base64():
    if not os.path.exists(ICON_PATH):
        return None
    with open(ICON_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

REGULAR_RANGE = range(1, 38)  # 1..37
STRONG_RANGE = range(1, 8)  # 1..7


def load_rows():
    rows = []
    with open(DATA_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            day, month, year = r["date"].split("/")
            date = datetime.date(int(year), int(month), int(day))
            nums = [int(r[f"n{i}"]) for i in range(1, 7)]
            rows.append({
                "draw_id": int(r["draw_id"]),
                "date": date,
                "numbers": nums,
                "strong": int(r["strong"]),
            })
    # הקובץ מסודר מהחדש לישן; נהפוך כדי שאינדקס 0 = ההגרלה הישנה ביותר
    rows.sort(key=lambda r: r["date"])
    return rows


def compute_stats(rows):
    n_draws = len(rows)
    last_date = rows[-1]["date"]
    first_date = rows[0]["date"]

    reg_count = {n: 0 for n in REGULAR_RANGE}
    reg_last_seen_idx = {n: None for n in REGULAR_RANGE}  # אינדקס ההגרלה האחרונה שבה הופיע
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
    strong_gap = {n: (n_draws - 1 - strong_last_seen_idx[n]) if strong_last_seen_idx[n] is not None else n_draws
                  for n in STRONG_RANGE}

    reg_last_date = {n: (rows[reg_last_seen_idx[n]]["date"] if reg_last_seen_idx[n] is not None else None)
                      for n in REGULAR_RANGE}
    strong_last_date = {n: (rows[strong_last_seen_idx[n]]["date"] if strong_last_seen_idx[n] is not None else None)
                         for n in STRONG_RANGE}

    hottest = sorted(REGULAR_RANGE, key=lambda n: (-reg_count[n], n))
    coldest = sorted(REGULAR_RANGE, key=lambda n: (reg_count[n], n))
    most_overdue = sorted(REGULAR_RANGE, key=lambda n: (-reg_gap[n], n))

    return {
        "n_draws": n_draws,
        "first_date": first_date,
        "last_date": last_date,
        "reg_count": reg_count,
        "reg_gap": reg_gap,
        "reg_last_date": reg_last_date,
        "strong_count": strong_count,
        "strong_gap": strong_gap,
        "strong_last_date": strong_last_date,
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
    """כמה בחירות משוקללות לפי תדירות היסטורית - לשעשוע בלבד, לא ניבוי אמיתי."""
    rng = random.Random(seed)
    picks = []
    seen = set()
    attempts = 0
    while len(picks) < count and attempts < count * 20:
        attempts += 1
        picked, strong_pick = _one_pick(rng, stats)
        key = (tuple(picked), strong_pick)
        if key in seen:
            continue
        seen.add(key)
        picks.append((picked, strong_pick))
    return picks


def load_picks_history():
    """טוען את ההצעות שנשמרו בהרצה הקודמת, אם קיימות."""
    if not os.path.exists(PICKS_HISTORY_PATH):
        return None
    with open(PICKS_HISTORY_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_picks_history(generated_after_draw_id, generated_date, picks):
    data = {
        "generated_after_draw_id": generated_after_draw_id,
        "generated_date": generated_date,
        "picks": [{"numbers": numbers, "strong": strong} for numbers, strong in picks],
    }
    os.makedirs(os.path.dirname(PICKS_HISTORY_PATH), exist_ok=True)
    with open(PICKS_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def check_previous_picks(rows, history):
    """
    בודק את ההצעות שנשמרו בהרצה הקודמת מול כל הגרלה חדשה שהתקיימה מאז.
    מחזיר רשימה (מהחדש לישן) של {"draw": ..., "match_rows": [...]} כשכל match_row
    כולל את מספר ההתאמות (0-6) ואם המספר החזק פגע, ממוין מהכי טוב לפחות טוב.
    """
    if not history:
        return []
    since_id = history["generated_after_draw_id"]
    new_draws = [r for r in rows if r["draw_id"] > since_id]
    prev_picks = [(p["numbers"], p["strong"]) for p in history["picks"]]

    results = []
    for draw in new_draws:
        draw_set = set(draw["numbers"])
        match_rows = []
        for numbers, strong in prev_picks:
            match_count = len(draw_set & set(numbers))
            strong_hit = strong == draw["strong"]
            match_rows.append({
                "numbers": numbers,
                "strong": strong,
                "match_count": match_count,
                "strong_hit": strong_hit,
            })
        match_rows.sort(key=lambda m: (-m["match_count"], -m["strong_hit"]))
        results.append({"draw": draw, "match_rows": match_rows})

    results.sort(key=lambda r: r["draw"]["draw_id"], reverse=True)
    return results


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


def render_last_draw(last_draw):
    """כרטיס קטן עם תוצאות ההגרלה האחרונה - כדי לראות מייד מי זכה."""
    nums_html = "".join(f'<span class="num-pill num-pill-lg">{n}</span>' for n in last_draw["numbers"])
    strong_pill = f'<span class="num-pill num-pill-lg num-pill-strong">{last_draw["strong"]}</span>'
    return f'''<div class="card draw-header">
      <div>
        <div class="draw-date">הגרלה מס' {last_draw["draw_id"]} · {fmt_date(last_draw["date"])}</div>
        <div class="pick-box">{nums_html}<span class="pick-plus">+</span>{strong_pill}</div>
      </div>
    </div>'''


def render_check_results(check_results):
    """
    בודק כמה הייתה שוות ההצעות מהפעם הקודמת מול ההגרלות שהתקיימו מאז -
    בשביל לראות אם היינו "פוגעים" אם היינו שולחים אותן בפועל.
    """
    if not check_results:
        return '''<p class="section-desc">
      עדיין אין הצעות קודמות לבדוק - ההצעות שבתחתית הדף הזה ייבדקו מול ההגרלה הבאה, בהרצה הבאה.
    </p>'''

    blocks = []
    for entry in check_results:
        draw = entry["draw"]
        match_rows = entry["match_rows"]
        best = match_rows[0]
        best_label = f'הכי טוב: {best["match_count"]} מתוך 6'
        if best["strong_hit"]:
            best_label += " (וגם המספר החזק!)"

        draw_nums_html = "".join(f'<span class="num-pill">{n}</span>' for n in draw["numbers"])
        draw_strong_pill = f'<span class="num-pill num-pill-strong">{draw["strong"]}</span>'

        rows_html = []
        for i, m in enumerate(match_rows, start=1):
            nums_html = "".join(f'<span class="num-pill">{n}</span>' for n in m["numbers"])
            strong_pill = f'<span class="num-pill num-pill-strong">{m["strong"]}</span>'
            strong_cell = "✅" if m["strong_hit"] else "—"
            rows_html.append(
                f'<tr><td class="num-cell">#{i}</td>'
                f'<td><span class="pick-nums">{nums_html}<span class="pick-plus">+</span>{strong_pill}</span></td>'
                f'<td class="match-count-cell">{m["match_count"]}</td>'
                f'<td>{strong_cell}</td></tr>'
            )

        blocks.append(f'''<div class="card check-draw">
      <div class="draw-header">
        <div>
          <div class="draw-date">הגרלה מס' {draw["draw_id"]} · {fmt_date(draw["date"])}</div>
          <div class="pick-box">{draw_nums_html}<span class="pick-plus">+</span>{draw_strong_pill}</div>
        </div>
        <span class="best-badge">{best_label}</span>
      </div>
      <table class="match-table">
        <thead><tr><th>#</th><th>ההצעה שלנו</th><th>התאמות</th><th>חזק</th></tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
    </div>''')

    return "".join(blocks)


def render_html(stats, picks, check_results, last_draw):
    icon_b64 = load_icon_base64()
    if icon_b64:
        icon_tags = (
            f'<link rel="apple-touch-icon" href="data:image/png;base64,{icon_b64}">\n'
            f'<link rel="icon" type="image/png" href="data:image/png;base64,{icon_b64}">'
        )
    else:
        icon_tags = ""

    reg_svg = bar_chart_svg(
        stats["reg_count"], list(REGULAR_RANGE), "chart-regular",
        highlight=set(stats["hottest"][:6])
    )
    strong_svg = bar_chart_svg(
        stats["strong_count"], list(STRONG_RANGE), "chart-strong", width=420,
        highlight={stats["hottest"][0]} & set(STRONG_RANGE)
    )

    def hot_cold_rows(nums, extra_label):
        out = []
        for n in nums:
            out.append(
                f'<tr><td class="num-cell"><span class="num-pill">{n}</span></td>'
                f'<td>{stats["reg_count"][n]}</td>'
                f'<td>{extra_label(n)}</td></tr>'
            )
        return "".join(out)

    hot_rows = hot_cold_rows(stats["hottest"][:10], lambda n: fmt_date(stats["reg_last_date"][n]))
    cold_rows = hot_cold_rows(stats["coldest"][:10], lambda n: fmt_date(stats["reg_last_date"][n]))
    overdue_rows = hot_cold_rows(
        stats["most_overdue"][:10],
        lambda n: f'{stats["reg_gap"][n]} הגרלות'
    )

    picks_rows = []
    for i, (pick, strong_pick) in enumerate(picks, start=1):
        nums_html = "".join(f'<span class="num-pill">{n}</span>' for n in pick)
        strong_pill = f'<span class="num-pill num-pill-strong">{strong_pick}</span>'
        picks_rows.append(
            f'<div class="pick-row"><span class="pick-idx">#{i}</span>'
            f'<span class="pick-nums">{nums_html}<span class="pick-plus">+</span>{strong_pill}</span></div>'
        )
    picks_html = "".join(picks_rows)

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
  .num-pill-lg {{ width: 44px; height: 44px; font-size: 1.15rem; margin-inline-end: 8px; }}
  .num-pill-strong {{ background: var(--series-hot); }}

  .pick-box {{ display: flex; align-items: center; flex-wrap: wrap; gap: 4px; margin: 10px 0; }}
  .pick-plus {{ color: var(--text-muted); margin: 0 6px; font-size: 1.2rem; }}
  .picks-list {{ display: flex; flex-direction: column; gap: 10px; }}
  .pick-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 8px 4px; border-bottom: 1px solid var(--gridline);
  }}
  .pick-row:last-child {{ border-bottom: none; }}
  .pick-idx {{ color: var(--text-muted); font-size: 0.85rem; width: 28px; flex-shrink: 0; }}
  .pick-nums {{ display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }}

  .draw-header {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }}
  .draw-date {{ color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 6px; }}
  .num-pill-lg {{ width: 36px; height: 36px; font-size: 1rem; }}
  .best-badge {{
    background: var(--series-hot); color: #fff; font-size: 0.78rem; font-weight: 600;
    padding: 4px 12px; border-radius: 999px; white-space: nowrap;
  }}
  .check-draw {{ margin-bottom: 16px; }}
  .check-draw:last-child {{ margin-bottom: 0; }}
  .match-table {{ margin-top: 14px; }}
  .match-count-cell {{ font-weight: 700; }}

  footer {{ color: var(--text-muted); font-size: 0.8rem; margin-top: 40px; line-height: 1.7; }}
  footer a {{ color: var(--text-secondary); }}
</style>
</head>
<body>
<div class="viz-root">
<div class="wrap">
  <h1>סטטיסטיקת הגרלות הלוטו הישראלי</h1>
  <p class="subtitle">מבוסס על {stats['n_draws']} הגרלות בפורמט הנוכחי (6 מתוך 1–37 + מספר חזק 1–7), מ-{fmt_date(stats['first_date'])} עד {fmt_date(stats['last_date'])}. מקור: ארכיון מפעל הפיס.</p>

  <div class="disclaimer">
    <strong>חשוב:</strong> הגרלת הלוטו היא אירוע אקראי לחלוטין ובלתי תלוי בהגרלות
    קודמות — לכל מספר יש בכל הגרלה בדיוק אותו סיכוי סטטיסטי להיבחר, בלי קשר
    לכמה פעמים הוא הופיע בעבר. הנתונים כאן הם <strong>תיאור היסטורי</strong> של מה שכבר
    קרה, לא ניבוי של מה שיקרה. ה"הצעה" בתחתית הדף היא לשעשוע בלבד.
  </div>

  <div class="tiles">
    <div class="tile"><div class="value">{stats['n_draws']}</div><div class="label">הגרלות שנותחו</div></div>
    <div class="tile"><div class="value">{stats['hottest'][0]}</div><div class="label">המספר השכיח ביותר ({stats['reg_count'][stats['hottest'][0]]} פעמים)</div></div>
    <div class="tile"><div class="value">{stats['coldest'][0]}</div><div class="label">המספר הפחות שכיח ({stats['reg_count'][stats['coldest'][0]]} פעמים)</div></div>
    <div class="tile"><div class="value">{stats['most_overdue'][0]}</div><div class="label">הכי הרבה זמן שלא הופיע ({stats['reg_gap'][stats['most_overdue'][0]]} הגרלות)</div></div>
  </div>

  <section>
    <h2>🎯 תוצאות ההגרלה האחרונה</h2>
    {render_last_draw(last_draw)}
  </section>

  <section>
    <h2>✅ איך ההצעות הקודמות שלנו הסתדרו</h2>
    <p class="section-desc">
      ההצעות שהופיעו בדוח הקודם, מול כל הגרלה שהתקיימה מאז - כדי לראות כמה
      היינו "פוגעים" אם היינו שולחים אותן בפועל. גם כאן: זה בדיעבד, לא ניבוי.
    </p>
    {render_check_results(check_results)}
  </section>

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
    הדוח נוצר אוטומטית ע"י סקריפט מקומי (fetch_data.py + build_report.py).
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
    rows = load_rows()
    stats = compute_stats(rows)
    history = load_picks_history()
    check_results = check_previous_picks(rows, history)
    picks = suggest_picks(stats, count=10)
    html = render_html(stats, picks, check_results, rows[-1])
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    save_picks_history(rows[-1]["draw_id"], datetime.date.today().isoformat(), picks)
    print(f"נוצר דוח: {OUT_PATH}")
    if check_results:
        best_overall = max(m["match_count"] for r in check_results for m in r["match_rows"])
        print(f"נבדקו {len(check_results)} הגרלות חדשות מול ההצעות הקודמות; ההתאמה הטובה ביותר: {best_overall} מתוך 6")


if __name__ == "__main__":
    main()
