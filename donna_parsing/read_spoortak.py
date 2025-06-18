import json
from queue import PriorityQueue
from dataclasses import dataclass, field
from typing import Any

from data.check_location_scenario_files import check_json_files
from parsedjson import JsonTrackPart, JsonOutput, JsonSignal

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
        self.lint = None
        self.kilometrering = None

    def __str__(self):
        return f'{self.area}-{self.code}'

    def __repr__(self):
        return f'{self.area}|{self.code}'

    def set_kilometrering(self, lint, kilometrering):
        self.lint = lint
        self.kilometrering = int(kilometrering)

class Signal:
    def __init__(self, area, code, side, lint, kilometrering):
        self.area = area
        self.code = code
        self.side = side
        self.lint = lint
        self.kilometrering = int(kilometrering)

    def reverse(self):
        if self.side == "M":
            self.side = "T"
        elif self.side == "T":
            self.side = "M"
        else:
            raise ValueError("Invalid side")

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

num_con = 0

def connect_track_parts(f: JsonTrackPart, t: JsonTrackPart):
    bools = [f.aSide, t.bSide]
    if any([len(side) >= 2 for side in bools]):
        if not (t.id in f.aSide and f.id in t.bSide):
            global num_con
            num_con += 1
            print(num_con, ": ", f, t)
            return

    if (f.id in t.aSide) or (t.id in f.bSide):
        print(f"Woops, loop found between {f} and {t}")

    f.add_a_side(t.id)
    t.add_b_side(f.id)
    # if (len(f.aSide) > 2) or (len(t.aSide) > 2) or len(f.bSide) > 2 or len(t.bSide) > 2:
        # raise ValueError("Too many connections")

class Spoortak:
    def __init__(self, f:Switch, fside, t:Switch, tside):
        self.f = f
        self.fside = fside
        self.t = t
        self.tside = tside
        self.signals: list[Signal] = []

    def add_signal(self, signal: Signal):
        self.signals.append(signal)

    def get_track_sections(self, reverse=False) -> (list[JsonTrackPart], list[JsonSignal]):
        tps = []
        signals = []
        # TODO: Figure out at what kilometrering a switch is
        # start = self.f.kilometrering
        lint = self.f.lint
        start = self.f.kilometrering
        name = repr(self.f) + self.fside
        if self.signals:
            b_side_signal = None
            for signal in self.signals:
                end = get_lint_compensated_kilometrering(signal.kilometrering, signal.lint, lint)
                len = abs(start - end)
                tp = JsonTrackPart(len, f"{name}|{repr(signal)}", False, False, False)

                if tps and reverse:
                    connect_track_parts(tp, tps[-1])
                elif tps:
                    connect_track_parts(tps[-1], tp)
                tps.append(tp)

                if signal.side == "M":
                    sig = JsonSignal(repr(signal), "A", tp.id)
                    signals.append(sig)

                if b_side_signal:
                    sig = JsonSignal(b_side_signal, "B", tp.id)
                    signals.append(sig)
                    b_side_signal = None

                if signal.side == "T":
                    b_side_signal = repr(signal)

                start = signal.kilometrering
                name = repr(signal)
                lint = signal.lint

        # TODO get lint of switch
        tolint = self.t.lint
        end = get_lint_compensated_kilometrering(self.t.kilometrering, lint, tolint)
        len = abs(start - end)
        tp = JsonTrackPart(len, f"{name}|{repr(self.t)}{self.tside}", False, False, False)

        if tps and reverse:
            connect_track_parts(tp, tps[-1])
        elif tps:
            connect_track_parts(tps[-1], tp)
        tps.append(tp)

        return tps, signals

    def __str__(self):
        return f'{self.f}{self.fside}-{self.t}{self.tside}'

    def __repr__(self):
        return f'{self.repr_f()}|{self.repr_t()}'

    def __len__(self):
        start = self.signals[0].kilometrering - 500 if self.signals else -500
        end = self.signals[-1].kilometrering + 500 if self.signals else 500
        lint = self.signals[0].lint if self.signals else None
        tolint = self.signals[-1].lint if self.signals else None
        end = get_lint_compensated_kilometrering(end, lint, tolint)
        return abs(start - end)

    def repr_f(self):
        return f'{repr(self.f)}|{self.fside}'

    def repr_t(self):
        return f'{repr(self.t)}|{self.tside}'

    def reverse(self):
        self.signals = self.signals[::-1]
        for signal in self.signals:
            signal.reverse()
        fside = self.fside
        self.fside = self.tside
        self.tside = fside

        f = self.f
        self.f = self.t
        self.t = f

@dataclass(order=True)
class PrioritizedItem:
    priority: int
    item: Any=field(compare=False)


switches: dict[str, Switch] = dict()
spoortak_start: dict[str, Spoortak] = dict()
spoortak_end: dict[str, Spoortak] = dict()
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
            spoortak_start[tak.repr_f()] = tak
            spoortak_end[tak.repr_t()] = tak
            print(tak)


def read_nonbelegging(filename):
    with open(filename) as f:
        for line in f:
            items = line.strip().split('|')
            if items[3] in ["WISSEL", "STOOTJUK", "TERRA_INCOGNITA"]:
                try:
                    switches[f"{items[0]}{items[2]}"].set_kilometrering(items[4], items[5])
                except KeyError as e:
                    print(f"Did not find {e.args[0]}")

def read_belegging(file):
    with open(file) as f:
        for line in f:
            items = line.strip().split('|')
            if "SEIN" in items[10]:
                track = f"{items[0]}|{items[2]}|{items[4]}"
                if track in spoortak_start:
                    tak = spoortak_start[track]
                    signal = Signal(items[7], items[9], items[11], items[12], items[13])
                    signals.append(signal)
                    tak.add_signal(signal)
                    print(signal)
                else:
                    print(f"Found removed track {track}")

def save_track_sections(filename):
    with open(filename, "w", encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=4, default=lambda o: o.__dict__, sort_keys=True)

def get_track_sections(start_track: str):
    initial_tak = spoortak_start[start_track]

    pq = PriorityQueue()
    pq.put(PrioritizedItem(len(initial_tak), initial_tak))
    tps, signals = initial_tak.get_track_sections()
    json_output.add_track_parts(tps)
    json_output.add_signals(signals)
    track_sections[repr(initial_tak)] = tps

    while not pq.empty():
        item = pq.get()
        priority, tak = item.priority, item.item
        tps = track_sections[repr(tak)]

        # Add a side
        if tak.tside in ["R", "L"]:
            extend_queue_to(pq, f"{repr(tak.t)}|V", tps, priority)
        else:
            extend_queue_to(pq, f"{repr(tak.t)}|R", tps, priority)
            extend_queue_to(pq, f"{repr(tak.t)}|L", tps, priority)

        # # Maybe add b side
        if tak.fside in ["R", "L"]:
            extend_queue_from(pq, f"{repr(tak.f)}|V", tps, priority)
        else:
            extend_queue_from(pq, f"{repr(tak.f)}|R", tps, priority)
            extend_queue_from(pq, f"{repr(tak.f)}|L", tps, priority)

def extend_queue_to(pq: PriorityQueue, tak, tps, priority):
    if tak in spoortak_end:
        next_track = spoortak_end[tak]

        # If the node was already added, don't flip it, but we found a loop
        if repr(next_track) not in track_sections:
            spoortak_start.pop(next_track.repr_f())
            spoortak_end.pop(next_track.repr_t())

            next_track.reverse()

            spoortak_start[next_track.repr_f()] = next_track
            spoortak_end[next_track.repr_t()] = next_track
        else:
            print(f"Loop between: {tps[-1].name} and {repr(next_track)}")

    if tak in spoortak_start:
        next_track = spoortak_start[tak]
        if repr(next_track) not in track_sections:
            next_tps, signals = next_track.get_track_sections()
            connect_track_parts(tps[-1], next_tps[0])
            track_sections[repr(next_track)] = next_tps
            json_output.add_track_parts(next_tps)
            json_output.add_signals(signals)
            pq.put(PrioritizedItem(priority + len(next_track), next_track))
        else:
            next_tps = track_sections[repr(next_track)]
            connect_track_parts(tps[-1], next_tps[0])

def extend_queue_from(pq: PriorityQueue, tak, tps, priority):
    if tak in spoortak_start:
        next_track = spoortak_start[tak]

        # If the node was already added, don't flip it, but we found a loop
        if repr(next_track) not in track_sections:
            spoortak_start.pop(next_track.repr_f())
            spoortak_end.pop(next_track.repr_t())

            next_track.reverse()

            spoortak_start[next_track.repr_f()] = next_track
            spoortak_end[next_track.repr_t()] = next_track
        else:
            print(f"Loop between: {tps[0].name} and {repr(next_track)}")

    if tak in spoortak_end:
        next_track = spoortak_end[tak]
        if repr(next_track) not in track_sections:
            next_tps, signals = next_track.get_track_sections()
            connect_track_parts(next_tps[-1], tps[0])
            track_sections[repr(next_track)] = next_tps
            json_output.add_track_parts(next_tps)
            json_output.add_signals(signals)
            pq.put(PrioritizedItem(priority + len(next_track), next_track))
        else:
            next_tps = track_sections[repr(next_track)]
            connect_track_parts(next_tps[-1], tps[0])


def load_kilometering(filename):
    with open(filename) as f:
        for line in f:
            items = line.strip().split('|')
            kilometrering_dict[f"{items[0]}|{items[1]}"] = (int(items[2]), int(items[3]))



if __name__ == '__main__':
    read_spoortak('data/prorail/donna/DONNA_93451_VER_1_IAUF_SPOORTAK_GEEN_ETCSL2.TXT')
    load_kilometering("data/prorail/donna/DONNA_93451_VER_1_IAUF_NEVENKILOMETRERING.TXT")
    read_nonbelegging("data/prorail/donna/DONNA_93451_VER_1_IAUF_INFRAOBJ_NIETBELEGD.TXT")
    read_belegging('data/prorail/donna/DONNA_93451_VER_1_IAUF_SPOORTAK_BELEGGING.TXT')
    get_track_sections("Shl|1063B|V")
    save_track_sections("data/prorail/parsed/netherlands-schiphol.json")
    for tp in json_output.trackParts:
        print(tp)
    check_json_files("data/prorail/parsed/netherlands-schiphol.json")
