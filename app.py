# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from db import init_db, SessionLocal
from models import User, Organization, Candidate, Settings, ResultRecord
from sqlalchemy.orm import joinedload
from wallet import verify_signature_hex
from blockchain import Blockchain
import config, time
from functools import wraps

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = config.SECRET_KEY

init_db()
blockchain = Blockchain(chain_file=config.BLOCKCHAIN_FILE, difficulty=config.POW_DIFFICULTY)

def get_db():
    return SessionLocal()

def get_settings():
    s = get_db().query(Settings).first()
    return s

# auth decorators
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Check if user is logged in
            if 'user_id' not in session:
                flash("Please log in first", "warning")
                return redirect(url_for('login'))

            # Check user role
            user_role = session.get('role')
            if user_role != role:
                flash("Access denied: insufficient permissions", "danger")
                return redirect(url_for('index'))

            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route("/")
def index():
    if "user_id" in session:
        role = session.get("role")
        if role == "admin":
            return redirect(url_for("admin_dashboard"))
        if role == "organization":
            return redirect(url_for("org_dashboard"))
        return redirect(url_for("voter_dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        db = get_db()
        u = db.query(User).filter_by(username=request.form.get("username")).first()
        if u and check_password_hash(u.password, request.form.get("password")):
            session["user_id"] = u.id
            session["role"] = u.role.value
            session["org_id"] = u.org_id
            flash("Logged in")
            db.close()
            return redirect(url_for("index"))
        flash("Invalid credentials")
        db.close()
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

### ADMIN ###
@app.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    db = get_db()
    orgs = db.query(Organization).all()
    users = db.query(User).all()
    candidates = db.query(Candidate).options(joinedload(Candidate.organization)).all()
    s = db.query(Settings).first()
    db.close()
    unconfirmed = len(blockchain.unconfirmed_transactions)
    chain_len = len(blockchain.chain)
    return render_template("admin_dashboard.html", orgs=orgs, users=users, candidates=candidates,
                           unconfirmed=unconfirmed, chain_len=chain_len, settings=s)

@app.route("/admin/create_org", methods=["POST"])
@login_required
@role_required("admin")
def admin_create_org():
    db = get_db()
    o = Organization(name=request.form.get("name"), description=request.form.get("description"))
    db.add(o); db.commit(); db.close()
    flash("Organization created")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/register_user", methods=["POST"])
@login_required
@role_required("admin")
def admin_register_user():
    db = get_db()
    username = request.form.get("username")
    pwd = request.form.get("password")
    role = request.form.get("role")
    org_id = request.form.get("org_id") or None
    public_key = request.form.get("public_key") or None
    hashed = generate_password_hash(pwd)
    u = User(username=username, password=hashed, role=role, org_id=org_id, public_key=public_key)
    db.add(u); db.commit(); db.close()
    flash("User created")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/create_candidate", methods=["POST"])
@login_required
@role_required("admin")
def admin_create_candidate():
    db = get_db()
    name = request.form.get("name")
    org_id = request.form.get("org_id") or None
    c = Candidate(name=name, org_id=org_id)
    db.add(c); db.commit(); db.close()
    flash("Candidate added")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/get_voting_status")
@login_required
@role_required("admin")
def admin_get_voting_status():
    db = get_db()
    s = db.query(Settings).first()
    state = "active" if s and s.voting_active else "stopped"
    db.close()
    return jsonify({"state": state})


@app.route("/admin/toggle_voting", methods=["POST"])
@login_required
@role_required("admin")
def admin_toggle_voting():
    db = get_db()
    s = db.query(Settings).first()
    if not s:
        s = Settings(voting_active=False, results_declared=False)
        db.add(s)
    s.voting_active = not s.voting_active
    db.commit()
    state = "active" if s.voting_active else "stopped"
    db.close()
    return jsonify({"state": state})


@app.route("/admin/declare_results", methods=["POST"])
@login_required
@role_required("admin")
def admin_declare_results():
    db = get_db()
    s = db.query(Settings).first()
    if not s:
        s = Settings(voting_active=False, results_declared=False)
        db.add(s)
        db.commit()

    # Stop voting and mark results declared
    s.results_declared = True
    s.voting_active = False

    # Calculate results from blockchain
    counts = {}
    for b in blockchain.chain[1:]:
        for tx in b.transactions:
            cand = tx.get("candidate_id")
            if cand is not None:
                counts[cand] = counts.get(cand, 0) + 1

    # Map candidate IDs to names
    candidates = db.query(Candidate).all()
    name_map = {c.id: c.name for c in candidates}
    result_by_name = {name_map.get(int(k), str(k)): v for k, v in counts.items()}

    # Determine winner
    winner = max(result_by_name, key=result_by_name.get) if result_by_name else "No Votes"

    # Store in result_records table
    total_votes = sum(result_by_name.values())
    record = ResultRecord(results_data=result_by_name, total_votes=total_votes, winner=winner)
    db.add(record)
    db.commit()

    db.close()
    return jsonify({'results_declared': True, 'voting_active': False, 'winner': winner})

@app.route("/admin/reset_voting", methods=["POST"])
@login_required
@role_required("admin")
def admin_reset_voting():
    db = get_db()
    s = db.query(Settings).first()

    # --- 1. Archive Current Election Results Before Reset ---
    if s and not s.results_declared:
        # Compute results from existing blockchain
        counts = {}
        for b in blockchain.chain[1:]:
            for tx in b.transactions:
                cand = tx.get("candidate_id")
                if cand is not None:
                    counts[cand] = counts.get(cand, 0) + 1

        candidates = db.query(Candidate).all()
        name_map = {c.id: c.name for c in candidates}
        result_by_name = {name_map.get(int(k), str(k)): v for k, v in counts.items()}

        total_votes = sum(result_by_name.values())
        winner = max(result_by_name, key=result_by_name.get) if result_by_name else "No Votes"

        # Store last election results
        record = ResultRecord(
            results_data=result_by_name,
            total_votes=total_votes,
            winner=winner
        )
        db.add(record)
        db.commit()

    # --- 2. Reset Settings ---
    if not s:
        s = Settings(voting_active=False, results_declared=False)
        db.add(s)
    else:
        s.voting_active = False
        s.results_declared = False
    db.commit()

    # --- 3. Reset blockchain (clear blocks, transactions) ---
    blockchain.reset_chain()

    # --- 4. Clear Candidates and Voters if Desired ---
    #db.query(Candidate).delete()
    #db.query(User).filter(User.role == "voter").delete()
    #db.commit()

    # --- 5. Finalize ---
    db.close()
    return jsonify({'reset': True, 'archived_results': True})

# @app.route("/admin/mine", methods=["POST"])
# @login_required
# @role_required("admin")
# def admin_mine():
#     db = get_db()
#     s = db.query(Settings).first()
#     # cannot mine if results declared
#     if s.results_declared:
#         db.close()
#         flash("Results already declared. Mining disabled.")
#         return redirect(url_for("admin_dashboard"))
#     if not blockchain.unconfirmed_transactions:
#         db.close()
#         flash("No transactions to mine")
#         return redirect(url_for("admin_dashboard"))
#     idx = blockchain.mine()
#     db.close()
#     if idx == -1:
#         flash("Mining failed")
#     else:
#         flash(f"Block mined: index {idx}")
#     return redirect(url_for("admin_dashboard"))

### ORGANIZATION ###
@app.route("/org/dashboard")
@login_required
@role_required("organization")
def org_dashboard():
    db = get_db()
    org_id = session.get("org_id")

    # Fetch organization info
    org = db.query(Organization).filter_by(id=org_id).first()

    candidates = (
        db.query(Candidate)
        .options(joinedload(Candidate.organization))
        .filter((Candidate.org_id == org_id) | (Candidate.org_id == None))
        .all()
    )

    voters = db.query(User).filter_by(org_id=org_id, role="voter").all()
    s = db.query(Settings).first()
    db.close()

    # Pass organization name to the template
    return render_template(
        "org_dashboard.html",
        org_name=org.name if org else "Unknown Organization",
        candidates=candidates,
        voters=voters,
        settings=s
    )

@app.route("/org/create_candidate", methods=["POST"])
@login_required
@role_required("organization")
def org_create_candidate():
    db = get_db()
    name = request.form.get("name")
    org_id = session.get("org_id")
    c = Candidate(name=name, org_id=org_id)
    db.add(c); db.commit(); db.close()
    flash("Candidate created")
    return redirect(url_for("org_dashboard"))

@app.route("/org/register_voter", methods=["POST"])
@login_required
@role_required("organization")
def org_register_voter():
    db = get_db()
    username = request.form.get("username")
    pwd = request.form.get("password")
    public_key = request.form.get("public_key")
    org_id = session.get("org_id")
    hashed = generate_password_hash(pwd)
    u = User(username=username, password=hashed, role="voter", org_id=org_id, public_key=public_key)
    db.add(u); db.commit(); db.close()
    flash("Voter created")
    return redirect(url_for("org_dashboard"))

### VOTER ###
@app.route("/voter/dashboard")
@login_required
@role_required("voter")
def voter_dashboard():
    db = get_db()
    candidates = db.query(Candidate).all()
    s = db.query(Settings).first()
    user_id = session.get("user_id")
    user = db.query(User).get(user_id)
    db.close()
    already_votes = blockchain.find_votes_by_voter(user.public_key) if user and user.public_key else []
    has_voted = len(already_votes) > 0
    voting_active = s.voting_active
    return render_template("voter_dashboard.html", candidates=candidates, voting_active=voting_active, has_voted=has_voted)

@app.route("/voter/cast", methods=["POST"])
@login_required
@role_required("voter")
def voter_cast():
    db = get_db()
    s = get_settings()
    if not s.voting_active:
        flash("Voting not active right now", "danger")
        db.close()
        return redirect(url_for("voter_dashboard"))

    user = db.query(User).get(session["user_id"])
    if not user or not user.public_key:
        flash("Missing public key. Contact organization.", "warning")
        db.close()
        return redirect(url_for("voter_dashboard"))

    if blockchain.find_votes_by_voter(user.public_key):
        flash("You already voted.", "warning")
        db.close()
        return redirect(url_for("voter_dashboard"))

    candidate_id = request.form.get("candidate_id")
    ballot_hash = request.form.get("ballot_hash")
    signature = request.form.get("signature")

    if not verify_signature_hex(user.public_key, ballot_hash, signature):
        flash("Signature verification failed.", "danger")
        db.close()
        return redirect(url_for("voter_dashboard"))

    tx = {
        "voter_pub": user.public_key,
        "voter_id": user.id,
        "candidate_id": int(candidate_id),
        "ballot_hash": ballot_hash,
        "signature": signature,
        "timestamp": time.time()
    }

    blockchain.add_new_transaction(tx)
    flash("✅ Vote submitted successfully.", "success")
    db.close()
    return redirect(url_for("voter_dashboard"))

### RESULTS ###
@app.route("/results")
def results():
    db = get_db()
    s = db.query(Settings).first()

    # Fetch all archived results (past elections)
    past_records = db.query(ResultRecord).order_by(ResultRecord.id.desc()).all()

    # Default placeholders
    current_counts = None
    current_winner = None
    current_declared = False
    current_status = "Voting not started"

    if s:
        # Determine current election status
        if s.voting_active:
            current_status = "Voting in progress"
        elif not s.voting_active and not s.results_declared:
            current_status = "Voting ended – Results not declared"
        elif s.results_declared:
            current_status = "Results declared"
            current_declared = True

    # If current results are declared, show the latest record as current
    if current_declared and past_records:
        latest_record = past_records[0]
        current_counts = latest_record.results_data
        current_winner = latest_record.winner

    db.close()

    return render_template(
        "results.html",
        declared=current_declared,
        status=current_status,
        counts=current_counts,
        winner=current_winner,
        records=past_records
    )

@app.route("/api/chain")
def api_chain():
    return jsonify(blockchain.to_list())

if __name__ == "__main__":
    app.run(debug=True)
