// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title SettlementHub
 * @dev On-chain settlement contract for BRICS Pay system
 * Executes netted transactions with finality after off-chain computation
 */
contract SettlementHub is Ownable {
    struct SettlementBatch {
        bytes32 merkleRoot;
        uint256 timestamp;
        bool executed;
        address[] participants;
    }

    mapping(bytes32 => SettlementBatch) public batches;
    mapping(address => mapping(address => bool)) public authorizedCurrencies;
    
    event BatchSubmitted(bytes32 indexed batchId, bytes32 merkleRoot, address submitter);
    event BatchExecuted(bytes32 indexed batchId, uint256 timestamp);
    event CurrencyAuthorized(address indexed currency, address indexed operator);
    event SettlementFinalized(bytes32 indexed batchId, address indexed token, address recipient, uint256 amount);

    constructor() Ownable(msg.sender) {}

    /**
     * @dev Authorize a currency token for settlement
     * @param token Address of the ERC20 token
     * @param operator Address allowed to operate this currency (e.g., central bank)
     */
    function authorizeCurrency(address token, address operator) external onlyOwner {
        authorizedCurrencies[token][operator] = true;
        emit CurrencyAuthorized(token, operator);
    }

    /**
     * @dev Submit a netted settlement batch from off-chain computation
     * @param merkleRoot Root of the Merkle tree containing settlement proofs
     * @param participants List of addresses involved in this batch
     */
    function submitBatch(bytes32 merkleRoot, address[] calldata participants) external {
        require(!batches[merkleRoot].executed, "Batch already executed");
        
        batches[merkleRoot] = SettlementBatch({
            merkleRoot: merkleRoot,
            timestamp: block.timestamp,
            executed: false,
            participants: participants
        });
        
        emit BatchSubmitted(merkleRoot, merkleRoot, msg.sender);
    }

    /**
     * @dev Execute settlement for a verified batch
     * @param merkleRoot The Merkle root of the batch to execute
     * @param token ERC20 token address for settlement
     * @param recipients Array of recipient addresses
     * @param amounts Array of amounts to transfer
     */
    function executeSettlement(
        bytes32 merkleRoot,
        address token,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external {
        SettlementBatch storage batch = batches[merkleRoot];
        require(batch.timestamp > 0, "Batch does not exist");
        require(!batch.executed, "Batch already executed");
        require(authorizedCurrencies[token][msg.sender], "Not authorized for this currency");
        require(recipients.length == amounts.length, "Length mismatch");

        batch.executed = true;
        
        IERC20 currency = IERC20(token);
        for (uint256 i = 0; i < recipients.length; i++) {
            if (amounts[i] > 0) {
                require(currency.transferFrom(msg.sender, recipients[i], amounts[i]), "Transfer failed");
                emit SettlementFinalized(merkleRoot, token, recipients[i], amounts[i]);
            }
        }
        
        emit BatchExecuted(merkleRoot, block.timestamp);
    }

    /**
     * @dev Get batch details
     */
    function getBatch(bytes32 merkleRoot) external view returns (
        bytes32 root,
        uint256 timestamp,
        bool executed,
        uint256 participantCount
    ) {
        SettlementBatch storage batch = batches[merkleRoot];
        return (batch.merkleRoot, batch.timestamp, batch.executed, batch.participants.length);
    }
}
