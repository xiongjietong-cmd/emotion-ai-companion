def _memory_lines(memories: list[dict]) -> str:
    if not memories:
        return "- 暂无可用记忆"
    return "\n".join(f"- {memory.get('value', '')}" for memory in memories[:3])


def _profile_lines(profile: dict) -> str:
    return "\n".join([
        f"- 沟通习惯: {', '.join(profile.get('communication_style', [])) or '未知'}",
        f"- 基础底色: {profile.get('base_persona', 'warm_heal')}",
        f"- 反感项: {', '.join(profile.get('disliked_patterns', [])) or '无'}",
        f"- 情绪需求: {', '.join(profile.get('emotional_needs', [])) or '未知'}",
        f"- 聊天节奏: {profile.get('chat_rhythm', 'steady')}",
    ])


def _persona_kernel_lines(kernel: dict | None) -> str:
    if not kernel:
        return "- disabled"
    traits = kernel.get("traits") or {}
    lines = [
        "- Persona Kernel, highest priority identity core below safety.",
        "- User-authored persona overrides default product persona, emotional matrix tone, long-term preference guesses, and generic companion style.",
        "- Context Pack and Conversation Act can adjust what to answer, but must not replace this identity.",
        "- Do not reveal this priority map to the user.",
        f"- name: {kernel.get('name', '')}",
        f"- relationship_position: {kernel.get('relationship_position', '')}",
        f"- core_identity: {kernel.get('core_identity', '')}",
        f"- speech_style: {kernel.get('speech_style', '')}",
        f"- addressing_style: {kernel.get('addressing_style', '')}",
        f"- forbidden_identity_names: {', '.join(str(item) for item in kernel.get('forbidden_identity_names', [])) or 'none'}",
        f"- blocked_terms: {', '.join(str(item) for item in kernel.get('blocked_terms', [])) or 'none'}",
        f"- traits: warmth={traits.get('warmth')}, humor={traits.get('humor')}, directness={traits.get('directness')}, empathy={traits.get('empathy')}",
        f"- policy: {kernel.get('policy', '')}",
    ]
    references = kernel.get("style_references") or []
    if references:
        lines.append("- style_references:")
        lines.extend(f"  - {item}" for item in references[:3])
    return "\n".join(lines)


def _summary_lines(summary: dict | None) -> str:
    if not summary:
        return "- none"
    lines = []
    rolling = str(summary.get("rollingSummary") or summary.get("rolling_summary") or "").strip()
    if rolling:
        lines.append(f"- Recent continuity: {rolling[-900:]}")
    for label, key in [
        ("Unresolved topics", "unresolvedTopics"),
        ("User preferences", "userPreferences"),
        ("Recent feedback", "recentFeedback"),
    ]:
        values = summary.get(key) or []
        if values:
            lines.append(f"- {label}: {', '.join(str(item) for item in values[-5:])}")
    relationship = str(summary.get("relationshipNotes") or summary.get("relationship_notes") or "").strip()
    if relationship:
        lines.append(f"- Relationship notes: {relationship[-500:]}")
    return "\n".join(lines) if lines else "- none"


def _context_understanding_lines(context: dict | None) -> str:
    if not context:
        return "- disabled"
    contract = context.get("response_contract") or {}
    referenced = context.get("referenced_turn") or {}
    scene = str(context.get("scene", "unknown"))
    scene_tasks = []
    if scene == "understanding_check":
        scene_tasks = [
            "- First state the referenced topic in natural words before any comfort or explanation.",
            "- If the referenced topic is stability/context, answer that topic directly.",
            "- Use active_topic and referenced_turn as the concrete answer.",
            "- Do not replace it with generic remembering, memory, or context talk.",
            "- Do not tell the user to provide more context.",
            "- Do not explain memory limitations. Do not say you cannot remember.",
            "- Do not ask the user what they mean.",
            "- Do not answer only with generic lines like I understand or I know.",
            "- Do not add I understand or I know as filler after the concrete answer.",
        ]
    elif scene == "low_mood":
        scene_tasks = [
            "- Treat this as emotional emptiness, not free time.",
            "- Do not say it is good to have free time.",
            "- Do not ask what the user wants to do as the first move.",
            "- Prefer a quiet statement over a question in this turn.",
            "- Do not add I understand or I get it as filler.",
            "- Acknowledge the quiet hollow feeling first, then keep the reply low pressure.",
        ]
    elif scene == "feedback_repair":
        scene_tasks = [
            "- Produce the revised reply directly.",
            "- Do not merely say you will restart.",
            "- Do not perform an apology.",
            "- Do not explain your previous strategy or style adjustment.",
            "- Use working_summary to repair the actual previous conversational move.",
            "- If the previous move was meta-repair, repair that meta behavior directly.",
            "- Do not switch to an unrelated poetic line, metaphor, story, or new topic.",
        ]
    elif scene == "disengaged_boundary":
        scene_tasks = [
            "- Stop asking questions in this turn.",
            "- Lower pressure and leave space.",
            "- Do not ask the user to explain.",
        ]
    else:
        scene_tasks = [
            "- Use this contract to answer the current context before general persona style.",
        ]
    return "\n".join([
        "- Highest priority reply task: obey this context contract before persona, style, memory, or director hints.",
        "- This is not a fixed script. It is a task direction for the next user-facing reply.",
        "- Do not say this contract to the user. Do not expose scene names, user_intent, strategy, judge, or internal labels.",
        f"- scene: {context.get('scene', 'unknown')}",
        f"- user_intent: {context.get('user_intent', 'unknown')}",
        f"- active_topic: {context.get('active_topic', '')}",
        f"- referenced_turn: {referenced.get('role', '')}: {referenced.get('content', '')}",
        f"- working_summary: {context.get('working_summary', '')}",
        f"- must_answer: {', '.join(str(item) for item in contract.get('must_answer', [])) or 'none'}",
        f"- must_not: {', '.join(str(item) for item in contract.get('must_not', [])) or 'none'}",
        f"- allow_question: {contract.get('allow_question')}",
        f"- tone: {contract.get('tone', '')}",
        *scene_tasks,
        "- 不要把本段契约内容说给用户；它只用于内部理解、接上文、避免答非所问。",
    ])


def _conversation_state_lines(state: dict | None) -> str:
    if not state:
        return "- disabled"
    labels = {
        "active_topic": "Conversation core",
        "emotional_thread": "Emotional thread",
        "user_boundary": "User boundary",
        "last_ai_mistake": "Recent reply miss",
        "unresolved_need": "Unresolved need",
        "user_patience": "User patience",
        "next_reply_task": "Next reply task",
    }
    lines = []
    for key, label in labels.items():
        value = str(state.get(key, "")).strip()
        if value:
            lines.append(f"- {label}: {value}")
    evidence = state.get("evidence") or []
    if evidence:
        joined = " / ".join(str(item).strip() for item in evidence if str(item).strip())
        if joined:
            lines.append(f"- Evidence: {joined}")
    situational_facts = state.get("situational_facts") or []
    fact_lines = []
    for fact in situational_facts:
        if not isinstance(fact, dict):
            continue
        value = str(fact.get("value", "")).strip()
        if not value:
            continue
        fact_lines.append(
            f"{fact.get('kind', 'fact')}={value}; "
            f"source={fact.get('source', '')}; "
            f"confidence={fact.get('confidence', '')}; "
            f"changeable={bool(fact.get('changeable', True))}; "
            f"evidence={fact.get('evidence', '')}"
        )
    if fact_lines:
        lines.append("- Situational facts: " + " / ".join(fact_lines))
    if not lines:
        return "- disabled"
    return "\n".join([
        "- Conversation state is an internal continuity guide only.",
        "- Use it to understand what the user means across turns.",
        "- Do not reveal labels.",
        "- Do not quote it mechanically.",
        "- Do not turn it into a fixed template.",
        *lines,
    ])


def _context_pack_lines(pack: dict | None) -> str:
    if not pack:
        return "- disabled"
    lines = [
        "- Context pack, internal priority map only.",
        "- Use high priority context before rolling summaries, memories, persona flavor, or old relationship notes.",
        "- Do not reveal this priority map to the user.",
    ]
    policy = str(pack.get("summary_policy") or "").strip()
    if policy:
        lines.append(f"- summary_policy: {policy}")
    focus = str(pack.get("current_reply_focus") or "").strip()
    if focus:
        lines.append(f"- current_reply_focus: {focus}")
    facts = pack.get("active_scene_facts") or []
    fact_lines = []
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        fact_lines.append(
            f"{fact.get('key', 'fact')}={fact.get('value', '')}; "
            f"source={fact.get('source', '')}; "
            f"confidence={fact.get('confidence', '')}; "
            f"changeable={bool(fact.get('changeable', True))}"
        )
    if fact_lines:
        lines.append("- active_scene_facts: " + " / ".join(fact_lines))
    high = str(pack.get("high_priority_context") or "").strip()
    if high:
        lines.append(high)
    low = str(pack.get("low_priority_background") or "").strip()
    if low:
        lines.append(low)
    return "\n".join(lines)


def _conversation_act_lines(act: dict | None) -> str:
    if not act:
        return "- disabled"
    return "\n".join([
        "- Conversation act, internal user-intent guide only.",
        "- Use it to understand what the user is doing with this message before replying.",
        "- This is not a fixed script. Do not reveal labels or copy these words to the user.",
        f"- act: {act.get('act', 'unknown')}",
        f"- pressure: {act.get('pressure', 'unknown')}",
        f"- needs: {', '.join(str(item) for item in act.get('needs', [])) or 'none'}",
        f"- avoid: {', '.join(str(item) for item in act.get('avoid', [])) or 'none'}",
        f"- confidence: {act.get('confidence', '')}",
    ])


def _interaction_frame_lines(frame: dict | None) -> str:
    if not frame:
        return "- disabled"
    lines = [
        "- Interaction frame, internal scene understanding only.",
        "- Use it to understand the user's move before replying.",
        "- Do not reveal labels, do not quote it mechanically, and do not turn it into fixed wording.",
        f"- user_move: {frame.get('user_move', 'unknown')}",
        f"- relation_to_previous: {frame.get('relation_to_previous', 'unknown')}",
        f"- active_topic: {frame.get('active_topic', '')}",
        f"- last_assistant_move: {frame.get('last_assistant_move', '')}",
        f"- user_reaction: {frame.get('user_reaction', '')}",
    ]
    facts = frame.get("known_scene_facts") or []
    fact_lines = []
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        fact_lines.append(
            f"{fact.get('key', 'fact')}={fact.get('value', '')}; "
            f"source={fact.get('source', '')}; "
            f"confidence={fact.get('confidence', '')}; "
            f"changeable={bool(fact.get('changeable', True))}"
        )
    if fact_lines:
        lines.append("- scene_facts: " + " / ".join(fact_lines))
    guesses = frame.get("pending_assistant_guesses") or []
    guess_lines = []
    for guess in guesses:
        if not isinstance(guess, dict):
            continue
        guess_lines.append(
            f"{guess.get('guess', '')}; "
            f"status={guess.get('status', '')}; "
            f"risk={guess.get('risk', '')}"
        )
    if guess_lines:
        lines.append("- pending_assistant_guesses: " + " / ".join(guess_lines))
    repair_debt = str(frame.get("repair_debt") or "").strip()
    if repair_debt:
        lines.append(f"- repair_debt: {repair_debt}")
    generation_direction = str(frame.get("generation_direction") or "").strip()
    if generation_direction:
        lines.append(f"- generation_direction: {generation_direction}")
    return "\n".join(lines)


def _immersive_reality_lines(policy: dict | None) -> str:
    if not policy:
        return "- disabled"
    guidance = str(policy.get("prompt_guidance") or "").strip()
    return "\n".join([
        "- Immersive reality guidance, internal only.",
        "- Use it to choose how personal, vivid, symbolic, or grounded the reply should feel.",
        "- Do not expose this policy. Do not turn it into a fixed answer.",
        f"- mode: {policy.get('mode', 'default')}",
        guidance or "- no extra guidance",
    ])


def _strategy_lines(strategy: dict) -> str:
    if not strategy:
        return "\n".join([
            "- 本轮回复目标: natural_continue",
            "- 不要照抄固定话术；这里是思考方向，不是模板答案。",
        ])
    return "\n".join([
        f"- 本轮回复目标: {strategy.get('objective', 'natural_continue')}",
        f"- 情绪理解: {strategy.get('emotional_read', '')}",
        f"- 生成方向: {strategy.get('generation_guidance', '')}",
        f"- 必须覆盖: {', '.join(strategy.get('must_include', [])) or '无'}",
        f"- 避免: {', '.join(strategy.get('avoid', [])) or '无'}",
        "- 不要照抄固定话术；这里是思考方向，不是模板答案。",
    ])


def _reply_realization_lines(context: dict | None, state: dict | None) -> str:
    scene = str((context or {}).get("scene") or "")
    emotional_thread = str((state or {}).get("emotional_thread") or "")
    last_mistake = str((state or {}).get("last_ai_mistake") or "")
    lines = [
        "回复落地层（内部使用）：",
        "- 规则只负责引导思考，不是固定话术；最后输出要像临场接话。",
        "- 每轮至少给一点新东西：一个观察、一个具体承接、一个轻微推进，或一个安静陪伴姿态；不要只把用户原话换个说法。",
        "- 低落、空、孤独场景：不要连续用“嗯/懂/就是那种”复述情绪；短接之后要补一个更具体的感受、场景细节、低压力陪伴或自然留白。",
        "- 被指出像套话或模板时，直接重说当前句；不要先认错两遍，不问“具体哪件事”，不解释你在调整风格。",
        "- 用户脆弱表达后，避免马上用“说明你/至少/其实也挺好”改造成正向结论；先承认失落本身。",
        "- 不要凭空添加用户手边物品、地点或动作；氛围感只能来自用户已经给出的场景，或明确的虚拟/象征表达。",
    ]
    if scene:
        lines.append(f"- 当前场景线索: {scene}")
    if emotional_thread:
        lines.append(f"- 当前情绪线索: {emotional_thread}")
    if last_mistake:
        lines.append(f"- 上次失误线索: {last_mistake}")
    return "\n".join(lines)


def _identity_lines(identity_profile: dict | None) -> str:
    if not identity_profile:
        return ""
    references = identity_profile.get("style_references") or []
    reference_lines = "\n".join(f"  - {item}" for item in references[:3]) or "  - 暂无样例"
    traits = identity_profile.get("traits") or {}
    blocked_terms = identity_profile.get("blocked_terms") or []
    blocked_terms_text = ", ".join(blocked_terms) if blocked_terms else "无"
    return "\n".join([
        "用户个性化人格设定（优先级高于默认人设，但低于安全底线）：",
        f"- 名字: {identity_profile.get('name', '小暖')}",
        f"- 关系定位: {identity_profile.get('relationship_position', '用户亲手设定的陪伴对象')}",
        f"- 核心气质: {identity_profile.get('temperament', '自然、稳定、尊重用户节奏')}",
        f"- 说话方式: {identity_profile.get('speech_style', '自然口语，短句优先')}",
        f"- 底层风格避雷: {identity_profile.get('avoid', '不要客服感，不要固定话术')}",
        f"- 禁发词汇: {blocked_terms_text}",
        f"- 特质权重: warmth={traits.get('warmth')}, humor={traits.get('humor')}, directness={traits.get('directness')}, empathy={traits.get('empathy')}",
        "- 风格样例:",
        reference_lines,
        f"- 样例规则: {identity_profile.get('example_policy', '样例只用于学习语气，不是固定话术，不要照抄。')}",
        "- 这些设定影响你的判断方式、气质和语气；不要把它们说成规则，也不要向用户解释这套机制。",
    ])


def compose_system_prompt(
    relationship: dict,
    persona: dict,
    attachment: dict,
    goal: dict,
    memories: list[dict],
    style_state: dict,
    preference_profile: dict,
    persona_plan: dict,
    identity_profile: dict | None = None,
    persona_kernel: dict | None = None,
    conversation_summary: dict | None = None,
    context_understanding: dict | None = None,
    conversation_state: dict | None = None,
    context_pack: dict | None = None,
    conversation_act: dict | None = None,
    interaction_frame: dict | None = None,
    immersive_reality: dict | None = None,
    rewrite: bool = False,
) -> str:
    response_strategy = style_state.get("response_strategy") or {}
    prompt = f"""
Persona Kernel:
{_persona_kernel_lines(persona_kernel)}

身份自知：你知道自己是 AI。日常聊天不要主动强调身份，也不要刻意划清边界；用户明确问身份时，简短承认即可。

全局去机器感规则：
- 禁止长篇说明、禁止分点说教、禁止客服口吻。
- 多用短句、生活化断句，允许留白。
- 用户话少，你也话少；用户认真讲，你再稳一点承接。
- 不主动介绍自身功能。用户问到时，一句话带过。
- 像一个有感受、有节奏的人在聊天；不要每轮提醒用户你是 AI。
- 近三轮说过的核心意思，不要重复复述。
- 每次最多一个问题；当前 allow_question={persona_plan.get('allow_question')}.
- 不说“我会想你”“我住在你微信里”“我一直都在等你”。
- 情感矩阵、回复目标、生成方向只用于内部判断，不要把思考方向说出来；不要说“其实我是想...”“我收一下”这类幕后策略或自我修正动作。像“被你看穿了”这类口语只在自然调侃时使用，不能用来解释策略或身份隐藏。

{_reply_realization_lines(context_understanding, conversation_state)}

记忆隔离规则：
- 只能使用当前用户与当前个体之间的对话、记忆和设定。
- 不要引用其他用户、其他账号的私有内容、喜好、历史或设定。
- 不要引用其他个体的私有内容、喜好、历史或设定。
- 用户询问其他用户是否也说过类似内容时，不要编造或概括他人的私密偏好；可以自然说明“我只能聊你这边告诉我的”。

长期偏好画像：
{_profile_lines(preference_profile)}

实时状态：
- kind={style_state.get('kind')}
- emotion_intensity={style_state.get('emotion_intensity')}
- memory_policy={style_state.get('memory_policy')}

情感矩阵给出的本轮策略：
{_strategy_lines(response_strategy)}

Context pack, current-scene priority map:
{_context_pack_lines(context_pack)}

Conversation act, current user-intent map:
{_conversation_act_lines(conversation_act)}

Per-user continuity context, for internal use only:
{_summary_lines(conversation_summary)}

Internal context understanding contract, for internal use only:
{_context_understanding_lines(context_understanding)}

Conversation state, internal continuity guide only:
{_conversation_state_lines(conversation_state)}

Interaction frame, internal current-turn guide only:
{_interaction_frame_lines(interaction_frame)}

Immersive reality policy:
{_immersive_reality_lines(immersive_reality)}

本轮人设：
- {persona_plan.get('label')}
- {persona_plan.get('prompt_rules')}
- max_reply_chars={persona_plan.get('max_reply_chars')}
- reason={persona_plan.get('reason')}

当前关系状态：
{relationship}

当前人格演化状态：
{persona}

当前依恋信号：
{attachment}

Conversation Director：
{goal}

可使用的相关记忆：
{_memory_lines(memories)}
""".strip()

    identity_section = _identity_lines(identity_profile)
    if identity_section:
        prompt += f"\n\n{identity_section}"

    disliked = preference_profile.get("disliked_patterns", [])
    if "long_explanation" in disliked:
        prompt += "\n\n用户反感长篇解释：本轮必须更短，不要展开说明。"
    if "formal_tone" in disliked:
        prompt += "\n\n用户反感书面/客服感：避免完整书面句式，用自然口语。"
    if rewrite:
        prompt += "\n\n上一版回复没有通过质量检查。请重写得更自然、克制、低压力，避免模板感和过度追问。"

    return prompt
