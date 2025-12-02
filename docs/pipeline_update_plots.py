import duckdb as db
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import json
import os

import plotly.express as px
from plotly.offline import plot


def pipeline_update_plots():
    tpa = db.read_csv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/TrafficPerAirport.csv")))
    tpt = db.read_csv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/TrafficPerTerritory.csv')))
    airports = db.read_csv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/Airport.csv')))
    airservice = db.read_csv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/AirService.csv')))
    aircraftmov = db.read_csv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/AircraftMovement.csv')))

    max_date_local = db.sql(' \
    SELECT MAX(Month) FROM tpa \
    ').fetchone()[0]

    six_months_ago = max_date_local - relativedelta(months=6)

    create_air_traffic_html(db.sql(f"SELECT AirService, AircraftMovement, Month, a.AirportName AS BaseAirport, a.Latitude AS BaseLatitude, a.Longitude AS BaseLongitude, \
            a2.AirportName AS StopoverAirport, a2.Latitude AS StopoverLatitude, a2.Longitude AS StopoverLongitude, \
            Passengers, Operations, Goods, Mail  \
            FROM tpa t INNER JOIN airports a ON a.AirportId = t.BaseAirportId  \
            INNER JOIN airports a2 ON a2.AirportId = t.StopoverAirportId \
            INNER JOIN airservice USING(AirServiceId)\
            INNER JOIN aircraftmov USING (AircraftMovementId)\
            WHERE Month >= '{six_months_ago.strftime(format="%Y-%m-%d")}'").df(),
            output_file="air_traffic.html", 
            div_id="air_traffic_div")
    
    fifteen_years_ago = max_date_local - relativedelta(years=16)

    create_air_traffic_line_graph(db.sql(f"SELECT Month, a.AirportName AS BaseAirport, \
            a2.AirportName AS StopoverAirport, \
            Passengers, Operations, Goods, Mail  \
            FROM tpa t INNER JOIN airports a ON a.AirportId = t.BaseAirportId  \
            INNER JOIN airports a2 ON a2.AirportId = t.StopoverAirportId \
            WHERE AirServiceId = 0 AND AircraftMovementId = 2 AND Month >= '{fifteen_years_ago.strftime(format="%Y-%m-%d")}'").df())

    predictions = db.read_csv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/predictions/Predictions.csv')))

    predictions = db.sql(f"SELECT * FROM predictions WHERE Month >= '2023-01-01'")

    create_prediction_line_graph(predictions.df())

    one_year_ago = max_date_local - relativedelta(months=12)

    create_airport_bar_chart(db.sql(f"SELECT a1.AirportName,  \
    SUM(Passengers) AS Passengers \
    FROM tpa INNER JOIN airports a1 ON StopoverAirportId = a1.AirportId \
    WHERE AirServiceId = 0 AND AircraftMovementId = 0 AND a1.AirportCode NOT LIKE 'ES_GC%' AND Month >= '{one_year_ago}'\
    GROUP BY a1.AirportName ORDER BY 2 DESC LIMIT 15\
    ").df())
    print("Everything good")


def create_air_traffic_html(df, output_file="air_traffic.html", div_id="air_traffic_div"):
    # Ensure Month is datetime
    df = df.copy()
    df["Month"] = pd.to_datetime(df["Month"])

    # Prepare minimal records list for embedding in HTML/JS
    records = []
    for _, r in df.iterrows():
        records.append({
            "AirService": None if pd.isna(r["AirService"]) else str(r["AirService"]),
            "AircraftMovement": None if pd.isna(r["AircraftMovement"]) else str(r["AircraftMovement"]),
            "Month": r["Month"].strftime("%Y-%m-%d"),
            "BaseAirport": None if pd.isna(r["BaseAirport"]) else str(r["BaseAirport"]),
            "BaseLatitude": None if pd.isna(r["BaseLatitude"]) else float(r["BaseLatitude"]),
            "BaseLongitude": None if pd.isna(r["BaseLongitude"]) else float(r["BaseLongitude"]),
            "StopoverAirport": None if pd.isna(r["StopoverAirport"]) else str(r["StopoverAirport"]),
            "StopoverLatitude": None if pd.isna(r["StopoverLatitude"]) else float(r["StopoverLatitude"]),
            "StopoverLongitude": None if pd.isna(r["StopoverLongitude"]) else float(r["StopoverLongitude"]),
            "Passengers": 0 if pd.isna(r.get("Passengers", 0)) else int(r.get("Passengers", 0)),
            "Operations": 0 if pd.isna(r.get("Operations", 0)) else int(r.get("Operations", 0)),
            "Goods": 0 if pd.isna(r.get("Goods", 0)) else int(r.get("Goods", 0)),
            "Mail": 0 if pd.isna(r.get("Mail", 0)) else int(r.get("Mail", 0))
        })

    raw_json = json.dumps(records)

    min_month = df["Month"].min().strftime("%Y-%m")
    max_month = df["Month"].max().strftime("%Y-%m")

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Air traffic geo plot</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    body {{ 
      font-family: Arial, sans-serif; 
      margin: 0; 
      background-color: #f5f5f5;
    }}
    
    .filters-container {{ 
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      margin: 20px 20px 20px 20px;
    }}
    
    .filters-grid {{ 
      display: grid; 
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 15px; 
      align-items: end;
    }}
    
    .filter-group {{ 
      display: flex; 
      flex-direction: column; 
    }}
    
    .filter-group label {{ 
      font-weight: bold;
      margin-bottom: 5px; 
      color: #333; 
      font-size: 14px;
    }}
    
    .filter-group select, .filter-group input[type="month"] {{ 
      padding: 8px 12px; 
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
      background: white;
    }}
    
    .reset-btn {{ 
      padding: 8px 20px;
      background-color: #e74c3c;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      font-weight: bold;
    }}
    
    .reset-btn:hover {{ 
      background-color: #c0392b;
    }}
    
    .chart-container {{
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      padding: 20px;
      margin: 0 20px 20px 20px;
    }}
    
    #{div_id} {{ 
      width: 100%; 
      height: 640px; 
    }}
    
    .empty-note {{ 
      color: #666; 
      text-align: center;
      padding: 20px;
      font-style: italic;
    }}

    .chart-title {{
      text-align: center;
      margin: 0 0 20px 0;
      font-size: 18px;
      color: #2c3e50;
      font-weight: bold;
    }}
  </style>
</head>
<body>
  <div class="filters-container">
    <div class="filters-grid">
      <div class="filter-group">
        <label>Metric</label>
        <select id="metricSel">
          <option value="Passengers">Passengers</option>
          <option value="Operations">Operations</option>
          <option value="Goods">Goods</option>
          <option value="Mail">Mail</option>
        </select>
      </div>

      <div class="filter-group">
        <label>Air Service</label>
        <select id="airServiceSel"></select>
      </div>

      <div class="filter-group">
        <label>Aircraft Movement</label>
        <select id="aircraftMovementSel"></select>
      </div>

      <div class="filter-group">
        <label>Base Airport</label>
        <select id="baseAirportSel"><option>All</option></select>
      </div>

      <div class="filter-group">
        <label>Stopover Airport</label>
        <select id="stopoverAirportSel"><option>All</option></select>
      </div>

      <div class="filter-group">
        <label>Start Month</label>
        <input id="startMonth" type="month" min="{min_month}" max="{max_month}" value="{min_month}">
      </div>

      <div class="filter-group">
        <label>End Month</label>
        <input id="endMonth" type="month" min="{min_month}" max="{max_month}" value="{max_month}">
      </div>

      <div class="filter-group">
        <button class="reset-btn" id="resetBtn">Reset Filters</button>
      </div>
    </div>
  </div>

  <div class="chart-container">
    <h3 class="chart-title">Traffic per airport connections</h3>
    <div id="{div_id}"></div>
    <div class="empty-note" id="emptyNote" style="display:none;">
      No data available for the selected filters and date range.
    </div>
  </div>

<script>
const rawData = {raw_json};
const plotDiv = document.getElementById("{div_id}");

function uniqSorted(arr) {{
  return Array.from(new Set(arr.filter(x => x !== null && x !== undefined))).sort();
}}

function populateSelect(id, values) {{
  const sel = document.getElementById(id);
  sel.innerHTML = "";
  values.forEach(v => {{
    const opt = document.createElement("option");
    opt.value = v;
    opt.text = v;
    sel.appendChild(opt);
  }});
}}

function initControls() {{
  populateSelect("airServiceSel", uniqSorted(rawData.map(d => d.AirService)));
  populateSelect("aircraftMovementSel", uniqSorted(rawData.map(d => d.AircraftMovement)));
  populateSelect("baseAirportSel", ["All"].concat(uniqSorted(rawData.map(d => d.BaseAirport))));
  populateSelect("stopoverAirportSel", ["All"].concat(uniqSorted(rawData.map(d => d.StopoverAirport))));

  document.getElementById("metricSel").addEventListener("change", updatePlot);
  document.getElementById("airServiceSel").addEventListener("change", updatePlot);
  document.getElementById("aircraftMovementSel").addEventListener("change", updatePlot);
  document.getElementById("baseAirportSel").addEventListener("change", updatePlot);
  document.getElementById("stopoverAirportSel").addEventListener("change", updatePlot);
  document.getElementById("startMonth").addEventListener("change", updatePlot);
  document.getElementById("endMonth").addEventListener("change", updatePlot);
  document.getElementById("resetBtn").addEventListener("click", resetFilters);

  resetFilters();
}}

function resetFilters() {{
  document.getElementById("metricSel").value = "Passengers";
  document.getElementById("airServiceSel").value = "Commercial";
  document.getElementById("aircraftMovementSel").value = "Total";
  document.getElementById("baseAirportSel").value = "All";
  document.getElementById("stopoverAirportSel").value = "All";
  document.getElementById("startMonth").value = "{min_month}";
  document.getElementById("endMonth").value = "{max_month}";
  updatePlot();
}}

function lineWidthForValue(v) {{
  if (v <= 0) return 1;
  return Math.min(12, Math.max(1, Math.log(v + 1) * 2.0));
}}
function markerSizeForValue(v) {{
  if (v <= 0) return 4;
  return Math.min(18, Math.max(4, Math.log(v + 1) * 3.0));
}}

function updatePlot() {{
  const metric = document.getElementById("metricSel").value;
  const airService = document.getElementById("airServiceSel").value;
  const aircraftMovement = document.getElementById("aircraftMovementSel").value;
  const baseAirport = document.getElementById("baseAirportSel").value;
  const stopoverAirport = document.getElementById("stopoverAirportSel").value;

  const startInput = document.getElementById("startMonth").value || "{min_month}";
  const endInput = document.getElementById("endMonth").value || "{max_month}";

  const startDate = new Date(startInput + "-01T00:00:00");
  const endDate = new Date(endInput + "-01T00:00:00");
  endDate.setMonth(endDate.getMonth() + 1);
  endDate.setMilliseconds(endDate.getMilliseconds() - 1);

  const filtered = rawData.filter(d => {{
    const m = new Date(d.Month);
    if (isNaN(m)) return false;
    if (m < startDate || m > endDate) return false;
    if (d.AirService !== airService) return false;
    if (d.AircraftMovement !== aircraftMovement) return false;
    if (baseAirport !== "All" && d.BaseAirport !== baseAirport) return false;
    if (stopoverAirport !== "All" && d.StopoverAirport !== stopoverAirport) return false;
    return true;
  }});

  // aggregate by base-stop pair
  const groups = {{}};
  filtered.forEach(d => {{
    if (d.BaseLatitude == null || d.BaseLongitude == null || d.StopoverLatitude == null || d.StopoverLongitude == null) return;
    const key = [d.BaseAirport, d.BaseLatitude, d.BaseLongitude, d.StopoverAirport, d.StopoverLatitude, d.StopoverLongitude].join("||");
    if (!groups[key]) {{
      groups[key] = {{
        BaseAirport: d.BaseAirport,
        BaseLatitude: +d.BaseLatitude,
        BaseLongitude: +d.BaseLongitude,
        StopoverAirport: d.StopoverAirport,
        StopoverLatitude: +d.StopoverLatitude,
        StopoverLongitude: +d.StopoverLongitude,
        value: 0
      }};
    }}
    const add = Number(d[metric] || 0);
    groups[key].value += isNaN(add) ? 0 : add;
  }});

  const groupList = Object.values(groups).sort((a,b) => b.value - a.value);

  const traces = [];
  groupList.forEach(g => {{
    const val = g.value;
    const lineW = lineWidthForValue(val);
    const mkSize = markerSizeForValue(val);

    traces.push({{
      type: "scattergeo",
      mode: "lines+markers",
      lon: [g.BaseLongitude, g.StopoverLongitude],
      lat: [g.BaseLatitude, g.StopoverLatitude],
      text: `${{g.BaseAirport}} → ${{g.StopoverAirport}}<br>${{metric}}: ${{val}}`,
      hoverinfo: "text",
      line: {{ width: lineW, color: "rgba(31,119,180,0.9)" }},
      marker: {{ size: mkSize, symbol: "circle", opacity: 0.9 }},
      name: `${{g.BaseAirport}} → ${{g.StopoverAirport}} (${{val}})`
    }});
  }});

  const airportAgg = {{}};
  groupList.forEach(g => {{
    if (!airportAgg[g.BaseAirport]) airportAgg[g.BaseAirport] = {{ lat: g.BaseLatitude, lon: g.BaseLongitude, total: 0 }};
    if (!airportAgg[g.StopoverAirport]) airportAgg[g.StopoverAirport] = {{ lat: g.StopoverLatitude, lon: g.StopoverLongitude, total: 0 }};
    airportAgg[g.BaseAirport].total += g.value;
    airportAgg[g.StopoverAirport].total += g.value;
  }});
  const airports = Object.keys(airportAgg);
  if (airports.length) {{
    traces.push({{
      type: "scattergeo",
      mode: "markers",
      lon: airports.map(a => airportAgg[a].lon),
      lat: airports.map(a => airportAgg[a].lat),
      text: airports.map(a => `${{a}}<br>${{metric}}: ${{airportAgg[a].total}}`),
      hoverinfo: "text",
      marker: {{
        size: airports.map(a => markerSizeForValue(airportAgg[a].total) + 2),
        symbol: "circle",
        line: {{ width: 0.5, color: "#333" }}
      }},
      name: "Airports"
    }});
  }}

  const layout = {{
    title: `Connections — ${{metric}} (sum over range)`,
    geo: {{
      scope: "world",
      projection: {{ type: "natural earth" }},
      showland: true,
      landcolor: "rgb(240,240,240)",
      showcountries: true,
      countrycolor: "rgb(200,200,200)"
    }},
    margin: {{ t: 40, b: 20, l: 0, r: 0 }},
    legend: {{ orientation: "h", y: -0.05 }}
  }};

  if (traces.length === 0) {{
    document.getElementById("emptyNote").style.display = "block";
    Plotly.react(plotDiv, [], layout, {{displayModeBar: true}});
  }} else {{
    document.getElementById("emptyNote").style.display = "none";
    Plotly.react(plotDiv, traces, layout, {{displayModeBar: true}});
  }}
}}

initControls();
resetFilters();
</script>
</body>
</html>
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote interactive map to {output_file}")


def create_air_traffic_line_graph(df, output_file="line_graph.html", div_id="line_graph_div"):
    # Ensure Month is datetime
    df = df.copy()
    df["Month"] = pd.to_datetime(df["Month"])
    
    # Prepare minimal records list for embedding in HTML/JS
    records = []
    for _, r in df.iterrows():
        records.append({
            "Month": r["Month"].strftime("%Y-%m-%d"),
            "BaseAirport": None if pd.isna(r["BaseAirport"]) else str(r["BaseAirport"]),
            "StopoverAirport": None if pd.isna(r["StopoverAirport"]) else str(r["StopoverAirport"]),
            "Passengers": 0 if pd.isna(r.get("Passengers", 0)) else int(r.get("Passengers", 0)),
            "Operations": 0 if pd.isna(r.get("Operations", 0)) else int(r.get("Operations", 0)),
            "Goods": 0 if pd.isna(r.get("Goods", 0)) else int(r.get("Goods", 0)),
            "Mail": 0 if pd.isna(r.get("Mail", 0)) else int(r.get("Mail", 0))
        })

    raw_json = json.dumps(records)

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Air Traffic Line Graph</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    body {{ 
      font-family: Arial, sans-serif; 
      margin: 20px; 
      background-color: #f5f5f5;
    }}
    
    .filters-container {{ 
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      margin-bottom: 20px;
    }}
    
    .filters-grid {{ 
      display: grid; 
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px; 
      align-items: end;
    }}
    
    .filter-group {{ 
      display: flex; 
      flex-direction: column; 
    }}
    
    .filter-group label {{ 
      font-weight: bold;
      margin-bottom: 5px; 
      color: #333; 
      font-size: 14px;
    }}
    
    .filter-group select {{ 
      padding: 8px 12px; 
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
      background: white;
    }}
    
    .reset-btn {{ 
      padding: 8px 20px;
      background-color: #e74c3c;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      font-weight: bold;
    }}
    
    .reset-btn:hover {{ 
      background-color: #c0392b;
    }}
    
    .chart-container {{
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      padding: 20px;
    }}
    
    #{div_id} {{ 
      width: 100%; 
      height: 500px; 
    }}
    
    .summary {{
      background: #3498db;
      color: white;
      padding: 15px;
      border-radius: 8px;
      margin-bottom: 20px;
      font-size: 14px;
    }}
    
    .empty-note {{ 
      color: #666; 
      text-align: center;
      padding: 40px;
      font-style: italic;
    }}
  </style>
</head>
<body>
  <div class="filters-container">
    <div class="filters-grid">
      <div class="filter-group">
        <label>Metric</label>
        <select id="metricSelect">
          <option value="Operations">Operations</option>
          <option value="Passengers">Passengers</option>
          <option value="Goods">Goods</option>
          <option value="Mail">Mail</option>
        </select>
      </div>

      <div class="filter-group">
        <label>Base Airport</label>
        <select id="baseAirportSelect">
          <option value="All">All Base Airports</option>
        </select>
      </div>

      <div class="filter-group">
        <label>Stopover Airport</label>
        <select id="stopoverAirportSelect">
          <option value="All">All Stopover Airports</option>
        </select>
      </div>

      <div class="filter-group">
        <button class="reset-btn" id="resetBtn">Reset Filters</button>
      </div>
    </div>
  </div>

  <div id="summaryDiv" class="summary" style="display:none;"></div>
  
  <div class="chart-container">
    <div id="{div_id}"></div>
    <div class="empty-note" id="emptyNote" style="display:none;">
      No data available for the selected filters.
    </div>
  </div>

<script>
const rawData = {raw_json};
const plotDiv = document.getElementById("{div_id}");

function getUniqueValues(field) {{
  const values = rawData
    .map(d => d[field])
    .filter(v => v !== null && v !== undefined)
    .filter((v, i, arr) => arr.indexOf(v) === i)
    .sort();
  return values;
}}

function populateSelect(selectId, options, includeAll = true) {{
  const select = document.getElementById(selectId);
  select.innerHTML = '';
  
  if (includeAll) {{
    const allOption = document.createElement('option');
    allOption.value = 'All';
    allOption.textContent = selectId === 'baseAirportSelect' ? 'All Base Airports' : 'All Stopover Airports';
    select.appendChild(allOption);
  }}
  
  options.forEach(option => {{
    const optionElement = document.createElement('option');
    optionElement.value = option;
    optionElement.textContent = option;
    select.appendChild(optionElement);
  }});
}}

function initializeControls() {{
  // Populate dropdowns
  populateSelect('baseAirportSelect', getUniqueValues('BaseAirport'));
  populateSelect('stopoverAirportSelect', getUniqueValues('StopoverAirport'));

  // Add event listeners
  document.getElementById('metricSelect').addEventListener('change', updatePlot);
  document.getElementById('baseAirportSelect').addEventListener('change', updatePlot);
  document.getElementById('stopoverAirportSelect').addEventListener('change', updatePlot);
  document.getElementById('resetBtn').addEventListener('click', resetFilters);

  // Initial plot
  updatePlot();
}}

function resetFilters() {{
  document.getElementById('metricSelect').value = 'Operations';
  document.getElementById('baseAirportSelect').value = 'All';
  document.getElementById('stopoverAirportSelect').value = 'All';
  updatePlot();
}}

function updatePlot() {{
  const selectedMetric = document.getElementById('metricSelect').value;
  const selectedBaseAirport = document.getElementById('baseAirportSelect').value;
  const selectedStopoverAirport = document.getElementById('stopoverAirportSelect').value;

  // Filter data based on selections
  let filteredData = rawData.filter(d => {{
    if (selectedBaseAirport !== 'All' && d.BaseAirport !== selectedBaseAirport) return false;
    if (selectedStopoverAirport !== 'All' && d.StopoverAirport !== selectedStopoverAirport) return false;
    return true;
  }});

  if (filteredData.length === 0) {{
    document.getElementById('emptyNote').style.display = 'block';
    document.getElementById('summaryDiv').style.display = 'none';
    Plotly.react(plotDiv, [], {{}});
    return;
  }}

  document.getElementById('emptyNote').style.display = 'none';

  // Group by month and sum the selected metric
  const monthlyData = {{}};
  filteredData.forEach(d => {{
    const month = d.Month.substring(0, 7); // YYYY-MM format
    if (!monthlyData[month]) {{
      monthlyData[month] = 0;
    }}
    monthlyData[month] += d[selectedMetric] || 0;
  }});

  // Convert to arrays for plotting
  const months = Object.keys(monthlyData).sort();
  const values = months.map(month => monthlyData[month]);

  // Calculate summary statistics
  const total = values.reduce((sum, val) => sum + val, 0);
  const average = total / values.length;
  const maxValue = Math.max(...values);
  const minValue = Math.min(...values);

  // Update summary
  const summaryDiv = document.getElementById('summaryDiv');
  summaryDiv.style.display = 'block';
  summaryDiv.innerHTML = `
    <strong>Summary:</strong> Total: ${{total.toLocaleString()}} | 
    Average per month: ${{average.toFixed(1)}} | 
    Max: ${{maxValue.toLocaleString()}} | 
    Min: ${{minValue.toLocaleString()}} | 
    Data points: ${{months.length}} months
  `;

  // Create trace
  const trace = {{
    type: 'scatter',
    mode: 'lines+markers',
    x: months,
    y: values,
    line: {{
      color: '#3498db',
      width: 3
    }},
    marker: {{
      color: '#2980b9',
      size: 6
    }},
    name: selectedMetric,
    hovertemplate: '<b>%{{x}}</b><br>' + selectedMetric + ': %{{y:,.0f}}<extra></extra>'
  }};

  // Create layout
  let title = `${{selectedMetric}} Over Time`;
  if (selectedBaseAirport !== 'All' || selectedStopoverAirport !== 'All') {{
    const airportInfo = [];
    if (selectedBaseAirport !== 'All') airportInfo.push(`Base: ${{selectedBaseAirport}}`);
    if (selectedStopoverAirport !== 'All') airportInfo.push(`Stopover: ${{selectedStopoverAirport}}`);
    title += ` (${{airportInfo.join(', ')}})`;
  }}

  const layout = {{
    title: {{
      text: title,
      font: {{ size: 18, color: '#2c3e50' }}
    }},
    xaxis: {{
      title: 'Month',
      type: 'category',
      tickangle: -45,
      gridcolor: '#ecf0f1'
    }},
    yaxis: {{
      title: selectedMetric,
      gridcolor: '#ecf0f1'
    }},
    plot_bgcolor: 'white',
    paper_bgcolor: 'white',
    margin: {{
      t: 60,
      b: 80,
      l: 80,
      r: 40
    }},
    hovermode: 'x unified'
  }};

  const config = {{
    displayModeBar: true,
    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
    displaylogo: false
  }};

  Plotly.react(plotDiv, [trace], layout, config);
}}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initializeControls);
</script>
</body>
</html>
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote interactive line graph to {output_file}")


def create_prediction_line_graph(df, output_file="prediction_graph.html", div_id="prediction_graph_div"):
    # Ensure Month is datetime
    df = df.copy()
    df["Month"] = pd.to_datetime(df["Month"])
    
    # Prepare minimal records list for embedding in HTML/JS
    records = []
    for _, r in df.iterrows():
        records.append({
            "Month": r["Month"].strftime("%Y-%m-%d"),
            "Island": str(r["Island"]) if not pd.isna(r["Island"]) else 0,
            "RealPassengers": float(r["RealPassengers"]) if not pd.isna(r["RealPassengers"]) else None,
            "yhat_lower": float(r["yhat_lower"]) if not pd.isna(r["yhat_lower"]) else 0,
            "yhat": float(r["yhat"]) if not pd.isna(r["yhat"]) else 0,
            "yhat_upper": float(r["yhat_upper"]) if not pd.isna(r["yhat_upper"]) else 0
        })

    raw_json = json.dumps(records)

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Passenger Predictions</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    body {{ 
      font-family: Arial, sans-serif; 
      margin: 0; 
      background-color: #f5f5f5;
    }}
    
    .filters-container {{ 
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      margin: 20px 20px 20px 20px;
    }}
    
    .filters-grid {{ 
      display: grid; 
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px; 
      align-items: end;
    }}
    
    .filter-group {{ 
      display: flex; 
      flex-direction: column; 
    }}
    
    .filter-group label {{ 
      font-weight: bold;
      margin-bottom: 5px; 
      color: #333; 
      font-size: 14px;
    }}
    
    .filter-group select {{ 
      padding: 8px 12px; 
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
      background: white;
    }}
    
    .reset-btn {{ 
      padding: 8px 20px;
      background-color: #e74c3c;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      font-weight: bold;
    }}
    
    .reset-btn:hover {{ 
      background-color: #c0392b;
    }}
    
    .chart-container {{
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      padding: 20px;
      margin: 0 20px 20px 20px;
    }}
    
    #{div_id} {{ 
      width: 100%; 
      height: 500px; 
    }}
    
    .summary {{
      background: #3498db;
      color: white;
      padding: 15px;
      border-radius: 8px;
      margin: 0 20px 20px 20px;
      font-size: 14px;
    }}
    
    .empty-note {{ 
      color: #666; 
      text-align: center;
      padding: 40px;
      font-style: italic;
    }}

    .legend-info {{
      background: #ecf0f1;
      padding: 10px;
      border-radius: 4px;
      margin-top: 10px;
      font-size: 12px;
      color: #555;
    }}
  </style>
</head>
<body>
  <div class="filters-container">
    <div class="filters-grid">
      <div class="filter-group">
        <label>Island ID</label>
        <select id="islandSelect">
          <option value="Canary Islands">Canary Islands</option>
        </select>
      </div>

      <div class="filter-group">
        <button class="reset-btn" id="resetBtn">Reset Filters</button>
      </div>
    </div>
  </div>

  <div id="summaryDiv" class="summary" style="display:none;"></div>
  
  <div class="chart-container">
    <div id="{div_id}"></div>
    <div class="empty-note" id="emptyNote" style="display:none;">
      No data available for the selected island.
    </div>
    <div class="legend-info">
      <strong>Legend:</strong> Real Passengers (blue solid), Prediction (red dashed), 
      Prediction Bounds (green dashed), Confidence Band (light gray shaded area)
    </div>
  </div>

<script>
const rawData = {raw_json};
const plotDiv = document.getElementById("{div_id}");

function getUniqueIslands() {{
  const islands = rawData
    .map(d => d.Island)
    .filter((v, i, arr) => arr.indexOf(v) === i)
    .sort((a, b) => a - b);
  return islands;
}}

function populateIslandSelect() {{
  const select = document.getElementById('islandSelect');
  select.innerHTML = '';
  
  const islands = getUniqueIslands();
  islands.forEach(island => {{
    const optionElement = document.createElement('option');
    optionElement.value = island.toString();
    optionElement.textContent = `${{island}}`;
    select.appendChild(optionElement);
  }});
}}

function initializeControls() {{
  populateIslandSelect();

  // Add event listeners
  document.getElementById('islandSelect').addEventListener('change', updatePlot);
  document.getElementById('resetBtn').addEventListener('click', resetFilters);

  // Initial plot
  updatePlot();
}}

function resetFilters() {{
  const islands = getUniqueIslands();
  const firstIsland = islands.length > 0 ? islands[0].toString() : 'Canary Islands';
  document.getElementById('islandSelect').value = firstIsland;
  updatePlot();
}}

function updatePlot() {{
  const selectedIsland = document.getElementById('islandSelect').value;

  // Filter data based on selection
  let filteredData = rawData;
  if (selectedIsland !== 'All') {{
    filteredData = rawData.filter(d => d.Island.toString() === selectedIsland);
  }}

  if (filteredData.length === 0) {{
    document.getElementById('emptyNote').style.display = 'block';
    document.getElementById('summaryDiv').style.display = 'none';
    Plotly.react(plotDiv, [], {{}});
    return;
  }}

  document.getElementById('emptyNote').style.display = 'none';

  // Sort by month
  filteredData.sort((a, b) => new Date(a.Month) - new Date(b.Month));

  const months = filteredData.map(d => d.Month.substring(0, 7)); // YYYY-MM format
  const realPassengers = filteredData.map(d => d.RealPassengers);
  const yhat = filteredData.map(d => d.yhat);
  const yhatLower = filteredData.map(d => d.yhat_lower);
  const yhatUpper = filteredData.map(d => d.yhat_upper);

  // Calculate summary statistics for real passengers
  const totalReal = realPassengers.reduce((sum, val) => sum + val, 0);
  const avgReal = totalReal / realPassengers.length;
  const maxReal = Math.max(...realPassengers);
  const minReal = Math.min(...realPassengers);

  // Update summary
  const summaryDiv = document.getElementById('summaryDiv');
  summaryDiv.style.display = 'block';
  let summaryText = `<strong>Real Passengers Summary:</strong> Total: ${{totalReal.toLocaleString()}} | 
    Average per month: ${{avgReal.toFixed(0)}} | 
    Max: ${{maxReal.toLocaleString()}} | 
    Min: ${{minReal.toLocaleString()}} | 
    Data points: ${{months.length}} months`;
  
  if (selectedIsland !== 'All') {{
    summaryText += ` | Island: ${{selectedIsland}}`;
  }}
  
  summaryDiv.innerHTML = summaryText;

  const traces = [];

  // Confidence band (fill between upper and lower bounds)
  traces.push({{
    type: 'scatter',
    mode: 'lines',
    x: months,
    y: yhatUpper,
    fill: 'tonexty',
    fillcolor: 'rgba(128, 128, 128, 0.2)',
    line: {{ color: 'transparent' }},
    name: 'Confidence Band',
    hovertemplate: '<b>%{{x}}</b><br>Upper Bound Prediction: %{{y:,.0f}}<extra></extra>',
    showlegend: false
  }});

  traces.push({{
    type: 'scatter',
    mode: 'lines',
    x: months,
    y: yhatLower,
    fill: 'tonexty',
    fillcolor: 'rgba(128, 128, 128, 0.2)',
    line: {{ color: 'transparent' }},
    name: 'Confidence Band',
    hovertemplate: '<b>%{{x}}</b><br>Lower Bound Prediction: %{{y:,.0f}}<extra></extra>'
  }});

  // Real passengers line
  traces.push({{
    type: 'scatter',
    mode: 'lines+markers',
    x: months,
    y: realPassengers,
    line: {{
      color: '#3498db',
      width: 3
    }},
    marker: {{
      color: '#2980b9',
      size: 4
    }},
    name: 'Real Passengers',
    hovertemplate: '<b>%{{x}}</b><br>Real Passengers: %{{y:,.0f}}<extra></extra>'
  }});

  // Prediction line
  traces.push({{
    type: 'scatter',
    mode: 'lines+markers',
    x: months,
    y: yhat,
    line: {{
      color: '#e74c3c',
      width: 3,
      dash: 'dash'
    }},
    marker: {{
      color: '#c0392b',
      size: 4
    }},
    name: 'Prediction',
    hovertemplate: '<b>%{{x}}</b><br>Prediction: %{{y:,.0f}}<extra></extra>'
  }});

  // Upper bound line
  traces.push({{
    type: 'scatter',
    mode: 'lines',
    x: months,
    y: yhatUpper,
    line: {{
      color: '#27ae60',
      width: 2,
      dash: 'dot'
    }},
    name: 'Upper Bound Prediction',
    hovertemplate: '<b>%{{x}}</b><br>Upper Bound Prediction: %{{y:,.0f}}<extra></extra>'
  }});

  // Lower bound line
  traces.push({{
    type: 'scatter',
    mode: 'lines',
    x: months,
    y: yhatLower,
    line: {{
      color: '#27ae60',
      width: 2,
      dash: 'dot'
    }},
    name: 'Lower Bound Prediction',
    hovertemplate: '<b>%{{x}}</b><br>Lower Bound Prediction: %{{y:,.0f}}<extra></extra>'
  }});

  // Create layout
  let title = 'Passenger Predictions vs Reality';
  if (selectedIsland !== 'Canary Islands') {{
    title += ` - ${{selectedIsland}}`;
  }} else {{
    title += ` - All islands`
  }}

  const layout = {{
    title: {{
      text: title,
      font: {{ size: 18, color: '#2c3e50' }}
    }},
    xaxis: {{
      title: 'Month',
      type: 'category',
      tickangle: -45,
      gridcolor: '#ecf0f1'
    }},
    yaxis: {{
      title: 'Number of Passengers',
      gridcolor: '#ecf0f1',
      tickformat: ',.0f'
    }},
    plot_bgcolor: 'white',
    paper_bgcolor: 'white',
    margin: {{
      t: 60,
      b: 100,
      l: 100,
      r: 40
    }},
    hovermode: 'x unified',
    legend: {{
      orientation: 'h',
      y: -0.2,
      x: 0.5,
      xanchor: 'center'
    }}
  }};

  const config = {{
    displayModeBar: true,
    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
    displaylogo: false
  }};

  Plotly.react(plotDiv, traces, layout, config);
}}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initializeControls);
</script>
</body>
</html>
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote prediction line graph to {output_file}")


def create_airport_bar_chart(df, output_file="airport_bar_chart.html", div_id="airport_bar_div"):
    """
    Creates an interactive bar chart showing airport passenger data using Plotly.
    
    Parameters:
    df: DataFrame with columns 'AirportName' and 'Passengers'
    output_file: HTML file name to save the chart
    div_id: ID for the div element (for embedding in other HTML)
    """
    
    # Make a copy and ensure data is clean
    df_clean = df.copy()
    df_clean = df_clean.sort_values('Passengers', ascending=True)  # Sort for better visualization
    
    # Shorten long airport names for better display
    df_clean['ShortName'] = df_clean['AirportName'].apply(lambda x: 
        x.replace('International Airport', 'Int\'l').replace('Airport', '').strip()
    )
    
    # Create the bar chart
    fig = px.bar(
        df_clean,
        x='Passengers',
        y='ShortName',
        orientation='h',  # Horizontal bars work better for long airport names
        title='Top Airports by Arriving Passengers',
        labels={'Passengers': 'Number of Passengers', 'ShortName': 'Airport'},
        color='Passengers',
        color_continuous_scale='Blues',
        text='Passengers'
    )
    
    # Customize the layout
    fig.update_layout(
        font_family="Arial, sans-serif",
        font_size=12,
        title_font_size=18,
        title_font_color='#2c3e50',
        title_x=0.5,  # Center the title
        
        # Chart dimensions and margins - increased left margin for more space
        height=600,
        margin=dict(l=150, r=20, t=60, b=40),  # Increased left margin from 20 to 150
        
        # Background colors
        plot_bgcolor='white',
        paper_bgcolor='white',
        
        # Grid styling
        xaxis=dict(
            gridcolor='#ecf0f1',
            title_font_size=14,
            tickformat=',.0f'  # Format numbers with commas
        ),
        yaxis=dict(
            gridcolor='#ecf0f1',
            title_font_size=14,
            tickfont=dict(size=11)  # Slightly smaller font for airport names
        ),
        
        # Color bar styling
        coloraxis_colorbar=dict(
            title="Passengers",
            title_font_size=12
        ),
        
        # Hover styling
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        )
    )
    
    # Customize the bars
    fig.update_traces(
        texttemplate='%{text:,.0f}',  # Format text labels with commas
        textposition='outside',
        textfont_size=10,
        hovertemplate='<b>%{y}</b><br>Passengers: %{x:,.0f}<extra></extra>',
        marker_line_width=0.5,
        marker_line_color='#2c3e50'
    )
    
    # Remove the color bar (legend) since it's not really needed for a single metric
    fig.update_layout(showlegend=False)
    fig.update_coloraxes(showscale=False)
    
    # Generate the plot HTML
    plot_html = plot(fig, output_type='div', include_plotlyjs=True)
    
    # Create the HTML with proper styling and div structure
    html_content = f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8" />
        <title>Airport Passenger Chart</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 0; 
                background-color: #f5f5f5;
            }}
            
            .chart-container {{
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 20px;
                margin: 20px;
            }}
            
            .plotly-graph-div {{ 
                width: 100% !important; 
                height: 600px !important; 
            }}
            
            .summary {{
                background: #3498db;
                color: white;
                padding: 15px;
                border-radius: 8px;
                margin: 20px;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="summary">
            <strong>Summary:</strong> 
            Total Passengers: {df_clean['Passengers'].sum():,.0f} | 
            Top Airport: {df_clean.iloc[-1]['AirportName']} ({df_clean.iloc[-1]['Passengers']:,.0f}) | 
            Airports Shown: {len(df_clean)}
        </div>
        
        <div class="chart-container">
            {plot_html}
        </div>
    </body>
    </html>
    """
    
    # Save the complete HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Wrote interactive bar chart to {output_file}")


if __name__ == "__main__":
    pipeline_update_plots()