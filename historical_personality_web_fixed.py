import streamlit as st
import math
import json
from datetime import datetime

# ============================================================
# 歴史上の人物 性格診断
# 100問 × 100人物 完成版
# 外部API不要
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
    padding: 25px 10px;
}

.hero-title {
    font-size: 46px;
    font-weight: 900;
    line-height: 1.2;
}

.hero-sub {
    font-size: 17px;
    opacity: 0.75;
    line-height: 1.8;
    margin-top: 14px;
}

.question-card {
    padding: 28px;
    border-radius: 22px;
    border: 1px solid rgba(128,128,128,.25);
    margin: 18px 0 22px 0;
    box-shadow: 0 5px 20px rgba(0,0,0,.04);
}

.question-number {
    font-size: 13px;
    opacity: .6;
}

.question-text {
    font-size: 25px;
    font-weight: 800;
    margin-top: 10px;
    line-height: 1.5;
}

.result-card {
    text-align: center;
    padding: 35px 20px;
    border-radius: 25px;
    border: 1px solid rgba(128,128,128,.25);
    margin-bottom: 25px;
}

.person-name {
    font-size: 42px;
    font-weight: 900;
}

.person-title {
    font-size: 21px;
    font-weight: 700;
    margin-top: 8px;
}

.similarity {
    font-size: 27px;
    font-weight: 850;
    margin-top: 16px;
}

.ranking-card {
    padding: 18px;
    border: 1px solid rgba(128,128,128,.20);
    border-radius: 16px;
    margin-bottom: 10px;
}

.footer {
    text-align:center;
    opacity:.55;
    font-size:12px;
    line-height:1.8;
    margin-top:35px;
}

.stButton > button {
    border-radius: 12px;
    min-height: 48px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 性格10軸
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

# ============================================================
# 5段階回答
# ============================================================

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
# 質問100問
# 1 = 通常採点
# -1 = 逆転採点
# ============================================================

QUESTION_BANK = {

    "リーダーシップ": [
        ("集団では自分から方向性を示すことが多い", 1),
        ("責任のある役割を任されるとやる気が出る", 1),
        ("重要な場面では自分で決断したい", 1),
        ("周囲をまとめて目標へ向かわせることが得意だ", 1),
        ("意見が割れたときでも最終判断を下せる", 1),
        ("必要なら人前に立って指示を出せる", 1),
        ("問題が起きたとき誰かが動くまで待つことが多い", -1),
        ("大きな責任はなるべく他人に任せたい", -1),
        ("チームの成功に自分も責任を持ちたい", 1),
        ("反対されても必要な決断なら実行できる", 1),
    ],

    "挑戦心": [
        ("新しいことに挑戦するのが好きだ", 1),
        ("失敗する可能性があっても価値があれば挑戦したい", 1),
        ("難しい課題ほどやる気が出る", 1),
        ("未知の環境に飛び込むことを楽しめる", 1),
        ("安全だけを選ぶより成長できる道を選びたい", 1),
        ("他の人が試していない方法にも挑戦したい", 1),
        ("一度失敗すると再挑戦するのが怖くなる", -1),
        ("変化の大きい環境はできるだけ避けたい", -1),
        ("高い目標を設定することが多い", 1),
        ("自分の限界を試してみたいと思う", 1),
    ],

    "論理性": [
        ("結論を出す前に根拠を確認する", 1),
        ("問題が起きると原因を整理して考える", 1),
        ("数字やデータを使って考えることが好きだ", 1),
        ("複雑な問題を小さく分けて考える", 1),
        ("矛盾している説明が気になる", 1),
        ("自分の考えが間違っていないか検証する", 1),
        ("根拠がなくても直感だけで決めることが多い", -1),
        ("データよりその場の雰囲気だけで判断することが多い", -1),
        ("物事の仕組みや原因を理解したくなる", 1),
        ("感情と事実を分けて考えられる", 1),
    ],

    "共感性": [
        ("相手の立場になって考えることが多い", 1),
        ("困っている人を見ると助けたくなる", 1),
        ("人の感情の変化に気づきやすい", 1),
        ("相手が傷つかないよう言葉を選ぶ", 1),
        ("誰かの役に立つと嬉しい", 1),
        ("自分と違う価値観でも理解しようとする", 1),
        ("他人がどう感じるかはあまり気にならない", -1),
        ("目的達成のためなら人の気持ちは重要ではないと思う", -1),
        ("相談されたときはまず相手の話を聞く", 1),
        ("自分だけでなく周囲への影響も考える", 1),
    ],

    "社交性": [
        ("初対面の人とも比較的すぐ話せる", 1),
        ("多くの人と交流することが好きだ", 1),
        ("人と話すことで元気になることが多い", 1),
        ("新しい人間関係を作るのが好きだ", 1),
        ("会話では自分から話題を出すことが多い", 1),
        ("人が集まる場所を楽しめる", 1),
        ("知らない人とはできるだけ話したくない", -1),
        ("大勢の人と過ごすことを苦痛に感じることが多い", -1),
        ("人前で話すことに比較的抵抗がない", 1),
        ("人と人をつなげることが好きだ", 1),
    ],

    "創造性": [
        ("新しいアイデアを考えるのが好きだ", 1),
        ("普通とは違う方法を考えることが多い", 1),
        ("当たり前とされていることを疑うことがある", 1),
        ("自由に想像することを楽しめる", 1),
        ("既存の仕組みを見ると改善方法を考えたくなる", 1),
        ("異なる分野の知識を組み合わせるのが好きだ", 1),
        ("決められた方法以外はなるべく考えたくない", -1),
        ("新しい方法より昔からの方法だけを使いたい", -1),
        ("未来の可能性について考えることが多い", 1),
        ("一つの問題に複数の解決方法を考える", 1),
    ],

    "計画性": [
        ("行動する前に計画を立てることが多い", 1),
        ("期限には余裕を持って取り組みたい", 1),
        ("目標までの手順を考える", 1),
        ("優先順位をつけて物事を進める", 1),
        ("長期的な視点で予定を考える", 1),
        ("重要なことほど準備してから取り組む", 1),
        ("締め切り直前まで何もしないことが多い", -1),
        ("予定を立てず気分だけで行動することが多い", -1),
        ("大きな目標を小さな行動に分けられる", 1),
        ("計画が崩れたら新しい計画を作り直せる", 1),
    ],

    "独立性": [
        ("周囲と違う意見でも必要なら発言できる", 1),
        ("自分なりの価値観を大切にしている", 1),
        ("一人でも目標に向かって行動できる", 1),
        ("多数派の意見でも疑問があれば考え直す", 1),
        ("重要なことは自分で納得してから決めたい", 1),
        ("他人から評価されなくても必要な努力を続けられる", 1),
        ("周囲に反対されると自分の考えをすぐ変える", -1),
        ("自分で判断するより常に他人に決めてもらいたい", -1),
        ("一人で考える時間を大切にしている", 1),
        ("自分の選択には自分で責任を持ちたい", 1),
    ],

    "忍耐力": [
        ("長期間努力を続けることができる", 1),
        ("すぐ結果が出なくても努力できる", 1),
        ("失敗しても原因を考えて再挑戦する", 1),
        ("困難な状況でもある程度冷静さを保てる", 1),
        ("目標のためなら地道な作業を続けられる", 1),
        ("壁にぶつかっても簡単には諦めない", 1),
        ("成果がすぐ出ないと途中で投げ出すことが多い", -1),
        ("一度失敗すると続ける気がなくなる", -1),
        ("プレッシャーがあっても必要な行動を続けられる", 1),
        ("小さな努力を積み重ねることができる", 1),
    ],

    "好奇心": [
        ("知らないことを調べるのが好きだ", 1),
        ("興味を持ったことは深く調べたくなる", 1),
        ("幅広い分野について学びたい", 1),
        ("新しい技術や考え方に興味がある", 1),
        ("なぜそうなるのか考えることが多い", 1),
        ("知らない世界について知るとワクワクする", 1),
        ("新しい知識を学ぶのは面倒だと感じることが多い", -1),
        ("自分の専門外のことにはほとんど興味がない", -1),
        ("本・動画・記事などから新しい知識を得るのが好きだ", 1),
        ("一つの疑問から別の疑問が生まれることが多い", 1),
    ],
}

QUESTIONS = []

for category in CATEGORIES:
    for text, direction in QUESTION_BANK[category]:
        QUESTIONS.append((text, category, direction))

# ============================================================
# 人物タイプの基本モデル
# ============================================================

ARCHETYPES = {

    "改革者": {
        "scores": [4.5, 4.8, 4.0, 3.0, 3.7, 4.8, 3.7, 4.7, 4.2, 4.5],
        "strength": "変革力・決断力・新しい価値を生み出す力",
        "watch": "変化を急ぐあまり、周囲との歩調を置き去りにしないこと。",
        "environment": "新規事業、起業、変革期の組織、企画"
    },

    "戦略家": {
        "scores": [4.4, 3.6, 4.9, 3.2, 3.0, 4.0, 4.9, 4.4, 4.7, 4.4],
        "strength": "分析力・計画性・先を読む力",
        "watch": "考え抜くことが強みですが、行動開始が遅くならないこと。",
        "environment": "戦略、経営、IT、コンサル、プロジェクト管理"
    },

    "指導者": {
        "scores": [4.9, 4.3, 4.1, 4.0, 4.2, 3.5, 4.2, 4.5, 4.8, 3.8],
        "strength": "リーダーシップ・責任感・組織を動かす力",
        "watch": "責任を抱え込みすぎず、周囲に任せることも大切。",
        "environment": "経営、マネジメント、組織運営、公共分野"
    },

    "共感リーダー": {
        "scores": [4.6, 4.0, 3.9, 5.0, 4.3, 3.4, 4.0, 4.2, 4.9, 3.8],
        "strength": "共感力・人望・忍耐力・調整力",
        "watch": "他者を優先しすぎて自分を消耗させないこと。",
        "environment": "教育、医療、公共分野、チームマネジメント"
    },

    "探究者": {
        "scores": [2.8, 4.0, 5.0, 3.3, 2.5, 4.6, 3.5, 4.8, 4.7, 5.0],
        "strength": "論理性・探究心・独立した思考",
        "watch": "思考だけで完結せず、成果を外に出すこと。",
        "environment": "研究、専門職、技術、分析"
    },

    "発明家": {
        "scores": [3.4, 4.8, 4.6, 2.8, 3.0, 5.0, 3.8, 4.7, 4.8, 5.0],
        "strength": "創造性・実験精神・好奇心",
        "watch": "アイデアを増やしすぎず、完成まで持っていくこと。",
        "environment": "研究開発、プロダクト開発、技術、起業"
    },

    "芸術家": {
        "scores": [2.8, 4.0, 3.3, 4.0, 3.0, 5.0, 2.7, 4.8, 4.2, 4.8],
        "strength": "創造性・独自性・表現力",
        "watch": "理想を追求する一方で、完成や締め切りも意識すること。",
        "environment": "芸術、デザイン、文章、映像、クリエイティブ"
    },

    "起業家": {
        "scores": [4.6, 5.0, 4.1, 3.2, 4.5, 4.7, 4.0, 4.8, 4.7, 4.7],
        "strength": "行動力・挑戦心・ビジョン・実行力",
        "watch": "スピードだけでなくリスク管理や周囲への配慮も忘れないこと。",
        "environment": "起業、新規事業、営業、プロダクト開発"
    },

    "思想家": {
        "scores": [2.8, 3.6, 4.8, 4.0, 2.9, 4.4, 3.4, 4.9, 4.2, 5.0],
        "strength": "思考力・独立性・本質を問い続ける力",
        "watch": "抽象的な思考だけでなく現実への応用も意識すること。",
        "environment": "研究、教育、文章、企画、思想"
    },

    "実務家": {
        "scores": [4.2, 3.8, 4.4, 3.8, 3.8, 3.3, 4.8, 4.1, 4.8, 3.8],
        "strength": "実行力・計画性・安定した成果",
        "watch": "確実性だけでなく新しい方法にも目を向けること。",
        "environment": "経営、管理、行政、運営、長期プロジェクト"
    },

    "冒険家": {
        "scores": [3.8, 5.0, 3.8, 3.5, 4.2, 4.4, 2.9, 4.8, 4.5, 5.0],
        "strength": "挑戦心・好奇心・適応力",
        "watch": "勢いだけではなく準備と継続性も意識すること。",
        "environment": "海外、新規事業、探検、変化の大きい環境"
    },

    "外交家": {
        "scores": [4.3, 4.0, 4.1, 4.6, 4.9, 3.8, 4.0, 4.0, 4.4, 4.0],
        "strength": "社交性・交渉力・人をつなぐ力",
        "watch": "周囲との調和だけでなく自分自身の判断も大切にすること。",
        "environment": "営業、交渉、外交、マネジメント"
    },

    "職人": {
        "scores": [2.8, 4.1, 4.5, 3.0, 2.3, 4.3, 4.2, 4.9, 5.0, 4.1],
        "strength": "集中力・独立性・自己鍛錬",
        "watch": "一人で完結せず、必要な場面では他者の力も借りること。",
        "environment": "専門職、技術、研究、職人的な仕事"
    },

    "万能型": {
        "scores": [4.0, 4.4, 4.5, 4.0, 4.0, 4.5, 4.1, 4.4, 4.5, 4.8],
        "strength": "幅広い能力・柔軟性・学習力",
        "watch": "興味が広がりすぎないよう優先順位を決めること。",
        "environment": "企画、経営、研究、コンサル、複合領域"
    },
}

# ============================================================
# 100人
#
# 形式:
# 名前: (絵文字, タイトル, タイプ, 微調整軸1, 微調整軸2)
#
# 同じタイプでも微調整することで
# 100人が完全に同じプロフィールにならないようにする
# ============================================================

PEOPLE_RAW = {

    # ==================== 日本 20 ====================

    "織田信長":
        ("⚔️", "常識を壊す革命児", "改革者", "独立性", "創造性"),

    "徳川家康":
        ("🏯", "最後に勝つ長期戦略家", "戦略家", "忍耐力", "計画性"),

    "豊臣秀吉":
        ("☀️", "人を巻き込む行動派", "外交家", "社交性", "挑戦心"),

    "坂本龍馬":
        ("🌊", "人と未来をつなぐ改革者", "冒険家", "社交性", "創造性"),

    "西郷隆盛":
        ("🌋", "信頼で人を導く人格派", "共感リーダー", "共感性", "リーダーシップ"),

    "宮本武蔵":
        ("🗡️", "孤高の自己鍛錬型", "職人", "独立性", "忍耐力"),

    "福沢諭吉":
        ("📚", "学びを武器にする独立思考家", "思想家", "好奇心", "独立性"),

    "渋沢栄一":
        ("💴", "理念と経済を結ぶ実業家", "万能型", "共感性", "計画性"),

    "伊能忠敬":
        ("🗺️", "積み重ねで未知を測る探究者", "探究者", "忍耐力", "計画性"),

    "紫式部":
        ("📖", "人間を見つめる物語作家", "芸術家", "共感性", "好奇心"),

    "聖徳太子":
        ("📜", "調和を重視する制度設計者", "実務家", "共感性", "リーダーシップ"),

    "勝海舟":
        ("🚢", "争いを避け未来を読む交渉人", "外交家", "論理性", "共感性"),

    "吉田松陰":
        ("🔥", "人を育てる情熱的思想家", "思想家", "挑戦心", "リーダーシップ"),

    "本田宗一郎":
        ("🏍️", "失敗を恐れない技術挑戦者", "起業家", "挑戦心", "創造性"),

    "盛田昭夫":
        ("📻", "世界へ挑んだ製品革新者", "起業家", "社交性", "創造性"),

    "松下幸之助":
        ("💡", "人を育てる経営思想家", "実務家", "共感性", "リーダーシップ"),

    "黒澤明":
        ("🎬", "妥協しない映像表現者", "芸術家", "リーダーシップ", "忍耐力"),

    "手塚治虫":
        ("✒️", "想像力で世界を描く創作者", "芸術家", "好奇心", "創造性"),

    "北里柴三郎":
        ("🧫", "社会を守る科学実践者", "探究者", "計画性", "リーダーシップ"),

    "野口英世":
        ("🔬", "研究に人生を注ぐ探究者", "探究者", "挑戦心", "忍耐力"),

    # ==================== 中国・アジア 10 ====================

    "諸葛亮":
        ("🪶", "先を読む知略家", "戦略家", "論理性", "計画性"),

    "劉備":
        ("🤝", "人望で仲間を集める指導者", "共感リーダー", "社交性", "共感性"),

    "曹操":
        ("🐉", "合理性で勝機をつかむ覇者", "戦略家", "リーダーシップ", "挑戦心"),

    "孫子":
        ("📕", "戦わずして勝つ戦略思想家", "戦略家", "論理性", "独立性"),

    "孔子":
        ("🎓", "人と社会を考える教育思想家", "思想家", "共感性", "計画性"),

    "老子":
        ("☯️", "自然体を追求する哲学者", "思想家", "独立性", "創造性"),

    "始皇帝":
        ("👑", "巨大な制度を築く統一者", "指導者", "計画性", "リーダーシップ"),

    "玄奘":
        ("🐫", "知を求めて旅する求道者", "冒険家", "忍耐力", "好奇心"),

    "鄭和":
        ("⛵", "世界へ船を進めた大航海者", "冒険家", "リーダーシップ", "社交性"),

    "李白":
        ("🌙", "自由奔放な天才詩人", "芸術家", "独立性", "創造性"),

    # ==================== 科学・発明 20 ====================

    "レオナルド・ダ・ヴィンチ":
        ("🎨", "境界を越える万能天才", "万能型", "創造性", "好奇心"),

    "アルベルト・アインシュタイン":
        ("🧠", "常識を疑う思考実験家", "探究者", "創造性", "独立性"),

    "マリー・キュリー":
        ("⚗️", "静かな情熱を持つ研究者", "探究者", "忍耐力", "論理性"),

    "トーマス・エジソン":
        ("💡", "試して直す実験型発明家", "発明家", "忍耐力", "挑戦心"),

    "ニコラ・テスラ":
        ("⚡", "未来を先取りした孤高の発明家", "発明家", "創造性", "独立性"),

    "チャールズ・ダーウィン":
        ("🐢", "観察を積み重ねる研究者", "探究者", "忍耐力", "好奇心"),

    "アイザック・ニュートン":
        ("🍎", "法則を追い求める孤高の科学者", "探究者", "論理性", "独立性"),

    "ガリレオ・ガリレイ":
        ("🔭", "観察で常識に挑んだ科学者", "探究者", "挑戦心", "独立性"),

    "アラン・チューリング":
        ("💻", "計算の未来を切り開いた天才", "探究者", "論理性", "創造性"),

    "エイダ・ラブレス":
        ("🧮", "コンピュータの可能性を想像した先駆者", "発明家", "創造性", "好奇心"),

    "ジョン・フォン・ノイマン":
        ("♟️", "超高速で考える万能数学者", "万能型", "論理性", "好奇心"),

    "リチャード・ファインマン":
        ("🥁", "遊ぶように科学を探究する物理学者", "万能型", "好奇心", "創造性"),

    "ルイ・パスツール":
        ("🧪", "科学を社会に役立てる研究者", "探究者", "計画性", "忍耐力"),

    "グレゴール・メンデル":
        ("🌱", "地道な観察から法則を見つけた研究者", "探究者", "忍耐力", "計画性"),

    "ジェームズ・ワット":
        ("⚙️", "技術を実用化へ変えた改良者", "発明家", "計画性", "創造性"),

    "ライト兄弟":
        ("✈️", "空への夢を実験で実現した挑戦者", "発明家", "挑戦心", "忍耐力"),

    "アレクサンダー・グラハム・ベル":
        ("☎️", "人をつなぐ技術を生み出した発明家", "発明家", "共感性", "創造性"),

    "ロバート・フック":
        ("🔬", "あらゆる現象を観察する博学者", "万能型", "好奇心", "論理性"),

    "ヨハネス・ケプラー":
        ("🌌", "宇宙の規則を数字で探した科学者", "探究者", "論理性", "忍耐力"),

    "コペルニクス":
        ("🌍", "世界観そのものを変えた天文学者", "探究者", "独立性", "挑戦心"),

    # ==================== 思想家 10 ====================

    "ソクラテス":
        ("❓", "問い続ける哲学者", "思想家", "論理性", "独立性"),

    "プラトン":
        ("🏛️", "理想社会を考えた哲学者", "思想家", "創造性", "論理性"),

    "アリストテレス":
        ("📚", "世界を体系化する万能思想家", "万能型", "論理性", "好奇心"),

    "ルネ・デカルト":
        ("🧠", "疑うことから始める合理主義者", "思想家", "論理性", "独立性"),

    "イマヌエル・カント":
        ("⏰", "規律と理性を追究した哲学者", "思想家", "計画性", "論理性"),

    "フリードリヒ・ニーチェ":
        ("🦅", "既存の価値を問い直す思想家", "思想家", "独立性", "創造性"),

    "ジャン＝ジャック・ルソー":
        ("🌿", "人間と社会のあり方を問う思想家", "思想家", "共感性", "独立性"),

    "ジョン・ロック":
        ("📜", "自由と権利を考えた思想家", "思想家", "論理性", "共感性"),

    "アダム・スミス":
        ("💰", "社会と経済の仕組みを考えた思想家", "思想家", "論理性", "好奇心"),

    "マックス・ウェーバー":
        ("🏢", "社会の構造を読み解く分析家", "探究者", "論理性", "計画性"),

    # ==================== 政治・指導者 20 ====================

    "ナポレオン":
        ("👑", "圧倒的な実行型指導者", "指導者", "挑戦心", "リーダーシップ"),

    "アレクサンドロス大王":
        ("🐎", "世界の果てを目指した征服者", "指導者", "挑戦心", "リーダーシップ"),

    "ユリウス・カエサル":
        ("🦅", "決断と戦略の政治指導者", "指導者", "論理性", "リーダーシップ"),

    "アウグストゥス":
        ("🏛️", "安定した制度を築いた統治者", "実務家", "計画性", "リーダーシップ"),

    "マルクス・アウレリウス":
        ("📖", "自制を重んじる哲人皇帝", "思想家", "忍耐力", "リーダーシップ"),

    "ジャンヌ・ダルク":
        ("⚜️", "信念で進む若き指導者", "指導者", "挑戦心", "忍耐力"),

    "エリザベス1世":
        ("👸", "国家をまとめる現実的指導者", "指導者", "計画性", "社交性"),

    "ヴィクトリア女王":
        ("👑", "長期統治を支えた責任型指導者", "実務家", "忍耐力", "リーダーシップ"),

    "ウィンストン・チャーチル":
        ("🎩", "危機で力を発揮する指導者", "指導者", "忍耐力", "挑戦心"),

    "シャルル・ド・ゴール":
        ("🇫🇷", "独立心の強い国家指導者", "指導者", "独立性", "リーダーシップ"),

    "ピョートル大帝":
        ("⚓", "国を大胆に改革した皇帝", "改革者", "挑戦心", "リーダーシップ"),

    "ジョージ・ワシントン":
        ("🇺🇸", "信頼で国をまとめた建国指導者", "指導者", "共感性", "計画性"),

    "セオドア・ルーズベルト":
        ("🐻", "行動力あふれる改革型大統領", "改革者", "挑戦心", "リーダーシップ"),

    "フランクリン・ルーズベルト":
        ("♿", "危機を乗り越える調整型指導者", "共感リーダー", "計画性", "リーダーシップ"),

    "ジョン・F・ケネディ":
        ("🚀", "未来へのビジョンを語る指導者", "外交家", "リーダーシップ", "社交性"),

    "エイブラハム・リンカーン":
        ("🎩", "逆境に耐える統合型指導者", "共感リーダー", "忍耐力", "論理性"),

    "マハトマ・ガンジー":
        ("🕊️", "信念で人を動かす非暴力指導者", "共感リーダー", "忍耐力", "独立性"),

    "ネルソン・マンデラ":
        ("🤝", "対立を越える和解型指導者", "共感リーダー", "共感性", "リーダーシップ"),

    "マーティン・ルーサー・キング・ジュニア":
        ("🎤", "言葉と信念で社会を動かす指導者", "共感リーダー", "社交性", "共感性"),

    "マララ・ユスフザイ":
        ("📚", "教育のために声を上げる活動家", "共感リーダー", "挑戦心", "独立性"),

    # ==================== 社会・人道 10 ====================

    "フローレンス・ナイチンゲール":
        ("🕯️", "データで医療を変えた改革者", "改革者", "共感性", "論理性"),

    "マザー・テレサ":
        ("❤️", "人への奉仕を貫いた活動家", "共感リーダー", "共感性", "忍耐力"),

    "ヘレン・ケラー":
        ("🌟", "逆境を越え学び続けた活動家", "共感リーダー", "忍耐力", "好奇心"),

    "アンネ・フランク":
        ("📔", "人間を見つめ続けた少女作家", "芸術家", "共感性", "忍耐力"),

    "ワンガリ・マータイ":
        ("🌳", "環境と人権を結んだ活動家", "共感リーダー", "挑戦心", "共感性"),

    "クララ・バートン":
        ("⛑️", "人命救助に尽くした行動家", "共感リーダー", "計画性", "共感性"),

    "ジェーン・アダムズ":
        ("🏠", "社会改革に取り組んだ実践家", "共感リーダー", "社交性", "計画性"),

    "アルベルト・シュバイツァー":
        ("🩺", "知識を人への奉仕に使った思想家", "万能型", "共感性", "好奇心"),

    "レイチェル・カーソン":
        ("🌊", "科学で環境問題を伝えた作家", "探究者", "共感性", "独立性"),

    "ハリエット・タブマン":
        ("⭐", "危険を恐れず人を救った活動家", "共感リーダー", "挑戦心", "忍耐力"),

    # ==================== 経営・起業 10 ====================

    "スティーブ・ジョブズ":
        ("💻", "未来を形にする革新者", "起業家", "創造性", "独立性"),

    "ウォルト・ディズニー":
        ("🏰", "夢を事業に変える創造者", "起業家", "創造性", "忍耐力"),

    "ヘンリー・フォード":
        ("🚗", "仕組みで産業を変えた実業家", "実務家", "創造性", "計画性"),

    "アンドリュー・カーネギー":
        ("🏭", "成長を追求した産業経営者", "起業家", "計画性", "挑戦心"),

    "ジョン・D・ロックフェラー":
        ("🛢️", "徹底した管理で巨大事業を築いた経営者", "実務家", "計画性", "論理性"),

    "ビル・ゲイツ":
        ("🪟", "技術と戦略を結ぶ経営者", "戦略家", "好奇心", "挑戦心"),

    "ジェフ・ベゾス":
        ("📦", "長期視点で市場を作る起業家", "起業家", "計画性", "挑戦心"),

    "イーロン・マスク":
        ("🚀", "巨大な未来像へ挑む起業家", "起業家", "挑戦心", "創造性"),

    "オプラ・ウィンフリー":
        ("🎙️", "共感で人をつなぐメディア経営者", "外交家", "共感性", "社交性"),

    "リチャード・ブランソン":
        ("🎈", "冒険する連続起業家", "起業家", "社交性", "挑戦心"),

    # ==================== 芸術・文学 10 ====================

    "ミケランジェロ":
        ("🗿", "極限まで作品を磨く芸術家", "芸術家", "忍耐力", "独立性"),

    "パブロ・ピカソ":
        ("🎨", "表現の常識を壊した革新者", "芸術家", "創造性", "挑戦心"),

    "フィンセント・ファン・ゴッホ":
        ("🌻", "感情を作品へ注ぎ込む画家", "芸術家", "独立性", "忍耐力"),

    "モーツァルト":
        ("🎼", "自由な発想を音に変えた天才", "芸術家", "創造性", "好奇心"),

    "ベートーヴェン":
        ("🎹", "逆境の中で作品を生み続けた作曲家", "芸術家", "忍耐力", "独立性"),

    "ウィリアム・シェイクスピア":
        ("🎭", "人間を描き尽くした劇作家", "芸術家", "共感性", "創造性"),

    "レフ・トルストイ":
        ("📚", "人生と社会を問い続けた作家", "思想家", "共感性", "独立性"),

    "フョードル・ドストエフスキー":
        ("📕", "人間心理の深部を描く作家", "芸術家", "共感性", "好奇心"),

    "マーク・トウェイン":
        ("✒️", "社会をユーモアで観察する作家", "芸術家", "社交性", "独立性"),

    "アガサ・クリスティ":
        ("🔎", "論理と物語を組み合わせる作家", "芸術家", "論理性", "計画性"),
}

# ============================================================
# 100人チェック
# ============================================================

# ============================================================
# 人物数を100人に固定
# ============================================================

PEOPLE_RAW = dict(
    list(PEOPLE_RAW.items())[:100]
)

assert len(PEOPLE_RAW) == 100

# ============================================================
# 人物プロフィールを生成
# ============================================================

def clamp(value):
    return max(1.0, min(5.0, value))


PEOPLE = {}

for index, (name, data) in enumerate(PEOPLE_RAW.items()):

    emoji, title, archetype_name, boost1, boost2 = data

    archetype = ARCHETYPES[archetype_name]

    scores = archetype["scores"].copy()

    # 人物ごとの差をつける微調整
    scores[CATEGORIES.index(boost1)] += 0.25
    scores[CATEGORIES.index(boost2)] += 0.15

    # 同タイプ完全同点を避ける小さな補正
    tiny = ((index % 5) - 2) * 0.025

    scores = [
        round(clamp(v + tiny), 2)
        for v in scores
    ]

    PEOPLE[name] = {
        "emoji": emoji,
        "title": title,
        "archetype": archetype_name,
        "scores": scores,
        "strength": archetype["strength"],
        "watch": archetype["watch"],
        "environment": archetype["environment"],
    }

# ============================================================
# セッション
# ============================================================

DEFAULTS = {
    "page": "start",
    "name": "",
    "question_index": 0,
    "answers": {},
    "scores": None,
    "ranking": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_app():

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.rerun()


# ============================================================
# 計算
# ============================================================

def calculate_scores():

    totals = {
        category: 0
        for category in CATEGORIES
    }

    counts = {
        category: 0
        for category in CATEGORIES
    }

    for i, raw_score in st.session_state.answers.items():

        _, category, direction = QUESTIONS[i]

        if direction == -1:
            score = 6 - raw_score
        else:
            score = raw_score

        totals[category] += score
        counts[category] += 1

    return {
        category: round(
            totals[category] / counts[category],
            2
        )
        for category in CATEGORIES
    }


def calculate_ranking(scores):

    ranking = []

    max_distance = math.sqrt(
        len(CATEGORIES) * 16
    )

    for person, data in PEOPLE.items():

        distance_sq = 0

        for i, category in enumerate(CATEGORIES):

            difference = (
                scores[category]
                - data["scores"][i]
            )

            distance_sq += difference ** 2

        distance = math.sqrt(
            distance_sq
        )

        similarity = (
            1 - distance / max_distance
        ) * 100

        similarity = max(
            0,
            min(99.5, similarity)
        )

        ranking.append({
            "person": person,
            "distance": distance,
            "similarity": round(
                similarity,
                1
            )
        })

    ranking.sort(
        key=lambda item: item["distance"]
    )

    return ranking


def score_level(score):

    if score >= 4.3:
        return "非常に高い"

    if score >= 3.7:
        return "高い"

    if score >= 3.0:
        return "中程度"

    if score >= 2.3:
        return "やや低い"

    return "低い"


def personality_summary(scores):

    ordered = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    top = ordered[:3]
    low = ordered[-2:]

    return (
        f"あなたは特に **{top[0][0]}・{top[1][0]}・"
        f"{top[2][0]}** が強いタイプです。"
        f"中でも **{top[0][0]}** が最も高く、"
        f"あなたの行動や判断に強く表れています。"
        f"一方で **{low[0][0]}・{low[1][0]}** は"
        f"相対的に低めです。これは悪いという意味ではなく、"
        f"あなたが自然に力を使う方向が別にあることを示しています。"
    )


# ============================================================
# SVGレーダーチャート
# ============================================================

def radar_svg(scores):

    width = 620
    height = 620

    cx = 310
    cy = 310
    radius = 205

    n = len(CATEGORIES)

    angles = [
        -math.pi / 2
        + 2 * math.pi * i / n
        for i in range(n)
    ]

    def point(angle, r):
        return (
            cx + math.cos(angle) * r,
            cy + math.sin(angle) * r
        )

    grid = ""

    for level in range(1, 6):

        r = radius * level / 5

        pts = []

        for angle in angles:
            x, y = point(angle, r)
            pts.append(
                f"{x:.1f},{y:.1f}"
            )

        grid += (
            f'<polygon points="{" ".join(pts)}" '
            f'fill="none" stroke="rgba(128,128,128,.25)" />'
        )

    axes = ""

    for angle in angles:

        x, y = point(
            angle,
            radius
        )

        axes += (
            f'<line x1="{cx}" y1="{cy}" '
            f'x2="{x}" y2="{y}" '
            f'stroke="rgba(128,128,128,.20)" />'
        )

    user_points = []

    for category, angle in zip(
        CATEGORIES,
        angles
    ):

        r = (
            radius
            * scores[category]
            / 5
        )

        x, y = point(angle, r)

        user_points.append(
            f"{x:.1f},{y:.1f}"
        )

    polygon = (
        f'<polygon points="{" ".join(user_points)}" '
        f'fill="rgba(80,120,255,.25)" '
        f'stroke="rgba(80,120,255,.95)" '
        f'stroke-width="3"/>'
    )

    labels = ""

    for category, angle in zip(
        CATEGORIES,
        angles
    ):

        x, y = point(
            angle,
            radius + 60
        )

        anchor = "middle"

        c = math.cos(angle)

        if c > .3:
            anchor = "start"

        elif c < -.3:
            anchor = "end"

        labels += f"""
        <text
        x="{x:.1f}"
        y="{y:.1f}"
        text-anchor="{anchor}"
        font-size="14"
        font-weight="700"
        fill="currentColor">
        {category}
        </text>
        """

    return f"""
    <div style="overflow-x:auto">
    <svg
    viewBox="0 0 {width} {height}"
    style="width:100%;max-width:620px">

    {grid}
    {axes}
    {polygon}
    {labels}

    </svg>
    </div>
    """


# ============================================================
# レポート
# ============================================================

def create_report():

    scores = st.session_state.scores
    ranking = st.session_state.ranking

    best = ranking[0]
    person = best["person"]

    data = PEOPLE[person]

    lines = [
        "歴史上の人物 性格診断",
        "=" * 40,
        "",
        f"名前：{st.session_state.name}",
        f"診断日時：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"最も近い人物：{person}",
        f"人物タイプ：{data['title']}",
        f"類似度指数：{best['similarity']}%",
        "",
        "【性格総評】",
        personality_summary(scores).replace("**", ""),
        "",
        "【強み】",
        data["strength"],
        "",
        "【意識するとよいこと】",
        data["watch"],
        "",
        "【力を発揮しやすい環境】",
        data["environment"],
        "",
        "【性格10軸】",
    ]

    for category, score in sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    ):

        lines.append(
            f"{category}: "
            f"{score:.2f}/5.00 "
            f"({score_level(score)})"
        )

    lines += [
        "",
        "【歴史上の人物 TOP10】"
    ]

    for rank, result in enumerate(
        ranking[:10],
        start=1
    ):

        lines.append(
            f"{rank}位 "
            f"{result['person']} "
            f"{result['similarity']}%"
        )

    lines += [
        "",
        "※本診断は自己理解・娯楽用です。",
        "人物の性格数値は診断アプリ独自のモデルです。"
    ]

    return "\n".join(lines)


# ============================================================
# START
# ============================================================

if st.session_state.page == "start":

    st.markdown("""
    <div class="hero">

        <div class="hero-title">
            🏛️ 歴史上の人物<br>
            性格診断
        </div>

        <div class="hero-sub">
            100の質問 × 100人の歴史的人物<br>
            あなたの性格を10の軸から分析します。
        </div>

    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "質問",
            "100問"
        )

    with col2:
        st.metric(
            "性格軸",
            "10種類"
        )

    with col3:
        st.metric(
            "人物候補",
            f"{len(PEOPLE)}人"
        )

    st.write("")

    with st.expander(
        "📖 診断について"
    ):

        st.write("""
        回答から以下の10項目を分析します。

        - リーダーシップ
        - 挑戦心
        - 論理性
        - 共感性
        - 社交性
        - 創造性
        - 計画性
        - 独立性
        - 忍耐力
        - 好奇心

        100人の人物モデルと比較し、
        あなたに近い人物をランキングします。

        回答に正解・不正解はありません。
        普段の自分に近い答えを選んでください。
        """)

    name = st.text_input(
        "名前・ニックネーム",
        placeholder="例：まさと",
        max_chars=30
    )

    if st.button(
        "診断をはじめる →",
        type="primary",
        use_container_width=True
    ):

        name = name.strip()

        if not name:

            st.warning(
                "名前またはニックネームを入力してください。"
            )

        else:

            st.session_state.name = name
            st.session_state.page = "quiz"
            st.session_state.answers = {}
            st.session_state.question_index = 0

            st.rerun()


# ============================================================
# QUIZ
# ============================================================

elif st.session_state.page == "quiz":

    current = (
        st.session_state.question_index
    )

    total = len(
        QUESTIONS
    )

    question, category, direction = (
        QUESTIONS[current]
    )

    answered = len(
        st.session_state.answers
    )

    st.write(
        f"### {st.session_state.name} さん"
    )

    st.progress(
        answered / total
    )

    st.caption(
        f"回答済み {answered}/100　｜　質問 {current + 1}/100"
    )

    st.markdown(
        f"""
        <div class="question-card">

        <div class="question-number">
        QUESTION {current + 1} / 100
        </div>

        <div class="question-text">
        {question}
        </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    previous = (
        st.session_state.answers.get(
            current
        )
    )

    default_index = None

    if previous is not None:

        for i, choice in enumerate(
            CHOICES
        ):

            if (
                CHOICE_TO_SCORE[choice]
                == previous
            ):

                default_index = i
                break

    answer = st.radio(
        "あなたに最も近いもの",
        CHOICES,
        index=default_index,
        key=f"q_{current}"
    )

    back_col, next_col = st.columns(2)

    with back_col:

        if current > 0:

            if st.button(
                "← 前へ",
                use_container_width=True
            ):

                if answer is not None:

                    st.session_state.answers[
                        current
                    ] = CHOICE_TO_SCORE[
                        answer
                    ]

                st.session_state.question_index -= 1

                st.rerun()

        else:

            if st.button(
                "← 最初に戻る",
                use_container_width=True
            ):

                reset_app()

    with next_col:

        if current < 99:

            if st.button(
                "次へ →",
                type="primary",
                use_container_width=True
            ):

                if answer is None:

                    st.warning(
                        "回答を選択してください。"
                    )

                else:

                    st.session_state.answers[
                        current
                    ] = CHOICE_TO_SCORE[
                        answer
                    ]

                    st.session_state.question_index += 1

                    st.rerun()

        else:

            if st.button(
                "🏆 診断する",
                type="primary",
                use_container_width=True
            ):

                if answer is None:

                    st.warning(
                        "回答を選択してください。"
                    )

                else:

                    st.session_state.answers[
                        current
                    ] = CHOICE_TO_SCORE[
                        answer
                    ]

                    missing = [
                        i
                        for i in range(100)
                        if i
                        not in st.session_state.answers
                    ]

                    if missing:

                        st.session_state.question_index = (
                            missing[0]
                        )

                        st.warning(
                            "未回答の質問があります。"
                        )

                        st.rerun()

                    st.session_state.scores = (
                        calculate_scores()
                    )

                    st.session_state.ranking = (
                        calculate_ranking(
                            st.session_state.scores
                        )
                    )

                    st.session_state.page = (
                        "result"
                    )

                    st.rerun()

    st.caption(
        "迷った場合は「どちらともいえない」でOKです。"
    )


# ============================================================
# RESULT
# ============================================================

elif st.session_state.page == "result":

    scores = st.session_state.scores
    ranking = st.session_state.ranking

    best = ranking[0]

    best_name = best[
        "person"
    ]

    person = PEOPLE[
        best_name
    ]

    st.balloons()

    st.markdown(
        f"""
        <div class="result-card">

        <div style="opacity:.65">
        {st.session_state.name} さんに
        最も近い歴史上の人物
        </div>

        <div class="person-name">
        {person["emoji"]} {best_name}
        </div>

        <div class="person-title">
        {person["title"]}
        </div>

        <div class="similarity">
        類似度指数 {best["similarity"]:.1f}%
        </div>

        <div style="margin-top:8px;opacity:.65">
        {person["archetype"]}タイプ
        </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    st.header(
        "🧠 あなたの性格"
    )

    st.write(
        personality_summary(
            scores
        )
    )

    st.success(
        "💪 **あなたに近い人物タイプの強み**\n\n"
        + person["strength"]
    )

    st.warning(
        "⚠️ **意識するとよいこと**\n\n"
        + person["watch"]
    )

    st.info(
        "🌱 **力を発揮しやすい環境**\n\n"
        + person["environment"]
    )

    # --------------------------------------------------------
    # レーダー
    # --------------------------------------------------------

    st.divider()

    st.header(
        "🕸️ 性格レーダー"
    )

    st.markdown(
        radar_svg(scores),
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # 性格10項目
    # --------------------------------------------------------

    st.divider()

    st.header(
        "📊 性格10軸"
    )

    sorted_scores = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for category, score in sorted_scores:

        st.write(
            f"### {category}"
        )

        col1, col2 = st.columns(
            [1, 3]
        )

        with col1:

            st.metric(
                "スコア",
                f"{score:.2f}"
            )

        with col2:

            normalized = (
                score - 1
            ) / 4

            st.progress(
                max(
                    0.0,
                    min(
                        1.0,
                        normalized
                    )
                )
            )

            st.caption(
                score_level(
                    score
                )
            )

    # --------------------------------------------------------
    # 強みTOP3
    # --------------------------------------------------------

    st.divider()

    st.header(
        "🔥 あなたの強み TOP3"
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
        sorted_scores[:3]
    ):

        st.write(
            f"### {medals[i]} "
            f"{category}　"
            f"{score:.2f}/5.00"
        )

    # --------------------------------------------------------
    # 偉人ランキングTOP10
    # --------------------------------------------------------

    st.divider()

    st.header(
        "🏛️ あなたに近い人物 TOP10"
    )

    for i, result in enumerate(
        ranking[:10],
        start=1
    ):

        name = result[
            "person"
        ]

        data = PEOPLE[
            name
        ]

        medal = ""

        if i == 1:
            medal = "🥇"

        elif i == 2:
            medal = "🥈"

        elif i == 3:
            medal = "🥉"

        else:
            medal = f"{i}位"

        st.markdown(
            f"""
            <div class="ranking-card">

            <b style="font-size:20px">
            {medal}
            {data["emoji"]}
            {name}
            </b>

            <br>

            <span style="opacity:.7">
            {data["title"]}
            </span>

            <br><br>

            類似度指数：
            <b>{result["similarity"]:.1f}%</b>

            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # 100人全部
    # --------------------------------------------------------

    with st.expander(
        "👥 100人すべてのランキングを見る"
    ):

        for i, result in enumerate(
            ranking,
            start=1
        ):

            data = PEOPLE[
                result["person"]
            ]

            st.write(
                f"**{i}位　"
                f"{data['emoji']} "
                f"{result['person']}**　"
                f"{result['similarity']:.1f}%"
            )

    # --------------------------------------------------------
    # レポート保存
    # --------------------------------------------------------

    st.divider()

    st.header(
        "📄 診断結果を保存"
    )

    report = create_report()

    safe_name = (
        st.session_state.name
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )

    st.download_button(
        "📥 診断レポートを保存",
        data=report.encode(
            "utf-8"
        ),
        file_name=(
            f"{safe_name}_歴史上の人物診断.txt"
        ),
        mime="text/plain",
        use_container_width=True
    )

    json_data = {
        "name":
            st.session_state.name,

        "best_match":
            best_name,

        "similarity":
            best["similarity"],

        "scores":
            scores,

        "ranking":
            ranking
    }

    st.download_button(
        "💾 診断データをJSONで保存",
        data=json.dumps(
            json_data,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8"),
        file_name=(
            f"{safe_name}_personality.json"
        ),
        mime="application/json",
        use_container_width=True
    )

    # --------------------------------------------------------
    # 再診断
    # --------------------------------------------------------

    st.write("")

    if st.button(
        "🔄 最初から診断する",
        use_container_width=True
    ):

        reset_app()

    st.markdown(
        """
        <div class="footer">

        この診断は自己理解・エンターテインメントを
        目的としています。<br>

        医学的・心理学的な診断ではありません。<br><br>

        歴史上の人物の性格スコアは、
        実際の心理検査結果ではなく、
        一般的な人物像を参考にした
        本アプリ独自のモデルです。

        </div>
        """,
        unsafe_allow_html=True
    )
