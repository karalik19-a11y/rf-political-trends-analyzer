"""Regional political analytics dashboard: map + elections + media heat."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
_ROOT = _SRC.parent
sys.path.insert(0, str(_SRC))
sys.path.insert(0, str(_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st
import folium
from streamlit_folium import st_folium

from territories import load_regions, region_by_code
from elections import elections_with_geo, write_demo_seed, load_all_elections
from regional_db import init_regional_db, media_by_region, region_mention_counts
from collector_regional import collect_regional

st.set_page_config(page_title="RF Regional Political Analytics", layout="wide")
st.title("Региональная политическая аналитика РФ")
st.caption(
    "A: территории · B: выборы по субъектам · C: медиа → регион/город. "
    "Агрегаты, не слежка за людьми. Уровень: субъект / город (топнимы), не улица."
)

init_regional_db()

# Sidebar
st.sidebar.header("Данные")
if st.sidebar.button("Собрать медиа + геопривязка", type="primary"):
    with st.spinner("RSS независимых источников..."):
        try:
            n = collect_regional()
            st.sidebar.success(f"Новых: {n}")
            st.rerun()
        except Exception as e:
            st.sidebar.error(str(e))

if st.sidebar.button("Создать DEMO-структуру выборов"):
    p = write_demo_seed()
    st.sidebar.info(f"Записано: {p.name} (замените официальным CSV)")

st.sidebar.markdown(
    """
**Загрузка выборов:** положите CSV в `data/elections/`  
Колонки: `election_id,region_code,turnout_pct`  
(+ optional: `leader_share_pct,region_name,source`)
"""
)

tab_map, tab_el, tab_media, tab_cmp = st.tabs(
    ["Карта", "Выборы (B)", "Медиа по регионам (C)", "Сравнение"]
)

regions = load_regions()
reg_df = pd.DataFrame(regions)
mentions = region_mention_counts()
reg_df["media_mentions"] = reg_df["code"].map(lambda c: mentions.get(c, 0))

el_df = elections_with_geo()

with tab_map:
    st.subheader("Карта субъектов")
    metric = st.selectbox(
        "Показатель на карте",
        ["media_mentions", "turnout_pct", "leader_share_pct"],
        format_func=lambda x: {
            "media_mentions": "Упоминания в медиа (C)",
            "turnout_pct": "Явка % (выборы B)",
            "leader_share_pct": "Доля лидера % (B)",
        }.get(x, x),
    )
    m = folium.Map(location=[64, 95], zoom_start=3)

    # merge election metric if needed
    plot_df = reg_df.copy()
    if metric in ("turnout_pct", "leader_share_pct") and not el_df.empty:
        # latest election_id group
        latest = el_df["election_id"].iloc[0]
        sub = el_df[el_df["election_id"] == el_df["election_id"].value_counts().index[0]]
        plot_df = plot_df.merge(
            sub[["region_code", metric]].rename(columns={"region_code": "code"}),
            on="code",
            how="left",
        )
        vals = plot_df[metric].fillna(0)
    else:
        vals = plot_df["media_mentions"].fillna(0)
        metric = "media_mentions"

    vmax = max(float(vals.max()), 1.0)
    for _, row in plot_df.iterrows():
        v = float(row.get(metric) or 0)
        radius = 5 + 25 * (v / vmax)
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius,
            popup=f"{row['name']}<br>{metric}={v}",
            tooltip=row["name"],
            color="#1f77b4",
            fill=True,
            fill_opacity=0.6,
        ).add_to(m)
    st_folium(m, width=None, height=520)
    st.dataframe(
        plot_df[["code", "name", "fd", "capital", "media_mentions"]].sort_values(
            "media_mentions", ascending=False
        ),
        use_container_width=True,
    )

with tab_el:
    st.subheader("Выборы по субъектам")
    if el_df.empty:
        st.warning("Нет CSV в data/elections/. Нажмите «Создать DEMO-структуру» или загрузите официальные данные.")
    else:
        eids = el_df["election_id"].unique().tolist()
        eid = st.selectbox("Кампания", eids)
        sub = el_df[el_df["election_id"] == eid].copy()
        st.write(f"Записей: {len(sub)}")
        if sub["source"].astype(str).str.contains("DEMO").any():
            st.error(
                "Сейчас загружена DEMO-структура (не официальные результаты). "
                "Подставьте CSV из открытых данных ЦИК / исследований."
            )
        c1, c2 = st.columns(2)
        with c1:
            if "turnout_pct" in sub.columns:
                fig = px.bar(
                    sub.sort_values("turnout_pct", ascending=False).head(20),
                    x="turnout_pct",
                    y="region_name" if "region_name" in sub.columns else "region_code",
                    orientation="h",
                    title="Топ-20 явка %",
                )
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            if "leader_share_pct" in sub.columns:
                fig = px.bar(
                    sub.sort_values("leader_share_pct", ascending=False).head(20),
                    x="leader_share_pct",
                    y="region_name" if "region_name" in sub.columns else "region_code",
                    orientation="h",
                    title="Топ-20 доля лидера %",
                )
                st.plotly_chart(fig, use_container_width=True)
        st.dataframe(sub, use_container_width=True)

with tab_media:
    st.subheader("Медиа → регион / город")
    items = media_by_region(3000)
    if not items:
        st.info("Нет новостей. Нажмите «Собрать медиа + геопривязка». При блокировках RSS — VPN.")
    else:
        mdf = pd.DataFrame(items)
        tagged = mdf["region_code"].notna().sum()
        st.metric("С геопривязкой", f"{tagged} / {len(mdf)}")
        counts = mdf.dropna(subset=["region_code"]).groupby("region_code").size().reset_index(name="n")
        counts["name"] = counts["region_code"].map(
            lambda c: (region_by_code(c) or {}).get("name", c)
        )
        fig = px.bar(
            counts.sort_values("n", ascending=False).head(25),
            x="n",
            y="name",
            orientation="h",
            title="Упоминания регионов в заголовках/текстах",
        )
        st.plotly_chart(fig, use_container_width=True)
        city_counts = (
            mdf.dropna(subset=["city_tag"])
            .groupby("city_tag")
            .size()
            .reset_index(name="n")
            .sort_values("n", ascending=False)
            .head(20)
        )
        if not city_counts.empty:
            st.subheader("Топ городов (по топонимам в тексте)")
            st.plotly_chart(
                px.bar(city_counts, x="n", y="city_tag", orientation="h"),
                use_container_width=True,
            )
        st.subheader("Лента с геометкой")
        for _, r in mdf.head(30).iterrows():
            geo = r["region_code"] or "—"
            city = r["city_tag"] or ""
            st.markdown(
                f"**[{r['source']}]** [{r['title']}]({r['link']})  \n"
                f"*{r['published']} · region={geo} · city={city}*"
            )

with tab_cmp:
    st.subheader("Сравнение субъектов")
    codes = [r["code"] for r in regions]
    names = {r["code"]: r["name"] for r in regions}
    a = st.selectbox("Регион A", codes, format_func=lambda c: names.get(c, c), index=min(76, len(codes)-1))
    b = st.selectbox("Регион B", codes, format_func=lambda c: names.get(c, c), index=min(77, len(codes)-1))
    col1, col2 = st.columns(2)
    for col, code in ((col1, a), (col2, b)):
        with col:
            st.markdown(f"### {names.get(code, code)}")
            st.write("Медиа-упоминаний:", mentions.get(code, 0))
            if not el_df.empty:
                row = el_df[el_df["region_code"] == code]
                if not row.empty:
                    st.write(row[["election_id", "turnout_pct", "leader_share_pct"]].head(5))
            local = [x for x in media_by_region(500) if x.get("region_code") == code][:8]
            for x in local:
                st.caption(f"• {x['title'][:100]}")

st.markdown("---")
st.caption(
    "Не госСМИ в RSS. Выборы — только из ваших CSV/открытых данных. "
    "Нет сбора политических взглядов частных лиц по улицам."
)
