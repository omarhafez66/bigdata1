# streamlit_dashboard_ux_v2_en.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from io import BytesIO

# -------------------------
# Requirements
# -------------------------
# pip install streamlit pandas plotly kaleido

# -------------------------
# Page config + base CSS
# -------------------------
st.set_page_config(page_title="Traffic & Weather — UX v2 (EN)", layout="wide", initial_sidebar_state="expanded")

base_css = """
<style>
:root{
  --bg:#ffffff;
  --muted:#6b7280;
  --card:#f8fafc;
  --accent:#ef4444;
}
body { background: var(--bg); }
.header-title { font-size: 34px; font-weight:800; margin:0; }
.header-sub { color: var(--muted); margin-top:6px; margin-bottom:18px; font-size:14px; }
.kpi { padding: 14px; border-radius: 12px; background: #ffffff; box-shadow: 0 6px 18px rgba(15,23,42,0.06); }
.metric-label {font-size:13px; color:var(--muted); margin-bottom:6px;}
.metric-value {font-size:26px; font-weight:700; color:#111827;}
.metric-caption {font-size:12px; color:var(--muted); margin-top:6px;}
.metric-delta {font-size:13px; margin-top:8px; display:inline-block; padding:5px 10px; border-radius:999px;}
.delta-up { background: rgba(16,185,129,0.12); color:#059669; }
.delta-down { background: rgba(239,68,68,0.12); color:#dc2626; }
.kpi-row { gap:16px; }
.small-note { font-size:13px; color:var(--muted); }
.legend-box { display:inline-block; padding:6px 10px; border-radius:6px; margin-right:8px; font-size:13px; background:#f3f4f6; color:#111827;}
@media (max-width:900px){
  .header-title { font-size:26px; }
  .metric-value { font-size:20px; }
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
# Load data (update path)
# -------------------------
@st.cache_data
def load_data(path=r"B:\Collage Assigments\Big Data\Project\project\merged_dataset.csv"):
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

# -------------------------
# Sidebar — Controls & Filters
# -------------------------
st.sidebar.title("Controls")
city = st.sidebar.selectbox("City", options=np.append(["All"], df["city"].dropna().unique()), index=0)
season = st.sidebar.multiselect("Season", options=df["season"].dropna().unique(), default=df["season"].dropna().unique())

# Area search + Top-N selector
st.sidebar.markdown("### Area filter")
area_search = st.sidebar.text_input("Search area (type to filter)")
top_n = st.sidebar.slider("Show Top N areas by vehicle count (0 = all)", 0, 50, 0)

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
if city != "All":
    df_f = df_f[df_f["city"] == city]
if season:
    df_f = df_f[df_f["season"].isin(season)]

# area search
if area_search:
    df_f = df_f[df_f["area"].str.contains(area_search, case=False, na=False)]

# top-N
if top_n > 0:
    top_areas = df_f.groupby("area")["vehicle_count"].sum().nlargest(top_n).index
    df_f = df_f[df_f["area"].isin(top_areas)]

# advanced filters
df_f = df_f[df_f["accident_count"] >= acc_threshold]

# date range
start = pd.to_datetime(dt_range[0])
end = pd.to_datetime(dt_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
df_f = df_f[(df_f["date_time"] >= start) & (df_f["date_time"] <= end)]

# empty guard
if df_f.empty:
    st.warning("No records match the filters — try widening the date range or removing filters.")
    st.stop()

# -------------------------
# Header + description
# -------------------------
colh1, colh2 = st.columns([9,3])
with colh1:
    st.markdown('<div style="display:flex;align-items:center;gap:14px;">'
                '<div style="font-size:34px;">🚦</div>'
                '<div><div class="header-title">Traffic & Weather — UX v2</div>'
                '<div class="header-sub">Interactive dashboard for traffic and weather with fast filters and quick insights.</div></div>'
                '</div>', unsafe_allow_html=True)
with colh2:
    st.markdown('<div style="text-align:right;">'
                '<div class="legend-box">Legend</div><div class="small-note">Colors = congestion level</div>'
                '</div>', unsafe_allow_html=True)

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

# metrics
avg_temp = df_f["temperature_c"].mean()
avg_humidity = df_f["humidity"].mean()
total_vehicles = int(df_f["vehicle_count"].sum())
total_accidents = int(df_f["accident_count"].sum())
vehicle_pct = pct_change(vehicle_agg, delta_period)
acc_series = df_time_all["accident_count"].resample("D").sum().fillna(0)
if agg == "Daily":
    acc_agg = acc_series
    acc_shift = 7
elif agg == "Weekly":
    acc_agg = acc_series.resample("W").sum()
    acc_shift = 1
else:
    acc_agg = acc_series.resample("M").sum()
    acc_shift = 1
acc_pct = pct_change(acc_agg, acc_shift)

def delta_html(pct):
    cls = "delta-up" if pct >= 0 else "delta-down"
    arrow = "▲" if pct >= 0 else "▼"
    return f'<span class="metric-delta {cls}">{arrow} {abs(pct):.1f}%</span>'

# -------------------------
# KPI Row (improved)
# -------------------------
k1, k2, k3, k4 = st.columns([1.7,1.3,1.3,1.3])
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
            <div class="metric-caption">Average humidity to help explain visibility and road conditions.</div>
        </div>
    """, unsafe_allow_html=True)
with k3:
    st.markdown(f"""
        <div class="kpi">
            <div class="metric-label">{ICON_VEH} Total Vehicles</div>
            <div class="metric-value">{total_vehicles:,}</div>
            {delta_html(vehicle_pct)}
            <div class="metric-caption">Total vehicle count in the filtered dataset.</div>
        </div>
    """, unsafe_allow_html=True)
with k4:
    st.markdown(f"""
        <div class="kpi">
            <div class="metric-label">{ICON_ACC} Total Accidents</div>
            <div class="metric-value">{total_accidents:,}</div>
            {delta_html(acc_pct)}
            <div class="metric-caption">Total accidents — check Detailed tab for peak times.</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# -------------------------
# Tabs with improved charts
# -------------------------
tab1, tab2, tab3 = st.tabs(["Overview", "Detailed", "Data & Export"])

with tab1:
    st.subheader("Overview — quick glance")
    c1, c2 = st.columns([2,1])

    # Scatter with min/max size and better legend placement
    with c1:
        st.markdown("**Temperature × Avg Speed × Vehicle Count**  \n*Bubble size represents vehicle density*")
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
st.sidebar.markdown("- Use the search box to filter areas quickly.")
st.sidebar.markdown("- Ensure colors are visible in dark mode if your users switch themes.")
st.sidebar.markdown("- Use Top-N to focus on the most important areas.")

# End of dashboard
