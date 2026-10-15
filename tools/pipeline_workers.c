// Game-side Vulkan compilation transport. Sloppy 0.6 Linux pool workers use
// raw clone stacks; libc/driver TLS needs actual pthreads. Only Vulkan calls run
// here. All create-info storage and program-map ownership remain in Sloppy.
#include <dlfcn.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stddef.h>
typedef int32_t (*Create)(void *, uint64_t, uint32_t, const void *, const void *, uint64_t *);
typedef struct {
    void *device; uint64_t cache; size_t count, stride; const uint8_t *infos;
    uint64_t *handles; Create create; atomic_size_t next; atomic_int failed;
} Batch;
static void *compile(void *arg) {
    Batch *b = arg;
    for (;;) {
        size_t i = atomic_fetch_add_explicit(&b->next, 1, memory_order_relaxed);
        if (i >= b->count) break;
        if (b->create(b->device,b->cache,1,b->infos+i*b->stride,NULL,b->handles+i) != 0)
            atomic_store_explicit(&b->failed,1,memory_order_relaxed);
    }
    return NULL;
}
int32_t botw_compile_pipelines(void *device,uint64_t cache,uint64_t count,
                              const void *infos,uint64_t stride,uint64_t *handles) {
    void *library = dlopen("libvulkan.so.1",RTLD_NOW|RTLD_LOCAL);
    if (!library) return -1;
    Create create = (Create)dlsym(library,"vkCreateGraphicsPipelines");
    if (!create) {dlclose(library);return -1;}
    Batch b = {.device=device,.cache=cache,.count=count,.stride=stride,
               .infos=infos,.handles=handles,.create=create,.next=0,.failed=0};
    pthread_t threads[3]; size_t started=0;
    for(size_t i=0;i<3 && i+1<count;i++)
        if(pthread_create(threads+started,NULL,compile,&b)==0) started++;
    compile(&b);
    for(size_t i=0;i<started;i++) pthread_join(threads[i],NULL);
    int32_t result=atomic_load_explicit(&b.failed,memory_order_relaxed);
    dlclose(library);
    return result;
}
