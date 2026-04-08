# generate_tokens.py
from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.modify'
]

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

# Save calendar token
with open('calendar_token.json', 'w') as f:
    f.write(creds.to_json())

# Same creds work for Gmail too
with open('gmail_token.json', 'w') as f:
    f.write(creds.to_json())

print("Done! calendar_token.json and gmail_token.json created.")