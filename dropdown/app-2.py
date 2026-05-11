"""
Databricks Catalog Explorer - Streamlit App
3 cascading dropdowns: Catalog -> Schemas (multi) -> Tables (multi)
Real-time refresh button on top.
"""

import os
import streamlit as st
import pandas as pd
from databricks import sql

# ============================================================
# Page config
# ============================================================
st.set_page_config(
    page_title="Databricks Catalog Explorer",
    page_icon="🗂️",
    layout="wide",
)

# ============================================================
# Credentials (from Streamlit secrets or env vars)
# ============================================================
HOST = st.secrets.get("DBX_HOST", os.getenv("DBX_HOST", ""))
HTTP_PATH = st.secrets.get("DBX_HTTP_PATH", os.getenv("DBX_HTTP_PATH", ""))
TOKEN = st.secrets.get("DBX_TOKEN", os.getenv("DBX_TOKEN", ""))

if not all([HOST, HTTP_PATH, TOKEN]):
    st.error("❌ Missing Databricks credentials. Set DBX_HOST, DBX_HTTP_PATH, DBX_TOKEN in Streamlit secrets.")
    st.stop()


# ============================================================
# Connection helper
# ============================================================
def get_connection():
    return sql.connect(
        server_hostname=HOST,
        http_path=HTTP_PATH,
        access_token=TOKEN,
    )


# ============================================================
# Cached fetch functions (30s TTL = near real-time)
# ============================================================
@st.cache_data(ttl=30, show_spinner=False)
def fetch_catalogs():
    """Return list of all catalogs."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SHOW CATALOGS")
            rows = cur.fetchall()
        return sorted([r[0] for r in rows])
    except Exception as e:
        st.error(f"Error fetching catalogs: {e}")
        return []


@st.cache_data(ttl=30, show_spinner=False)
def fetch_schemas(catalog: str):
    """Return list of schemas in a given catalog."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SHOW SCHEMAS IN `{catalog}`")
            rows = cur.fetchall()
        # SHOW SCHEMAS returns columns: databaseName
        schemas = [r[0] for r in rows]
        # Remove system/information_schema noise but keep if user wants
        return sorted(schemas)
    except Exception as e:
        st.error(f"Error fetching schemas for `{catalog}`: {e}")
        return []


@st.cache_data(ttl=30, show_spinner=False)
def fetch_tables(catalog: str, schema: str):
    """Return DataFrame of tables in catalog.schema."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SHOW TABLES IN `{catalog}`.`{schema}`")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        df = pd.DataFrame(rows, columns=cols)
        if not df.empty:
            df.insert(0, "catalog", catalog)
        return df
    except Exception as e:
        st.error(f"Error fetching tables for `{catalog}`.`{schema}`: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_table_details(catalog: str, schema: str, table: str):
    """Return DataFrame with column info for a table."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"DESCRIBE TABLE `{catalog}`.`{schema}`.`{table}`")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        st.error(f"Error describing `{catalog}`.`{schema}`.`{table}`: {e}")
        return pd.DataFrame()


# ============================================================
# UI
# ============================================================
st.title("🗂️ Databricks Catalog Explorer")
st.caption("Real-time view of Unity Catalog · auto-refresh every 30s")

# --- Top refresh bar ---
top_l, top_r = st.columns([1, 5])
with top_l:
    if st.button("🔄 Refresh", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
with top_r:
    st.info("Click **Refresh** to fetch the latest catalogs / schemas / tables from Databricks.")

st.divider()

# --- Box 1: Catalog (single select) ---
st.subheader("1️⃣ Select Catalog")
catalogs = fetch_catalogs()

if not catalogs:
    st.warning("No catalogs found.")
    st.stop()

selected_catalog = st.selectbox(
    "Catalog",
    options=catalogs,
    index=0,
    key="catalog_select",
)

# --- Box 2: Schemas (multi-select) ---
st.subheader("2️⃣ Select Schema(s)")
schemas = fetch_schemas(selected_catalog) if selected_catalog else []

selected_schemas = st.multiselect(
    "Schemas (one or more)",
    options=schemas,
    default=schemas[:1] if schemas else [],
    key="schema_select",
    placeholder="Choose one or more schemas",
)

# --- Box 3: Tables (multi-select, combined from all selected schemas) ---
st.subheader("3️⃣ Select Table(s)")

all_tables_df = pd.DataFrame()
table_options = []

if selected_schemas:
    frames = []
    for sch in selected_schemas:
        df = fetch_tables(selected_catalog, sch)
        if not df.empty:
            frames.append(df)
    if frames:
        all_tables_df = pd.concat(frames, ignore_index=True)
        # Display format: schema.table for clarity when multiple schemas selected
        name_col = "tableName" if "tableName" in all_tables_df.columns else all_tables_df.columns[2]
        db_col = "database" if "database" in all_tables_df.columns else all_tables_df.columns[1]
        table_options = [
            f"{row[db_col]}.{row[name_col]}"
            for _, row in all_tables_df.iterrows()
        ]
        table_options = sorted(set(table_options))

selected_tables = st.multiselect(
    "Tables (one or more)",
    options=table_options,
    key="table_select",
    placeholder="Choose one or more tables",
)

st.divider()

# ============================================================
# Results
# ============================================================
if selected_tables:
    st.subheader("📋 Selected Tables — Details")
    for full_name in selected_tables:
        schema_name, table_name = full_name.split(".", 1)
        with st.expander(f"📄 `{selected_catalog}.{schema_name}.{table_name}`", expanded=False):
            details_df = fetch_table_details(selected_catalog, schema_name, table_name)
            if not details_df.empty:
                st.dataframe(details_df, use_container_width=True, hide_index=True)
            else:
                st.info("No column info available.")
elif selected_schemas and not all_tables_df.empty:
    st.subheader(f"📋 All Tables in selected schema(s)")
    st.dataframe(all_tables_df, use_container_width=True, hide_index=True)
else:
    st.info("👆 Select a catalog, schema(s), and table(s) to view details.")

# ============================================================
# Footer
# ============================================================
st.divider()
with st.expander("ℹ️ About this app"):
    st.markdown(
        """
        - **Catalog** dropdown lists all catalogs you have access to.
        - **Schema** is a multi-select — choose one or many.
        - **Table** is a multi-select — choose one or many tables from the chosen schemas.
        - Click **🔄 Refresh** at the top to see newly created catalogs / schemas / tables.
        - Cached for 30 seconds for performance; refresh forces immediate re-fetch.
        """
    )
