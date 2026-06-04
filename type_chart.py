"""
Full Gen VI+ type effectiveness chart.
TYPE_CHART[attacking_type][defending_type] = multiplier
Only non-1x entries are stored; any missing pair defaults to 1.0.
"""

TYPE_CHART: dict[str, dict[str, float]] = {
    "normal":   {"rock": 0.5, "ghost": 0,   "steel": 0.5},
    "fire":     {"fire": 0.5, "water": 0.5, "grass": 2,   "ice": 2,   "bug": 2,
                 "rock": 0.5, "dragon": 0.5,"steel": 2},
    "water":    {"fire": 2,   "water": 0.5, "grass": 0.5, "ground": 2,"rock": 2,
                 "dragon": 0.5},
    "electric": {"water": 2,  "electric": 0.5,"grass": 0.5,"ground": 0,"flying": 2,
                 "dragon": 0.5},
    "grass":    {"fire": 0.5, "water": 2,   "grass": 0.5, "poison": 0.5,"ground": 2,
                 "flying": 0.5,"bug": 0.5,  "rock": 2,    "dragon": 0.5,"steel": 0.5},
    "ice":      {"fire": 0.5, "water": 0.5, "grass": 2,   "ice": 0.5, "ground": 2,
                 "flying": 2, "dragon": 2,  "steel": 0.5},
    "fighting": {"normal": 2, "ice": 2,     "poison": 0.5,"flying": 0.5,"psychic": 0.5,
                 "bug": 0.5,  "rock": 2,    "ghost": 0,   "dark": 2,  "steel": 2,
                 "fairy": 0.5},
    "poison":   {"grass": 2,  "poison": 0.5,"ground": 0.5,"rock": 0.5,"ghost": 0.5,
                 "steel": 0,  "fairy": 2},
    "ground":   {"fire": 2,   "electric": 2,"grass": 0.5, "poison": 2,"flying": 0,
                 "bug": 0.5,  "rock": 2,    "steel": 2},
    "flying":   {"electric": 0.5,"grass": 2,"fighting": 2,"bug": 2,   "rock": 0.5,
                 "steel": 0.5},
    "psychic":  {"fighting": 2,"poison": 2, "psychic": 0.5,"dark": 0, "steel": 0.5},
    "bug":      {"fire": 0.5, "grass": 2,   "fighting": 0.5,"poison": 0.5,"flying": 0.5,
                 "psychic": 2,"ghost": 0.5, "dark": 2,    "steel": 0.5,"fairy": 0.5},
    "rock":     {"fire": 2,   "ice": 2,     "fighting": 0.5,"ground": 0.5,"flying": 2,
                 "bug": 2,    "steel": 0.5},
    "ghost":    {"normal": 0, "psychic": 2, "ghost": 2,   "dark": 0.5},
    "dragon":   {"dragon": 2, "steel": 0.5, "fairy": 0},
    "dark":     {"fighting": 0.5,"psychic": 2,"ghost": 2,  "dark": 0.5,"fairy": 0.5},
    "steel":    {"fire": 0.5, "water": 0.5, "electric": 0.5,"ice": 2,  "rock": 2,
                 "steel": 0.5,"fairy": 2},
    "fairy":    {"fire": 0.5, "fighting": 2,"poison": 0.5, "dragon": 2,"dark": 2,
                 "steel": 0.5},
}

ALL_TYPES: list[str] = list(TYPE_CHART.keys())


def get_type_effectiveness(types: list[str]) -> dict[str, list[str]]:
    """
    Given a Pokemon's type(s), return its offensive and defensive matchups.

    Returns a dict with three keys:
      strong_against — types this Pokemon's moves hit for 2x+ (offensive)
      weak_to        — types that deal 2x+ damage to this Pokemon (defensive)
      immune_to      — types that deal 0 damage to this Pokemon (defensive)
    """
    # Offensive: union of each type's 2x targets
    strong_against: set[str] = set()
    for ptype in types:
        for defender, mult in TYPE_CHART.get(ptype, {}).items():
            if mult >= 2:
                strong_against.add(defender)

    # Defensive: multiply incoming multipliers across all of the Pokemon's types
    weak_to: list[str] = []
    immune_to: list[str] = []
    for attacker in ALL_TYPES:
        mult = 1.0
        for ptype in types:
            mult *= TYPE_CHART.get(attacker, {}).get(ptype, 1.0)
        if mult == 0:
            immune_to.append(attacker)
        elif mult >= 2:
            weak_to.append(attacker)

    return {
        "strong_against": sorted(strong_against),
        "weak_to": sorted(weak_to),
        "immune_to": sorted(immune_to),
    }
