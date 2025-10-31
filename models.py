from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class WeatherRequest(db.Model):
    __tablename__ = "weather_requests"
    id = db.Column(db.Integer, primary_key=True)
    user_input = db.Column(db.String(256), nullable=False)        
    resolved_name = db.Column(db.String(256))                     
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    start_date = db.Column(db.String(20))                         
    end_date = db.Column(db.String(20))
    weather_json = db.Column(db.Text)                             
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ai_summary = db.Column(db.Text)

    def weather(self):
        try:
            return json.loads(self.weather_json)
        except:
            return {}
