from flask import Flask, render_template, request, jsonify
import json
import random
import os
import re

app = Flask(__name__)
app.secret_key = "super_secret_key"

DIALOG_PATH = os.path.join(os.path.dirname(__file__), 'dialog_flow.json')
with open(DIALOG_PATH, 'r', encoding='utf-8') as f:
    DIALOG_FLOW = json.load(f)

EMOTION_ICONS = {
    "sad": "😢", "happy": "😄", "stressed": "😰", "anxious": "😟", "angry": "😡",
    "lonely": "🥺", "bored": "😴", "grateful": "🙏", "excited": "🤩", "tired": "😴",
    "unmotivated": "😶", "focused": "🧘", "frustrated": "😤", "unheard": "👂",
    "neutral": "🙂", "confused": "🤔", "overwhelmed": "😩", "hopeless": "😞",
    "worried": "😟", "energetic": "⚡", "creative": "🎨", "unwell": "🤒",
    "pain": "🤕", "nervous": "😬", "insecure": "😳", "proud": "🏅",
    "embarrassed": "😳", "nostalgic": "🕰️", "motivated": "🚀", "inspired": "🌟",
    "jealous": "😒", "rejected": "😔", "burnt out": "🔥", "peaceful": "🕊️",
    "content": "😊", "surprised": "😮", "curious": "🧐"
}

ACTIVITY_KEYWORDS = [
    "breathing exercise", "creative prompt", "mood journaling", "mini workout",
    "gratitude practice", "music suggestion", "fact", "quote", "definition"
]

def preprocess(text):
    return text.lower().strip()

def get_random_from_list(lst):
    return random.choice(lst) if lst else ""

def append_emotion_emoji(response, emotion):
    emoji = EMOTION_ICONS.get(emotion)
    if not emoji:
        return response
        
    if response.endswith(emoji):
        response = response[:-len(emoji)]

    return response.strip() + " " + emoji
    
def get_fact():
    return get_random_from_list(DIALOG_FLOW.get('knowledge_base', {}).get('facts', []))

def get_quote():
    return get_random_from_list(DIALOG_FLOW.get('knowledge_base', {}).get('quotes', []))

def get_definition(word=None):
    defs = DIALOG_FLOW.get('knowledge_base', {}).get('definitions', {})
    if word:
        key = word.strip().lower()
        if key in defs:
            return f"{key.capitalize()}: {defs[key]}"
        else:
            for k, v in defs.items():
                if key in k:
                    return f"{k.capitalize()}: {v}"
            return f"Sorry, I don't have a definition for '{word}'."
    return get_random_from_list([f"{k.capitalize()}: {v}" for k, v in defs.items()])

def get_activity(name=None):
    acts = DIALOG_FLOW.get('activities', {})
    if name and name in acts:
        return acts[name]
    return get_random_from_list(list(acts.values()))

def match_trigger(user_input):
    for trigger, data in DIALOG_FLOW['triggers'].items():
        if trigger in user_input:
            return data
    for greet in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]:
        if greet in user_input:
            return {
                "emotion": "neutral",
                "response": "Hello! How are you feeling today?",
                "followup": []
            }
    return None

def parse_activity_from_message(user_msg_clean):
    pattern = r"^(tell me|give me)\s+(.+)$"
    m = re.match(pattern, user_msg_clean)
    if m:
        activity_candidate = m.group(2).strip()
        for act in ACTIVITY_KEYWORDS:
            if activity_candidate == act or activity_candidate in act or act in activity_candidate:
                return act
    return None

def extract_definition_word(msg):
    patterns = [
        r"definition of ([\w\s\-']+)",
        r"define ([\w\s\-']+)",
        r"give me definition of ([\w\s\-']+)",
        r"tell me definition of ([\w\s\-']+)",
        r"what is the definition of ([\w\s\-']+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, msg)
        if match:
            return match.group(1).strip()
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get('message', '')
    user_msg_clean = preprocess(user_msg)

    def_word = extract_definition_word(user_msg_clean)
    if def_word:
        response = get_definition(def_word)
        emotion = "curious"
        followups = []
        response = append_emotion_emoji(response, emotion)
        return jsonify({
            'response': response,
            'emotion': emotion,
            'followups': followups
        })

    activity_key = parse_activity_from_message(user_msg_clean)
    if activity_key:
        if activity_key == "fact":
            response = get_fact()
            emotion = "curious"
        elif activity_key == "quote":
            response = get_quote()
            emotion = "motivated"
        elif activity_key == "definition":
            response = get_definition()
            emotion = "curious"
        else:
            response = get_activity(activity_key)
            emotion = "neutral"
        followups = []
        response = append_emotion_emoji(response, emotion)
        return jsonify({
            'response': response,
            'emotion': emotion,
            'followups': followups
        })

    data = match_trigger(user_msg_clean)

    if data:
        response = data.get('response', '')
        emotion = data.get('emotion', 'neutral')
        followups = data.get('followup', [])
    elif user_msg_clean in DIALOG_FLOW.get('followups', {}):
        if user_msg_clean in ["fact", "fun fact"]:
            response = get_fact()
            emotion = "curious"
            followups = []
        elif user_msg_clean in ["quote"]:
            response = get_quote()
            emotion = "motivated"
            followups = []
        elif user_msg_clean in ["definition", "define"]:
            tokens = user_msg_clean.split()
            word = tokens[-1] if len(tokens) > 1 else None
            response = get_definition(word)
            emotion = "curious"
            followups = []
        elif user_msg_clean in DIALOG_FLOW.get('activities', {}):
            response = get_activity(user_msg_clean)
            emotion = "neutral"
            followups = []
        else:
            response = DIALOG_FLOW['followups'][user_msg_clean]
            emotion = "neutral"
            followups = []
    elif user_msg_clean.startswith("define "):
        word = user_msg_clean.replace("define ", "")
        response = get_definition(word)
        emotion = "curious"
        followups = []
    elif user_msg_clean in DIALOG_FLOW.get('activities', {}):
        response = get_activity(user_msg_clean)
        emotion = "neutral"
        followups = []
    elif user_msg_clean in ["fact", "fun fact"]:
        response = get_fact()
        emotion = "curious"
        followups = []
    elif user_msg_clean == "quote":
        response = get_quote()
        emotion = "motivated"
        followups = []
    else:
        def_data = DIALOG_FLOW['default']
        response = def_data['response']
        emotion = def_data['emotion']
        followups = def_data.get('followup', [])

    response = append_emotion_emoji(response, emotion)

    return jsonify({
        'response': response,
        'emotion': emotion,
        'followups': followups
    })

if __name__ == '__main__':
    app.run(debug=True)
