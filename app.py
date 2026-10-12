import re
import streamlit as st
import pandas as pd
import preprocessor, helper
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

# ---------------------------------------------------------------
# Page settings
# ---------------------------------------------------------------
st.set_page_config(page_title="WhatsApp Chat Analyzer", layout="wide")

# Colours used everywhere
ACCENT = "#2F6B4F"      # dark green
LIGHT = "#B8C4CC"       # light grey
DARK = "#1F2933"        # almost black
PIE_COLORS = ["#2F6B4F", "#4A7FB0", "#C98B2B", "#B5584A", "#7A6FA8", "#8D99A5"]

# Simple look for the page
st.markdown(
    """
    <style>
    #MainMenu, footer {visibility: hidden;}
    .tile {
        border: 1px solid #DDE2E6;
        border-radius: 4px;
        padding: 14px 16px;
        background: #FFFFFF;
        margin-bottom: 10px;
    }
    .tile .label { font-size: 13px; color: #52606D; }
    .tile .value { font-size: 30px; font-weight: 600; color: #1F2933; line-height: 1.25; }
    .tile .value.text { font-size: 22px; line-height: 1.7; }
    .emoji-table { border-collapse: collapse; width: 100%; color: #1F2933; }
    .emoji-table th { text-align: left; font-size: 13px; color: #52606D;
                      border-bottom: 1px solid #DDE2E6; padding: 6px 8px; }
    .emoji-table td { padding: 6px 8px; border-bottom: 1px solid #EEF1F3; font-size: 16px; }
    .emoji-table td.emoji { font-size: 26px;
        font-family: "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif; }
    .swatch { display: inline-block; width: 12px; height: 12px; border-radius: 2px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Same simple look for all charts
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#9AA5B1",
    "axes.labelcolor": "#3E4C59",
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": "#E6E9EC",
    "grid.linewidth": 0.8,
    "xtick.color": "#52606D",
    "ytick.color": "#52606D",
    "font.size": 10,
})


# ---------------------------------------------------------------
# Small helper functions (only for display)
# ---------------------------------------------------------------
def show_tile(label, value):
    if isinstance(value, (int, float)):
        value = f"{int(value):,}"
        css = "value"
    else:
        css = "value text"
    st.markdown(
        f'<div class="tile"><div class="label">{label}</div><div class="{css}">{value}</div></div>',
        unsafe_allow_html=True,
    )


def new_chart(width=8, height=4, grid="y"):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.grid(False)
    if grid == "y":
        ax.yaxis.grid(True)
    if grid == "x":
        ax.xaxis.grid(True)
    return fig, ax


def show_chart(fig):
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def hbar(series, color=ACCENT, width=6, height=4, xlabel="Messages"):
    """Horizontal bar chart (biggest bar on top)."""
    fig, ax = new_chart(width, height, grid="x")
    bars = ax.barh(series.index, series.values, color=color)
    ax.invert_yaxis()
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xlabel(xlabel)
    show_chart(fig)


# ---------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------
st.sidebar.title("WhatsApp Chat Analyzer")
st.sidebar.write("1. Upload the chat file (.txt)")
uploaded_file = st.sidebar.file_uploader("Choose a file")

# ---------------------------------------------------------------
# Home page (no file yet)
# ---------------------------------------------------------------
if uploaded_file is None:
    st.title("WhatsApp Chat Analyzer")
    st.write(
        "Find out who talks the most, when the chat is busiest, "
        "and which words and emojis are used the most."
    )
    st.subheader("How to use")
    st.markdown(
        "1. In WhatsApp, open a chat and choose **Export chat** (without media).  \n"
        "2. Upload the .txt file using the sidebar on the left.  \n"
        "3. Select a person, or **Overall** for the whole group."
    )
    st.stop()

# ---------------------------------------------------------------
# Read the file
# ---------------------------------------------------------------
try:
    bytes_data = uploaded_file.getvalue()
    data = bytes_data.decode("utf-8")
    all_df = preprocessor.preprocess(data)
except Exception:
    st.error("This file could not be read. Please upload a WhatsApp chat exported as .txt")
    st.stop()

if all_df[all_df['event'] == 'message'].shape[0] == 0:
    st.error("No messages were found in this file. Please check the file and try again.")
    st.stop()

# Option to hide phone numbers (useful when showing on a big screen)
st.sidebar.write("2. Choose how names are shown")
hide_numbers = st.sidebar.checkbox("Hide phone numbers", value=True)
if hide_numbers:
    numbers = [u for u in all_df['user'].unique() if u.startswith('+')]
    names = {number: f"Member {i + 1}" for i, number in enumerate(numbers)}
    all_df['user'] = all_df['user'].replace(names)

# df = only real messages (used for all the charts)
# all_df = everything, including deleted messages, joined, left (used for counts)
df = all_df[all_df['event'] == 'message'].reset_index(drop=True)

# fetch unique users
user_list = df['user'].unique().tolist()
if 'group_notification' in user_list:
    user_list.remove('group_notification')
user_list.sort()
user_list.insert(0, "Overall")

st.sidebar.write("3. Select a person")
selected_user = st.sidebar.selectbox("Show analysis for", user_list)

# ---------------------------------------------------------------
# Numbers used on the page
# ---------------------------------------------------------------
num_messages, words, num_media_messages, num_links = helper.fetch_stats(selected_user, df)
deleted = helper.count_deleted(selected_user, all_df)
peak_label, peak_count, peak_hour = helper.peak_time(selected_user, df)
top_day, top_day_count = helper.busiest_date(selected_user, df)
start_date = df['date'].min().strftime("%d %b %Y")
end_date = df['date'].max().strftime("%d %b %Y")

# ---------------------------------------------------------------
# Page header
# ---------------------------------------------------------------
st.title("WhatsApp Chat Analyzer")
st.caption(f"{uploaded_file.name}   |   {start_date} to {end_date}   |   Showing: {selected_user}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Timeline", "Activity", "Words", "Emoji"])

# ---------------------------------------------------------------
# Tab 1 : Overview
# ---------------------------------------------------------------
with tab1:
    st.subheader("Top Statistics")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        show_tile("Total Messages", num_messages)
    with col2:
        show_tile("Total Words", words)
    with col3:
        show_tile("Media Shared", num_media_messages)
    with col4:
        show_tile("Links Shared", num_links)

    changes = helper.group_changes(all_df)
    share = num_messages / df.shape[0] * 100

    col1, col2, col3, col4 = st.columns(4)
    if selected_user == 'Overall':
        with col1:
            show_tile("Number of Users", helper.number_of_users(all_df))
        with col2:
            show_tile("Messages Deleted", deleted)
        with col3:
            show_tile("People Left", changes['left'])
        with col4:
            show_tile("Peak Time of Chat", peak_label)
    else:
        with col1:
            show_tile("Share of Chat", f"{share:.1f}%")
        with col2:
            show_tile("Messages Deleted", deleted)
        with col3:
            show_tile("Busiest Day", top_day)
        with col4:
            show_tile("Peak Time", peak_label)

    # short summary in simple words
    st.subheader("Summary")
    if selected_user == 'Overall':
        x, new_df = helper.most_busy_users(df)
        st.markdown(
            f"- The chat has **{num_messages:,}** messages from **{helper.number_of_users(all_df)}** people, "
            f"between {start_date} and {end_date}.\n"
            f"- **{new_df['name'][0]}** is the most active person with **{new_df['messages'][0]:,}** messages "
            f"({new_df['percent'][0]}% of the chat).\n"
            f"- The chat is busiest between **{peak_label}**. "
            f"The busiest day was **{top_day}** with **{top_day_count:,}** messages.\n"
            f"- **{num_media_messages:,}** messages were media files and **{deleted:,}** messages were deleted."
        )
    else:
        st.markdown(
            f"- **{selected_user}** sent **{num_messages:,}** messages, which is {share:.1f}% of the chat.\n"
            f"- Most messages were sent between **{peak_label}**.\n"
            f"- The busiest day was **{top_day}** with **{top_day_count:,}** messages.\n"
            f"- **{num_media_messages:,}** messages were media files and **{deleted:,}** messages were deleted."
        )

    # busiest users and group changes (Group level)
    if selected_user == 'Overall':
        st.subheader("Most Active Users")
        col1, col2 = st.columns(2)
        with col1:
            hbar(x, height=4.5)
        with col2:
            st.dataframe(new_df.set_index('name'), height=360)

        st.subheader("Group Changes")
        changes_df = pd.DataFrame(
            {"People": [changes['joined'], changes['added'], changes['left'], changes['removed']]},
            index=["Joined using invite link", "Added by a member", "Left the group", "Removed by an admin"],
        )
        st.table(changes_df)

    # media breakdown
    st.subheader("Media Shared")
    media = helper.media_breakdown(selected_user, df)
    if media.shape[0] == 0:
        st.write("No media was shared.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            hbar(media, height=3, xlabel="Number of files")

# ---------------------------------------------------------------
# Tab 2 : Timeline
# ---------------------------------------------------------------
with tab2:
    # monthly timeline
    st.subheader("Monthly Timeline")
    st.caption("Number of messages sent in each month.")
    timeline = helper.monthly_timeline(selected_user, df)
    fig, ax = new_chart(10, 4)
    bars = ax.bar(timeline['time'], timeline['message'], color=ACCENT, width=0.55)
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.margins(y=0.12)
    ax.set_ylabel("Messages")
    if timeline.shape[0] > 6:
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    show_chart(fig)

    # daily timeline
    st.subheader("Daily Timeline")
    st.caption("Number of messages sent on each day.")
    daily_timeline = helper.daily_timeline(selected_user, df)
    fig, ax = new_chart(10, 4)
    ax.plot(daily_timeline['only_date'], daily_timeline['message'], color=ACCENT, linewidth=1.5)
    ax.fill_between(daily_timeline['only_date'], daily_timeline['message'], color=ACCENT, alpha=0.12)
    ax.set_ylabel("Messages")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    show_chart(fig)

# ---------------------------------------------------------------
# Tab 3 : Activity
# ---------------------------------------------------------------
with tab3:
    st.subheader("Peak Time of Chat")
    st.caption(f"Messages sent in each hour of the day. The chat is busiest between {peak_label}.")
    hours = helper.hourly_activity(selected_user, df)
    fig, ax = new_chart(10, 3.8)
    colors = [ACCENT if h == peak_hour else LIGHT for h in hours.index]
    ax.bar(hours.index, hours.values, color=colors, width=0.7)
    ax.margins(y=0.08)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([helper.hour_text(h) for h in range(0, 24, 2)])
    ax.set_ylabel("Messages")
    show_chart(fig)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Most Busy Day")
        busy_day = helper.week_activity_map(selected_user, df)
        hbar(busy_day, height=3.5)

    with col2:
        st.subheader("Most Busy Month")
        busy_month = helper.month_activity_map(selected_user, df)
        hbar(busy_month, color="#4A7FB0", height=3.5)

    st.subheader("Weekly Activity Map")
    st.caption("A darker box means more messages on that day and hour.")
    user_heatmap = helper.activity_heatmap(selected_user, df)
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.heatmap(user_heatmap, cmap="Greens", linewidths=0.5, linecolor="white",
                cbar_kws={"shrink": 0.8}, ax=ax)
    ax.grid(False)
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.setp(ax.get_xticklabels(), rotation=90, fontsize=8)
    plt.setp(ax.get_yticklabels(), rotation=0)
    show_chart(fig)

# ---------------------------------------------------------------
# Tab 4 : Words
# ---------------------------------------------------------------
with tab4:
    col1, col2 = st.columns(2)

    # WordCloud
    with col1:
        st.subheader("Wordcloud")
        st.caption("A bigger word means it is used more often.")
        df_wc = helper.create_wordcloud(selected_user, df)
        if df_wc is None:
            st.write("Not enough words to make a word cloud.")
        else:
            fig, ax = plt.subplots(figsize=(7, 4.5))
            ax.imshow(df_wc, interpolation="bilinear")
            ax.axis("off")
            show_chart(fig)

    # most common words
    with col2:
        st.subheader("Most Common Words")
        st.caption("The 20 words used the most.")
        most_common_df = helper.most_common_words(selected_user, df)
        if most_common_df.shape[0] == 0:
            st.write("Not enough words to show.")
        else:
            fig, ax = new_chart(7, 6, grid="x")
            ax.barh(most_common_df[0], most_common_df[1], color=ACCENT)
            ax.invert_yaxis()
            ax.set_xlabel("Times used")
            show_chart(fig)

# ---------------------------------------------------------------
# Tab 5 : Emoji
# ---------------------------------------------------------------
with tab5:
    st.subheader("Emoji Analysis")
    emoji_df = helper.emoji_helper(selected_user, df)

    if emoji_df.shape[0] == 0:
        st.write("No emojis were used.")
    else:
        # top 5 emojis, everything else is grouped as "Others"
        total = int(emoji_df['count'].sum())
        top = emoji_df.head(5)
        labels = top['emoji'].tolist()
        values = top['count'].tolist()
        if total - sum(values) > 0:
            labels.append("Others")
            values.append(total - sum(values))
        colors = PIE_COLORS[:len(values)]

        col1, col2 = st.columns(2)

        # Chart (shows only the percentage) ...
        with col1:
            fig, ax = plt.subplots(figsize=(5, 5))
            ax.grid(False)
            ax.pie(
                values,
                colors=colors,
                startangle=90,
                counterclock=False,
                wedgeprops=dict(width=0.42, edgecolor="white"),
                autopct=lambda p: f"{p:.0f}%" if p >= 6 else "",
                pctdistance=0.79,
                textprops=dict(color="white", fontsize=11),
            )
            ax.text(0, 0, f"{total:,}\nemojis", ha="center", va="center", fontsize=13, color=DARK)
            show_chart(fig)

        # ... and the emojis are shown next to it in a clear list
        with col2:
            rows = ""
            for label, value, color in zip(labels, values, colors):
                percent = value / total * 100
                rows += (
                    f'<tr><td><span class="swatch" style="background:{color}"></span></td>'
                    f'<td class="emoji">{label if label != "Others" else "Others"}</td>'
                    f'<td>{value:,}</td><td>{percent:.1f}%</td></tr>'
                )
            st.markdown(
                f'<table class="emoji-table"><tr><th></th><th>Emoji</th><th>Count</th><th>Share</th></tr>{rows}</table>',
                unsafe_allow_html=True,
            )

        st.subheader("All Emojis")
        st.dataframe(emoji_df.set_index('emoji'), height=300)
