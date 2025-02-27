import copy
import sys
import queue as Q
from util import *

def process_scenario(data, g, agent):
    """Process the data from the scenario."""
    # Create a global end time (end of the planning horizon)
    g.global_end_time = max([2 * move["endTime"] for entry in data["trains"] for move in entry["movements"]])
    types = {x["name"]: x for x in data["types"]}
    node_intervals = {}
    edge_intervals = {}
    moves_per_agent = {}
    for entry in data["trains"]:
        measures = {}
        measures["trainLength"] = sum([types[x]["length"] for x in entry["trainUnitTypes"]])
        if len({types[i]["speed"] for i in entry["trainUnitTypes"]}) != 1:
            print("[ERROR] Not all train units have the same type")
        measures["trainSpeed"] = types[entry["trainUnitTypes"][0]]["speed"] * 10 / 3.6
        measures["walkingSpeed"] = data["walkingSpeed"]
        measures["headwayFollowing"] = data["headwayFollowing"]
        measures["headwayCrossing"] = data["headwayCrossing"]
        moves_per_agent[entry["trainNumber"]] = []
        node_intervals[entry["trainNumber"]] = {n:[] for n in g.nodes}
        edge_intervals[entry["trainNumber"]] = {e.get_identifier():[] for e in g.edges}
        # Each of the planned moves of the train must be converted to intervals
        process_moves(entry, g, measures, moves_per_agent, node_intervals, edge_intervals)
    # Combine intervals and merge overlapping intervals, taking into account the current agent
    node_intervals, edge_intervals, agent_intervals = combine_intervals_per_train(node_intervals, edge_intervals, g, agent)
    for node in node_intervals:
        for i in range(len(node_intervals[node])):
            interval = node_intervals[node][i]
            if int(interval[0]) > int(interval[1]):
                print(f"ERROR  node {node}: unsafe node interval {interval} has later end than start")
            if i > 0 and int(interval[0]) < int(node_intervals[node][i-1][1]):
                print(f"ERROR  node {node}: unsafe node interval {interval} has a start which comes before the end of previous interval {node_intervals[node][i-1]}")
    return node_intervals, edge_intervals, agent_intervals, moves_per_agent


def process_moves(entry, g, measures, moves_per_agent, node_intervals, edge_intervals):
    """Process the data for all moves. A move is defined by a start and end time and a start and end node. First the path is constructed, then the unsafe intervals for each node and edge in the path are generated."""
    for i in range(len(entry["movements"])):
        move = entry["movements"][i]
        current_train = entry["trainNumber"] # This is the train making the move, but not necessarily the delayed agent
        path = construct_path(g, move)
        current_node_intervals, current_edge_intervals = generate_unsafe_intervals(g, path, move, measures)
        moves_per_agent[entry["trainNumber"]].append(path)
        
        # If train starts at a parking track node, it is unsafe until its start time
        if i == 0 and g.nodes[move["startLocation"]].canReverse:
            current_node_intervals[move["startLocation"]].insert(0, (0, move["startTime"], 0))
            for neighbor in g.nodes[move["startLocation"]].associated:
                current_node_intervals[neighbor.name].insert(0, (0, move["startTime"], 0))
        # If train ends at a parking track node, it is unsafe until the end
        if i == len(entry["movements"]) - 1 and g.nodes[move["endLocation"]].canReverse:
            # Get the end of the last interval from the move
            end_time = current_node_intervals[move["endLocation"]][-1][1]
            current_node_intervals[move["endLocation"]].append((end_time, g.global_end_time, 0))
            for neighbor in g.nodes[move["endLocation"]].associated:
                current_node_intervals[neighbor.name].append((end_time, g.global_end_time, 0))
        # If the train waits at a node, it is unsafe in between the two intervals
        if i > 0 and entry["movements"][i-1]["endLocation"] == entry["movements"][i]["startLocation"]:
            current_start = current_node_intervals[move["startLocation"]][0][0]
            node_intervals[current_train][move["startLocation"]].sort()
            previous_end = node_intervals[current_train][move["startLocation"]][-1][1]
            current_node_intervals[move["startLocation"]].append((previous_end, current_start, 0))
            for neighbor in g.nodes[move["startLocation"]].associated:
                current_node_intervals[neighbor.name].append((previous_end, current_start, 0))
        for node in current_node_intervals:
            for tup in current_node_intervals[node]:
                node_intervals[current_train][node].append(tup)
        for edge in current_edge_intervals:
            for tup in current_edge_intervals[edge]:
                edge_intervals[current_train][edge].append(tup)
    return node_intervals, edge_intervals

def calculate_path(g, start, end, print_path_error=True):
    distances = {n: sys.maxsize for n in g.nodes}
    previous = {n: None for n in g.nodes}
    previous_edge = {n: None for n in g.nodes}
    pq = Q.PriorityQueue()
    distances[start.name] = 0
    pq_counter = 0
    # Use a counter so it doesn't have to compare nodes
    pq.put((distances[start.name], pq_counter, start))
    pq_counter += 1
    # This does not include the other node intervals: this will have to be updated with propagating SIPP searches
    while not pq.empty():
        u = pq.get()[2]
        for v in u.outgoing:
            tmp = distances[u.name] + v.length
            if tmp < distances[v.to_node.name]:
                distances[v.to_node.name] = tmp
                previous[v.to_node.name] = u
                previous_edge[v.to_node.name] = v
                pq.put((distances[v.to_node.name], pq_counter, v.to_node))
                pq_counter += 1
    path = []
    current = end
    try:
        while current != start:
            for x in current.incoming:
                if x.from_node == previous[current.name]:
                    path.insert(0, copy.deepcopy(x))
            current = previous[current.name]
    except:
        if print_path_error:
            print(f"##### ERROR ### No path was found between {start.name} and {end.name}")
    return path

def construct_path(g, move, print_path_error=True):
    """Construct a shortest path from the start to the end location to determine the locations and generate their unsafe intervals."""
    start = move["startLocation"]
    stops = move["stops"] if "stops" in move else {}
    end = move["endLocation"]
    all_movements = [start] + list(stops.keys()) + [end]
    path = []
    for i in range(len(all_movements) - 1):
        start = g.nodes[all_movements[i]]
        end = g.nodes[all_movements[i + 1]]
        next_path = calculate_path(g, start, end, print_path_error)
        if i != 0:
            next_path[0].stops_at_station = stops[all_movements[i]]
        path.extend(next_path)

    return path

def generate_unsafe_intervals(g, path, move, measures):
    cur_time = move["startTime"]
    node_intervals = {n:[] for n in g.nodes}
    edge_intervals = {e.get_identifier(): [] for e in g.edges}
    for e in path:
        # If the train reverses: going from an A to B side -> use walking speed
        if ("A" in e.from_node.name and "B" in e.to_node.name) or ("B" in e.from_node.name and "A" in e.to_node.name):
            # When turning around, the headway is also included in the end time, so the train has to wait until it can depart after reversing
            end_time = cur_time + (e.length + measures["trainLength"]) / measures["trainSpeed"] + measures["trainLength"] / measures["walkingSpeed"] + measures["headwayFollowing"]
            # In this case the intervals on the A and B nodes are the same
            node_intervals[e.from_node.name].append((cur_time, end_time, (e.length + measures["trainLength"]) / measures["walkingSpeed"]))
            node_intervals[e.to_node.name].append((cur_time, end_time, (e.length + measures["trainLength"]) / measures["walkingSpeed"]))
            edge_intervals[e.get_identifier()].append((cur_time, end_time, (e.length + measures["trainLength"]) / measures["walkingSpeed"]))
            for o in e.opposites:
                edge_intervals[o.get_identifier()].append((
                    cur_time,
                    cur_time + (e.length + measures["trainLength"]) / measures["walkingSpeed"] + measures["headwayCrossing"],
                    (e.length + measures["trainLength"]) / measures["walkingSpeed"]
                ))
            for a in e.associated:
                edge_intervals[a.get_identifier()].append((
                    cur_time, 
                    end_time,
                    (e.length + measures["trainLength"]) / measures["walkingSpeed"]
                ))
            e.set_start_time(cur_time)
            e.set_depart_time(cur_time)
            cur_time = end_time
        # In all other cases use train speed
        else:

            trainSpeed = min(e.max_speed, measures["trainSpeed"])

            extra_stop_time = 0
            if e.stops_at_station is not None:
                extra_stop_time = max(60, e.stops_at_station - cur_time)
            e.headway = measures["headwayFollowing"]

            node_intervals[e.from_node.name].append((
                cur_time,
                cur_time + (measures["trainLength"]) / trainSpeed + extra_stop_time + measures["headwayFollowing"],
                e.length / trainSpeed + extra_stop_time
            ))
            for x in e.from_node.associated:
                node_intervals[x.name].append((
                    cur_time,
                    cur_time + (e.length + measures["trainLength"]) / trainSpeed + extra_stop_time + measures["headwayFollowing"],
                    e.length / trainSpeed + extra_stop_time
                ))
            for x in e.from_node.opposites:
                node_intervals[x.name].append((
                    cur_time,
                    cur_time + (e.length + measures["trainLength"]) / trainSpeed + extra_stop_time + measures["headwayCrossing"],
                    e.length / trainSpeed + extra_stop_time
                ))
            end_time = cur_time + e.length / trainSpeed + extra_stop_time
            if e == path[-1]:
                node_intervals[e.to_node.name].append((
                    end_time,
                    end_time + (measures["trainLength"] / trainSpeed) + measures["headwayFollowing"],
                    e.length / trainSpeed
                ))
                # In case of an A-B move, the associated node should get the same interval
                for x in e.to_node.associated:
                    node_intervals[x.name].append((
                        end_time,
                        end_time + (measures["trainLength"] / trainSpeed) + measures["headwayFollowing"],
                        e.length / trainSpeed
                    ))
                #  The node in-between the edge is the opposite of the from node, which should get the crossing headway and same time as the from node
                for x in e.to_node.opposites:
                    node_intervals[x.name].append((
                        end_time,
                        end_time + (measures["trainLength"] / trainSpeed) + measures["headwayCrossing"],
                        e.length / trainSpeed
                    ))
            # # Edge interval
            # edge_intervals[e.get_identifier()].append((
            #     cur_time,
            #     cur_time + e.length / trainSpeed + measures["headwayFollowing"],
            #     e.length / trainSpeed
            # ))
            # # Associated edges (same side of switch) get the same interval
            # for x in e.associated:
            #     edge_intervals[x.get_identifier()].append((
            #         cur_time,
            #         cur_time + e.length / trainSpeed + measures["headwayFollowing"],
            #         e.length / trainSpeed
            #     ))
            # for x in e.opposites:
            #     edge_intervals[x.get_identifier()].append((
            #         cur_time,
            #         cur_time + e.length / trainSpeed + measures["headwayCrossing"],
            #         e.length / trainSpeed
            #     ))
            e.set_start_time(cur_time)
            e.set_depart_time(end_time)
            cur_time = end_time
    return node_intervals, edge_intervals

def combine_intervals_per_train(node_intervals, edge_intervals, g, agent=None):
    """Combine the intervals for individual trains together per node/edge and remove duplicates/overlap."""
    combined_nodes = {n: [] for n in g.nodes}
    combined_edges = {e.get_identifier(): [] for e in g.edges}
    agent_intervals = {"nodes": {n: [] for n in g.nodes}, "edges": {e.get_identifier(): [] for e in g.edges}}
    for train in node_intervals:
        for n in node_intervals[train]:
            node_intervals[train][n].sort()
            for tup in node_intervals[train][n]:
                double = False
                for x in combined_nodes[n]:
                    # If the new (tup) fits in existing (x) 
                    if tup[0] >= x[0] and tup[0] <= x[1] and tup[1] <= x[1] and tup[1] >= x[0]:
                        double = True
                    # if the existing (x) fits in the new (tup) -> replace
                    elif x[0] >= tup[0] and x[0] <= tup[1] and x[1] <= tup[1] and x[1] >= tup[0]:
                        combined_nodes[n].remove(x)
                if not double:
                    if train != int(agent):
                        combined_nodes[n].append(tup)
                    else:
                        agent_intervals["nodes"][n].append(tup)
    for train in edge_intervals:
        for e in edge_intervals[train]:
            for tup in edge_intervals[train][e]:
                double = False
                for x in combined_edges[e]:
                    # If the new (tup) fits in existing (x) 
                    if tup[0] >= x[0] and tup[0] <= x[1] and tup[1] <= x[1] and tup[1] >= x[0]:
                        double = True
                    # if the existing (x) fits in the new (tup) -> replace
                    elif x[0] >= tup[0] and x[0] <= tup[1] and x[1] <= tup[1] and x[1] >= tup[0]:
                        combined_edges[e].remove(x)
                if not double:
                    if train != int(agent):
                        combined_edges[e].append(tup)
                    else:
                        agent_intervals["edges"][e].append(tup)
    # Sort again to order mixed traffic and merge overlapping
    for n in combined_nodes:
        combined_nodes[n].sort()
        i = 0
        while i < len(combined_nodes[n]) - 1:
            # As list is sorted and contains no subcontained interval, we can simply check for overlap.
            if combined_nodes[n][i+1][0] < combined_nodes[n][i][1]:
                duration = max(combined_nodes[n][i+1][2], combined_nodes[n][i][2])
                # Replace the two intervals with one combined interval
                new_interval = (combined_nodes[n][i][0], combined_nodes[n][i+1][1], duration)
                combined_nodes[n].remove(combined_nodes[n][i+1])
                combined_nodes[n].remove(combined_nodes[n][i])
                combined_nodes[n].insert(i, new_interval)
            else:
                i += 1
    # Sort again to order mixed traffic and merge overlapping
    for e in combined_edges:
        combined_edges[e].sort()
        i = 0
        while i < len(combined_edges[e]) - 1:
            # As list is sorted and contains no subcontained interval, we can simply check for overlap.
            if combined_edges[e][i+1][0] < combined_edges[e][i][1]:
                duration = max(combined_edges[e][i+1][2], combined_edges[e][i][2])
                # Replace the two intervals with one combined interval
                new_interval = (combined_edges[e][i][0], combined_edges[e][i+1][1], duration)
                combined_edges[e].remove(combined_edges[e][i+1])
                combined_edges[e].remove(combined_edges[e][i])
                combined_edges[e].insert(i, new_interval)
            else:
                i += 1     
    return combined_nodes, combined_edges, agent_intervals