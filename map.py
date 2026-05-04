import json
import argparse
from pathlib import Path

import plotly.graph_objects as go

# Central config for map behavior and styling.
CONFIG = {
	"files": {
		"input": "mapping.json",
		"output": "map.svg",
	},
	"layout": {
		"title": "", # "TEF-Health Service Providers in Europe",
		"width": 1200,
		"height": 800,
		"background": "white",
		"margin": {"l": 20, "r": 20, "t": 48, "b": 20},
	},
	"coloring": {
		# Options:
		# - "country_color": use explicit country_color from mapping.json
		# - any other country-level field, e.g. "TEF_member_status": map value using value_colors
		# - None: no country highlighting (blank base map)
		"field": "TEF_member_status", # "country_color",
		"fallback_color": "#efefef",
		"value_colors": {
			"Partner": "#916349",
			"Associate partner": "#C8A47B",
		},
		"country_border_color": "#9b9b9b",
		"country_border_width": 0.7,
	},
	"points": {
		"enabled": False,
		"size": 3,
		"fill": "#111111",
		"stroke": "#1a1a1a",
		"stroke_width": 1.0,
	},
	"map": {
		"scope": "europe",
		"resolution": 50,
		"show_land": True,
		"land_color": "#efefef",
		"show_coastlines": True,
		"coastline_color": "#b5b5b5",
		"coastline_width": 0.6,
		"show_countries": True,
		"country_line_color": "#a8a8a8",
		"country_line_width": 0.5,
		"show_subunits": False,
		"subunit_line_color": "#c7c7c7",
		"subunit_line_width": 0.4,
		"show_lakes": True,
		"lake_color": "#ffffff",
		"show_ocean": True,
		"ocean_color": "#ffffff",
		"show_frame": False,
		"zoom": {
			# Set any value to None to disable that zoom control.
			"center_lat": 54.0,
			"center_lon": 12.0,
			"projection_scale": 1.95,
			"lat_range": None, # [34.0, 71.0],
			"lon_range": None, # [-12.0, 40.0],
		},
	},
}


def parse_args():
	parser = argparse.ArgumentParser(description="Generate SVG map")
	parser.add_argument("--output", default="map.svg", help="Output SVG path")
	parser.add_argument("--mapping", default="mapping.json", help="Input mapping JSON path")
	parser.add_argument(
		"--tef",
		default=None,
		choices=["nodes", "partners", "all"],
		help="Optional TEF mode: nodes, partners, all",
	)
	parser.add_argument("--resolution", type=int, default=50, choices=[50, 110], help="Map resolution")
	return parser.parse_args()


def load_mapping(path):
	with open(path, "r", encoding="utf-8") as infile:
		data = json.load(infile)
	if not isinstance(data, list):
		raise ValueError("mapping.json must contain a list of countries")
	return data


def is_partner_country(country):
	status = str(country.get("TEF_member_status", "")).strip().lower()
	return "partner" in status


def resolve_country_color(country):
	coloring = CONFIG["coloring"]
	field = coloring["field"]

	if field is None:
		return None

	fallback_color = coloring["fallback_color"]
	if field == "country_color":
		return country.get("country_color") or fallback_color

	value = country.get(field)
	if value is None:
		return fallback_color

	return coloring["value_colors"].get(str(value), fallback_color)


def build_country_arrays(countries):
	country_names = []
	color_values = []
	hover_text = []
	provider_count = []
	coloring_field = CONFIG["coloring"]["field"]

	for country in countries:
		country_name = country.get("country")
		country_color = resolve_country_color(country)
		providers = country.get("providers", [])
		if not country_name:
			continue
		if coloring_field is not None and not country_color:
			continue
		country_names.append(country_name)
		color_values.append(country_color)
		provider_count.append(len(providers))

		hover_suffix = f"{len(providers)} providers"
		if coloring_field and coloring_field != "country_color":
			hover_suffix += f", {coloring_field}={country.get(coloring_field)}"
		hover_text.append(f"{country_name}: {hover_suffix}")

	if CONFIG["coloring"]["field"] is not None and not country_names:
		raise ValueError("No countries with both country and country_color found")
	return country_names, color_values, provider_count, hover_text


def build_provider_arrays(countries, partner_only=False):
	lats = []
	lons = []
	texts = []
	for country in countries:
		if partner_only and not is_partner_country(country):
			continue
		for provider in country.get("providers", []):
			coords = provider.get("coordinates", {})
			lat = coords.get("latitude")
			lon = coords.get("longitude")
			if lat is None or lon is None:
				continue
			lats.append(float(lat))
			lons.append(float(lon))
			texts.append(f"{provider.get('name', 'Provider')} ({provider.get('city', 'Unknown city')})")
	return lats, lons, texts


def build_svg(countries, output_path, tef_mode=None):
	country_names, color_values, provider_count, hover_text = build_country_arrays(countries)
	fig = go.Figure()

	# Keep a geo subplot alive even when both coloring and points are disabled.
	fig.add_trace(
		go.Scattergeo(
			lat=[0.0],
			lon=[0.0],
			mode="markers",
			hoverinfo="skip",
			marker={"size": 1, "color": "rgba(0,0,0,0)"},
			showlegend=False,
		)
	)

	if CONFIG["coloring"]["field"] is not None:
		for country_name, country_color, count, hover in zip(country_names, color_values, provider_count, hover_text):
			fig.add_trace(
				go.Choropleth(
					locationmode="country names",
					locations=[country_name],
					z=[count],
					text=[hover],
					hovertemplate="%{text}<extra></extra>",
					colorscale=[[0.0, country_color], [1.0, country_color]],
					marker_line_color=CONFIG["coloring"]["country_border_color"],
					marker_line_width=CONFIG["coloring"]["country_border_width"],
					showscale=False,
				)
			)

	partner_points_only = tef_mode in {"partners", "all"}
	lats, lons, texts = build_provider_arrays(countries, partner_only=partner_points_only)
	if CONFIG["points"]["enabled"] and lats:
		point_color = CONFIG["points"]["fill"]
		if tef_mode in {"partners", "all"}:
			point_color = CONFIG["coloring"]["value_colors"].get("Partner", point_color)
		fig.add_trace(
			go.Scattergeo(
				lat=lats,
				lon=lons,
				mode="markers",
				text=texts,
				hovertemplate="%{text}<extra></extra>",
				marker={
					"size": CONFIG["points"]["size"],
					"color": point_color,
					"line": {
						"color": CONFIG["points"]["stroke"],
						"width": CONFIG["points"]["stroke_width"],
					},
				},
				showlegend=False,
			)
		)

	zoom = CONFIG["map"]["zoom"]
	geo_updates = {
		"scope": CONFIG["map"]["scope"],
		"resolution": CONFIG["map"]["resolution"],
		"showland": CONFIG["map"]["show_land"],
		"landcolor": CONFIG["map"]["land_color"],
		"showcountries": CONFIG["map"]["show_countries"],
		"countrycolor": CONFIG["map"]["country_line_color"],
		"countrywidth": CONFIG["map"]["country_line_width"],
		"showcoastlines": CONFIG["map"]["show_coastlines"],
		"coastlinecolor": CONFIG["map"]["coastline_color"],
		"coastlinewidth": CONFIG["map"]["coastline_width"],
		"showsubunits": CONFIG["map"]["show_subunits"],
		"subunitcolor": CONFIG["map"]["subunit_line_color"],
		"subunitwidth": CONFIG["map"]["subunit_line_width"],
		"showlakes": CONFIG["map"]["show_lakes"],
		"lakecolor": CONFIG["map"]["lake_color"],
		"showocean": CONFIG["map"]["show_ocean"],
		"oceancolor": CONFIG["map"]["ocean_color"],
		"showframe": CONFIG["map"]["show_frame"],
		"bgcolor": CONFIG["layout"]["background"],
	}
	if zoom["center_lat"] is not None and zoom["center_lon"] is not None:
		geo_updates["center"] = {"lat": zoom["center_lat"], "lon": zoom["center_lon"]}
	if zoom["projection_scale"] is not None:
		geo_updates["projection_scale"] = zoom["projection_scale"]
	if zoom["lat_range"] is not None:
		geo_updates["lataxis_range"] = zoom["lat_range"]
	if zoom["lon_range"] is not None:
		geo_updates["lonaxis_range"] = zoom["lon_range"]

	fig.update_geos(
		**geo_updates,
	)
	fig.update_layout(
		title_text=CONFIG["layout"]["title"],
		paper_bgcolor=CONFIG["layout"]["background"],
		plot_bgcolor=CONFIG["layout"]["background"],
		margin=CONFIG["layout"]["margin"],
		showlegend=False,
	)

	output = Path(output_path)
	fig.write_image(
		str(output),
		format="svg",
		width=CONFIG["layout"]["width"],
		height=CONFIG["layout"]["height"],
	)


def main():
	args = parse_args()
	tef_mode = args.tef

	CONFIG["files"]["input"] = args.mapping
	CONFIG["files"]["output"] = args.output
	CONFIG["map"]["resolution"] = args.resolution

	if tef_mode == "nodes":
		CONFIG["coloring"]["field"] = "TEF_member_status"
		CONFIG["points"]["enabled"] = False
	elif tef_mode == "partners":
		CONFIG["coloring"]["field"] = None
		CONFIG["points"]["enabled"] = True
	elif tef_mode == "all":
		CONFIG["coloring"]["field"] = "TEF_member_status"
		CONFIG["points"]["enabled"] = True
	else:
		CONFIG["coloring"]["field"] = None
		CONFIG["points"]["enabled"] = False

	countries = load_mapping(CONFIG["files"]["input"])
	build_svg(countries, CONFIG["files"]["output"], tef_mode=tef_mode)


if __name__ == "__main__":
	main()
