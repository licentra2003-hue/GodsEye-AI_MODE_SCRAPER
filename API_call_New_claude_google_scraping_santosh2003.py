import json

import requests

# Define the API endpoint and payload
url = "http://127.0.0.1:8000/scrape"

# What are the best transdermal vitamin patches for people who dislike swallowing pills?
# anti hairfall shampoo recommendation
# virtual hairstyle changer app
# Mobile Measurement Partner recommendations for app developers struggling with inefficient marketing spend?
# What are the best Mobile Measurement Partner solutions for mobile marketers to improve attribution accuracy?
payload = {"query": "What are the best transdermal vitamin patches for people who dislike swallowing pills?","location": "India","keep_page_open": True, "max_retries": 3}
output_filename = "final_output.json"

try:
    # Make the POST request
    response = requests.post(url, json=payload)
    
    # Raise an exception if the request returned an unsuccessful status code (e.g., 404, 500)
    response.raise_for_status() 
    
    # Parse the JSON response from the server
    data = response.json()
    
    # Write the parsed JSON data to the output file
    # 'w' mode overwrites the file if it already exists
    # indent=4 makes the JSON file human-readable (pretty-printed)
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully saved response to {output_filename}")

except requests.exceptions.ConnectionError as conn_err:
    print(f"Connection Error: Failed to connect to {url}.")
    print("Please ensure your local server is running.")
except requests.exceptions.HTTPError as http_err:
    print(f"HTTP Error: {http_err}")
    print(f"Response content: {response.text}")
except requests.exceptions.JSONDecodeError:
    print(f"JSON Decode Error: The server did not return valid JSON.")
    print(f"Response content: {response.text}")
except Exception as err:
    print(f"An unexpected error occurred: {err}")