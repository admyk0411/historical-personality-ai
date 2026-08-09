import streamlit as st
import math
import json
from datetime import datetime

# ============================================================
# 歴史上の人物 性格診断
# 100問 × 100人物 / 外部API不要
# ============================================================

st.set_page_config(
    page_title="歴史上の人物 性格診断",
    page_icon="🏛️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

CATEGORIES = [
    "リーダーシップ", "挑戦心", "論理性", "共感性", "社交性",
    "創造性", "計画性", "独立性", "忍耐力", "好奇心"
]

CHOICES = [
    "とてもそう思う",
    "そう思う",
    "どちらともいえない",
    "そう思わない",
    "まったくそう思わない",
]

CHOICE_TO_SCORE = {
    "とてもそう思う": 5,
    "そう思う": 4,
    "どちらともいえない": 3,
    "そう思わない": 2,
    "まったくそう思わない": 1,
}

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

QUESTIONS = [
    (text, category, direction)
    for category in CATEGORIES
    for text, direction in QUESTION_BANK[category]
]

# 100人それぞれが個別の10軸スコアを持つ。
# 順番は CATEGORIES と同じ。
PEOPLE_DATA = r"""
織田信長|4.9|4.7|4.2|3.0|3.8|4.7|3.7|4.7|4.4|4.4
徳川家康|4.3|4.0|4.9|3.1|2.9|3.9|4.9|4.3|4.6|4.3
豊臣秀吉|4.3|4.2|4.3|4.5|5.0|4.0|4.0|3.9|4.5|3.9
坂本龍馬|3.7|4.9|3.9|3.7|4.0|4.2|3.0|4.8|4.7|5.0
西郷隆盛|4.3|4.1|3.8|4.7|4.8|3.6|4.0|4.1|5.0|4.0
宮本武蔵|3.1|3.9|4.5|3.1|2.3|4.7|4.3|5.0|4.9|4.3
福沢諭吉|2.9|3.4|5.0|3.9|2.9|4.4|3.9|4.8|4.3|5.0
渋沢栄一|3.9|4.4|4.5|4.3|4.0|4.6|3.9|4.5|4.6|4.8
伊能忠敬|2.9|3.9|4.9|3.6|2.6|4.5|3.7|4.7|4.9|5.0
紫式部|3.1|4.1|3.5|3.8|3.3|4.9|2.7|4.7|4.1|5.0
聖徳太子|4.5|3.7|4.8|4.0|3.8|3.2|4.6|4.3|4.9|4.1
勝海舟|4.2|4.1|4.1|4.6|4.8|3.9|4.0|3.9|4.6|4.2
吉田松陰|3.0|3.6|5.0|4.0|2.7|4.3|3.6|5.0|4.4|5.0
本田宗一郎|4.4|5.0|4.4|3.3|4.5|5.0|3.8|4.7|4.7|4.7
盛田昭夫|4.5|5.0|4.0|3.3|4.9|4.8|4.0|4.6|4.9|4.5
松下幸之助|4.2|3.9|4.6|3.7|3.7|3.6|4.9|4.1|4.8|3.7
黒澤明|3.1|4.1|3.2|3.8|3.3|5.0|3.2|4.9|4.0|4.8
手塚治虫|3.0|4.1|3.5|4.3|3.1|5.0|2.9|4.9|4.2|4.6
北里柴三郎|2.8|3.9|5.0|3.4|2.7|4.7|3.6|4.7|4.7|4.9
野口英世|2.9|4.0|4.9|3.6|2.8|4.7|3.4|4.7|4.8|5.0
諸葛亮|4.7|3.4|5.0|3.2|3.0|4.1|5.0|4.4|4.8|4.3
劉備|4.7|4.3|4.1|4.8|4.2|3.6|3.9|4.1|4.8|3.8
曹操|4.4|3.4|4.9|3.1|3.1|4.2|4.7|4.5|5.0|4.5
孫子|4.3|3.8|4.8|3.4|3.0|4.1|5.0|4.3|4.6|4.4
孔子|3.0|3.7|4.8|4.1|3.0|4.2|3.5|4.9|4.1|5.0
老子|2.8|3.6|4.9|4.1|2.9|4.5|3.6|5.0|4.5|5.0
始皇帝|5.0|4.5|4.3|3.8|4.3|3.4|4.5|4.5|4.9|3.8
玄奘|3.7|5.0|3.9|3.7|4.2|4.3|3.1|5.0|4.6|5.0
鄭和|3.7|5.0|4.1|3.6|4.1|4.3|3.0|4.9|4.9|4.9
李白|2.7|3.9|3.5|3.8|3.3|5.0|3.0|5.0|4.4|5.0
レオナルド・ダ・ヴィンチ|4.3|4.3|4.7|3.8|4.0|4.5|4.1|4.3|4.6|5.0
アルベルト・アインシュタイン|3.0|4.1|4.8|3.2|2.4|4.8|3.6|4.8|4.8|5.0
マリー・キュリー|3.0|3.8|5.0|3.5|2.5|4.4|3.7|4.6|4.8|4.8
トーマス・エジソン|3.6|4.8|4.8|3.3|3.3|5.0|3.8|4.8|4.6|5.0
ニコラ・テスラ|3.4|4.7|4.7|3.1|3.2|5.0|3.9|4.8|4.7|4.9
チャールズ・ダーウィン|2.8|3.9|5.0|3.5|2.5|4.7|3.7|4.7|4.8|5.0
アイザック・ニュートン|2.9|3.8|5.0|3.5|2.6|4.7|3.6|4.7|4.7|4.9
ガリレオ・ガリレイ|3.0|4.0|5.0|3.5|2.7|4.4|3.6|5.0|4.8|4.8
アラン・チューリング|2.8|4.2|5.0|3.2|2.4|4.4|3.6|5.0|4.9|5.0
エイダ・ラブレス|3.4|4.6|4.4|2.8|3.2|5.0|3.8|4.9|4.6|5.0
ジョン・フォン・ノイマン|4.4|4.4|4.7|4.2|4.0|4.4|3.9|4.2|4.4|5.0
リチャード・ファインマン|4.1|4.5|4.6|3.8|3.8|4.6|4.1|4.5|4.5|4.9
ルイ・パスツール|2.7|3.9|5.0|3.5|2.6|4.8|3.6|4.7|4.7|5.0
グレゴール・メンデル|3.0|4.2|5.0|3.8|2.5|4.5|3.5|4.8|4.6|4.9
ジェームズ・ワット|3.6|4.8|4.6|3.0|3.6|5.0|3.6|4.7|4.7|4.9
ライト兄弟|3.7|4.6|4.6|2.8|3.3|5.0|3.8|4.7|5.0|5.0
アレクサンダー・グラハム・ベル|3.5|4.7|4.7|2.7|3.0|4.8|3.8|4.6|4.9|5.0
ロバート・フック|4.0|4.3|4.4|3.9|3.8|4.7|4.2|4.4|4.6|4.7
ヨハネス・ケプラー|3.0|4.2|5.0|3.2|2.6|4.8|3.9|4.7|5.0|5.0
コペルニクス|3.1|4.2|4.9|3.4|2.8|4.7|3.7|4.9|4.7|5.0
ソクラテス|3.0|3.7|5.0|3.8|2.8|4.4|3.7|4.8|4.2|5.0
プラトン|2.8|3.6|4.6|4.2|2.9|4.5|3.3|4.7|4.5|4.9
アリストテレス|4.0|4.6|4.8|3.9|4.0|4.5|3.9|4.3|4.8|5.0
ルネ・デカルト|3.0|3.8|4.8|4.4|2.8|4.5|3.5|4.9|4.1|5.0
イマヌエル・カント|2.7|3.5|4.9|4.1|3.1|4.3|3.3|5.0|4.4|5.0
フリードリヒ・ニーチェ|2.9|3.8|4.6|3.9|2.8|4.8|3.6|5.0|4.3|5.0
ジャン＝ジャック・ルソー|3.1|3.5|4.9|3.9|2.8|4.2|3.7|4.9|4.4|5.0
ジョン・ロック|2.9|3.4|5.0|4.1|2.7|4.6|3.6|5.0|4.1|5.0
アダム・スミス|2.8|3.6|4.7|3.8|3.0|4.3|3.4|5.0|4.7|4.8
マックス・ウェーバー|2.8|4.2|5.0|3.6|2.7|4.7|3.5|4.8|4.7|5.0
ナポレオン|5.0|4.5|4.1|3.8|4.2|3.4|4.1|4.4|5.0|3.7
アレクサンドロス大王|4.8|4.6|4.4|3.8|4.3|3.4|4.3|4.7|4.7|4.0
ユリウス・カエサル|4.7|4.4|4.4|4.0|4.3|3.5|4.3|4.4|4.7|3.8
アウグストゥス|4.0|4.0|4.5|3.9|3.6|3.2|4.8|4.1|4.8|3.8
マルクス・アウレリウス|3.0|3.6|4.7|4.0|3.3|4.4|3.6|4.9|4.5|5.0
ジャンヌ・ダルク|4.8|4.4|4.2|3.7|4.1|3.7|4.2|4.5|5.0|3.8
エリザベス1世|5.0|4.3|4.3|4.0|4.0|3.5|4.3|4.6|4.8|4.1
ヴィクトリア女王|4.2|3.8|4.7|3.7|3.7|3.4|4.9|4.3|4.8|4.1
ウィンストン・チャーチル|5.0|4.2|4.2|3.9|4.1|3.4|4.4|4.7|4.9|3.8
シャルル・ド・ゴール|4.7|4.5|4.4|3.6|4.3|3.7|4.4|4.7|4.6|4.0
ピョートル大帝|4.8|4.8|4.1|2.9|3.7|4.8|3.8|4.9|4.3|4.3
ジョージ・ワシントン|4.8|4.8|4.0|4.0|4.3|3.4|4.3|4.4|4.7|3.9
セオドア・ルーズベルト|4.7|4.6|4.3|3.3|3.6|5.0|3.6|4.9|4.3|4.6
フランクリン・ルーズベルト|4.4|4.1|3.9|5.0|4.2|3.5|4.3|4.1|5.0|3.9
ジョン・F・ケネディ|4.2|4.2|3.9|4.4|5.0|3.8|4.0|4.1|4.2|4.0
エイブラハム・リンカーン|4.4|3.8|3.8|4.9|4.1|3.9|4.0|4.3|4.7|3.9
マハトマ・ガンジー|4.6|3.9|4.0|5.0|4.2|3.4|4.3|4.3|4.8|4.0
ネルソン・マンデラ|4.4|4.0|4.1|5.0|4.3|3.6|4.2|4.6|5.0|4.1
マーティン・ルーサー・キング・ジュニア|4.6|4.0|4.2|5.0|4.3|3.6|4.2|4.1|5.0|3.9
マララ・ユスフザイ|4.5|3.9|4.1|4.9|4.3|3.5|4.1|4.3|5.0|4.2
フローレンス・ナイチンゲール|4.9|4.7|4.1|3.0|3.9|4.9|3.9|4.9|4.1|4.4
マザー・テレサ|4.5|4.3|4.0|4.8|4.1|3.5|4.3|4.1|4.7|4.1
ヘレン・ケラー|4.5|3.8|4.3|5.0|4.5|3.7|4.0|4.1|5.0|4.1
ワンガリ・マータイ|4.7|4.2|4.2|4.9|4.4|3.7|3.9|4.1|5.0|4.1
クララ・バートン|4.5|4.2|3.9|5.0|4.5|3.3|4.0|4.3|4.9|4.0
ジェーン・アダムズ|4.6|3.8|4.2|4.9|4.1|3.9|4.1|4.3|5.0|4.1
アルベルト・シュバイツァー|4.0|4.2|4.4|4.0|4.2|4.7|4.2|4.6|4.7|4.7
レイチェル・カーソン|2.9|4.0|5.0|3.4|2.7|4.7|3.5|5.0|4.5|5.0
ハリエット・タブマン|4.4|4.2|4.0|4.7|4.2|3.7|4.4|4.1|5.0|4.0
アンネ・フランク|2.7|4.1|3.2|3.8|3.0|5.0|2.7|4.6|4.2|5.0
スティーブ・ジョブズ|4.9|4.8|4.2|3.2|4.7|5.0|4.0|5.0|4.5|4.8
ウォルト・ディズニー|4.7|5.0|4.3|3.2|4.4|5.0|4.2|4.9|4.8|4.6
ヘンリー・フォード|4.4|3.9|4.8|4.0|3.7|3.4|4.8|4.0|5.0|3.8
アンドリュー・カーネギー|4.6|5.0|4.4|3.6|4.7|4.6|4.1|4.6|4.6|4.6
ジョン・D・ロックフェラー|4.0|3.6|4.4|3.9|4.2|3.3|4.8|4.0|4.9|4.1
ビル・ゲイツ|4.7|3.6|4.7|3.3|2.9|4.2|4.9|4.6|4.8|4.3
ジェフ・ベゾス|4.5|5.0|4.2|3.4|4.4|4.9|4.3|4.9|4.8|4.7
オプラ・ウィンフリー|4.5|4.2|4.0|4.7|5.0|3.8|4.1|4.4|4.6|4.1
ミケランジェロ|2.8|3.9|3.3|3.9|3.2|4.9|3.2|4.7|4.3|4.6
パブロ・ピカソ|3.0|3.9|3.4|4.1|3.2|5.0|2.9|4.8|4.4|5.0
""".strip()


def load_people():
    people = {}
    errors = []

    if not PEOPLE_DATA:
        return {}, ["人物データが空です。"]

    for line_no, raw_line in enumerate(PEOPLE_DATA.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = [p.strip() for p in line.split("|")]

        if len(parts) != 11:
            errors.append(
                f"人物データ{line_no}行目: 項目数が11ではありません。"
            )
            continue

        name = parts[0]

        if not name:
            errors.append(f"人物データ{line_no}行目: 名前が空です。")
            continue

        if name in people:
            errors.append(f"人物データ{line_no}行目: {name} が重複しています。")
            continue

        try:
            scores = [float(x) for x in parts[1:]]
        except ValueError:
            errors.append(f"人物データ{line_no}行目: 数値変換できないスコアがあります。")
            continue

        people[name] = {"scores": scores}

    return people, errors


PEOPLE, PEOPLE_LOAD_ERRORS = load_people()


def validate_app_data():
    errors = list(PEOPLE_LOAD_ERRORS)

    if len(CATEGORIES) != 10:
        errors.append(f"性格軸が10個ではありません。現在: {len(CATEGORIES)}")

    if len(set(CATEGORIES)) != len(CATEGORIES):
        errors.append("性格軸に重複があります。")

    if len(QUESTIONS) != 100:
        errors.append(f"質問数が100問ではありません。現在: {len(QUESTIONS)}問")

    per_category = {c: 0 for c in CATEGORIES}
    reverse_per_category = {c: 0 for c in CATEGORIES}

    for i, item in enumerate(QUESTIONS, start=1):
        if not isinstance(item, tuple) or len(item) != 3:
            errors.append(f"質問{i}: データ形式が不正です。")
            continue

        text, category, direction = item

        if not isinstance(text, str) or not text.strip():
            errors.append(f"質問{i}: 質問文が空です。")

        if category not in CATEGORIES:
            errors.append(f"質問{i}: 不正なカテゴリー {category}")

        if direction not in (1, -1):
            errors.append(f"質問{i}: 採点方向は1または-1である必要があります。")

        if category in per_category:
            per_category[category] += 1
            if direction == -1:
                reverse_per_category[category] += 1

    for category in CATEGORIES:
        if per_category[category] != 10:
            errors.append(
                f"{category}: 質問数が10問ではありません。現在: {per_category[category]}問"
            )

        if reverse_per_category[category] < 2:
            errors.append(
                f"{category}: 逆転質問が2問未満です。現在: {reverse_per_category[category]}問"
            )

    if len(PEOPLE) != 100:
        errors.append(f"人物数が100人ではありません。現在: {len(PEOPLE)}人")

    seen_vectors = set()

    for name, data in PEOPLE.items():
        scores = data.get("scores")

        if not isinstance(scores, list) or len(scores) != 10:
            errors.append(f"{name}: 性格スコアが10項目ではありません。")
            continue

        for idx, score in enumerate(scores):
            if not isinstance(score, (int, float)):
                errors.append(f"{name}: {CATEGORIES[idx]} が数値ではありません。")
            elif not 1.0 <= score <= 5.0:
                errors.append(
                    f"{name}: {CATEGORIES[idx]}={score} は1〜5の範囲外です。"
                )

        vector = tuple(scores)
        if vector in seen_vectors:
            errors.append(f"{name}: 他人物と10軸スコアが完全一致しています。")
        seen_vectors.add(vector)

    return errors


DATA_ERRORS = validate_app_data()

if DATA_ERRORS:
    st.error("アプリの診断データに問題があります。")
    st.write("GitHubのコードを確認してください。検出内容:")
    for error in DATA_ERRORS[:30]:
        st.write(f"・{error}")

    if len(DATA_ERRORS) > 30:
        st.write(f"・ほか {len(DATA_ERRORS) - 30} 件")

    st.stop()


DEFAULT_STATE = {
    "page": "start",
    "name": "",
    "question_index": 0,
    "answers": {},
    "scores": None,
    "ranking": None,
}

for key, default in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default


def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def calculate_scores():
    totals = {c: 0.0 for c in CATEGORIES}
    counts = {c: 0 for c in CATEGORIES}

    for index, raw_score in st.session_state.answers.items():
        if index < 0 or index >= len(QUESTIONS):
            continue

        _, category, direction = QUESTIONS[index]

        score = raw_score if direction == 1 else 6 - raw_score

        totals[category] += score
        counts[category] += 1

    result = {}

    for category in CATEGORIES:
        if counts[category] != 10:
            raise ValueError(
                f"{category} の有効回答数が10ではありません: {counts[category]}"
            )

        result[category] = round(totals[category] / counts[category], 2)

    return result


def profile_distance(user_scores, person_scores):
    # 10軸を同じ重みで比較するユークリッド距離。
    return math.sqrt(
        sum(
            (user_scores[category] - person_scores[i]) ** 2
            for i, category in enumerate(CATEGORIES)
        )
    )


def calculate_ranking(user_scores):
    raw = []

    for name, data in PEOPLE.items():
        distance = profile_distance(user_scores, data["scores"])
        raw.append({"person": name, "distance": distance})

    raw.sort(key=lambda x: x["distance"])

    # 類似度指数:
    # 「確率」ではなく、距離を0〜100の見やすい指数へ変換したもの。
    # 指数関数にすることで、近い人物ほど差が見えやすくなる。
    scale = 3.6

    for item in raw:
        similarity = 100.0 * math.exp(-item["distance"] / scale)
        item["similarity"] = round(max(0.0, min(99.5, similarity)), 1)

    return raw


def score_level(score):
    if score >= 4.4:
        return "非常に高い"
    if score >= 3.8:
        return "高い"
    if score >= 3.2:
        return "やや高い"
    if score >= 2.8:
        return "中程度"
    if score >= 2.2:
        return "やや低い"
    return "低い"


def trait_explanation(category, score):
    high = {
        "リーダーシップ": "人をまとめ、判断し、方向性を示す場面で力を発揮しやすいです。",
        "挑戦心": "未知の課題や変化を成長機会として捉えやすいです。",
        "論理性": "根拠・構造・データを整理して判断する傾向が強いです。",
        "共感性": "相手の立場や感情への感度が高く、関係性を大切にします。",
        "社交性": "人との交流やネットワークづくりからエネルギーを得やすいです。",
        "創造性": "既存の枠を越えて新しい組み合わせや解決策を考えやすいです。",
        "計画性": "先を見通し、手順や優先順位を組んで進めることが得意です。",
        "独立性": "周囲に流されず、自分の判断基準で考えやすいです。",
        "忍耐力": "すぐ結果が出なくても、継続して積み上げる力があります。",
        "好奇心": "未知の知識や仕組みを知ることへの欲求が強いです。",
    }

    low = {
        "リーダーシップ": "自分が先頭に立つより、専門性や支援役で力を発揮しやすい傾向があります。",
        "挑戦心": "未知へ飛び込むより、確実性や安全性を確認してから動く傾向があります。",
        "論理性": "数値や構造だけでなく、直感・経験・人間的な要素も重視しやすいです。",
        "共感性": "感情への配慮より、目的・事実・効率を優先する場面が比較的多いです。",
        "社交性": "大人数より、一人または少人数で集中できる環境を好みやすいです。",
        "創造性": "斬新さより、実績のある方法や再現性を重視する傾向があります。",
        "計画性": "細かな計画より、状況を見ながら柔軟に対応する方が自然です。",
        "独立性": "単独判断より、周囲の意見や合意を確認して進める傾向があります。",
        "忍耐力": "長期戦より、短期間で成果や変化が見える課題の方が力を出しやすいです。",
        "好奇心": "幅広く探索するより、必要な領域や既に関心のある分野を深めやすいです。",
    }

    if score >= 3.6:
        return high[category]

    if score <= 2.6:
        return low[category]

    return "極端に偏らず、状況に応じてこの特性を使い分けるバランス型です。"


def personality_summary(scores):
    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top = ordered[:3]
    low = sorted(scores.items(), key=lambda x: x[1])[:2]

    return (
        f"あなたの中で特に強いのは「{top[0][0]}」「{top[1][0]}」「{top[2][0]}」です。"
        f"最大の特徴である「{top[0][0]}」は {top[0][1]:.1f}/5.0。"
        f"{trait_explanation(top[0][0], top[0][1])} "
        f"一方、「{low[0][0]}」「{low[1][0]}」は他の特性と比べると低めです。"
        "低い項目は欠点を意味するものではなく、あなたが自然にエネルギーを使う方向との違いを示しています。"
    )


def match_reason(user_scores, person_name):
    person_scores = PEOPLE[person_name]["scores"]

    diffs = []
    for i, category in enumerate(CATEGORIES):
        difference = abs(user_scores[category] - person_scores[i])
        diffs.append((difference, category, user_scores[category], person_scores[i]))

    diffs.sort(key=lambda x: x[0])
    close = diffs[:3]

    return (
        f"特に近いのは、"
        f"「{close[0][1]}」({close[0][2]:.1f} ↔ {close[0][3]:.1f})、"
        f"「{close[1][1]}」({close[1][2]:.1f} ↔ {close[1][3]:.1f})、"
        f"「{close[2][1]}」({close[2][2]:.1f} ↔ {close[2][3]:.1f})です。"
    )


def biggest_differences(user_scores, person_name):
    person_scores = PEOPLE[person_name]["scores"]

    diffs = []
    for i, category in enumerate(CATEGORIES):
        difference = abs(user_scores[category] - person_scores[i])
        diffs.append((difference, category, user_scores[category], person_scores[i]))

    diffs.sort(key=lambda x: x[0], reverse=True)
    return diffs[:2]


def radar_svg(scores):
    width = 640
    height = 640
    cx = width / 2
    cy = height / 2
    radius = 205
    n = len(CATEGORIES)

    angles = [
        -math.pi / 2 + 2 * math.pi * i / n
        for i in range(n)
    ]

    def point(angle, r):
        return (
            cx + math.cos(angle) * r,
            cy + math.sin(angle) * r,
        )

    grid = ""
    for level in range(1, 6):
        r = radius * level / 5
        pts = []
        for angle in angles:
            x, y = point(angle, r)
            pts.append(f"{x:.1f},{y:.1f}")

        grid += (
            f'<polygon points="{" ".join(pts)}" '
            'fill="none" stroke="rgba(128,128,128,0.25)" stroke-width="1"/>'
        )

    axes = ""
    for angle in angles:
        x, y = point(angle, radius)
        axes += (
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
            'stroke="rgba(128,128,128,0.20)" stroke-width="1"/>'
        )

    user_points = []
    dots = ""

    for category, angle in zip(CATEGORIES, angles):
        r = radius * scores[category] / 5
        x, y = point(angle, r)
        user_points.append(f"{x:.1f},{y:.1f}")
        dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#4f7cff"/>'

    polygon = (
        f'<polygon points="{" ".join(user_points)}" '
        'fill="rgba(79,124,255,0.20)" stroke="#4f7cff" stroke-width="3"/>'
    )

    labels = ""
    for category, angle in zip(CATEGORIES, angles):
        x, y = point(angle, radius + 64)
        anchor = "middle"

        c = math.cos(angle)
        if c > 0.3:
            anchor = "start"
        elif c < -0.3:
            anchor = "end"

        labels += (
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            'dominant-baseline="middle" font-size="14" font-weight="700" '
            f'fill="currentColor">{category}</text>'
        )

    return f"""
    <div style="width:100%;overflow-x:auto;text-align:center;">
      <svg viewBox="0 0 {width} {height}" style="width:100%;max-width:640px;height:auto;"
           xmlns="http://www.w3.org/2000/svg">
        {grid}
        {axes}
        {polygon}
        {dots}
        {labels}
      </svg>
    </div>
    """


def create_report():
    scores = st.session_state.scores
    ranking = st.session_state.ranking
    best = ranking[0]
    best_name = best["person"]

    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    lines = [
        "歴史上の人物 性格診断",
        "=" * 48,
        f"名前: {st.session_state.name}",
        f"診断日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"最も近い人物: {best_name}",
        f"類似度指数: {best['similarity']:.1f}%",
        "",
        "【なぜ近いのか】",
        match_reason(scores, best_name),
        "",
        "【性格総評】",
        personality_summary(scores),
        "",
        "【10軸スコア】",
    ]

    for category, score in ordered:
        lines.append(
            f"{category}: {score:.2f}/5.00 ({score_level(score)})"
        )

    lines += ["", "【人物ランキング TOP10】"]

    for i, item in enumerate(ranking[:10], start=1):
        lines.append(
            f"{i}位 {item['person']} / 類似度指数 {item['similarity']:.1f}%"
        )

    lines += [
        "",
        "※類似度指数は確率ではありません。",
        "※本診断は自己理解・エンターテインメント用で、医学的・心理学的診断ではありません。",
        "※人物の10軸数値は、人物像を診断用にモデル化したアプリ独自のデータです。",
    ]

    return "\n".join(lines)


# ============================================================
# START
# ============================================================

if st.session_state.page == "start":
    st.title("🏛️ 歴史上の人物 性格診断")
    st.subheader("100の質問 × 100人の歴史的人物")

    st.write(
        "100問の回答を10の性格軸に分けて分析し、"
        "100人すべての人物プロフィールと比較します。"
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("質問", len(QUESTIONS))
    with c2:
        st.metric("性格軸", len(CATEGORIES))
    with c3:
        st.metric("人物候補", len(PEOPLE))

    with st.expander("診断の仕組み"):
        st.write(
            "各性格軸につき10問、合計100問です。"
            "各軸には逆転質問を2問入れており、単純にすべて同じ選択肢を選ぶだけでは"
            "高得点にならないようにしています。"
        )
        st.write(
            "最終結果では、あなたの10軸プロフィールと100人それぞれの10軸プロフィールの"
            "距離を比較してランキングします。"
        )

    name = st.text_input(
        "名前・ニックネーム",
        placeholder="例：まさと",
        max_chars=30,
    )

    if st.button("診断をはじめる →", type="primary", use_container_width=True):
        clean_name = name.strip()

        if not clean_name:
            st.warning("名前またはニックネームを入力してください。")
        else:
            st.session_state.name = clean_name
            st.session_state.question_index = 0
            st.session_state.answers = {}
            st.session_state.scores = None
            st.session_state.ranking = None
            st.session_state.page = "quiz"
            st.rerun()


# ============================================================
# QUIZ
# ============================================================

elif st.session_state.page == "quiz":
    current = st.session_state.question_index
    total = len(QUESTIONS)

    if current < 0 or current >= total:
        st.error("質問位置が不正になったため、最初の質問に戻しました。")
        st.session_state.question_index = 0
        st.rerun()

    question_text, _, _ = QUESTIONS[current]
    answered = len(st.session_state.answers)

    st.subheader(f"{st.session_state.name} さんの診断")
    st.progress(answered / total)
    st.caption(f"回答済み {answered}/{total} ｜ 質問 {current + 1}/{total}")

    st.info(f"### Q{current + 1}. {question_text}")

    previous_score = st.session_state.answers.get(current)
    default_index = None

    if previous_score is not None:
        for i, label in enumerate(CHOICES):
            if CHOICE_TO_SCORE[label] == previous_score:
                default_index = i
                break

    selected = st.radio(
        "あなたに最も近いものを選んでください",
        CHOICES,
        index=default_index,
        key=f"answer_{current}",
    )

    left, right = st.columns(2)

    with left:
        if current == 0:
            if st.button("← 最初に戻る", use_container_width=True):
                reset_app()
        else:
            if st.button("← 前の質問", use_container_width=True):
                if selected is not None:
                    st.session_state.answers[current] = CHOICE_TO_SCORE[selected]

                st.session_state.question_index -= 1
                st.rerun()

    with right:
        if current < total - 1:
            if st.button("次の質問 →", type="primary", use_container_width=True):
                if selected is None:
                    st.warning("回答を1つ選んでください。")
                else:
                    st.session_state.answers[current] = CHOICE_TO_SCORE[selected]
                    st.session_state.question_index += 1
                    st.rerun()
        else:
            if st.button("🏆 診断結果を見る", type="primary", use_container_width=True):
                if selected is None:
                    st.warning("最後の質問に回答してください。")
                else:
                    st.session_state.answers[current] = CHOICE_TO_SCORE[selected]

                    missing = [
                        i for i in range(total)
                        if i not in st.session_state.answers
                    ]

                    if missing:
                        st.warning(
                            f"未回答が {len(missing)} 問あります。最初の未回答へ移動します。"
                        )
                        st.session_state.question_index = missing[0]
                        st.rerun()

                    try:
                        scores = calculate_scores()
                        ranking = calculate_ranking(scores)
                    except Exception as exc:
                        st.error("診断計算中に問題が発生しました。")
                        st.code(str(exc))
                        st.stop()

                    st.session_state.scores = scores
                    st.session_state.ranking = ranking
                    st.session_state.page = "result"
                    st.rerun()

    st.caption("迷った場合は「どちらともいえない」を選んで問題ありません。")


# ============================================================
# RESULT
# ============================================================

elif st.session_state.page == "result":
    scores = st.session_state.scores
    ranking = st.session_state.ranking

    if not isinstance(scores, dict) or not isinstance(ranking, list) or not ranking:
        st.warning("結果データが見つからないため、スタート画面へ戻ります。")
        st.session_state.page = "start"
        st.rerun()

    best = ranking[0]
    best_name = best["person"]

    st.balloons()

    st.title("🎉 診断結果")
    st.subheader(f"{st.session_state.name} さんに最も近い人物")
    st.header(f"🏆 {best_name}")
    st.metric("類似度指数", f"{best['similarity']:.1f}%")
    st.caption("※類似度指数は確率ではなく、このアプリ独自の比較指数です。")

    st.divider()

    st.header("🔍 なぜこの人物に近いのか")
    st.write(match_reason(scores, best_name))

    large_diffs = biggest_differences(scores, best_name)
    if large_diffs:
        st.write("一方で、完全に同じタイプではありません。特に差があるのは:")
        for diff, category, user_score, person_score in large_diffs:
            st.write(
                f"・**{category}**：あなた {user_score:.1f} / 人物モデル {person_score:.1f}"
            )

    st.divider()

    st.header("🧠 あなたの性格総評")
    st.write(personality_summary(scores))

    ordered_scores = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    st.subheader("🔥 強み TOP3")

    medals = ["🥇", "🥈", "🥉"]

    for i, (category, score) in enumerate(ordered_scores[:3]):
        st.write(f"### {medals[i]} {category} — {score:.1f}/5.0")
        st.write(trait_explanation(category, score))

    st.subheader("🌱 相対的に低い3項目")

    for category, score in sorted(scores.items(), key=lambda x: x[1])[:3]:
        st.write(f"**{category} — {score:.1f}/5.0**")
        st.write(trait_explanation(category, score))

    st.divider()

    st.header("🕸️ 性格レーダー")
    st.markdown(radar_svg(scores), unsafe_allow_html=True)

    st.divider()

    st.header("📊 10軸の詳細")

    for category, score in ordered_scores:
        c1, c2 = st.columns([1, 3])

        with c1:
            st.metric(category, f"{score:.1f}")

        with c2:
            st.progress((score - 1) / 4)
            st.caption(f"{score_level(score)} — {trait_explanation(category, score)}")

    st.divider()

    st.header("🏛️ あなたに近い人物 TOP10")

    for rank, item in enumerate(ranking[:10], start=1):
        prefix = {
            1: "🥇",
            2: "🥈",
            3: "🥉",
        }.get(rank, f"{rank}位")

        st.write(
            f"### {prefix} {item['person']} — 類似度指数 {item['similarity']:.1f}%"
        )

        if rank <= 3:
            st.caption(match_reason(scores, item["person"]))

    with st.expander("100人すべてのランキングを見る"):
        for rank, item in enumerate(ranking, start=1):
            st.write(
                f"**{rank}位 {item['person']}** — {item['similarity']:.1f}%"
            )

    st.divider()

    st.header("📄 診断結果を保存")

    report = create_report()

    safe_name = (
        st.session_state.name
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )

    st.download_button(
        "📥 診断レポートを保存",
        data=report.encode("utf-8-sig"),
        file_name=f"{safe_name}_歴史上の人物性格診断.txt",
        mime="text/plain",
        use_container_width=True,
    )

    json_result = {
        "name": st.session_state.name,
        "created_at": datetime.now().isoformat(timespec="minutes"),
        "best_match": best_name,
        "similarity_index": best["similarity"],
        "scores": scores,
        "ranking": [
            {
                "rank": i + 1,
                "person": item["person"],
                "similarity_index": item["similarity"],
            }
            for i, item in enumerate(ranking)
        ],
    }

    st.download_button(
        "💾 診断データをJSONで保存",
        data=json.dumps(
            json_result,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
        file_name=f"{safe_name}_personality.json",
        mime="application/json",
        use_container_width=True,
    )

    st.write("")

    if st.button("🔄 最初からもう一度診断する", use_container_width=True):
        reset_app()

    st.divider()

    st.caption(
        "この診断は自己理解・エンターテインメントを目的としています。"
        "医学的・心理学的な診断ではありません。"
        "歴史上の人物の10軸スコアは実際の心理検査結果ではなく、"
        "一般的な人物像を参考に診断用にモデル化したアプリ独自のデータです。"
    )
