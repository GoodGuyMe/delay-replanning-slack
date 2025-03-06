import json 
from pathlib import Path

from generation.signal_sections import generate_signal_blocks


class Node:
    def __init__(self, name, type):
        self.name = name
        self.type = type
        self.outgoing = []
        self.incoming = []
        self.associated = []
        self.opposites = []
        self.canReverse = False
        self.stationPlatform = False
        self.routes = []

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.name == other.name
        return False

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(self.name)

    def __repr__(self) -> str:
        # return f"Node {self.name} of type {self.type} coming from {self.incoming} and going to {self.outgoing}\n"
        return f"Node {self.name}"

class Edge:
    def __init__(self, f, to, l):
        self.from_node = f
        self.to_node = to
        self.length = l
        self.opposites = []
        self.associated = []
        self.depart_time = None
        self.start_time = None
        self.max_speed = 50
        self.stops_at_station = None
    
    def get_identifier(self):
        return f"{self.from_node.name}--{self.to_node.name}"

    def __repr__(self) -> str:
        return f"Edge from {self.from_node.name} to {self.to_node.name} with length {self.length}"

    def set_depart_time(self, time):
        self.depart_time = time

    def set_start_time(self, time):
        self.start_time = time

    # def __eq__(self, other):
    #     if isinstance(other, Edge):
    #         return self.from_node == other.from_node and self.to_node == other.to_node
    #     return False

class Graph:
    def __init__(self):
        self.edges = []
        self.nodes = {}
        self.signals = []
        self.global_end_time = -1
        self.distance_markers = {}

    def add_node(self, n):
        if type(n) is Node:
            self.nodes[n.name] = n
            return n
    
    def add_edge(self, e):
        if type(e) is Edge:
            self.edges.append(e)
            e.to_node.incoming.append(e)
            e.from_node.outgoing.append(e)
            return e

    def add_signal(self, s):
        if type(s) is Signal:
            self.signals.append(s)
    
    def __repr__(self) -> str:
        return f"Graph with {len(self.edges)} edges and {len(self.nodes)} nodes:\n{self.nodes.values()}"

class Signal:
    def __init__(self, id, track):
        self.id = id
        self.track = track
    
def read_graph(file):
    try:
        base_path = Path(__file__).parent
        file_path = (base_path / file).resolve()
        data = json.load(open(file_path))
    except:
        data = json.load(open(file))
    g = Graph()
    nodes_per_id_A = {}
    nodes_per_id_B = {}
    track_lengths = {}
    for track in data["trackParts"]:
        track_lengths[track["id"]] = track["length"]
        if track["type"] == "RailRoad":
            a = g.add_node(Node(track["name"] + "A", track["type"]))
            b = g.add_node(Node(track["name"] + "B", track["type"]))
            if track["stationPlatform"]:
                a.stationPlatform = True
                b.stationPlatform = True
            # A/B nodes are associated because the have the same interval on the node if train can reverse
            if track["sawMovementAllowed"]:
                a.associated.append(b)
                b.associated.append(a)
                a.canReverse = True
                b.canReverse = True
            # A/B nodes are opposite because they have opposite edges attaches
            a.opposites.append(b)
            b.opposites.append(a)
            nodes_per_id_A[track["id"]] = [track["name"] + "A"]
            nodes_per_id_B[track["id"]] = [track["name"] + "B"]
        # Nodes on the same side of a switch are not associated -> they do not have same intervals, but the edges do
        elif track["type"] == "Switch":
            if len(track["aSide"]) > len(track["bSide"]):
                a = g.add_node(Node(track["name"] + "AR", track["type"]))
                b = g.add_node(Node(track["name"] + "AL", track["type"]))
                c = g.add_node(Node(track["name"] + "B", track["type"]))
                a.opposites.extend([c])
                b.opposites.extend([c])
                c.opposites.extend([a, b])
                nodes_per_id_A[track["id"]] = [track["name"] + "AR", track["name"] + "AL"]
                nodes_per_id_B[track["id"]] = [track["name"] + "B"]
            else:
                a = g.add_node(Node(track["name"] + "A", track["type"]))
                b = g.add_node(Node(track["name"] + "BR", track["type"]))
                c = g.add_node(Node(track["name"] + "BL", track["type"]))
                a.opposites.extend([b, c])
                b.opposites.extend([a])
                c.opposites.extend([a])
                nodes_per_id_A[track["id"]] = [track["name"] + "A"]
                nodes_per_id_B[track["id"]] = [track["name"] + "BR", track["name"] + "BL"]
        elif track["type"] == "EnglishSwitch":
            a = g.add_node(Node(track["name"] + "AR", track["type"]))
            b = g.add_node(Node(track["name"] + "AL", track["type"]))
            c = g.add_node(Node(track["name"] + "BR", track["type"]))
            d = g.add_node(Node(track["name"] + "BL", track["type"]))
            a.opposites.extend([c, d])
            b.opposites.extend([c, d])
            c.opposites.extend([a, b])
            d.opposites.extend([a, b])
            nodes_per_id_A[track["id"]] = [track["name"] + "AR", track["name"] + "AL"]
            nodes_per_id_B[track["id"]] = [track["name"] + "BR", track["name"] + "BL"]
    for track in data["trackParts"]:
        if track["type"] != "Bumper":
            aEdges = []
            bEdges = []
            bumperAside, bumperBside = True, True
            for i, aSideId in enumerate(track["aSide"]):
                fromNode = nodes_per_id_A[track["id"]][i]
                if aSideId in nodes_per_id_A:
                    bumperAside = False
                    # Connect the aSide node(s) to the respective edges
                    for aSideToTrack in nodes_per_id_A[aSideId]:
                        length = track_lengths[aSideId]
                        e = g.add_edge(Edge(g.nodes[aSideToTrack], g.nodes[fromNode], length))
                        aEdges.append(e)
                # This side is a bumper, so the other side attaches to itself
                elif g.nodes[fromNode].type == "RailRoad" and track["sawMovementAllowed"]:
                    toNode = nodes_per_id_B[track["id"]][i]
                    g.add_edge(Edge(g.nodes[toNode], g.nodes[fromNode], 0))
            for i, bSideId in enumerate(track["bSide"]):
                fromNode = nodes_per_id_B[track["id"]][i]
                if bSideId in nodes_per_id_B:
                    bumperBside = False
                    # Connect the bSide node(s) to the respective neighbors
                    for bSideToTrack in nodes_per_id_B[bSideId]:
                        length = track_lengths[bSideId]
                        e = g.add_edge(Edge(g.nodes[bSideToTrack], g.nodes[fromNode], length))
                        bEdges.append(e) 
                # This side is a bumper, so the other side attaches
                elif g.nodes[nodes_per_id_B[track["id"]][i]].type == "RailRoad" and track["sawMovementAllowed"]:
                    toNode = nodes_per_id_A[track["id"]][i]
                    g.add_edge(Edge(g.nodes[toNode], g.nodes[fromNode], 0))
            # If it is a double-ended (not dead-end) track where parking is allowed, then we can go from A->B and B->A
            if track["type"] == "RailRoad" and track["sawMovementAllowed"] and not bumperAside and not bumperBside:
                g.add_edge(Edge(g.nodes[nodes_per_id_A[track["id"]][i]], g.nodes[nodes_per_id_B[track["id"]][i]], 0))
                g.add_edge(Edge(g.nodes[nodes_per_id_B[track["id"]][i]], g.nodes[nodes_per_id_A[track["id"]][i]], 0))
            # Assign the associated edges (same side of switch)                  
            for x in aEdges:
                for y in aEdges:
                    if x != y and (x.from_node.name == y.from_node.name or x.to_node.name == y.to_node.name):
                        x.associated.append(y)
                        y.associated.append(x)
            for x in bEdges:
                for y in bEdges:
                    if x != y and (x.from_node.name == y.from_node.name or x.to_node.name == y.to_node.name):
                        x.associated.append(y)
                        y.associated.append(x)
    # Assign the opposite edges (opposite direction)
    for node in g.nodes:
        for e in g.nodes[node].outgoing:
            for opposite_node in g.nodes[node].opposites:
                for other_edge in g.nodes[opposite_node.name].incoming:
                    if other_edge.from_node in e.to_node.opposites:
                        e.opposites.append(other_edge)
        for e in g.nodes[node].incoming:
            for opposite_node in g.nodes[node].opposites:
                for other_edge in g.nodes[opposite_node.name].outgoing:
                    if other_edge.to_node in e.from_node.opposites:
                        e.opposites.append(other_edge)

    g.distance_markers = data["distanceMarkers"] if "distanceMarkers" in data else {"Start": 0}
    min_distance = min(g.distance_markers.values())
    for key, val in g.distance_markers.items():
        g.distance_markers[key] = val - min_distance

    # Extract signal locations
    signals = data["signals"] if "signals" in data else []
    for signal in signals:
        if signal["side"] == "A":
            track = g.nodes[nodes_per_id_A[signal["track"]][0]]
        else:
            track = g.nodes[nodes_per_id_B[signal["track"]][0]]
        g.add_signal(Signal(signal["name"], track))

    g_block = Graph()
    for signal in g.signals:
        g_block.add_node(Node(f"r-{signal.id}", "RailRoad"))

    for signal in g.signals:
        routes = generate_signal_blocks(signal, g.signals)
        for idx, route in enumerate(routes):
            # Add node in g
            # route_node = g_block.add_node(Node(f"r-{signal.id}_{idx}", "RailRoad"))

            length = 0

            # Add reference in every node that is part of that route to the route node, also count total length of route
            for idx2, node in enumerate(route):
                # node.routes.append(route_node.name)
                if 0 < idx2 < len(route) - 1:
                    length += get_length_of_edge(g, node, route[idx2 + 1])
                else:
                    length += node.outgoing[0].length if node.outgoing else 0

            # Create edges in g_block
            from_signal_node = g_block.nodes[f"r-{signal.id}"]

            # Only add edge if a signal is found at the end of the route
            to_signal = [signal for signal in g.signals if signal.track == route[-1]]
            if len(to_signal) == 1:
                to_signal_node = g_block.nodes[f"r-{to_signal[0].id}"]
                g_block.add_edge(Edge(from_signal_node, to_signal_node, length))
            else:
                print(to_signal)

    return g, g_block

def get_length_of_edge(g, from_node, to_node):
    length = [edge.length for edge in g.edges if edge.from_node == from_node and edge.to_node == to_node][0]
    return length

def print_node_intervals_per_train(node_intervals, edge_intervals, g, move=None):
    ### Print the intervals
    if move:
        print(f"\nMove from {move['startLocation']} to {move['endLocation']}\nUNSAFE INTERVALS\n")
    for train in node_intervals:
        print(f"=====Train {train}======")
        for n in node_intervals[train]:
            if len(node_intervals[train][n]) > 0:
                print(f"Node {n} has {len(node_intervals[train][n])} intervals:")
                for x in node_intervals[train][n]:
                    print(f"    <{x[0]},{x[1]}>")
                for e in g.nodes[n].outgoing:
                    if len(edge_intervals[train][e.get_identifier()]) > 0:
                        print(f"    Edge {e.get_identifier()} has {len(edge_intervals[train][e.get_identifier()])} intervals:")
                        for x in edge_intervals[train][e.get_identifier()]:
                            print(x)
    print("END\n\n")