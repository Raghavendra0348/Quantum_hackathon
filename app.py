from flask_cors import CORS
from flask import Flask, jsonify
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Mock list of jobs
jobs_list = [
    {"Job ID": 1, "Status": "Completed", "Backend": "AerSimulator", "Qubits": 2, "Shots": 1024, "Queue Position": 0, "Created": "2025-08-27 12:00:00", "Duration": "2s"},
    {"Job ID": 2, "Status": "Completed", "Backend": "AerSimulator", "Qubits": 2, "Shots": 1024, "Queue Position": 1, "Created": "2025-08-27 12:05:00", "Duration": "3s"},
]

@app.route('/jobs', methods=['GET'])
def get_jobs():
    return jsonify(jobs_list)

@app.route('/jobs/run/<int:job_id>', methods=['POST'])
def run_job(job_id):
    try:
        # --- Quantum Circuit: 2-qubit Bell state ---
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure([0, 1], [0, 1])

        # --- Execute Circuit ---
        backend = AerSimulator()
        tqc = transpile(qc, backend)
        job = backend.run(tqc, shots=1024)
        result = job.result()
        counts = result.get_counts()

        # --- Generate Histogram Base64 ---
        fig, ax = plt.subplots(figsize=(6,4))
        plot_histogram(counts, ax=ax)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        histogram_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        buf.close()
        plt.close(fig)

        return jsonify({'counts': counts, 'histogram_base64': histogram_base64})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

