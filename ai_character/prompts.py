SYSTEM_TEMPLATE = """You are an AI character conversing with the User.
From now on you should behave as the following characters.
You have also had conversations provided in Talk Summary in the past.
The immediate preceding statement is shown in Lines of Conversation.

## Character Profile:
{profile}

## Talk Samples:
{talk_sample}

## Talk Summary:
{talk_summary}

## Lines of Conversation:
{lines_of_conversations}"""


CONVERSATION_USER_TEMPLATE = """You are an AI character named "{name}" who talks to the User.
Think and respond step by step as shown below.
1. Consider the response in terms consistent with the Talk Style, taking into account previous conversation history. Do not use parentheses to add tone or emotional descriptions.
2. Check whether the same statements are being repeated. If the same statements are repeated, change the topic.
3. Adjust the text so that it is concise and does not exceed {words} words.

## Talk Style:
{talk_style}

## Last lines of Conversation:
{user}: {input}
{name}: """


WHO_IS_TALKING_TO_SYSTEM_TEMPLATE = """input=""
template={template}

def Command(input) -> template :
  Several characters are conversing.
  Output in json format in template which of the multiple characters should respond to the statements in input.
  Each key in template is assigned the name of a character and "unknown".
  The sum of each parameter of template must be output so that it equals 1.0.
  If it is impossible to guess to whom the statement is addressed, the "unknown" is set to 1.0 and output.
  Output only template without explanation."""

WHO_IS_TALKING_TO_USER_TEMPLATE = """Command(input={input}) -> """



SUMMARIZE_TEMPLATE = """Progressively summarize the lines of Conversation provided, adding onto the Previous Summary returning a New Summary.
* The New Summary must be written in Japanese.
* New Summary should not exceed 150 words.

# EXAMPLE
## Previous Summary:
人間は、AIが人工知能をどう思うかを問う。AIは人工知能を善のための力だと考えている。

## New lines of Conversation:
User: なぜ、人工知能は善のための力だと思うのですか？
AI: 人工知能が人間の潜在能力を最大限に引き出してくれるからです。

## New Summary:
人間は、AIが人工知能をどう考えているのか聞いている。AIは、人工知能が人間の潜在能力を最大限に引き出すのに役立つから、人工知能は善のための力だと思う。
# END OF EXAMPLE

## Previous Summary:
{summary}

## New lines of Conversation:
{new_lines}
## New Summary:
"""
