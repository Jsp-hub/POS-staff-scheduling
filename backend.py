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

# Convert the Timestamp column to datetime objects (only ONCE here)
features_df["Timestamp"] = pd.to_datetime(features_df["Timestamp"])

# Load trained ML model and encoders
model = joblib.load("Model/xgboost_model.joblib")
special_event_encoder = joblib.load("Encoders/special_event_encoder.joblib")
weather_encoder = joblib.load("Encoders/weather_encoder.joblib")

# Ensure the feature columns match model input format
def get_features_for_datetime(date_str, hour_str):
    #row = features_df[(features_df["Timestamp"] == date_str) & (features_df["Hour"].astype(str) == hour_str)]
    # Convert '2025-06-18' and '9' → '6/18/2025 9:00'
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_timestamp = datetime(date_obj.year, date_obj.month, date_obj.day, int(hour_str))
    #formatted_timestamp = f"{date_obj.month}/{date_obj.day}/{date_obj.year} {int(hour_str)}:00"

    row = features_df[(features_df["Timestamp"] == formatted_timestamp)]
    
    if row.empty:
        return None

    row = row.iloc[0].copy()

    # Encode categorical features using saved encoders
    if "Special_Event" in row:
        encoded_special_event = special_event_encoder.transform([[row["Special_Event"]]])[0][0]
        row["Special_Event_Encoded"] = encoded_special_event
        row.drop(labels=["Special_Event"], inplace=True)

    if "Weather" in row:
        encoded_weather = weather_encoder.transform([[row["Weather"]]])[0][0]
        row["Weather_Encoded"] = encoded_weather
        row.drop(labels=["Weather"], inplace=True)

    # Drop non-feature columns
    row = row.drop(labels=["Timestamp", "Weekday"])
    return row.to_dict()

def predict_covers(features):
    input_df = pd.DataFrame([features])

    #Ensure exact column order
    input_df = input_df[["Hour", "Is_Weekend", "Weather_Encoded", "Special_Event_Encoded"]]
    
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
