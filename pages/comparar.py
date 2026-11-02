from __future__ import annotations

from html import escape

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from bairroiq.map_data import (
    build_district_map,
    filter_districts,
    load_district_boundaries,
    selected_district_ranking,
)
from bairroiq.provider import load_history, load_metrics
from bairroiq.scoring import score_neighborhoods
from bairroiq.ui import (
    SCENARIO_DEFAULTS,
    render_header,
    render_scenario_builder,
    theme_palette,
)


_METRIC_OPTIONS = {
    "Empregos": "formal_jobs_score",
    "Segurança": "safety_score",
    "Iluminação LED": "lighting_led",
    "Arborização": "trees_score",
    "Mobilidade": "mobility_score",
    "Custo de vida": "affordability_score",
}
_HISTORY_METRICS = {
    "Empregos": "formal_jobs_score",
    "Iluminação LED": "lighting_led",
    "Segurança": "safety_score",
}
_COLORS = ["#2d8a6e", "#356ae6", "#d96b43", "#8a58b5", "#c59b35"]


def _sync_map_selection() -> None:
    selected = st.session_state["comparison-neighborhoods-widget"]
    st.session_state["selected-neighborhoods"] = selected
    st.session_state["comparison_neighborhoods"] = selected


render_header("compare")
st.title("Analytics / Comparação")
st.caption(
    "Explore o ranking, compare indicadores e acompanhe a evolução dos bairros selecionados."
)

palette = theme_palette()
metrics = load_metrics()
history = load_history()
all_neighborhoods = metrics["neighborhood"].tolist()

if "comparison-neighborhoods-widget" not in st.session_state:
    st.session_state["comparison-neighborhoods-widget"] = st.session_state.get(
        "comparison_neighborhoods",
        st.session_state.get("selected-neighborhoods", all_neighborhoods[:3]),
    )
st.session_state["comparison-neighborhoods-widget"] = [
    name
    for name in st.session_state["comparison-neighborhoods-widget"]
    if name in all_neighborhoods
]

selection_col, focus_col = st.columns([1.35, 1], gap="large")
with selection_col:
    selected = st.multiselect(
        "Regiões da análise",
        options=all_neighborhoods,
        max_selections=5,
        key="comparison-neighborhoods-widget",
        on_change=_sync_map_selection,
        placeholder="Selecione até cinco bairros",
    )
with focus_col:
    focus_mode = st.radio(
        "Foco da análise",
        options=["Visão geral", "Oportunidades", "Tendências"],
        horizontal=True,
        key="comparison-focus-mode",
    )

if len(selected) < 2:
    st.info("Selecione pelo menos dois bairros para visualizar a comparação completa.")
    st.stop()

for key, default in SCENARIO_DEFAULTS.items():
    st.session_state.setdefault(f"scenario-value-{key}", default)
weights = {
    key: int(st.session_state[f"scenario-value-{key}"])
    for key in SCENARIO_DEFAULTS
}
score_weights = weights if sum(weights.values()) else SCENARIO_DEFAULTS
scored = score_neighborhoods(metrics, score_weights)
comparison = scored[scored["neighborhood"].isin(selected)].copy()
ranking = selected_district_ranking(scored, selected)
history_comparison = history[history["neighborhood"].isin(selected)].copy()

dimensions = dict(_METRIC_OPTIONS)
if focus_mode == "Oportunidades":
    dimensions = {"Empregos": _METRIC_OPTIONS["Empregos"]}
elif focus_mode == "Tendências":
    dimensions = {
        "Empregos": "formal_jobs_score",
        "Iluminação LED": "lighting_led",
        "Segurança": "safety_score",
    }

leader = comparison.sort_values("priority_score", ascending=False).iloc[0]
average_score = comparison["priority_score"].mean()
active_priority = max(
    ((key, value) for key, value in weights.items() if value > 0),
    key=lambda item: item[1],
    default=None,
)
priority_labels = {
    "trees": "Arborização",
    "safety": "Segurança",
    "mobility": "Mobilidade",
    "budget": "Custo de vida",
}

st.markdown('<div class="section-heading">Resumo da análise</div>', unsafe_allow_html=True)
metric_columns = st.columns(4, gap="medium")
summary_metrics = (
    ("Bairros analisados", len(comparison), None),
    ("Líder do cenário", str(leader["neighborhood"]), f'{leader["priority_score"]:.1f}/100'),
    ("Média de aderência", f"{average_score:.1f}/100", None),
    (
        "Prioridade principal",
        priority_labels[active_priority[0]] if active_priority else "Nenhuma",
        f"{active_priority[1]}%" if active_priority else None,
    ),
)
for index, (label, value, detail) in enumerate(summary_metrics):
    with metric_columns[index]:
        with st.container(key=f"comparison-summary-{index + 1}", border=True):
            st.metric(label, value, detail)


st.markdown('<div class="section-heading">Resumo por indicador</div>', unsafe_allow_html=True)
table_data = comparison[["neighborhood", *dimensions.values(), "priority_score"]].copy()
table_data.columns = [
    "Bairro",
    *dimensions.keys(),
    "Aderência",
]
st.dataframe(
    table_data.sort_values("Aderência", ascending=False),
    width="stretch",
    hide_index=True,
    column_config={name: st.column_config.NumberColumn(format="%.1f%%") for name in [*dimensions.keys(), "Aderência"]},
)

search = st.session_state.get("map-search", "")
quick_filters = st.session_state.get("map-quick-filters", [])
visible = filter_districts(scored, selected, search, quick_filters)
scenario_column, map_column, ranking_column = st.columns(
    [0.7, 1.35, 0.85], gap="medium"
)

with map_column:
    with st.container(key="comparison-map-card", border=True):
        st.markdown('<div class="section-heading">Mapa por pontuação</div>', unsafe_allow_html=True)
        map_figure = build_district_map(
            visible,
            load_district_boundaries(),
            theme=st.session_state.get("bairroiq-theme", "light"),
        )
        st.plotly_chart(
            map_figure,
            key="comparison-map",
            width="stretch",
            height=390,
            config={"displayModeBar": False, "scrollZoom": True},
        )

with ranking_column:
    with st.container(key="comparison-ranking-card", border=True):
        st.markdown('<div class="section-heading">Ranking dos distritos</div>', unsafe_allow_html=True)
        st.caption(f"Exibindo {len(visible)} de {len(selected)} selecionados")
        visible_ranking = ranking[ranking["neighborhood"].isin(visible["neighborhood"])]
        for position, row in enumerate(
            visible_ranking.sort_values("priority_score", ascending=False).to_dict(
                orient="records"
            ),
            start=1,
        ):
            st.markdown(
                f'<div class="ranking-row"><span>#{position} '
                f'{escape(str(row["neighborhood"]))}</span><strong>'
                f'{row["priority_score"]:.1f}</strong></div>',
                unsafe_allow_html=True,
            )
        if not len(visible_ranking):
            st.info("Os filtros atuais não retornaram bairros.")
        st.caption("Pontuação personalizada de 0 a 100")

with scenario_column:
    with st.container(key="scenario-dashboard", border=True):
        st.markdown("### Monte seu cenário")
        st.caption("Ajuste os pesos de 0 a 100 para recalcular o ranking.")
        weights = render_scenario_builder()

st.markdown('<div class="section-heading">Comparação por dimensão</div>', unsafe_allow_html=True)
bar_column, radar_column = st.columns(2, gap="medium")
comparison_chart_data = comparison.melt(
    id_vars="neighborhood",
    value_vars=list(dimensions.values()),
    var_name="metric",
    value_name="score",
)
metric_labels = {column: label for label, column in dimensions.items()}
comparison_chart_data["metric"] = comparison_chart_data["metric"].map(metric_labels)

with bar_column:
    st.markdown("#### Indicadores dos bairros")
    bar_figure = px.bar(
        comparison_chart_data,
        x="metric",
        y="score",
        color="neighborhood",
        barmode="group",
        color_discrete_sequence=_COLORS,
        labels={"metric": "Indicador", "score": "Nota (0–100)", "neighborhood": "Bairro"},
    )
    bar_figure.update_layout(
        height=440,
        margin={"r": 12, "t": 12, "l": 8, "b": 80},
        paper_bgcolor=palette["surface"],
        plot_bgcolor=palette["surface"],
        font={"color": palette["ink"], "size": 11},
        xaxis={
            "tickangle": -20,
            "gridcolor": palette["line"],
            "tickfont": {"color": palette["ink"]},
            "title_font": {"color": palette["ink"]},
            "automargin": True,
        },
        yaxis={
            "range": [0, 100],
            "gridcolor": palette["line"],
            "tickfont": {"color": palette["ink"]},
            "title_font": {"color": palette["ink"]},
        },
        legend={"orientation": "h", "y": -0.32, "font": {"color": palette["ink"]}},
    )
    st.plotly_chart(bar_figure, width="stretch", config={"displayModeBar": False})

with radar_column:
    st.markdown("#### Perfil por dimensão")
    radar = go.Figure()
    for _, row in comparison.iterrows():
        radar.add_trace(
            go.Scatterpolar(
                r=[row[column] for column in dimensions.values()],
                theta=list(dimensions),
                fill="toself",
                name=row["neighborhood"],
                opacity=0.58,
                line={"width": 2},
            )
        )
    radar.update_layout(
        polar={
            "radialaxis": {
                "visible": True,
                "range": [0, 100],
                "gridcolor": palette["line"],
                "linecolor": palette["muted"],
                "tickfont": {"color": palette["ink"]},
            },
            "angularaxis": {
                "gridcolor": palette["line"],
                "linecolor": palette["muted"],
                "tickfont": {"color": palette["ink"]},
            },
            "bgcolor": palette["surface"],
        },
        height=440,
        margin={"r": 35, "t": 20, "l": 35, "b": 60},
        paper_bgcolor=palette["surface"],
        plot_bgcolor=palette["surface"],
        font={"color": palette["ink"], "size": 11},
        colorway=_COLORS,
        legend={"orientation": "h", "y": -0.2, "font": {"color": palette["ink"]}},
    )
    st.plotly_chart(radar, width="stretch", config={"displayModeBar": False})

st.markdown('<div class="section-heading">Evolução temporal</div>', unsafe_allow_html=True)
trend_control, year_control = st.columns([1, 2], gap="medium")
with trend_control:
    trend_metric = st.selectbox(
        "Indicador ao longo do tempo",
        options=list(_HISTORY_METRICS),
        index=1 if focus_mode == "Tendências" else 0,
    )
with year_control:
    years = st.slider("Período analisado", 2020, 2025, (2020, 2025))
trend_column = _HISTORY_METRICS[trend_metric]
trend_data = history_comparison[
    history_comparison["year"].between(years[0], years[1])
]
trend = px.line(
    trend_data,
    x="year",
    y=trend_column,
    color="neighborhood",
    markers=True,
    color_discrete_sequence=_COLORS,
    labels={
        "year": "Ano",
        trend_column: "Índice (0–100)",
        "neighborhood": "Bairro",
    },
)
trend.update_layout(
    height=340,
    margin={"r": 18, "t": 12, "l": 8, "b": 10},
    paper_bgcolor=palette["surface"],
    plot_bgcolor=palette["surface"],
    font={"color": palette["ink"], "size": 11},
    xaxis={"gridcolor": palette["line"], "linecolor": palette["muted"]},
    yaxis={"gridcolor": palette["line"], "linecolor": palette["muted"]},
    legend={"orientation": "h", "y": -0.2, "font": {"color": palette["ink"]}},
)
st.plotly_chart(trend, width="stretch", config={"displayModeBar": False})

st.markdown('<div class="section-heading">Diferenciais do duelo</div>', unsafe_allow_html=True)
scenario_dimensions = {
    "trees": ("Arborização", "trees_score"),
    "safety": ("Segurança", "safety_score"),
    "mobility": ("Mobilidade", "mobility_score"),
    "budget": ("Custo de vida", "affordability_score"),
}
active_dimensions = [
    (key, *scenario_dimensions[key])
    for key, weight in weights.items()
    if weight > 0
]
duel_columns = st.columns(min(3, len(comparison)), gap="medium")
for rank, (_, row) in enumerate(
    comparison.sort_values("priority_score", ascending=False).iterrows(),
    start=1,
):
    strongest = sorted(
        _METRIC_OPTIONS.items(),
        key=lambda item: row[item[1]],
        reverse=True,
    )[:2]
    weakest = min(_METRIC_OPTIONS.items(), key=lambda item: row[item[1]])
    with duel_columns[(rank - 1) % len(duel_columns)]:
        with st.container(key=f"duel-card-{rank}", border=True):
            st.markdown(
                f'#### #{rank} {escape(str(row["neighborhood"]))}'
            )
            st.markdown(
                f'<div class="duel-score">{row["priority_score"]:.1f}/100</div>'
                '<div class="duel-label">Aderência ao cenário</div>'
                '<div class="duel-item"><strong>Destaques:</strong> '
                f'{escape(strongest[0][0])} {row[strongest[0][1]]:.1f} · '
                f'{escape(strongest[1][0])} {row[strongest[1][1]]:.1f}</div>',
                unsafe_allow_html=True,
            )
            if active_dimensions and active_priority:
                weakest_priority = min(
                    active_dimensions, key=lambda item: row[item[2]]
                )
                st.markdown(
                    '<div class="duel-item"><strong>Prioridade principal:</strong> '
                    f'{escape(priority_labels[active_priority[0]])} '
                    f'({active_priority[1]}/100) · '
                    f'{row[weakest_priority[2]]:.1f}/100</div>'
                    '<div class="duel-item duel-opportunity"><strong>Oportunidade:</strong> '
                    f'{escape(weakest_priority[1])} '
                    f'({row[weakest_priority[2]]:.1f}/100)</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="duel-item duel-opportunity"><strong>Oportunidade:</strong> '
                    f'{escape(weakest[0])} ({row[weakest[1]]:.1f}/100)</div>',
                    unsafe_allow_html=True,
                )

st.markdown(
    '<div class="source-note">Protótipo com dados demonstrativos. '
    "Conecte o Observa Sampa pelo adaptador Databricks para substituir esta amostra.</div>",
    unsafe_allow_html=True,
)
