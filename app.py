import duckdb
import flask
from flask import request

# Initialize Flask app
app = flask.Flask(__name__)

# Setup a global DuckDB connection with spatial extension loaded
# Connect to a persistent database file with the geometry data
config = {"allow_unsigned_extensions": "true"}
con = duckdb.connect(r"data\tiles.db", True, config)

# Install spatial from wherever you built it
#con.execute("INSTALL spatial from <some path>")
con.execute("install spatial;")
con.execute("load spatial;")

# Tile endpoint to serve vector tiles
@app.route('/tiles/<int:z>/<int:x>/<int:y>.pbf')
def get_tile(z, x, y):
    
    params = [z, x, y]  # for both ST_TileEnvelope calls

    # Use the same ST_AsMVT pattern, but explicitly name the layer 't1'
    query = f"""
        SELECT ST_AsMVT(
            {{
                "geometry": ST_AsMVTGeom(
                    geometry,
                    ST_Extent(ST_TileEnvelope($1, $2, $3))
                ),
                'name': name
            }},
            't1'  -- <--- THIS IS THE MAGIC FIX 
        )
        FROM t1 
        WHERE ST_Intersects(geometry, ST_TileEnvelope($1, $2, $3))
    """

    with con.cursor() as local_con:
        try:
            tile_blob = local_con.execute(query, params).fetchone()
            tile = tile_blob[0] if tile_blob and tile_blob[0] else b''
            return flask.Response(tile, mimetype='application/x-protobuf')
        except Exception as e:
            # Print to terminal for debugging
            print(f"Tile error at {z}/{x}/{y}: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error generating tile: {str(e)}", 500

# HTML content for the index page
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no">
    <title>India Explorer</title>
    <script src='https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js'></script>
    <link href='https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css' rel='stylesheet' />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        body, html {
            margin: 0;
            padding: 0;
            height: 100%;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #e6f0fa;
        }
        #map { 
            position: absolute;
            inset: 0;
        }
        .controls {
            position: absolute;
            top: 20px;
            right: 20px;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .control-group {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(8px);
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            padding: 8px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
        }
        button {
            width: 36px;
            height: 36px;
            background: #ffffff;
            border: 1px solid #eee;
            border-radius: 8px;
            font-size: 18px;
            color: #333;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        button:hover {
            background: #f8f9fa;
            border-color: #ddd;
            transform: translateY(-1px);
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        #zoomLevel {
            font-size: 11px;
            font-weight: 600;
            color: #666;
            padding: 2px 6px;
            background: #f0f0f0;
            border-radius: 4px;
            min-width: 32px;
            text-align: center;
        }
        .header-badge {
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            padding: 12px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .header-badge i {
            color: #1a73e8;
            font-size: 20px;
        }
        .header-badge h1 {
            margin: 0;
            font-size: 16px;
            font-weight: 700;
            color: #1f2937;
        }
    </style>
</head>
<body>
<div id="map"></div>

<div class="header-badge">
    <i class="fas fa-city"></i>
    <h1>India Explorer</h1>
</div>

<div class="controls">
    <div class="control-group">
        <button id="centerBtn" title="Center on India">
            <i class="fas fa-crosshairs"></i>
        </button>
    </div>
    <div class="control-group">
        <button id="zoomIn" title="Zoom In">+</button>
        <div id="zoomLevel">z 4</div>
        <button id="zoomOut" title="Zoom Out">−</button>
    </div>
</div>

<script>
const map = new maplibregl.Map({
    container: 'map',
    style: {
        version: 8,
        sources: {
            'restaurants': { 
                type: 'vector', 
                tiles: [`${window.location.origin}/tiles/{z}/{x}/{y}.pbf`], 
                minzoom: 4, 
                maxzoom: 18 
            },
            'osm': { 
                type: 'raster', 
                tiles: ['https://a.tile.openstreetmap.org/{z}/{x}/{y}.png'], 
                tileSize: 256, 
                attribution: '© OpenStreetMap contributors' 
            }
        },
        layers: [
            { id: 'background', type: 'background', paint: { 'background-color': '#e6f0fa' } },
            { id: 'osm', type: 'raster', source: 'osm', minzoom: 0, maxzoom: 19 },
            { id: 'restaurants-point', type: 'circle', source: 'restaurants', 'source-layer': 't1',
              paint: { 
                  'circle-color': '#ff4757',
                  'circle-opacity': 0.6,
                  'circle-radius': [
                      'interpolate', ['linear'], ['zoom'],
                      4, 1.5,
                      10, 4,
                      18, 8
                  ]
              } 
            }
        ]
    },
    center: [78.9629, 20.5937],
    zoom: 4,
    minZoom: 2,
    maxZoom: 18
});

map.addControl(new maplibregl.NavigationControl({ showZoom: false }));

let currentPopup = null;

map.on('click', 'restaurants-point', (e) => {
    if (currentPopup) currentPopup.remove();

    const props = e.features?.[0]?.properties || {};
    let content = `
        <div style="font-family: system-ui, sans-serif; min-width: 200px; color: #1f2937; font-size: 13px;">
            <div style="font-weight: 700; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid #eee; font-size: 14px;">
                Restaurant Details
            </div>
    `;

    if (Object.keys(props).length === 0) {
        content += '<div style="color: #6b7280; font-style: italic;">No metadata available</div>';
    } else {
        for (const [key, value] of Object.entries(props)) {
            const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            let displayValue = value;
            
            content += `
                <div style="margin: 6px 0; display: flex; justify-content: space-between; gap: 10px;">
                    <span style="color: #6b7280;">${label}</span>
                    <span style="font-weight: 600;">${displayValue}</span>
                </div>
            `;
        }
    }
    content += '</div>';

    // The event coordinates for a point layer need to be handled slightly differently usually, 
    // but the geometry coordinates work natively if you grab it from the event
    const coordinates = e.features[0].geometry.coordinates.slice();

    // Ensure the popup handles wraps around the date line nicely
    while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
        coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
    }

    currentPopup = new maplibregl.Popup({ closeButton: true, maxWidth: '300px' })
        .setLngLat(coordinates)
        .setHTML(content)
        .addTo(map);
});

map.on('mouseenter', 'restaurants-point', () => map.getCanvas().style.cursor = 'pointer');
map.on('mouseleave', 'restaurants-point', () => map.getCanvas().style.cursor = '');

const zoomLevelDisplay = document.getElementById('zoomLevel');
const updateZoom = () => { zoomLevelDisplay.textContent = `z ${Math.round(map.getZoom())}`; };
map.on('zoom', updateZoom);

document.getElementById('zoomIn').addEventListener('click', () => map.zoomIn());
document.getElementById('zoomOut').addEventListener('click', () => map.zoomOut());
document.getElementById('centerBtn').addEventListener('click', () => {
    map.flyTo({ center: [78.9629, 20.5937], zoom: 4, bearing: 0, pitch: 0, essential: true, duration: 1000 });
});

map.on('zoomstart', () => { if (currentPopup) currentPopup.remove(); });
map.on('dragstart', () => { if (currentPopup) currentPopup.remove(); });
</script>
</body>
</html>
"""

# Serve the static HTML file for the index page
@app.route("/")
def index():
    return flask.Response(INDEX_HTML, mimetype='text/html')

if __name__ == '__main__':
    # Start on localhost
    app.run(debug=True)