"""Bridge to the two-phase SettlementHub (submit -> execute) with proof-gated verification."""
from __future__ import annotations

import json
from pathlib import Path

from web3 import Web3


class ChainClient:
    def __init__(self, rpc_url: str, operator_key: str,
                 deployments_path: str, hub_abi_path: str) -> None:
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"no chain at {rpc_url}")
        self.acct = self.w3.eth.account.from_key(operator_key)

        dep = json.loads(Path(deployments_path).read_text())
        abi = json.loads(Path(hub_abi_path).read_text())

        self.hub_address = Web3.to_checksum_address(dep["SettlementHub"])
        self.tokens = {c: Web3.to_checksum_address(dep[c])
                       for c in ("BRL", "RUB", "INR", "CNY", "ZAR")}
        self.hub = self.w3.eth.contract(address=self.hub_address, abi=abi)

    def _send(self, fn) -> dict:
        tx = fn.build_transaction({
            "from": self.acct.address,
            "nonce": self.w3.eth.get_transaction_count(self.acct.address, "pending"),
            "chainId": self.w3.eth.chain_id,
        })
        signed = self.acct.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        h = self.w3.eth.send_raw_transaction(raw)
        r = self.w3.eth.wait_for_transaction_receipt(h)
        if r["status"] != 1:
            raise RuntimeError(f"tx reverted: {h.hex()}")
        return r

    def submit_and_execute(self, merkle_root_hex: str, currency: str,
                           legs: list[tuple[str, int]]) -> dict:
        """Phases 1+2: commit the batch, then execute it (operator pays credit legs)."""
        root = bytes.fromhex(merkle_root_hex)
        if len(root) != 32:
            raise ValueError("merkle root must be 32 bytes")
        recipients = [a for a, _ in legs]
        amounts = [int(x) for _, x in legs]

        _, ts, executed, _n = self.hub.functions.getBatch(root).call()
        if executed:
            raise ValueError("batch already executed on-chain")
        if ts == 0:  # not committed yet -> phase 1
            self._send(self.hub.functions.submitBatch(root, recipients))

        r = self._send(self.hub.functions.executeSettlement(
            root, self.tokens[currency], recipients, amounts))
        return {"tx_hash": r["transactionHash"].hex(), "block": r["blockNumber"]}

    def verify_settlement_tx(self, tx_hash: str, currency: str,
                             merkle_root_hex: str, legs: list[tuple[str, int]]) -> None:
        """Proof gate: raises unless EVERY credit leg is proven on-chain."""
        r = self.w3.eth.get_transaction_receipt(tx_hash)  # raises if unknown tx
        if r["status"] != 1:
            raise ValueError("tx failed on-chain")
        if r["to"] and Web3.to_checksum_address(r["to"]) != self.hub_address:
            raise ValueError("tx was not sent to our SettlementHub")

        root = bytes.fromhex(merkle_root_hex)
        executed = self.hub.events.BatchExecuted().process_receipt(r)
        if not any(e.args.batchId == root for e in executed):
            raise ValueError("no BatchExecuted event for this merkle root")

        finalized = self.hub.events.SettlementFinalized().process_receipt(r)
        proven = {(Web3.to_checksum_address(e.args.recipient), int(e.args.amount))
                  for e in finalized if e.args.token == self.tokens[currency]}
        for addr, amt in legs:
            if (addr, amt) not in proven:
                raise ValueError(f"credit leg not proven on-chain: {addr} for {amt}")
