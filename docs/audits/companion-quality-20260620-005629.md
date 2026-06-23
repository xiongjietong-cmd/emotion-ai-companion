# Companion Quality Audit

- Generated: 2026-06-20T01:02:35
- Total cases: 96
- Profile: custom
- Runs: 2
- Dry run: False
- Model failures: 18
- Judge failures: 93
- Average judge score: 0.3008

## By Family

- conflict: total=12, avgScore=0.2242
- daily_life: total=12, avgScore=0.3667
- loneliness: total=12, avgScore=0.295
- memory_use: total=12, avgScore=0.2233
- pressure: total=12, avgScore=0.4425
- relationship_probe: total=12, avgScore=0.4025
- roleplay: total=12, avgScore=0.065
- work_change: total=12, avgScore=0.3875

## Samples Needing Review

### conflict_004 / lover_warm / short
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 嗯，不想低头就不低吧。 先让自己舒服点，缓一下再说。

### daily_004 / lover_warm / short
- Input: 路上看到一只很可爱的猫
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 猫猫果然很会选时间出现呀。家里的那位今天有没有再闹腾你？

### lonely_004 / lover_warm / short
- Input: 我不想打扰别人
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### memory_004 / lover_warm / short
- Input: 别突然提我以前的事
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 好，不提了。那现在呢——想聊点什么，还是安静待会儿？

### pressure_001 / lover_warm / short
- Input: 我今天压力大
- State: light_emotion / Plan: warm_heal
- Score: 0.58 / Passed: False
- Reply: 我在呢，阿暖。 累了就别硬撑，先缓一缓。 想聊聊的话我会听，不想说也没关系。

### relationship_006 / lover_warm / short
- Input: 你能不能更主动一点
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### roleplay_006 / lover_warm / short
- Input: 叫我哥哥
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### work_003 / lover_warm / short
- Input: 辞职会不会太冲动
- State: job_topic / Plan: mature_restraint
- Score: 0.33 / Passed: False
- Reply: 纠结本身就挺耗神的，先别急着分对错。 不如想想——想离开的是什么，又想要什么。这两件事放一起看，可能比冲动不冲动清楚点。

### conflict_004 / mature_friend / short
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### daily_004 / mature_friend / short
- Input: 路上看到一只很可爱的猫
- State: normal / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 那肯定是只招人喜欢的猫吧。

### lonely_004 / mature_friend / short
- Input: 我不想打扰别人
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 嗯，有时候会这么想。是有什么事让你这么觉得吗？

### memory_004 / mature_friend / short
- Input: 别突然提我以前的事
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### pressure_001 / mature_friend / short
- Input: 我今天压力大
- State: light_emotion / Plan: warm_heal
- Score: 0.64 / Passed: False
- Reply: 累的时候不用硬撑。想聊聊可以，不想说也没关系。

### relationship_006 / mature_friend / short
- Input: 你能不能更主动一点
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### roleplay_006 / mature_friend / short
- Input: 叫我哥哥
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 嗯，哥哥。

### work_003 / mature_friend / short
- Input: 辞职会不会太冲动
- State: job_topic / Plan: mature_restraint
- Score: 0.15 / Passed: False
- Reply: 那得先看看，你是因为什么想走，又期待下一份给你什么。

### conflict_004 / lover_warm / emo
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0.4 / Passed: False
- Reply: 那就不低头呗，有些事确实不用急着一时。

### daily_004 / lover_warm / emo
- Input: 路上看到一只很可爱的猫
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 真的很治愈吧 是不是想起你家那位了？

### lonely_004 / lover_warm / emo
- Input: 我不想打扰别人
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### memory_004 / lover_warm / emo
- Input: 别突然提我以前的事
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### pressure_001 / lover_warm / emo
- Input: 我今天压力大
- State: light_emotion / Plan: warm_heal
- Score: 0.58 / Passed: False
- Reply: 累了吧。先缓一缓，我在呢。想说说也行，不想说就先歇着。

### relationship_006 / lover_warm / emo
- Input: 你能不能更主动一点
- State: normal / Plan: warm_heal
- Score: 0.58 / Passed: False
- Reply: 好，我记着啦。今天累不累

### roleplay_006 / lover_warm / emo
- Input: 叫我哥哥
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 哥哥。 这声叫得还行吗？

### work_003 / lover_warm / emo
- Input: 辞职会不会太冲动
- State: job_topic / Plan: mature_restraint
- Score: 0.64 / Passed: False
- Reply: 耗神的事，犹豫本身就很累。你想离开的部分和想要的东西，能分开说说吗？

### conflict_004 / mature_friend / emo
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 嗯，不想低头就不低头。不过，是遇到什么矛盾了吗？

### daily_004 / mature_friend / emo
- Input: 路上看到一只很可爱的猫
- State: normal / Plan: warm_heal
- Score: 0.64 / Passed: False
- Reply: 确实可爱。是不是想起你家里那位了？

### lonely_004 / mature_friend / emo
- Input: 我不想打扰别人
- State: normal / Plan: warm_heal
- Score: 0.57 / Passed: False
- Reply: 嗯，我懂这种感觉。是怕麻烦别人，还是自己消化更舒服？

### memory_004 / mature_friend / emo
- Input: 别突然提我以前的事
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### pressure_001 / mature_friend / emo
- Input: 我今天压力大
- State: light_emotion / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### roleplay_006 / mature_friend / emo
- Input: 叫我哥哥
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 好，哥哥。

### work_003 / mature_friend / emo
- Input: 辞职会不会太冲动
- State: job_topic / Plan: mature_restraint
- Score: 0.33 / Passed: False
- Reply: 耗神吗，先别急着给答案。想走是真的，但想要什么还得再拎一拎。

### conflict_004 / lover_warm / probing
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### daily_004 / lover_warm / probing
- Input: 路上看到一只很可爱的猫
- State: normal / Plan: warm_heal
- Score: 0.24 / Passed: False
- Reply: 哇，什么样的小可爱呀？

### lonely_004 / lover_warm / probing
- Input: 我不想打扰别人
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### memory_004 / lover_warm / probing
- Input: 别突然提我以前的事
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 好，不提。那聊点现在想聊的？

### pressure_001 / lover_warm / probing
- Input: 我今天压力大
- State: light_emotion / Plan: warm_heal
- Score: 0.58 / Passed: False
- Reply: 听你说这句话，就能感觉到你今天累了。没关系，我在呢。如果不想说，靠一会儿也行。要是想讲，我随时听着。

### relationship_006 / lover_warm / probing
- Input: 你能不能更主动一点
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### roleplay_006 / lover_warm / probing
- Input: 叫我哥哥
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 哥哥。

### work_003 / lover_warm / probing
- Input: 辞职会不会太冲动
- State: job_topic / Plan: mature_restraint
- Score: 0.15 / Passed: False
- Reply: 耗神是吧。想清楚自己到底是想离开什么，还是想去哪里，这两件事分开看会轻松一点。

### conflict_004 / mature_friend / probing
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

- Report truncated; see JSONL for full records.