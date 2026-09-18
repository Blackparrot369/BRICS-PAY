// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SettlementHub.sol";
import "../src/MockCurrency.sol";

contract SettlementHubTest is Test {
    SettlementHub public hub;
    MockCurrency public brl;
    MockCurrency public rub;
    
    address public operator = makeAddr("operator");
    address public user1 = makeAddr("user1");
    address public user2 = makeAddr("user2");
    address public user3 = makeAddr("user3");

    function setUp() public {
        hub = new SettlementHub();
        brl = new MockCurrency("Brazilian Real", "BRL");
        rub = new MockCurrency("Russian Ruble", "RUB");
        
        // Authorize operator for currencies - owner is msg.sender (test contract)
        hub.authorizeCurrency(address(brl), operator);
        hub.authorizeCurrency(address(rub), operator);
        
        // Mint tokens to operator for testing
        brl.mint(operator, 10000 * 10 ** 18);
        rub.mint(operator, 10000 * 10 ** 18);
    }

    function test_DeployAndAuthorize() public view {
        assertEq(hub.owner(), address(this));
        assertTrue(hub.authorizedCurrencies(address(brl), operator));
        assertTrue(hub.authorizedCurrencies(address(rub), operator));
    }

    function test_SubmitBatch() public {
        bytes32 merkleRoot = keccak256(abi.encodePacked("test-batch"));
        address[] memory participants = new address[](3);
        participants[0] = user1;
        participants[1] = user2;
        participants[2] = user3;
        
        hub.submitBatch(merkleRoot, participants);
        
        (bytes32 root, uint256 timestamp, bool executed, uint256 count) = hub.getBatch(merkleRoot);
        assertEq(root, merkleRoot);
        assertGt(timestamp, 0);
        assertFalse(executed);
        assertEq(count, 3);
    }

    function test_ExecuteSettlement() public {
        bytes32 merkleRoot = keccak256(abi.encodePacked("settlement-1"));
        address[] memory participants = new address[](2);
        participants[0] = user1;
        participants[1] = user2;
        
        hub.submitBatch(merkleRoot, participants);
        
        // Approve tokens for transfer
        uint256 amount1 = 100 * 10 ** 18;
        uint256 amount2 = 50 * 10 ** 18;
        vm.prank(operator);
        brl.approve(address(hub), amount1 + amount2);
        
        address[] memory recipients = new address[](2);
        recipients[0] = user1;
        recipients[1] = user2;
        
        uint256[] memory amounts = new uint256[](2);
        amounts[0] = amount1;
        amounts[1] = amount2;
        
        vm.prank(operator);
        hub.executeSettlement(merkleRoot, address(brl), recipients, amounts);
        
        assertEq(brl.balanceOf(user1), amount1);
        assertEq(brl.balanceOf(user2), amount2);
        
        (,, bool executed,) = hub.getBatch(merkleRoot);
        assertTrue(executed);
    }

    function test_CannotExecuteTwice() public {
        bytes32 merkleRoot = keccak256(abi.encodePacked("batch-2"));
        address[] memory participants = new address[](1);
        participants[0] = user1;
        
        hub.submitBatch(merkleRoot, participants);
        
        vm.prank(operator);
        brl.approve(address(hub), 100 * 10 ** 18);
        address[] memory recipients = new address[](1);
        recipients[0] = user1;
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = 100 * 10 ** 18;
        
        vm.prank(operator);
        hub.executeSettlement(merkleRoot, address(brl), recipients, amounts);
        
        vm.prank(operator);
        vm.expectRevert("Batch already executed");
        hub.executeSettlement(merkleRoot, address(brl), recipients, amounts);
    }
}
