# Step 2: ROI Timeseries Extraction

Reduces 20,484 cortical vertices to 6 meaningful timeseries using three layers that each fix a specific accuracy problem.

## The 6 ROI Categories

| ROI Name | Yeo Network | NiMARE Term | Signature |
|---|---|---|---|
| `fear_salience` | SalVentAttn | `fear` | VIFS (if validated) |
| `deliberation` | Cont (Control) | `conflict` | None |
| `social_default` | Default | `social` | None |
| `reward_limbic` | Limbic | `reward` | None |
| `attention` | DorsAttn | `uncertainty` | None |
| `action_motor` | SomMot | `motor` | None |

## Layer 1: Schaefer Functional Parcellation (nilearn)

**Problem it fixes:** Anatomical atlases (e.g., Destrieux) mix functionally different regions. The superior frontal gyrus contains dlPFC, SMA, and mPFC all together — grouping them contaminates signals.

**What Schaefer does:** Divides the cortex into 400 parcels based on resting-state functional connectivity. Each parcel maps to one of 7 Yeo canonical networks. Already defined on fsaverage5 — no coordinate conversion needed.

```python
from nilearn import datasets, surface

schaefer = datasets.fetch_atlas_surf_schaefer(n_parcels=400)
sch_lh = surface.load_surf_data(schaefer['map_left'])   # (10242,)
sch_rh = surface.load_surf_data(schaefer['map_right'])  # (10242,)
sch_full = np.concatenate([sch_lh, sch_rh])              # (20484,)
sch_names = schaefer['labels']

def make_network_mask(key):
    mask = np.zeros(20484, dtype=bool)
    for idx, name in enumerate(sch_names):
        if key in str(name):
            mask |= (sch_full == idx)
    return mask

masks = {
    'fear_salience':  make_network_mask('_SalVentAttn_'),
    'deliberation':   make_network_mask('_Cont_'),
    'social_default': make_network_mask('_Default_'),
    'reward_limbic':  make_network_mask('_Limbic_'),
    'attention':      make_network_mask('_DorsAttn_'),
    'action_motor':   make_network_mask('_SomMot_'),
}
```

## Layer 2: NiMARE Meta-Analytic Weights

**Problem it fixes:** Schaefer masks are binary — every vertex counts equally. A vertex at the core of the anterior insula counts the same as a peripheral vertex that only sometimes activates.

**What NiMARE does:** Queries the Neurosynth database. Each voxel gets a z-score from meta-analysis across 14,000+ studies. High z-score = strong evidence. Projected onto fsaverage5 via `vol_to_surf`. Used as continuous weights instead of binary mask.

```python
# === RUN ONCE, SAVE TO DISK ===
from nimare.extract import fetch_neurosynth
from nimare.dataset import Dataset
from nimare.meta.cbma.ale import ALE
from nilearn.surface import vol_to_surf
from nilearn import datasets as nid

files = fetch_neurosynth(data_dir='./neurosynth_data')  # ~1GB download
dset = Dataset.load(files[0])
fsav = nid.fetch_surf_fsaverage('fsaverage5')
pial = {'left': fsav['pial_left'], 'right': fsav['pial_right']}

def neurosynth_weights(dset, term, pial):
    ids = dset.get_studies_by_label(f'terms_abstract_tfidf__{term}', label_threshold=0.001)
    results = ALE().fit(dset.slice(ids))
    z_map = results.get_map('z')
    w_lh = vol_to_surf(z_map, pial['left'])
    w_rh = vol_to_surf(z_map, pial['right'])
    return np.maximum(np.concatenate([w_lh, w_rh]), 0)  # (20484,), positive only

weight_maps = {}
for term in ['fear','reward','uncertainty','conflict','social','motor','memory']:
    weight_maps[term] = neurosynth_weights(dset, term, pial)
np.savez('./neurosynth_weights.npz', **weight_maps)  # cache
```

**Space projection concern:** Neurosynth maps are in MNI volumetric space. `vol_to_surf` projects by sampling at each vertex's 3D coordinate. Lossy in tightly folded sulci. Major peaks (amygdala, anterior insula, ACC) survive with approximately correct magnitudes.

**Performance:** Weight generation takes ~30 min first run, then cached to `.npz`.

## Layer 3: nltools Pre-Trained Signatures

**Problem it fixes:** Even weighted averaging collapses spatial patterns into one number. Two different brain states can produce the same weighted average. Trained multivariate signatures capture the full distributed pattern.

**Key signatures:**
- **VIFS** (Visually Induced Fear Signature) — predicts subjective fear
- **PINES** (Picture Induced Negative Emotion Signature) — predicts negative emotional intensity

Both trained on real fMRI with behavioral labels, validated across multiple cohorts.

```python
from nltools.data import Brain_Data

vifs_vol = Brain_Data('path/to/vifs_signature.nii.gz')
vifs_nii = vifs_vol.to_nifti()
vifs_surf = np.concatenate([
    vol_to_surf(vifs_nii, fsav['pial_left']),
    vol_to_surf(vifs_nii, fsav['pial_right'])
])  # (20484,) signed weights

pines_surf = ...  # same process
```

**Transfer validity concern:** VIFS/PINES were trained on real fMRI, not TRIBE v2 predictions. Before using, run validation: process 5 known stimuli (fear, neutral, positive, uncertain, surprise). If VIFS gives higher scores for the fear stimulus than neutral, the transfer works. If not, fall back to NiMARE weighted averaging. This takes 5 minutes.

## Combining All Three Layers

```python
def extract_timeseries(preds, schaefer_mask, nimare_weights, signature_weights=None):
    n_trs = preds.shape[0]
    result = {}

    # Layers 1+2: Schaefer mask * NiMARE weights -> weighted average
    combined = nimare_weights * schaefer_mask  # zero out non-network vertices
    w_sum = combined.sum()
    if w_sum > 0:
        result['weighted'] = np.array([np.dot(preds[t,:], combined)/w_sum for t in range(n_trs)])
    else:
        result['weighted'] = preds[:, schaefer_mask].mean(axis=1)  # fallback

    # Layer 3: signature dot product
    if signature_weights is not None:
        result['signature'] = np.array([np.dot(preds[t,:], signature_weights) for t in range(n_trs)])

    return result

def extract_all(preds, masks, weights, sigs):
    roi_ts = {}
    mapping = {
        'fear_salience':  ('fear', sigs.get('vifs')),
        'reward_limbic':  ('reward', None),
        'deliberation':   ('conflict', None),
        'social_default': ('social', None),
        'attention':      ('uncertainty', None),
        'action_motor':   ('motor', None),
    }
    for roi_name, (weight_key, sig) in mapping.items():
        w = weights.get(weight_key, masks[roi_name].astype(float))
        ts = extract_timeseries(preds, masks[roi_name], w, sig)
        roi_ts[roi_name] = ts.get('signature', ts['weighted'])
    return roi_ts
```

## Output
Dict mapping 6 category names to numpy arrays of shape `(n_TRs,)`. Each array is one timeseries: the predicted functional activation of that brain system at each timepoint.
