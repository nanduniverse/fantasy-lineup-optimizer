# NFL statistics fixture

`nflverse_2025.csv` is a small subset of the real 2025 weekly player dataset retrieved on 2026-09-10:
https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2025.csv

It retains only the importer-required columns and selected QB/RB/WR/TE/K/DE rows for weeks 1, 2, 3, and 18. K and DE records test the offensive-position filter. Tests never download this data. The complete dataset is not bundled with the app.

The fixture also includes `attempts`, `carries`, and `targets` for workload normalization. Weekly provider parser tests use synthetic reports with fixed timestamps; they do not make network calls.
