#!/usr/bin/env python3
"""
trends-daily fetcher
Fetch HN trends + GitHub Trending, generate index.html + archive
"""

import requests
import os
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from bs4 import BeautifulSoup
from html import unescape

# Config
HN_BASE = "https://hacker-news.firebaseio.com/v0"
GITHUB_TRENDING_URL = "https://github.com/trending"
REPO_DIR = Path(__file__).parent
ARCHIVE_DIR = REPO_DIR / "archive"

# Timezone: CST = UTC+8
CST = timezone(timedelta(hours=8))
today_str = datetime.now(CST).strftime("%Y-%m-%d")


def fetch_hn_top(n=20):
    """Fetch HN Top stories"""
    ids = requests.get(f"{HN_BASE}/topstories.json", timeout=10).json()[:n]
    items = []
    for i in ids:
        try:
            item = requests.get(f"{HN_BASE}/item/{i}.json", timeout=10).json()
            if item:
                items.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", "") or f"https://news.ycombinator.com/item?id={i}",
                    "score": item.get("score", 0),
                    "by": item.get("by", ""),
                    "comments": item.get("descendants", 0),
                    "hn_url": f"https://news.ycombinator.com/item?id={i}",
                    "text": item.get("text", ""),
                })
        except Exception as e:
            print(f"Error fetching HN item {i}: {e}")
    return items


def fetch_hn_ask(n=5):
    """Fetch HN Ask HN"""
    ids = requests.get(f"{HN_BASE}/askstories.json", timeout=10).json()[:n]
    items = []
    for i in ids:
        try:
            item = requests.get(f"{HN_BASE}/item/{i}.json", timeout=10).json()
            if item:
                items.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", "") or f"https://news.ycombinator.com/item?id={i}",
                    "score": item.get("score", 0),
                    "by": item.get("by", ""),
                    "comments": item.get("descendants", 0),
                    "hn_url": f"https://news.ycombinator.com/item?id={i}",
                    "text": item.get("text", ""),
                })
        except Exception as e:
            print(f"Error fetching HN item {i}: {e}")
    return items


def fetch_hn_show(n=5):
    """Fetch HN Show HN"""
    ids = requests.get(f"{HN_BASE}/showstories.json", timeout=10).json()[:n]
    items = []
    for i in ids:
        try:
            item = requests.get(f"{HN_BASE}/item/{i}.json", timeout=10).json()
            if item:
                items.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", "") or f"https://news.ycombinator.com/item?id={i}",
                    "score": item.get("score", 0),
                    "by": item.get("by", ""),
                    "comments": item.get("descendants", 0),
                    "hn_url": f"https://news.ycombinator.com/item?id={i}",
                    "text": item.get("text", ""),
                })
        except Exception as e:
            print(f"Error fetching HN item {i}: {e}")
    return items


def fetch_url_description(url, timeout=5):
    """抓取目标 URL 的 og:description 或 meta description，取前 150 字"""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        # 只解析前 10KB，够拿到 head 了
        text = resp.text[:10240]
        soup = BeautifulSoup(text, 'html.parser')

        # 优先 og:description
        og = soup.find('meta', attrs={'property': 'og:description'})
        if og and og.get('content'):
            desc = og['content'].strip()
        else:
            meta = soup.find('meta', attrs={'name': 'description'})
            if meta and meta.get('content'):
                desc = meta['content'].strip()
            else:
                return ''

        # 清理 HTML 实体，截断
        desc = unescape(desc)
        if len(desc) > 500:
            desc = desc[:497] + '...'
        return desc
    except Exception:
        return ''


def _extract_hn_desc(item):
    """从 HN item 提取摘要：优先 text 字段，否则为空（后续批量抓 URL）"""
    text = item.get('text', '')
    if text:
        # HN text 是 HTML，去掉标签
        clean = BeautifulSoup(text, 'html.parser').get_text().strip()
        if len(clean) > 500:
            clean = clean[:497] + '...'
        return clean
    return ''


def fetch_github_trending():
    """Fetch GitHub Trending using BeautifulSoup"""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    try:
        resp = requests.get(GITHUB_TRENDING_URL, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"GitHub Trending fetch failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    articles = soup.find_all('article', class_='Box-row')
    items = []

    for article in articles[:20]:
        h2 = article.find('h2')
        repo_name = ''
        link = ''
        if h2:
            a = h2.find('a')
            if a:
                href = a.get('href', '').strip('/')
                repo_name = href
                link = f"https://github.com/{href}"

        desc = ''
        p = article.find('p', class_='color-fg-muted')
        if p:
            desc = p.get_text().strip()

        lang = ''
        span = article.find('span', itemprop='programmingLanguage')
        if span:
            lang = span.get_text().strip()

        stars = ''
        stars_link = article.find('a', href=lambda h: h and '/stargazers' in h)
        if stars_link:
            stars = stars_link.get_text().strip()

        today = ''
        for span in article.find_all('span'):
            text = span.get_text()
            if 'today' in text.lower():
                today = text.strip()
                break

        if repo_name:
            items.append({
                "name": repo_name,
                "url": link,
                "description": desc,
                "language": lang,
                "stars": stars,
                "today_stars": today.replace(' stars today', '').replace(' star today', '')
            })

    return items


def generate_html(hn_top, hn_ask, hn_show, gh_trending):
    """Generate index.html"""

    def render_hn_list(items, title, icon):
        html = f'<section class="section"><h2>{icon} {title}</h2><ul class="list">'
        for i, item in enumerate(items, 1):
            desc_html = ''
            if item.get('description'):
                desc_html = f'<p class="desc">{item["description"]}</p>'
            html += f'''<li class="item">
                <a href="{item['url']}" target="_blank" class="title">{i}. {item['title']}</a>
                <span class="meta">⭐ {item['score']} · {item['by']} · <a href="{item['hn_url']}">💬 {item['comments']}</a></span>
                {desc_html}
            </li>'''
        html += '</ul></section>'
        return html

    def render_gh_list(items):
        html = '<section class="section"><h2>📦 GitHub 热门</h2><ul class="list">'
        for i, item in enumerate(items, 1):
            html += f'''<li class="item">
                <a href="{item['url']}" target="_blank" class="title">{i}. {item['name']}</a>
                <span class="meta">⭐ {item['stars']} (今日+{item['today_stars']}) · {item['language']}</span>
                <p class="desc">{item['description']}</p>
            </li>'''
        html += '</ul></section>'
        return html

    hn_top_html = render_hn_list(hn_top, 'HN 热门 Top 20', '🔥')
    hn_ask_html = render_hn_list(hn_ask, 'Ask HN — 大家在问', '💬')
    hn_show_html = render_hn_list(hn_show, 'Show HN — 大家在秀', '🎨')
    gh_html = render_gh_list(gh_trending)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>趋势日报 {today_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #e6edf3; padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: #161b22; border-radius: 12px; }}
        header h1 {{ font-size: 1.8em; margin-bottom: 8px; }}
        header .date {{ color: #8b949e; font-size: 0.95em; }}
        .section {{ background: #161b22; border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
        .section h2 {{ font-size: 1.2em; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #30363d; }}
        .list {{ list-style: none; }}
        .item {{ padding: 12px 0; border-bottom: 1px solid #21262d; }}
        .item:last-child {{ border-bottom: none; }}
        .title {{ color: #58a6ff; text-decoration: none; font-size: 1em; }}
        .title:hover {{ text-decoration: underline; }}
        .meta {{ display: block; color: #8b949e; font-size: 0.85em; margin-top: 4px; }}
        .meta a {{ color: #8b949e; text-decoration: none; }}
        .meta a:hover {{ text-decoration: underline; }}
        .desc {{ color: #8b949e; font-size: 0.9em; margin-top: 6px; }}
        .footer {{ text-align: center; color: #8b949e; font-size: 0.85em; margin-top: 30px; }}
        .footer a {{ color: #58a6ff; text-decoration: none; }}
        @media (max-width: 600px) {{ body {{ padding: 10px; }} .section {{ padding: 15px; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 趋势日报</h1>
            <p class="date">{today_str} · HN Top + Ask/Show + GitHub Trending</p>
        </header>
        {hn_top_html}
        {hn_ask_html}
        {hn_show_html}
        {gh_html}
        <footer class="footer">
            <p>📦 数据来源: <a href="https://github.com/trending" target="_blank">GitHub Trending</a> · <a href="https://news.ycombinator.com" target="_blank">Hacker News</a></p>
            <p>📅 历史存档: <a href="./archive/" target="_blank">archive/</a></p>
        </footer>
    </div>
</body>
</html>'''
    return html


def generate_archive_md(hn_top, hn_ask, hn_show, gh_trending):
    """Generate archive markdown"""

    def format_hn_list(items, title):
        md = f'## {title}\n\n'
        for i, item in enumerate(items, 1):
            md += f'{i}. [{item["title"]}]({item["url"]}) — ⭐{item["score"]}\n'
        return md

    def format_gh_list(items):
        md = '## GitHub Trending\n\n'
        for i, item in enumerate(items, 1):
            md += f'{i}. [{item["name"]}]({item["url"]}) — ⭐{item["stars"]} (今日+{item["today_stars"]}) — {item["description"]}\n'
        return md

    md = f'''# 趋势日报 — {today_str}

> 自动生成 · 数据来源: Hacker News + GitHub Trending

---

{format_hn_list(hn_top, "HN Top 20")}
{format_hn_list(hn_ask, "Ask HN")}
{format_hn_list(hn_show, "Show HN")}
{format_gh_list(gh_trending)}

---

*此文件由 trends-daily 自动生成*
'''
    return md


def build_wechat_message(hn_top, hn_ask, hn_show, gh_trending):
    """Build WeChat notification message"""

    lines = [f"📊 趋势日报 {today_str}\n"]

    lines.append("🔥 HN热门")
    for i, item in enumerate(hn_top[:5], 1):
        lines.append(f"{i}. {item['title'][:40]}")
    lines.append("")

    lines.append("💬 Ask HN")
    for i, item in enumerate(hn_ask[:3], 1):
        lines.append(f"{i}. {item['title'][:40]}")
    lines.append("")

    lines.append("📦 GitHub 🔥")
    for i, item in enumerate(gh_trending[:3], 1):
        lines.append(f"{i}. {item['name']} ⭐{item['stars']}")
    lines.append("")

    lines.append(f"👆 完整内容：http://econow.cn/trends-daily/")

    return "\n".join(lines)


def git_push():
    """Git add + commit + push"""
    import subprocess
    try:
        subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "commit", "-m", f"Auto update {today_str}"], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "push"], cwd=REPO_DIR, check=True)
        print("Git push done")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")
        return False


def main():
    print(f"Fetching trends for {today_str}...")

    # Fetch all data
    print("Fetching HN Top 20...")
    hn_top = fetch_hn_top(20)

    print("Fetching Ask HN...")
    hn_ask = fetch_hn_ask(5)

    print("Fetching Show HN...")
    hn_show = fetch_hn_show(5)

    print("Fetching GitHub Trending...")
    gh_trending = fetch_github_trending()

    # 为 HN 条目补充 description
    print("Enriching HN descriptions...")
    all_hn = hn_top + hn_ask + hn_show
    desc_count = 0

    def enrich_item(item):
        # 先尝试 HN 自带 text（Ask/Show 有）
        desc = _extract_hn_desc(item)
        if desc:
            item['description'] = desc
            return True
        # 否则抓目标 URL 的 meta description
        url = item.get('url', '')
        if url and not url.startswith('https://news.ycombinator.com'):
            desc = fetch_url_description(url)
            item['description'] = desc
            return bool(desc)
        item['description'] = ''
        return False

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(enrich_item, item): i for i, item in enumerate(all_hn)}
        for future in as_completed(futures):
            try:
                if future.result():
                    desc_count += 1
            except Exception:
                pass
    print(f"  {desc_count}/{len(all_hn)} items got descriptions")

    # Generate index.html
    print("Generating index.html...")
    html = generate_html(hn_top, hn_ask, hn_show, gh_trending)
    index_path = REPO_DIR / "index.html"
    index_path.write_text(html, encoding='utf-8')

    # Generate archive
    print("Generating archive...")
    ARCHIVE_DIR.mkdir(exist_ok=True)
    md = generate_archive_md(hn_top, hn_ask, hn_show, gh_trending)
    archive_path = ARCHIVE_DIR / f"{today_str}.md"
    archive_path.write_text(md, encoding='utf-8')

    # Build WeChat message
    wechat_msg = build_wechat_message(hn_top, hn_ask, hn_show, gh_trending)
    msg_path = REPO_DIR / "wechat_message.txt"
    msg_path.write_text(wechat_msg, encoding='utf-8')
    print(f"WeChat message saved to {msg_path}")

    # Save data for later use
    data = {
        "date": today_str,
        "hn_top": hn_top,
        "hn_ask": hn_ask,
        "hn_show": hn_show,
        "gh_trending": gh_trending
    }
    data_path = REPO_DIR / "data.json"
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Data saved to {data_path}")

    # Git push (if repo exists)
    git_push()

    print(f"\nDone! {today_str}")
    print(f"HN Top: {len(hn_top)}, Ask: {len(hn_ask)}, Show: {len(hn_show)}, GitHub: {len(gh_trending)}")

    return data


if __name__ == "__main__":
    main()
