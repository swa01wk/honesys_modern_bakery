import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import matplotlib.pyplot as plt
import json


class DataLoader:
    def __init__(self, file_paths):
        self.file_paths = file_paths
        self.data = None

    def load_data(self, sheet_name=None):
        all_data = []

        for file_path in self.file_paths:
            data = pd.read_excel(file_path, sheet_name=sheet_name)
            if isinstance(data, dict):
                data = pd.concat(data.values(), ignore_index=True)
            all_data.append(data)

        self.data = pd.concat(all_data, ignore_index=True)
        return self.data

    def convert_date(self, date_column):
        self.data[date_column] = pd.to_datetime(self.data[date_column], format="%Y%m%d")
        self.data[date_column] = self.data[date_column].dt.strftime('%Y-%m-%d %H:%M:%S')
        return self.data


class DataFilter:
    def __init__(self, data):
        self.data = data
        self.filtered_data = None

    def apply_filters(self, material_name, sold_to_party):
        self.filtered_data = self.data[
            (self.data["MaterialName"] == material_name)
            & (self.data["SoldToParty"] == sold_to_party)
        ]
        return self.filtered_data


class DataTransformer:
    def __init__(self, filtered_data):
        self.filtered_data = filtered_data
        self.transformed_data = None

    def transform_data(self):
        self.transformed_data = self.filtered_data.assign(
            shelved_count=lambda x: x["QuantityInBaseUnit"].apply(
                lambda q: q if q > 0 else 0
            ),
            expired_count=lambda x: x["QuantityInBaseUnit"].apply(
                lambda q: q if q < 0 else 0
            ),
        )
        return self.transformed_data

    def aggregrate_data(self):
        aggregrated_data = (
            self.transformed_data.groupby(["BillingDate", "MaterialName"])
            .agg(
                shelved_sum=("shelved_count", "sum"),
                expired_sum=("expired_count", "sum"),
            )
            .reset_index()
        )
        return aggregrated_data


class DataProcessor:
    def __init__(self, aggregated_data):
        self.aggregated_data = aggregated_data
        self.result_data = None

    def offset_and_recalculate(self, shift_offset):
        self.aggregated_data.sort_values(by="BillingDate", inplace=True)
        self.aggregated_data["expired_sum"] = self.aggregated_data["expired_sum"].shift(
            shift_offset, fill_value=0
        )
        self.aggregated_data["net_sum"] = (
            self.aggregated_data["shelved_sum"] - self.aggregated_data["expired_sum"]
        )
        self.result_data = (
            self.aggregated_data.groupby("BillingDate")
            .agg(
                shelved_sum=("shelved_sum", "sum"),
                expired_sum=("expired_sum", "sum"),
                net_sum=("net_sum", "sum"),
            )
            .reset_index()
        )
        self.result_data.set_index("BillingDate", inplace=True)
        return self.result_data.iloc[:shift_offset]


class DataForecast:
    def __init__(self, results, forecast_days, seasonal_period, max_expiry_ratio=0.05, safety_stock=20):
        self.results = results
        self.forecast_days = forecast_days
        self.seasonal_period = seasonal_period
        self.max_expiry_ratio = max_expiry_ratio  # Maximum percentage of shelved stock that can expire
        self.safety_stock = safety_stock  # Buffer to avoid stockouts
        self.carryover_stock = 0  # Initialize carryover stock

    def fit_model(self, column_quantity):
        # Fitting the Exponential Smoothing (ETS) model
        model = ExponentialSmoothing(
            self.results[column_quantity],
            seasonal="add",
            trend="add",
            seasonal_periods=self.seasonal_period,
            damped_trend=False,  # Allow more aggressive predictions by disabling damped trend
            initialization_method='estimated'  # Using 'estimated' for better fit
        ).fit(
            smoothing_level=0.6,  # More weight on recent data
            smoothing_slope=0.5,  # Moderate trend smoothing
            smoothing_seasonal=0.6  # More aggressive seasonal smoothing
        )
        return model

    def forecasting_period(self):
        max_date = self.results.index.max()
        max_date = pd.to_datetime(max_date, format="%Y-%m-%d")
        forecast_start_date = max_date + pd.Timedelta(days=1)
        forecast_index = pd.date_range(
            start=forecast_start_date, periods=self.forecast_days, freq="D"
        )
        return forecast_index

    def quantity_forecast(self, column_quantity):
        # Forecasting for a specific quantity (e.g., shelved_sum or expired_sum)
        forecast_model = self.fit_model(column_quantity)
        forecast_index = self.forecasting_period()
        forecast_series = forecast_model.forecast(steps=self.forecast_days).round()

        # Apply carryover stock adjustment and safety stock
        forecast_series += self.carryover_stock  # Add carryover stock from the previous day
        forecast_series = forecast_series.clip(lower=self.safety_stock)  # Ensure minimum stock level

        return pd.DataFrame(
            {f"forecast_{column_quantity}": forecast_series.values},
            index=forecast_index,
        )

    def shelved_forecast(self):
        # Forecast shelved quantities
        return self.quantity_forecast("shelved_sum")

    def expired_forecast(self, shelved_df):
        # Forecast expired quantities, but cap them based on max_expiry_ratio to minimize wastage
        expired_df = self.quantity_forecast("expired_sum")

        # Ensure expired values are negative or zero (expired stock should reduce the shelved stock)
        expired_df[f"forecast_expired_sum"] = expired_df[f"forecast_expired_sum"].clip(upper=0)

        # Cap expired quantities based on shelved stock, ensuring expired stock is non-positive
        expired_df[f"forecast_expired_sum"] = expired_df[f"forecast_expired_sum"].clip(
            upper=shelved_df[f"forecast_shelved_sum"] * (-self.max_expiry_ratio)
        )
        
        return expired_df

    def net_forecast(self):
        # Forecast shelved and expired quantities separately
        shelved_df = self.shelved_forecast()
        expired_df = self.expired_forecast(shelved_df)

        # Calculate net available stock by subtracting expired forecast from shelved forecast
        net_df = shelved_df[f"forecast_shelved_sum"] + expired_df[f"forecast_expired_sum"]

        # Ensure net forecast does not go below zero
        return pd.DataFrame({"forecast_net": net_df.clip(lower=0)}, index=shelved_df.index)

    def update_carryover_stock(self, actual_sold):
        # Update carryover stock based on sales data
        shelved_forecast = self.shelved_forecast()
        total_stock = shelved_forecast.sum().values[0]  # Total stock available (forecasted)
        unsold_stock = total_stock - actual_sold  # Stock left unsold

        # Carryover stock is unsold stock that rolls over to the next day
        self.carryover_stock = max(unsold_stock, 0)  # Ensure it's not negative

        # Clip carryover to avoid exceeding expiration limits
        self.carryover_stock = min(self.carryover_stock, total_stock * self.max_expiry_ratio)

# # file_paths = ["./data/SEP-OCT-NOV.xlsx", "./data/DEC-JAN-FEB-MAR.xlsx"]
# file_paths = ["./data/SEP-OCT-NOV.xlsx"]
# forecast_days = 7

# data_loader = DataLoader(file_paths=file_paths)
# data = data_loader.load_data()
# data = data_loader.convert_date("BillingDate")

# data_filter = DataFilter(data=data)
# filtered_data = data_filter.apply_filters(
#     material_name='BREAD ROLL SANDWICH 6.3/4" PLAIN', sold_to_party=210094
# )

# data_transformer = DataTransformer(filtered_data=filtered_data)
# transformed_data = data_transformer.transform_data()
# aggregated_data = data_transformer.aggregrate_data()

# data_processor = DataProcessor(aggregated_data=aggregated_data)
# result_df = data_processor.offset_and_recalculate(shift_offset=-4)

# forecast = DataForecast(results=result_df, forecast_days=forecast_days, seasonal_period=4)

# print(forecast.quantity_forecast("shelved_sum"))
# print(forecast.quantity_forecast("expired_sum"))
# print(forecast.net_forecast())

# # Plot forecasts
# plt.figure(figsize=(14, 6))
# plt.plot(result_df.index, result_df['shelved_sum'], label='Historical Shelved', marker='o')
# plt.plot(result_df.index, result_df['expired_sum'], label='Historical Expired', marker='o')
# plt.plot(
#     pd.date_range(start=result_df.index[-1] + pd.Timedelta(days=forecast_days), periods=forecast_days, freq='7D'),
#     forecast.quantity_forecast('shelved_sum'),
#     label='Forecast Shelved',
#     linestyle='--',
#     marker='o'
# )
# plt.plot(
#     pd.date_range(start=result_df.index[-1] + pd.Timedelta(days=forecast_days), periods=forecast_days, freq='7D'),
#     forecast.quantity_forecast('expired_sum'),
#     label='Forecast Expired',
#     linestyle='--',
#     marker='o'
# )
# plt.plot(
#     pd.date_range(start=result_df.index[-1] + pd.Timedelta(days=forecast_days), periods=forecast_days, freq='7D'),
#     forecast.net_forecast(),
#     label='Forecast Net Quantity',
#     linestyle='--',
#     marker='o'
# )
# plt.title('Forecast for Shelved, Expired, and Net Quantities')
# plt.xlabel('Offset Date')
# plt.ylabel('Quantity In Base Unit')
# plt.grid(True)
# plt.legend()
# plt.tight_layout()
# plt.show()
