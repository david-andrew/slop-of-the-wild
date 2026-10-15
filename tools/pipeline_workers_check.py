#!/usr/bin/env python3
"""CPU-only helper contract: stride, per-job status, joins and real TLS threads."""
from pathlib import Path
import os,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(tempfile.mkdtemp(prefix='pipeline-workers-',dir=ROOT/'build'))
(OUT/'fake.c').write_text(r'''
#include <stdint.h>
#include <stdatomic.h>
#include <time.h>
static atomic_int concurrent,peak;
static _Thread_local uint64_t calls;
int32_t vkCreateGraphicsPipelines(void *dev,uint64_t cache,uint32_t n,const uint64_t *info,const void *alloc,uint64_t *out){
    if(dev!=(void*)42 || cache!=71 || n!=1 || alloc) return -1;
    int active=atomic_fetch_add(&concurrent,1)+1,old=atomic_load(&peak);
    while(active>old && !atomic_compare_exchange_weak(&peak,&old,active)){}
    struct timespec delay={.tv_nsec=1000000};nanosleep(&delay,0);
    *out=info[0]*13+calls++*0;
    atomic_fetch_sub(&concurrent,1);
    return info[0]==999 ? -1:0;
}
int maximum_parallelism(void){return atomic_load(&peak);}
''')
(OUT/'test.c').write_text(r'''
#include <assert.h>
#include <stdint.h>
#include <dlfcn.h>
#include <stdio.h>
extern int32_t botw_compile_pipelines(void*,uint64_t,uint64_t,const void*,uint64_t,uint64_t*);
int main(void){
 void *lib=dlopen("libvulkan.so.1",RTLD_NOW|RTLD_LOCAL);assert(lib);
 for(int count=1;count<=33;count++){
  uint64_t infos[33][3],out[33]={0};
  for(int i=0;i<count;i++){infos[i][0]=i+1;infos[i][1]=0xFFFF;infos[i][2]=0xFFFF;}
  assert(botw_compile_pipelines((void*)42,71,count,infos,sizeof(infos[0]),out)==0);
  for(int i=0;i<count;i++)assert(out[i]==(uint64_t)(i+1)*13);
 }
 uint64_t failed=999,out=0;assert(botw_compile_pipelines((void*)42,71,1,&failed,8,&out)!=0);
 int (*peak)(void)=dlsym(lib,"maximum_parallelism");assert(peak && peak()>1);
 puts("PASS pthread pipeline transport: 561 unique jobs, padded stride, joined results, failure propagation and concurrent threads");
}
''')
subprocess.run(['cc','-O2','-fPIC','-shared','-pthread',str(OUT/'fake.c'),'-o',str(OUT/'libvulkan.so.1')],check=True)
subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror','-pthread',str(ROOT/'tools/pipeline_workers.c'),str(OUT/'test.c'),'-ldl','-o',str(OUT/'test')],check=True)
subprocess.run([str(OUT/'test')],env=os.environ|{'LD_LIBRARY_PATH':str(OUT)},check=True)
