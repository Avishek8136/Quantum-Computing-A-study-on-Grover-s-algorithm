# Quantum Password Cracking with Grover's Algorithm

Demo comparing **Classical Brute Force** vs **Qiskit Aer Simulator** vs **IBM Quantum Hardware** for password cracking using Grover's algorithm.

## 🚀 Quick Start

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure IBM Quantum Credentials

Your credentials are already in `.env`:
```
IBM_QUANTUM_TOKEN=701ZaN0gi5beJ7lI99WmJ2EwsR9zN5aM3rZ4kE8CphVR
IBM_QUANTUM_INSTANCE=crn:v1:bluemix:public:quantum-computing:us-east:a/...
```

### 3. Run the Demo

```powershell
python grover.py
```

## 📊 What It Does

The program will:

1. **Auto-load** your IBM Quantum credentials from `.env`
2. **Connect** to IBM Quantum and list available quantum computers
3. **Prompt** you to choose a backend (or use least busy)
4. **Ask** for a password to crack (2-3 characters recommended)
5. **Run three methods**:
   - Classical brute force (sequential search)
   - Qiskit Aer simulator (local quantum simulation)
   - IBM Quantum hardware (real quantum computer)
6. **Compare** results in a table

## 🎯 Example Usage

```
Enter password length (2-3 recommended): 2
Enter a 2-character password: Hi

Executing three methods:
  1. Classical brute force
  2. Qiskit Aer simulator (local)
  3. IBM Quantum hardware (ibm_brisbane)
```

## ⚡ Three-Way Comparison

You'll see output like:

```
Method               Result          Time                 Iterations/Attempts  Accuracy
--------------------------------------------------------------------------------
Classical            'Hi'            0.0045s              2,945                100%
Qiskit Aer (sim)     'Hi'            0.3241s              48                   98.2%
IBM ibm_brisbane     'Hi'            45.2341s             48                   87.5%
```

## 🔑 Key Insights
🔍 Why Low Accuracy?
The main issue: Your 12-qubit, 48-iteration Grover circuit transpiled to 714,861 gates!

Real quantum computers have:

Gate errors: ~0.1-1% error per gate
Decoherence: Qubits lose information over time
With 714K gates: Error accumulates massively → random results


- **Classical**: Tries thousands of combinations sequentially
- **Quantum**: Only √N Grover iterations needed (huge speedup!)
- **Aer**: Simulates quantum operations (slow on classical hardware)
- **IBM Quantum**: Runs on real quantum computer (true quantum advantage)

## ⚠️ Important Notes

- **Password Length**: Use 2-3 characters for best results
  - 2 chars = ~3,844 combinations, 12 qubits, 48 Grover iterations
  - 3 chars = ~238,328 combinations, 18 qubits, 383 iterations
- **IBM Queue Time**: Real quantum hardware jobs may wait in queue
- **Noise**: Real quantum computers have decoherence/errors (lower accuracy)

## 📝 Files

- `grover.py` - Main quantum password cracker
- `.env` - IBM Quantum credentials (keep secret!)
- `requirements.txt` - Python dependencies
- `README.md` - This file

## 🔒 Security Note

**DO NOT commit `.env` to GitHub!** It contains your API credentials.

Add to `.gitignore`:
```
.env
```

## 🎓 Learn More

- [IBM Quantum Documentation](https://quantum.ibm.com/docs)
- [Qiskit Textbook](https://qiskit.org/learn)
- [Grover's Algorithm](https://en.wikipedia.org/wiki/Grover%27s_algorithm)
