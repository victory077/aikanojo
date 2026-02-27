"""LLMクライアントモジュール - OpenAI互換APIへの接続を管理"""
import json
import re
from openai import OpenAI


class LLMClient:
    """LM Studio等のOpenAI互換APIクライアント

    LLM呼び出しを一元管理し、将来的な複数モデル切替に備える。
    """

    def __init__(self, base_url: str, api_key: str, model: str):
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def chat(self, system_prompt: str, user_message: str,
             temperature: float = 0.7, max_tokens: int | None = None) -> str:
        """システムプロンプト + ユーザーメッセージでLLMに問い合わせる

        Returns:
            LLMの応答テキスト
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def simple(self, prompt: str,
               temperature: float = 0.3, max_tokens: int | None = None) -> str:
        """ユーザーメッセージのみでLLMに問い合わせる（感情分析、記憶更新等）

        Returns:
            LLMの応答テキスト
        """
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def analyze_sentiment(self, user_message: str) -> int:
        """メッセージの感情分析を行い、好感度変動値(-5〜+5)を返す"""
        system_prompt = """あなたはメッセージの感情分析をするAIです。
ユーザーのメッセージが「優しい・褒め言葉・好意的」か「普通」か「ひどい・侮辱的・攻撃的」かを判定し、
好感度の変動値を-5から+5の整数で返してください。

判定基準:
- +5: とても優しい、愛情表現、褒め言葉
- +3: 優しい、気遣い、励まし
- +1: 普通の会話、質問
- -1: 少し失礼、からかい
- -3: 失礼、批判的
- -5: 非常にひどい、侮辱、暴言

JSONフォーマットで回答: {"score": 数値, "reason": "理由"}"""

        try:
            result_text = self.chat(system_prompt, user_message, temperature=0.3)
            json_match = re.search(r'\{[^}]+\}', result_text)
            if json_match:
                result = json.loads(json_match.group())
                score = int(result.get("score", 1))
                return max(-5, min(5, score))
        except Exception as e:
            print(f"感情分析エラー: {e}")

        return 1  # デフォルトは+1
