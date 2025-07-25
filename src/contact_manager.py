"""
Xero Contact Manager - Main Script
==================================

This module handles the core logic for creating new property contacts in Xero
by duplicating existing contacts with modifications.
"""

import os
import json
import base64
import copy
import traceback
from typing import Dict, Optional, Any, List
from dotenv import load_dotenv
import requests
import time

# Import our business rules
from constants import (
    parse_account_number, 
    increment_account_sequence,
    format_contact_name,
    validate_account_number,
    validate_contact_code,
    CONTACT_CODES
)

# Load environment variables - look in parent directory if not found
load_dotenv()
if not os.getenv('XERO_CLIENT_ID'):
    # Try loading from parent directory
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(parent_dir, '.env')
    load_dotenv(env_path)

class XeroContactManager:
    """Main class for managing Xero contacts and property account creation."""
    
    def __init__(self):
        """Initialize the Xero Contact Manager with API credentials."""
        self.client_id = os.getenv('XERO_CLIENT_ID')
        self.client_secret = os.getenv('XERO_CLIENT_SECRET')
        
        if not all([self.client_id, self.client_secret]):
            raise ValueError("Missing Xero API credentials in environment variables")
        
        self.access_token = None
        self.tenant_id = None
        self.base_url = "https://api.xero.com/api.xro/2.0"
        
    def authenticate(self) -> bool:
        """
        Authenticate with Xero API using Client Credentials (for Custom Connection apps).
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            print("Authenticating with Xero using Client Credentials...")
            
            # Client credentials flow for custom connections
            token_data = {
                'grant_type': 'client_credentials',
                'scope': 'accounting.contacts accounting.transactions'  # Updated scope for both contacts and invoices
            }
            
            # Use basic auth for client credentials
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
                print("Authentication successful!")
                
                # Get tenant information
                return self._get_tenant_info()
            else:
                print(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            return False
    
    def _get_tenant_info(self) -> bool:
        """
        Get tenant ID from Xero connections.
        For custom connections, try multiple methods.
        
        Returns:
            bool: True if tenant info retrieved successfully
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Method 1: Try the connections endpoint
            response = requests.get(
                'https://api.xero.com/connections',
                headers=headers
            )
            
            if response.status_code == 200:
                connections = response.json()
                if connections:
                    self.tenant_id = connections[0]['tenantId']
                    print(f"Connected to tenant: {connections[0]['tenantName']}")
                    return True
            
            print(f"Connections endpoint response: {response.status_code} - {response.text}")
            
            # Method 2: Try getting organisations directly (fallback for custom connections)
            print("Trying alternative method to get tenant info...")
            
            # For custom connections, we might need to extract tenant from the JWT token
            # or try the organisations endpoint without tenant-id header first
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
                    # For custom connections, we might be able to proceed without explicit tenant_id
                    # Use the organisation ID as tenant ID
                    self.tenant_id = orgs[0].get('OrganisationID')
                    print(f"Using organisation ID as tenant: {orgs[0].get('Name', 'Unknown')}")
                    return True
            
            print(f"Organisations endpoint response: {org_response.status_code} - {org_response.text}")
            
            # Method 3: For custom connections, sometimes we can proceed without tenant_id
            print("Attempting to proceed without explicit tenant ID...")
            self.tenant_id = "custom_connection"  # Placeholder
            return True
            
        except Exception as e:
            print(f"Error getting tenant info: {str(e)}")
            return False
    
    def search_contact_by_account_number(self, account_number: str) -> Optional[Dict[str, Any]]:
        """
        Search for a contact by account number or property base (first 8 chars).
        If given 8 characters, finds the latest contact for that property.
        
        Args:
            account_number (str): Full account number or first 8 chars for property search
            
        Returns:
            dict: Contact data if found, None otherwise
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            if self.tenant_id and self.tenant_id != "custom_connection":
                headers['Xero-Tenant-Id'] = self.tenant_id
            
            # If exactly 8 characters, search for all contacts and filter
            if len(account_number) == 8:
                print(f"Searching for latest contact at property: {account_number}")
                
                # Get all contacts and filter by property base
                response = requests.get(
                    f'{self.base_url}/Contacts',
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    all_contacts = data.get('Contacts', [])
                    
                    # Filter contacts that start with the property base
                    matching_contacts = [
                        contact for contact in all_contacts 
                        if contact.get('AccountNumber', '').startswith(account_number)
                    ]
                    
                    if matching_contacts:
                        # Sort by account number descending to get latest
                        matching_contacts.sort(key=lambda x: x.get('AccountNumber', ''), reverse=True)
                        latest_contact = matching_contacts[0]
                        print(f"Found {len(matching_contacts)} contacts for property {account_number}")
                        print(f"Latest contact: {latest_contact.get('AccountNumber')} - {latest_contact.get('Name')}")
                        return latest_contact
                    else:
                        print(f"No contacts found for property base: {account_number}")
                        return None
                else:
                    print(f"Error getting contacts: {response.status_code} - {response.text}")
                    return None
            
            else:
                # Original exact search logic
                if not validate_account_number(account_number):
                    print(f"Invalid account number format: {account_number}")
                    return None
                
                print(f"Searching for exact contact: {account_number}")
                
                params = {
                    'where': f'AccountNumber=="{account_number}"'
                }
                
                response = requests.get(
                    f'{self.base_url}/Contacts',
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    contacts = data.get('Contacts', [])
                    
                    if contacts:
                        print(f"Found contact: {contacts[0].get('Name', 'Unknown')}")
                        return contacts[0]
                    else:
                        print(f"No contact found with account number: {account_number}")
                        return None
                else:
                    print(f"Error searching for contact: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"Error searching for contact: {str(e)}")
            return None
    
    def search_contact_group_by_prefix(self, prefix: str) -> Optional[Dict[str, Any]]:
        """
        Search for a contact group that starts with the given prefix.
        
        Args:
            prefix (str): First 6 characters of contact name (e.g., "HDC006")
            
        Returns:
            dict: Contact group data if found, None otherwise
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            if self.tenant_id and self.tenant_id != "custom_connection":
                headers['Xero-Tenant-Id'] = self.tenant_id
            
            print(f"Searching for contact group starting with: {prefix}")
            
            # Get all contact groups
            response = requests.get(
                f'{self.base_url}/ContactGroups',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                contact_groups = data.get('ContactGroups', [])
                
                # Find group that starts with the prefix
                for group in contact_groups:
                    group_name = group.get('Name', '')
                    if group_name.startswith(prefix):
                        print(f"Found matching contact group: {group_name}")
                        return group
                
                print(f"No contact group found starting with: {prefix}")
                return None
            else:
                print(f"Error searching contact groups: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error searching for contact group: {str(e)}")
            return None

    def add_contact_to_group(self, contact_id: str, group_id: str) -> bool:
        """
        Add a contact to a contact group.
        
        Args:
            contact_id (str): ContactID of the contact to add
            group_id (str): ContactGroupID to add the contact to
            
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
            
            payload = {
                'Contacts': [
                    {
                        'ContactID': contact_id
                    }
                ]
            }
            
            print(f"Adding contact {contact_id} to group {group_id}")
            
            response = requests.put(
                f'{self.base_url}/ContactGroups/{group_id}/Contacts',
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                print("Successfully added contact to group")
                return True
            else:
                print(f"Error adding contact to group: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error adding contact to group: {str(e)}")
            return False
    
    def check_contact_exists(self, account_number: str) -> Optional[Dict[str, Any]]:
    """
    Check if a contact with the given account number already exists.
    
    Args:
        account_number (str): Full account number to check (e.g., "TST001002/1A")
        
    Returns:
        dict: Contact data if found, None if doesn't exist
    """
    try:
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.tenant_id and self.tenant_id != "custom_connection":
            headers['Xero-Tenant-Id'] = self.tenant_id
        
        print(f"Checking if contact exists: {account_number}")
        
        params = {
            'where': f'AccountNumber=="{account_number}"'
        }
        
        response = requests.get(
            f'{self.base_url}/Contacts',
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            contacts = data.get('Contacts', [])
            
            if contacts:
                print(f"✅ Contact exists: {contacts[0].get('Name', 'Unknown')}")
                return contacts[0]
            else:
                print(f"✅ Contact does not exist: {account_number}")
                return None
        else:
            print(f"❌ Error checking contact existence: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking contact existence: {str(e)}")
        return None

    def find_next_available_contact(self, base_account: str, contact_code: str, max_attempts: int = 50) -> Optional[str]:
    """
    Find the next available sequential contact number for a given base and contact code.
    
    Args:
        base_account (str): Base account without contact code (e.g., "TST001001")
        contact_code (str): Contact code to append (e.g., "/1A")
        max_attempts (int): Maximum number of sequences to check
        
    Returns:
        str: Next available account number if found, None if all checked slots are taken
    """
    try:
        # Parse the base account to get the property base and current sequence
        parsed = parse_account_number(base_account)
        if not parsed:
            print(f"❌ Cannot parse base account: {base_account}")
            return None
        
        property_base, current_sequence, _ = parsed
        
        # Start checking from the next sequence number
        next_sequence = int(current_sequence) + 1
        
        print(f"🔍 Looking for next available contact starting from sequence {next_sequence:03d}")
        
        for attempt in range(max_attempts):
            test_sequence = next_sequence + attempt
            test_account = f"{property_base}{test_sequence:03d}{contact_code}"
            
            print(f"   Checking: {test_account}")
            
            # Check if this account number exists
            existing_contact = self.check_contact_exists(test_account)
            
            if existing_contact is None:  # Contact doesn't exist - we found our slot!
                print(f"✅ Found available slot: {test_account}")
                return test_account
            else:
                print(f"   ❌ Taken: {test_account}")
                
        print(f"⚠️ No available contact found after checking {max_attempts} sequences")
        return None
        
    except Exception as e:
        print(f"❌ Error finding next available contact: {str(e)}")
        return None

    def validate_contact_before_creation(self, existing_contact: Dict[str, Any], contact_code: str) -> Dict[str, Any]:
    """
    Validate if the contact can be created and provide options if duplicate exists.
    
    Args:
        existing_contact (dict): Original contact data from Xero
        contact_code (str): Selected contact code (e.g., "/1A")
        
    Returns:
        dict: Validation result with status and options
    """
    try:
        # Get original account number and calculate next sequence
        original_account = existing_contact.get('AccountNumber', '')
        next_account_base = increment_account_sequence(original_account)
        
        if not next_account_base:
            return {
                'status': 'error',
                'message': f'Cannot increment account sequence from: {original_account}',
                'options': []
            }
        
        # Calculate the full account number with contact code
        proposed_account = f"{next_account_base.split('/')[0]}{contact_code}"
        
        print(f"🔍 Validating proposed account: {proposed_account}")
        
        # Check if the proposed account already exists
        existing_duplicate = self.check_contact_exists(proposed_account)
        
        if existing_duplicate is None:
            # No duplicate - all clear to create
            return {
                'status': 'available',
                'proposed_account': proposed_account,
                'message': f'Account {proposed_account} is available',
                'options': []
            }
        else:
            # Duplicate found - provide options
            duplicate_name = existing_duplicate.get('Name', 'Unknown Contact')
            
            # Find next available slot
            base_account_only = next_account_base.split('/')[0]  # Remove any existing contact code
            next_available = self.find_next_available_contact(base_account_only, contact_code)
            
            options = [
                {
                    'type': 'use_existing',
                    'account_number': proposed_account,
                    'contact_name': duplicate_name,
                    'contact_id': existing_duplicate.get('ContactID'),
                    'description': f'Use existing contact: {duplicate_name}'
                }
            ]
            
            if next_available:
                options.append({
                    'type': 'create_next',
                    'account_number': next_available,
                    'description': f'Create new contact: {next_available}'
                })
            else:
                options.append({
                    'type': 'no_available',
                    'description': 'No available sequential numbers found'
                })
            
            return {
                'status': 'duplicate_found',
                'proposed_account': proposed_account,
                'duplicate_contact': existing_duplicate,
                'message': f'Contact {proposed_account} already exists: {duplicate_name}',
                'options': options
            }
            
    except Exception as e:
        print(f"❌ Error in contact validation: {str(e)}")
        return {
            'status': 'error',
            'message': f'Validation error: {str(e)}',
            'options': []
        }

    def create_new_contact(self, existing_contact: Dict[str, Any], new_contact_data: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Create a new contact based on an existing contact with modifications.
        
        Args:
            existing_contact (dict): Original contact data from Xero
            new_contact_data (dict): New contact information with keys:
                - contact_code: New contact code (e.g., "/3B")
                - first_name: New contact's first name (required)
                - last_name: New contact's last name (optional)
                - email: New contact's email (optional)
                
        Returns:
            dict: Created contact data if successful, None otherwise
        """
        try:
            # Validate new contact data
            if not new_contact_data.get('first_name'):
                print("First name is required")
                return None
                
            contact_code = new_contact_data.get('contact_code', '')
            if not validate_contact_code(contact_code):
                print(f"Invalid contact code: {contact_code}")
                return None
            
            # Get original account number and increment sequence
            original_account = existing_contact.get('AccountNumber', '')
            new_account_number = increment_account_sequence(original_account)
            
            if not new_account_number:
                print(f"Failed to increment account number: {original_account}")
                return None
            
            # Add the contact code to the account number
            new_account_number_with_code = f"{new_account_number.split('/')[0]}{contact_code}"
            
            # Extract address components for contact name formatting
            original_name = existing_contact.get('Name', '')
            
            # Parse the original name to extract flat number and building address
            # Format: "ACCOUNT - (Flat X) Building Address" or "ACCOUNT - Building Address"
            name_parts = original_name.split(' - ', 1)
            if len(name_parts) == 2:
                address_part = name_parts[1]
                
                # Check if there's a flat number in parentheses
                if address_part.startswith('(') and ')' in address_part:
                    flat_end = address_part.index(')') + 1
                    flat_number = address_part[1:flat_end-1]  # Extract text between parentheses
                    building_address = address_part[flat_end:].strip()
                else:
                    flat_number = None
                    building_address = address_part
            else:
                # Fallback if name format is unexpected
                flat_number = None
                building_address = "Address Unknown"
            
            # Create new contact name
            new_contact_name = format_contact_name(
                new_account_number_with_code.split('/')[0], 
                flat_number, 
                building_address
            )
            
            # Build new contact data - only include fields with actual values
            new_contact = {
                'Name': new_contact_name,
                'AccountNumber': new_account_number_with_code,
                'ContactStatus': 'ACTIVE'
            }
            
            # Set primary contact details only if they have values
            first_name = new_contact_data['first_name']
            last_name = new_contact_data.get('last_name', '').strip()
            email = new_contact_data.get('email', '').strip()
            
            # Only include fields if they have actual values (not None or empty)
            if first_name:
                new_contact['FirstName'] = first_name
            
            # For LastName and EmailAddress, explicitly set empty string if user left them blank
            # This prevents Xero from auto-filling with default values
            if last_name:
                new_contact['LastName'] = last_name
            else:
                new_contact['LastName'] = ""  # Explicitly empty to prevent auto-fill
                
            if email:
                new_contact['EmailAddress'] = email
            else:
                new_contact['EmailAddress'] = ""  # Explicitly empty to prevent auto-fill
            
            # Copy relevant fields from existing contact, but only if they exist and have values
            fields_to_copy = [
                'Addresses', 'Phones', 'ContactGroups', 'DefaultCurrency',
                'SalesDefaultAccountCode', 'PurchasesDefaultAccountCode',
                'PaymentTerms', 'BrandingTheme'
            ]
            
            for field in fields_to_copy:
                if field in existing_contact and existing_contact[field]:
                    # Make a copy to avoid reference issues
                    try:
                        new_contact[field] = copy.deepcopy(existing_contact[field])
                    except:
                        new_contact[field] = existing_contact[field]
            
            # Only add ContactPersons if we have an email AND it's different from primary contact
            # This follows Xero's requirement that ContactPersons need email addresses
            if (email and 
                (first_name != existing_contact.get('FirstName') or 
                 last_name != existing_contact.get('LastName') or 
                 email != existing_contact.get('EmailAddress'))):
                contact_person = {
                    'FirstName': first_name,
                    'EmailAddress': email,
                    'IncludeInEmails': True
                }
                if last_name:
                    contact_person['LastName'] = last_name
                new_contact['ContactPersons'] = [contact_person]
            
            print(f"Creating contact with data structure:")
            print(f"  Name: {new_contact.get('Name')}")
            print(f"  AccountNumber: {new_contact.get('AccountNumber')}")
            if 'FirstName' in new_contact:
                print(f"  FirstName: {new_contact.get('FirstName')}")
            if 'LastName' in new_contact:
                value = new_contact.get('LastName')
                print(f"  LastName: '{value}' {'(explicitly empty)' if value == '' else ''}")
            if 'EmailAddress' in new_contact:
                value = new_contact.get('EmailAddress')
                print(f"  EmailAddress: '{value}' {'(explicitly empty)' if value == '' else ''}")
            if 'ContactPersons' in new_contact:
                print(f"  ContactPersons: {new_contact.get('ContactPersons')}")
            
            # Create the contact in Xero
            created_contact = self._create_contact_in_xero(new_contact)

            if created_contact and created_contact.get('ContactID'):
                # Try to add to contact group
                contact_name = created_contact.get('Name', '')
                if len(contact_name) >= 6:
                    prefix = contact_name[:6]  # First 6 characters
                    contact_group = self.search_contact_group_by_prefix(prefix)
                    
                    if contact_group:
                        group_id = contact_group.get('ContactGroupID')
                        group_name = contact_group.get('Name')
                        success = self.add_contact_to_group(created_contact['ContactID'], group_id)
                        
                        if success:
                            print(f"✅ Added contact to group: {group_name}")
                            created_contact['group_assignment'] = f"Added to group: {group_name}"
                        else:
                            print(f"❌ Failed to add contact to group: {group_name}")
                            created_contact['group_assignment'] = f"Failed to add to group: {group_name}"
                    else:
                        print(f"ℹ️ No contact group found for prefix: {prefix}")
                        created_contact['group_assignment'] = f"No contact group found for: {prefix}"
                
                return created_contact
            else:
                return None
            
        except Exception as e:
            print(f"Error creating new contact: {str(e)}")
            return None
    
    def _create_contact_in_xero(self, contact_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send new contact data to Xero API.
        
        Args:
            contact_data (dict): Contact data to create
            
        Returns:
            dict: Created contact data if successful, None otherwise
        """
        try:
            print("=== STARTING CONTACT CREATION ===")
            print(f"Access token exists: {'Yes' if self.access_token else 'No'}")
            print(f"Tenant ID: {self.tenant_id}")
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'  # Request JSON response
            }
            
            # Add tenant ID header only if we have a proper one
            if self.tenant_id and self.tenant_id != "custom_connection":
                headers['Xero-Tenant-Id'] = self.tenant_id
            
            payload = {
                'Contacts': [contact_data]
            }
            
            print(f"Headers: {headers}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            print("Making POST request to Xero...")
            response = requests.post(
                f'{self.base_url}/Contacts',
                headers=headers,
                json=payload
            )
            
            print(f"=== RESPONSE RECEIVED ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Content Length: {len(response.text)}")
            print(f"Response Content Type: {response.headers.get('Content-Type', 'Unknown')}")
            
            if response.text:
                print(f"First 1000 chars of response: {response.text[:1000]}")
            else:
                print("Response text is empty!")
            
            if response.status_code == 200:
                try:
                    # Check if response has content before parsing
                    if response.text.strip():
                        print("Attempting to parse JSON response...")
                        result = response.json()
                        print("JSON parsed successfully!")
                        
                        created_contacts = result.get('Contacts', [])
                        print(f"Number of contacts in response: {len(created_contacts)}")
                        
                        if created_contacts:
                            created_contact = created_contacts[0]
                            print(f"Successfully created contact: {created_contact.get('Name')}")
                            print(f"Account Number: {created_contact.get('AccountNumber')}")
                            return created_contact
                        else:
                            print("No contacts returned in response")
                            return None
                    else:
                        print("Empty response received - this might be normal for some Xero operations")
                        # For empty but successful responses, we might need to search for the created contact
                        return {"success": True, "message": "Contact created but no data returned"}
                except Exception as e:
                    print(f"Error parsing create response JSON: {e}")
                    print(f"Response content type: {response.headers.get('Content-Type')}")
                    print(f"Raw response: {response.text}")
                    return None
            else:
                print(f"Error creating contact: {response.status_code} - {response.text}")
                return None
            
        except Exception as e:
            print(f"Exception in _create_contact_in_xero: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
            return None
    
    def get_available_contact_codes(self) -> Dict[str, str]:
        """
        Get all available contact codes and their descriptions.
        
        Returns:
            dict: Contact codes and descriptions
        """
        return CONTACT_CODES.copy()


# Standalone functions for use by GUI or other modules
def create_new_property_contact(original_account_number: str, contact_code: str, 
                              first_name: str, last_name: str = "", email: str = "") -> bool:
    """
    Main function to create a new property contact.
    
    Args:
        original_account_number (str): Existing account number to duplicate
        contact_code (str): Contact code for new account (e.g., "/3B")
        first_name (str): New contact's first name
        last_name (str): New contact's last name (optional)
        email (str): New contact's email (optional)
        
    Returns:
        bool: True if contact created successfully, False otherwise
    """
    try:
        # Initialize contact manager
        manager = XeroContactManager()
        
        # Authenticate
        if not manager.authenticate():
            print("Failed to authenticate with Xero")
            return False
        
        # Search for existing contact
        existing_contact = manager.search_contact_by_account_number(original_account_number)
        if not existing_contact:
            print(f"Could not find contact with account number: {original_account_number}")
            return False
        
        # Prepare new contact data
        new_contact_data = {
            'contact_code': contact_code,
            'first_name': first_name,
            'last_name': last_name,
            'email': email
        }
        
        # Create new contact
        new_contact = manager.create_new_contact(existing_contact, new_contact_data)
        
        if new_contact:
            print(f"\n✅ Successfully created new contact!")
            print(f"Contact Name: {new_contact.get('Name')}")
            print(f"Account Number: {new_contact.get('AccountNumber')}")
            return True
        else:
            print("❌ Failed to create new contact")
            return False
            
    except Exception as e:
        print(f"Error in create_new_property_contact: {str(e)}")
        return False


# Example usage and testing
if __name__ == "__main__":
    print("Xero Contact Manager - Test Mode")
    print("-" * 40)
    
    # Example: Create new contact
    # create_new_property_contact(
    #     original_account_number="ANP001042/3B",
    #     contact_code="/3C", 
    #     first_name="John",
    #     last_name="Smith",
    #     email="john.smith@email.com"
    # )
