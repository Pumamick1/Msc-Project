from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)
latest_message = ""

def extract_entities_from_payload(payload):
    # Extract the parameters (entities) from the payload
    parameters = payload.get("queryResult", {}).get("parameters", {})
    
    # Find the entities that have values and store their names as strings, excluding 'geo-country'
    entity_names = [name for name, value in parameters.items() if value and name != 'geo-country']

    return entity_names



@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    global latest_message

    # If the request method is POST, then it's coming from Dialogflow
    if request.method == 'POST': 
        data = request.get_json()
        api_base_url = 'https://www.gov.uk/api/content/foreign-travel-advice/{}/entry-requirements'
        geo_country = data['queryResult']['parameters']['geo-country'] # Country the user is enquiring about
        api_specific_url = api_base_url.format(geo_country.lower())
    
        
        #Fetch entity names from payload 
        entity_names = extract_entities_from_payload(data)
        entity_keyword = entity_names[0]
        print(entity_names[0])


        # Fetching data from the UK foreign office API
        response_API = requests.get(api_specific_url)
        data = response_API.json()
        desired_slug = 'entry-requirements'
        html_content = ''
        for item in data.get("details", {}).get("parts", []):
            if item.get('slug') == desired_slug:    
                html_content = item.get('body', '')
                break

     #Search HTML file for ID tags that match parsed entity. 
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
                break  # Break the loop once a match is found

        # Return the clean content as the response to Dialogflow
        return jsonify({"fulfillmentText": clean_content})

# If the request is not from Dialogflow, return the latest message
    return jsonify({"latest_message": latest_message})

if __name__ == '__main__':
    app.run(debug=True)














 




