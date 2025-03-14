import numpy as np

from generation.graph import Graph, Node, Edge


def expand_block(track, end_tracks):
    if track in end_tracks or len(track.outgoing) == 0:
        return [[track]]
    routes = []
    expanded_blocks = [expand_block(e.to_node, end_tracks) for e in track.outgoing]
    for bl in expanded_blocks:
        routes.extend([[track] + block for block in bl])
    return routes

def flatten(xss):
    return [x for xs in xss for x in xs]

def generate_signal_blocks(from_signal, signals):
    end_tracks = [s.track for s in signals]
    routes = flatten([expand_block(e.to_node, end_tracks) for e in from_signal.track.outgoing])
    return routes

def create_graph_blocks(g):
    g_block = Graph()
    for signal in g.signals:
        signal_node = g_block.add_node(Node(f"r-{signal.id}", "RailRoad"))
        signal.track.routes.append(signal_node)

    for signal in g.signals:
        routes = generate_signal_blocks(signal, g.signals)
        for idx, route in enumerate(routes):

            length = 0
            # Add count total length of route
            for idx2, node in enumerate(route):
                if node.outgoing:
                    if idx2 < len(route) - 1:
                        length += get_length_of_edge(node, route[idx2 + 1])
                    else:
                        # Signal is at the end of this track, add the track length
                        length += node.outgoing[0].length

            # Create edges in g_block
            from_signal_node = g_block.nodes[f"r-{signal.id}"]

            # Only add edge if a signal is found at the end of the route
            to_signal = [signal for signal in g.signals if signal.track == route[-1]]
            if len(to_signal) == 1:
                to_signal_node = g_block.nodes[f"r-{to_signal[0].id}"]
                route_edge = g_block.add_edge(Edge(from_signal_node, to_signal_node, length))

                for node in route:
                    node.routes.append(route_edge)
    return g_block


def get_length_of_edge(from_node, to_node):
    res = [out.length for out in from_node.outgoing if out.to_node == to_node]
    assert len(res) == 1
    return res[0]


def convertMovesToBlock(moves_per_agent, g):
    block_routes = {}
    for agent in moves_per_agent:
        block_route = []
        for movements in moves_per_agent[agent]:
            routes = None
            for move in movements:
                if move.from_node in [signal.track for signal in g.signals]:
                    if routes:
                        assert len(routes) == 1
                        block_route.append(list(routes)[0])
                    routes = set(move.to_node.routes)
                routes = routes & set(move.to_node.routes)
        block_routes[agent] = [block_route]
    return block_routes