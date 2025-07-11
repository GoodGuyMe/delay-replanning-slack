import subprocess
import matplotlib.pyplot as plt
from datetime import timedelta
from logging import getLogger

logger = getLogger('pybook.' + __name__)

from generation import generate
from parseRePEAT import *

def plot_atf(segments, axs, eatfs, **kwargs):
    color = kwargs.get('color', None)
    label = kwargs.get('label', None)
    y_offset = kwargs.get('y_offset', 0)

    if 'expected_arrival_time' in kwargs:
        eat = kwargs['expected_arrival_time']
        axs[0].axhline(eat)

    line = None
    for (x0, x1, y0, y1) in segments:
        if x0 == "-inf" and x1 != "inf" and y1 != "inf":
            axs[0].hlines(float(y1) + y_offset, 0, float(x1), colors=color)
        line, = axs[0].plot([float(x0), float(x1)], [float(y0) + y_offset, float(y1) + y_offset], color=color)
    line.set_label(label) if line is not None else None

    plotted_intervals = []
    for path_eatf in eatfs.values():
        for (zeta, alpha, beta, delta, gammas) in path_eatf:
            min_gamma = 0
            max_gamma = 0
            for gamma_min, gamma_max, rt in gammas:
                # if gamma_max > gamma_min:
                #     raise ValueError(f"Max gamma > Min gamma, {gamma_max} > {gamma_min}")
                min_gamma += max(float(gamma_min) - float(rt), 0)
                max_gamma += max(float(gamma_max) - float(rt), 0)

            alpha = float(alpha)
            beta = float(beta)

            plotted_intervals.append((min(alpha, beta), beta, min_gamma, max_gamma))

            if alpha <= beta:
                # axs[1].plot([previous_beta, alpha], [min_gamma + y_offset, min_gamma + y_offset], color=color)
                axs[1].plot([alpha, beta], [min_gamma + y_offset, max_gamma + y_offset], color=color)
            # else:
            #     # axs[1].plot([previous_beta, beta - (gamma_diff)], [min_gamma + y_offset, min_gamma + y_offset], color=color)
            #     axs[1].plot([beta - (gamma_diff), beta], [min_gamma + y_offset, max_gamma + y_offset], color=color)
            # axs[1].plot([float(alpha), float(beta)], [min_gammas, max_gammas], color=color)
            previous_beta = beta

    previous_beta = 0
    plotted_intervals.sort(key=lambda x: x[0])

    for (alpha, beta, min_gamma, max_gamma) in plotted_intervals:
        axs[1].plot([previous_beta, alpha], [min_gamma + y_offset, min_gamma + y_offset], color=color)
        previous_beta = beta

            # logger.info(f"{alpha}, {beta}, {gammas}, {min_gammas} - {max_gammas}")

def setup_plt(**kwargs):
    widths = [10]
    heights = [4, 1]
    fig, axs = plt.subplots(ncols=1, nrows=2, gridspec_kw={"height_ratios": heights, "width_ratios": widths})
    axs = axs.transpose()
    fig.set_figheight(7)
    fig.set_figwidth(15)

    axs[0].set_xlabel("Departure time (hh:mm:ss)")
    axs[1].set_xlabel("Departure time (hh:mm:ss)")
    axs[0].set_ylabel("Arrival time (hh:mm:ss)")
    axs[1].set_ylabel("Total delay of agents (s)")
    axs[0].set_title("Arrival Time Function")
    axs[0].set_xlim(left=kwargs.get("min_x", None), right=kwargs.get("max_x", None))
    axs[1].set_xlim(left=kwargs.get("min_x", None), right=kwargs.get("max_x", None))
    axs[0].set_ylim(bottom=kwargs.get("min_y", None), top=kwargs.get("max_y", None))
    axs[0].grid()
    axs[1].grid()

    axs[0].set_xticklabels([str(timedelta(seconds=xtick)) for xtick in axs[0].get_xticks()])
    axs[0].set_yticklabels([str(timedelta(seconds=ytick)) for ytick in axs[0].get_yticks()])
    axs[1].set_xticklabels([str(timedelta(seconds=xtick)) for xtick in axs[1].get_xticks()])

    return fig, axs

def plot_experiments(exps, save_path=None, **kwargs):
    fig, axs = setup_plt(**kwargs)
    for e in exps:
        if e.results is None:
            logger.info(f"No results found, skipping {e}")
            continue
        logger.info(f"Plotting {e}")
        e.plot(axs, **kwargs)

    axs[0].legend()
    if save_path:
        fig.savefig(f"figures/{save_path}")
    plt.show()

class Agent:
    def __init__(self, id, origin, destination, velocity, start_time, **kwargs):
        self.id = id
        self.origin = origin
        self.destination = destination
        self.velocity = velocity
        self.start_time = start_time
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return str(self.__dict__)

class Layout:
    def __init__(self, layout):
        self.g, self.g_block, self.g_duration, self.g_block_duration = generate.time_graph_creation(layout)

    def station_to_block(self, station, direction=0):
        if station + "a" in self.g_block.stations:
            station = station + "a"
        if station in self.g_block.stations:
            if direction == "A":
                direction = 0
            if direction == "B":
                direction = 1
            return self.g_block.stations[station][direction]
        logger.error(f"Station {station} not found")
        return station

    def get_path_for_agent(self, move, current_train, velocity):
        from generation.interval_generation import construct_path
        from generation.signal_sections import convertMovesToBlock

        path = construct_path(self.g, move, current_agent=current_train, agent_velocity=velocity)
        moves_per_agent = {current_train: [path]}
        return convertMovesToBlock(moves_per_agent, self.g, current_train)[current_train][0]

class Scenario:
    def __init__(self, l: Layout, scen_file):
        self.l = l
        self.block_intervals, self.moves_per_agent, self.unsafe_computation_time, self.block_routes, self.t_moves_to_block = generate.time_scenario_creation(scen_file, self.l.g, self.l.g_block)

    def combine_intervals_per_train(self, filter_agents):
        # Combine intervals and merge overlapping intervals, taking into account the current agent
        return generate.combine_intervals_per_train(self.block_intervals, self.l.g_block, filter_agents)

    def get_flexibility(self, block_intervals, max_buffer_time, use_recovery_time):
        return generate.time_flexibility_creation(self.block_routes, block_intervals, max_buffer_time, use_recovery_time)

    def plot(self, agent_to_plot_route_of, block_intervals, buffer_times, recovery_times, plot_route_of_agent_to_plot_route_of=True):
        exclude_agent=-1
        if not plot_route_of_agent_to_plot_route_of:
            exclude_agent=agent_to_plot_route_of
        generate.plot_route(agent_to_plot_route_of, self.moves_per_agent, self.block_routes, block_intervals, self.l.g_block, buffer_times, recovery_times, exclude_agent=exclude_agent)

class Experiment:
    def __init__(self, s: Scenario, agent: Agent, filter_agents, max_buffer_time, use_recovery_time, metadata):
        self.s = s
        self.agent = agent
        self.metadata= metadata
        self.block_intervals = self.s.combine_intervals_per_train(filter_agents)

        self.buffer_times, self.recovery_times, self.time_flexibility_creation = s.get_flexibility(self.block_intervals, max_buffer_time, use_recovery_time)
        self.safe_block_intervals, self.safe_block_edges_intervals, self.atfs, self.indices_to_states, self.safe_computation_time = generate.time_interval_creation(self.block_intervals, self.s.l.g_block, self.buffer_times, self.recovery_times, self.agent.destination, agent.velocity)
        self.results = None

    def run_search(self, timeout, **kwargs):
        file = "output"
        generate.write_intervals_to_file(file, self.safe_block_intervals, self.atfs, self.indices_to_states, **kwargs)
        try:
            logger.debug(f'Running: {" ".join(["../search/buildDir/atsipp.exe", "--start", self.agent.origin, "--goal", self.agent.destination, "--edgegraph", file, "--search", "repeat", "--startTime", str(self.agent.start_time)])}')
            proc = subprocess.run(["../search/buildDir/atsipp.exe", "--start", self.agent.origin, "--goal", self.agent.destination, "--edgegraph", file, "--search", "repeat", "--startTime", str(self.agent.start_time)], timeout=timeout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        except subprocess.TimeoutExpired:
            logger.error(f'Timeout for repeat ({timeout}s) expired')
            return
        if int(proc.returncode) == 0:
            repeat_output = str(proc.stdout).split("'")[1].rsplit("\\r\\n")
            logger.debug(f"repeat output: {repeat_output}")
            metadata, catf, paths, eatfs = parse_list_of_outputs(repeat_output)
            logger.info(f"eats: {eatfs}")
            logger.info(f"cats: {catf}")
            self.results = (metadata, catf, paths, eatfs)
        else:
            logger.error(f'Search failed for repeat, ec: {proc.returncode}')


    def plot(self, axs, **kwargs):
        plot_atf(self.results[1], axs, self.results[3], label=self.metadata["label"], color=self.metadata["color"], y_offset=self.metadata["offset"], **kwargs)

    def get_running_time(self):
        return {
            "unsafe interval generation": self.s.unsafe_computation_time,
            "safe interval generation": self.safe_computation_time,
            "bt and crt generation": self.time_flexibility_creation,
            "converting routes to blocks": self.s.t_moves_to_block,
            "track graph creation": self.s.l.g_duration,
            "routing graph creation": self.s.l.g_block_duration,
            "FlexSIPP search time": float(self.results[0]["Search time"]) / 1000.0 if self.results is not None else -1,
        }

    def get_complexity(self):
        return {
            "nodes generated": int(self.results[0]["Nodes generated"]) if self.results is not None else -1,
            "nodes decreased": int(self.results[0]["Nodes decreased"]) if self.results is not None else -1,
            "nodes expanded": int(self.results[0]["Nodes expanded"]) if self.results is not None else -1,
        }

    def get_label(self):
        return {
            "label": self.metadata["label"],
        }

def run_experiments(exps: list[Experiment], timeout, **kwargs):
    for e in exps:
        e.run_search(timeout, **kwargs)
        logger.debug(f"results of {e}: {e.results}")

def setup_experiment(scenario: Scenario, overwrite_settings, default_direction=0):
    experiments = []
    for exp in overwrite_settings:
        set_default(exp)
        logger.info(f"Setting up experiment {exp}")

        origin = exp["origin"]
        destination = exp["destination"]
        velocity = exp["velocity"]
        start_time = exp["start_time"]
        max_buffer_time = exp["max_buffer_time"]
        use_recovery_time = exp["use_recovery_time"]
        metadata = exp["metadata"]
        filter_agents = exp["filter_agents"]


        origin_signal = scenario.l.station_to_block(origin, direction=default_direction)
        destination_signal = scenario.l.station_to_block(destination, direction=default_direction)
        agent = Agent(filter_agents, origin_signal, destination_signal, velocity, start_time)


        experiments.append(Experiment(scenario, agent, filter_agents, max_buffer_time, use_recovery_time, metadata))
    return experiments

default_settings = {
    "origin": "ASD|13a",
    "destination": "RTD|2",
    "velocity": 140/3.6,
    "max_buffer_time": 0,
    "start_time": 0,
    "use_recovery_time": False,
    "filter_agents": -1,
    "metadata": {
        "color": "Red",
        "label": "No flexibility",
        "offset": 0,
    }
}

def _set_default(setting: dict, default: dict):
    for key, value in default.items():
        if key not in setting:
            setting[key] = value
        elif isinstance(value, dict):
            _set_default(setting[key], value)

def set_default(setting):
    _set_default(setting, default_settings)