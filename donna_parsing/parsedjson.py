import json
from json import JSONEncoder


class JsonOutput(JSONEncoder):
    def __init__(self, trackParts=None, facilities=None, taskTypes=None, movementConstant=0, movementTrackCoefficient=0,
                 movementSwitchCoefficient=0, distanceEntries=None, signals=None, distanceMarkers=None):
        if facilities is None:
            facilities = []
        if taskTypes is None:
            taskTypes = []
        if distanceEntries is None:
            distanceEntries = []
        if distanceMarkers is None:
            distanceMarkers = {}
        if signals is None:
            signals = []
        if trackParts is None:
            trackParts = []
        self.trackParts = trackParts
        self.facilities = facilities
        self.taskTypes = taskTypes
        self.movementConstant = movementConstant
        self.movementTrackCoefficient = movementTrackCoefficient
        self.movementSwitchCoefficient = movementSwitchCoefficient
        self.distanceEntries = distanceEntries
        self.distanceMarkers = distanceMarkers
        self.signals = signals

    def add_track_parts(self, trackParts: list):
        self.trackParts.extend(trackParts)

    def add_signals(self, signals: list):
        self.signals.extend(signals)


class JsonTrackPart(JSONEncoder):
    __last_id = 0

    def __init__(self, length, name, sawMovementAllowed, parkingAllowed, stationPlatform):
        self.id = JsonTrackPart.__last_id
        JsonTrackPart.__last_id = JsonTrackPart.__last_id + 1
        self.length = length
        self.name = name + "-"
        self.sawMovementAllowed = sawMovementAllowed
        self.parkingAllowed = parkingAllowed
        self.stationPlatform = stationPlatform
        self.aSide = []
        self.bSide = []
        self.type = None
        self.checktype()

    def checktype(self):
        if len(self.aSide) == 2 and len(self.bSide) == 2:
            self.type = "EnglishSwitch"
        elif len(self.aSide) == 2 or len(self.bSide) == 2:
            self.type = "Switch"
        elif len(self.aSide) == 0 or len(self.bSide) == 0:
            self.type = "Bumper"
        else:
            self.type = "RailRoad"

    def add_a_side(self, trackId):
        if trackId not in self.aSide:
            self.aSide.append(trackId)
            self.checktype()

    def add_b_side(self, trackId):
        if trackId not in self.bSide:
            self.bSide.append(trackId)
            self.checktype()

    def __str__(self):
        return f"{self.id} - {self.type} : {self.name}, l:{self.length}, A:{self.aSide}, B:{self.bSide}"

    def __repr__(self):
        return f"<TrackPart id:{self.id} length:{self.length} name:{self.name} sawMovementAllowed:{self.sawMovementAllowed} parkingAllowed:{self.parkingAllowed} stationPlatform:{self.stationPlatform} type:{self.type}, aSide:{self.aSide}, bSide:{self.bSide}>"


class JsonSignal(JSONEncoder):
    def __init__(self, name, side, track):
        self.name = name
        self.side = side
        self.track = track

