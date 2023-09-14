import streamlit as st
import sqlite3
import bcrypt
import pandas as pd
import matplotlib.pyplot as plt
import datetime

# アプリ、画面設定
st.set_page_config(
    page_title="成績分析アプリ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# データベースに接続（存在しない場合は新規作成されます）
conn = sqlite3.connect('user.db')
c = conn.cursor()

# ユーザーテーブルを作成（存在しない場合のみ）
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)''')

# 成績テーブルを作成（存在しない場合のみ）
c.execute('''CREATE TABLE IF NOT EXISTS scores
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, score REAL, rank INTEGER, date DATE)''')

# データベースへの変更を保存
conn.commit()

# サイドバーにログインと新規ユーザー登録のフォームを表示
st.sidebar.title("ユーザーログインと登録")

# セッション状態を初期化
if 'username' not in st.session_state:
    st.session_state.username = None

# ページの状態を示す変数
page_state = st.sidebar.radio("アクションを選択してください:", ("ログイン", "成績入力/出力", "分析", "ログアウト", "新規ユーザー登録"))

# 初期変数
df = pd.DataFrame([], [])

if page_state == "新規ユーザー登録":
    st.sidebar.subheader("新規ユーザー登録")
    new_username = st.sidebar.text_input("新しいユーザー名")
    new_password = st.sidebar.text_input("新しいパスワード", type="password")

    if st.sidebar.button("新規ユーザー登録"):
        if new_username and new_password:
            # 既存のユーザー名をデータベースから検索
            c.execute("SELECT * FROM users WHERE username=?", (new_username,))
            existing_user = c.fetchone()

            if existing_user:
                st.sidebar.error("ユーザー名は既に存在します。別のユーザー名を選択してください。")
            else:
                # パスワードをハッシュ化
                hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

                # ユーザーデータをデータベースに挿入
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_username, hashed_password))
                conn.commit()
                st.sidebar.success("ユーザー登録が成功しました。ログインして各種機能を使用できます。")

elif page_state == "ログイン":
    st.sidebar.subheader("ログイン")
    username = st.sidebar.text_input("ユーザー名")
    password = st.sidebar.text_input("パスワード", type="password")

    if st.sidebar.button("ログイン"):
        if username and password:
            # ユーザーデータをデータベースから取得
            c.execute("SELECT * FROM users WHERE username=?", (username,))
            user = c.fetchone()

            if user and bcrypt.checkpw(password.encode('utf-8'), user[2]):
                st.sidebar.success("ログインに成功しました.")
                st.session_state.username = username
                st.title("サイドバーからメニューを選択してください")

# ログアウトの処理
if page_state == "ログアウト":
    st.sidebar.success("ログアウトしました.")
    st.session_state.username = None
    page_state = "ログイン"

# 成績入力/出力
elif page_state == "成績入力/出力":
    st.title("成績入力/出力ページ")

    # 成績入力フォーム
    user_id = st.session_state.username

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("入力する:")
        score = st.number_input("得点を入力してください",min_value=-300.0, max_value=300.0, value=0.0,step=0.1, format="%.1f")
        rank = st.selectbox("着順を入力してください", ("入力しない", 1, 2, 3, 4))
        date = st.date_input("日付を選択してください", datetime.date.today())

        if st.button("成績を記録"):
            if rank == "入力しない":
                c.execute("INSERT INTO scores (user_id, score, rank, date) VALUES (?, ?, NULL, ?)",
                          (user_id, score, date))
                conn.commit()
                st.success("成績を記録しました。")
            elif user_id and score is not None and rank and date:
                # 成績データをデータベースに挿入
                c.execute("INSERT INTO scores (user_id, score, rank, date) VALUES (?, ?, ?, ?)",
                          (user_id, score, rank, date))
                conn.commit()
                st.success("成績を記録しました。")

        # ユーザーごとの成績データをデータベースから取得
        if user_id:
            c.execute("SELECT id, score, rank, date FROM scores WHERE user_id=?", (user_id,))
            user_scores = c.fetchall()

            # 取得データのデータフレーム化
            df = pd.DataFrame(user_scores, columns=["ID", "得点", "着順", "日付"])
            df.index += 1  # 行番号を0から始めるために1を加える

            if user_scores:

                # データ削除用のセレクトボックス
                st.subheader("削除する:")
                selected_id = st.selectbox("IDを選択してください", df["ID"])
                st.warning("一度削除したデータは修復できません")
                if st.button("データを削除"):
                    # 選択したIDに対応するデータを削除
                    c.execute("DELETE FROM scores WHERE id=?", (selected_id,))
                    conn.commit()
                    st.success("データを削除しました.")
                    # データ削除後、データベースから新しいデータを取得し直す
                    c.execute("SELECT id, score, rank, date FROM scores WHERE user_id=?", (user_id,))
                    user_scores = c.fetchall()
                    df = pd.DataFrame(user_scores, columns=["ID", "得点", "着順", "日付"])
                    df.index += 1  # 行番号を0から始めるために1を加える

            else:
                st.warning("成績データがありません。成績を入力してください。")

    with col2:
        if not df.empty:
            # ユーザーID列を非表示にして成績データを表示
            st.subheader("データフレーム")
            st.dataframe(df.drop(columns=["ID"]), use_container_width=True)
        elif st.session_state.username:
            st.write("データがありません")
        else:
            st.write("ログインしてください")

elif page_state == "分析":
    st.subheader("分析")

    user_id = st.session_state.username
    c.execute("SELECT score, rank, date FROM scores WHERE user_id=?", (user_id,))
    user_scores = c.fetchall()

    # 取得データのデータフレーム化
    df_origin = pd.DataFrame(user_scores, columns=["得点", "着順", "日付"])
    df = df_origin.dropna()  # NaNデータ列を除外

    df_sorted_by_date = df.sort_values(by="日付", ascending=True)
    df_sorted_by_date = df_sorted_by_date.reset_index(drop=True)

    df_cumsum = df_sorted_by_date["得点"].cumsum()

    # タブ定義
    tab_graph, tab_analysis, tab_dataframe = st.tabs(["グラフ", "統計", "データフレーム"])

    with tab_graph:
        # 日付ごと
        st.subheader("得点(1局毎)")
        st.line_chart(df_sorted_by_date["得点"])

        # 累積和
        st.subheader("累積得点")
        st.area_chart(df_cumsum, color="#ff7f50")

        # 順位の変遷
        st.subheader("着順")
        #(0,0)が左上になるように準備
        fig, ax = plt.subplots(figsize=(10,3))
        
        ax.set_ylim([5, 0])
        
        ax.plot(df_sorted_by_date["着順"], marker='o', markersize = 20, color = "tab:green")
        st.pyplot(fig)

    with tab_analysis:
        col_analysis, col_discription = st.columns(2)
        with col_analysis:
            st.subheader("あなたの成績統計")
            match_count = df["得点"].count()
            match_count_exist_rank = df["着順"].count()
            sum_scores = df["得点"].sum()

            # 順位ごとのカウント
            match_count_1st = df[df["着順"] == 1]["着順"].count()
            match_count_2nd = df[df["着順"] == 2]["着順"].count()
            match_count_3rd = df[df["着順"] == 3]["着順"].count()
            match_count_4th = df[df["着順"] == 4]["着順"].count()

            sum_scores_exist_rank = df["得点"].sum()  # 順位あり総得点

            score_max_all = df_origin["得点"].max()
            score_min_all = df_origin["得点"].min()

            score_max = df["得点"].max()
            score_min = df["得点"].min()

            def per_match(number):
                return round((number / match_count_exist_rank) * 100, 2)

            rentai = df[df["着順"] < 3]["着順"].count()
            last_avoid = 100 - per_match(match_count_4th)

            mean = round(df["得点"].mean(), 3)
            std = round(df["得点"].std(), 3)
            rank_mean = round(df["着順"].mean(), 2)  # 順位があるところのみで計算

            data_analysis = [
                [f"{match_count_exist_rank}回","" , f"{match_count}回"],
                [f"{sum_scores_exist_rank}", "", f"{sum_scores}"],
                [f"{mean}","",""],
                [std,"",""],
                [rank_mean, "", ""],
                [f"{match_count_1st}回", f"{per_match(match_count_1st)}%",""],
                [f"{match_count_4th}回", f"{per_match(match_count_4th)}%", ""],
                [f"{rentai}回", f"{per_match(rentai)}%", ""],
                [f"{match_count-match_count_4th}回", f"{last_avoid}%", ""],
                [f"{score_max}","",f"{score_max_all}"],
                [f"{score_min}","", f"{score_min_all}"]
                ]
            columns_analysis = ["全データ", "試合数に対する割合","(順位なしを含む)"]
            index_analysis = ["試合数","総ポイント","平均得点", "標準偏差","平均着順","トップ数","ラス数","連対数","ラス回避","最大ポイント","最小ポイント"]
            df_analysis = pd.DataFrame(data_analysis, columns=columns_analysis, index= index_analysis)

            st.dataframe(df_analysis)

        with col_discription:
            st.subheader("各値の説明")

            with st.expander("平均と標準偏差", expanded=False):
                st.subheader("平均は位置、標準偏差は広がりを表す")
                st.write("統計的なこの2つの量は試合数が多くなればなるほど有用性が増します。\
                50試合ほどすれば自身の本当の実力に近い値が出ると期待されます。\
                標準偏差は小さいほど安定性がある打ち方であると言えます。")

            with st.expander("連対", expanded=False):
                st.subheader("2位以上にどれだけなれているか")
                st.write("連対とは終了時に1位もしくは2位であることです。\
                         一般に50%を上回っていれば良い打ち方であると言えます。\
                         固定メンバーで打つとき60%を超えればトップ層であるといえます。\
                         Mリーグを例に挙げれば、各シーズンで個人成績トップの選手は約67%の連対率になってます。\
                         ")
                
            with st.expander("トップ率", expanded=False):
                st.subheader("チャンスを活かせているか、ピンチを凌げているか")
                st.write("全員が同じ実力なら確率的にトップ率は25%になります。\
                         Mリーグの各シーズンのトップ率1位の平均は44.3%です。")

            with st.expander("ラス回避", expanded=False):
                st.subheader("慎重に打っているか")
                st.write("全員が同じ実力なら確率的にラス回避率は75%になります。この数字がより大きければ慎重派であると言えます。\
                         Mリーグの各シーズンのラス回避1位の平均は93.6%です。\
                         ラス回避率が高くても素点によってはポイントがマイナスになることもあるため注意が必要です。")
    with tab_dataframe:
        st.write(df)

# データベース接続を閉じる
conn.close()
