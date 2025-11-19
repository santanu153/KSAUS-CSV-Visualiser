KSUAS CSV Visualizer — Full-stack Flask app with ML Analytics

Overview

This project is a modern CSV visualization web app with predictive analytics: upload a CSV, create interactive charts, analyze trends, and forecast future values. Backend is Python + Flask + SQLite + scikit-learn; frontend uses Bootstrap and Chart.js.

Features:
- 📊 Multiple chart types (Bar, Line, Pie, Histogram)
- 🔮 Predictive analytics with linear regression (3/4/5 year forecasts)
- 📋 Comprehensive serial-wise analysis reports for each chart
- 📈 Statistical insights: mean, median, quartiles, outliers, trends
- 🗑️ Dataset management with upload/delete functionality

Quick start (Windows PowerShell)

1. Create and activate a virtual environment (recommended):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install --upgrade pip; pip install -r requirements.txt
```

3. Run the server:

```powershell
python run.py
```

4. Open http://127.0.0.1:5000 in your browser.

Notes

- Uploaded CSV files are stored in the `uploads/` folder.
- Metadata is stored in `datasets.db` (SQLite) in the project root.
- Basic API endpoints are available under `/api/*` for programmatic use.

Next steps / improvements

- Add authentication and per-user storage
- Support larger-than-memory CSVs with chunked processing
- Add more chart types and richer transform options
- Add server-side caching for expensive aggregations
