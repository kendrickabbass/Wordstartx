import os
import logging
import re
from collections import Counter
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import textstat
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token from environment variable
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
PORT = int(os.environ.get('PORT', 8080))

# User sessions to store last text
user_sessions = {}

# Flask app for Railway health checks
app = Flask(__name__)

@app.route('/')
def health_check():
    """Health check endpoint for Railway"""
    return 'Bot is running!', 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle webhook requests from Telegram"""
    try:
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        bot_app.process_update(update)
        return 'OK', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'Error', 500

def analyze_text(text):
    """Comprehensive text analysis"""
    # Word count
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)
    
    # Character count (excluding spaces)
    char_count = len(text.replace(' ', ''))
    
    # Character count (including spaces)
    char_count_with_spaces = len(text)
    
    # Sentence count
    sentences = re.split(r'[.!?]+', text)
    sentence_count = len([s for s in sentences if s.strip()])
    
    # Paragraph count
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    paragraph_count = len(paragraphs) if paragraphs else 1
    
    # Reading time (average 200 words per minute)
    reading_time_minutes = word_count / 200
    reading_time_seconds = reading_time_minutes * 60
    
    # Speaking time (average 150 words per minute)
    speaking_time_minutes = word_count / 150
    speaking_time_seconds = speaking_time_minutes * 60
    
    # Keyword frequency (top 5)
    stopwords = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 
                 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
                 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 
                 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
                 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get',
                 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no',
                 'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your',
                 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then',
                 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
                 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first',
                 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these',
                 'give', 'day', 'most', 'us'}
    
    word_freq = Counter([w.lower() for w in words if w.lower() not in stopwords])
    top_keywords = word_freq.most_common(5)
    
    # Readability score (Flesch Reading Ease)
    try:
        readability = textstat.flesch_reading_ease(text)
        if readability >= 90:
            readability_level = "Very Easy (5th grade)"
        elif readability >= 80:
            readability_level = "Easy (6th grade)"
        elif readability >= 70:
            readability_level = "Fairly Easy (7th grade)"
        elif readability >= 60:
            readability_level = "Plain English (8th-9th grade)"
        elif readability >= 50:
            readability_level = "Fairly Difficult (10th-12th grade)"
        elif readability >= 30:
            readability_level = "Difficult (College)"
        else:
            readability_level = "Very Difficult (College Graduate)"
        
        readability_score = round(readability, 2)
    except:
        readability_score = 0
        readability_level = "Unable to calculate"
    
    # Average word length
    avg_word_length = char_count / word_count if word_count > 0 else 0
    
    # Average sentence length
    avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
    
    # Longest word
    longest_word = max(words, key=len) if words else "N/A"
    
    # Unique word count
    unique_words = len(set([w.lower() for w in words]))
    
    return {
        'word_count': word_count,
        'char_count': char_count,
        'char_count_with_spaces': char_count_with_spaces,
        'sentence_count': sentence_count,
        'paragraph_count': paragraph_count,
        'reading_time_minutes': round(reading_time_minutes, 2),
        'reading_time_seconds': round(reading_time_seconds, 0),
        'speaking_time_minutes': round(speaking_time_minutes, 2),
        'speaking_time_seconds': round(speaking_time_seconds, 0),
        'top_keywords': top_keywords,
        'readability_score': readability_score,
        'readability_level': readability_level,
        'avg_word_length': round(avg_word_length, 2),
        'avg_sentence_length': round(avg_sentence_length, 2),
        'longest_word': longest_word,
        'unique_words': unique_words
    }

def format_analysis_result(data):
    """Format analysis results for display"""
    # Time formatting
    reading_minutes = int(data['reading_time_minutes'])
    reading_seconds = int(data['reading_time_seconds'] % 60)
    speaking_minutes = int(data['speaking_time_minutes'])
    speaking_seconds = int(data['speaking_time_seconds'] % 60)
    
    # Keywords formatting
    keywords_str = "\n".join([f"  • {word}: {count}x" for word, count in data['top_keywords']]) if data['top_keywords'] else "  No significant keywords found"
    
    result = f"""📊 **Text Analysis Results**

📝 **Word Count:** {data['word_count']}
📝 **Unique Words:** {data['unique_words']}
📝 **Characters (no spaces):** {data['char_count']}
📝 **Characters (with spaces):** {data['char_count_with_spaces']}
📝 **Sentences:** {data['sentence_count']}
📝 **Paragraphs:** {data['paragraph_count']}

⏱️ **Reading Time:** {reading_minutes}m {reading_seconds}s
🗣️ **Speaking Time:** {speaking_minutes}m {speaking_seconds}s

📈 **Keyword Frequency (Top 5):**
{keywords_str}

📊 **Readability Score:** {data['readability_score']} - {data['readability_level']}

📏 **Average Word Length:** {data['avg_word_length']} characters
📏 **Average Sentence Length:** {data['avg_sentence_length']} words
🔤 **Longest Word:** {data['longest_word']}

---
_Send me any text to analyze it!_
"""
    return result

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    welcome_text = """
👋 **Welcome to WordStartX Bot!**

I'm your powerful text analysis assistant. I can analyze any text you send me and provide:

✅ Word, character & sentence count
✅ Reading & speaking time estimates  
✅ Keyword frequency analysis
✅ Paragraph counter
✅ Readability score
✅ Unique word count
✅ Average word & sentence length

**How to use:**
• Send me any text message
• Forward a message to me
• Reply to a message with /analyze
• Use /help to see all commands

Let's get started! Send me some text to analyze. 📝
"""
    keyboard = [
        [InlineKeyboardButton("📊 Analyze Last Text", callback_data='analyze_last')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')],
        [InlineKeyboardButton("📊 Advanced Stats", callback_data='advanced')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when /help is issued."""
    help_text = """
📖 **Help & Commands**

**Available Commands:**
/start - Start the bot
/help - Show this help message
/analyze - Analyze the replied text or last text
/stats - Show bot statistics
/clear - Clear your session data

**How to use:**
1. Send any text to analyze it automatically
2. Reply to a message with /analyze
3. Forward a message to the bot
4. Use the inline buttons for quick actions

**What I analyze:**
• Word, character & sentence count
• Reading & speaking time estimates
• Keyword frequency (top 5)
• Paragraph counter
• Readability score (Flesch Reading Ease)
• Unique word count
• Average word & sentence length
• Longest word

**Tips:**
• For best results, send at least 50 words
• Long texts (1000+ words) give more accurate readability scores
• The bot works with any language, but readability scores are optimized for English

Need more help? Just ask! 😊
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /analyze command to analyze replied text or last text."""
    user_id = update.effective_user.id
    
    # Check if replying to a message
    if update.message.reply_to_message and update.message.reply_to_message.text:
        text = update.message.reply_to_message.text
    elif user_id in user_sessions and user_sessions[user_id]:
        text = user_sessions[user_id]
    else:
        await update.message.reply_text(
            "⚠️ No text found to analyze. Please send me some text first or reply to a message with /analyze."
        )
        return
    
    await update.message.reply_text("⏳ Analyzing your text... Please wait.")
    
    try:
        data = analyze_text(text)
        result = format_analysis_result(data)
        await update.message.reply_text(result, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error analyzing text: {e}")
        await update.message.reply_text("❌ Sorry, there was an error analyzing your text. Please try again.")

async def analyze_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callback for analysis."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'analyze_last':
        if user_id in user_sessions and user_sessions[user_id]:
            text = user_sessions[user_id]
            await query.edit_message_text("⏳ Analyzing your text... Please wait.")
            
            try:
                analysis_data = analyze_text(text)
                result = format_analysis_result(analysis_data)
                await query.edit_message_text(result, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error analyzing text: {e}")
                await query.edit_message_text("❌ Sorry, there was an error analyzing your text. Please try again.")
        else:
            await query.edit_message_text(
                "⚠️ No text found to analyze. Please send me some text first."
            )
    
    elif data == 'help':
        help_text = """
📖 **Help & Commands**

**Available Commands:**
/start - Start the bot
/help - Show this help message
/analyze - Analyze the replied text or last text
/stats - Show bot statistics

**How to use:**
• Send any text to analyze it automatically
• Reply to a message with /analyze
• Forward a message to the bot
• Use the inline buttons for quick actions

**What I analyze:**
• Word, character & sentence count
• Reading & speaking time estimates
• Keyword frequency (top 5)
• Paragraph counter
• Readability score
• Unique word count
• Average word & sentence length
• Longest word

Need more help? Just ask! 😊
"""
        await query.edit_message_text(help_text, parse_mode='Markdown')
    
    elif data == 'advanced':
        if user_id in user_sessions and user_sessions[user_id]:
            text = user_sessions[user_id]
            await query.edit_message_text("⏳ Generating advanced statistics...")
            
            try:
                analysis_data = analyze_text(text)
                # Show only the advanced stats
                advanced = f"""📊 **Advanced Text Statistics**

📝 **Vocabulary Richness:** {analysis_data['unique_words']} unique words out of {analysis_data['word_count']} total
📝 **Lexical Density:** {round((analysis_data['unique_words'] / analysis_data['word_count']) * 100, 2)}%

📏 **Average Word Length:** {analysis_data['avg_word_length']} characters
📏 **Average Sentence Length:** {analysis_data['avg_sentence_length']} words
📏 **Longest Word:** {analysis_data['longest_word']}

📈 **Readability:** {analysis_data['readability_score']} - {analysis_data['readability_level']}

⚡ **Reading Speed:** {round(analysis_data['word_count'] / (analysis_data['reading_time_minutes'] or 0.01))} words per minute
🗣️ **Speaking Speed:** {round(analysis_data['word_count'] / (analysis_data['speaking_time_minutes'] or 0.01))} words per minute

💡 **Text Statistics:**
• Total characters: {analysis_data['char_count_with_spaces']}
• Average characters per word: {analysis_data['avg_word_length']}
• Average words per sentence: {analysis_data['avg_sentence_length']}
"""
                await query.edit_message_text(advanced, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error generating advanced stats: {e}")
                await query.edit_message_text("❌ Sorry, there was an error generating advanced statistics.")
        else:
            await query.edit_message_text(
                "⚠️ No text found. Please send me some text first."
            )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send bot statistics."""
    total_users = len(user_sessions)
    stats_text = f"""
📊 **Bot Statistics**

👥 **Active Users:** {total_users}
📝 **Total Texts Analyzed:** {sum(1 for v in user_sessions.values() if v)}

**Bot Information:**
• Version: 2.0.0
• Status: Online ✅
• Platform: Railway.com
• Uptime: Running smoothly

**Features:**
• Text Analysis
• Readability Scores
• Keyword Frequency
• Time Estimates

Need analysis? Send me any text! 📝
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear user session data."""
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await update.message.reply_text("✅ Your session data has been cleared!")
    else:
        await update.message.reply_text("ℹ️ You don't have any saved session data.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages and analyze them automatically."""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Store the text for later use
    user_sessions[user_id] = text
    
    # Check if it's a command
    if text.startswith('/'):
        return
    
    await update.message.reply_text("📝 Analyzing your text...")
    
    try:
        data = analyze_text(text)
        result = format_analysis_result(data)
        await update.message.reply_text(result, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error analyzing text: {e}")
        await update.message.reply_text("❌ Sorry, there was an error analyzing your text. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred. Please try again later."
        )

def setup_bot():
    """Set up and return the bot application."""
    application = Application.builder().token(TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("clear", clear_command))

    # Register message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Register callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(analyze_callback, pattern='^(analyze_last|help|advanced)$'))

    # Register error handler
    application.add_error_handler(error_handler)
    
    return application

# Global variable to store bot application for webhook
bot_app = None

def main():
    """Start the bot."""
    global bot_app
    
    print("🤖 Bot is starting...")
    print(f"🌐 Running on port: {PORT}")
    
    # Setup bot application
    bot_app = setup_bot()
    
    # Set webhook if running on Railway
    if os.getenv('RAILWAY_ENVIRONMENT'):
        webhook_url = f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}/webhook"
        print(f"🔗 Setting webhook: {webhook_url}")
        bot_app.bot.set_webhook(url=webhook_url)
        
        # Run Flask app for webhook
        app.run(host='0.0.0.0', port=PORT)
    else:
        # Run polling for local development
        print("🔄 Running in polling mode...")
        bot_app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
