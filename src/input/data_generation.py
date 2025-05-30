import time
from skyfield.api import Topos, load, EarthSatellite
from skyfield.elementslib import osculating_elements_of
import numpy as np
import pandas as pd
from datetime import datetime
import requests
import shelve
import pickle
import hashlib
from filelock import FileLock
from functools import wraps


class SatellitePass:
    def __init__(self, id, nodeId, startTime, endTime, achievableKeyVolume, orbitId):
        self.id = id
        self.nodeId = nodeId
        self.startTime = startTime
        self.endTime = endTime
        self.achievableKeyVolume = achievableKeyVolume
        self.orbitId = orbitId

    def __repr__(self):
        return (
            f"SatellitePass(id={self.id}, nodeId={self.nodeId}, startTime={self.startTime}, "
            f"endTime={self.endTime}, achievableKeyVolume={self.achievableKeyVolume}, orbitId={self.orbitId})"
        )

    def to_dict(self):
        return self.__dict__


ts = load.timescale()

tle_lines = [
    "1 35683U 09041C   25045.14309186  .00001921  00000-0  29495-3 0  9992",
    "2 35683  97.8105 189.5655 0001400  83.0116 277.1253 14.74670943834658",
]


# Define cache file and lock file paths
WEATHER_CACHE_FILE = "./src/input/data/tmp/weather_data_cache.db"
WEATHER_LOCK_FILE = WEATHER_CACHE_FILE + ".lock"


def shelve_weather_cache(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        key_bytes = pickle.dumps((args, kwargs))
        key = hashlib.sha256(key_bytes).hexdigest()

        with FileLock(WEATHER_LOCK_FILE):
            with shelve.open(WEATHER_CACHE_FILE) as db:
                if key in db:
                    print("Weather cache hit")
                    return db[key]

        result = func(*args, **kwargs)

        with FileLock(WEATHER_LOCK_FILE):
            with shelve.open(WEATHER_CACHE_FILE) as db:
                if key not in db:
                    print("Weather cache write")
                    db[key] = result

        return result

    return wrapper


@shelve_weather_cache
def fetch_weather_data_with_cloud_coverage(latitude, longitude, date, max_retries=60):
    response = None

    # Base URL for the Open-Meteo API
    url = "https://archive-api.open-meteo.com/v1/era5"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": date,
        "end_date": date,
        "daily": "sunshine_duration,sunrise,sunset",
        "timezone": "auto",
    }

    # Try making the request with retry mechanism
    retries = 0
    while retries < max_retries:
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                break
            elif response.status_code == 429:
                print(
                    f"Rate limit hit. Retrying in 60 seconds... ({retries+1}/{max_retries})"
                )
                time.sleep(60)
                retries += 1
            else:
                raise Exception(
                    f"Failed to fetch data: {response.status_code}, {response.text} "
                    + f"with location {latitude}, {longitude}, {date}"
                )
        except Exception as e:
            if retries >= max_retries - 1:
                raise Exception(
                    f"Exception in data_generation.py with location {latitude}, {longitude}, {date}. Exception: {e}"
                )
            print(
                f"Request failed. Retrying in 60 seconds... ({retries+1}/{max_retries})"
            )
            time.sleep(60)
            retries += 1

    if response is None or response.status_code != 200:
        raise Exception(
            f"Failed to get a successful response after {max_retries} attempts."
        )

    # Parse the JSON response
    data = response.json()

    # Extract relevant data
    sunrise = data["daily"]["sunrise"][0]
    sunset = data["daily"]["sunset"][0]
    sunshine_duration = data["daily"]["sunshine_duration"][0]  # In seconds

    # Convert sunrise and sunset to datetime objects
    sunrise_time = datetime.fromisoformat(sunrise)
    sunset_time = datetime.fromisoformat(sunset)

    # Calculate the duration between sunrise and sunset in seconds
    daylight_duration_seconds = (sunset_time - sunrise_time).seconds

    # Calculate cloud coverage (1 - sunshine_duration / daylight_duration)
    if daylight_duration_seconds == 0:
        cloud_coverage = 0.5
    else:
        cloud_coverage = 1 - (sunshine_duration / daylight_duration_seconds)

    # Convert sunshine duration to hours for easier interpretation
    sunshine_duration_hours = sunshine_duration / 3600

    return {
        "date": date,
        "latitude": latitude,
        "longitude": longitude,
        "sunrise": sunrise_time,
        "sunset": sunset_time,
        "sunshine_duration_hours": sunshine_duration_hours,
        "daylight_duration_hours": daylight_duration_seconds
        / 3600,  # Convert seconds to hours
        "cloud_coverage_fraction": cloud_coverage,  # Value between 0 (clear) and 1 (fully cloudy)
    }


def convert_and_sort_dataframe_to_satellite_passes(df_satellite_passes):
    # Convert DataFrame rows to SatellitePass objects
    satellite_passes = []
    for idx, row in df_satellite_passes.iterrows():
        satellite_pass = SatellitePass(
            id=idx,
            nodeId=row["Station"],
            startTime=row["Start"],
            endTime=row["End"],
            achievableKeyVolume=row["Key Volume"],
            orbitId=row["Orbit"],
        )
        satellite_passes.append(satellite_pass.to_dict())

    # Sort the SatellitePass objects by startTime
    satellite_passes.sort(key=lambda sp: sp["startTime"])
    return satellite_passes


CACHE_FILE = "./src/input/data/tmp/satellite_passes_cache.db"
LOCK_FILE = CACHE_FILE + ".lock"


def shelve_cache(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Serialize args/kwargs to create a unique cache key
        key_bytes = pickle.dumps((args, kwargs))
        key = hashlib.sha256(key_bytes).hexdigest()

        # Use file lock for thread/process safety
        with FileLock(LOCK_FILE):
            with shelve.open(CACHE_FILE) as db:
                if key in db:
                    print("Satellite pass cache hit")
                    return db[key]

        # Compute result outside lock to avoid holding it for long
        result = func(*args, **kwargs)

        # Store result
        with FileLock(LOCK_FILE):
            with shelve.open(CACHE_FILE, writeback=True) as db:
                if key not in db:
                    print("Satellite pass cache write")
                    db[key] = result

        return result

    return wrapper


@shelve_cache
def get_satellite_passes(
    ground_terminals, start_time, end_time, step_duration, min_elevation_angle
):
    # Load the satellite
    satellite = EarthSatellite(tle_lines[0], tle_lines[1], "Satellite", ts)

    # Compute orbital period in seconds
    earth = satellite.at(ts.now())
    elements = osculating_elements_of(earth)
    orbit_duration = elements.period_in_days * 24 * 60 * 60

    # Function that assigns a satellite pass to an orbit
    def assign_orbit(row):
        # Calculate the time difference between the start of the pass and the orbit start time
        orbit_start_time = start_time
        pass_start_time = pd.to_datetime(row["Start"])
        time_difference = (pass_start_time - orbit_start_time).total_seconds()
        # Calculate orbit ID
        orbit_id = int(time_difference // orbit_duration)
        return orbit_id

    # Calculate key volume using approximation
    def calculate_key_volume(row):
        # Approximated key rate depending on elevation angle of satellite
        def key_rate_approximation(elevation):
            return (
                -0.0145 * (elevation**3)
                + 2.04 * (elevation**2)
                - 20.65 * elevation
                + 88.42
            )

        elevation_angles = row["Elevations"]
        key_rates = [key_rate_approximation(e) for e in elevation_angles]
        key_volume = sum(rate * step_duration for rate in key_rates)  # Volume in bits

        # Adjust key volume depending on cloud coverage
        terminal = row["Station"]
        lat = ground_terminals[terminal]["lat"]
        lon = ground_terminals[terminal]["lon"]
        date = row["Start"]
        # Parse the string into a datetime object
        date_object = datetime.strptime(row["Start"], "%Y-%m-%dT%H:%M:%S")
        # Format the datetime object to 'YYYY-MM-DD'
        date = date_object.strftime("%Y-%m-%d")

        # Fetch weather data
        api_result = fetch_weather_data_with_cloud_coverage(lat, lon, date)
        cloud_coverage_fraction = api_result["cloud_coverage_fraction"]

        if api_result["sunrise"] <= date_object <= api_result["sunset"]:
            print("#######")
            print(api_result["sunrise"])
            print(api_result["sunset"])
            print(date_object)
            return 0
        else:
            # Use cloud coverage to adjust key volume
            return key_volume * (1 - cloud_coverage_fraction)

    # Calculate Passes for Each Ground Terminal
    print("Calculating satellite passes ...")

    passes_data = []
    for terminal, position in ground_terminals.items():
        ground_station = Topos(
            latitude_degrees=position["lat"],
            longitude_degrees=position["lon"],
            elevation_m=position["alt"],
        )
        observer = satellite - ground_station

        # Create evenly spaced time steps
        time_steps = np.arange(start_time, end_time, np.timedelta64(step_duration, "s"))

        # Convert numpy datetime64 to datetime and then to Skyfield time objects
        skyfield_times = ts.utc(
            [t.astype(datetime).year for t in time_steps],
            [t.astype(datetime).month for t in time_steps],
            [t.astype(datetime).day for t in time_steps],
            [t.astype(datetime).hour for t in time_steps],
            [t.astype(datetime).minute for t in time_steps],
            [t.astype(datetime).second for t in time_steps],
        )
        elevation_angles = []
        for time in skyfield_times:
            alt, az, distance = observer.at(time).altaz()
            elevation_angles.append((time.utc_iso().replace("Z", ""), alt.degrees))

        # Filter for Above Horizon Passes
        elevation_angles = [
            (t, e) for t, e in elevation_angles if e >= min_elevation_angle
        ]

        # Group into Passes
        current_pass = []
        for t, e in elevation_angles:
            if (
                not current_pass
                or (
                    datetime.fromisoformat(t)
                    - datetime.fromisoformat(current_pass[-1][0])
                ).seconds
                <= 30
            ):
                current_pass.append((t, e))
            else:
                if current_pass:
                    passes_data.append({"station": terminal, "pass": current_pass})
                current_pass = [(t, e)]
        if current_pass:
            passes_data.append({"station": terminal, "pass": current_pass})

    # Convert to DataFrame
    satellite_passes = []
    for pass_info in passes_data:
        station = pass_info["station"]
        times, elevations = zip(*pass_info["pass"])
        satellite_passes.append(
            {
                "Station": station,
                "Start": times[0],
                "End": times[-1],
                "Elevations": elevations,
            }
        )
    df_satellite_passes = pd.DataFrame(satellite_passes)

    # Calculate approximated key volume
    print("Calculating key volumes ...")
    df_satellite_passes["Key Volume"] = df_satellite_passes.apply(
        calculate_key_volume, axis=1
    )
    df_satellite_passes = df_satellite_passes.drop("Elevations", axis=1)

    # Calculate orbits
    print("Calculating orbits ...")
    df_satellite_passes["Orbit"] = df_satellite_passes.apply(assign_orbit, axis=1)
    # print(df_satellite_passes)

    # Convert satellite passes dataframe to list of satellite pass objects
    satellite_passes_dict_list = convert_and_sort_dataframe_to_satellite_passes(
        df_satellite_passes
    )

    return satellite_passes_dict_list
