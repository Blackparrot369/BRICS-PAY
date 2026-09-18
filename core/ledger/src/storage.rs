//! Persistent storage for blockchain ledger

use std::path::Path;
use std::fs::{File, OpenOptions};
use std::io::{Read, Write, BufReader, BufWriter};
use crate::types::Block;

/// Simple file-based block storage
pub struct BlockStore {
    storage_path: String,
}

impl BlockStore {
    /// Create a new block store at the given path
    pub fn new<P: AsRef<Path>>(path: P) -> Self {
        BlockStore {
            storage_path: path.as_ref().to_string_lossy().to_string(),
        }
    }
    
    /// Save a block to disk
    pub fn save_block(&self, block: &Block) -> std::io::Result<()> {
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.storage_path)?;
        
        // Serialize block (simple JSON for now)
        let json = serde_json::to_string(block)?;
        writeln!(file, "{}", json)?;
        
        Ok(())
    }
    
    /// Load all blocks from disk
    pub fn load_blocks(&self) -> std::io::Result<Vec<Block>> {
        if !Path::new(&self.storage_path).exists() {
            return Ok(Vec::new());
        }
        
        let file = File::open(&self.storage_path)?;
        let reader = BufReader::new(file);
        let mut blocks = Vec::new();
        
        for line in std::io::BufRead::lines(reader) {
            let line = line?;
            if let Ok(block) = serde_json::from_str::<Block>(&line) {
                blocks.push(block);
            }
        }
        
        Ok(blocks)
    }
    
    /// Get the latest block from storage
    pub fn get_latest_block(&self) -> std::io::Result<Option<Block>> {
        let blocks = self.load_blocks()?;
        Ok(blocks.into_iter().last())
    }
    
    /// Clear all stored blocks (use with caution!)
    pub fn clear(&self) -> std::io::Result<()> {
        if Path::new(&self.storage_path).exists() {
            std::fs::remove_file(&self.storage_path)?;
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    
    #[test]
    fn test_block_storage() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("blocks.json");
        let store = BlockStore::new(&path);
        
        // Test save and load
        assert!(store.load_blocks().unwrap().is_empty());
        
        // TODO: Add actual block creation and testing
    }
}
