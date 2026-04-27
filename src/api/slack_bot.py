"""
ARK — Slack Relay Server (次元の門)
====================================================
Phase 13.5: Interactive Model Selection
外界(Slack)とARKを安全に繋ぐSocket Modeコネクター。
指示受信時のモデル選択UI、承認フロー、継続提案を担当します。
"""

import os
import re
import uuid
import logging
import asyncio
import urllib.request
import json
from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

load_dotenv()

log = logging.getLogger("ARK.SlackBot")

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")

app = AsyncApp(token=SLACK_BOT_TOKEN)

_on_command_callback = None
_on_approval_callback = None
_last_channel_id = None

# 次の航海のための文脈
_last_proposal_context = {}
_last_providers = {}

# モデル選択待ちのミッションを一時保存する辞書
_pending_missions = {}

def get_dynamic_models():
    """OllamaのAPIを叩いて動的にモデルリストを生成する"""
    options = [
        {"text": {"type": "plain_text", "text": "Gemini 2.5 Flash"}, "value": "gemini-2.5-flash"},
        {"text": {"type": "plain_text", "text": "Gemini 2.5 Pro"}, "value": "gemini-2.5-Pro"},
        {"text": {"type": "plain_text", "text": "GPT-4o (OpenAI)"}, "value": "gpt-4o"},
        {"text": {"type": "plain_text", "text": "Claude 3.5 Sonnet"}, "value": "claude-3.5-sonnet"}
    ]
    
    ollama_options = []
    try:
        # ローカルのOllamaサーバーからタグ一覧を取得
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            for model in data.get("models", []):
                model_name = model["name"]
                ollama_options.append({
                    "text": {"type": "plain_text", "text": f"🦙 Ollama ({model_name})"},
                    "value": f"ollama|{model_name}"
                })
    except Exception as e:
        log.warning(f"⚠️ [SlackBot] Ollama API接続エラー (ローカルモデルはフォールバックを使用します): {e}")
        # 取得失敗時はデフォルト設定を追加
        ollama_options.append({"text": {"type": "plain_text", "text": "Ollama (Local Default)"}, "value": "ollama"})
    
    # Ollamaのモデルをリストの先頭に追加
    options = ollama_options + options
    
    # Slackの選択肢上限(100件)を超えないように安全対策
    return options[:100]

def set_slack_callbacks(command_cb, approval_cb):
    global _on_command_callback, _on_approval_callback
    _on_command_callback = command_cb
    _on_approval_callback = approval_cb

@app.event("app_mention")
async def handle_app_mention(event, say):
    global _last_channel_id, _last_providers
    _last_channel_id = event.get("channel")
    user = event.get("user")
    text = event.get("text", "")
    
    command = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
    
    auto_approve = "--auto" in command
    command = command.replace("--auto", "").strip()
    
    providers = {}
    has_inline_provider = False
    for role in ["architect", "coder", "reviewer", "reflector"]:
        pattern = rf"--{role}\s+([a-zA-Z0-9_:\.-]+)"
        match = re.search(pattern, command)
        if match:
            providers[f"{role}_provider"] = match.group(1)
            command = re.sub(pattern, "", command).strip()
            has_inline_provider = True
            
    if not command:
        await say(f"<@{user}> ご主人様！指示内容が空のようです！")
        return

    # コマンド内にプロバイダー指定が1つでもあれば、スキップして即実行
    if has_inline_provider:
        _last_providers = providers
        log.info(f"📨 [Slack] Command with inline providers: {command} (Providers: {providers})")
        await say(f"<@{user}> ⚓️ 指定されたモデルで指令を受信しました！計画策定に入ります。\n> *{command}*")
        if _on_command_callback:
            await _on_command_callback(command, auto_approve, None, providers)
        return

    # 指定がない場合は、確認UIを表示するために一時保存
    mission_id = str(uuid.uuid4())
    _pending_missions[mission_id] = {
        "user": user,
        "command": command,
        "auto_approve": auto_approve,
        "workspace_path": None,
        "providers": {
            "architect_provider": "ollama",
            "coder_provider": "ollama",
            "reviewer_provider": "ollama",
            "reflector_provider": "ollama"
        }
    }

    # 動的に最新のモデル一覧を取得！
    dynamic_models = get_dynamic_models()

    # Slackにモデル選択のUIを送信
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"<@{user}> 指令を受け付けました！各工程で使用するモデルを選んでください。\n> *{command}*"}
        },
        {
            "type": "actions",
            "block_id": f"models_{mission_id}",
            "elements": [
                {
                    "type": "static_select",
                    "action_id": "select_model_architect",
                    "placeholder": {"type": "plain_text", "text": "Architect (Plan)"},
                    "options": dynamic_models,
                    "initial_option": dynamic_models[0]
                },
                {
                    "type": "static_select",
                    "action_id": "select_model_coder",
                    "placeholder": {"type": "plain_text", "text": "Coder (Write)"},
                    "options": dynamic_models,
                    "initial_option": dynamic_models[0]
                }
            ]
        },
        {
            "type": "actions",
            "block_id": f"models2_{mission_id}",
            "elements": [
                {
                    "type": "static_select",
                    "action_id": "select_model_reviewer",
                    "placeholder": {"type": "plain_text", "text": "Reviewer (Check)"},
                    "options": dynamic_models,
                    "initial_option": dynamic_models[0]
                },
                {
                    "type": "static_select",
                    "action_id": "select_model_reflector",
                    "placeholder": {"type": "plain_text", "text": "Reflector (Fix)"},
                    "options": dynamic_models,
                    "initial_option": dynamic_models[0]
                }
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "出撃する！"},
                    "style": "primary",
                    "action_id": "launch_mission_with_selected_models",
                    "value": mission_id
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "キャンセル"},
                    "style": "danger",
                    "action_id": "cancel_mission_setup",
                    "value": mission_id
                }
            ]
        }
    ]
    
    await say(text="モデル選択", blocks=blocks)

# モデル選択のドロップダウンが変更されたときの処理
@app.action(re.compile("select_model_.*"))
async def handle_model_selection(ack, body, action):
    await ack()
    action_id = action.get("action_id")
    selected_option = action.get("selected_option", {}).get("value")
    block_id = action.get("block_id", "")
    
    # block_id から mission_id を抽出 (models_UUID または models2_UUID)
    mission_id = block_id.replace("models_", "").replace("models2_", "")
    
    role = action_id.split("_")[-1] # architect, coder, reviewer, reflector
    provider_key = f"{role}_provider"
    
    if mission_id in _pending_missions:
        _pending_missions[mission_id]["providers"][provider_key] = selected_option
        log.info(f"Updated {provider_key} to {selected_option} for mission {mission_id}")

# 選択したモデルで出撃するボタンの処理
@app.action("launch_mission_with_selected_models")
async def handle_launch_with_models(ack, body, respond):
    await ack()
    action = body["actions"][0]
    mission_id = action.get("value")
    
    mission = _pending_missions.get(mission_id)
    if not mission:
        await respond(text="エラー：ミッション情報が見つかりません。タイムアウトした可能性があります。", replace_original=True)
        return
        
    global _last_providers
    _last_providers = mission["providers"]
    
    # 選択メニューを消して、出撃メッセージに置き換える
    await respond(text=f"⚓️ モデル設定完了！以下の構成で計画の策定に入ります。\nArchitect: `{_last_providers['architect_provider']}`\nCoder: `{_last_providers['coder_provider']}`", replace_original=True)
    
    if _on_command_callback:
        await _on_command_callback(
            mission["command"],
            mission["auto_approve"],
            mission["workspace_path"],
            mission["providers"]
        )
        
    del _pending_missions[mission_id]

# キャンセルボタンの処理
@app.action("cancel_mission_setup")
async def handle_cancel_setup(ack, body, respond):
    await ack()
    action = body["actions"][0]
    mission_id = action.get("value")
    
    if mission_id in _pending_missions:
        del _pending_missions[mission_id]
        
    await respond(text="ミッションのセットアップをキャンセルしました。", replace_original=True)


# --- 以下の承認待ち・提案の処理は以前と同じ ---

async def send_slack_message(text: str):
    if not _last_channel_id:
        return
    try:
        await app.client.chat_postMessage(channel=_last_channel_id, text=text)
    except Exception as e:
        log.error(f"❌ [Slack] Failed to send message: {e}")

async def send_slack_approval_message(plan_data: dict):
    if not _last_channel_id:
        return
        
    goal_text = plan_data.get("goal", "No Goal specified.")
    tasks = plan_data.get("tasks", [])
    task_list_str = "\n".join([f"• {t.get('title', 'Task')}" for t in tasks])

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
                    "text": {"type": "plain_text", "text": "Approve (出撃)"},
                    "style": "primary",
                    "action_id": "approve_plan"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Reject (却下)"},
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
    global _last_proposal_context
    if not _last_channel_id:
        return

    goal = proposal_data.get("next_goal") or proposal_data.get("goal", "")
    artifacts = ", ".join(proposal_data.get("artifacts", []))
    risks = proposal_data.get("risks", "")
    workspace_path = proposal_data.get("workspace_path")

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
                    "text": {"type": "plain_text", "text": "提案を採用して継続"},
                    "style": "primary",
                    "action_id": "launch_next_mission"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "キャンセル"},
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
        await respond(text="エラー：提案内容を見失いました。もう一度メンションで指示をお願いします。", replace_original=True)
        return

    await respond(text="提案を採用しました！同じドック（環境）で次のミッションを開始します！", replace_original=True)
    if _on_command_callback:
        await _on_command_callback(
            command,
            False,
            _last_proposal_context.get("workspace_path"),
            _last_providers
        )

@app.action("cancel_next_mission")
async def handle_cancel_next(ack, body, respond):
    await ack()
    await respond(text="提案をキャンセルしました。次の指示をお待ちしています！", replace_original=True)

async def start_slack_bot():
    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        log.warning("⚠️ [Slack] トークンが見つかりません。")
        return
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)
    log.info("🔌 [Slack] Connecting to Neuro-Link (Socket Mode)...")
    await handler.start_async()