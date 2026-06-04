"""
PokeDueler CLI — interactive Pokémon lookup and comparison tool.
Data sourced from the public PokéAPI (https://pokeapi.co).
"""

import logging

import requests

logger = logging.getLogger(__name__)

POKEAPI_BASE    = "https://pokeapi.co/api/v2"
REQUEST_TIMEOUT = 10


def get_pokemon_data(pokemon_name: str) -> dict | None:
    """Fetch Pokémon data by name from PokéAPI.

    Returns the raw API response dict, or None if the Pokémon is not found
    or a network error occurs.
    """
    url = f"{POKEAPI_BASE}/pokemon/{pokemon_name.strip().lower()}"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        if status == 404:
            print(f"Pokémon '{pokemon_name}' not found. Check the spelling and try again.")
        else:
            logger.error("PokéAPI HTTP %s for '%s': %s", status, pokemon_name, exc)
        return None
    except requests.Timeout:
        logger.warning("Request timed out for '%s' after %ds", pokemon_name, REQUEST_TIMEOUT)
        return None
    except requests.RequestException as exc:
        logger.error("Network error fetching '%s': %s", pokemon_name, exc)
        return None


def get_total_stats(data: dict) -> int:
    """Return the sum of all base stats from a PokéAPI Pokémon response."""
    return sum(s["base_stat"] for s in data.get("stats", []))


def display_pokemon_info(data: dict) -> None:
    """Print a formatted summary of a Pokémon's data to stdout."""
    print(f"\nName: {data['name'].capitalize()}")

    sprite = data.get("sprites", {}).get("front_default")
    if sprite:
        print(f"Sprite: {sprite}")

    official = (
        data.get("sprites", {})
        .get("other", {})
        .get("official-artwork", {})
        .get("front_default")
    )
    if official:
        print(f"Official Artwork: {official}")

    print("Types:", ", ".join(t["type"]["name"] for t in data.get("types", [])))
    print("Abilities:", ", ".join(a["ability"]["name"] for a in data.get("abilities", [])))

    print("\nStats:")
    for stat in data.get("stats", []):
        print(f"  {stat['stat']['name']}: {stat['base_stat']}")
    print(f"Total Stats: {get_total_stats(data)}")


def compare_pokemon(pokemon1: str, pokemon2: str) -> None:
    """Fetch and print a side-by-side stat comparison of two Pokémon."""
    data1 = get_pokemon_data(pokemon1)
    data2 = get_pokemon_data(pokemon2)
    if not data1 or not data2:
        return

    print(f"\n{'=' * 31}")
    print(f"⚔  {pokemon1.capitalize()} vs {pokemon2.capitalize()}")
    print(f"{'=' * 31}")

    display_pokemon_info(data1)
    print()
    display_pokemon_info(data2)

    total1 = get_total_stats(data1)
    total2 = get_total_stats(data2)
    print("\nResult:")
    if total1 > total2:
        print(f"{pokemon1.capitalize()} wins! ({total1} vs {total2})")
    elif total2 > total1:
        print(f"{pokemon2.capitalize()} wins! ({total2} vs {total1})")
    else:
        print(f"It's a tie! Both: {total1}")


def run_menu() -> None:
    """Run the interactive CLI menu loop."""
    while True:
        print("\nOptions:")
        print("  1. View Pokémon info")
        print("  2. Compare two Pokémon")
        print("  q. Quit")
        choice = input("Choose: ").strip().lower()

        if choice == "1":
            name = input("Pokémon name: ").strip()
            data = get_pokemon_data(name)
            if data:
                display_pokemon_info(data)
        elif choice == "2":
            p1 = input("First Pokémon: ").strip()
            p2 = input("Second Pokémon: ").strip()
            compare_pokemon(p1, p2)
        elif choice == "q":
            print("Bye, Trainer!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    run_menu()
