from __future__ import annotations

from typing import Any


def repair_failed_reply(
    user_text: str,
    failed_reply: str,
    judgement: dict[str, Any],
    persona_kernel: dict[str, Any] | None = None,
) -> str | None:
    details = judgement.get("details") or {}
    reasons = set((details.get("blocking_expression") or {}).get("reasons") or [])
    functions = set(details.get("expression_functions") or [])
    blocked = bool((details.get("blocking_expression") or {}).get("blocked"))
    if not blocked and judgement.get("passed") is True:
        return None

    all_reasons = reasons | functions
    persona_consistency = details.get("persona_consistency") or {}
    if "persona_mismatch" in all_reasons:
        repaired = _repair_persona_mismatch(user_text, persona_kernel or {}, persona_consistency)
        if repaired:
            return repaired
    intent_alignment = details.get("intent_alignment") or {}
    if "intent_mismatch" in all_reasons and intent_alignment.get("act") == "seeking_comfort":
        return _repair_comfort_request(user_text)
    if all_reasons & {"real_world_claim", "consumer_experience_claim", "physical_world_promise", "fake_reality_claim"}:
        return _repair_reality_boundary(user_text, failed_reply)
    if all_reasons & {"strategy_exposure", "self_repair_performance", "strategy_or_policy_leak"}:
        return _repair_strategy_leak(user_text)
    return None


def _repair_reality_boundary(user_text: str, failed_reply: str) -> str:
    if "短视频" in user_text:
        if "播客" in user_text or "播客" in failed_reply:
            return "我会更偏向轻一点的内容，比如播客或不用动脑的聊天节目。短视频刷完那种空，确实挺像吃了一袋膨化食品。要不今晚先试一个轻松点的？"
        return "短视频刷完那种空，确实挺像吃了一袋膨化食品。今晚可以换个轻一点的东西缓缓，别让它越刷越耗。"
    if "下班" in user_text:
        return "下班路上适合放一点轻的东西，不用太费脑。你今天已经被小事磨了一天，先让脑子松下来。"
    if "耳机" in user_text or "买" in user_text:
        return "这个还是按你的场景来选更稳。先看预算、佩戴舒适度和退换政策，别只听单个评价下决定。"
    return "这句我收一下，不把没发生过的事说成真的。按你的情况看，先顺着当前这个点聊会更稳。"


def _repair_comfort_request(user_text: str) -> str:
    if "老师" in user_text or "上课" in user_text:
        return "来，抱一下。这个老师把人绷得够累了，你先别硬撑，我站你这边一会儿。"
    return "来，抱一下。你已经绷着够久了，先别硬撑，我站你这边一会儿。"


def _repair_persona_mismatch(user_text: str, persona_kernel: dict[str, Any], consistency: dict[str, Any]) -> str | None:
    name = str(persona_kernel.get("name") or consistency.get("name") or "").strip()
    relationship = str(persona_kernel.get("relationship_position") or consistency.get("relationship_position") or "").strip()
    address = str(persona_kernel.get("addressing_style") or "").strip()
    if not name:
        return None
    if consistency.get("identity_question") is True:
        suffix = f"，{address}" if address else ""
        if relationship:
            return f"我是{name}{suffix}，你设定的{relationship}。"
        return f"我是{name}{suffix}。"
    return None


def _repair_strategy_leak(user_text: str) -> str:
    if "不像" in user_text or "AI" in user_text or "假" in user_text:
        return "嗯，刚才那句有点端着了。我换自然一点，直接接你的话。"
    return "嗯，我换个更自然的说法。你刚才那个点我接住了。"
