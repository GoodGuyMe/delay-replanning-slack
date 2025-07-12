import pandas as pd
import json

from pathlib import Path

from setup import *

class TadExperiment:
    def __init__(self, l: Layout, s_file, save_dir):
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

    def calculate_tad(self, trainseries, direction, f, t, timeout=300):
        trainseries = str(int(trainseries) // 100) if int(trainseries) > 100 else str(trainseries)
        if direction == "o" or direction == 1:
            direction = 1
        else:
            direction = 0
        series = self.agent_df.loc[(self.agent_df['trainNumber'].str.startswith(trainseries, na=False)) & (self.agent_df['trainNumber'].astype(int) % 2 == direction)].sort_values("start_time")
        agent = series.loc[series['stops'].map(len).idxmax()]
        if len(agent) == 0:
            return []
        stops_df = pd.DataFrame(agent["stops"])
        self.r_start = stops_df.loc[stops_df["location"].str.contains(f, na=False)]
        self.r_stop = stops_df.loc[stops_df["location"].str.contains(t, na=False)]
        allowed_nodes = calculate_allowed_nodes(self.r_start, self.r_stop, agent, self.scenario.l)

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

        experiments = setup_experiment(self.scenario, experiment_settings, default_direction=1)
        run_experiments(experiments, timeout, filter_tracks=allowed_nodes)
        return experiments

    def plot_tad(self, experiments, save=None, x_offset=900, y_offset=900):
        if experiments:
            kwargs = {"min_x": self.r_start["time"].iloc[0], "max_x": self.r_start["time"].iloc[0] + x_offset,
                      "min_y": self.r_stop["expected_arrival"].iloc[0] - y_offset, "max_y": self.r_stop["expected_arrival"].iloc[0] + y_offset,
                      "expected_arrival_time": self.r_stop["expected_arrival"].iloc[0]}
            if save is not None:
                save_path = self.save_dir / save
                save_path.parent.mkdir(exist_ok=True, parents=True)
                plot_experiments(experiments, save_path=save_path, **kwargs)
            plot_experiments(experiments, **kwargs)