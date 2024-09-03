import io
import os
import uuid
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from flask import Flask, request, jsonify, render_template, url_for
from ets_forecast import (
    DataLoader,
    DataFilter,
    DataTransformer,
    DataProcessor,
    DataForecast,
)
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

IMAGE_DIR = 'static/images'

@app.route("/filter_data", methods=["POST"])
def filter_data():
    file_path = request.json.get("file_path")
    material_name = request.json.get("material_name")
    sold_to_party = request.json.get("sold_to_party")

    data_loader = DataLoader(file_path=file_path)
    data = data_loader.load_data()
    data = data_loader.convert_date("BillingDate")

    data_filter = DataFilter(data=pd.DataFrame(data))
    filtered_data = data_filter.apply_filters(
        material_name=material_name, sold_to_party=sold_to_party
    )
    return jsonify(filtered_data.to_dict(orient="records")), 200

@app.route("/transform_data", methods=["POST"])
def transform_data():
    filtered_data = request.json.get("filtered_data")

    filtered_data = [
        {
            **record,
            "BillingDate": datetime.strptime(
                record["BillingDate"], "%a, %d %b %Y %H:%M:%S %Z"
            ).strftime("%Y-%m-%d"),
        }
        for record in filtered_data
    ]

    data_transformer = DataTransformer(filtered_data=pd.DataFrame(filtered_data))
    transformed_data = data_transformer.transform_data()
    aggregated_data = data_transformer.aggregrate_data()

    return jsonify(aggregated_data.to_dict(orient="records")), 200

@app.route("/forecast", methods=["POST"])
def forecast():
    cleanup_images()

    aggregated_data = request.json.get("aggregated_data")
    shift_offset = request.json.get("shift_offset", -4)  # offset by expiry period
    forecast_days = request.json.get("forecast_days", 7)
    seasonal_period = request.json.get("seasonal_period", 4)  # expiry period

    aggregated_data_df = pd.DataFrame(aggregated_data)
    aggregated_data_df['BillingDate'] = pd.to_datetime(aggregated_data_df['BillingDate'])  # Ensure datetime format
    aggregated_data_df.set_index("BillingDate", inplace=True)

    data_processor = DataProcessor(aggregated_data=aggregated_data_df)
    results = data_processor.offset_and_recalculate(shift_offset=shift_offset)

    data_forecast = DataForecast(
        results=results, forecast_days=forecast_days, seasonal_period=seasonal_period
    )

    forecast_shelved = data_forecast.quantity_forecast('shelved_sum')
    forecast_expired = data_forecast.quantity_forecast('expired_sum')
    forecast_net = data_forecast.net_forecast()

    plt.figure(figsize=(14, 6))
    plt.plot(results.index, results['shelved_sum'], label='Historical Shelved', marker='o')
    plt.plot(results.index, results['expired_sum'], label='Historical Expired', marker='o')
    
    last_date = pd.to_datetime(results.index[-1])

    plt.plot(
        pd.date_range(start=last_date + pd.Timedelta(days=forecast_days), periods=forecast_days, freq='D'),
        forecast_shelved,
        label='Forecast Shelved',
        linestyle='--',
        marker='o'
    )
    plt.plot(
        pd.date_range(start=last_date + pd.Timedelta(days=forecast_days), periods=forecast_days, freq='D'),
        forecast_expired,
        label='Forecast Expired',
        linestyle='--',
        marker='o'
    )
    plt.plot(
        pd.date_range(start=last_date + pd.Timedelta(days=forecast_days), periods=forecast_days, freq='D'),
        forecast_net,
        label='Forecast Net Quantity',
        linestyle='--',
        marker='o'
    )
    plt.title('Forecast for Shelved, Expired, and Net Quantities')
    plt.xlabel('Offset Date')
    plt.ylabel('Quantity In Base Unit')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
    image_filename = os.path.join(IMAGE_DIR, f"{uuid.uuid4().hex}.png")

    plt.savefig(image_filename)
    plt.close()

    return jsonify({"image_url": url_for('static', filename=f'images/{os.path.basename(image_filename)}')}), 200

def cleanup_images():
    """Delete old images to prevent storage issues."""
    for filename in os.listdir(IMAGE_DIR):
        file_path = os.path.join(IMAGE_DIR, filename)
        if os.path.isfile(file_path):
            os.unlink(file_path)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
