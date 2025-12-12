import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from io import BytesIO

# -----------------------
# Page config + base CSS
# -----------------------
st.set_page_config(page_title="Traffic & Weather Dashboard", layout="wide", initial_sidebar_state="expanded")

base_css = """
<style>
:root{
  --bg:#ffffff;
  --muted:#6b7280;
  --card:#f8fafc;
  --accent:#ef4444;
}
body { background: var(--bg); }
.header-title { font-size: 36px; font-weight:800; margin:0 0 0 -10px; }
.header-sub { color: var(--muted); margin-top:6px; margin-bottom:18px; margin-left:5px; font-size:14px; }

/* ======= KPI card style (clean + fixed height) ======= */
.kpi {
  background: #ffffff;
  border-radius: 12px;
  padding: 14px;
  margin-bottom:5px;
  box-shadow: 0 6px 18px rgba(15,23,42,0.06);
  border: 1px solid rgba(15,23,42,0.03);
  height: 150px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-sizing: border-box;
}

/* label, value, caption */
.metric-label { font-size:13px; color:var(--muted); margin:0; }
.metric-value { font-size:24px; font-weight:700; color:#111827; margin:0; }
.metric-caption { font-size:12px; color:var(--muted); margin:0; }

/* responsive tweaks */
@media (max-width:900px){
  .header-title { font-size:26px; }
  .metric-value { font-size:20px; }
  .kpi { height: 115px; padding:12px; }
}
@media (max-width:480px){
  .metric-label { font-size:12px; }
  .metric-value { font-size:18px; }
  .metric-caption { font-size:11px; }
  .kpi { height: 105px; }
}
</style>
"""

st.markdown(base_css, unsafe_allow_html=True)

# -------------------------
# Palette and constants
# -------------------------
PALETTE = {"Low": "#10B981", "Medium": "#F59E0B", "High": "#EF4444"}
ICON_TEMP = "🌡️"
ICON_HUM = "💧"
ICON_VEH = "🚗"
ICON_ACC = "⚠️"

# -------------------------
# Load data
# -------------------------
@st.cache_data
def load_data(path="merged_dataset.csv"):
    df = pd.read_csv(path)
    if "date_time" in df.columns:
        df["date_time"] = pd.to_datetime(df["date_time"], errors="coerce")
    else:
        raise KeyError("Missing required column: date_time")
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Failed loading dataset: {e}")
    st.stop()

# ---------------------
# Header + description
# ---------------------
st.markdown('<div>'
            '<div class="header-title">🚦Traffic & Weather</div>'
            '<div class="header-sub">Interactive dashboard for traffic and weather with fast filters and quick insights.</div>'
            '</div>', unsafe_allow_html=True)

# metrics
avg_temp = df["temperature_c"].mean()
avg_humidity = df["humidity"].mean()
total_vehicles = int(df["vehicle_count"].sum())
total_accidents = int(df["accident_count"].sum())

# -------
# KPI Row
# -------
k1, k2, k3, k4 = st.columns([1.3,1.3,1.3,1.3])

with k1:
    st.markdown(f"""
        <div class="kpi">
            <div class="metric-label">{ICON_TEMP} Average Temperature (°C)</div>
            <div class="metric-value">{avg_temp:.1f}</div>
            <div class="metric-caption">Average temperature for the selected period.</div>
        </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
        <div class="kpi">
            <div class="metric-label">{ICON_HUM} Avg Humidity (%)</div>
            <div class="metric-value">{avg_humidity:.0f}</div>
            <div class="metric-caption">Average humidity for the selected period.</div>
        </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
        <div class="kpi">
            <div class="metric-label">{ICON_VEH} Total Vehicles</div>
            <div class="metric-value">{total_vehicles:,}</div>
            <div class="metric-caption">Total vehicle count in the filtered dataset.</div>
        </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
        <div class="kpi">
            <div class="metric-label">{ICON_ACC} Total Accidents</div>
            <div class="metric-value">{total_accidents:,}</div>
            <div class="metric-caption">Total accidents in the selected filters.</div>
        </div>
    """, unsafe_allow_html=True)

st.write("\n")


# ----------------------------
# Sidebar — Controls & Filters
# ----------------------------
st.sidebar.title("Filters")

# --- 1. SEASONS AS CHECKBOXES ---
st.sidebar.markdown("### Seasons")
unique_seasons = df["season"].dropna().unique()
selected_seasons = []

# Loop through available seasons and create a checkbox for each
for s in unique_seasons:
    # Default to True (checked)
    if st.sidebar.checkbox(s, value=True):
        selected_seasons.append(s)

# --- 2. AREA AS DROPDOWN ---
st.sidebar.markdown("### Area Selection")
# Defined list from user requirements
specific_areas = ["Westminster", "Kensington", "Islington", "Camden", "Greenwich", "Chelsea", "Southwark"]
# Add 'All' option to the beginning
area_options = ["All"] + specific_areas

selected_area = st.sidebar.selectbox("Choose Area", area_options)

# --- 3. OTHER FILTERS ---
st.sidebar.markdown("---")
# Date range & aggregation
min_dt, max_dt = df["date_time"].min(), df["date_time"].max()
dt_range = st.sidebar.date_input("Date range", value=[min_dt.date(), max_dt.date()])
agg = st.sidebar.selectbox("Aggregation (for trends)", ["Daily", "Weekly", "Monthly"])

# Advanced
with st.sidebar.expander("Advanced"):
    min_acc, max_acc = int(df["accident_count"].min()), int(df["accident_count"].max())
    acc_threshold = st.slider("Min accidents per record", min_acc, max_acc, min_acc)
    show_grid = st.checkbox("Show grid lines on trends", value=False)
    theme_choice = st.selectbox("Chart Theme", ["plotly_white", "plotly_dark"])
    compact_mode = st.checkbox("Compact mode (less spacing)", value=False)

# -------------------------
# Apply filters
# -------------------------
df_f = df.copy()

# 1. Filter by Seasons (Checkboxes)
if selected_seasons:
    df_f = df_f[df_f["season"].isin(selected_seasons)]
else:
    st.warning("Please select at least one season from the sidebar.")
    st.stop()

# 2. Filter by Area (Dropdown)
if selected_area != "All":
    # This filters the dataframe to only the chosen area
    df_f = df_f[df_f["area"] == selected_area]

# 3. Advanced filters
df_f = df_f[df_f["accident_count"] >= acc_threshold]

# 4. Date range
start = pd.to_datetime(dt_range[0])
end = pd.to_datetime(dt_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
df_f = df_f[(df_f["date_time"] >= start) & (df_f["date_time"] <= end)]

# empty guard
if df_f.empty:
    st.warning("No records match the filters — try widening the date range or removing filters.")
    st.stop()


# -------------------------
# Prepare series + aggregations
# -------------------------
df_time_all = df_f.set_index("date_time").sort_index()
vehicle_daily = df_time_all["vehicle_count"].resample("D").sum().fillna(0)

if agg == "Daily":
    vehicle_agg = vehicle_daily
    delta_period = 7
elif agg == "Weekly":
    vehicle_agg = vehicle_daily.resample("W").sum()
    delta_period = 1
else:
    vehicle_agg = vehicle_daily.resample("M").sum()
    delta_period = 1

def pct_change(s, shift):
    if len(s) <= shift:
        return 0.0
    curr = s.iloc[-1]
    prev = s.iloc[-1-shift]
    if prev == 0:
        return 0.0
    return (curr - prev) / prev * 100



# -------------------------
# Tabs with improved charts
# -------------------------
tab1, tab2, tab3 = st.tabs(["Overview", "Detailed", "Data & Export"])

with tab1:
    st.subheader("Overview — quick glance")
    c1, c2 = st.columns([2,1])

    # Scatter with min/max size and better legend placement
    with c1:
        st.markdown("**Temperature × Avg Speed × Vehicle Count** \n*Bubble size represents vehicle density*")
        size_ref = max(df_f["vehicle_count"].max(), 1)
        fig = px.scatter(df_f, x="temperature_c", y="avg_speed_kmh",
                         size="vehicle_count", size_max=50,
                         color="congestion_level" if "congestion_level" in df_f.columns else None,
                         color_discrete_map=PALETTE,
                         hover_name="area",
                         hover_data={"vehicle_count":True, "date_time":True},
                         labels={"temperature_c":"Temp (°C)", "avg_speed_kmh":"Avg Speed (km/h)"},
                         title="Temperature vs Speed (bubble = vehicles)")
        fig.update_layout(legend=dict(title="Congestion", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                          template=theme_choice)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Weather Conditions")
        cond = df_f["weather_condition"].value_counts().reset_index()
        cond.columns = ["condition","count"]
        fig2 = px.pie(cond, values="count", names="condition", hole=0.55, title="Weather distribution")
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown("<div class='small-note'>Click a slice to filter records for that condition in hover details.</div>", unsafe_allow_html=True)

with tab2:
    st.subheader("Detailed analysis")

    # Heatmap accidents
    df_f = df_f.copy()
    df_f["hour"] = df_f["date_time"].dt.hour
    df_f["weekday"] = df_f["date_time"].dt.day_name()
    heat = df_f.groupby(["weekday","hour"])["accident_count"].sum().reset_index()
    weekdays = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    heat["weekday"] = pd.Categorical(heat["weekday"], categories=weekdays, ordered=True)
    heat = heat.sort_values(["weekday","hour"])
    fig3 = px.density_heatmap(heat, x="hour", y="weekday", z="accident_count",
                              category_orders={"weekday":weekdays}, title="Accidents heatmap (hour vs day)")
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")

    # Trend
    st.subheader("Vehicle trend")
    if agg == "Daily":
        plot_series = df_time_all["vehicle_count"].resample("D").sum().fillna(0)
        roll = 7
    elif agg == "Weekly":
        plot_series = df_time_all["vehicle_count"].resample("W").sum().fillna(0)
        roll = 4
    else:
        plot_series = df_time_all["vehicle_count"].resample("M").sum().fillna(0)
        roll = 3
    rolling = plot_series.rolling(roll).mean()
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=plot_series.index, y=plot_series.values, mode="lines", name="Total"))
    fig4.add_trace(go.Scatter(x=rolling.index, y=rolling.values, mode="lines", name=f"{roll}-period rolling mean"))
    fig4.update_layout(title="Vehicle counts over time", xaxis_title="Date", yaxis_title="Vehicles", template=theme_choice,
                       xaxis=dict(showgrid=show_grid), yaxis=dict(showgrid=show_grid))
    st.plotly_chart(fig4, use_container_width=True)

    # download PNG
    try:
        img = fig4.to_image(format="png", scale=2)
        st.download_button("Download trend image (PNG)", data=img, file_name="vehicle_trend.png", mime="image/png")
    except Exception:
        st.info("To download PNG: install `kaleido` (pip install kaleido).")

    st.markdown("---")

    # Congestion by area stacked
    st.subheader("Congestion by area")
    if "congestion_level" in df_f.columns:
        cong = df_f.groupby(["area","congestion_level"])["vehicle_count"].sum().reset_index()
        fig5 = px.bar(cong, x="area", y="vehicle_count", color="congestion_level", color_discrete_map=PALETTE,
                      title="Vehicles by congestion level per area")
    else:
        cong = df_f.groupby("area")["vehicle_count"].sum().reset_index().sort_values("vehicle_count", ascending=False)
        fig5 = px.bar(cong, x="area", y="vehicle_count", title="Vehicles per area")
    st.plotly_chart(fig5, use_container_width=True)

with tab3:
    st.subheader("Data & Export")
    st.write("Preview of filtered data (first 200 rows):")
    st.dataframe(df_f.head(200))

    csv = df_f.to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered CSV", data=csv, file_name="filtered_traffic_weather.csv", mime="text/csv")

    st.markdown("**Quick insights:**")
    try:
        top_area = df_f.groupby("area")["vehicle_count"].sum().idxmax()
    except Exception:
        top_area = "N/A"
    try:
        worst_cond = df_f.groupby("weather_condition")["accident_count"].sum().idxmax()
    except Exception:
        worst_cond = "N/A"
    st.markdown(f"- Area with highest vehicles: **{top_area}**")
    st.markdown(f"- Weather with most accidents: **{worst_cond}**")

# -------------------------
# Footer tips + accessibility
# -------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("**Tips & Accessibility**")
st.sidebar.markdown("- Select specific seasons to compare performance.")
st.sidebar.markdown("- Use the dropdown to isolate specific London areas.")
st.sidebar.markdown("- Ensure colors are visible in dark mode if your users switch themes.")
