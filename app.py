import os
import json
import time
import random
import colorsys
import asyncio
import aiohttp
import feedparser
import plotly.graph_objects as go
from flask import Flask, render_template_string, request, abort

app = Flask(__name__)

# Set a secret token for cache updates (change this to a strong random value!)
UPDATE_TOKEN = os.environ.get("UPDATE_TOKEN", "changeme123")

def fetch_trend_sync(state_code):
    import requests
    url = f"https://trends.google.com/trending/rss?geo=US-{state_code}"
    for _ in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(response.text)
            if feed.entries:
                return state_code, feed.entries[0].title
        except Exception as e:
            pass
        time.sleep(3)
    return state_code, "No data"

def get_all_trends_sync():
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_trend_sync, state_coords.keys()))
    return dict(results)




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

label_offsets = {
    "RI": (3.5, 0), "CT": (3.2, -1), "NJ": (3.5, -0.3),
    "DE": (3.5, -1), "MD": (3.2, -1.5), "MA": (3.2, 0.5),
    "VT": (-3.2, 2.2), "NH": (-1.5, 2.8)
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

CACHE_FILE = "trends_cache.json"
CACHE_EXPIRY = 600  # 10 minutes

def generate_colors(n):
    hues = [i / n for i in range(n)]
    random.shuffle(hues)
    colors = []
    for h in hues:
        r, g, b = colorsys.hls_to_rgb(h, random.uniform(0.5, 1.0), random.uniform(0.7, 1.0))
        colors.append(f'rgb({int(r*255)}, {int(g*255)}, {int(b*255)})')
    return colors
@app.route("/")
def index():
    # Only read from cache, never fetch trends here
    state_trends = None
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        # Accept cache even if slightly old, but warn if very old
        state_trends = data.get("trends")
        cache_age = time.time() - data.get("timestamp", 0)
    else:
        cache_age = None

        if not state_trends:
            return "<h2>Sorry, no trend data is available. Please try again later.</h2>"

    normalized_trends = {code: trend.strip() if trend.strip() else "No data" for code, trend in state_trends.items()}
    state_trends = normalized_trends

    unique_trends = sorted({t for t in state_trends.values() if t != "No data"})
    unique_trends.append("No data")

    colors = generate_colors(len(unique_trends) - 1)
    colors.append("rgb(200,200,200)")

    colorscale = []
    n = len(colors)
    for i, color in enumerate(colors):
        fraction = i / (n - 1)
        colorscale.append([fraction, color])
        colorscale.append([min(fraction + 0.00001, 1), color])

    z_values = [unique_trends.index(state_trends[code]) for code in state_trends]

    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        locations=list(state_trends.keys()),
        z=z_values,
        locationmode='USA-states',
        colorscale=colorscale,
        zmin=0,
        zmax=n-1,
        showscale=False,
        hovertext=[f"{code}: {state_trends[code]}" for code in state_trends],
        hoverinfo='text'  # Tooltips enabled on the map
    ))

    for code, trend in state_trends.items():
        lat, lon = state_coords[code]
        label = trend if len(trend) <= 14 else trend[:14] + "…"

        hover = 'skip'  # Disable tooltip on text labels
        if code in label_offsets:
            lon_offset, lat_offset = label_offsets[code]
            line_lon = lon + lon_offset
            line_lat = lat + lat_offset
            text_lon = line_lon + (0.3 if lon_offset > 0 else -0.3)
            text_lat = line_lat + (0.2 if lat_offset > 0 else -0.2)

            fig.add_trace(go.Scattergeo(
                lon=[lon, line_lon],
                lat=[lat, line_lat],
                mode='lines',
                line=dict(width=1, color='black'),
                hoverinfo='none'
            ))

            fig.add_trace(go.Scattergeo(
                lon=[text_lon], lat=[text_lat],
                text=[f"<span class='clickable-text'>{label}</span>"],
                mode='text',
                hoverinfo=hover,
                textfont=dict(size=11, color='black', family="Arial Black"),
                customdata=[trend]
            ))
        else:
            fig.add_trace(go.Scattergeo(
                lon=[lon], lat=[lat],
                text=[f"<span class='clickable-text'>{label}</span>"],
                mode='text',
                hoverinfo=hover,
                textfont=dict(size=11, color='black', family="Arial Black"),
                customdata=[trend]
            ))

    fig.update_layout(
        geo=dict(scope='usa', bgcolor='white'),
        title_text='What is America googling right now? (updated every 10 minutes)',
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor='white',
        plot_bgcolor='white',
        showlegend=False
    )

    graph_html = fig.to_html(full_html=False)
    # Inject CSS + JS for interactivity
    graph_html += (
        """
        <style>
        .clickable-text { cursor: pointer; text-decoration: underline; }
        </style>
        <script src=\"https://cdn.plot.ly/plotly-latest.min.js\"></script>
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            var plot = document.querySelector('.js-plotly-plot');
            plot.on('plotly_click', function(data) {
                if (data.points && data.points[0] && data.points[0].customdata) {
                    var trend = data.points[0].customdata;
                    if (trend && trend !== 'No data') {
                        window.open('https://www.google.com/search?q=' + encodeURIComponent(trend), '_blank');
                    }
                }
            });
        });
        </script>
        """
    )

    html_template = """
    <html>
    <head><title>US Google Trends by State</title></head>
    <body>
    {{ graph|safe }}
    </body>
    </html>
    """

    return render_template_string(html_template, graph=graph_html)

@app.route("/update_cache", methods=["POST"])
def update_cache_endpoint():
    token = request.args.get("token")
    if token != UPDATE_TOKEN:
        abort(403)
    print("Writing cache to:", os.path.abspath(CACHE_FILE))  # Debug print for Render logs
    state_trends = get_all_trends_sync()
    with open(CACHE_FILE, "w") as f:
        json.dump({"timestamp": time.time(), "trends": state_trends}, f)
    return {"status": "ok", "updated": True}

if __name__ == "__main__":
    app.run()
