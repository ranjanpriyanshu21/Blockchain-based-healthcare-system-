# Medical Blockchain System

## Overview

This project implements a blockchain-based medical records system with the following features:

- **Patient and Doctor Dashboards**: Separate interfaces for medical professionals and patients
- **Consent Management**: OTP-based consent system for patient data access
- **Blockchain Validation**: PBFT (Practical Byzantine Fault Tolerance) consensus protocol
- **Medical Record Tracking**: Secure storage and retrieval of medical records
- **Performance Metrics**: Real-time monitoring of blockchain performance

## Technologies Used

### Frontend
- HTML5, CSS3, JavaScript
- Tailwind CSS for styling
- Font Awesome for icons

### Backend
- Python 3
- Flask web framework
- SQLite database
- PBFT consensus algorithm
- Cryptographic hashing (SHA-256)

## Installation

### Prerequisites
- Python 3.7+
- pip package manager
- Modern web browser

### Backend Setup
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install flask flask-cors
   ```
3. Run the server:
   ```bash
   python server.py
   ```

### Frontend Setup
1. The frontend is served directly by the Flask server
2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```
 # Screenshots
 ![](/Screenshots/Screen1.jpg)
 ![](/Screenshots/Screen2.jpg)
 ![](/Screenshots/Screen3.jpg)
 ![](/Screenshots/Screen4.jpg)
 ![](/Screenshots/Screen5.jpg)


   

## System Architecture

### Key Components
1. **Authentication System**
   - Patient and doctor login with role-based access
   - Password protection for all accounts

2. **Consent Management**
   - Time-limited OTPs for patient consent
   - One-time-use consent tokens stored as hashes

3. **Blockchain Core**
   - SQLite-backed blockchain storage
   - Genesis block initialization
   - Chain validation mechanisms

4. **PBFT Consensus**
   - Simulated validator nodes
   - Voting-based block validation
   - Performance metrics collection

5. **Medical Records**
   - Tamper-evident record storage
   - Patient-specific data retrieval
   - Department-based organization

## Usage Instructions

### Patient Login
1. Select "Patient" role
2. Enter patient ID (e.g., p001) and password (patient123)
3. Click Login

### Doctor Login
1. Select "Doctor" role
2. Enter doctor ID (e.g., d001) and password (doctor123)
3. Click Login

### Doctor Features
- **Request Patient Consent**: Generate OTP for patient data access
- **Add Medical Record**: Create new records with patient consent
- **Validate Block**: Initiate PBFT consensus process
- **View System Metrics**: Monitor blockchain performance

### Patient Features
- **View Medical History**: Access all personal medical records
- **Refresh Data**: Get latest updates from blockchain

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/login` | POST | Authenticate users |
| `/api/request_consent` | POST | Generate consent OTP |
| `/api/add_record` | POST | Add new medical record |
| `/api/validate` | POST | Initiate block validation |
| `/api/patient_records` | POST | Retrieve patient records |
| `/api/metrics` | GET | Get system performance metrics |

## Sample Credentials

### Patients
- ID: p001, Password: patient123
- ID: p002, Password: patient456

### Doctors
- ID: d001, Password: doctor123 (Cardiology)
- ID: d002, Password: doctor456 (Oncology)

## Security Features

1. **Data Integrity**
   - All records cryptographically hashed
   - Chain validation on load

2. **Access Control**
   - Role-based authentication
   - Mandatory patient consent for all operations

3. **Consent System**
   - Time-limited OTPs (5 minutes)
   - One-time-use tokens
   - Consent hashes stored in blockchain

## Performance Considerations

1. **Batch Processing**
   - Records collected in batches
   - Configurable batch window (default: 6 seconds)

2. **Metrics Tracking**
   - Transactions per second (TPS)
   - Consensus latency
   - Energy consumption estimates
   - Success rates

## Troubleshooting

### Common Issues
1. **Genesis block not created**
   - Delete `medical_chain.db` and restart server
   
2. **Login failures**
   - Verify correct credentials from sample list
   - Check server console for errors

3. **Block validation delays**
   - Wait for batch window to complete
   - Check system metrics for validator performance

## License

This project is open-source and available for educational purposes. Commercial use requires permission.

## Future Enhancements

1. **Patient Consent App**
   - Mobile interface for OTP approval
   
2. **Extended Validator Network**
   - Real distributed nodes
   
3. **Advanced Cryptography**
   - Public/private key pairs
   - Digital signatures

4. **Inter-hospital Data Sharing**
   - Federated blockchain network

