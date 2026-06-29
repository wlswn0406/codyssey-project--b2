import os
import datetime
import google.genai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

LOGS_DIR = "logs"

def load_filtered_news():
    news_list = []
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-필터링.txt")
    if not os.path.exists(filename):
        return news_list
        
    current_news = {}
    body_lines = []
    in_body = False
    
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("[TITLE] "):
                current_news['title'] = line.replace("[TITLE] ", "")
                in_body = False
            elif line.startswith("[LINK] "):
                current_news['link'] = line.replace("[LINK] ", "")
                in_body = False
            elif line.startswith("[PUBLISHED] "):
                current_news['published'] = line.replace("[PUBLISHED] ", "")
                in_body = False
            elif line == "[BODY]":
                in_body = True
            elif line == "---":
                if 'title' in current_news and 'link' in current_news:
                    if in_body:
                        current_news['body'] = "\n".join(body_lines)
                    news_list.append(current_news)
                current_news = {}
                body_lines = []
                in_body = False
            elif in_body:
                body_lines.append(line)
    return news_list

def load_summarized_links():
    history = set()
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-요약.txt")
    if not os.path.exists(filename):
        return history
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith("[LINK] "):
                history.add(line.replace("[LINK] ", "").strip())
    return history

def save_error_to_log(log_type, link, error_msg):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-{log_type}.txt")
    with open(filename, 'a', encoding='utf-8') as f:
        tag = "요약 오류"
        f.write(f"[{tag}] {link} - {error_msg}\n")
        f.write("---\n")

def save_to_log(log_type, title, link, published, summary, image_url):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-{log_type}.txt")
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"[TITLE] {title}\n")
        f.write(f"[LINK] {link}\n")
        f.write(f"[PUBLISHED] {published}\n")
        f.write(f"[IMAGE] {image_url}\n")
        f.write(f"[SUMMARY]\n{summary}\n")
        f.write("---\n")

def generate_thumbnail_url(title):
    import urllib.parse
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "image_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        return ""
    
    prompt = prompt_template.format(keyword=title)
    encoded_prompt = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=450&nologo=true"

def generate_summary(title, link, body_text):
    if not client:
        raise ValueError("Gemini API 키 미설정")
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "summary_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        raise ValueError("summary_prompt.txt 파일을 찾을 수 없습니다.")
        
    try:
        prompt = prompt_template.format(title=title, link=link, body=body_text)
    except KeyError:
        prompt = prompt_template.format(title=title, link=link) + f"\n\n[본문]\n{body_text}"
        
    last_error = None
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            last_error = e
    raise last_error

def main():
    print("--- 3. 요약 파이프라인 시작 ---")
    news_list = load_filtered_news()
    summarized_links = load_summarized_links()
    
    for news in news_list:
        if news['link'] in summarized_links:
            continue
            
        print(f"\n요약 중: {news['title']}")
        try:
            summary = generate_summary(news['title'], news['link'], news.get('body', ''))
            image_url = generate_thumbnail_url(news['title'])
            save_to_log("요약", news['title'], news['link'], news['published'], summary, image_url)
        except Exception as e:
            print(f" -> [요약 API 오류] {e}")
            save_error_to_log("요약", news['link'], f"API 호출 실패: {e}")
    print("--- 3. 요약 파이프라인 종료 ---")

if __name__ == "__main__":
    main()
