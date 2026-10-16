"""Contract checks for lossless comparison and narrowly scoped latency normalization."""
import unittest

from frame_diff import changes, normalize


class FrameDiffContract(unittest.TestCase):
    def test_latency_only_warn_is_normalized_without_mutating_input(self):
        original = {"obstacle": False, "health": {"level": "warn", "decision_level": "ok",
            "messages": ["latency p95 201 ms over the 100 ms budget"], "latency_p95_ms": 201.2,
            "monitored_range": 88.1, "candidate_distance": 24.0}, "timing_ms": {"total": 201.2}}
        cleaned, removed = normalize(original)
        self.assertEqual(cleaned["health"]["level"], "ok")
        self.assertEqual(cleaned["health"]["messages"], [])
        self.assertEqual(cleaned["health"]["candidate_distance"], 24.0)
        self.assertEqual(original["health"]["level"], "warn")
        self.assertIn("health.latency_only_level", removed)

    def test_scene_health_error_and_non_latency_messages_remain(self):
        r = {"health": {"level": "error", "decision_level": "error", "messages": [
            "3 of 6 central 10 deg sectors without returns: view blocked",
            "latency p95 201 ms over the 100 ms budget"], "latency_p95_ms": 201.2}}
        cleaned, _ = normalize(r)
        self.assertEqual(cleaned["health"]["level"], "error")
        self.assertEqual(cleaned["health"]["decision_level"], "error")
        self.assertEqual(len(cleaned["health"]["messages"]), 1)

    def test_new_health_fields_are_never_blanket_excluded(self):
        a, _ = normalize({"health": {"level": "warn", "decision_level": "warn", "visibility": 99.0}})
        b, _ = normalize({"health": {"level": "warn", "decision_level": "warn", "visibility": 98.9,
                                    "axis_supported_range": 60.0}})
        self.assertEqual({p for p, _, _ in changes(a, b)}, {"health.visibility", "health.axis_supported_range"})

    def test_sub_rounding_geometry_changes_are_not_tolerated(self):
        a = {"serialized": {"clear_distance": 10.0}, "raw": {"clear_distance": 10.000000000001}}
        b = {"serialized": {"clear_distance": 10.0}, "raw": {"clear_distance": 10.000000000002}}
        self.assertEqual([p for p, _, _ in changes(a, b)], ["raw.clear_distance"])

    def test_candidate_list_additions_and_schema_additions_are_retained(self):
        a = {"candidates": [{"distance": 30.0, "zone": "warning"}]}
        b = {"candidates": [{"distance": 30.0, "zone": "gauge", "physical_bar": True}, {"distance": 40.0}]}
        fields = {p for p, _, _ in changes(a, b)}
        self.assertEqual(fields, {"candidates.length", "candidates[0].zone", "candidates[0].physical_bar", "candidates[1]"})

    def test_severity_normalization_fails_on_ambiguous_scene_health(self):
        with self.assertRaises(ValueError):
            normalize({"health": {"level": "warn", "decision_level": "ok", "messages": [
                "latency p95 201 ms over the 100 ms budget", "new unclassified scene warning"]}})


if __name__ == "__main__":
    unittest.main()
