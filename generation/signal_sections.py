from generation.graph import Edge


def convertMovesToBlock(moves_per_agent, g):
    block_routes = {}
    for agent in moves_per_agent:
        block_route = []
        for movements in moves_per_agent[agent]:
            blocks = None
            for move in movements:
                if move.from_node in [signal.track for signal in g.signals]:
                    if blocks:
                        assert len(blocks) == 1
                        block_route.append(list(blocks)[0])
                    blocks = set([block for block in move.to_node.blocks if isinstance(block, Edge)])
                blocks = blocks & set([block for block in move.to_node.blocks if isinstance(block, Edge) and block.direction == move.direction])
        block_routes[agent] = [block_route]
    return block_routes