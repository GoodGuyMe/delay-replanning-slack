import pickle

import generation

class GraphPickler(pickle.Pickler):
    def persistent_id(self, obj):
        if type(obj) is generation.graph.BlockEdge:
            return ("BlockEdge", {
                "id": obj.id,
                "length": obj.length,
                "direction": obj.direction,
                "from_node": obj.from_node.name,
                "to_node": obj.to_node.name,
                "trackNodes": [tn.name for tn in obj.trackNodes],
            })
        if type(obj) is generation.graph.BlockNode:
            return ("BlockNode", {
                "name": obj.name,
                "incoming": [inc.id for inc in obj.incoming],
                "outgoing": [out.id for out in obj.outgoing]
            })
        return None

class GraphUnpickler(pickle.Unpickler):
    def __init__(self, file, g):
        super().__init__(file)
        self.g = g


    def persistent_load(self, pid):
        type_tag, obj = pid
        if type_tag == "BlockEdge":
            f = obj["from_node"]
            t = obj["to_node"]
            length = obj["length"]
            track_nodes = [self.g.nodes[tn] for tn in obj["trackNodes"]]
            direction = obj["direction"]
            edge = generation.graph.BlockEdge(f, t, length, [], direction)
            edge.id = obj["id"]
            edge.trackNodes = track_nodes

            for node in track_nodes:
                if edge.id not in [e.id for e in node.blocks]:
                    node.blocks.append(edge)

            return edge
        if type_tag == "BlockNode":
            name = obj["name"]
            node = generation.graph.BlockNode(name)
            return node
        raise pickle.UnpicklingError("Can't unpickle this shit")

def fix_edge(g_block, edge):
    edge.from_node = g_block.nodes[edge.from_node]
    edge.from_node.outgoing.append(edge)
    edge.to_node = g_block.nodes[edge.to_node]
    edge.to_node.incoming.append(edge)


def unpickleGraph(filename, g):
    with open(filename, "rb") as f:
        unpickler = GraphUnpickler(f, g)
        g_block = unpickler.load()
    for edge in g_block.edges:
        fix_edge(g_block, edge)

    for node_name, node in g_block.nodes.items():
        signal_name = node_name[2:]
        signal = [signal for signal in g.signals if signal.id == signal_name][0]
        signal.track.blocks.append(node)

    return g_block