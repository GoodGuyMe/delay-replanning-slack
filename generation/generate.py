#! /usr/bin/env python
import time
import numpy as np
import argparse
import gzip
from pathlib import Path

from generation.safe_interval_graph import plot_safe_node_intervals, plot_unsafe_node_intervals
from util import *
from interval_generation import *
from convert_to_safe_intervals import *

# Example:
# $ python3 generate.py -l ../data/enkhuizen/location_enkhuizen.json -s ../data/enkhuizen/simple_freight+passenger_realistic.json -o output -a 1 -v 20 -p True
parser = argparse.ArgumentParser(
                    prog='create_intervals',
                    description='Encode train planning as an any start time graph')
parser.add_argument('-l', "--location", help = "Path to location file", required = True)
parser.add_argument('-s', "--scenario", help = "Path to scenario file", required = True)
parser.add_argument('-o', "--output", help = "output file", required = True)
parser.add_argument('-a', "--agent_id", help = "(optional) id of agent if it is one of the trains in scenario", default=-1)
parser.add_argument('-v', "--agent_speed", help="(optional) the speed of the agent for who we are getting safe intervals. (default=15)", default=15)
parser.add_argument('-p', "--printing", help="(optional) whether to print edge intervals (default=True)", default=True)

def read_scenario(file, g, g_block, agent=-1):
    """Read scenario files in json format."""
    try:
        base_path = Path(__file__).parent
        file_path = (base_path / file).resolve()
        data = json.load(open(file_path))
    except:
        data = json.load(open(file))
    start_time = time.time()
    node_intervals, edge_intervals, block_intervals, agent_intervals, moves_per_agent = process_scenario(data, g, g_block, agent)
    end_time = time.time()
    return node_intervals, edge_intervals, block_intervals, agent_intervals, moves_per_agent, end_time - start_time

def write_intervals_to_file(file, safe_node_intervals, safe_edge_intervals):
    """Write SIPP graph to gzip file for the search procedure"""
    with gzip.open(file, "wt") as f:
        f.write("vertex count: " + str(len([x for node in safe_node_intervals for x in safe_node_intervals[node]])) + "\n")
        for node in safe_node_intervals:
            for interval in safe_node_intervals[node]:
                f.write(node + " " + str(interval[0]) + " " + str(interval[1]) + "\n")
        for tup in safe_edge_intervals:
            # In our domain there is not really a difference between alpha and zeta since we have no waiting time, so they are the same, but we keep both for extendability. 
            f.write(str(tup[0]) + " " + str(tup[1]) + " " + str(tup[2]) + " " + str(tup[3]) + " " + str(tup[4]) + " " + str(tup[5]) + "\n")

def time_safe_intervals_and_write(location, scenario, agent_id, agent_speed, output):
    """For testing the time to get the safe intervals. Also writes to file (without timing). Used for experiments."""
    g, g_block = read_graph(location)
    unsafe_node_intervals, _, _, _, _, unsafe_computation_time = read_scenario(scenario, g, agent_id)
    start_time = time.time()
    safe_node_intervals, safe_edge_intervals, _ = create_safe_intervals(unsafe_node_intervals, g, agent_speed, print_intervals=False)
    safe_computation_time = time.time() - start_time
    write_intervals_to_file(output, safe_node_intervals, safe_edge_intervals)
    return unsafe_computation_time + safe_computation_time


def convertMovesToBlock(moves_per_agent, g, g_block):
    print("Converting moves")
    block_routes = {}
    for agent in moves_per_agent:
        block_route = []
        for movements in moves_per_agent[agent]:
            routes = None
            for move in movements:
                if move.from_node in [signal.track for signal in g.signals]:
                    if routes:
                        from_signal = list(routes)[0].split("_")[0]
                        via_route = list(routes)[0]
                        to_signal = "r-" + str([signal.id for signal in g.signals
                                                if signal.track == move.from_node][0])

                        edge_1 = list(filter(lambda e: e.from_node.name == from_signal and e.to_node.name == via_route, g_block.edges))[0]
                        edge_2 = list(filter(lambda e: e.from_node.name == via_route   and e.to_node.name == to_signal, g_block.edges))[0]

                        block_route.append(edge_1)
                        block_route.append(edge_2)
                        print(block_route)
                    routes = set(move.to_node.routes)
                routes = routes & set(move.to_node.routes)
                print(f"{move.to_node.name} - {move.to_node.routes}")
            print(routes)
        block_routes[agent] = [block_route]
    return block_routes




if __name__ == "__main__":
    args = parser.parse_args()
    g, g_block = read_graph(args.location)
    unsafe_node_intervals, unsafe_edge_intervals, block_intervals, agent_intervals, moves_per_agent, computation_time = read_scenario(args.scenario, g, g_block, args.agent_id)

    block_routes = convertMovesToBlock(moves_per_agent, g, g_block)

    plot_unsafe_node_intervals(unsafe_node_intervals, moves_per_agent, g.distance_markers)
    plot_unsafe_node_intervals(block_intervals, block_routes, g.distance_markers, fixed_block=True, moves_per_agent_2=moves_per_agent)
    safe_node_intervals, safe_edge_intervals, not_found_edges = create_safe_intervals(unsafe_node_intervals, g, float(args.agent_speed), print_intervals=args.printing == "True")
    safe_block_intervals, safe_block_edges_intervals, _ = create_safe_intervals(block_intervals, g_block, float(args.agent_speed), print_intervals=args.printing == "True")
    write_intervals_to_file(args.output, safe_node_intervals, safe_edge_intervals)
    # plot_safe_node_intervals(safe_node_intervals, moves_per_agent)
    # plot_safe_node_intervals(safe_node_intervals)
    plot_safe_node_intervals(safe_block_intervals, block_routes)
    # plot_safe_node_intervals(safe_block_intervals)
