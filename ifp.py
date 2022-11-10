import struct

from dataclasses import dataclass
from mathutils import Quaternion, Vector
from os import SEEK_CUR


def read_int16(fd, num=1, en='<'):
    res = struct.unpack('%s%dh' % (en, num), fd.read(2 * num))
    return res if num > 1 else res[0]


def read_uint32(fd, num=1, en='<'):
    res = struct.unpack('%s%dI' % (en, num), fd.read(4 * num))
    return res if num > 1 else res[0]


def read_float32(fd, num=1, en='<'):
    res = struct.unpack('%s%df' % (en, num), fd.read(4 * num))
    return res if num > 1 else res[0]


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


def write_val(fd, vals, t, en='<'):
    data = vals if hasattr(vals, '__len__') else (vals, )
    data = struct.pack('%s%d%s' % (en, len(data), t), *data)
    fd.write(data)


def write_uint16(fd, vals, en='<'):
    write_val(fd, vals, 'h', en)


def write_uint32(fd, vals, en='<'):
    write_val(fd, vals, 'I', en)


def write_float32(fd, vals, en='<'):
    write_val(fd, vals, 'f', en)


def write_str(fd, val, max_len):
    fd.write(val.encode())
    fd.write(b'\x00' * (max_len - len(val)))


@dataclass
class Keyframe:
    time: float
    pos: Vector
    rot: Quaternion
    scl: Vector


@dataclass
class Bone:
    name: str
    keyframe_type: str
    use_bone_id: bool
    bone_id: int
    sibling_x: int
    sibling_y: int
    keyframes: []


@dataclass
class Animation:
    name: str
    bones: []


@dataclass
class IfpData:
    name: str
    animations: []


class Anp3Bone(Bone):
    def get_keyframes_size(self):
        s = 16 if self.keyframe_type[2] == 'T' else 10
        return len(self.keyframes) * s

    def get_size(self):
        return 36 + self.get_keyframes_size()

    @classmethod
    def read(cls, fd):
        name = read_str(fd, 24)
        keyframe_type, keyframes_num, bone_id = read_uint32(fd, 3)
        keyframe_type = 'KRT0' if keyframe_type == 4 else 'KR00'

        keyframes = []
        for _ in range(keyframes_num):
            qx, qy, qz, qw, time = read_int16(fd, 5)
            px, py, pz = read_int16(fd, 3) if keyframe_type[2] == 'T' else (0, 0, 0)
            kf = Keyframe(
                time,
                Vector((px/1024.0, py/1024.0, pz/1024.0)),
                Quaternion((qw/4096.0, qx/4096.0, qy/4096.0, qz/4096.0)),
                Vector((1, 1, 1))
            )
            keyframes.append(kf)

        return cls(name, keyframe_type, True, bone_id, 0, 0, keyframes)

    def write(self, fd):
        keyframe_type = 4 if self.keyframe_type == 'KRT0' else 3

        write_str(fd, self.name, 24)
        write_uint32(fd, (keyframe_type, len(self.keyframes), self.bone_id))

        for kf in self.keyframes:
            qx = int(kf.rot.x*4096.0)
            qy = int(kf.rot.y*4096.0)
            qz = int(kf.rot.z*4096.0)
            qw = int(kf.rot.w*4096.0)
            write_uint16(fd, (qx, qy, qz, qw, int(kf.time)))

            if keyframe_type == 4:
                px = int(kf.pos.x*1024.0)
                py = int(kf.pos.y*1024.0)
                pz = int(kf.pos.z*1024.0)
                write_uint16(fd, (px, py, pz))


class Anp3Animation(Animation):
    @staticmethod
    def get_bone_class():
        return Anp3Bone

    def get_size(self):
        return 36 + sum(b.get_size() for b in self.bones)

    @classmethod
    def read(cls, fd):
        name = read_str(fd, 24)
        bones_num, keyframes_size, unk = read_uint32(fd, 3)
        bones = [Anp3Bone.read(fd) for _ in range(bones_num)]
        return cls(name, bones)

    def write(self, fd):
        keyframes_size = sum(b.get_keyframes_size() for b in self.bones)

        write_str(fd, self.name, 24)
        write_uint32(fd, (len(self.bones), keyframes_size, 1))
        for b in self.bones:
            b.write(fd)


class Anp3(IfpData):
    @staticmethod
    def get_animation_class():
        return Anp3Animation

    @classmethod
    def read(cls, fd):
        size = read_uint32(fd)
        name = read_str(fd, 24)
        animations_num = read_uint32(fd)
        animations = [cls.get_animation_class().read(fd) for _ in range(animations_num)]
        return cls(name, animations)

    def write(self, fd):
        size = 28 + sum(a.get_size() for a in self.animations)
        write_uint32(fd, size)
        write_str(fd, self.name, 24)
        write_uint32(fd, len(self.animations))
        for a in self.animations:
            a.write(fd)


class AnpkBone(Bone):
    def get_keyframes_size(self):
        s = 20
        if self.keyframe_type[2] == 'T':
            s += 12
        if self.keyframe_type[3] == 'S':
            s += 12
        return len(self.keyframes) * s

    def get_size(self):
        if self.use_bone_id:
            anim_len = 44
        else:
            anim_len = 48
        return self.get_keyframes_size() + anim_len + 24

    @classmethod
    def read(cls, fd):
        fd.seek(4, SEEK_CUR) # CPAN
        bone_len = read_uint32(fd)
        fd.seek(4, SEEK_CUR) # ANIM
        anim_len = read_uint32(fd)
        name = read_str(fd, 28)
        keyframes_num = read_uint32(fd)
        fd.seek(8, SEEK_CUR) # unk

        if anim_len == 44:
            bone_id = read_uint32(fd)
            sibling_x, sibling_y = 0, 0
            use_bone_id = True
        else:
            bone_id = 0
            sibling_x, sibling_y = read_uint32(fd, 2)
            use_bone_id = False

        keyframe_type = read_str(fd, 4)
        keyframes_len = read_uint32(fd)

        keyframes = []
        for _ in range(keyframes_num):
            qx, qy, qz, qw = read_float32(fd, 4)
            px, py, pz = read_float32(fd, 3) if keyframe_type[2] == 'T' else (0, 0, 0)
            sx, sy, sz = read_float32(fd, 3) if keyframe_type[3] == 'S' else (1, 1, 1)
            time = read_float32(fd)

            rot = Quaternion((qw, qx, qy, qz))
            rot.conjugate()

            kf = Keyframe(
                time,
                Vector((px, py, pz)),
                rot,
                Vector((sx, sy, sz)),
            )
            keyframes.append(kf)

        return cls(name, keyframe_type, use_bone_id, bone_id, sibling_x, sibling_y, keyframes)

    def write(self, fd):
        keyframes_num = len(self.keyframes)
        if self.use_bone_id:
            anim_len = 44
        else:
            anim_len = 48

        keyframes_len = self.get_keyframes_size()
        bone_len = keyframes_len + anim_len + 16

        write_str(fd, 'CPAN', 4)
        write_uint32(fd, bone_len)
        write_str(fd, 'ANIM', 4)
        write_uint32(fd, anim_len)
        write_str(fd, self.name, 28)
        write_uint32(fd, (keyframes_num, 0, keyframes_num - 1))

        if self.use_bone_id:
            write_uint32(fd, self.bone_id)
        else:
            write_uint32(fd, (self.sibling_x, self.sibling_y))

        write_str(fd, self.keyframe_type, 4)
        write_uint32(fd, keyframes_len)

        for kf in self.keyframes:
            rot = kf.rot.copy()
            rot.conjugate()
            write_float32(fd, (rot.x, rot.y, rot.z, rot.w))

            if self.keyframe_type[2] == 'T':
                write_float32(fd, kf.pos)

            if self.keyframe_type[3] == 'S':
                write_float32(fd, kf.scl)

            write_float32(fd, kf.time)


class AnpkAnimation(Animation):
    def get_bone_class():
        return AnpkBone

    def get_size(self):
        name_len = len(self.name) + 1
        name_align_len = (4 - name_len % 4) % 4
        return 32 + name_len + name_align_len + sum(b.get_size() for b in self.bones)

    @classmethod
    def read(cls, fd):
        fd.seek(4, SEEK_CUR) # NAME
        name_len = read_uint32(fd)
        name = read_str(fd, name_len)
        fd.seek((4 - name_len % 4) % 4, SEEK_CUR)
        fd.seek(4, SEEK_CUR) # DGAN
        animation_size = read_uint32(fd)
        fd.seek(4, SEEK_CUR) # INFO
        unk_size, bones_num = read_uint32(fd, 2)
        fd.seek(unk_size - 4, SEEK_CUR)
        bones = [AnpkBone.read(fd) for _ in range(bones_num)]
        return cls(name, bones)

    def write(self, fd):
        name_len = len(self.name) + 1
        animation_size = 16 + sum(b.get_size() for b in self.bones)

        write_str(fd, 'NAME', 4)
        write_uint32(fd, name_len)
        write_str(fd, self.name, name_len + (4 - name_len % 4) % 4)
        write_str(fd, 'DGAN', 4)
        write_uint32(fd, animation_size)
        write_str(fd, 'INFO', 4)
        write_uint32(fd, (8, len(self.bones), 0))
        for b in self.bones:
            b.write(fd)


class Anpk(IfpData):
    @staticmethod
    def get_animation_class():
        return AnpkAnimation

    @classmethod
    def read(cls, fd):
        size = read_uint32(fd)
        fd.seek(4, SEEK_CUR) # INFO
        info_len, animations_num = read_uint32(fd, 2)
        name = read_str(fd, info_len - 4)
        fd.seek((4 - info_len % 4) % 4, SEEK_CUR)

        animations = [cls.get_animation_class().read(fd) for _ in range(animations_num)]
        return cls(name, animations)

    def write(self, fd):
        name_len = len(self.name) + 1
        info_len = name_len + 4
        name_align_len = (4 - name_len % 4) % 4
        size = 12 + name_len + name_align_len + sum(a.get_size() for a in self.animations)

        write_uint32(fd, size)
        write_str(fd, 'INFO', 4)
        write_uint32(fd, (info_len, len(self.animations)))
        write_str(fd, self.name, name_len + name_align_len)
        for a in self.animations:
            a.write(fd)


ANIM_CLASSES = {
    'ANP3': Anp3,
    'ANPK': Anpk,
}


@dataclass
class Ifp:
    version: str
    data: object

    @classmethod
    def read(cls, fd):
        version = read_str(fd, 4)

        anim_cls = ANIM_CLASSES.get(version)
        if not anim_cls:
            raise Exception('Unknown IFP version')

        data = anim_cls.read(fd)
        return cls(version, data)

    def write(self, fd):
        write_str(fd, self.version, 4)
        self.data.write(fd)
        fd.write(b'\x00' * (2048 - (fd.tell() % 2048)))

    @classmethod
    def load(cls, filepath):
        with open(filepath, 'rb') as fd:
            return cls.read(fd)

    def save(self, filepath):
        with open(filepath, 'wb') as fd:
            return self.write(fd)
