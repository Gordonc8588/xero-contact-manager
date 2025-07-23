
import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv('XERO_CLIENT_ID')
client_secret = os.getenv('XERO_CLIENT_SECRET')

print(f"Client ID: {client_id[:10]}..." if client_id else "Client ID not found")
print(f"Client Secret: {client_secret[:10]}..." if client_secret else "Client Secret not found")

if client_id and client_secret:
    # Test authentication
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        'Authorization': f'Basic {credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    token_data = {
        'grant_type': 'client_credentials',
        'scope': 'accounting.contacts'
    }
    
    print("Testing authentication...")
    response = requests.post(
        'https://identity.xero.com/connect/token',
        data=token_data,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
else:
    print("Missing credentials!")
