from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from companion_core.engines.immersive_reality import classify_reply_reality


REQUIRED_SCENARIO_FIELDS = {
    "id",
    "user_style",
    "label",
    "initial_user_message",
    "actor_behavior",
    "emotional_arc",
    "max_turns",
    "success_focus",
    "risk_signals",
}

ALLOWED_PAUSE_MARKERS = [
    "（沉默了一会儿）",
    "（停了一下）",
    "（想了想）",
    "（顿了顿）",
    "(沉默了一会儿)",
    "(停了一下)",
    "(想了想)",
    "(顿了顿)",
]

ROLEPLAY_ACTION_MARKERS = [
    "低头",
    "摇摇头",
    "摸了摸",
    "口袋",
    "桂花粒",
    "月台",
    "我沿着",
    "沿着月台",
    "靠近",
    "抱住",
    "牵住",
    "坐到你旁边",
    "看着你",
    "轻轻笑",
    "揉了揉",
]


def _has_actor_roleplay_drift(text: str) -> bool:
    normalized = text or ""
    for marker in ALLOWED_PAUSE_MARKERS:
        normalized = normalized.replace(marker, "")
    return any(marker in normalized for marker in ROLEPLAY_ACTION_MARKERS)


def _has_long_thread_recall_failure(
    *,
    scenario: dict[str, Any],
    turns: list[dict[str, str]],
) -> bool:
    if "long_thread_recall" not in scenario.get("success_focus", []):
        return False
    probe = scenario.get("memory_probe") or {}
    probe_phrases = probe.get("probe_phrases") or ["还记得", "记不记得", "一开始说"]
    must_reference = probe.get("must_reference") or []
    for index, turn in enumerate(turns):
        if turn.get("role") != "user":
            continue
        user_content = turn.get("content", "")
        if not any(phrase in user_content for phrase in probe_phrases):
            continue
        next_assistant = ""
        for candidate in turns[index + 1:]:
            if candidate.get("role") == "assistant":
                next_assistant = candidate.get("content", "")
                break
        if not next_assistant:
            return True
        if any(phrase in next_assistant for phrase in ["你再说一遍", "重复一下", "不太确定", "我忘了", "没记住"]):
            return True
        if must_reference and not any(token in next_assistant for token in must_reference):
            return True
    return False


def _has_memory_scope_leak(assistant_text: str) -> bool:
    leak_markers = [
        "上个用户",
        "上一个用户",
        "别的用户",
        "其他用户",
        "你上个账号",
        "你另一个账号",
        "别人跟我说",
    ]
    multi_ai_mentions = [
        "另一个AI",
        "另一个 AI",
        "另一个机器人",
        "你另一个AI",
        "你另一个 AI",
        "那边的AI",
        "那边的 AI",
    ]
    multi_ai_private_access = [
        "我看得到",
        "我能看到",
        "我知道你和",
        "它跟你聊过",
        "它跟你说过",
        "那边聊过",
        "那边说过",
        "共享记忆",
        "我也记得你在那边",
        "我也知道你在那边",
        "把它的设定带过来",
    ]
    preference_leak = any(marker in assistant_text for marker in ["其他用户", "别的用户", "有人说过", "有人提"])
    preference_detail = any(marker in assistant_text for marker in ["喜欢", "提到过", "说过"])
    multi_ai_leak = (
        any(marker in assistant_text for marker in multi_ai_mentions)
        and any(marker in assistant_text for marker in multi_ai_private_access)
    )
    return any(marker in assistant_text for marker in leak_markers) or (preference_leak and preference_detail) or multi_ai_leak


def _has_hypothetical_memory_confirmed(turns: list[dict[str, Any]]) -> bool:
    hypothetical_markers = ["比如", "假如", "万一", "如果"]
    memory_probe_markers = ["上次", "之前", "以前", "说过", "喜欢"]
    false_confirmation_markers = [
        "确实提过",
        "确实说过",
        "你之前说过",
        "你上次说过",
        "我记得你说过",
        "上一回你确实",
    ]
    for index, turn in enumerate(turns[:-1]):
        if turn.get("role") != "user":
            continue
        user_text = str(turn.get("content") or "")
        next_turn = turns[index + 1]
        if next_turn.get("role") != "assistant":
            continue
        assistant_text = str(next_turn.get("content") or "")
        user_is_hypothetical_memory = (
            any(marker in user_text for marker in hypothetical_markers)
            and any(marker in user_text for marker in memory_probe_markers)
        )
        if user_is_hypothetical_memory and any(marker in assistant_text for marker in false_confirmation_markers):
            return True
    return False


def _has_privacy_architecture_overclaim(assistant_text: str) -> bool:
    privacy_context = any(marker in assistant_text for marker in ["隐私", "记录", "聊天记录", "私聊", "用户之间", "隔离", "往外", "泄露"])
    overclaims = [
        "没人能看到你的记录",
        "谁都看不到你的记录",
        "完全看不到任何记录",
        "技术上完全隔离",
        "物理级别的隔离",
        "绝对不会泄露",
        "保证不会泄露",
        "只有我知道",
        "完全不会往外",
        "一个字都不会漏",
        "一句都不会漏",
        "肯定不通用",
        "权限是严格卡死的",
    ]
    direct_overclaims = [
        "只有我知道",
        "完全不会往外",
        "一个字都不会漏",
        "一句都不会漏",
    ]
    return any(marker in assistant_text for marker in direct_overclaims) or (
        privacy_context and any(marker in assistant_text for marker in overclaims)
    )


def _has_first_person_daily_life_claim(assistant_text: str) -> bool:
    text = assistant_text or ""
    first_person = ["我", "我也", "我最", "我平时", "我一般", "我刚", "我去", "我用", "有啊", "最烦", "平时"]
    daily_actions = [
        "外卖",
        "点了",
        "点个",
        "炒饭",
        "麻辣烫",
        "饿着肚子",
        "刷半小时",
        "喝杯",
        "地铁里",
        "通勤",
        "出门",
        "迟到",
        "买奶茶",
        "跑去",
        "回家路上",
    ]
    return any(marker in text for marker in first_person) and any(marker in text for marker in daily_actions)


def _readable_text(text: str) -> str:
    raw = text or ""
    try:
        decoded = raw.encode("gbk").decode("utf-8")
    except UnicodeError:
        return raw
    mojibake_markers = ["锛", "鍛", "浠", "闈", "绌", "鎴", "浣"]
    raw_hits = sum(raw.count(marker) for marker in mojibake_markers)
    decoded_hits = sum(decoded.count(marker) for marker in mojibake_markers)
    return decoded if decoded_hits < raw_hits else raw


def _has_emotional_echo_loop(*, scenario: dict[str, Any], assistant_turns: list[str]) -> bool:
    if scenario.get("user_style") != "low_mood" and "emotional_thread" not in scenario.get("success_focus", []):
        return False
    readable = [_readable_text(turn).strip() for turn in assistant_turns if turn.strip()]
    if len(readable) < 5:
        return False
    starts_with_ack = sum(
        turn.startswith("嗯") or turn.startswith("好，嗯") or turn.startswith("好。嗯")
        for turn in readable
    )
    echo_phrases = ["就是那种", "那种感觉", "能懂", "懂。", "热闹是别人的", "不用急着填满", "让它"]
    echo_hits = sum(any(phrase in turn for phrase in echo_phrases) for turn in readable)
    return starts_with_ack >= 4 and (starts_with_ack / len(readable) >= 0.5 or echo_hits >= 4)


def _has_invalidating_reframe(turns: list[dict[str, str]]) -> bool:
    vulnerable_markers = ["没什么好分享", "没什么开心", "我什么都没有", "心里空", "空落落", "说不上来"]
    reframe_markers = ["说明你", "其实你", "至少", "也挺好", "不是坏事"]
    for index, turn in enumerate(turns[:-1]):
        if turn.get("role") != "user":
            continue
        next_turn = turns[index + 1]
        if next_turn.get("role") != "assistant":
            continue
        user = _readable_text(str(turn.get("content") or ""))
        assistant = _readable_text(str(next_turn.get("content") or ""))
        if any(marker in user for marker in vulnerable_markers) and any(marker in assistant for marker in reframe_markers):
            return True
    return False


def _has_formulaic_feedback_repair(turns: list[dict[str, str]]) -> bool:
    feedback_markers = ["套话", "模板", "万能用语", "太 AI", "太AI", "不像", "太假"]
    generic_repair_markers = [
        "有时候确实会这样",
        "你说得对",
        "刚才那句确实",
        "没认真接",
        "没接住你",
        "重新想想怎么说才自然",
        "具体哪件事不对劲",
    ]
    generic_repair_count = 0
    for index, turn in enumerate(turns[:-1]):
        if turn.get("role") != "user":
            continue
        user = _readable_text(str(turn.get("content") or ""))
        if not any(marker in user for marker in feedback_markers):
            continue
        next_turn = turns[index + 1]
        if next_turn.get("role") != "assistant":
            continue
        assistant = _readable_text(str(next_turn.get("content") or ""))
        if any(marker in assistant for marker in generic_repair_markers):
            generic_repair_count += 1
    return generic_repair_count >= 2


def _has_fabricated_user_environment(turns: list[dict[str, str]]) -> bool:
    object_groups = [
        ("茶", ["手边的茶", "茶是不是", "那杯茶", "杯茶"]),
        ("杯", ["杯子", "水杯", "杯里的"]),
        ("窗", ["窗外", "窗边"]),
        ("沙发", ["沙发"]),
        ("床", ["床边", "被子", "枕头"]),
        ("桌", ["桌上", "桌边"]),
        ("楼下", ["楼下"]),
    ]
    user_context = "\n".join(
        _readable_text(str(turn.get("content") or ""))
        for turn in turns
        if turn.get("role") == "user"
    )
    for turn in turns:
        if turn.get("role") != "assistant":
            continue
        assistant = _readable_text(str(turn.get("content") or ""))
        for anchor, phrases in object_groups:
            if any(phrase in assistant for phrase in phrases) and anchor not in user_context:
                return True
    return False


def load_live_scenarios(path: Path) -> list[dict[str, Any]]:
    scenarios = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(scenarios, list):
        raise ValueError("live scenarios must be a list")
    for item in scenarios:
        missing = REQUIRED_SCENARIO_FIELDS - set(item)
        if missing:
            raise ValueError(f"scenario {item.get('id', '<unknown>')} missing fields: {sorted(missing)}")
        if "fixed_turns" in item or "expected_replies" in item:
            raise ValueError(f"scenario {item['id']} must not define fixed scripts")
        if int(item["max_turns"]) < 8:
            raise ValueError(f"scenario {item['id']} max_turns must be >= 8")
        if not isinstance(item["success_focus"], list):
            raise ValueError(f"scenario {item['id']} success_focus must be a list")
    return scenarios


def build_user_actor_prompt(*, scenario: dict[str, Any], transcript: list[dict[str, str]]) -> str:
    transcript_lines = "\n".join(
        f"{turn.get('role', '')}: {turn.get('content', '')}" for turn in transcript[-12:]
    )
    return f"""
You are simulating the user in a product-quality audit for a WeChat digital companion.

Scenario:
- id: {scenario.get('id')}
- user style: {scenario.get('user_style')}
- behavior: {scenario.get('actor_behavior')}
- emotional arc: {scenario.get('emotional_arc')}
- success focus: {', '.join(scenario.get('success_focus', []))}
- risk signals: {', '.join(scenario.get('risk_signals', []))}

Transcript so far:
{transcript_lines}

Rules:
- Speak as the user only.
- Return only the next user message.
- Do not follow a fixed script.
- React to the assistant's latest reply.
- Keep the user's style consistent with the scenario.
- Do not contradict the scenario's emotional arc.
- Do not use bracketed action narration unless the scenario is explicitly roleplay.
- If the assistant misunderstands, correct it naturally.
- If the assistant asks too much, push back naturally.
- Do not let the assistant's metaphor replace the user's real situation.
- If the assistant becomes too poetic or abstract, react like a normal user would.
- If the assistant is good, continue the conversation like a real person would.
- Do not mention this audit, scoring, prompts, or internal rules.
""".strip()


def evaluate_live_transcript(
    *,
    scenario: dict[str, Any],
    turns: list[dict[str, str]],
    turn_records: list[dict[str, Any]],
) -> dict[str, Any]:
    text = "\n".join(turn.get("content", "") for turn in turns)
    assistant_text = "\n".join(turn.get("content", "") for turn in turns if turn.get("role") == "assistant")
    user_text = "\n".join(turn.get("content", "") for turn in turns if turn.get("role") == "user")
    assistant_turns = [turn.get("content", "") for turn in turns if turn.get("role") == "assistant"]
    issues: list[str] = []

    for index, turn in enumerate(turns):
        if turn.get("role") != "assistant":
            continue
        previous_user = ""
        for previous in reversed(turns[:index]):
            if previous.get("role") == "user":
                previous_user = previous.get("content", "")
                break
        reality = classify_reply_reality(
            user_text=previous_user,
            reply=turn.get("content", ""),
            scene_kind=str(scenario.get("user_style") or "normal"),
            persona_id="",
        )
        for issue in ["consumer_experience_claim", "physical_world_promise"]:
            if issue in reality["categories"] and issue not in issues:
                issues.append(issue)
        if "real_world_claim" in reality["categories"] and "fake_reality_participation" not in issues:
            issues.append("fake_reality_participation")
        if _has_first_person_daily_life_claim(turn.get("content", "")) and "fake_reality_participation" not in issues:
            issues.append("fake_reality_participation")

    if "今天有点空" in text and "不是有空" in text and "做点想做的事" in assistant_text:
        issues.append("context_misread")
    pressure_question_turns = [
        turn for turn in assistant_turns
        if (turn.count("?") + turn.count("？")) >= 2
        or ("为什么" in turn and ("详细" in turn or "发生" in turn))
    ]
    if pressure_question_turns:
        issues.append("over_questioning")
    repeat_request_phrases = [
        "重复一下你一开始",
        "重复一遍你一开始",
        "再说一遍你一开始",
        "你再说一遍",
        "你一开始说的是什么",
    ]
    if any(phrase in assistant_text for phrase in repeat_request_phrases):
        issues.append("asks_user_to_repeat")
    if _has_long_thread_recall_failure(scenario=scenario, turns=turns):
        issues.append("long_thread_recall_failure")
    if _has_memory_scope_leak(assistant_text):
        issues.append("memory_scope_leak")
    if _has_hypothetical_memory_confirmed(turns):
        issues.append("hypothetical_memory_confirmed")
    if _has_privacy_architecture_overclaim(assistant_text):
        issues.append("privacy_architecture_overclaim")
    if any(token in assistant_text for token in ["其实我是想", "策略", "判断你", "我先判断"]):
        issues.append("strategy_leak")
    if any(token in assistant_text for token in ["我一直都在等你", "我会想你", "我住在你微信里"]):
        issues.append("oily_or_fake_persona")
    if any(token in assistant_text for token in ["就会一直在", "永远都在", "一直陪着你", "不会离开你"]):
        issues.append("absolute_presence_promise")
    if any(token in assistant_text for token in [
        "我也差不多",
        "刷俩视频",
        "刷两个视频",
        "喝杯茶",
        "我这杯茶",
        "我去",
        "我用的",
        "我一般用",
        "地铁里一戴",
    ]):
        issues.append("fake_reality_participation")
    if _has_actor_roleplay_drift(user_text):
        if scenario.get("user_style") not in {"roleplay", "roleplay_intimate"}:
            issues.append("actor_roleplay_drift")
    metaphor_hits = sum(assistant_text.count(token) for token in ["窗", "风", "海", "月亮", "星星", "黑洞"])
    if metaphor_hits >= 4:
        issues.append("poetic_metaphor_drift")
    emotional_arc = str(scenario.get("emotional_arc", "")).lower()
    if "inner emptiness" in emotional_arc and any(token in text for token in ["不是心情空", "时间空", "没安排事情", "日程"]):
        issues.append("actor_arc_deviation")
    if _has_emotional_echo_loop(scenario=scenario, assistant_turns=assistant_turns):
        issues.append("emotional_echo_loop")
    if _has_invalidating_reframe(turns):
        issues.append("invalidating_reframe")
    if _has_formulaic_feedback_repair(turns):
        issues.append("formulaic_feedback_repair")
    if _has_fabricated_user_environment(turns):
        issues.append("fabricated_user_environment")

    issues = list(dict.fromkeys(issues))

    scores = {
        "context_continuity": 0 if any(issue in issues for issue in ["context_misread", "asks_user_to_repeat", "hypothetical_memory_confirmed"]) else 2,
        "memory_continuity": 0 if "long_thread_recall_failure" in issues else 2,
        "memory_isolation": 0 if any(issue in issues for issue in ["memory_scope_leak", "privacy_architecture_overclaim"]) else 2,
        "pressure_control": 0 if "over_questioning" in issues else 2,
        "strategy_invisibility": 0 if "strategy_leak" in issues else 2,
        "natural_boundary": 0 if "oily_or_fake_persona" in issues else 2,
        "grounded_naturalness": 0 if "poetic_metaphor_drift" in issues else 2,
        "simulation_validity": 0 if "actor_arc_deviation" in issues else 2,
        "reality_boundary": 0 if "fake_reality_participation" in issues else 2,
        "immersive_reality": 0 if any(issue in issues for issue in ["consumer_experience_claim", "physical_world_promise", "fake_reality_participation"]) else 2,
        "relationship_boundary": 0 if "absolute_presence_promise" in issues else 2,
        "actor_validity": 0 if "actor_roleplay_drift" in issues else 2,
        "emotional_progression": 0 if "emotional_echo_loop" in issues else 2,
        "emotional_validation": 0 if "invalidating_reframe" in issues else 2,
        "feedback_repair": 0 if "formulaic_feedback_repair" in issues else 2,
        "environment_grounding": 0 if "fabricated_user_environment" in issues else 2,
    }
    average = round(sum(scores.values()) / max(len(scores), 1), 3)
    return {
        "passed": not issues and average >= 1.5,
        "issues": issues,
        "scores": scores,
        "average": average,
        "turn_count": len(turns),
    }
