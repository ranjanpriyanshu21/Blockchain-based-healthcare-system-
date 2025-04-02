from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, UTC
import hashlib
import json
import time
import sqlite3
import random
import os

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Configuration
METRICS_FILE = "pbft_metrics.json"
BATCH_INTERVAL = 6
OTP_EXPIRY = 300


class MedicalBlockchain:
    def _init_(self):
        self.chain = []
        self.pending_records = []
        self.validators = ["Hospital Node", "Clinic Node", "Pharmacy Node", "Insurance Node"]
        self.pending_consents = {}
        self.db_init()
        self.load_chain()
        self.last_block_time = time.time()
        self.batch_window = BATCH_INTERVAL
        self.metrics = {'total_tx': 0, 'success_blocks': 0, 'attempted_blocks': 0, 'total_energy': 0}

        if not self.chain or self.chain[0]["previous_hash"] != "0":
         self.create_genesis_block()
         self.load_chain()

    def create_genesis_block(self):
        """Explicitly create genesis block with proper hashes"""
        print("🔄 Creating genesis block...")
        genesis_block = {
            "timestamp": datetime.now(UTC).isoformat(),
            "records": [],
            "previous_hash": "0",
            "data_hash": hashlib.sha256(json.dumps([], sort_keys=True).encode()).hexdigest(),
            "consent_hash": hashlib.sha256("".encode()).hexdigest()
        }

        try:
            with sqlite3.connect("medical_chain.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO blocks 
                    (timestamp, records, previous_hash, data_hash, consent_hash, medical_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    genesis_block["timestamp"],
                    json.dumps(genesis_block["records"]),
                    genesis_block["previous_hash"],
                    genesis_block["data_hash"],
                    genesis_block["consent_hash"],
                    json.dumps([])  # Empty medical data
                ))
                conn.commit()
        except sqlite3.Error as e:
            print(f"❌ Genesis block creation failed: {str(e)}")

    def get_batch_window_remaining(self):
        elapsed = time.time() - self.last_block_time
        return max(self.batch_window - elapsed, 0)

    def db_init(self):
        with sqlite3.connect("medical_chain.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    records TEXT,
                    previous_hash TEXT,
                    data_hash TEXT,
                    consent_hash TEXT,
                    medical_data TEXT
                )
            """)
            conn.commit()

    def validate_record(self, record):
        required = ["patient_id", "doctor_id", "data_hash", "consent_hash", "timestamp"]
        return all(record.get(field) for field in required)

    def create_candidate_block(self):
        previous_block = self.get_previous_block()
        previous_hash = "0" if not previous_block else self.hash(previous_block)
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "records": self.pending_records.copy(),
            "previous_hash": previous_hash,
            "data_hash": hashlib.sha256(
                json.dumps(self.pending_records, sort_keys=True).encode()
            ).hexdigest(),
            "consent_hash": hashlib.sha256(
                "".join([r['consent_hash'] for r in self.pending_records]).encode()
            ).hexdigest()
        }

    def add_block(self, candidate_block):
        try:
            with sqlite3.connect("medical_chain.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO blocks 
                    (timestamp, records, previous_hash, data_hash, consent_hash, medical_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    candidate_block["timestamp"],
                    json.dumps(candidate_block["records"]),
                    candidate_block["previous_hash"],
                    candidate_block["data_hash"],
                    candidate_block["consent_hash"],
                    json.dumps([r.get('medical_data', {}) for r in candidate_block["records"]])
                ))
                conn.commit()

                self.chain.append({
                    "index": cursor.lastrowid,
                    **candidate_block
                })

            self.pending_records.clear()
            self.metrics['success_blocks'] += 1
            return True, "Medical block added"
        except sqlite3.Error as e:
            return False, str(e)

    def load_chain(self):
        with sqlite3.connect("medical_chain.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, timestamp, records, previous_hash, data_hash, medical_data ,consent_hash FROM blocks")
            self.chain = [{
                "index": row[0],
                "timestamp": row[1],
                "records": json.loads(row[2]),
                "previous_hash": row[3],
                "data_hash": row[4],
                "consent_hash": row[5]
            } for row in cursor.fetchall()]

        is_valid, msg = self.validate_chain()
        if not is_valid:
            print(f"⚠ Chain Corruption Detected: {msg}")

    def generate_consent(self, patient_id):
        otp = str(random.randint(100000, 999999))
        consent_token = hashlib.sha256(f"{patient_id}{otp}".encode()).hexdigest()

        self.pending_consents[patient_id] = {
            'token': consent_token,
            'expiry': time.time() + OTP_EXPIRY,
            'used': False
        }
        return otp, consent_token

    def validate_consent(self, patient_id, otp):
        consent = self.pending_consents.get(patient_id)
        if not consent or time.time() > consent['expiry']:
            return False, "Expired or invalid consent"
        if consent['used']:  # This check prevents reuse
            return False, "Consent already used"

        expected = hashlib.sha256(f"{patient_id}{otp}".encode()).hexdigest()
        if consent['token'] == expected:
            consent['used'] = True  # Mark as used immediately
            return True, "Valid consent"
        return False, "Invalid OTP"

    def add_medical_record(self, record, medical_data, consent_otp):
        try:
            # Validate consent FIRST
            valid, msg = self.validate_consent(record['patient_id'], consent_otp)
            if not valid:
                return False, msg  # Reject if OTP is invalid/used

            # Proceed only if consent is valid
            full_record = {
                **record,
                "timestamp": datetime.now(UTC).isoformat(),
                "data_hash": hashlib.sha256(
                    json.dumps(medical_data, sort_keys=True).encode()
                ).hexdigest(),
                "consent_hash": hashlib.sha256(
                    f"{record['patient_id']}{consent_otp}".encode()
                ).hexdigest(),
                "medical_data": {
                    "diagnosis": medical_data['diagnosis'].strip(),
                    "prescription": medical_data['prescription'].strip(),
                    "notes": medical_data.get('notes', '').strip()
                }
            }

            if self.validate_record(full_record):
                self.pending_records.append(full_record)
                self.metrics['total_tx'] += 1
                return True, "Record added to batch"
            return False, "Invalid record format"

        except Exception as e:
            return False, f"System error: {str(e)}"

    def pbft_consensus(self):
        """
        Execute PBFT consensus protocol with enhanced validation simulation,
        error handling, and detailed metrics tracking
        """
        try:
            # 1. Pre-consensus checks
            if not self.validators:
                return False, "No validators configured"

            if not self.pending_records:
                return False, "No pending records to validate"

            is_valid, msg = self.validate_chain()
            if not is_valid:
                return False, f"Chain invalid: {msg}"

            # 2. Prepare for consensus
            candidate_block = self.create_candidate_block()
            total_validators = len(self.validators)
            required_votes = (2 * total_validators) // 3 + 1
            votes = 0
            validation_results = []
            start_time = time.perf_counter()

            # 3. Simulate network validation with realistic parameters
            for validator in self.validators:
                try:
                    # Simulate network latency and processing time
                    latency = random.uniform(0.1, 0.5)
                    time.sleep(latency)

                    # Simulate 10% chance of validator failure
                    if random.random() < 0.1:
                        raise Exception("Validator node unreachable")

                    # Perform actual validation
                    is_valid = self.validate_candidate_block(candidate_block)
                    validation_results.append({
                        "validator": validator,
                        "latency": latency,
                        "success": is_valid,
                        "error": None
                    })

                    if is_valid:
                        votes += 1

                except Exception as e:
                    validation_results.append({
                        "validator": validator,
                        "latency": latency,
                        "success": False,
                        "error": str(e)
                    })

            consensus_time = time.perf_counter() - start_time
            energy_used = consensus_time * total_validators * 20
            self.metrics['attempted_blocks'] += 1  # Track attempt immediately

            # 5. Determine consensus outcome FIRST
            success = False
            message = ""
            if votes >= required_votes:
                # Attempt to add block and update success status
                success, msg = self.add_block(candidate_block)
                if success:
                    self.last_block_time = time.time()
                    message = (
                        f"Block {candidate_block['data_hash'][:8]} committed | "
                        f"{votes}/{total_validators} validators approved | "
                        f"{len(candidate_block['records'])} transactions"
                    )
                else:
                    message = f"Block storage failed: {msg}"
            else:
                error_details = "\n".join(
                    f"{res['validator']}: {res['error'] or 'Invalid block'}"
                    for res in validation_results if not res['success']
                )
                message = (
                    f"Consensus failed ({votes}/{required_votes} votes)\n"
                    f"Validation errors:\n{error_details}"
                )

            # 6. Update energy AFTER block attempt
            self.metrics['total_energy'] += energy_used

            # 7. Log metrics WITH UPDATED SUCCESS STATUS
            self.log_metrics(
                latency=consensus_time,
                energy=energy_used,
                block=candidate_block,
                votes=votes,
                required_votes=required_votes,
                validation_results=validation_results
            )

            return success, message

        except Exception as e:
            error_id = hashlib.sha256(str(e).encode()).hexdigest()[:8]
            print(f"PBFT Critical Error [{error_id}]: {str(e)}")
            return False, f"Consensus process failed: {error_id}"

    def validate_candidate_block(self, block):
        return all(self.validate_record(r) for r in block['records'])

    def validate_chain(self):
        # Check genesis block
        if len(self.chain) > 0:
            genesis = self.chain[0]
            if genesis["previous_hash"] != "0":
                return False, "Genesis block corrupted"

        # Check all subsequent blocks
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # 1. Verify previous_hash linkage
            if current_block["previous_hash"] != self.hash(previous_block):
                return False, f"Block {i} has invalid previous hash"

            # 2. Verify current block's data integrity
            expected_data_hash = hashlib.sha256(
                json.dumps(current_block["records"], sort_keys=True).encode()
            ).hexdigest()
            if current_block["data_hash"] != expected_data_hash:
                return False, f"Block {i} has invalid data hash"

            # 3. Verify consent hashes (optional)
            expected_consent_hash = hashlib.sha256(
                "".join([r['consent_hash'] for r in current_block["records"]]).encode()
            ).hexdigest()
            if current_block["consent_hash"] != expected_consent_hash:
                return False, f"Block {i} has invalid consent hash"

        return True, "Chain is valid"

    def log_metrics(self, latency, energy, block, votes, required_votes, validation_results):
        try:
            tx_count = len(block.get('records', []))
            tps = tx_count / latency if latency > 0 else 0

            # Calculate success rate using cumulative values
            success_rate = 0
            if self.metrics['attempted_blocks'] > 0:
                success_rate = (self.metrics['success_blocks'] / self.metrics['attempted_blocks']) * 100

            metrics_data = {
                "timestamp": datetime.now(UTC).isoformat(),
                "latency": latency,
                "tps": round(tps, 2),
                "energy": round(energy, 2),
                "success_rate": round(success_rate, 2),
                "attempted_blocks": self.metrics['attempted_blocks'],
                "success_blocks": self.metrics['success_blocks'],
                "tx_count": tx_count,
                "consensus": {
                    "votes": votes,
                    "required_votes": required_votes,
                    "validator_count": len(self.validators)
                }
            }

            with open(METRICS_FILE, "a") as f:
                f.write(json.dumps(metrics_data) + "\n")

        except Exception as e:
            print(f"Metrics logging failed: {str(e)}")

    def hash(self, block):
        return hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()

    def get_previous_block(self):
        return self.chain[-1] if self.chain else None


# Authentication Database
patients = {
    "p001": {"password": "patient123", "phone": "8090937332"},
    "p002": {"password": "patient456", "phone": "+0987654321"}
}

doctors = {
    "d001": {"password": "doctor123", "department": "Cardiology"},
    "d002": {"password": "doctor456", "department": "Oncology"}
}

blockchain = MedicalBlockchain()


@app.route('/')
def serve_frontend():
    return send_from_directory('The-Ultimate-Python-Course-main', 'index.html')


@app.route('/api/metrics')
def get_metrics():
    try:
        if not os.path.exists(METRICS_FILE):
            return jsonify({"success": True, "metrics": [], "message": "No metrics collected yet"})

        with open(METRICS_FILE, "r") as f:
            try:
                metrics = [json.loads(line) for line in f.readlines()]
            except json.JSONDecodeError:
                metrics = []

        return jsonify({
            "success": True,
            "count": len(metrics),
            "latest": metrics[-1] if metrics else {},
            "metrics": metrics[-100:]  # Return last 100 entries
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to load metrics"
        }), 500

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('The-Ultimate-Python-Course-main', path)


@app.route('/api/login', methods=['POST'])
def handle_login():
    try:
        data = request.get_json()
        role = data.get('role')

        if role == 'patient':
            patient_id = data.get('patientId')
            if patients.get(patient_id) and patients[patient_id]['password'] == data.get('password'):
                return jsonify({"success": True, "userType": "patient", "patientId": patient_id})
        elif role == 'doctor':
            doctor_id = data.get('doctorId')
            if doctors.get(doctor_id) and doctors[doctor_id]['password'] == data.get('password'):
                return jsonify({"success": True, "userType": "doctor", "doctorId": doctor_id})

        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/request_consent', methods=['POST'])
def handle_request_consent():
    data = request.get_json()
    patient_id = data.get('patientId')
    password = data.get('password')

    if not patients.get(patient_id) or patients[patient_id]['password'] != password:
        return jsonify({"success": False, "message": "Invalid patient credentials"}), 401

    otp, token = blockchain.generate_consent(patient_id)
    return jsonify({"success": True, "otp": otp, "expiry": OTP_EXPIRY})


@app.route('/api/validate_chain', methods=['GET'])
def handle_validate_chain():
    is_valid, msg = blockchain.validate_chain()
    return jsonify({
        "valid": is_valid,
        "message": msg,
        "block_count": len(blockchain.chain)
    })

@app.route('/api/add_record', methods=['POST'])
def handle_add_record():
    try:
        data = request.get_json()

        # Debugging: Log incoming data
        print("Received data:", json.dumps(data, indent=2))

        # Extract medical_data from request
        medical_data = data.get('medical_data', {})

        # Validate required fields with content checks
        if not medical_data.get('diagnosis', '').strip():
            return jsonify({
                "success": False,
                "message": "Diagnosis cannot be empty",
                "error_type": "validation",
                "field": "diagnosis"
            }), 400

        if not medical_data.get('prescription', '').strip():
            return jsonify({
                "success": False,
                "message": "Prescription cannot be empty",
                "error_type": "validation",
                "field": "prescription"
            }), 400

        # Proceed with record creation
        record = {
            "patient_id": data['patientId'],
            "doctor_id": data['doctorId'],
            "department": data.get('department', 'General')
        }

        success, message = blockchain.add_medical_record(
            record,
            medical_data,
            data['otp']
        )

        if success:
            return jsonify({"success": True, "message": message})

        return jsonify({
            "success": False,
            "message": message,
            "error_type": "blockchain_validation"
        }), 400

    except KeyError as e:
        return jsonify({
            "success": False,
            "message": f"Missing required field: {str(e)}",
            "error_type": "missing_field"
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}",
            "error_type": "server_error"
        }), 500


@app.route('/api/validate', methods=['POST'])
def handle_validate():
    try:
        remaining = blockchain.get_batch_window_remaining()
        if remaining > 0:
            return jsonify({
                "success": False,
                "message": f"Batch window not reached ({remaining:.1f}s remaining)",
                "remaining": remaining
            }), 400

        success, message = blockchain.pbft_consensus()
        status_code = 200 if success else 400
        return jsonify({"success": success, "message": message}), status_code
    except Exception as e:
        print(f"Validation error: {str(e)}")
        return jsonify({"success": False, "message": f"Validation failed: {str(e)}"}), 500


@app.route('/api/patient_records', methods=['POST'])
def handle_patient_records():
    try:
        data = request.get_json()
        if not patients.get(data['patientId']) or patients[data['patientId']]['password'] != data['password']:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        records = []
        for block in blockchain.chain:
            for tx in block.get('records', []):
                if tx['patient_id'] == data['patientId']:
                    records.append({
                        "timestamp": tx['timestamp'],
                        "doctor_id": tx['doctor_id'],
                        "department": tx.get('department', 'Unknown'),
                        "diagnosis": tx.get('medical_data', {}).get('diagnosis'),
                        "prescription": tx.get('medical_data', {}).get('prescription'),
                        "notes": tx.get('medical_data', {}).get('notes', ''),
                        "consent_hash": tx['consent_hash']
                    })
        return jsonify({"success": True, "records": records})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/favicon.ico')
def favicon():
    return '', 204


if __name__ == '_main_':
    app.run(host='0.0.0.0', port=5000, debug=True)