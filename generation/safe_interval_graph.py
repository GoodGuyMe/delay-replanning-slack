from datetime import timedelta
from logging import getLogger

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.lines import Line2D

from generation.graph import BlockEdge, TrackEdge, Direction, BlockGraph

logger = getLogger('__main__.' + __name__)

def replaceAB(node, intervals):
    if "A" in node:
        node = node.replace("AR", "B")
        node = node.replace("AL", "B")
        node = node.replace("A", "B")
        if node + "R" in intervals:
            return node + "L"
        return node
    node = node.replace("BR", "A")
    node = node.replace("BL", "A")
    node = node.replace("B", "A")
    if node + "R" in intervals:
        return node + "L"
    return node

def plot_train_path(moves_per_agent, color_map=None, node_map=None, exclude_agent=-1):
    for agent_id, movements in moves_per_agent.items():
        if agent_id == exclude_agent:
            continue
        length_in_block = {b: 0 for b in node_map}
        color=None
        for movement in movements:
            for edge in movement:
                plotting_info = edge.plotting_info
                if plotting_info and agent_id in plotting_info:
                    block = plotting_info[agent_id]["block"].get_identifier()
                    if block in node_map:
                        y, e = node_map[block]
                        lib = length_in_block[block]
                        y = y + lib
                        start = plotting_info[agent_id]["start_time"]
                        end = plotting_info[agent_id]["end_time"]
                        train, = plt.plot([y, y + edge.length], [start, end], color=color,
                                          linestyle="-")
                        length_in_block[block] = lib + edge.length
                        color=train.get_color()
        if color_map is not None:
            color_map[agent_id] = color

def plot_blocking_staircase(blocking_times, block_routes, moves_per_agent, g_block: BlockGraph, buffer_times, recovery_times, plot_routes=None, exclude_agent=-1):
    node_map = dict()
    y = 0
    ax = plt.gca()
    plt.grid()

    x_axis = []
    xtics = []

    plot_route_track, plot_route_block = None, None
    if plot_routes:
        plot_route_track, plot_route_block = plot_routes

    if plot_route_block is None:
        for agent_id, movements in block_routes.items():
            for movement in movements:
                for edge in movement:
                    node = edge.get_identifier()
                    if node not in node_map:
                        node_map[str(node)] = (y, edge)
                        y += edge.length
    else:
        for edge in plot_route_block:
            node = edge.get_identifier()
            if node not in node_map:
                node_map[str(node)] = (y, edge)
                y += edge.length

    color_map = {}

    plot_train_path(moves_per_agent, color_map, node_map, exclude_agent)
    use_bt = False
    use_crt = False


    for node, (y, edge) in node_map.items():
        for start, stop, duration, train, recovery in blocking_times[edge.get_identifier()]:
            blocking_time = patches.Rectangle((y, start), edge.length, stop - start, linewidth=1, edgecolor='red', facecolor='none')
            ax.add_patch(blocking_time)
            if train != 0 and node in buffer_times[train]:
                # errors = np.zeros((2, 1))
                # errors[1, 0] = buffer_times[train][node]
                # ax.errorbar((2 * y + edge.length) / 2, stop, yerr=errors, fmt="none", color=color_map[train])
                if buffer_times[train][node] > 0:
                    use_bt = True
                    error_block = patches.Rectangle((y, stop), edge.length, buffer_times[train][node], linewidth=1, facecolor=color_map[train], alpha=0.3)
                    ax.add_patch(error_block)

                # if recovery_times[train][node] > 0:
                #     use_crt = True
                #     recovery_block = patches.Rectangle((y, stop), edge.length, recovery_times[train][node], linewidth=1, facecolor=None, alpha=0.0, hatch=r"\\")
                #     ax.add_patch(recovery_block)

    plt.ylabel(f"Time (s)")
    plt.xlabel(f"Distance")

    legend_items = [
        Line2D([0], [0], color="green", label="Train Path"),
        patches.Patch(facecolor=None,   edgecolor="red", label="Blocking Time", fill=False),
    ]
    if use_bt:
        legend_items.append(patches.Patch(facecolor="green", edgecolor=None,  label="Buffer time", alpha=0.3),)
    if use_crt:
        legend_items.append(patches.Patch(hatch=r"\\\\", edgecolor=None,  label="Recovery time", alpha=0.0))
    plt.legend(handles=legend_items ,loc="upper left")
    station_identifiers = {}
    for station, (n_a, n_b) in g_block.stations.items():
        for e in g_block.nodes[n_a].outgoing:
            station_identifiers[e.get_identifier()] = station
        for e in g_block.nodes[n_b].outgoing:
            station_identifiers[e.get_identifier()] = station

    for block_id, (dist, edge) in node_map.items():
        if block_id in station_identifiers:
                xtics.append(station_identifiers[block_id])
        # else:
        #     xtics.append("")
                x_axis.append(dist)

    # for key, value in distance_markers.items():
    #     x_axis.append(value)
    #     xtics.append(key)

    plt.xticks(x_axis, xtics, rotation=90)
    ax.set_yticklabels([str(timedelta(seconds=ytick)) for ytick in ax.get_yticks()])
    plt.tight_layout()


    # plt.gca().invert_yaxis()
    plt.title(f"Agents")
    plt.savefig("images/blocking_staircase")
    plt.show()