"""
מוריד את קובץ היסטוריית הגרלות הלוטו הרשמי ממפעל הפיס ושומר אותו כ-CSV מקומי.
מקור: https://www.pais.co.il/lotto/archive.aspx
"""
import csv
import datetime
import io
import os
import sys

import requests
import urllib3

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# במחשב הזה תעבורת HTTPS עוברת דרך סריקת ה-SSL של Avast, שמחליפה את
# האישור המקורי באישור חתום ע"י Avast (מהימן ב-Windows, אך לא ברשימת
# האישורים הפנימית של Python/requests). כדי לא להיתקע על שגיאת אימות
# אישור מקומית בלבד, מדלגים כאן על האימות של requests עצמו.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CSV_URL = "https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx"
OUT_PATH = os.path.join(os.path.dirname(__file__), "data", "lotto_raw.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# פורמט המשחק הנוכחי (6 מספרים מ-1 עד 37 + מספר חזק מ-1 עד 7) קבוע החל
# מהגרלה מס' 2234 בתאריך 05/03/2011 (ההגרלה הקודמת, 01/03/2011, עדיין
# כללה מספר חזק 8 - מחוץ לטווח הנוכחי). הגרלות ישנות יותר פעלו לפי כללים
# אחרים ולעיתים עומדות בטווחי המספרים הנוכחיים במקרה בלבד, ולכן הסינון
# נעשה לפי תאריך ולא לפי טווח המספרים, כדי לא לכלול אותן בטעות.
CURRENT_FORMAT_START_DATE = datetime.date(2011, 3, 5)
CURRENT_FORMAT_MIN_REGULAR = 1
CURRENT_FORMAT_MAX_REGULAR = 37
CURRENT_FORMAT_MIN_STRONG = 1
CURRENT_FORMAT_MAX_STRONG = 7


def fetch():
    resp = requests.get(CSV_URL, headers=HEADERS, timeout=30, verify=False)
    resp.raise_for_status()
    text = resp.content.decode("cp1255")
    return text


def parse_and_filter(text):
    lines = text.splitlines()
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 9:
            continue
        try:
            draw_id = int(parts[0])
            date_str = parts[1]
            day, month, year = date_str.split("/")
            date = datetime.date(int(year), int(month), int(day))
            nums = [int(x) for x in parts[2:8]]
            strong = int(parts[8])
        except ValueError:
            continue
        if date < CURRENT_FORMAT_START_DATE:
            continue
        # בדיקת שפיות: מהתאריך הזה ואילך כל ההגרלות אמורות לעמוד בטווח הנוכחי
        assert all(CURRENT_FORMAT_MIN_REGULAR <= n <= CURRENT_FORMAT_MAX_REGULAR for n in nums), line
        assert CURRENT_FORMAT_MIN_STRONG <= strong <= CURRENT_FORMAT_MAX_STRONG, line
        rows.append({
            "draw_id": draw_id,
            "date": date_str,
            "numbers": nums,
            "strong": strong,
        })
    return rows


def save(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["draw_id", "date", "n1", "n2", "n3", "n4", "n5", "n6", "strong"])
        for r in rows:
            writer.writerow([r["draw_id"], r["date"]] + r["numbers"] + [r["strong"]])


def main():
    print("מוריד נתונים ממפעל הפיס...")
    text = fetch()
    rows = parse_and_filter(text)
    if not rows:
        raise RuntimeError("לא נמצאו שורות תקינות בקובץ שהתקבל")
    save(rows, OUT_PATH)
    print(f"נשמרו {len(rows)} הגרלות (פורמט נוכחי בלבד) לקובץ: {OUT_PATH}")
    print(f"טווח תאריכים: {rows[-1]['date']} עד {rows[0]['date']}")


if __name__ == "__main__":
    main()
