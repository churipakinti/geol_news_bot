from keep_alive import keep_alive
import os
import requests
from bs4 import BeautifulSoup
import discord
from discord.ext import commands, tasks

# Load Token from Environment Variables (safer than hardcoding)
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1351055856942186557  # Replace with your Discord channel ID

# RSS Feed URL
rss_url = "https://us22.campaign-archive.com/feed?u=f72114448ed6d63ea977c699d&id=f2bc6d4d01"

# Variable to store the last published post
last_published_title = None

# Initialize Discord Bot
intents = discord.Intents.default()
intents.message_content = True  # Required for message reading
bot = commands.Bot(command_prefix="!", intents=intents)

# ✅ Function to Fetch RSS Data
def fetch_latest_post():
    global last_published_title

    response = requests.get(rss_url)
    soup = BeautifulSoup(response.content, "xml")

    latest_post = soup.find("item")
    if not latest_post:
        return None

    # Extract Main Data
    title = latest_post.find("title").text.strip() if latest_post.find("title") else "No title found"
    link = latest_post.find("link").text.strip() if latest_post.find("link") else "No link found"

    # If it's the same as the last post, return None (to avoid duplicates)
    if title == last_published_title:
        return None

    # Update last published title
    last_published_title = title

    # Fetch the actual webpage content
    page_response = requests.get(link)
    page_soup = BeautifulSoup(page_response.text, "html.parser")

    # Extract "Topic"
    topic = "No topic found"
    all_h4 = page_soup.find_all("h4")

    for h4 in all_h4:
        if "Topic:" in h4.get_text():
            topic_span = h4.find_next("span", style="font-weight:normal;")
            topic = topic_span.get_text(strip=True) if topic_span else "No topic found"
            break

    # Extract Speaker, Date, and Location
    speaker = page_soup.find("h3", class_="mcePastedContent")
    when = page_soup.find("h4", class_="mcePastedContent")
    where = page_soup.find_all("h4", class_="mcePastedContent")

    speaker = speaker.text.strip().replace("Speaker:", "").strip() if speaker else "No speaker found"
    when = when.text.strip().replace("When:", "").strip() if when else "Not found"
    where = where[1].text.strip().replace("Where:", "").replace("(see link below)", "").strip() if len(where) > 1 else "Not found"

    # Extract the first two images
    images = [img["src"] for img in page_soup.find_all("img", limit=2)] if page_soup.find_all("img") else []

    # Extract Zoom link
    zoom_link = next((a["href"] for a in page_soup.find_all("a", href=True) if "zoom" in a["href"]), "No Zoom link found")

    return {
        "title": title,
        "topic": topic,
        "speaker": speaker,
        "when": when,
        "where": where,
        "link": link,
        "zoom_link": zoom_link,
        "images": images
    }

# ✅ Function to Send Post to Discord
async def send_post():
    channel = bot.get_channel(CHANNEL_ID)
    post = fetch_latest_post()

    if not post:
        print("No new post found.")
        return

    embed = discord.Embed(
        title=f"📢  {post['topic']}",
        url=post["link"],
        color=discord.Color.blue()
    )

    embed.add_field(name="🎤 ** Speaker**", value=post["speaker"], inline=False)
    embed.add_field(name="📅 ** When**", value=post["when"], inline=False)
    embed.add_field(name="📍 ** Where**", value=post["where"], inline=False)

    if post["zoom_link"]:
        embed.add_field(name="💻 ** Zoom Meeting**", value=f"[Join Meeting]({post['zoom_link']})", inline=False)

    if len(post["images"]) > 0:
        embed.set_image(url=post["images"][1])  # First image
    if len(post["images"]) > 1:
        embed.set_thumbnail(url=post["images"][0])  # Second image

    await channel.send(embed=embed)

# ✅ Periodically Check for New Posts
@tasks.loop(minutes=10)  # Revisar cada 10 minutos
async def check_rss():
    await send_post()

# ✅ Bot Ready Event
@bot.event
async def on_ready():
    global last_published_title
    print(f"✅ Logged in as {bot.user}")
    
    # Get initial latest post title to avoid duplicate posting
    latest_post = fetch_latest_post()
    if latest_post:
        last_published_title = latest_post["title"]

    check_rss.start()  # Iniciar la verificación periódica del RSS

# ✅ Ping Command to Check if Bot is Alive
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

# Run the bot
bot.run(TOKEN)
