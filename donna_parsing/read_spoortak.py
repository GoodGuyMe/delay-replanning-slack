import json

from parsedjson import JsonTrackPart, JsonOutput

class Switch:
    def __init__(self, area, code):
        self.area = area
        self.code = code
        self.kilometrering = 0

    def __str__(self):
        return f'{self.area}-{self.code}'

    def __repr__(self):
        return f'{self.area}|{self.code}'

class Signal:
    def __init__(self, area, code, side, lint, kilometrering):
        self.area = area
        self.code = code
        self.side = side
        self.lint = lint
        self.kilometrering = int(kilometrering)

    def __str__(self):
        return f'{self.code}{self.side} - {self.lint}:{self.kilometrering}'

    def __repr__(self):
        return f'{self.area}|{self.code}'

def Connect_Track_Parts(left: JsonTrackPart, right: JsonTrackPart):
    left.add_a_side(right.id)
    right.add_b_side(left.id)

class Spoortak:
    def __init__(self, f:Switch, fside, t:Switch, tside):
        self.f = f
        self.fside = fside
        self.t = t
        self.tside = tside
        self.signals: list[Signal] = []

    def add_signal(self, signal: Signal):
        self.signals.append(signal)

    def get_track_sections(self) -> list[JsonTrackPart]:
        tps = []
        # TODO: Figure out at what kilometrering a switch is
        start = self.f.kilometrering
        startName = repr(self.f)
        if self.signals:
            for signal in self.signals:
                # TODO: Check lint
                len = abs(start - signal.kilometrering)
                tp = JsonTrackPart(len, f"{startName}|{repr(signal)}", False, False, False)

                if tps:
                    Connect_Track_Parts(tps[-1], tp)
                tps.append(tp)

                start = signal.kilometrering
                startName = repr(signal)

        len = abs(start - self.t.kilometrering)
        tp = JsonTrackPart(len, f"{startName}|{repr(self.t)}", False, False, False)

        if tps:
            tps[-1].add_a_side(tp.id)
            tp.add_b_side(tps[-1].id)
        tps.append(tp)

        return tps

    def __str__(self):
        return f'{self.f}{self.fside}-{self.t}{self.tside}'

    def __repr__(self):
        return f'{repr(self.f)}|{self.fside}'


switches: dict[str, Switch] = dict()
spoortakken: dict[str, Spoortak] = dict()
signals: list[Signal] = list()
track_sections: dict[str, list[JsonTrackPart]] = dict()
json_output = JsonOutput()

def add_if_new(switch: Switch) -> Switch:
    if f"{switch.area}{switch.code}" in switches:
        switch = switches[f"{switch.area}{switch.code}"]
    else:
        switches[f"{switch.area}{switch.code}"] = switch
    return switch

def read_spoortak(file):
    with open(file) as f:
        for line in f:
            items = line.strip().split('|')
            fromtak = add_if_new(Switch(items[0], items[2]))
            totak   = add_if_new(Switch(items[5], items[7]))

            tak = Spoortak(fromtak, items[4], totak, items[9])
            spoortakken[repr(tak)] = tak
            print(tak)

def read_belegging(file):
    with open(file) as f:
        for line in f:
            items = line.strip().split('|')
            if "SEIN" in items[10]:
                tak = spoortakken[f"{items[0]}|{items[2]}|{items[4]}"]
                signal = Signal(items[7], items[9], items[11], items[12], items[13])
                signals.append(signal)
                tak.add_signal(signal)
                print(signal)

def get_track_sections():
    for tak in spoortakken.values():
        tps = tak.get_track_sections()
        if tak.fside == "V":
            if f"{repr(tak.f)}R" in track_sections:
                connecting_tps = track_sections[f"{repr(tak.f)}R"]
                Connect_Track_Parts(connecting_tps[-1], tps[0])
            if f"{repr(tak.f)}L" in track_sections:
                connecting_tps = track_sections[f"{repr(tak.f)}L"]
                Connect_Track_Parts(connecting_tps[-1], tps[0])

        if tak.fside == "R" or tak.fside == "L":
            if f"{repr(tak.f)}V" in track_sections:
                connecting_tps = track_sections[f"{repr(tak.f)}V"]
                Connect_Track_Parts(connecting_tps[-1], tps[0])

        if tak.tside == "V":
            if f"{repr(tak.t)}R" in track_sections:
                connecting_tps = track_sections[f"{repr(tak.t)}R"]
                Connect_Track_Parts( tps[-1], connecting_tps[0])
            if f"{repr(tak.t)}L" in track_sections:
                connecting_tps = track_sections[f"{repr(tak.t)}L"]
                Connect_Track_Parts( tps[-1], connecting_tps[0])

        if tak.tside == "R" or tak.tside == "L":
            if f"{repr(tak.t)}V" in track_sections:
                connecting_tps = track_sections[f"{repr(tak.t)}V"]
                Connect_Track_Parts( tps[-1], connecting_tps[0])

        track_sections[f"{repr(tak.f)}{tak.fside}"] = tps
        track_sections[f"{repr(tak.t)}{tak.tside}"] = tps
        json_output.add_track_parts(tps)


def save_track_sections(filename):
    with open(f"data/prorail/parsed/{filename}.json", "w", encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=4, default=lambda o: o.__dict__, sort_keys=True)


if __name__ == '__main__':
    read_spoortak('data/prorail/donna/DONNA_93451_VER_1_IAUF_SPOORTAK.TXT')
    read_belegging('data/prorail/donna/DONNA_93451_VER_1_IAUF_SPOORTAK_BELEGGING.TXT')
    get_track_sections()
    save_track_sections("test1")

    for tp in json_output.trackParts:
        print(tp)