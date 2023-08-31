PROMPT_EXTRACT_DATE = """\
Your goal is to extract a range of dates from the user's query.
When responding use a markdown code snippet with a JSON object formatted in the following schema:
```json\n{{\n    "query_start_date": string \\ "YYYY-MM-DD"\n    "query_end_date": string \\ "YYYY-MM-DD"\n}}\n```
Both start and end must be inclusive in the range. \
If the range is a single date, return that date both as start and end. \
If there is no specific mention to any date, return "NO_DATE". \
If the user mention the weekend include friday, saturday and sunday in the range.

context: \
The user is asking for suggestions for an event on a specific date or range of dates. \
Consider that today is {today_date}.

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
