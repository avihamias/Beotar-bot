#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from flask import Flask

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN",   "8951028454:AAGS3__2akLN_ZbSSVcwZV8sTAXr0LNi_BE")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "5753124116")
BEITAR_URL       = "https://www.leaan.co.il/category/%D7%A1%D7%A4%D7%95%D7%A8%D7%98/%D7%9B%D7%93%D7%95%D7%A8%D7%92%D7%9C"
TEAM_FILTER      = "ביתר"
CHECK_INTERVAL   = 30

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger()

app = Flask(__name__)

@app.route("/")
def home():
    return "בוט ביתר ירושלים פעיל!", 200

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
        if r.ok:
            log.info("הודעת טלגרם נשלחה")
        else:
            log.warning(f"שגיאת טלגרם: {r.text}")
    except Exception as e:
        log.warning(f"שגיאה: {e}")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "he-IL,he;q=0.9",
}

def fetch_events():
    try:
        r = requests.get(BEITAR_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log.warning(f"שגיאת שליפה: {e}")
        return []
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    events = []
    seen = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/events/" not in href:
            continue
        try:
            eid = href.split("/events/")[1].split("/")[0].split("?")[0]
        except IndexError:
            continue
        if not eid or eid in seen:
            continue
        title = link.get_text(separator=" ", strip=True)
        if not title:
            continue
        if TEAM_FILTER and TEAM_FILTER not in title:
            continue
        full_url = href if href.startswith("http") else "https://www.leaan.co.il" + href
        seen.add(eid)
        events.append({"id": eid, "title": title, "url": full_url})
    return events

seen_events = set()
bot_started = False

def monitor_loop():
    global bot_started
    log.info("בוט מעקב ביתר ירושלים הופעל!")
    initial = fetch_events()
    for e in initial:
        seen_events.add(e["id"])
    log.info(f"נטענו {len(seen_events)} אירועים קיימים.")
    if not bot_started:
        bot_started = True
        send_telegram(f"✅ <b>בוט ביתר ירושלים פעיל!</b>\n\nמחפש כרטיסים כל {CHECK_INTERVAL} שניות\nכרגע {len(seen_events)} אירועים קיימים\n\nברגע שיצאו כרטיסים חדשים - תקבל הודעה! 🎟️")
    while True:
        try:
            events = fetch_events()
            new = [e for e in events if e["id"] not in seen_events]
            if new:
                for event in new:
                    seen_events.add(event["id"])
                    log.info(f"אירוע חדש: {event['title']}")
                    send_telegram(f"🎟️ <b>כרטיסים חדשים - ביתר ירושלים!</b>\n\n<b>{event['title']}</b>\n\n<a href='{event['url']}'>לחץ כאן לרכישה עכשיו!</a>")
            else:
                log.info(f"נבדקו {len(events)} אירועים - אין חדש")
        except Exception as e:
            log.error(f"שגיאה: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    import threading
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
