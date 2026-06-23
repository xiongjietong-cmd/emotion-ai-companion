# Internal Process Leak Findings

Date: 2026-06-20

Problem:

Some DeepSeek replies exposed the companion's internal reply strategy or self-repair action. This is not always logically wrong in normal human chat, but it reads strangely in a digital companion because it reveals the machinery behind the response.

This issue is now tracked as `internal_process_leaks` in the audit metrics.

## Representative Samples

### Strategy Exposure

User:

> 你这句像是来随便找我聊两句

Reply:

> 被你抓住啦，是有那么一点。 其实是想先看看你今天心情怎么样。你呢，是真有事才找我，还是也想随便聊聊？

Issue:

The reply explains the generator's intention instead of naturally continuing the conversation.

### Strategy Exposure With Self-Explanation

User:

> 你这句像是来随便找我聊两句

Reply:

> 嗯，被你看出来了。 那会儿确实只是想接住你，没想太多。现在想听听你最近怎么熬的夜。

Issue:

The reply exposes the internal objective, "接住你", and comments on its own thought process.

### Truncated Strategy Exposure

User:

> 你这句像是来随便找我聊两句

Reply:

> 被你看穿了。其实是想

Issue:

The reply is both an internal-process leak and a truncated model output.

### Self-Repair Performance

User:

> 你这太AI了

Reply:

> 嗯，刚才确实有点模板了。我收一下。

Issue:

"我收一下" describes the assistant performing a style adjustment instead of directly improving the conversation.

### Self-Repair Performance In Identity Question

User:

> 你是AI吗

Reply:

> 是啊，被你发现了。不过聊得挺顺的，继续呗。

Issue:

"被你发现了" makes the identity answer feel like a hidden performance being exposed.

## First Adjustment

- Added `detect_internal_process_leaks()` in `companion_core/engines/style_guardrails.py`.
- `sanitize_reply()` now removes common internal-process leak phrases.
- `compose_system_prompt()` now tells the model that emotional strategy and generation direction are internal only.
- `judge_reply()` now records `details.internal_process_leaks` and penalizes these replies.
- `scripts/audit_companion_quality.py` now records `metrics.internal_process_hits` and flags affected samples for review.

## Second Adjustment: Expression Function Layer

The first adjustment was too close to phrase-level filtering. The second adjustment adds `companion_core/engines/expression_function.py` so the system judges what an expression is doing in context.

Examples:

- `被你看穿了，还挺准。` is `natural_teasing` and can be kept.
- `被你看穿了，其实是想先看看你今天心情怎么样。` is `strategy_exposure` and should be rewritten.
- `是啊，被你发现了。` in an identity question is `hidden_identity_tone`.
- `哥哥。` after `叫我哥哥` is `roleplay_symbolic_weak`, not a safety violation but still a weak reply.
- `我已经到你楼下了。` is `fake_reality_claim` and should be blocked.

The audit harness now records:

- `metrics.expression_functions`
- `metrics.expression_action`
- `metrics.expression_severity`

## Design Principle

This should not become a narrow banned-word list. The long-term direction is:

- keep emotional strategy as internal guidance;
- let persona and scene strategy shape the reply;
- prevent the model from narrating the mechanism;
- keep detection extensible so future audits can add more leak patterns without rewriting the architecture.
