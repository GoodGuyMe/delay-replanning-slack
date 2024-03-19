# Replanning in Advance for Instant Delay Recovery

This project has the following directories:
- `generation`: Python module to generate the @SIPP search graph
- `search` (atSIPP): C++ module to search for any-start-time plans in the @SIPP search graph
- `data`: two dutch shunting yard layouts: Enkhuizen and Heerlen. This also includes code to generate new scenarios and explanation of how the real-life scenario was created.
- `experiments`: code to run experiments for our paper

Dependencies (version tested):
- gcc (13.2.1)
- boost (1.83)
- zlib (1.3.1)

Compiling:
```bash
    cd search
    meson setup --buildtype release  build
    meson compile -C build
    meson setup --buildtype debug build_debug
    meson compile -C build_debug
```

To cite, please use:

    Issa Hanou, Devin W. Thomas, Wheeler Ruml, and Mathijs de Weerdt. Replanning in Advance for Instant Delay Recovery in Multi-Agent Applications: Rerouting Trains in a Railway Hub. (2024). In Proceedings: International Conference on Automated Planning and Scheduling.

