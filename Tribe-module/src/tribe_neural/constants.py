"""Fixed constants for the neural processing pipeline."""

TR_DURATION: float = 1.5  # seconds per fMRI timepoint

ROI_LABELS: dict[str, str] = {
    "fear_salience": "threat and fear response",
    "reward_limbic": "reward and opportunity detection",
    "deliberation": "analytical thinking and rational control",
    "social_default": "awareness of others and social pressure",
    "action_motor": "urge to act (motor readiness)",
    "attention": "uncertainty and vigilance",
}

PAIR_LABELS: dict[str, str] = {
    "fear_social": "fear \u2194 social awareness",
    "fear_deliberation": "fear \u2194 analytical thinking",
    "fear_reward": "fear \u2194 reward detection",
    "reward_delib": "reward \u2194 analytical thinking",
    "reward_social": "reward \u2194 social awareness",
    "action_fear": "action urge \u2194 fear",
    "action_reward": "action urge \u2194 reward",
}

PAIRS: dict[str, tuple[str, str]] = {
    "fear_social": ("fear_salience", "social_default"),
    "fear_deliberation": ("fear_salience", "deliberation"),
    "fear_reward": ("fear_salience", "reward_limbic"),
    "reward_delib": ("reward_limbic", "deliberation"),
    "reward_social": ("reward_limbic", "social_default"),
    "action_fear": ("action_motor", "fear_salience"),
    "action_reward": ("action_motor", "reward_limbic"),
}

# Maps ROI name -> (Schaefer network substring, NiMARE term)
NETWORK_KEYS: dict[str, tuple[str, str]] = {
    "fear_salience": ("_SalVentAttn_", "fear"),
    "deliberation": ("_Cont_", "conflict"),
    "social_default": ("_Default_", "social"),
    "reward_limbic": ("_Limbic_", "reward"),
    "attention": ("_DorsAttn_", "uncertainty"),
    "action_motor": ("_SomMot_", "motor"),
}

# NiMARE weight generation terms (includes 'memory' for future use)
NIMARE_TERMS: list[str] = [
    "fear", "reward", "uncertainty", "conflict", "social", "motor", "memory",
]

# Composite score coefficients
# Composite score coefficients
VALENCE_WEIGHTS = {
    "reward_limbic_auc": 0.25,
    "reward_limbic_peak": 0.15,
    "fear_salience_auc": -0.20,
    "fear_salience_peak": -0.15,
    "deliberation_mean": 0.10,
    "attention_auc": -0.15,
}

AROUSAL_WEIGHTS = {
    "fear_salience_auc": 0.20,
    "reward_limbic_auc": 0.20,
    "fear_salience_peak": 0.20,
    "social_default_auc": 0.15,
    "attention_auc": 0.15,
    "action_motor_peak": 0.10,
}

NUM_VERTICES: int = 20_484
VERTICES_PER_HEMISPHERE: int = 10_242
