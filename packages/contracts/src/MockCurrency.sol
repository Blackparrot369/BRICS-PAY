// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title MockCurrency
 * @dev Mock ERC20 token representing a BRICS currency for testing
 */
contract MockCurrency is ERC20 {
    constructor(string memory name, string memory symbol)
        ERC20(name, symbol)
    {
        _mint(msg.sender, 1_000_000_000 * 10 ** decimals());
    }

    /**
     * @dev Mint additional tokens (for testing only)
     */
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}
