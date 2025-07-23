"""
Xero Invoice Manager - Module 2
===============================

This module handles invoice reassignment functionality for the property management system.
It searches for invoices assigned to old contacts after a move-in date and allows
reassignment to new contacts.

UPDATED: Now includes repeating invoice template reassignment functionality.
"""

import os
import json
import base64
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime, date
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()
if not os.getenv('XERO_CLIENT_ID'):
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(parent_dir, '.env')
    load_dotenv(env_path)


class XeroInvoiceManager:
    """Main class for managing Xero invoice reassignment operations."""
    
    def __init__(self, access_token: str = None, tenant_id: str = None):
        """
        Initialize the Xero Invoice Manager.
        
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
            print("Authenticating with Xero for invoice operations...")
            
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
                print("Invoice manager authentication successful!")
                return self._get_tenant_info()
            else:
                print(f"Invoice manager authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Invoice manager authentication failed: {str(e)}")
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
                    print(f"Connected to tenant for invoices: {connections[0]['tenantName']}")
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
            print(f"Error getting tenant info for invoices: {str(e)}")
            return False
    
    def search_invoices_by_contact_and_date(self, contact_id: str, move_in_date: date) -> List[Dict[str, Any]]:
        """
        Search for invoices assigned to a contact issued after a specific date.
        
        Args:
            contact_id (str): ContactID to search for
            move_in_date (date): Date when new occupier moved in
            
        Returns:
            list: List of invoice dictionaries
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            if self.tenant_id and self.tenant_id != "custom_connection":
                headers['Xero-Tenant-Id'] = self.tenant_id
            
            # Format date for Xero API (YYYY-MM-DD)
            date_str = move_in_date.strftime('%Y-%m-%d')
            print(f"Searching for invoices to contact {contact_id} issued after {date_str}")
            
            # Build query parameters - NO STATUS FILTERING, NO WHERE CLAUSE
            # Just get ALL invoices for this contact
            params = {
                'ContactIDs': contact_id,
                'order': 'Date DESC'
            }
            
            print(f"API Query: {params}")
            
            response = requests.get(
                f'{self.base_url}/Invoices',
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                all_invoices = data.get('Invoices', [])
                
                print(f"Total invoices returned from API: {len(all_invoices)}")
                
                # Manual date filtering after getting all invoices
                filtered_invoices = []
                
                for invoice in all_invoices:
                    invoice_date_str = invoice.get('DateString', '')
                    if invoice_date_str:
                        try:
                            # Parse the invoice date
                            invoice_date = datetime.fromisoformat(invoice_date_str.replace('T00:00:00', '')).date()
                            
                            # Check if invoice is after move-in date
                            if invoice_date >= move_in_date:
                                filtered_invoices.append(invoice)
                                print(f"✅ INCLUDED: {invoice.get('InvoiceNumber', 'N/A')} "
                                      f"Date: {invoice_date} "
                                      f"Status: {invoice.get('Status', 'N/A')} "
                                      f"Amount: ${invoice.get('Total', 0)}")
                            else:
                                print(f"❌ EXCLUDED (too old): {invoice.get('InvoiceNumber', 'N/A')} "
                                      f"Date: {invoice_date} "
                                      f"Status: {invoice.get('Status', 'N/A')}")
                        except Exception as e:
                            print(f"⚠️ Error parsing date for invoice {invoice.get('InvoiceNumber', 'N/A')}: {e}")
                    else:
                        print(f"⚠️ No date found for invoice {invoice.get('InvoiceNumber', 'N/A')}")
                
                # Log all unique statuses found
                all_statuses = set(invoice.get('Status', 'UNKNOWN') for invoice in all_invoices)
                print(f"All status codes found: {sorted(all_statuses)}")
                
                print(f"Final result: {len(filtered_invoices)} invoices after {move_in_date}")
                
                return filtered_invoices
            else:
                print(f"Error searching invoices: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Error searching for invoices: {str(e)}")
            return []
    
    def get_invoice_details(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific invoice.
        
        Args:
            invoice_id (str): InvoiceID to retrieve
            
        Returns:
            dict: Invoice details if found, None otherwise
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
                print(f"Error getting invoice details: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting invoice details: {str(e)}")
            return None
    
    def reassign_invoice_to_contact(self, invoice_id: str, new_contact_id: str) -> bool:
        """
        Reassign an invoice to a different contact.
        
        Args:
            invoice_id (str): InvoiceID to update
            new_contact_id (str): ContactID of new contact
            
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
            
            # Prepare the update payload
            payload = {
                'InvoiceID': invoice_id,
                'Contact': {
                    'ContactID': new_contact_id
                }
            }
            
            print(f"Reassigning invoice {invoice_id} to contact {new_contact_id}")
            
            response = requests.post(
                f'{self.base_url}/Invoices/{invoice_id}',
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully reassigned invoice {invoice_id}")
                return True
            else:
                print(f"❌ Error reassigning invoice: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error reassigning invoice: {str(e)}")
            return False
    
    def reassign_multiple_invoices(self, invoice_ids: List[str], new_contact_id: str) -> Tuple[List[str], List[str]]:
        """
        Reassign multiple invoices to a new contact.
        
        Args:
            invoice_ids (list): List of InvoiceIDs to reassign
            new_contact_id (str): ContactID of new contact
            
        Returns:
            tuple: (successful_ids, failed_ids)
        """
        successful = []
        failed = []
        
        print(f"\n🔄 Starting reassignment of {len(invoice_ids)} invoices...")
        
        for i, invoice_id in enumerate(invoice_ids, 1):
            print(f"Processing invoice {i}/{len(invoice_ids)}: {invoice_id}")
            
            if self.reassign_invoice_to_contact(invoice_id, new_contact_id):
                successful.append(invoice_id)
            else:
                failed.append(invoice_id)
        
        print(f"\n📊 Reassignment Summary:")
        print(f"✅ Successful: {len(successful)}")
        print(f"❌ Failed: {len(failed)}")
        
        return successful, failed
    
    def format_invoice_for_display(self, invoice: Dict[str, Any]) -> Dict[str, str]:
        """
        Format invoice data for display in UI.
        
        Args:
            invoice (dict): Raw invoice data from Xero API
            
        Returns:
            dict: Formatted invoice data for display
        """
        try:
            # Parse date string if available
            date_str = invoice.get('DateString', '')
            if date_str:
                try:
                    date_obj = datetime.fromisoformat(date_str.replace('T00:00:00', ''))
                    formatted_date = date_obj.strftime('%d %b %Y')
                except:
                    formatted_date = date_str
            else:
                formatted_date = 'N/A'
            
            # Parse due date
            due_date_str = invoice.get('DueDateString', '')
            if due_date_str:
                try:
                    due_date_obj = datetime.fromisoformat(due_date_str.replace('T00:00:00', ''))
                    formatted_due_date = due_date_obj.strftime('%d %b %Y')
                except:
                    formatted_due_date = due_date_str
            else:
                formatted_due_date = 'N/A'
            
            return {
                'invoice_id': invoice.get('InvoiceID', ''),
                'invoice_number': invoice.get('InvoiceNumber', 'N/A'),
                'date': formatted_date,
                'due_date': formatted_due_date,
                'status': invoice.get('Status', 'N/A'),
                'total': f"${float(invoice.get('Total', 0)):.2f}" if invoice.get('Total') else '$0.00',
                'amount_due': f"${float(invoice.get('AmountDue', 0)):.2f}" if invoice.get('AmountDue') else '$0.00',
                'reference': invoice.get('Reference', ''),
                'type': invoice.get('Type', 'N/A')
            }
            
        except Exception as e:
            print(f"Error formatting invoice for display: {str(e)}")
            return {
                'invoice_id': invoice.get('InvoiceID', ''),
                'invoice_number': 'Error formatting',
                'date': 'N/A',
                'due_date': 'N/A',
                'status': 'N/A',
                'total': '$0.00',
                'amount_due': '$0.00',
                'reference': '',
                'type': 'N/A'
            }
    
    def search_repeating_invoices_by_contact(self, contact_id: str) -> List[Dict[str, Any]]:
        """
        Search for repeating invoice templates assigned to a contact.
        
        Args:
            contact_id (str): ContactID to search for
            
        Returns:
            list: List of repeating invoice templates
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            if self.tenant_id and self.tenant_id != "custom_connection":
                headers['Xero-Tenant-Id'] = self.tenant_id
            
            print(f"Searching for repeating invoices for contact {contact_id}")
            
            # Get all repeating invoices and filter by contact
            response = requests.get(
                f'{self.base_url}/RepeatingInvoices',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                all_templates = data.get('RepeatingInvoices', [])
                
                # Filter by contact ID and exclude already deleted ones
                contact_templates = [
                    template for template in all_templates 
                    if (template.get('Contact', {}).get('ContactID') == contact_id and 
                        template.get('Status', '').upper() != 'DELETED')
                ]
                
                print(f"Found {len(contact_templates)} repeating invoice templates for contact")
                
                for template in contact_templates:
                    print(f"- Template {template.get('RepeatingInvoiceID', 'N/A')} "
                          f"Status: {template.get('Status', 'N/A')} "
                          f"Type: {template.get('Type', 'N/A')} "
                          f"Reference: {template.get('Reference', 'N/A')}")
                
                return contact_templates
            else:
                print(f"Error searching repeating invoices: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Error searching for repeating invoices: {str(e)}")
            return []
    
    def delete_repeating_invoice_template(self, template_id: str) -> bool:
        """
        Delete a repeating invoice template by setting status to DELETED.
        
        Args:
            template_id (str): RepeatingInvoiceID to delete
            
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
            
            # Prepare the delete payload
            payload = {
                'RepeatingInvoiceID': template_id,
                'Status': 'DELETED'
            }
            
            print(f"Deleting repeating invoice template {template_id}")
            
            response = requests.post(
                f'{self.base_url}/RepeatingInvoices/{template_id}',
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully deleted repeating invoice template {template_id}")
                return True
            else:
                print(f"❌ Error deleting repeating invoice template: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting repeating invoice template: {str(e)}")
            return False
    
    def create_repeating_invoice_template(self, template_data: Dict[str, Any], new_contact_id: str) -> Optional[Dict[str, Any]]:
        """
        Create a new repeating invoice template based on existing template data.
        
        Args:
            template_data (dict): Original template data from Xero API
            new_contact_id (str): ContactID of new contact
            
        Returns:
            dict: Created template data if successful, None otherwise
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            if self.tenant_id and self.tenant_id != "custom_connection":
                headers['Xero-Tenant-Id'] = self.tenant_id
            
            # Build new template payload copying all relevant fields
            new_template = {
                'Type': template_data.get('Type', 'ACCREC'),
                'Contact': {
                    'ContactID': new_contact_id
                },
                'Status': template_data.get('Status', 'DRAFT'),
                'LineAmountTypes': template_data.get('LineAmountTypes', 'Exclusive')
            }
            
            # Copy schedule information but use NextScheduledDate and set StartDate to same value
            if template_data.get('Schedule'):
                schedule = template_data['Schedule'].copy()
                
                # Get the NextScheduledDate from original template
                next_scheduled_date = schedule.get('NextScheduledDate')
                
                if next_scheduled_date:
                    # Set StartDate to the same value as NextScheduledDate to prevent Xero from using today's date
                    schedule['StartDate'] = next_scheduled_date
                    print(f"✅ Copying NextScheduledDate: {next_scheduled_date}")
                    print(f"✅ Setting StartDate to same value to prevent default to today")
                else:
                    # Fallback - remove StartDate if no NextScheduledDate found
                    schedule.pop('StartDate', None)
                    print(f"⚠️ No NextScheduledDate found in original template")
                
                # Remove any read-only fields that shouldn't be copied
                schedule.pop('NextScheduledDateString', None)
                
                new_template['Schedule'] = schedule
                
                print(f"📅 Schedule copied - next invoice will be generated on: {next_scheduled_date}")
            
            # Copy line items
            if template_data.get('LineItems'):
                line_items = []
                for item in template_data['LineItems']:
                    new_item = {
                        'Description': item.get('Description', ''),
                        'Quantity': item.get('Quantity', 1),
                        'UnitAmount': item.get('UnitAmount', 0),
                        'AccountCode': item.get('AccountCode', ''),
                        'TaxType': item.get('TaxType', '')
                    }
                    
                    # Include optional fields if they exist
                    for field in ['ItemCode', 'LineAmount', 'TaxAmount', 'DiscountRate', 'Tracking']:
                        if item.get(field):
                            new_item[field] = item[field]
                    
                    line_items.append(new_item)
                
                new_template['LineItems'] = line_items
            
            # Copy optional fields if they exist - but handle ApprovedForSending and Status specially
            optional_fields = [
                'Reference', 'BrandingThemeID', 'CurrencyCode',
                'SendCopy', 'MarkAsSent', 'IncludePDF'
            ]

            for field in optional_fields:
                if template_data.get(field):
                    new_template[field] = template_data[field]

            # Handle ApprovedForSending and Status based on whether new contact has email
            try:
                # Get new contact details to check for email address
                contact_response = requests.get(
                    f'{self.base_url}/Contacts/{new_contact_id}',
                    headers=headers
                )
                
                if contact_response.status_code == 200:
                    contact_data = contact_response.json()
                    contacts = contact_data.get('Contacts', [])
                    
                    if contacts:
                        contact = contacts[0]
                        email_address = contact.get('EmailAddress', '').strip()
                        
                        if email_address:
                            # Contact has email - set ApprovedForSending to true
                            new_template['ApprovedForSending'] = True
                            print(f"✅ Contact has email ({email_address}) - setting ApprovedForSending = True")
                        else:
                            # No email address - set Status to AUTHORISED
                            new_template['Status'] = 'AUTHORISED'
                            new_template['ApprovedForSending'] = False
                            print(f"⚠️ Contact has no email address - setting Status = AUTHORISED")
                    else:
                        # Fallback - set to AUTHORISED if we can't get contact details
                        new_template['Status'] = 'AUTHORISED'
                        new_template['ApprovedForSending'] = False
                        print(f"⚠️ Could not get contact details - setting Status = AUTHORISED")
                else:
                    # Fallback - set to AUTHORISED if API call fails
                    new_template['Status'] = 'AUTHORISED'
                    new_template['ApprovedForSending'] = False
                    print(f"⚠️ Failed to get contact details - setting Status = AUTHORISED")
                    
            except Exception as e:
                # Fallback - set to AUTHORISED if any error occurs
                new_template['Status'] = 'AUTHORISED'
                new_template['ApprovedForSending'] = False
                print(f"⚠️ Error checking contact email - setting Status = AUTHORISED: {str(e)}")
            
            print(f"Creating new repeating invoice template for contact {new_contact_id}")
            print(f"Template data: {json.dumps(new_template, indent=2)}")
            
            response = requests.post(
                f'{self.base_url}/RepeatingInvoices',
                headers=headers,
                json=new_template
            )
            
            if response.status_code == 200:
                result = response.json()
                created_templates = result.get('RepeatingInvoices', [])
                
                if created_templates:
                    created_template = created_templates[0]
                    print(f"✅ Successfully created repeating invoice template {created_template.get('RepeatingInvoiceID')}")
                    return created_template
                else:
                    print("❌ No template returned in response")
                    return None
            else:
                print(f"❌ Error creating repeating invoice template: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating repeating invoice template: {str(e)}")
            return None
    
    def reassign_repeating_invoice_template(self, old_contact_id: str, new_contact_id: str) -> Dict[str, Any]:
        """
        Reassign repeating invoice template from old contact to new contact.
        This involves: 1) Finding template, 2) Copying details, 3) Deleting old, 4) Creating new.
        
        Args:
            old_contact_id (str): ContactID of old contact
            new_contact_id (str): ContactID of new contact
            
        Returns:
            dict: Result with success status and details
        """
        result = {
            'success': False,
            'found_template': None,
            'deleted_successfully': False,
            'created_template': None,
            'error': None
        }
        
        try:
            print(f"\n🔄 Starting repeating invoice template reassignment...")
            print(f"From contact: {old_contact_id}")
            print(f"To contact: {new_contact_id}")
            
            # Step 1: Find existing template
            templates = self.search_repeating_invoices_by_contact(old_contact_id)
            
            if not templates:
                result['error'] = "No repeating invoice templates found for old contact"
                return result
            
            if len(templates) > 1:
                print(f"⚠️ Warning: Found {len(templates)} templates, processing the first one")
            
            template = templates[0]
            result['found_template'] = template
            
            template_id = template.get('RepeatingInvoiceID')
            print(f"📋 Found template: {template_id}")
            
            # Step 2: Create new template first (safer approach)
            print(f"🆕 Creating new template for new contact...")
            created_template = self.create_repeating_invoice_template(template, new_contact_id)
            
            if not created_template:
                result['error'] = "Failed to create new repeating invoice template"
                return result
            
            result['created_template'] = created_template
            
            # Step 3: Delete old template (only after successful creation)
            print(f"🗑️ Deleting old template...")
            deleted = self.delete_repeating_invoice_template(template_id)
            
            if deleted:
                result['deleted_successfully'] = True
                result['success'] = True
                print(f"✅ Successfully reassigned repeating invoice template!")
            else:
                result['error'] = "New template created but failed to delete old template - please delete manually in Xero"
                # Still mark as partial success since new template was created
                
            return result
            
        except Exception as e:
            result['error'] = f"Error during template reassignment: {str(e)}"
            print(f"❌ {result['error']}")
            return result
    
    def format_repeating_invoice_for_display(self, template: Dict[str, Any]) -> Dict[str, str]:
        """
        Format repeating invoice template data for display in UI.
        
        Args:
            template (dict): Raw template data from Xero API
            
        Returns:
            dict: Formatted template data for display
        """
        try:
            # Format schedule information
            schedule = template.get('Schedule', {})
            period = schedule.get('Period', 1)
            unit = schedule.get('Unit', 'MONTHLY').lower()
            
            frequency_text = f"Every {period} {unit}" if period > 1 else f"{unit.capitalize()}"
            
            # Format start date
            start_date_str = schedule.get('StartDate', '')
            if start_date_str:
                try:
                    # Parse Xero date format /Date(timestamp)/
                    if '/Date(' in start_date_str:
                        timestamp = int(start_date_str.split('(')[1].split('+')[0])
                        start_date = datetime.fromtimestamp(timestamp / 1000).strftime('%d %b %Y')
                    else:
                        start_date = start_date_str
                except:
                    start_date = start_date_str
            else:
                start_date = 'N/A'
            
            return {
                'template_id': template.get('RepeatingInvoiceID', ''),
                'reference': template.get('Reference', 'N/A'),
                'status': template.get('Status', 'N/A'),
                'type': template.get('Type', 'N/A'),
                'frequency': frequency_text,
                'start_date': start_date,
                'total': f"${float(template.get('Total', 0)):.2f}" if template.get('Total') else '$0.00',
                'line_items_count': len(template.get('LineItems', []))
            }
            
        except Exception as e:
            print(f"Error formatting repeating invoice for display: {str(e)}")
            return {
                'template_id': template.get('RepeatingInvoiceID', ''),
                'reference': 'Error formatting',
                'status': 'N/A',
                'type': 'N/A',
                'frequency': 'N/A',
                'start_date': 'N/A',
                'total': '$0.00',
                'line_items_count': 0
            }


# Standalone functions for integration with existing workflow
def search_invoices_for_reassignment(contact_id: str, move_in_date: date, 
                                   access_token: str = None, tenant_id: str = None) -> List[Dict[str, Any]]:
    """
    Standalone function to search for invoices that need reassignment.
    
    Args:
        contact_id (str): ContactID of old contact
        move_in_date (date): Date when new occupier moved in
        access_token (str, optional): Existing access token
        tenant_id (str, optional): Existing tenant ID
        
    Returns:
        list: List of invoices available for reassignment
    """
    try:
        manager = XeroInvoiceManager(access_token, tenant_id)
        return manager.search_invoices_by_contact_and_date(contact_id, move_in_date)
    except Exception as e:
        print(f"Error in search_invoices_for_reassignment: {str(e)}")
        return []


def reassign_selected_invoices(invoice_ids: List[str], new_contact_id: str,
                             access_token: str = None, tenant_id: str = None) -> Tuple[List[str], List[str]]:
    """
    Standalone function to reassign selected invoices to new contact.
    
    Args:
        invoice_ids (list): List of InvoiceIDs to reassign
        new_contact_id (str): ContactID of new contact
        access_token (str, optional): Existing access token
        tenant_id (str, optional): Existing tenant ID
        
    Returns:
        tuple: (successful_ids, failed_ids)
    """
    try:
        manager = XeroInvoiceManager(access_token, tenant_id)
        return manager.reassign_multiple_invoices(invoice_ids, new_contact_id)
    except Exception as e:
        print(f"Error in reassign_selected_invoices: {str(e)}")
        return [], invoice_ids


def search_repeating_invoices_for_contact(old_contact_id: str, 
                                        access_token: str = None, tenant_id: str = None) -> List[Dict[str, Any]]:
    """
    Standalone function to search for repeating invoice templates for a contact.
    
    Args:
        old_contact_id (str): ContactID of old contact
        access_token (str, optional): Existing access token
        tenant_id (str, optional): Existing tenant ID
        
    Returns:
        list: List of repeating invoice templates
    """
    try:
        manager = XeroInvoiceManager(access_token, tenant_id)
        return manager.search_repeating_invoices_by_contact(old_contact_id)
    except Exception as e:
        print(f"Error in search_repeating_invoices_for_contact: {str(e)}")
        return []


def reassign_repeating_invoice_template_for_contact(old_contact_id: str, new_contact_id: str,
                                                  access_token: str = None, tenant_id: str = None) -> Dict[str, Any]:
    """
    Standalone function to reassign repeating invoice template from old to new contact.
    
    Args:
        old_contact_id (str): ContactID of old contact
        new_contact_id (str): ContactID of new contact
        access_token (str, optional): Existing access token
        tenant_id (str, optional): Existing tenant ID
        
    Returns:
        dict: Result with success status and details
    """
    try:
        manager = XeroInvoiceManager(access_token, tenant_id)
        return manager.reassign_repeating_invoice_template(old_contact_id, new_contact_id)
    except Exception as e:
        print(f"Error in reassign_repeating_invoice_template_for_contact: {str(e)}")
        return {
            'success': False,
            'error': f"Error during template reassignment: {str(e)}"
        }


# Example usage and testing
if __name__ == "__main__":
    print("Xero Invoice Manager - Test Mode")
    print("-" * 40)
    
    # Example: Search for invoices
    # move_date = date(2024, 1, 1)
    # invoices = search_invoices_for_reassignment("contact-id-here", move_date)
    # print(f"Found {len(invoices)} invoices for potential reassignment")
    
    # Example: Search for repeating invoice templates  
    # templates = search_repeating_invoices_for_contact("contact-id-here")
    # print(f"Found {len(templates)} repeating invoice templates")