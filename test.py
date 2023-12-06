from openai import OpenAI
import os

os.environ['OPENAI_API_KEY'] = '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'
client = OpenAI()

user_message = "What are the visa requirements for Australia?"

completion = client.chat.completions.create(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "system", "content": "You are a consular assistance chatbot. Your task is to provide travel advice to British citizens."},
    {"role": "user", "content": user_message}
  ]
)

print(completion.choices[0].message)