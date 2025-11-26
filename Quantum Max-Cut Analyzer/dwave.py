import dwave_networkx as dnx
import dimod

def solve_maxcut_dwave(G):
    """Solve Max-Cut using D-Wave simulated annealing."""
    Q = {}
    for i, j in G.edges():
        Q[(i, j)] = G[i][j]['weight']
    bqm = dimod.BinaryQuadraticModel.from_qubo(Q)
    sampler = dimod.SimulatedAnnealingSampler()
    sampleset = sampler.sample(bqm, num_reads=100)
    best_sample = sampleset.first.sample
    return best_sample
