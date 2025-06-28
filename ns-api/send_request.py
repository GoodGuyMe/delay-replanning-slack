import json
import os
import random
from datetime import datetime, timezone, timedelta
from dateutil import parser

import requests
import pandas as pd

from scenario_json import JsonScenario, JsonMovements

start_time = datetime.now(tz=timezone(timedelta(hours=+2)))
start_time = start_time.replace(second=0, microsecond=0)

departures_url = "https://gateway.apiportal.ns.nl/reisinformatie-api/api/v2/departures?"
journey_url = "https://gateway.apiportal.ns.nl/reisinformatie-api/api/v2/journey?"
headers = {"Accept": "application/json", "Cache-Control": "no-cache", "Ocp-Apim-Subscription-Key": os.environ.get("Ocp-Apim")}
csv_file = "stations-2023-09.csv"

df = pd.read_csv(csv_file, sep=",")

def get_departures(station):
    url = f"{departures_url}station={station}"
    request = requests.get(url, headers=headers)
    return request.json()

def get_train_route(train):
    url = f"{journey_url}train={train}"
    request = requests.get(url, headers=headers)
    return request.json()

def parse_stop(stop):
    station = df.loc[df['uic'] == int(stop["stop"]["uicCode"]), "code"].iloc[0]
    departures = stop["departures"]
    arrivals = stop["arrivals"]
    if len(departures) == 0:
        if len(arrivals) == 0:
            print(f"ERROR, no departures or arrivals for {stop}")
            return f"Not in the netherlands", -1, -1
        print(f"Using arrival time as {stop['status']}")
        departures = arrivals
    if len(departures) > 1:
        print(f"ERROR, using first departure of {departures}")

    if len(arrivals) == 0:
        print(f"Using departure time as {stop['status']}")
        arrivals = departures
    departure_time = parser.parse(departures[0]["plannedTime"])
    arrival_time =   parser.parse(arrivals[0]["plannedTime"])

    offset_departure = (departure_time - start_time).total_seconds()
    offset_arrival = (arrival_time - start_time).total_seconds()
    track = departures[0]["plannedTrack"]
    if "-" in track:
        track = track.split("-")[0]
    return f"{station}|{track}", offset_departure, offset_arrival

def get_units(stop):
    try:
        type = [stop["plannedStock"]["trainType"]]
        units = []
        for part in stop["plannedStock"]["trainParts"]:
            units.append(part["stockIdentifier"])
        return units, type
    except Exception:
        return [0], ["UNKNOWN"]

def save_scenario(filename, scenario):
    with open(filename, "w", encoding='utf-8') as f:
        json.dump(scenario, f, ensure_ascii=False, indent=4, default=lambda o: o.__dict__, sort_keys=True)

if __name__ == "__main__":
    scenario = JsonScenario()
    trains = set()
    filter_traintypes = {"EUROSTAR"}
    stations = ["Shl", "Ledn", "Gv", "Dt"]

    for station in stations:
        response = get_departures(station)

        for departure in response["payload"]["departures"]:
            train = departure["product"]
            trains.add(train["number"])

    for train in trains:
        route = get_train_route(train)
        filtered_stops = []
        for stop in route["payload"]["stops"]:
            if stop["status"] != "PASSING":
                key, depart, arrive = parse_stop(stop)
                if depart > 0:
                    if key == "ASD|15a":
                        key = "ASD|13a"
                    if key == "ASD|14a":
                        key = "ASD|11a"
                    filtered_stops.append({"location": key, "time": depart, "expected_arrival": arrive})
        if len(filtered_stops) <= 1:
            print(f"Train is at the end of the stop at it's current time {route}")
            continue
        movements = [JsonMovements(filtered_stops)]
        unit, unit_types = get_units(route["payload"]["stops"][0])
        if len(set(unit_types) & filter_traintypes) == 0:
            scenario.add_train(train, unit, unit_types, movements)
        else:
            print(f"Train is of type {unit_types}")

    scenario.add_type("ICNG", 138, 200, 0.5, 1.1)
    scenario.add_type("EUROSTAR", 138, 200, 0.5, 1.1)
    scenario.add_type("SNG", 169, 140, 1.1, 1.1)
    scenario.add_type("SLT", 169, 140, 0.9, 1.1)
    scenario.add_type("VIRM", 138, 140, 0.7, 1.1)
    scenario.add_type("DDZ", 138, 140, 0.9, 1.1)
    scenario.add_type("ICM", 138, 140, 0.7, 1.1)
    scenario.add_type("ICD", 138, 140, 0.7, 1.1)
    scenario.add_type("UNKNOWN", 138, 140, 1, 1.1)
    save_scenario(f"../data/prorail/scenarios/SHL.json", scenario)