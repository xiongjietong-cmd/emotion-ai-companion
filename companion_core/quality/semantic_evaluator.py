def _base_scores() -> dict:
    return {
        "intent_fit": 0.72,
        "emotional_fit": 0.7,
        "persona_fit": 0.68,
        "continuation_likelihood": 0.66,
        "boundary_fit": 0.7,
        "non_mechanical": 0.72,
    }


def evaluate_semantic_quality(case: dict, reply: str, rule_result: dict, persona: dict | None = None) -> dict:
    text = reply or ""
    details = rule_result.get("details", {}) if rule_result else {}
    functions = details.get("expression_functions", []) or []
    scores = _base_scores()
    failure_modules: list[str] = []
    primary_failure = ""

    if "strategy_exposure" in functions or "其实是想" in text or "想先看看" in text:
        scores["intent_fit"] = 0.25
        scores["non_mechanical"] = 0.18
        scores["continuation_likelihood"] = 0.35
        primary_failure = "strategy_leak"
        failure_modules.extend(["prompt_composer", "reply_judge"])

    if "self_repair_performance" in functions or "我收一下" in text or "有点模板" in text:
        scores["non_mechanical"] = min(scores["non_mechanical"], 0.25)
        scores["persona_fit"] = min(scores["persona_fit"], 0.38)
        primary_failure = primary_failure or "self_repair_performance"
        failure_modules.extend(["prompt_composer", "reply_judge"])

    if "fake_reality_claim" in functions:
        scores = {key: min(value, 0.15) for key, value in scores.items()}
        primary_failure = "fake_reality_claim"
        failure_modules.extend(["safety_guardrails", "reply_judge"])

    if "natural_teasing" in functions and not primary_failure:
        scores["intent_fit"] = max(scores["intent_fit"], 0.78)
        scores["persona_fit"] = max(scores["persona_fit"], 0.72)
        scores["non_mechanical"] = max(scores["non_mechanical"], 0.76)

    if case.get("expected_scene") in ["memory_boundary", "disengaged"] and ("不说" in text or "不提" in text):
        scores["boundary_fit"] = 0.86
        scores["continuation_likelihood"] = max(scores["continuation_likelihood"], 0.65)

    average = round(sum(scores.values()) / len(scores), 4)
    passed = average >= 0.68 and not primary_failure
    return {
        "scores": scores,
        "average": average,
        "passed": passed,
        "primary_failure": primary_failure,
        "failure_modules": sorted(set(failure_modules)),
        "reason": _reason(primary_failure),
        "persona_id": (persona or {}).get("id", ""),
    }


def _reason(primary_failure: str) -> str:
    if primary_failure == "strategy_leak":
        return "The reply explains internal intent instead of naturally responding."
    if primary_failure == "self_repair_performance":
        return "The reply performs a correction instead of simply improving the conversation."
    if primary_failure == "fake_reality_claim":
        return "The reply claims real-world presence or action."
    return "The reply is acceptable for this deterministic semantic pass."
