# RainLens

RainLens is a static India precipitation viewer comparing ECMWF IFS and AIFS model output. Rainfall values are derived six-hourly accumulations from ECMWF Open Data. Model output is not an official warning.

## Run locally

From this directory:

```sh
python -m pip install -r requirements.txt
python pipeline.py
python -m http.server -d web 8000
```

Then open http://localhost:8000. The generated forecast data lives in `web/data/`. If ECMWF data cannot be fetched, the pipeline writes clearly labeled synthetic sample data; never treat it as a forecast.

Data: ECMWF Open Data, CC-BY-4.0. Grid resolution is 0.25 degrees, intervals are six-hourly, and output is not verified against observations.
