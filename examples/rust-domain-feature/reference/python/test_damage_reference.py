from __future__ import annotations

import random
import unittest

from damage_reference import calculate_damage


class DamageReferenceTest(unittest.TestCase):
    def test_known_cases(self) -> None:
        self.assertEqual(calculate_damage(10, 50, 10_000), 0)
        self.assertEqual(calculate_damage(100, 10, 15_000), 140)

    def test_damage_is_never_negative(self) -> None:
        rng = random.Random(12345)

        for _ in range(10_000):
            result = calculate_damage(
                base_damage=rng.randint(0, 10_000),
                armor=rng.randint(0, 10_000),
                multiplier_bps=rng.randint(0, 50_000),
            )
            self.assertGreaterEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
