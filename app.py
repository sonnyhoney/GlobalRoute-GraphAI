import os
import glob
import json
import streamlit as st
import pandas as pd
from neo4j import GraphDatabase
from google import genai
from dotenv import load_dotenv
from pyvis.network import Network
import streamlit.components.v1 as components

# Load environment variables
load_dotenv(override=True)

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+ssc://51204372.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "51204372")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

st.set_page_config(
    page_title="GlobalRoute | GraphAI Logistics Engine",
    page_icon="🚢",
    layout="wide"
)

# Custom Cyber-Graph Theme
st.markdown("""
<style>
    .main-title { font-size: 2.4rem !important; font-weight: 800; color: #FFFFFF; margin-bottom: 0px; }
    .sub-title { font-size: 1.1rem !important; font-weight: 500; color: #00d2ff; margin-bottom: 25px; }
    
    .stButton>button {
        width: 100%; border-radius: 8px; height: 3.2em; background-color: #0066fe; color: white; font-weight: 700; font-size: 1.05rem; border: none; transition: all 0.3s ease;
    }
    .stButton>button:hover { background-color: #0052cc; box-shadow: 0px 4px 14px rgba(0, 210, 255, 0.3); }
    
    .metric-card {
        background: linear-gradient(135deg, #111726 0%, #090d16 100%); padding: 16px 20px; border-radius: 12px; border-left: 4px solid #00d2ff; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .metric-title { font-size: 0.8rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 1.35rem; color: #FFFFFF; font-weight: 800; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CONNECTORS & RESOURCE CACHING
# ==========================================
@st.cache_resource
def get_neo4j_driver():
    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
        max_connection_lifetime=30,
        liveness_check_timeout=10
    )

driver = get_neo4j_driver()

def get_gemini_client():
    if GEMINI_API_KEY:
        return genai.Client(api_key=GEMINI_API_KEY)
    return None

def cleanup_temp_files():
    for temp_file in glob.glob("temp_graph_*.html"):
        try:
            os.remove(temp_file)
        except Exception:
            pass

# ==========================================
# GRAPH ROUTING & TRAVERSAL ALGORITHMS
# ==========================================
def get_available_locations():
    """Fetches all locations from Neo4j for dropdowns."""
    query = "MATCH (l:Location) RETURN l.code AS code, l.name AS name, l.type AS type, l.country AS country ORDER BY l.name ASC"
    with driver.session() as session:
        result = session.run(query)
        return [{"code": r["code"], "label": f"{r['name']} ({r['code']}) — {r['country']}"} for r in result]

def find_multi_modal_paths(origin_code, destination_code, blocked_chokepoints=None, max_depth=6):
    """
    Traverses Neo4j Knowledge Graph to find valid multi-modal freight paths.
    """
    if blocked_chokepoints is None:
        blocked_chokepoints = []

    cypher = """
    MATCH p = (src:Location {code: $origin})-[r:CORRIDOR*1..6]->(dst:Location {code: $dest})
    WHERE NONE(n IN nodes(p) WHERE n.code IN $blocked)
    WITH p,
         reduce(totalTime = 0, rel IN relationships(p) | totalTime + rel.transit_time_hrs) AS Total_Hours,
         reduce(totalCost = 0, rel IN relationships(p) | totalCost + rel.cost_usd_per_teu) AS Total_Cost_USD,
         reduce(totalCO2 = 0, rel IN relationships(p) | totalCO2 + rel.co2_kg_per_teu) AS Total_CO2_KG,
         reduce(minRel = 1.0, rel IN relationships(p) | CASE WHEN rel.reliability < minRel THEN rel.reliability ELSE minRel END) AS Min_Reliability,
         [n IN nodes(p) | n.name] AS Node_Names,
         [n IN nodes(p) | n.code] AS Node_Codes,
         [rel IN relationships(p) | {mode: rel.mode, time: rel.transit_time_hrs, cost: rel.cost_usd_per_teu, co2: rel.co2_kg_per_teu}] AS Leg_Details
    RETURN Total_Hours, Total_Cost_USD, Total_CO2_KG, Min_Reliability, Node_Names, Node_Codes, Leg_Details, length(p) AS Hops
    ORDER BY Total_Hours ASC
    LIMIT 10
    """
    
    with driver.session() as session:
        result = session.run(cypher, origin=origin_code, dest=destination_code, blocked=blocked_chokepoints)
        paths = []
        for record in result:
            paths.append({
                "total_hours": record["Total_Hours"],
                "total_days": round(record["Total_Hours"] / 24, 1),
                "total_cost_usd": record["Total_Cost_USD"],
                "total_co2_kg": record["Total_CO2_KG"],
                "min_reliability": round(record["Min_Reliability"] * 100, 1),
                "node_names": record["Node_Names"],
                "node_codes": record["Node_Codes"],
                "legs": record["Leg_Details"],
                "hops": record["Hops"]
            })
        return paths

# ==========================================
# INTERACTIVE PYVIS TOPOLOGY VISUALIZER
# ==========================================
def render_route_topology(path_nodes, blocked_nodes=None):
    if blocked_nodes is None:
        blocked_nodes = []

    # Ensure all path node codes are strings
    str_path_nodes = [str(n) for n in path_nodes if n is not None]
    str_blocked_nodes = [str(b) for b in blocked_nodes if b is not None]

    net = Network(height="480px", width="100%", bgcolor="#090d16", font_color="#cbd5e1")
    net.force_atlas_2based()
    
    path_pairs = set()
    if str_path_nodes and len(str_path_nodes) > 1:
        for i in range(len(str_path_nodes) - 1):
            path_pairs.add((str_path_nodes[i], str_path_nodes[i+1]))

    with driver.session() as session:
        # 1. Fetch only locations that have valid codes
        nodes_res = session.run("""
            MATCH (l:Location) 
            WHERE l.code IS NOT NULL 
            RETURN l.code AS code, l.name AS name, l.type AS type
        """)
        
        for r in nodes_res:
            code = str(r["code"])
            name = str(r["name"]) if r["name"] is not None else code
            l_type_str = str(r["type"]) if r["type"] is not None else ""
            
            if code in str_blocked_nodes:
                color = "#ef4444"
                size = 22
                label = f"⛔ {name}\n[BLOCKED]"
            elif code in str_path_nodes:
                color = "#00d2ff"
                size = 24
                label = f"⭐ {name}\n({code})"
            elif "Chokepoint" in l_type_str:
                color = "#f59e0b"
                size = 18
                label = f"⚠️ {name}"
            else:
                color = "#475569"
                size = 14
                label = f"{name} ({code})"
                
            net.add_node(code, label=label, color=color, size=size, font={"color": "white", "size": 11})

        # 2. Fetch corridors between valid locations
        edges_res = session.run("""
            MATCH (a:Location)-[r:CORRIDOR]->(b:Location) 
            WHERE a.code IS NOT NULL AND b.code IS NOT NULL
            RETURN a.code AS src, b.code AS tgt, r.mode AS mode, r.cost_usd_per_teu AS cost, r.transit_time_hrs AS hrs
        """)
        
        for r in edges_res:
            src = str(r["src"])
            tgt = str(r["tgt"])
            mode = str(r["mode"]) if r["mode"] is not None else "CORRIDOR"
            cost = r["cost"] if r["cost"] is not None else 0
            hrs = r["hrs"] if r["hrs"] is not None else 0
            
            if (src, tgt) in path_pairs:
                edge_color = "#00d2ff"
                edge_width = 3.5
            else:
                edge_color = "#1e293b"
                edge_width = 1.0

            net.add_edge(
                src, tgt, 
                title=f"{mode} | {hrs}h | ${cost}/TEU", 
                label=f"{mode[:5]} (${cost})", 
                color=edge_color, 
                width=edge_width,
                font={"color": "#94a3b8", "size": 8}
            )

    output_html = "temp_graph_route.html"
    net.save_graph(output_html)
    with open(output_html, "r", encoding="utf-8") as f:
        html_code = f.read()
    return html_code

# ==========================================
# GEMINI SUPPLY CHAIN ADVISOR
# ==========================================
def generate_ai_logistics_brief(origin_name, dest_name, optimal_path, disruption_scenario=None):
    client = get_gemini_client()
    if not client:
        return "⚠️ Add `GEMINI_API_KEY` to `.env` to activate real-time AI Executive Logistics Briefs."

    prompt = f"""
    You are an Executive Supply Chain & Maritime Routing AI Advisor.
    Analyze the following multi-modal freight routing facts retrieved directly from the Neo4j Knowledge Graph.

    --- ROUTE FACTS ---
    Origin: {origin_name}
    Destination: {dest_name}
    Primary Selected Route: {' ➔ '.join(optimal_path['node_names'])}
    Total Transit Lead Time: {optimal_path['total_days']} Days ({optimal_path['total_hours']} Hours)
    Total Freight Cost: ${optimal_path['total_cost_usd']} per TEU
    Scope 3 ESG Footprint: {optimal_path['total_co2_kg']} kg CO2/TEU
    Corridor Reliability: {optimal_path['min_reliability']}%
    Active Disruption Scenario: {disruption_scenario if disruption_scenario else 'Normal Operations (No Active Chokepoints Blocked)'}
    -------------------

    Write a concise 3-paragraph Executive Advisory Brief for a Chief Supply Chain Officer (CSCO):
    1. **Route Feasibility & Strategic Breakdown**: Justify the corridor and transport modes (Maritime ocean lanes vs Inland rail).
    2. **Risk & Resilience Assessment**: Highlight critical chokepoints traversed (or bypassed) and explain the operational risk.
    3. **Actionable Executive Recommendations**: Concrete steps regarding customs clearance, carbon compliance (Scope 3 ESG), and buffer lead times.
    """
    try:
        response = client.chats.create(model='gemini-3.5-flash-lite').send_message(prompt)
        return response.text
    except Exception as e:
        return f"Gemini Advisory Notice: {e}"

# ==========================================
# SIDEBAR CONTROLS & 4 DISRUPTION SCENARIOS
# ==========================================
st.sidebar.markdown("## ⚙️ GlobalRoute Engine")
st.sidebar.markdown("""
- **Graph Engine:** Neo4j Aura Cloud GDS
- **Algorithm:** Multi-Objective Dijkstra / Yen's Path
- **AI Advisor:** Google Gemini Flash
- **Domain:** Maritime & Inland Intermodal Freight
""")

st.sidebar.write("---")
st.sidebar.markdown("### 🚨 Chokepoint Disruption Simulator")
st.sidebar.caption("Simulate real-world canal blockages or geopolitical crises to trigger dynamic graph rerouting:")

# THE 4 SCENARIOS
simulate_suez = st.sidebar.checkbox("🚫 Red Sea / Suez Crisis (Port Said & Bab-el-Mandeb)", value=False)
simulate_hormuz = st.sidebar.checkbox("🚫 Strait of Hormuz Conflict (Persian Gulf & Jebel Ali)", value=False)
simulate_panama = st.sidebar.checkbox("🚫 Panama Canal Drought Restrictions", value=False)
simulate_malacca = st.sidebar.checkbox("🚫 Strait of Malacca Congestion", value=False)

blocked_nodes = []
disruption_label = []
if simulate_suez:
    blocked_nodes.extend(["EGPSD", "DJJIB"])
    disruption_label.append("Suez & Red Sea Blocked")
if simulate_hormuz:
    blocked_nodes.append("AEJEA")
    disruption_label.append("Strait of Hormuz / Jebel Ali Restricted")
if simulate_panama:
    blocked_nodes.append("PAPCN")
    disruption_label.append("Panama Canal Restricted")
if simulate_malacca:
    blocked_nodes.append("MYPKG")
    disruption_label.append("Strait of Malacca Congested")

active_disruption_str = ", ".join(disruption_label) if disruption_label else None

st.sidebar.write("---")
st.sidebar.markdown("[🌐 Sonny Honey Portfolio](https://adjacency.xyz)")
st.sidebar.markdown("[📄 Deep Dive Article](https://adjacency.xyz/articles/why-vector-search-fails-graphrag.html)")

# ==========================================
# MAIN INTERFACE
# ==========================================
st.markdown('<p class="main-title">🚢 GlobalRoute-GraphAI Engine</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Enterprise Multi-Modal Supply Chain & Maritime Routing Optimizer powered by Neo4j & Google Gemini</p>', unsafe_allow_html=True)

# Value Proposition Banner
st.markdown("""
<div style="background: #111726; border: 1px solid #1e293b; border-radius: 12px; padding: 18px 24px; margin-bottom: 25px;">
    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 15px;">
        <div>
            <div style="color: #00d2ff; font-weight: 700; font-size: 0.85rem; font-family: monospace;">MULTI-OBJECTIVE OPTIMIZATION</div>
            <p style="color: #FFFFFF; font-size: 1rem; font-weight: 700; margin: 4px 0 0 0;">Balance Cost ($/TEU), ETA (Days), &amp; Scope 3 ESG (kg CO₂)</p>
        </div>
        <div>
            <div style="color: #00d2ff; font-weight: 700; font-size: 0.85rem; font-family: monospace;">CHOKEPOINT RESILIENCE</div>
            <p style="color: #FFFFFF; font-size: 1rem; font-weight: 700; margin: 4px 0 0 0;">4-Scenario Geopolitical Disruption Simulator</p>
        </div>
        <div>
            <div style="color: #00d2ff; font-weight: 700; font-size: 0.85rem; font-family: monospace;">AUDITABLE LINEAGE</div>
            <p style="color: #FFFFFF; font-size: 1rem; font-weight: 700; margin: 4px 0 0 0;">Zero-Hallucination Neo4j Path Proof</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Dropdown Location Options
locations = get_available_locations()
loc_map = {l["code"]: l["label"] for l in locations}
code_list = [l["code"] for l in locations]

col_orig, col_dest, col_obj = st.columns([2, 2, 1.5])

with col_orig:
    default_origin_idx = code_list.index("CNSHA") if "CNSHA" in code_list else 0
    origin_code = st.selectbox("📍 Select Origin Port / Inland Hub:", code_list, format_func=lambda x: loc_map[x], index=default_origin_idx)

with col_dest:
    default_dest_idx = code_list.index("DEDUI") if "DEDUI" in code_list else 1
    dest_code = st.selectbox("🎯 Select Destination Terminal / DC:", code_list, format_func=lambda x: loc_map[x], index=default_dest_idx)

with col_obj:
    optimization_goal = st.selectbox("⚡ Optimization Objective:", ["Fastest Route (Lead Time)", "Cheapest Route (Cost $/TEU)", "Greenest Route (Lowest CO₂)", "Highest Reliability"])

st.write("")

if st.button("🚀 Calculate Optimal Multi-Modal Path & Analyze Risk"):
    if origin_code == dest_code:
        st.warning("⚠️ Origin and Destination cannot be the same location.")
    else:
        with st.spinner("Traversing Neo4j Knowledge Graph & evaluating multi-modal corridors..."):
            paths = find_multi_modal_paths(origin_code, dest_code, blocked_chokepoints=blocked_nodes)
            
            if not paths:
                st.error(f"❌ No viable path found between **{loc_map[origin_code]}** and **{loc_map[dest_code]}** under current chokepoint restrictions.")
                if blocked_nodes:
                    st.info(f"💡 Try unchecking some blocked chokepoints in the sidebar (Currently blocked: {', '.join(blocked_nodes)}).")
            else:
                if "Cheapest" in optimization_goal:
                    sorted_paths = sorted(paths, key=lambda x: x["total_cost_usd"])
                elif "Greenest" in optimization_goal:
                    sorted_paths = sorted(paths, key=lambda x: x["total_co2_kg"])
                elif "Reliability" in optimization_goal:
                    sorted_paths = sorted(paths, key=lambda x: x["min_reliability"], reverse=True)
                else:
                    sorted_paths = sorted(paths, key=lambda x: x["total_hours"])

                best_path = sorted_paths[0]

                # KPI CARDS
                st.markdown("### 📊 Route Performance & Cost Breakdown")
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                
                with kpi1:
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Total Transit Lead Time</div><div class="metric-value">{best_path["total_days"]} Days <span style="font-size: 0.9rem; color:#94a3b8;">({best_path["total_hours"]} hrs)</span></div></div>', unsafe_allow_html=True)
                with kpi2:
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Freight Cost per TEU</div><div class="metric-value">${best_path["total_cost_usd"]:,} USD</div></div>', unsafe_allow_html=True)
                with kpi3:
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Scope 3 ESG Footprint</div><div class="metric-value">{best_path["total_co2_kg"]:,} kg CO₂/TEU</div></div>', unsafe_allow_html=True)
                with kpi4:
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Corridor Reliability</div><div class="metric-value">{best_path["min_reliability"]}%</div></div>', unsafe_allow_html=True)

                st.write("")

                if blocked_nodes:
                    st.warning(f"🚨 **Disruption Active:** The route below dynamically bypasses blocked chokepoints: **{', '.join(blocked_nodes)}**.")

                # CORRIDOR SEQUENCE
                st.markdown("#### 🗺️ Multi-Modal Corridor Sequence")
                path_str = " &nbsp;➔&nbsp; ".join([f"**`{name}`**" for name in best_path["node_names"]])
                st.markdown(f"<div style='background: #111726; padding: 14px 18px; border-radius: 8px; border: 1px solid #1e293b; font-size: 1.05rem;'>{path_str}</div>", unsafe_allow_html=True)
                
                st.write("")

                # DETAILED LEG TABLE
                with st.expander("🔍 View Leg-by-Leg Intermodal Breakdown", expanded=True):
                    leg_rows = []
                    for i, leg in enumerate(best_path["legs"]):
                        leg_rows.append({
                            "Leg": f"Leg {i+1}",
                            "From": best_path["node_names"][i],
                            "To": best_path["node_names"][i+1],
                            "Mode": leg["mode"],
                            "Transit Time (hrs)": leg["time"],
                            "Cost ($/TEU)": f"${leg['cost']}",
                            "CO₂ (kg)": f"{leg['co2']} kg"
                        })
                    st.dataframe(pd.DataFrame(leg_rows), use_container_width=True)

                st.write("---")

                # INTERACTIVE PYVIS TOPOLOGY
                st.markdown("### 🕸️ Interactive Corridor Network Topology")
                st.caption("Inspect the active path highlighted in **Cyan**, background corridors in **Slate**, and blocked chokepoints in **Red**:")
                
                graph_html = render_route_topology(best_path["node_codes"], blocked_nodes=blocked_nodes)
                components.html(graph_html, height=500, scrolling=False)

                st.write("---")

                # GEMINI EXECUTIVE ADVISORY REPORT
                st.markdown("### 🤖 Google Gemini Supply Chain Advisory Brief")
                with st.spinner("Generating executive risk and feasibility briefing with Gemini..."):
                    brief = generate_ai_logistics_brief(
                        loc_map[origin_code],
                        loc_map[dest_code],
                        best_path,
                        disruption_scenario=active_disruption_str
                    )
                    st.markdown(brief)

                # EXPORT
                st.write("---")
                st.markdown("#### 📥 Export Route Planning Dossier")
                exp_c1, exp_c2 = st.columns(2)
                with exp_c1:
                    export_payload = {
                        "origin": loc_map[origin_code],
                        "destination": loc_map[dest_code],
                        "optimization_goal": optimization_goal,
                        "kpis": {
                            "transit_days": best_path["total_days"],
                            "transit_hours": best_path["total_hours"],
                            "cost_per_teu_usd": best_path["total_cost_usd"],
                            "co2_kg_per_teu": best_path["total_co2_kg"],
                            "reliability": f"{best_path['min_reliability']}%"
                        },
                        "corridor_sequence": best_path["node_names"],
                        "active_disruptions": active_disruption_str,
                        "executive_brief": brief
                    }
                    st.download_button(
                        label="📊 Download Route Dossier (.json)",
                        data=json.dumps(export_payload, indent=2),
                        file_name=f"GlobalRoute_{origin_code}_to_{dest_code}.json",
                        mime="application/json"
                    )
                with exp_c2:
                    st.download_button(
                        label="📄 Download Advisory Brief (.txt)",
                        data=f"GLOBALROUTE ADVISORY REPORT\nOrigin: {loc_map[origin_code]}\nDestination: {loc_map[dest_code]}\n\n{brief}",
                        file_name=f"GlobalRoute_Advisory_{origin_code}_to_{dest_code}.txt",
                        mime="text/plain"
                    )

        cleanup_temp_files()