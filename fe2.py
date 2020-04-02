#!/bin/env python3
import click
import struct


HARDCODED_KEY = 0x12350fd4


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


def decrypt_file(src_file: str, dst_file):
    encrypted = open(src_file, mode='rb').read()

    with open(dst_file, mode='wb') as decrypted:
        # Magic == 00 11
        #
        if struct.unpack('>H', encrypted[0: 2])[0] != 0x11:
            print('Incorrect magic for a Frontier Elite 2 savegame.')
        data, key = crypt(encrypted[2:-4], HARDCODED_KEY, decrypt=True)
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
@click.option('--decrypt', '-d', 'action', flag_value='decrypt', default=True, help='Decrypt the savegame to clear binary.')
@click.option('--encrypt', '-e', 'action', flag_value='encrypt', help='Encrypt back a savegame.')
@click.argument('srcfile', type=click.Path())
@click.argument('dstfile', type=click.Path())
def main(action: str, srcfile: str, dstfile: str):
    if action == 'decrypt':
        decrypt_file(srcfile, dstfile)
    elif action == 'encrypt':
        encrypt_file(srcfile, dstfile)


if __name__ == '__main__':
    main()
