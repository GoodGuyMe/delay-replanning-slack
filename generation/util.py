import json 
from pathlib import Path

from generation.graph import TrackGraph, Signal, TrackNode, TrackEdge
    
def read_graph(file) -> TrackGraph:
    try:
        base_path = Path(__file__).parent
        file_path = (base_path / file).resolve()
        data = json.load(open(file_path))
    except:
        data = json.load(open(file))
    g = TrackGraph(file)
    nodes_per_id_A = {}
    nodes_per_id_B = {}
    track_lengths = {}
    for track in data["trackParts"]:
        track_lengths[track["id"]] = track["length"]
        if track["type"] in {"RailRoad", "Bumper", "SideSwitch"}:
            a = g.add_node(TrackNode(track["name"] + "A", track["type"]))
            b = g.add_node(TrackNode(track["name"] + "B", track["type"]))
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
                a = g.add_node(TrackNode(track["name"] + "AR", track["type"]))
                b = g.add_node(TrackNode(track["name"] + "AL", track["type"]))
                c = g.add_node(TrackNode(track["name"] + "B", track["type"]))
                a.opposites.extend([c])
                b.opposites.extend([c])
                c.opposites.extend([a, b])
                nodes_per_id_A[track["id"]] = [track["name"] + "AR", track["name"] + "AL"]
                nodes_per_id_B[track["id"]] = [track["name"] + "B"]
            else:
                a = g.add_node(TrackNode(track["name"] + "A", track["type"]))
                b = g.add_node(TrackNode(track["name"] + "BR", track["type"]))
                c = g.add_node(TrackNode(track["name"] + "BL", track["type"]))
                a.opposites.extend([b, c])
                b.opposites.extend([a])
                c.opposites.extend([a])
                nodes_per_id_A[track["id"]] = [track["name"] + "A"]
                nodes_per_id_B[track["id"]] = [track["name"] + "BR", track["name"] + "BL"]
        elif track["type"] == "EnglishSwitch":
            a = g.add_node(TrackNode(track["name"] + "AR", track["type"]))
            b = g.add_node(TrackNode(track["name"] + "AL", track["type"]))
            c = g.add_node(TrackNode(track["name"] + "BR", track["type"]))
            d = g.add_node(TrackNode(track["name"] + "BL", track["type"]))
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
                        e = g.add_edge(TrackEdge(g.nodes[fromNode], g.nodes[aSideToTrack], length))
                        aEdges.append(e)
                # This side is a bumper, so the other side attaches to itself
                elif g.nodes[fromNode].type == "RailRoad" and track["sawMovementAl lowed"]:
                    toNode = nodes_per_id_B[track["id"]][i]
                    g.add_edge(TrackEdge(g.nodes[fromNode], g.nodes[toNode], 0))
            for i, bSideId in enumerate(track["bSide"]):
                fromNode = nodes_per_id_B[track["id"]][i]
                if bSideId in nodes_per_id_B:
                    bumperBside = False
                    # Connect the bSide node(s) to the respective neighbors
                    for bSideToTrack in nodes_per_id_B[bSideId]:
                        length = track_lengths[bSideId]
                        e = g.add_edge(TrackEdge(g.nodes[fromNode], g.nodes[bSideToTrack], length))
                        bEdges.append(e) 
                # This side is a bumper, so the other side attaches
                elif g.nodes[nodes_per_id_B[track["id"]][i]].type == "RailRoad" and track["sawMovementAllowed"]:
                    toNode = nodes_per_id_A[track["id"]][i]
                    g.add_edge(TrackEdge(g.nodes[fromNode], g.nodes[toNode], 0))


            if track["type"] == "SideSwitch":
                fromNode = None
                toNode = None
                if not track["aSide"]:
                    fromNode = g.nodes[track["name"] + "A"]
                    toNode = g.nodes[track["name"][0:-3] + track["name"][-2:-4:-1] + "-B"]
                if not track["bSide"]:
                    fromNode = g.nodes[track["name"] + "B"]
                    toNode = g.nodes[track["name"][0:-3] + track["name"][-2:-4:-1] + "-A"]

                if fromNode is None:
                    raise ValueError("A and B side populated somehow " + track)

                g.add_edge(TrackEdge(fromNode, toNode, 0))


            # If it is a double-ended (not dead-end) track where parking is allowed, then we can go from A->B and B->A
            if track["type"] == "RailRoad" and track["sawMovementAllowed"] and not bumperAside and not bumperBside:
                g.add_edge(TrackEdge(g.nodes[nodes_per_id_A[track["id"]][i]], g.nodes[nodes_per_id_B[track["id"]][i]], 0))
                g.add_edge(TrackEdge(g.nodes[nodes_per_id_B[track["id"]][i]], g.nodes[nodes_per_id_A[track["id"]][i]], 0))
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

    g.distance_markers = data["distanceMarkers"] if "distanceMarkers" in data and data["distanceMarkers"] else {"Start": 0}
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