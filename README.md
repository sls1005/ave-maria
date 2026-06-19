This is a project inspired by the [Ave Maria cipher](https://en.wikipedia.org/wiki/Polygraphia_(book)), a form of steganography invented by Johannes Trithemius. The goal of this project is to implement a similar form of steganography using text substitution to convert binary data into normal-looking text.

The code list is replaceable, therefore not limited to Latin words. You can use words from English or any other language to make it look like normal text, and because it is replaceable, you can also write your own code lists.

### Usage

#### Encode

```sh
python ave-maria.py encode -c code_lists/codes-en.txt -o encoded.txt input.txt
```

Where `code_lists/codes-en.txt` is the path to the code list file.

The input file can be a binary file containing any data.


#### Decode

```sh
python ave-maria.py decode -c code_lists/codes-en.txt -o decoded.txt input.txt
```

#### Code list

The code list is a list of words and phrases to use as codes. The sender and the receiver must have the same code list file (and a compatible implementation of this program) in order to communicate with each other.

You can write your own code list, or use one from the `code_lists` directory:

* [`code_lists/codes-en.txt`](code_lists/codes-en.txt) includes words used in modern daily life, conversations and messages.

The code list file should be a text file containing words or phrases separated by line separators. The encoding can be configured using CLI options, and whether there is a byte-order mark or not, when the encoding is UTF-8, is not important. (A compatible implementation must handle this correctly and must not require the byte-order mark to be or not be present when the encoding is UTF-8.)

The number of codes in a code list is unlimited, as long as it is equal to or greater than 256. One code must not be identical to another in the code list, and must not be a pure combination of any number of other codes from the same list, or it would be impossible to decode.

### Warning

Please note that steganography is different from encryption, and substitution ciphers aren't secure by modern standards (which is why this documentation used ‘encode’/‘decode’ instead of ‘encrypt’/‘decrypt’). Even if you change the code list, it is still not secure as a cipher. The goal of steganography isn't to make your message undecipherable but to make people not to know to decipher it (or intercept your letters, etc.).

To use this more securely, you should first encrypt your message with a modern cryptographic algorithm utilizing a symmetric/asymmetric key before applying steganography, and it would be even better if you could compress the message or data and salt it before applying encryption and steganography.