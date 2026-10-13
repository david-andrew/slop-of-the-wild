// Linux/x86-64 opt-in audit: count actual Vulkan draw submissions per present.
// cc -shared -fPIC -O2 tools/round82_draw_audit.c -o build/round82/draw-audit.so
#define _GNU_SOURCE
#include <link.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
static unsigned draws, frame;
static void (*real_draw)(void *,uint32_t,uint32_t,uint32_t,uint32_t);
static void (*real_indexed)(void *,uint32_t,uint32_t,uint32_t,int32_t,uint32_t);
static int (*real_present)(void *,const void *);
static void draw(void *b,uint32_t v,uint32_t i,uint32_t f,uint32_t g) { draws++; real_draw(b,v,i,f,g); }
static void indexed(void *b,uint32_t v,uint32_t i,uint32_t f,int32_t o,uint32_t g) { draws++; real_indexed(b,v,i,f,o,g); }
static int present(void *q,const void *i) {
    int r=real_present(q,i);
    char line[96];int n=snprintf(line,sizeof line,"draw sample: %u %u\n",++frame,draws);
    if(n>0 && n<(int)sizeof line)write(2,line,n);
    draws=0;return r;
}
unsigned int la_version(unsigned int v) { return LAV_CURRENT; }
unsigned int la_objopen(struct link_map *m,Lmid_t n,uintptr_t *c) { return LA_FLG_BINDTO|LA_FLG_BINDFROM; }
uintptr_t la_symbind64(Elf64_Sym *s,unsigned int n,uintptr_t *r,uintptr_t *d,unsigned int *f,const char *name) {
    if(!strcmp(name,"vkCmdDraw")){real_draw=(__typeof__(real_draw))s->st_value;return (uintptr_t)draw;}
    if(!strcmp(name,"vkCmdDrawIndexed")){real_indexed=(__typeof__(real_indexed))s->st_value;return (uintptr_t)indexed;}
    if(!strcmp(name,"vkQueuePresentKHR")){real_present=(__typeof__(real_present))s->st_value;return (uintptr_t)present;}
    return s->st_value;
}
