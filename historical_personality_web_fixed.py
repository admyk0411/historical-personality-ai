import streamlit as st
import math
import json
from datetime import datetime

# ============================================================
#  HISTORICAL PERSONALITY
#  歴史上の人物 性格診断 - 完成版
#  外部API不要 / 追加ライブラリ不要
# ============================================================

st.set_page_config(
    page_title="歴史上の人物 性格診断",
    page_icon="🏛️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ============================================================
# デザイン
# ============================================================

st.markdown("""
<style>

.block-container {
    max-width: 850px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

.hero {
    text-align: center;
    padding: 35px 15px 20px 15px;
}

.hero-title {
    font-size: 46px;
    font-weight: 900;
    line-height: 1.15;
    margin-bottom: 12px;
}

.hero-sub {
    font-size: 18px;
    opacity: 0.75;
    line-height: 1.8;
}

.question-card {
    padding: 28px;
    border: 1px solid rgba(128,128,128,0.25);
    border-radius: 22px;
    margin: 18px 0 22px 0;
    box-shadow: 0 5px 20px rgba(0,0,0,0.04);
}

.question-number {
    font-size: 14px;
    opacity: 0.65;
    margin-bottom: 8px;
}

.question-text {
    font-size: 25px;
    font-weight: 750;
    line-height: 1.55;
}

.result-hero {
    text-align: center;
    padding: 36px 20px;
    border-radius: 25px;
    border: 1px solid rgba(128,128,128,0.25);
    box-shadow: 0 8px 28px rgba(0,0,0,0.05);
    margin-bottom: 25px;
}

.result-label {
    opacity: 0.7;
    font-size: 16px;
}

.result-name {
    font-size: 43px;
    font-weight: 900;
    margin-top: 8px;
}

.result-title {
    font-size: 22px;
    font-weight: 700;
    margin-top: 8px;
}

.similarity {
    font-size: 28px;
    font-weight: 800;
    margin-top: 15px;
}

.person-card {
    padding: 20px;
    border-radius: 18px;
    border: 1px solid rgba(128,128,128,0.22);
    margin-bottom: 12px;
}

.big-score {
    font-size: 30px;
    font-weight: 800;
}

.small-muted {
    font-size: 14px;
    opacity: 0.65;
}

.section-title {
    font-size: 28px;
    font-weight: 850;
    margin-top: 25px;
    margin-bottom: 15px;
}

.footer-note {
    font-size: 13px;
    opacity: 0.6;
    line-height: 1.8;
    text-align: center;
    margin-top: 40px;
}

div[data-testid="stRadio"] label {
    font-size: 17px;
}

.stButton > button {
    border-radius: 12px;
    min-height: 48px;
    font-weight: 700;
}

div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,0.18);
    border-radius: 15px;
    padding: 12px;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# 基本設定
# ============================================================

CATEGORIES = [
    "リーダーシップ",
    "挑戦心",
    "論理性",
    "共感性",
    "社交性",
    "創造性",
    "計画性",
    "独立性",
    "忍耐力",
    "好奇心"
]

CHOICES = [
    "とてもそう思う",
    "そう思う",
    "どちらともいえない",
    "そう思わない",
    "まったくそう思わない"
]

CHOICE_TO_SCORE = {
    "とてもそう思う": 5,
    "そう思う": 4,
    "どちらともいえない": 3,
    "そう思わない": 2,
    "まったくそう思わない": 1
}

# ============================================================
# 100問
#
# 第3要素:
#  1  = 通常採点
# -1  = 逆転採点
#
# 逆転項目を混ぜ、単純に全部「そう思う」を選んだだけでは
# すべての能力が高くならないようにしています。
# ============================================================

QUESTIONS = [

    # ---------------- リーダーシップ 10 ----------------

    ("集団では、自分から方向性を示すことが多い",
     "リーダーシップ", 1),

    ("責任のある役割を任されるとやる気が出る",
     "リーダーシップ", 1),

    ("重要な場面では自分で決断したい",
     "リーダーシップ", 1),

    ("周囲をまとめて目標に向かわせることが得意だ",
     "リーダーシップ", 1),

    ("意見が割れたときでも最終判断を下せる",
     "リーダーシップ", 1),

    ("人前に立って指示することに抵抗がない",
     "リーダーシップ", 1),

    ("問題が起きたとき、人が動くのを待つことが多い",
     "リーダーシップ", -1),

    ("大きな責任はできるだけ他人に任せたい",
     "リーダーシップ", -1),

    ("チームの成功に自分が責任を持ちたい",
     "リーダーシップ", 1),

    ("必要なときには反対されても決断できる",
     "リーダーシップ", 1),

    # ---------------- 挑戦心 10 ----------------

    ("新しいことに挑戦するのが好きだ",
     "挑戦心", 1),

    ("失敗する可能性があっても価値があれば挑戦したい",
     "挑戦心", 1),

    ("難しい課題ほどやる気が出る",
     "挑戦心", 1),

    ("未知の環境に入ることを楽しめる",
     "挑戦心", 1),

    ("安全だけを選ぶより成長できる道を選びたい",
     "挑戦心", 1),

    ("周囲がやったことのない方法を試してみたい",
     "挑戦心", 1),

    ("失敗すると再び挑戦するのが怖くなる",
     "挑戦心", -1),

    ("変化が大きい環境はできるだけ避けたい",
     "挑戦心", -1),

    ("高い目標を設定することが多い",
     "挑戦心", 1),

    ("自分の限界を試してみたいと思う",
     "挑戦心", 1),

    # ---------------- 論理性 10 ----------------

    ("結論を出す前に根拠を確認する",
     "論理性", 1),

    ("問題が起きると原因を整理して考える",
     "論理性", 1),

    ("数字やデータを使って考えることが好きだ",
     "論理性", 1),

    ("複雑な問題を小さく分けて考えることが多い",
     "論理性", 1),

    ("矛盾した説明を聞くと気になる",
     "論理性", 1),

    ("自分の考えが間違っていないか検証する",
     "論理性", 1),

    ("根拠がなくても直感だけで決めることが多い",
     "論理性", -1),

    ("データより、その場の雰囲気だけで判断することが多い",
     "論理性", -1),

    ("仕組みや原因を理解したくなる",
     "論理性", 1),

    ("感情と事実を分けて考えることができる",
     "論理性", 1),

    # ---------------- 共感性 10 ----------------

    ("相手の立場になって考えることが多い",
     "共感性", 1),

    ("困っている人を見ると助けたくなる",
     "共感性", 1),

    ("人の感情の変化に気づきやすい",
     "共感性", 1),

    ("相手が傷つかないように言葉を選ぶ",
     "共感性", 1),

    ("誰かの役に立つと嬉しい",
     "共感性", 1),

    ("自分と違う価値観でも理解しようとする",
     "共感性", 1),

    ("他人がどう感じるかはあまり気にならない",
     "共感性", -1),

    ("目的達成のためなら人の気持ちは重要ではないと思う",
     "共感性", -1),

    ("人から相談を受けたとき、まず話を聞こうとする",
     "共感性", 1),

    ("自分の利益だけでなく周囲への影響も考える",
     "共感性", 1),

    # ---------------- 社交性 10 ----------------

    ("初対面の人とも比較的すぐに話せる",
     "社交性", 1),

    ("多くの人と交流することが好きだ",
     "社交性", 1),

    ("人と話すことで元気になることが多い",
     "社交性", 1),

    ("新しい人間関係を作るのが好きだ",
     "社交性", 1),

    ("会話では自分から話題を出すことが多い",
     "社交性", 1),

    ("人が集まる場所を楽しめる",
     "社交性", 1),

    ("知らない人とはできるだけ話したくない",
     "社交性", -1),

    ("大勢の人と過ごすと常に苦痛に感じる",
     "社交性", -1),

    ("人前で話すことに比較的抵抗がない",
     "社交性", 1),

    ("人と人をつなげることが好きだ",
     "社交性", 1),

    # ---------------- 創造性 10 ----------------

    ("新しいアイデアを考えるのが好きだ",
     "創造性", 1),

    ("普通とは違う方法を考えることが多い",
     "創造性", 1),

    ("当たり前とされていることを疑うことがある",
     "創造性", 1),

    ("自由に想像することを楽しめる",
     "創造性", 1),

    ("既存の仕組みを見ると改善案を考えたくなる",
     "創造性", 1),

    ("異なる分野の知識を組み合わせるのが好きだ",
     "創造性", 1),

    ("決められた方法以外はなるべく考えたくない",
     "創造性", -1),

    ("新しいアイデアより昔からの方法だけを使いたい",
     "創造性", -1),

    ("未来の可能性について考えることが多い",
     "創造性", 1),

    ("一つの問題に複数の解決方法を考える",
     "創造性", 1),

    # ---------------- 計画性 10 ----------------

    ("行動する前に計画を立てることが多い",
     "計画性", 1),

    ("期限より余裕を持って取り組みたい",
     "計画性", 1),

    ("目標までの手順を考える",
     "計画性", 1),

    ("優先順位をつけて物事を進める",
     "計画性", 1),

    ("長期的な視点で予定を考える",
     "計画性", 1),

    ("準備をしてから重要なことに取り組む",
     "計画性", 1),

    ("締め切り直前まで何もしないことが多い",
     "計画性", -1),

    ("予定を立てず、その場の気分だけで行動することが多い",
     "計画性", -1),

    ("大きな目標を小さな行動に分けることができる",
     "計画性", 1),

    ("計画が崩れたときには新しい計画を作り直せる",
     "計画性", 1),

    # ---------------- 独立性 10 ----------------

    ("周囲と違う意見でも必要なら発言できる",
     "独立性", 1),

    ("自分なりの価値観を大切にしている",
     "独立性", 1),

    ("一人でも目標に向かって行動できる",
     "独立性", 1),

    ("多数派の意見でも疑問があれば考え直す",
     "独立性", 1),

    ("重要なことは自分で納得してから決めたい",
     "独立性", 1),

    ("他人から評価されなくても必要な努力を続けられる",
     "独立性", 1),

    ("周囲に反対されると、自分の考えをすぐ変える",
     "独立性", -1),

    ("自分で判断するより常に他人に決めてもらいたい",
     "独立性", -1),

    ("一人で考える時間を大切にしている",
     "独立性", 1),

    ("自分の選択に責任を持ちたい",
     "独立性", 1),

    # ---------------- 忍耐力 10 ----------------

    ("長期間努力を続けることができる",
     "忍耐力", 1),

    ("すぐに結果が出なくても努力できる",
     "忍耐力", 1),

    ("失敗しても原因を考えて再挑戦する",
     "忍耐力", 1),

    ("困難な状況でもある程度冷静さを保てる",
     "忍耐力", 1),

    ("目標のためなら地道な作業を続けられる",
     "忍耐力", 1),

    ("途中で壁にぶつかっても簡単には諦めない",
     "忍耐力", 1),

    ("成果がすぐ出ないと途中で投げ出すことが多い",
     "忍耐力", -1),

    ("一度失敗すると、そのことを続ける気がなくなる",
     "忍耐力", -1),

    ("プレッシャーがあっても必要な行動を続けられる",
     "忍耐力", 1),

    ("小さな努力を積み重ねることができる",
     "忍耐力", 1),

    # ---------------- 好奇心 10 ----------------

    ("知らないことを調べるのが好きだ",
     "好奇心", 1),

    ("興味を持ったことは深く調べたくなる",
     "好奇心", 1),

    ("幅広い分野について学びたい",
     "好奇心", 1),

    ("新しい技術や考え方に興味がある",
     "好奇心", 1),

    ("なぜそうなるのか考えることが多い",
     "好奇心", 1),

    ("知らない世界について知るとワクワクする",
     "好奇心", 1),

    ("新しい知識を学ぶのは面倒だと感じることが多い",
     "好奇心", -1),

    ("自分の専門外のことにはほとんど興味がない",
     "好奇心", -1),

    ("本・動画・記事などから新しい知識を得るのが好きだ",
     "好奇心", 1),

    ("一つの疑問から別の疑問が次々に生まれることがある",
     "好奇心", 1)
]

# ============================================================
# 歴史上の人物プロフィール
#
# 数値は心理検査などで測定された歴史的事実ではなく、
# 診断ゲーム用に人物像をモデル化した値です。
# ============================================================

PEOPLE = {

    "織田信長": {
        "emoji": "⚔️",
        "country": "日本",
        "title": "常識を壊す革新者",
        "scores": [5.0,5.0,4.2,2.4,3.5,5.0,4.0,5.0,4.1,4.5],
        "summary":
            "既存の常識に縛られず、必要なら仕組みそのものを変えてしまう改革型。",
        "strength":
            "決断力、改革力、スピード、独立した判断",
        "watch":
            "目的を急ぐあまり、周囲の感情や合意形成を置き去りにしやすい。",
        "environment":
            "変革期、新規事業、競争の激しい環境、裁量が大きい仕事"
    },

    "徳川家康": {
        "emoji": "🏯",
        "country": "日本",
        "title": "最後に勝つ長期戦略家",
        "scores": [4.7,3.2,4.7,3.4,3.1,3.1,5.0,4.1,5.0,3.7],
        "summary":
            "短期的な勢いより、状況を読みながら長期的に勝ち筋を作る安定型。",
        "strength":
            "計画性、忍耐力、危機管理、長期的判断",
        "watch":
            "慎重になりすぎると、大きなチャンスへの初動が遅くなることがある。",
        "environment":
            "経営、長期プロジェクト、組織運営、リスク管理"
    },

    "豊臣秀吉": {
        "emoji": "☀️",
        "country": "日本",
        "title": "人を巻き込む成り上がり型",
        "scores": [4.8,4.8,3.9,3.5,5.0,4.1,4.0,4.0,4.7,4.1],
        "summary":
            "人間関係と行動力を武器に、チャンスをつかんで一気に前進するタイプ。",
        "strength":
            "社交性、行動力、適応力、人を動かす力",
        "watch":
            "成功体験が大きくなるほど、自分の判断を過信しないことが重要。",
        "environment":
            "営業、交渉、マネジメント、人脈を活用する仕事"
    },

    "坂本龍馬": {
        "emoji": "🌊",
        "country": "日本",
        "title": "人と未来をつなぐ改革者",
        "scores": [4.2,5.0,4.0,4.1,4.8,4.8,3.3,4.8,4.0,5.0],
        "summary":
            "新しい世界への好奇心と人をつなぐ能力で変化を生み出す自由な改革型。",
        "strength":
            "行動力、柔軟性、好奇心、人的ネットワーク",
        "watch":
            "アイデアが多い分、細かな管理や継続的な運用を意識するとさらに強い。",
        "environment":
            "新規事業、起業、営業、企画、変化の大きい組織"
    },

    "西郷隆盛": {
        "emoji": "🌋",
        "country": "日本",
        "title": "信頼で人を導く人格派",
        "scores": [4.8,4.1,3.4,5.0,4.0,3.0,3.5,4.3,5.0,3.3],
        "summary":
            "合理性だけではなく、人との信頼や責任を重視して集団をまとめるタイプ。",
        "strength":
            "人望、共感力、責任感、忍耐力",
        "watch":
            "情を重視しすぎると、合理的な判断との間で葛藤することがある。",
        "environment":
            "組織マネジメント、教育、公共性の高い仕事、チーム運営"
    },

    "宮本武蔵": {
        "emoji": "🗡️",
        "country": "日本",
        "title": "孤高の自己鍛錬型",
        "scores": [3.4,4.8,4.6,2.5,2.2,4.0,4.0,5.0,5.0,4.1],
        "summary":
            "他人との比較より、自分自身の技術と戦略を磨き続ける独立型。",
        "strength":
            "集中力、自己改善、独立性、勝負強さ",
        "watch":
            "一人で完結しようとせず、他者との協力を取り入れると可能性が広がる。",
        "environment":
            "専門職、研究、職人型の仕事、個人裁量の大きい環境"
    },

    "福沢諭吉": {
        "emoji": "📚",
        "country": "日本",
        "title": "学びを武器にする独立思考型",
        "scores": [4.0,4.1,4.8,3.8,3.7,4.2,4.1,5.0,4.2,5.0],
        "summary":
            "知識を得て自分の頭で考え、既存の価値観から精神的に独立しようとするタイプ。",
        "strength":
            "学習力、合理性、独立心、知識の応用",
        "watch":
            "考えを深めるだけでなく、現場で試すことでさらに強みが活きる。",
        "environment":
            "教育、コンサルティング、企画、知識集約型の仕事"
    },

    "諸葛亮": {
        "emoji": "🪶",
        "country": "中国",
        "title": "先を読む知略家",
        "scores": [4.2,3.2,5.0,4.0,2.5,4.2,5.0,4.3,4.8,4.8],
        "summary":
            "情報を集め、複数の可能性を考えた上で勝ち筋を組み立てる分析型。",
        "strength":
            "分析力、計画性、戦略思考、問題解決",
        "watch":
            "考え抜くことが強みだが、完全な情報を待ち続けないことも重要。",
        "environment":
            "戦略、IT、コンサルティング、企画、プロジェクト管理"
    },

    "ナポレオン": {
        "emoji": "👑",
        "country": "フランス",
        "title": "圧倒的な実行型リーダー",
        "scores": [5.0,5.0,4.8,2.3,4.1,4.0,4.7,5.0,4.8,4.2],
        "summary":
            "高い目標を掲げ、戦略を立て、強い意志で組織を前進させる実行型。",
        "strength":
            "リーダーシップ、戦略性、決断、実行力",
        "watch":
            "成功が続いているときほど、異論やリスク情報を意識的に取り入れる必要がある。",
        "environment":
            "経営、マネジメント、事業責任者、高競争環境"
    },

    "レオナルド・ダ・ヴィンチ": {
        "emoji": "🎨",
        "country": "イタリア",
        "title": "境界を越える万能探究者",
        "scores": [2.7,4.2,4.8,3.4,2.8,5.0,3.1,4.8,4.0,5.0],
        "summary":
            "分野の境界を気にせず、興味のままに観察・研究・創造を繰り返す探究型。",
        "strength":
            "創造性、好奇心、観察力、学際的思考",
        "watch":
            "興味が広がりすぎると、完成より次のアイデアへ進みやすい。",
        "environment":
            "研究、デザイン、開発、クリエイティブ、新しい技術領域"
    },

    "アインシュタイン": {
        "emoji": "🧠",
        "country": "ドイツ生まれ",
        "title": "常識を疑う思索家",
        "scores": [2.6,4.0,5.0,3.8,2.4,5.0,3.0,5.0,4.7,5.0],
        "summary":
            "常識をそのまま受け入れず、自分の思考によって物事の本質を追究するタイプ。",
        "strength":
            "論理性、独創性、独立思考、探究心",
        "watch":
            "思考の世界だけで完結せず、人との対話によって考えを磨くとさらに強い。",
        "environment":
            "研究、技術、分析、専門職、自由度の高い知的環境"
    },

    "ガンジー": {
        "emoji": "🕊️",
        "country": "インド",
        "title": "信念で人を動かす理想型",
        "scores": [4.6,4.1,4.1,5.0,4.0,3.5,4.2,4.8,5.0,4.2],
        "summary":
            "強い価値観と共感性を持ち、長期的な信念によって周囲を動かすタイプ。",
        "strength":
            "共感性、信念、忍耐力、社会的影響力",
        "watch":
            "理念を重視するあまり、自分自身への負担を大きくしすぎないことが重要。",
        "environment":
            "社会活動、教育、組織づくり、理念を重視する仕事"
    },

    "マリー・キュリー": {
        "emoji": "⚗️",
        "country": "ポーランド生まれ",
        "title": "静かな情熱を持つ研究者",
        "scores": [3.2,4.5,5.0,3.8,2.3,4.0,4.6,4.7,5.0,5.0],
        "summary":
            "派手さよりも知識と成果を重視し、一つのテーマを粘り強く追究するタイプ。",
        "strength":
            "探究心、忍耐力、論理性、集中力",
        "watch":
            "自分だけで抱え込まず、成果や考えを周囲と共有することも大切。",
        "environment":
            "研究、技術開発、専門職、長期的な課題に取り組む環境"
    },

    "ベンジャミン・フランクリン": {
        "emoji": "⚡",
        "country": "アメリカ",
        "title": "実用知を追う万能型",
        "scores": [4.2,4.4,4.6,4.0,4.5,4.7,4.5,4.5,4.5,5.0],
        "summary":
            "知識を得るだけでなく、社会や日常の問題に応用することを好むバランス型。",
        "strength":
            "好奇心、実践力、社交性、問題解決",
        "watch":
            "多方面で力を発揮できる反面、優先順位を明確にするとさらに成果が出やすい。",
        "environment":
            "起業、企画、研究、公共分野、複数領域を扱う仕事"
    },

    "エイブラハム・リンカーン": {
        "emoji": "🎩",
        "country": "アメリカ",
        "title": "逆境に耐える調整型リーダー",
        "scores": [4.8,4.2,4.5,4.8,3.7,3.7,4.4,4.7,5.0,4.3],
        "summary":
            "厳しい状況でも粘り強く、異なる立場を理解しながら大きな判断をするタイプ。",
        "strength":
            "忍耐力、共感性、責任感、調整力",
        "watch":
            "多くの立場を考えることで、決断までに精神的負担を抱えやすい。",
        "environment":
            "リーダー、マネジメント、交渉、公共性のある仕事"
    },

    "フローレンス・ナイチンゲール": {
        "emoji": "🕯️",
        "country": "イギリス",
        "title": "人を救うデータ改革者",
        "scores": [4.5,4.3,4.8,5.0,3.2,4.0,4.8,4.6,5.0,4.6],
        "summary":
            "人への強い関心と合理的な分析を組み合わせ、仕組みそのものを改善するタイプ。",
        "strength":
            "共感性、論理性、改革力、継続力",
        "watch":
            "責任感が強いため、自分自身にも厳しくなりすぎないことが重要。",
        "environment":
            "医療、公共分野、データ分析、業務改善、社会課題解決"
    },

    "スティーブ・ジョブズ": {
        "emoji": "💻",
        "country": "アメリカ",
        "title": "未来を形にする革新者",
        "scores": [4.8,5.0,4.2,2.5,4.0,5.0,4.2,5.0,4.7,5.0],
        "summary":
            "強いビジョンと美意識を持ち、まだ存在しない価値を形にしようとするタイプ。",
        "strength":
            "創造性、ビジョン、挑戦心、実行力",
        "watch":
            "高い基準を周囲にも求めすぎると、人間関係の摩擦につながることがある。",
        "environment":
            "起業、プロダクト開発、新規事業、デザイン、テクノロジー"
    },

    "ココ・シャネル": {
        "emoji": "🖤",
        "country": "フランス",
        "title": "自分の価値観を貫く創造者",
        "scores": [4.0,4.8,3.8,3.1,4.0,5.0,3.8,5.0,4.7,4.3],
        "summary":
            "社会の常識より自分自身の美意識を信じ、新しい価値観を作り出すタイプ。",
        "strength":
            "創造性、独立性、挑戦心、ブランド構築",
        "watch":
            "強い自己基準があるため、他者からの有益な意見も選択的に取り入れるとよい。",
        "environment":
            "デザイン、ブランド、起業、クリエイティブ産業"
    },

    "ネルソン・マンデラ": {
        "emoji": "🤝",
        "country": "南アフリカ",
        "title": "対立を越える統合型リーダー",
        "scores": [4.8,4.5,4.2,5.0,4.5,3.5,4.2,4.7,5.0,4.0],
        "summary":
            "強い信念を持ちながら、敵対する相手とも対話し、大きな目的へ人々をまとめるタイプ。",
        "strength":
            "共感性、忍耐力、リーダーシップ、調整力",
        "watch":
            "周囲の期待を背負いすぎず、自分のエネルギー管理も意識するとよい。",
        "environment":
            "経営、交渉、組織変革、社会課題、チームマネジメント"
    },

    "トーマス・エジソン": {
        "emoji": "💡",
        "country": "アメリカ",
        "title": "試して直す実験型",
        "scores": [4.0,5.0,4.4,2.8,3.5,4.8,4.2,4.6,5.0,4.9],
        "summary":
            "アイデアを考えるだけでなく、何度も実験して実用化へ近づける試行錯誤型。",
        "strength":
            "挑戦心、忍耐力、実験精神、実用化能力",
        "watch":
            "結果を追求するときほど、周囲との関係や役割分担を意識することも大切。",
        "environment":
            "研究開発、起業、プロダクト開発、技術職"
    }
}

# ============================================================
# 性格軸の説明
# ============================================================

CATEGORY_INFO = {

    "リーダーシップ": {
        "high": "人をまとめ、判断し、方向性を示す力が強い",
        "mid": "必要に応じて前にも後ろにも回れる",
        "low": "自分が指揮するより、専門性や支援役で力を発揮しやすい"
    },

    "挑戦心": {
        "high": "未知のことや難しい課題にも踏み込める",
        "mid": "リスクと安定のバランスを取る",
        "low": "安全性や確実性を確認してから動く傾向が強い"
    },

    "論理性": {
        "high": "根拠、構造、データをもとに考える",
        "mid": "論理と直感の両方を使う",
        "low": "感覚や経験、人間的な要素を重視しやすい"
    },

    "共感性": {
        "high": "他者の立場や感情を強く意識できる",
        "mid": "相手への配慮と自分の判断を両立する",
        "low": "感情より目的や合理性を優先しやすい"
    },

    "社交性": {
        "high": "人との交流からエネルギーを得やすい",
        "mid": "一人の時間と交流の両方を必要とする",
        "low": "少人数や一人で集中する環境を好みやすい"
    },

    "創造性": {
        "high": "既存の枠を越えた発想を生み出しやすい",
        "mid": "新しさと現実性をバランスよく考える",
        "low": "実績のある方法や再現性を重視しやすい"
    },

    "計画性": {
        "high": "先を見通し、手順を作って進める",
        "mid": "計画しつつ状況に応じて変更できる",
        "low": "その場の状況を見ながら柔軟に動く"
    },

    "独立性": {
        "high": "周囲に流されず自分で判断する",
        "mid": "自分の考えと他人の意見を組み合わせる",
        "low": "周囲との合意や共同判断を重視しやすい"
    },

    "忍耐力": {
        "high": "長期間の努力や逆境に粘り強い",
        "mid": "必要な範囲で継続し、切り替えもできる",
        "low": "短期間で結果が出る課題の方が力を発揮しやすい"
    },

    "好奇心": {
        "high": "未知の知識や分野を積極的に学ぶ",
        "mid": "必要性や興味に応じて学ぶ",
        "low": "既に知っている領域を深めることを好みやすい"
    }
}

# ============================================================
# セッション初期化
# ============================================================

DEFAULT_STATE = {
    "page": "start",
    "name": "",
    "question_index": 0,
    "answers": {},
    "result_scores": None,
    "ranking": None
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ============================================================
# 関数
# ============================================================

def reset_app():
    keys = list(st.session_state.keys())

    for key in keys:
        del st.session_state[key]

    st.rerun()


def reverse_score(score):
    return 6 - score


def calculate_scores():

    totals = {cat: 0 for cat in CATEGORIES}
    counts = {cat: 0 for cat in CATEGORIES}

    for i, raw_score in st.session_state.answers.items():

        question, category, direction = QUESTIONS[i]

        score = raw_score

        if direction == -1:
            score = reverse_score(score)

        totals[category] += score
        counts[category] += 1

    result = {}

    for category in CATEGORIES:

        if counts[category] > 0:
            result[category] = round(
                totals[category] / counts[category],
                2
            )
        else:
            result[category] = 3.0

    return result


def calculate_ranking(scores):

    ranking = []

    # 最大距離
    max_distance = math.sqrt(
        len(CATEGORIES) * (4 ** 2)
    )

    for person, data in PEOPLE.items():

        distance_squared = 0

        for index, category in enumerate(CATEGORIES):

            user_value = scores[category]
            person_value = data["scores"][index]

            distance_squared += (
                user_value - person_value
            ) ** 2

        distance = math.sqrt(distance_squared)

        # 距離を類似度へ
        base_similarity = (
            1 - distance / max_distance
        ) * 100

        # 表示が極端に高くなり過ぎないよう
        # 診断ゲーム用の指数へ調整
        similarity = max(
            0,
            min(99.5, base_similarity)
        )

        ranking.append({
            "person": person,
            "similarity": round(similarity, 1),
            "distance": distance
        })

    ranking.sort(
        key=lambda x: x["distance"]
    )

    return ranking


def score_level(score):

    if score >= 4.3:
        return "非常に高い"

    elif score >= 3.7:
        return "高い"

    elif score >= 3.0:
        return "中程度"

    elif score >= 2.3:
        return "やや低い"

    else:
        return "低い"


def category_description(category, score):

    if score >= 3.8:
        return CATEGORY_INFO[category]["high"]

    elif score >= 2.8:
        return CATEGORY_INFO[category]["mid"]

    else:
        return CATEGORY_INFO[category]["low"]


def generate_personality_summary(scores):

    sorted_scores = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    top1, top2, top3 = sorted_scores[:3]
    low1, low2 = sorted_scores[-2:]

    return (
        f"あなたの性格で特に目立つのは"
        f"「{top1[0]}」「{top2[0]}」「{top3[0]}」です。"
        f"{top1[0]}が最も高く、"
        f"{category_description(top1[0], top1[1])}傾向があります。"
        f"さらに{top2[0]}と{top3[0]}も強いため、"
        f"一つの能力だけに依存せず、複数の特性を組み合わせて"
        f"行動するタイプと考えられます。"
        f"一方で「{low1[0]}」「{low2[0]}」は相対的に低めです。"
        f"これは弱点という意味ではなく、"
        f"あなたが自然にエネルギーを使う方向が他にあることを示しています。"
    )


def generate_type_name(scores):

    sorted_scores = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    a = sorted_scores[0][0]
    b = sorted_scores[1][0]

    combinations = {

        frozenset(["リーダーシップ","挑戦心"]):
            "🔥 開拓型リーダー",

        frozenset(["論理性","計画性"]):
            "♟️ 戦略設計型",

        frozenset(["創造性","好奇心"]):
            "💡 探究クリエイター",

        frozenset(["独立性","創造性"]):
            "🚀 独立革新型",

        frozenset(["共感性","リーダーシップ"]):
            "🤝 共感型リーダー",

        frozenset(["忍耐力","計画性"]):
            "🏯 長期積み上げ型",

        frozenset(["社交性","リーダーシップ"]):
            "🌟 巻き込み型リーダー",

        frozenset(["論理性","好奇心"]):
            "🔬 知的探究型",

        frozenset(["独立性","論理性"]):
            "🧠 独立思考型",

        frozenset(["社交性","共感性"]):
            "🌈 コネクター型"
    }

    pair = frozenset([a, b])

    return combinations.get(
        pair,
        f"✨ {a} × {b}型"
    )


def make_radar_svg(scores):

    width = 620
    height = 620

    cx = width / 2
    cy = height / 2

    radius = 205

    n = len(CATEGORIES)

    def point(angle, r):

        x = cx + math.cos(angle) * r
        y = cy + math.sin(angle) * r

        return x, y

    angles = [
        (-math.pi / 2)
        + (2 * math.pi * i / n)
        for i in range(n)
    ]

    grid_lines = ""

    # 五段階グリッド
    for level in range(1, 6):

        r = radius * level / 5

        pts = []

        for angle in angles:

            x, y = point(angle, r)

            pts.append(
                f"{x:.1f},{y:.1f}"
            )

        grid_lines += (
            f'<polygon points="{" ".join(pts)}" '
            f'fill="none" '
            f'stroke="rgba(128,128,128,0.28)" '
            f'stroke-width="1"/>'
        )

    # 軸
    axes = ""

    for angle in angles:

        x, y = point(angle, radius)

        axes += (
            f'<line x1="{cx}" y1="{cy}" '
            f'x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="rgba(128,128,128,0.23)" '
            f'stroke-width="1"/>'
        )

    # ユーザー値
    user_pts = []

    for category, angle in zip(
        CATEGORIES,
        angles
    ):

        value = scores[category]

        r = radius * value / 5

        x, y = point(angle, r)

        user_pts.append(
            f"{x:.1f},{y:.1f}"
        )

    polygon = (
        f'<polygon points="{" ".join(user_pts)}" '
        f'fill="rgba(80,120,255,0.25)" '
        f'stroke="rgba(80,120,255,0.95)" '
        f'stroke-width="3"/>'
    )

    # 点
    dots = ""

    for p in user_pts:

        x, y = p.split(",")

        dots += (
            f'<circle cx="{x}" cy="{y}" r="5" '
            f'fill="rgba(80,120,255,1)"/>'
        )

    # ラベル
    labels = ""

    label_radius = radius + 62

    for category, angle in zip(
        CATEGORIES,
        angles
    ):

        x, y = point(
            angle,
            label_radius
        )

        anchor = "middle"

        cos_value = math.cos(angle)

        if cos_value > 0.3:
            anchor = "start"

        elif cos_value < -0.3:
            anchor = "end"

        score = scores[category]

        labels += f"""
        <text
            x="{x:.1f}"
            y="{y:.1f}"
            text-anchor="{anchor}"
            dominant-baseline="middle"
            font-size="14"
            font-weight="700"
            fill="currentColor">
            {category}
        </text>

        <text
            x="{x:.1f}"
            y="{y + 18:.1f}"
            text-anchor="{anchor}"
            dominant-baseline="middle"
            font-size="12"
            fill="currentColor"
            opacity="0.65">
            {score:.1f}
        </text>
        """

    return f"""
    <div style="
        width:100%;
        overflow-x:auto;
        display:flex;
        justify-content:center;
    ">

    <svg
        viewBox="0 0 {width} {height}"
        style="
            max-width:620px;
            width:100%;
            height:auto;
        "
        xmlns="http://www.w3.org/2000/svg">

        {grid_lines}
        {axes}
        {polygon}
        {dots}
        {labels}

    </svg>

    </div>
    """


def build_report(
    name,
    scores,
    ranking
):

    best = ranking[0]

    person = best["person"]

    data = PEOPLE[person]

    sorted_scores = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    lines = []

    lines.append(
        "歴史上の人物 性格診断"
    )

    lines.append(
        "=" * 45
    )

    lines.append(
        f"名前: {name}"
    )

    lines.append(
        f"診断日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    lines.append("")

    lines.append(
        f"あなたのタイプ: {generate_type_name(scores)}"
    )

    lines.append(
        f"最も近い人物: {person}"
    )

    lines.append(
        f"人物タイプ: {data['title']}"
    )

    lines.append(
        f"類似度指数: {best['similarity']:.1f}%"
    )

    lines.append("")

    lines.append(
        "【性格総評】"
    )

    lines.append(
        generate_personality_summary(scores)
    )

    lines.append("")

    lines.append(
        "【人物との共通点】"
    )

    lines.append(
        data["summary"]
    )

    lines.append("")

    lines.append(
        "【強み】"
    )

    lines.append(
        data["strength"]
    )

    lines.append("")

    lines.append(
        "【意識するとよいこと】"
    )

    lines.append(
        data["watch"]
    )

    lines.append("")

    lines.append(
        "【力を発揮しやすい環境】"
    )

    lines.append(
        data["environment"]
    )

    lines.append("")

    lines.append(
        "【10の性格スコア】"
    )

    for category, score in sorted_scores:

        lines.append(
            f"{category}: "
            f"{score:.2f} / 5.00 "
            f"({score_level(score)})"
        )

    lines.append("")

    lines.append(
        "【近い人物ランキング】"
    )

    for i, item in enumerate(
        ranking[:5],
        start=1
    ):

        lines.append(
            f"{i}位 "
            f"{item['person']} "
            f"{item['similarity']:.1f}%"
        )

    lines.append("")

    lines.append(
        "※この診断は自己理解・娯楽を目的としたもので、"
        "医学的・心理学的診断ではありません。"
    )

    lines.append(
        "歴史上の人物のスコアは、診断用にモデル化した人物像です。"
    )

    return "\n".join(lines)


# ============================================================
# START PAGE
# ============================================================

if st.session_state.page == "start":

    st.markdown("""
    <div class="hero">

        <div class="hero-title">
            🏛️ 歴史上の人物<br>
            性格診断
        </div>

        <div class="hero-sub">
            100の質問からあなたの性格を10の軸で分析。<br>
            あなたに近い歴史上の人物を見つけます。
        </div>

    </div>
    """, unsafe_allow_html=True)

    st.write("")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "質問",
            "100問"
        )

    with c2:
        st.metric(
            "性格軸",
            "10種類"
        )

    with c3:
        st.metric(
            "人物",
            f"{len(PEOPLE)}人"
        )

    st.write("")

    with st.expander(
        "📖 この診断について",
        expanded=False
    ):

        st.write("""
        この診断では、あなたの回答を次の10項目に分けて分析します。

        **リーダーシップ / 挑戦心 / 論理性 / 共感性 /
        社交性 / 創造性 / 計画性 / 独立性 / 忍耐力 / 好奇心**

        それぞれを1〜5の範囲で数値化し、
        歴史上の人物をモデル化したプロフィールと比較します。

        回答には正解・不正解はありません。
        「理想の自分」ではなく、
        普段の自分に近いものを選ぶのがおすすめです。
        """)

    st.write("")

    entered_name = st.text_input(
        "あなたの名前・ニックネーム",
        placeholder="例：まさと",
        max_chars=30
    )

    st.caption(
        "名前は診断結果の表示にだけ使用します。"
    )

    if st.button(
        "診断をはじめる →",
        type="primary",
        use_container_width=True
    ):

        clean_name = entered_name.strip()

        if not clean_name:

            st.warning(
                "名前またはニックネームを入力してください。"
            )

        else:

            st.session_state.name = clean_name
            st.session_state.question_index = 0
            st.session_state.answers = {}
            st.session_state.page = "quiz"

            st.rerun()

# ============================================================
# QUIZ PAGE
# ============================================================

elif st.session_state.page == "quiz":

    current = st.session_state.question_index

    total_questions = len(QUESTIONS)

    question_text, category, direction = (
        QUESTIONS[current]
    )

    answered = len(
        st.session_state.answers
    )

    st.write(
        f"**{st.session_state.name} さんの診断**"
    )

    st.progress(
        answered / total_questions
    )

    left, right = st.columns(2)

    with left:

        st.caption(
            f"回答済み {answered} / {total_questions}"
        )

    with right:

        st.caption(
            f"現在 Q{current + 1}"
        )

    st.markdown(
        f"""
        <div class="question-card">

            <div class="question-number">
                QUESTION {current + 1} / {total_questions}
            </div>

            <div class="question-text">
                {question_text}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    # 以前の回答がある場合だけ復元
    old_value = (
        st.session_state.answers.get(current)
    )

    default_index = None

    if old_value is not None:

        for i, choice in enumerate(
            CHOICES
        ):

            if (
                CHOICE_TO_SCORE[choice]
                == old_value
            ):

                default_index = i
                break

    radio_key = (
        f"answer_widget_{current}"
    )

    selected = st.radio(
        "あなたに最も近いものを選んでください",
        CHOICES,
        index=default_index,
        key=radio_key
    )

    st.write("")

    back_col, next_col = st.columns(2)

    with back_col:

        if current == 0:

            if st.button(
                "← 最初に戻る",
                use_container_width=True
            ):

                reset_app()

        else:

            if st.button(
                "← 前の質問",
                use_container_width=True
            ):

                # 現在選択済みなら保存
                if selected is not None:

                    st.session_state.answers[
                        current
                    ] = CHOICE_TO_SCORE[
                        selected
                    ]

                st.session_state.question_index -= 1

                st.rerun()

    with next_col:

        if current < total_questions - 1:

            if st.button(
                "次の質問 →",
                type="primary",
                use_container_width=True
            ):

                if selected is None:

                    st.warning(
                        "回答を1つ選んでください。"
                    )

                else:

                    st.session_state.answers[
                        current
                    ] = CHOICE_TO_SCORE[
                        selected
                    ]

                    st.session_state.question_index += 1

                    st.rerun()

        else:

            if st.button(
                "🏆 診断結果を見る",
                type="primary",
                use_container_width=True
            ):

                if selected is None:

                    st.warning(
                        "最後の質問に回答してください。"
                    )

                else:

                    st.session_state.answers[
                        current
                    ] = CHOICE_TO_SCORE[
                        selected
                    ]

                    if len(
                        st.session_state.answers
                    ) != total_questions:

                        # 念のため未回答を確認
                        missing = [
                            i
                            for i in range(
                                total_questions
                            )
                            if i
                            not in
                            st.session_state.answers
                        ]

                        if missing:

                            st.warning(
                                "未回答の質問があります。"
                            )

                            st.session_state.question_index = (
                                missing[0]
                            )

                            st.rerun()

                    scores = calculate_scores()

                    ranking = calculate_ranking(
                        scores
                    )

                    st.session_state.result_scores = (
                        scores
                    )

                    st.session_state.ranking = (
                        ranking
                    )

                    st.session_state.page = "result"

                    st.rerun()

    st.caption(
        "💡 迷った場合は「どちらともいえない」を選んでOKです。"
    )

# ============================================================
# RESULT PAGE
# ============================================================

elif st.session_state.page == "result":

    scores = st.session_state.result_scores

    ranking = st.session_state.ranking

    if not scores or not ranking:

        st.session_state.page = "start"
        st.rerun()

    best = ranking[0]

    best_person = best["person"]

    best_data = PEOPLE[
        best_person
    ]

    st.balloons()

    st.markdown(
        f"""
        <div class="result-hero">

            <div class="result-label">
                {st.session_state.name} さんに
                最も近い歴史上の人物
            </div>

            <div class="result-name">
                {best_data["emoji"]}
                {best_person}
            </div>

            <div class="result-title">
                {best_data["title"]}
            </div>

            <div class="similarity">
                類似度指数
                {best["similarity"]:.1f}%
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # タイプ
    # --------------------------------------------------------

    type_name = generate_type_name(
        scores
    )

    st.markdown(
        "### 🧬 あなたの性格タイプ"
    )

    st.success(
        type_name
    )

    st.write(
        generate_personality_summary(
            scores
        )
    )

    # --------------------------------------------------------
    # 人物との共通点
    # --------------------------------------------------------

    st.divider()

    st.markdown(
        f"## {best_data['emoji']} "
        f"{best_person}タイプの特徴"
    )

    st.write(
        best_data["summary"]
    )

    col1, col2 = st.columns(2)

    with col1:

        st.info(
            "💪 **強み**\n\n"
            + best_data["strength"]
        )

    with col2:

        st.warning(
            "⚠️ **意識するとよいこと**\n\n"
            + best_data["watch"]
        )

    st.success(
        "🌱 **力を発揮しやすい環境**\n\n"
        + best_data["environment"]
    )

    # --------------------------------------------------------
    # レーダーチャート
    # --------------------------------------------------------

    st.divider()

    st.markdown(
        "## 🕸️ 性格レーダー"
    )

    radar = make_radar_svg(
        scores
    )

    st.markdown(
        radar,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # 10軸
    # --------------------------------------------------------

    st.divider()

    st.markdown(
        "## 📊 10の性格スコア"
    )

    sorted_categories = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for category, score in sorted_categories:

        level = score_level(
            score
        )

        st.markdown(
            f"### {category}"
        )

        col_a, col_b = st.columns(
            [1, 3]
        )

        with col_a:

            st.markdown(
                f'<div class="big-score">'
                f'{score:.1f}'
                f'</div>',
                unsafe_allow_html=True
            )

            st.caption(
                f"/ 5.0　{level}"
            )

        with col_b:

            progress_value = (
                score - 1
            ) / 4

            progress_value = max(
                0.0,
                min(
                    1.0,
                    progress_value
                )
            )

            st.progress(
                progress_value
            )

            st.write(
                category_description(
                    category,
                    score
                )
            )

    # --------------------------------------------------------
    # 強みTOP3
    # --------------------------------------------------------

    st.divider()

    st.markdown(
        "## 🏆 あなたの強み TOP3"
    )

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for i, (
        category,
        score
    ) in enumerate(
        sorted_categories[:3]
    ):

        st.markdown(
            f"""
            <div class="person-card">

                <b style="font-size:20px;">
                    {medals[i]}
                    {i + 1}位
                    {category}
                </b>

                <br><br>

                スコア：
                <b>{score:.2f} / 5.00</b>

                <br><br>

                {category_description(
                    category,
                    score
                )}

            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # 相対的に低い3項目
    # --------------------------------------------------------

    st.divider()

    st.markdown(
        "## 🌱 相対的に低い3項目"
    )

    st.caption(
        "低い＝悪い、ではありません。"
        "あなたが自然に力を使う方向が別にあるという意味です。"
    )

    lower = sorted(
        scores.items(),
        key=lambda x: x[1]
    )[:3]

    for category, score in lower:

        st.write(
            f"**{category}："
            f"{score:.2f} / 5.00**"
        )

        st.write(
            category_description(
                category,
                score
            )
        )

    # --------------------------------------------------------
    # 偉人ランキング TOP5
    # --------------------------------------------------------

    st.divider()

    st.markdown(
        "## 🏛️ 歴史上の人物ランキング"
    )

    ranking_medals = [
        "🥇",
        "🥈",
        "🥉",
        "4️⃣",
        "5️⃣"
    ]

    for i, item in enumerate(
        ranking[:5]
    ):

        person = item[
            "person"
        ]

        data = PEOPLE[
            person
        ]

        similarity = item[
            "similarity"
        ]

        st.markdown(
            f"""
            <div class="person-card">

                <b style="font-size:21px;">
                    {ranking_medals[i]}
                    {person}
                </b>

                <span style="
                    opacity:0.65;
                    margin-left:8px;
                ">
                    {data["title"]}
                </span>

                <br><br>

                類似度指数：
                <b>{similarity:.1f}%</b>

            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # TOP2 / TOP3との違い
    # --------------------------------------------------------

    st.markdown(
        "### 🔍 2位・3位も見る"
    )

    for item in ranking[1:3]:

        person = item[
            "person"
        ]

        data = PEOPLE[
            person
        ]

        with st.expander(
            f"{data['emoji']} "
            f"{person} "
            f"— {item['similarity']:.1f}%"
        ):

            st.write(
                f"**{data['title']}**"
            )

            st.write(
                data["summary"]
            )

            st.write(
                f"**強み：** "
                f"{data['strength']}"
            )

    # --------------------------------------------------------
    # 回答統計
    # --------------------------------------------------------

    st.divider()

    st.markdown(
        "## 📈 診断データ"
    )

    raw_answers = list(
        st.session_state.answers.values()
    )

    raw_average = (
        sum(raw_answers)
        / len(raw_answers)
    )

    col1, col2, col3 = st.columns(
        3
    )

    with col1:

        st.metric(
            "回答数",
            "100 / 100"
        )

    with col2:

        st.metric(
            "平均回答",
            f"{raw_average:.2f}"
        )

    with col3:

        top_score = (
            sorted_categories[0][1]
        )

        st.metric(
            "最高特性",
            f"{top_score:.2f}"
        )

    # --------------------------------------------------------
    # レポートダウンロード
    # --------------------------------------------------------

    st.divider()

    st.markdown(
        "## 📄 診断結果を保存"
    )

    report_text = build_report(
        st.session_state.name,
        scores,
        ranking
    )

    safe_name = (
        st.session_state.name
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )

    st.download_button(
        label="📥 診断結果レポートを保存",
        data=report_text.encode(
            "utf-8"
        ),
        file_name=(
            f"{safe_name}_歴史上の人物性格診断.txt"
        ),
        mime="text/plain",
        use_container_width=True
    )

    # JSONも保存可能
    json_result = {
        "name": st.session_state.name,
        "type": type_name,
        "best_match": best_person,
        "similarity": best["similarity"],
        "scores": scores,
        "ranking": [
            {
                "rank": i + 1,
                "person": item["person"],
                "similarity": item["similarity"]
            }
            for i, item in enumerate(
                ranking
            )
        ]
    }

    st.download_button(
        label="💾 診断データ（JSON）を保存",
        data=json.dumps(
            json_result,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8"),
        file_name=(
            f"{safe_name}_personality_data.json"
        ),
        mime="application/json",
        use_container_width=True
    )

    # --------------------------------------------------------
    # 再診断
    # --------------------------------------------------------

    st.write("")

    if st.button(
        "🔄 最初からもう一度診断する",
        use_container_width=True
    ):

        reset_app()

    # --------------------------------------------------------
    # 注意事項
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="footer-note">

        この診断は自己理解・娯楽を目的としたものです。<br>
        医学的・心理学的な診断ではありません。<br><br>

        歴史上の人物について表示される性格数値は、
        実際に本人が心理検査を受けた結果ではなく、
        一般に知られている人物像を参考に
        このアプリ独自にモデル化したものです。

        </div>
        """,
        unsafe_allow_html=True
    )
