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
    # Get optional filters from URL query string (?class=...&subtype=...)
    class_filter   = request.args.get('class')
    subtype_filter = request.args.get('subtype')

    # Start building WHERE conditions and parameters
    where_conditions = [
        "ST_Intersects(geometry, ST_TileEnvelope($1, $2, $3))"
    ]
    params = [z, x, y]  # for both ST_TileEnvelope calls

    # Add filters only if provided
    if class_filter:
        where_conditions.append(f"class = '{class_filter}'")
    if subtype_filter:
        where_conditions.append(f"subtype = '{subtype_filter}'")

    # Join all WHERE parts
    where_clause = " AND ".join(where_conditions)

    # Use the same ST_AsMVT pattern that already works for you
    query = f"""
        SELECT ST_AsMVT({{
            "geometry": ST_AsMVTGeom(
                geometry,
                ST_Extent(ST_TileEnvelope($1, $2, $3))
            ),
            'subtype': subtype,
            'class': class,
            'height': height
        }})
        FROM t1 
        WHERE {where_clause}
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

@app.route('/stats')
def get_stats():
    # Get optional filters from query string (?class=...&subtype=...)
    class_filter   = request.args.get('class')
    subtype_filter = request.args.get('subtype')

    # Base query parts
    where_conditions = []
    params = []

    # Add filters only if provided (same logic as tiles, but no geometry)
    if class_filter:
        where_conditions.append("class = ?")
        params.append(class_filter)
    if subtype_filter:
        where_conditions.append("subtype = ?")
        params.append(subtype_filter)

    # If no filters → count everything
    where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

    # Simple aggregate query
    query = f"""
        SELECT 
            COUNT(*) AS count,
            AVG(height) AS avg_height
        FROM t1
        {where_clause}
    """

    with con.cursor() as cur:
        try:
            result = cur.execute(query, params).fetchone()
            if result:
                count, avg_height = result
                response = {
                    "count": int(count) if count is not None else 0,
                    "avg_height": round(float(avg_height), 2) if avg_height is not None else None
                }
            else:
                response = {"count": 0, "avg_height": None}

            return flask.jsonify(response), 200

        except Exception as e:
            print(f"Stats error: {str(e)}")
            import traceback
            traceback.print_exc()
            return flask.jsonify({"error": str(e)}), 500
        
# HTML content for the index page
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no">
    <title>NYC Buildings Explorer</title>
    <script src='https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js'></script>
    <link href='https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css' rel='stylesheet' />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        body, html {
            margin: 0;
            padding: 0;
            height: 100%;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        #map { 
            position: absolute;
            inset: 0;
        }
        .navbar {
            position: absolute;
            top: 12px;
            left: 12px;
            right: 12px;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.96);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.12);
            padding: 10px 16px;
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: nowrap;
        }
        .filter-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .filter-group label {
            font-weight: 600;
            font-size: 13px;
            color: #444;
            margin-right: 6px;
        }
        select {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: white;
            font-size: 13px;
            min-width: 140px;
        }
        .metrics {
            display: flex;
            gap: 24px;
            margin-left: auto;
        }
        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 10px 16px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            text-align: center;
            min-width: 110px;
        }
        .metric-value {
            font-size: 20px;
            font-weight: 700;
            color: #1a73e8;
            line-height: 1.1;
        }
        .metric-label {
            font-size: 11px;
            color: #666;
            margin-top: 4px;
        }
        .apply-btn {
            background: #1a73e8;
            color: white;
            border: none;
            padding: 9px 20px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            white-space: nowrap;
        }
        .apply-btn:hover {
            background: #1557b0;
        }

        .center-btn {
            background: #4b5563;
            color: white;
            border: none;
            padding: 9px 14px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
        }

        .center-btn:hover {
            background: #374151;
        }

        .clear-btn {
            background: #6b7280;           /* neutral gray */
            color: white;
            border: none;
            padding: 9px 16px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            white-space: nowrap;
        }

        .clear-btn:hover {
            background: #4b5563;
        }

    </style>
</head>
<body>
<div id="map"></div>

<div class="navbar">
    <div class="filter-group">
        <label>Subtype</label>
        <select id="subtypeSelect">
            <option value="">All</option>
        </select>
    </div>

    <div class="filter-group">
        <label>Class</label>
        <select id="classSelect">
            <option value="">All</option>
        </select>
    </div>

    <div class="metrics">
        <div class="metric-card">
            <div class="metric-value" id="buildingCount">—</div>
            <div class="metric-label">Buildings</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="avgHeight">—</div>
            <div class="metric-label">Avg Height</div>
        </div>
    </div>
    <button class="center-btn" id="centerBtn" title="Center on NYC">
        <i class="fas fa-crosshairs"></i> Center
    </button>

    <button class="apply-btn" id="applyBtn">Apply</button>
    <button class="clear-btn" id="clearBtn">Clear Filters</button>
    
</div>

<script>
// Hierarchical data: subtype → classes
const classesBySubtype = {
    "residential": ["house", "garage", "detached", "apartments", "semidetached_house", "terrace", "residential", "garages", "dormitory", "static_caravan", "cabin", "bungalow", "hut", "parking", "library"],
    "commercial": ["retail", "commercial", "office", "hotel", "warehouse", "supermarket", "parking", "post_office", "kiosk", "library"],
    "outbuilding": ["shed", "roof", "outbuilding", "carport"],
    "education": ["school", "university", "college", "kindergarten", "library"],
    "industrial": ["industrial", "manufacture"],
    "religious": ["church", "synagogue", "mosque", "chapel", "temple", "cathedral", "religious"],
    "service": ["storage_tank", "service", "toilets", "guardhouse", "boathouse"],
    "transportation": ["parking", "transportation", "train_station", "bridge_structure", "hangar"],
    "civic": ["library", "fire_station", "post_office", "public", "government", "civic"],
    "medical": ["hospital"],
    "agricultural": ["greenhouse", "stable", "barn", "silo"],
    "military": ["military", "bunker"],
    "entertainment": ["sports_centre", "stadium", "grandstand", "pavilion", "sports_hall", "library"]
};

const map = new maplibregl.Map({
    container: 'map',
    style: {
        version: 8,
        sources: {
            'buildings': { type: 'vector', tiles: [`${window.location.origin}/tiles/{z}/{x}/{y}.pbf`], minzoom: 10, maxzoom: 18 },
            'osm': { type: 'raster', tiles: ['https://a.tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: '© OpenStreetMap contributors' }
        },
        layers: [
            { id: 'background', type: 'background', paint: { 'background-color': '#e6f0fa' } },
            { id: 'osm', type: 'raster', source: 'osm', minzoom: 10, maxzoom: 19 },
            { id: 'buildings-fill', type: 'fill', source: 'buildings', 'source-layer': 'layer',
              paint: { 'fill-color': '#4a90e2', 'fill-opacity': 0.65, 'fill-outline-color': '#ffffff' } },
            { id: 'buildings-stroke', type: 'line', source: 'buildings', 'source-layer': 'layer',
              paint: { 'line-color': '#2c5aa0', 'line-width': 0.8 } }
        ]
    },
    center: [-74.0060, 40.7128],
    zoom: 12,
    minZoom: 10,
    maxZoom: 18
});

map.addControl(new maplibregl.NavigationControl());

// Populate subtype dropdown
const subtypeSelect = document.getElementById('subtypeSelect');
Object.keys(classesBySubtype).sort().forEach(key => {
    const opt = document.createElement('option');
    opt.value = key;
    opt.textContent = key.charAt(0).toUpperCase() + key.slice(1);
    subtypeSelect.appendChild(opt);
});

// Update class dropdown on subtype change
document.getElementById('subtypeSelect').addEventListener('change', e => {
    const subtype = e.target.value;
    const classSelect = document.getElementById('classSelect');
    classSelect.innerHTML = '<option value="">All</option>';
    if (subtype && classesBySubtype[subtype]) {
        classesBySubtype[subtype].sort().forEach(cls => {
            const opt = document.createElement('option');
            opt.value = cls;
            opt.textContent = cls.replace(/_/g, ' ');
            classSelect.appendChild(opt);
        });
    }
});

// Apply filters & update stats
document.getElementById('applyBtn').addEventListener('click', async () => {
    const subtypeVal = document.getElementById('subtypeSelect').value;
    const classVal   = document.getElementById('classSelect').value;

    // Build query string
    let qs = [];
    if (subtypeVal) qs.push(`subtype=${encodeURIComponent(subtypeVal)}`);
    if (classVal)   qs.push(`class=${encodeURIComponent(classVal)}`);
    const query = qs.length ? '?' + qs.join('&') : '';

    // Update map tiles
    const tileUrl = `${window.location.origin}/tiles/{z}/{x}/{y}.pbf${query}`;
    const source = map.getSource('buildings');
    if (source) {
        source.setTiles([tileUrl]);
        source._tiles = {};
        map.triggerRepaint();
    }

    // Fetch stats
    try {
        const resp = await fetch(`${window.location.origin}/stats${query}`);
        if (!resp.ok) throw new Error('Stats fetch failed');
        const data = await resp.json();

        document.getElementById('buildingCount').textContent = 
            data.count ? data.count.toLocaleString() : '0';
        document.getElementById('avgHeight').textContent = 
            data.avg_height ? data.avg_height.toFixed(1) + ' m' : '—';
    } catch (err) {
        console.error(err);
        document.getElementById('buildingCount').textContent = 'Error';
        document.getElementById('avgHeight').textContent = '—';
    }
});


// Clear Filters button
// Clear Filters & Center Map button
document.getElementById('clearBtn').addEventListener('click', async () => {
    // 1. Reset dropdowns
    document.getElementById('subtypeSelect').value = '';
    document.getElementById('classSelect').innerHTML = '<option value="">All</option>';

    // 2. Reset map view completely:
    //    - Center on NYC
    //    - Zoom to default level
    //    - North-up (bearing = 0)
    //    - 2D view (pitch = 0)
    map.flyTo({
        center: [-74.0060, 40.7128],
        zoom: 12,
        bearing: 0,           // force north-up
        pitch: 0,             // force 2D (flatten any 3D tilt)
        essential: true,
        duration: 1200        // smooth animation (~1.2 seconds)
    });

    // 3. Load default tiles (no filters)
    const tileUrl = `${window.location.origin}/tiles/{z}/{x}/{y}.pbf`;
    const source = map.getSource('buildings');
    if (source) {
        source.setTiles([tileUrl]);
        source._tiles = {};           // clear cached tiles
        map.triggerRepaint();
    }

    // 4. Refresh global stats
    try {
        const resp = await fetch(`${window.location.origin}/stats`);
        if (resp.ok) {
            const data = await resp.json();
            document.getElementById('buildingCount').textContent = 
                data.count ? data.count.toLocaleString() : '0';
            document.getElementById('avgHeight').textContent = 
                data.avg_height ? data.avg_height.toFixed(1) + ' m' : '—';
        }
    } catch (err) {
        console.error('Clear stats failed', err);
        document.getElementById('buildingCount').textContent = '—';
        document.getElementById('avgHeight').textContent = '—';
    }

    // 5. Close any open popup
    if (currentPopup) {
        currentPopup.remove();
        currentPopup = null;
    }
});

// Global variable to track the current popup (only one allowed)
let currentPopup = null;

// Popup (kept simple)
map.on('click', 'buildings-fill', (e) => {
    // Close any existing popup first
    if (currentPopup) {
        currentPopup.remove();
        currentPopup = null;
    }

    const props = e.features?.[0]?.properties || {};

    // Build modern popup content
    let content = `
        <div style="
            font-family: system-ui, -apple-system, sans-serif;
            min-width: 220px;
            color: #1f2937;
            font-size: 14px;
            line-height: 1.5;
        ">
            <div style="
                font-size: 16px;
                font-weight: 700;
                margin-bottom: 12px;
                color: #111827;
                border-bottom: 1px solid #e5e7eb;
                padding-bottom: 8px;
            ">
                Building Details
            </div>
    `;

    if (Object.keys(props).length === 0) {
        content += '<div style="color: #6b7280; font-style: italic;">No properties available</div>';
    } else {
        for (const [key, value] of Object.entries(props)) {
            const label = key
                .replace(/([A-Z])/g, ' $1')
                .replace(/_/g, ' ')
                .trim()
                .replace(/^./, str => str.toUpperCase());

            let displayValue = value;
            if (key.toLowerCase() === 'height' && !isNaN(value)) {
                displayValue = `${Number(value).toFixed(1)} m`;
            }

            content += `
                <div style="margin: 8px 0; display: flex; justify-content: space-between;">
                    <span style="font-weight: 500; color: #4b5563;">${label}</span>
                    <span style="font-weight: 600; color: #111827;">${displayValue}</span>
                </div>
            `;
        }
    }

    content += '</div>';

    // Create and store new popup
    currentPopup = new maplibregl.Popup({
        closeButton: true,
        closeOnClick: false,
        maxWidth: '280px',
        className: 'modern-popup'  // optional: add custom CSS
    })
        .setLngLat(e.lngLat)
        .setHTML(content)
        .addTo(map);

    // Optional: auto-remove on close
    currentPopup.on('close', () => {
            currentPopup = null;
        });
    });

    map.on('mouseenter', 'buildings-fill', () => map.getCanvas().style.cursor = 'pointer');
    map.on('mouseleave', 'buildings-fill', () => map.getCanvas().style.cursor = '');

    document.getElementById('centerBtn').addEventListener('click', () => {
        map.flyTo({
            center: [-74.0060, 40.7128],
            zoom: 12,
            bearing: 0,
            pitch: 0,
            essential: true,           // smooth animation
            duration: 1200             // nice fly-to duration in ms
        });
    });

    // Lightweight: only close when zoom or drag starts (no heavy loop)
    map.on('zoomstart', () => {
        if (currentPopup) {
            currentPopup.remove();
            currentPopup = null;
        }
    });

    map.on('dragstart', () => {
        if (currentPopup) {
            currentPopup.remove();
            currentPopup = null;
        }
    });

    // Initial load: apply default (no filters)
    document.getElementById('applyBtn').click();

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