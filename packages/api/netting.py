"""
Netting Engine for BRICS Pay
Computes optimal payment cycles to reduce settlement volume.
"""
from typing import List, Dict, Tuple
from app.ledger import Posting

def compute_netting(postings: List[Posting]) -> List[Posting]:
    """
    Compute net positions for all accounts across all currencies.
    Returns minimized set of transfers needed for settlement.
    """
    # Calculate net position per account per currency
    positions: Dict[str, Dict[str, int]] = {}
    
    for posting in postings:
        account = posting.account_id
        currency = posting.currency
        
        if account not in positions:
            positions[account] = {}
        if currency not in positions[account]:
            positions[account][currency] = 0
            
        # Credit increases balance, debit decreases
        if posting.is_credit:
            positions[account][currency] += posting.amount
        else:
            positions[account][currency] -= posting.amount
    
    # Create netting postings to zero out positions
    netting_postings = []
    timestamp = "2024-01-01T00:00:00Z"  # Would be dynamic in production
    
    for account, currencies in positions.items():
        for currency, balance in currencies.items():
            if balance != 0:
                # Create opposite posting to net out
                is_credit = balance < 0  # If positive balance, need debit to zero
                netting_postings.append(
                    Posting(
                        transaction_id=f"net-{account}-{currency}",
                        account_id=account,
                        currency=currency,
                        amount=abs(balance),
                        is_credit=is_credit,
                        timestamp=timestamp,
                        metadata={"type": "netting", "original_balance": balance}
                    )
                )
    
    return netting_postings
