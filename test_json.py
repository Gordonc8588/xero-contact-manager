
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

# Get tenant info with JSON header
connections_response = requests.get(
    'https://api.xero.com/connections',
    headers={
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
)

tenant_id = connections_response.json()[0]['tenantId']

# Test search with JSON headers
headers = {
    'Authorization': f'Bearer {access_token}',
    'Xero-Tenant-Id': tenant_id,
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

params = {'where': 'AccountNumber=="AEP019012/1B"'}

search_response = requests.get(
    'https://api.xero.com/api.xro/2.0/Contacts',
    headers=headers,
    params=params
)

print(f"Status: {search_response.status_code}")
print(f"Content-Type: {search_response.headers.get('Content-Type')}")
print(f"First 200 chars: {search_response.text[:200]}")

if search_response.status_code == 200:
    try:
        data = search_response.json()
        contacts = data.get('Contacts', [])
        print(f"Found {len(contacts)} contacts")
        if contacts:
            contact = contacts[0]
            print(f"Name: {contact.get('Name')}")
            print(f"Account: {contact.get('AccountNumber')}")
    except Exception as e:
        print(f"JSON parse error: {e}")
