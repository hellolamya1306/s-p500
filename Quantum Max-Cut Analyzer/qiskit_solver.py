from qiskit_optimization.applications.ising import max_cut
from qiskit_optimization.converters import QuadraticProgramToQubo
from qiskit_optimization import QuadraticProgram
from qiskit.algorithms import QAOA
from qiskit.primitives import Sampler
from qiskit_optimization.algorithms import MinimumEigenOptimizer

def solve_maxcut_qiskit(G):
    """Solve max-cut problem using QAOA (Qiskit)."""
    w = nx.adjacency_matrix(G).toarray()
    qubit_op, offset = max_cut.get_operator(w)
    
    qp = QuadraticProgram()
    for i in range(len(G.nodes)):
        qp.binary_var(name=f"x{i}")
    for i, j in G.edges():
        qp.minimize(linear=None, quadratic={(f"x{i}", f"x{j}"): -G[i][j]['weight']})
    
    qaoa = QAOA(sampler=Sampler(), reps=1)
    optimizer = MinimumEigenOptimizer(qaoa)
    result = optimizer.solve(qp)
    return result
