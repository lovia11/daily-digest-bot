import os
import requests
from datetime import datetime, timedelta, timezone

DEEPSEEK_API_KEY = os.getenv("sk-3ec915eda0df48b8a2306c6dabfd825b")
FEISHU_WEBHOOK_URL = os.getenv("https://open.feishu.cn/open-apis/bot/v2/hook/74cc8e2f-1cd4-44b8-8f71-ba83205faeaa")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"  # 可按你实际使用的模型名调整


def call_deepseek(prompt: str, temperature: float = 0.7) -> str:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("请先设置环境变量 DEEPSEEK_API_KEY")

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一个冷静、不煽情的每日简报助手。"
                    "只输出客观简洁的信息，不带任何负面渲染，不带无意义八卦。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": 800,
    }

    resp = requests.post(DEEPSEEK_API_URL, json=data, headers=headers, timeout=60)
    resp.raise_for_status()
    result = resp.json()
    return result["choices"][0]["message"]["content"].strip()


def generate_news_and_interest():
    """
    返回两个 markdown 字符串：
    - news_md: 今日新闻部分
    - interest_md: 今日兴趣拓展部分
    """

    # 1）生成偏科技 / AI / 长期趋势的「安全新闻简报」
    news_prompt = (
        "请以中文生成一份「今日世界简报」，仅包含：\n"
        "1）科技 / AI / 工程 / 科学进展相关的要点\n"
        "2）文化、教育、长期趋势类信息\n\n"
        "特别要求：\n"
        "- 不要包含任何血腥暴力、犯罪、灾难、八卦、情绪化社会事件、股市投资内容。\n"
        "- 条目控制在 3 条以内，每条用一行，简洁明了。\n"
        "- 不要胡编乱造具体日期、地点，如不确定请用「最近」「近几年」等模糊时间表达。\n"
        "- 使用 Markdown 列表格式输出，例如：\n"
        "- xxx\n"
        "- xxx"
    )
    news_md = call_deepseek(news_prompt, temperature=0.5)

    # 2）生成一个兴趣拓展主题
    interest_prompt = (
        "用户是一名计算机专业大三学生，对以下方向都感兴趣：\n"
        "- 体育（如 F1、电竞、篮球、足球）\n"
        "- 音乐\n"
        "- 艺术（绘画、摄影、建筑等）\n"
        "- 电子游戏\n"
        "- 科技前沿（AI、航天、工程）\n"
        "- 人文与历史\n"
        "- 生活方式（美食、旅行、文化）\n"
        "- 各种小众但有趣的冷门领域\n\n"
        "请为用户生成一个「今日兴趣拓展」主题，输出格式为：\n"
        "1）先给出一个主题名\n"
        "2）用 2~4 句介绍这个主题的有趣之处（不要太学术，轻松一点）\n"
        "3）最后用一句话告诉用户：为什么今天值得花 3 分钟了解这个东西\n"
        "要求：\n"
        "- 全程中文\n"
        "- 总长度控制在 200 字以内\n"
        "- 不要出现任何暴力、血腥、极端内容，不涉及政治争论\n"
        "- 适合在手机上快速阅读"
    )
    interest_md = call_deepseek(interest_prompt, temperature=0.9)

    return news_md, interest_md


def build_feishu_card(news_md: str, interest_md: str):
    """
    构造一个飞书「图文卡片」消息（interactive card）。
    文档风格：简单清晰，适合日常阅读。
    """
    # 默认按中国时区显示日期，你可以根据需要调整
    now_utc = datetime.now(timezone.utc)
    cn_tz = timezone(timedelta(hours=8))
    now_cn = now_utc.astimezone(cn_tz)
    date_str = now_cn.strftime("%Y-%m-%d")

    card = {
        "config": {
            "wide_screen_mode": True,
        },
        "header": {
            "template": "turquoise",
            "title": {
                "tag": "plain_text",
                "content": f"你的每日世界小报 · {date_str}",
            },
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "📌 **今日新闻简报（偏科技 & 趋势）**\n\n" + news_md,
                },
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "🎯 **今日兴趣拓展**\n\n" + interest_md,
                },
            },
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "小提示：如果哪一类主题你特别喜欢或不喜欢，可以在飞书里回复，我以后会帮你逐渐调整推荐方向。",
                    }
                ],
            },
        ],
    }

    return {
        "msg_type": "interactive",
        "card": card,
    }


def send_to_feishu(card_payload: dict):
    if not FEISHU_WEBHOOK_URL:
        raise RuntimeError("请先设置环境变量 FEISHU_WEBHOOK_URL")

    resp = requests.post(FEISHU_WEBHOOK_URL, json=card_payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main():
    news_md, interest_md = generate_news_and_interest()
    card_payload = build_feishu_card(news_md, interest_md)
    result = send_to_feishu(card_payload)
    print("发送结果：", result)


if __name__ == "__main__":
    main()
