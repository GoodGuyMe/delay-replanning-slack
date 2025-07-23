import numpy as np
import pandas as pd
import json

from pathlib import Path

from setup import *

class Runner:
    def __init__(self, l: Layout, s_file, save_dir):
        print(s_file)
        self.r_stop = None
        self.r_start = None
        self.scenario = Scenario(l, s_file)
        self.save_dir = Path(save_dir) / Path(s_file).stem
        self.agent_df = self._calculate_agent_df(s_file)

    def _calculate_agent_df(self, s_file):
        try:
            base_path = Path(__file__).parent
            file_path = (base_path / s_file).resolve()
            data = json.load(open(file_path))
        except:
            data = json.load(open(s_file))
        types = {x["name"]: x for x in data["types"]}
        agents = []
        for trainNumber, entry in enumerate(data["trains"]):
            trainNumber += 1
            move = entry["movements"][0]
            velocity = types[entry["trainUnitTypes"][0]]["speed"] / 3.6

            agent = Agent(trainNumber, move["startLocation"], move["endLocation"], velocity, move["startTime"],
                          endTime=move["endTime"],
                          startTimeHuman=str(timedelta(seconds=move["startTime"])),
                          endTimeHuman=str(timedelta(seconds=move["endTime"])),
                          trainNumber=entry["trainNumber"],
                          trainUnitTypes=entry["trainUnitTypes"],
                          stops=move["stops"]
                          )
            agents.append(agent)

        agent_df = pd.DataFrame([agent.__dict__ for agent in agents])

        return agent_df

    def _get_replanning_agent(self, trainseries, direction):
        series = self._get_series(trainseries, direction)
        index = 0 if len(series) == 1 else 1
        agent = series.iloc[index]
        return agent

    def _get_series(self, trainseries, direction):
        trainseries = str(int(trainseries) // 100) if int(trainseries) > 100 else str(trainseries)
        if direction == "o" or direction == 1:
            direction = 1
        else:
            direction = 0
        series = self.agent_df.loc[(self.agent_df['trainNumber'].str.startswith(trainseries, na=False)) & (
                self.agent_df['trainNumber'].astype(int) % 2 == direction) & (
                                           self.agent_df['trainNumber'].astype(int) < (
                                               int(trainseries) + 1) * 100)].sort_values("endTime")
        if series.empty:
            raise ValueError("No agent found")
        return series

    def get_inclusive_stops(self, agent):
        all_stops = agent["stops"]
        all_stops.extend([{
            "expected_arrival": agent["start_time"],
            "time": agent["start_time"],
            "location": agent["origin"]
        }, {
            "expected_arrival": agent["endTime"],
            "time": agent["endTime"],
            "location": agent["destination"]
        }])
        return all_stops

    def allowed_nodes(self, f, t, agent):
        stops_df = pd.DataFrame(self.get_inclusive_stops(agent))
        self.r_start = stops_df.loc[stops_df["location"].str.contains(f, na=False)]
        self.r_stop = stops_df.loc[stops_df["location"].str.contains(t, na=False)]
        return calculate_allowed_nodes(self.r_start, self.r_stop, agent, self.scenario.l)


class TadRunner(Runner):
    def run(self, trainseries, direction, f, t, timeout=300, default_direction=1):
        agent = self._get_replanning_agent(trainseries, direction)
        allowed_nodes = self.allowed_nodes(f, t, agent)
        # Setup experiment
        experiment_settings = [
            {
                "start_time": self.r_start["time"].iloc[0],
                "origin": self.r_start["location"].iloc[0],
                "destination": self.r_stop["location"].iloc[0],
                "filter_agents": agent['id'],
                "metadata": {
                    "offset": 0,
                },
            },
            {
                "start_time": self.r_start["time"].iloc[0],
                "origin": self.r_start["location"].iloc[0],
                "destination": self.r_stop["location"].iloc[0],
                "max_buffer_time": 900,
                "filter_agents": agent['id'],
                "metadata": {
                    "color": "Green",
                    "label": "Buffer time",
                }
            }, {
                "start_time": self.r_start["time"].iloc[0],
                "origin": self.r_start["location"].iloc[0],
                "destination": self.r_stop["location"].iloc[0],
                "max_buffer_time": 900,
                "use_recovery_time": True,
                "filter_agents": agent['id'],
                "metadata": {
                    "color": "Blue",
                    "label": "Recovery time",
                }
            }
        ]

        experiments = setup_experiment(self.scenario, experiment_settings, default_direction=default_direction)
        run_experiments(experiments, timeout, filter_tracks=allowed_nodes)
        return experiments

    def plot(self, experiments, save=None, x_offset=900, y_offset=900):
        if experiments:
            kwargs = {"min_x": self.r_start["time"].iloc[0], "max_x": self.r_start["time"].iloc[0] + x_offset,
                      "min_y": self.r_stop["expected_arrival"].iloc[0] - y_offset, "max_y": self.r_stop["expected_arrival"].iloc[0] + y_offset,
                      "expected_arrival_time": self.r_stop["expected_arrival"].iloc[0]}
            if save is not None:
                save_path = self.save_dir / save
                save_path.parent.mkdir(exist_ok=True, parents=True)
                plot_experiments(experiments, save_path=save_path, **kwargs)
            plot_experiments(experiments, **kwargs)

class RTRunner(Runner):
    def run(self, trainseries, direction, f, t, timeout=300):
        agent = self._get_replanning_agent(trainseries, direction)
        if len(agent) == 0:
            return []
        allowed_nodes = self.allowed_nodes(f, t, agent)
        start_time = self.r_start["time"].iloc[0]
        origin = self.r_start["location"].iloc[0]
        experiment_settings = []

        stops = agent["stops"][self.r_start.index[0] + 1:self.r_stop.index[0] + 1]

        for stop in stops:
            experiment_settings.append({
                "start_time": start_time,
                "origin": origin,
                "destination": stop["location"],
                "max_buffer_time": 900,
                "use_recovery_time": True,
                "filter_agents": agent["id"],
                "metadata": {
                    "expected_arrival": stop["expected_arrival"],
                    "label": f'route to {stop["location"]}'
                }
            })


        if direction == "o" or direction == 1:
            direction = 1
        else:
            direction = 0
        experiments = setup_experiment(self.scenario, experiment_settings, default_direction=direction)
        run_experiments(experiments, timeout, filter_tracks=allowed_nodes)
        return experiments

    def get_path_df(self, experiments):
        def sum_cols(df1, cols, name):
            df2 = df1.drop(columns=cols)
            df2[name] = df1[cols].sum(axis=1)
            return df2

        time_df = pd.DataFrame([exp.get_running_time() for exp in experiments],
                               index=[exp.metadata['label'] for exp in experiments])

        setup_cols = ["track graph creation", "routing graph creation"]
        recompute_cols = ["unsafe interval generation", "safe interval generation", "bt and crt generation",
                          "converting routes to blocks"]
        search_cols = ["FlexSIPP search time"]

        time_df = sum_cols(time_df, setup_cols, "Setup Time")
        time_df = sum_cols(time_df, recompute_cols, "Recompute Time")
        time_df = sum_cols(time_df, search_cols, "Search Time")

        path_df = pd.DataFrame(
            {exp.metadata["label"]: np.mean([len(path.split(";")) for path in exp.results[2]]) for exp in experiments if
             exp.results}, index=["Average path length"]).transpose()
        return path_df.join(time_df["Search Time"])