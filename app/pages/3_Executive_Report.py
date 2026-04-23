import sys
from pathlib import Path

# Bootstrap: ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.cris.ui.dashboard_data import load_dashboard_bundle
from src.cris.ui.styles import inject_global_styles

st.set_page_config(page_title="CRIS | Executive Report", layout="wide")
inject_global_styles()

st.title("Executive Intelligence Report")
st.caption("Automated summary, crime distribution, and key tactical insights derived from processed FIRs.")

bundle = load_dashboard_bundle(limit=100)
feature_df = pd.DataFrame(bundle["feature_rows"])
hotspots = {key: pd.DataFrame(value) for key, value in bundle["hotspots"].items()}
entity_df = pd.DataFrame(bundle["entity_frequency"])
confidence_df = pd.DataFrame(bundle["confidence"])

if feature_df.empty:
    st.warning("No data available to generate a report. Please upload and parse FIRs first.")
    st.stop()

# -----------------------------------------------------------------------------
# 1. Automated Executive Summary Generation
# -----------------------------------------------------------------------------
st.markdown("## 1. Executive Summary")

total_cases = len(feature_df)
most_common_crime = hotspots["crime_type"].iloc[0]["crime_type"] if not hotspots["crime_type"].empty else "Unknown"
most_common_crime_count = hotspots["crime_type"].iloc[0]["count"] if not hotspots["crime_type"].empty else 0
top_district = hotspots["district"].iloc[0]["district"] if not hotspots["district"].empty else "Unknown"
top_district_count = hotspots["district"].iloc[0]["count"] if not hotspots["district"].empty else 0

top_entity = entity_df.iloc[0]["entity"] if not entity_df.empty else "None"
top_entity_count = entity_df.iloc[0]["count"] if not entity_df.empty else 0

avg_confidence = confidence_df["parser_confidence"].mean() * 100 if not confidence_df.empty else 0.0

summary_text = f"""
Based on the analysis of **{total_cases}** processed FIR documents, the system has identified **{most_common_crime.upper()}** as the dominant crime category, accounting for **{most_common_crime_count}** incidents. 
The highest concentration of criminal activity is reported in the **{top_district.upper()}** district, which has registered **{top_district_count}** recent cases.

**Intelligence Highlights:**
- **Primary Subject of Interest:** The entity '**{top_entity}**' appears in **{top_entity_count}** separate incident narratives, suggesting a potential repeat offender or central figure in ongoing investigations.
- **Data Quality:** The automated pipeline extracted structured features with an average confidence score of **{avg_confidence:.1f}%**, utilizing deep-learning NER and baseline OCR validation.

**Actionable Recommendation:** Law enforcement resources should prioritize predictive deployments in **{top_district}** focusing on **{most_common_crime}** countermeasures.
"""

st.info(summary_text)

# -----------------------------------------------------------------------------
# 2. Visual Analytics & Distributions
# -----------------------------------------------------------------------------
st.markdown("## 2. Statistical Distributions")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Crime Category Breakdown")
    if not hotspots["crime_type"].empty:
        fig_crime = px.pie(
            hotspots["crime_type"], 
            names="crime_type", 
            values="count", 
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_crime.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_crime, width='stretch')

with col2:
    st.subheader("Geographic Hotspots")
    if not hotspots["district"].empty:
        fig_dist = px.bar(
            hotspots["district"].head(10),
            x="district",
            y="count",
            color="count",
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_dist, width='stretch')

# -----------------------------------------------------------------------------
# 3. Target Entities & Accuracy
# -----------------------------------------------------------------------------
st.markdown("## 3. High-Value Targets & Extraction Metrics")

col3, col4 = st.columns(2)

with col3:
    st.subheader("Most Frequent Entities (Accused/Victims)")
    if not entity_df.empty:
        fig_ent = px.bar(
            entity_df.head(8),
            x="count",
            y="entity",
            orientation='h',
            color="count",
            color_continuous_scale="Sunset"
        )
        fig_ent.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_ent, width='stretch')

with col4:
    st.subheader("System Confidence Spread")
    if not confidence_df.empty:
        fig_conf = go.Figure()
        fig_conf.add_trace(go.Box(y=confidence_df["parser_confidence"], name="Parser Output"))
        fig_conf.add_trace(go.Box(y=confidence_df["ocr_confidence"], name="OCR Output"))
        fig_conf.update_layout(yaxis_title="Confidence Score (0.0 - 1.0)", showlegend=False)
        st.plotly_chart(fig_conf, width='stretch')

st.markdown("---")
st.caption("Report generated automatically by the CRIS Analytics Engine.")
