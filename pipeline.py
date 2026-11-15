import json, os, datetime as dt
import numpy as np

OUT = "web/data"
STEPS = list(range(6, 145, 6))   # 24 six-hourly steps
LAT = (38, 6)
LON = (66, 99)
MODELS = ["ifs", "aifs-single"]

def client(m):
    from ecmwf.opendata import Client
    return Client(source="ecmwf", model=m, resol="0p25")

def newest_common_run():
    runs = []
    for m in MODELS:
        try:
            runs.append(client(m).latest(type="fc", param="tp", step=144))
        except Exception as e:
            print("latest() failed for", m, repr(e))
    return min(runs) if runs else None

def fetch(m, run):
    import xarray as xr
    f = f"{m}.grib2"
    client(m).retrieve(date=run.strftime("%Y%m%d"), time=run.hour, type="fc",
                       param="tp", step=STEPS, target=f)
    ds = xr.open_dataset(f, engine="cfgrib")
    da = ds["tp"].transpose("step", "latitude", "longitude").sortby("latitude", ascending=False)
    return da.sel(latitude=slice(*LAT), longitude=slice(*LON))

def regrid_to(da, ref):
    same = (da.shape[1:] == ref.shape[1:]
            and np.allclose(da.latitude, ref.latitude)
            and np.allclose(da.longitude, ref.longitude))
    if same:
        return da
    print("Regridding to common grid (linear interpolation)")
    return da.interp(latitude=ref.latitude, longitude=ref.longitude, method="linear")

def accum_to_rain(tp):
    tp = np.asarray(tp, dtype="float64")
    assert np.isfinite(tp).all(), "NaN/inf in tp"
    d = np.diff(tp, axis=0, prepend=0)
    # GRIB packing can make a flat IFS total fall by one quantization increment
    # (~0.244 mm). Allow up to 0.5 mm of packing noise; larger drops still fail.
    assert d.min() > -5e-4, f"accumulation not monotonic (min diff {d.min():.6f} m)"
    return np.clip(d, 0, None) * 1000

def precipitation_metres(values, units):
    """Normalize ECMWF IFS (m) and AIFS-Single (kg m**-2) totals to metres."""
    values = np.asarray(values, dtype="float64")
    normalized = units.strip().lower().replace(" ", "")
    if normalized in {"m", "metre", "meter", "metres", "meters"}:
        return values
    if normalized in {"kgm**-2", "kgm-2", "kg/m^2", "kgm^-2"}:
        # 1 kg m-2 of liquid water is 1 mm, or 0.001 m.
        return values / 1000
    raise AssertionError(f"unexpected total precipitation units: {units!r}")

def to_rain(da, run):
    hours = (da["step"].values / np.timedelta64(1, "h")).astype(int).tolist()
    assert hours == STEPS, f"unexpected steps {hours}"
    expected = np.array([np.datetime64(run) + np.timedelta64(h, "h") for h in STEPS])
    assert (da["valid_time"].values == expected).all(), "valid_time does not match run + step"
    return accum_to_rain(precipitation_metres(da.values, da.attrs.get("units", "m")))

def try_run(run, models):
    out, ref = {}, None
    for m in models:
        try:
            da = fetch(m, run)
            if ref is None:
                ref = da
            da = regrid_to(da, ref)
            out[m] = to_rain(da, run)
            print(m, run, "OK max mm:", round(float(out[m].max()), 1), "mean:", round(float(out[m].mean()), 3))
        except Exception as e:
            print("FAILED", m, run, repr(e))
    return out, ref

def pick_data():
    start = newest_common_run()
    if start is None:
        return None
    partial = None
    for k in range(4):
        run = start - dt.timedelta(hours=6 * k)
        out, ref = try_run(run, MODELS)
        if len(out) == len(MODELS):
            return run, out, ref
        if out and partial is None:
            partial = (run, out, ref)
    return partial

def synthetic(seed):
    rng = np.random.default_rng(seed)
    ny, nx = int((LAT[0] - LAT[1]) * 4) + 1, int((LON[1] - LON[0]) * 4) + 1
    yy, xx = np.mgrid[0:ny, 0:nx]
    frames = []
    for t in range(24):
        f = np.zeros((ny, nx))
        for _ in range(6):
            cy = (rng.uniform(.3, .8) * ny + t * .4) % ny
            cx = (rng.uniform(.2, .9) * nx + t * .8) % nx
            f += rng.uniform(5, 40) * np.exp(-(((yy - cy) / 12) ** 2 + ((xx - cx) / 16) ** 2))
        frames.append(np.clip(f - 1, 0, None))
    return np.array(frames)

def save(m, rain):
    data = [np.rint(r * 10).astype(int).flatten().tolist() for r in rain]
    with open(f"{OUT}/{m}.json", "w") as fh:
        json.dump({"scale": 10, "data": data}, fh)

def main():
    os.makedirs(OUT, exist_ok=True)
    picked = pick_data()
    if picked:
        run, results, ref = picked
        times = [str(t)[:19] + "Z" for t in ref["valid_time"].values]
        meta = dict(run=run.strftime("%Y-%m-%d %H:00 UTC"), times=times,
                    lat=[float(ref.latitude[0]), float(ref.latitude[-1])],
                    lon=[float(ref.longitude[0]), float(ref.longitude[-1])],
                    ny=int(ref.shape[1]), nx=int(ref.shape[2]), models=list(results),
                    paired=len(results) == len(MODELS), synthetic=False,
                    provenance={m: {"synthetic": False, "source": "ECMWF Open Data (CC-BY-4.0)"} for m in results})
        for m, r in results.items():
            save(m, r)
    else:
        now = dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        times = [(now + dt.timedelta(hours=6 * (i + 1))).strftime("%Y-%m-%dT%H:%M:%SZ") for i in range(24)]
        meta = dict(run=now.strftime("%Y-%m-%d %H:00 UTC"), times=times, lat=[38.0, 6.0], lon=[66.0, 99.0],
                    ny=int((LAT[0] - LAT[1]) * 4) + 1, nx=int((LON[1] - LON[0]) * 4) + 1,
                    models=list(MODELS), paired=True, synthetic=True,
                    provenance={m: {"synthetic": True, "source": "SYNTHETIC SAMPLE DATA - NOT A FORECAST"} for m in MODELS})
        for i, m in enumerate(MODELS):
            save(m, synthetic(i + 1))
        print("!!! USING SYNTHETIC SAMPLE DATA. Run python pipeline.py on a machine with internet for real data. !!!")
    meta.update(generated_at=dt.datetime.utcnow().isoformat() + "Z",
                note="row-major, north to south, values = mm*10 per 6h")
    with open(f"{OUT}/manifest.json", "w") as fh:
        json.dump(meta, fh)
    for m in meta["models"]:
        with open(f"{OUT}/{m}.json") as fh:
            d = json.load(fh)["data"]
        assert len(d) == 24 and all(len(x) == meta["ny"] * meta["nx"] for x in d), "shape mismatch"
        assert max(max(x) for x in d) / 10 < 600, "implausible rainfall: units/differencing error"
    print("validation passed; models:", meta["models"], "paired:", meta["paired"], "synthetic:", meta["synthetic"])

if __name__ == "__main__":
    main()
