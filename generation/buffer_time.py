from generation.util import get_all_affected_blocks


# TODO maybe should use smarter form off search, as list is most likely sorted on agent id right? or maybe it does not have to...
def get_single_buffer_time(intervals, agent):

    buffer_time = float("inf")
    for interval_agent, next_interval in zip(intervals, intervals[1:]):
        if interval_agent[3] == agent:
            return next_interval[0] - interval_agent[1]

    return buffer_time

def buffer_time(block_intervals, block_routes, g):

    buffer_times = {}
    for agent in block_routes:
        buffer_times[agent] = {}
        last_time = float("inf")
        # TODO: Need to do this for all blocks the train made unsafe, not only the blocks on the exact route
        for movement in block_routes[agent]:
            for edge in movement[::-1]:
                block = edge.get_identifier()
                blocks = block_intervals[block]
                time = get_single_buffer_time(blocks, agent)
                last_time = min(last_time, time)
                for affected_block in get_all_affected_blocks(block_intervals, block, g):
                    buffer_times[agent][affected_block] = last_time

    return buffer_times
