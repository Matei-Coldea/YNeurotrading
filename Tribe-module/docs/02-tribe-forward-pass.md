# Step 1: TRIBE v2 Forward Pass

## What It Does
TRIBE v2 takes text and predicts cortical surface activation. Internally it:
1. Converts text to speech via TTS
2. Runs forced alignment for word-level timings
3. Extracts LLaMA 3.2 text embeddings and Wav2Vec-BERT audio features
4. Fuses them through a learned Transformer
5. Projects to 20,484 cortical surface vertices

## Input
- TRIBE v2 expects a **file path** (not a string directly)
- Write text to a temp file, pass the path

## Output
- `numpy` array, shape `(n_TRs, 20484)`
- Rows = fMRI timepoints (~1.5-2 sec each)
- Columns 0-10,241 = left hemisphere vertices
- Columns 10,242-20,483 = right hemisphere vertices
- Values = predicted BOLD signal amplitudes, z-scored
  - `0.0` = baseline
  - `1.5+` = strong activation

## Performance
- 2-5 seconds on GPU
- This is the bottleneck of the entire pipeline

## Implementation

```python
import tempfile, os
import numpy as np
from tribev2 import TribeModel

token = os.environ.get('HF_TOKEN')
model = TribeModel.from_pretrained('facebook/tribev2', cache_folder='./cache', token=token)

def run_tribe(text: str) -> np.ndarray:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(text)
        path = f.name
    try:
        df = model.get_events_dataframe(text_path=path)
        preds, _ = model.predict(events=df)
        return preds  # shape (n_TRs, 20484)
    finally:
        os.unlink(path)
```

## Notes
- Model weights downloaded from Hugging Face — requires `HF_TOKEN` environment variable set with your Hugging Face access token
- No interactive `huggingface-cli login` needed; the token is passed directly via `token=` parameter
- The model should be loaded once at module init, not per-call
