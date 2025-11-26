import numpy as np
import networkx as nx

def correlation_to_graph(corr_matrix, threshold=0.5):
    """Convert correlation matrix to weighted graph."""
    G = nx.Graph()
    n = len(corr_matrix)
    for i in range(n):
        for j in range(i + 1, n):
            weight = abs(corr_matrix[i, j])
            if weight >= threshold:
                G.add_edge(i, j, weight=weight)
    return G

def get_qubo_from_graph(G):
    """Return QUBO dict for Max-Cut."""
    Q = {}
    for i, j in G.edges():
        w = G[i][j]['weight']
        Q[(i, i)] = Q.get((i, i), 0) - w
        Q[(j, j)] = Q.get((j, j), 0) - w
        Q[(i, j)] = Q.get((i, j), 0) + 2 * w
    return Q
