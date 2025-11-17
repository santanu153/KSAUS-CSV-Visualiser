import os
import io
import json
from datetime import datetime
from flask import current_app as app, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from . import db
from .models import Dataset
import pandas as pd

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


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
