from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)
latest_message = ""

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    global latest_message

    # If the request method is POST, then it's coming from Dialogflow
    if request.method == 'POST': 
        data = request.get_json()
        api_base_url = 'https://www.gov.uk/api/content/foreign-travel-advice/{}/entry-requirements'
        geo_country = data['queryResult']['parameters']['geo-country'] # Country the user is enquiring about
        api_specific_url = api_base_url.format(geo_country.lower())
        
        print(data) 

        # Fetching data from the UK foreign office API
        response_API = requests.get(api_specific_url)
        data = response_API.json()
        desired_slug = 'entry-requirements'
        html_content = ''
        for item in data.get("details", {}).get("parts", []):
            if item.get('slug') == desired_slug:    
                html_content = item.get('body', '')
                break

    #!!!!!!! MATCH DIALOGFLOW ENTITY WITH H-TAG IDs IN A DICT, THEN APPEND TO START KEYWORD!!!!!!!!!!!!!!!!!!
        start_keyword = '<h3 id="working-holiday-visa">Working holiday visa</h3>'
        end_keyword = '<h3'
        start_pos = html_content.find(start_keyword)
        if start_pos != -1:
            end_pos = html_content.find(end_keyword, start_pos + len(start_keyword))
            if end_pos == -1:
                end_pos = len(html_content)
            section_content = html_content[start_pos:end_pos].strip()
            clean_content = re.sub('<[^>]+>', '', section_content)
        else: 
            clean_content = "Section not found"

        # Return the clean content as the response to Dialogflow
        return jsonify({"fulfillmentText": clean_content})

# If the request is not from Dialogflow, return the latest message
    return jsonify({"latest_message": latest_message})

if __name__ == '__main__':
    app.run(debug=True)














 




