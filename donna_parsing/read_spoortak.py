import json

from data.check_location_scenario_files import check_json_files
from parsedjson import JsonTrackPart, JsonOutput

kilometrering_dict: dict[str, tuple] = dict()
json_output = JsonOutput()

def get_lint_compensated_kilometrering(kilometrering, lint_from, lint_to):
    if lint_from == lint_to:
        return kilometrering

    offset, sign = kilometrering_dict[f"{lint_from}|{lint_to}"]
    return (kilometrering + offset) * sign


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

def split_name(tp: JsonTrackPart):
    name = tp.name[0:-1]
    tps = name.split('|')
    f = f"{tps[0]}|{tps[1]}"
    t = f"{tps[2]}|{tps[3]}"
    return f, t

def get_connecting_track_part(tps: list[JsonTrackPart], connection: str, to: JsonTrackPart) -> tuple[JsonTrackPart, JsonTrackPart]:
    if split_name(tps[0])[0] == connection:
        return to, tps[0]
    if split_name(tps[-1])[1] == connection:
        return tps[-1], to
    raise ValueError("This should not happen! figure out whats wrong")

def connect_track_parts(f: JsonTrackPart, t: JsonTrackPart):
    f.add_a_side(t.id)
    t.add_b_side(f.id)
    # if (len(f.aSide) > 2) or (len(t.aSide) > 2) or len(f.bSide) > 2 or len(t.bSide) > 2:
    #     raise ValueError("Too many connections")

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
        # start = self.f.kilometrering
        start = self.signals[0].kilometrering - 500 if self.signals else -500
        name = repr(self.f) + self.fside
        lint = self.signals[0].lint if self.signals else None
        if self.signals:
            for signal in self.signals:
                end = get_lint_compensated_kilometrering(signal.kilometrering, signal.lint, lint)
                len = abs(start - end)
                tp = JsonTrackPart(len, f"{name}|{repr(signal)}", False, False, False)

                if tps:
                    connect_track_parts(tps[-1], tp)
                tps.append(tp)

                start = signal.kilometrering
                name = repr(signal)
                lint = signal.lint

        # TODO get lint of switch
        end = self.signals[-1].kilometrering + 500 if self.signals else 500
        tolint = self.signals[-1].lint if self.signals else None
        end = get_lint_compensated_kilometrering(end, lint, tolint)
        len = abs(start - end)
        tp = JsonTrackPart(len, f"{name}|{repr(self.t)}{self.tside}", False, False, False)

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
                connect_track_parts(*get_connecting_track_part(connecting_tps, f"{repr(tak.f)}R", tps[0]))
            if f"{repr(tak.f)}L" in track_sections:
                connecting_tps = track_sections[f"{repr(tak.f)}L"]
                connect_track_parts(*get_connecting_track_part(connecting_tps, f"{repr(tak.f)}L", tps[0]))

        if tak.fside == "R" or tak.fside == "L":
            if f"{repr(tak.f)}V" in track_sections:
                connecting_tps = track_sections[f"{repr(tak.f)}V"]
                connect_track_parts(*get_connecting_track_part(connecting_tps, f"{repr(tak.f)}V", tps[0]))

        if tak.tside == "V":
            if f"{repr(tak.t)}R" in track_sections:
                connecting_tps = track_sections[f"{repr(tak.t)}R"]
                connect_track_parts(*get_connecting_track_part(connecting_tps, f"{repr(tak.t)}R", tps[-1]))
            if f"{repr(tak.t)}L" in track_sections:
                connecting_tps = track_sections[f"{repr(tak.t)}L"]
                connect_track_parts(*get_connecting_track_part(connecting_tps, f"{repr(tak.t)}L", tps[-1]))

        if tak.tside == "R" or tak.tside == "L":
            if f"{repr(tak.t)}V" in track_sections:
                connecting_tps = track_sections[f"{repr(tak.t)}V"]
                connect_track_parts(*get_connecting_track_part(connecting_tps, f"{repr(tak.t)}V", tps[-1]))

        track_sections[f"{repr(tak.f)}{tak.fside}"] = tps
        track_sections[f"{repr(tak.t)}{tak.tside}"] = tps
        json_output.add_track_parts(tps)


def load_kilometering(filename):
    with open(filename) as f:
        for line in f:
            items = line.strip().split('|')
            kilometrering_dict[f"{items[0]}|{items[1]}"] = (int(items[2]), int(items[3]))

def save_track_sections(filename):
    with open(filename, "w", encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=4, default=lambda o: o.__dict__, sort_keys=True)


if __name__ == '__main__':
    read_spoortak('data/prorail/donna/DONNA_93451_VER_1_IAUF_SPOORTAK.TXT')
    load_kilometering("data/prorail/donna/DONNA_93451_VER_1_IAUF_NEVENKILOMETRERING.TXT")
    read_belegging('data/prorail/donna/DONNA_93451_VER_1_IAUF_SPOORTAK_BELEGGING.TXT')
    get_track_sections()
    save_track_sections("data/prorail/parsed/test1.json")
    check_json_files("data/prorail/parsed/test1.json")

    for tp in json_output.trackParts:
        print(tp)