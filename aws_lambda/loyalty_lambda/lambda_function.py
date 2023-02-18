# Installation Command: pip3 install -t $PWD [package_name]
import os
import json
import pymysql
import boto3
import random
import itertools
from ndicts.ndicts import NestedDict
from datetime import datetime
from base64 import b64decode
from botocore.vendored import requests

# -----------------------------
# Request, Response Information
# -----------------------------
path = query_param = body = method = None
response = {}

# -----------
# RDS Config.
# -----------
import os
endpoint = os.environ['LOYALTY_RDS_ENDPOINT']
username = os.environ['LOYALTY_RDS_USERNAME']
password = os.environ['LOYALTY_RDS_PASSWORD']
database_name = os.environ['LOYALTY_RDS_DB_NAME']
connections = pymysql.connect(host=endpoint, user=username, password=password, database=database_name)

# --------------
# DYNAMO Config.
# --------------
dynamo_table_name = os.environ['LOYALTY_DYNAMO_TABLE_NAME']
client = boto3.resource('dynamodb')

# ------------------------------
# INVITE CODE INCRYPTION CONFIG.
# ------------------------------
invite_code_key = os.environ['INVITE_CODE_KEY']

def generate_unique_card_id():
    allowed_characters = '0123456789ABCDEFGHIJKLMONPQRSTUVWXYZ'
    unique_card_id = list(itertools.combinations_with_replacement(allowed_characters, 3))
    
    return unique_card_id

def extract_req_info(event):
    print("* EXTRACTING REQUEST INFORMATION")
    
    global path, query_param, body, method, response # required to modify the global variable
    
    # Assign Req params
    path        = event["rawPath"] if event["rawPath"] != "" else None
    body        = json.loads(event["body"]) if "body" in event.keys() else None
    
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # ONLY FOR LAMBDA TESTING, REMOVE AFTER, USE THE ONE ABOVE
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # body = event["body"] if "body" in event.keys() else None
    
    method      = NestedDict(event)["requestContext","http","method"]
    query_param = event["queryStringParameters"] if "queryStringParameters" in event.keys() else None
    
    print(f"-\t Event: {event}")
    # print(json.dumps(event, sort_keys=True, indent=4))
    print(f"-\t Method {method}, Path {path}, QueryString {query_param}")
    print(f"-\t Body: {body}")
    
    reponse = {'type': 'success', 'data': {'method': method, 'path': path, 'query_param': query_param, 'body': body}}
    
def generate_api_response(statusCode):
    api_response = {
        'statusCode': statusCode,
        'body': json.dumps(response, default=str),
    }
    print(f"* API RESPONSE: {api_response}")
    return api_response

def lambda_handler(event, context):
    
    global response # required to modify the global variable; Line(global path, query_param, body, method) not required since modification not required in function but only read by value
    
    # Extract Request/Event Information
    extract_req_info(event)
    
    # --------------
    # Initialization
    # --------------
    print("* INITIALIZATION")
    
    # RDS Connection
    print(f"-\t RDS CONNECTION", end='...')
    cursor = connections.cursor()
    print(f"done", end='\n')
    
    # DYNAMO Connection
    print(f"-\t DYNAMO CONNECTION", end='...')
    customer_activity_table = client.Table(dynamo_table_name)
    print(f"done", end='\n')
    
    
    # ------------------
    # DATABASE Execution
    # ------------------
    # RDS Execution
    # Ref. https://www.w3schools.com/sql/default.asp
    # ----------------------------------------------
    # cursor.execute('SQL QUERY HERE') 
    # cursor.commit()
    # rows = cursor.fetchall()
    
    # DYNAMO Execution
    # Ref. https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html
    # --------------------------------------------------------------------------------
    
    # --------------------------------------------
    # API Endpoints Match with Database Procedures
    # --------------------------------------------
    print(f"* HANDLING API ENDPOINTS")
    
    # --------------------------
    # TEST ROUTES: DELETE AFTER |
    if method == "POST" and path == "/test":
        print(f"-\t Handling {method} {path}")
        response = {'TEST' : 'SUCCESS', 'DATA': body}
    if method == "GET" and path == "/test":
        print(f"-\t Handling {method} {path}")
        response = {'TEST' : 'SUCCESS', 'DATA': body}
    # TEST ROUTES: DELETE AFTER |
    # --------------------------
    
    # ------------------------------------
    # CUSTOMER & ADMIN INVOKED ROUTES
    # ------------------------------------
    if method == 'GET' and path == '/assign-new-card':
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param:
        # Payload: 
        print(f"-\t Handling {method} {path}")
        
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Generate Unique Card ID
        # 2. Add a new card to Card DB with Origin Online SignUp & Client ID 1(for now)
        
        # 1.
        print(f"-\t\t - Generate Unique Card ID")
        # Card ID [{group_name_identifier}{card_type}{unique_id}]
        card_id = ''
        card_cvc = random.randint(0, 999)
        
        group_name_identifier = '00A' # represents glowbal group
        card_type = '1' # represents GOLD card
        unique_ids = generate_unique_card_id()
        for index, item in enumerate(unique_ids): 
            uid = ''.join(item)
            card_id = f"{group_name_identifier}{card_type}{uid}"
            
            cursor.execute("SELECT * FROM CARD c WHERE c.card_id = %s", (card_id,)) # IMPORTANT BUG ISSUE: DON'T FORGET TO ADD ,(COMMA) AFTER variable in execute data
            connections.commit()
            result = cursor.fetchall()
            
            if len(result) == 0: #card_id is unique
                break
        
        print(f"-\t\t\t|- Generated Card ID: {card_id}")
        
        print(f"-\t\t - Add a new card to Card DB with Origin Online SignUp & Client ID 1(for glowbal)")
        data = (
            card_id,
            1, # client_id
            card_cvc,
            0, # status
            None, # customer_id
            "GOLD", # card_type
            "ONLINE SIGNUP", # origin
        )
        cursor.execute("INSERT INTO CARD VALUES(%s, %s, %s, %s, %s, %s, %s)", data)
        #cursor.execute('SELECT LAST_INSERT_ID()') # Returns ID of last insertion
        connections.commit()
        
        #result = cursor.fetchall()
        #print(f"-\t\t\t|- Added new Card: {result[0]}")
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        
        print(f"-\t CLEAN UP & LOGGING")
        
        # 1. 
        print(f"-\t\t - Generate Response Object")
        response = {
            'type': 'success',
            'data': {
                'card': {
                    'id': card_id,
                    'cvc': card_cvc
                }
            }
        }
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
        
    elif method == 'GET' and path == "/verify-card":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Card Number, Card CVC
        # Payload: 
        print(f"-\t Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Verify Card ID & CVC from Card DB
        print(f"-\t DB PROCEDURE")
        
        # 1.
        print(f"-\t\t - Verify Card ID & CVC from Card DB")
        data = (
            query_param['card_id']
        )
        cursor.execute("SELECT * from CARD c where c.card_id = %s", data)
        connections.commit()
        
        result = cursor.fetchall()
        print(f"-\t\t\t|- Card: {result}")
    
        card = result[0]
        card_id = card[0]
        card_cvc = card[2]
        
        verification = 'error'
        if card_cvc == int(query_param['card_cvc']):
            print(f"-\t\t\t|- Card Verified")
            verification = 'success'
        else:
            print(f"-\t\t\t|- Card NOT Verified")
            verification = 'error'
            card = None
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        
        print(f"-\t CLEAN UP & LOGGING")
        
        # 1. 
        print(f"-\t\t - Generate Response Object")
        response = {
            'type': verification,
            'data': {
                'card': card
            }
        }
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
    
    elif method == "POST" and path == "/signup":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: POST
        # Query Param: 
        # Payload: Customer Data, Card Number
        print(f"-\t Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Get Client ID from Card ID
        # 2. Add Customer(with or without mailing address) to Customer DB
        # 3. Add Card with Customer ID(F key) to Card DB
        print(f"-\t DB PROCEDURE")
        
        # 1.
        print(f"-\t\t - Get Client ID from Card ID")
        data = (
            body["card"]["id"]
        )
        new_customer_card_id = body["card"]["id"]
        cursor.execute("SELECT * from CARD c where c.card_id = %s", data)
        connections.commit()
        
        result = cursor.fetchall() # returns tuple of tuples(table rows)
        new_customer_client_id = result[0][1] # 1st row, 1st column(card_id) 2nd column(client_id)
        print(f"-\t\t\t|- New Customer client_id: {new_customer_client_id}")
        print(f"-\t\t\t|- New Customer Card: {result}")
        
        # 2.
        print(f"-\t\t - Add Customer(with or without mailing address) to Customer DB")
        member_since = datetime.now().strftime('%Y-%m-%d')
        data = (
            body["customer"]["id"], # Can also be "NULL" since customer_id is auto incremented
            new_customer_client_id,
            body["customer"]["full_name"],
            body["customer"]["phone_number"], 
            body["customer"]["email"], 
            0,  # verification will be updated when applicable
            body["customer"]["address"],
            member_since,
            0,  # num_referred will be incremented when applicable
            0,  # reward points will be incremented when applicable
            0   # money spend will be incremented when applicable
        )
        cursor.execute('INSERT INTO CUSTOMER VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', data)
        connections.commit()
        
        new_customer_customer_id = body["customer"]["id"]
        print(f"-\t\t\t|- New Customer customer_id: {new_customer_customer_id}")
        
        # 3.
        print(f"-\t\t - Add Card with Customer ID(F key) to Card DB")
        
        data = (
            new_customer_customer_id,
            1, #set card status to active
            new_customer_card_id
        )
        cursor.execute('UPDATE CARD c SET c.customer_id = %s, c.status = %s WHERE c.card_id = %s', data)
        connections.commit()
        
        result = cursor.fetchall()
        print(f"-\t\t\t|- New Customer card_id: {new_customer_card_id}")
        print(f"-\t\t\t|- New Customer Card: {result}")
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Append to Customer Activity/History DB
        # 2. Generate Response Object
        print(f"-\t CLEAN UP & LOGGING")
        
        # 1.
        print(f"-\t\t - Append to Customer Activity/History DB")
        
        # Format: {"description": "", "card_id": "", "scan_id": "", "date_time": "", "details": ""}
        activity_log = {
            'customer_id' : new_customer_customer_id,
            'activity_log': {"description": "New Card Assigned", "card_id": "1", "scan_id": "NULL", "date_time": "2022-11-22 13:00:00", "details": ""}
        }
        customer_activity_table.put_item(Item = activity_log)
        print(f"-\t\t\t|- Activity Log: {activity_log}")
        
        # 2. 
        print(f"-\t\t - Generate Response Object")
        cursor.execute('SELECT * FROM CUSTOMER c WHERE c.customer_id = %s', {new_customer_customer_id})
        connections.commit()
        
        result = cursor.fetchall()
        response = {
            'type': 'success',
            'data': {
                'customer' : {
                    'customer_id': result[0][0],
                    'client_id': result[0][1],
                    'full_name': result[0][2],
                    'phone_number': result[0][3],
                    'email': result[0][4],
                    'verification': result[0][5],
                    'address': result[0][6],
                    'num_referred': result[0][7],
                    'reward_points': result[0][8]
                }
            }
        }
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
        
    elif method == "GET" and path == "/get-customer-info":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Customer ID
        # Payload:
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. By Card ID
        # - Get Customer ID from Card ID in Card DB
        # - Search Customer in Customer DB
        # 2. By Customer ID
        # - Search Customer in Customer DB
        print(f"-\t DB PROCEDURE")
        
        if query_param and 'card_id' in query_param.keys():
            # 1.
            print(f"-\t\t By Card ID")
            data = (
                query_param['card_id']
            )
            cursor.execute('SELECT * FROM CARD c WHERE c.card_id = %s;', data)
            connections.commit()
            
            result = cursor.fetchall()
            customer_id = result[0][4]
            print(f"-\t\t\t|- Searched Customer customer_id: {customer_id}")
            print(f"-\t\t\t|- {result}")
            
            data = (
                customer_id
            )
        else:
            print(f"-\t\t By Customer ID")
            data = (
                query_param['customer_id']
            )
        
        # Common
        print(f"-\t\t Search Customer in Customer DB")
        cursor.execute('SELECT * FROM CUSTOMER c WHERE c.customer_id = %s;', data)
        connections.commit()
        
        result = cursor.fetchall()
        customer_data = result[0]
        print(f"-\t\t\t|- Searched Customer Data: {customer_data}")
        print(f"-\t\t\t|- {result}")
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        print(f"-\t CLEAN UP & LOGGING")
        response = {
            'type': 'success',
            'data': {
                'customer' : {
                    'customer_id': result[0][0],
                    'client_id': result[0][1],
                    'full_name': result[0][2],
                    'phone_number': result[0][3],
                    'email': result[0][4],
                    'verification': result[0][5],
                    'address': result[0][6],
                    'member_since': result[0][7],
                    'num_referred': result[0][8],
                    'reward_points': result[0][9],
                    'money_spent': result[0][10]
                }
            }
        }
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
    
    elif method == "GET" and path =="/get-customer-card-info":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Customer ID
        # Payload:
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Search Card in Card DB
        print(f"-\t DB PROCEDURE")
        
        # 1. Generate Response Object
        print(f"-\t Search Card in Card DB")
        data = (
            query_param['customer_id']
        )
        cursor.execute('SELECT * FROM CARD c, CLIENT cl WHERE c.customer_id = %s AND c.client_id = cl.client_id', data)
        connections.commit()
        
        result = cursor.fetchall()
        card_data = result[0]
        print(f"-\t\t\t|- Searched Card Data: {card_data}")
        print(f"-\t\t\t|- {result}")
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        print(f"-\t CLEAN UP & LOGGING")
        response = {
            'type': 'success',
            'data': {
                'card' : {
                    'card_id': result[0][0],
                    'client_id': result[0][1],
                    'client_name': result[0][8],
                    'security_code': result[0][2],
                    'status': result[0][3],
                    'customer_id': result[0][4],
                    'card_type': result[0][5],
                    'origin': result[0][6],
                    'invite_code': result[0][0]
                }
            }
        }
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
       
    elif method == "GET" and path == "/get-customer-promo-info":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Card ID
        # Payload:
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Get Card type of Card in Card DB
        # 2. Search Customer Custom Promo in Promo DB
        # 3. Search All Promos in Promo DB
        
        # 1. 
        print(f"-\t\t Search Card in Card DB")
        card_id = query_param['card_id']
        data = (
            card_id
        )
        cursor.execute('SELECT * FROM CARD c WHERE c.card_id = %s', data)
        connections.commit()
        
        result = cursor.fetchall()
        card_type = result[0][5]
        print(f"-\t\t\t|- Customer Card Type: {card_type}")
        print(f"-\t\t\t|- {result}")
        
            
        # 2.
        print(f"-\t\t Search Customer Custom Promo in Promo DB")
        data = (
            card_id
        )
        
        cursor.execute('SELECT * FROM PROMO p, CLIENT c, BUSINESS b WHERE p.card_id = %s AND p.client_id = c.client_id AND p.bus_id = b.bus_id ORDER BY p.date_valid_from', data)
        connections.commit()
        
        result = cursor.fetchall()
        custom_promo = result
        print(f"-\t\t\t|- Customer Custom Promo's: {custom_promo}")
        print(f"-\t\t\t|- {custom_promo}")
        
        # 3.
        print(f"-\t\t Search All Promos in Promo DB")
        
        data = (
            None,
        )
        # Null(used as None) value works with an 'is' i.e. 'table_attribute is None'
        cursor.execute('SELECT * FROM PROMO p, CLIENT c, BUSINESS b WHERE p.card_id IS %s AND p.client_id = c.client_id AND p.bus_id = b.bus_id ORDER BY p.date_valid_from', data) 
        connections.commit()
        
        result = cursor.fetchall()
        all_promo = result
        print(f"-\t\t\t|- Customer All Promo's: {all_promo}")
        print(f"-\t\t\t|- {all_promo}")
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        
        print(f"-\t CLEAN UP & LOGGING")
        
        # 1. 
        print(f"-\t\t - Generate Response Object")
        custom_promo_object_list = []
        all_promo_object_list = []
        for index, promo_row in enumerate(custom_promo):
            custom_promo_object_list.append({
                'promo_id': promo_row[0],
                'client_id': promo_row[1],
                'client_name': promo_row[13],
                'bus_id': promo_row[2],
                'bus_name': promo_row[15],
                'card_id': promo_row[3],
                'promo_name': promo_row[8],
                'date_valid_from': promo_row[9],
                'date_valid_to': promo_row[10],
                'custom_promo_validity': promo_row[11]
            })
            
        for index, promo_row in enumerate(all_promo):
            promo = ''
            if card_type == 'EVENT': promo = promo_row[4]
            if card_type == 'GOLD': promo = promo_row[5]
            if card_type == 'PLATINUM': promo = promo_row[6]
            if card_type == 'TITANIUM': promo = promo_row[7]
            all_promo_object_list.append({
                'promo_id': promo_row[0],
                'client_id': promo_row[1],
                'client_name': promo_row[13],
                'bus_id': promo_row[2],
                'bus_name': promo_row[15],
                'card_id': promo_row[3],
                'promo_name': promo,
                'date_valid_from': promo_row[9],
                'date_valid_to': promo_row[10]
            })
            
        response = {
            'type': 'success',
            'data': {
                'promo': {
                    'custom_promo': custom_promo_object_list,
                    'all_promo': all_promo_object_list
                }
            }
        }
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
        
    # -------------------------
    # ADMIN ONLY INVOKED ROUTES
    # -------------------------
    elif method == "GET" and path == "/get-client-info":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Client Name
        # Payload: 
        print(f"-\t Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Get Client from Client DB
        
        # 1. 
        print(f"-\t\t - Get Client Name from Client DB")
        client_name = query_param['client_name']
        data = (
            client_name,
        )
        cursor.execute('SELECT * FROM CLIENT c WHERE c.name = %s', data)
        connections.commit()
        
        result = cursor.fetchall()
        client_id = result[0][0]
        print(f"-\t\t\t|- Client ID: {client_id}")
        print(f"-\t\t\t|- {result}")
        
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        
        print(f"-\t CLEAN UP & LOGGING")
        
        # 1. 
        print(f"-\t\t - Generate Response Object")
        
        response = {
            'type': 'success',
            'data': {
                'client': {
                    'client_id': result[0][0],
                    'client_name': result[0][1]
                }
            }
        }
        
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
        
    elif method == "GET" and path == "/get-business-info":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Business Name
        # Payload: 
        print(f"-\t Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Get Business from Business DB
        
        # 1. 
        print(f"-\t\t - Get Business from Business DB")
        bus_name = query_param['bus_name']
        data = (
            bus_name,
        )
        cursor.execute('SELECT * FROM BUSINESS b WHERE b.name = %s', data)
        connections.commit()
        
        result = cursor.fetchall()
        bus_id = result[0][0]
        print(f"-\t\t\t|- Business ID: {bus_id}")
        print(f"-\t\t\t|- {result}")
        
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        
        print(f"-\t CLEAN UP & LOGGING")
        
        # 1. 
        print(f"-\t\t - Generate Response Object")
        
        response = {
            'type': 'success',
            'data': {
                'business': {
                    'bus_id': result[0][0],
                    'bus_name': result[0][1],
                    'client_id': result[0][2]
                }
            }
        }
        
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
    
    elif method == "GET" and path == "/get-customer-promo-info-on-scan":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Card ID
        # Payload:
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Get Card type of Card in Card DB
        # 2. Search Customer Custom Promo in Promo DB
        # 3. Search All Promos in Promo DB
        
        # 1. 
        print(f"-\t\t Search Card in Card DB")
        card_id = query_param['card_id']
        card_cvc = query_param['card_cvc']
        bus_id = int(query_param['bus_id'])
        data = (
            card_id
        )
        cursor.execute('SELECT * FROM CARD c WHERE c.card_id = %s', data)
        connections.commit()
        
        result = cursor.fetchall()
        card_type = result[0][5]
        print(f"-\t\t\t|- Customer Card Type: {card_type}")
        print(f"-\t\t\t|- {result}")
        
        if int(card_cvc) != int(result[0][2]):
            response = {
                'type': 'error',
                'message': 'card cvc not valid',
                'data': {
                    'promo': {
                        'custom_promo': None,
                        'all_promo': None
                    }
                }
            }
            return generate_api_response(200)
        
            
        # 2.
        print(f"-\t\t Search Customer Custom Promo in Promo DB")
        
        if bus_id == 0: # No business ID selected, Get promos from all business
            data = (
                card_id,
            )
            cursor.execute('SELECT * FROM PROMO p, CLIENT c, BUSINESS b WHERE p.card_id = %s AND p.client_id = c.client_id AND p.bus_id = b.bus_id ORDER BY p.date_valid_from', data)
        else:
            data = (
                card_id,
                bus_id,
                bus_id
            )
            cursor.execute('SELECT * FROM PROMO p, CLIENT c, BUSINESS b WHERE p.card_id = %s AND p.client_id = c.client_id AND p.bus_id = %s AND b.bus_id = %s ORDER BY p.date_valid_from', data)
        connections.commit()
        
        result = cursor.fetchall()
        custom_promo = result
        print(f"-\t\t\t|- Customer Custom Promo's: {custom_promo}")
        print(f"-\t\t\t|- {custom_promo}")
        
        # 3.
        print(f"-\t\t Search All Promos in Promo DB")

        if bus_id == 0: # No business ID selected, Get promos from all business
            data = (
                None,
            )
            # Null(used as None) value works with an 'is' i.e. 'table_attribute is None'
            cursor.execute('SELECT * FROM PROMO p, CLIENT c, BUSINESS b WHERE p.card_id IS %s AND p.client_id = c.client_id AND p.bus_id = b.bus_id ORDER BY p.date_valid_from', data) 
        else:
            data = (
                None,
                bus_id,
                bus_id
            )
            cursor.execute('SELECT * FROM PROMO p, CLIENT c, BUSINESS b WHERE p.card_id IS %s AND p.client_id = c.client_id AND p.bus_id = %s AND b.bus_id = %s ORDER BY p.date_valid_from', data) 
        connections.commit()
        
        result = cursor.fetchall()
        all_promo = result
        print(f"-\t\t\t|- Customer All Promo's: {all_promo}")
        print(f"-\t\t\t|- {all_promo}")
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        print(f"-\t CLEAN UP & LOGGING")
        
        # 1. 
        print(f"-\t\t - Generate Response Object")
        custom_promo_object_list = []
        all_promo_object_list = []
        for index, promo_row in enumerate(custom_promo):
            custom_promo_object_list.append({
                'promo_id': promo_row[0],
                'client_id': promo_row[1],
                'client_name': promo_row[13],
                'bus_id': promo_row[2],
                'bus_name': promo_row[15],
                'card_id': promo_row[3],
                'promo_name': promo_row[8],
                'date_valid_from': promo_row[9],
                'date_valid_to': promo_row[10],
                'custom_promo_validity': promo_row[11]
            })
            
        for index, promo_row in enumerate(all_promo):
            promo = ''
            if card_type == 'EVENT': promo = promo_row[4]
            if card_type == 'GOLD': promo = promo_row[5]
            if card_type == 'PLATINUM': promo = promo_row[6]
            if card_type == 'TITANIUM': promo = promo_row[7]
            all_promo_object_list.append({
                'promo_id': promo_row[0],
                'client_id': promo_row[1],
                'client_name': promo_row[13],
                'bus_id': promo_row[2],
                'bus_name': promo_row[15],
                'card_id': promo_row[3],
                'promo_name': promo,
                'date_valid_from': promo_row[9],
                'date_valid_to': promo_row[10]
            })
            
        response = {
            'type': 'success',
            'data': {
                'promo': {
                    'custom_promo': custom_promo_object_list,
                    'all_promo': all_promo_object_list
                }
            }
        }
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
        
    elif method == "GET" and path == "/get-all-business-info":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Client Name
        # Payload: 
        print(f"-\t Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Get Client Name from Client DB
        # 2. Get Client Businesses from Business DB via Client ID
        
        # 1. 
        print(f"-\t\t - Get Client Name from Client DB")
        client_name = query_param['client_name']
        data = (
            client_name,
        )
        cursor.execute('SELECT * FROM CLIENT c WHERE c.name = %s', data)
        connections.commit()
        
        result = cursor.fetchall()
        client_id = result[0][0]
        print(f"-\t\t\t|- Client ID: {client_id}")
        print(f"-\t\t\t|- {result}")
        
        # 2.
        print(f"-\t\t - Get Client Businesses from Business DB via Client ID")
        data = (
            client_id
        )
        cursor.execute('SELECT * FROM BUSINESS b WHERE b.client_id = %s', data)
        connections.commit()
        
        result = cursor.fetchall()
        client_business = result
        print(f"-\t\t\t|- Client All Business's: {client_business}")
        print(f"-\t\t\t|- {client_business}")
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        
        print(f"-\t CLEAN UP & LOGGING")
        
        # 1. 
        print(f"-\t\t - Generate Response Object")
        client_business_object_list = []
        for index, business in enumerate(client_business):
            client_business_object_list.append({
                'bus_id': business[0],
                'bus_name': business[1],
                'client_id': business[2]
            })
        
        response = {
            'type': 'success',
            'data': {
                'business': client_business_object_list
            }
        }
        
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
        
    elif method == "GET" and path == "/get-all-customer-info":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Limit(for get-all-customer-info i.e. first 50 all customers, first 100 all customers. Lazy Loading)
        # Payload:
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Search Customer in Customer DB
        print(f"-\t DB PROCEDURE")
        
        # 1. 
        print(f"-\t\t Search Customer in Customer DB")
        if query_param and 'limit' in query_param.keys():
            print(f"-\t\t With limit")
            data = (
                int(query_param['limit'])
            )
            cursor.execute('SELECT * FROM CUSTOMER ORDER BY customer_id LIMIT %s', data)
        else:
            print(f"-\t\t Without limit")
            cursor.execute('SELECT * FROM CUSTOMER')
        connections.commit()
        
        result = cursor.fetchall()
        all_customer_info = list(result)
        print(f"-\t\t\t|- Searched Customer Data: {result}")
        print(f"-\t\t\t|- {result}")
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        print(f"-\t CLEAN UP & LOGGING")
        
        # 1. 
        print(f"-\t\t - Generate Response Object")
        
        all_customer_info_list = []
        for index, customer_row in enumerate(all_customer_info):
            all_customer_info_list.append({
                'customer_id': customer_row[0],
                'client_id': customer_row[1],
                'full_name': customer_row[2],
                'phone_number': customer_row[3],
                'email': customer_row[4],
                'verification': customer_row[5],
                'address': customer_row[6],
                'member_since': customer_row[7],
                'num_referred': customer_row[8],
                'reward_points': customer_row[9],
                'money_spent': customer_row[10],
            })
        
        response = {
            'type': 'success',
            'data': {
                'customer': all_customer_info_list
            }
        }
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
    
    elif method == "GET" and path == "/get-all-card-info":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Limit(for get-all-card-info i.e. first 50 all cards, first 100 all cards. Lazy Loading)
        # Payload:
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Search Card in Card DB
        print(f"-\t DB PROCEDURE")
        
        # 1. 
        print(f"-\t\t Search Card in Card DB")
        if query_param and 'limit' in query_param.keys():
            print(f"-\t\t With limit")
            data = (
                int(query_param['limit'])
            )
            cursor.execute('SELECT * FROM CARD ORDER BY card_id LIMIT %s', data)
        else:
            print(f"-\t\t Without limit")
            cursor.execute('SELECT * FROM CARD')
        connections.commit()
        
        result = cursor.fetchall()
        all_card_info = list(result)
        print(f"-\t\t\t|- Searched Card Data: {result}")
        print(f"-\t\t\t|- {result}")
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        print(f"-\t CLEAN UP & LOGGING")
        
        # 1. 
        print(f"-\t\t - Generate Response Object")
        
        all_card_info_list = []
        for index, card_row in enumerate(all_card_info):
            all_card_info_list.append({
                'card_id': card_row[0],
                'client_id': card_row[1],
                'security_code': card_row[2],
                'status': card_row[3],
                'customer_id': card_row[4],
                'card_type': card_row[5],
                'origin': card_row[6]
            })
        
        response = {
            'type': 'success',
            'data': {
                'card': all_card_info_list
            }
        }
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
    
    elif method == "GET" and path == "/get-all-promo-info":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Limit(for get-all-promo-info i.e. first 50 all promos, first 100 all promos. Lazy Loading)
        # Payload:
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Search Promo in Promo DB
        print(f"-\t DB PROCEDURE")
        
        # 1. 
        print(f"-\t\t Search Promo in Promo DB")
        if query_param and 'limit' in query_param.keys():
            print(f"-\t\t With limit")
            data = (
                int(query_param['limit'])
            )
            cursor.execute('SELECT * FROM PROMO ORDER BY promo_id LIMIT %s', data)
        else:
            print(f"-\t\t Without limit")
            cursor.execute('SELECT * FROM PROMO')
        connections.commit()
        
        result = cursor.fetchall()
        all_promo_info = list(result)
        print(f"-\t\t\t|- Searched Promo Data: {result}")
        print(f"-\t\t\t|- {result}")
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        print(f"-\t CLEAN UP & LOGGING")
        
        # 1. 
        print(f"-\t\t - Generate Response Object")
        
        all_promo_info_list = []
        for index, promo_row in enumerate(all_promo_info):
            all_promo_info_list.append({
                'promo_id': promo_row[0],
                'client_id': promo_row[1],
                'bus_id': promo_row[2],
                'card_id': promo_row[3],
                'event_promo': promo_row[4],
                'gold_promo': promo_row[5],
                'platinum_promo': promo_row[6],
                'titanium_promo': promo_row[7],
                'custom_promo': promo_row[8],
                'date_valid_from': promo_row[9],
                'date_valid_to': promo_row[10],
                'custom_promo_validity': promo_row[11]
            })
        
        response = {
            'type': 'success',
            'data': {
                'promo': all_promo_info_list
            }
        }
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
        
    elif method == "GET" and path == "/get-all-scan-info":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Limit(for get-all-scan-info i.e. first 50 all scans, first 100 all scans. Lazy Loading)
        # Payload:
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Search Scan in Scan DB
        print(f"-\t DB PROCEDURE")
        
        # 1. 
        print(f"-\t\t Search Scan in Scan DB")
        if query_param and 'limit' in query_param.keys():
            print(f"-\t\t With limit")
            data = (
                int(query_param['limit'])
            )
            cursor.execute('SELECT * FROM SCAN ORDER BY scan_id LIMIT %s', data)
        else:
            print(f"-\t\t Without limit")
            cursor.execute('SELECT * FROM SCAN')
        connections.commit()
        
        result = cursor.fetchall()
        all_scan_info = list(result)
        print(f"-\t\t\t|- Searched Scan Data: {result}")
        print(f"-\t\t\t|- {result}")
        
        # ------------------
        # CLEAN UP & LOGGING
        # ------------------
        # 1. Generate Response Object
        print(f"-\t CLEAN UP & LOGGING")
        
        # 1. 
        print(f"-\t\t - Generate Response Object")
        
        all_scan_info_list = []
        for index, scan_row in enumerate(all_scan_info):
            all_scan_info_list.append({
                'scan_id': scan_row[0],
                'scan_time': scan_row[1],
                'scan_type': scan_row[2],
                'client_id': scan_row[3],
                'bus_id': scan_row[4],
                'customer_id': scan_row[5],
                'card_id': scan_row[6],
                'promo_id': scan_row[7]
            })
        
        response = {
            'type': 'success',
            'data': {
                'scan': all_scan_info_list
            }
        }
        print(f"-\t\t\t|- Response Object: {response}")
        print(f"-\t done")
    
    # ----
    # TODO
    # ----
    elif method == "POST" and path == "/signup-referral":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: POST
        # Query Param: 
        # Payload: Customer Data
        print(f"-\t Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Get Client ID & Card Type of referring customer
        # 2. Add Customer(with mailing address) to Customer DB
        # 3. Get Card ID for new customer(last uninitialized/unpopulated/unassigned-to-customer) row in Card ID
        # 4. Add Card with Customer ID(F key) & Same Client ID(F key) as the referring customer to Card DB
        # 5. Increment Referring Customer ‘# referred’ in Customer DB
        # 6. Append to Customer Activity/History DB
        print(f"-\t DB PROCEDURE")
        
        # 1.
        print(f"-\t\t - Get Client ID & Card Type of referring customer")
        data = (
            body["card"]["card_id"]
        )
        referring_customer_card_id = body["card"]["card_id"]
        cursor.execute("SELECT * from CARD c where c.card_id = %s", data)
        connections.commit()
        
        result = cursor.fetchall() # returns tuple of tuples(table rows)
        referring_customer_client_id = result[0][1] # 1st row, 1st column(card_id) 2nd column(client_id)
        referring_customer_customer_id = result[0][4]
        referring_customer_card_type = result[0][5]
        print(f"-\t\t\t|- Referring Customer customer_id: {referring_customer_card_id}, client_id: {referring_customer_client_id}, card_type: {referring_customer_card_type}")
        print(f"-\t\t\t|- {result}")
        
        # 2.
        print(f"-\t\t - Add Customer(with mailing address) to Customer DB")
        
        data = (
            "NULL", # customer_id is auto incremented
            referring_customer_client_id,
            body["customer"]["first_name"], 
            body["customer"]["middle_name"], 
            body["customer"]["last_name"], 
            body["customer"]["phone_number"], 
            body["customer"]["email"], 
            0,  # verification will be updated when applicable
            body["customer"]["address"], 
            0,  # num_referred will be incremented when applicable
            0   # reward points will be incremented when applicable
        )
        cursor.execute('INSERT INTO CUSTOMER VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', data)
        cursor.execute('SELECT LAST_INSERT_ID()') # Returns ID of last insertion
        connections.commit()
        
        result = cursor.fetchall()
        new_customer_customer_id = result[0][0]
        print(f"-\t\t\t|- New Customer customer_id: {new_customer_customer_id}")
        print(f"-\t\t\t|- {result}")
        
        # 3. 
        print(f"-\t\t - Get Card ID for new customer(last uninitialized/unpopulated/unassigned-to-customer) row in Card ID")
        
        # Titanium card referrals get titanium card. Event, Gold & Platinum card referrals get Gold card
        if referring_customer_card_type == 'TITANIUM':
            new_customer_card_type = 'TITANIUM'
        else:
            new_customer_card_type = 'GOLD'
        
        data = (
            new_customer_card_type
        )
        cursor.execute('SELECT * from CARD c WHERE c.card_type = %s AND c.status = 0 LIMIT 1;', data)
        connections.commit()
        
        result = cursor.fetchall()
        new_customer_card_id = result[0][0]
        print(f"-\t\t\t|- New Customer card_id: {new_customer_card_id}")
        print(f"-\t\t\t|- {result}")
        
        # 4.
        print(f"-\t\t - Add Card with Customer ID(F key) to Card DB")
        
        data = (
            referring_customer_client_id,
            1,
            new_customer_customer_id,
            "REFERRAL",
            new_customer_card_id
        )
        cursor.execute('UPDATE CARD c SET c.client_id = %s, c.status = %s, c.customer_id = %s, c.origin = %s WHERE c.card_id = %s;', data)
        cursor.execute('SELECT * FROM CARD c WHERE c.card_id = %s', (new_customer_card_id,))
        connections.commit()
        
        result = cursor.fetchall()
        new_customer_card_id = result[0][0] # new card_id
        print(f"-\t\t\t|- New Customer card_id: {new_customer_card_id}")
        print(f"-\t\t\t|- {result}")
        
        # 5.
        print(f"-\t\t - Increment Referring Customer ‘# referred’ in Customer DB")
        
        data = (
            1,
            referring_customer_customer_id
        )
        cursor.execute('UPDATE CUSTOMER c SET c.num_referred = c.num_referred + %s WHERE c.customer_id = %s;', data)
        cursor.execute('SELECT * FROM CUSTOMER c WHERE c.customer_id = %s;', (referring_customer_customer_id,))
        connections.commit()
        
        result = cursor.fetchall()
        referring_customer_customer_id = result[0][0]
        referring_customer_num_referred = result[0][9]
        print(f"-\t\t\t|- Referring Customer customer_id: {referring_customer_customer_id}, num_referred: {referring_customer_num_referred}")
        print(f"-\t\t\t|- {result}")
        
        # 6.
        print(f"-\t\t - Append to Customer Activity/History DB")
        
        # Format: {"description": "", "card_id": "", "scan_id": "", "date_time": "", "details": ""}
        # customer_activity_table.put_item(
        #     Item = {
        #         'customer_id' : new_customer_customer_id,
        #         'activity_log': {"description": "New Card Assigned By Referral", "card_id": {new_customer_card_id}, "scan_id": "NULL", "date_time": "2022-11-22 13:00:00", "details": "Origin": "REFERRAL"}
        #     }
        # )
        
        # customer_activity_table.put_item(
        #     Item = {
        #         'customer_id' : referring_customer_customer_id,
        #         'activity_log': {"description": "Referred User Signed Up", "card_id": {referring_customer_card_id}, "scan_id": "NULL", "date_time": "2022-11-22 13:00:00", "details": "Origin": {new_customer_customer_id}}
        #     }
        # )
        print(f"-\t done")
        
    elif method == "POST" and path == "/update-customer-info":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: POST
        # Query Param: 
        # Payload: Customer ID, Customer Data
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Update Customer in Customer DB
        # 2. Append to Customer Activity/History DB
        print(f"-\t DB PROCEDURE")
        
        # 1.
        print(f"-\t\t Update Customer in Customer DB")
        data = (
            body["customer"]["first_name"], 
            body["customer"]["middle_name"], 
            body["customer"]["last_name"], 
            body["customer"]["phone_number"], 
            body["customer"]["email"], 
            body["customer"]["verification"], 
            body["customer"]["address"], 
            body["customer"]["num_referred"], 
            body["customer"]["reward_points"], 
        )
        cursor.execute('UPDATE CUSTOMER c SET c.first_name = %s, c.middle_name = %s, c.last_name = %s, c.phone_number = %s, c.email = %s, c.verification = %s, c.address = %s, c.num_referred = %s, c.reward_points = %s', data)
        cursor.execute('SELECT * FROM CUSTOMER c WHERE c.customer_id = %s', (body["customer"]["customer_id"],))
        connections.commit()
        
        result = cursor.fetchall()
        print(f"-\t\t\t|- Updated Customer ID: {result[0][0]}")
        print(f"-\t\t\t|- {result}")
        
    elif method == "GET" and path == "/get-customer-offers":
        # ------------
        # API ENDPOINT
        # ------------
        # Request Type: GET
        # Query Param: Card ID, Client ID & Business ID
        # Payload:
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        # 1. Search Customer Custom Promo in Promo DB
        # 2. Search All Promos in Promo DB
        
        # 1.
        print(f"-\t\t Search Customer Custom Promo in Promo DB")
        data = (
            query_param['client_id'],
            query_param['bus_id'],
            query_param['card_id']
        )
        
        cursor.execute('SELECT * FROM PROMO p WHERE p.client_id = %s AND p.bus_id = %s AND p.card_id = %s ORDER BY p.date_created', data)
        connections.commit()
        
        result = cursor.fetchall()
        custom_promo = result
        print(f"-\t\t\t|- Customer Custom Promo's: {custom_promo}")
        print(f"-\t\t\t|- {custom_promo}")
        
        # 3.
        print(f"-\t\t Search All Promos in Promo DB")
        if query_param['bus_id'] == 0: # custom offer is not business specific, offer valid at all businesses under client
            data = (
                query_param['client_id'],
                query_param['card_id']
            )
            query = 'SELECT * FROM PROMO p WHERE p.client_id = %s AND p.card_id = %s ORDER BY p.date_created'
        else:
            data = (
                query_param['client_id'],
                query_param['bus_id'],
                query_param['card_id']
            )
            query = 'SELECT * FROM PROMO p WHERE p.client_id = %s AND p.bus_id = %s AND p.card_id = %s ORDER BY p.date_created'
            
        cursor.execute(query, data)
        connections.commit()
        
        result = cursor.fetchall()
        all_promo = result
        print(f"-\t\t\t|- Customer All Promo's: {all_promo}")
        print(f"-\t\t\t|- {all_promo}")
        
        response = {'data' : {'promo' : {'custom_promo': custom_promo, 'all_promo': all_promo}}}
        
    elif method == "GET" and path == "/get-customer-referral-link":
        # ------------
        # API ENDPOINT
        # ------------
        
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        
    elif method == "GET" and path == "/get-client-business-logo":
        # ------------
        # API ENDPOINT
        # ------------
        
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        
    elif method == "POST" and path == "/upgrade-customer":
        # ------------
        # API ENDPOINT
        # ------------
        
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
        
    else:
        print(f"-\t Unhandeled {method} {path}")
        response = {
            'type': 'error',
            'data': {}
        }
    
    # Close RDS Connections
    cursor.close()
    # connections.close() # Avoid This
    
    # -----------------------
    # Handle Request Response
    # -----------------------
    api_response = generate_api_response(200)
    return api_response