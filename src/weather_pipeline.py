import requests
import pandas as pd

from pathlib import Path
from datetime import datetime

CITY = "Raipur"

LATITUDE = 21.2514
LONGITUDE = 81.6296

TIMEZONE = "Asia/Kolkata"

FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
)

HISTORICAL_URL = (
    "https://archive-api.open-meteo.com/v1/archive"
)

PREVIOUS_RUNS_URL = (
    "https://previous-runs-api.open-meteo.com/v1/forecast"
)

BASE_DIR = Path(__file__).resolve().parent

WEATHER_FILE = BASE_DIR / "weather_data.csv"
FORECAST_FILE = BASE_DIR / "forecast_history.csv"
ACCURACY_FILE = BASE_DIR / "forecast_accuracy.csv"
PREVIOUS_RUNS_FILE = BASE_DIR / "previous_runs.csv"
ACCURACY_FILE = BASE_DIR / "forecast_accuracy.csv"

def get_current_time():

    return pd.Timestamp.now(
        tz=TIMEZONE
    ).tz_localize(None)


def request_api(url, params):

    try:

        response = requests.get(
            url,
            params=params,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        if "error" in data:
            raise RuntimeError(
                data.get(
                    "reason",
                    "Open-Meteo returned an API error."
                )
            )

        return data

    except requests.exceptions.RequestException as e:

        raise RuntimeError(
            f"API request failed:\n{e}"
        )


def fetch_weather():

    params = {

        "latitude": LATITUDE,
        "longitude": LONGITUDE,

        "timezone": TIMEZONE,

        "past_days": 10,
        "forecast_days": 7,

        "hourly": ",".join([

            "temperature_2m",
            "apparent_temperature",

            "relative_humidity_2m",
            "dew_point_2m",

            "precipitation_probability",
            "precipitation",
            "rain",

            "weather_code",

            "pressure_msl",

            "cloud_cover",

            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",

            "uv_index"
        ])
    }

    return request_api(
        FORECAST_URL,
        params
    )


def transform_weather(data):

    hourly = data["hourly"]

    df = pd.DataFrame(hourly)

    df = df.rename(
        columns={
            "time": "datetime",

            "temperature_2m":
                "temperature_c",

            "apparent_temperature":
                "feels_like_c",

            "relative_humidity_2m":
                "humidity_pct",

            "dew_point_2m":
                "dew_point_c",

            "precipitation_probability":
                "rain_probability_pct",

            "precipitation":
                "precipitation_mm",

            "rain":
                "rain_mm",

            "weather_code":
                "weather_code",

            "pressure_msl":
                "pressure_hpa",

            "cloud_cover":
                "cloud_cover_pct",

            "wind_speed_10m":
                "wind_speed_kmh",

            "wind_direction_10m":
                "wind_direction_deg",

            "wind_gusts_10m":
                "wind_gust_kmh",

            "uv_index":
                "uv_index"
        }
    )

    df["datetime"] = pd.to_datetime(
        df["datetime"]
    )

    df["date"] = (
        df["datetime"].dt.date
    )

    df["hour"] = (
        df["datetime"].dt.hour
    )

    df["city"] = CITY

    df["latitude"] = LATITUDE

    df["longitude"] = LONGITUDE

    current_date = (
        get_current_time().date()
    )

    df["data_type"] = df["date"].apply(
        lambda x:
        "Historical"
        if x < current_date
        else "Forecast"
    )

    columns = [

        "datetime",
        "date",
        "hour",

        "city",
        "latitude",
        "longitude",

        "data_type",

        "temperature_c",
        "feels_like_c",

        "humidity_pct",
        "dew_point_c",

        "rain_probability_pct",

        "precipitation_mm",
        "rain_mm",

        "weather_code",

        "pressure_hpa",

        "cloud_cover_pct",

        "wind_speed_kmh",
        "wind_direction_deg",
        "wind_gust_kmh",

        "uv_index"
    ]

    return df[columns]

def save_weather_data(df):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        WEATHER_FILE,
        index=False
    )

    print(
        f"Weather data saved: {len(df)} rows"
    )


def create_forecast_snapshot(data):

    hourly = data["hourly"]

    df = pd.DataFrame(hourly)

    df = df.rename(
        columns={
            "time":
                "forecast_for",

            "temperature_2m":
                "forecast_temperature_c",

            "precipitation_probability":
                "forecast_rain_probability_pct",

            "precipitation":
                "forecast_precipitation_mm",

            "weather_code":
                "forecast_weather_code"
        }
    )

    df = df[
        [
            "forecast_for",

            "forecast_temperature_c",

            "forecast_rain_probability_pct",

            "forecast_precipitation_mm",

            "forecast_weather_code"
        ]
    ]

    df["forecast_for"] = pd.to_datetime(
        df["forecast_for"]
    )

    generated_at = get_current_time()

    df["forecast_generated_at"] = (
        generated_at
    )

    df["lead_hours"] = (
        df["forecast_for"]
        -
        generated_at
    ).dt.total_seconds() / 3600

    df["city"] = CITY

    # Keep only current/future forecast times

    df = df[
        df["forecast_for"]
        >=
        generated_at.floor("h")
    ]

    return df[
        [
            "forecast_generated_at",
            "forecast_for",
            "lead_hours",

            "city",

            "forecast_temperature_c",
            "forecast_rain_probability_pct",
            "forecast_precipitation_mm",
            "forecast_weather_code"
        ]
    ]


def save_forecast_snapshot(df):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if (
        FORECAST_FILE.exists()
        and
        FORECAST_FILE.stat().st_size > 0
    ):

        try:

            existing = pd.read_csv(
                FORECAST_FILE
            )

            if not existing.empty:

                existing[
                    "forecast_generated_at"
                ] = pd.to_datetime(
                    existing[
                        "forecast_generated_at"
                    ]
                )

                existing[
                    "forecast_for"
                ] = pd.to_datetime(
                    existing[
                        "forecast_for"
                    ]
                )

                combined = pd.concat(
                    [
                        existing,
                        df
                    ],
                    ignore_index=True
                )

            else:

                combined = df

        except (
            pd.errors.EmptyDataError,
            pd.errors.ParserError
        ):

            combined = df

    else:

        combined = df

    combined = combined.drop_duplicates(
        subset=[
            "forecast_generated_at",
            "forecast_for",
            "city"
        ]
    )

    combined = combined.sort_values(
        [
            "forecast_generated_at",
            "forecast_for"
        ]
    )

    combined.to_csv(
        FORECAST_FILE,
        index=False
    )

    print(
        f"Forecast history saved: "
        f"{len(combined)} rows"
    )

def fetch_historical_weather():

    today = get_current_time().date()

    start_date = (
        today
        -
        pd.Timedelta(days=10)
    )

    end_date = (
        today
        -
        pd.Timedelta(days=1)
    )

    params = {

        "latitude": LATITUDE,
        "longitude": LONGITUDE,

        "start_date":
            start_date.strftime(
                "%Y-%m-%d"
            ),

        "end_date":
            end_date.strftime(
                "%Y-%m-%d"
            ),

        "timezone": TIMEZONE,

        "hourly": ",".join([

            "temperature_2m",
            "apparent_temperature",

            "relative_humidity_2m",
            "dew_point_2m",

            "precipitation",
            "rain",

            "weather_code",

            "pressure_msl",

            "cloud_cover",

            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m"
        ])
    }

    return request_api(
        HISTORICAL_URL,
        params
    )

def transform_historical_weather(data):

    hourly = data["hourly"]

    df = pd.DataFrame(hourly)

    df = df.rename(
        columns={

            "time":
                "datetime",

            "temperature_2m":
                "actual_temperature_c",

            "apparent_temperature":
                "actual_feels_like_c",

            "relative_humidity_2m":
                "actual_humidity_pct",

            "dew_point_2m":
                "actual_dew_point_c",

            "precipitation":
                "actual_precipitation_mm",

            "rain":
                "actual_rain_mm",

            "weather_code":
                "actual_weather_code",

            "pressure_msl":
                "actual_pressure_hpa",

            "cloud_cover":
                "actual_cloud_cover_pct",

            "wind_speed_10m":
                "actual_wind_speed_kmh",

            "wind_direction_10m":
                "actual_wind_direction_deg",

            "wind_gusts_10m":
                "actual_wind_gust_kmh"
        }
    )

    df["datetime"] = pd.to_datetime(
        df["datetime"]
    )

    df["date"] = (
        df["datetime"].dt.date
    )

    df["hour"] = (
        df["datetime"].dt.hour
    )

    df["city"] = CITY

    return df


def save_actual_weather(df):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        ACTUAL_FILE,
        index=False
    )

    print(
        f"Actual weather saved: "
        f"{len(df)} rows"
    )


def fetch_previous_runs():

    temperature_variables = []

    rain_probability_variables = []

    precipitation_variables = []

    for day in range(1, 8):

        temperature_variables.append(
            f"temperature_2m_previous_day{day}"
        )

        rain_probability_variables.append(
            "precipitation_probability_"
            f"previous_day{day}"
        )

        precipitation_variables.append(
            f"precipitation_previous_day{day}"
        )

    hourly_variables = (
        temperature_variables
        +
        rain_probability_variables
        +
        precipitation_variables
    )

    params = {

        "latitude": LATITUDE,
        "longitude": LONGITUDE,

        "timezone": TIMEZONE,

        # Need enough valid times to evaluate
        # the previous forecast runs.

        "past_days": 10,

        "forecast_days": 1,

        "hourly": ",".join(
            hourly_variables
        )
    }

    return request_api(
        PREVIOUS_RUNS_URL,
        params
    )


def transform_previous_runs(data):

    if "hourly" not in data:

        print(
            "Previous Runs API returned "
            "no hourly data."
        )

        return pd.DataFrame()

    hourly = data["hourly"]

    if "time" not in hourly:

        print(
            "Previous Runs API returned "
            "no time column."
        )

        return pd.DataFrame()

    df = pd.DataFrame(hourly)

    df["forecast_for"] = pd.to_datetime(
        df["time"]
    )

    records = []

    for day in range(1, 8):

        temperature_col = (
            f"temperature_2m_previous_day{day}"
        )

        rain_probability_col = (
            "precipitation_probability_"
            f"previous_day{day}"
        )

        precipitation_col = (
            f"precipitation_previous_day{day}"
        )

        if temperature_col not in df.columns:

            continue

        temp = df[
            [
                "forecast_for",
                temperature_col
            ]
        ].copy()

        temp = temp.rename(
            columns={
                temperature_col:
                    "forecast_temperature_c"
            }
        )

        if rain_probability_col in df.columns:

            temp[
                "forecast_rain_probability_pct"
            ] = df[
                rain_probability_col
            ]

        else:

            temp[
                "forecast_rain_probability_pct"
            ] = pd.NA

        if precipitation_col in df.columns:

            temp[
                "forecast_precipitation_mm"
            ] = df[
                precipitation_col
            ]

        else:

            temp[
                "forecast_precipitation_mm"
            ] = pd.NA

        temp[
            "forecast_horizon_days"
        ] = day

        temp["city"] = CITY

        temp[
            "forecast_generated_at"
        ] = (
            temp["forecast_for"]
            -
            pd.to_timedelta(
                day,
                unit="D"
            )
        )

        records.append(
            temp
        )

    if not records:

        print(
            "No previous-run variables were "
            "returned by the API."
        )

        return pd.DataFrame()

    result = pd.concat(
        records,
        ignore_index=True
    )

    result = result.dropna(
        subset=[
            "forecast_temperature_c"
        ]
    )

    result = result[
        [
            "forecast_generated_at",
            "forecast_for",
            "forecast_horizon_days",
            "city",

            "forecast_temperature_c",
            "forecast_rain_probability_pct",
            "forecast_precipitation_mm"
        ]
    ]

    result = result.drop_duplicates()

    result = result.sort_values(
        [
            "forecast_for",
            "forecast_horizon_days"
        ]
    )

    return result

def save_previous_runs(df):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if df.empty:

        print(
            "Previous runs returned no rows."
        )

        empty_columns = [

            "forecast_generated_at",
            "forecast_for",
            "forecast_horizon_days",
            "city",

            "forecast_temperature_c",
            "forecast_rain_probability_pct",
            "forecast_precipitation_mm"
        ]

        pd.DataFrame(
            columns=empty_columns
        ).to_csv(
            PREVIOUS_RUNS_FILE,
            index=False
        )

        return

    df.to_csv(
        PREVIOUS_RUNS_FILE,
        index=False
    )

    print(
        f"Previous runs saved: "
        f"{len(df)} rows"
    )


def create_forecast_accuracy():

    if not PREVIOUS_RUNS_FILE.exists():

        print(
            "Previous runs file does not exist."
        )

        return

    if not ACTUAL_FILE.exists():

        print(
            "Actual weather file does not exist."
        )

        return

    try:

        forecasts = pd.read_csv(
            PREVIOUS_RUNS_FILE
        )

        actual = pd.read_csv(
            ACTUAL_FILE
        )

    except pd.errors.EmptyDataError:

        print(
            "Forecast or actual weather CSV "
            "is empty."
        )

        return

    if forecasts.empty:

        print(
            "No previous-run forecasts "
            "available for accuracy analysis."
        )

        return

    if actual.empty:

        print(
            "No actual weather available "
            "for accuracy analysis."
        )

        return

    forecasts[
        "forecast_for"
    ] = pd.to_datetime(
        forecasts[
            "forecast_for"
        ]
    )

    actual[
        "datetime"
    ] = pd.to_datetime(
        actual[
            "datetime"
        ]
    )

    actual_columns = [

        "datetime",
        "city",

        "actual_temperature_c",
        "actual_precipitation_mm",
        "actual_rain_mm",
        "actual_weather_code"
    ]

    actual_subset = actual[
        actual_columns
    ].copy()

    accuracy = forecasts.merge(

        actual_subset,

        left_on=[
            "forecast_for",
            "city"
        ],

        right_on=[
            "datetime",
            "city"
        ],

        how="inner"
    )

    if accuracy.empty:

        print(
            "No forecast/reference matches "
            "were found yet."
        )

        # Create valid empty schema

        accuracy.to_csv(
            ACCURACY_FILE,
            index=False
        )

        return

    accuracy[
        "temperature_error_c"
    ] = (
        accuracy[
            "forecast_temperature_c"
        ]
        -
        accuracy[
            "actual_temperature_c"
        ]
    )

    accuracy[
        "absolute_temperature_error_c"
    ] = (
        accuracy[
            "temperature_error_c"
        ].abs()
    )


    accuracy[
        "predicted_rain"
    ] = (
        accuracy[
            "forecast_rain_probability_pct"
        ]
        >= 50
    )

    accuracy[
        "actual_rain"
    ] = (
        accuracy[
            "actual_rain_mm"
        ]
        > 0
    )

    accuracy[
        "rain_prediction_correct"
    ] = (
        accuracy[
            "predicted_rain"
        ]
        ==
        accuracy[
            "actual_rain"
        ]
    )


    accuracy[
        "forecast_horizon"
    ] = (
        accuracy[
            "forecast_horizon_days"
        ].astype(str)
        +
        " Day"
    )

    accuracy.to_csv(
        ACCURACY_FILE,
        index=False
    )

    print(
        f"Forecast accuracy saved: "
        f"{len(accuracy)} rows"
    )


def print_summary():

    print("\n")
    print("=" * 55)
    print("DATASET SUMMARY")
    print("=" * 55)

    files = [

        WEATHER_FILE,
        FORECAST_FILE,
        ACTUAL_FILE,
        PREVIOUS_RUNS_FILE,
        ACCURACY_FILE
    ]

    for file in files:

        if file.exists():

            try:

                df = pd.read_csv(
                    file
                )

                print(
                    f"{file.name:<28}"
                    f"{len(df):>8} rows"
                )

            except Exception:

                print(
                    f"{file.name:<28}"
                    "UNREADABLE"
                )

        else:

            print(
                f"{file.name:<28}"
                "NOT CREATED"
            )

    print("=" * 55)



def main():

    print("=" * 55)
    print("RAIPUR WEATHER TRACKER")
    print("=" * 55)

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        "\n[1/5] Fetching current + forecast data..."
    )

    forecast_data = fetch_weather()

    print(
        "[1/5] Transforming weather data..."
    )

    weather_df = transform_weather(
        forecast_data
    )

    save_weather_data(
        weather_df
    )

    print(
        "[1/5] Creating forecast snapshot..."
    )

    forecast_df = create_forecast_snapshot(
        forecast_data
    )

    save_forecast_snapshot(
        forecast_df
    )


    print(
        "\n[2/5] Fetching historical reference weather..."
    )

    historical_data = fetch_historical_weather()

    print(
        "[2/5] Transforming historical weather..."
    )

    actual_df = transform_historical_weather(
        historical_data
    )

    save_actual_weather(
        actual_df
    )

    print(
        "\n[3/5] Fetching previous forecast runs..."
    )

    previous_runs_data = fetch_previous_runs()

    print(
        "[3/5] Transforming previous runs..."
    )

    previous_runs_df = transform_previous_runs(
        previous_runs_data
    )

    save_previous_runs(
        previous_runs_df
    )

    print(
        "\n[4/5] Calculating forecast accuracy..."
    )

    create_forecast_accuracy()

    print(
        "\n[5/5] Pipeline summary..."
    )

    print_summary()

    print(
        "\nPIPELINE COMPLETED SUCCESSFULLY."
    )


if __name__ == "__main__":

    try:

        main()

    except Exception as e:

        print("\n")
        print("=" * 55)
        print("PIPELINE FAILED")
        print("=" * 55)

        print(
            f"\nError:\n{e}"
        )

        print(
            "\nCheck the API response, "
            "internet connection, and file paths."
        )
