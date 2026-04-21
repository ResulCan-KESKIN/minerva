# db.py — QuantShine DB bağlantısı
import streamlit as st
import psycopg2
import os


@st.cache_resource
def get_conn():
    return psycopg2.connect(
        host=os.environ["EXT_DB_HOST"],
        port=int(os.environ["EXT_DB_PORT"]),
        database=os.environ["EXT_DB_NAME"],
        user=os.environ["EXT_DB_USER"],
        password=os.environ["EXT_DB_PASSWORD"],
    )
