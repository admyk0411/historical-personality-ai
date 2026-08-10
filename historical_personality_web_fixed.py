import streamlit as st
import hashlib
import hmac
import json
import math
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

# =========================================================
# 基本設定
# =========================================================
st.set_page_config(
    page_title="歴史上の人物 性格診断",
    page_icon="🏛️",
    layout="centered",
)

APP_TITLE = "🏛️ 歴史上の人物 性格診断"
DB_PATH = "diagnosis_results.db"

# Secrets が未設定でも起動できる安全なフォールバック
try:
    IP_HASH_SALT = str(st.secrets.get("IP_HASH_SALT", "change-this-salt-before-public-release"))
except Exception:
    IP_HASH_SALT = "change-this-salt-before-public-release"

try:
    APP_URL = str(st.secrets.get("APP_URL", "https://historical-personality-ai-gujhfwuepxfoohbvrubhmw.streamlit.app/"))
except Exception:
    APP_URL = "https://historical-personality-ai-gujhfwuepxfoohbvrubhmw.streamlit.app/"


# =========================================================
# 10の性格軸
# -100 ～ +100 で評価
# =========================================================
AXES = {
    "leadership": {
        "name": "主導性",
        "low": "協調・支援",
        "high": "主導・牽引",
    },
    "novelty": {
        "name": "挑戦性",
        "low": "慎重・安定",
        "high": "挑戦・革新",
    },
    "logic": {
        "name": "論理性",
        "low": "感覚・情緒",
        "high": "論理・分析",
    },
    "social": {
        "name": "社交性",
        "low": "内省・少人数",
        "high": "交流・対外",
    },
    "structure": {
        "name": "計画性",
        "low": "柔軟・即興",
        "high": "計画・秩序",
    },
    "empathy": {
        "name": "共感性",
        "low": "客観・割り切り",
        "high": "共感・配慮",
    },
    "resilience": {
        "name": "精神的安定性",
        "low": "繊細・反応的",
        "high": "安定・粘り強い",
    },
    "independence": {
        "name": "自立性",
        "low": "協調・周囲重視",
        "high": "独立・自己決定",
    },
    "idealism": {
        "name": "理想志向",
        "low": "現実・実利",
        "high": "理念・理想",
    },
    "action": {
        "name": "行動性",
        "low": "熟考・観察",
        "high": "即行動・実践",
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


# =========================================================
# 100問：各軸10問
# direction = 1 なら同意ほど + 側
# direction = -1 なら同意ほど - 側（逆転項目）
# =========================================================
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

QUESTIONS = []
for axis_key, items in QUESTION_BANK.items():
    for text, direction in items:
        QUESTIONS.append({
            "axis": axis_key,
            "text": text,
            "direction": direction,
        })

assert len(QUESTIONS) == 100, "質問数は100問である必要があります。"


# =========================================================
# 20人の歴史的人物（男性10・女性10）
# 数値は「診断用の人物モデル」。学術的な心理測定値ではありません。
# =========================================================
FIGURES = [
    {
        "name": "織田信長", "gender": "男性", "emoji": "⚔️",
        "tagline": "常識を壊して前へ進む革新リーダー",
        "profile": {"leadership": 95, "novelty": 95, "logic": 55, "social": 35, "structure": 20, "empathy": -45, "resilience": 75, "independence": 90, "idealism": 45, "action": 95},
        "jobs": ["起業家", "新規事業開発", "経営・事業責任者"],
    },
    {
        "name": "徳川家康", "gender": "男性", "emoji": "🏯",
        "tagline": "長期戦に強い安定型ストラテジスト",
        "profile": {"leadership": 75, "novelty": -40, "logic": 80, "social": 20, "structure": 95, "empathy": 15, "resilience": 95, "independence": 60, "idealism": 10, "action": 20},
        "jobs": ["経営企画", "プロジェクトマネージャー", "リスク管理"],
    },
    {
        "name": "坂本龍馬", "gender": "男性", "emoji": "🌊",
        "tagline": "人をつなぎ未来を動かす変革コネクター",
        "profile": {"leadership": 65, "novelty": 90, "logic": 45, "social": 90, "structure": -20, "empathy": 65, "resilience": 65, "independence": 80, "idealism": 85, "action": 90},
        "jobs": ["ITコンサルタント", "事業開発", "アライアンス営業"],
    },
    {
        "name": "西郷隆盛", "gender": "男性", "emoji": "🐕",
        "tagline": "信念と人望で組織を動かす情熱型",
        "profile": {"leadership": 80, "novelty": 35, "logic": 10, "social": 55, "structure": 30, "empathy": 80, "resilience": 85, "independence": 65, "idealism": 90, "action": 70},
        "jobs": ["組織マネジメント", "人事・HR", "公共政策"],
    },
    {
        "name": "福沢諭吉", "gender": "男性", "emoji": "📚",
        "tagline": "学びと合理性で社会を変える啓蒙タイプ",
        "profile": {"leadership": 50, "novelty": 75, "logic": 85, "social": 30, "structure": 60, "empathy": 30, "resilience": 70, "independence": 90, "idealism": 75, "action": 55},
        "jobs": ["教育・研修", "コンサルタント", "研究・政策分析"],
    },
    {
        "name": "レオナルド・ダ・ヴィンチ", "gender": "男性", "emoji": "🎨",
        "tagline": "好奇心で分野を越境する万能クリエイター",
        "profile": {"leadership": 10, "novelty": 100, "logic": 90, "social": -20, "structure": 10, "empathy": 25, "resilience": 45, "independence": 95, "idealism": 70, "action": 30},
        "jobs": ["研究開発", "UX・プロダクトデザイン", "データサイエンス"],
    },
    {
        "name": "ナポレオン", "gender": "男性", "emoji": "🦅",
        "tagline": "判断と実行で勝負する高速指揮官",
        "profile": {"leadership": 100, "novelty": 65, "logic": 70, "social": 45, "structure": 80, "empathy": -35, "resilience": 85, "independence": 90, "idealism": 30, "action": 100},
        "jobs": ["経営者", "営業責任者", "プロジェクト統括"],
    },
    {
        "name": "アルベルト・アインシュタイン", "gender": "男性", "emoji": "🧠",
        "tagline": "常識を疑い本質を追う独創的思索家",
        "profile": {"leadership": -10, "novelty": 90, "logic": 100, "social": -35, "structure": 5, "empathy": 25, "resilience": 55, "independence": 100, "idealism": 75, "action": -20},
        "jobs": ["研究者", "AI・データ分析", "技術アーキテクト"],
    },
    {
        "name": "マハトマ・ガンディー", "gender": "男性", "emoji": "🕊️",
        "tagline": "理念と粘り強さで人を動かす信念型",
        "profile": {"leadership": 65, "novelty": 45, "logic": 25, "social": 55, "structure": 55, "empathy": 95, "resilience": 100, "independence": 90, "idealism": 100, "action": 55},
        "jobs": ["NPO・社会起業", "組織開発", "教育・人材育成"],
    },
    {
        "name": "スティーブ・ジョブズ", "gender": "男性", "emoji": "💻",
        "tagline": "理想を製品に変える執念のプロダクト型",
        "profile": {"leadership": 90, "novelty": 100, "logic": 50, "social": 20, "structure": 45, "empathy": -40, "resilience": 80, "independence": 95, "idealism": 85, "action": 85},
        "jobs": ["プロダクトマネージャー", "起業家", "クリエイティブディレクター"],
    },
    {
        "name": "卑弥呼", "gender": "女性", "emoji": "🔮",
        "tagline": "象徴性と統率力を併せ持つ求心力タイプ",
        "profile": {"leadership": 85, "novelty": 20, "logic": -20, "social": 40, "structure": 70, "empathy": 35, "resilience": 75, "independence": 65, "idealism": 55, "action": 45},
        "jobs": ["組織リーダー", "広報・ブランド", "コミュニティ運営"],
    },
    {
        "name": "紫式部", "gender": "女性", "emoji": "📖",
        "tagline": "人間観察に優れた静かな表現者",
        "profile": {"leadership": -45, "novelty": 40, "logic": 30, "social": -80, "structure": 45, "empathy": 90, "resilience": 20, "independence": 55, "idealism": 55, "action": -55},
        "jobs": ["ライター", "UXリサーチャー", "編集・コンテンツ企画"],
    },
    {
        "name": "北条政子", "gender": "女性", "emoji": "🌙",
        "tagline": "危機に強く組織を束ねる実務リーダー",
        "profile": {"leadership": 90, "novelty": 20, "logic": 65, "social": 50, "structure": 80, "empathy": 20, "resilience": 95, "independence": 80, "idealism": 35, "action": 80},
        "jobs": ["経営管理", "プロジェクトマネージャー", "オペレーション責任者"],
    },
    {
        "name": "津田梅子", "gender": "女性", "emoji": "🎓",
        "tagline": "教育で未来を変える計画的パイオニア",
        "profile": {"leadership": 55, "novelty": 70, "logic": 65, "social": 20, "structure": 85, "empathy": 70, "resilience": 80, "independence": 85, "idealism": 95, "action": 60},
        "jobs": ["教育企画", "人材開発", "社会事業"],
    },
    {
        "name": "与謝野晶子", "gender": "女性", "emoji": "✒️",
        "tagline": "感性と自立心で道を切り開く表現者",
        "profile": {"leadership": 25, "novelty": 75, "logic": -15, "social": 15, "structure": 5, "empathy": 70, "resilience": 55, "independence": 95, "idealism": 85, "action": 45},
        "jobs": ["コピーライター", "クリエイター", "広報・編集"],
    },
    {
        "name": "クレオパトラ", "gender": "女性", "emoji": "👑",
        "tagline": "知性と対人力で局面を動かす交渉家",
        "profile": {"leadership": 90, "novelty": 55, "logic": 75, "social": 90, "structure": 60, "empathy": 15, "resilience": 80, "independence": 85, "idealism": 20, "action": 75},
        "jobs": ["戦略コンサルタント", "外交・渉外", "営業・交渉"],
    },
    {
        "name": "ジャンヌ・ダルク", "gender": "女性", "emoji": "🛡️",
        "tagline": "強い使命感で突き進む信念アクター",
        "profile": {"leadership": 85, "novelty": 35, "logic": -10, "social": 45, "structure": 25, "empathy": 55, "resilience": 95, "independence": 90, "idealism": 100, "action": 100},
        "jobs": ["現場リーダー", "社会活動", "危機対応・プロジェクト推進"],
    },
    {
        "name": "マリー・キュリー", "gender": "女性", "emoji": "⚗️",
        "tagline": "静かな集中力で真理を追う研究者",
        "profile": {"leadership": 15, "novelty": 85, "logic": 100, "social": -55, "structure": 85, "empathy": 35, "resilience": 100, "independence": 95, "idealism": 70, "action": 35},
        "jobs": ["研究開発", "データサイエンティスト", "品質・分析職"],
    },
    {
        "name": "フローレンス・ナイチンゲール", "gender": "女性", "emoji": "🏥",
        "tagline": "共感とデータで現場を変える改善リーダー",
        "profile": {"leadership": 75, "novelty": 65, "logic": 90, "social": 25, "structure": 95, "empathy": 95, "resilience": 90, "independence": 85, "idealism": 95, "action": 80},
        "jobs": ["業務改善コンサルタント", "医療・公共分野", "データ分析・PM"],
    },
    {
        "name": "ヘレン・ケラー", "gender": "女性", "emoji": "🌟",
        "tagline": "困難を越えて言葉で社会を動かす発信者",
        "profile": {"leadership": 45, "novelty": 55, "logic": 35, "social": 55, "structure": 50, "empathy": 100, "resilience": 100, "independence": 90, "idealism": 100, "action": 65},
        "jobs": ["教育・講師", "広報・発信", "社会課題領域"],
    },
]

assert len(FIGURES) == 20
assert sum(1 for f in FIGURES if f["gender"] == "男性") == 10
assert sum(1 for f in FIGURES if f["gender"] == "女性") == 10


# =========================================================
# データ保存
# =========================================================
def init_db():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                ip_hash TEXT NOT NULL,
                result_name TEXT NOT NULL,
                scores_json TEXT NOT NULL,
                answers_json TEXT NOT NULL
            )
        """)
        conn.commit()


def save_result(result_id, ip_hash, result_name, scores, answers):
    try:
        init_db()
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO results
                (id, created_at, ip_hash, result_name, scores_json, answers_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                result_id,
                datetime.now(timezone.utc).isoformat(),
                ip_hash,
                result_name,
                json.dumps(scores, ensure_ascii=False),
                json.dumps(answers, ensure_ascii=False),
            ))
            conn.commit()
        return True
    except Exception:
        # 保存失敗で診断自体を壊さない
        return False


# =========================================================
# 匿名IP識別
# =========================================================
def get_client_ip():
    """
    生IPはDBに保存しない。
    プロキシ環境では X-Forwarded-For 等を参照する。
    取得できない場合は anonymous を使い、アプリを停止させない。
    """
    try:
        headers = st.context.headers
        for key in ("X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP"):
            value = headers.get(key)
            if value:
                return str(value).split(",")[0].strip()
    except Exception:
        pass
    return "anonymous"


def hash_ip(ip):
    # HMAC-SHA256: 生IPを保存せず、同一IPの擬似識別子を作る
    return hmac.new(
        IP_HASH_SALT.encode("utf-8"),
        ip.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# =========================================================
# 診断計算
# =========================================================
def calculate_scores(answers):
    axis_raw = {axis: 0 for axis in AXES}
    axis_count = {axis: 0 for axis in AXES}

    for i, q in enumerate(QUESTIONS):
        choice = answers[i]
        base = CHOICE_SCORES[choice]
        axis_raw[q["axis"]] += base * q["direction"]
        axis_count[q["axis"]] += 1

    # 各軸10問、1問最大±2 → raw最大±20
    # -100 ～ +100 に正規化
    scores = {}
    for axis in AXES:
        max_abs = axis_count[axis] * 2
        value = (axis_raw[axis] / max_abs) * 100 if max_abs else 0
        scores[axis] = round(value, 1)
    return scores


def distance(user_scores, profile):
    # 10軸の正規化ユークリッド距離
    sq = sum((user_scores[a] - profile[a]) ** 2 for a in AXES)
    return math.sqrt(sq / len(AXES))


def rank_figures(user_scores):
    ranked = []
    for idx, figure in enumerate(FIGURES):
        d = distance(user_scores, figure["profile"])
        # 完全な同点でも登録順で決まり、必ず1人に確定
        ranked.append((d, idx, figure))
    ranked.sort(key=lambda x: (round(x[0], 10), x[1]))
    return ranked


def similarity_percent(d):
    # 最大理論距離は200。距離を0～100%へ変換
    return max(0, min(100, round(100 * (1 - d / 200))))


def compatibility_score(base_profile, other_profile):
    """
    相性は単なる同一性ではなく、
    重要軸は近さ、挑戦性・社交性・行動性は適度な補完も評価。
    """
    stable_axes = ["logic", "structure", "empathy", "resilience", "idealism"]
    complement_axes = ["novelty", "social", "action", "leadership", "independence"]

    similarity = sum(1 - abs(base_profile[a] - other_profile[a]) / 200 for a in stable_axes) / len(stable_axes)

    # 補完軸は、完全な真逆ではなく「少し違う」ほど加点
    complement_parts = []
    for a in complement_axes:
        diff = abs(base_profile[a] - other_profile[a])
        # 差60前後を高評価
        complement_parts.append(max(0, 1 - abs(diff - 60) / 140))
    complement = sum(complement_parts) / len(complement_parts)

    return 0.65 * similarity + 0.35 * complement


def get_compatible_figures(result_figure, n=3):
    scored = []
    for f in FIGURES:
        if f["name"] == result_figure["name"]:
            continue
        scored.append((compatibility_score(result_figure["profile"], f["profile"]), f))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in scored[:n]]


def axis_explanation(scores, figure):
    # 人物に近い軸を3つ、ユーザーの特徴が強い軸を2つ説明
    closeness = sorted(
        AXES.keys(),
        key=lambda a: abs(scores[a] - figure["profile"][a])
    )[:3]

    strongest = sorted(
        AXES.keys(),
        key=lambda a: abs(scores[a]),
        reverse=True
    )[:2]

    parts = []
    for a in closeness:
        meta = AXES[a]
        side = meta["high"] if scores[a] >= 0 else meta["low"]
        parts.append(f"{meta['name']}（{side}）")

    extra = []
    for a in strongest:
        meta = AXES[a]
        side = meta["high"] if scores[a] >= 0 else meta["low"]
        extra.append(f"{meta['name']}は「{side}」寄り")

    return (
        f"あなたは特に、{figure['name']}の"
        + "・".join(parts)
        + "の傾向に近く判定されました。"
        + " また、"
        + "、".join(extra)
        + "という特徴が診断結果に強く表れています。"
    )


# =========================================================
# セッション初期化
# =========================================================
defaults = {
    "started": False,
    "page": 0,
    "answers": {},
    "completed": False,
    "result_id": None,
    "result_data": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_diagnosis():
    st.session_state.started = False
    st.session_state.page = 0
    st.session_state.answers = {}
    st.session_state.completed = False
    st.session_state.result_id = None
    st.session_state.result_data = None


# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>
.block-container {
    max-width: 900px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}
.hero {
    padding: 1.4rem 1.5rem;
    border-radius: 18px;
    border: 1px solid rgba(128,128,128,.25);
    margin-bottom: 1rem;
}
.privacy {
    padding: 1rem 1.1rem;
    border-radius: 14px;
    border: 1px solid rgba(128,128,128,.25);
    margin: .7rem 0 1rem 0;
}
.result-card {
    padding: 1.4rem 1.5rem;
    border-radius: 18px;
    border: 1px solid rgba(128,128,128,.28);
    margin: 1rem 0;
}
.small {
    font-size: .9rem;
    opacity: .78;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# ヘッダー
# =========================================================
st.markdown(f"""
<div class="hero">
    <h1>{APP_TITLE}</h1>
    <p><b>100の質問 × 10の性格軸 × 20人の歴史的人物</b></p>
    <p>5段階回答を点数化し、10軸のプロフィールから最も近い人物を必ず1人選出します。</p>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("質問", "100")
c2.metric("回答", "5択")
c3.metric("性格軸", "10")
c4.metric("人物候補", "20")


# =========================================================
# 結果画面
# =========================================================
if st.session_state.completed and st.session_state.result_data:
    data = st.session_state.result_data
    figure = data["figure"]
    scores = data["scores"]
    ranked = data["ranked"]
    compatible = data["compatible"]

    top_distance = ranked[0][0]
    match = similarity_percent(top_distance)

    st.success("診断が完了しました。")
    st.markdown(f"""
    <div class="result-card">
        <div style="font-size:3rem">{figure['emoji']}</div>
        <h2>あなたのタイプ：{figure['name']}</h2>
        <h3>{figure['tagline']}</h3>
        <p><b>マッチ度：{match}%</b></p>
        <p class="small">※人物プロフィールはこの診断のためのモデル化であり、歴史学・心理学上の確定的評価ではありません。</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("🔍 判断理由")
    st.write(axis_explanation(scores, figure))

    st.subheader("📊 10の性格軸")
    for axis, meta in AXES.items():
        value = scores[axis]
        # 0～100にしてprogressへ
        progress = int(round((value + 100) / 2))
        st.write(f"**{meta['name']}**　{value:+.0f}　（{meta['low']} ←→ {meta['high']}）")
        st.progress(max(0, min(100, progress)))

    st.subheader("💼 向いている仕事")
    st.write("・".join(figure["jobs"]))
    st.caption("職業適性を保証するものではなく、性格傾向から見た参考候補です。")

    st.subheader("🤝 相性の良いタイプ")
    cols = st.columns(3)
    for col, comp in zip(cols, compatible):
        with col:
            st.markdown(f"### {comp['emoji']} {comp['name']}")
            st.caption(comp["tagline"])

    st.subheader("🏅 近かった人物 TOP3")
    for rank, (d, _, f) in enumerate(ranked[:3], start=1):
        st.write(f"{rank}. **{f['name']}** — マッチ度 {similarity_percent(d)}%")

    # 保存用JSON
    export_data = {
        "diagnosis_id": st.session_state.result_id,
        "result": figure["name"],
        "match_percent": match,
        "axis_scores": scores,
        "answers": [
            {
                "no": i + 1,
                "question": QUESTIONS[i]["text"],
                "answer": st.session_state.answers[i],
                "score": CHOICE_SCORES[st.session_state.answers[i]] * QUESTIONS[i]["direction"],
                "axis": AXES[QUESTIONS[i]["axis"]]["name"],
            }
            for i in range(100)
        ],
    }

    st.download_button(
        "💾 診断結果・回答をJSONで保存",
        data=json.dumps(export_data, ensure_ascii=False, indent=2),
        file_name=f"historical_personality_{st.session_state.result_id}.json",
        mime="application/json",
        use_container_width=True,
    )

    # SNS共有
    st.subheader("📣 SNSでシェア")
    share_text = f"私の歴史上の人物タイプは「{figure['name']}」でした！ {figure['tagline']} #歴史上の人物性格診断"
    x_url = f"https://twitter.com/intent/tweet?text={quote(share_text)}&url={quote(APP_URL)}"
    line_url = f"https://social-plugins.line.me/lineit/share?url={quote(APP_URL)}&text={quote(share_text)}"
    fb_url = f"https://www.facebook.com/sharer/sharer.php?u={quote(APP_URL)}"

    s1, s2, s3 = st.columns(3)
    s1.link_button("Xで投稿", x_url, use_container_width=True)
    s2.link_button("LINEで送る", line_url, use_container_width=True)
    s3.link_button("Facebookで共有", fb_url, use_container_width=True)

    st.divider()
    if st.button("🔄 もう一度診断する", use_container_width=True):
        reset_diagnosis()
        st.rerun()

    st.stop()


# =========================================================
# 開始前
# =========================================================
if not st.session_state.started:
    st.markdown("""
    <div class="privacy">
        <h3>🔐 プライバシー設計</h3>
        <p><b>氏名・メールアドレスの入力は不要です。</b></p>
        <p>生のIPアドレスは保存せず、サーバー側でソルト付きHMAC-SHA256に変換した識別子だけを保存します。
        これにより、同一IP由来の診断を擬似的に紐付けつつ、生IPをそのままデータベースへ残さない設計です。</p>
        <p class="small">ただし、IP由来の識別子を利用する以上「完全匿名」を保証するものではありません。
        また、共有回線・VPN・携帯回線では同一人物を正確に識別できない場合があります。</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("20人の候補を見る"):
        men = [f["name"] for f in FIGURES if f["gender"] == "男性"]
        women = [f["name"] for f in FIGURES if f["gender"] == "女性"]
        st.write("**男性10人**：" + "、".join(men))
        st.write("**女性10人**：" + "、".join(women))

    consent = st.checkbox(
        "上記のプライバシー説明を確認し、回答・診断結果・ハッシュ化IP識別子が保存されることに同意します。"
    )

    if st.button("診断を始める", type="primary", use_container_width=True, disabled=not consent):
        st.session_state.started = True
        st.session_state.page = 0
        st.rerun()

    st.caption("所要時間の目安は回答速度によって変わります。診断結果は娯楽・自己理解の参考として利用してください。")
    st.stop()


# =========================================================
# 質問画面：10問 × 10ページ
# =========================================================
QUESTIONS_PER_PAGE = 10
total_pages = math.ceil(len(QUESTIONS) / QUESTIONS_PER_PAGE)
page = st.session_state.page
start = page * QUESTIONS_PER_PAGE
end = min(start + QUESTIONS_PER_PAGE, len(QUESTIONS))

answered_count = len(st.session_state.answers)
st.progress(answered_count / 100)
st.write(f"**進捗：{answered_count} / 100問**　｜　ページ {page + 1} / {total_pages}")

with st.form(key=f"question_form_{page}"):
    page_values = {}

    for i in range(start, end):
        q = QUESTIONS[i]
        axis_name = AXES[q["axis"]]["name"]

        existing = st.session_state.answers.get(i)
        options = ["選択してください"] + CHOICES
        default_index = options.index(existing) if existing in options else 0

        st.markdown(f"### Q{i + 1}. {q['text']}")
        selected = st.radio(
            f"回答（{axis_name}）",
            options=options,
            index=default_index,
            key=f"radio_{i}",
            horizontal=False,
            label_visibility="collapsed",
        )
        page_values[i] = selected
        st.divider()

    col1, col2 = st.columns(2)
    back_clicked = col1.form_submit_button(
        "← 前へ",
        use_container_width=True,
        disabled=(page == 0),
    )
    next_label = "診断結果を見る" if page == total_pages - 1 else "次へ →"
    next_clicked = col2.form_submit_button(
        next_label,
        type="primary",
        use_container_width=True,
    )

if back_clicked:
    # 現ページで選択済みのものだけ保存
    for i, selected in page_values.items():
        if selected in CHOICES:
            st.session_state.answers[i] = selected
    st.session_state.page = max(0, page - 1)
    st.rerun()

if next_clicked:
    missing = [i + 1 for i, selected in page_values.items() if selected not in CHOICES]
    if missing:
        st.error("このページのすべての質問に回答してください。未回答：" + "、".join(map(str, missing)))
    else:
        for i, selected in page_values.items():
            st.session_state.answers[i] = selected

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
                compatible = get_compatible_figures(winner, n=3)

                result_id = str(uuid.uuid4())
                ip_hash = hash_ip(get_client_ip())

                saved = save_result(
                    result_id=result_id,
                    ip_hash=ip_hash,
                    result_name=winner["name"],
                    scores=scores,
                    answers=st.session_state.answers,
                )

                st.session_state.result_id = result_id
                st.session_state.result_data = {
                    "figure": winner,
                    "scores": scores,
                    "ranked": ranked,
                    "compatible": compatible,
                    "saved": saved,
                }
                st.session_state.completed = True
                st.rerun()
