"""
PokeDueler — Head-to-Head. Stat for Stat.

Base application: PokeDueler branding, Midnight Crimson theme,
stat comparison cards, VS banner, and winner declaration.
"""

import base64
from pathlib import Path

import requests
import streamlit as st

# ── Constants ─────────────────────────────────────────────────────────────────

POKEAPI_BASE = "https://pokeapi.co/api/v2"
MAX_STAT = 255

TYPE_COLORS: dict[str, str] = {
    "normal": "#A8A878",   "fire": "#F08030",    "water": "#6890F0",
    "electric": "#F8D030", "grass": "#78C850",   "ice": "#98D8D8",
    "fighting": "#C03028", "poison": "#A040A0",  "ground": "#E0C068",
    "flying": "#A890F0",   "psychic": "#F85888", "bug": "#A8B820",
    "rock": "#B8A038",     "ghost": "#705898",   "dragon": "#7038F8",
    "dark": "#705848",     "steel": "#B8B8D0",   "fairy": "#EE99AC",
}

STAT_KEYS = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]
STAT_LABELS = ["HP", "ATK", "DEF", "SP.ATK", "SP.DEF", "SPD"]

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="PokeDueler",
    page_icon="⚔️",
    layout="wide",
)

# ── Theme CSS ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.stApp { background-color: #0E0E0E; }
body, p, span, div, li { color: #F1FAEE; }
h1, h2, h3, h4 { color: #F1FAEE !important; }
label, .stMarkdown { color: #A8DADC !important; }

.stButton > button {
    background-color: #E63946 !important;
    color: #F1FAEE !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
    letter-spacing: 1px;
}
.stButton > button:hover {
    background-color: #c1121f !important;
    box-shadow: 0 4px 18px rgba(230,57,70,0.45);
}

.stTextInput input {
    background-color: #1A1A1A !important;
    border: 1px solid #E63946 !important;
    color: #F1FAEE !important;
}

hr { border-color: rgba(230,57,70,0.25) !important; }
</style>
""", unsafe_allow_html=True)


# ── Data layer ────────────────────────────────────────────────────────────────

def get_pokemon_data(name: str) -> dict | None:
    """Fetch a single Pokémon's data from PokéAPI by name."""
    try:
        resp = requests.get(
            f"{POKEAPI_BASE}/pokemon/{name.strip().lower()}",
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


# ── VS banner ─────────────────────────────────────────────────────────────────

def render_vs_banner(sprite1: str | None, sprite2: str | None) -> None:
    vs_path = Path("images/pokemon.png")
    if vs_path.exists():
        with open(vs_path, "rb") as f:
            vs_b64 = base64.b64encode(f.read()).decode()
        p1_img = f"<img src='{sprite1}' style='position:absolute;left:7%;top:50%;transform:translateY(-50%);width:clamp(100px,22%,300px);filter:drop-shadow(0 0 16px rgba(230,57,70,0.6));'>" if sprite1 else ""
        p2_img = f"<img src='{sprite2}' style='position:absolute;right:7%;top:50%;transform:translateY(-50%);width:clamp(100px,22%,300px);filter:drop-shadow(0 0 16px rgba(168,218,220,0.6));'>" if sprite2 else ""
        st.markdown(
            f"<div style='position:relative;width:100%;margin:16px 0;'>"
            f"<img src='data:image/png;base64,{vs_b64}' style='width:100%;display:block;border-radius:12px;'>"
            f"{p1_img}{p2_img}</div>",
            unsafe_allow_html=True,
        )
    else:
        p1_img = f"<img src='{sprite1}' style='width:160px;filter:drop-shadow(0 0 16px rgba(230,57,70,0.6));'>" if sprite1 else ""
        p2_img = f"<img src='{sprite2}' style='width:160px;filter:drop-shadow(0 0 16px rgba(168,218,220,0.6));'>" if sprite2 else ""
        st.markdown(
            f"<div style='display:flex;align-items:center;justify-content:center;"
            f"gap:40px;padding:32px 0;background:linear-gradient(135deg,"
            f"rgba(230,57,70,0.15) 0%,rgba(14,14,14,1) 50%,rgba(168,218,220,0.15) 100%);"
            f"border-radius:12px;margin:16px 0;border:1px solid rgba(230,57,70,0.2);'>"
            f"{p1_img}"
            f"<span style='font-size:72px;font-weight:900;color:#E63946;-webkit-text-stroke:2px #0E0E0E;'>VS</span>"
            f"{p2_img}</div>",
            unsafe_allow_html=True,
        )


# ── Pokemon card ──────────────────────────────────────────────────────────────

def _section_header(title: str) -> str:
    return (
        f"<div style='text-align:center;margin:24px 0 10px;'>"
        f"<span style='color:#E63946;font-size:20px;font-weight:700;"
        f"text-transform:uppercase;letter-spacing:2px;'>{title}</span></div>"
    )


def display_pokemon_card(data: dict, col) -> int:
    """Render a Pokémon stat card into a Streamlit column. Returns total base stats."""
    with col:
        st.markdown(
            f"<div style='text-align:center;font-size:42px;font-weight:900;"
            f"color:#F1FAEE;letter-spacing:3px;text-transform:uppercase;"
            f"margin:20px 0 16px;'>{data['name']}</div>",
            unsafe_allow_html=True,
        )

        sprite_url = (
            data.get("sprites", {})
            .get("other", {})
            .get("official-artwork", {})
            .get("front_default")
        )
        if sprite_url:
            st.markdown(
                f"<div style='text-align:center;'>"
                f"<img src='{sprite_url}' style='width:180px;height:180px;"
                f"object-fit:contain;filter:drop-shadow(0 0 12px rgba(230,57,70,0.4));'>"
                f"</div>",
                unsafe_allow_html=True,
            )

        types = [t["type"]["name"] for t in data["types"]]
        st.markdown(_section_header("Type"), unsafe_allow_html=True)
        type_html = " ".join([
            f"<span style='background:{TYPE_COLORS.get(t,'#555')};color:#fff;"
            f"padding:5px 16px;border-radius:20px;margin:3px;display:inline-block;"
            f"font-size:14px;font-weight:600;'>{t.upper()}</span>"
            for t in types
        ])
        st.markdown(f"<div style='text-align:center;'>{type_html}</div>", unsafe_allow_html=True)

        st.markdown(_section_header("Stats"), unsafe_allow_html=True)
        total = 0
        stat_map = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
        for key, label in zip(STAT_KEYS, STAT_LABELS):
            val = stat_map.get(key, 0)
            total += val
            pct = round((val / MAX_STAT) * 100)
            st.markdown(
                f"<div style='margin:8px 0;'>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
                f"<span style='color:#A8DADC;font-weight:600;font-size:13px;'>{label}</span>"
                f"<span style='color:#F1FAEE;font-weight:700;font-size:13px;'>{val}</span></div>"
                f"<div style='background:rgba(230,57,70,0.18);border-radius:8px;height:14px;overflow:hidden;'>"
                f"<div style='background:#E63946;height:100%;width:{pct}%;border-radius:8px;'></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

        st.markdown(_section_header("Total Stats"), unsafe_allow_html=True)
        st.markdown(
            f"<div style='text-align:center;font-size:48px;font-weight:900;color:#F1FAEE;'>{total}</div>",
            unsafe_allow_html=True,
        )

        abilities = [a["ability"]["name"].replace("-", " ").title() for a in data["abilities"]]
        st.markdown(_section_header("Abilities"), unsafe_allow_html=True)
        ability_html = "  ".join(
            f"<span style='color:#F1FAEE;font-size:16px;font-weight:600;'>{a}</span>"
            for a in abilities
        )
        st.markdown(
            f"<div style='text-align:center;margin:8px 0;'>{ability_html}</div>",
            unsafe_allow_html=True,
        )

    return total


# ── Session state init ────────────────────────────────────────────────────────

def init_session() -> None:
    defaults = {"show_comparison": False, "p1_name": "", "p2_name": ""}
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    init_session()

    # Header
    st.markdown(
        "<div style='text-align:center;padding:32px 0 4px;'>"
        "<span style='font-size:56px;font-weight:900;letter-spacing:6px;color:#F1FAEE;'>POKE</span>"
        "<span style='font-size:56px;font-weight:900;letter-spacing:6px;color:#E63946;'>DUELER</span>"
        "</div>"
        "<p style='text-align:center;color:#A8DADC;letter-spacing:4px;font-size:13px;"
        "margin:0 0 28px;text-transform:uppercase;'>Head-to-Head · Stat for Stat</p>",
        unsafe_allow_html=True,
    )

    if not st.session_state.show_comparison:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### MY POKÉMON")
            p1 = st.text_input("First Pokémon", value="", placeholder="e.g. pikachu", label_visibility="collapsed")
        with col2:
            st.markdown("### YOUR POKÉMON")
            p2 = st.text_input("Second Pokémon", value="", placeholder="e.g. bulbasaur", label_visibility="collapsed")

        _, center, _ = st.columns([1, 2, 1])
        with center:
            compare = st.button("⚔️  BATTLE", use_container_width=True)

        if compare and p1 and p2:
            st.session_state.p1_name = p1
            st.session_state.p2_name = p2
            st.session_state.show_comparison = True
            st.rerun()

    if st.session_state.show_comparison:
        if st.button("↩️  New Battle"):
            st.session_state.show_comparison = False
            st.rerun()

        p1_name = st.session_state.p1_name
        p2_name = st.session_state.p2_name

        with st.spinner(f"Fetching {p1_name.title()} and {p2_name.title()}..."):
            data1 = get_pokemon_data(p1_name)
            data2 = get_pokemon_data(p2_name)

        if not data1:
            st.error(f"❌ '{p1_name}' not found. Check the spelling and try again.")
            st.session_state.show_comparison = False
            st.stop()
        if not data2:
            st.error(f"❌ '{p2_name}' not found. Check the spelling and try again.")
            st.session_state.show_comparison = False
            st.stop()

        sprite1 = data1.get("sprites", {}).get("other", {}).get("official-artwork", {}).get("front_default")
        sprite2 = data2.get("sprites", {}).get("other", {}).get("official-artwork", {}).get("front_default")
        render_vs_banner(sprite1, sprite2)

        st.divider()

        card1, card2 = st.columns(2)
        total1 = display_pokemon_card(data1, card1)
        total2 = display_pokemon_card(data2, card2)

        st.divider()

        if total1 > total2:
            winner_text, sub = f"🏆 {p1_name.upper()} WINS!", f"Total Stats: {total1} vs {total2}"
        elif total2 > total1:
            winner_text, sub = f"🏆 {p2_name.upper()} WINS!", f"Total Stats: {total2} vs {total1}"
        else:
            winner_text, sub = "🤝 IT'S A TIE!", f"Both have {total1} total stats"

        st.markdown(
            f"<div style='background:#E63946;color:#F1FAEE;padding:24px;border-radius:12px;"
            f"text-align:center;font-size:30px;font-weight:900;letter-spacing:2px;"
            f"box-shadow:0 6px 24px rgba(230,57,70,0.35);margin:8px 0 24px;'>"
            f"{winner_text}<br>"
            f"<span style='font-size:16px;font-weight:400;opacity:0.9;'>{sub}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
