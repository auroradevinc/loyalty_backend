import json

import os
import logging
import jwt
from jwt import PyJWKClient

try:
    customer_region = os.environ['LOYALTY_CUSTOMER_COGNITO_REGION']
    customer_userPoolId =  os.environ['LOYALTY_CUSTOMER_COGNITO_USER_POOL_ID']
    customer_url = (
        f"https://cognito-idp.{customer_region}.amazonaws.com/{customer_userPoolId}/.well-known/jwks.json"
    )
    customer_app_client = os.environ["LOYALTY_CUSTOMER_COGNITO_APP_CLIENT_ID"]

    # fetching jwks
    print('fetching jwks')
    customer_jwks_client = PyJWKClient(customer_url)
except Exception as e:
    logging.error(e)
    raise ("Unable to download CUSTOMER JWKS")

try:
    admin_region = os.environ['LOYALTY_ADMIN_COGNITO_REGION']
    admin_userPoolId =  os.environ['LOYALTY_ADMIN_COGNITO_USER_POOL_ID']
    admin_url = (
        f"https://cognito-idp.{admin_region}.amazonaws.com/{admin_userPoolId}/.well-known/jwks.json"
    )
    admin_app_client = os.environ["LOYALTY_ADMIN_COGNITO_APP_CLIENT_ID"]

    # fetching jwks
    print('fetching jwks')
    admin_jwks_client = PyJWKClient(admin_url)
except Exception as e:
    logging.error(e)
    raise ("Unable to download ADMIN JWKS")


def return_response(isAuthorized, other_params={}):
    return {"isAuthorized": isAuthorized, "context": other_params}


def lambda_handler(event, context):
    print(event)
    
    query_param = event["queryStringParameters"] if "queryStringParameters" in event.keys() else None
    
    if query_param['authorizer'] == os.environ["LOYALTY_CUSTOMER_API_CALL_KEY"]:
            print('AUTHORIZING CUSTOMER')
    elif query_param['authorizer'] == os.environ["LOYALTY_ADMIN_API_CALL_KEY"]:
            print('AUTHORIZING ADMIN')
    else:
        print(f"UNAUTHORIZED ACCESS: , {query_param['authorizer']}")
        return return_response(isAuthorized=False, other_params={})
        
    try:
        # fetching access token from event
        print('fetching access token from event')
        token = event["headers"]["authorization"]

        # check token structure
        print('check token structure')
        if len(token.split(".")) != 3:
            return return_response(isAuthorized=False, other_params={})
    except Exception as e:
        logging.error(e)
        return return_response(isAuthorized=False, other_params={})

    try:
        # get unverified headers
        print('get unverified headers')
        headers = jwt.get_unverified_header(token)
        # get signing key
        print('get signing key')
        
        if query_param['authorizer'] == os.environ["LOYALTY_CUSTOMER_API_CALL_KEY"]:
            signing_key = customer_jwks_client.get_signing_key_from_jwt(token)
        
        if query_param['authorizer'] == os.environ["LOYALTY_ADMIN_API_CALL_KEY"]:
            signing_key = admin_jwks_client.get_signing_key_from_jwt(token)
        
        # validating exp, iat, signature, iss
        print('validating exp, iat, signature, iss')
        data = jwt.decode(
            token,
            signing_key.key,
            algorithms=[headers.get("alg")],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": False,
            },
        )
    except jwt.InvalidTokenError as e:
        logging.error(e)
        return return_response(isAuthorized=False, other_params={})
    except jwt.DecodeError as e:
        logging.error(e)
        return return_response(isAuthorized=False, other_params={})
    except jwt.InvalidSignatureError as e:
        logging.error(e)
        return return_response(isAuthorized=False, other_params={})
    except jwt.ExpiredSignatureError as e:
        logging.error(e)
        return return_response(isAuthorized=False, other_params={})
    except jwt.InvalidIssuerError as e:
        logging.error(e)
        return return_response(isAuthorized=False, other_params={})
    except jwt.InvalidIssuedAtError as e:
        logging.error(e)
        return return_response(isAuthorized=False, other_params={})
    except Exception as e:
        logging.error(e)
        return return_response(isAuthorized=False, other_params={})

    try:
        # verifying audience...use data['client_id'] if verifying an access token else data['aud']
        print('verifying audience')
        if query_param['authorizer'] == os.environ["LOYALTY_CUSTOMER_API_CALL_KEY"]:
            app_client = customer_app_client
        if query_param['authorizer'] == os.environ["LOYALTY_ADMIN_API_CALL_KEY"]:
            app_client = admin_app_client
            
        if app_client != data.get("client_id"):
            return return_response(isAuthorized=False, other_params={})
    except Exception as e:
        logging.error(e)
        return return_response(isAuthorized=False, other_params={})

    try:
        # token_use check
        print("token_use check")
        if data.get("token_use") != "access":
            return return_response(isAuthorized=False, other_params={})
    except Exception as e:
        logging.error(e)
        return return_response(isAuthorized=False, other_params={})

    # try:
    #     # scope check
    #     print('scope check')
    #     if "openid" not in data.get("scope").split(" "):
    #         return return_response(isAuthorized=False, other_params={})
    # except Exception as e:
    #     logging.error(e)
    #     return return_response(isAuthorized=False, other_params={})
    
    print('Authorized')
    return return_response(isAuthorized=True, other_params={})
