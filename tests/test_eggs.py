from __future__ import annotations

import unittest

from useless_maybe.eggs import EGGS, PAPERWORK_EGGS
from useless_maybe.models import AgentSignals, Detection


class NewEggTests(unittest.TestCase):
    def test_signal_eggs_require_their_own_detection_and_render_counts(self) -> None:
        signals = AgentSignals(tool_calls=1_234, retries=12, repeated_actions=34)
        cases = (
            ("tool_form", "TOOL_OBSESSION", "Tool calls observed: 1,234.\nThe form has no field for results."),
            ("retry_counted", "RETRYING", "Retry count: 12.\nThe counting procedure worked on the first attempt."),
            ("loop_agenda", "LOOPING", "Repeated actions: 34.\nNo precedent has been established."),
        )
        by_id = {egg.id: egg for egg in EGGS}

        self.assertEqual(len(EGGS), 26)  # 23 original IDs plus these three.
        self.assertEqual(len(by_id), len(EGGS))
        for egg_id, detection_name, expected in cases:
            with self.subTest(egg=egg_id):
                egg = by_id[egg_id]
                own_detection = [Detection(detection_name, 0.5, "test signal")]
                other_detection = [Detection("CONTEXT_PRESSURE", 0.5, "unrelated")]
                self.assertTrue(egg.eligible(own_detection, uselessness=0, invocations=1))
                self.assertFalse(egg.eligible(other_detection, uselessness=100, invocations=100))
                self.assertFalse(egg.eligible([], uselessness=100, invocations=100))
                self.assertEqual(egg.render(signals, uselessness=0, invocations=1), expected)

    def test_paperwork_is_separate_ordered_and_invocation_gated(self) -> None:
        self.assertEqual(
            [egg.id for egg in PAPERWORK_EGGS],
            ["paperwork_received", "paperwork_staffed", "paperwork_completed"],
        )
        self.assertFalse({egg.id for egg in PAPERWORK_EGGS} & {egg.id for egg in EGGS})
        for egg in PAPERWORK_EGGS:
            with self.subTest(egg=egg.id):
                self.assertEqual(egg.weight, 0.7)
                self.assertEqual(egg.min_invocations, 8)
                self.assertFalse(egg.eligible([], uselessness=100, invocations=7))
                self.assertTrue(egg.eligible([], uselessness=0, invocations=8))
                self.assertEqual(len(egg.render(AgentSignals(), 0, 8).splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
