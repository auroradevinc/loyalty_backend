# Installation Command: pip3 install -t $PWD [package_name]
import json
import jwt
from base64 import b64decode
from botocore.vendored import requests

import os
cognito_region = os.environ['LOYALTY_CUSTOMER_COGNITO_REGION']
cognito_user_pool = os.environ['LOYALTY_CUSTOMER_COGNITO_USER_POOL_ID']

def lambda_handler(event, context):
    # Get the JWT from the event
    jwt_token = event['headers']['Authorization']
    
    # Split the JWT to get the encoded header, payload, and signature
    encoded_header, encoded_payload, encoded_signature = jwt_token.split('.')
    
    # Decode the header, payload, and signature
    header = json.loads(b64decode(encoded_header).decode('utf-8'))
    payload = json.loads(b64decode(encoded_payload).decode('utf-8'))
    signature = b64decode(encoded_signature)
    
    # Download the JSON Web Key Set (JWKS) from the user pool
    jwks_url = f"https://cognito-idp.{cognito_region}.amazonaws.com/{cognito_user_pool}/.well-known/jwks.json"
    jwks = requests.get(jwks_url).json()
    
    # Search the JWKS for the public key that matches the key ID in the header
    key_id = header['kid']
    key = None
    for jwk in jwks['keys']:
        if jwk['kid'] == key_id:
            key = jwk
            break
        
    # Use the key to verify the JWT's signature
    is_valid = False
    try:
        jwt.decode(jwt_token, key, algorithms='RS256')
        is_valid = True
    except jwt.exceptions.InvalidSignatureError:
        is_valid = False
        
    if is_valid:
        # JWT is valid, continue with the login process
        return {"statusCode": 200, "body": "JWT is valid"}
    else:
        # JWT is not valid, return an error
        return {"statusCode": 401, "body": "JWT is not valid"}
