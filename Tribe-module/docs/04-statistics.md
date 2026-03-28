# Step 3: Summary Statistics (11 per ROI)

Each ROI timeseries (~15-25 numbers) is reduced to 11 interpretable features.

## The 11 Statistics

| Stat | Type | Description |
|---|---|---|
| `peak` | float | Maximum activation value |
| `mean` | float | Average activation across all TRs |
| `auc` | float | Area under the curve (positive values only, via trapezoidal integration) |
| `onset_tr` | int | First TR where activation exceeds threshold (max of std, 0.3) |
| `time_to_peak` | int | TR index of maximum activation |
| `rise_time` | int | TRs from onset to peak (`time_to_peak - onset_tr`) |
| `rise_slope` | float | Rate of rise (`(peak - value_at_onset) / rise_time`) |
| `fwhm` | int | Full width at half maximum (TRs where activation >= peak/2) |
| `sustained` | bool | Whether mean of last 3 TRs > 0.5 * threshold |
| `trajectory` | str | `'rising'`, `'falling'`, or `'stable'` (compares first vs second half means) |
| `cv` | float | Coefficient of variation (`std / (|mean| + 1e-6)`) |
| `decay_slope` | float | Exponential decay rate post-peak (log-linear fit) |

## Implementation

```python
def extract_stats(ts):
    n=len(ts); peak=float(np.max(ts)); mean=float(np.mean(ts)); std=np.std(ts)
    threshold=max(std,0.3)
    above=np.where(ts>threshold)[0]
    onset=int(above[0]) if len(above)>0 else n
    ttp=int(np.argmax(ts)); rt=max(0,ttp-onset)
    auc=float(np.trapz(np.maximum(ts,0)))
    hm=peak/2; ah=ts>=hm
    fwhm=int(np.where(ah)[0][-1]-np.where(ah)[0][0]+1) if ah.any() else 0
    sustained=bool(np.mean(ts[-3:])>0.5*threshold) if n>=3 else False
    if n>=4:
        fh,sh=np.mean(ts[:n//2]),np.mean(ts[n//2:])
        trajectory='rising' if sh>fh+0.3*std else 'falling' if sh<fh-0.3*std else 'stable'
    else: trajectory='stable'
    rise_slope=float((peak-ts[onset])/rt) if rt>0 else float(peak)
    cv=float(std/(abs(mean)+1e-6))
    pp=ts[ttp:]
    ds=float(np.polyfit(np.arange(len(pp)),np.log(np.maximum(pp,0.01)),1)[0]) if len(pp)>2 and np.mean(pp)>0.01 else 0.0
    return {'peak':peak,'mean':mean,'auc':auc,'onset_tr':onset,'time_to_peak':ttp,
            'rise_time':rt,'rise_slope':rise_slope,'fwhm':fwhm,'sustained':sustained,
            'trajectory':trajectory,'cv':cv,'decay_slope':ds}
```

## Output
Dict mapping 6 ROI names to dicts of 11 values each. **66 numbers total** describing the full spatiotemporal profile of the neural response.
