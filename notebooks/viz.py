"""Notebook-only visualization helpers.

Impure by design (matplotlib + networkx) and therefore kept OUT of sim/. These
read Scenario/WorldState but never mutate them.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import networkx as nx


def _resource_summary(stock_row, resources) -> str:
    parts = [f"{resources[i]}:{int(v)}" for i, v in enumerate(stock_row) if v != 0]
    return ", ".join(parts) if parts else "(empty)"


def build_graph(scenario) -> nx.DiGraph:
    G = nx.DiGraph()
    for lid in scenario.location_ids:
        G.add_node(lid)
    for i, dsts in enumerate(scenario.destinations):
        for d in dsts:
            G.add_edge(scenario.location_ids[i], scenario.location_ids[d])
    # layer = topological generation, for a clean upstream->downstream layout
    for layer, generation in enumerate(nx.topological_generations(G)):
        for node in generation:
            G.nodes[node]["layer"] = layer
    return G


def draw_world(world, scenario, ax=None, title=None):
    G = build_graph(scenario)
    pos = nx.multipartite_layout(G, subset_key="layer")
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))
    labels = {
        lid: f"{lid}\n{_resource_summary(world.stock[i], scenario.resources)}"
        for i, lid in enumerate(scenario.location_ids)
    }
    nx.draw_networkx_edges(G, pos, ax=ax, arrows=True, arrowsize=22,
                           edge_color="#888", width=1.5, node_size=6000)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color="#cfe8ff",
                           node_size=6000, edgecolors="#4a90d9", linewidths=1.5)
    nx.draw_networkx_labels(G, pos, labels=labels, ax=ax, font_size=8)
    ax.set_title(title if title is not None else f"tick {world.tick}")
    ax.axis("off")
    return ax


def _priority_label(world, scenario, i, t) -> str:
    """Transform name, annotated with its accumulated nudge delta if non-zero."""
    name = scenario.transform_names[t]
    delta = int(world.priority[i, t])
    return f"{name}({delta:+d})" if delta else name


def summarize(world, scenario) -> str:
    lines = [f"tick {world.tick}"]
    for i, lid in enumerate(scenario.location_ids):
        # order is derived from the persistent priority scores, highest first
        order = " > ".join(_priority_label(world, scenario, i, t) for t in world.order(i))
        lines.append(f"  {lid}: {_resource_summary(world.stock[i], scenario.resources)}")
        lines.append(f"      priority: {order}")
    lines.append("  TOTALS: " + _resource_summary(world.stock.sum(axis=0), scenario.resources))
    return "\n".join(lines)
