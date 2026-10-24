import random

# Step 1: A list (Python's version of an array) of animal names
ANIMALS = [
    "elephant", "giraffe", "penguin", "dolphin", "kangaroo",
    "crocodile", "butterfly", "squirrel", "hedgehog", "cheetah",
    "zebra", "octopus", "flamingo", "gorilla", "tortoise",
]

MAX_WRONG = 6  # number of wrong guesses allowed


def pick_word():
    """Step 2: Choose a random animal from the list."""
    return random.choice(ANIMALS)


def show_progress(word, guessed):
    """Step 3: Show the word with blanks for letters not yet guessed."""
    return " ".join(letter if letter in guessed else "_" for letter in word)


def play():
    word = pick_word()
    guessed = set()   # all letters the player has tried
    wrong = 0

    print("Welcome to Hangman! Guess the animal.")

    # Step 4: Main game loop
    while wrong < MAX_WRONG:
        print("\n" + show_progress(word, guessed))
        print(f"Wrong guesses left: {MAX_WRONG - wrong}")
        print("Guessed so far:", " ".join(sorted(guessed)) or "none")

        # Step 5: Get and validate the player's guess
        guess = input("Enter a letter: ").strip().lower()

        if len(guess) != 1 or not guess.isalpha():
            print("Please enter a single letter.")
            continue
        if guess in guessed:
            print("You already tried that letter.")
            continue

        guessed.add(guess)

        # Step 6: Check the guess
        if guess in word:
            print("Good guess!")
        else:
            wrong += 1
            print("Nope, that letter is not in the word.")

        # Step 7: Check for a win
        if all(letter in guessed for letter in word):
            print(f"\nYou win! The animal was '{word}'.")
            return

    # Step 8: Out of guesses, the player loses
    print(f"\nGame over! The animal was '{word}'.")


if __name__ == "__main__":
    # Step 9: Let the player replay
    while True:
        play()
        again = input("\nPlay again? (y/n): ").strip().lower()
        if again != "y":
            print("Thanks for playing!")
            break
