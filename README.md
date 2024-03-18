# Any-Start-Time-Train-Routing

This project has the following directories:
- `generation`: Python module to generate the @SIPP search graph
- `search` (atSIPP): C++ module to search for any-start-time plans in the @SIPP search graph
- `data`: two dutch shunting yard layouts: Enkhuizen and Heerlen. This also includes code to generate new scenarios and explanation of how the real-life scenario was created.
- `experiments`: code to run experiments for our paper

Compiling:
- `meson setup --buildtype release  build`
- `meson setup --buildtype debug build_debug`
- `meson compile -C build`
- `meson compile -C build_debug`

To cite, please use:

    Issa Hanou, Devin W. Thomas, Wheeler Ruml, and Mathijs de Weerdt.Replanning in Advance for Instant Delay Recovery in Multi-Agent Applications: Rerouting Trains in a Railway Hub. (2024). In Proceedings: International Conference on Automated Planning and Scheduling.

