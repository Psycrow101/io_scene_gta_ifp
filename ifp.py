import struct

from dataclasses import dataclass
from mathutils import Quaternion, Vector
from os import SEEK_CUR


def read_int16(fd, num=1, en='<'):
    res = struct.unpack('%s%dh' % (en, num), fd.read(2 * num))
    return res if num > 1 else res[0]


def write_uint16(fd, vals, en='<'):
    data = vals if hasattr(vals, '__len__') else (vals, )
    data = struct.pack('%s%dh' % (en, len(data)), *data)
    fd.write(data)


def read_uint32(fd, num=1, en='<'):
    res = struct.unpack('%s%dI' % (en, num), fd.read(4 * num))
    return res if num > 1 else res[0]


def write_uint32(fd, vals, en='<'):
    data = vals if hasattr(vals, '__len__') else (vals, )
    data = struct.pack('%s%dI' % (en, len(data)), *data)
    fd.write(data)


def read_str(fd, max_len):
    n, res = 0, ''
    while n < max_len:
        b = fd.read(1)
        n += 1
        if b == b'\x00':
            break
        res += b.decode()

    fd.seek(max_len - n, SEEK_CUR)
    return res


def write_str(fd, val, max_len):
    fd.write(val.encode())
    fd.write(b'\x00' * (max_len - len(val)))


@dataclass
class Keyframe:
    time: int
    pos: Vector
    rot: Quaternion


@dataclass
class Bone:
    name: str
    keyframe_type: int
    bone_id: int
    keyframes: []

    def get_keyframes_size(self):
        s = 16 if self.keyframe_type == 4 else 10
        return len(self.keyframes) * s

    def get_size(self):
        return 36 + self.get_keyframes_size()

    @classmethod
    def read(cls, fd):
        name = fd.read(24).replace(b'\x00', b'').decode()
        keyframe_type, keyframes_num, bone_id = read_uint32(fd, 3)

        keyframes = []
        for _ in range(keyframes_num):
            qx, qy, qz, qw, time = read_int16(fd, 5)
            px, py, pz = read_int16(fd, 3) if keyframe_type == 4 else (0, 0, 0)
            kf = Keyframe(
                time,
                Vector((px/1024.0, py/1024.0, pz/1024.0)),
                Quaternion((qw/4096.0, qx/4096.0, qy/4096.0, qz/4096.0)),
            )
            keyframes.append(kf)

        return cls(name, keyframe_type, bone_id, keyframes)

    def write(self, fd):
        write_str(fd, self.name, 24)
        write_uint32(fd, (self.keyframe_type, len(self.keyframes), self.bone_id))

        for kf in self.keyframes:
            qx = int(kf.rot.x*4096.0)
            qy = int(kf.rot.y*4096.0)
            qz = int(kf.rot.z*4096.0)
            qw = int(kf.rot.w*4096.0)
            write_uint16(fd, (qx, qy, qz, qw, kf.time))

            if self.keyframe_type == 4:
                px = int(kf.pos.x*1024.0)
                py = int(kf.pos.y*1024.0)
                pz = int(kf.pos.z*1024.0)
                write_uint16(fd, (px, py, pz))


@dataclass
class Anp3Animation:
    name: str
    bones: []

    def get_size(self):
        return 36 + sum(b.get_size() for b in self.bones)

    @classmethod
    def read(cls, fd):
        name = read_str(fd, 24)
        bones_num, keyframes_size, unk = read_uint32(fd, 3)
        bones = [Bone.read(fd) for _ in range(bones_num)]
        return cls(name, bones)

    def write(self, fd):
        keyframes_size = sum(b.get_keyframes_size() for b in self.bones)

        write_str(fd, self.name, 24)
        write_uint32(fd, (len(self.bones), keyframes_size, 1))
        for b in self.bones:
            b.write(fd)


ANIM_CLASSES = {
    'ANP3': Anp3Animation,
}


@dataclass
class Ifp:
    name: str
    version: str
    animations: []

    @classmethod
    def read(cls, fd):
        version = read_str(fd, 4)

        anim_cls = ANIM_CLASSES.get(version)
        if not anim_cls:
            raise Exception('Unknown IFP version')

        size = read_uint32(fd)
        name = fd.read(24).replace(b'\x00', b'').decode()
        animations_num = read_uint32(fd)
        animations = [anim_cls.read(fd) for _ in range(animations_num)]

        return cls(name, version, animations)

    def write(self, fd):
        size = 4 + sum(a.get_size() for a in self.animations)

        write_str(fd, self.version, 4)
        write_uint32(fd, size)
        write_str(fd, self.name, 24)
        write_uint32(fd, len(self.animations))
        for a in self.animations:
            a.write(fd)

    @classmethod
    def load(cls, filepath):
        with open(filepath, 'rb') as fd:
            return cls.read(fd)

    def save(self, filepath):
        with open(filepath, 'wb') as fd:
            return self.write(fd)
