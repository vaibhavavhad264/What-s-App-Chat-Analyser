import re
import pandas as pd

# WhatsApp saves the date in two different styles:
#   iPhone  :  [8/3/26, 8:47:12 PM] Name: message
#   Android :  8/3/26, 8:47:12 PM - Name: message
IPHONE_PATTERN = r'^\[\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}:\d{2}\s?[APap][Mm]\]\s'
ANDROID_PATTERN = r'^\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}:\d{2}\s?[APap][Mm]\s-\s'

# also matches "This message was deleted by admin ..."
DELETED_STARTS = ("This message was deleted", "You deleted this message")


def find_event(user, message):
    """Tell what kind of line this is: message, deleted, joined, added, left, removed or other."""
    text = message.strip()

    # lines written by a person
    if user != "group_notification":
        if text.startswith(DELETED_STARTS):
            return "deleted"
        if text == "<message_history_notice message>":
            return "other"
        return "message"

    # lines written by WhatsApp itself
    if "joined" in text:
        return "joined"
    if " added " in text:
        return "added"
    if text.endswith(" left"):
        return "left"
    if " removed " in text:
        return "removed"
    return "other"


def count_people(event, message):
    """How many people are in this line (used for joined / added / left / removed)."""
    text = message.strip()
    if event == "added":
        names = text.split(" added ", 1)[1]
        return len(re.split(r',\s*and\s+|,\s*|\s+and\s+', names))
    if event in ("joined", "left", "removed"):
        return 1
    return 0


def preprocess(data):
    data = data.replace("\u202f", " ").replace("\u200e", "").replace("\r\n", "\n")

    # choose the style used in this file
    if re.search(IPHONE_PATTERN, data, flags=re.M):
        pattern = IPHONE_PATTERN
    else:
        pattern = ANDROID_PATTERN

    messages = re.split(pattern, data, flags=re.M)[1:]
    dates = re.findall(pattern, data, flags=re.M)
    df = pd.DataFrame({"user_message": messages, "message_date": dates})

    df["date"] = pd.to_datetime(
        df["message_date"].str.strip("[] -"),
        format="%m/%d/%y, %I:%M:%S %p",
        errors="coerce"
    )
    df.drop(columns=["message_date"], inplace=True)
    df = df.dropna(subset=["date"]).reset_index(drop=True)

    messages = []
    users = []

    for message in df["user_message"]:
        if message.startswith("- "):  # iPhone style system line
            users.append("group_notification")
            messages.append(message[2:])
        else:
            entry = re.split(r'^([^:\n]+?):\s', message, maxsplit=1)
            if entry[1:]:  # ['', 'Sender', 'text']
                users.append(entry[1])
                messages.append(entry[2])
            else:  # system line, no sender
                users.append("group_notification")
                messages.append(entry[0])

    df["user"] = users
    df["message"] = messages
    df.drop(columns=["user_message"], inplace=True)

    # what kind of line is it
    df["event"] = [find_event(u, m) for u, m in zip(df["user"], df["message"])]
    df["people"] = [count_people(e, m) for e, m in zip(df["event"], df["message"])]

    df['year'] = df['date'].dt.year
    df['month_num'] = df['date'].dt.month
    df['month'] = df['date'].dt.month_name()
    df['day'] = df['date'].dt.day
    df['only_date'] = df['date'].dt.date
    df['day_name'] = df['date'].dt.day_name()
    df['hour'] = df['date'].dt.hour
    df['minute'] = df['date'].dt.minute
    df['second'] = df['date'].dt.second

    period = []

    for hour in df['hour']:
        if hour == 23:
            period.append("23-00")
        elif hour == 0:
            period.append("00-01")
        else:
            period.append(f"{hour}-{hour + 1}")

    df['period'] = period

    return df
