# backend.py (Flask backend)
from flask import Flask, request, jsonify
import sqlite3
import math
import pandas as pd
import joblib
from datetime import datetime

app = Flask(__name__)

# Load features from CSV
features_df = pd.read_csv("Data/Calender testing data.csv")  # Moved to data/ folder

# Load trained ML model and encoders
model = joblib.load("Model/xgboost_model.joblib")
special_event_encoder = joblib.load("Encoders/special_event_encoder.joblib")
weather_encoder = joblib.load("Encoders/weather_encoder.joblib")

# Ensure the feature columns match model input format
def get_features_for_datetime(date_str, hour_str):
    #row = features_df[(features_df["Timestamp"] == date_str) & (features_df["Hour"].astype(str) == hour_str)]
    # Convert '2025-06-18' and '9' → '6/18/2025 9:00'
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_timestamp = f"{date_obj.month}/{date_obj.day}/{date_obj.year} {int(hour_str)}:00"

    row = features_df[(features_df["Timestamp"] == formatted_timestamp)]
    
    if row.empty:
        return None

    row = row.iloc[0].copy()

    # Encode categorical features using saved encoders
    if "Special_Event" in row:
        row["Special_Event"] = special_event_encoder.transform([row["Special_Event"]])[0]
    if "Weather" in row:
        row["Weather"] = weather_encoder.transform([row["Weather"]])[0]

    # Drop non-feature columns
    row = row.drop(labels=["Timestamp"])
    return row.to_dict()

def predict_covers(features):
    input_df = pd.DataFrame([features])
    return int(model.predict(input_df)[0])

def calculate_staff(covers):
    return {
        "waiter": math.ceil(covers / 20),
        "chef": math.ceil(covers / 50),
        "cleaner": math.ceil(covers / 80)
    }

def get_available_staff(role, shift_start, shift_end, needed):
    conn = sqlite3.connect("staff.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, phone FROM staff
        WHERE role=?
        AND time(available_start) <= time(?)
        AND time(available_end) >= time(?)
        AND date(available_start) <= date(?)
        AND date(available_end) >= date(?)
        LIMIT ?
    """, (role, shift_start, shift_end, shift_start, shift_end, needed))
    results = cursor.fetchall()
    conn.close()
    return results

def send_sms(phone, message):
    # Simulate SMS sending for demo purposes
    print(f"[SIMULATED SMS] To: {phone} | Message: {message}")

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    date_str = data["date"]
    hour_str = data.get("hour")

    features = get_features_for_datetime(date_str, hour_str)
    if features is None:
        return jsonify({"error": "No features found for this date and hour"}), 404

    covers = predict_covers(features)
    required = calculate_staff(covers)
    return jsonify({"covers": covers, "required_staff": required})

@app.route("/schedule", methods=["POST"])
def schedule():
    data = request.get_json()
    covers = data["covers"]
    shift_start = data["shift_start"]
    shift_end = data["shift_end"]

    required = calculate_staff(covers)
    all_scheduled = {}

    for role, count in required.items():
        staff_list = get_available_staff(role, shift_start, shift_end, count)
        for name, phone in staff_list:
            msg = f"Hi {name}, you're scheduled on {shift_start} to {shift_end}. Reply YES to confirm."
            send_sms(phone, msg)
        all_scheduled[role] = [name for name, _ in staff_list]

    return jsonify({"scheduled": all_scheduled})

if __name__ == "__main__":
    app.run(debug=True)
