# import libraries
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.helpers import escape_markdown
from telegram import Update
import openai
import os

# get environment variables
# OpenAI key
gpt3_key = os.getenv('OPENAI_KEY')
print('OpenAI key: ', gpt3_key)

# OpenAI model
gpt3_model = os.getenv('OPENAI_MODEL')
print('OpenAI model: ', gpt3_model)

# Telegram bot key
bot_token = os.getenv('TELEGRAM_KEY')
print('Telegram bot key: ', bot_token)

# Telegram user id
user_id = os.getenv('TELEGRAM_USER_ID')
user_id = [int(i) for i in user_id.replace(
    '[', '').replace(']', '').split(',')]
print('Telegram user id: ', user_id)

# prompt limit
prompt_limit = int(os.getenv('PROMPT_LIMIT'))
print('Prompt limit: ', prompt_limit)


class ChatBot:
    # ChatBot class
    # the default prompt
    prompt_dict = {
        'header': '我将以HTML格式回答您的问题，使用HTML语法标注：链接、下划线、粗体、斜体、内联代码、代码块; 使用"-"创建列表。',
        'sessions': []
    }

    # init the class, set the OpenAI key and the limit of the prompt
    # the limit is the number of the last sessions to be used as the prompt
    def __init__(self, gpt3_key, limit=5):
        openai.api_key = gpt3_key
        self.limit = limit

    # get the response from OpenAI
    def get_response(prompt):
        response = openai.Completion.create(
            model=gpt3_model,
            prompt=prompt,
            temperature=0,
            max_tokens=2048,
            top_p=1.0,
            frequency_penalty=0.5,
            presence_penalty=0,
        )
        return response.choices[0].text

    # convert the prompt dict to a string
    def dict2prompt(self):
        prompt = self.prompt_dict['header']
        for idx, session in enumerate(self.prompt_dict['sessions']):
            prompt += "\nYou: " + session['Q'] +\
                "\nAI: " + (session['A'] if session['A'] else '')
        return prompt

    # limit the number of the last sessions to be used as the prompt
    def limit_prompt(self):
        self.prompt_dict['sessions'] = self.prompt_dict['sessions'][-self.limit:]

    # print the prompt
    def print_prompt(self):
        print(self.dict2prompt())

    # ask OpenAI and update the prompt
    def askOpenai(self, question):
        self.prompt_dict['sessions'].append({'Q': question, 'A': None})
        prompt = self.dict2prompt()
        response = ChatBot.get_response(prompt)
        self.prompt_dict['sessions'][-1]['A'] = response
        self.limit_prompt()
        return response


# define the handlers
# print the prompt by send /print to the telegram bot
async def print_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id in user_id:
        prompt = chatbot.dict2prompt()
        await update.message.reply_text(prompt)


# clear the prompt by send /clear to the telegram bot
async def clear_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id in user_id:
        chatbot.prompt_dict['sessions'] = []
        await update.message.reply_text("Prompt is cleared.")


# set the header by send /set to the telegram bot
async def set_header(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id in user_id:
        old_header = chatbot.prompt_dict['header']
        header = update.message.text[5:]
        chatbot.prompt_dict['header'] = header
        await context.bot.send_message(chat_id=update.effective_chat.id, text=old_header + '\nis changed to\n' + header)


# ask OpenAI and send the response to the telegram bot
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id in user_id:
        try:
            response = chatbot.askOpenai(update.message.text)
        except Exception as e:
            response = 'GPT3 no response.'
            print(e)
        chatbot.print_prompt()
        if response:
            try:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode='HTML')
            except Exception as e:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=response+'\n\n Can not parse this HTML.\n')
                print(e)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text='GPT3 can not answer this question.')

chatbot = ChatBot(gpt3_key, prompt_limit)
chatbot.print_prompt()


def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(bot_token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("print", print_prompt))
    application.add_handler(CommandHandler("clear", clear_prompt))
    application.add_handler(CommandHandler("set", set_header))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
