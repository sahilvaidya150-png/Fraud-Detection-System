# Fraud Detection System

A local fraud-scoring dashboard backed by the PaySim transaction dataset, a fitted scikit-learn preprocessing/model pipeline, FastAPI, and React/Vite. Existing source files and original notebooks are retained; the workspace's previous source/config files were empty, so the working app is wired into the existing structure.

## Data and model

- Raw source: `data/raw/PS_20174392719_1491204439457_log.csv` (6,362,620 rows; `isFraud` target).
- Training input: `data/processed/fraud_sampled.csv` (172,473 rows; 8,213 fraud and 164,260 non-fraud records).
- The full raw file was checked in chunks: no missing values or negative values in the transaction features; the processed sample has no missing values or exact duplicate rows. API input bounds match observed raw-data ranges.
- Prediction validation accepts steps 1–743, amounts up to 92,445,516.64, origin balances up to 59,585,040.37 / 49,585,040.37, and destination balances up to 356,015,889.35 / 356,179,278.92; negative and non-finite values are rejected.
- `nameOrig`, `nameDest`, and `isFlaggedFraud` are excluded from features. The feature pipeline fits scaling and one-hot encoding on the training split only.
- Model: class-weighted logistic regression with a stratified 80/20 holdout, saved to `models/production/fraud_pipeline.joblib`.
- Metrics are saved to `artifacts/metrics/model_metrics.json`. Precision and average precision reflect the downsampled holdout prevalence, not the raw dataset prevalence; the report includes this caveat.
- The provided processed sample is used as the dashboard's historical transaction table. New API predictions are stored in a local SQLite database at `artifacts/predictions.sqlite`.

## Windows setup

Run these commands from the project root in PowerShell. Use Node.js 22.12 or newer for the Vite 8 frontend:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m ml.models.train
```

Start the API in one terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Start the dashboard in another terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open the dashboard at <http://localhost:5173>, the API documentation at <http://127.0.0.1:8000/docs>, and the health endpoint at <http://127.0.0.1:8000/api/health>. Vite proxies `/api` calls to port 8000.

The dashboard login is verified by the backend, and all data/prediction API routes require its signed, HTTP-only session cookie. In local development the backend prints a randomly generated one-time password for username `analyst` when it starts. To choose your own login, set `FRAUD_AUTH_USERNAME`, `FRAUD_AUTH_PASSWORD`, and `FRAUD_AUTH_SECRET` in the backend terminal before starting Uvicorn. Keep custom secrets private, bind the development server to `127.0.0.1`, and use HTTPS with `FRAUD_AUTH_COOKIE_SECURE=true` when serving outside the local machine.

## Notebook and checks

Open `notebooks/04_training_fixed.ipynb` in VS Code and run all cells from the project environment. It uses project-relative paths, invokes the same training pipeline as the API, writes the model and metrics artifacts, and scans the raw dataset in chunks for dataset-level counts. The original `notebooks/04_training.ipynb` remains unchanged.

Run automated tests from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest tests backend\tests
Set-Location frontend
npm run build
```

The API exposes `/api/health`, `/api/predictions/`, `/api/transactions/`, `/api/analytics/overview`, `/api/monitoring/`, and `/api/model/`. Monitoring reports only locally recorded predictions; drift status remains unavailable until a labelled live reference batch is supplied.

## Limitations

The processed training sample is an intentionally downsampled cohort, not a production-representative evaluation set. Threshold-based predictions and metrics are for demonstration and should not be treated as production-ready risk decisions without a representative temporal validation, calibration, operational review, and monitoring data. The video playback could not be inspected in this environment; the interface follows the dark navy/cyan design direction in the supplied requirements.