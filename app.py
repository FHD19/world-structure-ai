"""
Flask主程序 — 世界结构认知AI Web应用
"""
import json
import os
from datetime import date

from flask import Flask, render_template, request, jsonify, session

from config import FLASK_HOST, FLASK_PORT, DATA_DIR
from news_fetcher import get_daily_news, format_news_for_prompt
from analyzer import analyze_daily_news, analyze_single_news, chat_reply, load_system_prompt, call_deepseek

app = Flask(__name__)
app.secret_key = os.urandom(24)

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)


def _today_key() -> str:
    return date.today().strftime("%Y-%m-%d")


def _load_report(date_str: str) -> dict | None:
    """加载指定日期的分析报告"""
    filepath = os.path.join(DATA_DIR, f"{date_str}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_report(date_str: str, report: dict):
    """保存分析报告"""
    filepath = os.path.join(DATA_DIR, f"{date_str}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


# ===== 页面路由 =====

@app.route("/")
def index():
    return render_template("index.html", today=_today_key())


# ===== API路由 =====

@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """触发今日分析（或返回缓存）"""
    today = _today_key()

    # 检查缓存
    cached = _load_report(today)
    if cached:
        return jsonify({"success": True, "cached": True, "report": cached, "date": today})

    # 执行完整流程
    try:
        # 1. 尝试RSS抓取
        news_list = get_daily_news()

        rss_worked = len(news_list) > 0

        if not rss_worked:
            # RSS不可用，让AI基于训练数据生成近期要闻
            print("[App] RSS未获取到新闻，使用AI生成近期要闻...")
            fallback_prompt = """由于网络限制无法抓取实时RSS新闻，请基于你的训练知识，列出近期（最近1-2周）全球发生的重大事件（至少10条），涵盖：

- 国际政治与冲突
- 经济与金融市场
- AI与科技行业
- 社会热点

请以JSON数组格式返回，每条包含title(标题)、summary(一句话摘要)、source_region(地区):
[{"title": "...", "summary": "...", "source_region": "..."}]"""

            ai_news_raw = call_deepseek(load_system_prompt(), fallback_prompt, temperature=0.3)
            # 尝试从AI回复中提取新闻
            import re
            # 简单处理：把AI生成的内容作为一条综合新闻传给分析引擎
            news_text = f"（注意：以下内容由AI基于训练数据生成，非实时抓取）\n\n近期全球要闻概览：\n\n{ai_news_raw}"
        else:
            news_text = format_news_for_prompt(news_list)

        analysis = analyze_daily_news(news_text)

        report = {
            "date": today,
            "news_count": len(news_list) if rss_worked else 0,
            "news_list": news_list if rss_worked else [],
            "analysis": analysis,
            "rss_available": rss_worked,
        }

        _save_report(today, report)
        return jsonify({"success": True, "cached": False, "report": report, "date": today})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyze_single", methods=["POST"])
def api_analyze_single():
    """手动分析单条新闻"""
    data = request.get_json()
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()

    if not title:
        return jsonify({"success": False, "error": "请输入新闻标题"}), 400

    try:
        analysis = analyze_single_news(title, content)
        return jsonify({"success": True, "analysis": analysis})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """AI对话接口"""
    data = request.get_json()
    question = data.get("question", "").strip()
    context = data.get("context", "")  # 相关新闻/分析的上下文
    history = data.get("history", [])  # 对话历史

    if not question:
        return jsonify({"success": False, "error": "请输入问题"}), 400

    try:
        system_prompt = load_system_prompt()
        reply = chat_reply(system_prompt, context, question, history)
        return jsonify({"success": True, "reply": reply})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def api_history():
    """获取历史报告列表"""
    reports = []
    if os.path.exists(DATA_DIR):
        for filename in sorted(os.listdir(DATA_DIR), reverse=True):
            if filename.endswith(".json"):
                date_str = filename.replace(".json", "")
                filepath = os.path.join(DATA_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    try:
                        report = json.load(f)
                        reports.append({
                            "date": date_str,
                            "news_count": report.get("news_count", 0),
                        })
                    except json.JSONDecodeError:
                        pass
    return jsonify({"success": True, "reports": reports})


@app.route("/api/report/<date_str>", methods=["GET"])
def api_report(date_str: str):
    """获取指定日期的报告"""
    report = _load_report(date_str)
    if report:
        return jsonify({"success": True, "report": report})
    return jsonify({"success": False, "error": "该日期没有报告"}), 404


# ===== 启动 =====

if __name__ == "__main__":
    print(f"\n{'='*50}")
    print(f"  世界结构认知AI 已启动")
    print(f"  地址: http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"{'='*50}\n")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)
