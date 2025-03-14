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

    def get_identifier(self):
        return f"{self.name}"

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

    def __str__(self) -> str:
        # return f"Node {self.name} of type {self.type} coming from {self.incoming} and going to {self.outgoing}\n"
        return f"{self.name}"


class Edge:
    __last_id = 1
    def __init__(self, f, to, l):
        self.id = Edge.__last_id
        Edge.__last_id += 1
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
        return f"{self.from_node.name}--{self.to_node.name}--{self.id}"

    def __repr__(self) -> str:
        return f"Edge from {self.from_node.name} to {self.to_node.name} with length {self.length}"

    def set_depart_time(self, time):
        self.depart_time = time

    def set_start_time(self, time):
        self.start_time = time

    def __eq__(self, other):
        if isinstance(other, Edge):
            return self.from_node == other.from_node and self.to_node == other.to_node
        return False

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(self.id)

    def __str__(self):
        return f"{self.from_node.name}--{self.to_node.name}"


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