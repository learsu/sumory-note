#!/usr/bin/python
# Public Domain
# Original author: ArtForz
# Twisted integration: slush
# Twisted removed: lqs

import struct
import socket
import binascii
import time
import sys
import random
import cStringIO
import hashlib

from util import *

MY_VERSION = 31402
MY_SUBVERSION = ".4"

class CAddress(object):
    def __init__(self):
        self.nTime = 0
        self.nServices = 1
        self.pchReserved = "\x00" * 10 + "\xff" * 2
        self.ip = "0.0.0.0"
        self.port = 0
    def deserialize(self, f):
        #self.nTime = struct.unpack("<I", f.read(4))[0]
        self.nServices = struct.unpack("<Q", f.read(8))[0]
        self.pchReserved = f.read(12)
        self.ip = socket.inet_ntoa(f.read(4))
        self.port = struct.unpack(">H", f.read(2))[0]
    def serialize(self):
        r = ""
        #r += struct.pack("<I", self.nTime)
        r += struct.pack("<Q", self.nServices)
        r += self.pchReserved
        r += socket.inet_aton(self.ip)
        r += struct.pack(">H", self.port)
        return r
    def __repr__(self):
        return "CAddress(nServices=%i ip=%s port=%i)" % (self.nServices, self.ip, self.port)

class CInv(object):
    typemap = {
        0: "Error",
        1: "TX",
        2: "Block"}
    def __init__(self):
        self.type = 0
        self.hash = 0L
    def deserialize(self, f):
        self.type = struct.unpack("<i", f.read(4))[0]
        self.hash = deser_uint256(f)
    def serialize(self):
        r = ""
        r += struct.pack("<i", self.type)
        r += ser_uint256(self.hash)
        return r
    def __repr__(self):
        return "CInv(type=%s hash=%064x)" % (self.typemap[self.type], self.hash)

class CBlockLocator(object):
    def __init__(self):
        self.nVersion = MY_VERSION
        self.vHave = []
    def deserialize(self, f):
        self.nVersion = struct.unpack("<i", f.read(4))[0]
        self.vHave = deser_uint256_vector(f)
    def serialize(self):
        r = ""
        r += struct.pack("<i", self.nVersion)
        r += ser_uint256_vector(self.vHave)
        return r
    def __repr__(self):
        return "CBlockLocator(nVersion=%i vHave=%s)" % (self.nVersion, repr(self.vHave))

class COutPoint(object):
    def __init__(self):
        self.hash = 0
        self.n = 0
    def deserialize(self, f):
        self.hash = deser_uint256(f)
        self.n = struct.unpack("<I", f.read(4))[0]
    def serialize(self):
        r = ""
        r += ser_uint256(self.hash)
        r += struct.pack("<I", self.n)
        return r
    def __repr__(self):
        return "COutPoint(hash=%064x n=%i)" % (self.hash, self.n)

class CTxIn(object):
    def __init__(self):
        self.prevout = COutPoint()
        self.scriptSig = ""
        self.nSequence = 0
    def deserialize(self, f):
        self.prevout = COutPoint()
        self.prevout.deserialize(f)
        self.scriptSig = deser_string(f)
        self.nSequence = struct.unpack("<I", f.read(4))[0]
    def serialize(self):
        r = ""
        r += self.prevout.serialize()
        r += ser_string(self.scriptSig)
        r += struct.pack("<I", self.nSequence)
        return r
    def __repr__(self):
        return "CTxIn(prevout=%s scriptSig=%s nSequence=%i)" % (repr(self.prevout), binascii.hexlify(self.scriptSig), self.nSequence)

class CTxOut(object):
    def __init__(self):
        self.nValue = 0
        self.scriptPubKey = ""
    def deserialize(self, f):
        self.nValue = struct.unpack("<q", f.read(8))[0]
        self.scriptPubKey = deser_string(f)
    def serialize(self):
        r = ""
        r += struct.pack("<q", self.nValue)
        r += ser_string(self.scriptPubKey)
        return r
    def __repr__(self):
        return "CTxOut(nValue=%i.%08i scriptPubKey=%s)" % (self.nValue // 100000000, self.nValue % 100000000, binascii.hexlify(self.scriptPubKey))

class CTransaction(object):
    def __init__(self):
        self.nVersion = 1
        self.vin = []
        self.vout = []
        self.nLockTime = 0
        self.sha256 = None
    def deserialize(self, f):
        self.nVersion = struct.unpack("<i", f.read(4))[0]
        self.vin = deser_vector(f, CTxIn)
        self.vout = deser_vector(f, CTxOut)
        self.nLockTime = struct.unpack("<I", f.read(4))[0]
        self.sha256 = None
    def serialize(self):
        r = ""
        r += struct.pack("<i", self.nVersion)
        r += ser_vector(self.vin)
        r += ser_vector(self.vout)
        r += struct.pack("<I", self.nLockTime)
        return r
    
    def calc_sha256(self):
        if self.sha256 is None:
            self.sha256 = uint256_from_str(hashlib.sha256(hashlib.sha256(self.serialize()).digest()).digest())
        return self.sha256
    
    def is_valid(self):
        self.calc_sha256()
        for tout in self.vout:
            if tout.nValue < 0 or tout.nValue > 21000000L * 100000000L:
                return False
        return True
    def __repr__(self):
        return "CTransaction(nVersion=%i vin=%s vout=%s nLockTime=%i)" % (self.nVersion, repr(self.vin), repr(self.vout), self.nLockTime)

class CBlock(object):
    def __init__(self):
        self.nVersion = 1
        self.hashPrevBlock = 0
        self.hashMerkleRoot = 0
        self.nTime = 0
        self.nBits = 0
        self.nNonce = 0
        self.vtx = []
        self.sha256 = None
    def deserialize(self, f):
        self.nVersion = struct.unpack("<i", f.read(4))[0]
        self.hashPrevBlock = deser_uint256(f)
        self.hashMerkleRoot = deser_uint256(f)
        self.nTime = struct.unpack("<I", f.read(4))[0]
        self.nBits = struct.unpack("<I", f.read(4))[0]
        self.nNonce = struct.unpack("<I", f.read(4))[0]
        self.vtx = deser_vector(f, CTransaction)
    def serialize(self):
        r = []
        r.append(struct.pack("<i", self.nVersion))
        r.append(ser_uint256(self.hashPrevBlock))
        r.append(ser_uint256(self.hashMerkleRoot))
        r.append(struct.pack("<I", self.nTime))
        r.append(struct.pack("<I", self.nBits))
        r.append(struct.pack("<I", self.nNonce))
        r.append(ser_vector(self.vtx))
        return ''.join(r)
    def calc_sha256(self):
        if self.sha256 is None:
            r = []
            r.append(struct.pack("<i", self.nVersion))
            r.append(ser_uint256(self.hashPrevBlock))
            r.append(ser_uint256(self.hashMerkleRoot))
            r.append(struct.pack("<I", self.nTime))
            r.append(struct.pack("<I", self.nBits))
            r.append(struct.pack("<I", self.nNonce))
            self.sha256 = uint256_from_str(hashlib.sha256(hashlib.sha256(''.join(r)).digest()).digest())
        return self.sha256

    def is_valid(self):
        self.calc_sha256()
        target = uint256_from_compact(self.nBits)
        if self.sha256 > target:
            return False
        hashes = []
        for tx in self.vtx:
            tx.sha256 = None
            if not tx.is_valid():
                return False
            tx.calc_sha256()
            hashes.append(ser_uint256(tx.sha256))
        
        while len(hashes) > 1:
            newhashes = []
            for i in xrange(0, len(hashes), 2):
                i2 = min(i+1, len(hashes)-1)
                newhashes.append(hashlib.sha256(hashlib.sha256(hashes[i] + hashes[i2]).digest()).digest())
            hashes = newhashes
        
        if uint256_from_str(hashes[0]) != self.hashMerkleRoot:
            return False
        return True
    def __repr__(self):
        return "CBlock(nVersion=%i hashPrevBlock=%064x hashMerkleRoot=%064x nTime=%s nBits=%08x nNonce=%08x vtx=%s)" % (self.nVersion, self.hashPrevBlock, self.hashMerkleRoot, time.ctime(self.nTime), self.nBits, self.nNonce, repr(self.vtx))

class msg_version(object):
    command = "version"
    def __init__(self):
        self.nVersion = MY_VERSION
        self.nServices = 0
        self.nTime = time.time()
        self.addrTo = CAddress()
        self.addrFrom = CAddress()
        self.nNonce = random.getrandbits(64)
        self.strSubVer = MY_SUBVERSION
        self.nStartingHeight = 0
        
    def deserialize(self, f):
        self.nVersion = struct.unpack("<i", f.read(4))[0]
        if self.nVersion == 10300:
            self.nVersion = 300
        self.nServices = struct.unpack("<Q", f.read(8))[0]
        self.nTime = struct.unpack("<q", f.read(8))[0]
        self.addrTo = CAddress()
        self.addrTo.deserialize(f)
        self.addrFrom = CAddress()
        self.addrFrom.deserialize(f)
        self.nNonce = struct.unpack("<Q", f.read(8))[0]
        self.strSubVer = deser_string(f)
        self.nStartingHeight = struct.unpack("<i", f.read(4))[0]
    def serialize(self):
        r = []
        r.append(struct.pack("<i", self.nVersion))
        r.append(struct.pack("<Q", self.nServices))
        r.append(struct.pack("<q", self.nTime))
        r.append(self.addrTo.serialize())
        r.append(self.addrFrom.serialize())
        r.append(struct.pack("<Q", self.nNonce))
        r.append(ser_string(self.strSubVer))
        r.append(struct.pack("<i", self.nStartingHeight))
        return ''.join(r)
    def __repr__(self):
        return "msg_version(nVersion=%i nServices=%i nTime=%s addrTo=%s addrFrom=%s nNonce=0x%016X strSubVer=%s nStartingHeight=%i)" % (self.nVersion, self.nServices, time.ctime(self.nTime), repr(self.addrTo), repr(self.addrFrom), self.nNonce, self.strSubVer, self.nStartingHeight)

class msg_verack(object):
    command = "verack"
    def __init__(self):
        pass
    def deserialize(self, f):
        pass
    def serialize(self):
        return ""
    def __repr__(self):
        return "msg_verack()"

class msg_addr(object):
    command = "addr"
    def __init__(self):
        self.addrs = []
    def deserialize(self, f):
        self.addrs = deser_vector(f, CAddress)
    def serialize(self):
        return ser_vector(self.addrs)
    def __repr__(self):
        return "msg_addr(addrs=%s)" % (repr(self.addrs))

class msg_inv(object):
    command = "inv"
    def __init__(self):
        self.inv = []
    def deserialize(self, f):
        self.inv = deser_vector(f, CInv)
    def serialize(self):
        return ser_vector(self.inv)
    def __repr__(self):
        return "msg_inv(inv=%s)" % (repr(self.inv))

class msg_getdata(object):
    command = "getdata"
    def __init__(self):
        self.inv = []
    def deserialize(self, f):
        self.inv = deser_vector(f, CInv)
    def serialize(self):
        return ser_vector(self.inv)
    def __repr__(self):
        return "msg_getdata(inv=%s)" % (repr(self.inv))

class msg_getblocks(object):
    command = "getblocks"
    def __init__(self):
        self.locator = CBlockLocator()
        self.hashstop = 0L
    def deserialize(self, f):
        self.locator = CBlockLocator()
        self.locator.deserialize(f)
        self.hashstop = deser_uint256(f)
    def serialize(self):
        r = []
        r.append(self.locator.serialize())
        r.append(ser_uint256(self.hashstop))
        return ''.join(r)
    def __repr__(self):
        return "msg_getblocks(locator=%s hashstop=%064x)" % (repr(self.locator), self.hashstop)

class msg_tx(object):
    command = "tx"
    def __init__(self):
        self.tx = CTransaction()
    def deserialize(self, f):
        self.tx.deserialize(f)
    def serialize(self):
        return self.tx.serialize()
    def __repr__(self):
        return "msg_tx(tx=%s)" % (repr(self.tx))

class msg_block(object):
    command = "block"
    def __init__(self):
        self.block = CBlock()
    def deserialize(self, f):
        self.block.deserialize(f)
    def serialize(self):
        return self.block.serialize()
    def __repr__(self):
        return "msg_block(block=%s)" % (repr(self.block))

class msg_getaddr(object):
    command = "getaddr"
    def __init__(self):
        pass
    def deserialize(self, f):
        pass
    def serialize(self):
        return ""
    def __repr__(self):
        return "msg_getaddr()"

class msg_ping(object):
    command = "ping"
    def __init__(self):
        pass
    def deserialize(self, f):
        pass
    def serialize(self):
        return ""
    def __repr__(self):
        return "msg_ping()"

class msg_alert(object):
    command = "alert"
    def __init__(self):
        pass
    def deserialize(self, f):
        pass
    def serialize(self):
        return ""
    def __repr__(self):
        return "msg_alert()"
    