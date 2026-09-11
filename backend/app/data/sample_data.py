SAMPLE_REQUEST = {
    "your_roster": [
        {"player_id": "q1", "name": "Caleb Strong", "position": "QB", "recent_points": [18, 25, 22, 24], "season_average": 21.5, "matchup_multiplier": 1.04, "injury_risk": 0.01, "boom_rate": 0.40},
        {"player_id": "q2", "name": "Marcus Reed", "position": "QB", "recent_points": [14, 31, 12, 29], "season_average": 20.0, "matchup_multiplier": 1.08, "injury_risk": 0.02, "boom_rate": 0.65},
        {"player_id": "r1", "name": "Darius King", "position": "RB", "recent_points": [17, 18, 20, 19], "season_average": 17.8, "matchup_multiplier": 0.98, "injury_risk": 0.03, "boom_rate": 0.25},
        {"player_id": "r2", "name": "Jalen Brooks", "position": "RB", "recent_points": [8, 26, 10, 24], "season_average": 15.5, "matchup_multiplier": 1.05, "injury_risk": 0.05, "boom_rate": 0.70},
        {"player_id": "r3", "name": "Noah Grant", "position": "RB", "recent_points": [12, 14, 13, 15], "season_average": 13.3, "matchup_multiplier": 1.02, "injury_risk": 0.01, "boom_rate": 0.20},
        {"player_id": "w1", "name": "Tyler Banks", "position": "WR", "recent_points": [21, 17, 24, 22], "season_average": 19.8, "matchup_multiplier": 1.00, "injury_risk": 0.01, "boom_rate": 0.40},
        {"player_id": "w2", "name": "Chris Vega", "position": "WR", "recent_points": [6, 28, 9, 30], "season_average": 17.0, "matchup_multiplier": 1.10, "injury_risk": 0.02, "boom_rate": 0.75},
        {"player_id": "w3", "name": "Eli Foster", "position": "WR", "recent_points": [13, 14, 16, 15], "season_average": 14.5, "matchup_multiplier": 1.03, "injury_risk": 0.00, "boom_rate": 0.20},
        {"player_id": "t1", "name": "Owen Price", "position": "TE", "recent_points": [9, 12, 11, 13], "season_average": 10.8, "matchup_multiplier": 1.05, "injury_risk": 0.02, "boom_rate": 0.25},
        {"player_id": "t2", "name": "Mason Cole", "position": "TE", "recent_points": [4, 18, 7, 16], "season_average": 10.2, "matchup_multiplier": 1.08, "injury_risk": 0.03, "boom_rate": 0.65}
    ],
    "opponent_lineup": [
        {"player_id": "oq1", "name": "Opponent QB", "position": "QB", "recent_points": [23, 22, 25, 24], "season_average": 22.5},
        {"player_id": "or1", "name": "Opponent RB1", "position": "RB", "recent_points": [18, 19, 17, 20], "season_average": 18.0},
        {"player_id": "or2", "name": "Opponent RB2", "position": "RB", "recent_points": [14, 16, 15, 13], "season_average": 14.5},
        {"player_id": "ow1", "name": "Opponent WR1", "position": "WR", "recent_points": [18, 20, 21, 19], "season_average": 18.5},
        {"player_id": "ow2", "name": "Opponent WR2", "position": "WR", "recent_points": [12, 15, 14, 16], "season_average": 14.2},
        {"player_id": "ot1", "name": "Opponent TE", "position": "TE", "recent_points": [9, 10, 12, 11], "season_average": 10.0},
        {"player_id": "of1", "name": "Opponent FLEX", "position": "WR", "recent_points": [13, 14, 18, 17], "season_average": 15.0}
    ],
    "rules": {"qb": 1, "rb": 2, "wr": 2, "te": 1, "flex": 1},
    "simulations": 5000,
    "seed": 42
}
