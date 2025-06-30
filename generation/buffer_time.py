from logging import getLogger

logger = getLogger('__main__.' + __name__)

# TODO maybe should use smarter form off search, as list is most likely sorted on agent id right? or maybe it does not have to...
def get_single_buffer_time(intervals, agent):

    for interval_agent, next_interval in zip(intervals, intervals[1:]):
        if interval_agent[3] == agent:
            return next_interval[0] - interval_agent[1], interval_agent[4]

    recovery_time = 0.0
    for interval in intervals:
        if interval[3] == agent:
            recovery_time = interval[4]
            break
    return float("inf"), recovery_time

def flexibility(block_intervals, block_routes, max_buffer=float("inf"), use_recovery_time=True):

    buffer_times = {}
    recovery_times = {}
    for agent in block_routes:
        buffer_times[agent] = {}
        recovery_times[agent] = {}
        compound_recovery_time = 0.0
        last_buffer_time = max_buffer
        # TODO: Need to do this for all blocks the train made unsafe, not only the blocks on the exact route
        for movement in block_routes[agent][::-1]:
            for edge in movement[::-1]:
                # Calculate buffer time
                block = edge.get_identifier()
                blocks = block_intervals[block]
                current_buff_time, recovery = get_single_buffer_time(blocks, agent)

                # Recovery time cannot be larger than buffer time
                # compound_recovery_time = min(compound_recovery_time, last_buffer_time)

                # Buffer time can increase by recovery time if it would fit
                last_buffer_time = min(last_buffer_time, current_buff_time)

                if use_recovery_time:
                    # Calculate recovery time
                    compound_recovery_time += recovery

                if use_recovery_time:
                    last_buffer_time = min(last_buffer_time + recovery, max_buffer)

                # Store flexibility
                for affected_block in edge.get_affected_blocks():
                    buffer_times[agent][affected_block.get_identifier()] = last_buffer_time
                    recovery_times[agent][affected_block.get_identifier()] = compound_recovery_time



    return buffer_times, recovery_times
