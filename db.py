# db.py — QuantShine DB bağlantısı
import streamlit as st
import psycopg2
import os


@st.cache_resource
def get_conn():
    return psycopg2.connect(
        host=os.environ.get("EXT_DB_HOST", "aws-0-eu-west-1.pooler.supabase.com"),
        port=int(os.environ.get("EXT_DB_PORT", 6543)),
        database=os.environ.get("EXT_DB_NAME", "postgres"),
        user=os.environ.get("EXT_DB_USER", "postgres.ewetkqwkjbmblutbejsh"),
        password=os.environ.get("EXT_DB_PASSWORD", "QuantShine2025.")
    )
