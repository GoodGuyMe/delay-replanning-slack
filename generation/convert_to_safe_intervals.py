def create_safe_intervals(intervals, g, buffer_times, agent_speed=15, print_intervals=False):
    errors = []
    safe_node_intervals = {n: [] for n in g.nodes}
    safe_edge_intervals = {e.get_identifier(): [] for e in g.edges}
    arrival_time_functions = []
    safe_edge_node_references = {e.get_identifier(): [] for e in g.edges}
    state_indices = {n: {} for n in g.nodes} | {e.get_identifier(): {} for e in g.edges}# save the index per node and also the start of each interval
    edge_durations = {n: {} for n in g.nodes}
    indices_to_states = {}
    index = 0
    # Create safe intervals from the unsafe node intervals
    # Also store the state indices
    for node in g.nodes:
        current = 0
        train_before = 0
        duration = 0
        # Make sure they are ordered in chronological order
        intervals[node].sort()
        # Each tuple is (start, end, duration, train)
        for start, end, dur, train, _ in intervals[node]:
            if current > start:
                interval = (current, start, train_before, train, 0, 0)
                train_before = train
                print(f"INTERVAL ERROR safe node interval {interval} on node {node} has later end than start.")
            elif current == start:
                # Don't add safe intervals like (0,0), but do update for the next interval
                print(f"INTERVAL ERROR current == end.")
                train_before = train
                current = end
            else:
                interval = (current, start, train_before, train, 0, 0)
                safe_node_intervals[node].append(interval)
                train_before = train
                # Dictionary with node keys, each entry has a dictionary with interval keys and then the index value
                state_indices[node][str(interval)] = index
                indices_to_states[index] = node
                duration = dur
                edge_durations[node][str(interval)] = duration
                index += 1
                current = end
        if current < g.global_end_time:
            last_interval = (current, g.global_end_time, train_before, 0, 0, 0)
            safe_node_intervals[node].append(last_interval)
            state_indices[node][str(last_interval)] = index
            indices_to_states[index] = node
            edge_durations[node][str(last_interval)] = duration
            index += 1

    for edge in g.edges:
        node = edge.get_identifier()
        current = 0
        train_before = 0
        dur_before = 0
        # Make sure they are ordered in chronological order
        intervals[node].sort()
        # Each tuple is (start, end, duration)
        for start, end, dur, train, _ in intervals[node]:
            if current > start:
                interval = (current, start, train_before, train, dur_before, end - start)
                train_before = train
                dur_before = end - start
                print(f"INTERVAL ERROR safe node interval {interval} on node {node} has later end than start.")
            elif current == start:
                # Don't add safe intervals like (0,0), but do update for the next interval
                print(f"INTERVAL ERROR current == end.")
                train_before = train
                dur_before = end - start
                current = end
            else:
                interval = (current, start, train_before, train, dur_before, end - start)
                safe_edge_intervals[node].append(interval)
                train_before = train
                dur_before = end - start
                # Dictionary with node keys, each entry has a dictionary with interval keys and then the index value
                state_indices[node][str(interval)] = index
                index += 1
                current = end
        if current < g.global_end_time:
            last_interval = (current, g.global_end_time, train_before, 0, dur_before, 0)
            safe_edge_intervals[node].append(last_interval)
            state_indices[node][str(last_interval)] = index
            index += 1

    ## Print safe node intervals
    if print_intervals:
        for node in safe_node_intervals:
            print(f"Safe intervals on node {node}")
            for interval in safe_node_intervals[node]:
                print(f"    Interval {interval} with index {state_indices[node][str(interval)]}")
    # Assign the safe edge intervals


    for node in safe_node_intervals:
        # Interval is the safe interval on the from node: (start-time, end-time)
        for from_interval in safe_node_intervals[node]:
            for o in g.nodes[node].outgoing:
                from_index = state_indices[node][str(from_interval)]
                to_index = -1
                for edge_interval in safe_edge_intervals[o.get_identifier()]:
                    # The safe interval on the to node (start-time, end-time)
                    for to_interval in safe_node_intervals[o.to_node.name]:
                        # If there is some overlap between the intervals, then map them together
                        if to_interval[0] <= from_interval[1] and to_interval[1] >= from_interval[0]:
                            to_index = state_indices[o.to_node.name][str(to_interval)]
                            # zeta: start of u interval, so the interval is same as from node
                            zeta = from_interval[0]
                            # alpha: start of safe interval, without wait time, it will be the same as zeta
                            alpha = max(edge_interval[0], from_interval[0], to_interval[0] - o.length / agent_speed)
                            # beta: end of safe interval on u
                            beta = min(edge_interval[1], from_interval[1], to_interval[1] - o.length / agent_speed)

                            # TODO: check why the alpha is what it is, from that interval we select the train_before/after.
                            #  It's most likely the edge (maybe always?)
                            train_before = edge_interval[2]
                            train_after = edge_interval[3]

                            buffer_after = 0
                            if train_after != 0 and o.get_identifier() in buffer_times[train_after]:
                                buffer_after = buffer_times[train_after][o.get_identifier()]
                            elif train_after != 0 and print_intervals:
                                print(f"ERROR - Buffer time not found while it should have one for train {train_after} "
                                      f"at {o.get_identifier()}")

                            # If the interval is too short to make the move, don't include it.
                            if beta > alpha:
                                arrival_time_functions.append((
                                    from_index,
                                    to_index,
                                    zeta,
                                    alpha,
                                    beta,
                                    o.length / agent_speed, # delta: length of the edge or in case of A-B edge the time to walk to the other side
                                    train_before,
                                    train_after,
                                    buffer_after
                                ))
                                safe_edge_node_references[o.get_identifier()].append(((node, o.to_node.name), from_interval, to_interval, arrival_time_functions[-1]))
                            else:
                                if print_intervals:
                                    print(f"--------------------\nFound interval too short\nFrom: {node} to {o.to_node.name}\nf:{from_interval}, t:{to_interval}, e:{edge_interval}\nAlpha: {alpha}, Beta: {beta}")
                    if to_index < 0:
                        # If this is an opposite edge which cannot be connected due to node occupied it is okay that is not found
                        # This is true if this edge interval does not happen on the path of any agent
                        # print(f"INFO - NOT FOUND an interval for edge <{o.from_node.name},{o.to_node.name}> interval on from node {from_interval} (state {from_index}) and intervals on to node are {safe_node_intervals[o.to_node.name]}")
                        pass
    ### To print edge intervals
    if print_intervals:
        for e in safe_edge_node_references:
            for data in safe_edge_node_references[e]:
                atf = data[3]
                print(f"Edge has interval from {data[0][0]} state {atf[0]} {data[1]} to {data[0][1]} state {atf[1]} {data[2]} with zeta {atf[2]}, alpha {atf[3]}, beta {atf[4]}, delta {atf[5]}, train_before {atf[6]} and train_after {atf[7]}.")
        for node in safe_node_intervals:
            print(f"{node} safe intervals: {[str(x) for x in safe_node_intervals[node]]}")                
    return safe_node_intervals, safe_edge_intervals, arrival_time_functions, errors, indices_to_states
