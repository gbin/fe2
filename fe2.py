#!/bin/env python3
import click
import struct

HARDCODED_KEY = 0x12350fd4


def error(phase:str, input_offset:int, input_byte:int, output_offset:int, output_byte:int):
    print(f'Phase {phase}: input {input_offset}(0x{input_offset:x}):{input_byte:02x} should '
          f'be {output_offset}(0x{output_offset:x}):{output_byte:02x}')
    exit(-1)


def rol(val, r_bits, max_bits=32):
    return (val << r_bits % max_bits) & (2 ** max_bits - 1) | (
            (val & (2 ** max_bits - 1)) >> (max_bits - (r_bits % max_bits)))


def crypt(src: bytes, key: int, decrypt: bool) -> (bytearray, int):
    output = bytearray()
    for i in range(0, len(src), 2):
        w, = struct.unpack('>H', src[i: i + 2])
        d = (w ^ key) & 0xffff
        output.extend(struct.pack('>H', d))

        key_comp = d if decrypt else w

        # emulates the extend to 32bits for signed ints.
        if key_comp >= 0x8000:
            key_comp |= 0xffff0000
        key += key_comp
        key &= 0xffffffff
        key = rol(key, 1)
    return output, key


def _decomp(output: bytearray, src, i, final_length, ground_truth: bytearray = None) -> int:
    init_length = len(output)
    while len(output) - init_length < final_length and i < len(src):
        output.append(src[i])
        output_offset = len(output)-1
        if ground_truth and output[-1] != ground_truth[output_offset]:
            error(f'decomp copy on length {final_length:x}', i, src[i], output_offset, ground_truth[output_offset])
        if src[i] == 0:
            i += 1
            loop_for = src[i]
            i += 1
            if loop_for < 0:
                continue
            for j in range(loop_for):
                output.append(0)
                # This is another inconsistency of the original code
                # if len(output) - init_length == final_length:
                #     print(f'overshoot by {loop_for - j}')
                #     break
                output_offset = len(output)-1
                if ground_truth and output[-1] != ground_truth[output_offset]:
                    error('0 expansion on length {final_length:x}', i, 0, output_offset, ground_truth[output_offset])
            continue
        i += 1
    # Checking for that reveals bugs in the initial code
    # if len(output) - init_length != final_length:
    #     print(f'Error incorrect final produced length should be {final_length} and it is {len(output) - init_length}')
    return i


def decompress(src: bytearray, ground_truth: bytearray = None) -> bytearray:
    output = bytearray()
    i = 0
    i = _decomp(output, src, i, 0x80ed, ground_truth=ground_truth)
    for j in range(0x20B):
        output.append(src[i])
        i += 1
        output_offset = len(output)-1
        if ground_truth and output[-1] != ground_truth[output_offset]:
            error('0x20B copy', i, src[i], output_offset, ground_truth[output_offset])
    i -= 1  # This feels like a bug in the original code.

    _decomp(output, src, i, 0x3661, ground_truth=ground_truth)
    return output


def decrypt_file(src_file: str, dst_file: str = None, testmode: bool = False):
    encrypted = open(src_file, mode='rb').read()

    with open(dst_file, mode='rb' if testmode else 'wb') as decrypted:
        # Magic == 00 11
        #
        if struct.unpack('>H', encrypted[0: 2])[0] != 0x11:
            print('Incorrect magic for a Frontier Elite 2 savegame.')
        data, key = crypt(encrypted[2:-4], HARDCODED_KEY, decrypt=True)
        if testmode:
            with open('temp.decrypted', mode='wb') as decompressed:
                decompressed.write(data)
        data = decompress(data, decrypted.read() if testmode else None)
        if not testmode:
            decrypted.write(data)

        # Footer == Last Key
        last_value = struct.unpack('>I', encrypted[-4:])[0]
        if last_value != key:
            print(f'Incorrect footer. {key:x} instead of {last_value:x}')


def encrypt_file(src_file: str, dst_file: str):
    src = open(src_file, mode='rb').read()

    with open(dst_file, mode='wb') as encrypted:
        # Magic == 00 11
        #
        encrypted.write(struct.pack('>H', 0x11))
        data, key = crypt(src, HARDCODED_KEY, decrypt=False)
        encrypted.write(data)

        # Footer == Last Key
        encrypted.write(struct.pack('>I', key))


@click.command()
@click.option('--decrypt', '-d', 'action', flag_value='decrypt', default=True,
              help='Decrypt the savegame to clear binary.')
@click.option('--encrypt', '-e', 'action', flag_value='encrypt', help='Encrypt back a savegame.')
@click.option('--test', '-t', 'action', flag_value='test', help='Test the encryption decryption with a ground truth from amiSGE.')
@click.argument('srcfile', type=click.Path())
@click.argument('dstfile', type=click.Path())
def main(action: str, srcfile: str, dstfile: str):
    if action == 'decrypt':
        decrypt_file(srcfile, dstfile)
    elif action == 'encrypt':
        encrypt_file(srcfile, dstfile)
    elif action == 'test':
        decrypt_file(srcfile, dstfile, testmode=True)


if __name__ == '__main__':
    main()
