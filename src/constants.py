# “””
Business Rules and Constants for Xero Contact Management System

This module contains all the business logic, constants, and utility functions
for managing property contacts in the Xero accounting system.

UPDATED: Now includes detailed billing schedule information for invoice splitting.
“””

import re
from typing import Dict, Tuple, Optional

# ============================================================================

# CONTACT CODE DEFINITIONS

# ============================================================================

CONTACT_CODES = {
# Quarterly Billing
“/1A”: “Invoiced quarterly on the 1st”,
“/2A”: “Invoiced quarterly on the 5th”,
“/1B”: “Invoiced quarterly on the 12th”,
“/3A”: “Invoiced quarterly on the 14th”,

```
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
```

}

# Contact codes that represent active, recurring customers

ACTIVE_CUSTOMER_CODES = [”/1A”, “/2A”, “/1B”, “/3A”, “/3B”, “/3C”, “/3D”, “/1C”, “/B”, “/D”, “/A”]

# Contact codes for special situations

INACTIVE_CODES = [”/P”, “/Q”, “/R”, “/S”]

# Third party payer codes

THIRD_PARTY_CODES = [”/CR”, “/LH”]

# ============================================================================

# BILLING SCHEDULE DEFINITIONS

# ============================================================================

# Standard billing periods (used for invoice splitting calculations)

BILLING_PERIODS = {
“quarterly”: 90,  # days
“monthly”: 30     # days
}

# Detailed billing schedules for each contact code

# Used by invoice splitting module to determine invoice periods

BILLING_SCHEDULES = {
# Quarterly Billing (90-day periods)
“/1A”: {
“frequency”: “quarterly”,
“start_day”: 1,
“period_days”: 90,
“description”: “Quarterly billing starting 1st of quarter (Jan, Apr, Jul, Oct)”
},
“/2A”: {
“frequency”: “quarterly”,
“start_day”: 5,
“period_days”: 90,
“description”: “Quarterly billing starting 5th of quarter (Jan, Apr, Jul, Oct)”
},
“/1B”: {
“frequency”: “quarterly”,
“start_day”: 12,
“period_days”: 90,
“description”: “Quarterly billing starting 12th of quarter (Jan, Apr, Jul, Oct)”
},
“/3A”: {
“frequency”: “quarterly”,
“start_day”: 14,
“period_days”: 90,
“description”: “Quarterly billing starting 14th of quarter (Jan, Apr, Jul, Oct)”
},

```
# Monthly Billing (30-day periods)
"/3B": {
    "frequency": "monthly", 
    "start_day": 1,
    "period_days": 30,
    "description": "Monthly billing starting 1st of each month"
},
"/3C": {
    "frequency": "monthly", 
    "start_day": 16,
    "period_days": 30,
    "description": "Monthly billing starting 16th of each month"
},
"/3D": {
    "frequency": "monthly", 
    "start_day": 23,
    "period_days": 30,
    "description": "Monthly billing starting 23rd of each month"
},

# Payment Types (assume quarterly billing as default)
"/1C": {
    "frequency": "quarterly", 
    "start_day": 1,
    "period_days": 90,
    "description": "One person only pays - quarterly billing (default)"
},
"/A": {
    "frequency": "quarterly", 
    "start_day": 1,
    "period_days": 90,
    "description": "Payment plan customer - quarterly billing (default)"
},
"/B": {
    "frequency": "quarterly", 
    "start_day": 1,
    "period_days": 90,
    "description": "Standing order customer - quarterly billing (default)"
},
"/D": {
    "frequency": "quarterly", 
    "start_day": 1,
    "period_days": 90,
    "description": "Direct debit customer - quarterly billing (default)"
},

# Special Situations (these typically don't have regular billing)
"/P": {
    "frequency": "irregular", 
    "start_day": None,
    "period_days": None,
    "description": "Past account still due - no regular billing"
},
"/Q": {
    "frequency": "one-off", 
    "start_day": None,
    "period_days": None,
    "description": "One off job only - no regular billing"
},
"/R": {
    "frequency": "none", 
    "start_day": None,
    "period_days": None,
    "description": "Refuses to pay - not billed"
},
"/S": {
    "frequency": "none", 
    "start_day": None,
    "period_days": None,
    "description": "Stopped cleaning - not billed anymore"
},

# Third Party Payers (assume quarterly billing)
"/CR": {
    "frequency": "quarterly", 
    "start_day": 1,
    "period_days": 90,
    "description": "Castlerock/Edinvar/Places for People - quarterly billing"
},
"/LH": {
    "frequency": "quarterly", 
    "start_day": 1,
    "period_days": 90,
    "description": "Link Housing/Curb - quarterly billing"
}
```

}

# Quarterly start months (for calculating billing periods)

QUARTERLY_MONTHS = [1, 4, 7, 10]  # January, April, July, October

# ============================================================================

# ACCOUNT NUMBER STRUCTURE

# ============================================================================

# Account number format: ABC001234/XX

# Where:

# - ABC: 3 letter property code

# - 001234: 6 digit property identifier (first 8 chars total)

# - 9th character: Sequential counter for accounts at this property

# - /XX: Contact code suffix

ACCOUNT_NUMBER_PATTERN = r’^([A-Z]{3}\d{5})(\d)(/[A-Z0-9]+)$’

# ============================================================================

# UTILITY FUNCTIONS

# ============================================================================

def parse_account_number(account_number: str) -> Optional[Tuple[str, str, str]]:
“””
Parse an account number into its components.

```
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
```

def increment_account_sequence(account_number: str) -> Optional[str]:
“””
Increment the 9th character (sequence digit) of an account number.

```
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
```

def format_contact_name(account_number: str, flat_number: Optional[str], building_address: str) -> str:
“””
Format the contact name according to business rules.

```
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
```

def validate_account_number(account_number: str) -> bool:
“””
Validate if an account number follows the correct format.

```
Args:
    account_number (str): Account number to validate
    
Returns:
    bool: True if valid format, False otherwise
"""
return parse_account_number(account_number) is not None
```

def validate_contact_code(contact_code: str) -> bool:
“””
Validate if a contact code is in our defined list.

```
Args:
    contact_code (str): Contact code to validate (e.g., "/3B")
    
Returns:
    bool: True if valid contact code, False otherwise
"""
return contact_code in CONTACT_CODES
```

def get_contact_code_description(contact_code: str) -> Optional[str]:
“””
Get the description for a contact code.

```
Args:
    contact_code (str): Contact code (e.g., "/3B")
    
Returns:
    str: Description of the contact code, or None if not found
"""
return CONTACT_CODES.get(contact_code)
```

def is_active_customer(contact_code: str) -> bool:
“””
Check if a contact code represents an active customer.

```
Args:
    contact_code (str): Contact code to check
    
Returns:
    bool: True if active customer, False otherwise
"""
return contact_code in ACTIVE_CUSTOMER_CODES
```

def extract_property_base(account_number: str) -> Optional[str]:
“””
Extract the property base code (first 8 characters) from account number.

```
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
```

# ============================================================================

# NEW: BILLING SCHEDULE UTILITY FUNCTIONS

# ============================================================================

def get_billing_schedule(contact_code: str) -> Optional[Dict]:
“””
Get the billing schedule for a contact code.

```
Args:
    contact_code (str): Contact code (e.g., "/3B")
    
Returns:
    dict: Billing schedule information or None if not found
"""
return BILLING_SCHEDULES.get(contact_code)
```

def get_billing_frequency(contact_code: str) -> Optional[str]:
“””
Get the billing frequency for a contact code.

```
Args:
    contact_code (str): Contact code (e.g., "/3B")
    
Returns:
    str: Billing frequency ("monthly", "quarterly", etc.) or None if not found
"""
schedule = get_billing_schedule(contact_code)
return schedule.get('frequency') if schedule else None
```

def get_billing_period_days(contact_code: str) -> Optional[int]:
“””
Get the billing period in days for a contact code.

```
Args:
    contact_code (str): Contact code (e.g., "/3B")
    
Returns:
    int: Number of days in billing period (30 for monthly, 90 for quarterly) or None if not found
"""
schedule = get_billing_schedule(contact_code)
return schedule.get('period_days') if schedule else None
```

def get_billing_start_day(contact_code: str) -> Optional[int]:
“””
Get the billing start day for a contact code.

```
Args:
    contact_code (str): Contact code (e.g., "/3B")
    
Returns:
    int: Day of month when billing starts (1, 5, 12, 14, 16, 23) or None if not found
"""
schedule = get_billing_schedule(contact_code)
return schedule.get('start_day') if schedule else None
```

def is_regular_billing_code(contact_code: str) -> bool:
“””
Check if a contact code has regular billing (monthly or quarterly).

```
Args:
    contact_code (str): Contact code to check
    
Returns:
    bool: True if has regular billing, False otherwise
"""
frequency = get_billing_frequency(contact_code)
return frequency in ['monthly', 'quarterly'] if frequency else False
```

def can_split_invoices(contact_code: str) -> bool:
“””
Check if invoices for this contact code can be split.
Only contacts with regular billing can have invoices split.

```
Args:
    contact_code (str): Contact code to check
    
Returns:
    bool: True if invoices can be split, False otherwise
"""
return is_regular_billing_code(contact_code)
```

# ============================================================================

# EXAMPLE USAGE AND TESTING

# ============================================================================

if **name** == “**main**”:
# Example usage
original_account = “ANP001042/3B”
print(f”Original account: {original_account}”)

```
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

# NEW: Test billing schedule functions
print(f"\n=== Billing Schedule Information ===")
test_codes = ["/3B", "/1A", "/P", "/CR"]

for code in test_codes:
    schedule = get_billing_schedule(code)
    frequency = get_billing_frequency(code)
    period_days = get_billing_period_days(code)
    start_day = get_billing_start_day(code)
    can_split = can_split_invoices(code)
    
    print(f"\nContact Code: {code}")
    print(f"  Description: {get_contact_code_description(code)}")
    print(f"  Frequency: {frequency}")
    print(f"  Period Days: {period_days}")
    print(f"  Start Day: {start_day}")
    print(f"  Can Split Invoices: {can_split}")
    if schedule:
        print(f"  Schedule Description: {schedule.get('description', 'N/A')}")
```