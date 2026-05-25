"""
新闻抓取模块 — 百度新闻+36氪+网页抓取
确保在国内网络下能稳定获取最新新闻
"""
import hashlib
import re
import feedparser
import requests
from datetime import datetime, timedelta
from typing import Optional


# 通用请求头（模拟浏览器）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _fetch_baidu_news() -> list[dict]:
    """从百度新闻首页抓取最新新闻标题和链接"""
    news = []
    try:
        resp = requests.get("https://news.baidu.com/", headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"[百度新闻] HTTP {resp.status_code}")
            return news

        html = resp.text

        # 提取链接和标题（百度新闻首页结构）
        # 匹配 <a href="URL" ...>标题</a> 模式的新闻链接
        pattern = r'<a[^>]*href="(https?://[^"]*)"[^>]*>([^<]{10,120})</a>'
        matches = re.findall(pattern, html)

        seen = set()
        for url, title in matches:
            title = title.strip()
            # 过滤非新闻内容
            if len(title) < 10 or len(title) > 120:
                continue
            skip_words = ["©", "ICP", "京公网", "百度", "关于", "设为", "举报", "反馈",
                         "意见", "版权所有", "手机版", "客户端", "电脑版", "首页", "登录",
                         "注册", "搜索", "导航", "更多", "全部"]
            if any(w in title for w in skip_words):
                continue

            h = hashlib.md5(title.encode()).hexdigest()
            if h in seen:
                continue
            seen.add(h)

            news.append({
                "title": title,
                "link": url,
                "summary": "",
                "published": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "source_name": "百度新闻",
                "source_region": "中国/综合",
            })

        print(f"[百度新闻] 提取到 {len(news)} 条新闻")
    except Exception as e:
        print(f"[百度新闻] 抓取失败: {e}")

    return news


def _fetch_36kr_rss() -> list[dict]:
    """从36氪RSS抓取科技新闻"""
    news = []
    try:
        feed = feedparser.parse("https://36kr.com/feed")
        for entry in feed.entries[:15]:
            title = entry.get("title", "").strip()
            if not title:
                continue
            summary = entry.get("summary", "")
            summary = _clean_html(summary)[:300]
            news.append({
                "title": title,
                "link": entry.get("link", ""),
                "summary": summary,
                "published": entry.get("published", entry.get("updated", "")),
                "source_name": "36氪",
                "source_region": "中国/科技",
            })
        print(f"[36氪] RSS获取 {len(news)} 条科技新闻")
    except Exception as e:
        print(f"[36氪] 抓取失败: {e}")
    return news


def _fetch_cls_finance() -> list[dict]:
    """从财联社抓取财经快讯"""
    news = []
    try:
        # 财联社电报API
        resp = requests.get(
            "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8",
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("roll_data", [])[:15]
            for item in items:
                title = item.get("title", "").strip()
                if title:
                    news.append({
                        "title": title,
                        "link": f"https://www.cls.cn/detail/{item.get('id', '')}",
                        "summary": item.get("brief", "")[:300],
                        "published": datetime.fromtimestamp(item.get("ctime", 0)).strftime("%Y-%m-%d %H:%M"),
                        "source_name": "财联社",
                        "source_region": "中国/财经",
                    })
            print(f"[财联社] 获取 {len(news)} 条财经快讯")
    except Exception as e:
        print(f"[财联社] 抓取失败: {e}")
    return news


def _fetch_alternative() -> list[dict]:
    """备用源：直接请求一些可访问的新闻页面"""
    news = []
    alt_sources = [
        # 一些可能可用的新闻API/页面
        ("https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8", "财联社"),
    ]

    for url, name in alt_sources:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            # 尝试解析JSON
            try:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("data", {}).get("roll_data", [])
                for item in items[:20]:
                    title = item.get("title", "") or item.get("content", "")
                    if title and len(title) > 8:
                        news.append({
                            "title": title[:150],
                            "link": "",
                            "summary": item.get("brief", "")[:200],
                            "published": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "source_name": name,
                            "source_region": "中国",
                        })
            except:
                pass
        except Exception:
            pass
    return news


def get_daily_news(sources: Optional[list[dict]] = None) -> list[dict]:
    """
    获取今日新闻的主入口
    从多个国内可用源抓取，去重后返回
    """
    all_news = []
    seen = set()

    print("[新闻抓取] 开始从国内可用源抓取新闻...")

    # 1. 百度新闻
    for item in _fetch_baidu_news():
        h = hashlib.md5(item["title"].encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            all_news.append(item)

    # 2. 36氪科技新闻
    for item in _fetch_36kr_rss():
        h = hashlib.md5(item["title"].encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            all_news.append(item)

    # 3. 财联社财经新闻
    for item in _fetch_cls_finance():
        h = hashlib.md5(item["title"].encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            all_news.append(item)

    # 限制数量
    result = all_news[:20]
    print(f"[新闻抓取] 总计获取 {len(result)} 条新闻")
    return result


def _clean_html(text: str) -> str:
    """简易HTML清理"""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    return text.strip()


def format_news_for_prompt(news_list: list[dict]) -> str:
    """将新闻列表格式化为可发给AI的文本"""
    lines = []
    for i, item in enumerate(news_list, 1):
        lines.append(f"[{i}] {item['title']}")
        lines.append(f"    来源: {item['source_name']} ({item['source_region']})")
        if item.get("summary"):
            lines.append(f"    摘要: {item['summary']}")
        lines.append("")
    return "\n".join(lines)
