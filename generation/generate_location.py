import sys

class TrackPart:
    __last_id = 1

    def __init__(self, length, name, sawMovement, parkingAllowed, stationPlatform, trackType):
        self.id = TrackPart.__last_id
        TrackPart.__last_id += 1
        self.length = length
        self.name = name
        self.sawMovement = sawMovement
        self.parkingAllowed = parkingAllowed
        self.stationPlatform = stationPlatform
        self.type = trackType
        self.aSide = []
        self.bSide = []

    def __str__(self):
        return f"{self.type} : {self.name}"

    def __repr__(self):
        return f"<TrackPart id:{self.id} length:{self.length} name:{self.name} sawMovement:{self.sawMovement} parkingAllowed:{self.parkingAllowed} stationPlatform:{self.stationPlatform} type:{self.type}, aSide:{self.aSide}, bSide:{self.bSide}>"

def defaultFalse(inp):
    out = input(f"{inp} ([t]rue/[F]alse): ")
    return False if len(out) == 0 else out[0].lower() == "t"

def main():
    print("Location generation program, [t]rack, [c]onnection, [s]ave")
    track_parts = []
    for line in sys.stdin:
        if 'q' == line.strip():
            break
        if 't' == line.strip():
            track_parts.extend(track_part())
        if 'c' == line.strip():
            connections()
        if 's' == line.strip():
            save()
        print("Location generation program, [t]rack, [c]onnection, [s]ave")
    print("Exit")

def track_part():
    print("Create a new track part")
    name = input("Name: ")
    length = input("Length: ")
    parkingAllowed = False
    sawMovement = False
    stationPlatform = False

    # If name starts with a t, it can be a station, turnaround station or parking spot
    if name[0].lower() == "t":
        sawMovement = defaultFalse("Saw movement")
        parkingAllowed = defaultFalse("Parking allowed")
        stationPlatform = defaultFalse("Station platform")

    trackType = "RailRoad"
    # Determine type of switch if it's a switch
    if name[0].lower() == "s":
        trackType = input("Track type ([S]witch/[e]nglishSwitch): ")
        if len(trackType) == 0:
            trackType = "Switch"
        else:
            first_letter = trackType[0].lower()
            trackType = "EnglishSwitch" if first_letter == "e" else "Switch"

    #     TODO: create bumper track parts
    tp = TrackPart(length, name, sawMovement, parkingAllowed, stationPlatform, trackType)
    print(f"Create a new track part: {repr(tp)}")
    return [tp]

def connections():
    print("Create a new connection between two track parts")

def save():
    print("Save the track part")

if __name__ == '__main__':
    main()