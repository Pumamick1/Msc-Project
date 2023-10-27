from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)
latest_message = ""

def dynamic_text_generator(user_question, scraped_text):
    # Format the input to DeepAI
    input_to_deepai = f"Rephrase this text: {scraped_text} so that it answers this question: {scraped_text}. Your answer must include all the information from the text"

    response = requests.post(
        "https://api.deepai.org/api/text-generator",
        data={'text': input_to_deepai},
        headers={'api-key': '7feaf274-c450-40a1-8f90-552928bd1cd0'}
    )

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return "Sorry, I couldn't fetch the required information."

    # Extracting the output from DeepAI's response
    return response.json().get('output')


def extract_entities_from_payload(payload):
    # Extract the parameters (entities) from the payload
    parameters = payload.get("queryResult", {}).get("parameters", {})
    
    # Find the entities that have values and store their names as strings, excluding 'geo-country'
    entity_names = [name for name, value in parameters.items() if value and name != 'geo-country']

    return entity_names

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Webhook is up and running!"  # simple response for GET

    # Default value for user_response
    user_response = "Sorry, I couldn't fetch the required information."

    data = request.get_json()
    api_base_url = 'https://www.gov.uk/api/content/foreign-travel-advice/{}/entry-requirements'
    geo_country = data['queryResult']['parameters']['geo-country']
    user_question = data["queryResult"]["queryText"]
    api_specific_url = api_base_url.format(geo_country.lower())

    entity_names = extract_entities_from_payload(data)

    try:
        response_API = requests.get(api_specific_url)
        response_API.raise_for_status()  # raises an exception for HTTP error codes
        data = response_API.json()

        html_content = ''
        for item in data.get("details", {}).get("parts", []):
            if item.get('slug') == 'entry-requirements':
                html_content = item.get('body', '')
                break

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
        # Handle any request errors here (e.g., network issues, invalid URL, etc.)
        print("Error fetching data from API")

    return jsonify({"fulfillmentText": user_response})



if __name__ == '__main__':
    app.run(debug=True)














 




