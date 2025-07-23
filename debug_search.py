
import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv('XERO_CLIENT_ID')
client_secret = os.getenv('XERO_CLIENT_SECRET')

# Get access token
credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
token_response = requests.post(
    'https://identity.xero.com/connect/token',
    data={'grant_type': 'client_credentials', 'scope': 'accounting.contacts'},
    headers={'Authorization': f'Basic {credentials}', 'Content-Type': 'application/x-www-form-urlencoded'}
)

access_token = token_response.json()['access_token']

# Get tenant info
connections_response = requests.get(
    'https://api.xero.com/connections',
    headers={'Authorization': f'Bearer {access_token}'}
)

print(f"Connections response: {connections_response.status_code}")
if connections_response.status_code == 200:
    connections = connections_response.json()
    if connections:
        tenant_id = connections[0]['tenantId']
        print(f"Tenant ID: {tenant_id}")
        
        # Test different ways to search for contacts
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Xero-Tenant-Id': tenant_id,
            'Content-Type': 'application/json'
        }
        
        # 1. Get all contacts first
        print("\n1. Getting all contacts...")
        all_contacts_response = requests.get(
            'https://api.xero.com/api.xro/2.0/Contacts',
            headers=headers
        )
        
        print(f"All contacts response status: {all_contacts_response.status_code}")
        print(f"Response headers: {dict(all_contacts_response.headers)}")
        print(f"Response length: {len(all_contacts_response.text)}")
        print(f"First 500 chars: {all_contacts_response.text[:500]}")
        
        if all_contacts_response.status_code == 200 and all_contacts_response.text:
            try:
                data = all_contacts_response.json()
                contacts = data.get('Contacts', [])
                print(f"Found {len(contacts)} total contacts")
                
                # Show first few account numbers
                print("\nFirst 5 contact account numbers:")
                for i, contact in enumerate(contacts[:5]):
                    account_num = contact.get('AccountNumber', 'N/A')
                    name = contact.get('Name', 'N/A')
                    print(f"  {i+1}. {account_num} - {name}")
                    
            except Exception as e:
                print(f"Error parsing JSON: {e}")
        
        # 2. Try searching for specific account
        print(f"\n2. Searching for AEP019012/1B...")
        params = {'where': 'AccountNumber=="AEP019012/1B"'}
        
        search_response = requests.get(
            'https://api.xero.com/api.xro/2.0/Contacts',
            headers=headers,
            params=params
        )
        
        print(f"Search response status: {search_response.status_code}")
        print(f"Search response: {search_response.text}")
        
    else:
        print("No connections found")
else:
    print(f"Connections error: {connections_response.text}")
