from __future__ import annotations

import streamlit as st

from bairroiq.map_data import (
    build_district_map,
    district_from_map_selection,
    filter_districts,
    load_district_boundaries,
    selected_district_ranking,
    toggle_district_detail,
)
from bairroiq.provider import load_metrics
from bairroiq.scoring import build_scenario_insight, score_neighborhoods
from bairroiq.ui import (
    SCENARIO_DEFAULTS,
    render_header,
    render_scenario_builder,
)


_SELECTION_KEY = "selected-neighborhoods"


def _close_district_details() -> None:
    st.session_state["active-district-detail"] = None


def _update_selection(neighborhood: str) -> None:
    selected = set(st.session_state.get(_SELECTION_KEY, []))
    checkbox_key = f"district-checkbox-{neighborhood}"
    if st.session_state[checkbox_key]:
        selected.add(neighborhood)
    else:
        selected.discard(neighborhood)
    st.session_state[_SELECTION_KEY] = [
        name for name in st.session_state["neighborhood-options"] if name in selected
    ]
    st.session_state["comparison_neighborhoods"] = st.session_state[_SELECTION_KEY][:5]
    st.session_state["comparison-neighborhoods-widget"] = st.session_state[
        _SELECTION_KEY
    ][:5]


render_header("explore")
metrics = load_metrics()
neighborhood_names = metrics["neighborhood"].tolist()
if not neighborhood_names:
    st.error("A base não contém bairros para exibir.")
    st.stop()

st.session_state["neighborhood-options"] = neighborhood_names

for weight, default in SCENARIO_DEFAULTS.items():
    widget_key = f"scenario-{weight}"
    persisted_key = f"scenario-value-{weight}"
    if persisted_key not in st.session_state:
        st.session_state[persisted_key] = int(
            st.session_state.get(widget_key, default)
        )
    st.session_state[widget_key] = int(st.session_state[persisted_key])

selected_names = st.session_state[_SELECTION_KEY]
search = st.session_state.get("map-search", "")
quick_filters = st.session_state.get("map-quick-filters", [])
@st.fragment
def render_map_explorer() -> None:
    selected_names = st.session_state[_SELECTION_KEY]
    search = st.session_state.get("map-search", "")
    quick_filters = st.session_state.get("map-quick-filters", [])
    for name in neighborhood_names:
        checkbox_key = f"district-checkbox-{name}"
        if st.session_state.get(checkbox_key) != (name in selected_names):
            st.session_state[checkbox_key] = name in selected_names

    weights = {
        name: int(st.session_state[f"scenario-{name}"])
        for name in SCENARIO_DEFAULTS
    }
    weights_for_score = weights if sum(weights.values()) else SCENARIO_DEFAULTS
    scored = score_neighborhoods(metrics, weights_for_score)
    visible = filter_districts(scored, selected_names, search, quick_filters)
    figure = build_district_map(
        visible,
        load_district_boundaries(),
        theme=st.session_state.get("bairroiq-theme", "light"),
        selectable=True,
    )
    scenario_insight = build_scenario_insight(scored, weights, selected_names)
    selected_ranking = selected_district_ranking(scored, selected_names)

    visible_names = visible["neighborhood"].tolist()
    active_detail = st.session_state.get("active-district-detail")
    if active_detail not in selected_names:
        active_detail = None
        st.session_state["active-district-detail"] = None

    with st.container(key="map-stage"):
        map_generation = int(
            st.session_state.get("neighborhood-map-generation", 0)
        )
        previous_map_key = f"neighborhood-map-{map_generation - 1}"
        if map_generation and previous_map_key in st.session_state:
            del st.session_state[previous_map_key]

        map_state = st.plotly_chart(
            figure,
            key=f"neighborhood-map-{map_generation}",
            width="stretch",
            height="stretch",
            config={"displayModeBar": False, "scrollZoom": True},
            on_select="rerun",
            selection_mode="points",
        )
        selected_points = map_state.selection.points
        clicked_district = district_from_map_selection(selected_points, visible_names)
        if clicked_district:
            st.session_state["active-district-detail"] = toggle_district_detail(
                active_detail, clicked_district
            )
            st.session_state["neighborhood-map-generation"] = map_generation + 1
            st.rerun()

        active_detail = st.session_state.get("active-district-detail")
        if active_detail not in selected_names:
            active_detail = None
            st.session_state["active-district-detail"] = None
        focus_name = active_detail or (
            visible_names or selected_names or neighborhood_names
        )[0]
        focus = scored.loc[scored["neighborhood"] == focus_name].iloc[0]

        with st.container(key="scenario-panel", border=True):
            if not sum(weights.values()):
                st.markdown("### Monte seu cenário")
                st.caption("Defina ao menos uma prioridade para ativar as sugestões.")
            else:
                st.markdown("### Monte seu cenário")
                st.caption("Ajuste os pesos de 0 a 100 para recalcular o ranking.")
            render_scenario_builder()

        if active_detail:
            with st.container(key="district-popup"):
                st.markdown(f"### {active_detail} ({focus['priority_score']:.1f})")
                st.markdown(
                    '<div class="district-metrics">'
                    f'<span>Empregos <strong>{focus["formal_jobs_score"]:.1f}</strong></span>'
                    f'<span>Segurança <strong>{focus["safety_score"]:.1f}</strong></span>'
                    f'<span>LED <strong>{focus["lighting_led"]:.1f}</strong></span>'
                    f'<span>Arborização <strong>{focus["trees_score"]:.1f}</strong></span>'
                    f'<span>Mobilidade <strong>{focus["mobility_score"]:.1f}</strong></span>'
                    f'<span>Orçamento <strong>{focus["affordability_score"]:.1f}</strong></span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if scenario_insight.dominant_priority:
                    st.markdown(
                        '<div class="scenario-recommendation">'
                        f'<div class="duel-label">Sugestão · {scenario_insight.dominant_priority} '
                        f'({scenario_insight.dominant_weight}/100)</div>'
                        f'<p>Reforce {scenario_insight.dominant_priority.lower()} em '
                        f'<strong>{scenario_insight.recommended_name}</strong> '
                        f'({scenario_insight.recommended_score:.1f}/100).</p>'
                        f'<p>{scenario_insight.leader_name} lidera o cenário com '
                        f'{scenario_insight.leader_score:.1f}/100.</p>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.info("Ajuste uma prioridade para receber uma sugestão.")
                st.button(
                    "Fechar",
                    key="close-district-details",
                    width="stretch",
                    on_click=_close_district_details,
                )
        with st.container(key="ranking-panel", border=True):
            st.markdown("### Ranking de distritos")
            st.caption(
                f"Selecionados: {len(selected_names)} · No mapa: {len(visible)}"
            )
            if selected_ranking.empty:
                st.caption("Selecione bairros no menu para montar o ranking.")
            else:
                for rank, row in enumerate(
                    selected_ranking.to_dict(orient="records"), start=1
                ):
                    name = str(row["neighborhood"])
                    st.checkbox(
                        f"#{rank} {name} · {row['priority_score']:.1f}/100",
                        key=f"district-checkbox-{name}",
                        on_change=_update_selection,
                        args=(name,),
                    )
            st.caption("Clique em um bairro no mapa para ver sua análise.")


render_map_explorer()
