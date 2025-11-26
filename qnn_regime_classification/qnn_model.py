import pennylane as qml
from pennylane import numpy as np

n_qubits = 3
n_classes = 3
dev = qml.device("default.qubit", wires=n_qubits)

@qml.qnode(dev)
def quantum_classifier(inputs, weights):
    qml.templates.AngleEmbedding(inputs, wires=range(n_qubits))
    qml.templates.StronglyEntanglingLayers(weights, wires=range(n_qubits))
    return [qml.expval(qml.PauliZ(i)) for i in range(n_qubits)]

def predict_class(logits):
    return int(np.argmax(logits + 1e-4))  # Bias towards max

def get_weight_shape(n_layers=2):
    return (n_layers, n_qubits, 3)
