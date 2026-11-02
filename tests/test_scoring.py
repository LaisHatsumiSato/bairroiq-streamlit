import unittest

from bairroiq.sample_data import SampleDataProvider
from bairroiq.scoring import build_scenario_insight, score_neighborhoods


class ScoreNeighborhoodsTests(unittest.TestCase):
    def test_custom_priorities_change_the_ranking(self) -> None:
        metrics = SampleDataProvider().load_metrics()
        greenery = score_neighborhoods(
            metrics, {"trees": 100, "safety": 0, "mobility": 0, "budget": 0}
        )
        affordability = score_neighborhoods(
            metrics, {"trees": 0, "safety": 0, "mobility": 0, "budget": 100}
        )

        self.assertEqual(greenery.iloc[0]["neighborhood"], "Perdizes")
        self.assertEqual(affordability.iloc[0]["neighborhood"], "Sé")

    def test_zero_weights_are_rejected(self) -> None:
        metrics = SampleDataProvider().load_metrics()
        with self.assertRaisesRegex(ValueError, "ao menos uma prioridade"):
            score_neighborhoods(
                metrics, {"trees": 0, "safety": 0, "mobility": 0, "budget": 0}
            )

    def test_scenario_insight_updates_priority_and_recommendation(self) -> None:
        metrics = SampleDataProvider().load_metrics()
        selected = ["Vila Mariana", "Perdizes"]
        greenery_weights = {"trees": 100, "safety": 0, "mobility": 0, "budget": 0}
        safety_weights = {"trees": 0, "safety": 100, "mobility": 0, "budget": 0}

        greenery = build_scenario_insight(
            score_neighborhoods(metrics, greenery_weights),
            greenery_weights,
            selected,
        )
        safety = build_scenario_insight(
            score_neighborhoods(metrics, safety_weights),
            safety_weights,
            selected,
        )

        self.assertEqual(greenery.dominant_priority, "Arborização")
        self.assertEqual(greenery.recommended_name, "Vila Mariana")
        self.assertEqual(safety.dominant_priority, "Segurança")
        self.assertEqual(safety.recommended_name, "Perdizes")
        self.assertNotEqual(greenery.leader_name, safety.leader_name)

    def test_scenario_insight_explains_when_all_priorities_are_disabled(self) -> None:
        metrics = SampleDataProvider().load_metrics()
        weights = {"trees": 0, "safety": 0, "mobility": 0, "budget": 0}
        scored = score_neighborhoods(
            metrics, {"trees": 70, "safety": 70, "mobility": 60, "budget": 45}
        )

        insight = build_scenario_insight(scored, weights)

        self.assertIsNone(insight.dominant_priority)
        self.assertIsNone(insight.recommended_name)
        self.assertGreaterEqual(insight.leader_score, 0)


if __name__ == "__main__":
    unittest.main()
