import math
import json
import random
import argparse
import sys
from pathlib import Path
from check_location_scenario_files import check_scenario
from generation import generate

parser = argparse.ArgumentParser(
                    prog='generate_scenario',
                    description='Generate scenarios for railway hub planning')
parser.add_argument('-r', "--railwayLayout", help = "Folder name of railway hub layout", required = True)
parser.add_argument('-l', "--location", help = "Name of location file in the layout folder", required = True)
parser.add_argument('-n', "--trains", help = "Number of trains", required = True)
parser.add_argument('-t', "--types", help="Number of train types", required=True)
parser.add_argument('-s', "--seed", help="Seed used in random generator", required=True)
parser.add_argument('-w', "--timewindow", help="(optional) range in which the start time is sought, default=1000", default="1000")


def generate_scenario(layout, graph_file, num_trains, num_types, seed, time_window=1000):
    filename = layout + "/" + "scenario_n" + str(num_trains) + "_t" + str(num_types) + "_w" + str(time_window) + "_s" + str(seed) + ".json"
    random.seed(seed)
    file = layout + "/" + graph_file
    g = generate.read_graph(file)
    try:
        base_path = Path(__file__).parent
        file_path = (base_path / file).resolve()
        location_data = json.load(open(file_path))
        output_path = (base_path / filename).resolve()
    except:
        location_data = json.load(open(file))
        output_path = filename
    track_nodes = []
    colocations = {}
    bumpers = {b["id"]: b for b in location_data["trackParts"] if b["type"] == "Bumper"}     
    for t in location_data["trackParts"]:
        if t["type"] == "RailRoad":
            # For dead-end and ongoing tracks, start on the correct side.
            # If the bumper is on the aSide then start on the aSide
            if len(t["aSide"]) == 1 and t["aSide"][0] in bumpers:
                if t["sawMovementAllowed"]:
                    track_nodes.append((t["name"] + "A", "reversed"))
                    track_nodes.append((t["name"] + "B", "double"))
                    colocations[t["name"] + "B"] = "reversed"
                    colocations[t["name"] + "A"] = "double"                    
                else: 
                    track_nodes.append((t["name"] + "A", "outgoing"))
                    track_nodes.append((t["name"] + "B", "incoming"))
                    colocations[t["name"] + "B"] = "outgoing"
                    colocations[t["name"] + "A"] = "incoming"                     
            # If the bumper is on the bSide then start on the bSide
            elif len(t["bSide"]) == 1 and t["bSide"][0] in bumpers:
                if t["sawMovementAllowed"]:
                    track_nodes.append((t["name"] + "B", "reversed"))
                    track_nodes.append((t["name"] + "A", "double"))
                    colocations[t["name"] + "B"] = "double"
                    colocations[t["name"] + "A"] = "reversed"                     
                else:
                    track_nodes.append((t["name"] + "B", "incoming"))                    
                    track_nodes.append((t["name"] + "A", "outgoing"))
                    colocations[t["name"] + "B"] = "outgoing"
                    colocations[t["name"] + "A"] = "incoming"                     
            # For double-sided tracks, both are possible nodes.
            else:
                track_nodes.append((t["name"] + "B", "double"))
                track_nodes.append((t["name"] + "A", "double"))
                colocations[t["name"] + "B"] = "double"
                colocations[t["name"] + "A"] = "double"
    scenario = {
        "types": [], 
        "trains": [],
        "walkingSpeed": round(random.uniform(0.5, 5), 2),
        "headwayFollowing": round(random.uniform(50, 500), 2),
        "headwayCrossing": round(random.uniform(50, 500), 2)
    }
    for i in range(num_types):
        scenario["types"].append({
            "name": "type" + str(i),
            "speed": round(random.uniform(5, 50), 2),
            "length": round(random.uniform(100, 2000), 2)
        })
    cur_time = 0
    trainUnitIds = set()
    incoming_outgoing_nodes = {"incoming": [node[0] for node in track_nodes if node[1] == "incoming"], "outgoing": [node[0] for node in track_nodes if node[1] == "outgoing"]}
    unoccupied_nodes = get_start_end_nodes_free(track_nodes, colocations, g)    
    for i in range(1, num_trains + 1):
        numTrainUnits = random.randint(1, 3)
        trainUnits = []
        while len(trainUnits) != numTrainUnits:
            id = random.randint(100, 1000)
            if id not in trainUnitIds:
                trainUnitIds.add(id)
                trainUnits.append(id)
        trainUnitType = random.choice(scenario["types"])
        train = {
            "trainNumber": i,
            "trainUnits": trainUnits,
            "trainUnitTypes": [trainUnitType["name"] for _ in range(numTrainUnits)],
            "movements": []
        }
        scenario["trains"].append(train)
        trainLength = numTrainUnits * trainUnitType["length"]
        numTrainMoves = random.randint(1, 3)
        # Pick a number of moves
        while len(scenario["trains"][-1]["movements"]) < numTrainMoves:
            start_ends = get_start_and_end_locations(scenario, colocations, track_nodes, unoccupied_nodes, numTrainMoves)
            all_errors = []
            for m in start_ends:
                start = m[0]
                end = m[1]
                start_time = round(random.uniform(cur_time, cur_time + time_window), 2)
                move = {"startLocation": start, "endLocation": end, "startTime": start_time}
                print(f"Now trying {len(scenario['trains'][-1]['movements']) + 1}th out of {numTrainMoves} moves for train {train['trainNumber']} from {start} to {end}")
                path = generate.construct_path(g, move, False)
                # If a start/end combination could not match to a path, try again.
                if len(path) > 0:
                    path_time = start_time
                    for e in path:
                        if ("A" in e.from_node.name and "A" in e.to_node.name) or ("B" in e.from_node.name and "B" in e.to_node.name):
                            path_time += (e.length + trainLength) / trainUnitType["speed"]
                        else: # If edge from A to B or vice versa, use walking speed    
                            path_time += (e.length + trainLength) / trainUnitType["speed"] + trainLength / scenario["walkingSpeed"]
                    path_time += max(scenario["headwayFollowing"], scenario["headwayCrossing"]) # only add headway once
                    move["endTime"] = round(path_time, 2)
                    scenario["trains"][-1]["movements"].append(move)
                    errors, intervals, warnings, safe_node_intervals, safe_edge_intervals = check_scenario(scenario, location_data, g, incoming_outgoing_nodes, False, False, False, trainUnitType["speed"])
                    all_errors.extend(errors)
                    cur_time = path_time
                else:
                    all_errors.append(f"ERROR no path found for {move}")
            if len(all_errors) > 0:
                # Reset the current trains moves
                scenario["trains"][-1]["movements"] = []
            else:
                cur_time = path_time
                if len(scenario["trains"][-1]["movements"]) == 1:
                    for x in unoccupied_nodes["start"]:
                        if x[0] == scenario["trains"][-1]["movements"][0]["startLocation"] and x[1] != "incoming":
                            unoccupied_nodes["start"].remove(x)
                            break
                if len(scenario["trains"][-1]["movements"]) == numTrainMoves:
                    for x in unoccupied_nodes["end"]:
                        if x[0] == scenario["trains"][-1]["movements"][-1]["endLocation"] and x[1] != "outgoing":
                            unoccupied_nodes["end"].remove(x)
                            break
    json.dump(scenario, open(output_path, "w"))
        
def get_start_end_nodes_free(track_nodes, colocations, g):
    unoccupied_nodes = {"start": [], "end": []}
    # Get the correct start nodes: start at correct side of a dead-end track
    for node in track_nodes:
        # Outgoing nodes cannot be start nodes
        if node[1] == "outgoing":
            unoccupied_nodes["end"].append(node)
        elif node[1] == "incoming":
            unoccupied_nodes["start"].append(node)
        # If this a track where the co-location is a bumper, select the other side 
        elif node[1] == "double" and colocations[node[0]] == 'reversed':
            if node[0][-1] == "A":
                other_node_name = node[0][0:-1] + "B"
            else:
                other_node_name = node[0][0:-1] + "A"
            unoccupied_nodes["start"].append((other_node_name, "station"))
            unoccupied_nodes["end"].append((other_node_name, "station"))
    return unoccupied_nodes

def get_start_and_end_locations(scenario, colocations, track_nodes, unoccupied_nodes, num_train_moves):
    # Give a high probability to starting the first move on an incoming track and ending the last move on an outgoing track
    percentage_incoming_outgoing = 60
    incoming_start = random.randrange(0,100) < percentage_incoming_outgoing
    outgoing_end = random.randrange(0,100) < percentage_incoming_outgoing

    nodes = []
    for i in range(num_train_moves):
        start_tup = random.choice(unoccupied_nodes["start"])
        end_tup = random.choice(unoccupied_nodes["end"])
        if i == 0:
            # If forced incoming start, make sure to start there on first move
            while incoming_start and start_tup[1] != "incoming":
                start_tup = random.choice(unoccupied_nodes["start"])
            start = start_tup[0]
        else:
            # Take end of previous node as the next start. 
            start = nodes[-1][1]
        # Cannot end at same node as start
        if i == num_train_moves - 1:
            # If forced outgoing end, make sure to end there on last move
            while outgoing_end and end_tup[1] != "outgoing":
                end_tup = random.choice(unoccupied_nodes["end"])
            # Cannot end at a station node on last move
            while not outgoing_end and end_tup[1] == "station":
                end_tup = random.choice(unoccupied_nodes["end"])
        else:
            # Cannot end at outgoing node on non-last move
            while end_tup[1] == "outgoing" or end_tup[0][0:-1] == start[0:-1]:
                end_tup = random.choice(unoccupied_nodes["end"])
        nodes.append((start, end_tup[0]))       
    return nodes                 

if __name__ == "__main__":
    args = parser.parse_args()
    generate_scenario(args.railwayLayout, args.location, int(args.trains), int(args.types), int(args.seed), int(args.timewindow))