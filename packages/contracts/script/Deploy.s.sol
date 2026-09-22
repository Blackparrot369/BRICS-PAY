// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {SettlementHub} from "../src/SettlementHub.sol";
import {MockCurrency} from "../src/MockCurrency.sol";

/// @dev Deploys hub + 5 mock currencies, writes deployments/local.json
///      in a SINGLE write (serialize-accumulate then one writeJson).
///      Fixes the clobbering bug where each writeJson replaced the file,
///      leaving only the last key behind.
contract Deploy is Script {
    function run() external {
        uint256 deployerKey = vm.envOr(
            "OPERATOR_PRIVATE_KEY",
            uint256(0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80)
        );

        vm.startBroadcast(deployerKey);
        SettlementHub hub = new SettlementHub();
        MockCurrency brl = new MockCurrency("Brazilian Real", "BRL", msg.sender);
        MockCurrency rub = new MockCurrency("Russian Ruble", "RUB", msg.sender);
        MockCurrency inr = new MockCurrency("Indian Rupee", "INR", msg.sender);
        MockCurrency cny = new MockCurrency("Chinese Yuan", "CNY", msg.sender);
        MockCurrency zar = new MockCurrency("South African Rand", "ZAR", msg.sender);
        vm.stopBroadcast();

        // each serializeAddress returns the JSON accumulated SO FAR —
        // reassign it, then write the complete object once
        string memory json = "deployments";
        json = vm.serializeAddress(json, "SettlementHub", address(hub));
        json = vm.serializeAddress(json, "BRL", address(brl));
        json = vm.serializeAddress(json, "RUB", address(rub));
        json = vm.serializeAddress(json, "INR", address(inr));
        json = vm.serializeAddress(json, "CNY", address(cny));
        json = vm.serializeAddress(json, "ZAR", address(zar));
        vm.writeJson(json, "deployments/local.json");

    }
}
