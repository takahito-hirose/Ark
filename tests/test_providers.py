"""
ARK — Provider Tests
=====================
MockProvider を使用した接続不要のオフラインテスト。
外部LLM（Ollama/Gemini）への接続を一切行わず実行できる。

Run:
    python -m pytest tests/test_providers.py -v
"""

from __future__ import annotations

import unittest

from src.core.config import ARKConfig, ConfigLoader
from src.core.factory import get_provider, list_providers
from src.core.providers import (
    BaseProvider,
    GeminiProvider,
    MockProvider,
    OllamaProvider,
)


# ===========================================================================
# TestBaseProviderContract: インターフェース準拠チェック
# ===========================================================================

class TestBaseProviderContract(unittest.TestCase):
    """BaseProvider のコントラクト（契約）を検証するテスト群。"""

    def test_mock_is_subclass_of_base(self) -> None:
        """MockProvider は BaseProvider の具象サブクラスであること。"""
        self.assertTrue(issubclass(MockProvider, BaseProvider))

    def test_ollama_is_subclass_of_base(self) -> None:
        """OllamaProvider は BaseProvider の具象サブクラスであること。"""
        self.assertTrue(issubclass(OllamaProvider, BaseProvider))

    def test_gemini_is_subclass_of_base(self) -> None:
        """GeminiProvider は BaseProvider の具象サブクラスであること。"""
        self.assertTrue(issubclass(GeminiProvider, BaseProvider))

    def test_base_provider_is_abstract(self) -> None:
        """BaseProvider は直接インスタンス化できないこと（ABCであること）。"""
        with self.assertRaises(TypeError):
            BaseProvider()  # type: ignore[abstract]


# ===========================================================================
# TestMockProvider: MockProvider の動作検証
# ===========================================================================

class TestMockProvider(unittest.TestCase):
    """MockProvider の動作を検証するテスト群。外部接続不要。"""

    def setUp(self) -> None:
        self.provider = MockProvider()

    def test_generate_returns_string(self) -> None:
        """generate() は str を返すこと。"""
        result = self.provider.generate("テスト用プロンプト")
        self.assertIsInstance(result, str)

    def test_generate_never_returns_none(self) -> None:
        """generate() は None を返さないこと。"""
        result = self.provider.generate("None返却テスト")
        self.assertIsNotNone(result)

    def test_generate_returns_nonempty_string(self) -> None:
        """generate() は空文字列以外を返すこと。"""
        result = self.provider.generate("空文字列テスト")
        self.assertGreater(len(result), 0)

    def test_generate_includes_mock_marker(self) -> None:
        """デフォルトレスポンスには [MOCK RESPONSE] マーカーが含まれること。"""
        result = self.provider.generate("マーカーテスト")
        self.assertIn("[MOCK RESPONSE]", result)

    def test_generate_embeds_prompt(self) -> None:
        """プロンプトがレスポンスに埋め込まれること。"""
        prompt = "ユニークなプロンプト文字列_12345"
        result = self.provider.generate(prompt)
        self.assertIn(prompt, result)

    def test_long_prompt_is_truncated(self) -> None:
        """100文字超のプロンプトは省略記号付きで切り詰められること。"""
        long_prompt = "あ" * 200
        result = self.provider.generate(long_prompt)
        self.assertIn("...", result)

    def test_custom_template(self) -> None:
        """カスタムテンプレート指定時はそのテンプレートが使われること。"""
        provider = MockProvider(response_template="CUSTOM: {prompt}")
        result = provider.generate("test")
        self.assertEqual(result, "CUSTOM: test")

    def test_is_instance_of_base_provider(self) -> None:
        """MockProvider インスタンスは BaseProvider のインスタンスであること。"""
        self.assertIsInstance(self.provider, BaseProvider)

    def test_repr(self) -> None:
        """__repr__ が適切な文字列を返すこと。"""
        self.assertIn("MockProvider", repr(self.provider))


# ===========================================================================
# TestGeminiProviderStub: GeminiProvider の雛形検証
# ===========================================================================

class TestGeminiProviderStub(unittest.TestCase):
    """GeminiProvider の雛形（APIキー未設定）挙動を検証するテスト群。"""

    def test_gemini_instantiation_without_key(self) -> None:
        """APIキーなしでもインスタンス化はできること（generate()時にエラー）。"""
        provider = GeminiProvider(api_key="", model_name="gemini-1.5-flash")
        self.assertIsInstance(provider, BaseProvider)

    def test_gemini_generate_raises_without_package(self) -> None:
        """google-generativeaiまたはAPIキーなしでgenerate()はRuntimeErrorを送出すること。"""
        provider = GeminiProvider(api_key="", model_name="gemini-1.5-flash")
        with self.assertRaises(RuntimeError):
            provider.generate("テスト")

    def test_gemini_repr(self) -> None:
        """__repr__ が適切な文字列を返すこと。"""
        provider = GeminiProvider(model_name="gemini-1.5-flash")
        self.assertIn("GeminiProvider", repr(provider))
        self.assertIn("gemini-1.5-flash", repr(provider))


# ===========================================================================
# TestGetProvider: ファクトリー関数の検証
# ===========================================================================

class TestGetProvider(unittest.TestCase):
    """get_provider() ファクトリー関数を検証するテスト群。"""

    def setUp(self) -> None:
        """ARKConfig を mock プロバイダー設定でロードする。"""
        # ConfigLoader.load() を経由してデフォルト設定を取得しつつ
        # プロバイダーをすべて "mock" に上書きする
        self.cfg = ConfigLoader.load()
        self.cfg.architect_provider = "mock"
        self.cfg.coder_provider = "mock"
        self.cfg.reviewer_provider = "mock"
        # 新しく追加したモデル設定も一応 mock ではデフォルトのままにするか、明示的に設定
        self.cfg.architect_model = "gemini-3.1-pro"
        self.cfg.coder_model = "gemini-3-flash"
        self.cfg.reviewer_model = "gemini-3-flash"

    def test_get_provider_architect_returns_mock(self) -> None:
        """get_provider('architect') が MockProvider を返すこと。"""
        provider = get_provider("architect", self.cfg)
        self.assertIsInstance(provider, MockProvider)

    def test_get_provider_coder_returns_mock(self) -> None:
        """get_provider('coder') が MockProvider を返すこと。"""
        provider = get_provider("coder", self.cfg)
        self.assertIsInstance(provider, MockProvider)

    def test_get_provider_reviewer_returns_mock(self) -> None:
        """get_provider('reviewer') が MockProvider を返すこと。"""
        provider = get_provider("reviewer", self.cfg)
        self.assertIsInstance(provider, MockProvider)

    def test_get_provider_returns_base_provider_instance(self) -> None:
        """get_provider() の戻り値は BaseProvider のインスタンスであること。"""
        provider = get_provider("architect", self.cfg)
        self.assertIsInstance(provider, BaseProvider)

    def test_get_provider_mock_can_generate(self) -> None:
        """get_provider() で取得した MockProvider が generate() できること。"""
        provider = get_provider("architect", self.cfg)
        result = provider.generate("設計を考えよ")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_get_provider_unknown_role_raises(self) -> None:
        """未知のロール名で ValueError が送出されること。"""
        with self.assertRaises(ValueError) as ctx:
            get_provider("unknown_role", self.cfg)
        self.assertIn("unknown_role", str(ctx.exception))

    def test_get_provider_unknown_provider_name_raises(self) -> None:
        """未知のプロバイダー名で ValueError が送出されること。"""
        self.cfg.architect_provider = "nonexistent_llm"  # type: ignore[assignment]
        with self.assertRaises(ValueError) as ctx:
            get_provider("architect", self.cfg)
        self.assertIn("nonexistent_llm", str(ctx.exception))

    def test_get_provider_case_insensitive_role(self) -> None:
        """ロール名は大文字小文字を区別しないこと。"""
        provider_lower = get_provider("architect", self.cfg)
        provider_upper = get_provider("ARCHITECT", self.cfg)
        self.assertEqual(type(provider_lower), type(provider_upper))

    def test_list_providers_returns_expected(self) -> None:
        """list_providers() が登録済みプロバイダー名を返すこと。"""
        providers = list_providers()
        self.assertIn("ollama", providers)
        self.assertIn("mock", providers)
        self.assertIn("gemini", providers)


# ===========================================================================
# TestFullMockWorkflow: MockProvider を使った疑似エンドツーエンドテスト
# ===========================================================================

class TestFullMockWorkflow(unittest.TestCase):
    """
    LLMへの接続を一切行わずに、Architect/Coder/Reviewer の
    全エージェントが動作できることを確認するテスト。
    """

    def _make_mock_cfg(self) -> "ARKConfig":
        cfg = ConfigLoader.load()
        cfg.architect_provider = "mock"
        cfg.coder_provider = "mock"
        cfg.reviewer_provider = "mock"
        return cfg

    def test_all_agents_can_generate_without_connection(self) -> None:
        """MockProvider設定で全エージェントが接続なしにgenerate()できること。"""
        cfg = self._make_mock_cfg()

        architect = get_provider("architect", cfg)
        coder     = get_provider("coder", cfg)
        reviewer  = get_provider("reviewer", cfg)

        # 各エージェントが generate() を呼べること
        plan_text   = architect.generate("Pythonで Hello World アプリを設計せよ")
        code_text   = coder.generate(f"以下の設計に基づいてコードを生成せよ:\n{plan_text[:200]}")
        review_text = reviewer.generate(f"以下のコードをレビューせよ:\n{code_text[:200]}")

        for role, result in [
            ("architect", plan_text),
            ("coder", code_text),
            ("reviewer", review_text),
        ]:
            with self.subTest(role=role):
                self.assertIsInstance(result, str, f"{role} の generate() が str を返さなかった")
                self.assertGreater(len(result), 0, f"{role} の generate() が空文字列を返した")

    def test_mock_provider_is_deterministic(self) -> None:
        """MockProvider は同一プロンプトで同一結果を返すこと。"""
        cfg = self._make_mock_cfg()
        provider = get_provider("architect", cfg)
        prompt = "同一プロンプトテスト"

        result1 = provider.generate(prompt)
        result2 = provider.generate(prompt)
        self.assertEqual(result1, result2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
