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
        text = resp.text[:10240]
        soup = BeautifulSoup(text, 'html.parser')
        og = soup.find('meta', attrs={'property': 'og:description'})
        if og and og.get('content'):
            desc = og['content'].strip()
        else:
            meta = soup.find('meta', attrs={'name': 'description'})
            if meta and meta.get('content'):
                desc = meta['content'].strip()
            else:
                return ''
        desc = unescape(desc)
        return desc
    except Exception:
        return ''


def _extract_hn_desc(item):
    """从 HN item 提取摘要：优先 text 字段，否则为空"""
    text = item.get('text', '')
    if text:
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

    def render_hn_item(item, i):
        desc = item.get('description', '')
        desc_html = '<p class="desc">' + desc + '</p>' if desc else ''
        return '''<li class="item">
            <span class="num">''' + str(i) + '''</span>
            <div class="content">
                <a href="''' + item['url'] + '''" target="_blank" class="title">''' + item['title'] + '''</a>
                <div class="meta">
                    <span class="score">''' + str(item['score']) + ''' pts</span>
                    <span class="by">by ''' + item['by'] + '''</span>
                    <a href="''' + item['hn_url'] + '''" target="_blank" class="comments">''' + str(item['comments']) + ''' comments</a>
                </div>
                ''' + desc_html + '''
            </div>
        </li>'''

    def render_gh_item(item, i):
        return '''<li class="item">
            <span class="num">''' + str(i) + '''</span>
            <div class="content">
                <a href="''' + item['url'] + '''" target="_blank" class="title">''' + item['name'] + '''</a>
                <div class="meta">
                    <span class="score">''' + item['stars'] + '''</span>
                    <span class="today">+''' + item['today_stars'] + ''' today</span>
                    <span class="lang">''' + item['language'] + '''</span>
                </div>
                <p class="desc">''' + item['description'] + '''</p>
            </div>
        </li>'''

    def render_hn_list(items, title, extra_class=''):
        items_html = '\n'.join(render_hn_item(item, i) for i, item in enumerate(items, 1))
        cls = 'hn-section ' + extra_class if extra_class else 'hn-section'
        return '''<section class="section ''' + cls + '''">
    <h2>''' + title + '''</h2>
    <ul class="list hn-list">''' + items_html + '''</ul>
</section>'''

    def render_gh_list(items, extra_class=''):
        items_html = '\n'.join(render_gh_item(item, i) for i, item in enumerate(items, 1))
        cls = 'gh-section ' + extra_class if extra_class else 'gh-section'
        return '''<section class="section ''' + cls + '''">
    <h2>GitHub Trending</h2>
    <ul class="list gh-list">''' + items_html + '''</ul>
</section>'''

    hn_top_html = render_hn_list(hn_top, 'Hacker News Top', 'hn-top')
    hn_ask_html = render_hn_list(hn_ask, 'Ask HN', 'ask')
    hn_show_html = render_hn_list(hn_show, 'Show HN', 'show')
    gh_html = render_gh_list(gh_trending, 'gh')

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>趋势日报 ''' + today_str + '''</title>
    <style>
        :root {
            --bg: #0a0a0f;
            --card: #111118;
            --border: #1e1e2e;
            --text: #e4e4e7;
            --muted: #71717a;
            --accent: #f97316;
            --hn: #ff6600;
            --gh: #238636;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html { scroll-behavior: smooth; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }
        a { color: inherit; text-decoration: none; }
        .container { max-width: 1600px; margin: 0 auto; padding: 40px 32px; }

        /* Header */
        header { text-align: center; margin-bottom: 40px; }
        header h1 { font-size: 2.2rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 8px; }
        header h1 span { color: var(--accent); }
        header .date { color: var(--muted); font-size: 0.9rem; }

        /* Grid */
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-areas:
                "gh hn-top"
                "ask show";
            gap: 20px;
        }
        .hn-top { grid-area: hn-top; }
        .ask { grid-area: ask; }
        .show { grid-area: show; }
        .gh { grid-area: gh; }

        /* Section */
        .section {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }
        .section h2 {
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
            color: var(--hn);
        }
        .gh-section h2 { color: var(--gh); }
        .ask h2 { color: var(--accent); }
        .show h2 { color: #a855f7; }

        /* List */
        .list { list-style: none; }
        .item {
            display: flex;
            gap: 12px;
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
            transition: background 0.15s;
        }
        .item:last-child { border-bottom: none; }
        .item:hover { background: rgba(255,255,255,0.02); }
        .num {
            flex-shrink: 0;
            width: 24px;
            height: 24px;
            background: var(--border);
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--muted);
        }
        .content { flex: 1; min-width: 0; }
        .title {
            color: var(--text);
            font-size: 0.9rem;
            font-weight: 500;
            display: block;
            margin-bottom: 6px;
            line-height: 1.4;
        }
        .title:hover { color: var(--accent); }
        .meta {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            font-size: 0.78rem;
            color: var(--muted);
        }
        .meta .score { color: #fbbf24; }
        .meta a.comments { color: var(--muted); }
        .meta a.comments:hover { color: var(--text); }
        .desc {
            color: var(--muted);
            font-size: 0.82rem;
            margin-top: 6px;
            line-height: 1.5;
        }

        /* Footer */
        footer {
            text-align: center;
            padding: 32px 20px;
            color: var(--muted);
            font-size: 0.82rem;
        }
        footer a { color: var(--accent); }
        footer a:hover { text-decoration: underline; }
        footer .sources { margin-bottom: 8px; }
        .archive-link {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--card);
            border: 1px solid var(--border);
            padding: 10px 20px;
            border-radius: 8px;
            margin-top: 16px;
            transition: all 0.15s;
        }
        .archive-link:hover {
            border-color: var(--accent);
            color: var(--accent);
        }

        /* Responsive */
        @media (max-width: 900px) {
            .grid { grid-template-columns: 1fr; }
            .gh, .hn-top, .ask, .show { grid-area: auto; }
        }
        @media (max-width: 600px) {
            .container { padding: 20px 12px; }
            header h1 { font-size: 1.5rem; }
            .item { padding: 12px 14px; }
            .section h2 { padding: 12px 14px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>趋势日报</h1>
            <p class="date">''' + today_str + ''' · Hacker News + GitHub Trending</p>
        </header>

        <div class="grid">
            ''' + hn_top_html + '''
            ''' + hn_ask_html + '''
            ''' + hn_show_html + '''
            ''' + gh_html + '''
        </div>

        <footer>
            <p class="sources">
                数据来源: <a href="https://github.com/trending" target="_blank">GitHub Trending</a> ·
                <a href="https://news.ycombinator.com" target="_blank">Hacker News</a>
            </p>
            <a href="./archive/" class="archive-link">历史存档</a>
        </footer>
    </div>
</body>
</html>'''
    return html


def generate_archive_index():
    """Generate archive/index.html listing all archived days"""
    ARCHIVE_INDEX = ARCHIVE_DIR / "index.html"

    # 读取所有归档，按日期倒序
    archives = sorted(ARCHIVE_DIR.glob("*.html"), reverse=True)

    def render_archive_item(path):
        date_str = path.stem
        try:
            content = path.read_text(encoding='utf-8')
            import re
            match = re.search(r'<h1>.*?<span>(.*?)</span>', content)
            preview = match.group(1)[:50] if match else ''
        except Exception:
            preview = ''

        return '<a href="' + date_str + '.html" class="card">\n            <span class="date">' + date_str + '</span>\n            <span class="preview">' + preview + '</span>\n        </a>'

    cards_html = '\n'.join(render_archive_item(p) for p in archives)

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>历史存档 — 趋势日报</title>
    <style>
        :root {
            --bg: #0a0a0f;
            --card: #111118;
            --border: #1e1e2e;
            --text: #e4e4e7;
            --muted: #71717a;
            --accent: #f97316;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }
        a { color: inherit; text-decoration: none; }
        .container { max-width: 900px; margin: 0 auto; padding: 40px 20px; }
        header { margin-bottom: 32px; }
        header h1 { font-size: 1.8rem; font-weight: 700; margin-bottom: 8px; }
        header h1 span { color: var(--accent); }
        header .sub { color: var(--muted); font-size: 0.9rem; }
        .back { display: inline-flex; align-items: center; gap: 6px; color: var(--muted); font-size: 0.85rem; margin-bottom: 20px; }
        .back:hover { color: var(--accent); }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
        .card {
            display: flex;
            flex-direction: column;
            gap: 6px;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px 18px;
            transition: all 0.15s;
        }
        .card:hover { border-color: var(--accent); transform: translateY(-2px); }
        .card .date { font-weight: 600; font-size: 0.95rem; }
        .card .preview { color: var(--muted); font-size: 0.82rem; line-height: 1.4; }
        .empty { color: var(--muted); text-align: center; padding: 60px 0; }
        footer { text-align: center; padding: 40px 20px; color: var(--muted); font-size: 0.82rem; }
        footer a { color: var(--accent); }
        @media (max-width: 600px) {
            .container { padding: 20px 12px; }
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="../index.html" class="back">回到今日</a>
        <header>
            <h1>历史存档</h1>
            <p class="sub">共 ''' + str(len(archives)) + ''' 期</p>
        </header>
        <div class="grid">
            ''' + (cards_html if cards_html else '<p class="empty">暂无存档</p>') + '''
        </div>
        <footer>
            <p>数据来源: <a href="https://news.ycombinator.com" target="_blank">Hacker News</a> · <a href="https://github.com/trending" target="_blank">GitHub Trending</a></p>
        </footer>
    </div>
</body>
</html>'''
    ARCHIVE_INDEX.write_text(html, encoding='utf-8')


def generate_archive_html(hn_top, hn_ask, hn_show, gh_trending):
    """Generate archive HTML page"""

    def format_hn_list(items, title):
        items_html = ''
        for i, item in enumerate(items, 1):
            items_html += '<li><a href="' + item['url'] + '" target="_blank">' + item['title'] + '</a> — ' + str(item['score']) + ' pts</li>\n'
        return '<section class="section"><h2>' + title + '</h2><ul>' + items_html + '</ul></section>'

    def format_gh_list(items):
        items_html = ''
        for i, item in enumerate(items, 1):
            items_html += '<li><a href="' + item['url'] + '" target="_blank">' + item['name'] + '</a> — ' + item['stars'] + ' (今日+' + item['today_stars'] + ') — ' + item['description'] + '</li>\n'
        return '<section class="section"><h2>GitHub Trending</h2><ul>' + items_html + '</ul></section>'

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>趋势日报 ''' + today_str + '''</title>
    <style>
        :root { --bg: #0a0a0f; --card: #111118; --border: #1e1e2e; --text: #e4e4e7; --muted: #71717a; --accent: #f97316; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; min-height: 100vh; }
        a { color: inherit; text-decoration: none; }
        .container { max-width: 1100px; margin: 0 auto; padding: 40px 24px; }
        header { margin-bottom: 32px; }
        header h1 { font-size: 1.8rem; font-weight: 700; margin-bottom: 8px; }
        header h1 span { color: var(--accent); }
        header .date { color: var(--muted); font-size: 0.9rem; }
        .back { display: inline-flex; align-items: center; gap: 6px; color: var(--muted); font-size: 0.85rem; margin-bottom: 20px; }
        .back:hover { color: var(--accent); }
        .section { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px 24px; margin-bottom: 16px; }
        .section h2 { font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent); margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
        .section ul { list-style: none; }
        .section li { padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
        .section li:last-child { border-bottom: none; }
        .section li a:hover { color: var(--accent); }
        footer { text-align: center; padding: 32px 20px; color: var(--muted); font-size: 0.82rem; }
        footer a { color: var(--accent); }
        @media (max-width: 600px) { .container { padding: 20px 12px; } }
    </style>
</head>
<body>
    <div class="container">
        <a href="../index.html" class="back">← 回到今日</a>
        <header>
            <h1>趋势日报 <span>''' + today_str + '''</span></h1>
            <p class="date">Hacker News + GitHub Trending</p>
        </header>
        ''' + format_hn_list(hn_top, 'HN Top 20') + '''
        ''' + format_hn_list(hn_ask, 'Ask HN') + '''
        ''' + format_hn_list(hn_show, 'Show HN') + '''
        ''' + format_gh_list(gh_trending) + '''
        <footer>
            <p>数据来源: <a href="https://news.ycombinator.com" target="_blank">Hacker News</a> · <a href="https://github.com/trending" target="_blank">GitHub Trending</a></p>
        </footer>
    </div>
</body>
</html>'''
    return html


def build_wechat_message(hn_top, hn_ask, hn_show, gh_trending):
    """Build WeChat notification message"""
    lines = ["趋势日报 " + today_str + "\n"]
    lines.append("HN热门")
    for i, item in enumerate(hn_top[:5], 1):
        lines.append(str(i) + ". " + item['title'][:40])
    lines.append("")
    lines.append("Ask HN")
    for i, item in enumerate(hn_ask[:3], 1):
        lines.append(str(i) + ". " + item['title'][:40])
    lines.append("")
    lines.append("GitHub Trending")
    for i, item in enumerate(gh_trending[:3], 1):
        lines.append(str(i) + ". " + item['name'] + " " + item['stars'])
    lines.append("")
    lines.append("完整内容：http://econow.cn/trends-daily/")
    return "\n".join(lines)


def git_push():
    """Git add + commit + push"""
    import subprocess
    try:
        subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "commit", "-m", "Auto update " + today_str], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "push"], cwd=REPO_DIR, check=True)
        print("Git push done")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")
        return False


def main():
    print("Fetching trends for " + today_str + "...")

    print("Fetching HN Top 20...")
    hn_top = fetch_hn_top(20)

    print("Fetching Ask HN...")
    hn_ask = fetch_hn_ask(20)

    print("Fetching Show HN...")
    hn_show = fetch_hn_show(20)

    print("Fetching GitHub Trending...")
    gh_trending = fetch_github_trending()

    # 为 HN 条目补充 description
    print("Enriching HN descriptions...")
    all_hn = hn_top + hn_ask + hn_show
    desc_count = 0

    def enrich_item(item):
        desc = _extract_hn_desc(item)
        if desc:
            item['description'] = desc
            return True
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
    print("  " + str(desc_count) + "/" + str(len(all_hn)) + " items got descriptions")

    # Generate index.html
    print("Generating index.html...")
    html = generate_html(hn_top, hn_ask, hn_show, gh_trending)
    index_path = REPO_DIR / "index.html"
    index_path.write_text(html, encoding='utf-8')

    # Generate archive
    print("Generating archive...")
    ARCHIVE_DIR.mkdir(exist_ok=True)
    html = generate_archive_html(hn_top, hn_ask, hn_show, gh_trending)
    archive_path = ARCHIVE_DIR / (today_str + ".html")
    archive_path.write_text(html, encoding='utf-8')

    # Generate archive index page
    print("Generating archive index...")
    generate_archive_index()

    # Build WeChat message
    wechat_msg = build_wechat_message(hn_top, hn_ask, hn_show, gh_trending)
    msg_path = REPO_DIR / "wechat_message.txt"
    msg_path.write_text(wechat_msg, encoding='utf-8')
    print("WeChat message saved to " + str(msg_path))

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
    print("Data saved to " + str(data_path))

    # Git push (if repo exists)
    git_push()

    print("\nDone! " + today_str)
    print("HN Top: " + str(len(hn_top)) + ", Ask: " + str(len(hn_ask)) + ", Show: " + str(len(hn_show)) + ", GitHub: " + str(len(gh_trending)))

    return data


if __name__ == "__main__":
    main()
