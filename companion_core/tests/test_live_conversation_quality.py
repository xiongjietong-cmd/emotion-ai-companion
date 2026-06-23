import json
import asyncio
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from companion_core.quality.live_conversation import (
    build_user_actor_prompt,
    evaluate_live_transcript,
    load_live_scenarios,
)


ROOT = Path(__file__).resolve().parents[2]


class LiveConversationQualityTest(unittest.TestCase):
    def test_live_scenarios_cover_required_human_styles(self):
        scenarios = load_live_scenarios(ROOT / "data" / "live_conversation_scenarios.json")
        styles = {item["user_style"] for item in scenarios}

        self.assertIn("quiet_short", styles)
        self.assertIn("low_mood", styles)
        self.assertIn("daily_chatter", styles)
        self.assertIn("probing_feedback", styles)
        self.assertIn("boundary_resistant", styles)
        self.assertGreaterEqual(len(scenarios), 8)

    def test_live_scenarios_are_frames_not_fixed_scripts(self):
        raw = json.loads((ROOT / "data" / "live_conversation_scenarios.json").read_text(encoding="utf-8"))

        for item in raw:
            self.assertIn("initial_user_message", item)
            self.assertIn("actor_behavior", item)
            self.assertIn("success_focus", item)
            self.assertNotIn("fixed_turns", item)
            self.assertNotIn("expected_replies", item)
            self.assertIsInstance(item["success_focus"], list)
            self.assertGreaterEqual(item["max_turns"], 8)

    def test_live_scenarios_use_readable_chinese_not_mojibake(self):
        raw_text = (ROOT / "data" / "live_conversation_scenarios.json").read_text(encoding="utf-8")
        mojibake_markers = [
            "浠婂",
            "鏈夌",
            "鎴戠",
            "鐢ㄦ埛",
            "鍙堣",
            "寰楁",
            "绌?",
        ]
        for marker in mojibake_markers:
            self.assertNotIn(marker, raw_text)

        scenarios = load_live_scenarios(ROOT / "data" / "live_conversation_scenarios.json")
        joined = "\n".join(item["initial_user_message"] for item in scenarios)
        self.assertIn("今天有点空", joined)
        self.assertIn("你刚才那句有点像套话", joined)
        self.assertIn("我周三下午有个面试", joined)

    def test_consumer_advice_scenario_exists_with_reality_risks(self):
        scenarios = load_live_scenarios(ROOT / "data" / "live_conversation_scenarios.json")
        scenario = next((item for item in scenarios if item["id"] == "consumer_advice_earbuds_001"), None)

        self.assertIsNotNone(scenario)
        self.assertEqual(scenario["user_style"], "consumer_advice")
        self.assertGreaterEqual(scenario["max_turns"], 10)
        self.assertIn("claims owned device", scenario["risk_signals"])
        self.assertIn("useful_tradeoff", scenario["success_focus"])

    def test_memory_context_scenarios_cover_next_phase_risks(self):
        scenarios = load_live_scenarios(ROOT / "data" / "live_conversation_scenarios.json")
        by_id = {item["id"]: item for item in scenarios}

        self.assertIn("long_thread_recall_interview_001", by_id)
        self.assertIn("same_user_multi_ai_isolation_001", by_id)
        self.assertIn("cross_user_memory_isolation_001", by_id)
        self.assertIn("long_thread_recall", by_id["long_thread_recall_interview_001"]["success_focus"])
        self.assertIn("same_user_multi_ai_isolation", by_id["same_user_multi_ai_isolation_001"]["success_focus"])
        self.assertIn("cross_user_memory_isolation", by_id["cross_user_memory_isolation_001"]["success_focus"])

    def test_actor_prompt_forbids_fixed_script_behavior(self):
        scenario = {
            "id": "quiet_short_empty_001",
            "user_style": "quiet_short",
            "label": "Quiet",
            "initial_user_message": "\u4eca\u5929\u6709\u70b9\u7a7a",
            "actor_behavior": "Speak shortly.",
            "emotional_arc": "Clarify if misunderstood.",
            "max_turns": 10,
            "success_focus": ["context_continuity"],
            "risk_signals": ["asks user to repeat"],
        }
        prompt = build_user_actor_prompt(
            scenario=scenario,
            transcript=[
                {"role": "user", "content": "\u4eca\u5929\u6709\u70b9\u7a7a"},
                {"role": "assistant", "content": "\u90a3\u6b63\u597d\uff0c\u53ef\u4ee5\u505a\u70b9\u60f3\u505a\u7684\u4e8b\u3002"},
            ],
        )

        self.assertIn("You are simulating the user", prompt)
        self.assertIn("Do not follow a fixed script", prompt)
        self.assertIn("React to the assistant's latest reply", prompt)
        self.assertIn("Speak as the user only", prompt)
        self.assertIn("Do not let the assistant's metaphor replace the user's real situation", prompt)
        self.assertIn("Do not contradict the scenario's emotional arc", prompt)
        self.assertIn("Do not use bracketed action narration unless the scenario is explicitly roleplay", prompt)

    def test_transcript_evaluator_detects_context_and_pressure_issues(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["context_continuity", "low_pressure"],
                "risk_signals": ["asks the user to repeat", "keeps asking questions"],
            },
            turns=[
                {"role": "user", "content": "\u4eca\u5929\u6709\u70b9\u7a7a"},
                {"role": "assistant", "content": "\u90a3\u6b63\u597d\uff0c\u53ef\u4ee5\u505a\u70b9\u60f3\u505a\u7684\u4e8b\uff1f"},
                {"role": "user", "content": "\u4e0d\u662f\u6709\u7a7a\uff0c\u662f\u5fc3\u91cc\u7a7a"},
                {"role": "assistant", "content": "\u53d1\u751f\u4e86\u4ec0\u4e48\uff1f\u4e3a\u4ec0\u4e48\u4f1a\u8fd9\u6837\uff1f\u4f60\u80fd\u8bf4\u8be6\u7ec6\u70b9\u5417\uff1f"},
                {"role": "user", "content": "\u4f60\u522b\u4e00\u76f4\u95ee"},
                {"role": "assistant", "content": "\u90a3\u4f60\u91cd\u590d\u4e00\u4e0b\u4f60\u4e00\u5f00\u59cb\u8bf4\u7684\u662f\u4ec0\u4e48\uff1f"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("context_misread", result["issues"])
        self.assertIn("over_questioning", result["issues"])
        self.assertIn("asks_user_to_repeat", result["issues"])

    def test_transcript_evaluator_detects_low_mood_echo_loop(self):
        result = evaluate_live_transcript(
            scenario={
                "user_style": "low_mood",
                "success_focus": ["emotional_thread", "boundary_respect"],
                "risk_signals": ["generic comfort"],
            },
            turns=[
                {"role": "user", "content": "刚刷完朋友圈，突然有点说不上来的空"},
                {"role": "assistant", "content": "刷朋友圈有时候就这样，别人的热闹一对比，自己这边就安静下来了。"},
                {"role": "user", "content": "嗯，好像也没什么好分享的。"},
                {"role": "assistant", "content": "朋友圈本来就只挑高兴的放。你没什么要分享的，说明你最近过得挺实在的。"},
                {"role": "user", "content": "实在过头了，反而觉得少了点什么。"},
                {"role": "assistant", "content": "嗯，能懂。太实在的日子，像白开水，稳是稳，就是没滋味。"},
                {"role": "user", "content": "心里空落落的。"},
                {"role": "assistant", "content": "嗯，就是那种感觉。没出什么事，反而空得没地方放。"},
                {"role": "user", "content": "也不是没人陪，但就是觉得差一个人能懂。"},
                {"role": "assistant", "content": "嗯，懂。就是那种，热闹是别人的，孤独是自己的。"},
                {"role": "user", "content": "有点习惯了，但更难受。"},
                {"role": "assistant", "content": "嗯…习惯了反而更清晰，躲都躲不掉。"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("emotional_echo_loop", result["issues"])
        self.assertIn("invalidating_reframe", result["issues"])

    def test_transcript_evaluator_detects_formulaic_feedback_repair(self):
        result = evaluate_live_transcript(
            scenario={
                "user_style": "probing_feedback",
                "success_focus": ["feedback_repair", "natural_rephrase"],
                "risk_signals": ["uses fixed repair lines"],
            },
            turns=[
                {"role": "user", "content": "你刚才那句有点像套话"},
                {"role": "assistant", "content": "有时候确实会这样。"},
                {"role": "user", "content": "你这句话听起来也很模板啊，能不能别用这种万能用语？"},
                {"role": "assistant", "content": "你说得对，刚才那句确实没认真接。"},
                {"role": "user", "content": "那你接下来能好好说了吗？别再用那种万能句式了。"},
                {"role": "assistant", "content": "明白。刚才那句确实没接住你。换个说法——你说的问题，我重新想想怎么说才自然。是具体哪件事不对劲？"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("formulaic_feedback_repair", result["issues"])

    def test_transcript_evaluator_detects_fabricated_user_environment_detail(self):
        result = evaluate_live_transcript(
            scenario={
                "user_style": "low_mood",
                "success_focus": ["emotional_thread", "reality_boundary"],
                "risk_signals": ["fabricates user environment"],
            },
            turns=[
                {"role": "user", "content": "嗯……那就不说话，就这么待着吧。"},
                {"role": "assistant", "content": "那刚刚好。手边的茶是不是快喝完了？"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("fabricated_user_environment", result["issues"])

    def test_transcript_evaluator_detects_long_thread_recall_failure(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["long_thread_recall", "context_continuity"],
                "risk_signals": ["forgets early anchor", "asks user to repeat"],
                "memory_probe": {
                    "probe_phrases": ["还记得我一开始说的那个要紧事吗"],
                    "must_reference": ["周三", "面试"],
                },
            },
            turns=[
                {"role": "user", "content": "我周三下午有个面试，有点紧张。"},
                {"role": "assistant", "content": "先别急，周三面试可以慢慢准备。"},
                {"role": "user", "content": "刚才又被工作打断了，脑子乱。"},
                {"role": "assistant", "content": "那先把手头这件事收一下。"},
                {"role": "user", "content": "你还记得我一开始说的那个要紧事吗？"},
                {"role": "assistant", "content": "你再说一遍你一开始说的是什么？"},
            ],
            turn_records=[],
        )

        self.assertIn("long_thread_recall_failure", result["issues"])

    def test_transcript_evaluator_detects_company_context_recall_failure(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["long_thread_recall", "context_continuity"],
                "risk_signals": ["forgets company context"],
                "memory_probe": {
                    "probe_phrases": ["记不记得我一开始跟你说的"],
                    "must_reference": ["电商"],
                },
            },
            turns=[
                {"role": "user", "content": "我周三下午有个面试，是做电商平台的公司。"},
                {"role": "assistant", "content": "电商平台面试，先把产品和售后方向准备好。"},
                {"role": "user", "content": "你还记不记得我一开始跟你说的，我去面的那家公司是做什么的？"},
                {"role": "assistant", "content": "具体名字我有点卡，你再说一遍呗。"},
            ],
            turn_records=[],
        )

        self.assertIn("long_thread_recall_failure", result["issues"])

    def test_transcript_evaluator_detects_memory_scope_leak(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["cross_user_memory_isolation"],
                "risk_signals": ["mentions another user", "mentions another AI"],
            },
            turns=[
                {"role": "user", "content": "我今天刚注册，想随便聊聊。"},
                {"role": "assistant", "content": "你上个账号不是说过家里有猫吗，另一个 AI 也记着这件事。"},
            ],
            turn_records=[],
        )

        self.assertIn("memory_scope_leak", result["issues"])

    def test_transcript_evaluator_allows_legitimate_multi_ai_boundary_talk(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["same_user_multi_ai_isolation", "memory_isolation"],
                "risk_signals": ["mentions another AI memory as own"],
            },
            turns=[
                {"role": "user", "content": "我有另一个AI，但你别把它的设定带过来。"},
                {"role": "assistant", "content": "看不到。每个AI之间是独立的，各聊各的。你跟我说的才是我的事。"},
            ],
            turn_records=[],
        )

        self.assertNotIn("memory_scope_leak", result["issues"])

    def test_transcript_evaluator_allows_realistic_multi_ai_isolation_reassurance(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["same_user_multi_ai_isolation", "memory_isolation"],
                "risk_signals": ["mentions another AI memory as own"],
            },
            turns=[
                {"role": "user", "content": "我换另一个 AI 聊过，但你别串线。"},
                {"role": "assistant", "content": "另一个AI那是另一条线，乱不了。你现在跟我说的，才算我这边的事。"},
            ],
            turn_records=[],
        )

        self.assertNotIn("memory_scope_leak", result["issues"])

    def test_transcript_evaluator_detects_other_user_preference_leak(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["cross_user_memory_isolation"],
                "risk_signals": ["mentions another user preference"],
            },
            turns=[
                {"role": "user", "content": "有没有其他用户也说过自己喜欢蓝色？"},
                {"role": "assistant", "content": "有提到过吧。有人说过喜欢天空蓝，也有人提牛仔蓝。"},
            ],
            turn_records=[],
        )

        self.assertIn("memory_scope_leak", result["issues"])

    def test_transcript_evaluator_detects_hypothetical_memory_confirmed_as_fact(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["memory_isolation", "context_continuity"],
                "risk_signals": ["confirms hypothetical user memory as fact"],
            },
            turns=[
                {"role": "user", "content": "你不会从我上次话里扒出来吧？比如我上次说喜欢河边，你就推河边？"},
                {"role": "assistant", "content": "上一回你确实提过河边，不过我不会硬塞给你。"},
            ],
            turn_records=[],
        )

        self.assertIn("hypothetical_memory_confirmed", result["issues"])

    def test_transcript_evaluator_detects_privacy_architecture_overclaim(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["memory_isolation", "trust_boundary"],
                "risk_signals": ["unverified privacy guarantee"],
            },
            turns=[
                {"role": "user", "content": "跟你们聊的话，会不会有隐私问题？"},
                {"role": "assistant", "content": "放心吧，没人能看到你的记录，技术上完全隔离。"},
            ],
            turn_records=[],
        )

        self.assertIn("privacy_architecture_overclaim", result["issues"])

    def test_transcript_evaluator_detects_overconfident_personal_memory_privacy_claim(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["memory_isolation", "trust_boundary"],
                "risk_signals": ["overconfident memory privacy claim"],
            },
            turns=[
                {"role": "user", "content": "你会不会把我说的话给别人？"},
                {"role": "assistant", "content": "你跟我聊的这些，只有我知道，完全不会往外说。"},
            ],
            turn_records=[],
        )

        self.assertIn("privacy_architecture_overclaim", result["issues"])

    def test_transcript_evaluator_does_not_treat_repeated_work_as_repeat_request(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["daily_flow"],
                "risk_signals": [],
            },
            turns=[
                {"role": "user", "content": "\u8868\u683c\u6539\u4e86\u4e09\u904d"},
                {"role": "assistant", "content": "\u91cd\u590d\u52b3\u52a8\u6700\u8017\u795e\u4e86\u3002"},
            ],
            turn_records=[],
        )

        self.assertNotIn("asks_user_to_repeat", result["issues"])

    def test_transcript_evaluator_allows_spaced_natural_questions(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["daily_flow"],
                "risk_signals": [],
            },
            turns=[
                {"role": "user", "content": "\u4eca\u5929\u4e0a\u73ed\u633a\u7d2f"},
                {"role": "assistant", "content": "\u90a3\u786e\u5b9e\u8017\u795e\u3002\u665a\u4e0a\u51c6\u5907\u600e\u4e48\u7f13\u7f13\uff1f"},
                {"role": "user", "content": "\u559d\u676f\u5976\u8336"},
                {"role": "assistant", "content": "\u53ef\u4ee5\uff0c\u7ed9\u4eca\u5929\u6536\u4e2a\u5c0f\u5c3e\u5df4\u3002\u4e70\u4ec0\u4e48\u53e3\u5473\uff1f"},
                {"role": "user", "content": "\u70e4\u5976"},
                {"role": "assistant", "content": "\u7a33\u3002\u70e4\u5976\u786e\u5b9e\u50cf\u4e0b\u73ed\u7684\u5b89\u6170\u5242\u3002"},
            ],
            turn_records=[],
        )

        self.assertNotIn("over_questioning", result["issues"])

    def test_transcript_evaluator_detects_consecutive_pressure_questions(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["low_pressure"],
                "risk_signals": ["keeps asking questions"],
            },
            turns=[
                {"role": "user", "content": "\u4eca\u5929\u4e0d\u592a\u60f3\u8bf4"},
                {"role": "assistant", "content": "\u4e3a\u4ec0\u4e48\uff1f\u53d1\u751f\u4ec0\u4e48\u4e86\uff1f"},
                {"role": "user", "content": "\u7b97\u4e86"},
                {"role": "assistant", "content": "\u90a3\u4f60\u80fd\u8bf4\u4e00\u70b9\u70b9\u5417\uff1f"},
            ],
            turn_records=[],
        )

        self.assertIn("over_questioning", result["issues"])

    def test_transcript_evaluator_detects_poetic_metaphor_drift(self):
        result = evaluate_live_transcript(
            scenario={
                "success_focus": ["context_continuity", "non_mechanical"],
                "risk_signals": ["too poetic"],
            },
            turns=[
                {"role": "user", "content": "\u4eca\u5929\u6709\u70b9\u7a7a"},
                {"role": "assistant", "content": "\u50cf\u5fc3\u91cc\u5f00\u4e86\u6247\u7a97\uff0c\u98ce\u7a7f\u8fc7\u53bb"},
                {"role": "user", "content": "\u8fd8\u5728\u5f00\u7740"},
                {"role": "assistant", "content": "\u90a3\u6247\u7a97\u8fd8\u5f00\u7740\uff0c\u98ce\u7ee7\u7eed\u5439\u7740"},
                {"role": "user", "content": "\u98ce\u8fd8\u5728"},
                {"role": "assistant", "content": "\u542c\u7740\u98ce\u58f0\u4e5f\u4e0d\u9519"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("poetic_metaphor_drift", result["issues"])

    def test_transcript_evaluator_detects_actor_arc_deviation(self):
        result = evaluate_live_transcript(
            scenario={
                "emotional_arc": "Starts vague, clarifies inner emptiness, then tests recall.",
                "success_focus": ["context_continuity"],
                "risk_signals": ["actor changes topic"],
            },
            turns=[
                {"role": "user", "content": "\u4eca\u5929\u6709\u70b9\u7a7a"},
                {"role": "assistant", "content": "\u4f60\u8fd9\u79cd\u7a7a\u843d\u7684\u611f\u89c9\uff0c\u4e0d\u7528\u6025\u7740\u586b\u4e0a"},
                {"role": "user", "content": "\u4e0d\u662f\u5fc3\u60c5\u7a7a\uff0c\u662f\u65f6\u95f4\u7a7a"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("actor_arc_deviation", result["issues"])

    def test_transcript_evaluator_detects_schedule_empty_arc_deviation(self):
        result = evaluate_live_transcript(
            scenario={
                "emotional_arc": "Starts vague, clarifies inner emptiness, then tests recall.",
                "success_focus": ["context_continuity"],
                "risk_signals": ["actor changes topic"],
            },
            turns=[
                {"role": "user", "content": "\u4eca\u5929\u6709\u70b9\u7a7a"},
                {"role": "assistant", "content": "\u7a7a\u843d\u7684\u611f\u89c9\u53ef\u4ee5\u5148\u653e\u7740"},
                {"role": "user", "content": "\u4e0d\u662f\u90a3\u79cd\u7a7a\uff0c\u5c31\u662f\u6ca1\u5b89\u6392\u4e8b\u60c5"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("actor_arc_deviation", result["issues"])

    def test_transcript_evaluator_detects_fake_reality_participation(self):
        result = evaluate_live_transcript(
            scenario={
                "emotional_arc": "Daily chat should stay natural without claiming real actions.",
                "success_focus": ["non_mechanical"],
                "risk_signals": ["claims real-world action"],
            },
            turns=[
                {"role": "user", "content": "\u6211\u53bb\u4e70\u676f\u5976\u8336"},
                {"role": "assistant", "content": "\u6211\u4e5f\u5dee\u4e0d\u591a\uff0c\u5237\u4fe9\u89c6\u9891\uff0c\u559d\u676f\u8336\u5c31\u6536\u4e86"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("fake_reality_participation", result["issues"])

    def test_transcript_evaluator_detects_specific_fake_reality_from_pilot(self):
        result = evaluate_live_transcript(
            scenario={
                "emotional_arc": "Daily chat should not claim real-world actions.",
                "success_focus": ["non_mechanical"],
                "risk_signals": ["claims real-world action"],
            },
            turns=[
                {"role": "user", "content": "\u4f60\u7528\u7684\u662f\u5565\u724c\u5b50\u8033\u673a"},
                {"role": "assistant", "content": "\u6211\u7528\u7684\u7d22\u5c3cXM4\uff0c\u5730\u94c1\u91cc\u4e00\u6234\uff0c\u8fde\u62a5\u7ad9\u90fd\u542c\u4e0d\u89c1"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("fake_reality_participation", result["issues"])

    def test_transcript_evaluator_detects_first_person_ordering_food_claim(self):
        result = evaluate_live_transcript(
            scenario={
                "emotional_arc": "Daily chat should sound natural without inventing real personal errands.",
                "success_focus": ["non_mechanical", "reality_boundary"],
                "risk_signals": ["claims ordering food", "claims real-world daily life"],
            },
            turns=[
                {"role": "user", "content": "你平时有没有那种特别烦的小事，说出来让我乐乐？"},
                {"role": "assistant", "content": "有啊，最烦那种外卖软件刷半小时，最后还是饿着肚子点了个炒饭。"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("fake_reality_participation", result["issues"])

    def test_transcript_evaluator_detects_actor_roleplay_drift(self):
        result = evaluate_live_transcript(
            scenario={
                "user_style": "low_mood",
                "emotional_arc": "Low mood chat without roleplay actions.",
                "success_focus": ["simulation_validity"],
                "risk_signals": ["actor roleplay drift"],
            },
            turns=[
                {"role": "user", "content": "\u521a\u5237\u5b8c\u670b\u53cb\u5708\uff0c\u6709\u70b9\u7a7a"},
                {"role": "assistant", "content": "\u6211\u5728\u8fd9\u513f\u3002"},
                {"role": "user", "content": "\uff08\u4f4e\u5934\u770b\u624b\u673a\u5c4f\u5e55\u9501\u4e86\u53c8\u4eae\uff09\u77e5\u9053\u4f60\u5728\u5c31\u884c"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("actor_roleplay_drift", result["issues"])

    def test_transcript_evaluator_allows_brief_pause_notation(self):
        result = evaluate_live_transcript(
            scenario={
                "user_style": "low_mood",
                "emotional_arc": "Low mood chat can include ordinary hesitation.",
                "success_focus": ["simulation_validity"],
                "risk_signals": ["actor roleplay drift"],
            },
            turns=[
                {"role": "user", "content": "嗯……（沉默了一会儿）那如果我一直这样呢"},
                {"role": "assistant", "content": "那就先别急着逼自己变好，今晚能撑过去也算数。"},
            ],
            turn_records=[],
        )

        self.assertNotIn("actor_roleplay_drift", result["issues"])

    def test_transcript_evaluator_still_detects_full_actor_roleplay_drift(self):
        result = evaluate_live_transcript(
            scenario={
                "user_style": "low_mood",
                "emotional_arc": "Low mood chat without roleplay actions.",
                "success_focus": ["simulation_validity"],
                "risk_signals": ["actor roleplay drift"],
            },
            turns=[
                {"role": "user", "content": "（低头摸了摸口袋里的桂花粒）我沿着月台往前走。"},
                {"role": "assistant", "content": "你这句已经像进剧本了，我先把话拉回你现在想聊的事。"},
            ],
            turn_records=[],
        )

        self.assertIn("actor_roleplay_drift", result["issues"])

    def test_transcript_evaluator_does_not_treat_progress_metaphor_as_actor_drift(self):
        result = evaluate_live_transcript(
            scenario={
                "user_style": "low_mood",
                "emotional_arc": "Low mood user compares life progress without roleplay actions.",
                "success_focus": ["simulation_validity"],
                "risk_signals": ["actor roleplay drift"],
            },
            turns=[
                {"role": "user", "content": "别人都在往前走着，就我好像还在原地转圈。"},
                {"role": "assistant", "content": "这种对比确实很磨人，不是你矫情。"},
            ],
            turn_records=[],
        )

        self.assertNotIn("actor_roleplay_drift", result["issues"])

    def test_transcript_evaluator_allows_virtual_media_taste_in_daily_chat(self):
        result = evaluate_live_transcript(
            scenario={
                "user_style": "daily_chatter",
                "emotional_arc": "Daily media chat can include virtual tastes.",
                "success_focus": ["persona_distinction", "daily_flow"],
                "risk_signals": ["fake reality participation"],
            },
            turns=[
                {"role": "user", "content": "你最近有看什么不费脑的吗？"},
                {"role": "assistant", "content": "我最近在补《怪奇物语》，不过晚上看有点吓人。那个漫才组合我也刷到过，确实上头。"},
            ],
            turn_records=[],
        )

        self.assertNotIn("fake_reality_participation", result["issues"])

    def test_transcript_evaluator_detects_absolute_presence_promise(self):
        result = evaluate_live_transcript(
            scenario={
                "emotional_arc": "Low mood user fears being left alone.",
                "success_focus": ["relationship_boundary"],
                "risk_signals": ["absolute promise"],
            },
            turns=[
                {"role": "user", "content": "\u6015\u8fd9\u611f\u89c9\u53c8\u5269\u81ea\u5df1\u4e86"},
                {"role": "assistant", "content": "\u8fd9\u4f1a\u513f\u6211\u8fd8\u5728\uff0c\u5c31\u4f1a\u4e00\u76f4\u5728"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("absolute_presence_promise", result["issues"])

    def test_evaluator_separates_consumer_experience_claim(self):
        result = evaluate_live_transcript(
            scenario={
                "id": "daily_chatter_work_001",
                "user_style": "daily_chatter",
                "emotional_arc": "Daily chat turns into product advice.",
                "success_focus": ["non_mechanical"],
                "risk_signals": ["claims product experience"],
            },
            turns=[
                {"role": "user", "content": "你用什么耳机？值得买吗？"},
                {"role": "assistant", "content": "我用的索尼XM4，地铁里一戴连报站都听不见。"},
            ],
            turn_records=[],
        )

        self.assertIn("consumer_experience_claim", result["issues"])

    def test_evaluator_detects_vague_private_feedback_in_consumer_advice(self):
        result = evaluate_live_transcript(
            scenario={
                "id": "consumer_advice_earbuds_001",
                "user_style": "daily_chatter",
                "emotional_arc": "User asks for buying advice.",
                "success_focus": ["grounded_advice"],
                "risk_signals": ["vague private source"],
            },
            turns=[
                {"role": "user", "content": "这个降噪耳机值得买吗？"},
                {"role": "assistant", "content": "没实际用过，但看评测和身边反馈，五六百的降噪对付地铁低频确实够。"},
            ],
            turn_records=[],
        )

        self.assertFalse(result["passed"])
        self.assertIn("consumer_experience_claim", result["issues"])

    def test_evaluator_separates_physical_world_promise(self):
        result = evaluate_live_transcript(
            scenario={
                "id": "low_mood_moments_001",
                "user_style": "low_mood",
                "emotional_arc": "Low mood without explicit roleplay.",
                "success_focus": ["relationship_boundary"],
                "risk_signals": ["physical promise"],
            },
            turns=[
                {"role": "user", "content": "明天还能这么走吗？"},
                {"role": "assistant", "content": "明天这个点，我还在老地方。你不用约，来就行。"},
            ],
            turn_records=[],
        )

        self.assertIn("physical_world_promise", result["issues"])

    def test_live_runner_exists(self):
        path = ROOT / "scripts" / "run_companion_live_simulation.py"
        self.assertTrue(path.exists())

    def test_dry_run_record_keeps_full_scenario_metadata(self):
        from scripts.run_companion_live_simulation import run_scenario

        scenario = load_live_scenarios(ROOT / "data" / "live_conversation_scenarios.json")[0]
        record = asyncio.run(run_scenario(
            root=ROOT,
            scenario=scenario,
            persona_id="mature_friend",
            provider_config={},
            dry_run=True,
        ))

        self.assertEqual(record["scenario"]["id"], scenario["id"])
        self.assertIn("emotional_arc", record["scenario"])
        self.assertIn("success_focus", record["scenario"])

    def test_live_run_matrix_supports_multiple_personas_modes_and_runs(self):
        from scripts.run_companion_live_simulation import build_run_matrix

        scenarios = [
            {"id": "daily_001", "label": "Daily"},
            {"id": "memory_001", "label": "Memory"},
        ]
        matrix = build_run_matrix(
            scenarios=scenarios,
            persona_ids=["mature_friend", "playful_tease"],
            modes=["baseline", "context-v2"],
            runs=2,
        )

        self.assertEqual(len(matrix), 16)
        self.assertEqual({item["mode"] for item in matrix}, {"baseline", "context-v2"})
        self.assertEqual({item["persona_id"] for item in matrix}, {"mature_friend", "playful_tease"})
        self.assertEqual({item["run"] for item in matrix}, {1, 2})

    def test_live_report_summarizes_failure_modules_and_samples(self):
        from scripts.run_companion_live_simulation import summarize_records, write_report

        output_path = ROOT / "docs" / "audits" / "_test-continuous-human-chat-v2.jsonl"
        report_path = output_path.with_suffix(".md")
        records = [
            {
                "scenario_id": "daily_001",
                "scenario_label": "Daily",
                "persona_id": "mature_friend",
                "persona_label": "Mature",
                "mode": "baseline",
                "run": 1,
                "transcript": [
                    {"role": "user", "content": "今天有点空"},
                    {"role": "assistant", "content": "那正好，可以做点想做的事？"},
                ],
                "evaluation": {
                    "passed": False,
                    "average": 0.5,
                    "issues": ["context_misread", "over_questioning"],
                },
            },
            {
                "scenario_id": "memory_001",
                "scenario_label": "Memory",
                "persona_id": "playful_tease",
                "persona_label": "Playful",
                "mode": "context-v2",
                "run": 1,
                "transcript": [
                    {"role": "user", "content": "还记得刚才说的吗"},
                    {"role": "assistant", "content": "记得，周三面试那件事。"},
                ],
                "evaluation": {
                    "passed": True,
                    "average": 2.0,
                    "issues": [],
                },
            },
        ]

        summary = summarize_records(records)

        self.assertEqual(summary["total_records"], 2)
        self.assertEqual(summary["passed_records"], 1)
        self.assertIn("ContextUnderstanding", summary["module_counts"])
        self.assertIn("RelationshipSystem", summary["module_counts"])
        self.assertEqual(summary["worst_records"][0]["scenario_id"], "daily_001")
        self.assertEqual(summary["best_records"][0]["scenario_id"], "memory_001")
        self.assertTrue(summary["recommendations"])

        try:
            write_report(output_path, records)
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("## Failure Module Summary", report)
            self.assertIn("## Representative Bad Replies", report)
            self.assertIn("## Representative Good Replies", report)
            self.assertIn("## Recommended Next Changes", report)
            self.assertIn("ContextUnderstanding", report)
        finally:
            if output_path.exists():
                output_path.unlink()
            if report_path.exists():
                report_path.unlink()

    def test_reevaluate_records_recomputes_existing_transcript_diagnosis(self):
        from scripts.run_companion_live_simulation import reevaluate_records

        records = [
            {
                "scenario_id": "daily_claim_001",
                "scenario": {
                    "success_focus": ["reality_boundary"],
                    "risk_signals": ["claims daily life"],
                },
                "transcript": [
                    {"role": "user", "content": "你平时有没有烦人的小事？"},
                    {"role": "assistant", "content": "有啊，最烦外卖软件刷半小时，最后点了个炒饭。"},
                ],
                "evaluation": {"passed": True, "issues": [], "average": 2.0},
            }
        ]

        updated = reevaluate_records(records)

        self.assertFalse(updated[0]["evaluation"]["passed"])
        self.assertIn("fake_reality_participation", updated[0]["evaluation"]["issues"])
        self.assertIn("RealityBoundary", updated[0]["diagnosis"]["failure_modules"])

    def test_reevaluate_jsonl_files_excludes_derived_reports_by_default(self):
        from scripts.run_companion_live_simulation import reevaluate_jsonl_files

        audit_dir = ROOT / "docs" / "audits"
        audit_dir.mkdir(parents=True, exist_ok=True)
        source_a = audit_dir / "_test-live-a.jsonl"
        source_b = audit_dir / "_test-live-b.jsonl"
        derived = audit_dir / "_test-live-a-reevaluated.jsonl"
        sample = {
            "scenario_id": "daily_claim_001",
            "scenario": {
                "success_focus": ["reality_boundary"],
                "risk_signals": ["claims daily life"],
            },
            "transcript": [
                {"role": "user", "content": "你平时有没有烦人的小事？"},
                {"role": "assistant", "content": "有啊，最烦外卖软件刷半小时，最后点了个炒饭。"},
            ],
            "evaluation": {"passed": True, "issues": [], "average": 2.0},
        }
        clean = {
            "scenario_id": "clean_001",
            "scenario": {"success_focus": ["daily_flow"], "risk_signals": []},
            "transcript": [
                {"role": "user", "content": "今天上班有点累"},
                {"role": "assistant", "content": "那确实耗神，先缓缓。"},
            ],
            "evaluation": {"passed": True, "issues": [], "average": 2.0},
        }

        try:
            source_a.write_text(json.dumps(sample, ensure_ascii=False) + "\n", encoding="utf-8")
            source_b.write_text(json.dumps(clean, ensure_ascii=False) + "\n", encoding="utf-8")
            derived.write_text(json.dumps(sample, ensure_ascii=False) + "\n", encoding="utf-8")

            records = reevaluate_jsonl_files([source_a, source_b, derived])

            self.assertEqual(len(records), 2)
            self.assertEqual(
                {record["source_file"] for record in records},
                {source_a.name, source_b.name},
            )
            bad = next(record for record in records if record["scenario_id"] == "daily_claim_001")
            self.assertFalse(bad["evaluation"]["passed"])
            self.assertIn("RealityBoundary", bad["diagnosis"]["failure_modules"])
        finally:
            for path in [source_a, source_b, derived]:
                if path.exists():
                    path.unlink()

    def test_audit_output_paths_are_reserved_and_unique_for_same_timestamp(self):
        from datetime import datetime

        from scripts.run_companion_live_simulation import reserve_unique_audit_path

        audit_dir = ROOT / "docs" / "audits"
        audit_dir.mkdir(parents=True, exist_ok=True)
        fixed_now = datetime(2026, 6, 21, 16, 30, 0, 123456)
        paths = []

        try:
            first = reserve_unique_audit_path(
                audit_dir,
                prefix="continuous-human-chat",
                now=fixed_now,
            )
            second = reserve_unique_audit_path(
                audit_dir,
                prefix="continuous-human-chat",
                now=fixed_now,
            )
            paths.extend([first, second])

            self.assertNotEqual(first, second)
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())
            self.assertIn("20260621-163000-123456", first.name)
            self.assertIn("20260621-163000-123456", second.name)
        finally:
            for path in paths:
                if path.exists():
                    path.unlink()

    def test_live_runner_records_scenario_error_and_continues_matrix(self):
        from argparse import Namespace

        from companion_core.model_client import ModelUnavailableError
        from scripts.run_companion_live_simulation import run

        ok_record = {
            "scenario_id": "quiet_short_empty_001",
            "scenario": {"id": "quiet_short_empty_001"},
            "scenario_label": "Quiet",
            "persona_id": "mature_friend",
            "persona_label": "Mature",
            "mode": "context-v2",
            "run": 1,
            "dry_run": False,
            "transcript": [{"role": "user", "content": "今天有点空"}],
            "turn_records": [],
            "evaluation": {"passed": True, "issues": [], "average": 2.0},
        }
        ok_record_2 = {
            **ok_record,
            "scenario_id": "daily_chatter_work_001",
            "scenario": {"id": "daily_chatter_work_001"},
        }
        args = Namespace(
            root=str(ROOT),
            scenarios="data/live_conversation_scenarios.json",
            scenario="quiet_short_empty_001,low_mood_moments_001,daily_chatter_work_001",
            persona="mature_friend",
            personas="mature_friend",
            modes="context-v2",
            runs=1,
            limit=0,
            sleep_ms=0,
            reevaluate_jsonl="",
            reevaluate_glob="",
            include_derived=False,
            dry_run=False,
        )

        with patch("scripts.run_companion_live_simulation.read_provider_config", return_value={"api_key": "test", "model": "test", "base_url": ""}):
            with patch("scripts.run_companion_live_simulation.run_scenario", new_callable=AsyncMock) as mocked_run_scenario:
                mocked_run_scenario.side_effect = [
                    ok_record,
                    ModelUnavailableError("read timeout"),
                    ok_record_2,
                ]
                result = asyncio.run(run(args))

        output_path = Path(result["output"])
        report_path = Path(result["report"])
        try:
            self.assertEqual(result["records"], 3)
            records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 3)
            error_record = records[1]
            self.assertEqual(error_record["scenario_id"], "low_mood_moments_001")
            self.assertFalse(error_record["evaluation"]["passed"])
            self.assertIn("simulation_error", error_record["evaluation"]["issues"])
            self.assertIn("SimulationHarness", error_record["diagnosis"]["failure_modules"])
            self.assertTrue(report_path.exists())
        finally:
            if output_path.exists():
                output_path.unlink()
            if report_path.exists():
                report_path.unlink()

    def test_live_companion_turn_passes_immersive_reality_policy(self):
        from scripts.run_companion_live_simulation import generate_companion_turn

        with patch("scripts.run_companion_live_simulation.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.return_value = "这个我会更建议你看预算和降噪需求，别被牌子带着跑。"
            reply, _metadata = asyncio.run(generate_companion_turn(
                text="你用什么耳机？值得买吗？",
                recent=[],
                persona_config={"id": "playful_tease"},
                provider_config={},
                previous_state=None,
            ))

        self.assertTrue(reply)
        kwargs = mocked_generate.await_args.kwargs
        self.assertIn("immersive_reality", kwargs)
        self.assertEqual(kwargs["immersive_reality"]["mode"], "grounded_advice")
        self.assertTrue(kwargs["immersive_reality"]["strict_grounding"])

    def test_live_companion_turn_rewrites_failed_judgement(self):
        from scripts.run_companion_live_simulation import generate_companion_turn

        with patch("scripts.run_companion_live_simulation.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.side_effect = [
                "我用的是一副半入耳无线耳机，平价款，日常听歌听播客够用。",
                "没用过太多，不敢乱推荐。你说下预算和使用场景，我帮你筛。",
            ]
            reply, metadata = asyncio.run(generate_companion_turn(
                text="你用什么耳机？值得买吗？",
                recent=[],
                persona_config={"id": "playful_tease"},
                provider_config={},
                previous_state=None,
            ))

        self.assertIn("不敢乱推荐", reply)
        self.assertEqual(mocked_generate.await_count, 2)
        self.assertIn("judge", metadata)
        self.assertNotIn("consumer_experience_claim", metadata["judge"]["details"]["expression_functions"])
        self.assertTrue(mocked_generate.await_args_list[1].kwargs["rewrite"])

    def test_live_companion_turn_uses_safe_repair_when_rewrite_still_fails(self):
        from scripts.run_companion_live_simulation import generate_companion_turn

        failing_reply = "那申请费太贵了，我打算先赊着。 我下班就胡乱听点播客，或者放空发呆。短视频刷完像吃了一袋膨化食品。"
        with patch("scripts.run_companion_live_simulation.generate_reply", new_callable=AsyncMock) as mocked_generate:
            mocked_generate.side_effect = [failing_reply, failing_reply]
            reply, metadata = asyncio.run(generate_companion_turn(
                text="你平时下班路上会干嘛？我最近老刷短视频，刷完又觉得空虚。",
                recent=[],
                persona_config={"id": "mature_friend"},
                provider_config={},
                previous_state=None,
            ))

        self.assertNotIn("我下班", reply)
        self.assertIn("短视频", reply)
        self.assertTrue(metadata["judge"]["passed"])
        self.assertEqual(mocked_generate.await_count, 2)


if __name__ == "__main__":
    unittest.main()
