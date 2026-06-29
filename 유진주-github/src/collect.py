import os
import feedparser
import glob
import time
import datetime
import re

LOGS_DIR = "logs"
AI_KEYWORDS = [
    "ai",
    "artificial intelligence",
    "machine learning",
    "ml",
    "llm",
    "large language model",
    "generative ai",
    "openai",
    "anthropic",
    "gemini",
    "chatgpt",
    "model",
    "models",
    "보안",
    "취약점",
    "규제",
    "정책",
    "모델",
    "업데이트",
]


def is_test_mode():
    return os.environ.get("COLLECT_TEST_MODE", "false").lower() in {"1", "true", "yes", "y"}


def get_test_limit():
    if not is_test_mode():
        return 0
    raw_limit = os.environ.get("COLLECT_LIMIT", "2")
    try:
        return max(1, int(raw_limit))
    except ValueError:
        return 2

def init_log(log_type):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-{log_type}.txt")
    with open(filename, 'a', encoding='utf-8') as f:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{log_type} 파이프라인 실행] {now_str}\n---\n")

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


def matches_keywords(title, summary_text, keywords):
    text = f"{title} {summary_text}".lower()
    return any(keyword.lower() in text for keyword in keywords)

def main():
    print("--- 1. 수집 파이프라인 시작 ---")
    init_log("수집")
    urls = [
        "https://news.google.com/rss/search?q=AI+OR+Artificial+Intelligence&hl=ko&gl=KR&ceid=KR:ko",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://venturebeat.com/category/ai/feed/"
    ]
    history_links = load_history_from_logs()
    keywords = AI_KEYWORDS
    collected_total = 0
    test_limit = get_test_limit()
    
    for url in urls:
        print(f"\n[URL 파싱 중] {url}")
        try:
            import requests
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            print(f" -> 파싱 성공: 총 {len(feed.entries)}개의 기사 발견")
            
            matched_count = 0
            for entry in feed.entries:
                if test_limit and collected_total >= test_limit:
                    break

                title = entry.title
                link = entry.link
                published = getattr(entry, "published", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                summary_text = getattr(entry, "summary", getattr(entry, "description", ""))
                summary_text = re.sub(r'<[^>]+>', '', summary_text).strip()
                
                is_recent = True
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_dt = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    if (datetime.datetime.now() - published_dt).total_seconds() > 7 * 24 * 3600:
                        is_recent = False
                        
                if not is_recent:
                    continue
                
                if matches_keywords(title, summary_text, keywords):
                    if link not in history_links:
                        matched_count += 1
                        collected_total += 1
                        history_links.add(link)
                        save_to_log("수집", title, link, published, summary_text)
            print(f" -> 날짜/키워드 필터링 통과 기사: {matched_count}개")
        except Exception as e:
            print(f" -> RSS 파싱 에러: {e}")
            save_error_to_log("수집", url, str(e))

    if collected_total == 0:
        with open(os.path.join(LOGS_DIR, f"{datetime.datetime.now().strftime('%Y%m%d')}-수집.txt"), 'a', encoding='utf-8') as f:
            f.write("[STATUS] NO_ARTICLES\n")
            f.write("---\n")
        print("\n -> 조건에 맞는 기사가 0건이라 후속 단계는 중단됩니다.")
    else:
        print(f"\n -> 총 수집 기사 수: {collected_total}개")
    print("\n--- 1. 수집 파이프라인 종료 ---")

if __name__ == "__main__":
    main()
