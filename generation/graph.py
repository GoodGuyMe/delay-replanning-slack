from __future__ import annotations

import contextlib
import re
import os
import pickle
import logging
import tqdm
from typing import Iterator

import generation.GraphPickler

from queue import Queue
from copy import copy
from logging import getLogger

logger = getLogger('__main__.' + __name__)

class TqdmLogger:
    """File-like class redirecting tqdm progress bar to given logging logger."""
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def write(self, msg: str) -> None:
        self.logger.info(msg.lstrip("\r"))

    def flush(self) -> None:
        pass

class Node:
    def __init__(self, name):
        self.name = name
        self.outgoing:list[Edge] = []
        self.incoming:list[Edge] = []

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

class BlockNode(Node):
    def __init__(self, name):
        super().__init__(name)

class TrackNode(Node):
    def __init__(self, name, type):
        super().__init__(name)
        self.associated:list[Node] = []
        self.opposites:list[Node] = []
        self.blocks:list[BlockEdge] = []
        self.canReverse = False
        self.stationPlatform = False
        self.type = type
        self.direction = ''.join(set(re.findall("[AB]", f"{name[-2:]}")))
        if self.direction != "A" and self.direction != "B":
            raise ValueError("Direction must be either A or B")


class Signal:
    def __init__(self, id, track: TrackNode):
        self.id = id
        self.track = track
        self.direction = track.direction

    def __repr__(self) -> str:
        return f"Signal {self.id} on track {self.track}"


class Edge:
    __last_id = 1
    def __init__(self, f:Node, t:Node, l):
        self.id = Edge.__last_id
        Edge.__last_id += 1
        self.from_node = f
        self.to_node = t
        self.length = l

    def get_identifier(self):
        return f"{self.from_node.name}--{self.to_node.name}--{self.id}"

    def __repr__(self) -> str:
        return f"Edge from {self.from_node.name} to {self.to_node.name} with length {self.length}"

    def __eq__(self, other):
        if isinstance(other, Edge):
            return self.from_node == other.from_node and self.to_node == other.to_node
        return False

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(self.id)

    def __str__(self):
        return f"{self.from_node.name}--{self.to_node.name}"

class BlockEdge(Edge):
    def __init__(self, f, t, l, tracknodes_on_route:list[TrackNode], direction):
        super().__init__(f, t, l)
        self.trackNodes:list[TrackNode] = list(tracknodes_on_route)
        for n in tracknodes_on_route:
            self.trackNodes.extend(n.associated)
            self.trackNodes.extend(n.opposites)
        self.direction = direction

    def get_affected_blocks(self) -> list:
        affected_blocks = set()
        for node in self.trackNodes:
            affected_blocks = affected_blocks.union(set(node.blocks))
        return list(affected_blocks)


class TrackEdge(Edge):
    def __init__(self, f, t, l):
        super().__init__(f, t, l)
        self.depart_time = {}
        self.start_time = {}
        self.opposites:  list[Edge] = []
        self.associated: list[Edge] = []
        self.max_speed = 50
        self.stops_at_station = None
        self.direction = ''.join(set(re.findall("[AB]", f"{str(f)[-2:]} {str(t)[-2:]}")))
        # if self.direction != "A" and self.direction != "B":
        #     raise ValueError("Direction must be either A or B")

    def set_depart_time(self, agent, time):
        self.depart_time[agent] = time

    def set_start_time(self, agent, time):
        self.start_time[agent] = time

class Graph:
    def __init__(self):
        self.edges: list[Edge] = []
        self.nodes: dict[str, Node] = {}
        self.global_end_time = -1

    def add_node(self, n):
        if isinstance(n, Node):
            self.nodes[n.name] = n
            return n

    def add_edge(self, e):
        if isinstance(e, Edge):
            self.edges.append(e)
            e.to_node.incoming.append(e)
            e.from_node.outgoing.append(e)
            return e

    def __repr__(self) -> str:
        return f"Graph with {len(self.edges)} edges and {len(self.nodes)} nodes:\n{self.nodes.values()}"

    def __eq__(self, other):
        if isinstance(other, Graph):
            return (self.edges == other.edges and
                    self.nodes == other.nodes and
                    self.global_end_time == other.global_end_time)
        return NotImplemented

class TrackGraph(Graph):
    def __init__(self, file_name):
        super().__init__()
        self.signals: list[Signal] = []
        self.distance_markers = {}
        self.file_name = file_name

    def add_signal(self, s):
        if isinstance(s, Signal):
            self.signals.append(s)


class BlockGraph(Graph):
    def __init__(self, g: TrackGraph):
        super().__init__()
        logger.info("Creating initial signals")
        track_to_signal = {signal.track: signal for signal in g.signals}
        for signal in g.signals:
            block = self.add_node(BlockNode(f"r-{signal.id}"))
            signal.track.blocks.append(block)
        for signal in tqdm.tqdm(g.signals, file=TqdmLogger(logger), mininterval=5, ascii=False):
            blocks = self.generate_signal_blocks(signal, g.signals)
            for idx, (block, length) in enumerate(blocks):

                # Create edges in g_block
                from_signal_node = self.nodes[f"r-{signal.id}"]

                # Only add edge if a signal is found at the end of the route
                to_signal = track_to_signal[block[-1]]
                to_signal_node = self.nodes[f"r-{to_signal.id}"]
                direction = "".join(set(signal.direction + to_signal.direction))
                self.add_edge(BlockEdge(from_signal_node, to_signal_node, length, block, direction))

    def __eq__(self, other):
        return super().__eq__(other)

    def add_edge(self, e):
        super().add_edge(e)

        for node in e.trackNodes:
            node.blocks.append(e)

    def generate_signal_blocks(self, from_signal: Signal, signals: list[Signal]):
        end_tracks = {s.track for s in signals}
        start_track = from_signal.track

        result = []

        queue = Queue()
        queue.put(([start_track], {start_track}, 0))

        while not queue.empty():
            route, visited, length = queue.get()

            if len(route[-1].outgoing) == 0:
                #No outgoing edges, what to do?
                # Should only happen when at the end of a track, and it's not allowed to turn around
                continue

            for e in route[-1].outgoing:
                next_track = e.to_node

                if next_track in end_tracks:
                    route = copy(route)
                    route.append(next_track)
                    result.append((route[1:], length + e.length))

                elif next_track not in visited:
                    route = copy(route)
                    visited = copy(visited)

                    visited.add(next_track)
                    route.append(next_track)
                    queue.put((route, visited, length + e.length))

        return result


def block_graph_constructor(g: TrackGraph):
    last_modified = os.path.getmtime(g.file_name)
    filename = f"{g.file_name}-{last_modified}-g_block.pkl"
    if os.path.exists(filename) and False:
        logger.info("Using existing track graph")
        return generation.GraphPickler.unpickleGraph(filename, g)
    g_block = BlockGraph(g)
    with open(f"{g.file_name}-{last_modified}-g_block.pkl", "wb") as f:
        pickler = generation.GraphPickler.GraphPickler(f, pickle.HIGHEST_PROTOCOL)
        pickler.dump(g_block)
    return g_block