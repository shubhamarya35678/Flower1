
import asyncio
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

import config
from AnonXMusic import app
from AnonXMusic.misc import SUDOERS
from AnonXMusic.utils.database import (
    get_top_groups_by_requests, 
    get_served_chats, 
    get_group_request_stats,
    get_top_users_global,
    get_user_stats_detailed
)
from AnonXMusic.utils.decorators.language import language
from config import BANNED_USERS

@app.on_message(filters.command(["rankinggroups" "topgc", "topgroups"]) & ~BANNED_USERS)
@language
async def top_groups_command(client, message: Message, _):
    """Show top 10 groups by song requests"""
    
    # Send initial message
    msg = await message.reply_text("🔍 <b>Fetching top groups data...</b>", parse_mode=ParseMode.HTML)
    
    try:
        # Get top groups from database
        top_groups = await get_top_groups_by_requests(10)
        
        if not top_groups:
            return await msg.edit_text(
                "<blockquote>❌ <b>No group statistics found!</b>\n\n<i>Groups need to request songs to appear in rankings.</i></blockquote>",
                parse_mode=ParseMode.HTML
            )
        
        # Build the ranking message with HTML formatting
        text = f"<blockquote>🏆 <b>TOP 10 GROUPS BY SONG REQUESTS</b>\n\n"
        text += f"📊 <b>Ranked by total song requests</b>\n"
        text += f"🎵 <b>Bot:</b> {app.mention}\n\n"
        
        # Add rankings
        for i, group in enumerate(top_groups, 1):
            chat_id = group.get("chat_id", "Unknown")
            chat_title = group.get("chat_title", "Unknown Group")
            chat_username = group.get("chat_username", None)
            total_requests = group.get("total_requests", 0)
            last_request = group.get("last_request")
            last_query = group.get("last_query", "Unknown")
            
            # Escape HTML characters in group title
            chat_title_escaped = chat_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # Create group link if username exists, otherwise just show name
            if chat_username and not str(chat_username).startswith("None"):
                group_link = f'<a href="https://t.me/{chat_username}"><b>{chat_title_escaped}</b></a>'
            else:
                group_link = f"<b>{chat_title_escaped}</b>"
            
            # Escape HTML in query
            last_query_escaped = last_query.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # Truncate long queries
            if len(last_query_escaped) > 20:
                last_query_escaped = last_query_escaped[:17] + "..."
            
            # Format last request time
            if last_request:
                try:
                    if isinstance(last_request, str):
                        time_str = "Recently"
                    else:
                        # Calculate time difference
                        now = datetime.now()
                        diff = now - last_request
                        
                        if diff.days > 0:
                            time_str = f"{diff.days}d ago"
                        elif diff.seconds > 3600:
                            hours = diff.seconds // 3600
                            time_str = f"{hours}h ago"
                        elif diff.seconds > 60:
                            minutes = diff.seconds // 60
                            time_str = f"{minutes}m ago"
                        else:
                            time_str = "Just now"
                except:
                    time_str = "Unknown"
            else:
                time_str = "Unknown"
            
            # Add ranking emoji
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"<b>{i}.</b>"
            
            text += f"{emoji} {group_link}\n\n"
            text += f"    ├ <b>🎵 Requests:</b> <code>{total_requests:,}</code>\n"
            # text += f"    ├ <b>🎤 Last Song:</b> <code>{last_query_escaped}</code>\n"
            text += f"    └ <b>⏰ Last Active:</b> <code>{time_str}</code>\n\n"
        
        # Add footer
        try:
            total_served = len(await get_served_chats())
            text += f"<b>📈 Total Served Groups:</b> <code>{total_served:,}</code>\n\n"
        except:
            text += f"<b>📈 Active Groups:</b> <code>{len(top_groups)}</code>\n\n"
        
        # text += f"<b>🔄 Updated:</b> <code>{datetime.now().strftime('%d/%m/%Y %H:%M')}</code>\n"
        # text += f"<b>💡 Tip:</b> Use <code>/check &lt;chat_id&gt;</code> to check specific group stats</blockquote>"
        
        # Send the ranking
        await msg.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=False)
        
    except Exception as e:
        await msg.edit_text(
            f"<blockquote>❌ <b>Error occurred while fetching data!</b>\n\n"
            f"<b>Error:</b> <code>{str(e)}</code>\n\n"
            f"<i>Please try again later or contact support.</i></blockquote>",
            parse_mode=ParseMode.HTML
        )

@app.on_message(filters.command(["check"]) & ~BANNED_USERS)
@language
async def check_group_command(client, message: Message, _):
    """Check specific group statistics by chat ID"""
    
    # Check if chat ID is provided
    if len(message.text.split()) < 2:
        return await message.reply_text(
            "<blockquote>❌ <b>Usage Error!</b>\n\n"
            "<b>Usage:</b> <code>/check &lt;chat_id&gt;</code>\n"
            "<b>Example:</b> <code>/check -1001234567890</code>\n\n"
            "<b>💡 Tip:</b> Use <code>/topgc</code> to see top groups with their IDs</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    try:
        chat_id = int(message.text.split()[1])
    except ValueError:
        return await message.reply_text(
            "<blockquote>❌ <b>Invalid Chat ID!</b>\n\n"
            "<b>Please provide a valid numeric chat ID</b>\n"
            "<b>Example:</b> <code>/check -1001234567890</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    # Send loading message
    msg = await message.reply_text(
        f"<blockquote>🔍 <b>Checking group data for:</b> <code>{chat_id}</code>...</blockquote>", 
        parse_mode=ParseMode.HTML
    )
    
    try:
        stats = await get_group_request_stats(chat_id)
        
        if not stats:
            return await msg.edit_text(
                f"<blockquote>❌ <b>No statistics found!</b>\n\n"
                f"<b>Chat ID:</b> <code>{chat_id}</code>\n\n"
                f"<i>This group has not made any song requests yet.</i></blockquote>",
                parse_mode=ParseMode.HTML
            )
        
        # Get today's requests
        today = datetime.now().strftime("%Y-%m-%d")
        today_requests = stats.get("daily_requests", {}).get(today, 0)
        
        # Get top user
        top_users = stats.get("top_users", {})
        if top_users:
            top_user_id = max(top_users.keys(), key=lambda x: top_users[x])
            top_user_requests = top_users[top_user_id]
        else:
            top_user_id = "Unknown"
            top_user_requests = 0
        
        # Create group link if username exists
        chat_username = stats.get("chat_username", None)
        chat_title = stats.get("chat_title", "Unknown Group")
        
        # Escape HTML characters
        chat_title_escaped = chat_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        last_query_escaped = stats.get('last_query', 'Unknown').replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        if chat_username and not str(chat_username).startswith("None"):
            group_link = f'<a href="https://t.me/{chat_username}"><b>{chat_title_escaped}</b></a>'
        else:
            group_link = f"<b>{chat_title_escaped}</b>"
        
        # Format last request time
        last_request = stats.get("last_request")
        if last_request:
            try:
                if isinstance(last_request, str):
                    time_str = "Recently"
                else:
                    now = datetime.now()
                    diff = now - last_request
                    
                    if diff.days > 0:
                        time_str = f"{diff.days} days ago"
                    elif diff.seconds > 3600:
                        hours = diff.seconds // 3600
                        time_str = f"{hours} hours ago"
                    elif diff.seconds > 60:
                        minutes = diff.seconds // 60
                        time_str = f"{minutes} minutes ago"
                    else:
                        time_str = "Just now"
            except:
                time_str = "Unknown"
        else:
            time_str = "Unknown"
        
        text = f"<blockquote>📊 <b>GROUP STATISTICS</b>\n\n"
        text += f"<b>🏷 Group:</b> {group_link}\n"
        text += f"<b>🆔 Chat ID:</b> <code>{chat_id}</code>\n\n"
        text += f"<b>🎵 Total Requests:</b> <code>{stats.get('total_requests', 0):,}</code>\n"
        text += f"<b>📅 Today's Requests:</b> <code>{today_requests}</code>\n"
        text += f"<b>👑 Top User ID:</b> <code>{top_user_id}</code> (<code>{top_user_requests}</code> requests)\n\n"
        text += f"<b>🎤 Last Song:</b> <code>{last_query_escaped}</code>\n"
        text += f"<b>⏰ Last Request:</b> <code>{time_str}</code>\n\n"
        # text += f"<b>🔄 Checked:</b> <code>{datetime.now().strftime('%d/%m/%Y %H:%M')}</code></blockquote>"
        
        await msg.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=False)
        
    except Exception as e:
        await msg.edit_text(
            f"<blockquote>❌ <b>Error occurred while checking group!</b>\n\n"
            f"<b>Chat ID:</b> <code>{chat_id}</code>\n"
            f"<b>Error:</b> <code>{str(e)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

# Optional: Add a detailed group stats command for current group
@app.on_message(filters.command(["groupstats"]) & filters.group & ~BANNED_USERS)
@language
async def group_stats_command(client, message: Message, _):
    """Show detailed stats for current group"""
    
    try:        
        stats = await get_group_request_stats(message.chat.id)
        
        if not stats:
            return await message.reply_text(
                "<blockquote>❌ <b>No statistics found for this group.</b>\n\n"
                "<i>Start requesting songs to generate statistics!</i></blockquote>",
                parse_mode=ParseMode.HTML
            )
        
        # Get today's requests
        today = datetime.now().strftime("%Y-%m-%d")
        today_requests = stats.get("daily_requests", {}).get(today, 0)
        
        # Get top user
        top_users = stats.get("top_users", {})
        if top_users:
            top_user_id = max(top_users.keys(), key=lambda x: top_users[x])
            top_user_requests = top_users[top_user_id]
        else:
            top_user_id = "Unknown"
            top_user_requests = 0
        
        # Escape HTML characters
        group_title_escaped = message.chat.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        last_query_escaped = stats.get('last_query', 'Unknown').replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        text = f"<blockquote>📊 <b>CURRENT GROUP STATISTICS</b>\n\n"
        text += f"<b>🏷 Group:</b> <b>{group_title_escaped}</b>\n"
        text += f"<b>🆔 Chat ID:</b> <code>{message.chat.id}</code>\n\n"
        text += f"<b>🎵 Total Requests:</b> <code>{stats.get('total_requests', 0):,}</code>\n"
        text += f"<b>📅 Today's Requests:</b> <code>{today_requests}</code>\n"
        text += f"<b>👑 Top User ID:</b> <code>{top_user_id}</code> (<code>{top_user_requests}</code> requests)\n\n"
        text += f"<b>🎤 Last Song:</b> <code>{last_query_escaped}</code>\n"
        text += f"<b>⏰ Last Request:</b> <code>{stats.get('last_request', 'Unknown')}</code></blockquote>"
        
        await message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
    except Exception as e:
        await message.reply_text(
            f"<blockquote>❌ <b>Error:</b> <code>{str(e)}</code></blockquote>", 
            parse_mode=ParseMode.HTML
        )

@app.on_message(filters.command(["topusers", "topu"]) & ~BANNED_USERS)
@language
async def top_users_command(client, message: Message, _):
    """Show top 10 users globally by song requests"""
    
    # Send initial message
    msg = await message.reply_text("🔍 <b>Fetching top users data...</b>", parse_mode=ParseMode.HTML)
    
    try:
        # Get top users from database
        top_users = await get_top_users_global(10)
        
        if not top_users:
            return await msg.edit_text(
                "<blockquote>❌ <b>No user statistics found!</b>\n\n<i>Users need to request songs to appear in rankings.</i></blockquote>",
                parse_mode=ParseMode.HTML
            )
        
        # Build the ranking message with HTML formatting
        text = f"<blockquote>👥 <b>TOP 10 USERS BY SONG REQUESTS</b>\n\n"
        text += f"📊 <b>Ranked by total song requests across all groups</b>\n"
        text += f"🎵 <b>Bot:</b> {app.mention}\n\n"
        
        # Add rankings
        for i, user in enumerate(top_users, 1):
            user_id = user.get("_id", "Unknown")
            total_requests = user.get("total_requests", 0)
            groups = user.get("groups", [])
            group_count = len(groups)
            
            # Get user mention if possible
            try:
                user_info = await app.get_users(int(user_id))
                user_mention = user_info.mention
                user_name = user_info.first_name or "Unknown"
            except:
                user_mention = f"<code>{user_id}</code>"
                user_name = "Unknown User"
            
            # Add ranking emoji
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"<b>{i}.</b>"
            
            text += f"{emoji} {user_mention}\n"
            text += f"    ├ <b>🎵 Total Requests:</b> <code>{total_requests:,}</code>\n"
            text += f"    ├ <b>🏘 Active Groups:</b> <code>{group_count}</code>\n"
            text += f"    └ <b>🆔 User ID:</b> <code>{user_id}</code>\n\n"
        
        # Add footer
        text += f"<b>🔄 Updated:</b> <code>{datetime.now().strftime('%d/%m/%Y %H:%M')}</code>\n"
        text += f"<b>💡 Tip:</b> Use <code>/userinfo &lt;user_id&gt;</code> to check specific user stats</blockquote>"
        
        # Send the ranking
        await msg.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
    except Exception as e:
        await msg.edit_text(
            f"<blockquote>❌ <b>Error occurred while fetching users data!</b>\n\n"
            f"<b>Error:</b> <code>{str(e)}</code>\n\n"
            f"<i>Please try again later or contact support.</i></blockquote>",
            parse_mode=ParseMode.HTML
        )

@app.on_message(filters.command(["userinfo", "uinfo"]) & ~BANNED_USERS)
@language
async def user_info_command(client, message: Message, _):
    """Show detailed statistics for a specific user"""
    
    # Check if user ID is provided
    if len(message.text.split()) < 2:
        return await message.reply_text(
            "<blockquote>❌ <b>Usage Error!</b>\n\n"
            "<b>Usage:</b> <code>/userinfo &lt;user_id&gt;</code>\n"
            "<b>Example:</b> <code>/userinfo 123456789</code>\n\n"
            "<b>💡 Tip:</b> Use <code>/topusers</code> to see top users with their IDs</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    try:
        user_id = int(message.text.split()[1])
    except ValueError:
        return await message.reply_text(
            "<blockquote>❌ <b>Invalid User ID!</b>\n\n"
            "<b>Please provide a valid numeric user ID</b>\n"
            "<b>Example:</b> <code>/userinfo 123456789</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    # Send loading message
    msg = await message.reply_text(
        f"<blockquote>🔍 <b>Checking user data for:</b> <code>{user_id}</code>...</blockquote>", 
        parse_mode=ParseMode.HTML
    )
    
    try:
        user_stats = await get_user_stats_detailed(user_id)
        
        if not user_stats or user_stats.get("total_requests", 0) == 0:
            return await msg.edit_text(
                f"<blockquote>❌ <b>No statistics found!</b>\n\n"
                f"<b>User ID:</b> <code>{user_id}</code>\n\n"
                f"<i>This user has not made any song requests yet.</i></blockquote>",
                parse_mode=ParseMode.HTML
            )
        
        # Get user info
        try:
            user_info = await app.get_users(user_id)
            user_mention = user_info.mention
            user_name = user_info.first_name or "Unknown"
            username = f"@{user_info.username}" if user_info.username else "No username"
        except:
            user_mention = f"<code>{user_id}</code>"
            user_name = "Unknown User"
            username = "No username"
        
        # Build response
        text = f"<blockquote>👤 <b>USER STATISTICS</b>\n\n"
        text += f"<b>🏷 User:</b> {user_mention}\n"
        text += f"<b>👤 Name:</b> <b>{user_name}</b>\n"
        text += f"<b>🆔 User ID:</b> <code>{user_id}</code>\n"
        text += f"<b>📝 Username:</b> <code>{username}</code>\n\n"
        text += f"<b>🎵 Total Requests:</b> <code>{user_stats['total_requests']:,}</code>\n"
        text += f"<b>🏘 Active Groups:</b> <code>{user_stats['group_count']}</code>\n\n"
        
        # Show top 5 groups where user is most active
        text += f"<b>🏆 TOP GROUPS BY REQUESTS:</b>\n"
        for i, group in enumerate(user_stats["groups"][:5], 1):
            chat_title = group.get("chat_title", "Unknown Group")
            chat_username = group.get("chat_username")
            requests = group.get("requests", 0)
            
            # Escape HTML
            chat_title_escaped = chat_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # Create group link
            if chat_username and not str(chat_username).startswith("None"):
                group_link = f'<a href="https://t.me/{chat_username}">{chat_title_escaped}</a>'
            else:
                group_link = chat_title_escaped
            
            text += f"    <b>{i}.</b> {group_link} - <code>{requests}</code> requests\n"
        
        text += f"\n<b>🔄 Checked:</b> <code>{datetime.now().strftime('%d/%m/%Y %H:%M')}</code></blockquote>"
        
        await msg.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=False)
        
    except Exception as e:
        await msg.edit_text(
            f"<blockquote>❌ <b>Error occurred while checking user!</b>\n\n"
            f"<b>User ID:</b> <code>{user_id}</code>\n"
            f"<b>Error:</b> <code>{str(e)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
