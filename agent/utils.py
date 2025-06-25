def render_graph_to_image(graph, output_path="graph.png",):
    img = graph.get_graph().draw_mermaid_png()
    with open(output_path, "wb") as f:
        f.write(img)
    print(f"Graph image saved to {output_path}")