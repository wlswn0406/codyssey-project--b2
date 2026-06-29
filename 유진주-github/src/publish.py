import os
import glob
import datetime

LOGS_DIR = "logs"

def load_summarized_news():
    news_list = []
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-요약.txt")
    if not os.path.exists(filename):
        return news_list
        
    current_news = {}
    summary_lines = []
    in_summary = False
    
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("[TITLE] "):
                current_news['title'] = stripped.replace("[TITLE] ", "")
            elif stripped.startswith("[LINK] "):
                current_news['link'] = stripped.replace("[LINK] ", "")
            elif stripped.startswith("[PUBLISHED] "):
                current_news['published'] = stripped.replace("[PUBLISHED] ", "")
            elif stripped.startswith("[IMAGE] "):
                current_news['image'] = stripped.replace("[IMAGE] ", "")
            elif stripped == "[SUMMARY]":
                in_summary = True
            elif stripped == "---":
                if 'title' in current_news and 'link' in current_news:
                    current_news['summary'] = "\n".join(summary_lines)
                    news_list.append(current_news)
                current_news = {}
                summary_lines = []
                in_summary = False
            elif in_summary:
                summary_lines.append(stripped)
    return news_list

def save_to_markdown(news_list):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}-news.md"
    
    existing_links = set()
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                if "**원문 링크**: [보러가기](" in line:
                    link = line.split("**원문 링크**: [보러가기](")[1].split(")")[0]
                    existing_links.add(link)
    
    mode = 'a' if os.path.exists(filename) else 'w'
    added_count = 0
    
    try:
        with open(filename, mode, encoding='utf-8') as f:
            if mode == 'w':
                f.write(f"# {today} AI 핵심 뉴스 리포트\n\n")
                
            for item in news_list:
                if item['link'] in existing_links:
                    continue
                    
                content = f"## {item['title']}\n\n"
                if 'published' in item:
                    content += f"**발행일시**: {item['published']}\n"
                content += f"**원문 링크**: [보러가기]({item['link']})\n\n"
                if 'image' in item and item['image']:
                    content += f"![썸네일 이미지]({item['image']})\n\n"
                content += f"### AI 3줄 요약 및 논조\n\n{item['summary']}\n\n---\n\n"
                f.write(content)
                added_count += 1
                
        print(f"{filename} 마크다운 파일 업데이트 완료 ({added_count}건 추가)")
    except Exception as e:
        print(f"마크다운 저장 실패: {e}")

def main():
    print("--- 4. 마크다운 발행 파이프라인 시작 ---")
    news_list = load_summarized_news()
    if news_list:
        save_to_markdown(news_list)
    else:
        print("발행할 새 기사가 없습니다.")
    print("--- 4. 마크다운 발행 파이프라인 종료 ---")

if __name__ == "__main__":
    main()
