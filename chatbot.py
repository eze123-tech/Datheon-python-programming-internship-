import json
import re
import sys
from enum import Enum, auto
from pathlib import Path

FAQ_PATH = Path(__file__).with_name("sample_faq.json")

ANSWER_THRESHOLD = 0.5    # confident match: answer directly
SUGGEST_THRESHOLD = 0.25  # weak match: ask "did you mean ...?"

# ---------- Regex patterns ----------
EXIT_RE = re.compile(r"^(bye|goodbye|exit|quit)(\s+(now|please|bot))?[\s!.]*$")
YES_RE = re.compile(r"^(y|yes|yeah|yep|yup|sure|ok|okay)(\s+please)?[\s!.]*$")
NO_RE = re.compile(
    r"^(n|no|nope|nah|nothing|that's all|thats all|that is all|"
    r"i'm good|im good|all good)[\s!.]*$"
)
THANKS_RE = re.compile(r"\b(thanks|thank you|thx|cheers)\b")
HELP_RE = re.compile(r"^(help|menu|topics)\b|\bwhat can (you|i) (do|ask)\b")

# ---------- Keyword normalization ----------
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "do", "does", "did",
    "i", "me", "my", "you", "your", "we", "our", "it", "to", "of", "for",
    "in", "on", "at", "and", "or", "how", "what", "when", "where", "which",
    "who", "will", "can", "could", "would", "should", "please", "tell",
    "about", "have", "has", "much", "there", "this", "that", "with", "if",
    "so", "then",
}

# Maps different ways of saying the same thing onto one keyword.
# Extend this as you add FAQs.
SYNONYMS = {
    "open": "hour", "opening": "hour", "close": "hour", "closing": "hour",
    "timing": "hour", "schedule": "hour",
    "upload": "submit", "send": "submit", "repo": "submit",
    "github": "submit", "link": "submit",
    "cert": "certificate", "certification": "certificate",
    "get": "receive",
}


def normalize(text):
    """Lowercase, trim, and collapse repeated whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def tokenize(text):
    """Extract keyword set: regex split, drop stopwords, light stemming, synonyms."""
    tokens = set()
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if word in STOPWORDS:
            continue
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]  # "hours" -> "hour"
        tokens.add(SYNONYMS.get(word, word))
    return tokens


class State(Enum):
    GREETING = auto()   # waiting for the first message
    IDENTIFY = auto()   # working out what the user wants
    RESOLVED = auto()   # answered; asking if there is anything else
    EXIT = auto()


class Chatbot:
    def __init__(self, faq_path=FAQ_PATH):
        data = self._load(faq_path)
        self.faqs = data.get("faqs", [])
        for faq in self.faqs:
            faq["_tokens"] = tokenize(faq["question"])

        greetings = sorted(
            (g.lower() for g in data.get("greetings", [])), key=len, reverse=True
        )
        self.greeting_re = (
            re.compile(r"^\s*(?:" + "|".join(map(re.escape, greetings)) + r")\b[\s,!.:-]*")
            if greetings else None
        )

        self.state = State.GREETING
        self.misses = 0      # consecutive unrecognized queries
        self.pending = None  # FAQ suggested via "did you mean ...?"

    @staticmethod
    def _load(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            sys.exit(f"Could not find FAQ file: {path}")
        except json.JSONDecodeError as err:
            sys.exit(f"FAQ file is not valid JSON: {err}")

    # ---------- Matching ----------
    def _best_match(self, text):
        user_tokens = tokenize(text)
        best, best_score, best_overlap = None, 0.0, 0
        for faq in self.faqs:
            overlap = len(user_tokens & faq["_tokens"])
            if not overlap:
                continue
            score = overlap / min(len(user_tokens), len(faq["_tokens"]))
            if (score, overlap) > (best_score, best_overlap):
                best, best_score, best_overlap = faq, score, overlap
        return best, best_score

    # ---------- Responses ----------
    def _resolve(self, faq):
        self.misses = 0
        self.state = State.RESOLVED
        return f"{faq['answer']}\n\nIs there anything else I can help with?"

    def _help_text(self):
        topics = "\n".join(f"  - {faq['question']}" for faq in self.faqs)
        return f"I can help with questions like:\n{topics}"

    def _fallback(self):
        self.misses += 1
        self.state = State.IDENTIFY
        if self.misses == 1:
            return ("I'm not sure I understood that. Could you rephrase it? "
                    "Type 'help' to see what I can answer.")
        return (f"Sorry, I still can't answer that.\n{self._help_text()}\n"
                "For anything else, please contact our support team directly.")

    def respond(self, raw):
        text = normalize(raw)
        if not text:
            return "I didn't catch that. What would you like to know?"

        # 1. Exit commands work in every state
        if EXIT_RE.match(text):
            self.state = State.EXIT
            return "Thanks for chatting. Goodbye!"

        # 2. Reply to a "did you mean ...?" suggestion
        if self.pending is not None:
            faq, self.pending = self.pending, None
            if YES_RE.match(text):
                return self._resolve(faq)
            if NO_RE.match(text):
                return ("No problem. Try rephrasing your question, "
                        "or type 'help' to see what I can answer.")

        # 3. After an answer, handle "anything else?" replies
        if self.state is State.RESOLVED:
            if NO_RE.match(text):
                self.state = State.EXIT
                return "Glad I could help. Goodbye!"
            if YES_RE.match(text):
                self.state = State.IDENTIFY
                return "Sure, what else would you like to know?"

        # 4. Greeting (optionally followed by a question: "hi, what are your hours?")
        prefix = ""
        match = self.greeting_re.match(text) if self.greeting_re else None
        if match:
            rest = text[match.end():].strip()
            if not rest:
                self.state = State.IDENTIFY
                return "Hello! How can I help you today? (Type 'help' to see topics.)"
            text, prefix = rest, "Hello! "

        # 5. Small intents
        if HELP_RE.search(text):
            self.state = State.IDENTIFY
            return self._help_text()
        if THANKS_RE.search(text):
            self.state = State.RESOLVED
            return "You're welcome! Is there anything else I can help with?"

        # 6. FAQ matching with confidence handling
        faq, score = self._best_match(text)
        if faq and score >= ANSWER_THRESHOLD:
            return prefix + self._resolve(faq)
        if faq and score >= SUGGEST_THRESHOLD:
            self.pending = faq
            self.misses = 0
            self.state = State.IDENTIFY
            return f'Did you mean: "{faq["question"]}" (yes/no)'

        return self._fallback()

    def run(self):
        print("Support Assistant (type 'bye', 'exit' or 'quit' to leave)\n")
        print("Bot: Hello! Ask me about hours, project submission, or certificates.\n")
        while self.state is not State.EXIT:
            try:
                user = input("You: ")
            except (EOFError, KeyboardInterrupt):
                print("\nBot: Goodbye!")
                break
            print(f"Bot: {self.respond(user)}\n")


if __name__ == "__main__":
    Chatbot().run()
