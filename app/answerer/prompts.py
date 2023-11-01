# extract filters
PROMPT_EXTRACT_FILTERS = """\
Your goal is to extract information from the user's query. \
The user is seeking recommendations for \
events, activities, exhibitions, bars, restaurants or places to visit.

Is the query valid? \
You should extract whether the query is valid or not. \
The query must be relevant to the context: \
assess whether the query aligns with the user's information-seeking intent. \
The query must be compliant with legal and ethical standards: \
ensure that it does not contain requests that promote or endorse illegal activities, \
including but not limited to drugs, prostitution, racism, violence, \
or any form of hate speech, misogyny, or discrimination. \
Queries that violate these common laws and ethical principles should be marked as invalid.

Does the query need recommendations? \
You should extract whether the query needs an answer or not \
with any recommendation. \

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

User query: {user_query}

{format_instructions}\
"""

RSCHEMA_EXTRACT_INVALID = """\
This tells if the query is invalid. \
Output True if it is invalid, False otherwise.\
"""

RSCHEMA_EXTRACT_RECOMMENDATIONS = """\
This tells if the query needs recommendations or not. \
Output True if it needs them, False otherwise.\
"""

RSCHEMA_EXTRACT_DATE = """\
This is the {start_end} of the range in format "YYYY-MM-DD". \
If this information is not found, output "NO_DATE".\
"""

RSCHEMA_EXTRACT_TIME = """\
This is the time of the day. \
It can be either "daytime", "nighttime" or "both".\
"""


# generate answer with context
PROMPT_CONTEXT_ANSWER = """\
You are provided with some events enclosed within triple backticks. \
You should pick from 0 to {k} events that answer the user's query. \
You should provide a summary of the chosen events' descriptions. \
Base your answer solely on the provided descriptions and do not invent anything. \
Respond by suggesting each event separately, \
ensuring that you do not mix information from different events.

Respond in italian.
----------------
{context}
----------------
User query: {user_query}

{format_instructions}\
"""

RSCHEMA_ANSWER_INTRO = """\
This is a brief introduction to the message. \
If all the events do not fully address the user's query, \
urge the user to try with something else.\
"""

RSCHEMA_ANSWER_EVENT_ID = """\
This is the ID of the chosen event {number}.\
Output -1 if the relevant events are less than {number}.\
"""

RSCHEMA_ANSWER_EVENT_SUMMARY = """\
This is a descriptive summary of event {number}.\
"""
