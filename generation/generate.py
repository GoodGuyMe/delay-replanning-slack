#! /usr/bin/env python
import time
import argparse
import gzip

from generation.buffer_time import flexibility
from generation.graph import BlockGraph
from generation.safe_interval_graph import plot_safe_node_intervals, plot_blocking_staircase
from generation.signal_sections import convertMovesToBlock
from generation.interval_generation import *
from generation.convert_to_safe_intervals import *

# Example:
# $ python3 generate.py -l ../data/enkhuizen/location_enkhuizen.json -s ../data/enkhuizen/simple_freight+passenger_realistic.json -o output -a 1 -v 20 -p True
parser = argparse.ArgumentParser(
                    prog='create_intervals',
                    description='Encode train planning as an any start time graph')
parser.add_argument('-l', "--location", help = "Path to location file", required = True)
parser.add_argument('-s', "--scenario", help = "Path to scenario file", required = True)
parser.add_argument('-o', "--output", help = "output file", required = True)
parser.add_argument('-a', "--agent_id", help = "(optional) id of agent if it is one of the trains in scenario", default=-1)
parser.add_argument('-v', "--agent_speed", help="(optional) the speed of the agent for who we are getting safe intervals. (default=40)", default=40)
parser.add_argument('-p', "--printing", help="(optional) whether to print edge intervals (default=True)", default="True")
parser.add_argument('-b', "--buffer", help="(optional) max buffer time (default=float(\"inf\")", default=float("inf"))
parser.add_argument('-r', "--recovery", help="(optional) use recovery time (default=True", default="True")

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

def write_intervals_to_file(file, safe_node_intervals, safe_edge_intervals, indices_to_states):
    """Write SIPP graph to gzip file for the search procedure"""
    # with open(file + "_unzipped", "wt") as f:
    with gzip.open(file, "wt") as f:
        f.write("vertex count: " + str(len([x for node in safe_node_intervals for x in safe_node_intervals[node]])) + "\n")
        f.write("edge count: " + str(len(safe_edge_intervals)) + "\n")

        num_trains = 0

        """ Write safe node intervals, as 'node_name start end id_before id_after'"""
        for node in safe_node_intervals:
            for start, end, id_before, id_after, _, _ in safe_node_intervals[node]:
                max_buffer  = 0.0
                num_trains = max(num_trains, id_before, id_after)
                f.write(f"{node} {start} {end} {id_before} {id_after} {max_buffer}\n")

        """Write atfs, as 'from_id to_id zeta alpha beta delta id_before max_buf_before len_unsafe_before id_after max_buf_after len_unsafe_after'"""
        for from_id, to_id, zeta, alpha, beta, delta, id_before, crt_b, id_after, buffer_after, crt_a in safe_edge_intervals:
            # In our domain there is not really a difference between alpha and zeta since we have no waiting time, so they are the same, but we keep both for extendability.
            num_trains = max(num_trains, id_before, id_after)
            f.write(f"{from_id} {to_id} {zeta} {alpha} {beta} {delta} {id_before} {crt_b} {id_after} {buffer_after} {crt_a}\n")
        f.write(f"num_trains {num_trains}\n")

def time_safe_intervals_and_write(location, scenario, agent_id, agent_speed, output, max_buffer_time, use_recovery_time, plot=False):
    """For testing the time to get the safe intervals. Also writes to file (without timing). Used for experiments."""
    g = read_graph(location)
    g_block = BlockGraph(g)
    _, _, block_intervals, _, moves_per_agent, unsafe_computation_time = read_scenario(scenario, g, g_block, agent_id)
    block_routes = convertMovesToBlock(moves_per_agent, g)
    buffer_times, recovery_times = flexibility(block_intervals, block_routes, max_buffer_time, use_recovery_time)
    start_time = time.time()
    safe_block_intervals, safe_block_edges_intervals, atfs, _, indices_to_states = create_safe_intervals(block_intervals, g_block, buffer_times, recovery_times, float(agent_speed), print_intervals=False)
    safe_computation_time = time.time() - start_time
    write_intervals_to_file(output, safe_block_intervals, atfs, indices_to_states)
    if plot:
        plot_blocking_staircase(block_intervals, block_routes, moves_per_agent, g.distance_markers, buffer_times, recovery_times)
    return unsafe_computation_time + safe_computation_time

if __name__ == "__main__":
    args = parser.parse_args()
    g = read_graph(args.location)
    g_block = BlockGraph(g)
    unsafe_node_intervals, unsafe_edge_intervals, block_intervals, agent_intervals, moves_per_agent, computation_time = read_scenario(args.scenario, g, g_block, args.agent_id)
    block_routes = convertMovesToBlock(moves_per_agent, g)
    buffer_times, recovery_times = flexibility(block_intervals, block_routes, float(args.buffer), args.recovery.strip().lower() == "true")
    plot_blocking_staircase(block_intervals, block_routes, moves_per_agent, g.distance_markers, buffer_times, recovery_times)
    safe_block_intervals, safe_block_edges_intervals, atfs, _, indices_to_states = create_safe_intervals(block_intervals, g_block, buffer_times, recovery_times, float(args.agent_speed), args.recovery.strip().lower() == "true")
    write_intervals_to_file(args.output, safe_block_intervals, atfs, indices_to_states)
    # plot_safe_node_intervals(safe_block_intervals | safe_block_edges_intervals, block_routes)