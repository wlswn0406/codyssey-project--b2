import os
import feedparser
import glob
import time
import datetime

LOGS_DIR = "logs"

def load_history_from_logs():
    history = set()
    if not os.path.exists(LOGS_DIR):
        return history
    for filepath in glob.glob(os.path.join(LOGS_DIR, "*.txt")):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("[LINK] "):
                    history.add(line.replace("[LINK] ", "").strip())
    return history

def save_error_to_log(log_type, url, error_msg):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-{log_type}.txt")
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"[수집 오류] {url} - {error_msg}\n")
        f.write("---\n")

def save_to_log(log_type, title, link, published, summary_text):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-{log_type}.txt")
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"[TITLE] {title}\n")
        f.write(f"[LINK] {link}\n")
        f.write(f"[PUBLISHED] {published}\n")
        f.write(f"[SUMMARY]\n{summary_text}\n")
        f.write("---\n")

def main():
    print("--- 1. 수집 파이프라인 시작 ---")
    urls = [
        "https://news.google.com/rss/search?q=AI+OR+Artificial+Intelligence&hl=ko&gl=KR&ceid=KR:ko",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://venturebeat.com/category/ai/feed/"
    ]
    history_links = load_history_from_logs()
    keywords = ["보안", "취약점", "규제", "정책", "모델", "업데이트", "security", "policy", "regulation", "model", "release"]
    
    for url in urls:
        try:
            import requests
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            for entry in feed.entries:
                title = entry.title
                link = entry.link
                published = getattr(entry, "published", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                summary_text = getattr(entry, "summary", getattr(entry, "description", ""))
                import re
                summary_text = re.sub(r'<[^>]+>', '', summary_text).strip()
                
                is_recent = True
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_dt = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    if (datetime.datetime.now() - published_dt).total_seconds() > 7 * 24 * 3600:
                        is_recent = False
                        
                if not is_recent:
                    continue
                
                if any(k.lower() in title.lower() for k in keywords):
                    if link not in history_links:
                        history_links.add(link)
                        save_to_log("수집", title, link, published, summary_text)
        except Exception as e:
            print(f"RSS 파싱 에러 ({url}): {e}")
            save_error_to_log("수집", url, str(e))
    print("--- 1. 수집 파이프라인 종료 ---")

if __name__ == "__main__":
    main()
