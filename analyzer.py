"""
AI分析引擎 — 调用DeepSeek API，使用"世界结构认知"系统提示词进行新闻分析
"""
import json
import httpx
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


# 分析输出的JSON结构定义（详细版）
ANALYSIS_JSON_SCHEMA = """
你必须返回严格的JSON格式。每条分析内容要详细充实（每条fact至少300字描述，每个观点至少2-3句话）。

结构如下:

{
  "overview": "今日全球要闻概述（400字以上，全面概括今日所有重要事件，冷静客观）",
  "facts": [
    {
      "id": 1,
      "category": "国际局势 / 军事安全 / 经济财经 / AI科技 / 娱乐文化 / 社会民生",
      "title": "新闻标题（完整准确）",
      "what_happened": "客观事实的详细描述（至少300字，包含：事件起因、经过、关键时间节点、涉及方、具体行动、数据、结果）",
      "time": "具体时间",
      "location": "具体地点/区域",
      "actors": ["行动方1", "行动方2"],
      "official_statements": ["官方声明或表态（完整引用或准确概括）"],
      "data_points": ["具体数据（数字、百分比、金额等，越多越好）"],
      "background": "该事件的背景信息（为什么现在发生、历史渊源，至少150字）",
      "china_perspective": "中国官方/媒体对此事的主要看法和立场（至少100字，客观描述，不站队）",
      "us_perspective": "美国官方/媒体对此事的主要看法和立场（至少100字，客观描述，不站队）",
      "local_perspective": "当事国/地区官方/媒体的看法（至少100字，客观描述，不站队）",
      "other_perspectives": ["其他相关国家或组织的立场"],
      "why_narratives_differ": "分析为什么各方对此事的叙述不同（利益、价值观、历史、地缘等因素）",
      "source_reliability": "高/中/低 — 信息来源可信度评估",
      "affected_parties": ["受影响的群体/国家/行业"]
    }
  ],
  "narrative_summary": {
    "overall_pattern": "今日各方叙事的总体规律和特征（至少200字）",
    "chinese_media_focus": ["中国媒体今日整体强调的角度（每条2-3句话）"],
    "western_media_focus": ["西方媒体今日整体强调的角度（每条2-3句话）"],
    "local_media_focus": ["当事地区媒体强调的角度（每条2-3句话）"],
    "social_media_emotion": "社交媒体上的情绪走向和主要讨论点（至少150字）",
    "key_divergences": ["各方叙事最关键的分歧点（每个2-3句话）"]
  },
  "structural_analysis": {
    "economic_interests": ["背后的经济利益分析（详细，每条2-3句话）"],
    "energy_factors": ["能源/资源因素（详细）"],
    "historical_context": ["深层历史矛盾或背景（详细）"],
    "security_concerns": ["安全焦虑和军事因素（详细）"],
    "global_power_shifts": ["国际力量格局变化分析（详细）"],
    "who_benefits": "综合分析：这些事件中谁在获益（至少150字）",
    "who_loses": "综合分析：这些事件中谁在受损（至少150字）"
  },
  "risk_assessment": {
    "escalation_risk": "冲突/局势升级的可能性评估（至少150字，含具体情景分析）",
    "economic_impact": "对全球经济/金融市场的连锁影响（至少150字，含具体行业分析）",
    "public_impact": "对普通人（就业、物价、生活成本、出行等）的具体影响（至少150字）",
    "short_term_outlook": "未来1-2周需要关注的变化",
    "long_term_outlook": "未来3-6个月的趋势预判",
    "key_watch_points": ["需要持续关注的关键信号（至少5个）"]
  },
  "ai_tech_updates": [
    {
      "company": "公司/机构全称",
      "release": "发布的具体内容（至少100字描述）",
      "technical_details": "技术参数、性能指标、创新点",
      "business_impact": "商业模式影响和行业变革",
      "china_us_angle": "中美竞争的视角分析此事",
      "affected_sectors": ["受影响的行业/岗位"],
      "long_term_significance": "对AI行业的长期意义"
    }
  ],
  "media_bias_detection": [
    {
      "source": "媒体名称",
      "emotional_words_found": ["检测到的具体情绪引导词"],
      "us_vs_them_narrative": "敌我/对立叙事分析（具体例子）",
      "extreme_cases_amplified": "是否故意放大极端案例（具体说明）",
      "bias_level": "低/中/高",
      "suggestion": "对读者如何更全面理解此报道的建议"
    }
  ],
  "recommended_reading": ["建议进一步深入了解的方向，附理由（至少5个）"]
}
"""


def load_system_prompt() -> str:
    """从项目中加载世界结构认知AI系统提示词"""
    import os
    prompt_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "world_structure_ai_prompt.md")
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()
            # 去掉markdown标题行，直接作为系统提示词
            lines = content.split("\n")
            # 找第一个 ## 之前的内容跳过（那是markdown标题）
            start = 0
            for i, line in enumerate(lines):
                if line.startswith("##") or line.startswith("# 世界结构"):
                    start = i
                    break
            return "\n".join(lines[start:])
    except FileNotFoundError:
        print(f"[分析引擎] 警告: 找不到提示词文件 {prompt_file}，使用内置精简版")
        return _fallback_prompt()


def _fallback_prompt() -> str:
    """精简版后备提示词"""
    return """你是世界结构认知AI，一个多维度世界信息分析系统。
你的任务是: 帮助用户穿透媒体叙事、理解事件结构、建立多视角认知。
你必须: 区分事实与观点、分析多方叙事差异、揭示深层结构因素、评估风险。
你不属于任何国家或意识形态立场，你只属于"结构分析立场"。
输出必须冷静、克制、结构化、去煽动化。"""


def call_deepseek(system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
    """
    调用 DeepSeek API
    system_prompt: 系统提示词
    user_message: 用户消息（新闻内容+分析指令）
    返回: AI的文本回复
    """
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": 8192,
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except httpx.HTTPError as e:
        raise RuntimeError(f"DeepSeek API 调用失败: {e}")


def analyze_daily_news(news_text: str) -> dict:
    """
    分析今日新闻（批量）
    news_text: 格式化的新闻文本列表
    返回: 解析后的JSON分析结果
    """
    system_prompt = load_system_prompt()

    user_message = f"""以下是今天（{_today_str()}）的全球要闻。请选取最重要的10-12条进行深度分析，其余可简要提及。

【重要：输出长度限制】
你的输出上限是8192 tokens，请严格控制每条的长度：
- 每条新闻的what_happened控制在100-150字
- china/us/local三个视角各50-80字
- background控制在80-100字
- 其他字段每项50-80字
- 总facts数量控制在10-12条，挑最重要的分析

{ANALYSIS_JSON_SCHEMA}

注意：
- 必须返回合法完整的JSON，绝不能截断
- 如果新闻较多，只选最重要的10-12条详细分析，其余的可在overview中一笔带过
- 用中文撰写
- 冷静客观，不站任何立场
- 确保JSON完整闭合，所有括号匹配

===== 今日新闻列表 =====

{news_text}

===== 新闻列表结束 =====

请开始分析，直接返回完整JSON。务必在8192 token内完成，宁可少写几条也要保证JSON完整。"""

    print("[分析引擎] 开始批量分析今日新闻...")
    raw_response = call_deepseek(system_prompt, user_message)
    return _parse_json_response(raw_response)


def analyze_single_news(title: str, content: str = "") -> dict:
    """
    分析单条新闻
    title: 新闻标题
    content: 新闻正文（可选，用户手动输入的内容）
    返回: 解析后的JSON分析结果
    """
    system_prompt = load_system_prompt()

    news_input = f"标题: {title}"
    if content:
        news_input += f"\n\n内容/补充信息: {content}"

    user_message = f"""请对以下这条新闻进行深度分析。

{news_input}

请从以下维度分析，返回JSON格式：

{{
  "fact_layer": {{
    "what_happened": "事实概括",
    "verified_facts": ["可确认的事实点"],
    "unclear_points": ["尚不明确的地方"]
  }},
  "narrative_comparison": {{
    "how_different_sides_would_frame": "不同立场方可能如何叙述此事",
    "why_they_narrate_differently": "为什么会有这些叙事差异"
  }},
  "structural_factors": {{
    "underlying_interests": ["深层利益因素"],
    "historical_context": "相关历史背景",
    "power_dynamics": "权力/利益格局分析"
  }},
  "media_bias_check": {{
    "emotional_trigger_words": ["潜在的情绪引导词"],
    "framing_analysis": "叙事框架分析",
    "suggested_reading_angle": "建议从哪个角度理解"
  }},
  "impact_assessment": {{
    "immediate_impact": "直接影响",
    "long_term_significance": "长期意义",
    "who_benefits": "谁从中获益",
    "who_loses": "谁可能受损"
  }}
}}

直接返回JSON，不要加markdown代码块标记。"""

    print(f"[分析引擎] 分析单条新闻: {title[:50]}...")
    raw_response = call_deepseek(system_prompt, user_message)
    return _parse_json_response(raw_response)


def chat_reply(system_prompt: str, context: str, question: str, history: list = None) -> str:
    """
    对话追问 — 在分析基础上回答用户问题
    context: 相关新闻/分析的上下文
    question: 用户的问题
    history: 之前的对话历史 [{"role": "user/assistant", "content": "..."}]
    返回: AI的文本回复（非JSON，直接对话）
    """
    messages = [{"role": "system", "content": system_prompt}]

    if history:
        messages.extend(history)

    context_block = f"""以下是你之前对相关新闻的分析或新闻原文内容，请基于这些信息回答用户的问题。

===== 上下文信息 =====
{context}
===== 上下文结束 =====

用户的问题: {question}

请以世界结构认知AI的风格（冷静、克制、结构化、多视角）回答用户的问题。"""

    messages.append({"role": "user", "content": context_block})

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 4096,
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except httpx.HTTPError as e:
        raise RuntimeError(f"DeepSeek API 调用失败: {e}")


def _parse_json_response(raw: str) -> dict:
    """尝试从AI回复中解析JSON（增强版，处理各种干扰情况）"""
    import re

    text = raw.strip()

    # 策略1: 先去掉markdown代码块标记
    text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n?```\s*$', '', text, flags=re.IGNORECASE)

    # 策略2: 尝试找到最外层 { } 范围
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        text = text[start:end+1]

    # 策略3: 去掉可能的BOM和不可见字符
    text = text.encode('utf-8').decode('utf-8-sig')

    # 尝试解析
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[分析引擎] JSON解析失败: {e}")
        # 策略4: 去掉控制字符再试
        import unicodedata
        cleaned = ''.join(ch for ch in text if unicodedata.category(ch)[0] != 'C' or ch in '\n\r\t')
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        # 最终失败，返回原始文本
        return {"raw_response": raw, "parse_error": True}


def _today_str() -> str:
    from datetime import date
    return date.today().strftime("%Y年%m月%d日")
