"""One-time script: Generate NiMARE meta-analytic weight maps.

Downloads Neurosynth database (~1GB), runs ALE meta-analysis for each
term, projects onto fsaverage5 surface, and saves as .npz.

Takes ~30 minutes on first run.
"""

from __future__ import annotations

import argparse
import logging

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

TERMS = ["fear", "reward", "uncertainty", "conflict", "social", "motor", "memory"]


def main(output_path: str, neurosynth_dir: str = "./neurosynth_data") -> None:
    from nilearn import datasets as nid
    from nilearn.surface import vol_to_surf
    from nimare.dataset import Dataset
    from nimare.extract import fetch_neurosynth
    from nimare.meta.cbma.ale import ALE

    logger.info("Fetching Neurosynth database to %s ...", neurosynth_dir)
    files = fetch_neurosynth(data_dir=neurosynth_dir)
    dset = Dataset.load(files[0])

    fsav = nid.fetch_surf_fsaverage("fsaverage5")
    pial = {"left": fsav["pial_left"], "right": fsav["pial_right"]}

    weight_maps: dict[str, np.ndarray] = {}

    for term in TERMS:
        logger.info("Processing term: %s", term)
        ids = dset.get_studies_by_label(
            f"terms_abstract_tfidf__{term}", label_threshold=0.001
        )
        if len(ids) == 0:
            logger.warning("No studies found for term '%s' — skipping", term)
            continue

        logger.info("  Found %d studies, running ALE...", len(ids))
        results = ALE().fit(dset.slice(ids))
        z_map = results.get_map("z")

        w_lh = vol_to_surf(z_map, pial["left"])
        w_rh = vol_to_surf(z_map, pial["right"])
        weight_maps[term] = np.maximum(np.concatenate([w_lh, w_rh]), 0)
        logger.info("  %s: max=%.2f, nonzero=%d",
                     term, weight_maps[term].max(),
                     (weight_maps[term] > 0).sum())

    np.savez(output_path, **weight_maps)
    logger.info("Saved weight maps to %s", output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate NiMARE weight maps")
    parser.add_argument("--output", required=True, help="Output .npz path")
    parser.add_argument("--neurosynth-dir", default="./neurosynth_data",
                        help="Directory for Neurosynth data cache")
    args = parser.parse_args()
    main(args.output, args.neurosynth_dir)
