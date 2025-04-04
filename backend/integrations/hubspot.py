import json
import secrets
import base64
import httpx
import asyncio
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

authorization_url = (
    f'https://app.hubspot.com/oauth/authorize'
    f'?client_id={CLIENT_ID}'
    f'&redirect_uri={REDIRECT_URI}'
    f'&scope=oauth%20crm.objects.contacts.read'
)


async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode('utf-8')).decode('utf-8')
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)
    return f'{authorization_url}&state={encoded_state}'


async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error'))
    
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')

    # Decode state from the request
    state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode('utf-8'))
    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    # Retrieve saved state from Redis
    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    if not saved_state:
        raise HTTPException(status_code=400, detail='No saved state found.')

    # Decode saved state from Redis
    saved_state_data = json.loads(base64.urlsafe_b64decode(saved_state).decode('utf-8'))

    # Validate state
    if original_state != saved_state_data.get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    # Exchange authorization code for access token
    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                'https://api.hubapi.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'redirect_uri': REDIRECT_URI,
                'code': code
            },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
        )

    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)

    # Close popup window
    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)


async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    print(f"Credentials: {credentials}")
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')
    return credentials

async def create_integration_item_metadata_object(response_json):
    integration_items = []
    
    for contact in response_json:
        properties = contact.get('properties', {})
        
        integration_item = IntegrationItem(
            id=contact.get('id'),
            type="contact",
            name=f"{properties.get('firstname', '')} {properties.get('lastname', '')}".strip(),
            creation_time=properties.get('createdate', None),
            last_modified_time=properties.get('lastmodifieddate', None)
        )
        
        integration_items.append(integration_item)
    
    return integration_items


async def get_items_hubspot(credentials):
    access_token = json.loads(credentials).get('access_token')

    async with httpx.AsyncClient() as client:
        response = await client.get(
            'https://api.hubapi.com/crm/v3/objects/contacts',
            headers={'Authorization': f'Bearer {access_token}'}
        )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail='Failed to fetch HubSpot items')

    data = response.json()
    contacts = data.get("results", [])

    # Convert to IntegrationItem format
    integration_items = await create_integration_item_metadata_object(contacts)
    print(f"Integration Items: {integration_items}")

    return integration_items
