import { NextResponse } from 'next/server';

/**
 * 🧠 繋ぎ込みテスト用 APIエンドポイント
 * フロントエンドからのコマンドを受け取って、処理結果を返すよ！
 */
export async function POST(req: Request) {
  try {
    const { command } = await req.json();

    // 本当はここで OpenAI や FastAPI（Pythonバックエンド） にリクエストを投げる！
    // 今回は「考えてる感」を出すために、わざと1.5秒待機させるね💋
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // AIからのモック返答を生成
    const mockResponse = `「${command}」の指示を受信したよ！現在の環境に反映中...`;
    
    // 適当に消費トークンを計算（文字数ベースでそれっぽく）
    const tokensUsed = command.length * 2 + Math.floor(Math.random() * 20);

    return NextResponse.json({
      message: mockResponse,
      tokens: tokensUsed,
      level: 'success'
    });
    
  } catch (error) {
    return NextResponse.json(
      { message: 'コマンドの解析に失敗しちゃった💦', level: 'error' },
      { status: 500 }
    );
  }
}