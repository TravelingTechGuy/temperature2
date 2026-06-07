import time
from collections import defaultdict
from datetime import datetime, timezone
from arduino.app_utils import App, Bridge
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.dbstorage_tsstore import TimeSeriesStore

MEASUREMENT_NAME = "weather"

db = TimeSeriesStore()
db.start()

# globals
DeviceUnits = "F"
IntervalInSeconds = 300    #default is 300sec == 5min

# get sensor data from hardware side
def getTemperatureData():
    response = Bridge.call("get_sensor_data")
    if response:
        celsius, fahrenheit, humidity = response
        print(f"Celsius: {celsius:.2f}\tFahrenheit: {fahrenheit:.2f}\tHumidity: {humidity:.2f}")
        return response
    else:
        print("Could not retrieve sensor metrics.")
        return None

def writeToDB(sample):
    celsius, fahrenheit, humidity = sample

    # One timestamp shared by all values
    ts = int(time.time_ns() / 1_000_000)

    db.write_sample(measure="celsius", value=celsius, ts=ts, measurement_name=MEASUREMENT_NAME)
    db.write_sample(measure="fahrenheit", value=fahrenheit, ts=ts, measurement_name=MEASUREMENT_NAME)
    db.write_sample(measure="humidity", value=humidity, ts=ts, measurement_name=MEASUREMENT_NAME)

    return ts

def readFromDB(hours):
    start_from = f"-{hours}h"
    merged = defaultdict(dict)

    for measure in ["celsius", "fahrenheit", "humidity"]:
        data = db.read_samples(measure=measure, measurement_name=MEASUREMENT_NAME, start_from=start_from, limit=100000)
        for _, ts, value in data:
            merged[ts][measure] = value

    samples = [
        {
            "timestamp": ts,
            "celsius": values.get("celsius"),
            "fahrenheit": values.get("fahrenheit"),
            "humidity": values.get("humidity"),
        }
        for ts, values in sorted(merged.items())
    ]

    return samples

# toggle F/C
def toggleDeviceUnits():
    global DeviceUnits
    DeviceUnits = "C" if DeviceUnits == "F" else "F"
    print(f"Degrees changed to {DeviceUnits}")
    Bridge.call("set_device_units", DeviceUnits)
    return {"units": DeviceUnits}

# API call
def getTemp():
    response = getTemperatureData()
    if not response:
        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "celsius": 0,
            "fahrenheit": 0,
            "humidity": 0
        }
    celsius, fahrenheit, humidity = response
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "celsius": celsius,
        "fahrenheit": fahrenheit,
        "humidity": humidity
    }

def getHistory(hours: int = 4):
    samples = readFromDB(hours)
    return {
        "hours": hours,
        "count": len(samples),
        "samples": samples,
    }

def setInterval(interval: int = 300):
    global IntervalInSeconds
    IntervalInSeconds = interval
    return {"intervalInSeconds": IntervalInSeconds}

# set up web interface
ui = WebUI()
ui.expose_api("GET", "/temp", getTemp)
ui.expose_api("GET", "/history", getHistory)
ui.expose_api("GET", "/units", lambda: {"units": DeviceUnits})
ui.expose_api("GET", "/setUnits", toggleDeviceUnits)
ui.expose_api("GET", "/interval", lambda: {"intervalInSeconds": IntervalInSeconds})
ui.expose_api("GET", "/setInterval", setInterval)

def loop():
    # get sample data every interval, and write to database
    response = getTemperatureData()
    if response:
        writeToDB(response)
    time.sleep(IntervalInSeconds)

App.run(user_loop=loop)
