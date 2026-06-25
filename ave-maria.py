#!/usr/bin/env python
# Python 3+ is required.
# Version: 0.5.1-1
from sys import argv, stdin, stdout, stderr
from os import linesep
from os.path import exists
from secrets import randbelow
from collections import namedtuple

usage = '''
Usage: ave-maria.py [subcommamd] [options] [file]

Available subcommands & options:
      e, encode, -e, --encode                     Enable the encoder mode (default mode). Cannot be used with -d.

      d, decode, -d, --decode                     Enable the decoder mode. Cannot be used with -e.

      -h, --help                                  Show this help message and exit.

      -x, --extract, --extract-codes <file>       Make a code list by using words from <file>, which shuold be a text file containing a lot of words, e.g., an article.

      -c, -cl, --code-list <file>                 Specify the code list to be used. The code list should be a text file containing words or phrases separated by line separators (linebreaks). It must not contain a code that is identical to another code or is only a combination of other codes and/or the word-separator.

      -ws, -wsep, --word-separator <character>    Specify the word separator. (Default: space)

      -cenc, --code-list-encoding <encoding>      Specify the encoding of the code list file. (Default: the same as -ienc or -oenc if given, or UTF-8-sig if not)

      -ienc, --input-encoding <encoding>          Specify the encoding of the input file. (Default: the same as -cenc if given, or UTF-8-sig if not)

      -oenc, --output-encoding <encoding>         Specify the encoding of the output file. Not applicable for the decoder mode. (Default: the same as -cenc or -ienc if given, or UTF-8 without BOM if not given)

      -8bits, --8-bits                            Encode every 8 bits. The number of codes in the code list must be greater than or equal to 256.

      -4bits, --4-bits                            Encode every 4 bits. The number of codes in the code list must be greater than or equal to 16.

      -2bits, --2-bits                            Encode every 2 bits. The number of codes in the code list must be greater than or equal to 4.

      -1bit, --1-bit                              Encode every 1 bit. The number of codes in the code list must be greater than or equal to 2.

      --encoder-block-size <size>                 Specify the block size used of an encoder. <size> must be an integral number.

      --no-punc, --no-punctuation                 Do not add random punctuation.

      --no-capitalize, --no-capitalise            Do not randomly capitalize words (for encoding). Use case-sensitive mode (for decoding).

      --no-linebreaks                             Do not randomly add linebreaks.

      -o, --output <file>                         Specify the output file.

The argument [file] should be the name or path to the file that will be used as the input (the file containing the plaintext / encoded text, but not the code list, which is supplied using -c). Note that the input file doesn't need to be a text file. If the input file isn't given, this will read from stdin.

Example: ./ave-maria.py encode -c code_lists/codes-en.txt -o encoded.txt input.txt
'''

# Class
CodeValidationResult = namedtuple('CodeValidationResult', "error_code, double_check_set") # int, set[int]
EncoderConfiguration = namedtuple('EncoderConfiguration', "wordsep, block_size, capitalize, use_punctuation, add_linebreaks") # str, int, bool, bool, bool
DecoderConfiguration = namedtuple('DecoderConfiguration', "wordsep, case_sensitive") # str, bool

MODE_ENCODE = 1
MODE_DECODE = 2
MODE_EXTRACT = 3

def read_as_bytes(file, n = None):
    tmp = file.read() if n is None else file.read(n)
    return tmp.encode(file.encoding) if not('b' in file.mode) else tmp

def load_code_list(file_path, encoding = 'UTF-8-sig'):
    with open(file_path, 'r', encoding=encoding) as file:
        return list(filter(lambda s: s != '', map(lambda s: s.rstrip('\r\n'), file)))

def divide_bytes_into_bits(a, nbits): # bytes -> int, iterator
    n = 1 << nbits
    bit_count = 0
    for b in a:
        k = b
        while True:
            yield k % n
            k >>= nbits
            bit_count += nbits
            if bit_count >= 8:
                bit_count %= 8
                break

def encode(code_list, input_file=stdin, output_file=stdout, nbits = 8, config = EncoderConfiguration(wordsep = ' ', block_size=500, use_punctuation = True, capitalize = True, add_linebreaks = True)):
    if nbits not in (1, 2, 4, 8):
        raise ValueError("Encoding by {0} bits is not supported.".format(nbits))
    wordsep = config.wordsep
    block_size = config.block_size
    n_codes = len(code_list)
    random_counter_cap = 0
    random_counter_line = randbelow(block_size) if config.add_linebreaks else 0
    offset = 0
    should_add_wordsep = False
    buf = read_as_bytes(input_file, block_size)
    buf_len = len(buf)
    need_final_dot = (buf_len > 0)
    while buf_len > 0:
        for x in divide_bytes_into_bits(buf, nbits):
            if should_add_wordsep:
                output_file.write(wordsep)
            else:
                should_add_wordsep = True
            code = code_list[(x + offset) % n_codes]
            if config.capitalize or config.use_punctuation or config.add_linebreaks:
                if random_counter_cap == 0:
                    if config.capitalize:
                        code = code.capitalize()
                    random_counter_cap = randbelow(1000 + block_size)
                output_file.write(code)
                random_counter_cap >>= 1
                if config.use_punctuation or config.add_linebreaks:
                    if random_counter_cap == 0: # Check again because we changed its value.
                        r = randbelow(1000)
                        if r < 35:
                            output_file.write(',')
                            random_counter_cap = randbelow(1000 + block_size)
                        else:
                            p = '.'
                            if r < 37:
                                p = '!'
                            elif r < 50:
                                p = '?'
                            if config.use_punctuation:
                                output_file.write(p)
                            if config.add_linebreaks:
                                random_counter_line >>= 1
                                if random_counter_line == 0:
                                    output_file.write(linesep * 2)
                                    random_counter_line = randbelow(block_size)
                                    should_add_wordsep = False
            else:
                output_file.write(code)
            offset = (offset + 1) % n_codes
        buf = read_as_bytes(input_file, block_size)
        buf_len = len(buf)
    if need_final_dot and random_counter_cap > 0:
        output_file.write('.')

def decode(code_list, double_check_set=set(), input_file=stdin, output_file=stdout, nbits = 8, config = DecoderConfiguration(wordsep = ' ', case_sensitive = False)):
    from ahocorasick_rs import AhoCorasick, MatchKind # 3rd-party package
    ac = AhoCorasick(map(str.lower, code_list), matchkind=MatchKind.LeftmostLongest)
    if nbits not in (1, 2, 4, 8):
        raise ValueError("Decoding by {0} bits is not supported.".format(nbits))
    wordsep = config.wordsep
    n_codes = len(code_list)
    max_pos_nbit_num = (1 << nbits) - 1
    max_len = max(len(wordsep), max(map(len, code_list)))
    buf_size = max_len * max(10, n_codes)
    offset = 0
    buf_temp = input_file.read(buf_size)
    buf = buf_temp if config.case_sensitive else buf_temp.lower()
    flag_final = False
    bit_count = 0
    acc = 0
    while True:
        edge = 0
        for t in ac.find_matches_as_indexes(buf, overlapping=False):
            if (t[0] in double_check_set) and (t[2] > len(buf) - max_len) and (not flag_final):
                break
            else:
                k = (t[0] - offset) % n_codes
                if k > max_pos_nbit_num:
                    raise RuntimeError("An internal counter seems out of sync. It is likely that the code file or the input file is incomplete or corrupt, or a command flag or argument is different from the original configuration used for encoding the file.")
                acc += k << bit_count
                if acc > 255:
                    raise RuntimeError
                bit_count += nbits
                if bit_count >= 8:
                    output_file.write(bytes([acc]))
                    bit_count %= 8
                    acc = 0
                edge = t[2]
                offset = (offset + 1) % n_codes
        if flag_final:
            break
        else:
            buf = buf[edge:]
            buf_temp = input_file.read(buf_size)
            if len(buf_temp) == 0:
                flag_final = True
            else:
                buf += buf_temp if config.case_sensitive else buf_temp.lower()
    if bit_count != 0:
        raise RuntimeError("The ciphertext seems incomplete!")

def extract_codes(file): #-> list[str]
    code_list = []
    code_set = set()
    for line in file:
        for s in line.split():
            if s.isalpha():
                s_lower = s.lower()
                if s_lower not in code_set:
                    code_list.append(s_lower)
                    code_set.add(s_lower)
    return code_list

def validateCodes(code_list, nbits = 8, wordsep = ' ', case_sensitive = False): # side effect
    result_set = set()
    error_code = 0
    n_codes = len(code_list)
    code_list_local = code_list if case_sensitive else list(map(str.lower, code_list))
    codes_and_indices = dict(map(reversed, enumerate(code_list_local)))
    if wordsep not in codes_and_indices:
        codes_and_indices[wordsep] = -1
    min_codes_required = 2 ** nbits
    if n_codes < min_codes_required:
        stderr.write("[Error] There are only {0} codes in the code file. At least {1} are required.\n\n".format(n_codes, min_codes_required))
        error_code |= 1
    reported = set()
    for code_idx1, code1 in enumerate(code_list_local):
        if code_idx1 not in reported:
            for code_idx2, code2 in enumerate(code_list_local):
                if code_idx1 != code_idx2:
                    if code1 == code2:
                        error_code |= 2
                        stderr.write("[Error] It seems that code number {0} ('{1}') and {2} ('{3}') are identical!\n\n".format(code_idx1 + 1, code_list[code_idx1], code_idx2 + 1, code_list[code_idx2]))
                        reported |= {code_idx1, code_idx2}
                    elif code_idx1 not in result_set:
                        start_idx = code2.find(code1)
                        if (start_idx != -1) and (start_idx + len(code1) < len(code2)):
                            result_set.add(code_idx1)
        n = len(code1)
        if n > 0:
            records = {0 : -1} # key: index of code1; value: a key of records that is also a previous index of code1 used for slicing
            for i in range(1, n + 1):
                new_records = dict()
                for j in records.keys():
                    if j != 0 or i != n: # This order is intended.
                        # ^^^^^^^^^ avoid finding the code itself
                        s = code1[j:i]
                        if s in codes_and_indices: #O(1)
                            new_records[i] = j
                            break
                if len(new_records) > 0:
                    records.update(new_records)
            if n in records: # O(1)
                error_code |= 4 # This is error because a code shouldn't consist only of other codes.
                stderr.write("[Error] Code number {0}, '{1}', seems to consist of other code(s) in the code file only".format(code_idx1 + 1, code_list[code_idx1]))
                indices = []
                skip_indices = set([-1])
                i = n
                while i > 0:
                    j = records[i]
                    k = codes_and_indices[code1[j:i]]
                    if k not in skip_indices:
                        indices.append(k)
                        skip_indices.add(k) # We only need to report unique elements
                    i = j
                len_indices = len(indices)
                if len_indices > 0:
                    flag = False
                    use_and = (len_indices > 1)
                    for idx_idx, idx in enumerate(reversed(indices)):
                        if flag:
                            stderr.write(", and" if use_and and (idx_idx + 1 == len_indices) else ',')
                        else:
                            stderr.write(", including")
                            flag = True
                        stderr.write(" code number {0}, '{1}'".format(idx + 1, code_list[idx]))
                stderr.write(".\n\n")
    return CodeValidationResult(error_code, result_set)

def main():
    mode = None
    wordsep = ' '
    input_file_name = None
    output_file_name = None
    code_list_file_name = None
    raw_text_file_name = None
    code_list_file_encoding = None
    input_file_encoding = None
    output_file_encoding = None
    nbits = None
    encoder_block_size = 500
    should_extract_codes = False
    no_punctuation = False
    no_capitalize = False
    should_not_add_linebreaks = False
    mode_selected = False
    argc = len(argv)
    if argc == 1:
        exit(usage)
    i = 1
    while i < argc:
        a = argv[i]
        if (a in ('e', 'encode', '-e', '--encode')) and not mode_selected:
            if  mode == MODE_DECODE:
                stderr.write("[Error] The encoder mode and the decoder mode cannot be used at the same time.\n")
                exit()
            mode = MODE_ENCODE
            mode_selected = True
        elif (a in ('d', 'decode', '-d', '--decode')) and not mode_selected:
            if mode == MODE_ENCODE:
                stderr.write("[Error] The encoder mode and the decoder mode cannot be used at the same time.\n")
                exit()
            mode = MODE_DECODE
            mode_selected = True
        elif a in ('-x', '--extract', '--extract-codes'):
            i += 1
            if i == argc:
                stderr.write("[Error] <file> is expected after %s but is not given.\n" % a)
                exit()
            raw_text_file_name = argv[i]
            should_extract_codes = True
        elif a in ('-c', '-cl', '--code-list'):
            i += 1
            if i == argc:
                stderr.write("[Error] <file> is expected after %s but is not given.\n" % a)
                exit()
            code_list_file_name = argv[i]
        elif a in ('-ws', '-wsep', '--word-separator'):
            i += 1
            if i == argc:
                stderr.write("[Error] <character> is expected after %s but is not given.\n" % a)
                exit()
            wordsep = argv[i]
        elif a in ('-cenc', '--code-list-encoding'):
            i += 1
            if i == argc:
                stderr.write("[Error] <encoding> is expected after %s but is not given.\n" % a)
                exit()
            code_list_file_encoding = argv[i]
        elif a in ('-ienc', '--input-encoding'):
            i += 1
            if i == argc:
                stderr.write("[Error] <encoding> is expected after %s but is not given.\n" % a)
                exit()
            input_file_encoding = argv[i]
        elif a in ('-oenc', '--output-encoding'):
            i += 1
            if i == argc:
                stderr.write("[Error] <encoding> is expected after %s but is not given.\n" % a)
                exit()
            output_file_encoding = argv[i]
        elif a in ('-8bits', '--8-bits'):
            nbits = 8
        elif a in ('-4bits', '--4-bits'):
            nbits = 4
        elif a in ('-2bits', '--2-bits'):
            nbits = 2
        elif a in ('-1bit', '--1-bit'):
            nbits = 1
        elif a == '--encoder-block-size':
            i += 1
            if i == argc:
                stderr.write("[Error] <size> is expected after %s but is not given.\n" % a)
                exit()
            try:
                encoder_block_size = int(argv[i])
            except:
                stderr.write("[Error] <size> should be an integer.\n")
                exit()
        elif a in ('--no-punc', '--no-punctuation'):
            no_punctuation = True
        elif a in ('--no-capitalize', '--no-capitalise'):
            no_capitalize = True
        elif a == '--no-linebreaks':
            should_not_add_linebreaks = True
        elif a in ('-o', '--output'):
            i += 1
            if i == argc:
                stderr.write("[Error] <file> is expected after %s but is not given.\n" % a)
                exit()
            output_file_name = argv[i]
        else:
            input_file_name = a
        i += 1
    if should_extract_codes:
        if code_list_file_name is not None:
            stderr.write("[Error] You cannot use both the '--code-list' and '--extract-codes' options at the same time.\n")
            exit()
        if mode is None:
            mode = MODE_EXTRACT
    if mode == MODE_DECODE and output_file_name is None:
        stderr.write("[Error] Writing binary data to stdout is not supported. Please specify an output file.\n")
        exit()
    if code_list_file_encoding is None:
        if output_file_encoding is None:
            if (should_extract_codes or mode == MODE_DECODE) and (input_file_encoding is not None):
                code_list_file_encoding = output_file_encoding = input_file_encoding
            else:
                code_list_file_encoding = 'UTF-8-sig'
                output_file_encoding = 'UTF-8'
        else:
            code_list_file_encoding = output_file_encoding
    elif output_file_encoding is None:
        output_file_encoding = code_list_file_encoding
    if (should_extract_codes or mode == MODE_DECODE) and (input_file_encoding is None):
        input_file_encoding = code_list_file_encoding
    if input_file_name is not None:
        if input_file_name.startswith('-') and (not exists(input_file_name)):
            stderr.write("[Error] Unknown option: '%s'" % input_file_name)
            exit()
    code_list = []
    if should_extract_codes:
        with open(raw_text_file_name, 'r', encoding=input_file_encoding) as file:
            code_list = extract_codes(file)
        if mode == MODE_EXTRACT:
            output_file = stdout if output_file_name is None else open(output_file_name, 'w', encoding=output_file_encoding)
            for code in code_list:
                output_file.write(code + linesep)
            if output_file is not stdout:
                output_file.close()
            exit()
    elif code_list_file_name is None:
        stderr.write("[Error] No code list file is specified.\n")
        exit()
    else:
        code_list = load_code_list(code_list_file_name, code_list_file_encoding)
    if nbits is None:
        nbits = 1
        for k in (8, 4, 2):
            if len(code_list) >= (1 << k):
                nbits = k
                break
    err_code, double_check_set = validateCodes(code_list, nbits=nbits, wordsep=wordsep, case_sensitive=no_capitalize)
    if err_code != 0:
        stderr.write("It seems that the code file is problematic and cannot be used.\n")
        exit()
    if mode is None:
        mode = MODE_ENCODE
    if mode == MODE_ENCODE:
        input_file = stdin if input_file_name is None else open(input_file_name, 'rb')
        output_file = stdout if output_file_name is None else open(output_file_name, 'w', encoding=output_file_encoding)
        encode(code_list, input_file, output_file, nbits, EncoderConfiguration(wordsep=wordsep, block_size=encoder_block_size, use_punctuation=not(no_punctuation), capitalize=not(no_capitalize), add_linebreaks=not(should_not_add_linebreaks)))
        if input_file is not stdin:
            input_file.close()
        if output_file is not stdout:
            output_file.close()
    elif mode == MODE_DECODE:
        input_file = stdin if input_file_name is None else open(input_file_name, 'r', encoding=input_file_encoding)
        output_file = stdout if output_file_name is None else open(output_file_name, 'wb')
        decode(code_list, double_check_set, input_file, output_file, nbits, DecoderConfiguration(wordsep=wordsep, case_sensitive=no_capitalize))
        if input_file is not stdin:
            input_file.close()
        if output_file is not stdout:
            output_file.close()
    print("") # for linebreak

main()