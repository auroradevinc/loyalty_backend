import os
import json
import pymysql
import boto3
from ndicts.ndicts import NestedDict

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

def extract_req_info(event):
    print("* EXTRACTING REQUEST INFORMATION")
    
    global path, query_param, body, method, response
    
    # Assign Req params
    path        = event["rawPath"] if event["rawPath"] != "" else None
    # body        = json.loads(event["body"]) if "body" in event.keys() else None
    
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # ONLY FOR LAMBDA TESTING, REMOVE AFTER, USE THE ONE ABOVE
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    body        = event["body"] if "body" in event.keys() else None
    
    method      = NestedDict(event)["requestContext","http","method"]
    query_param = event["queryStringParameters"] if "queryStringParameters" in event.keys() else None
    
    print(f"-\t Event: {event}")
    # print(json.dumps(event, sort_keys=True, indent=4))
    print(f"-\t Method {method}, Path {path}, QueryString {query_param}")
    print(f"-\t Body: {body}")
    
    reponse = {'data': {'method': method, 'path': path, 'query_param': query_param, 'body': body}}

def lambda_handler(event, context):
    
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
    if method == "POST" and path == "/signup":
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
        # 4. Append to Customer Activity/History DB
        print(f"-\t DB PROCEDURE")
        
        # 1.
        print(f"-\t\t - Get Client ID from Card ID")
        data = (
            body["card"]["card_id"]
        )
        new_customer_card_id = body["card"]["card_id"]
        cursor.execute("SELECT * from CARD c where c.card_id = %s", data)
        connections.commit()
        
        result = cursor.fetchall() # returns tuple of tuples(table rows)
        new_customer_client_id = result[0][1] # 1st row, 1st column(card_id) 2nd column(client_id)
        print(f"-\t\t\t|- New Customer client_id: {new_customer_client_id}")
        print(f"-\t\t\t|- {result}")
        
        # 2.
        print(f"-\t\t - Add Customer(with or without mailing address) to Customer DB")
        
        data = (
            "NULL", # customer_id is auto incremented
            new_customer_client_id,
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
        print(f"-\t\t - Add Card with Customer ID(F key) to Card DB")
        
        data = (
            new_customer_customer_id,
            new_customer_card_id
        )
        cursor.execute('UPDATE CARD c SET c.customer_id = %s WHERE c.card_id = %s', data)
        connections.commit()
        print(f"-\t\t\t|- New Customer card_id: {new_customer_card_id}")
        print(f"-\t\t\t|- {result}")
        
        # 4.
        print(f"-\t\t - Append to Customer Activity/History DB")
        
        # Format: {"description": "", "card_id": "", "scan_id": "", "date_time": "", "details": ""}
        customer_activity_table.put_item(
            Item = {
                'customer_id' : new_customer_customer_id,
                'activity_log': {"description": "New Card Assigned", "card_id": "1", "scan_id": "NULL", "date_time": "2022-11-22 13:00:00", "details": ""}
            }
        )
        print(f"-\t done")
        
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
        # Get Customer ID from Card ID in Card DB
        # Search Customer in Customer DB
        # 2. By Customer ID
        # Search Customer in Customer DB
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
        cursor.execute('SELECT * FROM CUSTOMER c WHERE c.customer_id = %s;', data)
        connections.commit()
        
        result = cursor.fetchall()
        customer_data = result[0]
        print(f"-\t\t\t|- Searched Customer Data: {customer_data}")
        print(f"-\t\t\t|- {result}")
        
        response = {'data': {'customer_data': customer_data}}
        
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
        print(f"-\t\t\t|- Searched Customer Data: {result}")
        print(f"-\t\t\t|- {result}")
        
        response = {'data' : {'customer_data' : list(result)}}
        
    elif method == "POST" and path == "update-customer-info":
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
        
        
    elif method == "GET" and path == "/get-customer-offers":
        # ------------
        # API ENDPOINT
        # ------------
        
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
    elif method == "GET" and path == "/get-customer-offers":
        # ------------
        # API ENDPOINT
        # ------------
        
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
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
    elif method == "POST" and path == "upgrade-customer":
        # ------------
        # API ENDPOINT
        # ------------
        
        print(f"\t - Handling {method} {path}")
        
        # ------------
        # DB PROCEDURE
        # ------------
    else:
        print("UNHANDELED ROUTE")
    
    # Close RDS Connections
    cursor.close()
    # connections.close() # Avoid This
    
    # -----------------------
    # Handle Request Response
    # -----------------------
    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
