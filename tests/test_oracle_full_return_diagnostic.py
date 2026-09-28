import numpy as np

from scripts.diagnose_oracle_full_returns import translate_window


def test_full_return_translation_preserves_sources_and_drops_only_old_near_points():
    def item(frame, displacement):
        return {"frame": frame, "displacement": displacement,
                "xyz": np.array([[42, 2, 3], [45, 4, 5]], np.float32),
                "intensity": np.array([1, 2]), "target": np.array([True, False]),
                "all_source": np.array([True, False]), "strict": np.array([False, True]),
                "rail": np.array([False, True])}
    history = [item(10, 0), item(11, 3)]
    union = translate_window(history, 3, 40)
    assert union["xyz"].tolist() == [[42, 4, 5], [42, 2, 3], [45, 4, 5]]
    assert union["origins"].tolist() == [10, 11, 11]
    assert union["target"].tolist() == [False, True, False]
    assert union["strict"].tolist() == [True, False, True]
    # Original point identities and coordinates are retained for other windows.
    assert history[0]["xyz"][0].tolist() == [42, 2, 3]
