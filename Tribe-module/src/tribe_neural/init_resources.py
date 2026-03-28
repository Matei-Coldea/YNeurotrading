"""Load all heavy resources once at startup."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from tribe_neural.constants import NETWORK_KEYS, NUM_VERTICES

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("TRIBE_DATA_DIR", "./data"))


@dataclass
class Resources:
    """Container for all pre-loaded pipeline resources."""

    model: object  # TribeModel (typed as object to avoid import at module level)
    masks: dict[str, np.ndarray] = field(default_factory=dict)
    weight_maps: dict[str, np.ndarray] = field(default_factory=dict)
    signatures: dict[str, np.ndarray | None] = field(default_factory=dict)


def _build_schaefer_masks() -> dict[str, np.ndarray]:
    """Compute 6 boolean masks from the Schaefer 400-parcel atlas."""
    from nilearn import datasets, surface

    schaefer = datasets.fetch_atlas_surf_schaefer(n_parcels=400)
    sch_lh = surface.load_surf_data(schaefer["map_left"])
    sch_rh = surface.load_surf_data(schaefer["map_right"])
    sch_full = np.concatenate([sch_lh, sch_rh])
    sch_names = schaefer["labels"]

    def make_network_mask(key: str) -> np.ndarray:
        mask = np.zeros(NUM_VERTICES, dtype=bool)
        for idx, name in enumerate(sch_names):
            if key in str(name):
                mask |= sch_full == idx
        return mask

    masks = {}
    for roi_name, (network_key, _) in NETWORK_KEYS.items():
        masks[roi_name] = make_network_mask(network_key)
        logger.info(
            "Schaefer mask %s: %d vertices", roi_name, masks[roi_name].sum()
        )

    return masks


def _load_weight_maps(data_dir: Path) -> dict[str, np.ndarray]:
    """Load pre-generated NiMARE weight maps from .npz file."""
    path = data_dir / "neurosynth_weights.npz"
    if not path.exists():
        logger.warning("NiMARE weights not found at %s — using empty weights", path)
        return {}

    data = np.load(str(path))
    weight_maps = {key: data[key] for key in data.files}
    logger.info("Loaded NiMARE weights for terms: %s", list(weight_maps.keys()))
    return weight_maps


def _load_signatures(data_dir: Path) -> dict[str, np.ndarray | None]:
    """Load VIFS/PINES surface projections if validated."""
    sigs: dict[str, np.ndarray | None] = {"vifs": None, "pines": None}

    validation_failed = (data_dir / "vifs_validation_failed").exists()
    if validation_failed:
        logger.warning("VIFS validation failed marker found — signatures disabled")
        return sigs

    for name in ("vifs", "pines"):
        path = data_dir / f"{name}_surface.npy"
        if path.exists():
            sigs[name] = np.load(str(path))
            logger.info("Loaded %s signature: shape %s", name, sigs[name].shape)
        else:
            logger.info("Signature %s not found at %s — skipping", name, path)

    return sigs


def load_resources() -> Resources:
    """Load all resources needed by the pipeline.

    Loads TRIBE v2 model (requires HF_TOKEN env var), Schaefer masks,
    NiMARE weight maps, and optionally VIFS/PINES signatures.
    """
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("HF_TOKEN environment variable is not set")

    logger.info("Loading TRIBE v2 model...")
    from tribev2 import TribeModel

    model = TribeModel.from_pretrained(
        "facebook/tribev2", cache_folder=str(DATA_DIR / "cache"), token=hf_token
    )
    logger.info("TRIBE v2 model loaded")

    logger.info("Building Schaefer masks...")
    masks = _build_schaefer_masks()

    logger.info("Loading NiMARE weight maps...")
    weight_maps = _load_weight_maps(DATA_DIR)

    logger.info("Loading signatures...")
    signatures = _load_signatures(DATA_DIR)

    return Resources(
        model=model,
        masks=masks,
        weight_maps=weight_maps,
        signatures=signatures,
    )
