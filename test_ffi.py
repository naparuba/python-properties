
gcc -fPIC -shared -O3 -march=native -ffast-math tuto.c -o tuto.so -std=gnu99 -fopenmp

#include <stdio.h>
#include "omp.h"

int factorial_fast(int n){
  if(n <= 0){
    return 1;
  }else{
    int r = factorial_fast(n - 1) * n;
    //printf("%d->%d\n", n, r);
    return r;
  }
}




int compute_large(int n){
  int r=0;
  #pragma omp simd for
  for(int i=0; i<n;i++){
    r += 1;
  }
  return r;
}


# file "cffi_factorials.py"

import time
import threading
from cffi import FFI
ffi = FFI()

ffi.cdef("int factorial_fast(int);")
ffi.cdef("int compute_large(int n);")

C = ffi.dlopen("./tuto.so")
factorial_fast = C.factorial_fast
compute_large = C.compute_large

N = 10000000
NB_THREADS=1

def f(n):
    print "Compute", n
    for i in xrange(n):
        r = compute_large(10000)
    print "Finish"

t0 = time.time()

threads = []
for tid in xrange(NB_THREADS):
    t = threading.Thread(None, target=f, args=(N / NB_THREADS, ))
    threads.append(t)

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()

t1 = time.time()
print "Result:", t1 - t0