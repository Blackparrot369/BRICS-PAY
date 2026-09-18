//! BRICS Pay Cryptographic Primitives
//! 
//! This module provides secure cryptographic operations for the BRICS Pay system,
//! including digital signatures, hashing, and key management.

use sha2::{Sha256, Digest};
use ed25519_dalek::{Keypair, Signature, Signer, Verifier, PublicKey};
use rand::rngs::OsRng;
use serde::{Serialize, Deserialize};

/// Represents a BRICS Pay user account with cryptographic keys
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Account {
    pub account_id: String,
    pub public_key: PublicKey,
    pub country_code: CountryCode,
}

/// BRICS member nation country codes
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum CountryCode {
    BR, // Brazil
    RU, // Russia
    IN, // India
    CN, // China
    ZA, // South Africa
}

impl Account {
    /// Generate a new account with fresh keypair
    pub fn generate(country: CountryCode) -> (Self, Keypair) {
        let mut csprng = OsRng {};
        let keypair = Keypair::generate(&mut csprng);
        
        let account_id = Self::derive_account_id(&keypair.public);
        
        let account = Account {
            account_id,
            public_key: keypair.public,
            country_code: country,
        };
        
        (account, keypair)
    }
    
    /// Derive account ID from public key using SHA-256
    fn derive_account_id(public_key: &PublicKey) -> String {
        let bytes = public_key.as_bytes();
        let hash = Sha256::digest(bytes);
        hex::encode(&hash[..8]) // First 8 bytes for shorter ID
    }
}

/// Transaction data structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transaction {
    pub from: String,
    pub to: String,
    pub amount: u64,
    pub currency: Currency,
    pub timestamp: u64,
    pub nonce: u64,
}

/// Supported currencies in BRICS Pay
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum Currency {
    BRL, // Brazilian Real
    RUB, // Russian Ruble
    INR, // Indian Rupee
    CNY, // Chinese Yuan
    ZAR, // South African Rand
    XBR, // BRICS Reserve Currency (future)
}

impl Transaction {
    /// Create a new transaction
    pub fn new(from: String, to: String, amount: u64, currency: Currency) -> Self {
        Transaction {
            from,
            to,
            amount,
            currency,
            timestamp: 0,
            nonce: 0,
        }
    }
    
    /// Serialize transaction to bytes for signing
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
    pub fn hash(&self) -> [u8; 32] {
        let bytes = self.to_bytes();
        let mut hash = [0u8; 32];
        hash.copy_from_slice(Sha256::digest(&bytes).as_slice());
        hash
    }
    
    /// Sign transaction with private key
    pub fn sign(&self, keypair: &Keypair) -> Signature {
        keypair.sign(&self.to_bytes())
    }
    
    /// Verify transaction signature
    pub fn verify(&self, signature: &Signature, public_key: &PublicKey) -> Result<(), &'static str> {
        public_key.verify(&self.to_bytes(), signature)
            .map_err(|_| "Invalid signature")
    }
}

/// Hash utility functions
pub mod hash {
    use sha2::{Sha256, Digest};
    
    pub fn sha256(data: &[u8]) -> [u8; 32] {
        let mut hash = [0u8; 32];
        hash.copy_from_slice(Sha256::digest(data).as_slice());
        hash
    }
    
    pub fn hash_chain(prev_hash: &[u8; 32], data: &[u8]) -> [u8; 32] {
        let mut hasher = Sha256::new();
        hasher.update(prev_hash);
        hasher.update(data);
        let mut result = [0u8; 32];
        result.copy_from_slice(hasher.finalize().as_slice());
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_account_generation() {
        let (account, _keypair) = Account::generate(CountryCode::IN);
        assert!(!account.account_id.is_empty());
        assert_eq!(account.country_code, CountryCode::IN);
    }
    
    #[test]
    fn test_transaction_signing() {
        let (account, keypair) = Account::generate(CountryCode::BR);
        let tx = Transaction::new(
            account.account_id.clone(),
            "recipient123".to_string(),
            1000,
            Currency::BRL,
        );
        
        let signature = tx.sign(&keypair);
        assert!(tx.verify(&signature, &keypair.public).is_ok());
    }
}
