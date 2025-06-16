import copy
import sys
import queue as Q

from generation.graph import BlockEdge
from generation.signal_sections import convertMovesToBlock
from generation.util import *

def process_scenario(data, g, g_block, agent):
    """Process the data from the scenario."""
    # Create a global end time (end of the planning horizon)
    g.global_end_time = max([2 * move["endTime"] for entry in data["trains"] for move in entry["movements"]])
    g_block.global_end_time = g.global_end_time
    types = {x["name"]: x for x in data["types"]}
    moves_per_agent = {}
    block_intervals = {}
    for entry in data["trains"]:
        measures = {}
        measures["trainLength"] = sum([types[x]["length"] for x in entry["trainUnitTypes"]])
        if len({types[i]["speed"] for i in entry["trainUnitTypes"]}) != 1:
            print("[ERROR] Not all train units have the same type")
        measures["trainSpeed"] = types[entry["trainUnitTypes"][0]]["speed"]
        measures["walkingSpeed"] = data["walkingSpeed"]
        measures["headwayFollowing"] = data["headwayFollowing"]
        measures["headwayCrossing"] = data["headwayCrossing"]
        measures["releaseTime"] = data["releaseTime"] if "releaseTime" in data else 0
        measures["setupTime"] = data["setupTime"] if "setupTime" in data else 0
        measures["sightReactionTime"] = data["sightReactionTime"] if "sightReactionTime" in data else 0
        measures["minimumStopTime"] = data["minimumStopTime"] if "minimumStopTime" in data else 60
        moves_per_agent[entry["trainNumber"]] = []
        block_intervals[entry["trainNumber"]] = {e.get_identifier():[] for e in g_block.edges} | {n: [] for n in g_block.nodes}
        # Each of the planned moves of the train must be converted to intervals
        process_moves(entry, g, g_block, measures, moves_per_agent, block_intervals)
    # Combine intervals and merge overlapping intervals, taking into account the current agent
    block_intervals, agent_intervals = combine_intervals_per_train(block_intervals, g, g_block, agent)
    for node in block_intervals:
        for i in range(len(block_intervals[node])):
            interval = block_intervals[node][i]
            if int(interval[0]) > int(interval[1]):
                print(f"ERROR  node {node}: unsafe node interval {interval} has later end than start")
            if i > 0 and int(interval[0]) < int(block_intervals[node][i-1][1]):
                print(f"ERROR  node {node}: unsafe node interval {interval} has a start which comes before the end of previous interval {block_intervals[node][i-1]}")
    return block_intervals, agent_intervals, moves_per_agent


def process_moves(entry, g, g_block, measures, moves_per_agent, block_intervals):
    """Process the data for all moves. A move is defined by a start and end time and a start and end node. First the path is constructed, then the unsafe intervals for each node and edge in the path are generated."""
    for i in range(len(entry["movements"])):
        move = entry["movements"][i]
        current_train = entry["trainNumber"] # This is the train making the move, but not necessarily the delayed agent
        path = construct_path(g, move)
        moves_per_agent[entry["trainNumber"]].append(path)
        block_routes = convertMovesToBlock(moves_per_agent, g)[current_train][0]
        current_block_intervals = generate_unsafe_intervals(g_block, path, block_routes, move, measures, current_train)

        
        # # If train starts at a parking track node, it is unsafe until its start time
        # if i == 0 and g.nodes[move["startLocation"]].canReverse:
        #     current_node_intervals[move["startLocation"]].insert(0, (0, move["startTime"], 0))
        #     for neighbor in g.nodes[move["startLocation"]].associated:
        #         current_node_intervals[neighbor.name].insert(0, (0, move["startTime"], 0))
        # # If train ends at a parking track node, it is unsafe until the end
        # if i == len(entry["movements"]) - 1 and g.nodes[move["endLocation"]].canReverse:
        #     # Get the end of the last interval from the move
        #     end_time = current_node_intervals[move["endLocation"]][-1][1]
        #     current_node_intervals[move["endLocation"]].append((end_time, g.global_end_time, 0))
        #     for neighbor in g.nodes[move["endLocation"]].associated:
        #         current_node_intervals[neighbor.name].append((end_time, g.global_end_time, 0))
        # If the train waits at a node, it is unsafe in between the two intervals
        for node in current_block_intervals:
            for tup in current_block_intervals[node]:
                block_intervals[current_train][node].append(tup)
    return block_intervals

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
                    path.insert(0, x)
            current = previous[current.name]
    except Exception as e:
        if print_path_error:
            print(f"##### ERROR ### {e} No path was found between {start.name} and {end.name}")
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
        if next_path and i != 0:
            next_path[0].stops_at_station = stops[all_movements[i]]
        path.extend(next_path)

    return path

def calculate_blocking_time(e: TrackEdge, cur_time, blocking_intervals, measures, current_train, path: list[BlockEdge]):

    station_time = 0
    if e.stops_at_station is not None:
        station_time = max(measures["minimumStopTime"], e.stops_at_station - cur_time)

    train_speed = min(e.max_speed, measures["trainSpeed"])
    clearing_time = measures["trainLength"] / train_speed
    end_occupation_time = cur_time + e.length / train_speed + clearing_time + station_time

    # Recovery time calculation
    if e.stops_at_station is not None:
        recovery_time = station_time - measures["minimumStopTime"]
    else:
        recovery_time = (e.length / train_speed) - e.length / (train_speed * 1.08)

    # Calculate running time, clearing time and release time for current track
    occupation_time = (
            cur_time,
            end_occupation_time + measures["releaseTime"],
            e.length / train_speed + station_time,
            current_train,
            recovery_time
        )

    for block in e.from_node.blocks:
        blocking_intervals[block.get_identifier()].append(occupation_time)

    # Calculate the approach time for the next piece of track,
    start_approach_time = cur_time + station_time - measures["setupTime"] - measures["sightReactionTime"]
    end_approach_time =   cur_time + station_time + (e.length / train_speed)

    N_BLOCKS = 1

    # Find current spot in block graph
    bools = [e.from_node in block.trackNodes for block in path]
    current_path_index = bools.index(True) if True in bools else None

    next_blocks_approach_time = (start_approach_time,
                     end_approach_time,
                     0,
                     current_train,
                     0.0
    )

    if current_path_index is not None:
        for path_block in path[current_path_index:current_path_index + N_BLOCKS]:
            for tn in path_block.trackNodes:
                for block in tn.blocks:
                    blocking_intervals[block.get_identifier()].append(next_blocks_approach_time)

def generate_unsafe_intervals(g_block, path: list[TrackEdge], block_path: list[BlockEdge], move, measures, current_train):
    cur_time = move["startTime"]
    block_intervals = {e.get_identifier():[] for e in g_block.edges} | {n: [] for n in g_block.nodes}
    for e in path:
        # If the train reverses: going from an A to B side -> use walking speed
        # if ("A" in e.from_node.name and "B" in e.to_node.name) or ("B" in e.from_node.name and "A" in e.to_node.name):
        #     # When turning around, the headway is also included in the end time, so the train has to wait until it can depart after reversing
        #     end_time = cur_time + (e.length + measures["trainLength"]) / measures["trainSpeed"] + measures["trainLength"] / measures["walkingSpeed"] + measures["headwayFollowing"]
        #     e.set_start_time(current_train, cur_time)
        #     e.set_depart_time(current_train, end_time)
        #     cur_time = end_time
        # In all other cases use train speed
        # else:
            calculate_blocking_time(e, cur_time, block_intervals, measures, current_train, block_path)

            train_speed = min(e.max_speed, measures["trainSpeed"])

            extra_stop_time = 0
            if e.stops_at_station is not None:
                extra_stop_time = max(measures["minimumStopTime"], e.stops_at_station - cur_time)

            # Time train leaves the node
            end_time = cur_time + e.length / train_speed + extra_stop_time
            e.set_start_time(current_train, cur_time)
            e.set_depart_time(current_train, end_time)
            cur_time = end_time
    return block_intervals

def combine_intervals(intervals, identifier, agent_intervals, combined, agent):
    for train in intervals:
        for n in intervals[train]:
            intervals[train][n].sort()
            for tup in intervals[train][n]:
                double = False
                for x in combined[n]:
                    # If the new (tup) fits in existing (x)
                    if tup[0] >= x[0] and tup[0] <= x[1] and tup[1] <= x[1] and tup[1] >= x[0]:
                        double = True
                    # if the existing (x) fits in the new (tup) -> replace
                    elif x[0] >= tup[0] and x[0] <= tup[1] and x[1] <= tup[1] and x[1] >= tup[0]:
                        combined[n].remove(x)
                if not double:
                    if train != int(agent):
                        combined[n].append(tup)
                    else:
                        pass
                        # agent_intervals[identifier][n].append(tup)

def sort_and_merge(combined):
    for n in combined:
        combined[n].sort()
        i = 0
        while i < len(combined[n]) - 1:
            # As list is sorted and contains no subcontained interval, we can simply check for overlap.
            if combined[n][i+1][0] <= combined[n][i][1]:
                duration = combined[n][i+1][2] + combined[n][i][2]
                recovery = combined[n][i+1][4] + combined[n][i][4]
                # Replace the two intervals with one combined interval
                new_interval = (combined[n][i][0], combined[n][i+1][1], duration, combined[n][i][3], recovery)
                combined[n].remove(combined[n][i+1])
                combined[n].remove(combined[n][i])
                combined[n].insert(i, new_interval)
            else:
                i += 1

def combine_intervals_per_train(block_intervals, g, g_block, agent=None):
    """Combine the intervals for individual trains together per node/edge and remove duplicates/overlap."""
    combined_blocks = {e.get_identifier(): [] for e in g_block.edges} | {n: [] for n in g_block.nodes}
    agent_intervals = {"blocks": {e.get_identifier(): [] for e in g_block.edges}} | {n: [] for n in g_block.nodes}

    combine_intervals(block_intervals, "blocks", agent_intervals, combined_blocks, agent)

    # Sort again to order mixed traffic and merge overlapping
    sort_and_merge(combined_blocks)

    return combined_blocks, agent_intervals