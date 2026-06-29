import os
import datetime

LOGS_DIR = "logs"
PUBLISH_SUFFIX = "-발행"


def ensure_dir(path):
    if path and not os.path.exists(path):
        os.makedirs(path)


def load_summarized_news():
    news_list = []
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = os.path.join(LOGS_DIR, f"{today}-요약.txt")
    if not os.path.exists(filename):
        return news_list

    current_news = {}
    summary_lines = []
    in_summary = False

    with open(filename, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if line.startswith("[TITLE] "):
                current_news["title"] = line.replace("[TITLE] ", "")
            elif line.startswith("[LINK] "):
                current_news["link"] = line.replace("[LINK] ", "")
            elif line.startswith("[PUBLISHED] "):
                current_news["published"] = line.replace("[PUBLISHED] ", "")
            elif line.startswith("[IMAGE] "):
                current_news["image"] = line.replace("[IMAGE] ", "")
            elif line == "[SUMMARY]":
                in_summary = True
                summary_lines = []
            elif line == "---":
                if "title" in current_news and "link" in current_news:
                    current_news["summary"] = "\n".join(summary_lines).strip()
                    news_list.append(current_news)
                current_news = {}
                summary_lines = []
                in_summary = False
            elif in_summary:
                summary_lines.append(line)

    return news_list


def write_report(path, report_title, news_list):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {report_title}\n\n")
        for item in news_list:
            f.write(f"## {item['title']}\n\n")
            
            translated_title, eng_sum, kor_sum, tone_tag = parse_summary_blocks(item.get('summary', ''))
            
            if translated_title:
                f.write(f"**번역 제목**: {translated_title}\n\n")
                
            if item.get("published"):
                f.write(f"**날짜**: {item['published']}\n")
            f.write(f"**링크**: [원문 기사 보러가기]({item['link']})\n\n")
            
            if item.get("image"):
                f.write(f"![썸네일 이미지]({item['image']})\n\n")
            
            f.write("### 요약 (Original)\n")
            if eng_sum:
                for line in eng_sum:
                    f.write(f"- {line}\n")
            else:
                f.write("요약 정보 없음\n")
            f.write("\n")
                
            f.write("### 번역 (Translated)\n")
            if kor_sum:
                for line in kor_sum:
                    f.write(f"- {line}\n")
            else:
                # 파싱 실패 시 원본 전체 출력
                f.write(f"{item.get('summary', '')}\n")
            f.write("\n")
                
            if tone_tag:
                f.write(f"**태그**: {tone_tag}\n\n")
            
            f.write("---\n\n")


def parse_summary_blocks(summary_text):
    lines = [line.strip() for line in summary_text.splitlines() if line.strip()]
    
    translated_title = ""
    english_summary = []
    korean_summary = []
    tone_tag = ""
    
    current_section = None
    
    for line in lines:
        if line.startswith("**[기사 제목 번역]**"):
            current_section = "translated_title"
            continue
        elif line.startswith("**[영문 3줄 요약"):
            current_section = "english_summary"
            continue
        elif line.startswith("**[국문 3줄 요약"):
            current_section = "korean_summary"
            continue
            
        if "#긍정" in line or "#부정" in line or "#중립" in line:
            for tag in ["#긍정", "#부정", "#중립"]:
                if tag in line:
                    tone_tag = tag
                    break
            continue
            
        if current_section == "translated_title":
            translated_title += line + " "
        elif current_section == "english_summary":
            if line.startswith("-"):
                english_summary.append(line.lstrip("-").strip())
        elif current_section == "korean_summary":
            if line.startswith("-"):
                korean_summary.append(line.lstrip("-").strip())
                
    return translated_title.strip(), english_summary, korean_summary, tone_tag


def update_index(index_path, page_title, link_path, intro_text):
    ensure_dir(os.path.dirname(index_path))
    if not os.path.exists(index_path):
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(f"# {page_title}\n\n")
            f.write(f"{intro_text}\n\n")
            f.write("### 리포트 목록\n\n")
            f.write(f"- [{os.path.basename(link_path)} 보기](./{link_path})\n")
        return

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    if link_path not in content:
        marker = "### 리포트 목록\n\n"
        if marker not in content:
            content += f"\n{marker}"
        prefix, suffix = content.split(marker, 1)
        new_content = prefix + marker + f"- [{os.path.basename(link_path)} 보기](./{link_path})\n" + suffix
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(new_content)


def save_to_markdown(news_list):
    today_text = datetime.datetime.now().strftime("%Y-%m-%d")
    today_stamp = datetime.datetime.now().strftime("%Y%m%d")
    report_name = f"{today_text}-news.md"
    folder_name = f"{today_stamp}{PUBLISH_SUFFIX}"

    unique_news = []
    seen_links = set()
    for item in news_list:
        link = item.get("link")
        if not link or link in seen_links:
            continue
        seen_links.add(link)
        unique_news.append(item)

    if not unique_news:
        print("발행할 새 기사가 없습니다.")
        return

    folder_report_path = os.path.join(folder_name, report_name)
    folder_index_path = os.path.join(folder_name, "index.md")

    write_report(folder_report_path, f"{today_text} AI 발행 확인용 리포트", unique_news)
    update_index(
        folder_index_path,
        f"{today_text} AI 뉴스 발행 확인용 페이지",
        report_name,
        "이 폴더는 GitHub Pages로 push하기 전에 발행 상태를 확인하기 위한 중간 산출물입니다."
    )

    print(f"{folder_report_path} 생성 완료 ({len(unique_news)}건)")


def main():
    print("--- 4. 마크다운 발행 파이프라인 시작 ---")
    news_list = load_summarized_news()
    save_to_markdown(news_list)
    print("--- 4. 마크다운 발행 파이프라인 종료 ---")


if __name__ == "__main__":
    main()
