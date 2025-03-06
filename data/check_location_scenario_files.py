import json
import sys
from pathlib import Path

sys.path.insert(1, '../generation')
import generate

def check_json_files(loc_file, scen_file=None, show_error=True, show_warning=False, show_intervals=True,):
    print(f"\n### Processing {loc_file}")
    base_path = Path(__file__).parent
    file_path = (base_path / loc_file).resolve()
    g, g_block = generate.read_graph(loc_file)
    location = json.load(open(file_path))
    check_location(location, g, show_error, show_warning)
    if scen_file is not None:
        print(f"### Processing {scen_file}")
        base_path = Path(__file__).parent
        file_path = (base_path / scen_file).resolve()
        scenario = json.load(open(file_path))  
        check_scenario(scenario, location, g, show_error, show_warning, show_intervals)


def check_location(location, g, show_error, show_warning):
    errors = []
    warnings = []
    parts = {}
    names = set()
    for entry in location["trackParts"]:
        id = entry["id"]
        if id in parts:
            errors.append(f"ERROR double id {id}")
        parts[entry["id"]] = entry
        if entry["name"] in names:
            errors.append(f"ERROR name double {entry['name']}")
        names.add(entry["name"])
        if entry["type"] == "RailRoad":
            if entry["name"][0] != "t":
                errors.append(f"ERROR: railroad id {id} has name {entry['name']}")
            if len(entry["aSide"]) != 1:
                errors.append(f"ERROR Railroad id {id} does not have 1 aside: {entry['aSide']}")
            if len(entry["bSide"]) != 1:
                errors.append(f"ERROR Railroad id {id} does not have 1 aside: {entry['bSide']}")                
            if entry["name"][2:] != entry["id"]:
                warnings.append(f"--WARNING name is {entry['name']} but id is {id}")
            if entry["length"] == 0:
                warnings.append(f"--WARNING track length of {id} is 0")
        elif entry["type"] == "Switch":
            if entry["name"][0] != "s":
                errors.append(f"ERROR: switch id {id} has name {entry['name']}")
            if not ((len(entry["aSide"]) == 1 and len(entry["bSide"]) == 2) or (len(entry["aSide"]) == 2 and len(entry["bSide"]) == 1)):
                errors.append(f"ERROR Switch id {id} does not have correct a/b side numbers")              
            if entry["name"][2:] != entry["id"]:
                warnings.append(f"--WARNING name is {entry['name']} but id is {id}")
            if entry["length"] != 100:
                warnings.append(f"--WARNING length of switch {id} is not 100")
        elif entry["type"] == "EnglishSwitch":
            if entry["name"][0] != "s":
                errors.append(f"ERROR: english switch id {id} has name {entry['name']}")
            if len(entry["aSide"]) != 2:
                errors.append(f"ERROR Railroad id {id} does not have 1 aside: {entry['aSide']}")
            if len(entry["bSide"]) != 2:
                errors.append(f"ERROR Railroad id {id} does not have 1 aside: {entry['bSide']}")
            if entry["name"][2:] != entry["id"]:
                warnings.append(f"--WARNING name is {entry['name']} but id is {id}")
            if entry["length"] != 100:
                warnings.append(f"--WARNING length of switch {id} is not 100")                
        elif entry["type"] == "Bumper":
            if entry["name"][0] != "b":
                errors.append(f"ERROR: bumper id {id} has name {entry['name']}")
            if entry["name"][2:] != entry["id"]:
                warnings.append(f"--INFO name is {entry['name']} but id is {id}")
            if not ((len(entry["aSide"]) == 1 and len(entry["bSide"]) == 0) or (len(entry["aSide"]) == 0 and len(entry["bSide"]) == 1)):
                errors.append(f"ERROR Bumper id {id} does not have correct a/b side numbers")    
            if entry["length"] != 0:
                errors.append(f"ERROR length of bumper {id} is not 0")                
    for id in parts:         
        for a in parts[id]["aSide"]:
            if a not in parts:
                errors.append(f"ERROR: {a} is aside of {id} but not a trackpart")
            elif id not in parts[a]["bSide"]:
                errors.append(f"ERROR: {a} is aside of {id} but {id} not in bside of {a}")
        for b in parts[id]["bSide"]:
            if b not in parts:
                errors.append(f"ERROR: {b} is bside of {id} but not a trackpart")
            elif id not in parts[b]["aSide"]:
                errors.append(f"ERROR: {b} is bside of {id} but {id} not in aside of {b}")   
    print(f"Processed location with {len(g.nodes)} nodes and {len(g.edges)} edges")
    if show_error:
        print("ERRORS[\n", "\n  ".join(errors), "\n]")
    if show_warning:
        print("WARNINGS", warnings) 
    return errors, warnings      

def check_scenario(scenario, location, g, incoming_outgoing, show_error, show_warning, show_intervals, agent_speed=15):
    errors = []
    warnings = []
    train_names = set([entry["name"] for entry in location['trackParts']])
    # To check no two share the same
    first_starts = []
    last_ends = []
    # To check no intermediate moves use an occupied node - keep track of the time that the train ends there or leaves its first start
    all_starts = {entry["movements"][0]["startLocation"]: entry["movements"][0]["startTime"] for entry in scenario["trains"]}
    all_ends = {entry["movements"][-1]["endLocation"]: entry["movements"][-1]["endTime"] for entry in scenario["trains"]} 
    for entry in scenario["trains"]:
        for move in entry["movements"]:
            track_type = move["startLocation"][-1]
            track_part = move["startLocation"][0:-1]
            if track_type != "A" and track_type != "B":
                errors.append(f"ERROR move of train {entry['trainNumber']} starts on a location that is not an A or B node")
            elif track_part not in train_names: 
                errors.append(f"ERROR move of train {entry['trainNumber']} starts on a node that is not a trackpart in the location.")
            track_type = move["endLocation"][-1]
            track_part = move["endLocation"][0:-1]
            if track_type != "A" and track_type != "B":
                errors.append(f"ERROR move of train {entry['trainNumber']} ends on a location that is not an A or B node")
            elif track_part not in train_names: 
                errors.append(f"ERROR move of train {entry['trainNumber']} ends on a node that is not a trackpart in the location.")
            if move["endLocation"] in all_ends and move["endLocation"] not in incoming_outgoing["outgoing"] and move["endTime"] > all_ends[move['endLocation']]:
                errors.append(f"ERROR train {entry['trainNumber']} goes to node {move['endLocation']} after another train has already ended there")
            if move["endLocation"] in all_starts and move["endLocation"] not in incoming_outgoing["incoming"] and move["endTime"] < all_starts[move['endLocation']]:
                errors.append(f"ERROR train {entry['trainNumber']} goes to node {move['endLocation']} before another train has left the node")
        if entry["movements"][0]["startLocation"] in first_starts and entry["movements"][0]["startLocation"] not in incoming_outgoing["incoming"]:
            errors.append(f"ERROR: cannot start at the same node that is not an incoming track")
        if entry["movements"][0]["startLocation"] in last_ends and all_ends[entry["movements"][0]["startLocation"]] < entry["movements"][0]["startTime"]:
            errors.append(f"ERROR another train arrived at node {entry['movements'][0]['startLocation']} before train {entry['trainNumber']} could depart")
        first_starts.append(entry["movements"][0]["startLocation"])
        if entry["movements"][-1]["endLocation"] in last_ends and entry["movements"][-1]["endLocation"] not in incoming_outgoing["outgoing"]:
            errors.append(f"ERROR: cannot end at same node that is not an outgoing track")
        last_ends.append(entry["movements"][-1]["endLocation"])
    # Check the path is within in the end time
    types = {x["name"]: x for x in scenario["types"]}
    measures = {
        "walkingSpeed": scenario["walkingSpeed"],
        "headwayFollowing": scenario["headwayFollowing"],
        "headwayCrossing": scenario["headwayCrossing"]
    }
    node_intervals_per_train = {}
    for entry in scenario["trains"]:
        measures["trainLength"] = sum([types[x]["length"] for x in entry["trainUnitTypes"]])
        measures["trainSpeed"] = types[entry["trainUnitTypes"][0]]["speed"] 
        node_intervals_per_train[entry["trainNumber"]] = {n: [] for n in g.nodes}
        for move in entry["movements"]:
            path = generate.construct_path(g, move)
            if len(path) == 0:
                errors.append(f"ERROR No path was found for move {move} of train {entry['trainNumber']}")
            node_intervals, _, _ = generate.generate_unsafe_intervals(g, path, move, measures)
            for tup in node_intervals[move["endLocation"]]:
                # Only check the start of the interval due to headway times 
                if tup[0] > move["endTime"]:
                    errors.append(f"ERROR train {entry['trainNumber']} has interval {tup} at end location {move['endLocation']} with end time {move['endTime']}")
    # Check for interfering intervals
    seen_intervals = {n:[] for n in g.nodes}
    for train in node_intervals_per_train:
        for n in node_intervals_per_train[train]:
            same_train_intervals = {n: [] for n in g.nodes}
            for int in node_intervals_per_train[train][n]:
                disregard = False
                for x in same_train_intervals[n]:
                    if x[0] >= int[0] and x[0] <= int[1] and x[1] <= int[1] and x[1] >= int[0]:
                        # Fully contained in other interval for same train, so we can disregard this
                        disregard = True
                same_train_intervals[n].append(int)
                for x in seen_intervals[n]:
                    if x[0] >= int[0] and x[0] <= int[1] and not disregard:
                        errors.append(f"ERROR start of new interval of train {train} on node {n}: {int} interferes with previous interval {x}")
                    if x[1] <= int[1] and x[1] >= int[0] and not disregard:
                        errors.append(f"ERROR end of new interval of train {train} on node {n}: {int} interferes with previous interval {x}")
                if not disregard:
                    seen_intervals[n].append(int)
        # Run complete unsafe interval generation process
        node_intervals, edge_intervals, block_intervals, agent_intervals, moves_per_agent = generate.process_scenario(scenario, g, train)
        safe_node_intervals, safe_edge_intervals, not_found_edges = generate.create_safe_intervals(node_intervals, g, agent_speed, False)
        errors.extend(not_found_edges)
    # print(f"Processed scenario with {len(scenario['trains'])} trains using {len(scenario['types'])} different types")
    if show_error:
        print("ERRORS[", "\n  ".join(errors), "]")
    if show_warning:
        print("WARNINGS[", "\n  ".join(errors), "]") 
    if show_intervals:
        print("EDGE INTERVALS[", "\n  ".join(not_found_edges), "]")
    return errors, not_found_edges, warnings, safe_node_intervals, safe_edge_intervals
        

if __name__ == "__main__":
    check_json_files("enkhuizen/location_enkhuizen.json", "enkhuizen/simple_freight+passenger.json")
    check_json_files("enkhuizen/location_enkhuizen.json", "enkhuizen/simple_freight+passenger_realistic.json")
    check_json_files("enkhuizen/location_enkhuizen.json", "enkhuizen/scenario_enkhuizen.json")
    check_json_files("enkhuizen/location_enkhuizen.json", "enkhuizen/scenario_small.json")
    check_json_files("heerlen/location_heerlen.json", "heerlen/scenario_small.json")