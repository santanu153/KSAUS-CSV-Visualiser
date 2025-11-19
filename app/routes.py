import os
import io
import json
from datetime import datetime
from flask import current_app as app, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from . import db
from .models import Dataset
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

ALLOWED = set(['csv', 'tsv'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'no file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'no selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        saved_name = f"{ts}_{filename}"
        path = os.path.join(app.config['UPLOAD_FOLDER'], saved_name)
        file.save(path)

        # parse with pandas
        try:
            sep = ','
            if filename.lower().endswith('.tsv'):
                sep = '\t'
            df = pd.read_csv(path, sep=sep)
        except Exception as e:
            return jsonify({'error': 'failed parsing CSV', 'detail': str(e)}), 400

        meta = {}
        meta['columns'] = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            is_numeric = pd.api.types.is_numeric_dtype(df[col])
            unique_sample = df[col].dropna().unique()[:5].tolist()
            meta['columns'].append({
                'name': col,
                'dtype': dtype,
                'is_numeric': bool(is_numeric),
                'unique_sample': unique_sample,
                'unique_count': int(df[col].nunique(dropna=True)),
            })
        rows, cols = df.shape
        meta['rows'] = int(rows)
        meta['cols'] = int(cols)

        ds = Dataset(filename=saved_name, original_name=filename, rows=rows, cols=cols, meta_json=json.dumps(meta))
        db.session.add(ds)
        db.session.commit()

        # store a small preview as CSV-in-memory if needed or rely on file reads
        return jsonify({'success': True, 'dataset': ds.to_dict()}), 201
    else:
        return jsonify({'error': 'file type not allowed'}), 400


@app.route('/api/datasets', methods=['GET'])
def list_datasets():
    all_ds = Dataset.query.order_by(Dataset.upload_time.desc()).all()
    return jsonify([d.to_dict() for d in all_ds])


@app.route('/api/dataset/<int:ds_id>/preview', methods=['GET'])
def dataset_preview(ds_id):
    ds = Dataset.query.get_or_404(ds_id)
    path = os.path.join(app.config['UPLOAD_FOLDER'], ds.filename)
    if not os.path.exists(path):
        return jsonify({'error': 'file not found'}), 404
    try:
        # read first 200 rows
        df = pd.read_csv(path, nrows=200)
        records = df.fillna('').to_dict(orient='records')
        return jsonify({'rows': records, 'columns': df.columns.tolist()})
    except Exception as e:
        return jsonify({'error': 'failed reading file', 'detail': str(e)}), 500


@app.route('/api/dataset/<int:ds_id>/columns', methods=['GET'])
def dataset_columns(ds_id):
    ds = Dataset.query.get_or_404(ds_id)
    meta = json.loads(ds.meta_json or '{}')
    return jsonify(meta.get('columns', []))


@app.route('/api/dataset/<int:ds_id>/chart', methods=['POST'])
def dataset_chart(ds_id):
    payload = request.get_json() or {}
    xcol = payload.get('x')
    ycol = payload.get('y')
    chart_type = payload.get('type', 'bar')
    agg = payload.get('agg', 'mean')

    ds = Dataset.query.get_or_404(ds_id)
    path = os.path.join(app.config['UPLOAD_FOLDER'], ds.filename)
    if not os.path.exists(path):
        return jsonify({'error': 'file not found'}), 404

    try:
        df = pd.read_csv(path)
    except Exception as e:
        return jsonify({'error': 'failed reading file', 'detail': str(e)}), 500

    if xcol is None:
        return jsonify({'error': 'x column required'}), 400

    # Handle histogram
    if chart_type == 'histogram':
        if xcol not in df.columns:
            return jsonify({'error': 'column not found'}), 400
        
        # Get numeric data for histogram
        data = df[xcol].dropna()
        
        # Check if data is numeric
        if not pd.api.types.is_numeric_dtype(data):
            return jsonify({'error': 'histogram requires numeric column'}), 400
        
        # Calculate histogram bins (default 10 bins)
        num_bins = payload.get('bins', 10)
        
        # Use numpy histogram for better control
        import numpy as np
        counts, bin_edges = np.histogram(data, bins=num_bins)
        
        # Create labels from bin edges
        labels = []
        for i in range(len(bin_edges) - 1):
            labels.append(f"{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}")
        
        # Convert numpy int64 to Python int for JSON serialization
        values = [int(count) for count in counts]
        
        return jsonify({'labels': labels, 'values': values, 'type': 'histogram'})

    if chart_type in ['line', 'bar'] and ycol is None:
        return jsonify({'error': 'y column required for this chart type'}), 400

    # simple grouping
    if ycol:
        if agg == 'sum':
            grouped = df.groupby(xcol)[ycol].sum()
        else:
            grouped = df.groupby(xcol)[ycol].mean()
        labels = grouped.index.astype(str).tolist()
        values = grouped.fillna(0).astype(float).tolist()
        return jsonify({'labels': labels, 'values': values, 'type': chart_type})
    else:
        # when y not provided, we can return counts per x
        counts = df[xcol].value_counts()
        labels = counts.index.astype(str).tolist()
        values = counts.astype(int).tolist()
        return jsonify({'labels': labels, 'values': values, 'type': 'bar'})


@app.route('/api/dataset/<int:ds_id>', methods=['DELETE'])
def delete_dataset(ds_id):
    ds = Dataset.query.get_or_404(ds_id)
    path = os.path.join(app.config['UPLOAD_FOLDER'], ds.filename)
    
    # Delete file from filesystem if it exists
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            return jsonify({'error': 'failed to delete file', 'detail': str(e)}), 500
    
    # Delete from database
    db.session.delete(ds)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Dataset deleted successfully'})


@app.route('/api/dataset/<int:ds_id>/predict', methods=['POST'])
def predict_trend(ds_id):
    """
    Predict future trends using linear regression.
    Expects JSON: { "x": "column_name", "y": "column_name", "years": 3/4/5 }
    """
    payload = request.get_json() or {}
    xcol = payload.get('x')
    ycol = payload.get('y')
    years = payload.get('years', 3)
    
    if xcol is None or ycol is None:
        return jsonify({'error': 'both x and y columns required for prediction'}), 400
    
    if years not in [3, 4, 5]:
        return jsonify({'error': 'years must be 3, 4, or 5'}), 400
    
    ds = Dataset.query.get_or_404(ds_id)
    path = os.path.join(app.config['UPLOAD_FOLDER'], ds.filename)
    if not os.path.exists(path):
        return jsonify({'error': 'file not found'}), 404
    
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return jsonify({'error': 'failed reading file', 'detail': str(e)}), 500
    
    if xcol not in df.columns or ycol not in df.columns:
        return jsonify({'error': 'column not found'}), 400
    
    # Check if both columns are numeric
    if not pd.api.types.is_numeric_dtype(df[xcol]) or not pd.api.types.is_numeric_dtype(df[ycol]):
        return jsonify({'error': 'both columns must be numeric for prediction'}), 400
    
    # Remove missing values
    clean_df = df[[xcol, ycol]].dropna()
    
    if len(clean_df) < 2:
        return jsonify({'error': 'insufficient data for prediction'}), 400
    
    # Prepare data for linear regression
    X = clean_df[xcol].values.reshape(-1, 1)
    y = clean_df[ycol].values
    
    # Fit linear regression model
    model = LinearRegression()
    model.fit(X, y)
    
    # Get current data stats
    current_max_x = clean_df[xcol].max()
    current_min_x = clean_df[xcol].min()
    x_range = current_max_x - current_min_x
    
    # Determine step size for predictions
    # If x appears to be years, use 1-year steps
    # Otherwise, extrapolate based on data distribution
    step = 1 if x_range < 100 else x_range / len(clean_df)
    
    # Generate future X values
    future_x = []
    for i in range(1, years + 1):
        future_x.append(current_max_x + (i * step))
    
    # Predict future values
    future_X = np.array(future_x).reshape(-1, 1)
    predictions = model.predict(future_X)
    
    # Calculate R² score and trend direction
    r2_score = model.score(X, y)
    slope = model.coef_[0]
    trend_direction = 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
    
    # Format predictions
    forecast = []
    for i, (x_val, y_pred) in enumerate(zip(future_x, predictions)):
        forecast.append({
            'x': float(x_val),
            'y': float(y_pred),
            'year': i + 1
        })
    
    return jsonify({
        'success': True,
        'forecast': forecast,
        'model_info': {
            'r2_score': float(r2_score),
            'slope': float(slope),
            'intercept': float(model.intercept_),
            'trend': trend_direction
        },
        'current_data': {
            'x_min': float(current_min_x),
            'x_max': float(current_max_x),
            'y_min': float(clean_df[ycol].min()),
            'y_max': float(clean_df[ycol].max()),
            'data_points': len(clean_df)
        }
    })


@app.route('/api/dataset/<int:ds_id>/analyze', methods=['POST'])
def analyze_charts(ds_id):
    """
    Generate comprehensive analysis reports for all chart types.
    Expects JSON: { "x": "column_name", "y": "column_name" }
    """
    payload = request.get_json() or {}
    xcol = payload.get('x')
    ycol = payload.get('y')
    
    if xcol is None:
        return jsonify({'error': 'x column required'}), 400
    
    ds = Dataset.query.get_or_404(ds_id)
    path = os.path.join(app.config['UPLOAD_FOLDER'], ds.filename)
    if not os.path.exists(path):
        return jsonify({'error': 'file not found'}), 404
    
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return jsonify({'error': 'failed reading file', 'detail': str(e)}), 500
    
    if xcol not in df.columns:
        return jsonify({'error': 'x column not found'}), 400
    
    if ycol and ycol not in df.columns:
        return jsonify({'error': 'y column not found'}), 400
    
    reports = []
    
    # Report 1: Bar Chart Analysis
    if ycol:
        bar_analysis = analyze_bar_chart(df, xcol, ycol)
        reports.append({
            'serial': 1,
            'chart_type': 'Bar Chart',
            'icon': '📊',
            'analysis': bar_analysis
        })
    
    # Report 2: Line Chart Analysis
    if ycol:
        line_analysis = analyze_line_chart(df, xcol, ycol)
        reports.append({
            'serial': 2,
            'chart_type': 'Line Chart',
            'icon': '📈',
            'analysis': line_analysis
        })
    
    # Report 3: Pie Chart Analysis
    if ycol:
        pie_analysis = analyze_pie_chart(df, xcol, ycol)
        reports.append({
            'serial': 3,
            'chart_type': 'Pie Chart',
            'icon': '🥧',
            'analysis': pie_analysis
        })
    
    # Report 4: Histogram Analysis
    if pd.api.types.is_numeric_dtype(df[xcol]):
        histogram_analysis = analyze_histogram(df, xcol)
        reports.append({
            'serial': 4,
            'chart_type': 'Histogram',
            'icon': '📉',
            'analysis': histogram_analysis
        })
    
    return jsonify({
        'success': True,
        'reports': reports,
        'dataset_info': {
            'name': ds.original_name,
            'rows': ds.rows,
            'cols': ds.cols,
            'x_column': xcol,
            'y_column': ycol
        }
    })


def analyze_bar_chart(df, xcol, ycol):
    """Analyze bar chart data and generate insights"""
    grouped = df.groupby(xcol)[ycol].mean()
    
    insights = {
        'summary': f'Analyzing {len(grouped)} categories by average {ycol}',
        'statistics': {
            'total_categories': int(len(grouped)),
            'highest_value': float(grouped.max()),
            'lowest_value': float(grouped.min()),
            'average_value': float(grouped.mean()),
            'median_value': float(grouped.median()),
            'std_deviation': float(grouped.std())
        },
        'top_performers': [],
        'bottom_performers': [],
        'key_insights': []
    }
    
    # Top 3 categories
    top_3 = grouped.nlargest(3)
    for idx, (category, value) in enumerate(top_3.items(), 1):
        insights['top_performers'].append({
            'rank': idx,
            'category': str(category),
            'value': float(value)
        })
    
    # Bottom 3 categories
    bottom_3 = grouped.nsmallest(3)
    for idx, (category, value) in enumerate(bottom_3.items(), 1):
        insights['bottom_performers'].append({
            'rank': idx,
            'category': str(category),
            'value': float(value)
        })
    
    # Generate key insights
    value_range = grouped.max() - grouped.min()
    insights['key_insights'].append(f"The data spans a range of {value_range:.2f} units")
    
    if grouped.std() / grouped.mean() > 0.5:
        insights['key_insights'].append("High variability detected across categories")
    else:
        insights['key_insights'].append("Relatively consistent values across categories")
    
    # Check for outliers
    q1 = grouped.quantile(0.25)
    q3 = grouped.quantile(0.75)
    iqr = q3 - q1
    outliers = grouped[(grouped < q1 - 1.5 * iqr) | (grouped > q3 + 1.5 * iqr)]
    if len(outliers) > 0:
        insights['key_insights'].append(f"Found {len(outliers)} potential outlier(s)")
    
    return insights


def analyze_line_chart(df, xcol, ycol):
    """Analyze line chart data for trends"""
    grouped = df.groupby(xcol)[ycol].mean().sort_index()
    
    insights = {
        'summary': f'Trend analysis of {ycol} over {xcol}',
        'statistics': {
            'data_points': int(len(grouped)),
            'starting_value': float(grouped.iloc[0]),
            'ending_value': float(grouped.iloc[-1]),
            'peak_value': float(grouped.max()),
            'lowest_value': float(grouped.min()),
            'average_value': float(grouped.mean())
        },
        'trend_analysis': {},
        'key_insights': []
    }
    
    # Calculate trend
    values = grouped.values
    if len(values) > 1:
        x_numeric = np.arange(len(values))
        slope = np.polyfit(x_numeric, values, 1)[0]
        
        if slope > 0:
            trend = 'Upward'
            trend_emoji = '📈'
        elif slope < 0:
            trend = 'Downward'
            trend_emoji = '📉'
        else:
            trend = 'Stable'
            trend_emoji = '➡️'
        
        insights['trend_analysis'] = {
            'direction': trend,
            'emoji': trend_emoji,
            'slope': float(slope),
            'change_rate': f"{((grouped.iloc[-1] - grouped.iloc[0]) / grouped.iloc[0] * 100):.2f}%"
        }
        
        # Key insights
        change_pct = (grouped.iloc[-1] - grouped.iloc[0]) / grouped.iloc[0] * 100
        insights['key_insights'].append(f"Overall change: {change_pct:+.2f}% from start to end")
        
        # Volatility
        volatility = grouped.std() / grouped.mean() * 100
        insights['key_insights'].append(f"Volatility index: {volatility:.2f}%")
        
        # Peaks and troughs
        peak_idx = grouped.idxmax()
        trough_idx = grouped.idxmin()
        insights['key_insights'].append(f"Peak at {peak_idx}, Trough at {trough_idx}")
    
    return insights


def analyze_pie_chart(df, xcol, ycol):
    """Analyze pie chart distribution"""
    grouped = df.groupby(xcol)[ycol].sum()
    total = grouped.sum()
    
    insights = {
        'summary': f'Distribution analysis of {ycol} across {xcol} categories',
        'statistics': {
            'total_value': float(total),
            'number_of_segments': int(len(grouped)),
            'largest_segment_value': float(grouped.max()),
            'smallest_segment_value': float(grouped.min()),
            'average_segment_value': float(grouped.mean())
        },
        'distribution': [],
        'key_insights': []
    }
    
    # Calculate percentages
    percentages = (grouped / total * 100).sort_values(ascending=False)
    
    for idx, (category, pct) in enumerate(percentages.items(), 1):
        insights['distribution'].append({
            'rank': idx,
            'category': str(category),
            'value': float(grouped[category]),
            'percentage': f"{pct:.2f}%"
        })
    
    # Key insights
    top_segment = percentages.iloc[0]
    insights['key_insights'].append(f"Largest segment: {percentages.index[0]} ({top_segment:.2f}%)")
    
    # Check for concentration
    top_3_total = percentages.head(3).sum()
    if top_3_total > 70:
        insights['key_insights'].append(f"High concentration: Top 3 segments represent {top_3_total:.2f}% of total")
    else:
        insights['key_insights'].append(f"Balanced distribution: Top 3 segments represent {top_3_total:.2f}% of total")
    
    # Check for dominant segment
    if top_segment > 50:
        insights['key_insights'].append("Single dominant segment detected (>50%)")
    
    return insights


def analyze_histogram(df, xcol):
    """Analyze histogram distribution"""
    data = df[xcol].dropna()
    
    insights = {
        'summary': f'Distribution analysis of {xcol}',
        'statistics': {
            'count': int(len(data)),
            'mean': float(data.mean()),
            'median': float(data.median()),
            'mode': float(data.mode()[0]) if len(data.mode()) > 0 else None,
            'std_dev': float(data.std()),
            'min': float(data.min()),
            'max': float(data.max()),
            'range': float(data.max() - data.min())
        },
        'quartiles': {
            'q1': float(data.quantile(0.25)),
            'q2': float(data.quantile(0.50)),
            'q3': float(data.quantile(0.75))
        },
        'key_insights': []
    }
    
    # Calculate skewness
    mean = data.mean()
    median = data.median()
    
    if abs(mean - median) < data.std() * 0.1:
        distribution = 'Normally distributed (symmetric)'
    elif mean > median:
        distribution = 'Right-skewed (positive skew)'
    else:
        distribution = 'Left-skewed (negative skew)'
    
    insights['key_insights'].append(distribution)
    
    # Check for outliers
    q1 = data.quantile(0.25)
    q3 = data.quantile(0.75)
    iqr = q3 - q1
    outliers = data[(data < q1 - 1.5 * iqr) | (data > q3 + 1.5 * iqr)]
    
    if len(outliers) > 0:
        insights['key_insights'].append(f"Detected {len(outliers)} outliers ({len(outliers)/len(data)*100:.2f}%)")
    else:
        insights['key_insights'].append("No significant outliers detected")
    
    # Coefficient of variation
    cv = (data.std() / data.mean()) * 100
    if cv < 15:
        insights['key_insights'].append(f"Low variability (CV: {cv:.2f}%)")
    elif cv < 30:
        insights['key_insights'].append(f"Moderate variability (CV: {cv:.2f}%)")
    else:
        insights['key_insights'].append(f"High variability (CV: {cv:.2f}%)")
    
    return insights


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
