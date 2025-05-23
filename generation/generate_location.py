import sys
import json
from json import JSONEncoder

class OutputJSONEncoder(JSONEncoder):
    def __init__(self, trackParts, facilities=None, taskTypes=None, movementConstant=0, movementTrackCoefficient=0,
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
        self.trackParts = trackParts
        self.facilities = facilities
        self.taskTypes = taskTypes
        self.movementConstant = movementConstant
        self.movementTrackCoefficient = movementTrackCoefficient
        self.movementSwitchCoefficient = movementSwitchCoefficient
        self.distanceEntries = distanceEntries
        self.distanceMarkers = distanceMarkers
        self.signals = signals

    def default(self, o):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class TrackPart(JSONEncoder):
    __last_id = 1

    def __init__(self, length, name, sawMovementAllowed, parkingAllowed, stationPlatform, type, aSide=None, bSide=None,
                 id=None):
        if bSide is None:
            bSide = []
        if aSide is None:
            aSide = []
        if id is None:
            id = TrackPart.__last_id
        self.id = id
        TrackPart.__last_id = max(TrackPart.__last_id, id + 1)
        self.length = length
        self.name = name
        self.sawMovementAllowed = sawMovementAllowed
        self.parkingAllowed = parkingAllowed
        self.stationPlatform = stationPlatform
        self.type = type
        self.aSide = aSide
        self.bSide = bSide


    def __str__(self):
        return f"{self.type} : {self.name}"

    def __repr__(self):
        return f"<TrackPart id:{self.id} length:{self.length} name:{self.name} sawMovementAllowed:{self.sawMovementAllowed} parkingAllowed:{self.parkingAllowed} stationPlatform:{self.stationPlatform} type:{self.type}, aSide:{self.aSide}, bSide:{self.bSide}>"

    def default(self, o):
        if isinstance(o, TrackPart):
            return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
        return json.JSONEncoder.default(self, o)

class Signal(JSONEncoder):
    def __init__(self, name, side, track):
        self.name = name
        self.side = side
        self.track = track

    def default(self, o):
        if isinstance(o, Signal):
            return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
        return json.JSONEncoder.default(self, o)

def defaultFalse(inp):
    out = input(f"{inp} ([t]rue/[F]alse): ")
    return False if len(out) == 0 else out[0].lower() == "t"


def main():
    print("Location generation program, [t]rack, [c]onnection, s[e]in, [d]istance marker, [s]ave, [l]oad")
    track_parts = dict()
    distance_markers = dict()
    signals = list()
    for line in sys.stdin:
        c = line.strip()[0]
        if 'q' == c:
            break
        elif 't' == c:
            for tp in track_part():
                track_parts[tp.name] = tp
        elif 'c' == c:
            connections(track_parts)
        elif 's' == c:
            save(track_parts, signals, distance_markers)
        elif 'l' == c:
            track_parts = dict()
            tps, signals, distance_markers = load()
            for tp in tps:
                track_parts[tp.name] = tp
        elif 'd' == c:
            create_distance_markers(distance_markers)
        elif 'e' == c:
            signals.extend(add_signals(track_parts))
        print("Location generation program, [t]rack, [c]onnection, s[e]in, [d]istance marker, [s]ave")
    print("Exit")

def track_part():
    print("Create a new track part")
    name = input("Name: ")
    length = int(input("Length: "))
    parkingAllowed = False
    sawMovement = False
    stationPlatform = False

    # If name starts with a t, it can be a station, turnaround station or parking spot
    # if name[0].lower() == "t":
    #     sawMovement = defaultFalse("Saw movement")
    #     parkingAllowed = defaultFalse("Parking allowed")
    #     stationPlatform = defaultFalse("Station platform")

    trackType = "RailRoad"
    # Determine type of switch if it's a switch
    # if name[0].lower() == "s":
    #     trackType = input("Track type ([S]witch/[e]nglishSwitch): ")
    #     if len(trackType) == 0:
    #         trackType = "Switch"
    #     else:
    #         first_letter = trackType[0].lower()
    #         trackType = "EnglishSwitch" if first_letter == "e" else "Switch"

    #     TODO: create bumper track parts
    tp = TrackPart(length, name, sawMovement, parkingAllowed, stationPlatform, trackType)
    print(f"Create a new track part: {repr(tp)}")
    return [tp]


def checktype(track_part):
    if len(track_part.aSide) == 2 and len(track_part.bSide) == 2:
        track_part.type = "EnglishSwitch"
    elif len(track_part.aSide) == 2 or len(track_part.bSide) == 2:
        track_part.type = "Switch"


def connections(track_parts):
    print("Create a new connection between two track parts")
    print("Give connection as: track_name_a track_name_b")
    for i in track_parts.values():
        print(f"{i}")
    try:
        for line in sys.stdin:
            if 'q' == line.strip():
                break
            new_connection = line.strip().split(" ")
            if len(new_connection) != 2:
                continue
            t1 = new_connection[0]
            t2 = new_connection[1]
            track_parts[t1].aSide.append(track_parts[t2].id)
            track_parts[t2].bSide.append(track_parts[t1].id)
            checktype(track_parts[t1])
            checktype(track_parts[t2])
            print(f"Added connection between {track_parts[t1]} and {track_parts[t2]}")
    except Exception as e:
        print(e)
        connections(track_parts)


def add_signals(track_parts):
    new_signals = []
    print("Create new signals")
    while True:
        try:
            name = input("Signal name/id: ")
            if (name.strip() == "q"):
                return new_signals
            print("A or B side, B side is in increasing kilometrage")
            side = input("Side: ").strip()
            track = input("Signal at end of track part: ").strip()
            new_signals.append(Signal(name, side, track_parts[track].id))
        except Exception as e:
            print(e)
            print("Invalid track name")

def create_distance_markers(distance_markers):
    print("Create distance marker by {name} {km}")

    for line in sys.stdin:
        if 'q' == line.strip():
            break
        new_connection = line.strip().split(" ")
        if len(new_connection) != 2:
            continue
        name = new_connection[0]
        km = int(new_connection[1].replace(".", ""))
        distance_markers[name] = km

def save(track_parts, signals, distance_markers):
    print("Save the track part")
    filename = input("Filename: ")
    with open(f"{filename}.json", "w", encoding='utf-8') as f:
        output = OutputJSONEncoder(list(track_parts.values()),
                                   signals=signals,
                                   distanceMarkers=distance_markers)
        json.dump(output, f, ensure_ascii=False, indent=4, default=lambda o: o.__dict__, sort_keys=True)

def object_load(obj):
    # if len(obj) == 9:
    try:
        return TrackPart(**obj)
    except TypeError:
        try:
            return OutputJSONEncoder(**obj)
        except TypeError:
            try:
                return Signal(**obj)
            except TypeError:
                return obj


def load():
    print("Load the track part")
    filename = input("Filename: ")
    with open(f"{filename}.json", "r", encoding='utf-8') as f:
        data = json.load(f, object_hook=object_load)
    return data.trackParts, data.signals, data.distanceMarkers

if __name__ == '__main__':
    main()