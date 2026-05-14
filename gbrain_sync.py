#!/usr/bin/env python3
"""
分析当天 trends 数据，把值得注意的信号写入 gbrain
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fetch_trends import REPO_DIR

CST = timezone(timedelta(hours=8))

# AI/编程相关的关键词，用于判断是否值得记录
AI_KEYWORDS = [
    'ai', 'llm', 'gpt', 'claude', 'cursor', 'copilot', 'agent',
    'vibe coding', 'vibe', 'model', 'openai', 'anthropic',
    'machine learning', 'neural', 'rag', 'embed', 'inference',
    'python', 'rust', 'golang', 'typescript', 'javascript',
    'devops', 'kubernetes', 'docker', 'cloud', 'aws', 'deployment',
    'database', 'postgres', 'sqlite', 'vector', 'sqlite'
]

TOOL_KEYWORDS = [
    'tool', 'cli', 'app', 'launch', 'show hn', 'open source',
    'library', 'framework', 'api', 'sdk', 'plugin', 'extension',
    'saas', 'platform', 'service', 'generator', 'builder'
]

SIGNAL_KEYWORDS = [
    'free', 'open source', 'launch', 'new', 'first', 'releases',
    'breaking', 'viral', 'trending', 'fast', 'better', 'faster'
]


def is_interesting(item, min_score=50, check_url=False):
    """判断一条内容是否值得写入 gbrain"""
    title = item.get('title', item.get('name', '')).lower()
    desc = item.get('description', '').lower()
    score = item.get('score', item.get('stars', 0))

    if score < min_score:
        return False, ''

    text = title + ' ' + desc

    # AI/编程相关
    for kw in AI_KEYWORDS:
        if kw in text:
            return True, f'ai_keyword:{kw}'

    # 工具类
    for kw in TOOL_KEYWORDS:
        if kw in text:
            return True, f'tool:{kw}'

    # 信号词
    for kw in SIGNAL_KEYWORDS:
        if kw in text:
            return True, f'signal:{kw}'

    return False, ''


def extract_hn_signals(hn_top, hn_ask, hn_show):
    """从 HN 数据中提取值得注意的信号"""
    signals = {'top': [], 'ask': [], 'show': []}

    for category, items in [('top', hn_top), ('ask', hn_ask), ('show', hn_show)]:
        for item in items:
            interesting, reason = is_interesting(item)
            if interesting:
                signals[category].append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'score': item.get('score', 0),
                    'comments': item.get('comments', 0),
                    'by': item.get('by', ''),
                    'hn_url': item.get('hn_url', ''),
                    'reason': reason,
                    'description': item.get('description', '')
                })

    return signals


def extract_gh_signals(gh_trending):
    """从 GitHub Trending 中提取值得注意的信号"""
    signals = []

    for item in gh_trending:
        stars = item.get('stars', '0')
        # 解析 stars 数字
        try:
            stars_num = int(stars.replace(',', '').replace('k', '000').replace('K', '000'))
        except:
            stars_num = 0

        title = item.get('name', '').lower()
        desc = item.get('description', '').lower()
        text = title + ' ' + desc

        interesting = False
        reason = ''

        if stars_num > 1000:
            interesting = True
            reason = 'high_stars'
        else:
            for kw in AI_KEYWORDS + TOOL_KEYWORDS:
                if kw in text:
                    interesting = True
                    reason = f'keyword:{kw}'
                    break

        if interesting:
            signals.append({
                'name': item.get('name', ''),
                'url': item.get('url', ''),
                'stars': item.get('stars', ''),
                'today_stars': item.get('today_stars', ''),
                'language': item.get('language', ''),
                'description': item.get('description', ''),
                'reason': reason
            })

    return signals


def build_gbrain_page_content(date_str, hn_signals, gh_signals, raw_data=None):
    """生成 gbrain 页面的 markdown 内容"""

    # HN Top 信号
    hn_top_lines = []
    for item in hn_signals.get('top', [])[:10]:
        hn_top_lines.append(
            f"- [{item['title']}]({item['url']}) "
            f"({item['score']} pts, [{item['comments']} comments]({item['hn_url']})) "
            f"via @{item['by']} - {item['reason']}"
        )

    hn_ask_lines = []
    for item in hn_signals.get('ask', [])[:5]:
        hn_ask_lines.append(
            f"- [{item['title']}]({item['url']}) "
            f"({item['score']} pts, [{item['comments']} comments]({item['hn_url']})) "
            f"via @{item['by']}"
        )

    hn_show_lines = []
    for item in hn_signals.get('show', [])[:5]:
        hn_show_lines.append(
            f"- [{item['title']}]({item['url']}) "
            f"({item['score']} pts, [{item['comments']} comments]({item['hn_url']})) "
            f"via @{item['by']}"
        )

    gh_lines = []
    for item in gh_signals[:10]:
        gh_lines.append(
            f"- [{item['name']}]({item['url']}) "
            f"({item['stars']}, +{item['today_stars']} today) "
            f"[{item['language']}] - {item['description'][:80]} - {item['reason']}"
        )

    content = f"""---
date: {date_str}
type: trends-daily
tags: [hacker-news, github-trending, trends]
---

# Trends Daily — {date_str}

## HN Top ({len(hn_signals.get('top', []))} notable items)

{chr(10).join(hn_top_lines) if hn_top_lines else '_None above threshold_'}

## Ask HN ({len(hn_signals.get('ask', []))} notable items)

{chr(10).join(hn_ask_lines) if hn_ask_lines else '_None above threshold_'}

## Show HN ({len(hn_signals.get('show', []))} notable items)

{chr(10).join(hn_show_lines) if hn_show_lines else '_None above threshold_'}

## GitHub Trending ({len(gh_signals)} notable items)

{chr(10).join(gh_lines) if gh_lines else '_None above threshold_'}

---

_Extracted from trends-daily on {date_str}_
"""
    return content


def save_to_gbrain(date_str, content, slug):
    """写入 gbrain（通过调用 gbrain MCP 工具）"""
    # 这个函数由调用方通过 MCP 工具实现
    pass


def generate_trends_summary():
    """生成趋势摘要（供 gbrain 使用）"""
    data_path = REPO_DIR / "data.json"
    if not data_path.exists():
        print("No data.json found, skipping")
        return None

    data = json.loads(data_path.read_text())
    date_str = data.get('date', datetime.now(CST).strftime("%Y-%m-%d"))

    hn_signals = extract_hn_signals(
        data.get('hn_top', []),
        data.get('hn_ask', []),
        data.get('hn_show', [])
    )

    gh_signals = extract_gh_signals(data.get('gh_trending', []))

    content = build_gbrain_page_content(date_str, hn_signals, gh_signals, data)

    return {
        'date': date_str,
        'slug': f'trends-daily-{date_str}',
        'content': content,
        'hn_signals': hn_signals,
        'gh_signals': gh_signals
    }


def save_signals_json(date_str, hn_signals, gh_signals):
    """把提取的信号存为 JSON 文件，供 gbrain cron job 读取"""
    import os
    output = {
        'date': date_str,
        'slug': f'trends-daily-{date_str}',
        'hn_signals': hn_signals,
        'gh_signals': gh_signals
    }
    # 存到 trends-daily 目录下
    out_path = Path(__file__).parent / 'trends_signals.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Signals saved to {out_path}")
    return out_path


if __name__ == "__main__":
    result = generate_trends_summary()
    if result:
        print(f"Generated trends summary for {result['date']}")
        print(f"Slug: {result['slug']}")
        print(f"HN Top signals: {len(result['hn_signals']['top'])}")
        print(f"HN Ask signals: {len(result['hn_signals']['ask'])}")
        print(f"HN Show signals: {len(result['hn_signals']['show'])}")
        print(f"GH signals: {len(result['gh_signals'])}")

        # 保存为 JSON
        save_signals_json(result['date'], result['hn_signals'], result['gh_signals'])
