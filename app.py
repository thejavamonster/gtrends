import asyncio
import aiohttp
import feedparser
import plotly.graph_objects as go
import plotly.express as px
import random
import streamlit as st
import time

state_coords = {
    "AL": [32.806671, -86.791130], "AK": [61.370716, -152.404419],
    "AZ": [33.729759, -111.431221], "AR": [34.969704, -92.373123],
    "CA": [36.116203, -119.681564], "CO": [39.059811, -105.311104],
    "CT": [41.597782, -72.755371], "DE": [39.318523, -75.507141],
    "FL": [27.766279, -81.686783], "GA": [33.040619, -83.643074],
    "HI": [21.094318, -157.498337], "ID": [44.240459, -114.478828],
    "IL": [40.349457, -88.986137], "IN": [39.849426, -86.258278],
    "IA": [42.011539, -93.210526], "KS": [38.526600, -96.726486],
    "KY": [37.668140, -84.670067], "LA": [31.169546, -91.867805],
    "ME": [44.693947, -69.381927], "MD": [39.063946, -76.802101],
    "MA": [42.230171, -71.530106], "MI": [43.326618, -84.536095],
    "MN": [45.694454, -93.900192], "MS": [32.741646, -89.678696],
    "MO": [38.456085, -92.288368], "MT": [46.921925, -110.454353],
    "NE": [41.125370, -98.268082], "NV": [38.313515, -117.055374],
    "NH": [43.452492, -71.563896], "NJ": [40.298904, -74.521011],
    "NM": [34.840515, -106.248482], "NY": [42.165726, -74.948051],
    "NC": [35.630066, -79.806419], "ND": [47.528912, -99.784012],
    "OH": [40.388783, -82.764915], "OK": [35.565342, -96.928917],
    "OR": [44.572021, -122.070938], "PA": [40.590752, -77.209755],
    "RI": [41.680893, -71.511780], "SC": [33.856892, -80.945007],
    "SD": [44.299782, -99.438828], "TN": [35.747845, -86.692345],
    "TX": [31.054487, -97.563461], "UT": [40.150032, -111.862434],
    "VT": [44.045876, -72.710686], "VA": [37.769337, -78.169968],
    "WA": [47.400902, -121.490494], "WV": [38.491226, -80.954456],
    "WI": [44.268543, -89.616508], "WY": [42.755966, -107.302490]
}

small_states = ["RI", "CT", "DE", "NJ", "MD", "MA", "NH", "VT"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

async def fetch_trend(session, state_code):
    url = f"https://trends.google.com/trending/rss?geo=US-{state_code}"
    for _ in range(3):
        await asyncio.sleep(random.uniform(1.0, 2.0))
        try:
            async with session.get(url, headers=headers) as response:
                text = await response.text()
                feed = feedparser.parse(text)
                if feed.entries:
                    return state_code, feed.entries[0].title
        except:
            pass
    return state_code, "No data"

async def get_all_trends():
    trends = {}
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_trend(session, state) for state in state_coords]
        results = await asyncio.gather(*tasks)
        for code, trend in results:
            trends[code] = trend
    return trends

def generate_map(state_trends):
    unique_trends = list(set(state_trends.values()))
    colors = px.colors.qualitative.Plotly * ((len(unique_trends) // len(px.colors.qualitative.Plotly)) + 1)

    fig = go.Figure()

    fig.add_trace(go.Choropleth(
        locations=list(state_trends.keys()),
        z=[unique_trends.index(state_trends[code]) for code in state_trends],
        locationmode='USA-states',
        colorscale=[[i/(len(unique_trends)-1 if len(unique_trends)>1 else 1), colors[i]] for i in range(len(unique_trends))],
        showscale=False,
        hovertext=[f"{code}: {state_trends[code]}" for code in state_trends],
        hoverinfo='text'
    ))

    for code, trend in state_trends.items():
        lat, lon = state_coords[code]
        label = trend if len(trend) <= 14 else trend[:14] + "…"

        if code in small_states:
            fig.add_annotation(
                x=lon + 2, y=lat + 1,
                xref='x', yref='y',
                text=f"{code}: {label}",
                showarrow=True,
                arrowhead=2,
                ax=lon, ay=lat,
                font=dict(size=10, color="black"),
                bgcolor="white"
            )
        else:
            fig.add_trace(go.Scattergeo(
                lon=[lon], lat=[lat],
                text=label,
                mode='text',
                textfont=dict(size=11, color='black', family="Arial Black")
            ))

    fig.update_layout(
        geo=dict(scope='usa'),
        title_text='US Top Google Trends by State',
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor='white',
        height=800,
        width=1400
    )

    return fig

st.set_page_config(layout="wide")

st.title("US Top Google Trends by State")

status_text = st.empty()

state_trends = {}

try:
    state_trends = asyncio.run(get_all_trends())
except Exception as e:
    status_text.error(f"Failed to fetch trends: {e}")
else:
    status_text.text(f"Last updated: {time.ctime()}")

    fig = generate_map(state_trends)
    st.plotly_chart(fig, use_container_width=True)
