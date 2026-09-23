"""Streamlit dashboard for RF political trends."""

import sys
from pathlib import Path

# Ensure src/ is on path whether launched as streamlit run src/dashboard.py or from bat
_SRC = Path(__file__).resolve().parent
_ROOT = _SRC.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px

from database import init_db, get_recent_items
from analyzer import (
    load_dataframe,
    top_keywords,
    volume_by_day,
    volume_by_source,
    recent_trends,
    keyword_timeline,
    sentiment_stats,
)
from export import export_to_csv, export_to_json
from updater import check_update, apply_update, read_local_version

st.set_page_config(page_title="RF Political Trends Analyzer", layout="wide")

st.title("Анализатор политических тенденций РФ")
st.caption(
    "Только независимые публичные RSS (Meduza, Mediazona, Moscow Times, BBC, DW и др.). "
    "Не госСМИ. Исследовательские цели."
)

try:
    init_db()
except Exception as e:
    st.error(f"Ошибка БД: {e}")
    st.stop()

# Sidebar
st.sidebar.header("Управление")
st.sidebar.caption(f"Версия: {read_local_version()}")

if st.sidebar.button("Собрать новости сейчас", type="primary"):
    with st.spinner("Сбор RSS (нужен интернет; при блокировках — VPN)..."):
        try:
            from collector import collect
            n = collect()
            st.sidebar.success(f"Готово. Новых записей: {n}")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Ошибка сбора: {e}")

days = st.sidebar.slider("Период анализа (дней)", 1, 30, 7)
limit = st.sidebar.number_input("Лимит записей", 100, 10000, 2000)

st.sidebar.markdown("---")
st.sidebar.subheader("Обновление программы")
if st.sidebar.button("Проверить обновления"):
    with st.spinner("Запрос к GitHub..."):
        try:
            available, info = check_update()
            st.session_state["update_info"] = info
            st.session_state["update_available"] = available
        except Exception as e:
            st.sidebar.error(f"Не удалось проверить: {e}")

info = st.session_state.get("update_info")
if info:
    st.sidebar.write(f"Локально: **{info.get('local_version')}**")
    st.sidebar.write(f"На GitHub: **{info.get('remote_version')}** ({info.get('remote_sha')})")
    if info.get("remote_message"):
        st.sidebar.caption(info["remote_message"])
    if st.session_state.get("update_available"):
        st.sidebar.warning("Доступно обновление")
        if st.sidebar.button("Скачать и установить обновление"):
            with st.spinner("Скачивание и установка (data/ не трогаем)..."):
                try:
                    msg = apply_update()
                    st.sidebar.success(msg)
                    st.session_state["update_available"] = False
                except Exception as e:
                    st.sidebar.error(f"Ошибка обновления: {e}")
    else:
        st.sidebar.success("У вас актуальная версия")

st.sidebar.markdown("---")
st.sidebar.subheader("Экспорт")
if st.sidebar.button("Экспорт CSV"):
    try:
        path = export_to_csv(limit=limit)
        st.sidebar.success(f"CSV: {path.name}")
        with open(path, "rb") as f:
            st.sidebar.download_button("Скачать CSV", f, file_name=path.name, mime="text/csv")
    except Exception as e:
        st.sidebar.error(str(e))

if st.sidebar.button("Экспорт JSON"):
    try:
        path = export_to_json(limit=limit)
        st.sidebar.success(f"JSON: {path.name}")
        with open(path, "rb") as f:
            st.sidebar.download_button("Скачать JSON", f, file_name=path.name, mime="application/json")
    except Exception as e:
        st.sidebar.error(str(e))

df = load_dataframe(limit=limit)

if df.empty:
    st.info(
        "База пуста. Нажмите в сайдбаре **«Собрать новости сейчас»**. "
        "Если источники недоступны из РФ — включите VPN и повторите."
    )
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Записей", len(df))
col2.metric("Источников", df["source"].nunique())
col3.metric("Свежая", str(df["published"].max())[:16] if not df.empty else "-")
col4.metric("Старая", str(df["published"].min())[:16] if not df.empty else "-")

sent = sentiment_stats(df)
if sent["total_with_score"] > 0:
    st.metric(
        "Средний sentiment (-1..+1)",
        f"{sent['avg']:.3f}" if sent["avg"] is not None else "n/a",
        help=f"+{sent['positive']} / ~{sent['neutral']} / -{sent['negative']}",
    )

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Обзор", "Ключевые слова", "Тренды по дням", "Поиск по теме", "Sentiment"]
)

with tab1:
    st.subheader("Объём по источникам")
    src_counts = volume_by_source(df)
    fig = px.bar(x=src_counts.index, y=src_counts.values, labels={"x": "Источник", "y": "Количество"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Последние новости")
    recent = get_recent_items(limit=25)
    for item in recent:
        sent_str = f" | sentiment: {item.sentiment_score:.2f}" if item.sentiment_score is not None else ""
        st.markdown(f"**[{item.source}]** [{item.title}]({item.link})  \n*{item.published}{sent_str}*")
        if item.summary:
            st.caption((item.summary[:280] + "...") if len(item.summary or "") > 280 else item.summary)

with tab2:
    st.subheader("Топ ключевых слов")
    kws = top_keywords(df, top_n=40)
    if kws:
        kw_df = pd.DataFrame(kws, columns=["keyword", "count"])
        fig = px.bar(kw_df, x="count", y="keyword", orientation="h")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(kw_df, use_container_width=True)
    else:
        st.info("Ключевые слова пока не извлечены — соберите новости.")

with tab3:
    st.subheader("Динамика публикаций")
    daily = volume_by_day(df)
    if not daily.empty:
        fig = px.line(daily, x="published", y="count", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    trends = recent_trends(days=days)
    st.write(f"За **{trends['period_days']}** дн.: **{trends['total']}** публикаций")
    st.write("По источникам:", trends.get("by_source", {}))
    if trends.get("sample_titles"):
        st.subheader("Примеры заголовков")
        for t in trends["sample_titles"]:
            st.write(f"- {t}")

with tab4:
    keyword = st.text_input("Тема / слово", value="санкции")
    if keyword:
        timeline = keyword_timeline(df, keyword)
        if not timeline.empty:
            fig = px.bar(timeline, x="published", y="count", title=f"«{keyword}»")
            st.plotly_chart(fig, use_container_width=True)
            st.write(f"Всего: {timeline['count'].sum()}")
        else:
            st.info("Упоминаний не найдено.")

with tab5:
    if sent["total_with_score"] == 0:
        st.info("Sentiment выключен в config (enable_sentiment: false) или ещё не посчитан.")
    else:
        pie_df = pd.DataFrame(
            {
                "label": ["Positive", "Neutral", "Negative"],
                "count": [sent["positive"], sent["neutral"], sent["negative"]],
            }
        )
        fig = px.pie(pie_df, values="count", names="label")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("Независимые RSS · не госСМИ · не для слежки · соблюдайте закон и этику.")
