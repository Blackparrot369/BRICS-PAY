//! Block and transaction validation logic

use crate::types::{Block, Transaction};

/// Validate a block against the previous block
pub fn validate_block(current: &Block, prev: &Block) -> bool {
    // Check previous hash linkage
    if current.header.prev_hash != prev.hash() {
        return false;
    }
    
    // Check height is sequential
    if current.header.height != prev.header.height + 1 {
        return false;
    }
    
    // Verify merkle root
    if !current.verify_merkle_root() {
        return false;
    }
    
    // Validate all transactions
    for tx in &current.transactions {
        if !validate_transaction(tx) {
            return false;
        }
    }
    
    true
}

/// Validate a single transaction
pub fn validate_transaction(tx: &Transaction) -> bool {
    // Check non-empty addresses
    if tx.from.is_empty() || tx.to.is_empty() {
        return false;
    }
    
    // Genesis transaction is special
    if tx.from == "GENESIS" {
        return tx.amount == 0;
    }
    
    // Check positive amount
    if tx.amount == 0 {
        return false;
    }
    
    // Check timestamp is reasonable (not too far in future)
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    if tx.timestamp > now + 3600 { // Allow 1 hour clock skew
        return false;
    }
    
    true
}

/// Validate transaction signature (placeholder - integrates with crypto module)
pub fn verify_transaction_signature(_tx: &Transaction, _signature: &[u8], _public_key: &[u8]) -> bool {
    // TODO: Integrate with brics-crypto module
    true
}
