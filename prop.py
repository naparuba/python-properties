import time
import sys
import os
import traceback

try:
    import cPickle
except ImportError:
    import pickle as cPickle

try:
    xrange
except NameError:
    xrange = range

try:
    from shinken.objects.host import Host
except ImportError:
    Host = None
from multiprocessing.sharedctypes import Value, Array
from ctypes import c_bool, c_wchar_p, c_long


def print_title(title):
    print("\n\n")
    print("#" * 60)
    print("TITLE: %s" % title)
    print("#" * 60)


def print_timed_entry(title, N, ref_time):
    elapsed_time = time.time() - ref_time
    print("\t%-25s:   (%d loops) => %.3f seconds    (%10.4f M/s)" % (title, N, elapsed_time, (N / elapsed_time) / 1000000.0))


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
    N = int(total_size / bloc_size)
    print("Will allocate %dK with %d blocs (%d by bloc) " % (total_size / 1024, N, bloc_size))
    t0 = time.time()
    for i in xrange(N):
        to_open = f.fileno()
        buf = mmap.mmap(to_open, bloc_size, mmap.MAP_SHARED, mmap.PROT_WRITE)
        bufs.append(buf)
        try:
            i = ctypes.c_int.from_buffer(buf)
        except TypeError:  # in pypy 5
            print("PYPY detected, skip this test")
            return
        
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
        s.raw = b'foo'
        
        new_i = struct.unpack('i', buf[:4])
        new_s = struct.unpack('3s', buf[4:7])
        # print "I", new_i, "S", new_s
    
    d = time.time() - t0
    print("Time to read/write %d file to /dev/shm: %.3f  (%.1f ops/s)" % (N, d, N / d))
    
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
        print("(in the son) i.value is ", i.value)
        sys.exit(0)
    else:  # father
        i.value = 9999
    
    time.sleep(2)


def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    
    
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    
    
    return wrapper


class AutoProperties(type):
    def __new__(cls, name, bases, dct):
        # First map integer properties
        for (prop_raw, v) in dct['int_properties'].items():
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


@add_metaclass(AutoProperties)
class OOO(object):
    # __metaclass__ = AutoProperties
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


from cffi import FFI

ffi = FFI()

ffi.cdef('''
typedef struct FOO FOO;
struct FOO {
   int prop1;
   int prop2;
   int prop3;
   int prop4;
   int prop5;
   int prop6;
   int prop7;
   int prop8;
   int prop9;
   int prop10;
};
void FOO_set_prop1(FOO*, int);

''')

# ffi.set_source("_example",
# r"""
#    void FOO_set_prop1(FOO* self, int v){
#        self->prop1 = v;
#    }
# """)
try:
    Clib = None
    Clib = ffi.verify(
        r'''
    typedef struct FOO FOO;
    struct FOO {
    int prop1;
    int prop2;
    int prop3;
    int prop4;
    int prop5;
    int prop6;
    int prop7;
    int prop8;
    int prop9;
    int prop10;
    };
    void FOO_set_prop1(FOO* self, int v){
    self->prop1 = v;
    };
        '''
    )
except Exception as exp:
    print('ERROR CFFI: %s' % traceback.format_exc())
# ffi.compile()
print("CLib", Clib)


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
    
    if Host is None:
        print("Shinken is not installed, skip this test")
        return
    
    # Hack fill default, by setting values directly to class
    cls = Host
    for prop, entry in cls.properties.items():
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
    print("Number of elements", N)
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
        for (k, e) in properties.items():
            nb_fields += 1
            if not hasattr(h, k):
                continue
            elif delete_bool:
                if isinstance(getattr(h, k), bool):
                    delattr(h, k)
                    # pass
                    nb_delete += 1
        
        for (k, e) in Host.running_properties.items():
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
    print("TIME pickle %.2f   len=%d" % (time.time() - t0, len(buf)))
    print("Phases: create=%.2f default=%.2f pythonize=%.2f clean=%.2f" % (p1, p2, p3, p4))


def bench_getattr_hasattr():
    ################## Becnh host creation with setattr/getattr/hasattr
    print_title("Bench host creation with setattr/getattr/hasattr")
    
    N = 1000000
    
    print("############ CFFI")
    if Clib is None:
        print('CLib is None, skiping this test')
        return
    FOO_set_prop1 = Clib.FOO_set_prop1
    struct_obj = ffi.new("FOO*")
    
    class CFFISurClass(object):
        def __init__(self):
            self.struct_obj = ffi.new("FOO*")
    
    cffi_sur_class = CFFISurClass()
    
    t0 = time.time()
    for i in xrange(N):
        struct_obj.prop1 = 33
    print_timed_entry('CFFI: struct.prop1', N, t0)
    
    t0 = time.time()
    for i in xrange(N):
        cffi_sur_class.struct_obj.prop1 = 33
    print_timed_entry('CFFI: CLASS->struct.x', N, t0)
    
    t0 = time.time()
    for i in xrange(N):
        FOO_set_prop1(struct_obj, 33)
    print_timed_entry('CFFI: f(struct*, value)', N, t0)
    
    o = OOO()
    
    print("############ Getattr & hasattr")
    t0 = time.time()
    for i in xrange(N):
        try:
            getattr(o, 'blabla')
        except AttributeError as exp:
            pass
    print_timed_entry('Get+try', N, t0)
    
    t0 = time.time()
    for i in xrange(N):
        hasattr(o, 'blabla')
    print_timed_entry('hasattr', N, t0)
    
    ####### Integers
    x = o._x
    
    N = 1000000
    
    
    # rr = range(N)
    def rr():
        return xrange(N)
    
    
    print("############ Integers")
    
    t0 = time.time()
    for i in rr():
        v = o.x
        assert (v == 1)
    print_timed_entry('@Property access', N, t0)
    
    t0 = time.time()
    for i in rr():
        v = o._x
        assert (v == 1)
    print_timed_entry('Direct access _x', N, t0)
    
    t0 = time.time()
    for i in rr():
        v = o.__dict__['_x']
        assert (v == 1)
    print_timed_entry('Direct __dict__ access', N, t0)
    
    code = compile('v = o._x', '<string>', 'exec')
    t0 = time.time()
    for i in rr():
        exec (code, locals())
        assert (v == 1)
    print_timed_entry('Compile+Exec', N, t0)
    
    t0 = time.time()
    for i in rr():
        v = getattr(o, '_x')
        assert (v == 1)
    print_timed_entry('Getattr _x', N, t0)
    
    print("############ Python Booleans with bitmask")
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
    
    t0 = time.time()
    for i in rr():
        v = o.__dict__['_b1']
        assert (v is True)
    print_timed_entry('__dict__', N, t0)
    
    print("############## ctypes booleans")
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
        exec (code, locals())
        assert (v == 1)
    print_timed_entry('compile+exec', N, t0)
    # print "\tExec :   FOR N: %d => %.2f" % (N, time.time() - t0)
    
    print("############ Class property default access")
    
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
    
    print("Hasattr a value on class?", hasattr(o, 'x'), "and on dict?", 'x' in o.__dict__)
    print("Getattr a value on a class?", getattr(o, 'x'))


def bench_sharedctypes():
    N = 100000
    NB_PROC = 2
    elements = []
    t0 = time.time()
    for i in xrange(N):
        elements.append(Value(c_bool, False, lock=False))
    t1 = time.time()
    creation_time = (t1 - t0)
    print("Shared types Bool : Create: %.2f  (%d/s)" % (creation_time, N / creation_time))
    
    M = 200
    t2 = time.time()
    for j in xrange(M):
        for i in xrange(N):
            elements[i].value = True
    t3 = time.time()
    set_time = t3 - t2
    print("Shared types Bool: Linear set:  %.2f (%d/s)" % (set_time, N * M / set_time))
    
    from multiprocessing import Process
    def set_massive(process_id, lst, nb_loop):
        print("PROCESS %d (nb_loop:%s)" % (process_id, nb_loop))
        k = 0
        for j in xrange(int(nb_loop)):
            for cvalue in lst:
                k += 1
                cvalue.value = True
        print("PROCESS %d finish (%d operations)" % (process_id, k))
    
    
    all_process = []
    for process_id in xrange(NB_PROC):
        p = Process(target=set_massive, args=(process_id, elements, M / NB_PROC))
        all_process.append(p)
    t0 = time.time()
    for p in all_process:
        p.start()
    for p in all_process:
        p.join()
    t1 = time.time()
    process_time = t1 - t0
    print("Shared types Bool: // set:  %.2f (%d/s)" % (process_time, N * M / process_time))


share_memory_mapping()
bench_getattr_hasattr()
bench_host_creation_with_attr()
bench_sharedctypes()
