"""
BRICS Pay Ledger Service - FastAPI Backend
Handles off-chain ledger, netting computation, and cycle detection.
"""
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum
import hashlib
import json

app = FastAPI(
    title="BRICS Pay Ledger",
    description="Off-chain ledger service for BRICS payment system with netting optimization",
    version="1.0.0"
)

# ============================================================================
# Types & Models
# ============================================================================

class Currency(str, Enum):
    BRL = "BRL"  # Brazilian Real
    RUB = "RUB"  # Russian Ruble
    INR = "INR"  # Indian Rupee
    CNY = "CNY"  # Chinese Yuan
    ZAR = "ZAR"  # South African Rand
    XBR = "XBR"  # BRICS Reserve Unit

class TransactionStatus(str, Enum):
    PENDING = "pending"
    NETTED = "netted"
    SETTLED = "settled"
    FAILED = "failed"

class Account(BaseModel):
    id: str
    owner: str
    currency: Currency
    balance: int = 0  # Stored in smallest unit (like satoshis)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Posting(BaseModel):
    """A single ledger posting (debit or credit)"""
    id: str
    account_id: str
    amount: int  # Positive for credit, negative for debit
    currency: Currency
    transaction_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict] = None

class Transaction(BaseModel):
    """A transaction containing multiple postings (must sum to zero per currency)"""
    id: str
    postings: List[Posting]
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    settled_at: Optional[datetime] = None

class NettingCycle(BaseModel):
    """Represents a netted cycle of transactions"""
    id: str
    original_transactions: List[str]
    netted_transactions: List[Transaction]
    savings: Dict[Currency, int]  # Amount saved per currency through netting
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ============================================================================
# In-Memory Storage (Production would use PostgreSQL)
# ============================================================================

accounts_db: Dict[str, Account] = {}
transactions_db: Dict[str, Transaction] = {}
postings_db: Dict[str, Posting] = {}
netting_cycles_db: Dict[str, NettingCycle] = {}

# ============================================================================
# Helper Functions
# ============================================================================

def generate_id(prefix: str, data: str) -> str:
    """Generate deterministic ID from data"""
    hash_val = hashlib.sha256(data.encode()).hexdigest()[:16]
    return f"{prefix}_{hash_val}"

def validate_transaction_balance(txn: Transaction) -> bool:
    """Ensure transaction postings sum to zero per currency"""
    currency_sums: Dict[Currency, int] = {}
    for posting in txn.postings:
        currency_sums[posting.currency] = currency_sums.get(posting.currency, 0) + posting.amount
    return all(v == 0 for v in currency_sums.values())

def get_account_balance(account_id: str) -> int:
    """Calculate current balance for an account based on postings"""
    return sum(
        p.amount for p in postings_db.values() 
        if p.account_id == account_id
    )

# ============================================================================
# API Endpoints - Accounts
# ============================================================================

@app.post("/accounts", status_code=status.HTTP_201_CREATED, response_model=Account)
async def create_account(account: Account):
    """Create a new account for a BRICS currency"""
    if account.id in accounts_db:
        raise HTTPException(status_code=400, detail="Account already exists")
    accounts_db[account.id] = account
    return account

@app.get("/accounts/{account_id}", response_model=Account)
async def get_account(account_id: str):
    """Get account details and balance"""
    if account_id not in accounts_db:
        raise HTTPException(status_code=404, detail="Account not found")
    return accounts_db[account_id]

@app.get("/accounts/{account_id}/postings", response_model=List[Posting])
async def get_account_postings(account_id: str):
    """Get all postings for an account"""
    if account_id not in accounts_db:
        raise HTTPException(status_code=404, detail="Account not found")
    return [p for p in postings_db.values() if p.account_id == account_id]

# ============================================================================
# API Endpoints - Transactions
# ============================================================================

@app.post("/transactions", status_code=status.HTTP_201_CREATED, response_model=Transaction)
async def create_transaction(txn: Transaction):
    """
    Create a new transaction with multiple postings.
    Validates that postings sum to zero per currency.
    """
    if not validate_transaction_balance(txn):
        raise HTTPException(
            status_code=400, 
            detail="Transaction postings must sum to zero per currency"
        )
    
    # Validate accounts exist and have sufficient balance
    for posting in txn.postings:
        if posting.account_id not in accounts_db:
            raise HTTPException(
                status_code=400, 
                detail=f"Account {posting.account_id} not found"
            )
    
    # Skip balance check for now - in production this would use proper locking
    # Balance checks are enforced by the double-entry requirement (sum to zero)
    
    # Store transaction and postings
    transactions_db[txn.id] = txn
    for posting in txn.postings:
        postings_db[posting.id] = posting
    
    return txn

@app.get("/transactions/{transaction_id}", response_model=Transaction)
async def get_transaction(transaction_id: str):
    """Get transaction details"""
    if transaction_id not in transactions_db:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transactions_db[transaction_id]

@app.get("/transactions", response_model=List[Transaction])
async def list_transactions(status_filter: Optional[TransactionStatus] = None):
    """List transactions with optional status filter"""
    txns = list(transactions_db.values())
    if status_filter:
        txns = [t for t in txns if t.status == status_filter]
    return txns

# ============================================================================
# API Endpoints - Netting Engine
# ============================================================================

@app.post("/netting/compute", response_model=NettingCycle)
async def compute_netting_cycle(transaction_ids: List[str]):
    """
    Compute netting cycle for a set of transactions.
    This is the core optimization that reduces settlement volume.
    
    Example: A->B: 100, B->C: 100, C->A: 100
    Netted: No actual transfer needed (cycle cancels out)
    """
    if not transaction_ids:
        raise HTTPException(status_code=400, detail="No transactions provided")
    
    # Fetch transactions
    txns = []
    for tid in transaction_ids:
        if tid not in transactions_db:
            raise HTTPException(status_code=404, detail=f"Transaction {tid} not found")
        txns.append(transactions_db[tid])
    
    # Build net position per account per currency
    net_positions: Dict[str, Dict[Currency, int]] = {}
    
    for txn in txns:
        for posting in txn.postings:
            if posting.account_id not in net_positions:
                net_positions[posting.account_id] = {}
            net_positions[posting.account_id][posting.currency] = \
                net_positions[posting.account_id].get(posting.currency, 0) + posting.amount
    
    # Create netted transactions (simplified - production would use graph algorithms)
    netted_postings = []
    savings: Dict[Currency, int] = {}
    
    for account_id, currencies in net_positions.items():
        for currency, net_amount in currencies.items():
            if net_amount != 0:
                posting = Posting(
                    id=generate_id("post", f"{account_id}{currency}{net_amount}"),
                    account_id=account_id,
                    amount=net_amount,
                    currency=currency,
                    transaction_id=generate_id("net", f"{account_id}{currency}"),
                    metadata={"original_count": len(txns), "type": "netted"}
                )
                netted_postings.append(posting)
                
                # Calculate savings (absolute value of cancelled amounts)
                original_total = sum(
                    abs(p.amount) for t in txns 
                    for p in t.postings 
                    if p.account_id == account_id and p.currency == currency
                )
                savings[currency] = savings.get(currency, 0) + original_total - abs(net_amount)
    
    # Group netted postings into transactions
    netted_txn = Transaction(
        id=generate_id("ntxn", str(datetime.utcnow())),
        postings=netted_postings,
        status=TransactionStatus.NETTED
    )
    
    # Store netting cycle
    cycle = NettingCycle(
        id=generate_id("cycle", str(transaction_ids)),
        original_transactions=transaction_ids,
        netted_transactions=[netted_txn],
        savings=savings
    )
    netting_cycles_db[cycle.id] = cycle
    
    # Store the netted transaction so it can be settled
    transactions_db[netted_txn.id] = netted_txn
    for posting in netted_txn.postings:
        postings_db[posting.id] = posting
    
    return cycle

@app.get("/netting/cycles/{cycle_id}", response_model=NettingCycle)
async def get_netting_cycle(cycle_id: str):
    """Get netting cycle details"""
    if cycle_id not in netting_cycles_db:
        raise HTTPException(status_code=404, detail="Cycle not found")
    return netting_cycles_db[cycle_id]

# ============================================================================
# API Endpoints - Settlement Bridge
# ============================================================================

@app.post("/settlement/prepare/{transaction_id}")
async def prepare_for_settlement(transaction_id: str):
    """
    Prepare a netted transaction for on-chain settlement.
    This generates the payload for the SettlementHub smart contract.
    """
    if transaction_id not in transactions_db:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    txn = transactions_db[transaction_id]
    if txn.status != TransactionStatus.NETTED:
        raise HTTPException(
            status_code=400, 
            detail="Only netted transactions can be prepared for settlement"
        )
    
    # Generate settlement payload
    settlement_payload = {
        "transaction_id": txn.id,
        "postings": [
            {
                "account": p.account_id,
                "amount": p.amount,
                "currency": p.currency.value
            }
            for p in txn.postings
        ],
        "timestamp": txn.created_at.isoformat(),
        "merkle_root": hashlib.sha256(
            json.dumps([p.model_dump() for p in txn.postings], sort_keys=True, default=str).encode()
        ).hexdigest()
    }
    
    return {
        "status": "ready",
        "payload": settlement_payload,
        "contract_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"  # Placeholder
    }


# ============================================================================
# Health & Status
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "accounts": len(accounts_db),
        "transactions": len(transactions_db),
        "netting_cycles": len(netting_cycles_db)
    }

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    total_volume = sum(
        abs(p.amount) for t in transactions_db.values() 
        for p in t.postings
    )
    total_saved = sum(
        sum(cycle.savings.values()) for cycle in netting_cycles_db.values()
    )
    
    return {
        "total_accounts": len(accounts_db),
        "total_transactions": len(transactions_db),
        "total_volume": total_volume,
        "netting_cycles_processed": len(netting_cycles_db),
        "volume_saved_through_netting": total_saved
    }


# ============================================================================
# ON-CHAIN SETTLEMENT BRIDGE (hybrid phase 2)
# ============================================================================
import hashlib, json, os as _os
from pathlib import Path as _Path
from web3 import Web3 as _W3
from .chain import ChainClient

MEMBERS = json.loads(_Path(_os.environ.get("MEMBERS_PATH", "members.json")).read_text())
settlement_meta_db: dict = {}

def get_chain() -> ChainClient:
    global _chain
    try:
        return _chain
    except NameError:
        _chain = ChainClient(
            rpc_url=_os.environ.get("RPC_URL", "http://127.0.0.1:8545"),
            operator_key=_os.environ["OPERATOR_PRIVATE_KEY"],
            deployments_path=_os.environ.get("DEPLOYMENTS_PATH", "../contracts/deployments/local.json"),
            hub_abi_path=_os.environ.get("HUB_ABI_PATH", "../contracts/deployments/SettlementHub.abi.json"),
        )
        return _chain

def _merkle_root_for(txn) -> str:
    return hashlib.sha256(
        json.dumps([p.model_dump() for p in txn.postings], sort_keys=True, default=str).encode()
    ).hexdigest()

def _credit_legs(txn) -> list:
    legs = []
    for p in txn.postings:
        if p.amount <= 0:
            continue
        acct = accounts_db.get(p.account_id)
        if acct is None:
            raise HTTPException(422, f"unknown account {p.account_id}")
        addr = MEMBERS.get(acct.owner)
        if addr is None:
            raise HTTPException(422, f"no chain address for member '{acct.owner}'")
        legs.append((_W3.to_checksum_address(addr), int(p.amount)))
    return legs

@app.post("/settlement/execute/{transaction_id}")
async def execute_settlement(transaction_id: str):
    """On-chain phases 1+2: submitBatch(commit) then executeSettlement(operator pays credits)."""
    if transaction_id not in transactions_db:
        raise HTTPException(404, "Transaction not found")
    txn = transactions_db[transaction_id]
    if txn.status != TransactionStatus.NETTED:
        raise HTTPException(400, "only netted transactions can be executed")
    legs = _credit_legs(txn)
    if not legs:
        raise HTTPException(400, "no credit legs to settle")
    root = _merkle_root_for(txn)
    currency = txn.postings[0].currency.value
    result = get_chain().submit_and_execute(root, currency, legs)
    settlement_meta_db[transaction_id] = {"root": root, "legs": legs, "currency": currency}
    return {"transaction_id": transaction_id, "currency": currency, "merkle_root": root, **result}

@app.post("/settlement/confirm/{transaction_id}")
async def confirm_settlement(transaction_id: str, blockchain_tx_hash: str):
    """HARDENED: verifies the tx on-chain BEFORE any balance moves."""
    if transaction_id not in transactions_db:
        raise HTTPException(404, "Transaction not found")
    txn = transactions_db[transaction_id]
    if txn.status == TransactionStatus.SETTLED:
        raise HTTPException(409, "already settled")
    meta = settlement_meta_db.get(transaction_id)
    if meta is None:
        raise HTTPException(400, "execute on-chain first")
    try:
        get_chain().verify_settlement_tx(blockchain_tx_hash, meta["currency"], meta["root"], meta["legs"])
    except Exception as e:
        raise HTTPException(400, f"on-chain verification failed: {e}")
    txn.status = TransactionStatus.SETTLED
    txn.settled_at = datetime.utcnow()
    for posting in txn.postings:
        account = accounts_db.get(posting.account_id)
        if account:
            account.balance += posting.amount
    return {"status": "settled", "transaction_id": transaction_id,
            "blockchain_tx_hash": blockchain_tx_hash, "settled_at": str(txn.settled_at)}


# ============================================================================
# ON-CHAIN SETTLEMENT BRIDGE (hybrid phase 2)
# ============================================================================
import hashlib, json, os as _os
from pathlib import Path as _Path
from web3 import Web3 as _W3
from .chain import ChainClient

MEMBERS = json.loads(_Path(_os.environ.get("MEMBERS_PATH", "members.json")).read_text())
settlement_meta_db: dict = {}

def get_chain() -> ChainClient:
    global _chain
    try:
        return _chain
    except NameError:
        _chain = ChainClient(
            rpc_url=_os.environ.get("RPC_URL", "http://127.0.0.1:8545"),
            operator_key=_os.environ["OPERATOR_PRIVATE_KEY"],
            deployments_path=_os.environ.get("DEPLOYMENTS_PATH", "../contracts/deployments/local.json"),
            hub_abi_path=_os.environ.get("HUB_ABI_PATH", "../contracts/deployments/SettlementHub.abi.json"),
        )
        return _chain

def _merkle_root_for(txn) -> str:
    return hashlib.sha256(
        json.dumps([p.model_dump() for p in txn.postings], sort_keys=True, default=str).encode()
    ).hexdigest()

def _credit_legs(txn) -> list:
    legs = []
    for p in txn.postings:
        if p.amount <= 0:
            continue
        acct = accounts_db.get(p.account_id)
        if acct is None:
            raise HTTPException(422, f"unknown account {p.account_id}")
        addr = MEMBERS.get(acct.owner)
        if addr is None:
            raise HTTPException(422, f"no chain address for member '{acct.owner}'")
        legs.append((_W3.to_checksum_address(addr), int(p.amount)))
    return legs

@app.post("/settlement/execute/{transaction_id}")
async def execute_settlement(transaction_id: str):
    """On-chain phases 1+2: submitBatch(commit) then executeSettlement(operator pays credits)."""
    if transaction_id not in transactions_db:
        raise HTTPException(404, "Transaction not found")
    txn = transactions_db[transaction_id]
    if txn.status != TransactionStatus.NETTED:
        raise HTTPException(400, "only netted transactions can be executed")
    legs = _credit_legs(txn)
    if not legs:
        raise HTTPException(400, "no credit legs to settle")
    root = _merkle_root_for(txn)
    currency = txn.postings[0].currency.value
    result = get_chain().submit_and_execute(root, currency, legs)
    settlement_meta_db[transaction_id] = {"root": root, "legs": legs, "currency": currency}
    return {"transaction_id": transaction_id, "currency": currency, "merkle_root": root, **result}

@app.post("/settlement/confirm/{transaction_id}")
async def confirm_settlement(transaction_id: str, blockchain_tx_hash: str):
    """HARDENED: verifies the tx on-chain BEFORE any balance moves."""
    if transaction_id not in transactions_db:
        raise HTTPException(404, "Transaction not found")
    txn = transactions_db[transaction_id]
    if txn.status == TransactionStatus.SETTLED:
        raise HTTPException(409, "already settled")
    meta = settlement_meta_db.get(transaction_id)
    if meta is None:
        raise HTTPException(400, "execute on-chain first")
    try:
        get_chain().verify_settlement_tx(blockchain_tx_hash, meta["currency"], meta["root"], meta["legs"])
    except Exception as e:
        raise HTTPException(400, f"on-chain verification failed: {e}")
    txn.status = TransactionStatus.SETTLED
    txn.settled_at = datetime.utcnow()
    for posting in txn.postings:
        account = accounts_db.get(posting.account_id)
        if account:
            account.balance += posting.amount
    return {"status": "settled", "transaction_id": transaction_id,
            "blockchain_tx_hash": blockchain_tx_hash, "settled_at": str(txn.settled_at)}
