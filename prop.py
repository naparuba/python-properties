import time
import sys
import os
import cPickle
from shinken.objects.host import Host


def print_title(title):
    print "\n\n"
    print "#" * 50
    print "TITLE: %s" % title
    print "#" * 50


def print_timed_entry(title, N, ref_time):
    print "\t%-25s:   (%d loops) => %.2f seconds" % (title, N, time.time() - ref_time)


def share_memory_mapping():
    print_title('share memory mapping')
    #### Share memory mapping
    import mmap
    import ctypes
    import struct
    
    P = '/dev/shm/blabla.txt'
    
    total_size = 100 * 1000000  # *1Mo
    bloc_size = 100 * mmap.PAGESIZE
    # write a simple example file
    with open(P, "wb") as f:
        f.write(b"\x00" * total_size)
    f = open(P, 'r+b')
    
    bufs = []
    N = total_size / bloc_size
    print "Will allocate %dK with %d blocs (%d by bloc) " % (total_size / 1024, N, bloc_size)
    t0 = time.time()
    for i in xrange(N):
        to_open = f.fileno()
        buf = mmap.mmap(to_open, bloc_size, mmap.MAP_SHARED, mmap.PROT_WRITE)
        bufs.append(buf)
        i = ctypes.c_int.from_buffer(buf)
        
        # Set a value
        i.value = 10
        
        # And manipulate it for kicks
        i.value += 1
        
        assert i.value == 11
        offset = struct.calcsize(i._type_)
        
        # The offset should be uninitialized ('\x00')
        # print buf[offset]
        # assert buf[offset] == '\x00'
        
        # Now ceate a string containing 'foo' by first creating a c_char array
        s_type = ctypes.c_char * len('foo')
        
        # Now create the ctypes instance
        s = s_type.from_buffer(buf, offset)
        
        # And finally set it
        s.raw = 'foo'
        
        new_i = struct.unpack('i', buf[:4])
        new_s = struct.unpack('3s', buf[4:7])
        # print "I", new_i, "S", new_s
    
    d = time.time() - t0
    print "Time to read/write %d file to /dev/shm: %.3f  (%.1f ops/s)" % (N, d, N / d)
    
    # Try fork job
    buf = mmap.mmap(-1, bloc_size, mmap.MAP_SHARED, mmap.PROT_WRITE)
    bufs.append(buf)
    i = ctypes.c_int.from_buffer(buf)
    # Set a value
    i.value = 10
    
    pid = os.fork()
    if pid == 0:  # son
        time.sleep(1)
        i = ctypes.c_int.from_buffer(buf)
        print "(in the son) i.value is ", i.value
        sys.exit(0)
    else:  # father
        i.value = 9999
    
    time.sleep(2)


class AutoProperties(type):
    def __new__(cls, name, bases, dct):
        # First map integer properties
        for (prop_raw, v) in dct['int_properties'].iteritems():
            prop = '_' + prop_raw
            
            
            def protected(prop):
                def __get(self):
                    # return self._y              #  ==> 3.5s
                    return getattr(self, prop)  # ==> 4.4s
                
                
                return __get
            
            
            get = protected(prop)
            
            
            def protected(prop):
                def __set(self, v):
                    # print "SET", '_'+prop_raw, v
                    setattr(self, '_' + prop_raw, v)
                
                
                return __set
            
            
            set = protected(prop)
            
            dct[prop_raw] = property(get, set)
        
        return type.__new__(cls, name, bases, dct)


class OOO(object):
    __metaclass__ = AutoProperties
    int_properties = {'x': 1, 'y': 1}
    bool_properties = {'b1': True, 'b2': True}
    
    
    def __init__(self):
        self._x = 1
        self._y = 1
        
        self._b1 = True
        self._b2 = True
    
    
    @property
    def b1(self):
        return self._b1
    
    
    @b1.setter
    def b1(self, v):
        self._b1 = v
    
    
    '''
    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, v):
        self._y = v
    '''
    
    '''
    def getY(self):
        return self._y
    def setY(self, v):
        self._y = v
    y = property(getY, setY)
    '''


def bench_host_creation_with_attr():
    ################## Becnh host creation with setattr/getattr/hasattr
    print_title("Bench host creation with attr")
    
    '''
    def testBit(int_type, offset):
        mask = 1 << offset
        return(int_type & mask)
    def setBit(int_type, offset):
        mask = 1 << offset
        return(int_type | mask)
    
    N = 10000000
    
    for pos in [20, 256]:
        t0 = time.time()
        mask = 1 << pos
        for i in xrange(N):
            f = 0
            #print "Set pos %d" % pos
            b = f | mask
            #print "Is set?", testBit(f, pos)
            #print type(f)
        print "Pos:%d %.2f" % (pos, time.time() - t0)
    '''
    
    # Hack fill default, by setting values directly to class
    cls = Host
    for prop, entry in cls.properties.iteritems():
        if entry.has_default:
            v = entry.pythonize(entry.default)
            setattr(cls, prop, v)
            # print "Pop: %s => %s" % (prop, v)
    
    delete_bool = False
    delete_running = False
    lst = []
    p1 = 0.0
    p2 = 0.0
    p3 = 0.0
    p4 = 0.0
    N = 40000
    print "Number of elements", N
    for i in xrange(N):
        t0 = time.time()
        h = Host({'host_name': 'blablacar', 'address': '127.0.0.%d' % i, 'active_checks_enabled': '1'})
        p1 += (time.time() - t0)
        # print h.__dict__
        # print h.active_checks_enabled
        
        t0 = time.time()
        # h.fill_default()
        p2 += (time.time() - t0)
        # print h.__dict__
        # print h.active_checks_enabled
        
        t0 = time.time()
        h.pythonize()
        p3 += (time.time() - t0)
        # print h.__dict__
        # print h.passive_checks_enabled
        
        t0 = time.time()
        nb_delete = 0
        nb_fields = 0
        properties = Host.properties
        for (k, e) in properties.iteritems():
            nb_fields += 1
            if not hasattr(h, k):
                continue
            elif delete_bool:
                if isinstance(getattr(h, k), bool):
                    delattr(h, k)
                    # pass
                    nb_delete += 1
        
        for (k, e) in Host.running_properties.iteritems():
            nb_fields += 1
            if not hasattr(h, k):
                continue
            elif delete_running:
                delattr(h, k)
                continue
            elif delete_bool:
                if isinstance(getattr(h, k), bool):
                    delattr(h, k)
                    # pass
                    nb_delete += 1
                
                #    print cPickle.dumps(h, 0)
        p4 += (time.time() - t0)
        
        #    print "Deleted: %d / %d total" % (nb_delete, nb_fields)
        lst.append(h)
    t0 = time.time()
    buf = cPickle.dumps(lst, 2)
    print "TIME picle %.2f   len=%d" % (time.time() - t0, len(buf))
    print "Phases: create=%.2f default=%.2f pythonize=%.2f clean=%.2f" % (p1, p2, p3, p4)


def bench_getattr_hasattr():
    ################## Becnh host creation with setattr/getattr/hasattr
    print_title("Becnh host creation with setattr/getattr/hasattr")
    
    h = Host({'host_name': 'blablacar', 'address': '127.0.0', 'active_checks_enabled': '1'})
    
    ######## Bench Get/Hasattr
    N = 1000000
    t0 = time.time()
    for i in xrange(N):
        try:
            getattr(h, 'blabla')
        except AttributeError, exp:
            pass
    print_timed_entry('Get+try', N, t0)
    # print "Get+try : %.2f" % (time.time() - t0)
    t0 = time.time()
    for i in xrange(N):
        hasattr(h, 'blabla')
    print_timed_entry('hasattr', N, t0)
    # print "Hasattr : %.2f" % (time.time() - t0)
    
    o = OOO()
    
    ####### Integers
    x = o._x
    
    N = 1000000
    
    
    # rr = range(N)
    def rr():
        return xrange(N)
    
    
    print "############ Integers"
    
    t0 = time.time()
    for i in rr():
        v = o.x
        assert (v == 1)
    print_timed_entry('@Property access', N, t0)
    # print "\t@Property access: FOR N: %d => %.2f" % (N, time.time() - t0)
    
    t0 = time.time()
    for i in rr():
        v = o._x
        assert (v == 1)
    print_timed_entry('Direct access _x', N, t0)
    # print "\tDirect access _x:     FOR N: %d => %.2f" % (N, time.time() - t0)
    
    t0 = time.time()
    for i in rr():
        v = o.__dict__['_x']
        assert (v == 1)
    print_timed_entry('Direct __dict__ access', N, t0)
    # print "\tDirect __dict__ access :   FOR N: %d => %.2f" % (N, time.time() - t0)
    
    code = compile('v = o._x', '<string>', 'exec')
    t0 = time.time()
    for i in rr():
        exec code in locals()
        assert (v == 1)
    print_timed_entry('Compile+Exec', N, t0)
    # print "\tCompile+Exec :   FOR N: %d => %.2f" % (N, time.time() - t0)
    
    print "############ Python Booleans with bitmask"
    o._b1 = True
    
    t0 = time.time()
    for i in rr():
        v = o.b1
    print_timed_entry('@property', N, t0)
    # print "\tProperty: FOR N: %d => %.2f" % (N, time.time() - t0)
    
    '''
    def testBit(int_type, offset):
        mask = 1 << offset
        return(int_type & mask)
    def setBit(int_type, offset):
        mask = 1 << offset
        return(int_type | mask)
    def clearBit(int_type, offset):
        mask = ~(1 << offset)
        return(int_type & mask)
    '''
    b = 0
    offset = 5
    mask = 1 << offset
    b = b | mask
    
    t0 = time.time()
    for i in rr():
        v = (b & mask) != 0
        assert (v is True)
    print_timed_entry('Raw', N, t0)
    # print "\tRaw:     FOR N: %d => %.2f" % (N, time.time() - t0)
    
    t0 = time.time()
    for i in rr():
        v = o.__dict__['_b1']
        assert (v is True)
    print_timed_entry('__dict__', N, t0)
    # print "\tDict :   FOR N: %d => %.2f" % (N, time.time() - t0)
    
    print "############## ctypes booleans"
    import ctypes
    
    c_uint8 = ctypes.c_uint8
    
    class Flags_bits(ctypes.LittleEndianStructure):
        _fields_ = [
            ("f1", c_uint8, 1),  # asByte & 1
            ("f2", c_uint8, 1),  # asByte & 2
            ("f3", c_uint8, 1),  # asByte & 4
            ("f4", c_uint8, 1),  # asByte & 8
        ]
    
    class Flags(ctypes.Union):
        _anonymous_ = ("bit",)
        _fields_ = [
            ("bit", Flags_bits),
            ("asByte", c_uint8)
        ]
    
    flags = Flags()
    flags.asByte = 0x2  # ->0010
    
    '''
    print( "logout: %i"      % flags.bit.f1   )
    # `bit` is defined as anonymous field, so its fields can also be accessed directly:
    print( "f1: %i"      % flags.bit.f1     )
    print( "f2:  %i" % flags.bit.f2 )
    print( "f3   :  %i" % flags.bit.f3    )
    print( "f4  : %i"      % flags.bit.f4       )
    '''
    
    t0 = time.time()
    for i in rr():
        v = flags.bit.f2
        assert (v == 1)
    print_timed_entry('Raw', N, t0)
    # print "\tRaw :   FOR N: %d => %.2f" % (N, time.time() - t0)
    
    t0 = time.time()
    for i in rr():
        v = getattr(flags.bit, 'f2')
        assert (v == 1)
    print_timed_entry('getattr', N, t0)
    # print "\tGetattr :   FOR N: %d => %.2f" % (N, time.time() - t0)
    
    code = compile('v = flags.bit.f2', '<string>', 'exec')
    t0 = time.time()
    for i in rr():
        exec code in locals()
        assert (v == 1)
    print_timed_entry('compile+exec', N, t0)
    # print "\tExec :   FOR N: %d => %.2f" % (N, time.time() - t0)
    
    print "############ Class property default access"
    
    class BBBB(object):
        x = 1
        
        
        def __init__(self):
            self.y = 2
    
    o = BBBB()
    t0 = time.time()
    for i in rr():
        v = o.x
        assert (v == 1)
    print_timed_entry('Direct on class level', N, t0)
    # print "\tProperty (default) on class: FOR N: %d => %.2f" % (N, time.time() - t0)
    
    t0 = time.time()
    for i in rr():
        v = o.y
        assert (v == 2)
    print_timed_entry('Direct on instance', N, t0)
    # print "\tRaw (direct):     FOR N: %d => %.2f" % (N, time.time() - t0)
    
    print "Hasattr a value on class?", hasattr(o, 'x'), "and on dict?", 'x' in o.__dict__
    print "Getattr a value on a class?", getattr(o, 'x')


share_memory_mapping()
bench_getattr_hasattr()
bench_host_creation_with_attr()
