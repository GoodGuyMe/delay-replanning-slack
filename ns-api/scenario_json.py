from json import JSONEncoder

class JsonScenario(JSONEncoder):
    def __init__(self):
        self.types = []
        self.trains = []
        self.headwayFollowing = 180
        self.headwayCrossing = 120
        self.walkingSpeed = 1.4
        self.releaseTime = 20
        self.setupTime = 20
        self.sightReactionTime = 10
        self.minimumStopTime = 100

    def add_type(self, name, length, speed, acceleration, deceleration, minimum_station_time):
        self.types.append({
            'name': name,
            'length': length,
            'speed': speed,
            'acceleration': acceleration,
            'deceleration': deceleration,
            'minimum_station_time': minimum_station_time,
        })

    def add_train(self, train_number, train_units, train_type, movements):
        self.trains.append({
            'trainNumber': train_number,
            'trainUnits': train_units,
            'trainUnitTypes': train_type,
            'movements': movements
        })

class JsonMovements(JSONEncoder):
    def __init__(self, stops):
        self.startLocation = stops[0]["location"]
        self.startTime = stops[0]["time"]
        self.endLocation = stops[-1]["location"]
        self.endTime = stops[-1]["time"]
        self.stops = stops[1:-1]

