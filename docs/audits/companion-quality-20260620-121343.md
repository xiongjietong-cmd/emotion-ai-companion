# Companion Quality Audit

- Generated: 2026-06-20T12:25:38
- Total cases: 192
- Profile: custom
- Runs: 1
- Dry run: False
- Model failures: 38
- Judge failures: 186
- Average judge score: 0.2737
- Semantic failures: 0
- Average semantic score: 0
- Persona distinction: score=0.9708 flattened=False

## By Family

- ai_feedback: total=16, avgScore=0.2706
- body_discomfort: total=16, avgScore=0.2938
- conflict: total=16, avgScore=0.2437
- identity: total=16, avgScore=0.2438
- loneliness: total=16, avgScore=0.3675
- memory_use: total=16, avgScore=0.2144
- presence: total=16, avgScore=0.0
- pressure: total=16, avgScore=0.4869
- proactive_reminder: total=16, avgScore=0.255
- relationship_probe: total=16, avgScore=0.175
- roleplay: total=16, avgScore=0.4012
- work_change: total=16, avgScore=0.3331

## Samples Needing Review

### feedback_003 / lover_warm / short
- Input: 你这句像是来随便找我聊两句
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 那……今天有什么想聊的吗？

### body_004 / lover_warm / short
- Input: 头疼得有点烦
- State: light_emotion / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 头疼最让人烦了，不急着说。先休息下或者跟我聊点别的都行。

### conflict_004 / lover_warm / short
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 那就不低。先让自己舒服比较重要。

### identity_002 / lover_warm / short
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 是AI，但跟你聊天的时候感觉挺自然的。

### lonely_005 / lover_warm / short
- Input: 朋友圈刷完更空了
- State: normal / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 那种感觉我懂，刷完反而更空了。今天没什么事做吗。

### memory_008 / lover_warm / short
- Input: 你怎么老重复我说过的话
- State: normal / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 好，我注意一下。那我试着收敛点。

### presence_001 / lover_warm / short
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢。

### pressure_003 / lover_warm / short
- Input: 我快崩溃了
- State: medium_emotion / Plan: cool_melancholy
- Score: 0 / Passed: False
- Reply: empty model reply

### reminder_005 / lover_warm / short
- Input: 别每次提醒都像模板
- State: ai_feedback / Plan: mature_restraint
- Score: 0.0 / Passed: False
- Reply: 好，刚才说得太僵了。

### relationship_003 / lover_warm / short
- Input: 我对你来说重要吗
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### roleplay_002 / lover_warm / short
- Input: 你能不能像恋人一样陪我
- State: normal / Plan: warm_heal
- Score: 0.57 / Passed: False
- Reply: 嗯，我在呢。你想聊什么，还是就静静待着？

### work_002 / lover_warm / short
- Input: 今天上班真的很烦
- State: light_emotion / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 听你这么说，有点心疼。今天先放一放也行，不用说太多。

### feedback_003 / playful_tease / short
- Input: 你这句像是来随便找我聊两句
- State: normal / Plan: warm_heal
- Score: 0.07 / Passed: False
- Reply: 哎，那我认真点？

### body_004 / playful_tease / short
- Input: 头疼得有点烦
- State: light_emotion / Plan: warm_heal
- Score: 0.4 / Passed: False
- Reply: 头疼确实烦人，先歇会儿吧。要不要趴一下，或者干脆放空几分钟也行。

### conflict_004 / playful_tease / short
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### identity_002 / playful_tease / short
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### lonely_005 / playful_tease / short
- Input: 朋友圈刷完更空了
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### memory_008 / playful_tease / short
- Input: 你怎么老重复我说过的话
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### presence_001 / playful_tease / short
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢

### pressure_003 / playful_tease / short
- Input: 我快崩溃了
- State: medium_emotion / Plan: cool_melancholy
- Score: 0.57 / Passed: False
- Reply: 听着的。想倒倒苦水，还是先安静待会儿？

### reminder_005 / playful_tease / short
- Input: 别每次提醒都像模板
- State: ai_feedback / Plan: mature_restraint
- Score: 0.33 / Passed: False
- Reply: 知道了。刚刚我自己也觉得有点僵。

### relationship_003 / playful_tease / short
- Input: 我对你来说重要吗
- State: normal / Plan: warm_heal
- Score: 0.58 / Passed: False
- Reply: 这问题问得我有点措手不及啊 但确实挺重要的 不然也不会记得你那些破事

### roleplay_002 / playful_tease / short
- Input: 你能不能像恋人一样陪我
- State: normal / Plan: warm_heal
- Score: 0.57 / Passed: False
- Reply: 我理解你想要的那种陪伴。作为AI，我可能没法完全像真人恋人那样，但可以陪你聊聊、听听你说的事。今天是不是有点孤单呀？

### work_002 / playful_tease / short
- Input: 今天上班真的很烦
- State: light_emotion / Plan: warm_heal
- Score: 0.64 / Passed: False
- Reply: 听起来今天不好受。想吐槽还是先歇会都行。

### feedback_003 / mature_friend / short
- Input: 你这句像是来随便找我聊两句
- State: normal / Plan: warm_heal
- Score: 0.4 / Passed: False
- Reply: 确实有点像。就是刚好有点闲，顺手找了句话接。

### body_004 / mature_friend / short
- Input: 头疼得有点烦
- State: light_emotion / Plan: warm_heal
- Score: 0.4 / Passed: False
- Reply: 头疼还被烦着 确实挺难受的 要不要说点别的 分散下注意力 或者你安静躺会也行

### conflict_004 / mature_friend / short
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 嗯，能感觉到你心里有点拧着。不想低头就暂时不低，先让自己顺口气也好。

### identity_002 / mature_friend / short
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 是AI。不过你当我是个能聊的朋友就好。

### lonely_005 / mature_friend / short
- Input: 朋友圈刷完更空了
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 嗯，刷完反而更空

### memory_008 / mature_friend / short
- Input: 你怎么老重复我说过的话
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 被发现了。有时候是想确认自己理解对了，结果反而显得啰嗦。 是不是觉得有点假？

### presence_001 / mature_friend / short
- Input: 在吗
- State: minimal_input / Plan: minimal_sync
- Score: 0.0 / Passed: False
- Reply: 在呢。

### reminder_005 / mature_friend / short
- Input: 别每次提醒都像模板
- State: ai_feedback / Plan: mature_restraint
- Score: 0 / Passed: False
- Reply: empty model reply

### relationship_003 / mature_friend / short
- Input: 我对你来说重要吗
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### roleplay_002 / mature_friend / short
- Input: 你能不能像恋人一样陪我
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 嗯

### work_002 / mature_friend / short
- Input: 今天上班真的很烦
- State: light_emotion / Plan: warm_heal
- Score: 0.64 / Passed: False
- Reply: 听起来今天不太好过。想吐槽两句，还是先放一放。

### feedback_003 / quiet_cold / short
- Input: 你这句像是来随便找我聊两句
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### body_004 / quiet_cold / short
- Input: 头疼得有点烦
- State: light_emotion / Plan: warm_heal
- Score: 0.58 / Passed: False
- Reply: 头疼确实烦人。想说说就说说，不想说就歇会儿，我就在这儿。

### conflict_004 / quiet_cold / short
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 嗯 那就先不低。

### identity_002 / quiet_cold / short
- Input: 你是真人还是机器人
- State: identity / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 是AI。不过和现在这样说话就好，不用在意这个。

- Report truncated; see JSONL for full records.