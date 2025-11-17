from . import db
from datetime import datetime
import json


class Dataset(db.Model):
    __tablename__ = 'datasets'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(512), nullable=False)
    original_name = db.Column(db.String(512), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    rows = db.Column(db.Integer)
    cols = db.Column(db.Integer)
    meta_json = db.Column(db.Text)  # JSON string with column info, dtypes, sample

    def to_dict(self):
        meta = {}
        try:
            meta = json.loads(self.meta_json or "{}")
        except Exception:
            meta = {}
        return {
            'id': self.id,
            'filename': self.filename,
            'original_name': self.original_name,
            'upload_time': self.upload_time.isoformat(),
            'rows': self.rows,
            'cols': self.cols,
            'metadata': meta,
        }
