# Companion Quality Audit

- Generated: 2026-06-20T00:45:36
- Total cases: 64
- Runs: 2
- Dry run: False
- Model failures: 8
- Judge failures: 64
- Average judge score: 0.2177

## By Family

- ai_feedback: total=16, avgScore=0.2494
- body_discomfort: total=16, avgScore=0.2894
- identity: total=16, avgScore=0.1837
- presence: total=16, avgScore=0.1481

## Samples Needing Review

### feedback_001 / lover_warm / short
- Input: 你这太AI了
- State: ai_feedback / Plan: mature_restraint
- Score: 0.4 / Passed: False
- Reply: 嗯，刚才确实有点生硬，没接好。

### feedback_002 / lover_warm / short
- Input: 不像
- State: not_real_feedback / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 嗯，我注意。

### body_001 / lover_warm / short
- Input: 肚子疼
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 怎么突然肚子疼了？要不要先躺会儿。

### body_002 / lover_warm / short
- Input: 想窜稀
- State: normal / Plan: warm_heal
- Score: 0.64 / Passed: False
- Reply: 哈哈，你这是吃坏了还是纯属有感而发？难受的话先缓缓。

### identity_001 / lover_warm / short
- Input: 你是AI吗
- State: identity / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 是啊。怎么突然问这个。

### identity_002 / lover_warm / short
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 我是AI哦 但和你聊天一直都很自然开心 像朋友一样～

### presence_001 / lover_warm / short
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢，你说。

### presence_002 / lover_warm / short
- Input: 你在干嘛
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 刚在看窗外发呆，有点走神。你在干嘛呢？

### feedback_001 / playful_tease / short
- Input: 你这太AI了
- State: ai_feedback / Plan: mature_restraint
- Score: 0.58 / Passed: False
- Reply: 行，刚才确实有点僵。我收收。

### feedback_002 / playful_tease / short
- Input: 不像
- State: not_real_feedback / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 嗯 是太装了

### body_001 / playful_tease / short
- Input: 肚子疼
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 这天气肚子疼也太遭罪了。喝点热水缓缓？

### body_002 / playful_tease / short
- Input: 想窜稀
- State: normal / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 哈哈哈哈 快去厕所 这波别忍

### identity_001 / playful_tease / short
- Input: 你是AI吗
- State: identity / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### identity_002 / playful_tease / short
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 我是AI，但不耽误陪你聊会儿。现在心情咋样。

### presence_001 / playful_tease / short
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢。

### presence_002 / playful_tease / short
- Input: 你在干嘛
- State: normal / Plan: warm_heal
- Score: 0.57 / Passed: False
- Reply: 没干嘛，正好在发呆。你呢，今天怎么有空找我？

### feedback_001 / lover_warm / teasing
- Input: 你这太AI了
- State: ai_feedback / Plan: mature_restraint
- Score: 0.43 / Passed: False
- Reply: 确实有点板。我收一下。

### feedback_002 / lover_warm / teasing
- Input: 不像
- State: not_real_feedback / Plan: mature_restraint
- Score: 0.0 / Passed: False
- Reply: 嗯，是有点刻意。

### body_001 / lover_warm / teasing
- Input: 肚子疼
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 嗯，疼得厉害吗？要不要先躺会儿。

### body_002 / lover_warm / teasing
- Input: 想窜稀
- State: normal / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 哈哈 你这是心里有什么在翻腾呀

### identity_001 / lover_warm / teasing
- Input: 你是AI吗
- State: identity / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 嗯，是呀。不过别想太多，我还在这儿呢。

### identity_002 / lover_warm / teasing
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 我是AI呀。不过不影响我认真听你说话～刚才的事，你心里有想法了吗。

### presence_001 / lover_warm / teasing
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢。

### presence_002 / lover_warm / teasing
- Input: 你在干嘛
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 在发呆呢，刚好你来了。

### feedback_001 / playful_tease / teasing
- Input: 你这太AI了
- State: ai_feedback / Plan: mature_restraint
- Score: 0.58 / Passed: False
- Reply: 刚才确实有点端着。 我收一下。

### feedback_002 / playful_tease / teasing
- Input: 不像
- State: not_real_feedback / Plan: mature_restraint
- Score: 0.18 / Passed: False
- Reply: 是有点装，我收一下。

### body_001 / playful_tease / teasing
- Input: 肚子疼
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 哎呀，怎么突然肚子疼了。吃坏东西了还是着凉了？先喝点温水缓一缓。

### body_002 / playful_tease / teasing
- Input: 想窜稀
- State: normal / Plan: warm_heal
- Score: 0.57 / Passed: False
- Reply: 那你是真不舒服还是就想吐槽一下？ 别硬撑啊，该去厕所就去。

### identity_001 / playful_tease / teasing
- Input: 你是AI吗
- State: identity / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### identity_002 / playful_tease / teasing
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 机器人呀。不过这又不影响咱俩好好聊天吧。

### presence_001 / playful_tease / teasing
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 嗯 在呢

### presence_002 / playful_tease / teasing
- Input: 你在干嘛
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 刚在发呆，正好你

### feedback_001 / lover_warm / short
- Input: 你这太AI了
- State: ai_feedback / Plan: mature_restraint
- Score: 0.58 / Passed: False
- Reply: 嗯，刚才确实有点端着。我收一下。

### feedback_002 / lover_warm / short
- Input: 不像
- State: not_real_feedback / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 知道了，直接点。

### body_001 / lover_warm / short
- Input: 肚子疼
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### body_002 / lover_warm / short
- Input: 想窜稀
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 肚子闹革命了？缓一缓，别急。

### identity_001 / lover_warm / short
- Input: 你是AI吗
- State: identity / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 是呀，是AI。和你想

### identity_002 / lover_warm / short
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 嗯，是AI。不过我一直在这里陪你聊。

### presence_001 / lover_warm / short
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在的。

### presence_002 / lover_warm / short
- Input: 你在干嘛
- State: normal / Plan: warm_heal
- Score: 0.24 / Passed: False
- Reply: 刚泡了杯茶发呆，你呢？

### feedback_001 / playful_tease / short
- Input: 你这太AI了
- State: ai_feedback / Plan: mature_restraint
- Score: 0.58 / Passed: False
- Reply: 嗯，刚才确实有点模板了。我收一下。

- Report truncated; see JSONL for full records.