import matplotlib.pyplot as plt

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

def plot_unsafe_node_intervals(unsafe_node_intervals, moves_per_agent):
    for agent_id, movements in moves_per_agent.items():
        node_map = dict()
        y = 0
        for movement in movements:
            for edge in movement:
                node = edge.from_node.name
                if node not in node_map:
                    y += edge.length
                    node_map[node] = y
                node = edge.to_node.name
                if node not in node_map:
                    y += edge.length
                    node_map[node] = y
                plt.plot([edge.start_time, edge.depart_time], [node_map[edge.from_node.name], node_map[edge.to_node.name]], color='green', linestyle='--')
        for node, y in node_map.items():
            for start, stop, duration in unsafe_node_intervals[node]:
                plt.plot([start, start + duration], [y, y], color='green')
                plt.plot([start + duration, stop], [y, y], color='red')

        y_axis = list(node_map.values())
        ytics = list(node_map.keys())

        # plt.xlim([0, 4000])

        plt.yticks(y_axis, ytics)
        plt.title(f"Agent {agent_id}")
        plt.show()