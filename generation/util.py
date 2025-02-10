import json 
from pathlib import Path

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

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.name == other.name
        return False

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(self.name)

    def __repr__(self) -> str:
        return f"Node {self.name} of type {self.type} coming from {self.incoming} and going to {self.outgoing}\n"

class Edge:
    def __init__(self, f, to, l):
        self.from_node = f
        self.to_node = to
        self.length = l
        self.opposites = []
        self.associated = []
        self.depart_time = None
        self.start_time = None
    
    def get_identifier(self):
        return f"{self.from_node.name}--{self.to_node.name}"

    def __repr__(self) -> str:
        return f"Edge from {self.from_node.name} to {self.to_node.name} with length {self.length}"

    def set_depart_time(self, time):
        self.depart_time = time

    def set_start_time(self, time):
        self.start_time = time

class Graph:
    def __init__(self):
        self.edges = []
        self.nodes = {}
        self.global_end_time = -1

    def add_node(self, n):
        if type(n) is Node:
            self.nodes[n.name] = n
            return n
    
    def add_edge(self, e):
        if type(e) is Edge:
            self.edges.append(e)
            return e
    
    def __repr__(self) -> str:
        return f"Graph with {len(self.edges)} edges and {len(self.nodes)} nodes:\n{self.nodes.values()}"
    
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
                        length = track["length"]
                        if g.nodes[aSideToTrack].type == "RailRoad":
                            length = track_lengths[aSideId]
                        e = g.add_edge(Edge(g.nodes[aSideToTrack], g.nodes[fromNode], length))
                        g.nodes[fromNode].incoming.append(e)
                        g.nodes[aSideToTrack].outgoing.append(e)
                        aEdges.append(e)
                # This side is a bumper, so the other side attaches to itself
                elif g.nodes[fromNode].type == "RailRoad" and track["sawMovementAllowed"]:
                    toNode = nodes_per_id_B[track["id"]][i]
                    e = g.add_edge(Edge(g.nodes[toNode], g.nodes[fromNode], 0))
                    g.nodes[fromNode].incoming.append(e)
                    g.nodes[toNode].outgoing.append(e)
            for i, bSideId in enumerate(track["bSide"]):
                fromNode = nodes_per_id_B[track["id"]][i]
                if bSideId in nodes_per_id_B:
                    bumperBside = False
                    # Connect the bSide node(s) to the respective neighbors
                    for bSideToTrack in nodes_per_id_B[bSideId]:
                        length = track["length"]
                        if g.nodes[bSideToTrack].type == "RailRoad":
                            length = track_lengths[bSideId]
                        e = g.add_edge(Edge(g.nodes[bSideToTrack], g.nodes[fromNode], length))
                        g.nodes[fromNode].incoming.append(e)
                        g.nodes[bSideToTrack].outgoing.append(e)
                        bEdges.append(e) 
                # This side is a bumper, so the other side attaches
                elif g.nodes[nodes_per_id_B[track["id"]][i]].type == "RailRoad" and track["sawMovementAllowed"]:
                    toNode = nodes_per_id_A[track["id"]][i]
                    e = g.add_edge(Edge(g.nodes[toNode], g.nodes[fromNode], 0))
                    g.nodes[fromNode].incoming.append(e)
                    g.nodes[toNode].outgoing.append(e)
            # If it is a double-ended (not dead-end) track where parking is allowed, then we can go from A->B and B->A
            if track["type"] == "RailRoad" and track["sawMovementAllowed"] and not bumperAside and not bumperBside:
                e = g.add_edge(Edge(g.nodes[nodes_per_id_A[track["id"]][i]], g.nodes[nodes_per_id_B[track["id"]][i]], 0))
                g.nodes[nodes_per_id_B[track["id"]][i]].incoming.append(e)
                g.nodes[nodes_per_id_A[track["id"]][i]].outgoing.append(e)
                e = g.add_edge(Edge(g.nodes[nodes_per_id_B[track["id"]][i]], g.nodes[nodes_per_id_A[track["id"]][i]], 0))
                g.nodes[nodes_per_id_A[track["id"]][i]].incoming.append(e)
                g.nodes[nodes_per_id_B[track["id"]][i]].outgoing.append(e)
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
    return g

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