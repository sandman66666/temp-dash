"""
Test script for Descope API integration
"""
import asyncio
import aiohttp
import os
import ssl
import certifi
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_descope_connection():
    # Load environment variables
    load_dotenv()
    
    descope_url = os.getenv('DESCOPE_API_URL')
    bearer_token = os.getenv('DESCOPE_BEARER_TOKEN')
    
    logger.info(f"Testing Descope API connection to: {descope_url}")
    logger.info(f"Using bearer token: {bearer_token[:10]}...")  # Show first 10 chars
    
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json'
    }
    
    # Search query to get all users
    payload = {
        "tenantIds": [],
        "text": "",
        "roleNames": [],
        "loginIds": [],
        "ssoAppIds": [],
        "customAttributes": {}
    }
    
    # Create SSL context with certifi certificates
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    try:
        conn = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=conn) as session:
            logger.info("Making request to Descope API...")
            async with session.post(descope_url, headers=headers, json=payload) as response:
                logger.info(f"Response status: {response.status}")
                response_text = await response.text()
                logger.info(f"Response body: {response_text[:200]}...")  # Show first 200 chars
                
                if response.status == 200:
                    data = await response.json()
                    users = data.get('users', [])
                    logger.info(f"Successfully fetched users. Total count: {len(users)}")
                else:
                    logger.error(f"Error response from Descope: {response.status}")
                    
    except Exception as e:
        logger.error(f"Exception while testing Descope connection: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_descope_connection())