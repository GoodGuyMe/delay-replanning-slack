import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.lines import Line2D


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

def plot_train_path(moves_per_agent, color_map=None, plot_route_track=None):
    node_map2 = dict()
    y2 = 0
    plot_nodes = {edge.from_node.name for edge in plot_route_track}
    for agent_id, movements in moves_per_agent.items():
        color=None
        for movement in movements:
            for edge in movement:
                node = edge.from_node.name
                if node not in node_map2:
                    node_map2[node] = (y2, edge)
                    y2 += edge.length
                if node in node_map2 and node in plot_nodes:
                    y_cur, old_len = node_map2[node]
                    linestyle = "-"
                    train, = plt.plot([y_cur, y_cur + edge.length], [edge.start_time[agent_id], edge.depart_time[agent_id]], color=color,
                                      linestyle=linestyle)
                    color=train.get_color()
        if color_map is not None:
            color_map[agent_id] = color

def plot_blocking_staircase(blocking_times, block_routes, moves_per_agent, distance_markers, buffer_times, recovery_times, xtics_dist = 5000, plot_routes=None):
    node_map = dict()
    y = 0
    ax = plt.gca()
    plt.grid()

    x_axis = []
    xtics = []

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

    plot_train_path(moves_per_agent, color_map, plot_route_track)


    for node, (y, edge) in node_map.items():
        for start, stop, duration, train, recovery in blocking_times[edge.get_identifier()]:
            blocking_time = patches.Rectangle((y, start), edge.length, stop - start, linewidth=1, edgecolor='red', facecolor='none')
            ax.add_patch(blocking_time)
            if train != 0 and node in buffer_times[train]:
                # errors = np.zeros((2, 1))
                # errors[1, 0] = buffer_times[train][node]
                # ax.errorbar((2 * y + edge.length) / 2, stop, yerr=errors, fmt="none", color=color_map[train])

                error_block = patches.Rectangle((y, stop), edge.length, buffer_times[train][node], linewidth=1, facecolor=color_map[train], alpha=0.3)
                recovery_block = patches.Rectangle((y, stop), edge.length, recovery_times[train][node], linewidth=1, facecolor=None, alpha=0.0, hatch=r"\\")
                ax.add_patch(error_block)
                ax.add_patch(recovery_block)

    plt.ylabel(f"Time (s)")
    plt.xlabel(f"Distance")

    legend_items = [
        Line2D([0], [0], color="green", label="Train Path"),
        patches.Patch(facecolor=None,   edgecolor="red", label="Blocking Time", fill=False),
        patches.Patch(facecolor="green", edgecolor=None,  label="Buffer time", alpha=0.3),
        patches.Patch(hatch=r"\\\\", edgecolor=None,  label="Recovery time", alpha=0.0)
    ]
    plt.legend(handles=legend_items ,loc="upper left")
    last_dist = float("-inf")

    for (dist, edge) in node_map.values():
        if "r" in edge.from_node.name:
            if last_dist < dist:
                last_dist = dist + xtics_dist
                xtics.append(edge.from_node.name[2:])
            else:
                xtics.append("")
            x_axis.append(dist)

    for key, value in distance_markers.items():
        x_axis.append(value)
        xtics.append(key)

    plt.xticks(x_axis, xtics, rotation=90)
    plt.tight_layout()


    # plt.gca().invert_yaxis()
    plt.title(f"Agents")
    plt.savefig("images/blocking_staircase")
    plt.show()