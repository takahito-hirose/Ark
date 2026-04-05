"""
ARK — Slack Relay Server (次元の門)
====================================================
Phase 13: ARK Remote Command
外界(Slack)とARKを安全に繋ぐSocket Modeコネクター。
コマンドの解析、承認フロー、および継続航海の提案を担当します。
"""

import os
import re
import logging
import asyncio
from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

# ここで確実に .env を読み込みます！
load_dotenv()

log = logging.getLogger("ARK.SlackBot")

# トークンの読み込み
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")

app = AsyncApp(token=SLACK_BOT_TOKEN)

# Orchestratorとやり取りするためのコールバック関数と状態保持
_on_command_callback = None
_on_approval_callback = None
_last_channel_id = None
_last_proposal_context = {}  # 次の航海のための文脈（目標とワークスペースパス）を保持

def set_slack_callbacks(command_cb, approval_cb):
    """main.pyからARKのコア機能を注入するためのセットアップ関数"""
    global _on_command_callback, _on_approval_callback
    _on_command_callback = command_cb
    _on_approval_callback = approval_cb

# メンションされた時のイベントリスナー
@app.event("app_mention")
async def handle_app_mention(event, say):
    """メンションをキャッチし、新規コマンドとしてARKへ流し込む"""
    global _last_channel_id
    _last_channel_id = event.get("channel")
    user = event.get("user")
    text = event.get("text", "")
    
    command = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
    auto_approve = "--auto" in command
    command = command.replace("--auto", "").strip()
    
    log.info(f"📨 [Slack] Received command from {user}: {command}")
    
    if not command:
        await say(f"<@{user}> ご主人様！指示内容が空のようです！")
        return
        
    await say(f"<@{user}> ⚓️ 司令を受信しました！計画（Plan）の策定に入ります。\n> *{command}*")
    
    if _on_command_callback:
        # 新規プロジェクトとして起動するため workspace_path は None
        await _on_command_callback(command, auto_approve, None)

async def send_slack_message(text: str):
    """シンプルなメッセージをSlackに送る関数（PR通知用など）"""
    if not _last_channel_id:
        return
    try:
        await app.client.chat_postMessage(channel=_last_channel_id, text=text)
    except Exception as e:
        log.error(f"❌ [Slack] Failed to send message: {e}")

async def send_slack_approval_message(plan_data: dict):
    """Architectの設計図をSlackに送信し、承認ボタンを表示する"""
    if not _last_channel_id:
        return
        
    goal_text = plan_data.get("goal", "No Goal specified.")
    tasks = plan_data.get("tasks", [])
    task_list_str = "\n".join([f"• {t.get('title', 'Task')}" for t in tasks])

    # Slackの文字数制限（3000文字）対策
    if len(goal_text) > 1500: goal_text = goal_text[:1500] + "\n\n... (省略)"
    if len(task_list_str) > 800: task_list_str = task_list_str[:800] + "\n... (省略)"
    if not task_list_str: task_list_str = "単一タスク、または分割不要。"

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "📝 *ミッション・プランの承認待ち*"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*【指令】*\n```\n{goal_text}\n```\n*【タスク (WBS)】*\n```\n{task_list_str}\n```"}
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Approve (出撃)", "emoji": True},
                    "style": "primary",
                    "action_id": "approve_plan"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Reject (却下)", "emoji": True},
                    "style": "danger",
                    "action_id": "reject_plan"
                }
            ]
        }
    ]
    
    try:
        await app.client.chat_postMessage(channel=_last_channel_id, text="プラン承認待ち", blocks=blocks)
    except Exception as e:
        log.error(f"❌ [Slack] Failed to send approval message: {e}")

async def send_slack_next_proposal_message(proposal_data: dict):
    """完了後に提案される次のタスクをSlackに表示し、継続実行を促す"""
    global _last_proposal_context
    if not _last_channel_id:
        return

    # 🌟 FIX: ここを "next_goal" から取得するように修正！
    goal = proposal_data.get("next_goal") or proposal_data.get("goal", "")
    artifacts = ", ".join(proposal_data.get("artifacts", []))
    risks = proposal_data.get("risks", "")
    workspace_path = proposal_data.get("workspace_path")

    # 継続航海のためにコンテキストを保存
    _last_proposal_context = {
        "command": goal,
        "workspace_path": workspace_path
    }

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "🧭 *次なる航路の提案 (Next Course Proposal)*"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*【Target Goal】*\n```\n{goal}\n```"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*【Expected Artifacts】*\n{artifacts}\n\n*【Identified Risks】*\n{risks}"}
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🚀 提案を採用して継続", "emoji": True},
                    "style": "primary",
                    "action_id": "launch_next_mission"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🛑 キャンセル", "emoji": True},
                    "style": "danger",
                    "action_id": "cancel_next_mission"
                }
            ]
        }
    ]
    try:
        await app.client.chat_postMessage(channel=_last_channel_id, text="次なる航路の提案", blocks=blocks)
    except Exception as e:
        log.error(f"❌ [Slack] Failed to send next proposal: {e}")

# --- ボタンアクション群 ---

@app.action("approve_plan")
async def handle_approve(ack, body, respond):
    await ack()
    await respond(text="✅ *承認完了！大艦隊が出撃します！*", replace_original=True)
    if _on_approval_callback: _on_approval_callback(True)

@app.action("reject_plan")
async def handle_reject(ack, body, respond):
    await ack()
    await respond(text="❌ *却下しました。*", replace_original=True)
    if _on_approval_callback: _on_approval_callback(False)

@app.action("launch_next_mission")
async def handle_launch_next(ack, body, respond):
    await ack()
    command = _last_proposal_context.get("command")
    if not command:
        await respond(text="⚠️ エラー: 提案内容を見失いました。もう一度メンションで指示をお願いします。", replace_original=True)
        return

    await respond(text="🚀 *提案を採用しました！同じドック（環境）で次のミッションを開始します！*", replace_original=True)
    if _on_command_callback:
        # 既存のワークスペースパスを引き継いで実行する！
        await _on_command_callback(
            command,
            False,
            _last_proposal_context.get("workspace_path")
        )

@app.action("cancel_next_mission")
async def handle_cancel_next(ack, body, respond):
    await ack()
    await respond(text="🛑 *提案をキャンセルしました。* 次の指示をお待ちしています！", replace_original=True)

async def start_slack_bot():
    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        log.warning("⚠️ [Slack] トークンが見つかりません。")
        return
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)
    log.info("🔌 [Slack] Connecting to Neuro-Link (Socket Mode)...")
    await handler.start_async()