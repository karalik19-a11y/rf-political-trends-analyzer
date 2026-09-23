"""Streamlit dashboard for RF political trends."""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from database import init_db, get_recent_items
from analyzer import load_dataframe, top_keywords, volume_by_day, volume_by_source, recent_trends, keyword_timeline

st.set_page_config(page_title="RF Political Trends Analyzer", layout="wide")

st.title("Анализатор политических тенденций РФ (публичные источники)")
st.caption("Данные собираются только из открытых RSS-лент. Система для исследовательских целей.")

init_db()

# Sidebar
st.sidebar.header("Управление")
if st.sidebar.button("Обновить данные (запустить collector)"):
    with st.spinner("Сбор новостей..."):
        from collector import collect
        collect()
    st.sidebar.success("Сбор завершён")

days = st.sidebar.slider("Период анализа (дней)", 1, 30, 7)
limit = st.sidebar.number_input("Лимит записей для анализа", 100, 10000, 2000)

df = load_dataframe(limit=limit)

if df.empty:
    st.warning("База пуста. Нажмите «Обновить данные» в сайдбаре или запустите `python -m src.collector`.")
    st.stop()

# Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Всего записей в выборке", len(df))
col2.metric("Источников", df["source"].nunique())
col3.metric("Самая свежая", str(df["published"].max())[:16] if not df.empty else "-")
col4.metric("Самая старая", str(df["published"].min())[:16] if not df.empty else "-")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Обзор", "Ключевые слова", "Тренды по дням", "Поиск по теме"])

with tab1:
    st.subheader("Объём публикаций по источникам")
    src_counts = volume_by_source(df)
    fig = px.bar(x=src_counts.index, y=src_counts.values, labels={"x": "Источник", "y": "Количество"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Последние новости")
    recent = get_recent_items(limit=20)
    for item in recent:
        st.markdown(f"**[{item.source}]** [{item.title}]({item.link})  \n*{item.published}*")
        if item.summary:
            st.caption(item.summary[:300] + "...")

with tab2:
    st.subheader("Топ ключевых слов")
    kws = top_keywords(df, top_n=40)
    if kws:
        kw_df = pd.DataFrame(kws, columns=["keyword", "count"])
        fig = px.bar(kw_df, x="count", y="keyword", orientation="h", title="Частота ключевых слов")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(kw_df, use_container_width=True)
    else:
        st.info("Ключевые слова пока не извлечены.")

with tab3:
    st.subheader(f"Динамика публикаций (последние данные)")
    daily = volume_by_day(df)
    if not daily.empty:
        fig = px.line(daily, x="published", y="count", markers=True, title="Количество новостей по дням")
        st.plotly_chart(fig, use_container_width=True)
    trends = recent_trends(days=days)
    st.write(f"За последние **{trends['period_days']}** дней: **{trends['total']}** публикаций")
    st.write("По источникам:", trends.get("by_source", {}))
    if trends.get("sample_titles"):
        st.subheader("Примеры заголовков")
        for t in trends["sample_titles"]:
            st.write(f"- {t}")

with tab4:
    st.subheader("Динамика упоминаний ключевого слова / темы")
    keyword = st.text_input("Введите слово или фразу (например: выборы, санкции, экономика, Путин)", value="санкции")
    if keyword:
        timeline = keyword_timeline(df, keyword)
        if not timeline.empty:
            fig = px.bar(timeline, x="published", y="count", title=f"Упоминания «{keyword}» по дням")
            st.plotly_chart(fig, use_container_width=True)
            st.write(f"Всего упоминаний в выборке: {timeline['count'].sum()}")
        else:
            st.info("Упоминаний не найдено в текущей выборке.")

st.markdown("---")
st.caption("Система использует только публичные RSS. Не является инструментом слежки. Соблюдайте законодательство и этику.")
