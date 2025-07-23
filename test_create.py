
import os
import sys
import requests
import base64
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.append('src')
from constants import increment_account_sequence

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
tenant_id = requests.get(
    'https://api.xero.com/connections',
    headers={'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'}
).json()[0]['tenantId']

print(f"Tenant ID: {tenant_id}")

# Test creating a simple contact based on WDS007142/2A
headers = {
    'Authorization': f'Bearer {access_token}',
    'Xero-Tenant-Id': tenant_id,
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# Create a test contact
new_account = increment_account_sequence("WDS007142/2A")
print(f"Original account: WDS007142/2A")
print(f"New account number: {new_account}")

# Add the contact code
new_account_with_code = f"{new_account.split('/')[0]}/2A"
print(f"New account with code: {new_account_with_code}")

test_contact = {
    'Name': f'{new_account.split("/")[0]} - (3F2) 7 Westfield Street',
    'AccountNumber': new_account_with_code,
    'ContactStatus': 'ACTIVE',
    'ContactPersons': [{
        'FirstName': 'Occupier',
        'LastName': '',
        'EmailAddress': '',
        'IncludeInEmails': True
    }]
}

payload = {'Contacts': [test_contact]}

print(f"Sending contact data:")
print(f"  Name: {test_contact['Name']}")
print(f"  AccountNumber: {test_contact['AccountNumber']}")
print(f"  ContactPersons: {test_contact['ContactPersons']}")

create_response = requests.post(
    'https://api.xero.com/api.xro/2.0/Contacts',
    headers=headers,
    json=payload
)

print(f"\nCreate response status: {create_response.status_code}")
print(f"Create response headers: {dict(create_response.headers)}")
print(f"Create response text: {create_response.text}")

if create_response.status_code == 200:
    try:
        result = create_response.json()
        print(f"Success! Created contact: {result}")
    except Exception as e:
        print(f"JSON parse error: {e}")
