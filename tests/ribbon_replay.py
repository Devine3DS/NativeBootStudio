"""Replay the native scalar ribbon generator, with explicit curve/API stubs.

This executes the original and patched instruction streams. It is not an Xbox
emulator: curve sampling, resource locks and register save helpers are stubbed.
The comparison covers all 780 output vertices, including native alpha/time math.
"""

import math
import struct
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN


def replay(image, ribbon_type, time, curve_rgb):
    decoder = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
    instructions = {}
    for lo, hi in [(0x1B2F8, 0x1BF1C), (0x58700, 0x587A0)]:
        for i in decoder.disasm(bytes(image[lo:hi]), 0x98000000 + lo):
            instructions[i.address] = (i.mnemonic, i.op_str.replace(" ", "").split(","))
    memory = {}
    regs = [0] * 32
    floats = [0.0] * 32
    bits = [None] * 32
    cr = {}
    lr = 0
    regs[1] = 0x100000
    regs[3] = 0x200000
    floats[1] = time

    def write(a, blob):
        for j, v in enumerate(blob):
            memory[(a + j) & 0xFFFFFFFF] = v

    def read(a, n):
        a &= 0xFFFFFFFF
        if 0x98000000 <= a and a + n <= 0x98000000 + len(image):
            return bytes(image[a - 0x98000000 : a - 0x98000000 + n])
        return bytes(memory.get((a + j) & 0xFFFFFFFF, 0) for j in range(n))

    def integer(s):
        return int(s, 0)

    def reg(s):
        return int(s[1:])

    def addr(s):
        imm, base = s[:-1].split("(")
        return (integer(imm) + regs[reg(base)]) & 0xFFFFFFFF

    def signed(v):
        return (v & 0xFFFFFFFF) - (0x100000000 if v & 0x80000000 else 0)

    def setf(index, value, single=False):
        floats[index] = struct.unpack(">f", struct.pack(">f", value))[0] if single else value
        bits[index] = None

    def wf(a, v):
        write(a, struct.pack(">f", v))

    write(regs[3] + 4, struct.pack(">I", 0x210000))
    write(regs[3] + 8, struct.pack(">I", ribbon_type & 0xFFFFFFFF))
    for index in range(6):
        wf(0x98077994 + 4 * index, math.sin(index * math.pi / 3))
        wf(0x980779AC + 4 * index, math.cos(index * math.pi / 3))
    # Runtime globals also have file-backed addresses. Explicit runtime writes
    # must take precedence over the initial bytes of the native image.
    native_read = read

    def read(a, n):
        a &= 0xFFFFFFFF
        if all((a + j) & 0xFFFFFFFF in memory for j in range(n)):
            return bytes(memory[(a + j) & 0xFFFFFFFF] for j in range(n))
        return native_read(a, n)

    pc = 0x9801B2F8
    steps = 0
    hits = {}
    while pc != 0x980439CC:
        steps += 1
        if steps > 150000:
            raise AssertionError("Native ribbon replay exceeded step limit")
        op, args = instructions[pc]
        nextpc = pc + 4
        hits[pc] = hits.get(pc, 0) + 1
        if op in ("li", "lis"):
            regs[reg(args[0])] = integer(args[1]) * (65536 if op == "lis" else 1)
        elif op == "mr":
            regs[reg(args[0])] = regs[reg(args[1])]
        elif op == "mflr":
            regs[reg(args[0])] = lr
        elif op == "addi":
            regs[reg(args[0])] = regs[reg(args[1])] + integer(args[2])
        elif op == "extsw":
            regs[reg(args[0])] = signed(regs[reg(args[1])])
        elif op == "clrlwi":
            regs[reg(args[0])] = regs[reg(args[1])] & ((1 << (32 - integer(args[2]))) - 1)
        elif op == "lwz":
            regs[reg(args[0])] = struct.unpack(">I", read(addr(args[1]), 4))[0]
        elif op in ("stw", "stwu", "stb", "std"):
            a = addr(args[1])
            v = regs[reg(args[0])]
            n = {"stw": 4, "stwu": 4, "stb": 1, "std": 8}[op]
            write(a, (v & ((1 << (n * 8)) - 1)).to_bytes(n, "big"))
            if op == "stwu":
                regs[reg(args[1].split("(")[1][:-1])] = a
        elif op == "lfs":
            setf(reg(args[0]), struct.unpack(">f", read(addr(args[1]), 4))[0])
        elif op == "lfd":
            index = reg(args[0])
            bits[index] = int.from_bytes(read(addr(args[1]), 8), "big")
            floats[index] = struct.unpack(">d", read(addr(args[1]), 8))[0]
        elif op in ("stfs", "stfsu"):
            a = addr(args[1])
            wf(a, floats[reg(args[0])])
            if op == "stfsu":
                regs[reg(args[1].split("(")[1][:-1])] = a
        elif op == "fcfid":
            v = bits[reg(args[1])]
            if v & (1 << 63):
                v -= 1 << 64
            setf(reg(args[0]), float(v))
        elif op in ("fmr", "frsp", "fneg"):
            v = floats[reg(args[1])]
            setf(reg(args[0]), -v if op == "fneg" else v, op == "frsp")
        elif op in ("fadds", "fsubs", "fmuls"):
            a, b = (floats[reg(s)] for s in args[1:])
            setf(reg(args[0]), a + b if op == "fadds" else a - b if op == "fsubs" else a * b, True)
        elif op in ("fmadds", "fmsubs", "fnmsubs"):
            a, c, b = (floats[reg(s)] for s in args[1:])
            v = a * c + b if op == "fmadds" else a * c - b
            setf(reg(args[0]), -v if op == "fnmsubs" else v, True)
        elif op in ("cmpwi", "cmplwi", "fcmpu"):
            key = integer(args[0][2:])
            a = floats[reg(args[1])] if op == "fcmpu" else regs[reg(args[1])]
            b = floats[reg(args[2])] if op == "fcmpu" else integer(args[2])
            if op == "cmpwi":
                a = signed(a)
            cr[key] = (a > b) - (a < b)
        elif op in ("blt", "ble", "bgt", "bge", "beq", "bne"):
            value = cr[integer(args[0][2:])]
            take = {
                "blt": value < 0,
                "ble": value <= 0,
                "bgt": value > 0,
                "bge": value >= 0,
                "beq": value == 0,
                "bne": value != 0,
            }[op]
            if take:
                nextpc = integer(args[1])
        elif op == "b":
            nextpc = integer(args[0])
        elif op == "bl":
            target = integer(args[0])
            lr = nextpc
            if target in (0x9804397C, 0x98043CC0, 0x98043D0C, 0x980164B8, 0x9802E800):
                pass
            elif target == 0x98015388:
                wf(regs[4], 0.0)
                wf(regs[5], 1.0)
            elif target == 0x9802F918:
                regs[3] = 0x300000
            elif target == 0x98015AF8:
                t = floats[1]
                wf(regs[5], 0.03)
                wf(regs[6], 0.02)
                for pointer, values in [
                    (regs[7], [*curve_rgb, 0.7]),
                    (regs[8], [t, 0.1 * math.sin(t), 0.1 * math.cos(t), 1]),
                    (regs[9], [1, 0, 0, 0]),
                    (regs[10], [0, 1, 0, 0]),
                    (struct.unpack(">I", read(regs[1] + 0x54, 4))[0], [0, 0, 1, 0]),
                ]:
                    for i, v in enumerate(values):
                        wf(pointer + 4 * i, v)
            else:
                raise AssertionError("Unknown native call " + hex(target))
        else:
            raise AssertionError("Unsupported native instruction " + op)
        pc = nextpc
    return read(0x300000, 0x5550), hits
