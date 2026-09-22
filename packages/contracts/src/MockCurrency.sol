// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @dev 2 decimals on purpose — mirrors real fiat units (cent/kopek/paisa/fen),
///      so on-chain amounts map 1:1 to the off-chain ledger's 2dp invariant.
contract MockCurrency is ERC20, Ownable {
    constructor(string memory name, string memory symbol, address centralBank)
        ERC20(name, symbol)
        Ownable(centralBank)
    {}

    function decimals() public pure override returns (uint8) {
        return 2;
    }

    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }
}
