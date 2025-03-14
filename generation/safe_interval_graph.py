import matplotlib.pyplot as plt
import matplotlib.patches as patches

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

def plot_train_path(moves_per_agent):
    train = None
    node_map2 = dict()
    y2 = 0
    if moves_per_agent:
        for agent_id, movements in moves_per_agent.items():
            for movement in movements:
                for edge in movement[1:]:
                    node = edge.from_node.name
                    if node not in node_map2:
                        node_map2[node] = (y2, edge)
                        y2 += edge.length
                    y_cur, old_len = node_map2[node]
                    train, = plt.plot([y_cur, y_cur + edge.length], [edge.start_time, edge.depart_time], color='black',
                                      linestyle='--')
    return train

def plot_safe_node_intervals(safe_node_intervals, moves_per_agent=None):
    if moves_per_agent is None:
        node_map = dict()
        for idx, node in enumerate(safe_node_intervals):
            node_map[node] = idx
            for start, stop in safe_node_intervals[node]:
                plt.plot([start, stop], [idx, idx], label=node, color='red')
        y_axis = list(node_map.values())
        ytics = list(node_map.keys())
        plt.yticks(y_axis, ytics)
        plt.show()
        return
    for agent_id, movements in moves_per_agent.items():
        node_map = dict()
        y = 0
        for movement in movements:
            for edge in movement:
                node = edge.from_node
                if node not in node_map:
                    node_map[node] = y
                    y += 1
                node = edge
                if node not in node_map:
                    node_map[node] = y
                    y += 1
                node = edge.to_node
                if node not in node_map:
                    node_map[node] = y
                    y += 1
        for node, y in node_map.items():
            for start, stop in safe_node_intervals[node.get_identifier()]:
                plt.plot([start, stop], [y, y], color='green')

        y_axis = list(node_map.values())
        ytics = list(node_map.keys())

        plt.xlim([0, 3000])

        plt.yticks(y_axis, ytics)
        plt.title(f"Agent {agent_id}")
        plt.show()

def plot_unsafe_node_intervals(unsafe_node_intervals, moves_per_agent, distance_markers, fixed_block=False, moves_per_agent_2=None):
    node_map = dict()
    y = 0
    ax = plt.gca()
    hw = None

    x_axis = []
    xtics = []

    for agent_id, movements in moves_per_agent.items():
        for movement in movements:
            for edge in movement:
                node = edge.from_node.name
                if "_" not in node and fixed_block:
                    x_axis.append(y)
                    xtics.append(node)
                if node not in node_map:
                    node_map[node] = (y, edge)
                    y += edge.length
        for node, (y, edge) in node_map.items():
            if fixed_block:
                pass
                for start, stop, duration in unsafe_node_intervals[node]:
                    blocking_time = patches.Rectangle((y, start), edge.length, duration, linewidth=1, edgecolor='red', facecolor='none')
                    ax.add_patch(blocking_time)
            else:
                for start, stop, duration in unsafe_node_intervals[node]:
                    hw, = plt.plot([y, y+edge.length], [start + 180, start + duration + 180], color='red', linestyle='-')


    plt.ylabel(f"Time (s)")
    plt.xlabel(f"Distance")

    train = plot_train_path(moves_per_agent)
    train.set_label("Train") if train else None
    hw.set_label("Headway") if hw else None
    plt.legend()


    max_distance = 40000

    for key, value in distance_markers.items():
        if value < max_distance:
            x_axis.append(value)
            xtics.append(key)

    plt.xticks(x_axis, xtics, rotation=90)
    plt.title(f"Agents")
    plt.show()


def plot_blocking_staircase(blocking_times, block_routes, moves_per_agent, distance_markers):
    node_map = dict()
    y = 0
    ax = plt.gca()

    x_axis = []
    xtics = []

    for agent_id, movements in block_routes.items():
        for movement in movements:
            for edge in movement:
                node = edge.get_identifier()
                if node not in node_map:
                    node_map[str(node)] = (y, edge)
                    y += edge.length
        for node, (y, edge) in node_map.items():
            for start, stop, duration in blocking_times[edge.get_identifier()]:
                blocking_time = patches.Rectangle((y, start), edge.length, stop - start, linewidth=1, edgecolor='red', facecolor='none')
                ax.add_patch(blocking_time)

    plt.ylabel(f"Time (s)")
    plt.xlabel(f"Distance")

    train = plot_train_path(moves_per_agent)
    train.set_label("Train") if train else None
    plt.legend()

    for (dist, edge) in node_map.values():
        if "r" in edge.from_node.name:
            x_axis.append(dist)
            xtics.append(edge.from_node.name)

    max_distance = 40000

    for key, value in distance_markers.items():
        if value < max_distance:
            x_axis.append(value)
            xtics.append(key)

    plt.xticks(x_axis, xtics, rotation=90)
    plt.title(f"Agents")
    plt.show()