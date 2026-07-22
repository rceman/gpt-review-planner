from __future__ import annotations


def calculate_damage(base_damage: int, armor: int, multiplier_bps: int) -> int:
    scaled = base_damage * multiplier_bps // 10_000
    return max(0, scaled - armor)
