import os
import sys
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv(override=True)

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+ssc://51204372.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "51204372")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_PASSWORD:
    print("❌ ERROR: NEO4J_PASSWORD is not set in environment variables.")
    sys.exit(1)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# ==============================================================================
# SEED DATA: GLOBAL MULTI-MODAL LOGISTICS NODES & MARITIME CORRIDORS
# ==============================================================================

NODES_DATA = [
    # Global Seaports (Asia, Europe, Americas, Middle East, Africa)
    {"code": "CNSHA", "name": "Port of Shanghai", "country": "China", "type": "Seaport", "lat": 31.2304, "lon": 121.4737, "capacity_teu_annual": 47300000},
    {"code": "CNNGB", "name": "Port of Ningbo-Zhoushan", "country": "China", "type": "Seaport", "lat": 29.8683, "lon": 121.5440, "capacity_teu_annual": 33350000},
    {"code": "SGSIN", "name": "Port of Singapore", "country": "Singapore", "type": "Transshipment Hub", "lat": 1.3521, "lon": 103.8198, "capacity_teu_annual": 37300000},
    {"code": "KRPUS", "name": "Port of Busan", "country": "South Korea", "type": "Seaport", "lat": 35.1796, "lon": 129.0756, "capacity_teu_annual": 22700000},
    {"code": "AEJEA", "name": "Port of Jebel Ali (Dubai)", "country": "UAE", "type": "Transshipment Hub", "lat": 24.9857, "lon": 55.0273, "capacity_teu_annual": 14000000},
    {"code": "NLRTM", "name": "Port of Rotterdam", "country": "Netherlands", "type": "Seaport", "lat": 51.9244, "lon": 4.4777, "capacity_teu_annual": 14450000},
    {"code": "DEHAM", "name": "Port of Hamburg", "country": "Germany", "type": "Seaport", "lat": 53.5511, "lon": 9.9937, "capacity_teu_annual": 8350000},
    {"code": "BEANR", "name": "Port of Antwerp-Bruges", "country": "Belgium", "type": "Seaport", "lat": 51.2194, "lon": 4.4025, "capacity_teu_annual": 13500000},
    {"code": "USLAX", "name": "Port of Los Angeles", "country": "USA", "type": "Seaport", "lat": 33.7432, "lon": -118.2673, "capacity_teu_annual": 10660000},
    {"code": "USNYC", "name": "Port of New York & New Jersey", "country": "USA", "type": "Seaport", "lat": 40.7128, "lon": -74.0060, "capacity_teu_annual": 9490000},
    {"code": "ZADUR", "name": "Port of Durban", "country": "South Africa", "type": "Transshipment Hub", "lat": -29.8587, "lon": 31.0218, "capacity_teu_annual": 2900000},
    {"code": "BRSSZ", "name": "Port of Santos", "country": "Brazil", "type": "Seaport", "lat": -23.9618, "lon": -46.3322, "capacity_teu_annual": 4800000},

    # Critical Maritime Chokepoints / Canals (4 Scenarios Covered)
    {"code": "EGPSD", "name": "Suez Canal (Port Said)", "country": "Egypt", "type": "Maritime Chokepoint", "lat": 31.2653, "lon": 32.3019, "capacity_teu_annual": 25000000},
    {"code": "DJJIB", "name": "Bab-el-Mandeb Strait (Djibouti)", "country": "Djibouti", "type": "Maritime Chokepoint", "lat": 11.8251, "lon": 42.5903, "capacity_teu_annual": 20000000},
    {"code": "AEHZM", "name": "Strait of Hormuz Chokepoint", "country": "Oman/Iran/UAE", "type": "Maritime Chokepoint", "lat": 26.5667, "lon": 56.2500, "capacity_teu_annual": 18000000},
    {"code": "PAPCN", "name": "Panama Canal Transit Hub", "country": "Panama", "type": "Maritime Chokepoint", "lat": 8.9824, "lon": -79.5199, "capacity_teu_annual": 14000000},
    {"code": "ZACPT", "name": "Cape of Good Hope Corridor", "country": "South Africa", "type": "Alternative Maritime Route", "lat": -34.3568, "lon": 18.4740, "capacity_teu_annual": 40000000},
    {"code": "MYPKG", "name": "Strait of Malacca (Port Klang)", "country": "Malaysia", "type": "Maritime Chokepoint", "lat": 3.0000, "lon": 101.4000, "capacity_teu_annual": 13700000},

    # Inland Intermodal Rail & Distribution Centers (DCs)
    {"code": "DEDUI", "name": "Duisburg Intermodal Rail Port", "country": "Germany", "type": "Inland Rail Hub", "lat": 51.4344, "lon": 6.7623, "capacity_teu_annual": 4000000},
    {"code": "USCHI", "name": "Chicago Intermodal Freight Center", "country": "USA", "type": "Inland Rail Hub", "lat": 41.8781, "lon": -87.6298, "capacity_teu_annual": 8000000},
    {"code": "ZAJNB", "name": "Johannesburg City Deep Dry Port", "country": "South Africa", "type": "Inland Rail Hub", "lat": -26.2041, "lon": 28.0473, "capacity_teu_annual": 1200000},
    {"code": "CNZZO", "name": "Zhengzhou Belt & Road Rail Hub", "country": "China", "type": "Inland Rail Hub", "lat": 34.7466, "lon": 113.6253, "capacity_teu_annual": 2500000}
]

# Business-weighted routes connecting the network
EDGES_DATA = [
    # ASIA TO MIDDLE EAST (Via Strait of Hormuz)
    {"from": "CNSHA", "to": "SGSIN", "mode": "OCEAN_LANE", "transit_time_hrs": 120, "cost_usd_per_teu": 450, "co2_kg_per_teu": 280, "reliability": 0.95, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "CNNGB", "to": "SGSIN", "mode": "OCEAN_LANE", "transit_time_hrs": 115, "cost_usd_per_teu": 430, "co2_kg_per_teu": 270, "reliability": 0.96, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "SGSIN", "to": "MYPKG", "mode": "OCEAN_LANE", "transit_time_hrs": 18, "cost_usd_per_teu": 120, "co2_kg_per_teu": 40, "reliability": 0.98, "is_chokepoint": True, "status": "OPERATIONAL"},
    
    # Strait of Hormuz / Persian Gulf Access
    {"from": "MYPKG", "to": "AEHZM", "mode": "OCEAN_LANE", "transit_time_hrs": 144, "cost_usd_per_teu": 520, "co2_kg_per_teu": 340, "reliability": 0.90, "is_chokepoint": True, "status": "OPERATIONAL"},
    {"from": "AEHZM", "to": "AEJEA", "mode": "OCEAN_LANE", "transit_time_hrs": 24, "cost_usd_per_teu": 130, "co2_kg_per_teu": 70, "reliability": 0.93, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "AEJEA", "to": "DJJIB", "mode": "OCEAN_LANE", "transit_time_hrs": 72, "cost_usd_per_teu": 380, "co2_kg_per_teu": 190, "reliability": 0.85, "is_chokepoint": False, "status": "OPERATIONAL"},

    # DIRECT ARABIAN SEA BYPASS (Used when Hormuz / Jebel Ali is Blocked)
    {"from": "MYPKG", "to": "DJJIB", "mode": "OCEAN_LANE", "transit_time_hrs": 180, "cost_usd_per_teu": 720, "co2_kg_per_teu": 430, "reliability": 0.94, "is_chokepoint": False, "status": "OPERATIONAL"},

    # RED SEA & SUEZ TO EUROPE
    {"from": "DJJIB", "to": "EGPSD", "mode": "CANAL_TRANSIT", "transit_time_hrs": 96, "cost_usd_per_teu": 1100, "co2_kg_per_teu": 310, "reliability": 0.88, "is_chokepoint": True, "status": "OPERATIONAL"},
    {"from": "EGPSD", "to": "NLRTM", "mode": "OCEAN_LANE", "transit_time_hrs": 192, "cost_usd_per_teu": 850, "co2_kg_per_teu": 520, "reliability": 0.94, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "EGPSD", "to": "BEANR", "mode": "OCEAN_LANE", "transit_time_hrs": 188, "cost_usd_per_teu": 830, "co2_kg_per_teu": 510, "reliability": 0.94, "is_chokepoint": False, "status": "OPERATIONAL"},

    # SUEZ/RED SEA BYPASS VIA CAPE OF GOOD HOPE (Used when Suez/Bab-el-Mandeb is Blocked)
    {"from": "SGSIN", "to": "ZADUR", "mode": "OCEAN_LANE", "transit_time_hrs": 288, "cost_usd_per_teu": 950, "co2_kg_per_teu": 780, "reliability": 0.98, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "ZADUR", "to": "ZACPT", "mode": "OCEAN_LANE", "transit_time_hrs": 48, "cost_usd_per_teu": 250, "co2_kg_per_teu": 130, "reliability": 0.97, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "ZACPT", "to": "NLRTM", "mode": "OCEAN_LANE", "transit_time_hrs": 336, "cost_usd_per_teu": 1450, "co2_kg_per_teu": 950, "reliability": 0.96, "is_chokepoint": False, "status": "OPERATIONAL"},

    # TRANS-PACIFIC (Asia to US West Coast)
    {"from": "CNSHA", "to": "USLAX", "mode": "OCEAN_LANE", "transit_time_hrs": 336, "cost_usd_per_teu": 1850, "co2_kg_per_teu": 920, "reliability": 0.91, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "KRPUS", "to": "USLAX", "mode": "OCEAN_LANE", "transit_time_hrs": 288, "cost_usd_per_teu": 1700, "co2_kg_per_teu": 840, "reliability": 0.93, "is_chokepoint": False, "status": "OPERATIONAL"},

    # TRANS-PANAMA (Asia to US East Coast)
    {"from": "CNSHA", "to": "PAPCN", "mode": "OCEAN_LANE", "transit_time_hrs": 456, "cost_usd_per_teu": 2600, "co2_kg_per_teu": 1350, "reliability": 0.82, "is_chokepoint": True, "status": "OPERATIONAL"},
    {"from": "PAPCN", "to": "USNYC", "mode": "OCEAN_LANE", "transit_time_hrs": 120, "cost_usd_per_teu": 750, "co2_kg_per_teu": 380, "reliability": 0.93, "is_chokepoint": False, "status": "OPERATIONAL"},

    # TRANS-ATLANTIC (Europe to US & South America)
    {"from": "NLRTM", "to": "USNYC", "mode": "OCEAN_LANE", "transit_time_hrs": 216, "cost_usd_per_teu": 1250, "co2_kg_per_teu": 640, "reliability": 0.95, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "NLRTM", "to": "BRSSZ", "mode": "OCEAN_LANE", "transit_time_hrs": 360, "cost_usd_per_teu": 1600, "co2_kg_per_teu": 980, "reliability": 0.92, "is_chokepoint": False, "status": "OPERATIONAL"},

    # INLAND INTERMODAL RAIL TERMINALS
    {"from": "NLRTM", "to": "DEDUI", "mode": "INLAND_RAIL", "transit_time_hrs": 8, "cost_usd_per_teu": 180, "co2_kg_per_teu": 25, "reliability": 0.99, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "BEANR", "to": "DEDUI", "mode": "INLAND_RAIL", "transit_time_hrs": 10, "cost_usd_per_teu": 195, "co2_kg_per_teu": 28, "reliability": 0.98, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "USLAX", "to": "USCHI", "mode": "INLAND_RAIL", "transit_time_hrs": 72, "cost_usd_per_teu": 850, "co2_kg_per_teu": 140, "reliability": 0.94, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "USNYC", "to": "USCHI", "mode": "INLAND_RAIL", "transit_time_hrs": 36, "cost_usd_per_teu": 520, "co2_kg_per_teu": 85, "reliability": 0.96, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "ZADUR", "to": "ZAJNB", "mode": "INLAND_RAIL", "transit_time_hrs": 24, "cost_usd_per_teu": 320, "co2_kg_per_teu": 65, "reliability": 0.91, "is_chokepoint": False, "status": "OPERATIONAL"},
    {"from": "CNSHA", "to": "CNZZO", "mode": "INLAND_RAIL", "transit_time_hrs": 18, "cost_usd_per_teu": 290, "co2_kg_per_teu": 45, "reliability": 0.97, "is_chokepoint": False, "status": "OPERATIONAL"}
]

def init_neo4j_schema():
    print("\n⚙️  Configuring Neo4j Constraints and Performance Indexes...")
    with driver.session() as session:
        session.run("CREATE CONSTRAINT location_code_uniq IF NOT EXISTS FOR (l:Location) REQUIRE l.code IS UNIQUE")
        session.run("CREATE INDEX location_type_idx IF NOT EXISTS FOR (l:Location) ON (l.type)")
        print("✅ Constraints & Indexes applied.")

def seed_database():
    print("\n📦 Seeding Enhanced Global Supply Chain & Maritime Nodes (including Hormuz)...")
    with driver.session() as session:
        cypher_nodes = """
        UNWIND $nodes AS n
        MERGE (l:Location {code: n.code})
        SET l.name = n.name,
            l.country = n.country,
            l.type = n.type,
            l.lat = n.lat,
            l.lon = n.lon,
            l.capacity_teu_annual = n.capacity_teu_annual
        """
        session.run(cypher_nodes, nodes=NODES_DATA)
        print(f"✅ Ingested {len(NODES_DATA)} Global Ports, Hubs, and Inland Terminals.")

        print("\n🌐 Constructing Multi-Modal Shipping Corridors & Bypass Topologies...")
        cypher_edges = """
        UNWIND $edges AS e
        MATCH (src:Location {code: e.from})
        MATCH (dst:Location {code: e.to})
        MERGE (src)-[r:CORRIDOR {mode: e.mode}]->(dst)
        SET r.transit_time_hrs = e.transit_time_hrs,
            r.cost_usd_per_teu = e.cost_usd_per_teu,
            r.co2_kg_per_teu = e.co2_kg_per_teu,
            r.reliability = e.reliability,
            r.is_chokepoint = e.is_chokepoint,
            r.status = e.status
        """
        session.run(cypher_edges, edges=EDGES_DATA)
        print(f"✅ Ingested {len(EDGES_DATA)} Maritime & Inland corridors.")

def verify_and_report_metrics():
    print("\n" + "="*60)
    print("📊 UPDATED GLOBAL LOGISTICS KNOWLEDGE GRAPH SUMMARY")
    print("="*60)
    with driver.session() as session:
        res_nodes = session.run("MATCH (l:Location) RETURN count(l) AS count").single()['count']
        res_edges = session.run("MATCH ()-[r:CORRIDOR]->() RETURN count(r) AS count").single()['count']
        res_chokepoints = session.run("MATCH ()-[r:CORRIDOR {is_chokepoint: true}]->() RETURN count(r) AS count").single()['count']
        
        print(f"• Total Logistical Locations:  {res_nodes}")
        print(f"• Total Active Corridors:       {res_edges}")
        print(f"• Critical Chokepoints Tracked: {res_chokepoints}")
        
        print("\n🔍 Middle East & Arabian Sea Corridors (Hormuz & Bypass):")
        sample_query = """
        MATCH (src:Location)-[r:CORRIDOR]->(dst:Location)
        WHERE src.code IN ['MYPKG', 'AEHZM', 'AEJEA']
        RETURN src.name AS Origin, r.mode AS Mode, 
               dst.name AS Destination, r.transit_time_hrs AS Hours, 
               r.cost_usd_per_teu AS CostUSD, r.is_chokepoint AS Chokepoint
        """
        results = session.run(sample_query)
        for record in results:
            choke_badge = "⚠️ CHOKEPOINT" if record['Chokepoint'] else "✅ Open Lane"
            print(f"  • {record['Origin']} ➔ {record['Destination']} ({record['Hours']}h, ${record['CostUSD']}/TEU) [{choke_badge}]")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        init_neo4j_schema()
        seed_database()
        verify_and_report_metrics()
        print("🎉 Neo4j Knowledge Graph successfully updated with 4-Scenario Chokepoint Support!")
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
    finally:
        driver.close()