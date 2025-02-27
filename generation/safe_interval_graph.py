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
                node = edge.from_node.name
                if node not in node_map:
                    node_map[node] = y
                    y += 1
                node = edge.to_node.name
                if node not in node_map:
                    node_map[node] = y
                    y += 1
        for node, y in node_map.items():
            for start, stop in safe_node_intervals[node]:
                plt.plot([start, stop], [y, y], color='green')

        y_axis = list(node_map.values())
        ytics = list(node_map.keys())

        # plt.xlim([0, 4000])

        plt.yticks(y_axis, ytics)
        plt.title(f"Agent {agent_id}")
        plt.show()

        for node, y in node_map.items():
            for start, stop in safe_node_intervals[replaceAB(node, safe_node_intervals)]:
                plt.plot([start, stop], [y, y], color='green')

        y_axis = list(node_map.values())
        ytics = [replaceAB(node,safe_node_intervals) for node in node_map.keys()]

        # plt.xlim([0, 4000])

        plt.yticks(y_axis, ytics)
        plt.title(f"Agent {agent_id} opposite")
        plt.show()

def plot_unsafe_node_intervals(unsafe_node_intervals, moves_per_agent, distance_markers, fixed_block=False):
    node_map = dict()
    y = 0
    ax = plt.gca()
    max_time = 0
    hw = None
    train = None
    for agent_id, movements in moves_per_agent.items():
        for movement in movements:
            for edge in movement:
                node = edge.from_node.name
                if node not in node_map:
                    node_map[node] = (y, edge)
                    y += edge.length
                y_cur, old_len = node_map[node]
                train, = plt.plot([y_cur, y_cur + edge.length], [edge.start_time, edge.depart_time], color='black', linestyle='--')
                max_time = max(max_time, edge.depart_time)
        for node, (y, edge) in node_map.items():
            for start, stop, duration in unsafe_node_intervals[node]:
                if fixed_block:
                    occupied = patches.Rectangle((y, start), edge.length, duration, linewidth=1, edgecolor='red', facecolor='none')
                    ax.add_patch(occupied)
                else:
                    hw, = plt.plot([y, y+edge.length], [start + 180, start + duration + 180], color='red', linestyle='-')
                # ax.add_patch(headway)

    plt.ylabel(f"Time (s)")
    plt.xlabel(f"Distance")

    train.set_label("Train") if train else None
    hw.set_label("Headway") if hw else None
    plt.legend()

    distances = [n for (n, _) in node_map.values()]
    tracks = list(node_map.keys())
    print(tracks)

    x_axis = []
    xtics = []

    max_distance = max(distances)

    # for track, distance in zip(tracks, distances):
    #     if "t" in track:
    #         x_axis.append(distance)
    #         xtics.append(track)


    for key, value in distance_markers.items():
        if value < max_distance:
            x_axis.append(value)
            xtics.append(key)

    plt.xticks(x_axis, xtics, rotation=90)
    plt.title(f"Agents")
    plt.show()