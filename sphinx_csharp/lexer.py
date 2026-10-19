""" C# signature tokenizer """

from typing import NamedTuple

# Punctuation of more than one character
# Note: The parser joins operators such as >> from single characters, as > also closes generic arguments.
PUNCTUATION = ('::', '=>')


class Token(NamedTuple):
    # A word, such as a name, keyword or number, a string or char literal, or punctuation
    kind: str
    text: str
    # The span of the token in the signature
    start: int
    end: int


def is_word_char(char: str) -> bool:
    """ Whether a character can be part of a name, keyword or number """
    return char.isalnum() or char == '_'


def literal_end(sig: str, start: int) -> int:
    """ The end of the string or char literal at start, or of the signature if the literal is unterminated """
    # A verbatim string such as @"C:\" escapes a quote by doubling it
    verbatim = sig[start] == '@'
    quote = sig[start + verbatim]
    i = start + verbatim + 1
    while i < len(sig):
        if sig[i] == quote:
            if not (verbatim and sig.startswith(quote, i + 1)):
                return i + 1
            i += 1
        elif sig[i] == '\\' and not verbatim:
            i += 1
        i += 1
    return len(sig)


def tokenize(sig: str) -> list[Token]:
    """ Split a signature into tokens, leaving out whitespace """
    tokens = []
    i = 0
    while i < len(sig):
        char = sig[i]
        if char.isspace():
            i += 1
            continue
        if char in '"\'' or sig.startswith('@"', i):
            kind, end = 'literal', literal_end(sig, i)
        elif is_word_char(char) or char == '@' and i + 1 < len(sig) and is_word_char(sig[i + 1]):
            kind, end = 'word', i + 1
            while end < len(sig) and is_word_char(sig[end]):
                end += 1
        else:
            kind, end = 'punct', i + (2 if sig.startswith(PUNCTUATION, i) else 1)
        tokens.append(Token(kind, sig[i:end], i, end))
        i = end
    return tokens
