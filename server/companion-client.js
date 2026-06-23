export const DEFAULT_COMPANION_CORE_TIMEOUT_MS = 30000;

export function getCompanionCoreUrl() {
  return (process.env.COMPANION_CORE_URL || "http://127.0.0.1:3105").replace(/\/+$/, "");
}

function normalizeSidecarResponse(body) {
  const reply = body.reply || "";
  const replyParts = Array.isArray(body.reply_parts)
    ? body.reply_parts
    : Array.isArray(body.replyParts)
      ? body.replyParts
      : (reply ? [reply] : []);
  return {
    ok: true,
    reply,
    replyParts: replyParts.map((part) => String(part || "").trim()).filter(Boolean),
    relationshipDelta: body.relationship_delta || body.relationshipDelta || {},
    memoryCandidates: body.memory_candidates || body.memoryCandidates || [],
    directorGoal: body.director_goal || body.directorGoal || {},
    judge: body.judge || {},
  };
}

export async function callCompanionCore(payload, options = {}) {
  const timeoutMs = Number(options.timeoutMs || process.env.COMPANION_CORE_TIMEOUT_MS || DEFAULT_COMPANION_CORE_TIMEOUT_MS);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${getCompanionCoreUrl()}/v1/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    const body = await response.json().catch(() => ({}));

    if (!response.ok) {
      const error = new Error(`Companion core failed: ${response.status}`);
      error.code = "COMPANION_CORE_ERROR";
      error.status = response.status;
      error.body = body;
      throw error;
    }

    return normalizeSidecarResponse(body);
  } catch (error) {
    if (error.code === "COMPANION_CORE_ERROR") {
      throw error;
    }
    const wrapped = new Error(`Companion core unavailable: ${error.message}`);
    wrapped.code = "COMPANION_CORE_UNAVAILABLE";
    wrapped.cause = error;
    throw wrapped;
  } finally {
    clearTimeout(timer);
  }
}

export function isCompanionUnavailable(error) {
  const detail = error?.body?.detail || error?.body || {};
  return error?.code === "COMPANION_CORE_UNAVAILABLE"
    || (error?.code === "COMPANION_CORE_ERROR" && error?.status === 503)
    || detail.code === "MODEL_UNAVAILABLE";
}

export async function createCompanionReply(payload, options = {}) {
  return callCompanionCore(payload, options);
}
