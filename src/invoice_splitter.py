# “””
Xero Invoice Splitter - Module 4

This module handles invoice splitting functionality for the property management system.
When occupiers change mid-billing period, invoices need to be split between:

- Previous occupier (invoice start → move-out date)
- New occupier (move-in date → invoice end)
- Void period (move-out → move-in) - written off as lost revenue

FUNCTIONALITY:

- Find most recent unpaid invoice for previous occupier
- Calculate billing periods based on contact codes
- Split invoices pro-rata by days
- Modify existing invoice for previous occupier
- Create new invoice for new occupier
- Round amounts up to nearest 10p (£0.10)
  “””

import os
import json
import base64
import math
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime, date, timedelta
from calendar import monthrange
from dotenv import load_dotenv
import requests

# Import our business rules

from constants import parse_account_number, CONTACT_CODES

# Load environment variables

load_dotenv()
if not os.getenv(‘XERO_CLIENT_ID’):
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(**file**)))
env_path = os.path.join(parent_dir, ‘.env’)
load_dotenv(env_path)

class XeroInvoiceSplitter:
“”“Main class for invoice splitting operations.”””

```
def __init__(self, access_token: str = None, tenant_id: str = None):
    """
    Initialize the Xero Invoice Splitter.
    
    Args:
        access_token (str, optional): Existing access token
        tenant_id (str, optional): Existing tenant ID
    """
    self.client_id = os.getenv('XERO_CLIENT_ID')
    self.client_secret = os.getenv('XERO_CLIENT_SECRET')
    
    if not all([self.client_id, self.client_secret]):
        raise ValueError("Missing Xero API credentials in environment variables")
    
    self.access_token = access_token
    self.tenant_id = tenant_id
    self.base_url = "https://api.xero.com/api.xro/2.0"
    
    # If no token provided, we'll need to authenticate
    if not self.access_token:
        self.authenticate()

def authenticate(self) -> bool:
    """
    Authenticate with Xero API using Client Credentials.
    
    Returns:
        bool: True if authentication successful, False otherwise
    """
    try:
        print("Authenticating with Xero for invoice splitting operations...")
        
        token_data = {
            'grant_type': 'client_credentials',
            'scope': 'accounting.contacts accounting.transactions'
        }
        
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.post(
            'https://identity.xero.com/connect/token',
            data=token_data,
            headers=headers
        )
        
        if response.status_code == 200:
            token_info = response.json()
            self.access_token = token_info['access_token']
            print("Invoice splitter authentication successful!")
            return self._get_tenant_info()
        else:
            print(f"Invoice splitter authentication failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Invoice splitter authentication failed: {str(e)}")
        return False

def _get_tenant_info(self) -> bool:
    """Get tenant ID from Xero connections."""
    try:
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.get(
            'https://api.xero.com/connections',
            headers=headers
        )
        
        if response.status_code == 200:
            connections = response.json()
            if connections:
                self.tenant_id = connections[0]['tenantId']
                print(f"Connected to tenant for invoice splitting: {connections[0]['tenantName']}")
                return True
        
        # Fallback method
        org_response = requests.get(
            f'{self.base_url}/Organisations',
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }
        )
        
        if org_response.status_code == 200:
            orgs = org_response.json().get('Organisations', [])
            if orgs:
                self.tenant_id = orgs[0].get('OrganisationID')
                print(f"Using organisation ID as tenant: {orgs[0].get('Name', 'Unknown')}")
                return True
        
        # Last resort for custom connections
        self.tenant_id = "custom_connection"
        return True
        
    except Exception as e:
        print(f"Error getting tenant info for invoice splitting: {str(e)}")
        return False

def get_contact_billing_info(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract billing frequency and schedule from contact information.
    
    Args:
        contact_data (dict): Contact data from Xero
        
    Returns:
        dict: Billing information including frequency and start dates
    """
    try:
        account_number = contact_data.get('AccountNumber', '')
        parsed = parse_account_number(account_number)
        
        if not parsed:
            return {
                'error': f'Cannot parse account number: {account_number}',
                'contact_code': None,
                'frequency': None,
                'schedule': None
            }
        
        base_code, sequence_digit, contact_code = parsed
        
        # Define billing schedules based on contact codes
        # TODO: Move this to constants.py once you add the complete mapping
        BILLING_SCHEDULES = {
            # Quarterly Billing
            "/1A": {"frequency": "quarterly", "start_month": 1, "start_day": 1},     # Jan 1, Apr 1, Jul 1, Oct 1
            "/2A": {"frequency": "quarterly", "start_month": 1, "start_day": 5},     # Jan 5, Apr 5, Jul 5, Oct 5
            "/1B": {"frequency": "quarterly", "start_month": 1, "start_day": 12},    # Jan 12, Apr 12, Jul 12, Oct 12
            "/3A": {"frequency": "quarterly", "start_month": 1, "start_day": 14},    # Jan 14, Apr 14, Jul 14, Oct 14
            
            # Monthly Billing
            "/3B": {"frequency": "monthly", "start_month": 1, "start_day": 1},       # 1st of each month
            "/3C": {"frequency": "monthly", "start_month": 1, "start_day": 16},      # 16th of each month
            "/3D": {"frequency": "monthly", "start_month": 1, "start_day": 23},      # 23rd of each month
            
            # Other codes (assume quarterly for now)
            "/1C": {"frequency": "quarterly", "start_month": 1, "start_day": 1},
            "/A": {"frequency": "quarterly", "start_month": 1, "start_day": 1},
            "/B": {"frequency": "quarterly", "start_month": 1, "start_day": 1},
            "/D": {"frequency": "quarterly", "start_month": 1, "start_day": 1},
        }
        
        schedule = BILLING_SCHEDULES.get(contact_code)
        
        if not schedule:
            return {
                'error': f'Unknown contact code: {contact_code}',
                'contact_code': contact_code,
                'frequency': None,
                'schedule': None
            }
        
        return {
            'error': None,
            'contact_code': contact_code,
            'frequency': schedule['frequency'],
            'schedule': schedule,
            'account_number': account_number
        }
        
    except Exception as e:
        return {
            'error': f'Error extracting billing info: {str(e)}',
            'contact_code': None,
            'frequency': None,
            'schedule': None
        }

def calculate_invoice_period(self, invoice_date: date, billing_info: Dict[str, Any]) -> Tuple[date, date]:
    """
    Calculate the start and end dates of an invoice period.
    
    Args:
        invoice_date (date): Date the invoice was issued
        billing_info (dict): Billing information from get_contact_billing_info
        
    Returns:
        tuple: (period_start_date, period_end_date)
    """
    try:
        frequency = billing_info['frequency']
        schedule = billing_info['schedule']
        
        if frequency == 'monthly':
            # Monthly billing - period is one month
            start_day = schedule['start_day']
            
            # Find the start of the period this invoice covers
            if invoice_date.day >= start_day:
                # Invoice is for current month
                period_start = invoice_date.replace(day=start_day)
            else:
                # Invoice is for previous month
                if invoice_date.month == 1:
                    period_start = invoice_date.replace(year=invoice_date.year - 1, month=12, day=start_day)
                else:
                    period_start = invoice_date.replace(month=invoice_date.month - 1, day=start_day)
            
            # Calculate end date (day before next period starts)
            if period_start.month == 12:
                next_period_start = period_start.replace(year=period_start.year + 1, month=1, day=start_day)
            else:
                next_period_start = period_start.replace(month=period_start.month + 1, day=start_day)
            
            period_end = next_period_start - timedelta(days=1)
            
        elif frequency == 'quarterly':
            # Quarterly billing - period is three months
            start_day = schedule['start_day']
            
            # Define quarterly start months
            quarterly_months = [1, 4, 7, 10]  # Jan, Apr, Jul, Oct
            
            # Find which quarter this invoice covers
            invoice_quarter_month = None
            for quarter_month in quarterly_months:
                quarter_start = date(invoice_date.year, quarter_month, start_day)
                if quarter_month <= 10:
                    next_quarter_start = date(invoice_date.year, quarter_month + 3, start_day)
                else:
                    next_quarter_start = date(invoice_date.year + 1, 1, start_day)
                
                if quarter_start <= invoice_date < next_quarter_start:
                    invoice_quarter_month = quarter_month
                    break
            
            # If not found in current year, check previous year
            if invoice_quarter_month is None:
                for quarter_month in quarterly_months:
                    quarter_start = date(invoice_date.year - 1, quarter_month, start_day)
                    if quarter_month <= 10:
                        next_quarter_start = date(invoice_date.year - 1, quarter_month + 3, start_day)
                    else:
                        next_quarter_start = date(invoice_date.year, 1, start_day)
                    
                    if quarter_start <= invoice_date < next_quarter_start:
                        invoice_quarter_month = quarter_month
                        period_start = quarter_start
                        period_end = next_quarter_start - timedelta(days=1)
                        break
            else:
                # Calculate period dates for current year
                period_start = date(invoice_date.year, invoice_quarter_month, start_day)
                if invoice_quarter_month <= 10:
                    next_quarter_start = date(invoice_date.year, invoice_quarter_month + 3, start_day)
                else:
                    next_quarter_start = date(invoice_date.year + 1, 1, start_day)
                
                period_end = next_quarter_start - timedelta(days=1)
        
        else:
            raise ValueError(f"Unknown frequency: {frequency}")
        
        return period_start, period_end
        
    except Exception as e:
        print(f"Error calculating invoice period: {str(e)}")
        # Fallback: assume invoice date is start, 90 days period
        return invoice_date, invoice_date + timedelta(days=89)

def get_latest_unpaid_invoice(self, contact_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the most recent unpaid invoice for a contact.
    
    Args:
        contact_id (str): ContactID to search for
        
    Returns:
        dict: Latest unpaid invoice data if found, None otherwise
    """
    try:
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.tenant_id and self.tenant_id != "custom_connection":
            headers['Xero-Tenant-Id'] = self.tenant_id
        
        print(f"Searching for latest unpaid invoice for contact: {contact_id}")
        
        # Get invoices for this contact, ordered by date descending
        params = {
            'ContactIDs': contact_id,
            'order': 'Date DESC',
            'Statuses': 'AUTHORISED,SUBMITTED'  # Only get unpaid invoices
        }
        
        response = requests.get(
            f'{self.base_url}/Invoices',
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            invoices = data.get('Invoices', [])
            
            # Find the first invoice with outstanding amount
            for invoice in invoices:
                amount_due = float(invoice.get('AmountDue', 0))
                if amount_due > 0:
                    print(f"✅ Found unpaid invoice: {invoice.get('InvoiceNumber', 'N/A')} - £{amount_due:.2f} due")
                    
                    # Get full invoice details including line items
                    invoice_id = invoice.get('InvoiceID')
                    detailed_invoice = self.get_invoice_details(invoice_id)
                    
                    return detailed_invoice if detailed_invoice else invoice
            
            print("ℹ️ No unpaid invoices found for contact")
            return None
        else:
            print(f"❌ Error searching for invoices: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting latest unpaid invoice: {str(e)}")
        return None

def get_invoice_details(self, invoice_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific invoice including line items.
    
    Args:
        invoice_id (str): InvoiceID to retrieve
        
    Returns:
        dict: Detailed invoice data if found, None otherwise
    """
    try:
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.tenant_id and self.tenant_id != "custom_connection":
            headers['Xero-Tenant-Id'] = self.tenant_id
        
        response = requests.get(
            f'{self.base_url}/Invoices/{invoice_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            invoices = data.get('Invoices', [])
            return invoices[0] if invoices else None
        else:
            print(f"❌ Error getting invoice details: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting invoice details: {str(e)}")
        return None

def calculate_split(self, invoice: Dict[str, Any], contact_data: Dict[str, Any], 
                   vacate_date: date, move_in_date: date) -> Dict[str, Any]:
    """
    Calculate how to split an invoice between previous and new occupiers.
    
    Args:
        invoice (dict): Invoice data from Xero
        contact_data (dict): Contact data for billing info
        vacate_date (date): When previous occupier moved out
        move_in_date (date): When new occupier moved in
        
    Returns:
        dict: Split calculation results
    """
    try:
        # Get billing information
        billing_info = self.get_contact_billing_info(contact_data)
        
        if billing_info.get('error'):
            return {
                'success': False,
                'error': billing_info['error']
            }
        
        # Parse invoice date
        invoice_date_str = invoice.get('DateString', '')
        if invoice_date_str:
            invoice_date = datetime.fromisoformat(invoice_date_str.replace('T00:00:00', '')).date()
        else:
            return {
                'success': False,
                'error': 'Cannot parse invoice date'
            }
        
        # Calculate invoice period
        period_start, period_end = self.calculate_invoice_period(invoice_date, billing_info)
        
        # Validate dates
        if vacate_date < period_start or vacate_date > period_end:
            return {
                'success': False,
                'error': f'Vacate date must be within invoice period ({period_start} to {period_end})'
            }
        
        if move_in_date < period_start or move_in_date > period_end:
            return {
                'success': False,
                'error': f'Move-in date must be within invoice period ({period_start} to {period_end})'
            }
        
        if move_in_date <= vacate_date:
            return {
                'success': False,
                'error': 'Move-in date must be after vacate date'
            }
        
        # Calculate days
        total_days = (period_end - period_start).days + 1
        previous_occupier_days = (vacate_date - period_start).days + 1
        void_days = (move_in_date - vacate_date).days - 1
        new_occupier_days = (period_end - move_in_date).days + 1
        
        # Get invoice amounts
        total_amount = float(invoice.get('Total', 0))
        amount_due = float(invoice.get('AmountDue', 0))
        
        # Calculate split amounts (daily pro-rata)
        daily_rate = total_amount / total_days
        
        previous_occupier_amount = daily_rate * previous_occupier_days
        new_occupier_amount = daily_rate * new_occupier_days
        void_amount = daily_rate * void_days
        
        # Round up to nearest 10p (£0.10)
        previous_occupier_amount = math.ceil(previous_occupier_amount * 10) / 10
        new_occupier_amount = math.ceil(new_occupier_amount * 10) / 10
        void_amount = math.ceil(void_amount * 10) / 10
        
        return {
            'success': True,
            'invoice_details': {
                'invoice_id': invoice.get('InvoiceID'),
                'invoice_number': invoice.get('InvoiceNumber'),
                'total_amount': total_amount,
                'amount_due': amount_due,
                'period_start': period_start,
                'period_end': period_end,
                'total_days': total_days
            },
            'split_calculation': {
                'daily_rate': daily_rate,
                'previous_occupier': {
                    'days': previous_occupier_days,
                    'amount': previous_occupier_amount,
                    'period': f"{period_start} to {vacate_date}"
                },
                'new_occupier': {
                    'days': new_occupier_days,
                    'amount': new_occupier_amount,
                    'period': f"{move_in_date} to {period_end}"
                },
                'void_period': {
                    'days': void_days,
                    'amount': void_amount,
                    'period': f"{vacate_date + timedelta(days=1)} to {move_in_date - timedelta(days=1)}" if void_days > 0 else "None"
                }
            },
            'billing_info': billing_info
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error calculating split: {str(e)}'
        }

def modify_existing_invoice(self, invoice: Dict[str, Any], new_amount: float, 
                           period_description: str) -> bool:
    """
    Modify existing invoice to reflect only the previous occupier's portion.
    
    Args:
        invoice (dict): Original invoice data
        new_amount (float): New total amount for previous occupier
        period_description (str): Description of the period covered
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.tenant_id and self.tenant_id != "custom_connection":
            headers['Xero-Tenant-Id'] = self.tenant_id
        
        invoice_id = invoice.get('InvoiceID')
        original_total = float(invoice.get('Total', 0))
        
        # Calculate scaling factor
        scale_factor = new_amount / original_total
        
        # Modify line items proportionally
        modified_line_items = []
        for line_item in invoice.get('LineItems', []):
            original_line_amount = float(line_item.get('LineAmount', 0))
            new_line_amount = original_line_amount * scale_factor
            
            # Round line amount to 2 decimal places
            new_line_amount = round(new_line_amount, 2)
            
            modified_line_item = {
                'LineItemID': line_item.get('LineItemID'),
                'Description': f"{line_item.get('Description', '')} ({period_description})",
                'Quantity': line_item.get('Quantity', 1),
                'UnitAmount': round(new_line_amount / float(line_item.get('Quantity', 1)), 2),
                'AccountCode': line_item.get('AccountCode', ''),
                'TaxType': line_item.get('TaxType', ''),
                'LineAmount': new_line_amount
            }
            
            # Include optional fields if they exist
            for field in ['ItemCode', 'TaxAmount', 'DiscountRate', 'Tracking']:
                if line_item.get(field):
                    modified_line_item[field] = line_item[field]
            
            modified_line_items.append(modified_line_item)
        
        # Prepare update payload
        payload = {
            'InvoiceID': invoice_id,
            'LineItems': modified_line_items
        }
        
        print(f"Modifying invoice {invoice.get('InvoiceNumber')} from £{original_total:.2f} to £{new_amount:.2f}")
        
        response = requests.post(
            f'{self.base_url}/Invoices/{invoice_id}',
            headers=headers,
            json=payload
        )
        
        if response.status_code in [200, 204]:
            print(f"✅ Successfully modified invoice {invoice.get('InvoiceNumber')}")
            return True
        else:
            print(f"❌ Error modifying invoice: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error modifying existing invoice: {str(e)}")
        return False

def create_new_invoice(self, original_invoice: Dict[str, Any], new_contact_id: str, 
                      new_amount: float, period_description: str) -> Optional[Dict[str, Any]]:
    """
    Create new invoice for new occupier based on original invoice structure.
    
    Args:
        original_invoice (dict): Original invoice data to base new invoice on
        new_contact_id (str): ContactID of new occupier
        new_amount (float): Total amount for new occupier
        period_description (str): Description of the period covered
        
    Returns:
        dict: Created invoice data if successful, None otherwise
    """
    try:
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.tenant_id and self.tenant_id != "custom_connection":
            headers['Xero-Tenant-Id'] = self.tenant_id
        
        original_total = float(original_invoice.get('Total', 0))
        scale_factor = new_amount / original_total
        
        # Create line items proportionally
        new_line_items = []
        for line_item in original_invoice.get('LineItems', []):
            original_line_amount = float(line_item.get('LineAmount', 0))
            new_line_amount = original_line_amount * scale_factor
            
            # Round line amount to 2 decimal places
            new_line_amount = round(new_line_amount, 2)
            
            new_line_item = {
                'Description': f"{line_item.get('Description', '')} ({period_description})",
                'Quantity': line_item.get('Quantity', 1),
                'UnitAmount': round(new_line_amount / float(line_item.get('Quantity', 1)), 2),
                'AccountCode': line_item.get('AccountCode', ''),
                'TaxType': line_item.get('TaxType', ''),
                'LineAmount': new_line_amount
            }
            
            # Include optional fields if they exist
            for field in ['ItemCode', 'TaxAmount', 'DiscountRate', 'Tracking']:
                if line_item.get(field):
                    new_line_item[field] = line_item[field]
            
            new_line_items.append(new_line_item)
        
        # Prepare new invoice payload
        new_invoice = {
            'Type': original_invoice.get('Type', 'ACCREC'),
            'Contact': {
                'ContactID': new_contact_id
            },
            'Date': original_invoice.get('DateString', datetime.now().strftime('%Y-%m-%d')),
            'DueDate': original_invoice.get('DueDateString'),
            'LineAmountTypes': original_invoice.get('LineAmountTypes', 'Exclusive'),
            'LineItems': new_line_items,
            'Status': 'AUTHORISED'
        }
        
        # Include optional fields if they exist in original
        optional_fields = ['Reference', 'BrandingThemeID', 'CurrencyCode']
        for field in optional_fields:
            if original_invoice.get(field):
                new_invoice[field] = original_invoice[field]
        
        payload = {
            'Invoices': [new_invoice]
        }
        
        print(f"Creating new invoice for new occupier: £{new_amount:.2f}")
        
        response = requests.post(
            f'{self.base_url}/Invoices',
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            created_invoices = result.get('Invoices', [])
            
            if created_invoices:
                created_invoice = created_invoices[0]
                print(f"✅ Successfully created new invoice: {created_invoice.get('InvoiceNumber')}")
                return created_invoice
            else:
                print("❌ No invoice returned in response")
                return None
        else:
            print(f"❌ Error creating new invoice: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating new invoice: {str(e)}")
        return None
```

# Standalone functions for integration with existing workflow

def get_latest_invoice_for_splitting(old_contact_id: str, access_token: str = None,
tenant_id: str = None) -> Optional[Dict[str, Any]]:
“””
Standalone function to get latest unpaid invoice for splitting.

```
Args:
    old_contact_id (str): ContactID of previous occupier
    access_token (str, optional): Existing access token
    tenant_id (str, optional): Existing tenant ID
    
Returns:
    dict: Latest unpaid invoice if found, None otherwise
"""
try:
    splitter = XeroInvoiceSplitter(access_token, tenant_id)
    return splitter.get_latest_unpaid_invoice(old_contact_id)
except Exception as e:
    print(f"Error in get_latest_invoice_for_splitting: {str(e)}")
    return None
```

def calculate_invoice_split(invoice: Dict[str, Any], contact_data: Dict[str, Any],
vacate_date: date, move_in_date: date,
access_token: str = None, tenant_id: str = None) -> Dict[str, Any]:
“””
Standalone function to calculate invoice split.

```
Args:
    invoice (dict): Invoice data
    contact_data (dict): Contact data for billing info
    vacate_date (date): When previous occupier moved out
    move_in_date (date): When new occupier moved in
    access_token (str, optional): Existing access token
    tenant_id (str, optional): Existing tenant ID
    
Returns:
    dict: Split calculation results
"""
try:
    splitter = XeroInvoiceSplitter(access_token, tenant_id)
    return splitter.calculate_split(invoice, contact_data, vacate_date, move_in_date)
except Exception as e:
    print(f"Error in calculate_invoice_split: {str(e)}")
    return {
        'success': False,
        'error': f'Error calculating split: {str(e)}'
    }
```

def execute_invoice_split(invoice: Dict[str, Any], new_contact_id: str,
split_calculation: Dict[str, Any],
access_token: str = None, tenant_id: str = None) -> Dict[str, Any]:
“””
Standalone function to execute the invoice split (modify + create).

```
Args:
    invoice (dict): Original invoice data
    new_contact_id (str): ContactID of new occupier
    split_calculation (dict): Results from calculate_invoice_split
    access_token (str, optional): Existing access token
    tenant_id (str, optional): Existing tenant ID
    
Returns:
    dict: Results of split execution
"""
try:
    splitter = XeroInvoiceSplitter(access_token, tenant_id)
    
    # Extract calculation data
    calc_data = split_calculation['split_calculation']
    previous_amount = calc_data['previous_occupier']['amount']
    new_amount = calc_data['new_occupier']['amount']
    previous_period = calc_data['previous_occupier']['period']
    new_period = calc_data['new_occupier']['period']
    
    # Modify existing invoice for previous occupier
    modify_success = splitter.modify_existing_invoice(
        invoice, 
        previous_amount, 
        f"Period: {previous_period}"
    )
    
    # Create new invoice for new occupier
    new_invoice = None
    if modify_success:
        new_invoice = splitter.create_new_invoice(
            invoice,
            new_contact_id,
            new_amount,
            f"Period: {new_period}"
        )
    
    return {
        'success': modify_success and (new_invoice is not None),
        'modified_invoice': modify_success,
        'created_invoice': new_invoice,
        'previous_amount': previous_amount,
        'new_amount': new_amount
    }
    
except Exception as e:
    print(f"Error in execute_invoice_split: {str(e)}")
    return {
        'success': False,
        'error': f'Error executing split: {str(e)}'
    }
```

# Example usage and testing

if **name** == “**main**”:
print(“Xero Invoice Splitter - Test Mode”)
print(”-” * 40)

```
# Example: Get latest invoice for splitting
# invoice = get_latest_invoice_for_splitting("contact-id-here")
# if invoice:
#     print(f"Found invoice: {invoice.get('InvoiceNumber')} - £{invoice.get('AmountDue')}")

# Example: Calculate split
# split_result = calculate_invoice_split(
#     invoice, contact_data, 
#     date(2025, 2, 14), date(2025, 2, 28)
# )
# if split_result['success']:
#     print(f"Previous occupier: £{split_result['split_calculation']['previous_occupier']['amount']}")
#     print(f"New occupier: £{split_result['split_calculation']['new_occupier']['amount']}")
```