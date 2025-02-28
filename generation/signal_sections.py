def expand_block(track, end_tracks):
    print(track.name)
    if track in end_tracks or len(track.outgoing) == 0:
        return [[track]]
    # TODO: make sure train is not turning around (or maybe it can?)
    routes = []
    expanded_blocks = [expand_block(e.to_node, end_tracks) for e in track.outgoing]
    for bl in expanded_blocks:
        routes.extend([[track] + block for block in bl])
    return routes

def flatten(xss):
    return [x for xs in xss for x in xs]

def generate_signal_blocks(from_signal, signals):
    end_tracks = [s.track for s in signals]
    routes = flatten([expand_block(e.to_node, end_tracks) for e in from_signal.track.outgoing])
    return routes