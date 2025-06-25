from __future__ import annotations

import contextlib
import re
import os
import pickle
import logging
import sys
import time
from enum import Enum

import tqdm
from typing import Iterator

import generation.GraphPickler

from queue import Queue
from copy import copy
from logging import getLogger

a_to_s = {
    "4.5": 40,
    "7": 40,
    "8": 40,
    "9": 40,
    "10": 40,
    "12": 60,
    "15": 80,
    "18": 80,
    "18.5": 80,
    "20": 125,
    "29": 140,
    "34.7": 140,
    "39.1": 160
}
def angle_to_speed(angle):
    if angle is None:
        return 200 / 3.6
    return a_to_s[angle] / 3.6

logger = getLogger('__main__.' + __name__)

class Direction(Enum):
    SAME = 1
    OPPOSE = 2
    BOTH = 3

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
        self.blk:list[BlockEdge] = []
        self.blocksOpp:list[BlockEdge] = []
        self.canReverse = False
        self.stationPlatform = False
        self.type = type
        self.direction = ''.join(set(re.findall("[AB]", f"{name[-2:]}")))
        if self.direction != "A" and self.direction != "B":
            raise ValueError("Direction must be either A or B")

    def blocks(self, dir: Direction = Direction.SAME):
        if dir == Direction.SAME:
            return self.blk
        if dir == Direction.OPPOSE:
            return self.blocksOpp
        return self.blk + self.blocksOpp

class Signal:
    def __init__(self, id, track: TrackNode):
        self.id = id
        self.track = track
        self.direction = track.direction

    def __repr__(self) -> str:
        return f"Signal {self.id} on track {self.track}"


class Edge:
    __last_id = 1
    def __init__(self, f:Node, t:Node, l, mv):
        self.id = Edge.__last_id
        Edge.__last_id += 1
        self.from_node = f
        self.to_node = t
        self.length = l
        self.max_speed = mv

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
    def __init__(self, f, t, l, tracknodes_on_route:list[TrackNode], direction, mv):
        super().__init__(f, t, l, mv)
        self.tn:list[TrackNode] = list(tracknodes_on_route)
        self.tnAssociated:list[TrackNode] = list()
        self.tnOpposites:list[TrackNode] = list()
        for n in tracknodes_on_route:
            self.tnAssociated.extend(n.associated)
            self.tnOpposites.extend(n.opposites)
        self.direction = direction
        if self.direction == "BA":
            self.direction = "AB"

    def tracknodes(self, direction:Direction) -> list[TrackNode]:
        if direction == Direction.BOTH:
            return self.tn + self.tnAssociated + self.tnOpposites
        if direction == Direction.SAME:
            return self.tn + self.tnAssociated
        return self.tnOpposites


    def get_affected_blocks(self) -> list:
        affected_blocks = set()
        for node in self.tracknodes("AB"):
            affected_blocks = affected_blocks.union(set(node.blocks(Direction.BOTH)))
        return list(affected_blocks)


class TrackEdge(Edge):
    def __init__(self, f, t, l, switch_angle=None):
        super().__init__(f, t, l, angle_to_speed(switch_angle))
        self.plotting_info = {}
        self.opposites:  list[Edge] = []
        self.associated: list[Edge] = []
        self.stops_at_station = {}
        self.direction = ''.join(set(re.findall("[AB]", f"{str(f)[-2:]} {str(t)[-2:]}")))
        # if self.direction != "A" and self.direction != "B":
        #     raise ValueError("Direction must be either A or B")


    def set_plotting_info(self, agent, cur_time, end_time, block_edge):
        self.plotting_info[agent] = {
            "start_time": cur_time,
            "end_time": end_time,
            "block": block_edge,
        }


class Graph:
    def __init__(self):
        self.edges: list[Edge] = []
        self.nodes: dict[str, Node] = {}
        self.global_end_time = -1
        self.stations: dict[str, (str, str)] = {}

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

    def get_station(self, station):
        if station in self.stations:
            return self.stations[station]
        if f"{station}a" in self.stations:
            return self.stations[f"{station}a"]
        if f"{station}b" in self.stations:
            return self.stations[f"{station}b"]
        if station[0:-1] in self.stations:
            return self.stations[station[0:-1]]

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
            signal.track.blk.append(block)
        for signal in tqdm.tqdm(g.signals, file=TqdmLogger(logger), mininterval=1, ascii=False):
            blocks = self.generate_signal_blocks(signal, g.signals)
            for idx, (block, length, max_velocity) in enumerate(blocks):

                # Create edges in g_block
                from_signal_node = self.nodes[f"r-{signal.id}"]

                # Only add edge if a signal is found at the end of the route
                to_signal = track_to_signal[block[-1]]
                to_signal_node = self.nodes[f"r-{to_signal.id}"]
                direction = "".join(set(signal.direction + to_signal.direction))
                e = self.add_edge(BlockEdge(from_signal_node, to_signal_node, length, block, direction, max_velocity))
                logger.debug(f"Found block {e} with length {length} and max velocity {max_velocity}")
        for station, track_nodes in g.stations.items():
            node_a, node_b = track_nodes

            station_track_a = g.nodes[node_a]
            station_block_a = {edge.to_node.name for edge in station_track_a.blocks(Direction.SAME) if
                               isinstance(edge, BlockEdge) and station_track_a.direction in edge.direction}
            if len(station_block_a) == 0:
                logger.error(f"Found no blocks corresponding to track {station_track_a}")
                continue

            station_track_b = g.nodes[node_b]
            station_block_b = {edge.to_node.name for edge in station_track_b.blocks(Direction.SAME) if
                               isinstance(edge, BlockEdge) and station_track_b.direction in edge.direction}
            if len(station_block_b) == 0:
                logger.error(f"Found no blocks corresponding to track {station_block_b}")
                continue

            self.stations[station] = (station_block_a.pop(), station_block_b.pop())

    def __eq__(self, other):
        return super().__eq__(other)

    def add_edge(self, e):
        super().add_edge(e)

        for node in e.tracknodes(Direction.SAME):
            node.blk.append(e)
        for node in e.tracknodes(Direction.OPPOSE):
            node.blocksOpp.append(e)

        return e

    def generate_signal_blocks(self, from_signal: Signal, signals: list[Signal]):
        end_tracks = {s.track for s in signals}
        start_track = from_signal.track

        result = []

        queue = Queue()
        queue.put(([start_track], {start_track}, 0, sys.maxsize))

        while not queue.empty():
            route, visited, length, max_velocity = queue.get()

            if len(route[-1].outgoing) == 0:
                #No outgoing edges, what to do?
                # Should only happen when at the end of a track, and it's not allowed to turn around
                logger.debug(f"No outgoing edges at {route[-1]}")
                continue

            for e in route[-1].outgoing:
                next_track = e.to_node

                if next_track in end_tracks:
                    route = copy(route)
                    route.append(next_track)
                    result.append((route[1:], length + e.length, min(max_velocity, e.max_speed)))

                elif next_track not in visited:
                    route = copy(route)
                    visited = copy(visited)

                    visited.add(next_track)
                    route.append(next_track)
                    queue.put((route, visited, length + e.length, min(max_velocity, e.max_speed)))

        return result


def block_graph_constructor(g: TrackGraph, use_pickle=False):
    if not use_pickle:
        return BlockGraph(g)

    last_modified = os.path.getmtime(g.file_name)
    filename = f"{g.file_name}-{last_modified}-g_block.pkl"
    if os.path.exists(filename):
        logger.info("Using existing track graph")
        start = time.time()
        g_block = generation.GraphPickler.unpickleGraph(filename, g)
        duration = time.time() - start
        logger.info(f"Unpickling graph took {duration} seconds")
        return g_block
    g_block = BlockGraph(g)
    with open(f"{g.file_name}-{last_modified}-g_block.pkl", "wb") as f:
        pickler = generation.GraphPickler.GraphPickler(f, pickle.HIGHEST_PROTOCOL)
        pickler.dump(g_block)
    return g_block