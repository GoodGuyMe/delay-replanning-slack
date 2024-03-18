# Scenario creation explanation
This file contains some information used to create the `example_enkhuizen_realdata.json` file, which was the base for creating the `scenario_reallife_enkhuizen`. The realdata file shows the actual arrival times, while the scenario has a time in seconds, where `t=0` is the start of the day at 04:30 AM.

The data is based on Tuesday October 31, 2023, where `departureScenario` is the time at Bovenkarspel Flora station. When a train was shunted, no arrival time at the station is known, so we keep 2 minutes for arriving trains. The parking tracks were assigned randomly. The A/B nodes are added manually to the start/end locations, in such a way that a reversal should never be the start of a move. The speeds, headways, and train types are based on the informaiton provided below. A train can consist of multiple train units, which must be the same type, so they all have the same speed. 


### Variables
- Train speeds:
    - VIRM 50 km/h = 13.9 m/s
    - ICM 40 km/h = 11.1 m/s
    - SNG 60 km/h = 16.7 m/s
    - SLT 55 km/h = 15.2 m/s
- Walking speed:
    - 5 km/h = 1.4 m/s


### Sources used:
- https://www.treinenweb.nl/materieel/ICM/intercitymaterieel-icm.html
- https://nl.wikipedia.org/wiki/Sprinter_Nieuwe_Generatie
- https://www.railwiki.nl/index.php/SNG

