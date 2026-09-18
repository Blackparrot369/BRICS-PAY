//! Core data types for BRICS Pay Ledger

use sha2::{Sha256, Digest};

/// Hash type (32-byte SHA-256)
pub type Hash = [u8; 32];

/// Supported currencies in BRICS Pay
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Currency {
    BRL, // Brazilian Real
    RUB, // Russian Ruble
    INR, // Indian Rupee
    CNY, // Chinese Yuan
    ZAR, // South African Rand
    XBR, // BRICS Reserve Currency (future)
}

/// BRICS member nation country codes
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CountryCode {
    BR, // Brazil
    RU, // Russia
    IN, // India
    CN, // China
    ZA, // South Africa
}

/// Transaction structure
#[derive(Debug, Clone)]
pub struct Transaction {
    pub from: String,
    pub to: String,
    pub amount: u64,
    pub currency: Currency,
    pub timestamp: u64,
    pub nonce: u64,
}

impl Transaction {
    /// Serialize transaction to bytes for hashing
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut bytes = Vec::new();
        bytes.extend_from_slice(self.from.as_bytes());
        bytes.extend_from_slice(self.to.as_bytes());
        bytes.extend_from_slice(&self.amount.to_le_bytes());
        bytes.extend_from_slice(&(self.currency as u8).to_le_bytes());
        bytes.extend_from_slice(&self.timestamp.to_le_bytes());
        bytes.extend_from_slice(&self.nonce.to_le_bytes());
        bytes
    }
    
    /// Compute transaction hash
    pub fn hash(&self) -> Hash {
        let bytes = self.to_bytes();
        let mut hash = [0u8; 32];
        hash.copy_from_slice(Sha256::digest(&bytes).as_slice());
        hash
    }
}

/// Block header structure
#[derive(Debug, Clone)]
pub struct BlockHeader {
    pub version: u32,
    pub height: u64,
    pub prev_hash: Hash,
    pub merkle_root: Hash,
    pub timestamp: u64,
    pub validator_id: String,
}

impl BlockHeader {
    /// Serialize header to bytes for hashing
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut bytes = Vec::new();
        bytes.extend_from_slice(&self.version.to_le_bytes());
        bytes.extend_from_slice(&self.height.to_le_bytes());
        bytes.extend_from_slice(&self.prev_hash);
        bytes.extend_from_slice(&self.merkle_root);
        bytes.extend_from_slice(&self.timestamp.to_le_bytes());
        bytes.extend_from_slice(self.validator_id.as_bytes());
        bytes
    }
    
    /// Compute header hash
    pub fn hash(&self) -> Hash {
        let bytes = self.to_bytes();
        let mut hash = [0u8; 32];
        hash.copy_from_slice(Sha256::digest(&bytes).as_slice());
        hash
    }
}

/// Block structure containing transactions
#[derive(Debug, Clone)]
pub struct Block {
    pub header: BlockHeader,
    pub transactions: Vec<Transaction>,
    pub signature: Vec<u8>,
}

impl Block {
    /// Compute merkle root of transactions
    pub fn compute_merkle_root(transactions: &[Transaction]) -> Hash {
        if transactions.is_empty() {
            return [0u8; 32];
        }
        
        if transactions.len() == 1 {
            return transactions[0].hash();
        }
        
        let mut hashes: Vec<Hash> = transactions.iter().map(|tx| tx.hash()).collect();
        
        while hashes.len() > 1 {
            let mut new_hashes = Vec::new();
            for i in (0..hashes.len()).step_by(2) {
                let left = hashes[i];
                let right = if i + 1 < hashes.len() {
                    hashes[i + 1]
                } else {
                    left
                };
                
                let mut hasher = Sha256::new();
                hasher.update(&left);
                hasher.update(&right);
                let mut result = [0u8; 32];
                result.copy_from_slice(hasher.finalize().as_slice());
                new_hashes.push(result);
            }
            hashes = new_hashes;
        }
        
        hashes[0]
    }
    
    /// Compute block hash
    pub fn hash(&self) -> Hash {
        self.header.hash()
    }
    
    /// Verify merkle root matches transactions
    pub fn verify_merkle_root(&self) -> bool {
        let computed_root = Self::compute_merkle_root(&self.transactions);
        computed_root == self.header.merkle_root
    }
}
