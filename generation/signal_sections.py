from generation.graph import Edge, TrackGraph, BlockEdge


def convertMovesToBlock(moves_per_agent, g: TrackGraph) -> dict[int, list[BlockEdge]]:
    block_routes = {}
    signal_tracks = {signal.track for signal in g.signals}
    for agent in moves_per_agent:
        block_route = []
        for movements in moves_per_agent[agent]:
            blocks = None
            for move in movements:
                if blocks is None:
                    blocks = {block for block in move.to_node.blocks if isinstance(block, Edge)}
                blocks = blocks & {block for block in move.to_node.blocks if isinstance(block, Edge) and move.direction in block.direction}
                if move.to_node in signal_tracks:
                    if len(blocks) != 1:
                        raise ValueError(f"Should really only be one, {blocks}")
                    block_route.append(list(blocks)[0])
                    blocks = None
        block_routes[agent] = [block_route]
    return block_routes