"""
Xero Previous Contact Manager - Module 3
=========================================

This module handles the management of previous contacts after successful
contact creation and invoice reassignment. It determines whether to archive
contacts with zero balance or convert them to "/P" status for outstanding balances.

FUNCTIONALITY:
- Get contact balance from Xero API
- Handle zero balance contacts (set INACTIVE + /P)
- Handle outstanding balance contacts (keep ACTIVE + /P)
- Remove from current contact groups
- Add to "+ Previous accounts still due" group
"""

import os
import json
import base64
from typing import Dict, Optional, Any, List, Tuple
from dotenv import load_dotenv
import requests

# Import our business rules
from constants import parse_account_number, CONTACT_CODES

# Load environment variables
load_dotenv()
if not os.getenv('XERO_CLIENT_ID'):
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(parent_dir, '.env')
    load_dotenv(env_path)


class XeroPreviousContactManager:
    """Main class for managing previous contact status and group assignments."""
    
    def __init__(self, access_token: str = None, tenant_id: str = None):
        """
        Initialize the Xero Previous Contact Manager.
        
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
            print("Authenticating with Xero for previous contact operations...")
            
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
                print("Previous contact manager authentication successful!")
                return self._get_tenant_info()
            else:
                print(f"Previous contact manager authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Previous contact manager authentication failed: {str(e)}")
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
                    print(f"Connected to tenant for previous contacts: {connections[0]['tenantName']}")
                    return True
            
            print(f"Connections endpoint response: {response.status_code} - {response.text}")
            
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
            print(f"Error getting tenant info for previous contacts: {str(e)}")
            return False
    
    def get_contact_balance(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the outstanding balance for a contact from Xero.
        
        Args:
            contact_id (str): ContactID to check balance for
            
        Returns:
            dict: Balance information with 'outstanding' amount and raw contact data
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            if self.tenant_id and self.tenant_id != "custom_connection":
                headers['Xero-Tenant-Id'] = self.tenant_id
            
            print(f"Getting balance for contact: {contact_id}")
            
            response = requests.get(
                f'{self.base_url}/Contacts/{contact_id}',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                contacts = data.get('Contacts', [])
                
                if contacts:
                    contact = contacts[0]
                    balances = contact.get('Balances', {})
                    accounts_receivable = balances.get('AccountsReceivable', {})
                    outstanding = float(accounts_receivable.get('Outstanding', 0.0))
                    overdue = float(accounts_receivable.get('Overdue', 0.0))
                    
                    print(f"✅ Contact balance retrieved:")
                    print(f"   Outstanding: ${outstanding:.2f}")
                    print(f"   Overdue: ${overdue:.2f}")
                    
                    return {
                        'outstanding': outstanding,
                        'overdue': overdue,
                        'has_balance': outstanding != 0.0,
                        'contact_data': contact
                    }
                else:
                    print("❌ No contact data returned")
                    return None
            else:
                print(f"❌ Error getting contact balance: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting contact balance: {str(e)}")
            return None
    
    def get_contact_groups_for_contact(self, contact_id: str) -> List[Dict[str, Any]]:
        """
        Get all contact groups that a contact belongs to.
        
        Args:
            contact_id (str): ContactID to check groups for
            
        Returns:
            list: List of contact group dictionaries
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            if self.tenant_id and self.tenant_id != "custom_connection":
                headers['Xero-Tenant-Id'] = self.tenant_id
            
            # Get contact details which includes ContactGroups
            response = requests.get(
                f'{self.base_url}/Contacts/{contact_id}',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                contacts = data.get('Contacts', [])
                
                if contacts:
                    contact = contacts[0]
                    contact_groups = contact.get('ContactGroups', [])
                    
                    print(f"📋 Found {len(contact_groups)} groups for contact:")
                    for group in contact_groups:
                        print(f"   - {group.get('Name', 'Unknown')} (ID: {group.get('ContactGroupID', 'N/A')})")
                    
                    return contact_groups
                else:
                    print("❌ No contact data returned")
                    return []
            else:
                print(f"❌ Error getting contact groups: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting contact groups: {str(e)}")
            return []
    
    def remove_contact_from_group(self, contact_id: str, group_id: str) -> bool:
        """
        Remove a contact from a specific contact group.
        
        Args:
            contact_id (str): ContactID to remove
            group_id (str): ContactGroupID to remove from
            
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
            
            print(f"Removing contact {contact_id} from group {group_id}")
            
            response = requests.delete(
                f'{self.base_url}/ContactGroups/{group_id}/Contacts/{contact_id}',
                headers=headers
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully removed contact from group")
                return True
            else:
                print(f"❌ Error removing contact from group: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error removing contact from group: {str(e)}")
            return False
    
    def find_previous_accounts_group(self) -> Optional[Dict[str, Any]]:
        """
        Find the "+ Previous accounts still due" contact group.
        
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
            
            print("Searching for '+ Previous accounts still due' contact group...")
            
            response = requests.get(
                f'{self.base_url}/ContactGroups',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                contact_groups = data.get('ContactGroups', [])
                
                # Find the exact group name
                for group in contact_groups:
                    group_name = group.get('Name', '')
                    if group_name == "+ Previous accounts still due":
                        print(f"✅ Found '+ Previous accounts still due' group: {group.get('ContactGroupID')}")
                        return group
                
                print("❌ '+ Previous accounts still due' group not found")
                return None
            else:
                print(f"❌ Error searching contact groups: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error searching for previous accounts group: {str(e)}")
            return None
    
    def add_contact_to_group(self, contact_id: str, group_id: str) -> bool:
        """
        Add a contact to a contact group.
        
        Args:
            contact_id (str): ContactID to add
            group_id (str): ContactGroupID to add to
            
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
            
            print(f"Adding contact {contact_id} to '+ Previous accounts still due' group {group_id}")
            
            response = requests.put(
                f'{self.base_url}/ContactGroups/{group_id}/Contacts',
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                print("✅ Successfully added contact to '+ Previous accounts still due' group")
                return True
            else:
                print(f"❌ Error adding contact to group: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error adding contact to group: {str(e)}")
            return False
    
    def update_contact_to_previous_status(self, contact_id: str, contact_data: Dict[str, Any], has_balance: bool) -> bool:
        """
        Update contact to previous status with /P code and appropriate ContactStatus.
        
        Args:
            contact_id (str): ContactID to update
            contact_data (dict): Current contact data from Xero
            has_balance (bool): Whether contact has outstanding balance
            
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
            
            # Get current account number and parse it
            current_account = contact_data.get('AccountNumber', '')
            parsed = parse_account_number(current_account)
            
            if not parsed:
                print(f"❌ Cannot parse account number: {current_account}")
                return False
            
            base_code, sequence_digit, old_contact_code = parsed
            
            # Create new account number with /P code
            new_account_number = f"{base_code}{sequence_digit}/P"
            
            # Determine contact status based on balance
            if has_balance:
                new_status = "ACTIVE"  # Keep active if they owe money
                status_reason = "Outstanding balance - keeping ACTIVE"
            else:
                new_status = "INACTIVE"  # Set inactive if zero balance
                status_reason = "Zero balance - setting INACTIVE"
            
            print(f"🔄 Updating contact to previous status:")
            print(f"   Current Account: {current_account}")
            print(f"   New Account: {new_account_number}")
            print(f"   New Status: {new_status} ({status_reason})")
            
            # Prepare update payload
            payload = {
                'ContactID': contact_id,
                'AccountNumber': new_account_number,
                'ContactStatus': new_status
            }
            
            response = requests.post(
                f'{self.base_url}/Contacts/{contact_id}',
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully updated contact to /P status")
                return True
            else:
                print(f"❌ Error updating contact: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating contact to previous status: {str(e)}")
            return False
    
    def handle_previous_contact_workflow(self, old_contact_id: str) -> Dict[str, Any]:
        """
        Main workflow function to handle previous contact after successful reassignment.
        
        Args:
            old_contact_id (str): ContactID of the previous contact
            
        Returns:
            dict: Result with success status and details
        """
        result = {
            'success': False,
            'balance_info': None,
            'groups_removed': [],
            'added_to_previous_group': False,
            'contact_updated': False,
            'error': None
        }
        
        try:
            print(f"\n🔄 Starting previous contact workflow for: {old_contact_id}")
            
            # Step 1: Get contact balance
            print("📊 Step 1: Getting contact balance...")
            balance_info = self.get_contact_balance(old_contact_id)
            
            if not balance_info:
                result['error'] = "Failed to get contact balance"
                return result
            
            result['balance_info'] = balance_info
            outstanding = balance_info['outstanding']
            has_balance = balance_info['has_balance']
            contact_data = balance_info['contact_data']
            
            print(f"💰 Balance Status: ${outstanding:.2f} outstanding")
            print(f"📋 Action: {'Keep ACTIVE (has balance)' if has_balance else 'Set INACTIVE (zero balance)'}")
            
            # Step 2: Get current contact groups
            print("👥 Step 2: Getting current contact groups...")
            current_groups = self.get_contact_groups_for_contact(old_contact_id)
            
            # Step 3: Remove from current groups
            print(f"🗑️ Step 3: Removing from {len(current_groups)} current groups...")
            removed_groups = []
            
            for group in current_groups:
                group_id = group.get('ContactGroupID')
                group_name = group.get('Name', 'Unknown')
                
                if self.remove_contact_from_group(old_contact_id, group_id):
                    removed_groups.append(group_name)
                    print(f"   ✅ Removed from: {group_name}")
                else:
                    print(f"   ❌ Failed to remove from: {group_name}")
            
            result['groups_removed'] = removed_groups
            
            # Step 4: Find "+ Previous accounts still due" group
            print("🔍 Step 4: Finding '+ Previous accounts still due' group...")
            previous_group = self.find_previous_accounts_group()
            
            if not previous_group:
                result['error'] = "'+ Previous accounts still due' group not found"
                print("❌ Cannot continue without target group")
                return result
            
            # Step 5: Add to "+ Previous accounts still due" group
            print("➕ Step 5: Adding to '+ Previous accounts still due' group...")
            group_id = previous_group.get('ContactGroupID')
            
            if self.add_contact_to_group(old_contact_id, group_id):
                result['added_to_previous_group'] = True
                print("   ✅ Successfully added to '+ Previous accounts still due' group")
            else:
                print("   ❌ Failed to add to '+ Previous accounts still due' group")
            
            # Step 6: Update contact to /P status
            print("🏷️ Step 6: Updating contact to /P status...")
            if self.update_contact_to_previous_status(old_contact_id, contact_data, has_balance):
                result['contact_updated'] = True
                print("   ✅ Successfully updated contact to /P status")
            else:
                print("   ❌ Failed to update contact to /P status")
            
            # Determine overall success
            if (result['contact_updated'] and 
                result['added_to_previous_group'] and 
                len(result['groups_removed']) > 0):
                result['success'] = True
                print(f"\n🎉 Previous contact workflow completed successfully!")
                
                # Summary
                print(f"📋 Summary:")
                print(f"   💰 Outstanding Balance: ${outstanding:.2f}")
                print(f"   🏷️ Status: {'ACTIVE' if has_balance else 'INACTIVE'} + /P")
                print(f"   👥 Removed from {len(removed_groups)} groups: {', '.join(removed_groups)}")
                print(f"   ➕ Added to: + Previous accounts still due")
            else:
                result['error'] = "Some operations failed - check logs for details"
                print(f"\n⚠️ Previous contact workflow completed with some failures")
            
            return result
            
        except Exception as e:
            result['error'] = f"Error during previous contact workflow: {str(e)}"
            print(f"❌ {result['error']}")
            return result


# Standalone functions for integration with existing workflow
def get_previous_contact_balance(old_contact_id: str, access_token: str = None, tenant_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Standalone function to get balance for previous contact.
    
    Args:
        old_contact_id (str): ContactID of previous contact
        access_token (str, optional): Existing access token
        tenant_id (str, optional): Existing tenant ID
        
    Returns:
        dict: Balance information with outstanding amount and status
    """
    try:
        manager = XeroPreviousContactManager(access_token, tenant_id)
        return manager.get_contact_balance(old_contact_id)
    except Exception as e:
        print(f"Error in get_previous_contact_balance: {str(e)}")
        return None


def handle_previous_contact_after_reassignment(old_contact_id: str, access_token: str = None, tenant_id: str = None) -> Dict[str, Any]:
    """
    Standalone function to handle previous contact after successful invoice reassignment.
    
    Args:
        old_contact_id (str): ContactID of previous contact
        access_token (str, optional): Existing access token
        tenant_id (str, optional): Existing tenant ID
        
    Returns:
        dict: Result with success status and details
    """
    try:
        manager = XeroPreviousContactManager(access_token, tenant_id)
        return manager.handle_previous_contact_workflow(old_contact_id)
    except Exception as e:
        print(f"Error in handle_previous_contact_after_reassignment: {str(e)}")
        return {
            'success': False,
            'error': f"Error during previous contact handling: {str(e)}"
        }


# Example usage and testing
if __name__ == "__main__":
    print("Xero Previous Contact Manager - Test Mode")
    print("-" * 50)
    
    # Example: Check contact balance
    # balance_info = get_previous_contact_balance("contact-id-here")
    # if balance_info:
    #     print(f"Outstanding balance: ${balance_info['outstanding']:.2f}")
    #     print(f"Has balance: {balance_info['has_balance']}")
    
    # Example: Handle previous contact workflow
    # result = handle_previous_contact_after_reassignment("contact-id-here")
    # print(f"Workflow success: {result['success']}")
    # if result.get('error'):
    #     print(f"Error: {result['error']}")
