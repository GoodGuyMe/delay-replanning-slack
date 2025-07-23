#! /usr/bin/env python
import os
import logging
if __name__ == "__main__":
    # Set logging levels before importing (and loading) all other loggers to propagate settings
    logging.basicConfig()
    logging.root.setLevel(logging.INFO)
    logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger('__main__')
    logger.setLevel(os.environ.get("LOGLEVEL", logging.DEBUG))

import json
import time
import argparse
from pathlib import Path

from generation.buffer_time import flexibility
from generation.graph import block_graph_constructor
from generation.safe_interval_graph import plot_blocking_staircase
from generation.interval_generation import *
from generation.convert_to_safe_intervals import *
from generation.util import read_graph

# Example:
# $ python3 generate.py -l ../data/enkhuizen/location_enkhuizen.json -s ../data/enkhuizen/simple_freight+passenger_realistic.json -o output -a 1 -v 20 -p True
parser = argparse.ArgumentParser(
                    prog='create_intervals',
                    description='Encode train planning as an any start time graph')
parser.add_argument('-l', "--location", help = "Path to location file", required = True)
parser.add_argument('-s', "--scenario", help = "Path to scenario file", required = True)
parser.add_argument('-o', "--output", help = "output file", required = True)
parser.add_argument('-d', "--destination", help="Destination of the agent for who we are getting safe intervals")
parser.add_argument('-a', "--agent_id", help = "(optional) id of agent if it is one of the trains in scenario", default=-1)
parser.add_argument('-v', "--agent_speed", help="(optional) the speed of the agent for who we are getting safe intervals. (default=40)", default=40)
parser.add_argument('-p', "--printing", help="(optional) whether to print edge intervals (default=True)", default="True")
parser.add_argument('-b', "--buffer", help="(optional) max buffer time (default=float(\"inf\")", default=float("inf"))
parser.add_argument('-r', "--recovery", help="(optional) use recovery time (default=True", default="True")

def read_scenario(file, g, g_block):
    """Read scenario files in json format."""
    try:
        base_path = Path(__file__).parent
        file_path = (base_path / file).resolve()
        data = json.load(open(file_path))
    except:
        data = json.load(open(file))
    start_time = time.time()
    block_intervals, moves_per_agent = process_scenario(data, g, g_block)
    end_time = time.time()
    return block_intervals, moves_per_agent, end_time - start_time

def write_intervals_to_file(file, safe_node_intervals, safe_edge_intervals, indices_to_states, **kwargs):
    """Write SIPP graph to gzip file for the search procedure"""

    def filter_origin(n):
        return n.split("-")[1].split("|")[0]
    filter_tracks = kwargs.get("filter_tracks", set())

    if len(filter_tracks) > 0:
        logger.debug(f'Filtering tracks: {filter_tracks}')
        new_safe_edge_intervals = []
        for e in safe_edge_intervals:
            if filter_origin(indices_to_states[e[0]]) in filter_tracks or filter_origin(indices_to_states[e[1]]) in filter_tracks:
                new_safe_edge_intervals.append(e)
        safe_edge_intervals = new_safe_edge_intervals


    with open(file, "wt") as f:
        f.write("vertex count: " + str(len([x for node in safe_node_intervals for x in safe_node_intervals[node]])) + "\n")
        f.write("edge count: " + str(len(safe_edge_intervals)) + "\n")

        num_trains = 0

        """ Write safe node intervals, as 'node_name start end id_before id_after'"""
        for node in safe_node_intervals:
            for start, end, id_before, id_after, buf_after, _ in safe_node_intervals[node]:
                num_trains = max(num_trains, id_before, id_after)
                f.write(f"{node} {start} {end} {id_before} {id_after} {buf_after}\n")

        """Write atfs, as 'from_id to_id zeta alpha beta delta id_before max_buf_before len_unsafe_before id_after max_buf_after len_unsafe_after'"""
        for from_id, to_id, zeta, alpha, beta, delta, id_before, crt_b, id_after, buffer_after, crt_a, heuristic in safe_edge_intervals:
            # In our domain there is not really a difference between alpha and zeta since we have no waiting time, so they are the same, but we keep both for extendability.
            num_trains = max(num_trains, id_before, id_after)
            f.write(f"{from_id} {to_id} {zeta} {alpha} {beta} {delta} {id_before} {crt_b} {id_after} {buffer_after} {crt_a} {heuristic}\n")
        f.write(f"num_trains {num_trains}\n")

def time_graph_creation(location):
    start_time = time.time()
    g = read_graph(location)
    end_time = time.time()
    g_time = end_time - start_time
    start_time = time.time()
    g_block = block_graph_constructor(g)
    end_time = time.time()
    return g, g_block, g_time, end_time - start_time

def time_scenario_creation(scenario, g, g_block):
    block_intervals, moves_per_agent, unsafe_computation_time = read_scenario(scenario, g, g_block)
    start_time = time.time()
    block_routes = convertMovesToBlock(moves_per_agent, g)
    end_time = time.time()
    return block_intervals, moves_per_agent, unsafe_computation_time, block_routes, end_time - start_time

def time_flexibility_creation(block_routes, block_intervals, max_buffer_time, use_recovery_time):
    start_time = time.time()
    buffer_times, recovery_times = flexibility(block_intervals, block_routes, max_buffer_time, use_recovery_time)
    end_time = time.time()
    return buffer_times, recovery_times, end_time - start_time

def time_interval_creation(block_intervals, g_block, buffer_times, recovery_times, destination, agent_velocity, **kwargs):
    start_time = time.time()
    safe_block_intervals, safe_block_edges_intervals, atfs, _, indices_to_states = create_safe_intervals(
        block_intervals, g_block, buffer_times, recovery_times, destination, float(agent_velocity), print_intervals=False, **kwargs)
    safe_computation_time = time.time() - start_time
    return safe_block_intervals, safe_block_edges_intervals, atfs, indices_to_states, safe_computation_time

def plot_route(plot_agent, moves_per_agent, block_routes, block_intervals, g_block, buffer_times, recovery_times, plottings=None, exclude_agent=-1):
    if plottings is None:
        plottings = (moves_per_agent[plot_agent][0], block_routes[plot_agent][0]) if plot_agent in block_routes else None
    plot_blocking_staircase(block_intervals, block_routes, moves_per_agent, g_block, buffer_times, recovery_times, plot_routes=plottings, exclude_agent=exclude_agent)


def main():
    args = parser.parse_args()
    g, g_block, _, _ = time_graph_creation(args.location)
    block_intervals, moves_per_agent, computation_time = read_scenario(args.scenario, g, g_block, args.agent_id)
    block_routes = convertMovesToBlock(moves_per_agent, g)
    buffer_times, recovery_times = flexibility(block_intervals, block_routes, float(args.buffer), args.recovery.strip().lower() == "true")
    agent_route = 2
    plot_route = (moves_per_agent[agent_route][0], block_routes[agent_route][0]) if agent_route in block_routes else None
    plot_blocking_staircase(block_intervals, block_routes, moves_per_agent, g_block, buffer_times, recovery_times, plot_routes=plot_route)
    safe_block_intervals, safe_block_edges_intervals, atfs, _, indices_to_states = create_safe_intervals(block_intervals, g_block, buffer_times, recovery_times, args.destination, float(args.agent_speed), args.recovery.strip().lower() == "true")
    write_intervals_to_file(args.output, safe_block_intervals, atfs, indices_to_states)
    # plot_safe_node_intervals(safe_block_intervals | safe_block_edges_intervals, block_routes)

if __name__ == "__main__":
    main()