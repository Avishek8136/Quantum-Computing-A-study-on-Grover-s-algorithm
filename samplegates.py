# Import necessary libraries
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt

# Create a simulator
sim = AerSimulator()

# -------------------------
# 1️⃣ SUPERPOSITION (Hadamard Gate)
# -------------------------
qc1 = QuantumCircuit(1, 1)
qc1.h(0)                     # Put qubit 0 into superposition
qc1.measure(0, 0)
print("Superposition Circuit:")
print(qc1.draw())

result1 = sim.run(qc1, shots=1000000).result()
counts1 = result1.get_counts()
plot_histogram(counts1, title="Hadamard Gate (Superposition)")
plt.show()

# -------------------------
# 2️⃣ PAULI-X (NOT) Gate
# -------------------------
qc2 = QuantumCircuit(1, 1)
qc2.x(0)                     # Flip |0⟩ -> |1⟩
qc2.measure(0, 0)
print("Pauli-X Circuit:")
print(qc2.draw())

result2 = sim.run(qc2, shots=1000).result()
counts2 = result2.get_counts()
plot_histogram(counts2, title="Pauli-X Gate")
plt.show()

# -------------------------
# 3️⃣ PAULI-Y Gate
# -------------------------
qc3 = QuantumCircuit(1, 1)
qc3.y(0)                     # Adds phase and flips qubit
qc3.measure(0, 0)
print("Pauli-Y Circuit:")
print(qc3.draw())

result3 = sim.run(qc3, shots=1000).result()
counts3 = result3.get_counts()
plot_histogram(counts3, title="Pauli-Y Gate")
plt.show()

# -------------------------
# 4️⃣ PAULI-Z Gate
# -------------------------
qc4 = QuantumCircuit(1, 1)
qc4.x(0)                     # Flip |0⟩ -> |1⟩ to see phase effect
qc4.h(0)                     # Create superposition first
qc4.z(0)                     # Apply Z (flips phase of |1⟩)
qc4.h(0)                     # Bring back to measurement basis
qc4.measure(0, 0)
print("Pauli-Z Circuit:")
print(qc4.draw())

result4 = sim.run(qc4, shots=1000).result()
counts4 = result4.get_counts()
plot_histogram(counts4, title="Pauli-Z Gate")
plt.show()

# -------------------------
# 5️⃣ CNOT + ENTANGLEMENT
# -------------------------
qc5 = QuantumCircuit(2, 2)
qc5.h(0)                     # Create superposition on qubit 0
qc5.cx(0, 1)                 # Entangle qubit 1 with qubit 0
qc5.measure([0, 1], [0, 1])
print("CNOT + Entanglement Circuit:")
print(qc5.draw())

result5 = sim.run(qc5, shots=1000).result()
counts5 = result5.get_counts()
plot_histogram(counts5, title="CNOT Entanglement")
plt.show()
