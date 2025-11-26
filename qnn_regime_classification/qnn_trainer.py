from qnn_model import quantum_classifier, get_weight_shape, predict_class
from regime_data import generate_regime_data
from pennylane.optimize import AdamOptimizer
from pennylane import numpy as np

def train_qnn(epochs=50, n_layers=2, lr=0.1):
    X, y = generate_regime_data()
    weights = np.random.randn(*get_weight_shape(n_layers))
    opt = AdamOptimizer(lr)

    def cost(weights):
        loss = 0
        for xi, yi in zip(X, y):
            logits = quantum_classifier(xi, weights)
            probs = (logits + 1) / 2
            loss += -np.log(probs[yi] + 1e-6)
        return loss / len(X)

    for epoch in range(epochs):
        weights = opt.step(cost, weights)

    preds = np.array([predict_class(quantum_classifier(xi, weights)) for xi in X])
    acc = np.mean(preds == y)
    return acc, weights
