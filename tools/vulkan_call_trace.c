// Opt-in Linux/x86-64 dynamic-linker audit of unmodified Vulkan/ALSA calls.
// cc -shared -fPIC -O2 tools/vulkan_call_trace.c -o build/pacing060/vulkan-trace.so
// LD_AUDIT=$PWD/build/pacing060/vulkan-trace.so flock ... <game>
// Reports monotonic call boundaries and present serials; CPU calls, not GPU timestamps.
// The legacy "vk call:" prefix is retained for existing attribution parsers.
#define _GNU_SOURCE
#include <link.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static uint64_t present_serial;
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec*1e-9; }
static void report(const char *name, double start, int result, int always) {
    double end = now();
    if (!always && (end-start)*1000 <= 2) return;
    char b[192];
    int n = snprintf(b, sizeof b, "vk call: %s %.9f %.9f %.6f result %d frame %lu\n", name, start, end, (end-start)*1000, result, (unsigned long)present_serial);
    if (n > 0 && n < (int)sizeof b) write(2, b, n);
}
// Dispatchable handles are pointers; non-dispatchable handles are uint64_t on
// this 64-bit ABI. Opaque Vulkan structs are only forwarded, never inspected.
#define CALL(NAME, PARAMS, ARGS, ALWAYS) \
    static int (*real_##NAME) PARAMS; \
    static int trace_##NAME PARAMS { double call_start=now(); int r=real_##NAME ARGS; report(#NAME,call_start,r,ALWAYS); if (!strcmp(#NAME,"vkQueuePresentKHR")) present_serial++; return r; }
#define CREATE(NAME) CALL(NAME, (void *d, const void *i, const void *a, uint64_t *o), (d,i,a,o), 1)
CREATE(vkCreateBuffer)
CREATE(vkCreateImage)
CREATE(vkAllocateMemory)
CREATE(vkCreateSwapchainKHR)
CREATE(vkCreateDescriptorPool)
CALL(vkCreateGraphicsPipelines, (void *d,uint64_t c,uint32_t n,const void *i,const void *a,uint64_t *o), (d,c,n,i,a,o), 1)
CALL(vkGetPipelineCacheData, (void *d,uint64_t c,size_t *n,void *p), (d,c,n,p), 1)
CALL(vkWaitForFences, (void *d,uint32_t n,const uint64_t *f,uint32_t all,uint64_t timeout), (d,n,f,all,timeout), 0)
static int (*real_vkAcquireNextImageKHR)(void *,uint64_t,uint64_t,uint64_t,uint64_t,uint32_t *);
static int trace_vkAcquireNextImageKHR(void *d,uint64_t s,uint64_t timeout,uint64_t sem,uint64_t f,uint32_t *i) {
    double start=now(); int r=real_vkAcquireNextImageKHR(d,s,timeout,sem,f,i);
    report("vkAcquireNextImageKHR",start,r,0);
    if ((now()-start)*1000>2 && (r==0 || r==1000001003)) {
        char b[128]; int n=snprintf(b,sizeof b,"vk acquire image: %u timeout %lu frame %lu\n",*i,(unsigned long)timeout,(unsigned long)present_serial);
        if (n>0 && n<(int)sizeof b) write(2,b,n);
    }
    return r;
}
static int (*real_vkGetSwapchainImagesKHR)(void *,uint64_t,uint32_t *,uint64_t *);
static int trace_vkGetSwapchainImagesKHR(void *d,uint64_t s,uint32_t *n,uint64_t *images) {
    double start=now(); int r=real_vkGetSwapchainImagesKHR(d,s,n,images);
    report("vkGetSwapchainImagesKHR",start,r,1);
    char b[128]; int count=snprintf(b,sizeof b,"vk swapchain images: %u frame %lu\n",*n,(unsigned long)present_serial);
    if(count>0 && count<(int)sizeof b) write(2,b,count);
    return r;
}
CALL(vkQueuePresentKHR, (void *q,const void *i), (q,i), 0)
CALL(vkQueueSubmit2, (void *q,uint32_t n,const void *i,uint64_t f), (q,n,i,f), 0)
CALL(vkDeviceWaitIdle, (void *d), (d), 0)
CALL(vkMapMemory, (void *d,uint64_t m,uint64_t o,uint64_t s,uint32_t f,void **p), (d,m,o,s,f,p), 0)
CALL(libdecor_dispatch, (void *p,int timeout), (p,timeout), 0)
CALL(snd_pcm_recover, (void *p,int e,int silent), (p,e,silent), 1)
static long (*real_snd_pcm_avail_update)(void *);
static long trace_snd_pcm_avail_update(void *p) { double t=now(); long r=real_snd_pcm_avail_update(p); report("snd_pcm_avail_update",t,(int)r,0); return r; }
static long (*real_snd_pcm_writei)(void *,const void *,unsigned long);
static long trace_snd_pcm_writei(void *p,const void *b,unsigned long n) { double t=now(); long r=real_snd_pcm_writei(p,b,n); report("snd_pcm_writei",t,(int)r,0); return r; }
static void (*real_vkUpdateDescriptorSets)(void *,uint32_t,const void *,uint32_t,const void *);
static void trace_vkUpdateDescriptorSets(void *d,uint32_t n,const void *w,uint32_t c,const void *p) {
    double t=now(); real_vkUpdateDescriptorSets(d,n,w,c,p); report("vkUpdateDescriptorSets",t,0,0);
}
unsigned int la_version(unsigned int v) { return LAV_CURRENT; }
unsigned int la_objopen(struct link_map *map, Lmid_t ns, uintptr_t *cookie) { return LA_FLG_BINDTO | LA_FLG_BINDFROM; }
uintptr_t la_symbind64(Elf64_Sym *sym,unsigned int ndx,uintptr_t *ref,uintptr_t *def,unsigned int *flags,const char *name) {
#define BIND(NAME) if (!strcmp(name,#NAME)) { real_##NAME=(__typeof__(real_##NAME))sym->st_value; return (uintptr_t)trace_##NAME; }
    BIND(libdecor_dispatch) BIND(snd_pcm_recover) BIND(snd_pcm_avail_update) BIND(snd_pcm_writei)
    BIND(vkCreateBuffer) BIND(vkCreateImage) BIND(vkAllocateMemory)
    BIND(vkCreateSwapchainKHR) BIND(vkCreateDescriptorPool) BIND(vkCreateGraphicsPipelines)
    BIND(vkWaitForFences) BIND(vkAcquireNextImageKHR) BIND(vkQueuePresentKHR)
    BIND(vkGetPipelineCacheData) BIND(vkGetSwapchainImagesKHR) BIND(vkQueueSubmit2) BIND(vkDeviceWaitIdle) BIND(vkMapMemory) BIND(vkUpdateDescriptorSets)
    return sym->st_value;
}
