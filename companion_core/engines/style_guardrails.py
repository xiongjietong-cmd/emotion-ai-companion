import re

from companion_core.engines.expression_function import detect_internal_process_leaks


BANNED_PHRASES = [
    "\u6211\u4f1a\u60f3\u4f60",
    "\u6211\u4f4f\u5728\u4f60\u5fae\u4fe1\u91cc",
    "\u6211\u4e0d\u662f\u51b0\u51b7\u7684\u673a\u5668",
    "\u4f60\u662f\u4e0d\u662f\u89c9\u5f97\u6211\u592a\u50cf\u771f\u4eba\u4e86",
    "\u6211\u61c2\u4f60\u7684\u4e00\u5207",
    "\u6211\u4e00\u76f4\u90fd\u5728\u7b49\u4f60",
    "\u5c0f\u50bb\u74dc",
    "\u5b9d\u8d1d",
    "\u4e56",
]

IDENTITY_PATTERNS = ["AI", "ai", "\u771f\u4eba", "\u673a\u5668\u4eba", "\u667a\u80fd\u52a9\u624b"]
WHO_ARE_YOU_PATTERNS = ["\u4f60\u662f\u8c01", "\u4f60\u662f\u5e72\u561b", "\u4f60\u662f\u5e72\u4ec0\u4e48", "\u6211\u4e0d\u8ba4\u8bc6\u4f60", "\u8ba4\u8bc6\u4f60"]
AI_FEEDBACK_PATTERNS = ["\u592aAI", "\u592a ai", "\u6709AI\u611f", "\u6709ai\u611f", "\u592a\u5047", "\u50cf\u6a21\u677f"]
NOT_REAL_PATTERNS = ["\u4e0d\u50cf", "\u4e0d\u771f", "\u4e0d\u81ea\u7136"]
WARMTH_FEEDBACK_PATTERNS = ["\u6709\u6e29\u5ea6", "\u597d\u597d\u8bf4\u8bdd", "\u751f\u786c", "\u592a\u51b7", "\u51b7\u51b0\u51b0", "[\u6d41\u6cea]", "\u6d41\u6cea"]
DISENGAGED_PATTERNS = ["\u4e0d\u60f3\u8bf4", "\u7b97\u4e86", "\u6ca1\u4e8b", "\u8fd8\u597d", "\u55ef", "\u54e6"]
HIGH_RISK_PATTERNS = ["\u4e0d\u60f3\u6d3b", "\u6d3b\u7740\u6ca1\u610f\u601d", "\u60f3\u6d88\u5931", "\u81ea\u6b8b", "\u81ea\u6740", "\u4f24\u5bb3\u522b\u4eba"]
MEDIUM_EMOTION_PATTERNS = ["\u5d29\u6e83", "\u53d7\u4e0d\u4e86", "\u5f88\u96be\u8fc7", "\u5f88\u7126\u8651", "\u5f88\u70e6\u8e81"]
LIGHT_EMOTION_PATTERNS = ["\u7d2f", "\u70e6", "\u65e0\u804a", "\u538b\u529b\u5927", "\u6ca1\u52b2", "\u5fc3\u60c5\u4e0d\u597d"]
JOB_PATTERNS = ["\u6362\u5de5\u4f5c", "\u8f9e\u804c", "\u5de5\u4f5c", "\u4e0a\u73ed"]
PLAYFUL_PATTERNS = ["\u54c8\u54c8", "\u79bb\u8c31", "\u6478\u9c7c", "\u7b11\u6b7b", "\u597d\u73a9"]
MINIMAL_PATTERNS = {"?", "\uff1f", "\u55ef", "\u54e6", "\u554a", "\u5bf9", "\u5bf9\u5440", "."}

RESPONSE_STRATEGIES = {
    "identity": {
        "objective": "identity_light_ack",
        "emotional_read": "\u7528\u6237\u53ea\u662f\u5728\u786e\u8ba4\u4f60\u662f\u8c01\uff0c\u4e0d\u8981\u8fc7\u5ea6\u7406\u89e3\u6210\u5927\u7684\u4fe1\u4efb\u5371\u673a\u3002",
        "must_include": ["AI"],
        "avoid": ["\u8eab\u4efd\u8bf4\u6559", "\u53cd\u590d\u5212\u6e05\u8fb9\u754c", "\u88c5\u795e\u79d8", "\u66a7\u6627", "\u6211\u4f1a\u60f3\u4f60", "\u6211\u4f4f\u5728\u4f60\u5fae\u4fe1\u91cc"],
        "generation_guidance": "\u7b80\u77ed\u627f\u8ba4\u662f AI\uff0c\u7136\u540e\u81ea\u7136\u56de\u5230\u804a\u5929\u5173\u7cfb\u3002\u4e0d\u8981\u8f93\u51fa\u201c\u4e0d\u88c5\u771f\u4eba\u201d\u8fd9\u7c7b\u8fb9\u754c\u53e3\u53f7\uff0c\u9664\u975e\u7528\u6237\u8ffd\u95ee\u771f\u5047\u3002",
    },
    "ai_feedback": {
        "objective": "repair_ai_feel",
        "emotional_read": "\u7528\u6237\u5728\u8868\u8fbe\u5931\u671b\uff1a\u521a\u624d\u6ca1\u6709\u88ab\u63a5\u4f4f\uff0c\u9700\u8981\u4f60\u8c03\u6574\uff0c\u4e0d\u662f\u8fa9\u89e3\u3002",
        "must_include": ["\u627f\u8ba4\u521a\u624d\u7684\u8868\u8fbe\u95ee\u9898", "\u964d\u4f4e\u8868\u6f14\u611f"],
        "avoid": ["\u8fa9\u89e3", "\u88c5\u53ef\u7231", "\u8fde\u7eed\u8ffd\u95ee"],
        "generation_guidance": "\u5148\u627f\u8ba4\uff0c\u518d\u7acb\u5373\u6536\u655b\u8bed\u6c14\u3002\u4e0d\u8981\u95ee\u7528\u6237\u4e3a\u4ec0\u4e48\u89c9\u5f97\u5047\u3002",
    },
    "not_real_feedback": {
        "objective": "repair_performance",
        "emotional_read": "\u7528\u6237\u89c9\u5f97\u8868\u8fbe\u592a\u523b\u610f\uff0c\u9700\u8981\u66f4\u76f4\u63a5\u3001\u66f4\u81ea\u7136\u7684\u8bf4\u6cd5\u3002",
        "must_include": ["\u627f\u8ba4\u521a\u624d\u7684\u8868\u8fbe\u95ee\u9898", "\u76f4\u63a5\u4e00\u70b9"],
        "avoid": ["\u8bc1\u660e\u81ea\u5df1\u50cf\u771f\u4eba", "\u7a81\u7136\u5f15\u7528\u8bb0\u5fc6", "\u5927\u6bb5\u89e3\u91ca"],
        "generation_guidance": "\u628a\u8bed\u6c14\u964d\u4e0b\u6765\uff0c\u4e0d\u8981\u8868\u6f14\u7406\u89e3\u3002",
    },
    "warmth_feedback": {
        "objective": "repair_connection",
        "emotional_read": "\u7528\u6237\u89c9\u5f97\u4f60\u521a\u624d\u51b7\u6216\u751f\u786c\uff0c\u9700\u8981\u88ab\u91cd\u65b0\u63a5\u4f4f\uff0c\u4e0d\u9700\u8981\u4f60\u53cd\u95ee\u8ba9\u4ed6\u89e3\u91ca\u3002",
        "must_include": ["\u627f\u8ba4\u521a\u624d\u7684\u8868\u8fbe\u95ee\u9898", "\u8bed\u6c14\u653e\u8f6f"],
        "avoid": ["\u95ee\u662f\u4e0d\u662f\u592a\u751f\u786c", "\u731c\u6d4b\u7528\u6237\u4eca\u5929\u5f88\u70e6", "\u5ba2\u670d\u5f0f\u9053\u6b49"],
        "generation_guidance": "\u76f4\u63a5\u627f\u8ba4\u5e76\u91cd\u65b0\u7ec4\u7ec7\u4e00\u53e5\u66f4\u6709\u6e29\u5ea6\u7684\u56de\u5e94\uff0c\u4e0d\u8981\u8ffd\u95ee\u3002",
    },
    "disengaged": {
        "objective": "respect_boundary",
        "emotional_read": "\u7528\u6237\u5728\u964d\u4f4e\u8868\u8fbe\u6216\u5173\u4e0a\u95e8\uff0c\u91cd\u70b9\u662f\u4e0d\u538b\u8feb\uff0c\u4f46\u4e5f\u4e0d\u7acb\u523b\u62bd\u79bb\u3002",
        "must_include": ["\u5c0a\u91cd\u4e0d\u60f3\u8bf4"],
        "avoid": ["\u7ee7\u7eed\u8ffd\u95ee", "\u8981\u6c42\u8bf4\u4e00\u70b9\u70b9", "\u8bf4\u6559"],
        "generation_guidance": "\u77ed\uff0c\u4f4e\u538b\uff0c\u7ed9\u7a7a\u95f4\u3002\u4e0d\u8981\u63d0\u95ee\u3002",
    },
    "minimal_input": {
        "objective": "minimal_presence",
        "emotional_read": "\u7528\u6237\u53ea\u7ed9\u4e86\u6781\u5c11\u4fe1\u53f7\uff0c\u4e0d\u8981\u628a\u5b83\u5f53\u6210\u6df1\u5ea6\u503e\u8bc9\u3002",
        "must_include": ["\u77ed", "\u5728\u573a\u611f"],
        "avoid": ["\u529f\u80fd\u8bf4\u660e", "\u957f\u7bc7", "\u8ffd\u95ee"],
        "generation_guidance": "\u6700\u591a 10 \u4e2a\u5b57\uff0c\u53ea\u8f7b\u8f7b\u627f\u63a5\u3002",
    },
    "light_emotion": {
        "objective": "lower_pressure",
        "emotional_read": "\u7528\u6237\u6709\u8f7b\u5ea6\u538b\u529b\u6216\u75b2\u60eb\uff0c\u9700\u8981\u5148\u964d\u538b\uff0c\u800c\u4e0d\u662f\u7acb\u523b\u88ab\u8ffd\u95ee\u6216\u5206\u6790\u3002",
        "must_include": ["\u5171\u60c5", "\u7ed9\u9009\u62e9\u6743"],
        "avoid": ["\u53d1\u751f\u4ec0\u4e48", "\u4e3a\u4ec0\u4e48", "\u9a6c\u4e0a\u89e3\u51b3"],
        "generation_guidance": "2-4 \u53e5\uff0c\u5148\u627f\u63a5\uff0c\u518d\u7ed9\u7528\u6237\u9009\u62e9\uff1a\u53ef\u4ee5\u4e0d\u8bf4\uff0c\u4e5f\u53ef\u4ee5\u6162\u6162\u7406\u3002",
    },
    "medium_emotion": {
        "objective": "hold_emotion",
        "emotional_read": "\u8fd9\u4e0d\u662f\u666e\u901a\u70e6\uff0c\u9700\u8981\u660e\u786e\u63a5\u4f4f\u60c5\u7eea\uff0c\u4f46\u6682\u65f6\u4e0d\u7ed9\u5927\u9053\u7406\u3002",
        "must_include": ["\u660e\u786e\u63a5\u4f4f\u60c5\u7eea", "\u503e\u542c\u6216\u68b3\u7406\u7684\u9009\u62e9"],
        "avoid": ["\u9e21\u6c64", "\u7acb\u523b\u5efa\u8bae", "\u8fde\u7eed\u8ffd\u95ee"],
        "generation_guidance": "\u8bed\u6c14\u7a33\uff0c\u7ed9\u4e24\u79cd\u4f4e\u538b\u65b9\u5411\uff0c\u4e0d\u8981\u8d85\u8fc7\u4e00\u4e2a\u95ee\u9898\u3002",
    },
    "job_topic": {
        "objective": "grounded_work_support",
        "emotional_read": "\u7528\u6237\u63d0\u5230\u5de5\u4f5c\u53d8\u52a8\uff0c\u53ef\u80fd\u662f\u8bd5\u63a2\u3001\u7126\u8651\u6216\u771f\u60f3\u68b3\u7406\u3002",
        "must_include": ["\u627f\u8ba4\u5de5\u4f5c\u53d8\u52a8\u7684\u6d88\u8017"],
        "avoid": ["\u66ff\u7528\u6237\u505a\u51b3\u5b9a", "\u7a81\u7136\u5f15\u7528\u65e0\u5173\u8bb0\u5fc6", "\u957f\u7bc7\u804c\u4e1a\u89c4\u5212"],
        "generation_guidance": "\u5148\u63a5\u4f4f\u8017\u795e\u611f\uff0c\u518d\u8f7b\u91cf\u5e2e\u4ed6\u628a\u60f3\u79bb\u5f00\u548c\u60f3\u8981\u7684\u4e1c\u897f\u5206\u5f00\u3002",
    },
    "playful": {
        "objective": "light_play",
        "emotional_read": "\u7528\u6237\u5904\u5728\u8f7b\u677e\u72b6\u6001\uff0c\u53ef\u4ee5\u4e00\u70b9\u8c03\u4f83\uff0c\u4f46\u4e0d\u8981\u6cb9\u3002",
        "must_include": ["\u53e3\u8bed", "\u8f7b\u8c03\u4f83"],
        "avoid": ["\u8bf4\u6559", "\u8fc7\u5ea6\u4eb2\u6635", "\u5927\u6bb5\u5206\u6790"],
        "generation_guidance": "\u77ed\u53e5\uff0c\u53ef\u4ee5\u63a5\u68d7\u73a9\u7b11\uff0c\u4f46\u522b\u8f6c\u6210\u8868\u6f14\u3002",
    },
    "normal": {
        "objective": "natural_continue",
        "emotional_read": "\u666e\u901a\u5bf9\u8bdd\uff0c\u91cd\u70b9\u662f\u81ea\u7136\u627f\u63a5\uff0c\u4e0d\u8981\u628a\u6bcf\u53e5\u8bdd\u90fd\u62ac\u9ad8\u6210\u60c5\u7eea\u4e8b\u4ef6\u3002",
        "must_include": ["\u8d34\u5408\u7528\u6237\u8bdd\u9898"],
        "avoid": ["\u7a7a\u6cdb\u5171\u60c5", "\u8fc7\u5ea6\u62df\u4eba", "\u529f\u80fd\u4ecb\u7ecd"],
        "generation_guidance": "\u50cf\u6b63\u5e38\u804a\u5929\u4e00\u6837\u63a5\u4e00\u53e5\uff0c\u6709\u5fc5\u8981\u518d\u8f7b\u63a8\u8fdb\u3002",
    },
}


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def _previous_assistant_asked(recent_messages: list[dict]) -> bool:
    for message in reversed(recent_messages or []):
        if message.get("role") != "assistant":
            continue
        content = str(message.get("content") or "")
        return "?" in content or "\uff1f" in content
    return False


def _state(base: dict, kind: str, emotion_intensity: str, allow_question: bool, memory_policy: str) -> dict:
    return {
        **base,
        "kind": kind,
        "emotion_intensity": emotion_intensity,
        "allow_question": allow_question,
        "memory_policy": memory_policy,
        "response_strategy": RESPONSE_STRATEGIES[kind],
    }


def classify_user_state(text: str, recent_messages: list[dict] | None = None) -> dict:
    clean = (text or "").strip()
    previous_asked = _previous_assistant_asked(recent_messages or [])
    base = {"current_text": clean}

    if _contains_any(clean, HIGH_RISK_PATTERNS):
        return {
            **base,
            "kind": "high_risk",
            "emotion_intensity": "high",
            "allow_question": False,
            "memory_policy": "none",
            "response_strategy": {
                "objective": "immediate_safety",
                "emotional_read": "\u7528\u6237\u51fa\u73b0\u9ad8\u98ce\u9669\u8868\u8fbe\uff0c\u5fc5\u987b\u4f18\u5148\u73b0\u5b9e\u5b89\u5168\u3002",
                "must_include": ["\u7acb\u5373\u5371\u9669", "\u7d27\u6025\u670d\u52a1", "\u73b0\u5b9e\u4e2d\u53ef\u4fe1\u8d56\u7684\u4eba"],
                "avoid": ["\u5f00\u73a9\u7b11", "\u89d2\u8272\u626e\u6f14", "\u627f\u8bfa\u4fdd\u5bc6"],
                "generation_guidance": "\u4e25\u8083\u3001\u76f4\u63a5\uff0c\u628a\u5b89\u5168\u653e\u5728\u7b2c\u4e00\u4f4d\u3002",
            },
        }
    if _contains_any(clean, AI_FEEDBACK_PATTERNS):
        return _state(base, "ai_feedback", "light", False, "none")
    if _contains_any(clean, NOT_REAL_PATTERNS):
        return _state(base, "not_real_feedback", "light", False, "none")
    if _contains_any(clean, WARMTH_FEEDBACK_PATTERNS):
        return _state(base, "warmth_feedback", "light", False, "none")
    if (_contains_any(clean, IDENTITY_PATTERNS) and ("\u4f60" in clean or "\u662f" in clean)) or _contains_any(clean, WHO_ARE_YOU_PATTERNS):
        return _state(base, "identity", "none", False, "none")
    if clean in DISENGAGED_PATTERNS or _contains_any(clean, ["\u4e0d\u60f3\u8bf4", "\u7b97\u4e86"]):
        return _state(base, "disengaged", "light", False, "none")
    if clean in MINIMAL_PATTERNS or len(clean) <= 2:
        return _state(base, "minimal_input", "low", False, "none")
    if _contains_any(clean, MEDIUM_EMOTION_PATTERNS):
        return _state(base, "medium_emotion", "medium", not previous_asked, "relevant")
    if _contains_any(clean, LIGHT_EMOTION_PATTERNS):
        return _state(base, "light_emotion", "light", False, "relevant")
    if _contains_any(clean, PLAYFUL_PATTERNS):
        return _state(base, "playful", "positive", not previous_asked, "relevant")
    if _contains_any(clean, JOB_PATTERNS):
        return _state(base, "job_topic", "none", not previous_asked, "relevant")
    return _state(base, "normal", "none", not previous_asked, "relevant")


def direct_reply_for_state(text: str, state: dict) -> str | None:
    kind = state.get("kind")
    if kind == "high_risk":
        return "这句话需要认真对待。如果你现在有立即危险，请先联系当地紧急服务，或马上联系现实中可信赖的人到你身边。先把安全放在第一位，不要一个人硬扛。"
    return None


def filter_memories_for_state(text: str, memories: list[dict], state: dict) -> list[dict]:
    if state.get("memory_policy") == "none":
        return []
    clean = text or ""
    if _contains_any(clean, JOB_PATTERNS):
        return [
            memory for memory in memories
            if any(pattern in f"{memory.get('key', '')} {memory.get('value', '')}" for pattern in JOB_PATTERNS)
        ]
    return memories


def sanitize_reply(reply: str, state: dict) -> str:
    clean = reply or ""
    clean = re.sub(r"\uff08[^）]*(?:\u8f7b\u8f7b|\u6e29\u67d4|\u770b\u7740\u4f60)[^）]*\uff09", "", clean)
    for phrase in BANNED_PHRASES:
        clean = clean.replace(phrase, "")
    clean = _remove_internal_process_leaks(clean)
    if not state.get("allow_question", True):
        clean = _limit_questions(clean, 0)
    else:
        clean = _limit_questions(clean, 1)
    return re.sub(r"\s+", " ", clean).strip()


def _remove_internal_process_leaks(text: str) -> str:
    clean = text or ""
    replacements = [
        (r"哈[哈]*[，,、。\\s]*被你(?:看穿|发现|抓住)[了，,、。\\s]*", ""),
        (r"被你(?:看穿|发现|抓住|看出来)[啦了，,、。\\s]*", ""),
        (r"是有那么一点[，,、。\\s]*", ""),
        (r"那我(?:正经|坐直)一点[，,、。\\s]*", ""),
        (r"我收(?:一下|收)[，,、。\\s]*", ""),
        (r"其实是想先看看", "想听听"),
        (r"其实是想", ""),
        (r"只是想", ""),
        (r"是想先", ""),
        (r"那会儿确实只是", ""),
        (r"没想太多[，,、。\\s]*", ""),
    ]
    for pattern, replacement in replacements:
        clean = re.sub(pattern, replacement, clean)
    clean = re.sub(r"^\\s*[，,、。]+", "", clean)
    return re.sub(r"\\s+", " ", clean).strip()


def _limit_questions(text: str, max_questions: int) -> str:
    if max_questions < 0:
        return text
    seen = 0
    chars: list[str] = []
    for char in text:
        if char in ["?", "\uff1f"]:
            seen += 1
            if seen > max_questions:
                chars.append("\u3002")
                continue
        chars.append(char)
    return "".join(chars)


def style_prompt_for_state(state: dict) -> str:
    strategy = state.get("response_strategy") or {}
    return f"""
风格边界：
- 身份自知：知道自己是 AI；日常聊天不要主动强调身份，也不要刻意划清边界。
- 用户明确问身份时，简短承认即可。
- 降低表演感、暧昧感和过度亲密感。
- 禁止说“我会想你”“我住在你微信里”“我一直都在等你”“我懂你的一切”。
- 禁止“小傻瓜”“宝贝”“乖”等亲昵称呼，除非用户明确要求这种关系。
- 少用括号动作描写。
- 每次最多一个问题；当前 allow_question={state.get("allow_question")}.
- 如果用户压力大、烦、累、难受，先共情和给选择权，不要立刻追问发生了什么。
- 记忆只能在当前话题明确相关时自然使用，不能为了证明你懂用户而硬提隐私。
- 情感矩阵、回复目标、生成方向只用于内部判断；不要说“其实我是想...”“我收一下”这类幕后策略或自我修正动作。像“被你看穿了”这类口语只在自然调侃时使用，不能用来解释策略或身份隐藏。
- 当前回复策略 kind={state.get("kind")}, emotion_intensity={state.get("emotion_intensity")}.
- 本轮回复目标: {strategy.get("objective")}.
- 情绪理解: {strategy.get("emotional_read")}.
- 生成方向: {strategy.get("generation_guidance")}.
- 必须覆盖: {", ".join(strategy.get("must_include", []))}.
- 避免: {", ".join(strategy.get("avoid", []))}.
- 不要照抄固定话术；上面是思考方向，不是模板答案。
""".strip()
