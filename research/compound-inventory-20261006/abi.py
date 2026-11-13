# Minimal legacy Keccak-256 (Ethereum), no external dependencies.
RC=[0x1,0x8082,0x800000000000808a,0x8000000080008000,0x808b,0x80000001,0x8000000080008081,0x8000000000008009,0x8a,0x88,0x80008009,0x8000000a,0x8000808b,0x800000000000008b,0x8000000000008089,0x8000000000008003,0x8000000000008002,0x8000000000000080,0x800a,0x800000008000000a,0x8000000080008081,0x8000000000008080,0x80000001,0x8000000080008008]
R=[[0,36,3,41,18],[1,44,10,45,2],[62,6,43,15,61],[28,55,25,21,56],[27,20,39,8,14]]; MASK=(1<<64)-1

def kh(b):
 b=bytearray(b); b.append(1)
 while len(b)%136!=135:b.append(0)
 b.append(128);a=[0]*25
 def rot(v,n):return ((v<<n)|(v>>(64-n)))&MASK if n else v
 for off in range(0,len(b),136):
  for i in range(17):a[i]^=int.from_bytes(b[off+i*8:off+i*8+8],'little')
  for rc in RC:
   c=[a[x]^a[x+5]^a[x+10]^a[x+15]^a[x+20] for x in range(5)];d=[c[(x-1)%5]^rot(c[(x+1)%5],1) for x in range(5)]
   for x in range(5):
    for y in range(5):a[x+5*y]^=d[x]
   z=[0]*25
   for x in range(5):
    for y in range(5):z[y+5*((2*x+3*y)%5)]=rot(a[x+5*y],R[x][y])
   for x in range(5):
    for y in range(5):a[x+5*y]=z[x+5*y]^((~z[(x+1)%5+5*y])&z[(x+2)%5+5*y])
   a[0]^=rc
 return b''.join(x.to_bytes(8,'little') for x in a)[:32].hex()
def enc(sig,*args):return '0x'+kh(sig.encode())[:8]+''.join((a.removeprefix('0x').zfill(64) if isinstance(a,str) else hex(a)[2:].zfill(64)) for a in args)
def words(h):return [int(h[i:i+64],16) for i in range(2,len(h),64)]
assert kh(b'')=='c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470'
assert enc('transfer(address,uint256)',1,1).startswith('0xa9059cbb')
