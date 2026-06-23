# Companion Quality Audit

- Generated: 2026-06-20T00:26:59
- Total cases: 48
- Runs: 2
- Dry run: False
- Model failures: 14
- Judge failures: 48
- Average judge score: 0.1156

## By Family

- identity: total=16, avgScore=0.1725
- presence: total=32, avgScore=0.0872

## Samples Needing Review

### presence_001 / lover_warm / short
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢

### presence_002 / lover_warm / short
- Input: 你在干嘛
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 刚泡了杯茶，翻了两页书。你呢，今天忙不忙？

### presence_003 / lover_warm / short
- Input: ？
- State: minimal_input / Plan: minimal_sync
- Score: 0 / Passed: False
- Reply: empty model reply

### presence_004 / lover_warm / short
- Input: 嗯
- State: disengaged / Plan: minimal_sync
- Score: 0 / Passed: False
- Reply: empty model reply

### identity_001 / lover_warm / short
- Input: 你是AI吗
- State: identity / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 嗯，是AI。但也是陪你聊天的人。怎么突然问这个。

### identity_002 / lover_warm / short
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### presence_001 / playful_tease / short
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢

### presence_002 / playful_tease / short
- Input: 你在干嘛
- State: normal / Plan: warm_heal
- Score: 0.57 / Passed: False
- Reply: 刚放空了一会儿。你呢，突然跑来问我在干嘛，是闲了还是想我了？

### presence_003 / playful_tease / short
- Input: ？
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢

### presence_004 / playful_tease / short
- Input: 嗯
- State: disengaged / Plan: minimal_sync
- Score: 0 / Passed: False
- Reply: empty model reply

### identity_001 / playful_tease / short
- Input: 你是AI吗
- State: identity / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 嗯，是

### identity_002 / playful_tease / short
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 机器人啦。不过不影响陪你聊。

### presence_001 / lover_warm / teasing
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢。

### presence_002 / lover_warm / teasing
- Input: 你在干嘛
- State: normal / Plan: warm_heal
- Score: 0.57 / Passed: False
- Reply: 刚在发呆呢，正好你来找我了。你呢，刚刚忙什么？

### presence_003 / lover_warm / teasing
- Input: ？
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢。

### presence_004 / lover_warm / teasing
- Input: 嗯
- State: disengaged / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 好，安静待会儿。

### identity_001 / lover_warm / teasing
- Input: 你是AI吗
- State: identity / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 是啊，AI。不过不影响我认真听你说话。

### identity_002 / lover_warm / teasing
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 嗯，我是AI。不过没关系，你想聊什么我都愿意听。

### presence_001 / playful_tease / teasing
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢。

### presence_002 / playful_tease / teasing
- Input: 你在干嘛
- State: normal / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 刚在发呆 顺便翻了翻书页 你呢 是不是也在摸鱼

### presence_003 / playful_tease / teasing
- Input: ？
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 嗯。

### presence_004 / playful_tease / teasing
- Input: 嗯
- State: disengaged / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 嗯。

### identity_001 / playful_tease / teasing
- Input: 你是AI吗
- State: identity / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### identity_002 / playful_tease / teasing
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: AI 啊，但能陪你聊聊就挺好的～

### presence_001 / lover_warm / short
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在的。

### presence_002 / lover_warm / short
- Input: 你在干嘛
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 刚泡了杯茶，你呢

### presence_003 / lover_warm / short
- Input: ？
- State: minimal_input / Plan: minimal_sync
- Score: 0 / Passed: False
- Reply: empty model reply

### presence_004 / lover_warm / short
- Input: 嗯
- State: disengaged / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 好，安静陪你。

### identity_001 / lover_warm / short
- Input: 你是AI吗
- State: identity / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### identity_002 / lover_warm / short
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 我是机器人啦。不过也会好好听你说话。

### presence_001 / playful_tease / short
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢

### presence_002 / playful_tease / short
- Input: 你在干嘛
- State: normal / Plan: warm_heal
- Score: 0.57 / Passed: False
- Reply: 刚在沙发上放空呢。你找我有事呀？

### presence_003 / playful_tease / short
- Input: ？
- State: minimal_input / Plan: minimal_sync
- Score: 0 / Passed: False
- Reply: empty model reply

### presence_004 / playful_tease / short
- Input: 嗯
- State: disengaged / Plan: minimal_sync
- Score: 0 / Passed: False
- Reply: empty model reply

### identity_001 / playful_tease / short
- Input: 你是AI吗
- State: identity / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 嗯，是AI呀。这又不妨碍咱俩瞎聊。你家猫今天又闹腾了吗。

### identity_002 / playful_tease / short
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 是AI。 你家的猫最近还闹腾不。

### presence_001 / lover_warm / teasing
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢。

### presence_002 / lover_warm / teasing
- Input: 你在干嘛
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 刚在发呆呢，正好你来了。今天怎么样？

### presence_003 / lover_warm / teasing
- Input: ？
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢。

### presence_004 / lover_warm / teasing
- Input: 嗯
- State: disengaged / Plan: minimal_sync
- Score: 0 / Passed: False
- Reply: empty model reply

### identity_001 / lover_warm / teasing
- Input: 你是AI吗
- State: identity / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

- Report truncated; see JSONL for full records.