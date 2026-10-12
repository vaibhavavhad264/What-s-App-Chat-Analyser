import re
from urlextract import URLExtract
from wordcloud import WordCloud
import pandas as pd
from collections import Counter
import emoji
extractor = URLExtract()

# Media lines look like:  <image omitted>   <sticker omitted>   <document omitted> file.pdf
MEDIA_TAG = r'<[^<>\n]*omitted>'


def load_stop_words():
    with open('stop_hinglish.txt', 'r') as f:
        return set(f.read().split())


def remove_media_tag(message):
    # remove <image omitted> style tags and the [forwarded] tag, keep the real text
    message = re.sub(MEDIA_TAG, '', message)
    message = re.sub(r'\[forwarded\]', '', message, flags=re.I)
    return message.strip()


def fetch_stats(selected_user,df):

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    # fetch the number of messages
    num_messages = df.shape[0]

    # fetch the total number of words
    words = []
    for message in df['message']:
        words.extend(remove_media_tag(message).split())

    # fetch number of media messages (image, video, sticker, document, audio, GIF)
    num_media_messages = df[df['message'].str.contains(MEDIA_TAG, regex=True)].shape[0]

    # fetch number of links shared
    links = []
    for message in df['message']:
        links.extend(extractor.find_urls(message))

    return num_messages,len(words),num_media_messages,len(links)


def media_breakdown(selected_user, df):

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    # take the word before "omitted", for example image / sticker / document
    types = df['message'].str.extract(r'<([^<>\n]*?)\s*omitted>')[0].dropna()
    types = types.str.strip().str.capitalize()
    types = types.replace({'Gif': 'GIF', 'Media': 'Other media'})

    return types.value_counts()


def most_busy_users(df):
    counts = df['user'].value_counts()
    x = counts.head(10)
    new_df = pd.DataFrame({
        'name': counts.index,
        'messages': counts.values,
        'percent': (counts / df.shape[0] * 100).round(2).values
    })
    return x, new_df


def count_deleted(selected_user, all_df):

    if selected_user != 'Overall':
        all_df = all_df[all_df['user'] == selected_user]

    return all_df[all_df['event'] == 'deleted'].shape[0]


def group_changes(all_df):
    # how many people joined, were added, left or were removed
    people = all_df.groupby('event')['people'].sum()

    result = {}
    for name in ['joined', 'added', 'left', 'removed']:
        result[name] = int(people.get(name, 0))
    return result


def number_of_users(all_df):
    return all_df[all_df['user'] != 'group_notification']['user'].nunique()


def hour_text(hour):
    # 21 -> "9 PM"
    hour = hour % 24
    suffix = "AM" if hour < 12 else "PM"
    return f"{hour % 12 or 12} {suffix}"


def hourly_activity(selected_user, df):

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    return df['hour'].value_counts().reindex(range(24), fill_value=0).sort_index()


def peak_time(selected_user, df):
    hours = hourly_activity(selected_user, df)
    peak_hour = int(hours.idxmax())
    return f"{hour_text(peak_hour)} - {hour_text(peak_hour + 1)}", int(hours.max()), peak_hour


def busiest_date(selected_user, df):

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    per_day = df.groupby('only_date').size()
    top_day = per_day.idxmax()
    return top_day.strftime("%d %b %Y"), int(per_day.max())


def create_wordcloud(selected_user,df):

    stop_words = load_stop_words()

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    temp = df[df['user'] != 'group_notification'].copy()

    def remove_stop_words(message):
        y = []
        for word in remove_media_tag(message).lower().split():
            if word not in stop_words and not word.startswith('http'):
                y.append(word)
        return " ".join(y)

    temp['message'] = temp['message'].apply(remove_stop_words)
    text = temp['message'].str.cat(sep=" ").strip()

    if text == "":
        return None

    wc = WordCloud(width=800,height=500,min_font_size=10,background_color='white',colormap='Dark2')
    df_wc = wc.generate(text)
    return df_wc

def most_common_words(selected_user,df):

    stop_words = load_stop_words()

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    temp = df[df['user'] != 'group_notification']

    words = []

    for message in temp['message']:
        for word in remove_media_tag(message).lower().split():
            if word not in stop_words and not word.startswith('http'):
                words.append(word)

    most_common_df = pd.DataFrame(Counter(words).most_common(20))
    return most_common_df


def emoji_helper(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    emojis = []

    # emoji_list keeps emojis with skin colour or joined emojis in one piece
    for message in df['message'].dropna():
        for item in emoji.emoji_list(message):
            emojis.append(item['emoji'])

    emoji_df = pd.DataFrame(
        Counter(emojis).most_common(),
        columns=['emoji', 'count']
    )

    return emoji_df



def monthly_timeline(selected_user,df):

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    timeline = df.groupby(['year', 'month_num', 'month']).count()['message'].reset_index()

    time = []
    for i in range(timeline.shape[0]):
        time.append(timeline['month'][i] + "-" + str(timeline['year'][i]))

    timeline['time'] = time

    return timeline

def daily_timeline(selected_user,df):

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    daily_timeline = df.groupby('only_date').count()['message'].reset_index()

    return daily_timeline

def week_activity_map(selected_user,df):

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    return df['day_name'].value_counts()

def month_activity_map(selected_user,df):

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    return df['month'].value_counts()

def activity_heatmap(selected_user,df):

    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    user_heatmap = df.pivot_table(index='day_name', columns='period', values='message', aggfunc='count').fillna(0)

    # keep days in week order and hours in clock order, with all 24 hours
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    user_heatmap = user_heatmap.reindex([d for d in days if d in user_heatmap.index])

    all_periods = ['00-01'] + [f"{h}-{h + 1}" for h in range(1, 23)] + ['23-00']
    user_heatmap = user_heatmap.reindex(columns=all_periods, fill_value=0)
    user_heatmap.columns = [hour_text(h) for h in range(24)]

    return user_heatmap
