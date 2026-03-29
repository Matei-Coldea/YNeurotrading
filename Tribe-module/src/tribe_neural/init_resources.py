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
    whisperx_model: object = None  # Warm whisperx ASR model
    whisperx_align_model: object = None  # Warm whisperx alignment model
    whisperx_align_metadata: dict = field(default_factory=dict)


def _build_schaefer_masks() -> dict[str, np.ndarray]:
    """Compute 6 boolean masks from the Schaefer 400-parcel atlas.

    Projects the volumetric atlas to fsaverage5 surface (left + right)
    since the surface-native fetcher was removed in nilearn 0.13.
    """
    from nilearn import datasets
    from nilearn.surface import vol_to_surf

    nilearn_dir = os.environ.get("NILEARN_DATA_DIR", str(DATA_DIR / "nilearn"))
    schaefer = datasets.fetch_atlas_schaefer_2018(
        n_rois=400, resolution_mm=1, data_dir=nilearn_dir,
    )
    fsav = datasets.fetch_surf_fsaverage("fsaverage5", data_dir=nilearn_dir)

    sch_lh = np.rint(vol_to_surf(schaefer["maps"], fsav["pial_left"])).astype(int)
    sch_rh = np.rint(vol_to_surf(schaefer["maps"], fsav["pial_right"])).astype(int)
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


def _load_whisperx() -> tuple:
    """Load whisperx ASR and alignment models once into GPU memory."""
    import torch
    import whisperx

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "default"

    asr_model = whisperx.load_model(
        "large-v3", device=device, compute_type=compute_type, language="en",
    )
    align_model, align_metadata = whisperx.load_align_model(
        language_code="en", device=device,
        model_name="WAV2VEC2_ASR_LARGE_LV60K_960H",
    )
    return asr_model, align_model, align_metadata


def _patch_whisperx(asr_model: object, align_model: object, align_metadata: dict) -> None:
    """Monkey-patch ExtractWordsFromAudio to use warm whisperx models."""
    import torch
    import whisperx
    from tribev2.eventstransforms import ExtractWordsFromAudio

    device = "cuda" if torch.cuda.is_available() else "cpu"

    @staticmethod
    def _fast_transcribe(wav_filename, language):
        audio = whisperx.load_audio(str(wav_filename))
        result = asr_model.transcribe(audio, batch_size=16)

        aligned = whisperx.align(
            result["segments"], align_model, align_metadata,
            audio, device=device,
        )

        words = []
        for i, segment in enumerate(aligned["segments"]):
            sentence = segment["text"].replace('"', "")
            for word in segment.get("words", []):
                if "start" not in word:
                    continue
                words.append({
                    "text": word["word"].replace('"', ""),
                    "start": word["start"],
                    "duration": word["end"] - word["start"],
                    "sequence_id": i,
                    "sentence": sentence,
                })

        import pandas as pd
        return pd.DataFrame(words)

    ExtractWordsFromAudio._get_transcript_from_audio = _fast_transcribe
    logger.info("ExtractWordsFromAudio patched to use in-process whisperx")


def _enable_cuda_optimizations() -> None:
    """Enable CUDA performance flags for inference."""
    import torch

    if not torch.cuda.is_available():
        return

    # TF32: ~2-3x faster matmuls with negligible precision loss
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    # cuDNN benchmark: auto-tune convolution algorithms for this GPU
    torch.backends.cudnn.benchmark = True

    logger.info(
        "CUDA optimizations enabled: TF32 matmul=%s, cuDNN benchmark=%s",
        torch.backends.cuda.matmul.allow_tf32,
        torch.backends.cudnn.benchmark,
    )


def _optimize_tribe_model(model_wrapper: object) -> None:
    """Enable bf16 autocast for TRIBE inference."""
    import torch

    model = model_wrapper._model
    if model is None:
        return

    # Wrap the forward method with bf16 autocast so inputs are automatically
    # cast — avoids dtype mismatch between fp32 data loader and bf16 model.
    original_forward = model.forward

    @torch.amp.autocast("cuda", dtype=torch.float16)
    def autocast_forward(*args, **kwargs):
        return original_forward(*args, **kwargs)

    model.forward = autocast_forward
    logger.info("TRIBE model forward wrapped with fp16 autocast")


def _patch_tts() -> None:
    """Replace gTTS (network call to Google) with edge-tts (faster)."""
    import asyncio

    import edge_tts
    from tribev2.demo_utils import TextToEvents, get_audio_and_text_events

    def get_events(self):
        import pandas as pd

        audio_path = Path(self.infra.uid_folder(create=True)) / "audio.mp3"

        async def _generate():
            communicate = edge_tts.Communicate(self.text, "en-US-AriaNeural")
            await communicate.save(str(audio_path))

        # Run async edge-tts in a sync context
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(lambda: asyncio.run(_generate())).result()
        else:
            asyncio.run(_generate())

        logger.info("Wrote TTS audio to %s (edge-tts)", audio_path)

        audio_event = {
            "type": "Audio",
            "filepath": str(audio_path),
            "start": 0,
            "timeline": "default",
            "subject": "default",
        }
        return get_audio_and_text_events(pd.DataFrame([audio_event]))

    # Replace the inner method inside the exca InfraMethod decorator
    prop = TextToEvents.__dict__["get_events"]
    prop.fget.method = get_events
    logger.info("TextToEvents patched to use edge-tts instead of gTTS")


def load_resources() -> Resources:
    """Load all resources needed by the pipeline.

    Loads TRIBE v2 model (requires HF_TOKEN env var), Schaefer masks,
    NiMARE weight maps, and optionally VIFS/PINES signatures.
    """
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("HF_TOKEN environment variable is not set")

    # Enable CUDA optimizations before loading any models
    _enable_cuda_optimizations()

    logger.info("Loading TRIBE v2 model...")
    from tribev2.demo_utils import TribeModel

    model = TribeModel.from_pretrained(
        "facebook/tribev2", cache_folder=str(DATA_DIR / "cache"),
    )
    logger.info("TRIBE v2 model loaded")

    # Optimize TRIBE model: bf16 + torch.compile
    _optimize_tribe_model(model)

    logger.info("Building Schaefer masks...")
    masks = _build_schaefer_masks()

    logger.info("Loading NiMARE weight maps...")
    weight_maps = _load_weight_maps(DATA_DIR)

    logger.info("Loading signatures...")
    signatures = _load_signatures(DATA_DIR)

    logger.info("Loading whisperx models (ASR + alignment)...")
    whisperx_model, align_model, align_metadata = _load_whisperx()
    logger.info("whisperx models loaded — monkey-patching ExtractWordsFromAudio")
    _patch_whisperx(whisperx_model, align_model, align_metadata)

    # Replace gTTS with edge-tts
    _patch_tts()

    return Resources(
        model=model,
        masks=masks,
        weight_maps=weight_maps,
        signatures=signatures,
        whisperx_model=whisperx_model,
        whisperx_align_model=align_model,
        whisperx_align_metadata=align_metadata,
    )
