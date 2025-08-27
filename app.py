from flask import Flask, jsonify, request
from flask_cors import CORS
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt
import io, base64, time
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ---------- in-memory storage ----------
jobs = {}
job_counter = 0

@app.route('/jobs/cancel/<int:job_id>', methods=['POST'])
def cancel_job(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job['Status'] in ['Completed', 'Error','Cancelled']:
        return jsonify({"error": f"Cannot cancel job in status {job['Status']}"}), 400
    job['Status'] = 'Cancelled'
    update_queue_positions()
    return jsonify({"message": "Job cancelled successfully"})


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def update_queue_positions():
    queued = [j for j in jobs.values() if j["Status"] in ("Queued", "Running")]
    queued_sorted = sorted(queued, key=lambda x: x.get("Created"))
    for pos, job in enumerate(queued_sorted):
        job["Queue Position"] = pos

def create_job(backend="AerSimulator", qubits=2, shots=1024):
    global job_counter
    job_counter += 1
    job_id = job_counter
    jobs[job_id] = {
        "Job ID": job_id,
        "Status": "Queued",
        "Backend": backend,
        "Qubits": int(qubits),
        "Shots": int(shots),
        "Queue Position": None,
        "Created": now_str(),
        "Duration": None,
        "Result": None,
        "Error": None,
    }
    update_queue_positions()
    return jobs[job_id]

# Seed example jobs
create_job()
create_job()
create_job()

# ---------- endpoints ----------
@app.route("/")
def home():
    return jsonify({"message": "Quantum Dashboard Backend is running!"})

@app.route("/jobs", methods=["GET"])
def list_jobs():
    all_jobs = sorted(jobs.values(), key=lambda x: x["Job ID"])
    return jsonify(all_jobs), 200

@app.route("/jobs/<int:job_id>", methods=["GET"])
def get_job(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job), 200

@app.route("/jobs/new", methods=["POST"])
def new_job():
    data = request.get_json() or {}
    backend = data.get("backend", "AerSimulator")
    qubits = int(data.get("qubits", 2))
    shots = int(data.get("shots", 1024))
    job = create_job(backend=backend, qubits=qubits, shots=shots)
    return jsonify(job), 201

@app.route("/jobs/run/<int:job_id>", methods=["POST"])
def run_job(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job["Status"] == "Running":
        return jsonify({"error": "Job already running"}), 400

    job["Status"] = "Running"
    job["Started"] = now_str()
    update_queue_positions()

    start_time = time.time()
    try:
        qc = QuantumCircuit(job["Qubits"], job["Qubits"])
        qc.h(0)
        if job["Qubits"] > 1:
            qc.cx(0, 1)
        qc.measure(list(range(job["Qubits"])), list(range(job["Qubits"])))

        backend_sim = AerSimulator()
        tqc = transpile(qc, backend_sim)
        qjob = backend_sim.run(tqc, shots=job["Shots"])
        result = qjob.result()
        counts = result.get_counts()

        fig, ax = plt.subplots(figsize=(6, 3))
        plot_histogram(counts, ax=ax)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        histogram_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        buf.close()
        plt.close(fig)

        duration = round(time.time() - start_time, 3)
        job["Duration"] = duration
        job["Result"] = {"counts": counts, "histogram_base64": histogram_base64}
        job["Status"] = "Completed"
        job["Completed"] = now_str()
        update_queue_positions()

        return jsonify(job["Result"]), 200

    except Exception as e:
        job["Status"] = "Error"
        job["Error"] = str(e)
        update_queue_positions()
        return jsonify({"error": str(e)}), 500

@app.route("/backends", methods=["GET"])
def list_backends():
    return jsonify(["AerSimulator"]), 200

@app.route("/jobs/delete/<int:job_id>", methods=["DELETE"])
def delete_job(job_id):
    if job_id in jobs:
        del jobs[job_id]
        update_queue_positions()
        return jsonify({"ok": True}), 200
    return jsonify({"error": "Job not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
