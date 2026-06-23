from fastapi import FastAPI
from fastapi.responses import JSONResponse

from companion_core.engines.attachment import build_attachment_signal
from companion_core.engines.conversation_act import classify_conversation_act
from companion_core.engines.context_pack import build_context_pack
from companion_core.engines.context_understanding import understand_context
from companion_core.engines.conversation_state import update_conversation_state
from companion_core.engines.director import decide_conversation_goal
from companion_core.engines.judge import judge_reply
from companion_core.engines.immersive_reality import plan_immersive_reality
from companion_core.engines.interaction_frame import build_interaction_frame
from companion_core.engines.memory import extract_memory_candidates, select_memories
from companion_core.engines.personality import evolve_personality
from companion_core.engines.personality_compiler import compile_personality_config
from companion_core.engines.persona_kernel import build_persona_kernel
from companion_core.engines.preference_profile import build_preference_profile
from companion_core.engines.persona_scheduler import schedule_persona
from companion_core.engines.relationship import update_relationship
from companion_core.engines.reply_rhythm import decide_reply_rhythm, split_reply_parts
from companion_core.engines.safe_reply_repair import repair_failed_reply
from companion_core.engines.style_guardrails import (
    classify_user_state,
    direct_reply_for_state,
    filter_memories_for_state,
    sanitize_reply,
)
from companion_core.model_client import ModelUnavailableError, generate_reply
from companion_core.models import ReplyRequest, ReplyResponse


app = FastAPI(title="Digital Companion Core")


def _model_unavailable_response(exc: ModelUnavailableError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "ok": False,
            "code": "MODEL_UNAVAILABLE",
            "error": "model unavailable",
            "detail": str(exc),
        },
    )


def _relationship_delta(before: dict, after: dict) -> dict:
    delta = {}
    for key, value in after.items():
        try:
            after_value = float(value)
            before_value = float(before.get(key, 0))
        except (TypeError, ValueError):
            continue
        change = round(after_value - before_value, 4)
        if change != 0:
            delta[key] = change
    return delta


def _split_reply_parts(reply: str, max_parts: int = 4) -> list[str]:
    return split_reply_parts(reply, {"profile": "steady", "max_parts": max_parts})


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/v1/reply", response_model=ReplyResponse)
async def create_reply(request: ReplyRequest) -> ReplyResponse:
    before = dict(request.relationship or {})
    recent_messages = [message.model_dump() for message in request.recent_messages]
    conversation_summary = dict(request.conversation_summary or {})
    memories = [memory.model_dump() for memory in request.memories]
    features = dict(request.features or {})
    user_state = classify_user_state(request.text, recent_messages)
    preference_profile = build_preference_profile([*recent_messages, {"role": "user", "content": request.text}])

    relationship = update_relationship(before, request.text, recent_messages)
    relationship_delta = _relationship_delta(before, relationship)

    safe_memories = filter_memories_for_state(request.text, memories, user_state)
    selected_memories = select_memories(request.text, safe_memories, relationship)
    persona = evolve_personality(relationship, recent_messages)
    identity_profile = compile_personality_config(request.personality_config)
    persona_kernel = build_persona_kernel(identity_profile)
    attachment = build_attachment_signal(relationship, selected_memories, recent_messages)
    goal = decide_conversation_goal(request.text, relationship, selected_memories, persona)
    immersive_reality = plan_immersive_reality(
        user_text=request.text,
        scene_kind=str(goal.get("scene_kind") or goal.get("kind") or goal.get("primary_goal") or user_state.get("kind") or "normal"),
        persona_id=str(request.personality_config.get("personaId") or request.personality_config.get("id") or ""),
        identity_profile=identity_profile,
    )
    persona_plan = schedule_persona(preference_profile, user_state, recent_messages)
    context_understanding = None
    if features.get("context_understanding") is True:
        context_understanding = understand_context(
            request.text,
            recent_messages,
            selected_memories,
            conversation_summary,
        )
    conversation_state = dict(request.conversation_state or {})
    if features.get("conversation_state") is True:
        conversation_state = update_conversation_state(
            text=request.text,
            recent_messages=recent_messages,
            previous_state=conversation_state,
            context_understanding=context_understanding,
        )
    interaction_frame = build_interaction_frame(
        text=request.text,
        recent_messages=recent_messages,
        conversation_state=conversation_state,
        selected_memories=selected_memories,
    )
    conversation_act = classify_conversation_act(request.text, recent_messages)
    context_pack = build_context_pack(
        text=request.text,
        recent_messages=recent_messages,
        conversation_summary=conversation_summary,
        conversation_state=conversation_state,
        interaction_frame=interaction_frame,
        selected_memories=selected_memories,
    )
    direct_reply = direct_reply_for_state(request.text, user_state)
    if direct_reply:
        reply = direct_reply
    else:
        try:
            reply = await generate_reply(
                request.text,
                selected_memories,
                relationship,
                persona,
                attachment,
                goal,
                provider_config=request.provider_config,
                style_state=user_state,
                preference_profile=preference_profile,
                persona_plan=persona_plan,
                identity_profile=identity_profile,
                persona_kernel=persona_kernel,
                conversation_summary=conversation_summary,
                context_understanding=context_understanding,
                conversation_state=conversation_state,
                context_pack=context_pack,
                conversation_act=conversation_act,
                interaction_frame=interaction_frame,
                immersive_reality=immersive_reality,
            )
        except ModelUnavailableError as exc:
            return _model_unavailable_response(exc)
        reply = sanitize_reply(reply, user_state)
    judgement = judge_reply(request.text, reply, relationship, selected_memories, goal, persona_kernel=persona_kernel)

    if not direct_reply and not judgement["passed"]:
        try:
            reply = await generate_reply(
                request.text,
                selected_memories,
                relationship,
                persona,
                attachment,
                goal,
                rewrite=True,
                provider_config=request.provider_config,
                style_state=user_state,
                preference_profile=preference_profile,
                persona_plan=persona_plan,
                identity_profile=identity_profile,
                persona_kernel=persona_kernel,
                conversation_summary=conversation_summary,
                context_understanding=context_understanding,
                conversation_state=conversation_state,
                context_pack=context_pack,
                conversation_act=conversation_act,
                interaction_frame=interaction_frame,
                immersive_reality=immersive_reality,
            )
        except ModelUnavailableError as exc:
            return _model_unavailable_response(exc)
        reply = sanitize_reply(reply, user_state)
        judgement = judge_reply(request.text, reply, relationship, selected_memories, goal, persona_kernel=persona_kernel)

    if not direct_reply and not judgement["passed"]:
        repaired_reply = repair_failed_reply(request.text, reply, judgement, persona_kernel=persona_kernel)
        if repaired_reply:
            reply = sanitize_reply(repaired_reply, user_state)
            judgement = judge_reply(request.text, reply, relationship, selected_memories, goal, persona_kernel=persona_kernel)

    rhythm = decide_reply_rhythm(request.text, relationship)
    reply_parts = split_reply_parts(reply, rhythm)

    return ReplyResponse(
        reply="\n".join(reply_parts) if reply_parts else reply,
        reply_parts=reply_parts,
        relationship_delta=relationship_delta,
        memory_candidates=extract_memory_candidates(request.text),
        director_goal=goal,
        judge=judgement,
    )
