from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Topic(db.Model):
    __tablename__ = "topics"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True)
    type = db.Column(db.String(64), default="")
    rate = db.Column(db.Integer, default=10)

class Recording(db.Model):
    __tablename__ = "recordings"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), default="")
    topics_json = db.Column(db.Text, default="[]")
    status = db.Column(db.String(16), default="recording")
    size = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(256), default="")
