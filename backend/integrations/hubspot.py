import json
import secrets
import base64
import httpx
import asyncio
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis
from dotenv import load_dotenv
import os
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
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    return f'{authorization_url}&state={encoded_state}'

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error'))
    

    code = request.query_params.get('code')
    print(f"Code: {code}")  # Debugging log
    encoded_state = request.query_params.get('state')
    print(f"Encoded State: {encoded_state}")  # Debugging log


    # Try decoding base64 safely
    try:
        decoded_state = json.loads(base64.urlsafe_b64decode(encoded_state).decode())
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid state encoding')
    
    original_state = decoded_state.get('state')
    user_id = decoded_state.get('user_id')
    org_id = decoded_state.get('org_id')

    print(f"Original State: {original_state}")  # Debugging log
    print(f"User ID: {user_id}")  # Debugging log
    print(f"Org ID: {org_id}")  # Debugging log

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.hubapi.com/oauth/v1/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uri': REDIRECT_URI,
                'code': code
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
    await delete_key_redis(f'hubspot_state:{org_id}:{user_id}')
    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)


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
    
    return json.loads(credentials)

async def refresh_hubspot_token(user_id, org_id):
    credentials = await get_hubspot_credentials(user_id, org_id)
    refresh_token = credentials.get('refresh_token')

    async with httpx.AsyncClient() as client:
        token_data = {
            'grant_type': 'refresh_token',
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'refresh_token': refresh_token
        }

        response = await client.post(
            'https://api.hubapi.com/oauth/v1/token',
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

    if response.status_code == 200:
        new_credentials = response.json()
        await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(new_credentials), expire=600)
        return new_credentials
    else:
        raise HTTPException(status_code=400, detail='Failed to refresh token')

async def get_items_hubspot(credentials):
    print(f"Credentials: {credentials}")
    access_token = json.loads(credentials).get('access_token')
    print(f"Access Token: {access_token}")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            'https://api.hubapi.com/crm/v3/objects/contacts',
            headers={'Authorization': f'Bearer {access_token}'}
        )

    # if response.status_code == 401:
    #     credentials = await refresh_hubspot_token(user_id, org_id)
    #     return await get_items_hubspot(user_id, org_id)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail='Failed to fetch HubSpot items')
    
    data = response.json()
    
    print(f'list_of_integration_item_metadata: {data["results"]}')
    return response.json().get('results', [])
