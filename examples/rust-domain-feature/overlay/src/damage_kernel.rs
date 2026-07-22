#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DamageInput {
    pub base_damage: i32,
    pub armor: i32,
    pub multiplier_bps: i32,
}

pub fn calculate_damage(input: DamageInput) -> i32 {
    let scaled = input
        .base_damage
        .saturating_mul(input.multiplier_bps)
        / 10_000;

    scaled.saturating_sub(input.armor).max(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn armor_cannot_make_damage_negative() {
        assert_eq!(
            calculate_damage(DamageInput {
                base_damage: 10,
                armor: 50,
                multiplier_bps: 10_000,
            }),
            0
        );
    }

    #[test]
    fn multiplier_uses_basis_points() {
        assert_eq!(
            calculate_damage(DamageInput {
                base_damage: 100,
                armor: 10,
                multiplier_bps: 15_000,
            }),
            140
        );
    }
}
