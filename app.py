from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
from models import db, WeatherRequest
from utils import ai_chat_response, geocode_location, reverse_geocode, get_weather
from export_utils import export_as_csv, export_as_markdown, export_as_json
from dotenv import load_dotenv
import os, json, io
from datetime import datetime
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///weather.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "devkey")
db.init_app(app)

# Add template filter for date formatting
@app.template_filter('datetime')
def datetime_filter(timestamp):
    """Convert timestamp to readable date"""
    try:
        return datetime.fromtimestamp(int(timestamp)).strftime('%a, %b %d')
    except:
        return "N/A"

@app.before_first_request
def create_tables():
    db.create_all()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/create", methods=["GET","POST"])
def create():
    if request.method == "POST":
        user_input = request.form.get("location").strip()
        start_date = request.form.get("start_date") or ""
        end_date = request.form.get("end_date") or ""
        # simple validation: ensure location non-empty
        if not user_input:
            flash("Please enter location", "danger")
            return redirect(url_for("create"))

        geo = geocode_location(user_input)
        if not geo:
            flash("Could not resolve location. Try more specific input.", "danger")
            return redirect(url_for("create"))

        # validate date ranges (simple check)
        if start_date and end_date and start_date > end_date:
            flash("Start date must be before end date", "danger")
            return redirect(url_for("create"))

        # fetch weather with date range if provided
        weather = get_weather(geo["lat"], geo["lon"], start_date=start_date, end_date=end_date)
        
        # Import the summary function
        from utils import ai_generate_summary
        
        # Generate AI summary
        summary = ai_generate_summary(weather, geo["name"])
        
        # Create the weather request object with summary
        w = WeatherRequest(
            user_input=user_input,
            resolved_name=geo["name"],
            lat=geo["lat"],
            lon=geo["lon"],
            start_date=start_date,
            end_date=end_date,
            weather_json=json.dumps(weather),
            ai_summary=summary
        )
        
        # Add to database and commit to get the ID
        db.session.add(w)
        db.session.commit()
        flash("Weather fetched and stored!", "success")

        return redirect(url_for("view", id=w.id))
    
    return render_template("create.html")

@app.route("/chat/<int:id>", methods=["GET", "POST"])
def chat(id):
    rec = WeatherRequest.query.get_or_404(id)
    answer = None
    if request.method == "POST":
        question = request.form.get("message")
        weather = rec.weather()
        answer = ai_chat_response(question, rec.resolved_name, weather, rec.start_date, rec.end_date)
    return render_template("chat.html", rec=rec, answer=answer)

@app.route("/view/<int:id>")
def view(id):
    rec = WeatherRequest.query.get_or_404(id)
    weather_data = rec.weather()
    
    # Calculate predicted temperature
    from utils import predict_next_temp
    pred_temp = predict_next_temp(weather_data)
    
    return render_template("view.html", rec=rec, weather=weather_data, pred_temp=pred_temp)

@app.route("/list")
def list_requests():
    recs = WeatherRequest.query.order_by(WeatherRequest.created_at.desc()).all()
    return render_template("index.html", records=recs)

@app.route("/api/requests", methods=["GET"])
def api_list():
    recs = WeatherRequest.query.all()
    out = []
    for r in recs:
        out.append({"id": r.id, "user_input": r.user_input, "resolved": r.resolved_name, "lat": r.lat, "lon": r.lon})
    return jsonify(out)

@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit(id):
    rec = WeatherRequest.query.get_or_404(id)
    if request.method == "POST":
        # permit update of user_input and dates; revalidate and optionally re-fetch weather
        rec.user_input = request.form.get("location").strip()
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        if start_date and end_date and start_date > end_date:
            flash("Start date must be before end date", "danger")
            return redirect(url_for("edit", id=id))

        geo = geocode_location(rec.user_input)
        if geo:
            rec.resolved_name = geo["name"]
            rec.lat = geo["lat"]
            rec.lon = geo["lon"]
            # re-fetch weather with date range
            weather = get_weather(rec.lat, rec.lon, start_date=start_date, end_date=end_date)
            rec.weather_json = json.dumps(weather)
        rec.start_date = start_date
        rec.end_date = end_date
        db.session.commit()
        flash("Record updated", "success")
        return redirect(url_for("view", id=id))
    return render_template("edit.html", rec=rec)

@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    rec = WeatherRequest.query.get_or_404(id)
    db.session.delete(rec)
    db.session.commit()
    flash("Record deleted", "success")
    return redirect(url_for("list_requests"))

@app.route("/export/<int:id>/<string:fmt>")
def export(id, fmt):
    rec = WeatherRequest.query.get_or_404(id)
    if fmt.lower() == "csv":
        data = export_as_csv(rec)
        return send_file(io.BytesIO(data.encode()), mimetype="text/csv", as_attachment=True, download_name=f"weather_{id}.csv")
    if fmt.lower() == "md":
        data = export_as_markdown(rec)
        return send_file(io.BytesIO(data.encode()), mimetype="text/markdown", as_attachment=True, download_name=f"weather_{id}.md")
    if fmt.lower() == "json":
        data = export_as_json(rec)
        return jsonify(data)
    return "Unsupported format", 400

@app.route("/api/weather")
def api_weather():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if not lat or not lon:
        return jsonify({"error":"lat & lon required"}), 400
    try:
        w = get_weather(float(lat), float(lon))
        return jsonify(w)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/chat/<int:id>", methods=["POST"])
def api_chat(id):
    rec = WeatherRequest.query.get_or_404(id)
    data = request.get_json()
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    try:
        weather_data = rec.weather()
        response = ai_chat_response(message, rec.resolved_name, weather_data, rec.start_date, rec.end_date)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": "Failed to generate response"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")