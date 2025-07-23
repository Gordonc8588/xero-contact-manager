"""
Business Rules and Constants for Xero Contact Management System
================================================================

This module contains all the business logic, constants, and utility functions
for managing property contacts in the Xero accounting system.
"""

import re
from typing import Dict, Tuple, Optional

# ============================================================================
# CONTACT CODE DEFINITIONS
# ============================================================================

CONTACT_CODES = {
    # Quarterly Billing
    "/1A": "Invoiced quarterly on the 1st",
    "/2A": "Invoiced quarterly on the 5th", 
    "/1B": "Invoiced quarterly on the 12th",
    "/3A": "Invoiced quarterly on the 14th",
    
    # Monthly Billing
    "/3B": "Invoiced monthly on the 1st",
    "/3C": "Invoiced monthly on the 16th",
    "/3D": "Invoiced monthly on the 23rd",
    
    # Payment Types
    "/1C": "One person only pays",
    "/A": "Current customer on a payment plan",
    "/B": "Pays by standing order",
    "/D": "Pays by Direct Debit",
    
    # Special Situations
    "/P": "Past account still due (person moved out but still owes)",
    "/Q": "One off job only",
    "/R": "Refuses to pay. Not billed",
    "/S": "Stopped cleaning the stair. Not billed anymore, but may still owe money",
    
    # Third Party Payers
    "/CR": "Accounts paid for by Castlerock/Edinvar/Places for People",
    "/LH": "Accounts paid for by Link Housing/Curb"
}

# Contact codes that represent active, recurring customers
ACTIVE_CUSTOMER_CODES = ["/1A", "/2A", "/1B", "/3A", "/3B", "/3C", "/3D", "/1C", "/B", "/D", "/A"]

# Contact codes for special situations
INACTIVE_CODES = ["/P", "/Q", "/R", "/S"]

# Third party payer codes
THIRD_PARTY_CODES = ["/CR", "/LH"]

# ============================================================================
# ACCOUNT NUMBER STRUCTURE
# ============================================================================

# Account number format: ABC001234/XX
# Where:
# - ABC: 3 letter property code
# - 001234: 6 digit property identifier (first 8 chars total)
# - 9th character: Sequential counter for accounts at this property
# - /XX: Contact code suffix

ACCOUNT_NUMBER_PATTERN = r'^([A-Z]{3}\d{5})(\d)(/[A-Z0-9]+)$'

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def parse_account_number(account_number: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse an account number into its components.
    
    Args:
        account_number (str): Full account number (e.g., "ANP001042/3B")
        
    Returns:
        tuple: (base_code, sequence_digit, contact_code) or None if invalid
        
    Example:
        parse_account_number("ANP001042/3B") -> ("ANP00104", "2", "/3B")
    """
    match = re.match(ACCOUNT_NUMBER_PATTERN, account_number)
    if match:
        base_code = match.group(1)  # First 8 characters (ANP00104)
        sequence_digit = match.group(2)  # 9th character (2)
        contact_code = match.group(3)  # Contact code (/3B)
        return base_code, sequence_digit, contact_code
    return None

def increment_account_sequence(account_number: str) -> Optional[str]:
    """
    Increment the 9th character (sequence digit) of an account number.
    
    Args:
        account_number (str): Original account number
        
    Returns:
        str: New account number with incremented sequence, or None if invalid
        
    Example:
        increment_account_sequence("ANP001042/3B") -> "ANP001043/3B"
    """
    parsed = parse_account_number(account_number)
    if not parsed:
        return None
        
    base_code, sequence_digit, contact_code = parsed
    
    try:
        new_sequence = str(int(sequence_digit) + 1)
        return f"{base_code}{new_sequence}{contact_code}"
    except ValueError:
        return None

def format_contact_name(account_number: str, flat_number: Optional[str], building_address: str) -> str:
    """
    Format the contact name according to business rules.
    
    Args:
        account_number (str): Account number
        flat_number (str, optional): Flat/unit number (e.g., "Flat 1", "Unit 2A")
        building_address (str): Building number and street name
        
    Returns:
        str: Formatted contact name
        
    Examples:
        format_contact_name("AEP019012", "Flat 1", "19 Argyle Place") 
        -> "AEP019012 - (Flat 1) 19 Argyle Place"
        
        format_contact_name("ANP001043", None, "1 Albion Place")
        -> "ANP001043 - 1 Albion Place"
    """
    if flat_number:
        return f"{account_number} - ({flat_number}) {building_address}"
    else:
        return f"{account_number} - {building_address}"

def validate_account_number(account_number: str) -> bool:
    """
    Validate if an account number follows the correct format.
    
    Args:
        account_number (str): Account number to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    return parse_account_number(account_number) is not None

def validate_contact_code(contact_code: str) -> bool:
    """
    Validate if a contact code is in our defined list.
    
    Args:
        contact_code (str): Contact code to validate (e.g., "/3B")
        
    Returns:
        bool: True if valid contact code, False otherwise
    """
    return contact_code in CONTACT_CODES

def get_contact_code_description(contact_code: str) -> Optional[str]:
    """
    Get the description for a contact code.
    
    Args:
        contact_code (str): Contact code (e.g., "/3B")
        
    Returns:
        str: Description of the contact code, or None if not found
    """
    return CONTACT_CODES.get(contact_code)

def is_active_customer(contact_code: str) -> bool:
    """
    Check if a contact code represents an active customer.
    
    Args:
        contact_code (str): Contact code to check
        
    Returns:
        bool: True if active customer, False otherwise
    """
    return contact_code in ACTIVE_CUSTOMER_CODES

def extract_property_base(account_number: str) -> Optional[str]:
    """
    Extract the property base code (first 8 characters) from account number.
    
    Args:
        account_number (str): Full account number
        
    Returns:
        str: Property base code or None if invalid
        
    Example:
        extract_property_base("ANP001042/3B") -> "ANP00104"
    """
    parsed = parse_account_number(account_number)
    if parsed:
        return parsed[0]  # Return base_code
    return None

# ============================================================================
# EXAMPLE USAGE AND TESTING
# ============================================================================

if __name__ == "__main__":
    # Example usage
    original_account = "ANP001042/3B"
    print(f"Original account: {original_account}")
    
    # Parse account
    parsed = parse_account_number(original_account)
    if parsed:
        base, seq, code = parsed
        print(f"Base: {base}, Sequence: {seq}, Code: {code}")
    
    # Increment sequence
    new_account = increment_account_sequence(original_account)
    print(f"New account: {new_account}")
    
    # Format contact name
    contact_name = format_contact_name("ANP001043", "Flat 3B", "1 Albion Place")
    print(f"Contact name: {contact_name}")
    
    # Get contact code description
    description = get_contact_code_description("/3B")
    print(f"Contact code /3B means: {description}")