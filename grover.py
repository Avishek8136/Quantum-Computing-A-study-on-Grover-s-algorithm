import hashlib
import itertools
import string
import time
import math
import os
from dotenv import load_dotenv
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler
from qiskit.circuit.library import MCXGate
import numpy as np


class QuantumHashCracker:
    def __init__(self):
        # full charset: a-z A-Z 0-9
        self.charset = string.ascii_lowercase + string.ascii_uppercase + string.digits
        self.attempts = 0
        self.quantum_iterations = 0
        self.service = None  # IBM Quantum service
        self.backend = None  # selected backend (Aer or IBM)
        
        # auto-load credentials from .env
        load_dotenv()
        token = os.getenv('IBM_QUANTUM_TOKEN')
        instance = os.getenv('IBM_QUANTUM_INSTANCE')
        
        if token and instance:
            print("✓ Loading IBM Quantum credentials from .env")
            print(f"  Token: {token[:20]}..." if len(token) > 20 else f"  Token: {token}")
            print(f"  Instance: {instance[:60]}..." if len(instance) > 60 else f"  Instance: {instance}")
            self.configure_ibm_runtime(token, instance, silent=False)
        else:
            if not token:
                print("⚠ IBM_QUANTUM_TOKEN not found in .env")
            if not instance:
                print("⚠ IBM_QUANTUM_INSTANCE not found in .env")

    def configure_ibm_runtime(self, token, instance=None, silent=False):
        # set up IBM Quantum credentials (CRN format for ibm_cloud channel)
        try:
            # CRN format uses ibm_cloud channel
            QiskitRuntimeService.save_account(
                channel="ibm_cloud", 
                token=token, 
                instance=instance, 
                overwrite=True
            )
            # initialize service
            self.service = QiskitRuntimeService(channel="ibm_cloud")
            if not silent:
                print("✓ IBM Quantum credentials configured")
                print(f"✓ Connected to instance: {instance}")
        except Exception as e:
            if not silent:
                print(f"⚠ Warning: Could not configure IBM Runtime: {e}")
                print("Trying to connect with existing saved account...")
            # try to use existing saved credentials
            try:
                self.service = QiskitRuntimeService(channel="ibm_cloud")
                if not silent:
                    print("✓ Connected using saved credentials")
            except Exception as e2:
                if not silent:
                    print(f"✗ Failed: {e2}")
                    print("Falling back to Aer simulator only")
    
    def select_backend(self, backend_name="aer_simulator"):
        # choose backend: 'aer_simulator' or IBM device like 'ibm_brisbane'
        if backend_name == "aer_simulator":
            self.backend = AerSimulator()
            print(f"✓ Using Aer simulator (local)")
        elif self.service:
            # store backend name (string) for IBM Runtime; service will create samplers
            self.backend = backend_name
            print(f"✓ Using IBM backend: {backend_name}")
        else:
            print("Error: IBM service not configured. Using Aer simulator.")
            self.backend = AerSimulator()
    
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

    def _oracle(self, qc, n_qubits, target_index):
        # phase-flip the target basis state |target_index> using Qiskit gates
        bits = format(target_index, f'0{n_qubits}b')
        # map target to all-1s by flipping qubits that are 0 in target
        for qubit, b in enumerate(bits):
            if b == '0':
                qc.x(qubit)
        # multi-controlled Z via H + MCX + H (Hadamard trick)
        qc.h(n_qubits - 1)
        if n_qubits > 1:
            qc.mcx(list(range(n_qubits - 1)), n_qubits - 1)
        qc.h(n_qubits - 1)
        # undo the earlier Xs
        for qubit, b in enumerate(bits):
            if b == '0':
                qc.x(qubit)

    def _diffusion(self, qc, n_qubits):
        # inversion-about-average (diffusion) using Qiskit gates
        for qubit in range(n_qubits):
            qc.h(qubit)
            qc.x(qubit)
        # multi-controlled Z on all-1s state
        qc.h(n_qubits - 1)
        if n_qubits > 1:
            qc.mcx(list(range(n_qubits - 1)), n_qubits - 1)
        qc.h(n_qubits - 1)
        for qubit in range(n_qubits):
            qc.x(qubit)
            qc.h(qubit)

    def create_grover_circuit(self, n_qubits, target_index, iterations):
        # build Qiskit circuit with Grover iterations
        qc = QuantumCircuit(n_qubits, n_qubits)
        
        # initial superposition
        for qubit in range(n_qubits):
            qc.h(qubit)
        
        # Grover iterations
        for _ in range(iterations):
            self._oracle(qc, n_qubits, target_index)
            self._diffusion(qc, n_qubits)
        
        # measure all qubits
        qc.measure(range(n_qubits), range(n_qubits))
        return qc

    def quantum_search(self, target_hash, length):
        # run Grover on Qiskit backend (Aer or IBM Runtime)
        search_space = self.calculate_search_space(length)
        n_qubits = math.ceil(math.log2(search_space))
        # ensure at least 1 iteration (avoid zero for small search spaces)
        optimal_iterations = max(1, int(math.pi / 4 * math.sqrt(search_space)))
        self.quantum_iterations = optimal_iterations

        # classical search to get target index for oracle construction
        target_index = None
        for candidate in itertools.product(self.charset, repeat=length):
            text = ''.join(candidate)
            if self.simple_hash(text) == target_hash:
                target_index = self.text_to_index(text)
                break
        if target_index is None:
            return False, None, 0, {}

        # build circuit
        qc = self.create_grover_circuit(n_qubits, target_index, optimal_iterations)
        
        # ensure backend is set
        if self.backend is None:
            self.backend = AerSimulator()
        
        start_time = time.time()
        
        # execute on backend (Aer or IBM Runtime)
        if isinstance(self.backend, AerSimulator):
            # local Aer execution
            transpiled = transpile(qc, self.backend)
            job = self.backend.run(transpiled, shots=1024)
            result = job.result()
            counts = result.get_counts()
        else:
            # IBM Runtime execution using primitives interface
            backend_name = self.backend
            
            try:
                # Get backend object from service
                backend_obj = self.service.backend(backend_name)
                print(f"✓ Retrieved backend: {backend_name}")
                
                # Check if circuit is too large for hardware
                if n_qubits > 20 or optimal_iterations > 10:
                    print(f"⚠ Warning: Circuit may be too large for reliable results on current hardware")
                    print(f"   Qubits: {n_qubits}, Iterations: {optimal_iterations}")
                    print(f"   Consider using a 2-character password for better accuracy")
                
                # Transpile circuit for IBM hardware (required as of March 2024)
                print(f"⏳ Transpiling circuit for {backend_name}...")
                qc_transpiled = transpile(qc, backend=backend_obj, optimization_level=3)
                print(f"✓ Circuit transpiled (depth: {qc_transpiled.depth()}, gates: {qc_transpiled.size()})")
                
                # Warn if transpiled circuit is very large
                if qc_transpiled.size() > 100000:
                    print(f"⚠ Warning: Transpiled circuit has {qc_transpiled.size()} gates!")
                    print(f"   Real quantum hardware will have high error rates with this many gates")
                    print(f"   Accuracy will be significantly reduced")
                
                # Create Sampler in batch mode (error mitigation options depend on plan)
                try:
                    # Try with default options (open plan may not support all mitigation)
                    sampler = Sampler(mode=backend_obj)
                    print(f"✓ Created Sampler in batch mode")
                except Exception as sampler_err:
                    print(f"⚠ Sampler creation failed: {sampler_err}")
                    raise
                
                # Submit transpiled job
                job = sampler.run([qc_transpiled], shots=1024)
                print(f"✓ Job submitted (ID: {job.job_id()}), waiting for result...")
                print(f"⏳ Waiting for IBM quantum computer ..")
                
                # Wait indefinitely for result
                result = job.result(timeout=None)
                print(f"✓ Job complete!")
                
                # Parse IBM Runtime result format
                print(f"ℹ Parsing result...")
                try:
                    # SamplerV2 result format: PrimitiveResult with pub_results
                    pub_result = result[0]
                    
                    # Get counts from DataBin
                    if hasattr(pub_result, 'data'):
                        # New format: pub_result.data has measurement results
                        meas_data = pub_result.data
                        
                        # Try different attribute names for measurements
                        if hasattr(meas_data, 'meas'):
                            counts = meas_data.meas.get_counts()
                        elif hasattr(meas_data, 'c'):
                            counts = meas_data.c.get_counts()
                        else:
                            # Fallback: try to find any BitArray attribute
                            for attr_name in dir(meas_data):
                                attr = getattr(meas_data, attr_name)
                                if hasattr(attr, 'get_counts'):
                                    counts = attr.get_counts()
                                    break
                            else:
                                counts = {}
                    else:
                        counts = {}
                    
                    print(f"✓ Parsed {len(counts)} measurement outcomes")
                    
                except Exception as parse_err:
                    print(f"⚠ Result parsing error: {parse_err}")
                    print(f"ℹ Result type: {type(result)}")
                    print(f"ℹ Result[0] type: {type(result[0])}")
                    if hasattr(result[0], 'data'):
                        print(f"ℹ Data attributes: {dir(result[0].data)}")
                    counts = {}
                
            except Exception as e:
                print(f"⚠ IBM Runtime execution failed: {e}")
                return False, None, 0, {}

            # Handle different result/result formats robustly
            if not counts:
                # If counts not already parsed, try legacy formats
                try:
                    counts = result[0].data.meas.get_counts()
                except Exception:
                    try:
                        quasi = getattr(result, 'quasi_dists', None)
                        if quasi and len(quasi) > 0:
                            probs = quasi[0].binary_probabilities()
                            counts = {format(int(k), f'0{n_qubits}b'): int(v * 1024) for k, v in probs.items()}
                    except Exception:
                        counts = {}
        
        sim_time = time.time() - start_time
        
        # parse result
        if counts:
            max_state = max(counts.items(), key=lambda x: x[1])
            measured_index = int(max_state[0], 2)
            measured_text = self.index_to_text(measured_index, length)
            success = measured_index == target_index
            return success, measured_text, sim_time, counts
        else:
            return False, None, sim_time, {}
    
    def quantum_search_aer(self, target_hash, length):
        # run specifically on Aer simulator
        old_backend = self.backend
        self.backend = AerSimulator()
        result = self.quantum_search(target_hash, length)
        self.backend = old_backend
        return result
    
    def quantum_search_ibm(self, target_hash, length, backend_name):
        # run specifically on IBM quantum hardware
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
    # main demo runner with three-way comparison
    print("="*80)
    print("QUANTUM PASSWORD CRACKING WITH GROVER'S ALGORITHM")
    print("Comparing: Classical vs Qiskit Aer Simulator vs IBM Quantum Hardware")
    print("="*80)
    
    # Create cracker (auto-loads .env credentials)
    cracker = QuantumHashCracker()
    
    # Check if IBM Quantum is available
    ibm_available = cracker.service is not None
    
    if ibm_available:
        print("\n✓ IBM Quantum service connected")
        print("\nFetching available backends...")
        try:
            backends = cracker.service.backends()
            print("\nAvailable IBM quantum backends:")
            available_backends = []
            for b in backends:
                try:
                    if b.status().operational and b.num_qubits >= 10:
                        available_backends.append(b)
                        print(f"  • {b.name} ({b.num_qubits} qubits, queue: {b.status().pending_jobs})")
                except:
                    pass
            
            if available_backends:
                print(f"\nRecommended: Use least busy backend for faster execution")
                backend_name = input(f"\nEnter backend name (default: {available_backends[0].name}): ").strip()
                if not backend_name:
                    backend_name = available_backends[0].name
            else:
                print("\nNo operational backends available. Will run Aer only.")
                ibm_available = False
                backend_name = None
        except Exception as e:
            print(f"\nError fetching backends: {e}")
            print("Will run Aer simulator only.")
            ibm_available = False
            backend_name = None
    else:
        print("\n⚠ IBM Quantum not configured. Add credentials to .env file.")
        print("Running Classical vs Aer comparison only.")
        backend_name = None
    
    print(f"\nFull character set available:")
    print(f"  Lowercase: a-z")
    print(f"  Uppercase: A-Z")
    print(f"  Numbers: 0-9")
    print(f"  Total: {len(cracker.charset)} characters")
    
    # Get password from user
    print("\nNote: Longer passwords require exponentially more qubits!")
    print("Recommended for demonstration:")
    print("  • 1 character: Best accuracy on real quantum hardware (>85%)")
    print("  • 2 characters: Moderate accuracy, shows quantum advantage clearly")
    print("  • 3+ characters: Aer simulator only (too many gates for current hardware)")
    
    length = int(input("\nEnter password length (1-2 recommended for IBM hardware): "))
    message = input(f"Enter a {length}-character password: ").strip()
    
    # Validate input
    if len(message) != length:
        print(f"Error: Password must be exactly {length} characters. You entered {len(message)}.")
        return
    
    if not all(c in cracker.charset for c in message):
        print(f"Error: Use only characters from: a-z, A-Z, 0-9")
        return
    
    # Calculate if this is feasible
    search_space = cracker.calculate_search_space(length)
    n_qubits = math.ceil(math.log2(search_space))
    
    if ibm_available and n_qubits > 20:
        print(f"\nWarning: {n_qubits} qubits needed. Most IBM hardware has <127 qubits.")
        print("Consider using 2-3 characters for better results.")
    
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
    
    print(f"\nExecuting three methods:")
    print(f"  1. Classical brute force")
    print(f"  2. Qiskit Aer simulator (local)")
    if ibm_available and backend_name:
        print(f"  3. IBM Quantum hardware ({backend_name})")
    else:
        print(f"  3. IBM Quantum (skipped - not available)")
    
    input("\nPress Enter to start...")
    
    # Run Classical
    print("\n" + "="*80)
    print("RUNNING: Classical Brute Force")
    print("="*80)
    classical_result = cracker.classical_bruteforce(target_hash, length)
    print(f"✓ Classical complete: found '{classical_result[0]}' in {classical_result[2]:.4f}s")
    
    # Run Aer Simulator
    print("\n" + "="*80)
    print("RUNNING: Qiskit Aer Simulator (local)")
    print("="*80)
    # compute grover iterations for display (quantum_search will compute internally too)
    quantum_iters = max(1, int(math.pi / 4 * math.sqrt(search_space)))
    print(f"Building {n_qubits}-qubit circuit with {quantum_iters} Grover iterations...")
    aer_result = cracker.quantum_search_aer(target_hash, length)
    print(f"✓ Aer complete: found '{aer_result[1]}' in {aer_result[2]:.4f}s")
    
    # Run IBM Quantum Hardware
    if ibm_available and backend_name:
        print("\n" + "="*80)
        print(f"RUNNING: IBM Quantum Hardware ({backend_name})")
        print("="*80)
        print(f"⏳ Submitting job to IBM quantum computer...")
        print(f"   This may take several minutes due to queue time...")
        ibm_result = cracker.quantum_search_ibm(target_hash, length, backend_name)
        if ibm_result[1]:
            print(f"✓ IBM Quantum complete: found '{ibm_result[1]}' in {ibm_result[2]:.4f}s")
        else:
            print(f"⚠ IBM Quantum failed or timed out")
    else:
        ibm_result = (False, None, 0, {})
    
    # Show final comparison
    cracker.display_three_way_comparison(
        classical_result,
        aer_result,
        ibm_result,
        backend_name
    )
    
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    
if __name__ == '__main__':
    main()