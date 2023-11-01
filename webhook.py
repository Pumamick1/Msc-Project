from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)
latest_entity_name = ""

def dynamic_text_generator(user_question, scraped_text):
    input_to_deepai = f"Answer this question: '{user_question}' using this information: '{scraped_text}'."
    response = requests.post(
        "https://api.deepai.org/api/text-generator",
        data={'text': input_to_deepai},
        headers={'api-key': '7feaf274-c450-40a1-8f90-552928bd1cd0'}
    )
    if response.status_code != 200:
        return "Sorry, I couldn't fetch the required information."
    return f"Based on our research, {response.json().get('output')}"

def extract_active_contexts(payload):
    return payload.get("queryResult", {}).get("outputContexts", [])

def extract_entities_from_payload(payload):
    global latest_entity_name  # Use the global variable

    parameters = payload.get("queryResult", {}).get("parameters", {})
    geo_country = parameters.get("geo-country", "")
    
    geo_country = parameters.get("geo-country", "")
    if isinstance(geo_country, list) and geo_country:
        geo_country = geo_country[0]

    if not geo_country:
        active_contexts = extract_active_contexts(payload)
        for context in active_contexts:
            if 'geo-country' in context['parameters']:
                geo_country = context['parameters']['geo-country']
                if geo_country:
                    break


    entity_names = [name for name, value in parameters.items() if value and name != 'geo-country']

    # If no entity name is recognized in the current request, use the latest recognized entity name
    if not entity_names and latest_entity_name:
        entity_names = [latest_entity_name]
    elif entity_names:
        latest_entity_name = entity_names[0]  # Update the global variable if an entity is recognized

    return entity_names, geo_country

def is_supported_input(data):
    geo_country = data["queryResult"]["parameters"].get("geo-country", "")
    if isinstance(geo_country, list) and geo_country:
        geo_country = geo_country[0]
    geo_country = geo_country.lower()

    supported_countries = ["australia", "russia"]
    if geo_country not in supported_countries:
        return False, "Sorry, I currently support information only for Australia and Russia."
    return True, ""

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Webhook is up and running!"

    data = request.get_json()
    api_base_url = 'https://www.gov.uk/api/content/foreign-travel-advice/{}/entry-requirements'

    supported, message = is_supported_input(data)
    if not supported:
        return jsonify({"fulfillmentText": message})

    entity_names, geo_country = extract_entities_from_payload(data)
    user_question = data["queryResult"]["queryText"]
    api_specific_url = api_base_url.format(geo_country.lower())
    print(entity_names)

    if not geo_country:
        return jsonify({"fulfillmentText": "Sorry, I couldn't identify the country."})

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
                    user_response = dynamic_text_generator(user_question, clean_content)
                    break

    except requests.RequestException:
        user_response = "Sorry, I couldn't fetch the required information."

    return jsonify({"fulfillmentText": user_response})

if __name__ == '__main__':
    app.run(debug=True)

