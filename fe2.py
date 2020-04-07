#!/bin/env python3
import ctypes
import datetime
from typing import List

import click
import struct
from io import StringIO

from attr import dataclass

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


def _decompress(output: bytearray, src: bytearray, i : int, final_length : int, ground_truth: bytearray = None) -> int:
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


def _compress(output: bytearray, src: bytearray, src_offset: int, length: int, ground_truth: bytearray = None) -> bytearray:
    i = src_offset
    while i - src_offset < length:
        b = src[i]
        i += 1
        output.append(b)
        if ground_truth and output[-1] != ground_truth[len(output)-1]:
            error(f'copy compress at {length:x}', src_offset+i-1, b, len(output)-1, ground_truth[len(output)-1])

        if b == 0:
            count = 0
            while src[i] == 0 and count <= 254:
                i += 1
                if i - src_offset == length + 2:  # This is a bug in the original code off by 2
                    break
                count += 1
            output.append(count)

            if ground_truth and output[-1] != ground_truth[len(output)-1]:
                error(f'zero compress at {length:x}', src_offset+i-1, count, len(output)-1, ground_truth[len(output)-1])


def compress(src: bytearray, ground_truth: bytearray = None) -> bytearray:
    output = bytearray()
    _compress(output, src, 0, 0x80ed, ground_truth=ground_truth)
    i = 0x80ee
    for j in range(0x20C): # off by ones EVERYWHERE!!!
        output.append(src[i])
        i += 1
        output_offset = len(output)-1
        if ground_truth and output[-1] != ground_truth[output_offset]:
            error('0x20B copy', i, src[i], output_offset, ground_truth[output_offset])

    _compress(output, src, i, 0x3661, ground_truth=ground_truth)
    if len(output) % 2:
        output.append(0xe5)  # yeah this crap just takes a random byte from memory
    return output


def decompress(src: bytearray, ground_truth: bytearray = None) -> bytearray:
    output = bytearray()
    i = 0
    i = _decompress(output, src, i, 0x80ed, ground_truth=ground_truth)
    for j in range(0x20B):
        output.append(src[i])
        i += 1
        output_offset = len(output)-1
        if ground_truth and output[-1] != ground_truth[output_offset]:
            error('0x20B copy', i, src[i], output_offset, ground_truth[output_offset])
    i -= 1  # This feels like a bug in the original code.

    _decompress(output, src, i, 0x3661, ground_truth=ground_truth)
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


def encrypt_file(src_file: str, dst_file: str, testmode: bool = False):
    src = open(src_file, mode='rb').read()

    with open(dst_file, mode='rb' if testmode else 'wb') as encrypted:
        # Magic == 00 11
        #
        if not testmode:
            encrypted.write(struct.pack('>H', 0x11))
        data = compress(src, encrypted.read() if testmode else None)
        data, key = crypt(data, HARDCODED_KEY, decrypt=False)
        if not testmode:
            encrypted.write(data)

            # Footer == Last Key
            encrypted.write(struct.pack('>I', key))


OBJ_TYPES_NAMES = {0x02: 'Ship In Hyperspace',
                   0x0a: 'Kind Of Ship In Hyperspace',
                   0x0f: 'Starport',
                   0x1d: 'Star/Planet',
                   0x1f: 'Space Station',
                   0x4e: 'Ship in current system',
                   0x4f: 'Active ship in current system'}


E1_NAMES = {0x01: "Laser Cooling Booster",
            0x02: "Auto Refueler",
            0x04: "Military Cameras",
            }

E2_NAMES = {0x01: "Cargo Bay Life Support",
            0x02: "Cargo Bay Life Support",
            0x04: "Scanner",
            0x08: "Normal ECM",
            0x10: "Fuel Scoop",
            0x20: "Autopilot",
            0x40: "Radar Mapper",
            0x80: "Naval ECM",
            }

E3_NAMES = {0x01: "Hyperspace Cloud Analyser",
            0x02: "Fighter Launch Device",
            0x04: "Energy Bomb",
            0x08: "Escape Capsule",
            0x10: "Energy Booster Unit",
            0x20: "Cargo Scoop Conversion",
            0x40: "Atmospheric Shielding",
            }

DRIVE_TYPE = {0x0: "None",
              0x1: "Interplanetary",
              0x2: "Hyperdrive Class 1",
              0x3: "Hyperdrive Class 2",
              0x4: "Hyperdrive Class 3",
              0x5: "Hyperdrive Class 4",
              0x6: "Hyperdrive Class 5",
              0x7: "Hyperdrive Class 6",
              0x8: "Hyperdrive Class 7",
              0x9: "Hyperdrive Class 8",
              0xa: "Military Class 1",
              0xb: "Military Class 2",
              0xc: "Military Class 3",
              0xd: "Military Class 4",
              }

@dataclass
class GameObject:
    _all_objs: List["GameObject"]
    id: int
    tid: int
    name: str = ''
    speed: float = 0.0
    bounty: int = 0
    unknown_counter1: int = 0
    unknown_counter2: int = 0
    shooting_started: bool = False
    relative: int = 0
    main_forward_acc: int = 0
    main_reverse_acc: int = 0
    equipment1: int = 0
    equipment2: int = 0
    equipment3: int = 0
    drive_type: int = 0
    guns: List[int] = 0

    @staticmethod
    def get_type(tid: int) -> str:
        return OBJ_TYPES_NAMES.get(tid, "Unknown " + str(tid))

    def __str__(self):
        result = StringIO()
        print(f'id {self.id:x}:', file=result)
        print(f'  type: {self.get_type(self.tid)}', file=result)
        print(f'  designation: {self.name}', file=result)
        if self.relative:
            obj_relative = self._all_objs[self.relative]
            print(f'  near: {self.get_type(obj_relative.tid)} {obj_relative.name}', file=result)
        if self.bounty:
            print(f'  attached bounty: ${self.bounty}', file=result)
        if self.speed:
            print(f'  speed: {self.speed} m.s⁻¹', file=result)
        if self.main_forward_acc:
            print(f'  forward acceleration: {self.main_forward_acc} m.s⁻²', file=result)
        if self.main_reverse_acc:
            print(f'  reverse acceleration: {self.main_reverse_acc} m.s⁻²', file=result)

        # print(f'  equipment1:{self.equipment1:08b}', file=result)
        # print(f'  equipment2:{self.equipment2:08b}', file=result)
        # print(f'  equipment3:{self.equipment3:08b}', file=result)

        equipment = [name for mask, name in E1_NAMES.items() if self.equipment1 & mask]
        equipment.extend([name for mask, name in E2_NAMES.items() if self.equipment2 & mask])
        equipment.extend([name for mask, name in E3_NAMES.items() if self.equipment3 & mask])
        if equipment:
            print(f'  equipment:', file=result)
            for eq in equipment:
                print(f'    - {eq}', file=result)
        if self.drive_type:
            print(f'  drive type: {DRIVE_TYPE[self.drive_type]}', file=result)

        if self.guns:
            print(f'  guns:', file=result)
            for position, value in zip(('front', 'back', 'top', 'bottom'), self.guns):
                print(f'    - {position}:{value}', file=result)
        return result.getvalue()


NAME_OFFSET = 0x3a
STR_MAXSIZE = 20
SPEED_OFFSET = 0x12
BOUNTY_OFFSET = 0x32
COUNTER1_OFFSET = 0x1a
COUNTER2_OFFSET = 0x1e
SHOOTING_STARTED = 0x5e
RELATIVE_OBJ_OFFSET = 0xa6
MAIN_FORWARD_ACCELERATION_OFFSET = 0xfc
MAIN_REVERSE_ACCELERATION_OFFSET = 0xfe
E1_OFFSET = 0x100
E2_OFFSET = 0x103   # doc is wrong
E3_OFFSET = 0x102
DRIVE_TYPE_OFFSET = 0x108
GUN_MOUNTS_OFFSET = 0x109
GUN_FRONT_OFFSET = 0x10a
GUN_REAR_OFFSET = 0x10b
GUN_TOP_OFFSET = 0x10c
GUN_BOTTOM_OFFSET = 0x10d

OWN_SHIP_ID_OFFSET = 0x8892

MONEY_OFFSET = 0x88D2    # 0x83cc for real
CARGO_SPACE_OFFSET = 0x88d6
FUEL_OFFSET = 0x88da
DAY_OFFSET = 0x8804
TARGET_OFFSET = 0x88B8

ELITE_RATING = {0x0000: "Harmless",
                0x0004: "Mostly Harmless",
                0x0008: "Poor",
                0x0010: "Below Average",
                0x0020: "Average",
                0x0040: "Above Average",
                0x0080: "Competent",
                0x03e8: "Dangerous",
                0x0bb8: "Deadly",
                0x1770: "ELITE",
                }

IMPERIAL_TITLE = {0x0000: "Outsider",
                  0x0002: "Serf",
                  0x0010: "Master",
                  0x0052: "Sir",
                  0x0100: "Squire",
                  0x0240: "Lord",
                  0x0510: "Baron",
                  0x0962: "Viscount",
                  0x1000: "Count",
                  0x19a2: "Earl",
                  0x2710: "Marquis",
                  0x3932: "Duke",
                  0x5100: "Prince",
                  }

FEDERAL_RANK = {0x0000: "None",
                0x0002: "Private",
                0x0010: "Corporal",
                0x0052: "Sergeant",
                0x0100: "Sergeant-Major",
                0x0240: "Major",
                0x0510: "Colonel",
                0x0962: "Lieutenant",
                0x1000: "Lieutenant Commander",
                0x19a2: "Captain",
                0x2710: "Commodore",
                0x3932: "Rear Admiral",
                0x5100: "Admiral",
                }

KILLS_OFFSET = 0x892D
FEDERAL_PTS_OFFSET = 0x8930
IMPERIAL_PTS_OFFSET = 0x8932

def decode_str(src: bytes, offset) -> str:
    raw_name = struct.unpack(f'{STR_MAXSIZE}s', src[offset:offset + STR_MAXSIZE])[0]
    return ctypes.create_string_buffer(raw_name).value.decode()  # clean up the C string


def decode_word(src: bytes, offset) -> int:
    return struct.unpack(f'>H', src[offset:offset+2])[0]

def decode_long(src: bytes, offset) -> int:
    return struct.unpack(f'>i', src[offset:offset+4])[0]

def inspect(src_file: str):
    src = open(src_file, mode='rb').read()
    base_offset = -0x506  # offset between the PC and Amiga version

    print(f'Player:')

    nb_days = decode_long(src, base_offset + DAY_OFFSET)

    # this is a weird date calculation ignoring a lot of rules.
    date = datetime.date(int(nb_days / 365.25), 1, 1) + datetime.timedelta(days=nb_days % 365.25)
    own_ship = src[base_offset+OWN_SHIP_ID_OFFSET]-1

    federal_pts = decode_word(src, base_offset + FEDERAL_PTS_OFFSET)
    rank = ''
    for pts_for_rank, name in FEDERAL_RANK.items():
        if federal_pts >= pts_for_rank:
            rank = name
        else:
            break
    imperial_pts = decode_word(src, base_offset + IMPERIAL_PTS_OFFSET)
    title = ''
    for pts_for_title, name in IMPERIAL_TITLE.items():
        if imperial_pts >= pts_for_title:
            title = name
        else:
            break
    kills = decode_word(src, base_offset + KILLS_OFFSET)
    rating = ''
    for kills_for_rating, name in ELITE_RATING.items():
        if kills >= kills_for_rating:
            rating = name
        else:
            break

    print(f'  Date: {date}')
    print(f'  Money: ¢{decode_long(src, base_offset + MONEY_OFFSET)/10}')
    print(f'  Federal Rank: {rank} with {federal_pts} points')
    print(f'  Imperial Title: {title} with {imperial_pts} points')
    print(f'  Elite rating: {rating} with {kills} kills')
    print(f'  Ship ID: {own_ship:x}')
    print(f'  Selected target ID: {src[base_offset+OWN_SHIP_ID_OFFSET]-1:x}')
    print(f'  Cargo Space: {decode_word(src, base_offset + CARGO_SPACE_OFFSET)}t [0x{base_offset + CARGO_SPACE_OFFSET:x}]')
    print(f'  Fuel: {decode_word(src, base_offset + FUEL_OFFSET)}t')
    print()
    print(f'Game Objects:')

    objects = []
    for i in range(0x73):
        obj = GameObject(objects, i, src[i])
        objects.append(obj)
        if obj.tid != 0:
            base_offset = 0x11e * i + 0x72
            obj.name = decode_str(src, base_offset + NAME_OFFSET)
            obj.speed = decode_word(src, base_offset + SPEED_OFFSET) / 10.0
            obj.bounty = decode_word(src, base_offset + BOUNTY_OFFSET)
            obj.unknown_counter1 = decode_word(src, base_offset + COUNTER1_OFFSET)
            obj.unknown_counter2 = decode_word(src, base_offset + COUNTER2_OFFSET)
            obj.shooting_started = src[base_offset + SHOOTING_STARTED] == 0x0a
            obj.relative = src[base_offset + RELATIVE_OBJ_OFFSET]
            obj.main_forward_acc = decode_word(src, base_offset + MAIN_FORWARD_ACCELERATION_OFFSET)
            obj.main_reverse_acc = decode_word(src, base_offset + MAIN_REVERSE_ACCELERATION_OFFSET)
            obj.equipment1 = src[base_offset + E1_OFFSET]
            obj.equipment2 = src[base_offset + E2_OFFSET]
            obj.equipment3 = src[base_offset + E3_OFFSET]
            obj.drive_type = src[base_offset + DRIVE_TYPE_OFFSET]
            obj.guns = [src[base_offset+GUN_FRONT_OFFSET+goff] for goff in range(src[base_offset+GUN_MOUNTS_OFFSET])]
    for i, obj in enumerate(objects):
        if obj.tid != 0:
            if i == own_ship:
                print(' vvvv This is your own ship vvvv ------------------------')
            print(obj)




@click.command()
@click.option('--decrypt', '-d', 'action', flag_value='decrypt', default=True,
              help='Decrypt the savegame to clear binary.')
@click.option('--encrypt', '-e', 'action', flag_value='encrypt', help='Encrypt back a savegame.')
@click.option('--inspect', '-i', 'action', flag_value='inspect', help='Inspect a decrypted savegame.')
@click.option('--testdec', '-t', 'action', flag_value='testdec', help='Test the decryption with a ground truth from amiSGE.')
@click.option('--testenc', '-T', 'action', flag_value='testenc', help='Test the encryption with a ground truth from amiSGE.')
@click.argument('srcfile', type=click.Path())
@click.argument('dstfile', type=click.Path(), required=False)
def main(action: str, srcfile: str, dstfile: str):
    if action == 'decrypt':
        decrypt_file(srcfile, dstfile)
    elif action == 'encrypt':
        encrypt_file(srcfile, dstfile)
    elif action == 'testdec':
        decrypt_file(srcfile, dstfile, testmode=True)
    elif action == 'testenc':
        encrypt_file(srcfile, dstfile, testmode=True)
    elif action == 'inspect':
        inspect(srcfile)


if __name__ == '__main__':
    main()
