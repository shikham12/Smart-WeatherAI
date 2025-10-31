import json, csv, io
import pandas as pd

def export_as_json(record):
    return json.loads(record.weather_json)

def export_as_csv(record):
    data = export_as_json(record)
    # create CSV containing current + daily summary
    rows = []
    # current
    cur = data.get("current", {})
    rows.append({"type":"current","dt":cur.get("dt"), "temp":cur.get("temp"), "weather":cur.get("weather")})
    # daily
    for d in data.get("daily", []):
        rows.append({"type":"daily", "dt":d.get("dt"), "min": d.get("temp",{}).get("min"), "max": d.get("temp",{}).get("max"), "weather": d.get("weather")})
    df = pd.DataFrame(rows)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    return csv_buf.getvalue()

def export_as_markdown(record):
    data = export_as_json(record)
    md = f"# Weather for {record.resolved_name}\n\n"
    cur = data.get("current", {})
    md += f"**Current temp:** {cur.get('temp')} \n\n"
    md += "## 5-day forecast\n\n"
    for d in data.get("daily", [])[:5]:
        md += f"- Date ts {d.get('dt')}: min {d.get('temp',{}).get('min')}, max {d.get('temp',{}).get('max')}\n"
    return md
