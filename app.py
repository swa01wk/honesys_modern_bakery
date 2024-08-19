from flask import Flask, request, jsonify
from ets_forecast import (
    DataLoader,
    DataFilter,
    DataTransformer,
    DataProcessor,
    DataForecast,
)
import pandas as pd
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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
    aggregated_data = request.json.get("aggregated_data")
    shift_offset = request.json.get("shift_offset", -4)  # offset by expiry period
    forecast_days = request.json.get("forecast_days", 7)
    seasonal_period = request.json.get("seasonal_period", 4)  # expiry period

    aggregated_data_df = pd.DataFrame(aggregated_data)
    aggregated_data_df.set_index("BillingDate", inplace=True)

    data_processor = DataProcessor(aggregated_data=aggregated_data_df)
    results = data_processor.offset_and_recalculate(shift_offset=shift_offset)

    data_forecast = DataForecast(
        results=results, forecast_days=forecast_days, seasonal_period=seasonal_period
    )
    # forecast_result = data_forecast.quantity_forecast('expired_sum')
    forecast_result = data_forecast.net_forecast()

    return jsonify(forecast_result.to_dict(orient="records")), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
