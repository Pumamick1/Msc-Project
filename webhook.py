from flask import Flask, request, jsonify, Response
import requests
import re
from google.oauth2 import service_account
from google.cloud import dialogflow
import json
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
from http.client import responses
import time
import timeit
from functions import scraper, dynamic_text_generator, detect_intent_texts, format_geo_country, extract_entities_from_payload

#Global variables 

access_token = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDMHOpEPbJwuGoyerxNuW7b4WsRtoH40xJ3bVfYVsxFwPWh9ojMyvQO7SAbBbzOrqdejKwFjtoP+VdmWekX0/+ruOkTwOIohCHMzSq/ZPuCvAAOI8OYmqulwTBEJy1xb2ccQf84aXASbQnTwnxrV2vMBoI5wYtMAmIA7/WOngAN+L+TNtgqZqdin4703wPd+/9GfHf97mJ4hhsjbaUxW37fVpbA3J/dxixs5NVY75VMqdqpFydIM38NrsnG/W9G9YrzU+v2XUxS6mIDKRCdJitWRRkh1OSDnbRzyCcBa0pNRIRZl5/PNbLrmWwYO5gMEKVG2nnHvK+ns9iZr7d0ZC2FAgMBAAECggEAES0hvapfeMLcFPFlJTlEjfZTN0NffpvsguZNrSPovrn1MbL4Yht2HEdyGzQJZm8mIHvAAhu6V/vIkhFg3yN08XN3EbV6kqRD3+MoBMEvtRmy+32g+ReS+DjgoeuWFGSmjac0HgApcTOBzzMfmzzZEms9zDRwT24n5yJKTL0ZDhPJHUzuvwkNW8NOmhM5VkyUW9k63rwYIDIGMNMUFN7LwVOnTNgzaEvWmhYuOR7QZHmCkHwXgE8lv8KRrbza331vr7oocdkGj+zRQufanjfxxUfTwQarON1bPFA++8mTZpBv5CrOwddnfJ2M+n8xfOoVGsMg4GBun0QaEJDBtdywhQKBgQD21GCvtxsepSTi+DOTBxqzudn0DIN+ifBI5Ee9JONF8YqXHoKxQibCcrnUCgZt+dZRHMWCdzllGctI43uJdBPIIJDfF7JvV1hdW1smz1UU/ihyLvzlOdf9r+SYRduxwCUL0ETS+sN0Zz2zIyFv+DrZeDVB8zP3zsiKm2QmJ/ifvwKBgQDTskE+gDV3hv+83Z+hme+bpf+lCpQGIRT9s6Wb7JXmwwawd4ekl9nz8AMp0WR29wOr/bx0Sj1ESn3TaD2WVrJzt8y+a/HRkOHZl3WlkJxPPkZ5U2AV9lSt6h2dHvbSnWCHaKiV7sIdpsyhys5+mOQ7RB7mECr/n/ndZYn89ifDuwKBgQCoG28aXdAnp/weZULjATSrcYnC0H8CQLoZOvitFqF/solccRg7170ENBTiGE3WuxC/P6Q5PjAl7lJoex5ZOGh8pcllWANcF5YER0MmhJEC8jLjyaLOD/5ONmyvVOzS+/V/PUKSmt1huyrnhaaxVtPl5xwGpbggL4Kf/ENSRWjsiwKBgFNIoqBrIh3HD5+G9UFHZVuvv9Z3RervYum4nmOsfQDPIzeTntqjHwz4FNaD2WlwHpKwfU6m0lmmkL/2F5youQYLflI/91/CBwhqrM8ZCFWoo2Mh6QBa68+L9mCVCPetEIfVJdXum5G8yG6ycfCeR9QFJb7PB4uPrWZrhxDs6pH3AoGAbIg5tGcBKbZ741giHYc1/51qLrYF5hlAFsldiqU6nc9w/X4FA6l3Nw0MZAbSRSb3BNLvYrjJmQjuSvSuwH+Sdd"
advisories_url = 'https://www.gov.uk/api/content/foreign-travel-advice/{}'
fco_api_base_url = 'https://www.gov.uk/api/content/foreign-travel-advice/{}/{}'
fco_api_response = ' '
prior_intent_name = ' '
entity_names = []
previous_message_entity = ' '
geo_country = None 
geo_country_str = ' '
geo_country_from_prior_question = ' '
supported_countries = ['Australia', 'Russia']
message_count = 0
user_question = ' '
user_response = 'Test'
message_count = 0

os.environ['TWILIO_ACCOUNT_SID'] = 'AC0a931cb7c2d4af86bcb5b0eb730f1c64'
os.environ['TWILIO_AUTH_TOKEN'] = 'f9d9a0748581a84c57fd611c38dbdeca'

app = Flask(__name__)
latest_entity_name = ""

                
#Main code for webhook
@app.route('/webhook', methods = ['POST', 'GET'])
def webhook():

    print("Webhook triggered")

    #Global variables 
    global fco_api_base_url 
    global fco_api_response
    global entity_names
    global previous_message_entity
    global geo_country 
    global geo_country_str
    global geo_country_from_prior_question
    global supported_countries 
    global message_count
    global user_question
    global user_response
    global message_count
    global prior_intent_name

    user_response = ' '

    #Retrieve data from Dialogflow payload and parse intent name, entitiy name and geo country
    dialogflow_data = request.get_json()
    intent_name = dialogflow_data['queryResult']['intent']['displayName']
    parameters = {key: value for key, value in dialogflow_data['queryResult']['parameters'].items() if value}
    entity_names, geo_country = extract_entities_from_payload(dialogflow_data)

    print('Test Details: ')
    print(' ')
    print('1.) Intent Name: ', intent_name)
    
    #Check if this is first message sent by user 
    if message_count == 0: 
        user_response += 'Hello! '
    else: 
        user_response = ' '

    message_count += 1

    #Extract user question from payload
    user_question = dialogflow_data['queryResult']['queryText']
   # print('4.) User Question: ', user_question)

    #Construct API URL for initial and non-follow up questions 
    if intent_name != 'follow-up': 
        print('2.) Entities:', entity_names)
        print("3.) Geo-country: ", geo_country)
        

    #Construct API URL for follow-up questions
    if intent_name == 'follow-up': 
        if not geo_country:
            geo_country = geo_country_from_prior_question
            print('5.) No new geo-country. Using country from before instead:', geo_country)
        
        for param_name, param_value in parameters.items():
                if param_name in entity_names and param_name != 'geo-country' and param_value != ' ': 
                    print(f"6.) Entity {param_name} in follow-up question matches entity in initial question")
                if param_name not in entity_names and param_name != 'geo-country' and param_value != ' ':
                    entity_names.append(param_name)
                    print(f"6.) Entity {param_value} in follow-up entity does NOT match entities in initial question")

        api_specific_url = fco_api_base_url.format(geo_country, prior_intent_name)

    #Retrieve data from FCO API 

    if intent_name == 'travel-advisories':
        for country in format_geo_country(geo_country):
            #print(advisories_url)
            #print(geo_country, type(geo_country))
           #print(advisories_url.format(geo_country))
            api_specific_url = advisories_url.format(geo_country.lower())

            response_API = requests.get(api_specific_url)
            response_API.raise_for_status()
            fco_api_response = response_API.json()
            
    elif intent_name != 'follow-up':

        prior_intent_name = intent_name

        for country in format_geo_country(geo_country):
            for entity in entity_names:
                #print('Entity: ', entity)
                api_specific_url = fco_api_base_url.format(country, intent_name)
                scraper_response = scraper(api_specific_url, [entity], user_question)
                fco_api_response += country + ':' + '\n ' + scraper_response + '\n' + '\n'

    #Send user question and FCO API response to DeepAI 
   # print("FCO API RESPONSE: ", fco_api_response)
    print("4.) URL: ", api_specific_url)
    print("hi!")
    user_response = dynamic_text_generator(user_question, fco_api_response)
    geo_country_from_prior_question = geo_country
    
    return jsonify({
        "fulfillmentText": user_response
       })     

@app.route('/whatsapp', methods =['GET', 'POST'])
def whatsapp():

    start_time = time.time()
    project_id = 'consularassistanceagent-yxuj'
    session_id = 'test'
    language_code = "en-US"
    incoming_message = request.form.get('Body', '')

    intent = detect_intent_texts(project_id, session_id, incoming_message, language_code)
    time.sleep(6)

    #account_sid = os.environ['TWILIO_ACCOUNT_SID'] DELETE
    #auth_token = os.environ['TWILIO_AUTH_TOKEN'] DELETE
    #client = Client(account_sid, auth_token) DELETE
    #test = 'test' DELETE

    response = MessagingResponse()
    response.message(user_response)
    end_time = time.time()
    runtime = end_time - start_time
   # print("6.) Runtime: ", runtime)
    print("7.) User Response: ", user_response)
    return Response(str(response), mimetype="application/xml")

    


if __name__ == '__main__':
    app.run(debug=False)

