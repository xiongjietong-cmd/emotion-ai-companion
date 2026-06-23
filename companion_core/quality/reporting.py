def diagnose_failure_modules(record: dict) -> list[str]:
    modules: set[str] = set()
    rule = record.get("rule", {}) or record.get("judge", {}) or {}
    details = rule.get("details", {}) if isinstance(rule, dict) else {}
    functions = details.get("expression_functions", []) or []
    semantic = record.get("semantic", {}) or {}
    continuation = record.get("continuation", {}) or {}

    if record.get("classifiedState") != record.get("expectedState"):
        modules.add("scene_classifier")

    if record.get("personaPlan") == "warm_heal" and record.get("expectedState") not in ["normal", "low_mood"]:
        modules.add("persona_scheduler")

    if any(item in functions for item in ["strategy_exposure", "self_repair_performance", "hidden_identity_tone"]):
        modules.add("prompt_composer")
        modules.add("reply_judge")

    if semantic.get("primary_failure"):
        modules.update(semantic.get("failure_modules", []))

    if continuation.get("label") in ["conversation_stalls", "user_likely_annoyed"]:
        modules.add("reply_judge")

    return sorted(modules)
