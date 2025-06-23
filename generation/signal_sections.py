from logging import getLogger

from generation.graph import Edge, TrackGraph, BlockEdge, Direction

logger = getLogger('__main__.' + __name__)

def convertMovesToBlock(moves_per_agent, g: TrackGraph, agent=None) -> dict[int, list[BlockEdge]]:
    block_routes = {}
    signal_tracks = {signal.track for signal in g.signals}
    if agent is not None:
        moves_per_agent = {agent: moves_per_agent[agent]}
    for agent in moves_per_agent:
        logger.debug(f"Converting moves to block for {agent}.")
        block_route = []
        for movements in moves_per_agent[agent]:
            blocks = None
            for move in movements:
                if blocks is None:
                    blocks = {block for block in move.to_node.blocks(Direction.SAME) if isinstance(block, Edge)}
                blocks = blocks & {block for block in move.to_node.blocks(Direction.SAME) if isinstance(block, Edge)}
                logger.debug(f"Move: {move}, blocks possible {blocks}")
                if move.to_node in signal_tracks:
                    if len(blocks) == 0:
                        raise ValueError(f"No valid block found for last move {move}")
                    if len(blocks) > 1:
                        logger.critical(f"Should really only be one, {blocks}")
                    block_route.append(list(blocks)[0])
                    blocks = None
                elif len(blocks) == 0:
                    raise ValueError(f"Should really only be one, {blocks}")
        block_routes[agent] = [block_route]
    return block_routes