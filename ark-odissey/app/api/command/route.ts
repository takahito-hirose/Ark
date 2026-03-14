import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const { command } = await req.json();

    // 🌟 FastAPIバックエンド (ポート8000) にリクエストを転送（プロキシ）
    const response = await fetch('http://127.0.0.1:8000/api/command', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ command }),
    });

    if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error: any) {
    return NextResponse.json(
      { message: `API Proxy Error: ${error.message}`, level: 'error' },
      { status: 500 }
    );
  }
}