#from flask import Flask, request, jsonify #, Response
import requests
import re
#from google.oauth2 import service_account
from google.cloud import dialogflow
#from twilio.twiml.messaging_response import MessagingResponse
#from twilio.rest import Client
import os
#from http.client import responses
from openai import OpenAI

os.environ['OPENAI_API_KEY'] = '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'
client = OpenAI()


def detect_intent_texts(project_id, session_id, texts, language_code):
    """Returns the result of detect intent with texts as inputs.

    Using the same `session_id` between requests allows continuation
    of the conversation."""

    session_client = dialogflow.SessionsClient()

    session = session_client.session_path(project_id, session_id)
    print("Session path: {}\n".format(session))

   
    text_input = dialogflow.TextInput(text=texts, language_code=language_code)

    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )

    #print('TYPE!!!!!', type(response))        
    #print("Detected intent: ", response.query_result.intent.display_name)
    #print("Detected country: ", response.query_result.parameters)
    
    return response
        


def format_geo_country(geo_country):
    
    if isinstance(geo_country, list):
        
        return [country.lower() for country in geo_country]
    else:
        
        return [geo_country.lower()]

def extract_entities_from_payload(payload):
    global latest_entity_name

    parameters = payload.get("queryResult", {}).get("parameters", {})
    geo_country = parameters.get("geo-country", [])

    entity_names = [name for name, value in parameters.items() if value and name != 'geo-country']

    if not entity_names and latest_entity_name:
        entity_names = [latest_entity_name]
    elif entity_names:
        latest_entity_name = entity_names[0]

    return entity_names, geo_country


#Dynamically produce user response
def dynamic_text_generator(user_question, scraped_text):

    prompt = f"Answer this question \"{user_question}\" Use the following information to provide a concise answer: \"{scraped_text}\""

    client = OpenAI()
   
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a Consular Assistance Chatbot. You provide Consualar support to British nationals"},
            {"role": "user", "content": prompt}
        ]
        )
    
    generated_text = completion.choices[0].message.content 
    response = str(generated_text)
    
    return response

# Webscrape function
def scraper(api_specific_url, entity_names, user_question): 

    
    try:
        response_API = requests.get(api_specific_url)
        response_API.raise_for_status()
        data = response_API.json()

        html_content = ''
        for item in data.get("details", {}).get("parts", []):
            if item.get('slug') == 'entry-requirements':
                html_content = item.get('body', '')
                break

        if not entity_names:  
            #print("there are no entities in this list")
            clean_content = re.sub('<[^>]+>', '', html_content)  # clean the entire content
            user_response = dynamic_text_generator(user_question, clean_content)
        else:
            tags_to_search = ['h2', 'h3']
            clean_content = "Section not found"
            for tag in tags_to_search:
                start_keyword = f'<{tag} id="{entity_names[0]}">'
                end_keyword = f'<{tag}'
                start_pos = html_content.find(start_keyword)

                if start_pos != -1:
                    end_pos = html_content.find(end_keyword, start_pos + len(start_keyword))
                    if end_pos == -1:
                        end_pos = len(html_content)
                    section_content = html_content[start_pos:end_pos].strip()
                    clean_content = re.sub('<[^>]+>', '', section_content)
                    #print(clean_content)
                    break
                

    except requests.RequestException as e:
        print(e)
        user_response = "Sorry, I couldn't fetch the required information."
   # print("Cleaned Content:",clean_content)
    return clean_content