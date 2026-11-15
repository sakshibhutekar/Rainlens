# RainLens

RainLens is a static map for exploring ECMWF six-hourly precipitation forecasts over India. It compares IFS with AIFS Single and provides a point forecast chart and summary.

**Live site:** [sakshibhutekar.github.io/Rainlens](https://sakshibhutekar.github.io/Rainlens/)

## 1. How it was created

### Forecast data

The data comes from [ECMWF Open Data](https://github.com/ecmwf/ecmwf-opendata), using the `ecmwf-opendata` Python client. RainLens requests total precipitation (`tp`) for the IFS and AIFS Single models at 0.25-degree resolution. IFS is ECMWF's physics-based Integrated Forecasting System; AIFS is its machine-learning-based Artificial Intelligence Forecasting System. [ECMWF describes the two systems](https://www.ecmwf.int/en/forecasts/documentation-and-support/changes-ecmwf-model).

The pipeline requests forecast leads from +6 through +144 hours in six-hour steps. It first asks each model for its latest cycle that has a +144-hour forecast, then tries that cycle and up to three earlier six-hour cycles. A paired result from the same cycle is preferred. If only one model can be read and validated, the pipeline can save that model as a partial run and marks `paired` false in the manifest.

The downloaded global GRIB fields are cropped to latitudes 38°N–6°N and longitudes 66°E–99°E. This produces a grid covering India and nearby areas. When model grids do not match, the pipeline linearly regrids one model onto the reference model's grid before comparison. It checks that forecast steps and valid times match the run, rejects non-finite values and large accumulation drops, and validates the final output dimensions and rainfall range.

### Converting precipitation to six-hour rainfall

The downloaded `tp` fields are accumulated totals from the start of a forecast, so the pipeline differences each step against the previous step (using zero before the first +6-hour step). This produces rainfall for each individual six-hour interval.

The two GRIBs use different units: IFS precipitation is in metres, while AIFS Single precipitation is in kg/m². For liquid water, 1 kg/m² is equivalent to 1 mm of water, so AIFS values are converted to metres before differencing. [ECMWF's AIFS parameter table lists these units](https://confluence.ecmwf.int/spaces/FCST/pages/496875126/Implementation%2Bof%2BAIFS%2BSingle%2Bv1). After differencing, the pipeline converts metres to millimetres.

GRIB packing can cause a tiny negative difference even when accumulated precipitation should be flat. The pipeline allows decreases of up to 0.5 mm as packing noise and clips those differences to zero. A larger decrease is treated as a data reset or invalid field, and that model/run is rejected rather than silently presented as rainfall.

### Data files and browser app

`pipeline.py` writes three files under `web/data/`:

- `ifs.json` and `aifs-single.json` contain 24 forecast frames each. Values are stored as integer tenths of a millimetre (`scale: 10`) to reduce JSON size. Each frame is a flattened, row-major grid with north at the top.
- `manifest.json` records the model run, valid times, grid bounds and dimensions, available models, paired/synthetic flags, provenance, and the encoding note.

The browser loads these relative JSON paths; it does not call ECMWF directly. Leaflet displays a map and the decoded rainfall overlay. Chart.js shows the IFS and AIFS series in distinct colors at a clicked grid cell or selected city, highlighting the currently selected step. Users can switch between IFS, AIFS, and the paired difference view, and between dark and light themes. The timeline supports play, previous/next, keyboard arrows, and spacebar. City shortcuts include Mumbai, Pune, Chh. Sambhaji Nagar, Nagpur, Delhi, Bengaluru, Chennai, Kolkata, and Hyderabad.

The rain summary follows the selected model (or labels the IFS vs AIFS comparison view), chooses the wettest contiguous run of intervals, and reports its start as the first interval's end time minus six hours. Each interval is classed by its peak six-hour amount: light (<2.5 mm), moderate (2.5–<10 mm), heavy (10–25 mm), or very heavy (>25 mm). Rainy steps for this summary are those with at least 0.2 mm. If paired six-day totals differ by more than a factor of two and by more than 10 mm, the summary also flags the disagreement. Summary times are shown in India Standard Time (IST); model run time is shown in UTC.

The map overlay uses a transparent rainfall color scale in mm per six hours. In Difference mode, the field is AIFS minus IFS: red means AIFS is wetter, blue means AIFS is drier, and differences below 2 mm per six-hour interval are transparent. The About dialog describes the models, attribution, and guidance limitations.

RainLens uses OpenStreetMap raster tiles with a CSS dark filter, with OpenStreetMap attribution. This replaced the old no-key CARTO tile URL because [CARTO now requires an API key for external basemaps](https://carto.com/blog/positron-dark-matter-new-look/index.html). Leaflet and Chart.js are loaded from CDNs.

### Low rainfall values and the 0.3 mm question

RainLens stores rainfall to the nearest 0.1 mm, so a value of 0.3 mm is stored as `3` with `scale: 10`, then decoded back to 0.3 mm in the browser. The browser uses a floating-point typed array so tenths of a millimetre are retained; an earlier integer-array decode truncated decimal values and has been corrected. Values below 0.2 mm per six-hour interval are transparent on the map; values from 0.2 mm to below 1 mm use the light-blue color. The point chart can show these small values directly.

There is also a separate threshold in the written summary: if the sum across the full six-day forecast at the selected point is below 1 mm, the summary says “No significant rain expected.” That can make a small amount such as 0.3 mm seem absent from the summary even though it remains in the data and chart. Low amounts may also be visually subtle on the map because the overlay is partially transparent.

### Local generation and deployment

To install the pipeline dependencies, generate or refresh the forecast files, and serve the static app locally:

```sh
python -m pip install -r requirements.txt
python pipeline.py
python -m http.server --directory web 8000
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) on the same computer. Keep the server command running while using the page.

The GitHub Actions workflow at `.github/workflows/deploy-pages.yml` runs on each push to `main` (and can also be started manually). It checks out the repository, configures Pages, uploads **only `web/`** as the Pages artifact, and deploys it. It does not install Python dependencies or run `pipeline.py`. To publish a refreshed forecast, run the pipeline locally, commit the updated JSON files in `web/data/`, and push to `main`. The `.gitignore` excludes downloaded `*.grib2` files and `*.idx` request indexes; it does not ignore the JSON forecast data.

The repository uses ECMWF Open Data under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). Please retain attribution when reusing the forecast data.

### What the current paired run shows

The following comparison was calculated from the committed paired real-data run **2026-11-14 18:00 UTC**, over 24 six-hour steps and 17,157 grid cells (129 x 133). AIFS-minus-IFS is the signed-difference convention. All grid cells are equally weighted; these are not area-weighted or land-only statistics.

| Measure | Result |
| --- | ---: |
| Paired grid-cell / six-hour values | 411,768 |
| Mean rainfall per grid cell per interval | IFS 0.862 mm; AIFS 0.773 mm |
| Mean AIFS - IFS difference per interval | -0.089 mm |
| Mean absolute interval difference | 0.658 mm |
| Median absolute interval difference | 0.0 mm |
| Interval pairs differing by less than 0.2 mm | 72.38% |
| 90th percentile absolute interval difference | 1.4 mm |
| Interval pairs differing by at least 2 mm | 7.72% |
| Six-day average total per grid cell | IFS 20.69 mm; AIFS 18.54 mm |
| Mean AIFS - IFS difference in six-day totals | -2.15 mm per grid cell |
| Absolute six-day total difference: median / 90th percentile | 0.8 mm / 25.34 mm |
| Largest absolute six-day total difference at one cell | 481.9 mm |

The low median interval difference supports the conclusion that the two forecasts often give similar values at a grid cell and time step. The six-day totals have a different shape: the mean absolute difference is 9.47 mm, while the median is 0.8 mm and the 90th percentile is 25.34 mm. The upper tail of localized large differences pulls the mean upward; the median alone does not describe those hotspots.

To check the visible Bay of Bengal hotspot, we compared an approximate rectangle (6-23 N, 80-99 E) with the rest of the grid. This is not a coastline or ocean polygon; the box includes both sea and nearby land.

| Region | Grid cells | Cells meeting six-day disagreement rule | Median / P90 absolute six-day difference | Six-hour pairs with abs. difference >=2 mm |
| --- | ---: | ---: | ---: | ---: |
| Approximate Bay of Bengal box | 5,313 (31.0%) | 1,101 (68.7% of qualifying cells) | 12.1 / 58.4 mm | 22.22% |
| Outside that box | 11,844 (69.0%) | 502 (31.3% of qualifying cells) | 0.2 / 3.97 mm | 1.22% |

The spatial counts support saying that disagreement in this run is concentrated around the Bay of Bengal region. Because the calculation uses an approximate box and not a land mask, it does not establish what share of India's land area is in disagreement.

**Conclusion:** For this forecast pair, agreement is close at the typical grid cell, while a smaller set of large, geographically concentrated differences drives much of the total discrepancy. The numbers do not say which model was more accurate. IFS is physics-based and AIFS is machine-learning-based; determining forecast skill requires comparing each forecast with independent observations (such as gauges or radar) for the same places and times. [ECMWF describes this model distinction](https://www.ecmwf.int/en/forecasts/documentation-and-support/changes-ecmwf-model).

## 2. Limitations

- **Six-hour intervals:** Rain amounts represent each six-hour accumulation interval, not hourly timing. The forecast has 24 frames, covering +6 to +144 hours (six days). A displayed interval's start is its end time minus six hours.
- **Grid resolution:** The 0.25° grid is relatively coarse and cannot resolve every local storm, valley, coastline effect, or terrain-driven rainfall feature. Point charts use the nearest grid cell rather than an observation at the exact clicked coordinate.
- **Forecast uncertainty:** IFS and AIFS are model guidance and can disagree. RainLens does not verify either model against rain gauges or radar, and it does not provide probabilities or calibrated confidence.
- **Not an official warning:** This app is for exploration and must not be used as an official weather alert or as a substitute for local meteorological guidance.
- **Run availability:** ECMWF publishes forecast cycles on its own schedule and applies service limits. If the newest run is incomplete or unavailable, the pipeline tries earlier cycles. If it can only validate one model, comparison is disabled for that run.
- **Synthetic fallback:** If no real model result can be used, the pipeline writes clearly labeled synthetic sample data so the interface can still be previewed. The red banner and map watermark indicate this; sample values are not forecasts.
- **Manual forecast refresh:** GitHub Pages deploys the JSON files already committed to `web/data/`; it does not fetch new forecasts. Data gets fresher only after the pipeline is run and its outputs are pushed.
- **Online dependencies:** The app needs a network connection for Leaflet, Chart.js, and OpenStreetMap tiles. Forecast JSON is static and served from the site itself.
- **Summary thresholds:** Per-interval values below 0.2 mm are not rendered on the map and are not counted as rainy steps in the text summary. The text summary also reports no significant rain when the six-day point total is below 1 mm.
