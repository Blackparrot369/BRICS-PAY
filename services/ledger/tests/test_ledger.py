"""
Test suite for BRICS Pay Ledger Service
Tests accounts, transactions, netting engine, and settlement bridge.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app, accounts_db, transactions_db, postings_db, netting_cycles_db

client = TestClient(app)

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def clear_dbs():
    """Clear all databases before each test"""
    accounts_db.clear()
    transactions_db.clear()
    postings_db.clear()
    netting_cycles_db.clear()
    yield

@pytest.fixture
def sample_accounts():
    """Create sample accounts for testing"""
    accounts = [
        {"id": "acc_brazil_001", "owner": "Banco do Brasil", "currency": "BRL"},
        {"id": "acc_russia_001", "owner": "Sberbank", "currency": "RUB"},
        {"id": "acc_india_001", "owner": "SBI", "currency": "INR"},
        {"id": "acc_china_001", "owner": "ICBC", "currency": "CNY"},
        {"id": "acc_sa_001", "owner": "Standard Bank", "currency": "ZAR"},
    ]
    for acc in accounts:
        client.post("/accounts", json=acc)
    return accounts

@pytest.fixture
def sample_funded_accounts(sample_accounts):
    """Create accounts with initial funding transactions"""
    # Fund each account with their currency
    funding_txns = [
        {
            "id": "fund_brl",
            "postings": [
                {"id": "fp1", "account_id": "acc_central_brl", "amount": -1000000, "currency": "BRL", "transaction_id": "fund_brl"},
                {"id": "fp2", "account_id": "acc_brazil_001", "amount": 1000000, "currency": "BRL", "transaction_id": "fund_brl"},
            ]
        },
        {
            "id": "fund_rub",
            "postings": [
                {"id": "fp3", "account_id": "acc_central_rub", "amount": -1000000, "currency": "RUB", "transaction_id": "fund_rub"},
                {"id": "fp4", "account_id": "acc_russia_001", "amount": 1000000, "currency": "RUB", "transaction_id": "fund_rub"},
            ]
        },
        {
            "id": "fund_inr",
            "postings": [
                {"id": "fp5", "account_id": "acc_central_inr", "amount": -1000000, "currency": "INR", "transaction_id": "fund_inr"},
                {"id": "fp6", "account_id": "acc_india_001", "amount": 1000000, "currency": "INR", "transaction_id": "fund_inr"},
            ]
        },
    ]
    
    # Create central bank accounts first
    central_accounts = [
        {"id": "acc_central_brl", "owner": "Central Bank Brazil", "currency": "BRL"},
        {"id": "acc_central_rub", "owner": "Central Bank Russia", "currency": "RUB"},
        {"id": "acc_central_inr", "owner": "Reserve Bank India", "currency": "INR"},
    ]
    for acc in central_accounts:
        client.post("/accounts", json=acc)
    
    # Post funding transactions
    for txn in funding_txns:
        client.post("/transactions", json=txn)
    
    return sample_accounts

@pytest.fixture
def sample_transaction(sample_funded_accounts):
    """Create a sample multi-party transaction"""
    txn = {
        "id": "txn_001",
        "postings": [
            {"id": "post_001", "account_id": "acc_brazil_001", "amount": -10000, "currency": "BRL", "transaction_id": "txn_001"},
            {"id": "post_002", "account_id": "acc_russia_001", "amount": 10000, "currency": "BRL", "transaction_id": "txn_001"},
        ],
        "status": "pending"
    }
    response = client.post("/transactions", json=txn)
    return response.json()

# ============================================================================
# Account Tests
# ============================================================================

def test_create_account():
    """Test account creation"""
    account = {
        "id": "acc_test_001",
        "owner": "Test Bank",
        "currency": "BRL"
    }
    response = client.post("/accounts", json=account)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "acc_test_001"
    assert data["owner"] == "Test Bank"
    assert data["currency"] == "BRL"
    assert data["balance"] == 0

def test_get_account(sample_accounts):
    """Test retrieving an account"""
    response = client.get("/accounts/acc_brazil_001")
    assert response.status_code == 200
    data = response.json()
    assert data["owner"] == "Banco do Brasil"
    assert data["currency"] == "BRL"

def test_get_nonexistent_account():
    """Test 404 for nonexistent account"""
    response = client.get("/accounts/nonexistent")
    assert response.status_code == 404

def test_duplicate_account():
    """Test creating duplicate account fails"""
    account = {"id": "acc_dup", "owner": "Bank A", "currency": "BRL"}
    client.post("/accounts", json=account)
    response = client.post("/accounts", json=account)
    assert response.status_code == 400

# ============================================================================
# Transaction Tests
# ============================================================================

def test_create_balanced_transaction(sample_funded_accounts):
    """Test creating a balanced transaction"""
    txn = {
        "id": "txn_test_001",
        "postings": [
            {"id": "p1", "account_id": "acc_brazil_001", "amount": -5000, "currency": "BRL", "transaction_id": "txn_test_001"},
            {"id": "p2", "account_id": "acc_russia_001", "amount": 5000, "currency": "BRL", "transaction_id": "txn_test_001"},
        ]
    }
    response = client.post("/transactions", json=txn)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert len(data["postings"]) == 2

def test_create_unbalanced_transaction_fails(sample_funded_accounts):
    """Test that unbalanced transactions are rejected"""
    txn = {
        "id": "txn_bad_001",
        "postings": [
            {"id": "p1", "account_id": "acc_brazil_001", "amount": -5000, "currency": "BRL", "transaction_id": "txn_bad_001"},
            {"id": "p2", "account_id": "acc_russia_001", "amount": 3000, "currency": "BRL", "transaction_id": "txn_bad_001"},  # Doesn't sum to zero
        ]
    }
    response = client.post("/transactions", json=txn)
    assert response.status_code == 400
    assert "sum to zero" in response.json()["detail"]

def test_transaction_nonexistent_account():
    """Test transaction with nonexistent account fails"""
    txn = {
        "id": "txn_bad_002",
        "postings": [
            {"id": "p1", "account_id": "nonexistent", "amount": -5000, "currency": "BRL", "transaction_id": "txn_bad_002"},
            {"id": "p2", "account_id": "acc_brazil_001", "amount": 5000, "currency": "BRL", "transaction_id": "txn_bad_002"},
        ]
    }
    response = client.post("/transactions", json=txn)
    assert response.status_code == 400

def test_get_transaction(sample_transaction):
    """Test retrieving a transaction"""
    response = client.get(f"/transactions/{sample_transaction['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_transaction["id"]

def test_list_transactions(sample_transaction):
    """Test listing transactions with filter"""
    # Get all
    response = client.get("/transactions")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    
    # Filter by status
    response = client.get("/transactions?status_filter=pending")
    assert response.status_code == 200
    assert all(t["status"] == "pending" for t in response.json())

# ============================================================================
# Netting Engine Tests
# ============================================================================

def test_compute_netting_cycle_simple(sample_funded_accounts):
    """Test basic netting cycle computation"""
    # Create circular transactions: A->B->C->A
    txns = [
        {
            "id": "txn_circle_1",
            "postings": [
                {"id": "p1", "account_id": "acc_brazil_001", "amount": -100, "currency": "BRL", "transaction_id": "txn_circle_1"},
                {"id": "p2", "account_id": "acc_russia_001", "amount": 100, "currency": "BRL", "transaction_id": "txn_circle_1"},
            ]
        },
        {
            "id": "txn_circle_2",
            "postings": [
                {"id": "p3", "account_id": "acc_russia_001", "amount": -100, "currency": "BRL", "transaction_id": "txn_circle_2"},
                {"id": "p4", "account_id": "acc_india_001", "amount": 100, "currency": "BRL", "transaction_id": "txn_circle_2"},
            ]
        },
        {
            "id": "txn_circle_3",
            "postings": [
                {"id": "p5", "account_id": "acc_india_001", "amount": -100, "currency": "BRL", "transaction_id": "txn_circle_3"},
                {"id": "p6", "account_id": "acc_brazil_001", "amount": 100, "currency": "BRL", "transaction_id": "txn_circle_3"},
            ]
        }
    ]
    
    # Submit transactions
    txn_ids = []
    for txn in txns:
        resp = client.post("/transactions", json=txn)
        assert resp.status_code == 201
        txn_ids.append(resp.json()["id"])
    
    # Compute netting
    response = client.post("/netting/compute", json=txn_ids)
    assert response.status_code == 200
    data = response.json()
    
    assert "id" in data
    assert len(data["original_transactions"]) == 3
    assert "savings" in data
    # In a perfect circle, net positions should be zero
    # Savings should equal the total volume that was cancelled

def test_compute_netting_partial(sample_funded_accounts):
    """Test netting where not all amounts cancel"""
    txns = [
        {
            "id": "txn_partial_1",
            "postings": [
                {"id": "p1", "account_id": "acc_brazil_001", "amount": -100, "currency": "BRL", "transaction_id": "txn_partial_1"},
                {"id": "p2", "account_id": "acc_russia_001", "amount": 100, "currency": "BRL", "transaction_id": "txn_partial_1"},
            ]
        },
        {
            "id": "txn_partial_2",
            "postings": [
                {"id": "p3", "account_id": "acc_russia_001", "amount": -50, "currency": "BRL", "transaction_id": "txn_partial_2"},
                {"id": "p4", "account_id": "acc_india_001", "amount": 50, "currency": "BRL", "transaction_id": "txn_partial_2"},
            ]
        }
    ]
    
    txn_ids = []
    for txn in txns:
        resp = client.post("/transactions", json=txn)
        assert resp.status_code == 201
        txn_ids.append(resp.json()["id"])
    
    response = client.post("/netting/compute", json=txn_ids)
    assert response.status_code == 200
    data = response.json()
    
    # Russia should have net +50 (received 100, sent 50)
    # Brazil should have net -100
    # India should have net +50

def test_netting_empty_transaction_list():
    """Test netting with empty list fails"""
    response = client.post("/netting/compute", json=[])
    assert response.status_code == 400

def test_netting_nonexistent_transaction():
    """Test netting with nonexistent transaction fails"""
    response = client.post("/netting/compute", json=["nonexistent_txn"])
    assert response.status_code == 404

def test_get_netting_cycle(sample_funded_accounts):
    """Test retrieving a netting cycle"""
    # Create and net a transaction
    txn = {
        "id": "txn_for_cycle",
        "postings": [
            {"id": "p1", "account_id": "acc_brazil_001", "amount": -100, "currency": "BRL", "transaction_id": "txn_for_cycle"},
            {"id": "p2", "account_id": "acc_russia_001", "amount": 100, "currency": "BRL", "transaction_id": "txn_for_cycle"},
        ]
    }
    client.post("/transactions", json=txn)
    
    response = client.post("/netting/compute", json=["txn_for_cycle"])
    cycle_id = response.json()["id"]
    
    response = client.get(f"/netting/cycles/{cycle_id}")
    assert response.status_code == 200
    assert response.json()["id"] == cycle_id

# ============================================================================
# Settlement Bridge Tests
# ============================================================================

def test_prepare_settlement(sample_funded_accounts):
    """Test preparing a netted transaction for settlement"""
    # Create and net a transaction
    txn = {
        "id": "txn_settle_001",
        "postings": [
            {"id": "p1", "account_id": "acc_brazil_001", "amount": -100, "currency": "BRL", "transaction_id": "txn_settle_001"},
            {"id": "p2", "account_id": "acc_russia_001", "amount": 100, "currency": "BRL", "transaction_id": "txn_settle_001"},
        ]
    }
    client.post("/transactions", json=txn)
    net_response = client.post("/netting/compute", json=["txn_settle_001"])
    netted_txn_id = net_response.json()["netted_transactions"][0]["id"]
    
    # Prepare for settlement
    response = client.post(f"/settlement/prepare/{netted_txn_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "payload" in data
    assert "contract_address" in data

def test_prepare_non_netted_transaction_fails(sample_funded_accounts):
    """Test that pending transactions cannot be prepared for settlement"""
    txn = {
        "id": "txn_pending_settle",
        "postings": [
            {"id": "p1", "account_id": "acc_brazil_001", "amount": -100, "currency": "BRL", "transaction_id": "txn_pending_settle"},
            {"id": "p2", "account_id": "acc_russia_001", "amount": 100, "currency": "BRL", "transaction_id": "txn_pending_settle"},
        ]
    }
    client.post("/transactions", json=txn)
    
    # Try to prepare without netting
    response = client.post("/settlement/prepare/txn_pending_settle")
    assert response.status_code == 400
    assert "netted" in response.json()["detail"].lower()

def test_confirm_settlement(sample_funded_accounts):
    """Test confirming on-chain settlement"""
    # Create and net a transaction
    txn = {
        "id": "txn_confirm_001",
        "postings": [
            {"id": "p1", "account_id": "acc_brazil_001", "amount": -100, "currency": "BRL", "transaction_id": "txn_confirm_001"},
            {"id": "p2", "account_id": "acc_russia_001", "amount": 100, "currency": "BRL", "transaction_id": "txn_confirm_001"},
        ]
    }
    client.post("/transactions", json=txn)
    net_response = client.post("/netting/compute", json=["txn_confirm_001"])
    netted_txn_id = net_response.json()["netted_transactions"][0]["id"]
    
    # Confirm settlement
    blockchain_hash = "0xabc123def456..."
    response = client.post(f"/settlement/confirm/{netted_txn_id}?blockchain_tx_hash={blockchain_hash}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "settled"
    assert data["blockchain_tx_hash"] == blockchain_hash
    
    # Verify transaction status updated
    txn_response = client.get(f"/transactions/{netted_txn_id}")
    assert txn_response.json()["status"] == "settled"

# ============================================================================
# Health & Stats Tests
# ============================================================================

def test_health_check():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "accounts" in data
    assert "transactions" in data

def test_stats_endpoint(sample_funded_accounts, sample_transaction):
    """Test statistics endpoint"""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_accounts"] >= 5
    assert data["total_transactions"] >= 1
    assert "total_volume" in data
    assert "volume_saved_through_netting" in data

# ============================================================================
# Integration Test: Full Flow
# ============================================================================

def test_full_payment_flow():
    """Test complete payment flow: accounts -> transactions -> netting -> settlement"""
    # 1. Create accounts
    accounts = [
        {"id": "acc_a", "owner": "Bank A", "currency": "XBR", "balance": 10000},
        {"id": "acc_b", "owner": "Bank B", "currency": "XBR", "balance": 10000},
        {"id": "acc_c", "owner": "Bank C", "currency": "XBR", "balance": 10000},
    ]
    for acc in accounts:
        client.post("/accounts", json=acc)
    
    # 2. Create circular transactions
    txns = [
        {
            "id": "flow_1",
            "postings": [
                {"id": "f1p1", "account_id": "acc_a", "amount": -500, "currency": "XBR", "transaction_id": "flow_1"},
                {"id": "f1p2", "account_id": "acc_b", "amount": 500, "currency": "XBR", "transaction_id": "flow_1"},
            ]
        },
        {
            "id": "flow_2",
            "postings": [
                {"id": "f2p1", "account_id": "acc_b", "amount": -500, "currency": "XBR", "transaction_id": "flow_2"},
                {"id": "f2p2", "account_id": "acc_c", "amount": 500, "currency": "XBR", "transaction_id": "flow_2"},
            ]
        },
        {
            "id": "flow_3",
            "postings": [
                {"id": "f3p1", "account_id": "acc_c", "amount": -500, "currency": "XBR", "transaction_id": "flow_3"},
                {"id": "f3p2", "account_id": "acc_a", "amount": 500, "currency": "XBR", "transaction_id": "flow_3"},
            ]
        }
    ]
    
    for txn in txns:
        resp = client.post("/transactions", json=txn)
        assert resp.status_code == 201
    
    # 3. Compute netting (should cancel out completely)
    net_response = client.post("/netting/compute", json=["flow_1", "flow_2", "flow_3"])
    assert net_response.status_code == 200
    cycle = net_response.json()
    
    # 4. Prepare for settlement
    netted_txn_id = cycle["netted_transactions"][0]["id"]
    prep_response = client.post(f"/settlement/prepare/{netted_txn_id}")
    assert prep_response.status_code == 200
    
    # 5. Confirm settlement
    settle_response = client.post(
        f"/settlement/confirm/{netted_txn_id}",
        params={"blockchain_tx_hash": "0xsettlement123"}
    )
    assert settle_response.status_code == 200
    
    # 6. Verify final state
    stats = client.get("/stats").json()
    assert stats["total_transactions"] >= 4  # 3 original + 1 netted
    assert stats["netting_cycles_processed"] >= 1
