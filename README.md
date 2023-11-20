# Weeklend Chat
⚡ The AI for your free time ⚡


## 🤔 What is it?
Weeklend is a chatbot that operates on WhatsApp to provide recommendations on events, activities, bars, restaurants or places to go.


## 🔧 How is the repo structured?
### Chatbot
#### 🪝 WhatsApp Webhook
A webhook communicates with the WhatsApp Cloud API for receiving messages from the users and sending the appropriate answers back to them.

*Main dependencies: [fastapi](https://github.com/tiangolo/fastapi)*

#### 🤖 LLM
An LLM agent is used when a message is received to decide whether to directly respond to the user or to call a function that searches for events in the vectorstore. When searching for the events, the LLM extracts the date (or date range) from the user's query as well as if it refers to daytime or nighttime.
When the function is called, a second LLM evaluates the relevance of the retrieved events and formulates a response.

*Main dependencies: [langchain](https://github.com/langchain-ai/langchain), [openai](https://github.com/openai/openai-python)*

#### 💾 SQL Database
A SQL database is used for storing **users**, **conversations** and **events** information.

*Main dependencies: [sqlalchemy](https://github.com/sqlalchemy/sqlalchemy), [alembic](https://github.com/sqlalchemy/alembic)*

#### 🏪 Vectorstore
A vectorstore is used to store the embeddings associated to the events' descriptions and retrieve the most similar to a given query.

*Main dependencies: [pinecone](https://github.com/pinecone-io/pinecone-python-client)*


### Events data mining
#### 🕷️ Web Scraper
A scraper has been developed to retrieve events from certain websites.

*Main dependencies: [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/)*

#### 📝 Google Form
An integration to retrieve the events inserted into a Google Form and saved into a Google Sheet is available.

*Main dependencies: [google-api-python-client](https://github.com/googleapis/google-api-python-client)*


## 🚀 Where can I try it?
Scan the QR code and start chatting with the deployed version:

<center><img src="assets/weeklend-wa-qr.png" width="120" height="120"></center>


## 💻 How can I use the code?
### Commands
* The app main entry point sits at `app/main.py` and can be run with command: `uvicorn app.main:app`.
* To run tests use the command: `pytest`
* When the database schema is modified, run a migration by following these steps:
  * Generate a migration with: `alembic revision --autogenerate -m "Your migration title"`;
  * Check the auto-generated migration file in `migrations/` folder and manually modify it if necessary;
  * Upgrade the database schema with: `alembic upgrade head`.
* There are a few UIs built to interact with different parts of the app, to use them:
  * Activate the backend for the UIs with: `uvicorn interface.backend:app`;
  * Run the frontend with: `streamlit run main_ui.py`.

### User Interfaces
The `interface/` folder contains the following UIs:
* `interface.uis.chatbot:ui`: a chatbot UI for chatting with the LLM connected to the vectorstore;
* `interface.uis.control_panel:ui`: a UI for loading events to the vectorstore, and running the web scrapers and Google Form integrations;
* `interface.uis.dashboard:ui`: a dashboard UI to visualize usage KPIs of the deployed app.

*Main dependencies: [streamlit](https://github.com/streamlit/streamlit), [pandas](https://github.com/pandas-dev/pandas), [altair](https://github.com/altair-viz/altair)*


## 🪂 How is it deployed?
* The app is deployed as an AWS Lambda function.
  * Automatic deployment is enabled through GitHub Actions on every push to `master` branch, with a workflow that runs `black` linting and `pytest` tests before deploying the new version.
* An AWS API Gateway ensures the webhook connection between the Lambda function and WhatsApp Cloud API.
* The SQL database is hosted on AWS RDS.
* The vectorstore is hosted on Pinecone.
* The LLM is run by OpenAI and called through their API.
