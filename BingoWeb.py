from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import osmnx as ox
import networkx as nx
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-secret-key')

# Load the road network graph once at startup
print("Loading OSM street graph...")
G = ox.graph_from_place("Windhoek, Namibia", network_type="drive")  # use 'drive' network for cars
print("Graph loaded.")

# Load restaurant CSV with fallback encoding
df_raw = pd.read_csv("restaurants.csv", encoding='latin1')

# Convert to GeoDataFrame
df = gpd.GeoDataFrame(
    df_raw,
    geometry=gpd.points_from_xy(df_raw["Longitude"], df_raw["Latitude"]),
    crs="EPSG:4326"
)

# --------------------------
# ROUTES
# --------------------------

# Login page
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "1234":
            session["username"] = username
            return redirect(url_for("game"))
        else:
            return render_template("login.html", error=True)
    return render_template("login.html", error=False)

# Game page - protected route
@app.route("/game")
def game():
    if "username" in session:
        return render_template("Bingog.html")
    else:
        return redirect(url_for("login"))

# Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

# List all themes
@app.route("/themes")
def get_themes():
    themes = df["Theme"].dropna().unique().tolist()
    return jsonify(themes)

# Get restaurants by theme
@app.route("/restaurants")
def get_restaurants():
    theme = request.args.get("theme")
    results = df[df["Theme"] == theme][["Name", "Latitude", "Longitude", "Website / Social Media", "Theme"]]
    results = results.rename(columns={"Website / Social Media": "Link"})
    return jsonify(results.to_dict(orient="records"))

# Get initial route from user to restaurant
@app.route("/route")
def get_route():
    try:
        start = tuple(map(float, request.args.get("start").split(",")))
        end = tuple(map(float, request.args.get("end").split(",")))
        orig = ox.distance.nearest_nodes(G, start[1], start[0])
        dest = ox.distance.nearest_nodes(G, end[1], end[0])
        path = nx.shortest_path(G, orig, dest, weight="length")
        coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in path]
        return jsonify(coords)
    except Exception as e:
        print("Routing error:", e)
        return jsonify([]), 500

# Live route recalculation
@app.route("/recalculate")
def recalculate_route():
    try:
        current = tuple(map(float, request.args.get("current").split(",")))
        destination = tuple(map(float, request.args.get("destination").split(",")))
        orig = ox.distance.nearest_nodes(G, current[1], current[0])
        dest = ox.distance.nearest_nodes(G, destination[1], destination[0])
        path = nx.shortest_path(G, orig, dest, weight="length")
        coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in path]
        return jsonify(coords)
    except Exception as e:
        print("Recalculation error:", e)
        return jsonify([]), 500

# --------------------------
# RUN APP
# --------------------------

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
