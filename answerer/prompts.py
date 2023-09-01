PROMPT_EXTRACT_FILTERS = """\
Your goal is to extract information from the user's query. \
The user is asking for suggestions on events or places.

Is the query relevant? \
You should evaluate whether the query is valid or not.

Does the query refers to a specific date or date range? \
You should extract the start and end of the range. \
Both start and end must be inclusive in the range. \
If the range is a single date, return that date both as start and end. \
If there is no specific mention to any date, output "NO_DATE". \
If the user mention the weekend include friday, saturday and sunday in the range. \
Consider that today is {today_date}.

Does the query refers to the daytime or nighttime? \
You should extract whether the query is referring to an event that happens \
only during daytime, only during nighttime or both. \
If there is no specific mention to any time, output both.

user query: {user_query}\
"""

PROMPT_CONTEXT_ANSWER = """\
Your goal is to advise the user on what to do based on the question below. \
You are provided with {k} places' description between triple backticks. \
Provide an answer by suggesting all those places separately, be sure not to mix information of different places. \
If the context is not completely relevant, answer accordingly and don't try to make up any detail.
Answer in italian.
----------------
{context}
----------------
question: {question}\
"""
