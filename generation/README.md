# Generation

This module contains the code to generate the @SIPP graphs. The `generate.py` contains the general workflow to be run as well as the code for reading scenario files and writing the safe intervals to a gzip file. The `util.py` contains the graph structure classes for the railway network graph as well as the read method for railway graph files. The main work is done in `interval_generation.py` to create unsafe intervals given the trains in the scenario. `convert_to_safe_intervals.py` creates the SIPP graph which can be written to a file. 

