import os
import openai
from telegram import Update
from telegram.ext import Application, CommandHandler, filters, ContextTypes, MessageHandler
from elevenlabs import save
from elevenlabs.client import ElevenLabs
import requests
from dotenv import load_dotenv
load_dotenv()

# Initialize API clients
openai_api_key = os.getenv('OPENAI_API_KEY')
openai_client = openai.OpenAI(api_key=openai_api_key)
elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
ElevenLabs_client = ElevenLabs(
  api_key=os.environ.get('ELEVENLABS_API_KEY'), # Defaults to ELEVEN_API_KEY
)
TOKEN = os.getenv('TELEGRAM_BOT_NAME')


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await process_and_reply(update, context, text)

async def handle_audio_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Download and save the audio file
    audio_file = await context.bot.get_file(update.message.voice.file_id)
    audio_path = f'voice_{update.message.voice.file_unique_id}.ogg'
    with open(audio_path, 'wb') as f:
        response = requests.get(audio_file.file_path)
        f.write(response.content)

    # Transcribe the audio file with Whisper API
    with open(audio_path, "rb") as file:
        transcription = openai_client.audio.transcriptions.create(
            model="whisper-1", 
            file=file
        )
    transcribed_text = transcription.text

    await process_and_reply(update, context, transcribed_text)

async def process_and_reply(update, context, input_text):
    # Process the input text with OpenAI ChatGPT
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
            "role": "system",
            "content": "You are Lennart and act as a helpfull personal assisant, keep anwser very short and percise "
            },
            {
            "role": "user",
            "content": input_text
            }
        ],
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
        )
    gpt_response = response.choices[0].message.content

    # Convert GPT response to audio with ElevenLabs
    audio = ElevenLabs_client.generate(
        text=gpt_response,
        voice="Chris",
        model="eleven_multilingual_v2"
    )
    response_filename = 'response_audio.mp3'
    save(audio, response_filename)

    # Send the audio file back to the user
    await context.bot.send_voice(chat_id=update.effective_chat.id, voice=open(response_filename, 'rb'))

if __name__ == '__main__':
    print('running')
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_text_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_audio_message))

    print('polling')
    app.run_polling()
