"""Full E2E settlement against a live chain. Skips cleanly if no chain.

Enforces the README claim — 'proven end-to-end' — on every run:
3 gross payments -> one netted cycle -> submitBatch + executeSettlement
on-chain -> confirm gated by receipt verification -> chain == ledger.

Amounts are randomized per run so the merkle root is unique and the test
is re-runnable against a persistent anvil.
"""
import json
import os
import random

import pytest

RPC_URL = os.environ.get("RPC_URL", "")
CHAIN_UP = False
if RPC_URL:
    try:
        from web3 import Web3
        CHAIN_UP = Web3(Web3.HTTPProvider(RPC_URL)).is_connected()
    except Exception:
        pass

pytestmark = pytest.mark.skipif(not CHAIN_UP, reason="requires a live chain (anvil)")


def test_full_settlement_e2e():
    import app.main as m
    from fastapi.testclient import TestClient

    client = TestClient(m.app)

    assert client.post("/accounts", json={
        "id": "e2e_a", "owner": "bank-a", "currency": "BRL", "balance": 0}).status_code == 201
    assert client.post("/accounts", json={
        "id": "e2e_b", "owner": "bank-b", "currency": "BRL", "balance": 0}).status_code == 201

    # on-chain balance BEFORE (delta-based so the test re-runs on a persistent chain)
    bank_b_addr = json.loads(open("members.json").read())["bank-b"]
    import app.main as _m
    onchain_before = _m.get_chain().onchain_balance(bank_b_addr, "BRL")

    base = random.randint(100000, 900000)
    amts = [base, base + 25000, base + 15000]
    total = sum(amts)

    for i, amt in enumerate(amts, 1):
        r = client.post("/transactions", json={
            "id": f"e2e_txn_{i}",
            "postings": [
                {"id": f"e2e_p{i}a", "account_id": "e2e_a", "amount": -amt,
                 "currency": "BRL", "transaction_id": f"e2e_txn_{i}"},
                {"id": f"e2e_p{i}b", "account_id": "e2e_b", "amount": amt,
                 "currency": "BRL", "transaction_id": f"e2e_txn_{i}"},
            ]})
        assert r.status_code == 201, r.text

    net = client.post("/netting/compute",
                      json=["e2e_txn_1", "e2e_txn_2", "e2e_txn_3"]).json()
    nid = net["netted_transactions"][0]["id"]

    exec_resp = client.post(f"/settlement/execute/{nid}")
    assert exec_resp.status_code == 200, exec_resp.text
    txh = exec_resp.json()["tx_hash"]

    # THE SECURITY GATE, AUTOMATED: fake hash rejected, zero movement
    fake = client.post(f"/settlement/confirm/{nid}",
                       params={"blockchain_tx_hash": "0x" + "00" * 32})
    assert fake.status_code == 400, fake.text
    assert client.get("/accounts/e2e_b").json()["balance"] == 0, \
        "balances moved without on-chain proof!"

    # real proof settles
    ok = client.post(f"/settlement/confirm/{nid}", params={"blockchain_tx_hash": txh})
    assert ok.status_code == 200 and ok.json()["status"] == "settled", ok.text
    assert client.get("/accounts/e2e_b").json()["balance"] == total

    # chain == ledger, to the unit (delta: cumulative on-chain balance)
    onchain_after = m.get_chain().onchain_balance(bank_b_addr, "BRL")
    assert onchain_after == onchain_before + total, \
        f"on-chain {onchain_after} != {onchain_before} + {total}"
