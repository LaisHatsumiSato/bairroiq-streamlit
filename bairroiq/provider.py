from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from bairroiq.databricks import DatabricksConfig, DatabricksDataProvider
from bairroiq.sample_data import SampleDataProvider


@st.cache_resource
def get_provider() -> SampleDataProvider | DatabricksDataProvider:
    provider_name = os.getenv("BAIRROIQ_DATA_PROVIDER", "sample").strip().lower()
    if provider_name == "sample":
        return SampleDataProvider()
    if provider_name != "databricks":
        raise ValueError("BAIRROIQ_DATA_PROVIDER deve ser 'sample' ou 'databricks'.")

    secrets = st.secrets if Path(".streamlit/secrets.toml").is_file() else {}
    return DatabricksDataProvider(DatabricksConfig.from_sources(secrets))


@st.cache_data(ttl=300)
def load_metrics() -> pd.DataFrame:
    return get_provider().load_metrics()


@st.cache_data(ttl=300)
def load_history() -> pd.DataFrame:
    return get_provider().load_history()
