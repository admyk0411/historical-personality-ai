import base64
import hashlib
import hmac
import io
import json
import math
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ONE-COPY EDITION
# 運営者メールアドレスをコード内に設定済み。
# GitHubが公開リポジトリの場合、このメールアドレスも閲覧可能です。

# ============================================================
# 歴史上の人物 性格診断 — Ultimate Edition
# 100問 / 5択 / 10軸 / 20人物（男性10・女性10）
#
# 設計方針
# - OpenAI API不要（APIクレジット切れで診断停止しない）
# - 生IPは保存しない。HMAC-SHA256の擬似識別子のみ保存
# - 100問の回答を各軸に数値化し、20人物から必ず1人に確定
# - 診断理由 / 強み / 注意点 / 向いている仕事 / 相性タイプ
# - 結果画像（SNSカード）を自動生成
# - X / LINE / Facebook 共有導線
# - JSON保存
# - SQLite保存 + Supabase REST保存（設定時のみ）
# - 広告/スポンサー枠を設定でON/OFF可能
# ============================================================

st.set_page_config(
    page_title="歴史上の人物 性格診断｜100問でわかるあなたの偉人タイプ",
    page_icon="🏛️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

APP_NAME = "歴史上の人物 性格診断"
APP_VERSION = "3.0"
DB_PATH = "diagnosis_results.db"

# ------------------------------------------------------------
# Secrets helper
# ------------------------------------------------------------
def secret(name: str, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

IP_HASH_SALT = str(secret("IP_HASH_SALT", "CHANGE-ME-BEFORE-PUBLIC-RELEASE"))
APP_URL = str(secret("APP_URL", "https://historical-personality-ai-gujhfwuepxfoohbvrubhmw.streamlit.app/")).rstrip("/") + "/"
SUPABASE_URL = str(secret("SUPABASE_URL", "")).rstrip("/")
SUPABASE_KEY = str(secret("SUPABASE_KEY", ""))
ADS_ENABLED = str(secret("ADS_ENABLED", "false")).lower() in ("1", "true", "yes", "on")
ADS_HTML_TOP = str(secret("ADS_HTML_TOP", ""))
ADS_HTML_RESULT = str(secret("ADS_HTML_RESULT", ""))
SPONSOR_TEXT = str(secret("SPONSOR_TEXT", ""))
SPONSOR_URL = str(secret("SPONSOR_URL", ""))
ADMIN_EMAIL = "vwzaz39528@yahoo.co.jp"
CONTACT_EMAIL = "vwzaz39528@yahoo.co.jp"
PRIVACY_POLICY_URL = str(secret("PRIVACY_POLICY_URL", "")).strip()
TERMS_URL = str(secret("TERMS_URL", "")).strip()

# ------------------------------------------------------------
# Design tokens
# ------------------------------------------------------------
CSS = """
<style>
:root {
  --card-radius: 22px;
}
.block-container {
  max-width: 940px;
  padding-top: 1.6rem;
  padding-bottom: 5rem;
}
.hero {
  border: 1px solid rgba(127,127,127,.22);
  border-radius: 26px;
  padding: 1.6rem 1.7rem 1.4rem 1.7rem;
  margin-bottom: 1rem;
  background:
    radial-gradient(circle at 85% 15%, rgba(210,167,90,.12), transparent 32%),
    radial-gradient(circle at 10% 90%, rgba(103,126,234,.10), transparent 32%);
}
.hero h1 { margin: 0 0 .3rem 0; line-height: 1.2; }
.hero p { margin: .35rem 0; }
.badge-row { display:flex; gap:.45rem; flex-wrap:wrap; margin-top:.8rem; }
.badge {
  border:1px solid rgba(127,127,127,.24);
  border-radius:999px;
  padding:.26rem .65rem;
  font-size:.86rem;
}
.soft-card {
  border: 1px solid rgba(127,127,127,.22);
  border-radius: var(--card-radius);
  padding: 1.2rem 1.25rem;
  margin: .8rem 0;
}
.result-card {
  border: 1px solid rgba(127,127,127,.24);
  border-radius: 26px;
  padding: 1.25rem;
  margin: 1rem 0 1.3rem 0;
  background:
    linear-gradient(135deg, rgba(199,155,73,.08), rgba(92,111,215,.06));
}
.small { opacity:.74; font-size:.9rem; }
.muted { opacity:.70; }
.center { text-align:center; }
.kicker {
  font-size:.82rem; letter-spacing:.08em; text-transform:uppercase; opacity:.72;
}
.big-number { font-size:1.8rem; font-weight:800; }
.reason {
  border-left: 4px solid rgba(180,140,70,.55);
  padding: .25rem 0 .25rem .9rem;
  margin: .7rem 0;
}
.ad-slot {
  border:1px dashed rgba(127,127,127,.25);
  border-radius:14px;
  padding:.8rem;
  text-align:center;
  opacity:.72;
  font-size:.86rem;
}
div[data-testid="stRadio"] label { line-height: 1.45; }
div[data-testid="stMetricValue"] { font-size: 1.55rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ------------------------------------------------------------
# 10 axes
# Scores are normalized to -100..+100
# ------------------------------------------------------------
AXES = {
    "leadership": {
        "name": "主導性", "low": "協調・支援", "high": "主導・牽引",
        "desc_high": "自分で方向を示し、人や物事を前へ進めやすい",
        "desc_low": "周囲を支え、状況を見ながら力を発揮しやすい",
    },
    "novelty": {
        "name": "挑戦性", "low": "慎重・安定", "high": "挑戦・革新",
        "desc_high": "未知や変化を機会として捉えやすい",
        "desc_low": "再現性や安全性を重視し、堅実に進めやすい",
    },
    "logic": {
        "name": "論理性", "low": "感覚・情緒", "high": "論理・分析",
        "desc_high": "根拠・構造・データを使って考えやすい",
        "desc_low": "直感や人間的な感覚を判断材料にしやすい",
    },
    "social": {
        "name": "社交性", "low": "内省・少人数", "high": "交流・対外",
        "desc_high": "人との交流から情報やエネルギーを得やすい",
        "desc_low": "一人や少人数で深く考えることで力を発揮しやすい",
    },
    "structure": {
        "name": "計画性", "low": "柔軟・即興", "high": "計画・秩序",
        "desc_high": "手順・締切・進捗を整理して進めやすい",
        "desc_low": "状況に合わせて柔軟に変化させやすい",
    },
    "empathy": {
        "name": "共感性", "low": "客観・割り切り", "high": "共感・配慮",
        "desc_high": "人の気持ちや関係性を丁寧に読み取りやすい",
        "desc_low": "感情から距離を取り、基準や結論を優先しやすい",
    },
    "resilience": {
        "name": "精神的安定性", "low": "繊細・反応的", "high": "安定・粘り強い",
        "desc_high": "圧力や失敗の中でも立て直しやすい",
        "desc_low": "変化や周囲の反応を敏感に捉えやすい",
    },
    "independence": {
        "name": "自立性", "low": "協調・周囲重視", "high": "独立・自己決定",
        "desc_high": "自分の基準で考え、意思決定しやすい",
        "desc_low": "周囲との合意や経験者の知見を重視しやすい",
    },
    "idealism": {
        "name": "理想志向", "low": "現実・実利", "high": "理念・理想",
        "desc_high": "意味・使命・未来像を重視しやすい",
        "desc_low": "目の前の成果や実用性を重視しやすい",
    },
    "action": {
        "name": "行動性", "low": "熟考・観察", "high": "即行動・実践",
        "desc_high": "小さく始め、動きながら修正しやすい",
        "desc_low": "情報を集め、見通しを立ててから動きやすい",
    },
}

CHOICES = [
    "強くそう思わない",
    "そう思わない",
    "どちらでもない",
    "そう思う",
    "強くそう思う",
]
CHOICE_SCORES = {
    "強くそう思わない": -2,
    "そう思わない": -1,
    "どちらでもない": 0,
    "そう思う": 1,
    "強くそう思う": 2,
}

# ------------------------------------------------------------
# 100 questions: 10 per axis
# direction 1 = agreement -> positive pole
# direction -1 = reverse scored item
# ------------------------------------------------------------
QUESTION_BANK = {
    "leadership": [
        ("集団では、自分から方向性を示すことが多い。", 1),
        ("重要な場面では、自分が決断役になりたい。", 1),
        ("周囲が迷っていると、自分が先頭に立つことがある。", 1),
        ("責任の重い役割でも、必要なら引き受けられる。", 1),
        ("意見が割れたとき、結論をまとめるのが得意だ。", 1),
        ("自分より他の人に最終判断を任せたいことが多い。", -1),
        ("リーダー役より、支える役のほうが自然だ。", -1),
        ("注目を集める立場はできるだけ避けたい。", -1),
        ("自分の考えを押し出すより、全員に合わせることが多い。", -1),
        ("大きな決断では、誰かに背中を押してもらいたい。", -1),
    ],
    "novelty": [
        ("未知のことでも、面白そうなら試してみたい。", 1),
        ("新しい方法を考えることにワクワクする。", 1),
        ("多少の失敗リスクがあっても挑戦を選ぶことがある。", 1),
        ("変化の多い環境を刺激的だと感じる。", 1),
        ("前例がなくても、合理的なら実行したい。", 1),
        ("実績のある方法を変えるのはなるべく避けたい。", -1),
        ("新しい環境より、慣れた環境のほうが安心する。", -1),
        ("成功確率が読めないことには手を出したくない。", -1),
        ("大きな変化より、小さな改善を積み重ねたい。", -1),
        ("斬新さより、確実性を優先することが多い。", -1),
    ],
    "logic": [
        ("感情より、根拠やデータを優先して判断することが多い。", 1),
        ("複雑な問題を分解して考えるのが好きだ。", 1),
        ("結論を出す前に、原因と結果のつながりを確認する。", 1),
        ("数字や比較材料があると判断しやすい。", 1),
        ("反対意見でも筋が通っていれば受け入れられる。", 1),
        ("理屈より、その場の気持ちを大切にして決めることが多い。", -1),
        ("数字で説明されるより、直感で理解するほうが得意だ。", -1),
        ("細かな分析をすると、かえって決めにくくなる。", -1),
        ("論理的に正しくても、人の気持ちに反するなら選びにくい。", -1),
        ("理由を整理するより、感覚で素早く決めることが多い。", -1),
    ],
    "social": [
        ("初対面の人とも比較的すぐ会話できる。", 1),
        ("人が多い場に行くとエネルギーが出る。", 1),
        ("自分から人に話しかけることが多い。", 1),
        ("新しい人脈を作ることに抵抗が少ない。", 1),
        ("考えを誰かと話しながら整理するのが好きだ。", 1),
        ("一人で過ごす時間のほうが回復できる。", -1),
        ("大人数の集まりの後はかなり疲れる。", -1),
        ("知らない人が多い場所では静かになりやすい。", -1),
        ("自分の考えは、まず一人で整理したい。", -1),
        ("広い人間関係より、少数の深い関係を好む。", -1),
    ],
    "structure": [
        ("予定や締切を先に決めると動きやすい。", 1),
        ("大きな目標は、細かな手順に分けて進める。", 1),
        ("物事を始める前に準備を整えるほうだ。", 1),
        ("ルールや役割が明確な環境は働きやすい。", 1),
        ("進捗を確認しながら計画を修正することが多い。", 1),
        ("予定を細かく決めず、その日の気分で動きたい。", -1),
        ("締切が近づいてから集中することが多い。", -1),
        ("計画より、その場の流れを優先したい。", -1),
        ("整理整頓は必要になったときだけすればよいと思う。", -1),
        ("準備に時間を使うより、まず始めたい。", -1),
    ],
    "empathy": [
        ("相手の立場を想像してから言葉を選ぶことが多い。", 1),
        ("困っている人を見ると放っておきにくい。", 1),
        ("人の表情や声の変化に気づきやすい。", 1),
        ("正しさだけでなく、相手がどう受け取るかも重視する。", 1),
        ("誰かの悩みを聞くと、その気持ちを深く考える。", 1),
        ("感情に配慮しすぎると判断が鈍ると思う。", -1),
        ("人の悩みは本人が解決すべきだと思うことが多い。", -1),
        ("厳しいことでも、必要ならためらわず言える。", -1),
        ("人の気持ちより、公平なルールを優先することが多い。", -1),
        ("共感するより、具体的な解決策を示すほうが得意だ。", -1),
    ],
    "resilience": [
        ("予想外の問題が起きても、比較的冷静でいられる。", 1),
        ("失敗しても、原因を整理して次に切り替えられる。", 1),
        ("長期的な目標に粘り強く取り組める。", 1),
        ("プレッシャーのある場面でも普段に近い判断ができる。", 1),
        ("批判を受けても、必要以上に引きずらないほうだ。", 1),
        ("小さな失敗でも長く気になってしまう。", -1),
        ("予定外の出来事が続くとかなり混乱する。", -1),
        ("人からどう見られているかを強く気にする。", -1),
        ("難しい状況が続くと、諦めたくなりやすい。", -1),
        ("強いプレッシャーの下では判断力が落ちやすい。", -1),
    ],
    "independence": [
        ("周囲と違っても、自分が正しいと思えば意見を言える。", 1),
        ("一人でも必要な判断を進められる。", 1),
        ("他人の評価より、自分の基準を大切にしている。", 1),
        ("自分で調べて結論を出すことが好きだ。", 1),
        ("多数派でなくても、自分の信念を維持できる。", 1),
        ("周囲の意見と違うと、自分の考えに自信がなくなる。", -1),
        ("決断するときは、できるだけ誰かに確認したい。", -1),
        ("人から反対されると、考えを変えることが多い。", -1),
        ("自分だけ別の行動を取るのは避けたい。", -1),
        ("自分の判断より、経験者の判断に従うほうが安心だ。", -1),
    ],
    "idealism": [
        ("目先の利益より、長期的に意味のあることを選びたい。", 1),
        ("社会や組織をより良くする理想を持っている。", 1),
        ("困難でも、価値があると思うことには挑みたい。", 1),
        ("仕事には収入以外の使命や意味も求めたい。", 1),
        ("現状に満足せず、より良い未来を構想することが多い。", 1),
        ("理想より、今すぐ得られる実利を優先することが多い。", -1),
        ("大きな理念より、目の前の現実対応のほうが大切だ。", -1),
        ("世の中を変えるより、自分の生活を安定させたい。", -1),
        ("高い理想は、現実では役に立たないことが多いと思う。", -1),
        ("意味より、効率や結果を優先して選ぶことが多い。", -1),
    ],
    "action": [
        ("良い案を思いついたら、まず小さく試してみる。", 1),
        ("考え続けるより、行動しながら修正するほうだ。", 1),
        ("必要な場面では素早く決断できる。", 1),
        ("チャンスだと思ったら、早めに動く。", 1),
        ("準備が完璧でなくても、十分なら始められる。", 1),
        ("情報が十分そろうまで、行動を待つことが多い。", -1),
        ("失敗を避けるため、何度も考えてから動く。", -1),
        ("急いで決めるより、時間をかけて検討したい。", -1),
        ("新しいことは、他の人の様子を見てから始めたい。", -1),
        ("行動する前に、ほぼ確実な見通しがほしい。", -1),
    ],
}
QUESTIONS = [
    {"axis": axis, "text": text, "direction": direction}
    for axis, items in QUESTION_BANK.items()
    for text, direction in items
]
assert len(QUESTIONS) == 100

# ------------------------------------------------------------
# 20 figures: 10 men, 10 women
# These are editorial diagnosis profiles, not psychological facts.
# ------------------------------------------------------------
FIGURES = [
    {
        "name":"織田信長","roman":"ODA NOBUNAGA","gender":"男性","symbol":"⚔","era":"戦国時代",
        "tagline":"常識を壊し、決断で時代を動かす革新リーダー",
        "profile":{"leadership":95,"novelty":95,"logic":55,"social":35,"structure":20,"empathy":-45,"resilience":75,"independence":90,"idealism":45,"action":95},
        "strengths":["大胆な意思決定","既存ルールを疑う革新性","変化局面での推進力"],
        "watchouts":["結論を急ぎすぎる","周囲への配慮が後回しになりやすい"],
        "jobs":["起業家","新規事業開発","事業責任者","プロダクト責任者"],
        "motif":"flame",
    },
    {
        "name":"徳川家康","roman":"TOKUGAWA IEYASU","gender":"男性","symbol":"🏯","era":"戦国〜江戸",
        "tagline":"長期戦に強く、勝ち筋を積み上げる安定型ストラテジスト",
        "profile":{"leadership":75,"novelty":-40,"logic":80,"social":20,"structure":95,"empathy":15,"resilience":95,"independence":60,"idealism":10,"action":20},
        "strengths":["長期視点","リスク管理","粘り強い計画遂行"],
        "watchouts":["慎重さが強すぎると機会を逃す","変化の初動が遅くなりやすい"],
        "jobs":["経営企画","PMO","リスク管理","プロジェクトマネージャー"],
        "motif":"castle",
    },
    {
        "name":"坂本龍馬","roman":"SAKAMOTO RYOMA","gender":"男性","symbol":"🌊","era":"幕末",
        "tagline":"人と人をつなぎ、新しい未来を動かす変革コネクター",
        "profile":{"leadership":65,"novelty":90,"logic":45,"social":90,"structure":-20,"empathy":65,"resilience":65,"independence":80,"idealism":85,"action":90},
        "strengths":["人脈形成","新しい構想","立場を越えた調整"],
        "watchouts":["細部の詰めが甘くなりやすい","興味が広がりすぎる"],
        "jobs":["ITコンサルタント","事業開発","アライアンス","ソリューション営業"],
        "motif":"wave",
    },
    {
        "name":"西郷隆盛","roman":"SAIGO TAKAMORI","gender":"男性","symbol":"◆","era":"幕末〜明治",
        "tagline":"信念と人望で組織を動かす情熱型リーダー",
        "profile":{"leadership":80,"novelty":35,"logic":10,"social":55,"structure":30,"empathy":80,"resilience":85,"independence":65,"idealism":90,"action":70},
        "strengths":["人望","使命感","困難に耐える強さ"],
        "watchouts":["信念が強すぎると柔軟性を失う","情に引っ張られやすい"],
        "jobs":["組織マネジメント","人事・HR","公共領域","チームリーダー"],
        "motif":"mountain",
    },
    {
        "name":"福沢諭吉","roman":"FUKUZAWA YUKICHI","gender":"男性","symbol":"📚","era":"幕末〜明治",
        "tagline":"学びと合理性で社会を変える自立型の啓蒙家",
        "profile":{"leadership":50,"novelty":75,"logic":85,"social":30,"structure":60,"empathy":30,"resilience":70,"independence":90,"idealism":75,"action":55},
        "strengths":["学習力","論理的説明","自立した判断"],
        "watchouts":["理屈を優先しすぎる","他者にも自立を求めすぎる"],
        "jobs":["コンサルタント","教育・研修","政策分析","リサーチ"],
        "motif":"book",
    },
    {
        "name":"レオナルド・ダ・ヴィンチ","roman":"LEONARDO DA VINCI","gender":"男性","symbol":"✦","era":"ルネサンス",
        "tagline":"好奇心で分野を越境する万能クリエイター",
        "profile":{"leadership":10,"novelty":100,"logic":90,"social":-20,"structure":10,"empathy":25,"resilience":45,"independence":95,"idealism":70,"action":30},
        "strengths":["越境的な発想","観察力","創造と分析の両立"],
        "watchouts":["関心が分散しやすい","完成より探究を優先しやすい"],
        "jobs":["研究開発","UX/プロダクトデザイン","データサイエンス","技術企画"],
        "motif":"gear",
    },
    {
        "name":"ナポレオン","roman":"NAPOLEON BONAPARTE","gender":"男性","symbol":"♛","era":"近代フランス",
        "tagline":"判断と実行で勝負する高速指揮官",
        "profile":{"leadership":100,"novelty":65,"logic":70,"social":45,"structure":80,"empathy":-35,"resilience":85,"independence":90,"idealism":30,"action":100},
        "strengths":["高速意思決定","戦略実行","責任を引き受ける力"],
        "watchouts":["強引になりやすい","成功体験を過信しやすい"],
        "jobs":["経営者","営業責任者","プロジェクト統括","危機対応責任者"],
        "motif":"crown",
    },
    {
        "name":"アルベルト・アインシュタイン","roman":"ALBERT EINSTEIN","gender":"男性","symbol":"∑","era":"20世紀",
        "tagline":"常識を疑い、本質を追う独創的な思索家",
        "profile":{"leadership":-10,"novelty":90,"logic":100,"social":-35,"structure":5,"empathy":25,"resilience":55,"independence":100,"idealism":75,"action":-20},
        "strengths":["本質思考","独創性","一人で深く考える力"],
        "watchouts":["考えが深くなりすぎて初動が遅れる","説明が抽象的になりやすい"],
        "jobs":["研究者","AI・データ分析","技術アーキテクト","R&D"],
        "motif":"orbit",
    },
    {
        "name":"マハトマ・ガンディー","roman":"MAHATMA GANDHI","gender":"男性","symbol":"☮","era":"20世紀",
        "tagline":"理念と粘り強さで人を動かす信念型",
        "profile":{"leadership":65,"novelty":45,"logic":25,"social":55,"structure":55,"empathy":95,"resilience":100,"independence":90,"idealism":100,"action":55},
        "strengths":["共感力","強い理念","長期的な粘り"],
        "watchouts":["理想を優先しすぎる","自分にも他者にも高い基準を求めやすい"],
        "jobs":["社会起業","組織開発","教育","NPO・公共領域"],
        "motif":"sun",
    },
    {
        "name":"スティーブ・ジョブズ","roman":"STEVE JOBS","gender":"男性","symbol":"◉","era":"現代",
        "tagline":"理想をプロダクトへ変える執念のビジョナリー",
        "profile":{"leadership":90,"novelty":100,"logic":50,"social":20,"structure":45,"empathy":-40,"resilience":80,"independence":95,"idealism":85,"action":85},
        "strengths":["ビジョン提示","プロダクト感覚","高い基準でやり切る力"],
        "watchouts":["要求水準が高くなりすぎる","共感より完成度を優先しやすい"],
        "jobs":["プロダクトマネージャー","起業家","クリエイティブディレクター","事業開発"],
        "motif":"pixel",
    },

    {
        "name":"卑弥呼","roman":"HIMIKO","gender":"女性","symbol":"☾","era":"弥生時代",
        "tagline":"象徴性と統率力で集団をまとめる求心力タイプ",
        "profile":{"leadership":85,"novelty":20,"logic":-20,"social":40,"structure":70,"empathy":35,"resilience":75,"independence":65,"idealism":55,"action":45},
        "strengths":["求心力","役割を束ねる力","象徴的な発信"],
        "watchouts":["情報が閉じやすい","周囲から意図が見えにくくなる"],
        "jobs":["組織リーダー","広報・ブランド","コミュニティ運営","マネジメント"],
        "motif":"moon",
    },
    {
        "name":"紫式部","roman":"MURASAKI SHIKIBU","gender":"女性","symbol":"✒","era":"平安時代",
        "tagline":"人間観察に優れた、静かな洞察型ストーリーテラー",
        "profile":{"leadership":-45,"novelty":40,"logic":30,"social":-80,"structure":45,"empathy":90,"resilience":20,"independence":55,"idealism":55,"action":-55},
        "strengths":["人間観察","文章表現","深い内省"],
        "watchouts":["考え込みすぎる","対外的な自己主張を控えすぎる"],
        "jobs":["ライター","UXリサーチャー","編集","コンテンツ企画"],
        "motif":"ink",
    },
    {
        "name":"北条政子","roman":"HOJO MASAKO","gender":"女性","symbol":"⛰","era":"鎌倉時代",
        "tagline":"危機に強く、組織を束ねる実務型リーダー",
        "profile":{"leadership":90,"novelty":20,"logic":65,"social":50,"structure":80,"empathy":20,"resilience":95,"independence":80,"idealism":35,"action":80},
        "strengths":["危機対応","組織統率","現実的な判断"],
        "watchouts":["厳しさが先に出やすい","守りを固めすぎる"],
        "jobs":["経営管理","PM","オペレーション責任者","管理職"],
        "motif":"mountain",
    },
    {
        "name":"津田梅子","roman":"TSUDA UMEKO","gender":"女性","symbol":"✧","era":"明治〜昭和",
        "tagline":"教育で未来を変える、計画的なパイオニア",
        "profile":{"leadership":55,"novelty":70,"logic":65,"social":20,"structure":85,"empathy":70,"resilience":80,"independence":85,"idealism":95,"action":60},
        "strengths":["長期的な育成","計画性","社会を変える使命感"],
        "watchouts":["責任を抱え込みやすい","理想のために無理をしやすい"],
        "jobs":["教育企画","人材開発","社会事業","研修コンサル"],
        "motif":"star",
    },
    {
        "name":"与謝野晶子","roman":"YOSANO AKIKO","gender":"女性","symbol":"❀","era":"近代日本",
        "tagline":"感性と自立心で道を切り開く表現者",
        "profile":{"leadership":25,"novelty":75,"logic":-15,"social":15,"structure":5,"empathy":70,"resilience":55,"independence":95,"idealism":85,"action":45},
        "strengths":["表現力","自分の価値観を貫く力","感性から新しい意味を作る力"],
        "watchouts":["型にはめられる環境が苦手","感情が判断に強く影響することがある"],
        "jobs":["コピーライター","クリエイター","広報","編集"],
        "motif":"flower",
    },
    {
        "name":"クレオパトラ","roman":"CLEOPATRA","gender":"女性","symbol":"♕","era":"古代エジプト",
        "tagline":"知性と対人力で局面を動かす戦略的ネゴシエーター",
        "profile":{"leadership":90,"novelty":55,"logic":75,"social":90,"structure":60,"empathy":15,"resilience":80,"independence":85,"idealism":20,"action":75},
        "strengths":["交渉力","対外コミュニケーション","戦略的判断"],
        "watchouts":["駆け引きを複雑にしすぎる","成果優先になりやすい"],
        "jobs":["戦略コンサルタント","渉外","営業・交渉","事業責任者"],
        "motif":"crown",
    },
    {
        "name":"ジャンヌ・ダルク","roman":"JOAN OF ARC","gender":"女性","symbol":"✚","era":"中世フランス",
        "tagline":"強い使命感で突き進む信念アクター",
        "profile":{"leadership":85,"novelty":35,"logic":-10,"social":45,"structure":25,"empathy":55,"resilience":95,"independence":90,"idealism":100,"action":100},
        "strengths":["勇気","使命感","圧力下で動く力"],
        "watchouts":["一直線になりすぎる","慎重な検討を飛ばしやすい"],
        "jobs":["現場リーダー","社会活動","危機対応","プロジェクト推進"],
        "motif":"shield",
    },
    {
        "name":"マリー・キュリー","roman":"MARIE CURIE","gender":"女性","symbol":"⚛","era":"近代科学",
        "tagline":"静かな集中力で真理を追う粘り強い研究者",
        "profile":{"leadership":15,"novelty":85,"logic":100,"social":-55,"structure":85,"empathy":35,"resilience":100,"independence":95,"idealism":70,"action":35},
        "strengths":["集中力","科学的思考","圧倒的な継続力"],
        "watchouts":["一人で抱え込みやすい","成果のために休息を後回しにしやすい"],
        "jobs":["研究開発","データサイエンティスト","品質分析","技術専門職"],
        "motif":"atom",
    },
    {
        "name":"フローレンス・ナイチンゲール","roman":"FLORENCE NIGHTINGALE","gender":"女性","symbol":"✚","era":"近代英国",
        "tagline":"共感とデータで現場を変える改善リーダー",
        "profile":{"leadership":75,"novelty":65,"logic":90,"social":25,"structure":95,"empathy":95,"resilience":90,"independence":85,"idealism":95,"action":80},
        "strengths":["データ活用","現場改善","共感と合理性の両立"],
        "watchouts":["使命感から働きすぎる","改善要求が高くなりやすい"],
        "jobs":["業務改善コンサル","医療・公共","データ分析","PM"],
        "motif":"lamp",
    },
    {
        "name":"ヘレン・ケラー","roman":"HELEN KELLER","gender":"女性","symbol":"★","era":"20世紀",
        "tagline":"困難を越え、言葉と行動で社会を動かす発信者",
        "profile":{"leadership":45,"novelty":55,"logic":35,"social":55,"structure":50,"empathy":100,"resilience":100,"independence":90,"idealism":100,"action":65},
        "strengths":["強い回復力","共感的発信","社会的使命感"],
        "watchouts":["使命を背負いすぎる","感情的負荷を抱え込みやすい"],
        "jobs":["教育・講師","広報・発信","社会課題領域","コミュニティ運営"],
        "motif":"star",
    },
]
assert len(FIGURES) == 20
assert sum(1 for f in FIGURES if f["gender"] == "男性") == 10
assert sum(1 for f in FIGURES if f["gender"] == "女性") == 10

FIGURE_BY_NAME = {f["name"]: f for f in FIGURES}

# ------------------------------------------------------------
# Data persistence
# ------------------------------------------------------------
def init_db():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                ip_hash TEXT NOT NULL,
                result_name TEXT NOT NULL,
                match_percent INTEGER NOT NULL,
                scores_json TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                app_version TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                diagnosis_id TEXT,
                ip_hash TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                ip_hash TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                page_context TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ad_inquiries (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                company TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL
            )
        """)
        conn.commit()

def save_local(payload):
    try:
        init_db()
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO results
                (id, created_at, ip_hash, result_name, match_percent,
                 scores_json, answers_json, app_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload["id"], payload["created_at"], payload["ip_hash"],
                payload["result_name"], payload["match_percent"],
                json.dumps(payload["scores"], ensure_ascii=False),
                json.dumps(payload["answers"], ensure_ascii=False),
                APP_VERSION,
            ))
            conn.commit()
        return True
    except Exception:
        return False

def save_supabase(payload):
    """
    Optional persistent save.
    Create a Supabase table named `diagnosis_results` with matching columns.
    If not configured or if remote save fails, diagnosis still works.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        body = {
            "id": payload["id"],
            "created_at": payload["created_at"],
            "ip_hash": payload["ip_hash"],
            "result_name": payload["result_name"],
            "match_percent": payload["match_percent"],
            "scores": payload["scores"],
            "answers": payload["answers"],
            "app_version": APP_VERSION,
        }
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/diagnosis_results",
            headers=headers,
            json=body,
            timeout=4,
        )
        return 200 <= r.status_code < 300
    except Exception:
        return False

def save_result(payload):
    local_ok = save_local(payload)
    remote_ok = save_supabase(payload)
    return {"local": local_ok, "remote": remote_ok}


def save_feedback(diagnosis_id, ip_hash, rating, comment):
    try:
        init_db()
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("""
                INSERT INTO feedback
                (id, created_at, diagnosis_id, ip_hash, rating, comment)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                datetime.now(timezone.utc).isoformat(),
                diagnosis_id,
                ip_hash,
                int(rating),
                str(comment or "")[:2000],
            ))
            conn.commit()
        return True
    except Exception:
        return False


def save_report(ip_hash, category, message, page_context):
    try:
        init_db()
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("""
                INSERT INTO reports
                (id, created_at, ip_hash, category, message, page_context)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                datetime.now(timezone.utc).isoformat(),
                ip_hash,
                str(category)[:100],
                str(message)[:4000],
                str(page_context)[:500],
            ))
            conn.commit()
        return True
    except Exception:
        return False


def save_ad_inquiry(company, contact_name, email, message):
    try:
        init_db()
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("""
                INSERT INTO ad_inquiries
                (id, created_at, company, contact_name, email, message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                datetime.now(timezone.utc).isoformat(),
                str(company)[:200],
                str(contact_name)[:200],
                str(email)[:320],
                str(message)[:4000],
            ))
            conn.commit()
        return True
    except Exception:
        return False


def simple_email_valid(email):
    email = str(email or "").strip()
    return (
        "@" in email
        and "." in email.split("@")[-1]
        and " " not in email
        and len(email) <= 320
    )


def mailto_url(recipient, subject, body):
    if not recipient:
        return ""
    return (
        f"mailto:{recipient}"
        f"?subject={quote(subject)}"
        f"&body={quote(body)}"
    )

def get_local_stats():
    """
    Returns:
        total_diagnoses: completed diagnosis count
        unique_users: approximate unique users based on hashed IP
    """
    try:
        init_db()
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            total = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
            unique_users = conn.execute(
                "SELECT COUNT(DISTINCT ip_hash) FROM results"
            ).fetchone()[0]
        return {
            "total_diagnoses": int(total or 0),
            "unique_users": int(unique_users or 0),
            "source": "local",
        }
    except Exception:
        return {
            "total_diagnoses": 0,
            "unique_users": 0,
            "source": "local",
        }


def get_supabase_stats():
    """
    Uses Supabase REST count when configured.
    If unavailable, returns None so the app can fall back to SQLite.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Prefer": "count=exact",
        }

        # Total completed diagnoses
        total_resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/diagnosis_results?select=id",
            headers={
                **headers,
                "Range": "0-0",
            },
            timeout=4,
        )

        total = 0
        content_range = total_resp.headers.get("Content-Range", "")
        if "/" in content_range:
            tail = content_range.split("/")[-1]
            if tail.isdigit():
                total = int(tail)

        # Fetch ip_hash values for approximate unique-user count.
        # This is intended for small-to-medium traffic. For large traffic,
        # replace with a Supabase SQL/RPC aggregate.
        unique_users = None
        uniq_resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/diagnosis_results?select=ip_hash&limit=10000",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
            timeout=4,
        )
        if 200 <= uniq_resp.status_code < 300:
            rows = uniq_resp.json()
            unique_users = len({
                row.get("ip_hash")
                for row in rows
                if row.get("ip_hash")
            })

        if 200 <= total_resp.status_code < 300:
            return {
                "total_diagnoses": total,
                "unique_users": unique_users,
                "source": "supabase",
            }

    except Exception:
        pass

    return None


def get_site_stats():
    remote = get_supabase_stats()
    if remote is not None:
        return remote
    return get_local_stats()

# ------------------------------------------------------------
# Privacy / IP pseudonymization
# ------------------------------------------------------------
def get_client_ip():
    try:
        headers = st.context.headers
        for key in ("CF-Connecting-IP", "X-Forwarded-For", "X-Real-IP"):
            value = headers.get(key)
            if value:
                return str(value).split(",")[0].strip()
    except Exception:
        pass
    return "anonymous"

def hash_ip(ip):
    return hmac.new(
        IP_HASH_SALT.encode("utf-8"),
        ip.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

# ------------------------------------------------------------
# Scoring
# ------------------------------------------------------------
def calculate_scores(answers):
    axis_raw = {a: 0 for a in AXES}
    counts = {a: 0 for a in AXES}
    for i, q in enumerate(QUESTIONS):
        base = CHOICE_SCORES[answers[i]]
        axis_raw[q["axis"]] += base * q["direction"]
        counts[q["axis"]] += 1
    scores = {}
    for axis in AXES:
        maximum = counts[axis] * 2
        scores[axis] = round((axis_raw[axis] / maximum) * 100, 1)
    return scores

def distance(user_scores, profile):
    # Weighted normalized Euclidean distance.
    # All axes are currently equal weight to avoid hidden prioritization.
    sq = sum((user_scores[a] - profile[a]) ** 2 for a in AXES)
    return math.sqrt(sq / len(AXES))

def rank_figures(scores):
    ranked = []
    for idx, f in enumerate(FIGURES):
        d = distance(scores, f["profile"])
        ranked.append((d, idx, f))
    ranked.sort(key=lambda x: (round(x[0], 12), x[1]))
    return ranked

def match_percent(d):
    # Theoretical max distance = 200
    return max(0, min(100, round(100 * (1 - d / 200))))

def dominant_axes(scores, n=3):
    return sorted(AXES.keys(), key=lambda a: abs(scores[a]), reverse=True)[:n]

def closest_axes(scores, figure, n=4):
    return sorted(AXES.keys(), key=lambda a: abs(scores[a] - figure["profile"][a]))[:n]

def compatibility_score(base, other):
    """
    Compatibility = shared values + moderate complementarity.
    Not a scientific relationship compatibility score.
    """
    value_axes = ["logic", "empathy", "resilience", "idealism", "structure"]
    complement_axes = ["leadership", "social", "action", "novelty", "independence"]

    shared = sum(
        1 - abs(base[a] - other[a]) / 200
        for a in value_axes
    ) / len(value_axes)

    comp = []
    for a in complement_axes:
        diff = abs(base[a] - other[a])
        comp.append(max(0, 1 - abs(diff - 55) / 145))
    complementary = sum(comp) / len(comp)

    return 0.68 * shared + 0.32 * complementary

def compatible_figures(figure, n=3):
    ranked = []
    for f in FIGURES:
        if f["name"] == figure["name"]:
            continue
        ranked.append((compatibility_score(figure["profile"], f["profile"]), f))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in ranked[:n]]

def result_reason(scores, figure):
    caxes = closest_axes(scores, figure, 4)
    daxes = dominant_axes(scores, 3)
    close_text = "、".join(
        f"{AXES[a]['name']}（{AXES[a]['high'] if scores[a] >= 0 else AXES[a]['low']}）"
        for a in caxes
    )
    dom_text = "、".join(
        f"{AXES[a]['name']} {scores[a]:+.0f}"
        for a in daxes
    )
    return (
        f"20人の人物プロフィールとの10軸距離を比較した結果、"
        f"あなたは **{figure['name']}** に最も近くなりました。"
        f"特に近かったのは {close_text}。"
        f"また、あなた自身の特徴が強く出た軸は {dom_text} です。"
    )

def score_insight(axis, value):
    meta = AXES[axis]
    if value >= 40:
        return meta["desc_high"]
    if value <= -40:
        return meta["desc_low"]
    if value >= 0:
        return f"{meta['high']}寄りだが、状況によって{meta['low']}側も使い分けやすい"
    return f"{meta['low']}寄りだが、状況によって{meta['high']}側も使い分けやすい"


def future_outlook(scores, figure):
    top = dominant_axes(scores, 3)
    strongest = AXES[top[0]]["name"]
    second = AXES[top[1]]["name"]
    low_axis = min(AXES.keys(), key=lambda a: abs(scores[a]))
    balance = AXES[low_axis]["name"]
    text = (
        f"今後は、あなたの強みである{strongest}と{second}を意識して使うほど、"
        f"{figure['name']}タイプらしい持ち味が伸びていきます。"
        f"一方で{balance}は状況に応じて変化しやすい軸です。"
        f"得意分野だけに寄せず、異なるタイプの人と組むことで判断の幅が広がり、"
        f"仕事や人間関係でもより安定して力を発揮しやすくなるでしょう。"
    )
    return text[:145]

# ------------------------------------------------------------
# Portrait / SNS card generator
# The portrait is an original symbolic illustration generated by code.
# It intentionally avoids using copyrighted portraits.
# ------------------------------------------------------------
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
]

def font_path():
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return p
    return None

def get_font(size, bold=False):
    fp = font_path()
    if fp:
        try:
            return ImageFont.truetype(fp, size=size)
        except Exception:
            pass
    return ImageFont.load_default()

def palette_for(figure):
    # Deterministic palette from figure name
    h = int(hashlib.sha256(figure["name"].encode("utf-8")).hexdigest()[:6], 16)
    hue_group = h % 6
    palettes = [
        ((29,32,44),(196,151,82),(242,228,202)),
        ((25,40,55),(80,144,170),(225,238,241)),
        ((48,29,38),(173,84,94),(244,219,214)),
        ((31,47,38),(92,145,108),(225,238,226)),
        ((48,42,27),(176,137,67),(245,231,196)),
        ((34,30,54),(126,103,178),(234,225,245)),
    ]
    return palettes[hue_group]

def draw_symbolic_portrait(figure, size=900):
    bg, accent, light = palette_for(figure)
    img = Image.new("RGB", (size, size), bg)
    d = ImageDraw.Draw(img)

    # background concentric motifs
    for i in range(7):
        margin = 50 + i*46
        alpha_color = tuple(min(255, c + i*3) for c in bg)
        d.ellipse([margin, margin, size-margin, size-margin], outline=alpha_color, width=2)

    # rays
    cx = cy = size//2
    for k in range(16):
        ang = 2*math.pi*k/16
        r1, r2 = size*0.31, size*0.46
        x1, y1 = cx + math.cos(ang)*r1, cy + math.sin(ang)*r1
        x2, y2 = cx + math.cos(ang)*r2, cy + math.sin(ang)*r2
        d.line((x1,y1,x2,y2), fill=accent, width=3)

    # shoulders
    d.rounded_rectangle(
        [size*0.20, size*0.64, size*0.80, size*0.93],
        radius=int(size*.11), fill=accent
    )

    # neck
    d.rounded_rectangle(
        [size*0.43, size*0.52, size*0.57, size*0.70],
        radius=int(size*.04), fill=light
    )

    # face
    d.ellipse([size*.31,size*.19,size*.69,size*.61], fill=light)

    # stylized hair/headwear depends on motif
    motif = figure.get("motif","")
    if motif in ("crown","castle"):
        d.polygon([
            (size*.30,size*.30),(size*.38,size*.16),(size*.46,size*.29),
            (size*.54,size*.13),(size*.62,size*.29),(size*.70,size*.18),
            (size*.69,size*.37),(size*.31,size*.37),
        ], fill=accent)
    elif motif in ("moon","ink","flower","lamp"):
        d.arc([size*.27,size*.14,size*.73,size*.60], 175, 370, fill=accent, width=int(size*.09))
        d.ellipse([size*.28,size*.18,size*.38,size*.34], fill=accent)
        d.ellipse([size*.62,size*.18,size*.72,size*.34], fill=accent)
    else:
        d.arc([size*.27,size*.13,size*.73,size*.58], 180, 360, fill=accent, width=int(size*.10))

    # eyes / nose / mouth
    eye_r = size*.012
    for ex in (size*.43,size*.57):
        d.ellipse([ex-eye_r,size*.39-eye_r,ex+eye_r,size*.39+eye_r], fill=bg)
    d.line((size*.50,size*.41,size*.49,size*.48), fill=accent, width=max(2,int(size*.006)))
    d.arc([size*.43,size*.45,size*.57,size*.54], 15, 165, fill=accent, width=max(2,int(size*.006)))

    # motif badge
    d.ellipse([size*.38,size*.72,size*.62,size*.96], fill=bg, outline=light, width=4)
    sym_font = get_font(int(size*.10), bold=True)
    sym = figure["symbol"]
    bbox = d.textbbox((0,0), sym, font=sym_font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    d.text((cx-tw/2,size*.84-th/2), sym, font=sym_font, fill=light)

    return img

def fit_text(draw, text, max_width, start_size, min_size=20):
    for s in range(start_size, min_size-1, -2):
        font = get_font(s, bold=True)
        box = draw.textbbox((0,0), text, font=font)
        if box[2]-box[0] <= max_width:
            return font
    return get_font(min_size, bold=True)

def make_share_card(figure, scores, match):
    W, H = 1200, 1500
    bg, accent, light = palette_for(figure)
    img = Image.new("RGB", (W,H), (246,243,236))
    d = ImageDraw.Draw(img)

    # main dark panel
    d.rounded_rectangle([45,45,W-45,H-45], radius=48, fill=bg)

    # decorative lines
    for i in range(5):
        x = 70 + i*235
        d.line((x,80,x+150,80), fill=accent, width=3)

    small = get_font(34, bold=True)
    body = get_font(30)
    score_font = get_font(68, bold=True)

    d.text((90,105),"HISTORICAL PERSONALITY", font=small, fill=accent)
    d.text((90,155),"100問 × 10軸 × 20人", font=body, fill=light)

    portrait = draw_symbolic_portrait(figure, 700)
    portrait = portrait.resize((620,620))
    img.paste(portrait, (290,245))

    # name
    name_font = fit_text(d, figure["name"], 1000, 78, 44)
    box = d.textbbox((0,0), figure["name"], font=name_font)
    tw = box[2]-box[0]
    d.text(((W-tw)/2,900), figure["name"], font=name_font, fill=light)

    roman_font = fit_text(d, figure["roman"], 1000, 34, 24)
    box = d.textbbox((0,0), figure["roman"], font=roman_font)
    d.text(((W-(box[2]-box[0]))/2,1000), figure["roman"], font=roman_font, fill=accent)

    # tagline wrapped manually
    tagline = figure["tagline"]
    tag_font = get_font(31, bold=True)
    # split around Japanese punctuation/length
    lines = []
    current = ""
    for ch in tagline:
        trial = current + ch
        box = d.textbbox((0,0), trial, font=tag_font)
        if box[2]-box[0] > 900 and current:
            lines.append(current)
            current = ch
        else:
            current = trial
    if current:
        lines.append(current)
    y = 1060
    for line in lines[:2]:
        box = d.textbbox((0,0), line, font=tag_font)
        d.text(((W-(box[2]-box[0]))/2,y), line, font=tag_font, fill=(235,232,225))
        y += 48

    # Match badge
    d.rounded_rectangle([310,1185,890,1325], radius=60, fill=accent)
    label_font = get_font(31, bold=True)
    d.text((370,1213),"MATCH",font=label_font,fill=bg)
    d.text((585,1195),f"{match}%",font=score_font,fill=bg)

    footer = "#歴史上の人物性格診断"
    footer_font = get_font(28, bold=True)
    box = d.textbbox((0,0), footer, font=footer_font)
    d.text(((W-(box[2]-box[0]))/2,1370), footer, font=footer_font, fill=light)

    bio = io.BytesIO()
    img.save(bio, format="PNG", optimize=True)
    return bio.getvalue()

def portrait_bytes(figure):
    bio = io.BytesIO()
    draw_symbolic_portrait(figure, 900).save(bio, format="PNG", optimize=True)
    return bio.getvalue()

# ------------------------------------------------------------
# Ads / sponsor hooks
# ------------------------------------------------------------

def render_bug_report(page_context="unknown"):
    with st.expander("🐞 不具合・エラーを報告"):
        st.caption("開発中のため、表示崩れ・エラー・診断中の問題があればここから送れます。")
        with st.form(f"bug_report_{page_context}", clear_on_submit=True):
            category = st.selectbox(
                "種類",
                ["エラーが表示された", "画面が動かない", "表示がおかしい", "診断結果について", "その他"],
            )
            message = st.text_area(
                "状況を教えてください",
                placeholder="例：Q31から次へ進めない／表示されたエラー文など",
                max_chars=4000,
            )
            submit = st.form_submit_button("不具合報告を保存", use_container_width=True)
        if submit:
            if not message.strip():
                st.warning("状況を入力してください。")
            else:
                ok = save_report(
                    hash_ip(get_client_ip()),
                    category,
                    message,
                    page_context,
                )
                if ok:
                    st.success("報告を保存しました。ありがとうございます。")
                else:
                    st.error("報告の保存に失敗しました。")

        if ADMIN_EMAIL:
            body = f"""不具合報告

ページ: {page_context}
種類: {category}

状況:
{message}
"""
            url = mailto_url(ADMIN_EMAIL, f"【{APP_NAME}】不具合報告", body)
            if url:
                st.link_button("メールアプリから直接送る", url, use_container_width=True)


def render_advertising_contact():
    with st.expander("📨 広告掲載・スポンサーのお問い合わせ"):
        st.write(
            "この診断サイトへの広告掲載・タイアップ・スポンサーのご相談はこちらから受け付けています。"
        )
        with st.form("ad_inquiry_form", clear_on_submit=True):
            company = st.text_input("会社名・屋号（任意）")
            contact_name = st.text_input("お名前")
            email = st.text_input("返信先メールアドレス")
            message = st.text_area(
                "お問い合わせ内容",
                placeholder="掲載希望内容、商品・サービス、希望時期など",
                max_chars=4000,
            )
            send = st.form_submit_button("お問い合わせを保存", use_container_width=True)

        if send:
            if not contact_name.strip() or not simple_email_valid(email) or not message.strip():
                st.warning("お名前・有効なメールアドレス・お問い合わせ内容を入力してください。")
            else:
                ok = save_ad_inquiry(company, contact_name, email, message)
                if ok:
                    st.success("お問い合わせを保存しました。")
                else:
                    st.error("お問い合わせの保存に失敗しました。")

        if CONTACT_EMAIL:
            body = f"""広告掲載のお問い合わせ

会社名・屋号: {company}
お名前: {contact_name}
返信先: {email}

内容:
{message}
"""
            url = mailto_url(CONTACT_EMAIL, f"【{APP_NAME}】広告掲載のお問い合わせ", body)
            if url:
                st.link_button(
                    "メールアプリで広告掲載メールを送る",
                    url,
                    use_container_width=True,
                )
        else:
            st.caption(
                "運営者メールアドレスはまだ設定されていません。"
                "Secrets に ADMIN_EMAIL を設定すると、メール送信ボタンも有効になります。"
            )


def render_ad(position):
    if not ADS_ENABLED:
        return
    html = ADS_HTML_TOP if position == "top" else ADS_HTML_RESULT
    if html.strip():
        components.html(html, height=120, scrolling=False)
    elif SPONSOR_TEXT:
        safe_url = SPONSOR_URL if SPONSOR_URL.startswith("http") else APP_URL
        st.markdown(
            f'<div class="ad-slot">PR / スポンサー：'
            f'<a href="{safe_url}" target="_blank">{SPONSOR_TEXT}</a></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="ad-slot">広告・スポンサー掲載枠</div>', unsafe_allow_html=True)

# ------------------------------------------------------------
# Session state
# ------------------------------------------------------------
DEFAULTS = {
    "started": False,
    "page": 0,
    "answers": {},
    "completed": False,
    "result_id": None,
    "result_data": None,
    "feedback_submitted": False,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

def reset():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v if not isinstance(v, dict) else {}
    # clear stale radio keys
    for k in list(st.session_state.keys()):
        if k.startswith("radio_"):
            del st.session_state[k]

# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
site_stats = get_site_stats()
hero_count = f"{site_stats['total_diagnoses']:,}"

st.markdown(f"""
<div class="hero" style="position:relative;">
  <div style="position:absolute;right:18px;top:16px;text-align:right;">
    <div style="font-size:.72rem;opacity:.68;">TOTAL DIAGNOSES</div>
    <div style="font-size:1.45rem;font-weight:800;">{hero_count} 回</div>
  </div>
  <div class="kicker">Historical Personality Test</div>
  <h1>🏛️ 歴史上の人物 性格診断</h1>
  <p><b>100の質問から、あなたの思考・行動傾向を10軸で数値化。</b><br>
  男性10人・女性10人、計20人の歴史的人物プロフィールと比較し、最も近い1人を確定します。</p>
  <div class="badge-row">
    <span class="badge">100問</span>
    <span class="badge">5段階回答</span>
    <span class="badge">10性格軸</span>
    <span class="badge">20人物</span>
    <span class="badge">API不要</span>
    <span class="badge">結果画像つき</span>
  </div>
</div>
""", unsafe_allow_html=True)

render_ad("top")

stat_a, stat_b = st.columns(2)
with stat_a:
    st.metric(
        "🏛️ これまでの診断回数",
        f"{site_stats['total_diagnoses']:,} 回",
    )
with stat_b:
    unique_display = (
        f"{site_stats['unique_users']:,} 人"
        if site_stats.get("unique_users") is not None
        else "集計中"
    )
    st.metric(
        "👥 推定ユニーク利用者",
        unique_display,
    )

st.caption(
    "※ユニーク利用者数は、保存されたハッシュ化IP識別子を基準にした概算です。"
    "同じ回線を複数人で使う場合や、VPN・携帯回線では実人数と一致しないことがあります。"
)

# ------------------------------------------------------------
# Result page
# ------------------------------------------------------------
if st.session_state.completed and st.session_state.result_data:
    data = st.session_state.result_data
    figure = data["figure"]
    scores = data["scores"]
    ranked = data["ranked"]
    compatible = data["compatible"]
    match = data["match"]

    portrait = portrait_bytes(figure)

    st.success("100問の診断が完了しました。", icon="✅")
    cimg, ctext = st.columns([0.42, 0.58], vertical_alignment="center")
    with cimg:
        st.image(portrait, use_container_width=True)
    with ctext:
        st.markdown(f"""
        <div class="result-card">
          <div class="kicker">YOUR HISTORICAL TYPE</div>
          <h2>{figure['name']}</h2>
          <p class="muted">{figure['roman']} ｜ {figure['era']}</p>
          <h3>{figure['tagline']}</h3>
          <div class="big-number">マッチ度 {match}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.caption("人物の数値プロフィールとイラストは、この診断のために作成した独自モデルです。歴史学上・心理学上の確定的評価ではありません。")

    render_ad("result")

    st.subheader("🔍 なぜこの人物になった？")
    st.markdown(f'<div class="reason">{result_reason(scores, figure)}</div>', unsafe_allow_html=True)

    close = closest_axes(scores, figure, 4)
    cols = st.columns(4)
    for col, axis in zip(cols, close):
        with col:
            meta = AXES[axis]
            st.metric(meta["name"], f"{scores[axis]:+.0f}")
            st.caption(meta["high"] if scores[axis] >= 0 else meta["low"])

    st.subheader("🧭 あなたの10軸プロフィール")
    for axis, meta in AXES.items():
        value = scores[axis]
        pct = max(0, min(100, round((value + 100) / 2)))
        st.markdown(f"**{meta['name']}：{value:+.0f}**　`{meta['low']} ←→ {meta['high']}`")
        st.progress(pct)
        st.caption(score_insight(axis, value))

    st.subheader("💎 このタイプの強み")
    s_cols = st.columns(3)
    for col, text in zip(s_cols, figure["strengths"]):
        with col:
            st.markdown(f'<div class="soft-card"><b>{text}</b></div>', unsafe_allow_html=True)

    st.subheader("⚠️ 力を発揮するための注意点")
    for item in figure["watchouts"]:
        st.write(f"・{item}")

    st.subheader("🔭 今後の展望")
    st.info(future_outlook(scores, figure))

    st.subheader("💼 向いている仕事")
    job_cols = st.columns(2)
    for idx, job in enumerate(figure["jobs"]):
        with job_cols[idx % 2]:
            st.markdown(f'<div class="soft-card"><b>{job}</b></div>', unsafe_allow_html=True)
    st.caption("職業適性を保証するものではありません。性格傾向から見た参考候補です。")

    st.subheader("🤝 相性の良い歴史人物タイプ")
    comp_cols = st.columns(3)
    for col, f in zip(comp_cols, compatible):
        with col:
            st.image(portrait_bytes(f), use_container_width=True)
            st.markdown(f"**{f['name']}**")
            st.caption(f["tagline"])

    st.subheader("🏅 あなたに近かった人物 TOP5")
    for rank, (dist, _, f) in enumerate(ranked[:5], start=1):
        st.write(f"**{rank}. {f['name']}**　—　マッチ度 {match_percent(dist)}%")

    # SNS card
    st.divider()
    st.subheader("📣 結果を画像つきでシェア")
    share_card = make_share_card(figure, scores, match)
    st.image(share_card, caption="SNS投稿用の結果カード", use_container_width=True)

    share_text = (
        f"100問の『歴史上の人物 性格診断』をやったら、"
        f"私は「{figure['name']}」タイプでした！\n"
        f"{figure['tagline']}\n"
        f"マッチ度 {match}%\n"
        f"#歴史上の人物性格診断"
    )

    st.download_button(
        "🖼️ SNS用結果画像を保存",
        data=share_card,
        file_name=f"historical_personality_{figure['roman'].lower().replace(' ','_')}.png",
        mime="image/png",
        type="primary",
        use_container_width=True,
    )

    with st.expander("投稿文を表示・コピー"):
        st.code(share_text, language=None)

    x_url = f"https://twitter.com/intent/tweet?text={quote(share_text)}&url={quote(APP_URL)}"
    line_url = f"https://social-plugins.line.me/lineit/share?url={quote(APP_URL)}&text={quote(share_text)}"
    fb_url = f"https://www.facebook.com/sharer/sharer.php?u={quote(APP_URL)}"

    sx, sl, sf = st.columns(3)
    sx.link_button("𝕏 Xで投稿", x_url, use_container_width=True)
    sl.link_button("LINEで送る", line_url, use_container_width=True)
    sf.link_button("Facebookで共有", fb_url, use_container_width=True)

    st.info(
        "SNSの仕様上、Webサイトから端末内の画像を投稿へ自動添付できないサービスがあります。"
        "上の「SNS用結果画像を保存」で画像を保存し、投稿画面で添付すると画像つきで共有できます。",
        icon="ℹ️",
    )

    # JSON export
    export_data = {
        "diagnosis_id": st.session_state.result_id,
        "app_version": APP_VERSION,
        "result": figure["name"],
        "match_percent": match,
        "axis_scores": scores,
        "top5": [
            {"rank": i+1, "name": f["name"], "match_percent": match_percent(d)}
            for i, (d, _, f) in enumerate(ranked[:5])
        ],
        "answers": [
            {
                "no": i+1,
                "question": QUESTIONS[i]["text"],
                "axis": AXES[QUESTIONS[i]["axis"]]["name"],
                "answer": st.session_state.answers[i],
                "effective_score": CHOICE_SCORES[st.session_state.answers[i]] * QUESTIONS[i]["direction"],
            }
            for i in range(100)
        ],
    }
    st.download_button(
        "💾 診断データ（JSON）も保存",
        data=json.dumps(export_data, ensure_ascii=False, indent=2),
        file_name=f"historical_personality_{st.session_state.result_id}.json",
        mime="application/json",
        use_container_width=True,
    )

    st.divider()
    st.subheader("⭐ 診断の満足度")
    st.write("診断結果をすべて確認したあと、5段階で評価してください。")
    if not st.session_state.get("feedback_submitted", False):
        with st.form("satisfaction_form"):
            rating = st.radio(
                "満足度",
                options=[1, 2, 3, 4, 5],
                index=4,
                horizontal=True,
                format_func=lambda x: f"{x} ★" if x == 5 else str(x),
            )
            comment = st.text_area(
                "感想・改善してほしい点（任意）",
                max_chars=2000,
            )
            fb_submit = st.form_submit_button("満足度を送信", type="primary", use_container_width=True)
        if fb_submit:
            ok = save_feedback(
                st.session_state.result_id,
                hash_ip(get_client_ip()),
                rating,
                comment,
            )
            if ok:
                st.session_state.feedback_submitted = True
                st.success("評価を送信しました。ありがとうございます。")
            else:
                st.error("評価の保存に失敗しました。")
    else:
        st.success("満足度は送信済みです。")

    render_bug_report("result")
    render_advertising_contact()

    st.divider()
    if st.button("🔄 もう一度診断する", use_container_width=True):
        reset()
        st.rerun()

    # transparency
    with st.expander("診断ロジックとプライバシーについて"):
        st.markdown("""
        **診断ロジック**
        - 100問を10軸に10問ずつ割り当てています。
        - 5段階回答を -2 / -1 / 0 / +1 / +2 に変換します。
        - 逆転項目は符号を反転し、各軸を -100〜+100 に正規化します。
        - 20人物それぞれの10軸プロフィールとの距離を比較し、最短の1人を結果として確定します。
        - 完全同点の場合も登録順をタイブレークに利用するため、結果は必ず1人に確定します。

        **プライバシー**
        - 氏名・メールアドレスの入力は不要です。
        - 生のIPアドレスは保存しません。
        - IPは秘密のソルトを使ったHMAC-SHA256へ変換し、その擬似識別子のみ保存します。
        - IP由来の識別子を使うため「完全匿名」を保証するものではありません。
        - 広告を有効にした場合、広告事業者側でCookie等が利用される場合があります。
        """)

    st.stop()

# ------------------------------------------------------------
# Landing page
# ------------------------------------------------------------
if not st.session_state.started:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("質問", "100")
    c2.metric("回答", "5択")
    c3.metric("性格軸", "10")
    c4.metric("人物", "20")

    st.markdown("""
    <div class="soft-card">
      <h3>🔐 匿名性を重視した設計</h3>
      <p><b>名前・メールアドレス・SNSアカウントの入力は不要です。</b></p>
      <p>診断保存時、生のIPアドレスは保存せず、秘密のソルトを使った
      HMAC-SHA256の擬似識別子へ変換します。</p>
      <p class="small">ただしIP由来の識別子を利用するため、完全匿名を保証するものではありません。
      VPN・共有回線・携帯回線では同一人物を正確に識別できない場合があります。</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["20人の候補", "10の性格軸", "診断の仕組み"])
    with tab1:
        men = [f for f in FIGURES if f["gender"] == "男性"]
        women = [f for f in FIGURES if f["gender"] == "女性"]
        st.markdown("**男性10人**")
        for f in men:
            st.write(f"{f['name']} — {f['tagline']}")
        st.markdown("**女性10人**")
        for f in women:
            st.write(f"{f['name']} — {f['tagline']}")
    with tab2:
        for meta in AXES.values():
            st.write(f"**{meta['name']}**：{meta['low']} ←→ {meta['high']}")
    with tab3:
        st.markdown("""
        1. 100問を5段階で回答  
        2. 回答を数値へ変換  
        3. 10の性格軸を -100〜+100 で算出  
        4. 20人全員のプロフィールと比較  
        5. 最も近い人物を1人に確定  
        6. 判断理由・仕事・相性・SNS用画像を表示
        """)

    consent = st.checkbox(
        "プライバシー説明を確認し、回答・診断結果・ハッシュ化したIP識別子が保存されることに同意します。"
    )

    if st.button(
        "100問の診断を始める",
        type="primary",
        use_container_width=True,
        disabled=not consent,
    ):
        st.session_state.started = True
        st.session_state.page = 0
        st.rerun()

    with st.expander("📈 サイト利用状況"):
        st.write(f"**累計診断回数：{site_stats['total_diagnoses']:,} 回**")
        if site_stats.get("unique_users") is not None:
            st.write(f"**推定ユニーク利用者：{site_stats['unique_users']:,} 人**")
        st.caption(
            "診断完了時に1回として集計します。"
            "ユニーク利用者数はハッシュ化IP識別子による概算です。"
        )

    render_bug_report("top")
    render_advertising_contact()

    if PRIVACY_POLICY_URL or TERMS_URL:
        link_cols = st.columns(2)
        if PRIVACY_POLICY_URL:
            link_cols[0].link_button("プライバシーポリシー", PRIVACY_POLICY_URL, use_container_width=True)
        if TERMS_URL:
            link_cols[1].link_button("利用規約", TERMS_URL, use_container_width=True)

    st.caption("※この診断は自己理解・娯楽を目的とした独自診断です。医療・採用・心理検査などの専門判断には使用しないでください。")
    st.stop()

# ------------------------------------------------------------
# Question flow: 10 questions x 10 pages
# ------------------------------------------------------------
PER_PAGE = 10
total_pages = len(QUESTIONS) // PER_PAGE
page = st.session_state.page
start = page * PER_PAGE
end = start + PER_PAGE

answered = len(st.session_state.answers)
st.progress(answered / 100)
st.markdown(f"**進捗 {answered} / 100問**　｜　ページ **{page+1} / {total_pages}**")
st.caption("迷った場合は「どちらでもない」を選んでください。考えすぎず、普段の自分に近い回答がおすすめです。")

with st.form(key=f"form_{page}"):
    current = {}
    for i in range(start, end):
        q = QUESTIONS[i]
        options = ["選択してください"] + CHOICES
        existing = st.session_state.answers.get(i)
        idx = options.index(existing) if existing in options else 0

        st.markdown(f"### Q{i+1}. {q['text']}")
        selected = st.radio(
            f"Q{i+1} 回答",
            options,
            index=idx,
            key=f"radio_{i}",
            label_visibility="collapsed",
        )
        current[i] = selected
        st.divider()

    back_col, next_col = st.columns(2)
    back = back_col.form_submit_button(
        "← 前の10問",
        use_container_width=True,
        disabled=(page == 0),
    )
    next_label = "診断結果を見る" if page == total_pages - 1 else "次の10問 →"
    nxt = next_col.form_submit_button(
        next_label,
        type="primary",
        use_container_width=True,
    )

if back:
    for i, ans in current.items():
        if ans in CHOICES:
            st.session_state.answers[i] = ans
    st.session_state.page = max(0, page-1)
    st.rerun()

if nxt:
    missing = [i+1 for i, ans in current.items() if ans not in CHOICES]
    if missing:
        st.error("このページに未回答があります：" + "、".join(map(str, missing)))
    else:
        for i, ans in current.items():
            st.session_state.answers[i] = ans

        if page < total_pages - 1:
            st.session_state.page += 1
            st.rerun()
        else:
            if len(st.session_state.answers) != 100:
                st.error("100問すべての回答を確認できませんでした。前のページを確認してください。")
            else:
                scores = calculate_scores(st.session_state.answers)
                ranked = rank_figures(scores)
                winner = ranked[0][2]
                match = match_percent(ranked[0][0])
                compatible = compatible_figures(winner, 3)
                result_id = str(uuid.uuid4())
                created_at = datetime.now(timezone.utc).isoformat()
                ip_hash = hash_ip(get_client_ip())

                answers_payload = {
                    str(i): st.session_state.answers[i] for i in range(100)
                }
                payload = {
                    "id": result_id,
                    "created_at": created_at,
                    "ip_hash": ip_hash,
                    "result_name": winner["name"],
                    "match_percent": match,
                    "scores": scores,
                    "answers": answers_payload,
                }
                save_status = save_result(payload)

                st.session_state.result_id = result_id
                st.session_state.result_data = {
                    "figure": winner,
                    "scores": scores,
                    "ranked": ranked,
                    "compatible": compatible,
                    "match": match,
                    "save_status": save_status,
                }
                st.session_state.completed = True
                st.rerun()
