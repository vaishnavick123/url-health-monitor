import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

API_BASE = "http://localhost:8000"

st.title("🌐 URL Health Monitor")

# --- Overall Health Dashboard ---
st.subheader("📊 Overall Health")
health_response = requests.get(f"{API_BASE}/health")
if health_response.status_code == 200:
    health_data = health_response.json()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Monitored URLs", health_data["total_monitored"])
    col2.metric("Currently UP", health_data["current_up"])
    col3.metric("Currently DOWN", health_data["current_down"])

    if health_data["total_monitored"] > 0:
        uptime_df = pd.DataFrame({
            "Status": ["UP", "DOWN"],
            "Count": [health_data["current_up"], health_data["current_down"]],
        })
        fig = px.pie(uptime_df, values="Count", names="Status", title="Current URL Status Distribution")
        st.plotly_chart(fig)

        if health_data["average_uptime_last_24h"] is not None:
            st.metric("Average Uptime (Last 24h)", f"{health_data['average_uptime_last_24h']:.2f}%")
        else:
            st.warning("Not enough data to calculate average uptime in the last 24 hours.")
    else:
        st.info("No URLs being monitored yet.")
else:
    st.error("Failed to fetch overall health data.")

st.markdown("---")


# --- Input Box ---
url_input = st.text_area("Enter URLs (one per line)", height=150)
check_button = st.button("Check URL Health")

if check_button:
    urls = [line.strip() for line in url_input.strip().splitlines() if line.strip()]
    if not urls:
        st.warning("Please enter at least one valid URL.")
    else:
        with st.spinner("Checking URLs..."):
            response = requests.post(f"{API_BASE}/check", json={"urls": urls})
            if response.status_code == 200:
                st.success("Check complete!")
                for result in response.json():
                    status_color = "🟢" if "UP" in result["status"] else "🔴"
                    response_time_str = f"({result['response_time']:.2f} ms)" if result.get("response_time") is not None else ""
                    anomaly_indicator = ""
                    anomaly_message = ""

                    # Display anomaly message if the response_time_anomaly is True
                    if result.get("response_time_anomaly"):
                        anomaly_message = "Frequent ups and downs in status."

                    st.write(f"{status_color} {anomaly_indicator} `{result['url']}` — **{result['status']}** {response_time_str}")
                    if anomaly_message:
                        st.warning(anomaly_message)
            else:
                st.error("Error during URL check!")

st.markdown("---")
st.subheader("🕓 Recent Checks")
history_response = requests.get(f"{API_BASE}/history")
if history_response.status_code == 200:
    history = history_response.json()
    if history:
        history_df = pd.DataFrame(history)
        history_df["checked_at"] = pd.to_datetime(history_df["checked_at"])
        history_df = history_df.sort_values(by="checked_at", ascending=False)

        if "response_time_anomaly" not in history_df.columns:
            history_df["response_time_anomaly"] = False
        else:
            history_df["response_time_anomaly"] = history_df["response_time_anomaly"].fillna(False)

        st.dataframe(history_df[["url", "status", "response_time", "checked_at"]])
    else:
        st.info("No check history available.")
else:
    st.error("Could not fetch history.")

# --- URL Classification Section ---
st.subheader("🏷️ Classify URLs")
classify_input = st.text_area("Enter URLs to classify (one per line)", height=100)
classify_button = st.button("Classify URLs")

if classify_button:
    urls_to_classify = [line.strip() for line in classify_input.strip().splitlines() if line.strip()]
    if urls_to_classify:
        with st.spinner("Classifying URLs..."):
            response = requests.post(f"{API_BASE}/classify", json={"urls": urls_to_classify})
            if response.status_code == 200:
                st.success("Classification complete!")
                classification_results = response.json()
                for result in classification_results:
                    st.write(f"`{result['url']}` — **Category:** `{result['category']}`")
            else:
                st.error("Error during URL classification!")
    else:
        st.warning("Please enter at least one URL to classify.")


st.markdown("---")
st.subheader("⚠️ Recent Downtime Events")
downtime_response = requests.get(f"{API_BASE}/recent_downtime")
if downtime_response.status_code == 200:
    downtime_data = downtime_response.json()
    if downtime_data:
        for event in downtime_data:
            st.error(f"🔴 `{event['url']}` has been down since `{datetime.fromisoformat(event['down_since']).strftime('%Y-%m-%d %H:%M:%S UTC')}`")
    else:
        st.info("No recent downtime events.")
else:
    st.error("Could not fetch recent downtime events.")

# --- Uptime Percentage Display (Example for a specific URL) ---
st.markdown("---")
st.subheader("📈 Uptime Metrics")
url_to_check_uptime = st.text_input("Enter URL to see uptime:", "")
if url_to_check_uptime:
    col1, col2, col3 = st.columns(3)
    for period in ["24h", "7d", "30d"]:
        uptime_response = requests.get(f"{API_BASE}/metrics/{url_to_check_uptime}", params={"period": period})
        if uptime_response.status_code == 200:
            uptime_data = uptime_response.json()
            col_metric = None
            if period == "24h":
                col_metric = col1
            elif period == "7d":
                col_metric = col2
            elif period == "30d":
                col_metric = col3

            if col_metric:
                uptime_value = f"{uptime_data['uptime_percentage']:.2f}%" if uptime_data.get("uptime_percentage") is not None else "N/A"
                col_metric.metric(f"Uptime (Last {period})", uptime_value)
        else:
            st.error(f"Could not fetch uptime for {url_to_check_uptime} ({period})")

st.markdown("---")
st.subheader("🧪 Control Mock URL State for Testing")
st.text("Mock URL - http://localhost:8000/mock-url")
if st.button("Toggle Mock URL Status"):
    res = requests.post(f"{API_BASE}/toggle-mock-url")
    st.success(f"Toggled! New status: {res.json()['new_status']}")

if st.button("Check Mock URL Health"):
    res = requests.get(f"{API_BASE}/mock-url")
    if res.status_code == 200:
        st.success("✅ Mock URL is up!")
    else:
        st.error("💥 Mock URL is down!")
