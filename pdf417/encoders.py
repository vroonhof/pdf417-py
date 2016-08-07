from builtins import range
from future.utils import iteritems
from pdf417.data import CHARACTERS_LOOKUP, SWITCH_CODES, Submode
from pdf417.util import switch_base, chunks


class Encoder(object):

    def can_encode(self, char):
        """Checks whether the given character can be encoded using this encoder."""
        raise NotImplementedError()

    def get_switch_code(self, data):
        """Returns the switch code word for the encoding mode implemented by the encoder."""
        raise NotImplementedError()

    def encode(self, data, add_switch_code):
        """Encodes a string into codewords."""
        raise NotImplementedError()


class ByteEncoder(Encoder):
    """Encodes data into code words using the Byte compaction mode.

    Can encode: ASCII 0 to 255
    Rate compaction: 1.2 byte per code word
    """

    # Code word used to switch to Byte mode
    SWITCH_CODE_WORD = 901

    # Alternate code word used to switch to Byte mode; used when number of bytes
    # to encode is divisible by 6.
    SWITCH_CODE_WORD_ALT = 924

    def can_encode(self, char):
        """Byte encoder can encode any one character"""
        return True

    def get_switch_code(self, data):
        return self.SWITCH_CODE_WORD_ALT if len(data) % 6 == 0 \
            else self.SWITCH_CODE_WORD

    def encode(self, data, add_switch_code):
        code_words = []

        if add_switch_code:
            code_words.append(self.get_switch_code(data))

        # Encode in chunks of 6 bytes
        for chunk in chunks(data, size=6):
            code_words.extend(self.encode_chunk(chunk))

        return code_words

    def encode_chunk(self, chunk):
        return self.encode_full_chunk(chunk) if len(chunk) == 6 \
            else self.encode_incomplete_chunk(chunk)

    def encode_full_chunk(self, chunk):
        """Encodes a chunk consisting of exactly 6 bytes.

        The chunk is encoded to 5 code words by changing the base from 256 to 900.
        """
        digits = [ord(i) for i in chunk]
        return switch_base(digits, 256, 900)

    def encode_incomplete_chunk(self, chunk):
        """Encodes a chunk consisting of less than 6 bytes.

        The chunk is encoded to the same number of code words leaving the base unchanged.
        """
        return [ord(i) for i in chunk]


class TextEncoder(Encoder):
    """Encodes data into code words using the Text compaction mode.

    Can encode: ASCII 9, 10, 13 and 32-126
    Rate compaction: 2 bytes per code word
    """

    # Code word used to switch to Text mode.
    SWITCH_CODE_WORD = 900

    # By default, encoding starts with uppercase submode
    DEFAULT_SUBMODE = Submode.UPPER

    # Since each code word consists of 2 characters, a padding value is
    # needed when encoding a single character. 29 is used as padding because
    # it's a switch in all 4 submodes, and doesn't add any data.
    PADDING_INTERIM_CODE = 29

    def get_switch_code(self, data):
        return self.SWITCH_CODE_WORD

    def can_encode(self, char):
        return char in CHARACTERS_LOOKUP

    def exists_in_submode(self, char, submode):
        return char in CHARACTERS_LOOKUP and \
               submode in CHARACTERS_LOOKUP[char]

    def get_submode(self, char):
        if char not in CHARACTERS_LOOKUP:
            raise ValueError("Cannot encode char: " + char)

        submodes = CHARACTERS_LOOKUP[char].keys()

        preference = [Submode.LOWER, Submode.UPPER, Submode.MIXED, Submode.PUNCT]

        for submode in preference:
            if submode in submodes:
                return submode

        raise ValueError("Cannot encode char: " + char)

    def encode_interim(self, data):
        submode = self.DEFAULT_SUBMODE

        codes = []

        for char in data:
            # Do we need to switch submode?
            if not self.exists_in_submode(char, submode):
                prev_submode = submode
                submode = self.get_submode(char)

                switch_codes = SWITCH_CODES[prev_submode][submode]
                codes.extend(switch_codes)

            codes.append(CHARACTERS_LOOKUP[char][submode])

        return codes

    def encode(self, data, add_switch_code):
        interim_codes = self.encode_interim(data)
        code_words = [self.SWITCH_CODE_WORD] if add_switch_code else []
        code_words.extend([self.encode_chunk(chunk) for chunk in chunks(interim_codes, 2)])

        return code_words

    def encode_chunk(self, chunk):
        if len(chunk) == 1:
            chunk.append(self.PADDING_INTERIM_CODE)

        return 30 * chunk[0] + chunk[1]
