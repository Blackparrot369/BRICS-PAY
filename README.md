BRICS-PAY — Hybrid Settlement Network (Prototype)

    A working prototype of a cross-border settlement network where member bankssettle in local currencies — off-chain netting for cost, on-chain finalityfor trust. Settlement is proven, not claimed.

How it works

 member banks            off-chain (FastAPI)              on-chain (EVM)┌─────────┐   payments   ┌──────────────────────┐  commit   ┌──────────────────┐│ bank-a  │─────────────▶│  double-entry ledger │──────────▶│ SettlementHub    ││ bank-b  │   (pending)  │  multilateral netting│  execute  │ submitBatch()    │└─────────┘              │  (N payments → 1 net)│──────────▶│ executeSettlement()                         └──────────────────────┘           └──────────────────┘                                   │                                  │                                   │  confirm(tx_hash)                │ events:                                   ▼                                  │ BatchExecuted                         balances move ONLY after ────────────────────┘ SettlementFinalized                         the tx receipt is verified

The security gate: POST /settlement/confirm replays BatchExecuted andSettlementFinalized events from the transaction receipt and checks everycredit leg against the ledger's netted positions before a single balanceunit moves. A fabricated tx hash → 400, ledger untouched. Finality isverified against the chain, never taken on faith.
Proven end-to-end

3 gross payments (50000 + 75000 + 40000)  → netted to ONE settlement cycle  → submitBatch (commit) + executeSettlement (execute) on-chain  → confirm with verified receipt → "settled"  → chain balanceOf(bank-b) == 165000 == ledger balance ✓fake hash → {"detail":"on-chain verification failed: ..."} → balance still 165000 ✓

Stack
Layer	Tech
Ledger + netting + API	Python 3.13, FastAPI, Pydantic (in-memory MVP)
Settlement	Solidity 0.8.24, OpenZeppelin, Foundry
Chain bridge	web3.py — signing, receipts, event decoding
CI	GitHub Actions: pytest + forge test + slither

Quickstart

# 1. chain + contractsanvilcd packages/contractsforge script script/Deploy.s.sol --rpc-url http://127.0.0.1:8545 --broadcastforge inspect SettlementHub abi --json > deployments/SettlementHub.abi.json# authorize the operator (anvil key #0) to settle BRLcast send 0x5FbDB2315678afecb367f032d93F642f64180aa3 \  "authorizeCurrency(address,address)" \  0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512 \  0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80# 2. APIcd packages/api && python3 -m venv .venv && source .venv/bin/activatepip install -r requirements.txt -r requirements-dev.txtexport RPC_URL=http://127.0.0.1:8545export OPERATOR_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80uvicorn app.main:app --reload    # interactive docs at localhost:8000/docs# 3. testspytest tests/ -v                 # 20 passingcd ../contracts && forge test -vvv   # 4 passing


Security notes

See docs/audit-notes.md for findings logged during thebuild, including: the merkle root is committed but not yet enforced atexecution (HIGH, roadmap: per-leg merkle proofs), and why unit tests thataccepted unverified hashes were rewritten as security-contract tests.
Roadmap

     PostgreSQL persistence (ledger survives restarts)
     Enforce merkle proofs per settlement leg (closes the HIGH finding)
     Operator → multisig; keys → KMS
     ISO 20022 (pacs.008/pacs.002) member messaging
     FX service (cross-currency cycles)
     Multi-currency settlement cycles (RUB/INR/CNY/ZAR)

Contributing

Good first issues are labeled. PRs welcome — every change must keeppytest + forge test green, and anything touching confirm_settlementmust keep the proof gate airtight.
License

Apache-2.0 — see LICENSE.
