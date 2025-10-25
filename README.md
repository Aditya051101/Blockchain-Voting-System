Custom Blockchain Voting System (PoW + JSON blockchain + MySQL users)

Overview:
- Blockchain stored in blockchain_data/chain.json (real chain with PoW)
- MySQL used for users/roles/organizations/candidates only
- Votes recorded as transactions in the blockchain, not in MySQL
- Admin mines blocks to confirm votes (PoW mining simulation)

Run (summary):
1. Install MySQL and create database (see config.py)
2. Create Python venv and install requirements
3. Create an admin account: python create_admin.py
4. Create private & public keys: python key.py
4. Run: python app.py
5. Open http://localhost:5000

Security notes:
- Private keys must be kept secret; signing occurs in the browser (client-side)
- For demo purposes private keys are typed into the browser; real systems use secure wallets
