import os
import glob
import datetime
import requests
from bs4 import BeautifulSoup
import google.genai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

LOGS_DIR = "logs"

def load_collected_news():
    news_list = []
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-수집.txt")
    if not os.path.exists(filename):
        return news_list
        
    current_news = {}
    summary_lines = []
    in_summary = False
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("[TITLE] "):
                current_news['title'] = line.replace("[TITLE] ", "")
                in_summary = False
            elif line.startswith("[LINK] "):
                current_news['link'] = line.replace("[LINK] ", "")
                in_summary = False
            elif line.startswith("[PUBLISHED] "):
                current_news['published'] = line.replace("[PUBLISHED] ", "")
                in_summary = False
            elif line == "[SUMMARY]":
                in_summary = True
            elif line == "---":
                if 'title' in current_news and 'link' in current_news:
                    if 'published' not in current_news:
                        current_news['published'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if in_summary:
                        current_news['summary'] = "\n".join(summary_lines)
                    news_list.append(current_news)
                current_news = {}
                summary_lines = []
                in_summary = False
            elif in_summary:
                summary_lines.append(line)
    return news_list

def load_evaluated_links():
    history = set()
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-필터링.txt")
    if not os.path.exists(filename):
        return history
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith("[LINK] "):
                history.add(line.replace("[LINK] ", "").strip())
    return history

def save_skip_log(link, score):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-필터링.txt")
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"[LINK] {link}\n")
        f.write(f"[STATUS] SKIP (Score: {score})\n")
        f.write("---\n")

def save_error_to_log(log_type, link, error_msg):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-{log_type}.txt")
    with open(filename, 'a', encoding='utf-8') as f:
        tag = "평가 오류" if log_type == "필터링" else "요약 오류"
        f.write(f"[{tag}] {link} - {error_msg}\n")
        f.write("---\n")

def save_to_log(log_type, title, link, published, body):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-{log_type}.txt")
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"[TITLE] {title}\n")
        f.write(f"[LINK] {link}\n")
        f.write(f"[PUBLISHED] {published}\n")
        f.write(f"[BODY]\n{body}\n")
        f.write("---\n")

def evaluate_importance(title, link, summary):
    if not client:
        raise ValueError("Gemini API 키 미설정")
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "filter_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        raise ValueError("filter_prompt.txt 파일을 찾을 수 없습니다.")
    prompt = prompt_template.format(title=title, link=link, summary=summary)
    
    last_error = None
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            result = response.text.strip()
            if result == "SKIP":
                return 0
            import re
            numbers = re.findall(r'\d+', result)
            if numbers:
                return int(numbers[0])
            return 0
        except Exception as e:
            last_error = e
    raise last_error

def scrape_body(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text(separator='\n')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:3000]
    except Exception as e:
        print(f"웹 스크래핑 실패 ({url}): {e}")
        return ""

def main():
    print("--- 2. 평가 및 본문 수집 파이프라인 시작 ---")
    news_list = load_collected_news()
    evaluated_links = load_evaluated_links()
    
    for news in news_list:
        if news['link'] in evaluated_links:
            continue
            
        print(f"\n평가 중: {news['title']}")
        try:
            score = evaluate_importance(news['title'], news['link'], news.get('summary', ''))
            if score >= 7:
                print(f" -> [중요도 {score}점] 기사 본문 수집을 시작합니다.")
                body_text = scrape_body(news['link'])
                if body_text:
                    save_to_log("필터링", news['title'], news['link'], news['published'], body_text)
                else:
                    print(" -> [본문 수집 실패]")
                    save_error_to_log("필터링", news['link'], "본문 스크래핑 실패")
                    save_skip_log(news['link'], "Scrape Error")
            else:
                print(" -> [중요도 미달 또는 SKIP] 기사를 건너뜁니다.")
                save_skip_log(news['link'], score)
        except Exception as e:
            print(f" -> [평가 API 오류] {e}")
            save_error_to_log("필터링", news['link'], f"API 호출 실패: {e}")
    print("--- 2. 평가 및 본문 수집 파이프라인 종료 ---")

if __name__ == "__main__":
    main()
