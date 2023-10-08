# Weeklend Chat
⚡ The AI for your free time ⚡

## 🤔 What is it?
Weeklend is a chatbot that operates on WhatsApp to provide recommendations on events, activities, bars, restaurants or places to go.

## 🔧 How is the repo structured?

### Chatbot

**🪝 WhatsApp Webhook**

A webhook communicates with the WhatsApp Cloud API for receiving messages from the users and sending the appropriate answers back to them.

*Main dependencies: [fastapi](https://github.com/tiangolo/fastapi)*

**🤖 LLM**

When a message is received, an LLM is used for:
* Extracting macro information from the message, e.g., whether the message is valid or not, if it refers to a specific date or range of dates, which are used for filtering the events;
* Generating the answer using the most relevant events retrieved from the vectorstore as context.

*Main dependencies: [langchain](https://github.com/langchain-ai/langchain), [openai](https://github.com/openai/openai-python)*

**💾 SQL Database**

A SQL database is used for storing **users**, **conversations** and **events** information.

*Main dependencies: [sqlalchemy](https://github.com/sqlalchemy/sqlalchemy), [alembic](https://github.com/sqlalchemy/alembic)*

**🏪 Vectorstore**

A vectorstore is used to store the embeddings associated to the events' descriptions and retrieve the most similar to a given query.

*Main dependencies: [pinecone](https://github.com/pinecone-io/pinecone-python-client)*

### Events data mining

**🕷️ Web Scraper**

A scraper has been developed to retrieve events from certain websites.

*Main dependencies: [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/)*



## 🚀 Where can I try it?
Scan the QR code and start chatting with the deployed version:

<center><img src="assets/weeklend-wa-qr.png" width="120" height="120"></center>

## 💻 How can I use the code?
* The app main entry point sits at `app/main.py` and can be run with command: `uvicorn app.main:app`.
* In the `interface/` folder there are a few UIs built with *[streamlit](https://github.com/streamlit/streamlit)* that can be used to interact with different parts of the app:
  * `interface.uis.chatbot:ui`: a chatbot UI for chatting with the LLM connected to the vectorstore;
  * `interface.uis.control_panel:ui`: a simple UI for loading events to the vectorstore and running the web scrapers.
* There is a main file controlling all UIs at `main_ui.py`, to use it:
  * Activate the backend for the UIs with: `uvicorn interface.backend:app`;
  * Run the streamlit frontend with: `streamlit run main_ui.py`.
* To run tests use the command: `pytest`

## 🪂 How is it deployed?
* The app is deployed as an AWS Lambda function - automatic deployment is enabled through GitHub Actions on every push to `master` branch, with a workflow that runs `black` linting and `pytest` tests before deploying the new version.
* An AWS API Gateway ensures the webhook connection between the Lambda function and WhatsApp Cloud API.
* The SQL database is hosted on AWS RDS.
* The vectorstore is hosted on Pinecone.
* The LLM is run by OpenAI and called through their API.
