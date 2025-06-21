import json
import networkx as nx # pip install networkx
import matplotlib.pyplot as plt # pip install matplotlib (for basic visualization)

def load_unique_properties(filepath):
    """Loads unique properties from a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_knowledge_graph(properties):
    """Builds a NetworkX graph from property data."""
    G = nx.DiGraph() # Directed graph

    for prop_data in properties:
        prop_id = prop_data.get('id')
        if not prop_id:
            continue

        # Add Property Node - ensure all attributes are strings for GML compatibility
        G.add_node(prop_id,
                   type="Property",
                   title=str(prop_data.get('title', '')),
                   price=str(prop_data.get('price', '')),
                   url=str(prop_data.get('url', '')),
                   bedrooms=str(prop_data.get('bedrooms', '')),
                   bathrooms=str(prop_data.get('bathrooms', '')),
                   areaSqFt=str(prop_data.get('areaSqFt', '')),
                   latitude=str(prop_data.get('latitude', '')),
                   longitude=str(prop_data.get('longitude', '')))

        # Add Location Node and "LOCATED_IN" relationship
        location_name = prop_data.get('full_address') or prop_data.get('location_raw') or prop_data.get('location', '')
        if location_name:
            # Use a simpler, normalized location name for the node if full address is too long/varied
            simple_location_name = " ".join(location_name.lower().split(',')[:1]).strip() # e.g., "Kathmandu"
            if simple_location_name:
                G.add_node(simple_location_name, type="Location")
                G.add_edge(prop_id, simple_location_name, relation="LOCATED_IN")

        # Add Amenities Nodes and "HAS_AMENITY" relationship
        amenities = prop_data.get('extracted_amenities', [])
        for amenity in amenities:
            if amenity:  # Only add non-empty amenities
                amenity_node_id = f"Amenity:{amenity}" # Unique ID for amenity node
                G.add_node(amenity_node_id, type="Amenity", name=str(amenity))
                G.add_edge(prop_id, amenity_node_id, relation="HAS_AMENITY")

        # Example: Infer Property Type from title/description
        property_type = "House" # Default
        title = prop_data.get('title', '').lower()
        if "apartment" in title or "flat" in title:
            property_type = "Apartment"
        elif "condo" in title:
            property_type = "Condominium"
        elif "villa" in title:
            property_type = "Villa"
        elif "land" in title:
            property_type = "Land"
        
        type_node_id = f"Type:{property_type}"
        G.add_node(type_node_id, type="PropertyType", name=property_type)
        G.add_edge(prop_id, type_node_id, relation="IS_TYPE_OF")

        # Add source information
        source = prop_data.get('source', '')
        if source:
            source_node_id = f"Source:{source}"
            G.add_node(source_node_id, type="Source", name=str(source))
            G.add_edge(prop_id, source_node_id, relation="FROM_SOURCE")

    return G

def save_graph_gml(graph, filepath):
    """Saves the graph to a GML file."""
    # Clean the graph to ensure all attributes are strings
    clean_graph = nx.DiGraph()
    
    # Copy nodes with string attributes
    for node, attrs in graph.nodes(data=True):
        clean_attrs = {}
        for key, value in attrs.items():
            if value is None:
                clean_attrs[key] = ""
            else:
                clean_attrs[key] = str(value)
        clean_graph.add_node(node, **clean_attrs)
    
    # Copy edges
    for u, v, attrs in graph.edges(data=True):
        clean_attrs = {}
        for key, value in attrs.items():
            if value is None:
                clean_attrs[key] = ""
            else:
                clean_attrs[key] = str(value)
        clean_graph.add_edge(u, v, **clean_attrs)
    
    nx.write_gml(clean_graph, filepath)
    print(f"Knowledge graph saved to {filepath} in GML format.")

def visualize_graph(graph):
    """Basic visualization of the knowledge graph (for small graphs)."""
    plt.figure(figsize=(12, 12))
    pos = nx.spring_layout(graph, k=0.15, iterations=20) # Positions nodes for visualization

    node_colors = []
    for node_id in graph.nodes():
        node_type = graph.nodes[node_id].get('type', 'Unknown')
        if node_type == "Property":
            node_colors.append('skyblue')
        elif node_type == "Location":
            node_colors.append('lightcoral')
        elif node_type == "Amenity":
            node_colors.append('lightgreen')
        elif node_type == "PropertyType":
            node_colors.append('lightsalmon')
        else:
            node_colors.append('lightgray')

    nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=2000, alpha=0.9)
    nx.draw_networkx_edges(graph, pos, width=1.0, alpha=0.5, edge_color='gray')
    nx.draw_networkx_labels(graph, pos, font_size=8, font_weight='bold')

    edge_labels = nx.get_edge_attributes(graph, 'relation')
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_color='red', font_size=7)

    plt.title("Real Estate Knowledge Graph")
    plt.axis('off')
    plt.show()


def main():
    input_filepath = '../data/unique_properties.json'
    output_gml_filepath = '../data/real_estate_kg.gml'

    properties = load_unique_properties(input_filepath)
    print(f"Building knowledge graph from {len(properties)} unique properties...")

    kg = build_knowledge_graph(properties)
    print(f"Knowledge graph built with {kg.number_of_nodes()} nodes and {kg.number_of_edges()} edges.")

    save_graph_gml(kg, output_gml_filepath)

    # For very small graphs, we can try to visualize. For larger, use dedicated tools.
    # if kg.number_of_nodes() < 50: # Avoid visualizing excessively large graphs
    #     visualize_graph(kg)
    # else:
    #     print("Graph is too large for simple matplotlib visualization. Use Gephi or similar.")

main()