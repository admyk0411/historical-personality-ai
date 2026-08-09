import streamlit as st
import json
import os
from datetime import datetime

# ============================================================
# さっき作った100問・100人版からデータを読み込む
# ============================================================

try:
    from historical_personality_ai import (
        TRAITS,
        PEOPLE,
        QUESTIONS,
        find_top_people,
        closest_traits
    )

except Exception as e:

    st.error(
        "historical_personality_ai.py を読み込めませんでした。"
    )

    st.write(
        "historical_personality_web.py と "
        "historical_personality_ai.py を "
        "同じデスクトップに置いてください。"
    )

    st.code(str(e))

    st.stop()


# ============================================================
# 基本設定
# ============================================================

st.set_page_config(
    page_title="歴史人物性格診断AI",
    page_icon="🏛️",
    layout="centered"
)

WEB_DATA_FILE = "web_personality_data.json"
AI_RESULT_FILE = "web_ai_analysis.txt"

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5"
)


def get_openai_api_key():
    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        return os.getenv("OPENAI_API_KEY")

# ============================================================
# デザイン
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        text-align: center;
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .sub-title {
        text-align: center;
        font-size: 18px;
        color: gray;
        margin-bottom: 30px;
    }

    .question-box {
        padding: 28px;
        border-radius: 18px;
        border: 1px solid #dddddd;
        margin-top: 20px;
        margin-bottom: 20px;
    }

    .result-box {
        padding: 22px;
        border-radius: 18px;
        border: 1px solid #dddddd;
        margin-bottom: 15px;
    }

    .person-name {
        font-size: 28px;
        font-weight: bold;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# データ
# ============================================================

def new_data():

    return {
        "answers": [],
        "completed": False
    }


def load_data():

    if not os.path.exists(WEB_DATA_FILE):

        return new_data()

    try:

        with open(
            WEB_DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return new_data()


def save_data(data):

    with open(
        WEB_DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# セッション初期化
# ============================================================

if "data" not in st.session_state:

    st.session_state.data = load_data()


if "page" not in st.session_state:

    st.session_state.page = "ホーム"


# ============================================================
# 性格スコア計算
# ============================================================

def calculate_scores(data):

    score_sum = {
        trait: 0
        for trait in TRAITS
    }

    question_count = {
        trait: 0
        for trait in TRAITS
    }

    for answer in data["answers"]:

        trait = answer["trait"]

        score_sum[trait] += answer["score"]

        question_count[trait] += 1

    scores = {}

    for trait in TRAITS:

        count = question_count[trait]

        if count == 0:

            scores[trait] = 0

        else:

            maximum = count * 10

            scores[trait] = round(
                score_sum[trait]
                / maximum
                * 100
            )

    return scores


# ============================================================
# 回答処理
# ============================================================

def register_answer(choice):

    data = st.session_state.data

    current_number = len(
        data["answers"]
    )

    if current_number >= len(QUESTIONS):

        return

    q = QUESTIONS[current_number]

    selected_text = (
        q["a"]
        if choice == "a"
        else q["b"]
    )

    score = (
        10
        if choice == q["high_choice"]
        else 0
    )

    data["answers"].append(
        {
            "number": q["number"],
            "trait": q["trait"],
            "question": q["question"],
            "answer": selected_text,
            "choice": choice,
            "score": score,
            "date": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }
    )

    if len(data["answers"]) >= len(QUESTIONS):

        data["completed"] = True

        st.session_state.page = "結果"

    save_data(data)

    st.session_state.data = data


# ============================================================
# リセット
# ============================================================

def reset_diagnosis():

    st.session_state.data = new_data()

    save_data(
        st.session_state.data
    )

    st.session_state.page = "ホーム"


# ============================================================
# サイドバー
# ============================================================

with st.sidebar:

    st.title("🏛️ メニュー")

    pages = [
        "ホーム",
        "性格診断",
        "結果",
        "AI詳細分析",
        "歴史人物一覧"
    ]

    selected_page = st.radio(
        "ページ",
        pages,
        index=pages.index(
            st.session_state.page
        )
    )

    st.session_state.page = selected_page

    st.divider()

    answered = len(
        st.session_state.data["answers"]
    )

    st.write(
        f"回答数：{answered}/100"
    )

    st.progress(
        min(answered / 100, 1.0)
    )

    st.divider()

    if st.button(
        "🗑️ 診断を最初からやり直す"
    ):

        reset_diagnosis()

        st.rerun()


# ============================================================
# 共通タイトル
# ============================================================

st.markdown(
    """
    <div class="main-title">
    🏛️ 歴史人物性格診断AI
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="sub-title">
    100の質問から、
    あなたに近い歴史人物を分析します
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# ホーム
# ============================================================

if st.session_state.page == "ホーム":

    st.subheader(
        "あなたは歴史上の誰に近い？"
    )

    st.write(
        """
        100個の質問に答えることで、
        あなたの考え方や行動傾向を
        10種類の性格軸で分析します。

        その結果を歴史人物100人の
        アプリ内プロフィールと比較します。
        """
    )

    st.info(
        """
        この診断は娯楽・自己分析用です。

        心理学的・医学的な
        性格診断ではありません。
        """
    )

    answered = len(
        st.session_state.data["answers"]
    )

    if answered == 0:

        button_text = "診断をスタート 🚀"

    elif answered < 100:

        button_text = (
            f"{answered + 1}問目から続ける ▶"
        )

    else:

        button_text = "診断結果を見る 🏆"

    if st.button(
        button_text,
        use_container_width=True,
        type="primary"
    ):

        if answered >= 100:

            st.session_state.page = "結果"

        else:

            st.session_state.page = "性格診断"

        st.rerun()


# ============================================================
# 性格診断
# ============================================================

elif st.session_state.page == "性格診断":

    data = st.session_state.data

    current = len(
        data["answers"]
    )

    if current >= len(QUESTIONS):

        st.success(
            "🎉 100問すべて完了しました！"
        )

        if st.button(
            "診断結果を見る",
            type="primary",
            use_container_width=True
        ):

            st.session_state.page = "結果"

            st.rerun()

    else:

        q = QUESTIONS[current]

        progress = (
            current
            / len(QUESTIONS)
        )

        st.progress(progress)

        st.write(
            f"### 質問 {current + 1} / 100"
        )

        st.caption(
            f"分析カテゴリー：{q['trait']}"
        )

        st.markdown(
            f"""
            <div class="question-box">
            <h2>{q["question"]}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("どちらが自分に近いですか？")

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "A\n\n" + q["a"],
                use_container_width=True,
                type="primary",
                key=f"a_{current}"
            ):

                register_answer("a")

                st.rerun()

        with col2:

            if st.button(
                "B\n\n" + q["b"],
                use_container_width=True,
                key=f"b_{current}"
            ):

                register_answer("b")

                st.rerun()

        st.caption(
            "回答は1問ごとに自動保存されます。"
        )


# ============================================================
# 結果
# ============================================================

elif st.session_state.page == "結果":

    data = st.session_state.data

    if len(data["answers"]) == 0:

        st.warning(
            "まだ質問に回答していません。"
        )

    else:

        if not data["completed"]:

            st.warning(
                "まだ100問すべて終了していないため、"
                "現在は暫定結果です。"
            )

        scores = calculate_scores(data)

        results = find_top_people(
            scores,
            10
        )

        winner = results[0]

        st.subheader(
            "🏆 あなたの歴史人物タイプ"
        )

        st.markdown(
            f"""
            <div class="result-box">

            <div class="person-name">
            {winner["person"]["name"]}タイプ
            </div>

            <br>

            アプリ内類似度：
            <b>{winner["similarity"]}%</b>

            <br><br>

            カテゴリー：
            {winner["person"]["category"]}

            </div>
            """,
            unsafe_allow_html=True
        )

        st.caption(
            "※類似度は科学的確率ではなく、"
            "このアプリ内のプロフィールとの近さです。"
        )

        st.divider()

        st.subheader(
            "📊 あなたの10種類の性格スコア"
        )

        sorted_scores = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        for trait, score in sorted_scores:

            st.write(
                f"**{trait}　{score}/100**"
            )

            st.progress(
                score / 100
            )

        st.divider()

        st.subheader(
            "🥇 歴史人物ランキング TOP5"
        )

        for rank, result in enumerate(
            results[:5],
            start=1
        ):

            person = result["person"]

            common = closest_traits(
                scores,
                person
            )

            with st.expander(
                f"{rank}位　"
                f"{person['name']} "
                f"｜{result['similarity']}%"
            ):

                st.write(
                    f"**カテゴリー：** "
                    f"{person['category']}"
                )

                st.write(
                    "**特に近い特徴：** "
                    + "・".join(common)
                )

                st.write(
                    "**人物プロフィール**"
                )

                for trait in TRAITS:

                    st.write(
                        f"{trait}: "
                        f"{person['traits'][trait]}"
                    )

        st.divider()

        if st.button(
            "🤖 AIに詳しく分析してもらう",
            type="primary",
            use_container_width=True
        ):

            st.session_state.page = (
                "AI詳細分析"
            )

            st.rerun()


# ============================================================
# AI詳細分析
# ============================================================

elif st.session_state.page == "AI詳細分析":

    data = st.session_state.data

    st.subheader(
        "🤖 AIによる詳細分析"
    )

    if len(data["answers"]) == 0:

        st.warning(
            "まず性格診断をしてください。"
        )

    elif not get_openai_api_key():

        st.error(
            "OPENAI_API_KEY が設定されていません。"
        )

        st.write(
            """
            OpenAI APIキーが設定されていません。
            Streamlit CloudのSecrets設定を
            確認してください。
            """
        )

    else:

        scores = calculate_scores(data)

        results = find_top_people(
            scores,
            5
        )

        st.write(
            """
            100問の回答・10種類の性格スコア・
            歴史人物TOP5をLLMに渡して、
            分析文章を生成します。
            """
        )

        if not data["completed"]:

            st.warning(
                "100問終了前なので暫定分析になります。"
            )

        if st.button(
            "✨ AI分析を開始",
            type="primary",
            use_container_width=True
        ):

            try:

                from openai import OpenAI

                client = OpenAI(
                    api_key=get_openai_api_key()
                )

                score_text = "\n".join(
                    f"{trait}: {value}/100"
                    for trait, value
                    in sorted(
                        scores.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )
                )

                people_text = ""

                for rank, result in enumerate(
                    results,
                    start=1
                ):

                    person = result["person"]

                    people_text += (
                        f"\n{rank}位 "
                        f"{person['name']}\n"
                    )

                    people_text += (
                        f"カテゴリー: "
                        f"{person['category']}\n"
                    )

                    people_text += (
                        f"類似度: "
                        f"{result['similarity']}%\n"
                    )

                    people_text += (
                        "プロフィール: "
                        + ", ".join(
                            f"{trait}="
                            f"{person['traits'][trait]}"
                            for trait in TRAITS
                        )
                        + "\n"
                    )

                answers_text = "\n".join(
                    f"{answer['number']}. "
                    f"{answer['question']} "
                    f"→ {answer['answer']}"
                    for answer
                    in data["answers"]
                )

                instructions = """
あなたは娯楽・自己分析用の
歴史人物性格診断AIです。

必ず以下を守ってください。

・心理学的・医学的診断とは表現しない。
・ユーザーの人格を断定しない。
・「今回の回答では〜の傾向があります」
  という表現を使う。
・歴史人物の性格数値は
  このアプリ専用の仮プロフィールである。
・類似度を科学的確率として扱わない。
・日本語で分かりやすく説明する。
・歴史人物について、
  提供されていない事実を作らない。
"""

                prompt = f"""
以下の性格診断結果を分析してください。


====================

【性格スコア】

{score_text}


====================

【歴史人物TOP5】

{people_text}


====================

【質問への回答】

{answers_text}


====================


以下の形式で回答してください。


# あなたの性格タイプ

特徴を一言で表す。


# 総合分析

今回の回答から見える
考え方・価値観・行動傾向を説明。


# あなたの強み

4〜5個。


# 注意すると良い傾向

3〜4個。


# 最も近い歴史人物

1位の人物を説明。


# なぜこの人物なのか

性格スコアを使って説明。


# 共通点

3〜5個。


# 違うところ

プロフィール数値の違いを説明。


# 2位・3位との違い

なぜ1位の方が近かったか説明。


# 仕事で活かせそうな特徴

向いている環境や役割を説明。
職業を断定しない。


# 学習スタイル

結果から考えられる
勉強方法を説明。


# 人間関係

コミュニケーションの
強みと注意点。


# 最後に

結果を簡潔にまとめる。


最後に必ず、

「この結果は娯楽・自己分析を目的とした
アプリ内プロフィールとの比較であり、
心理学的な性格診断ではありません。」

と記載してください。
"""

                with st.spinner(
                    "AIが分析しています..."
                ):

                    response = (
                        client.responses.create(
                            model=OPENAI_MODEL,
                            instructions=instructions,
                            input=prompt
                        )
                    )

                result_text = (
                    response.output_text
                )

                st.success(
                    "AI分析が完成しました！"
                )

                st.markdown(
                    result_text
                )

                with open(
                    AI_RESULT_FILE,
                    "w",
                    encoding="utf-8"
                ) as f:

                    f.write(
                        result_text
                    )

            except Exception as e:

                st.error(
                    "AI分析中にエラーが発生しました。"
                )

                st.code(
                    str(e)
                )

                st.write(
                    """
                    APIキー・API利用設定・モデル名を
                    確認してください。
                    """
                )


# ============================================================
# 歴史人物一覧
# ============================================================

elif st.session_state.page == "歴史人物一覧":

    st.subheader(
        f"🏛️ 歴史人物 {len(PEOPLE)}人"
    )

    st.write(
        "診断で比較対象になっている人物です。"
    )

    search = st.text_input(
        "人物名・カテゴリーを検索"
    )

    filtered_people = []

    for person in PEOPLE:

        text = (
            person["name"]
            + person["category"]
        )

        if (
            search == ""
            or search.lower()
            in text.lower()
        ):

            filtered_people.append(
                person
            )

    st.write(
        f"{len(filtered_people)}人表示"
    )

    for person in filtered_people:

        with st.expander(
            f"{person['name']} "
            f"｜{person['category']}"
        ):

            for trait in TRAITS:

                score = (
                    person["traits"][trait]
                )

                st.write(
                    f"**{trait}："
                    f"{score}/100**"
                )

                st.progress(
                    score / 100
                )


# ============================================================
# 最後の注意書き
# ============================================================

st.divider()

st.caption(
    """
    このアプリは娯楽・自己分析を目的としたものです。
    歴史人物の性格数値は比較用の仮プロフィールであり、
    心理学的・医学的診断ではありません。
    """
)