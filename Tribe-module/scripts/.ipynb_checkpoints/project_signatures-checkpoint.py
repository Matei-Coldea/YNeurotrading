"""One-time script: Download and project VIFS/PINES signatures to fsaverage5.

Downloads signature NIfTI files from Neurovault, projects from MNI
volumetric space onto the fsaverage5 cortical surface, and saves as .npy.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Neurovault collection IDs for the signatures
SIGNATURES = {
    "vifs": {
        "description": "Visually Induced Fear Signature",
        "neurovault_id": 3604,  # Collection ID — verify before use
    },
    "pines": {
        "description": "Picture Induced Negative Emotion Signature",
        "neurovault_id": 3198,  # Collection ID — verify before use
    },
}


def project_to_surface(nifti_path: str) -> np.ndarray:
    """Project a volumetric NIfTI to fsaverage5 surface."""
    from nilearn import datasets as nid
    from nilearn.surface import vol_to_surf

    fsav = nid.fetch_surf_fsaverage("fsaverage5")
    w_lh = vol_to_surf(nifti_path, fsav["pial_left"])
    w_rh = vol_to_surf(nifti_path, fsav["pial_right"])
    return np.concatenate([w_lh, w_rh])


def main(output_dir: str) -> None:
    from nltools.data import Brain_Data

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for name, info in SIGNATURES.items():
        output_path = out / f"{name}_surface.npy"
        if output_path.exists():
            logger.info("%s already exists — skipping", output_path)
            continue

        logger.info("Loading %s (%s)...", name, info["description"])
        try:
            # nltools can fetch from Neurovault by collection ID
            brain_data = Brain_Data(info["neurovault_id"])
            nifti = brain_data.to_nifti()

            logger.info("Projecting %s to fsaverage5 surface...", name)
            surface_weights = project_to_surface(nifti)

            np.save(str(output_path), surface_weights)
            logger.info("Saved %s: shape=%s, range=[%.2f, %.2f]",
                         name, surface_weights.shape,
                         surface_weights.min(), surface_weights.max())
        except Exception:
            logger.exception("Failed to process %s — skipping", name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and project VIFS/PINES signatures"
    )
    parser.add_argument("--output-dir", required=True, help="Output directory")
    args = parser.parse_args()
    main(args.output_dir)
