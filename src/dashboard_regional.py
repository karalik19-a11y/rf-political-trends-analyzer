"""Regional political analytics dashboard."""

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
from elections import elections_with_geo, write_demo_seed
from regional_db import init_regional_db, media_by_region, region_mention_counts
from collector_regional import collect_regional
from updater import check_update, apply_update, read_local_version

st.set_page_config(page_title="Аналитика регионов РФ", layout="wide")
st.title("Региональная политическая аналитика РФ")
st.caption("Карта · новости по регионам · выборы. Запуск: START.bat")

init_regional_db()

st.sidebar.header("Обновление")
st.sidebar.caption(f"Версия {read_local_version()}")

if st.sidebar.button("Проверить обновление на GitHub"):
    with st.spinner("Проверка..."):
        try:
            available, info = check_update()
            st.session_state["upd_info"] = info
            st.session_state["upd_avail"] = available
        except Exception as e:
            st.sidebar.error(f"Не удалось проверить: {e}")

info = st.session_state.get("upd_info")
if info:
    st.sidebar.write(f"Сейчас: **{info.get('local_version')}**")
    st.sidebar.write(f"На сайте: **{info.get('remote_version')}**")
    if st.session_state.get("upd_avail"):
        st.sidebar.warning("Доступно обновление")
        if st.sidebar.button("Скачать и установить", type="primary"):
            with st.spinner("Установка..."):
                try:
                    apply_update()
                    st.sidebar.success("Готово. Закройте программу и снова нажмите START.bat")
                    st.session_state["upd_avail"] = False
                except Exception as e:
                    st.sidebar.error(str(e))
    else:
        st.sidebar.success("У вас последняя версия")

st.sidebar.markdown("---")
st.sidebar.header("Данные")
if st.sidebar.button("Собрать новости по регионам", type="primary"):
    with st.spinner("Загрузка новостей..."):
        try:
            n = collect_regional()
            st.sidebar.success(f"Добавлено новых: {n}")
            st.rerun()
        except Exception as e:
            st.sidebar.error(str(e))

if st.sidebar.button("Создать пример данных выборов"):
    p = write_demo_seed()
    st.sidebar.info("Пример создан. Для реальных данных нужен файл CSV в папке data/elections")

tab_map, tab_el, tab_media, tab_cmp = st.tabs(
    ["Карта", "Выборы", "Новости по регионам", "Сравнение"]
)

regions = load_regions()
reg_df = pd.DataFrame(regions)
mentions = region_mention_counts()
reg_df["media_mentions"] = reg_df["code"].map(lambda c: mentions.get(c, 0))
el_df = elections_with_geo()

with tab_map:
    st.subheader("Карта субъектов")
    metric = st.selectbox(
        "Что показать на карте",
        ["media_mentions", "turnout_pct", "leader_share_pct"],
        format_func=lambda x: {
            "media_mentions": "Сколько раз регион упоминался в новостях",
            "turnout_pct": "Явка на выборах, %",
            "leader_share_pct": "Доля лидера, %",
        }.get(x, x),
    )
    m = folium.Map(location=[64, 95], zoom_start=3)
    plot_df = reg_df.copy()
    use_metric = "media_mentions"
    if metric in ("turnout_pct", "leader_share_pct") and not el_df.empty:
        eid = el_df["election_id"].value_counts().index[0]
        sub = el_df[el_df["election_id"] == eid]
        plot_df = plot_df.merge(
            sub[["region_code", metric]].rename(columns={"region_code": "code"}),
            on="code",
            how="left",
        )
        use_metric = metric
    vals = plot_df[use_metric].fillna(0) if use_metric in plot_df.columns else plot_df["media_mentions"].fillna(0)
    vmax = max(float(vals.max()), 1.0)
    for _, row in plot_df.iterrows():
        v = float(row.get(use_metric) or 0)
        radius = 5 + 25 * (v / vmax)
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius,
            popup=f"{row['name']}<br>{use_metric}={v}",
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
    st.subheader("Выборы по регионам")
    if el_df.empty:
        st.warning("Пока нет данных. Слева можно создать пример или положить CSV в data/elections.")
    else:
        eids = el_df["election_id"].unique().tolist()
        eid = st.selectbox("Какая кампания", eids)
        sub = el_df[el_df["election_id"] == eid].copy()
        if sub["source"].astype(str).str.contains("DEMO").any():
            st.warning("Сейчас показан пример, не официальные цифры ЦИК.")
        c1, c2 = st.columns(2)
        with c1:
            if "turnout_pct" in sub.columns:
                st.plotly_chart(
                    px.bar(
                        sub.sort_values("turnout_pct", ascending=False).head(20),
                        x="turnout_pct",
                        y="region_name" if "region_name" in sub.columns else "region_code",
                        orientation="h",
                        title="Явка %",
                    ),
                    use_container_width=True,
                )
        with c2:
            if "leader_share_pct" in sub.columns:
                st.plotly_chart(
                    px.bar(
                        sub.sort_values("leader_share_pct", ascending=False).head(20),
                        x="leader_share_pct",
                        y="region_name" if "region_name" in sub.columns else "region_code",
                        orientation="h",
                        title="Доля лидера %",
                    ),
                    use_container_width=True,
                )
        st.dataframe(sub, use_container_width=True)

with tab_media:
    st.subheader("Новости по регионам")
    items = media_by_region(3000)
    if not items:
        st.info("Нажмите слева «Собрать новости по регионам». Если не грузится — попробуйте VPN.")
    else:
        mdf = pd.DataFrame(items)
        st.metric("С привязкой к региону", f"{mdf['region_code'].notna().sum()} из {len(mdf)}")
        counts = mdf.dropna(subset=["region_code"]).groupby("region_code").size().reset_index(name="n")
        counts["name"] = counts["region_code"].map(lambda c: (region_by_code(c) or {}).get("name", c))
        st.plotly_chart(
            px.bar(counts.sort_values("n", ascending=False).head(25), x="n", y="name", orientation="h"),
            use_container_width=True,
        )
        city_counts = (
            mdf.dropna(subset=["city_tag"]).groupby("city_tag").size().reset_index(name="n")
            .sort_values("n", ascending=False).head(20)
        )
        if not city_counts.empty:
            st.subheader("Города")
            st.plotly_chart(px.bar(city_counts, x="n", y="city_tag", orientation="h"), use_container_width=True)
        for _, r in mdf.head(25).iterrows():
            st.markdown(
                f"**[{r['source']}]** [{r['title']}]({r['link']})  \n"
                f"*{r['published']} · {r['region_code'] or '—'} · {r['city_tag'] or ''}*"
            )

with tab_cmp:
    st.subheader("Сравнить два региона")
    codes = [r["code"] for r in regions]
    names = {r["code"]: r["name"] for r in regions}
    a = st.selectbox("Первый регион", codes, format_func=lambda c: names.get(c, c), index=min(76, len(codes) - 1))
    b = st.selectbox("Второй регион", codes, format_func=lambda c: names.get(c, c), index=min(77, len(codes) - 1))
    for col, code in zip(st.columns(2), (a, b)):
        with col:
            st.markdown(f"### {names.get(code, code)}")
            st.write("Упоминаний в новостях:", mentions.get(code, 0))
            if not el_df.empty:
                row = el_df[el_df["region_code"] == code]
                if not row.empty:
                    st.write(row[["election_id", "turnout_pct", "leader_share_pct"]].head(3))

st.caption("Закрыть программу: закрыть чёрное окно START.bat")
