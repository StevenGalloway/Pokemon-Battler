"""
PokeDueler — Head-to-Head. Stat for Stat.

A Streamlit application for comparing Pokémon base stats using live data
from the PokéAPI (https://pokeapi.co). Features autocomplete search,
radar chart overlays, type effectiveness analysis, and session battle history.
"""

import base64
import logging
import random
from pathlib import Path

import plotly.graph_objects as go
import requests
import streamlit as st

from type_chart import get_type_effectiveness

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

POKEAPI_BASE = "https://pokeapi.co/api/v2"
MAX_STAT     = 255
MAX_HISTORY  = 5
REQUEST_TIMEOUT = 10

TYPE_COLORS: dict[str, str] = {
    "normal": "#A8A878",   "fire": "#F08030",    "water": "#6890F0",
    "electric": "#F8D030", "grass": "#78C850",   "ice": "#98D8D8",
    "fighting": "#C03028", "poison": "#A040A0",  "ground": "#E0C068",
    "flying": "#A890F0",   "psychic": "#F85888", "bug": "#A8B820",
    "rock": "#B8A038",     "ghost": "#705898",   "dragon": "#7038F8",
    "dark": "#705848",     "steel": "#B8B8D0",   "fairy": "#EE99AC",
}

STAT_KEYS   = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]
STAT_LABELS = ["HP", "ATK", "DEF", "SP.ATK", "SP.DEF", "SPD"]

# ── Page config (must be first Streamlit call) ────────────────────────────────

st.set_page_config(
    page_title="PokeDueler",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme CSS ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Backgrounds ── */
.stApp { background-color: #0E0E0E; }
section[data-testid="stSidebar"] {
    background-color: #141414 !important;
    border-right: 1px solid rgba(230,57,70,0.35);
}

/* ── Global text ── */
body, p, span, div, li { color: #F1FAEE; }
h1, h2, h3, h4 { color: #F1FAEE !important; }
label, .stMarkdown { color: #A8DADC !important; }

/* ── Buttons ── */
.stButton > button {
    background-color: #E63946 !important;
    color: #F1FAEE !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
    letter-spacing: 1px;
    transition: background-color 0.2s, box-shadow 0.2s;
}
.stButton > button:hover {
    background-color: #c1121f !important;
    box-shadow: 0 4px 18px rgba(230,57,70,0.45);
}
.stButton > button:focus { outline: none !important; box-shadow: none !important; }

/* ── Selectbox ── */
[data-baseweb="select"] > div {
    background-color: #1A1A1A !important;
    border: 1px solid #E63946 !important;
}
[data-baseweb="select"] span,
[data-baseweb="select"] input { color: #F1FAEE !important; }
[data-baseweb="popover"] ul { background-color: #1A1A1A !important; }
[data-baseweb="option"]:hover { background-color: rgba(230,57,70,0.25) !important; }

/* ── Text input (fallback) ── */
.stTextInput input {
    background-color: #1A1A1A !important;
    border: 1px solid #E63946 !important;
    color: #F1FAEE !important;
}

/* ── Dividers ── */
hr { border-color: rgba(230,57,70,0.25) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #141414; }
::-webkit-scrollbar-thumb { background: #E63946; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── Data layer ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_pokemon_list() -> list[str]:
    """Fetch all Pokémon names from PokéAPI. Cached for 1 hour."""
    try:
        resp = requests.get(
            f"{POKEAPI_BASE}/pokemon?limit=1302&offset=0",
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return [p["name"] for p in resp.json()["results"]]
    except requests.Timeout:
        logger.warning("PokéAPI list request timed out after %ds", REQUEST_TIMEOUT)
        return []
    except requests.RequestException as exc:
        logger.error("Failed to load Pokémon list: %s", exc)
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_pokemon_data(name: str) -> dict | None:
    """Fetch a single Pokémon's data by name. Cached for 5 minutes."""
    try:
        resp = requests.get(
            f"{POKEAPI_BASE}/pokemon/{name.strip().lower()}",
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        if status == 404:
            logger.debug("Pokémon not found: '%s'", name)
        else:
            logger.error("PokéAPI HTTP %s for '%s': %s", status, name, exc)
        return None
    except requests.Timeout:
        logger.warning("PokéAPI data request timed out for '%s'", name)
        return None
    except requests.RequestException as exc:
        logger.error("Network error fetching '%s': %s", name, exc)
        return None


# ── Chart ─────────────────────────────────────────────────────────────────────

def extract_stats(data: dict) -> list[int]:
    """Extract base stats in STAT_KEYS order from a PokéAPI Pokémon response."""
    stat_map = {s["stat"]["name"]: s["base_stat"] for s in data.get("stats", [])}
    return [stat_map.get(key, 0) for key in STAT_KEYS]


def build_radar_chart(data1: dict, data2: dict) -> go.Figure:
    """Return a Plotly Scatterpolar figure overlaying both Pokémon's base stats."""
    s1 = extract_stats(data1)
    s2 = extract_stats(data2)
    labels = STAT_LABELS + [STAT_LABELS[0]]  # close the polygon

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=s1 + [s1[0]], theta=labels, fill="toself",
        name=data1["name"].title(),
        line=dict(color="#E63946", width=2),
        fillcolor="rgba(230,57,70,0.25)",
    ))
    fig.add_trace(go.Scatterpolar(
        r=s2 + [s2[0]], theta=labels, fill="toself",
        name=data2["name"].title(),
        line=dict(color="#A8DADC", width=2),
        fillcolor="rgba(168,218,220,0.25)",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True, range=[0, MAX_STAT],
                gridcolor="rgba(255,255,255,0.08)",
                linecolor="rgba(255,255,255,0.08)",
                tickfont=dict(color="#A8DADC", size=9),
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.08)",
                linecolor="rgba(255,255,255,0.08)",
                tickfont=dict(color="#F1FAEE", size=12, family="sans-serif"),
            ),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            font=dict(color="#F1FAEE", size=13),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(230,57,70,0.3)",
            borderwidth=1,
        ),
        margin=dict(l=60, r=60, t=30, b=30),
        height=380,
    )
    return fig


# ── UI helpers ────────────────────────────────────────────────────────────────

def _badge(label: str, bg: str, text: str = "#fff") -> str:
    return (
        f"<span style='background:{bg};color:{text};padding:4px 14px;"
        f"border-radius:20px;margin:3px;display:inline-block;"
        f"font-size:13px;font-weight:600;letter-spacing:.5px;'>"
        f"{label.upper()}</span>"
    )


def _section_header(title: str) -> str:
    return (
        f"<div style='text-align:center;margin:24px 0 10px;'>"
        f"<span style='color:#E63946;font-size:20px;font-weight:700;"
        f"text-transform:uppercase;letter-spacing:2px;'>{title}</span></div>"
    )


# ── Pokémon card sub-renderers ────────────────────────────────────────────────

def render_pokemon_name(name: str) -> None:
    """Render the Pokémon name as a large heading."""
    st.markdown(
        f"<div style='text-align:center;font-size:42px;font-weight:900;"
        f"color:#F1FAEE;letter-spacing:3px;text-transform:uppercase;"
        f"margin:20px 0 16px;'>{name}</div>",
        unsafe_allow_html=True,
    )


def render_pokemon_sprite(data: dict) -> None:
    """Render the official artwork sprite if available."""
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


def render_type_section(types: list[str]) -> None:
    """Render type badge row."""
    st.markdown(_section_header("Type"), unsafe_allow_html=True)
    badges = " ".join(_badge(t, TYPE_COLORS.get(t, "#555")) for t in types)
    st.markdown(f"<div style='text-align:center;'>{badges}</div>", unsafe_allow_html=True)


def render_stat_bars(data: dict) -> int:
    """Render stat progress bars. Returns the total base stat sum."""
    st.markdown(_section_header("Stats"), unsafe_allow_html=True)
    stat_map = {s["stat"]["name"]: s["base_stat"] for s in data.get("stats", [])}
    total = 0
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
            f"<div style='background:#E63946;height:100%;width:{pct}%;border-radius:8px;"
            f"transition:width .4s ease;'></div></div></div>",
            unsafe_allow_html=True,
        )
    st.markdown(_section_header("Total Stats"), unsafe_allow_html=True)
    st.markdown(
        f"<div style='text-align:center;font-size:48px;font-weight:900;"
        f"color:#F1FAEE;'>{total}</div>",
        unsafe_allow_html=True,
    )
    return total


def render_abilities(data: dict) -> None:
    """Render the abilities list."""
    abilities = [a["ability"]["name"].replace("-", " ").title() for a in data.get("abilities", [])]
    st.markdown(_section_header("Abilities"), unsafe_allow_html=True)
    ability_html = "  ".join(
        f"<span style='color:#F1FAEE;font-size:16px;font-weight:600;'>{a}</span>"
        for a in abilities
    )
    st.markdown(
        f"<div style='text-align:center;margin:8px 0;'>{ability_html}</div>",
        unsafe_allow_html=True,
    )


def render_type_matchups(types: list[str]) -> None:
    """Render offensive and defensive type matchup badge rows."""
    eff = get_type_effectiveness(types)
    st.markdown(_section_header("Type Matchups"), unsafe_allow_html=True)
    for icon, label, key in [
        ("⚔️", "Strong vs", "strong_against"),
        ("🛡️", "Weak to",   "weak_to"),
        ("✨", "Immune to", "immune_to"),
    ]:
        items = eff[key]
        if items:
            badges = " ".join(_badge(t, TYPE_COLORS.get(t, "#555")) for t in items)
            st.markdown(
                f"<div style='margin:6px 0;'>"
                f"<span style='color:#A8DADC;font-size:13px;font-weight:600;'>"
                f"{icon} {label}: </span>"
                f"<span style='display:inline-flex;flex-wrap:wrap;gap:4px;'>{badges}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )


def display_pokemon_card(data: dict, col) -> int:
    """Render a full Pokémon card into the given Streamlit column. Returns total stats."""
    types = [t["type"]["name"] for t in data.get("types", [])]
    with col:
        render_pokemon_name(data["name"])
        render_pokemon_sprite(data)
        render_type_section(types)
        total = render_stat_bars(data)
        render_abilities(data)
        render_type_matchups(types)
    return total


# ── Battle history ────────────────────────────────────────────────────────────

def save_to_history(p1: str, p2: str, winner: str) -> None:
    if "battle_history" not in st.session_state:
        st.session_state.battle_history = []
    entry = {"p1": p1, "p2": p2, "winner": winner}
    history: list[dict] = st.session_state.battle_history
    if not history or history[0] != entry:
        st.session_state.battle_history = ([entry] + history)[:MAX_HISTORY]


def display_sidebar(pokemon_list: list[str]) -> None:
    with st.sidebar:
        st.markdown(
            "<div style='text-align:center;padding:16px 0 8px;'>"
            "<span style='font-size:28px;font-weight:900;letter-spacing:4px;color:#F1FAEE;'>POKE</span>"
            "<span style='font-size:28px;font-weight:900;letter-spacing:4px;color:#E63946;'>DUELER</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align:center;color:#A8DADC;font-size:11px;"
            "letter-spacing:2px;margin-bottom:16px;'>HEAD-TO-HEAD · STAT FOR STAT</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        st.markdown(
            "<p style='color:#E63946;font-weight:700;font-size:14px;"
            "letter-spacing:2px;text-transform:uppercase;'>⚔️ Battle History</p>",
            unsafe_allow_html=True,
        )

        history: list[dict] = st.session_state.get("battle_history", [])
        if not history:
            st.markdown(
                "<p style='color:#A8DADC;font-size:13px;'>No battles yet.</p>",
                unsafe_allow_html=True,
            )
        else:
            for i, battle in enumerate(history):
                p1, p2, winner = battle["p1"], battle["p2"], battle["winner"]
                winner_label = "Tie" if winner == "tie" else winner.title()
                st.markdown(
                    f"<div style='background:rgba(230,57,70,0.08);border:1px solid "
                    f"rgba(230,57,70,0.25);border-radius:8px;padding:10px 12px;margin:6px 0;'>"
                    f"<div style='font-size:13px;font-weight:600;color:#F1FAEE;'>"
                    f"{p1.title()} vs {p2.title()}</div>"
                    f"<div style='font-size:11px;color:#A8DADC;margin-top:2px;'>"
                    f"Winner: {winner_label}</div></div>",
                    unsafe_allow_html=True,
                )

                def _rematch(entry=battle):
                    if entry["p1"] in pokemon_list:
                        st.session_state.p1_sel = entry["p1"]
                    if entry["p2"] in pokemon_list:
                        st.session_state.p2_sel = entry["p2"]
                    st.session_state.show_comparison = True
                    st.session_state.p1_locked = entry["p1"]
                    st.session_state.p2_locked = entry["p2"]

                st.button("⚔️ Rematch", key=f"rematch_{i}", on_click=_rematch, use_container_width=True)

        st.divider()
        st.markdown(
            "<p style='color:#A8DADC;font-size:11px;text-align:center;'>"
            "Data: PokéAPI · v2.0.0</p>",
            unsafe_allow_html=True,
        )


# ── Session state init ────────────────────────────────────────────────────────

def init_session(pokemon_list: list[str]) -> None:
    defaults: dict = {
        "show_comparison": False,
        "p1_locked": "",
        "p2_locked": "",
        "battle_history": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    if pokemon_list:
        if "p1_sel" not in st.session_state:
            st.session_state.p1_sel = pokemon_list[0]
        if "p2_sel" not in st.session_state:
            st.session_state.p2_sel = pokemon_list[1] if len(pokemon_list) > 1 else pokemon_list[0]


# ── VS banner ─────────────────────────────────────────────────────────────────

def render_vs_banner(sprite1: str | None, sprite2: str | None) -> None:
    vs_path = Path("images/pokemon.png")
    if vs_path.exists():
        with open(vs_path, "rb") as f:
            vs_b64 = base64.b64encode(f.read()).decode()
        img_src = f"data:image/png;base64,{vs_b64}"
        p1_img = (
            f"<img src='{sprite1}' style='position:absolute;left:7%;top:50%;"
            f"transform:translateY(-50%);width:clamp(100px,22%,300px);"
            f"filter:drop-shadow(0 0 16px rgba(230,57,70,0.6));'>"
            if sprite1 else ""
        )
        p2_img = (
            f"<img src='{sprite2}' style='position:absolute;right:7%;top:50%;"
            f"transform:translateY(-50%);width:clamp(100px,22%,300px);"
            f"filter:drop-shadow(0 0 16px rgba(168,218,220,0.6));'>"
            if sprite2 else ""
        )
        st.markdown(
            f"<div style='position:relative;width:100%;margin:16px 0;'>"
            f"<img src='{img_src}' style='width:100%;display:block;border-radius:12px;'>"
            f"{p1_img}{p2_img}</div>",
            unsafe_allow_html=True,
        )
    else:
        p1_img = (
            f"<img src='{sprite1}' style='width:160px;"
            f"filter:drop-shadow(0 0 16px rgba(230,57,70,0.6));'>"
            if sprite1 else ""
        )
        p2_img = (
            f"<img src='{sprite2}' style='width:160px;"
            f"filter:drop-shadow(0 0 16px rgba(168,218,220,0.6));'>"
            if sprite2 else ""
        )
        st.markdown(
            f"<div style='display:flex;align-items:center;justify-content:center;"
            f"gap:40px;padding:32px 0;background:linear-gradient(135deg,"
            f"rgba(230,57,70,0.15) 0%,rgba(14,14,14,1) 50%,rgba(168,218,220,0.15) 100%);"
            f"border-radius:12px;margin:16px 0;border:1px solid rgba(230,57,70,0.2);'>"
            f"{p1_img}"
            f"<span style='font-size:72px;font-weight:900;color:#E63946;"
            f"-webkit-text-stroke:2px #0E0E0E;'>VS</span>"
            f"{p2_img}</div>",
            unsafe_allow_html=True,
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    with st.spinner("Loading Pokédex..."):
        pokemon_list = load_pokemon_list()

    use_text_fallback = not pokemon_list
    init_session(pokemon_list)
    display_sidebar(pokemon_list)

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

    # Input section
    if not st.session_state.show_comparison:
        col1, col2 = st.columns(2)

        def rand_p1():
            if pokemon_list:
                st.session_state.p1_sel = random.choice(pokemon_list)

        def rand_p2():
            if pokemon_list:
                st.session_state.p2_sel = random.choice(pokemon_list)

        with col1:
            st.markdown("### MY POKÉMON")
            p1_in_col, p1_btn_col = st.columns([5, 1])
            with p1_in_col:
                if use_text_fallback:
                    p1_input = st.text_input("Name", value="pikachu", key="p1_text", label_visibility="collapsed")
                else:
                    p1_input = st.selectbox(
                        "MY POKÉMON", pokemon_list,
                        index=pokemon_list.index(st.session_state.p1_sel) if st.session_state.p1_sel in pokemon_list else 0,
                        key="p1_sel", label_visibility="collapsed",
                    )
            with p1_btn_col:
                st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)
                st.button("🎲", key="rand1", on_click=rand_p1, help="Random Pokémon", use_container_width=True)

        with col2:
            st.markdown("### YOUR POKÉMON")
            p2_in_col, p2_btn_col = st.columns([5, 1])
            with p2_in_col:
                if use_text_fallback:
                    p2_input = st.text_input("Name", value="bulbasaur", key="p2_text", label_visibility="collapsed")
                else:
                    p2_input = st.selectbox(
                        "YOUR POKÉMON", pokemon_list,
                        index=pokemon_list.index(st.session_state.p2_sel) if st.session_state.p2_sel in pokemon_list else 0,
                        key="p2_sel", label_visibility="collapsed",
                    )
            with p2_btn_col:
                st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)
                st.button("🎲", key="rand2", on_click=rand_p2, help="Random Pokémon", use_container_width=True)

        _, center, _ = st.columns([1, 2, 1])
        with center:
            compare = st.button("⚔️  BATTLE", use_container_width=True)

        if compare:
            p1_name = p1_input if use_text_fallback else st.session_state.p1_sel
            p2_name = p2_input if use_text_fallback else st.session_state.p2_sel
            if p1_name and p2_name:
                st.session_state.p1_locked = p1_name
                st.session_state.p2_locked = p2_name
                st.session_state.show_comparison = True
                st.rerun()

    # Comparison results
    if st.session_state.show_comparison:
        if st.button("↩️  New Battle", key="reset"):
            st.session_state.show_comparison = False
            st.rerun()

        p1_name = st.session_state.p1_locked
        p2_name = st.session_state.p2_locked

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

        st.markdown(
            "<p style='text-align:center;color:#A8DADC;font-size:13px;"
            "letter-spacing:2px;text-transform:uppercase;margin-bottom:0;'>Stat Comparison</p>",
            unsafe_allow_html=True,
        )
        _, chart_col, _ = st.columns([1, 3, 1])
        with chart_col:
            st.plotly_chart(build_radar_chart(data1, data2), use_container_width=True)

        st.divider()

        card1, card2 = st.columns(2)
        total1 = display_pokemon_card(data1, card1)
        total2 = display_pokemon_card(data2, card2)

        st.divider()

        if total1 > total2:
            winner_text  = f"🏆 {p1_name.upper()} WINS!"
            winner_sub   = f"Total Stats: {total1} vs {total2}"
            winner_name  = p1_name
            banner_color = "#E63946"
        elif total2 > total1:
            winner_text  = f"🏆 {p2_name.upper()} WINS!"
            winner_sub   = f"Total Stats: {total2} vs {total1}"
            winner_name  = p2_name
            banner_color = "#E63946"
        else:
            winner_text  = "🤝 IT'S A TIE!"
            winner_sub   = f"Both have {total1} total stats"
            winner_name  = "tie"
            banner_color = "#457B9D"

        st.markdown(
            f"<div style='background:{banner_color};color:#F1FAEE;padding:24px;"
            f"border-radius:12px;text-align:center;font-size:30px;font-weight:900;"
            f"letter-spacing:2px;box-shadow:0 6px 24px rgba(230,57,70,0.35);margin:8px 0 24px;'>"
            f"{winner_text}<br>"
            f"<span style='font-size:16px;font-weight:400;opacity:0.9;'>{winner_sub}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        save_to_history(p1_name, p2_name, winner_name)


if __name__ == "__main__":
    main()
