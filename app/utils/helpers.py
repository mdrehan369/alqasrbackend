from random import randint

CHARS = "abcdefghiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"


def generate_random_string(n: int = 15):
    st = ""
    for i in range(n):
        st += CHARS[randint(0, len(CHARS) - 1)]

    return st
