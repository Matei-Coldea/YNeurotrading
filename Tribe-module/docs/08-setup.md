# Setup & Dependencies

## Core Dependencies

```bash
# TRIBE v2 (Facebook Research)
git clone https://github.com/facebookresearch/tribev2.git
cd tribev2 && pip install -e '.[plotting]'

# Neuroimaging tools
pip install nilearn nibabel scipy
```

## Authentication

Set your Hugging Face token as an environment variable. The code reads it via `os.environ.get('HF_TOKEN')` and passes it directly to `TribeModel.from_pretrained()` — no interactive `huggingface-cli login` needed.

```bash
export HF_TOKEN=hf_YOUR_TOKEN_HERE
```

You must first accept the model terms on the `facebook/tribev2` Hugging Face page before the token will work.

## Layer 2: NiMARE (Meta-Analytic Weights)

```bash
pip install nimare
```

- First run downloads ~1GB Neurosynth database
- Weight generation takes ~30 min, then cached to `neurosynth_weights.npz`

## Layer 3: nltools (Pre-Trained Signatures)

```bash
pip install nltools
```

- Download VIFS and PINES signatures from Neurovault
- **Must run 5-stimulus validation before using** (takes ~5 min):
  - Process 5 known stimuli: fear, neutral, positive, uncertain, surprise
  - If VIFS scores fear > neutral, the transfer works
  - If not, fall back to NiMARE weighted averaging only

## One-Time Data Generation

These steps run once and cache results to disk:

1. **Neurosynth weights** (~30 min): generates `neurosynth_weights.npz` with z-score maps for 7 terms (fear, reward, uncertainty, conflict, social, motor, memory)
2. **Signature projection** (~5 min): projects VIFS/PINES from volumetric to fsaverage5 surface
3. **Signature validation** (~5 min): 5-stimulus test to confirm transfer validity

## Runtime Requirements

- **GPU** recommended for TRIBE v2 inference (2-5 sec/call)
- CPU works but will be significantly slower
- Steps 2-6 of the pipeline are CPU-only and fast (<30ms total)

## File Structure (after setup)

```
./cache/                     # TRIBE v2 model weights (Hugging Face)
./neurosynth_data/           # Neurosynth database (~1GB)
./neurosynth_weights.npz     # Cached meta-analytic weight maps
```
