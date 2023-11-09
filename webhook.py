from flask import Flask, request, jsonify
import requests
import re

#Global variables 

fco_api_base_url = 'https://www.gov.uk/api/content/foreign-travel-advice/{}/entry-requirements'
fco_api_response = ' '
entity_names = []
previous_message_entity = ' '
geo_country = None 
geo_country_str = ' '
geo_country_from_prior_question = ' '
supported_countries = ['Australia', 'Russia']
message_count = 0
user_question = ' '
user_response = ' '
message_count = 0

app = Flask(__name__)
latest_entity_name = ""




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
    input_to_deepai = f"Provide a detailed answer to this question, from the perspective of British citizens: '{user_question}'. Base your answer on this information: '{scraped_text}'."
    response = requests.post(
        "https://api.deepai.org/api/text-generator",
        data={'text': input_to_deepai},
        headers={'api-key': '7feaf274-c450-40a1-8f90-552928bd1cd0'}  # Replace with your actual API key
    )
    if response.status_code != 200:
        print(response.status_code)
        return "Sorry, I couldn't fetch the required information."
    return f"Based on our research, {response.json().get('output')}"

# Webscrape function
def scraper(api_specific_url, entity_names): 

    
    try:
        response_API = requests.get(api_specific_url)
        response_API.raise_for_status()
        data = response_API.json()

        html_content = ''
        for item in data.get("details", {}).get("parts", []):
            if item.get('slug') == 'entry-requirements':
                html_content = item.get('body', '')
                break

        if not entity_names:  # if no entity was detected in follow-up
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
                    print(clean_content)
                    break
                

    except requests.RequestException as e:
        print(e)
        user_response = "Sorry, I couldn't fetch the required information."
    return clean_content
                

    


# Note: You would call this function from within your Flask route handler and handle the response accordingly.


# The rest of your code...


#Main code for webhook
@app.route('/webhook', methods = ['POST', 'GET'])
def webhook():

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

    user_response = ' '

    #Retrieve data from Dialogflow payload 

    dialogflow_data = request.get_json()

    # Retrieve intent name and parameters from dialogflow payload 
    intent_name = dialogflow_data['queryResult']['intent']['displayName']
    parameters = {key: value for key, value in dialogflow_data['queryResult']['parameters'].items() if value}
    entity_names, geo_country = extract_entities_from_payload(dialogflow_data)
    print('Test Details: ')
    print(' ')
    print('1.) Intent Name: ', intent_name)
    print('2.) Parameters: ', parameters)
    
    #Check if this is first message sent by user 
    if message_count == 0: 
        user_response += 'Hello! '
    else: 
        user_response = ' '

    message_count += 1
    print('3.) Total messages: ', message_count)

    #Extract user question from payload
    user_question = dialogflow_data['queryResult']['queryText']
    print('4.) User Question: ', user_question)

    #Construct API URL for initial and non-follow up questions 
    if intent_name != 'follow-up': 
        print("5.) Country: ", geo_country, "Country from prior question ", geo_country_from_prior_question )
        print('6.) Entity names:', entity_names)

    #Construct API URL for follow-up questions
    if intent_name == 'follow-up': 
        if not geo_country:
            geo_country = geo_country_from_prior_question
            print('5.) No new geo-country. Using country from before instead:', geo_country)
        else: 
            print('5.) Geo-country: ', geo_country)

        for param_name, param_value in parameters.items():
                if param_name in entity_names and param_name != 'geo-country' and param_value != ' ': 
                    print(f"6.) Entity {param_name} in follow-up question matches entity in initial question")
                if param_name not in entity_names and param_name != 'geo-country' and param_value != ' ':
                    entity_names.append(param_name)
                    print(f"6.) Entity {param_value} in follow-up entity does NOT match entities in initial question")

    #Retrieve data from FCO API 
    for country in format_geo_country(geo_country):
        for entity in entity_names:
            print('Entity: ', entity)
            api_specific_url = fco_api_base_url.format(country)
            scraper_response = scraper(api_specific_url, [entity])
            fco_api_response += country + ':' + '\n ' + scraper_response + '\n' + '\n'
        print('7.) API specific URL: ', api_specific_url)

    print('8.) FCO API Response:')
    print(' ')
    print(fco_api_response)

    #Send user question and FCO API response to DeepAI 

    user_response += dynamic_text_generator(user_question, fco_api_response)
    print('9.) Webhook Response: ')
    print(' ')
    print(user_response)

    geo_country_from_prior_question = geo_country

    return jsonify({
        "fulfillmentText": user_response
        })

if __name__ == '__main__':
    app.run(debug=True)

