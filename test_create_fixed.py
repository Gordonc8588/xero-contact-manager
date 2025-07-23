
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

headers = {
    'Authorization': f'Bearer {access_token}',
    'Xero-Tenant-Id': tenant_id,
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# Test 1: Create contact WITH email (should use primary contact fields)
print("=== TEST 1: Contact with email ===")
new_account = increment_account_sequence("WDS007142/2A")
new_account_with_code = f"{new_account.split('/')[0]}/2A"

test_contact_with_email = {
    'Name': f'{new_account.split("/")[0]} - (3F2) 7 Westfield Street',
    'AccountNumber': new_account_with_code,
    'ContactStatus': 'ACTIVE',
    'FirstName': 'New',
    'LastName': 'Occupier', 
    'EmailAddress': 'newtenant@example.com'
}

payload = {'Contacts': [test_contact_with_email]}
create_response = requests.post('https://api.xero.com/api.xro/2.0/Contacts', headers=headers, json=payload)

print(f"Status: {create_response.status_code}")
if create_response.status_code == 200:
    print("SUCCESS! Contact created with email.")
else:
    print(f"Error: {create_response.text[:500]}")

print("\n" + "="*50)

# Test 2: Create contact WITHOUT email (should work with just primary fields)
print("=== TEST 2: Contact without email ===")
new_account2 = increment_account_sequence(new_account_with_code)
new_account_with_code2 = f"{new_account2.split('/')[0]}/2A"

test_contact_no_email = {
    'Name': f'{new_account2.split("/")[0]} - (3F2) 7 Westfield Street',
    'AccountNumber': new_account_with_code2,
    'ContactStatus': 'ACTIVE',
    'FirstName': 'Another',
    'LastName': 'Occupier'
    # No EmailAddress
}

payload2 = {'Contacts': [test_contact_no_email]}
create_response2 = requests.post('https://api.xero.com/api.xro/2.0/Contacts', headers=headers, json=payload2)

print(f"Status: {create_response2.status_code}")
if create_response2.status_code == 200:
    print("SUCCESS! Contact created without email.")
else:
    print(f"Error: {create_response2.text[:500]}")
