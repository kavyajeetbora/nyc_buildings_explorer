# NYC Buildings Explorer — Dynamic Vector Tiles with DuckDB

A lightweight, modern web dashboard that visualizes New York City building footprints from Overture Maps using dynamic vector tiles generated on-the-fly by DuckDB Spatial. No pre-generated MBTiles/PMTiles — tiles are created in real time from a DuckDB database, filtered server-side, and served directly to MapLibre GL JS.

<video src="docs/Demo.mp4" 
       controls 
       autoplay 
       loop 
       muted 
       style="max-width:60%; border-radius:8px;">
  Your browser does not support the video tag.
</video>

This repository is a practical boilerplate for building fast, filterable, on-demand vector tile dashboards with open geospatial data.

## Features

- Dynamic vector tile serving from DuckDB (no static tile generation)
- Server-side filtering by subtype and class (Overture schema)
- Real-time summary statistics: building count + average height
- Hierarchical dropdown filters (subtype → class)    
- Minimalistic navbar with metric cards
- Single active popup with clean, sentence-case property display
- Reset / center map button (forces north-up + 2D view)
- Zoom restriction to prevent blank map at low zoom levels
- Smooth fly-to animations on reset/center
- Click-to-inspect building properties

## Tech Stack

### Backend

- Python + Flask
- DuckDB (with spatial extension) — query engine & MVT generation
- DuckDB persistent database file (tiles.db)

### Frontend

- MapLibre GL JS v3
- Vanilla JavaScript (no frameworks)
- Font Awesome for icons

### Data

- Overture Maps buildings theme (example release)
- Filtered to an area of interest (e.g., NYC bounding box)
- Geometries transformed to Web Mercator (EPSG:3857)

## Project Structure

```
├── app.py                                  # Flask server + DuckDB logic
├── data/
│   └── tiles.db                            # DuckDB database with t1 table + RTREE index
├── data-engineering/
│   └── 01-generate tiles db from overture.ipynb   # Colab/Jupyter notebook to build tiles.db
├── requirements.txt                        # Python dependencies (e.g., flask, duckdb, mapbox-vector-tile)
├── setup.py                                # project setup / helper install script
└── README.md
```

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/kavyajeetbora/nyc_buildings_explorer.git
cd nyc_buildings_explorer
```

### 2. Data Engineering: generate tiles.db
- Open and run the provided Google Colab notebook to build the DuckDB database (tiles.db) used by the server:
    - Notebook: <a href="https://colab.research.google.com/github/kavyajeetbora/foursquare_ai/blob/master/notebooks/16%20-%20Generate%20tiles%20db%20from%20overture.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>
    - What the notebook does:
        - downloads Overture Maps building data for the area of interest,
        - filters to the project bbox (NYC example),
        - converts geometries to Web Mercator (EPSG:3857),
        - creates a DuckDB table (t1) with the MVT-ready geometry column,
        - creates a spatial (RTREE) index for fast tile queries,
        - writes the persistent DuckDB file as data/tiles.db.
    - How to use it:
        1. Click the Colab badge and run the notebook (Runtime → Run all). The notebook loads and enables DuckDB’s spatial extension and executes the SQL/processing cells.
        2. After the run completes, download the generated file and place it at:
             `data/tiles.db`
        3. Alternatively, run the same SQL locally with DuckDB (install/load the spatial extension, create table, build RTREE index, and WRITE the database file) if you prefer not to use Colab.
- Notes:
    - The server expects the file at `data/tiles.db` and will use the DuckDB spatial extension to generate tiles on demand (no pre-generated MBTiles required).
    - Ensure the notebook completes without errors and the final `tiles.db` contains the `t1` table and its spatial index before starting the server.
- Run the entire notebook (Jupyter / VS Code) and save the output file as:
```text
data\tiles.db
```

### 3. Install dependencies
```powershell
python setup.py setup
```

### 4. Activate the virtual environment (Windows)
```powershell
venv\Scripts\Activate
```

### 5. Run the server
```powershell
python run.py
```

### 6. Open the app
- Visit http://localhost:5000 in your browser to view the application

## Why DuckDB + MVT?

- Zero server setup (embedded DB)
- Extremely fast spatial queries & MVT generation
- No need to pre-generate thousands of tiles
- Easy to add more filters (height range, bbox, etc.)
- Great for prototyping or medium-scale vector tile apps

## Ideal starting points

- Overture Maps dashboards
- Real-time filtered building / POI visualizers
- DuckDB + MapLibre proof-of-concepts
- Teaching dynamic vector tiles without heavy infrastructure

## License

MIT — feel free to fork, modify, and use in your own GIS projects. Contributions welcome.

Made with ❤️ for the open geospatial community.