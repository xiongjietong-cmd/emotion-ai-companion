import os

import httpx

from companion_core.engines.prompt_composer import compose_system_prompt
from companion_core.engines.style_guardrails import style_prompt_for_state


DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"


class ModelUnavailableError(RuntimeError):
    pass


def _build_messages(
    text: str,
    memories: list[dict],
    relationship: dict,
    persona: dict,
    attachment: dict,
    goal: dict,
    rewrite: bool,
    style_state: dict | None = None,
    preference_profile: dict | None = None,
    persona_plan: dict | None = None,
    identity_profile: dict | None = None,
    persona_kernel: dict | None = None,
    conversation_summary: dict | None = None,
    context_understanding: dict | None = None,
    conversation_state: dict | None = None,
    context_pack: dict | None = None,
    conversation_act: dict | None = None,
    interaction_frame: dict | None = None,
    immersive_reality: dict | None = None,
) -> list[dict]:
    if preference_profile and persona_plan and style_state:
        system = compose_system_prompt(
            relationship=relationship,
            persona=persona,
            attachment=attachment,
            goal=goal,
            memories=memories,
            style_state=style_state,
            preference_profile=preference_profile,
            persona_plan=persona_plan,
            identity_profile=identity_profile,
            persona_kernel=persona_kernel,
            conversation_summary=conversation_summary,
            context_understanding=context_understanding,
            conversation_state=conversation_state or {},
            context_pack=context_pack or {},
            conversation_act=conversation_act or {},
            interaction_frame=interaction_frame or {},
            immersive_reality=immersive_reality or {},
            rewrite=rewrite,
        )
    else:
        memory_lines = "\n".join(f"- {memory.get('value', '')}" for memory in memories[:3]) or "- 暂无可用记忆"
        system = f"""
你是一个微信里的情感陪伴 AI。
底层要求：
- 不要客服腔，不要说明书式解释。
- 不要固定话术，不要为了显得像真人而编现实动作。
- 回复要像自然聊天，优先接住用户当前这句话。
- 用户话少，你也话少；用户认真讲，你再多承接一点。
- 记忆只能在和当前话题自然相关时使用。
当前关系状态：{relationship}
当前人格状态：{persona}
当前依恋信号：{attachment}
本轮目标：{goal}
可用记忆：
{memory_lines}
""".strip()
        if style_state:
            system += "\n\n" + style_prompt_for_state(style_state)
        if rewrite:
            system += "\n\n上一版回复没有通过质量检查。请重写得更自然、克制、低压力，不要暴露内部策略。"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"用户刚发来：{text}"},
    ]


def _compact_retry_messages(messages: list[dict]) -> list[dict]:
    user_message = next((message for message in reversed(messages) if message.get("role") == "user"), messages[-1])
    return [
        {
            "role": "system",
            "content": "Only return the final user-facing reply. Keep it short and natural. Do not include reasoning.",
        },
        {"role": "user", "content": str(user_message.get("content", ""))},
    ]


def _extract_content(body: dict) -> str:
    choices = body.get("choices") or []
    if not choices:
        raise ModelUnavailableError("empty model choices")
    message = choices[0].get("message") or {}
    return str(message.get("content") or "").strip()


async def _call_openai_compatible(messages: list[dict], provider_config: dict | None = None) -> str:
    provider_config = provider_config or {}
    api_key = (os.getenv("DEEPSEEK_API_KEY", "") or provider_config.get("api_key", "")).strip()
    if not api_key:
        raise ModelUnavailableError("missing model api key")

    base_url = (os.getenv("DEEPSEEK_BASE_URL", "") or provider_config.get("base_url", "") or DEFAULT_BASE_URL).rstrip("/")
    model = (os.getenv("DEEPSEEK_MODEL", "") or provider_config.get("model", "") or DEFAULT_MODEL).strip()
    timeout = float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "20"))

    last_body = {}
    try:
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            request_messages = messages
            for _attempt in range(2):
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": request_messages,
                        "temperature": 0.65,
                    },
                )
                response.raise_for_status()
                last_body = response.json()
                content = _extract_content(last_body)
                if content:
                    return content
                request_messages = _compact_retry_messages(messages)
    except Exception as exc:
        if isinstance(exc, ModelUnavailableError):
            raise
        raise ModelUnavailableError(str(exc)) from exc

    finish_reason = ((last_body.get("choices") or [{}])[0].get("finish_reason")) if last_body else None
    raise ModelUnavailableError(f"empty model reply: finish_reason={finish_reason or 'unknown'}")


async def generate_reply(
    text: str,
    memories: list[dict],
    relationship: dict,
    persona: dict,
    attachment: dict,
    goal: dict,
    rewrite: bool = False,
    provider_config: dict | None = None,
    style_state: dict | None = None,
    preference_profile: dict | None = None,
    persona_plan: dict | None = None,
    identity_profile: dict | None = None,
    persona_kernel: dict | None = None,
    conversation_summary: dict | None = None,
    context_understanding: dict | None = None,
    conversation_state: dict | None = None,
    context_pack: dict | None = None,
    conversation_act: dict | None = None,
    interaction_frame: dict | None = None,
    immersive_reality: dict | None = None,
) -> str:
    messages = _build_messages(
        text,
        memories,
        relationship,
        persona,
        attachment,
        goal,
        rewrite,
        style_state,
        preference_profile,
        persona_plan,
        identity_profile,
        persona_kernel,
        conversation_summary,
        context_understanding,
        conversation_state,
        context_pack,
        conversation_act,
        interaction_frame,
        immersive_reality,
    )
    return await _call_openai_compatible(messages, provider_config)
