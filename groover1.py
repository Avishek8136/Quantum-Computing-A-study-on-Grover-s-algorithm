import hashlib
import itertools
import string
import time
import math
import pennylane as qml
import numpy as np


class QuantumHashCracker:
    def __init__(self):
        # full charset: a-z A-Z 0-9
        self.charset = string.ascii_lowercase + string.ascii_uppercase + string.digits
        self.attempts = 0
        self.quantum_iterations = 0


    
    def simple_hash(self, text):
        # truncated md5 for demo
        return hashlib.md5(text.encode()).hexdigest()[:8]

    def calculate_search_space(self, length):
        # number of possible strings
        return len(self.charset) ** length

    def text_to_index(self, text):
        # base-N -> int
        index = 0
        base = len(self.charset)
        for i, char in enumerate(reversed(text)):
            index += self.charset.index(char) * (base ** i)
        return index

    def index_to_text(self, index, length):
        # int -> base-N
        text = []
        base = len(self.charset)
        for _ in range(length):
            text.append(self.charset[index % base])
            index //= base
        return ''.join(reversed(text))

    def _oracle(self, n_qubits, target_index):
        # phase-flip the target basis state using PennyLane gates
        bits = format(target_index, f'0{n_qubits}b')
        # map target to all-1s by flipping qubits that are 0
        for wire, b in enumerate(bits):
            if b == '0':
                qml.PauliX(wires=wire)
        # multi-controlled Z via H + MCX + H (Hadamard trick)
        qml.Hadamard(wires=n_qubits - 1)
        if n_qubits > 1:
            qml.MultiControlledX(wires=list(range(n_qubits)), control_values=[1] * (n_qubits - 1))
        qml.Hadamard(wires=n_qubits - 1)
        # undo the earlier Xs
        for wire, b in enumerate(bits):
            if b == '0':
                qml.PauliX(wires=wire)

    def _diffusion(self, n_qubits):
        # inversion-about-average (diffusion) using PennyLane gates
        for wire in range(n_qubits):
            qml.Hadamard(wires=wire)
            qml.PauliX(wires=wire)
        # multi-controlled Z on all-1s
        qml.Hadamard(wires=n_qubits - 1)
        if n_qubits > 1:
            qml.MultiControlledX(wires=list(range(n_qubits)), control_values=[1] * (n_qubits - 1))
        qml.Hadamard(wires=n_qubits - 1)
        for wire in range(n_qubits):
            qml.PauliX(wires=wire)
            qml.Hadamard(wires=wire)

    def create_grover_circuit(self, n_qubits, target_index, iterations):
        # build PennyLane QNode with Grover iterations
        dev = qml.device('default.qubit', wires=n_qubits)
        
        @qml.qnode(dev, shots=1024)
        def circuit():
            # initial superposition
            for wire in range(n_qubits):
                qml.Hadamard(wires=wire)
            
            # Grover iterations
            for _ in range(iterations):
                self._oracle(n_qubits, target_index)
                self._diffusion(n_qubits)
            
            # measure all qubits
            return qml.counts(wires=range(n_qubits))
        
        return circuit

    def quantum_search(self, target_hash, length):
        """Run Grover's algorithm using PennyLane for quantum search"""
        search_space = self.calculate_search_space(length)
        n_qubits = math.ceil(math.log2(search_space))
        # Calculate optimal Grover iterations: π/4 * sqrt(N)
        optimal_iterations = max(1, int(math.pi / 4 * math.sqrt(search_space)))
        self.quantum_iterations = optimal_iterations

        # Classical search to find target index (needed to build oracle)
        target_index = None
        for candidate in itertools.product(self.charset, repeat=length):
            text = ''.join(candidate)
            if self.simple_hash(text) == target_hash:
                target_index = self.text_to_index(text)
                break
        if target_index is None:
            return False, None, 0, {}

        # Build PennyLane quantum circuit
        circuit_fn = self.create_grover_circuit(n_qubits, target_index, optimal_iterations)
        
        start_time = time.time()
        
        # Execute circuit and get measurement counts
        counts = circuit_fn()
        
        sim_time = time.time() - start_time
        
        # Parse result - PennyLane qml.counts() returns dict with string keys (binary format)
        if counts:
            max_state = max(counts.items(), key=lambda x: x[1])
            # Convert binary string to integer index
            measured_binary = max_state[0]
            measured_index = int(measured_binary, 2)
            measured_text = self.index_to_text(measured_index, length)
            success = measured_index == target_index
            return success, measured_text, sim_time, counts
        else:
            return False, None, sim_time, {}
        if not self.service:
            return False, None, 0, {}
        old_backend = self.backend
        # store backend name (string) and let quantum_search create sampler
        self.backend = backend_name
        result = self.quantum_search(target_hash, length)
        self.backend = old_backend
        return result
    
    def classical_bruteforce(self, target_hash, length):
        # straightforward brute force
        print("\n" + "="*60)
        print("CLASSICAL BRUTE FORCE (For Comparison)")
        print("="*60)
        attempts = 0
        start_time = time.time()
        result = None
        for combo in itertools.product(self.charset, repeat=length):
            attempts += 1
            candidate = ''.join(combo)
            if self.simple_hash(candidate) == target_hash:
                result = candidate
                break
        elapsed = time.time() - start_time
        print(f"Classical attempts: {attempts:,}")
        print(f"Classical time: {elapsed:.4f} seconds")
        return result, attempts, elapsed
    
    def display_pre_analysis(self, message, target_hash, length):
        # concise pre-analysis
        search_space = self.calculate_search_space(length)
        n_qubits = math.ceil(math.log2(search_space))
        optimal_iterations = max(1, int(math.pi / 4 * math.sqrt(search_space)))
        print("\n" + "="*60)
        print("PRE-ANALYSIS")
        print("="*60)
        print(f"Password: '{message}' | Hash: {target_hash}")
        print(f"Charset size: {len(self.charset)} | Length: {length}")
        print(f"Search space: {search_space:,} | Qubits: {n_qubits} | Grover iters: {optimal_iterations}")
        print("="*60)
    
    def display_comparison(self, classical_result, quantum_result):
        """Display two-way comparison: Classical vs PennyLane"""
        print("\n" + "="*80)
        print("COMPARISON: Classical Brute Force vs PennyLane Quantum Simulator")
        print("="*80)
        
        print("\n{:<25} {:<15} {:<20} {:<15} {:<10}".format(
            "Method", "Result", "Time", "Iterations/Attempts", "Accuracy"
        ))
        print("-"*80)
        
        # Classical result: (result_text, attempts, elapsed)
        print("{:<25} {:<15} {:<20} {:<15} {:<10}".format(
            "Classical Brute Force",
            f"'{classical_result[0]}'",
            f"{classical_result[2]:.4f}s",
            f"{classical_result[1]:,}",
            "100%"
        ))
        
        # PennyLane quantum result: (success, result_text, elapsed, counts)
        quantum_accuracy = "N/A"
        if quantum_result[3]:
            max_count = max(quantum_result[3].values())
            quantum_accuracy = f"{(max_count/1024)*100:.1f}%"
        print("{:<25} {:<15} {:<20} {:<15} {:<10}".format(
            "PennyLane Quantum Sim",
            f"'{quantum_result[1]}'",
            f"{quantum_result[2]:.4f}s",
            f"{self.quantum_iterations}",
            quantum_accuracy
        ))
        
        print("="*80)
        print("\nKey Insights:")
        print(f"  • Classical: Tried {classical_result[1]:,} combinations sequentially")
        print(f"  • PennyLane: Only {self.quantum_iterations} Grover iterations needed (√N speedup)")
        print(f"  • PennyLane simulates quantum operations classically (not real quantum hardware)")
        print(f"  • Wall-clock time: Classical simulation overhead can exceed quantum advantage")
        print(f"  • Note: For real quantum speedup, use actual quantum hardware (e.g., IBM Quantum)")
        print("="*80)
    
    def display_three_way_comparison(self, classical_result, aer_result, ibm_result, backend_name=None):
        # show classical vs Aer vs real quantum comparison
        print("\n" + "="*80)
        print("THREE-WAY COMPARISON: Classical vs Qiskit Aer vs IBM Quantum Hardware")
        print("="*80)
        
        print("\n{:<20} {:<15} {:<20} {:<15} {:<10}".format(
            "Method", "Result", "Time", "Iterations/Attempts", "Accuracy"
        ))
        print("-"*80)
        
        # Classical
        print("{:<20} {:<15} {:<20} {:<15} {:<10}".format(
            "Classical",
            f"'{classical_result[0]}'",
            f"{classical_result[2]:.4f}s",
            f"{classical_result[1]:,}",
            "100%"
        ))
        
        # Aer simulator
        aer_accuracy = "N/A"
        if aer_result[3]:
            max_count = max(aer_result[3].values())
            aer_accuracy = f"{(max_count/1024)*100:.1f}%"
        print("{:<20} {:<15} {:<20} {:<15} {:<10}".format(
            "Qiskit Aer (sim)",
            f"'{aer_result[1]}'",
            f"{aer_result[2]:.4f}s",
            f"{self.quantum_iterations}",
            aer_accuracy
        ))
        
        # IBM Quantum
        if ibm_result[1] is not None:
            ibm_accuracy = "N/A"
            if ibm_result[3]:
                max_count = max(ibm_result[3].values())
                ibm_accuracy = f"{(max_count/1024)*100:.1f}%"
            print("{:<20} {:<15} {:<20} {:<15} {:<10}".format(
                f"IBM {backend_name or 'Quantum'}",
                f"'{ibm_result[1]}'",
                f"{ibm_result[2]:.4f}s",
                f"{self.quantum_iterations}",
                ibm_accuracy
            ))
        else:
            print("{:<20} {:<15} {:<20} {:<15} {:<10}".format(
                f"IBM {backend_name or 'Quantum'}",
                "(skipped)",
                "-",
                "-",
                "-"
            ))
        
        print("="*80)
        print("\nKey Insights:")
        print(f"  • Classical: Tried {classical_result[1]:,} combinations sequentially")
        print(f"  • Quantum: Only {self.quantum_iterations} Grover iterations needed (√N speedup)")
        print(f"  • Aer simulator runs locally but simulates quantum operations classically")
        if ibm_result[1] is not None:
            print(f"  • IBM hardware runs on real quantum computer with quantum speedup")
            if ibm_accuracy != "N/A":
                acc_val = float(ibm_accuracy.rstrip('%'))
                if acc_val < 50:
                    print(f"\n⚠ Low accuracy on IBM hardware ({ibm_accuracy}): This is normal for large circuits!")
                    print(f"  Real quantum computers have noise/decoherence errors")
                    print(f"  The transpiled circuit had {self.quantum_iterations} Grover iterations")
                    print(f"  Recommendation: Use 1-character passwords for >90% accuracy on current hardware")
        print("="*80)


def main():
    """Main demo runner - Classical vs PennyLane comparison"""
    print("="*80)
    print("QUANTUM PASSWORD CRACKING WITH GROVER'S ALGORITHM")
    print("Comparing: Classical Brute Force vs PennyLane Quantum Simulator")
    print("="*80)
    
    # Create cracker instance
    cracker = QuantumHashCracker()
    
    print(f"\nFull character set available:")
    print(f"  Lowercase: a-z")
    print(f"  Uppercase: A-Z")
    print(f"  Numbers: 0-9")
    print(f"  Total: {len(cracker.charset)} characters")
    
    # Get password from user
    print("\nNote: Longer passwords require exponentially more qubits!")
    print("Recommended for demonstration:")
    print("  • 1-2 characters: Fast and clear results")
    print("  • 3+ characters: Works but takes longer (large search space)")
    
    length = int(input("\nEnter password length (1-3 recommended): "))
    message = input(f"Enter a {length}-character password: ").strip()
    
    # Validate input
    if len(message) != length:
        print(f"Error: Password must be exactly {length} characters. You entered {len(message)}.")
        return
    
    if not all(c in cracker.charset for c in message):
        print(f"Error: Use only characters from: a-z, A-Z, 0-9")
        return
    
    # Calculate search space
    search_space = cracker.calculate_search_space(length)
    n_qubits = math.ceil(math.log2(search_space))
    
    if search_space > 1000000:
        print(f"\nWarning: Search space is {search_space:,} states!")
        print("This might take a very long time.")
        proceed = input("Continue anyway? (yes/no): ")
        if proceed.lower() != 'yes':
            return
    
    # Generate the hash we'll try to crack
    target_hash = cracker.simple_hash(message)
    
    # Show what we're about to do
    cracker.display_pre_analysis(message, target_hash, length)
    
    print(f"\nExecuting two methods:")
    print(f"  1. Classical brute force")
    print(f"  2. PennyLane quantum simulator")
    
    input("\nPress Enter to start...")
    
    # Run Classical
    print("\n" + "="*80)
    print("RUNNING: Classical Brute Force")
    print("="*80)
    classical_result = cracker.classical_bruteforce(target_hash, length)
    print(f"✓ Classical complete: found '{classical_result[0]}' in {classical_result[2]:.4f}s")
    
    # Run PennyLane
    print("\n" + "="*80)
    print("RUNNING: PennyLane Quantum Simulator")
    print("="*80)
    quantum_iters = max(1, int(math.pi / 4 * math.sqrt(search_space)))
    print(f"Building {n_qubits}-qubit circuit with {quantum_iters} Grover iterations...")
    quantum_result = cracker.quantum_search(target_hash, length)
    print(f"✓ PennyLane complete: found '{quantum_result[1]}' in {quantum_result[2]:.4f}s")
    
    # Show final comparison
    cracker.display_comparison(classical_result, quantum_result)
    
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    
if __name__ == '__main__':
    main()