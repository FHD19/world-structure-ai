"""
新闻抓取模块 — 多源抓取（百度/新浪/163/头条/36氪/IT之家/财联社/凤凰网）
总共8个来源，确保在国内网络下能稳定获取最新新闻
"""
import hashlib
import json
import re
import feedparser
import requests
from datetime import datetime
from typing import Optional


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

SKIP_WORDS = ["©", "ICP", "京公网", "百度", "关于", "设为", "举报", "反馈",
              "意见", "版权所有", "手机版", "客户端", "电脑版", "首页", "登录",
              "注册", "搜索", "导航", "更多", "全部", "广告", "推广", "服务协议",
              "隐私政策", "用户协议", "法律声明", "网站地图", "English", "APP",
              "下载", "微信", "微博", "二维码", "扫一扫", "点击加载", "查看更多",
              "正在加载", "评论", "分享到", "Copyright", "营业执照",
              "互联网新闻信息", "网络文化经营", "网络视听", "广播电视"]


def _html_extract(html: str, min_len: int = 12, max_len: int = 150) -> list[dict]:
    """从HTML中提取新闻链接（处理嵌套标签）"""
    news = []
    seen = set()
    # 匹配 <a> 标签，允许内部有嵌套元素
    pattern = r'<a[^>]*href="(https?://[^"]*)"[^>]*>(.*?)</a>'
    matches = re.findall(pattern, html, re.DOTALL)
    for url, raw_text in matches:
        title = re.sub(r'<[^>]+>', '', raw_text).strip()
        if len(title) < min_len or len(title) > max_len:
            continue
        if not re.search(r'[一-鿿]', title):
            continue
        if len(re.findall(r'[一-鿿]', title)) < 5:
            continue
        if any(w in title for w in SKIP_WORDS):
            continue
        h = hashlib.md5(title.encode()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        news.append({"title": title, "link": url})
    return news


# ===== 来源1: 百度新闻 =====
def _fetch_baidu() -> list[dict]:
    news = []
    try:
        resp = requests.get("https://news.baidu.com/", headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"[百度新闻] HTTP {resp.status_code}")
            return news
        for item in _html_extract(resp.text, min_len=10, max_len=120)[:10]:
            news.append({
                "title": item["title"], "link": item["link"], "summary": "",
                "published": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "source_name": "百度新闻", "source_region": "中国/综合",
            })
        print(f"[百度新闻] {len(news)}条")
    except Exception as e:
        print(f"[百度新闻] 失败: {e}")
    return news


# ===== 来源2: 新浪新闻API（5个频道） =====
def _fetch_sina() -> list[dict]:
    news = []
    # 多频道覆盖：要闻/国内/国际/科技/财经
    channels = [
        ("121", "1354"),   # 要闻
        ("153", "2511"),   # 国内
        ("153", "2510"),   # 国际
        ("153", "2514"),   # 科技
        ("153", "2509"),   # 财经
    ]
    for pageid, lid in channels:
        try:
            url = f"https://feed.mix.sina.com.cn/api/roll/get?pageid={pageid}&lid={lid}&k=&num=8&page=1"
            resp = requests.get(url, headers={**HEADERS, "Referer": "https://news.sina.com.cn/"}, timeout=10)
            data = resp.json()
            items = data.get("result", {}).get("data", [])
            for item in items:
                title = item.get("title", "").strip()
                if title and len(title) >= 10:
                    news.append({
                        "title": title, "link": item.get("url", ""),
                        "summary": item.get("intro", "")[:200],
                        "published": item.get("ctime", ""),
                        "source_name": "新浪新闻", "source_region": "中国/综合",
                    })
        except Exception as e:
            print(f"[新浪-{pageid}/{lid}] 失败: {e}")
    print(f"[新浪新闻] {len(news)}条")
    return news


# ===== 来源3: 网易新闻JSONP =====
def _fetch_163() -> list[dict]:
    news = []
    try:
        resp = requests.get(
            "https://temp.163.com/special/00804KVA/cm_yaowen.js",
            headers=HEADERS, timeout=10,
        )
        text = resp.text.strip()
        # 去掉 JSONP 包裹
        if text.startswith("data_callback("):
            text = text[len("data_callback("):]
        if text.endswith(")"):
            text = text[:-1]
        data = json.loads(text)
        seen = set()
        for item in data:
            title = item.get("title", "").strip()
            if not title or len(title) < 10:
                continue
            if not re.search(r'[一-鿿]', title):
                continue
            h = hashlib.md5(title.encode()).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            news.append({
                "title": title, "link": item.get("docurl", ""),
                "summary": item.get("digest", "")[:200],
                "published": item.get("time", ""),
                "source_name": "网易新闻", "source_region": "中国/综合",
            })
            if len(news) >= 15:
                break
        print(f"[网易新闻] {len(news)}条")
    except Exception as e:
        print(f"[网易新闻] 失败: {e}")
    return news


# ===== 来源4: 头条热榜 =====
def _fetch_toutiao() -> list[dict]:
    news = []
    try:
        resp = requests.get(
            "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc",
            headers={**HEADERS, "Referer": "https://www.toutiao.com/"},
            timeout=10,
        )
        data = resp.json()
        items = data.get("data", [])
        for item in items[:15]:
            title = item.get("Title", "").strip()
            if title and len(title) >= 8:
                news.append({
                    "title": title,
                    "link": f"https://www.toutiao.com/trending/{item.get('ClusterId', '')}",
                    "summary": item.get("Label", "")[:200],
                    "published": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "source_name": "头条热榜", "source_region": "中国/综合",
                })
        print(f"[头条热榜] {len(news)}条")
    except Exception as e:
        print(f"[头条热榜] 失败: {e}")
    return news


# ===== 来源5: 36氪RSS =====
def _fetch_36kr() -> list[dict]:
    news = []
    try:
        feed = feedparser.parse("https://36kr.com/feed")
        for entry in feed.entries[:10]:
            title = entry.get("title", "").strip()
            if not title:
                continue
            summary = _clean_html(entry.get("summary", ""))[:300]
            news.append({
                "title": title, "link": entry.get("link", ""),
                "summary": summary,
                "published": entry.get("published", entry.get("updated", "")),
                "source_name": "36氪", "source_region": "中国/科技",
            })
        print(f"[36氪] {len(news)}条")
    except Exception as e:
        print(f"[36氪] 失败: {e}")
    return news


# ===== 来源6: IT之家RSS =====
def _fetch_ithome() -> list[dict]:
    news = []
    try:
        feed = feedparser.parse("https://www.ithome.com/rss/")
        for entry in feed.entries[:10]:
            title = entry.get("title", "").strip()
            if not title:
                continue
            summary = _clean_html(entry.get("summary", ""))[:300]
            news.append({
                "title": title, "link": entry.get("link", ""),
                "summary": summary,
                "published": entry.get("published", entry.get("updated", "")),
                "source_name": "IT之家", "source_region": "中国/科技",
            })
        print(f"[IT之家] {len(news)}条")
    except Exception as e:
        print(f"[IT之家] 失败: {e}")
    return news


# ===== 来源7: 财联社API =====
def _fetch_cls() -> list[dict]:
    news = []
    try:
        resp = requests.get(
            "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8",
            headers=HEADERS, timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("roll_data", [])
            for item in items[:10]:
                title = item.get("title", "").strip()
                if title:
                    news.append({
                        "title": title,
                        "link": f"https://www.cls.cn/detail/{item.get('id', '')}",
                        "summary": item.get("brief", "")[:300],
                        "published": datetime.fromtimestamp(item.get("ctime", 0)).strftime("%Y-%m-%d %H:%M"),
                        "source_name": "财联社", "source_region": "中国/财经",
                    })
        print(f"[财联社] {len(news)}条")
    except Exception as e:
        print(f"[财联社] 失败: {e}")
    return news


# ===== 来源8: 凤凰网 =====
def _fetch_ifeng() -> list[dict]:
    news = []
    try:
        resp = requests.get("https://www.ifeng.com/", headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"[凤凰网] HTTP {resp.status_code}")
            return news
        for item in _html_extract(resp.text)[:10]:
            news.append({
                "title": item["title"], "link": item["link"], "summary": "",
                "published": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "source_name": "凤凰网", "source_region": "中国/综合",
            })
        print(f"[凤凰网] {len(news)}条")
    except Exception as e:
        print(f"[凤凰网] 失败: {e}")
    return news


# ===== 主入口 =====
def get_daily_news(sources: Optional[list[dict]] = None) -> list[dict]:
    """
    从8个国内可用源抓取今日新闻，去重后返回最多60条
    确保每个来源最多贡献10条，保证来源多样性
    """
    all_news = []
    seen = set()
    per_source_limit = 10  # 每个源最多取N条

    print("[新闻抓取] 开始从8个源抓取新闻...")

    fetchers = [
        _fetch_baidu,
        _fetch_sina,
        _fetch_163,
        _fetch_toutiao,
        _fetch_36kr,
        _fetch_ithome,
        _fetch_cls,
        _fetch_ifeng,
    ]

    for fetcher in fetchers:
        try:
            source_count = 0
            for item in fetcher():
                h = hashlib.md5(item["title"].encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    all_news.append(item)
                    source_count += 1
                    if source_count >= per_source_limit:
                        break
        except Exception as e:
            print(f"[{fetcher.__name__}] 异常: {e}")

    result = all_news[:60]
    # 按来源统计
    from collections import Counter
    src_counts = Counter(n["source_name"] for n in result)
    src_summary = " | ".join(f"{k}:{v}" for k, v in src_counts.most_common())
    print(f"[新闻抓取] 总计 {len(result)} 条（{src_summary}）")
    return result


def _clean_html(text: str) -> str:
    """简易HTML清理"""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#34;", '"')
    text = text.replace("&#39;", "'")
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
