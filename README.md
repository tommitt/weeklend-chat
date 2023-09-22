# Weeklend Chat
⚡ The AI for your free time ⚡

## 🤔 What is it?
Weeklend is a chatbot that operates on WhatsApp to provide recommendations on events, activities, bars, restaurants or places to go.

## 🔧 How is the repo structured?

### Chatbot

**🪝 WhatsApp Webhook**

A webhook communicates with the WhatsApp Cloud API for receiving messages from the users and sending the appropriate answers back to them.

*Main dependencies:* [fastapi](https://github.com/tiangolo/fastapi)

**🤖 LLM**

When a message is received, an LLM is used for:
* Extracting macro information from the message, e.g., whether the message is valid or not, if it refers to a specific date or range of dates, which are used for filtering the events;
* Generating the answer using the most relevant events retrieved from the vectorstore as context.

*Main dependencies:* [langchain](https://github.com/langchain-ai/langchain), [openai](https://github.com/openai/openai-python)

**💾 SQL database**

A SQL database is used for storing **users**, **conversations** and **events** information.

*Main dependencies:* [sqlalchemy](https://github.com/sqlalchemy/sqlalchemy)

**🏪 Vectorstore**

A vectorstore is used to store the embeddings associated to the events' descriptions and retrieve the most similar to a given query.

*Main dependencies:* [pinecone](https://github.com/pinecone-io/pinecone-python-client)

### Events data mining

**🕷️ Web scraper**

A scraper has been developed to retrieve events from certain websites.

*Main dependencies:* [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/)



## 🚀 Where can I try it?
Scan the QR code and start chatting with the deployed version:

<center><img src="assets/weeklend-wa-qr.png" width="120" height="120"></center>

## 💻 How can I use the code?
Under the `frontend/` folder there are a few UIs built with [streamlit](https://github.com/streamlit/streamlit) that can be used to test different parts of the code.
