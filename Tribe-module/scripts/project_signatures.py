"""One-time script: Download and project VIFS/PINES signatures to fsaverage5.

Downloads signature NIfTI files from Neurovault / GitHub, projects from MNI
volumetric space onto the fsaverage5 cortical surface, and saves as .npy.
"""

from __future__ import annotations

import argparse
import logging
import tempfile
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# VIFS is hosted on the CANlab GitHub repo, not Neurovault.
VIFS_URL = (
    "https://raw.githubusercontent.com/canlab/"
    "Neuroimaging_Pattern_Masks/master/"
    "Multivariate_signature_patterns/2021_Zhou_Subjective_Fear/VIFS.nii"
)

# PINES is Neurovault image 1696 (collection 306, Chang et al. 2015).
PINES_NEUROVAULT_ID = 1696


def project_to_surface(nifti_path: str) -> np.ndarray:
    """Project a volumetric NIfTI to fsaverage5 surface."""
    from nilearn import datasets as nid
    from nilearn.surface import vol_to_surf

    fsav = nid.fetch_surf_fsaverage("fsaverage5")
    w_lh = vol_to_surf(nifti_path, fsav["pial_left"])
    w_rh = vol_to_surf(nifti_path, fsav["pial_right"])
    return np.concatenate([w_lh, w_rh])


def _download_vifs(output_path: Path) -> None:
    """Download VIFS from CANlab GitHub and project to surface."""
    import urllib.request

    logger.info("Downloading VIFS from CANlab GitHub...")
    with tempfile.NamedTemporaryFile(suffix=".nii") as tmp:
        urllib.request.urlretrieve(VIFS_URL, tmp.name)
        logger.info("Projecting vifs to fsaverage5 surface...")
        surface_weights = project_to_surface(tmp.name)

    np.save(str(output_path), surface_weights)
    logger.info("Saved vifs: shape=%s, range=[%.2f, %.2f]",
                surface_weights.shape, surface_weights.min(), surface_weights.max())


def _download_pines(output_path: Path) -> None:
    """Download PINES from Neurovault and project to surface."""
    from nilearn.datasets import fetch_neurovault_ids

    logger.info("Downloading PINES from Neurovault (image %d)...", PINES_NEUROVAULT_ID)
    result = fetch_neurovault_ids(image_ids=[PINES_NEUROVAULT_ID])
    nifti_path = result["images"][0]

    logger.info("Projecting pines to fsaverage5 surface...")
    surface_weights = project_to_surface(nifti_path)

    np.save(str(output_path), surface_weights)
    logger.info("Saved pines: shape=%s, range=[%.2f, %.2f]",
                surface_weights.shape, surface_weights.min(), surface_weights.max())


def main(output_dir: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # VIFS
    vifs_path = out / "vifs_surface.npy"
    if vifs_path.exists():
        logger.info("vifs_surface.npy already exists — skipping")
    else:
        try:
            _download_vifs(vifs_path)
        except Exception:
            logger.exception("Failed to process vifs — skipping")

    # PINES
    pines_path = out / "pines_surface.npy"
    if pines_path.exists():
        logger.info("pines_surface.npy already exists — skipping")
    else:
        try:
            _download_pines(pines_path)
        except Exception:
            logger.exception("Failed to process pines — skipping")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and project VIFS/PINES signatures"
    )
    parser.add_argument("--output-dir", required=True, help="Output directory")
    args = parser.parse_args()
    main(args.output_dir)
