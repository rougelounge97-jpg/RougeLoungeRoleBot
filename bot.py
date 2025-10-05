# Rouge Lounge Role Panel Bot (discord.py 2.x)
# -------------------------------------------------------------
# 概要:
# - Slashコマンド /setup_roles で「ゲスト」「キャスト希望」の役職付与パネルを投稿
# - 2つのボタンでロールを付与/解除（トグル）
# - 「キャスト希望」を押した人には、面接チャンネルへの案内をDM or その場で通知
#
# 前提:
# 1) Discord Developer PortalでBotを作成し、Tokenを取得
# 2) BotのPrivileged Gateway Intentsで「SERVER MEMBERS INTENT (Guild Members)」をON
# 3) Botに以下の権限を付与してサーバーへ招待（URLのスコープに applications.commands, bot を含める）
#    - Manage Roles（ロールの管理）
#    - Send Messages / Read Message History / Use Slash Commands
# 4) サーバーで「ゲスト」「キャスト希望」ロールを作成済み
# 5) Python 3.10+ を推奨
# 6) 依存ライブラリ: discord.py, python-dotenv
#    pip install -U discord.py python-dotenv
#
# 起動方法:
# - .env ファイルをプロジェクト直下に作成
#   DISCORD_TOKEN=あなたのボットトークン
# - python bot.py で起動
#
# 使用方法:
# - /setup_roles コマンドを実行し、
#    customer_role = 「ゲスト」ロール
#    candidate_role = 「キャスト希望」ロール
#    interview_channel = 「キャスト面接用」チャンネル
#   を指定すると、パネルが投稿されます。
#
# 注意事項:
# - Botのロールが、付与/解除したいロールより「上」にある必要があります（ロール階層）
# - 初回起動時、on_ready 内でコマンド同期 (tree.sync) を行います
# - グローバルコマンドの反映に数分かかる場合があります。ギルド限定同期に切り替える場合は GUILD_ID を設定して tree.sync(guild=...) を使用してください

import os
import os
from dotenv import load_dotenv

# Renderなどの環境では .env がなくてもエラーにならないようにする
load_dotenv()  # .envがあれば読み込む、なければスルー

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN が見つかりません。Render の Environment に設定してください。")
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# 必要なIntent（メンバー操作のためにmembersが必要）
intents = discord.Intents.default()
intents.members = True
intents.guilds = True

# prefix不要のため、commands.Bot でも command_prefix は未使用
bot = commands.Bot(command_prefix=commands.when_mentioned_or("/"), intents=intents)

def has_manage_roles(interaction: discord.Interaction) -> bool:
    perms = interaction.user.guild_permissions
    return perms.manage_roles or perms.administrator

class RolePanelView(discord.ui.View):
    def __init__(self, guest_role: discord.Role, candidate_role: discord.Role, interview_channel: discord.TextChannel):
        super().__init__(timeout=None)
        self.guest_role = guest_role
        self.candidate_role = candidate_role
        self.interview_channel = interview_channel

    @discord.ui.button(label="ゲストロールをトグル", style=discord.ButtonStyle.primary, custom_id="rouge_guest_toggle")
    async def guest_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        role = self.guest_role
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Guest role toggle off")
                await interaction.response.send_message("ゲストロールを解除しました。", ephemeral=True)
            else:
                await member.add_roles(role, reason="Guest role toggle on")
                await interaction.response.send_message("ゲストロールを付与しました。ようこそ Rouge Lounge へ。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("権限不足のためロール変更に失敗しました。運営に連絡してください。", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)

    @discord.ui.button(label="キャスト希望ロールをトグル", style=discord.ButtonStyle.secondary, custom_id="rouge_candidate_toggle")
    async def candidate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        role = self.candidate_role
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Candidate role toggle off")
                await interaction.response.send_message("キャスト希望ロールを解除しました。", ephemeral=True)
            else:
                await member.add_roles(role, reason="Candidate role toggle on")
                # 面接用チャンネルの案内（ephemeral）
                mention = self.interview_channel.mention if self.interview_channel else "面接チャンネル"
                msg = (
                    f"キャスト希望ロールを付与しました。\n"
                    f"{mention} に\n"
                    "以下のテンプレで自己紹介を投稿してください：\n\n"
                    "・お名前（呼び名）\n"
                    "・VRChat ID\n"
                    "・活動可能時間（曜日/時間帯）\n"
                    "・得意な雰囲気（例：落ち着き/おしゃべり/ミステリアス etc.）\n"
                    "・ひとこと\n"
                )
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("権限不足のためロール変更に失敗しました。運営に連絡してください。", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)


@bot.event
async def on_ready():
    try:
        # グローバル同期。ギルド限定同期にする場合は guild=discord.Object(GUILD_ID) を指定
        await bot.tree.sync()
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")
        print("App commands synced.")
    except Exception as e:
        print("Command sync failed:", e)


@bot.tree.command(name="setup_roles", description="役職付与パネルを投稿します（運営のみ）")
@app_commands.describe(
    guest_role="『ゲスト』ロールを指定",
    candidate_role="『キャスト希望』ロールを指定",
    interview_channel="『キャスト面接用』テキストチャンネルを指定",
    title="埋め込みタイトル（省略可）",
    description="埋め込み本文（省略可）"
)
async def setup_roles(
    interaction: discord.Interaction,
    guest_role: discord.Role,
    candidate_role: discord.Role,
    interview_channel: discord.TextChannel,
    title: Optional[str] = "役職付与パネル / Rouge Lounge",
    description: Optional[str] = (
        "以下のボタンからロールを付与できます。\n"
        "・『ゲスト』: 一般チャンネルへアクセス\n"
        "・『キャスト希望』: 面接チャンネルで自己紹介をお願いします"
    ),
):
    # 実行者の権限チェック
    if not has_manage_roles(interaction):
        return await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)

    embed = discord.Embed(title=title, description=description)
    embed.set_footer(text="Rouge Lounge")

    view = RolePanelView(guest_role=guest_role, candidate_role=candidate_role, interview_channel=interview_channel)
    await interaction.response.send_message("役職付与パネルを作成しました。", ephemeral=True)
    await interaction.channel.send(embed=embed, view=view)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(".env の DISCORD_TOKEN が見つかりません。設定してください。")

    bot.run(TOKEN)
