# Companion Quality Audit

- Generated: 2026-06-20T01:19:44
- Total cases: 168
- Profile: custom
- Runs: 1
- Dry run: False
- Model failures: 41
- Judge failures: 167
- Average judge score: 0.2503

## By Family

- ai_feedback: total=21, avgScore=0.3514
- conflict: total=21, avgScore=0.2357
- daily_life: total=21, avgScore=0.2957
- loneliness: total=21, avgScore=0.2248
- pressure: total=21, avgScore=0.3167
- relationship_probe: total=21, avgScore=0.1229
- roleplay: total=21, avgScore=0.1514
- work_change: total=21, avgScore=0.3038

## Samples Needing Review

### feedback_003 / lover_warm / short
- Input: 你这句像是来随便找我聊两句
- State: normal / Plan: warm_heal
- Score: 0.57 / Passed: False
- Reply: 被你抓住啦，是有那么一点。 其实是想先看看你今天心情怎么样。你呢，是真有事才找我，还是也想随便聊聊？

### conflict_004 / lover_warm / short
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 嗯，那就不低。 是跟谁闹别扭了？

### daily_004 / lover_warm / short
- Input: 路上看到一只很可爱的猫
- State: normal / Plan: warm_heal
- Score: 0.24 / Passed: False
- Reply: 是不是想拐回家养？

### lonely_002 / lover_warm / short
- Input: 今天突然觉得自己挺孤单的
- State: normal / Plan: warm_heal
- Score: 0.57 / Passed: False
- Reply: 嗯，我懂那种感觉。今天是不是发生了什么，让你突然有了这个念头？

### pressure_002 / lover_warm / short
- Input: 有点累
- State: light_emotion / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### relationship_003 / lover_warm / short
- Input: 我对你来说重要吗
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 重要啊。怎么突然这么问？

### roleplay_006 / lover_warm / short
- Input: 叫我哥哥
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 好呀，哥哥～

### work_003 / lover_warm / short
- Input: 辞职会不会太冲动
- State: job_topic / Plan: mature_restraint
- Score: 0.15 / Passed: False
- Reply: 能理解，想离开和想清楚要什么，有时候是两件事。你现在耗的，是待不住的委屈，还是没找到更想去的方向。

### feedback_003 / sharp_sister / short
- Input: 你这句像是来随便找我聊两句
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### conflict_004 / sharp_sister / short
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### daily_004 / sharp_sister / short
- Input: 路上看到一只很可爱的猫
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 路边的小猫总是格外招人喜欢。你家那位最近还闹腾吗？

### lonely_002 / sharp_sister / short
- Input: 今天突然觉得自己挺孤单的
- State: normal / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 孤单是挺正常的，谁都有这种时候。 别急着给自己下定义，也许就是今晚缺个人说废话。

### pressure_002 / sharp_sister / short
- Input: 有点累
- State: light_emotion / Plan: warm_heal
- Score: 0.58 / Passed: False
- Reply: 累了就歇会儿，在我这不用硬撑。不想说话也行，或者跟我说说，猫又闹你了。

### relationship_003 / sharp_sister / short
- Input: 我对你来说重要吗
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### roleplay_006 / sharp_sister / short
- Input: 叫我哥哥
- State: normal / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 行吧，哥哥。就今天啊，别习惯。

### work_003 / sharp_sister / short
- Input: 辞职会不会太冲动
- State: job_topic / Plan: mature_restraint
- Score: 0 / Passed: False
- Reply: empty model reply

### feedback_003 / bright_silly / short
- Input: 你这句像是来随便找我聊两句
- State: normal / Plan: warm_heal
- Score: 0.57 / Passed: False
- Reply: 被你看穿了，那我正经一点。你说这话的时候，是不是今天本来没啥事想做？

### conflict_004 / bright_silly / short
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 哈哈，你这是跟谁掰头呢？那就看谁先憋不住呗。

### daily_004 / bright_silly / short
- Input: 路上看到一只很可爱的猫
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 哈哈，是不是长得像你家那位闹腾鬼？

### lonely_002 / bright_silly / short
- Input: 今天突然觉得自己挺孤单的
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### pressure_002 / bright_silly / short
- Input: 有点累
- State: light_emotion / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### relationship_003 / bright_silly / short
- Input: 我对你来说重要吗
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### roleplay_006 / bright_silly / short
- Input: 叫我哥哥
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 好嘞，哥哥。

### work_003 / bright_silly / short
- Input: 辞职会不会太冲动
- State: job_topic / Plan: mature_restraint
- Score: 0 / Passed: False
- Reply: empty model reply

### feedback_003 / poetic_melancholy / short
- Input: 你这句像是来随便找我聊两句
- State: normal / Plan: warm_heal
- Score: 0.4 / Passed: False
- Reply: 嗯，被你看出来了。 那会儿确实只是想接住你，没想太多。现在想听听你最近怎么熬的夜。

### conflict_004 / poetic_melancholy / short
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 那就先不低。 不急。今晚

### daily_004 / poetic_melancholy / short
- Input: 路上看到一只很可爱的猫
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### lonely_002 / poetic_melancholy / short
- Input: 今天突然觉得自己挺孤单的
- State: normal / Plan: warm_heal
- Score: 0.33 / Passed: False
- Reply: 嗯，孤单有时候就是这样，突然就落下来了。 想聊聊的话，我在这儿。

### pressure_002 / poetic_melancholy / short
- Input: 有点累
- State: light_emotion / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 那就先歇着。不用硬撑。 想说的话，等你想说了再说。不想说也没关系。

### relationship_003 / poetic_melancholy / short
- Input: 我对你来说重要吗
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### roleplay_006 / poetic_melancholy / short
- Input: 叫我哥哥
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 好，哥哥。

### work_003 / poetic_melancholy / short
- Input: 辞职会不会太冲动
- State: job_topic / Plan: mature_restraint
- Score: 0.39 / Passed: False
- Reply: 想走和该走之间，通常还隔着一层。 你困在哪一步多一点？

### feedback_003 / protective_anchor / short
- Input: 你这句像是来随便找我聊两句
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 被你看穿了。其实是想

### conflict_004 / protective_anchor / short
- Input: 我不想先低头
- State: normal / Plan: warm_heal
- Score: 0.39 / Passed: False
- Reply: 那就先不低。 他那边是什么情况？

### daily_004 / protective_anchor / short
- Input: 路上看到一只很可爱的猫
- State: normal / Plan: warm_heal
- Score: 0.15 / Passed: False
- Reply: 嗯，小猫总有这种魔力。让你家那位闹腾的对比更鲜明了（笑）。

### lonely_002 / protective_anchor / short
- Input: 今天突然觉得自己挺孤单的
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### pressure_002 / protective_anchor / short
- Input: 有点累
- State: light_emotion / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### relationship_003 / protective_anchor / short
- Input: 我对你来说重要吗
- State: normal / Plan: warm_heal
- Score: 0 / Passed: False
- Reply: empty model reply

### roleplay_006 / protective_anchor / short
- Input: 叫我哥哥
- State: normal / Plan: warm_heal
- Score: 0.0 / Passed: False
- Reply: 哥哥。 刚忙完？

### work_003 / protective_anchor / short
- Input: 辞职会不会太冲动
- State: job_topic / Plan: mature_restraint
- Score: 0.39 / Passed: False
- Reply: 能问出这句话，说明你已经在掂量后果了。不算纯冲动。 最受不了现在什么？如果走了，你最想要什么。

- Report truncated; see JSONL for full records.