"""
民宿日历同步脚本
从各平台抓取 iCal 数据，合并后生成各平台专属的 ics 文件
每个平台的文件排除自己平台的预订，只包含其他平台的预订
"""

import requests
import os
from datetime import datetime, timezone
from icalendar import Calendar, Event, vText

# ─────────────────────────────────────────
# 配置：各平台 iCal 链接
# ─────────────────────────────────────────
PLATFORMS = {
    "airbnb": "https://zh.airbnb.com/calendar/ical/1631007673684810992.ics?t=f947d27a1b1e4ea5aae4d7187713417b",
    "booking": "https://ical.booking.com/v1/export?t=6af3742f-8de8-466b-b96b-fde0524b2a4e",
    "agoda": "https://ycs.agoda.com/en-us/api/ari/icalendar?key=Wo%2fmNl0ENJaLicNon%2b3fxDW1udtQZaft",
    "vrbo": "https://www.vrbo.com/icalendar/78777af9d957449f9a02cb9c0693026d.ics?nonTentative",
}

# 输出目录
OUTPUT_DIR = "docs"


def fetch_calendar(name, url):
    """抓取单个平台的 iCal 数据"""
    print(f"正在抓取 {name} 的日历...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CalendarSync/1.0)"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        cal = Calendar.from_ical(response.content)
        events = list(cal.walk("VEVENT"))
        print(f"  ✓ {name}: 获取到 {len(events)} 个预订")
        return events
    except Exception as e:
        print(f"  ✗ {name}: 抓取失败 - {e}")
        return []


def make_calendar(events, source_platform):
    """
    生成合并后的 iCal 文件
    events: dict { platform_name: [events] }
    source_platform: 排除哪个平台自己的预订
    """
    cal = Calendar()
    cal.add("prodid", f"-//Calendar Sync//{source_platform}//ZH")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add(
        "x-wr-calname",
        vText(f"民宿同步日历（用于{source_platform}）")
    )
    cal.add(
        "x-wr-caldesc",
        vText(f"包含除 {source_platform} 以外所有平台的预订")
    )

    count = 0
    for platform, platform_events in events.items():
        if platform == source_platform:
            continue  # 排除自己平台的预订
        for event in platform_events:
            new_event = Event()
            # 复制原始事件的所有属性
            for key, value in event.items():
                try:
                    new_event.add(key, value)
                except Exception:
                    pass
            # 在摘要里标注来源平台
            original_summary = str(event.get("summary", "Blocked"))
            new_event["summary"] = vText(f"[{platform}] {original_summary}")
            cal.add_component(new_event)
            count += 1

    print(f"  → 给 {source_platform} 生成了 {count} 个屏蔽事件")
    return cal.to_ical()


def main():
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 抓取所有平台数据
    print("=" * 50)
    print(f"开始同步 - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 50)

    all_events = {}
    for name, url in PLATFORMS.items():
        all_events[name] = fetch_calendar(name, url)

    # 为每个平台生成专属合并文件
    print("\n生成各平台专属日历文件...")
    for platform in PLATFORMS:
        ical_data = make_calendar(all_events, platform)
        output_path = os.path.join(OUTPUT_DIR, f"{platform}.ics")
        with open(output_path, "wb") as f:
            f.write(ical_data)
        print(f"  ✓ 已写入 {output_path}")

    # 生成一个状态页面
    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <title>民宿日历同步状态</title>
  <style>
    body {{ font-family: sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; }}
    h1 {{ color: #333; }}
    .card {{ background: #f5f5f5; border-radius: 8px; padding: 16px; margin: 12px 0; }}
    .label {{ font-weight: bold; color: #555; }}
    code {{ background: #e0e0e0; padding: 2px 6px; border-radius: 4px; font-size: 13px; word-break: break-all; }}
    .updated {{ color: #888; font-size: 13px; margin-top: 20px; }}
  </style>
</head>
<body>
  <h1>🏠 民宿日历同步</h1>
  <p>以下链接请导入到对应平台的「导入日历」功能中：</p>
"""
    base_url = "https://{YOUR_GITHUB_USERNAME}.github.io/{YOUR_REPO_NAME}"
    for platform in PLATFORMS:
        url = f"{base_url}/{platform}.ics"
        html += f"""
  <div class="card">
    <div class="label">{platform.upper()} 导入链接</div>
    <br>
    <code>{url}</code>
  </div>
"""
    html += f"""
  <p class="updated">最后更新：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
</body>
</html>
"""
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    print("\n✅ 同步完成！")
    print(f"   输出目录：{OUTPUT_DIR}/")
    for platform in PLATFORMS:
        print(f"   - {platform}.ics")


if __name__ == "__main__":
    main()
